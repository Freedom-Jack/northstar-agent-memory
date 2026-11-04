"""The SQLite history store: idempotent appends, blobs, watermark, round trip, append-only (MEMORY-ARCHITECTURE §2.2, §3.4).

Every fixture is invented.
"""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import replace

import pytest

from northstar_agent_memory import paths
from northstar_agent_memory.core import db
from northstar_agent_memory.core.history import HistoryConflict, SQLiteHistoryStore
from northstar_agent_memory.core.ids import content_hash
from northstar_agent_memory.core.ports import HistoryStore, Watermark, WorkEvent
from northstar_agent_memory.transcript import Message, Source


@pytest.fixture
def store(store_root):
    s = SQLiteHistoryStore(store_root)
    yield s
    s.close()


def make_source(sid="S1", n=3, **kw) -> Source:
    messages = [
        Message(
            id=f"{sid}:{i}", source_id=sid, ordinal=i, speaker="user" if i % 2 == 0 else "assistant",
            text=f"turn {i} of {sid}", occurred_at=f"2026-03-02T09:{i:02d}:00+01:00",
            origin="typed" if i % 2 == 0 else "assistant_output", agent="claude-code",
            model_family=None if i % 2 == 0 else "claude", meta={"n": i},
        )
        for i in range(n)
    ]
    return Source(id=sid, kind="chat", app="claude-code", project="energy-dash", title="Dashboard", started_at="2026-03-02T09:00:00+01:00",
                  messages=messages, meta={"k": "v"}, **kw)


def raw(store, sql, args=()):
    return store.conn.execute(sql, args)


def refused(store, sql, args=()):
    with pytest.raises(sqlite3.IntegrityError):
        store.conn.execute(sql, args)


# --- the port ---------------------------------------------------------------------------------------------


def test_it_implements_the_port(store):
    assert isinstance(store, HistoryStore)


def test_it_opens_under_the_given_root(store, store_root):
    assert (store_root / "history.db").is_file()


def test_it_uses_the_data_root_by_default(isolated_home):
    with SQLiteHistoryStore() as s:
        s.add_source(make_source(), scope="personal")
    assert (paths.data_root() / "history.db").is_file()
    assert paths.data_root().is_relative_to(isolated_home)


# --- sources and messages ---------------------------------------------------------------------------------


def test_add_source_is_first_write_wins(store):
    src = make_source()
    assert store.add_source(src, scope="project:energy-dash", account="acct-1") is True
    assert store.add_source(src, scope="project:energy-dash", account="other") is False
    row = raw(store, "SELECT * FROM source WHERE id='S1'").fetchone()
    assert (row["scope"], row["account"], row["sensitivity"], row["tenant_id"]) == ("project:energy-dash", "acct-1", "normal", "local")
    assert raw(store, "SELECT COUNT(*) FROM source").fetchone()[0] == 1


def sensitivity(store, sid="S1"):
    return raw(store, "SELECT sensitivity FROM source WHERE id=?", (sid,)).fetchone()[0]


def test_a_later_add_source_may_raise_the_sensitivity(store):
    src = make_source()
    store.add_source(src, scope="personal")
    assert store.add_source(src, scope="personal", sensitivity="sensitive") is False
    assert sensitivity(store) == "sensitive"
    assert store.add_source(src, scope="personal", sensitivity="private") is False
    assert sensitivity(store) == "private"


def test_a_later_add_source_never_lowers_the_sensitivity(store):
    """Attack: re-adding a private chat with the default (or a lower) sensitivity to expose it."""
    src = make_source()
    store.add_source(src, scope="personal", sensitivity="private")
    store.add_source(src, scope="personal")  # the default is 'normal'
    assert sensitivity(store) == "private"
    store.add_source(src, scope="personal", sensitivity="sensitive")
    assert sensitivity(store) == "private"
    store.add_source_from_transcript(src, scope="personal", sensitivity="normal")
    assert sensitivity(store) == "private"


def test_a_different_scope_or_kind_is_an_error_not_silently_ignored(store):
    """Attack: re-adding a project-scoped source as personal (or as another kind) to widen who may see it."""
    src = make_source()
    store.add_source(src, scope="project:energy-dash", sensitivity="sensitive")
    with pytest.raises(HistoryConflict, match="cannot become"):
        store.add_source(src, scope="personal", sensitivity="private")
    with pytest.raises(HistoryConflict, match="cannot become"):
        store.add_source(replace(src, kind="document"), scope="project:energy-dash")
    row = raw(store, "SELECT kind, scope, sensitivity FROM source WHERE id='S1'").fetchone()
    assert (row["kind"], row["scope"], row["sensitivity"]) == ("chat", "project:energy-dash", "sensitive")


def test_a_conflicting_add_source_from_transcript_writes_nothing(store):
    src = make_source()
    store.add_source(src, scope="project:energy-dash")
    with pytest.raises(HistoryConflict):
        store.add_source_from_transcript(make_source(n=5), scope="personal")
    assert raw(store, "SELECT COUNT(*) FROM message").fetchone()[0] == 0


def test_an_unknown_sensitivity_is_refused(store):
    with pytest.raises(ValueError, match="sensitivity"):
        store.add_source(make_source(), scope="personal", sensitivity="secret")


def test_the_schema_holds_the_same_line_when_the_store_is_bypassed(store):
    store.add_source(make_source(), scope="project:energy-dash", sensitivity="sensitive")
    refused(store, "UPDATE source SET scope = 'personal' WHERE id = 'S1'")
    refused(store, "UPDATE source SET kind = 'document' WHERE id = 'S1'")
    refused(store, "UPDATE source SET sensitivity = 'normal' WHERE id = 'S1'")
    refused(store, "DELETE FROM source WHERE id = 'S1'")
    raw(store, "UPDATE source SET sensitivity = 'private' WHERE id = 'S1'")
    assert sensitivity(store) == "private"


def test_append_source_is_add_source(store):
    assert store.append_source(make_source(), scope="personal") is True
    assert store.append_source(make_source(), scope="personal") is False


def test_a_bad_scope_is_refused(store):
    with pytest.raises(sqlite3.IntegrityError):
        store.add_source(make_source(), scope="everywhere")


def test_a_message_needs_its_source(store):
    with pytest.raises(ValueError, match="unknown source"):
        store.append_message(make_source().messages[0])


def test_append_message_stores_the_text_word_for_word(store):
    store.add_source(make_source(), scope="personal")
    text = "  keep  1-minute readings\n\nfor 7 days é — \"quoted\"\t "
    m = Message(id="S1:9", source_id="S1", ordinal=9, speaker="user", text=text, origin="pasted")
    assert store.append_message(m) is True
    stored = store.get_message("S1:9")
    assert stored.message.text == text
    assert stored.content_hash == content_hash(text)
    assert stored.fidelity == "verbatim"
    assert stored.message.branch is None


def test_content_hash_ignores_spacing_but_the_text_does_not(store):
    store.add_source(make_source(n=0), scope="personal")
    store.append_message(Message(id="a", source_id="S1", ordinal=0, speaker="user", text="same  words"))
    store.append_message(Message(id="b", source_id="S1", ordinal=1, speaker="user", text="same words"))
    a, b = store.get_message("a"), store.get_message("b")
    assert a.content_hash == b.content_hash
    assert a.message.text != b.message.text


def test_fidelity_is_stored(store):
    store.add_source(make_source(n=0), scope="personal")
    m = Message(id="r", source_id="S1", ordinal=0, speaker="user", text="what I said", origin="model_reported")
    store.append_message(m, fidelity="model_reported")
    assert store.get_message("r").fidelity == "model_reported"
    with pytest.raises(sqlite3.IntegrityError):
        store.append_message(Message(id="r2", source_id="S1", ordinal=1, speaker="user", text="x"), fidelity="guess")


def test_reappending_a_message_adds_nothing(store):
    store.add_source(make_source(n=0), scope="personal")
    m = make_source().messages[0]
    assert store.append_message(m) is True
    before = store.watermark()
    assert store.append_message(m) is False
    assert store.watermark() == before
    assert raw(store, "SELECT COUNT(*) FROM message").fetchone()[0] == 1


def test_the_same_place_under_another_id_is_the_same_message(store):
    store.add_source(make_source(n=0), scope="personal")
    first = Message(id="x1", source_id="S1", ordinal=4, speaker="user", text="hello")
    again = Message(id="x2", source_id="S1", ordinal=4, speaker="user", text="hello")
    assert store.append_message(first) is True
    assert store.append_message(again) is False
    assert store.get_message("x2") is None


@pytest.mark.parametrize(
    "change",
    [
        {"text": "different words"},
        {"text": "turn 0 of S1 "},  # even a space: the text is word for word
        {"speaker": "assistant", "origin": "assistant_output", "text": "turn 0 of S1"},  # other speaker: another place, see below
        {"origin": "pasted"},
        {"agent": "codex"},
        {"model_family": "openai"},
    ],
)
def test_a_conflicting_reappend_is_refused_and_nothing_changes(store, change):
    store.add_source(make_source(n=0), scope="personal")
    original = make_source().messages[0]
    store.append_message(original)
    other = replace(original, **change)
    if change.get("speaker") == "assistant":
        # The key includes the speaker, so this is a different message at the same ordinal, which is allowed.
        other.id = "S1:0b"
        assert store.append_message(other) is True
        return
    with pytest.raises(HistoryConflict):
        store.append_message(other)
    assert store.get_message(original.id).message == original
    assert raw(store, "SELECT COUNT(*) FROM message").fetchone()[0] == 1


def test_a_conflict_under_another_id_is_refused_too(store):
    store.add_source(make_source(n=0), scope="personal")
    store.append_message(Message(id="x1", source_id="S1", ordinal=4, speaker="user", text="hello"))
    with pytest.raises(HistoryConflict):
        store.append_message(Message(id="x2", source_id="S1", ordinal=4, speaker="user", text="goodbye"))
    assert store.get_message("x2") is None


def test_a_reused_id_with_another_ordinal_is_a_conflict(store):
    store.add_source(make_source(n=0), scope="personal")
    store.append_message(Message(id="x1", source_id="S1", ordinal=4, speaker="user", text="hello"))
    with pytest.raises(HistoryConflict):
        store.append_message(Message(id="x1", source_id="S1", ordinal=5, speaker="user", text="hello"))


def test_branches_are_separate_places(store):
    store.add_source(make_source(n=0), scope="personal")
    store.append_message(Message(id="m", source_id="S1", ordinal=0, speaker="user", text="main"))
    assert store.append_message(Message(id="m-b", source_id="S1", ordinal=0, speaker="user", text="edited", branch="1")) is True
    assert store.get_message("m-b").message.branch == "1"
    assert [s.message.id for s in store.messages_for_source("S1")] == ["m", "m-b"]


def test_append_messages_counts_new_ones_and_is_idempotent(store):
    src = make_source(n=5)
    store.add_source(src, scope="personal")
    assert store.append_messages(src.messages) == 5
    assert store.append_messages(src.messages) == 0
    assert store.append_messages(src.messages[:2] + [Message(id="S1:5", source_id="S1", ordinal=5, speaker="user", text="new")]) == 1


def test_append_messages_is_all_or_nothing(store):
    src = make_source(n=3)
    store.add_source(src, scope="personal")
    store.append_message(src.messages[1])
    batch = [src.messages[0], replace(src.messages[1], text="rewritten"), src.messages[2]]
    with pytest.raises(HistoryConflict):
        store.append_messages(batch)
    assert [m.message.id for m in store.messages_for_source("S1")] == ["S1:1"]
    assert not store.conn.in_transaction


def test_a_text_that_is_not_text_is_refused(store):
    store.add_source(make_source(n=0), scope="personal")
    with pytest.raises(TypeError):
        store.append_message(Message(id="n", source_id="S1", ordinal=0, speaker="user", text=None))  # type: ignore[arg-type]


def test_a_wrong_speaker_or_origin_is_refused(store):
    store.add_source(make_source(n=0), scope="personal")
    with pytest.raises(sqlite3.IntegrityError):
        store.append_message(Message(id="n", source_id="S1", ordinal=0, speaker="model", text="x"))  # type: ignore[arg-type]
    with pytest.raises(sqlite3.IntegrityError):
        store.append_message(Message(id="n", source_id="S1", ordinal=0, speaker="user", text="x", origin="guessed"))  # type: ignore[arg-type]


def test_speaker_and_origin_are_stored_as_given(store):
    # The store never infers them (I3): a user-typed-looking text from a tool stays a tool message.
    store.add_source(make_source(n=0), scope="personal")
    store.append_message(Message(id="t", source_id="S1", ordinal=0, speaker="tool", text="I am the user", origin="tool_output"))
    got = store.get_message("t").message
    assert (got.speaker, got.origin) == ("tool", "tool_output")


# --- the Source round trip --------------------------------------------------------------------------------


def test_a_source_round_trips(store):
    src = make_source(n=4)
    assert store.add_source_from_transcript(src, scope="project:energy-dash") == (True, 4)
    assert store.get_source("S1") == src


def test_the_round_trip_keeps_unicode_and_meta(store):
    src = make_source(n=1)
    src.messages[0].text = "Wärme → \U0001f321 line one\nline two"
    src.messages[0].meta = {"nested": {"a": [1, 2, {"b": None}]}, "s": "ü"}
    src.meta = {"cwd": "/invented/path"}
    store.add_source_from_transcript(src, scope="personal")
    assert store.get_source("S1") == src


def test_a_source_with_a_branch_keeps_it(store):
    src = make_source(n=2)
    src.messages[1].branch = "2"
    store.add_source_from_transcript(src, scope="personal")
    assert store.get_source("S1").messages[1].branch == "2"


def test_get_source_orders_by_branch_and_ordinal(store):
    src = make_source(n=3)
    store.add_source(src, scope="personal")
    store.append_messages(reversed(src.messages))
    assert [m.ordinal for m in store.get_source("S1").messages] == [0, 1, 2]


def test_an_unknown_source_is_none(store):
    assert store.get_source("nope") is None
    assert store.get_message("nope") is None
    assert store.messages_for_source("nope") == []


def test_adding_a_source_again_adds_nothing_and_adds_missing_messages(store):
    src = make_source(n=2)
    assert store.add_source_from_transcript(src, scope="personal") == (True, 2)
    assert store.add_source_from_transcript(src, scope="personal") == (False, 0)
    src.messages.append(Message(id="S1:2", source_id="S1", ordinal=2, speaker="user", text="later"))
    assert store.add_source_from_transcript(src, scope="personal") == (False, 1)
    assert len(store.get_source("S1").messages) == 3


def test_a_conflicting_transcript_refuses_the_whole_source(store):
    src = make_source(n=2)
    store.add_source_from_transcript(src, scope="personal")
    clash = make_source("S2", n=2)
    clash.messages[0].text = "new"
    other = make_source(n=2)
    other.messages[1].text = "rewritten"
    with pytest.raises(HistoryConflict):
        store.add_source_from_transcript(other, scope="personal")
    assert store.get_source("S1") == src


def test_a_source_that_fails_midway_leaves_nothing(store):
    src = make_source("S9", n=3)
    src.messages[2].speaker = "robot"  # type: ignore[assignment]
    with pytest.raises(sqlite3.IntegrityError):
        store.add_source_from_transcript(src, scope="personal")
    assert store.get_source("S9") is None
    assert store.watermark() == Watermark(0, 0)


def test_many_sources_in_one_transaction(store):
    sources = [make_source(f"S{i}", n=4) for i in range(50)]
    with store.batch():
        assert store.conn.in_transaction
        for s in sources:
            store.add_source_from_transcript(s, scope="personal")
    assert not store.conn.in_transaction
    assert store.watermark().message_seq == 200
    assert store.get_source("S37") == sources[37]


def test_a_batch_that_fails_rolls_everything_back(store):
    store.add_source_from_transcript(make_source("S0"), scope="personal")
    with pytest.raises(HistoryConflict):
        with store.batch():
            for i in range(1, 5):
                store.add_source_from_transcript(make_source(f"S{i}"), scope="personal")
            bad = make_source("S0")
            bad.messages[0].text = "rewritten"
            store.add_source_from_transcript(bad, scope="personal")
    assert [r[0] for r in raw(store, "SELECT id FROM source")] == ["S0"]
    assert not store.conn.in_transaction


def test_a_batch_commits_once(store):
    with store.batch():
        store.add_source_from_transcript(make_source("A"), scope="personal")
        # A second connection sees nothing until the batch commits.
        other = sqlite3.connect(db.store_path("history", store.root))
        assert other.execute("SELECT COUNT(*) FROM source").fetchone()[0] == 0
        other.close()
    other = sqlite3.connect(db.store_path("history", store.root))
    assert other.execute("SELECT COUNT(*) FROM source").fetchone()[0] == 1
    other.close()


def test_a_reopened_store_has_the_same_data(store_root):
    with SQLiteHistoryStore(store_root) as a:
        a.add_source_from_transcript(make_source(), scope="personal")
    with SQLiteHistoryStore(store_root) as b:
        assert b.get_source("S1") == make_source()


# --- watermark and reading --------------------------------------------------------------------------------


def test_watermark_starts_at_zero(store):
    assert store.watermark() == Watermark(0, 0)
    assert store.messages_since(0) == []


def test_watermark_counts_up_with_each_new_message(store):
    src = make_source(n=3)
    store.add_source(src, scope="personal")
    seen = []
    for m in src.messages:
        store.append_message(m)
        seen.append(store.watermark().message_seq)
    assert seen == [1, 2, 3]


def test_a_source_with_no_messages_does_not_move_the_watermark(store):
    store.add_source(make_source(n=0), scope="personal")
    assert store.watermark() == Watermark(0, 0)


def test_messages_since_is_in_seq_order_after_the_given_seq(store):
    for sid in ("A", "B"):
        store.add_source_from_transcript(make_source(sid, n=3), scope="personal")
    everything = store.messages_since(0)
    assert [s.seq for s in everything] == [1, 2, 3, 4, 5, 6]
    assert [s.message.id for s in everything] == ["A:0", "A:1", "A:2", "B:0", "B:1", "B:2"]
    assert [s.message.id for s in store.messages_since(4)] == ["B:1", "B:2"]
    assert store.messages_since(6) == []


def test_messages_since_takes_a_watermark_and_a_limit(store):
    store.add_source_from_transcript(make_source("A", n=5), scope="personal")
    mark = store.watermark()
    store.add_source_from_transcript(make_source("B", n=2), scope="personal")
    assert [s.message.id for s in store.messages_since(mark)] == ["B:0", "B:1"]
    assert len(store.messages_since(0, limit=3)) == 3
    assert store.messages_since(0, limit=3)[-1].seq == 3


def test_seq_follows_arrival_not_ordinal(store):
    src = make_source(n=3)
    store.add_source(src, scope="personal")
    for m in reversed(src.messages):
        store.append_message(m)
    assert [s.message.ordinal for s in store.messages_since(0)] == [2, 1, 0]
    assert [m.message.ordinal for m in store.messages_for_source("S1")] == [0, 1, 2]


def test_a_refused_append_does_not_use_up_a_seq(store):
    src = make_source(n=2)
    store.add_source(src, scope="personal")
    store.append_message(src.messages[0])
    with pytest.raises(HistoryConflict):
        store.append_message(replace(src.messages[0], text="x"))
    store.append_message(src.messages[1])
    assert [s.seq for s in store.messages_since(0)] == [1, 2]


def test_work_events_have_their_own_counter(store):
    store.add_source(make_source(n=1), scope="personal")
    store.append_message(make_source(n=1).messages[0])
    store.append_work_event(WorkEvent(id="w1", source_id="S1", kind="commit", ref="a41c9e0", evidence="strong"))
    store.append_work_event(WorkEvent(id="w2", source_id="S1", kind="file_version", ref="f.py@abc", evidence="weak"))
    assert store.watermark() == Watermark(message_seq=1, work_event_seq=2)


# --- work events and blobs --------------------------------------------------------------------------------


def test_a_work_event_is_idempotent_and_conflicts_are_refused(store):
    store.add_source(make_source(n=0), scope="personal")
    ev = WorkEvent(id="w1", source_id="S1", kind="commit", ref="a41c9e0", evidence="strong",
                   occurred_at="2026-03-02T10:00:00Z", meta={"files": 3})
    assert store.append_work_event(ev) is True
    assert store.append_work_event(ev) is False
    with pytest.raises(HistoryConflict):
        store.append_work_event(WorkEvent(id="w1", source_id="S1", kind="commit", ref="other", evidence="strong"))
    with pytest.raises(HistoryConflict):
        store.append_work_event(WorkEvent(id="w1", source_id="S1", kind="commit", ref="a41c9e0", evidence="weak"))
    row = raw(store, "SELECT * FROM work_event WHERE id='w1'").fetchone()
    assert (row["ref"], row["evidence"], row["occurred_at"], row["meta"]) == ("a41c9e0", "strong", "2026-03-02T10:00:00Z", '{"files": 3}')


def test_a_work_event_needs_its_source_and_its_snapshot(store):
    with pytest.raises(ValueError, match="unknown source"):
        store.append_work_event(WorkEvent(id="w1", source_id="S1", kind="commit", ref="r", evidence="weak"))
    store.add_source(make_source(n=0), scope="personal")
    with pytest.raises(ValueError, match="unknown snapshot"):
        store.append_work_event(WorkEvent(id="w1", source_id="S1", kind="render", ref="r", evidence="weak", snapshot_sha256="0" * 64))
    with pytest.raises(sqlite3.IntegrityError):
        store.append_work_event(WorkEvent(id="w2", source_id="S1", kind="screenshot", ref="r", evidence="weak"))  # type: ignore[arg-type]


def test_a_work_event_points_at_its_blob(store):
    store.add_source(make_source(n=0), scope="personal")
    sha = store.put_blob(b"<svg/>", "image/svg+xml")
    store.append_work_event(WorkEvent(id="w1", source_id="S1", kind="diagram", ref="d1", evidence="medium", snapshot_sha256=sha))
    assert raw(store, "SELECT snapshot_sha256 FROM work_event").fetchone()[0] == sha
    assert store.get_blob(sha) == b"<svg/>"


def test_put_blob_returns_the_sha256_and_writes_the_file_once(store, store_root):
    data = b"snapshot bytes \x00\xff"
    sha = store.put_blob(data, "application/octet-stream")
    assert sha == hashlib.sha256(data).hexdigest()
    path = db.blob_path(sha, store_root)
    assert path == store_root / "blobs" / sha[:2] / sha[2:4] / sha
    assert path.read_bytes() == data
    assert store.get_blob(sha) == data


def test_blobs_are_deduplicated(store, store_root):
    a = store.put_blob(b"same", "text/plain")
    mtime = db.blob_path(a, store_root).stat().st_mtime_ns
    b = store.put_blob(b"same", "text/other")
    assert a == b
    assert raw(store, "SELECT COUNT(*) FROM blob").fetchone()[0] == 1
    assert raw(store, "SELECT media_type, size FROM blob").fetchone()[:] == ("text/plain", 4)  # first write wins
    assert db.blob_path(a, store_root).stat().st_mtime_ns == mtime  # the file was not rewritten
    assert len([p for p in (store_root / "blobs").rglob("*") if p.is_file()]) == 1


def test_different_blobs_are_kept_apart(store):
    a, b = store.put_blob(b"one"), store.put_blob(b"two")
    assert a != b
    assert (store.get_blob(a), store.get_blob(b)) == (b"one", b"two")


def test_an_empty_blob_is_a_blob(store):
    sha = store.put_blob(b"")
    assert sha == hashlib.sha256(b"").hexdigest()
    assert store.get_blob(sha) == b""


def test_an_unknown_blob_is_none(store):
    assert store.get_blob("0" * 64) is None


def test_a_blob_whose_file_is_missing_is_rewritten_by_the_next_put(store, store_root):
    sha = store.put_blob(b"data")
    db.blob_path(sha, store_root).unlink()
    assert store.get_blob(sha) is None
    assert store.put_blob(b"data") == sha
    assert store.get_blob(sha) == b"data"


def test_a_corrupt_blob_is_an_error_not_data(store, store_root):
    sha = store.put_blob(b"data")
    db.blob_path(sha, store_root).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="corrupt"):
        store.get_blob(sha)


def test_no_blob_temp_files_are_left_behind(store, store_root):
    store.put_blob(b"x" * 1000)
    assert [p.name for p in (store_root / "blobs").rglob("*.tmp")] == []


def test_a_blob_row_cannot_be_changed_or_deleted(store):
    sha = store.put_blob(b"data")
    refused(store, "UPDATE blob SET media_type='x' WHERE sha256=?", (sha,))
    refused(store, "DELETE FROM blob WHERE sha256=?", (sha,))


# --- reconciliation ---------------------------------------------------------------------------------------


def test_every_reconciliation_outcome_is_recorded(store):
    store.add_source(make_source(n=0), scope="personal")
    store.append_message(Message(id="r", source_id="S1", ordinal=0, speaker="user", text="as reported", origin="model_reported"),
                         fidelity="model_reported")
    store.append_message(Message(id="v", source_id="S1", ordinal=1, speaker="user", text="as typed"), fidelity="reconciled")
    a = store.record_reconciliation("r", "v", "hash", 1.0, "matched")
    b = store.record_reconciliation("r", None, "none", None, "could_not_confirm")
    assert a != b
    rows = raw(store, "SELECT * FROM reconciliation ORDER BY id").fetchall()
    assert [(r["method"], r["outcome"], r["verbatim_message_id"]) for r in rows] == [
        ("hash", "matched", "v"), ("none", "could_not_confirm", None)]


def test_a_reconciliation_needs_known_messages_and_a_match_needs_a_partner(store):
    store.add_source(make_source(n=1), scope="personal")
    store.append_messages(make_source(n=1).messages)
    with pytest.raises(ValueError, match="unknown message"):
        store.record_reconciliation("missing", None, "none", None, "reported_only")
    with pytest.raises(ValueError, match="unknown message"):
        store.record_reconciliation("S1:0", "missing", "hash", 1.0, "matched")
    with pytest.raises(sqlite3.IntegrityError):
        store.record_reconciliation("S1:0", None, "hash", 1.0, "matched")


def test_the_reported_message_is_not_edited_by_reconciliation(store):
    store.add_source(make_source(n=0), scope="personal")
    reported = Message(id="r", source_id="S1", ordinal=0, speaker="user", text="as reported", origin="model_reported")
    store.append_message(reported, fidelity="model_reported")
    store.append_message(Message(id="v", source_id="S1", ordinal=1, speaker="user", text="as typed"))
    store.record_reconciliation("r", "v", "fuzzy", 0.93, "matched")
    got = store.get_message("r")
    assert got.message == reported and got.fidelity == "model_reported"


# --- append-only, through SQL -----------------------------------------------------------------------------


@pytest.fixture
def filled(store):
    src = make_source(n=2)
    store.add_source_from_transcript(src, scope="personal")
    store.append_work_event(WorkEvent(id="w1", source_id="S1", kind="commit", ref="a41c9e0", evidence="strong"))
    store.record_reconciliation("S1:0", "S1:1", "hash", 1.0, "matched")
    return store


def test_sql_cannot_update_a_message(filled):
    refused(filled, "UPDATE message SET text='changed' WHERE id='S1:0'")
    refused(filled, "UPDATE message SET speaker='assistant' WHERE id='S1:0'")
    refused(filled, "UPDATE message SET origin='pasted' WHERE id='S1:0'")
    refused(filled, "UPDATE message SET occurred_at=NULL WHERE id='S1:0'")
    assert filled.get_message("S1:0").message == make_source().messages[0]


def test_sql_cannot_delete_without_a_purge_authorization(filled):
    refused(filled, "DELETE FROM message WHERE id='S1:0'")
    refused(filled, "DELETE FROM message")
    refused(filled, "DELETE FROM work_event WHERE id='w1'")
    refused(filled, "DELETE FROM reconciliation")
    assert raw(filled, "SELECT COUNT(*) FROM message").fetchone()[0] == 2


def test_an_authorization_for_another_row_does_not_open_this_one(filled):
    raw(filled, "INSERT INTO purge_authorization (purge_id, target_table, target_id, authorized_at) VALUES ('p', 'message', 'S1:1', 'now')")
    refused(filled, "DELETE FROM message WHERE id='S1:0'")
    raw(filled, "INSERT INTO purge_authorization (purge_id, target_table, target_id, authorized_at) VALUES ('p', 'work_event', 'S1:0', 'now')")
    refused(filled, "DELETE FROM message WHERE id='S1:0'")


def test_an_authorized_row_can_be_deleted_by_sql_but_never_edited(filled):
    raw(filled, "DELETE FROM reconciliation WHERE 0")  # no-op, no authorization needed for zero rows
    filled.authorize_purge("p1", [("reconciliation", filled.conn.execute("SELECT id FROM reconciliation").fetchone()[0])])
    raw(filled, "DELETE FROM reconciliation")
    filled.authorize_purge("p1", [("message", "S1:1")])
    refused(filled, "UPDATE message SET text='x' WHERE id='S1:1'")  # text is frozen even for a purge
    raw(filled, "DELETE FROM message WHERE id='S1:1'")
    assert [m.message.id for m in filled.messages_for_source("S1")] == ["S1:0"]


def test_the_watermark_survives_a_purge(filled):
    before = filled.watermark()
    filled.authorize_purge("p", [("reconciliation", filled.conn.execute("SELECT id FROM reconciliation").fetchone()[0]), ("message", "S1:1")])
    filled.purge_authorized("p")
    assert filled.watermark() == before
    filled.append_message(Message(id="S1:7", source_id="S1", ordinal=7, speaker="user", text="after"))
    assert filled.watermark().message_seq == before.message_seq + 1


def test_the_purge_authorization_log_itself_is_append_only(filled):
    filled.authorize_purge("p", [("message", "S1:0")])
    refused(filled, "UPDATE purge_authorization SET target_id='x'")
    refused(filled, "DELETE FROM purge_authorization")


# --- the history.db half of a purge -----------------------------------------------------------------------


def test_purge_authorized_deletes_only_what_was_authorized(filled, store_root):
    sha = filled.put_blob(b"secret snapshot")
    keep = filled.put_blob(b"other snapshot")
    rid = filled.conn.execute("SELECT id FROM reconciliation").fetchone()[0]
    filled.authorize_purge("p1", [("reconciliation", rid), ("message", "S1:0"), ("message", "S1:1"), ("blob", sha)])
    assert filled.purge_authorized("p1") == 4
    assert filled.messages_for_source("S1") == []
    assert filled.get_source("S1") is not None
    assert filled.get_blob(sha) is None and not db.blob_path(sha, store_root).exists()
    assert filled.get_blob(keep) == b"other snapshot"
    assert raw(filled, "SELECT COUNT(*) FROM work_event").fetchone()[0] == 1
    assert filled.purge_authorized("p1") == 0  # running it again deletes nothing more


def test_authorize_purge_is_idempotent_and_checks_the_table(filled):
    filled.authorize_purge("p", [("message", "S1:0"), ("message", "S1:0")])
    filled.authorize_purge("p", [("message", "S1:0")])
    assert raw(filled, "SELECT COUNT(*) FROM purge_authorization").fetchone()[0] == 1
    with pytest.raises(sqlite3.IntegrityError):
        filled.authorize_purge("p", [("memory_item", "x")])


def test_a_purge_that_would_orphan_a_row_deletes_nothing(filled):
    filled.authorize_purge("p", [("message", "S1:0")])  # a reconciliation still points at it
    with pytest.raises(sqlite3.IntegrityError):
        filled.purge_authorized("p")
    assert len(filled.messages_for_source("S1")) == 2
    assert not filled.conn.in_transaction


def test_a_blob_a_work_event_keeps_cannot_be_purged_alone(store):
    store.add_source(make_source(n=0), scope="personal")
    sha = store.put_blob(b"snap")
    store.append_work_event(WorkEvent(id="w1", source_id="S1", kind="render", ref="r", evidence="weak", snapshot_sha256=sha))
    store.authorize_purge("p", [("blob", sha)])
    with pytest.raises(sqlite3.IntegrityError):
        store.purge_authorized("p")
    assert store.get_blob(sha) == b"snap"


# --- tenant and PRAGMAs -----------------------------------------------------------------------------------


def test_every_row_carries_the_tenant(store):
    store.add_source_from_transcript(make_source(n=1), scope="personal")
    store.append_work_event(WorkEvent(id="w", source_id="S1", kind="commit", ref="r", evidence="weak"))
    store.put_blob(b"x")
    for table in ("source", "message", "work_event", "blob"):
        assert {r[0] for r in raw(store, f"SELECT tenant_id FROM {table}")} == {"local"}


def test_another_tenant_is_stamped_on_every_row(store_root):
    with SQLiteHistoryStore(store_root, tenant_id="acme") as s:
        s.add_source_from_transcript(make_source(n=1), scope="personal")
        assert {r[0] for r in s.conn.execute("SELECT tenant_id FROM message")} == {"acme"}


def test_recorded_at_is_set_by_the_store(store):
    store.add_source_from_transcript(make_source(n=1), scope="personal")
    assert raw(store, "SELECT recorded_at FROM message").fetchone()[0].endswith("Z")


# --- review fixes ---------------------------------------------------------------------------------------------


def test_a_failed_call_inside_a_batch_leaves_no_partial_rows(store):
    src = make_source("S1", 3)
    with store.batch():
        store.add_source(src, scope="personal")
        store.append_message(src.messages[0])
        bad = [src.messages[1], replace(src.messages[0], text="rewritten")]
        with pytest.raises(HistoryConflict):
            store.append_messages(bad)  # caught: the batch goes on
        assert store.get_message("S1:1") is None
        with pytest.raises(HistoryConflict):
            store.add_source_from_transcript(
                Source(id="S2", messages=[Message(id="S2:0", source_id="S2", ordinal=0, speaker="user", text="a"),
                                          Message(id="S2:0", source_id="S2", ordinal=0, speaker="user", text="b")]),
                scope="personal",
            )
        assert store.get_source("S2") is None
    assert [m.message.id for m in store.messages_since(0)] == ["S1:0"]


def test_purge_inside_a_batch_is_refused(store):
    sha = store.put_blob(b"x")
    store.authorize_purge("p1", [("blob", sha)])
    with store.batch():
        with pytest.raises(RuntimeError):
            store.purge_authorized("p1")
    assert store.get_blob(sha) == b"x"
