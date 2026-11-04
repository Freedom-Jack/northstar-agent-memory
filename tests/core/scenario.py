"""One invented chat and the proposals made from it, built only through the ports, for the contract and integration
tests (Robin's meter logger; nothing here reads real chats or the real data root).

The chat: Robin asks for readings in SQLite, the AI suggests keeping raw readings for 14 days and then only daily
averages, and Robin adopts that in his own words. The adopted claim is an item that came from an AI (§5.9).
"""

from __future__ import annotations

from northstar_agent_memory.core import events
from northstar_agent_memory.core.events import EventEnvelope
from northstar_agent_memory.core.gate import FULL_RULES
from northstar_agent_memory.core.ports import ModelCall, Proposal, Verdict
from northstar_agent_memory.transcript import Message, Source

CONFIG = "config-scenario-1"
SOURCE_ID = "LOG1"
SCOPE = "project:meter-logger"
SAID = "2026-04-06T08:15:00Z"
WORK_FAMILY = "claude"  # the family of the AI that did the work, and of the AI turn
CHECKER = "openai"  # the other family, which checks
PROMPT_HASH = "c0ffee1"
ACTOR = f"model:extract@1#{PROMPT_HASH}"

TEXTS = [
    ("user", "typed", "Let's log the meter readings to SQLite, one file per meter."),
    ("assistant", "assistant_output", "I suggest keeping raw readings for 14 days and then storing only daily averages."),
    ("user", "typed", "Yes, keep raw readings for 14 days and then only daily averages."),
    ("user", "typed", "I want a weekly summary email every Monday."),
]


def message_id(ordinal: int) -> str:
    return f"{SOURCE_ID}:{ordinal}"


def said_at(ordinal: int) -> str:
    """When the invented message was said: an item's said_at is the time of the message of yours it cites (I16)."""
    return f"2026-04-06T08:{10 + ordinal:02d}:00+00:00"


def source() -> Source:
    messages = [
        Message(
            id=message_id(n), source_id=SOURCE_ID, ordinal=n, speaker=speaker, text=text, origin=origin,  # type: ignore[arg-type]
            occurred_at=said_at(n),
            agent="claude-code" if speaker == "assistant" else None,
            model_family=WORK_FAMILY if speaker == "assistant" else None,
        )
        for n, (speaker, origin, text) in enumerate(TEXTS)
    ]
    return Source(id=SOURCE_ID, kind="chat", app="claude-code", project="meter-logger", started_at=SAID, messages=messages)


def load_history(history) -> Source:
    """Add the source and every message through the HistoryStore port."""
    chat = source()
    history.add_source(chat, scope=SCOPE)
    for message in chat.messages:
        history.append_message(message)
    return chat


def start_run(runs) -> str:
    """A running run, with the model call its proposals name by prompt hash recorded first (§5.12)."""
    run_id = runs.start_run("manual")
    runs.record_call(ModelCall("test-provider", "test-model", WORK_FAMILY, PROMPT_HASH, [message_id(0)], run_id=run_id, raw_output="{}"))
    return run_id


def op(type_: str, payload: dict, *, actor: str = ACTOR) -> EventEnvelope:
    return events.make_event(type_, payload, actor=actor, config_version=CONFIG)


def span(ordinal: int, quote: str) -> tuple[int, int]:
    start = TEXTS[ordinal][2].index(quote)
    return start, start + len(quote)


def evidence(evidence_id: str, subject_id: str, ordinal: int, quote: str, role: str) -> EventEnvelope:
    start, end = span(ordinal, quote)
    return op(
        "evidence.anchored",
        dict(evidence_id=evidence_id, subject_kind="item", subject_id=subject_id, message_id=message_id(ordinal),
             start_char=start, end_char=end, quote=quote, role=role, lineage="primary"),
    )  # fmt: skip


def adopted_ops(item_id: str = "m1") -> list[EventEnvelope]:
    """An item from the AI's suggestion and your adoption of it: two evidence spans, then the item."""
    ai_id, you_id = f"ev-{item_id}-ai", f"ev-{item_id}-you"
    return [
        evidence(ai_id, item_id, 1, "keeping raw readings for 14 days", "primary"),
        evidence(you_id, item_id, 2, "keep raw readings for 14 days", "adoption"),
        op("item.created", dict(
            item_id=item_id, kind="decision", line="Raw readings are kept for 14 days, then only daily averages",
            scope=SCOPE, learned_in=SOURCE_ID, said_at=said_at(2), evidence_ids=[ai_id, you_id],
        )),
    ]  # fmt: skip


def yours_ops(item_id: str = "m2") -> list[EventEnvelope]:
    """An item from your own words alone."""
    ev = f"ev-{item_id}"
    return [
        evidence(ev, item_id, 0, "log the meter readings to SQLite", "primary"),
        op("item.created", dict(
            item_id=item_id, kind="decision", line="Meter readings are logged to SQLite, one file per meter",
            scope=SCOPE, learned_in=SOURCE_ID, said_at=said_at(0), evidence_ids=[ev],
        )),
    ]  # fmt: skip


def checked(family: str = CHECKER, *, rules=FULL_RULES, outcome: str = "pass", independent: bool = True) -> Verdict:
    return Verdict(family, list(rules), outcome, independent)  # type: ignore[arg-type]


def proposal(run_id: str, ops: list[EventEnvelope], *, verdicts: list[Verdict] | None = None, inputs=()) -> Proposal:
    """A proposal with the check its tier needs: a full check by the other family, unless `verdicts` says otherwise."""
    made = Proposal.build(run_id, ops, inputs=inputs)
    made.verdicts = [checked()] if verdicts is None else list(verdicts)
    return made


def record(runs, proposal: Proposal) -> Proposal:
    """What the maintenance stage does before the gate sees a proposal: save it in runs.db with the verdicts the checker
    recorded for it, each naming a recorded call of its family in this run (the gate reads verdicts from there)."""
    for verdict in proposal.verdicts:
        if verdict.model_call_id is None:
            prompt_hash = f"check-{verdict.checker_family}"
            known = [c for c in runs.calls(proposal.run_id) if c["prompt_hash"] == prompt_hash]
            verdict.model_call_id = known[0]["id"] if known else runs.record_call(
                ModelCall("test-provider", "test-model", verdict.checker_family, prompt_hash, [message_id(0)], run_id=proposal.run_id, raw_output="{}")
            )
    runs.save_proposal(proposal)
    return proposal


class Recorded:
    """A write gate that records each proposal in runs.db first, as the maintenance stage does, then applies it."""

    def __init__(self, gate, runs) -> None:
        self.gate, self.runs = gate, runs

    def apply(self, proposal: Proposal):
        return self.gate.apply(record(self.runs, proposal))

    def apply_user(self, proposal: Proposal, authority):
        return self.gate.apply_user(record(self.runs, proposal), authority)
