"""Import past Claude Code transcripts into history.db (connectors-claude-code-and-codex.md §12 "one-off backfill";
MEMORY-ARCHITECTURE §2.2, §5.2).

`backfill(root, store)` reads a folder laid out like ~/.claude/projects (`<project>/<session>.jsonl`, and the
`<project>/<session>/subagents/*.jsonl` files newer versions keep) and writes what was said, through the same history
store and rules as live capture:

- Only sessions in scope: the gate (`scope.in_scope`) runs on each session's working folder, and again on each line's
  own folder, so a turn typed after a `cd` out of a personal folder is left out. Everything else is counted, never
  stored. Sessions started in Northstar's own folders are skipped (I24), and nothing runs at all in a hidden run.
- Secrets are replaced before anything is written (secrets.py). The words are otherwise kept as they are, fidelity
  "verbatim", speaker from Claude Code's roles (user, assistant), never inferred (I3).
- Origins are classified from Claude Code's own markers (origin.py). A user turn becomes the user's own words
  (typed, or pasted when it is all pasted text, with `paste_ranges` in meta) and, if present, one message per block
  Northstar delivered (speaker "northstar", origin northstar_injected). Hook and system injections, command
  output, compaction summaries, interrupt markers and tool traffic are not the user's words and are not stored.
- Sidechains (subagents) are not part of the conversation (§10.3): the subagent's final message is kept as an
  assistant message on branch "sidechain:<agent id>", the branch live capture uses, with `speaker_scope: subagent` in
  meta. A final already stored under that branch (live) or under the older name "subagent:<agent id>" (an earlier
  backfill) is matched by its line, else by exact text, and not written again. isMeta lines are not turns, except
  that one carrying a Northstar block is read for that block only.
- Idempotent with live capture: a message is matched by session id and the transcript line's uuid (kept in meta as
  `uuid`, with `part` for a second message from one line) and written once. A message live capture stored without a
  uuid is matched by speaker and exact text instead. A message whose place holds other words is counted as a
  conflict and left as it is; history is never overwritten (I6).
- Parsing is eval/claude_code.py's `parse_session`; this module adds the raw view the origin split needs.

A progress line goes to `progress` for each project and a summary at the end. Run again after a session grows and only
its new lines are written.

Work events from git are not recorded here: a commit counts as made "during a captured session" only live
(work_events.py).
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from northstar_agent_memory import config as config_module
from northstar_agent_memory.capture import origin, scope
from northstar_agent_memory.capture.secrets import Finding, scrub, tally
from northstar_agent_memory.core.history import HistoryConflict, SQLiteHistoryStore
from northstar_agent_memory.eval.claude_code import APP, FAMILY, ParsedSession, parse_session, parse_time
from northstar_agent_memory.transcript import Message, Source

_PEEK_LINES = 400  # how far into a file to look for its working folder
SUBAGENT_BRANCH = "sidechain:"  # the branch of a subagent's final message: live capture's name for it (ingest.py)
OLD_SUBAGENT_BRANCH = "subagent:"  # what this module called it before: stored finals under it still count


@dataclass(slots=True)
class ProjectReport:
    name: str
    sessions_in_scope: int = 0
    sessions_out_of_scope: int = 0
    messages_written: int = 0
    messages_skipped: int = 0  # already stored, in conflict, or not captured


@dataclass(slots=True)
class BackfillReport:
    projects: list[ProjectReport] = field(default_factory=list)
    sessions_in_scope: int = 0
    sessions_out_of_scope: int = 0
    sessions_own_runs: int = 0  # started in Northstar's own folders (I24)
    sessions_unreadable: int = 0
    sessions_conflict: int = 0  # the id is stored with another kind or scope
    messages_written: int = 0
    messages_already_stored: int = 0
    messages_conflict: int = 0
    not_captured: Counter[str] = field(default_factory=Counter)  # messages left out, by reason
    lines_skipped: Counter[str] = field(default_factory=Counter)  # transcript lines that are not turns, by type
    secrets: Counter[str] = field(default_factory=Counter)  # secrets removed, by kind
    hidden_run: bool = False

    @property
    def messages_skipped(self) -> int:
        return self.messages_already_stored + self.messages_conflict + sum(self.not_captured.values())

    def summary_lines(self) -> list[str]:
        if self.hidden_run:
            return ["Backfill: nothing done, this is one of Northstar's own runs (NORTHSTAR_HIDDEN_RUN)."]
        secrets = ", ".join(f"{kind} {n}" for kind, n in sorted(self.secrets.items())) or "none"
        left_out = ", ".join(f"{why} {n}" for why, n in sorted(self.not_captured.items())) or "none"
        lines = ", ".join(f"{why} {n}" for why, n in sorted(self.lines_skipped.items()))
        return [
            f"Backfill: {self.sessions_in_scope} sessions in scope, {self.sessions_out_of_scope} out of scope"
            f" ({self.sessions_own_runs} of Northstar's own runs, {self.sessions_unreadable} unreadable)",
            f"Messages: {self.messages_written} written, {self.messages_already_stored} already stored,"
            f" {self.messages_conflict} in conflict, {sum(self.not_captured.values())} not captured",
            f"Not captured, by reason: {left_out}",
            f"Transcript lines that are not turns: {lines or 'none'}",
            f"Secrets removed, by kind: {secrets}",
        ]


# --- reading a transcript, raw --------------------------------------------------------------------------------


@dataclass(slots=True)
class _Line:
    index: int  # the line's position in its file: the order messages are written in
    cwd: str | None
    user_text: str | None  # a user line's text blocks, joined as the parser joins them
    meta: bool
    sidechain: bool


@dataclass(slots=True)
class _Final:
    """The last thing a subagent said."""

    session_id: str
    agent_key: str
    uuid: str
    timestamp: str | None
    cwd: str | None
    text: str
    index: int


@dataclass(slots=True)
class _Raw:
    lines: dict[str, _Line] = field(default_factory=dict)  # by uuid
    finals: list[_Final] = field(default_factory=list)


def _text_blocks(content: Any) -> list[str]:
    if isinstance(content, str):
        return [content]
    if isinstance(content, list):
        return [b["text"] for b in content if isinstance(b, dict) and b.get("type") == "text" and isinstance(b.get("text"), str)]
    return []


def _peek(path: Path) -> tuple[str | None, str | None]:
    """(working folder, session id) from the first lines that name them."""
    cwd = sid = None
    with path.open(encoding="utf-8", errors="replace") as fh:
        for n, raw in enumerate(fh):
            if n >= _PEEK_LINES or (cwd and sid):
                break
            try:
                obj = json.loads(raw)
            except ValueError:
                continue
            if not isinstance(obj, dict):
                continue
            cwd = cwd or (obj["cwd"] if isinstance(obj.get("cwd"), str) and obj["cwd"] else None)
            sid = sid or (obj["sessionId"] if isinstance(obj.get("sessionId"), str) and obj["sessionId"] else None)
    return cwd, sid


def _read_raw(path: Path) -> _Raw:
    raw = _Raw()
    finals: dict[tuple[str, str], _Final] = {}
    with path.open(encoding="utf-8", errors="replace") as fh:
        for index, text in enumerate(fh):
            try:
                obj = json.loads(text)
            except ValueError:
                continue
            if not isinstance(obj, dict) or obj.get("type") not in ("user", "assistant"):
                continue
            uuid = obj.get("uuid") if isinstance(obj.get("uuid"), str) else None
            cwd = obj.get("cwd") if isinstance(obj.get("cwd"), str) else None
            message = obj.get("message") if isinstance(obj.get("message"), dict) else {}
            texts = _text_blocks(message.get("content"))
            sidechain = bool(obj.get("isSidechain"))
            if uuid:
                raw.lines[uuid] = _Line(
                    index, cwd, "\n".join(texts) if obj["type"] == "user" else None, bool(obj.get("isMeta")), sidechain
                )
            if sidechain and obj["type"] == "assistant" and uuid and any(t.strip() for t in texts):
                sid = obj.get("sessionId") if isinstance(obj.get("sessionId"), str) else path.stem
                stem = path.stem[len("agent-"):] if path.stem.startswith("agent-") else path.stem  # agent-<id>.jsonl
                key = str(obj.get("agentId") or stem)
                body = "\n\n".join(t for t in texts if t.strip())
                finals[(sid, key)] = _Final(sid, key, uuid, obj.get("timestamp") if isinstance(obj.get("timestamp"), str) else None, cwd, body, index)
    raw.finals = list(finals.values())
    return raw


# --- the project folders -------------------------------------------------------------------------------------


def _projects(root: Path) -> dict[str, list[Path]]:
    """Transcript files by project: the first folder below root (files straight in root go under its own name)."""
    out: dict[str, list[Path]] = {}
    for path in sorted(root.rglob("*.jsonl")):
        rel = path.relative_to(root)
        out.setdefault(rel.parts[0] if len(rel.parts) > 1 else root.name, []).append(path)
    return out


_EARLIEST = datetime.min.replace(tzinfo=timezone.utc)


def _sort_key(s: ParsedSession) -> tuple:
    return (parse_time(s.first_timestamp) or _EARLIEST, parse_time(s.last_timestamp) or _EARLIEST, s.path)


def _scope_of(cwd: str, config: Mapping[str, Any]) -> str:
    return scope.project_scope(cwd, config) or "personal"


# --- one session ---------------------------------------------------------------------------------------------


@dataclass(slots=True)
class _Item:
    """One message to write, before it has an ordinal."""

    index: int
    uuid: str
    part: str  # "" for the line's first message, "n0", "n1" ... for Northstar blocks in it
    speaker: str
    origin: str
    text: str
    occurred_at: str | None
    model_family: str | None = None
    meta: dict = field(default_factory=dict)


def _scrub_user(parts: origin.TurnParts) -> tuple[str, list[list[int]], list[Finding]]:
    """The user's words with secrets replaced, and the paste ranges moved to match."""
    text, found = parts.user_text, []
    if not parts.paste_ranges:
        text, found = scrub(text)
        return text, [], found
    pieces: list[str] = []
    ranges: list[list[int]] = []
    pos = size = 0
    cuts = [(0, 0)] + list(parts.paste_ranges)
    for start, end in cuts[1:]:
        for chunk, pasted in ((text[pos:start], False), (text[start:end], True)):
            clean, f = scrub(chunk)
            found += f
            if pasted and clean:
                ranges.append([size, size + len(clean)])
            pieces.append(clean)
            size += len(clean)
        pos = end
    clean, f = scrub(text[pos:])
    found += f
    pieces.append(clean)
    joined = "".join(pieces)
    again, f = scrub(joined)  # a secret that spans a boundary
    if again != joined:
        found += f
        return again, [], found
    return joined, ranges, found


class _Writer:
    """Writes one project's sessions and keeps the report."""

    def __init__(self, store: SQLiteHistoryStore, config: Mapping[str, Any], report: BackfillReport) -> None:
        self.store = store
        self.config = config
        self.report = report
        self.allowed: dict[str, bool] = {}

    def allowed_cwd(self, cwd: str | None) -> bool:
        if not cwd:
            return True  # the session's own folder was already checked
        if cwd not in self.allowed:
            self.allowed[cwd] = scope.in_scope(cwd, self.config)
        return self.allowed[cwd]

    def skip(self, reason: str, n: int = 1) -> None:
        self.report.not_captured[reason] += n

    # -- building the items --

    def items(self, parsed: ParsedSession, raw: _Raw, seen_uuids: set[str]) -> list[_Item]:
        out: list[_Item] = []
        for m in parsed.source.messages:
            uuid = m.meta.get("uuid")
            line = raw.lines.get(uuid) if isinstance(uuid, str) else None
            if not isinstance(uuid, str):
                self.skip("no_uuid")
                continue
            seen_uuids.add(uuid)
            if not self.allowed_cwd(line.cwd if line else None):
                self.skip("out_of_scope_turn")
                continue
            index = line.index if line else 0
            if m.speaker == "tool":
                self.skip("tool_use")
            elif m.speaker == "assistant":
                text, found = scrub(m.text)
                tally(found, self.report.secrets)
                meta = {"uuid": uuid, "message_id": m.meta.get("message_id"), "model": m.meta.get("model")}
                out.append(_Item(index, uuid, "", "assistant", "assistant_output", text, m.occurred_at, FAMILY, meta))
            elif m.speaker == "user":
                out.extend(self._user_items(m, line, uuid, index))
            else:
                self.skip(f"speaker:{m.speaker}")
        # Meta lines are not turns; one that carries a Northstar block is read for the block (I24).
        for uuid, line in raw.lines.items():
            if uuid in seen_uuids or line.sidechain or line.user_text is None or not origin.contains_northstar_block(line.user_text):
                continue
            if not self.allowed_cwd(line.cwd):
                self.skip("out_of_scope_turn")
                continue
            parts = origin.split_turn(line.user_text)
            out.extend(self._northstar_items(parts, uuid, line.index, None))
        out.sort(key=lambda i: (i.index, i.part))
        return out

    def _user_items(self, m: Message, line: _Line | None, uuid: str, index: int) -> list[_Item]:
        if line is None or line.user_text is None:
            # No raw line to split (should not happen): the parser's text, which already has wrappers removed.
            parts = origin.TurnParts(spans=[], user_text=m.text, paste_ranges=[tuple(r) for r in m.meta.get("paste_ranges", [])])
        else:
            parts = origin.split_turn(line.user_text)
            for why, n in parts.dropped.items():
                self.skip(f"injected:{why}", n)
        out: list[_Item] = []
        if parts.user_text:
            text, ranges, found = _scrub_user(parts)
            tally(found, self.report.secrets)
            meta: dict[str, Any] = {"uuid": uuid}
            if ranges:
                meta["paste_ranges"] = ranges
            if parts.command:
                meta["command"] = parts.command
            out.append(_Item(index, uuid, "", "user", parts.user_origin, text, m.occurred_at, None, meta))
        else:
            self.skip("no_user_words")
        out.extend(self._northstar_items(parts, uuid, index, m.occurred_at))
        return out

    def _northstar_items(self, parts: origin.TurnParts, uuid: str, index: int, when: str | None) -> list[_Item]:
        out = []
        for k, block in enumerate(parts.northstar):
            text, found = scrub(block)
            tally(found, self.report.secrets)
            out.append(_Item(index, uuid, f"n{k}", "northstar", "northstar_injected", text, when, None, {"uuid": uuid, "part": f"n{k}"}))
        return out

    # -- writing --

    def write_session(self, parsed: ParsedSession, raw: _Raw, cwd: str) -> int:
        """Write one session's messages; returns how many were new."""
        sid = parsed.source.id
        seen: set[str] = set()
        items = self.items(parsed, raw, seen)
        info = self.store.get_source_info(sid)
        if info is not None and info["kind"] != "chat":
            self.report.sessions_conflict += 1
            return 0
        title, found = scrub(parsed.source.title) if parsed.source.title else (None, [])
        tally(found, self.report.secrets)
        source = Source(
            id=sid, kind="chat", app=APP, project=Path(cwd).name or None, title=title,
            started_at=parsed.source.started_at,
            meta={"cwd": cwd, "git_branch": parsed.git_branch, "capture": "backfill"},
        )
        with self.store.batch():
            if info is None:
                self.store.add_source(source, scope=_scope_of(cwd, self.config))
            written = self._append(sid, items, branch=None)
        for why, n in parsed.skipped.items():
            self.report.lines_skipped[why] += n
        return written

    def _append(self, sid: str, items: list[_Item], branch: str | None, also: tuple[str, ...] = ()) -> int:
        """Write the items on `branch`. `also` names other branches whose messages count as the same (an old name)."""
        stored = [s.message for s in self.store.messages_for_source(sid)]
        known_ids = {m.id: m for m in stored}
        known_keys = {(m.meta.get("uuid"), m.meta.get("part", "")): m for m in stored if m.meta.get("uuid")}
        names = {branch, *also}
        live = Counter((m.speaker, m.text) for m in stored if not m.meta.get("uuid") and m.branch in names)
        ordinals = [m.ordinal for m in stored if m.branch == branch]
        next_ordinal = max(ordinals) + 1 if ordinals else 0
        written = 0
        for item in items:
            message_id = f"{sid}:{item.uuid}" + (f":{item.part}" if item.part else "")
            have = known_ids.get(message_id) or known_keys.get((item.uuid, item.part))
            if have is not None:
                if have.text == item.text:
                    self.report.messages_already_stored += 1
                else:  # stored with other words (a response caught half-written): left as it is, never overwritten
                    self.report.messages_conflict += 1
                continue
            if live[(item.speaker, item.text)] > 0:  # live capture stored it without the line's uuid
                live[(item.speaker, item.text)] -= 1
                self.report.messages_already_stored += 1
                continue
            message = Message(
                id=message_id, source_id=sid, ordinal=next_ordinal, speaker=item.speaker, text=item.text,  # type: ignore[arg-type]
                occurred_at=item.occurred_at, origin=item.origin, agent=APP,  # type: ignore[arg-type]
                model_family=item.model_family, branch=branch, meta={**item.meta, "capture": "backfill"},
            )
            try:
                added = self.store.append_message(message, fidelity="verbatim")
            except HistoryConflict:
                self.report.messages_conflict += 1
                continue
            if added:
                next_ordinal += 1
                written += 1
                self.report.messages_written += 1
            else:
                self.report.messages_already_stored += 1
        return written

    def write_subagents(self, finals: list[_Final]) -> int:
        """A subagent's last message on its own branch (§10.3), for sessions already in the store."""
        written = 0
        for final in finals:
            if self.store.get_source_info(final.session_id) is None:
                self.skip("subagent_without_session")
                continue
            if not self.allowed_cwd(final.cwd):
                self.skip("out_of_scope_turn")
                continue
            text, found = scrub(final.text)
            tally(found, self.report.secrets)
            item = _Item(
                0, final.uuid, "", "assistant", "assistant_output", text, final.timestamp, FAMILY,
                {"uuid": final.uuid, "speaker_scope": "subagent", "agent_ref": final.agent_key},
            )
            written += self._append(
                final.session_id, [item], branch=SUBAGENT_BRANCH + final.agent_key,
                also=(OLD_SUBAGENT_BRANCH + final.agent_key,),
            )
        return written


# --- the entry point -----------------------------------------------------------------------------------------


def backfill(
    root: str | Path,
    store: SQLiteHistoryStore,
    *,
    config: Mapping[str, Any] | None = None,
    progress: Callable[[str], None] | None = print,
) -> BackfillReport:
    """Import the transcripts under `root` into `store`. See the module docstring for the rules.

    `config` is the settings (the scope gate reads `[capture] personal_paths`); `progress` gets one line per project and
    the summary lines (None for silence).
    """
    say = progress or (lambda line: None)
    report = BackfillReport()
    if scope.hidden_run():
        report.hidden_run = True
        for line in report.summary_lines():
            say(line)
        return report
    cfg = config_module.load() if config is None else config
    writer = _Writer(store, cfg, report)
    base = Path(root).expanduser()
    for name, files in _projects(base).items():
        project = ProjectReport(name)
        before = report.messages_skipped
        in_scope: list[tuple[Path, str]] = []
        in_ids: set[str] = set()
        out_ids: set[str] = set()
        own_ids: set[str] = set()
        for path in files:
            try:
                cwd, sid = _peek(path)
            except OSError:
                report.sessions_unreadable += 1
                continue
            key = sid or path.stem
            if origin.inside_data_root(cwd):
                own_ids.add(key)
            elif cwd and scope.in_scope(cwd, cfg):
                in_scope.append((path, cwd))
                in_ids.add(key)
            else:
                out_ids.add(key)
        out_ids -= in_ids | own_ids
        own_ids -= in_ids
        project.sessions_in_scope = len(in_ids)
        project.sessions_out_of_scope = len(out_ids) + len(own_ids)
        report.sessions_in_scope += len(in_ids)
        report.sessions_out_of_scope += len(out_ids)
        report.sessions_own_runs += len(own_ids)
        project.messages_written = _write_project(writer, in_scope)
        project.messages_skipped = report.messages_skipped - before
        report.projects.append(project)
        say(
            f"{name}: {project.sessions_in_scope} sessions in scope, {project.sessions_out_of_scope} out of scope,"
            f" {project.messages_written} messages written, {project.messages_skipped} skipped"
        )
    for line in report.summary_lines():
        say(line)
    return report


def _write_project(writer: _Writer, files: list[tuple[Path, str]]) -> int:
    """Parse the project's in-scope files, count each copied line once (a fork or an old-style resume copies lines
    into a later file, as `parse_projects` does), write the sessions, then the subagents' final messages."""
    parsed: list[tuple[ParsedSession, str, _Raw]] = []
    for path, cwd in files:
        try:
            parsed.append((parse_session(path), cwd, _read_raw(path)))
        except OSError:
            writer.report.sessions_unreadable += 1
    parsed.sort(key=lambda t: _sort_key(t[0]))
    seen: set[str] = set()
    finals: list[_Final] = []
    written = 0
    for session, cwd, raw in parsed:
        if session.line_keys & seen:
            session = parse_session(session.path, skip=seen)
        seen |= session.line_keys
        finals.extend(raw.finals)
        has_northstar = any(
            ln.user_text and origin.contains_northstar_block(ln.user_text) for ln in raw.lines.values() if not ln.sidechain
        )
        if session.source.messages or has_northstar:
            written += writer.write_session(session, raw, cwd)
    return written + writer.write_subagents(finals)
