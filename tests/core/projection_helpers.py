"""Helpers for the projector, reader and replay tests: append events and project them the way the write gate will.

Every fixture is invented (Robin's energy dashboard, MEMORY-ARCHITECTURE §6).
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from northstar_agent_memory.core import db, events
from northstar_agent_memory.core.events import EventEnvelope
from northstar_agent_memory.core.projector import Projector
from northstar_agent_memory.core.replay import append_event

from .conftest import ACTOR, CONFIG, EXAMPLE_PAYLOADS

START = datetime(2026, 3, 2, 9, 30, tzinfo=timezone.utc)


def stamp(n: int) -> str:
    """The recorded_at of the n-th event: one minute apart, in utc_now's format."""
    return (START + timedelta(minutes=n)).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class Log:
    """Appends events to a memory.db, validates them, and projects them in one transaction per call."""

    def __init__(self, conn, tenant_id: str = db.DEFAULT_TENANT):
        self.conn = conn
        self.tenant_id = tenant_id
        self.projector = Projector(tenant_id)
        self.count = 0
        self.events: list[EventEnvelope] = []

    def envelope(self, type_: str, fields: dict | None = None, *, base: bool = True, **env) -> EventEnvelope:
        """Build a stamped event. `fields` override the type's example payload (or stand alone when base is False)."""
        payload = {**(EXAMPLE_PAYLOADS[type_] if base else {}), **(fields or {})}
        self.count += 1
        envelope = events.make_event(type_, payload, actor=env.pop("actor", ACTOR), config_version=CONFIG, **env)
        envelope.recorded_at = stamp(self.count)
        events.validate(envelope)
        return envelope

    def run(self, *ops, **env) -> list[EventEnvelope]:
        """Append and project several events as one proposal. Each op is a type, or (type, fields), or (type, fields, env)."""
        batch = []
        for op in ops:
            type_, fields, extra = _split(op)
            batch.append(self.envelope(type_, fields, **{**env, **extra}))
        with db.transaction(self.conn):
            for envelope in batch:
                append_event(self.conn, envelope, tenant_id=self.tenant_id)
            self.projector.apply(self.conn, batch)
        self.events += batch
        return batch

    def add(self, type_: str, fields: dict | None = None, **env) -> EventEnvelope:
        return self.run((type_, fields, env))[0]


def _split(op):
    if isinstance(op, str):
        return op, None, {}
    if len(op) == 2:
        return op[0], op[1], {}
    return op


def row(conn, table: str, row_id: str) -> dict | None:
    found = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (row_id,)).fetchone()
    return dict(found) if found is not None else None


def history(conn, table: str, row_id: str) -> list[dict]:
    """The row-history intervals of a row, oldest first, as (seq_from, seq_to, snapshot)."""
    rows = conn.execute(f"SELECT * FROM {table}_history WHERE id = ? ORDER BY seq_from", (row_id,)).fetchall()
    return [{**dict(r), "snapshot": json.loads(r["snapshot"])} for r in rows]


def evidence_op(evidence_id: str, subject_id: str, *, subject_kind: str = "item", **fields):
    """An evidence.anchored op for a subject, by the user, typed."""
    base = dict(evidence_id=evidence_id, subject_kind=subject_kind, subject_id=subject_id, message_id="A1", start_char=0,
                end_char=20, quote="Store readings in SQLite", role="primary", speaker="user", agent=None,
                model_family=None, origin="typed", context="energy-dash")  # fmt: skip
    return "evidence.anchored", {**base, **fields}


def seed_item(log: Log, item_id: str, *, kind: str = "decision", origin: str = "yours", scope: str = "project:energy-dash", **fields):
    """Evidence plus an item citing it, as one proposal. Returns the events."""
    evidence_id = f"ev-{item_id}"
    item = dict(item_id=item_id, kind=kind, line=f"Line of {item_id}", scope=scope, learned_in="A", origin=origin,
                evidence_ids=[evidence_id], said_at="2026-03-02T09:30:00Z")  # fmt: skip
    # the evidence was said where the item was learned, so it adds no second context
    return log.run(evidence_op(evidence_id, item_id, context=item["learned_in"] if "learned_in" not in fields else fields["learned_in"]), ("item.created", {**item, **fields}))


def seed_topic(log: Log, topic_id: str, *, parent_id: str | None = None, anchor_id: str = "m1", **fields):
    return log.add("topic.created", dict(topic_id=topic_id, label=f"Topic {topic_id}", anchor_id=anchor_id, parent_id=parent_id, **fields))
