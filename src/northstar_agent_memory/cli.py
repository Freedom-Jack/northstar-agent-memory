"""The `northstar` command: checks, and the measurement harness (DESIGN §8, §9).

    northstar doctor
    northstar models check [--family F]
    northstar eval lme prepare --file PATH
    northstar eval run --dataset lme|pilot --answerer-family F --judge-family G [--dry-run] [--held-out]
    northstar eval judge-check --judge-family G --generator-family F
    northstar eval normal-use --projects-dir PATH
    northstar eval report --run RUN_ID

Nothing here prints an API key, an email or a login token, or the text of a chat. Runs write under paths.eval_root(). Results
that hold text from chats are never written inside a git work tree unless `--allow-repo-path` says so,
and `normal-use` never reads a whole home folder. A run on the test split needs `--held-out`
(DESIGN §8).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from northstar_agent_memory import __version__
from northstar_agent_memory import config as northstar_config
from northstar_agent_memory.eval import longmemeval as lme
from northstar_agent_memory.eval import normal_use, report, runner
from northstar_agent_memory.eval.scenarios.ledger import ask
from northstar_agent_memory.eval.scenarios.pilot import load_pilot
from northstar_agent_memory.eval.types import QAItem
from northstar_agent_memory.models.harness import Found, HarnessNotFound, call_timeout
from northstar_agent_memory.models.harness_claude import claude_login, find_claude_binary, sign_in_command
from northstar_agent_memory.models.harness_codex import SIGN_IN_ACTION as CODEX_SIGN_IN_ACTION
from northstar_agent_memory.models.harness_codex import codex_login, find_codex_binary
from northstar_agent_memory.models.keys import ENV_VARS, key_status
from northstar_agent_memory.models.port import FAMILIES, ModelError
from northstar_agent_memory.models.registry import build_port, resolve_route
from northstar_agent_memory.paths import data_root, eval_root, harness_cwd

FAMILY_CHOICES = [*FAMILIES, "stub"]
MANIFEST = "lme_manifest.json"
JUDGE_CHECK_ITEMS = 40  # items a judge check uses unless --n says otherwise: about 2 wrong answers each, and 60 are needed


class CliError(Exception):
    """A problem the person can fix; shown without a traceback."""


# --- privacy guards ----------------------------------------------------------------------------


def inside_git_work_tree(path: Path | str) -> bool:
    """Whether `path`, once resolved, is in a git work tree (it or a parent holds `.git`). The path need not exist."""
    here = Path(path).expanduser().resolve()
    return any((p / ".git").exists() for p in [here, *here.parents])


def refuse_repo_path(path: Path | str, allow: bool, what: str) -> None:
    """Results can hold text from chats, so they are not written where a commit could publish them."""
    if not allow and inside_git_work_tree(path):
        raise CliError(
            f"{what} ({Path(path).expanduser().resolve()}) is inside a git work tree, where a commit could publish it; "
            "choose a folder outside it, or pass --allow-repo-path"
        )


def add_allow_repo_path(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--allow-repo-path", action="store_true", help="allow results to be written inside a git work tree")


# --- doctor ------------------------------------------------------------------------------------


def filevault_status() -> str:
    """The first line of `fdesetup status`, or why it could not be read."""
    try:
        proc = subprocess.run(["fdesetup", "status"], capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return "unknown (fdesetup is not available)"
    lines = (proc.stdout or proc.stderr).strip().splitlines()
    return lines[0] if lines else "unknown"


def _usd(x: float) -> str:
    return f"${x:,.2f}"


def _program(find, config: dict) -> tuple[Found | None, str]:
    """The program a harness would run, or None and why there is none."""
    try:
        return find(config), ""
    except HarnessNotFound as err:
        return None, str(err)


def _claude_login_line(config: dict, binary: Found) -> str:
    login = claude_login(config)
    if login.signed_in is None:
        return f"unknown ({login.note})"
    if not login.signed_in:
        return f"not signed in; sign in once with `{sign_in_command(binary.path)}`"
    how = {
        "claude.ai": "your claude.ai plan",
        "oauth_token": "an OAuth token for your plan",
        "api_key": "an API key, not your plan: calls would be billed to the key",
        "api_key_helper": "an API key helper, not your plan: calls would be billed to the key",
        "third_party": "a cloud provider, not your plan",
    }.get(login.method or "")
    return "signed in" + (f" with {how}" if how else "") + (f", plan {login.plan}" if login.plan else "")


def _codex_login_line() -> str:
    login = codex_login()
    if login.file_found is None:
        return "auth.json could not be read"
    if not login.file_found:
        return f"no auth.json (not signed in, or the login is in the keychain); {CODEX_SIGN_IN_ACTION}"
    return f"auth_mode {login.mode}" if login.mode else "auth.json holds no auth_mode"


def print_harness(config: dict) -> None:
    """The harness programs and logins (local commands only: no model is called, and no email or token is shown)."""
    try:
        seconds = call_timeout(config)
    except ModelError as err:
        seconds, note = None, f" ({err})"
    else:
        note = f" (a call stops after {seconds:g} s)" if seconds else " (no time limit)"
    print(f"harness runs start in an empty folder, with hooks off and no saved transcript: {harness_cwd()}{note}")
    for name, find in (("claude", find_claude_binary), ("codex", find_codex_binary)):
        found, why = _program(find, config)
        if found is None:
            print(f"  {name}: not found ({why})")
            continue
        print(f"  {name}: {found.path}  (from {found.source})")
        print(f"    login: {_claude_login_line(config, found) if name == 'claude' else _codex_login_line()}")


def cmd_doctor(args: argparse.Namespace) -> int:
    config = northstar_config.load()
    budget = config.get("budget", {})
    print(f"northstar {__version__}")
    print(f"config version: {config.get('config_version', 'unknown')}")
    print(f"data root: {data_root()}  ({'exists' if data_root().exists() else 'not created yet'})")
    settings = northstar_config.settings_path()
    print(f"settings file: {settings}  ({'present' if settings.exists() else 'absent: defaults only'})")
    print(f"FileVault: {filevault_status()}")
    try:
        route = resolve_route(config)
    except ModelError as err:
        raise CliError(str(err)) from err
    if route == "harness":
        print("route: harness (hidden model calls run through Claude Code and Codex on your own plans: no API key, no dollar bill)")
    else:
        print("route: api (hidden model calls use the vendors' APIs and your keys, metered against the cost caps)")
    print(f'  change it with route.default = "harness" or "api" in {settings}')
    print_harness(config)
    print("API keys (used on the api route; where each would come from; the key is never shown):")
    for family in FAMILIES:
        status = key_status(family)
        hint = "" if status != "missing" else f"  (Keychain item northstar-{family}, or {ENV_VARS[family]})"
        print(f"  {family}: {status}{hint}")
    if route == "harness":
        print("monthly cost cap: not used on the harness route (your plans' own limits apply; a limit reached stops a run until the reset)")
    else:
        soft, hard = budget.get("monthly_soft_usd") or 0, budget.get("monthly_hard_usd") or 0
        if hard > 0:
            print(f"monthly cost cap: soft {_usd(soft)}, hard {_usd(hard)}")
        else:
            print("monthly cost cap: not set, so live model calls are refused until budget.monthly_hard_usd is set")
        print(f"run budget: {_usd(float(budget.get('run_default_usd') or 0))} unless --budget-usd says otherwise")
    print("models per role:")
    for family in FAMILIES:
        for role in ("answerer", "judge", "worker", "worker_small", "checker", "sim_user"):
            model = northstar_config.model_for(config, family, role)
            note = ""
            if not model:
                note = "not set"
            elif not northstar_config.price_for(config, model):
                note = "no price, so live calls are refused"
            print(f"  {family}.{role}: {model or '-'}{'  (' + note + ')' if note else ''}")
    return 0


# --- models check ------------------------------------------------------------------------------


def model_ids(family: str) -> list[str]:
    """The model IDs the configured key can reach, from the vendor's list endpoint."""
    from northstar_agent_memory.models.keys import get_api_key

    key = get_api_key(family)
    if family == "anthropic":
        import anthropic

        client = anthropic.Anthropic(api_key=key)
    else:
        import openai

        client = openai.OpenAI(api_key=key)
    return sorted({m.id for m in client.models.list()})


def cmd_models_check(args: argparse.Namespace) -> int:
    config = northstar_config.load()
    failed = False
    for family in [args.family] if args.family else list(FAMILIES):
        status = key_status(family)
        if status == "missing":
            print(f"{family}: no key (store one in the Keychain as northstar-{family}, or set {ENV_VARS[family]})")
            failed = True
            continue
        try:
            ids = model_ids(family)
        except Exception as err:  # noqa: BLE001 - say what failed, never the message (it may echo a key)
            code = getattr(err, "status_code", None)
            print(f"{family}: could not list models ({type(err).__name__}{f', HTTP {code}' if code else ''})")
            failed = True
            continue
        roles: dict[str, list[str]] = {}
        for role in ("answerer", "judge", "worker", "worker_small", "checker", "sim_user"):
            model = northstar_config.model_for(config, family, role)
            if model:
                roles.setdefault(model, []).append(role)
        print(f"{family}: {len(ids)} models reachable (key from {status})")
        for model in ids:
            used = f"  <- configured for {', '.join(roles[model])}" if model in roles else ""
            print(f"  {model}{used}")
        for model, used in roles.items():
            if model not in ids:
                print(f"  WARNING: {model} is configured for {', '.join(used)} but is not in the list")
    print("Nothing was changed. Put model IDs in defaults.toml through a release, or in settings.toml to try one.")
    return 1 if failed else 0


# --- eval lme prepare --------------------------------------------------------------------------


def manifest_path() -> Path:
    return eval_root() / MANIFEST


def make_port(config: dict, **kwargs):
    """The port for a run, with a setup mistake (such as an unknown route) reported plainly."""
    try:
        return build_port(config, **kwargs)
    except (ModelError, ValueError) as err:
        raise CliError(str(err)) from err


def cmd_lme_prepare(args: argparse.Namespace) -> int:
    path = Path(args.file).expanduser()
    if not path.is_file():
        raise CliError(f"{path} is not a file")
    try:
        lme.verify(path)
        records = lme.load(path)
    except ValueError as err:
        raise CliError(str(err)) from err
    config = northstar_config.load()
    seed = int(config["eval"]["seed"])
    selection = lme.select(lme.to_items(records), config["eval"]["longmemeval"], seed)
    meta = {
        "file": str(path.resolve()),
        "sha256": lme.sha256_of(path),
        "seed": seed,
        "config_version": config.get("config_version", ""),
        "selection_rules": config["eval"]["longmemeval"],
    }
    lme.write_manifest(selection, manifest_path(), meta)
    print(f"{path.name}: checksum matches the published file; {len(records)} records")
    for split, items in selection.items():
        types: dict[str, int] = {}
        for item in items:
            key = item.question_type + (" (abstention)" if item.abstention else "")
            types[key] = types.get(key, 0) + 1
        print(f"  {split}: {len(items)} items  " + ", ".join(f"{t} {n}" for t, n in sorted(types.items())))
    print(f"manifest: {manifest_path()}")
    return 0


# --- datasets ----------------------------------------------------------------------------------


def load_items(dataset: str, split: str) -> list[QAItem]:
    """The items of a dataset split: the LongMemEval subset a manifest names, or the pilot's probes."""
    if dataset == "pilot":
        world = load_pilot()
        probes = [p for p in world.probes if p.split == split]
        if not probes:
            raise CliError(f"the pilot has no {split!r} probes; it is a development set")
        return [ask(world, p) for p in probes]
    manifest = manifest_path()
    if not manifest.exists():
        raise CliError("no LongMemEval selection yet: run `northstar eval lme prepare --file PATH` first")
    info = json.loads(manifest.read_text(encoding="utf-8"))
    file = Path(info.get("meta", {}).get("file", "")) if info.get("meta") else Path("")
    if not file.is_file():
        raise CliError(f"the LongMemEval file the manifest names is gone ({file}); run `eval lme prepare` again")
    wanted = set(info.get("dev", [])) | set(info.get("test", []))  # load_selection needs both splits
    try:
        records = [r for r in lme.load(file) if r["question_id"] in wanted]
    except ValueError as err:
        raise CliError(str(err)) from err
    return lme.load_selection(manifest, lme.to_items(records))[split]


def parse_systems(text: str) -> list[str]:
    by_lower = {s.lower(): s for s in runner.SYSTEMS}  # "b3" and "B3" are one system; "none" stays lower case
    names = [by_lower.get(s.strip().lower(), s.strip()) for s in text.split(",") if s.strip()]
    bad = [n for n in names if n not in runner.SYSTEMS]
    if bad or not names:
        raise CliError(f"systems must be some of {', '.join(runner.SYSTEMS)}; got {text!r}")
    return list(dict.fromkeys(names))


def runs_dir(run_id: str) -> Path:
    return eval_root() / "runs" / run_id


def new_run_id(prefix: str) -> str:
    return f"{prefix}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"


# --- eval run ----------------------------------------------------------------------------------


def print_estimate(estimate: dict[str, dict], budget_usd: float) -> None:
    print(f"{'system':<8}{'items':>6}{'calls':>9}{'input tok':>13}{'output tok':>12}{'answer $':>11}{'judge $':>10}{'total $':>10}")
    def money(x: float | None) -> str:
        return "-" if x is None else f"{x:.2f}"

    total, priced = 0.0, True
    notes: set[str] = set()
    for name, e in estimate.items():
        t = e["total_usd"]
        priced = priced and t is not None
        total += t or 0.0
        notes.update(e["unpriced"])
        print(
            f"{name:<8}{e['items']:>6}{e['calls']:>9}{e['input_tokens']:>13,}{e['output_tokens']:>12,}"
            f"{money(e['answer_usd']):>11}{money(e['judge_usd']):>10}{money(t):>10}"
        )
    print(f"{'total':<8}{'':>6}{'':>9}{'':>13}{'':>12}{'':>11}{'':>10}{money(total if priced else None):>10}")
    for note in sorted(notes):
        print(f"  not priced: {note}")
    if priced and total > budget_usd:
        print(f"This is more than the run budget of {_usd(budget_usd)}: raise it with --budget-usd, or run fewer systems or items.")
    print("An estimate from token counts with assumed output sizes, for sizing a run; recorded calls cost nothing.")


def cmd_eval_run(args: argparse.Namespace) -> int:
    config = northstar_config.load()
    if args.held_out and args.split != "test":
        raise CliError("--held-out goes with --split test: the held-out data is looked at once, in a run that says so")
    if args.split == "test" and not args.held_out and not args.dry_run:
        raise CliError(
            "a run on the test split needs --held-out: it is a look at the held-out data, so it needs a clean git work tree "
            "and a passing judge check for the run's judge, and it is logged"
        )
    systems = parse_systems(args.systems)
    items = runner.limit_items(load_items(args.dataset, args.split), args.limit)
    if not items:
        raise CliError(f"the {args.dataset} {args.split} split has no items")
    if args.judge_family == args.answerer_family and not args.allow_same_family:
        raise CliError("the judge must be of another family than the answerer (the family rule)")
    budget = float(args.budget_usd if args.budget_usd is not None else config["budget"]["run_default_usd"])
    if args.dry_run:
        print(f"dry run: {len(items)} {args.dataset} {args.split} items, systems {', '.join(systems)}; no model is called")
        print_estimate(runner.estimate_cost(items, systems, args.answerer_family, args.judge_family, config), budget)
        return 0

    run_id = args.run_id or new_run_id(f"{args.dataset}-{args.split}-{args.answerer_family}")
    out_dir = runs_dir(run_id)
    refuse_repo_path(out_dir, args.allow_repo_path, "the run folder")
    port = make_port(config, run_id=run_id, mode="replay" if args.replay_only else "record", run_budget_usd=budget)
    try:
        summary = runner.run_qa(
            items,
            systems,
            answerer_family=args.answerer_family,
            judge_family=args.judge_family,
            port=port,
            config=config,
            run_id=run_id,
            out_dir=out_dir,
            max_workers=args.workers,
            allow_same_family=args.allow_same_family,
            dataset=items[0].dataset if items else args.dataset,
            split=args.split,
            held_out=args.held_out,
        )
    except (ModelError, ValueError) as err:
        raise CliError(str(err)) from err
    print(
        f"run {run_id}: {summary.answered} answered, {summary.judged} judged, {summary.skipped} already done, "
        f"{len(summary.errors)} failed; {_usd(summary.spent_usd)} counted this time"
    )
    for e in summary.errors[:5]:
        print(f"  failed: {e['system']} {e['item']}: {e['error'][:200]}")
    if summary.stopped:
        print(f"stopped early: {summary.stopped[:300]}")
    print(f"results: {out_dir}")
    if args.held_out:
        print(f"logged in the held-out ledger: {eval_root() / runner.HELD_OUT_LEDGER}")
    if not summary.complete:
        print(f"resume with: northstar eval run ... --run-id {run_id}")
    print(f"report: northstar eval report --run {run_id}")
    return 2 if summary.stopped else 1 if summary.errors else 0


# --- eval judge-check --------------------------------------------------------------------------


def cmd_judge_check(args: argparse.Namespace) -> int:
    config = northstar_config.load()
    if args.judge_family == args.generator_family and not args.allow_same_family:
        raise CliError("the judge must be of another family than the family that writes the test answers")
    items = runner.limit_items(load_items(args.dataset, args.split), args.n)
    run_id = args.run_id or new_run_id("judge-check")
    refuse_repo_path(runs_dir(run_id), args.allow_repo_path, "the judge-check folder")
    budget = float(args.budget_usd if args.budget_usd is not None else config["budget"]["run_default_usd"])
    port = make_port(config, run_id=run_id, mode="record", run_budget_usd=budget)
    try:
        result = runner.run_judge_check(
            items, port, args.judge_family, args.generator_family, config, runs_dir(run_id), allow_same_family=args.allow_same_family
        )
    except (ModelError, ValueError) as err:
        raise CliError(str(err)) from err
    m = result["meta"]

    def rate(x: float | None) -> str:
        return "-" if x is None else f"{x * 100:.1f}%"

    print(f"judge check {run_id}: {result['judge_family']} judge on {result['generator_family']} answers, {len(items)} items")
    print(
        f"  accepted {rate(m['false_accept_rate'])} of {m['n_negatives']} wrong answers (bar: below {result['bar'] * 100:.0f}%; "
        f"95% upper bound {rate(m['false_accept_upper95'])}; at least {result['min_wrong']} wrong answers needed)"
    )
    for kind, share in sorted(m["false_accept_by_kind"].items()):
        print(f"    {kind}: {rate(share)} of {m['n_by_kind'][kind]}")
    print(
        f"  accepted {rate(m['true_accept_rate'])} of {m['n_positives']} right answers "
        f"(at least {result['min_true_accept'] * 100:.0f}% needed)"
    )
    if result["result"] == "passed":
        print("  PASSED: this judge may count")
    elif result["result"] == "insufficient":
        print(f"  INSUFFICIENT: {m['n_negatives']} wrong answers were tested; use more items (--n) before this judge can count")
    else:
        print("  FAILED: this judge does not count yet")
    print(f"results: {runs_dir(run_id)}  (pass --run-id {run_id} to `eval run` to keep the check with a run)")
    return 0 if result["passed"] else 1


# --- eval normal-use ---------------------------------------------------------------------------


def cmd_normal_use(args: argparse.Namespace) -> int:
    root = Path(args.projects_dir).expanduser()
    if not root.is_dir():
        raise CliError(f"{root} is not a folder")
    resolved = root.resolve()
    if resolved == Path.home().resolve() or resolved == Path(resolved.anchor):
        raise CliError(f"{root} is a whole home folder or disk, not a folder of transcripts: name the folder that holds them")
    target = Path(args.out).expanduser() if args.out else normal_use.default_report_path()
    refuse_repo_path(target, args.allow_repo_path, "the report path")
    files = sum(1 for _ in resolved.rglob("*.jsonl"))
    print(f"{files} transcript files (*.jsonl) under {resolved}; reading them now")
    if not files:
        raise CliError(f"no transcript files under {root}")
    result = normal_use.analyse(root, since=args.since)
    target = result.save(target)
    weeks = result.weekly()
    w = result.window
    print(f"{w['sessions']} sessions on {w['days']} active days, {len(weeks)} weeks; no model was called")
    print(
        f"  continuing {sum(x.continuing for x in weeks)}, fresh {sum(x.fresh for x in weeks)}, "
        f"restarts {sum(x.restarts for x in weeks)}; passed half the window {sum(x.passed_half_window for x in weeks)}; "
        f"re-explanation candidates {sum(x.units for x in weeks)} units, correction candidates {sum(x.correction_candidates for x in weeks)}"
    )
    print(f"written to {target} (it holds text from the chats, so it stays under the data root unless --out says otherwise)")
    return 0


# --- eval report -------------------------------------------------------------------------------


def cmd_report(args: argparse.Namespace) -> int:
    out_dir = Path(args.run) if Path(args.run).is_dir() else runs_dir(args.run)
    refuse_repo_path(out_dir, args.allow_repo_path, "the report path")
    try:
        summary, md_path = report.write_report(out_dir)
    except FileNotFoundError as err:
        raise CliError(str(err)) from err
    print(report.to_markdown(summary))
    print(f"written to {md_path}")
    return 0


# --- parser ------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="northstar", description="Northstar: a memory and focus layer for the AI you already use.")
    top = parser.add_subparsers(dest="command", required=True)

    top.add_parser("doctor", help="show the data root, the route, the harness programs and logins, key status, cost caps and configured models").set_defaults(func=cmd_doctor)

    models = top.add_parser("models", help="model access").add_subparsers(dest="models_command", required=True)
    check = models.add_parser("check", help="list the models your keys can reach (changes nothing)")
    check.add_argument("--family", choices=list(FAMILIES))
    check.set_defaults(func=cmd_models_check)

    ev = top.add_parser("eval", help="the measurement harness").add_subparsers(dest="eval_command", required=True)

    lme_cmd = ev.add_parser("lme", help="LongMemEval").add_subparsers(dest="lme_command", required=True)
    prepare = lme_cmd.add_parser("prepare", help="verify the file and fix the dev and test subsets")
    prepare.add_argument("--file", required=True, help="longmemeval_s_cleaned.json")
    prepare.set_defaults(func=cmd_lme_prepare)

    run = ev.add_parser("run", help="answer and judge a dataset with the baselines")
    run.add_argument("--dataset", choices=["lme", "pilot"], required=True)
    run.add_argument("--split", choices=["dev", "test"], default="dev")
    run.add_argument("--systems", default=",".join(runner.SYSTEMS), help="comma-separated, from none, B0..B4")
    run.add_argument("--answerer-family", choices=FAMILY_CHOICES, required=True)
    run.add_argument("--judge-family", choices=FAMILY_CHOICES, required=True)
    run.add_argument("--limit", type=int, help="use only N items, spread over the question types")
    run.add_argument("--budget-usd", type=float, help="stop the run before it would spend more than this")
    run.add_argument("--workers", type=int, default=4)
    run.add_argument("--run-id", help="resume this run, or name a new one")
    run.add_argument("--dry-run", action="store_true", help="print the cost estimate and stop")
    run.add_argument("--replay-only", action="store_true", help="use recorded calls only; never call a model")
    run.add_argument("--allow-same-family", action="store_true", help="tests only: let the judge share the answerer's family")
    run.add_argument("--held-out", action="store_true", help="a look at the held-out (test) split: needs a clean work tree and a passing judge check")
    add_allow_repo_path(run)
    run.set_defaults(func=cmd_eval_run)

    jc = ev.add_parser("judge-check", help="test a judge on wrong-but-on-topic answers")
    jc.add_argument("--judge-family", choices=FAMILY_CHOICES, required=True)
    jc.add_argument("--generator-family", choices=FAMILY_CHOICES, required=True)
    jc.add_argument("--dataset", choices=["lme", "pilot"], default="lme")
    jc.add_argument("--split", choices=["dev", "test"], default="dev")
    jc.add_argument("--n", type=int, default=JUDGE_CHECK_ITEMS, help="items to use")
    jc.add_argument("--budget-usd", type=float)
    jc.add_argument("--run-id")
    jc.add_argument("--allow-same-family", action="store_true", help="tests only")
    add_allow_repo_path(jc)
    jc.set_defaults(func=cmd_judge_check)

    nu = ev.add_parser("normal-use", help="measures from Claude Code transcripts; no model calls")
    nu.add_argument("--projects-dir", required=True)
    nu.add_argument("--since", help="only sessions that start on or after this date (YYYY-MM-DD)")
    nu.add_argument("--out", help="where to write the JSON; default under the data root")
    add_allow_repo_path(nu)
    nu.set_defaults(func=cmd_normal_use)

    rep = ev.add_parser("report", help="tables for a run")
    rep.add_argument("--run", required=True, help="a run id, or a run folder")
    add_allow_repo_path(rep)
    rep.set_defaults(func=cmd_report)
    return parser


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except CliError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> None:
    sys.exit(run(argv))
