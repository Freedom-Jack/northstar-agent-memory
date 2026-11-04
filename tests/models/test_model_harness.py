"""What the two headless routes share: running a program, the empty folder, the prompt and the failure rules."""

import dataclasses
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

import model_fakes as f
from northstar_agent_memory.models import harness
from northstar_agent_memory.models.harness import (
    LIMIT,
    MODEL,
    OTHER,
    REFUSED,
    SIGN_IN,
    HarnessResult,
    call_timeout,
    child_env,
    classify,
    excerpt,
    render_prompt,
    working_folder,
)
from northstar_agent_memory.models.harness import run_process as real_run_process  # before the autouse fixture refuses it
from northstar_agent_memory.models.port import ModelError, ModelResult, Usage
from northstar_agent_memory.paths import harness_cwd


def py(code: str) -> list[str]:
    return [sys.executable, "-I", "-c", code]


# --- running a program (real, harmless child processes) -----------------------------------------------


def test_a_program_gets_its_stdin_folder_and_environment_and_its_output_comes_back(tmp_path):
    code = (
        "import os, sys; sys.stdout.write(sys.stdin.read().upper() + '|' + os.getcwd() + '|' + os.environ['NORTHSTAR_X']);"
        "sys.stderr.write('warning'); sys.exit(3)"
    )
    proc = real_run_process(py(code), stdin="héllo\n", cwd=tmp_path, env={**os.environ, "NORTHSTAR_X": "1"}, timeout_s=30)
    assert proc.returncode == 3 and proc.stderr == "warning"
    assert proc.stdout == f"HÉLLO\n|{tmp_path.resolve()}|1"


def test_output_that_is_not_utf8_is_replaced_not_fatal(tmp_path):
    proc = real_run_process(py("import sys; sys.stdout.buffer.write(b'ok \\xff')"), stdin="", cwd=tmp_path, env=dict(os.environ), timeout_s=30)
    assert proc.stdout == "ok �"


def test_a_program_that_runs_too_long_is_stopped(tmp_path):
    started = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        real_run_process(py("import time; time.sleep(60)"), stdin="", cwd=tmp_path, env=dict(os.environ), timeout_s=0.5)
    assert time.monotonic() - started < 20


def test_a_timeout_stops_everything_the_program_started(tmp_path):
    pid_file = tmp_path / "grandchild.pid"
    grandchild = f"import os, time; open({str(pid_file)!r}, 'w').write(str(os.getpid())); time.sleep(60)"
    parent = f"import subprocess, sys, time; subprocess.Popen([sys.executable, '-I', '-c', {grandchild!r}]); time.sleep(60)"
    with pytest.raises(subprocess.TimeoutExpired):
        real_run_process(py(parent), stdin="", cwd=tmp_path, env=dict(os.environ), timeout_s=3)
    pid = int(pid_file.read_text())
    for _ in range(100):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.1)
    os.kill(pid, 9)
    pytest.fail("the grandchild was still running after the timeout")


def test_a_program_that_cannot_start_raises_os_error(tmp_path):
    with pytest.raises(OSError):
        real_run_process([str(tmp_path / "no-such-program")], stdin="", cwd=tmp_path, env=dict(os.environ), timeout_s=5)


# --- the empty folder ----------------------------------------------------------------------------


def test_the_harness_folder_is_made_under_the_data_root_and_reused_while_empty(isolated_home):
    assert not harness_cwd().exists()
    with working_folder() as first:
        assert first == harness_cwd() == isolated_home / "data" / "harness-cwd" and first.is_dir()
    with working_folder() as second:
        assert second == first


def test_a_folder_with_something_in_it_is_left_alone_and_a_fresh_one_is_used_and_removed():
    root = harness_cwd()
    root.mkdir(parents=True)
    (root / ".claude").mkdir()
    with working_folder() as cwd:
        assert cwd.parent == root and cwd != root and not any(cwd.iterdir())
        (cwd / "scratch.txt").write_text("a run left this")
    assert not cwd.exists() and (root / ".claude").exists()


def test_a_folder_that_cannot_be_made_is_a_model_error():
    harness_cwd().parent.mkdir(parents=True)
    harness_cwd().write_text("a file where the folder should be")
    with pytest.raises(ModelError, match="could not prepare the empty folder"):
        with working_folder():
            pytest.fail("no folder was made")


# --- the prompt ----------------------------------------------------------------------------------


def test_one_user_message_is_sent_exactly_as_it_is():
    assert render_prompt([{"role": "user", "content": "  two  lines\nof text \n"}]) == "  two  lines\nof text \n"


def test_a_longer_exchange_has_its_earlier_turns_in_a_transcript():
    prompt = render_prompt(
        [
            {"role": "user", "content": "a"},
            {"role": "assistant", "content": "b"},
            {"role": "user", "content": "c"},
            {"role": "assistant", "content": "d"},
            {"role": "user", "content": "e"},
        ]
    )
    assert prompt.index('<turn role="user">\na\n') < prompt.index('<turn role="assistant">\nb\n') < prompt.index("c\n</turn>")
    assert prompt.index("</conversation_so_far>") < prompt.index("latest message, which follows.") < prompt.rindex("e")
    assert prompt.endswith("\n\ne")


@pytest.mark.parametrize(
    ("messages", "problem"),
    [
        ([], "no messages"),
        ([{"role": "assistant", "content": "x"}], "must come from the user"),
        ([{"role": "user", "content": ""}], "is empty"),
        ([{"role": "tool", "content": "x"}, {"role": "user", "content": "y"}], "role 'tool'"),
    ],
)
def test_a_list_of_messages_that_cannot_be_sent_says_why(messages, problem):
    with pytest.raises(ModelError, match=problem):
        render_prompt(messages)


# --- failures ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("You've hit your session limit · resets 3pm", LIMIT),
        ("You hit your spend cap set by the owner of your workspace.", LIMIT),
        ("Your workspace is out of credits. Add credits to continue.", LIMIT),
        ("Not logged in · Please run /login", SIGN_IN),
        ("Your access token could not be refreshed. Please log out and sign in again.", SIGN_IN),
        ("There's an issue with the selected model (x). It may not exist or you may not have access to it.", MODEL),
        ("The model `gpt-6` does not exist or you do not have access to it.", MODEL),
        ("This request was blocked due to a misalignment policy violation.", REFUSED),
        ("API Error: Repeated 529 Overloaded errors", OTHER),
        ("", OTHER),
        # words that look like a status or a model problem but are not
        ("Model metadata for `gpt-x` not found. Defaulting to fallback metadata", OTHER),
        ("read 4290 tokens from port 4403", OTHER),
    ],
)
def test_what_a_program_says_decides_the_kind_of_failure(text, kind):
    assert classify(text) == kind


def test_a_status_decides_only_what_the_words_do_not():
    assert classify("unclear", 429) == LIMIT and classify("unclear", 402) == LIMIT
    assert classify("unclear", 401) == SIGN_IN and classify("unclear", 403) == SIGN_IN
    assert classify("unclear", 404) == MODEL
    assert classify("unclear", 500) == OTHER and classify("unclear", None) == OTHER
    assert classify("You've hit your weekly limit", 401) == LIMIT  # the words are the more specific


def test_an_excerpt_is_one_short_line_with_key_and_token_values_removed(monkeypatch):
    monkeypatch.setenv("SOME_SERVICE_API_KEY", "abcdefgh-12345678")
    monkeypatch.setenv("SHORT_TOKEN", "abc")  # too short to be worth hiding: it would mangle ordinary words
    monkeypatch.setenv("PLAIN_SETTING", "visible-value-123")
    text = "line one\n\n  line   two abcdefgh-12345678 abc visible-value-123"
    assert excerpt(text) == "line one line two [redacted] abc visible-value-123"
    assert excerpt("x" * 500, 20) == "x" * 19 + "…"


def test_the_child_environment_drops_what_it_is_told_and_adds_what_it_is_given(monkeypatch):
    monkeypatch.setenv("NORTHSTAR_DROP", "1")
    monkeypatch.setenv("NORTHSTAR_KEEP", "2")
    env = child_env(["NORTHSTAR_DROP", "NOT_SET_AT_ALL"], {"NORTHSTAR_ADD": "3"})
    assert "NORTHSTAR_DROP" not in env and env["NORTHSTAR_KEEP"] == "2" and env["NORTHSTAR_ADD"] == "3"
    assert "NORTHSTAR_DROP" in os.environ


@pytest.mark.parametrize(("setting", "expected"), [(None, 600.0), (30, 30.0), ("1.5", 1.5), (0, None), (-1, None)])
def test_the_time_limit(config, setting, expected):
    if setting is None:
        del config["harness"]["timeout_s"]
    else:
        config["harness"]["timeout_s"] = setting
    assert call_timeout(config) == expected


def test_a_time_limit_that_is_not_a_number_is_a_model_error(config):
    config["harness"]["timeout_s"] = "soon"
    with pytest.raises(ModelError, match="harness.timeout_s must be a number"):
        call_timeout(config)


def test_a_harness_result_is_a_model_result_that_also_keeps_the_api_equivalent_cost():
    result = HarnessResult("t", None, Usage(1, 2), 0.0, 0.1, "anthropic", "m", "m", "end_turn", api_equivalent_usd=0.5)
    assert isinstance(result, ModelResult) and dataclasses.asdict(result)["api_equivalent_usd"] == 0.5
    assert HarnessResult("t", None, Usage(), 0.0, 0.1, "openai", "m", "m", None).api_equivalent_usd is None


def test_no_test_can_start_a_program_by_accident():
    with pytest.raises(AssertionError, match="fake harness.run_process"):
        harness.run_process(["true"], stdin="", cwd=Path("."), env={}, timeout_s=1)
    assert f.FakeProcess().replies  # the fake the other tests use is there
