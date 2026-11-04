"""The history store on SQLite: chat history word for word, never edited (MEMORY-ARCHITECTURE §2.2, §3.1, §3.2).

`SQLiteHistoryStore` implements `ports.HistoryStore` over history.db and the `blobs/` folder. Its writer is capture.

- Text is stored once, exactly as given. `content_hash` is `ids.content_hash` of the text. Replacing secrets before
  writing is the capture layer's job (§2.2, D-6): this store never sees or alters them.
- Speaker, origin, agent and model_family come from the caller, which has the app's own role map. The store never
  infers them (I3) and the schema's triggers never let them change (I20).
- A source is written once. A later `add_source` of the same id changes nothing but may raise its sensitivity (normal,
  sensitive, private; never lower it: a lower or default value keeps the stored one). A different kind or scope is a
  `HistoryConflict`, never ignored: the schema's triggers hold the same line.
- Appends are idempotent: the same message again adds nothing and returns False. A message with the same source,
  branch, ordinal and speaker but other words is refused with `HistoryConflict`, never overwritten (I6).
- `watermark()` is a monotonic counter: the highest `message.seq` and `work_event.seq` ever assigned (AUTOINCREMENT),
  not the highest row present, so a purge never moves it back.
- Snapshots are content-addressed blobs under `db.blob_path`, written once.
- Deleting is possible only for rows a `purge_authorization` row names; the saga of §3.4 that decides what to
  remove is a later part. `authorize_purge` and `purge_authorized` are the history.db half of its port.
- One writer, one thread. Write methods are each one transaction; `batch()` joins several into one.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Iterator, Literal, Sequence

from northstar_agent_memory.core import db
from northstar_agent_memory.core.ids import content_hash, new_id, utc_now
from northstar_agent_memory.core.ports import StoredMessage, Watermark, WorkEvent
from northstar_agent_memory.transcript import Message, Source

DEFAULT_BRANCH = "0"  # Message.branch None is the main line, stored as '0'
SENSITIVITY_RANK = {"normal": 0, "sensitive": 1, "private": 2}  # a source's sensitivity only moves up this list
# Deleted in this order so foreign keys hold: things that point at a row go before it.
_PURGE_ORDER = ("reconciliation", "work_event", "message", "source", "blob")
_KEY = {"blob": "sha256"}  # a table's id column, where it is not `id`


class HistoryConflict(ValueError):
    """A record was appended again with different content. History is never overwritten."""


def _json(meta: dict) -> str:
    return json.dumps(meta, ensure_ascii=False, sort_keys=True)


def _message_from_row(row: sqlite3.Row) -> Message:
    return Message(
        id=row["id"],
        source_id=row["source_id"],
        ordinal=row["ordinal"],
        speaker=row["speaker"],
        text=row["text"],
        occurred_at=row["occurred_at"],
        origin=row["origin"],
        agent=row["agent"],
        model_family=row["model_family"],
        branch=None if row["branch"] == DEFAULT_BRANCH else row["branch"],
        meta=json.loads(row["meta"]),
    )


def _stored(row: sqlite3.Row) -> StoredMessage:
    return StoredMessage(_message_from_row(row), row["seq"], row["fidelity"], row["content_hash"])


class SQLiteHistoryStore:
    """history.db and blobs/ under `root` (the data root when None)."""

    def __init__(self, root: Path | None = None, *, tenant_id: str = db.DEFAULT_TENANT) -> None:
        self.root = root
        self.tenant_id = tenant_id
        self.conn = db.open_store("history", root)

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "SQLiteHistoryStore":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # --- transactions ----------------------------------------------------------------------------------------

    @contextmanager
    def _write(self) -> Iterator[sqlite3.Connection]:
        """One transaction, or a savepoint in the open `batch()`: a call that fails undoes its own rows even when the
        caller catches the error and keeps the batch going."""
        if self.conn.in_transaction:
            self.conn.execute("SAVEPOINT history_call")
            try:
                yield self.conn
            except BaseException:
                self.conn.execute("ROLLBACK TO history_call")
                self.conn.execute("RELEASE history_call")
                raise
            self.conn.execute("RELEASE history_call")
        else:
            with db.transaction(self.conn) as conn:
                yield conn

    @contextmanager
    def batch(self) -> Iterator[None]:
        """Everything written inside commits together, or not at all (many sources in one transaction)."""
        with db.transaction(self.conn):
            yield

    def _exists(self, table: str, key: str) -> bool:
        column = _KEY.get(table, "id")
        return self.conn.execute(f"SELECT 1 FROM {table} WHERE {column} = ?", (key,)).fetchone() is not None

    # --- sources and messages --------------------------------------------------------------------------------

    def add_source(self, source: Source, *, scope: str, sensitivity: str = "normal", account: str | None = None) -> bool:
        """Store a source's own fields, not its messages. The first write wins: False if the id exists.

        `scope` is personal, project:<id>, work:<org> or session:<id>; the data model gives a harness Source none,
        so capture supplies it. For a source that exists, a different kind or scope raises `HistoryConflict`; a higher
        sensitivity is stored, a lower one is ignored (it never goes down); nothing else changes.
        """
        if sensitivity not in SENSITIVITY_RANK:
            raise ValueError(f"sensitivity must be one of {tuple(SENSITIVITY_RANK)}, not {sensitivity!r}")
        with self._write() as conn:
            stored = conn.execute("SELECT kind, scope, sensitivity FROM source WHERE id = ?", (source.id,)).fetchone()
            if stored is not None:
                if (stored["kind"], stored["scope"]) != (source.kind, scope):
                    raise HistoryConflict(
                        f"source {source.id!r} is stored as {stored['kind']} in {stored['scope']}; it cannot become"
                        f" {source.kind} in {scope}"
                    )
                if SENSITIVITY_RANK[sensitivity] > SENSITIVITY_RANK[stored["sensitivity"]]:
                    conn.execute("UPDATE source SET sensitivity = ? WHERE id = ?", (sensitivity, source.id))
                return False
            conn.execute(
                "INSERT INTO source (tenant_id, id, kind, app, account, project, title, started_at, scope, sensitivity,"
                " meta, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (self.tenant_id, source.id, source.kind, source.app, account, source.project, source.title,
                 source.started_at, scope, sensitivity, _json(source.meta), utc_now()),
            )
            return True

    append_source = add_source

    def append_message(self, message: Message, *, fidelity: str = "verbatim") -> bool:
        """Append one turn word for word. False if it is already stored; `HistoryConflict` if the same place holds
        other words (or another speaker, origin, agent or model family). Its source must exist."""
        with self._write() as conn:
            return self._append_message(conn, message, fidelity)

    def append_messages(self, messages: Iterable[Message], *, fidelity: str = "verbatim") -> int:
        """Append several messages in one transaction and return how many were new. One conflict refuses all."""
        with self._write() as conn:
            return sum(self._append_message(conn, m, fidelity) for m in messages)

    def _append_message(self, conn: sqlite3.Connection, m: Message, fidelity: str) -> bool:
        branch = m.branch if m.branch is not None else DEFAULT_BRANCH
        wanted = (m.source_id, branch, m.ordinal, m.speaker, m.text, m.origin, m.agent, m.model_family)
        by_id = conn.execute("SELECT * FROM message WHERE id = ?", (m.id,)).fetchone()
        found = by_id or conn.execute(
            "SELECT * FROM message WHERE source_id = ? AND branch = ? AND ordinal = ? AND speaker = ?",
            (m.source_id, branch, m.ordinal, m.speaker),
        ).fetchone()
        if found is not None:
            have = tuple(found[k] for k in ("source_id", "branch", "ordinal", "speaker", "text", "origin", "agent", "model_family"))
            if have != wanted:
                raise HistoryConflict(
                    f"message {m.id!r} (source {m.source_id!r}, ordinal {m.ordinal}) is already stored with other content"
                )
            return False
        if not self._exists("source", m.source_id):
            raise ValueError(f"unknown source {m.source_id!r}: add the source before its messages")
        conn.execute(
            "INSERT INTO message (tenant_id, id, source_id, branch, ordinal, speaker, agent, model_family, origin,"
            " occurred_at, text, content_hash, fidelity, meta, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (self.tenant_id, m.id, m.source_id, branch, m.ordinal, m.speaker, m.agent, m.model_family, m.origin,
             m.occurred_at, m.text, content_hash(m.text), fidelity, _json(m.meta), utc_now()),
        )
        return True

    def add_source_from_transcript(
        self,
        source: Source,
        *,
        scope: str,
        sensitivity: str = "normal",
        account: str | None = None,
        fidelity: str = "verbatim",
    ) -> tuple[bool, int]:
        """Store a harness Source and its Messages as they are, in one transaction. Returns (source added, new messages).

        Speaker, origin, agent and model_family are taken from the messages as capture set them; nothing is inferred.
        """
        with self._write() as conn:
            added = self.add_source(source, scope=scope, sensitivity=sensitivity, account=account)
            new = sum(self._append_message(conn, m, fidelity) for m in source.messages)
            return added, new

    # --- work events and blobs -------------------------------------------------------------------------------

    def append_work_event(self, event: WorkEvent) -> bool:
        """Append a work event. False if the id exists with the same content; `HistoryConflict` if it differs."""
        with self._write() as conn:
            row = conn.execute("SELECT * FROM work_event WHERE id = ?", (event.id,)).fetchone()
            if row is not None:
                if (row["source_id"], row["kind"], row["ref"], row["evidence"]) != (
                    event.source_id, event.kind, event.ref, event.evidence
                ):
                    raise HistoryConflict(f"work event {event.id!r} is already stored with other content")
                return False
            if not self._exists("source", event.source_id):
                raise ValueError(f"unknown source {event.source_id!r}: add the source before its work events")
            if event.snapshot_sha256 is not None and not self._exists("blob", event.snapshot_sha256):
                raise ValueError(f"unknown snapshot {event.snapshot_sha256!r}: put_blob it first")
            conn.execute(
                "INSERT INTO work_event (tenant_id, id, source_id, kind, ref, evidence, snapshot_sha256, occurred_at,"
                " meta, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (self.tenant_id, event.id, event.source_id, event.kind, event.ref, event.evidence,
                 event.snapshot_sha256, event.occurred_at, _json(event.meta), utc_now()),
            )
            return True

    def put_blob(self, data: bytes, media_type: str | None = None) -> str:
        """Store a snapshot named by its SHA-256 and return the hash. The same bytes are stored once."""
        sha = hashlib.sha256(data).hexdigest()
        path = db.blob_path(sha, self.root)
        with self._write() as conn:
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp = path.with_name(f"{sha}.{os.getpid()}.tmp")
                fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                with os.fdopen(fd, "wb") as fh:
                    fh.write(data)
                    fh.flush()
                    os.fsync(fh.fileno())
                os.replace(tmp, path)
            conn.execute(
                "INSERT INTO blob (tenant_id, sha256, size, media_type, created_at) VALUES (?, ?, ?, ?, ?)"
                " ON CONFLICT DO NOTHING",
                (self.tenant_id, sha, len(data), media_type, utc_now()),
            )
        return sha

    def get_blob(self, sha256: str) -> bytes | None:
        """The stored bytes, or None. A file whose bytes no longer match its name is an error, not data."""
        if not self._exists("blob", sha256):
            return None
        path = db.blob_path(sha256, self.root)
        try:
            data = path.read_bytes()
        except FileNotFoundError:
            return None
        if hashlib.sha256(data).hexdigest() != sha256:
            raise ValueError(f"blob {sha256} is corrupt: its bytes do not match its hash")
        return data

    def record_reconciliation(
        self,
        reported_message_id: str,
        verbatim_message_id: str | None,
        method: Literal["hash", "tag", "fuzzy", "none"],
        score: float | None,
        outcome: Literal["matched", "reported_only", "could_not_confirm"],
    ) -> str:
        """Record one outcome of matching a model-reported turn to word-for-word text (§2.2) and return its id."""
        with self._write() as conn:
            for message_id in (reported_message_id, verbatim_message_id):
                if message_id is not None and not self._exists("message", message_id):
                    raise ValueError(f"unknown message {message_id!r}")
            rid = new_id()
            conn.execute(
                "INSERT INTO reconciliation (tenant_id, id, reported_message_id, verbatim_message_id, method, score,"
                " outcome, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (self.tenant_id, rid, reported_message_id, verbatim_message_id, method, score, outcome, utc_now()),
            )
            return rid

    # --- reading ---------------------------------------------------------------------------------------------

    def get_source(self, source_id: str) -> Source | None:
        """The source with its messages in (branch, ordinal) order."""
        row = self.conn.execute("SELECT * FROM source WHERE id = ?", (source_id,)).fetchone()
        if row is None:
            return None
        return Source(
            id=row["id"],
            kind=row["kind"],
            app=row["app"],
            project=row["project"],
            title=row["title"],
            started_at=row["started_at"],
            messages=[s.message for s in self.messages_for_source(source_id)],
            meta=json.loads(row["meta"]),
        )

    def get_source_info(self, source_id: str) -> dict | None:
        """A source's stored row without its messages (kind, scope, project, app, sensitivity, ...), or None. The write
        gate reads kind and scope from it (I3, I24); it is the same row `HistoryRead` reads from the connection."""
        row = self.conn.execute("SELECT * FROM source WHERE id = ? AND tenant_id = ?", (source_id, self.tenant_id)).fetchone()
        if row is None:
            return None
        info = {key: row[key] for key in row.keys()}
        info["meta"] = json.loads(info["meta"])
        return info

    def get_message(self, message_id: str) -> StoredMessage | None:
        row = self.conn.execute("SELECT * FROM message WHERE id = ?", (message_id,)).fetchone()
        return _stored(row) if row else None

    def messages_for_source(self, source_id: str) -> list[StoredMessage]:
        """A source's messages in (branch, ordinal) order."""
        rows = self.conn.execute(
            "SELECT * FROM message WHERE source_id = ? ORDER BY branch, ordinal, seq", (source_id,)
        ).fetchall()
        return [_stored(r) for r in rows]

    def messages_since(self, seq: int | Watermark, limit: int = 1000) -> list[StoredMessage]:
        """Messages with `seq` above the given one (or a Watermark's message_seq), in seq order."""
        after = seq.message_seq if isinstance(seq, Watermark) else seq
        rows = self.conn.execute("SELECT * FROM message WHERE seq > ? ORDER BY seq LIMIT ?", (after, limit)).fetchall()
        return [_stored(r) for r in rows]

    def watermark(self) -> Watermark:
        """The last `message.seq` and `work_event.seq` ever assigned (0 when none). Monotonic: a purge never lowers it."""
        seqs = {r["name"]: r["seq"] for r in self.conn.execute("SELECT name, seq FROM sqlite_sequence")}
        return Watermark(seqs.get("message", 0), seqs.get("work_event", 0))

    # --- purge (the history.db half; the saga of §3.4 is a later part) ----------------------------------------

    def authorize_purge(self, purge_id: str, targets: Sequence[tuple[str, str]]) -> None:
        """Record (target table, target id) pairs a purge will remove, before removing anything. A blob's id is its hash."""
        with self._write() as conn:
            conn.executemany(
                "INSERT INTO purge_authorization (tenant_id, purge_id, target_table, target_id, authorized_at)"
                " VALUES (?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
                [(self.tenant_id, purge_id, table, key, utc_now()) for table, key in targets],
            )

    def purge_authorized(self, purge_id: str) -> int:
        """Delete every row this purge authorized, then its blob files. Returns the number of rows deleted.

        A row still pointed at by one that is not authorized (a message with a reconciliation, a blob a work event
        keeps) makes the whole call fail and delete nothing.
        """
        deleted = 0
        files: list[Path] = []
        if self.conn.in_transaction:
            raise RuntimeError("purge_authorized cannot run inside batch(): files would go before the rows are committed")
        with self._write() as conn:
            for table in _PURGE_ORDER:
                column = _KEY.get(table, "id")
                keys = [
                    r["target_id"]
                    for r in conn.execute(
                        "SELECT target_id FROM purge_authorization WHERE purge_id = ? AND target_table = ?",
                        (purge_id, table),
                    )
                ]
                for key in keys:
                    deleted += conn.execute(f"DELETE FROM {table} WHERE {column} = ?", (key,)).rowcount
                    if table == "blob":
                        files.append(db.blob_path(key, self.root))
        for path in files:
            path.unlink(missing_ok=True)
        return deleted
