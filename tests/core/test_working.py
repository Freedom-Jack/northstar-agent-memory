"""SQLiteWorkingStore: threads, sessions, live decisions, versions, side topics, receipts and the echo guard (§2.9)."""

from __future__ import annotations

import sqlite3

import pytest

from northstar_agent_memory import paths
from northstar_agent_memory.core import ports, working
from northstar_agent_memory.core.ids import content_hash, is_ulid
from northstar_agent_memory.core.working import SQLiteWorkingStore, UserWordsRequired, echo_overlap, fingerprints, is_echo

# Invented: Robin's energy dashboard (MEMORY-ARCHITECTURE §6).
DELIVERED = (
    "2026-03-02 · project energy-dash · decided by the user: Readings are stored in SQLite on the Pi, one file per meter."
)


@pytest.fixture
def store(open_all):
    return SQLiteWorkingStore(open_all["working"])


@pytest.fixture
def thread(store):
    return store.open_thread("Energy dashboard logger", scope="project:energy-dash", project="energy-dash")


@pytest.fixture
def session(store, thread):
    store.start_session("S1", app="claude-code", project="energy-dash", thread_id=thread, started_at="2026-03-02T09:00:00.000Z")
    return "S1"


def test_it_is_a_working_store(store):
    assert isinstance(store, ports.WorkingStore)


def test_open_from_a_root(store_root):
    s = SQLiteWorkingStore.open(store_root)
    assert (store_root / "working.db").is_file()
    s.close()


def test_the_default_open_uses_the_isolated_data_root(isolated_home):
    s = SQLiteWorkingStore.open()
    assert (paths.data_root() / "working.db").is_file()
    assert paths.data_root().is_relative_to(isolated_home)
    s.close()


# --- threads ---


def test_open_thread_makes_an_active_thread(store):
    tid = store.open_thread("Dryer alert", scope="project:energy-dash", project="energy-dash")
    row = store.get_thread(tid)
    assert is_ulid(tid)
    assert row["title"] == "Dryer alert" and row["status"] == "active" and row["project"] == "energy-dash"
    assert row["goal_text"] is None and row["goal_message_id"] is None and row["goal_basis"] is None
    assert row["tenant_id"] == "local"
    assert row["opened_at"] == row["last_active"]


def test_open_thread_with_a_goal_in_your_words(store):
    tid = store.open_thread(
        "Dryer alert", scope="personal", goal_text="Alert me when the dryer costs double", goal_message_id="M7", goal_basis="stated"
    )
    row = store.get_thread(tid)
    assert (row["goal_text"], row["goal_message_id"], row["goal_basis"]) == ("Alert me when the dryer costs double", "M7", "stated")


def test_goal_basis_defaults_to_stated(store):
    tid = store.open_thread("t", scope="personal", goal_text="Ship the logger", goal_message_id="M1")
    assert store.get_thread(tid)["goal_basis"] == "stated"


def test_a_goal_without_a_message_id_is_refused(store):
    with pytest.raises(UserWordsRequired):
        store.open_thread("t", scope="personal", goal_text="Ship the logger")
    with pytest.raises(UserWordsRequired):
        store.open_thread("t", scope="personal", goal_text="Ship the logger", goal_message_id="")
    assert store.threads() == []


def test_a_message_id_without_a_goal_is_refused(store):
    with pytest.raises(ValueError):
        store.open_thread("t", scope="personal", goal_message_id="M1")
    with pytest.raises(ValueError):
        store.open_thread("t", scope="personal", goal_basis="stated")


def test_open_thread_refuses_bad_input(store):
    with pytest.raises(ValueError):
        store.open_thread(" ", scope="personal")
    with pytest.raises(sqlite3.IntegrityError):
        store.open_thread("t", scope="everyone")
    with pytest.raises(ValueError):
        store.open_thread("t", scope="personal", goal_text="g", goal_message_id="M1", goal_basis="guessed")


def test_thread_id_can_be_given_and_is_unique(store):
    assert store.open_thread("t", scope="personal", thread_id="T1") == "T1"
    with pytest.raises(sqlite3.IntegrityError):
        store.open_thread("again", scope="personal", thread_id="T1")


def test_set_goal_replaces_it_with_your_words(store, thread):
    store.set_goal(thread, "Keep one SQLite file per meter", "M2")
    assert store.get_thread(thread)["goal_text"] == "Keep one SQLite file per meter"
    store.set_goal(thread, "Same goal, reused", "M9", basis="reused")
    row = store.get_thread(thread)
    assert (row["goal_message_id"], row["goal_basis"]) == ("M9", "reused")
    with pytest.raises(UserWordsRequired):
        store.set_goal(thread, "no id", "")
    with pytest.raises(KeyError):
        store.set_goal("nope", "g", "M1")


def test_pause_close_resume(store, thread):
    store.pause_thread(thread)
    assert store.get_thread(thread)["status"] == "paused"
    store.close_thread(thread)
    assert store.get_thread(thread)["status"] == "closed"
    store.resume_thread(thread, at="2026-04-01T00:00:00.000Z")
    row = store.get_thread(thread)
    assert row["status"] == "active" and row["last_active"] == "2026-04-01T00:00:00.000Z"


def test_set_thread_status_refuses_bad_values_and_unknown_threads(store, thread):
    with pytest.raises(ValueError):
        store.set_thread_status(thread, "done")  # type: ignore[arg-type]
    with pytest.raises(KeyError):
        store.set_thread_status("nope", "paused")


def test_touch_thread_sets_last_active(store, thread):
    store.touch_thread(thread, "2026-03-05T10:00:00.000Z")
    assert store.get_thread(thread)["last_active"] == "2026-03-05T10:00:00.000Z"
    with pytest.raises(KeyError):
        store.touch_thread("nope", "2026-03-05T10:00:00.000Z")


def test_threads_filter_by_project_and_status_and_order_by_last_active(store):
    a = store.open_thread("a", scope="project:p1", project="p1")
    b = store.open_thread("b", scope="project:p1", project="p1")
    c = store.open_thread("c", scope="project:p2", project="p2")
    store.touch_thread(a, "2030-01-01T00:00:00.000Z")
    store.touch_thread(c, "2029-01-01T00:00:00.000Z")
    store.touch_thread(b, "2028-01-01T00:00:00.000Z")
    store.pause_thread(b)
    assert [t["id"] for t in store.threads()] == [a, c, b]
    assert {t["id"] for t in store.threads(project="p1")} == {a, b}
    assert [t["id"] for t in store.threads(project="p1", status="paused")] == [b]
    assert [t["id"] for t in store.threads(status="active")] == [a, c]
    with pytest.raises(ValueError):
        store.threads(status="nope")


def test_get_thread_of_nothing(store):
    assert store.get_thread("nope") is None


# --- sessions ---


def test_start_session_and_context_used(store, thread, session):
    row = store.get_session(session)
    assert (row["app"], row["project"], row["thread_id"], row["context_used"]) == ("claude-code", "energy-dash", thread, None)
    store.set_context_used(session, 41_000)
    assert store.get_session(session)["context_used"] == 41_000
    store.set_context_used(session, 0)
    assert store.get_session(session)["context_used"] == 0


def test_context_used_refuses_nonsense(store, session):
    for bad in (-1, 1.5, True, "9"):
        with pytest.raises(ValueError):
            store.set_context_used(session, bad)  # type: ignore[arg-type]
    with pytest.raises(KeyError):
        store.set_context_used("nope", 1)


def test_start_session_twice_leaves_the_first(store, session):
    store.start_session(session, app="codex", project=None, started_at="2027-01-01T00:00:00.000Z")
    row = store.get_session(session)
    assert row["app"] == "claude-code" and row["started_at"] == "2026-03-02T09:00:00.000Z"


def test_start_session_needs_a_real_thread(store):
    with pytest.raises(KeyError):
        store.start_session("S2", app="codex", project=None, thread_id="nope", started_at="2026-03-02T09:00:00.000Z")


def test_attach_session_and_list_a_threads_sessions(store, thread):
    other = store.open_thread("other", scope="personal")
    store.start_session("S2", app="codex", project=None, started_at="2026-03-03T09:00:00.000Z")
    store.start_session("S1", app="claude-code", project=None, thread_id=thread, started_at="2026-03-02T09:00:00.000Z")
    assert store.get_session("S2")["thread_id"] is None
    store.attach_session("S2", thread)
    assert [s["id"] for s in store.sessions(thread)] == ["S1", "S2"]
    store.attach_session("S2", other)
    assert [s["id"] for s in store.sessions(thread)] == ["S1"]
    with pytest.raises(KeyError):
        store.attach_session("nope", thread)
    with pytest.raises(KeyError):
        store.attach_session("S2", "nope")


# --- live decisions ---


def test_a_live_decision_carries_your_quote_and_turn(store, thread):
    did = store.add_live_decision(thread, "decided", "One SQLite file per meter", "let's do one file per meter", "M4")
    [row] = store.live_decisions(thread)
    assert row["id"] == did and row["status"] == "live" and row["kind"] == "decided"
    assert (row["line"], row["your_quote"], row["message_id"]) == ("One SQLite file per meter", "let's do one file per meter", "M4")


def test_a_decision_without_a_user_message_id_is_refused(store, thread):
    for bad in ("", None):
        with pytest.raises(UserWordsRequired):
            store.add_live_decision(thread, "decided", "x", "quote", bad)  # type: ignore[arg-type]
    with pytest.raises(UserWordsRequired):
        store.add_live_decision(thread, "decided", "x", "  ", "M1")
    assert store.live_decisions(thread, status=None) == []


def test_the_user_turn_check_refuses_an_ai_turn(open_all):
    turns = {"M1": True, "A2": False}
    s = SQLiteWorkingStore(open_all["working"], is_user_turn=lambda mid: turns.get(mid, False))
    tid = s.open_thread("t", scope="personal")
    s.add_live_decision(tid, "ruled_out", "No Postgres on the Pi", "no Postgres on the Pi", "M1")
    with pytest.raises(UserWordsRequired):
        s.add_live_decision(tid, "decided", "x", "the assistant said so", "A2")
    with pytest.raises(UserWordsRequired):
        s.add_live_decision(tid, "decided", "x", "q", "unknown")
    with pytest.raises(UserWordsRequired):
        s.open_thread("t2", scope="personal", goal_text="g", goal_message_id="A2")
    v = s.record_version(tid, "refs/northstar/v1")
    with pytest.raises(UserWordsRequired):
        s.add_feedback(v, "q", "A2")
    assert len(s.live_decisions(tid)) == 1


def test_decision_validation(store, thread):
    with pytest.raises(ValueError):
        store.add_live_decision(thread, "guessed", "x", "q", "M1")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        store.add_live_decision(thread, "decided", " ", "q", "M1")
    with pytest.raises(KeyError):
        store.add_live_decision("nope", "decided", "x", "q", "M1")


def test_decision_status_and_filtering(store, thread):
    a = store.add_live_decision(thread, "decided", "a", "qa", "M1")
    b = store.add_live_decision(thread, "constraint", "b", "qb", "M2")
    c = store.add_live_decision(thread, "ruled_out", "c", "qc", "M3")
    store.set_decision_status(b, "in_memory")
    store.set_decision_status(c, "dropped")
    assert [d["id"] for d in store.live_decisions(thread)] == [a]
    assert [d["id"] for d in store.live_decisions(thread, "in_memory")] == [b]
    assert [d["id"] for d in store.live_decisions(thread, None)] == [a, b, c]
    with pytest.raises(ValueError):
        store.set_decision_status(a, "kept")  # type: ignore[arg-type]
    with pytest.raises(KeyError):
        store.set_decision_status("nope", "dropped")
    with pytest.raises(ValueError):
        store.live_decisions(thread, "kept")


# --- versions ---


def test_versions_in_order_with_parent_turn_and_feedback(store, thread):
    v1 = store.record_version(thread, "refs/northstar/t/1", made_at_turn=3)
    v2 = store.record_version(thread, "abc123" * 10 + "abcd", artifact_kind="render", parent_id=v1, made_at_turn=5)
    f = store.add_feedback(v1, "too cluttered", "M6")
    store.add_feedback(v1, "bigger numbers", "M8")
    versions = store.versions(thread)
    assert [v["id"] for v in versions] == [v1, v2]
    assert versions[0]["artifact_kind"] == "git_ref" and versions[0]["made_at_turn"] == 3 and versions[0]["best"] == 0
    assert versions[1]["parent_id"] == v1 and versions[1]["artifact_kind"] == "render"
    assert versions[0]["feedback"] == [
        {"your_quote": "too cluttered", "message_id": "M6"},
        {"your_quote": "bigger numbers", "message_id": "M8"},
    ]
    assert versions[1]["feedback"] == [] and is_ulid(f)


def test_feedback_needs_your_turn(store, thread):
    v = store.record_version(thread, "ref")
    with pytest.raises(UserWordsRequired):
        store.add_feedback(v, "nice", "")
    with pytest.raises(UserWordsRequired):
        store.add_feedback(v, "", "M1")
    with pytest.raises(KeyError):
        store.add_feedback("nope", "q", "M1")
    assert store.versions(thread)[0]["feedback"] == []


def test_version_validation(store, thread):
    with pytest.raises(ValueError):
        store.record_version(thread, "")
    with pytest.raises(ValueError):
        store.record_version(thread, "ref", artifact_kind="video")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        store.record_version(thread, "ref", made_at_turn=-1)
    with pytest.raises(KeyError):
        store.record_version("nope", "ref")
    with pytest.raises(KeyError):
        store.record_version(thread, "ref", parent_id="nope")
    other = store.open_thread("other", scope="personal")
    parent = store.record_version(other, "ref")
    with pytest.raises(ValueError):
        store.record_version(thread, "ref", parent_id=parent)


def test_one_best_version_per_thread(store, thread):
    other = store.open_thread("other", scope="personal")
    v1 = store.record_version(thread, "r1")
    v2 = store.record_version(thread, "r2")
    w1 = store.record_version(other, "w1")
    assert store.best_version(thread) is None
    store.set_best(thread, v1)
    store.set_best(other, w1)
    assert store.best_version(thread)["id"] == v1
    store.set_best(thread, v2)
    assert store.best_version(thread)["id"] == v2
    assert [v["best"] for v in store.versions(thread)] == [0, 1]
    assert store.best_version(other)["id"] == w1
    store.set_best(thread, v2)  # setting it again changes nothing
    assert store.best_version(thread)["id"] == v2


def test_best_version_carries_its_feedback(store, thread):
    v = store.record_version(thread, "r1")
    store.add_feedback(v, "this one", "M1")
    store.set_best(thread, v)
    assert store.best_version(thread)["feedback"] == [{"your_quote": "this one", "message_id": "M1"}]


def test_set_best_refuses_a_version_of_another_thread(store, thread):
    other = store.open_thread("other", scope="personal")
    w = store.record_version(other, "w")
    with pytest.raises(ValueError):
        store.set_best(thread, w)
    with pytest.raises(KeyError):
        store.set_best(thread, "nope")


# --- side topics ---


def test_side_topics(store, thread):
    a = store.add_side_topic(thread, "Should the Pi get a UPS?", opened_at_message="M12")
    b = store.add_side_topic(thread, "Colours of the chart")
    assert [s["id"] for s in store.side_topics(thread)] == [a, b]
    assert store.side_topics(thread)[0]["opened_at_message"] == "M12"
    store.set_side_topic_status(a, "split_off")
    store.set_side_topic_status(b, "closed")
    assert store.side_topics(thread) == []
    assert [s["id"] for s in store.side_topics(thread, "split_off")] == [a]
    assert {s["id"] for s in store.side_topics(thread, None)} == {a, b}
    with pytest.raises(ValueError):
        store.set_side_topic_status(a, "gone")  # type: ignore[arg-type]
    with pytest.raises(KeyError):
        store.set_side_topic_status("nope", "closed")
    with pytest.raises(ValueError):
        store.add_side_topic(thread, " ")
    with pytest.raises(KeyError):
        store.add_side_topic("nope", "x")
    with pytest.raises(ValueError):
        store.side_topics(thread, "gone")


# --- receipts ---


def test_a_receipt_records_items_hash_and_fingerprints_not_the_text(store, session):
    fps = fingerprints(DELIVERED)
    rid = store.record_receipt(session, "facts", ["m3@1", "m4@2"], content_hash(DELIVERED), fps, at="2026-03-02T09:05:00.000Z")
    [row] = store.receipts(session)
    assert row["id"] == rid and row["kind"] == "facts" and row["at"] == "2026-03-02T09:05:00.000Z"
    assert row["items"] == ["m3@1", "m4@2"] and row["fingerprints"] == fps
    assert row["text_hash"] == content_hash(DELIVERED)
    assert DELIVERED not in str(row) and "SQLite" not in str(row)


def test_receipt_validation(store, session):
    h = content_hash("x")
    with pytest.raises(ValueError):
        store.record_receipt(session, "gossip", [], h, [])  # type: ignore[arg-type]
    for bad in ("m3", "m3@", "@1", "m3@one", "m 3@1"):
        with pytest.raises(ValueError):
            store.record_receipt(session, "facts", [bad], h, [])
    with pytest.raises(ValueError):
        store.record_receipt(session, "facts", [], "", [])
    with pytest.raises(KeyError):
        store.record_receipt("nope", "facts", [], h, [])
    assert store.receipts() == []


def test_receipts_filter_by_session_and_time(store, thread, session):
    store.start_session("S2", app="codex", project=None, started_at="2026-03-02T09:00:00.000Z")
    h = content_hash("x")
    a = store.record_receipt(session, "start_note", ["m1@1"], h, [], at="2026-03-02T09:01:00.000Z")
    b = store.record_receipt("S2", "recall", [], h, [], at="2026-03-02T09:02:00.000Z")
    c = store.record_receipt(session, "refill", ["m2@3"], h, [], at="2026-03-02T09:03:00.000Z")
    assert [r["id"] for r in store.receipts()] == [a, b, c]
    assert [r["id"] for r in store.receipts(session)] == [a, c]
    assert [r["id"] for r in store.receipts(since="2026-03-02T09:02:00.000Z")] == [b, c]
    assert [r["id"] for r in store.receipts("S2", since="2026-03-02T09:03:00.000Z")] == []


def test_receipt_default_time_is_now(store, session):
    store.record_receipt(session, "focus_note", [], content_hash("x"), [])
    assert store.receipts()[0]["at"].endswith("Z")


def test_delivered_fingerprints_across_a_sessions_receipts(store, session):
    h = content_hash("x")
    store.record_receipt(session, "facts", [], h, ["aa", "bb"])
    store.record_receipt(session, "refill", [], h, ["bb", "cc"])
    store.start_session("S2", app=None, project=None, started_at="2026-03-02T09:00:00.000Z")
    store.record_receipt("S2", "facts", [], h, ["zz"])
    assert store.delivered_fingerprints(session) == {"aa", "bb", "cc"}
    assert store.delivered_fingerprints("nope") == set()


# --- fingerprints and the echo guard (I11) ---


def test_fingerprints_are_8_word_windows():
    text = "one two three four five six seven eight nine ten"
    fps = fingerprints(text)
    assert len(fps) == 3  # words 1-8, 2-9, 3-10
    assert all(len(f) == 16 for f in fps)
    assert len(set(fps)) == 3


def test_fingerprints_ignore_case_spacing_and_punctuation():
    a = fingerprints("Readings are stored in SQLite on the Pi, one file per meter.")
    b = fingerprints("readings   ARE stored in sqlite on the pi -- one file per meter")
    assert a == b and len(a) == 5  # 12 words


def test_fingerprints_of_short_and_empty_text():
    assert fingerprints("") == [] and fingerprints("  \n ... ") == []
    short = fingerprints("only five words here today")
    assert len(short) == 1
    assert fingerprints("only five words here today") == short
    assert len(fingerprints("exactly eight words in this little test run")) == 1


def test_fingerprints_do_not_repeat():
    assert len(fingerprints("go " * 20)) == 1


def test_fingerprint_size_can_change():
    assert len(fingerprints("a b c d e", size=2)) == 4


def test_an_echo_of_delivered_text_is_caught():
    delivered = fingerprints(DELIVERED)
    assert echo_overlap(DELIVERED.split(": ")[1].upper(), delivered) == 1.0
    reply = "As noted: readings are stored in SQLite on the Pi, one file per meter."
    assert echo_overlap(reply, delivered) == pytest.approx(5 / 7)  # two new words add two new windows
    assert is_echo(reply, delivered)


def test_new_text_is_not_an_echo():
    delivered = fingerprints(DELIVERED)
    fresh = "I think we should keep one-minute readings for seven days and then average them by the hour."
    assert echo_overlap(fresh, delivered) == 0.0
    assert not is_echo(fresh, delivered)


def test_partial_overlap_is_measured_against_the_candidates_fingerprints():
    delivered = fingerprints("alpha beta gamma delta epsilon zeta eta theta")
    candidate = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu"  # 5 windows, 1 delivered
    assert echo_overlap(candidate, delivered) == pytest.approx(0.2)
    assert not is_echo(candidate, delivered)
    assert is_echo(candidate, delivered, threshold=0.2)


def test_the_threshold_is_0_6():
    assert working.ECHO_OVERLAP == 0.6 and working.FINGERPRINT_WORDS == 8
    delivered = fingerprints("a1 b2 c3 d4 e5 f6 g7 h8 i9 j10")  # 3 windows
    # 5 windows in the candidate; 3 delivered: exactly 0.6
    assert echo_overlap("a1 b2 c3 d4 e5 f6 g7 h8 i9 j10 k11 l12", delivered) == pytest.approx(3 / 5)
    assert is_echo("a1 b2 c3 d4 e5 f6 g7 h8 i9 j10 k11 l12", delivered)


def test_empty_text_has_no_overlap():
    assert echo_overlap("", ["aa"]) == 0.0
    assert not is_echo("", ["aa"])


# --- the rule: working memory is never a source ---


def test_no_method_hands_back_evidence():
    public = [n for n in dir(SQLiteWorkingStore) if not n.startswith("_")]
    assert not [n for n in public if "evidence" in n or "quote" in n.replace("your_quote", "")]
    assert "EvidenceQuote" not in vars(working)


def test_every_table_has_tenant_id_and_rows_carry_it(store, thread, open_all):
    cols = {
        r["name"]
        for t in ("work_thread", "session", "live_decision", "version", "version_feedback", "side_topic", "receipt")
        for r in open_all["working"].execute(f"PRAGMA table_info({t})")
        if r["name"] == "tenant_id"
    }
    assert cols == {"tenant_id"}
    assert store.get_thread(thread)["tenant_id"] == "local"


def test_another_tenant_sees_nothing(open_all, thread):
    other = SQLiteWorkingStore(open_all["working"], tenant_id="acme")
    assert other.get_thread(thread) is None
    assert other.threads() == []
    with pytest.raises(KeyError):
        other.add_side_topic(thread, "x")
    mine = other.open_thread("theirs", scope="personal")
    assert other.get_thread(mine)["tenant_id"] == "acme"


def test_state_survives_reopening(store_root):
    s = SQLiteWorkingStore.open(store_root)
    tid = s.open_thread("t", scope="personal")
    s.add_live_decision(tid, "decided", "x", "q", "M1")
    s.close()
    again = SQLiteWorkingStore.open(store_root)
    assert [d["line"] for d in again.live_decisions(tid)] == ["x"]
    again.close()


# --- review fixes ---


def test_resume_sets_status_and_last_active_together(store, thread):
    store.close_thread(thread)
    store.resume_thread(thread, "2026-03-05T10:00:00.000Z")
    row = store.get_thread(thread)
    assert row["status"] == "active" and row["last_active"] == "2026-03-05T10:00:00.000Z"
    with pytest.raises(KeyError):
        store.resume_thread("nope")


def test_touch_session_moves_last_active(store, session):
    store.touch_session(session, "2026-03-05T10:00:00.000Z")
    assert store.get_session(session)["last_active"] == "2026-03-05T10:00:00.000Z"
    with pytest.raises(KeyError):
        store.touch_session("nope", "2026-03-05T10:00:00.000Z")
