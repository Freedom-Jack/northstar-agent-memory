"""The memory reader: by ID, as of a seq or a time, changed since, subgraph, events (MEMORY-ARCHITECTURE §2.3, §3.2).

Every fixture is invented.
"""

from __future__ import annotations

import json

import pytest

from northstar_agent_memory.core import events
from northstar_agent_memory.core.ports import MemoryReader, Subgraph
from northstar_agent_memory.core.reader import KINDS, SQLiteMemoryReader, normalize_time, row_as_of

from .projection_helpers import Log, evidence_op, seed_item, seed_topic, stamp
from .test_projector import batch, link_fields, place


@pytest.fixture
def log(memory):
    return Log(memory)


@pytest.fixture
def reader(memory):
    return SQLiteMemoryReader(memory)


def revise(log, item_id, line, **fields):
    return log.add("item.revised", {"item_id": item_id, "line": line, "reason": "restated", **fields})


def test_the_reader_meets_the_port(reader):
    assert isinstance(reader, MemoryReader)


# --- watermark and time ---------------------------------------------------------------------------------------------


def test_the_watermark_is_the_highest_seq(log, reader):
    assert reader.watermark() == 0
    seed_item(log, "m1")
    assert reader.watermark() == 2
    log.add("item.value_changed", {"item_id": "m1"})
    assert reader.watermark() == 3


@pytest.mark.parametrize(
    "given, expected",
    [
        ("2026-03-02T09:30:00Z", "2026-03-02T09:30:00.000Z"),
        ("2026-03-02T09:30:00.250Z", "2026-03-02T09:30:00.250Z"),
        ("2026-03-02T10:30:00+01:00", "2026-03-02T09:30:00.000Z"),
        ("2026-03-02T09:30:00", "2026-03-02T09:30:00.000Z"),
        ("2026-03-02", "2026-03-02T23:59:59.999Z"),
    ],
)
def test_times_are_normalized_to_utc_milliseconds(given, expected):
    assert normalize_time(given) == expected


def test_seq_at_finds_the_last_event_at_or_before_a_time(log, reader):
    seed_item(log, "m1")  # seq 1, 2 at minutes 1, 2
    revise(log, "m1", "again")  # seq 3 at minute 3
    assert reader.seq_at("2026-03-02T09:30:00Z") == 0
    assert reader.seq_at(stamp(1)) == 1
    assert reader.seq_at("2026-03-02T09:32:30Z") == 2
    assert reader.seq_at(stamp(3)) == 3
    assert reader.seq_at("2030-01-01") == 3
    assert reader.seq_at("2026-03-02") == 3


# --- items, as of ---------------------------------------------------------------------------------------------------


def test_get_item_reads_now_and_earlier_states(log, reader):
    seed_item(log, "m5", kind="plan")  # seq 2 creates it
    revise(log, "m5", "Second", time_bound=True)  # seq 3
    revise(log, "m5", "Third")  # seq 4
    log.add("item.value_changed", {"item_id": "m5"})  # seq 5
    assert reader.get_item("m5")["line"] == "Third"
    assert reader.get_item("m5", as_of_seq=5)["value"] == "kept"
    assert reader.get_item("m5", as_of_seq=4)["value"] == "forming" and reader.get_item("m5", as_of_seq=4)["line"] == "Third"
    assert reader.get_item("m5", as_of_seq=3)["line"] == "Second" and reader.get_item("m5", as_of_seq=3)["version"] == 2
    assert reader.get_item("m5", as_of_seq=2)["line"] == "Line of m5" and reader.get_item("m5", as_of_seq=2)["version"] == 1
    assert reader.get_item("m5", as_of_seq=1) is None
    assert reader.get_item("m5", as_of_seq=0) is None


def test_get_item_as_of_a_time(log, reader):
    seed_item(log, "m5")
    revise(log, "m5", "Second")
    assert reader.get_item("m5", as_of=stamp(2))["line"] == "Line of m5"
    assert reader.get_item("m5", as_of=stamp(3))["line"] == "Second"
    assert reader.get_item("m5", as_of="2026-03-02T09:31:00Z") is None


def test_get_item_refuses_two_ways_to_say_when(reader):
    with pytest.raises(ValueError):
        reader.get_item("m1", as_of_seq=1, as_of="2026-03-02")


def test_an_unknown_item_is_none(reader):
    assert reader.get_item("nope") is None and reader.get_item("nope", as_of_seq=3) is None


def test_a_row_from_history_has_the_shape_of_a_current_row(log, reader):
    seed_item(log, "m5")
    revise(log, "m5", "Second")
    assert set(reader.get_item("m5", as_of_seq=2)) == set(reader.get_item("m5"))


def test_a_purged_item_reads_as_a_stub_at_every_seq(log, reader):
    seed_item(log, "m3", your_words="SQLite please")
    revise(log, "m3", "Second wording")
    log.add("purge.applied", {"item_ids": ["m3"], "requested_at": "2026-04-01T09:00:00Z"})
    assert reader.get_item("m3")["status"] == "purged"
    for seq in (2, 3):
        old = reader.get_item("m3", as_of_seq=seq)
        assert old["line"] == "removed at your request on 2026-04-01" and old["your_words"] == ""


def test_a_removed_row_is_gone_after_its_removal_and_there_before(log, reader):
    created = seed_item(log, "m1")
    b = batch(log, *created)
    assert reader.get_item("m1") is None
    assert reader.get_item("m1", as_of_seq=created[1].seq)["id"] == "m1"
    assert reader.get_item("m1", as_of_seq=b.seq) is None
    assert reader.get("evidence", "ev-m1", as_of=created[0].seq)["quote"] == "Store readings in SQLite"


def test_versions_are_kept_and_readable(log, reader):
    seed_item(log, "m5", kind="plan")
    revise(log, "m5", "Second")
    revise(log, "m5", "Third")
    log.add("item.value_changed", {"item_id": "m5"})
    assert [v["line"] for v in reader.item_versions("m5")] == ["Line of m5", "Second", "Third"]
    assert reader.item_versions("m5")[1]["version"] == 2
    assert reader.get_item_version("m5", 1)["line"] == "Line of m5"
    assert reader.get_item_version("m5", 3)["value"] == "kept"
    assert reader.get_item_version("m5", 4) is None and reader.get_item_version("nope", 1) is None
    assert reader.item_versions("nope") == []


def test_a_version_stored_twice_reads_as_its_last_state(log, reader):
    seed_item(log, "m5")  # version 1
    log.add("item.value_changed", {"item_id": "m5"})  # still version 1, later state
    revise(log, "m5", "Second")
    assert reader.get_item_version("m5", 1)["value"] == "kept"
    assert [v["version"] for v in reader.item_versions("m5")] == [1, 2]


def test_evidence_for_a_subject(log, reader):
    log.run(evidence_op("e1", "m1"), evidence_op("e2", "m1"), evidence_op("e3", "m2"), evidence_op("e4", "st1", subject_kind="style_line"))
    assert [e["id"] for e in reader.evidence_for("m1")] == ["e1", "e2"]
    assert [e["id"] for e in reader.evidence_for("st1")] == ["e4"]
    assert reader.evidence_for("nope") == []


# --- get by kind ----------------------------------------------------------------------------------------------------


def test_get_reads_every_kind_of_row(log, reader):
    seed_item(log, "m1")
    seed_item(log, "m2")
    log.add("link.applied", link_fields())
    stance = log.add("stance.recorded", {"item_id": "m1", "evidence_ids": ["ev-m1"]})
    log.add("work.registered")
    log.add("style.recorded")
    log.add("correction.applied")
    log.add("scope.hold_changed")
    seed_topic(log, "t5")
    place(log, "p1", "m1", "t5")
    log.add("supersession.applied", dict(supersession_id="s1", old_item="m1", old_version=1, new_item="m2", reason="your_later_statement"))
    log.add("conflict.opened", dict(conflict_id="c1", side_a_item="m1", side_a_version=1, side_b_item="m2", side_b_version=1,
                                    kind="across_contexts", state="both_stand"))  # fmt: skip
    found = {
        "item": "m1", "evidence": "ev-m1", "link": "l1", "supersession": "s1", "conflict": "c1", "work": "w1",
        "style_line": "st1", "correction": "co1", "scope": "project:energy-dash", "topic": "t5", "placement": "p1",
        "stance": stance.id,
    }  # fmt: skip
    assert set(found) == set(KINDS)
    for kind, row_id in found.items():
        assert reader.get(kind, row_id)["id"] == row_id, kind
        assert reader.get(kind, "nope") is None
        assert reader.get(kind, row_id, as_of=0) is None, kind


def test_get_an_unknown_kind_is_refused(reader):
    with pytest.raises(ValueError, match="unknown kind"):
        reader.get("topic_history", "t1")
    with pytest.raises(ValueError):
        row_as_of(reader.conn, "bogus", "x", 1)


def test_get_accepts_a_seq_or_a_time(log, reader):
    seed_topic(log, "t1")  # seq 1
    log.add("topic.renamed")  # seq 2
    assert reader.get("topic", "t1", as_of=1)["label"] == "Topic t1"
    assert reader.get("topic", "t1", as_of=stamp(1))["label"] == "Topic t1"
    assert reader.get("topic", "t1", as_of=2)["label"] == "Energy dashboard"
    assert reader.get("topic", "t1")["label"] == "Energy dashboard"


def test_get_a_link_as_of_each_of_its_states(log, reader):
    seed_item(log, "m1")
    seed_item(log, "m2")
    log.add("link.proposed", link_fields())  # 5
    log.add("link.applied", link_fields())  # 6
    log.add("link.confirmed", {"link_id": "l1", "via": "click"})  # 7
    assert [reader.get("link", "l1", as_of=s)["status"] if reader.get("link", "l1", as_of=s) else None for s in (4, 5, 6, 7)] == [
        None, "proposed", "applied", "confirmed"]


# --- events ---------------------------------------------------------------------------------------------------------


def test_events_since_come_back_stamped_and_in_order(log, reader):
    seed_item(log, "m1")
    log.add("item.value_changed", {"item_id": "m1"})
    revise(log, "m1", "Second")
    got = reader.events_since(0)
    assert [e.seq for e in got] == [1, 2, 3, 4] and [e.type for e in got][-1] == "item.revised"
    assert all(e.recorded_at and e.id for e in got)
    assert [e.seq for e in reader.events_since(2)] == [3, 4]
    assert [e.seq for e in reader.events_since(0, limit=2)] == [1, 2]
    assert [e.type for e in reader.events_since(0, types=["item.value_changed", "item.revised"])] == ["item.value_changed", "item.revised"]
    assert reader.events_since(4) == []


def test_a_stored_event_equals_the_one_appended(log, reader):
    sent = seed_item(log, "m1", why="because")[1]
    (back,) = reader.events_since(1, limit=1)
    assert back.payload == sent.payload and back.subjects == sent.subjects == ["m1"]
    assert (back.id, back.type, back.actor, back.config_version, back.recorded_at) == (sent.id, sent.type, sent.actor, sent.config_version, sent.recorded_at)
    assert events.validate(back) is back
    assert reader.get_event(sent.id) == back and reader.get_event("nope") is None


def test_events_keep_their_proposal_keys_and_inputs(log, reader):
    seed_item(log, "m1")
    done = log.add("item.value_changed", {"item_id": "m1"}, run_id="r2", proposal_id="pr2", index_in_proposal=0, inputs=["m1@1"])
    stored = reader.get_event(done.id)
    assert (stored.run_id, stored.proposal_id, stored.index_in_proposal, stored.inputs) == ("r2", "pr2", 0, ["m1@1"])


def test_a_compensating_event_keeps_what_it_compensates(log, reader):
    seed_item(log, "m6")
    seed_item(log, "m7")
    sup = log.add("supersession.applied", dict(supersession_id="s1", old_item="m6", old_version=1, new_item="m7", reason="your_later_statement"))
    undo = log.add("supersession.undone", {"supersession_id": "s1", "reason": "audit disagreed"}, compensates=sup.id)
    assert reader.get_event(undo.id).compensates == sup.id and reader.get_event(sup.id).compensates is None


# --- changed since ---------------------------------------------------------------------------------------------------


def test_changed_since_names_the_items_touched_after_a_seq(log, reader):
    seed_item(log, "m1")  # 1,2
    seed_item(log, "m2")  # 3,4
    seed_item(log, "m3")  # 5,6
    assert reader.changed_since(0) == ["m1", "m2", "m3"]
    assert reader.changed_since(4) == ["m3"]
    log.add("item.value_changed", {"item_id": "m1"})  # 7
    assert reader.changed_since(4) == ["m3", "m1"]
    assert reader.changed_since(7) == []


def test_changed_since_follows_links_conflicts_and_evidence_to_their_items(log, reader):
    seed_item(log, "m1")
    seed_item(log, "m2")
    seed_item(log, "m3")
    log.add("link.applied", link_fields("l1", "m1", "m2"))
    mark = reader.watermark()
    log.add("link.confirmed", {"link_id": "l1", "via": "click"})
    assert reader.changed_since(mark) == ["m1", "m2"]
    mark = reader.watermark()
    log.add("conflict.opened", dict(conflict_id="c1", side_a_item="m2", side_a_version=1, side_b_item="m3", side_b_version=1,
                                    kind="across_contexts", state="both_stand"))  # fmt: skip
    log.add("conflict.reopened", {"conflict_id": "c1", "reason": "x"})
    assert reader.changed_since(mark) == ["m2", "m3"]
    mark = reader.watermark()
    log.add("evidence.anchored", dict(evidence_id="e9", subject_kind="item", subject_id="m1", message_id="A9", start_char=0, end_char=5,
                                      quote="hello", role="support", speaker="user", agent=None, model_family=None, origin="typed", context="energy-dash"))  # fmt: skip
    assert reader.changed_since(mark) == ["m1"]


def test_changed_since_leaves_out_topics_and_other_things_that_are_not_items(log, reader):
    seed_item(log, "m1")
    mark = reader.watermark()
    seed_topic(log, "t1", anchor_id="goal-anchor")
    log.add("work.registered")
    assert reader.changed_since(mark) == []
    place_mark = reader.watermark()
    place(log, "p1", "m1", "t1")
    assert reader.changed_since(place_mark) == ["m1"]


def test_changed_since_counts_what_a_compensation_batch_undid(log, reader):
    seed_item(log, "m1")
    seed_item(log, "m2")
    rev = revise(log, "m2", "Second")
    log.add("item.value_changed", {"item_id": "m1"})
    mark = reader.watermark()
    batch(log, rev)
    assert reader.changed_since(mark) == ["m2"]


def test_changed_since_still_names_an_item_a_rollback_removed(log, reader):
    created = seed_item(log, "m1")
    mark = reader.watermark()
    batch(log, *created)
    assert reader.changed_since(mark) == ["m1"]


# --- subgraph --------------------------------------------------------------------------------------------------------


@pytest.fixture
def chain(log):
    """m1 - m2 - m3 - m4 by applied links, m5 by a proposed link to m1, and m1 used_in work w1."""
    for item_id in ("m1", "m2", "m3", "m4", "m5", "m6"):
        seed_item(log, item_id)
    log.add("link.applied", link_fields("l12", "m1", "m2"))
    log.add("link.applied", link_fields("l23", "m3", "m2", link_type="refines"))
    log.add("link.applied", link_fields("l34", "m3", "m4"))
    log.add("link.confirmed", {"link_id": "l34", "via": "click"})
    log.add("link.proposed", link_fields("l15", "m1", "m5"))
    log.add("link.applied", dict(link_id="lw", from_id="m1", to_id="w1", link_type="used_in", reason="same session", stated_by="construction",
                                 to_kind="work", checked_by=[]))  # fmt: skip
    return log


def ids(graph: Subgraph):
    return sorted(graph.items), [link["id"] for link in graph.links]


def test_depth_zero_is_the_items_asked_for(chain, reader):
    graph = reader.subgraph(["m1"], depth=0)
    assert ids(graph) == (["m1"], ["lw"])


def test_depth_one_is_the_items_a_link_away_in_either_direction(chain, reader):
    assert ids(reader.subgraph(["m2"], depth=1)) == (["m1", "m2", "m3"], ["l12", "l23", "lw"])
    assert ids(reader.subgraph(["m1"])) == (["m1", "m2"], ["l12", "lw"])


def test_depth_two_and_more_reach_further(chain, reader):
    assert ids(reader.subgraph(["m1"], depth=2)) == (["m1", "m2", "m3"], ["l12", "l23", "lw"])
    assert ids(reader.subgraph(["m1"], depth=3)) == (["m1", "m2", "m3", "m4"], ["l12", "l23", "l34", "lw"])
    assert ids(reader.subgraph(["m1"], depth=9)) == ids(reader.subgraph(["m1"], depth=3))


def test_only_links_of_the_asked_statuses_count(chain, reader):
    assert ids(reader.subgraph(["m1"], depth=1, statuses=("proposed",))) == (["m1", "m5"], ["l15"])
    assert ids(reader.subgraph(["m3"], depth=1, statuses=("confirmed",))) == (["m3", "m4"], ["l34"])
    assert ids(reader.subgraph(["m1"], depth=2, statuses=("applied", "confirmed", "proposed")))[0] == ["m1", "m2", "m3", "m5"]


def test_a_retracted_link_is_not_followed(chain, reader):
    chain.add("link.retracted", {"link_id": "l12", "reason": "gone"})
    assert ids(reader.subgraph(["m1"], depth=2)) == (["m1"], ["lw"])


def test_the_links_returned_have_both_ends_in_the_graph_or_a_work_end(chain, reader):
    graph = reader.subgraph(["m2", "m3"], depth=0)
    assert ids(graph) == (["m2", "m3"], ["l23"])
    for link in graph.links:
        assert link["from_id"] in graph.items and (link["to_id"] in graph.items or link["to_kind"] == "work")


def test_unknown_ids_are_ignored_and_rows_are_current_item_rows(chain, reader):
    graph = reader.subgraph(["nope", "m6"], depth=2)
    assert ids(graph) == (["m6"], [])
    assert reader.subgraph([], depth=2).items == {}
    assert reader.subgraph(["m1"]).items["m1"] == reader.get_item("m1")


def test_a_merged_item_is_reached_like_any_other(chain, reader):
    chain.add("link.applied", link_fields("l46", "m6", "m4", "same_as"))
    graph = reader.subgraph(["m4"], depth=1)
    assert sorted(graph.items) == ["m3", "m4", "m6"] and graph.items["m6"]["merged_into"] == "m4"


def test_a_link_json_column_is_stored_text(chain, reader):
    link = reader.subgraph(["m1"]).links[0]
    assert json.loads(link["checked_by"]) == []
