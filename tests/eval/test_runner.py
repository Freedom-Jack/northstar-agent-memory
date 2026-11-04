"""Runner tests: a stub model answers and judges; nothing touches the network."""

from __future__ import annotations

import copy
import json
import re
from dataclasses import replace
from pathlib import Path

import pytest

from northstar_agent_memory import config as northstar_config
from northstar_agent_memory.eval import baselines as bl
from northstar_agent_memory.eval import judge as jd
from northstar_agent_memory.eval import longmemeval as lme
from northstar_agent_memory.eval import runner
from northstar_agent_memory.eval.scenarios.pilot import load_pilot
from northstar_agent_memory.models.budget import BudgetGuard, CostLedger
from northstar_agent_memory.models.port import (
    BudgetExceeded,
    ModelError,
    ModelRequest,
    ModelUnavailable,
    NoCostCap,
    NoCredentials,
    PlanLimitReached,
)
from northstar_agent_memory.models.recorder import RecordingPort
from northstar_agent_memory.models.stub import StubModel

FIXTURE = Path(__file__).parent / "fixtures" / "lme_tiny.json"
ITEMS = lme.to_items(lme.load(FIXTURE))
GOLD = {i.question: i for i in ITEMS}
WRONG_ID = "su_001"  # the stub answerer gets this one wrong


def _tag(text: str, tag: str) -> str:
    m = re.search(rf"<{tag}>\n(.*?)\n</{tag}>", text, re.S)
    return m.group(1) if m else ""


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


def make_handler(fail=None):
    """Answers every baseline's calls and judges by comparing with the gold answer."""

    def handler(req):
        text = req.messages[-1]["content"]
        if req.purpose == "judge.qa":
            response = _tag(text, "response").lower()
            if "<explanation>" in text:
                return {"rationale": "r", "label": "correct" if "know" in response else "wrong"}
            return {"rationale": "r", "label": "correct" if _tag(text, "correct_answer").lower() in response else "wrong"}
        if req.purpose == "b4.observe":
            return {"observations": [{"text": "the user mentioned something", "message_ids": []}]}
        question = re.findall(r"Question: (.*)", req.messages[0]["content"])[-1]
        item = GOLD[question]
        if fail and fail(item):
            raise ModelError("the stub is told to fail")
        answer = "I don't know" if item.abstention else "something else" if item.id == WRONG_ID else item.gold_answer
        if req.purpose in ("b2.step", "b2.answer"):
            return {"action": "answer", "pattern": None, "session_id": None, "start": None, "end": None, "answer": answer, "cited": []}
        return {"answer": answer, "cited": []}

    return with_batches(handler)


@pytest.fixture
def config():
    return northstar_config.load()


@pytest.fixture(autouse=True)
def clean_git(monkeypatch):
    """The code under test is at a fixed commit with a clean tree, whatever the real checkout is."""
    monkeypatch.setattr(runner, "git_state", lambda: ("c0ffee0123", False))


def without_model(config, family, role):
    cfg = copy.deepcopy(config)
    cfg["models"][family][role] = ""
    return cfg


@pytest.fixture
def stub():
    return StubModel(make_handler())


def run(stub, config, tmp_path, systems=runner.SYSTEMS, **kw):
    kw = {"answerer_family": "stub", "judge_family": "stub", "allow_same_family": True, "run_id": "r1", **kw}
    return runner.run_qa(ITEMS, list(systems), port=stub, config=config, out_dir=tmp_path / "run", **kw)


def rows(tmp_path, name):
    return runner.read_jsonl(tmp_path / "run" / name)


# --- a run -----------------------------------------------------------------------------------------


def test_every_system_answers_and_is_judged(stub, config, tmp_path):
    summary = run(stub, config, tmp_path)
    assert (summary.answered, summary.judged, summary.skipped, summary.errors) == (30, 30, 0, [])
    assert summary.complete
    assert len(rows(tmp_path, runner.PREDICTIONS_FILE)) == len(rows(tmp_path, runner.JUDGEMENTS_FILE)) == 30
    judgements = runner.load_judgements(tmp_path / "run")
    assert {(j.system, j.item_id) for j in judgements} == {(s, i.id) for s in runner.SYSTEMS for i in ITEMS}
    assert all(j.rationale.startswith("not independent") for j in judgements if j.judge_family != "code")
    run_json = runner.load_run(tmp_path / "run")
    assert run_json["systems"] == list(runner.SYSTEMS)
    assert {i["id"] for i in run_json["items"]} == {i.id for i in ITEMS}
    assert run_json["allow_same_family"] is True


def test_the_default_systems_hold_the_closed_book_run_and_the_evidence():
    assert "none" in runner.SYSTEMS and "B3" in runner.SYSTEMS
    assert runner.SYSTEMS == ("none", "B0", "B1", "B2", "B3", "B4")
    assert {n: c.system for n, c in runner.baseline_classes().items()} == {n: n for n in runner.SYSTEMS}


def test_the_judge_marks_the_wrong_and_right_answers(stub, config, tmp_path):
    run(stub, config, tmp_path, systems=("B3",))
    outcome = {j.item_id: j.outcome for j in runner.load_judgements(tmp_path / "run")}
    assert outcome[WRONG_ID] == "hallucinated"
    assert outcome["ku_002_abs"] == "correct"
    assert outcome["tr_001"] == "correct"


def test_judgements_carry_the_judge_cost(config, tmp_path):
    from northstar_agent_memory.models.port import ModelResult, Usage

    inner = make_handler()

    def handler(req):
        base = inner(req)
        return ModelResult(json.dumps(base), base, Usage(10, 5), 0.25, 1.5, "stub", "m", "m", "end_turn")

    run(StubModel(handler), config, tmp_path, systems=("B1",))
    judged = rows(tmp_path, runner.JUDGEMENTS_FILE)
    assert len(judged) == 5  # one batched call, its cost and time shared among the five pairs
    assert sum(r["judge_cost_usd"] for r in judged) == pytest.approx(0.25)
    assert sum(r["judge_latency_s"] for r in judged) == pytest.approx(1.5)
    predictions = runner.load_predictions(tmp_path / "run")
    assert all(p.cost_usd == 0.25 and p.calls == 1 for p in predictions)


def test_the_judge_must_be_of_another_family(stub, config, tmp_path):
    with pytest.raises(ValueError, match="family rule"):
        run(stub, config, tmp_path, allow_same_family=False)
    assert not (tmp_path / "run").exists()


def test_limit_takes_items_from_each_type_in_turn():
    picked = runner.limit_items(ITEMS, 3)
    assert [i.id for i in picked] == ["ku_001", "tr_001", "ms_001"]
    assert runner.limit_items(ITEMS, None) == ITEMS and runner.limit_items(ITEMS, 99) == ITEMS


def test_an_unknown_system_is_refused(stub, config, tmp_path):
    with pytest.raises(ValueError, match="unknown system"):
        run(stub, config, tmp_path, systems=("B9",))


def test_a_model_without_an_id_is_refused_before_any_call(stub, config, tmp_path):
    cfg = without_model(config, "openai", "judge")
    with pytest.raises(ModelError, match="openai.judge"):
        run(stub, cfg, tmp_path, answerer_family="anthropic", judge_family="openai", allow_same_family=False)
    assert stub.calls == []


def test_a_different_judge_family_is_used_and_not_flagged(tmp_path):
    cfg = copy.deepcopy(northstar_config.load())
    cfg["models"]["openai"] = {role: "gpt-test" for role in cfg["models"]["anthropic"]}
    stub = StubModel(make_handler())
    summary = runner.run_qa(
        ITEMS, ["B1"], answerer_family="anthropic", judge_family="openai", port=stub, config=cfg, run_id="r2", out_dir=tmp_path / "run"
    )
    assert summary.complete
    assert {c.family for c in stub.calls if c.purpose == "judge.qa.batch"} == {"openai"}
    assert {c.family for c in stub.calls if c.purpose == "lme.answer"} == {"anthropic"}
    assert not any(j.rationale.startswith("not independent") for j in runner.load_judgements(tmp_path / "run"))
    assert runner.load_run(tmp_path / "run")["models"]["openai.judge"] == "gpt-test"


# --- resuming ----------------------------------------------------------------------------------------


def test_a_second_call_skips_finished_pairs(stub, config, tmp_path):
    first = run(stub, config, tmp_path, systems=("B1", "B3"), limit=2)
    assert (first.answered, first.judged) == (4, 4)
    calls = len(stub.calls)
    second = run(stub, config, tmp_path, systems=("B1", "B3"), limit=2)
    assert (second.answered, second.judged, second.skipped) == (0, 0, 4)
    assert len(stub.calls) == calls
    third = run(stub, config, tmp_path, systems=("B1", "B3"))
    assert (third.answered, third.judged, third.skipped) == (6, 6, 4)
    assert len(rows(tmp_path, runner.PREDICTIONS_FILE)) == 10
    assert len(runner.load_run(tmp_path / "run")["items"]) == 5


def test_a_run_can_gain_a_system(stub, config, tmp_path):
    run(stub, config, tmp_path, systems=("B1",))
    summary = run(stub, config, tmp_path, systems=("B3",))
    assert (summary.answered, summary.skipped) == (5, 0)
    assert runner.load_run(tmp_path / "run")["systems"] == ["B1", "B3"]


def test_a_failed_item_is_recorded_and_tried_again(config, tmp_path):
    stub = StubModel(make_handler(fail=lambda item: item.id == "tr_001"))
    first = run(stub, config, tmp_path, systems=("B1",))
    assert [(e["item"], e["system"]) for e in first.errors] == [("tr_001", "B1")]
    assert not first.complete and first.judged == 4
    failed = [r for r in rows(tmp_path, runner.PREDICTIONS_FILE) if r["meta"].get("error")]
    assert len(failed) == 1 and failed[0]["answer"] == ""
    assert "tr_001" not in {r["item_id"] for r in rows(tmp_path, runner.JUDGEMENTS_FILE)}

    healed = run(StubModel(make_handler()), config, tmp_path, systems=("B1",))
    assert (healed.answered, healed.judged, healed.skipped, healed.errors) == (1, 1, 4, [])
    assert len(runner.load_predictions(tmp_path / "run")) == 5
    assert not any(p.meta.get("error") for p in runner.load_predictions(tmp_path / "run"))


def test_an_answered_item_is_only_judged_again(config, tmp_path):
    stub = StubModel(make_handler())
    run(stub, config, tmp_path, systems=("B1",))
    path = tmp_path / "run" / runner.JUDGEMENTS_FILE
    kept = path.read_text().splitlines()[:-2]  # the run stopped before its last two judgements
    path.write_text("\n".join(kept) + "\n" + '{"item_id": "torn')  # and cut a line short
    before = len(stub.calls)
    summary = run(stub, config, tmp_path, systems=("B1",))
    assert (summary.answered, summary.judged, summary.skipped) == (0, 2, 3)
    assert all(c.purpose == "judge.qa.batch" for c in stub.calls[before:]) and len(stub.calls) == before + 1
    assert len(runner.load_judgements(tmp_path / "run")) == 5


def test_a_budget_error_stops_the_run_and_writes_nothing_for_it(config, tmp_path):
    def handler(req):
        if req.purpose == "lme.answer":
            raise BudgetExceeded("the run budget is used")
        return make_handler()(req)

    summary = run(StubModel(handler), config, tmp_path, systems=("B1",), max_workers=1)
    assert summary.stopped and "BudgetExceeded" in summary.stopped
    assert summary.answered == summary.judged == 0 and not summary.complete
    assert rows(tmp_path, runner.PREDICTIONS_FILE) == []
    assert runner.load_run(tmp_path / "run") is not None


def test_a_resumed_run_must_keep_its_families(stub, config, tmp_path):
    run(stub, config, tmp_path, systems=("B1",))
    with pytest.raises(ValueError, match="another run id"):
        run(stub, config, tmp_path, systems=("B1",), judge_family="anthropic")


def test_a_run_through_the_recorder_replays_for_free(config, tmp_path):
    stub = StubModel(make_handler())
    port = BudgetGuard(RecordingPort(stub, tmp_path / "rec.sqlite"), CostLedger(tmp_path / "ledger.sqlite"), config, "r1")
    run(port, config, tmp_path, systems=("B1", "B4"))
    live = len(stub.calls)
    assert live > 0
    replay = RecordingPort(stub, tmp_path / "rec.sqlite", mode="replay")
    again = runner.run_qa(
        ITEMS, ["B1", "B4"], answerer_family="stub", judge_family="stub", allow_same_family=True,
        port=replay, config=config, run_id="r1", out_dir=tmp_path / "run2",
    )
    assert again.complete and again.judged == 10
    assert len(stub.calls) == live


# --- code judging --------------------------------------------------------------------------------------


def test_a_forbidden_term_is_judged_wrong_by_code(stub, config):
    judge = runner.jd.QAJudge(stub, "stub", allow_same_family=True)
    item = replace(ITEMS[0], meta={"forbidden_terms": ["migraine", "clinic"]})
    leak = runner.Prediction(item.id, "B1", "Out for a Clinic visit.", meta={"family": "stub"})
    fine = runner.Prediction(item.id, "B1", "Out for an appointment.", meta={"family": "stub"})
    j = runner.judge_prediction(judge, item, leak)
    assert (j.outcome, j.judge_family) == ("hallucinated", "code")
    assert stub.calls == []
    assert runner.judge_prediction(judge, item, fine).judge_family == "stub"
    assert runner.leaked_term(item, "a clinical trial") is None


# --- cost estimate ---------------------------------------------------------------------------------------


def test_the_estimate_prices_each_system_from_config(config):
    big = [replace(i, haystack=i.haystack * 100) for i in ITEMS]  # longer than the token budget
    est = runner.estimate_cost(big, list(runner.SYSTEMS), "anthropic", "openai", config)
    assert set(est) == set(runner.SYSTEMS)
    # both families have models and prices by default
    assert all(e["total_usd"] is not None and e["unpriced"] == [] and e["judge_usd"] > 0 for e in est.values())
    assert est["B0"]["answer_usd"] > est["B1"]["answer_usd"] > est["none"]["answer_usd"] > 0
    assert est["none"]["calls"] == 2 * len(big)  # one answer and one judgement per item
    assert est["B4"]["calls"] > est["B1"]["calls"]
    assert est["B1"]["items"] == len(big)

    cfg = without_model(config, "openai", "judge")
    unpriced = runner.estimate_cost(ITEMS, ["B1"], "anthropic", "openai", cfg)["B1"]
    assert unpriced["total_usd"] is None and unpriced["unpriced"] == ["openai judge: no model configured"]
    cfg["models"]["openai"]["judge"] = "gpt-test"
    cfg["prices"]["gpt-test"] = {"input": 1.0, "output": 4.0}
    priced = runner.estimate_cost(ITEMS, ["B1"], "anthropic", "openai", cfg)["B1"]
    assert priced["unpriced"] == [] and priced["judge_usd"] > 0
    assert priced["total_usd"] == pytest.approx(priced["answer_usd"] + priced["judge_usd"])


def test_the_stub_family_costs_nothing(config):
    est = runner.estimate_cost(ITEMS, ["B0", "B2"], "stub", "stub", config)
    assert all(e["total_usd"] == 0.0 and e["calls"] > 0 for e in est.values())


def test_the_estimate_grows_with_the_history(config):
    short = ITEMS[0]
    long = replace(short, haystack=short.haystack * 20)
    a = runner.estimate_cost([short], ["B0", "B4"], "anthropic", "anthropic", config)
    b = runner.estimate_cost([long], ["B0", "B4"], "anthropic", "anthropic", config)
    assert b["B0"]["input_tokens"] > 3 * a["B0"]["input_tokens"]
    assert b["B4"]["calls"] > a["B4"]["calls"]


def test_no_model_is_called_by_an_estimate(config):
    stub = StubModel()
    runner.estimate_cost(ITEMS, list(runner.SYSTEMS), "anthropic", "openai", config)
    assert stub.calls == []


# --- the judge's own test --------------------------------------------------------------------------------


# the five items, copied under other ids and questions: a judge check needs 60 wrong answers
CLONES = [replace(i, id=f"{i.id}-{k}", question=f"{i.question} [{k}]") for k in range(8) for i in ITEMS]
CLONE_GOLD = {**GOLD, **{i.question: i for i in CLONES}}


def probe_handler(strict: bool):
    def handler(req):
        if req.purpose == "judge.meta.probes":
            item = CLONE_GOLD[re.findall(r"<question>\n(.*?)\n</question>", req.messages[0]["content"], re.S)[0]]
            positive = item.gold_answer
            return {
                "positive": positive,
                "wrong_on_topic": "a wrong thing about the topic",
                "partial": "part of it" if not item.abstention else None,
                "vague": "it was something like that",
                "stale": None,
            }
        text = req.messages[-1]["content"]
        response = _tag(text, "response").lower()
        if not strict:
            return {"rationale": "fine", "label": "correct"}
        if "<explanation>" in text:
            return {"rationale": "r", "label": "correct" if "know" in response or "not enough" in response else "wrong"}
        return {"rationale": "r", "label": "correct" if _tag(text, "correct_answer").lower() in response else "wrong"}

    return with_batches(handler)


def test_a_strict_judge_passes_its_check(config, tmp_path):
    result = runner.run_judge_check(CLONES, StubModel(probe_handler(True)), "openai", "anthropic", config, tmp_path)
    assert result["passed"] is True and result["result"] == "passed" and result["bar"] == 0.10
    assert result["meta"]["false_accept_rate"] == 0.0 and result["meta"]["n_negatives"] >= 60
    assert result["meta"]["true_accept_rate"] >= 0.85 and result["meta"]["false_accept_upper95"] < 0.10
    saved = json.loads((tmp_path / runner.JUDGE_CHECK_FILE).read_text())
    assert saved["passed"] is True and saved["judge_family"] == "openai"
    assert len(runner.read_jsonl(tmp_path / runner.JUDGE_PROBES_FILE)) == result["meta"]["n"]


def test_the_judge_check_records_what_it_tested(config, tmp_path):
    result = runner.run_judge_check(CLONES, StubModel(probe_handler(True)), "openai", "anthropic", config, tmp_path)
    saved = json.loads((tmp_path / runner.JUDGE_CHECK_FILE).read_text())
    assert saved["judge_model"] == config["models"]["openai"]["judge"] == "gpt-6.1-sol"
    assert saved["prompt_hash"] == jd.prompt_hash() and saved["dataset"] == CLONES[0].dataset
    assert set(saved["probe_kinds"]) == {"positive", "wrong_on_topic", "partial", "vague"}
    assert saved["probe_kinds"]["positive"] == len(CLONES) and saved["n_items"] == len(CLONES)
    assert saved["min_wrong"] == 60 and saved["min_true_accept"] == 0.85
    assert saved["config_version"] == config["config_version"] and result["prompt_hash"] == saved["prompt_hash"]


def test_a_judge_check_on_too_few_wrong_answers_is_insufficient_not_a_pass(config, tmp_path):
    result = runner.run_judge_check(ITEMS, StubModel(probe_handler(True)), "openai", "anthropic", config, tmp_path)
    assert result["meta"]["false_accept_rate"] == 0.0 and 0 < result["meta"]["n_negatives"] < 60
    assert result["result"] == "insufficient" and result["passed"] is False
    assert json.loads((tmp_path / runner.JUDGE_CHECK_FILE).read_text())["result"] == "insufficient"


def test_a_judge_that_accepts_everything_fails_its_check(config, tmp_path):
    result = runner.run_judge_check(CLONES, StubModel(probe_handler(False)), "openai", "anthropic", config, tmp_path)
    assert result["passed"] is False and result["result"] == "failed" and result["meta"]["false_accept_rate"] == 1.0
    assert json.loads((tmp_path / runner.JUDGE_CHECK_FILE).read_text())["passed"] is False


def test_a_judge_that_rejects_the_right_answers_fails_its_check(config, tmp_path):
    def handler(req):
        if req.purpose == "judge.qa.batch":
            return {"verdicts": [{"id": i, "rationale": "r", "label": "wrong"} for i in re.findall(r'<pair id="(p\d+)">', req.messages[-1]["content"])]}
        return probe_handler(True)(req)

    result = runner.run_judge_check(CLONES, StubModel(handler), "openai", "anthropic", config, tmp_path)
    assert result["meta"]["false_accept_rate"] == 0.0 and result["meta"]["true_accept_rate"] == 0.0
    assert result["result"] == "failed" and result["passed"] is False


def test_the_judge_check_obeys_the_family_rule(config, tmp_path):
    with pytest.raises(ValueError, match="family rule"):
        runner.run_judge_check(CLONES, StubModel(probe_handler(True)), "openai", "openai", config, tmp_path)


def test_the_judge_check_sends_every_request_without_cache_or_fallback(config, tmp_path):
    stub = StubModel(probe_handler(True))
    runner.run_judge_check(CLONES[:5], stub, "openai", "anthropic", config, tmp_path)
    assert {c.purpose for c in stub.calls} == {"judge.meta.probes", "judge.qa.batch"}
    assert all(c.cache is False and c.allow_fallback is False for c in stub.calls)


# --- scenario worlds -----------------------------------------------------------------------------------------


def test_the_pilot_runs_with_each_probe_asked_at_its_checkpoint(config, tmp_path):
    world = load_pilot()
    questions = {p.question: p for p in world.probes}

    def single(req):
        if req.purpose == "judge.qa":
            return {"rationale": "r", "label": "correct"}
        question = re.findall(r"Question: (.*)", req.messages[0]["content"])[-1]
        assert question in questions
        return {"answer": "an answer", "cited": []}

    stub = StubModel(with_batches(single))
    summary = runner.run_scenario_qa(
        world, ["B1", "B3"], answerer_family="stub", judge_family="stub", allow_same_family=True,
        port=stub, config=config, run_id="pilot1", out_dir=tmp_path / "pilot", limit=6,
    )
    assert (summary.answered, summary.judged, summary.errors) == (12, 12, [])
    run_json = runner.load_run(tmp_path / "pilot")
    assert run_json["dataset"] == "scenario:pilot" and len(run_json["items"]) == 6
    asked = [c for c in stub.calls if c.purpose == "lme.answer"]
    assert len(asked) == 12
    # a probe sees only the history up to its checkpoint
    probe = next(p for p in world.probes if p.question in asked[0].messages[0]["content"])
    last_before = probe.meta["after_message_id"]
    later = [m.id for s in world.sessions for m in s.messages]
    after = later[later.index(last_before) + 1 :]
    assert after and not any(f"[{i}]" in asked[0].messages[0]["content"] for i in after)


# --- the report --------------------------------------------------------------------------------------------


def two_family_run(tmp_path, systems=("B1", "B3"), run_id="r2"):
    cfg = copy.deepcopy(northstar_config.load())
    cfg["models"]["openai"] = {role: "gpt-test" for role in cfg["models"]["anthropic"]}
    stub = StubModel(make_handler())
    out = tmp_path / "run"
    runner.run_qa(ITEMS, list(systems), answerer_family="anthropic", judge_family="openai", port=stub, config=cfg, run_id=run_id, out_dir=out)
    return cfg, out


def test_the_summary_scores_each_system(stub, config, tmp_path):
    from northstar_agent_memory.eval import report

    run(stub, config, tmp_path, systems=("B1", "B3"))
    summary = report.summarize(tmp_path / "run")
    b3 = summary["systems"]["B3"]
    assert b3["n_judged"] == 5 and b3["n_errors"] == 0
    assert b3["counts"] == {"correct": 4, "hallucinated": 1, "omitted": 0}
    assert b3["accuracy"]["estimate"] == pytest.approx(0.8) and b3["accuracy"]["n"] == 5
    assert b3["accuracy"]["low"] <= 0.8 <= b3["accuracy"]["high"]
    assert b3["abstention_accuracy"]["estimate"] == 1.0 and b3["abstention_accuracy"]["n"] == 1
    assert b3["answerable_accuracy"]["n"] == 4
    assert set(b3["by_type"]) == {"knowledge-update", "temporal-reasoning", "multi-session", "single-session-user"}
    assert b3["by_type"]["single-session-user"]["estimate"] == 0.0
    assert b3["calls"] == 5 and b3["tokens"]["input"] > 0 and b3["tokens"]["mean_context"] > 0
    assert b3["cost_usd"]["total"] == b3["cost_usd"]["answer"] + b3["cost_usd"]["judge"]
    assert summary["run"]["n_items"] == 5 and summary["run"]["answerer_family"] == "stub"
    assert summary["ledger"] is None


def test_scores_are_provisional_until_an_independent_judge_has_passed_its_check(stub, config, tmp_path):
    from northstar_agent_memory.eval import report

    run(stub, config, tmp_path, systems=("B1",))
    summary = report.summarize(tmp_path / "run")
    assert summary["counts"] is False and summary["not_independent"] == 5
    md = report.to_markdown(summary)
    assert "Provisional" in md and "own family" in md and "no judge check on file" in md


def test_scores_count_after_a_passing_judge_check(tmp_path):
    from northstar_agent_memory.eval import report

    cfg, out = two_family_run(tmp_path)
    assert report.summarize(out)["counts"] is False  # no check yet
    runner.run_judge_check(CLONES, StubModel(probe_handler(True)), "openai", "anthropic", cfg, out)
    summary = report.summarize(out)
    assert summary["counts"] is True and summary["judge_check"]["passed"] is True
    md = report.to_markdown(summary)
    assert "Provisional" not in md and "## Judge check" in md and "passed" in md and "95% upper bound" in md
    assert summary["judge_check"]["judge_batch_size"] == 8 and "8 answers to a call" in md.split("## Judge check")[1]
    assert "grades 8 answers to a call" in md.split("## ")[0]  # the run summary line
    # a check that tested too few wrong answers, or a failed one, does not make the scores count
    runner.run_judge_check(ITEMS, StubModel(probe_handler(True)), "openai", "anthropic", cfg, out)
    summary = report.summarize(out)
    assert summary["counts"] is False and "too few wrong answers" in report.to_markdown(summary)
    runner.run_judge_check(CLONES, StubModel(probe_handler(False)), "openai", "anthropic", cfg, out)
    summary = report.summarize(out)
    assert summary["counts"] is False
    assert "failed its test" in report.to_markdown(summary)


def test_scores_count_only_for_the_judge_model_and_prompt_that_were_tested(tmp_path, monkeypatch):
    from northstar_agent_memory.eval import report

    cfg, out = two_family_run(tmp_path)
    runner.run_judge_check(CLONES, StubModel(probe_handler(True)), "openai", "anthropic", cfg, out)
    assert report.summarize(out)["counts"] is True
    path = out / runner.JUDGE_CHECK_FILE
    saved = json.loads(path.read_text())

    path.write_text(json.dumps({**saved, "judge_model": "another-judge"}))  # tested with another model
    summary = report.summarize(out)
    assert summary["counts"] is False and "another-judge" in report.to_markdown(summary)

    path.write_text(json.dumps({**saved, "prompt_hash": "0" * 16}))  # tested with another prompt
    summary = report.summarize(out)
    assert summary["counts"] is False and "another judge prompt" in report.to_markdown(summary)

    path.write_text(json.dumps(saved))
    assert report.summarize(out)["counts"] is True


def test_an_item_without_a_judgement_counts_as_omitted(stub, config, tmp_path):
    from northstar_agent_memory.eval import report

    run(stub, config, tmp_path, systems=("B3",))
    path = tmp_path / "run" / runner.JUDGEMENTS_FILE
    path.write_text("\n".join(path.read_text().splitlines()[:3]) + "\n")
    s = report.summarize(tmp_path / "run")["systems"]["B3"]
    assert s["n_judged"] == 3 and s["counts"]["omitted"] == 2
    assert s["accuracy"]["n"] == 5 and s["accuracy"]["estimate"] <= 0.6


def test_a_failed_item_shows_as_an_error_and_not_a_cost(config, tmp_path):
    from northstar_agent_memory.eval import report

    run(StubModel(make_handler(fail=lambda item: item.id == "tr_001")), config, tmp_path, systems=("B1",))
    s = report.summarize(tmp_path / "run")["systems"]["B1"]
    assert s["n_errors"] == 1 and s["n_judged"] == 4 and s["calls"] == 4 and s["counts"]["omitted"] == 1


def test_the_report_holds_no_question_or_answer_text(stub, config, tmp_path):
    from northstar_agent_memory.eval import report

    run(stub, config, tmp_path, systems=("B1", "B3"))
    summary, md_path = report.write_report(tmp_path / "run")
    text = json.dumps(summary) + md_path.read_text()
    for item in ITEMS:
        assert item.question not in text and item.id not in text
        assert len(item.gold_answer) < 5 or item.gold_answer not in text
    assert "something else" not in text
    assert (tmp_path / "run" / "report.json").exists()
    assert "| B3 |" in md_path.read_text() and "p95 s" in md_path.read_text()


def test_the_report_adds_the_ledgers_live_spend(stub, config, tmp_path):
    from northstar_agent_memory.eval import report
    from northstar_agent_memory.models.port import ModelResult, Usage

    run(stub, config, tmp_path, systems=("B1",))
    ledger = CostLedger(tmp_path / "ledger.sqlite")
    ledger.record("r1", "lme.answer", ModelResult("t", None, Usage(1, 1), 0.5, 1.0, "stub", "m", "m", "end_turn"))
    summary = report.summarize(tmp_path / "run", tmp_path / "ledger.sqlite")
    assert summary["ledger"] == {"calls": 1, "spent_usd": 0.5}
    assert "1 live calls" in report.to_markdown(summary)


def test_summarizing_a_folder_without_a_run_fails_plainly(tmp_path):
    from northstar_agent_memory.eval import report

    with pytest.raises(FileNotFoundError, match="run.json"):
        report.summarize(tmp_path)


# --- the measurement port ----------------------------------------------------------------------------------


def test_every_request_goes_out_without_cache_or_fallback(config, tmp_path):
    stub = StubModel(make_handler())
    run(stub, config, tmp_path)
    assert len(stub.calls) > 30
    assert all(c.cache is False and c.allow_fallback is False for c in stub.calls)


def test_the_measurement_port_overrides_a_request_that_asks_for_cache_or_the_fallback():
    stub = StubModel(lambda req: "ok")
    ask = ModelRequest("t", "answerer", "stub", "s", [{"role": "user", "content": "q"}], cache=True, allow_fallback=True)
    runner.measured(stub).complete(ask)
    assert (stub.calls[0].cache, stub.calls[0].allow_fallback) == (False, False)
    assert (ask.cache, ask.allow_fallback) == (True, True)  # the caller's request is not changed
    port = runner.measured(stub)
    assert runner.measured(port) is port


@pytest.mark.parametrize("error", [BudgetExceeded, NoCostCap, NoCredentials, ModelUnavailable])
def test_a_fatal_error_stops_the_whole_run(config, tmp_path, error):
    def handler(req):
        if req.purpose == "lme.answer":
            raise error("this will fail for every call")
        return make_handler()(req)

    stub = StubModel(handler)
    summary = run(stub, config, tmp_path, systems=("B1", "B3"), max_workers=1)
    assert summary.stopped and error.__name__ in summary.stopped and not summary.complete
    assert summary.errors == [] and summary.answered == 0
    assert len(stub.calls) == 1  # nothing was tried after the first fatal error
    assert rows(tmp_path, runner.PREDICTIONS_FILE) == []


def test_a_fatal_error_while_judging_stops_the_run_too(config, tmp_path):
    def handler(req):
        if req.purpose.startswith("judge.qa"):
            raise ModelUnavailable("404: no such model")
        return make_handler()(req)

    summary = run(StubModel(handler), config, tmp_path, systems=("B1",), max_workers=1)
    assert "ModelUnavailable" in summary.stopped and summary.judged == 0 and summary.errors == []


# --- item by item ------------------------------------------------------------------------------------------


def test_every_system_runs_on_an_item_before_any_runs_on_the_next(stub, config, tmp_path):
    run(stub, config, tmp_path, systems=("B1", "B3", "none"), max_workers=1)
    order = [(r["item_id"], r["system"]) for r in rows(tmp_path, runner.PREDICTIONS_FILE)]
    assert order == [(item.id, system) for item in ITEMS for system in ("B1", "B3", "none")]


def test_a_stop_leaves_the_systems_on_the_same_items(config, tmp_path):
    answers = []

    def handler(req):
        if req.purpose == "lme.answer":
            answers.append(req)
            if len(answers) == 8:
                raise BudgetExceeded("the run budget is used")
        return make_handler()(req)

    summary = run(StubModel(handler), config, tmp_path, systems=("B1", "B3", "none"), max_workers=1)
    assert summary.stopped
    done = {}
    for r in rows(tmp_path, runner.JUDGEMENTS_FILE):
        done.setdefault(r["system"], set()).add(r["item_id"])
    assert {s: len(v) for s, v in done.items()} == {"B1": 3, "B3": 2, "none": 2}  # items 1 and 2 are whole, item 3 is cut
    assert done["B3"] == done["none"] == {i.id for i in ITEMS[:2]} and done["B1"] == {i.id for i in ITEMS[:3]}


# --- resuming with the same settings --------------------------------------------------------------------------


def first_run(config, tmp_path, **kw):
    run(StubModel(make_handler()), config, tmp_path, systems=("B1",), **kw)
    return runner.load_run(tmp_path / "run")


def test_the_run_keeps_a_fingerprint_of_what_it_was_made_with(config, tmp_path):
    fp = first_run(config, tmp_path)["fingerprint"]
    assert fp["config_version"] == config["config_version"] and fp["token_budget"] == config["eval"]["token_budget"]
    assert fp["models"] == {"stub.answerer": "stub-answerer", "stub.judge": "stub-judge"}
    assert fp["answer_prompt_hash"] == runner.answer_prompt_hash() and fp["judge_prompt_hash"] == jd.prompt_hash()
    assert (fp["git_commit"], fp["git_dirty"]) == ("c0ffee0123", False)
    assert fp["bars"] == {"lme_margin_points": 10, "judge_false_accept_max": 0.10}
    assert fp["system_params"] == {}
    run_json = runner.load_run(tmp_path / "run")
    assert run_json["config_version"] == fp["config_version"] and run_json["models"] == fp["models"]


def test_the_fingerprint_names_the_parameters_of_b0_and_b2(stub, config, tmp_path):
    port = runner.measured(stub)
    systems = [bl.FullHistory(port, "stub", max_context=5000), bl.GrepAgent(port, "stub", max_steps=3)]
    run(stub, config, tmp_path, systems=systems)
    assert runner.load_run(tmp_path / "run")["fingerprint"]["system_params"] == {"B0": {"max_context": 5000}, "B2": {"max_steps": 3}}


def test_a_resume_with_the_same_settings_goes_on(stub, config, tmp_path):
    first_run(config, tmp_path)
    again = run(stub, config, tmp_path, systems=("B1",))
    assert again.skipped == 5 and again.complete


def test_a_resume_may_add_a_system_that_needs_another_model(stub, config, tmp_path):
    first_run(config, tmp_path)
    run(stub, config, tmp_path, systems=("B4",))
    fp = runner.load_run(tmp_path / "run")["fingerprint"]
    assert fp["models"]["stub.worker_small"] == "stub-worker_small" and fp["models"]["stub.answerer"] == "stub-answerer"


def changed_config(config, **edits):
    cfg = copy.deepcopy(config)
    for path, value in edits.items():
        node = cfg
        *head, last = path.split(".")
        for part in head:
            node = node[part]
        node[last] = value
    return cfg


@pytest.mark.parametrize(
    "edits, message",
    [
        ({"config_version": "2099-01-01.1"}, "the config version was '{version}', now '2099-01-01.1'"),
        ({"eval.token_budget": 4000}, "the token budget was 8000, now 4000"),
        ({"eval.lme_margin_points": 15}, "the bar lme_margin_points was 10, now 15"),
    ],
)
def test_a_resume_refuses_a_changed_config(stub, config, tmp_path, edits, message):
    first_run(config, tmp_path)
    with pytest.raises(ValueError, match="another run id") as err:
        run(stub, changed_config(config, **edits), tmp_path, systems=("B1",))
    assert message.format(version=config["config_version"]) in str(err.value)  # the shipped version, whatever it is now


def test_a_resume_refuses_a_changed_model(config, tmp_path):
    cfg = changed_config(config)
    cfg["models"]["anthropic"]["judge"] = "claude-sonnet-5-5"
    kw = {"answerer_family": "anthropic", "judge_family": "openai", "allow_same_family": False}
    run(StubModel(make_handler()), cfg, tmp_path, systems=("B1",), **kw)
    cfg["models"]["openai"]["judge"] = "gpt-6.1-terra"
    with pytest.raises(ValueError, match="the model for openai.judge was 'gpt-6.1-sol', now 'gpt-6.1-terra'"):
        run(StubModel(make_handler()), cfg, tmp_path, systems=("B1",), **kw)


def test_a_resume_refuses_changed_prompts(stub, config, tmp_path, monkeypatch):
    first_run(config, tmp_path)
    with monkeypatch.context() as m:
        m.setattr(bl, "ANSWER_SYSTEM", bl.ANSWER_SYSTEM + " Be brief.")
        with pytest.raises(ValueError, match="the answer prompts was"):
            run(stub, config, tmp_path, systems=("B1",))
    with monkeypatch.context() as m:
        m.setattr(jd, "QA_SYSTEM", jd.QA_SYSTEM + " Be strict.")
        with pytest.raises(ValueError, match="the judge prompt and rules was"):
            run(stub, config, tmp_path, systems=("B1",))
    assert run(stub, config, tmp_path, systems=("B1",)).skipped == 5  # nothing was written by the refused calls


def test_a_resume_refuses_changed_system_parameters(stub, config, tmp_path):
    port = runner.measured(stub)
    run(stub, config, tmp_path, systems=[bl.GrepAgent(port, "stub", max_steps=3)])
    with pytest.raises(ValueError, match=r"the system parameter B2 was \{'max_steps': 3\}, now \{'max_steps': 5\}"):
        run(stub, config, tmp_path, systems=[bl.GrepAgent(port, "stub", max_steps=5)])
    run(stub, config, tmp_path, systems=[bl.FullHistory(port, "stub", max_context=1000)])  # a system of its own may join
    with pytest.raises(ValueError, match="the system parameter B0"):
        run(stub, config, tmp_path, systems=[bl.FullHistory(port, "stub", max_context=2000)])


def test_a_resume_refuses_another_commit_or_a_dirty_tree(stub, config, tmp_path, monkeypatch):
    first_run(config, tmp_path)
    monkeypatch.setattr(runner, "git_state", lambda: ("deadbeef99", False))
    with pytest.raises(ValueError, match="the git commit was 'c0ffee0123', now 'deadbeef99'"):
        run(stub, config, tmp_path, systems=("B1",))
    monkeypatch.setattr(runner, "git_state", lambda: ("c0ffee0123", True))
    with pytest.raises(ValueError, match="the git work tree being dirty was False, now True"):
        run(stub, config, tmp_path, systems=("B1",))


def test_a_resume_names_every_change_at_once(stub, config, tmp_path, monkeypatch):
    first_run(config, tmp_path)
    monkeypatch.setattr(runner, "git_state", lambda: ("deadbeef99", True))
    with pytest.raises(ValueError) as err:
        run(stub, changed_config(config, **{"eval.token_budget": 1000}), tmp_path, systems=("B1",))
    text = str(err.value)
    assert "the token budget" in text and "the git commit" in text and "dirty" in text


def test_a_run_made_before_fingerprints_is_not_resumed(stub, config, tmp_path):
    first_run(config, tmp_path)
    run_json = runner.load_run(tmp_path / "run")
    del run_json["fingerprint"]
    runner.write_json(tmp_path / "run" / runner.RUN_FILE, run_json)
    with pytest.raises(ValueError, match="did not record what it was made with"):
        run(stub, config, tmp_path, systems=("B1",))


def test_git_state_reads_the_commit_and_whether_the_tree_is_dirty(monkeypatch):
    monkeypatch.undo()  # the autouse fixture replaced it
    import subprocess

    outputs = {"rev-parse": "abc123\n", "status": " M file.py\n"}

    def fake(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 0, stdout=outputs[cmd[3]], stderr="")

    monkeypatch.setattr(subprocess, "run", fake)
    assert runner.git_state() == ("abc123", True)
    outputs["status"] = ""
    assert runner.git_state() == ("abc123", False)

    def broken(cmd, **kw):
        raise FileNotFoundError("git")

    monkeypatch.setattr(subprocess, "run", broken)
    assert runner.git_state() == ("unknown", True)


# --- held-out discipline ------------------------------------------------------------------------------------


TEST_ITEMS = [replace(i, split="test") for i in ITEMS]


def judge_check_file(root: Path, name="chk", **edits) -> Path:
    check = {
        "judge_family": "stub", "judge_model": "stub-judge", "prompt_hash": jd.prompt_hash(), "passed": True,
        "checked_at": "2026-10-28T10:00:00+00:00", **edits,
    }
    runner.write_json(root / name / runner.JUDGE_CHECK_FILE, check)
    return root / name


def held_out_run(stub, config, tmp_path, items=None, **kw):
    kw = {
        "answerer_family": "stub", "judge_family": "stub", "allow_same_family": True, "run_id": "h1", "held_out": True,
        "runs_root": tmp_path / "runs", "held_out_ledger": tmp_path / "held-out-ledger.jsonl", **kw,
    }
    return runner.run_qa(items or TEST_ITEMS, kw.pop("systems", ["B1"]), port=stub, config=config, out_dir=tmp_path / "runs" / "h1", **kw)


def test_a_run_on_the_test_split_needs_held_out(stub, config, tmp_path):
    with pytest.raises(ValueError, match="held-out run"):
        runner.run_qa(
            TEST_ITEMS, ["B1"], answerer_family="stub", judge_family="stub", allow_same_family=True, port=stub,
            config=config, run_id="t", out_dir=tmp_path / "run",
        )
    with pytest.raises(ValueError, match="held-out run"):
        runner.run_qa(
            ITEMS, ["B1"], answerer_family="stub", judge_family="stub", allow_same_family=True, port=stub,
            config=config, run_id="t", out_dir=tmp_path / "run", split="test",
        )
    assert stub.calls == [] and not (tmp_path / "run").exists()


def test_a_held_out_run_refuses_a_dirty_work_tree(stub, config, tmp_path, monkeypatch):
    judge_check_file(tmp_path / "runs")
    monkeypatch.setattr(runner, "git_state", lambda: ("c0ffee0123", True))
    with pytest.raises(ValueError, match="clean git work tree"):
        held_out_run(stub, config, tmp_path)
    assert stub.calls == [] and not (tmp_path / "held-out-ledger.jsonl").exists()


def test_a_held_out_run_needs_a_passing_judge_check_for_its_judge(stub, config, tmp_path):
    with pytest.raises(ValueError, match="no passing judge check for the stub judge stub-judge"):
        held_out_run(stub, config, tmp_path)
    for edits in ({"passed": False}, {"judge_model": "other"}, {"prompt_hash": "0" * 16}, {"judge_family": "openai"}):
        judge_check_file(tmp_path / "runs", **edits)
        with pytest.raises(ValueError, match="no passing judge check"):
            held_out_run(stub, config, tmp_path)
    assert stub.calls == [] and not (tmp_path / "held-out-ledger.jsonl").exists()
    assert not (tmp_path / "runs" / "h1").exists()


def test_a_held_out_run_records_itself_and_keeps_the_check(stub, config, tmp_path):
    judge_check_file(tmp_path / "runs")
    summary = held_out_run(stub, config, tmp_path)
    assert summary.complete and summary.judged == 5
    out = tmp_path / "runs" / "h1"
    run_json = runner.load_run(out)
    fp = run_json["fingerprint"]
    assert run_json["held_out"] is True and run_json["split"] == "test"
    assert (fp["git_commit"], fp["git_dirty"]) == ("c0ffee0123", False)
    assert fp["answer_prompt_hash"] and fp["judge_prompt_hash"] == jd.prompt_hash() and fp["bars"]["lme_margin_points"] == 10
    assert json.loads((out / runner.JUDGE_CHECK_FILE).read_text())["prompt_hash"] == jd.prompt_hash()  # kept with the run
    (entry,) = runner.read_jsonl(tmp_path / "held-out-ledger.jsonl")
    assert entry["run_id"] == "h1" and entry["split"] == "test" and entry["systems"] == ["B1"] and entry["n_items"] == 5
    assert entry["git_commit"] == "c0ffee0123" and entry["git_dirty"] is False and entry["judge_model"] == "stub-judge"
    assert entry["judge_prompt_hash"] == jd.prompt_hash() and entry["bars"] == fp["bars"]
    assert "question" not in json.dumps(entry) and ITEMS[0].id not in json.dumps(entry)
    held_out_run(stub, config, tmp_path)  # a resume is a look at the data too
    assert len(runner.read_jsonl(tmp_path / "held-out-ledger.jsonl")) == 2


def test_the_newest_passing_check_is_the_one_kept(stub, config, tmp_path):
    judge_check_file(tmp_path / "runs", "old", checked_at="2026-10-01T00:00:00+00:00", note="old")
    judge_check_file(tmp_path / "runs", "new", checked_at="2026-10-20T00:00:00+00:00", note="new")
    held_out_run(stub, config, tmp_path)
    assert json.loads((tmp_path / "runs" / "h1" / runner.JUDGE_CHECK_FILE).read_text())["note"] == "new"


def test_held_out_does_not_look_in_other_folders_than_runs(stub, config, tmp_path):
    judge_check_file(tmp_path / "elsewhere")
    with pytest.raises(ValueError, match="no passing judge check"):
        held_out_run(stub, config, tmp_path)


def test_b0_runs_on_the_reference_subset_on_the_test_split(stub, config, tmp_path, monkeypatch):
    judge_check_file(tmp_path / "runs")
    seen = []

    def b0_subset(items, cfg):
        seen.append((list(items), cfg))
        return [items[0], items[2]]

    monkeypatch.setattr(lme, "b0_subset", b0_subset, raising=False)
    summary = held_out_run(stub, config, tmp_path, systems=["B0", "B1"])
    assert summary.complete and (summary.answered, summary.judged) == (7, 7)  # 2 of B0, 5 of B1
    (items, cfg), = seen
    assert [i.id for i in items] == [i.id for i in TEST_ITEMS] and cfg == config["eval"]["longmemeval"]
    done = {(r["system"], r["item_id"]) for r in rows_at(tmp_path / "runs" / "h1", runner.JUDGEMENTS_FILE)}
    assert {i for s, i in done if s == "B0"} == {TEST_ITEMS[0].id, TEST_ITEMS[2].id}
    assert {i for s, i in done if s == "B1"} == {i.id for i in TEST_ITEMS}
    assert runner.load_run(tmp_path / "runs" / "h1")["subsets"] == {"B0": [TEST_ITEMS[0].id, TEST_ITEMS[2].id]}
    again = held_out_run(stub, config, tmp_path, systems=["B0", "B1"])
    assert again.skipped == 7 and again.answered == 0


def test_b0_runs_on_every_dev_item(stub, config, tmp_path, monkeypatch):
    monkeypatch.setattr(lme, "b0_subset", lambda *a: pytest.fail("the subset is for the test split"), raising=False)
    summary = run(stub, config, tmp_path, systems=("B0",))
    assert summary.judged == 5 and runner.load_run(tmp_path / "run")["subsets"] == {}


def rows_at(path, name):
    return runner.read_jsonl(path / name)


# --- batched judging ------------------------------------------------------------------------------------------


def with_batch_size(config, n):
    cfg = copy.deepcopy(config)
    cfg["eval"]["judge_batch_size"] = n
    return cfg


def batch_calls(stub):
    """For each batched judge call, the item ids it graded, in the order of its pairs."""
    out = []
    for call in stub.calls:
        if call.purpose == "judge.qa.batch":
            questions = re.findall(r"<question>\n(.*?)\n</question>", call.messages[-1]["content"], re.S)
            out.append([GOLD[q].id for q in questions])
    return out


def judge_purposes(stub):
    return [c.purpose for c in stub.calls if c.purpose.startswith("judge.qa")]


def test_answers_are_judged_in_batches_that_mix_items_and_never_repeat_one(config, tmp_path):
    stub = StubModel(make_handler())
    summary = run(stub, with_batch_size(config, 3), tmp_path, systems=("B1", "B3"), max_workers=1)
    assert (summary.answered, summary.judged, summary.complete) == (10, 10, True)
    batches = batch_calls(stub)
    assert sum(map(len, batches)) + judge_purposes(stub).count("judge.qa") == 10
    assert all(len(b) <= 3 and len(set(b)) == len(b) for b in batches)  # never two answers to one item side by side
    assert max(map(len, batches)) == 3 and len(judge_purposes(stub)) < 10  # fewer calls than one a pair
    assert len({i for b in batches for i in b}) > 3  # a batch mixes items and the run goes on through the items
    assert {(j.system, j.item_id) for j in runner.load_judgements(tmp_path / "run")} == {(s, i.id) for s in ("B1", "B3") for i in ITEMS}
    assert all(c.cache is False and c.allow_fallback is False for c in stub.calls)


def test_a_batch_size_of_one_judges_pair_by_pair(config, tmp_path):
    stub = StubModel(make_handler())
    summary = run(stub, with_batch_size(config, 1), tmp_path, systems=("B1",), max_workers=1)
    assert summary.judged == 5 and judge_purposes(stub) == ["judge.qa"] * 5


def test_the_default_batch_size_is_eight(config, tmp_path):
    cfg = copy.deepcopy(config)
    cfg["eval"].pop("judge_batch_size", None)
    stub = StubModel(make_handler())
    run(stub, cfg, tmp_path, systems=("B1", "B3", "B4"), max_workers=1)
    assert max(map(len, batch_calls(stub))) == 5  # five items: the most distinct items one batch can hold
    assert runner.load_run(tmp_path / "run")["fingerprint"]["judge_batch_size"] == 8


def test_the_batches_do_not_depend_on_which_thread_finishes_first(config, tmp_path):
    cfg = with_batch_size(config, 3)
    made = []
    for workers, name in ((1, "one"), (4, "four")):
        stub = StubModel(make_handler())
        runner.run_qa(
            ITEMS, ["B1", "B3", "none"], answerer_family="stub", judge_family="stub", allow_same_family=True, port=stub,
            config=cfg, run_id="r", out_dir=tmp_path / name, max_workers=workers,
        )
        made.append(sorted(batch_calls(stub)))
    assert made[0] == made[1]


def test_a_forbidden_term_is_judged_by_code_and_never_sent_to_the_model(config, tmp_path):
    items = [replace(i, meta={"forbidden_terms": ["something else"]}) if i.id == WRONG_ID else i for i in ITEMS]
    stub = StubModel(make_handler())
    summary = runner.run_qa(
        items, ["B1"], answerer_family="stub", judge_family="stub", allow_same_family=True, port=stub,
        config=with_batch_size(config, 8), run_id="r", out_dir=tmp_path / "run", max_workers=1,
    )
    assert summary.judged == 5
    (batch,) = batch_calls(stub)
    assert WRONG_ID not in batch and len(batch) == 4
    by_item = {j.item_id: j for j in runner.load_judgements(tmp_path / "run")}
    assert (by_item[WRONG_ID].outcome, by_item[WRONG_ID].judge_family) == ("hallucinated", "code")


def test_a_failed_batch_is_recorded_for_each_pair_and_judged_again_on_resume(config, tmp_path):
    cfg = with_batch_size(config, 8)

    def handler(req):
        if req.purpose == "judge.qa.batch":
            return {"nothing": []}
        return make_handler()(req)

    first = run(StubModel(handler), cfg, tmp_path, systems=("B1",), max_workers=1)
    assert first.judged == 0 and len(first.errors) == 5 and not first.complete
    assert all("no verdicts" in e["error"] for e in first.errors)
    assert rows(tmp_path, runner.JUDGEMENTS_FILE) == []
    stub = StubModel(make_handler())
    healed = run(stub, cfg, tmp_path, systems=("B1",), max_workers=1)
    assert (healed.answered, healed.judged, healed.errors) == (0, 5, []) and len(batch_calls(stub)) == 1


@pytest.mark.parametrize("error", [BudgetExceeded, NoCredentials, ModelUnavailable, PlanLimitReached])
def test_a_stop_while_answering_still_judges_what_was_answered(config, tmp_path, error):
    answers = []

    def handler(req):
        if req.purpose == "lme.answer":
            answers.append(req)
            if len(answers) == 4:
                raise error("stop")
        return make_handler()(req)

    stub = StubModel(handler)
    summary = run(stub, with_batch_size(config, 8), tmp_path, systems=("B1",), max_workers=1)
    assert summary.stopped and error.__name__ in summary.stopped
    assert (summary.answered, summary.judged) == (3, 3)  # the three answers were judged, in one batch, though the run stopped
    assert len(rows(tmp_path, runner.JUDGEMENTS_FILE)) == 3 and len(batch_calls(stub)) == 1
    resumed = run(StubModel(make_handler()), with_batch_size(config, 8), tmp_path, systems=("B1",), max_workers=1)
    assert (resumed.answered, resumed.judged, resumed.skipped, resumed.errors) == (2, 2, 3, [])


def test_a_stop_in_the_judge_keeps_the_answers_and_a_resume_judges_them_in_batches(config, tmp_path):
    cfg = with_batch_size(config, 2)

    def handler(req):
        if req.purpose == "judge.qa.batch":
            raise BudgetExceeded("the plan is used")
        return make_handler()(req)

    stub = StubModel(handler)
    summary = run(stub, cfg, tmp_path, systems=("B1", "B3"), max_workers=1)
    assert "BudgetExceeded" in summary.stopped and summary.judged == 0
    assert judge_purposes(stub) == ["judge.qa.batch"]  # nothing more was tried against a judge that cannot answer
    saved = len(runner.load_predictions(tmp_path / "run"))
    assert saved == summary.answered and saved >= 3 and rows(tmp_path, runner.JUDGEMENTS_FILE) == []
    fresh = StubModel(make_handler())
    resumed = run(fresh, cfg, tmp_path, systems=("B1", "B3"), max_workers=1)
    assert resumed.complete and resumed.judged == 10 and resumed.answered == 10 - saved
    assert len(runner.load_judgements(tmp_path / "run")) == 10


def test_a_resume_judges_answered_pairs_in_batches_of_distinct_items(config, tmp_path):
    cfg = with_batch_size(config, 4)
    run(StubModel(make_handler()), cfg, tmp_path, systems=("B1", "B3"), max_workers=1)
    (tmp_path / "run" / runner.JUDGEMENTS_FILE).write_text("")  # every judgement lost, every answer kept
    stub = StubModel(make_handler())
    summary = run(stub, cfg, tmp_path, systems=("B1", "B3"), max_workers=1)
    assert (summary.answered, summary.judged, summary.skipped) == (0, 10, 0)
    assert not [c for c in stub.calls if c.purpose != "judge.qa.batch" and c.purpose != "judge.qa"]  # no answering again
    batches = batch_calls(stub)
    assert len(batches) == 2 and all(len(set(b)) == len(b) <= 4 for b in batches)
    assert judge_purposes(stub).count("judge.qa") == 2  # the last item's two answers cannot share a batch
    assert sum(map(len, batches)) + judge_purposes(stub).count("judge.qa") == 10


def test_the_batch_size_is_part_of_what_a_run_was_made_with(config, tmp_path):
    run(StubModel(make_handler()), with_batch_size(config, 3), tmp_path, systems=("B1",))
    fp = runner.load_run(tmp_path / "run")["fingerprint"]
    assert fp["judge_batch_size"] == 3 and fp["judge_prompt_hash"] == jd.prompt_hash(3) != jd.prompt_hash(8)
    with pytest.raises(ValueError, match="the judge batch size was 3, now 5"):
        run(StubModel(make_handler()), with_batch_size(config, 5), tmp_path, systems=("B1",))
    assert run(StubModel(make_handler()), with_batch_size(config, 3), tmp_path, systems=("B1",)).skipped == 5


def test_a_held_out_run_needs_a_judge_check_made_at_its_batch_size(stub, config, tmp_path):
    judge_check_file(tmp_path / "runs", prompt_hash=jd.prompt_hash(8))
    with pytest.raises(ValueError, match="no passing judge check"):
        held_out_run(stub, with_batch_size(config, 4), tmp_path)
    assert held_out_run(stub, with_batch_size(config, 8), tmp_path).complete


# --- the judge check, batched ---------------------------------------------------------------------------------------


def test_the_judge_check_judges_its_probe_answers_in_mixed_batches(config, tmp_path):
    cfg = with_batch_size(config, 4)
    stub = StubModel(probe_handler(True))
    result = runner.run_judge_check(CLONES, stub, "openai", "anthropic", cfg, tmp_path)
    judge_calls = [c for c in stub.calls if c.purpose.startswith("judge.qa")]
    assert result["meta"]["n"] > 100
    assert {c.purpose for c in judge_calls} == {"judge.qa.batch"} and result["passed"] is True
    sizes, kinds = [], []
    for call in judge_calls:
        text = call.messages[-1]["content"]
        questions = re.findall(r"<question>\n(.*?)\n</question>", text, re.S)
        assert len(set(questions)) == len(questions) <= 4  # never two answers to one item in a batch
        sizes.append(len(questions))
        kinds.append(len(set(re.findall(r"<response>\n(.*?)\n</response>", text, re.S))))
    assert sum(sizes) == result["meta"]["n"] and sizes.count(4) >= len(sizes) - 4
    assert max(kinds) > 1


def test_the_judge_check_stores_the_batch_size_and_the_hash_that_covers_it(config, tmp_path):
    result = runner.run_judge_check(CLONES, StubModel(probe_handler(True)), "openai", "anthropic", with_batch_size(config, 6), tmp_path)
    saved = json.loads((tmp_path / runner.JUDGE_CHECK_FILE).read_text())
    assert saved["judge_batch_size"] == result["judge_batch_size"] == 6
    assert saved["prompt_hash"] == jd.prompt_hash(6) != jd.prompt_hash(8)


def test_the_judge_check_shuffles_with_the_config_seed(config, tmp_path):
    def order(seed):
        cfg = with_batch_size(config, 4)
        cfg["eval"]["seed"] = seed
        stub = StubModel(probe_handler(True))
        runner.run_judge_check(CLONES, stub, "openai", "anthropic", cfg, tmp_path / str(seed))
        return [c.messages[-1]["content"] for c in stub.calls if c.purpose == "judge.qa.batch"]

    assert order(1) == order(1) != order(2)


def test_a_judge_check_at_one_batch_size_does_not_vouch_for_a_run_at_another(config, tmp_path):
    runner.run_judge_check(CLONES, StubModel(probe_handler(True)), "openai", "anthropic", with_batch_size(config, 8), tmp_path / "chk")
    found = runner.find_judge_check([tmp_path / "chk"], "openai", config["models"]["openai"]["judge"], jd.prompt_hash(8))
    assert found is not None
    assert runner.find_judge_check([tmp_path / "chk"], "openai", config["models"]["openai"]["judge"], jd.prompt_hash(1)) is None
