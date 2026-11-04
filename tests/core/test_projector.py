"""The projector: every event type, row history, merges, compensation and purge (MEMORY-ARCHITECTURE §2.3-§2.8, §3.4, §5.9).

Every fixture is invented. Each test appends events through `Log`, which validates them as the gate will.
"""

from __future__ import annotations

import json
import sqlite3

import pytest

from northstar_agent_memory.core import events
from northstar_agent_memory.core.events import EVENT_TYPES, ITEM_CLASS_OF_KIND, PLAIN_ITEM_KINDS
from northstar_agent_memory.core.ports import Projector as ProjectorPort
from northstar_agent_memory.core.projector import PURGE_STUB, Projector, ProjectionError

from .conftest import EXAMPLE_PAYLOADS
from .projection_helpers import Log, evidence_op, history, row, seed_item, seed_topic


@pytest.fixture
def log(memory):
    return Log(memory)


def items(log, *ids, **kw):
    for item_id in ids:
        seed_item(log, item_id, **kw)


# --- the projector as a whole -------------------------------------------------------------------------------------


def test_the_projector_meets_the_port():
    assert isinstance(Projector(), ProjectorPort)


@pytest.mark.parametrize("type_", EVENT_TYPES)
def test_every_event_type_has_a_handler(type_):
    assert callable(getattr(Projector, "_on_" + type_.replace(".", "_")))


def test_there_are_42_handlers():
    handlers = [name for name in dir(Projector) if name.startswith("_on_")]
    assert len(handlers) == len(EVENT_TYPES) == 42


def test_events_need_their_seq_in_order(memory):
    env = events.make_event("scope.hold_changed", EXAMPLE_PAYLOADS["scope.hold_changed"], actor="code:t", config_version="c")
    env.recorded_at = "2026-03-02T09:30:00.000Z"
    with pytest.raises(ProjectionError, match="seq"):
        Projector().apply(memory, [env])
    env.seq = 5
    second = events.make_event("scope.hold_changed", EXAMPLE_PAYLOADS["scope.hold_changed"], actor="code:t", config_version="c")
    second.seq = 5
    with pytest.raises(ProjectionError, match="seq order"):
        Projector().apply(memory, [env, second])


def test_an_unknown_schema_version_is_refused(memory):
    env = events.make_event("scope.hold_changed", EXAMPLE_PAYLOADS["scope.hold_changed"], actor="code:t", config_version="c")
    env.seq, env.schema_version = 1, 2
    with pytest.raises(ProjectionError, match="I15"):
        Projector().apply(memory, [env])


def test_a_payload_that_does_not_fit_is_refused(memory):
    env = events.make_event("scope.hold_changed", EXAMPLE_PAYLOADS["scope.hold_changed"], actor="code:t", config_version="c")
    env.seq = 1
    env.payload = {"scope_id": "personal"}
    with pytest.raises(ProjectionError, match="schema"):
        Projector().apply(memory, [env])


def test_an_item_needs_its_origin_stamped(log):
    env = log.envelope("item.created", {"origin": "yours"})
    env.payload["origin"] = None
    env.seq = 1
    with pytest.raises(ProjectionError, match="origin"):
        Projector().apply(log.conn, [env])


def test_a_rejected_event_rolls_the_whole_proposal_back(log):
    items(log, "m1")
    before = log.conn.execute("SELECT COUNT(*) FROM event").fetchone()[0]
    with pytest.raises(ProjectionError, match="does not exist"):
        log.run(("item.value_changed", {"item_id": "m1"}), ("item.value_changed", {"item_id": "nope"}))
    assert log.conn.execute("SELECT COUNT(*) FROM event").fetchone()[0] == before
    assert row(log.conn, "item", "m1")["value"] == "forming"
    assert history(log.conn, "item", "m1") == []


def test_tenant_id_goes_on_every_row(memory):
    log = Log(memory, tenant_id="acme")
    seed_item(log, "m1")
    log.add("item.value_changed", {"item_id": "m1"})
    assert {r[0] for r in memory.execute("SELECT tenant_id FROM item")} == {"acme"}
    assert {r[0] for r in memory.execute("SELECT tenant_id FROM item_history")} == {"acme"}
    assert {r[0] for r in memory.execute("SELECT tenant_id FROM evidence")} == {"acme"}


# --- evidence and items -------------------------------------------------------------------------------------------


def test_evidence_is_stored_as_stamped(log):
    ev = log.add("evidence.anchored")
    stored = row(log.conn, "evidence", "ev1")
    assert stored["subject_kind"] == "item" and stored["subject_id"] == "m3" and stored["message_id"] == "A4"
    assert (stored["start_char"], stored["end_char"]) == (5, 79)
    assert stored["speaker"] == "assistant" and stored["agent"] == "claude-code" and stored["model_family"] == "claude"
    assert stored["origin"] == "assistant_output" and stored["lineage"] == "primary" and stored["role"] == "primary"
    assert stored["created_seq"] == stored["seq_from"] == ev.seq


def test_evidence_can_support_a_style_line_or_a_correction(log):
    log.run(evidence_op("e1", "st1", subject_kind="style_line"), evidence_op("e2", "co1", subject_kind="correction"))
    assert row(log.conn, "evidence", "e1")["subject_kind"] == "style_line"
    assert row(log.conn, "evidence", "e2")["subject_kind"] == "correction"


@pytest.mark.parametrize("kind", PLAIN_ITEM_KINDS)
def test_a_new_item_takes_its_class_from_its_kind(log, kind):
    seed_item(log, "m1", kind=kind)
    assert row(log.conn, "item", "m1")["class"] == ITEM_CLASS_OF_KIND[kind]


def test_a_new_item_starts_forming_active_and_at_version_one(log):
    evs = seed_item(log, "m1", valid_from="2026-03-01", valid_to="2026-03-31", time_bound=True, your_words="SQLite", why="small")
    item = row(log.conn, "item", "m1")
    assert (item["version"], item["value"], item["status"]) == (1, "forming", "active")
    assert (item["origin"], item["check_status"]) == ("yours", "not_needed")
    assert json.loads(item["contexts_seen"]) == ["A"] and item["learned_in"] == "A"
    assert item["created_seq"] == item["seq_from"] == evs[1].seq
    assert item["recorded_at"] == evs[1].recorded_at and item["said_at"] == "2026-03-02T09:30:00Z"
    assert (item["valid_from"], item["valid_to"], item["time_bound"]) == ("2026-03-01", "2026-03-31", 1)
    assert (item["your_words"], item["why"]) == ("SQLite", "small")
    assert item["merged_into"] is None and item["goal_status"] is None and item["question_status"] is None
    assert history(log.conn, "item", "m1") == []


def test_an_adopted_claim_starts_unchecked(log):
    seed_item(log, "m3", origin="adopted:claude-code")
    item = row(log.conn, "item", "m3")
    assert item["origin"] == "adopted:claude-code" and item["check_status"] == "unchecked"


def test_a_revision_raises_the_version_and_keeps_the_old_one_in_history(log):
    items(log, "m5", kind="plan", time_bound=True)
    created = log.events[-1].seq
    rev = log.add("item.revised", {"item_id": "m5", "line": "Planned the demo; no later record", "reason": "refresh", "time_bound": None})
    item = row(log.conn, "item", "m5")
    assert item["version"] == 2 and item["line"] == "Planned the demo; no later record"
    assert item["time_bound"] == 1 and item["seq_from"] == rev.seq and item["created_seq"] == created
    (old,) = history(log.conn, "item", "m5")
    assert (old["seq_from"], old["seq_to"], old["version"]) == (created, rev.seq, 1)
    assert old["snapshot"]["line"] == "Line of m5"


def test_a_revision_sets_only_the_fields_it_names(log):
    items(log, "m1", why="because", your_words="mine")
    log.add("item.revised", {"item_id": "m1", "line": "New", "reason": "restated", "applies_when": "on the Pi", "time_bound": True,
                             "valid_from": "2026-04-01", "scope": "project:other", "question_key": "where?"})
    item = row(log.conn, "item", "m1")
    assert (item["why"], item["your_words"]) == ("because", "mine")
    assert (item["applies_when"], item["time_bound"], item["valid_from"], item["scope"], item["question_key"]) == (
        "on the Pi", 1, "2026-04-01", "project:other", "where?")


def test_value_moves_to_kept(log):
    items(log, "m3")
    ev = log.add("item.value_changed", {"item_id": "m3"})
    item = row(log.conn, "item", "m3")
    assert item["value"] == "kept" and item["version"] == 1 and item["seq_from"] == ev.seq
    assert history(log.conn, "item", "m3")[0]["snapshot"]["value"] == "forming"


def test_a_widened_scope_is_personal_and_a_new_version(log):
    items(log, "m7", scope="project:de-course")
    log.add("item.scope_widened", {"item_id": "m7", "from_scope": "project:de-course", "evidence_ids": ["ev-m7"]})
    item = row(log.conn, "item", "m7")
    assert item["scope"] == "personal" and item["version"] == 2
    assert history(log.conn, "item", "m7")[0]["snapshot"]["scope"] == "project:de-course"


@pytest.mark.parametrize("to_status", ["superseded", "retracted", "quarantined"])
def test_status_changes_and_returns_to_active(log, to_status):
    items(log, "m3")
    log.add("item.status_changed", {"item_id": "m3", "from_status": "active", "to_status": to_status})
    assert row(log.conn, "item", "m3")["status"] == to_status
    log.add("item.status_changed", {"item_id": "m3", "from_status": to_status, "to_status": "active"})
    assert row(log.conn, "item", "m3")["status"] == "active"
    assert [h["snapshot"]["status"] for h in history(log.conn, "item", "m3")] == ["active", to_status]


def test_purged_is_not_a_status_change(log):
    items(log, "m3")
    with pytest.raises(ProjectionError, match="purge"):
        log.add("item.status_changed", {"item_id": "m3", "from_status": "active", "to_status": "purged"})


def test_a_check_sets_the_check_state(log):
    items(log, "m4", origin="adopted:claude-code")
    log.add("item.checked", {"item_id": "m4", "check_status": "checked", "checker_family": "openai"})
    assert row(log.conn, "item", "m4")["check_status"] == "checked"
    log.add("item.checked", {"item_id": "m4", "check_status": "contradicted", "checker_family": "openai", "evidence_ids": ["ev-m4"]})
    assert row(log.conn, "item", "m4")["check_status"] == "contradicted"


def test_a_change_that_changes_nothing_adds_no_history(log):
    items(log, "m1")
    log.add("item.checked", {"item_id": "m1", "check_status": "not_needed", "checker_family": None})
    assert history(log.conn, "item", "m1") == []


def test_a_stance_is_stored_once_under_the_events_id(log):
    items(log, "m3")
    ev = log.add("stance.recorded", {"item_id": "m3", "evidence_ids": ["ev-m3"]})
    stance = row(log.conn, "stance", ev.id)
    assert stance["item_id"] == "m3" and stance["stance"] == "adopted" and json.loads(stance["evidence_ids"]) == ["ev-m3"]
    assert stance["created_seq"] == ev.seq


def test_row_history_chains_without_gaps(log):
    items(log, "m1")
    seqs = [log.events[-1].seq]
    for line in ("one", "two", "three"):
        seqs.append(log.add("item.revised", {"item_id": "m1", "line": line, "reason": "restated"}).seq)
    seqs.append(log.add("item.value_changed", {"item_id": "m1"}).seq)
    chain = [(h["seq_from"], h["seq_to"]) for h in history(log.conn, "item", "m1")]
    assert chain == list(zip(seqs, seqs[1:]))
    assert row(log.conn, "item", "m1")["seq_from"] == seqs[-1]


# --- links ---------------------------------------------------------------------------------------------------------


def link_fields(link_id="l1", from_id="m1", to_id="m2", link_type="supports", **extra):
    base = dict(link_id=link_id, from_id=from_id, to_id=to_id, link_type=link_type, reason="m1 backs m2", stated_by="northstar",
                to_kind="item", checked_by=[])  # fmt: skip
    return {**base, **extra}


def test_a_link_goes_from_proposed_to_applied_to_confirmed(log):
    items(log, "m1", "m2")
    p = log.add("link.proposed", link_fields())
    link = row(log.conn, "link", "l1")
    assert (link["status"], link["type"], link["from_id"], link["to_id"], link["to_kind"]) == ("proposed", "supports", "m1", "m2", "item")
    assert link["stated_by"] == "northstar" and link["created_seq"] == link["seq_from"] == p.seq
    log.add("link.applied", link_fields(checked_by=["openai"]))
    link = row(log.conn, "link", "l1")
    assert link["status"] == "applied" and json.loads(link["checked_by"]) == ["openai"] and link["created_seq"] == p.seq
    log.add("link.confirmed", {"link_id": "l1", "via": "click"})
    assert row(log.conn, "link", "l1")["status"] == "confirmed"
    assert [h["snapshot"]["status"] for h in history(log.conn, "link", "l1")] == ["proposed", "applied"]


def test_a_link_can_be_applied_without_being_proposed(log):
    items(log, "m1", "m2")
    log.add("link.applied", link_fields(link_type="refines"))
    assert row(log.conn, "link", "l1")["status"] == "applied"


def test_a_link_to_work_points_at_the_work(log):
    items(log, "m3")
    log.add("link.applied", dict(link_id="l2", from_id="m3", to_id="w1", link_type="used_in", reason="same session",
                                 stated_by="construction", to_kind="work", checked_by=[]))  # fmt: skip
    link = row(log.conn, "link", "l2")
    assert (link["to_kind"], link["to_id"], link["type"]) == ("work", "w1", "used_in")


@pytest.mark.parametrize(
    "first, then, final",
    [("link.rejected", None, "rejected"), ("link.retracted", None, "retracted"), ("link.confirmed", "link.retracted", "retracted"),
     ("link.confirmed", "link.rejected", "rejected")],
)  # fmt: skip
def test_a_link_can_be_rejected_or_retracted(log, first, then, final):
    items(log, "m1", "m2")
    log.add("link.applied", link_fields())
    for type_ in (first, then):
        if type_:
            fields = {"link_id": "l1", "via": "click"} if type_ != "link.retracted" else {"link_id": "l1", "reason": "gone"}
            log.add(type_, fields)
    assert row(log.conn, "link", "l1")["status"] == final


@pytest.mark.parametrize("first, second", [("link.rejected", "link.confirmed"), ("link.retracted", "link.rejected")])
def test_a_finished_link_cannot_move_again(log, first, second):
    items(log, "m1", "m2")
    log.add("link.applied", link_fields())
    log.add(first, {"link_id": "l1", "via": "click"} if first == "link.rejected" else {"link_id": "l1", "reason": "gone"})
    with pytest.raises(ProjectionError, match="cannot become"):
        log.add(second, {"link_id": "l1", "via": "click"})


def test_applying_a_link_twice_is_refused(log):
    items(log, "m1", "m2")
    log.add("link.applied", link_fields())
    with pytest.raises(ProjectionError, match="not proposed"):
        log.add("link.applied", link_fields())


def test_a_same_as_link_merges_the_items(log):
    seed_item(log, "m12")
    seed_item(log, "m14")
    seed_item(log, "m9")
    log.add("item.value_changed", {"item_id": "m12"})
    merge = log.add("link.applied", link_fields("l9", "m14", "m12", "same_as", ))
    gone, kept = row(log.conn, "item", "m14"), row(log.conn, "item", "m12")
    assert gone["merged_into"] == "m12" and gone["status"] == "superseded" and gone["line"] == "Line of m14"
    assert json.loads(kept["contexts_seen"]) == ["A"]
    assert kept["value"] == "kept" and kept["status"] == "active"
    assert row(log.conn, "evidence", "ev-m14")["subject_id"] == "m12"
    assert row(log.conn, "evidence", "ev-m12")["subject_id"] == "m12"
    assert row(log.conn, "item", "m9")["merged_into"] is None
    assert row(log.conn, "link", "l9")["type"] == "same_as" and row(log.conn, "item", "m14")["seq_from"] == merge.seq


def test_a_merge_gathers_the_contexts_seen(log):
    seed_item(log, "m12")
    seed_item(log, "m14", learned_in="B")
    log.add("link.applied", link_fields("l9", "m14", "m12", "same_as"))
    assert json.loads(row(log.conn, "item", "m12")["contexts_seen"]) == ["A", "B"]


def test_a_proposed_same_as_merges_only_when_it_is_applied_or_confirmed(log):
    items(log, "m12", "m14")
    log.add("link.proposed", link_fields("l9", "m14", "m12", "same_as"))
    assert row(log.conn, "item", "m14")["merged_into"] is None
    log.add("link.confirmed", {"link_id": "l9", "via": "click"})
    assert row(log.conn, "item", "m14")["merged_into"] == "m12"
    assert row(log.conn, "evidence", "ev-m14")["subject_id"] == "m12"


@pytest.mark.parametrize("how", ["link.retracted", "link.rejected"])
def test_retracting_or_rejecting_a_merge_unmerges(log, how):
    seed_item(log, "m12")
    seed_item(log, "m14", learned_in="B")
    log.add("link.applied", link_fields("l9", "m14", "m12", "same_as"))
    log.add(how, {"link_id": "l9", "via": "click"} if how == "link.rejected" else {"link_id": "l9", "reason": "different"})
    gone, kept = row(log.conn, "item", "m14"), row(log.conn, "item", "m12")
    assert gone["merged_into"] is None and gone["status"] == "active"
    assert row(log.conn, "evidence", "ev-m14")["subject_id"] == "m14"
    assert row(log.conn, "evidence", "ev-m12")["subject_id"] == "m12"
    assert json.loads(kept["contexts_seen"]) == ["A"]


def test_an_item_merged_twice_is_refused(log):
    items(log, "m1", "m2", "m3")
    log.add("link.applied", link_fields("l1", "m1", "m2", "same_as"))
    with pytest.raises(ProjectionError, match="already merged"):
        log.add("link.applied", link_fields("l2", "m1", "m3", "same_as"))


def test_unmerging_one_alias_keeps_the_other_aliases_contexts(log):
    seed_item(log, "k", learned_in="A")
    seed_item(log, "a1", learned_in="B")
    seed_item(log, "a2", learned_in="C")
    log.add("link.applied", link_fields("l1", "a1", "k", "same_as"))
    log.add("link.applied", link_fields("l2", "a2", "k", "same_as"))
    assert json.loads(row(log.conn, "item", "k")["contexts_seen"]) == ["A", "B", "C"]
    log.add("link.retracted", {"link_id": "l1", "reason": "different"})
    assert json.loads(row(log.conn, "item", "k")["contexts_seen"]) == ["A", "C"]
    assert row(log.conn, "item", "a2")["merged_into"] == "k" and row(log.conn, "item", "a1")["merged_into"] is None


# --- supersession and conflicts ------------------------------------------------------------------------------------


def test_a_supersession_makes_the_old_item_superseded(log):
    items(log, "m6", "m7")
    ev = log.add("supersession.applied", dict(supersession_id="s1", old_item="m6", old_version=1, new_item="m7", new_version=None,
                                              reason="your_later_statement", evidence_ids=["ev-m7"]))  # fmt: skip
    sup = row(log.conn, "supersession", "s1")
    assert (sup["old_item"], sup["old_version"], sup["new_item"], sup["new_version"], sup["status"]) == ("m6", 1, "m7", None, "applied")
    assert sup["reason"] == "your_later_statement" and json.loads(sup["evidence_ids"]) == ["ev-m7"] and sup["at"] == ev.recorded_at
    assert row(log.conn, "item", "m6")["status"] == "superseded" and row(log.conn, "item", "m7")["status"] == "active"
    assert history(log.conn, "item", "m6")[0]["snapshot"]["status"] == "active"


def test_undoing_a_supersession_restores_the_old_item(log):
    items(log, "m6", "m7")
    log.add("supersession.applied", dict(supersession_id="s1", old_item="m6", old_version=1, new_item="m7", reason="your_later_statement"))
    log.add("supersession.undone", {"supersession_id": "s1", "reason": "audit disagreed"})
    assert row(log.conn, "supersession", "s1")["status"] == "undone"
    assert row(log.conn, "item", "m6")["status"] == "active"


def test_a_refresh_is_a_new_version_of_the_same_item(log):
    items(log, "m5", kind="plan", time_bound=True)
    log.run(("item.revised", {"item_id": "m5", "line": "Planned the demo; no later record", "reason": "refresh"}),
            ("supersession.applied", dict(supersession_id="s1", old_item="m5", old_version=1, new_item="m5", new_version=2, reason="refresh")))  # fmt: skip
    item = row(log.conn, "item", "m5")
    assert item["version"] == 2 and item["status"] == "active"
    assert row(log.conn, "supersession", "s1")["new_version"] == 2


def test_undoing_a_refresh_restores_the_old_content_as_a_new_version(log):
    items(log, "m5", kind="plan", time_bound=True)
    log.run(("item.revised", {"item_id": "m5", "line": "Planned the demo; no later record", "reason": "refresh"}),
            ("supersession.applied", dict(supersession_id="s1", old_item="m5", old_version=1, new_item="m5", new_version=2, reason="refresh")))  # fmt: skip
    log.add("supersession.undone", {"supersession_id": "s1", "reason": "audit disagreed"})
    item = row(log.conn, "item", "m5")
    assert item["line"] == "Line of m5" and item["version"] == 3 and item["status"] == "active"
    assert [h["version"] for h in history(log.conn, "item", "m5")] == [1, 2]


def conflict_fields(**extra):
    base = dict(conflict_id="c1", side_a_item="m1", side_a_version=1, side_b_item="m2", side_b_version=1, kind="across_contexts",
                state="both_stand", question_id=None, link_id=None, recheck_after=None)  # fmt: skip
    return {**base, **extra}


def test_a_conflict_opens_in_the_state_it_is_given(log):
    items(log, "m1", "m2", "m11")
    ev = log.add("conflict.opened", conflict_fields(state="contested", question_id="m11", recheck_after="2026-04-01"))
    conflict = row(log.conn, "conflict", "c1")
    assert (conflict["state"], conflict["kind"], conflict["question_id"], conflict["recheck_after"]) == ("contested", "across_contexts", "m11", "2026-04-01")
    assert conflict["resolution"] is None and conflict["created_seq"] == ev.seq and conflict["side_a_item"] == "m1"


def test_a_conflict_is_resolved_with_its_rule_and_inputs(log):
    items(log, "m1", "m2", "m11")
    log.add("conflict.opened", conflict_fields(state="open", kind="same_context"))
    log.add("conflict.resolved", dict(conflict_id="c1", step=2, state="resolved", rule_version="rules-1", winner="m2", resolution_inputs=["e1"]))
    conflict = row(log.conn, "conflict", "c1")
    assert conflict["state"] == "resolved"
    assert json.loads(conflict["resolution"]) == {"step": 2, "winner": "m2", "inputs": ["e1"], "rule_version": "rules-1"}
    log.add("conflict.resolved", dict(conflict_id="c1", step=3, state="contested", rule_version="rules-1", winner=None, question_id="m11",
                                      recheck_after="2026-05-01"))  # fmt: skip
    conflict = row(log.conn, "conflict", "c1")
    assert conflict["state"] == "contested" and conflict["question_id"] == "m11" and "winner" not in json.loads(conflict["resolution"])
    assert conflict["recheck_after"] == "2026-05-01"


def test_a_reopened_conflict_has_no_resolution(log):
    items(log, "m1", "m2")
    log.add("conflict.opened", conflict_fields(state="open"))
    log.add("conflict.resolved", dict(conflict_id="c1", step=2, state="resolved", rule_version="r", winner="m1"))
    log.add("conflict.reopened", {"conflict_id": "c1", "reason": "audit disagreed", "state": "contested", "recheck_after": "2026-06-01"})
    conflict = row(log.conn, "conflict", "c1")
    assert (conflict["state"], conflict["resolution"], conflict["recheck_after"]) == ("contested", None, "2026-06-01")


def test_undoing_an_opened_conflict_marks_it_undone(log):
    items(log, "m1", "m2")
    opened = log.add("conflict.opened", conflict_fields())
    log.add("conflict.undone", {"conflict_id": "c1", "reason": "opened in error"}, compensates=opened.id)
    assert row(log.conn, "conflict", "c1")["state"] == "undone"


def test_undoing_a_resolution_restores_the_state_before_it(log):
    items(log, "m1", "m2")
    log.add("conflict.opened", conflict_fields(state="open"))
    resolved = log.add("conflict.resolved", dict(conflict_id="c1", step=2, state="resolved", rule_version="r", winner="m1"))
    log.add("conflict.undone", {"conflict_id": "c1", "reason": "audit disagreed"}, compensates=resolved.id)
    conflict = row(log.conn, "conflict", "c1")
    assert (conflict["state"], conflict["resolution"]) == ("open", None)


def test_undoing_a_reopening_restores_the_resolution(log):
    items(log, "m1", "m2")
    log.add("conflict.opened", conflict_fields(state="open"))
    log.add("conflict.resolved", dict(conflict_id="c1", step=2, state="resolved", rule_version="r", winner="m1"))
    reopened = log.add("conflict.reopened", {"conflict_id": "c1", "reason": "recheck date passed"})
    log.add("conflict.undone", {"conflict_id": "c1", "reason": "reopened in error"}, compensates=reopened.id)
    conflict = row(log.conn, "conflict", "c1")
    assert conflict["state"] == "resolved" and json.loads(conflict["resolution"])["winner"] == "m1"


def test_without_compensates_the_latest_change_is_undone(log):
    items(log, "m1", "m2")
    log.add("conflict.opened", conflict_fields(state="open"))
    log.add("conflict.resolved", dict(conflict_id="c1", step=2, state="resolved", rule_version="r", winner="m1"))
    log.add("conflict.undone", {"conflict_id": "c1", "reason": "audit disagreed"})
    assert row(log.conn, "conflict", "c1")["state"] == "open"
    with pytest.raises(ProjectionError, match="cannot undo"):
        log.add("conflict.undone", {"conflict_id": "c1", "reason": "again"})


# --- goals and questions --------------------------------------------------------------------------------------------


def test_a_goal_is_an_item_of_kind_goal(log):
    log.run(evidence_op("ev11", "m9", context="C"), ("goal.created", {"evidence_ids": ["ev11"]}))
    goal = row(log.conn, "item", "m9")
    assert (goal["kind"], goal["class"], goal["goal_basis"], goal["goal_status"], goal["work_id"]) == ("goal", "view", "stated", "active", "T2")
    assert goal["raised_by"] is None and goal["question_status"] is None and goal["origin"] == "yours"
    assert goal["scope"] == "project:energy-dash" and json.loads(goal["contexts_seen"]) == ["C"]


def test_a_goal_changes_status_and_is_confirmed(log):
    log.run(evidence_op("ev11", "m9"), ("goal.created", {"evidence_ids": ["ev11"], "basis": "reported"}))
    log.add("goal.status_changed", {"item_id": "m9", "from_status": "active", "to_status": "paused"})
    assert row(log.conn, "item", "m9")["goal_status"] == "paused"
    log.add("goal.confirmed", {"item_id": "m9", "evidence_ids": ["ev13"]})
    goal = row(log.conn, "item", "m9")
    assert goal["goal_basis"] == "stated" and goal["version"] == 1
    assert [h["snapshot"]["goal_basis"] for h in history(log.conn, "item", "m9")] == ["reported", "reported"]


def test_goal_events_need_a_goal(log):
    items(log, "m1")
    with pytest.raises(ProjectionError, match="not a goal"):
        log.add("goal.status_changed", {"item_id": "m1", "from_status": "active", "to_status": "done"})
    with pytest.raises(ProjectionError, match="not a goal"):
        log.add("goal.confirmed", {"item_id": "m1"})


def test_a_question_is_an_item_of_kind_question(log):
    log.run(evidence_op("ev14", "m11"), ("question.created", {"evidence_ids": ["ev14"], "question_key": "alert fatigue"}))
    question = row(log.conn, "item", "m11")
    assert (question["kind"], question["class"], question["raised_by"], question["question_status"]) == ("question", "view", "you", "open")
    assert question["question_key"] == "alert fatigue" and question["goal_status"] is None
    assert json.loads(question["answered_by"]) == [] and row(log.conn, "item", "m1") is None
    seed_item(log, "m12")
    log.add("question.status_changed", {"item_id": "m11", "from_status": "open", "to_status": "answered", "answered_by": ["m12"]})
    assert row(log.conn, "item", "m11")["question_status"] == "answered"
    log.add("question.status_changed", {"item_id": "m11", "from_status": "answered", "to_status": "dormant", "answered_by": []})
    assert row(log.conn, "item", "m11")["question_status"] == "dormant"


def test_question_events_need_a_question(log):
    items(log, "m1")
    with pytest.raises(ProjectionError, match="not a question"):
        log.add("question.status_changed", {"item_id": "m1", "from_status": "open", "to_status": "dormant", "answered_by": []})


# --- work, working style, corrections, scopes ----------------------------------------------------------------------


def test_work_is_registered_and_labelled(log):
    ev = log.add("work.registered")
    work = row(log.conn, "work", "w1")
    assert (work["kind"], work["ref"], work["project"], work["evidence"], work["work_event_id"]) == ("commit", "a41c9e0", "energy-dash", "medium", "we1")
    assert work["label_source"] == "commit_message" and work["snapshot_sha256"] is None and work["created_seq"] == ev.seq
    log.add("work.labelled")
    work = row(log.conn, "work", "w1")
    assert work["label"] == "One SQLite file per meter with downsampling" and work["label_source"] == "checked"
    assert history(log.conn, "work", "w1")[0]["snapshot"]["label_source"] == "commit_message"


def test_working_style_is_recorded_and_revised(log):
    log.add("style.recorded")
    assert row(log.conn, "style_line", "st1")["basis"] == "stated_default"
    log.add("style.revised")
    assert row(log.conn, "style_line", "st1")["line"] == "Prefers short answers first"
    log.add("style.revised", {"line": None, "status": "retracted"})
    style = row(log.conn, "style_line", "st1")
    assert (style["line"], style["status"]) == ("Prefers short answers first", "retracted")
    assert len(history(log.conn, "style_line", "st1")) == 2


def test_a_correction_is_a_constraint_until_lifted(log):
    log.add("correction.applied")
    correction = row(log.conn, "correction", "co1")
    assert (correction["kind"], correction["target"], correction["via"], correction["status"]) == ("rename", "t1", "click", "active")
    assert json.loads(correction["constraint_rule"]) == {"label_fixed": True} and json.loads(correction["params"]) == {"label": "Energy dashboard"}
    assert correction["evidence_id"] is None and correction["lifted_reason"] is None
    log.add("correction.lifted")
    correction = row(log.conn, "correction", "co1")
    assert (correction["status"], correction["lifted_reason"]) == ("lifted", "your_undo")
    assert history(log.conn, "correction", "co1")[0]["snapshot"]["status"] == "active"


def test_a_typed_correction_keeps_the_evidence_id(log):
    log.add("correction.applied", {"via": "typed", "evidence_id": "ev5", "kind": "not_what_i_think", "target": "m3", "params": {}, "constraint": {}})
    assert row(log.conn, "correction", "co1")["evidence_id"] == "ev5"


def test_a_scope_is_held_and_released(log):
    ev = log.add("scope.hold_changed")
    scope = row(log.conn, "scope", "project:energy-dash")
    assert (scope["kind"], scope["held"], scope["held_seq"], scope["created_seq"]) == ("project", 1, ev.seq, ev.seq)
    released = log.add("scope.hold_changed", {"held": False, "reason": "you released it"})
    scope = row(log.conn, "scope", "project:energy-dash")
    assert (scope["held"], scope["held_seq"], scope["seq_from"]) == (0, None, released.seq)
    assert history(log.conn, "scope", "project:energy-dash")[0]["snapshot"]["held"] == 1


def test_the_personal_scope_has_its_own_kind(log):
    log.add("scope.hold_changed", {"scope_id": "personal"})
    assert row(log.conn, "scope", "personal")["kind"] == "personal"


# --- topics and placement ------------------------------------------------------------------------------------------


def test_a_topic_is_created_and_can_have_a_sub_topic(log):
    items(log, "m1")
    seed_topic(log, "t1", formation_overlap=0.4)
    seed_topic(log, "t2", parent_id="t1", label_fixed=True)
    top, sub = row(log.conn, "topic", "t1"), row(log.conn, "topic", "t2")
    assert (top["label"], top["status"], top["parent_id"], top["anchor_id"], top["label_fixed"]) == ("Topic t1", "active", None, "m1", 0)
    assert top["formation_overlap"] == 0.4 and (sub["parent_id"], sub["label_fixed"]) == ("t1", 1)


def test_topics_have_two_levels_at_most(log):
    seed_topic(log, "t1")
    seed_topic(log, "t2", parent_id="t1")
    with pytest.raises(ProjectionError, match="two levels"):
        seed_topic(log, "t3", parent_id="t2")
    with pytest.raises(ProjectionError, match="does not exist"):
        seed_topic(log, "t4", parent_id="nope")


def test_a_split_retires_the_topic_into_new_ones(log):
    seed_topic(log, "t1")
    log.add("topic.split")
    old = row(log.conn, "topic", "t1")
    assert (old["status"], old["redirect_to"]) == ("split_into", "t3")
    new = {t: row(log.conn, "topic", t) for t in ("t3", "t4")}
    assert (new["t3"]["label"], new["t3"]["anchor_id"], new["t3"]["status"], new["t3"]["parent_id"]) == ("Logger", "m1", "active", None)
    assert new["t4"]["label"] == "Charts" and new["t4"]["formation_overlap"] == 0.5 and new["t4"]["label_fixed"] == 0


def test_a_split_sub_topic_makes_sub_topics_of_the_same_parent(log):
    seed_topic(log, "t0")
    seed_topic(log, "t1", parent_id="t0")
    log.add("topic.split")
    assert row(log.conn, "topic", "t3")["parent_id"] == "t0" and row(log.conn, "topic", "t4")["parent_id"] == "t0"


def test_a_sub_topic_can_branch_out_and_a_topic_can_fold_back(log):
    seed_topic(log, "t1")
    seed_topic(log, "t2", parent_id="t1")
    seed_topic(log, "t5", parent_id="t1")
    log.add("topic.branched")
    assert row(log.conn, "topic", "t2")["parent_id"] is None
    log.add("topic.folded_back", {"topic_id": "t5"})
    folded = row(log.conn, "topic", "t5")
    assert (folded["status"], folded["redirect_to"], folded["parent_id"]) == ("folded_into", "t1", "t1")
    with pytest.raises(ProjectionError, match="not a sub-topic"):
        log.add("topic.branched", {"topic_id": "t1", "old_parent_id": "t9"})
    with pytest.raises(ProjectionError, match="folded_into"):
        log.add("topic.dormant", {"topic_id": "t5", "to_status": "active"})


def test_a_merged_topic_redirects(log):
    seed_topic(log, "t3")
    seed_topic(log, "t4")
    log.add("topic.merged")
    old = row(log.conn, "topic", "t4")
    assert (old["status"], old["redirect_to"]) == ("merged_into", "t3")
    assert row(log.conn, "topic", "t3")["status"] == "active"
    with pytest.raises(ProjectionError, match="merged_into"):
        log.add("topic.merged")


def test_a_renamed_topic_stays_fixed_once_you_fixed_it(log):
    seed_topic(log, "t1")
    log.add("topic.renamed")
    topic = row(log.conn, "topic", "t1")
    assert (topic["label"], topic["label_fixed"]) == ("Energy dashboard", 1)
    log.add("topic.renamed", {"label": "Energy", "label_fixed": False, "old_label": "Energy dashboard"})
    topic = row(log.conn, "topic", "t1")
    assert (topic["label"], topic["label_fixed"]) == ("Energy", 1)


def test_a_topic_goes_dormant_and_wakes(log):
    seed_topic(log, "t5")
    log.add("topic.dormant")
    assert row(log.conn, "topic", "t5")["status"] == "dormant"
    log.add("topic.dormant", {"to_status": "active", "reason": "new activity"})
    assert row(log.conn, "topic", "t5")["status"] == "active"
    assert [h["snapshot"]["status"] for h in history(log.conn, "topic", "t5")] == ["active", "dormant"]


def place(log, placement_id, item_id, topic_id, role="home", tentative=False):
    return log.add("idea.placed", dict(placement_id=placement_id, item_id=item_id, topic_id=topic_id, role=role, tentative=tentative,
                                       reasons=["same chat"]))  # fmt: skip


def places(conn, item_id):
    rows = conn.execute("SELECT topic_id, role, tentative FROM placement WHERE item_id = ? ORDER BY topic_id", (item_id,))
    return [tuple(r) for r in rows]


def test_an_idea_is_placed_with_its_reasons(log):
    items(log, "m7")
    seed_topic(log, "t5")
    ev = log.add("idea.placed")
    placement = row(log.conn, "placement", "p1")
    assert (placement["item_id"], placement["topic_id"], placement["role"], placement["tentative"]) == ("m7", "t5", "home", 0)
    assert json.loads(placement["reasons"]) == ["same chat", "argues with m6"] and placement["created_seq"] == ev.seq


def test_placing_again_settles_a_tentative_placement(log):
    items(log, "m7")
    seed_topic(log, "t5")
    place(log, "p1", "m7", "t5", tentative=True)
    place(log, "p9", "m7", "t5", tentative=False)
    assert places(log.conn, "m7") == [("t5", "home", 0)]
    assert row(log.conn, "placement", "p1")["tentative"] == 0 and row(log.conn, "placement", "p9") is None
    assert history(log.conn, "placement", "p1")[0]["snapshot"]["tentative"] == 1


def test_a_new_home_demotes_the_old_home(log):
    items(log, "m7")
    seed_topic(log, "t1"), seed_topic(log, "t5")
    place(log, "p1", "m7", "t5")
    place(log, "p2", "m7", "t1")
    assert places(log.conn, "m7") == [("t1", "home", 0), ("t5", "also_in", 0)]
    assert row(log.conn, "placement", "p1")["role"] == "also_in"


def test_a_new_home_removes_the_old_one_when_there_are_two_also_in_places(log):
    items(log, "m7")
    for t in ("t1", "t2", "t3", "t4"):
        seed_topic(log, t)
    place(log, "p1", "m7", "t1")
    place(log, "p2", "m7", "t2", "also_in")
    place(log, "p3", "m7", "t3", "also_in")
    place(log, "p4", "m7", "t4")
    assert places(log.conn, "m7") == [("t2", "also_in", 0), ("t3", "also_in", 0), ("t4", "home", 0)]
    assert row(log.conn, "placement", "p1") is None
    assert history(log.conn, "placement", "p1")[0]["snapshot"]["role"] == "home"


def test_an_idea_has_at_most_two_also_in_places(log):
    items(log, "m7")
    for t in ("t1", "t2", "t3", "t4"):
        seed_topic(log, t)
    place(log, "p1", "m7", "t1")
    place(log, "p2", "m7", "t2", "also_in")
    place(log, "p3", "m7", "t3", "also_in")
    with pytest.raises(ProjectionError, match="also_in"):
        place(log, "p4", "m7", "t4", "also_in")


def test_moving_an_idea_keeps_the_place_and_its_role(log):
    items(log, "m7")
    seed_topic(log, "t1"), seed_topic(log, "t5")
    place(log, "p1", "m7", "t5")
    log.add("idea.moved", dict(role="home", to_topic_id="t1"))
    assert places(log.conn, "m7") == [("t1", "home", 0)]
    assert row(log.conn, "placement", "p1")["topic_id"] == "t1"
    assert history(log.conn, "placement", "p1")[0]["snapshot"]["topic_id"] == "t5"


def test_moving_the_home_demotes_a_home_already_in_the_target_topic(log):
    items(log, "m7")
    seed_topic(log, "t1"), seed_topic(log, "t5")
    place(log, "p1", "m7", "t5")
    place(log, "p2", "m7", "t1", "also_in")
    log.add("idea.moved", dict(role="home", to_topic_id="t1"))
    assert places(log.conn, "m7") == [("t1", "home", 0)]
    assert row(log.conn, "placement", "p1") is None and row(log.conn, "placement", "p2")["role"] == "home"


def test_moving_an_idea_that_is_not_there_is_refused(log):
    items(log, "m7")
    seed_topic(log, "t1"), seed_topic(log, "t5")
    with pytest.raises(ProjectionError, match="no place"):
        log.add("idea.moved")


def test_a_retired_topic_keeps_its_placements(log):
    items(log, "m7")
    seed_topic(log, "t3"), seed_topic(log, "t4")
    place(log, "p1", "m7", "t4")
    log.add("topic.merged")
    assert places(log.conn, "m7") == [("t4", "home", 0)]


# --- compensation --------------------------------------------------------------------------------------------------


def batch(log, *events, **fields):
    payload = dict(batch_id=f"b{log.count}", reason="audit disagreed", compensated_event_ids=[e.id for e in events], run_id_undone=None)
    return log.add("compensation.batch", {**payload, **fields})


def test_a_batch_removes_what_the_events_created(log):
    created = seed_item(log, "m1")
    seed_item(log, "m2")
    b = batch(log, *created)
    assert row(log.conn, "item", "m1") is None and row(log.conn, "evidence", "ev-m1") is None
    assert row(log.conn, "item", "m2") is not None
    (old,) = history(log.conn, "item", "m1")
    assert (old["seq_from"], old["seq_to"]) == (created[1].seq, b.seq)


def test_a_batch_restores_what_a_change_changed(log):
    items(log, "m1")
    rev = log.add("item.revised", {"item_id": "m1", "line": "Different", "reason": "restated", "why": "new reason"})
    batch(log, rev)
    item = row(log.conn, "item", "m1")
    assert (item["line"], item["why"], item["version"]) == ("Line of m1", "", 3)
    assert [h["version"] for h in history(log.conn, "item", "m1")] == [1, 2]


def test_a_batch_leaves_other_fields_alone(log):
    items(log, "m1")
    status = log.add("item.status_changed", {"item_id": "m1", "from_status": "active", "to_status": "quarantined"})
    log.add("item.value_changed", {"item_id": "m1"})
    batch(log, status)
    item = row(log.conn, "item", "m1")
    assert (item["status"], item["value"], item["version"]) == ("active", "kept", 1)


def test_a_batch_undoes_a_run_latest_event_first(log):
    evs = seed_item(log, "m1")
    stance = log.add("stance.recorded", {"item_id": "m1", "evidence_ids": ["ev-m1"]})
    kept = log.add("item.value_changed", {"item_id": "m1"})
    rev = log.add("item.revised", {"item_id": "m1", "line": "Changed", "reason": "restated"})
    batch(log, *evs, stance, kept, rev)
    assert row(log.conn, "item", "m1") is None and row(log.conn, "evidence", "ev-m1") is None
    assert row(log.conn, "stance", stance.id) is None  # a stance cannot outlive its item


def test_a_batch_puts_back_what_the_events_removed(log):
    items(log, "m7")
    seed_topic(log, "t1"), seed_topic(log, "t2"), seed_topic(log, "t3")
    place(log, "p1", "m7", "t1")
    place(log, "p2", "m7", "t2", "also_in")
    place(log, "p3", "m7", "t3", "also_in")
    seed_topic(log, "t4")
    moved = place(log, "p4", "m7", "t4")  # demotes... two also_in places: the old home is removed
    assert row(log.conn, "placement", "p1") is None
    batch(log, moved)
    assert places(log.conn, "m7") == [("t1", "home", 0), ("t2", "also_in", 0), ("t3", "also_in", 0)]
    assert row(log.conn, "placement", "p4") is None


def test_a_batch_undoes_a_merge(log):
    seed_item(log, "m12")
    seed_item(log, "m14", learned_in="B")
    merge = log.add("link.applied", link_fields("l9", "m14", "m12", "same_as"))
    batch(log, merge)
    assert row(log.conn, "link", "l9") is None
    assert row(log.conn, "item", "m14")["merged_into"] is None and row(log.conn, "item", "m14")["status"] == "active"
    assert row(log.conn, "evidence", "ev-m14")["subject_id"] == "m14"
    assert json.loads(row(log.conn, "item", "m12")["contexts_seen"]) == ["A"]


def test_a_batch_undoes_a_topic_split(log):
    seed_topic(log, "t1")
    split = log.add("topic.split")
    batch(log, split)
    assert row(log.conn, "topic", "t3") is None and row(log.conn, "topic", "t4") is None
    assert row(log.conn, "topic", "t1")["status"] == "active" and row(log.conn, "topic", "t1")["redirect_to"] is None


def test_a_batch_can_be_undone_in_turn(log):
    items(log, "m1")
    rev = log.add("item.revised", {"item_id": "m1", "line": "Different", "reason": "restated"})
    first = batch(log, rev)
    batch(log, first)
    assert row(log.conn, "item", "m1")["line"] == "Different"


def test_a_change_made_after_the_event_is_not_overwritten(log):
    items(log, "m1")
    rev = log.add("item.revised", {"item_id": "m1", "line": "Different", "reason": "restated"})
    log.add("item.revised", {"item_id": "m1", "line": "Different again", "reason": "restated"})
    with pytest.raises(ProjectionError, match="changed after"):
        batch(log, rev)
    assert row(log.conn, "item", "m1")["line"] == "Different again"


def test_an_event_that_was_undone_by_its_own_event_is_skipped(log):
    items(log, "m6", "m7")
    sup = log.add("supersession.applied", dict(supersession_id="s1", old_item="m6", old_version=1, new_item="m7", reason="your_later_statement"))
    log.add("supersession.undone", {"supersession_id": "s1", "reason": "audit disagreed"}, compensates=sup.id)
    batch(log, sup)
    assert row(log.conn, "supersession", "s1")["status"] == "undone"
    assert row(log.conn, "item", "m6")["status"] == "active"


def test_a_purge_cannot_be_compensated(log):
    items(log, "m1")
    purge = log.add("purge.applied", {"item_ids": ["m1"]})
    with pytest.raises(ProjectionError, match="purge"):
        batch(log, purge)


def test_a_batch_names_earlier_events_only(log):
    items(log, "m1")
    with pytest.raises(ProjectionError, match="earlier"):
        log.add("compensation.batch", dict(batch_id="b", reason="x", compensated_event_ids=["01HZZZZZZZZZZZZZZZZZZZZZZZ"]))


# --- purge ---------------------------------------------------------------------------------------------------------


def test_a_purge_leaves_a_stub_and_scrubs_the_words(log):
    seed_item(log, "m3", your_words="SQLite please", why="small")
    log.add("item.revised", {"item_id": "m3", "line": "Second wording", "reason": "restated"})
    log.add("stance.recorded", {"item_id": "m3", "evidence_ids": ["ev-m3"]})
    log.add("purge.applied", {"item_ids": ["m3"], "requested_at": "2026-04-01T09:00:00Z"})
    item = row(log.conn, "item", "m3")
    assert item["status"] == "purged" and item["line"] == PURGE_STUB.format(date="2026-04-01") == "removed at your request on 2026-04-01"
    assert (item["your_words"], item["why"], item["question_key"]) == ("", "", "")
    assert row(log.conn, "evidence", "ev-m3")["quote"] == ""
    for snapshot in history(log.conn, "item", "m3"):
        assert snapshot["snapshot"]["line"] == item["line"] and snapshot["snapshot"]["your_words"] == ""
    for history_row in history(log.conn, "evidence", "ev-m3"):
        assert history_row["snapshot"]["quote"] == ""


def test_a_purge_leaves_no_words_anywhere_in_memory_db(log):
    log.run(evidence_op("ev-m3", "m3", quote="Haystack quote words"),
            ("item.created", dict(item_id="m3", kind="decision", line="Needle in a haystack", scope="personal", learned_in="A",
                                  origin="yours", evidence_ids=["ev-m3"], said_at="2026-03-02T09:30:00Z",
                                  your_words="SQLite please", why="because tiny")))  # fmt: skip
    seed_item(log, "m4", line="Plain line")
    log.add("item.revised", {"item_id": "m3", "line": "Second needle", "reason": "restated"})
    log.add("link.applied", link_fields("l1", "m3", "m4", reason="the needle backs it"))
    log.add("purge.applied", {"item_ids": ["m3"]})
    for table in ("item", "item_history", "evidence", "evidence_history", "link", "link_history", "event"):
        for stored in log.conn.execute(f"SELECT * FROM {table}"):
            text = " ".join(str(v) for v in stored)
            assert "needle" not in text.lower(), table
            assert "SQLite please" not in text and "because tiny" not in text and "Haystack quote" not in text, table
    assert row(log.conn, "item", "m4")["line"] == "Plain line"
    assert row(log.conn, "evidence", "ev-m4")["quote"] == "Store readings in SQLite"


def test_a_purge_authorizes_what_it_scrubs_and_keeps_that_record(log):
    items(log, "m3")
    log.add("purge.applied", {"item_ids": ["m3"], "purge_id": "pg9"})
    targets = {(r["target_table"], r["target_id"]) for r in log.conn.execute("SELECT * FROM purge_authorization WHERE purge_id = 'pg9'")}
    assert {("evidence", "ev-m3"), ("evidence_history", "ev-m3"), ("item_history", "m3")} <= targets
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        log.conn.execute("DELETE FROM purge_authorization")


def test_a_purge_covers_items_merged_into_the_purged_item(log):
    seed_item(log, "m12", line="Kept idea")
    seed_item(log, "m14", line="Alias wording")
    log.add("link.applied", link_fields("l9", "m14", "m12", "same_as", ))
    log.add("purge.applied", {"item_ids": ["m12"]})
    assert row(log.conn, "item", "m14")["status"] == "purged" and "Alias" not in row(log.conn, "item", "m14")["line"]
    assert row(log.conn, "evidence", "ev-m14")["quote"] == ""


def test_a_purge_does_not_touch_other_items(log):
    items(log, "m3", "m4")
    log.add("purge.applied", {"item_ids": ["m3"]})
    assert row(log.conn, "item", "m4")["status"] == "active" and row(log.conn, "evidence", "ev-m4")["quote"] == "Store readings in SQLite"


def test_a_purge_of_an_unknown_item_is_refused(log):
    with pytest.raises(ProjectionError, match="does not exist"):
        log.add("purge.applied", {"item_ids": ["nope"]})


def test_a_batch_of_a_stance_removes_only_the_stance(log):
    items(log, "m1")
    stance = log.add("stance.recorded", {"item_id": "m1", "evidence_ids": ["ev-m1"]})
    b = batch(log, stance)
    assert row(log.conn, "stance", stance.id) is None and row(log.conn, "item", "m1") is not None
    auth = log.conn.execute("SELECT * FROM purge_authorization WHERE target_table = 'stance'").fetchone()
    assert auth["target_id"] == stance.id and auth["purge_id"] == f"compensation:{b.id}"


def test_purged_words_become_numbered_tokens_and_equal_words_share_one(log):
    seed_item(log, "m3")
    log.add("item.revised", {"item_id": "m3", "line": "Another wording", "reason": "restated"})
    log.add("item.revised", {"item_id": "m3", "line": "Line of m3", "reason": "restated"})
    log.add("purge.applied", {"item_ids": ["m3"]})
    lines = [json.loads(r["payload"]).get("line") for r in log.conn.execute("SELECT payload FROM event WHERE type IN ('item.created', 'item.revised') ORDER BY seq")]
    assert lines[0] == lines[2] and lines[0] != lines[1]
    assert all(line.startswith("[purged:") for line in lines)


# --- review fixes: loops, purged items, dangling ends, atomic apply ----------------------------------------------------


def test_a_merge_that_would_loop_the_aliases_is_refused(log):
    items(log, "m1", "m2")
    log.add("link.applied", link_fields("l1", "m1", "m2", "same_as"))
    with pytest.raises(ProjectionError, match="loop"):
        log.add("link.applied", link_fields("l2", "m2", "m1", "same_as"))
    assert row(log.conn, "item", "m2")["merged_into"] is None


def test_a_longer_alias_loop_is_refused(log):
    items(log, "m1", "m2", "m3")
    log.add("link.applied", link_fields("l1", "m1", "m2", "same_as"))
    log.add("link.applied", link_fields("l2", "m2", "m3", "same_as"))
    with pytest.raises(ProjectionError, match="loop"):
        log.add("link.applied", link_fields("l3", "m3", "m1", "same_as"))


def _purged(log):
    items(log, "m3", "m4")
    log.add("purge.applied", {"item_ids": ["m3"]})


@pytest.mark.parametrize("type_,fields", [
    ("item.revised", {"item_id": "m3", "base_version": 1, "line": "the old words again", "reason": "restated"}),
    ("item.value_changed", {"item_id": "m3"}),
    ("item.status_changed", {"item_id": "m3", "from_status": "active", "to_status": "retracted"}),
    ("item.checked", {"item_id": "m3"}),
    ("link.proposed", link_fields("l8", "m4", "m3", "supports")),
    ("link.applied", link_fields("l8", "m3", "m4", "supports")),
    ("evidence.anchored", evidence_op("ev-new", "m3")[1]),
])  # fmt: skip
def test_nothing_changes_or_joins_a_purged_item(log, type_, fields):
    _purged(log)
    with pytest.raises(ProjectionError, match="purged"):
        log.add(type_, fields)
    assert row(log.conn, "item", "m3")["line"] == PURGE_STUB.format(date=row(log.conn, "item", "m3")["line"][-10:])


def test_a_link_to_an_item_that_does_not_exist_is_refused(log):
    items(log, "m1")
    with pytest.raises(ProjectionError, match="does not exist"):
        log.add("link.applied", link_fields("l1", "m1", "nope", "supports"))


def test_apply_is_all_or_nothing_even_outside_a_transaction(memory):
    from northstar_agent_memory.core.replay import append_event

    log = Log(memory)
    good = log.envelope("scope.hold_changed", {"scope_id": "project:a", "held": True})
    bad = log.envelope("item.value_changed", {"item_id": "nope"})
    for env in (good, bad):
        append_event(memory, env)
    assert not memory.in_transaction
    with pytest.raises(ProjectionError):
        log.projector.apply(memory, [good, bad])
    assert row(memory, "scope", "project:a") is None and not memory.in_transaction


# --- hardening: contexts from evidence, answered_by, references, rollback of evidence ----------------------------------


def seed_in_context(log, item_id, context, *, learned_in="project:energy-dash", **fields):
    """An item whose one piece of evidence was stamped with `context`."""
    evidence_id = f"ev-{item_id}"
    item = dict(item_id=item_id, kind="decision", line=f"Line of {item_id}", scope="personal", learned_in=learned_in, origin="yours",
                evidence_ids=[evidence_id], said_at="2026-03-02T09:30:00Z")  # fmt: skip
    return log.run(evidence_op(evidence_id, item_id, context=context), ("item.created", {**item, **fields}))


def contexts(log, item_id):
    return json.loads(row(log.conn, "item", item_id)["contexts_seen"])


def test_evidence_keeps_the_context_the_gate_stamped(log):
    seed_in_context(log, "m1", "personal")
    assert row(log.conn, "evidence", "ev-m1")["context"] == "personal"
    seed_item(log, "m2")
    assert row(log.conn, "evidence", "ev-m2")["context"] == "A"


def test_evidence_from_a_new_context_extends_contexts_seen(log):
    seed_in_context(log, "m1", "project:energy-dash")
    assert contexts(log, "m1") == ["project:energy-dash"]
    anchored = log.add("evidence.anchored", {**evidence_op("ev-late", "m1", context="personal")[1]})
    assert contexts(log, "m1") == ["project:energy-dash", "personal"]
    (old,) = history(log.conn, "item", "m1")
    assert json.loads(old["snapshot"]["contexts_seen"]) == ["project:energy-dash"] and old["seq_to"] == anchored.seq
    assert row(log.conn, "item", "m1")["version"] == 1  # a context is not a new version of the line


def test_evidence_in_a_context_already_seen_changes_nothing(log):
    seed_in_context(log, "m1", "project:energy-dash")
    log.add("evidence.anchored", {**evidence_op("ev-again", "m1", context="project:energy-dash")[1]})
    assert contexts(log, "m1") == ["project:energy-dash"] and history(log.conn, "item", "m1") == []


def test_evidence_from_the_context_the_item_was_learned_in_leaves_contexts_seen_alone(log):
    seed_item(log, "m1")
    log.add("evidence.anchored", {**evidence_op("ev-more", "m1", context="A")[1]})
    assert contexts(log, "m1") == ["A"] and history(log.conn, "item", "m1") == []


def test_evidence_anchored_before_its_item_counts_when_the_item_arrives(log):
    log.run(evidence_op("ev-a", "m1", context="personal"), evidence_op("ev-b", "m1", context="project:de-course"),
            ("item.created", dict(item_id="m1", kind="decision", line="L", scope="personal", learned_in="project:energy-dash",
                                  origin="yours", evidence_ids=["ev-a", "ev-b"], said_at="2026-03-02T09:30:00Z")))  # fmt: skip
    assert contexts(log, "m1") == ["project:energy-dash", "personal", "project:de-course"]


def test_evidence_for_a_style_line_or_a_correction_touches_no_item(log):
    seed_item(log, "m1")
    log.add("evidence.anchored", {**evidence_op("e-style", "st1", subject_kind="style_line", context="personal")[1]})
    assert contexts(log, "m1") == ["A"] and row(log.conn, "evidence", "e-style")["context"] == "personal"


def test_a_rollback_of_the_evidence_takes_its_context_back(log):
    seed_in_context(log, "m1", "project:energy-dash")
    late = log.add("evidence.anchored", {**evidence_op("ev-late", "m1", context="personal")[1]})
    batch(log, late)
    assert contexts(log, "m1") == ["project:energy-dash"] and row(log.conn, "evidence", "ev-late") is None


def test_an_unmerge_keeps_the_contexts_the_kept_items_own_evidence_brought(log):
    seed_in_context(log, "k", "project:energy-dash")
    log.add("evidence.anchored", {**evidence_op("ev-k2", "k", context="personal")[1]})
    seed_in_context(log, "a", "project:de-course", learned_in="project:de-course")
    log.add("link.applied", link_fields("l1", "a", "k", "same_as"))
    assert contexts(log, "k") == ["project:energy-dash", "personal", "project:de-course"]
    log.add("link.retracted", {"link_id": "l1", "reason": "different ideas"})
    assert contexts(log, "k") == ["project:energy-dash", "personal"]


def test_an_answered_question_keeps_the_items_that_answer_it(log):
    log.run(evidence_op("ev14", "m11"), ("question.created", {"evidence_ids": ["ev14"]}))
    seed_item(log, "m12")
    seed_item(log, "m13")
    changed = log.add("question.status_changed", {"item_id": "m11", "from_status": "open", "to_status": "answered", "answered_by": ["m12", "m13"]})
    assert json.loads(row(log.conn, "item", "m11")["answered_by"]) == ["m12", "m13"]
    log.add("question.status_changed", {"item_id": "m11", "from_status": "answered", "to_status": "open", "answered_by": []})
    assert json.loads(row(log.conn, "item", "m11")["answered_by"]) == []
    batch(log, changed)  # undoing the answer puts the earlier (empty) list back, field by field from row history
    assert json.loads(row(log.conn, "item", "m11")["answered_by"]) == []


def test_only_a_question_has_answers(log):
    seed_item(log, "m1")
    assert row(log.conn, "item", "m1")["answered_by"] is None
    with pytest.raises(sqlite3.IntegrityError):
        log.conn.execute("UPDATE item SET answered_by = '[]' WHERE id = 'm1'")


def test_an_answer_that_does_not_exist_is_a_projection_error_not_a_commit_failure(log):
    """Attack: a question marked answered by an item that is not there. Before, the foreign key (when there was one) failed at
    COMMIT, after the gate had finished; now the projector refuses it and nothing is written."""
    log.run(evidence_op("ev14", "m11"), ("question.created", {"evidence_ids": ["ev14"]}))
    with pytest.raises(ProjectionError, match="'ghost'.*does not exist"):
        log.add("question.status_changed", {"item_id": "m11", "from_status": "open", "to_status": "answered", "answered_by": ["ghost"]})
    assert row(log.conn, "item", "m11")["question_status"] == "open" and json.loads(row(log.conn, "item", "m11")["answered_by"]) == []


def test_a_purged_item_cannot_be_named_as_an_answer(log):
    log.run(evidence_op("ev14", "m11"), ("question.created", {"evidence_ids": ["ev14"]}))
    seed_item(log, "m12")
    log.add("purge.applied", {"item_ids": ["m12"]})
    with pytest.raises(ProjectionError, match="purged"):
        log.add("question.status_changed", {"item_id": "m11", "from_status": "open", "to_status": "answered", "answered_by": ["m12"]})


@pytest.mark.parametrize(
    ("type_", "fields"),
    [
        ("conflict.opened", dict(side_a_item="m1", side_b_item="ghost")),
        ("conflict.opened", dict(side_a_item="ghost", side_b_item="m2")),
        ("conflict.opened", dict(side_a_item="m1", side_b_item="m2", question_id="ghost")),
    ],
)
def test_a_conflict_that_names_a_missing_item_is_a_projection_error(log, type_, fields):
    items(log, "m1", "m2")
    with pytest.raises(ProjectionError, match="'ghost' does not exist"):
        log.add(type_, {"conflict_id": "c1", "side_a_version": 1, "side_b_version": 1, **fields})
    assert row(log.conn, "conflict", "c1") is None


def test_resolving_a_conflict_with_a_missing_question_is_a_projection_error(log):
    items(log, "m6", "m7")
    log.add("conflict.opened", dict(conflict_id="c1", side_a_item="m6", side_b_item="m7", side_a_version=1, side_b_version=1))
    with pytest.raises(ProjectionError, match="'ghost' does not exist"):
        log.add("conflict.resolved", dict(conflict_id="c1", step=3, state="contested", question_id="ghost", winner=None))
    assert row(log.conn, "conflict", "c1")["question_id"] is None


def test_a_rollback_that_would_orphan_a_row_is_a_projection_error_not_a_commit_failure(log):
    """Attack: roll back the event that created an item while a link and a placement still name it. Before, every row of the
    batch was written and the foreign keys failed at COMMIT; now the batch is refused and the gate's transaction rolls back."""
    created = seed_item(log, "m1")
    seed_item(log, "m2")
    seed_topic(log, "t1")
    log.add("link.applied", link_fields("l1", "m2", "m1"))
    log.add("idea.placed", dict(placement_id="p1", item_id="m1", topic_id="t1", role="home", tentative=False, reasons=[]))
    with pytest.raises(ProjectionError, match="no longer exists"):
        batch(log, *created)
    assert not log.conn.in_transaction  # the failed proposal rolled back, every row of the batch with it
    for table, key in (("item", "m1"), ("evidence", "ev-m1"), ("link", "l1"), ("placement", "p1")):
        assert row(log.conn, table, key) is not None, table
    assert log.conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_a_rollback_of_evidence_writes_the_authorization_the_schema_asks_for(log):
    created = seed_item(log, "m1")
    b = batch(log, *created)
    auth = {(r["target_table"], r["target_id"], r["purge_id"]) for r in log.conn.execute("SELECT * FROM purge_authorization")}
    assert ("evidence", "ev-m1", f"compensation:{b.id}") in auth
    assert row(log.conn, "evidence", "ev-m1") is None
    (gone,) = history(log.conn, "evidence", "ev-m1")
    assert gone["seq_to"] == b.seq
