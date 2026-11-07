"""Putting capture's hooks into Claude Code, and taking them out (connectors-claude-code-and-codex.md §14, §14.1, §14.4;
note 22 A11).

Two ways, each given an explicit path and never a default: nothing here knows where the real Claude Code settings live.
Use one of the two, not both: with both, every turn would be spooled twice, so `refuse_duplicate` turns the second down.

(a) A settings file. `install_settings(path)` merges Northstar's entries into the "hooks" object of a settings.json and
    leaves every other byte of the file as it is: the entries are spliced into the file's own text (its indent, its
    one-line arrays, its escapes, its line endings), not written out again by a JSON encoder. It refuses a file that is
    not valid JSON, keeps a timestamped backup beside the file before it writes, and does nothing (no write, no backup)
    when the entries are already there. A second install updates the entries in place and never duplicates them.
    `uninstall_settings(path)` splices only Northstar's entries (and the groups, lists and object they leave empty) out
    of the file's current text, so install then uninstall gives the user's file back byte for byte, and whatever
    the user changed in between stays changed. It does not restore the backup, which would lose that. (Where the
    splice cannot be made to give the same settings as the merge, which only an unusual file does, the file is written
    out again instead, as in earlier versions.)
(b) A plugin folder for a marketplace install. `render_plugin(folder)` writes `.claude-plugin/plugin.json`,
    `.claude-plugin/marketplace.json` and `hooks/hooks.json` with the absolute path of the interpreter in each hook, so the
    plugin works wherever Claude Code copies it; `plugin_commands(folder)` gives the commands that add it. It refuses an
    interpreter that is not an absolute path. The repository's own `plugin/` folder is something else: the same hooks
    with a path relative to the checkout (TEMPLATE_PYTHON), for `claude --plugin-dir ./plugin` from a checkout only, and
    with no marketplace file (see plugin/README.md).

The hook command runs the project's own interpreter, `<repo>/.venv/bin/python`, with no `uv run` in front (it costs about
100 ms), in exec form: no shell, no quoting, the absolute path baked in so Claude Code can run it from any folder, and
`-P` so the session's working folder is never put on the module search path.
Each Northstar entry is recognised by the hook module's name in its arguments, nothing else.

Before it writes anything, an install checks that the data folder is encrypted at rest (PL-3: the core's
`require_encryption`) and leaves a stamp the hook looks for (`ensure_encryption`).

Standard library only apart from the package's own version: nothing here imports the core until the encryption check.
"""

from __future__ import annotations

import copy
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from northstar_agent_memory import __version__
from northstar_agent_memory.capture import spool

MODULE = "northstar_agent_memory.capture.hook"
PLUGIN_NAME = "northstar"
MARKETPLACE_NAME = "northstar-local"
SETTINGS_BACKUP_TAG = ".northstar-backup-"
INSTALLS_FILE = "installs.json"

# The events capture uses and each one's hook timeout in seconds, at or above the §4.3 values. The hook itself ends
# sooner (hook.py HARD_CAP_S: 0.4 s for SessionEnd, 1.0 s for UserPromptSubmit, 0.75 s for the rest), so a timeout is a
# ceiling that is never reached.
EVENTS: dict[str, int] = {
    "SessionStart": 5,
    "UserPromptSubmit": 3,
    "Stop": 8,
    "SubagentStop": 2,
    "PreCompact": 2,
    "PostCompact": 2,
    "SessionEnd": 2,
}

# The interpreter in the repository's own plugin/ folder: relative to the plugin, so no one's home folder is committed.
TEMPLATE_PYTHON = "${CLAUDE_PLUGIN_ROOT}/../.venv/bin/python"

PLUGIN_DESCRIPTION = (
    "Northstar capture: writes what is said in your Claude Code sessions, both sides and word for word, into your own "
    "chat history on this machine. Only sessions inside the personal folders you named. No model is called."
)


class InstallError(Exception):
    """A problem the person can fix: shown without a traceback."""


# --- the interpreter and the command ---------------------------------------------------------------------------


def project_root() -> Path | None:
    """The repository this package is run from (it holds pyproject.toml above src/), or None when it is installed
    somewhere else."""
    root = Path(__file__).resolve().parents[3]
    return root if (root / "pyproject.toml").is_file() and (root / "src" / "northstar_agent_memory").is_dir() else None


def project_python(root: Path | None = None) -> str:
    """The absolute path of the project's own interpreter: `<repo>/.venv/bin/python` (`Scripts/python.exe` on Windows).

    The path is not resolved: a virtual environment finds its packages through the path it was started by, so a link to
    the base interpreter must stay a link. Outside a repository checkout, the interpreter running this code."""
    base = project_root() if root is None else root
    if base is not None:
        for relative in (Path(".venv") / "bin" / "python", Path(".venv") / "Scripts" / "python.exe"):
            candidate = base / relative
            if candidate.exists():
                return str(candidate)
    return sys.executable


def hook_entry(event: str, python: str) -> dict[str, Any]:
    """One hook, exec form. `-P` keeps the session's working folder off the module search path."""
    return {"type": "command", "command": python, "args": ["-P", "-m", MODULE, event], "timeout": EVENTS[event]}


def hooks_config(python: str) -> dict[str, list[dict[str, Any]]]:
    """The "hooks" object capture needs: one group with one hook for each event."""
    return {event: [{"hooks": [hook_entry(event, python)]}] for event in EVENTS}


def is_northstar_hook(hook: object) -> bool:
    """Whether a hook entry is one of ours: it runs the capture hook module (in its arguments, or in a command line)."""
    if not isinstance(hook, dict):
        return False
    args = hook.get("args")
    if isinstance(args, list) and MODULE in args:
        return True
    command = hook.get("command")
    return isinstance(command, str) and MODULE in command


def check_command(python: str, timeout_s: float = 20.0) -> tuple[bool, str]:
    """Whether `python -m <the hook module>` starts. It runs as a hidden run on an empty input, so it writes nothing,
    and reports in a few words what went wrong if it does not."""
    env = dict(os.environ)
    env["NORTHSTAR_HIDDEN_RUN"] = "1"
    try:
        proc = subprocess.run(
            [python, "-P", "-m", MODULE, "SessionStart"], input="", capture_output=True, text=True, env=env,
            timeout=timeout_s, check=False,
        )
    except FileNotFoundError:
        return False, f"{python} does not exist"
    except OSError as err:
        return False, f"{python} cannot be run ({type(err).__name__})"
    except subprocess.TimeoutExpired:
        return False, f"{python} did not answer within {timeout_s:g} s"
    if proc.returncode != 0:
        last = (proc.stderr or "").strip().splitlines()[-1:] or [f"exit code {proc.returncode}"]
        return False, f"{python} could not start the hook: {last[0][:200]}"
    return True, f"{python} starts the hook"


# --- merging into a settings object ----------------------------------------------------------------------------


@dataclass(slots=True)
class Change:
    event: str
    action: str  # add, update, keep, remove
    entry: dict[str, Any] | None = None

    def line(self) -> str:
        shown = json.dumps(self.entry, ensure_ascii=False) if self.entry is not None else ""
        return f"  {self.action:<6} {self.event}: {shown}".rstrip()


def _hooks_object(settings: dict[str, Any], *, create: bool) -> dict[str, Any] | None:
    if "hooks" not in settings:
        if not create:
            return None
        settings["hooks"] = {}
    hooks = settings["hooks"]
    if not isinstance(hooks, dict):
        raise InstallError('the settings file has a "hooks" key that is not an object; fix it by hand first')
    return hooks


def merge_hooks(settings: dict[str, Any], python: str) -> tuple[dict[str, Any], list[Change]]:
    """`settings` with Northstar's hooks in place, and what was done for each event. `settings` is not changed."""
    out = copy.deepcopy(settings)
    hooks = _hooks_object(out, create=True)
    assert hooks is not None
    changes: list[Change] = []
    for event in EVENTS:
        entry = hook_entry(event, python)
        groups = hooks.get(event)
        if groups is None:
            hooks[event] = [{"hooks": [entry]}]
            changes.append(Change(event, "add", entry))
            continue
        if not isinstance(groups, list) or not all(isinstance(g, dict) and isinstance(g.get("hooks", []), list) for g in groups):
            raise InstallError(f'the "{event}" hooks in the settings file are not in the shape Claude Code uses; fix them by hand first')
        found = [(gi, hi) for gi, g in enumerate(groups) for hi, h in enumerate(g.get("hooks", [])) if is_northstar_hook(h)]
        if not found:
            groups.append({"hooks": [entry]})
            changes.append(Change(event, "add", entry))
            continue
        first_gi, first_hi = found[0]
        current = groups[first_gi]["hooks"][first_hi]
        for gi, hi in reversed(found[1:]):  # an earlier mistake left more than one: keep the first
            del groups[gi]["hooks"][hi]
        groups[first_gi]["hooks"][first_hi] = entry
        emptied = {gi for gi, _ in found[1:]}
        hooks[event] = [g for gi, g in enumerate(groups) if g.get("hooks") or gi not in emptied]
        changes.append(Change(event, "keep" if current == entry and len(found) == 1 else "update", entry))
    return out, changes


def remove_hooks(settings: dict[str, Any]) -> tuple[dict[str, Any], list[Change]]:
    """`settings` without Northstar's hooks, and what was removed. Groups, event lists and the "hooks" object that this
    leaves empty go too; anything that was already empty, or is not ours, stays."""
    out = copy.deepcopy(settings)
    hooks = _hooks_object(out, create=False)
    changes: list[Change] = []
    if hooks is None:
        return out, changes
    for event in list(hooks):
        groups = hooks[event]
        if not isinstance(groups, list):
            continue
        kept: list[Any] = []
        removed_here = False
        for group in groups:
            inner = group.get("hooks") if isinstance(group, dict) else None
            if not isinstance(inner, list):
                kept.append(group)
                continue
            ours = [h for h in inner if is_northstar_hook(h)]
            if not ours:
                kept.append(group)
                continue
            removed_here = True
            for h in ours:
                changes.append(Change(event, "remove", h))
            rest = [h for h in inner if not is_northstar_hook(h)]
            if rest:
                kept.append({**group, "hooks": rest})
        if removed_here:
            if kept:
                hooks[event] = kept
            else:
                del hooks[event]
    if changes and not hooks:
        del out["hooks"]
    return out, changes


# --- reading and writing a settings file -----------------------------------------------------------------------


def _indent_of(text: str) -> str | int:
    match = re.search(r'^([ \t]+)"', text, re.M)
    if not match:
        return 2
    lead = match.group(1)
    return "\t" if lead.startswith("\t") else len(lead)


def _dump(settings: dict[str, Any], indent: str | int, trailing_newline: bool) -> str:
    return json.dumps(settings, indent=indent, ensure_ascii=False) + ("\n" if trailing_newline else "")


def read_text(path: Path) -> str:
    """The file's text exactly as it is: line endings are not translated, so a splice can leave them as they were."""
    try:
        return path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as err:
        raise InstallError(f"{path} cannot be read ({type(err).__name__})") from err


def read_settings(path: Path) -> tuple[dict[str, Any], str | int, bool]:
    """(the settings object, its indent, whether it ends in a newline). A missing file reads as an empty object.
    Refuses a folder, an unreadable file, anything that is not valid JSON, and JSON that is not an object."""
    if path.is_dir():
        raise InstallError(f"{path} is a folder, not a settings file")
    if not path.exists():
        return {}, 2, True
    text = read_text(path)
    if not text.strip():
        return {}, 2, True
    try:
        data = json.loads(text)
    except ValueError as err:
        raise InstallError(f"{path} is not valid JSON ({err}); nothing was changed: fix the file, then run this again") from err
    if not isinstance(data, dict):
        raise InstallError(f"{path} is valid JSON but not an object, which a settings file must be; nothing was changed")
    return data, _indent_of(text), text.endswith("\n")


def backup_path(path: Path, now: float | None = None) -> Path:
    """`<name>.northstar-backup-<UTC time>` beside the file; a second one in the same second gets a counter."""
    stamp = datetime.fromtimestamp(time.time() if now is None else now).strftime("%Y%m%dT%H%M%S")
    candidate = path.with_name(f"{path.name}{SETTINGS_BACKUP_TAG}{stamp}")
    n = 1
    while candidate.exists():
        n += 1
        candidate = path.with_name(f"{path.name}{SETTINGS_BACKUP_TAG}{stamp}-{n}")
    return candidate


def _write_atomically(target: Path, text: str, mode: int | None) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.northstar-{os.getpid()}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600 if mode is None else mode)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:  # newline="": the text goes out as it is
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        if mode is not None:
            os.chmod(tmp, mode)
        os.replace(tmp, target)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


# --- splicing into the file's own text ---------------------------------------------------------------------------
#
# json.dumps writes a file out in its own style: it turns a one-line array into one line per element, an escape into
# the character, and so on. A user's settings file is theirs, so Northstar's entries are put into it, and taken out
# again, as edits to the text: a position and the text to put there. Everything outside those positions is untouched.


@dataclass(slots=True)
class _Node:
    """A JSON value in a text: where it starts and ends, and its members (object) or items (array)."""

    kind: str  # object, array or scalar
    start: int
    end: int
    members: list["_Member"] = field(default_factory=list)
    items: list["_Node"] = field(default_factory=list)


@dataclass(slots=True)
class _Member:
    key: str
    start: int  # where its key's quote is
    value: _Node

    @property
    def end(self) -> int:
        return self.value.end


_STRING = re.compile(r'"(?:[^"\\]|\\.)*"', re.S)
_SCALAR = re.compile(r"[^\s,\]}]+")
_Edit = tuple[int, int, str]  # replace text[start:end] with the string


def _skip_space(text: str, i: int) -> int:
    while i < len(text) and text[i] in " \t\r\n":
        i += 1
    return i


def _parse_value(text: str, i: int) -> _Node:
    """The node that starts at `i` in `text`, which json.loads has already accepted (so this only finds the edges)."""
    c = text[i]
    if c == "{":
        node = _Node("object", i, i)
        i = _skip_space(text, i + 1)
        while text[i] != "}":
            key = _STRING.match(text, i)
            assert key is not None
            colon = _skip_space(text, key.end())
            value = _parse_value(text, _skip_space(text, colon + 1))
            node.members.append(_Member(json.loads(key.group()), i, value))
            i = _skip_space(text, value.end)
            if text[i] == ",":
                i = _skip_space(text, i + 1)
        node.end = i + 1
        return node
    if c == "[":
        node = _Node("array", i, i)
        i = _skip_space(text, i + 1)
        while text[i] != "]":
            item = _parse_value(text, i)
            node.items.append(item)
            i = _skip_space(text, item.end)
            if text[i] == ",":
                i = _skip_space(text, i + 1)
        node.end = i + 1
        return node
    match = _STRING.match(text, i) if c == '"' else _SCALAR.match(text, i)
    assert match is not None
    return _Node("scalar", i, match.end())


def _member(node: _Node, key: str) -> _Member | None:
    return next((m for m in node.members if m.key == key), None)


def _value_of(text: str, node: _Node) -> Any:
    return json.loads(text[node.start : node.end])


def _line_indent(text: str, pos: int) -> str:
    start = text.rfind("\n", 0, pos) + 1
    end = start
    while end < len(text) and text[end] in " \t":
        end += 1
    return text[start:end]


def _unit(indent: str | int) -> str:
    return indent if isinstance(indent, str) else " " * indent


def _render(value: Any, indent: str, multiline: bool, unit: str, nl: str, key: str | None = None) -> str:
    """`value` (or `"key": value`) as text for a place indented by `indent`: on one line, or in the file's own indent."""
    head = "" if key is None else json.dumps(key, ensure_ascii=False) + ": "
    if not multiline:
        return head + json.dumps(value, ensure_ascii=False)
    body = json.dumps(value, indent=unit or None, ensure_ascii=False)
    return head + body.replace("\n", nl + indent)


def _removals(node: _Node, spans: list[tuple[int, int]], drop: set[int]) -> list[_Edit]:
    """Edits that take the children `drop` out of a container whose children sit at `spans`, with the comma and the
    space that went with each: a child that has one after it takes up to the next child's start, and the last child
    takes the comma and space before it. A container left with nothing keeps its brackets and nothing between."""
    if not drop:
        return []
    if len(drop) == len(spans):
        return [(node.start + 1, node.end - 1, "")]
    edits: list[_Edit] = []
    i = 0
    while i < len(spans):
        if i not in drop:
            i += 1
            continue
        j = i
        while j + 1 < len(spans) and (j + 1) in drop:
            j += 1
        if j + 1 < len(spans):
            edits.append((spans[i][0], spans[j + 1][0], ""))
        else:
            edits.append((spans[i - 1][1], spans[j][1], ""))  # i > 0: something is kept
        i = j + 1
    return edits


def _member_spans(node: _Node) -> list[tuple[int, int]]:
    return [(m.start, m.end) for m in node.members]


def _item_spans(node: _Node) -> list[tuple[int, int]]:
    return [(n.start, n.end) for n in node.items]


def _append(text: str, node: _Node, children: list[Any], unit: str, nl: str, keys: list[str] | None) -> _Edit:
    """The edit that adds `children` (values, or members when `keys` names them) after a container's last child, in
    the style of the children it has: the same space and line break before each, and on one line where they are."""
    spans = _member_spans(node) if node.kind == "object" else _item_spans(node)
    if spans:
        gap = text[spans[-2][1] : spans[-1][0]] if len(spans) > 1 else text[node.start + 1 : spans[0][0]]
        sep = gap.replace(",", "", 1)
        multiline = "\n" in sep
        indent = sep.rsplit("\n", 1)[-1] if multiline else ""
        out = "".join(
            "," + sep + _render(v, indent, multiline, unit, nl, None if keys is None else keys[n]) for n, v in enumerate(children)
        )
        return (spans[-1][1], spans[-1][1], out)
    multiline = "\n" in text
    outer = _line_indent(text, node.start)
    indent = outer + unit
    sep = nl + indent if multiline else ""
    out = ("," + sep).join(_render(v, indent, multiline, unit, nl, None if keys is None else keys[n]) for n, v in enumerate(children))
    return (node.start + 1, node.end - 1, sep + out + (nl + outer if multiline else ""))


def _apply_edits(text: str, edits: list[_Edit]) -> str:
    for start, end, new in sorted(edits, key=lambda e: (e[0], e[1]), reverse=True):
        text = text[:start] + new + text[end:]
    return text


def _same_json(a: Any, b: Any) -> bool:
    """Equal, key order included."""
    return json.dumps(a, ensure_ascii=False) == json.dumps(b, ensure_ascii=False)


def _hook_groups(text: str, groups: _Node) -> list[tuple[_Node, list[tuple[int, _Node, bool]]]]:
    """Each group of an event, with its hooks as (index, node, is ours). Shapes were checked by the merge."""
    out = []
    for group in groups.items:
        listed = _member(group, "hooks")
        hooks = listed.value.items if listed is not None and listed.value.kind == "array" else []
        out.append((group, [(i, h, is_northstar_hook(_value_of(text, h))) for i, h in enumerate(hooks)]))
    return out


def splice_merge(text: str, python: str, indent: str | int) -> str | None:
    """`text` with Northstar's hooks put in as edits to it, or None when that cannot be done (a file with nothing in
    it, an unusual shape, or a result that is not the settings merge_hooks gives)."""
    try:
        data = json.loads(text)
        want, _ = merge_hooks(data, python)
        root = _parse_value(text, _skip_space(text, 0))
        if root.kind != "object":
            return None
        unit, nl = _unit(indent), "\r\n" if "\r\n" in text else "\n"
        edits: list[_Edit] = []
        member = _member(root, "hooks")
        if member is None:
            edits.append(_append(text, root, [hooks_config(python)], unit, nl, ["hooks"]))
        else:
            hooks = member.value
            new_events: list[tuple[str, Any]] = []
            for event in EVENTS:
                entry = hook_entry(event, python)
                m = _member(hooks, event)
                if m is None:
                    new_events.append((event, [{"hooks": [entry]}]))
                    continue
                groups = _hook_groups(text, m.value)
                found = [(gi, hi, node) for gi, (_, hs) in enumerate(groups) for hi, node, ours in hs if ours]
                if not found:
                    edits.append(_append(text, m.value, [{"hooks": [entry]}], unit, nl, None))
                    continue
                first_gi, _, first = found[0]
                if _value_of(text, first) != entry:
                    multiline = "\n" in text[first.start : first.end]
                    edits.append((first.start, first.end, _render(entry, _line_indent(text, first.start), multiline, unit, nl)))
                drop_groups: set[int] = set()
                for gi, (group, hs) in enumerate(groups):
                    drop = {hi for g2, hi, _ in found[1:] if g2 == gi}
                    if not drop:
                        continue
                    if len(drop) == len(hs) and gi != first_gi:
                        drop_groups.add(gi)  # nothing of the user's left in it: the group goes
                    else:
                        listed = _member(group, "hooks")
                        assert listed is not None
                        edits.extend(_removals(listed.value, _item_spans(listed.value), drop))
                edits.extend(_removals(m.value, _item_spans(m.value), drop_groups))
            if new_events:
                edits.append(_append(text, hooks, [v for _, v in new_events], unit, nl, [k for k, _ in new_events]))
        out = _apply_edits(text, edits)
        return out if _same_json(json.loads(out), want) else None
    except Exception:  # whatever went wrong, the caller writes the file out again; a splice is only used when it checks out
        return None


def splice_remove(text: str) -> str | None:
    """`text` without Northstar's hooks, as edits to it (see `splice_merge` for when this gives None)."""
    try:
        data = json.loads(text)
        want, changes = remove_hooks(data)
        if not changes:
            return text
        root = _parse_value(text, _skip_space(text, 0))
        member = _member(root, "hooks")
        if root.kind != "object" or member is None or member.value.kind != "object":
            return None
        hooks = member.value
        edits: list[_Edit] = []
        drop_events: set[int] = set()
        for ei, event in enumerate(hooks.members):
            if event.value.kind != "array":
                continue
            groups = _hook_groups(text, event.value)
            drop_groups: set[int] = set()
            touched = False
            for gi, (group, hs) in enumerate(groups):
                ours = {i for i, _, is_ours in hs if is_ours}
                if not ours:
                    continue
                touched = True
                if len(ours) == len(hs):
                    drop_groups.add(gi)
                else:
                    listed = _member(group, "hooks")
                    assert listed is not None
                    edits.extend(_removals(listed.value, _item_spans(listed.value), ours))
            if touched and len(drop_groups) == len(groups):
                drop_events.add(ei)
            else:
                edits.extend(_removals(event.value, _item_spans(event.value), drop_groups))
        if len(drop_events) == len(hooks.members):
            index = root.members.index(member)
            edits = _removals(root, _member_spans(root), {index})  # the whole "hooks" key goes, and all that is inside
        else:
            edits.extend(_removals(hooks, _member_spans(hooks), drop_events))
        out = _apply_edits(text, edits)
        return out if _same_json(json.loads(out), want) else None
    except Exception:  # as in splice_merge
        return None


@dataclass(slots=True)
class SettingsPlan:
    path: Path
    python: str | None
    changes: list[Change]
    before: str  # the file's text now ("" if it does not exist)
    after: str
    exists: bool
    backup: Path | None = None  # where the backup is (or would be) made; None when nothing changes or there is no file
    written: bool = False

    @property
    def changed(self) -> bool:
        return any(c.action != "keep" for c in self.changes)

    def lines(self) -> list[str]:
        out = [f"settings file: {self.path}" + ("" if self.exists else "  (does not exist: it would be created)")]
        out.extend(c.line() for c in self.changes)
        if not self.changed:
            out.append("nothing to change")
        elif self.backup is not None:
            out.append(f"backup: {self.backup}")
        return out

    def diff(self) -> str:
        """A unified diff of the whole file; it can show neighbouring keys, so it is for tests and a person's own eyes."""
        return "".join(difflib.unified_diff(self.before.splitlines(True), self.after.splitlines(True), "before", "after"))


def _apply(path: Path, transform, splicer, python: str | None, *, dry_run: bool, now: float | None) -> SettingsPlan:
    path = Path(path).expanduser()
    settings, indent, newline = read_settings(path)
    before = read_text(path) if path.exists() else ""
    new, changes = transform(settings)
    plan = SettingsPlan(path, python, changes, before, before, path.exists())
    if not plan.changed:
        return plan
    spliced = splicer(before, indent) if before.strip() else None
    plan.after = spliced if spliced is not None else _dump(new, indent, newline if plan.exists and before.strip() else True)
    if plan.exists and before.strip():
        plan.backup = backup_path(path, now)
    if dry_run:
        return plan
    target = path.resolve() if path.is_symlink() else path
    mode = (os.stat(target).st_mode & 0o777) if plan.exists else None
    if plan.backup is not None:
        shutil.copy2(target, plan.backup)
    _write_atomically(target, plan.after, mode)
    plan.written = True
    return plan


def install_settings(path: Path | str, python: str | None = None, *, dry_run: bool = False, now: float | None = None) -> SettingsPlan:
    """Merge Northstar's hooks into the settings file at `path` (see the module docstring). `path` has no default."""
    interpreter = project_python() if python is None else python
    return _apply(
        Path(path), lambda s: merge_hooks(s, interpreter), lambda text, indent: splice_merge(text, interpreter, indent),
        interpreter, dry_run=dry_run, now=now,
    )


def uninstall_settings(path: Path | str, *, dry_run: bool = False, now: float | None = None) -> SettingsPlan:
    """Remove only Northstar's hooks from the settings file at `path`."""
    p = Path(path).expanduser()
    if not p.exists():
        raise InstallError(f"{p} does not exist: there is nothing to remove")
    return _apply(p, remove_hooks, lambda text, indent: splice_remove(text), None, dry_run=dry_run, now=now)


def northstar_events(settings: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """The events with a Northstar hook in a settings object (or a plugin's hooks.json), and those hooks."""
    hooks = settings.get("hooks") if isinstance(settings, dict) else None
    found: dict[str, list[dict[str, Any]]] = {}
    if not isinstance(hooks, dict):
        return found
    for event, groups in hooks.items():
        for group in groups if isinstance(groups, list) else []:
            for h in group.get("hooks", []) if isinstance(group, dict) and isinstance(group.get("hooks"), list) else []:
                if is_northstar_hook(h):
                    found.setdefault(event, []).append(h)
    return found


def installed_events(path: Path | str) -> list[str] | None:
    """Read-only: the capture events a settings file (or a plugin's hooks.json) has hooks for, or None if it cannot be read."""
    try:
        data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return sorted(northstar_events(data)) if isinstance(data, dict) else None


def hook_interpreters(path: Path | str) -> list[str]:
    """Read-only: the interpreters the Northstar hooks in a settings file (or hooks.json) name, without duplicates."""
    try:
        data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    seen: dict[str, None] = {}
    for hooks in northstar_events(data).values():
        for h in hooks:
            if isinstance(h.get("command"), str) and MODULE not in h["command"]:
                seen[h["command"]] = None
    return list(seen)


# --- a local plugin folder -------------------------------------------------------------------------------------


def plugin_files(python: str) -> dict[str, str]:
    """The plugin's files, as relative path -> text. The plugin holds no secrets (§14.1)."""
    manifest = {"name": PLUGIN_NAME, "version": __version__, "description": PLUGIN_DESCRIPTION}
    market = {
        "name": MARKETPLACE_NAME,
        "owner": {"name": "Northstar (this machine)"},
        "plugins": [{"name": PLUGIN_NAME, "source": "./", "description": PLUGIN_DESCRIPTION}],
    }
    return {
        ".claude-plugin/plugin.json": json.dumps(manifest, indent=2) + "\n",
        ".claude-plugin/marketplace.json": json.dumps(market, indent=2) + "\n",
        "hooks/hooks.json": json.dumps({"hooks": hooks_config(python)}, indent=2) + "\n",
    }


@dataclass(slots=True)
class PluginPlan:
    folder: Path
    python: str
    files: dict[str, str]
    status: dict[str, str] = field(default_factory=dict)  # relative path -> new, changed, same
    written: bool = False

    @property
    def changed(self) -> bool:
        return any(s != "same" for s in self.status.values())

    def lines(self) -> list[str]:
        out = [f"plugin folder: {self.folder}"]
        for rel, state in self.status.items():
            out.append(f"  {state:<7} {rel}")
        out.append("hooks command: " + self.python + " -P -m " + MODULE + " <Event>")
        out.append("events: " + ", ".join(EVENTS))
        return out


def render_plugin(folder: Path | str, python: str | None = None, *, dry_run: bool = False) -> PluginPlan:
    """Write the plugin's files into `folder` (made if missing): a self-contained plugin, with the absolute path of the
    interpreter in every hook, that works from a marketplace install as from `--plugin-dir`. It refuses an interpreter
    that is not an absolute path, and a folder that already holds another plugin or marketplace under these file names,
    and touches no other file there. `folder` has no default."""
    target = Path(folder).expanduser()
    if target.exists() and not target.is_dir():
        raise InstallError(f"{target} is not a folder")
    interpreter = project_python() if python is None else python
    if not os.path.isabs(interpreter) or "${" in interpreter:
        # A marketplace install copies the folder into Claude Code's own plugin cache, so a path relative to the folder
        # (TEMPLATE_PYTHON is one) points at nothing there: the hooks would fail on every event.
        raise InstallError(
            f"the plugin's hooks need the absolute path of an interpreter, not {interpreter!r}: "
            "a plugin added from a marketplace is copied away from this folder"
        )
    files = plugin_files(interpreter)
    plan = PluginPlan(target, interpreter, files)
    for rel, text in files.items():
        path = target / rel
        if not path.exists():
            plan.status[rel] = "new"
            continue
        try:
            current = path.read_text(encoding="utf-8")
            data = json.loads(current)
        except (OSError, ValueError) as err:
            raise InstallError(f"{path} exists and is not valid JSON; move it away first") from err
        wanted = PLUGIN_NAME if rel.endswith("plugin.json") else MARKETPLACE_NAME if rel.endswith("marketplace.json") else None
        if wanted is not None and (not isinstance(data, dict) or data.get("name") != wanted):
            raise InstallError(f"{path} belongs to something other than Northstar's plugin; use another folder")
        if rel == "hooks/hooks.json" and not isinstance(data, dict):
            raise InstallError(f"{path} exists and is not a hooks file; use another folder")
        plan.status[rel] = "same" if current == text else "changed"
    if dry_run:
        return plan
    for rel, text in files.items():
        if plan.status[rel] != "same":
            _write_atomically(target / rel, text, None if plan.status[rel] == "new" else (os.stat(target / rel).st_mode & 0o777))
    plan.written = True
    return plan


def plugin_commands(folder: Path | str) -> list[str]:
    """The exact commands that add the plugin in Claude Code (§14.3 step 4, note 22 A11)."""
    path = str(Path(folder).expanduser().resolve())
    quoted = f'"{path}"' if " " in path else path
    return [
        "To try it in one Claude Code session:",
        f"  claude --plugin-dir {quoted}",
        "To keep it (once, in a terminal):",
        f"  claude plugin marketplace add {quoted}",
        f"  claude plugin install {PLUGIN_NAME}@{MARKETPLACE_NAME} --scope user",
        "Or inside Claude Code:",
        f"  /plugin marketplace add {path}",
        f"  /plugin install {PLUGIN_NAME}@{MARKETPLACE_NAME}",
        "Then restart Claude Code so the hooks load.",
    ]


# --- what was installed where -----------------------------------------------------------------------------------


def installs_path(root: Path | None = None) -> Path:
    return spool.capture_dir(root) / INSTALLS_FILE


def recorded_installs(root: Path | None = None) -> list[dict[str, str]]:
    """The installs this machine knows about, as {kind: settings|plugin, path, at}. `status` and `doctor` read these
    files to say whether the hooks are still there; nothing else is read from Claude Code's configuration."""
    try:
        data = json.loads(installs_path(root).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    items = data.get("installs") if isinstance(data, dict) else None
    return [i for i in items if isinstance(i, dict) and isinstance(i.get("kind"), str) and isinstance(i.get("path"), str)] if isinstance(items, list) else []


def _save_installs(items: list[dict[str, str]], root: Path | None) -> None:
    path = installs_path(root)
    spool.make_private_dirs(path.parent)
    _write_atomically(path, json.dumps({"installs": items}, indent=2) + "\n", 0o600)


def record_install(kind: str, path: Path | str, root: Path | None = None, *, now: float | None = None) -> None:
    target = str(Path(path).expanduser().resolve())
    items = [i for i in recorded_installs(root) if not (i["kind"] == kind and i["path"] == target)]
    items.append({"kind": kind, "path": target, "at": spool.local_stamp(now)})
    _save_installs(items, root)


def forget_install(kind: str, path: Path | str, root: Path | None = None) -> None:
    target = str(Path(path).expanduser().resolve())
    items = recorded_installs(root)
    kept = [i for i in items if not (i["kind"] == kind and i["path"] == target)]
    if len(kept) != len(items):
        _save_installs(kept, root)


# --- one way only, and only on an encrypted volume ---------------------------------------------------------------


def other_installs(kind: str, root: Path | None = None) -> list[dict[str, str]]:
    """The recorded installs of the other kind (settings file or plugin) that still have Northstar hooks in them."""
    out = []
    for item in recorded_installs(root):
        if item["kind"] == kind:
            continue
        target = Path(item["path"])
        hooks_file = target / "hooks" / "hooks.json" if item["kind"] == "plugin" else target
        if installed_events(hooks_file):
            out.append(item)
    return out


def refuse_duplicate(kind: str, root: Path | None = None) -> None:
    """Raise InstallError if capture is already installed the other way. With a settings file and a plugin both in
    place, Claude Code runs both sets of hooks and every turn is spooled twice. An install whose hooks are gone (the
    file edited by hand, the folder deleted) does not count."""
    others = other_installs(kind, root)
    if not others:
        return
    other = others[0]
    undo = (
        f"`northstar capture uninstall --settings {other['path']}`"
        if other["kind"] == "settings"
        else f"`claude plugin uninstall {PLUGIN_NAME}@{MARKETPLACE_NAME}`, then delete {other['path']}"
    )
    raise InstallError(
        f"capture is already installed as a {other['kind']} ({other['path']}), and a second way would record every turn "
        f"twice: nothing was changed. Use that one, or take it out first ({undo}), then run this again"
    )


def check_encryption(root: Path | None = None) -> str:
    """Check that the data root is on an encrypted volume (PL-3: the core's `require_encryption`: FileVault on the boot
    volume, or an encrypted, unlocked volume). Raises InstallError, naming the reason, when it is not: nothing is then
    installed. Imports the core, which a hook never does. Writes nothing."""
    from northstar_agent_memory import paths
    from northstar_agent_memory.core.db import EncryptionRequired, require_encryption

    base = paths.data_root() if root is None else root
    try:
        require_encryption(base)
    except EncryptionRequired as err:
        raise InstallError(f"capture is not installed, because the data folder is not known to be encrypted at rest: {err}") from err
    return f"{base} is on an encrypted volume"


def ensure_encryption(root: Path | None = None, *, dry_run: bool = False, now: float | None = None) -> str:
    """`check_encryption`, and unless `dry_run` the stamp the hook looks for (spool.write_encryption_stamp): the hook
    writes nothing until it is there."""
    detail = check_encryption(root)
    if dry_run:
        return f"{detail} (the stamp that lets the hook write would be made)"
    from northstar_agent_memory import paths

    stamp = spool.write_encryption_stamp(paths.data_root() if root is None else root, now=now)
    return f"{detail}; stamp written to {stamp}"
