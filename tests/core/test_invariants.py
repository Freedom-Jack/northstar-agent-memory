"""The invariant table of §7, the check functions the gate runs, and the read-only sweep over whole stores.
Every fixture is invented; see gate_fixtures.py."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from northstar_agent_memory.core import db, invariants as inv
from northstar_agent_memory.core.invariants import (
    ENFORCERS, GATE_CHECKS, INVARIANTS, Context, Evidence, HistoryRead, Limits, MemoryRead, Violation,
)  # fmt: skip
from northstar_agent_memory.core.ports import Proposal
from northstar_agent_memory.transcript import Message

from .gate_fixtures import CHECKER, NOW, SAID, SCOPE, make_world, varied, world  # noqa: F401

SPEC = Path(__file__).parents[2] / "docs" / "design" / "revision-2026-10-23" / "MEMORY-ARCHITECTURE.md"


# --- the table ----------------------------------------------------------------------------------------------------


def spec_invariants() -> dict[str, str]:
    text = SPEC.read_text(encoding="utf-8")
    section = text[text.index("## 7. Invariants") : text.index("## 8. What changed")]
    return {m.group(1): m.group(2) for m in re.finditer(r"^\| (I\d+) \| (.*?) \|", section, re.M)}


def test_the_table_lists_exactly_the_invariants_of_section_7():
    spec = spec_invariants()
    assert len(spec) == 25 and set(INVARIANTS) == set(spec)  # I8 is dropped with the Book, I22 merged into I5
    assert "I8" not in INVARIANTS and "I22" not in INVARIANTS


def test_every_enforcer_is_known_and_the_later_build_steps_are_named():
    assert all(set(v) <= set(ENFORCERS) and v for v in INVARIANTS.values())
    later = {"I9": "rebuild", "I27": "rebuild", "I10": "extraction", "I11": "extraction", "I18": "replay", "I19": "lint",
             "I23": "lint", "I25": "delivery", "I26": "structure", "I6": "trigger"}  # fmt: skip
    for key, step in later.items():
        assert step in INVARIANTS[key], key
    assert INVARIANTS["I1"] == ("gate", "sweep")


def test_every_invariant_the_gate_enforces_has_a_check():
    covered = {i for ids, _ in GATE_CHECKS for i in ids}
    assert {i for i, how in INVARIANTS.items() if "gate" in how} <= covered
    assert covered <= set(INVARIANTS)


def test_the_gate_checks_are_functions_that_take_a_context():
    assert all(callable(check) for _, check in GATE_CHECKS)


def test_nothing_in_the_core_logic_names_a_product(world):
    """I23: the core is product-blind. A cheap lint over the two files of this part."""
    root = Path(inv.__file__).parent
    banned = re.compile(r"claude|chatgpt|openai|anthropic|codex|gemini", re.I)
    for name in ("gate.py", "invariants.py"):
        for number, text in enumerate((root / name).read_text(encoding="utf-8").splitlines(), 1):
            assert not banned.search(text), f"{name}:{number}: {text}"


# --- helpers ------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "problem, expected",
    [
        ("payload: I3: speaker comes from capture, not from a proposal", "I3"),
        ("payload: I1: an item cites at least one piece of evidence", "I1"),
        ("proposal_id and index_in_proposal come together (I14)", "I14"),
        ("I5: a typed correction cites your words", "I5"),
        ("payload: unknown field 'x'", "I15"),
        ("I15: item.created has no schema version 7", "I15"),
        ("a link carries one line of reason", "I15"),
        ("I99: not an invariant", "I15"),
    ],
)
def test_invariant_of_reads_the_id_a_problem_names(problem, expected):
    assert inv.invariant_of(problem) == expected


@pytest.mark.parametrize("text, parsed", [("m3@2", ("item", "m3", "2")), ("item:m3@2", ("item", "m3", "2")), ("message:S1:0@1", ("message", "S1:0", "1")), ("start_note:t1@3", ("start_note", "t1", "3"))])
def test_parse_input(text, parsed):
    assert inv.parse_input(text) == parsed


def test_input_problem_names_derived_and_unknown_inputs():
    assert inv.input_problem("m3@2") is None and inv.input_problem("link:l1@4") is None and inv.input_problem("message:S1:0@1") is None
    for kind in inv.DERIVED_INPUT_KINDS:
        assert "derived" in inv.input_problem(f"{kind}:x@1")
    assert "not a typed input" in inv.input_problem("diary:x@1")


def test_quote_problem():
    text = "Keep  one   file per meter, please."
    assert inv.quote_problem(text, 0, len("Keep  one   file per meter"), "Keep one file per meter") is None  # normalized spaces
    assert "outside" in inv.quote_problem(text, 5, 500, "one")
    assert "outside" in inv.quote_problem(text, -1, 3, "Kee")
    assert "empty" in inv.quote_problem(text, 0, 3, "  ")
    assert "not the text" in inv.quote_problem(text, 0, 4, "Kept")
    assert inv.quote_problem("Café au lait", 0, 5, "Café") is None  # Unicode normalized


def ev(role="primary", speaker="user", origin="typed", agent=None, source_id="S1", lineage="primary", model_family=None, subject_id="m1"):
    return Evidence("e", "item", subject_id, "S1:0", 0, 3, "abc", role, lineage, speaker, agent, model_family, origin, source_id)


def test_origin_is_computed_from_the_evidence():
    assert inv.origin_of([ev()]) == "yours"
    assert inv.origin_of([ev(speaker="assistant", origin="assistant_output", agent="claude-code"), ev("adoption")]) == "adopted:claude-code"
    assert inv.origin_of([ev(speaker="assistant", agent=None, model_family="fam", origin="assistant_output")]) == "adopted:fam"
    assert inv.origin_of([ev(speaker="assistant", agent=None, origin="assistant_output")]) == "adopted:assistant"
    assert inv.origin_of([ev(speaker="assistant", role="support", origin="assistant_output"), ev()]) == "yours"  # an AI span that only supports
    assert inv.origin_of([ev(speaker="tool", origin="tool_output")]) is None and inv.origin_of([]) is None


def test_typed_by_you_means_your_speaker_and_a_typed_origin():
    assert ev().typed_by_you
    assert not ev(origin="pasted").typed_by_you and not ev(origin="model_reported").typed_by_you
    assert not ev(speaker="assistant", origin="assistant_output").typed_by_you


def item_row(line="Readings go to SQLite", scope=SCOPE, kind="decision", words=""):
    return dict(line=line, scope=scope, kind=kind, your_words=words)


def test_exact_key_needs_the_same_scope_kind_and_line_or_words():
    assert inv.exact_key(item_row("A  b"), item_row("a B"))
    assert not inv.exact_key(item_row("A b"), item_row("A b", scope="personal"))
    assert not inv.exact_key(item_row("A b"), item_row("A b", kind="result"))
    assert not inv.exact_key(item_row("A b"), item_row("A c"))
    assert inv.exact_key(item_row("A b", words="the same words"), item_row("A c", words="The  same words"))
    assert not inv.exact_key(item_row("A b", words=""), item_row("A c", words=""))  # no words, no key


def test_merge_problem():
    a, b = item_row("One"), item_row("Two")
    assert inv.merge_problem(a, b, ["x", "y"]) is None
    assert "exact key" in inv.merge_problem(a, b, ["x"])
    assert inv.merge_problem(a, item_row("one"), []) is None
    assert "scope" in inv.merge_problem(a, item_row("One", scope="personal"), ["x", "y"])
    assert "does not exist" in inv.merge_problem(a, None, ["x", "y"])
    assert "no verdict backs" in inv.merge_problem(a, b, ["x", "y"], checked_by=["x", "z"])


def test_scope_covers():
    assert inv.scope_covers(SCOPE, SCOPE) and inv.scope_covers(SCOPE, "personal") and inv.scope_covers("personal", "personal")
    assert not inv.scope_covers("personal", SCOPE) and not inv.scope_covers("project:other", SCOPE)
    assert inv.scope_covers("personal", "session:abc")  # a session source sets no bar


def test_parse_time_reads_offsets_and_assumes_utc():
    assert inv.parse_time("2026-03-02T09:30:00Z") == inv.parse_time("2026-03-02T10:30:00+01:00") == inv.parse_time("2026-03-02T09:30:00")
    assert inv.parse_time("yesterday") is None and inv.parse_time(None) is None and inv.parse_time(5) is None


def test_limits_come_from_the_config_section_and_refuse_bad_values():
    assert Limits.from_config(None) == Limits() and Limits.from_config({}) == Limits()
    lim = Limits.from_config({"maintenance": {"loss_bound": 0.1, "max_ops_per_proposal": 5, "other": 1}})
    assert (lim.loss_bound, lim.max_ops_per_proposal, lim.loss_bound_min) == (0.1, 5, 1)
    for bad in (-1, "5", True):
        with pytest.raises(ValueError):
            Limits.from_config({"maintenance": {"loss_bound": bad}})
    assert Limits().loss_bound == 0.05  # §5.9 (start)


def test_retired_by_names_what_a_run_retires():
    assert inv.retired_by("supersession.applied", dict(old_item="a", new_item="b")) == "a"
    assert inv.retired_by("supersession.applied", dict(old_item="a", new_item="a")) is None  # a new version of the same item
    assert inv.retired_by("link.applied", dict(link_type="same_as", from_id="a")) == "a"
    assert inv.retired_by("link.applied", dict(link_type="supports", from_id="a")) is None
    assert inv.retired_by("item.status_changed", dict(item_id="a", from_status="active", to_status="quarantined")) == "a"
    assert inv.retired_by("item.status_changed", dict(item_id="a", from_status="quarantined", to_status="active")) is None
    assert inv.retired_by("item.created", dict(item_id="a")) is None


# --- check functions on a context ---------------------------------------------------------------------------------


def context(world, ops, **kw):
    proposal = Proposal.build(world.run_id, ops, inputs=kw.pop("inputs", ()))
    return Context(proposal, proposal.ops, MemoryRead(world.memory), HistoryRead(world.history), NOW, **kw)


def test_violations_carry_the_invariant_id_the_reason_and_the_op(world):
    ops = world.yours("m1")
    ops[0].payload["start_char"] += 1
    ops[0].payload["end_char"] += 1
    found = inv.check_i2(context(world, ops))
    assert [(v.invariant, v.op_index) for v in found] == [("I2", 0)] and found[0].reason
    assert isinstance(found[0], Violation) and found[0].ref is None


def test_the_schema_check_can_be_asked_for_i3_or_i15_alone(world):
    ops = world.yours("m1")
    ops[0].payload["speaker"] = "user"
    ops[1].payload["surprise"] = 1
    ctx = context(world, ops)
    assert [(v.invariant, v.op_index) for v in inv.check_i3(ctx)] == [("I3", 0)]
    assert [(v.invariant, v.op_index) for v in inv.check_i15(ctx)] == [("I15", 1)]


def test_a_valid_proposal_has_no_violations_from_any_gate_check(world):
    ctx = context(world, world.adopted("m1"), verdict_families=[CHECKER])
    assert [v for _, check in GATE_CHECKS for v in check(ctx)] == []


def test_the_loss_bound_counts_this_run_before_this_proposal(world):
    world.pad(100, "i")
    retire = lambda n: world.op("item.status_changed", dict(item_id=f"i{n}", from_status="active", to_status="retracted", reason="x"))  # noqa: E731
    world.applied([retire(0), retire(1)])
    bound = inv.loss_bound(context(world, [retire(2), retire(1)]))
    assert bound.before == {"i0", "i1"} and bound.retired == {"i2"} and bound.total == 3
    assert bound.active == 98 + 2 and bound.allowed == 5 and not bound.exceeded


def test_proposal_inputs_and_op_inputs_are_both_checked_for_i7(world):
    ctx = context(world, world.yours("m1"), inputs=["start_note:t1@1"])
    found = inv.check_i7(ctx)
    assert len(found) == 1 and found[0].op_index is None  # the proposal's own input, copied onto its ops, is reported once


def test_i13_reasons_say_the_cap_and_the_count(world):
    ops = [world.op("topic.renamed", dict(topic_id=f"t{n}", old_label="A", label="B", label_fixed=False, reason="x")) for n in range(5)]
    reasons = [v.reason for v in inv.check_i13(context(world, ops))]
    assert reasons == ["a run may change 3 topic labels, this one would 5"]


def test_correction_break_is_none_for_kinds_that_constrain_nothing(world):
    for kind in ("keep", "pin"):
        assert inv.correction_break(dict(kind=kind, target="m1"), "item.status_changed", dict(item_id="m1", from_status="active", to_status="superseded"), MemoryRead(world.memory)) is None


def test_the_evidence_a_proposal_anchors_is_stamped_in_the_context_from_history(world):
    ctx = context(world, world.adopted("m1"))
    mine = ctx.new_evidence["ev-m1-0"]
    assert (mine.speaker, mine.agent, mine.model_family, mine.origin, mine.source_id) == ("assistant", "claude-code", "claude", "assistant_output", "S1")
    assert ctx.claim_families() == {"claude"}
    assert ctx.op_origin(ctx.ops[-1]) == "adopted:claude-code"


def test_history_read_works_from_a_store_or_a_connection(world):
    for source in (world.history, world.conns["history"]):
        h = HistoryRead(source)
        assert h.message("S1:0").text.startswith("Let's keep") and h.message("nope") is None
        assert h.source("S1") == {"kind": "chat", "scope": SCOPE, "project": "energy-dash"} and h.source("nope") is None
        assert h.northstar_marked(h.message("N1:0")) and not h.northstar_marked(h.message("S1:0"))


def test_history_read_without_a_connection_skips_source_lookups(world):
    class OnlyMessages:
        def get_message(self, message_id):
            return world.history.get_message(message_id)

    h = HistoryRead(OnlyMessages())
    assert h.message("S1:1").speaker == "assistant" and h.source("S1") is None


# --- the sweep ----------------------------------------------------------------------------------------------------


def clean(world):
    """A store the gate built: an adopted item, items from your words, a stated goal, a style line, corrections, a merge."""
    world.applied(world.adopted("m1"))
    world.applied(world.yours("m2"))
    world.applied(world.goal("g1"))
    world.applied(world.yours("m3", line="Hourly averages are enough for monthly charts"))
    world.applied(world.yours("m4", line="Hourly averages are enough for monthly charts"))
    world.applied([world.op("link.applied", dict(link_id="l1", from_id="m4", to_id="m3", link_type="same_as", reason="same line", stated_by="northstar"))])
    world.applied([
        world.evidence("ev-s", "st1", "S1:6", "Always put the totals first", "support", "style_line"),
        world.op("style.recorded", dict(style_id="st1", line="Totals first", scope="personal", basis="stated_default", evidence_ids=["ev-s"])),
    ])  # fmt: skip
    world.applied_user([world.op("correction.applied", dict(correction_id="co1", kind="rename", target="t1", via="click", at=SAID, constraint={"label_fixed": True}), actor="user")])
    world.applied_user([
        world.evidence("ev-c", "co2", "S1:6", "Keep the weekly report short", "support", "correction", actor="user"),
        world.op("correction.applied", dict(correction_id="co2", kind="pin", target="m2", via="typed", at=SAID, constraint={}, evidence_id="ev-c"), actor="user"),
    ])  # fmt: skip
    world.applied([world.op("stance.recorded", dict(item_id="m1", stance="adopted", evidence_ids=["ev-m1-1"]))])
    world.applied_user([
        world.op("correction.applied", dict(correction_id="co3", kind="keep", target="m2", via="click", at=SAID, constraint={}), actor="user"),
        world.op("item.value_changed", dict(item_id="m2", from_value="forming", to_value="kept", signal="your_keep"), actor="user"),
    ])  # fmt: skip
    return world


def sweep(world, *, history=True):
    stores = {"memory": world.conns["memory"]}
    if history:
        stores["history"] = world.conns["history"]
    return inv.sweep(stores)


def ids(violations):
    return {v.invariant for v in violations}


def test_a_store_the_gate_built_is_clean(varied):
    assert sweep(clean(varied)) == []


def test_a_store_the_gate_built_is_clean_without_history_too(varied):
    assert sweep(clean(varied), history=False) == []


def test_the_sweep_changes_nothing(varied):
    world = varied
    clean(world)
    before = {name: list(conn.iterdump()) for name, conn in world.conns.items() if name in ("memory", "history")}
    changes = world.memory.total_changes
    sweep(world)
    assert world.memory.total_changes == changes
    assert {name: list(conn.iterdump()) for name, conn in world.conns.items() if name in ("memory", "history")} == before
    assert not world.memory.in_transaction


def test_an_empty_store_is_clean(world):
    assert sweep(world) == []


def drop(world, *triggers):
    for name in triggers:
        world.memory.execute(f"DROP TRIGGER {name}")


def raw(world, sql, *args):
    world.memory.execute(sql, args)


def damage_missing_evidence(w):
    drop(w, "evidence_no_delete")
    raw(w, "DELETE FROM evidence WHERE id = 'ev-m2-0'")


def damage_unknown_message(w):
    drop(w, "evidence_frozen")
    raw(w, "UPDATE evidence SET message_id = 'S9:9' WHERE id = 'ev-m2-0'")


def damage_quote(w):
    drop(w, "evidence_frozen")
    raw(w, "UPDATE evidence SET quote = 'another quote entirely' WHERE id = 'ev-m2-0'")


def damage_speaker(w):
    drop(w, "evidence_frozen")
    raw(w, "UPDATE evidence SET speaker = 'user' WHERE id = 'ev-m1-0'")


def damage_adoption(w):
    drop(w, "evidence_frozen")
    raw(w, "UPDATE evidence SET role = 'adoption' WHERE id = 'ev-m1-0'")


def damage_adoption_gone(w):
    drop(w, "evidence_no_delete")
    raw(w, "DELETE FROM evidence WHERE id = 'ev-m1-1'")


def damage_origin(w):
    raw(w, "UPDATE item SET origin = 'yours' WHERE id = 'm1'")


def damage_goal(w):
    raw(w, "UPDATE item SET origin = 'adopted:claude-code' WHERE id = 'g1'")


def damage_style(w):
    drop(w, "evidence_no_delete")
    raw(w, "DELETE FROM evidence WHERE id = 'ev-s'")


def damage_typed_correction(w):
    drop(w, "evidence_frozen")
    raw(w, "UPDATE evidence SET origin = 'pasted' WHERE id = 'ev-c'")


def damage_trigger(w):
    drop(w, "event_no_update")


def damage_input(w):
    drop(w, "event_no_update")
    raw(w, """UPDATE event SET inputs = '["change_log:run1@1"]' WHERE seq = 1""")


def damage_echo(w):
    drop(w, "evidence_frozen")
    raw(w, "UPDATE evidence SET lineage = 'northstar_echo' WHERE subject_id = 'm2'")


def damage_merge(w):
    raw(w, "INSERT INTO link (id, from_id, to_id, type, reason, stated_by, status, created_seq, seq_from) VALUES ('lx', 'm2', 'm3', 'same_as', 'x', 'northstar', 'applied', 99, 99)")


def damage_proposal_gap(w):
    drop(w, "event_no_delete", "event_subject_no_delete")
    raw(w, "DELETE FROM event_subject WHERE seq = 2")
    raw(w, "DELETE FROM event WHERE seq = 2")


def damage_payload(w):
    drop(w, "event_no_update")
    raw(w, """UPDATE event SET payload = '{"surprise": 1}' WHERE seq = 3""")


def damage_time(w):
    raw(w, "UPDATE item SET said_at = '2027-01-01T00:00:00Z' WHERE id = 'm2'")


def damage_scope(w):
    raw(w, "UPDATE item SET scope = 'personal' WHERE id = 'm2'")


def damage_correction(w):
    raw(
        w,
        "INSERT INTO event (id, type, schema_version, subjects, payload, actor, config_version, recorded_at) VALUES (?, 'topic.renamed', 1, '[\"t1\"]', ?, 'code:weekly', 'c1', ?)",
        "01ARZ3NDEKTSV4RRFFQ69G5FAV",
        '{"topic_id": "t1", "old_label": "A", "label": "B", "label_fixed": false, "reason": "x"}',
        NOW,
    )


def damage_northstar_message(w):
    w.history.append_message(Message(id="N1:1", source_id="N1", ordinal=1, speaker="assistant", text="a hidden run", origin="assistant_output"))


def damage_northstar_evidence(w):
    raw(
        w,
        "INSERT INTO evidence (id, subject_kind, subject_id, message_id, start_char, end_char, quote, role, speaker, agent, model_family, origin, lineage, created_seq, seq_from)"
        " VALUES ('ev-n', 'item', 'm2', 'N1:0', 0, 7, 'Earlier', 'support', 'northstar', NULL, NULL, 'northstar_injected', 'primary', 99, 99)",
    )


def damage_history_trigger(w):
    w.conns["history"].execute("DROP TRIGGER message_no_update")


DAMAGE = {
    "an item with no evidence": (damage_missing_evidence, {"I1"}),
    "evidence for a message that is not there": (damage_unknown_message, {"I1"}),
    "a quote that is not the message's text": (damage_quote, {"I2"}),
    "a speaker changed after capture": (damage_speaker, {"I3", "I20"}),
    "an adoption span that is the AI's own words": (damage_adoption, {"I4"}),
    "an origin changed after capture": (damage_origin, {"I20"}),
    "an adopted item whose adoption span is gone": (damage_adoption_gone, {"I4"}),
    "a goal that is not yours": (damage_goal, {"I5"}),
    "a style line with no evidence": (damage_style, {"I5"}),
    "a typed correction on words that were pasted": (damage_typed_correction, {"I3", "I5"}),
    "an append-only trigger removed": (damage_trigger, {"I6"}),
    "a derived input in the log": (damage_input, {"I7"}),
    "an item resting on echoes": (damage_echo, {"I11"}),
    "a merge with no key and no families": (damage_merge, {"I12"}),
    "a proposal with a missing event": (damage_proposal_gap, {"I14"}),
    "an event that no longer matches its schema": (damage_payload, {"I15"}),
    "an item said after it was recorded": (damage_time, {"I16"}),
    "an item wider than where it was learned": (damage_scope, {"I17"}),
    "an automated change after a correction": (damage_correction, {"I21"}),
    "a message in a Northstar output source that is not marked": (damage_northstar_message, {"I24"}),
    "evidence on Northstar's own text": (damage_northstar_evidence, {"I24"}),
    "a history trigger removed": (damage_history_trigger, {"I6"}),
}


@pytest.mark.parametrize("name", list(DAMAGE))
def test_the_sweep_finds_each_kind_of_damage(world, name):
    damage, expected = DAMAGE[name]
    clean(world)
    damage(world)
    found = sweep(world)
    assert expected <= ids(found), (name, found)
    assert all(v.reason and v.invariant in INVARIANTS for v in found)
    assert all(v.ref for v in found if v.invariant != "I14") or name == "a proposal with a missing event"


def test_every_invariant_the_sweep_enforces_has_a_damage_case():
    swept = {i for i, how in INVARIANTS.items() if "sweep" in how}
    covered = {i for _, expected in DAMAGE.values() for i in expected}
    assert swept <= covered, swept - covered


def test_the_sweep_says_which_row_is_wrong(world):
    clean(world)
    damage_time(world)
    found = [v for v in sweep(world) if v.invariant == "I16"]
    assert found and {v.ref for v in found} == {"item:m2"}


def test_a_purged_item_is_not_asked_for_evidence(world):
    clean(world)
    raw(world, "UPDATE item SET status = 'purged' WHERE id = 'm2'")
    drop(world, "evidence_no_delete")
    raw(world, "DELETE FROM evidence WHERE subject_id = 'm2'")
    assert [v for v in sweep(world) if v.invariant != "I6"] == []  # (the dropped trigger is I6's to report)


def test_a_store_that_is_not_there_to_sweep_is_an_error(world):
    with pytest.raises(KeyError):
        inv.sweep({})


def test_the_sweep_finds_an_automated_rollback_of_your_correction(world):
    world.applied(world.yours("m1"))
    op = world.op(
        "correction.applied",
        dict(correction_id="co-1", kind="not_what_i_think", target="m1", via="click", params={}, constraint={"rule": "x"}, at=SAID),
        actor="user",
    )
    assert world.apply_user([op]).status == "applied"
    assert inv.sweep(world.conns | {"history": world.history.conn}) == []
    batch = world.op("compensation.batch", dict(batch_id="b1", reason="undo", compensated_event_ids=[op.id]))
    # the gate refuses it, so write it as damage would have left it
    with db.transaction(world.memory):
        world.memory.execute(
            "INSERT INTO event (id, type, schema_version, subjects, payload, actor, run_id, config_version, recorded_at, inputs)"
            " VALUES (?, 'compensation.batch', 1, '[\"b1\"]', ?, 'model:x@1#abc', NULL, 'c', ?, '[]')",
            (batch.id, json.dumps(batch.payload), NOW),
        )
    found_ids = {(v.invariant, v.ref) for v in inv.sweep(world.conns | {"history": world.history.conn})}
    assert ("I21", f"event:{batch.id}") in found_ids
