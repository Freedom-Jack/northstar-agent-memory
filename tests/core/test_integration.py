"""The core end to end, on invented data (MEMORY-ARCHITECTURE §5.9, §7): a chat in history, an item adopted from an AI
through the write gate, projected, read back as of a seq, replayed to an identical hash, and swept clean. Broken twins
of the proposal are refused and change nothing. Nothing here reads real chats or the real data root."""

from __future__ import annotations

import copy

import pytest

from northstar_agent_memory.core import db, ports, replay
from northstar_agent_memory.core.gate import UserAuthority, WriteGate
from northstar_agent_memory.core.history import SQLiteHistoryStore
from northstar_agent_memory.core.invariants import sweep
from northstar_agent_memory.core.projector import Projector
from northstar_agent_memory.core.reader import SQLiteMemoryReader
from northstar_agent_memory.core.runs import SQLiteRunStore

from . import scenario as sc

NOW = "2026-04-06T12:00:00.000Z"


class Core:
    """Every store opened under one root, a gate with the real projector, and a reader."""

    def __init__(self, root):
        self.conns = {name: db.open_store(name, root) for name in db.STORES}
        self.history = SQLiteHistoryStore(root)
        self.runs = SQLiteRunStore(self.conns["runs"])
        self.run_id = None
        self.gate = sc.Recorded(
            WriteGate(self.conns["memory"], self.history, Projector(), runs=self.runs, config={}, clock=lambda: NOW), self.runs
        )
        self.reader = SQLiteMemoryReader(self.conns["memory"])

    @property
    def memory(self):
        return self.conns["memory"]

    def stores(self):
        return {"memory": self.memory, "history": self.history.conn}

    def count(self, table: str) -> int:
        return self.memory.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def close(self):
        self.history.close()
        for conn in self.conns.values():
            conn.close()


@pytest.fixture
def core(store_root):
    c = Core(store_root)
    sc.load_history(c.history)
    c.run_id = sc.start_run(c.runs)
    yield c
    c.close()


def fingerprint(c: Core) -> tuple:
    """Everything a refused proposal must leave alone."""
    return (c.count("event"), c.count("item"), c.count("evidence"), c.count("event_subject"), replay.canonical_hash(c.memory, include_history=True))


# --- the chain ---------------------------------------------------------------------------------------------------


def test_an_adopted_item_goes_from_history_to_memory_and_back(core):
    chat = core.history.get_source(sc.SOURCE_ID)
    assert [m.speaker for m in chat.messages] == ["user", "assistant", "user", "user"]

    result = core.gate.apply(sc.proposal(core.run_id, sc.adopted_ops("m1")))
    assert result.status == "applied" and len(result.applied_seqs) == 3

    item = core.reader.get_item("m1")
    assert item["origin"] == "adopted:claude-code" and item["check_status"] == "unchecked"
    assert item["status"] == "active" and item["version"] == 1 and item["scope"] == sc.SCOPE

    evidence = {e["role"]: e for e in core.reader.evidence_for("m1")}
    assert set(evidence) == {"primary", "adoption"}
    # who said it comes from history, never from the proposer (I3)
    assert (evidence["primary"]["speaker"], evidence["primary"]["model_family"]) == ("assistant", sc.WORK_FAMILY)
    assert (evidence["adoption"]["speaker"], evidence["adoption"]["origin"]) == ("user", "typed")
    # the quotes are exact spans of the stored messages (I1, I2)
    for row in evidence.values():
        stored = core.history.get_message(row["message_id"])
        assert stored.message.text[row["start_char"] : row["end_char"]] == row["quote"]

    stamped = core.reader.events_since(0)
    assert [e.type for e in stamped] == ["evidence.anchored", "evidence.anchored", "item.created"]
    assert stamped[-1].payload["origin"] == "adopted:claude-code"  # the log carries the origin, so replay needs no history
    assert [e.seq for e in stamped] == result.applied_seqs


def test_a_later_change_reads_back_as_of_the_earlier_seq(core):
    first = core.gate.apply(sc.proposal(core.run_id, sc.adopted_ops("m1")))
    seq_after_first = first.applied_seqs[-1]
    revise = sc.op("item.revised", dict(item_id="m1", base_version=1, line="Raw readings are kept for 30 days", reason="refresh"))
    second = core.gate.apply(sc.proposal(core.run_id, [revise], inputs=["m1@1"]))
    assert second.status == "applied", second.rejections

    now = core.reader.get_item("m1")
    then = core.reader.get_item("m1", as_of_seq=seq_after_first)
    assert now["version"] == 2 and now["line"].endswith("30 days")
    assert then["version"] == 1 and then["line"].endswith("daily averages")
    assert core.reader.get_item("m1", as_of_seq=seq_after_first - 1) is None  # before the item existed
    assert [v["version"] for v in core.reader.item_versions("m1")] == [1, 2]
    assert core.reader.get_item_version("m1", 1)["line"] == then["line"]
    assert core.reader.changed_since(seq_after_first) == ["m1"]
    assert core.reader.watermark() == second.applied_seqs[-1]


def test_a_replay_of_the_log_gives_the_identical_hash(core):
    core.gate.apply(sc.proposal(core.run_id, sc.adopted_ops("m1")))
    core.gate.apply(sc.proposal(core.run_id, sc.yours_ops("m2")))
    revise = sc.op("item.revised", dict(item_id="m1", base_version=1, line="Raw readings are kept for 30 days", reason="refresh"))
    core.gate.apply(sc.proposal(core.run_id, [revise], inputs=["m1@1"]))

    report = replay.verify_replay(core.memory)
    assert report.ok and not report.mismatched_tables and report.live_hash == report.replay_hash
    rebuilt = replay.rebuild_from(core.memory)
    try:
        assert replay.canonical_hash(rebuilt, include_history=True) == replay.canonical_hash(core.memory, include_history=True)
    finally:
        rebuilt.close()


def test_the_sweep_finds_no_violation_after_a_run(core):
    assert sweep(core.stores()) == []  # empty stores are sound
    core.gate.apply(sc.proposal(core.run_id, sc.adopted_ops("m1")))
    core.gate.apply(sc.proposal(core.run_id, sc.yours_ops("m2")))
    before = fingerprint(core)
    assert sweep(core.stores()) == []
    assert fingerprint(core) == before  # the sweep changes nothing


def test_applying_the_same_proposal_again_is_a_duplicate(core):
    made = sc.proposal(core.run_id, sc.adopted_ops("m1"))
    first = core.gate.apply(made)
    before = fingerprint(core)
    again = core.gate.apply(made)
    assert again.status == "duplicate" and again.ok and again.applied_seqs == first.applied_seqs
    assert fingerprint(core) == before


def test_the_gate_leaves_the_callers_proposal_unstamped(core):
    made = sc.proposal(core.run_id, sc.adopted_ops("m1"))
    original = copy.deepcopy(made.ops)
    core.gate.apply(made)
    assert made.ops == original


def test_the_run_store_records_what_the_gate_applied(core):
    made = sc.record(core.runs, sc.proposal(core.run_id, sc.adopted_ops("m1")))
    result = core.gate.apply(made)
    core.runs.set_proposal_state(made.proposal_id, "applied")
    core.runs.log_change(core.run_id, "adoption", "Added: raw readings are kept for 14 days", [str(s) for s in result.applied_seqs])
    core.runs.finish_run(core.run_id, "applied", watermark_to=core.history.watermark().message_seq)
    assert core.runs.get_proposal(made.proposal_id)["state"] == "applied"
    assert core.runs.get_run(core.run_id)["state"] == "applied"
    assert len(core.runs.read_change_log(core.run_id)) == 1
    # a finished run fences out any later proposal of its own (§5.9 step 2)
    late = core.gate.apply(sc.proposal(core.run_id, sc.yours_ops("m2")))
    assert late.status == "rejected" and {r.invariant for r in late.rejections} == {"fencing"}


# --- broken twins ------------------------------------------------------------------------------------------------


def twin_without_your_adoption():
    ops = sc.adopted_ops("m1")
    del ops[1]  # the adoption span is gone, but the item still says it was adopted
    ops[-1].payload["evidence_ids"] = ["ev-m1-ai"]
    return ops


def twin_with_moved_offsets():
    ops = sc.adopted_ops("m1")
    ops[0].payload["start_char"] += 2
    ops[0].payload["end_char"] += 2
    return ops


def twin_with_a_changed_quote():
    ops = sc.adopted_ops("m1")
    ops[1].payload["quote"] = "keep raw readings for 30 days"
    return ops


def twin_with_a_speaker_you_set():
    ops = sc.adopted_ops("m1")
    ops[1].payload["speaker"] = "user"  # the proposer may not say who spoke (I3)
    return ops


def twin_from_the_wrong_turn():
    ops = sc.adopted_ops("m1")
    ops[1].payload["message_id"] = sc.message_id(3)  # a turn that does not hold the quote
    return ops


@pytest.mark.parametrize(
    "twin, invariants",
    [
        (twin_without_your_adoption, {"I4"}),
        (twin_with_moved_offsets, {"I2"}),
        (twin_with_a_changed_quote, {"I2"}),
        (twin_with_a_speaker_you_set, {"I3"}),
        (twin_from_the_wrong_turn, {"I2"}),
    ],
)
def test_a_broken_twin_is_rejected_and_writes_nothing(core, twin, invariants):
    before = fingerprint(core)
    result = core.gate.apply(sc.proposal(core.run_id, twin()))
    assert result.status == "rejected" and not result.ok and result.applied_seqs == []
    assert invariants <= {r.invariant for r in result.rejections}, result.rejections
    assert fingerprint(core) == before
    assert sweep(core.stores()) == []


def test_without_the_check_its_tier_needs_the_proposal_is_refused(core):
    before = fingerprint(core)
    none = core.gate.apply(sc.proposal(core.run_id, sc.adopted_ops("m1"), verdicts=[]))
    assert none.status == "rejected" and {r.invariant for r in none.rejections} == {"verification"}
    same_family = core.gate.apply(sc.proposal(core.run_id, sc.adopted_ops("m1"), verdicts=[sc.checked(sc.WORK_FAMILY)]))
    assert same_family.status == "rejected"  # the family that did the work may not check it
    failing = core.gate.apply(sc.proposal(core.run_id, sc.adopted_ops("m1"), verdicts=[sc.checked(outcome="fail")]))
    assert failing.status == "rejected"
    assert fingerprint(core) == before


def test_a_stale_input_is_requeued_not_rejected(core):
    core.gate.apply(sc.proposal(core.run_id, sc.adopted_ops("m1")))
    before = fingerprint(core)
    revise = sc.op("item.revised", dict(item_id="m1", base_version=1, line="Another line", reason="refresh"))
    result = core.gate.apply(sc.proposal(core.run_id, [revise], inputs=["m1@7"]))
    assert result.status == "requeued" and not result.ok
    assert fingerprint(core) == before


def test_a_rejected_proposal_can_be_fixed_and_applied(core):
    bad = core.gate.apply(sc.proposal(core.run_id, twin_with_moved_offsets()))
    assert bad.status == "rejected"
    good = core.gate.apply(sc.proposal(core.run_id, sc.adopted_ops("m1")))
    assert good.status == "applied"
    assert replay.verify_replay(core.memory).ok and sweep(core.stores()) == []


def test_the_core_is_a_set_of_ports(core):
    assert isinstance(core.gate, ports.MemoryWriter) and isinstance(core.reader, ports.MemoryReader)
    assert isinstance(core.history, ports.HistoryStore) and isinstance(core.runs, ports.RunStore)
    assert isinstance(Projector(), ports.Projector)


def test_a_proposal_saved_in_runs_db_and_loaded_again_applies_the_same(core):
    made = sc.record(core.runs, sc.proposal(core.run_id, sc.adopted_ops("m1")))
    loaded = core.runs.load_proposal(made.proposal_id)
    assert loaded is not None and loaded.proposal_id == made.proposal_id and loaded.risk_tier == made.risk_tier
    result = core.gate.apply(loaded)
    assert result.status == "applied", result.rejections
    assert core.gate.apply(made).status == "duplicate"  # the original has the same run key, so it is the same proposal
    assert sweep(core.stores()) == [] and replay.verify_replay(core.memory).ok


def test_a_purge_you_ask_for_scrubs_memory_and_still_replays_and_sweeps_clean(core):
    core.gate.apply(sc.proposal(core.run_id, sc.adopted_ops("m1")))
    ask = sc.op("correction.applied", dict(correction_id="co1", kind="purge", target="m1", via="click", at=sc.SAID, constraint={}), actor="user")
    purge = sc.op("purge.applied", dict(purge_id="pg1", item_ids=["m1"], requested_at=sc.SAID), actor="user")
    result = core.gate.apply_user(sc.proposal(core.run_id, [ask, purge], verdicts=[], inputs=["m1@1"]), UserAuthority(surface="ui", user_action=True))
    assert result.status == "applied", result.rejections
    assert core.reader.get_item("m1")["status"] == "purged"
    quotes = [e["quote"] for e in core.reader.evidence_for("m1")]
    assert all("14 days" not in q for q in quotes)  # the quotes are scrubbed
    dump = "".join(str(tuple(r)) for t in ("event", "item_history", "evidence", "evidence_history") for r in core.memory.execute(f"SELECT * FROM {t}"))
    assert "daily averages" not in dump and "14 days" not in dump  # no copy of the words is left in memory.db
    assert replay.verify_replay(core.memory).ok
    assert sweep(core.stores()) == []


def test_a_purge_or_rollback_a_model_proposes_is_still_refused(core):
    core.gate.apply(sc.proposal(core.run_id, sc.adopted_ops("m1")))
    before = fingerprint(core)
    purge = sc.op("purge.applied", dict(purge_id="pg1", item_ids=["m1"], requested_at=sc.SAID))  # the work's own actor
    result = core.gate.apply(sc.proposal(core.run_id, [purge], inputs=["m1@1"]))
    assert result.status == "rejected" and "I5" in {r.invariant for r in result.rejections}
    assert fingerprint(core) == before and core.reader.get_item("m1")["status"] == "active"


def test_a_command_you_start_needs_no_model_check_and_a_models_keeps_its_tier():
    from northstar_agent_memory.core.events import risk_tier

    purge = dict(purge_id="pg1", item_ids=["m1"], requested_at=sc.SAID)
    batch = dict(batch_id="b1", reason="you undid a run", compensated_event_ids=["e1"])
    assert risk_tier(sc.op("purge.applied", purge, actor="user")) == "low"
    assert risk_tier(sc.op("compensation.batch", batch, actor="user")) == "low"
    assert risk_tier(sc.op("purge.applied", purge)) == "high"
    assert risk_tier(sc.op("compensation.batch", batch)) == "high"


# --- the package ---------------------------------------------------------------------------------------------------


def test_the_package_exports_what_the_parts_above_use():
    import northstar_agent_memory.core as package

    assert len(package.__all__) == len(set(package.__all__))
    for name in package.__all__:
        assert hasattr(package, name), name
    assert package.STORES == db.STORES and len(package.STORES) == 6
    assert package.SQLiteMemoryReader is SQLiteMemoryReader and package.WriteGate is WriteGate


def test_the_core_makes_no_model_call():
    """Nothing in the core imports the model layer, a vendor SDK or the harness (principle 4: models only propose)."""
    import ast
    from pathlib import Path

    import northstar_agent_memory.core as package

    banned = ("northstar_agent_memory.models", "northstar_agent_memory.eval", "anthropic", "openai", "httpx", "requests", "urllib.request")
    for path in Path(package.__file__).parent.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            for name in names:
                assert not name.startswith(banned), f"{path.name} imports {name}"


def test_working_memory_checks_your_turns_against_history(core, store_root):
    from northstar_agent_memory.core.working import SQLiteWorkingStore, UserWordsRequired

    def is_user_turn(message_id: str) -> bool:
        stored = core.history.get_message(message_id)
        return stored is not None and stored.message.speaker == "user"

    working = SQLiteWorkingStore(core.conns["working"], is_user_turn=is_user_turn)
    tid = working.open_thread("Reports", scope=sc.SCOPE, goal_text="a weekly summary email every Monday", goal_message_id=sc.message_id(3))
    assert working.get_thread(tid)["goal_message_id"] == sc.message_id(3)
    with pytest.raises(UserWordsRequired):  # the AI's turn is not your words
        working.add_live_decision(tid, "decided", "Keep raw readings", "keeping raw readings for 14 days", sc.message_id(1))
    with pytest.raises(UserWordsRequired):  # and a turn that is not in history is no turn
        working.add_live_decision(tid, "decided", "Keep raw readings", "keep raw readings", "LOG1:99")
    working.add_live_decision(tid, "decided", "Keep raw readings", "keep raw readings for 14 days", sc.message_id(2))
    assert [d["message_id"] for d in working.live_decisions(tid)] == [sc.message_id(2)]
