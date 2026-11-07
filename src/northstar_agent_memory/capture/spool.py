"""The spool: what the hooks write and the ingester reads (connectors-claude-code-and-codex.md §4.2, MEMORY-ARCHITECTURE §5.2).

The hooks never write the database (one writer: ingest.py). Each hook appends one line to a spool file, fsyncs, and
exits.

- Layout: <data root>/spool/claude-code/<UTC date>.jsonl, one file per day, owner-only (0700 folder, 0600 files).
  Lines are never changed or removed by a hook; the ingester deletes a file only once it is fully ingested and old.
- A record is one JSON line: a ULID `id`, `event`, `session_id`, `transcript_path`, `cwd`, `occurred_at` (local time
  with offset) and `recorded_at` (UTC), `scrub` (which scrubber ran: "secrets", or "noop" in tests only), and the
  scrubbed `payload`. Secrets are replaced before the line is built (MEMORY-ARCHITECTURE §2.2).
- The reader keeps a watermark per spool file (<file>.mark: the byte offset just after the last line handled) and
  returns only complete lines past it. A torn last line (a hook killed mid-write) is left alone until it is finished;
  if a later append follows it, the append starts on a new line, so the torn line becomes one invalid line that the
  reader skips and counts, and no good record is lost.
- Locks are advisory file locks (flock), so a crashed process never leaves one behind.
- A marker record (`make_marker`) holds no text: only the event, the session, the transcript path and the sizes of what
  the hook was about to scrub. It is written before the scrubbing starts, so a hook that is ended mid-scrub (the
  watchdog, or Claude Code's own timeout) still leaves the turn known, and reconciliation can recover it from the
  transcript. It rides under the event's own name with no text in its payload, so the ingester reads it as a record
  that makes no message and still learns the session and its transcript from it.
- Everything is created owner-only: the folders (every one made here, parents included) 0700, the files 0600.
- The encryption stamp (<data root>/capture/encryption.stamp) is what `capture install` writes once the data root is on
  an encrypted volume (PL-3); the hook writes nothing without a valid one.

This module also holds the capture log (<data root>/capture/capture.log): one line per error or notable event,
never the text of a turn, and never an error out of the logger itself.

Standard library and paths.py only: the hook imports this on every event. The ULID is made here, not by core/ids.py,
because importing the core package costs about a tenth of a second.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from northstar_agent_memory import paths

CONNECTOR = "claude-code"
VERSION = 1
LOG_LIMIT_BYTES = 1_000_000
DONE_KEEP_S = 48 * 3600  # a fully ingested spool file is kept this long, then deleted (§4.2)

_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # Crockford base32, as core/ids.py

try:  # POSIX
    import fcntl
except ImportError:  # Windows: not run on a machine yet
    fcntl = None  # type: ignore[assignment]


# --- places ----------------------------------------------------------------------------------------------------


def _root(root: Path | None) -> Path:
    return paths.data_root() if root is None else root


def spool_dir(root: Path | None = None, connector: str = CONNECTOR) -> Path:
    return _root(root) / "spool" / connector


def capture_dir(root: Path | None = None) -> Path:
    return _root(root) / "capture"


def log_path(root: Path | None = None) -> Path:
    return capture_dir(root) / "capture.log"


def lock_path(root: Path | None = None) -> Path:
    return capture_dir(root) / "ingest.lock"


def state_path(root: Path | None = None) -> Path:
    return capture_dir(root) / "state.json"


def stamp_path(root: Path | None = None) -> Path:
    return capture_dir(root) / "encryption.stamp"


def make_private_dirs(folder: Path) -> None:
    """Make `folder` and every missing parent above it, each owner-only (0700). `os.makedirs(mode=0o700)` applies the
    mode to the last folder only: the parents it makes get the default (0755), which left <data root>/spool open to
    other users of the machine. A folder that already exists is left as it is."""
    missing: list[Path] = []
    probe = folder
    while not probe.exists() and probe != probe.parent:
        missing.append(probe)
        probe = probe.parent
    for path in reversed(missing):
        try:
            os.mkdir(path, 0o700)
            os.chmod(path, 0o700)  # the umask can only remove bits, but the mode is not left to it
        except FileExistsError:  # another hook made it first
            pass


# --- ids and times ---------------------------------------------------------------------------------------------


def new_ulid(now_ms: int | None = None) -> str:
    """A ULID: 48 bits of milliseconds, 80 random bits, 26 Crockford base32 characters (same form as core/ids.py)."""
    ms = time.time_ns() // 1_000_000 if now_ms is None else now_ms
    value = (ms << 80) | int.from_bytes(os.urandom(10), "big")
    chars = []
    for _ in range(26):
        chars.append(_ALPHABET[value & 31])
        value >>= 5
    return "".join(reversed(chars))


def utc_stamp(now: float | None = None) -> str:
    when = datetime.fromtimestamp(time.time() if now is None else now, timezone.utc)
    return when.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def local_stamp(now: float | None = None) -> str:
    """Local time with its offset, e.g. 2026-03-02T09:30:00.123+01:00 (a message's occurred_at)."""
    return datetime.fromtimestamp(time.time() if now is None else now).astimezone().isoformat(timespec="milliseconds")


# --- locks -----------------------------------------------------------------------------------------------------


def _lock_fd(fd: int, blocking: bool) -> bool:
    if fcntl is not None:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        except BlockingIOError:
            return False
        return True
    import msvcrt  # Windows; untested

    try:
        msvcrt.locking(fd, msvcrt.LK_LOCK if blocking else msvcrt.LK_NBLCK, 1)
    except OSError:
        return False
    return True


def try_lock(path: Path) -> int | None:
    """Take an exclusive lock on `path` (made if missing) without waiting. The open descriptor, or None when it is
    held. The lock lasts until `unlock(fd)` or the process ends."""
    make_private_dirs(path.parent)
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    if _lock_fd(fd, blocking=False):
        return fd
    os.close(fd)
    return None


def unlock(fd: int) -> None:
    os.close(fd)  # closing releases the lock


def lock_held(path: Path) -> bool:
    """Whether another process holds the lock now (a probe: it takes the lock and lets go at once)."""
    if not path.exists():
        return False
    fd = try_lock(path)
    if fd is None:
        return True
    unlock(fd)
    return False


# --- writing ---------------------------------------------------------------------------------------------------


def make_record(
    event: str,
    session_id: str,
    payload: dict[str, Any],
    *,
    transcript_path: str | None = None,
    cwd: str | None = None,
    scrub: str = "secrets",
    now: float | None = None,
) -> dict[str, Any]:
    """One spool record. `payload` must already be scrubbed."""
    return {
        "v": VERSION,
        "id": new_ulid(None if now is None else int(now * 1000)),
        "event": event,
        "session_id": session_id,
        "transcript_path": transcript_path,
        "cwd": cwd,
        "occurred_at": local_stamp(now),
        "recorded_at": utc_stamp(now),
        "scrub": scrub,
        "payload": payload,
    }


MARKER_SCRUB = "marker"  # the `scrub` of a record that holds no text: there was nothing to scrub
MARKER_KEY = "marker"  # in a marker's payload: what it stands for


def make_marker(
    event: str,
    session_id: str,
    sizes: dict[str, int],
    *,
    transcript_path: str | None = None,
    cwd: str | None = None,
    now: float | None = None,
) -> dict[str, Any]:
    """A text-free record for a turn whose text is about to be scrubbed: the event's own name, the session, the
    transcript path, and `sizes` (characters by field, and bytes in all). Nothing of the turn is in it."""
    record = make_record(
        event, session_id, {MARKER_KEY: "scrub_pending", "sizes": dict(sizes)},
        transcript_path=transcript_path, cwd=cwd, scrub=MARKER_SCRUB, now=now,
    )
    return record


def is_marker(record: "SpoolRecord | dict[str, Any]") -> bool:
    payload = record.payload if isinstance(record, SpoolRecord) else record.get("payload")
    return isinstance(payload, dict) and payload.get(MARKER_KEY) == "scrub_pending"


def _write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    while view:
        view = view[os.write(fd, view) :]


def append(record: dict[str, Any], *, root: Path | None = None, connector: str = CONNECTOR, sync: bool = True) -> Path:
    """Append one record to today's file and fsync (unless `sync` is False: the bytes are then in the system's cache,
    which survives the process being killed but not a power cut). Returns the file.

    One write call under an exclusive lock, so concurrent hooks never interleave. If the file does not end in a newline
    (an earlier writer died mid-line), the new line starts on a fresh one.
    """
    folder = spool_dir(root, connector)
    make_private_dirs(folder)
    path = folder / f"{str(record['recorded_at'])[:10]}.jsonl"
    line = json.dumps(record, ensure_ascii=True, separators=(",", ":")).encode("ascii") + b"\n"
    fd = os.open(path, os.O_RDWR | os.O_APPEND | os.O_CREAT, 0o600)  # read-write: it looks at the last byte
    try:
        _lock_fd(fd, blocking=True)
        size = os.fstat(fd).st_size
        if size and os.pread(fd, 1, size - 1) != b"\n":
            line = b"\n" + line
        _write_all(fd, line)
        if sync:
            os.fsync(fd)
    finally:
        os.close(fd)
    return path


# --- reading ---------------------------------------------------------------------------------------------------


@dataclass(slots=True)
class SpoolRecord:
    id: str
    event: str
    session_id: str
    transcript_path: str | None
    cwd: str | None
    occurred_at: str | None
    recorded_at: str
    scrub: str | None
    payload: dict[str, Any]
    file: str = ""  # the spool file's name
    end: int = 0  # the byte offset just after this record's line
    raw: dict[str, Any] = field(default_factory=dict, repr=False)


def spool_files(root: Path | None = None, connector: str = CONNECTOR) -> list[Path]:
    folder = spool_dir(root, connector)
    return sorted(folder.glob("*.jsonl")) if folder.is_dir() else []


def _mark(path: Path) -> Path:
    return path.with_name(path.name + ".mark")


def watermark(path: Path) -> int:
    """The byte offset past the last line of this spool file that was handled (0 if none, or if the mark is unreadable)."""
    try:
        return max(int(_mark(path).read_text(encoding="ascii").strip()), 0)
    except (OSError, ValueError):
        return 0


def set_watermark(path: Path, offset: int) -> None:
    mark = _mark(path)
    tmp = mark.with_name(mark.name + f".{os.getpid()}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        _write_all(fd, str(offset).encode("ascii"))
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(tmp, mark)


def _parse(line: bytes) -> dict[str, Any] | None:
    try:
        obj = json.loads(line)
    except ValueError:
        return None
    needed = ("id", "event", "session_id", "recorded_at", "payload")
    if not isinstance(obj, dict) or any(k not in obj for k in needed) or not isinstance(obj["payload"], dict):
        return None
    if not all(isinstance(obj[k], str) and obj[k] for k in ("id", "event", "session_id", "recorded_at")):
        return None
    return obj


def read_file(path: Path, start: int | None = None) -> tuple[list[SpoolRecord], int, int]:
    """(records, end, corrupt): the valid records from `start` (the watermark by default) on, the offset just after the
    last complete line read, and how many complete lines were not valid records. A last line with no newline is
    left out: it is not complete."""
    offset = watermark(path) if start is None else start
    try:
        with path.open("rb") as fh:
            fh.seek(offset)
            data = fh.read()
    except FileNotFoundError:
        return [], offset, 0
    records: list[SpoolRecord] = []
    corrupt = 0
    pos = offset
    while True:
        nl = data.find(b"\n", pos - offset)
        if nl < 0:
            break
        line = data[pos - offset : nl]
        pos = offset + nl + 1
        if not line.strip():
            continue
        obj = _parse(line)
        if obj is None:
            corrupt += 1
            continue
        records.append(
            SpoolRecord(
                id=obj["id"], event=obj["event"], session_id=obj["session_id"],
                transcript_path=obj.get("transcript_path") if isinstance(obj.get("transcript_path"), str) else None,
                cwd=obj.get("cwd") if isinstance(obj.get("cwd"), str) else None,
                occurred_at=obj.get("occurred_at") if isinstance(obj.get("occurred_at"), str) else None,
                recorded_at=obj["recorded_at"], scrub=obj.get("scrub") if isinstance(obj.get("scrub"), str) else None,
                payload=obj["payload"], file=path.name, end=pos, raw=obj,
            )
        )
    return records, pos, corrupt


def has_pending(root: Path | None = None, connector: str = CONNECTOR) -> bool:
    """Whether any spool file has bytes past its watermark (a torn last line counts until it is finished or skipped)."""
    for path in spool_files(root, connector):
        try:
            if path.stat().st_size > watermark(path):
                return True
        except OSError:
            continue
    return False


def read_pending(root: Path | None = None, connector: str = CONNECTOR) -> list[SpoolRecord]:
    """Every record not yet ingested, oldest file first, in file order."""
    out: list[SpoolRecord] = []
    for path in spool_files(root, connector):
        out.extend(read_file(path)[0])
    return out


def prune(root: Path | None = None, connector: str = CONNECTOR, *, keep_s: float = DONE_KEEP_S, now: float | None = None) -> int:
    """Delete spool files that are fully ingested and older than `keep_s`. Returns how many."""
    now = time.time() if now is None else now
    removed = 0
    for path in spool_files(root, connector):
        try:
            done = path.stat().st_size <= watermark(path)
            old = now - path.stat().st_mtime > keep_s
            if done and old:
                path.unlink()
                _mark(path).unlink(missing_ok=True)
                removed += 1
        except OSError:
            continue
    return removed


# --- the encryption stamp ----------------------------------------------------------------------------------------

STAMP_VERSION = 1


def _stamp_facts(root: Path) -> tuple[str, int]:
    """What a stamp is tied to: where the data root really is, and which volume (device) it is on."""
    real = os.path.realpath(root)
    return real, os.stat(real).st_dev


def write_encryption_stamp(root: Path | None = None, *, now: float | None = None) -> Path:
    """Record that the data root was found to be on an encrypted volume (PL-3). `capture install` calls this after the
    core's `require_encryption` passed; the stamp is tied to the data root's real path and its volume, so a data root
    that is moved to another disk needs a new check. Owner-only (0600)."""
    base = _root(root)
    make_private_dirs(base)
    real, device = _stamp_facts(base)
    stamp = {
        "v": STAMP_VERSION, "checked_at": utc_stamp(now), "data_root": real, "device": device,
        "checked_by": "core.db.require_encryption",
    }
    path = stamp_path(root)
    make_private_dirs(path.parent)
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        _write_all(fd, (json.dumps(stamp, indent=2) + "\n").encode("ascii"))
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(tmp, path)
    return path


def encryption_stamp(root: Path | None = None) -> tuple[bool, str]:
    """(valid, why): whether the data root carries a valid encryption stamp, and in a few words what is wrong if not.
    Reads two small things and makes no model, database or subprocess call: the hook asks this on every event."""
    path = stamp_path(root)
    try:
        data = json.loads(path.read_text(encoding="ascii"))
    except FileNotFoundError:
        return False, "no encryption stamp: run `northstar capture install` to check that the data folder is encrypted"
    except (OSError, ValueError):
        return False, f"the encryption stamp {path} cannot be read: run `northstar capture install` again"
    if not isinstance(data, dict) or data.get("v") != STAMP_VERSION:
        return False, "the encryption stamp is not in a form this version knows: run `northstar capture install` again"
    try:
        real, device = _stamp_facts(_root(root))
    except OSError as err:
        return False, f"the data root cannot be examined ({type(err).__name__})"
    if data.get("data_root") != real:
        return False, "the encryption stamp is for another data folder: run `northstar capture install` again"
    if data.get("device") != device:
        return False, "the data folder is on another volume than when it was checked: run `northstar capture install` again"
    return True, f"checked {data.get('checked_at', 'at an unknown time')}"


# --- scrubbing -------------------------------------------------------------------------------------------------


def in_test_run(env: dict[str, str] | None = None) -> bool:
    """A test run: NORTHSTAR_TEST_MODE (as core/db.py) is set, or pytest is running."""
    env = os.environ if env is None else env
    return env.get("NORTHSTAR_TEST_MODE", "") not in ("", "0") or "PYTEST_CURRENT_TEST" in env


def load_scrubber() -> tuple[Callable[[str], str], str] | None:
    """(function, name) for replacing secrets in a string: capture/secrets.py's `scrub`, imported when first needed.

    If that module cannot be imported, a test run gets a no-op named "noop" (the hook says so in each record);
    anything else gets None, and the caller writes nothing: no turn is ever written unscrubbed.
    """
    try:
        import importlib

        scrub = importlib.import_module("northstar_agent_memory.capture.secrets").scrub

        def run(text: str) -> str:
            result = scrub(text)
            return result[0] if isinstance(result, tuple) else result

        return run, "secrets"
    except Exception:  # missing or broken module
        if in_test_run():
            return (lambda text: text), "noop"
        return None


def scrub_value(value: Any, fn: Callable[[str], str]) -> Any:
    """`value` with `fn` applied to every string in it, however deep."""
    if isinstance(value, str):
        return fn(value)
    if isinstance(value, dict):
        return {k: scrub_value(v, fn) for k, v in value.items()}
    if isinstance(value, list):
        return [scrub_value(v, fn) for v in value]
    return value


# --- the capture log -------------------------------------------------------------------------------------------


def log(who: str, message: str, *, level: str = "error", root: Path | None = None) -> None:
    """Append one line to the capture log. It holds no turn text. Never raises: a broken log must not break a hook."""
    try:
        path = log_path(root)
        make_private_dirs(path.parent)
        if path.exists() and path.stat().st_size > LOG_LIMIT_BYTES:
            os.replace(path, path.with_name(path.name + ".1"))
        line = f"{utc_stamp()} {level} {who} pid={os.getpid()} " + " ".join(str(message).split())[:400] + "\n"
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            _write_all(fd, line.encode("utf-8", "replace"))
        finally:
            os.close(fd)
    except Exception:
        pass
