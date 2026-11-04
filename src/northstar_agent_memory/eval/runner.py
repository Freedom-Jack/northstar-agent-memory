"""Runs the baselines on QA items, judges every answer, and keeps what it learned (DESIGN §8;
note 09, Implications §2, §4, §7).

One run is one directory (`run.json`, `predictions.jsonl`, `judgements.jsonl`). Both JSONL
files are appended to as each item finishes, so a stopped run resumes by skipping the
(item, system) pairs already judged and judging again, without answering again, those
that were answered but not judged. An item that failed is written with the error in
`meta["error"]`, has no judgement, and is tried again on resume. A budget, credential or
model-availability error stops the whole run, since every later call would fail the same way.

Items go in order and every requested system runs on item 1 before any runs on item 2, so
a stop leaves the systems on the same items. Every model request goes out with the prompt
cache and the server-side refusal fallback off (`MeasuredPort`), so what is measured is the
model asked for. `run.json` keeps a fingerprint (config version, token budget, models,
prompt hashes, system parameters, git commit and dirty flag); a resume that differs in any
part is refused. A run on the test split is a held-out run: it needs `held_out=True`, a clean
git work tree and a passing judge check for the run's judge model and prompt, and it is
appended to the held-out ledger.

The judge is of one family and the answerer of another (the family rule); `allow_same_family`
exists for tests only, and such judgements say "not independent". Probe metadata
`forbidden_terms` (scenario S15, ledger.py) is checked by code before any model judges.
`estimate_cost` prices a run from token estimates, with no model call.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field, fields, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

from northstar_agent_memory.eval import baselines as bl
from northstar_agent_memory.eval import judge as jd
from northstar_agent_memory.eval import longmemeval as lme
from northstar_agent_memory.eval.metrics import normalize_text
from northstar_agent_memory.eval.scenarios.ledger import World, ask
from northstar_agent_memory.eval.tokens import CHARS_PER_TOKEN, estimate_tokens
from northstar_agent_memory.eval.types import Judgement, Prediction, QAItem
from northstar_agent_memory.models.budget import billed_result, cost_usd, resolve_model
from northstar_agent_memory.models.port import (
    BudgetExceeded,
    ModelError,
    ModelPort,
    ModelRequest,
    ModelResult,
    ModelUnavailable,
    NoCostCap,
    NoCredentials,
    Usage,
)
from northstar_agent_memory.paths import eval_root
from northstar_agent_memory.transcript import Source

# "none" is the closed-book run (no history), which finds the questions that need memory; B3 is
# the ceiling. Both are in every default set (DESIGN §8, "Questions that need memory").
SYSTEMS = ("none", "B0", "B1", "B2", "B3", "B4")
FATAL = (BudgetExceeded, NoCostCap, NoCredentials, ModelUnavailable)

RUN_FILE = "run.json"
PREDICTIONS_FILE = "predictions.jsonl"
JUDGEMENTS_FILE = "judgements.jsonl"
JUDGE_CHECK_FILE = "judge-check.json"
JUDGE_PROBES_FILE = "judge-probes.jsonl"
HELD_OUT_LEDGER = "held-out-ledger.jsonl"
TEST_SPLIT = "test"

# Assumptions behind `estimate_cost`: output sizes of calls that have not happened yet.
ANSWER_OUT_TOKENS = 120
JUDGE_OUT_TOKENS = 250
OBSERVE_OUT_RATIO = 0.12  # B4: observation tokens written per token of session read
B2_STEPS = 4  # B2: calls per item, the last one the answer
B2_OBSERVATION_TOKENS = 2000


def baseline_classes() -> dict[str, type]:
    """The baseline classes in baselines.py, by the `system` name each one carries."""
    return {c.system: c for c in vars(bl).values() if isinstance(c, type) and getattr(c, "system", "") in SYSTEMS}


def make_baseline(name: str, port: ModelPort, family: str, token_budget: int | None = None) -> bl.Baseline:
    if name not in SYSTEMS:
        raise ValueError(f"unknown system {name!r}; the systems are {', '.join(SYSTEMS)}")
    classes = baseline_classes()
    if name not in classes:
        raise ValueError(f"system {name!r} has no baseline class in baselines.py")
    return classes[name](port, family, token_budget=token_budget)


def limit_items(items: Sequence[QAItem], n: int | None) -> list[QAItem]:
    """The first n items taken in turn from each question type, so a small run still covers every type."""
    items = list(items)
    if n is None or n >= len(items):
        return items
    groups: dict[str, list[QAItem]] = {}
    for item in items:
        groups.setdefault(item.question_type, []).append(item)
    out: list[QAItem] = []
    for k in range(max(map(len, groups.values()), default=0)):
        for group in groups.values():
            if k < len(group) and len(out) < n:
                out.append(group[k])
    return out


# --- cost estimate ---------------------------------------------------------------------------


def history_tokens(item: QAItem) -> int:
    """The estimated tokens of the whole history as the baselines print it (ids, speakers, headers)."""
    chars = sum(len(m.text) + len(m.id) + len(m.speaker) + 6 for s in item.haystack for m in s.messages)
    return math.ceil((chars + 40 * len(item.haystack)) / CHARS_PER_TOKEN)


def _session_tokens(source: Source) -> int:
    return history_tokens(QAItem("", "", "", "", "", [source]))


def _answer_input(item: QAItem, context_tokens: int) -> int:
    return estimate_tokens(bl.ANSWER_SYSTEM + json.dumps(bl.ANSWER_SCHEMA)) + estimate_tokens(item.question) + 40 + context_tokens


@dataclass(slots=True)
class _Call:
    role: str
    input_tokens: int
    output_tokens: int


def _calls_for(system: str, item: QAItem, budget: int) -> list[_Call]:
    """The model calls one baseline makes for one item, in estimated tokens."""
    history = history_tokens(item)
    if system == "none":
        return [_Call("answerer", _answer_input(item, 0), ANSWER_OUT_TOKENS)]
    if system == "B0":
        return [_Call("answerer", _answer_input(item, min(history, bl.DEFAULT_MAX_CONTEXT)), ANSWER_OUT_TOKENS)]
    if system == "B1":
        return [_Call("answerer", _answer_input(item, min(history, budget)), ANSWER_OUT_TOKENS)]
    if system == "B3":
        gold = set(item.evidence_message_ids)
        evidence = sum(estimate_tokens(r.render() + "\n\n") for r in bl.all_rounds(item) if gold.intersection(r.message_ids))
        return [_Call("answerer", _answer_input(item, min(evidence, budget)), ANSWER_OUT_TOKENS)]
    if system == "B2":
        base = estimate_tokens(bl.GREP_SYSTEM + json.dumps(bl.ACTION_SCHEMA)) + estimate_tokens(item.question) + 80
        step = min(B2_OBSERVATION_TOKENS, budget // max(B2_STEPS - 1, 1))
        return [_Call("answerer", base + k * step, ANSWER_OUT_TOKENS) for k in range(B2_STEPS)]
    if system == "B4":
        fixed = estimate_tokens(bl.OBSERVE_SYSTEM + json.dumps(bl.OBSERVE_SCHEMA))
        calls, log_tokens = [], 0
        for source in item.haystack:
            read = _session_tokens(source)
            written = min(bl.OBSERVE_MAX_TOKENS, max(60, int(read * OBSERVE_OUT_RATIO)))
            log_tokens += written
            calls.append(_Call("worker_small", fixed + read, written))
        calls.append(_Call("answerer", _answer_input(item, min(log_tokens, budget)), ANSWER_OUT_TOKENS))
        return calls
    raise ValueError(f"no estimate for system {system!r}")


def _judge_call(item: QAItem) -> _Call:
    prompt = jd.QA_SYSTEM + json.dumps(jd.QA_SCHEMA) + jd.qa_prompt(item, "x" * 300)
    return _Call("judge", estimate_tokens(prompt), JUDGE_OUT_TOKENS)


def estimate_cost(
    items: Iterable[QAItem],
    systems: Sequence[str],
    answerer_family: str,
    judge_family: str,
    config: dict,
) -> dict[str, dict]:
    """Dollars per system for answering and judging `items`, from token estimates and config prices.

    No model is called. A model with no configured ID or price makes that side's dollars and
    `total_usd` None, and `unpriced` says which. The "stub" family costs nothing. The numbers rest on the assumed
    output sizes at the top of this module, so they are for sizing a run, not for billing.
    """
    items = list(items)
    budget = int(config["eval"]["token_budget"])
    out: dict[str, dict] = {}
    for system in systems:
        usage = Usage()
        usd = {"answer": 0.0, "judge": 0.0}
        unpriced: set[str] = set()
        unpriced_parts: set[str] = set()
        calls = 0
        for item in items:
            calls_of_item = [(c, answerer_family, "answer") for c in _calls_for(system, item, budget)]
            calls_of_item.append((_judge_call(item), judge_family, "judge"))
            for call, family, part in calls_of_item:
                calls += 1
                usage = usage + Usage(call.input_tokens, call.output_tokens)
                if family == "stub":
                    continue
                model = resolve_model(config, ModelRequest("estimate", call.role, family, "", []))  # type: ignore[arg-type]
                price = config.get("prices", {}).get(model) if model else None
                if not price:
                    unpriced_parts.add(part)
                    unpriced.add(f"{family} {call.role}: " + ("no model configured" if not model else f"no price for {model}"))
                    continue
                usd[part] += cost_usd(price, Usage(call.input_tokens, call.output_tokens))
        out[system] = {
            "items": len(items),
            "calls": calls,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "answer_usd": None if "answer" in unpriced_parts else usd["answer"],
            "judge_usd": None if "judge" in unpriced_parts else usd["judge"],
            "total_usd": None if unpriced else usd["answer"] + usd["judge"],
            "unpriced": sorted(unpriced),
        }
    return out


# --- files -------------------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_jsonl(path: Path) -> list[dict]:
    """The rows of a JSONL file; a line cut short by a stopped run is skipped."""
    if not Path(path).exists():
        return []
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _end_line(path: Path) -> None:
    """Make a file end in a newline, so a row appended after a stopped run starts on its own line."""
    if path.exists() and path.stat().st_size:
        with path.open("rb+") as fh:
            fh.seek(-1, os.SEEK_END)
            if fh.read(1) != b"\n":
                fh.write(b"\n")


def write_json(path: Path, data: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def prediction_from_dict(row: dict) -> Prediction:
    row = dict(row)
    row["usage"] = Usage(**row.get("usage", {}))
    return Prediction(**{f.name: row[f.name] for f in fields(Prediction) if f.name in row})


def judgement_from_dict(row: dict) -> Judgement:
    return Judgement(**{f.name: row[f.name] for f in fields(Judgement) if f.name in row})


def load_run(out_dir: Path | str) -> dict | None:
    path = Path(out_dir) / RUN_FILE
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def load_predictions(out_dir: Path | str) -> list[Prediction]:
    """The latest prediction of each (item, system): a retried item replaces its earlier failure."""
    latest = {(r["item_id"], r["system"]): r for r in read_jsonl(Path(out_dir) / PREDICTIONS_FILE)}
    return [prediction_from_dict(r) for r in latest.values()]


def load_judgement_rows(out_dir: Path | str) -> list[dict]:
    latest = {(r["item_id"], r["system"]): r for r in read_jsonl(Path(out_dir) / JUDGEMENTS_FILE)}
    return list(latest.values())


def load_judgements(out_dir: Path | str) -> list[Judgement]:
    return [judgement_from_dict(r) for r in load_judgement_rows(out_dir)]


class _Appender:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.lock = threading.Lock()
        path.parent.mkdir(parents=True, exist_ok=True)
        _end_line(path)

    def add(self, row: dict) -> None:
        line = json.dumps(row, ensure_ascii=False) + "\n"
        with self.lock, self.path.open("a", encoding="utf-8") as fh:
            fh.write(line)


class MeasuredPort:
    """A port for measurement: every request goes out with the prompt cache and the fallback off.

    A cached prefix changes what a call costs and a server-side refusal fallback changes which
    model answers; a measurement must hold both fixed. Build baselines and judges on this port
    (run_qa and run_judge_check do), or a baseline object handed to run_qa is not covered.
    """

    def __init__(self, inner: ModelPort) -> None:
        self.inner = inner

    def complete(self, req: ModelRequest) -> ModelResult:
        return self.inner.complete(replace(req, cache=False, allow_fallback=False))


def measured(port: ModelPort) -> ModelPort:
    return port if isinstance(port, MeasuredPort) else MeasuredPort(port)


class _Meter:
    """A port that remembers, per thread, what its last call cost, for the judgement's record."""

    def __init__(self, inner: ModelPort) -> None:
        self.inner = inner
        self._local = threading.local()

    def complete(self, req: ModelRequest) -> ModelResult:
        result = self.inner.complete(req)
        self._local.cost = getattr(self._local, "cost", 0.0) + result.cost_usd
        self._local.latency = getattr(self._local, "latency", 0.0) + result.latency_s
        return result

    def take(self) -> tuple[float, float]:
        cost, latency = getattr(self._local, "cost", 0.0), getattr(self._local, "latency", 0.0)
        self._local.cost = self._local.latency = 0.0
        return cost, latency


# --- judging by code ----------------------------------------------------------------------------


leaked_term = jd.leaked_term


def judge_prediction(judge: jd.QAJudge, item: QAItem, prediction: Prediction) -> Judgement:
    if prediction.answer.strip() and leaked_term(item, prediction.answer):
        return Judgement(
            item.id, prediction.system, "hallucinated", False, "code", "", "the answer contains a term the probe forbids"
        )
    return judge.judge(item, prediction)


# --- what a run was made with --------------------------------------------------------------------


def git_state() -> tuple[str, bool]:
    """(commit, dirty) of the git work tree this code is in; ("unknown", True) when it cannot be read."""
    here = str(Path(__file__).resolve().parent)

    def git(*args: str) -> str:
        proc = subprocess.run(["git", "-C", here, *args], capture_output=True, text=True, timeout=30, check=True)
        return proc.stdout

    try:
        return git("rev-parse", "HEAD").strip(), bool(git("status", "--porcelain").strip())
    except (OSError, subprocess.SubprocessError):
        return "unknown", True


def _hash(*parts: object) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]


def answer_prompt_hash() -> str:
    """A short hash of every prompt and schema the baselines send, and of the question template."""
    sample = QAItem("h", "hash", "Q?", "A", "t", [])
    return _hash(
        bl.ANSWER_SYSTEM,
        bl.ANSWER_SCHEMA,
        getattr(bl, "CLOSED_BOOK_SYSTEM", ""),
        bl.GREP_SYSTEM,
        bl.ACTION_SCHEMA,
        bl.FINAL_SCHEMA,
        bl.OBSERVE_SYSTEM,
        bl.OBSERVE_SCHEMA,
        bl.question_message(sample, "C"),
    )


def bars_in_force(config: dict) -> dict:
    """The bars the run is judged by, as the config holds them now (DESIGN §8)."""
    e = config["eval"]
    return {"lme_margin_points": e["lme_margin_points"], "judge_false_accept_max": e["judge_false_accept_max"]}


_FINGERPRINT_LABELS = {
    "config_version": "the config version",
    "token_budget": "the token budget",
    "models": "the model for",
    "answer_prompt_hash": "the answer prompts",
    "judge_prompt_hash": "the judge prompt and rules",
    "judge_batch_size": "the judge batch size",
    "system_params": "the system parameter",
    "bars": "the bar",
    "git_commit": "the git commit",
    "git_dirty": "the git work tree being dirty",
}


def make_fingerprint(config: dict, models: dict[str, str], systems: Sequence[bl.Baseline]) -> dict:
    """What a run was made with; a resume must match it (config, budget, models, prompts, parameters, code)."""
    params: dict[str, dict] = {}
    for s in systems:
        for name in ("max_context", "max_steps"):
            if hasattr(s, name):
                params.setdefault(s.system, {})[name] = getattr(s, name)
    commit, dirty = git_state()
    batch = jd.judge_batch_size(config)
    return {
        "config_version": config.get("config_version", ""),
        "token_budget": int(config["eval"]["token_budget"]),
        "models": models,
        "answer_prompt_hash": answer_prompt_hash(),
        "judge_prompt_hash": jd.prompt_hash(batch),
        "judge_batch_size": batch,
        "system_params": params,
        "bars": bars_in_force(config),
        "git_commit": commit,
        "git_dirty": dirty,
    }


def fingerprint_changes(old: dict, new: dict) -> list[str]:
    """What differs between two fingerprints, in words. A model or system new to `new` is not a change."""
    changes = []
    for key, label in _FINGERPRINT_LABELS.items():
        before, after = old.get(key), new.get(key)
        if key not in old:
            changes.append(f"{label} was not recorded")
        elif isinstance(before, dict) and isinstance(after, dict):
            for sub in sorted(before.keys() & after.keys()):
                if before[sub] != after[sub]:
                    changes.append(f"{label} {sub} was {before[sub]!r}, now {after[sub]!r}")
        elif before != after:
            changes.append(f"{label} was {before!r}, now {after!r}")
    return changes


def merge_fingerprint(old: dict, new: dict) -> dict:
    return {k: ({**old.get(k, {}), **v} if isinstance(v, dict) else v) for k, v in new.items()}


# --- held-out discipline -----------------------------------------------------------------------


def find_judge_check(roots: Iterable[Path], judge_family: str, judge_model: str, prompt_hash: str) -> tuple[Path, dict] | None:
    """The newest passing judge check in `roots` (run folders) made for this judge model and prompt."""
    found: list[tuple[str, Path, dict]] = []
    for root in roots:
        path = Path(root) / JUDGE_CHECK_FILE
        if not path.is_file():
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if (
            raw.get("passed") is True
            and raw.get("judge_family") == judge_family
            and raw.get("judge_model") == judge_model
            and raw.get("prompt_hash") == prompt_hash
        ):
            found.append((str(raw.get("checked_at", "")), path, raw))
    if not found:
        return None
    _, path, raw = max(found, key=lambda f: f[0])
    return path, raw


def require_held_out(
    models: dict[str, str], judge_family: str, runs_root: Path, out_dir: Path, judge_batch_size: int | None = None
) -> tuple[Path, dict]:
    """Refuse a held-out run on a dirty work tree or without a passing judge check for this judge.

    Returns the matching check: its path and content.
    """
    commit, dirty = git_state()
    if dirty:
        raise ValueError(
            f"a held-out run needs a clean git work tree (commit {commit[:10]}, with changes not committed): "
            "commit or stash them first, so the result names the code that made it"
        )
    judge_model = models[f"{judge_family}.judge"]
    roots = [out_dir, *sorted(p for p in runs_root.glob("*") if p.is_dir())] if runs_root.is_dir() else [out_dir]
    judge_hash = jd.prompt_hash(judge_batch_size)
    check = find_judge_check(roots, judge_family, judge_model, judge_hash)
    if check is None:
        raise ValueError(
            f"no passing judge check for the {judge_family} judge {judge_model} with prompt hash {judge_hash}: "
            "run `northstar eval judge-check` on the dev split first, and fix the judge until it passes"
        )
    return check


# --- the run -----------------------------------------------------------------------------------


@dataclass
class RunSummary:
    run_id: str
    out_dir: Path
    systems: list[str]
    n_items: int
    answered: int = 0  # predictions made in this call
    judged: int = 0  # judgements made in this call
    skipped: int = 0  # (item, system) pairs finished before this call
    errors: list[dict] = field(default_factory=list)
    stopped: str | None = None  # why the run stopped early
    spent_usd: float = 0.0  # cost of this call's answers and judgements, as if run live

    @property
    def complete(self) -> bool:
        return not self.errors and self.stopped is None


def _models_used(config: dict, systems: Sequence[str], answerer_family: str, judge_family: str) -> dict[str, str]:
    """The model ID for each role a run needs; empty where none is configured."""
    roles = [(answerer_family, "answerer"), (judge_family, "judge")]
    if "B4" in systems:
        roles.append((answerer_family, "worker_small"))
    return {
        f"{family}.{role}": resolve_model(config, ModelRequest("run", role, family, "", []))  # type: ignore[arg-type]
        for family, role in roles
    }


def run_qa(
    items: Sequence[QAItem],
    systems: Sequence[str | bl.Baseline],
    *,
    answerer_family: str,
    judge_family: str,
    port: ModelPort,
    config: dict,
    run_id: str,
    out_dir: Path | str,
    max_workers: int = 4,
    limit: int | None = None,
    allow_same_family: bool = False,
    dataset: str | None = None,
    split: str | None = None,
    held_out: bool = False,
    runs_root: Path | str | None = None,
    held_out_ledger: Path | str | None = None,
) -> RunSummary:
    """Answer and judge `items` with each system, appending results to `out_dir` as they finish.

    `systems` are names ("none", "B0".."B4") or objects with `system`, `family` and `answer(item)`.
    Call again with the same `out_dir` to resume; a call made with other settings than the first
    is refused. Raises ValueError when the judge's family is the answerer's (the family rule), when
    the split is `test` and `held_out` is not set, when a held-out run has a dirty git work tree or
    no passing judge check for its judge, and when a resume differs from the run it resumes; and
    ModelError when a model the run needs is not configured. On the test split B0 runs on
    `longmemeval.b0_subset` only (DESIGN §8, "Held-out sizes").
    """
    if judge_family == answerer_family and not allow_same_family:
        raise ValueError(f"a {judge_family} judge cannot score {answerer_family} work (the family rule)")
    items = limit_items(items, limit)
    if len({i.id for i in items}) != len(items):
        raise ValueError("item ids are not unique")
    port = measured(port)
    token_budget = int(config["eval"]["token_budget"])
    systems_in = [make_baseline(s, port, answerer_family, token_budget) if isinstance(s, str) else s for s in systems]
    names = [s.system for s in systems_in]
    if len(set(names)) != len(names):
        raise ValueError("a system is listed twice")
    for s in systems_in:
        if s.family != answerer_family:
            raise ValueError(f"{s.system} answers as {s.family}, not {answerer_family}")
    models = _models_used(config, names, answerer_family, judge_family)
    missing = [k for k, m in models.items() if not m]
    if missing:
        raise ModelError(
            f"no model is configured for {', '.join(missing)}; run `northstar models check` to see what your key reaches"
        )

    dataset_name = dataset or (items[0].dataset if items else "")
    split_name = split or (items[0].split if items else "")
    on_test = split_name == TEST_SPLIT or any(i.split == TEST_SPLIT for i in items)
    if on_test and not held_out:
        raise ValueError("a run on the test split is a held-out run: it needs held_out=True (--held-out)")
    out_dir = Path(out_dir)
    check = None
    if held_out:
        runs = Path(runs_root) if runs_root else eval_root() / "runs"
        check = require_held_out(models, judge_family, runs, out_dir, jd.judge_batch_size(config))
    subsets: dict[str, list[str]] = {}
    if on_test and "B0" in names and dataset_name.startswith("longmemeval"):
        b0_ids = [i.id for i in lme.b0_subset(list(items), config["eval"]["longmemeval"])]
        if len(b0_ids) < len(items):
            subsets["B0"] = b0_ids
    runs_on = {name: set(ids) for name, ids in subsets.items()}

    manifest = _update_manifest(
        out_dir, run_id, items, names, answerer_family, judge_family, allow_same_family, dataset_name, split_name,
        make_fingerprint(config, models, systems_in), subsets, held_out,
    )
    if held_out and check is not None:
        _record_held_out(out_dir, check, manifest, Path(held_out_ledger) if held_out_ledger else eval_root() / HELD_OUT_LEDGER)

    predictions = _Appender(out_dir / PREDICTIONS_FILE)
    judgements = _Appender(out_dir / JUDGEMENTS_FILE)
    done = {(r["item_id"], r["system"]) for r in read_jsonl(out_dir / JUDGEMENTS_FILE)}
    answered = {
        (p.item_id, p.system): p for p in load_predictions(out_dir) if not p.meta.get("error")
    }  # answered without error

    meter = _Meter(port)
    batch_size = jd.judge_batch_size(config)
    judge = jd.QAJudge(meter, judge_family, allow_same_family=allow_same_family, batch_size=batch_size)
    summary = RunSummary(run_id, out_dir, names, len(items))
    stop = threading.Event()
    judge_down = threading.Event()  # judging itself hit a stop error: the rest wait for a resume
    lock = threading.Lock()
    pending: list[tuple[QAItem, Prediction]] = []  # answered, waiting to be judged, in task order
    arrived: dict[int, tuple[QAItem, Prediction] | None] = {}  # finished tasks not yet in `pending`; None: nothing to judge
    next_seq = 0

    def release(seq: int, entry: tuple[QAItem, Prediction] | None, final: bool = False) -> None:
        """Move finished tasks into `pending` in task order, so the batches do not depend on which thread finished first."""
        nonlocal next_seq
        with lock:
            if seq >= 0:
                arrived[seq] = entry
            while next_seq in arrived:
                ready = arrived.pop(next_seq)
                next_seq += 1
                if ready is not None:
                    pending.append(ready)
            if final:  # a stop left gaps: what finished beyond them is still judged
                for k in sorted(arrived):
                    if arrived[k] is not None:
                        pending.append(arrived[k])  # type: ignore[arg-type]
                arrived.clear()

    def take_batch(final: bool) -> list[tuple[QAItem, Prediction]] | None:
        """A batch from `pending`: full, or whatever is left when `final`; never two answers to one item."""
        with lock:
            if judge_down.is_set():
                return None
            picked = jd.pick_batch(pending, batch_size, lambda entry: entry[0].id)
            if not picked or (len(picked) < batch_size and not final):
                return None
            batch = [pending[k] for k in picked]
            for k in reversed(picked):
                del pending[k]
            return batch

    def judge_batch(batch: list[tuple[QAItem, Prediction]]) -> None:
        meter.take()  # drop what an earlier failed judgement left on this thread
        try:
            results = judge.judge_many([(item, prediction) for item, prediction in batch])
        except FATAL as err:
            with lock:
                summary.stopped = summary.stopped or f"{type(err).__name__}: {err}"
            judge_down.set()
            stop.set()
            return
        except Exception as err:  # noqa: BLE001 - a failed batch is judged again on resume
            with lock:
                for item, prediction in batch:
                    summary.errors.append({"item": item.id, "system": prediction.system, "error": f"{type(err).__name__}: {err}"})
            return
        cost, latency = meter.take()
        for judgement in results:  # the call's cost and time are shared among the pairs it graded
            judgements.add(
                {**asdict(judgement), "judge_cost_usd": cost / len(batch), "judge_latency_s": latency / len(batch)}
            )
        with lock:
            summary.judged += len(batch)
            summary.spent_usd += cost

    def flush(final: bool = False) -> None:
        while (batch := take_batch(final)) is not None:
            judge_batch(batch)

    def work(seq: int, baseline: bl.Baseline, item: QAItem) -> None:
        if stop.is_set():
            return
        key = (item.id, baseline.system)
        try:
            prediction = answered.get(key)
            if prediction is None:
                prediction = _answer(baseline, item)
                predictions.add(asdict(prediction))
                with lock:
                    summary.answered += 1
                    summary.spent_usd += prediction.cost_usd
                if prediction.meta.get("error"):
                    with lock:
                        summary.errors.append({"item": item.id, "system": baseline.system, "error": prediction.meta["error"]})
                    release(seq, None)
                    flush()
                    return
            release(seq, (item, prediction))
        except FATAL as err:
            with lock:
                summary.stopped = summary.stopped or f"{type(err).__name__}: {err}"
            stop.set()
            return
        except Exception as err:  # noqa: BLE001 - one item's failure does not stop the run
            with lock:
                summary.errors.append({"item": item.id, "system": baseline.system, "error": f"{type(err).__name__}: {err}"})
            release(seq, None)
            flush()
            return
        flush()

    tasks = []
    for item in items:  # item by item: every system on this item before any on the next
        for baseline in systems_in:
            if baseline.system in runs_on and item.id not in runs_on[baseline.system]:
                continue
            if (item.id, baseline.system) in done:
                summary.skipped += 1
            else:
                tasks.append((baseline, item))
    pool = ThreadPoolExecutor(max_workers=max(1, max_workers))
    try:
        for future in [pool.submit(work, n, b, i) for n, (b, i) in enumerate(tasks)]:
            future.result()
    except BaseException:
        stop.set()
        pool.shutdown(wait=False, cancel_futures=True)
        raise
    pool.shutdown()
    release(-1, None, final=True)
    flush(final=True)  # what is left, also after a stop: answered work is judged, not left for a resume
    manifest["updated_at"] = _now()
    write_json(out_dir / RUN_FILE, manifest)
    return summary


def _answer(baseline: bl.Baseline, item: QAItem) -> Prediction:
    """The baseline's prediction; any failure other than a fatal one becomes an empty one.

    A call that failed after the vendor billed it keeps its cost, so a failed item is not free.
    """
    try:
        return baseline.answer(item)
    except FATAL:
        raise
    except Exception as err:  # noqa: BLE001
        meta = {"family": baseline.family, "baseline": baseline.system, "error": f"{type(err).__name__}: {err}"}
        billed = billed_result(err)
        if billed is None:
            return Prediction(item.id, baseline.system, "", meta=meta)
        return Prediction(
            item.id, baseline.system, "", usage=billed.usage, cost_usd=billed.cost_usd, latency_s=billed.latency_s, calls=1, meta=meta
        )


def _update_manifest(
    out_dir: Path,
    run_id: str,
    items: Sequence[QAItem],
    systems: Sequence[str],
    answerer_family: str,
    judge_family: str,
    allow_same_family: bool,
    dataset: str,
    split: str,
    fingerprint: dict,
    subsets: dict[str, list[str]],
    held_out: bool,
) -> dict:
    """Write run.json: what was asked and with what. A resumed run must match its first call."""
    old = load_run(out_dir)
    new_items = {i.id: {"id": i.id, "question_type": i.question_type, "abstention": i.abstention, "split": i.split} for i in items}
    if old is not None:
        for key, value in (("answerer_family", answerer_family), ("judge_family", judge_family)):
            if old[key] != value:
                raise ValueError(f"{out_dir} holds a run with {key} {old[key]!r}, not {value!r}; use another run id")
        if "fingerprint" not in old:
            raise ValueError(f"{out_dir} holds a run that did not record what it was made with; use another run id")
        changes = fingerprint_changes(old["fingerprint"], fingerprint)
        if changes:
            raise ValueError(f"{out_dir} was made with other settings: {'; '.join(changes)}; use another run id")
        fingerprint = merge_fingerprint(old["fingerprint"], fingerprint)
        new_items = {**{i["id"]: i for i in old["items"]}, **new_items}
        systems = list(dict.fromkeys([*old["systems"], *systems]))
        subsets = {**old.get("subsets", {}), **subsets}
        held_out = held_out or bool(old.get("held_out"))
    manifest = {
        "run_id": run_id,
        "dataset": dataset,
        "split": split,
        "answerer_family": answerer_family,
        "judge_family": judge_family,
        "allow_same_family": allow_same_family,
        "config_version": fingerprint["config_version"],
        "token_budget": fingerprint["token_budget"],
        "models": fingerprint["models"],
        "held_out": held_out,
        "fingerprint": fingerprint,
        "systems": list(systems),
        "subsets": subsets,  # systems that run on some of the items only: {system: [item ids]}
        "items": list(new_items.values()),
        "created_at": old["created_at"] if old else _now(),
        "updated_at": _now(),
    }
    write_json(out_dir / RUN_FILE, manifest)
    return manifest


def _record_held_out(out_dir: Path, check: tuple[Path, dict], manifest: dict, ledger: Path) -> None:
    """Keep the judge check with the run, so the report finds it, and log the held-out run."""
    path, raw = check
    own = out_dir / JUDGE_CHECK_FILE
    if path.resolve() != own.resolve():
        write_json(own, raw)
    fp = manifest["fingerprint"]
    _Appender(ledger).add(
        {
            "at": _now(),
            "run_id": manifest["run_id"],
            "dataset": manifest["dataset"],
            "split": manifest["split"],
            "systems": manifest["systems"],
            "n_items": len(manifest["items"]),
            "config_version": fp["config_version"],
            "git_commit": fp["git_commit"],
            "git_dirty": fp["git_dirty"],
            "judge_model": manifest["models"][f"{manifest['judge_family']}.judge"],
            "answer_prompt_hash": fp["answer_prompt_hash"],
            "judge_prompt_hash": fp["judge_prompt_hash"],
            "judge_check_at": raw.get("checked_at", ""),
            "bars": fp["bars"],
        }
    )


def run_scenario_qa(world: World, systems: Sequence[str | bl.Baseline], **kwargs) -> RunSummary:
    """The same run on a world's probes, each asked with the history up to its checkpoint."""
    items = [ask(world, probe) for probe in world.probes]
    kwargs.setdefault("dataset", items[0].dataset if items else f"scenario:{world.id}")
    return run_qa(items, systems, **kwargs)


# --- the judge's own test -----------------------------------------------------------------------


def run_judge_check(
    items: Sequence[QAItem],
    port: ModelPort,
    judge_family: str,
    generator_family: str,
    config: dict,
    out_dir: Path | str,
    *,
    allow_same_family: bool = False,
) -> dict:
    """Test the QA judge on wrong-but-on-topic, partial, vague and stale answers (note 09, finding 7).

    The generator writes a right answer and the wrong ones. The judge counts only when at least
    `judge.MIN_WRONG_PROBES` wrong answers were tested (else the result is "insufficient"), it accepted
    fewer than `eval.judge_false_accept_max` of them, and it accepted at least `judge.MIN_TRUE_ACCEPT` of
    the right ones. The Wilson 95% upper bound of the false-accept rate is reported. The result goes to
    `judge-check.json` in `out_dir` with the judge model, a hash of the judge prompt and rules, the
    dataset, the probe kinds and the judge batch size; the answers it judged go to `judge-probes.jsonl`.
    The probe answers are judged the way the judge is used, `eval.judge_batch_size` to a call: shuffled
    with `eval.seed`, so a call mixes items and kinds, and never two answers to one item in a call.
    """
    if judge_family == generator_family and not allow_same_family:
        raise ValueError(f"a {judge_family} judge cannot be tested on {generator_family} answers (the family rule)")
    items = list(items)
    bar = float(config["eval"]["judge_false_accept_max"])
    port = measured(port)
    probes = jd.make_probe_answers(items, port, generator_family)  # type: ignore[arg-type]
    batch_size = jd.judge_batch_size(config)
    judge = jd.QAJudge(port, judge_family, allow_same_family=allow_same_family, batch_size=batch_size)  # type: ignore[arg-type]
    meta = jd.meta_evaluate(judge, items, probes, seed=int(config["eval"]["seed"]))
    outcome = jd.verdict(meta, bar)
    kinds: dict[str, int] = {}
    for p in probes:
        kinds[p.kind] = kinds.get(p.kind, 0) + 1
    types: dict[str, int] = {}
    for item in items:
        key = item.question_type + (" (abstention)" if item.abstention else "")
        types[key] = types.get(key, 0) + 1
    result = {
        "judge_family": judge_family,
        "generator_family": generator_family,
        "judge_model": resolve_model(config, ModelRequest("check", "judge", judge_family, "", [])),  # type: ignore[arg-type]
        "prompt_hash": jd.prompt_hash(batch_size),
        "judge_batch_size": batch_size,
        "dataset": items[0].dataset if items else "",
        "split": items[0].split if items else "",
        "n_items": len(items),
        "question_types": types,
        "probe_kinds": kinds,
        "bar": bar,
        "min_wrong": jd.MIN_WRONG_PROBES,
        "min_true_accept": jd.MIN_TRUE_ACCEPT,
        "result": outcome,
        "passed": outcome == "passed",
        "config_version": config.get("config_version", ""),
        "checked_at": _now(),
        "meta": asdict(meta),
    }
    out_dir = Path(out_dir)
    write_json(out_dir / JUDGE_CHECK_FILE, result)
    probe_file = out_dir / JUDGE_PROBES_FILE
    probe_file.write_text("".join(json.dumps(asdict(p), ensure_ascii=False) + "\n" for p in probes), encoding="utf-8")
    return result
