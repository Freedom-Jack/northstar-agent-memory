import logging
import sqlite3
from contextlib import closing
from datetime import UTC, datetime

import pytest

import model_fakes as f
from northstar_agent_memory.models.budget import ROUTES, BudgetGuard, CostLedger, attach, cost_usd, estimate_cost
from northstar_agent_memory.models.harness import HarnessResult
from northstar_agent_memory.models.port import (
    BudgetExceeded,
    ModelError,
    ModelRefused,
    ModelResult,
    NoCostCap,
    PlanLimitReached,
    Usage,
)
from northstar_agent_memory.models.recorder import RecordingPort
from northstar_agent_memory.models.stub import StubModel


def result(cost: float, from_record=False) -> ModelResult:
    return ModelResult("t", None, Usage(10, 5), cost, 0.1, "anthropic", "claude-opus-5-5", "claude-opus-5-5", "end_turn",
                       from_record=from_record)


class Costly:
    """Inner port returning a fixed cost per call."""

    def __init__(self, cost=0.01, error=None):
        self.cost, self.error, self.n = cost, error, 0

    def complete(self, req):
        self.n += 1
        if self.error:
            raise self.error
        return result(self.cost)


@pytest.fixture
def ledger(tmp_path):
    return CostLedger(tmp_path / "ledger.sqlite")


def guard(inner, ledger, config, run_id="r1", **kw):
    return BudgetGuard(inner, ledger, config, run_id, **kw)


def test_no_cap_refuses_live_calls_but_not_stub(ledger):
    config = f.make_config()  # hard cap 0 by default
    inner = Costly()
    with pytest.raises(NoCostCap, match="settings.toml"):
        guard(inner, ledger, config).complete(f.make_req())
    assert inner.n == 0
    stub = guard(StubModel(), ledger, config)
    assert stub.complete(f.make_req(family="stub", role="judge")).text == "stub"


def test_live_call_is_recorded_in_ledger(ledger, config):
    guard(Costly(0.0123), ledger, config).complete(f.make_req(purpose="lme.answer"))
    (row,) = ledger.entries()
    assert row["run_id"] == "r1" and row["purpose"] == "lme.answer" and row["family"] == "anthropic"
    assert row["model"] == "claude-opus-5-5" and row["cost_usd"] == 0.0123 and row["input_tokens"] == 10
    assert row["at"].endswith("+00:00")
    assert ledger.run_spent_usd("r1") == pytest.approx(0.0123) and ledger.run_spent_usd("other") == 0
    assert ledger.month_to_date_usd() == pytest.approx(0.0123)


def test_month_to_date_ignores_other_months(ledger):
    ledger.record("r", "p", result(3.0))
    now = datetime.now(UTC)
    next_month = now.replace(year=now.year + (now.month == 12), month=now.month % 12 + 1, day=1)
    assert ledger.month_to_date_usd() == 3.0
    assert ledger.month_to_date_usd(now=next_month) == 0.0


def test_hard_cap(ledger):
    config = f.make_config(monthly_hard_usd=1.0, monthly_soft_usd=0.5, run_default_usd=50)
    ledger.record("old", "p", result(0.999))
    inner = Costly()
    with pytest.raises(BudgetExceeded, match="monthly hard cap"):
        guard(inner, ledger, config).complete(f.make_req(max_tokens=4000))
    assert inner.n == 0


def test_run_budget(ledger, config):
    ledger.record("r1", "p", result(4.999))
    inner = Costly()
    with pytest.raises(BudgetExceeded, match="run 'r1'"):
        guard(inner, ledger, config).complete(f.make_req())
    assert inner.n == 0
    # another run, or a bigger budget for this one, is fine
    guard(inner, ledger, config, run_id="r2").complete(f.make_req())
    guard(inner, ledger, config, run_budget_usd=50).complete(f.make_req())
    assert inner.n == 2


def test_estimate_is_conservative(config):
    req = f.make_req(system="x" * 3500, max_tokens=100_000)
    price = config["prices"]["claude-opus-5-5"]
    # 3500 chars of system plus 5 of message is about 1002 input tokens; output capped at 4000
    assert estimate_cost(price, req) == pytest.approx((1002 * 4 + 4000 * 20) / 1e6)
    small = f.make_req(system="", messages=[{"role": "user", "content": ""}], max_tokens=100)
    assert estimate_cost(price, small) == pytest.approx(100 * 20 / 1e6)


def test_soft_cap_warns_once(ledger, caplog):
    config = f.make_config(monthly_hard_usd=100, monthly_soft_usd=0.001, run_default_usd=5)
    g = guard(Costly(), ledger, config)
    with caplog.at_level(logging.WARNING):
        g.complete(f.make_req())
        g.complete(f.make_req())
    assert sum("soft cap" in r.message for r in caplog.records) == 1
    assert g.past_soft_cap


def test_replays_cost_nothing_and_need_no_cap(tmp_path, ledger):
    no_cap = f.make_config()
    inner = Costly(0.5)
    recorder = RecordingPort(inner, tmp_path / "rec.sqlite")
    capped = f.make_config(monthly_hard_usd=100, run_default_usd=5)
    guard(recorder, ledger, capped).complete(f.make_req())  # live, recorded
    assert ledger.run_spent_usd("r1") == 0.5
    # a later run with no cap set can still replay, and nothing is added to the ledger
    again = guard(RecordingPort(inner, tmp_path / "rec.sqlite", mode="replay"), ledger, no_cap, run_id="r2")
    out = again.complete(f.make_req())
    assert out.from_record and inner.n == 1
    assert ledger.run_spent_usd("r2") == 0 and len(ledger.entries()) == 1
    # but a miss in the same setting is refused by the recorder, still without spending
    with pytest.raises(ModelError, match="no recording"):
        again.complete(f.make_req(system="new"))


def test_record_mode_hit_passes_with_no_cap_but_miss_is_refused(tmp_path, ledger):
    inner = Costly()
    rec = RecordingPort(inner, tmp_path / "rec.sqlite")
    guard(rec, ledger, f.make_config(monthly_hard_usd=10)).complete(f.make_req())
    no_cap = guard(rec, ledger, f.make_config(), run_id="r2")
    assert no_cap.complete(f.make_req()).from_record
    with pytest.raises(NoCostCap):
        no_cap.complete(f.make_req(system="new"))


def test_billed_failure_is_metered(ledger, config):
    err = ModelRefused("declined")
    err.result = result(0.2)
    with pytest.raises(ModelRefused):
        guard(Costly(error=err), ledger, config).complete(f.make_req())
    (row,) = ledger.entries()
    assert row["cost_usd"] == 0.2 and row["outcome"] == "ModelRefused"


def test_unbilled_failure_is_not_metered(ledger, config):
    with pytest.raises(ModelError):
        guard(Costly(error=ModelError("net")), ledger, config).complete(f.make_req())
    assert ledger.entries() == []


def test_missing_price_refuses_before_calling(ledger, config):
    inner = Costly()
    with pytest.raises(ModelError, match="no price"):
        guard(inner, ledger, config).complete(f.make_req(model="claude-unpriced"))
    assert inner.n == 0


def test_cost_usd_formula(config):
    price = config["prices"]["claude-opus-5-5"]
    usage = Usage(input_tokens=1_000, output_tokens=2_000, cache_read_tokens=3_000, cache_write_tokens=4_000)
    expected = (1_000 * 4 + 2_000 * 20 + 3_000 * 0.2 + 4_000 * 4 * 1.25) / 1e6
    assert cost_usd(price, usage) == pytest.approx(expected)


def test_long_prompt_cache_read_uses_the_explicit_long_price(config):
    price = config["prices"]["gpt-6-astra"]  # 272K threshold; 20 in, 75 out, 2.00 cached when long
    long = Usage(input_tokens=100_000, output_tokens=10_000, cache_read_tokens=200_000)
    assert cost_usd(price, long) == pytest.approx((100_000 * 20 + 10_000 * 75 + 200_000 * 2.00) / 1e6)
    short = Usage(input_tokens=100_000, output_tokens=10_000, cache_read_tokens=100_000)
    assert cost_usd(price, short) == pytest.approx((100_000 * 10 + 10_000 * 50 + 100_000 * 1.00) / 1e6)


def test_long_prompt_without_long_cache_read_keeps_the_ratio(config):
    price = config["prices"]["claude-haiku-5-5"]  # no long_cache_read: 0.01 * 0.50 / 0.10
    usage = Usage(input_tokens=0, output_tokens=0, cache_read_tokens=200_000)
    assert cost_usd(price, usage) == pytest.approx(200_000 * 0.05 / 1e6)


def test_estimate_prices_input_at_the_cache_write_rate_only_when_caching(config):
    price = config["prices"]["claude-opus-5-5"]
    plain = f.make_req(system="x" * 3500, messages=[{"role": "user", "content": ""}], max_tokens=100)
    cached = f.make_req(system="x" * 3500, messages=[{"role": "user", "content": ""}], max_tokens=100, cache=True)
    # 3500 chars at 3.5 chars per token is 1000 tokens; opus input is 4, a cache write is 5
    assert estimate_cost(price, plain) == pytest.approx((1000 * 4 + 100 * 20) / 1e6)
    assert estimate_cost(price, cached) == pytest.approx((1000 * 5 + 100 * 20) / 1e6)


def test_estimate_ignores_the_cache_flag_for_openai(config):
    price = config["prices"]["gpt-6.1-sol"]
    req = f.make_req(family="openai", system="x" * 3500, messages=[{"role": "user", "content": ""}], max_tokens=100)
    cached = f.make_req(
        family="openai", system="x" * 3500, messages=[{"role": "user", "content": ""}], max_tokens=100, cache=True
    )
    assert estimate_cost(price, cached) == estimate_cost(price, req) == pytest.approx((1000 * 2 + 100 * 10) / 1e6)


# --- the harness route (DESIGN §1.4, 2026-10-29): a plan has no dollar bill -----------------------------------


def harness_result(api_equivalent=0.42, family="anthropic") -> HarnessResult:
    return HarnessResult("t", None, Usage(120, 30, 400, 50), 0.0, 1.5, family, "claude-opus-5-5", "claude-opus-5-5",
                         "end_turn", request_id="sess-1", api_equivalent_usd=api_equivalent)


class Planned:
    """Inner port for the harness route: a result, or an error."""

    def __init__(self, result=None, error=None):
        self.result, self.error, self.n = result or harness_result(), error, 0

    def complete(self, req):
        self.n += 1
        if self.error:
            raise self.error
        return self.result


def test_the_routes_are_the_two_the_design_names():
    assert ROUTES == ("harness", "api")


def test_a_harness_call_needs_no_cap_and_is_recorded_with_its_tokens_its_route_and_the_api_equivalent(ledger):
    config = f.make_config()  # no monthly cap: on the api route this call would be refused
    inner = Planned()
    out = guard(inner, ledger, config, route="harness").complete(f.make_req(purpose="lme.answer"))
    assert out.cost_usd == 0.0 and inner.n == 1
    (row,) = ledger.entries()
    assert row["route"] == "harness" and row["family"] == "anthropic" and row["purpose"] == "lme.answer"
    assert (row["input_tokens"], row["output_tokens"], row["cache_read_tokens"], row["cache_write_tokens"]) == (120, 30, 400, 50)
    assert row["cost_usd"] == 0.0 and row["api_equivalent_usd"] == 0.42 and row["request_id"] == "sess-1"
    assert ledger.month_to_date_usd() == 0.0 and ledger.run_spent_usd("r1") == 0.0  # nothing was billed


def test_the_same_call_on_the_api_route_is_still_refused_without_a_cap(ledger):
    inner = Planned()
    with pytest.raises(NoCostCap):
        guard(inner, ledger, f.make_config(), route="api").complete(f.make_req())
    with pytest.raises(NoCostCap):
        guard(inner, ledger, f.make_config()).complete(f.make_req())  # api is the guard's default
    assert inner.n == 0


def test_the_caps_and_the_run_budget_do_not_apply_on_the_harness_route(ledger):
    config = f.make_config(monthly_hard_usd=0.0001, monthly_soft_usd=0.00005, run_default_usd=0.0001)
    ledger.record("old", "p", result(5.0))  # an earlier month's spend on the api route is already past the cap
    inner = Planned()
    g = guard(inner, ledger, config, route="harness")
    for _ in range(3):
        g.complete(f.make_req(max_tokens=100_000))
    assert inner.n == 3 and not g.past_soft_cap


def test_a_call_without_an_api_equivalent_records_none(ledger, config):
    guard(Planned(harness_result(api_equivalent=None, family="openai")), ledger, config, route="harness").complete(
        f.make_req(family="openai")
    )
    (row,) = ledger.entries()
    assert row["route"] == "harness" and row["api_equivalent_usd"] is None


def test_a_plan_limit_stops_a_run_like_a_cap_and_is_not_recorded(ledger, config):
    inner = Planned(error=PlanLimitReached("You hit your spend cap"))
    with pytest.raises(BudgetExceeded, match="spend cap") as info:
        guard(inner, ledger, config, route="harness").complete(f.make_req())
    assert type(info.value) is PlanLimitReached and ledger.entries() == []


def test_a_harness_call_that_failed_after_the_model_answered_is_recorded_with_its_tokens(ledger, config):
    err = attach(ModelError("structured output is not valid JSON"), harness_result(api_equivalent=0.1))
    with pytest.raises(ModelError):
        guard(Planned(error=err), ledger, config, route="harness").complete(f.make_req())
    (row,) = ledger.entries()
    assert row["outcome"] == "ModelError" and row["route"] == "harness" and row["output_tokens"] == 30
    assert row["api_equivalent_usd"] == 0.1


def test_api_calls_are_recorded_as_api_and_stub_calls_as_stub_whatever_the_route(ledger, config):
    guard(Costly(0.01), ledger, config).complete(f.make_req())
    guard(StubModel(), ledger, config, route="harness").complete(f.make_req(family="stub", role="judge"))
    guard(StubModel(), ledger, config).complete(f.make_req(family="stub", role="judge"))
    assert [(r["route"], r["family"], r["api_equivalent_usd"]) for r in ledger.entries()] == [
        ("api", "anthropic", None),
        ("stub", "stub", None),
        ("stub", "stub", None),
    ]


def test_a_route_that_is_not_known_is_refused_so_a_typo_cannot_switch_the_caps_off(ledger, config):
    with pytest.raises(ValueError, match="route must be one of"):
        guard(Planned(), ledger, config, route="harnes")


def test_a_ledger_made_before_the_harness_route_gains_its_columns_and_keeps_its_rows(tmp_path):
    path = tmp_path / "old.sqlite"
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.executescript(
            """
            CREATE TABLE calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, run_id TEXT NOT NULL, family TEXT NOT NULL,
                model TEXT NOT NULL, served_model TEXT, purpose TEXT NOT NULL, input_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL, cache_read_tokens INTEGER NOT NULL, cache_write_tokens INTEGER NOT NULL,
                cost_usd REAL NOT NULL, latency_s REAL NOT NULL, outcome TEXT NOT NULL, request_id TEXT
            );
            INSERT INTO calls (at, run_id, family, model, purpose, input_tokens, output_tokens, cache_read_tokens,
                cache_write_tokens, cost_usd, latency_s, outcome)
            VALUES ('2026-10-28T10:00:00+00:00', 'old-run', 'openai', 'gpt-6-astra', 'lme.answer', 10, 5, 0, 0, 1.5, 0.2, 'ok'),
                   ('2026-10-28T10:01:00+00:00', 'old-run', 'stub', 'stub-judge', 'judge.qa', 1, 1, 0, 0, 0.0, 0.0, 'ok');
            """
        )
    ledger = CostLedger(path)
    old_api, old_stub = ledger.entries("old-run")
    assert (old_api["route"], old_api["api_equivalent_usd"], old_api["cost_usd"]) == ("api", None, 1.5)
    assert (old_stub["route"], old_stub["api_equivalent_usd"]) == ("stub", None)  # every older call was a stub or an API call
    ledger.record("new-run", "p", harness_result(), route="harness")
    new = ledger.entries("new-run")[0]
    assert (new["route"], new["api_equivalent_usd"]) == ("harness", 0.42)
    assert CostLedger(path).run_spent_usd("old-run") == 1.5  # opening it again changes nothing
    assert len(CostLedger(path).entries()) == 3
