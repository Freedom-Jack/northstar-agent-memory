"""The projector: events into current-state rows and row history (MEMORY-ARCHITECTURE §2.3-§2.8, §3.1, §3.4, §5.9, I18).

`Projector` implements `ports.Projector`. The write gate calls `apply(conn, envelopes)` inside its transaction on
memory.db, after the events are appended (so each has its `seq`). For every event it changes the current-state tables
and keeps row history: before a row changes or is removed its old state goes to `<table>_history` with `seq_to` set to
the event's seq, and the row's `seq_from` becomes that seq (`db.archive_row`). A row touched twice by one event is
archived once. The same event stream always gives the same rows: the projector reads only `conn` and the envelope,
uses no clock and no randomness, and only looks at events with a lower seq than the one it is projecting.

What each family does (the schema files say which columns):
- Items: `item.created` makes a forming, active item (class from kind; adopted claims start `unchecked`).
  `item.revised` and `item.scope_widened` raise the version; value, status and check change in place.
- A `same_as` link that becomes applied or confirmed is a merge: the `from` item gets `merged_into`, becomes
  superseded (its line stays as an alias) and its evidence moves to the kept item. Retracting or rejecting that link
  undoes the merge.
- `supersession.applied` makes the old item superseded when the new one is a different item; for a refresh (same
  item) the version bump belongs to `item.revised`. `supersession.undone` restores the old item to active, or the old
  version's content for a refresh (as a new version, so versions only rise).
- Evidence carries the context the gate stamped (the source's project, or "personal"). An item's `contexts_seen`
  starts with `learned_in` and grows by each new context its evidence is anchored in, so a second context comes
  from the evidence and never from a claim in a proposal (§2.4, §5.5).
- Goals and questions are items with their extra columns. An answered question keeps `answered_by`, the items that
  answer it; each must exist and not be purged. Topic events change topics only: a retired topic keeps its
  placements and `redirect_to` says where it lives now (ideas move by `idea.moved`).
- Placement: every idea has one home. Making a place home demotes the old home to also_in, or removes it if the idea
  already has two also_in places.
- `compensation.batch` reverses the named events, latest first, field by field from row history. A field already
  back to its earlier value is left alone; a field changed by a later event that is not itself being undone is an
  error. An event that has its own typed compensating event (`supersession.undone` and so on, before the batch) is
  skipped, and a purge is never compensated. A stance is append-only, so the batch removes the one its event recorded under a purge_authorization row
  named for the batch (a stance has no row history, so undoing the batch does not bring it back); evidence rows a
  batch removes are authorized the same way, because only a purge or a rollback may delete evidence. A batch that
  would leave a row pointing at a removed item is an error, not a foreign-key failure at COMMIT.
- `purge.applied` stubs the items (and the items merged into them) as "removed at your request on <date>", scrubs
  evidence quotes, link reasons, row-history snapshots and the text in the event payloads that mention them, under
  `purge_authorization` rows it writes first (§3.4). In the event payloads the words become numbered tokens
  (`[purged:3]`), the same words by the same token, so equal stays equal and a replay over the scrubbed log makes
  the same decisions; a purge is always the last word on an item, so it ends in the same rows.

An event the projector cannot apply raises `ProjectionError`, whether the cause is an unknown row, a rule of the
schema or a reference that would not hold at COMMIT; the gate's transaction then rolls back.
"""

from __future__ import annotations

import json
import re
import sqlite3
from typing import Any, Sequence

from northstar_agent_memory.core import db, events
from northstar_agent_memory.core.events import EventEnvelope
from northstar_agent_memory.core.reader import HISTORY_TABLES, row_as_of

PURGE_STUB = "removed at your request on {date}"
# Item fields whose change raises the version (§2.4: the line, the scope, and what qualifies them).
VERSIONED_FIELDS = (
    "line", "your_words", "why", "question_key", "scope", "applies_when", "valid_from", "valid_to", "time_bound",
)  # fmt: skip
# Free text a purge removes from event payloads that mention a purged item; link text is scrubbed the same way.
SCRUBBED_KEYS = ("line", "your_words", "why", "question_key", "quote")
SCRUBBED_LINK_EVENTS = ("link.proposed", "link.applied")
_NOT_REVERTED = ("tenant_id", "seq_from", "version")
_LINK_ENTRY = {  # link events that move a link into a status, and the statuses they may start from
    "confirmed": ("proposed", "applied"),
    "rejected": ("proposed", "applied", "confirmed"),
    "retracted": ("proposed", "applied", "confirmed"),
}
_CHUNK = 400
_TOKEN = re.compile(r"^\[purged:\d+\]$")


class ProjectionError(RuntimeError):
    """An event that cannot be projected: an unknown row, a rule of the schema, or a state it does not fit."""


def dump(value: Any) -> str:
    """Canonical JSON text for JSON columns and snapshots."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _val(value: Any) -> Any:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (list, dict)):
        return dump(value)
    return value


def _row(conn: sqlite3.Connection, table: str, row_id: str) -> sqlite3.Row | None:
    return conn.execute(f"SELECT * FROM {table} WHERE id = ?", (row_id,)).fetchone()


def _need(conn: sqlite3.Connection, table: str, row_id: str) -> sqlite3.Row:
    row = _row(conn, table, row_id)
    if row is None:
        raise ProjectionError(f"{table} {row_id!r} does not exist")
    return row


def _archive(conn: sqlite3.Connection, table: str, row: sqlite3.Row, seq: int) -> None:
    if row["seq_from"] != seq:  # already this event's own state
        db.archive_row(conn, table, row["id"], seq)


def _insert(conn: sqlite3.Connection, table: str, values: dict[str, Any]) -> None:
    names = ", ".join(values)
    marks = ", ".join("?" for _ in values)
    conn.execute(f"INSERT INTO {table} ({names}) VALUES ({marks})", tuple(_val(v) for v in values.values()))


def _change(conn: sqlite3.Connection, table: str, row_id: str, seq: int, **changes: Any) -> bool:
    """Set columns of a current row, archiving its old state first. Does nothing if no value differs."""
    row = _need(conn, table, row_id)
    diff = {k: _val(v) for k, v in changes.items() if row[k] != _val(v)}
    if not diff:
        return False
    _archive(conn, table, row, seq)
    diff["seq_from"] = seq
    sets = ", ".join(f"{k} = ?" for k in diff)
    conn.execute(f"UPDATE {table} SET {sets} WHERE id = ?", (*diff.values(), row_id))
    return True


def _authorize_removal(conn: sqlite3.Connection, table: str, row_id: str, seq: int) -> None:
    """Write the purge_authorization row that lets a rollback delete `row_id` of `table` (evidence, stance), named for
    the event at `seq`, and keep it. The schema refuses such a delete without it."""
    event = conn.execute("SELECT id, tenant_id, recorded_at FROM event WHERE seq = ?", (seq,)).fetchone()
    if event is None:
        raise ProjectionError(f"cannot remove {table} {row_id!r}: there is no event at seq {seq} to authorize it")
    conn.execute(
        "INSERT OR IGNORE INTO purge_authorization (tenant_id, purge_id, target_table, target_id, authorized_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (event["tenant_id"], f"compensation:{event['id']}", table, row_id, event["recorded_at"]),
    )


def _remove(conn: sqlite3.Connection, table: str, row_id: str, seq: int) -> None:
    row = _need(conn, table, row_id)
    _archive(conn, table, row, seq)
    if table == "evidence":  # only a purge or a rollback deletes evidence (the schema's trigger)
        _authorize_removal(conn, table, row_id, seq)
    conn.execute(f"DELETE FROM {table} WHERE id = ?", (row_id,))


def _live_item(conn: sqlite3.Connection, item_id: str) -> sqlite3.Row:
    """An item that exists and is not purged: a purge is the last word, so nothing writes to a purged item again."""
    item = _need(conn, "item", item_id)
    if item["status"] == "purged":
        raise ProjectionError(f"item {item_id!r} was purged; nothing can change or join it any more")
    return item


def _chunks(items: Sequence[str]) -> list[list[str]]:
    return [list(items[i : i + _CHUNK]) for i in range(0, len(items), _CHUNK)]


def _marks(n: int) -> str:
    return ", ".join("?" for _ in range(n))


def _touched_ids(conn: sqlite3.Connection, table: str, seq: int) -> list[str]:
    """Ids of the rows of `table` that the event at `seq` created, changed or removed."""
    ids: set[str] = set()
    for sql in (
        f"SELECT id FROM {table}_history WHERE seq_to = ?",
        f"SELECT id FROM {table}_history WHERE seq_from = ?",
        f"SELECT id FROM {table} WHERE seq_from = ?",
    ):
        ids.update(r[0] for r in conn.execute(sql, (seq,)))
    return sorted(ids)


def revert_event(
    conn: sqlite3.Connection, target_seq: int, at_seq: int, tables: Sequence[str] = HISTORY_TABLES
) -> None:
    """Undo what the event at `target_seq` did to the rows of `tables`, as one more change at `at_seq`.

    A row the event created is removed; one it removed is put back; one it changed gets back the fields it changed,
    provided they still hold the value the event gave them (or already hold the earlier one). The version of an item
    never goes back: if a versioned field is restored, the version rises instead.
    """
    for table in tables:
        revert_rows(conn, table, _touched_ids(conn, table, target_seq), target_seq, at_seq)


def revert_rows(conn: sqlite3.Connection, table: str, row_ids: Sequence[str], target_seq: int, at_seq: int) -> None:
    """`revert_event` for some rows of one table. Removals come first, then changes, then rows put back, with
    rows that return to being an idea's home last, so a unique home is never doubled on the way."""
    plans = [plan for row_id in row_ids if (plan := _plan_revert(conn, table, row_id, target_seq, at_seq))]
    plans.sort(key=lambda plan: (plan[0], plan[1]))
    for _, _, apply in plans:
        apply()


def _snapshot(conn: sqlite3.Connection, sql: str, args: tuple) -> dict | None:
    row = conn.execute(sql, args).fetchone()
    return json.loads(row[0]) if row is not None else None


def _plan_revert(conn, table: str, row_id: str, target_seq: int, at_seq: int):
    """(phase, row id, action) for undoing one row, or None when there is nothing to do. Raises if a later event
    changed what this event set."""
    before = _snapshot(conn, f"SELECT snapshot FROM {table}_history WHERE id = ? AND seq_to = ?", (row_id, target_seq))
    current = _row(conn, table, row_id)
    after = _snapshot(conn, f"SELECT snapshot FROM {table}_history WHERE id = ? AND seq_from = ?", (row_id, target_seq))
    if after is None and current is not None and current["seq_from"] == target_seq:
        after = dict(current)
    if before is None and after is None:
        return None
    if before is None:  # the event created it
        if current is None:
            return None
        if current["seq_from"] not in (target_seq, at_seq):
            raise ProjectionError(f"{table} {row_id!r} was changed after the event being undone (seq {target_seq})")
        return 0, row_id, lambda: _remove(conn, table, row_id, at_seq)
    if after is None:  # the event removed it
        if current is not None:
            return None
        restored = {k: v for k, v in before.items() if k != "seq_from"}
        return 3, row_id, lambda: _insert(conn, table, {**restored, "seq_from": at_seq})
    if current is None:
        raise ProjectionError(f"{table} {row_id!r} no longer exists, so seq {target_seq} cannot be undone")
    restore: dict[str, Any] = {}
    for column, earlier in before.items():
        if column in _NOT_REVERTED or earlier == after.get(column):
            continue
        now = current[column]
        if now == earlier:
            continue
        if now != after.get(column):
            raise ProjectionError(f"{table} {row_id!r} {column} was changed after the event being undone (seq {target_seq})")
        restore[column] = earlier
    if table == "item" and any(column in VERSIONED_FIELDS for column in restore):
        restore["version"] = current["version"] + 1
    if not restore:
        return None
    return (2 if restore.get("role") == "home" else 1), row_id, lambda: _change(conn, table, row_id, at_seq, **restore)


class Projector:
    """`ports.Projector` for memory.db. `tenant_id` goes on every row it writes (§3.3)."""

    def __init__(self, tenant_id: str = db.DEFAULT_TENANT):
        self.tenant_id = tenant_id

    def apply(self, conn: sqlite3.Connection, envelopes: Sequence[EventEnvelope]) -> None:
        last = 0
        conn.execute("SAVEPOINT projector_apply")  # all of the events, or none, even outside the gate's transaction
        try:
            for env in envelopes:
                if not isinstance(env.seq, int) or env.seq <= last:
                    raise ProjectionError(f"{env.type}: events are projected in seq order, each with its seq (got {env.seq!r})")
                last = env.seq
                self._project(conn, env)
        except BaseException:
            conn.execute("ROLLBACK TO projector_apply")
            conn.execute("RELEASE projector_apply")
            raise
        conn.execute("RELEASE projector_apply")

    def _project(self, conn: sqlite3.Connection, env: EventEnvelope) -> None:
        cls = events.payload_class(env.type, env.schema_version)
        handler = getattr(self, "_on_" + env.type.replace(".", "_"), None)
        if cls is None or handler is None:
            raise ProjectionError(f"I15: no schema for {env.type} version {env.schema_version}")
        try:
            payload = cls(**env.payload)
        except TypeError as err:
            raise ProjectionError(f"{env.type} at seq {env.seq}: payload does not fit its schema: {err}") from err
        try:
            handler(conn, env, payload)
        except sqlite3.IntegrityError as err:
            raise ProjectionError(f"{env.type} at seq {env.seq}: {err}") from err

    def _new(self, conn: sqlite3.Connection, table: str, seq: int, values: dict[str, Any]) -> None:
        _insert(conn, table, {"tenant_id": self.tenant_id, **values, "created_seq": seq, "seq_from": seq})

    # --- evidence ---------------------------------------------------------------------------------------------

    def _on_evidence_anchored(self, conn, env, p):
        found = _row(conn, "item", p.subject_id) if p.subject_kind == "item" else None
        if found is not None and found["status"] == "purged":
            raise ProjectionError(f"item {p.subject_id!r} was purged; no evidence can be anchored to it")
        self._new(conn, "evidence", env.seq, dict(
            id=p.evidence_id, subject_kind=p.subject_kind, subject_id=p.subject_id, message_id=p.message_id,
            start_char=p.start_char, end_char=p.end_char, quote=p.quote, role=p.role, speaker=p.speaker,
            agent=p.agent, model_family=p.model_family, origin=p.origin, lineage=p.lineage, context=p.context,
        ))  # fmt: skip
        if p.subject_kind == "item" and p.context is not None and found is not None:
            self._add_context(conn, env.seq, found, p.context)

    def _add_context(self, conn, seq: int, item: sqlite3.Row, context: str) -> None:
        """Evidence from a context the item has not been seen in joins its `contexts_seen`."""
        seen = json.loads(item["contexts_seen"])
        if context not in seen:
            _change(conn, "item", item["id"], seq, contexts_seen=[*seen, context])

    # --- items ------------------------------------------------------------------------------------------------

    def _new_item(self, conn, env, kind: str, p, **extra) -> None:
        if p.origin is None:
            raise ProjectionError(f"{env.type} at seq {env.seq}: origin must be stamped from capture before projection")
        self._new(conn, "item", env.seq, {
            "id": p.item_id, "version": 1, "kind": kind, "class": events.ITEM_CLASS_OF_KIND[kind], "line": p.line,
            "your_words": p.your_words, "why": getattr(p, "why", ""), "question_key": getattr(p, "question_key", ""),
            "scope": p.scope, "applies_when": getattr(p, "applies_when", "unknown"), "learned_in": p.learned_in,
            "contexts_seen": self._first_contexts(conn, p), "origin": p.origin, "value": "forming", "status": "active",
            "check_status": "unchecked" if p.origin.startswith("adopted:") else "not_needed", "said_at": p.said_at,
            "valid_from": getattr(p, "valid_from", None), "valid_to": getattr(p, "valid_to", None),
            "recorded_at": env.recorded_at, "time_bound": getattr(p, "time_bound", False), **extra,
        })

    def _first_contexts(self, conn, p) -> list[str]:
        """`learned_in`, then the contexts of the evidence already anchored to this item (evidence comes first, §6.2)."""
        seen = [p.learned_in]
        for found in conn.execute(
            "SELECT context FROM evidence WHERE subject_kind = 'item' AND subject_id = ? AND context IS NOT NULL"
            " ORDER BY created_seq, id", (p.item_id,)
        ):
            if found["context"] not in seen:
                seen.append(found["context"])
        return seen

    def _on_item_created(self, conn, env, p):
        self._new_item(conn, env, p.kind, p)

    def _on_item_revised(self, conn, env, p):
        item = _live_item(conn, p.item_id)
        changes: dict[str, Any] = {"line": p.line, "version": item["version"] + 1}
        for name in ("your_words", "why", "question_key", "applies_when", "valid_from", "valid_to", "scope", "time_bound"):
            if getattr(p, name) is not None:
                changes[name] = getattr(p, name)
        _change(conn, "item", p.item_id, env.seq, **changes)

    def _on_item_value_changed(self, conn, env, p):
        _live_item(conn, p.item_id)
        _change(conn, "item", p.item_id, env.seq, value=p.to_value)

    def _on_item_scope_widened(self, conn, env, p):
        item = _live_item(conn, p.item_id)
        _change(conn, "item", p.item_id, env.seq, scope=p.to_scope, version=item["version"] + 1)

    def _on_item_status_changed(self, conn, env, p):
        if p.to_status == "purged":
            raise ProjectionError("a purge is purge.applied, not a status change")
        _live_item(conn, p.item_id)
        _change(conn, "item", p.item_id, env.seq, status=p.to_status)

    def _on_item_checked(self, conn, env, p):
        _live_item(conn, p.item_id)
        _change(conn, "item", p.item_id, env.seq, check_status=p.check_status)

    def _on_stance_recorded(self, conn, env, p):
        _live_item(conn, p.item_id)
        _insert(conn, "stance", dict(
            tenant_id=self.tenant_id, id=env.id, item_id=p.item_id, stance=p.stance, evidence_ids=list(p.evidence_ids),
            created_seq=env.seq,
        ))  # fmt: skip

    # --- links and merges -------------------------------------------------------------------------------------

    def _link_values(self, p) -> dict[str, Any]:
        return dict(
            id=p.link_id, from_id=p.from_id, to_id=p.to_id, to_kind=p.to_kind, type=p.link_type, reason=p.reason,
            stated_by=p.stated_by, checked_by=list(p.checked_by),
        )  # fmt: skip

    def _check_link_ends(self, conn, p) -> None:
        _live_item(conn, p.from_id)
        if p.to_kind == "item":
            _live_item(conn, p.to_id)

    def _on_link_proposed(self, conn, env, p):
        self._check_link_ends(conn, p)
        self._new(conn, "link", env.seq, {**self._link_values(p), "status": "proposed"})

    def _on_link_applied(self, conn, env, p):
        link = _row(conn, "link", p.link_id)
        if link is None:
            self._check_link_ends(conn, p)
            self._new(conn, "link", env.seq, {**self._link_values(p), "status": "applied"})
        elif link["status"] != "proposed":
            raise ProjectionError(f"link {p.link_id!r} is {link['status']}, not proposed")
        else:
            _change(conn, "link", p.link_id, env.seq, reason=p.reason, stated_by=p.stated_by, checked_by=list(p.checked_by),
                    status="applied")  # fmt: skip
        link = _need(conn, "link", p.link_id)
        if link["type"] == "same_as":
            self._merge(conn, env.seq, link["from_id"], link["to_id"])

    def _link_decision(self, conn, env, link_id: str, status: str) -> None:
        link = _need(conn, "link", link_id)
        if link["status"] not in _LINK_ENTRY[status]:
            raise ProjectionError(f"link {link_id!r} is {link['status']}; it cannot become {status}")
        _change(conn, "link", link_id, env.seq, status=status)
        if link["type"] != "same_as":
            return
        merged = link["status"] in ("applied", "confirmed")
        if status == "confirmed" and link["status"] == "proposed":
            self._merge(conn, env.seq, link["from_id"], link["to_id"])
        elif status in ("rejected", "retracted") and merged:
            self._unmerge(conn, env.seq, link_id)

    def _on_link_confirmed(self, conn, env, p):
        self._link_decision(conn, env, p.link_id, "confirmed")

    def _on_link_rejected(self, conn, env, p):
        self._link_decision(conn, env, p.link_id, "rejected")

    def _on_link_retracted(self, conn, env, p):
        self._link_decision(conn, env, p.link_id, "retracted")

    def _merge(self, conn, seq: int, from_id: str, to_id: str) -> None:
        """`from_id` becomes an alias of `to_id`: merged_into, superseded, its evidence and contexts move across."""
        gone, kept = _live_item(conn, from_id), _live_item(conn, to_id)
        if gone["merged_into"] is not None:
            raise ProjectionError(f"item {from_id!r} is already merged into {gone['merged_into']!r}")
        chain, ahead = {from_id}, kept
        while ahead is not None:  # an alias chain never loops back on itself
            if ahead["id"] in chain:
                raise ProjectionError(f"merging {from_id!r} into {to_id!r} would make a loop of aliases")
            chain.add(ahead["id"])
            ahead = _row(conn, "item", ahead["merged_into"]) if ahead["merged_into"] is not None else None
        for ev in conn.execute(
            "SELECT id FROM evidence WHERE subject_kind = 'item' AND subject_id = ? ORDER BY id", (from_id,)
        ).fetchall():
            _change(conn, "evidence", ev["id"], seq, subject_id=to_id)
        _change(conn, "item", from_id, seq, merged_into=to_id, status="superseded" if gone["status"] == "active" else gone["status"])
        contexts = json.loads(kept["contexts_seen"])
        contexts += [c for c in json.loads(gone["contexts_seen"]) if c not in contexts]
        _change(conn, "item", to_id, seq, contexts_seen=contexts)

    def _unmerge(self, conn, seq: int, link_id: str) -> None:
        """Undo the merge a same_as link made: the alias and its evidence go back, from the row history of the event
        that merged them. The kept item loses the contexts only that alias brought."""
        entry = conn.execute(
            "SELECT seq FROM event WHERE seq < ? AND type IN ('link.applied', 'link.confirmed')"
            " AND json_extract(payload, '$.link_id') = ? ORDER BY seq LIMIT 1",
            (seq, link_id),
        ).fetchone()
        if entry is None:
            raise ProjectionError(f"link {link_id!r} has no event that merged its items")
        link = _need(conn, "link", link_id)
        revert_rows(conn, "item", [link["from_id"]], entry["seq"], seq)
        revert_rows(conn, "evidence", _touched_ids(conn, "evidence", entry["seq"]), entry["seq"], seq)
        kept = _need(conn, "item", link["to_id"])
        brought = {kept["learned_in"]}
        for alias in conn.execute("SELECT contexts_seen FROM item WHERE merged_into = ?", (link["to_id"],)).fetchall():
            brought.update(json.loads(alias["contexts_seen"]))
        brought.update(  # contexts its own evidence was anchored in stay
            r["context"] for r in conn.execute(
                "SELECT DISTINCT context FROM evidence WHERE subject_kind = 'item' AND subject_id = ? AND context IS NOT NULL",
                (link["to_id"],),
            )
        )  # fmt: skip
        _change(conn, "item", link["to_id"], seq, contexts_seen=[c for c in json.loads(kept["contexts_seen"]) if c in brought])

    # --- supersession and conflicts ---------------------------------------------------------------------------

    def _on_supersession_applied(self, conn, env, p):
        old = _live_item(conn, p.old_item)
        _live_item(conn, p.new_item)
        self._new(conn, "supersession", env.seq, dict(
            id=p.supersession_id, old_item=p.old_item, old_version=p.old_version, new_item=p.new_item,
            new_version=p.new_version, reason=p.reason, evidence_ids=list(p.evidence_ids), at=env.recorded_at,
            status="applied",
        ))  # fmt: skip
        if p.old_item != p.new_item and old["status"] == "active":
            _change(conn, "item", p.old_item, env.seq, status="superseded")

    def _on_supersession_undone(self, conn, env, p):
        sup = _need(conn, "supersession", p.supersession_id)
        _change(conn, "supersession", p.supersession_id, env.seq, status="undone")
        item = _need(conn, "item", sup["old_item"])
        if sup["old_item"] != sup["new_item"]:
            if item["status"] == "superseded":
                _change(conn, "item", sup["old_item"], env.seq, status="active")
            return
        if item["version"] == sup["old_version"]:
            return
        old = conn.execute(
            "SELECT snapshot FROM item_history WHERE id = ? AND version = ? ORDER BY seq_from DESC LIMIT 1",
            (sup["old_item"], sup["old_version"]),
        ).fetchone()
        if old is None:
            raise ProjectionError(f"version {sup['old_version']} of {sup['old_item']!r} is not in row history")
        earlier = json.loads(old["snapshot"])
        content = {name: earlier[name] for name in VERSIONED_FIELDS}
        if any(item[name] != value for name, value in content.items()):
            _change(conn, "item", sup["old_item"], env.seq, version=item["version"] + 1, **content)

    def _conflict_items(self, conn, *item_ids: str | None) -> None:
        for item_id in item_ids:
            if item_id is not None:
                _need(conn, "item", item_id)

    def _on_conflict_opened(self, conn, env, p):
        self._conflict_items(conn, p.side_a_item, p.side_b_item, p.question_id)
        self._new(conn, "conflict", env.seq, dict(
            id=p.conflict_id, side_a_item=p.side_a_item, side_a_version=p.side_a_version, side_b_item=p.side_b_item,
            side_b_version=p.side_b_version, kind=p.kind, state=p.state, resolution=None, question_id=p.question_id,
            link_id=p.link_id, recheck_after=p.recheck_after,
        ))  # fmt: skip

    def _on_conflict_resolved(self, conn, env, p):
        conflict = _need(conn, "conflict", p.conflict_id)
        self._conflict_items(conn, p.question_id)
        resolution = {"step": p.step, "inputs": list(p.resolution_inputs), "rule_version": p.rule_version}
        if p.winner is not None:
            resolution["winner"] = p.winner
        _change(conn, "conflict", p.conflict_id, env.seq, state=p.state, resolution=resolution,
                question_id=p.question_id if p.question_id is not None else conflict["question_id"],
                recheck_after=p.recheck_after)  # fmt: skip

    def _on_conflict_reopened(self, conn, env, p):
        _need(conn, "conflict", p.conflict_id)
        _change(conn, "conflict", p.conflict_id, env.seq, state=p.state, resolution=None, recheck_after=p.recheck_after)

    def _on_conflict_undone(self, conn, env, p):
        conflict = _need(conn, "conflict", p.conflict_id)
        if env.compensates is not None:
            target = conn.execute("SELECT seq, type FROM event WHERE id = ?", (env.compensates,)).fetchone()
        else:  # the latest change to the conflict is the one undone
            target = conn.execute("SELECT seq, type FROM event WHERE seq = ?", (conflict["seq_from"],)).fetchone()
        if target is None or target["seq"] >= env.seq:
            raise ProjectionError(f"conflict {p.conflict_id!r}: there is no earlier event to undo")
        if target["type"] == "conflict.opened":
            _change(conn, "conflict", p.conflict_id, env.seq, state="undone", resolution=None)
        elif target["type"] in ("conflict.resolved", "conflict.reopened"):
            earlier = row_as_of(conn, "conflict", p.conflict_id, target["seq"] - 1)
            if earlier is None:
                raise ProjectionError(f"conflict {p.conflict_id!r} had no state before seq {target['seq']}")
            _change(conn, "conflict", p.conflict_id, env.seq, **{
                k: earlier[k] for k in ("state", "resolution", "question_id", "recheck_after")
            })  # fmt: skip
        else:
            raise ProjectionError(f"conflict.undone cannot undo a {target['type']} event")

    # --- goals and questions ----------------------------------------------------------------------------------

    def _on_goal_created(self, conn, env, p):
        self._new_item(conn, env, "goal", p, goal_basis=p.basis, goal_status="active", work_id=p.work_id)

    def _goal(self, conn, item_id: str) -> sqlite3.Row:
        item = _need(conn, "item", item_id)
        if item["kind"] != "goal":
            raise ProjectionError(f"item {item_id!r} is a {item['kind']}, not a goal")
        return item

    def _on_goal_status_changed(self, conn, env, p):
        self._goal(conn, p.item_id)
        _change(conn, "item", p.item_id, env.seq, goal_status=p.to_status)

    def _on_goal_confirmed(self, conn, env, p):
        self._goal(conn, p.item_id)
        _change(conn, "item", p.item_id, env.seq, goal_basis="stated")

    def _on_question_created(self, conn, env, p):
        self._new_item(conn, env, "question", p, raised_by=p.raised_by, question_status="open", answered_by=[])

    def _on_question_status_changed(self, conn, env, p):
        item = _need(conn, "item", p.item_id)
        if item["kind"] != "question":
            raise ProjectionError(f"item {p.item_id!r} is a {item['kind']}, not a question")
        answers = []
        for answer_id in p.answered_by:  # a missing item is an error here, not a foreign-key failure at COMMIT
            if _row(conn, "item", answer_id) is None:
                raise ProjectionError(f"question {p.item_id!r} names {answer_id!r} as its answer, which does not exist")
            _live_item(conn, answer_id)
            answers.append(answer_id)
        _change(conn, "item", p.item_id, env.seq, question_status=p.to_status, answered_by=answers)

    # --- work, working style, corrections, scopes -------------------------------------------------------------

    def _on_work_registered(self, conn, env, p):
        self._new(conn, "work", env.seq, dict(
            id=p.work_id, kind=p.kind, ref=p.ref, project=p.project, label=p.label, label_source=p.label_source,
            evidence=p.evidence, work_event_id=p.work_event_id, snapshot_sha256=p.snapshot_sha256,
            occurred_at=p.occurred_at,
        ))  # fmt: skip

    def _on_work_labelled(self, conn, env, p):
        _change(conn, "work", p.work_id, env.seq, label=p.label, label_source=p.label_source)

    def _on_style_recorded(self, conn, env, p):
        self._new(conn, "style_line", env.seq, dict(id=p.style_id, line=p.line, scope=p.scope, basis=p.basis, status="active"))

    def _on_style_revised(self, conn, env, p):
        changes = {k: v for k, v in (("line", p.line), ("status", p.status)) if v is not None}
        _change(conn, "style_line", p.style_id, env.seq, **changes)

    def _on_correction_applied(self, conn, env, p):
        self._new(conn, "correction", env.seq, dict(
            id=p.correction_id, kind=p.kind, target=p.target, via=p.via, evidence_id=p.evidence_id, params=p.params,
            constraint_rule=p.constraint, at=p.at, status="active", lifted_reason=None,
        ))  # fmt: skip

    def _on_correction_lifted(self, conn, env, p):
        _change(conn, "correction", p.correction_id, env.seq, status="lifted", lifted_reason=p.reason)

    def _on_scope_hold_changed(self, conn, env, p):
        held, held_seq = int(p.held), (env.seq if p.held else None)
        if _row(conn, "scope", p.scope_id) is None:
            kind = p.scope_id.split(":", 1)[0]
            self._new(conn, "scope", env.seq, dict(id=p.scope_id, kind=kind, label=None, held=held, held_seq=held_seq))
        else:
            _change(conn, "scope", p.scope_id, env.seq, held=held, held_seq=held_seq)

    # --- topics and placement ---------------------------------------------------------------------------------

    def _live_topic(self, conn, topic_id: str) -> sqlite3.Row:
        topic = _need(conn, "topic", topic_id)
        if topic["status"] not in ("active", "dormant"):
            raise ProjectionError(f"topic {topic_id!r} is {topic['status']}")
        return topic

    def _on_topic_created(self, conn, env, p):
        if p.parent_id is not None:
            _need(conn, "topic", p.parent_id)
        self._new(conn, "topic", env.seq, dict(
            id=p.topic_id, label=p.label, label_fixed=p.label_fixed, parent_id=p.parent_id, anchor_id=p.anchor_id,
            status="active", redirect_to=None, formation_overlap=p.formation_overlap,
        ))  # fmt: skip

    def _on_topic_split(self, conn, env, p):
        old = self._live_topic(conn, p.topic_id)
        _change(conn, "topic", p.topic_id, env.seq, status="split_into", redirect_to=p.redirect_to)
        for new in p.new_topics:
            self._new(conn, "topic", env.seq, dict(
                id=new["topic_id"], label=new["label"], label_fixed=False, parent_id=old["parent_id"],
                anchor_id=new["anchor_id"], status="active", redirect_to=None, formation_overlap=p.formation_overlap,
            ))  # fmt: skip

    def _on_topic_branched(self, conn, env, p):
        topic = self._live_topic(conn, p.topic_id)
        if topic["parent_id"] != p.old_parent_id:
            raise ProjectionError(f"topic {p.topic_id!r} is not a sub-topic of {p.old_parent_id!r}")
        _change(conn, "topic", p.topic_id, env.seq, parent_id=None)

    def _on_topic_merged(self, conn, env, p):
        self._live_topic(conn, p.from_topic_id)
        _need(conn, "topic", p.into_topic_id)
        _change(conn, "topic", p.from_topic_id, env.seq, status="merged_into", redirect_to=p.into_topic_id)

    def _on_topic_folded_back(self, conn, env, p):
        topic = self._live_topic(conn, p.topic_id)
        if topic["parent_id"] != p.into_parent_id:
            raise ProjectionError(f"topic {p.topic_id!r} is not a sub-topic of {p.into_parent_id!r}")
        _change(conn, "topic", p.topic_id, env.seq, status="folded_into", redirect_to=p.into_parent_id)

    def _on_topic_renamed(self, conn, env, p):
        topic = _need(conn, "topic", p.topic_id)
        _change(conn, "topic", p.topic_id, env.seq, label=p.label, label_fixed=bool(topic["label_fixed"] or p.label_fixed))

    def _on_topic_dormant(self, conn, env, p):
        self._live_topic(conn, p.topic_id)
        _change(conn, "topic", p.topic_id, env.seq, status=p.to_status)

    def _also_in(self, conn, item_id: str, exclude: set[str]) -> int:
        rows = conn.execute("SELECT id FROM placement WHERE item_id = ? AND role = 'also_in'", (item_id,)).fetchall()
        return sum(1 for r in rows if r["id"] not in exclude)

    def _demote_other_home(self, conn, seq: int, item_id: str, keep: set[str]) -> None:
        """The idea is about to get a new home: the old one becomes an also_in place, or goes if there are two."""
        home = conn.execute("SELECT id FROM placement WHERE item_id = ? AND role = 'home'", (item_id,)).fetchone()
        if home is None or home["id"] in keep:
            return
        if self._also_in(conn, item_id, keep) < 2:
            _change(conn, "placement", home["id"], seq, role="also_in")
        else:
            _remove(conn, "placement", home["id"], seq)

    def _on_idea_placed(self, conn, env, p):
        _live_item(conn, p.item_id)
        self._live_topic(conn, p.topic_id)
        place = conn.execute("SELECT * FROM placement WHERE item_id = ? AND topic_id = ?", (p.item_id, p.topic_id)).fetchone()
        if place is None:
            if p.role == "home":
                self._demote_other_home(conn, env.seq, p.item_id, set())
            self._new(conn, "placement", env.seq, dict(
                id=p.placement_id, item_id=p.item_id, topic_id=p.topic_id, role=p.role, tentative=p.tentative,
                reasons=list(p.reasons),
            ))  # fmt: skip
            return
        if p.role == "home":
            self._demote_other_home(conn, env.seq, p.item_id, {place["id"]})
        elif place["role"] == "home" and self._also_in(conn, p.item_id, {place["id"]}) >= 2:
            raise ProjectionError(f"item {p.item_id!r} already has two also_in places")
        _change(conn, "placement", place["id"], env.seq, role=p.role, tentative=p.tentative, reasons=list(p.reasons))

    def _on_idea_moved(self, conn, env, p):
        source = conn.execute("SELECT * FROM placement WHERE item_id = ? AND topic_id = ?", (p.item_id, p.from_topic_id)).fetchone()
        if source is None:
            raise ProjectionError(f"item {p.item_id!r} has no place in topic {p.from_topic_id!r}")
        _live_item(conn, p.item_id)
        self._live_topic(conn, p.to_topic_id)
        target = conn.execute("SELECT * FROM placement WHERE item_id = ? AND topic_id = ?", (p.item_id, p.to_topic_id)).fetchone()
        keep = {source["id"]} | ({target["id"]} if target is not None else set())
        if p.role == "home":
            self._demote_other_home(conn, env.seq, p.item_id, keep)
        elif source["role"] == "home" and self._also_in(conn, p.item_id, keep) >= 2:
            raise ProjectionError(f"item {p.item_id!r} already has two also_in places")
        if target is None:
            _change(conn, "placement", source["id"], env.seq, topic_id=p.to_topic_id, role=p.role, tentative=p.tentative)
            return
        _remove(conn, "placement", source["id"], env.seq)
        role = "home" if "home" in (p.role, target["role"]) else "also_in"
        _change(conn, "placement", target["id"], env.seq, role=role, tentative=p.tentative)

    # --- compensation and purge -------------------------------------------------------------------------------

    def _on_compensation_batch(self, conn, env, p):
        targets: dict[int, str] = {}
        for event_id in p.compensated_event_ids:
            row = conn.execute("SELECT seq, type FROM event WHERE id = ?", (event_id,)).fetchone()
            if row is None or row["seq"] >= env.seq:
                raise ProjectionError(f"compensation.batch names {event_id!r}, which is not an earlier event")
            if row["type"] == "purge.applied":
                raise ProjectionError("a purge cannot be compensated (§3.4)")
            targets[row["seq"]] = event_id
        for target_seq in sorted(targets, reverse=True):
            done = conn.execute(
                "SELECT 1 FROM event WHERE compensates = ? AND seq < ? AND type <> 'compensation.batch'",
                (targets[target_seq], env.seq),
            ).fetchone()
            if done is None:
                revert_event(conn, target_seq, env.seq)
                self._drop_stance(conn, targets[target_seq], env)
        self._check_references(conn)

    def _check_references(self, conn) -> None:
        """A rollback that removes an item must not leave a link, placement, stance, conflict or supersession pointing at
        it: say so now, as a ProjectionError, rather than as a foreign-key failure when the transaction commits."""
        broken = conn.execute("PRAGMA foreign_key_check").fetchall()
        if broken:
            first = broken[0]
            raise ProjectionError(
                f"the batch would leave {first[0]} row {first[1]} pointing at {first[2]} that no longer exists"
                + (f" (and {len(broken) - 1} more)" if len(broken) > 1 else "")
            )

    def _drop_stance(self, conn, event_id: str, env: EventEnvelope) -> None:
        """A stance is append-only and has no row history, but it cannot outlive the item a rollback removes: the
        batch removes the stance its event recorded, under a purge_authorization row named for the batch."""
        if conn.execute("SELECT 1 FROM stance WHERE id = ?", (event_id,)).fetchone() is None:
            return
        conn.execute(
            "INSERT OR IGNORE INTO purge_authorization (tenant_id, purge_id, target_table, target_id, authorized_at)"
            " VALUES (?, ?, 'stance', ?, ?)",
            (self.tenant_id, f"compensation:{env.id}", event_id, env.recorded_at),
        )
        conn.execute("DELETE FROM stance WHERE id = ?", (event_id,))

    def _on_purge_applied(self, conn, env, p):
        stub = PURGE_STUB.format(date=p.requested_at[:10])
        purged = self._purge_set(conn, p.item_ids)
        evidence = self._evidence_of(conn, purged)
        links = self._links_of(conn, purged)
        event_ids = self._event_ids_about(conn, purged | evidence, env.seq)

        def authorize(table: str, ids: set[str]) -> None:
            conn.executemany(
                "INSERT OR IGNORE INTO purge_authorization (tenant_id, purge_id, target_table, target_id, authorized_at)"
                " VALUES (?, ?, ?, ?, ?)",
                [(self.tenant_id, p.purge_id, table, i, p.requested_at) for i in sorted(ids)],
            )

        authorize("item_history", purged)
        authorize("evidence", evidence)
        authorize("evidence_history", evidence)
        authorize("link", links)
        authorize("link_history", links)
        authorize("event", event_ids)

        item_text = {"line": stub, "your_words": "", "why": "", "question_key": ""}
        for item_id in sorted(purged):
            _change(conn, "item", item_id, env.seq, status="purged", **item_text)
        self._scrub_history(conn, "item_history", sorted(purged), item_text)
        for evidence_id in sorted(evidence):
            if _row(conn, "evidence", evidence_id) is not None:
                _change(conn, "evidence", evidence_id, env.seq, quote="")
        self._scrub_history(conn, "evidence_history", sorted(evidence), {"quote": ""})
        for link_id in sorted(links):
            if _row(conn, "link", link_id) is not None:
                _change(conn, "link", link_id, env.seq, reason=stub)
        self._scrub_history(conn, "link_history", sorted(links), {"reason": stub})
        self._scrub_events(conn, event_ids)

    def _purge_set(self, conn, item_ids: Sequence[str]) -> set[str]:
        """The items to purge and, transitively, the items merged into them (their lines are the same idea's text)."""
        purged = set(item_ids)
        for item_id in item_ids:
            _need(conn, "item", item_id)
        frontier = set(purged)
        while frontier:
            found: set[str] = set()
            for chunk in _chunks(sorted(frontier)):
                rows = conn.execute(f"SELECT id FROM item WHERE merged_into IN ({_marks(len(chunk))})", chunk).fetchall()
                found.update(r["id"] for r in rows)
            frontier = found - purged
            purged |= found
        return purged

    def _evidence_of(self, conn, item_ids: set[str]) -> set[str]:
        """Ids of the evidence rows that ever supported these items (current rows and row history)."""
        found: set[str] = set()
        for chunk in _chunks(sorted(item_ids)):
            marks = _marks(len(chunk))
            found.update(r["id"] for r in conn.execute(
                f"SELECT id FROM evidence WHERE subject_kind = 'item' AND subject_id IN ({marks})", chunk))
            found.update(r["id"] for r in conn.execute(
                "SELECT id FROM evidence_history WHERE json_extract(snapshot, '$.subject_kind') = 'item'"
                f" AND json_extract(snapshot, '$.subject_id') IN ({marks})", chunk))
        return found

    def _links_of(self, conn, item_ids: set[str]) -> set[str]:
        """Ids of the links that ever joined these items (current rows and row history)."""
        found: set[str] = set()
        for chunk in _chunks(sorted(item_ids)):
            marks = _marks(len(chunk))
            for column in ("from_id", "to_id"):
                found.update(r["id"] for r in conn.execute(f"SELECT id FROM link WHERE {column} IN ({marks})", chunk))
                found.update(r["id"] for r in conn.execute(
                    f"SELECT id FROM link_history WHERE json_extract(snapshot, '$.{column}') IN ({marks})", chunk))
        return found

    def _event_ids_about(self, conn, subjects: set[str], before_seq: int) -> set[str]:
        found: set[str] = set()
        for chunk in _chunks(sorted(subjects)):
            rows = conn.execute(
                f"SELECT DISTINCT e.id FROM event e, json_each(e.subjects) j WHERE e.seq < ? AND j.value IN ({_marks(len(chunk))})",
                (before_seq, *chunk),
            )
            found.update(r["id"] for r in rows)
        return found

    def _scrub_history(self, conn, table: str, ids: Sequence[str], fields: dict[str, str]) -> None:
        for chunk in _chunks(list(ids)):
            rows = conn.execute(f"SELECT id, seq_from, snapshot FROM {table} WHERE id IN ({_marks(len(chunk))})", chunk)
            for row in rows.fetchall():
                state = json.loads(row["snapshot"])
                scrubbed = {**state, **{k: v for k, v in fields.items() if k in state}}
                if scrubbed != state:
                    conn.execute(
                        f"UPDATE {table} SET snapshot = ? WHERE id = ? AND seq_from = ?",
                        (dump(scrubbed), row["id"], row["seq_from"]),
                    )

    def _scrub_events(self, conn, event_ids: set[str]) -> None:
        """Replace the words in these events' payloads by numbered tokens, the same words by the same token. The
        log then holds no text, but equal and unequal stay what they were, so a replay over the scrubbed log
        compares values the way the live run did (an event is undone only if its fields differ, and so on)."""
        tokens: dict[str, str] = {}
        rows = []
        for chunk in _chunks(sorted(event_ids)):
            rows += conn.execute(
                f"SELECT seq, id, type, payload FROM event WHERE id IN ({_marks(len(chunk))})", chunk
            ).fetchall()
        for row in sorted(rows, key=lambda r: r["seq"]):
            payload = json.loads(row["payload"])
            keys = SCRUBBED_KEYS + (("reason",) if row["type"] in SCRUBBED_LINK_EVENTS else ())
            scrubbed = dict(payload)
            for key in sorted(k for k in keys if isinstance(payload.get(k), str) and payload[k]):
                text = payload[key]
                if not _TOKEN.match(text):
                    scrubbed[key] = tokens.setdefault(text, f"[purged:{len(tokens) + 1}]")
            if scrubbed != payload:
                conn.execute("UPDATE event SET payload = ? WHERE id = ?", (dump(scrubbed), row["id"]))
