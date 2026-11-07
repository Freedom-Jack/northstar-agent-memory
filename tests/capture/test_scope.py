"""The scope gate and the self-capture guard (connectors-claude-code-and-codex.md §7, §11; I24)."""

from __future__ import annotations

import os

import pytest

from northstar_agent_memory import paths
from northstar_agent_memory.capture import scope
from northstar_agent_memory.models import harness

from . import assert_throwaway_root, make_repo


@pytest.fixture(autouse=True)
def _throwaway_root():
    assert_throwaway_root()
    yield
    assert_throwaway_root()


def cfg(*personal) -> dict:
    return {"capture": {"personal_paths": [str(p) for p in personal]}}


@pytest.fixture
def home(tmp_path):
    base = tmp_path / "personal"
    base.mkdir()
    return base


# --- in_scope -------------------------------------------------------------------------------------------------


def test_a_folder_inside_a_personal_path_is_in_scope(home):
    repo = make_repo(home)
    assert scope.in_scope(repo, cfg(home))
    assert scope.in_scope(repo / "src", cfg(home))
    assert scope.in_scope(str(home), cfg(home))  # the personal folder itself


def test_a_folder_outside_every_personal_path_is_out_of_scope(home, tmp_path):
    elsewhere = tmp_path / "work" / "employer-repo"
    elsewhere.mkdir(parents=True)
    assert not scope.in_scope(elsewhere, cfg(home))
    assert not scope.in_scope(tmp_path / "personal-notes", cfg(home))  # a sibling that only shares a name prefix


def test_no_setting_means_nothing_is_captured(home):
    assert not scope.in_scope(home, {})
    assert not scope.in_scope(home, {"capture": {}})
    assert not scope.in_scope(home, {"capture": {"personal_paths": []}})


def test_the_setting_may_be_one_string_and_bad_entries_are_ignored(home):
    assert scope.in_scope(home, {"capture": {"personal_paths": str(home)}})
    assert scope.in_scope(home, {"capture": {"personal_paths": [7, None, "", "relative/path", str(home)]}})
    assert not scope.in_scope(home, {"capture": {"personal_paths": 5}})
    assert not scope.in_scope(home, {"capture": "oops"})


def test_a_missing_or_relative_working_folder_is_out_of_scope(home):
    for cwd in (None, "", "   ", 7, "relative/dir", "."):
        assert not scope.in_scope(cwd, cfg(home))


def test_a_tilde_in_the_setting_is_expanded(home, monkeypatch):
    monkeypatch.setenv("HOME", str(home.parent))
    repo = make_repo(home)
    assert scope.in_scope(repo, {"capture": {"personal_paths": ["~/personal"]}})
    assert not scope.in_scope(repo, {"capture": {"personal_paths": ["~/other"]}})


def test_a_worktree_under_a_personal_repository_is_in_scope(home):
    repo = make_repo(home)
    worktree = repo / ".claude" / "worktrees" / "fix-readings"
    worktree.mkdir(parents=True)
    assert scope.in_scope(worktree, cfg(home))
    assert scope.in_scope(worktree / "src", cfg(home))
    assert scope.project_scope(worktree, cfg(home)) == "project:energy-dash"


def test_symlinks_are_resolved_before_the_check(home, tmp_path):
    outside = tmp_path / "employer"
    outside.mkdir()
    inside = home / "proj"
    inside.mkdir()
    (home / "looks-personal").symlink_to(outside)  # inside the personal folder by name, outside by place
    (tmp_path / "looks-elsewhere").symlink_to(inside)  # outside by name, inside by place
    assert not scope.in_scope(home / "looks-personal", cfg(home))
    assert scope.in_scope(tmp_path / "looks-elsewhere", cfg(home))


def test_a_personal_path_that_is_a_symlink_is_resolved_too(home, tmp_path):
    repo = make_repo(home)
    link = tmp_path / "link-to-personal"
    link.symlink_to(home)
    assert scope.in_scope(repo, cfg(link))


def test_a_symlink_loop_is_out_of_scope_not_an_error(home, tmp_path):
    (tmp_path / "a").symlink_to(tmp_path / "b")
    (tmp_path / "b").symlink_to(tmp_path / "a")
    assert not scope.in_scope(tmp_path / "a" / "x", cfg(home))


def test_the_data_root_is_never_in_scope_even_inside_a_personal_path(tmp_path, monkeypatch):
    personal = tmp_path / "everything"
    monkeypatch.setenv("NORTHSTAR_HOME", str(personal / "northstar"))
    root = paths.data_root()
    (root / "harness-cwd").mkdir(parents=True)
    (personal / "proj").mkdir()
    assert scope.in_scope(personal / "proj", cfg(personal))
    assert not scope.in_scope(root, cfg(personal))
    assert not scope.in_scope(paths.harness_cwd(), cfg(personal))
    assert not scope.in_scope(root / "anything" / "below", cfg(personal))


def test_the_data_root_can_be_given_for_a_test(home, tmp_path):
    other = home / "northstar-data"
    other.mkdir()
    assert not scope.in_scope(other, cfg(home), data_root=other)
    assert scope.in_scope(other, cfg(home), data_root=tmp_path / "somewhere-else")


# --- the hidden-run marker (I24) --------------------------------------------------------------------------------


def test_the_hidden_run_marker():
    assert scope.HIDDEN_RUN_ENV == "NORTHSTAR_HIDDEN_RUN"
    assert scope.hidden_run({"NORTHSTAR_HIDDEN_RUN": "1"})
    assert scope.hidden_run({"NORTHSTAR_HIDDEN_RUN": "yes"})
    assert not scope.hidden_run({"NORTHSTAR_HIDDEN_RUN": "0"})
    assert not scope.hidden_run({"NORTHSTAR_HIDDEN_RUN": ""})
    assert not scope.hidden_run({})


def test_the_hidden_run_marker_reads_the_real_environment_by_default(monkeypatch):
    monkeypatch.delenv("NORTHSTAR_HIDDEN_RUN", raising=False)
    assert not scope.hidden_run()
    monkeypatch.setenv("NORTHSTAR_HIDDEN_RUN", "1")
    assert scope.hidden_run()


def test_the_harness_marks_every_program_it_starts_with_the_same_marker(monkeypatch):
    monkeypatch.delenv("NORTHSTAR_HIDDEN_RUN", raising=False)
    assert harness.HIDDEN_RUN_ENV == scope.HIDDEN_RUN_ENV
    env = harness.child_env(["SOME_DROPPED_VARIABLE"])
    assert env[scope.HIDDEN_RUN_ENV] == "1"
    assert scope.hidden_run(env)
    assert scope.HIDDEN_RUN_ENV not in os.environ  # the marker is for the child only
    # Both headless routes build their environment through it.
    from northstar_agent_memory.models import harness_claude
    from northstar_agent_memory.models.port import ModelRequest

    request = ModelRequest(purpose="test.hidden_run", role="worker", family="anthropic", system="s", messages=[{"role": "user", "content": "hi"}])
    assert scope.hidden_run(harness_claude.environment(request))
    # Codex's calls take their environment from the same function (every start in harness_codex.py goes through it).
    from northstar_agent_memory.models import harness_codex
    import inspect

    source = inspect.getsource(harness_codex)
    assert source.count("env=") == source.count("env=harness.child_env(")


# --- the project a source starts in -------------------------------------------------------------------------------


def test_the_project_is_the_repository_that_holds_the_folder(home):
    repo = make_repo(home, "garden notes")
    assert scope.project_scope(repo / "src", cfg(home)) == "project:garden-notes"


def test_without_a_repository_the_project_is_the_first_folder_below_the_personal_path(home):
    deep = home / "scratch" / "a" / "b"
    deep.mkdir(parents=True)
    assert scope.project_scope(deep, cfg(home)) == "project:scratch"
    assert scope.project_scope(home, cfg(home)) == "project:personal"


def test_a_repository_at_the_personal_path_itself_names_the_project(home):
    (home / ".git").mkdir()
    (home / "src" / "pkg").mkdir(parents=True)
    assert scope.project_scope(home / "src" / "pkg", cfg(home)) == "project:personal"


def test_out_of_scope_has_no_project(home, tmp_path):
    assert scope.project_scope(tmp_path, cfg(home)) is None


# --- case: the volume decides ---------------------------------------------------------------------------------


@pytest.fixture
def case_blind(monkeypatch):
    """macOS (APFS as shipped) and Windows ignore case in a path."""
    monkeypatch.setattr(scope, "CASE_INSENSITIVE", True)


@pytest.fixture
def case_sensitive(monkeypatch):
    monkeypatch.setattr(scope, "CASE_INSENSITIVE", False)


def test_this_platform_is_taken_to_ignore_case_exactly_where_apfs_and_ntfs_do():
    import sys

    assert scope.CASE_INSENSITIVE == (sys.platform in ("darwin", "win32"))


def test_a_working_folder_spelled_in_another_case_is_still_in_scope(tmp_path, case_blind):
    personal = tmp_path / "Personal"  # the setting says "Personal" ...
    repo = make_repo(personal)
    spelled = tmp_path / "personal" / "energy-dash"  # ... Claude Code reports the folder as "personal"
    assert scope.in_scope(spelled, cfg(personal))
    assert scope.in_scope(tmp_path / "PERSONAL" / "Energy-Dash" / "SRC", cfg(personal))
    assert scope.in_scope(tmp_path / "PERSONAL", cfg(personal))  # the personal folder itself
    assert scope.in_scope(repo, cfg(tmp_path / "PERSONAL"))  # and the setting in another case than the folder


def test_the_same_working_folder_is_out_of_scope_where_the_volume_tells_the_cases_apart(tmp_path, case_sensitive):
    personal = tmp_path / "Personal"
    make_repo(personal)
    assert scope.in_scope(personal / "energy-dash", cfg(personal))
    assert not scope.in_scope(tmp_path / "personal" / "energy-dash", cfg(personal))
    assert not scope.in_scope(tmp_path / "PERSONAL", cfg(personal))


def test_case_never_makes_a_sibling_that_shares_a_prefix_in_scope(tmp_path, case_blind):
    personal = tmp_path / "Personal"
    personal.mkdir()
    assert not scope.in_scope(tmp_path / "PERSONAL-notes", cfg(personal))
    assert not scope.in_scope(tmp_path / "personal2", cfg(personal))
    assert not scope.in_scope(tmp_path, cfg(personal))


def test_the_data_root_stays_out_of_scope_whatever_its_case(tmp_path, case_blind):
    personal = tmp_path / "Personal"
    root = personal / "Northstar-Data"
    root.mkdir(parents=True)
    assert scope.in_scope(personal / "other", cfg(personal))
    assert not scope.in_scope(personal / "northstar-data", cfg(personal), data_root=root)
    assert not scope.in_scope(personal / "NORTHSTAR-DATA" / "harness-cwd", cfg(personal), data_root=root)


def test_unicode_spellings_of_one_folder_name_match_where_case_is_ignored(tmp_path, case_blind):
    personal = tmp_path / "Café"  # precomposed
    personal.mkdir()
    assert scope.in_scope(tmp_path / "Café" / "repo", cfg(personal))  # decomposed, another case below


def test_the_project_is_found_whatever_the_case_of_the_working_folder(tmp_path, case_blind):
    personal = tmp_path / "Personal"
    repo = make_repo(personal, "Energy-Dash")
    assert scope.project_scope(repo / "src", cfg(personal)) == "project:Energy-Dash"
    assert scope.project_scope(tmp_path / "personal" / "Energy-Dash" / "src", cfg(personal)) is not None
    # a folder spelled in another case still lands in a project named for the folder below the personal folder
    loose = personal / "Notes" / "deep"
    loose.mkdir(parents=True)
    assert scope.project_scope(tmp_path / "PERSONAL" / "Notes" / "deep", cfg(personal)) == "project:Notes"
    assert scope.project_scope(tmp_path / "PERSONAL", cfg(personal)) == "project:Personal"


def test_a_worktree_folder_is_recognised_whatever_the_case(tmp_path, case_blind):
    personal = tmp_path / "Personal"
    repo = make_repo(personal, "energy-dash")
    tree = repo / ".claude" / "worktrees" / "feature"
    tree.mkdir(parents=True)
    spelled = tmp_path / "personal" / "energy-dash" / ".CLAUDE" / "Worktrees" / "feature"
    assert scope.project_scope(tree, cfg(personal)) == "project:energy-dash"
    assert scope.project_scope(spelled, cfg(personal)) == "project:energy-dash"


@pytest.mark.skipif(not (os.path.exists(os.path.expanduser("~")) and __import__("sys").platform == "darwin"), reason="macOS only")
def test_on_this_mac_a_real_folder_found_under_another_case_is_in_scope(tmp_path):
    personal = tmp_path / "RealPersonal"
    repo = make_repo(personal)
    twisted = tmp_path / "realpersonal" / "energy-dash"
    if not twisted.exists():
        pytest.skip("this volume is case-sensitive")
    assert scope.in_scope(twisted, cfg(personal))
