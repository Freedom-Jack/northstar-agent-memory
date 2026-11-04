"""The attacks an independent check built against the write gate, rerun against the whole core as it is wired together:
the real projector, the SQLite run store, history and memory stores, and the config the shipped code reads
(MEMORY-ARCHITECTURE principle 4, §5.9, §5.12; GOAL §4.7). A proposal makes claims about itself (a verdict, your words, who
acted, when it was said, which family did the work), and the gate must find each out for itself.

Each test names the attack and shows it is refused now, with nothing written. Where a refusal could be a side effect of an
unrelated rule, the same proposal is then shown to apply once the claim is made true, so the refusal is for the lie. Every
fixture is invented; see gate_fixtures.py. Where the unit tests in test_gate_attacks.py use a fake projector for speed, these
use the real one, so what the gate accepts the projector has to be able to apply."""

from __future__ import annotations

import json

import pytest

from northstar_agent_memory import config as northstar_config
from northstar_agent_memory.core import UserAuthority, db, events, invariants as inv, ports
from northstar_agent_memory.core.gate import FULL_RULES, LOSS_BOUND_RULE, NOT_INDEPENDENT, GateResult, WriteGate
from northstar_agent_memory.core.ports import Proposal, Verdict, WorkEvent
from northstar_agent_memory.core.projector import Projector

from .gate_fixtures import CHECKER, NOW, PROMPT_HASH, SAID, SCOPE, TIME, WORK_FAMILY, YOU, make_world

THIRD = "third-family"


@pytest.fixture
def w(store_root):
    world = make_world(store_root, projector=Projector())
    yield world
    world.close()


def found(result) -> set[str]:
    return {r.invariant for r in result.rejections}


def refused(world, result, *invariants, before=None):
    """The result is a refusal naming each invariant, and nothing was appended."""
    assert result.status in ("rejected", "held"), result
    assert set(invariants) <= found(result), result.rejections
    if before is not None:
        assert world.count("event") == before
    return result


def forged(world, ops, verdicts, **kw):
    """What a proposal can do on its own: carry verdicts. Nothing is recorded in runs.db for them."""
    return world.gate.apply(world.proposal(ops, verdicts=verdicts, **kw))


def status_of(world, item_id):
    return world.memory.execute("SELECT status FROM item WHERE id = ?", (item_id,)).fetchone()[0]


# --- 1. a forged verdict with no recorded call: a medium change, a high change and a merge ---------------------------------


def test_attack_forged_verdict_on_a_medium_change(w):
    """A new item is a medium change. The proposal carries 'openai passed it'; no model call of openai is recorded."""
    before = w.count("event")
    result = forged(w, w.yours("m1"), [Verdict(CHECKER, ["meaning_both_ways"], "pass", True)])
    refused(w, result, "verification", before=before)
    assert w.count("item") == 0
    assert w.apply(w.yours("m1")).status == "applied"  # with the verdict the checker recorded, the same change applies


def test_attack_forged_verdict_on_a_high_change(w):
    w.applied(w.yours("m1"))
    retire = lambda: [w.op("item.status_changed", dict(item_id="m1", from_status="active", to_status="retracted", reason="x"))]  # noqa: E731
    refused(w, forged(w, retire(), [Verdict(CHECKER, list(FULL_RULES), "pass", True)]), "verification")
    assert status_of(w, "m1") == "active"
    assert w.apply(retire()).status == "applied" and status_of(w, "m1") == "retracted"


def test_attack_forged_verdict_on_a_merge(w):
    """A same_as merge with no exact key claims two agreeing families: its own checked_by, and a verdict nobody recorded."""
    w.raw_item("a", "Readings go to SQLite")
    w.raw_item("b", "Meter data is stored in SQLite")
    merge = lambda: [w.op("link.applied", dict(link_id=w.next("l"), from_id="b", to_id="a", link_type="same_as", reason="same idea", stated_by="northstar", checked_by=[WORK_FAMILY, CHECKER]))]  # noqa: E731
    refused(w, forged(w, merge(), [Verdict(CHECKER, list(FULL_RULES), "pass", True)]), "I12")
    assert status_of(w, "b") == "active"
    assert w.apply(merge()).status == "applied" and status_of(w, "b") == "superseded"


def test_attack_a_verdict_that_copies_a_real_calls_id_is_still_forged(w):
    """The proposal carries a verdict naming a call that is recorded (a real call of the right family); the proposal itself is not."""
    call = w.call_for(CHECKER, w.run_id)
    refused(w, forged(w, w.yours("m1"), [Verdict(CHECKER, list(FULL_RULES), "pass", True, call)]), "verification")


def test_attack_a_verdict_written_straight_into_runs_db_with_a_call_of_another_family(w):
    """A damaged or tampered runs.db: the verdict says openai, the call it names is claude's own."""
    p = w.proposal(w.yours("m1"), verdicts=[])
    w.plant(p, Verdict(CHECKER, list(FULL_RULES), "pass", True, w.runs.recorded_call(PROMPT_HASH, w.run_id)["id"]))
    result = refused(w, w.gate.apply(p), "verification")
    assert "did the work" in result.rejections[0].reason or "not a openai call" in result.rejections[0].reason


def test_attack_a_run_stores_verdict_for_a_proposal_cannot_be_moved_to_other_ops(w):
    good = w.proposal(w.yours("m1"), verdicts=[w.verdict()])
    w.record(good)
    evil = w.proposal(w.yours("m2", line="Something nobody checked"), verdicts=good.verdicts)
    evil.proposal_id = good.proposal_id
    for op in evil.ops:
        op.proposal_id = good.proposal_id
    result = refused(w, w.gate.apply(evil), "verification")
    assert "judged other ops" in result.rejections[0].reason
    assert w.count("item") == 0


# --- 2. your_words that appear in no cited user text -------------------------------------------------------------------


def test_attack_your_words_that_nothing_you_typed_contains(w):
    result = refused(w, w.apply(w.yours("m1", your_words="never keep readings longer than a day")), "I2", before=0)
    assert "appear nowhere" in result.rejections[0].reason
    assert w.apply(w.yours("m1", your_words="keep one SQLite file per meter")).status == "applied"


@pytest.mark.parametrize("message, quote", [("S1:1", "keeping 1-minute readings for 7 days"), ("S1:5", "the Pi Zero keeps up"), ("S2:0", "the dryer alert should fire"), ("S1:4", "12 passed")])
def test_attack_your_words_taken_from_an_ai_a_paste_a_report_or_a_tool(w, message, quote):
    parts = [("S1:0", "keep one SQLite file per meter", "primary"), (message, quote, "support")]
    refused(w, w.apply(w.item_ops("m1", "Readings go to SQLite", parts, your_words=quote)), "I2")


def test_attack_a_quoted_span_in_a_why_that_you_never_said(w):
    refused(w, w.apply(w.yours("m1", why='You said "never throw readings away"')), "I2")


# --- 3. a check of an adopted claim by the family that said it -------------------------------------------------------------


def adopted_by_the_other_family(world):
    """An AI of the openai family said it; you adopted it; claude's session recorded it, so a stored claim now stands."""
    parts = [("S2:1", "a rolling baseline for the alerts", "primary"), ("S2:2", "A rolling baseline is a good idea", "adoption")]
    world.applied(world.item_ops("m1", "Alerts use a rolling baseline", parts), verdicts=[world.verdict(THIRD)])


def test_attack_the_family_that_said_an_adopted_claim_checks_it(w):
    adopted_by_the_other_family(w)
    check = lambda family: [w.op("item.checked", dict(item_id="m1", check_status="checked", checker_family=family))]  # noqa: E731
    result = refused(w, w.apply(check(CHECKER), verdicts=[w.verdict(CHECKER, full=False)]), "verification")
    assert "said the claim" in result.rejections[0].reason
    assert w.apply(check(THIRD), verdicts=[w.verdict(THIRD, full=False)]).status == "applied"


def test_attack_the_same_family_retracts_the_claim_it_said(w):
    """Not only a check: a retraction of the stored claim, judged by the family that said it."""
    adopted_by_the_other_family(w)
    retire = [w.op("item.status_changed", dict(item_id="m1", from_status="active", to_status="retracted", reason="x"))]
    refused(w, w.apply(retire, verdicts=[w.verdict(CHECKER)]), "verification")
    assert status_of(w, "m1") == "active"


def test_attack_a_check_status_with_no_check_behind_it(w):
    """A proposal writes 'not_independent' on an adopted claim: a check result nobody made, at the lowest tier."""
    adopted_by_the_other_family(w)
    claim = [w.op("item.checked", dict(item_id="m1", check_status=NOT_INDEPENDENT, checker_family=CHECKER))]
    refused(w, w.apply(claim, verdicts=[]), "verification")
    assert w.memory.execute("SELECT check_status FROM item WHERE id = 'm1'").fetchone()[0] == "unchecked"


def test_attack_the_work_family_is_named_wrongly_in_the_actor(w):
    """The ops' actor names the hash of a call that is recorded as openai's, to hide that claude did the work, and
    claude then 'checks' it. The stage saved the proposal with its job, and the job's calls (claude's) say who did it."""
    job = w.runs.enqueue(w.run_id, "extract", "job-1")
    w.runs.record_call(ports.ModelCall("test-provider", "test-model", WORK_FAMILY, "real-work-hash", ["S1:0"], run_id=w.run_id, job_id=job, raw_output="{}"))
    w.runs.record_call(ports.ModelCall("test-provider", "test-model", CHECKER, "decoy-hash", ["S1:0"], run_id=w.run_id, raw_output="{}"))
    p = w.proposal(w.yours("m1"), verdicts=[w.verdict(WORK_FAMILY)])
    for op in p.ops:
        op.actor = "model:extract@1#decoy-hash"
    for v in p.verdicts:
        v.model_call_id = w.call_for(WORK_FAMILY, w.run_id)
    w.runs.save_proposal(p, job_id=job)
    result = refused(w, w.gate.apply(p), "verification")
    assert "did the work" in result.rejections[0].reason
    assert w.count("item") == 0
    # the same proposal, saved with no job, is judged on the actor's word alone: that is the gap a job closes
    q = w.proposal(w.yours("m2"), verdicts=[w.verdict(WORK_FAMILY)])
    for op in q.ops:
        op.actor = "model:extract@1#decoy-hash"
    for v in q.verdicts:
        v.model_call_id = w.call_for(WORK_FAMILY, w.run_id)
    w.runs.save_proposal(q)
    assert w.gate.apply(q).status == "applied"


# --- 4. a purge and a retraction under actor 'user' ------------------------------------------------------------------------


def purge(world, item="m1", pid=None):
    return world.op("purge.applied", dict(purge_id=pid or world.next("pg"), item_ids=[item], requested_at=SAID), actor="user")


def retract(world, item="m1", actor="user"):
    return world.op("item.status_changed", dict(item_id=item, from_status="active", to_status="retracted", reason="you said it is wrong"), actor=actor)


def click(world, kind, target, cid, actor="user"):
    return world.op("correction.applied", dict(correction_id=cid, kind=kind, target=target, via="click", at=SAID, constraint={}), actor=actor)


@pytest.mark.parametrize("claim", ["user", "code:ui", "code:capture"])
def test_attack_a_purge_under_the_actor_user_through_apply(w, claim):
    """The op says it is yours (or that a code module acts on your click). apply() is for automation and takes no one's word."""
    w.raw_item("m1")
    ops = [click(w, "purge", "m1", "co1", actor=claim), w.op("purge.applied", dict(purge_id="pg1", item_ids=["m1"], requested_at=SAID), actor=claim)]
    refused(w, w.apply(ops, verdicts=[w.verdict(CHECKER)]), "I5", before=0)
    assert w.count("item") == 1 and w.count("correction") == 0


def test_attack_a_retraction_under_the_actor_user_through_apply(w):
    w.applied(w.yours("m1"))
    before = w.count("event")
    refused(w, w.apply([retract(w)], verdicts=[]), "I5", before=before)
    refused(w, w.apply([retract(w)], verdicts=[w.verdict(CHECKER)]), "I5", before=before)  # a verdict does not make it yours
    assert status_of(w, "m1") == "active"


def test_attack_a_purge_through_apply_user_with_no_request(w):
    """Your authority is handed over, but nothing of yours asks for this purge: no typed words, no recorded click."""
    w.raw_item("m1")
    result = refused(w, w.apply_user([purge(w)]), "I5", before=0)
    assert "typed words or a recorded click" in result.rejections[0].reason
    assert w.count("item") == 1
    assert w.apply_user([click(w, "purge", "m1", "co1"), purge(w)]).status == "applied"


def test_attack_a_purge_through_apply_user_on_words_you_did_not_type(w):
    w.raw_item("m1")
    ev = w.evidence("ev-p", "co1", "S2:0", "the dryer alert should fire", "support", "correction", actor="user")  # a model's report of your turn
    typed = w.op("correction.applied", dict(correction_id="co1", kind="purge", target="m1", via="typed", at=SAID, constraint={}, evidence_id="ev-p"), actor="user")
    refused(w, w.apply_user([ev, typed, purge(w)]), "I5", before=0)


def test_attack_a_model_op_under_your_authority(w):
    """The authority is yours; the op is a model's. apply_user carries only ops under the actor user."""
    w.raw_item("m1")
    refused(w, w.apply_user([w.op("item.status_changed", dict(item_id="m1", from_status="active", to_status="retracted", reason="x"), actor=w.actor)]), "I5")
    assert status_of(w, "m1") == "active"


def test_attack_your_authority_made_without_a_user_action_or_by_a_stage(w):
    with pytest.raises(ValueError):
        UserAuthority(surface="ui", user_action=False)
    with pytest.raises(ValueError):
        UserAuthority(surface="stage", user_action=True)  # type: ignore[arg-type]
    p = w.record(w.proposal([retract(w)], verdicts=[]))
    w.raw_item("m1")
    result = w.gate.apply_user(p, object())  # type: ignore[arg-type]
    assert result.status == "rejected" and result.rejections[0].invariant == "authority"
    assert status_of(w, "m1") == "active"


def test_a_retraction_of_yours_through_apply_user_is_a_click_and_needs_no_verdict(w):
    """Not an attack: the control case. A retraction is yours to make, and nothing but your authority is asked of it."""
    w.applied(w.yours("m1"))
    assert w.apply_user([retract(w)]).status == "applied" and status_of(w, "m1") == "retracted"


# --- 5. a re-proposed rejected link and an automated retraction of a confirmed one --------------------------------------------


def two_items(world):
    world.raw_item("a", "Readings go to SQLite")
    world.raw_item("b", "Meter data is stored in SQLite")


def link(world, link_id, link_type="supports", from_id="a", to_id="b", op="link.proposed", **kw):
    return world.op(op, dict(link_id=link_id, from_id=from_id, to_id=to_id, link_type=link_type, reason="same topic", stated_by="northstar", **kw))


def test_attack_a_rejected_link_is_proposed_again(w):
    two_items(w)
    w.applied([link(w, "l1")])
    assert w.apply_user([w.op("link.rejected", dict(link_id="l1", via="click"), actor="user")]).status == "applied"
    result = refused(w, w.apply([link(w, "l2")]), "I21", before=w.count("event"))
    assert "you rejected this link (l1)" in result.rejections[0].reason
    refused(w, w.apply([link(w, "l3", op="link.applied")]), "I21")  # and not applied outright either
    assert w.count("link") == 1


def test_attack_a_rejected_link_comes_back_the_other_way_round(w):
    two_items(w)
    w.applied([link(w, "l1", "conflicts", checked_by=[WORK_FAMILY, CHECKER])])
    w.applied_user([w.op("link.rejected", dict(link_id="l1", via="click"), actor="user")])
    refused(w, w.apply([link(w, "l2", "conflicts", "b", "a", checked_by=[WORK_FAMILY, CHECKER])]), "I21")


def test_attack_an_automated_retraction_of_a_link_you_confirmed(w):
    two_items(w)
    w.applied([link(w, "l1")])
    w.applied_user([w.op("link.confirmed", dict(link_id="l1", via="click"), actor="user")])
    result = refused(w, w.apply([w.op("link.retracted", dict(link_id="l1", reason="an item it joins was retracted"))]), "I21")
    assert "you confirmed this link" in result.rejections[0].reason
    assert w.memory.execute("SELECT status FROM link WHERE id = 'l1'").fetchone()[0] == "confirmed"
    assert w.apply_user([w.op("link.retracted", dict(link_id="l1", reason="you took it back"), actor="user")]).status == "applied"


def test_attack_a_link_that_says_you_stated_it(w):
    """stated_by is a claim: 'you' sets who may undo the link, and 'construction' makes a model's link a low-tier one."""
    two_items(w)
    refused(w, w.apply([w.op("link.proposed", dict(link_id="l1", from_id="a", to_id="b", link_type="supports", reason="x", stated_by="you"))]), "I5")
    w.raw_item("m1")
    add_work(w, "w1", "strong")
    sneaky = w.op("link.applied", dict(link_id="l2", from_id="m1", to_id="w1", to_kind="work", link_type="used_in", reason="x", stated_by="construction"))
    refused(w, w.apply([sneaky], verdicts=[]), "I5")  # a model's op, under no verdict


# --- 6. a value promotion with an unverified signal ----------------------------------------------------------------------------


def value(world, item="m1", signal="your_keep", ids=(), actor=None):
    return world.op("item.value_changed", dict(item_id=item, from_value="forming", to_value="kept", signal=signal, evidence_ids=list(ids)), actor=actor)


def add_work(world, work_id, evidence):
    with db.transaction(world.memory):
        world.memory.execute("INSERT INTO work (id, kind, ref, evidence, created_seq, seq_from) VALUES (?, 'commit', 'a41c9e0', ?, 0, 0)", (work_id, evidence))


@pytest.mark.parametrize("signal", ["later_day", "second_context", "your_keep", "built_on", "used_in_work"])
def test_attack_a_value_moves_to_kept_on_a_signal_nothing_shows(w, signal):
    w.applied(w.yours("m1"))
    result = refused(w, w.apply([value(w, signal=signal)]), "I1", before=w.count("event"))
    assert "does not move" in result.rejections[0].reason
    assert w.memory.execute("SELECT value FROM item WHERE id = 'm1'").fetchone()[0] == "forming"


def test_attack_a_value_moves_on_an_ais_words_a_day_later(w):
    w.applied(w.adopted("m1"))
    ai_later = w.evidence("ev-a", "m1", "S2:1", "a rolling baseline for the alerts", "support")
    refused(w, w.apply([ai_later, value(w, signal="later_day")]), "I1")


def test_attack_a_value_moves_on_evidence_of_another_item(w):
    w.applied(w.yours("m1"))
    w.applied(w.yours("m2", line="Hourly averages are enough for monthly charts"))
    refused(w, w.apply([value(w, "m1", "later_day", ["ev-m2-0"])]), "I1")


def test_attack_a_model_makes_up_the_work_that_moves_a_value(w):
    """work.registered says 'strong' with an invented work event; a used_in link follows; the value moves. All low tier."""
    w.applied(w.yours("m1"))
    made_up = w.op("work.registered", dict(work_id="w9", kind="commit", ref="deadbeef", evidence="strong", work_event_id="no-such-event"))
    used = w.op("link.applied", dict(link_id="l9", from_id="m1", to_id="w9", to_kind="work", link_type="used_in", reason="built it", stated_by="construction"), actor="code:construction")
    refused(w, w.apply([made_up, used, value(w, signal="used_in_work")], verdicts=[]), "I3", before=w.count("event"))
    assert w.count("work") == 0 and w.memory.execute("SELECT value FROM item WHERE id = 'm1'").fetchone()[0] == "forming"


def test_attack_a_model_inflates_a_real_weak_work_event_to_strong(w):
    w.history.append_work_event(WorkEvent(id="we1", source_id="S1", kind="commit", ref="a41c9e0", evidence="weak"))
    inflated = lambda level: w.op("work.registered", dict(work_id="w1", kind="commit", ref="a41c9e0", evidence=level, work_event_id="we1"))  # noqa: E731
    result = refused(w, w.apply([inflated("strong")], verdicts=[]), "I3")
    assert "captured work event says 'weak'" in result.rejections[0].reason
    assert w.apply([inflated("weak")], verdicts=[]).status == "applied"


# --- 7. said_at 1999 and learned_in 'NO-SUCH-SOURCE' ------------------------------------------------------------------------


def test_attack_said_at_in_1999(w):
    result = refused(w, w.apply(w.yours("m1", said_at="1999-01-01T00:00:00Z")), "I16", before=0)
    assert "not when the message of yours" in result.rejections[0].reason
    assert w.apply(w.yours("m1", said_at=TIME["S1:0"])).status == "applied"


def test_attack_learned_in_a_source_that_does_not_exist(w):
    result = refused(w, w.apply(w.yours("m1", learned_in="NO-SUCH-SOURCE")), "I3", before=0)
    assert "not the source or context" in result.rejections[0].reason
    assert w.apply(w.yours("m1", learned_in="S1")).status == "applied"


def test_attack_a_later_statement_that_is_not_later(w):
    """A supersession 'by your later statement' where the new item rests on the earlier message."""
    quote = {"S1:0": "keep one SQLite file per meter", "S1:6": "Keep the weekly report short"}
    w.applied(w.item_ops("old", "Reports are short", [("S1:6", quote["S1:6"], "primary")]))
    w.applied(w.item_ops("new", "Readings are stored in SQLite", [("S1:0", quote["S1:0"], "primary")]))
    w.memory.execute("UPDATE item SET said_at = '2030-01-01T00:00:00Z' WHERE id = 'new'")  # the field a proposer would supply
    supersede = w.op("supersession.applied", dict(supersession_id="s1", old_item="old", old_version=1, new_item="new", reason="your_later_statement"))
    refused(w, w.apply([supersede]), "I16")
    assert status_of(w, "old") == "active"


# --- 8. a rollback that retires more than the loss bound ---------------------------------------------------------------------


def batch(world, event_ids, actor=None, **kw):
    return world.op("compensation.batch", dict(batch_id=world.next("b"), reason="the audit disagreed", compensated_event_ids=list(event_ids), **kw), actor=actor)


@pytest.fixture
def six_made(w):
    """100 older items, and six that an earlier run created; a later run then rolls them back."""
    w.pad(100, "i")
    created = []
    for n in range(6):
        ops = w.yours(f"n{n}", line=f"Meter {n} logs to its own SQLite file")
        w.applied(ops)
        created.append(next(op.id for op in ops if op.type == "item.created"))
    later = w.runs.start_run("manual")
    w.runs.finish_run(w.run_id, "applied")
    return w, created, later


def live(world):
    return world.count("item", "id LIKE 'n%' AND status = 'active'")


def test_attack_a_rollback_removes_more_items_than_the_loss_bound(six_made):
    w, created, later = six_made
    result = refused(w, w.apply([batch(w, created)], run_id=later), "I13")
    assert result.status == "held" and "6 items" in result.rejections[0].reason
    assert w.count("item", "id LIKE 'n%'") == 6  # none of them was taken away
    assert w.apply([batch(w, created[:5])], run_id=later).status == "applied"  # five of 106 is the bound
    assert w.count("item", "id LIKE 'n%'") == 1


def test_attack_a_rollback_in_pieces_across_one_run(six_made):
    w, created, later = six_made
    assert w.apply([batch(w, created[:3])], run_id=later).status == "applied"
    refused(w, w.apply([batch(w, created[3:])], run_id=later), "I13")


def test_attack_a_rollback_of_a_whole_run_names_one_event(six_made):
    w, created, later = six_made
    refused(w, w.apply([batch(w, created[:1], run_id_undone=w.run_id)], run_id=later), "I13")


def test_a_second_check_releases_the_held_rollback_and_your_own_is_not_counted(six_made):
    w, created, later = six_made
    release = w.verdict(rules=[*FULL_RULES, LOSS_BOUND_RULE])
    assert w.apply([batch(w, created)], run_id=later, verdicts=[release]).status == "applied"


def test_your_own_rollback_is_not_counted_against_the_bound(six_made):
    w, created, later = six_made
    assert w.apply_user([batch(w, created, actor="user")], run_id=later).status == "applied"
    assert w.count("item", "id LIKE 'n%'") == 0


# --- the reason a replacement or a conflict resolution gives is found, not read ----------------------------------------------------


def two_views(world):
    world.applied(world.yours("a", line="Readings are stored in SQLite"))
    world.applied(world.item_ops("b", "Reports are short", [("S1:6", "Keep the weekly report short", "primary")]))


def supersede(world, reason, sid="s1"):
    return world.op("supersession.applied", dict(supersession_id=sid, old_item="a", old_version=1, new_item="b", reason=reason))


def test_attack_a_supersession_that_says_you_corrected_it(w):
    """High tier, checked by the other family, but 'your_correction' is the proposal's own word: no correction of yours exists."""
    two_views(w)
    result = refused(w, w.apply([supersede(w, "your_correction")]), "I5", before=w.count("event"))
    assert "none is on file" in result.rejections[0].reason
    assert status_of(w, "a") == "active"
    w.applied_user([w.op("correction.applied", dict(correction_id="co1", kind="not_what_i_think", target="a", via="click", at=SAID, constraint={}), actor="user")])
    assert w.apply([supersede(w, "your_correction")]).status == "applied" and status_of(w, "a") == "superseded"


def test_attack_a_supersession_that_says_a_check_contradicted_the_claim(w):
    two_views(w)
    refused(w, w.apply([supersede(w, "check_contradicted")]), "I1")
    assert status_of(w, "a") == "active"


def test_attack_a_conflict_settled_in_your_name(w):
    """Step 0 of §2.6 is your correction; the proposal says it settled the conflict that way and has none."""
    w.applied(w.yours("c", line="Keep raw readings forever"))
    w.applied(w.item_ops("d", "Delete raw readings after seven days", [("S1:6", "Keep the weekly report short", "primary")]))
    w.applied([w.op("conflict.opened", dict(conflict_id="c1", side_a_item="c", side_a_version=1, side_b_item="d", side_b_version=1, kind="same_context", state="open"))])
    resolve = lambda step, winner: [w.op("conflict.resolved", dict(conflict_id="c1", step=step, state="resolved", rule_version="r1", winner=winner))]  # noqa: E731
    refused(w, w.apply(resolve(0, "c")), "I5")
    refused(w, w.apply(resolve(2, "c")), "I16")  # c was said first: not the later statement
    refused(w, w.apply(resolve(0, "zzz")), "I1")  # not a side at all
    assert w.apply(resolve(2, "d")).status == "applied"  # d was said later, by the time of the messages
    assert w.memory.execute("SELECT state FROM conflict WHERE id = 'c1'").fetchone()[0] == "resolved"


def test_attack_a_scope_widened_on_evidence_the_item_does_not_rest_on(w):
    """Widening a project item to personal on a message from another project, anchored to some other item."""
    w.applied(w.yours("m1"))
    w.applied(w.item_ops("m2", "Data lives in local files first", [("P1:0", "I also keep data in local files first", "primary")], scope="project:de-course"))
    widen = w.op("item.scope_widened", dict(item_id="m1", base_version=1, from_scope=SCOPE, to_scope="personal", evidence_ids=["ev-m2-0"]))
    result = refused(w, w.apply([widen]), "I17")
    assert "rests on" in result.rejections[0].reason
    own = w.evidence("ev-w", "m1", "P1:0", "I also keep data in local files first", "scope")
    assert w.apply([own, w.op("item.scope_widened", dict(item_id="m1", base_version=1, from_scope=SCOPE, to_scope="personal", evidence_ids=["ev-w"]))]).status == "applied"


# --- 9. a single-family user: a medium change applies, labelled not independent -------------------------------------------------


def single_family(world, families):
    """The gate as the shipped code builds it: the families a check may be routed to come from [maintenance] in the config."""
    config = {"maintenance": {"check_families": list(families)}}
    return WriteGate(world.memory, world.history, Projector(), runs=world.runs, config=config, clock=lambda: NOW)


def labelled(world, family=WORK_FAMILY, *, full=False):
    return world.verdict(family, full=full, independent=False)


def test_a_medium_change_for_a_single_family_user_applies_labelled_not_independent(w):
    gate = single_family(w, [WORK_FAMILY])
    p = w.record(w.proposal(w.yours("m1"), verdicts=[labelled(w)]))
    result = gate.apply(p)
    assert result.status == "applied" and isinstance(result, GateResult) and result.labels == [NOT_INDEPENDENT]
    assert [(v["checker_family"], v["independent"]) for v in w.runs.verdicts(p.proposal_id)] == [(WORK_FAMILY, 0)]
    assert w.count("item") == 1


def test_a_high_change_for_a_single_family_user_applies_on_a_full_check_labelled(w):
    gate = single_family(w, [WORK_FAMILY])
    w.raw_item("m1")
    retire = lambda: [w.op("item.status_changed", dict(item_id="m1", from_status="active", to_status="retracted", reason="x"))]  # noqa: E731
    refused(w, gate.apply(w.record(w.proposal(retire(), verdicts=[labelled(w, full=False)]))), "verification")
    result = gate.apply(w.record(w.proposal(retire(), verdicts=[labelled(w, full=True)])))
    assert result.status == "applied" and result.labels == [NOT_INDEPENDENT]


def test_the_not_independent_label_is_refused_while_another_family_is_on_the_list(w):
    """The same proposal, but the config lists two families: a check by the work's own family is not allowed to stand in."""
    gate = single_family(w, [WORK_FAMILY, CHECKER])
    p = w.record(w.proposal(w.yours("m1"), verdicts=[labelled(w)]))
    result = refused(w, gate.apply(p), "verification", before=0)
    assert "another family is left" in result.rejections[0].reason


def test_the_not_independent_label_cannot_stand_in_without_a_recorded_call(w):
    gate = single_family(w, [WORK_FAMILY])
    p = w.proposal(w.yours("m1"), verdicts=[])
    w.plant(p, labelled(w, full=False).__class__(WORK_FAMILY, ["meaning_both_ways"], "pass", False, None))
    refused(w, gate.apply(p), "verification")


def test_the_shipped_config_lists_the_families_a_check_may_use(w):
    """A gate built from the shipped config knows the families left, in the vocabulary the model layer and capture use;
    your settings.toml may narrow the list to the one family you have."""
    from northstar_agent_memory.models.port import FAMILIES

    shipped = northstar_config.defaults()
    assert set(shipped["maintenance"]["check_families"]) == set(FAMILIES)
    gate = WriteGate(w.memory, w.history, Projector(), runs=w.runs, config=shipped, clock=lambda: NOW)
    assert gate.families == frozenset(FAMILIES)
    narrowed = northstar_config._merge(shipped, {"maintenance": {"check_families": ["anthropic"]}})
    assert WriteGate(w.memory, w.history, Projector(), runs=w.runs, config=narrowed, clock=lambda: NOW).families == frozenset({"anthropic"})
    with pytest.raises(ValueError):
        WriteGate(w.memory, w.history, Projector(), runs=w.runs, config={"maintenance": {"check_families": "anthropic"}}, clock=lambda: NOW)


# --- the seams between the three tracks ------------------------------------------------------------------------------------------


def test_the_gate_stamps_the_evidence_context_and_a_proposal_cannot_name_one(w):
    ops = w.yours("m1")
    ops[0].payload["context"] = "de-course"
    result = refused(w, w.apply(ops), "I3")
    assert "context comes from capture" in result.rejections[0].reason
    w.applied(w.yours("m1"))
    stored = w.memory.execute("SELECT context FROM evidence WHERE id = 'ev-m1-0'").fetchone()[0]
    assert stored == events.evidence_context("energy-dash")
    assert json.loads(w.memory.execute("SELECT contexts_seen FROM item WHERE id = 'm1'").fetchone()[0]) == ["S1", "energy-dash"]


def test_the_history_adapter_gives_the_gate_a_sources_kind_and_scope(w):
    assert isinstance(w.history, ports.SourceInfoReader)
    info = w.history.get_source_info("S3")
    assert (info["kind"], info["scope"]) == ("chat", "personal") and w.history.get_source_info("none") is None


def test_every_required_trigger_is_installed_in_the_stores_the_gate_reads(w):
    stores = {"memory": w.memory, "history": w.conns["history"], "runs": w.conns["runs"]}
    assert [v for v in inv.sweep(stores) if "trigger" in v.reason.lower()] == []


def test_a_gate_with_a_run_store_never_reads_the_proposals_own_verdicts(w):
    """Even a verdict the proposal carries and the run store has never seen (and which would be a pass) is not read."""
    p = w.proposal(w.yours("m1"), verdicts=[])
    w.record(p)
    p.verdicts = [Verdict(CHECKER, list(FULL_RULES), "pass", True, w.call_for(CHECKER, w.run_id))]
    refused(w, w.gate.apply(p), "verification")
    assert YOU.user_action is True  # (the authority the tests hand to apply_user is the only other way in)
