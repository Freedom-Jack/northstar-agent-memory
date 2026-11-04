"""Attacks on the write gate, each built the way an independent check built it: a proposal that claims something about
itself that the gate must find out for itself (MEMORY-ARCHITECTURE principle 4, §5.9, §5.12; GOAL §4.7). Every test
states the attack, and shows the gate refuses it now. Every fixture is invented; see gate_fixtures.py."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from northstar_agent_memory.core import db, invariants as inv, ports
from northstar_agent_memory.core.gate import FULL_RULES, LOSS_BOUND_RULE, NOT_INDEPENDENT, GateResult, WriteGate
from northstar_agent_memory.core.ports import Proposal, Verdict

from .gate_fixtures import CHECKER, NOW, PROMPT_HASH, SAID, SCOPE, TIME, WORK_FAMILY, FakeProjector, make_world, varied, world  # noqa: F401

THIRD = "third-family"
SCHEMA = Path(inv.__file__).parent / "schema"


def found(result) -> set[str]:
    return {r.invariant for r in result.rejections}


def events_count(w) -> int:
    return w.count("event")


def reject(w, ops, invariant, *, user=False, **kw):
    """Apply ops and expect a rejection naming `invariant`, with nothing written."""
    before = events_count(w)
    result = w.apply_user(ops, **kw) if user else w.apply(ops, **kw)
    assert result.status == "rejected", result
    assert invariant in found(result), result.rejections
    assert events_count(w) == before
    return result


def forge(w, ops, verdicts, **kw):
    """What a proposal can do alone: carry verdicts of its own. Nothing is recorded in runs.db for it."""
    return w.gate.apply(w.proposal(ops, verdicts=verdicts, **kw))


def item_op(ops):
    return next(op for op in ops if op.type in ("item.created", "goal.created", "question.created"))


# --- 1. forged verdicts: verdicts come from runs.db, never from the proposal ---------------------------------------------


def test_a_forged_independent_verdict_does_not_satisfy_a_medium_proposal(world):
    """Attack: Verdict('openai', ..., 'pass', independent=True) carried by the proposal, no call recorded anywhere."""
    forged = Verdict(CHECKER, ["meaning_both_ways"], "pass", True)
    before = events_count(world)
    result = forge(world, world.yours("m1"), [forged])
    assert result.status == "rejected" and found(result) == {"verification"} and events_count(world) == before
    assert "no proposal of this id is recorded" in result.rejections[0].reason


def test_a_forged_verdict_that_names_a_real_call_of_the_right_family_is_still_forged(world):
    call = world.call_for(CHECKER, world.run_id)  # the attacker copies a real call's id
    result = forge(world, world.yours("m1"), [Verdict(CHECKER, list(FULL_RULES), "pass", True, call)])
    assert result.status == "rejected" and found(result) == {"verification"}


def test_a_forged_verdict_does_not_satisfy_a_high_proposal(world):
    world.raw_item("m1")
    retire = [world.op("item.status_changed", dict(item_id="m1", from_status="active", to_status="retracted", reason="x"))]
    result = forge(world, retire, [Verdict(CHECKER, list(FULL_RULES), "pass", True)])
    assert result.status == "rejected" and found(result) == {"verification"}
    assert world.memory.execute("SELECT status FROM item WHERE id = 'm1'").fetchone()[0] == "active"


def test_forged_verdicts_do_not_give_a_merge_its_two_agreeing_families(world):
    """Attack: a merge with no exact key, backed by a forged verdict and a checked_by that names the forged family (I12)."""
    world.raw_item("a", "Readings go to SQLite")
    world.raw_item("b", "Meter data is stored in SQLite")
    merge = lambda: world.op("link.applied", dict(link_id=world.next("l"), from_id="b", to_id="a", link_type="same_as", reason="same idea", stated_by="northstar", checked_by=[WORK_FAMILY, CHECKER]))  # noqa: E731
    result = forge(world, [merge()], [Verdict(CHECKER, list(FULL_RULES), "pass", True)])
    assert result.status == "rejected" and "I12" in found(result)
    assert world.memory.execute("SELECT status FROM item WHERE id = 'b'").fetchone()[0] == "active"
    assert world.apply([merge()]).status == "applied"  # the same merge with a verdict the checker recorded


def test_a_recorded_verdict_is_read_from_runs_db_and_what_the_proposal_carries_is_ignored(world):
    ops = world.yours("m1")
    p = world.proposal(ops, verdicts=[world.verdict(CHECKER, full=False)])
    world.record(p)
    p.verdicts = [Verdict(THIRD, [], "fail", True)]  # a carried verdict, failing: not read
    assert world.gate.apply(p).status == "applied"
    p2 = world.proposal(world.yours("m2"), verdicts=[])
    world.plant(p2, world.verdict(CHECKER, full=False, outcome="fail"))  # a recorded failure binds
    p2.verdicts = [world.verdict(CHECKER, full=False)]  # carried passes are not read
    assert world.gate.apply(p2).status == "rejected"


def test_verdicts_recorded_for_other_ops_do_not_carry_over_to_a_proposal_of_the_same_id(world):
    """Attack: reuse the id of a proposal a checker passed, with ops nobody checked."""
    good = world.proposal(world.yours("m1"), verdicts=[world.verdict()])
    world.record(good)
    evil = world.proposal(world.yours("m2", line="Something nobody checked"), verdicts=good.verdicts)
    evil.proposal_id = good.proposal_id
    for op in evil.ops:
        op.proposal_id = good.proposal_id
    result = world.gate.apply(evil)
    assert result.status == "rejected" and found(result) == {"verification"}
    assert "judged other ops" in result.rejections[0].reason
    assert world.count("item") == 0


def test_a_verdict_must_name_a_recorded_call_of_this_run(world):
    other_run = world.runs.start_run("manual")
    elsewhere = world.runs.record_call(ports.ModelCall("p", "m", CHECKER, "h-else", ["S1:0"], run_id=other_run, raw_output="{}"))
    world.runs.finish_run(other_run, "cancelled")
    p = world.proposal(world.yours("m1"), verdicts=[])
    world.plant(p, world.verdict(CHECKER, call=elsewhere))
    result = world.gate.apply(p)
    assert found(result) == {"verification"} and "not recorded for this run" in result.rejections[0].reason
    p = world.proposal(world.yours("m2"), verdicts=[])
    world.plant(p, world.verdict(CHECKER, call=None))
    assert "names no model call" in world.gate.apply(p).rejections[0].reason


def test_a_verdict_must_not_name_the_work_s_own_call(world):
    work_call = world.runs.recorded_call(PROMPT_HASH, world.run_id)["id"]
    p = world.proposal(world.yours("m1"), verdicts=[])
    world.plant(p, world.verdict(WORK_FAMILY, call=work_call))
    result = world.gate.apply(p)
    assert found(result) == {"verification"} and "cannot check itself" in result.rejections[0].reason
    # nor a call that ran the work's prompt, whatever family it says
    same_prompt = world.runs.record_call(ports.ModelCall("p", "m", CHECKER, PROMPT_HASH, ["S1:0"], run_id=world.run_id, raw_output="{}"))
    p = world.proposal(world.yours("m2"), verdicts=[])
    world.plant(p, world.verdict(CHECKER, call=same_prompt))
    assert "cannot check itself" in world.gate.apply(p).rejections[0].reason


def test_a_verdict_must_name_a_call_that_succeeded(world):
    failed = world.runs.record_call(ports.ModelCall("p", "m", CHECKER, "h-err", ["S1:0"], run_id=world.run_id, raw_output="", status="error"))
    p = world.proposal(world.yours("m1"), verdicts=[])
    world.plant(p, world.verdict(CHECKER, call=failed))
    assert "did not succeed" in world.gate.apply(p).rejections[0].reason


def test_a_verdict_names_a_call_of_the_family_it_states(world):
    claude_call = world.runs.record_call(ports.ModelCall("p", "m", "claude", "h-c", ["S1:0"], run_id=world.run_id, raw_output="{}"))
    p = world.proposal(world.yours("m1"), verdicts=[])
    world.plant(p, world.verdict(CHECKER, call=claude_call))  # a runs.db that holds this anyway is not believed
    assert "is not a openai call" in world.gate.apply(p).rejections[0].reason


def test_without_a_run_store_the_proposals_own_verdicts_stand(store_root):
    """Tests only: with no runs.db there is nowhere to read them from."""
    w = make_world(store_root, with_runs=False)
    try:
        assert w.apply(w.yours("m1"), verdicts=[w.verdict(CHECKER, full=False, call=None)]).status == "applied"
        assert w.apply(w.adopted("m2"), verdicts=[w.verdict(WORK_FAMILY, call=None)]).status == "rejected"  # the AI's own family
    finally:
        w.close()


# --- 2. your_words and quoted whys are your typed words ---------------------------------------------------------------


def test_an_item_whose_your_words_appear_nowhere_in_your_typed_text_is_rejected(world):
    """Attack: your_words invented, with real evidence cited."""
    result = reject(world, world.yours("m1", your_words="never keep readings longer than a day"), "I2")
    assert "appear nowhere" in result.rejections[0].reason


@pytest.mark.parametrize("op_type", ["item.created", "goal.created", "question.created"])
def test_i2_covers_every_op_that_creates_an_item(world, op_type):
    extra = dict(basis="stated") if op_type == "goal.created" else dict(raised_by="you") if op_type == "question.created" else {}
    kind = {"item.created": "decision", "goal.created": "goal", "question.created": "question"}[op_type]
    parts = [("S1:3", "an alert when running the dryer costs double", "primary")]
    reject(world, world.item_ops("x1", "Alert on doubled cost", parts, kind=kind, type_=op_type, your_words="alert me when the dryer is on", **extra), "I2")
    ok = world.item_ops("x2", "Alert on doubled cost", parts, kind=kind, type_=op_type, your_words="an alert when running the dryer costs double", **extra)
    assert world.apply(ok).status == "applied"


def test_your_words_in_a_revision_are_checked_against_what_the_item_rests_on(world):
    world.applied(world.yours("m1"))
    revise = lambda words: world.op("item.revised", dict(item_id="m1", base_version=1, line="Readings are stored in SQLite", reason="restated", your_words=words))  # noqa: E731
    reject(world, [revise("never keep readings longer than a day")], "I2")
    assert world.apply([revise("one SQLite file per meter")]).status == "applied"


def test_your_words_must_be_words_you_typed_not_an_ais_or_pasted_ones(world):
    """Attack: your_words taken from an AI's span, a pasted note, a model's report of your turn, or a tool."""
    ai = world.adopted("m1", your_words="keeping 1-minute readings for 7 days")  # the AI's words, claimed as yours
    reject(world, ai, "I2")
    assert world.apply(world.adopted("m2", your_words="keep the 1-minute readings for 7 days")).status == "applied"  # your adoption span
    for mid, quote in (("S1:5", "the Pi Zero keeps up"), ("S2:0", "the dryer alert should fire"), ("S1:4", "12 passed")):
        parts = [("S1:0", "keep one SQLite file per meter", "primary"), (mid, quote, "support")]
        reject(world, world.item_ops(world.next("p"), "Readings go to SQLite", parts, your_words=quote), "I2")


def test_your_words_match_after_normalizing_spaces_and_unicode(world):
    assert world.apply(world.yours("m1", your_words="keep   one  SQLite\nfile per meter")).status == "applied"
    assert world.apply(world.yours("m2", your_words="")).status == "applied"  # none carries it: nothing to check


def test_a_quote_in_a_why_is_checked_like_your_words(world):
    """Attack: a why that presents an invented sentence as a quote of yours."""
    reject(world, world.yours("m1", why='You said "never throw readings away"'), "I2")
    assert world.apply(world.yours("m2", why='You said "keep one SQLite file per meter"')).status == "applied"
    assert world.apply(world.yours("m3", why="You wanted one file per meter, no quotation marks")).status == "applied"
    reject(world, world.yours("m4", why="Because “nobody will read raw rows”"), "I2")


def test_a_typed_corrections_label_is_your_typed_word(world):
    ev = lambda: world.evidence("ev-t", "co1", "S1:6", "Keep the weekly report short", "support", "correction", actor="user")  # noqa: E731
    correction = lambda label: world.op("correction.applied", dict(correction_id="co1", kind="rename", target="t1", via="typed", at=SAID, constraint={"label_fixed": True}, evidence_id="ev-t", params={"label": label}), actor="user")  # noqa: E731
    reject(world, [ev(), correction("Dryer alerts")], "I2", user=True)
    assert world.apply_user([ev(), correction("weekly report short")]).status == "applied"


# --- 3. the family rule covers the claim: every AI evidence row of every item an op touches ------------------------------

AI_PARTS = [("S2:1", "a rolling baseline for the alerts", "primary"), ("S2:2", "A rolling baseline is a good idea", "adoption")]  # an AI of another family said it


def adopted_from_other_family(w):
    w.applied(w.item_ops("m1", "Alerts use a rolling baseline", AI_PARTS), verdicts=[w.verdict(THIRD)])
    w.raw_item("m2", "Readings go to SQLite")


TOUCHING = {
    "item.checked": lambda w, family: w.op("item.checked", dict(item_id="m1", check_status="checked", checker_family=family)),
    "item.status_changed": lambda w, family: w.op("item.status_changed", dict(item_id="m1", from_status="active", to_status="retracted", reason="x")),
    "supersession.applied (old item)": lambda w, family: w.op("supersession.applied", dict(supersession_id="s1", old_item="m1", old_version=1, new_item="m2", reason="ai_self_correction")),
    "link.applied (an end)": lambda w, family: w.op("link.applied", dict(link_id="l1", from_id="m2", to_id="m1", link_type="supports", reason="x", stated_by="northstar")),
    "conflict.opened (a side)": lambda w, family: w.op("conflict.opened", dict(conflict_id="c1", side_a_item="m1", side_a_version=1, side_b_item="m2", side_b_version=1, kind="same_context", state="open")),
}


@pytest.mark.parametrize("name", list(TOUCHING))
def test_the_family_that_said_a_stored_claim_may_not_check_a_later_change_to_it(world, name):
    """Attack: an op about an item an AI of the other family said, in a proposal that cites none of that AI's words, checked
    by that same family. Only evidence in the same proposal was barred before."""
    adopted_from_other_family(world)
    op = TOUCHING[name]
    result = reject(world, [op(world, CHECKER)], "verification", verdicts=[world.verdict(CHECKER)])
    assert "said the claim" in result.rejections[0].reason
    assert world.apply([op(world, THIRD)], verdicts=[world.verdict(THIRD)]).status == "applied"


def test_the_claim_families_come_from_every_stored_ai_row_of_the_item(world):
    adopted_from_other_family(world)
    ctx_ops = [TOUCHING["supersession.applied (old item)"](world, THIRD)]
    proposal = Proposal.build(world.run_id, ctx_ops)
    ctx = inv.Context(proposal, proposal.ops, inv.MemoryRead(world.memory), inv.HistoryRead(world.history), NOW)
    assert ctx.claim_families() == {CHECKER}
    assert inv.touched_items(ctx_ops[0]) == ["m1", "m2"]


def test_the_family_that_did_the_work_stays_barred(world):
    reject(world, world.yours("m1"), "verification", verdicts=[world.verdict(WORK_FAMILY)])


# --- 4. user authority --------------------------------------------------------------------------------------------------


def purge_ops(world, *marks, item="m1"):
    return [*marks, world.op("purge.applied", dict(purge_id=world.next("pg"), item_ids=[item], requested_at=SAID), actor="user")]


def click(world, kind="purge", target="m1", cid="co1", **kw):
    return world.op("correction.applied", dict(correction_id=cid, kind=kind, target=target, via="click", at=SAID, constraint={}, **kw), actor="user")


def test_a_purge_needs_your_typed_words_or_a_recorded_click(world):
    """Attack: a purge nobody asked for, carried on a bare authority."""
    world.raw_item("m1")
    result = reject(world, purge_ops(world), "I5", user=True)
    assert "typed words or a recorded click" in result.rejections[0].reason
    reject(world, purge_ops(world, click(world, target="m9")), "I5", user=True)  # a request about another item
    assert world.apply_user(purge_ops(world, click(world))).status == "applied"


def test_a_typed_purge_request_needs_typed_words(world):
    world.raw_item("m1")
    typed = lambda mid, quote: [  # noqa: E731
        world.evidence("ev-p", "co1", mid, quote, "support", "correction", actor="user"),
        world.op("correction.applied", dict(correction_id="co1", kind="purge", target="m1", via="typed", at=SAID, constraint={}, evidence_id="ev-p"), actor="user"),
    ]
    reject(world, purge_ops(world, *typed("S2:0", "the dryer alert should fire")), "I5", user=True)  # a report of your turn
    assert world.apply_user(purge_ops(world, *typed("S1:6", "Keep the weekly report short"))).status == "applied"


def test_a_purge_request_you_recorded_earlier_counts(world):
    world.raw_item("m1")
    world.raw_item("m2")
    world.applied_user([click(world, target="m1")])
    assert world.apply_user(purge_ops(world)).status == "applied"
    reject(world, purge_ops(world, item="m2"), "I5", user=True)


def test_a_lifted_purge_request_does_not_count(world):
    world.raw_item("m1")
    world.memory.execute(
        "INSERT INTO correction (id, kind, target, via, params, at, status, lifted_reason, created_seq, seq_from)"
        " VALUES ('old', 'purge', 'm1', 'click', '{}', ?, 'lifted', 'your_undo', 0, 0)", (SAID,)
    )
    reject(world, purge_ops(world), "I5", user=True)


def test_authority_ops_still_face_the_code_checks(world):
    """Your authority lifts the model verdicts, not the code: a mark on words you did not type is refused."""
    ev = world.evidence("ev-g", "g1", "S1:5", "the Pi Zero keeps up", "support", actor="user")
    confirm = world.op("goal.confirmed", dict(item_id="g1", evidence_ids=["ev-g"]), actor="user")
    reject(world, [ev, confirm], "I5", user=True)


# --- 5. I21 for links: the link table binds ----------------------------------------------------------------------------


def two_items(w):
    w.raw_item("a", "Readings go to SQLite")
    w.raw_item("b", "Meter data is stored in SQLite")


def link_op(w, link_id, link_type="supports", from_id="a", to_id="b", **kw):
    return w.op("link.proposed", dict(link_id=link_id, from_id=from_id, to_id=to_id, link_type=link_type, reason="same topic", stated_by="northstar", **kw))


def you_reject(w, link_id):
    assert w.apply_user([w.op("link.rejected", dict(link_id=link_id, via="click"), actor="user")]).status == "applied"


def test_a_link_you_rejected_is_never_applied_or_proposed_again_by_automation(varied):
    """Attack: no correction row exists, only the link table says the link was rejected."""
    w = varied
    two_items(w)
    w.applied([link_op(w, "l1")])
    you_reject(w, "l1")
    assert w.count("correction") == 0 and w.memory.execute("SELECT status FROM link WHERE id = 'l1'").fetchone()[0] == "rejected"
    result = reject(w, [link_op(w, "l2")], "I21")
    assert "you rejected this link (l1)" in result.rejections[0].reason
    again = w.op("link.applied", dict(link_id="l3", from_id="a", to_id="b", link_type="supports", reason="again", stated_by="northstar"))
    reject(w, [again], "I21")
    assert w.apply([link_op(w, "l4", "refines")]).status == "applied"  # another type is another link
    assert w.apply([link_op(w, "l5", from_id="b", to_id="a")]).status == "applied"  # supports is not symmetric
    assert w.apply_user([w.op("link.applied", dict(link_id="l6", from_id="a", to_id="b", link_type="supports", reason="you said so", stated_by="you"), actor="user")]).status == "rejected"  # a model-judged link is not your authority's to carry


def test_a_rejected_symmetric_link_binds_either_way_round(varied):
    w = varied
    two_items(w)
    w.applied([link_op(w, "l1", "conflicts", checked_by=[WORK_FAMILY, CHECKER])])
    you_reject(w, "l1")
    reject(w, [link_op(w, "l2", "conflicts", "b", "a", checked_by=[WORK_FAMILY, CHECKER])], "I21")
    reject(w, [link_op(w, "l3", "conflicts", "a", "b", checked_by=[WORK_FAMILY, CHECKER])], "I21")


def test_a_link_you_confirmed_is_not_retracted_by_automation(varied):
    w = varied
    two_items(w)
    w.applied([link_op(w, "l1")])
    assert w.apply_user([w.op("link.confirmed", dict(link_id="l1", via="click"), actor="user")]).status == "applied"
    retract = lambda actor=None: w.op("link.retracted", dict(link_id="l1", reason="an item it joins was retracted"), actor=actor)  # noqa: E731
    result = reject(w, [retract()], "I21")
    assert "you confirmed this link" in result.rejections[0].reason
    assert w.memory.execute("SELECT status FROM link WHERE id = 'l1'").fetchone()[0] == "confirmed"
    assert w.apply_user([retract("user")]).status == "applied"  # yours to withdraw
    # a link nobody confirmed can still be retracted by automation
    w.applied([link_op(w, "l2", "refines")])
    assert w.apply([w.op("link.retracted", dict(link_id="l2", reason="x"))]).status == "applied"


def test_the_sweep_finds_an_automated_event_that_broke_your_word_about_a_link(varied):
    w = varied
    two_items(w)
    w.applied([link_op(w, "l1")])
    you_reject(w, "l1")
    swept = lambda: [v for v in inv.sweep({"memory": w.memory, "history": w.conns["history"]}) if v.invariant == "I21"]  # noqa: E731 (the raw items cite no evidence: I1's)
    assert swept() == []
    with db.transaction(w.memory):  # what a store damaged behind the gate's back would hold
        w.memory.execute(
            "INSERT INTO event (id, type, schema_version, subjects, payload, actor, run_id, config_version, recorded_at, inputs)"
            " VALUES ('01ARZ3NDEKTSV4RRFFQ69G5FAV', 'link.proposed', 1, '[\"l9\"]', ?, 'model:x@1#abc', NULL, 'c', ?, '[]')",
            (json.dumps(dict(link_id="l9", from_id="a", to_id="b", link_type="supports", reason="again", stated_by="northstar", to_kind="item", checked_by=[])), NOW),
        )
    assert [(v.invariant, "link l1" in v.reason) for v in swept()] == [("I21", True)]


# --- 6. value promotion: forming to kept on a signal code can see ------------------------------------------------------


def value_op(item="m1", signal="your_keep", ids=(), actor=None, w=None):
    return w.op("item.value_changed", dict(item_id=item, from_value="forming", to_value="kept", signal=signal, evidence_ids=list(ids)), actor=actor)


@pytest.mark.parametrize("signal", ["later_day", "built_on", "used_in_work", "second_context", "your_keep"])
def test_a_value_does_not_move_on_a_signal_nothing_shows(world, signal):
    """Attack: item.value_changed, any signal, no evidence of it."""
    world.applied(world.yours("m1"))
    result = reject(world, [value_op(signal=signal, w=world)], "I1")
    assert "does not move" in result.rejections[0].reason
    assert world.memory.execute("SELECT value FROM item WHERE id = 'm1'").fetchone()[0] == "forming"


def test_later_day_needs_your_words_on_two_different_days(world):
    world.applied(world.item_ops("m1", "Data lives in local files first", [("S3:0", "I keep data in local files first", "primary")], scope="personal"))
    same_day = [world.evidence("ev-a", "m1", "S1:6", "Always put the totals first", "support")]
    reject(world, [*same_day, value_op(signal="later_day", ids=["ev-a"], w=world)], "I1", verdicts=[])
    later = [world.evidence("ev-b", "m1", "S3:1", "Local files first also holds for my notes", "support")]
    assert world.apply([*later, value_op(signal="later_day", ids=["ev-b"], w=world)]).status == "applied"
    assert world.memory.execute("SELECT value FROM item WHERE id = 'm1'").fetchone()[0] == "kept"


def test_an_ais_words_on_a_later_day_are_not_yours(world):
    world.applied(world.adopted("m1"))
    ai_later = [world.evidence("ev-a", "m1", "S2:1", "a rolling baseline for the alerts", "support")]  # the same day, but even so
    reject(world, [*ai_later, value_op(signal="later_day", w=world)], "I1")


def test_second_context_needs_your_words_in_two_contexts(world):
    world.applied(world.item_ops("m1", "Data lives in local files first", [("S3:0", "I keep data in local files first", "primary")], scope="personal"))
    same = [world.evidence("ev-a", "m1", "S3:1", "Local files first also holds for my notes", "support")]  # the same context
    reject(world, [*same, value_op(signal="second_context", ids=["ev-a"], w=world)], "I1")
    other = [world.evidence("ev-b", "m1", "P1:0", "I also keep data in local files first", "support")]
    assert world.apply([*other, value_op(signal="second_context", ids=["ev-b"], w=world)]).status == "applied"


def test_the_evidence_context_is_read_from_the_stored_row_when_there_is_one(world):
    world.applied(world.item_ops("m1", "Data lives in local files first", [("S3:0", "I keep data in local files first", "primary")], scope="personal"))
    world.applied([world.evidence("ev-b", "m1", "P1:0", "I also keep data in local files first", "support")])
    ctx_ops = [value_op(signal="second_context", w=world)]
    proposal = Proposal.build(world.run_id, ctx_ops)
    ctx = inv.Context(proposal, proposal.ops, inv.MemoryRead(world.memory), inv.HistoryRead(world.history), NOW)
    assert {e.context for e in inv._item_evidence(ctx, "m1").values()} == {"personal", "de-course"}
    assert inv.value_signal_problem(ctx, ctx_ops[0]) is None


def test_your_keep_needs_a_keep_correction_of_yours(world):
    world.applied(world.yours("m1"))
    world.applied_user([click(world, "keep", "m1", "co-k")])
    assert world.apply([value_op(w=world)]).status == "applied"
    world.applied(world.yours("m2"))
    world.memory.execute("INSERT INTO correction (id, kind, target, via, params, at, status, lifted_reason, created_seq, seq_from) VALUES ('co-l', 'keep', 'm2', 'click', '{}', ?, 'lifted', 'your_undo', 0, 0)", (SAID,))
    reject(world, [value_op("m2", w=world)], "I1")  # a lifted keep is no keep
    reject(world, [click(world, "keep", "m2", "co-x")], "I5")  # and a model cannot make the keep itself


def test_a_keep_and_its_value_move_in_one_proposal_of_yours(world):
    world.applied(world.yours("m1"))
    assert world.apply_user([click(world, "keep", "m1", "co-k"), value_op(actor="user", w=world)]).status == "applied"


def test_built_on_needs_a_later_typed_stance_of_yours(world):
    world.applied(world.yours("m1"))  # said at 09:00
    build = lambda eid, mid, quote: [world.evidence(eid, "m1", mid, quote, "support"), world.op("stance.recorded", dict(item_id="m1", stance="built_on", evidence_ids=[eid]))]  # noqa: E731
    world.applied(build("ev-late", "S1:6", "Keep the weekly report short"))
    assert world.apply([value_op(signal="built_on", w=world)]).status == "applied"
    world.applied(world.item_ops("m2", "Weekly reports are short", [("S1:6", "Keep the weekly report short", "primary")]))  # said at 09:06
    world.applied(build_for(world, "m2", "ev-early", "S1:0", "keep one SQLite file per meter"))
    reject(world, [value_op("m2", "built_on", w=world)], "I1")  # a stance of yours from before it was said
    world.applied(build_for(world, "m2", "ev-ai", "S1:1", "keeping 1-minute readings for 7 days"))
    reject(world, [value_op("m2", "built_on", w=world)], "I1")  # nor an AI's


def build_for(w, item, eid, mid, quote):
    return [w.evidence(eid, item, mid, quote, "support"), w.op("stance.recorded", dict(item_id=item, stance="built_on", evidence_ids=[eid]))]


def add_work(w, work_id, evidence):
    with db.transaction(w.memory):
        w.memory.execute("INSERT INTO work (id, kind, ref, evidence, created_seq, seq_from) VALUES (?, 'commit', 'a41c9e0', ?, 0, 0)", (work_id, evidence))


def used_in(w, work_id, link_id="l1"):
    return w.op("link.applied", dict(link_id=link_id, from_id="m1", to_id=work_id, to_kind="work", link_type="used_in", reason="made in the same session as the commit", stated_by="construction"), actor="code:construction")


def test_used_in_work_needs_a_used_in_link_to_work_with_medium_or_strong_evidence(world):
    world.applied(world.yours("m1"))
    add_work(world, "w-weak", "weak")
    add_work(world, "w-medium", "medium")
    world.applied([used_in(world, "w-weak")])
    reject(world, [value_op(signal="used_in_work", w=world)], "I1")  # only opened, never touched
    world.applied([used_in(world, "w-medium", "l2")])
    assert world.apply([value_op(signal="used_in_work", w=world)]).status == "applied"


def test_a_used_in_link_made_in_the_same_proposal_counts_when_its_work_is_on_file(world):
    world.applied(world.yours("m1"))
    add_work(world, "w-strong", "strong")
    assert world.apply([used_in(world, "w-strong"), value_op(signal="used_in_work", w=world)]).status == "applied"


def test_a_value_that_is_kept_does_not_move_again_and_never_moves_back(world):
    world.applied(world.yours("m1"))
    world.applied_user([click(world, "keep", "m1", "co-k"), value_op(actor="user", w=world)])
    assert world.apply([value_op(w=world)]).status == "requeued"  # kept already
    back = value_op(w=world)
    back.payload.update(from_value="kept", to_value="forming")
    reject(world, [back], "I15")  # the schema has no way back


def test_the_evidence_a_value_cites_must_be_the_items_own(world):
    world.applied(world.yours("m1"))
    world.applied(world.yours("m2", line="Hourly averages are enough for monthly charts"))
    result = reject(world, [value_op("m1", "later_day", ["ev-m2-0"], w=world)], "I1")
    assert "not evidence of m1" in result.rejections[0].reason


# --- 7. said_at, learned_in, and a later statement by message time -----------------------------------------------------


def test_said_at_must_be_when_the_cited_message_of_yours_was_said(world):
    """Attack: said_at set to any time before the proposal is recorded."""
    result = reject(world, world.yours("m1", said_at=TIME["S1:6"]), "I16")
    assert "not when the message of yours" in result.rejections[0].reason
    reject(world, world.yours("m2", said_at="2026-03-01T00:00:00Z"), "I16")
    assert world.apply(world.yours("m3", said_at="2026-03-02T09:00:00Z")).status == "applied"  # the same moment, written another way


def test_an_adopted_items_said_at_is_the_adoption_message_not_the_ais(world):
    reject(world, world.adopted("m1", said_at=TIME["S1:1"]), "I16")  # when the AI said it
    assert world.apply(world.adopted("m2", said_at=TIME["S1:2"])).status == "applied"  # when you adopted it


@pytest.mark.parametrize("op_type, extra", [("goal.created", dict(basis="stated")), ("question.created", dict(raised_by="you"))])
def test_said_at_and_learned_in_are_checked_on_goals_and_questions(world, op_type, extra):
    kind = "goal" if op_type == "goal.created" else "question"
    parts = [("S1:3", "an alert when running the dryer costs double", "primary")]
    reject(world, world.item_ops("x1", "Alert on doubled cost", parts, kind=kind, type_=op_type, said_at=TIME["S1:0"], **extra), "I16")
    reject(world, world.item_ops("x2", "Alert on doubled cost", parts, kind=kind, type_=op_type, learned_in="S2", **extra), "I3")


def test_learned_in_must_be_the_source_or_context_of_the_cited_evidence(world):
    """Attack: an item that says it was learned somewhere else, to look like a second context."""
    result = reject(world, world.yours("m1", learned_in="S2"), "I3")
    assert "not the source or context" in result.rejections[0].reason
    reject(world, world.yours("m2", learned_in="de-course"), "I3")
    for ok in ("S1", "energy-dash", SCOPE):  # the source, its project, its scope
        assert world.apply(world.yours(world.next("o"), learned_in=ok)).status == "applied"


def later_statement_pair(w, old_message, new_message):
    quote = {"S1:0": "keep one SQLite file per meter", "S1:6": "Keep the weekly report short"}
    w.applied(w.item_ops("old", "Readings are stored in SQLite", [(old_message, quote[old_message], "primary")]))
    w.applied(w.item_ops("new", "Reports are short", [(new_message, quote[new_message], "primary")]))
    return w.op("supersession.applied", dict(supersession_id="s1", old_item="old", old_version=1, new_item="new", reason="your_later_statement"))


def test_a_later_statement_is_later_by_message_time(world):
    assert world.apply([later_statement_pair(world, "S1:0", "S1:6")]).status == "applied"


def test_a_later_statement_that_was_said_earlier_is_refused_whatever_the_items_say(world):
    """Attack: the new item's said_at field is made to look later than the old one's. The messages say otherwise."""
    supersede = later_statement_pair(world, "S1:6", "S1:0")  # the new item rests on the earlier message
    world.memory.execute("UPDATE item SET said_at = '2026-03-02T10:30:00Z' WHERE id = 'new'")  # a proposer-supplied field
    result = reject(world, [supersede], "I16")
    assert "not said after" in result.rejections[0].reason
    assert world.apply([world.op("supersession.applied", dict(supersession_id="s2", old_item="old", old_version=1, new_item="new", reason="ai_self_correction"))]).status == "applied"  # other reasons need no statement


def test_a_later_statement_needs_your_typed_words_for_the_new_item(world):
    world.raw_item("old")
    world.memory.execute("UPDATE item SET said_at = '2026-03-02T08:00:00Z' WHERE id = 'old'")
    world.applied(world.adopted("new"))
    supersede = world.op("supersession.applied", dict(supersession_id="s1", old_item="old", old_version=1, new_item="new", reason="your_later_statement"))
    assert world.apply([supersede]).status == "applied"  # old has only a said_at on file, and your adoption of new is later than it
    world.raw_item("old2")
    world.memory.execute("UPDATE item SET said_at = '2026-03-09T00:00:00Z' WHERE id = 'old2'")
    reject(world, [world.op("supersession.applied", dict(supersession_id="s2", old_item="old2", old_version=1, new_item="new", reason="your_later_statement"))], "I16")


# --- 8. the loss bound counts what a rollback removes ------------------------------------------------------------------


def batch_of(w, event_ids, actor=None, **kw):
    return w.op("compensation.batch", dict(batch_id=w.next("b"), reason="the audit disagreed", compensated_event_ids=list(event_ids), **kw), actor=actor)


@pytest.fixture
def six_items(varied):
    """100 padding items, and six more that one earlier run created; the run that rolls them back starts from zero."""
    w = varied
    w.pad(100, "i")
    created = [item_op(ops).id for ops in (w.yours(f"n{n}", line=f"Meter {n} logs to its own SQLite file") for n in range(6)) for _ in [w.applied(ops)]]
    w.later_run = w.runs.start_run("manual")
    w.runs.finish_run(w.run_id, "applied")
    return w, created


def test_an_automated_rollback_that_removes_more_than_the_loss_bound_is_held(six_items):
    """Attack: remove six items of 106 (the bound is five) through a compensation.batch, which retired_by never saw."""
    w, created = six_items
    result = w.apply([batch_of(w, created)], run_id=w.later_run)
    assert result.status == "held" and found(result) == {"I13"} and "6 items" in result.rejections[0].reason
    assert w.count("item", "id LIKE 'n%'") == 6  # nothing was rolled back
    assert w.apply([batch_of(w, created[:5])], run_id=w.later_run).status == "applied"  # five is within the bound
    if type(w.gate.projector).__name__ == "Projector":
        assert w.count("item", "id LIKE 'n%'") == 1  # the real projector took them away


def test_a_second_check_releases_a_rollback_held_for_the_loss_bound(six_items):
    w, created = six_items
    release = w.verdict(rules=[*FULL_RULES, LOSS_BOUND_RULE])
    assert w.apply([batch_of(w, created)], run_id=w.later_run, verdicts=[release]).status == "applied"


def test_rolling_back_a_whole_run_counts_the_items_it_created(six_items):
    w, created = six_items
    result = w.apply([batch_of(w, created[:1], run_id_undone=w.run_id)], run_id=w.later_run)
    assert result.status == "held" and "6 items" in result.rejections[0].reason


def test_rollbacks_in_one_run_add_up(six_items):
    w, created = six_items
    assert w.apply([batch_of(w, created[:3])], run_id=w.later_run).status == "applied"
    result = w.apply([batch_of(w, created[3:])], run_id=w.later_run)  # three more: six in the run
    assert result.status == "held" and "6 items" in result.rejections[0].reason


def test_a_rollback_that_brings_back_a_retired_item_counts_as_retiring_it(six_items):
    w, _ = six_items
    memory = inv.MemoryRead(w.memory)
    restored = w.op("item.status_changed", dict(item_id="n0", from_status="retracted", to_status="active", reason="exit"))  # an earlier event: the batch would undo it
    with db.transaction(w.memory):
        w.memory.execute("INSERT INTO event (id, type, schema_version, subjects, payload, actor, config_version, recorded_at, inputs) VALUES (?, 'item.status_changed', 1, '[\"n0\"]', ?, 'code:x', 'c', ?, '[]')", (restored.id, json.dumps(restored.payload), NOW))
    assert inv.batch_losses(memory, dict(compensated_event_ids=[restored.id])) == {"n0"}
    assert inv.batch_losses(memory, dict(compensated_event_ids=["no-such-event"])) == set()


def test_your_own_rollback_is_not_counted(six_items):
    w, created = six_items
    assert w.apply_user([batch_of(w, created, actor="user")], run_id=w.later_run).status == "applied"


# --- 9. no other family left: the check is labelled "not independent" and the change applies ---------------------------


def sole_family_gate(w, families):
    return WriteGate(w.memory, w.history, FakeProjector(), runs=w.runs, config={}, clock=lambda: NOW, families=families)


def not_independent(w, family=WORK_FAMILY, *, full=True, **kw):
    return w.verdict(family, full=full, independent=False, **kw)


def test_where_no_other_family_is_left_the_change_applies_labelled_not_independent(world):
    gate = sole_family_gate(world, [WORK_FAMILY])
    p = world.record(world.proposal(world.yours("m1"), verdicts=[not_independent(world)]))
    result = gate.apply(p)
    assert result.status == "applied" and isinstance(result, GateResult) and result.labels == [NOT_INDEPENDENT]
    rows = world.runs.verdicts(p.proposal_id)  # and runs.db keeps the label
    assert [(r["checker_family"], r["independent"]) for r in rows] == [(WORK_FAMILY, 0)]
    assert world.count("item") == 1


def test_a_check_by_the_work_s_own_family_is_refused_while_another_family_is_left(world):
    gate = sole_family_gate(world, [WORK_FAMILY, CHECKER])
    p = world.record(world.proposal(world.yours("m1"), verdicts=[not_independent(world)]))
    result = gate.apply(p)
    assert result.status == "rejected" and found(result) == {"verification"} and "another family is left" in result.rejections[0].reason
    assert world.count("item") == 0


def test_when_the_families_are_not_known_the_recorded_label_stands(world):
    gate = sole_family_gate(world, None)
    p = world.record(world.proposal(world.yours("m1"), verdicts=[not_independent(world)]))
    assert gate.apply(p).labels == [NOT_INDEPENDENT]


def test_a_check_labelled_not_independent_still_needs_its_own_recorded_call(world):
    gate = sole_family_gate(world, [WORK_FAMILY])
    for bad in (not_independent(world, call=None), not_independent(world, call=world.runs.recorded_call(PROMPT_HASH, world.run_id)["id"])):
        p = world.proposal(world.yours(world.next("m")), verdicts=[])
        world.plant(p, bad)
        assert gate.apply(p).status == "rejected"


def test_a_lie_of_independence_by_the_works_own_family_is_not_believed(world):
    gate = sole_family_gate(world, [WORK_FAMILY])
    p = world.record(world.proposal(world.yours("m1"), verdicts=[world.verdict(WORK_FAMILY)]))  # independent=True, said by the family that did the work
    result = gate.apply(p)
    assert result.status == "rejected" and "did the work or said the claim" in result.rejections[0].reason


def test_a_high_change_needs_the_full_effort_check_even_when_it_is_not_independent(world):
    gate = sole_family_gate(world, [WORK_FAMILY])
    world.raw_item("m1")
    retire = lambda: [world.op("item.status_changed", dict(item_id="m1", from_status="active", to_status="retracted", reason="x"))]  # noqa: E731
    assert gate.apply(world.record(world.proposal(retire(), verdicts=[not_independent(world, full=False)]))).status == "rejected"
    result = gate.apply(world.record(world.proposal(retire(), verdicts=[not_independent(world)])))
    assert result.status == "applied" and result.labels == [NOT_INDEPENDENT]


def test_a_fully_independent_check_leaves_no_label_beside_a_labelled_one(world):
    gate = sole_family_gate(world, [WORK_FAMILY, CHECKER])
    result = gate.apply(world.record(world.proposal(world.yours("m1"), verdicts=[not_independent(world, CHECKER), world.verdict(CHECKER)])))
    assert result.status == "applied" and result.labels == []
    assert world.submit(world.proposal(world.yours("m2"))).labels == []  # an ordinary independent check


def test_the_event_of_a_check_with_no_independent_family_carries_the_label(world):
    """The adopted claim was said by the same family that checks it, and no other is left: the item's check is
    recorded as not independent, on the event, and the verdict says so in runs.db."""
    gate = sole_family_gate(world, [WORK_FAMILY])
    world.applied(world.adopted("m1"), verdicts=[world.verdict(THIRD)])
    check = world.op("item.checked", dict(item_id="m1", check_status="checked", checker_family=WORK_FAMILY))
    result = gate.apply(world.record(world.proposal([check], verdicts=[not_independent(world, full=False)])))
    assert result.status == "applied" and result.labels == [NOT_INDEPENDENT]
    stored = json.loads(world.memory.execute("SELECT payload FROM event WHERE type = 'item.checked'").fetchone()[0])
    assert stored["check_status"] == NOT_INDEPENDENT and stored["checker_family"] == WORK_FAMILY
    # a check by an independent family keeps its own status
    check2 = world.op("item.checked", dict(item_id="m1", check_status="checked", checker_family=THIRD))
    assert gate.apply(world.record(world.proposal([check2], verdicts=[world.verdict(THIRD, full=False)]))).labels == []
    assert json.loads(world.memory.execute("SELECT payload FROM event WHERE type = 'item.checked' ORDER BY seq DESC").fetchone()[0])["check_status"] == "checked"


# --- 10. the sweep checks every append-only trigger the schema has -------------------------------------------------------

NOT_APPEND_ONLY = {"topic_two_levels_insert", "topic_two_levels_update", "placement_also_in_limit"}  # limits, not append-only


def schema_triggers(store):
    return set(re.findall(r"CREATE TRIGGER (\w+)", (SCHEMA / f"{store}.sql").read_text(encoding="utf-8")))


def test_required_triggers_name_every_append_only_and_history_trigger_of_the_schema():
    for store in ("memory", "history", "runs"):
        assert set(inv.REQUIRED_TRIGGERS[store]) == schema_triggers(store) - NOT_APPEND_ONLY, store
        assert len(inv.REQUIRED_TRIGGERS[store]) == len(set(inv.REQUIRED_TRIGGERS[store]))
    for store in ("index", "overview", "working"):  # the stores that have none, still have none
        assert not schema_triggers(store), f"{store} gained a trigger: name it in REQUIRED_TRIGGERS"


def test_every_history_table_of_the_schema_has_both_its_triggers_required():
    text = (SCHEMA / "memory.sql").read_text(encoding="utf-8")
    for table in re.findall(r"CREATE TABLE (\w+_history) ", text):
        assert {f"{table}_no_update", f"{table}_no_delete"} <= set(inv.REQUIRED_TRIGGERS["memory"]), table


@pytest.mark.parametrize("store, trigger", [(s, t) for s, names in inv.REQUIRED_TRIGGERS.items() for t in names])
def test_the_sweep_reports_each_required_trigger_that_is_missing(world, store, trigger):
    conn = {"memory": world.memory, "history": world.conns["history"], "runs": world.conns["runs"]}[store]
    conn.execute(f"DROP TRIGGER {trigger}")
    stores = {"memory": world.memory, "history": world.conns["history"], "runs": world.conns["runs"]}
    assert [(v.invariant, v.ref) for v in inv.sweep(stores)] == [("I6", f"{store}:{trigger}")]


# --- the sweep finds what the new gate checks refuse ---------------------------------------------------------------------


def test_the_sweep_finds_words_that_are_not_yours_and_a_learned_in_that_is_not_where_it_was_said(world):
    world.applied(world.yours("m1", your_words="keep one SQLite file per meter"))
    stores = {"memory": world.memory, "history": world.conns["history"]}
    assert inv.sweep(stores) == []
    world.memory.execute("UPDATE item SET your_words = 'something I never typed' WHERE id = 'm1'")
    assert {(v.invariant, v.ref) for v in inv.sweep(stores)} == {("I2", "item:m1")}
    world.memory.execute("UPDATE item SET your_words = 'keep one SQLite file per meter', learned_in = 'S2' WHERE id = 'm1'")
    assert {(v.invariant, v.ref) for v in inv.sweep(stores)} == {("I3", "item:m1")}


def test_the_sweep_finds_one_of_your_marks_recorded_under_another_actor(world):
    stores = {"memory": world.memory, "history": world.conns["history"]}
    payload = dict(correction_id="co9", kind="pin", target="m1", via="click", at=SAID, constraint={}, params={})
    with db.transaction(world.memory):
        world.memory.execute(
            "INSERT INTO event (id, type, schema_version, subjects, payload, actor, config_version, recorded_at, inputs)"
            " VALUES ('01ARZ3NDEKTSV4RRFFQ69G5FAV', 'correction.applied', 1, '[\"co9\"]', ?, 'code:overview', 'c', ?, '[]')", (json.dumps(payload), NOW),
        )
    assert [(v.invariant, v.ref) for v in inv.sweep(stores)] == [("I5", "event:01ARZ3NDEKTSV4RRFFQ69G5FAV")]


# --- the evidence context is stamped from the message's source, never named by a proposal -------------------------------


def test_the_gate_stamps_the_evidence_context_and_a_proposal_cannot_name_one(varied):
    w = varied
    ops = w.item_ops("m1", "Data lives in local files first", [("S3:0", "I keep data in local files first", "primary")], scope="personal")
    ops[0].payload["context"] = "de-course"  # a draft that names its own context
    reject(w, ops, "I3")
    ops[0].payload["context"] = None
    w.applied(ops)
    w.applied([w.evidence("ev-p", "m1", "P1:0", "I also keep data in local files first", "support")])
    stamped = {json.loads(r[0]).get("evidence_id"): json.loads(r[0]).get("context") for r in w.memory.execute("SELECT payload FROM event WHERE type = 'evidence.anchored'")}
    assert stamped == {"ev-m1-0": "personal", "ev-p": "de-course"}  # a chat outside any project is 'personal'
    if type(w.gate.projector).__name__ == "Projector":
        assert {r[0] for r in w.memory.execute("SELECT context FROM evidence")} == {"personal", "de-course"}
        w.memory.execute("DROP TRIGGER evidence_frozen")
        w.memory.execute("UPDATE evidence SET context = 'elsewhere' WHERE id = 'ev-p'")
        ctx = inv.Context(Proposal.build(w.run_id, [value_op(w=w)]), [value_op(w=w)], inv.MemoryRead(w.memory), inv.HistoryRead(w.history), NOW)
        assert {e.context for e in inv._item_evidence(ctx, "m1").values()} == {"personal", "elsewhere"}  # the stored row is read first
