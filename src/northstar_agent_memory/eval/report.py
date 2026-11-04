"""The report of a run: every system side by side, each score with its cost (DESIGN §8;
note 09, Implications §2, §4 and §7).

`summarize` reads a run directory (runner.py) and returns a plain dict; `to_markdown` turns it
into tables. The rules the report keeps:

- Every comparison is paired and uses only the items all compared systems have judgements for:
  the accuracy table uses the items every full-coverage system finished, and each pair of systems
  uses the items both finished, with a 95% bootstrap interval of the difference. A system that
  runs on a subset by design (B0 on the test split) is compared with another only on that subset.
- A run with a system that has fewer judged items than it should, or errors, carries an
  INCOMPLETE banner.
- `decide` applies DESIGN §8, "How a bar is decided", to a paired difference.
- When the run holds "none" (closed book) and B3 (the evidence), each item is classed as needing
  memory (none wrong, B3 right), answerable without memory (none right) or unsolved (B3 wrong),
  and every system's accuracy over the items that need memory is the headline.
- Cost counts failed items too. The report warns when the predictions' and judges' cost is not
  within 5% of the cost ledger's live spend, and when a model that answered is not the one asked for.
- Scores count only when the run's judge passed its own test on wrong-but-on-topic answers
  (`judge-check.json`) and the tested judge model and prompt hash are the run's.

The report holds counts and system names only, never question or answer text.
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path

from northstar_agent_memory import config as northstar_config
from northstar_agent_memory.eval import runner
from northstar_agent_memory.eval.metrics import (
    Interval,
    PairedDifference,
    bootstrap_ci,
    cost_summary,
    paired_difference,
    qa_scores,
)
from northstar_agent_memory.eval.types import Judgement, QAItem
from northstar_agent_memory.models.budget import CostLedger
from northstar_agent_memory.models.registry import LEDGER_DB
from northstar_agent_memory.paths import eval_root

ABOVE = "above"  # "at least N points above"
AS_GOOD = "as_good"  # "at least as good as"
AS_GOOD_FLOOR_POINTS = -10.0
LEDGER_TOLERANCE = 0.05
NONE_SYSTEM = "none"
ORACLE_SYSTEM = "B3"
NEEDED, WITHOUT_MEMORY, UNSOLVED = "needed", "answerable_without_memory", "unsolved"


# --- deciding a bar ----------------------------------------------------------------------------


def decide(difference: PairedDifference | Interval | dict, kind: str, points: float = 0.0) -> str:
    """"pass", "fail" or "undecided" for a paired difference against a bar (DESIGN §8, "How a bar is decided").

    `difference` is a PairedDifference, an Interval, or a dict with `estimate`, `low` and `high`, all in
    accuracy (0 to 1); `points` is in percentage points.

    - ABOVE ("at least N points above"): passes when the difference is at least N points and its
      95% interval's lower bound is above zero.
    - AS_GOOD ("at least as good as"): passes when the difference is not below zero and the lower
      bound is above -10 points.

    Fails when the difference itself is short of the bar (below N, or below zero). Undecided when the
    difference reaches the bar but the interval is too wide to say so.
    """
    if isinstance(difference, PairedDifference):
        difference = difference.difference
    if isinstance(difference, Interval):
        estimate, low = difference.estimate, difference.low
    else:
        estimate, low = difference["estimate"], difference["low"]
    estimate, low = round(estimate * 100, 9), round(low * 100, 9)
    if kind == ABOVE:
        need, floor = points, 0.0
    elif kind == AS_GOOD:
        need, floor = 0.0, AS_GOOD_FLOOR_POINTS
    else:
        raise ValueError(f"unknown bar kind {kind!r}; use {ABOVE!r} or {AS_GOOD!r}")
    if estimate < need:
        return "fail"
    return "pass" if low > floor else "undecided"


# --- summarizing -------------------------------------------------------------------------------


def _interval(values: list[float], seed: int) -> dict | None:
    if not values:
        return None
    iv: Interval = bootstrap_ci(values, seed=seed)
    return {"estimate": iv.estimate, "low": iv.low, "high": iv.high, "n": iv.n}


def classify_needed(correct: dict[str, dict[str, float]]) -> dict[str, str]:
    """Each item judged for both "none" and B3: needed, answerable without memory, or unsolved.

    - answerable without memory: "none" was right (whatever B3 did);
    - needed: "none" was wrong and B3 was right, so memory made the difference;
    - unsolved: both were wrong.
    """
    none, oracle = correct[NONE_SYSTEM], correct[ORACLE_SYSTEM]
    out = {}
    for item_id in sorted(none.keys() & oracle.keys()):
        out[item_id] = WITHOUT_MEMORY if none[item_id] else NEEDED if oracle[item_id] else UNSOLVED
    return out


def _pair(judgements: list[Judgement], a: str, b: str, seed: int, margin_points: float) -> dict:
    try:
        pd = paired_difference(judgements, a, b, seed)
    except ValueError:  # no item judged for both
        return {
            "a": a, "b": b, "n": 0, "accuracy_a": None, "accuracy_b": None, "difference": None,
            "above": "undecided", "as_good": "undecided",
        }
    diff = {"estimate": pd.difference.estimate, "low": pd.difference.low, "high": pd.difference.high, "n": pd.n}
    return {
        "a": a,
        "b": b,
        "n": pd.n,
        "accuracy_a": pd.accuracy_a,
        "accuracy_b": pd.accuracy_b,
        "difference": diff,
        "above": decide(pd, ABOVE, margin_points),
        "as_good": decide(pd, AS_GOOD),
    }


def summarize(out_dir: Path | str, ledger_db: Path | str | None = None) -> dict:
    """Scores, comparisons, counts, tokens, cost and latency per system for the run in `out_dir`."""
    out_dir = Path(out_dir)
    run = runner.load_run(out_dir)
    if run is None:
        raise FileNotFoundError(f"no run in {out_dir}: {runner.RUN_FILE} is missing")
    config = northstar_config.load()
    seed = int(config["eval"]["seed"])
    margin = float(config["eval"]["lme_margin_points"])
    fingerprint = run.get("fingerprint", {})
    systems_in_run: list[str] = run["systems"]
    items = [
        QAItem(i["id"], run["dataset"], "", "", i["question_type"], [], abstention=i["abstention"], split=i.get("split", "dev"))
        for i in run["items"]
    ]
    item_ids = [i.id for i in items]
    by_id = {i.id: i for i in items}
    subsets: dict[str, list[str]] = run.get("subsets", {})
    expected = {s: [i for i in item_ids if s not in subsets or i in set(subsets[s])] for s in systems_in_run}

    rows = runner.load_judgement_rows(out_dir)
    judgements = [j for j in (runner.judgement_from_dict(r) for r in rows) if j.item_id in by_id and j.system in expected]
    predictions = [p for p in runner.load_predictions(out_dir) if p.item_id in by_id and p.system in expected]
    judged: dict[str, dict[str, Judgement]] = {s: {} for s in systems_in_run}
    for j in judgements:
        judged[j.system][j.item_id] = j
    correct = {s: {i: 1.0 if j.outcome == "correct" else 0.0 for i, j in by_item.items()} for s, by_item in judged.items()}

    # the items every system with full coverage has judgements for
    judged_systems = [s for s in systems_in_run if judged[s]]
    full = [s for s in judged_systems if len(expected[s]) == len(item_ids)] or judged_systems
    common = sorted(set.intersection(*(set(judged[s]) for s in full)), key=item_ids.index) if full else []
    common_set = set(common)

    judge_cost = {s: sum(r.get("judge_cost_usd", 0.0) for r in rows if r["system"] == s) for s in systems_in_run}
    errors = {s: sum(1 for p in predictions if p.system == s and p.meta.get("error")) for s in systems_in_run}
    ok_predictions = [p for p in predictions if not p.meta.get("error")]
    failed_usd = {s: sum(p.cost_usd for p in predictions if p.system == s and p.meta.get("error")) for s in systems_in_run}

    costs = cost_summary(ok_predictions)
    not_independent = sum(1 for j in judgements if j.rationale.startswith("not independent"))

    systems: dict[str, dict] = {}
    for system in systems_in_run:
        mine = judged[system]
        own_items = [by_id[i] for i in expected[system]]
        scores = qa_scores([j for j in judgements if j.system == system], own_items).get(system)
        compared = [by_id[i] for i in common if i in mine]
        c = correct[system]
        by_type_items: dict[str, list[QAItem]] = {}
        for item in compared:
            by_type_items.setdefault(item.question_type, []).append(item)
        cost = costs.get(system)
        answer_usd = (cost.total_cost_usd if cost else 0.0) + failed_usd[system]
        own_correct = [c.get(i.id, 0.0) for i in own_items]
        systems[system] = {
            "n_items": len(own_items),
            "n_judged": len(mine),
            "n_errors": errors[system],
            "complete": len(mine) >= len(own_items) and errors[system] == 0,
            # on the items every system finished: the figures to compare
            "compared": {
                "n": len(compared),
                "accuracy": _interval([c[i.id] for i in compared], seed),
                "answerable_accuracy": _interval([c[i.id] for i in compared if not i.abstention], seed),
                "abstention_accuracy": _interval([c[i.id] for i in compared if i.abstention], seed),
                "by_type": {t: _interval([c[i.id] for i in group], seed) for t, group in sorted(by_type_items.items())},
            },
            # on all of the system's own items, an item with no judgement counting as omitted
            "accuracy": _interval(own_correct, seed),
            "answerable_accuracy": _interval([c.get(i.id, 0.0) for i in own_items if not i.abstention], seed),
            "abstention_accuracy": _interval([c.get(i.id, 0.0) for i in own_items if i.abstention], seed),
            "by_type": {
                t: _interval([c.get(i.id, 0.0) for i in own_items if i.question_type == t], seed)
                for t in sorted({i.question_type for i in own_items})
            },
            "counts": {
                "correct": scores.overall.correct if scores else 0,
                "hallucinated": scores.overall.hallucinated if scores else 0,
                "omitted": scores.overall.omitted if scores else len(own_items),
            },
            "tokens": {
                "mean_context": cost.mean_context_tokens if cost else 0.0,
                "input": cost.usage.input_tokens if cost else 0,
                "output": cost.usage.output_tokens if cost else 0,
                "cache_read": cost.usage.cache_read_tokens if cost else 0,
                "cache_write": cost.usage.cache_write_tokens if cost else 0,
            },
            "calls": cost.calls if cost else 0,
            "cost_usd": {
                "answer": answer_usd,
                "failed": failed_usd[system],
                "judge": judge_cost[system],
                "total": answer_usd + judge_cost[system],
                "per_item": (answer_usd + judge_cost[system]) / len(own_items) if own_items else 0.0,
            },
            "latency_s": {"p50": cost.p50_latency_s if cost else 0.0, "p95": cost.p95_latency_s if cost else 0.0},
            "served_models": sorted({str(p.meta.get("model")) for p in ok_predictions if p.system == system and p.meta.get("model")}),
        }

    pairs = [_pair(judgements, a, b, seed, margin) for a, b in itertools.combinations(judged_systems, 2)]
    needs = _needs_memory(judged, correct, judgements, seed, margin)

    ledger = _ledger(run["run_id"], ledger_db)
    warnings = _warnings(run, systems, judgements, run.get("models", {}), ledger)
    check = _judge_check(out_dir)
    incomplete = [s for s, v in systems.items() if not v["complete"]]
    return {
        "run": {k: run[k] for k in ("run_id", "dataset", "split", "answerer_family", "judge_family", "config_version", "token_budget", "models")}
        | {
            "n_items": len(items),
            "created_at": run["created_at"],
            "updated_at": run["updated_at"],
            "held_out": bool(run.get("held_out")),
            "git_commit": fingerprint.get("git_commit"),
            "git_dirty": fingerprint.get("git_dirty"),
            "answer_prompt_hash": fingerprint.get("answer_prompt_hash"),
            "judge_prompt_hash": fingerprint.get("judge_prompt_hash"),
            "judge_batch_size": fingerprint.get("judge_batch_size"),
            "bars": fingerprint.get("bars"),
        },
        "complete": not incomplete,
        "incomplete": incomplete,
        "n_common": len(common),
        "subset_systems": sorted(subsets),
        "not_independent": not_independent,
        "systems": systems,
        "pairs": pairs,
        "needs_memory": needs,
        "warnings": warnings,
        "judge_check": check,
        "ledger": ledger,
    } | _counts(check, run, fingerprint, not_independent)


def _counts(check: dict | None, run: dict, fingerprint: dict, not_independent: int) -> dict:
    """Whether the scores count: the judge passed its test, and the tested judge model and prompt are the run's."""
    requested = run.get("models", {}).get(f"{run['judge_family']}.judge")
    why = []
    if check is None:
        why.append("the judge has not passed its test on wrong-but-on-topic answers (no judge check on file)")
    elif check["result"] == "insufficient":
        why.append(f"the judge check tested too few wrong answers ({check['n_negatives']}, at least {check['min_wrong']} needed)")
    elif not check["passed"]:
        why.append("the judge failed its test on wrong-but-on-topic answers")
    elif check["judge_family"] != run["judge_family"]:
        why.append("the judge check was for another judge family")
    elif check.get("judge_model") != requested:
        why.append(f"the judge check tested {check.get('judge_model')}, not the run's judge {requested}")
    elif check.get("prompt_hash") != fingerprint.get("judge_prompt_hash"):
        why.append("the judge check was made with another judge prompt or rules than the run's")
    if not_independent:
        why.append(f"{not_independent} judgements were made by the answerer's own family")
    return {"counts": not why, "provisional_because": why}


def _judge_check(out_dir: Path) -> dict | None:
    check_file = out_dir / runner.JUDGE_CHECK_FILE
    if not check_file.exists():
        return None
    raw = json.loads(check_file.read_text(encoding="utf-8"))
    m = raw["meta"]
    return {
        "judge_family": raw["judge_family"],
        "judge_model": raw.get("judge_model"),
        "served_model": m["judge_model"],
        "prompt_hash": raw.get("prompt_hash"),
        "generator_family": raw["generator_family"],
        "dataset": raw.get("dataset"),
        "probe_kinds": raw.get("probe_kinds", {}),
        "bar": raw["bar"],
        "min_wrong": raw.get("min_wrong", 60),
        "min_true_accept": raw.get("min_true_accept", 0.85),
        "judge_batch_size": raw.get("judge_batch_size"),
        "result": raw.get("result", "passed" if raw["passed"] else "failed"),
        "passed": raw["passed"],
        "n_positives": m["n_positives"],
        "n_negatives": m["n_negatives"],
        "true_accept_rate": m["true_accept_rate"],
        "false_accept_rate": m["false_accept_rate"],
        "false_accept_upper95": m["false_accept_upper95"],
        "false_accept_by_kind": m["false_accept_by_kind"],
        "n_by_kind": m["n_by_kind"],
    }


def _needs_memory(
    judged: dict[str, dict[str, Judgement]], correct: dict[str, dict[str, float]], judgements: list[Judgement], seed: int, margin: float
) -> dict | None:
    """The questions that need memory, when the run holds both "none" and B3 with judgements."""
    if not (judged.get(NONE_SYSTEM) and judged.get(ORACLE_SYSTEM)):
        return None
    classes = classify_needed(correct)
    needed = {i for i, k in classes.items() if k == NEEDED}
    counts = {k: sum(1 for v in classes.values() if v == k) for k in (NEEDED, WITHOUT_MEMORY, UNSOLVED)}
    accuracy = {s: _interval([c[i] for i in sorted(needed) if i in c], seed) for s, c in correct.items() if c}
    on_needed = [j for j in judgements if j.item_id in needed]
    pairs = [_pair(on_needed, a, b, seed, margin) for a, b in itertools.combinations([s for s in judged if judged[s]], 2)]
    return {"n": len(classes), "counts": counts, "accuracy": accuracy, "pairs": pairs}


def _warnings(run: dict, systems: dict[str, dict], judgements: list[Judgement], models: dict, ledger: dict | None) -> list[str]:
    out: list[str] = []
    answerer = models.get(f"{run['answerer_family']}.answerer")
    for name, s in systems.items():
        other = [m for m in s["served_models"] if m != answerer]
        if answerer and other:
            out.append(f"{name} was answered by {', '.join(other)}, not the requested {answerer}; a fallback may have answered")
    judge = models.get(f"{run['judge_family']}.judge")
    served = sorted({j.judge_model for j in judgements if j.judge_family != "code" and j.judge_model})
    if judge and any(m != judge for m in served):
        out.append(f"judgements were made by {', '.join(served)}, not the requested {judge}")
    if ledger is not None:
        counted = sum(s["cost_usd"]["total"] for s in systems.values())
        spent = ledger["spent_usd"]
        if max(counted, spent) > 0 and abs(counted - spent) > LEDGER_TOLERANCE * max(counted, spent):
            out.append(
                f"the predictions and judgements cost ${counted:.4f} and the cost ledger holds ${spent:.4f} live for this run "
                "(more than 5% apart): replayed calls cost nothing live, and calls that failed after the vendor billed them, "
                "or steps lost with a failed item, show only in the ledger"
            )
    return out


def _ledger(run_id: str, ledger_db: Path | str | None) -> dict | None:
    """What the cost ledger holds for the run: live spend only, since replays cost nothing."""
    path = Path(ledger_db) if ledger_db else eval_root() / LEDGER_DB
    if not path.exists():
        return None
    entries = CostLedger(path).entries(run_id)
    return {"calls": len(entries), "spent_usd": sum(e["cost_usd"] for e in entries)}


# --- markdown ---------------------------------------------------------------------------------


def _pct(iv: dict | None) -> str:
    if iv is None:
        return "-"
    return f"{iv['estimate'] * 100:.1f}% [{iv['low'] * 100:.1f}, {iv['high'] * 100:.1f}]"


def _points(iv: dict | None) -> str:
    if iv is None:
        return "-"
    return f"{iv['estimate'] * 100:+.1f} [{iv['low'] * 100:+.1f}, {iv['high'] * 100:+.1f}]"


def _usd(x: float) -> str:
    return f"${x:.4f}" if x < 1 else f"${x:.2f}"


def _table(head: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(head) + " |", "|" + "|".join(["---"] + ["---:"] * (len(head) - 1)) + "|"]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return lines


def _pair_table(pairs: list[dict], margin: float) -> list[str]:
    return _table(
        ["A vs B", "items", "A", "B", "A - B, points [95%]", f"A at least {margin:g} above B", "A at least as good as B"],
        [
            [
                f"{p['a']} vs {p['b']}",
                str(p["n"]),
                "-" if p["accuracy_a"] is None else f"{p['accuracy_a'] * 100:.1f}%",
                "-" if p["accuracy_b"] is None else f"{p['accuracy_b'] * 100:.1f}%",
                _points(p["difference"]),
                p["above"],
                p["as_good"],
            ]
            for p in pairs
        ],
    )


def to_markdown(summary: dict) -> str:
    run, systems = summary["run"], summary["systems"]
    margin = float((run.get("bars") or {}).get("lme_margin_points", northstar_config.load()["eval"]["lme_margin_points"]))
    lines = [
        f"# Run {run['run_id']}",
        "",
        f"{run['dataset']} {run['split']}, {run['n_items']} items; answerer family {run['answerer_family']}, "
        f"judge family {run['judge_family']}"
        + (f" (grades {run['judge_batch_size']} answers to a call)" if run.get("judge_batch_size") else "")
        + f"; config {run['config_version']}; token budget {run['token_budget']}"
        + (f"; held-out run, code {str(run['git_commit'])[:10]}" if run.get("held_out") else "")
        + ".",
        "",
    ]
    if not summary["complete"]:
        short = ", ".join(
            f"{n} ({s['n_judged']}/{s['n_items']} judged" + (f", {s['n_errors']} failed" if s["n_errors"] else "") + ")"
            for n, s in systems.items()
            if not s["complete"]
        )
        lines += [
            f"**INCOMPLETE: {short}.** Every comparison below uses only the {summary['n_common']} items all compared "
            "systems finished; resume the run, then read the report again.",
            "",
        ]
    if not summary["counts"]:
        lines += [f"**Provisional: these scores do not count yet, because {'; '.join(summary['provisional_because'])}.**", ""]
    for w in summary["warnings"]:
        lines += [f"**Warning:** {w}", ""]

    needs = summary["needs_memory"]
    if needs is not None:
        c = needs["counts"]
        lines += [
            "## Questions that need memory (the headline)",
            "",
            f"Of {needs['n']} items judged for both the closed-book run (none) and B3: {c[NEEDED]} need memory "
            f"(none wrong, B3 right), {c[WITHOUT_MEMORY]} are answerable without memory (none right), {c[UNSOLVED]} are unsolved "
            "(both wrong). Accuracy over the items that need memory:",
            "",
        ]
        lines += _table(
            ["system", "items", "accuracy"],
            [[n, str(iv["n"]) if iv else "0", _pct(iv)] for n, iv in needs["accuracy"].items()],
        )
        lines += ["", "Paired differences over the items that need memory:", ""]
        lines += _pair_table(needs["pairs"], margin)
        lines += [""]
    elif NONE_SYSTEM in systems or ORACLE_SYSTEM in systems:
        lines += ["The questions that need memory are found only when the run holds both none (closed book) and B3, each judged.", ""]

    lines += [f"## Accuracy on the {summary['n_common']} items all systems finished (95% bootstrap interval over items)", ""]
    if summary["subset_systems"]:
        lines += [
            f"{', '.join(summary['subset_systems'])} ran on a subset of the items by design; its row holds only items the other systems "
            "also finished, so compare it with another system in the paired tables, not by this column.",
            "",
        ]
    lines += _table(
        ["system", "judged", "items", "accuracy", "answerable", "abstention"],
        [
            [name, f"{s['n_judged']}/{s['n_items']}", str(s["compared"]["n"]), _pct(s["compared"]["accuracy"]),
             _pct(s["compared"]["answerable_accuracy"]), _pct(s["compared"]["abstention_accuracy"])]
            for name, s in systems.items()
        ],
    )
    types = sorted({t for s in systems.values() for t in s["compared"]["by_type"]})
    lines += ["", "## Accuracy by question type", ""]
    lines += _table(["system"] + types, [[name] + [_pct(s["compared"]["by_type"].get(t)) for t in types] for name, s in systems.items()])

    lines += ["", "## Paired differences on all items (each pair on the items both systems finished)", ""]
    lines += _pair_table(summary["pairs"], margin)
    lines += [
        "",
        f"A bar is decided on the difference and its interval: \"at least N points above\" passes when the difference is at least N "
        "and the interval's lower bound is above 0; \"at least as good as\" passes when the difference is at least 0 and the lower "
        "bound is above -10. Fail means the difference itself is short of the bar; undecided means it reaches the bar but the "
        "interval is too wide to say.",
    ]

    lines += ["", "## Outcomes (on each system's own items; an item with no judgement counts as omitted)", ""]
    lines += _table(
        ["system", "correct", "hallucinated", "omitted", "errors"],
        [
            [name, str(s["counts"]["correct"]), str(s["counts"]["hallucinated"]), str(s["counts"]["omitted"]), str(s["n_errors"])]
            for name, s in systems.items()
        ],
    )

    lines += ["", "## Models that answered", ""]
    lines += _table(
        ["system", "answered by"], [[name, ", ".join(s["served_models"]) or "-"] for name, s in systems.items()]
    )

    lines += ["", "## Tokens, cost and latency (cost includes failed items)", ""]
    lines += _table(
        ["system", "context tokens", "input", "output", "calls", "answer $", "failed $", "judge $", "$ per item", "p50 s", "p95 s"],
        [
            [
                name,
                f"{s['tokens']['mean_context']:.0f}",
                str(s["tokens"]["input"]),
                str(s["tokens"]["output"]),
                str(s["calls"]),
                _usd(s["cost_usd"]["answer"]),
                _usd(s["cost_usd"]["failed"]),
                _usd(s["cost_usd"]["judge"]),
                _usd(s["cost_usd"]["per_item"]),
                f"{s['latency_s']['p50']:.1f}",
                f"{s['latency_s']['p95']:.1f}",
            ]
            for name, s in systems.items()
        ],
    )
    ledger = summary["ledger"]
    if ledger:
        lines += ["", f"The cost ledger holds {ledger['calls']} live calls for this run, {_usd(ledger['spent_usd'])} in all."]

    check = summary["judge_check"]
    if check:
        lines += ["", "## Judge check", ""]
        lines += [
            f"{check['judge_family']} judge ({check['judge_model']}; served as {check['served_model']}) on answers written by "
            f"{check['generator_family']}: {check['result']}. Accepted {_rate(check['false_accept_rate'])} of "
            f"{check['n_negatives']} wrong answers (bar: below {check['bar'] * 100:.0f}%, with at least {check['min_wrong']} tested; "
            f"95% upper bound {_rate(check['false_accept_upper95'])}) and {_rate(check['true_accept_rate'])} of {check['n_positives']} "
            f"right ones (at least {check['min_true_accept'] * 100:.0f}% needed). Prompt hash {check['prompt_hash']}"
            + (f", {check['judge_batch_size']} answers to a call." if check.get("judge_batch_size") else "."),
            "",
        ]
        lines += _table(
            ["kind of wrong answer", "n", "accepted"],
            [[k, str(check["n_by_kind"][k]), _rate(v)] for k, v in sorted(check["false_accept_by_kind"].items())],
        )
    return "\n".join(lines) + "\n"


def _rate(x: float | None) -> str:
    return "-" if x is None else f"{x * 100:.1f}%"


def write_report(out_dir: Path | str, ledger_db: Path | str | None = None) -> tuple[dict, Path]:
    """Summarize the run and write `report.json` and `report.md` beside its files."""
    out_dir = Path(out_dir)
    summary = summarize(out_dir, ledger_db)
    runner.write_json(out_dir / "report.json", summary)
    (out_dir / "report.md").write_text(to_markdown(summary), encoding="utf-8")
    return summary, out_dir / "report.md"
