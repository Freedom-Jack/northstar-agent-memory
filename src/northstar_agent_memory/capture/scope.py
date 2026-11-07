"""The scope gate and the self-capture guard (connectors-claude-code-and-codex.md §7, §11; MEMORY-ARCHITECTURE §7 I24).

Only a session whose working folder lies inside one of the user's personal folders is captured. The folders are
`[capture] personal_paths` in <data root>/settings.toml ("~" allowed). Everything else is ignored silently: no spool
line, no log line, no counter.

- The working folder is resolved before it is compared (symlinks followed, "~" expanded), so a link inside a personal
  folder that points out of it does not count, and one that points in does.
- A worktree under a personal repository counts: Claude Code keeps them in <repo>/.claude/worktrees/<name>, which is
  inside the repository's folder.
- Folders are compared the way the volume does. macOS (APFS and HFS+ as shipped) and Windows ignore case, so there
  "~/personal" is the folder "~/Personal" and a working folder spelled in another case is still inside it; Linux does
  not. The comparison goes through `os.path.normcase` plus case folding (and, on macOS, Unicode normalisation, which
  APFS also ignores), per path part, so "Personal2" is never taken for "Personal". Names that are shown or used for
  a project keep their own spelling.
- The data root is never in scope, even when it lies inside a personal folder: Northstar's own runs start in an empty
  folder under it (models/harness.py) and are never captured (I24).
- A hidden run (a Northstar-launched `claude -p` or `codex exec`) carries NORTHSTAR_HIDDEN_RUN=1 in its environment,
  which the hooks it starts inherit. Hooks and the ingester stop at once when it is set.

Python's standard library and paths.py only: the hook runs on every event and pays for each import.
"""

from __future__ import annotations

import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Mapping

from northstar_agent_memory import paths

HIDDEN_RUN_ENV = "NORTHSTAR_HIDDEN_RUN"

_WORKTREES = (".claude", "worktrees")

# Whether this platform's usual file system ignores case. A module value, so a test can try both.
CASE_INSENSITIVE = sys.platform in ("darwin", "win32")


def hidden_run(env: Mapping[str, str] | None = None) -> bool:
    """True when this process is one of Northstar's own hidden runs (I24): the marker is set to anything but "" or "0"."""
    env = os.environ if env is None else env
    return env.get(HIDDEN_RUN_ENV, "") not in ("", "0")


def _resolve(path: object) -> Path | None:
    """An absolute, resolved path, or None for anything that is not one (empty, relative, unreadable)."""
    if not isinstance(path, (str, os.PathLike)) or not str(path).strip():
        return None
    try:
        expanded = Path(os.path.expanduser(str(path)))
        if not expanded.is_absolute():
            return None
        return expanded.resolve()
    except (OSError, RuntimeError, ValueError):  # a symlink loop, a NUL byte, no home folder
        return None


def personal_paths(config: Mapping[str, Any]) -> list[Path]:
    """The personal folders from `[capture].personal_paths`, resolved. A single string counts as a list of one."""
    section = config.get("capture", {}) if isinstance(config, Mapping) else {}
    raw = section.get("personal_paths", []) if isinstance(section, Mapping) else []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, (list, tuple)):
        return []
    return [p for p in (_resolve(item) for item in raw) if p is not None]


def _fold(part: str) -> str:
    """One path part as the file system compares it: normcase and case folding where case is ignored (then in one
    Unicode form, which APFS ignores too). On a case-sensitive file system, the part itself."""
    if not CASE_INSENSITIVE:
        return part
    return unicodedata.normalize("NFC", os.path.normcase(part).casefold())


def _key(path: Path) -> tuple[str, ...]:
    return tuple(_fold(part) for part in path.parts)


def _inside(path: Path, root: Path) -> bool:
    """Whether `path` is `root` or lies below it, part by part (so /a/b2 is not inside /a/b)."""
    mine, theirs = _key(path), _key(root)
    return mine[: len(theirs)] == theirs


def _owner(cwd: object, config: Mapping[str, Any], data_root: Path | None) -> tuple[Path, Path] | None:
    """(resolved working folder, the personal folder that holds it), or None when out of scope."""
    resolved = _resolve(cwd)
    if resolved is None:
        return None
    root = _resolve(paths.data_root() if data_root is None else data_root)
    if root is not None and _inside(resolved, root):
        return None
    for personal in personal_paths(config):
        if _inside(resolved, personal):
            return resolved, personal
    return None


def in_scope(cwd: object, config: Mapping[str, Any], *, data_root: Path | None = None) -> bool:
    """Whether a session working in `cwd` is captured (§7). `data_root` is for tests; it defaults to paths.data_root()."""
    return _owner(cwd, config, data_root) is not None


def _slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-.") or "root"


def project_scope(cwd: object, config: Mapping[str, Any], *, data_root: Path | None = None) -> str | None:
    """The scope a source starts with: "project:<name>", where the project is the repository that holds `cwd`
    (MEMORY-ARCHITECTURE §2.7: project by default). None when `cwd` is out of scope.

    A Claude Code worktree is named for the repository it hangs from. Where no repository is found between `cwd`
    and the personal folder, the project is the first folder below the personal folder (or the personal folder
    itself, when `cwd` is that folder).
    """
    found = _owner(cwd, config, data_root)
    if found is None:
        return None
    resolved, personal = found
    parts = resolved.parts
    folded = _key(resolved)
    for i in range(len(parts) - 1):
        if folded[i : i + 2] == tuple(_fold(name) for name in _WORKTREES):
            resolved = Path(*parts[:i]) if i else Path(parts[0])
            break
    if not _inside(resolved, personal):  # a worktree folder cut back to above the personal folder
        resolved = personal
    here, home = _key(resolved), _key(personal)
    probe = resolved
    while True:
        if (probe / ".git").exists():
            return "project:" + _slug(probe.name)
        if _key(probe) == home or probe == probe.parent:
            break
        probe = probe.parent
    if here == home:
        return "project:" + _slug(personal.name)
    return "project:" + _slug(resolved.parts[len(personal.parts)])  # the first folder below the personal folder
