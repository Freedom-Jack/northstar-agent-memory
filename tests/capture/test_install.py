"""Installing and removing capture's hooks: always against a temporary folder, never the real Claude Code settings."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from northstar_agent_memory import __version__, paths
from northstar_agent_memory.capture import hook, install, spool

from . import assert_throwaway_root, event, make_repo, write_settings

REPO = Path(__file__).resolve().parents[2]
PYTHON = "/opt/northstar/.venv/bin/python"  # an invented interpreter: the pure tests never run it


@pytest.fixture(autouse=True)
def _throwaway_root():
    assert_throwaway_root()
    yield
    assert_throwaway_root()


@pytest.fixture
def settings_dir(tmp_path):
    folder = tmp_path / "claude-home"  # stands in for ~/.claude; nothing here is the real one
    folder.mkdir()
    return folder


def write_json(path: Path, data, indent=2, newline=True) -> str:
    text = json.dumps(data, indent=indent) + ("\n" if newline else "")
    path.write_text(text, encoding="utf-8")
    return text


USER_SETTINGS = {
    "model": "opus",
    "permissions": {"allow": ["Bash(git status)"], "deny": ["Read(./.env)"]},
    "env": {"FOO": "bar"},
    "hooks": {
        "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "/usr/local/bin/audit"}]}],
        "Stop": [{"hooks": [{"type": "command", "command": "/usr/local/bin/notify", "timeout": 4}]}],
    },
    "statusLine": {"type": "command", "command": "echo hi"},
}


def ours(settings: dict) -> dict:
    return install.northstar_events(settings)


def backups(path: Path) -> list[Path]:
    return sorted(path.parent.glob(path.name + install.SETTINGS_BACKUP_TAG + "*"))


# --- the command -----------------------------------------------------------------------------------------------


def test_the_events_are_the_ones_the_hook_handles():
    assert set(install.EVENTS) == set(hook.FIELDS)


def test_timeouts_are_at_or_above_the_budgets_and_above_the_hooks_own_cap():
    floors = {"SessionStart": 5, "UserPromptSubmit": 3, "Stop": 2, "SubagentStop": 2, "PreCompact": 2, "PostCompact": 2, "SessionEnd": 1.5}
    for event_name, timeout in install.EVENTS.items():
        assert timeout >= floors[event_name], event_name
        assert timeout > hook.HARD_CAP_S.get(event_name, hook.DEFAULT_CAP_S)


def test_the_entry_is_exec_form_with_the_interpreter_and_no_uv():
    entry = install.hook_entry("Stop", PYTHON)
    assert entry == {
        "type": "command", "command": PYTHON,
        "args": ["-P", "-m", "northstar_agent_memory.capture.hook", "Stop"], "timeout": install.EVENTS["Stop"],
    }
    assert "uv" not in json.dumps(entry).replace(PYTHON, "").split()  # no `uv run` in front


def test_the_config_has_one_group_with_one_hook_per_event():
    config = install.hooks_config(PYTHON)
    assert set(config) == set(install.EVENTS)
    for name, groups in config.items():
        assert len(groups) == 1 and len(groups[0]["hooks"]) == 1
        assert groups[0]["hooks"][0]["args"][-1] == name and "matcher" not in groups[0]


def test_the_project_interpreter_is_the_repos_venv_and_is_not_resolved(tmp_path):
    root = tmp_path / "checkout"
    (root / ".venv" / "bin").mkdir(parents=True)
    real = tmp_path / "base-python"
    real.write_text("")
    (root / ".venv" / "bin" / "python").symlink_to(real)
    assert install.project_python(root) == str(root / ".venv" / "bin" / "python")  # the link, not its target


def test_without_a_venv_the_running_interpreter_is_used(tmp_path):
    assert install.project_python(tmp_path) == sys.executable


def test_this_checkouts_interpreter_is_absolute():
    assert Path(install.project_python()).is_absolute()
    assert install.project_root() == REPO


def test_an_entry_is_recognised_by_the_module_and_nothing_else():
    assert install.is_northstar_hook(install.hook_entry("Stop", PYTHON))
    assert install.is_northstar_hook({"type": "command", "command": f"{PYTHON} -m {install.MODULE} Stop"})
    assert not install.is_northstar_hook({"type": "command", "command": "/usr/local/bin/notify northstar"})
    assert not install.is_northstar_hook("northstar_agent_memory.capture.hook")
    assert not install.is_northstar_hook({"type": "command", "command": "x", "args": ["--module", "other"]})


def test_the_generated_command_really_starts_the_hook():
    ok, detail = install.check_command(install.project_python())
    assert ok, detail


def test_a_command_that_does_not_exist_or_cannot_start_the_hook_is_reported(tmp_path):
    ok, detail = install.check_command(str(tmp_path / "no-python"))
    assert not ok and "does not exist" in detail
    broken = tmp_path / "broken-python"
    broken.write_text("#!/bin/sh\necho 'No module named northstar_agent_memory' >&2\nexit 1\n")
    broken.chmod(0o755)
    ok, detail = install.check_command(str(broken))
    assert not ok and "No module named" in detail


def test_the_check_runs_as_a_hidden_run_and_writes_nothing():
    install.check_command(install.project_python())
    assert not (paths.data_root() / "spool").exists() and not (paths.data_root() / "capture").exists()


def test_the_command_in_a_settings_entry_runs_end_to_end_from_another_folder(tmp_path):
    """What Claude Code would do: run the entry's command and args from the session's folder, with the event on stdin."""
    personal = tmp_path / "personal"
    repo = make_repo(personal)
    write_settings(personal)
    spool.write_encryption_stamp()
    entry = install.hook_entry("UserPromptSubmit", install.project_python())
    env = {**os.environ, "NORTHSTAR_CAPTURE_NO_SPAWN": "1"}
    env.pop("NORTHSTAR_HIDDEN_RUN", None)
    proc = subprocess.run(
        [entry["command"], *entry["args"]], input=json.dumps(event("UserPromptSubmit", repo, prompt="hello there")),
        capture_output=True, text=True, env=env, cwd=repo, timeout=30,
    )
    assert (proc.returncode, proc.stdout, proc.stderr) == (0, "", "")
    assert [r.payload["prompt"] for r in spool.read_pending() if not spool.is_marker(r)] == ["hello there"]


# --- merging ---------------------------------------------------------------------------------------------------


def test_installing_into_a_missing_file_creates_it_with_every_event(settings_dir):
    path = settings_dir / "settings.json"
    plan = install.install_settings(path, PYTHON)
    assert plan.written and plan.backup is None and not plan.exists
    data = json.loads(path.read_text())
    assert set(data) == {"hooks"} and set(data["hooks"]) == set(install.EVENTS)
    assert data["hooks"] == install.hooks_config(PYTHON)
    assert backups(path) == []


def test_installing_leaves_every_other_key_and_hook_alone_and_keeps_a_backup(settings_dir):
    path = settings_dir / "settings.json"
    original = write_json(path, USER_SETTINGS, indent=4)
    plan = install.install_settings(path, PYTHON, now=1_800_000_000)
    after = json.loads(path.read_text())
    for key in USER_SETTINGS:
        if key != "hooks":
            assert after[key] == USER_SETTINGS[key]
    assert after["hooks"]["PreToolUse"] == USER_SETTINGS["hooks"]["PreToolUse"]
    assert after["hooks"]["Stop"][0] == USER_SETTINGS["hooks"]["Stop"][0]  # the user's own Stop hook is still first
    assert len(after["hooks"]["Stop"]) == 2 and install.is_northstar_hook(after["hooks"]["Stop"][1]["hooks"][0])
    assert set(ours(after)) == set(install.EVENTS)
    assert list(after) == list(USER_SETTINGS)  # key order kept
    (backup,) = backups(path)
    assert backup == plan.backup and backup.read_text() == original
    assert ".northstar-backup-20" in backup.name
    assert path.read_text().startswith('{\n    "model"')  # the file's own 4-space indent
    assert path.read_text().endswith("}\n")


def test_a_second_install_changes_nothing_and_makes_no_backup(settings_dir):
    path = settings_dir / "settings.json"
    write_json(path, USER_SETTINGS)
    install.install_settings(path, PYTHON, now=1_800_000_000)
    first = path.read_text()
    again = install.install_settings(path, PYTHON, now=1_800_000_100)
    assert not again.changed and not again.written and again.backup is None
    assert [c.action for c in again.changes] == ["keep"] * len(install.EVENTS)
    assert path.read_text() == first and len(backups(path)) == 1
    assert sum(len(v) for v in ours(json.loads(first)).values()) == len(install.EVENTS)  # one each


def test_installing_with_another_interpreter_updates_in_place_without_duplicating(settings_dir):
    path = settings_dir / "settings.json"
    write_json(path, USER_SETTINGS)
    install.install_settings(path, PYTHON)
    plan = install.install_settings(path, "/elsewhere/.venv/bin/python")
    assert {c.action for c in plan.changes} == {"update"}
    found = ours(json.loads(path.read_text()))
    assert all(len(v) == 1 and v[0]["command"] == "/elsewhere/.venv/bin/python" for v in found.values())
    assert len(backups(path)) == 2  # one for each change, named apart even in the same second


def test_duplicates_left_by_an_earlier_mistake_are_collapsed_to_one(settings_dir):
    path = settings_dir / "settings.json"
    entry = install.hook_entry("Stop", PYTHON)
    write_json(path, {"hooks": {"Stop": [{"hooks": [entry, {"type": "command", "command": "/x"}]}, {"hooks": [entry]}]}})
    plan = install.install_settings(path, PYTHON)
    stop = json.loads(path.read_text())["hooks"]["Stop"]
    assert [c.action for c in plan.changes if c.event == "Stop"] == ["update"]
    assert stop == [{"hooks": [entry, {"type": "command", "command": "/x"}]}]


def test_an_install_in_a_one_line_file_stays_on_one_line_and_a_file_without_a_final_newline_keeps_none(settings_dir):
    path = settings_dir / "settings.json"
    path.write_text('{"model":"opus"}', encoding="utf-8")
    install.install_settings(path, PYTHON)
    text = path.read_text()
    assert text.startswith('{"model":"opus","hooks": {') and "\n" not in text and not text.endswith("\n")
    assert set(ours(json.loads(text))) == set(install.EVENTS)
    install.uninstall_settings(path)
    assert path.read_text() == '{"model":"opus"}'


def test_the_files_permissions_and_its_backup_keep_its_mode(settings_dir):
    path = settings_dir / "settings.json"
    write_json(path, USER_SETTINGS)
    path.chmod(0o600)
    install.install_settings(path, PYTHON)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(backups(path)[0].stat().st_mode) == 0o600


def test_a_settings_file_that_is_a_link_stays_a_link(settings_dir, tmp_path):
    target = tmp_path / "dotfiles" / "settings.json"
    target.parent.mkdir()
    write_json(target, USER_SETTINGS)
    link = settings_dir / "settings.json"
    link.symlink_to(target)
    install.install_settings(link, PYTHON)
    assert link.is_symlink()
    assert set(ours(json.loads(target.read_text()))) == set(install.EVENTS)


def test_no_temporary_file_is_left_behind(settings_dir):
    path = settings_dir / "settings.json"
    write_json(path, USER_SETTINGS)
    install.install_settings(path, PYTHON)
    install.uninstall_settings(path)
    assert sorted(p.name for p in settings_dir.iterdir() if "tmp" in p.name) == []


def test_the_plan_text_names_each_event_and_the_backup(settings_dir):
    path = settings_dir / "settings.json"
    write_json(path, USER_SETTINGS)
    text = "\n".join(install.install_settings(path, PYTHON, dry_run=True).lines())
    for name in install.EVENTS:
        assert f"add    {name}:" in text
    assert "backup:" in text and str(path) in text
    assert "/usr/local/bin/audit" not in text  # nothing of the user's other hooks is shown


# --- refusals --------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("content", ["{not json", "", "[1, 2]", '"text"', "{'single': 'quotes'}", '{"a": 1,}'])
def test_a_file_that_is_not_a_json_object_is_refused_and_left_as_it_is(settings_dir, content):
    path = settings_dir / "settings.json"
    path.write_text(content, encoding="utf-8")
    if content == "":  # an empty file holds no settings: it is treated as {}
        install.install_settings(path, PYTHON)
        assert set(json.loads(path.read_text())) == {"hooks"}
        return
    with pytest.raises(install.InstallError):
        install.install_settings(path, PYTHON)
    with pytest.raises(install.InstallError):
        install.uninstall_settings(path)
    assert path.read_text() == content and backups(path) == []


def test_an_invalid_file_is_not_changed_by_a_dry_run_either(settings_dir):
    path = settings_dir / "settings.json"
    path.write_text("{oops", encoding="utf-8")
    with pytest.raises(install.InstallError, match="not valid JSON"):
        install.install_settings(path, PYTHON, dry_run=True)


@pytest.mark.parametrize(
    "data",
    [{"hooks": []}, {"hooks": {"Stop": {"hooks": []}}}, {"hooks": {"Stop": ["x"]}}, {"hooks": {"Stop": [{"hooks": "x"}]}}],
)
def test_hooks_in_a_shape_claude_code_does_not_use_are_refused(settings_dir, data):
    path = settings_dir / "settings.json"
    original = write_json(path, data)
    with pytest.raises(install.InstallError):
        install.install_settings(path, PYTHON)
    assert path.read_text() == original and backups(path) == []


def test_a_folder_is_not_a_settings_file(settings_dir):
    with pytest.raises(install.InstallError, match="folder"):
        install.install_settings(settings_dir, PYTHON)


def test_the_install_functions_have_no_default_path():
    import inspect

    for fn in (install.install_settings, install.uninstall_settings, install.render_plugin):
        first = next(iter(inspect.signature(fn).parameters.values()))
        assert first.default is inspect.Parameter.empty, fn.__name__


# --- dry run ---------------------------------------------------------------------------------------------------


def test_a_dry_run_writes_nothing_and_says_what_it_would_do(settings_dir):
    path = settings_dir / "settings.json"
    write_json(path, USER_SETTINGS)
    before = path.read_bytes()
    plan = install.install_settings(path, PYTHON, dry_run=True)
    assert plan.changed and not plan.written and plan.backup is not None and not plan.backup.exists()
    assert path.read_bytes() == before and backups(path) == []
    assert "+" in plan.diff() and "northstar_agent_memory.capture.hook" in plan.diff()


def test_a_dry_run_on_a_missing_file_creates_neither_it_nor_its_folder(tmp_path):
    path = tmp_path / "not-yet" / "settings.json"
    install.install_settings(path, PYTHON, dry_run=True)
    assert not path.parent.exists()


# --- uninstall -------------------------------------------------------------------------------------------------


def test_install_then_uninstall_gives_back_the_original_file_exactly(settings_dir):
    path = settings_dir / "settings.json"
    original = write_json(path, USER_SETTINGS)
    install.install_settings(path, PYTHON)
    assert path.read_text() != original
    plan = install.uninstall_settings(path)
    assert path.read_text() == original
    assert plan.written and {c.action for c in plan.changes} == {"remove"} and len(plan.changes) == len(install.EVENTS)


def test_uninstall_on_a_file_that_had_no_hooks_removes_the_hooks_key_it_added(settings_dir):
    path = settings_dir / "settings.json"
    original = write_json(path, {"model": "opus", "env": {"A": "1"}})
    install.install_settings(path, PYTHON)
    install.uninstall_settings(path)
    assert path.read_text() == original


def test_uninstall_removes_only_northstars_hooks_even_in_a_shared_group(settings_dir):
    path = settings_dir / "settings.json"
    mine = install.hook_entry("Stop", PYTHON)
    theirs = {"type": "command", "command": "/usr/local/bin/notify"}
    write_json(path, {"hooks": {"Stop": [{"hooks": [theirs, mine]}], "SessionEnd": [{"hooks": [install.hook_entry("SessionEnd", PYTHON)]}]}})
    install.uninstall_settings(path)
    assert json.loads(path.read_text()) == {"hooks": {"Stop": [{"hooks": [theirs]}]}}


def test_uninstall_leaves_a_group_with_a_matcher_and_other_hooks_untouched(settings_dir):
    path = settings_dir / "settings.json"
    write_json(path, USER_SETTINGS)
    install.install_settings(path, PYTHON)
    install.uninstall_settings(path)
    assert json.loads(path.read_text())["hooks"] == USER_SETTINGS["hooks"]


def test_uninstall_keeps_a_backup_and_a_second_uninstall_does_nothing(settings_dir):
    path = settings_dir / "settings.json"
    write_json(path, USER_SETTINGS)
    install.install_settings(path, PYTHON)
    installed_text = path.read_text()
    install.uninstall_settings(path)
    backs = backups(path)
    assert len(backs) == 2 and installed_text in [b.read_text() for b in backs]  # the file as it was before the removal
    again = install.uninstall_settings(path)
    assert not again.changed and not again.written and len(backups(path)) == 2


def test_uninstall_of_a_missing_file_says_so(settings_dir):
    with pytest.raises(install.InstallError, match="nothing to remove"):
        install.uninstall_settings(settings_dir / "settings.json")


def test_uninstall_does_not_touch_other_keys_changed_since_the_install(settings_dir):
    path = settings_dir / "settings.json"
    write_json(path, USER_SETTINGS)
    install.install_settings(path, PYTHON)
    data = json.loads(path.read_text())
    data["model"] = "sonnet"  # the user edits the file in between
    write_json(path, data)
    install.uninstall_settings(path)
    assert json.loads(path.read_text()) == {**USER_SETTINGS, "model": "sonnet"}


def test_installed_events_and_interpreters_are_read_without_writing(settings_dir):
    path = settings_dir / "settings.json"
    write_json(path, USER_SETTINGS)
    assert install.installed_events(path) == []
    assert install.installed_events(settings_dir / "missing.json") is None
    install.install_settings(path, PYTHON)
    assert install.installed_events(path) == sorted(install.EVENTS)
    assert install.hook_interpreters(path) == [PYTHON]
    path.write_text("{bad")
    assert install.installed_events(path) is None and install.hook_interpreters(path) == []


# --- the plugin folder -----------------------------------------------------------------------------------------


def test_the_plugin_folder_holds_the_manifest_the_marketplace_and_the_hooks(tmp_path):
    folder = tmp_path / "northstar-plugin"
    plan = install.render_plugin(folder, PYTHON)
    assert plan.written and set(plan.status.values()) == {"new"}
    assert sorted(str(p.relative_to(folder)) for p in folder.rglob("*") if p.is_file()) == [
        ".claude-plugin/marketplace.json", ".claude-plugin/plugin.json", "hooks/hooks.json",
    ]
    manifest = json.loads((folder / ".claude-plugin" / "plugin.json").read_text())
    assert manifest["name"] == "northstar" and manifest["version"] == __version__
    market = json.loads((folder / ".claude-plugin" / "marketplace.json").read_text())
    assert market["name"] == "northstar-local" and market["plugins"][0]["name"] == "northstar"
    hooks_json = json.loads((folder / "hooks" / "hooks.json").read_text())
    assert hooks_json == {"hooks": install.hooks_config(PYTHON)}


def test_the_plugin_holds_no_secret_and_no_home_folder(tmp_path):
    install.render_plugin(tmp_path / "p", PYTHON)
    text = "".join(p.read_text() for p in (tmp_path / "p").rglob("*") if p.is_file())
    assert "/Users/" not in text and "token" not in text.lower() and "key" not in text.lower()


def test_rendering_again_changes_nothing_and_a_changed_file_is_replaced(tmp_path):
    folder = tmp_path / "p"
    install.render_plugin(folder, PYTHON)
    assert set(install.render_plugin(folder, PYTHON).status.values()) == {"same"}
    plan = install.render_plugin(folder, "/elsewhere/python")
    assert plan.status["hooks/hooks.json"] == "changed" and plan.status[".claude-plugin/plugin.json"] == "same"
    assert "/elsewhere/python" in (folder / "hooks" / "hooks.json").read_text()


def test_a_dry_run_of_the_plugin_writes_nothing(tmp_path):
    folder = tmp_path / "p"
    plan = install.render_plugin(folder, PYTHON, dry_run=True)
    assert not folder.exists() and not plan.written and set(plan.status.values()) == {"new"}


def test_a_folder_with_another_plugin_in_it_is_refused_and_untouched(tmp_path):
    folder = tmp_path / "p"
    (folder / ".claude-plugin").mkdir(parents=True)
    other = '{"name": "someone-elses-plugin"}'
    (folder / ".claude-plugin" / "plugin.json").write_text(other)
    with pytest.raises(install.InstallError, match="something other than Northstar"):
        install.render_plugin(folder, PYTHON)
    assert (folder / ".claude-plugin" / "plugin.json").read_text() == other and not (folder / "hooks").exists()


def test_a_file_where_the_plugin_folder_should_be_is_refused(tmp_path):
    (tmp_path / "p").write_text("x")
    with pytest.raises(install.InstallError, match="not a folder"):
        install.render_plugin(tmp_path / "p", PYTHON)


def test_the_plugin_commands_name_the_folder_and_the_plugin(tmp_path):
    folder = tmp_path / "northstar plugin"  # a space needs quoting
    text = "\n".join(install.plugin_commands(folder))
    assert f'claude --plugin-dir "{folder.resolve()}"' in text
    assert "claude plugin install northstar@northstar-local --scope user" in text
    assert "/plugin marketplace add" in text
    plain = "\n".join(install.plugin_commands(tmp_path / "p"))
    assert f"claude --plugin-dir {(tmp_path / 'p').resolve()}" in plain


def test_the_repositorys_plugin_folder_is_the_same_plugin_with_a_path_relative_to_the_plugin():
    files = install.plugin_files(install.TEMPLATE_PYTHON)
    for rel in (".claude-plugin/plugin.json", "hooks/hooks.json"):
        assert (REPO / "plugin" / rel).read_text() == files[rel], rel
    text = (REPO / "plugin" / "hooks" / "hooks.json").read_text()
    assert "${CLAUDE_PLUGIN_ROOT}/../.venv/bin/python" in text and "/Users/" not in text


# --- what was installed where ----------------------------------------------------------------------------------


def test_installs_are_recorded_and_forgotten_in_the_data_root(settings_dir):
    path = settings_dir / "settings.json"
    assert install.recorded_installs() == []
    install.record_install("settings", path, now=1_800_000_000)
    install.record_install("settings", path)  # again: one entry
    install.record_install("plugin", settings_dir / "plugin")
    items = install.recorded_installs()
    assert [(i["kind"], i["path"]) for i in items] == [("settings", str(path.resolve())), ("plugin", str((settings_dir / "plugin").resolve()))]
    assert stat.S_IMODE(install.installs_path().stat().st_mode) == 0o600
    install.forget_install("settings", path)
    assert [i["kind"] for i in install.recorded_installs()] == ["plugin"]
    install.forget_install("settings", path)  # nothing left to forget
    assert len(install.recorded_installs()) == 1


def test_a_damaged_installs_file_reads_as_none(settings_dir):
    install.record_install("settings", settings_dir / "settings.json")
    install.installs_path().write_text("{broken")
    assert install.recorded_installs() == []


def test_a_group_without_a_hooks_key_beside_duplicates_does_not_crash_the_merge():
    dup = {"type": "command", "command": "/old/python", "args": ["-m", install.MODULE, "Stop"]}
    settings = {"hooks": {"Stop": [{"matcher": "x"}, {"hooks": [dup, dict(dup, command="/older/python")]}]}}
    new, changes = install.merge_hooks(settings, PYTHON)
    stop = new["hooks"]["Stop"]
    assert stop[0] == {"matcher": "x"}  # the user's own group is left alone
    assert [h["command"] for g in stop for h in g.get("hooks", [])] == [PYTHON]
    assert changes[[c.event for c in changes].index("Stop")].action == "update"


# --- byte for byte: the file's own text is spliced, never written out again -------------------------------------------

# Settings in the shapes people actually write: each is (name, the file's exact text). None has a Northstar hook.
ODD_FILES = {
    "one-line arrays": (
        '{\n  "permissions": {\n    "allow": ["Bash(git status)", "Read(./src/**)"],\n    "deny": []\n  },\n'
        '  "hooks": {\n    "Stop": [{"hooks": [{"type": "command", "command": "/usr/local/bin/notify"}]}]\n  },\n  "model": "opus"\n}\n'
    ),
    "tabs and no final newline": '{\n\t"model": "opus",\n\t"hooks": {\n\t\t"Stop": [\n\t\t\t{\n\t\t\t\t"hooks": [{ "type": "command", "command": "x" }]\n\t\t\t}\n\t\t]\n\t}\n}',
    "windows line endings": '{\r\n  "model": "opus",\r\n  "env": {\r\n    "A": "1"\r\n  }\r\n}\r\n',
    "escapes and non-ascii": '{\n  "greeting": "caf\\u00e9 \\ud83d\\ude00",\n  "name": "Zoë",\n  "path": "C:\\\\Users\\\\x\\/y"\n}\n',
    "compact": '{"model":"opus","env":{"A":"1"},"hooks":{"Stop":[{"hooks":[{"type":"command","command":"x"}]}]}}',
    "blank lines and trailing spaces": '\n{\n  "model" :  "opus" ,  \n\n  "env":{"A":"1"}\n\n}\n\n',
    "an empty object": "{}\n",
    "a very different indent": '{\n        "model": "opus",\n        "hooks": {\n                "Stop": [\n                        {"hooks": [{"type": "command", "command": "x"}]}\n                ]\n        }\n}\n',
    "numbers and literals": '{\n  "a": 1.50e3,\n  "b": null,\n  "c": [true, false, -0],\n  "d": 1e-7\n}\n',
}


@pytest.mark.parametrize("name", list(ODD_FILES))
def test_install_then_uninstall_gives_back_the_users_file_byte_for_byte(settings_dir, name):
    path = settings_dir / "settings.json"
    original = ODD_FILES[name]
    path.write_bytes(original.encode("utf-8"))
    plan = install.install_settings(path, PYTHON)
    installed = path.read_bytes().decode("utf-8")
    assert plan.written and installed != original
    data = json.loads(installed)
    assert data["hooks"] == {**json.loads(original).get("hooks", {}), **{k: v for k, v in data["hooks"].items()}}  # the user's own hooks first
    assert set(ours(data)) == set(install.EVENTS)
    for key, value in json.loads(original).items():
        if key != "hooks":
            assert data[key] == value
    plan = install.uninstall_settings(path)
    assert plan.written and path.read_bytes().decode("utf-8") == original
    assert len(backups(path)) == 2  # the original before the install, and the installed file before the removal


@pytest.mark.parametrize("name", list(ODD_FILES))
def test_the_install_keeps_the_files_own_style_for_what_it_adds(settings_dir, name):
    path = settings_dir / "settings.json"
    original = ODD_FILES[name]
    path.write_bytes(original.encode("utf-8"))
    install.install_settings(path, PYTHON)
    installed = path.read_bytes().decode("utf-8")
    if "\r\n" in original:
        assert "\n" not in installed.replace("\r\n", "")  # every line ends the way the file's do
    if "\n" not in original:
        assert "\n" not in installed  # a file on one line stays on one line
    if "\t" in original:
        assert "\n\t\t\t" in installed and "\n    " not in installed


def test_the_edit_touches_nothing_outside_the_entries_it_adds(settings_dir):
    path = settings_dir / "settings.json"
    original = ODD_FILES["one-line arrays"]
    path.write_text(original, encoding="utf-8")
    install.install_settings(path, PYTHON)
    installed = path.read_text()
    assert installed.startswith(original[: original.index('"Stop": [{"hooks": [{"type": "command", "command": "/usr/local/bin/notify"}]}')])
    assert '"allow": ["Bash(git status)", "Read(./src/**)"]' in installed and '"deny": []' in installed  # not re-flowed
    assert installed.endswith('"model": "opus"\n}\n')


def test_uninstall_keeps_what_the_user_changed_after_the_install_in_their_own_text(settings_dir):
    path = settings_dir / "settings.json"
    path.write_text(ODD_FILES["one-line arrays"], encoding="utf-8")
    install.install_settings(path, PYTHON)
    edited = path.read_text().replace('"model": "opus"', '"model":   "sonnet"  ').replace('["Bash(git status)"', '[ "Bash(git status)"')
    path.write_text(edited, encoding="utf-8")
    install.uninstall_settings(path)
    assert path.read_text() == ODD_FILES["one-line arrays"].replace('"model": "opus"', '"model":   "sonnet"  ').replace(
        '["Bash(git status)"', '[ "Bash(git status)"')


def test_an_update_replaces_the_entry_where_it_stands_and_uninstall_still_leaves_the_rest_alone(settings_dir):
    path = settings_dir / "settings.json"
    original = ODD_FILES["one-line arrays"]
    path.write_text(original, encoding="utf-8")
    install.install_settings(path, PYTHON)
    install.install_settings(path, "/elsewhere/.venv/bin/python")
    text = path.read_text()
    assert "/opt/northstar" not in text and text.count("/elsewhere/.venv/bin/python") == len(install.EVENTS)
    install.uninstall_settings(path)
    assert path.read_text() == original


def test_uninstall_takes_our_hook_out_of_a_group_it_shares_and_leaves_the_neighbours_bytes(settings_dir):
    mine = json.dumps(install.hook_entry("Stop", PYTHON))
    a, b = '{"type": "command", "command": "a"}', '{"type": "command",   "command": "b"}'
    cases = [
        ([mine, b], [b]),
        ([a, mine], [a]),
        ([a, mine, b], [a, b]),
        ([a, mine, mine, b], [a, b]),
        ([mine, a, mine], [a]),
    ]
    for hooks, left in cases:
        path = settings_dir / "settings.json"
        frame = '{\n  "hooks": {\n    "Stop": [\n      {"matcher": "x", "hooks": [%s]}\n    ]\n  }\n}\n'
        path.write_text(frame % ", ".join(hooks), encoding="utf-8")
        install.uninstall_settings(path)
        assert path.read_text() == frame % ", ".join(left), hooks


def test_uninstall_takes_out_the_groups_and_lists_that_held_only_our_entries(settings_dir):
    path = settings_dir / "settings.json"
    mine = json.dumps(install.hook_entry("Stop", PYTHON))
    path.write_text('{"model": "opus", "hooks": {"Stop": [{"hooks": [' + mine + ']}], "PreToolUse": [{"hooks": [{"type": "command", "command": "a"}]}]}}', encoding="utf-8")
    install.uninstall_settings(path)
    assert path.read_text() == '{"model": "opus", "hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": "a"}]}]}}'
    path.write_text('{"model": "opus", "hooks": {"Stop": [{"hooks": [' + mine + "]}]}}", encoding="utf-8")
    install.uninstall_settings(path)
    assert path.read_text() == '{"model": "opus"}'


def test_a_random_file_in_a_random_style_round_trips(settings_dir):
    import random

    rnd = random.Random(20261105)
    path = settings_dir / "settings.json"
    user = lambda: {"type": "command", "command": rnd.choice(["/usr/local/bin/audit", "echo é", "x y"])}
    for _ in range(150):
        data: dict = {}
        for key in rnd.sample(["model", "permissions", "env", "statusLine"], rnd.randint(0, 4)):
            data[key] = rnd.choice(["opus", {"allow": ["a", "b é"], "deny": []}, {"A": "1"}, [1, 2, {"x": None}], 3.5, True])
        if rnd.random() < 0.8:
            data["hooks"] = {
                event: [{**({"matcher": "Bash"} if rnd.random() < 0.4 else {}), "hooks": [user() for _ in range(rnd.randint(1, 3))]} for _ in range(rnd.randint(1, 2))]
                for event in rnd.sample(["PreToolUse", "Notification", "Stop", "SessionEnd"], rnd.randint(0, 3))
            }
        text = json.dumps(
            data, indent=rnd.choice([None, 1, 2, 4, "\t"]), separators=rnd.choice([None, (",", ":"), (", ", ": ")]), ensure_ascii=rnd.random() < 0.5
        ) + rnd.choice(["", "\n"])
        if rnd.random() < 0.2:
            text = text.replace("\n", "\r\n")
        if data.get("hooks") == {}:
            continue  # an empty "hooks" object holds nothing, and goes with ours
        path.write_bytes(text.encode("utf-8"))
        install.install_settings(path, PYTHON)
        assert set(ours(json.loads(path.read_text()))) == set(install.EVENTS), text
        install.uninstall_settings(path)
        assert path.read_bytes().decode("utf-8") == text


def test_when_the_splice_cannot_match_the_merge_the_file_is_written_out_again(settings_dir, monkeypatch):
    path = settings_dir / "settings.json"
    path.write_text(ODD_FILES["compact"], encoding="utf-8")
    monkeypatch.setattr(install, "splice_merge", lambda *a, **k: None)
    install.install_settings(path, PYTHON)
    text = path.read_text()
    assert text.startswith('{\n  "model": "opus"') and set(ours(json.loads(text))) == set(install.EVENTS)
    monkeypatch.setattr(install, "splice_remove", lambda *a, **k: None)
    install.uninstall_settings(path)
    assert json.loads(path.read_text()) == json.loads(ODD_FILES["compact"])


def test_a_splice_that_would_give_other_settings_than_the_merge_is_not_used(settings_dir):
    text = ODD_FILES["compact"]
    assert install.splice_merge(text, PYTHON, 2) is not None
    assert install.splice_remove(text) == text  # nothing of ours in it: the very same text
    assert install.splice_merge("", PYTHON, 2) is None and install.splice_merge("[1]", PYTHON, 2) is None


def test_a_file_with_windows_line_endings_is_read_and_written_untranslated(settings_dir):
    path = settings_dir / "settings.json"
    path.write_bytes(b'{\r\n  "model": "opus"\r\n}\r\n')
    plan = install.install_settings(path, PYTHON)
    assert b"\r\n" in path.read_bytes() and b"\n" not in path.read_bytes().replace(b"\r\n", b"")
    assert plan.backup.read_bytes() == b'{\r\n  "model": "opus"\r\n}\r\n'


# --- the plugin: self-contained for a marketplace, relative only in the repository's own folder ----------------------


def test_the_rendered_plugin_names_the_interpreter_by_its_absolute_path_in_every_hook(tmp_path):
    install.render_plugin(tmp_path / "p", PYTHON)
    text = (tmp_path / "p" / "hooks" / "hooks.json").read_text()
    assert "${" not in text and "CLAUDE_PLUGIN_ROOT" not in text
    hooks = json.loads(text)["hooks"]
    assert set(hooks) == set(install.EVENTS)
    for event_name, groups in hooks.items():
        (hook_entry,) = groups[0]["hooks"]
        assert hook_entry["command"] == PYTHON and os.path.isabs(hook_entry["command"])
        assert hook_entry["args"] == ["-P", "-m", install.MODULE, event_name]


def test_a_rendered_plugin_still_works_after_claude_code_copies_it_elsewhere(tmp_path):
    """What a marketplace install does: the folder is copied into the plugin cache, away from where it was rendered."""
    import shutil

    install.render_plugin(tmp_path / "rendered", install.project_python())
    shutil.copytree(tmp_path / "rendered", tmp_path / "cache" / "northstar" / "0.1.0")
    hooks = json.loads((tmp_path / "cache" / "northstar" / "0.1.0" / "hooks" / "hooks.json").read_text())["hooks"]
    for groups in hooks.values():
        command = groups[0]["hooks"][0]["command"]
        assert Path(command).is_absolute() and Path(command).exists()
    ok, detail = install.check_command(hooks["Stop"][0]["hooks"][0]["command"])
    assert ok, detail


@pytest.mark.parametrize("python", [install.TEMPLATE_PYTHON, "python", ".venv/bin/python", "${CLAUDE_PLUGIN_ROOT}/bin/python", "/x/${HOME}/python"])
def test_a_plugin_is_never_rendered_with_an_interpreter_that_needs_the_checkout(tmp_path, python):
    with pytest.raises(install.InstallError, match="absolute path of an interpreter"):
        install.render_plugin(tmp_path / "p", python)
    assert not (tmp_path / "p").exists()
    with pytest.raises(install.InstallError, match="absolute path"):
        install.render_plugin(tmp_path / "p", python, dry_run=True)


def test_the_repositorys_plugin_folder_says_it_is_for_plugin_dir_only_and_has_no_marketplace_file():
    readme = (REPO / "plugin" / "README.md").read_text()
    assert "claude --plugin-dir ./plugin" in readme
    assert "not for a marketplace install" in readme and "northstar capture install --plugin-dir" in readme
    assert not (REPO / "plugin" / ".claude-plugin" / "marketplace.json").exists()
    assert sorted(p.relative_to(REPO / "plugin").as_posix() for p in (REPO / "plugin").rglob("*") if p.is_file()) == [
        ".claude-plugin/plugin.json", "README.md", "hooks/hooks.json"]


# --- one way, not two ---------------------------------------------------------------------------------------------


def test_a_second_way_is_refused_while_the_first_still_has_hooks(settings_dir, tmp_path):
    settings = settings_dir / "settings.json"
    install.install_settings(settings, PYTHON)
    install.record_install("settings", settings)
    with pytest.raises(install.InstallError, match="already installed as a settings") as err:
        install.refuse_duplicate("plugin")
    assert str(settings.resolve()) in str(err.value) and "northstar capture uninstall --settings" in str(err.value)
    assert "twice" in str(err.value)
    install.refuse_duplicate("settings")  # the same way again is an update, not a duplicate

    folder = tmp_path / "plugin"
    install.render_plugin(folder, PYTHON)
    install.uninstall_settings(settings)
    install.forget_install("settings", settings)
    install.record_install("plugin", folder)
    with pytest.raises(install.InstallError, match="already installed as a plugin") as err:
        install.refuse_duplicate("settings")
    assert "claude plugin uninstall northstar@northstar-local" in str(err.value) and str(folder.resolve()) in str(err.value)
    install.refuse_duplicate("plugin")


def test_an_install_whose_hooks_are_gone_does_not_count(settings_dir, tmp_path):
    settings = settings_dir / "settings.json"
    install.install_settings(settings, PYTHON)
    install.record_install("settings", settings)
    install.uninstall_settings(settings)  # by hand, or by an earlier version: the record is still there
    install.refuse_duplicate("plugin")
    settings.unlink()  # or the file is gone
    install.refuse_duplicate("plugin")
    folder = tmp_path / "plugin"
    install.render_plugin(folder, PYTHON)
    install.record_install("plugin", folder)
    (folder / "hooks" / "hooks.json").unlink()
    install.refuse_duplicate("settings")
    assert install.other_installs("settings") == []


# --- encryption at rest -------------------------------------------------------------------------------------------


def test_install_checks_encryption_and_leaves_the_stamp(settings_dir):
    assert not spool.encryption_stamp()[0]
    detail = install.ensure_encryption(now=1_800_000_000)
    assert "encrypted volume" in detail and str(spool.stamp_path()) in detail
    assert spool.encryption_stamp()[0] and stat.S_IMODE(spool.stamp_path().stat().st_mode) == 0o600


def test_a_dry_run_checks_but_leaves_no_stamp():
    assert "would be made" in install.ensure_encryption(dry_run=True)
    assert not spool.stamp_path().exists()


def test_without_encryption_nothing_is_stamped_and_the_reason_is_given(monkeypatch):
    from northstar_agent_memory.core import db

    def refuse(root=None):
        raise db.EncryptionRequired(f"{root} is not on an encrypted volume: turn FileVault on")

    monkeypatch.setattr(db, "require_encryption", refuse)
    for dry_run in (False, True):
        with pytest.raises(install.InstallError, match="not known to be encrypted at rest.*turn FileVault on"):
            install.ensure_encryption(dry_run=dry_run)
    assert not spool.stamp_path().exists()


def test_the_installs_file_is_made_in_owner_only_folders(settings_dir, tmp_path):
    root = tmp_path / "fresh" / "Northstar"
    old = os.umask(0)
    try:
        install.record_install("settings", settings_dir / "settings.json", root=root)
    finally:
        os.umask(old)
    assert [stat.S_IMODE(p.stat().st_mode) for p in (tmp_path / "fresh", root, root / "capture")] == [0o700] * 3
