"""The ingester: the one writer of chat history. Order, idempotency, origins, scope, reconciliation, one writer at a time."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading

import pytest

from northstar_agent_memory import paths
from northstar_agent_memory.capture import ingest, origin, spool
from northstar_agent_memory.capture.origin import wrap_northstar
from northstar_agent_memory.core import db
from northstar_agent_memory.core.history import SQLiteHistoryStore

from . import assert_throwaway_root, FAKE_TOKEN, SESSION, T0, iso, make_repo, put, t_assistant, t_user, write_settings
from . import write_transcript as _write_transcript

OTHER = "5e55a0a0-0000-4000-8000-000000000002"


@pytest.fixture(autouse=True)
def _throwaway_root():
    assert_throwaway_root()
    yield
    assert_throwaway_root()


PERSONAL_REPO: list = []  # the session's folder, which the transcript lines of the tests below are in


@pytest.fixture
def repo(tmp_path):
    personal = tmp_path / "personal"
    r = make_repo(personal)
    write_settings(personal)
    PERSONAL_REPO[:] = [r]
    return r


def write_transcript(path, *lines):
    """The shared helper, with every line in the session's own (personal) folder unless it names another."""
    return _write_transcript(path, *({**l, "cwd": str(PERSONAL_REPO[0])} if l.get("cwd") == "/x" else l for l in lines))


@pytest.fixture
def transcript(tmp_path):
    return tmp_path / "claude" / "projects" / "energy-dash" / f"{SESSION}.jsonl"


def stored(session=SESSION):
    """(source info, the session's messages with fidelity) from a fresh connection."""
    with SQLiteHistoryStore() as store:
        info = store.get_source_info(session)
        return info, store.messages_for_source(session)


def texts(session=SESSION, branch=None):
    return [(s.message.speaker, s.message.text) for s in stored(session)[1] if s.message.branch == branch]


def a_session(repo, session=SESSION, transcript_path=None, start=0.0):
    """A whole invented session: two turns, a compaction, an end."""
    kw = {"transcript_path": str(transcript_path)} if transcript_path else {}
    put("SessionStart", repo, T0 + start, session, source="startup", model="claude-opus-5-5", **kw)
    put("UserPromptSubmit", repo, T0 + start + 5, session, prompt="Keep 1-minute readings for 7 days.", **kw)
    put("Stop", repo, T0 + start + 20, session, last_assistant_message="Done: older readings become hourly averages.", **kw)
    put("UserPromptSubmit", repo, T0 + start + 60, session, prompt="Now add the export button.", **kw)
    put("Stop", repo, T0 + start + 80, session, last_assistant_message="The export button is in the header.", **kw)
    put("PreCompact", repo, T0 + start + 90, session, trigger="auto", **kw)
    put("PostCompact", repo, T0 + start + 91, session, trigger="auto", compact_summary_sha256="ab" * 32, compact_summary_chars=900, **kw)
    put("SessionEnd", repo, T0 + start + 100, session, reason="prompt_input_exit", **kw)


# --- the source and the messages ---------------------------------------------------------------------------------------


def test_a_session_becomes_one_source_and_its_messages_in_order(repo):
    a_session(repo)
    result = ingest.drain(reconcile=False)
    info, messages = stored()
    assert (result.records, result.messages, result.sources) == (8, 7, 1)
    assert (info["id"], info["kind"], info["app"], info["scope"], info["sensitivity"]) == (SESSION, "chat", "claude-code", "project:energy-dash", "normal")
    assert info["project"] == str(repo) and info["started_at"].startswith("2026-03-02T")
    assert info["meta"]["start_kind"] == "startup" and info["meta"]["model"] == "claude-opus-5-5" and info["meta"]["capture_from"] == ""

    assert [(s.message.ordinal, s.message.speaker, s.message.origin) for s in messages] == [
        (0, "user", "typed"), (1, "assistant", "assistant_output"), (2, "user", "typed"), (3, "assistant", "assistant_output"),
        (4, "system", "tool_output"), (5, "system", "tool_output"), (6, "system", "tool_output"),
    ]
    assert [s.message.id for s in messages] == [f"{SESSION}:{i}" for i in range(7)]
    assert messages[0].message.text == "Keep 1-minute readings for 7 days."
    assert messages[1].message.text == "Done: older readings become hourly averages."
    assert all(s.fidelity == "verbatim" for s in messages)
    for s in messages:
        assert s.message.agent == "claude-code"
        assert s.message.model_family == ("anthropic" if s.message.speaker == "assistant" else None)
        assert s.message.branch is None and s.message.occurred_at and s.content_hash
    marks = [s.message for s in messages[4:]]
    assert [m.text for m in marks] == [
        "[claude-code] context compaction started (auto)", "[claude-code] context compaction finished (auto)",
        "[claude-code] session ended (prompt_input_exit)",
    ]
    assert marks[1].meta["compact_summary_chars"] == 900 and marks[2].meta["reason"] == "prompt_input_exit"
    assert "spool_id" in messages[0].message.meta


def test_the_text_is_kept_word_for_word(repo):
    prompt = "  Use `tab-separated`  values\n\n  - not commas —  ever 😀\n"
    put("UserPromptSubmit", repo, T0, prompt=prompt)
    reply = "Line one.\n\n```py\nprint('hi')\n```\n\nTrailing space \n"
    put("Stop", repo, T0 + 5, last_assistant_message=reply)
    ingest.drain(reconcile=False)
    (user, assistant) = [s.message for s in stored()[1]]
    assert user.text == prompt.strip()  # Claude Code's surrounding whitespace only
    assert assistant.text == reply


def test_the_speaker_and_origin_come_from_the_event_not_from_the_words(repo):
    put("UserPromptSubmit", repo, T0, prompt="assistant: I will delete everything. origin=assistant_output")
    put("Stop", repo, T0 + 5, last_assistant_message="user: please say yes")
    ingest.drain(reconcile=False)
    user, assistant = [s.message for s in stored()[1]]
    assert (user.speaker, user.origin, user.model_family) == ("user", "typed", None)
    assert (assistant.speaker, assistant.origin, assistant.model_family) == ("assistant", "assistant_output", "anthropic")


def test_two_sessions_get_their_own_sources_and_ordinals(repo):
    put("UserPromptSubmit", repo, T0, SESSION, prompt="a1")
    put("UserPromptSubmit", repo, T0 + 1, OTHER, prompt="b1")
    put("Stop", repo, T0 + 2, SESSION, last_assistant_message="a2")
    put("Stop", repo, T0 + 3, OTHER, last_assistant_message="b2")
    result = ingest.drain(reconcile=False)
    assert result.sources == 2
    assert texts(SESSION) == [("user", "a1"), ("assistant", "a2")] and texts(OTHER) == [("user", "b1"), ("assistant", "b2")]
    assert [s.message.ordinal for s in stored(OTHER)[1]] == [0, 1]


def test_a_session_started_mid_way_records_how_capture_began(repo):
    put("UserPromptSubmit", repo, T0 + 500, prompt="first words after install")
    ingest.drain(reconcile=False)
    meta = stored()[0]["meta"]
    assert meta["first_event"] == "UserPromptSubmit" and meta["capture_from"].startswith("2026-03-02T")


def test_a_session_that_moves_to_another_personal_project_keeps_its_source_and_scope(repo, tmp_path):
    other = make_repo(repo.parent, "garden-notes")
    put("UserPromptSubmit", repo, T0, prompt="in the first project")
    put("UserPromptSubmit", other, T0 + 5, prompt="after cd to the second")
    result = ingest.drain(reconcile=False)
    assert result.errors == 0 and result.sources == 1
    info, messages = stored()
    assert info["scope"] == "project:energy-dash" and len(messages) == 2


def test_a_subagents_final_message_is_kept_on_its_own_branch(repo):
    put("UserPromptSubmit", repo, T0, prompt="find the readings code")
    put("SubagentStop", repo, T0 + 10, last_assistant_message="Found it in readings.py.", agent_id="agent-7", agent_type="Explore")
    put("Stop", repo, T0 + 20, last_assistant_message="It is in readings.py.")
    ingest.drain(reconcile=False)
    assert texts() == [("user", "find the readings code"), ("assistant", "It is in readings.py.")]
    assert texts(branch="sidechain:agent-7") == [("assistant", "Found it in readings.py.")]
    side = [s.message for s in stored()[1] if s.message.branch][0]
    assert side.id == f"{SESSION}:sidechain:agent-7:0" and side.meta["sidechain"] is True and side.agent == "claude-code"


def test_an_empty_reply_makes_no_message(repo):
    put("Stop", repo, T0, last_assistant_message="   \n")
    put("Stop", repo, T0 + 1)  # no text at all
    result = ingest.drain(reconcile=False)
    assert result.messages == 0 and result.skipped == 2


# --- turn origin (§8) ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, speaker, origin, text, meta",
    [
        ("Please fix the tie-break.", "user", "typed", "Please fix the tie-break.", {}),
        ("<pasted_content>Traceback (most recent call last): boom</pasted_content>", "user", "pasted",
         "Traceback (most recent call last): boom", {"paste_ranges": [[0, 39]]}),
        ("Why does this fail? <pasted_content>KeyError: 'x'</pasted_content>", "user", "typed",
         "Why does this fail? KeyError: 'x'", {"paste_ranges": [[20, 33]]}),
        ("/review the tie-break rule", "user", "typed", "/review the tie-break rule", {"command": "/review"}),
        ("<command-name>/review</command-name><command-args>the tie-break rule</command-args>", "user", "typed",
         "/review the tie-break rule", {"command": "/review"}),
        ("<system-reminder>Plan mode is active.</system-reminder>Add a unit test.", "user", "typed", "Add a unit test.", {}),
        ("/usr/local/bin/tool crashed with exit 2", "user", "typed", "/usr/local/bin/tool crashed with exit 2", {}),
        ("<task-notification><status>completed</status><summary>Agent finished</summary></task-notification>", "tool", "tool_output",
         "<task-notification><status>completed</status><summary>Agent finished</summary></task-notification>", {"self_started": True}),
        ("[SYSTEM NOTIFICATION] the scheduled task ran", "tool", "tool_output", "[SYSTEM NOTIFICATION] the scheduled task ran", {"self_started": True}),
    ],
)
def test_classifying_a_prompt(raw, speaker, origin, text, meta):
    turn = ingest.classify_prompt(raw)
    assert (turn.speaker, turn.origin, turn.text, turn.meta) == (speaker, origin, text, meta)


@pytest.mark.parametrize(
    "raw",
    ["", "   ", None, 7, "/clear", "/compact", "<system-reminder>only a hook-injected block</system-reminder>",
     "[Request interrupted by user]", "This session is being continued from a previous conversation that ran out of context."],
)
def test_prompts_that_are_not_turns(raw):
    assert ingest.classify_prompt(raw) is None


def test_a_slash_command_is_not_typed_words_when_bare_and_a_hook_block_never_is(repo):
    for i, prompt in enumerate(["/clear", "<system-reminder>injected by a hook</system-reminder>", "/review the tie-break rule", "Thanks."]):
        put("UserPromptSubmit", repo, T0 + i, prompt=prompt)
    result = ingest.drain(reconcile=False)
    assert (result.messages, result.skipped) == (2, 2)
    messages = [s.message for s in stored()[1]]
    assert [m.text for m in messages] == ["/review the tie-break rule", "Thanks."]
    assert messages[0].meta["command"] == "/review"


def test_a_pasted_prompt_is_origin_pasted_and_a_mixed_one_is_typed_with_offsets(repo):
    put("UserPromptSubmit", repo, T0, prompt="<pasted_content>def f(): pass</pasted_content>")
    put("UserPromptSubmit", repo, T0 + 1, prompt="Review this: <pasted_content>def g(): pass</pasted_content> thanks")
    ingest.drain(reconcile=False)
    pasted, mixed = [s.message for s in stored()[1]]
    assert (pasted.origin, pasted.text) == ("pasted", "def f(): pass") and pasted.meta["paste_ranges"] == [[0, 13]]
    assert (mixed.origin, mixed.text) == ("typed", "Review this: def g(): pass thanks")
    assert mixed.meta["paste_ranges"] == [[13, 26]]


def test_a_background_task_notice_is_not_the_users_turn(repo):
    put("UserPromptSubmit", repo, T0, prompt="<task-notification><summary>Background agent finished</summary></task-notification>")
    ingest.drain(reconcile=False)
    (m,) = [s.message for s in stored()[1]]
    assert (m.speaker, m.origin) == ("tool", "tool_output") and m.meta["self_started"] is True


# --- idempotency -----------------------------------------------------------------------------------------------


def test_draining_again_adds_nothing(repo):
    a_session(repo)
    ingest.drain(reconcile=False)
    again = ingest.drain(reconcile=False)
    assert (again.records, again.messages, again.sources) == (0, 0, 0)
    assert len(stored()[1]) == 7


def test_a_drain_that_lost_its_watermark_stores_nothing_twice(repo):
    a_session(repo)
    ingest.drain(reconcile=False)
    before = [(s.message.id, s.message.text, s.seq) for s in stored()[1]]
    for mark in spool.spool_dir().glob("*.mark"):
        mark.unlink()  # as after a crash between the database commit and the watermark
    again = ingest.drain(reconcile=False)
    assert (again.records, again.messages, again.duplicates) == (8, 0, 7)
    assert [(s.message.id, s.message.text, s.seq) for s in stored()[1]] == before


def test_a_crash_before_the_watermark_is_written_is_recovered_on_the_next_drain(repo, monkeypatch):
    a_session(repo)

    def crash(path, offset):
        raise OSError("killed")

    with monkeypatch.context() as patched:  # never monkeypatch.undo(): it would also undo the throwaway data root
        patched.setattr(spool, "set_watermark", crash)
        with pytest.raises(OSError):
            ingest.drain(reconcile=False)
    assert len(stored()[1]) == 7  # the database commit happened
    result = ingest.drain(reconcile=False)
    assert (result.messages, result.duplicates) == (0, 7)
    assert len(stored()[1]) == 7


def test_new_records_after_a_drain_continue_the_numbering(repo):
    put("UserPromptSubmit", repo, T0, prompt="one")
    ingest.drain(reconcile=False)
    put("Stop", repo, T0 + 5, last_assistant_message="two")
    put("UserPromptSubmit", repo, T0 + 10, prompt="three")
    ingest.drain(reconcile=False)
    assert [(s.message.ordinal, s.message.text) for s in stored()[1]] == [(0, "one"), (1, "two"), (2, "three")]


# --- the gates and the scrubber -------------------------------------------------------------------------------------


def test_a_record_out_of_scope_at_ingest_is_not_written(repo, tmp_path):
    put("UserPromptSubmit", repo, T0, prompt="hello")
    write_settings(tmp_path / "somewhere-else")  # the folder was taken off the personal list since
    result = ingest.drain(reconcile=False)
    assert (result.out_of_scope, result.messages, result.sources) == (1, 0, 0)
    assert stored()[0] is None


def test_a_session_in_the_data_root_is_not_ingested_even_if_spooled(repo):
    harness_dir = paths.harness_cwd()
    harness_dir.mkdir(parents=True)
    write_settings(paths.data_root().parent, repo.parent)
    put("UserPromptSubmit", harness_dir, T0, prompt="a hidden harness prompt")
    result = ingest.drain(reconcile=False)
    assert (result.out_of_scope, result.messages) == (1, 0)


def test_a_record_that_was_not_scrubbed_is_refused(repo):
    put("UserPromptSubmit", repo, T0, prompt=f"token {FAKE_TOKEN}", scrub=None)
    result = ingest.drain(reconcile=False)
    assert (result.errors, result.messages) == (1, 0)
    assert "not scrubbed" in spool.log_path().read_text()


def test_text_is_scrubbed_again_on_the_way_in(repo):
    put("UserPromptSubmit", repo, T0, prompt=f"push with {FAKE_TOKEN} now", scrub="noop")
    put("Stop", repo, T0 + 5, last_assistant_message=f"using {FAKE_TOKEN}", scrub="noop")
    ingest.drain(reconcile=False)
    for _, text in texts():
        assert FAKE_TOKEN not in text and "Ab1Cd2Ef3" not in text
    assert texts()[0][1].startswith("push with ") and texts()[0][1].endswith(" now")


def test_with_no_scrubber_nothing_is_written(repo, monkeypatch):
    put("UserPromptSubmit", repo, T0, prompt="hello")
    monkeypatch.setitem(sys.modules, "northstar_agent_memory.capture.secrets", None)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("NORTHSTAR_TEST_MODE", raising=False)
    result = ingest.drain(reconcile=False)
    assert result.messages == 0 and spool.has_pending()
    assert not (paths.data_root() / "history.db").exists()


def test_torn_and_corrupt_lines_do_not_stop_the_good_records(repo):
    put("UserPromptSubmit", repo, T0, prompt="before")
    path = spool.spool_files()[0]
    with path.open("ab") as fh:
        fh.write(b"garbage line\n")
        fh.write(b'{"v":1,"id":"01TORN","event":"Stop","session_id":"s')  # a hook killed mid-write
    result = ingest.drain(reconcile=False)
    assert (result.messages, result.corrupt) == (1, 1)
    assert spool.has_pending()  # the torn bytes still wait
    put("Stop", repo, T0 + 5, last_assistant_message="after")  # the next hook starts a fresh line
    result = ingest.drain(reconcile=False)
    assert (result.messages, result.corrupt) == (1, 1)
    assert [t for _, t in texts()] == ["before", "after"]
    assert not spool.has_pending()


def test_a_spool_file_that_is_done_and_old_is_deleted_after_the_drain(repo):
    put("UserPromptSubmit", repo, T0, prompt="hello")
    path = spool.spool_files()[0]
    ingest.drain(reconcile=False, now=path.stat().st_mtime + spool.DONE_KEEP_S + 10)
    assert spool.spool_files() == [] and len(stored()[1]) == 1


# --- reconciliation against the transcript (§12) ------------------------------------------------------------------------


def reconciled(session=SESSION):
    return [s for s in stored(session)[1] if s.fidelity == "reconciled"]


def test_a_turn_the_hooks_missed_is_added_from_the_transcript_as_reconciled(repo, transcript):
    kw = {"transcript_path": str(transcript)}
    put("SessionStart", repo, T0, source="startup", **kw)
    put("UserPromptSubmit", repo, T0 + 5, prompt="Turn one.", **kw)
    put("Stop", repo, T0 + 20, last_assistant_message="Reply one.", **kw)
    # turn two: both hooks timed out
    put("UserPromptSubmit", repo, T0 + 120, prompt="Turn three.", **kw)
    put("Stop", repo, T0 + 140, last_assistant_message="Reply three.", **kw)
    put("SessionEnd", repo, T0 + 150, reason="other", **kw)
    write_transcript(
        transcript,
        t_user("Turn one.", T0 + 5, "u1"), t_assistant("Reply one.", T0 + 20, "a1"),
        t_user("Turn two.", T0 + 60, "u2"), t_assistant("Reply two.", T0 + 80, "a2"),
        t_user("Turn three.", T0 + 120, "u3"), t_assistant("Reply three.", T0 + 140, "a3"),
    )
    result = ingest.drain(now=T0 + 151)
    assert (result.reconciled, result.mismatches, result.errors) == (2, 0, 0)
    rows = stored()[1]
    assert [(s.message.speaker, s.message.text, s.fidelity) for s in rows] == [
        ("user", "Turn one.", "verbatim"), ("assistant", "Reply one.", "verbatim"),
        ("user", "Turn three.", "verbatim"), ("assistant", "Reply three.", "verbatim"),
        ("system", "[claude-code] session ended (other)", "verbatim"),
        ("user", "Turn two.", "reconciled"), ("assistant", "Reply two.", "reconciled"),
    ]
    user, reply = [s.message for s in reconciled()]
    assert (user.origin, user.agent, user.model_family, user.occurred_at) == ("typed", "claude-code", None, "2026-03-02T09:01:00.000Z")
    assert (reply.origin, reply.agent, reply.model_family) == ("assistant_output", "claude-code", "anthropic")
    assert user.meta["reconciled"] is True and user.meta["transcript_uuid"] == "u2" and reply.meta["transcript_uuid"] == "a2"


def test_an_image_only_prompt_in_the_transcript_adds_no_blank_user_turn(repo, transcript):
    kw = {"transcript_path": str(transcript)}
    put("SessionStart", repo, T0, source="startup", **kw)
    put("UserPromptSubmit", repo, T0 + 5, prompt="Turn one.", **kw)
    put("Stop", repo, T0 + 20, last_assistant_message="Reply one.", **kw)
    put("SessionEnd", repo, T0 + 150, reason="other", **kw)
    image = t_user("", T0 + 60, "u2")
    image["message"]["content"] = [{"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "AAAA"}}]
    write_transcript(
        transcript, t_user("Turn one.", T0 + 5, "u1"), t_assistant("Reply one.", T0 + 20, "a1"),
        image, t_assistant("The chart looks fine.", T0 + 80, "a2"),
    )
    result = ingest.drain(now=T0 + 151)
    assert (result.reconciled, result.errors) == (1, 0)
    assert [m.message.text for m in reconciled()] == ["The chart looks fine."]
    assert all(s.message.text.strip() for s in stored()[1])


def test_reconciling_again_adds_nothing(repo, transcript):
    kw = {"transcript_path": str(transcript)}
    put("SessionStart", repo, T0, source="startup", **kw)
    put("UserPromptSubmit", repo, T0 + 120, prompt="Turn three.", **kw)
    put("SessionEnd", repo, T0 + 150, reason="other", **kw)
    write_transcript(transcript, t_user("Turn one.", T0 + 5, "u1"), t_assistant("Reply one.", T0 + 20, "a1"),
                     t_user("Turn three.", T0 + 120, "u3"))
    assert ingest.drain(now=T0 + 151).reconciled == 2
    assert ingest.drain(now=T0 + 152).reconciled == 0
    state = json.loads(spool.state_path().read_text())
    for entry in state["sessions"].values():
        entry["rec_sig"] = None  # forget that this transcript was read: it is read again, and its turns are recognised
    spool.state_path().write_text(json.dumps(state))
    assert ingest.drain(now=T0 + 153).reconciled == 0
    put("SessionEnd", repo, T0 + 300, reason="other", **kw)  # a later event tells the ingester where the transcript is
    with open(transcript, "a") as fh:  # the transcript grew: only the new turn is added
        fh.write('{"type":"user","uuid":"u4","sessionId":"%s","timestamp":"2026-03-02T09:05:00.000Z","message":{"role":"user","content":"Turn four."}}\n' % SESSION)
    assert ingest.drain(now=T0 + 400).reconciled == 1
    assert len(reconciled()) == 3 and len(stored()[1]) == 6


def test_a_missed_reply_alone_is_added_without_duplicating_the_hooked_turn(repo, transcript):
    kw = {"transcript_path": str(transcript)}
    put("SessionStart", repo, T0, source="startup", **kw)
    put("UserPromptSubmit", repo, T0 + 5, prompt="Turn one.", **kw)  # its Stop hook timed out
    put("SessionEnd", repo, T0 + 150, reason="other", **kw)
    write_transcript(transcript, t_user("Turn one.", T0 + 5, "u1"), t_assistant("Reply one.", T0 + 20, "a1"))
    result = ingest.drain(now=T0 + 151)
    assert result.reconciled == 1
    assert [(s.message.speaker, s.fidelity) for s in stored()[1] if s.message.speaker != "system"] == [("user", "verbatim"), ("assistant", "reconciled")]


def test_the_narration_before_tool_calls_is_added_beside_the_final_reply_the_hook_has(repo, transcript):
    kw = {"transcript_path": str(transcript)}
    put("UserPromptSubmit", repo, T0 + 5, prompt="Fix it.", **kw)
    put("Stop", repo, T0 + 40, last_assistant_message="Fixed.", **kw)  # a Stop hook carries the final text only
    put("SessionEnd", repo, T0 + 50, reason="other", **kw)
    write_transcript(transcript, t_user("Fix it.", T0 + 5, "u1"), t_assistant("Let me look at the file.", T0 + 10, "a1"),
                     t_assistant("The bug is in the sort key.", T0 + 20, "a2"), t_assistant("Fixed.", T0 + 40, "a3"))
    result = ingest.drain(now=T0 + 60)
    assert (result.reconciled, result.mismatches, result.errors) == (2, 0, 0)
    assert [(s.message.speaker, s.message.text, s.fidelity) for s in stored()[1] if s.message.speaker == "assistant"] == [
        ("assistant", "Fixed.", "verbatim"),
        ("assistant", "Let me look at the file.", "reconciled"), ("assistant", "The bug is in the sort key.", "reconciled"),
    ]
    narration = reconciled()[0].message
    assert (narration.origin, narration.agent, narration.model_family, narration.occurred_at) == (
        "assistant_output", "claude-code", "anthropic", "2026-03-02T09:00:10.000Z")
    assert narration.meta["reconciled"] is True and narration.meta["transcript_uuid"] == "a1"
    assert ingest.drain(now=T0 + 70).reconciled == 0  # and only once


def test_a_turn_whose_stop_hook_was_lost_gets_all_its_assistant_texts(repo, transcript):
    kw = {"transcript_path": str(transcript)}
    put("UserPromptSubmit", repo, T0 + 5, prompt="Fix it.", **kw)
    put("SessionEnd", repo, T0 + 50, reason="other", **kw)
    write_transcript(transcript, t_user("Fix it.", T0 + 5, "u1"), t_assistant("Let me look.", T0 + 10, "a1"),
                     t_assistant("Fixed.", T0 + 40, "a2"))
    assert ingest.drain(now=T0 + 60).reconciled == 2
    assert [(s.message.text, s.fidelity) for s in stored()[1] if s.message.speaker == "assistant"] == [
        ("Let me look.", "reconciled"), ("Fixed.", "reconciled")]


def test_a_mismatch_is_logged_and_nothing_is_overwritten(repo, transcript):
    kw = {"transcript_path": str(transcript)}
    put("SessionStart", repo, T0, source="startup", **kw)
    put("UserPromptSubmit", repo, T0 + 5, prompt="Keep readings for 7 days.", **kw)
    put("Stop", repo, T0 + 20, last_assistant_message="Kept for 7 days.", **kw)
    put("SessionEnd", repo, T0 + 30, reason="other", **kw)
    write_transcript(transcript, t_user("Keep readings for 30 days.", T0 + 6, "u1"),
                     t_assistant("Something else entirely was said here.", T0 + 20, "a1"))
    result = ingest.drain(now=T0 + 40)
    assert (result.mismatches, result.reconciled) == (2, 0)
    assert [t for sp, t in texts() if sp != "system"] == ["Keep readings for 7 days.", "Kept for 7 days."]
    assert all(s.fidelity == "verbatim" for s in stored()[1])
    log = spool.log_path().read_text()
    assert log.count("mismatch session=" + SESSION) == 2 and "kind=user" in log and "kind=assistant" in log
    assert "readings" not in log and "days" not in log  # hashes and sizes only, never the words


def test_whitespace_and_unicode_differences_are_not_mismatches(repo, transcript):
    kw = {"transcript_path": str(transcript)}
    put("UserPromptSubmit", repo, T0 + 5, prompt="Keep  the readings\nfor café days.", **kw)
    put("Stop", repo, T0 + 20, last_assistant_message="Done.\n\nAll set.", **kw)
    put("SessionEnd", repo, T0 + 30, reason="other", **kw)
    write_transcript(transcript, t_user("Keep the readings for café days.", T0 + 5, "u1"), t_assistant("Done. All set.", T0 + 20, "a1"))
    result = ingest.drain(now=T0 + 40)
    assert (result.mismatches, result.reconciled) == (0, 0)


def test_turns_from_before_capture_began_are_not_reconciled(repo, transcript):
    kw = {"transcript_path": str(transcript)}
    put("SessionStart", repo, T0 + 1000, source="resume", **kw)  # a resumed session: its earlier turns are the backfill's
    put("UserPromptSubmit", repo, T0 + 1005, prompt="Back again.", **kw)
    put("SessionEnd", repo, T0 + 1100, reason="other", **kw)
    write_transcript(transcript, t_user("Before Northstar.", T0 + 5, "u1"), t_assistant("An old reply.", T0 + 20, "a1"),
                     t_user("Back again.", T0 + 1005, "u2"))
    assert ingest.drain(now=T0 + 1200).reconciled == 0
    assert texts()[0] == ("user", "Back again.")


def test_a_fresh_session_has_all_its_turns_reconciled_from_the_first(repo, transcript):
    kw = {"transcript_path": str(transcript)}
    put("SessionStart", repo, T0, source="startup", **kw)  # the first prompt's hook was lost
    put("UserPromptSubmit", repo, T0 + 60, prompt="Second.", **kw)
    put("SessionEnd", repo, T0 + 100, reason="other", **kw)
    write_transcript(transcript, t_user("First.", T0 + 5, "u1"), t_user("Second.", T0 + 60, "u2"))
    assert ingest.drain(now=T0 + 200).reconciled == 1
    assert [s.message.text for s in reconciled()] == ["First."]


def test_a_session_still_in_progress_is_not_reconciled_until_it_has_been_quiet(repo, transcript):
    kw = {"transcript_path": str(transcript)}
    put("SessionStart", repo, T0, source="startup", **kw)
    put("UserPromptSubmit", repo, T0 + 60, prompt="Second.", **kw)
    write_transcript(transcript, t_user("First.", T0 + 5, "u1"), t_user("Second.", T0 + 60, "u2"))
    assert ingest.drain(now=T0 + 90, grace_s=120).reconciled == 0  # the hook for a turn may simply not have arrived yet
    assert ingest.drain(now=T0 + 60 + 121, grace_s=120).reconciled == 1  # a crashed session is settled after a while


def test_no_reconcile_option_skips_it(repo, transcript):
    kw = {"transcript_path": str(transcript)}
    put("SessionStart", repo, T0, source="startup", **kw)
    put("SessionEnd", repo, T0 + 100, reason="other", **kw)
    write_transcript(transcript, t_user("First.", T0 + 5, "u1"))
    assert ingest.drain(reconcile=False, now=T0 + 200).reconciled == 0
    assert ingest.drain(now=T0 + 200).reconciled == 1


@pytest.mark.parametrize("kind", ["missing", "not_jsonl", "garbage", "directory", "no_path"])
def test_an_unreadable_transcript_does_not_disturb_capture(repo, tmp_path, kind):
    target = tmp_path / "t" / "session.jsonl"
    if kind == "not_jsonl":
        target = write_transcript(tmp_path / "t" / "session.txt", t_user("x", T0, "u1"))
    elif kind == "garbage":
        target.parent.mkdir(parents=True)
        target.write_bytes(b"\xff\xfe not json \x00\n{{{\n")
    elif kind == "directory":
        target.mkdir(parents=True)
    kw = {} if kind == "no_path" else {"transcript_path": str(target)}
    put("UserPromptSubmit", repo, T0 + 5, prompt="hello", **kw)
    put("SessionEnd", repo, T0 + 10, reason="other", **kw)
    result = ingest.drain(now=T0 + 20)
    assert (result.messages, result.reconciled, result.errors) == (2, 0, 0)


def test_secrets_in_the_transcript_are_replaced_before_they_are_stored(repo, transcript):
    kw = {"transcript_path": str(transcript)}
    put("SessionStart", repo, T0, source="startup", **kw)
    put("SessionEnd", repo, T0 + 100, reason="other", **kw)
    write_transcript(transcript, t_user(f"Use {FAKE_TOKEN} to push", T0 + 5, "u1"), t_assistant(f"Pushed with {FAKE_TOKEN}.", T0 + 9, "a1"))
    assert ingest.drain(now=T0 + 200).reconciled == 2
    for s in reconciled():
        assert "Ab1Cd2Ef3" not in s.message.text and FAKE_TOKEN not in s.message.text


def test_a_transcript_turn_that_is_not_the_users_words_is_not_added(repo, transcript):
    kw = {"transcript_path": str(transcript)}
    put("SessionStart", repo, T0, source="startup", **kw)
    put("SessionEnd", repo, T0 + 100, reason="other", **kw)
    write_transcript(
        transcript,
        {**t_user("<system-reminder>injected</system-reminder>", T0 + 3, "u0")},
        {**t_user("tool output text", T0 + 4, "u1"), "isMeta": True},
        {"type": "user", "uuid": "u2", "sessionId": SESSION, "timestamp": "2026-03-02T09:00:06.000Z",
         "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "ok"}]}},
        t_user("What the user typed.", T0 + 7, "u3"),
    )
    assert ingest.drain(now=T0 + 200).reconciled == 1
    assert [s.message.text for s in reconciled()] == ["What the user typed."]


def everything_stored():
    with SQLiteHistoryStore() as store:
        return str([tuple(r) for table in ("source", "message", "work_event") for r in store.conn.execute(f"SELECT * FROM {table}")])


def test_turns_made_after_leaving_the_personal_folders_are_not_reconciled(repo, transcript, tmp_path):
    work = tmp_path / "work" / "billing"  # not a personal folder
    kw = {"transcript_path": str(transcript)}
    put("SessionStart", repo, T0, source="startup", **kw)
    put("UserPromptSubmit", repo, T0 + 5, prompt="In the dashboard.", **kw)
    put("Stop", repo, T0 + 20, last_assistant_message="Here.", **kw)
    put("SessionEnd", repo, T0 + 150, reason="other", **kw)
    # The hooks (which ask the gate at each event) wrote nothing for the turns after the cd out. The transcript has them.
    write_transcript(
        transcript,
        t_user("In the dashboard.", T0 + 5, "u1"), t_assistant("Here.", T0 + 20, "a1"),
        t_user("Now client Acme invoice 4411.", T0 + 60, "u2", cwd=str(work)),
        t_assistant("Let me open the Acme file.", T0 + 70, "a2", cwd=str(work)),
        t_assistant("Invoice 4411 is for Acme.", T0 + 80, "a3", cwd=str(work)),
    )
    result = ingest.drain(now=T0 + 200)
    assert (result.reconciled, result.mismatches, result.errors) == (0, 0, 0)
    assert "Acme" not in everything_stored() and "4411" not in everything_stored()
    # Back in a personal folder (another one is also fine), the same session is reconciled again.
    other = make_repo(repo.parent, "garden-notes")
    with open(transcript, "a") as fh:
        for line in (t_user("Back home.", T0 + 100, "u3", cwd=str(other)), t_assistant("Welcome back.", T0 + 110, "a4", cwd=str(other))):
            fh.write(json.dumps(line) + "\n")
    put("SessionEnd", repo, T0 + 300, reason="other", **kw)
    assert ingest.drain(now=T0 + 400).reconciled == 2
    assert [s.message.text for s in reconciled()] == ["Back home.", "Welcome back."]
    assert "Acme" not in everything_stored()


def test_an_assistant_line_after_a_cd_out_is_dropped_but_the_turn_before_it_stays(repo, transcript, tmp_path):
    kw = {"transcript_path": str(transcript)}
    put("SessionStart", repo, T0, source="startup", **kw)
    put("SessionEnd", repo, T0 + 150, reason="other", **kw)
    write_transcript(
        transcript,
        t_user("Look at the notes.", T0 + 5, "u1"), t_assistant("Opening them.", T0 + 10, "a1"),
        t_assistant("These are the billing notes for Acme.", T0 + 20, "a2", cwd=str(tmp_path / "work")),
    )
    assert ingest.drain(now=T0 + 200).reconciled == 2
    assert [s.message.text for s in reconciled()] == ["Look at the notes.", "Opening them."]


def test_a_transcript_turn_in_the_data_root_is_not_reconciled(repo, transcript):
    own = paths.harness_cwd()
    own.mkdir(parents=True)
    write_settings(paths.data_root().parent, repo.parent)  # even a personal folder that covers the data root
    kw = {"transcript_path": str(transcript)}
    put("SessionStart", repo, T0, source="startup", **kw)
    put("SessionEnd", repo, T0 + 150, reason="other", **kw)
    write_transcript(transcript, t_user("A hidden harness prompt.", T0 + 5, "u1", cwd=str(own)))
    assert ingest.drain(now=T0 + 200).reconciled == 0


# --- turn origin in live capture and in reconciliation (§8, I24) --------------------------------------------------------


def test_a_block_northstar_delivered_is_its_own_message_and_never_the_users(repo):
    block = wrap_northstar("Decision D1: lowest device id wins.")
    put("UserPromptSubmit", repo, T0, prompt=f"What was decided about ties?\n{block}")
    put("UserPromptSubmit", repo, T0 + 10, prompt=f"<system-reminder>Hook: {wrap_northstar('Start note: Lamport clocks.')}</system-reminder>")
    put("UserPromptSubmit", repo, T0 + 20, prompt=wrap_northstar("Only a block."))
    result = ingest.drain(reconcile=False)
    assert (result.messages, result.errors) == (4, 0)
    rows = [s.message for s in stored()[1]]
    assert [(m.speaker, m.origin, m.text) for m in rows] == [
        ("user", "typed", "What was decided about ties?"),
        ("northstar", "northstar_injected", "Decision D1: lowest device id wins."),
        ("northstar", "northstar_injected", "Start note: Lamport clocks."),
        ("northstar", "northstar_injected", "Only a block."),
    ]
    assert [m.meta.get("part") for m in rows] == [None, "n0", "n0", "n0"]
    assert all(m.agent == "claude-code" and m.model_family is None for m in rows)
    assert origin.NORTHSTAR_TAG not in everything_stored()


def test_a_pasted_prompt_with_a_secret_keeps_its_offsets(repo):
    put("UserPromptSubmit", repo, T0, prompt=f"Why? <pasted_content>token {FAKE_TOKEN} fails</pasted_content> thanks", scrub="noop")
    ingest.drain(reconcile=False)
    (m,) = [s.message for s in stored()[1]]
    assert FAKE_TOKEN not in m.text and m.text.startswith("Why? token ") and m.text.endswith(" fails thanks")
    (start, end), = m.meta["paste_ranges"]
    assert m.text[start:end].startswith("token ") and m.text[start:end].endswith(" fails")


def test_reconciliation_does_not_store_northstars_block_as_the_users_words(repo, transcript):
    kw = {"transcript_path": str(transcript)}
    block = wrap_northstar("Decision D1: lowest device id wins.")
    put("SessionStart", repo, T0, source="startup", **kw)
    put("SessionEnd", repo, T0 + 150, reason="other", **kw)  # both hooks of the turn were lost
    write_transcript(transcript, t_user(f"What was decided about ties?\n{block}", T0 + 5, "u1"), t_assistant("D1.", T0 + 9, "a1"))
    assert ingest.drain(now=T0 + 200).reconciled == 3
    assert [(s.message.speaker, s.message.origin, s.message.text, s.message.meta.get("part")) for s in reconciled()] == [
        ("user", "typed", "What was decided about ties?", None),
        ("northstar", "northstar_injected", "Decision D1: lowest device id wins.", "n0"),
        ("assistant", "assistant_output", "D1.", None),
    ]
    assert origin.NORTHSTAR_TAG not in everything_stored()


def test_a_block_stored_live_is_not_added_again_by_reconciliation(repo, transcript):
    kw = {"transcript_path": str(transcript)}
    block = wrap_northstar("Decision D1: lowest device id wins.")
    put("SessionStart", repo, T0, source="startup", **kw)
    put("UserPromptSubmit", repo, T0 + 5, prompt=f"What was decided about ties?\n{block}", **kw)
    put("Stop", repo, T0 + 9, last_assistant_message="D1.", **kw)
    put("SessionEnd", repo, T0 + 150, reason="other", **kw)
    write_transcript(transcript, t_user(f"What was decided about ties?\n{block}", T0 + 5, "u1"), t_assistant("D1.", T0 + 9, "a1"))
    result = ingest.drain(now=T0 + 200)
    assert (result.reconciled, result.mismatches) == (0, 0)


def test_a_command_and_a_paste_in_the_transcript_match_the_hooked_turns(repo, transcript):
    kw = {"transcript_path": str(transcript)}
    put("SessionStart", repo, T0, source="startup", **kw)
    put("UserPromptSubmit", repo, T0 + 5, prompt="/review the tie-break rule", **kw)
    put("UserPromptSubmit", repo, T0 + 60, prompt="Why? <pasted_content>KeyError: 'x'</pasted_content> thanks", **kw)
    put("SessionEnd", repo, T0 + 150, reason="other", **kw)
    write_transcript(
        transcript,
        t_user("<command-name>/review</command-name><command-message>review</command-message><command-args>the tie-break rule</command-args>", T0 + 5, "u1"),
        t_user("Why? <pasted_content>KeyError: 'x'</pasted_content> thanks", T0 + 60, "u2"),
    )
    result = ingest.drain(now=T0 + 200)
    assert (result.reconciled, result.mismatches) == (0, 0)
    command, pasted = [s.message for s in stored()[1] if s.message.speaker == "user"]
    assert command.meta["command"] == "/review" and pasted.meta["paste_ranges"] == [[5, 18]]


# --- a delivery the hooks made twice -----------------------------------------------------------------------------------


def test_a_prompt_delivered_twice_with_the_same_prompt_id_is_stored_once(repo):
    put("UserPromptSubmit", repo, T0, prompt="Add the export button.", prompt_id="p-1")
    put("UserPromptSubmit", repo, T0 + 40, prompt="Add the export button.", prompt_id="p-1")  # however late
    put("Stop", repo, T0 + 50, last_assistant_message="Added.", prompt_id="p-1")
    put("Stop", repo, T0 + 51, last_assistant_message="Added.", prompt_id="p-1")
    result = ingest.drain(reconcile=False)
    assert (result.messages, result.duplicates) == (2, 2)
    assert texts() == [("user", "Add the export button."), ("assistant", "Added.")]
    again = ingest.drain(reconcile=False)  # and once stored, once only
    assert again.messages == 0


def test_the_same_prompt_id_in_another_session_or_event_is_not_a_duplicate(repo):
    put("UserPromptSubmit", repo, T0, SESSION, prompt="Same words.", prompt_id="p-1")
    put("UserPromptSubmit", repo, T0 + 1, OTHER, prompt="Same words.", prompt_id="p-1")
    put("Stop", repo, T0 + 2, SESSION, last_assistant_message="Reply.", prompt_id="p-1")
    assert ingest.drain(reconcile=False).messages == 3


def test_a_second_stop_with_other_words_for_one_prompt_is_kept(repo):
    put("UserPromptSubmit", repo, T0, prompt="Fix it.", prompt_id="p-1")
    put("Stop", repo, T0 + 10, last_assistant_message="Fixed the sort key.", prompt_id="p-1")
    put("Stop", repo, T0 + 30, last_assistant_message="And the tie-break too.", prompt_id="p-1")  # after a stop hook continued it
    assert ingest.drain(reconcile=False).messages == 3


def test_without_a_prompt_id_the_same_words_within_five_seconds_are_one_delivery(repo):
    put("UserPromptSubmit", repo, T0, prompt="Add the export button.")
    put("UserPromptSubmit", repo, T0 + 4.5, prompt="Add the export button.")
    put("Stop", repo, T0 + 10, last_assistant_message="Added.")
    put("Stop", repo, T0 + 12, last_assistant_message="Added.")
    result = ingest.drain(reconcile=False)
    assert (result.messages, result.duplicates) == (2, 2)
    assert texts() == [("user", "Add the export button."), ("assistant", "Added.")]


def test_without_a_prompt_id_the_same_words_later_are_a_new_turn(repo):
    put("UserPromptSubmit", repo, T0, prompt="yes")
    put("Stop", repo, T0 + 20, last_assistant_message="Done.")
    put("UserPromptSubmit", repo, T0 + 40, prompt="yes")
    put("UserPromptSubmit", repo, T0 + 41, prompt="Different words.")  # other words are never a duplicate
    result = ingest.drain(reconcile=False)
    assert (result.messages, result.duplicates) == (4, 0)


def test_two_deliveries_in_separate_drains_are_still_one(repo):
    put("UserPromptSubmit", repo, T0, prompt="Add the export button.")
    ingest.drain(reconcile=False)
    put("UserPromptSubmit", repo, T0 + 1, prompt="Add the export button.")
    result = ingest.drain(reconcile=False)
    assert (result.messages, result.duplicates) == (0, 1) and len(stored()[1]) == 1


# --- work events (§2.2) -----------------------------------------------------------------------------------------------------


def git(folder, *args, when=None):
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "GIT_AUTHOR_NAME": "Robin",
           "GIT_AUTHOR_EMAIL": "robin@example.org", "GIT_COMMITTER_NAME": "Robin", "GIT_COMMITTER_EMAIL": "robin@example.org"}
    if when:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = when
    done = subprocess.run(["git", "-c", "commit.gpgsign=false", "-C", str(folder), *args], capture_output=True, text=True,
                          env=env, check=True, stdin=subprocess.DEVNULL)
    return done.stdout.strip()


def commit(folder, message, at):
    (folder / "file.txt").write_text(f"{message}\n", encoding="utf-8")
    git(folder, "add", "file.txt")
    git(folder, "commit", "-m", message, when=iso(at))
    return git(folder, "rev-parse", "HEAD")


@pytest.fixture
def git_repo(tmp_path):
    personal = tmp_path / "personal"
    folder = personal / "energy-dash"
    folder.mkdir(parents=True)
    git(folder, "init")
    write_settings(personal)
    PERSONAL_REPO[:] = [folder]
    return folder


def work_events_stored():
    with SQLiteHistoryStore() as store:
        return [(r["ref"], r["source_id"], r["evidence"]) for r in store.conn.execute("SELECT * FROM work_event ORDER BY seq")]


def test_the_commits_of_a_session_are_recorded_when_it_ends(git_repo):
    before = commit(git_repo, "Before the session", T0 - 600)
    put("SessionStart", git_repo, T0, source="startup")
    put("UserPromptSubmit", git_repo, T0 + 5, prompt="Add the export button.")
    first = commit(git_repo, "Add the export button", T0 + 30)
    put("Stop", git_repo, T0 + 40, last_assistant_message="Added.")
    second = commit(git_repo, "Style the button", T0 + 50)
    put("SessionEnd", git_repo, T0 + 60, reason="other")
    after = commit(git_repo, "Made after the session", T0 + 3600)
    result = ingest.drain(reconcile=False, now=T0 + 61)
    assert result.work_events == 2
    assert work_events_stored() == [(first, SESSION, "medium"), (second, SESSION, "medium")]
    assert before not in str(work_events_stored()) and after not in str(work_events_stored())
    assert ingest.drain(reconcile=False, now=T0 + 62).work_events == 0  # and once only
    assert len(work_events_stored()) == 2


def test_the_commits_of_a_session_that_went_quiet_are_recorded_when_it_settles(git_repo):
    put("SessionStart", git_repo, T0, source="startup")
    put("UserPromptSubmit", git_repo, T0 + 5, prompt="Add the export button.")
    sha = commit(git_repo, "Add the export button", T0 + 30)
    put("Stop", git_repo, T0 + 40, last_assistant_message="Added.")  # no SessionEnd: the terminal was closed
    assert ingest.drain(now=T0 + 60, grace_s=120).work_events == 0  # still within the quiet window: it may go on
    assert work_events_stored() == []
    assert ingest.drain(now=T0 + 40 + 121, grace_s=120).work_events == 1
    assert work_events_stored() == [(sha, SESSION, "medium")]


def test_a_folder_outside_the_personal_folders_has_no_work_events(git_repo, tmp_path):
    work = tmp_path / "work" / "billing"
    work.mkdir(parents=True)
    git(work, "init")
    sha = commit(work, "Invoice run", T0 + 30)
    put("SessionStart", git_repo, T0, source="startup")
    put("SessionEnd", git_repo, T0 + 60, reason="other")
    ingest.drain(reconcile=False, now=T0 + 61)  # the session's folder is personal; record_commits is asked for the other one
    from northstar_agent_memory.capture import work_events

    with SQLiteHistoryStore() as store:
        report = work_events.record_commits(store, SESSION, work, session_started_at=iso(T0))
    assert report.skipped == "out_of_scope" and report.recorded == 0
    assert sha not in str(work_events_stored())


def test_a_folder_taken_off_the_personal_list_records_nothing_at_session_end(git_repo, tmp_path):
    put("SessionStart", git_repo, T0, source="startup")
    commit(git_repo, "Add the export button", T0 + 30)
    put("SessionEnd", git_repo, T0 + 60, reason="other")
    write_settings(tmp_path / "somewhere-else")
    result = ingest.drain(now=T0 + 61)
    assert (result.out_of_scope, result.work_events) == (2, 0) and work_events_stored() == []


def test_work_events_are_recorded_even_when_reconciliation_is_skipped(git_repo):
    put("SessionStart", git_repo, T0, source="startup")
    sha = commit(git_repo, "Add the export button", T0 + 30)
    put("SessionEnd", git_repo, T0 + 60, reason="other")
    assert ingest.drain(reconcile=False, now=T0 + 61).work_events == 1
    assert work_events_stored() == [(sha, SESSION, "medium")]


def test_a_git_failure_does_not_stop_capture_and_is_retried_a_few_times(git_repo, monkeypatch):
    from northstar_agent_memory.capture import work_events

    put("SessionStart", git_repo, T0, source="startup")
    put("UserPromptSubmit", git_repo, T0 + 5, prompt="hello")
    put("SessionEnd", git_repo, T0 + 60, reason="other")
    calls = []

    def broken(*a, **k):
        calls.append(1)
        return work_events.WorkEventReport(error="git log timed out after 5 s")

    monkeypatch.setattr(work_events, "record_commits", broken)
    for n in range(5):
        assert ingest.drain(reconcile=False, now=T0 + 61 + n).messages == (2 if n == 0 else 0)
    assert len(calls) == ingest.WORK_TRIES and "timed out" in spool.log_path().read_text()
    assert len(stored()[1]) == 2


# --- one writer ----------------------------------------------------------------------------------------------------


def test_a_second_ingester_does_not_run_while_one_holds_the_lock(repo, monkeypatch):
    put("UserPromptSubmit", repo, T0, prompt="hello")
    inside, release = threading.Event(), threading.Event()
    real = ingest.drain
    calls = []

    def slow(*a, **k):
        calls.append(1)
        inside.set()
        assert release.wait(10)
        return real(*a, **k)

    monkeypatch.setattr(ingest, "drain", slow)
    first = []
    thread = threading.Thread(target=lambda: first.append(ingest.run(reconcile=False)))
    thread.start()
    assert inside.wait(10)
    assert ingest.run(reconcile=False) is None  # one ingester at a time
    assert spool.lock_held(spool.lock_path())
    release.set()
    thread.join(10)
    assert first[0].messages == 1 and calls == [1]
    assert not spool.lock_held(spool.lock_path())


def test_a_record_written_as_the_lock_is_let_go_is_drained_by_another_round(repo, monkeypatch):
    put("UserPromptSubmit", repo, T0, prompt="first")
    real = ingest.drain
    calls = []

    def drain_then_a_hook_writes(*a, **k):
        result = real(*a, **k)
        if not calls:
            put("Stop", repo, T0 + 5, last_assistant_message="second")  # the hook saw the lock held, and did not spawn
        calls.append(1)
        return result

    monkeypatch.setattr(ingest, "drain", drain_then_a_hook_writes)
    total = ingest.run(reconcile=False)
    assert len(calls) == 2 and total.messages == 2
    assert [t for _, t in texts()] == ["first", "second"] and not spool.has_pending()


def test_a_record_written_while_a_drain_found_nothing_is_not_left_waiting(repo, monkeypatch):
    real = ingest.drain
    calls = []

    def empty_drain_then_a_hook_writes(*a, **k):
        result = real(*a, **k)  # the spool was empty
        if not calls:
            put("UserPromptSubmit", repo, T0, prompt="written while the lock was held")  # the hook did not spawn
        calls.append(1)
        return result

    monkeypatch.setattr(ingest, "drain", empty_drain_then_a_hook_writes)
    total = ingest.run(reconcile=False)
    assert total.messages == 1 and len(calls) == 2
    assert [t for _, t in texts()] == ["written while the lock was held"] and not spool.has_pending()


def test_concurrent_ingester_processes_write_every_message_exactly_once(repo):
    for i in range(30):
        for session in (SESSION, OTHER):
            put("UserPromptSubmit", repo, T0 + i * 2, session, prompt=f"{session[-1]} question {i}")
            put("Stop", repo, T0 + i * 2 + 1, session, last_assistant_message=f"{session[-1]} answer {i}")
    env = {**os.environ}
    env.pop("NORTHSTAR_HIDDEN_RUN", None)
    procs = [
        subprocess.Popen([sys.executable, "-m", "northstar_agent_memory.capture.ingest", "--drain", "--no-reconcile"],
                         env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for _ in range(4)
    ]
    outputs = [p.communicate(timeout=120) for p in procs]
    assert [p.returncode for p in procs] == [0, 0, 0, 0], outputs
    assert not spool.has_pending()
    for session in (SESSION, OTHER):
        rows = stored(session)[1]
        assert len(rows) == 60
        assert [s.message.ordinal for s in rows] == list(range(60))
        assert len({s.message.text for s in rows}) == 60
        assert [s.message.speaker for s in rows] == ["user", "assistant"] * 30
    with SQLiteHistoryStore() as store:
        assert store.watermark().message_seq == 120  # no message was written and then written again


# --- the command line ------------------------------------------------------------------------------------------------


def test_main_drains_and_exits_0(repo):
    put("UserPromptSubmit", repo, T0, prompt="hello")
    assert ingest.main(["--drain", "--no-reconcile"]) == 0
    assert texts() == [("user", "hello")] and not spool.has_pending()


def test_main_without_drain_prints_usage_and_does_nothing(repo, capsys):
    put("UserPromptSubmit", repo, T0, prompt="hello")
    assert ingest.main([]) == 2
    assert spool.has_pending()
    assert "usage" in capsys.readouterr().err


def test_a_hidden_run_does_not_ingest(repo, monkeypatch):
    put("UserPromptSubmit", repo, T0, prompt="hello")
    monkeypatch.setenv("NORTHSTAR_HIDDEN_RUN", "1")
    assert ingest.main(["--drain"]) == 0
    assert spool.has_pending() and not (paths.data_root() / "history.db").exists()


def test_main_exits_when_another_ingester_holds_the_lock(repo):
    put("UserPromptSubmit", repo, T0, prompt="hello")
    fd = spool.try_lock(spool.lock_path())
    try:
        assert ingest.main(["--drain", "--no-reconcile"]) == 0
        assert spool.has_pending()
    finally:
        spool.unlock(fd)
    assert ingest.main(["--drain", "--no-reconcile"]) == 0 and not spool.has_pending()


def test_an_unencrypted_data_root_leaves_the_spool_untouched_and_is_logged(repo, monkeypatch):
    put("UserPromptSubmit", repo, T0, prompt="hello")

    def refuse(*a, **k):
        raise db.EncryptionRequired("the data folder is not on an encrypted volume")

    monkeypatch.setattr(ingest, "SQLiteHistoryStore", refuse)
    assert ingest.main(["--drain"]) == 1
    assert spool.has_pending() and spool.watermark(spool.spool_files()[0]) == 0
    assert "not on an encrypted volume" in spool.log_path().read_text()


def test_an_unexpected_failure_is_logged_and_the_spool_is_kept(repo, monkeypatch):
    put("UserPromptSubmit", repo, T0, prompt="hello")
    monkeypatch.setattr(ingest, "drain", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("disk on fire")))
    assert ingest.main(["--drain"]) == 1
    assert spool.has_pending() and "RuntimeError: disk on fire" in spool.log_path().read_text()


def test_a_torn_last_line_does_not_make_the_ingester_loop(repo, monkeypatch):
    put("UserPromptSubmit", repo, T0, prompt="hello")
    with spool.spool_files()[0].open("ab") as fh:
        fh.write(b'{"v":1,"id":"01TORN"')  # a hook killed mid-write: it waits for ever, and is not a reason to go on
    real = ingest.drain
    calls = []
    monkeypatch.setattr(ingest, "drain", lambda *a, **k: (calls.append(1), real(*a, **k))[1])
    total = ingest.run(reconcile=False)
    assert total.messages == 1 and len(calls) == 1  # only a torn line waits: no second round
