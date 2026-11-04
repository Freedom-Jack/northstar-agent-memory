"""Replay: rebuild memory.db's current state from the event log alone, and compare (MEMORY-ARCHITECTURE §3.1, I18).

`rebuild` reads every event of a memory.db in seq order, appends it to a fresh database and projects it, so the fresh
database holds only what the event log can explain. `canonical_hash` reduces the current-state tables to one hash
(each table's rows sorted by id, its columns in schema order, tenant included). `verify_replay` rebuilds and compares
the live hash with the rebuilt one, and lists which rows differ. The weekly replay of §3.1 calls it; a mismatch means
a full rebuild of the derived stores and a look at the cause.

The row history tables are compared too: they are part of memory, and they replay the same way.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from urllib.parse import quote
from dataclasses import dataclass, field
from pathlib import Path

from northstar_agent_memory.core import db
from northstar_agent_memory.core.events import EventEnvelope
from northstar_agent_memory.core.projector import Projector, dump
from northstar_agent_memory.core.reader import HISTORY_TABLES, event_from_row

CURRENT_STATE_TABLES = HISTORY_TABLES + ("stance",)
HISTORY_STATE_TABLES = tuple(f"{t}_history" for t in HISTORY_TABLES)
MAX_DIFFERENCES = 50


def append_event(conn: sqlite3.Connection, envelope: EventEnvelope, *, tenant_id: str = db.DEFAULT_TENANT) -> int:
    """Append a stamped event and its subject rows to memory.db's event log. Returns its seq.

    With `envelope.seq` set (a replay) the event keeps that seq; with None the next seq is assigned and written
    back to the envelope. Call inside a transaction. The projector is called separately.
    """
    values = dict(
        tenant_id=tenant_id, seq=envelope.seq, id=envelope.id, type=envelope.type, schema_version=envelope.schema_version,
        subjects=json.dumps(envelope.subjects, ensure_ascii=False), payload=dump(envelope.payload), actor=envelope.actor,
        run_id=envelope.run_id, proposal_id=envelope.proposal_id, index_in_proposal=envelope.index_in_proposal,
        inputs=json.dumps(envelope.inputs, ensure_ascii=False), compensates=envelope.compensates,
        config_version=envelope.config_version, recorded_at=envelope.recorded_at,
    )  # fmt: skip
    if values["seq"] is None:
        del values["seq"]
    cursor = conn.execute(
        f"INSERT INTO event ({', '.join(values)}) VALUES ({', '.join('?' for _ in values)})", tuple(values.values())
    )
    seq = envelope.seq if envelope.seq is not None else cursor.lastrowid
    conn.executemany(
        "INSERT OR IGNORE INTO event_subject (tenant_id, subject_id, seq) VALUES (?, ?, ?)",
        [(tenant_id, subject, seq) for subject in envelope.subjects],
    )
    envelope.seq = seq
    return seq


def _query(conn: sqlite3.Connection, sql: str, args: tuple = ()) -> sqlite3.Cursor:
    """Run a read on any connection and get rows by column name, whatever the connection's own row factory."""
    cursor = conn.cursor()
    cursor.row_factory = sqlite3.Row
    return cursor.execute(sql, args)


def scratch_store(path: Path | str = ":memory:") -> sqlite3.Connection:
    """An empty, migrated memory.db: in memory by default, or at `path`. Rows come back as sqlite3.Row."""
    conn = sqlite3.connect(path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    db.migrate(conn, "memory")
    return conn


def rebuild_from(
    source: sqlite3.Connection, dest: sqlite3.Connection | None = None, *, tenant_id: str | None = None
) -> sqlite3.Connection:
    """Replay the event log of `source` into `dest` (a fresh in-memory store by default) and return `dest`.

    `dest` must be empty (and use sqlite3.Row rows, as `db.open_store` and `scratch_store` do). Events are appended
    with their own seq, one at a time and in order, then projected in the same transaction. Nothing is read from
    `source` but its event table.
    """
    dest = scratch_store() if dest is None else dest
    if _query(dest, "SELECT 1 FROM event LIMIT 1").fetchone() is not None:
        raise ValueError("a replay needs an empty memory.db")
    if tenant_id is None:
        first = _query(source, "SELECT tenant_id FROM event ORDER BY seq LIMIT 1").fetchone()
        tenant_id = first["tenant_id"] if first is not None else db.DEFAULT_TENANT
    projector = Projector(tenant_id)
    with db.transaction(dest):
        for row in _query(source, "SELECT * FROM event ORDER BY seq"):
            envelope = event_from_row(row)
            append_event(dest, envelope, tenant_id=row["tenant_id"])
            projector.apply(dest, [envelope])
    return dest


def rebuild(memory_db_path: Path | str) -> sqlite3.Connection:
    """A fresh in-memory memory.db rebuilt from the event log of the memory.db at `memory_db_path` (opened read-only)."""
    source = sqlite3.connect(f"file:{quote(Path(memory_db_path).resolve().as_posix())}?mode=ro", uri=True)
    source.row_factory = sqlite3.Row
    try:
        return rebuild_from(source)
    finally:
        source.close()


# --- hashing -------------------------------------------------------------------------------------------------------


def _key(table: str) -> str:
    return "id, seq_from" if table.endswith("_history") else "id"


def table_rows(conn: sqlite3.Connection, table: str) -> tuple[list[str], list[list]]:
    columns = [r["name"] for r in _query(conn, f"PRAGMA table_info({table})")]
    rows = _query(conn, f"SELECT {', '.join(columns)} FROM {table} ORDER BY {_key(table)}").fetchall()
    return columns, [list(r) for r in rows]


def table_hash(conn: sqlite3.Connection, table: str) -> str:
    columns, rows = table_rows(conn, table)
    text = json.dumps([table, columns, rows], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def table_hashes(conn: sqlite3.Connection, *, include_history: bool = False) -> dict[str, str]:
    tables = CURRENT_STATE_TABLES + (HISTORY_STATE_TABLES if include_history else ())
    return {table: table_hash(conn, table) for table in tables}


def canonical_hash(conn: sqlite3.Connection, *, include_history: bool = False) -> str:
    """One SHA-256 over the current-state tables (and, with `include_history`, their row history tables)."""
    parts = table_hashes(conn, include_history=include_history)
    return hashlib.sha256("\n".join(f"{t}:{h}" for t, h in parts.items()).encode("ascii")).hexdigest()


# --- verification --------------------------------------------------------------------------------------------------


@dataclass
class ReplayReport:
    """The result of comparing live memory with a replay of its own event log (I18)."""

    ok: bool
    live_hash: str
    replay_hash: str
    mismatched_tables: list[str] = field(default_factory=list)
    differences: list[str] = field(default_factory=list)  # up to MAX_DIFFERENCES, e.g. "item m3: line differs"


def _by_key(table: str, columns: list[str], rows: list[list]) -> dict[tuple, dict]:
    key = [columns.index(c) for c in _key(table).split(", ")]
    return {tuple(row[i] for i in key): dict(zip(columns, row)) for row in rows}


def _differences(live: sqlite3.Connection, replayed: sqlite3.Connection, table: str) -> list[str]:
    columns, live_rows = table_rows(live, table)
    _, replay_rows = table_rows(replayed, table)
    mine, theirs = _by_key(table, columns, live_rows), _by_key(table, columns, replay_rows)
    out = []
    for key in sorted(set(mine) | set(theirs), key=str):
        label = f"{table} {'/'.join(str(k) for k in key)}"
        if key not in theirs:
            out.append(f"{label}: in memory, not in the replay")
        elif key not in mine:
            out.append(f"{label}: in the replay, not in memory")
        elif mine[key] != theirs[key]:
            names = [c for c in columns if mine[key][c] != theirs[key][c]]
            out.append(f"{label}: {', '.join(names)} {'differs' if len(names) == 1 else 'differ'}")
    return out


def verify_replay(conn: sqlite3.Connection) -> ReplayReport:
    """Rebuild memory from `conn`'s event log and compare it with `conn` (I18): current-state tables and row history."""
    replayed = rebuild_from(conn)
    try:
        live = table_hashes(conn, include_history=True)
        again = table_hashes(replayed, include_history=True)
        mismatched = [t for t in live if live[t] != again[t]]
        differences: list[str] = []
        for table in mismatched:
            differences += _differences(conn, replayed, table)
        return ReplayReport(
            ok=not mismatched,
            live_hash=canonical_hash(conn, include_history=True),
            replay_hash=canonical_hash(replayed, include_history=True),
            mismatched_tables=mismatched,
            differences=differences[:MAX_DIFFERENCES],
        )
    finally:
        replayed.close()
