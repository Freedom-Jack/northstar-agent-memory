"""GPT models through Codex's `exec`, on the user's own ChatGPT plan (DESIGN §1.4, revised 2026-10-29).

One `codex exec --json` call per request, with the prompt on stdin (`-`) and the answer read from the
JSONL events (learn.chatgpt.com/docs/non-interactive-mode): the last `agent_message` item is the answer,
`turn.completed` holds the token usage, and `turn.failed` or `error` the reason a run failed. A run
starts in an empty folder, read-only, with no saved session (`--ephemeral`), hooks off and web search off.
Codex has no system-prompt flag in `exec`; the system text goes in the documented `developer_instructions`
config key (`-c`), which Codex adds as a developer message beside its own instructions.

The prompt is kept lean (DESIGN §1.4: hidden sub-tasks on the user's plan should not waste it). Measured
on 2026-11-04 with `codex debug prompt-input` (codex-cli 0.165.0-alpha.1.2), the assembled prompt for a
one-word request is 67,371 characters: additional tool definitions 22,184, Codex's base instructions
21,454, skills instructions 10,725, multi-agent role and mode 2,779, the user's global AGENTS.md and
environment 1,281; a live one-word call used 15,310 input tokens. Northstar's requests use no tools and
want plain answers, so every run passes switches that bring it to about 13,100 characters:
`-c model_instructions_file=<short neutral text under the data root>` replaces the base instructions;
`--disable incremental_tools` (the tool block), `plugins`, `shell_tool`, `view_image` and `sleep_tool`
remove tools and their notes; `--enable omit_skill_descriptions` shrinks the skills block to about 5,900.
Codex renames features between versions and an unknown name makes the run fail, so a switch is passed only
when `codex features list` (a local command, no model call) names the feature and does not call it
removed. That list is read once per program and kept; if it cannot be read, the run goes without switches.

The reasoning effort is always set (`-c model_reasoning_effort`), so that the user's own default does
not apply: "medium" when the request gives none. low, medium, high, xhigh and max all exist for
the GPT-6 models in the catalog the CLI ships; "ultra" is left out, since it adds automatic task
delegation. A structured request writes its schema to a temporary file for `--output-schema`.

The call runs on the ChatGPT login: the API-key variables are left out of its environment. No price is
needed and `cost_usd` is 0.0, as there is no dollar bill on a plan. `max_tokens` is not sent (`exec` takes no cap).

Failures: not signed in raises NoCredentials; a usage limit, spend cap or empty workspace raises
PlanLimitReached; a model the plan does not serve raises ModelUnavailable; a policy block raises
ModelRefused; a timeout or anything else raises ModelError. A call that failed after the model answered
carries its tokens (budget.attach). `served_model` is the model asked for: `exec` does not say which answered.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
from contextlib import ExitStack
from dataclasses import dataclass, field
from pathlib import Path

from northstar_agent_memory.models import harness
from northstar_agent_memory.models.budget import attach, require_model
from northstar_agent_memory.models.harness import Found, HarnessResult, Process, classify, failure, int_of
from northstar_agent_memory.models.port import ModelError, ModelRequest, ModelResult, Usage
from northstar_agent_memory.models.schema import assert_strict
from northstar_agent_memory.paths import data_root

PRODUCT = "Codex"
SIGN_IN_ACTION = "sign in through the ChatGPT app"
SIGN_IN_HINT = f"Codex is not signed in: {SIGN_IN_ACTION}"
CODEX_APP_BINARY = Path("/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex")
# Codex's levels are the same names as ours, so each maps to itself ("ultra" is left out, see above).
EFFORTS = {"low": "low", "medium": "medium", "high": "high", "xhigh": "xhigh", "max": "max"}
DEFAULT_EFFORT = "medium"
# Left out of a run's environment: either would send it to an API key instead of the ChatGPT login.
DROPPED_ENV = ("OPENAI_API_KEY", "CODEX_API_KEY")
# What the base instructions are replaced with: Northstar's requests come from a program, with no tools.
BASE_INSTRUCTIONS = (
    "You are called by a program, not a person. Follow the developer instructions and answer only in the "
    "requested format.\n"
)
# Feature switches for a lean prompt (see the module docstring): (flag, feature name), in this order.
LEAN_FEATURES = (
    ("--disable", "incremental_tools"),
    ("--disable", "plugins"),
    ("--disable", "shell_tool"),
    ("--disable", "view_image"),
    ("--disable", "sleep_tool"),
    ("--enable", "omit_skill_descriptions"),
)
FEATURES_TIMEOUT_S = 30.0


# --- the program ---------------------------------------------------------------------------------


def find_codex_binary(config: dict) -> Found:
    """[harness].codex_binary, else `codex` on PATH, else the copy bundled with the ChatGPT app."""
    return harness.find_binary(
        config,
        product=PRODUCT,
        setting="codex_binary",
        command="codex",
        bundled=lambda: [CODEX_APP_BINARY],
        bundled_source="ChatGPT app",
    )


# --- one call ------------------------------------------------------------------------------------


def toml_string(text: str) -> str:
    """`text` as a TOML basic string, for a `-c key=value` override (Codex reads the value as TOML)."""
    return json.dumps(text, ensure_ascii=False).replace("\x7f", "\\u007f")


def base_instructions_path() -> Path:
    """Where the short base-instructions text lives: under the data root, not in the run's empty folder."""
    return data_root() / "harness-config" / "codex-base-instructions.md"


def write_base_instructions() -> Path:
    """Make sure the file holds BASE_INSTRUCTIONS (rewritten only when it differs) and return its path."""
    path = base_instructions_path()
    try:
        if not path.is_file() or path.read_text(encoding="utf-8") != BASE_INSTRUCTIONS:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(BASE_INSTRUCTIONS, encoding="utf-8")
    except OSError as err:
        raise ModelError(f"could not write the {PRODUCT} base instructions ({err.strerror or type(err).__name__})") from None
    return path


_features_cache: dict[str, frozenset[str]] = {}


def parse_features(text: str) -> frozenset[str]:
    """The feature names `codex features list` shows that are not removed. A line is `name  stage  enabled`,
    the stage being one or two words ("stable", "under development", "removed")."""
    names = set()
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[-1] in ("true", "false") and parts[1] != "removed":
            names.add(parts[0])
    return frozenset(names)


def available_features(binary: Path | str, timeout_s: float | None) -> frozenset[str]:
    """The features this program lists as not removed, asked once per program and kept (also when the answer is
    none). A failed or timed-out probe gives none: the run then has no switches rather than failing."""
    key = str(binary)
    if key not in _features_cache:
        names: frozenset[str] = frozenset()
        try:
            with harness.working_folder() as cwd:
                proc = harness.run_process(
                    [key, "features", "list"], stdin="", cwd=cwd, env=harness.child_env(DROPPED_ENV),
                    timeout_s=FEATURES_TIMEOUT_S if timeout_s is None else min(FEATURES_TIMEOUT_S, timeout_s),
                )
            if proc.returncode == 0:
                names = parse_features(proc.stdout)
        except (subprocess.TimeoutExpired, OSError, ValueError, ModelError):
            pass
        _features_cache[key] = names
    return _features_cache[key]


def lean_switches(features: frozenset[str]) -> list[str]:
    """The `--disable`/`--enable` flags for the features this Codex has."""
    return [part for flag, name in LEAN_FEATURES if name in features for part in (flag, name)]


def command(
    binary: Path | str,
    req: ModelRequest,
    model: str,
    effort: str,
    schema_path: Path | None = None,
    *,
    instructions_path: Path | None = None,
    switches: list[str] | None = None,
) -> list[str]:
    """The command line for one request. The prompt is not in it: `-` makes Codex read it from stdin."""
    argv = [
        str(binary),
        "exec",
        "--ephemeral",
        "--skip-git-repo-check",
        "-s",
        "read-only",
        "--json",
        "-m",
        model,
        "-c",
        f"model_reasoning_effort={toml_string(effort)}",
    ]
    if req.system.strip():
        argv += ["-c", f"developer_instructions={toml_string(req.system)}"]
    argv += ["--disable", "hooks", "-c", f"web_search={toml_string('disabled')}"]
    if instructions_path is not None:
        argv += ["-c", f"model_instructions_file={toml_string(str(instructions_path))}"]
    argv += switches or []
    if schema_path is not None:
        argv += ["--output-schema", str(schema_path)]
    return [*argv, "-"]


class CodexExec:
    """ModelPort for the "openai" family on the harness route. The program is found at the first call."""

    def __init__(self, config: dict) -> None:
        self.config = config

    def complete(self, req: ModelRequest) -> ModelResult:
        if req.family != "openai":
            raise ModelError(f"the Codex route got a {req.family!r} request")
        model = require_model(self.config, req)
        if req.effort is not None and req.effort not in EFFORTS:
            raise ModelError(f"unknown effort {req.effort!r}")
        effort = EFFORTS[req.effort] if req.effort is not None else DEFAULT_EFFORT
        if req.schema is not None:
            assert_strict(req.schema)
        prompt = harness.render_prompt(req.messages)
        binary = find_codex_binary(self.config).path
        started = time.monotonic()
        with ExitStack() as stack:
            schema_path = None
            if req.schema is not None:
                folder = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="northstar-codex-")))
                schema_path = folder / "schema.json"
                schema_path.write_text(json.dumps(req.schema, ensure_ascii=False), encoding="utf-8")
            argv = command(
                binary, req, model, effort, schema_path,
                instructions_path=write_base_instructions(),
                switches=lean_switches(available_features(binary, harness.call_timeout(self.config))),
            )
            proc = self._run(argv, prompt)
        return self._result(req, model, proc, time.monotonic() - started)

    def _run(self, argv: list[str], prompt: str) -> Process:
        timeout = harness.call_timeout(self.config)
        try:
            with harness.working_folder() as cwd:
                return harness.run_process(
                    argv, stdin=prompt, cwd=cwd, env=harness.child_env(DROPPED_ENV), timeout_s=timeout
                )
        except subprocess.TimeoutExpired:
            raise ModelError(f"{PRODUCT} did not finish within {timeout:g} s and was stopped") from None
        except (OSError, ValueError) as err:  # ValueError: a null byte in the command line
            raise ModelError(f"could not start {PRODUCT} ({getattr(err, 'strerror', None) or type(err).__name__})") from None

    def _result(self, req: ModelRequest, model: str, proc: Process, latency: float) -> ModelResult:
        run = _read_events(proc.stdout)
        result = HarnessResult(
            text="",
            parsed=None,
            usage=run.usage,
            cost_usd=0.0,
            latency_s=latency,
            family="openai",
            model=model,
            served_model=model,
            stop_reason="end_turn" if run.completed and run.failed is None else None,
            request_id=run.thread_id,
        )
        if run.failed is not None or not run.completed:
            raise _billed(_failure(run, proc), result)
        if run.answer is None:
            raise _billed(ModelError(f"{PRODUCT} finished without an answer"), result)
        result.text = run.answer
        if req.schema is None:
            return result
        try:
            parsed = json.loads(run.answer)
        except ValueError:
            raise _billed(ModelError("structured output is not valid JSON"), result) from None
        if not isinstance(parsed, dict):
            raise _billed(ModelError("structured output is not a JSON object"), result)
        result.parsed = parsed
        return result


@dataclass(slots=True)
class _Run:
    thread_id: str | None = None
    answer: str | None = None
    usage: Usage = field(default_factory=Usage)
    completed: bool = False
    failed: str | None = None  # the message of `turn.failed`
    errors: list[str] = field(default_factory=list)  # messages of `error` events
    other_output: list[str] = field(default_factory=list)  # stdout lines that are not events


def _read_events(stdout: str) -> _Run:
    """Read the JSONL events of `exec --json`; a line that is not an event is kept as plain output."""
    run = _Run()
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except ValueError:
            run.other_output.append(line)
            continue
        kind = event.get("type") if isinstance(event, dict) else None
        if not isinstance(kind, str):
            run.other_output.append(line)
        elif kind == "thread.started":
            run.thread_id = event.get("thread_id") if isinstance(event.get("thread_id"), str) else None
        elif kind == "item.completed":
            item = event.get("item")
            if isinstance(item, dict) and item.get("type") == "agent_message" and isinstance(item.get("text"), str):
                run.answer = item["text"]
        elif kind == "turn.completed":
            run.completed = True
            run.usage = _usage(event.get("usage"))
        elif kind == "turn.failed":
            error = event.get("error")
            message = error.get("message") if isinstance(error, dict) else error
            run.failed = str(message) if message else "no detail"
        elif kind == "error" and event.get("message"):
            run.errors.append(str(event["message"]))
    return run


def _usage(raw: object) -> Usage:
    """Codex counts cached input inside `input_tokens`, and reasoning inside `output_tokens`, as OpenAI does."""
    raw = raw if isinstance(raw, dict) else {}
    cached = int_of(raw.get("cached_input_tokens"))
    written = int_of(raw.get("cache_write_input_tokens"))  # none for OpenAI models; counted inside input if present
    return Usage(
        input_tokens=max(int_of(raw.get("input_tokens")) - cached - written, 0),
        output_tokens=int_of(raw.get("output_tokens")),
        cache_read_tokens=cached,
        cache_write_tokens=written,
    )


def _failure(run: _Run, proc: Process) -> ModelError:
    messages = list(dict.fromkeys([*run.errors, *([run.failed] if run.failed else [])]))
    text = "\n".join(messages) or "\n".join(p for p in (proc.stderr, *run.other_output) if p and p.strip())
    where = f"exit status {proc.returncode}" if proc.returncode else ""
    return failure(classify(text), PRODUCT, ": ".join(p for p in (where, text) if p), SIGN_IN_HINT)


def _billed(err: ModelError, result: ModelResult) -> ModelError:
    """Attach the result when the model had already been called, so the ledger records the plan's tokens."""
    u = result.usage
    return attach(err, result) if u.input_tokens + u.output_tokens + u.cache_read_tokens + u.cache_write_tokens else err


# --- the login, for the doctor -------------------------------------------------------------------

_MODE = re.compile(r"[A-Za-z0-9_-]{1,32}")


@dataclass(frozen=True, slots=True)
class CodexLogin:
    """Codex's login mode from auth.json. Only `auth_mode` is looked at: no other field of that file is read."""

    file_found: bool | None  # None: the file could not be read
    mode: str | None = None  # e.g. "chatgpt"


def codex_login() -> CodexLogin:
    home = os.environ.get("CODEX_HOME") or str(Path.home() / ".codex")
    try:
        raw = (Path(home) / "auth.json").read_text(encoding="utf-8")
    except FileNotFoundError:
        return CodexLogin(False)
    except OSError:
        return CodexLogin(None)
    try:
        mode = json.loads(raw).get("auth_mode")
    except (ValueError, AttributeError):
        return CodexLogin(True)
    return CodexLogin(True, mode if isinstance(mode, str) and _MODE.fullmatch(mode) else None)
