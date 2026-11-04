"""Report tests: runs are written by hand (fake judgements), so each rule is checked on known numbers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from northstar_agent_memory.eval import judge as jd
from northstar_agent_memory.eval import report, runner
from northstar_agent_memory.eval.metrics import Interval, PairedDifference, paired_difference
from northstar_agent_memory.eval.types import Judgement
from northstar_agent_memory.models.budget import CostLedger
from northstar_agent_memory.models.port import ModelResult, Usage

ANSWERER = "stub-answerer"
JUDGE = "stub-judge"
TYPES = ("knowledge-update", "temporal-reasoning")


def make_run(
    tmp_path: Path,
    verdicts: dict[str, str],
    n: int = 10,
    subsets: dict[str, list[str]] | None = None,
    errors: dict[str, list[str]] | None = None,
    served: dict[str, str] | None = None,
    cost: float = 0.0,
    judge_model: str = JUDGE,
    systems: list[str] | None = None,
) -> Path:
    """A run of `n` items i00.. . `verdicts` maps a system to a string of c (correct), w (wrong) and - (no judgement),
    one character per item in order; a string shorter than the items leaves the rest unjudged."""
    out = tmp_path / "run"
    ids = [f"i{k:02d}" for k in range(n)]
    systems = systems or list(verdicts)
    runner.write_json(
        out / runner.RUN_FILE,
        {
            "run_id": "r1", "dataset": "longmemeval_s", "split": "dev", "answerer_family": "stub", "judge_family": "stub",
            "allow_same_family": True, "config_version": "v", "token_budget": 8000,
            "models": {"stub.answerer": ANSWERER, "stub.judge": JUDGE}, "held_out": False,
            "fingerprint": {"config_version": "v", "judge_prompt_hash": jd.prompt_hash(), "judge_batch_size": jd.judge_batch_size(), "git_commit": "c0ffee", "git_dirty": False, "bars": {"lme_margin_points": 10}},
            "systems": systems, "subsets": subsets or {},
            "items": [{"id": i, "question_type": TYPES[k % 2], "abstention": k % 5 == 4, "split": "dev"} for k, i in enumerate(ids)],
            "created_at": "t", "updated_at": "t",
        },
    )
    judgements, predictions = [], []
    for system, marks in verdicts.items():
        for item_id, mark in zip(ids, marks):
            if mark in "cw":
                judgements.append(
                    {"item_id": item_id, "system": system, "outcome": "correct" if mark == "c" else "hallucinated", "abstained": False,
                     "judge_family": "stub", "judge_model": judge_model, "rationale": "r", "judge_cost_usd": cost, "judge_latency_s": 0.1}
                )
            failed = item_id in (errors or {}).get(system, [])
            if mark != "-" or failed:
                predictions.append(
                    {"item_id": item_id, "system": system, "answer": "" if failed else "a", "cited_message_ids": [], "context_tokens": 100,
                     "usage": {"input_tokens": 100, "output_tokens": 10}, "cost_usd": cost, "latency_s": 1.0, "calls": 1,
                     "meta": {"family": "stub", "model": (served or {}).get(system, ANSWERER), **({"error": "boom"} if failed else {})}}
                )
    (out / runner.JUDGEMENTS_FILE).write_text("".join(json.dumps(r) + "\n" for r in judgements))
    (out / runner.PREDICTIONS_FILE).write_text("".join(json.dumps(r) + "\n" for r in predictions))
    return out


def pair(summary: dict, a: str, b: str, needs=False) -> dict:
    pairs = summary["needs_memory"]["pairs"] if needs else summary["pairs"]
    return next(p for p in pairs if (p["a"], p["b"]) == (a, b))


# --- deciding a bar ---------------------------------------------------------------------------------------


def diff(estimate: float, low: float, high: float | None = None) -> dict:
    return {"estimate": estimate, "low": low, "high": high if high is not None else estimate + 0.1}


@pytest.mark.parametrize(
    "estimate, low, margin, expected",
    [
        (0.12, 0.01, 10, "pass"),
        (0.10, 0.02, 10, "pass"),  # exactly at the bar
        (0.12, 0.00, 10, "undecided"),  # reaches the bar, but the interval touches zero
        (0.12, -0.05, 10, "undecided"),
        (0.099, 0.02, 10, "fail"),  # the difference is short of the bar
        (-0.05, -0.2, 10, "fail"),
        (0.10, 0.0001, 10, "pass"),
        (0.05, 0.01, 5, "pass"),
    ],
)
def test_at_least_n_points_above(estimate, low, margin, expected):
    assert report.decide(diff(estimate, low), report.ABOVE, margin) == expected


@pytest.mark.parametrize(
    "estimate, low, expected",
    [
        (0.0, -0.05, "pass"),
        (0.04, -0.09, "pass"),
        (0.0, -0.10, "undecided"),  # the lower bound must be above -10 points, not at it
        (0.03, -0.25, "undecided"),
        (-0.01, -0.05, "fail"),  # below zero
        (-0.20, -0.40, "fail"),
    ],
)
def test_at_least_as_good_as(estimate, low, expected):
    assert report.decide(diff(estimate, low), report.AS_GOOD) == expected


def test_decide_takes_an_interval_a_paired_difference_or_a_dict():
    iv = Interval(0.2, 0.05, 0.35, 40)
    assert report.decide(iv, report.ABOVE, 10) == "pass"
    assert report.decide(PairedDifference("a", "b", 40, 0.7, 0.5, iv), report.ABOVE, 10) == "pass"
    assert report.decide({"estimate": 0.2, "low": 0.05, "high": 0.35}, report.ABOVE, 10) == "pass"
    with pytest.raises(ValueError, match="unknown bar kind"):
        report.decide(iv, "better")


def fake_judgements(system: str, marks: str) -> list[Judgement]:
    return [Judgement(f"q{k}", system, "correct" if m == "c" else "hallucinated", False, "code", "") for k, m in enumerate(marks)]


def test_decide_on_fake_judgements():
    # A is right on 36 of 40 and B on 20: a large paired difference, far from zero
    j = fake_judgements("A", "c" * 36 + "w" * 4) + fake_judgements("B", "c" * 20 + "w" * 20)
    d = paired_difference(j, "A", "B", seed=1)
    assert d.difference.estimate == pytest.approx(0.4) and d.difference.low > 0.2
    assert report.decide(d, report.ABOVE, 10) == "pass" and report.decide(d, report.AS_GOOD) == "pass"
    # the other way round: B is far behind
    d = paired_difference(j, "B", "A", seed=1)
    assert report.decide(d, report.ABOVE, 10) == "fail" and report.decide(d, report.AS_GOOD) == "fail"
    # ten items where A is one question ahead: 10 points, but the interval reaches below zero
    j = fake_judgements("A", "c" * 6 + "w" * 4) + fake_judgements("B", "c" * 5 + "w" * 5)
    d = paired_difference(j, "A", "B", seed=1)
    assert d.difference.estimate == pytest.approx(0.1) and d.difference.low <= 0
    assert report.decide(d, report.ABOVE, 10) == "undecided"
    # the same two systems are as good as each other when they agree item by item
    j = fake_judgements("A", "c" * 5 + "w" * 5) + fake_judgements("B", "c" * 5 + "w" * 5)
    d = paired_difference(j, "A", "B", seed=1)
    assert d.difference.estimate == 0 and report.decide(d, report.AS_GOOD) == "pass"
    assert report.decide(d, report.ABOVE, 10) == "fail"


# --- comparisons on the items every system finished ----------------------------------------------------------


def test_every_comparison_uses_only_the_items_all_compared_systems_judged(tmp_path):
    # X judged all 10 items; Y only the first 6, and Z only the first 4
    out = make_run(tmp_path, {"X": "cccccwwwww", "Y": "ccwwww", "Z": "cwcw"})
    s = report.summarize(out)
    assert s["n_common"] == 4
    assert {n: v["compared"]["n"] for n, v in s["systems"].items()} == {"X": 4, "Y": 4, "Z": 4}
    assert s["systems"]["X"]["compared"]["accuracy"]["estimate"] == 1.0  # "cccc", not "cccccwwwww" (50%)
    assert s["systems"]["X"]["accuracy"]["estimate"] == 0.5  # on its own items, as before
    assert s["systems"]["X"]["compared"]["accuracy"]["n"] == 4
    # each pair uses the items its two systems share
    assert pair(s, "X", "Y")["n"] == 6 and pair(s, "X", "Z")["n"] == 4 and pair(s, "Y", "Z")["n"] == 4
    xy = pair(s, "X", "Y")  # on the first six items X is right on 5 and Y on 2
    assert xy["accuracy_a"] == pytest.approx(5 / 6) and xy["accuracy_b"] == pytest.approx(2 / 6)
    assert xy["difference"]["n"] == 6 and xy["difference"]["estimate"] == pytest.approx(0.5)
    assert xy["difference"]["low"] <= xy["difference"]["estimate"] <= xy["difference"]["high"]


def test_the_pairs_cover_every_pair_of_systems_with_a_bootstrap_interval(tmp_path):
    out = make_run(tmp_path, {"A": "c" * 10, "B": "cwcwcwcwcw", "C": "w" * 10})
    s = report.summarize(out)
    assert [(p["a"], p["b"]) for p in s["pairs"]] == [("A", "B"), ("A", "C"), ("B", "C")]
    ab = pair(s, "A", "B")
    assert ab["accuracy_a"] == 1.0 and ab["accuracy_b"] == 0.5 and ab["difference"]["estimate"] == pytest.approx(0.5)
    assert 0 < ab["difference"]["low"] < 0.5 < ab["difference"]["high"] <= 1.0
    assert ab["above"] == "pass" and ab["as_good"] == "pass"
    ac = pair(s, "A", "C")
    assert ac["difference"]["estimate"] == 1.0 and ac["above"] == "pass"
    bc = pair(s, "B", "C")
    assert bc["difference"]["estimate"] == pytest.approx(0.5)


def test_a_pair_without_common_items_is_undecided(tmp_path):
    out = make_run(tmp_path, {"A": "cccccc----", "B": "------cccc"})
    s = report.summarize(out)
    p = pair(s, "A", "B")
    assert p["n"] == 0 and p["difference"] is None and p["above"] == p["as_good"] == "undecided"
    assert s["n_common"] == 0
    assert "| A vs B | 0 |" in report.to_markdown(s)


def test_the_markdown_shows_each_pair_with_its_decision(tmp_path):
    out = make_run(tmp_path, {"B1": "cwcwcwcwcw", "B3": "c" * 10})
    md = report.to_markdown(report.summarize(out))
    assert "## Paired differences on all items" in md
    assert "| B1 vs B3 | 10 |" in md
    row = next(line for line in md.splitlines() if line.startswith("| B1 vs B3"))
    assert "-50.0" in row and "fail" in row  # B1 is 50 points behind B3


# --- an incomplete run -------------------------------------------------------------------------------------


def test_a_complete_run_has_no_banner(tmp_path):
    s = report.summarize(make_run(tmp_path, {"X": "c" * 10, "Y": "w" * 10}))
    assert s["complete"] is True and s["incomplete"] == []
    assert "INCOMPLETE" not in report.to_markdown(s)


def test_a_system_with_fewer_judged_items_than_items_makes_the_run_incomplete(tmp_path):
    s = report.summarize(make_run(tmp_path, {"X": "c" * 10, "Y": "c" * 7}))
    assert s["complete"] is False and s["incomplete"] == ["Y"]
    assert s["systems"]["Y"]["n_judged"] == 7 and s["systems"]["X"]["complete"] is True
    md = report.to_markdown(s)
    assert md.count("INCOMPLETE") == 1 and "Y (7/10 judged)" in md and "X (" not in md.split("INCOMPLETE")[1].split(".**")[0]
    assert "only the 7 items all compared systems finished" in md


def test_an_error_makes_the_run_incomplete(tmp_path):
    s = report.summarize(make_run(tmp_path, {"X": "c" * 10, "Y": "ccc-cccccc"}, errors={"Y": ["i03"]}))
    assert s["incomplete"] == ["Y"] and s["systems"]["Y"]["n_errors"] == 1 and s["systems"]["Y"]["n_judged"] == 9
    assert "Y (9/10 judged, 1 failed)" in report.to_markdown(s)


def test_a_system_with_no_judgement_at_all_does_not_empty_the_comparison(tmp_path):
    s = report.summarize(make_run(tmp_path, {"X": "c" * 10, "Y": "w" * 10, "Z": "-" * 10}, systems=["X", "Y", "Z"]))
    assert s["incomplete"] == ["Z"] and s["n_common"] == 10
    assert all("Z" not in (p["a"], p["b"]) for p in s["pairs"])


# --- a system that runs on part of the items by design ------------------------------------------------------


def test_a_system_on_a_declared_subset_is_complete_and_compared_on_its_items(tmp_path):
    subset = ["i00", "i01", "i02", "i03"]
    out = make_run(tmp_path, {"B0": "cccc", "B1": "ccwwwwwwww"}, subsets={"B0": subset})
    s = report.summarize(out)
    assert s["complete"] is True and s["subset_systems"] == ["B0"]
    assert (s["systems"]["B0"]["n_items"], s["systems"]["B0"]["n_judged"]) == (4, 4)
    assert (s["systems"]["B1"]["n_items"], s["systems"]["B1"]["n_judged"]) == (10, 10)
    assert pair(s, "B0", "B1")["n"] == 4
    assert pair(s, "B0", "B1")["accuracy_b"] == pytest.approx(0.5)  # B1 on the same four items
    assert s["systems"]["B1"]["compared"]["n"] == 10  # the full-coverage system sets the comparison set
    assert s["systems"]["B0"]["compared"]["n"] == 4
    md = report.to_markdown(s)
    assert "INCOMPLETE" not in md and "ran on a subset of the items by design" in md


def test_a_system_short_of_its_subset_is_incomplete(tmp_path):
    out = make_run(tmp_path, {"B0": "ccc", "B1": "c" * 10}, subsets={"B0": ["i00", "i01", "i02", "i03"]})
    assert report.summarize(out)["incomplete"] == ["B0"]


# --- the questions that need memory ------------------------------------------------------------------------


def test_each_item_is_classed_by_what_the_closed_book_run_and_b3_did():
    correct = {"none": {"a": 0.0, "b": 0.0, "c": 1.0, "d": 1.0}, "B3": {"a": 1.0, "b": 0.0, "c": 1.0, "d": 0.0}}
    assert report.classify_needed(correct) == {
        "a": "needed",  # none wrong, B3 right
        "b": "unsolved",  # both wrong
        "c": "answerable_without_memory",  # none right
        "d": "answerable_without_memory",  # none right (B3 missed it): it does not need memory
    }


def test_the_headline_is_every_systems_accuracy_over_the_questions_that_need_memory(tmp_path):
    #            items: 0 1 2 3 4 5 6 7 8 9
    marks = {
        "none": "ccwwwwwwww",  # right on 0 and 1: answerable without memory
        "B3":   "cccccwwwww",  # right on 0-4; wrong on 5-9
        "B1":   "wcwcwwwwcw",
    }
    s = report.summarize(make_run(tmp_path, marks))
    needs = s["needs_memory"]
    # needed: none wrong and B3 right: items 2, 3, 4. Without memory: 0, 1. Unsolved: 5-9.
    assert needs["n"] == 10 and needs["counts"] == {"needed": 3, "answerable_without_memory": 2, "unsolved": 5}
    assert needs["accuracy"]["none"]["estimate"] == 0.0 and needs["accuracy"]["none"]["n"] == 3
    assert needs["accuracy"]["B3"]["estimate"] == 1.0
    assert needs["accuracy"]["B1"]["estimate"] == pytest.approx(1 / 3)  # right on item 3 only
    assert pair(s, "B3", "B1", needs=True)["n"] == 3  # the pairs follow the run's order of systems
    assert pair(s, "none", "B3", needs=True)["difference"]["estimate"] == -1.0
    md = report.to_markdown(s)
    assert md.index("## Questions that need memory (the headline)") < md.index("## Accuracy on the")
    assert "3 need memory (none wrong, B3 right), 2 are answerable without memory (none right), 5 are unsolved" in md
    assert "| B1 | 3 | 33.3%" in md


def test_the_needs_memory_view_needs_both_none_and_b3(tmp_path):
    s = report.summarize(make_run(tmp_path, {"B3": "c" * 10, "B1": "w" * 10}))
    assert s["needs_memory"] is None
    md = report.to_markdown(s)
    assert "both none (closed book) and B3" in md and "## Questions that need memory" not in md
    s = report.summarize(make_run(tmp_path, {"B1": "c" * 10, "B4": "w" * 10}))
    assert s["needs_memory"] is None and "both none" not in report.to_markdown(s)


def test_no_question_needs_memory_when_the_closed_book_run_is_always_right(tmp_path):
    s = report.summarize(make_run(tmp_path, {"none": "c" * 10, "B3": "c" * 10}))
    assert s["needs_memory"]["counts"]["needed"] == 0
    assert s["needs_memory"]["accuracy"]["none"] is None and s["needs_memory"]["pairs"][0]["n"] == 0


def test_the_needs_memory_view_counts_only_items_both_systems_judged(tmp_path):
    s = report.summarize(make_run(tmp_path, {"none": "wwww", "B3": "cc"}))
    assert s["needs_memory"]["n"] == 2 and s["needs_memory"]["counts"]["needed"] == 2


# --- the models that answered, and what the run cost ------------------------------------------------------


def test_a_model_that_is_not_the_one_asked_for_is_a_warning(tmp_path):
    clean = report.summarize(make_run(tmp_path, {"B1": "c" * 10}))
    assert clean["warnings"] == [] and clean["systems"]["B1"]["served_models"] == [ANSWERER]
    s = report.summarize(make_run(tmp_path, {"B1": "c" * 10, "B3": "c" * 10}, served={"B3": "claude-sonnet-5-5"}))
    assert any("B3 was answered by claude-sonnet-5-5, not the requested stub-answerer" in w for w in s["warnings"])
    assert s["systems"]["B3"]["served_models"] == ["claude-sonnet-5-5"]
    md = report.to_markdown(s)
    assert "**Warning:**" in md and "| B3 | claude-sonnet-5-5 |" in md


def test_a_judge_that_is_not_the_one_asked_for_is_a_warning(tmp_path):
    s = report.summarize(make_run(tmp_path, {"B1": "c" * 10}, judge_model="some-fallback"))
    assert any("judgements were made by some-fallback, not the requested stub-judge" in w for w in s["warnings"])


def test_cost_includes_the_items_that_failed(tmp_path):
    out = make_run(tmp_path, {"X": "ccc-ccccc-"}, cost=0.5, errors={"X": ["i03", "i09"]})
    s = report.summarize(out)["systems"]["X"]
    assert s["n_errors"] == 2 and s["n_judged"] == 8 and s["calls"] == 8  # tokens and calls of the answered items
    assert s["cost_usd"]["failed"] == pytest.approx(1.0)
    assert s["cost_usd"]["answer"] == pytest.approx(5.0)  # 10 predictions, failed ones included
    assert s["cost_usd"]["judge"] == pytest.approx(4.0)
    assert s["cost_usd"]["total"] == pytest.approx(9.0) and s["cost_usd"]["per_item"] == pytest.approx(0.9)
    assert "failed $" in report.to_markdown(report.summarize(out))


def record(ledger: CostLedger, usd: float, n: int = 1) -> None:
    for _ in range(n):
        ledger.record("r1", "lme.answer", ModelResult("t", None, Usage(1, 1), usd, 1.0, "stub", "m", "m", "end_turn"))


def test_the_ledger_is_checked_against_the_predictions_and_judgements(tmp_path):
    out = make_run(tmp_path, {"X": "c" * 10}, cost=0.5)  # 10 answers and 10 judgements at 0.5: $10 as if live
    ledger = CostLedger(tmp_path / "ledger.sqlite")
    record(ledger, 1.0, 10)  # $10 live
    s = report.summarize(out, tmp_path / "ledger.sqlite")
    assert s["ledger"] == {"calls": 10, "spent_usd": pytest.approx(10.0)} and s["warnings"] == []
    record(ledger, 0.4)  # $10.40 live: within 5%
    assert report.summarize(out, tmp_path / "ledger.sqlite")["warnings"] == []
    record(ledger, 1.0)  # $11.40: 12% over
    s = report.summarize(out, tmp_path / "ledger.sqlite")
    (warning,) = s["warnings"]
    assert "$10.0000" in warning and "$11.4000" in warning and "5%" in warning
    assert "cost ledger" in report.to_markdown(s)


def test_a_ledger_far_below_the_predictions_is_a_warning_too(tmp_path):
    out = make_run(tmp_path, {"X": "c" * 10}, cost=0.5)
    record(CostLedger(tmp_path / "ledger.sqlite"), 1.0, 5)  # half of it was replayed, or lost
    assert len(report.summarize(out, tmp_path / "ledger.sqlite")["warnings"]) == 1


def test_a_run_with_no_cost_and_no_ledger_calls_has_no_cost_warning(tmp_path):
    out = make_run(tmp_path, {"X": "c" * 10})
    CostLedger(tmp_path / "ledger.sqlite")
    assert report.summarize(out, tmp_path / "ledger.sqlite")["warnings"] == []


# --- what is in the report ---------------------------------------------------------------------------------


def test_the_report_records_the_run_it_describes(tmp_path):
    out = make_run(tmp_path, {"X": "c" * 10})
    summary, md = report.write_report(out)
    assert summary["run"]["git_commit"] == "c0ffee" and summary["run"]["held_out"] is False
    assert summary["run"]["judge_prompt_hash"] == jd.prompt_hash() and summary["run"]["bars"] == {"lme_margin_points": 10}
    assert json.loads((out / "report.json").read_text())["pairs"] == []
    assert "# Run r1" in md.read_text()


def test_the_report_names_no_item(tmp_path):
    out = make_run(tmp_path, {"none": "ccwwwwwwww", "B3": "c" * 10, "B1": "wcwcwwwwcw"})
    summary, md = report.write_report(out)
    text = json.dumps(summary) + md.read_text()
    assert "i00" not in text and "i09" not in text


def test_the_run_summary_shows_the_judge_batch_size(tmp_path):
    out = make_run(tmp_path, {"X": "c" * 10})
    summary, md = report.write_report(out)
    assert summary["run"]["judge_batch_size"] == jd.judge_batch_size() == 8
    assert "judge family stub (grades 8 answers to a call)" in md.read_text()
    run = json.loads((out / runner.RUN_FILE).read_text())
    del run["fingerprint"]["judge_batch_size"]  # a run made before judging was batched
    runner.write_json(out / runner.RUN_FILE, run)
    summary, md = report.write_report(out)
    assert summary["run"]["judge_batch_size"] is None and "answers to a call" not in md.read_text()

