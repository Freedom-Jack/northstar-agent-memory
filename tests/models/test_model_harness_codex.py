"""Codex's `exec` as a model port. No program is ever started: harness.run_process is faked."""

import json
import os
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

import model_fakes as f
from northstar_agent_memory.models import harness, harness_codex
from northstar_agent_memory.models.budget import billed_result
from northstar_agent_memory.models.harness import HarnessNotFound, HarnessResult, Process
from northstar_agent_memory.models.harness_codex import (
    CodexExec,
    CodexLogin,
    codex_login,
    find_codex_binary,
    toml_string,
)
from northstar_agent_memory.models.port import (
    BudgetExceeded,
    ModelError,
    ModelRefused,
    ModelUnavailable,
    NoCredentials,
    PlanLimitReached,
    SchemaNotStrict,
)

REAL_WHICH = shutil.which
SECRET = "sk-openai-test-do-not-print-0123456789"


@pytest.fixture
def program(tmp_path):
    return f.make_program(tmp_path / "bin" / "codex")


@pytest.fixture
def cfg(config, program):
    return f.with_programs(f.with_openai(config), codex=program)  # the judge role is "gpt-test"


FEATURES = """\
apps                                     stable             true
apply_patch_freeform                     removed            false
hooks                                    stable             true
incremental_tools                        stable             true
omit_skill_descriptions                  under development  false
plugins                                  stable             true
shell_tool                               stable             true
sleep_tool                               stable             true
view_image                               stable             true
"""
LEAN = [
    "--disable", "incremental_tools", "--disable", "plugins", "--disable", "shell_tool",
    "--disable", "view_image", "--disable", "sleep_tool", "--enable", "omit_skill_descriptions",
]


class Fake(f.FakeProcess):
    """FakeProcess for the `exec` calls; the `features list` probe is answered apart and kept in `probes`."""

    def __init__(self, *replies, features=Process(0, FEATURES, "")):
        super().__init__(*replies)
        self.features = features
        self.probes: list[dict] = []

    def __call__(self, argv, *, stdin, cwd, env, timeout_s):
        if list(argv[1:]) == ["features", "list"]:
            self.probes.append({"argv": list(argv), "cwd": Path(cwd), "timeout_s": timeout_s})
            if isinstance(self.features, BaseException):
                raise self.features
            return self.features
        return super().__call__(argv, stdin=stdin, cwd=cwd, env=env, timeout_s=timeout_s)


@pytest.fixture(autouse=True)
def fresh_features_cache():
    harness_codex._features_cache.clear()
    yield
    harness_codex._features_cache.clear()


def install(monkeypatch, *replies, **kw) -> Fake:
    fake = Fake(*replies, **kw)
    monkeypatch.setattr(harness, "run_process", fake)
    return fake


def complete(cfg, **kw):
    kw.setdefault("family", "openai")
    return CodexExec(cfg).complete(f.make_req(**kw))


# --- the command ---------------------------------------------------------------------------------


def test_a_plain_request_runs_this_command_with_the_prompt_on_stdin(cfg, program, monkeypatch, isolated_home):
    fake = install(monkeypatch, f.codex_ok("hi"))
    complete(cfg)
    (call,) = fake.calls
    instructions = isolated_home / "data" / "harness-config" / "codex-base-instructions.md"
    assert call["argv"] == [
        str(program), "exec", "--ephemeral", "--skip-git-repo-check", "-s", "read-only", "--json",
        "-m", "gpt-test",
        "-c", 'model_reasoning_effort="medium"',
        "-c", 'developer_instructions="Be brief."',
        "--disable", "hooks", "-c", 'web_search="disabled"',
        "-c", f"model_instructions_file={json.dumps(str(instructions))}",
        *LEAN,
        "-",
    ]
    assert call["stdin"] == "hello" and call["timeout_s"] == 600


def test_a_structured_request_gives_the_schema_in_a_file_that_is_gone_afterwards(cfg, program, monkeypatch, isolated_home):
    fake = install(monkeypatch, f.codex_ok('{"verdict": "yes"}'))
    complete(cfg, schema=f.SCHEMA, effort="high")
    (call,) = fake.calls
    argv = call["argv"]
    assert argv[argv.index("--output-schema") + 1] == str(call["schema_path"])
    assert argv[-3:] == ["--output-schema", str(call["schema_path"]), "-"]
    assert json.loads(call["schema_text"]) == f.SCHEMA
    assert not call["schema_path"].exists()  # a temporary file, removed after the call
    assert call["schema_path"].parent != call["cwd"]  # and never in the run's empty folder
    assert 'model_reasoning_effort="high"' in argv


@pytest.mark.parametrize("effort", ["low", "medium", "high", "xhigh", "max"])
def test_each_effort_is_set_explicitly_and_ultra_is_never_chosen(cfg, monkeypatch, effort):
    fake = install(monkeypatch, f.codex_ok())
    complete(cfg, effort=effort)
    argv = fake.calls[0]["argv"]
    assert argv[argv.index("-c") + 1] == f'model_reasoning_effort="{effort}"'
    assert "ultra" not in " ".join(argv[1:])  # it adds automatic task delegation


def test_no_effort_still_sets_one_so_the_users_own_default_does_not_apply(cfg, monkeypatch):
    fake = install(monkeypatch, f.codex_ok())
    complete(cfg)
    assert 'model_reasoning_effort="medium"' in fake.calls[0]["argv"]


def test_an_empty_system_prompt_sends_no_instructions(cfg, monkeypatch):
    fake = install(monkeypatch, f.codex_ok())
    complete(cfg, system="")
    assert not any(a.startswith("developer_instructions") for a in fake.calls[0]["argv"])


@pytest.mark.parametrize(
    "text",
    [
        "Be brief.",
        'Line one.\n\nLine "two" \\ with a backslash, tab\tand é ✓ and 😀.',
        "ends with a backslash \\",
        "bell \x07, escape \x1b, DEL \x7f, and a literal \\n",
        "# not a comment ' ''' \"\"\" [table] = 1",
    ],
)
def test_the_system_prompt_is_a_toml_string_that_reads_back_as_it_was(text):
    assert tomllib.loads(f"x = {toml_string(text)}")["x"] == text


def test_the_system_prompt_goes_to_the_cli_as_developer_instructions(cfg, monkeypatch):
    system = 'Say "ok".\nTwice.'
    fake = install(monkeypatch, f.codex_ok())
    complete(cfg, system=system)
    override = next(a for a in fake.calls[0]["argv"] if a.startswith("developer_instructions="))
    assert tomllib.loads(override)["developer_instructions"] == system


def test_earlier_turns_are_rendered_as_a_transcript_before_the_last_user_message(cfg, monkeypatch):
    fake = install(monkeypatch, f.codex_ok())
    messages = [{"role": "user", "content": "q1"}, {"role": "assistant", "content": "a1"}, {"role": "user", "content": "q2"}]
    complete(cfg, messages=messages)
    assert fake.calls[0]["stdin"] == (
        "<conversation_so_far>\n"
        '<turn role="user">\nq1\n</turn>\n'
        '<turn role="assistant">\na1\n</turn>\n'
        "</conversation_so_far>\n\n"
        "The conversation so far is above, oldest turn first. Reply to the user's latest message, which follows.\n\n"
        "q2"
    )


def test_a_request_that_cannot_be_sent_starts_no_program(cfg, config, monkeypatch):
    fake = install(monkeypatch, f.codex_ok())
    adapter = CodexExec(cfg)
    with pytest.raises(ModelError, match="anthropic"):
        adapter.complete(f.make_req(family="anthropic"))
    with pytest.raises(ModelError, match="unknown effort 'ultra'"):
        adapter.complete(f.make_req(family="openai", effort="ultra"))
    with pytest.raises(SchemaNotStrict):
        adapter.complete(f.make_req(family="openai", schema={"type": "object", "properties": {"a": {"type": "string"}}}))
    with pytest.raises(ModelError, match="last message must come from the user"):
        adapter.complete(f.make_req(family="openai", messages=[{"role": "assistant", "content": "a"}]))
    blank = f.with_programs(config, codex=Path(cfg["harness"]["codex_binary"]))
    blank["models"]["openai"]["judge"] = ""
    with pytest.raises(ModelError, match="no openai model"):
        CodexExec(blank).complete(f.make_req(family="openai"))
    assert fake.calls == []


# --- the lean prompt ------------------------------------------------------------------------------


def test_the_base_instructions_are_written_under_the_data_root_and_named_in_the_override(cfg, monkeypatch, isolated_home):
    fake = install(monkeypatch, f.codex_ok())
    complete(cfg)
    (call,) = fake.calls
    path = isolated_home / "data" / "harness-config" / "codex-base-instructions.md"
    assert path.read_text(encoding="utf-8") == harness_codex.BASE_INSTRUCTIONS
    override = next(a for a in call["argv"] if a.startswith("model_instructions_file="))
    assert tomllib.loads(override)["model_instructions_file"] == str(path)
    assert not path.is_relative_to(call["cwd"]) and not any(call["cwd"].iterdir())  # never in the run's folder
    assert call["cwd_was_empty"]


def test_a_changed_instructions_file_is_put_back(cfg, monkeypatch, isolated_home):
    install(monkeypatch, f.codex_ok())
    complete(cfg)
    path = isolated_home / "data" / "harness-config" / "codex-base-instructions.md"
    path.write_text("edited", encoding="utf-8")
    complete(cfg)
    assert path.read_text(encoding="utf-8") == harness_codex.BASE_INSTRUCTIONS


def test_the_features_probe_runs_through_run_process_in_the_empty_folder(cfg, program, monkeypatch, isolated_home):
    fake = install(monkeypatch, f.codex_ok())
    complete(cfg)
    (probe,) = fake.probes
    assert probe["argv"] == [str(program), "features", "list"]
    assert probe["cwd"] == isolated_home / "data" / "harness-cwd" and probe["timeout_s"] == 30


def test_removed_and_unknown_features_are_skipped(cfg, monkeypatch):
    listing = (
        "incremental_tools                        removed            false\n"
        "plugins                                  stable             true\n"
        "shell_tool                               under development  false\n"
        "omit_skill_descriptions                  removed            false\n"
        "some_new_feature                         stable             true\n"
    )
    fake = install(monkeypatch, f.codex_ok(), features=Process(0, listing, ""))
    complete(cfg)
    argv = fake.calls[0]["argv"]
    assert argv[argv.index("-"):] == ["-"]
    assert argv[-5:-1] == ["--disable", "plugins", "--disable", "shell_tool"]
    assert "incremental_tools" not in argv and "omit_skill_descriptions" not in argv and "some_new_feature" not in argv


def test_parse_features_reads_names_with_a_two_word_stage():
    assert harness_codex.parse_features(FEATURES) == {
        "apps", "hooks", "incremental_tools", "omit_skill_descriptions", "plugins", "shell_tool", "sleep_tool", "view_image",
    }
    assert harness_codex.parse_features("garbage\n\nerror: nope") == frozenset()


@pytest.mark.parametrize(
    "features",
    [
        Process(1, "", "error: unrecognized subcommand"),
        Process(0, "not a table at all", ""),
        subprocess.TimeoutExpired(["codex", "features", "list"], 30),
        OSError(8, "Exec format error"),
    ],
)
def test_a_failed_features_probe_means_no_switches_and_the_call_still_runs(cfg, monkeypatch, features):
    fake = install(monkeypatch, f.codex_ok("still fine"), features=features)
    assert complete(cfg).text == "still fine"
    argv = fake.calls[0]["argv"]
    assert "--enable" not in argv and "incremental_tools" not in argv and "plugins" not in argv
    assert any(a.startswith("model_instructions_file=") for a in argv)


def test_the_features_are_read_once_per_program(cfg, monkeypatch):
    fake = install(monkeypatch, f.codex_ok())
    complete(cfg)
    complete(cfg)
    assert len(fake.probes) == 1 and len(fake.calls) == 2
    assert fake.calls[0]["argv"] == fake.calls[1]["argv"]


def test_each_program_has_its_own_features(tmp_path, config, monkeypatch):
    first, second = f.make_program(tmp_path / "a" / "codex"), f.make_program(tmp_path / "b" / "codex")
    fake = install(monkeypatch, f.codex_ok())
    complete(f.with_programs(f.with_openai(config), codex=first))
    complete(f.with_programs(f.with_openai(config), codex=second))
    assert [p["argv"][0] for p in fake.probes] == [str(first), str(second)]


# --- the folder and the environment ----------------------------------------------------------------


def test_a_run_starts_in_the_empty_harness_folder_under_the_data_root(cfg, monkeypatch, isolated_home):
    fake = install(monkeypatch, f.codex_ok())
    complete(cfg)
    (call,) = fake.calls
    assert call["cwd"] == isolated_home / "data" / "harness-cwd" and call["cwd_was_empty"]


def test_the_environment_has_no_api_key_and_the_real_one_is_untouched(cfg, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", SECRET)
    monkeypatch.setenv("CODEX_API_KEY", SECRET)
    monkeypatch.setenv("NORTHSTAR_TEST_KEEP", "kept")
    fake = install(monkeypatch, f.codex_ok())
    complete(cfg)
    env = fake.calls[0]["env"]
    assert "OPENAI_API_KEY" not in env and "CODEX_API_KEY" not in env
    assert env["NORTHSTAR_TEST_KEEP"] == "kept" and "PATH" in env
    assert os.environ["OPENAI_API_KEY"] == SECRET


def test_the_time_limit_comes_from_settings(cfg, monkeypatch):
    cfg["harness"]["timeout_s"] = 45
    fake = install(monkeypatch, f.codex_ok())
    complete(cfg)
    assert fake.calls[0]["timeout_s"] == 45


# --- the result ----------------------------------------------------------------------------------


def test_the_answer_is_the_last_agent_message_and_the_usage_splits_cached_input(cfg, monkeypatch):
    stdout = "".join(
        json.dumps(e) + "\n"
        for e in (
            {"type": "thread.started", "thread_id": "th-9"},
            {"type": "item.completed", "item": {"type": "agent_message", "text": "an early note"}},
            {"type": "item.completed", "item": {"type": "agent_message", "text": "the answer"}},
            {"type": "turn.completed", "usage": {"input_tokens": 1000, "cached_input_tokens": 400, "output_tokens": 200,
                                                  "reasoning_output_tokens": 150}},
        )
    )
    install(monkeypatch, Process(0, stdout, ""))
    result = complete(cfg)
    assert isinstance(result, HarnessResult)
    assert result.text == "the answer" and result.parsed is None
    # OpenAI counts cached tokens inside input and reasoning tokens inside output, as the API adapter assumes.
    assert (result.usage.input_tokens, result.usage.cache_read_tokens, result.usage.output_tokens) == (600, 400, 200)
    assert result.usage.cache_write_tokens == 0
    assert result.cost_usd == 0.0 and result.api_equivalent_usd is None
    assert result.family == "openai" and result.model == result.served_model == "gpt-test"
    assert result.stop_reason == "end_turn" and result.request_id == "th-9"
    assert result.latency_s >= 0 and not result.from_record


def test_a_structured_answer_is_parsed(cfg, monkeypatch):
    install(monkeypatch, f.codex_ok('{"verdict": "yes"}'))
    result = complete(cfg, schema=f.SCHEMA)
    assert result.parsed == {"verdict": "yes"} and result.text == '{"verdict": "yes"}'


def test_an_answer_that_is_not_valid_json_for_a_schema_call_is_an_error_that_carries_the_tokens(cfg, monkeypatch):
    install(monkeypatch, f.codex_ok("not json"))
    with pytest.raises(ModelError, match="not valid JSON") as info:
        complete(cfg, schema=f.SCHEMA)
    assert billed_result(info.value).usage.output_tokens == 200


def test_an_answer_that_is_not_an_object_is_an_error(cfg, monkeypatch):
    install(monkeypatch, f.codex_ok("[1, 2]"))
    with pytest.raises(ModelError, match="not a JSON object"):
        complete(cfg, schema=f.SCHEMA)


def test_a_finished_turn_with_no_answer_is_an_error_that_carries_the_tokens(cfg, monkeypatch):
    install(monkeypatch, f.codex_ok(answer=None))
    with pytest.raises(ModelError, match="finished without an answer") as info:
        complete(cfg)
    assert billed_result(info.value).usage.input_tokens == 600


def test_lines_that_are_not_events_and_errors_before_a_finished_turn_do_not_fail_the_call(cfg, monkeypatch):
    stdout = "Reading prompt from stdin...\n" + f.codex_events("fine", errors=["Reconnecting... 1/5"])
    install(monkeypatch, Process(0, stdout, "warning: Model metadata for `gpt-test` not found."))
    assert complete(cfg).text == "fine"


# --- failures ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "process",
    [
        f.codex_failed("You hit your spend cap set by the owner of your workspace. Ask an owner to increase your spend cap to continue."),
        f.codex_failed("You hit your spend cap set in your workspace. Increase your spend cap to continue."),
        f.codex_failed("Your workspace is out of credits. Add credits to continue."),
        f.codex_failed("Your workspace is out of credits. Ask your workspace owner to refill in order to continue."),
        f.codex_failed("You've hit your usage limit. Upgrade to Pro (https://chatgpt.com/explore/pro), visit https://chatgpt.com/settings/usage to purchase more credits"),
        f.codex_failed("You’ve hit your usage limit for gpt-test. Switch to another model now,"),
        f.codex_failed("You've hit your usage limit. To get more access now, send a request to your admin"),
        f.codex_failed("exceeded retry limit, last status: 429 Too Many Requests"),
        f.codex_failed("generic text", errors=["You hit your spend cap set by the owner of your workspace."]),
        Process(1, "", "Error: You hit your spend cap set by the owner of your workspace."),
    ],
)
def test_a_usage_limit_spend_cap_or_empty_workspace_raises_plan_limit_reached(cfg, monkeypatch, process):
    install(monkeypatch, process)
    with pytest.raises(PlanLimitReached) as info:
        complete(cfg)
    assert isinstance(info.value, BudgetExceeded)  # so a run stops on it and waits for the reset


@pytest.mark.parametrize(
    "process",
    [
        f.codex_failed("Your access token could not be refreshed. Please log out and sign in again."),
        f.codex_failed("Your authentication session could not be refreshed automatically. Please log out and sign in again."),
        f.codex_failed("unexpected status 401 Unauthorized: Missing bearer, auth error: 1"),
        f.codex_failed("ChatGPT account ID not available, please re-run `codex login`"),
        Process(1, "", "Not logged in"),
        Process(1, "", "no Codex credentials were found. Run codex login or provide an API key"),
    ],
)
def test_not_signed_in_says_to_sign_in_through_the_chatgpt_app(cfg, monkeypatch, process):
    install(monkeypatch, process)
    with pytest.raises(NoCredentials) as info:
        complete(cfg)
    assert str(info.value) == "Codex is not signed in: sign in through the ChatGPT app"


@pytest.mark.parametrize(
    "message",
    [
        "The model `gpt-test` does not exist or you do not have access to it.",
        "Model 'gpt-test' not found",
        "The 'gpt-test' model is not supported when using Codex with a ChatGPT account.",
        "model_not_found: gpt-test",
        "unknown model gpt-test",
    ],
)
def test_a_model_the_plan_does_not_serve_raises_model_unavailable(cfg, monkeypatch, message):
    install(monkeypatch, f.codex_failed(message))
    with pytest.raises(ModelUnavailable):
        complete(cfg)


@pytest.mark.parametrize("message", ["cyber policy: this request was flagged", "This request was blocked due to a misalignment policy violation."])
def test_a_policy_block_raises_model_refused(cfg, monkeypatch, message):
    install(monkeypatch, f.codex_failed(message))
    with pytest.raises(ModelRefused, match="Codex refused the request"):
        complete(cfg)


@pytest.mark.parametrize(
    ("process", "shown"),
    [
        (f.codex_failed("stream disconnected before completion"), "stream disconnected"),
        (Process(1, "", "boom on stderr"), "exit status 1: boom on stderr"),
        (Process(2, "stray output", ""), "exit status 2: stray output"),
        (Process(0, "", ""), "Codex failed (no detail)"),
        (f.codex_failed("something", errors=["first", "something"]), "first something"),
    ],
)
def test_any_other_failure_raises_a_plain_model_error_with_what_the_program_said(cfg, monkeypatch, process, shown):
    install(monkeypatch, process)
    with pytest.raises(ModelError, match="Codex failed") as info:
        complete(cfg)
    assert type(info.value) is ModelError and shown in str(info.value)


def test_a_warning_on_stderr_does_not_turn_a_real_failure_into_a_model_error_kind(cfg, monkeypatch):
    # "Model metadata for `x` not found" is a warning Codex prints on stderr; the structured failure decides.
    install(monkeypatch, Process(1, f.codex_events(failed="stream error"), "Model metadata for `gpt-test` not found."))
    with pytest.raises(ModelError) as info:
        complete(cfg)
    assert type(info.value) is ModelError


def test_a_call_that_takes_too_long_is_stopped_and_the_message_holds_no_prompt(cfg, monkeypatch):
    install(monkeypatch, subprocess.TimeoutExpired(["codex", "-c", 'developer_instructions="Be brief."'], 600))
    with pytest.raises(ModelError, match=r"Codex did not finish within 600 s and was stopped") as info:
        complete(cfg)
    assert type(info.value) is ModelError and "Be brief" not in str(info.value)


def test_a_program_that_cannot_start_is_a_model_error(cfg, monkeypatch):
    install(monkeypatch, OSError(8, "Exec format error", "/secret/path/codex"))
    with pytest.raises(ModelError, match=r"could not start Codex \(Exec format error\)") as info:
        complete(cfg)
    assert "/secret/path" not in str(info.value)


def test_nothing_from_the_environment_reaches_a_message(cfg, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", SECRET)
    monkeypatch.setenv("CODEX_API_KEY", SECRET)
    for process in (Process(1, "", f"Error: {SECRET} was rejected"), f.codex_failed(f"You hit your spend cap {SECRET}")):
        install(monkeypatch, process)
        with pytest.raises(ModelError) as info:
            complete(cfg)
        assert SECRET not in str(info.value)
    assert "[redacted]" in str(info.value)


# --- finding the program -------------------------------------------------------------------------


def test_a_program_named_in_settings_comes_first(tmp_path, config, monkeypatch):
    named = f.make_program(tmp_path / "named" / "codex")
    monkeypatch.setattr(shutil, "which", lambda cmd, *a, **k: str(f.make_program(tmp_path / "path" / "codex")))
    monkeypatch.setattr(harness_codex, "CODEX_APP_BINARY", f.make_program(tmp_path / "app" / "codex"))
    found = find_codex_binary(f.with_programs(config, codex=named))
    assert (found.path, found.source) == (named, "settings")


def test_codex_on_path_comes_before_the_one_in_the_app(tmp_path, config, monkeypatch):
    on_path = f.make_program(tmp_path / "path" / "codex")
    monkeypatch.setattr(shutil, "which", REAL_WHICH)
    monkeypatch.setenv("PATH", str(tmp_path / "path"))
    monkeypatch.setattr(harness_codex, "CODEX_APP_BINARY", f.make_program(tmp_path / "app" / "codex"))
    found = find_codex_binary(config)
    assert (found.path, found.source) == (on_path, "PATH")


def test_the_copy_bundled_with_the_chatgpt_app_is_the_last_resort(tmp_path, config, monkeypatch):
    bundled = f.make_program(tmp_path / "ChatGPT.app" / "codex")
    monkeypatch.setattr(harness_codex, "CODEX_APP_BINARY", bundled)
    found = find_codex_binary(config)
    assert (found.path, found.source) == (bundled, "ChatGPT app")


def test_the_real_bundled_location_is_the_one_the_design_names():
    # The autouse fixture moved it for the tests; the source holds the real one.
    source = Path(harness_codex.__file__).read_text(encoding="utf-8")
    assert 'Path("/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex")' in source


def test_a_program_in_settings_that_is_not_there_is_an_error_not_a_fallback(tmp_path, config):
    with pytest.raises(HarnessNotFound, match="harness.codex_binary") as info:
        find_codex_binary(f.with_programs(config, codex=tmp_path / "missing" / "codex"))
    assert isinstance(info.value, ModelUnavailable)


def test_nothing_found_says_where_to_put_the_program(config):
    with pytest.raises(HarnessNotFound, match=r"Codex was not found: put `codex` on PATH, install the ChatGPT app, or set harness\.codex_binary in "):
        find_codex_binary(config)
    with pytest.raises(HarnessNotFound):
        CodexExec(f.with_openai(config)).complete(f.make_req(family="openai"))  # builds without it; fails at the first call


# --- the login, for the doctor ---------------------------------------------------------------------


def write_auth(path: Path, text: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "auth.json").write_text(text, encoding="utf-8")


def test_only_the_auth_mode_of_auth_json_is_looked_at(tmp_path, monkeypatch):
    home = tmp_path / "codex-home"
    write_auth(home, json.dumps({
        "auth_mode": "chatgpt",
        "OPENAI_API_KEY": SECRET,
        "tokens": {"id_token": "id-secret", "access_token": "access-secret", "refresh_token": "refresh-secret",
                   "account_id": "acct-secret"},
        "last_refresh": "2026-10-29T00:00:00Z",
    }))
    monkeypatch.setenv("CODEX_HOME", str(home))
    login = codex_login()
    assert login == CodexLogin(True, "chatgpt")
    for secret in (SECRET, "id-secret", "access-secret", "refresh-secret", "acct-secret"):
        assert secret not in repr(login)


def test_codex_home_defaults_to_dot_codex_in_the_home_folder(tmp_path, monkeypatch):
    write_auth(tmp_path / "home" / ".codex", '{"auth_mode": "apikey"}')
    monkeypatch.delenv("CODEX_HOME")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    assert codex_login() == CodexLogin(True, "apikey")


def test_no_auth_json_means_no_login_file(tmp_path):
    assert codex_login() == CodexLogin(False)  # CODEX_HOME points at a folder that is not there


@pytest.mark.parametrize("text", ["not json", "[]", '"auth_mode"', "{}", '{"auth_mode": 7}', '{"auth_mode": "has space"}'])
def test_a_file_without_a_usable_auth_mode_shows_none(tmp_path, monkeypatch, text):
    write_auth(tmp_path / "h", text)
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "h"))
    assert codex_login() == CodexLogin(True, None)


def test_a_file_that_cannot_be_read_is_reported_as_such(tmp_path, monkeypatch):
    (tmp_path / "h" / "auth.json").mkdir(parents=True)  # a folder where the file should be
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "h"))
    assert codex_login() == CodexLogin(None)
