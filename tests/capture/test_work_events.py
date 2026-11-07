"""Work events from git: commits made during a captured session, on a temporary repository (MEMORY-ARCHITECTURE §2.2)."""

from __future__ import annotations

import os
import random
import string
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from northstar_agent_memory import paths
from northstar_agent_memory.capture import scope, work_events
from northstar_agent_memory.capture.work_events import last_seen, normalise_remote, record_commits, repo_id, repo_root
from northstar_agent_memory.core.history import SQLiteHistoryStore
from northstar_agent_memory.core.ports import WorkEvent
from northstar_agent_memory.transcript import Source

from . import assert_throwaway_root, write_settings

SESSION_START = "2026-03-02T09:00:00+00:00"
SESSION_END = "2026-03-02T12:00:00+00:00"


def git(repo: Path, *args: str, when: str | None = None) -> str:
    env = {
        **os.environ,
        "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "GIT_AUTHOR_NAME": "Robin", "GIT_AUTHOR_EMAIL": "robin@example.org",
        "GIT_COMMITTER_NAME": "Robin", "GIT_COMMITTER_EMAIL": "robin@example.org",
    }
    if when:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = when
    done = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main", "-C", str(repo), *args],
        capture_output=True, text=True, env=env, check=True, stdin=subprocess.DEVNULL,
    )
    return done.stdout.strip()


def commit(repo: Path, message: str, when: str, name: str = "file.txt") -> str:
    (repo / name).write_text(f"{message}\n{when}\n", encoding="utf-8")
    git(repo, "add", name)
    git(repo, "commit", "-m", message, when=when)
    return git(repo, "rev-parse", "HEAD")


@pytest.fixture(autouse=True)
def _throwaway_root(tmp_path):
    assert_throwaway_root()
    write_settings(tmp_path / "Personal")  # the personal folders: record_commits asks the scope gate itself
    yield
    assert_throwaway_root()


@pytest.fixture
def repo(tmp_path) -> Path:
    path = tmp_path / "Personal" / "energy-dash"
    path.mkdir(parents=True)
    git(path, "init")
    return path


@pytest.fixture
def store(tmp_path):
    s = SQLiteHistoryStore(tmp_path / "stores")
    s.add_source(Source(id="S1", kind="chat", app="claude-code"), scope="personal")
    yield s
    s.close()


def events(store) -> list[dict]:
    return [dict(r) for r in store.conn.execute("SELECT * FROM work_event ORDER BY seq")]


def snapshot(repo: Path) -> dict[str, tuple[int, int]]:
    """Every file under the repository with its size and modification time."""
    return {str(p.relative_to(repo)): (p.stat().st_size, p.stat().st_mtime_ns) for p in repo.rglob("*") if p.is_file()}


# --- recording -----------------------------------------------------------------------------------------------


def test_commits_made_during_the_session_become_medium_evidence_work_events(repo, store):
    before = commit(repo, "Before the session", "2026-03-02T08:00:00+00:00")
    one = commit(repo, "Add hourly averages\n\nlong body that is not the label", "2026-03-02T09:30:00+00:00")
    two = commit(repo, "Keep 1-minute readings for 7 days", "2026-03-02T10:15:00+00:00")
    report = record_commits(store, "S1", repo, session_started_at=SESSION_START, session_ended_at=SESSION_END)
    assert (report.found, report.recorded, report.skipped, report.error) == (2, 2, None, None)
    rows = events(store)
    assert [r["ref"] for r in rows] == [one, two]  # oldest first, and not the earlier commit
    assert before not in {r["ref"] for r in rows}
    assert {(r["kind"], r["evidence"], r["source_id"]) for r in rows} == {("commit", "medium", "S1")}
    assert datetime.fromisoformat(rows[0]["occurred_at"]) == datetime(2026, 3, 2, 9, 30, tzinfo=timezone.utc)
    import json

    assert json.loads(rows[0]["meta"])["label"] == "Add hourly averages"
    assert json.loads(rows[1]["meta"])["label"] == "Keep 1-minute readings for 7 days"
    assert json.loads(rows[0]["meta"])["repo"] == report.repo == repo_id(repo_root(repo))


def test_only_new_commits_are_recorded_the_next_time(repo, store):
    first = commit(repo, "One", "2026-03-02T09:10:00+00:00")
    record_commits(store, "S1", repo, session_started_at=SESSION_START)
    assert last_seen(store, repo_id(repo_root(repo))) == first
    again = record_commits(store, "S1", repo, session_started_at=SESSION_START)
    assert (again.found, again.recorded) == (0, 0)
    second = commit(repo, "Two", "2026-03-02T09:40:00+00:00")
    third = commit(repo, "Three", "2026-03-02T09:50:00+00:00")
    report = record_commits(store, "S1", repo, session_started_at=SESSION_START)
    assert report.recorded == 2
    assert [r["ref"] for r in events(store)] == [first, second, third]
    assert last_seen(store, repo_id(repo_root(repo))) == third


def test_a_commit_is_never_recorded_twice_even_for_another_session(repo, store):
    sha = commit(repo, "Shared", "2026-03-02T09:10:00+00:00")
    store.add_source(Source(id="S2", kind="chat", app="claude-code"), scope="personal")
    record_commits(store, "S1", repo, session_started_at=SESSION_START)
    report = record_commits(store, "S2", repo, session_started_at=SESSION_START)
    assert (report.found, report.recorded) == (0, 0)  # the repository's last seen commit is already this one
    assert [(r["ref"], r["source_id"]) for r in events(store)] == [(sha, "S1")]


def test_a_commit_already_recorded_without_a_repository_mark_is_counted_not_duplicated(repo, store):
    sha = commit(repo, "Seen before", "2026-03-02T09:10:00+00:00")
    ident = repo_id(repo_root(repo))
    store.append_work_event(
        WorkEvent(id=f"commit:{ident}:{sha}", source_id="S1", kind="commit", ref=sha, evidence="medium", meta={})
    )
    report = record_commits(store, "S1", repo, session_started_at=SESSION_START)
    assert (report.found, report.recorded, report.already_known) == (1, 0, 1)
    assert len(events(store)) == 1


def test_work_done_outside_the_session_is_not_claimed(repo, store):
    commit(repo, "Last week", "2026-02-20T09:00:00+00:00")
    commit(repo, "Next week", "2026-03-09T09:00:00+00:00")
    report = record_commits(store, "S1", repo, session_started_at=SESSION_START, session_ended_at=SESSION_END)
    assert report.found == 0 and events(store) == []


def test_with_nothing_seen_and_no_session_start_nothing_is_claimed(repo, store):
    commit(repo, "Some commit", "2026-03-02T09:10:00+00:00")
    report = record_commits(store, "S1", repo)
    assert report.skipped == "no_baseline" and events(store) == []


def test_a_known_last_commit_bounds_the_range_without_a_session_start(repo, store):
    first = commit(repo, "One", "2026-03-02T09:10:00+00:00")
    record_commits(store, "S1", repo, session_started_at=SESSION_START)
    second = commit(repo, "Two", "2026-03-02T09:20:00+00:00")
    report = record_commits(store, "S1", repo)
    assert report.recorded == 1 and [r["ref"] for r in events(store)] == [first, second]


def test_a_last_commit_that_was_rewritten_away_falls_back_to_the_time_bound(repo, store):
    first = commit(repo, "One", "2026-03-02T09:10:00+00:00")
    record_commits(store, "S1", repo, session_started_at=SESSION_START)
    git(repo, "commit", "--amend", "-m", "One, reworded", when="2026-03-02T09:10:00+00:00")
    report = record_commits(store, "S1", repo, session_started_at=SESSION_START)
    assert report.error is None and report.recorded == 1
    assert first in {r["ref"] for r in events(store)} and len(events(store)) == 2


def test_the_label_is_the_first_line_with_secrets_replaced(repo, store):
    rnd = random.Random(3)
    token = "ghp_" + "aQ7" + "".join(rnd.choice(string.ascii_letters + string.digits) for _ in range(33))
    commit(repo, f"Fix login, token {token} was committed", "2026-03-02T09:10:00+00:00")
    report = record_commits(store, "S1", repo, session_started_at=SESSION_START)
    import json

    label = json.loads(events(store)[0]["meta"])["label"]
    assert token not in label and "[secret removed: github_token]" in label
    assert dict(report.secrets) == {"github_token": 1}
    assert token not in str(events(store))


# --- not a repository, own folders, hidden runs, failures -------------------------------------------------------


def test_a_folder_that_is_not_a_repository_records_nothing(tmp_path, store):
    plain = tmp_path / "Personal" / "notes"
    plain.mkdir(parents=True)
    report = record_commits(store, "S1", plain, session_started_at=SESSION_START)
    assert report.skipped == "not_a_repository" and events(store) == []
    assert record_commits(store, "S1", tmp_path / "Personal" / "missing", session_started_at=SESSION_START).skipped == "not_a_repository"
    assert record_commits(store, "S1", None, session_started_at=SESSION_START).skipped == "not_a_repository"


def test_a_subfolder_of_a_repository_counts(repo, store):
    sub = repo / "src" / "pkg"
    sub.mkdir(parents=True)
    commit(repo, "In the repo", "2026-03-02T09:10:00+00:00")
    assert record_commits(store, "S1", sub, session_started_at=SESSION_START).recorded == 1


def test_a_repository_inside_the_data_root_is_northstars_own_and_skipped(store):
    own = paths.harness_cwd() / "run-1"
    own.mkdir(parents=True)
    git(own, "init")
    commit(own, "Own", "2026-03-02T09:10:00+00:00")
    assert record_commits(store, "S1", own, session_started_at=SESSION_START).skipped == "own_folder"
    assert events(store) == []


def test_a_folder_outside_the_personal_folders_is_refused_whoever_asks(tmp_path, store):
    work = tmp_path / "Work" / "billing"
    work.mkdir(parents=True)
    git(work, "init")
    commit(work, "Invoice run", "2026-03-02T09:30:00+00:00")
    report = record_commits(store, "S1", work, session_started_at=SESSION_START, session_ended_at=SESSION_END)
    assert (report.skipped, report.found, report.recorded) == ("out_of_scope", 0, 0) and events(store) == []
    # The folders the caller names are the ones that count, not the user's settings file.
    only_work = {"capture": {"personal_paths": [str(tmp_path / "Work")]}}
    assert record_commits(store, "S1", work, session_started_at=SESSION_START, config=only_work).recorded == 1
    nothing = {"capture": {"personal_paths": []}}
    assert record_commits(store, "S1", work, session_started_at=SESSION_START, config=nothing).skipped == "out_of_scope"


def test_a_personal_folder_that_holds_the_data_root_is_still_northstars_own(repo, store):
    own = paths.harness_cwd() / "run-2"
    own.mkdir(parents=True)
    git(own, "init")
    commit(own, "Own", "2026-03-02T09:30:00+00:00")
    covering = {"capture": {"personal_paths": [str(paths.data_root().parent)]}}
    assert record_commits(store, "S1", own, session_started_at=SESSION_START, config=covering).skipped == "own_folder"
    assert events(store) == []


def test_a_hidden_run_records_nothing(repo, store, monkeypatch):
    commit(repo, "Mine", "2026-03-02T09:10:00+00:00")
    monkeypatch.setenv(scope.HIDDEN_RUN_ENV, "1")
    assert record_commits(store, "S1", repo, session_started_at=SESSION_START).skipped == "hidden_run"
    assert events(store) == []


def test_a_git_timeout_or_failure_is_reported_never_raised(repo, store, monkeypatch):
    commit(repo, "Mine", "2026-03-02T09:10:00+00:00")
    real = subprocess.run

    def slow(argv, **kw):
        if "log" in argv:
            raise subprocess.TimeoutExpired(argv, kw.get("timeout", 0))
        return real(argv, **kw)

    monkeypatch.setattr(work_events.subprocess, "run", slow)
    report = record_commits(store, "S1", repo, session_started_at=SESSION_START, timeout=0.5)
    assert report.error is not None and "timed out" in report.error and events(store) == []
    monkeypatch.setattr(work_events.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError("no git")))
    assert record_commits(store, "S1", repo, session_started_at=SESSION_START).skipped == "not_a_repository"


def test_the_commands_are_read_only_and_short(repo, store, monkeypatch):
    commit(repo, "Mine", "2026-03-02T09:10:00+00:00")
    seen: list[tuple[list[str], dict]] = []
    real = subprocess.run

    def spy(argv, **kw):
        seen.append((argv, kw))
        return real(argv, **kw)

    monkeypatch.setattr(work_events.subprocess, "run", spy)
    record_commits(store, "S1", repo, session_started_at=SESSION_START)
    assert seen
    allowed = {"rev-parse", "config", "cat-file", "log"}
    for argv, kw in seen:
        sub = argv[argv.index("-C") + 2]
        assert sub in allowed, argv
        assert "--no-optional-locks" in argv
        assert kw["timeout"] <= 10 and kw["env"]["GIT_TERMINAL_PROMPT"] == "0" and kw["env"]["GIT_PAGER"] == "cat"


def test_the_repository_is_not_altered(repo, store):
    commit(repo, "One", "2026-03-02T09:10:00+00:00")
    commit(repo, "Two", "2026-03-02T09:20:00+00:00")
    (repo / "scratch.txt").write_text("untracked\n", encoding="utf-8")  # a dirty tree, to tempt a status refresh
    before = snapshot(repo)
    record_commits(store, "S1", repo, session_started_at=SESSION_START)
    record_commits(store, "S1", repo, session_started_at=SESSION_START)
    assert snapshot(repo) == before
    assert not (repo / ".git" / "index.lock").exists()


# --- naming a repository -------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://github.com/Robin/Energy-Dash.git", "github.com/robin/energy-dash"),
        ("git@github.com:Robin/Energy-Dash.git", "github.com/robin/energy-dash"),
        ("https://robin:s3cretpw@github.com/robin/energy-dash/", "github.com/robin/energy-dash"),
        ("ssh://git@example.org:2222/robin/dash.git", "example.org:2222/robin/dash"),
    ],
)
def test_remotes_are_normalised_without_credentials(url, expected):
    assert normalise_remote(url) == expected


def test_the_same_remote_names_the_same_repository_whatever_the_folder(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    for folder, url in ((a, "https://user:pw@example.org/robin/dash.git"), (b, "git@example.org:robin/dash.git")):
        folder.mkdir()
        git(folder, "init")
        git(folder, "remote", "add", "origin", url)
    assert repo_id(a) == repo_id(b)
    assert "pw" not in repo_id(a) and len(repo_id(a)) == 64


def test_a_repository_without_a_remote_is_named_without_its_absolute_path(repo):
    ident = repo_id(repo_root(repo))
    assert len(ident) == 64 and str(repo) not in ident
