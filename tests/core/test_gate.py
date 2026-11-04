"""The write gate: its order of checks, verdicts by tier, caps and the loss bound, stamping, and randomized mutations
of valid proposals (MEMORY-ARCHITECTURE §5.9, §5.12, §7). Every fixture is invented; see gate_fixtures.py."""

from __future__ import annotations

import json
import math
import random
from pathlib import Path

import pytest

from northstar_agent_memory.core import db, events, invariants as inv, ports
from northstar_agent_memory.core.gate import FULL_RULES, LOSS_BOUND_RULE, UserAuthority, WriteGate, op_tier, proposal_tier
from northstar_agent_memory.core.ids import new_id
from northstar_agent_memory.core.invariants import quote_problem
from northstar_agent_memory.core.ports import EvidenceQuote, Proposal, Verdict

from .gate_fixtures import CHECKER, M, NOW, SAID, SCOPE, WORK_FAMILY, YOU, FakeProjector, RaisingProjector, make_world, varied, world  # noqa: F401

THIRD = "third-family"


def found(result) -> set[str]:
    return {r.invariant for r in result.rejections}


def events_count(w) -> int:
    return w.count("event")


def reject(w, ops, invariant, *, user=False, **kw):
    """Apply ops (yours, through your authority, when `user`) and expect a rejection naming `invariant`, with nothing written."""
    before = events_count(w)
    result = w.apply_user(ops, **kw) if user else w.apply(ops, **kw)
    assert result.status == "rejected", result
    assert invariant in found(result), result.rejections
    assert events_count(w) == before
    return result


def add_correction(w, kind, target, params=None, status="active", via="click"):
    cid = w.next("co")
    with db.transaction(w.memory):
        w.memory.execute(
            "INSERT INTO correction (id, kind, target, via, params, at, status, lifted_reason, created_seq, seq_from)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0)",
            (cid, kind, target, via, json.dumps(params or {}), SAID, status, "your_undo" if status == "lifted" else None),
        )
    return cid


# --- the port, applying, stamping ---------------------------------------------------------------------------------


def test_it_is_a_memory_writer(world):
    assert isinstance(world.gate, ports.MemoryWriter)


def test_an_adopted_item_applies_and_who_said_it_is_stamped_from_history(world):
    ops = world.adopted("m1")
    result = world.apply(ops)
    assert result.status == "applied" and result.ok and len(result.applied_seqs) == 3
    assert result.applied_seqs == sorted(result.applied_seqs)
    rows = {r["id"]: r for r in world.memory.execute("SELECT * FROM evidence")}
    assert (rows["ev-m1-0"]["speaker"], rows["ev-m1-0"]["agent"], rows["ev-m1-0"]["model_family"], rows["ev-m1-0"]["origin"]) == (
        "assistant", "claude-code", "claude", "assistant_output"
    )
    assert (rows["ev-m1-1"]["speaker"], rows["ev-m1-1"]["origin"]) == ("user", "typed")
    item = world.memory.execute("SELECT * FROM item WHERE id = 'm1'").fetchone()
    assert item["origin"] == "adopted:claude-code" and item["check_status"] == "unchecked"
    stored = json.loads(world.memory.execute("SELECT payload FROM event WHERE type = 'item.created'").fetchone()[0])
    assert stored["origin"] == "adopted:claude-code"  # the log is self-contained (I18)
    anchored = json.loads(world.memory.execute("SELECT payload FROM event WHERE type = 'evidence.anchored' ORDER BY seq").fetchone()[0])
    assert anchored["speaker"] == "assistant" and anchored["model_family"] == "claude"


def test_an_item_from_your_words_is_yours(world):
    world.applied(world.yours("m1"))
    assert world.memory.execute("SELECT origin, check_status FROM item").fetchone()[:] == ("yours", "not_needed")


def test_events_carry_the_run_key_time_and_subjects(world):
    ops = world.yours("m1")
    proposal = world.proposal(ops)
    world.submit(proposal)
    rows = world.memory.execute("SELECT * FROM event ORDER BY seq").fetchall()
    assert [(r["run_id"], r["proposal_id"], r["index_in_proposal"]) for r in rows] == [
        (world.run_id, proposal.proposal_id, 0), (world.run_id, proposal.proposal_id, 1)
    ]
    assert {r["recorded_at"] for r in rows} == {NOW}
    assert json.loads(rows[1]["subjects"]) == ["m1"]
    assert world.count("event_subject", "subject_id = 'm1'") == 2  # the evidence's subject and the item's own


def test_the_proposal_is_not_changed_by_the_gate(world):
    ops = world.adopted("m1")
    proposal = world.proposal(ops)
    world.submit(proposal)
    assert all(op.payload["speaker"] is None and op.seq is None and op.recorded_at == "" for op in proposal.ops if op.type == "evidence.anchored")
    assert proposal.ops[-1].payload["origin"] is None


def test_a_low_tier_proposal_needs_no_verdict(world):
    op = world.op("work.labelled", dict(work_id="w1", label="One SQLite file per meter", label_source="commit_message"))
    assert proposal_tier([op]) == "low"
    assert world.apply([op], verdicts=[]).status == "applied"


def test_an_empty_proposal_is_refused(world):
    assert found(world.submit(Proposal(world.run_id, new_id(), []))) == {"I15"}


# --- verdicts by risk tier (§5.9) ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "make",
    [
        lambda w: None,  # none at all
        lambda w: w.verdict(WORK_FAMILY, full=False),  # the family that did the work, with a call of its own
        lambda w: w.verdict("code", full=False),  # the gate's own code is not an independent check
        lambda w: w.verdict(CHECKER, full=False, call=None),  # a check that names no recorded call
    ],
)
def test_a_medium_proposal_needs_one_passing_check_by_another_family(world, make):
    verdict = make(world)
    reject(world, world.yours("m1"), "verification", verdicts=[] if verdict is None else [verdict])


def test_a_medium_proposal_passes_with_one_check_by_another_family(world):
    assert world.apply(world.yours("m1"), verdicts=[world.verdict(full=False)]).status == "applied"


def test_a_failing_verdict_refuses_the_proposal_even_beside_a_passing_one(world):
    reject(world, world.yours("m1"), "verification", verdicts=[world.verdict(), world.verdict(THIRD, outcome="fail")])


def test_the_family_of_the_ai_that_said_the_claim_may_not_check_it(world):
    """Work from a claude session, but the claim was said by the other family's AI: that family is barred as well."""
    parts = [("S2:1", "a rolling baseline for the alerts", "primary"), ("S2:2", "A rolling baseline is a good idea", "adoption")]
    ops = world.item_ops("m1", "Alerts use a rolling baseline", parts)
    reject(world, ops, "verification", verdicts=[world.verdict(CHECKER)])
    assert world.apply(ops, verdicts=[world.verdict(THIRD)]).status == "applied"


def test_a_high_proposal_needs_a_full_effort_check(world):
    world.raw_item("m1")
    retire = [world.op("item.status_changed", dict(item_id="m1", from_status="active", to_status="retracted", reason="you said so"))]
    assert proposal_tier(retire) == "high"
    reject(world, retire, "verification", verdicts=[world.verdict(full=False)])
    reject(world, retire, "verification", verdicts=[world.verdict(rules=list(FULL_RULES[:-1]))])
    assert world.apply(retire, verdicts=[world.verdict(full=True)]).status == "applied"


def test_a_verdict_must_not_name_a_call_of_another_family(world):
    """The run store refuses to record it; a runs.db that holds one anyway is still not believed."""
    other = world.runs.record_call(ports.ModelCall("p", "m", "claude", "h2", ["S1:0"], run_id=world.run_id, raw_output="{}"))
    with pytest.raises(ValueError):
        world.runs.save_proposal(proposal := world.proposal(world.yours("m1"), verdicts=[world.verdict(CHECKER, call=other)]))
        world.runs.record_verdict(proposal.proposal_id, proposal.verdicts[0])
    p = world.proposal(world.yours("m1"), verdicts=[])
    world.plant(p, world.verdict(CHECKER, call=other))
    result = world.gate.apply(p)
    assert result.status == "rejected" and found(result) == {"verification"} and "not a openai call" in result.rejections[0].reason
    good = world.runs.record_call(ports.ModelCall("p", "m", CHECKER, "h3", ["S1:0"], run_id=world.run_id, raw_output="{}"))
    assert world.apply(world.yours("m2"), verdicts=[world.verdict(CHECKER, call=good)]).status == "applied"


def test_the_proposals_own_risk_tier_is_not_trusted(world):
    proposal = world.proposal(world.yours("m1"), verdicts=[])
    proposal.risk_tier = "low"
    result = world.submit(proposal)
    assert result.status == "rejected" and found(result) == {"verification"}


def test_recording_that_a_claim_has_no_check_is_low_risk(world):
    for status in ("not_needed", "unchecked"):
        op = world.op("item.checked", dict(item_id="m4", check_status=status))
        assert op_tier(op) == "low"
        assert world.apply([op], verdicts=[]).status == "applied"


def test_a_check_of_an_adopted_claim_names_a_family_a_verdict_backs(world):
    op = world.op("item.checked", dict(item_id="m4", check_status="checked", checker_family=CHECKER))
    assert world.apply([op], verdicts=[world.verdict(CHECKER, full=False)]).status == "applied"
    op = world.op("item.checked", dict(item_id="m4", check_status="checked", checker_family=THIRD))
    reject(world, [op], "verification", verdicts=[world.verdict(CHECKER, full=False)])


# --- 0 replay (I14) -----------------------------------------------------------------------------------------------


def test_applying_a_proposal_twice_changes_nothing(world):
    proposal = world.proposal(world.adopted("m1"))
    first = world.submit(proposal)
    again = world.submit(proposal)
    assert again.status == "duplicate" and again.ok and again.applied_seqs == first.applied_seqs
    assert (events_count(world), world.count("item"), world.count("evidence")) == (3, 1, 2)


def test_a_replayed_proposal_is_a_duplicate_even_after_its_run_ended_and_its_inputs_changed(world):
    world.raw_item("m0")
    proposal = world.proposal(world.yours("m1"), inputs=["m0@1"])
    first = world.submit(proposal)
    world.runs.finish_run(world.run_id, "applied")
    world.raw_item("other")
    world.memory.execute("UPDATE item SET version = 2 WHERE id = 'm0'")
    assert world.submit(proposal).applied_seqs == first.applied_seqs


def test_the_same_proposal_id_with_other_events_is_refused(world):
    proposal = world.proposal(world.yours("m1"))
    world.submit(proposal)
    tampered = world.proposal(world.yours("m2"))
    tampered.proposal_id = proposal.proposal_id
    for op in tampered.ops:
        op.proposal_id = proposal.proposal_id
    result = world.submit(tampered)
    assert result.status == "rejected" and found(result) == {"I14"}
    assert world.count("item") == 1


def test_an_op_must_carry_this_runs_key_and_its_own_index(world):
    ops = world.yours("m1")
    proposal = world.proposal(ops)
    proposal.ops[0].proposal_id = "another"
    assert "I14" in found(world.submit(proposal))
    proposal = world.proposal(world.yours("m2"))
    proposal.ops[1].index_in_proposal = 0
    assert "I14" in found(world.submit(proposal))
    proposal = world.proposal(world.yours("m3"))
    proposal.ops[1].run_id = "another-run"
    assert "I14" in found(world.submit(proposal))
    assert events_count(world) == 0


def test_an_event_id_or_item_that_exists_is_not_created_again(world):
    ops = world.yours("m1")
    world.applied(ops)
    clash = world.yours("m2")
    clash[0].id = ops[0].id
    assert "I14" in found(world.apply(clash))
    reject(world, world.yours("m1"), "I14")  # item m1 exists already


# --- 2 fencing ----------------------------------------------------------------------------------------------------


def test_a_proposal_of_a_run_that_is_not_current_is_fenced_out(world):
    world.runs.finish_run(world.run_id, "applied")
    reject(world, world.yours("m1"), "fencing")


def test_a_proposal_of_an_unknown_run_is_fenced_out(world):
    result = world.submit(world.proposal(world.yours("m1"), run_id=new_id()))
    assert found(result) == {"fencing"} and result.status == "rejected"


def test_a_newer_running_run_fences_out_the_older_one(world):
    world.runs.start_run("idle")
    reject(world, world.yours("m1"), "fencing")


def test_a_held_run_may_still_apply(world):
    world.runs.finish_run(world.run_id, "held")
    assert world.apply(world.yours("m1")).status == "applied"


def test_without_a_run_store_there_is_no_fencing(store_root):
    w = make_world(store_root, with_runs=False)
    try:
        assert w.apply(w.yours("m1"), run_id="anything").status == "applied"
    finally:
        w.close()


# --- 3 freshness --------------------------------------------------------------------------------------------------


def test_a_stale_input_version_requeues_the_proposal(world):
    world.raw_item("m0", version=2)
    result = world.apply(world.yours("m1"), inputs=["m0@1"])
    assert result.status == "requeued" and not result.ok and found(result) == {"freshness"}
    assert events_count(world) == 0
    assert world.apply(world.yours("m2"), inputs=["m0@2"]).status == "applied"
    assert world.apply(world.yours("m3"), inputs=["item:m0@2"]).status == "applied"


@pytest.mark.parametrize("text", ["missing@1", "message:nowhere:9@1", "m0@x", "link:nope@3"])
def test_an_input_that_is_gone_or_malformed_requeues(world, text):
    world.raw_item("m0")
    assert world.apply(world.yours("m1"), inputs=[text]).status == "requeued"


def test_a_message_input_that_is_in_history_is_fresh(world):
    assert world.apply(world.yours("m1"), inputs=["message:S1:0@1"]).status == "applied"


def test_an_input_this_proposal_creates_is_fresh(world):
    assert world.apply(world.yours("m1"), inputs=["m1@1"]).status == "applied"


def test_an_op_built_on_a_state_that_changed_requeues(world):
    world.raw_item("m0", version=2)
    revise = world.op("item.revised", dict(item_id="m0", base_version=1, line="A new line", reason="restated"))
    assert world.apply([revise]).status == "requeued"
    world.raw_item("m5")
    retire = world.op("item.status_changed", dict(item_id="m5", from_status="quarantined", to_status="active", reason="exit"))
    assert world.apply([retire]).status == "requeued"
    vanished = world.op("supersession.applied", dict(supersession_id="s1", old_item="gone", old_version=1, new_item="m5", reason="your_later_statement"))
    assert world.apply([vanished]).status == "requeued"


def test_freshness_comes_before_the_code_checks(world):
    world.raw_item("m0", version=2)
    ops = world.yours("m1")
    ops[0].payload["start_char"] += 3  # an I2 violation as well
    assert world.apply(ops, inputs=["m0@1"]).status == "requeued"


# --- 4 freezes ----------------------------------------------------------------------------------------------------


def test_a_frozen_change_type_is_refused(world):
    world.runs.freeze("new_item")
    reject(world, world.yours("m1"), "freeze")
    reject(world, world.adopted("m2"), "freeze")


def test_a_freeze_stops_automation_and_not_you(world):
    world.runs.freeze("topic_change")
    rename = lambda actor: [world.op("topic.renamed", dict(topic_id="t1", old_label="Energy", label="Home energy", label_fixed=True, reason="you renamed it"), actor=actor)]  # noqa: E731
    reject(world, rename(world.actor), "freeze")
    assert world.apply_user(rename("user")).status == "applied"


def test_another_change_type_is_not_frozen(world):
    world.runs.freeze("merge")
    assert world.apply(world.yours("m1")).status == "applied"


# --- 5 code checks, one invariant at a time -----------------------------------------------------------------------


def test_i1_evidence_must_exist_in_chat_history(world):
    ops = world.yours("m1")
    ops[0].payload["message_id"] = "S9:9"
    assert {"I1"} <= found(reject(world, ops, "I1"))
    ops = world.yours("m2")
    ops[-1].payload["evidence_ids"] = ["no-such-evidence"]
    reject(world, ops, "I1")


def test_i1_evidence_must_belong_to_the_item_that_cites_it(world):
    ops = world.yours("m1")
    ops[0].payload["subject_id"] = "someone-else"
    reject(world, ops, "I1")  # evidence for an item that does not exist, and cited by another


def test_i1_the_proposals_own_quotes_must_name_real_messages(world):
    proposal = world.proposal(world.yours("m1"))
    proposal.evidence = [EvidenceQuote("S9:9", 0, 5, "hello")]
    assert "I1" in found(world.submit(proposal))


def test_i2_a_quote_must_be_the_text_at_its_span(world):
    ops = world.yours("m1")
    ops[0].payload["start_char"] += 2
    ops[0].payload["end_char"] += 2
    reject(world, ops, "I2")
    ops = world.yours("m2")
    ops[0].payload["quote"] = "keep one SQLite file per sensor"
    reject(world, ops, "I2")
    ops = world.yours("m3")
    ops[0].payload["end_char"] = 10_000
    reject(world, ops, "I2")


def test_i2_spaces_and_unicode_are_normalized_before_comparing(world):
    ops = world.yours("m1")
    ops[0].payload["quote"] = "keep   one SQLite\nfile per meter"
    assert world.apply(ops).status == "applied"


def test_i2_the_proposals_own_quotes_are_checked_too(world):
    proposal = world.proposal(world.yours("m1"))
    proposal.evidence = [EvidenceQuote("S1:0", 0, 5, "keep one")]
    assert "I2" in found(world.submit(proposal))
    proposal = world.proposal(world.yours("m2"))
    proposal.evidence = [EvidenceQuote("S1:0", 6, 9, "keep")]  # wait: 'Let's keep'
    start = M["S1:0"][2].index("keep")
    proposal.evidence = [EvidenceQuote("S1:0", start, start + 4, "keep")]
    assert world.submit(proposal).status == "applied"


@pytest.mark.parametrize("field, value", [("speaker", "user"), ("agent", "claude-code"), ("model_family", "claude"), ("origin", "typed")])
def test_i3_a_proposal_carries_no_speaker_agent_family_or_origin(world, field, value):
    ops = world.adopted("m1")
    ops[0].payload[field] = value
    reject(world, ops, "I3")


def test_i3_a_proposal_cannot_set_an_items_origin(world):
    ops = world.yours("m1")
    ops[-1].payload["origin"] = "yours"
    reject(world, ops, "I3")
    ops = world.goal("g1")
    ops[-1].payload["origin"] = "yours"
    reject(world, ops, "I3")


def test_i3_a_speaker_swapped_in_the_payload_is_refused_even_when_it_agrees_with_nothing(world):
    ops = world.adopted("m1")
    ops[0].payload["speaker"] = "user"  # the AI's span claimed as yours
    ops[0].payload["origin"] = "typed"
    result = reject(world, ops, "I3")
    assert len([r for r in result.rejections if r.invariant == "I3"]) == 2


def test_i4_an_adopted_item_needs_a_span_of_words_you_typed(world):
    ops = world.adopted("m1")
    ops = [op for op in ops if op.payload.get("evidence_id") != "ev-m1-1"]
    ops[-1].payload["evidence_ids"] = ["ev-m1-0"]
    reject(world, ops, "I4")


@pytest.mark.parametrize("message, quote", [("S1:1", "keeping 1-minute readings"), ("S1:5", "the Pi Zero keeps up"), ("S1:4", "pytest: 12 passed")])
def test_i4_an_adoption_span_must_be_words_you_typed(world, message, quote):
    parts = [("S1:1", "keeping 1-minute readings for 7 days", "primary"), (message, quote, "adoption")]
    reject(world, world.item_ops("m1", "Readings are kept for 7 days", parts), "I4")


def test_i4_an_item_must_rest_on_you_or_an_ai_you_adopted(world):
    reject(world, world.item_ops("m1", "Tests pass", [("S1:4", "pytest: 12 passed", "primary")]), "I4")


def test_i4_a_stance_of_adopting_needs_words_you_typed(world):
    ops = world.yours("m1")
    ops += [world.evidence("ev-pasted", "m1", "S1:5", "the Pi Zero keeps up", "support")]
    ops += [world.op("stance.recorded", dict(item_id="m1", stance="adopted", evidence_ids=["ev-pasted"]))]
    reject(world, ops, "I4")
    ops = world.yours("m2")
    ops += [world.op("stance.recorded", dict(item_id="m2", stance="adopted", evidence_ids=["ev-m2-0"]))]
    assert world.apply(ops).status == "applied"


def test_i4_a_question_an_ai_raised_needs_your_typed_words_taking_it_up(world):
    ops = world.item_ops(
        "q1", "How do I avoid alert fatigue?", [("S2:0", "the dryer alert should fire", "primary")], kind="question",
        type_="question.created", raised_by="ai_taken_up",
    )  # fmt: skip
    reject(world, ops, "I4")


def test_i5_a_stated_goal_needs_words_you_typed(world):
    assert world.apply(world.goal("g1")).status == "applied"
    reject(world, world.goal("g2", "S2:0", "the dryer alert should fire when the cost doubles"), "I5")  # a chat app model's report
    reject(world, world.goal("g3", "S1:5", "the Pi Zero keeps up with six sensors"), "I5")  # pasted


def test_i5_a_reported_goal_is_stored_as_reported_and_sets_nothing_else(world):
    ops = world.goal("g1", "S2:0", "the dryer alert should fire when the cost doubles", basis="reported")
    assert world.apply(ops).status == "applied"
    assert world.memory.execute("SELECT goal_basis FROM item WHERE id = 'g1'").fetchone()[0] == "reported"


def test_i5_a_goal_is_never_an_ais_suggestion(world):
    ops = world.item_ops(
        "g1", "Use a rolling baseline", [("S2:1", "a rolling baseline for the alerts", "primary"), ("S2:2", "A rolling baseline is a good idea", "adoption")],
        kind="goal", type_="goal.created", basis="stated",
    )  # fmt: skip
    reject(world, ops, "I5", verdicts=[world.verdict(THIRD)])


def test_i5_confirming_or_finishing_a_goal_needs_your_typed_words(world):
    world.applied(world.goal("g1"))
    ops = [world.evidence("ev-c", "g1", "S1:5", "the Pi Zero keeps up", "support"), world.op("goal.confirmed", dict(item_id="g1", evidence_ids=["ev-c"]))]
    reject(world, ops, "I5")
    ops = [world.evidence("ev-d", "g1", "S1:6", "Keep the weekly report short", "support"), world.op("goal.status_changed", dict(item_id="g1", from_status="active", to_status="done", evidence_ids=["ev-d"]))]
    assert world.apply(ops).status == "applied"
    ops = [world.op("goal.status_changed", dict(item_id="g1", from_status="done", to_status="dropped", evidence_ids=[]))]
    reject(world, ops, "I5")


def test_i5_a_working_style_line_needs_your_typed_words(world):
    typed = [world.evidence("ev-s", "st1", "S1:6", "Always put the totals first", "support", "style_line")]
    style = lambda basis, eids: world.op("style.recorded", dict(style_id="st1", line="Totals first", scope="personal", basis=basis, evidence_ids=eids))  # noqa: E731
    assert world.apply(typed + [style("stated_default", ["ev-s"])]).status == "applied"
    pasted = [world.evidence("ev-p", "st2", "S1:5", "the Pi Zero keeps up", "support", "style_line")]
    ops = pasted + [world.op("style.recorded", dict(style_id="st2", line="Pi Zero", scope="personal", basis="stated_default", evidence_ids=["ev-p"]))]
    reject(world, ops, "I5")
    one = [world.evidence("ev-o", "st3", "S1:6", "Always put the totals first", "support", "style_line")]
    ops = one + [world.op("style.recorded", dict(style_id="st3", line="Totals", scope="personal", basis="seen_in_sessions", evidence_ids=["ev-o"]))]
    reject(world, ops, "I5")  # seen in one session only
    two = one + [world.evidence("ev-q", "st4", "S3:0", "I keep data in local files first", "support", "style_line")]
    two[0].payload["subject_id"] = "st4"
    ops = two + [world.op("style.recorded", dict(style_id="st4", line="Local files", scope="personal", basis="seen_in_sessions", evidence_ids=["ev-o", "ev-q"]))]
    assert world.apply(ops).status == "applied"


def test_i5_a_typed_correction_or_link_decision_needs_your_typed_words(world):
    ev = lambda eid, mid, quote: world.evidence(eid, "co1", mid, quote, "support", "correction", actor="user")  # noqa: E731
    correction = lambda eid: world.op("correction.applied", dict(correction_id="co1", kind="rename", target="t1", via="typed", at=SAID, constraint={"label_fixed": True}, evidence_id=eid), actor="user")  # noqa: E731
    reject(world, [ev("ev-r", "S2:0", "the dryer alert should fire"), correction("ev-r")], "I5", user=True)  # a report of your turn
    assert world.apply_user([ev("ev-t", "S1:6", "Keep the weekly report short"), correction("ev-t")]).status == "applied"
    link = world.op("link.rejected", dict(link_id="l1", via="typed", evidence_id="ev-r"), actor="user")
    reject(world, [world.evidence("ev-r", "l1", "S2:0", "the dryer alert", "support", "item", actor="user"), link], "I5", user=True)


MARKS = [
    ("correction.applied", dict(correction_id="co1", kind="pin", target="m1", via="click", at=SAID, constraint={})),
    ("correction.lifted", dict(correction_id="co1", reason="your_undo")),
    ("purge.applied", dict(purge_id="pg1", item_ids=["m1"], requested_at=SAID)),
    ("link.confirmed", dict(link_id="l1", via="click")),
    ("link.rejected", dict(link_id="l1", via="click")),
    ("goal.confirmed", dict(item_id="g1", evidence_ids=["ev-1"])),
    ("scope.hold_changed", dict(scope_id=SCOPE, held=True, reason="held")),
]


@pytest.mark.parametrize("type_, payload", MARKS)
def test_i5_your_marks_are_never_a_proposals_to_make_under_any_actor(world, type_, payload):
    """Attack: a proposal records your mark under the actor of its choice. The gate does not believe an actor field."""
    for actor in (world.actor, "code:overview", "code:capture", "user"):
        reject(world, [world.op(type_, payload, actor=actor)], "I5")


@pytest.mark.parametrize("type_, payload", [m for m in MARKS if m[0] not in ("purge.applied", "goal.confirmed")])
def test_i5_your_marks_go_through_your_authority(world, type_, payload):
    result = world.apply_user([world.op(type_, payload, actor="user")])
    assert result.status == "applied", result
    assert {e[0] for e in world.memory.execute("SELECT actor FROM event")} == {"user"}


def test_the_actor_user_is_refused_in_apply_for_any_op_and_needs_your_authority(world):
    plain = world.op("topic.renamed", dict(topic_id="t1", old_label="Energy", label="Home energy", label_fixed=True, reason="you renamed it"), actor="user")
    result = reject(world, [plain], "I5", verdicts=[])
    assert "apply_user" in result.rejections[0].reason
    assert world.apply_user([plain], verdicts=[]).status == "applied"


def test_a_code_module_acting_on_your_click_is_recorded_as_you(world):
    mark = world.op("correction.applied", dict(correction_id="co1", kind="pin", target="m1", via="click", at=SAID, constraint={}), actor="code:overview")
    proposal = world.proposal([mark], verdicts=[])
    assert world.gate.apply_user(world.record(proposal), YOU).status == "applied"
    assert [r[0] for r in world.memory.execute("SELECT actor FROM event")] == ["user"]
    assert mark.actor == "code:overview"  # the caller's proposal is not changed


def test_a_model_cannot_ride_on_your_authority(world):
    mine = world.op("topic.renamed", dict(topic_id="t1", old_label="A", label="B", label_fixed=False, reason="x"))
    reject(world, [mine], "I5", user=True)  # an op under a model's actor
    reject(world, world.yours("m1"), "I5", user=True)  # an item judged by a model's checks is not one of your marks
    for bad in (None, "not an authority", object()):
        result = world.gate.apply_user(world.record(world.proposal([mine])), bad)
        assert result.status == "rejected" and found(result) == {"authority"}


def test_an_authority_needs_the_explicit_flag_and_a_known_surface():
    with pytest.raises(ValueError):
        UserAuthority(surface="ui", user_action=False)
    with pytest.raises(ValueError):
        UserAuthority(surface="stage", user_action=True)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        UserAuthority("ui")  # type: ignore[call-arg]
    assert UserAuthority(surface="cli", user_action=True).surface == "cli"


def test_only_the_surfaces_that_are_yours_construct_a_user_authority():
    """Lint: no module of the package but gate.py (its definition) and the surfaces named in USER_SURFACE_MODULES builds one."""
    root = Path(inv.__file__).parents[1]
    allowed = {"core/gate.py", "cli.py", "capture.py", "ui.py"}
    for path in root.rglob("*.py"):
        rel = path.relative_to(root).as_posix()
        if "UserAuthority(" in path.read_text(encoding="utf-8"):
            assert rel in allowed, f"{rel} builds a UserAuthority; only your capture, overview and command line may"


def test_your_marks_need_no_model_verdict_and_are_not_high_tier(world):
    """Attack surface: item.status_changed to retracted is a high-tier retire for a model; for you it is a mark."""
    world.raw_item("m1")
    retire = world.op("item.status_changed", dict(item_id="m1", from_status="active", to_status="retracted", reason="not what I think"), actor="user")
    assert proposal_tier([retire]) == "low"  # yours: the same op under a model's actor is high
    assert proposal_tier([world.op("item.status_changed", dict(retire.payload))]) == "high"
    assert world.apply_user([retire], verdicts=[]).status == "applied"
    world.raw_item("m2")
    assert world.apply([world.op("item.status_changed", dict(item_id="m2", from_status="active", to_status="retracted", reason="x"))], verdicts=[]).status == "rejected"


def test_i7_no_derived_input(world):
    for text in ("start_note:t1@3", "change_log:run9@1", "overview:x@2", "model_output:call7@1", "topic_view:t1@1", "goal_card:g1@1"):
        result = reject(world, world.yours(world.next("m")), "I7", inputs=[text])
        assert "derived" in result.rejections[0].reason


def test_i7_an_input_must_be_a_typed_object(world):
    reject(world, world.yours("m1"), "I7", inputs=["notes:today@1"])


def test_i7_a_derived_input_on_one_op_is_refused_too(world):
    ops = world.yours("m1")
    ops[1].inputs = ["change_log:run9@1"]
    result = reject(world, ops, "I7")
    assert result.rejections[0].op_index == 1


def test_i11_i24_northstars_own_text_is_never_evidence(world):
    ops = world.item_ops("m1", "Hourly averages are enough", [("N1:0", "hourly averages are enough", "primary")])
    reject(world, ops, "I24")


def test_i11_an_item_cannot_rest_on_echoes_alone(world):
    ops = world.yours("m1")
    ops[0].payload["lineage"] = "northstar_echo"
    reject(world, ops, "I11")


def test_i12_a_merge_with_an_exact_key_applies(world):
    world.raw_item("a", "Readings are stored in SQLite, one file per meter")
    world.raw_item("b", "readings are stored in  SQLite, one file per meter")
    merge = world.op("link.applied", dict(link_id="l1", from_id="b", to_id="a", link_type="same_as", reason="same line", stated_by="northstar"))
    assert world.apply([merge]).status == "applied"
    assert world.memory.execute("SELECT status, merged_into FROM item WHERE id = 'b'").fetchone()[:] == ("superseded", "a")


def test_i12_a_merge_with_the_same_words_of_yours_applies(world):
    world.raw_item("a", "Line one")
    world.raw_item("b", "Line two")
    world.memory.execute("UPDATE item SET your_words = 'one SQLite file per meter' WHERE id IN ('a', 'b')")
    merge = world.op("link.applied", dict(link_id="l1", from_id="b", to_id="a", link_type="same_as", reason="your words", stated_by="northstar"))
    assert world.apply([merge]).status == "applied"


def test_i12_a_merge_with_two_agreeing_families_applies(world):
    world.raw_item("a", "Readings go to SQLite")
    world.raw_item("b", "Meter data is stored in SQLite")
    merge = world.op("link.applied", dict(link_id="l1", from_id="b", to_id="a", link_type="same_as", reason="same idea", stated_by="northstar", checked_by=[WORK_FAMILY, CHECKER]))
    assert world.apply([merge]).status == "applied"  # the family that proposed it and the one that checked it


def test_i12_a_merge_with_neither_an_exact_key_nor_two_families_is_refused(world):
    world.raw_item("a", "Readings go to SQLite")
    world.raw_item("b", "Meter data is stored in SQLite")
    merge = world.op("link.applied", dict(link_id="l1", from_id="b", to_id="a", link_type="same_as", reason="same idea", stated_by="northstar"), actor="model:other@1#deadbeef")
    reject(world, [merge], "I12")  # one family only: the checker; the proposer's call is not on record
    merge = world.op("link.applied", dict(link_id="l2", from_id="b", to_id="a", link_type="same_as", reason="same idea", stated_by="northstar"), actor="code:linker")
    reject(world, [merge], "I12")


def test_i12_a_different_scope_is_a_link_and_never_a_merge(world):
    world.raw_item("a", "Same line", scope=SCOPE)
    world.raw_item("b", "Same line", scope="personal")
    merge = world.op("link.applied", dict(link_id="l1", from_id="b", to_id="a", link_type="same_as", reason="same", stated_by="northstar"))
    assert "different scopes" in reject(world, [merge], "I12").rejections[0].reason


def test_i12_a_merge_names_items_that_exist_and_checkers_a_verdict_backs(world):
    world.raw_item("a", "Readings go to SQLite")
    world.raw_item("b", "Meter data is stored in SQLite")
    missing = world.op("link.applied", dict(link_id="l1", from_id="b", to_id="ghost", link_type="same_as", reason="x", stated_by="northstar"))
    reject(world, [missing], "I12")
    lying = world.op("link.applied", dict(link_id="l2", from_id="b", to_id="a", link_type="same_as", reason="x", stated_by="northstar", checked_by=[WORK_FAMILY, THIRD]))
    reject(world, [lying], "I12")


def test_i12_a_proposed_link_is_not_yet_a_merge(world):
    world.raw_item("a", "Readings go to SQLite")
    world.raw_item("b", "Meter data is stored in SQLite")
    proposed = world.op("link.proposed", dict(link_id="l1", from_id="b", to_id="a", link_type="same_as", reason="same idea", stated_by="northstar"))
    assert world.apply([proposed]).status == "applied"
    assert world.memory.execute("SELECT status FROM item WHERE id = 'b'").fetchone()[0] == "active"


# --- 7 caps and the loss bound (I13) ------------------------------------------------------------------------------


def retire(world, item_id, **kw):
    return world.op("item.status_changed", dict(item_id=item_id, from_status="active", to_status="retracted", reason="you said so"), **kw)


@pytest.fixture
def hundred(world):
    world.pad(100, "i")
    return world


def test_a_run_may_retire_five_percent_of_active_items(hundred):
    assert hundred.apply([retire(hundred, f"i{n}") for n in range(5)]).status == "applied"


def test_a_run_over_its_loss_bound_is_held(hundred):
    result = hundred.apply([retire(hundred, f"i{n}") for n in range(6)])
    assert result.status == "held" and not result.ok and found(result) == {"I13"}
    assert "second check" in result.rejections[0].reason and events_count(hundred) == 0


def test_the_loss_bound_counts_the_whole_run(hundred):
    assert hundred.apply([retire(hundred, f"i{n}") for n in range(3)]).status == "applied"
    assert hundred.apply([retire(hundred, f"i{n}") for n in range(3, 5)]).status == "applied"
    result = hundred.apply([retire(hundred, "i5")])
    assert result.status == "held" and found(result) == {"I13"}
    other_run = hundred.runs.start_run("manual")  # the next run starts from its own count
    hundred.runs.finish_run(hundred.run_id, "applied")
    assert hundred.apply([retire(hundred, "i5")], run_id=other_run).status == "applied"


def test_supersession_merge_and_quarantine_all_count_as_retiring(hundred):
    ops = [hundred.op("supersession.applied", dict(supersession_id=f"s{n}", old_item=f"i{n}", old_version=1, new_item=f"i{n + 50}", reason="ai_self_correction")) for n in range(2)]
    ops += [hundred.op("link.applied", dict(link_id="l1", from_id="i10", to_id="i11", link_type="same_as", reason="x", stated_by="northstar", checked_by=[WORK_FAMILY, CHECKER]))]
    ops += [hundred.op("item.status_changed", dict(item_id=f"i{n}", from_status="active", to_status="quarantined", reason="failed check")) for n in (20, 21, 22)]
    result = hundred.apply(ops)
    assert result.status == "held" and "6 items" in result.rejections[0].reason


def test_a_refresh_your_own_marks_and_the_same_item_retire_nothing(hundred):
    refresh = [hundred.op("supersession.applied", dict(supersession_id=f"s{n}", old_item=f"i{n}", old_version=1, new_item=f"i{n}", new_version=2, reason="refresh")) for n in range(10)]
    assert hundred.apply(refresh).status == "applied"
    yours = [retire(hundred, f"i{n}", actor="user") for n in range(20, 30)]
    assert hundred.apply_user(yours).status == "applied"


def test_a_second_check_releases_a_held_run(hundred):
    ops = [retire(hundred, f"i{n}") for n in range(6)]
    release = hundred.verdict(rules=[*FULL_RULES, LOSS_BOUND_RULE])
    assert hundred.apply(ops, verdicts=[release]).status == "applied"


def test_a_second_check_by_the_work_family_does_not_release_a_held_run(hundred):
    ops = [retire(hundred, f"i{n}") for n in range(6)]
    result = hundred.apply(ops, verdicts=[hundred.verdict(rules=[*FULL_RULES, LOSS_BOUND_RULE]), hundred.verdict(WORK_FAMILY, rules=[LOSS_BOUND_RULE])])
    assert result.status == "applied"  # the other family's release stands; the work family's adds nothing
    ops = [retire(hundred, f"i{n}") for n in range(10, 16)]
    result = hundred.apply(ops, verdicts=[hundred.verdict(WORK_FAMILY, rules=[*FULL_RULES, LOSS_BOUND_RULE])])
    assert result.status == "rejected" and found(result) == {"verification"}


def test_a_small_store_may_still_retire_one_item_per_run(world):
    for n in range(10):
        world.raw_item(f"i{n}")
    assert world.apply([retire(world, "i0")]).status == "applied"
    assert world.apply([retire(world, "i1")]).status == "held"


def test_the_loss_bound_is_read_from_the_config(store_root):
    w = make_world(store_root, config={"maintenance": {"loss_bound": 0.2, "loss_bound_min": 0}})
    try:
        for n in range(10):
            w.raw_item(f"i{n}")
        assert w.apply([retire(w, "i0"), retire(w, "i1")]).status == "applied"
        assert w.apply([retire(w, "i2")]).status == "held"
    finally:
        w.close()


def test_caps_per_proposal_and_per_run(store_root):
    w = make_world(store_root, config={"maintenance": {"max_ops_per_proposal": 3}})
    try:
        for n in range(4):
            w.raw_item(f"i{n}")
        ops = [w.op("item.status_changed", dict(item_id=f"i{n}", from_status="active", to_status="retracted", reason="x"), actor="user") for n in range(4)]
        reject(w, ops, "I13", user=True)
        assert w.apply_user(ops[:3]).status == "applied"
    finally:
        w.close()


def test_caps_on_topic_splits_merges_labels_and_idea_moves(world):
    def split(n):
        return world.op("topic.split", dict(topic_id=f"t{n}", redirect_to=f"u{n}", formation_overlap=0.5, reason="two clusters", new_topics=[dict(topic_id=f"u{n}", label="A", anchor_id="m1"), dict(topic_id=f"v{n}", label="B", anchor_id="m2")]))

    assert world.apply([split(1), split(2)]).status == "applied"
    result = world.apply([split(3)])  # a third, in the same run
    assert result.status == "rejected" and found(result) == {"I13"}
    other = world.runs.start_run("manual")
    world.runs.finish_run(world.run_id, "applied")
    assert world.apply([split(3)], run_id=other).status == "applied"
    rename = lambda n, actor=None: world.op("topic.renamed", dict(topic_id=f"r{n}", old_label="A", label="B", label_fixed=False, reason="x"), actor=actor)  # noqa: E731
    reject(world, [rename(n) for n in range(4)], "I13", run_id=other)
    assert world.apply_user([rename(n, "user") for n in range(6)], run_id=other).status == "applied"  # your renames are exempt
    move = lambda n: world.op("idea.moved", dict(item_id=f"m{n}", from_topic_id="t1", to_topic_id="t2", role="home", tentative=False, reason="weekly"))  # noqa: E731
    reject(world, [move(1), move(2)], "I13", run_id=other)


# --- I15, I16, I17, I20, I21, projection --------------------------------------------------------------------------


def test_i15_a_proposal_must_match_a_versioned_schema(world):
    ops = world.yours("m1")
    ops[1].payload["surprise"] = 1
    reject(world, ops, "I15")
    ops = world.yours("m2")
    ops[1].schema_version = 7
    result = reject(world, ops, "I15")
    assert "schema version 7" in result.rejections[0].reason
    proposal = world.proposal(world.yours("m3"))
    proposal.ops[1].type = "item.vanished"  # Proposal.build cannot tier an unknown type, so change it afterwards
    result = world.submit(proposal)
    assert result.status == "rejected" and "I15" in found(result)
    ops = world.yours("m4")
    del ops[1].payload["line"]
    reject(world, ops, "I15")
    ops = world.yours("m5")
    ops[1].compensates = new_id()
    reject(world, ops, "I15")  # undoes an event that does not exist


def test_i15_the_rejection_names_the_op_to_blame(world):
    ops = world.yours("m1")
    ops[1].payload["scope"] = "everywhere"
    assert reject(world, ops, "I15").rejections[0].op_index == 1


def test_i16_said_before_recorded_and_valid_times_consistent(world):
    reject(world, world.yours("m1", said_at="2026-03-06T09:00:00Z"), "I16")  # after the gate's clock
    reject(world, world.yours("m2", said_at="yesterday"), "I16")
    reject(world, world.yours("m3", valid_from="2026-03-09T00:00:00Z", valid_to="2026-03-01T00:00:00Z"), "I16")
    assert world.apply(world.yours("m4", valid_from="2026-03-01T00:00:00Z", valid_to="2026-03-09T00:00:00Z")).status == "applied"


def test_i16_evidence_from_a_message_dated_after_it_is_recorded(store_root):
    w = make_world(store_root)
    try:
        early = WriteGate(w.memory, w.history, FakeProjector(), runs=w.runs, config={}, clock=lambda: "2026-03-02T08:30:00.000Z")
        result = early.apply(w.record(w.proposal(w.yours("m1", said_at="2026-03-02T08:00:00Z"))))
        assert result.status == "rejected" and found(result) == {"I16"}
    finally:
        w.close()


def test_i16_a_later_statement_was_said_after_the_one_it_replaces(world):
    world.raw_item("old")
    world.raw_item("new")
    world.memory.execute("UPDATE item SET said_at = '2026-03-01T00:00:00Z' WHERE id = 'new'")
    supersede = lambda reason: world.op("supersession.applied", dict(supersession_id=world.next("s"), old_item="old", old_version=1, new_item="new", reason=reason))  # noqa: E731
    reject(world, [supersede("your_later_statement")], "I16")
    assert world.apply([supersede("ai_self_correction")]).status == "applied"


def test_i17_a_new_item_is_no_wider_than_where_it_was_learned(world):
    reject(world, world.yours("m1", scope="personal"), "I17")  # learned in a project chat
    reject(world, world.yours("m2", scope="project:de-course"), "I17")  # a different project
    ops = world.item_ops("m3", "Data lives in local files first", [("S3:0", "I keep data in local files first", "primary")], scope="personal")
    assert world.apply(ops).status == "applied"
    ops = world.item_ops("m4", "Data lives in local files first here", [("S3:0", "I keep data in local files first", "primary")], scope="project:energy-dash")
    assert world.apply(ops).status == "applied"  # you may narrow what you said in a chat outside any project


def test_i17_a_scope_widens_only_on_evidence_from_a_second_context(world):
    world.applied(world.yours("m1"))
    widen = lambda eid, mid, quote: [world.evidence(eid, "m1", mid, quote, "scope"), world.op("item.scope_widened", dict(item_id="m1", base_version=1, from_scope=SCOPE, to_scope="personal", evidence_ids=[eid]))]  # noqa: E731
    reject(world, widen("ev-w1", "S1:6", "Keep the weekly report short"), "I17")  # the same project
    assert world.apply(widen("ev-w2", "P1:0", "I also keep data in local files first")).status == "applied"
    assert world.memory.execute("SELECT scope FROM item WHERE id = 'm1'").fetchone()[0] == "personal"


def test_i17_a_revision_may_not_widen_a_scope(world):
    world.applied(world.yours("m1"))
    revise = world.op("item.revised", dict(item_id="m1", base_version=1, line="Readings are stored in SQLite", reason="restated", scope="personal"))
    reject(world, [revise], "I17")


def test_i20_evidence_is_anchored_once_and_never_changes(world):
    world.applied(world.yours("m1"))
    again = world.yours("m2")
    again[0].payload["evidence_id"] = "ev-m1-0"
    again[1].payload["evidence_ids"] = ["ev-m1-0"]
    reject(world, again, "I20")


CORRECTION_CASES = [
    ("not_what_i_think", "m1", {}, "item.status_changed", dict(item_id="m1", from_status="retracted", to_status="active", reason="exit")),
    ("not_what_i_think", "m1", {}, "item.revised", dict(item_id="m1", base_version=1, line="Another line", reason="restated")),
    ("project_only", "m1", {}, "item.scope_widened", dict(item_id="m1", base_version=1, from_scope=SCOPE, to_scope="personal", evidence_ids=["ev-s"])),
    ("rename", "t1", {}, "topic.renamed", dict(topic_id="t1", old_label="Energy", label="Home energy", label_fixed=False, reason="weekly")),
    ("move", "m1", {}, "idea.moved", dict(item_id="m1", from_topic_id="t1", to_topic_id="t2", role="home", tentative=False, reason="weekly")),
    ("keep_together", "t1", {}, "topic.split", dict(topic_id="t1", redirect_to="t3", formation_overlap=0.5, reason="x", new_topics=[dict(topic_id="t3", label="A", anchor_id="m1"), dict(topic_id="t4", label="B", anchor_id="m2")])),
    ("these_are_different", "a", {"with": "b"}, "link.applied", dict(link_id="l9", from_id="b", to_id="a", link_type="same_as", reason="same", stated_by="northstar", checked_by=[WORK_FAMILY, CHECKER])),
    ("these_are_different", "t1", {"with": "t2"}, "topic.merged", dict(from_topic_id="t2", into_topic_id="t1", reason="overlap")),
    ("give_own_topic", "t1", {}, "topic.folded_back", dict(topic_id="t1", into_parent_id="t0", reason="thin")),
    ("give_own_topic", "t1", {}, "topic.merged", dict(from_topic_id="t1", into_topic_id="t2", reason="overlap")),
    ("fold_back", "t1", {}, "topic.branched", dict(topic_id="t1", old_parent_id="t0", reason="separate")),
    ("not_part_of_this", "m1", {"topic": "t5"}, "idea.placed", dict(placement_id="p1", item_id="m1", topic_id="t5", role="home", tentative=False, reasons=["x"])),
    ("not_part_of_this", "m1", {"topic": "t5"}, "idea.moved", dict(item_id="m1", from_topic_id="t1", to_topic_id="t5", role="home", tentative=False, reason="weekly")),
    ("confirm_link", "l1", {}, "link.retracted", dict(link_id="l1", reason="an item it joins was retracted")),
    ("purge", "m1", {}, "item.checked", dict(item_id="m1", check_status="checked", checker_family=CHECKER)),
]


def seed_for_corrections(world):
    world.raw_item("m1")
    world.memory.execute("UPDATE item SET status = 'retracted' WHERE id = 'm1'")
    world.raw_item("a", "Readings go to SQLite")
    world.raw_item("b", "Meter data is stored in SQLite")
    with db.transaction(world.memory):
        world.memory.execute(
            "INSERT INTO link (id, from_id, to_id, type, reason, stated_by, status, created_seq, seq_from)"
            " VALUES ('l1', 'a', 'b', 'supports', 'x', 'northstar', 'applied', 0, 0)"
        )


@pytest.mark.parametrize("kind, target, params, type_, payload", CORRECTION_CASES)
def test_i21_an_automated_change_may_not_break_a_correction(world, kind, target, params, type_, payload):
    seed_for_corrections(world)
    op = lambda **kw: world.op(type_, dict(payload), **kw)  # noqa: E731
    if type_ == "item.scope_widened":
        world.memory.execute("UPDATE item SET status = 'active' WHERE id = 'm1'")
        extra = lambda **kw: [world.evidence("ev-s", "m1", "S3:0", "I keep data in local files first", "scope", **kw)]  # noqa: E731
    else:
        extra = lambda **kw: []  # noqa: E731
    if type_ == "item.revised":
        world.memory.execute("UPDATE item SET status = 'active' WHERE id = 'm1'")
    cid = add_correction(world, kind, target, params)
    result = reject(world, [*extra(), op()], "I21")
    assert cid in result.rejections[0].reason or any(cid in r.reason for r in result.rejections)
    # your own change is not an automated one, and a lifted correction no longer binds
    if type_ in inv.USER_AUTHORITY_OPS and type_ != "link.applied":
        assert world.apply_user([*extra(actor="user"), op(actor="user")]).status == "applied"


def test_i21_a_lifted_correction_no_longer_binds(world):
    seed_for_corrections(world)
    add_correction(world, "rename", "t1", status="lifted")
    rename = world.op("topic.renamed", dict(topic_id="t1", old_label="Energy", label="Home energy", label_fixed=False, reason="weekly"))
    assert world.apply([rename]).status == "applied"


def test_i21_a_correction_about_another_target_does_not_bind(world):
    seed_for_corrections(world)
    add_correction(world, "rename", "t9")
    rename = world.op("topic.renamed", dict(topic_id="t1", old_label="Energy", label="Home energy", label_fixed=False, reason="weekly"))
    assert world.apply([rename]).status == "applied"


def test_i21_a_rejected_link_is_never_proposed_again(world):
    seed_for_corrections(world)
    add_correction(world, "reject_link", "l1")
    again = world.op("link.proposed", dict(link_id="l8", from_id="a", to_id="b", link_type="supports", reason="again", stated_by="northstar"))
    reject(world, [again], "I21")
    other_type = world.op("link.proposed", dict(link_id="l9", from_id="a", to_id="b", link_type="refines", reason="other type", stated_by="northstar"))
    assert world.apply([other_type]).status == "applied"


def test_i21_later_evidence_never_lifts_a_correction(world):
    seed_for_corrections(world)
    add_correction(world, "not_what_i_think", "m1")
    ops = [world.evidence("ev-n", "m1", "S1:0", "keep one SQLite file per meter", "support"), world.op("item.status_changed", dict(item_id="m1", from_status="retracted", to_status="active", reason="said again"))]
    reject(world, ops, "I21")


def your_correction(w, item_id="m1"):
    op = w.op(
        "correction.applied",
        dict(correction_id="co-1", kind="not_what_i_think", target=item_id, via="click", params={}, constraint={"rule": "x"}, at=SAID),
        actor="user",
    )
    assert w.apply_user([op]).status == "applied"
    return op.id


def test_i21_an_automated_rollback_cannot_undo_your_correction(varied):
    w = varied
    w.applied(w.yours("m1"))
    event_id = your_correction(w)
    undo = lambda **kw: w.op("compensation.batch", dict(batch_id=w.next("b"), reason="undo", compensated_event_ids=[event_id]), **kw)  # noqa: E731
    reject(w, [undo()], "I21")
    assert w.count("correction") == 1
    # your own rollback is yours to make
    assert w.apply_user([undo(actor="user")]).status == "applied"


def test_i21_an_automated_rollback_of_automated_events_still_applies(varied):
    w = varied
    first = w.yours("m1")
    w.applied(first)
    batch = w.op("compensation.batch", dict(batch_id="b1", reason="bad run", compensated_event_ids=[e.id for e in first]))
    assert w.apply([batch]).status == "applied"


def test_a_malformed_actor_is_refused_not_a_crash(world):
    ops = world.yours("m1")
    ops[-1].actor = None
    result = world.apply(ops)
    assert result.status == "rejected" and "I15" in found(result)


def test_a_medium_proposal_from_an_unrecorded_model_call_is_refused(world):
    """With a run store, the family that did the work comes from a recorded call; with none recorded it is unknown,
    so no verdict can be shown independent of it (§5.12: outputs are recorded before they are read)."""
    world.actor = "model:extract@1#deadbeef"
    result = reject(world, world.adopted("m1"), "verification")
    assert "no recorded model call" in result.rejections[0].reason
    assert world.apply(world.adopted("m2"), verdicts=[world.verdict(WORK_FAMILY)]).status == "rejected"


def test_projection_errors_roll_everything_back(store_root):
    w = make_world(store_root, projector=RaisingProjector())
    try:
        result = w.apply(w.yours("m1"))
        assert result.status == "rejected" and found(result) == {"projection"}
        assert w.count("event") == 0 and w.count("event_subject") == 0 and w.count("item") == 0
        assert not w.memory.in_transaction
    finally:
        w.close()


def test_an_event_the_real_projector_cannot_apply_is_refused_and_leaves_nothing(store_root):
    from northstar_agent_memory.core.projector import Projector

    w = make_world(store_root, projector=Projector())
    try:
        ops = w.yours("m1") + [w.op("topic.renamed", dict(topic_id="no-such-topic", old_label="A", label="B", label_fixed=False, reason="x"))]
        result = w.apply(ops)
        assert result.status == "rejected" and found(result) == {"projection"}
        assert w.count("event") == 0 and w.count("item") == 0 and w.count("evidence") == 0
        assert w.apply(w.yours("m2")).status == "applied"  # and the gate is usable afterwards
    finally:
        w.close()


def test_other_projector_errors_roll_back_and_propagate(store_root):
    class Broken:
        def apply(self, conn, envelopes):
            raise RuntimeError("bug")

    w = make_world(store_root, projector=Broken())
    try:
        with pytest.raises(RuntimeError):
            w.apply(w.yours("m1"))
        assert w.count("event") == 0 and not w.memory.in_transaction
    finally:
        w.close()


def test_the_projector_sees_stamped_events_with_seq_in_order(store_root):
    seen = []

    class Spy:
        def apply(self, conn, envelopes):
            assert conn.in_transaction
            seen.extend((e.seq, e.type, e.payload.get("speaker") or e.payload.get("origin")) for e in envelopes)

    w = make_world(store_root, projector=Spy())
    try:
        w.applied(w.adopted("m1"))
        assert [s[0] for s in seen] == [1, 2, 3] and seen[0][2] == "assistant" and seen[2][2] == "adopted:claude-code"
    finally:
        w.close()


def test_a_gate_without_a_work_family_still_requires_a_checker(store_root):
    w = make_world(store_root, with_runs=False)
    try:
        reject(w, w.yours("m1"), "verification", verdicts=[])
        assert w.apply(w.yours("m2")).status == "applied"
        reject(w, w.adopted("m3"), "verification", verdicts=[w.verdict(WORK_FAMILY)])  # the claim's own family
    finally:
        w.close()


def test_the_gate_reads_the_config_when_none_is_given(store_root, isolated_home):
    (isolated_home / "data").mkdir(parents=True, exist_ok=True)
    (isolated_home / "data" / "settings.toml").write_text("[maintenance]\nmax_ops_per_proposal = 2\n", encoding="utf-8")
    w = make_world(store_root)
    try:
        gate = WriteGate(w.memory, w.history, FakeProjector(), runs=w.runs)
        assert gate.limits.max_ops_per_proposal == 2
        assert "I13" in found(gate.apply(w.record(w.proposal(w.adopted("m1")))))
    finally:
        w.close()


# --- randomized mutations of valid proposals ----------------------------------------------------------------------

SUBJECTS = ["Readings", "Hourly averages", "The logger", "Alerts", "The weekly report", "Charts", "The Pi Zero"]
VERBS = ["are stored in", "run on", "are kept for", "use", "are limited to", "stay in"]
OBJECTS = ["SQLite", "local files", "a rolling baseline", "hourly buckets", "one file per meter", "a small queue"]


def line(rng):
    return f"{rng.choice(SUBJECTS)} {rng.choice(VERBS)} {rng.choice(OBJECTS)} ({rng.randint(1, 9999)})"


def window(rng, message_id, low=2, high=5):
    words = M[message_id][2].split(" ")
    n = rng.randint(low, min(high, len(words)))
    i = rng.randint(0, len(words) - n)
    return " ".join(words[i : i + n])


def v_yours(w, rng):
    mid = rng.choice(["S1:0", "S1:6"])
    return w.proposal(w.item_ops(w.next("m"), line(rng), [(mid, window(rng, mid), "primary")], kind=rng.choice(["decision", "result", "conclusion", "plan"])))


def v_adopted(w, rng):
    parts = [("S1:1", window(rng, "S1:1"), "primary"), ("S1:2", window(rng, "S1:2"), "adoption")]
    return w.proposal(w.item_ops(w.next("m"), line(rng), parts))


def v_goal(w, rng):
    return w.proposal(w.goal(w.next("g"), "S1:3", window(rng, "S1:3")))


def v_supersede(w, rng):
    old, new = w.next("o"), w.next("n")
    w.raw_item(old, line(rng))
    w.raw_item(new, line(rng))
    reason = rng.choice(["ai_self_correction", "scope_split"])  # your_later_statement rests on your messages' times: see below
    return w.proposal([w.op("supersession.applied", dict(supersession_id=w.next("s"), old_item=old, old_version=1, new_item=new, reason=reason))])


def v_merge(w, rng):
    a, b, text = w.next("a"), w.next("b"), line(rng)
    w.raw_item(a, text)
    w.raw_item(b, text.upper() if rng.random() < 0.5 else text)  # the same line: an exact key
    return w.proposal([w.op("link.applied", dict(link_id=w.next("l"), from_id=b, to_id=a, link_type="same_as", reason="same line", stated_by="northstar"))])


def v_retire(w, rng):
    ids = [w.next("r") for _ in range(rng.randint(1, 5))]
    for item_id in ids:
        w.raw_item(item_id, line(rng))
    return w.proposal([retire(w, i) for i in ids])


VALID = {"yours": v_yours, "adopted": v_adopted, "goal": v_goal, "supersede": v_supersede, "merge": v_merge, "retire": v_retire}
ITEM_KINDS = ("yours", "adopted", "goal")


def evidence_ops(proposal):
    return [op for op in proposal.ops if op.type == "evidence.anchored"]


def m_offsets(w, rng, p):
    op = rng.choice(evidence_ops(p))
    pl = op.payload
    for _ in range(50):
        shift = rng.choice([-7, -3, -1, 1, 2, 5, 9])
        start = max(0, pl["start_char"] + shift)
        end = start + (pl["end_char"] - pl["start_char"])
        if quote_problem(M[pl["message_id"]][2], start, end, pl["quote"]):
            pl["start_char"], pl["end_char"] = start, end
            return


def m_speaker(w, rng, p):
    op = rng.choice(evidence_ops(p))
    op.payload["speaker"] = "user" if M[op.payload["message_id"]][0] != "user" else "assistant"


def m_origin_raised(w, rng, p):
    p.ops[-1].payload["origin"] = "yours"


def m_drop_adoption(w, rng, p):
    gone = [op for op in p.ops if op.payload.get("role") == "adoption"][0]
    p.ops.remove(gone)
    p.ops[-1].payload["evidence_ids"].remove(gone.payload["evidence_id"])
    for index, op in enumerate(p.ops):
        op.index_in_proposal = index


def m_adoption_by_assistant(w, rng, p):
    op = [op for op in p.ops if op.payload.get("role") == "adoption"][0]
    quote = window(rng, "S1:1")
    start = M["S1:1"][2].index(quote)
    op.payload.update(message_id="S1:1", quote=quote, start_char=start, end_char=start + len(quote))


def m_goal_from_report(w, rng, p):
    op = evidence_ops(p)[0]
    quote = window(rng, "S2:0")
    start = M["S2:0"][2].index(quote)
    op.payload.update(message_id="S2:0", quote=quote, start_char=start, end_char=start + len(quote))


def m_derived_input(w, rng, p):
    bad = rng.choice(["start_note:t1@3", "change_log:run9@1", "overview:x@2", "model_output:call7@1", "view:t3@1", "topic_view:t1@1"])
    p.inputs = [bad]
    for op in p.ops:
        op.inputs = [bad]


def m_stale_input(w, rng, p):
    name = w.next("stale")
    w.raw_item(name, version=2)
    p.inputs = [f"{name}@1"]
    for op in p.ops:
        op.inputs = [f"{name}@1"]


def m_merge_unbacked(w, rng, p):
    a, b = [w.next("a"), w.next("b")]
    w.raw_item(a, line(rng))
    w.raw_item(b, line(rng) + " and more")
    p.ops[0].payload.update(from_id=b, to_id=a)
    p.ops[0].actor = "model:elsewhere@1#" + "".join(rng.choice("0123456789abcdef") for _ in range(8))


def m_over_the_bound(w, rng, p):
    new_run = w.runs.start_run("manual")  # a run that has retired nothing yet
    w.runs.finish_run(w.run_id, "applied")
    w.run_id = new_run
    w.pad(rng.randint(0, 80), w.next("pad-"))
    active = w.memory.execute("SELECT COUNT(*) FROM item WHERE status = 'active'").fetchone()[0]
    count = math.floor(0.05 * active) + 1 + rng.randint(0, 3)
    while count <= math.floor(0.05 * (active + count)):  # the items to retire are active too
        count += 1
    ids = [w.next("x") for _ in range(count)]
    for item_id in ids:
        w.raw_item(item_id)
    p.run_id = new_run
    p.ops = [retire(w, i) for i in ids]
    for index, op in enumerate(p.ops):
        op.run_id, op.proposal_id, op.index_in_proposal = new_run, p.proposal_id, index


# name -> (applies to, mutator, expected status, expected invariant)
MUTATIONS = {
    "moved offsets": (ITEM_KINDS, m_offsets, "rejected", "I2"),
    "speaker swapped": (ITEM_KINDS, m_speaker, "rejected", "I3"),
    "origin raised": (("yours", "adopted"), m_origin_raised, "rejected", "I3"),
    "adoption without your span": (("adopted",), m_drop_adoption, "rejected", "I4"),
    "adoption by the AI's own words": (("adopted",), m_adoption_by_assistant, "rejected", "I4"),
    "goal from a model-reported turn": (("goal",), m_goal_from_report, "rejected", "I5"),
    "derived input": (tuple(VALID), m_derived_input, "rejected", "I7"),
    "merge without a key or two families": (("merge",), m_merge_unbacked, "rejected", "I12"),
    "run over its loss bound": (("retire",), m_over_the_bound, "held", "I13"),
    "stale input version": (tuple(VALID), m_stale_input, "requeued", "freshness"),
}


@pytest.mark.parametrize("seed", range(12))
def test_every_valid_proposal_applies_and_every_mutation_of_one_is_refused_for_the_right_reason(varied, seed):
    world = varied
    rng = random.Random(seed)
    world.pad(400)  # a run may retire 5% of 400 items
    for kind, build in VALID.items():
        proposal = build(world, rng)
        before = events_count(world)
        result = world.submit(proposal)
        assert result.status == "applied", (seed, kind, result)
        assert events_count(world) == before + len(proposal.ops)
    for name, (kinds, mutate, status, invariant) in MUTATIONS.items():
        for kind in kinds:
            proposal = VALID[kind](world, rng)
            mutate(world, rng, proposal)
            before = events_count(world)
            result = world.submit(proposal)
            assert (result.status, invariant in found(result)) == (status, True), (seed, name, kind, result)
            assert events_count(world) == before, (seed, name, kind)


@pytest.mark.parametrize("seed", range(12))
def test_a_proposal_applied_twice_applies_once(varied, seed):
    world = varied
    rng = random.Random(1000 + seed)
    world.pad(400)
    for kind, build in VALID.items():
        proposal = build(world, rng)
        first = world.submit(proposal)
        before = events_count(world)
        again = world.submit(proposal)
        assert (first.status, again.status) == ("applied", "duplicate"), (seed, kind)
        assert again.applied_seqs == first.applied_seqs and events_count(world) == before


@pytest.mark.parametrize("seed", range(6))
def test_a_replay_with_other_content_is_refused(world, seed):
    rng = random.Random(2000 + seed)
    first = v_yours(world, rng)
    world.submit(first)
    other = v_adopted(world, rng)
    other.proposal_id = first.proposal_id
    for op in other.ops:
        op.proposal_id = first.proposal_id
    result = world.submit(other)
    assert result.status == "rejected" and "I14" in found(result)


def test_the_mutation_table_covers_what_the_brief_names():
    assert set(MUTATIONS) == {
        "moved offsets", "speaker swapped", "origin raised", "adoption without your span", "adoption by the AI's own words",
        "goal from a model-reported turn", "derived input", "merge without a key or two families", "run over its loss bound",
        "stale input version",
    }


def test_valid_event_drafts_of_every_type_pass_intake(world):
    """Every one of the 42 example payloads is a valid draft: the gate's schema check is not stricter than events.py."""
    from .conftest import draft_payload

    for type_ in events.EVENT_TYPES:
        op = world.op(type_, draft_payload(type_))
        proposal = Proposal.build(world.run_id, [op])
        from northstar_agent_memory.core.invariants import Context, HistoryRead, MemoryRead, check_schema

        ctx = Context(proposal, proposal.ops, MemoryRead(world.memory), HistoryRead(world.history), NOW)
        assert check_schema(ctx) == [], type_
