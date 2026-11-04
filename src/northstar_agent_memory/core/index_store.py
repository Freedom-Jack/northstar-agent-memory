"""index.db: the AI index (MEMORY-ARCHITECTURE §2.10, §3.2). A minimal adapter for the IndexPort.

`SQLiteIndexStore` is create, read, update and delete over the tables of index.sql, plus BM25 keyword search over
`keys` (items) and `history_keys` (chat-history exchanges) that returns ids with scores. `search` answers the port
with the keyword list alone: the other three lists (links, meaning, time), their reciprocal-rank fusion and the
near-duplicate drop of §4.2 come with the index builder in a later build step, as does the full rebuild. What is
here already keeps the rules of the two directions that need no other store: a push returns only active facts,
never a contradicted one, whose scope covers the chat; a pull returns active facts and views in the scopes you
allowed. The index never uses who said it or which product (I23).

Most of the index is derived and rebuilt. `use`, `gate_bar` and `gate_bar_move` are state, not derived: use and your
corrections move them, and no rebuild can recompute them. A rebuild keeps them: `clear_derived` empties only
`DERIVED_TABLES`, and `STATE_TABLES` names the rest. A rebuild that works on a copy of index.db starts from the live
file, so the state is in the copy; one that builds a new file must copy these three tables across before the swap.
"""

from __future__ import annotations

import json
import re
import sqlite3
import struct
from typing import Any, Literal, Mapping, Sequence

from northstar_agent_memory import config as _config
from northstar_agent_memory.core.db import DEFAULT_TENANT, maintenance_setting, open_store, transaction
from northstar_agent_memory.core.ids import new_id, utc_now
from northstar_agent_memory.core.ports import SearchHit, SearchQuery

USE_KINDS = ("delivered", "recalled", "viewed", "built_on")
VECTOR_FIELDS = ("line", "question_key")
GATE_DIRECTIONS = ("lower", "raise")
GATE_REASONS = ("re_explanation", "presumption", "leak")
GOAL_CARD_TOP_ITEMS = 8  # §2.10; the fallback for `[maintenance] goal_card_top_items` (I19)

# What a rebuild replaces. `use`, `gate_bar` and `gate_bar_move` are not here: they are state a rebuild keeps.
DERIVED_TABLES = (
    "item_line", "item_filtered", "keys", "vectors", "history_keys", "history_vectors", "link_view", "goal_card",
    "start_note",
)
STATE_TABLES = ("use", "gate_bar", "gate_bar_move")

_JSON_COLUMNS = ("aliases", "top_items", "open_questions", "items")
_WORD = re.compile(r"\w+")
_ITEM_LINE_COLUMNS = (
    "item_id", "version", "kind", "line_text", "class", "scope", "status", "value", "check_status", "salience",
    "said_at", "built_at",
)
_LINK_COLUMNS = ("link_id", "from_id", "to_id", "to_kind", "type", "strength")


def match_query(text: str) -> str | None:
    """Turn free text into an FTS5 query: each word quoted, joined by OR so BM25 ranks by how many match.

    Quoting keeps user text from being read as FTS5 syntax. Returns None when there are no words.
    """
    words = _WORD.findall(text.casefold())
    return " OR ".join(f'"{w}"' for w in dict.fromkeys(words)) or None


def pack_vector(values: Sequence[float]) -> bytes:
    return struct.pack(f"<{len(values)}f", *values)


def unpack_vector(blob: bytes) -> list[float]:
    return list(struct.unpack(f"<{len(blob) // 4}f", blob))


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


class SQLiteIndexStore:
    """The IndexPort on index.db. One writer (the maintenance rebuild, plus use and correction updates).

    `config` holds `[maintenance]` (the loaded config if None): a goal card lists at most `goal_card_top_items` items."""

    def __init__(self, conn: sqlite3.Connection, tenant_id: str = DEFAULT_TENANT, *, config: Mapping[str, Any] | None = None) -> None:
        self.conn = conn
        self.tenant_id = tenant_id
        section = (_config.load() if config is None else config).get("maintenance", {})
        self.goal_card_top_items = int(maintenance_setting(section, "goal_card_top_items", GOAL_CARD_TOP_ITEMS, whole=True, low=1))

    @classmethod
    def open(cls, root=None, tenant_id: str = DEFAULT_TENANT, **kwargs) -> "SQLiteIndexStore":
        return cls(open_store("index", root), tenant_id, **kwargs)

    def close(self) -> None:
        self.conn.close()

    def _all(self, sql: str, args: Sequence[Any]) -> list[dict[str, Any]]:
        return [_row(r) for r in self.conn.execute(sql, args).fetchall()]  # type: ignore[misc]

    # --- item lines ---

    def put_item_line(self, line: Mapping[str, Any]) -> None:
        """Insert or replace one item's line. `line` has the columns of item_line (`salience`, `built_at` optional)."""
        values = {"salience": 0.0, "said_at": None, "built_at": utc_now(), **line}
        missing = [c for c in _ITEM_LINE_COLUMNS if c not in values]
        if missing:
            raise ValueError(f"item line is missing {missing}")
        columns = ("tenant_id", *_ITEM_LINE_COLUMNS)
        sql = f"INSERT OR REPLACE INTO item_line ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})"
        with transaction(self.conn):
            self.conn.execute(sql, (self.tenant_id, *(values[c] for c in _ITEM_LINE_COLUMNS)))

    def item_line(self, item_id: str) -> dict[str, Any] | None:
        return _row(self.conn.execute("SELECT * FROM item_line WHERE item_id = ? AND tenant_id = ?", (item_id, self.tenant_id)).fetchone())

    def item_lines(self, *, scope: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
        sql, args = "SELECT * FROM item_line WHERE tenant_id = ?", [self.tenant_id]
        if scope is not None:
            sql, args = sql + " AND scope = ?", args + [scope]
        if status is not None:
            sql, args = sql + " AND status = ?", args + [status]
        return self._all(sql + " ORDER BY item_id", args)

    def set_salience(self, item_id: str, salience: float) -> None:
        with transaction(self.conn):
            self.conn.execute("UPDATE item_line SET salience = ? WHERE item_id = ? AND tenant_id = ?", (salience, item_id, self.tenant_id))

    def delete_item(self, item_id: str) -> None:
        """Remove an item from the line table, the filtered list, the keyword index, its vectors and its links."""
        with transaction(self.conn):
            for table in ("item_line", "item_filtered", "keys", "vectors"):
                self.conn.execute(f"DELETE FROM {table} WHERE item_id = ? AND tenant_id = ?", (item_id, self.tenant_id))
            self.conn.execute(
                "DELETE FROM link_view WHERE (from_id = ? OR to_id = ?) AND tenant_id = ?", (item_id, item_id, self.tenant_id)
            )

    def set_filtered(self, item_id: str, reason: str) -> None:
        """An active item kept out of the index, with its reason (I9)."""
        if not reason.strip():
            raise ValueError("an item kept out of the index needs a reason")
        with transaction(self.conn):
            self.conn.execute(
                "INSERT OR REPLACE INTO item_filtered (tenant_id, item_id, reason) VALUES (?, ?, ?)", (self.tenant_id, item_id, reason)
            )

    def filtered(self) -> list[dict[str, Any]]:
        return self._all("SELECT * FROM item_filtered WHERE tenant_id = ? ORDER BY item_id", (self.tenant_id,))

    # --- keyword index over items ---

    def put_keys(
        self,
        item_id: str,
        *,
        line: str,
        your_words: str = "",
        why: str = "",
        question_key: str = "",
        topic_labels: str = "",
        aliases: str = "",
    ) -> None:
        """Replace an item's keyword row. The id columns are not indexed, so the delete scans the table (fine for an
        incremental rebuild)."""
        with transaction(self.conn):
            self.conn.execute("DELETE FROM keys WHERE item_id = ? AND tenant_id = ?", (item_id, self.tenant_id))
            self.conn.execute(
                "INSERT INTO keys (tenant_id, item_id, line, your_words, why, question_key, topic_labels, aliases)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (self.tenant_id, item_id, line, your_words, why, question_key, topic_labels, aliases),
            )

    def search_keys(self, text: str, limit: int = 20) -> list[tuple[str, float]]:
        """Items matching the words of `text`, best first, as (item_id, score). The score is BM25 turned so that
        higher is better. No filtering by status or scope: that is `search`."""
        query = match_query(text)
        if query is None:
            return []
        rows = self.conn.execute(
            "SELECT item_id, -bm25(keys) AS score FROM keys WHERE keys MATCH ? AND tenant_id = ? ORDER BY score DESC, item_id LIMIT ?",
            (query, self.tenant_id, limit),
        ).fetchall()
        return [(r["item_id"], r["score"]) for r in rows]

    # --- vectors ---

    def put_vector(self, item_id: str, model: str, field: Literal["line", "question_key"], version: int, values: Sequence[float]) -> None:
        _choice(field, VECTOR_FIELDS, "field")
        if not values:
            raise ValueError("a vector needs at least one number")
        with transaction(self.conn):
            self.conn.execute(
                "INSERT OR REPLACE INTO vectors (tenant_id, item_id, model, field, version, dim, vector, built_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (self.tenant_id, item_id, model, field, version, len(values), pack_vector(values), utc_now()),
            )

    def get_vector(self, item_id: str, model: str, field: Literal["line", "question_key"]) -> list[float] | None:
        row = self.conn.execute(
            "SELECT vector FROM vectors WHERE item_id = ? AND model = ? AND field = ? AND tenant_id = ?",
            (item_id, model, field, self.tenant_id),
        ).fetchone()
        return None if row is None else unpack_vector(row["vector"])

    def delete_vectors_not_from(self, model: str) -> int:
        """Drop vectors of any other model, so a model change rebuilds them. Returns how many were dropped."""
        with transaction(self.conn):
            cursor = self.conn.execute("DELETE FROM vectors WHERE model != ? AND tenant_id = ?", (model, self.tenant_id))
        return cursor.rowcount

    # --- chat-history exchanges ---

    def put_exchange(
        self,
        exchange_id: str,
        *,
        source_id: str,
        user_message_id: str,
        reply_message_id: str | None,
        occurred_at: str,
        your_text: str,
        reply_text: str = "",
        item_lines: str = "",
    ) -> None:
        """Replace one exchange (your turn with its reply) in the history keyword index. Your text and the reply are
        separate columns, so a search can return your words by default (§4.7)."""
        with transaction(self.conn):
            self.conn.execute("DELETE FROM history_keys WHERE exchange_id = ? AND tenant_id = ?", (exchange_id, self.tenant_id))
            self.conn.execute(
                "INSERT INTO history_keys (tenant_id, exchange_id, source_id, user_message_id, reply_message_id, occurred_at,"
                " your_text, reply_text, item_lines) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (self.tenant_id, exchange_id, source_id, user_message_id, reply_message_id, occurred_at, your_text, reply_text, item_lines),
            )

    def delete_exchange(self, exchange_id: str) -> None:
        with transaction(self.conn):
            self.conn.execute("DELETE FROM history_keys WHERE exchange_id = ? AND tenant_id = ?", (exchange_id, self.tenant_id))
            self.conn.execute("DELETE FROM history_vectors WHERE exchange_id = ? AND tenant_id = ?", (exchange_id, self.tenant_id))

    def search_history(self, text: str, limit: int = 20) -> list[dict[str, Any]]:
        """Exchanges matching the words of `text`, best first: the ids of the exchange, source and messages, when it
        happened, and `score` (BM25, higher is better). It returns ids only, never the texts."""
        query = match_query(text)
        if query is None:
            return []
        rows = self.conn.execute(
            "SELECT exchange_id, source_id, user_message_id, reply_message_id, occurred_at, -bm25(history_keys) AS score"
            " FROM history_keys WHERE history_keys MATCH ? AND tenant_id = ? ORDER BY score DESC, exchange_id LIMIT ?",
            (query, self.tenant_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def put_history_vector(self, exchange_id: str, model: str, values: Sequence[float]) -> None:
        if not values:
            raise ValueError("a vector needs at least one number")
        with transaction(self.conn):
            self.conn.execute(
                "INSERT OR REPLACE INTO history_vectors (tenant_id, exchange_id, model, dim, vector, built_at) VALUES (?, ?, ?, ?, ?, ?)",
                (self.tenant_id, exchange_id, model, len(values), pack_vector(values), utc_now()),
            )

    def get_history_vector(self, exchange_id: str, model: str) -> list[float] | None:
        row = self.conn.execute(
            "SELECT vector FROM history_vectors WHERE exchange_id = ? AND model = ? AND tenant_id = ?",
            (exchange_id, model, self.tenant_id),
        ).fetchone()
        return None if row is None else unpack_vector(row["vector"])

    # --- links ---

    def put_link(self, link: Mapping[str, Any]) -> None:
        """Insert or replace a checked link, with the columns of link_view."""
        missing = [c for c in _LINK_COLUMNS if c not in link]
        if missing:
            raise ValueError(f"link is missing {missing}")
        with transaction(self.conn):
            self.conn.execute(
                f"INSERT OR REPLACE INTO link_view (tenant_id, {', '.join(_LINK_COLUMNS)}) VALUES (?, {', '.join('?' for _ in _LINK_COLUMNS)})",
                (self.tenant_id, *(link[c] for c in _LINK_COLUMNS)),
            )

    def delete_link(self, link_id: str) -> None:
        with transaction(self.conn):
            self.conn.execute("DELETE FROM link_view WHERE link_id = ? AND tenant_id = ?", (link_id, self.tenant_id))

    def links_of(self, item_id: str) -> list[dict[str, Any]]:
        """Links with this item at either end, for searching one or two steps out (§4.2 L1)."""
        return self._all(
            "SELECT * FROM link_view WHERE (from_id = ? OR to_id = ?) AND tenant_id = ? ORDER BY link_id",
            (item_id, item_id, self.tenant_id),
        )

    # --- goal cards and start notes ---

    def put_goal_card(
        self,
        card_id: str,
        goal_text: str,
        *,
        goal_item_id: str | None = None,
        thread_id: str | None = None,
        aliases: Sequence[str] = (),
        project: str | None = None,
        top_items: Sequence[str] = (),
        open_questions: Sequence[str] = (),
        last_active: str | None = None,
    ) -> None:
        if goal_item_id is None and thread_id is None:
            raise ValueError("a goal card belongs to a goal item or a work thread")
        if len(top_items) > self.goal_card_top_items:
            raise ValueError(f"a goal card holds at most {self.goal_card_top_items} top items")
        with transaction(self.conn):
            self.conn.execute(
                "INSERT OR REPLACE INTO goal_card (tenant_id, id, goal_item_id, thread_id, goal_text, aliases, project, top_items,"
                " open_questions, last_active, built_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    self.tenant_id, card_id, goal_item_id, thread_id, goal_text, json.dumps(list(aliases)), project,
                    json.dumps(list(top_items)), json.dumps(list(open_questions)), last_active, utc_now(),
                ),
            )

    def goal_card(self, card_id: str) -> dict[str, Any] | None:
        return _row(self.conn.execute("SELECT * FROM goal_card WHERE id = ? AND tenant_id = ?", (card_id, self.tenant_id)).fetchone())

    def goal_cards(self, *, project: str | None = None) -> list[dict[str, Any]]:
        """Cards, most recently active first. Which goals and threads are active is decided by whoever builds them."""
        sql, args = "SELECT * FROM goal_card WHERE tenant_id = ?", [self.tenant_id]
        if project is not None:
            sql, args = sql + " AND project = ?", args + [project]
        return self._all(sql + " ORDER BY last_active DESC, id", args)

    def put_start_note(self, thread_id: str, text: str, items: Sequence[str], watermark: int) -> None:
        with transaction(self.conn):
            self.conn.execute(
                "INSERT OR REPLACE INTO start_note (tenant_id, thread_id, text, items, built_at, watermark) VALUES (?, ?, ?, ?, ?, ?)",
                (self.tenant_id, thread_id, text, json.dumps(list(items)), utc_now(), watermark),
            )

    def start_note(self, thread_id: str) -> dict[str, Any] | None:
        return _row(self.conn.execute("SELECT * FROM start_note WHERE thread_id = ? AND tenant_id = ?", (thread_id, self.tenant_id)).fetchone())

    # --- use ---

    def record_use(self, item_id: str, kind: Literal["delivered", "recalled", "viewed", "built_on"], context: str, at: str | None = None) -> None:
        _choice(kind, USE_KINDS, "kind")
        if not context:
            raise ValueError("a use needs the session or chat it happened in")
        with transaction(self.conn):
            self.conn.execute(
                "INSERT INTO use (tenant_id, id, item_id, kind, at, context) VALUES (?, ?, ?, ?, ?, ?)",
                (self.tenant_id, new_id(), item_id, kind, at or utc_now(), context),
            )

    def uses(self, item_id: str) -> list[dict[str, Any]]:
        """Every use of an item, oldest first, for salience (§5.11)."""
        return self._all("SELECT * FROM use WHERE item_id = ? AND tenant_id = ? ORDER BY at, id", (item_id, self.tenant_id))

    def use_summary(self, item_id: str) -> dict[str, Any] | None:
        return _row(self.conn.execute("SELECT * FROM use_summary WHERE item_id = ? AND tenant_id = ?", (item_id, self.tenant_id)).fetchone())

    # --- the strict gate's bar ---

    def set_gate_bar(self, project: str, bar: float, floor: float) -> None:
        if bar < floor:
            raise ValueError("the bar cannot start below its floor")
        with transaction(self.conn):
            self.conn.execute(
                "INSERT OR REPLACE INTO gate_bar (tenant_id, project, bar, floor, updated_at) VALUES (?, ?, ?, ?, ?)",
                (self.tenant_id, project, bar, floor, utc_now()),
            )

    def gate_bar(self, project: str) -> float | None:
        row = self.conn.execute("SELECT bar FROM gate_bar WHERE project = ? AND tenant_id = ?", (project, self.tenant_id)).fetchone()
        return None if row is None else row["bar"]

    def move_gate_bar(
        self,
        project: str,
        direction: Literal["lower", "raise"],
        reason: Literal["re_explanation", "presumption", "leak"],
        *,
        step: float,
        floor: float,
        ref: str | None = None,
    ) -> float:
        """Move the bar one step, never below `floor`; log the move; return the new bar. The project needs a bar
        already (`set_gate_bar`: its starting value comes from the config)."""
        _choice(direction, GATE_DIRECTIONS, "direction")
        _choice(reason, GATE_REASONS, "reason")
        if step <= 0:
            raise ValueError("a step is positive")
        now = utc_now()
        with transaction(self.conn):
            row = self.conn.execute("SELECT bar FROM gate_bar WHERE project = ? AND tenant_id = ?", (project, self.tenant_id)).fetchone()
            if row is None:
                raise KeyError(f"project {project!r} has no gate bar yet")
            before = row["bar"]
            after = max(floor, before - step if direction == "lower" else before + step)
            self.conn.execute(
                "UPDATE gate_bar SET bar = ?, floor = ?, updated_at = ? WHERE project = ? AND tenant_id = ?",
                (after, floor, now, project, self.tenant_id),
            )
            self.conn.execute(
                "INSERT INTO gate_bar_move (tenant_id, id, project, at, direction, reason, bar_before, bar_after, ref)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (self.tenant_id, new_id(), project, now, direction, reason, before, after, ref),
            )
        return after

    def gate_bar_moves(self, project: str) -> list[dict[str, Any]]:
        return self._all("SELECT * FROM gate_bar_move WHERE project = ? AND tenant_id = ? ORDER BY at, id", (project, self.tenant_id))

    # --- search (keyword list only) ---

    def search(self, query: SearchQuery) -> list[SearchHit]:
        """Keyword search over `keys`, filtered for the query's direction (see the module docstring).

        Every hit is found by 'words'; the score is BM25 (higher is better). `as_of_seq` needs row history from
        memory.db and is not supported here.
        """
        if query.as_of_seq is not None:
            raise NotImplementedError("earlier versions come from memory.db, not the index")
        found = self.search_keys(query.text, limit=max(query.top_n * 5, 50))
        skip = set(query.exclude_item_ids) | {f["item_id"] for f in self.filtered()}  # kept out of the index (I9)
        hits: list[SearchHit] = []
        for item_id, score in found:
            line = self.item_line(item_id)
            if line is None or item_id in skip or line["status"] != "active":
                continue
            if query.direction == "push":
                scopes = {"personal"} | ({f"project:{query.project}"} if query.project else set())
                if line["class"] != "fact" or line["check_status"] == "contradicted" or line["scope"] not in scopes:
                    continue
            elif query.allowed_scopes is not None and line["scope"] not in query.allowed_scopes:
                continue
            hits.append(SearchHit(item_id, line["version"], line["line_text"], score, ["words"], line["scope"], line["kind"]))
            if len(hits) == query.top_n:
                break
        return hits

    # --- rebuild support ---

    def clear_derived(self) -> None:
        """Empty every derived table for a full rebuild. `STATE_TABLES` (`use`, `gate_bar`, `gate_bar_move`) are state a
        rebuild keeps, so they are never cleared here."""
        with transaction(self.conn):
            for table in DERIVED_TABLES:
                self.conn.execute(f"DELETE FROM {table} WHERE tenant_id = ?", (self.tenant_id,))
