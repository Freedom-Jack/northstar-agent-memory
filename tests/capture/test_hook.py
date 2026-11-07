"""The hook client: what it writes, what it never writes, that it never speaks, and that it is fast."""

from __future__ import annotations

import io
import json
import os
import stat
import subprocess
import sys
import textwrap
import time

import pytest

from northstar_agent_memory import paths
from northstar_agent_memory.capture import hook, spool

from . import T0, assert_throwaway_root, FAKE_TOKEN, SESSION, event, make_repo, put, write_settings


@pytest.fixture(autouse=True)
def _throwaway_root():
    assert_throwaway_root()
    yield
    assert_throwaway_root()


class Spawns:
    """Stands in for starting the ingester: records the calls."""

    def __init__(self):
        self.calls = 0

    def __call__(self, env=None):
        self.calls += 1


@pytest.fixture
def repo(tmp_path):
    personal = tmp_path / "personal"
    r = make_repo(personal)
    write_settings(personal)
    spool.write_encryption_stamp()  # what `capture install` leaves once the data folder is known to be encrypted (PL-3)
    return r


@pytest.fixture
def spawns():
    return Spawns()


def run(name, data, *, spawn=None, env=None, argv=None):
    """Run the hook in this process on `data`; returns (exit code, stdout of the process is checked by capsys)."""
    return hook.main(
        argv if argv is not None else [name], stdin=io.StringIO(json.dumps(data)), env=env if env is not None else {}, spawn=spawn,
    )


def spooled():
    """The records that carry a turn: the text-free markers written ahead of them are left out (see `markers`)."""
    return [r for r in spool.read_pending() if not spool.is_marker(r)]


def markers():
    return [r for r in spool.read_pending() if spool.is_marker(r)]


def nothing_written():
    """No spool, no log, no lock: the encryption stamp the fixture put in capture/ is the one thing there."""
    root = paths.data_root()
    left = {p.name for p in (root / "capture").iterdir()} if (root / "capture").exists() else set()
    return not (root / "spool").exists() and left <= {spool.stamp_path().name}


# --- the events -------------------------------------------------------------------------------------------------


def test_every_event_becomes_one_spool_record(repo, capsys):
    cases = [
        ("SessionStart", {"source": "startup", "model": "claude-opus-5-5"}),
        ("UserPromptSubmit", {"prompt": "Keep 1-minute readings for 7 days.", "permission_mode": "default"}),
        ("Stop", {"last_assistant_message": "Done: older readings are hourly averages.", "stop_hook_active": False}),
        ("PreCompact", {"trigger": "auto", "custom_instructions": "keep the schema"}),
        ("PostCompact", {"trigger": "auto", "compact_summary": "The user and Claude built a dashboard."}),
        ("SubagentStop", {"last_assistant_message": "Found 3 files.", "agent_id": "a1", "agent_type": "Explore"}),
        ("SessionEnd", {"reason": "clear"}),
    ]
    for name, fields in cases:
        assert run(name, event(name, repo, **fields)) == 0
    records = spooled()
    assert [r.event for r in records] == [c[0] for c in cases]
    for r in records:
        assert (r.session_id, r.cwd, r.scrub) == (SESSION, str(repo), "secrets")
        assert r.transcript_path == f"/nowhere/{SESSION}.jsonl"
    by = {r.event: r.payload for r in records}
    assert by["SessionStart"] == {"source": "startup", "model": "claude-opus-5-5"}
    assert by["UserPromptSubmit"] == {"prompt": "Keep 1-minute readings for 7 days.", "permission_mode": "default"}
    assert by["Stop"] == {"last_assistant_message": "Done: older readings are hourly averages.", "stop_hook_active": False}
    assert by["SubagentStop"]["agent_id"] == "a1" and by["SessionEnd"] == {"reason": "clear"}
    assert capsys.readouterr().out == ""


def test_the_event_name_may_come_from_the_payload_when_no_argument_is_given(repo):
    assert run(None, event("Stop", repo, last_assistant_message="ok"), argv=[]) == 0
    assert [r.event for r in spooled()] == ["Stop"]


def test_the_compaction_summary_is_never_kept_only_its_hash_and_size(repo):
    summary = "The user decided on hourly averages."
    run("PostCompact", event("PostCompact", repo, trigger="manual", compact_summary=summary))
    run("PreCompact", event("PreCompact", repo, trigger="manual", custom_instructions="remember the tie-break rule"))
    by = {r.event: r for r in spooled()}
    post, pre = by["PostCompact"], by["PreCompact"]
    assert "compact_summary" not in post.payload
    assert post.payload["compact_summary_chars"] == len(summary) and len(post.payload["compact_summary_sha256"]) == 64
    assert pre.payload == {"trigger": "manual", "has_custom_instructions": True}
    assert summary not in spool.spool_files()[0].read_text() and "tie-break" not in spool.spool_files()[0].read_text()


def test_only_the_named_fields_are_kept_never_tool_inputs_or_the_rest(repo):
    run("Stop", event("Stop", repo, last_assistant_message="ok", tool_input={"command": "cat ~/.ssh/id_ed25519"},
                      permission_mode="bypassPermissions", extra="x"))
    (r,) = spooled()
    assert r.payload == {"last_assistant_message": "ok"}


def test_events_the_client_does_not_handle_are_ignored(repo, spawns):
    for name in ("PostToolUse", "Notification", "SubagentStart", "PreToolUse", "Nonsense"):
        assert run(name, event(name, repo), spawn=spawns) == 0
    assert nothing_written() and spawns.calls == 0


def test_a_payload_without_a_session_id_is_ignored(repo, spawns):
    data = event("Stop", repo, last_assistant_message="ok")
    del data["session_id"]
    assert run("Stop", data, spawn=spawns) == 0
    assert nothing_written() and spawns.calls == 0


def test_a_worktree_under_a_personal_repository_is_captured(repo):
    worktree = repo / ".claude" / "worktrees" / "try-it"
    worktree.mkdir(parents=True)
    run("UserPromptSubmit", event("UserPromptSubmit", worktree, prompt="hello"))
    assert len(spooled()) == 1


# --- the gates: nothing written, nothing said -------------------------------------------------------------------------


def test_outside_the_personal_paths_nothing_is_written_and_nothing_printed(repo, tmp_path, spawns, capsys):
    other = tmp_path / "employer" / "repo"
    other.mkdir(parents=True)
    for name in ("SessionStart", "UserPromptSubmit", "Stop", "SessionEnd"):
        assert run(name, event(name, other, prompt="a secret plan", last_assistant_message="x"), spawn=spawns) == 0
    assert nothing_written()
    assert spawns.calls == 0
    out = capsys.readouterr()
    assert out.out == "" and out.err == ""


def test_with_no_settings_at_all_nothing_is_captured(tmp_path, spawns):
    assert run("Stop", event("Stop", tmp_path, last_assistant_message="x"), spawn=spawns) == 0
    assert nothing_written() and spawns.calls == 0


def test_a_session_in_the_data_root_is_never_captured(repo, spawns):
    write_settings(paths.data_root().parent, repo.parent)  # even a personal path that holds the data root
    paths.harness_cwd().mkdir(parents=True)
    assert run("UserPromptSubmit", event("UserPromptSubmit", paths.harness_cwd(), prompt="hi"), spawn=spawns) == 0
    assert not (paths.data_root() / "spool").exists() and spawns.calls == 0


def test_a_hidden_run_writes_nothing_even_in_scope_and_does_not_read_stdin(repo, spawns, capsys):
    class Exploding(io.StringIO):
        def read(self, *a, **k):
            raise AssertionError("a hidden run must exit before reading its input")

    code = hook.main(["UserPromptSubmit"], stdin=Exploding(), env={"NORTHSTAR_HIDDEN_RUN": "1"}, spawn=spawns)
    assert code == 0 and nothing_written() and spawns.calls == 0
    assert capsys.readouterr().out == ""
    assert run("Stop", event("Stop", repo, last_assistant_message="x"), spawn=spawns, env={"NORTHSTAR_HIDDEN_RUN": "1"}) == 0
    assert nothing_written()


def test_hooks_started_by_the_harness_are_skipped_end_to_end(repo, monkeypatch):
    """The marker the harness puts in a child's environment is the one the hook honours."""
    from northstar_agent_memory.models import harness

    env = harness.child_env([])
    assert run("Stop", event("Stop", repo, last_assistant_message="x"), env=env) == 0
    assert nothing_written()


# --- secrets ----------------------------------------------------------------------------------------------------


def test_secrets_are_replaced_before_the_spool_is_written(repo):
    prompt = f"push with {FAKE_TOKEN} please"
    reply = f"I will use {FAKE_TOKEN} now"
    run("UserPromptSubmit", event("UserPromptSubmit", repo, prompt=prompt))
    run("Stop", event("Stop", repo, last_assistant_message=reply))
    raw = spool.spool_files()[0].read_text()
    assert FAKE_TOKEN not in raw and "Ab1Cd2Ef3Gh4" not in raw
    user, assistant = spooled()
    assert user.payload["prompt"].startswith("push with ") and user.payload["prompt"].endswith(" please")
    assert user.scrub == "secrets"


def test_without_the_scrubber_a_real_run_writes_nothing_and_says_so_in_the_log(repo, monkeypatch, spawns):
    monkeypatch.setitem(sys.modules, "northstar_agent_memory.capture.secrets", None)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("NORTHSTAR_TEST_MODE", raising=False)
    assert run("Stop", event("Stop", repo, last_assistant_message=f"key {FAKE_TOKEN}"), spawn=spawns) == 0
    assert not (paths.data_root() / "spool").exists() and spawns.calls == 0
    assert "scrubber could not be loaded" in spool.log_path().read_text()


def test_in_a_test_run_a_missing_scrubber_falls_back_to_a_no_op_that_the_record_names(repo, monkeypatch):
    monkeypatch.setitem(sys.modules, "northstar_agent_memory.capture.secrets", None)
    run("Stop", event("Stop", repo, last_assistant_message="plain text"))
    (r,) = spooled()
    assert r.scrub == "noop" and r.payload["last_assistant_message"] == "plain text"


# --- errors are swallowed ----------------------------------------------------------------------------------------------


@pytest.mark.parametrize("stdin", ["", "   \n", "not json at all {", "[1, 2, 3]", '"a string"', "\x00\x01"])
def test_unusable_input_is_swallowed(repo, capsys, stdin):
    assert hook.main(["Stop"], stdin=io.StringIO(stdin), env={}, spawn=None) == 0
    out = capsys.readouterr()
    assert out.out == "" and out.err == ""


def test_an_error_while_writing_is_swallowed_after_one_log_line(repo, monkeypatch, capsys):
    def boom(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(spool, "append", boom)
    assert run("Stop", event("Stop", repo, last_assistant_message="x")) == 0
    out = capsys.readouterr()
    assert out.out == "" and out.err == ""
    lines = spool.log_path().read_text().splitlines()
    assert len(lines) == 1 and "OSError: disk full" in lines[0] and " hook " in lines[0]


def test_a_broken_settings_file_is_swallowed(tmp_path, capsys):
    paths.data_root().mkdir(parents=True)
    (paths.data_root() / "settings.toml").write_text("[capture\nbroken", encoding="utf-8")
    assert run("Stop", event("Stop", tmp_path, last_assistant_message="x")) == 0
    assert capsys.readouterr().out == ""
    assert "TOMLDecodeError" in spool.log_path().read_text()


def test_a_failure_to_start_the_ingester_is_swallowed_and_the_record_is_kept(repo):
    def refuse(env=None):
        raise OSError("no such program")

    assert run("Stop", event("Stop", repo, last_assistant_message="x"), spawn=refuse) == 0
    assert len(spooled()) == 1
    assert "no such program" in spool.log_path().read_text()


def test_an_oversized_event_is_not_spooled_and_is_logged(repo, monkeypatch):
    monkeypatch.setattr(hook, "MAX_STDIN_CHARS", 100)
    data = event("Stop", repo, last_assistant_message="x" * 500)
    assert run("Stop", data) == 0
    assert not (paths.data_root() / "spool").exists()
    assert "larger than the cap" in spool.log_path().read_text()


# --- starting the ingester ----------------------------------------------------------------------------------------------


def test_the_ingester_is_started_once_after_the_record_is_written(repo, spawns):
    run("Stop", event("Stop", repo, last_assistant_message="x"), spawn=spawns)
    assert spawns.calls == 1 and len(spooled()) == 1


def test_the_environment_can_turn_the_spawn_off(repo, spawns):
    run("Stop", event("Stop", repo, last_assistant_message="x"), spawn=spawns, env={hook.NO_SPAWN_ENV: "1"})
    assert spawns.calls == 0 and len(spooled()) == 1


def test_spawn_starts_the_drain_detached_unless_the_lock_is_held(monkeypatch):
    started = []

    class FakePopen:
        def __init__(self, argv, **kwargs):
            started.append((argv, kwargs))

    monkeypatch.setattr(subprocess, "Popen", FakePopen)
    assert hook.spawn_ingester({"A": "1"}) is True
    argv, kwargs = started[0]
    assert argv == [sys.executable, "-P", "-m", "northstar_agent_memory.capture.ingest", "--drain"]
    assert kwargs["cwd"] == str(paths.data_root())  # never the session's folder, which the hook inherits
    assert kwargs["start_new_session"] is True and kwargs["stdout"] == subprocess.DEVNULL and kwargs["stdin"] == subprocess.DEVNULL
    assert kwargs["env"] == {"A": "1"}

    fd = spool.try_lock(spool.lock_path())  # an ingester is running
    try:
        assert hook.spawn_ingester() is False
    finally:
        spool.unlock(fd)
    assert len(started) == 1
    assert hook.spawn_ingester() is True


# --- time ------------------------------------------------------------------------------------------------------


def test_the_hook_returns_well_under_100_ms_with_the_spawn_mocked(repo, spawns):
    data = event("UserPromptSubmit", repo, prompt="Please keep the readings. " * 40)
    run("UserPromptSubmit", data, spawn=spawns)  # warm: the first call imports the scrubber
    times = []
    for _ in range(25):
        start = time.perf_counter()
        assert run("UserPromptSubmit", data, spawn=spawns) == 0
        times.append(time.perf_counter() - start)
    times.sort()
    assert times[len(times) // 2] < 0.05, times
    assert times[int(len(times) * 0.9)] < 0.1, times
    assert spawns.calls == 26


def test_out_of_scope_exits_in_a_few_milliseconds(repo, tmp_path, spawns):
    data = event("Stop", tmp_path, last_assistant_message="x")
    times = []
    for _ in range(10):
        start = time.perf_counter()
        run("Stop", data, spawn=spawns)
        times.append(time.perf_counter() - start)
    assert sorted(times)[5] < 0.02, times


def test_the_hard_caps_are_well_under_the_hook_timeouts():
    # connectors-claude-code-and-codex.md §4.3: hook timeouts in seconds
    timeouts = {"SessionStart": 5, "UserPromptSubmit": 3, "Stop": 8, "SubagentStop": 2, "PreCompact": 2, "PostCompact": 2, "SessionEnd": 1}
    for name, limit in timeouts.items():
        assert hook.cap_for([name]) <= limit / 2, name
    assert hook.cap_for([]) == hook.DEFAULT_CAP_S


def test_the_watchdog_ends_the_process_with_status_zero():
    exits = []
    timer = hook.arm_watchdog(0.05, exits.append)
    time.sleep(0.3)
    assert exits == [0]
    timer.cancel()


def test_the_watchdog_can_be_cancelled_and_never_fires_early():
    exits = []
    timer = hook.arm_watchdog(5, exits.append)
    timer.cancel()
    time.sleep(0.05)
    assert exits == []


# --- the real process ---------------------------------------------------------------------------------------------


def _hook_process(argv, data, env_extra):
    env = {**os.environ, "NORTHSTAR_CAPTURE_NO_SPAWN": "1", **env_extra}
    env.pop("NORTHSTAR_HIDDEN_RUN", None)
    env.update(env_extra)
    start = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, "-m", "northstar_agent_memory.capture.hook", *argv], input=json.dumps(data),
        capture_output=True, text=True, env=env, timeout=30,
    )
    return proc, time.perf_counter() - start


def test_the_real_process_exits_0_prints_nothing_and_leaves_one_spool_line(repo):
    proc, seconds = _hook_process(["UserPromptSubmit"], event("UserPromptSubmit", repo, prompt="hello there"), {})
    assert (proc.returncode, proc.stdout, proc.stderr) == (0, "", "")
    assert [r.payload["prompt"] for r in spooled()] == ["hello there"]
    assert seconds < 2.0  # python start-up included; the budgets are 3 s and up


def test_the_real_process_out_of_scope_or_hidden_leaves_nothing(repo, tmp_path):
    other = tmp_path / "elsewhere"
    other.mkdir()
    proc, _ = _hook_process(["Stop"], event("Stop", other, last_assistant_message="x"), {})
    assert (proc.returncode, proc.stdout, proc.stderr) == (0, "", "")
    proc, _ = _hook_process(["Stop"], event("Stop", repo, last_assistant_message="x"), {"NORTHSTAR_HIDDEN_RUN": "1"})
    assert (proc.returncode, proc.stdout, proc.stderr) == (0, "", "")
    assert nothing_written()


def test_the_real_process_swallows_garbage_input(repo):
    proc = subprocess.run(
        [sys.executable, "-m", "northstar_agent_memory.capture.hook", "Stop"], input="{{{", capture_output=True, text=True,
        env={**os.environ, "NORTHSTAR_CAPTURE_NO_SPAWN": "1"}, timeout=30,
    )
    assert (proc.returncode, proc.stdout, proc.stderr) == (0, "", "")


def test_the_real_process_reads_a_prompt_in_utf8_whatever_the_locale(repo):
    data = event("UserPromptSubmit", repo, prompt="café 日本語 😀")
    env = {**os.environ, "NORTHSTAR_CAPTURE_NO_SPAWN": "1", "LC_ALL": "C", "LANG": "C", "PYTHONUTF8": "0", "PYTHONCOERCECLOCALE": "0"}
    proc = subprocess.run(
        [sys.executable, "-m", "northstar_agent_memory.capture.hook", "UserPromptSubmit"],
        input=json.dumps(data, ensure_ascii=False).encode("utf-8"), capture_output=True, env=env, timeout=30,
    )
    assert (proc.returncode, proc.stdout, proc.stderr) == (0, b"", b"")
    assert [r.payload["prompt"] for r in spooled()] == ["café 日本語 😀"]


# --- code from the session's folder never runs ------------------------------------------------------------------------


def poisoned_folder(base):
    """A session folder holding files named like a standard-library module and like this package. Importing either one
    writes `ran.txt` (and stops the process), so a test sees both that it ran and that it broke the run."""
    folder = base
    folder.mkdir(parents=True)
    note = folder.parent / (folder.name + "-ran.txt")
    body = f"open({str(note)!r}, 'a').write(__name__ + ' imported' + chr(10))\nraise SystemExit(0)\n"
    (folder / "dataclasses.py").write_text(body, encoding="utf-8")
    (folder / "northstar_agent_memory.py").write_text(body, encoding="utf-8")
    return folder, note


def wait_for(condition, seconds=30.0):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if condition():
            return True
        time.sleep(0.05)
    return False


def test_a_plain_python_dash_m_in_the_session_folder_would_run_its_files(tmp_path):
    """The control: the files above really do hijack `python -m` without -P, so the tests below prove something."""
    folder, note = poisoned_folder(tmp_path / "session")
    subprocess.run([sys.executable, "-c", "import dataclasses"], cwd=folder, env={**os.environ, "PYTHONSAFEPATH": ""}, timeout=30, check=False)
    assert note.exists() and "dataclasses imported" in note.read_text()


def test_the_ingester_is_started_with_p_and_from_the_data_root_so_the_session_folder_is_never_imported(repo, tmp_path, monkeypatch):
    folder, note = poisoned_folder(tmp_path / "session")
    put("SessionStart", repo, T0, source="startup", model="claude-opus-5-5")
    put("UserPromptSubmit", repo, T0 + 5, prompt="Keep the readings for a week.")
    monkeypatch.chdir(folder)  # the hook inherits the session's folder, as it does from Claude Code
    for var in ("NORTHSTAR_CAPTURE_NO_SPAWN", "NORTHSTAR_HIDDEN_RUN"):
        monkeypatch.delenv(var, raising=False)
    assert hook.spawn_ingester() is True
    assert wait_for(lambda: spool.state_path().exists()), "the ingester never finished a drain"
    assert wait_for(lambda: not spool.lock_held(spool.lock_path()))
    assert not note.exists(), note.read_text()
    assert spool.watermark(spool.spool_files()[0]) > 0  # it read the spool: it ran, and ran the real modules


def test_the_hook_runs_with_p_in_a_folder_with_look_alike_files_and_spools_the_turn(repo, tmp_path):
    folder, note = poisoned_folder(tmp_path / "session")
    entry = hook_command_of_the_installer()
    proc = subprocess.run(
        entry, input=json.dumps(event("UserPromptSubmit", repo, prompt="hello there")), capture_output=True, text=True,
        env={**os.environ, "NORTHSTAR_CAPTURE_NO_SPAWN": "1", "NORTHSTAR_HIDDEN_RUN": ""}, cwd=folder, timeout=30,
    )
    assert (proc.returncode, proc.stdout, proc.stderr) == (0, "", "")
    assert not note.exists()
    assert [r.payload["prompt"] for r in spooled()] == ["hello there"]


def hook_command_of_the_installer():
    from northstar_agent_memory.capture import install

    entry = install.hook_entry("UserPromptSubmit", sys.executable)
    assert entry["args"][0] == "-P"
    return [entry["command"], *entry["args"]]


def test_the_hook_itself_drops_the_working_folder_from_the_path_when_started_without_p(repo, tmp_path):
    folder, note = poisoned_folder(tmp_path / "session")
    (folder / "northstar_agent_memory.py").unlink()  # a look-alike package cannot be undone from inside the package
    proc = subprocess.run(
        [sys.executable, "-m", "northstar_agent_memory.capture.hook", "UserPromptSubmit"],
        input=json.dumps(event("UserPromptSubmit", repo, prompt="hello there")), capture_output=True, text=True,
        env={**os.environ, "NORTHSTAR_CAPTURE_NO_SPAWN": "1", "NORTHSTAR_HIDDEN_RUN": "", "PYTHONSAFEPATH": ""},
        cwd=folder, timeout=30,
    )
    assert (proc.returncode, proc.stdout, proc.stderr) == (0, "", "")
    assert not note.exists()
    assert [r.payload["prompt"] for r in spooled()] == ["hello there"]


# --- a turn whose scrubbing does not finish is not lost --------------------------------------------------------------


def test_a_text_free_marker_is_spooled_before_the_scrub_and_the_record_names_it(repo):
    prompt = "Keep the 1-minute readings for 7 days, my password is Tr0ub4dor&3 ok."
    seen = []

    def spy(text):  # what is already in the spool when the scrubber starts
        seen.append([r.payload for r in spool.read_pending()])
        return text

    real = spool.load_scrubber
    spool.load_scrubber = lambda: (spy, "secrets")
    try:
        run("UserPromptSubmit", event("UserPromptSubmit", repo, prompt=prompt, permission_mode="default"))
    finally:
        spool.load_scrubber = real
    assert seen and seen[0] == [{"marker": "scrub_pending", "sizes": {"prompt": len(prompt)}}]
    (marker,) = markers()
    assert (marker.event, marker.session_id, marker.cwd, marker.transcript_path) == (
        "UserPromptSubmit", SESSION, str(repo), f"/nowhere/{SESSION}.jsonl")
    assert marker.scrub == spool.MARKER_SCRUB and marker.payload == {"marker": "scrub_pending", "sizes": {"prompt": len(prompt)}}
    (record,) = spooled()
    assert record.raw["after_marker"] == marker.id and record.payload["prompt"] == prompt
    raw_marker = [line for line in spool.spool_files()[0].read_text().splitlines() if "scrub_pending" in line][0]
    assert "Tr0ub4dor" not in raw_marker and "readings" not in raw_marker  # no word of the turn


def test_replies_get_a_marker_too_and_events_without_text_do_not(repo):
    reply, found = "Done: older readings are hourly averages.", "Found 3 files."
    run("Stop", event("Stop", repo, last_assistant_message=reply))
    run("SubagentStop", event("SubagentStop", repo, last_assistant_message=found, agent_id="a1"))
    run("SessionStart", event("SessionStart", repo, source="startup", model="claude-opus-5-5"))
    run("SessionEnd", event("SessionEnd", repo, reason="clear"))
    run("PostCompact", event("PostCompact", repo, trigger="auto", compact_summary="A long summary."))
    assert [(m.event, m.payload["sizes"]) for m in markers()] == [
        ("Stop", {"last_assistant_message": len(reply)}), ("SubagentStop", {"last_assistant_message": len(found)})]


def test_a_prompt_with_nothing_in_it_needs_no_marker(repo):
    run("UserPromptSubmit", event("UserPromptSubmit", repo, prompt=""))
    assert markers() == [] and len(spooled()) == 1


def test_a_scrub_that_never_finishes_leaves_the_marker_and_no_record(repo):
    class Killed(BaseException):  # stands for the process being ended, which no `except Exception` sees
        pass

    def never(text):
        raise Killed

    real = spool.load_scrubber
    spool.load_scrubber = lambda: (never, "secrets")
    try:
        with pytest.raises(Killed):
            hook.capture("UserPromptSubmit", event("UserPromptSubmit", repo, prompt="a long prompt " * 1000), {}, spawn=None)
    finally:
        spool.load_scrubber = real
    assert spooled() == [] and len(markers()) == 1
    assert markers()[0].payload["sizes"] == {"prompt": len("a long prompt ") * 1000}


STUCK_SCRUB = textwrap.dedent(
    """
    import io, re, sys
    from northstar_agent_memory.capture import hook, spool

    def stuck(text):  # a regular expression that never finishes: the thread timer cannot run while it holds the lock
        re.match(r"(a+)+$", "a" * 60 + "b")
        return text

    spool.load_scrubber = lambda: (stuck, "secrets")
    hook.arm_watchdog(0.3)
    code = hook.main(["UserPromptSubmit"], stdin=io.StringIO(sys.argv[1]), env={"NORTHSTAR_CAPTURE_NO_SPAWN": "1"}, spawn=None)
    sys.exit(code + 7)  # reached only if the watchdog did not end the process
    """
)


@pytest.mark.skipif(not hasattr(__import__("signal"), "setitimer"), reason="no interval timer on this platform")
def test_the_watchdog_ends_a_process_stuck_in_a_scrub_and_the_turn_is_still_known(repo):
    prompt = "the prompt that never finishes scrubbing"
    start = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, "-P", "-c", STUCK_SCRUB, json.dumps(event("UserPromptSubmit", repo, prompt=prompt))],
        capture_output=True, text=True, env={**os.environ, "NORTHSTAR_HIDDEN_RUN": ""}, timeout=30,
    )
    assert time.perf_counter() - start < 5
    assert (proc.returncode, proc.stdout, proc.stderr) == (0, "", "")  # the watchdog's exit(0), not the script's 7
    assert spooled() == []
    (marker,) = markers()
    assert (marker.event, marker.session_id, marker.transcript_path) == ("UserPromptSubmit", SESSION, f"/nowhere/{SESSION}.jsonl")
    assert marker.payload["sizes"] == {"prompt": len(prompt)}
    assert prompt not in spool.spool_files()[0].read_text()
    log = spool.log_path().read_text()
    assert "watchdog: ended the hook after 0.3 s during scrub (event UserPromptSubmit)" in log and "marker record stands for the turn" in log


def test_the_watchdog_says_what_the_hook_was_doing(repo, monkeypatch):
    monkeypatch.setitem(hook._progress, "stage", "spool")
    monkeypatch.setitem(hook._progress, "event", "Stop")
    monkeypatch.setitem(hook._progress, "marker", False)
    exits = []
    dog = hook.arm_watchdog(0.05, exits.append)
    time.sleep(0.3)
    dog.cancel()
    assert exits == [0]  # once, though two timers are armed
    (line,) = spool.log_path().read_text().splitlines()
    assert "watchdog: ended the hook after 0.05 s during spool (event Stop)" in line and "marker" not in line


def test_cancelling_the_watchdog_puts_the_signal_handler_back(repo):
    import signal

    before = signal.getsignal(signal.SIGALRM)
    dog = hook.arm_watchdog(5, lambda code: None)
    dog.cancel()
    assert signal.getsignal(signal.SIGALRM) == before and signal.getitimer(signal.ITIMER_REAL)[0] == 0


# --- the encryption stamp ---------------------------------------------------------------------------------------------


def log_text():
    return spool.log_path().read_text() if spool.log_path().exists() else ""


def test_without_a_stamp_nothing_is_written_and_the_log_says_why(repo, spawns):
    spool.stamp_path().unlink()
    assert run("Stop", event("Stop", repo, last_assistant_message="x"), spawn=spawns) == 0
    assert not (paths.data_root() / "spool").exists() and spawns.calls == 0
    assert "nothing was written: no encryption stamp: run `northstar capture install`" in log_text()


@pytest.mark.parametrize(
    "damage, words",
    [
        (lambda s: "not json {", "cannot be read"),
        (lambda s: json.dumps({**json.loads(s), "v": 99}), "not in a form this version knows"),
        (lambda s: json.dumps({**json.loads(s), "data_root": "/somewhere/else"}), "for another data folder"),
        (lambda s: json.dumps({**json.loads(s), "device": json.loads(s)["device"] + 1}), "another volume"),
        (lambda s: json.dumps([1, 2]), "not in a form this version knows"),
    ],
)
def test_a_stamp_that_does_not_fit_this_data_root_is_as_good_as_none(repo, spawns, damage, words):
    path = spool.stamp_path()
    path.write_text(damage(path.read_text()), encoding="ascii")
    assert run("UserPromptSubmit", event("UserPromptSubmit", repo, prompt="hello"), spawn=spawns) == 0
    assert not (paths.data_root() / "spool").exists() and spawns.calls == 0
    assert words in log_text()


def test_every_event_is_refused_without_a_stamp_and_taken_with_one(repo, spawns):
    spool.stamp_path().unlink()
    for name in hook.FIELDS:
        run(name, event(name, repo), spawn=spawns)
    assert spool.read_pending() == []
    spool.write_encryption_stamp()
    for name in hook.FIELDS:
        run(name, event(name, repo), spawn=spawns)
    assert [r.event for r in spooled()] == list(hook.FIELDS)


def test_out_of_scope_sessions_are_ignored_before_the_stamp_is_looked_at(repo, tmp_path, spawns):
    spool.stamp_path().unlink()
    other = tmp_path / "elsewhere"
    other.mkdir()
    assert run("Stop", event("Stop", other, last_assistant_message="x"), spawn=spawns) == 0
    assert not (paths.data_root() / "spool").exists() and not spool.log_path().exists()  # silent, as the scope gate is


def test_the_real_process_writes_nothing_without_a_stamp(repo):
    spool.stamp_path().unlink()
    proc, _ = _hook_process(["UserPromptSubmit"], event("UserPromptSubmit", repo, prompt="hello there"), {})
    assert (proc.returncode, proc.stdout, proc.stderr) == (0, "", "")
    assert not (paths.data_root() / "spool").exists()
    assert "no encryption stamp" in log_text()


def test_the_spools_folders_are_owner_only_parents_included(repo):
    run("Stop", event("Stop", repo, last_assistant_message="x"))
    root = paths.data_root()
    for folder in (root / "spool", root / "spool" / "claude-code", root / "capture"):
        assert stat.S_IMODE(folder.stat().st_mode) == 0o700, folder


# --- with the ingester ----------------------------------------------------------------------------------------------


def test_the_ingester_reads_a_marker_as_a_record_that_makes_no_message_and_stores_the_turn_once(repo):
    from northstar_agent_memory.capture import ingest
    from northstar_agent_memory.core.history import SQLiteHistoryStore

    run("SessionStart", event("SessionStart", repo, source="startup", model="claude-opus-5-5"))
    run("UserPromptSubmit", event("UserPromptSubmit", repo, prompt="Keep the readings for a week."))
    run("Stop", event("Stop", repo, last_assistant_message="Done: a week."))
    assert len(markers()) == 2
    result = ingest.run(reconcile=False)
    assert (result.records, result.messages, result.skipped, result.errors, result.corrupt) == (5, 2, 3, 0, 0)  # 2 markers + SessionStart
    with SQLiteHistoryStore() as store:
        texts = [r[0] for r in store.conn.execute("SELECT text FROM message ORDER BY ordinal")]
    assert texts == ["Keep the readings for a week.", "Done: a week."]


def test_a_marker_alone_still_tells_the_ingester_the_session_and_its_transcript(repo):
    """The hook was ended mid-scrub: only the marker is in the spool. The ingester must not fail on it, and must learn
    the session, so that the transcript can be reconciled later."""
    from northstar_agent_memory.capture import ingest

    spool.append(spool.make_marker("UserPromptSubmit", SESSION, {"prompt": 900}, transcript_path="/nowhere/t.jsonl", cwd=str(repo)))
    result = ingest.run(reconcile=False)
    assert (result.records, result.messages, result.errors, result.sources) == (1, 0, 0, 1)
    state = json.loads(spool.state_path().read_text())
    assert state["sessions"][SESSION]["transcript_path"] == "/nowhere/t.jsonl"
