"""One contract test suite per port (MEMORY-ARCHITECTURE §3.2): every adapter of a port must pass the same tests.

An adapter is a class registered in ADAPTERS. It opens each port and says how to seed the two stores no port
writes to (index.db and overview.db are written by builders that come later), and how to read the marks the
overview port only writes. SQLite is the only adapter now; a Postgres adapter joins by adding one class here.
The tests call only the port's methods, plus the read methods the adapters share beyond the ports (named below).
Every fixture is invented (Robin's meter logger, see scenario.py).
"""

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from northstar_agent_memory.core import db, ports
from northstar_agent_memory.core.gate import WriteGate
from northstar_agent_memory.core.history import SQLiteHistoryStore
from northstar_agent_memory.core.ids import content_hash, utc_now
from northstar_agent_memory.core.index_store import SQLiteIndexStore
from northstar_agent_memory.core.overview_store import SQLiteOverviewStore
from northstar_agent_memory.core.ports import ModelCall, SearchQuery, Verdict, WorkEvent
from northstar_agent_memory.core.projector import Projector
from northstar_agent_memory.core.reader import SQLiteMemoryReader
from northstar_agent_memory.core.runs import SQLiteRunStore
from northstar_agent_memory.core.working import SQLiteWorkingStore, fingerprints
from northstar_agent_memory.transcript import Message, Source

from . import scenario as sc

# --- adapters ------------------------------------------------------------------------------------------------------


class SQLiteAdapter:
    """The SQLite adapter of every port, under a throwaway root."""

    name = "sqlite"

    def __init__(self, root: Path):
        self.root = root
        self.closers: list[Any] = []

    def _keep(self, store):
        self.closers.append(store)
        return store

    def history(self) -> ports.HistoryStore:
        return self._keep(SQLiteHistoryStore(self.root))

    def runs(self) -> ports.RunStore:
        return self._keep(SQLiteRunStore.open(self.root))

    def working(self) -> ports.WorkingStore:
        return self._keep(SQLiteWorkingStore.open(self.root))

    def index(self) -> ports.IndexPort:
        return self._keep(SQLiteIndexStore.open(self.root))

    def overview(self) -> ports.OverviewStore:
        return self._keep(SQLiteOverviewStore.open(self.root))

    def memory(self, history, runs) -> tuple[ports.MemoryWriter, ports.MemoryReader]:
        conn = db.open_store("memory", self.root)
        self.closers.append(conn)
        writer = WriteGate(conn, history, Projector(), runs=runs, config={}, clock=utc_now)
        return writer, SQLiteMemoryReader(conn)

    # --- what no port writes ---

    def seed_index(self, index, *, lines=(), cards=(), notes=(), bars=()) -> None:
        for line in lines:
            index.put_item_line({"version": 1, "value": "forming", "check_status": "not_needed", **line})
            index.put_keys(line["item_id"], line=line["line_text"])
        for card_id, text, extra in cards:
            index.put_goal_card(card_id, text, **extra)
        for thread_id, text, items in notes:
            index.put_start_note(thread_id, text, items, 7)
        for project, bar, floor in bars:
            index.set_gate_bar(project, bar, floor)

    def seed_overview(self, overview, *, topics=(), ideas=(), suggestions=(), open_items=(), left_off=()) -> None:
        for topic_id, label, extra in topics:
            overview.put_topic(topic_id, label, **extra)
        for item_id, line in ideas:
            overview.put_idea(item_id, shown_line=line, shown_is_yours=True, origin_mark="yours", version=1)
        for suggestion in suggestions:
            overview.put_suggestion(suggestion)
        for kind, ref, line, extra in open_items:
            overview.put_open_item(kind, ref, line, **extra)
        for thread_id, extra in left_off:
            overview.put_left_off(thread_id, **extra)

    def read_mark(self, overview, item_id: str):
        return overview.mark(item_id)

    def read_topic_mark(self, overview, topic_id: str):
        return overview.topic_mark(topic_id)

    def close(self) -> None:
        for store in reversed(self.closers):
            store.close()


ADAPTERS = {"sqlite": SQLiteAdapter}


@pytest.fixture(params=sorted(ADAPTERS))
def adapter(request, store_root):
    made = ADAPTERS[request.param](store_root)
    yield made
    made.close()


@pytest.fixture
def history(adapter):
    return adapter.history()


@pytest.fixture
def loaded(adapter):
    """A history with the scenario chat, a run store with a running run, and the memory writer and reader."""
    history, runs = adapter.history(), adapter.runs()
    sc.load_history(history)
    run_id = sc.start_run(runs)
    writer, reader = adapter.memory(history, runs)
    return Loaded(history, runs, writer, reader, run_id)


@dataclass
class Loaded:
    history: Any
    runs: Any
    writer: Any
    reader: Any
    run_id: str

    def apply(self, made: ports.Proposal) -> ports.ApplyResult:
        """What a stage does: store the proposal in runs.db, record each check it was given as a verdict made by a
        recorded call of that family, then hand the proposal to the gate. The gate reads the verdicts from runs.db and
        ignores the ones the proposal carries (§5.9)."""
        stored = {v.id for v in self.runs.verdicts_for(made.proposal_id)}
        if self.runs.get_proposal(made.proposal_id) is None:
            self.runs.save_proposal(dataclasses.replace(made, verdicts=[]))
        for v in made.verdicts:
            if v.id in stored:
                continue
            call = None
            if v.checker_family != "code":
                call = self.runs.record_call(
                    ModelCall("test-provider", "test-model", v.checker_family, f"check-{v.id}", [sc.message_id(0)], run_id=made.run_id, raw_output="{}")
                )
            self.runs.record_verdict(
                made.proposal_id, Verdict(v.checker_family, list(v.rules), v.outcome, v.independent, model_call_id=call, notes=v.notes, id=v.id)
            )
        return self.writer.apply(made)


# --- HistoryStore --------------------------------------------------------------------------------------------------


def msg(n: int, text: str = "hello", *, source_id: str = "H1", speaker="user", origin="typed", **kw) -> Message:
    return Message(id=f"{source_id}:{n}", source_id=source_id, ordinal=n, speaker=speaker, text=text, origin=origin, **kw)  # type: ignore[arg-type]


def refused(call) -> bool:
    """True when a call refuses by raising ValueError or returning False: both say 'not stored'."""
    try:
        return call() is False
    except ValueError:
        return True


@pytest.fixture
def chat(history):
    history.add_source(Source(id="H1", kind="chat", app="claude-code", project="meter-logger", title="Logger"), scope=sc.SCOPE)
    return history


def test_history_is_a_history_store(history):
    assert isinstance(history, ports.HistoryStore)


def test_history_adds_a_source_once(history):
    source = Source(id="H1", kind="chat", app="claude-code", title="First title", meta={"tag": "é"})
    assert history.add_source(source, scope="personal") is True
    assert history.add_source(source, scope="personal") is False
    got = history.get_source("H1")
    assert (got.id, got.kind, got.app, got.title, got.meta) == ("H1", "chat", "claude-code", "First title", {"tag": "é"})
    assert history.get_source("nope") is None


def test_history_keeps_messages_word_for_word_and_in_order(chat):
    text = "  Keep   the spacing,\nthe newline and the é  "
    chat.append_message(msg(1, "second"))
    chat.append_message(msg(0, text, origin="pasted"))
    stored = chat.get_message("H1:0")
    assert stored.message.text == text and stored.message.origin == "pasted"
    assert stored.content_hash == content_hash(text) and stored.fidelity == "verbatim"
    assert [m.id for m in chat.get_source("H1").messages] == ["H1:0", "H1:1"]  # in (branch, ordinal) order
    assert chat.get_message("H1:9") is None


def test_history_stores_who_spoke_as_given_never_inferred(chat):
    chat.append_message(msg(0, "I can do that", speaker="assistant", origin="assistant_output", agent="claude-code", model_family="claude"))
    chat.append_message(msg(1, "pytest: 3 passed", speaker="tool", origin="tool_output"))
    a, t = chat.get_message("H1:0").message, chat.get_message("H1:1").message
    assert (a.speaker, a.origin, a.agent, a.model_family) == ("assistant", "assistant_output", "claude-code", "claude")
    assert (t.speaker, t.origin, t.agent, t.model_family) == ("tool", "tool_output", None, None)


def test_history_append_is_idempotent_and_never_overwrites(chat):
    assert chat.append_message(msg(0, "original")) is True
    assert chat.append_message(msg(0, "original")) is False
    assert refused(lambda: chat.append_message(msg(0, "changed")))
    assert chat.get_message("H1:0").message.text == "original"
    assert len(chat.get_source("H1").messages) == 1


def test_history_refuses_a_message_of_an_unknown_source(history):
    with pytest.raises(ValueError):
        history.append_message(msg(0, source_id="ghost"))


def test_history_marks_model_reported_fidelity(chat):
    chat.append_message(msg(0, "I said X", origin="model_reported"), fidelity="model_reported")
    assert chat.get_message("H1:0").fidelity == "model_reported"


def test_history_watermark_and_messages_since(chat):
    assert chat.watermark().message_seq == 0 and chat.messages_since(0) == []
    for n in range(5):
        chat.append_message(msg(n, f"turn {n}"))
    mark = chat.watermark()
    assert mark.message_seq >= 5
    everything = chat.messages_since(0)
    assert [m.message.id for m in everything] == [f"H1:{n}" for n in range(5)]
    assert [m.seq for m in everything] == sorted(m.seq for m in everything)
    assert len(chat.messages_since(0, limit=2)) == 2
    after = chat.messages_since(everything[1].seq)
    assert [m.message.id for m in after] == ["H1:2", "H1:3", "H1:4"]
    assert chat.messages_since(mark.message_seq) == []
    chat.append_message(msg(5, "later"))
    assert [m.message.id for m in chat.messages_since(mark.message_seq)] == ["H1:5"]


def test_history_a_replayed_capture_adds_nothing(chat):
    for n in range(3):
        chat.append_message(msg(n))
    before = chat.watermark()
    for n in range(3):
        assert chat.append_message(msg(n)) is False
    assert chat.watermark() == before


def test_history_work_events_and_blobs(chat):
    sha = chat.put_blob(b"def energy(): ...", "text/x-python")
    assert sha == chat.put_blob(b"def energy(): ...", "text/x-python") and len(sha) == 64
    assert chat.get_blob(sha) == b"def energy(): ..."
    assert chat.get_blob("0" * 64) is None
    event = WorkEvent(id="W1", source_id="H1", kind="file_version", ref="energy.py", evidence="medium", snapshot_sha256=sha)
    assert chat.append_work_event(event) is True
    assert chat.append_work_event(event) is False
    assert chat.watermark().work_event_seq >= 1


def test_history_records_every_reconciliation_outcome(chat):
    chat.append_message(msg(0, "I said X", origin="model_reported"), fidelity="model_reported")
    chat.append_message(msg(1, "I said X"))
    first = chat.record_reconciliation("H1:0", "H1:1", "hash", 1.0, "matched")
    second = chat.record_reconciliation("H1:0", None, "none", None, "reported_only")
    assert first != second
    with pytest.raises(ValueError):
        chat.record_reconciliation("H1:404", None, "none", None, "could_not_confirm")


def test_history_purge_removes_only_what_was_authorized(chat):
    for n in range(3):
        chat.append_message(msg(n, f"turn {n}"))
    mark = chat.watermark()
    chat.authorize_purge("purge-1", [("message", "H1:1")])
    assert chat.get_message("H1:1") is not None  # authorizing alone removes nothing
    assert chat.purge_authorized("purge-1") == 1
    assert chat.get_message("H1:1") is None
    assert chat.get_message("H1:0") is not None and chat.get_message("H1:2") is not None
    assert chat.purge_authorized("purge-1") == 0
    assert chat.watermark() == mark  # a purge never lowers the watermark


# --- MemoryWriter and MemoryReader ---------------------------------------------------------------------------------


def test_memory_ports_are_implemented(loaded):
    assert isinstance(loaded.writer, ports.MemoryWriter) and isinstance(loaded.reader, ports.MemoryReader)


def test_memory_an_empty_log_reads_as_empty(loaded):
    r = loaded.reader
    assert r.watermark() == 0 and r.events_since(0) == [] and r.get_item("m1") is None
    assert r.item_versions("m1") == [] and r.evidence_for("m1") == [] and r.changed_since(0) == []
    assert r.get_event("none") is None and r.seq_at(utc_now()) == 0


def test_memory_apply_appends_stamps_and_projects(loaded):
    result = loaded.apply(sc.proposal(loaded.run_id, sc.adopted_ops("m1")))
    assert result.status == "applied" and result.ok and len(result.applied_seqs) == 3
    r = loaded.reader
    assert r.watermark() == result.applied_seqs[-1]
    item = r.get_item("m1")
    assert item["version"] == 1 and item["status"] == "active" and item["origin"] == "adopted:claude-code"
    assert {e["role"] for e in r.evidence_for("m1")} == {"primary", "adoption"}
    stamped = r.events_since(0)
    assert [e.seq for e in stamped] == result.applied_seqs and [e.type for e in stamped][-1] == "item.created"
    assert r.get_event(stamped[0].id).seq == stamped[0].seq
    assert [e.type for e in r.events_since(0, types=["item.created"])] == ["item.created"]
    assert len(r.events_since(0, limit=1)) == 1
    assert r.events_since(result.applied_seqs[-1]) == []


def test_memory_apply_twice_is_a_duplicate_and_changes_nothing(loaded):
    made = sc.proposal(loaded.run_id, sc.adopted_ops("m1"))
    first = loaded.apply(made)
    second = loaded.apply(made)
    assert second.status == "duplicate" and second.ok and second.applied_seqs == first.applied_seqs
    assert loaded.reader.watermark() == first.applied_seqs[-1]


@pytest.mark.parametrize("bad", ["no_verdict", "same_family", "moved_span"])
def test_memory_a_refused_proposal_writes_nothing(loaded, bad):
    ops = sc.adopted_ops("m1")
    verdicts = None
    if bad == "no_verdict":
        verdicts = []
    elif bad == "same_family":
        verdicts = [sc.checked(sc.WORK_FAMILY)]
    else:
        ops[0].payload["start_char"] += 1
    result = loaded.apply(sc.proposal(loaded.run_id, ops, verdicts=verdicts))
    assert result.status == "rejected" and not result.ok and result.rejections and result.applied_seqs == []
    assert all(r.invariant and r.reason for r in result.rejections)
    assert loaded.reader.watermark() == 0 and loaded.reader.get_item("m1") is None


def test_memory_a_stale_input_is_requeued(loaded):
    loaded.apply(sc.proposal(loaded.run_id, sc.adopted_ops("m1")))
    revise = sc.op("item.revised", dict(item_id="m1", base_version=1, line="Another line", reason="refresh"))
    before = loaded.reader.watermark()
    result = loaded.apply(sc.proposal(loaded.run_id, [revise], inputs=["m1@5"]))
    assert result.status == "requeued" and not result.ok and loaded.reader.watermark() == before


def test_memory_a_proposal_of_another_run_is_fenced_out(loaded):
    other = loaded.runs.start_run("manual")  # a newer run now holds the memory
    result = loaded.apply(sc.proposal(loaded.run_id, sc.adopted_ops("m1")))
    assert result.status == "rejected" and other and loaded.reader.get_item("m1") is None


def test_memory_reads_an_earlier_state_by_seq_and_by_time(loaded):
    r = loaded.reader
    first = loaded.apply(sc.proposal(loaded.run_id, sc.adopted_ops("m1")))
    checkpoint = first.applied_seqs[-1]
    revise = sc.op("item.revised", dict(item_id="m1", base_version=1, line="Raw readings are kept for 30 days", reason="refresh"))
    assert loaded.apply(sc.proposal(loaded.run_id, [revise], inputs=["m1@1"])).status == "applied"
    assert r.get_item("m1")["version"] == 2
    assert r.get_item("m1", as_of_seq=checkpoint)["version"] == 1
    assert r.get_item("m1", as_of_seq=checkpoint - 1) is None
    assert r.get_item_version("m1", 1)["line"].endswith("daily averages") and r.get_item_version("m1", 2)["version"] == 2
    assert r.get_item_version("m1", 3) is None
    assert [v["version"] for v in r.item_versions("m1")] == [1, 2]
    assert r.changed_since(checkpoint) == ["m1"] and r.changed_since(r.watermark()) == []
    assert r.seq_at("2999-01-01T00:00:00Z") == r.watermark() and r.seq_at("2000-01-01T00:00:00Z") == 0
    with pytest.raises(ValueError):
        r.get_item("m1", as_of_seq=checkpoint, as_of="2999-01-01T00:00:00Z")


def test_memory_reading_changes_nothing(loaded):
    loaded.apply(sc.proposal(loaded.run_id, sc.adopted_ops("m1")))
    r = loaded.reader
    before = (r.watermark(), r.events_since(0), r.get_item("m1"), r.evidence_for("m1"))
    r.get_item("m1", as_of_seq=1), r.changed_since(0), r.subgraph(["m1"], depth=2), r.item_versions("m1")
    assert (r.watermark(), r.events_since(0), r.get_item("m1"), r.evidence_for("m1")) == before


def test_memory_subgraph_follows_links_of_the_asked_statuses(loaded):
    r = loaded.reader
    loaded.apply(sc.proposal(loaded.run_id, sc.adopted_ops("m1")))
    loaded.apply(sc.proposal(loaded.run_id, sc.yours_ops("m2")))
    link = sc.op("link.applied", dict(
        link_id="l1", from_id="m2", to_id="m1", link_type="supports", reason="the logger keeps what the decision says",
        stated_by="northstar", checked_by=[sc.CHECKER],
    ))  # fmt: skip
    result = loaded.apply(sc.proposal(loaded.run_id, [link], inputs=["m1@1", "m2@1"]))
    assert result.status == "applied", result.rejections
    graph = r.subgraph(["m2"], depth=1)
    assert set(graph.items) == {"m1", "m2"} and [row["id"] for row in graph.links] == ["l1"]
    assert set(r.subgraph(["m2"], depth=0).items) == {"m2"}
    assert r.subgraph(["m2"], depth=1, statuses=("proposed",)).links == []
    assert r.subgraph(["nope"]).items == {}


# --- WorkingStore --------------------------------------------------------------------------------------------------


@pytest.fixture
def working(adapter):
    return adapter.working()


def test_working_is_a_working_store(working):
    assert isinstance(working, ports.WorkingStore)


def test_working_opens_and_lists_threads(working):
    a = working.open_thread("Alerts", scope=sc.SCOPE, project="meter-logger")
    b = working.open_thread("Reports", scope=sc.SCOPE, project="meter-logger")
    c = working.open_thread("Notes", scope="personal", project=None)
    assert working.get_thread(a)["title"] == "Alerts" and working.get_thread(a)["status"] == "active"
    assert working.get_thread("nope") is None
    assert {t["id"] for t in working.threads()} == {a, b, c}
    assert {t["id"] for t in working.threads(project="meter-logger")} == {a, b}
    working.set_thread_status(b, "paused")
    assert [t["id"] for t in working.threads(status="paused")] == [b]
    assert {t["id"] for t in working.threads(status="active")} == {a, c}
    working.touch_thread(a, "2026-04-07T10:00:00.000Z")
    assert working.get_thread(a)["last_active"] == "2026-04-07T10:00:00.000Z"
    with pytest.raises(ValueError):
        working.set_thread_status(a, "finished")  # type: ignore[arg-type]


def test_working_a_goal_is_your_words_with_your_turn(working):
    with pytest.raises(ValueError):
        working.open_thread("Alerts", scope=sc.SCOPE, goal_text="Alert me when the dryer costs double")  # no turn named
    with pytest.raises(ValueError):
        working.open_thread("Alerts", scope=sc.SCOPE, goal_text="  ", goal_message_id="LOG1:3")
    tid = working.open_thread(
        "Alerts", scope=sc.SCOPE, goal_text="Alert me when the dryer costs double", goal_message_id="LOG1:3", goal_basis="stated"
    )
    thread = working.get_thread(tid)
    assert thread["goal_text"] == "Alert me when the dryer costs double" and thread["goal_message_id"] == "LOG1:3"


def test_working_versions_keep_one_best_and_your_feedback(working):
    tid = working.open_thread("Reports", scope=sc.SCOPE)
    v1 = working.record_version(tid, "a41c9e0", made_at_turn=2)
    v2 = working.record_version(tid, "b52d0f1", parent_id=v1)
    other = working.record_version(working.open_thread("Other", scope="personal"), "zzz")
    with pytest.raises(ValueError):
        working.record_version(tid, "c63e1a2", parent_id=other)  # a parent of another thread
    working.add_feedback(v1, "the totals should come first", "LOG1:3")
    with pytest.raises(ValueError):
        working.add_feedback(v1, "", "LOG1:3")
    with pytest.raises(ValueError):
        working.add_feedback(v1, "shorter please", "")
    assert [v["id"] for v in working.versions(tid)] == [v1, v2]
    assert working.versions(tid)[0]["feedback"] == [{"your_quote": "the totals should come first", "message_id": "LOG1:3"}]
    assert working.best_version(tid) is None
    working.set_best(tid, v1)
    working.set_best(tid, v2)
    assert working.best_version(tid)["id"] == v2
    assert [v["id"] for v in working.versions(tid) if v["best"]] == [v2]
    with pytest.raises(ValueError):
        working.set_best(tid, other)


def test_working_live_decisions_need_your_words(working):
    tid = working.open_thread("Alerts", scope=sc.SCOPE)
    with pytest.raises(ValueError):
        working.add_live_decision(tid, "decided", "Use a rolling baseline", "", "LOG1:3")
    with pytest.raises(ValueError):
        working.add_live_decision(tid, "decided", "Use a rolling baseline", "a rolling baseline", "")
    d1 = working.add_live_decision(tid, "decided", "Use a rolling baseline", "let's use a rolling baseline", "LOG1:3")
    d2 = working.add_live_decision(tid, "ruled_out", "No fixed limit", "no fixed limit", "LOG1:3")
    assert {d["id"] for d in working.live_decisions(tid)} == {d1, d2}
    working.set_decision_status(d1, "in_memory")
    assert [d["id"] for d in working.live_decisions(tid)] == [d2]
    assert {d["id"] for d in working.live_decisions(tid, status=None)} == {d1, d2}
    with pytest.raises(ValueError):
        working.set_decision_status(d1, "forgotten")  # type: ignore[arg-type]


def test_working_side_topics(working):
    tid = working.open_thread("Alerts", scope=sc.SCOPE)
    s1 = working.add_side_topic(tid, "Which sensor gives the dryer reading?")
    s2 = working.add_side_topic(tid, "Email layout", opened_at_message="LOG1:3")
    assert {s["id"] for s in working.side_topics(tid)} == {s1, s2}
    working.set_side_topic_status(s1, "closed")
    assert [s["id"] for s in working.side_topics(tid)] == [s2]
    assert {s["id"] for s in working.side_topics(tid, status=None)} == {s1, s2}


def test_working_receipts_keep_hashes_and_never_the_text(working):
    working.start_session("chat-1", app="claude-code", project="meter-logger", started_at="2026-04-07T09:00:00.000Z")
    text = "Earlier you decided that raw readings are kept for 14 days and then only daily averages."
    rid = working.record_receipt("chat-1", "facts", ["m1@1"], content_hash(text), fingerprints(text), at="2026-04-07T09:05:00.000Z")
    assert rid
    working.record_receipt("chat-1", "recall", ["m2@1"], "hash2", [], at="2026-04-07T09:30:00.000Z")
    rows = working.receipts("chat-1")
    assert [r["kind"] for r in rows] == ["facts", "recall"]
    assert [r["id"] for r in working.receipts(since="2026-04-07T09:10:00.000Z")] == [rows[1]["id"]]
    assert working.receipts("another-chat") == []
    assert all(text not in json.dumps(r, default=str) and "text" not in r for r in rows)  # the delivered text is not kept
    with pytest.raises(ValueError):
        working.record_receipt("chat-1", "facts", ["not an item"], "h", [])
    with pytest.raises((KeyError, ValueError)):
        working.record_receipt("no-such-session", "facts", ["m1@1"], "h", [])
    working.attach_session("chat-1", working.open_thread("Alerts", scope=sc.SCOPE))
    working.set_context_used("chat-1", 4200)
    with pytest.raises((KeyError, ValueError)):
        working.set_context_used("no-such-session", 1)


# --- IndexPort -----------------------------------------------------------------------------------------------------

LINES = [
    dict(item_id="f1", kind="decision", line_text="Raw readings are kept for 14 days, then only daily averages", **{"class": "fact"}, scope=sc.SCOPE, status="active"),
    dict(item_id="f2", kind="decision", line_text="Readings from the dryer meter are logged to SQLite", **{"class": "fact"}, scope="personal", status="active"),
    dict(item_id="f3", kind="decision", line_text="Readings for the other project use Postgres", **{"class": "fact"}, scope="project:other", status="active"),
    dict(item_id="v1", kind="principle", line_text="Readings should be cheap to store", **{"class": "view"}, scope="personal", status="active"),
    dict(item_id="f4", kind="decision", line_text="Readings used to be kept forever", **{"class": "fact"}, scope=sc.SCOPE, status="superseded"),
]  # fmt: skip


@pytest.fixture
def index(adapter):
    made = adapter.index()
    adapter.seed_index(made, lines=LINES)
    return made


def ids(hits) -> list[str]:
    return [h.item_id for h in hits]


def test_index_is_an_index_port(index):
    assert isinstance(index, ports.IndexPort)


def test_index_push_gives_active_facts_that_cover_this_chat(index):
    hits = index.search(SearchQuery("readings", direction="push", project="meter-logger"))
    assert set(ids(hits)) == {"f1", "f2"}  # not the view, not another project, not the superseded fact
    assert all(h.found_by and set(h.found_by) <= {"links", "words", "meaning", "time"} for h in hits)
    by_id = {h.item_id: h for h in hits}
    assert by_id["f1"].line_text == LINES[0]["line_text"] and by_id["f1"].version == 1 and by_id["f1"].scope == sc.SCOPE
    assert by_id["f1"].kind == "decision"
    assert [h.score for h in hits] == sorted((h.score for h in hits), reverse=True)


def test_index_push_without_a_project_gives_only_personal_facts(index):
    assert ids(index.search(SearchQuery("readings", direction="push"))) == ["f2"]


def test_index_pull_gives_facts_and_views_in_the_allowed_scopes(index):
    everything = set(ids(index.search(SearchQuery("readings", direction="pull"))))
    assert {"f1", "f2", "v1"} <= everything and "f4" not in everything
    narrowed = ids(index.search(SearchQuery("readings", direction="pull", allowed_scopes=["personal"])))
    assert set(narrowed) == {"f2", "v1"}


def test_index_search_honours_exclusions_and_top_n(index):
    query = SearchQuery("readings", direction="pull", exclude_item_ids=["f2"])
    assert "f2" not in ids(index.search(query))
    assert len(index.search(SearchQuery("readings", direction="pull", top_n=1))) == 1
    assert index.search(SearchQuery("zzzunmatched", direction="pull")) == []
    assert index.search(SearchQuery("", direction="pull")) == []


def test_index_search_text_is_words_never_syntax(index):
    for text in ['readings" OR (', "NEAR(readings", "*", "readings AND", "col:readings", "'; DROP TABLE keys; --"]:
        index.search(SearchQuery(text, direction="pull"))  # must not raise
    assert "f1" in ids(index.search(SearchQuery("readings AND", direction="pull")))


def test_index_search_changes_nothing(index):
    before = index.search(SearchQuery("readings", direction="pull"))
    index.search(SearchQuery("readings", direction="push", project="meter-logger"))
    assert index.search(SearchQuery("readings", direction="pull")) == before


def test_index_goal_cards_and_start_notes(adapter):
    index = adapter.index()
    adapter.seed_index(
        index,
        cards=[
            ("c1", "Alert me when the dryer costs double", dict(goal_item_id="g1", project="meter-logger", top_items=["f1"], last_active="2026-04-07T10:00:00Z")),
            ("c2", "A weekly summary email", dict(thread_id="t2", project="meter-logger", last_active="2026-04-08T10:00:00Z")),
            ("c3", "Notes on the garden", dict(thread_id="t3", project="garden", last_active="2026-04-01T10:00:00Z")),
        ],
        notes=[("t2", "Where you left off: the email layout.", ["f1@1"])],
    )
    assert index.goal_card("c1")["goal_text"] == "Alert me when the dryer costs double"
    assert index.goal_card("nope") is None
    assert {c["id"] for c in index.goal_cards()} == {"c1", "c2", "c3"}
    assert [c["id"] for c in index.goal_cards(project="meter-logger")] == ["c2", "c1"]  # most recently active first
    note = index.start_note("t2")
    assert note["text"].startswith("Where you left off") and note["items"] == ["f1@1"]
    assert index.start_note("t9") is None


def test_index_counts_uses(index):
    assert index.use_summary("f1") is None
    index.record_use("f1", "delivered", "chat-1", at="2026-04-07T09:00:00.000Z")
    index.record_use("f1", "delivered", "chat-2", at="2026-04-08T09:00:00.000Z")
    index.record_use("f1", "recalled", "chat-2", at="2026-04-09T09:00:00.000Z")
    summary = index.use_summary("f1")
    assert (summary["delivered"], summary["recalled"], summary["viewed"], summary["built_on"]) == (2, 1, 0, 0)
    assert summary["contexts"] == 2 and summary["last_at"].startswith("2026-04-09")
    with pytest.raises(ValueError):
        index.record_use("f1", "admired", "chat-1")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        index.record_use("f1", "viewed", "")


def test_index_the_gate_bar_moves_one_step_and_never_below_its_floor(adapter):
    index = adapter.index()
    adapter.seed_index(index, bars=[("meter-logger", 0.5, 0.2)])
    assert index.gate_bar("meter-logger") == 0.5 and index.gate_bar("garden") is None
    assert index.move_gate_bar("meter-logger", "lower", "re_explanation", step=0.1, floor=0.2) == pytest.approx(0.4)
    assert index.move_gate_bar("meter-logger", "raise", "leak", step=0.25, floor=0.2) == pytest.approx(0.65)
    assert index.move_gate_bar("meter-logger", "lower", "presumption", step=1.0, floor=0.2) == pytest.approx(0.2)
    assert index.gate_bar("meter-logger") == pytest.approx(0.2)
    with pytest.raises(ValueError):
        index.move_gate_bar("meter-logger", "lower", "boredom", step=0.1, floor=0.2)  # type: ignore[arg-type]


# --- OverviewStore -------------------------------------------------------------------------------------------------


@pytest.fixture
def overview(adapter):
    made = adapter.overview()
    adapter.seed_overview(
        made,
        topics=[
            ("t-logging", "Logging", dict(entries=["m1", "m2"], open_count=1)),
            ("t-alerts", "Alerts", {}),
            ("t-rotation", "Rotation", dict(parent_id="t-logging")),
        ],
        ideas=[("m1", "Raw readings are kept for 14 days")],
        suggestions=[
            dict(link_id="l1", from_id="m2", to_id="m1", type="supports", reason="the logger follows the decision"),
            dict(link_id="l2", from_id="m1", to_id="m3", type="refines", reason="a narrower case", status="confirmed"),
        ],
        open_items=[("open_question", "q1", "How do I avoid alert fatigue?", dict(topic_id="t-alerts", since="2026-04-01T00:00:00Z"))],
        left_off=[("t1", dict(last_state="The alert fires twice", last_steps=["wrote the baseline"], next_step="debounce the alert"))],
    )
    return made


def test_overview_is_an_overview_store(overview):
    assert isinstance(overview, ports.OverviewStore)


def test_overview_topics_are_two_levels(overview):
    assert [t["topic_id"] for t in overview.topics()] == ["t-alerts", "t-logging"]
    assert [t["topic_id"] for t in overview.topics(parent_id="t-logging")] == ["t-rotation"]
    assert overview.topics(parent_id="t-alerts") == []
    view = overview.topic_view("t-logging")
    assert view["label"] == "Logging" and view["entries"] == ["m1", "m2"] and view["open_count"] == 1
    assert overview.topic_view("nope") is None


def test_overview_ideas_open_items_and_where_you_left_off(overview):
    assert overview.idea_view("m1")["shown_line"] == "Raw readings are kept for 14 days"
    assert overview.idea_view("nope") is None
    assert [o["ref_id"] for o in overview.open_items()] == ["q1"]
    assert [o["ref_id"] for o in overview.open_items(topic_id="t-alerts")] == ["q1"]
    assert overview.open_items(topic_id="t-logging") == []
    left = overview.left_off("t1")
    assert left["last_state"] == "The alert fires twice" and left["last_steps"] == ["wrote the baseline"]
    assert overview.left_off("t2") is None


def test_overview_suggestions_wait_for_your_confirmation(overview):
    assert [s["link_id"] for s in overview.suggestions()] == ["l1"]
    assert [s["link_id"] for s in overview.suggestions("confirmed")] == ["l2"]
    assert overview.suggestions("rejected") == []
    with pytest.raises(ValueError):
        overview.suggestions("maybe")


def test_overview_layout_keeps_the_previous_position(overview):
    assert overview.layout() == []
    nodes = [dict(node_id="m1", node_kind="entry", x=1.0, y=2.0), dict(node_id="t-logging", node_kind="topic", x=5.0, y=5.0)]
    overview.set_layout(nodes, seed=7)
    first = {n["node_id"]: n for n in overview.layout()}
    assert (first["m1"]["x"], first["m1"]["y"]) == (1.0, 2.0) and first["m1"]["prev_x"] is None
    overview.set_layout([dict(node_id="m1", node_kind="entry", x=3.0, y=4.0)], seed=7)
    second = {n["node_id"]: n for n in overview.layout()}
    assert set(second) == {"m1"}  # a node left out is dropped
    assert (second["m1"]["x"], second["m1"]["prev_x"], second["m1"]["prev_y"]) == (3.0, 1.0, 2.0)
    with pytest.raises(ValueError):
        overview.set_layout([dict(node_id="m1", node_kind="planet", x=0, y=0)], seed=1)


def test_overview_remembers_what_you_saw_pinned_and_opened(adapter, overview):
    overview.mark_seen("m1", 2, at="2026-04-07T09:00:00.000Z")
    overview.set_pinned("m1", True)
    mark = adapter.read_mark(overview, "m1")
    assert mark["last_seen_version"] == 2 and mark["pinned"] == 1  # a pin does not forget what you saw
    overview.mark_seen("m1", 3)
    assert adapter.read_mark(overview, "m1")["pinned"] == 1 and adapter.read_mark(overview, "m1")["last_seen_version"] == 3
    overview.set_pinned("m1", False)
    assert adapter.read_mark(overview, "m1")["pinned"] == 0
    overview.record_hidden_open("t-logging")
    overview.record_hidden_open("t-logging")
    assert adapter.read_topic_mark(overview, "t-logging")["hidden_opens"] == 2


# --- RunStore ------------------------------------------------------------------------------------------------------


@pytest.fixture
def runs(adapter):
    return adapter.runs()


def test_runs_is_a_run_store(runs):
    assert isinstance(runs, ports.RunStore)


def test_runs_have_a_state(runs):
    rid = runs.start_run("nightly", watermark_from=4)
    run = runs.get_run(rid)
    assert (run["state"], run["trigger"], run["watermark_from"]) == ("running", "nightly", 4)
    runs.finish_run(rid, "applied", watermark_to=9, result={"changes": 2})
    run = runs.get_run(rid)
    assert (run["state"], run["watermark_to"]) == ("applied", 9) and run["ended_at"] is not None
    with pytest.raises(ValueError):
        runs.start_run("whenever")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        runs.finish_run(runs.start_run("manual"), "exploded")  # type: ignore[arg-type]


def test_runs_a_held_run_has_no_end_time(runs):
    rid = runs.start_run("weekly")
    runs.finish_run(rid, "held")
    assert runs.get_run(rid)["state"] == "held" and runs.get_run(rid)["ended_at"] is None


def test_runs_jobs_are_idempotent_by_key(runs):
    rid = runs.start_run("manual")
    first = runs.enqueue(rid, "extract", "extract:LOG1", {"source": "LOG1"})
    assert runs.enqueue(rid, "extract", "extract:LOG1", {"source": "LOG1"}) == first
    assert runs.enqueue(rid, "extract", "extract:LOG2") != first
    assert len(runs.jobs(rid)) == 2


def test_runs_lease_takes_the_oldest_job_of_the_asked_stages(runs):
    rid = runs.start_run("manual")
    j1 = runs.enqueue(rid, "extract", "k1", {"n": 1})
    j2 = runs.enqueue(rid, "extract", "k2", {"n": 2})
    j3 = runs.enqueue(rid, "check", "k3")
    assert runs.lease("w1", ["replay"], 60) is None
    job = runs.lease("w1", ["extract"], 60)
    assert job.id == j1 and job.attempts == 1 and job.lease_owner == "w1" and job.payload == {"n": 1} and job.run_id == rid
    assert runs.lease("w2", ["extract"], 60).id == j2
    assert runs.lease("w3", ["extract"], 60) is None  # both are leased
    assert runs.lease("w3", ["check", "extract"], 60).id == j3


def test_runs_an_expired_lease_is_taken_again(runs):
    rid = runs.start_run("manual")
    job_id = runs.enqueue(rid, "extract", "k1")
    first = runs.lease("w1", ["extract"], 60, now="2026-04-07T09:00:00.000Z")
    assert runs.lease("w2", ["extract"], 60, now="2026-04-07T09:00:30.000Z") is None
    again = runs.lease("w2", ["extract"], 60, now="2026-04-07T09:01:30.000Z")
    assert again.id == job_id == first.id and again.attempts == 2 and again.lease_owner == "w2"


def test_runs_complete_and_fail(runs):
    rid = runs.start_run("manual")
    done, retried, failed = (runs.enqueue(rid, "extract", f"k{n}") for n in range(3))
    for _ in range(3):
        runs.lease("w", ["extract"], 60)
    runs.complete(done)
    runs.fail(retried, "timeout", retry=True)
    runs.fail(failed, "bad output", retry=False)
    again = runs.lease("w", ["extract"], 60)
    assert again.id == retried and again.attempts == 2  # only the retried job comes back
    assert runs.lease("w", ["extract"], 60) is None


def test_runs_record_calls_by_ids_never_by_assembled_text(runs):
    rid = runs.start_run("manual")
    call = ModelCall("test-provider", "test-model", "claude", "h1", ["LOG1:0", "m1@1"], run_id=rid, raw_output='{"ok": true}', tokens_in=10)
    call_id = runs.record_call(call)
    assert runs.get_call(call_id)["raw_output"] == '{"ok": true}'
    assert runs.recorded_call("h1", rid)["id"] == call_id and runs.recorded_call("unknown") is None
    with pytest.raises(ValueError):
        runs.record_call(ModelCall("p", "m", "claude", "h2", ["the whole prompt as one long text, with spaces"], run_id=rid))


def test_runs_save_a_proposal_with_its_verdicts_and_set_its_state(runs):
    rid = runs.start_run("manual")
    made = sc.proposal(rid, sc.adopted_ops("m1"), verdicts=[sc.checked()])
    runs.save_proposal(made)
    loaded = runs.load_proposal(made.proposal_id)
    assert [op.type for op in loaded.ops] == [op.type for op in made.ops] and loaded.risk_tier == made.risk_tier
    assert [v.checker_family for v in loaded.verdicts] == [sc.CHECKER]
    extra = Verdict("anthropic", ["scope"], "pass", True)
    runs.record_verdict(made.proposal_id, extra)
    assert len(runs.verdicts(made.proposal_id)) == 2
    assert runs.get_proposal(made.proposal_id)["state"] == "pending"
    runs.set_proposal_state(made.proposal_id, "applied")
    assert runs.get_proposal(made.proposal_id)["state"] == "applied"
    with pytest.raises(ValueError):
        runs.set_proposal_state(made.proposal_id, "lost")  # type: ignore[arg-type]


def test_runs_a_quarantine_allows_three_attempts_then_discards(runs):
    deadline = "2999-01-01T00:00:00.000Z"
    q = runs.quarantine("item", "m1", "the check failed", deadline)
    assert runs.quarantine("item", "m1", "failed again", deadline) == q
    assert runs.quarantine("item", "m1", "failed a third time", deadline) == q
    assert runs.get_quarantine(q)["attempts"] == 3 and runs.get_quarantine(q)["state"] == "open"
    runs.quarantine("item", "m1", "failed a fourth time", deadline)
    assert runs.get_quarantine(q)["state"] == "exited" and runs.get_quarantine(q)["exit"] == "discarded"
    other = runs.quarantine("link", "l1", "unclear", deadline)
    runs.exit_quarantine(other, "fresh_call")
    assert runs.get_quarantine(other)["exit"] == "fresh_call"
    with pytest.raises(ValueError):
        runs.exit_quarantine(other, "discarded")  # it has exited already


def test_runs_an_error_budget_freezes_a_change_type(runs):
    assert runs.budget("merge") is None
    row = runs.record_audit("merge", n=100, errors=1, freeze_above=0.02)
    assert not row["frozen"] and row["audited_n"] == 100 and row["audited_errors"] == 1
    row = runs.record_audit("merge", n=100, errors=5, freeze_above=0.02)  # 6 of 200 is 3%
    assert row["frozen"] and runs.budget("merge")["frozen"]
    row = runs.record_audit("merge", n=1000, errors=0, freeze_above=0.02)
    assert row["frozen"]  # a freeze stays until a test run passes
    assert not runs.record_audit("scope_widened", n=100, errors=2, freeze_above=0.02)["frozen"]  # exactly 2% is within budget
    with pytest.raises(ValueError):
        runs.record_audit("merge", n=1, errors=2)


def test_runs_the_change_log_is_one_plain_line_per_change(runs):
    rid = runs.start_run("manual")
    c1 = runs.log_change(rid, "adoption", "Added: raw readings are kept for 14 days", ["e1", "e2"], undo_handle="undo-1")
    runs.log_change(rid, "merge", "Merged two lines about the logger", ["e3"])
    log = runs.read_change_log(rid)
    assert [row["id"] for row in log][0] == c1 and len(log) == 2
    assert log[0]["undo_handle"] == "undo-1" and log[0]["event_ids"] == ["e1", "e2"] and log[0]["undone_at"] is None
    with pytest.raises(ValueError):
        runs.log_change(rid, "merge", "   ", [])
    with pytest.raises((KeyError, ValueError)):
        runs.log_change("no-such-run", "merge", "A line", [])


# --- the protocols match the adapters ------------------------------------------------------------------------------


def _mismatch(port_name: str, name: str, proto_fn, adapter_fn) -> list[str]:
    """What differs between a protocol method and the adapter's: a missing name, a parameter the adapter lacks or
    takes another way, a default the protocol has and the adapter lacks, or a required parameter only the adapter has."""
    import inspect

    wanted = list(inspect.signature(proto_fn).parameters.values())[1:]  # without self
    given = {p.name: p for p in list(inspect.signature(adapter_fn).parameters.values())}
    problems = []
    for p in wanted:
        q = given.get(p.name)
        if q is None:
            if not any(g.kind is inspect.Parameter.VAR_KEYWORD for g in given.values()):
                problems.append(f"{port_name}.{name}: no parameter {p.name!r}")
            continue
        if p.kind is inspect.Parameter.KEYWORD_ONLY and q.kind is inspect.Parameter.POSITIONAL_ONLY:
            problems.append(f"{port_name}.{name}: {p.name!r} must be a keyword")
        if p.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD and q.kind is not inspect.Parameter.POSITIONAL_OR_KEYWORD:
            problems.append(f"{port_name}.{name}: {p.name!r} is positional or keyword in the port")
        if p.default is not inspect.Parameter.empty and q.default is inspect.Parameter.empty:
            problems.append(f"{port_name}.{name}: {p.name!r} has a default in the port and none in the adapter")
    for q in given.values():
        if q.name not in {p.name for p in wanted} and q.default is inspect.Parameter.empty and q.kind in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY,
        ) and q.name != "self":
            problems.append(f"{port_name}.{name}: the adapter needs {q.name!r}, which the port does not pass")
    return problems


def test_every_adapter_has_every_method_of_its_port_with_the_same_parameters(loaded, adapter):
    import typing

    stores = {
        "HistoryStore": (ports.HistoryStore, loaded.history),
        "MemoryWriter": (ports.MemoryWriter, loaded.writer),
        "MemoryReader": (ports.MemoryReader, loaded.reader),
        "WorkingStore": (ports.WorkingStore, adapter.working()),
        "IndexPort": (ports.IndexPort, adapter.index()),
        "OverviewStore": (ports.OverviewStore, adapter.overview()),
        "RunStore": (ports.RunStore, loaded.runs),
    }
    problems = []
    for port_name, (proto, instance) in stores.items():
        for name in sorted(typing.get_protocol_members(proto)):
            if not hasattr(instance, name):
                problems.append(f"{port_name}.{name}: the adapter has no such method")
            else:
                problems += _mismatch(port_name, name, getattr(proto, name), getattr(instance, name))
    assert problems == []


def test_the_ports_list_the_reads_callers_use():
    import typing

    wanted = {
        ports.RunStore: {
            "get_run", "load_proposal", "verdicts_for", "get_call", "recorded_call", "get_quarantine", "read_change_log", "jobs",
            "runs", "is_frozen", "mark_running", "get_proposal", "verdicts",
        },
        ports.WorkingStore: {"delivered_fingerprints"},
        ports.HistoryStore: {"append_messages", "messages_for_source"},
        ports.MemoryReader: {"get", "get_item_version"},
    }
    for proto, names in wanted.items():
        assert names <= set(typing.get_protocol_members(proto)), (proto.__name__, names - set(typing.get_protocol_members(proto)))


@pytest.mark.skipif(not hasattr(SQLiteHistoryStore, "get_source_info"), reason="the history adapter does not have get_source_info yet")
def test_a_history_store_gives_a_sources_kind_and_scope(history):
    history.add_source(Source(id="H1", kind="chat", app="claude-code"), scope="project:meter-logger")
    assert isinstance(history, ports.SourceInfoReader)
    info = history.get_source_info("H1")
    assert info["kind"] == "chat" and info["scope"] == "project:meter-logger" and history.get_source_info("nope") is None


# --- the starting values in the config are the numbers the code holds (I19) -----------------------------------------


def test_the_shipped_maintenance_block_matches_the_constants_the_core_still_holds():
    from northstar_agent_memory import config
    from northstar_agent_memory.core import index_store, runs, working
    from northstar_agent_memory.core.invariants import Limits

    block = config.defaults()["maintenance"]
    limits = Limits()
    for field in Limits.__dataclass_fields__:
        assert block[field] == getattr(limits, field), field  # the gate's caps and loss bound
    assert Limits.from_config(config.defaults()) == limits
    assert block["goal_card_top_items"] == index_store.GOAL_CARD_TOP_ITEMS
    assert block["fingerprint_words"] == working.FINGERPRINT_WORDS
    assert block["echo_overlap"] == working.ECHO_OVERLAP
    assert block["quarantine_attempts"] == runs.MAX_QUARANTINE_ATTEMPTS
    assert block["quarantine_days"] == runs.QUARANTINE_DAYS
    assert block["error_budget"] == runs.DEFAULT_ERROR_BUDGET
    assert block["error_budget_min_sample"] == runs.ERROR_BUDGET_MIN_SAMPLE
    assert block["max_job_attempts"] == runs.MAX_JOB_ATTEMPTS
    assert block["idle_trigger_minutes"] == runs.IDLE_TRIGGER_MINUTES
    assert "maintenance" in config.defaults() and config.defaults()["config_version"] >= "2026-11-04.2"


# --- the run store through its port: verdicts, the attempt cap and the budget ---------------------------------------


def test_runs_a_verdict_is_recorded_with_its_call_family_and_label(runs):
    rid = runs.start_run("manual")
    made = sc.proposal(rid, sc.adopted_ops("m1"), verdicts=[])
    runs.save_proposal(made)
    call = runs.record_call(ModelCall("test-provider", "test-model", "openai", "hv", ["m1@1"], run_id=rid, raw_output="{}"))
    runs.record_verdict(made.proposal_id, Verdict("openai", ["scope"], "pass", False, model_call_id=call))
    [v] = runs.verdicts_for(made.proposal_id)
    assert (v.checker_family, v.model_call_id, v.independent, v.passed) == ("openai", call, False, True)
    with pytest.raises(ValueError):  # a verdict that says it is claude's, with an openai call behind it
        runs.record_verdict(made.proposal_id, Verdict("claude", ["scope"], "pass", True, model_call_id=call))
    assert len(runs.verdicts_for(made.proposal_id)) == 1


def test_runs_a_job_that_keeps_failing_is_quarantined(runs):
    rid = runs.start_run("manual")
    job_id = runs.enqueue(rid, "extract", "k1")
    states = []
    for _ in range(3):
        assert runs.lease("w", ["extract"], 60).id == job_id
        runs.mark_running(job_id)
        states.append(runs.fail(job_id, "model timed out", retry=True))
    assert states == ["queued", "queued", "quarantined"]
    assert runs.lease("w", ["extract"], 60) is None and [j["state"] for j in runs.jobs(rid)] == ["quarantined"]


def test_runs_a_type_freezes_only_after_a_minimum_sample(runs):
    assert not runs.record_audit("merge", n=5, errors=1)["frozen"]  # 20% of 5 audited: too few to say
    assert runs.record_audit("merge", n=15, errors=0)["frozen"]  # 20 audited, 1 wrong: 5%, above 2%
