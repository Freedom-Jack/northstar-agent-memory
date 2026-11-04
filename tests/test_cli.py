"""CLI tests: no network, no keys, no Keychain; a stub model stands in for the vendors."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

import northstar_agent_memory
from northstar_agent_memory import cli
from northstar_agent_memory import config as northstar_config
from northstar_agent_memory.eval import judge as jd
from northstar_agent_memory.eval import longmemeval as lme
from northstar_agent_memory.eval import runner
from northstar_agent_memory.models import harness
from northstar_agent_memory.models.harness import Process
from northstar_agent_memory.models.recorder import RecordingPort
from northstar_agent_memory.models.stub import StubModel
from northstar_agent_memory.paths import data_root, eval_root, harness_cwd

EVAL_TESTS = Path(__file__).parent / "eval"
TINY = EVAL_TESTS / "fixtures" / "lme_tiny.json"
CLAUDE_CODE = EVAL_TESTS / "fixtures" / "claude_code"
SECRET = "sk-test-do-not-print-0123456789"


def with_batches(single):
    """A handler that also answers a batched judge request: each pair goes to `single` as a one-pair request."""

    def handler(req):
        if req.purpose != "judge.qa.batch":
            return single(req)
        verdicts = []
        for pair_id, body in re.findall(r'<pair id="(p\d+)">\n(.*?)</pair>', req.messages[-1]["content"], re.S):
            one = replace(req, purpose="judge.qa", messages=[{"role": "user", "content": body}])
            verdicts.append({"id": pair_id, **single(one)})
        return {"verdicts": verdicts}

    return handler


def single_handler(req):
    """Answers anything, and judges everything correct; the flow is what these tests are about."""
    if req.purpose == "judge.qa":
        return {"rationale": "r", "label": "correct"}
    if req.purpose == "judge.meta.probes":
        return {"positive": "right", "wrong_on_topic": "wrong", "partial": None, "vague": "maybe", "stale": None}
    if req.purpose == "b4.observe":
        return {"observations": [{"text": "a note", "message_ids": []}]}
    if req.purpose in ("b2.step", "b2.answer"):
        return {"action": "answer", "pattern": None, "session_id": None, "start": None, "end": None, "answer": "an answer", "cited": []}
    return {"answer": "an answer", "cited": []}


handler = with_batches(single_handler)


@pytest.fixture(autouse=True)
def quiet_filevault(monkeypatch):
    monkeypatch.setattr(cli, "filevault_status", lambda: "FileVault is On.")


@pytest.fixture
def ports(monkeypatch, tmp_path):
    """Replace build_port with a recording stub; the calls it received are kept."""
    seen: list[dict] = []
    stub = StubModel(handler)

    def fake_build_port(config, *, run_id, mode="record", run_budget_usd=None, **_):
        seen.append({"run_id": run_id, "mode": mode, "budget": run_budget_usd})
        return RecordingPort(stub, tmp_path / "calls.sqlite", mode=mode)

    monkeypatch.setattr(cli, "build_port", fake_build_port)
    stub.seen = seen  # type: ignore[attr-defined]
    return stub


@pytest.fixture
def no_port(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("a port was built, so a model could have been called")

    monkeypatch.setattr(cli, "build_port", refuse)


@pytest.fixture
def tiny_test_selection(monkeypatch):
    """All five items of the fixture in the test split, none in dev."""
    monkeypatch.setitem(lme.SHA256, TINY.name, lme.sha256_of(TINY))
    settings = data_root() / "settings.toml"
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(
        "[eval.longmemeval]\nper_type_dev = 0\nper_type_test = 1\nabstention_dev = 0\nabstention_test = 1\n", encoding="utf-8"
    )
    assert cli.run(["eval", "lme", "prepare", "--file", str(TINY)]) == 0


def write_settings(text: str) -> None:
    settings = data_root() / "settings.toml"
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(settings.read_text(encoding="utf-8") + text if settings.exists() else text, encoding="utf-8")


@pytest.fixture
def tiny_selection(monkeypatch):
    """A one-per-type LongMemEval subset of the invented fixture, prepared the normal way."""
    monkeypatch.setitem(lme.SHA256, TINY.name, lme.sha256_of(TINY))
    settings = data_root() / "settings.toml"
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(
        "[eval.longmemeval]\nper_type_dev = 1\nper_type_test = 0\nabstention_dev = 1\nabstention_test = 0\n", encoding="utf-8"
    )
    assert cli.run(["eval", "lme", "prepare", "--file", str(TINY)]) == 0


# --- doctor ------------------------------------------------------------------------------------------------


def test_doctor_reports_the_setup_and_never_a_key(capsys, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", SECRET)
    assert cli.run(["doctor"]) == 0
    out = capsys.readouterr().out
    assert SECRET not in out
    assert f"data root: {data_root()}" in out
    assert "config version: " + northstar_config.load()["config_version"] in out
    assert "FileVault: FileVault is On." in out
    assert "anthropic: sdk-default" in out and "openai: env" in out
    assert "monthly cost cap: not used on the harness route" in out  # the shipped route is the harness
    assert "anthropic.answerer: claude-opus-5-5" in out
    assert "openai.answerer: gpt-6-astra" in out and "openai.judge: gpt-6.1-sol" in out and "(not set)" not in out


def test_doctor_shows_caps_when_set_and_the_route_is_the_api(capsys):
    write_settings('[route]\ndefault = "api"\n[budget]\nmonthly_soft_usd = 80\nmonthly_hard_usd = 120\n')
    assert cli.run(["doctor"]) == 0
    out = capsys.readouterr().out
    assert "route: api (hidden model calls use the vendors' APIs and your keys, metered against the cost caps)" in out
    assert "monthly cost cap: soft $80.00, hard $120.00" in out and "run budget: $5.00" in out
    assert "settings file:" in out and "present" in out


def test_doctor_on_the_api_route_says_when_no_cap_is_set(capsys):
    write_settings('[route]\ndefault = "api"\n')
    assert cli.run(["doctor"]) == 0
    assert "monthly cost cap: not set, so live model calls are refused" in capsys.readouterr().out


# --- doctor: the stores and encryption at rest ----------------------------------------------------------------


def stores_section(out: str) -> str:
    return out.split("stores:\n", 1)[1].split("route:", 1)[0]


def test_doctor_lists_the_six_stores_and_creates_none(capsys):
    from northstar_agent_memory.core import db

    assert cli.run(["doctor"]) == 0
    section = stores_section(capsys.readouterr().out)
    for name in db.STORES:
        assert f"  {name}: not created yet\n" in section
    assert "encryption at rest: satisfied (FileVault is On.)" in section
    assert not any(db.store_path(name).exists() for name in db.STORES)  # a check never creates a store


def test_doctor_shows_each_present_store_with_its_schema_version_and_size(capsys):
    from northstar_agent_memory.core import db

    for name in ("history", "memory"):
        db.open_store(name, data_root()).close()
    assert cli.run(["doctor"]) == 0
    section = stores_section(capsys.readouterr().out)
    for name in ("history", "memory"):
        assert re.search(rf"  {name}: present, schema v1, \d+(\.\d)? (B|KB|MB)\n", section), section
    for name in ("working", "index", "overview", "runs"):
        assert f"  {name}: not created yet" in section


def test_doctor_says_when_a_store_cannot_be_read(capsys):
    from northstar_agent_memory.core import db

    path = db.store_path("runs", data_root())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"this is not a database" * 100)
    assert cli.run(["doctor"]) == 0
    line = next(l for l in stores_section(capsys.readouterr().out).splitlines() if l.startswith("  runs:"))
    assert "present, " in line and "but unreadable" in line


def test_doctor_says_when_encryption_at_rest_is_not_satisfied(capsys, monkeypatch):
    monkeypatch.setattr(cli, "filevault_status", lambda: "FileVault is Off.")
    assert cli.run(["doctor"]) == 0
    section = stores_section(capsys.readouterr().out)
    assert "encryption at rest: NOT satisfied (FileVault is Off.; real capture stays off until FileVault is on)" in section
    assert "not enforced while NORTHSTAR_HOME is set" in section  # the tests' throwaway root is exempt


def test_encryption_at_rest_is_only_checked_on_macos(monkeypatch):
    assert cli.encryption_at_rest() == (True, "FileVault is On.")
    monkeypatch.setattr(cli.sys, "platform", "linux")
    ok, detail = cli.encryption_at_rest()
    assert not ok and "macOS only" in detail


def test_store_line_compares_the_schema_version_with_the_newest():
    base = {"name": "memory", "present": True, "latest": 2, "size": 2048}
    assert cli.store_line({**base, "version": 2}) == "  memory: present, schema v2, 2.0 KB"
    assert "schema v1 (v2 is newest: it is migrated when the store opens)" in cli.store_line({**base, "version": 1})
    assert "schema v3, newer than this program knows (v2)" in cli.store_line({**base, "version": 3})
    assert cli.store_line({"name": "runs", "present": False, "latest": 1}) == "  runs: not created yet"


def test_store_report_counts_the_write_ahead_log_in_the_size(tmp_path):
    from northstar_agent_memory.core import db

    conn = db.open_store("history", tmp_path)
    try:
        entry = next(e for e in cli.store_report(tmp_path) if e["name"] == "history")
        wal = tmp_path / "history.db-wal"
        assert entry["size"] == (tmp_path / "history.db").stat().st_size + (wal.stat().st_size if wal.exists() else 0)
        assert entry["version"] == entry["latest"] == 1
    finally:
        conn.close()


# --- doctor: the route, the programs and the logins (no model is called) --------------------------------------

EMAIL = "someone@example.com"
CLAUDE_STATUS = (
    '{"loggedIn": true, "authMethod": "claude.ai", "apiProvider": "firstParty", "email": "%s", '
    '"orgId": "org-123", "orgName": "Some Org", "subscriptionType": "max"}' % EMAIL
)
CODEX_SECRETS = ("sk-codex-secret-1", "id-token-secret", "access-token-secret", "refresh-token-secret", "account-secret")


def program(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\n")
    path.chmod(0o755)
    return path


@pytest.fixture
def programs(tmp_path):
    """Claude Code and Codex named in settings, and a login file for Codex that holds secrets."""
    claude, codex = program(tmp_path / "apps" / "claude"), program(tmp_path / "apps" / "codex")
    write_settings(f'[harness]\nclaude_binary = "{claude}"\ncodex_binary = "{codex}"\n')
    return claude, codex


@pytest.fixture
def codex_home(tmp_path, monkeypatch):
    home = tmp_path / "codex-home"
    home.mkdir()
    (home / "auth.json").write_text(
        json.dumps({"auth_mode": "chatgpt", "OPENAI_API_KEY": CODEX_SECRETS[0],
                    "tokens": {"id_token": CODEX_SECRETS[1], "access_token": CODEX_SECRETS[2],
                               "refresh_token": CODEX_SECRETS[3], "account_id": CODEX_SECRETS[4]}})
    )
    monkeypatch.setenv("CODEX_HOME", str(home))
    return home


def answer_with(monkeypatch, process):
    calls = []

    def run(argv, **kwargs):
        calls.append({"argv": argv, **kwargs})
        return process

    monkeypatch.setattr(harness, "run_process", run)
    return calls


def test_doctor_shows_the_route_the_programs_and_the_logins(capsys, monkeypatch, programs, codex_home):
    claude, codex = programs
    monkeypatch.setenv("ANTHROPIC_API_KEY", SECRET)
    calls = answer_with(monkeypatch, Process(0, CLAUDE_STATUS, ""))
    assert cli.run(["doctor"]) == 0
    captured = capsys.readouterr()
    out = captured.out
    assert "route: harness (hidden model calls run through Claude Code and Codex on your own plans: no API key, no dollar bill)" in out
    assert 'change it with route.default = "harness" or "api" in' in out
    assert f"harness runs start in an empty folder, with hooks off and no saved transcript: {harness_cwd()} (a call stops after 600 s)" in out
    assert f"  claude: {claude}  (from settings)\n    login: signed in with your claude.ai plan, plan max\n" in out
    assert f"  codex: {codex}  (from settings)\n    login: auth_mode chatgpt\n" in out
    # a local command only, run as a call would run it: on the plan login, never on a key
    (call,) = calls
    assert call["argv"] == [str(claude), "auth", "status"] and "ANTHROPIC_API_KEY" not in call["env"]
    for secret in (EMAIL, "org-123", "Some Org", SECRET, *CODEX_SECRETS):
        assert secret not in out and secret not in captured.err


def test_doctor_says_what_is_signed_out_and_how_to_sign_in(capsys, monkeypatch, programs):
    claude, _ = programs
    answer_with(monkeypatch, Process(1, '{"loggedIn": false, "authMethod": "none"}', ""))
    assert cli.run(["doctor"]) == 0
    out = capsys.readouterr().out
    assert f"    login: not signed in; sign in once with `{claude} auth login`" in out
    assert "    login: no auth.json (not signed in, or the login is in the keychain); sign in through the ChatGPT app" in out


def test_doctor_says_when_claude_code_cannot_say_whether_it_is_signed_in(capsys, monkeypatch, programs):
    def timed_out(argv, **kwargs):
        raise subprocess.TimeoutExpired(argv, 30)

    monkeypatch.setattr(harness, "run_process", timed_out)
    assert cli.run(["doctor"]) == 0
    assert "    login: unknown (`auth status` did not answer)" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("status", "shown"),
    [
        ('{"loggedIn": true, "authMethod": "api_key"}', "signed in with an API key, not your plan: calls would be billed to the key"),
        ('{"loggedIn": true, "authMethod": "api_key_helper"}', "signed in with an API key helper, not your plan"),
        ('{"loggedIn": true, "authMethod": "third_party"}', "signed in with a cloud provider, not your plan"),
        ('{"loggedIn": true, "authMethod": "oauth_token"}', "signed in with an OAuth token for your plan"),
        ('{"loggedIn": true}', "signed in\n"),
    ],
)
def test_doctor_warns_when_the_login_is_not_the_plan(capsys, monkeypatch, programs, status, shown):
    answer_with(monkeypatch, Process(0, status, ""))
    assert cli.run(["doctor"]) == 0
    assert f"    login: {shown}" in capsys.readouterr().out


def test_doctor_says_when_a_program_is_not_found(capsys):
    assert cli.run(["doctor"]) == 0  # nothing is installed in the isolated environment
    out = capsys.readouterr().out
    assert "  claude: not found (Claude Code was not found: put `claude` on PATH, install the Claude app, or set harness.claude_binary in" in out
    assert "  codex: not found (Codex was not found: put `codex` on PATH, install the ChatGPT app, or set harness.codex_binary in" in out
    assert "login:" not in out  # no program to ask, and the Codex login is only asked of a Codex that is there


def test_doctor_shows_the_time_limit_from_settings(capsys):
    write_settings("[harness]\ntimeout_s = 90\n")
    assert cli.run(["doctor"]) == 0
    assert "(a call stops after 90 s)" in capsys.readouterr().out


def test_doctor_with_an_unknown_route_fails_plainly(capsys):
    write_settings('[route]\ndefault = "cloud"\n')
    assert cli.run(["doctor"]) == 1
    assert "error: route 'cloud' is not one of harness, api" in capsys.readouterr().err


def test_a_run_with_an_unknown_route_is_reported_plainly_not_as_a_traceback(capsys):
    write_settings('[route]\ndefault = "cloud"\n')
    assert stub_run("--limit", "2", "--run-id", "bad-route", dataset="pilot", systems="B1") == 1
    assert "error: route 'cloud' is not one of harness, api" in capsys.readouterr().err


def test_filevault_status_reads_fdesetup(monkeypatch):
    monkeypatch.undo()  # the autouse fixture replaced it
    ok = subprocess.CompletedProcess([], 0, stdout="FileVault is Off.\n", stderr="")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: ok)
    assert cli.filevault_status() == "FileVault is Off."

    def gone(*a, **k):
        raise FileNotFoundError

    monkeypatch.setattr(subprocess, "run", gone)
    assert cli.filevault_status().startswith("unknown")


def test_main_exits_with_the_command_status(capsys):
    with pytest.raises(SystemExit) as stop:
        cli.main(["doctor"])
    assert stop.value.code == 0
    assert "northstar" in capsys.readouterr().out


def test_the_package_entry_point_runs_the_cli(capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["northstar", "doctor"])
    with pytest.raises(SystemExit) as stop:
        northstar_agent_memory.main()
    assert stop.value.code == 0


# --- models check ------------------------------------------------------------------------------------------


def test_models_check_lists_what_a_key_reaches(capsys, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", SECRET)
    monkeypatch.setattr(cli, "model_ids", lambda family: ["claude-opus-5-5", "claude-x"] if family == "anthropic" else ["gpt-a"])
    assert cli.run(["models", "check"]) == 0
    out = capsys.readouterr().out
    assert "anthropic: 2 models reachable" in out and "claude-opus-5-5  <- configured for answerer" in out
    assert "openai: 1 models reachable" in out and "gpt-a" in out
    assert "Nothing was changed" in out and SECRET not in out
    assert not (data_root() / "settings.toml").exists()


def test_models_check_says_when_a_key_is_missing(capsys):
    assert cli.run(["models", "check", "--family", "openai"]) == 1
    out = capsys.readouterr().out
    assert "openai: no key" in out and "northstar-openai" in out and "OPENAI_API_KEY" in out


def test_models_check_warns_about_a_configured_model_that_is_not_listed(capsys, monkeypatch):
    monkeypatch.setattr(cli, "model_ids", lambda family: ["claude-haiku-5-5"])
    cli.run(["models", "check", "--family", "anthropic"])
    assert "WARNING: claude-opus-5-5 is configured for" in capsys.readouterr().out


def test_models_check_never_prints_an_error_message(capsys, monkeypatch):
    class AuthError(Exception):
        status_code = 401

    def fail(family):
        raise AuthError(f"Incorrect API key provided: {SECRET}")

    monkeypatch.setattr(cli, "model_ids", fail)
    assert cli.run(["models", "check", "--family", "anthropic"]) == 1
    out = capsys.readouterr().out
    assert "AuthError, HTTP 401" in out and SECRET not in out


# --- eval lme prepare --------------------------------------------------------------------------------------


def test_prepare_verifies_selects_and_writes_the_manifest(tiny_selection, capsys):
    manifest = json.loads((eval_root() / "lme_manifest.json").read_text())
    assert len(manifest["dev"]) == 5 and manifest["test"] == []
    assert manifest["meta"]["sha256"] == lme.sha256_of(TINY) and manifest["meta"]["file"].endswith("lme_tiny.json")
    assert manifest["meta"]["seed"] == northstar_config.load()["eval"]["seed"]


def test_the_test_split_loads_too(tiny_selection, no_port, capsys):
    args = ["eval", "run", "--dataset", "lme", "--split", "test", "--answerer-family", "anthropic", "--judge-family", "openai", "--dry-run"]
    assert cli.run(args) == 1  # the tiny selection has no test items; loading the manifest still works
    assert "split has no items" in capsys.readouterr().err


def test_prepare_prints_counts_by_type(monkeypatch, capsys):
    monkeypatch.setitem(lme.SHA256, TINY.name, lme.sha256_of(TINY))
    settings = data_root() / "settings.toml"
    settings.parent.mkdir(parents=True)
    settings.write_text("[eval.longmemeval]\nper_type_dev = 1\nper_type_test = 0\nabstention_dev = 1\nabstention_test = 0\n")
    assert cli.run(["eval", "lme", "prepare", "--file", str(TINY)]) == 0
    out = capsys.readouterr().out
    assert "checksum matches" in out and "dev: 5 items" in out and "knowledge-update (abstention) 1" in out


def test_prepare_refuses_a_file_that_is_not_the_published_one(capsys):
    assert cli.run(["eval", "lme", "prepare", "--file", str(TINY)]) == 1  # no checksum is published for this name
    assert "no published checksum" in capsys.readouterr().err
    assert not (eval_root() / "lme_manifest.json").exists()


def test_prepare_refuses_a_changed_file(tmp_path, monkeypatch, capsys):
    changed = tmp_path / lme.S_FILE
    changed.write_bytes(b"[]")
    assert cli.run(["eval", "lme", "prepare", "--file", str(changed)]) == 1
    assert "is not the published" in capsys.readouterr().err


def test_prepare_needs_a_file(capsys, tmp_path):
    assert cli.run(["eval", "lme", "prepare", "--file", str(tmp_path / "missing.json")]) == 1
    assert "is not a file" in capsys.readouterr().err


# --- eval run: the dry run -----------------------------------------------------------------------------------


def test_a_dry_run_prints_the_estimate_and_calls_no_model(tiny_selection, no_port, capsys):
    args = ["eval", "run", "--dataset", "lme", "--split", "dev", "--answerer-family", "anthropic", "--judge-family", "openai", "--dry-run"]
    assert cli.run(args) == 0
    out = capsys.readouterr().out
    assert "dry run: 5 lme dev items, systems none, B0, B1, B2, B3, B4; no model is called" in out
    for system in runner.SYSTEMS:
        assert f"\n{system} " in out
    assert "not priced" not in out  # both families have models and prices
    assert not (eval_root() / "runs").exists()


def test_a_dry_run_says_which_models_have_no_price(tiny_selection, no_port, capsys):
    write_settings('[models.openai]\njudge = ""\n')
    args = ["eval", "run", "--dataset", "lme", "--split", "dev", "--answerer-family", "anthropic", "--judge-family", "openai", "--dry-run"]
    assert cli.run(args) == 0
    assert "not priced: openai judge: no model configured" in capsys.readouterr().out


def test_a_dry_run_on_the_pilot_warns_when_over_budget(no_port, capsys):
    args = ["eval", "run", "--dataset", "pilot", "--systems", "B0", "--answerer-family", "anthropic", "--judge-family", "anthropic",
            "--allow-same-family", "--dry-run", "--budget-usd", "0.0001"]
    assert cli.run(args) == 0
    out = capsys.readouterr().out
    assert "59 pilot dev items" in out and "more than the run budget of $0.00" in out


def test_a_dry_run_honours_limit(no_port, capsys):
    args = ["eval", "run", "--dataset", "pilot", "--systems", "B1", "--answerer-family", "stub", "--judge-family", "stub",
            "--allow-same-family", "--limit", "7", "--dry-run"]
    assert cli.run(args) == 0
    assert "7 pilot dev items" in capsys.readouterr().out


def test_the_family_rule_holds_on_the_command_line(no_port, capsys):
    args = ["eval", "run", "--dataset", "pilot", "--answerer-family", "openai", "--judge-family", "openai", "--dry-run"]
    assert cli.run(args) == 1
    assert "family rule" in capsys.readouterr().err


def test_bad_input_is_reported_plainly(no_port, capsys):
    base = ["eval", "run", "--dataset", "lme", "--answerer-family", "anthropic", "--judge-family", "openai", "--dry-run"]
    assert cli.run(base) == 1
    assert "eval lme prepare" in capsys.readouterr().err
    assert cli.run([*base[:-1], "--systems", "B7", "--dry-run"]) == 1  # the systems are checked after the data
    assert cli.run(["eval", "run", "--dataset", "pilot", "--split", "test", "--answerer-family", "anthropic",
                    "--judge-family", "openai", "--dry-run"]) == 1
    assert "development set" in capsys.readouterr().err


# --- eval run: end to end ---------------------------------------------------------------------------------------


def stub_run(*extra, dataset="lme", systems="B1,B3,B4"):
    return cli.run(["eval", "run", "--dataset", dataset, "--systems", systems, "--answerer-family", "stub", "--judge-family", "stub",
                    "--allow-same-family", *extra])


def test_a_run_writes_results_resumes_and_reports(tiny_selection, ports, capsys):
    assert stub_run("--run-id", "tiny1", "--workers", "2", "--budget-usd", "1.5") == 0
    out = capsys.readouterr().out
    assert "15 answered, 15 judged, 0 already done, 0 failed" in out
    run_dir = eval_root() / "runs" / "tiny1"
    assert f"results: {run_dir}" in out
    assert ports.seen == [{"run_id": "tiny1", "mode": "record", "budget": 1.5}]
    assert len(runner.load_predictions(run_dir)) == len(runner.load_judgements(run_dir)) == 15

    calls = len(ports.calls)
    assert stub_run("--run-id", "tiny1") == 0
    assert "0 answered, 0 judged, 15 already done" in capsys.readouterr().out
    assert len(ports.calls) == calls

    assert cli.run(["eval", "report", "--run", "tiny1"]) == 0
    report_out = capsys.readouterr().out
    assert "# Run tiny1" in report_out and "| B3 |" in report_out and "Provisional" in report_out
    assert (run_dir / "report.md").exists() and (run_dir / "report.json").exists()
    assert cli.run(["eval", "report", "--run", str(run_dir)]) == 0


def test_a_run_on_the_pilot_asks_each_probe_at_its_checkpoint(ports, capsys):
    assert stub_run("--limit", "4", "--run-id", "pilot1", dataset="pilot", systems="B1,B3") == 0
    assert "8 answered, 8 judged" in capsys.readouterr().out
    run_json = runner.load_run(eval_root() / "runs" / "pilot1")
    assert run_json["dataset"] == "scenario:pilot" and len(run_json["items"]) == 4


def test_replay_only_asks_for_a_port_that_never_calls_a_model(tiny_selection, ports):
    stub_run("--replay-only", "--run-id", "tiny2", systems="B1")
    assert ports.seen[0]["mode"] == "replay"


def test_a_stopped_run_says_how_to_resume(tiny_selection, monkeypatch, capsys):
    from northstar_agent_memory.models.port import BudgetExceeded

    def broke(req):
        raise BudgetExceeded("the run budget is used")

    monkeypatch.setattr(cli, "build_port", lambda config, **k: StubModel(broke))
    assert stub_run("--run-id", "tiny3", "--workers", "1", systems="B1") == 2
    out = capsys.readouterr().out
    assert "stopped early: BudgetExceeded" in out and "--run-id tiny3" in out


def test_a_missing_model_is_an_error_not_a_traceback(tiny_selection, ports, capsys):
    write_settings('[models.openai]\njudge = ""\n')
    args = ["eval", "run", "--dataset", "lme", "--answerer-family", "anthropic", "--judge-family", "openai"]
    assert cli.run(args) == 1
    assert "no model is configured for openai.judge" in capsys.readouterr().err
    assert ports.calls == []


# --- eval judge-check ---------------------------------------------------------------------------------------------


def test_judge_check_runs_and_saves_its_result(tiny_selection, ports, capsys):
    args = ["eval", "judge-check", "--judge-family", "stub", "--generator-family", "anthropic", "--n", "4", "--run-id", "chk1"]
    code = cli.run(args)
    captured = capsys.readouterr()
    out = captured.out
    assert not captured.err, captured.err
    saved = json.loads((eval_root() / "runs" / "chk1" / runner.JUDGE_CHECK_FILE).read_text())
    assert (code == 0) == saved["passed"]
    assert "judge check chk1: stub judge on anthropic answers, 4 items" in out and "wrong answers" in out
    assert "95% upper bound" in out and "at least 60 wrong answers needed" in out
    assert "INSUFFICIENT: " in out  # four items cannot give 60 wrong answers; the generic stub judge also accepts them all
    assert code == 1 and saved["passed"] is False and saved["result"] == "insufficient"
    assert saved["judge_model"] == "stub-judge" and saved["prompt_hash"] == jd.prompt_hash() and saved["judge_batch_size"] == 8


def test_judge_check_obeys_the_family_rule(no_port, capsys):
    assert cli.run(["eval", "judge-check", "--judge-family", "openai", "--generator-family", "openai", "--dataset", "pilot"]) == 1
    assert "another family" in capsys.readouterr().err


# --- eval normal-use ----------------------------------------------------------------------------------------------


def test_normal_use_writes_a_report_with_no_model_call(no_port, tmp_path, capsys):
    out_file = tmp_path / "nu" / "report.json"
    assert cli.run(["eval", "normal-use", "--projects-dir", str(CLAUDE_CODE), "--out", str(out_file)]) == 0
    out = capsys.readouterr().out
    assert "no model was called" in out and f"written to {out_file}" in out
    data = json.loads(out_file.read_text())
    assert data["window"]["sessions"] == 6 and data["weeks"]


def test_normal_use_writes_under_the_data_root_by_default(no_port, capsys):
    assert cli.run(["eval", "normal-use", "--projects-dir", str(CLAUDE_CODE), "--since", "2026-01-01"]) == 0
    files = list((eval_root() / "normal_use").glob("claude-code-*.json"))
    assert len(files) == 1


def test_normal_use_needs_a_folder(no_port, tmp_path, capsys):
    assert cli.run(["eval", "normal-use", "--projects-dir", str(tmp_path / "nope")]) == 1
    assert "is not a folder" in capsys.readouterr().err


def test_report_for_an_unknown_run_fails_plainly(capsys):
    assert cli.run(["eval", "report", "--run", "nothing-here"]) == 1
    assert "run.json is missing" in capsys.readouterr().err


# --- systems -----------------------------------------------------------------------------------------------------


def test_the_default_systems_hold_none_and_b3(no_port, capsys):
    run_parser = cli.build_parser().parse_args(["eval", "run", "--dataset", "pilot", "--answerer-family", "stub", "--judge-family", "stub"])
    assert cli.parse_systems(run_parser.systems) == ["none", "B0", "B1", "B2", "B3", "B4"]
    assert cli.parse_systems("b3, NONE ,b1,B3") == ["B3", "none", "B1"]  # one spelling each, no repeats
    with pytest.raises(cli.CliError, match="some of none, B0"):
        cli.parse_systems("B7")


# --- held-out ----------------------------------------------------------------------------------------------------


@pytest.fixture
def clean_tree(monkeypatch):
    monkeypatch.setattr(runner, "git_state", lambda: ("c0ffee0123", False))


def write_judge_check(name="chk0", **edits):
    meta = {"judge_model": "stub-judge", "n_positives": 70, "n_negatives": 70, "true_accept_rate": 1.0, "false_accept_rate": 0.0,
            "false_accept_upper95": 0.05, "false_accept_by_kind": {"vague": 0.0}, "n_by_kind": {"vague": 70}}
    check = {"judge_family": "stub", "generator_family": "anthropic", "judge_model": "stub-judge", "prompt_hash": jd.prompt_hash(),
             "bar": 0.1, "passed": True, "result": "passed", "checked_at": "2026-10-28T10:00:00+00:00", "meta": meta, **edits}
    runner.write_json(eval_root() / "runs" / name / runner.JUDGE_CHECK_FILE, check)


def held_out_args(*extra, split="test", systems="B1,B3"):
    return ["eval", "run", "--dataset", "lme", "--split", split, "--systems", systems, "--answerer-family", "stub",
            "--judge-family", "stub", "--allow-same-family", *extra]


def test_a_run_on_the_test_split_needs_held_out(tiny_test_selection, no_port, capsys):
    assert cli.run(held_out_args("--run-id", "h0")) == 1
    err = capsys.readouterr().err
    assert "needs --held-out" in err and "clean git work tree" in err
    assert not (eval_root() / "runs" / "h0").exists()


def test_a_dry_run_on_the_test_split_needs_no_flag(tiny_test_selection, no_port, capsys):
    assert cli.run(held_out_args("--dry-run")) == 0
    assert "5 lme test items" in capsys.readouterr().out


def test_held_out_goes_only_with_the_test_split(tiny_selection, no_port, capsys):
    assert cli.run(held_out_args("--held-out", split="dev")) == 1
    assert "--held-out goes with --split test" in capsys.readouterr().err


def test_a_held_out_run_needs_a_clean_tree_and_a_passing_judge_check(tiny_test_selection, ports, monkeypatch, capsys):
    write_judge_check()
    monkeypatch.setattr(runner, "git_state", lambda: ("c0ffee0123", True))
    assert cli.run(held_out_args("--held-out", "--run-id", "h1")) == 1
    assert "clean git work tree" in capsys.readouterr().err
    monkeypatch.setattr(runner, "git_state", lambda: ("c0ffee0123", False))
    write_judge_check(prompt_hash="0" * 16)
    (eval_root() / "runs" / "chk0" / runner.JUDGE_CHECK_FILE).unlink()
    write_judge_check("chk1", passed=False)
    assert cli.run(held_out_args("--held-out", "--run-id", "h1")) == 1
    assert "no passing judge check" in capsys.readouterr().err
    assert ports.calls == [] and not (eval_root() / runner.HELD_OUT_LEDGER).exists()


def test_a_held_out_run_is_logged_and_keeps_its_check(tiny_test_selection, ports, clean_tree, capsys):
    write_judge_check()
    assert cli.run(held_out_args("--held-out", "--run-id", "h2")) == 0
    out = capsys.readouterr().out
    assert "10 answered, 10 judged" in out and "held-out ledger" in out
    run_dir = eval_root() / "runs" / "h2"
    run_json = runner.load_run(run_dir)
    assert run_json["held_out"] is True and run_json["fingerprint"]["git_commit"] == "c0ffee0123"
    assert (run_dir / runner.JUDGE_CHECK_FILE).exists()
    (entry,) = runner.read_jsonl(eval_root() / runner.HELD_OUT_LEDGER)
    assert entry["run_id"] == "h2" and entry["systems"] == ["B1", "B3"] and entry["split"] == "test"
    assert cli.run(["eval", "report", "--run", "h2"]) == 0
    assert "held-out run, code c0ffee0123" in capsys.readouterr().out


# --- privacy ------------------------------------------------------------------------------------------------------


@pytest.fixture
def repo(tmp_path):
    """A folder that is a git work tree: it holds a .git."""
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    return root


def test_a_path_in_a_git_work_tree_is_found_even_when_it_does_not_exist(repo, tmp_path):
    assert cli.inside_git_work_tree(repo) and cli.inside_git_work_tree(repo / "a" / "b" / "report.json")
    assert not cli.inside_git_work_tree(tmp_path / "elsewhere" / "report.json")
    linked = tmp_path / "linked"  # a linked work tree holds a .git file
    linked.mkdir()
    (linked / ".git").write_text("gitdir: /somewhere/else\n")
    assert cli.inside_git_work_tree(linked / "sub")
    (repo / "link").symlink_to(tmp_path)  # a path is judged after it is resolved
    assert not cli.inside_git_work_tree(repo / "link" / "elsewhere")
    assert cli.inside_git_work_tree(tmp_path / "elsewhere" / ".." / "repo" / "x")


def test_normal_use_refuses_an_out_path_in_a_git_work_tree(no_port, repo, capsys):
    out_file = repo / "docs" / "usage.json"
    assert cli.run(["eval", "normal-use", "--projects-dir", str(CLAUDE_CODE), "--out", str(out_file)]) == 1
    err = capsys.readouterr().err
    assert "inside a git work tree" in err and "--allow-repo-path" in err
    assert not out_file.exists()
    assert cli.run(["eval", "normal-use", "--projects-dir", str(CLAUDE_CODE), "--out", str(out_file), "--allow-repo-path"]) == 0
    assert out_file.exists()


def test_normal_use_refuses_the_data_root_inside_a_git_work_tree(no_port, repo, monkeypatch, capsys):
    monkeypatch.setenv("NORTHSTAR_HOME", str(repo / "home"))
    assert cli.run(["eval", "normal-use", "--projects-dir", str(CLAUDE_CODE)]) == 1
    assert "inside a git work tree" in capsys.readouterr().err
    assert not (repo / "home").exists()


def test_a_report_path_in_a_git_work_tree_is_refused(repo, capsys):
    run_dir = repo / "run"
    runner.write_json(run_dir / runner.RUN_FILE, {"run_id": "x"})
    assert cli.run(["eval", "report", "--run", str(run_dir)]) == 1
    assert "inside a git work tree" in capsys.readouterr().err
    assert not (run_dir / "report.md").exists()


def test_a_run_folder_in_a_git_work_tree_is_refused(repo, monkeypatch, capsys):
    monkeypatch.setenv("NORTHSTAR_HOME", str(repo / "home"))
    monkeypatch.setattr(cli, "build_port", lambda *a, **k: pytest.fail("a port was built"))
    assert stub_run("--run-id", "r", "--limit", "2", dataset="pilot") == 1
    assert "inside a git work tree" in capsys.readouterr().err
    assert not (repo / "home").exists()


def test_normal_use_refuses_the_home_folder(no_port, tmp_path, monkeypatch, capsys):
    home = tmp_path / "home"
    (home / "Library").mkdir(parents=True)
    (home / "Library" / "notes.jsonl").write_text("{}\n")
    monkeypatch.setenv("HOME", str(home))
    assert cli.run(["eval", "normal-use", "--projects-dir", str(home)]) == 1
    err = capsys.readouterr().err
    assert "whole home folder" in err
    assert cli.run(["eval", "normal-use", "--projects-dir", "~"]) == 1
    assert cli.run(["eval", "normal-use", "--projects-dir", "/"]) == 1
    capsys.readouterr()
    assert cli.run(["eval", "normal-use", "--projects-dir", str(home / "Library"), "--out", str(tmp_path / "o.json")]) == 0  # a folder below it is fine


def test_normal_use_says_how_many_transcript_files_before_it_reads(no_port, tmp_path, monkeypatch, capsys):
    from northstar_agent_memory.eval import normal_use

    def fail(*a, **k):
        assert f"{len(list(CLAUDE_CODE.rglob('*.jsonl')))} transcript files" in capsys.readouterr().out  # printed before reading
        raise RuntimeError("stop here")

    monkeypatch.setattr(normal_use, "analyse", fail)
    with pytest.raises(RuntimeError):
        cli.run(["eval", "normal-use", "--projects-dir", str(CLAUDE_CODE), "--out", str(tmp_path / "o.json")])


def test_normal_use_with_no_transcripts_is_an_error(no_port, tmp_path, capsys):
    (tmp_path / "empty").mkdir()
    assert cli.run(["eval", "normal-use", "--projects-dir", str(tmp_path / "empty")]) == 1
    captured = capsys.readouterr()
    assert "0 transcript files" in captured.out and "no transcript files" in captured.err


def test_the_gitignore_keeps_personal_files_out_of_a_commit():
    ignore = (Path(__file__).parent.parent / ".gitignore").read_text().splitlines()
    for pattern in ("*.sqlite", "*.sqlite-wal", "*.sqlite-shm", "runs/", "normal_use/", "settings.toml"):
        assert pattern in ignore


def test_a_plan_limit_stops_a_run_on_the_harness_route_cleanly_and_says_how_to_resume(tiny_selection, monkeypatch, capsys, programs):
    limit = json.dumps(
        {"type": "result", "subtype": "success", "is_error": True, "result": "You've hit your session limit · resets 3pm",
         "stop_reason": None, "session_id": "s", "total_cost_usd": 0, "usage": {}, "modelUsage": {}, "uuid": "u"}
    )
    calls = answer_with(monkeypatch, Process(1, limit, ""))
    args = ["eval", "run", "--dataset", "lme", "--systems", "B1", "--answerer-family", "anthropic", "--judge-family", "openai",
            "--workers", "1", "--run-id", "limit1"]
    assert cli.run(args) == 2
    out = capsys.readouterr().out
    assert "stopped early: PlanLimitReached: Claude Code: your plan or workspace refused the call for usage or spend" in out
    assert "resume with: northstar eval run ... --run-id limit1" in out
    assert len(calls) == 1 and calls[0]["argv"][0] == str(programs[0])  # the first refusal ended the run: nothing else was tried
    from northstar_agent_memory.models.budget import CostLedger

    assert CostLedger(eval_root() / "cost-ledger.sqlite").entries() == []  # a refused call used no tokens
