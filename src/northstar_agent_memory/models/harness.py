"""What the two headless routes share (DESIGN §1.4, revised 2026-10-29).

Hidden sub-tasks run through the harness the user already has, on the user's own plans:
Claude Code's headless mode for Claude (harness_claude.py) and Codex's `exec` for ChatGPT's
models (harness_codex.py). This module holds the parts both need: finding the program, the
empty folder a run starts in, the one place a process is started, the prompt text for a
multi-turn request, and the rules that turn a failure into the right error.

No dollars are billed on a plan, so a harness result costs 0.0. What Claude Code reports at
API list prices (`total_cost_usd`) rides along as `api_equivalent_usd`, for the cost ledger
only. Nothing from the environment goes into a message: an excerpt of a program's own
output has the values of key and token variables removed first, and no command line is
shown, since it holds the system prompt.
"""

from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import uuid
from collections.abc import Callable, Iterable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from northstar_agent_memory.config import settings_path
from northstar_agent_memory.models.port import (
    ModelError,
    ModelRefused,
    ModelResult,
    ModelUnavailable,
    NoCredentials,
    PlanLimitReached,
)
from northstar_agent_memory.paths import harness_cwd

DEFAULT_TIMEOUT_S = 600.0
# Every program the harness starts carries this marker, so the hooks it would run and the ingester skip it (I24).
HIDDEN_RUN_ENV = "NORTHSTAR_HIDDEN_RUN"


class HarnessNotFound(ModelUnavailable):
    """The program for a harness is not there, so no call can run (fatal for a run, like a missing model)."""


@dataclass(slots=True)
class HarnessResult(ModelResult):
    """A result from a headless call: `cost_usd` is 0.0 on a plan, and this is what the vendor's own meter
    estimated at API list prices (None when it gives none). Only the cost ledger reads it."""

    api_equivalent_usd: float | None = None


@dataclass(slots=True)
class Process:
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True, slots=True)
class Found:
    """The program a harness would run, and where it was found (for the doctor)."""

    path: Path
    source: str  # "settings", "PATH" or the app that bundles it


# --- finding the program -------------------------------------------------------------------------


def executable(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def find_binary(
    config: dict,
    *,
    product: str,
    setting: str,
    command: str,
    bundled: Callable[[], Iterable[Path]],
    bundled_source: str,
) -> Found:
    """The program for `product`: the path in [harness].<setting>, else `command` on PATH, else the
    first usable copy inside the desktop app. A path named in settings is never skipped silently."""
    configured = str(config.get("harness", {}).get(setting) or "").strip()
    if configured:
        path = Path(configured).expanduser()
        if executable(path):
            return Found(path, "settings")
        raise HarnessNotFound(f"harness.{setting} in {settings_path()} names a file that is not a program: {path}")
    on_path = shutil.which(command)
    if on_path:
        return Found(Path(on_path), "PATH")
    for candidate in bundled():
        if executable(candidate):
            return Found(candidate, bundled_source)
    raise HarnessNotFound(
        f"{product} was not found: put `{command}` on PATH, install the {bundled_source}, "
        f"or set harness.{setting} in {settings_path()}"
    )


def call_timeout(config: dict) -> float | None:
    """The longest one call may take, from [harness].timeout_s; None (no limit) when it is 0."""
    value = config.get("harness", {}).get("timeout_s", DEFAULT_TIMEOUT_S)
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        raise ModelError(f"harness.timeout_s must be a number of seconds, not {value!r}") from None
    return seconds if seconds > 0 else None


# --- running a program ---------------------------------------------------------------------------


def child_env(drop: Iterable[str], extra: Mapping[str, str] | None = None) -> dict[str, str]:
    """The environment for a run: a copy without `drop` (the variables that would put it on an API key or
    another provider instead of the plan login), plus `extra`, plus NORTHSTAR_HIDDEN_RUN=1: Northstar's own runs
    are never captured as the user's sessions (I24)."""
    dropped = set(drop)
    env = {name: value for name, value in os.environ.items() if name not in dropped}
    env.update(extra or {})
    env[HIDDEN_RUN_ENV] = "1"
    return env


@contextmanager
def working_folder() -> Iterator[Path]:
    """An empty folder for one run to start in: the harness folder under the data root when it is empty,
    else a fresh empty folder inside it, removed afterwards (DESIGN §1.4)."""
    root = harness_cwd()
    try:
        root.mkdir(parents=True, exist_ok=True)
        free = not any(root.iterdir())
        fresh = root if free else root / f"run-{uuid.uuid4().hex[:12]}"
        if not free:
            fresh.mkdir()
    except OSError as err:
        raise ModelError(f"could not prepare the empty folder for a harness run ({err.strerror or type(err).__name__})") from None
    try:
        yield fresh
    finally:
        if fresh != root:
            shutil.rmtree(fresh, ignore_errors=True)


def run_process(argv: list[str], *, stdin: str, cwd: Path, env: dict[str, str], timeout_s: float | None) -> Process:
    """Run one command to its end, `stdin` as its input; the only place the harness starts a process.

    It starts in a session of its own so that a timeout stops everything it started. Raises
    subprocess.TimeoutExpired (after the whole group is killed) and OSError (it could not start);
    callers turn both into a ModelError without the command line, which holds the system prompt.
    """
    with subprocess.Popen(
        argv,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        start_new_session=True,
    ) as proc:
        try:
            stdout, stderr = proc.communicate(stdin, timeout=timeout_s)
        except BaseException:
            _kill_group(proc)
            raise
    return Process(proc.returncode, stdout, stderr)


def _kill_group(proc: subprocess.Popen) -> None:
    try:
        if hasattr(os, "killpg"):
            os.killpg(proc.pid, signal.SIGKILL)
        else:
            proc.kill()
    except (ProcessLookupError, PermissionError):
        pass


# --- the prompt ----------------------------------------------------------------------------------


def render_prompt(messages: list[dict]) -> str:
    """The text a run reads on stdin. One user message goes as it is. A longer exchange sends the earlier
    turns first as a delimited transcript, then the last user message, which the model answers."""
    if not messages:
        raise ModelError("the request has no messages")
    for m in messages:
        if m.get("role") not in ("user", "assistant"):
            raise ModelError(f"a message has the role {m.get('role')!r}; only 'user' and 'assistant' are sent")
    *earlier, last = messages
    if last["role"] != "user":
        raise ModelError("the last message must come from the user")
    text = str(last.get("content", ""))
    if not text.strip():
        raise ModelError("the last user message is empty")
    if not earlier:
        return text
    turns = "\n".join(f'<turn role="{m["role"]}">\n{m.get("content", "")}\n</turn>' for m in earlier)
    return (
        f"<conversation_so_far>\n{turns}\n</conversation_so_far>\n\n"
        "The conversation so far is above, oldest turn first. Reply to the user's latest message, which follows.\n\n"
        f"{text}"
    )


# --- failures ------------------------------------------------------------------------------------

# Phrases the programs print, matched on lower-cased text with straight apostrophes. Claude Code's are
# from its own list of limit messages (and the errors page, code.claude.com/docs/en/errors); Codex's from
# the messages it ships. Checked in this order: limit, sign-in, model, refusal.
_LIMIT = re.compile(
    r"you(?:'ve| have)? (?:hit|reached) (?:your|the)\b|\busage limit|\bspend (?:limit|cap)|\bsession limit|\bweekly limit"
    r"|\brate[ -]?limit|\blimit (?:reached|exceeded)|out of (?:extra )?(?:usage|credits)|requires usage credits"
    r"|usage credits required|credit balance is too low|usage allocation has been disabled|seat type doesn't include"
    r"|shared budget|\bquota|too many requests|limiting requests|\b429\b|\b402\b"
)
_SIGN_IN = re.compile(
    r"not (?:logged|signed) in|(?:please )?run /login|login expired|sign in again|sign in to continue"
    r"|log out and sign in|authentication (?:required|failed|error)|authentication_failed|failed to authenticate"
    r"|invalid (?:api key|auth token|authentication credentials)|oauth (?:token|authentication) (?:has |is )?"
    r"(?:expired|revoked|disabled)|\bunauthori[sz]ed\b|\b401\b|\b403\b|no codex credentials|codex login|auth error"
    r"|(?:access token|authentication session) could not be refreshed"
)
_MODEL = re.compile(
    r"issue with the selected model|model_not_found|(?:unknown|invalid|unsupported) model\b"
    r"|model [`'\"]?[^\s`'\"]+[`'\"]? (?:was |is )?(?:not found|not available|not supported|does not exist|doesn't exist|unavailable)"
    r"|not available with the|may not exist or you may not have access|not supported when using codex"
)
_REFUSED = re.compile(r"(?:cyber|bio) policy|misalignment policy|policy violation|blocked due to")

LIMIT, SIGN_IN, MODEL, REFUSED, OTHER = "limit", "sign_in", "model", "refused", "other"
_STATUS_KIND = {401: SIGN_IN, 403: SIGN_IN, 402: LIMIT, 404: MODEL, 429: LIMIT}


def classify(text: str, status: int | None = None) -> str:
    """What kind of failure `text` (a program's own words) describes. The words come first, as they are
    the more specific; an HTTP status, when the program gives one, decides what the words do not."""
    lowered = text.lower().replace("’", "'")
    for kind, pattern in ((LIMIT, _LIMIT), (SIGN_IN, _SIGN_IN), (MODEL, _MODEL), (REFUSED, _REFUSED)):
        if pattern.search(lowered):
            return kind
    return _STATUS_KIND.get(status, OTHER) if isinstance(status, int) else OTHER


_SECRET_NAME = re.compile(r"(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIALS?)$")


def excerpt(text: str, limit: int = 300) -> str:
    """A short, one-line piece of a program's output for a message, with key and token values removed."""
    for name, value in os.environ.items():
        if len(value) >= 8 and _SECRET_NAME.search(name.upper()):
            text = text.replace(value, "[redacted]")
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


def failure(kind: str, vendor: str, detail: str, sign_in_hint: str) -> ModelError:
    """The error for a failed run. `detail` is the program's own words; a sign-in failure shows only the hint."""
    seen = excerpt(detail) or "no detail"
    if kind == LIMIT:
        return PlanLimitReached(f"{vendor}: your plan or workspace refused the call for usage or spend ({seen})")
    if kind == SIGN_IN:
        return NoCredentials(sign_in_hint)
    if kind == MODEL:
        return ModelUnavailable(f"{vendor}: the model is not available here ({seen})")
    if kind == REFUSED:
        return ModelRefused(f"{vendor} refused the request ({seen})")
    return ModelError(f"{vendor} failed ({seen})")


def int_of(value: object) -> int:
    """A token count from a program's JSON: an int, else 0 (a bool or a missing value is not a count)."""
    return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0
