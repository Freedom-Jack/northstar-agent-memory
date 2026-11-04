"""The six SQLite stores and how they open (MEMORY-ARCHITECTURE §2.1, §3.1).

`open_store(name)` returns one connection to `<data root>/<name>.db` with the PRAGMAs of §3.1, after applying any
pending schema migrations. Each store has one writer; this module only opens connections and keeps the rules of
the files themselves. Schema files live in `schema/`: `<store>.sql` is version 1, `<store>.<n>.sql` is version n.
"""

from __future__ import annotations

import json
import os
import plistlib
import re
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping

from northstar_agent_memory import paths
from northstar_agent_memory.core.ids import utc_now

STORES = ("history", "memory", "working", "index", "overview", "runs")
DEFAULT_TENANT = "local"  # every table carries tenant_id (§3.3)

# Full sync where a lost write would lose canonical data; the derived stores can be rebuilt (§3.1).
SYNCHRONOUS = {
    "history": "FULL",
    "memory": "FULL",
    "working": "FULL",
    "runs": "FULL",
    "index": "NORMAL",
    "overview": "NORMAL",
}
BUSY_TIMEOUT_MS = 5000

SCHEMA_DIR = Path(__file__).parent / "schema"


class EncryptionRequired(RuntimeError):
    """Real capture stays off until the data folder is encrypted at rest (PL-3, §3.1)."""


# Set this (to anything but "" or "0") only in a test run: it lets the stores open on an unencrypted volume.
TEST_MARKER = "NORTHSTAR_TEST_MODE"
_BOOT_MOUNTS = ("/", "/System/Volumes/Data")


def _fdesetup_status() -> str:
    result = subprocess.run(["fdesetup", "status"], capture_output=True, text=True, timeout=10, check=False)
    return result.stdout


def _volume_device(path: Path) -> str:
    """The device node of the volume that holds `path` (or the nearest folder above it that exists), from `df`."""
    probe = path
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    result = subprocess.run(["df", "-P", str(probe)], capture_output=True, text=True, timeout=10, check=False)
    lines = result.stdout.strip().splitlines()
    if result.returncode != 0 or len(lines) < 2 or not lines[-1].split()[0].startswith("/dev/"):
        raise ValueError(f"could not find the volume that holds {probe}")
    return lines[-1].split()[0]


def _volume_info(path: Path) -> dict[str, Any]:
    """`diskutil info -plist` for the volume that holds `path`: its encryption, lock state and mount point."""
    result = subprocess.run(
        ["diskutil", "info", "-plist", _volume_device(path)], capture_output=True, timeout=10, check=False
    )
    info = plistlib.loads(result.stdout)
    if result.returncode != 0 or "Error" in info:
        raise ValueError(f"diskutil could not describe the volume: {info.get('ErrorMessage') or result.returncode}")
    return info


def _temp_roots() -> list[Path]:
    names = [tempfile.gettempdir(), "/tmp", "/var/tmp", "/private/tmp", "/private/var/tmp"]
    return [Path(n).resolve() for n in names]


def _is_test_run(root: Path) -> bool:
    """A test run: the test marker is set, or the data root lies inside a temporary folder (symlinks resolved, so a
    link inside /tmp that points at a real folder does not count). A bare NORTHSTAR_HOME elsewhere does not."""
    if os.environ.get(TEST_MARKER, "") not in ("", "0"):
        return True
    if not os.environ.get("NORTHSTAR_HOME"):
        return False
    resolved = root.resolve()
    return any(resolved.is_relative_to(temp) for temp in _temp_roots())


def require_encryption(root: Path | None = None) -> None:
    """On macOS, raise unless the data root is on an encrypted volume (PL-3).

    The check is skipped only in a test run: the test marker `NORTHSTAR_TEST_MODE` is set, or NORTHSTAR_HOME points
    inside a temporary folder. NORTHSTAR_HOME alone moves a real data root and does not skip it. A data root
    counts as encrypted when it is on the boot volume and FileVault is on, or when `diskutil info` shows its volume
    as an encrypted, unlocked APFS volume (an encrypted disk image mounted for the data root works the same way).
    Any failure to find out is a refusal. Off macOS the platform's own adapter decides.
    """
    root = paths.data_root() if root is None else root
    if sys.platform != "darwin" or _is_test_run(root):
        return
    try:
        info = _volume_info(root)
        if info.get("Locked"):
            raise EncryptionRequired(f"the volume holding {root} is locked")
        if info.get("FileVault"):
            return  # an encrypted APFS volume: the boot volume under FileVault, or an encrypted disk image mounted
        if info.get("MountPoint") in _BOOT_MOUNTS and "FileVault is On" in _fdesetup_status():
            return
    except (OSError, subprocess.SubprocessError, ValueError, plistlib.InvalidFileException) as err:
        raise EncryptionRequired(f"could not check that {root} is encrypted: {err}") from err
    raise EncryptionRequired(
        f"{root} is not on an encrypted volume: turn FileVault on, or keep the data folder on an encrypted disk image"
    )


# --- starting values -----------------------------------------------------------------------------------------------


def maintenance_setting(
    section: Mapping[str, Any], key: str, default: float, *, whole: bool = False, low: float = 0, high: float | None = None,
    low_open: bool = False,
) -> float:
    """One `[maintenance]` number: the default if the key is missing, else a validated number (ValueError if not).

    `whole` wants a whole number; the value must be at least `low` (above it with `low_open`) and at most `high`."""
    value = section.get(key)
    if value is None:
        return default
    bad = isinstance(value, bool) or not isinstance(value, (int, float)) or (whole and int(value) != value)
    bad = bad or value < low or (low_open and value == low) or (high is not None and value > high)
    if bad:
        kind = "a whole number" if whole else "a number"
        span = f"from {low} to {high}" if high is not None else (f"above {low}" if low_open else f"of {low} or more")
        raise ValueError(f"[maintenance] {key} must be {kind} {span}, got {value!r}")
    return int(value) if whole else float(value)


def store_path(name: str, root: Path | None = None) -> Path:
    if name not in STORES:
        raise ValueError(f"unknown store {name!r}; expected one of {STORES}")
    return (root if root is not None else paths.data_root()) / f"{name}.db"


def blob_path(sha256: str, root: Path | None = None) -> Path:
    """`<data root>/blobs/aa/bb/<sha256>`: snapshots are named by their content hash."""
    if not re.fullmatch(r"[0-9a-f]{64}", sha256):
        raise ValueError(f"not a SHA-256 hex digest: {sha256!r}")
    base = root if root is not None else paths.data_root()
    return base / "blobs" / sha256[:2] / sha256[2:4] / sha256


def open_store(name: str, root: Path | None = None) -> sqlite3.Connection:
    """Open a store, creating and migrating it. Rows come back as sqlite3.Row.

    With no `root` the real data root is used, and then on macOS it must be on an encrypted volume (require_encryption).
    The connection is in autocommit mode: write inside `transaction(conn)`.
    """
    if root is None:
        require_encryption()
    path = store_path(name, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, isolation_level=None, timeout=BUSY_TIMEOUT_MS / 1000)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(f"PRAGMA synchronous={SYNCHRONOUS[name]}")
        conn.execute("PRAGMA secure_delete=ON")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
        migrate(conn, name)
    except BaseException:
        conn.close()
        raise
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """BEGIN IMMEDIATE ... COMMIT, or ROLLBACK on any error. One writer at a time; no nesting."""
    if conn.in_transaction:
        raise RuntimeError("already in a transaction")
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
        conn.execute("COMMIT")  # deferred foreign keys are checked here, and a failure leaves the transaction open
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise


# --- migrations ---------------------------------------------------------------------------------------------


def migration_files(name: str) -> list[tuple[int, Path]]:
    """The schema files of a store as (version, path), in order. `<name>.sql` is version 1."""
    found = []
    for path in SCHEMA_DIR.glob(f"{name}*.sql"):
        if path.name == f"{name}.sql":
            found.append((1, path))
        else:
            match = re.fullmatch(re.escape(name) + r"\.(\d+)\.sql", path.name)
            if match:
                found.append((int(match.group(1)), path))
    found.sort()
    versions = [v for v, _ in found]
    if versions != list(range(1, len(versions) + 1)):
        raise RuntimeError(f"schema files for {name} must be versions 1..n without gaps, found {versions}")
    return found


def statements(script: str) -> Iterator[str]:
    """Split a SQL script into complete statements (trigger bodies stay whole)."""
    buffer = ""
    for line in script.splitlines(keepends=True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            if buffer.strip():
                yield buffer
            buffer = ""
    leftover = [line for line in buffer.splitlines() if line.strip() and not line.strip().startswith("--")]
    if leftover:
        raise ValueError(f"incomplete SQL statement: {leftover[0][:80]!r}")


_VERSION_TABLE = """CREATE TABLE IF NOT EXISTS schema_version (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  store TEXT NOT NULL,
  version INTEGER NOT NULL,
  applied_at TEXT NOT NULL,
  PRIMARY KEY (store, version))"""


def current_version(conn: sqlite3.Connection, name: str) -> int:
    exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_version'").fetchone()
    if not exists:
        return 0
    row = conn.execute("SELECT MAX(version) FROM schema_version WHERE store=?", (name,)).fetchone()
    return row[0] or 0


def migrate(conn: sqlite3.Connection, name: str) -> list[int]:
    """Apply each schema file that is not recorded yet, each in one transaction. Returns the versions applied."""
    conn.execute(_VERSION_TABLE)
    applied = []
    for version, path in migration_files(name):
        with transaction(conn):
            done = conn.execute("SELECT 1 FROM schema_version WHERE store=? AND version=?", (name, version)).fetchone()
            if done:
                continue
            for statement in statements(path.read_text(encoding="utf-8")):
                conn.execute(statement)
            conn.execute(
                "INSERT INTO schema_version (store, version, applied_at) VALUES (?, ?, ?)", (name, version, utc_now())
            )
            applied.append(version)
    return applied


# --- row history --------------------------------------------------------------------------------------------


def archive_row(conn: sqlite3.Connection, table: str, row_id: str, seq_to: int) -> bool:
    """Copy the current row of `table` into `<table>_history`, closed at `seq_to` (§2.3 row history).

    Call it before changing or deleting a current-state row. The current row's `seq_from` is the event seq at
    which that state began, and it becomes the history row's `seq_from`. Returns False if there is no such row.
    Call inside the writer's transaction.
    """
    row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (row_id,)).fetchone()
    if row is None:
        return False
    snapshot = {key: row[key] for key in row.keys()}
    columns = {r["name"] for r in conn.execute(f"PRAGMA table_info({table}_history)")}
    values: dict[str, Any] = {
        "tenant_id": row["tenant_id"],
        "id": row_id,
        "seq_from": row["seq_from"],
        "seq_to": seq_to,
        "snapshot": json.dumps(snapshot, ensure_ascii=False, sort_keys=True),
    }
    if "version" in columns and "version" in snapshot:
        values["version"] = snapshot["version"]
    names = ", ".join(values)
    marks = ", ".join("?" for _ in values)
    conn.execute(f"INSERT INTO {table}_history ({names}) VALUES ({marks})", tuple(values.values()))
    return True
