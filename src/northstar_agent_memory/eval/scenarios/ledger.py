"""The world ledger: a synthetic person's chats and the hidden record that holds the truth
(note 09, Implications §3, §5, §6; DESIGN §8, "The harness, built first").

A World is a persona, the sessions they had (oldest first), the gold memories and gold
updates that a memory system should end up with, and probes: questions with checkpoints.
Probes come from the ledger, not the text, so most scoring is done by code. `haystack_for`
gives the history up to a probe's checkpoint, so the same probe can be asked of any system.

Probe metadata: `after_message_id` (the checkpoint), `scenario` ("S1".."S18") and `kind`
(also the item's question_type). Optional: `forbidden_terms` (words an answer must not
contain), `staleness_expected` (the answer should say the topic may be out of date).
"""

from __future__ import annotations

import copy
import json
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timedelta
from pathlib import Path

from northstar_agent_memory.eval.scenarios.library import BY_ID, PROBE_KINDS, SCENARIOS
from northstar_agent_memory.eval.types import GoldMemory, GoldUpdate, QAItem
from northstar_agent_memory.models.port import FAMILIES
from northstar_agent_memory.transcript import Message, Source, message_index, source_from_dict

# MEMORY-ARCHITECTURE §2.4. A plain fact about the person is a "definition".
KINDS = (
    "decision",
    "ruled_out",
    "result",
    "conclusion",
    "definition",
    "plan",
    "principle",
    "approach",
    "position",
    "goal",
    "question",
)
HOLDERS = ("user", "other_person", "ai_unadopted", "hypothetical")
SPEAKERS = ("user", "assistant")
MINUTES_PER_MESSAGE = 2


@dataclass(slots=True)
class Project:
    id: str
    name: str
    description: str
    kind: str = "personal"  # "work" | "personal"


@dataclass(slots=True)
class Persona:
    name: str  # invented; referred to as they/them
    summary: str
    projects: list[Project] = field(default_factory=list)
    traits: list[str] = field(default_factory=list)  # the messiness the sessions carry


@dataclass(slots=True)
class World:
    id: str
    persona: Persona
    sessions: list[Source]  # oldest first
    gold_memories: list[GoldMemory]
    gold_updates: list[GoldUpdate]
    probes: list[QAItem]  # haystack left empty; see haystack_for
    tags: dict[str, list[str]] = field(default_factory=dict)  # memory key, update key or probe id -> scenarios
    meta: dict = field(default_factory=dict)


# --- JSON ------------------------------------------------------------------------------


def world_to_dict(world: World) -> dict:
    return asdict(world)


def world_from_dict(data: dict) -> World:
    persona = data["persona"]
    return World(
        id=data["id"],
        persona=Persona(
            name=persona["name"],
            summary=persona.get("summary", ""),
            projects=[Project(**p) for p in persona.get("projects", [])],
            traits=list(persona.get("traits", [])),
        ),
        sessions=[source_from_dict(s) for s in data["sessions"]],
        gold_memories=[GoldMemory(**m) for m in data["gold_memories"]],
        gold_updates=[GoldUpdate(**u) for u in data["gold_updates"]],
        probes=[QAItem(**{**p, "haystack": [source_from_dict(s) for s in p.get("haystack", [])]}) for p in data["probes"]],
        tags={k: list(v) for k, v in data.get("tags", {}).items()},
        meta=dict(data.get("meta", {})),
    )


def save_world(world: World, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(world_to_dict(world), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def load_world(path: Path) -> World:
    return world_from_dict(json.loads(path.read_text(encoding="utf-8")))


def source_from_script(data: dict) -> Source:
    """Expand a compact hand-written session into a Source.

    `messages` is a list of [speaker, text] or [speaker, text, extras]; extras may hold
    `origin`, `at`, `model_family`. Ids are "<id>:<ordinal>"; times run from `started_at`;
    assistant turns take the session's `agent` and `model_family`.
    """
    sid = data["id"]
    start = datetime.fromisoformat(data["started_at"])
    app = data.get("app")
    messages = []
    for i, row in enumerate(data["messages"]):
        speaker, text = row[0], row[1]
        extras = row[2] if len(row) > 2 else {}
        assistant = speaker == "assistant"
        messages.append(
            Message(
                id=f"{sid}:{i}",
                source_id=sid,
                ordinal=i,
                speaker=speaker,
                text=text,
                occurred_at=extras.get("at") or (start + timedelta(minutes=MINUTES_PER_MESSAGE * i)).isoformat(),
                origin=extras.get("origin", "assistant_output" if assistant else "typed"),
                agent=data.get("agent", app) if assistant else None,
                model_family=extras.get("model_family", data.get("model_family")) if assistant else None,
            )
        )
    return Source(
        id=sid,
        kind=data.get("kind", "chat"),
        app=app,
        project=data.get("project"),
        title=data.get("title"),
        started_at=data["started_at"],
        messages=messages,
    )


def memory_from_script(spec: dict) -> tuple[GoldMemory, list[str]]:
    """A gold memory from its compact form, with its scenario tags.

    Keys: key, line, kind, evidence; optional holder ("user"), must_record (true),
    scope ("personal"), adopted_from, meta, scenarios.
    """
    memory = GoldMemory(
        key=spec["key"],
        line=spec["line"],
        kind=spec["kind"],
        holder=spec.get("holder", "user"),
        evidence_message_ids=list(spec["evidence"]),
        must_record=spec.get("must_record", True),
        scope=spec.get("scope", "personal"),
        adopted_from=spec.get("adopted_from"),
        meta=dict(spec.get("meta", {})),
    )
    return memory, list(spec.get("scenarios", []))


def update_from_script(spec: dict) -> tuple[GoldUpdate, list[str]]:
    """A gold update from its compact form: key, old, new, at, reason, scenarios."""
    update = GoldUpdate(
        key=spec["key"],
        old_key=spec["old"],
        new_key=spec["new"],
        at_message_id=spec["at"],
        reason=spec["reason"],
    )
    return update, list(spec.get("scenarios", []))


def probe_from_script(world_id: str, spec: dict) -> tuple[QAItem, list[str]]:
    """A probe from its compact form, with its scenario tags (the probe's own scenario first).

    Keys: id, question, answer, kind, scenario, after (the checkpoint message id), evidence;
    optional meta (extra probe metadata), scenarios (further tags), question_date.
    """
    kind = spec["kind"]
    probe = QAItem(
        id=spec["id"],
        dataset=f"scenario:{world_id}",
        question=spec["question"],
        gold_answer=spec["answer"],
        question_type=kind,
        haystack=[],
        evidence_message_ids=list(spec.get("evidence", [])),
        question_date=spec.get("question_date"),
        abstention=kind == "abstention",
        meta={**spec.get("meta", {}), "after_message_id": spec["after"], "scenario": spec["scenario"], "kind": kind},
    )
    tags = [spec["scenario"], *[s for s in spec.get("scenarios", []) if s != spec["scenario"]]]
    return probe, tags


# --- order and haystacks -----------------------------------------------------------------


def message_order(world: World) -> dict[str, int]:
    """Position of each message in the whole history."""
    return {m.id: i for i, m in enumerate(m for s in world.sessions for m in s.messages)}


def haystack_for(world: World, probe: QAItem) -> list[Source]:
    """The sessions up to the probe's checkpoint; the checkpoint session stops after it."""
    checkpoint = probe.meta["after_message_id"]
    out: list[Source] = []
    for session in world.sessions:
        ids = [m.id for m in session.messages]
        if checkpoint in ids:
            kept = copy.deepcopy(session)
            kept.messages = kept.messages[: ids.index(checkpoint) + 1]
            out.append(kept)
            return out
        out.append(copy.deepcopy(session))
    raise KeyError(f"checkpoint {checkpoint!r} is not in the world")


def ask(world: World, probe: QAItem) -> QAItem:
    """The probe with its haystack filled in, ready to give to a system."""
    return replace(probe, haystack=haystack_for(world, probe))


def fill_question_dates(world: World) -> None:
    """Give each probe without a question date the time of its checkpoint message."""
    index = message_index(world.sessions)
    for probe in world.probes:
        if probe.question_date is None:
            message = index.get(probe.meta.get("after_message_id", ""))
            if message is not None:
                probe.question_date = message.occurred_at


def coverage(world: World) -> dict[str, int]:
    """How many gold elements and probes carry each scenario tag."""
    counts = {s.id: 0 for s in SCENARIOS}
    for scenarios in world.tags.values():
        for sid in scenarios:
            if sid in counts:
                counts[sid] += 1
    return counts


# --- validation ----------------------------------------------------------------------------


def validate(world: World) -> list[str]:
    """Everything wrong with a world, as plain sentences; an empty list means it is sound."""
    problems: list[str] = []
    if not world.id:
        problems.append("the world has no id")
    if not world.persona.name.strip():
        problems.append("the persona has no name")

    # Sessions and messages.
    seen_sources: set[str] = set()
    seen_messages: set[str] = set()
    previous_start: datetime | None = None
    for s in world.sessions:
        if s.id in seen_sources:
            problems.append(f"session id {s.id} is used twice")
        seen_sources.add(s.id)
        try:
            start = datetime.fromisoformat(s.started_at or "")
            if previous_start is not None and start < previous_start:
                problems.append(f"session {s.id} starts before the one before it")
            previous_start = start
        except (ValueError, TypeError):
            problems.append(f"session {s.id} has no valid start time")
        if not s.messages:
            problems.append(f"session {s.id} has no messages")
        for i, m in enumerate(s.messages):
            if m.id in seen_messages:
                problems.append(f"message id {m.id} is used twice")
            seen_messages.add(m.id)
            if m.source_id != s.id or m.ordinal != i:
                problems.append(f"message {m.id} does not match its place ({s.id}, {i})")
            if i and m.occurred_at and s.messages[i - 1].occurred_at and m.occurred_at < s.messages[i - 1].occurred_at:
                problems.append(f"message {m.id} is earlier than the message before it")
            if m.speaker not in SPEAKERS:
                problems.append(f"message {m.id} has speaker {m.speaker!r}")
            if not m.text.strip():
                problems.append(f"message {m.id} is empty")
            if m.speaker == "assistant":
                if m.model_family not in FAMILIES:
                    problems.append(f"assistant message {m.id} has model family {m.model_family!r}")
                if not m.agent:
                    problems.append(f"assistant message {m.id} has no agent")
            elif m.model_family is not None:
                problems.append(f"user message {m.id} has a model family")
    order = message_order(world)
    index = message_index(world.sessions)

    def known(ids: list[str], where: str) -> bool:
        ok = True
        for mid in ids:
            if mid not in index:
                problems.append(f"{where}: message {mid} does not exist")
                ok = False
        return ok

    # Gold memories.
    memories: dict[str, GoldMemory] = {}
    for g in world.gold_memories:
        where = f"memory {g.key}"
        if g.key in memories:
            problems.append(f"{where}: the key is used twice")
        memories[g.key] = g
        if not g.line.strip():
            problems.append(f"{where}: no line")
        if g.kind not in KINDS:
            problems.append(f"{where}: kind {g.kind!r} is not a memory kind")
        if g.holder not in HOLDERS:
            problems.append(f"{where}: holder {g.holder!r} is not valid")
        if not g.evidence_message_ids:
            problems.append(f"{where}: no evidence")
        elif known(g.evidence_message_ids, where):
            speakers = {index[i].speaker for i in g.evidence_message_ids}
            if g.holder == "user" and "user" not in speakers:
                problems.append(f"{where}: held by the user, but no evidence is in the user's words")
            if g.adopted_from is not None:
                if g.adopted_from not in FAMILIES:
                    problems.append(f"{where}: adopted_from {g.adopted_from!r} is not a family")
                elif not any(
                    index[i].speaker == "assistant" and index[i].model_family == g.adopted_from
                    for i in g.evidence_message_ids
                ):
                    problems.append(f"{where}: adopted from {g.adopted_from}, but no evidence is that family's turn")
                if g.holder != "user":
                    problems.append(f"{where}: an adopted idea is held by the user")

    # Gold updates.
    updates: dict[str, GoldUpdate] = {}
    for u in world.gold_updates:
        where = f"update {u.key}"
        if u.key in updates:
            problems.append(f"{where}: the key is used twice")
        updates[u.key] = u
        if u.old_key == u.new_key:
            problems.append(f"{where}: old and new are the same memory")
        for k in (u.old_key, u.new_key):
            if k not in memories:
                problems.append(f"{where}: memory {k} does not exist")
        if u.at_message_id not in index:
            problems.append(f"{where}: message {u.at_message_id} does not exist")
        elif u.old_key in memories and all(i in order for i in memories[u.old_key].evidence_message_ids):
            last_old = max((order[i] for i in memories[u.old_key].evidence_message_ids), default=-1)
            if order[u.at_message_id] <= last_old:
                problems.append(f"{where}: the change is not after the evidence of {u.old_key}")
        if not u.reason.strip():
            problems.append(f"{where}: no reason")

    # Probes.
    probes: dict[str, QAItem] = {}
    for p in world.probes:
        where = f"probe {p.id}"
        if p.id in probes:
            problems.append(f"{where}: the id is used twice")
        probes[p.id] = p
        if not p.question.strip():
            problems.append(f"{where}: no question")
        if not p.gold_answer.strip():
            problems.append(f"{where}: no gold answer")
        if p.haystack:
            problems.append(f"{where}: carries a haystack; it is built by haystack_for")
        scenario = p.meta.get("scenario")
        kind = p.meta.get("kind")
        if scenario not in BY_ID:
            problems.append(f"{where}: scenario {scenario!r} is not one of the 18")
        if kind not in PROBE_KINDS:
            problems.append(f"{where}: kind {kind!r} is not a probe kind")
        elif kind != p.question_type:
            problems.append(f"{where}: kind {kind} differs from question_type {p.question_type}")
        elif scenario in BY_ID and kind not in BY_ID[scenario].probe_kinds:
            problems.append(f"{where}: kind {kind} is not one of {scenario}'s probe kinds")
        if (kind == "abstention") != p.abstention:
            problems.append(f"{where}: abstention flag and kind disagree")
        checkpoint = p.meta.get("after_message_id")
        if checkpoint not in index:
            problems.append(f"{where}: checkpoint message {checkpoint!r} does not exist")
        known(p.evidence_message_ids, where)
        if p.abstention and p.evidence_message_ids:
            problems.append(f"{where}: an abstention probe has evidence")
        if not p.abstention and not p.evidence_message_ids:
            problems.append(f"{where}: no evidence")
        if checkpoint in order:
            for mid in p.evidence_message_ids:
                if mid in order and order[mid] > order[checkpoint]:
                    problems.append(f"{where}: evidence {mid} comes after the checkpoint")

    # Tags.
    elements = set(memories) | set(updates) | set(probes)
    if len(elements) != len(memories) + len(updates) + len(probes):
        problems.append("a key is used by more than one of memories, updates and probes")
    for key, scenarios in world.tags.items():
        if key not in elements:
            problems.append(f"tag for {key}: no such memory, update or probe")
        for sid in scenarios:
            if sid not in BY_ID:
                problems.append(f"tag for {key}: {sid} is not one of the 18")
    for key in sorted(elements):
        if not world.tags.get(key):
            problems.append(f"{key} has no scenario tag")
    for p in world.probes:
        scenario = p.meta.get("scenario")
        if scenario in BY_ID and scenario not in world.tags.get(p.id, []):
            problems.append(f"probe {p.id}: its scenario {scenario} is not among its tags")
    return problems
