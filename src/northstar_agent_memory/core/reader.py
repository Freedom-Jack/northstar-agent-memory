"""Read-only views of memory.db: by ID, as of a seq or a time, changed since, subgraph, events (MEMORY-ARCHITECTURE §2.3, §3.2).

`SQLiteMemoryReader` implements `ports.MemoryReader` over one connection to memory.db. Reading never changes the store.

- Rows come back as dicts keyed by column name, with each value as stored: JSON columns such as `contexts_seen` are
  still JSON text, and booleans are 0 or 1. A row from row history has the same shape as a current row.
- "As of seq N" is the state after every event with seq <= N: the current row if its `seq_from` is at most N, else
  the history row with `seq_from <= N < seq_to` (§2.3 row history). A row that did not exist yet, or was removed
  by then, is None.
- "As of a time" is the highest seq recorded at or before that time. `recorded_at` is stored as `ids.utc_now()` writes
  it (UTC, milliseconds), so times are compared as normalized text. A date with no time means the end of that day.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timezone
from typing import Sequence

from northstar_agent_memory.core.events import EventEnvelope
from northstar_agent_memory.core.ports import Row, Subgraph

# Tables that keep row history, and the kinds `get` knows (stance and event have no history).
HISTORY_TABLES = (
    "item", "evidence", "link", "supersession", "conflict", "work", "style_line", "correction", "scope", "topic",
    "placement",
)  # fmt: skip
KINDS = HISTORY_TABLES + ("stance",)
_CHUNK = 500


def normalize_time(value: str) -> str:
    """An ISO 8601 time as `YYYY-MM-DDTHH:MM:SS.mmmZ` in UTC; a bare date is the end of that day."""
    text = value.strip()
    if len(text) == 10:
        day = date.fromisoformat(text)
        moment = datetime(day.year, day.month, day.day, 23, 59, 59, 999000, tzinfo=timezone.utc)
    else:
        moment = datetime.fromisoformat(text)
        moment = moment.replace(tzinfo=timezone.utc) if moment.tzinfo is None else moment.astimezone(timezone.utc)
    return moment.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def row_as_of(conn: sqlite3.Connection, table: str, row_id: str, seq: int | None = None) -> Row | None:
    """A row of a history-keeping table as it stood after event `seq` (the current row when `seq` is None)."""
    if table == "stance":
        row = conn.execute("SELECT * FROM stance WHERE id = ?", (row_id,)).fetchone()
        return dict(row) if row is not None and (seq is None or row["created_seq"] <= seq) else None
    if table not in HISTORY_TABLES:
        raise ValueError(f"unknown kind {table!r}; expected one of {KINDS}")
    current = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (row_id,)).fetchone()
    if current is not None and (seq is None or current["seq_from"] <= seq):
        return dict(current)
    if seq is None:
        return None
    old = conn.execute(
        f"SELECT snapshot FROM {table}_history WHERE id = ? AND seq_from <= ? AND ? < seq_to", (row_id, seq, seq)
    ).fetchone()
    return json.loads(old["snapshot"]) if old is not None else None


def event_from_row(row: sqlite3.Row) -> EventEnvelope:
    return EventEnvelope(
        type=row["type"],
        payload=json.loads(row["payload"]),
        actor=row["actor"],
        config_version=row["config_version"],
        subjects=json.loads(row["subjects"]),
        id=row["id"],
        schema_version=row["schema_version"],
        run_id=row["run_id"],
        proposal_id=row["proposal_id"],
        index_in_proposal=row["index_in_proposal"],
        inputs=json.loads(row["inputs"]),
        compensates=row["compensates"],
        recorded_at=row["recorded_at"],
        seq=row["seq"],
    )


def _marks(n: int) -> str:
    return ", ".join("?" for _ in range(n))


class SQLiteMemoryReader:
    """`ports.MemoryReader` on a connection to memory.db."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    # --- seq and time ---------------------------------------------------------------------------------------

    def watermark(self) -> int:
        row = self.conn.execute(
            "SELECT COALESCE((SELECT seq FROM sqlite_sequence WHERE name = 'event'), (SELECT MAX(seq) FROM event), 0)"
        ).fetchone()
        return row[0] or 0

    def seq_at(self, as_of: str) -> int:
        row = self.conn.execute("SELECT MAX(seq) FROM event WHERE recorded_at <= ?", (normalize_time(as_of),)).fetchone()
        return row[0] or 0

    def _resolve(self, as_of_seq: int | None, as_of: str | int | None) -> int | None:
        if as_of_seq is not None and as_of is not None:
            raise ValueError("give as_of_seq or as_of, not both")
        if as_of_seq is not None:
            return as_of_seq
        if as_of is None:
            return None
        return as_of if isinstance(as_of, int) else self.seq_at(as_of)

    # --- rows -----------------------------------------------------------------------------------------------

    def get(self, kind: str, row_id: str, as_of: int | str | None = None) -> Row | None:
        """One row of any kind (item, evidence, link, supersession, conflict, work, style_line, correction, scope,
        topic, placement, stance), now or as of a seq (int) or an ISO time (str)."""
        return row_as_of(self.conn, kind, row_id, self._resolve(None, as_of))

    def get_item(self, item_id: str, *, as_of_seq: int | None = None, as_of: str | None = None) -> Row | None:
        return row_as_of(self.conn, "item", item_id, self._resolve(as_of_seq, as_of))

    def _stored_versions(self, item_id: str) -> dict[int, Row]:
        """Every version of an item, each as its last stored state (a version can be stored more than once)."""
        found: dict[int, tuple[int, Row]] = {}
        for old in self.conn.execute("SELECT snapshot FROM item_history WHERE id = ?", (item_id,)):
            state = json.loads(old["snapshot"])
            if state["version"] not in found or found[state["version"]][0] < state["seq_from"]:
                found[state["version"]] = (state["seq_from"], state)
        current = self.conn.execute("SELECT * FROM item WHERE id = ?", (item_id,)).fetchone()
        if current is not None:
            found[current["version"]] = (current["seq_from"], dict(current))
        return {version: state for version, (_, state) in found.items()}

    def get_item_version(self, item_id: str, version: int) -> Row | None:
        return self._stored_versions(item_id).get(version)

    def item_versions(self, item_id: str) -> list[Row]:
        stored = self._stored_versions(item_id)
        return [stored[v] for v in sorted(stored)]

    def evidence_for(self, subject_id: str) -> list[Row]:
        rows = self.conn.execute(
            "SELECT * FROM evidence WHERE subject_id = ? ORDER BY created_seq, id", (subject_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    # --- events ---------------------------------------------------------------------------------------------

    def events_since(self, seq: int, limit: int = 1000, types: Sequence[str] | None = None) -> list[EventEnvelope]:
        sql, args = "SELECT * FROM event WHERE seq > ?", [seq]
        if types:
            sql += f" AND type IN ({_marks(len(types))})"
            args += list(types)
        rows = self.conn.execute(sql + " ORDER BY seq LIMIT ?", (*args, limit)).fetchall()
        return [event_from_row(r) for r in rows]

    def get_event(self, event_id: str) -> EventEnvelope | None:
        row = self.conn.execute("SELECT * FROM event WHERE id = ?", (event_id,)).fetchone()
        return event_from_row(row) if row is not None else None

    # --- changed since --------------------------------------------------------------------------------------

    def _any_row(self, table: str, row_id: str) -> Row | None:
        """The current row, or else its last stored state (a removed row still names the items it joined)."""
        current = self.conn.execute(f"SELECT * FROM {table} WHERE id = ?", (row_id,)).fetchone()
        if current is not None:
            return dict(current)
        old = self.conn.execute(
            f"SELECT snapshot FROM {table}_history WHERE id = ? ORDER BY seq_from DESC LIMIT 1", (row_id,)
        ).fetchone()
        return json.loads(old["snapshot"]) if old is not None else None

    def _items_of(self, subject_id: str) -> list[str]:
        """The items an event subject stands for: an item itself, or the items a link, conflict, supersession,
        evidence, correction or placement joins."""
        if self._any_row("item", subject_id) is not None:
            return [subject_id]
        link = self._any_row("link", subject_id)
        if link is not None:
            return [link["from_id"]] + ([link["to_id"]] if link["to_kind"] == "item" else [])
        conflict = self._any_row("conflict", subject_id)
        if conflict is not None:
            return [conflict["side_a_item"], conflict["side_b_item"]]
        supersession = self._any_row("supersession", subject_id)
        if supersession is not None:
            return [supersession["old_item"], supersession["new_item"]]
        evidence = self._any_row("evidence", subject_id)
        if evidence is not None:
            return [evidence["subject_id"]] if evidence["subject_kind"] == "item" else []
        correction = self._any_row("correction", subject_id)
        if correction is not None:
            return [correction["target"]] if self._any_row("item", correction["target"]) is not None else []
        placement = self._any_row("placement", subject_id)
        if placement is not None:
            return [placement["item_id"]]
        return []

    def changed_since(self, seq: int) -> list[str]:
        """Ids of items touched by events after `seq`, oldest touch first: items named as event subjects, and items
        that links, conflicts, supersessions, evidence, corrections and placements named there join. A compensation
        batch touches what the events it undid touched."""
        last: dict[str, int] = {}
        subjects = self.conn.execute(
            "SELECT subject_id, MAX(seq) AS seq FROM event_subject WHERE seq > ? GROUP BY subject_id", (seq,)
        ).fetchall()
        for row in subjects:
            last[row["subject_id"]] = row["seq"]
        batches = self.conn.execute("SELECT seq, payload FROM event WHERE seq > ? AND type = 'compensation.batch'", (seq,))
        for batch in batches.fetchall():
            for event_id in json.loads(batch["payload"]).get("compensated_event_ids", []):
                rows = self.conn.execute(
                    "SELECT s.subject_id FROM event_subject s JOIN event e ON e.seq = s.seq WHERE e.id = ?", (event_id,)
                )
                for row in rows.fetchall():
                    last[row["subject_id"]] = max(last.get(row["subject_id"], 0), batch["seq"])
        touched: dict[str, int] = {}
        for subject_id, at in last.items():
            for item_id in self._items_of(subject_id):
                touched[item_id] = max(touched.get(item_id, 0), at)
        return [item_id for item_id, _ in sorted(touched.items(), key=lambda kv: (kv[1], kv[0]))]

    # --- subgraph -------------------------------------------------------------------------------------------

    def subgraph(
        self, item_ids: Sequence[str], depth: int = 1, *, statuses: Sequence[str] = ("applied", "confirmed")
    ) -> Subgraph:
        """The items, and links of the given statuses between them, up to `depth` steps out along links. A link to a
        piece of work (used_in) is included and its work end is not followed."""
        statuses = tuple(statuses)
        items: dict[str, Row] = {}
        frontier: list[str] = []
        for item_id in item_ids:
            row = self.conn.execute("SELECT * FROM item WHERE id = ?", (item_id,)).fetchone()
            if row is not None and item_id not in items:
                items[item_id] = dict(row)
                frontier.append(item_id)
        status_marks = _marks(len(statuses))
        for _ in range(max(depth, 0)):
            step: list[str] = []
            for item_id in sorted(frontier):
                found = self.conn.execute(
                    f"SELECT from_id, to_id, to_kind FROM link WHERE status IN ({status_marks}) AND to_kind = 'item'"
                    " AND (from_id = ? OR to_id = ?)",
                    (*statuses, item_id, item_id),
                ).fetchall()
                for link in found:
                    other = link["to_id"] if link["from_id"] == item_id else link["from_id"]
                    if other in items:
                        continue
                    row = self.conn.execute("SELECT * FROM item WHERE id = ?", (other,)).fetchone()
                    if row is not None:
                        items[other] = dict(row)
                        step.append(other)
            frontier = step
            if not frontier:
                break
        links: list[Row] = []
        ids = sorted(items)
        for start in range(0, len(ids), _CHUNK):
            chunk = ids[start : start + _CHUNK]
            rows = self.conn.execute(
                f"SELECT * FROM link WHERE status IN ({status_marks}) AND from_id IN ({_marks(len(chunk))})",
                (*statuses, *chunk),
            ).fetchall()
            links += [dict(r) for r in rows if r["to_kind"] == "work" or r["to_id"] in items]
        links.sort(key=lambda r: r["id"])
        return Subgraph(items=items, links=links)
