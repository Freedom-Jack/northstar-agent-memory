"""working.db: working memory, the live record of each piece of work in progress (MEMORY-ARCHITECTURE §2.9, §3.2).

`SQLiteWorkingStore` implements the WorkingStore port: work threads, sessions, live decisions, versions with your
feedback, side topics and receipts. Its writer is the live writer.

Working memory is never a source for memory (§2.9, §5.2). Maintenance extracts from chat history only, so a wrong
live note cannot become long-term memory. This store therefore has no method that returns working-memory text as
evidence: no `EvidenceQuote`, no evidence rows, nothing shaped for the write gate. Its rows serve delivery, the echo
guard and "where you left off" only, and a receipt keeps a hash and fingerprints of what Northstar delivered, not
the text.

Your words only: a goal, a live decision and a piece of feedback each carry a quote and the id of one of your own
turns. A record without that id is refused. If the store is given `is_user_turn` (a lookup into history.db), the id
must also name a turn of yours.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from typing import Any, Callable, Iterable, Literal, Sequence

from northstar_agent_memory.core.db import DEFAULT_TENANT, open_store, transaction
from northstar_agent_memory.core.ids import new_id, normalize_text, utc_now

THREAD_STATUSES = ("active", "paused", "closed")
GOAL_BASES = ("stated", "reused")
ARTIFACT_KINDS = ("git_ref", "render", "file")
DECISION_KINDS = ("decided", "ruled_out", "constraint")
DECISION_STATUSES = ("live", "in_memory", "dropped")
SIDE_TOPIC_STATUSES = ("open", "split_off", "closed")
RECEIPT_KINDS = ("start_note", "facts", "refill", "focus_note", "recall")

FINGERPRINT_WORDS = 8  # §2.5, I11
ECHO_OVERLAP = 0.6  # §2.5, I11

_WORD = re.compile(r"\w+")
_ITEM_AT_VERSION = re.compile(r"^[^@\s]+@\d+$")
_JSON_COLUMNS = ("items", "fingerprints")


class UserWordsRequired(ValueError):
    """A goal, decision or feedback without your own quote and the id of your own turn."""


# --- fingerprints for the echo guard (§2.5, I11) -------------------------------------------------------------------


def fingerprints(text: str, size: int = FINGERPRINT_WORDS) -> list[str]:
    """Hashes of every run of `size` consecutive words of `text`, in order and without repeats.

    Words are lower-cased runs of letters and digits, so spacing, case and punctuation do not matter. A text of fewer
    than `size` words gets one fingerprint of all its words. Only the hashes are kept in a receipt, never the text.
    """
    words = _WORD.findall(normalize_text(text).casefold())
    if not words:
        return []
    found: dict[str, None] = {}
    for start in range(max(1, len(words) - size + 1)):
        digest = hashlib.sha256(" ".join(words[start : start + size]).encode("utf-8")).hexdigest()[:16]
        found[digest] = None
    return list(found)


def echo_overlap(text: str, delivered: Iterable[str]) -> float:
    """The share of `text`'s fingerprints that appear among the delivered fingerprints, from 0.0 to 1.0.

    A quote whose overlap reaches ECHO_OVERLAP is Northstar repeating itself, not new evidence (I11). A quote of
    fewer than 8 words cannot be caught this way: the receipt's item list and text hash cover that case.
    """
    own = set(fingerprints(text))
    if not own:
        return 0.0
    return len(own & set(delivered)) / len(own)


def is_echo(text: str, delivered: Iterable[str], threshold: float = ECHO_OVERLAP) -> bool:
    return echo_overlap(text, delivered) >= threshold


# --- helpers -------------------------------------------------------------------------------------------------------


def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    out = dict(row)
    for key in _JSON_COLUMNS:
        if key in out:
            out[key] = json.loads(out[key])
    return out


def _choice(value: str, allowed: Sequence[str], name: str) -> str:
    if value not in allowed:
        raise ValueError(f"{name} must be one of {allowed}, got {value!r}")
    return value


class SQLiteWorkingStore:
    """The WorkingStore port on working.db. One writer; reads never change the store."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        tenant_id: str = DEFAULT_TENANT,
        *,
        is_user_turn: Callable[[str], bool] | None = None,
    ) -> None:
        self.conn = conn
        self.tenant_id = tenant_id
        self.is_user_turn = is_user_turn

    @classmethod
    def open(cls, root=None, tenant_id: str = DEFAULT_TENANT, **kwargs) -> "SQLiteWorkingStore":
        return cls(open_store("working", root), tenant_id, **kwargs)

    def close(self) -> None:
        self.conn.close()

    # --- internals ---

    def _one(self, table: str, id_: str) -> dict[str, Any] | None:
        return _row(self.conn.execute(f"SELECT * FROM {table} WHERE id = ? AND tenant_id = ?", (id_, self.tenant_id)).fetchone())

    def _need(self, table: str, id_: str) -> dict[str, Any]:
        row = self._one(table, id_)
        if row is None:
            raise KeyError(f"no {table} with id {id_!r}")
        return row

    def _your_words(self, quote: str | None, message_id: str | None, what: str) -> None:
        if not quote or not quote.strip():
            raise UserWordsRequired(f"{what} needs your own words as a quote")
        if not message_id:
            raise UserWordsRequired(f"{what} needs the id of your own turn: without it the record is refused")
        if self.is_user_turn is not None and not self.is_user_turn(message_id):
            raise UserWordsRequired(f"{what}: message {message_id!r} is not one of your own turns")

    # --- work threads ---

    def open_thread(
        self,
        title: str,
        *,
        scope: str,
        project: str | None = None,
        goal_text: str | None = None,
        goal_message_id: str | None = None,
        goal_basis: Literal["stated", "reused"] | None = None,
        thread_id: str | None = None,
    ) -> str:
        """Create an active thread and return its id. A goal is your words and needs the id of your turn."""
        if not title.strip():
            raise ValueError("a thread needs a title")
        if goal_text is None:
            if goal_message_id is not None or goal_basis is not None:
                raise ValueError("goal_message_id and goal_basis need goal_text")
        else:
            self._your_words(goal_text, goal_message_id, "a goal")
            goal_basis = _choice(goal_basis or "stated", GOAL_BASES, "goal_basis")  # type: ignore[assignment]
        tid, now = thread_id or new_id(), utc_now()
        with transaction(self.conn):
            self.conn.execute(
                "INSERT INTO work_thread (tenant_id, id, title, project, scope, status, goal_text, goal_message_id,"
                " goal_basis, opened_at, last_active) VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?, ?, ?)",
                (self.tenant_id, tid, title, project, scope, goal_text, goal_message_id, goal_basis, now, now),
            )
        return tid

    def set_goal(
        self, thread_id: str, goal_text: str, message_id: str, basis: Literal["stated", "reused"] = "stated"
    ) -> None:
        """Set or replace the goal, in your words, with the id of your turn."""
        self._your_words(goal_text, message_id, "a goal")
        _choice(basis, GOAL_BASES, "basis")
        self._need("work_thread", thread_id)
        with transaction(self.conn):
            self.conn.execute(
                "UPDATE work_thread SET goal_text = ?, goal_message_id = ?, goal_basis = ? WHERE id = ? AND tenant_id = ?",
                (goal_text, message_id, basis, thread_id, self.tenant_id),
            )

    def get_thread(self, thread_id: str) -> dict[str, Any] | None:
        return self._one("work_thread", thread_id)

    def threads(self, *, project: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
        """Threads, most recently active first."""
        sql, args = "SELECT * FROM work_thread WHERE tenant_id = ?", [self.tenant_id]
        if project is not None:
            sql, args = sql + " AND project = ?", args + [project]
        if status is not None:
            sql, args = sql + " AND status = ?", args + [_choice(status, THREAD_STATUSES, "status")]
        rows = self.conn.execute(sql + " ORDER BY last_active DESC, id DESC", args).fetchall()
        return [_row(r) for r in rows]  # type: ignore[misc]

    def set_thread_status(self, thread_id: str, status: Literal["active", "paused", "closed"]) -> None:
        _choice(status, THREAD_STATUSES, "status")
        self._need("work_thread", thread_id)
        with transaction(self.conn):
            self.conn.execute(
                "UPDATE work_thread SET status = ? WHERE id = ? AND tenant_id = ?", (status, thread_id, self.tenant_id)
            )

    def pause_thread(self, thread_id: str) -> None:
        self.set_thread_status(thread_id, "paused")

    def close_thread(self, thread_id: str) -> None:
        self.set_thread_status(thread_id, "closed")

    def resume_thread(self, thread_id: str, at: str | None = None) -> None:
        """Make a paused or closed thread active again and mark it active now."""
        self._need("work_thread", thread_id)
        with transaction(self.conn):  # one step: a thread is never active with an old last_active
            self.conn.execute(
                "UPDATE work_thread SET status = 'active', last_active = ? WHERE id = ? AND tenant_id = ?",
                (at or utc_now(), thread_id, self.tenant_id),
            )

    def touch_thread(self, thread_id: str, at: str) -> None:
        """Set last_active."""
        self._need("work_thread", thread_id)
        with transaction(self.conn):
            self.conn.execute(
                "UPDATE work_thread SET last_active = ? WHERE id = ? AND tenant_id = ?", (at, thread_id, self.tenant_id)
            )

    # --- sessions ---

    def start_session(
        self, session_id: str, *, app: str | None, project: str | None, thread_id: str | None = None, started_at: str
    ) -> None:
        """Record a session. One that exists already is left as it is, so capture can see it again."""
        if thread_id is not None:
            self._need("work_thread", thread_id)
        with transaction(self.conn):
            self.conn.execute(
                "INSERT OR IGNORE INTO session (tenant_id, id, app, project, thread_id, started_at, last_active)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (self.tenant_id, session_id, app, project, thread_id, started_at, started_at),
            )

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        return self._one("session", session_id)

    def sessions(self, thread_id: str) -> list[dict[str, Any]]:
        """The sessions of a thread, oldest first."""
        rows = self.conn.execute(
            "SELECT * FROM session WHERE thread_id = ? AND tenant_id = ? ORDER BY started_at, id", (thread_id, self.tenant_id)
        ).fetchall()
        return [_row(r) for r in rows]  # type: ignore[misc]

    def touch_session(self, session_id: str, at: str) -> None:
        """Set a session's last_active (`start_session` leaves an existing session as it is)."""
        self._need("session", session_id)
        with transaction(self.conn):
            self.conn.execute(
                "UPDATE session SET last_active = ? WHERE id = ? AND tenant_id = ?", (at, session_id, self.tenant_id)
            )

    def attach_session(self, session_id: str, thread_id: str) -> None:
        self._need("session", session_id)
        self._need("work_thread", thread_id)
        with transaction(self.conn):
            self.conn.execute(
                "UPDATE session SET thread_id = ? WHERE id = ? AND tenant_id = ?", (thread_id, session_id, self.tenant_id)
            )

    def set_context_used(self, session_id: str, tokens: int) -> None:
        """The token count from the app's transcript."""
        if isinstance(tokens, bool) or not isinstance(tokens, int) or tokens < 0:
            raise ValueError(f"context_used must be a count of tokens, got {tokens!r}")
        self._need("session", session_id)
        with transaction(self.conn):
            self.conn.execute(
                "UPDATE session SET context_used = ? WHERE id = ? AND tenant_id = ?", (tokens, session_id, self.tenant_id)
            )

    # --- versions ---

    def record_version(
        self,
        thread_id: str,
        artifact: str,
        *,
        artifact_kind: Literal["git_ref", "render", "file"] = "git_ref",
        parent_id: str | None = None,
        made_at_turn: int | None = None,
    ) -> str:
        """Record a version of the work and return its id. The parent must be a version of the same thread."""
        if not artifact:
            raise ValueError("a version needs its artifact: a hidden git ref, a render's sha256 or a file")
        _choice(artifact_kind, ARTIFACT_KINDS, "artifact_kind")
        self._need("work_thread", thread_id)
        if parent_id is not None and self._need("version", parent_id)["thread_id"] != thread_id:
            raise ValueError("the parent version belongs to another thread")
        if made_at_turn is not None and (isinstance(made_at_turn, bool) or made_at_turn < 0):
            raise ValueError("made_at_turn must be zero or more")
        vid = new_id()
        with transaction(self.conn):
            self.conn.execute(
                "INSERT INTO version (tenant_id, id, thread_id, artifact, artifact_kind, parent_id, made_at_turn, best,"
                " created_at) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)",
                (self.tenant_id, vid, thread_id, artifact, artifact_kind, parent_id, made_at_turn, utc_now()),
            )
        return vid

    def add_feedback(self, version_id: str, your_quote: str, message_id: str) -> str:
        """Attach your next message to a version as feedback."""
        self._your_words(your_quote, message_id, "feedback")
        self._need("version", version_id)
        fid = new_id()
        with transaction(self.conn):
            self.conn.execute(
                "INSERT INTO version_feedback (tenant_id, id, version_id, your_quote, message_id, at) VALUES (?, ?, ?, ?, ?, ?)",
                (self.tenant_id, fid, version_id, your_quote, message_id, utc_now()),
            )
        return fid

    def set_best(self, thread_id: str, version_id: str) -> None:
        """Make this the thread's one best version (your pick, or your last approval in your own words)."""
        if self._need("version", version_id)["thread_id"] != thread_id:
            raise ValueError("that version belongs to another thread")
        with transaction(self.conn):
            self.conn.execute(
                "UPDATE version SET best = 0 WHERE thread_id = ? AND tenant_id = ? AND best = 1", (thread_id, self.tenant_id)
            )
            self.conn.execute("UPDATE version SET best = 1 WHERE id = ? AND tenant_id = ?", (version_id, self.tenant_id))

    def _with_feedback(self, version: dict[str, Any]) -> dict[str, Any]:
        rows = self.conn.execute(
            "SELECT your_quote, message_id FROM version_feedback WHERE version_id = ? AND tenant_id = ? ORDER BY at, id",
            (version["id"], self.tenant_id),
        ).fetchall()
        version["feedback"] = [dict(r) for r in rows]
        return version

    def versions(self, thread_id: str) -> list[dict[str, Any]]:
        """Versions oldest first, each with a `feedback` list of {your_quote, message_id}."""
        rows = self.conn.execute(
            "SELECT * FROM version WHERE thread_id = ? AND tenant_id = ? ORDER BY created_at, id", (thread_id, self.tenant_id)
        ).fetchall()
        return [self._with_feedback(_row(r)) for r in rows]  # type: ignore[arg-type]

    def best_version(self, thread_id: str) -> dict[str, Any] | None:
        row = _row(
            self.conn.execute(
                "SELECT * FROM version WHERE thread_id = ? AND tenant_id = ? AND best = 1", (thread_id, self.tenant_id)
            ).fetchone()
        )
        return None if row is None else self._with_feedback(row)

    # --- live decisions ---

    def add_live_decision(
        self,
        thread_id: str,
        kind: Literal["decided", "ruled_out", "constraint"],
        line: str,
        your_quote: str,
        message_id: str,
    ) -> str:
        """Note a decision from one of your own turns. Without the id of your turn the record is refused."""
        _choice(kind, DECISION_KINDS, "kind")
        if not line.strip():
            raise ValueError("a decision needs a line")
        self._your_words(your_quote, message_id, "a live decision")
        self._need("work_thread", thread_id)
        did = new_id()
        with transaction(self.conn):
            self.conn.execute(
                "INSERT INTO live_decision (tenant_id, id, thread_id, kind, line, your_quote, message_id, status, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, 'live', ?)",
                (self.tenant_id, did, thread_id, kind, line, your_quote, message_id, utc_now()),
            )
        return did

    def live_decisions(self, thread_id: str, status: str | None = "live") -> list[dict[str, Any]]:
        """Decisions of a thread in the order they were noted; `status=None` returns every status."""
        sql, args = "SELECT * FROM live_decision WHERE thread_id = ? AND tenant_id = ?", [thread_id, self.tenant_id]
        if status is not None:
            sql, args = sql + " AND status = ?", args + [_choice(status, DECISION_STATUSES, "status")]
        return [_row(r) for r in self.conn.execute(sql + " ORDER BY created_at, id", args).fetchall()]  # type: ignore[misc]

    def set_decision_status(self, decision_id: str, status: Literal["live", "in_memory", "dropped"]) -> None:
        _choice(status, DECISION_STATUSES, "status")
        self._need("live_decision", decision_id)
        with transaction(self.conn):
            self.conn.execute(
                "UPDATE live_decision SET status = ? WHERE id = ? AND tenant_id = ?", (status, decision_id, self.tenant_id)
            )

    # --- side topics ---

    def add_side_topic(self, thread_id: str, line: str, opened_at_message: str | None = None) -> str:
        if not line.strip():
            raise ValueError("a side topic needs a line")
        self._need("work_thread", thread_id)
        sid = new_id()
        with transaction(self.conn):
            self.conn.execute(
                "INSERT INTO side_topic (tenant_id, id, thread_id, line, opened_at_message, status) VALUES (?, ?, ?, ?, ?, 'open')",
                (self.tenant_id, sid, thread_id, line, opened_at_message),
            )
        return sid

    def set_side_topic_status(self, side_topic_id: str, status: Literal["open", "split_off", "closed"]) -> None:
        _choice(status, SIDE_TOPIC_STATUSES, "status")
        self._need("side_topic", side_topic_id)
        with transaction(self.conn):
            self.conn.execute(
                "UPDATE side_topic SET status = ? WHERE id = ? AND tenant_id = ?", (status, side_topic_id, self.tenant_id)
            )

    def side_topics(self, thread_id: str, status: str | None = "open") -> list[dict[str, Any]]:
        sql, args = "SELECT * FROM side_topic WHERE thread_id = ? AND tenant_id = ?", [thread_id, self.tenant_id]
        if status is not None:
            sql, args = sql + " AND status = ?", args + [_choice(status, SIDE_TOPIC_STATUSES, "status")]
        return [_row(r) for r in self.conn.execute(sql + " ORDER BY id", args).fetchall()]  # type: ignore[misc]

    # --- receipts ---

    def record_receipt(
        self,
        session_id: str,
        kind: Literal["start_note", "facts", "refill", "focus_note", "recall"],
        items: Sequence[str],
        text_hash: str,
        fingerprints: Sequence[str],
        at: str | None = None,
    ) -> str:
        """Note what Northstar gave an AI: `item@version` strings, the text's hash and its 8-word fingerprints.

        The delivered text itself is not stored. Make the hash with `ids.content_hash` and the fingerprints with
        this module's `fingerprints`.
        """
        _choice(kind, RECEIPT_KINDS, "kind")
        for item in items:
            if not _ITEM_AT_VERSION.match(item):
                raise ValueError(f"receipt items are item@version strings, got {item!r}")
        if not text_hash:
            raise ValueError("a receipt needs the hash of the delivered text")
        self._need("session", session_id)
        rid = new_id()
        with transaction(self.conn):
            self.conn.execute(
                "INSERT INTO receipt (tenant_id, id, session_id, at, kind, items, text_hash, fingerprints)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    self.tenant_id, rid, session_id, at or utc_now(), kind,
                    json.dumps(list(items)), text_hash, json.dumps(list(fingerprints)),
                ),
            )
        return rid

    def receipts(self, session_id: str | None = None, *, since: str | None = None) -> list[dict[str, Any]]:
        """Receipts oldest first, of one session or all; `since` keeps those at or after that time."""
        sql, args = "SELECT * FROM receipt WHERE tenant_id = ?", [self.tenant_id]
        if session_id is not None:
            sql, args = sql + " AND session_id = ?", args + [session_id]
        if since is not None:
            sql, args = sql + " AND at >= ?", args + [since]
        return [_row(r) for r in self.conn.execute(sql + " ORDER BY at, id", args).fetchall()]  # type: ignore[misc]

    def delivered_fingerprints(self, session_id: str) -> set[str]:
        """Every fingerprint Northstar delivered into one session, for `echo_overlap`."""
        found: set[str] = set()
        for receipt in self.receipts(session_id):
            found.update(receipt["fingerprints"])
        return found
