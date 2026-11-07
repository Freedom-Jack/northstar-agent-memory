"""Work events from git: the commits made during a captured session (MEMORY-ARCHITECTURE §2.2, §5.2).

When a session's working folder is a git repository, `record_commits` records each new commit as a work event of that
session: kind "commit", ref the SHA, evidence "medium" (a commit made during a captured session; the evidence ladder
of note 20 gives "strong" to what the user authored or decided in their own words), label the commit's first line with
secrets replaced. It is written through the history store, the one writer of history.db.

- "New" means after the last commit already seen for that repository: the newest commit work event whose meta names
  the same repo, read from history.db itself, so no second place keeps state. `<last>..HEAD` is listed when the last
  one is still in the repository. A commit is kept only if it was made inside the session (at or after its start, and
  before its end when that is known), so work done between sessions is not claimed. With no commit seen yet, the
  session's start time is the only bound; with neither, nothing is recorded.
- Read with plain git commands (`rev-parse`, `config`, `cat-file`, `log`), no optional locks, no pager, no prompts, a
  short timeout. Nothing here can change the repository: no checkout, fetch, status refresh, hook or config write.
- A repository is named by the hash of its normalised remote (credentials, scheme and ".git" dropped), else of its
  folder relative to home, so no absolute path or password reaches the record (connectors §6, `context_ref`).
- A folder outside the personal folders (the scope gate, §7), a folder inside Northstar's data root, and a hidden run
  (NORTHSTAR_HIDDEN_RUN=1), are skipped (I24): `record_commits` asks the gate itself, whoever calls it. The ingester
  calls it when a captured session ends or settles (ingest.py); the backfill does not.
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from northstar_agent_memory import config as config_module
from northstar_agent_memory.capture import origin as _origin, scope
from northstar_agent_memory.capture.secrets import scrub, tally
from northstar_agent_memory.core.history import SQLiteHistoryStore
from northstar_agent_memory.core.ports import WorkEvent

DEFAULT_TIMEOUT_S = 5.0
DEFAULT_LIMIT = 200
_SEP = "\x1f"
_NO_GIT_ENV = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_COMMON_DIR", "GIT_NAMESPACE")


@dataclass(slots=True)
class Commit:
    sha: str
    committed_at: str  # ISO 8601 with offset, as git prints it
    committed_epoch: int
    subject: str  # the first line, as git printed it (not yet scrubbed)


@dataclass(slots=True)
class WorkEventReport:
    """What one call did. `skipped` is a reason the folder was not looked at; `error` a git failure (never raised)."""

    repo: str | None = None
    found: int = 0  # commits in range and inside the session
    recorded: int = 0
    already_known: int = 0
    skipped: str | None = None  # "hidden_run", "own_folder", "out_of_scope", "not_a_repository", "no_baseline"
    error: str | None = None
    secrets: Counter[str] = field(default_factory=Counter)


class GitError(RuntimeError):
    pass


def _env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in _NO_GIT_ENV}
    env.update(
        GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0", GIT_PAGER="cat", GIT_CONFIG_NOSYSTEM="1", LC_ALL="C",
        GIT_ASKPASS="true",
    )
    return env


def _git(root: Path, *args: str, timeout: float = DEFAULT_TIMEOUT_S) -> str:
    """One read-only git command in `root`. GitError on a non-zero exit, a timeout or a missing git."""
    argv = ["git", "--no-optional-locks", "-c", "core.fsmonitor=false", "-C", str(root), *args]
    try:
        done = subprocess.run(
            argv, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, env=_env(),
            stdin=subprocess.DEVNULL, check=False,
        )
    except subprocess.TimeoutExpired:
        raise GitError(f"git {args[0]} timed out after {timeout:g} s") from None
    except OSError as err:
        raise GitError(f"git could not run ({err.strerror or type(err).__name__})") from None
    if done.returncode != 0:
        raise GitError(f"git {args[0]} failed")
    return done.stdout


def repo_root(cwd: str | Path, timeout: float = DEFAULT_TIMEOUT_S) -> Path | None:
    """The top folder of the repository holding `cwd`, or None when it is not in one."""
    folder = Path(cwd).expanduser()
    if not folder.is_dir():
        return None
    try:
        out = _git(folder, "rev-parse", "--show-toplevel", timeout=timeout).strip()
    except GitError:
        return None
    return Path(out) if out else None


def normalise_remote(url: str) -> str:
    """host/owner/repo in lower case: scheme, user and password and a trailing ".git" dropped."""
    u = url.strip()
    u = re.sub(r"^[A-Za-z][A-Za-z0-9+.\-]*://", "", u)
    u = re.sub(r"^[^@/]*@", "", u)  # user:password@ or git@
    u = re.sub(r"^([^/:]+):(?!\d+/)", r"\1/", u)  # scp-style host:path
    u = re.sub(r"\.git/?$", "", u).rstrip("/")
    return u.lower()


def repo_id(root: Path, timeout: float = DEFAULT_TIMEOUT_S) -> str:
    """sha256 of the normalised origin remote; with no remote, of the folder relative to home (else the path)."""
    try:
        remote = _git(root, "config", "--get", "remote.origin.url", timeout=timeout).strip()
    except GitError:
        remote = ""
    if remote:
        key = "remote:" + normalise_remote(remote)
    else:
        try:
            key = "dir:" + str(root.resolve().relative_to(Path.home().resolve()))
        except ValueError:
            key = "dir:" + str(root.resolve())
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def last_seen(store: SQLiteHistoryStore, repo: str) -> str | None:
    """The newest commit already recorded for this repository, or None."""
    row = store.conn.execute(
        "SELECT ref FROM work_event WHERE kind = 'commit' AND json_extract(meta, '$.repo') = ? ORDER BY seq DESC LIMIT 1",
        (repo,),
    ).fetchone()
    return row["ref"] if row else None


def _epoch(value: str | None) -> float | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).timestamp()


def list_commits(
    root: Path, *, after_sha: str | None = None, timeout: float = DEFAULT_TIMEOUT_S, limit: int = DEFAULT_LIMIT
) -> list[Commit]:
    """Commits reachable from HEAD, oldest first; only those after `after_sha` when it is still in the repository."""
    rev = ["HEAD"]
    if after_sha and re.fullmatch(r"[0-9a-f]{7,64}", after_sha):
        try:
            _git(root, "cat-file", "-e", f"{after_sha}^{{commit}}", timeout=timeout)
            rev = [f"{after_sha}..HEAD"]
        except GitError:
            pass  # rewritten away or never here: fall back to the time bound
    out = _git(root, "log", f"-n{int(limit)}", f"--format=%H{_SEP}%cI{_SEP}%ct{_SEP}%s", *rev, "--", timeout=timeout)
    commits = []
    for line in out.splitlines():
        parts = line.split(_SEP, 3)
        if len(parts) == 4 and parts[2].isdigit():
            commits.append(Commit(parts[0], parts[1], int(parts[2]), parts[3]))
    commits.reverse()
    return commits


def record_commits(
    store: SQLiteHistoryStore,
    source_id: str,
    cwd: str | Path | None,
    *,
    session_started_at: str | None = None,
    session_ended_at: str | None = None,
    evidence: str = "medium",
    timeout: float = DEFAULT_TIMEOUT_S,
    limit: int = DEFAULT_LIMIT,
    config: Mapping[str, Any] | None = None,
    data_root: Path | None = None,
) -> WorkEventReport:
    """Record the repository's new commits made during the session as work events of `source_id` (which must exist).

    `cwd` must be in scope (`[capture] personal_paths` in `config`, the user's settings by default; `data_root` is for
    tests): a folder outside the personal folders is refused here, so no caller can record its commits.

    Never raises for a git problem: the report carries `skipped` or `error`. Safe to call again: a commit is
    recorded once, under an id made from the repository and the SHA.
    """
    report = WorkEventReport()
    if scope.hidden_run():
        report.skipped = "hidden_run"
        return report
    if not cwd or _origin.inside_data_root(cwd):
        report.skipped = "own_folder" if cwd else "not_a_repository"
        return report
    cfg = config_module.load() if config is None else config
    if not scope.in_scope(cwd, cfg, data_root=data_root):
        report.skipped = "out_of_scope"
        return report
    root = repo_root(cwd, timeout)
    if root is None:
        report.skipped = "not_a_repository"
        return report
    try:
        report.repo = repo = repo_id(root, timeout)
        last = last_seen(store, repo)
        start, end = _epoch(session_started_at), _epoch(session_ended_at)
        if last is None and start is None:
            report.skipped = "no_baseline"  # nothing seen and no session start to bound by: claim nothing
            return report
        commits = list_commits(root, after_sha=last, timeout=timeout, limit=limit)
    except GitError as err:
        report.error = str(err)
        return report

    for commit in commits:
        if start is not None and commit.committed_epoch < start:
            continue
        if end is not None and commit.committed_epoch > end:
            continue
        report.found += 1
        event_id = f"commit:{repo}:{commit.sha}"
        if store.conn.execute("SELECT 1 FROM work_event WHERE id = ?", (event_id,)).fetchone():
            report.already_known += 1
            continue
        label, findings = scrub(commit.subject.strip())
        tally(findings, report.secrets)
        added = store.append_work_event(
            WorkEvent(
                id=event_id, source_id=source_id, kind="commit", ref=commit.sha, evidence=evidence,  # type: ignore[arg-type]
                occurred_at=commit.committed_at, meta={"repo": repo, "label": label},
            )
        )
        report.recorded += int(added)
        report.already_known += int(not added)
    return report
