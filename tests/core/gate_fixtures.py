"""Fixtures for the write gate and invariant tests: a minimal fake projector, an invented chat history, and builders
that make valid proposals. Every message is invented (Robin's energy dashboard, MEMORY-ARCHITECTURE §6); nothing here
reads real chats or the real data root. The fake projector stands in for the real one: it writes only the rows the
gate's checks read (evidence, items, links, corrections, stances, style lines)."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

import pytest

from northstar_agent_memory.core import db, events
from northstar_agent_memory.core.events import EventEnvelope
from northstar_agent_memory.core.gate import FULL_RULES, UserAuthority, WriteGate
from northstar_agent_memory.core.history import SQLiteHistoryStore
from northstar_agent_memory.core.ports import ApplyResult, ModelCall, Proposal, Verdict
from northstar_agent_memory.core.projector import Projector
from northstar_agent_memory.core.runs import SQLiteRunStore
from northstar_agent_memory.transcript import Message, Source

CONFIG = "config-test-1"
NOW = "2026-03-05T12:00:00.000Z"
SAID = "2026-03-02T09:30:00Z"
SCOPE = "project:energy-dash"
WORK_FAMILY = "claude"  # the family that does the work in these tests
CHECKER = "openai"  # the other family, which checks it
PROMPT_HASH = "9f2c1ab"
AUTO = "auto-call"  # a verdict made with this call id gets a recorded call of its family in its proposal's run
YOU = UserAuthority(surface="ui", user_action=True)  # what your overview hands the gate for a click of yours


class FakeProjector:
    """Writes the current-state rows the gate's checks read, and nothing else. Unknown event types are ignored."""

    def apply(self, conn: sqlite3.Connection, envelopes: Sequence[EventEnvelope]) -> None:
        for env in envelopes:
            handler = getattr(self, "on_" + env.type.replace(".", "_"), None)
            if handler:
                handler(conn, env)

    def on_evidence_anchored(self, conn, env):
        p = env.payload
        conn.execute(
            "INSERT INTO evidence (id, subject_kind, subject_id, message_id, start_char, end_char, quote, role, speaker, agent,"
            " model_family, origin, lineage, created_seq, seq_from) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                p["evidence_id"], p["subject_kind"], p["subject_id"], p["message_id"], p["start_char"], p["end_char"], p["quote"],
                p["role"], p["speaker"], p["agent"], p["model_family"], p["origin"], p["lineage"], env.seq, env.seq,
            ),
        )  # fmt: skip

    def _new_item(self, conn, env, kind, **extra):
        p = env.payload
        adopted = p["origin"].startswith("adopted:")
        conn.execute(
            "INSERT INTO item (id, version, kind, class, line, your_words, why, question_key, scope, applies_when, learned_in,"
            " origin, check_status, said_at, valid_from, valid_to, recorded_at, time_bound, goal_basis, goal_status, work_id,"
            " raised_by, question_status, created_seq, seq_from) VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,"
            " ?, ?, ?, ?, ?, ?, ?)",
            (
                p["item_id"], kind, events.ITEM_CLASS_OF_KIND[kind], p["line"], p.get("your_words", ""), p.get("why", ""),
                p.get("question_key", ""), p["scope"], p.get("applies_when", "unknown"), p["learned_in"], p["origin"],
                "unchecked" if adopted else "not_needed", p["said_at"], p.get("valid_from"), p.get("valid_to"), env.recorded_at,
                int(p.get("time_bound", False)), extra.get("goal_basis"), "active" if kind == "goal" else None,
                p.get("work_id"), extra.get("raised_by"), "open" if kind == "question" else None, env.seq, env.seq,
            ),
        )  # fmt: skip

    def on_item_created(self, conn, env):
        self._new_item(conn, env, env.payload["kind"])

    def on_goal_created(self, conn, env):
        self._new_item(conn, env, "goal", goal_basis=env.payload["basis"])

    def on_question_created(self, conn, env):
        self._new_item(conn, env, "question", raised_by=env.payload["raised_by"])

    def _change(self, conn, env, item_id, sql, args=()):
        db.archive_row(conn, "item", item_id, env.seq)
        conn.execute(f"UPDATE item SET {sql}, seq_from = ? WHERE id = ?", (*args, env.seq, item_id))

    def on_item_revised(self, conn, env):
        self._change(conn, env, env.payload["item_id"], "line = ?, version = version + 1", (env.payload["line"],))

    def on_item_status_changed(self, conn, env):
        self._change(conn, env, env.payload["item_id"], "status = ?", (env.payload["to_status"],))

    def on_item_value_changed(self, conn, env):
        self._change(conn, env, env.payload["item_id"], "value = 'kept'")

    def on_item_scope_widened(self, conn, env):
        self._change(conn, env, env.payload["item_id"], "scope = 'personal', version = version + 1")

    def on_goal_status_changed(self, conn, env):
        self._change(conn, env, env.payload["item_id"], "goal_status = ?", (env.payload["to_status"],))

    def on_supersession_applied(self, conn, env):
        p = env.payload
        conn.execute(
            "INSERT INTO supersession (id, old_item, old_version, new_item, new_version, reason, evidence_ids, at, created_seq, seq_from)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (p["supersession_id"], p["old_item"], p["old_version"], p["new_item"], p.get("new_version"), p["reason"],
             json.dumps(p["evidence_ids"]), env.recorded_at, env.seq, env.seq),
        )  # fmt: skip
        if p["old_item"] != p["new_item"]:
            self._change(conn, env, p["old_item"], "status = 'superseded'")

    def _link(self, conn, env, status):
        p = env.payload
        conn.execute(
            "INSERT INTO link (id, from_id, to_id, to_kind, type, reason, stated_by, status, checked_by, created_seq, seq_from)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (p["link_id"], p["from_id"], p["to_id"], p["to_kind"], p["link_type"], p["reason"], p["stated_by"], status,
             json.dumps(p["checked_by"]), env.seq, env.seq),
        )  # fmt: skip
        if status == "applied" and p["link_type"] == "same_as":
            self._change(conn, env, p["from_id"], "status = 'superseded', merged_into = ?", (p["to_id"],))

    def on_link_applied(self, conn, env):
        self._link(conn, env, "applied")

    def on_link_proposed(self, conn, env):
        self._link(conn, env, "proposed")

    def _link_status(self, conn, env, status):
        conn.execute("UPDATE link SET status = ?, seq_from = ? WHERE id = ?", (status, env.seq, env.payload["link_id"]))

    def on_link_confirmed(self, conn, env):
        self._link_status(conn, env, "confirmed")

    def on_link_rejected(self, conn, env):
        self._link_status(conn, env, "rejected")

    def on_link_retracted(self, conn, env):
        self._link_status(conn, env, "retracted")

    def on_correction_applied(self, conn, env):
        p = env.payload
        conn.execute(
            "INSERT INTO correction (id, kind, target, via, evidence_id, params, constraint_rule, at, created_seq, seq_from)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (p["correction_id"], p["kind"], p["target"], p["via"], p.get("evidence_id"), json.dumps(p["params"]),
             json.dumps(p["constraint"]), p["at"], env.seq, env.seq),
        )  # fmt: skip

    def on_stance_recorded(self, conn, env):
        p = env.payload
        conn.execute(
            "INSERT INTO stance (id, item_id, stance, evidence_ids, created_seq) VALUES (?, ?, ?, ?, ?)",
            (env.id, p["item_id"], p["stance"], json.dumps(p["evidence_ids"]), env.seq),
        )

    def on_style_recorded(self, conn, env):
        p = env.payload
        conn.execute(
            "INSERT INTO style_line (id, line, scope, basis, created_seq, seq_from) VALUES (?, ?, ?, ?, ?, ?)",
            (p["style_id"], p["line"], p["scope"], p["basis"], env.seq, env.seq),
        )


class RaisingProjector:
    """A projector whose store refuses the change, after the gate has appended the events."""

    def apply(self, conn, envelopes):
        conn.execute("INSERT INTO item (id) VALUES ('broken')")  # violates NOT NULL


# --- the invented chat history --------------------------------------------------------------------------------------

M = {
    "S1:0": ("user", "typed", "Let's keep one SQLite file per meter. Hourly averages are enough for the monthly charts."),
    "S1:1": ("assistant", "assistant_output", "I suggest keeping 1-minute readings for 7 days, then downsampling to hourly averages."),
    "S1:2": ("user", "typed", "Yes, do that: keep the 1-minute readings for 7 days and downsample after."),
    "S1:3": ("user", "typed", "I want an alert when running the dryer costs double."),
    "S1:4": ("tool", "tool_output", "pytest: 12 passed in 0.8s"),
    "S1:5": ("user", "pasted", "Notes pasted from my notebook: the Pi Zero keeps up with six sensors."),
    "S1:6": ("user", "typed", "Keep the weekly report short. Always put the totals first."),
    "S2:0": ("user", "model_reported", "I said the dryer alert should fire when the cost doubles."),
    "S2:1": ("assistant", "assistant_output", "Consider a rolling baseline for the alerts instead of a fixed limit."),
    "S2:2": ("user", "typed", "A rolling baseline is a good idea, let's use it for the alerts."),
    "S3:0": ("user", "typed", "In my own projects I keep data in local files first."),
    "S3:1": ("user", "typed", "Local files first also holds for my notes."),
    "P1:0": ("user", "typed", "In the course project I also keep data in local files first."),
    "N1:0": ("northstar", "northstar_injected", "Earlier you decided that hourly averages are enough."),
}
TIME = {mid: f"2026-03-02T09:{n:02d}:00+00:00" for n, mid in enumerate(M)}  # when each invented message was said
TIME["S3:1"] = "2026-03-04T10:00:00+00:00"  # two days later: your words on a later day
PROJECT = {"S3": None, "P1": "de-course", "N1": None}  # a source's project; the rest are in "energy-dash"
SOURCES = {  # id -> (kind, scope, app)
    "S1": ("chat", SCOPE, "claude-code"),
    "S2": ("chat", SCOPE, "chat-app"),
    "S3": ("chat", "personal", "chat-app"),
    "P1": ("chat", "project:de-course", "claude-code"),
    "N1": ("northstar_output", "personal", "northstar"),
}
FAMILY = {"claude-code": "claude", "chat-app": "openai"}  # app -> the family of its AI turns


@dataclass
class World:
    """Stores under a throwaway root, an invented history, a run store, and a gate on a fake projector."""

    root: Path
    conns: dict[str, sqlite3.Connection]
    history: SQLiteHistoryStore
    runs: SQLiteRunStore
    gate: WriteGate
    run_id: str
    actor: str
    counter: int = 0
    texts: dict[str, str] = field(default_factory=dict)
    calls: dict[tuple[str, str], str] = field(default_factory=dict)

    @property
    def memory(self) -> sqlite3.Connection:
        return self.conns["memory"]

    def close(self) -> None:
        self.history.close()
        for conn in self.conns.values():
            conn.close()

    # --- builders ---

    def next(self, prefix: str = "x") -> str:
        self.counter += 1
        return f"{prefix}{self.counter}"

    def call_for(self, family: str, run_id: str) -> str:
        """A recorded model call of this family in this run (one per family and run), for a verdict to name."""
        key = (run_id, family)
        if key not in self.calls:
            self.calls[key] = self.runs.record_call(
                ModelCall("test-provider", "test-model", family, f"check-{family}-{len(self.calls)}", ["S1:0"], run_id=run_id, raw_output="{}")
            )
        return self.calls[key]

    def op(self, type_: str, payload: dict[str, Any] | None = None, *, actor: str | None = None, **fields) -> EventEnvelope:
        return events.make_event(type_, dict(payload or {}), actor=actor or self.actor, config_version=CONFIG, **fields)

    def span(self, message_id: str, quote: str) -> tuple[int, int]:
        text = M[message_id][2]
        start = text.index(quote)
        return start, start + len(quote)

    def evidence(
        self, eid: str, subject_id: str, message_id: str, quote: str, role: str = "primary", subject_kind: str = "item",
        lineage: str = "primary", actor: str | None = None,
    ) -> EventEnvelope:
        start, end = self.span(message_id, quote)
        return self.op(
            "evidence.anchored",
            dict(evidence_id=eid, subject_kind=subject_kind, subject_id=subject_id, message_id=message_id, start_char=start,
                 end_char=end, quote=quote, role=role, lineage=lineage),
            actor=actor,
        )  # fmt: skip

    def item_ops(
        self, item_id: str, line: str, parts: Sequence[tuple[str, str, str]], *, kind: str = "decision", scope: str = SCOPE,
        type_: str = "item.created", **payload,
    ) -> list[EventEnvelope]:
        """Evidence ops, then the creating op. `parts` are (message id, quote, role)."""
        ids = [f"ev-{item_id}-{n}" for n in range(len(parts))]
        ops = [self.evidence(eid, item_id, mid, quote, role) for eid, (mid, quote, role) in zip(ids, parts)]
        yours = [(m, role) for m, _, role in parts if M[m][0] == "user"]
        said = next((TIME[m] for m, role in yours if role == "adoption"), TIME[yours[0][0]] if yours else SAID)  # the message of yours it cites
        base: dict[str, Any] = dict(item_id=item_id, line=line, scope=scope, learned_in=yours[0][0].split(":")[0] if yours else "S1", said_at=said, evidence_ids=ids)
        if type_ == "item.created":
            base["kind"] = kind
        base.update(payload)
        ops.append(self.op(type_, base))
        return ops

    def yours(self, item_id: str | None = None, line: str = "Readings are stored in SQLite, one file per meter", **kw) -> list[EventEnvelope]:
        item_id = item_id or self.next("m")
        return self.item_ops(item_id, line, [("S1:0", "keep one SQLite file per meter", "primary")], **kw)

    def adopted(self, item_id: str | None = None, line: str = "Readings older than 7 days are kept as hourly averages", **kw) -> list[EventEnvelope]:
        item_id = item_id or self.next("m")
        parts = [("S1:1", "keeping 1-minute readings for 7 days", "primary"), ("S1:2", "keep the 1-minute readings for 7 days", "adoption")]
        return self.item_ops(item_id, line, parts, **kw)

    def goal(self, item_id: str | None = None, message_id: str = "S1:3", quote: str = "an alert when running the dryer costs double", basis: str = "stated") -> list[EventEnvelope]:
        item_id = item_id or self.next("g")
        return self.item_ops(
            item_id, "Alert when running the dryer costs double", [(message_id, quote, "primary")], kind="goal",
            type_="goal.created", basis=basis,
        )  # fmt: skip

    def verdict(self, family: str = CHECKER, *, full: bool = True, outcome: str = "pass", independent: bool = True, rules=None, call: str | None = AUTO) -> Verdict:
        """A verdict. By default it names a call of its family that the proposal's run records when it is submitted;
        `call=None` is a verdict that names no call, and an id names that call."""
        listed = list(rules) if rules is not None else (list(FULL_RULES) if full else ["meaning_both_ways"])
        return Verdict(family, listed, outcome, independent, call)  # type: ignore[arg-type]

    def proposal(self, ops: list[EventEnvelope], *, verdicts: Sequence[Verdict] | None = None, inputs: Sequence[str] = (), run_id: str | None = None) -> Proposal:
        """A proposal with the checks its tier needs (a full check by the other family), unless `verdicts` says otherwise.
        The verdicts are on the proposal, as a stage would carry them; `submit` records them in runs.db."""
        proposal = Proposal.build(run_id or self.run_id, ops, inputs=inputs)
        proposal.verdicts = [self.verdict()] if verdicts is None else list(verdicts)
        return proposal

    def plant(self, proposal: Proposal, verdict: Verdict, *, at: str = NOW) -> None:
        """Put a verdict straight into runs.db, past the run store's own checks: what a damaged or tampered runs.db holds."""
        self.record(proposal)
        if verdict.model_call_id == AUTO:
            verdict.model_call_id = self.call_for(verdict.checker_family, proposal.run_id)
        with db.transaction(self.runs.conn):
            self.runs.conn.execute(
                "INSERT INTO verdict (tenant_id, id, proposal_id, checker_family, rules, outcome, independent, model_call_id, notes, at)"
                " VALUES ('local', ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (verdict.id, proposal.proposal_id, verdict.checker_family, json.dumps(verdict.rules), verdict.outcome,
                 int(verdict.independent), verdict.model_call_id, verdict.notes, at),
            )  # fmt: skip

    def record(self, proposal: Proposal) -> Proposal:
        """What the maintenance stage does before the gate sees a proposal: save it in runs.db with the verdicts the
        checker recorded for it, each naming its own recorded call."""
        if self.runs is not None and self.runs.get_run(proposal.run_id) is not None:
            for v in proposal.verdicts:
                if v.model_call_id == AUTO:
                    v.model_call_id = self.call_for(v.checker_family, proposal.run_id)
            self.runs.save_proposal(proposal)
        return proposal

    def submit(self, proposal: Proposal) -> ApplyResult:
        return self.gate.apply(self.record(proposal))

    def apply(self, ops: list[EventEnvelope], **kw) -> ApplyResult:
        return self.submit(self.proposal(ops, **kw))

    def apply_user(self, ops: list[EventEnvelope], **kw) -> ApplyResult:
        """Ops of yours (the actor `user`) through your authority: no verdict is needed."""
        kw.setdefault("verdicts", [])
        return self.gate.apply_user(self.record(self.proposal(ops, **kw)), YOU)

    def applied(self, ops: list[EventEnvelope], **kw) -> ApplyResult:
        result = self.apply(ops, **kw)
        assert result.status == "applied", result
        return result

    def applied_user(self, ops: list[EventEnvelope], **kw) -> ApplyResult:
        result = self.apply_user(ops, **kw)
        assert result.status == "applied", result
        return result

    def raw_item(self, item_id: str, line: str | None = None, scope: str = SCOPE, kind: str = "decision", version: int = 1) -> None:
        """Insert an active item row directly, for tests that need many items without applying a proposal each."""
        with db.transaction(self.memory):
            self.memory.execute(
                "INSERT INTO item (id, version, kind, class, line, scope, learned_in, origin, said_at, recorded_at, created_seq, seq_from)"
                " VALUES (?, ?, ?, 'fact', ?, ?, 'S1', 'yours', ?, ?, 0, 0)",
                (item_id, version, kind, line or f"line of {item_id}", scope, SAID, SAID),
            )

    def pad(self, n: int, prefix: str = "pad-") -> list[str]:
        """Insert n active item rows in one transaction, so a run's loss bound has something to be a share of."""
        ids = [f"{prefix}{i}" for i in range(n)]
        with db.transaction(self.memory):
            self.memory.executemany(
                "INSERT INTO item (id, version, kind, class, line, scope, learned_in, origin, said_at, recorded_at, created_seq, seq_from)"
                " VALUES (?, 1, 'decision', 'fact', ?, ?, 'S1', 'yours', ?, ?, 0, 0)",
                [(i, f"padding line {i}", SCOPE, SAID, SAID) for i in ids],
            )
        return ids

    def count(self, table: str, where: str = "1=1") -> int:
        return self.memory.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}").fetchone()[0]


def make_world(root: Path, *, config: dict | None = None, with_runs: bool = True, projector=None) -> World:
    conns = {name: db.open_store(name, root) for name in db.STORES}
    history = SQLiteHistoryStore(root)
    by_source: dict[str, list[Message]] = {}
    for ordinal, (mid, (speaker, origin, text)) in enumerate(M.items()):
        source_id = mid.split(":")[0]
        app = SOURCES[source_id][2]
        by_source.setdefault(source_id, []).append(
            Message(
                id=mid, source_id=source_id, ordinal=int(mid.split(":")[1]), speaker=speaker, text=text, origin=origin,  # type: ignore[arg-type]
                occurred_at=TIME[mid], agent=app if speaker != "user" else None,
                model_family=FAMILY.get(app) if speaker == "assistant" else None,
            )
        )  # fmt: skip
    for source_id, (kind, scope, app) in SOURCES.items():
        history.add_source(Source(id=source_id, kind=kind, app=app, project=PROJECT.get(source_id, "energy-dash"), started_at=NOW), scope=scope)  # type: ignore[arg-type]
        for message in by_source[source_id]:
            history.append_message(message, fidelity="model_reported" if message.origin == "model_reported" else "verbatim")
    runs = SQLiteRunStore(conns["runs"])
    run_id = runs.start_run("manual")
    runs.record_call(ModelCall("test-provider", "test-model", WORK_FAMILY, PROMPT_HASH, ["S1:0"], run_id=run_id, raw_output="{}"))
    gate = WriteGate(
        conns["memory"], history, projector or FakeProjector(), runs=runs if with_runs else None,
        config={} if config is None else config, clock=lambda: NOW,
    )  # fmt: skip
    return World(root, conns, history, runs, gate, run_id, f"model:extract@1#{PROMPT_HASH}")


@pytest.fixture(params=["fake", "real"])
def varied(request, store_root):
    """The gate on the fake projector and on the real one: what the gate accepts, the projector must be able to apply."""
    projector = FakeProjector() if request.param == "fake" else Projector()
    w = make_world(store_root, projector=projector)
    yield w
    w.close()


@pytest.fixture
def world(store_root):
    w = make_world(store_root)
    yield w
    w.close()
