"""The hook client: `python -m northstar_agent_memory.capture.hook <event>` (connectors-claude-code-and-codex.md §4, §5.1).

Claude Code runs this for each hook event and writes the event's JSON on stdin. In this order:
1. A hidden run (NORTHSTAR_HIDDEN_RUN=1) or a working folder out of scope: exit 0 at once, with no output and no file
   written (I24, the scope gate).
2. No valid encryption stamp under the data root (`capture install` writes it once the volume is encrypted, PL-3):
   nothing is written, and the capture log says why.
3. For an event that carries text (a prompt, a reply): append a marker record with no text in it (event, session,
   transcript path, sizes), then replace secrets in what will be kept, and append the record (spool.py). The marker
   comes first because the scrubber is regular expressions in C, which no thread can interrupt: a long input can run
   past the watchdog's thread timer, and a process that is ended mid-scrub would otherwise leave nothing behind and the
   turn would be lost without a trace. With the marker, reconciliation can fetch the turn from the transcript. No turn
   is written unscrubbed: if the scrubber cannot be loaded outside a test run, nothing is written.
4. Start the ingester in the background unless one is running (a lock file), and exit 0.

It never blocks the session: no database, no network, no model. A watchdog ends the process after a hard cap
(HARD_CAP_S) well under the hook timeouts of §4.3: a thread timer for a disk call that hangs, and an interval timer
(SIGALRM, where there is one) for a long scrub, whose handler the regular-expression engine lets run. Each logs what the
hook was doing. Every error is swallowed after one line in
the capture log; the session never sees a traceback, and the exit code is always 0 (§4.1 step 11). The hook prints
nothing, because the standard output of some hooks goes to the model (note 22 A2, A3); delivering memory on
UserPromptSubmit is a later build step.

Events (note 22 A1-A4, A12): SessionStart (source, model), UserPromptSubmit (prompt), Stop (last_assistant_message),
PreCompact and PostCompact (trigger; the summary is not kept, only its hash and size, since it is a model's text and
never an input to memory, I7), SessionEnd (reason), SubagentStop (a sidechain: its final message is kept on its own
branch). Any other event is ignored. Only the fields named in FIELDS are kept; tool inputs and the rest of a payload
are never spooled.

The hook runs in the session's working folder, and `python -m` would put that folder first on the module search path,
so a file there named like a standard-library module (dataclasses.py) or like this package would run instead of the real
one. The installer's command passes `-P` (no working folder on the path); a run without it removes the folder from the
path before anything is imported (the first lines below). The ingester is started the same way, from the data root.

Standard library, paths.py, scope.py and spool.py only: the hook pays for every import.
"""

from __future__ import annotations

import os
import sys

if __name__ == "__main__" and not sys.flags.safe_path:  # started without -P: the working folder is not code to import from
    try:
        _cwd = os.path.realpath(os.getcwd())
        sys.path[:] = [p for p in sys.path if os.path.realpath(p or ".") != _cwd]
    except OSError:  # the working folder is gone: only the empty entry could name it
        sys.path[:] = [p for p in sys.path if p]

import hashlib
import json
import signal
import threading
from pathlib import Path
from typing import Any, Callable, Mapping, TextIO

from northstar_agent_memory import paths
from northstar_agent_memory.capture import scope, spool

MAX_STDIN_CHARS = 16_000_000  # §4.1 step 1: beyond this, nothing is kept (the transcript reconciliation fills in)

# The most time one hook process may take, in seconds. The hook timeouts are 1.5 s (SessionEnd) to 8 s (§4.3); the
# client deadlines 0.5 s to 5 s. The work takes a few milliseconds.
HARD_CAP_S = {"SessionEnd": 0.4, "UserPromptSubmit": 1.0}
DEFAULT_CAP_S = 0.75

NO_SPAWN_ENV = "NORTHSTAR_CAPTURE_NO_SPAWN"  # tests and `doctor`: spool, but do not start the ingester

# The payload fields kept for each event.
FIELDS: dict[str, tuple[str, ...]] = {
    "SessionStart": ("source", "model"),
    "UserPromptSubmit": ("prompt", "prompt_id", "permission_mode"),
    "Stop": ("last_assistant_message", "stop_hook_active", "prompt_id"),
    "SubagentStop": ("last_assistant_message", "agent_id", "agent_type", "stop_hook_active"),
    "PreCompact": ("trigger",),
    "PostCompact": ("trigger",),
    "SessionEnd": ("reason",),
}


def build_payload(event: str, data: Mapping[str, Any]) -> dict[str, Any]:
    """The fields to keep for `event`, before scrubbing."""
    payload = {k: data[k] for k in FIELDS[event] if k in data and data[k] is not None}
    if event == "PostCompact" and isinstance(data.get("compact_summary"), str):
        payload["compact_summary"] = data["compact_summary"]  # replaced by its hash and size once scrubbed
    if event == "PreCompact" and data.get("custom_instructions"):
        payload["has_custom_instructions"] = True  # the user's own words are not kept here
    return payload


def _summarize_compaction(payload: dict[str, Any]) -> None:
    summary = payload.pop("compact_summary", None)
    if isinstance(summary, str):
        payload["compact_summary_sha256"] = hashlib.sha256(summary.encode("utf-8", "replace")).hexdigest()
        payload["compact_summary_chars"] = len(summary)


def read_event(stdin: TextIO) -> dict[str, Any] | None:
    """The event JSON from stdin, or None if it is empty, too large, or not a JSON object."""
    text = stdin.read(MAX_STDIN_CHARS + 1)
    if not text.strip():
        return None
    if len(text) > MAX_STDIN_CHARS:
        spool.log("hook", "an event was larger than the cap and was not spooled; the transcript will fill it in", level="warn")
        return None
    data = json.loads(text)
    return data if isinstance(data, dict) else None


def spawn_ingester(env: Mapping[str, str] | None = None, root: Path | None = None) -> bool:
    """Start `python -P -m northstar_agent_memory.capture.ingest --drain` detached, unless one holds the lock. True if started.

    It starts in the data root with `-P`, not in the session's working folder: the hook inherits that folder, and
    `python -m` would otherwise import a `dataclasses.py` or a `northstar_agent_memory` from it (code from the session's
    folder, run with the data root's secrets in reach). The ingester takes the lock itself and exits if it is held,
    so a race between two hooks starts at most one that works.
    """
    if spool.lock_held(spool.lock_path(root)):
        return False
    import subprocess

    subprocess.Popen(
        [sys.executable, "-P", "-m", "northstar_agent_memory.capture.ingest", "--drain"],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        close_fds=True, start_new_session=True, env=None if env is None else dict(env),
        cwd=str(paths.data_root() if root is None else root),
    )
    return True


# What the hook is doing, for the watchdog's log line (it runs on a timer, and has no other way to know).
_progress: dict[str, Any] = {"stage": "start", "event": None, "marker": False}

# The fields that carry the user's or the assistant's words: a marker is written before these are scrubbed.
TEXT_FIELDS: dict[str, tuple[str, ...]] = {
    "UserPromptSubmit": ("prompt",),
    "Stop": ("last_assistant_message",),
    "SubagentStop": ("last_assistant_message",),
}


def text_sizes(event: str, payload: Mapping[str, Any]) -> dict[str, int]:
    """The length in characters of each non-empty text field `event` carries (never the text)."""
    return {k: len(payload[k]) for k in TEXT_FIELDS.get(event, ()) if isinstance(payload.get(k), str) and payload[k]}


def capture(
    event: str,
    data: Mapping[str, Any],
    env: Mapping[str, str],
    *,
    config: Mapping[str, Any] | None = None,
    root: Path | None = None,
    spawn: Callable[..., Any] | None = spawn_ingester,
) -> bool:
    """Handle one parsed event. True if a record was spooled. Raises on error; `main` swallows it."""
    if event not in FIELDS:
        return False
    session_id = data.get("session_id")
    cwd = data.get("cwd")
    if not isinstance(session_id, str) or not session_id:
        return False
    if config is None:
        from northstar_agent_memory import config as config_module

        config = config_module.load()
    if not scope.in_scope(cwd, config, data_root=root):
        return False
    _progress.update(stage="stamp", event=event)
    valid, why = spool.encryption_stamp(root)
    if not valid:
        spool.log("hook", f"nothing was written: {why}", root=root)
        return False

    loaded = spool.load_scrubber()
    if loaded is None:
        spool.log("hook", "the secret scrubber could not be loaded: nothing was written", root=root)
        return False
    fn, scrub_name = loaded
    transcript = data.get("transcript_path")
    transcript = transcript if isinstance(transcript, str) else None
    payload = build_payload(event, data)
    sizes = text_sizes(event, payload)
    marker_id = None
    if sizes:
        _progress.update(stage="marker")
        marker = spool.make_marker(event, session_id, sizes, transcript_path=transcript, cwd=cwd)
        spool.append(marker, root=root, sync=False)  # in the system's cache is enough to outlive a killed process
        marker_id = marker["id"]
        _progress["marker"] = True
    _progress["stage"] = "scrub"
    payload = spool.scrub_value(payload, fn)
    if event == "PostCompact":
        _summarize_compaction(payload)
    _progress["stage"] = "spool"
    record = spool.make_record(event, session_id, payload, transcript_path=transcript, cwd=cwd, scrub=scrub_name)
    if marker_id is not None:
        record["after_marker"] = marker_id  # this record is the turn the marker stood for
    spool.append(record, root=root)
    if spawn is not None and env.get(NO_SPAWN_ENV, "") in ("", "0"):
        spawn(env)
    return True


def main(
    argv: list[str] | None = None,
    *,
    stdin: TextIO | None = None,
    env: Mapping[str, str] | None = None,
    config: Mapping[str, Any] | None = None,
    spawn: Callable[..., Any] | None = spawn_ingester,
) -> int:
    """Run one hook. Always returns 0, prints nothing."""
    argv = sys.argv[1:] if argv is None else argv
    env = os.environ if env is None else env
    try:
        if scope.hidden_run(env):
            return 0
        if stdin is None:
            sys.stdin.reconfigure(encoding="utf-8", errors="replace")  # the locale may not be UTF-8; a bad byte is not fatal
            stdin = sys.stdin
        data = read_event(stdin)
        if data is None:
            return 0
        event = argv[0] if argv else data.get("hook_event_name")
        _progress["event"] = event if isinstance(event, str) else None
        if isinstance(event, str):
            capture(event, data, env, config=config, spawn=spawn)
    except Exception as err:  # the session must never see a traceback
        spool.log("hook", f"{type(err).__name__}: {err}")
    return 0


class Watchdog:
    """Ends the process (`exit_fn(0)`) after `seconds`, whatever it is doing, and logs what it was doing.

    Two timers, because each covers what the other cannot: a thread timer fires while the main thread waits in a call
    that lets go of the interpreter lock (a disk call that hangs), and an interval timer (SIGALRM, in the main thread
    on POSIX) fires while it is inside a long regular-expression match, which holds the lock for the whole match but
    checks for signals as it goes. Whichever fires first acts, once.
    """

    def __init__(self, seconds: float, exit_fn: Callable[[int], Any] = os._exit) -> None:
        self.seconds, self._exit, self._fired = seconds, exit_fn, False
        self._signal_armed, self._old_handler = False, None
        self._timer = threading.Timer(seconds, self._fire)
        self._timer.daemon = True
        self._timer.start()
        if hasattr(signal, "setitimer") and threading.current_thread() is threading.main_thread():
            try:
                self._old_handler = signal.signal(signal.SIGALRM, lambda signum, frame: self._fire())
                signal.setitimer(signal.ITIMER_REAL, seconds)
                self._signal_armed = True
            except (ValueError, OSError):  # no signals here: the thread timer is all there is
                pass

    def _fire(self) -> None:
        if self._fired:
            return
        self._fired = True
        stage, event = _progress.get("stage"), _progress.get("event")
        note = "; a marker record stands for the turn, and reconciliation will fetch it from the transcript" if _progress.get("marker") else ""
        spool.log("hook", f"watchdog: ended the hook after {self.seconds:g} s during {stage} (event {event}){note}")
        self._exit(0)

    def cancel(self) -> None:
        self._timer.cancel()
        if self._signal_armed:
            self._signal_armed = False
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, self._old_handler if self._old_handler is not None else signal.SIG_DFL)


def arm_watchdog(seconds: float, exit_fn: Callable[[int], Any] = os._exit) -> Watchdog:
    """End the process with status 0 after `seconds` (see `Watchdog`). `cancel()` disarms it."""
    return Watchdog(seconds, exit_fn)


def cap_for(argv: list[str]) -> float:
    return HARD_CAP_S.get(argv[0], DEFAULT_CAP_S) if argv else DEFAULT_CAP_S


if __name__ == "__main__":
    arm_watchdog(cap_for(sys.argv[1:]))
    code = main()
    sys.stdout.flush()
    os._exit(code)  # do not wait for the interpreter to wind down
