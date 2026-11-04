"""The 42 event types, the envelope, validation (I3, I14, I15), risk tiers and the port records."""

from __future__ import annotations

import copy
import json
import re
from dataclasses import fields
from pathlib import Path

import pytest

from northstar_agent_memory.core import events, ports
from northstar_agent_memory.core.events import EventEnvelope, EventValidationError, validate
from northstar_agent_memory.core.ids import is_ulid, new_id

from .conftest import ACTOR, CONFIG, EXAMPLE_PAYLOADS, MODEL_ACTOR, draft_payload

SPEC = Path(__file__).parents[2] / "docs" / "design" / "revision-2026-10-23" / "MEMORY-ARCHITECTURE.md"

# §2.3's table, as the spec lists it (family -> types).
SPEC_FAMILIES = {
    "Evidence": ["evidence.anchored"],
    "Items": ["item.created", "item.revised", "item.value_changed", "item.scope_widened", "item.status_changed", "item.checked"],
    "Your moves": ["stance.recorded"],
    "Links": ["link.proposed", "link.applied", "link.confirmed", "link.rejected", "link.retracted"],
    "Supersession": ["supersession.applied", "supersession.undone"],
    "Conflicts": ["conflict.opened", "conflict.resolved", "conflict.reopened", "conflict.undone"],
    "Goals and questions": ["goal.created", "goal.status_changed", "goal.confirmed", "question.created", "question.status_changed"],
    "Your work": ["work.registered", "work.labelled"],
    "Working style": ["style.recorded", "style.revised"],
    "Corrections": ["correction.applied", "correction.lifted"],
    "Structure": ["topic.created", "topic.split", "topic.branched", "topic.merged", "topic.folded_back", "topic.renamed", "topic.dormant", "idea.placed", "idea.moved"],
    "Maintenance and privacy": ["compensation.batch", "purge.applied", "scope.hold_changed"],
}
ALL_TYPES = [t for types in SPEC_FAMILIES.values() for t in types]


# --- the catalog ---------------------------------------------------------------------------------------------------


def test_there_are_42_types_in_12_families():
    assert len(events.EVENT_TYPES) == 42 == len(set(events.EVENT_TYPES))
    assert len(events.FAMILIES) == 12
    assert len(events.PAYLOADS) == 42


def test_the_families_match_the_spec_table_in_order():
    assert [list(v) for v in events.FAMILIES.values()] == list(SPEC_FAMILIES.values())
    assert list(events.EVENT_TYPES) == ALL_TYPES


@pytest.mark.skipif(not SPEC.exists(), reason="the design docs are not in this checkout")
def test_the_catalog_matches_memory_architecture_section_2_3():
    text = SPEC.read_text(encoding="utf-8")
    section = text.split("There are 42 event types in 12 families")[1].split("The 2026-10-09 catalog")[0]
    rows = re.findall(r"^\| ([^|]+?) \| (`[^|]+`) \|$", section, flags=re.M)
    rows = [(f, re.findall(r"`([^`]+)`", ts)) for f, ts in rows if f not in ("Family",)]
    assert [(f, ts) for f, ts in rows] == [(f, SPEC_FAMILIES[f]) for f in SPEC_FAMILIES]
    assert sum(len(ts) for _, ts in rows) == 42


def test_each_type_has_a_payload_class_with_its_family():
    for type_ in events.EVENT_TYPES:
        cls = events.payload_class(type_)
        assert cls is not None and cls.TYPE == type_
        assert events.FAMILY_OF[type_] in events.FAMILIES
        assert type_ in events.FAMILIES[events.FAMILY_OF[type_]]
        assert cls.__doc__, f"{cls.__name__} needs a docstring that says what it holds"
    assert events.payload_class("item.created", 2) is None
    assert events.payload_class("item.dreamed") is None


def test_examples_cover_exactly_the_42_types():
    assert set(EXAMPLE_PAYLOADS) == set(events.EVENT_TYPES)


def test_every_payload_class_has_subject_fields_that_exist():
    for type_ in events.EVENT_TYPES:
        cls = events.payload_class(type_)
        names = {f.name for f in fields(cls)}
        assert cls.SUBJECTS, type_
        assert set(cls.SUBJECTS) <= names, type_
        assert set(cls.STAMPED) <= names and set(cls.STAMPED_REQUIRED) <= set(cls.STAMPED)


# --- valid envelopes -----------------------------------------------------------------------------------------------


@pytest.mark.parametrize("type_", ALL_TYPES)
def test_a_valid_stamped_envelope_of_every_type_validates(make_envelope, type_):
    env = make_envelope(type_)
    assert validate(env) is env
    assert events.problems(env) == []
    assert env.subjects, "subjects come from the payload"


@pytest.mark.parametrize("type_", ALL_TYPES)
def test_a_valid_draft_of_every_type_validates(make_envelope, type_):
    validate(make_envelope(type_, draft=True), draft=True)


@pytest.mark.parametrize("type_", ALL_TYPES)
def test_every_type_round_trips_through_json(make_envelope, type_):
    env = make_envelope(type_)
    text = events.to_json(env)
    assert events.from_json(text) == env
    assert text == events.to_json(events.from_json(text))  # canonical
    assert json.loads(text)["type"] == type_


def test_json_is_canonical_with_sorted_keys():
    env = events.make_event("link.confirmed", {"link_id": "l1", "via": "click"}, actor=ACTOR, config_version=CONFIG, id="01H0000000000000000000000A")
    text = events.to_json(env)
    keys = list(json.loads(text))
    assert keys == sorted(keys) and " " not in text.replace("l1", "")


def test_make_event_fills_defaults_and_subjects():
    env = events.make_event(
        "supersession.applied",
        {"supersession_id": "s1", "old_item": "m1", "old_version": 1, "new_item": "m2", "reason": "your_later_statement"},
        actor=MODEL_ACTOR, config_version=CONFIG,
    )
    assert env.payload["evidence_ids"] == [] and env.payload["new_version"] is None
    assert env.subjects == ["s1", "m1", "m2"]
    assert is_ulid(env.id)
    assert env.seq is None and env.recorded_at == ""
    explicit = events.make_event("link.confirmed", {"link_id": "l1", "via": "click"}, actor=ACTOR, config_version=CONFIG, subjects=["x"])
    assert explicit.subjects == ["x"]


def test_make_event_accepts_a_payload_dataclass():
    payload = events.LinkRetracted(link_id="l1", reason="gone")
    env = events.make_event("link.retracted", payload, actor=ACTOR, config_version=CONFIG)
    assert env.payload == {"link_id": "l1", "reason": "gone"} and env.subjects == ["l1"]


def test_ids_are_ulids_and_increase():
    a = EventEnvelope("link.confirmed", {}, ACTOR, CONFIG)
    b = EventEnvelope("link.confirmed", {}, ACTOR, CONFIG)
    assert a.id < b.id


def test_from_dict_refuses_unknown_envelope_fields():
    with pytest.raises(EventValidationError, match="unknown envelope field"):
        events.from_dict({"type": "link.confirmed", "payload": {}, "actor": ACTOR, "config_version": "c", "mood": "x"})
    with pytest.raises(EventValidationError):
        events.from_json("[1, 2]")


# --- rejections ----------------------------------------------------------------------------------------------------


def reject(env, *, draft=False, match=None):
    with pytest.raises(EventValidationError, match=match) as err:
        validate(env, draft=draft)
    assert err.value.problems
    return err.value.problems


def test_an_unknown_type_is_rejected(make_envelope):
    env = make_envelope("link.confirmed")
    env.type = "link.liked"
    reject(env, match="unknown event type")
    env.type = None
    reject(env, match="unknown event type")


@pytest.mark.parametrize("type_", ALL_TYPES)
def test_a_missing_required_field_is_rejected_for_every_type(make_envelope, type_):
    cls = events.payload_class(type_)
    required = [f.name for f in fields(cls) if f.default is f.default_factory and f.name not in cls.STAMPED]
    # dataclasses.MISSING is both sentinels when a field has no default
    assert required, type_
    for name in required:
        env = make_envelope(type_)
        del env.payload[name]
        assert any(f"missing field {name!r}" in p for p in reject(env)), (type_, name)


def test_a_wrongly_typed_field_is_rejected(make_envelope):
    env = make_envelope("item.created")
    env.payload["said_at"] = 20260302
    reject(env, match="said_at")
    env = make_envelope("item.created")
    env.payload["evidence_ids"] = "ev1"
    reject(env, match="evidence_ids")
    env = make_envelope("item.created")
    env.payload["evidence_ids"] = ["ev1", 2]
    reject(env, match=r"evidence_ids\[1\]")
    env = make_envelope("item.revised")
    env.payload["base_version"] = True  # a boolean is not an integer
    reject(env, match="base_version")
    env = make_envelope("item.revised")
    env.payload["base_version"] = "1"
    reject(env, match="base_version")
    env = make_envelope("topic.created")
    env.payload["label_fixed"] = "yes"
    reject(env, match="label_fixed")
    env = make_envelope("topic.created")
    env.payload["formation_overlap"] = "half"
    reject(env, match="formation_overlap")
    env = make_envelope("correction.applied")
    env.payload["constraint"] = ["not", "an", "object"]
    reject(env, match="constraint")
    env = make_envelope("topic.split")
    env.payload["formation_overlap"] = True
    reject(env, match="formation_overlap")
    env = make_envelope("link.confirmed")
    env.payload = ["link_id", "l1"]
    reject(env, match="payload must be an object")


def test_a_value_outside_an_enumeration_is_rejected(make_envelope):
    env = make_envelope("item.created")
    env.payload["kind"] = "idea"
    reject(env, match="kind")
    env = make_envelope("item.created")
    env.payload["kind"] = "goal"  # goals have their own event
    reject(env, match="kind")
    env = make_envelope("item.value_changed")
    env.payload["to_value"] = "forming"
    reject(env, match="to_value")  # value never moves back
    env = make_envelope("item.value_changed")
    env.payload["from_value"] = "kept"
    reject(env, match="from_value")
    env = make_envelope("link.applied")
    env.payload["link_type"] = "causes"
    reject(env, match="link_type")
    env = make_envelope("conflict.resolved")
    env.payload["step"] = 4
    reject(env, match="step")
    env = make_envelope("conflict.resolved")
    env.payload["step"] = True  # True == 1 but is not the number 1
    reject(env, match="step")
    env = make_envelope("item.scope_widened")
    env.payload["to_scope"] = "project:other"
    reject(env, match="to_scope")  # only to personal


def test_an_unknown_payload_field_is_rejected(make_envelope):
    env = make_envelope("link.confirmed")
    env.payload["mood"] = "pleased"
    reject(env, match="unknown field 'mood'")


def test_a_proposal_cannot_carry_speaker_or_origin_i3(make_envelope):
    # item.created has no speaker field at all
    env = make_envelope("item.created", draft=True)
    env.payload["speaker"] = "user"
    reject(env, draft=True, match="unknown field 'speaker'")
    # evidence.anchored has the stamped fields, but only the gate may fill them
    env = make_envelope("evidence.anchored", draft=True)
    validate(env, draft=True)
    for name, value in [("speaker", "user"), ("agent", "claude-code"), ("model_family", "claude"), ("origin", "typed"), ("context", "energy-dash")]:
        env = make_envelope("evidence.anchored", draft=True)
        env.payload[name] = value
        reject(env, draft=True, match=f"I3: {name}")
    env = make_envelope("item.created", draft=True)
    env.payload["origin"] = "yours"
    reject(env, draft=True, match="I3: origin")


def test_a_stamped_event_needs_its_stamps(make_envelope):
    env = make_envelope("evidence.anchored")
    env.payload["speaker"] = None
    reject(env, match="speaker must be stamped")
    env = make_envelope("evidence.anchored")
    env.payload["origin"] = None
    reject(env, match="origin must be stamped")
    env = make_envelope("evidence.anchored")
    env.payload["agent"] = None  # a user turn has no agent
    env.payload["model_family"] = None
    validate(env)
    env = make_envelope("evidence.anchored")
    env.payload["context"] = None
    reject(env, match="context must be stamped")
    env = make_envelope("item.created")
    env.payload["origin"] = None
    reject(env, match="origin must be stamped")
    env = make_envelope("item.created")
    env.payload["origin"] = "somebody"
    reject(env, match="origin must be")
    for ok in ("yours", "adopted:claude-code", "adopted:codex"):
        env = make_envelope("item.created")
        env.payload["origin"] = ok
        validate(env)


def test_a_payload_must_match_its_schema_version_i15(make_envelope):
    env = make_envelope("item.created", schema_version=2)
    reject(env, match="I15: item.created has no schema version 2")
    env = make_envelope("item.created", schema_version=0)
    reject(env, match="I15")
    env = make_envelope("item.created", schema_version="1")
    reject(env, match="schema_version must be an integer")
    assert events.SUPPORTED_SCHEMA_VERSIONS["item.created"] == (1,)


def test_a_future_schema_version_is_checked_against_its_own_fields(monkeypatch, make_envelope):
    """Registering a version 2 schema makes version 2 payloads valid and keeps version 1 payloads valid."""

    @events.dataclass
    class ItemValueChangedV2(events.ItemValueChanged):
        VERSION = 2
        note: str = ""

    monkeypatch.setitem(events.PAYLOADS, ("item.value_changed", 2), ItemValueChangedV2)
    env = make_envelope("item.value_changed", schema_version=2)
    env.payload["note"] = "x"
    validate(env)
    env = make_envelope("item.value_changed")  # version 1 does not know "note"
    env.payload["note"] = "x"
    reject(env, match="unknown field 'note'")


@pytest.mark.parametrize(
    ("change", "match"),
    [
        (dict(actor="somebody"), "actor"),
        (dict(actor=""), "actor"),
        (dict(config_version=""), "config_version"),
        (dict(subjects=[]), "subjects"),
        (dict(subjects=["m1", ""]), "subjects"),
        (dict(inputs=["m1"]), "object@version"),
        (dict(inputs=["m1@"]), "object@version"),
        (dict(id="not-a-ulid"), "ULID"),
        (dict(compensates="evt"), "compensates"),
        (dict(proposal_id="p1"), "come together"),
        (dict(index_in_proposal=0), "come together"),
        (dict(proposal_id="p1", index_in_proposal=0), "run_id"),
        (dict(run_id="r1", proposal_id="p1", index_in_proposal=-1), "index_in_proposal"),
        (dict(recorded_at=""), "recorded_at"),
    ],
)
def test_envelope_fields_are_checked(make_envelope, change, match):
    env = make_envelope("link.confirmed", **change)
    assert any(re.search(match, p) for p in reject(env))


def test_a_good_envelope_with_run_proposal_inputs_and_compensates_passes(make_envelope):
    env = make_envelope(
        "supersession.undone", run_id="r1", proposal_id="p1", index_in_proposal=2,
        inputs=["m5@1", "supersession:s1@1"], compensates=new_id(), actor=MODEL_ACTOR,
    )
    validate(env)


def test_a_draft_has_no_seq_and_may_lack_recorded_at(make_envelope):
    env = make_envelope("link.confirmed", draft=True)
    validate(env, draft=True)
    env.seq = 5
    reject(env, draft=True, match="no seq")
    env = make_envelope("link.confirmed")
    env.seq = 5  # an appended event
    validate(env)


def test_every_problem_is_listed(make_envelope):
    env = make_envelope("item.created", actor="x", config_version="")
    del env.payload["line"]
    env.payload["extra"] = 1
    found = reject(env)
    assert len(found) >= 4


# --- cross-field rules ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("type_", "change", "match"),
    [
        ("item.created", dict(evidence_ids=[]), "I1"),
        ("item.created", dict(scope="session:abc"), "scope"),
        ("item.created", dict(scope="galaxy"), "scope"),
        ("item.created", dict(line="  "), "line"),
        ("evidence.anchored", dict(end_char=5, start_char=5), "end_char"),
        ("evidence.anchored", dict(quote=" "), "quote"),
        ("item.scope_widened", dict(from_scope="personal"), "already personal"),
        ("item.scope_widened", dict(evidence_ids=[]), "second context"),
        ("item.status_changed", dict(to_status="active"), "same"),
        ("item.checked", dict(check_status="contradicted"), "evidence of its own"),
        ("item.checked", dict(checker_family=None), "names the family"),
        ("stance.recorded", dict(evidence_ids=[]), "I4"),
        ("link.applied", dict(link_type="supports"), "used_in"),
        ("link.applied", dict(to_kind="item"), "used_in"),
        ("link.applied", dict(reason=" "), "reason"),
        ("link.proposed", dict(to_id="m8", link_type="supports"), "different items"),
        ("link.confirmed", dict(via="typed"), "typed"),
        ("supersession.applied", dict(new_version=None), "names its version"),
        ("supersession.applied", dict(new_version=1), "greater"),
        ("conflict.opened", dict(side_b_item="m6"), "two different"),
        ("conflict.resolved", dict(winner=None), "winner"),
        ("conflict.resolved", dict(step=1, state="resolved", winner=None), "both_stand"),
        ("conflict.resolved", dict(step=3, state="contested"), "no winner"),
        ("goal.created", dict(evidence_ids=[]), "I1"),
        ("goal.confirmed", dict(evidence_ids=[]), "typed words"),
        ("goal.status_changed", dict(to_status="active"), "same"),
        ("question.status_changed", dict(answered_by=[]), "answers"),
        ("question.created", dict(evidence_ids=[]), "I1"),
        ("style.recorded", dict(evidence_ids=[]), "I5"),
        ("style.revised", dict(line=None), "changes the line"),
        ("correction.applied", dict(via="typed"), "I5"),
        ("topic.created", dict(parent_id="t2", topic_id="t2"), "own parent"),
        ("topic.created", dict(label=" "), "label"),
        ("topic.split", dict(new_topics=[{"topic_id": "t3", "label": "x", "anchor_id": "m1"}], redirect_to="t3"), "at least two"),
        ("topic.split", dict(redirect_to="t9"), "one of the new topics"),
        ("topic.split", dict(formation_overlap=1.5), "between 0 and 1"),
        ("topic.merged", dict(into_topic_id="t4"), "itself"),
        ("idea.placed", dict(reasons=["a", "b", "c"]), "two"),
        ("idea.moved", dict(to_topic_id="t5"), "different topic"),
        ("compensation.batch", dict(compensated_event_ids=[]), "at least one"),
        ("scope.hold_changed", dict(scope_id="everything"), "scope_id"),
    ],
)
def test_cross_field_rules(make_envelope, type_, change, match):
    env = make_envelope(type_)
    env.payload.update(change)
    assert any(re.search(match, p, re.I) for p in reject(env)), events.problems(env)


def test_valid_variants_of_cross_field_rules(make_envelope):
    for type_, change in [
        ("conflict.resolved", dict(step=1, state="both_stand", winner=None)),
        ("conflict.resolved", dict(step=3, state="contested", winner=None)),
        ("conflict.resolved", dict(step=0, state="resolved", winner="m6")),
        ("conflict.opened", dict(state="contested", question_id="m20")),
        ("supersession.applied", dict(old_item="m1", new_item="m2", new_version=None)),
        ("item.checked", dict(check_status="contradicted", evidence_ids=["ev30"])),
        ("item.checked", dict(check_status="not_independent", checker_family=None)),
        ("link.confirmed", dict(via="click", evidence_id=None)),
        ("correction.applied", dict(via="typed", evidence_id="ev5")),
        ("question.status_changed", dict(to_status="dormant", answered_by=[])),
        ("topic.dormant", dict(to_status="active")),
        ("scope.hold_changed", dict(scope_id="personal", held=False)),
        ("item.revised", dict(scope="personal", reason="project_only")),
    ]:
        env = make_envelope(type_)
        env.payload.update(change)
        validate(env)


# --- risk tiers (§5.9) ---------------------------------------------------------------------------------------------


def test_every_event_type_has_a_change_type_with_a_tier(make_envelope):
    for type_ in ALL_TYPES:
        env = make_envelope(type_)
        assert events.change_type(env) in events.RISK_TIER
        assert events.risk_tier(env) in events.RISK_TIERS


def test_every_tier_is_used_and_values_are_valid():
    assert set(events.RISK_TIER.values()) == {"low", "medium", "high"}
    assert set(events.RISK_TIERS) == {"low", "medium", "high"}


@pytest.mark.parametrize(
    ("change", "tier"),
    [
        # low: evidence; refresh; value from forming to kept; placement in an existing topic; work labels
        ("evidence", "low"), ("refresh", "low"), ("value_kept", "low"), ("placement", "low"), ("work_label", "low"),
        # medium: a new item from your move; an adoption; supports, refines and answers links; the check of an adopted claim
        ("new_item", "medium"), ("adoption", "medium"), ("link_supports", "medium"), ("link_refines", "medium"),
        ("link_answers", "medium"), ("adopted_claim_check", "medium"),
        # high: supersede; merge; a conflict opened or resolved; a widened scope; a broader idea; any topic change;
        # a claim marked contradicted; rollback
        ("supersede", "high"), ("merge", "high"), ("conflict_opened", "high"), ("conflict_resolved", "high"),
        ("scope_widened", "high"), ("broader_idea", "high"), ("topic_change", "high"), ("claim_contradicted", "high"),
        ("rollback", "high"),
    ],
)
def test_the_tier_table_follows_section_5_9(change, tier):
    assert events.RISK_TIER[change] == tier


@pytest.mark.parametrize(
    ("type_", "change", "expected"),
    [
        ("evidence.anchored", {}, "low"),
        ("item.created", {}, "medium"),
        ("item.revised", {"reason": "refresh"}, "low"),
        ("item.revised", {"reason": "your_revision"}, "medium"),
        ("item.value_changed", {}, "low"),
        ("item.scope_widened", {}, "high"),
        ("item.status_changed", {}, "high"),
        ("item.checked", {"check_status": "checked"}, "medium"),
        ("item.checked", {"check_status": "contradicted", "evidence_ids": ["e"]}, "high"),
        ("stance.recorded", {"stance": "adopted"}, "medium"),
        ("stance.recorded", {"stance": "stated"}, "low"),
        ("link.applied", {"link_type": "supports", "to_kind": "item", "to_id": "m9"}, "medium"),
        ("link.applied", {"link_type": "refines", "to_kind": "item", "to_id": "m9"}, "medium"),
        ("link.applied", {"link_type": "answers", "to_kind": "item", "to_id": "m9"}, "medium"),
        ("link.applied", {"link_type": "same_as", "to_kind": "item", "to_id": "m9"}, "high"),
        ("link.applied", {"link_type": "conflicts", "to_kind": "item", "to_id": "m9"}, "high"),
        ("link.applied", {"link_type": "case_of", "to_kind": "item", "to_id": "m9"}, "high"),
        ("link.applied", {"link_type": "used_in"}, "low"),
        ("link.applied", {"link_type": "used_in", "stated_by": "northstar"}, "medium"),
        ("link.applied", {"link_type": "advances", "to_kind": "item", "to_id": "m9"}, "low"),
        ("supersession.applied", {}, "high"),
        ("supersession.undone", {}, "high"),
        ("conflict.opened", {}, "high"),
        ("conflict.resolved", {}, "high"),
        ("goal.created", {}, "medium"),
        ("work.labelled", {}, "low"),
        ("topic.created", {}, "high"),
        ("topic.merged", {}, "high"),
        ("idea.placed", {}, "low"),
        ("idea.moved", {}, "high"),
        ("compensation.batch", {}, "high"),
    ],
)
def test_risk_tier_of_an_event(make_envelope, type_, change, expected):
    env = make_envelope(type_)
    env.payload.update(change)
    assert events.risk_tier(env) == expected


def test_max_tier_takes_the_riskiest():
    assert events.max_tier([]) == "low"
    assert events.max_tier(["low", "medium"]) == "medium"
    assert events.max_tier(["high", "low", "medium"]) == "high"


def test_change_type_refuses_an_unknown_type():
    with pytest.raises(ValueError):
        events.change_type(EventEnvelope("item.dreamed", {}, ACTOR, CONFIG))


# --- the port records ----------------------------------------------------------------------------------------------


def test_proposal_build_numbers_ops_and_takes_the_riskiest_tier(make_envelope):
    ops = [make_envelope("evidence.anchored", draft=True), make_envelope("item.created", draft=True), make_envelope("supersession.applied", draft=True)]
    proposal = ports.Proposal.build("run-1", ops, proposal_id="prop-1", inputs=["m5@1"], evidence=[ports.EvidenceQuote("A1", 0, 5, "Store")])
    assert proposal.risk_tier == "high"
    assert [(o.run_id, o.proposal_id, o.index_in_proposal) for o in proposal.ops] == [("run-1", "prop-1", 0), ("run-1", "prop-1", 1), ("run-1", "prop-1", 2)]
    assert all(o.inputs == ["m5@1"] for o in proposal.ops)
    for op in proposal.ops:
        validate(op, draft=True)
    assert proposal.evidence[0].quote == "Store" and proposal.abstentions == [] and proposal.verdicts == []


def test_proposal_build_generates_an_id_and_a_low_tier_for_low_ops(make_envelope):
    proposal = ports.Proposal.build("run-1", [make_envelope("evidence.anchored", draft=True)])
    assert is_ulid(proposal.proposal_id)
    assert proposal.risk_tier == "low"
    assert ports.Proposal.build("run-1", []).risk_tier == "low"


def test_verdict_and_apply_result():
    verdict = ports.Verdict("openai", ["meaning_both_ways", "attribution", "scope", "hedge"], "pass", True)
    assert verdict.passed and verdict.independent and verdict.id
    assert not ports.Verdict("code", [], "fail", True).passed
    applied = ports.ApplyResult("applied", [1041, 1042])
    assert applied.ok and applied.applied_seqs == [1041, 1042] and applied.rejections == []
    assert ports.ApplyResult("duplicate", [1041]).ok
    rejected = ports.ApplyResult("rejected", rejections=[ports.Rejection("I2", "quote is not in the message", 0)])
    assert not rejected.ok and rejected.rejections[0].invariant == "I2" and rejected.applied_seqs == []
    assert not ports.ApplyResult("requeued").ok and not ports.ApplyResult("held").ok


def test_the_seven_ports_are_protocols_with_their_main_calls():
    expected = {
        "HistoryStore": {"append_message", "append_work_event", "put_blob", "watermark"},
        "MemoryWriter": {"apply"},
        "MemoryReader": {"get_item", "changed_since", "subgraph", "events_since"},
        "WorkingStore": {"open_thread", "record_version", "add_live_decision", "record_receipt"},
        "IndexPort": {"search", "goal_card", "start_note", "record_use"},
        "OverviewStore": {"topics", "idea_view", "left_off", "layout", "mark_seen"},
        "RunStore": {"enqueue", "lease", "record_call", "quarantine", "log_change"},
    }
    for name, methods in expected.items():
        port = getattr(ports, name)
        assert methods <= {m for m in dir(port) if not m.startswith("_")}, name
    assert callable(getattr(ports.Projector, "apply"))


def test_a_class_with_the_methods_satisfies_a_port():
    class FakeWriter:
        def apply(self, proposal):
            return ports.ApplyResult("applied", [1])

        def apply_user(self, proposal, authority):
            return ports.ApplyResult("applied", [1])

    class FakeProjector:
        def apply(self, conn, envelopes):
            return None

    assert isinstance(FakeWriter(), ports.MemoryWriter)
    assert isinstance(FakeProjector(), ports.Projector)
    assert not isinstance(object(), ports.MemoryWriter)


def test_search_defaults_follow_the_push_rules():
    query = ports.SearchQuery("how do I store sensor readings")
    assert query.direction == "push" and query.top_n == 12 and query.allowed_scopes is None
    hit = ports.SearchHit("m1", 1, "2026-03-02 · decided by the user: SQLite", 0.03, ["words", "meaning"], "project:energy-dash", "decision")
    assert hit.found_by == ["words", "meaning"]


def test_examples_do_not_mutate_between_tests():
    original = copy.deepcopy(EXAMPLE_PAYLOADS)
    assert draft_payload("item.created") == {k: v for k, v in original["item.created"].items() if k != "origin"}
    assert EXAMPLE_PAYLOADS == original


# --- the context stamped on evidence, and a question's answers -------------------------------------------------------


def test_the_context_of_evidence_is_the_sources_project_or_personal():
    assert events.evidence_context("energy-dash") == "energy-dash"
    assert events.evidence_context(" energy-dash ") == "energy-dash"
    for none in (None, "", "   "):
        assert events.evidence_context(none) == events.PERSONAL_CONTEXT == "personal"


def test_a_proposal_cannot_name_the_context_of_its_evidence(make_envelope):
    """Attack: a model claims its evidence comes from a second context, to turn an item's value to kept."""
    assert "context" in events.EvidenceAnchored.STAMPED
    env = make_envelope("evidence.anchored", draft=True)
    validate(env, draft=True)
    env.payload["context"] = "personal"
    reject(env, draft=True, match="I3: context")


def test_a_stamped_event_may_carry_its_context_and_it_must_name_one(make_envelope):
    env = make_envelope("evidence.anchored")
    validate(env)  # the example has none: events before the gate stamped a context still validate
    env.payload["context"] = "energy-dash"
    validate(env)
    env.payload["context"] = "  "
    reject(env, match="context must name")


def test_the_context_is_not_part_of_what_a_draft_may_carry(make_envelope):
    assert "context" not in draft_payload("evidence.anchored")


@pytest.mark.parametrize(
    ("fields_", "match"),
    [
        (dict(to_status="answered", answered_by=[]), "names its answers"),
        (dict(to_status="dormant", answered_by=["m12"]), "only an answered question"),
        (dict(to_status="answered", answered_by=["m11"]), "cannot answer itself"),
        (dict(to_status="answered", answered_by=["m12", "m12"]), "each item once"),
    ],
)
def test_a_questions_answers_must_make_sense(make_envelope, fields_, match):
    env = make_envelope("question.status_changed")
    env.payload.update(fields_)
    reject(env, match=match)
