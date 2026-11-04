"""Claude Code's headless mode as a model port. No program is ever started: harness.run_process is faked."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

import model_fakes as f
from northstar_agent_memory.models import harness, harness_claude
from northstar_agent_memory.models.budget import billed_result
from northstar_agent_memory.models.harness import HarnessNotFound, HarnessResult, Process
from northstar_agent_memory.models.harness_claude import (
    ClaudeCodeHeadless,
    bundled_copies,
    claude_login,
    find_claude_binary,
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

# The real lookups, taken before the autouse fixture replaces them, for the tests of discovery.
REAL_BUNDLED_COPIES = bundled_copies
REAL_WHICH = shutil.which

SCHEMA_ARG = '{"type":"object","properties":{"verdict":{"type":"string"}},"required":["verdict"],"additionalProperties":false}'
SECRET = "sk-ant-test-do-not-print-0123456789"


@pytest.fixture
def program(tmp_path):
    # A folder name with a space, as in "Application Support": a command to type has to be quoted.
    return f.make_program(tmp_path / "Application Support" / "claude")


@pytest.fixture
def cfg(config, program):
    return f.with_programs(config, claude=program)


def install(monkeypatch, *replies) -> f.FakeProcess:
    fake = f.FakeProcess(*replies)
    monkeypatch.setattr(harness, "run_process", fake)
    return fake


def complete(cfg, **kw):
    return ClaudeCodeHeadless(cfg).complete(f.make_req(**kw))


# --- the command ---------------------------------------------------------------------------------


def test_a_structured_request_runs_this_command_with_the_prompt_on_stdin(cfg, program, monkeypatch):
    fake = install(monkeypatch, f.claude_ok(structured={"verdict": "yes"}))
    complete(cfg, schema=f.SCHEMA, effort="high", max_tokens=2000, cache=True)
    (call,) = fake.calls
    assert call["argv"] == [
        str(program), "-p", "--output-format", "json", "--no-session-persistence",
        "--settings", '{"disableAllHooks": true}', "--tools", "",
        "--system-prompt", "Be brief.", "--model", "claude-opus-5-5",
        "--effort", "high", "--json-schema", SCHEMA_ARG, "--safe-mode",
    ]
    assert call["stdin"] == "hello"
    assert call["timeout_s"] == 600


def test_a_plain_request_sends_no_schema_and_no_effort(cfg, program, monkeypatch):
    fake = install(monkeypatch, f.claude_ok("hi"))
    complete(cfg, role="worker_small")
    assert fake.calls[0]["argv"] == [
        str(program), "-p", "--output-format", "json", "--no-session-persistence",
        "--settings", '{"disableAllHooks": true}', "--tools", "",
        "--system-prompt", "Be brief.", "--model", "claude-haiku-5-5", "--safe-mode",
    ]


def test_the_model_a_request_names_wins_and_needs_no_price(cfg, monkeypatch):
    fake = install(monkeypatch, f.claude_ok("hi", models={"claude-unpriced": {"inputTokens": 1, "outputTokens": 1}}))
    complete(cfg, model="claude-unpriced")  # a plan has no price list: nothing is looked up
    argv = fake.calls[0]["argv"]
    assert argv[argv.index("--model") + 1] == "claude-unpriced"


@pytest.mark.parametrize("effort", ["low", "medium", "high", "xhigh", "max"])
def test_each_effort_goes_to_the_cli_as_it_is(cfg, monkeypatch, effort):
    fake = install(monkeypatch, f.claude_ok())
    complete(cfg, effort=effort)
    argv = fake.calls[0]["argv"]
    assert argv[argv.index("--effort") + 1] == effort


def test_an_empty_system_prompt_still_replaces_claude_codes_own(cfg, monkeypatch):
    fake = install(monkeypatch, f.claude_ok())
    complete(cfg, system="  ")
    argv = fake.calls[0]["argv"]
    assert argv[argv.index("--system-prompt") + 1] == harness_claude.NEUTRAL_SYSTEM


def test_the_system_prompt_goes_to_the_cli_unchanged(cfg, monkeypatch):
    system = "Line one.\n\nLine two with \"quotes\", é and --dashes."
    fake = install(monkeypatch, f.claude_ok())
    complete(cfg, system=system)
    argv = fake.calls[0]["argv"]
    assert argv[argv.index("--system-prompt") + 1] == system


def test_earlier_turns_are_rendered_as_a_transcript_before_the_last_user_message(cfg, monkeypatch):
    fake = install(monkeypatch, f.claude_ok())
    messages = [
        {"role": "user", "content": "first question"},
        {"role": "assistant", "content": "first answer"},
        {"role": "user", "content": "second question"},
    ]
    complete(cfg, messages=messages)
    assert fake.calls[0]["stdin"] == (
        "<conversation_so_far>\n"
        '<turn role="user">\nfirst question\n</turn>\n'
        '<turn role="assistant">\nfirst answer\n</turn>\n'
        "</conversation_so_far>\n\n"
        "The conversation so far is above, oldest turn first. Reply to the user's latest message, which follows.\n\n"
        "second question"
    )


@pytest.mark.parametrize(
    "messages",
    [
        [],
        [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}],
        [{"role": "user", "content": "   "}],
        [{"role": "system", "content": "s"}, {"role": "user", "content": "q"}],
    ],
)
def test_a_request_that_cannot_be_sent_starts_no_program(cfg, monkeypatch, messages):
    fake = install(monkeypatch, f.claude_ok())
    with pytest.raises(ModelError):
        complete(cfg, messages=messages)
    assert fake.calls == []


def test_checks_come_before_any_program_is_started(cfg, config, monkeypatch):
    fake = install(monkeypatch, f.claude_ok())
    adapter = ClaudeCodeHeadless(cfg)
    with pytest.raises(ModelError, match="openai"):
        adapter.complete(f.make_req(family="openai"))
    with pytest.raises(ModelError, match="unknown effort 'ultra'"):
        adapter.complete(f.make_req(effort="ultra"))
    with pytest.raises(SchemaNotStrict):
        adapter.complete(f.make_req(schema={"type": "object", "properties": {"a": {"type": "string"}}}))
    unset = f.with_programs(config, claude=Path(cfg["harness"]["claude_binary"]))
    unset["models"]["anthropic"]["judge"] = ""
    with pytest.raises(ModelError, match="no anthropic model"):
        ClaudeCodeHeadless(unset).complete(f.make_req())
    assert fake.calls == []


# --- the folder and the environment ----------------------------------------------------------------


def test_a_run_starts_in_the_empty_harness_folder_under_the_data_root(cfg, monkeypatch, isolated_home):
    fake = install(monkeypatch, f.claude_ok())
    complete(cfg)
    complete(cfg)
    first, second = fake.calls
    expected = isolated_home / "data" / "harness-cwd"
    assert first["cwd"] == second["cwd"] == expected
    assert first["cwd_was_empty"] and second["cwd_was_empty"]


def test_a_folder_that_is_not_empty_gets_a_fresh_empty_subfolder_that_is_removed(cfg, monkeypatch, isolated_home):
    root = isolated_home / "data" / "harness-cwd"
    root.mkdir(parents=True)
    (root / "left-behind.txt").write_text("x")
    fake = install(monkeypatch, f.claude_ok())
    complete(cfg)
    (call,) = fake.calls
    assert call["cwd"].parent == root and call["cwd_was_empty"]
    assert not call["cwd"].exists()  # cleaned up afterwards
    assert [p.name for p in root.iterdir()] == ["left-behind.txt"]


def test_the_environment_has_no_api_key_or_provider_switch_and_the_real_one_is_untouched(cfg, monkeypatch):
    for name, value in {
        "ANTHROPIC_API_KEY": SECRET,
        "ANTHROPIC_AUTH_TOKEN": "bearer-" + SECRET,
        "CLAUDE_CODE_USE_BEDROCK": "1",
        "CLAUDE_CODE_USE_VERTEX": "1",
        "CLAUDE_CODE_USE_FOUNDRY": "1",
        "CLAUDE_CODE_EFFORT_LEVEL": "max",
        "NORTHSTAR_TEST_KEEP": "kept",
    }.items():
        monkeypatch.setenv(name, value)
    fake = install(monkeypatch, f.claude_ok())
    complete(cfg, effort="low")
    env = fake.calls[0]["env"]
    for name in harness_claude.DROPPED_ENV:
        assert name not in env
    assert env["NORTHSTAR_TEST_KEEP"] == "kept" and "PATH" in env
    assert os.environ["ANTHROPIC_API_KEY"] == SECRET  # a copy was changed, not the process's own environment


def test_the_refusal_fallback_is_turned_off_only_when_the_request_asks(cfg, monkeypatch):
    fake = install(monkeypatch, f.claude_ok())
    complete(cfg)
    complete(cfg, allow_fallback=False)
    default, measured = fake.calls
    assert "CLAUDE_CODE_DISABLE_REFUSAL_FALLBACK" not in default["env"]
    assert measured["env"]["CLAUDE_CODE_DISABLE_REFUSAL_FALLBACK"] == "1"


@pytest.mark.parametrize(("setting", "expected"), [(900, 900), (0, None), ("12.5", 12.5)])
def test_the_time_limit_comes_from_settings(cfg, monkeypatch, setting, expected):
    cfg["harness"]["timeout_s"] = setting
    fake = install(monkeypatch, f.claude_ok())
    complete(cfg)
    assert fake.calls[0]["timeout_s"] == expected


# --- the result ----------------------------------------------------------------------------------


def test_the_result_holds_the_answer_the_tokens_and_the_route_costs_nothing(cfg, monkeypatch):
    install(monkeypatch, f.claude_ok("the answer", cost=0.25))
    result = complete(cfg)
    assert isinstance(result, HarnessResult)
    assert result.text == "the answer" and result.parsed is None
    assert (result.usage.input_tokens, result.usage.output_tokens) == (120, 30)
    assert (result.usage.cache_read_tokens, result.usage.cache_write_tokens) == (400, 50)
    assert result.cost_usd == 0.0 and result.api_equivalent_usd == 0.25  # a plan has no bill; the CLI's estimate is kept
    assert result.family == "anthropic" and result.model == result.served_model == "claude-opus-5-5"
    assert result.stop_reason == "end_turn" and result.request_id == "sess-1"
    assert result.latency_s >= 0 and not result.from_record


def test_tokens_are_summed_over_every_model_in_the_run_and_the_main_writer_is_the_served_model(cfg, monkeypatch):
    models = {
        "claude-haiku-5-5": {"inputTokens": 10, "outputTokens": 5, "cacheReadInputTokens": 1, "cacheCreationInputTokens": 2},
        "claude-opus-5-5": {"inputTokens": 100, "outputTokens": 40, "cacheReadInputTokens": 0, "cacheCreationInputTokens": 0},
    }
    install(monkeypatch, f.claude_ok(models=models))
    result = complete(cfg)
    assert (result.usage.input_tokens, result.usage.output_tokens) == (110, 45)
    assert (result.usage.cache_read_tokens, result.usage.cache_write_tokens) == (1, 2)
    assert result.served_model == "claude-opus-5-5"


def test_a_fallback_model_that_answered_is_the_served_model(cfg, monkeypatch):
    models = {
        "claude-opus-5-5": {"inputTokens": 100, "outputTokens": 0},
        "claude-sonnet-5-5": {"inputTokens": 100, "outputTokens": 60},
    }
    install(monkeypatch, f.claude_ok(models=models))
    result = complete(cfg)
    assert result.model == "claude-opus-5-5" and result.served_model == "claude-sonnet-5-5"


def test_without_model_usage_the_main_loops_usage_and_the_requested_model_stand_in(cfg, monkeypatch):
    install(monkeypatch, f.claude_ok(models={}, usage={"input_tokens": 7, "output_tokens": 3}))
    result = complete(cfg)
    assert (result.usage.input_tokens, result.usage.output_tokens) == (7, 3)
    assert result.served_model == "claude-opus-5-5"


def test_the_structured_output_is_the_parsed_result_and_the_text_is_its_json(cfg, monkeypatch):
    install(monkeypatch, f.claude_ok("", structured={"verdict": "yes"}))
    result = complete(cfg, schema=f.SCHEMA)
    assert result.parsed == {"verdict": "yes"} and result.text == '{"verdict":"yes"}'


def test_a_schema_call_with_no_structured_output_is_an_error_that_carries_the_tokens(cfg, monkeypatch):
    install(monkeypatch, f.claude_ok('{"verdict": "yes"}'))  # free text is never taken for the validated output
    with pytest.raises(ModelError, match="no structured output") as info:
        complete(cfg, schema=f.SCHEMA)
    assert billed_result(info.value).usage.output_tokens == 30


def test_the_run_that_could_not_make_valid_output_is_an_error_that_carries_the_tokens(cfg, monkeypatch):
    process = Process(1, f.claude_json("", subtype="error_max_structured_output_retries", is_error=True,
                                       errors=["no valid output"]), "")
    install(monkeypatch, process)
    with pytest.raises(ModelError, match="error_max_structured_output_retries: no valid output") as info:
        complete(cfg, schema=f.SCHEMA)
    assert type(info.value) is ModelError and billed_result(info.value).usage.output_tokens == 30


def test_a_refusal_raises_model_refused_with_the_tokens(cfg, monkeypatch):
    install(monkeypatch, f.claude_ok("", stop="refusal"))
    with pytest.raises(ModelRefused, match="claude-opus-5-5 refused") as info:
        complete(cfg)
    assert billed_result(info.value).stop_reason == "refusal"


def test_a_list_of_messages_gives_its_last_result(cfg, monkeypatch):
    install(monkeypatch, Process(0, "[" + f.claude_json("old") + ',{"type":"system"},' + f.claude_json("new") + "]", ""))
    assert complete(cfg).text == "new"


def test_a_warning_line_before_the_json_does_not_hide_it(cfg, monkeypatch):
    install(monkeypatch, Process(0, "warning: something\n" + f.claude_json("fine") + "\n", ""))
    assert complete(cfg).text == "fine"


# --- failures ------------------------------------------------------------------------------------


def test_not_signed_in_says_how_to_sign_in_with_the_program_that_would_run(cfg, program, monkeypatch):
    install(monkeypatch, f.claude_failed("Not logged in · Please run /login"))
    with pytest.raises(NoCredentials) as info:
        complete(cfg)
    assert str(info.value) == f"Claude Code is not signed in: sign in once with `'{program}' auth login`"


@pytest.mark.parametrize(
    "process",
    [
        Process(1, "Not logged in · Please run /login\n", ""),
        Process(1, "", "Error: Invalid API key · Fix external API key"),
        Process(1, "", "Login expired · Please run /login"),
        Process(1, "", "API Error: 401 Invalid authentication credentials"),
        f.claude_failed("Authentication required · Sign in again to continue"),
        f.claude_failed("Failed to authenticate. Please run /login", status=None),
        f.claude_failed("something unclear", status=401),
        f.claude_failed("something unclear", status=403),
        f.claude_failed("something unclear", api_error="gateway_signin_required"),
    ],
)
def test_a_login_that_is_missing_or_rejected_raises_no_credentials(cfg, monkeypatch, process):
    install(monkeypatch, process)
    with pytest.raises(NoCredentials, match="sign in once with"):
        complete(cfg)


@pytest.mark.parametrize(
    "process",
    [
        f.claude_failed("You've hit your session limit · resets 3pm (Europe/London)"),
        f.claude_failed("You’ve hit your weekly limit"),
        f.claude_failed("You've hit your Opus limit"),
        f.claude_failed("You've hit your org's monthly spend limit"),
        f.claude_failed("You've reached your Fable limit."),
        f.claude_failed("You're out of extra usage"),
        f.claude_failed("Your org is out of usage · add funds to continue"),
        f.claude_failed("Opus requires usage credits."),
        f.claude_failed("Credit balance is too low"),
        f.claude_failed("Server is temporarily limiting requests"),
        f.claude_failed("API Error: Request rejected (429)"),
        Process(1, "", "You've hit your session limit"),
        f.claude_failed("nothing recognisable", status=429),
        f.claude_failed("nothing recognisable", api_error="usage_limit_reached"),
    ],
)
def test_a_usage_session_rate_or_spend_limit_raises_plan_limit_reached(cfg, monkeypatch, process):
    install(monkeypatch, process)
    with pytest.raises(PlanLimitReached) as info:
        complete(cfg)
    assert isinstance(info.value, BudgetExceeded)  # so a run stops on it, as it does on a cap


@pytest.mark.parametrize(
    "process",
    [
        f.claude_failed("There's an issue with the selected model (claude-nope). It may not exist or you may not have access to it."),
        f.claude_failed("Model 'claude-nope' not found"),
        f.claude_failed("Claude Opus is not available with the Claude Pro plan"),
        f.claude_failed("nothing recognisable", status=404),
    ],
)
def test_a_model_the_plan_does_not_serve_raises_model_unavailable(cfg, monkeypatch, process):
    install(monkeypatch, process)
    with pytest.raises(ModelUnavailable):
        complete(cfg)


@pytest.mark.parametrize(
    ("process", "shown"),
    [
        (f.claude_failed("API Error: Repeated 529 Overloaded errors"), "529 Overloaded"),
        (Process(2, "not json at all", ""), "no JSON result, exit status 2: not json at all"),
        (Process(1, "", ""), "no JSON result, exit status 1"),
        (Process(3, f.claude_json("fine"), "crashed on exit"), "exit status 3: crashed on exit"),
        (f.claude_failed("API Error: No response from API"), "No response from API"),
    ],
)
def test_any_other_failure_raises_a_plain_model_error_with_what_the_program_said(cfg, monkeypatch, process, shown):
    install(monkeypatch, process)
    with pytest.raises(ModelError, match="Claude Code failed") as info:
        complete(cfg)
    assert type(info.value) is ModelError and shown in str(info.value)


def test_a_call_that_fails_after_the_model_was_used_carries_its_tokens_one_that_never_started_does_not(cfg, monkeypatch):
    install(monkeypatch, f.claude_failed("You've hit your session limit"))
    with pytest.raises(PlanLimitReached) as never_started:
        complete(cfg)
    assert billed_result(never_started.value) is None
    used = f.claude_json("You've hit your weekly limit", is_error=True)  # the model answered, then the limit came
    install(monkeypatch, Process(1, used, ""))
    with pytest.raises(PlanLimitReached) as after:
        complete(cfg)
    assert billed_result(after.value).usage.output_tokens == 30


def test_a_call_that_takes_too_long_is_stopped_and_the_message_holds_no_prompt(cfg, monkeypatch):
    install(monkeypatch, subprocess.TimeoutExpired(["claude", "--system-prompt", "Be brief."], 600))
    with pytest.raises(ModelError, match=r"did not finish within 600 s and was stopped") as info:
        complete(cfg)
    assert type(info.value) is ModelError and "Be brief" not in str(info.value) and info.value.__cause__ is None


def test_a_program_that_cannot_start_is_a_model_error(cfg, monkeypatch):
    install(monkeypatch, PermissionError(13, "Permission denied", "/secret/path/claude"))
    with pytest.raises(ModelError, match=r"could not start Claude Code \(Permission denied\)") as info:
        complete(cfg)
    assert "/secret/path" not in str(info.value)


def test_nothing_from_the_environment_reaches_a_message(cfg, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", SECRET)
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "bearer-" + SECRET)
    for process in (
        Process(1, "", f"API Error: 500 {SECRET} and bearer-{SECRET} echoed"),
        f.claude_failed(f"You've hit your session limit {SECRET}"),
        Process(2, f"garbage {SECRET}", ""),
    ):
        install(monkeypatch, process)
        with pytest.raises(ModelError) as info:
            complete(cfg)
        assert SECRET not in str(info.value)
    assert "[redacted]" in str(info.value)


# --- finding the program -------------------------------------------------------------------------


def test_a_program_named_in_settings_comes_first(tmp_path, config, monkeypatch):
    named = f.make_program(tmp_path / "named" / "claude")
    on_path = f.make_program(tmp_path / "path" / "claude")
    monkeypatch.setattr(shutil, "which", lambda cmd, *a, **k: str(on_path))
    monkeypatch.setattr(harness_claude, "bundled_copies", lambda: [f.make_program(tmp_path / "app" / "claude")])
    found = find_claude_binary(f.with_programs(config, claude=named))
    assert (found.path, found.source) == (named, "settings")


def test_a_program_in_settings_that_is_not_there_is_an_error_not_a_fallback(tmp_path, config, monkeypatch):
    f.make_program(tmp_path / "path" / "claude")
    monkeypatch.setattr(shutil, "which", REAL_WHICH)
    monkeypatch.setenv("PATH", str(tmp_path / "path"))
    with pytest.raises(HarnessNotFound, match="harness.claude_binary") as info:
        find_claude_binary(f.with_programs(config, claude=tmp_path / "missing" / "claude"))
    assert isinstance(info.value, ModelUnavailable)  # fatal for a run, as a missing model is


def test_claude_on_path_comes_before_the_one_in_the_app(tmp_path, config, monkeypatch):
    on_path = f.make_program(tmp_path / "path" / "claude")
    monkeypatch.setattr(shutil, "which", REAL_WHICH)
    monkeypatch.setenv("PATH", str(tmp_path / "path"))
    monkeypatch.setattr(harness_claude, "bundled_copies", lambda: [f.make_program(tmp_path / "app" / "claude")])
    found = find_claude_binary(config)
    assert (found.path, found.source) == (on_path, "PATH")


def test_the_newest_copy_bundled_with_the_app_is_used_and_versions_compare_as_numbers(tmp_path, config, monkeypatch):
    home = tmp_path / "home"
    root = home / "Library" / "Application Support" / "Claude" / "claude-code"
    tail = Path("claude.app") / "Contents" / "MacOS" / "claude"
    for version, build in (("2.1.9", "aaa"), ("2.1.309", "bbb"), ("2.1.30", "ccc")):
        f.make_program(root / version / build / tail)
    (root / "not-a-version" / "zzz").mkdir(parents=True)
    (root / "2.2.0" / "empty-build").mkdir(parents=True)  # newest, but holds no program
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(harness_claude, "bundled_copies", REAL_BUNDLED_COPIES)
    found = find_claude_binary(config)
    assert found.path == root / "2.1.309" / "bbb" / tail and found.source == "Claude app"
    assert [p.parts[-6] for p in REAL_BUNDLED_COPIES()][:4] == ["2.2.0", "2.1.309", "2.1.30", "2.1.9"]


def test_the_newest_build_of_a_version_is_tried_first(tmp_path, monkeypatch):
    home = tmp_path / "home"
    root = home / "Library" / "Application Support" / "Claude" / "claude-code" / "2.1.309"
    tail = Path("claude.app") / "Contents" / "MacOS" / "claude"
    old, new = f.make_program(root / "old" / tail), f.make_program(root / "new" / tail)
    os.utime(root / "old", (1_000_000, 1_000_000))
    os.utime(root / "new", (2_000_000, 2_000_000))
    monkeypatch.setenv("HOME", str(home))
    assert REAL_BUNDLED_COPIES() == [new, old]


def test_nothing_found_says_where_to_put_the_program(config, tmp_path):
    with pytest.raises(HarnessNotFound, match=r"Claude Code was not found: put `claude` on PATH, install the Claude app, or set harness\.claude_binary in "):
        find_claude_binary(config)
    with pytest.raises(HarnessNotFound):
        ClaudeCodeHeadless(config).complete(f.make_req())  # the adapter builds without it and fails at the first call


# --- the login, for the doctor ---------------------------------------------------------------------


AUTH_JSON = (
    '{"loggedIn": true, "authMethod": "claude.ai", "apiProvider": "firstParty", "email": "someone@example.com", '
    '"orgId": "org-123", "orgName": "Some Org", "subscriptionType": "max", "configDirectory": "/home/x/.claude"}'
)


def test_the_login_shows_only_whether_it_is_signed_in_how_and_the_plan(cfg, program, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", SECRET)
    fake = install(monkeypatch, Process(0, AUTH_JSON, ""))
    login = claude_login(cfg)
    assert (login.signed_in, login.method, login.plan) == (True, "claude.ai", "max")
    for secret in ("someone@example.com", "org-123", "Some Org", "firstParty"):
        assert secret not in repr(login)
    (call,) = fake.calls
    assert call["argv"] == [str(program), "auth", "status"] and call["stdin"] == ""
    assert "ANTHROPIC_API_KEY" not in call["env"]  # it asks as a call would run: on the plan login, not a key
    assert call["cwd_was_empty"] and call["timeout_s"] == harness_claude.AUTH_TIMEOUT_S


def test_not_signed_in(cfg, monkeypatch):
    install(monkeypatch, Process(1, '{"loggedIn": false, "authMethod": "none"}', ""))
    assert claude_login(cfg) == harness_claude.ClaudeLogin(False, "none", None)


def test_the_exit_status_says_it_when_the_json_does_not(cfg, monkeypatch):
    install(monkeypatch, Process(1, "Not logged in. Run claude auth login to authenticate.", ""))
    assert claude_login(cfg).signed_in is False
    install(monkeypatch, Process(0, "Logged in", ""))
    assert claude_login(cfg).signed_in is True


def test_a_plan_or_method_that_is_not_what_it_should_be_is_not_shown(cfg, monkeypatch):
    install(monkeypatch, Process(0, '{"loggedIn": true, "authMethod": "x@y.z", "subscriptionType": "a b <script>"}', ""))
    login = claude_login(cfg)
    assert (login.signed_in, login.method, login.plan) == (True, None, None)


@pytest.mark.parametrize("reply", [subprocess.TimeoutExpired(["claude"], 30), PermissionError(13, "no"), ModelError("x")])
def test_a_login_check_that_cannot_answer_says_so(cfg, monkeypatch, reply):
    install(monkeypatch, reply)
    assert claude_login(cfg).signed_in is None


def test_no_program_means_no_login_to_ask(config):
    assert claude_login(config).signed_in is None
