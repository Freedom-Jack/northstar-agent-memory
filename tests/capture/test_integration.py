"""The capture parts together: the real hook client writes the spool, the ingester reads it and reconciles the transcript,
the backfill reads the same transcripts afterwards. Each test is one of the problems found in the capture check, driven
through the whole path rather than one module. Every fixture is invented; the data root is the throwaway one."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys

import pytest

from northstar_agent_memory import paths
from northstar_agent_memory.capture import hook, ingest, scope, spool
from northstar_agent_memory.capture.backfill import backfill
from northstar_agent_memory.capture.origin import NORTHSTAR_TAG, wrap_northstar
from northstar_agent_memory.core.history import SQLiteHistoryStore

from . import FAKE_TOKEN, SESSION, T0, assert_throwaway_root, event, iso, make_repo, t_assistant, t_user, write_settings
from . import write_transcript


@pytest.fixture(autouse=True)
def _throwaway_root():
    assert_throwaway_root()
    yield
    assert_throwaway_root()


@pytest.fixture
def repo(tmp_path):
    personal = tmp_path / "personal"
    r = make_repo(personal)
    write_settings(personal)
    spool.write_encryption_stamp()  # what `capture install` leaves (PL-3)
    return r


@pytest.fixture
def projects(tmp_path):
    """Claude Code's own projects folder for the session below."""
    return tmp_path / "claude" / "projects"


@pytest.fixture
def transcript(projects):
    return projects / "energy-dash" / f"{SESSION}.jsonl"


def fire(name, cwd, at, *, session=SESSION, transcript_path=None, **fields):
    """One hook run, in this process, at epoch time `at` (the spool record's recorded_at is the wall clock, so the time
    the ingester sees is set on the written record afterwards). Returns the exit code."""
    data = event(name, cwd, session, **fields)
    if transcript_path is not None:
        data["transcript_path"] = str(transcript_path)
    before = len(spool.read_pending())
    code = hook.main([name], stdin=io.StringIO(json.dumps(data)), env={hook.NO_SPAWN_ENV: "1"}, spawn=None)
    _retime(before, at)
    return code


def _retime(before, at):
    """The hook stamps real time on its records; the tests want an invented morning, so each file is rewritten."""
    (path,) = spool.spool_files()
    lines = path.read_text(encoding="utf-8").splitlines()
    out = []
    for n, line in enumerate(lines):
        obj = json.loads(line)
        if n >= before:
            obj["recorded_at"] = iso(at)
            obj["occurred_at"] = iso(at)
        out.append(json.dumps(obj))
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def rows(session=SESSION):
    with SQLiteHistoryStore() as store:
        stored = store.messages_for_source(session)
    # In the order said, not the order captured: a reconciled message is appended after later ones (ingest.reconcile).
    stored.sort(key=lambda m: (m.message.branch or "", m.message.occurred_at))
    return [(m.message.branch, m.message.speaker, m.message.origin, m.message.text, m.fidelity) for m in stored]


def everything():
    with SQLiteHistoryStore() as store:
        return " ".join(r[0] for r in store.conn.execute("SELECT text FROM message"))


def run_backfill(projects):
    with SQLiteHistoryStore() as store:
        return backfill(projects, store, progress=None)


def sub_line(text, at, uuid, agent_id, cwd):
    line = t_assistant(text, at, uuid, cwd=str(cwd))
    line.update(isSidechain=True, agentId=agent_id)
    return line


# --- (1) a turn made outside the personal folders is not reconciled --------------------------------------------------------


def test_1_a_turn_after_a_cd_out_is_not_captured_by_reconciliation_and_not_by_the_backfill(repo, transcript, projects, tmp_path):
    work = tmp_path / "work" / "client"
    work.mkdir(parents=True)
    fire("SessionStart", repo, T0, transcript_path=transcript, source="startup")
    fire("SessionEnd", repo, T0 + 150, transcript_path=transcript, reason="other")  # both hooks of the later turns were lost
    write_transcript(
        transcript,
        t_user("Look at the notes.", T0 + 5, "u1", cwd=str(repo)), t_assistant("Opening them.", T0 + 10, "a1", cwd=str(repo)),
        t_user("Now the Acme invoice 4411.", T0 + 60, "u2", cwd=str(work)), t_assistant("It is for Acme.", T0 + 70, "a2", cwd=str(work)),
    )
    result = ingest.run(now=T0 + 200)
    assert (result.reconciled, result.errors) == (2, 0)
    run_backfill(projects)
    assert [(r[1], r[3]) for r in rows() if r[3] and r[0] is None and r[1] != "system"] == [("user", "Look at the notes."), ("assistant", "Opening them.")]
    assert "Acme" not in everything() and "4411" not in everything()


# --- (2) a subagent's final message once ------------------------------------------------------------------------------------


def test_2_a_subagent_final_stored_live_is_not_stored_again_by_reconciliation_or_the_backfill(repo, transcript, projects):
    final = "The subagent found three TODOs."
    fire("SessionStart", repo, T0, transcript_path=transcript, source="startup")
    fire("UserPromptSubmit", repo, T0 + 5, transcript_path=transcript, prompt="Scan for TODOs.", prompt_id="p1")
    fire("SubagentStop", repo, T0 + 15, transcript_path=transcript, last_assistant_message=final, agent_id="a1b2c3", agent_type="Explore")
    fire("Stop", repo, T0 + 20, transcript_path=transcript, last_assistant_message="Three TODOs found.", prompt_id="p1")
    fire("SessionEnd", repo, T0 + 30, transcript_path=transcript, reason="other")
    write_transcript(
        transcript, t_user("Scan for TODOs.", T0 + 5, "u1", cwd=str(repo)), t_assistant("Three TODOs found.", T0 + 20, "a1", cwd=str(repo)),
    )
    sub = projects / "energy-dash" / SESSION / "subagents" / "agent-a1b2c3.jsonl"
    write_transcript(sub, sub_line(final, T0 + 14, "s1", "a1b2c3", repo))  # the file says which agent it is
    ingest.run(now=T0 + 200)
    before = rows()
    assert [r[0] for r in before if r[3] == final] == ["sidechain:a1b2c3"]
    report = run_backfill(projects)
    assert rows() == before and report.messages_written == 0
    # and by a file that only carries the id in its name
    write_transcript(sub, {k: v for k, v in sub_line(final, T0 + 14, "s1", "a1b2c3", repo).items() if k != "agentId"})
    run_backfill(projects)
    assert [r[3] for r in rows() if r[0] == "sidechain:a1b2c3"] == [final]


# --- (3) a Northstar block is never the user's words, and nothing is doubled ----------------------------------------------


def test_3_a_northstar_block_is_its_own_message_live_in_reconciliation_and_in_the_backfill(repo, transcript, projects):
    block = wrap_northstar("Decision D1: lowest device id wins.")
    prompt = f"What was decided about ties?\n{block}"
    fire("SessionStart", repo, T0, transcript_path=transcript, source="startup")
    fire("UserPromptSubmit", repo, T0 + 5, transcript_path=transcript, prompt=prompt, prompt_id="p1")
    fire("Stop", repo, T0 + 9, transcript_path=transcript, last_assistant_message="D1.", prompt_id="p1")
    fire("SessionEnd", repo, T0 + 20, transcript_path=transcript, reason="other")
    write_transcript(transcript, t_user(prompt, T0 + 5, "u1", cwd=str(repo)), t_assistant("D1.", T0 + 9, "a1", cwd=str(repo)))
    result = ingest.run(now=T0 + 200)
    assert (result.reconciled, result.mismatches) == (0, 0)
    before = rows()
    assert [(r[1], r[2], r[3]) for r in before if r[1] != "system"] == [
        ("user", "typed", "What was decided about ties?"),
        ("northstar", "northstar_injected", "Decision D1: lowest device id wins."),
        ("assistant", "assistant_output", "D1."),
    ]
    run_backfill(projects)
    assert rows() == before and NORTHSTAR_TAG not in everything()


# --- (4) the ingester never imports a file from the session's folder ------------------------------------------------------


def test_4_the_real_hook_spawn_does_not_import_a_module_named_file_from_the_session_folder(repo, tmp_path):
    bad = repo / "src"
    marker = tmp_path / "imported.txt"
    for name in ("dataclasses.py", "json.py", "northstar_agent_memory.py"):
        (bad / name).write_text(f"open({str(marker)!r}, 'a').write({name!r})\nraise SystemExit(3)\n", encoding="utf-8")
    fire("UserPromptSubmit", bad, T0, prompt="Keep the readings for a week.", prompt_id="p1")  # spooled, not spawned
    env = {**os.environ, "NORTHSTAR_HOME": str(paths.data_root())}
    proc = subprocess.Popen(
        [sys.executable, "-P", "-m", "northstar_agent_memory.capture.ingest", "--drain"],
        cwd=str(bad), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )  # the command the hook builds, but started in the session's folder: with -P it still imports nothing from it
    proc.communicate(timeout=60)
    assert not marker.exists()
    # and the hook's own spawn, which the installer does not need to protect: the folder is the data root's
    calls = []
    real = subprocess.Popen
    subprocess.Popen = lambda *a, **kw: calls.append((a, kw))  # type: ignore[assignment]
    try:
        hook.spawn_ingester(env)
    finally:
        subprocess.Popen = real
    (args, kw), = calls
    assert args[0][:4] == [sys.executable, "-P", "-m", "northstar_agent_memory.capture.ingest"] and kw["cwd"] == str(paths.data_root())


# --- (5) the commits made in a session are recorded -----------------------------------------------------------------------


def _git(folder, *args, when=None):
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "GIT_AUTHOR_NAME": "Robin",
           "GIT_AUTHOR_EMAIL": "robin@example.org", "GIT_COMMITTER_NAME": "Robin", "GIT_COMMITTER_EMAIL": "robin@example.org"}
    if when:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = when
    done = subprocess.run(["git", "-c", "commit.gpgsign=false", "-C", str(folder), *args], capture_output=True, text=True,
                          env=env, check=True, stdin=subprocess.DEVNULL)
    return done.stdout.strip()


def test_5_the_commits_of_a_hooked_session_are_recorded_and_those_of_an_outside_folder_are_not(repo, tmp_path):
    _git(repo, "init")
    fire("SessionStart", repo, T0, source="startup")
    fire("UserPromptSubmit", repo, T0 + 5, prompt="Add the export button.", prompt_id="p1")
    (repo / "f.txt").write_text("x\n", encoding="utf-8")
    _git(repo, "add", "f.txt")
    _git(repo, "commit", "-m", "Add the export button", when=iso(T0 + 30))
    sha = _git(repo, "rev-parse", "HEAD")
    fire("Stop", repo, T0 + 40, last_assistant_message="Added.", prompt_id="p1")
    fire("SessionEnd", repo, T0 + 60, reason="other")
    result = ingest.run(reconcile=False, now=T0 + 61)
    assert result.work_events == 1
    with SQLiteHistoryStore() as store:
        assert [(r["ref"], r["source_id"]) for r in store.conn.execute("SELECT * FROM work_event")] == [(sha, SESSION)]
    outside = tmp_path / "work" / "client"
    outside.mkdir(parents=True)
    _git(outside, "init")
    (outside / "f.txt").write_text("x\n", encoding="utf-8")
    _git(outside, "add", "f.txt")
    _git(outside, "commit", "-m", "Client work", when=iso(T0 + 30))
    fire("SessionEnd", outside, T0 + 60, session="5e55a0a0-0000-4000-8000-000000000002", reason="other")  # the hook refuses it
    assert ingest.run(reconcile=False, now=T0 + 300).work_events == 0


# --- (6) one event delivered twice ----------------------------------------------------------------------------------------


def test_6_an_event_the_hook_ran_twice_is_stored_once_and_the_marker_does_not_count_as_a_message(repo, transcript):
    for at in (T0 + 5, T0 + 6):  # the same payload, registered twice: two hook runs
        fire("UserPromptSubmit", repo, at, transcript_path=transcript, prompt="Add the export button.", prompt_id="p1")
        fire("Stop", repo, at + 5, transcript_path=transcript, last_assistant_message="Added.", prompt_id="p1")
    result = ingest.run(reconcile=False, now=T0 + 100)
    assert (result.messages, result.duplicates, result.errors) == (2, 2, 0)
    assert [(r[1], r[3]) for r in rows()] == [("user", "Add the export button."), ("assistant", "Added.")]


# --- (7) intermediate assistant text, which live capture lacks, is filled in once ----------------------------------------


def test_7_intermediate_assistant_text_is_added_by_reconciliation_and_the_backfill_adds_nothing(repo, transcript, projects):
    fire("SessionStart", repo, T0, transcript_path=transcript, source="startup")
    fire("UserPromptSubmit", repo, T0 + 5, transcript_path=transcript, prompt="Add the export button.", prompt_id="p1")
    fire("Stop", repo, T0 + 20, transcript_path=transcript, last_assistant_message="The button is in the header.", prompt_id="p1")
    fire("SessionEnd", repo, T0 + 30, transcript_path=transcript, reason="other")
    tool = t_assistant("x", T0 + 12, "a2", cwd=str(repo))
    tool["message"]["content"] = [{"type": "tool_use", "id": "t1", "name": "Edit", "input": {}}]
    write_transcript(
        transcript, t_user("Add the export button.", T0 + 5, "u1", cwd=str(repo)),
        t_assistant("First I will look at the header.", T0 + 8, "a1", cwd=str(repo)), tool,
        t_assistant("The button is in the header.", T0 + 20, "a3", cwd=str(repo)),
    )
    result = ingest.run(now=T0 + 200)
    assert (result.reconciled, result.mismatches, result.errors) == (1, 0, 0)
    got = rows()
    assert [(r[1], r[3], r[4]) for r in got if r[1] != "system"] == [
        ("user", "Add the export button.", "verbatim"),
        ("assistant", "First I will look at the header.", "reconciled"),
        ("assistant", "The button is in the header.", "verbatim"),
    ]
    assert run_backfill(projects).messages_written == 0 and rows() == got


# --- (8) a slow scrub does not lose the turn --------------------------------------------------------------------------------


def test_8_a_turn_whose_scrub_was_cut_short_is_recovered_from_the_transcript_with_its_secret_removed(repo, transcript):
    class Killed(BaseException):
        pass

    def never(text):
        raise Killed

    real = spool.load_scrubber
    spool.load_scrubber = lambda: (never, "secrets")
    try:
        data = event("UserPromptSubmit", repo, transcript_path=str(transcript), prompt=f"Use the token {FAKE_TOKEN} for the sync.", prompt_id="p1")
        with pytest.raises(Killed):
            hook.capture("UserPromptSubmit", data, {hook.NO_SPAWN_ENV: "1"}, spawn=None)
    finally:
        spool.load_scrubber = real
    assert [r for r in spool.read_pending() if not spool.is_marker(r)] == []
    _retime(0, T0 + 5)
    fire("SessionEnd", repo, T0 + 30, transcript_path=transcript, reason="other")
    write_transcript(
        transcript, t_user(f"Use the token {FAKE_TOKEN} for the sync.", T0 + 5, "u1", cwd=str(repo)),
        t_assistant("Synced.", T0 + 9, "a1", cwd=str(repo)),
    )
    result = ingest.run(now=T0 + 200)  # the marker told it the session and the transcript
    assert (result.reconciled, result.errors) == (2, 0)
    got = [(r[1], r[4]) for r in rows() if r[1] != "system"]
    assert got == [("user", "reconciled"), ("assistant", "reconciled")]
    assert FAKE_TOKEN not in everything() and "Use the token" in everything()


# --- (9) the hook writes nothing without the encryption stamp ---------------------------------------------------------------


def test_9_without_the_stamp_nothing_is_written_and_after_install_it_is(tmp_path):
    personal = tmp_path / "personal"
    r = make_repo(personal)
    write_settings(personal)
    data = event("UserPromptSubmit", r, prompt="Keep the readings.", prompt_id="p1")
    hook.main(["UserPromptSubmit"], stdin=io.StringIO(json.dumps(data)), env={hook.NO_SPAWN_ENV: "1"}, spawn=None)
    assert not (paths.data_root() / "spool").exists()
    assert "encrypt" in spool.log_path().read_text().lower()
    spool.write_encryption_stamp()
    hook.main(["UserPromptSubmit"], stdin=io.StringIO(json.dumps(data)), env={hook.NO_SPAWN_ENV: "1"}, spawn=None)
    assert [x.payload.get("prompt") for x in spool.read_pending() if not spool.is_marker(x)] == ["Keep the readings."]


# --- (10) a case-different path does not escape the gate --------------------------------------------------------------------


@pytest.mark.parametrize("insensitive", [True, False])
def test_10_a_path_in_another_case_follows_the_platform_through_the_hook_and_the_ingester(repo, monkeypatch, insensitive):
    monkeypatch.setattr(scope, "CASE_INSENSITIVE", insensitive)
    other_case = type(repo)(str(repo).replace("personal", "PERSONAL"))
    data = event("UserPromptSubmit", other_case, prompt="Keep the readings.", prompt_id="p1")
    hook.main(["UserPromptSubmit"], stdin=io.StringIO(json.dumps(data)), env={hook.NO_SPAWN_ENV: "1"}, spawn=None)
    written = [x for x in spool.read_pending() if not spool.is_marker(x)]
    assert bool(written) is insensitive
    # a record already in the spool is checked again by the ingester under the same rule
    if not insensitive:
        spool.append(spool.make_record("UserPromptSubmit", SESSION, {"prompt": "Keep the readings."}, transcript_path="/nowhere/t.jsonl", cwd=str(other_case)))
    result = ingest.run(reconcile=False)
    assert (result.messages == 1) is insensitive and (result.out_of_scope == 1) is (not insensitive)

