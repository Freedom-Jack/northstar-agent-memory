"""Model-driven generation of more synthetic personas (note 09, Implications §5; DESIGN §8).

The pipeline, all through the ModelPort with strict schemas:
1. scenario.plan: family A writes the ledger (persona, gold memories, gold updates, probes)
   and a plan of sessions. Gold elements cite scripted evidence items ("beats"), because the
   text does not exist yet.
2. scenario.render: family A writes each session as chat turns.
3. scenario.mess: family A makes it messy (hedges, typos, drift, half-retractions), because
   simulated users are too cooperative (Zhou et al. 2026).
4. scenario.validate: family B, never A, reads the finished session and says, for each beat,
   whether it is present and can be inferred, and in which messages. Evidence ids come from
   this check. A session with failing beats is re-rendered with the checker's notes, up to
   `max_rerenders` times; beats that still fail are dropped, and so is every gold element
   left without evidence. What was re-rendered and dropped is recorded in `world.meta`.

The result is a World that passes `validate`. A human spot check of 5 to 10% of sessions
still follows (note 09 §5). Seeds must be invented; never feed this a real person's chats.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from northstar_agent_memory.eval.scenarios.library import BY_ID, PROBE_KINDS, SCENARIOS
from northstar_agent_memory.eval.scenarios.ledger import (
    HOLDERS,
    KINDS,
    MINUTES_PER_MESSAGE,
    Persona,
    Project,
    World,
    fill_question_dates,
    memory_from_script,
    probe_from_script,
    update_from_script,
    validate,
)
from northstar_agent_memory.models.port import FAMILIES, ModelPort, ModelRequest, Usage, other_family
from northstar_agent_memory.transcript import Message, Source

# The apps a synthetic person uses, and the family behind each assistant.
APP_FAMILY = {"claude-code": "anthropic", "claude.ai": "anthropic", "codex": "openai", "chatgpt": "openai"}
APP_KIND = {"claude-code": "work", "codex": "work", "claude.ai": "chat", "chatgpt": "chat"}

TRAITS = (
    "hedges and typos",
    "a joke that is not a decision",
    "a half-retraction",
    "topic drift inside a chat",
    "an AI suggestion the user ignores",
    "an AI suggestion the user adopts in their own words",
    "a teammate's opinion",
    "a hypothetical",
    "a pasted text with an injected instruction",
    "a mild sensitive disclosure",
    "two people or two things with the same name",
    "an open question that stays open",
    "a correction",
)


class GenerationError(Exception):
    """The models' output cannot be turned into a sound world."""


# --- schemas (strict: every property required, optional values are unions with null) -------


def _obj(properties: dict) -> dict:
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def _arr(item: dict) -> dict:
    return {"type": "array", "items": item}


_STR = {"type": "string"}
_MAYBE_STR = {"type": ["string", "null"]}
_BOOL = {"type": "boolean"}
_STRS = _arr(_STR)

PLAN_SCHEMA = _obj(
    {
        "persona": _obj(
            {
                "name": _STR,
                "summary": _STR,
                "projects": _arr(
                    _obj({"id": _STR, "name": _STR, "description": _STR, "kind": {"type": "string", "enum": ["work", "personal"]}})
                ),
                "traits": _STRS,
            }
        ),
        "sessions": _arr(
            _obj(
                {
                    "id": _STR,
                    "started_at": _STR,  # ISO 8601 with an offset
                    "app": {"type": "string", "enum": list(APP_FAMILY)},
                    "project": _MAYBE_STR,
                    "title": _STR,
                    "beats": _arr(
                        _obj(
                            {
                                "id": _STR,
                                "speaker": {"type": "string", "enum": ["user", "assistant"]},
                                "content": _STR,
                                "indirect": _BOOL,
                            }
                        )
                    ),
                }
            )
        ),
        "gold_memories": _arr(
            _obj(
                {
                    "key": _STR,
                    "line": _STR,
                    "kind": {"type": "string", "enum": list(KINDS)},
                    "holder": {"type": "string", "enum": list(HOLDERS)},
                    "evidence": _STRS,
                    "must_record": _BOOL,
                    "scope": _STR,
                    "adopted_from": {"type": ["string", "null"], "enum": [*FAMILIES, None]},
                    "scenarios": _STRS,
                }
            )
        ),
        "gold_updates": _arr(
            _obj({"key": _STR, "old": _STR, "new": _STR, "at": _STR, "reason": _STR, "scenarios": _STRS})
        ),
        "probes": _arr(
            _obj(
                {
                    "id": _STR,
                    "scenario": _STR,
                    "kind": {"type": "string", "enum": list(PROBE_KINDS)},
                    "after": _STR,
                    "question": _STR,
                    "answer": _STR,
                    "evidence": _STRS,
                    "forbidden_terms": _STRS,
                }
            )
        ),
    }
)

_MESSAGES = _arr(
    _obj(
        {
            "speaker": {"type": "string", "enum": ["user", "assistant"]},
            "text": _STR,
            "origin": {"type": "string", "enum": ["typed", "pasted"]},
        }
    )
)
RENDER_SCHEMA = _obj({"messages": _MESSAGES})  # also the schema of the messiness pass

VALIDATE_SCHEMA = _obj(
    {
        "verdicts": _arr(
            _obj(
                {
                    "beat": _STR,
                    "present": _BOOL,
                    "inferable": _BOOL,
                    "message_ordinals": _arr({"type": "integer"}),
                    "note": _STR,
                }
            )
        )
    }
)


# --- prompts ---------------------------------------------------------------------------------

_SCENARIO_TEXT = "\n".join(f"{s.id} {s.name}: {s.holds}" for s in SCENARIOS)

PLAN_SYSTEM = f"""You write the hidden record of an invented person, for testing an AI memory system.
The person is referred to as they/them. Everything is invented; use no real person, company or private data.

Output the persona, a plan of chat sessions in time order, and the ledger.
- A session is one chat with an AI app (claude-code, codex, claude.ai or chatgpt). It has beats: short
  descriptions of what a turn says or implies, each with an id unique across the whole plan, the speaker, and
  whether it is indirect (implied, not stated).
- Gold memories are what a memory system should end up recording. Each cites beat ids as evidence. Use
  must_record false for distractors that must NOT become the person's memory: a hypothetical, a joke, another
  person's view, an AI suggestion the person ignored, an instruction inside pasted text.
  Kinds: {", ".join(KINDS)} (a plain fact about the person is a definition). Holders: {", ".join(HOLDERS)}.
  A memory held by "user" needs a beat spoken by the user; use adopted_from (anthropic or openai) only when the
  person took up that family's assistant idea, and then cite the assistant's beat and the person's own beat.
- Gold updates say that new supersedes old, at the beat where the change happens, which must come after the
  evidence for the old memory.
- Probes are questions asked of a memory system after a checkpoint beat ("after"), with the gold answer and
  the beats that support it. Probe kinds: {", ".join(PROBE_KINDS)}. An abstention probe has no evidence, and the
  answer says the history does not tell. A stale_premise question assumes an outdated state. Spread the
  checkpoints over time. Use forbidden_terms for words an answer must not contain (otherwise an empty list).
- Tag every memory, update and probe with the scenarios it serves. The scenarios:
{_SCENARIO_TEXT}
Make the person messy and ambiguous, not cooperative. Keep each session short."""

RENDER_SYSTEM = """You write one chat session between a person and an AI assistant, from a plan of beats.
Write the person's turns like a real person typing: lowercase, short, typos, hedges, side remarks.
Write the assistant's turns as a real assistant would: plain, helpful, not sycophantic. Every beat must come out
in the turns, in order, said by its speaker; an indirect beat is implied, never stated outright. Do not add
facts that change the plan. If a person pastes text, put it in its own user turn with origin "pasted".
Output the turns as the schema asks."""

MESS_SYSTEM = """You make a chat session messier and more human without changing what it establishes.
Add the listed traits where they fit: hedges, typos, a joke, a half-retraction, topic drift, an assistant
suggestion that is ignored, and so on. Every beat must still be present and inferable, said by its speaker, and
no new fact may contradict it. Return the whole session in the same schema."""

VALIDATE_SYSTEM = """You check a finished chat session against its plan.
For each beat, say whether it is present (said, or for an indirect beat implied) and whether a careful reader could
infer it from the text alone, and give the ordinals of the messages that carry it. Be strict: a beat that is
missing, contradicted, said by the wrong speaker or only vaguely hinted at is not present. Add a short note on
what is wrong with any beat that fails."""


# --- calls -----------------------------------------------------------------------------------


@dataclass(slots=True)
class _Meter:
    calls: int = 0
    usage: Usage = field(default_factory=Usage)
    cost_usd: float = 0.0


def _call(
    port: ModelPort,
    meter: _Meter,
    *,
    purpose: str,
    role: str,
    family: str,
    system: str,
    payload: dict,
    schema: dict,
    max_tokens: int,
    metadata: dict | None = None,
) -> dict:
    result = port.complete(
        ModelRequest(
            purpose=purpose,
            role=role,  # type: ignore[arg-type]
            family=family,  # type: ignore[arg-type]
            system=system,
            messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
            schema=schema,
            max_tokens=max_tokens,
            metadata=metadata or {},
        )
    )
    meter.calls += 1
    meter.usage = meter.usage + result.usage
    meter.cost_usd += result.cost_usd
    if not isinstance(result.parsed, dict):
        raise GenerationError(f"{purpose}: the reply has no structured output")
    return result.parsed


def _render(port, meter, family, session: dict, traits: list[str], messy: bool, feedback: list[dict]) -> list[dict]:
    meta = {"session": session["id"]}
    payload = {"session": session, "assistant_app": session["app"]}
    if feedback:
        payload["fix_these_beats"] = feedback
    turns = _call(
        port, meter, purpose="scenario.render", role="sim_user", family=family, system=RENDER_SYSTEM,
        payload=payload, schema=RENDER_SCHEMA, max_tokens=8000, metadata=meta,
    )["messages"]
    if messy:
        turns = _call(
            port, meter, purpose="scenario.mess", role="sim_user", family=family, system=MESS_SYSTEM,
            payload={"session": session, "traits": traits, "messages": turns}, schema=RENDER_SCHEMA,
            max_tokens=8000, metadata=meta,
        )["messages"]
    return [t for t in turns if t["text"].strip()]


def _check(port, meter, family, session: dict, turns: list[dict]) -> dict[str, dict]:
    """Family B's verdict per beat id; a beat passes only when it is present, inferable and located."""
    shown = [{"ordinal": i, "speaker": t["speaker"], "text": t["text"]} for i, t in enumerate(turns)]
    reply = _call(
        port, meter, purpose="scenario.validate", role="checker", family=family, system=VALIDATE_SYSTEM,
        payload={"beats": session["beats"], "messages": shown}, schema=VALIDATE_SCHEMA, max_tokens=4000,
        metadata={"session": session["id"]},
    )
    speakers = {b["id"]: b["speaker"] for b in session["beats"]}  # evidence must be in the beat's speaker's turn
    out: dict[str, dict] = {}
    for v in reply["verdicts"]:
        wanted = speakers.get(v["beat"])
        ordinals = sorted({o for o in v["message_ordinals"] if 0 <= o < len(turns) and wanted in (None, turns[o]["speaker"])})
        ok = v["present"] and v["inferable"] and bool(ordinals)
        out[v["beat"]] = {"ok": ok, "ordinals": ordinals, "note": v["note"]}
    for beat in session["beats"]:
        out.setdefault(beat["id"], {"ok": False, "ordinals": [], "note": "the checker gave no verdict"})
    return out


# --- the pipeline -------------------------------------------------------------------------------


def generate(
    port: ModelPort,
    *,
    seed: str,
    n_sessions: int = 12,
    scenarios: tuple[str, ...] | None = None,
    start_date: str = "2026-01-05",
    weeks: int = 6,
    family: str = "anthropic",
    world_id: str | None = None,
    max_rerenders: int = 1,
    messy: bool = True,
) -> World:
    """Generate one persona. `family` writes; the other family checks."""
    if family not in FAMILIES:
        raise ValueError(f"family must be one of {FAMILIES}")
    checker = other_family(family)
    wanted = tuple(scenarios) if scenarios else tuple(s.id for s in SCENARIOS)
    meter = _Meter()
    plan = _call(
        port, meter, purpose="scenario.plan", role="worker", family=family, system=PLAN_SYSTEM,
        payload={"seed": seed, "sessions": n_sessions, "scenarios": list(wanted), "start_date": start_date, "weeks": weeks},
        schema=PLAN_SCHEMA, max_tokens=32000,
    )
    dropped: list[dict] = []
    rerendered: list[str] = []

    # Sessions: plan, render, make messy, check, re-render, drop.
    sources: list[Source] = []
    located: dict[str, list[str]] = {}  # beat id -> message ids, for beats that passed
    seen_sessions: set[str] = set()
    seen_beats: set[str] = set()
    project_ids = {p["id"] for p in plan["persona"]["projects"]}
    traits = list(plan["persona"]["traits"]) or list(TRAITS)
    for session in sorted(plan["sessions"], key=_when):
        sid = session["id"]
        why = _session_problem(session, seen_sessions)
        if why:
            dropped.append({"kind": "session", "id": sid, "why": why})
            continue
        seen_sessions.add(sid)
        beats = []
        for beat in session["beats"]:
            if beat["id"] in seen_beats:
                dropped.append({"kind": "beat", "id": beat["id"], "why": "the beat id is used twice"})
            else:
                seen_beats.add(beat["id"])
                beats.append(beat)
        session = {**session, "beats": beats}
        feedback: list[dict] = []
        for attempt in range(max_rerenders + 1):
            turns = _render(port, meter, family, session, traits, messy, feedback)
            verdicts = _check(port, meter, checker, session, turns)
            failing = [b for b in beats if not verdicts[b["id"]]["ok"]]
            if not failing:
                break
            feedback = [{"beat": b["id"], "problem": verdicts[b["id"]]["note"]} for b in failing]
            if attempt < max_rerenders:
                rerendered.append(sid)
        source = _source(session, turns, project_ids)
        sources.append(source)
        for beat in beats:
            verdict = verdicts[beat["id"]]
            if verdict["ok"]:
                located[beat["id"]] = [source.messages[i].id for i in verdict["ordinals"] if i < len(source.messages)]
            else:
                dropped.append({"kind": "beat", "id": beat["id"], "why": f"failed the check: {verdict['note']}"})
    sources = [s for s in sources if s.messages]

    world = _build_world(plan, sources, located, world_id or _slug(plan["persona"]["name"]), dropped)
    _prune(world, dropped)
    fill_question_dates(world)
    world.meta["generation"] = {
        "seed": seed,
        "writer_family": family,
        "checker_family": checker,
        "scenarios": list(wanted),
        "rerendered": sorted(set(rerendered)),
        "dropped": dropped,
        "calls": meter.calls,
        "cost_usd": meter.cost_usd,
        "tokens": {"input": meter.usage.input_tokens, "output": meter.usage.output_tokens},
    }
    return world


def _when(session: dict) -> datetime:
    try:
        when = datetime.fromisoformat(session["started_at"])
    except ValueError:
        return datetime.max.replace(tzinfo=timezone.utc)
    return when if when.tzinfo else when.replace(tzinfo=timezone.utc)


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "persona"


def _session_problem(session: dict, seen: set[str]) -> str | None:
    if not session["id"] or session["id"] in seen:
        return "the session id is empty or used twice"
    try:
        if datetime.fromisoformat(session["started_at"]).tzinfo is None:
            return "the start time has no offset"
    except ValueError:
        return "the start time is not ISO 8601"
    if session["app"] not in APP_FAMILY:
        return "the app is not one of the known apps"
    if not session["beats"]:
        return "no beats"
    return None


def _source(session: dict, turns: list[dict], project_ids) -> Source:
    sid, app = session["id"], session["app"]
    start = datetime.fromisoformat(session["started_at"])
    messages = []
    for i, turn in enumerate(turns):
        assistant = turn["speaker"] == "assistant"
        messages.append(
            Message(
                id=f"{sid}:{i}",
                source_id=sid,
                ordinal=i,
                speaker=turn["speaker"],
                text=turn["text"],
                occurred_at=(start + timedelta(minutes=MINUTES_PER_MESSAGE * i)).isoformat(),
                origin="assistant_output" if assistant else turn.get("origin", "typed"),
                agent=app if assistant else None,
                model_family=APP_FAMILY[app] if assistant else None,
            )
        )
    project = session["project"] if session["project"] in project_ids else None
    return Source(
        id=sid,
        kind=APP_KIND[app],
        app=app,
        project=project,
        title=session["title"],
        started_at=session["started_at"],
        messages=messages,
    )


def _build_world(plan: dict, sources: list[Source], located: dict[str, list[str]], world_id: str, dropped: list[dict]) -> World:
    p = plan["persona"]
    world = World(
        id=world_id,
        persona=Persona(
            name=p["name"],
            summary=p["summary"],
            projects=[Project(**proj) for proj in p["projects"]],
            traits=list(p["traits"]),
        ),
        sessions=sources,
        gold_memories=[],
        gold_updates=[],
        probes=[],
    )
    used: set[str] = set()

    def evidence(beats: list[str]) -> list[str]:
        ids = [m for b in beats for m in located.get(b, [])]
        return list(dict.fromkeys(ids))

    def tags_for(spec: dict, extra: tuple[str, ...] = ()) -> list[str]:
        return [s for s in dict.fromkeys([*extra, *spec.get("scenarios", [])]) if s in BY_ID]

    def claim(kind: str, key: str, tags: list[str]) -> bool:
        if key in used:
            dropped.append({"kind": kind, "id": key, "why": "the key is used twice"})
        elif not tags:
            dropped.append({"kind": kind, "id": key, "why": "no valid scenario tag"})
        else:
            used.add(key)
            return True
        return False

    for spec in plan["gold_memories"]:
        tags = tags_for(spec)
        if claim("memory", spec["key"], tags):
            memory, _ = memory_from_script({**spec, "evidence": evidence(spec["evidence"])})
            world.gold_memories.append(memory)
            world.tags[memory.key] = tags
    for spec in plan["gold_updates"]:
        tags = tags_for(spec)
        at = located.get(spec["at"], [])
        if not at:
            dropped.append({"kind": "update", "id": spec["key"], "why": "its change beat was dropped"})
        elif claim("update", spec["key"], tags):
            update, _ = update_from_script({**spec, "at": at[0]})
            world.gold_updates.append(update)
            world.tags[update.key] = tags
    for spec in plan["probes"]:
        tags = tags_for(spec, extra=(spec["scenario"],))
        after = located.get(spec["after"], [])
        if not after:
            dropped.append({"kind": "probe", "id": spec["id"], "why": "its checkpoint beat was dropped"})
        elif claim("probe", spec["id"], tags):
            forbidden = [t for t in spec["forbidden_terms"] if t.strip()]
            probe, _ = probe_from_script(
                world.id,
                {**spec, "after": after[-1], "evidence": evidence(spec["evidence"]), "meta": {"forbidden_terms": forbidden} if forbidden else {}},
            )
            world.probes.append(probe)
            world.tags[probe.id] = tags
    return world


_ELEMENT = re.compile(r"^(memory|update|probe) (\S+?): ")


def _prune(world: World, dropped: list[dict]) -> None:
    """Drop every gold element that `validate` objects to, until the world is sound."""
    for _ in range(100):
        problems = validate(world)
        if not problems:
            return
        victims: dict[tuple[str, str], str] = {}
        for problem in problems:
            match = _ELEMENT.match(problem)
            if match is None:
                raise GenerationError(f"the world has a problem no element can be dropped for: {problem}")
            victims.setdefault((match[1], match[2]), problem)
        for (kind, key), problem in victims.items():
            dropped.append({"kind": kind, "id": key, "why": problem})
        gone = {key for _, key in victims}
        world.gold_memories = [m for m in world.gold_memories if m.key not in gone]
        world.gold_updates = [u for u in world.gold_updates if u.key not in gone]
        world.probes = [q for q in world.probes if q.id not in gone]
        world.tags = {k: v for k, v in world.tags.items() if k not in gone}
    raise GenerationError("the world did not become sound after 100 rounds of dropping")
