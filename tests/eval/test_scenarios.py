"""Scripted scenarios: the library, the ledger, the pilot persona and the generator (no network)."""

from __future__ import annotations

import copy
import json
import shutil
from collections import Counter

import pytest

from northstar_agent_memory.eval.scenarios import generate as gen
from northstar_agent_memory.eval.scenarios.ledger import (
    HOLDERS,
    KINDS,
    ask,
    coverage,
    haystack_for,
    load_world,
    message_order,
    save_world,
    source_from_script,
    validate,
    world_from_dict,
    world_to_dict,
)
from northstar_agent_memory.eval.scenarios.library import BY_ID, OPERATIONS, PROBE_KINDS, SCENARIOS
from northstar_agent_memory.eval.scenarios.pilot import DATA_DIR, load_pilot
from northstar_agent_memory.models.port import ModelRequest, other_family
from northstar_agent_memory.models.schema import assert_strict
from northstar_agent_memory.models.stub import StubModel
from northstar_agent_memory.transcript import message_index


@pytest.fixture(scope="module")
def pilot():
    return load_pilot()


# --- library ----------------------------------------------------------------------------------


def test_library_has_the_18_scenarios():
    assert [s.id for s in SCENARIOS] == [f"S{i}" for i in range(1, 19)]
    for s in SCENARIOS:
        assert s.name and s.holds
        assert s.operations and set(s.operations) <= set(OPERATIONS)
        assert s.probe_kinds and set(s.probe_kinds) <= set(PROBE_KINDS)
    assert BY_ID["S5"].name == "Reversal of a reversal"


# --- the pilot --------------------------------------------------------------------------------


def test_pilot_validates_with_no_problems(pilot):
    assert validate(pilot) == []


def test_pilot_covers_all_18_scenarios(pilot):
    counts = coverage(pilot)
    assert all(counts[s.id] > 0 for s in SCENARIOS), counts
    # Each scenario has at least one probe, so each can be scored.
    probed = {p.meta["scenario"] for p in pilot.probes}
    assert probed == set(BY_ID)


def test_pilot_size_follows_the_brief(pilot):
    messages = [m for s in pilot.sessions for m in s.messages]
    assert 28 <= len(pilot.sessions) <= 34
    assert 250 <= len(messages) <= 350
    assert 40 <= len(pilot.gold_memories) <= 70
    assert 8 <= len(pilot.gold_updates) <= 15
    assert 40 <= len(pilot.probes) <= 60
    short = [s for s in pilot.sessions if 4 <= len(s.messages) <= 10]
    assert len(short) >= len(pilot.sessions) * 0.7


def test_pilot_spans_about_six_weeks_in_early_2026(pilot):
    first, last = pilot.sessions[0].started_at, pilot.sessions[-1].started_at
    assert first.startswith("2026-01") and last.startswith("2026-02")
    assert pilot.sessions[0].started_at <= pilot.sessions[-1].started_at


def test_every_evidence_id_resolves_and_is_exact(pilot):
    index = message_index(pilot.sessions)
    ids = [i for g in pilot.gold_memories for i in g.evidence_message_ids]
    ids += [i for p in pilot.probes for i in p.evidence_message_ids]
    ids += [u.at_message_id for u in pilot.gold_updates]
    ids += [p.meta["after_message_id"] for p in pilot.probes]
    assert ids and all(i in index for i in ids)
    for s in pilot.sessions:
        for i, m in enumerate(s.messages):
            assert m.id == f"{s.id}:{i}" and m.source_id == s.id and m.ordinal == i


def test_pilot_uses_both_families_and_several_apps(pilot):
    assistants = [m for s in pilot.sessions for m in s.messages if m.speaker == "assistant"]
    assert {m.model_family for m in assistants} == {"anthropic", "openai"}
    assert {m.agent for m in assistants} >= {"claude-code", "codex", "claude.ai", "chatgpt"}
    assert {s.project for s in pilot.sessions} == {None, "atlas", "hearth"}
    assert {m.speaker for s in pilot.sessions for m in s.messages} == {"user", "assistant"}


def test_pilot_has_distractors_and_attribution_cases(pilot):
    by_key = {g.key: g for g in pilot.gold_memories}
    distractors = [g for g in pilot.gold_memories if not g.must_record]
    assert len(distractors) >= 5
    assert {g.holder for g in distractors} == {"hypothetical", "ai_unadopted", "other_person"}
    assert all(g.holder in HOLDERS and g.kind in KINDS for g in pilot.gold_memories)
    # An AI idea the user took up is the user's, with the AI family named.
    assert by_key["m_backoff_jitter"].adopted_from == "openai" and by_key["m_backoff_jitter"].must_record
    assert by_key["m_ai_otel"].holder == "ai_unadopted"
    # An injected instruction sits in a pasted message and is not the user's.
    inject = by_key["m_inject_summaries"]
    pasted = message_index(pilot.sessions)[inject.evidence_message_ids[0]]
    assert pasted.origin == "pasted" and inject.holder != "user" and not inject.must_record


def test_pilot_scenario_specifics(pilot):
    updates = {u.key: u for u in pilot.gold_updates}
    # A to B to A: the last state is the first state's idea again, by a new memory.
    assert updates["u_store_influx"].new_key == updates["u_store_back"].old_key
    assert updates["u_store_back"].new_key == "m_store_sqlite_2"
    # A goal lifecycle is a chain: set, stalled, abandoned, revived.
    chain = [updates[k].new_key for k in ("u_goal_stall", "u_goal_drop", "u_goal_revive")]
    assert chain == ["m_goal_10k_stalled", "m_goal_10k_abandoned", "m_goal_5k_revived"]
    # An implicit change and a correction are labelled as such.
    assert updates["u_dog_travel"].reason == "implicit"
    assert updates["u_cache_correction"].reason == "user_correction"
    # The open question stays open.
    open_q = next(g for g in pilot.gold_memories if g.key == "m_open_platform")
    assert open_q.kind == "question" and open_q.meta["open"] is True
    # Two Alexes and two Atlases are separate memories.
    keys = {g.key for g in pilot.gold_memories}
    assert {"m_alex_moreau", "m_alex_pryce", "m_atlas_work", "m_trek_plan"} <= keys


def test_pilot_probes_cover_kinds_and_times(pilot):
    kinds = Counter(p.question_type for p in pilot.probes)
    assert set(kinds) == set(PROBE_KINDS)
    assert all(kinds[k] >= 4 for k in PROBE_KINDS)
    assert all(p.abstention == (p.question_type == "abstention") for p in pilot.probes)
    assert all(not p.evidence_message_ids for p in pilot.probes if p.abstention)
    days = {p.question_date[:10] for p in pilot.probes}
    assert len(days) >= 12  # checkpoints spread over the weeks
    assert all(p.dataset == "scenario:pilot" and p.gold_answer.strip() for p in pilot.probes)


def test_pilot_privacy_and_dormancy_probes(pilot):
    leaks = [p for p in pilot.probes if p.meta.get("forbidden_terms")]
    assert len(leaks) >= 2
    for p in leaks:
        assert p.meta["scenario"] == "S15" and "migraine" in p.meta["forbidden_terms"]
        assert not any(t in p.gold_answer.lower() for t in p.meta["forbidden_terms"])
    dormant = next(p for p in pilot.probes if p.meta.get("staleness_expected"))
    last = pilot.sessions[-1].started_at[:10]
    assert dormant.meta["last_mentioned"] < last
    order = message_order(pilot)
    seen = max(order[i] for i in dormant.evidence_message_ids)
    assert order[dormant.meta["after_message_id"]] - seen > 150  # long untouched


# --- JSON ---------------------------------------------------------------------------------------


def test_json_round_trip(pilot, tmp_path):
    path = tmp_path / "w" / "pilot.json"
    save_world(pilot, path)
    again = load_world(path)
    assert again == pilot
    assert world_from_dict(json.loads(json.dumps(world_to_dict(pilot)))) == pilot
    assert validate(again) == []


def test_source_from_script_expands_ids_times_and_assistant_tags():
    s = source_from_script(
        {
            "id": "x1",
            "kind": "work",
            "app": "codex",
            "model_family": "openai",
            "project": "p",
            "started_at": "2026-02-01T10:00:00+00:00",
            "messages": [["user", "hi"], ["assistant", "hello"], ["user", "pasted text", {"origin": "pasted"}]],
        }
    )
    assert [m.id for m in s.messages] == ["x1:0", "x1:1", "x1:2"]
    assert [m.occurred_at[11:16] for m in s.messages] == ["10:00", "10:02", "10:04"]
    assistant = s.messages[1]
    assert (assistant.agent, assistant.model_family, assistant.origin) == ("codex", "openai", "assistant_output")
    assert s.messages[0].agent is None and s.messages[0].model_family is None
    assert s.messages[2].origin == "pasted"


def test_partial_pilot_loads_what_was_written(tmp_path):
    for name in ("persona.json", "sessions_01.json"):
        shutil.copy(DATA_DIR / name, tmp_path / name)
    partial = load_pilot(tmp_path)
    assert len(partial.sessions) == 7 and not partial.probes and not partial.gold_memories
    assert validate(partial) == []
    with pytest.raises(FileNotFoundError):
        load_pilot(tmp_path / "missing")


# --- haystacks ------------------------------------------------------------------------------------


def test_haystack_for_truncates_at_the_checkpoint(pilot):
    probe = next(p for p in pilot.probes if p.meta["after_message_id"] == "s27:9")
    hay = haystack_for(pilot, probe)
    assert hay[-1].id == "s27" and len(hay[-1].messages) == 10
    assert [s.id for s in hay] == [s.id for s in pilot.sessions[: len(hay)]]
    assert "s28" not in {s.id for s in hay}

    mid = next(p for p in pilot.probes if p.meta["after_message_id"] == "s28:3")
    hay = haystack_for(pilot, mid)
    assert hay[-1].id == "s28"
    assert [m.id for m in hay[-1].messages] == ["s28:0", "s28:1", "s28:2", "s28:3"]
    assert all(s.id != "s29" for s in hay)
    # The world is untouched, and a probe's evidence is always inside its haystack.
    assert len(pilot.sessions[27].messages) == 10
    seen = {m.id for s in hay for m in s.messages}
    assert all(i in seen for i in mid.evidence_message_ids)


def test_haystack_for_every_probe_contains_its_evidence(pilot):
    for probe in pilot.probes:
        seen = {m.id for s in haystack_for(pilot, probe) for m in s.messages}
        assert probe.meta["after_message_id"] in seen
        assert set(probe.evidence_message_ids) <= seen
        last = haystack_for(pilot, probe)[-1].messages[-1]
        assert last.id == probe.meta["after_message_id"]


def test_ask_fills_the_haystack_and_leaves_the_probe_alone(pilot):
    probe = pilot.probes[0]
    item = ask(pilot, probe)
    assert item.haystack and not probe.haystack
    assert item.id == probe.id and item.gold_answer == probe.gold_answer


def test_haystack_for_unknown_checkpoint(pilot):
    probe = copy.deepcopy(pilot.probes[0])
    probe.meta["after_message_id"] = "nope:1"
    with pytest.raises(KeyError):
        haystack_for(pilot, probe)


# --- validate catches what is wrong ------------------------------------------------------------------


def _broken(pilot, edit):
    world = copy.deepcopy(pilot)
    edit(world)
    return validate(world)


def test_validate_flags_bad_evidence_and_checkpoints(pilot):
    problems = _broken(pilot, lambda w: w.gold_memories[0].evidence_message_ids.append("s99:1"))
    assert any("s99:1 does not exist" in p for p in problems)
    problems = _broken(pilot, lambda w: w.probes[0].meta.update(after_message_id="s99:1"))
    assert any("checkpoint" in p for p in problems)
    problems = _broken(pilot, lambda w: setattr(w.probes[0], "gold_answer", " "))
    assert any("no gold answer" in p for p in problems)


def test_validate_flags_updates_out_of_order_or_unknown(pilot):
    problems = _broken(pilot, lambda w: setattr(w.gold_updates[0], "at_message_id", "s01:0"))
    assert any("not after the evidence" in p for p in problems)
    problems = _broken(pilot, lambda w: setattr(w.gold_updates[0], "new_key", "m_nothing"))
    assert any("m_nothing does not exist" in p for p in problems)


def test_validate_flags_abstention_with_evidence_and_late_evidence(pilot):
    abstain = next(i for i, p in enumerate(pilot.probes) if p.abstention)
    problems = _broken(pilot, lambda w: w.probes[abstain].evidence_message_ids.append("s01:0"))
    assert any("abstention probe has evidence" in p for p in problems)
    problems = _broken(pilot, lambda w: w.probes[0].evidence_message_ids.append("s32:0"))
    assert any("comes after the checkpoint" in p for p in problems)
    problems = _broken(pilot, lambda w: setattr(w.probes[abstain], "abstention", False))
    assert any("abstention flag and kind disagree" in p for p in problems)


def test_validate_flags_speakers_families_and_untagged_elements(pilot):
    problems = _broken(pilot, lambda w: setattr(w.sessions[0].messages[0], "speaker", "tool"))
    assert any("speaker 'tool'" in p for p in problems)
    problems = _broken(pilot, lambda w: setattr(w.sessions[0].messages[1], "model_family", None))
    assert any("model family" in p for p in problems)
    problems = _broken(pilot, lambda w: w.tags.pop(w.gold_memories[0].key))
    assert any("no scenario tag" in p for p in problems)
    problems = _broken(pilot, lambda w: setattr(w.probes[0], "question_type", "history"))
    assert any("differs from question_type" in p or "not one of" in p for p in problems)


def test_validate_flags_user_memories_without_user_evidence_and_bad_adoption(pilot):
    # m_incident_ingest cites the user's words; strip them and only the assistant remains.
    def only_assistant(w):
        g = next(g for g in w.gold_memories if g.key == "m_incident_ingest")
        g.evidence_message_ids = ["s16:1", "s16:3"]

    assert any("no evidence is in the user's words" in p for p in _broken(pilot, only_assistant))

    def wrong_family(w):
        next(g for g in w.gold_memories if g.key == "m_backoff_jitter").adopted_from = "anthropic"

    assert any("that family's turn" in p for p in _broken(pilot, wrong_family))


# --- generate ------------------------------------------------------------------------------------------

PLAN = {
    "persona": {
        "name": "Ila Verrall",
        "summary": "An invented person for a test.",
        "projects": [{"id": "api", "name": "api", "description": "A work service.", "kind": "work"}],
        "traits": ["hedges and typos"],
    },
    "sessions": [
        {
            "id": "g1", "started_at": "2026-03-02T09:00:00+00:00", "app": "claude-code", "project": "api", "title": "First",
            "beats": [
                {"id": "b1", "speaker": "user", "content": "Ila says they live in Leeds", "indirect": False},
                {"id": "b2", "speaker": "user", "content": "Ila wishes aloud for a boat", "indirect": False},
                {"id": "b6", "speaker": "assistant", "content": "The assistant proposes weekly reviews", "indirect": False},
                {"id": "b7", "speaker": "user", "content": "Ila agrees: weekly reviews it is", "indirect": False},
            ],
        },
        {
            "id": "g2", "started_at": "2026-03-09T18:00:00+00:00", "app": "chatgpt", "project": None, "title": "Second",
            "beats": [
                {"id": "b3", "speaker": "user", "content": "Ila says they moved to York", "indirect": False},
                {"id": "b4", "speaker": "user", "content": "Ila mentions a new bike", "indirect": True},
            ],
        },
        {
            "id": "g3", "started_at": "2026-03-16T18:00:00+00:00", "app": "claude.ai", "project": None, "title": "Third",
            "beats": [{"id": "b5", "speaker": "user", "content": "Ila names their new cat", "indirect": False}],
        },
    ],
    "gold_memories": [
        {"key": "m1", "line": "Ila lives in Leeds.", "kind": "definition", "holder": "user", "evidence": ["b1"], "must_record": True, "scope": "personal", "adopted_from": None, "scenarios": ["S1"]},
        {"key": "m2", "line": "Ila lives in York.", "kind": "definition", "holder": "user", "evidence": ["b3"], "must_record": True, "scope": "personal", "adopted_from": None, "scenarios": ["S1"]},
        {"key": "m3", "line": "Ila would buy a boat.", "kind": "plan", "holder": "hypothetical", "evidence": ["b2"], "must_record": False, "scope": "personal", "adopted_from": None, "scenarios": ["S7"]},
        {"key": "m4", "line": "Ila's cat is called Pepper.", "kind": "definition", "holder": "user", "evidence": ["b5"], "must_record": True, "scope": "personal", "adopted_from": None, "scenarios": ["S16"]},
        {"key": "m5", "line": "Ila holds weekly reviews.", "kind": "approach", "holder": "user", "evidence": ["b6", "b7"], "must_record": True, "scope": "project:api", "adopted_from": "anthropic", "scenarios": ["S9"]},
        {"key": "m6", "line": "Nothing.", "kind": "definition", "holder": "user", "evidence": ["b5"], "must_record": True, "scope": "personal", "adopted_from": None, "scenarios": ["S99"]},
    ],
    "gold_updates": [
        {"key": "u1", "old": "m1", "new": "m2", "at": "b3", "reason": "user_later_statement", "scenarios": ["S1"]},
        {"key": "u2", "old": "m2", "new": "m4", "at": "b5", "reason": "implicit", "scenarios": ["S2"]},
    ],
    "probes": [
        {"id": "p1", "scenario": "S1", "kind": "current_state", "after": "b3", "question": "Where do I live?", "answer": "York.", "evidence": ["b3"], "forbidden_terms": []},
        {"id": "p2", "scenario": "S1", "kind": "history", "after": "b3", "question": "Where did I live before?", "answer": "Leeds.", "evidence": ["b1", "b3"], "forbidden_terms": []},
        {"id": "p3", "scenario": "S7", "kind": "attribution", "after": "b2", "question": "Do I want a boat?", "answer": "No, a wish.", "evidence": ["b2"], "forbidden_terms": ["boat yard", ""]},
        {"id": "p4", "scenario": "S1", "kind": "abstention", "after": "b3", "question": "What street?", "answer": "Not said.", "evidence": [], "forbidden_terms": []},
        {"id": "p5", "scenario": "S16", "kind": "current_state", "after": "b5", "question": "Cat name?", "answer": "Pepper.", "evidence": ["b5"], "forbidden_terms": []},
        {"id": "p6", "scenario": "S2", "kind": "history", "after": "b3", "question": "Wrong kind for S2.", "answer": "x", "evidence": ["b3"], "forbidden_terms": []},
    ],
}


class FakeWorld:
    """Scripted replies for each purpose. Rendering writes a "(bN)" marker for each beat it
    covers, and the fake checker finds markers, so the check reads the rendered text."""

    def __init__(self, plan=None, never=("b5",), second_try=("b4",)):
        self.plan = plan or PLAN
        self.never = set(never)  # beats no render ever covers
        self.second_try = set(second_try)  # beats the first render misses
        self.renders: Counter = Counter()
        self.requests: list[ModelRequest] = []
        self.port = StubModel(self.handle)

    def handle(self, req: ModelRequest):
        self.requests.append(req)
        payload = json.loads(req.messages[0]["content"])
        if req.purpose == "scenario.plan":
            return self.plan
        if req.purpose == "scenario.render":
            session = payload["session"]
            self.renders[session["id"]] += 1
            turns = []
            for beat in session["beats"]:
                if beat["id"] in self.never:
                    continue
                if beat["id"] in self.second_try and self.renders[session["id"]] < 2:
                    continue
                turns.append({"speaker": beat["speaker"], "text": f"{beat['content']} ({beat['id']})", "origin": "typed"})
            return {"messages": turns}
        if req.purpose == "scenario.mess":
            return {"messages": payload["messages"]}
        if req.purpose == "scenario.validate":
            verdicts = []
            for beat in payload["beats"]:
                found = [m["ordinal"] for m in payload["messages"] if f"({beat['id']})" in m["text"]]
                verdicts.append(
                    {"beat": beat["id"], "present": bool(found), "inferable": bool(found), "message_ordinals": found,
                     "note": "" if found else "not found in the text"}
                )
            return {"verdicts": verdicts}
        raise AssertionError(req.purpose)


def test_generation_schemas_are_strict():
    for schema in (gen.PLAN_SCHEMA, gen.RENDER_SCHEMA, gen.VALIDATE_SCHEMA):
        assert_strict(schema)


def test_generate_end_to_end_with_a_fake_port():
    fake = FakeWorld()
    world = gen.generate(fake.port, seed="a made-up person who moves house", n_sessions=3)
    assert validate(world) == []
    assert world.id == "ila-verrall" and world.persona.name == "Ila Verrall"
    # g3 had nothing that passed, so it has no messages and is left out.
    assert [s.id for s in world.sessions] == ["g1", "g2"]

    # Evidence ids come from the checker's located messages.
    by_key = {g.key: g for g in world.gold_memories}
    assert by_key["m1"].evidence_message_ids == ["g1:0"]
    assert by_key["m5"].evidence_message_ids == ["g1:2", "g1:3"] and by_key["m5"].adopted_from == "anthropic"
    update = next(u for u in world.gold_updates if u.key == "u1")
    assert update.at_message_id == "g2:0" and update.old_key == "m1" and update.new_key == "m2"
    p1 = next(p for p in world.probes if p.id == "p1")
    assert p1.meta["after_message_id"] == "g2:0" and p1.question_date == "2026-03-09T18:00:00+00:00"
    assert next(p for p in world.probes if p.id == "p3").meta["forbidden_terms"] == ["boat yard"]
    assert next(p for p in world.probes if p.id == "p4").abstention

    # The beat that never rendered is dropped, and so is everything that needed it.
    gen_meta = world.meta["generation"]
    dropped = {(d["kind"], d["id"]) for d in gen_meta["dropped"]}
    assert ("beat", "b5") in dropped
    assert {"m4", "u2", "p5"} <= {i for _, i in dropped}
    assert "m4" not in by_key and all(u.key != "u2" for u in world.gold_updates)
    assert all(p.id != "p5" for p in world.probes)
    # Bad plan items are recorded too: an unknown scenario tag, and a kind the scenario lacks.
    assert ("memory", "m6") in dropped and ("probe", "p6") in dropped
    assert gen_meta["rerendered"] == ["g2", "g3"]
    assert world.tags["p1"] == ["S1"] and world.tags["m5"] == ["S9"]


def test_generate_re_renders_a_failing_session_and_keeps_the_fixed_beat():
    fake = FakeWorld()
    world = gen.generate(fake.port, seed="x")
    g2 = next(s for s in world.sessions if s.id == "g2")
    assert [m.text for m in g2.messages] == ["Ila says they moved to York (b3)", "Ila mentions a new bike (b4)"]
    assert fake.renders == Counter({"g1": 1, "g2": 2, "g3": 2})
    # plan + g1 (render, mess, check) + g2 twice + g3 twice
    assert world.meta["generation"]["calls"] == 1 + 3 + 6 + 6
    assert not any(d["id"] == "b4" for d in world.meta["generation"]["dropped"] if d["kind"] == "beat")


def test_generate_never_lets_a_family_check_its_own_work():
    for writer in ("anthropic", "openai"):
        fake = FakeWorld()
        world = gen.generate(fake.port, seed="x", family=writer)
        by_purpose = {}
        for req in fake.requests:
            by_purpose.setdefault(req.purpose, set()).add(req.family)
        assert by_purpose["scenario.plan"] == by_purpose["scenario.render"] == by_purpose["scenario.mess"] == {writer}
        assert by_purpose["scenario.validate"] == {other_family(writer)}
        assert world.meta["generation"]["checker_family"] == other_family(writer)
        for req in fake.requests:
            assert req.schema is not None
            assert_strict(req.schema)
            assert {"scenario.plan": "worker", "scenario.render": "sim_user", "scenario.mess": "sim_user", "scenario.validate": "checker"}[req.purpose] == req.role


def test_generate_tags_assistant_turns_by_app_and_skips_mess_when_asked():
    fake = FakeWorld()
    world = gen.generate(fake.port, seed="x", messy=False, max_rerenders=0)
    assert "scenario.mess" not in {r.purpose for r in fake.requests}
    g1 = next(s for s in world.sessions if s.id == "g1")
    assistant = next(m for m in g1.messages if m.speaker == "assistant")
    assert (assistant.agent, assistant.model_family) == ("claude-code", "anthropic")
    assert g1.kind == "work" and g1.project == "api"
    # With no second try, the beat the first render misses is dropped, with its recorded reason.
    dropped = {d["id"]: d["why"] for d in world.meta["generation"]["dropped"] if d["kind"] == "beat"}
    assert "b4" in dropped and "failed the check" in dropped["b4"]
    assert world.meta["generation"]["rerendered"] == []
    assert validate(world) == []


def test_generate_rejects_an_unusable_session_and_a_bad_family():
    plan = copy.deepcopy(PLAN)
    plan["sessions"][1]["started_at"] = "next tuesday"
    world = gen.generate(FakeWorld(plan).port, seed="x")
    assert validate(world) == []
    assert all(s.id != "g2" for s in world.sessions)
    assert any(d["kind"] == "session" and d["id"] == "g2" for d in world.meta["generation"]["dropped"])
    with pytest.raises(ValueError):
        gen.generate(FakeWorld().port, seed="x", family="stub")


def test_generate_errors_when_a_reply_has_no_structured_output():
    port = StubModel(lambda req: "plain text, no schema parse")
    with pytest.raises(Exception):
        gen.generate(port, seed="x")


def test_validate_flags_messages_out_of_time_order(pilot):
    world = copy.deepcopy(pilot)
    world.sessions[0].messages[1].occurred_at = "2000-01-01T00:00:00"
    assert any("earlier than the message before it" in p for p in validate(world))


def test_generate_check_requires_the_beats_speaker_to_carry_it():
    plan = copy.deepcopy(PLAN)
    plan["sessions"][0]["beats"][0]["speaker"] = "assistant"  # b1 is planned as an assistant beat

    class WrongSpeaker(FakeWorld):
        def handle(self, req):
            out = super().handle(req)
            if req.purpose in ("scenario.render", "scenario.mess"):
                for t in out["messages"]:
                    t["speaker"] = "user"  # the render says it in the user's turn instead
            return out

    fake = WrongSpeaker(plan)
    world = gen.generate(fake.port, seed="x", max_rerenders=0)
    dropped = {d["id"] for d in world.meta["generation"]["dropped"] if d["kind"] == "beat"}
    assert "b1" in dropped
    assert validate(world) == []


def test_generate_drops_a_session_with_an_unknown_app():
    plan = copy.deepcopy(PLAN)
    plan["sessions"][1]["app"] = "notepad"
    world = gen.generate(FakeWorld(plan).port, seed="x")
    assert all(s.id != "g2" for s in world.sessions) and validate(world) == []
