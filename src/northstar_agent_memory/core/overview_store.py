"""overview.db: the human structure (MEMORY-ARCHITECTURE §2.11, §3.2). A minimal adapter for the OverviewStore port.

`SQLiteOverviewStore` is create, read, update and delete over the tables of overview.sql: topic and idea views,
suggestions, open items, "where you left off", the layout and its marks. It holds what any display needs and decides
nothing about how it looks. The builder that fills it each maintenance run (the full rebuild, the placement of new
topics near their strongest links, the projection checks of §5.10) comes in a later build step.

Most of it is derived. `layout`, `layout_meta`, `mark` and `topic_mark` are your state, so `clear_derived` keeps them.
Your decisions on suggestions are kept too: a link you confirmed or rejected stays decided through a rebuild, so a
link you turned down does not come back as waiting. Memory's link rows are the record of those decisions (the events
`link.confirmed` and `link.rejected`), and a rebuild puts each suggestion back with the status memory shows
(`put_suggestion_from_link`); the rows kept here only carry the status across a clear.
Marks stay on this Mac and are never given to a model (§2.11). I27: a link Northstar found lives in `suggestion`
until you confirm it, and `idea_view.links` is for stated or confirmed links only; the builder keeps that rule.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Mapping, Sequence

from northstar_agent_memory.core.db import DEFAULT_TENANT, open_store, transaction
from northstar_agent_memory.core.ids import new_id, utc_now

SUGGESTION_STATUSES = ("waiting", "confirmed", "rejected")
NODE_KINDS = ("topic", "entry")
OPEN_ITEM_KINDS = ("open_question", "open_conflict", "active_goal", "next_step", "goal_gap")

# What a rebuild replaces. layout, layout_meta, mark and topic_mark are not here: they are state.
# `suggestion` is derived, but its rows you decided (confirmed or rejected) are kept: see `clear_derived`.
DERIVED_TABLES = ("topic_view", "idea_view", "suggestion", "open_item", "left_off")
STATE_TABLES = ("layout", "layout_meta", "mark", "topic_mark")

_JSON_COLUMNS = (
    "entries", "work_cues", "sources", "links", "conflict_pairs", "last_steps", "changed_since", "open_questions",
)
_SUGGESTION_COLUMNS = ("link_id", "from_id", "to_id", "type", "reason")
# What memory's link status means for the overview: a link Northstar found waits for you until you decide (I27).
# 'applied' (checked and stated by construction) and 'retracted' links are not suggestions at all.
LINK_SUGGESTION_STATUS = {"proposed": "waiting", "confirmed": "confirmed", "rejected": "rejected"}


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


def _list(values: Sequence[Any]) -> str:
    return json.dumps(list(values), ensure_ascii=False)


class SQLiteOverviewStore:
    """The OverviewStore port on overview.db. One writer; reads never change the store."""

    def __init__(self, conn: sqlite3.Connection, tenant_id: str = DEFAULT_TENANT) -> None:
        self.conn = conn
        self.tenant_id = tenant_id

    @classmethod
    def open(cls, root=None, tenant_id: str = DEFAULT_TENANT) -> "SQLiteOverviewStore":
        return cls(open_store("overview", root), tenant_id)

    def close(self) -> None:
        self.conn.close()

    def _all(self, sql: str, args: Sequence[Any]) -> list[dict[str, Any]]:
        return [_row(r) for r in self.conn.execute(sql, args).fetchall()]  # type: ignore[misc]

    def _one(self, sql: str, args: Sequence[Any]) -> dict[str, Any] | None:
        return _row(self.conn.execute(sql, args).fetchone())

    # --- topics ---

    def put_topic(
        self,
        topic_id: str,
        label: str,
        *,
        parent_id: str | None = None,
        entries: Sequence[str] = (),
        more_count: int = 0,
        open_count: int = 0,
        changed_since_seen: bool = False,
        status: str = "active",
    ) -> None:
        """Insert or replace a topic view. `entries` are item ids: your pins, then open items, then salience."""
        if not label.strip():
            raise ValueError("a topic needs a label")
        with transaction(self.conn):
            self.conn.execute(
                "INSERT OR REPLACE INTO topic_view (tenant_id, topic_id, label, parent_id, entries, more_count, open_count,"
                " changed_since_seen, status, built_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    self.tenant_id, topic_id, label, parent_id, _list(entries), more_count, open_count,
                    int(changed_since_seen), status, utc_now(),
                ),
            )

    def topics(self, *, parent_id: str | None = None) -> list[dict[str, Any]]:
        """Topic views: the top level when `parent_id` is None, else the sub-topics of that topic. By label."""
        if parent_id is None:
            return self._all("SELECT * FROM topic_view WHERE tenant_id = ? AND parent_id IS NULL ORDER BY label, topic_id", (self.tenant_id,))
        return self._all(
            "SELECT * FROM topic_view WHERE tenant_id = ? AND parent_id = ? ORDER BY label, topic_id", (self.tenant_id, parent_id)
        )

    def topic_view(self, topic_id: str) -> dict[str, Any] | None:
        return self._one("SELECT * FROM topic_view WHERE topic_id = ? AND tenant_id = ?", (topic_id, self.tenant_id))

    def delete_topic(self, topic_id: str) -> None:
        with transaction(self.conn):
            self.conn.execute("DELETE FROM topic_view WHERE topic_id = ? AND tenant_id = ?", (topic_id, self.tenant_id))

    # --- ideas ---

    def put_idea(
        self,
        item_id: str,
        *,
        shown_line: str,
        shown_is_yours: bool,
        origin_mark: str,
        version: int,
        work_cues: Sequence[Any] = (),
        sources: Sequence[Any] = (),
        links: Sequence[Any] = (),
        conflict_pairs: Sequence[Any] = (),
    ) -> None:
        """Insert or replace an idea view. `work_cues` holds one to three cues (§2.11), or none for an idea with no work."""
        if len(work_cues) > 3:
            raise ValueError("an idea shows at most 3 work cues")
        if not shown_line.strip():
            raise ValueError("an idea needs a shown line")
        with transaction(self.conn):
            self.conn.execute(
                "INSERT OR REPLACE INTO idea_view (tenant_id, item_id, shown_line, shown_is_yours, origin_mark, work_cues, sources,"
                " links, conflict_pairs, version, built_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    self.tenant_id, item_id, shown_line, int(shown_is_yours), origin_mark, _list(work_cues), _list(sources),
                    _list(links), _list(conflict_pairs), version, utc_now(),
                ),
            )

    def idea_view(self, item_id: str) -> dict[str, Any] | None:
        return self._one("SELECT * FROM idea_view WHERE item_id = ? AND tenant_id = ?", (item_id, self.tenant_id))

    def delete_idea(self, item_id: str) -> None:
        with transaction(self.conn):
            self.conn.execute("DELETE FROM idea_view WHERE item_id = ? AND tenant_id = ?", (item_id, self.tenant_id))

    # --- suggestions (links Northstar found, waiting for you: I27) ---

    def put_suggestion(self, suggestion: Mapping[str, Any]) -> None:
        """Insert or replace a suggestion, with the columns of `suggestion`. New ones are `waiting`; one put again
        without a status keeps the status you gave it."""
        missing = [c for c in _SUGGESTION_COLUMNS if c not in suggestion]
        if missing:
            raise ValueError(f"suggestion is missing {missing}")
        status = suggestion.get("status")
        if status is not None:
            _choice(status, SUGGESTION_STATUSES, "status")
        with transaction(self.conn):
            if status is None:
                # Put again without a status (a rebuild): what you confirmed or rejected stays decided.
                old = self.conn.execute(
                    "SELECT status, created_at FROM suggestion WHERE link_id = ? AND tenant_id = ?", (suggestion["link_id"], self.tenant_id)
                ).fetchone()
                status = old["status"] if old else "waiting"
                suggestion = {**suggestion, "created_at": suggestion.get("created_at") or (old["created_at"] if old else None)}
            self.conn.execute(
                "INSERT OR REPLACE INTO suggestion (tenant_id, link_id, from_id, to_id, type, reason, status, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    self.tenant_id, *(suggestion[c] for c in _SUGGESTION_COLUMNS), status,
                    suggestion.get("created_at") or utc_now(),
                ),
            )

    def put_suggestion_from_link(self, link: Mapping[str, Any]) -> str | None:
        """Rebuild a suggestion from one of memory's link rows (`id`, `from_id`, `to_id`, `type`, `reason`, `status`,
        `stated_by`) and return its status, or None when the link is not a suggestion.

        Memory is the record of what you decided, so the status comes from the link row: proposed is waiting,
        confirmed and rejected are those. It replaces what this table held, so a decision made in memory since the
        last build shows at once, and a rejection kept through `clear_derived` can never outlive memory's word. Only a
        link Northstar found (`stated_by` 'northstar') is a suggestion; a link that is applied or retracted, or one you
        stated, is not, and any suggestion held for it is removed.
        """
        status = LINK_SUGGESTION_STATUS.get(link["status"]) if link.get("stated_by", "northstar") == "northstar" else None
        link_id = link["id"] if "id" in link else link["link_id"]
        if status is None:
            with transaction(self.conn):
                self.conn.execute("DELETE FROM suggestion WHERE link_id = ? AND tenant_id = ?", (link_id, self.tenant_id))
            return None
        old = self._one("SELECT created_at FROM suggestion WHERE link_id = ? AND tenant_id = ?", (link_id, self.tenant_id))
        self.put_suggestion(
            {
                "link_id": link_id, "from_id": link["from_id"], "to_id": link["to_id"], "type": link["type"],
                "reason": link["reason"], "status": status, "created_at": old["created_at"] if old else None,
            }
        )
        return status

    def suggestions(self, status: str = "waiting") -> list[dict[str, Any]]:
        """Links Northstar found, waiting for your confirmation (I27), oldest first."""
        _choice(status, SUGGESTION_STATUSES, "status")
        return self._all(
            "SELECT * FROM suggestion WHERE status = ? AND tenant_id = ? ORDER BY created_at, link_id", (status, self.tenant_id)
        )

    def set_suggestion_status(self, link_id: str, status: str) -> None:
        _choice(status, SUGGESTION_STATUSES, "status")
        if self._one("SELECT 1 FROM suggestion WHERE link_id = ? AND tenant_id = ?", (link_id, self.tenant_id)) is None:
            raise KeyError(f"no suggestion for link {link_id!r}")
        with transaction(self.conn):
            self.conn.execute("UPDATE suggestion SET status = ? WHERE link_id = ? AND tenant_id = ?", (status, link_id, self.tenant_id))

    # --- open items and where you left off ---

    def put_open_item(
        self,
        kind: str,
        ref_id: str,
        line: str,
        *,
        topic_id: str | None = None,
        since: str | None = None,
        open_item_id: str | None = None,
    ) -> str:
        """Add something to learn and return its id. A term that merely appeared is never a gap; the builder decides."""
        _choice(kind, OPEN_ITEM_KINDS, "kind")
        oid = open_item_id or new_id()
        with transaction(self.conn):
            self.conn.execute(
                "INSERT OR REPLACE INTO open_item (tenant_id, id, kind, ref_id, line, topic_id, since, built_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (self.tenant_id, oid, kind, ref_id, line, topic_id, since, utc_now()),
            )
        return oid

    def open_items(self, *, topic_id: str | None = None) -> list[dict[str, Any]]:
        sql, args = "SELECT * FROM open_item WHERE tenant_id = ?", [self.tenant_id]
        if topic_id is not None:
            sql, args = sql + " AND topic_id = ?", args + [topic_id]
        return self._all(sql + " ORDER BY since, id", args)

    def put_left_off(
        self,
        thread_id: str,
        *,
        last_state: str = "",
        last_steps: Sequence[str] = (),
        changed_since: Sequence[str] = (),
        goal: str | None = None,
        next_step: str | None = None,
        open_questions: Sequence[str] = (),
    ) -> None:
        with transaction(self.conn):
            self.conn.execute(
                "INSERT OR REPLACE INTO left_off (tenant_id, thread_id, last_state, last_steps, changed_since, goal, next_step,"
                " open_questions, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    self.tenant_id, thread_id, last_state, _list(last_steps), _list(changed_since), goal, next_step,
                    _list(open_questions), utc_now(),
                ),
            )

    def left_off(self, thread_id: str) -> dict[str, Any] | None:
        return self._one("SELECT * FROM left_off WHERE thread_id = ? AND tenant_id = ?", (thread_id, self.tenant_id))

    # --- layout ---

    def layout(self) -> list[dict[str, Any]]:
        return self._all("SELECT * FROM layout WHERE tenant_id = ? ORDER BY node_kind, node_id", (self.tenant_id,))

    def layout_meta(self) -> dict[str, Any] | None:
        return self._one("SELECT * FROM layout_meta WHERE tenant_id = ?", (self.tenant_id,))

    def set_layout(self, nodes: Sequence[Mapping[str, Any]], seed: int) -> None:
        """Replace the positions. Each node has `node_id`, `node_kind`, `x`, `y`; its previous position becomes
        `prev_x`, `prev_y`, and a node that is new has none. Nodes left out are dropped. The layout version goes up."""
        for node in nodes:
            _choice(node["node_kind"], NODE_KINDS, "node_kind")
        now = utc_now()
        with transaction(self.conn):
            before = {
                r["node_id"]: (r["x"], r["y"])
                for r in self.conn.execute("SELECT node_id, x, y FROM layout WHERE tenant_id = ?", (self.tenant_id,))
            }
            self.conn.execute("DELETE FROM layout WHERE tenant_id = ?", (self.tenant_id,))
            for node in nodes:
                prev_x, prev_y = before.get(node["node_id"], (None, None))
                self.conn.execute(
                    "INSERT INTO layout (tenant_id, node_id, node_kind, x, y, prev_x, prev_y, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (self.tenant_id, node["node_id"], node["node_kind"], node["x"], node["y"], prev_x, prev_y, now),
                )
            self.conn.execute(
                "INSERT INTO layout_meta (tenant_id, id, seed, version, updated_at) VALUES (?, 1, ?, 1, ?)"
                " ON CONFLICT (tenant_id, id) DO UPDATE SET seed = excluded.seed, version = version + 1, updated_at = excluded.updated_at",
                (self.tenant_id, seed, now),
            )

    # --- marks ---

    def mark_seen(self, item_id: str, version: int, at: str | None = None) -> None:
        """The last version of an idea you saw. A pin is kept."""
        with transaction(self.conn):
            self.conn.execute(
                "INSERT INTO mark (tenant_id, item_id, last_seen_version, seen_at) VALUES (?, ?, ?, ?)"
                " ON CONFLICT (tenant_id, item_id) DO UPDATE SET last_seen_version = excluded.last_seen_version, seen_at = excluded.seen_at",
                (self.tenant_id, item_id, version, at or utc_now()),
            )

    def mark(self, item_id: str) -> dict[str, Any] | None:
        return self._one("SELECT * FROM mark WHERE item_id = ? AND tenant_id = ?", (item_id, self.tenant_id))

    def set_pinned(self, item_id: str, pinned: bool) -> None:
        """Pin or unpin an idea. One you have not seen yet gets a mark with last_seen_version 0."""
        now = utc_now()
        with transaction(self.conn):
            self.conn.execute(
                "INSERT INTO mark (tenant_id, item_id, last_seen_version, seen_at, pinned) VALUES (?, ?, 0, ?, ?)"
                " ON CONFLICT (tenant_id, item_id) DO UPDATE SET pinned = excluded.pinned",
                (self.tenant_id, item_id, now, int(pinned)),
            )

    def pinned(self) -> list[str]:
        rows = self.conn.execute("SELECT item_id FROM mark WHERE tenant_id = ? AND pinned = 1 ORDER BY item_id", (self.tenant_id,))
        return [r["item_id"] for r in rows]

    def record_hidden_open(self, topic_id: str, at: str | None = None) -> None:
        """You opened a topic's hidden entries; this feeds the split bar (§5.8)."""
        with transaction(self.conn):
            self.conn.execute(
                "INSERT INTO topic_mark (tenant_id, topic_id, hidden_opens, last_opened_at) VALUES (?, ?, 1, ?)"
                " ON CONFLICT (tenant_id, topic_id) DO UPDATE SET hidden_opens = hidden_opens + 1, last_opened_at = excluded.last_opened_at",
                (self.tenant_id, topic_id, at or utc_now()),
            )

    def topic_mark(self, topic_id: str) -> dict[str, Any] | None:
        return self._one("SELECT * FROM topic_mark WHERE topic_id = ? AND tenant_id = ?", (topic_id, self.tenant_id))

    # --- rebuild support ---

    def clear_derived(self) -> None:
        """Empty every derived table for a rebuild. The layout and the marks are your state and stay, and so do your
        decisions on suggestions: the confirmed and rejected rows are kept, and only the waiting ones go. The builder
        then puts each suggestion back from memory's link rows (`put_suggestion_from_link`), which say the same."""
        with transaction(self.conn):
            for table in DERIVED_TABLES:
                if table == "suggestion":
                    self.conn.execute("DELETE FROM suggestion WHERE status = 'waiting' AND tenant_id = ?", (self.tenant_id,))
                else:
                    self.conn.execute(f"DELETE FROM {table} WHERE tenant_id = ?", (self.tenant_id,))
