"""The `northstar` command: checks, and the measurement harness (DESIGN §8, §9).

    northstar doctor
    northstar models check [--family F]
    northstar eval lme prepare --file PATH
    northstar eval run --dataset lme|pilot --answerer-family F --judge-family G [--dry-run] [--held-out]
    northstar eval judge-check --judge-family G --generator-family F
    northstar eval normal-use --projects-dir PATH
    northstar eval report --run RUN_ID

Nothing here prints an API key, an email or a login token, or the text of a chat. `capture install` never runs without an
explicit --settings or --plugin-dir path: no command here defaults to, or looks in, the real Claude Code configuration. Runs write under paths.eval_root(). Results
that hold text from chats are never written inside a git work tree unless `--allow-repo-path` says so,
and `normal-use` never reads a whole home folder. A run on the test split needs `--held-out`
(DESIGN §8).
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import ExitStack, contextmanager
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from northstar_agent_memory import __version__
from northstar_agent_memory import config as northstar_config
from northstar_agent_memory.capture import backfill as capture_backfill
from northstar_agent_memory.capture import ingest as capture_ingest
from northstar_agent_memory.capture import install as capture_install
from northstar_agent_memory.capture import scope, spool
from northstar_agent_memory.core import db as core_db
from northstar_agent_memory.core.history import SQLiteHistoryStore
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


def encryption_at_rest() -> tuple[bool, str]:
    """Whether the data folder is encrypted at rest, as real capture needs it (PL-3, MEMORY-ARCHITECTURE §3.1)."""
    if sys.platform != "darwin":
        return False, "not checked: this check reads FileVault, which is macOS only"
    status = filevault_status()
    if "FileVault is On" in status:
        return True, status
    return False, f"{status}; real capture stays off until FileVault is on"


def _bytes(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{int(size)} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{n} B"


def store_report(root: Path) -> list[dict]:
    """One entry per store: whether its file is there, its schema version beside the newest this program knows, and
    its size (with its write-ahead log). It only reads, and never creates a store."""
    report = []
    for name in core_db.STORES:
        path = core_db.store_path(name, root)
        entry: dict = {"name": name, "present": path.exists(), "latest": core_db.migration_files(name)[-1][0]}
        if entry["present"]:
            entry["size"] = sum(p.stat().st_size for p in (path, path.with_name(path.name + "-wal")) if p.exists())
            try:
                conn = sqlite3.connect(f"file:{quote(path.resolve().as_posix())}?mode=ro", uri=True)
                try:
                    entry["version"] = core_db.current_version(conn, name)
                finally:
                    conn.close()
            except sqlite3.Error as err:
                entry["error"] = str(err)
        report.append(entry)
    return report


def store_line(entry: dict) -> str:
    if not entry["present"]:
        return f"  {entry['name']}: not created yet"
    if "error" in entry:
        return f"  {entry['name']}: present, {_bytes(entry['size'])}, but unreadable ({entry['error']})"
    version, latest = entry["version"], entry["latest"]
    if version < latest:
        schema = f"schema v{version} (v{latest} is newest: it is migrated when the store opens)"
    elif version > latest:
        schema = f"schema v{version}, newer than this program knows (v{latest})"
    else:
        schema = f"schema v{version}"
    return f"  {entry['name']}: present, {schema}, {_bytes(entry['size'])}"


def print_stores() -> None:
    print("stores:")
    for entry in store_report(data_root()):
        print(store_line(entry))
    satisfied, detail = encryption_at_rest()
    enforced = "" if not os.environ.get("NORTHSTAR_HOME") else "; not enforced while NORTHSTAR_HOME is set"
    print(f"  encryption at rest: {'satisfied' if satisfied else 'NOT satisfied'} ({detail}){enforced}")


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
    print_stores()
    print_capture(config, full=False)
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


# --- capture -----------------------------------------------------------------------------------


def _when(epoch: float | None) -> str:
    if epoch is None:
        return "never"
    return datetime.fromtimestamp(epoch).astimezone().isoformat(timespec="seconds")


def spool_report(root: Path) -> dict:
    """The spool's size and what has not been ingested yet. It only reads (no text is shown) and creates nothing."""
    files = spool.spool_files(root)
    out: dict = {"files": 0, "bytes": 0, "pending": 0, "corrupt": 0, "oldest": None}
    for path in files:
        try:
            out["bytes"] += path.stat().st_size
            records, _, corrupt = spool.read_file(path)
        except OSError:
            continue
        out["files"] += 1
        out["pending"] += len(records)
        out["corrupt"] += corrupt
        for rec in records:
            if out["oldest"] is None or rec.recorded_at < out["oldest"]:
                out["oldest"] = rec.recorded_at
    return out


def history_report(root: Path) -> dict | None:
    """Sources and messages in history.db, by app. Read-only; None when there is no history.db or it cannot be read."""
    path = core_db.store_path("history", root)
    if not path.exists():
        return None
    try:
        conn = sqlite3.connect(f"file:{quote(path.resolve().as_posix())}?mode=ro", uri=True)
        try:
            rows = conn.execute(
                "SELECT s.app, COUNT(DISTINCT s.id), COUNT(m.id) FROM source s LEFT JOIN message m ON m.source_id = s.id GROUP BY s.app"
            ).fetchall()
            newest = conn.execute("SELECT MAX(occurred_at) FROM message").fetchone()[0]
        finally:
            conn.close()
    except sqlite3.Error:
        return None
    return {"apps": {app or "unknown": (sources, messages) for app, sources, messages in rows}, "newest": newest}


def last_log_error(root: Path) -> str | None:
    """The newest error line of the capture log, as written (it holds no turn text), or None."""
    path = spool.log_path(root)
    try:
        with path.open("rb") as fh:
            fh.seek(0, os.SEEK_END)
            fh.seek(max(fh.tell() - 65536, 0))
            lines = fh.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        parts = line.split(" ", 2)
        if len(parts) == 3 and parts[1] == "error":
            return line[:300]
    return None


def last_ingest_time(root: Path) -> float | None:
    """When the ingester last finished a drain: it saves its state file at the end of each one."""
    try:
        return spool.state_path(root).stat().st_mtime
    except OSError:
        return None


def install_report(root: Path) -> list[dict]:
    """Each recorded install, with the capture events its hooks cover and whether the interpreter they name is there."""
    out = []
    for item in capture_install.recorded_installs(root):
        target = Path(item["path"])
        hooks_file = target / "hooks" / "hooks.json" if item["kind"] == "plugin" else target
        interpreters = capture_install.hook_interpreters(hooks_file)
        out.append(
            {
                **item,
                "events": capture_install.installed_events(hooks_file),
                "missing_python": [p for p in interpreters if not Path(p).exists()],
            }
        )
    return out


def print_capture(config: dict, *, full: bool) -> None:
    """The capture section of `doctor` (full=False) and of `capture status` (full=True). Local reads only: no model, no
    chat text, and nothing is created."""
    root = data_root()
    print("capture (Claude Code):")
    folders = scope.personal_paths(config)
    if folders:
        print(f"  personal folders ({len(folders)}): " + ", ".join(str(p) + ("" if p.exists() else " (missing)") for p in folders))
    else:
        print(f"  personal folders: none set, so nothing is captured; list them as [capture] personal_paths in {northstar_config.settings_path()}")
    installs = install_report(root)
    if not installs:
        print("  hooks: not installed (`northstar capture install --settings PATH` or `--plugin-dir PATH`)")
    for item in installs:
        events = item["events"]
        if events is None:
            state = "the file cannot be read"
        elif not events:
            state = "no Northstar hooks in it any more"
        elif len(events) < len(capture_install.EVENTS):
            state = f"only {len(events)} of {len(capture_install.EVENTS)} events: {', '.join(events)}"
        else:
            state = f"all {len(events)} events"
        if item["missing_python"]:
            state += f"; the interpreter {item['missing_python'][0]} is gone: install again"
        print(f"  hooks: {item['kind']} {item['path']}: {state} (installed {item['at']})")
    stamped, why = spool.encryption_stamp(root)
    if stamped:
        print(f"  encryption stamp: valid ({why})")
    else:
        print(f"  encryption stamp: NOT valid, so the hooks write nothing: {why}")
    spooled = spool_report(root)
    waiting = f"{spooled['pending']} records waiting" + (f", the oldest from {spooled['oldest']}" if spooled["oldest"] else "")
    if spooled["corrupt"]:
        waiting += f", {spooled['corrupt']} unreadable lines"
    print(f"  spool: {waiting}" + (f" ({spooled['files']} files, {_bytes(spooled['bytes'])})" if full else ""))
    running = spool.lock_held(spool.lock_path(root))
    print(f"  ingester: {'running now' if running else 'not running'}; last ingest {_when(last_ingest_time(root))}")
    if full:
        history = history_report(root)
        if history is None:
            print("  history.db: no history yet")
        else:
            apps = history["apps"]
            total_sources = sum(s for s, _ in apps.values())
            total_messages = sum(m for _, m in apps.values())
            print(f"  history.db: {total_sources} sources, {total_messages} messages" + (f", newest {history['newest']}" if history["newest"] else ""))
            for app, (sources, messages) in sorted(apps.items()):
                print(f"    {app}: {sources} sources, {messages} messages")
    error = last_log_error(root)
    print(f"  capture log, last error: {error or 'none'}")


def cmd_capture_status(args: argparse.Namespace) -> int:
    print_capture(northstar_config.load(), full=True)
    return 0


def _print_plan(plan, dry_run: bool) -> None:
    if dry_run:
        print("dry run: nothing is written")
    for line in plan.lines():
        print(line)


def cmd_capture_install(args: argparse.Namespace) -> int:
    config = northstar_config.load()
    kind = "settings" if args.settings else "plugin"
    try:
        capture_install.refuse_duplicate(kind, data_root())  # a second way would record every turn twice
    except capture_install.InstallError as err:
        raise CliError(str(err)) from err
    python = capture_install.project_python()
    ok, detail = capture_install.check_command(python)
    print(f"check: {detail}" if ok else f"check FAILED: {detail}")
    if not ok and not args.dry_run:
        raise CliError("the hook command does not start, so nothing was installed; run `uv sync` in the repository, then try again")
    try:
        print(f"encryption at rest: {capture_install.check_encryption(data_root())}")  # PL-3: before anything is installed
        if args.settings:
            plan = capture_install.install_settings(args.settings, python, dry_run=args.dry_run)
        else:
            plan = capture_install.render_plugin(args.plugin_dir, python, dry_run=args.dry_run)
    except capture_install.InstallError as err:
        raise CliError(str(err)) from err
    _print_plan(plan, args.dry_run)
    target = args.settings or args.plugin_dir
    if kind == "settings":
        print("no other key in the settings file changes")
    if not args.dry_run:
        if kind == "settings":
            print("installed: new Claude Code sessions run the hooks" if plan.changed else "already installed: nothing changed")
        else:
            print("plugin folder written")
        stamp = spool.write_encryption_stamp(data_root())  # the hook writes nothing without it
        print(f"encryption stamp written: {stamp}")
        capture_install.record_install(kind, target, data_root())
    if kind == "plugin":
        for line in capture_install.plugin_commands(target):
            print(line)
    if not scope.personal_paths(config):
        print(f"note: no personal folders are set, so nothing is captured yet; list them as [capture] personal_paths in {northstar_config.settings_path()}")
    return 0


def cmd_capture_uninstall(args: argparse.Namespace) -> int:
    try:
        plan = capture_install.uninstall_settings(args.settings, dry_run=args.dry_run)
    except capture_install.InstallError as err:
        raise CliError(str(err)) from err
    _print_plan(plan, args.dry_run)
    if not args.dry_run:
        capture_install.forget_install("settings", args.settings, data_root())
        print(f"removed {sum(1 for c in plan.changes if c.action == 'remove')} Northstar hooks; nothing else in the file changed")
        waiting = spool_report(data_root())["pending"]
        if waiting:
            print(f"{waiting} spool records are still waiting: `northstar capture ingest` writes them")
        print("what was captured stays in history.db until you excise it")
    return 0


def cmd_capture_ingest(args: argparse.Namespace) -> int:
    if scope.hidden_run():
        print("this is one of Northstar's own runs: nothing is ingested")
        return 0
    try:
        result = capture_ingest.run()
    except core_db.EncryptionRequired as err:
        raise CliError(str(err)) from err
    if result is None:
        print("another ingester is running now; nothing done")
        return 0
    print(
        f"ingested {result.records} records: {result.messages} messages, {result.sources} new sources; "
        f"{result.duplicates} already stored, {result.skipped} make no message, {result.out_of_scope} out of scope, "
        f"{result.corrupt} unreadable, {result.errors} refused"
    )
    if result.reconciled or result.mismatches:
        print(f"reconciled with transcripts: {result.reconciled} messages added, {result.mismatches} turns differ (kept as captured)")
    return 0


class _DryRunStore:
    """The history store for a backfill that must write nothing: everything runs inside one transaction that is rolled
    back at the end, so counts such as "already stored" are the real ones. `batch()` is a no-op because the store
    then uses savepoints inside the open transaction."""

    def __init__(self, store: SQLiteHistoryStore) -> None:
        self._store = store

    def __getattr__(self, name: str):
        return getattr(self._store, name)

    @contextmanager
    def batch(self):
        yield


def backfill_dry_run(folder: Path, config: dict, progress):
    """Count what `backfill` would do. With a history.db, its rows are read inside a transaction that is rolled back;
    without one, a scratch store in a folder under the data root is used and removed (no row is ever committed)."""
    with ExitStack() as stack:
        if core_db.store_path("history", data_root()).exists():
            store = stack.enter_context(SQLiteHistoryStore())
        else:
            scratch = spool.capture_dir(data_root())
            scratch.mkdir(parents=True, mode=0o700, exist_ok=True)
            tmp = stack.enter_context(tempfile.TemporaryDirectory(prefix="dry-run-", dir=scratch))
            store = stack.enter_context(SQLiteHistoryStore(Path(tmp)))
        store.conn.execute("BEGIN IMMEDIATE")
        try:
            return capture_backfill.backfill(folder, _DryRunStore(store), config=config, progress=progress)
        finally:
            if store.conn.in_transaction:
                store.conn.execute("ROLLBACK")


def cmd_capture_backfill(args: argparse.Namespace) -> int:
    folder = Path(args.source).expanduser()
    if not folder.is_dir():
        raise CliError(f"{folder} is not a folder")
    resolved = folder.resolve()
    if resolved == Path.home().resolve() or resolved == Path(resolved.anchor):
        raise CliError(f"{folder} is a whole home folder or disk, not a folder of transcripts: name the folder that holds them")
    config = northstar_config.load()
    if not scope.personal_paths(config):
        raise CliError(f"no personal folders are set, so nothing would be captured; list them as [capture] personal_paths in {northstar_config.settings_path()}")
    try:
        if args.dry_run:
            print("dry run: counting only; nothing is written")
            backfill_dry_run(folder, config, lambda line: print(line.replace(" written", " would be written")))
        else:
            with SQLiteHistoryStore() as store:
                capture_backfill.backfill(folder, store, config=config, progress=print)
    except core_db.EncryptionRequired as err:
        raise CliError(str(err)) from err
    return 0


# --- parser ------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="northstar", description="Northstar: a memory and focus layer for the AI you already use.")
    top = parser.add_subparsers(dest="command", required=True)

    top.add_parser("doctor", help="show the data root, the six stores and encryption at rest, the route, the harness programs and logins, key status, cost caps and configured models").set_defaults(func=cmd_doctor)

    models = top.add_parser("models", help="model access").add_subparsers(dest="models_command", required=True)
    check = models.add_parser("check", help="list the models your keys can reach (changes nothing)")
    check.add_argument("--family", choices=list(FAMILIES))
    check.set_defaults(func=cmd_models_check)

    cap = top.add_parser("capture", help="capture for Claude Code: status, hooks install and removal, backfill, ingest").add_subparsers(dest="capture_command", required=True)
    cap.add_parser("status", help="personal folders, hooks, the spool, the ingester, what history.db holds and the capture log's last error (reads only)").set_defaults(func=cmd_capture_status)
    ci = cap.add_parser("install", help="put the capture hooks into a settings file or a plugin folder you name (never a default path)")
    where = ci.add_mutually_exclusive_group(required=True)
    where.add_argument("--settings", metavar="PATH", help="merge the hooks into this settings.json (a timestamped backup is kept beside it)")
    where.add_argument("--plugin-dir", metavar="PATH", help="write a local Claude Code plugin folder here, and print the commands that add it")
    ci.add_argument("--dry-run", action="store_true", help="print exactly what would change, and change nothing")
    ci.set_defaults(func=cmd_capture_install)
    cu = cap.add_parser("uninstall", help="remove only Northstar's hooks from a settings file")
    cu.add_argument("--settings", metavar="PATH", required=True)
    cu.add_argument("--dry-run", action="store_true", help="print what would be removed, and change nothing")
    cu.set_defaults(func=cmd_capture_uninstall)
    cb = cap.add_parser("backfill", help="import past Claude Code transcripts (sessions inside your personal folders only)")
    cb.add_argument("--from", dest="source", metavar="FOLDER", required=True, help="a folder laid out like ~/.claude/projects")
    cb.add_argument("--dry-run", action="store_true", help="count sessions in and out of scope and messages; write nothing")
    cb.set_defaults(func=cmd_capture_backfill)
    cap.add_parser("ingest", help="drain the capture spool into history.db now").set_defaults(func=cmd_capture_ingest)

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
