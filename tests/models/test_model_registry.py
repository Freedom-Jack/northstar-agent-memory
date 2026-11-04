import pytest

import model_fakes as f
from northstar_agent_memory.models import harness, registry
from northstar_agent_memory.models.anthropic_adapter import AnthropicAdapter
from northstar_agent_memory.models.budget import CostLedger
from northstar_agent_memory.models.harness_claude import ClaudeCodeHeadless
from northstar_agent_memory.models.harness_codex import CodexExec
from northstar_agent_memory.models.openai_adapter import OpenAIAdapter
from northstar_agent_memory.models.port import ModelError, NoCostCap, PlanLimitReached
from northstar_agent_memory.models.registry import FamilyRouter, build_port, resolve_route
from northstar_agent_memory.models.stub import StubModel


def test_stub_family_through_the_full_stack_defaults_under_eval_root(isolated_home):
    port = build_port(f.make_config(), run_id="run-a")
    req = f.make_req(family="stub")
    assert not port.complete(req).from_record
    assert port.complete(req).from_record
    eval_dir = isolated_home / "data" / "eval"
    assert (eval_dir / registry.RECORD_DB).exists() and (eval_dir / registry.LEDGER_DB).exists()


def test_live_family_without_a_cap_is_refused_before_any_adapter_is_built(tmp_path):
    port = build_port(
        f.make_config(), run_id="r", record_db=tmp_path / "a.sqlite", ledger_db=tmp_path / "b.sqlite", route="api"
    )
    with pytest.raises(NoCostCap):
        port.complete(f.make_req(family="openai"))


def test_missing_key_fails_only_for_the_family_used(config):
    router = FamilyRouter(f.with_openai(config), route="api")
    with pytest.raises(ModelError, match="OpenAI"):
        router.complete(f.make_req(family="openai"))
    assert router.complete(f.make_req(family="stub")).text == "stub"


def test_router_creates_adapters_lazily_and_routes_by_family(config, monkeypatch):
    made = []

    class Fake:
        def __init__(self, name):
            self.name = name

        def complete(self, req):
            return self.name

    router = FamilyRouter(config)
    monkeypatch.setattr(router, "_make", lambda family: made.append(family) or Fake(family))
    assert made == []
    assert router.complete(f.make_req(family="openai")) == "openai"
    assert router.complete(f.make_req(family="openai")) == "openai"
    assert router.complete(f.make_req(family="anthropic")) == "anthropic"
    assert made == ["openai", "anthropic"]


def test_recorded_replay_mode_never_calls_a_model(tmp_path, config):
    kwargs = dict(run_id="r", record_db=tmp_path / "a.sqlite", ledger_db=tmp_path / "b.sqlite")
    build_port(config, **kwargs).complete(f.make_req(family="stub"))
    replay = build_port(f.make_config(), mode="replay", **kwargs)
    assert replay.complete(f.make_req(family="stub")).from_record
    with pytest.raises(ModelError, match="no recording"):
        replay.complete(f.make_req(family="stub", system="different"))


def test_model_change_in_config_is_a_new_recording(tmp_path, config):
    kwargs = dict(run_id="r", record_db=tmp_path / "a.sqlite", ledger_db=tmp_path / "b.sqlite")
    port = build_port(config, **kwargs)
    # stub models are named by role, so key by an explicit model instead
    port.complete(f.make_req(family="stub", model="m1"))
    assert port.complete(f.make_req(family="stub", model="m1")).from_record
    assert not port.complete(f.make_req(family="stub", model="m2")).from_record


# --- the route (DESIGN §1.4, 2026-10-29) ------------------------------------------------------------


def test_the_route_comes_from_config_unless_an_argument_overrides_it(config):
    assert config["route"]["default"] == "harness" and resolve_route(config) == "harness"
    assert resolve_route(config, "api") == "api"
    config["route"]["default"] = "api"
    assert resolve_route(config) == "api" and resolve_route(config, "harness") == "harness"
    assert resolve_route({}) == "harness"  # a config with no [route] gets the design's default


@pytest.mark.parametrize("bad", ["cloud", "API", "harnes"])
def test_a_route_that_is_not_known_is_refused_plainly(config, bad):
    with pytest.raises(ModelError, match=f"route '{bad}' is not one of harness, api: set route.default in .*settings.toml"):
        resolve_route(config, bad)
    config["route"]["default"] = bad
    with pytest.raises(ModelError, match="is not one of"):
        FamilyRouter(config)
    with pytest.raises(ModelError, match="is not one of"):
        build_port(config, run_id="r")


def test_the_harness_route_builds_claude_code_and_codex_with_no_key(config):
    router = FamilyRouter(config)  # the isolated environment has no key of either vendor
    assert router.route == "harness"
    assert isinstance(router._make("anthropic"), ClaudeCodeHeadless)
    assert isinstance(router._make("openai"), CodexExec)
    assert isinstance(router._make("stub"), StubModel)
    with pytest.raises(ModelError, match="unknown model family"):
        router._make("gemini")


def test_the_api_route_builds_the_vendors_adapters(config, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-not-real")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-not-real")
    router = FamilyRouter(config, route="api")
    assert isinstance(router._make("anthropic"), AnthropicAdapter)
    assert isinstance(router._make("openai"), OpenAIAdapter)
    assert isinstance(router._make("stub"), StubModel)
    with pytest.raises(ModelError, match="unknown model family"):
        router._make("gemini")


def test_each_family_goes_to_its_own_program_on_the_harness_route(tmp_path, config, monkeypatch):
    claude, codex = f.make_program(tmp_path / "claude"), f.make_program(tmp_path / "codex")
    fake = f.FakeProcess(f.claude_ok("from claude"))
    monkeypatch.setattr(harness, "run_process", fake)
    router = FamilyRouter(f.with_programs(f.with_openai(config), claude=claude, codex=codex))
    assert router.complete(f.make_req(family="anthropic")).text == "from claude"
    assert fake.calls[-1]["argv"][0] == str(claude)
    monkeypatch.setattr(harness, "run_process", f.FakeProcess(f.codex_ok("from codex")))
    assert router.complete(f.make_req(family="openai")).text == "from codex"


def test_a_harness_run_needs_no_cap_and_the_ledger_records_its_tokens_and_route(tmp_path, monkeypatch):
    program = f.make_program(tmp_path / "claude")
    fake = f.FakeProcess(f.claude_ok("the answer", cost=0.25))
    monkeypatch.setattr(harness, "run_process", fake)
    config = f.with_programs(f.make_config(), claude=program)  # no monthly cap at all
    assert config["budget"]["monthly_hard_usd"] == 0
    kwargs = dict(run_id="run-h", record_db=tmp_path / "rec.sqlite", ledger_db=tmp_path / "ledger.sqlite")
    port = build_port(config, **kwargs)
    first = port.complete(f.make_req(purpose="lme.answer"))
    assert first.text == "the answer" and first.cost_usd == 0.0 and not first.from_record
    again = port.complete(f.make_req(purpose="lme.answer"))  # recorded: a replay runs no program and adds no row
    assert again.from_record and again.text == "the answer" and len(fake.calls) == 1
    (row,) = CostLedger(tmp_path / "ledger.sqlite").entries("run-h")
    assert (row["route"], row["family"], row["cost_usd"], row["api_equivalent_usd"]) == ("harness", "anthropic", 0.0, 0.25)
    assert (row["input_tokens"], row["output_tokens"], row["cache_read_tokens"], row["cache_write_tokens"]) == (120, 30, 400, 50)
    assert row["purpose"] == "lme.answer" and row["outcome"] == "ok" and row["request_id"] == "sess-1"


def test_a_plan_limit_stops_the_run_with_a_budget_error_and_leaves_no_record(tmp_path, monkeypatch):
    program = f.make_program(tmp_path / "codex")
    monkeypatch.setattr(harness, "run_process", f.FakeProcess(f.codex_failed("You hit your spend cap set by the owner of your workspace.")))
    config = f.with_programs(f.make_config(), codex=program)
    port = build_port(config, run_id="r", record_db=tmp_path / "rec.sqlite", ledger_db=tmp_path / "ledger.sqlite")
    with pytest.raises(PlanLimitReached):
        port.complete(f.make_req(family="openai"))
    assert CostLedger(tmp_path / "ledger.sqlite").entries() == []


def test_the_route_argument_wins_over_config_so_the_api_route_is_still_capped(tmp_path):
    port = build_port(f.make_config(), run_id="r", record_db=tmp_path / "a.sqlite", ledger_db=tmp_path / "b.sqlite", route="api")
    with pytest.raises(NoCostCap):
        port.complete(f.make_req(family="anthropic"))
    config = f.make_config()
    config["route"]["default"] = "api"
    port = build_port(config, run_id="r", record_db=tmp_path / "a.sqlite", ledger_db=tmp_path / "b.sqlite")
    with pytest.raises(NoCostCap):  # the configured route applies when no argument is given
        port.complete(f.make_req(family="anthropic"))


def test_a_stub_run_is_the_same_on_both_routes(tmp_path):
    for route in ("harness", "api"):
        ledger_db = tmp_path / f"{route}.sqlite"
        port = build_port(f.make_config(), run_id="r", record_db=tmp_path / f"{route}-rec.sqlite", ledger_db=ledger_db, route=route)
        assert port.complete(f.make_req(family="stub")).text == "stub"
        (row,) = CostLedger(ledger_db).entries()
        assert row["route"] == "stub" and row["family"] == "stub"
