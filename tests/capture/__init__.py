"""Helpers for the capture tests. Every fixture is invented: the folders, the sessions, the transcripts and the secrets.

Nothing here reads ~/.claude or any real Claude Code configuration; installation and settings live under the throwaway
data root that tests/conftest.py sets up (NORTHSTAR_HOME).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from northstar_agent_memory import paths
from northstar_agent_memory.capture import spool

T0 = datetime(2026, 3, 2, 9, 0, 0, tzinfo=timezone.utc).timestamp()  # the invented morning every fixture starts at
SESSION = "5e55a0a0-0000-4000-8000-000000000001"
FAKE_TOKEN = "ghp_" + "Ab1Cd2Ef3Gh4Ij5Kl6Mn7Op8Qr9St0Uv1Wx2"  # an invented GitHub-style token (36 characters after ghp_)


def write_settings(*personal: Path | str) -> None:
    """<data root>/settings.toml with [capture] personal_paths."""
    root = paths.data_root()
    root.mkdir(parents=True, exist_ok=True)
    listing = ", ".join(json.dumps(str(p)) for p in personal)
    (root / "settings.toml").write_text(f"[capture]\npersonal_paths = [{listing}]\n", encoding="utf-8")


def make_repo(base: Path, name: str = "energy-dash") -> Path:
    """An invented personal repository: a folder with a .git folder."""
    repo = base / name
    (repo / ".git").mkdir(parents=True)
    (repo / "src").mkdir()
    return repo


def event(name: str, cwd: Path | str, session: str = SESSION, **fields) -> dict:
    """A Claude Code hook payload, as it arrives on stdin (note 22 A1-A4)."""
    return {
        "session_id": session,
        "transcript_path": fields.pop("transcript_path", f"/nowhere/{session}.jsonl"),
        "cwd": str(cwd),
        "hook_event_name": name,
        **fields,
    }


def put(name: str, cwd: Path | str, at: float, session: str = SESSION, *, scrub: str | None = "secrets", **fields) -> dict:
    """Append one spool record as a hook would have, at epoch time `at`; the fields are the event's payload."""
    data = event(name, cwd, session, **fields)
    transcript = data.pop("transcript_path")
    for key in ("session_id", "cwd", "hook_event_name"):
        data.pop(key)
    record = spool.make_record(name, session, data, transcript_path=transcript, cwd=str(cwd), now=at)
    if scrub is None:
        record.pop("scrub")
    else:
        record["scrub"] = scrub
    spool.append(record)
    return record


# --- Claude Code transcript lines -------------------------------------------------------------------------------


def iso(at: float) -> str:
    return datetime.fromtimestamp(at, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def t_user(text: str, at: float, uuid: str, cwd: str = "/x", session: str = SESSION) -> dict:
    return {
        "type": "user", "uuid": uuid, "sessionId": session, "timestamp": iso(at), "cwd": cwd, "isSidechain": False,
        "message": {"role": "user", "content": text},
    }


def t_assistant(text: str, at: float, uuid: str, cwd: str = "/x", session: str = SESSION, msg: str | None = None) -> dict:
    return {
        "type": "assistant", "uuid": uuid, "sessionId": session, "timestamp": iso(at), "cwd": cwd, "isSidechain": False,
        "message": {"id": msg or "msg_" + uuid, "role": "assistant", "model": "claude-opus-5-5",
                    "content": [{"type": "text", "text": text}], "usage": {"input_tokens": 1, "output_tokens": 1}},
    }


def write_transcript(path: Path, *lines: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(line) for line in lines) + "\n", encoding="utf-8")
    return path


def assert_throwaway_root() -> None:
    """Every capture test runs against the throwaway data root of tests/conftest.py, never the real one."""
    home = os.environ.get("NORTHSTAR_HOME", "")
    assert home and "pytest-of-" in str(paths.data_root()), f"not a throwaway data root: {paths.data_root()}"
