"""Claude through Claude Code's headless mode, on the user's own plan (DESIGN §1.4, revised 2026-10-29).

One `claude -p` call per request, with the prompt on stdin and the answer read from the JSON result
(code.claude.com/docs/en/headless, cli-reference, agent-sdk/typescript). A run starts in an empty
folder with hooks off, no tools and no saved transcript, so it is never captured as the user's
session (I24); `--safe-mode` also leaves out CLAUDE.md, skills, plugins, MCP servers and auto
memory, which `-p` would otherwise load from ~/.claude, and keeps the plan login (unlike `--bare`,
which reads only an API key). The system prompt replaces Claude Code's own.

The call runs on the plan login: the API-key and bearer-token variables, the cloud-provider switches
and the effort variable are left out of its environment (`ANTHROPIC_API_KEY` wins over the login in
`-p`, the provider switches win over both, and `CLAUDE_CODE_EFFORT_LEVEL` wins over `--effort`).
A request with `allow_fallback` off (measurement runs) sets `CLAUDE_CODE_DISABLE_REFUSAL_FALLBACK`,
so the model it names is the one that answers; `served_model` is read from `modelUsage`.

Effort goes in `--effort` (low, medium, high, xhigh, max, as on the API). `max_tokens` is not sent: the
CLI has no per-call cap, and `stop_reason` says when a reply was cut. No price is needed: a plan has no
dollar bill, so `cost_usd` is 0.0, and the CLI's own `total_cost_usd` (API list prices) is kept as
`api_equivalent_usd` for the ledger.

Failures: not signed in raises NoCredentials; a usage, session, rate or spend limit raises
PlanLimitReached; a model the plan does not serve raises ModelUnavailable; a refusal raises
ModelRefused; a timeout or anything else raises ModelError. A call that failed after the model
answered carries its tokens (budget.attach).
"""

from __future__ import annotations

import json
import re
import shlex
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from northstar_agent_memory.models import harness
from northstar_agent_memory.models.budget import attach, require_model
from northstar_agent_memory.models.harness import (
    LIMIT,
    SIGN_IN,
    Found,
    HarnessNotFound,
    HarnessResult,
    Process,
    classify,
    failure,
    int_of,
)
from northstar_agent_memory.models.port import ModelError, ModelRefused, ModelRequest, ModelResult, Usage
from northstar_agent_memory.models.schema import assert_strict

PRODUCT = "Claude Code"
EFFORTS = ("low", "medium", "high", "xhigh", "max")
# Left out of a run's environment: each would send it to an API key or another provider instead of the plan.
DROPPED_ENV = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX",
    "CLAUDE_CODE_USE_FOUNDRY",
    "CLAUDE_CODE_EFFORT_LEVEL",
)
NEUTRAL_SYSTEM = "You are a helpful assistant."  # for an empty system prompt, which Claude Code would not take as a replacement
AUTH_TIMEOUT_S = 30.0
# Typed kinds on a result (marked internal in the CLI's own schema, so only a shortcut for the words).
_TYPED_KINDS = {
    "usage_limit_reached": LIMIT,
    "model_requires_usage_credits": LIMIT,
    "long_context_credits_required": LIMIT,
    "gateway_signin_required": SIGN_IN,
    "gateway_session_expired": SIGN_IN,
    "api_key_auth_disabled": SIGN_IN,
    "org_disabled_credential": SIGN_IN,
    "invalid_credential_header": SIGN_IN,
    "provider_credentials": SIGN_IN,
}


# --- the program ---------------------------------------------------------------------------------


def _version_key(name: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", name))


def bundled_copies() -> list[Path]:
    """The copies of Claude Code inside the Claude app, newest version first (versions compare as numbers)."""
    root = Path.home() / "Library" / "Application Support" / "Claude" / "claude-code"
    copies: list[Path] = []
    try:
        versions = sorted(
            ((_version_key(d.name), d) for d in root.iterdir() if d.is_dir()), key=lambda kd: kd[0], reverse=True
        )
        for key, version_dir in versions:
            if not key:
                continue
            builds = sorted((b for b in version_dir.iterdir() if b.is_dir()), key=lambda b: b.stat().st_mtime, reverse=True)
            copies += [b / "claude.app" / "Contents" / "MacOS" / "claude" for b in builds]
    except OSError:
        pass
    return copies


def find_claude_binary(config: dict) -> Found:
    """[harness].claude_binary, else `claude` on PATH, else the newest copy bundled with the Claude app."""
    return harness.find_binary(
        config,
        product=PRODUCT,
        setting="claude_binary",
        command="claude",
        bundled=bundled_copies,
        bundled_source="Claude app",
    )


def sign_in_command(binary: Path | str) -> str:
    return shlex.join([str(binary), "auth", "login"])


def sign_in_hint(binary: Path | str) -> str:
    return f"Claude Code is not signed in: sign in once with `{sign_in_command(binary)}`"


# --- one call ------------------------------------------------------------------------------------


def command(binary: Path | str, req: ModelRequest, model: str) -> list[str]:
    """The command line for one request. The prompt is not in it: it goes on stdin."""
    argv = [
        str(binary),
        "-p",
        "--output-format",
        "json",
        "--no-session-persistence",
        "--settings",
        json.dumps({"disableAllHooks": True}),
        "--tools",
        "",
        "--system-prompt",
        req.system if req.system.strip() else NEUTRAL_SYSTEM,
        "--model",
        model,
    ]
    if req.effort is not None:
        argv += ["--effort", req.effort]
    if req.schema is not None:
        argv += ["--json-schema", json.dumps(req.schema, separators=(",", ":"), ensure_ascii=False)]
    return [*argv, "--safe-mode"]


def environment(req: ModelRequest) -> dict[str, str]:
    extra = {} if req.allow_fallback else {"CLAUDE_CODE_DISABLE_REFUSAL_FALLBACK": "1"}
    return harness.child_env(DROPPED_ENV, extra)


class ClaudeCodeHeadless:
    """ModelPort for the "anthropic" family on the harness route. The program is found at the first call."""

    def __init__(self, config: dict) -> None:
        self.config = config

    def complete(self, req: ModelRequest) -> ModelResult:
        if req.family != "anthropic":
            raise ModelError(f"the Claude Code route got a {req.family!r} request")
        model = require_model(self.config, req)
        if req.effort is not None and req.effort not in EFFORTS:
            raise ModelError(f"unknown effort {req.effort!r}")
        if req.schema is not None:
            assert_strict(req.schema)
        prompt = harness.render_prompt(req.messages)
        binary = find_claude_binary(self.config).path
        argv = command(binary, req, model)
        started = time.monotonic()
        proc = self._run(argv, prompt, environment(req))
        return self._result(req, model, proc, time.monotonic() - started, binary)

    def _run(self, argv: list[str], prompt: str, env: dict[str, str]) -> Process:
        timeout = harness.call_timeout(self.config)
        try:
            with harness.working_folder() as cwd:
                return harness.run_process(argv, stdin=prompt, cwd=cwd, env=env, timeout_s=timeout)
        except subprocess.TimeoutExpired:
            raise ModelError(f"{PRODUCT} did not finish within {timeout:g} s and was stopped") from None
        except (OSError, ValueError) as err:  # ValueError: a null byte in the command line
            raise ModelError(f"could not start {PRODUCT} ({getattr(err, 'strerror', None) or type(err).__name__})") from None

    def _result(self, req: ModelRequest, model: str, proc: Process, latency: float, binary: Path) -> ModelResult:
        data = _parse_result(proc.stdout)
        usage, per_model = _usage(data or {})
        cost = (data or {}).get("total_cost_usd")
        stop = (data or {}).get("stop_reason")
        session = (data or {}).get("session_id") or (data or {}).get("uuid")
        result = HarnessResult(
            text="",
            parsed=None,
            usage=usage,
            cost_usd=0.0,
            latency_s=latency,
            family="anthropic",
            model=model,
            served_model=_served_model(per_model, model),
            stop_reason=stop if isinstance(stop, str) else None,
            request_id=session if isinstance(session, str) else None,
            api_equivalent_usd=float(cost) if isinstance(cost, (int, float)) and not isinstance(cost, bool) else None,
        )
        subtype = (data or {}).get("subtype")
        if data is None or proc.returncode != 0 or data.get("is_error") is True or subtype not in (None, "success"):
            raise _billed(self._failure(data, proc, binary), result)
        if result.stop_reason == "refusal":
            raise _billed(ModelRefused(f"{result.served_model} refused the request"), result)
        if req.schema is None:
            text = data.get("result")
            result.text = text if isinstance(text, str) else ""
            return result
        output = data.get("structured_output")
        if output is None:
            raise _billed(ModelError(f"{PRODUCT} returned no structured output (stop reason {result.stop_reason})"), result)
        result.parsed = output
        result.text = json.dumps(output, ensure_ascii=False, separators=(",", ":"))
        return result

    def _failure(self, data: dict | None, proc: Process, binary: Path) -> ModelError:
        text = _failure_text(data, proc)
        fields = data or {}
        status, typed, subtype = fields.get("api_error_status"), fields.get("api_error"), fields.get("subtype")
        kind = _TYPED_KINDS.get(typed) if isinstance(typed, str) else None
        kind = kind or classify(text, status if isinstance(status, int) else None)
        if data is None:
            where = f"no JSON result, exit status {proc.returncode}"
        elif subtype not in (None, "success"):
            where = str(subtype)
        else:
            where = f"exit status {proc.returncode}" if proc.returncode else ""
        return failure(kind, PRODUCT, ": ".join(p for p in (where, text) if p), sign_in_hint(binary))


def _billed(err: ModelError, result: ModelResult) -> ModelError:
    """Attach the result when the model had already been called, so the ledger records the plan's tokens."""
    u = result.usage
    return attach(err, result) if u.input_tokens + u.output_tokens + u.cache_read_tokens + u.cache_write_tokens else err


def _parse_result(stdout: str) -> dict | None:
    """The result object of `--output-format json`: the whole output, else the last line that holds one.
    A list of messages (as `--verbose` prints) gives its last result."""
    text = stdout.strip()
    for candidate in [text, *reversed(text.splitlines())] if text else []:
        try:
            value = json.loads(candidate)
        except ValueError:
            continue
        if isinstance(value, list):
            value = next((v for v in reversed(value) if isinstance(v, dict) and v.get("type") == "result"), None)
        if isinstance(value, dict) and value.get("type") == "result":
            return value
    return None


def _usage(data: dict) -> tuple[Usage, dict]:
    """Tokens from `modelUsage`, which counts every model call of the run, else from `usage` (main loop only)."""
    per_model = data.get("modelUsage")
    per_model = {name: e for name, e in per_model.items() if isinstance(e, dict)} if isinstance(per_model, dict) else {}
    if per_model:
        total = Usage()
        for e in per_model.values():
            total += Usage(
                int_of(e.get("inputTokens")),
                int_of(e.get("outputTokens")),
                int_of(e.get("cacheReadInputTokens")),
                int_of(e.get("cacheCreationInputTokens")),
            )
        return total, per_model
    raw = data.get("usage") if isinstance(data.get("usage"), dict) else {}
    return (
        Usage(
            int_of(raw.get("input_tokens")),
            int_of(raw.get("output_tokens")),
            int_of(raw.get("cache_read_input_tokens")),
            int_of(raw.get("cache_creation_input_tokens")),
        ),
        {},
    )


def _served_model(per_model: dict, requested: str) -> str:
    """The model that wrote the most output (a tie goes to the one asked for), else the one asked for."""
    if not per_model:
        return requested
    return max(per_model, key=lambda name: (int_of(per_model[name].get("outputTokens")), name == requested))


def _failure_text(data: dict | None, proc: Process) -> str:
    parts: list[str] = []
    if data is not None:
        if data.get("is_error") is True and isinstance(data.get("result"), str):
            parts.append(data["result"])
        if isinstance(data.get("errors"), list):
            parts += [str(e) for e in data["errors"]]
    parts.append(proc.stderr)
    if data is None:
        parts.append(proc.stdout)
    return "\n".join(p for p in parts if p and p.strip())


# --- the login, for the doctor -------------------------------------------------------------------

_AUTH_METHODS = frozenset({"none", "claude.ai", "oauth_token", "api_key", "api_key_helper", "third_party"})
_PLAN = re.compile(r"[A-Za-z0-9_-]{1,24}")


@dataclass(frozen=True, slots=True)
class ClaudeLogin:
    """What `claude auth status` says, cut down to what is safe to show: no email, organization or token."""

    signed_in: bool | None  # None: could not tell
    method: str | None = None
    plan: str | None = None
    note: str = ""


def claude_login(config: dict) -> ClaudeLogin:
    """Ask the program whether it is signed in (a local command; no model is called). It runs in the same
    environment a call would, so it reports the login a call would use."""
    try:
        binary = find_claude_binary(config).path
    except HarnessNotFound:
        return ClaudeLogin(None, note="no program to ask")
    try:
        with harness.working_folder() as cwd:
            proc = harness.run_process(
                [str(binary), "auth", "status"],
                stdin="",
                cwd=cwd,
                env=harness.child_env(DROPPED_ENV),
                timeout_s=AUTH_TIMEOUT_S,
            )
    except (subprocess.TimeoutExpired, OSError, ModelError):
        return ClaudeLogin(None, note="`auth status` did not answer")
    try:
        data = json.loads(proc.stdout)
    except ValueError:
        data = None
    data = data if isinstance(data, dict) else {}
    signed_in = data["loggedIn"] if isinstance(data.get("loggedIn"), bool) else proc.returncode == 0
    method = data.get("authMethod")
    plan = data.get("subscriptionType")
    return ClaudeLogin(
        signed_in,
        method if method in _AUTH_METHODS else None,
        plan if isinstance(plan, str) and _PLAN.fullmatch(plan) else None,
    )
