"""The ingester: the one writer of chat history (MEMORY-ARCHITECTURE §2.2, §5.2; connectors-claude-code-and-codex.md §4.2, §8, §12).

`python -m northstar_agent_memory.capture.ingest --drain` reads the spool the hooks wrote (spool.py) and writes
history.db through SQLiteHistoryStore. A lock file allows one ingester at a time; it exits when the spool is drained.
The hooks start it after each event; nothing else writes history.

What it writes, from the app's own events and roles (I3), never inferred by a model, and never changed afterwards (I20):
- One source per Claude Code session: id = the session id, kind "chat", app "claude-code", project = the working
  folder, started_at, scope "project:<repository>" (scope.project_scope), and in its meta how capture began.
- UserPromptSubmit: the prompt is split by origin.split_turn, the same split the backfill makes, so live and
  backfilled histories agree. The user's own words are speaker "user", origin "typed", or "pasted" when the whole text is
  pasted; a mixed prompt stays typed, with the paste offsets in meta["paste_ranges"]. A slash command with words after it
  is typed, with the command in meta["command"]; a bare command ("/clear") is no turn. A block Northstar delivered
  (the northstar-context marker) is its own message, speaker "northstar", origin "northstar_injected", meta["part"]
  "n0", "n1" ...: never the user's words (I24). Hook-injected blocks and wrappers are removed; a background-task notice
  is kept as speaker "tool", origin "tool_output" (§8, self_started). Each message carries meta["uuid"] when the hook
  payload names the transcript line, so the backfill matches it by line, else by speaker and exact text.
- Stop: the assistant's final text for the turn. Speaker "assistant", agent "claude-code", model_family "anthropic",
  origin "assistant_output".
- SubagentStop: the subagent's final text on its own branch "sidechain:<agent_id>", same attribution (§10.3). The
  backfill uses the same branch name.
- PreCompact, PostCompact, SessionEnd: a system message each, origin "tool_output", saying what happened.

Ordinals follow the order captured: a turn the hooks missed and the transcript later supplies is appended at the end,
with its true time in occurred_at and meta["reconciled"] true; order by occurred_at for the order said.

Idempotent: each message carries the spool record's id in meta["spool_id"], and a record already stored is skipped, so
a drain that stopped between the database and the watermark, or a second one, adds nothing twice. A record that
conflicts with what is stored is logged and skipped, never overwritten (I6).

A delivery the hooks made twice is skipped too: a UserPromptSubmit or Stop whose (session, event, prompt_id) is already
stored (a Stop also with the same words, since a prompt can end in more than one Stop); without a prompt_id, the same
words from the same event in the same session within DUPLICATE_WITHIN_S.

Reconciliation (§12: transcripts are audit truth, hooks are the record). When a session has ended, or has been quiet for
GRACE_S, its transcript is read if readable: turns the hooks missed (a crash, a hook timeout) are added with fidelity
"reconciled", and so are the assistant's intermediate texts (what it said before tool calls within a turn), which the
hooks never carry, so a session's live and backfilled histories match. A turn that both have but with different words
is logged as a mismatch (hashes and sizes only) and neither is changed. Turns from before capture began for the session
(an install mid-session, a resume, a fork) are not reconciled; the one-off backfill, with the user's go-ahead, is the
way to bring those in. The scope gate runs again on each transcript line's own folder: a turn made after a `cd` out of
the personal folders is never added (§7), and the user's words are split by origin as in live capture.

Work events (§2.2): when a session ends, or settles, the commits made in its folder during it are recorded
(work_events.record_commits), for a folder the scope gate accepted.

Secrets are replaced in everything written: the spool text was scrubbed by the hook, is scrubbed again here (a second
pass changes nothing), and transcript text is scrubbed before it is stored. With no scrubber, nothing is written.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Callable, Mapping

from northstar_agent_memory import config as config_module
from northstar_agent_memory.capture import origin, scope, spool
from northstar_agent_memory.core.db import EncryptionRequired
from northstar_agent_memory.core.history import HistoryConflict, SQLiteHistoryStore
from northstar_agent_memory.core.ids import normalize_text
from northstar_agent_memory.eval.claude_code import (
    _COMPACT_SUMMARY,
    _GENERATED,
    _INTERRUPTED,
    APP,
    FAMILY,
    parse_session,
    parse_time,
)
from northstar_agent_memory.transcript import Message, Source

GRACE_S = 120.0  # a session quiet this long counts as settled, and its transcript is reconciled
CAPTURE_SLACK_S = 5.0  # a transcript turn this much before capture began for the session is not reconciled
PAIR_WITHIN_S = 120.0  # two turns with different words this close in time are one turn, and a mismatch
DUPLICATE_WITHIN_S = 5.0  # the same words from the same event this close, with no prompt id, are one delivery made twice
WORK_TRIES = 3  # attempts to read a session's commits when git fails, before it is let go
STATE_KEEP_S = 30 * 86400  # Claude Code's own transcript retention (note 22 A12)
MAX_ROUNDS = 10

_NOTICE = re.compile(r"<task-notification\b")

HANDLED = frozenset(
    {"SessionStart", "UserPromptSubmit", "Stop", "SubagentStop", "PreCompact", "PostCompact", "SessionEnd"}
)


@dataclass(slots=True)
class DrainResult:
    records: int = 0  # spool records read
    messages: int = 0  # messages written from records
    sources: int = 0  # sources created
    duplicates: int = 0  # records already stored (an earlier, interrupted drain)
    out_of_scope: int = 0  # records whose working folder is no longer in scope
    skipped: int = 0  # records that make no message by design (a bare command, an empty reply, SessionStart)
    corrupt: int = 0  # spool lines that were not valid records
    errors: int = 0  # records refused: unscrubbed, or in conflict with what is stored
    reconciled: int = 0  # messages added from transcripts
    work_events: int = 0  # commits recorded as work events
    mismatches: int = 0  # turns where hook and transcript differ

    def add(self, other: "DrainResult") -> None:
        for name in self.__slots__:
            setattr(self, name, getattr(self, name) + getattr(other, name))

    @property
    def notable(self) -> bool:
        return bool(self.corrupt or self.errors or self.mismatches or self.reconciled or self.out_of_scope)


# --- reading a prompt ------------------------------------------------------------------------------------------


@dataclass(slots=True)
class Turn:
    speaker: str
    origin: str
    text: str
    meta: dict[str, Any] = field(default_factory=dict)


_NORTHSTAR_BLOCK = re.compile(
    rf"<{origin.NORTHSTAR_TAG}\b[^>]{{0,200}}>.*?</{origin.NORTHSTAR_TAG}\b[^>]{{0,200}}>", re.S
)


def split_prompt(raw: object) -> list[Turn]:
    """What a UserPromptSubmit prompt holds, from Claude Code's own markers (§8): the user's own words (or, for a
    prompt that is not theirs, a tool notice), then each block Northstar delivered. Empty when it holds no turn.

    The split is origin.split_turn, the one the backfill makes of a transcript line, so the two agree."""
    if not isinstance(raw, str) or not raw.strip():
        return []
    parts = origin.split_turn(raw)
    turns: list[Turn] = []
    user = _user_turn(raw, parts)
    if user is not None:
        turns.append(user)
    for k, block in enumerate(parts.northstar):
        turns.append(Turn("northstar", "northstar_injected", block, {"part": f"n{k}"}))
    return turns


def _user_turn(raw: str, parts: origin.TurnParts) -> Turn | None:
    text = parts.user_text
    if not text:
        shown = _NORTHSTAR_BLOCK.sub("", raw).strip()  # Northstar's blocks are their own messages, never a notice's
        if shown and (_NOTICE.search(shown) or shown.startswith(_GENERATED)):  # not the user's words, but kept as what arrived
            return Turn("tool", "tool_output", shown, {"self_started": True})
        return None  # only hook-injected or wrapper blocks, an interrupt, a compaction summary, or Northstar's own text
    if text.startswith(_INTERRUPTED) or text.startswith(_COMPACT_SUMMARY):
        return None
    if text == parts.command and not parts.paste_ranges:
        return None  # a bare command, such as /clear: no words
    if text.startswith(_GENERATED) or "automated background-task event" in text[:300]:
        return Turn("tool", "tool_output", text, {"self_started": True})
    meta: dict[str, Any] = {}
    if parts.command:
        meta["command"] = parts.command
    if parts.paste_ranges:
        meta["paste_ranges"] = [list(r) for r in parts.paste_ranges]
    return Turn("user", parts.user_origin, text, meta)


def classify_prompt(raw: object) -> Turn | None:
    """The user's turn in a UserPromptSubmit prompt (or its tool notice). None when it is no turn."""
    return next((t for t in split_prompt(raw) if t.speaker != "northstar"), None)


# --- the state file --------------------------------------------------------------------------------------------


class State:
    """<data root>/capture/state.json: soft facts per session for reconciliation. Losing it loses only timing."""

    def __init__(self, root: Path | None) -> None:
        self.path = spool.state_path(root)
        self.sessions: dict[str, dict[str, Any]] = {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("sessions"), dict):
                self.sessions = {k: v for k, v in data["sessions"].items() if isinstance(v, dict)}
        except (OSError, ValueError):
            pass

    def save(self, now: float) -> None:
        self.sessions = {k: v for k, v in self.sessions.items() if now - v.get("last_at", now) < STATE_KEEP_S}
        spool.make_private_dirs(self.path.parent)
        tmp = self.path.with_name(f"state.json.{os.getpid()}.tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"v": 1, "sessions": self.sessions}, fh)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.path)


def _epoch(stamp: str | None) -> float | None:
    when = parse_time(stamp)
    return when.timestamp() if when else None


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat(timespec="seconds")


# --- the writer ------------------------------------------------------------------------------------------------


@dataclass(slots=True)
class _TurnRef:
    user: Message  # the user's own words: the transcript line with Northstar's blocks and injections cut out
    texts: list[Message]  # the assistant messages of the turn, in order
    start: float | None  # the user message's time, epoch seconds
    end: float | None  # the next turn's start
    north: list[str] = field(default_factory=list)  # the blocks Northstar delivered in the user's line
    dropped: bool = False  # made after a `cd` out of the personal folders: not captured


def _norm(text: str) -> str:
    return normalize_text(text)


def _digest(text: str) -> str:
    return hashlib.sha256(_norm(text).encode("utf-8", "replace")).hexdigest()[:12]


class _Writer:
    """One drain's writing to the store: sources, messages, and reconciliation."""

    def __init__(
        self, store: SQLiteHistoryStore, config: Mapping[str, Any], state: State, scrub: Callable[[str], str],
        root: Path | None, result: DrainResult,
    ) -> None:
        self.store, self.config, self.state, self.scrub = store, config, state, scrub
        self.root, self.result = root, result
        self._scope_cache: dict[str, str | None] = {}
        self._known: set[str] = set()
        self._ordinals: dict[tuple[str, str | None], int] = {}
        self._seen: dict[str, set[str]] = {}
        self._line_scope: dict[str, bool] = {}

    # --- helpers ---

    def _project_scope(self, cwd: str | None) -> str | None:
        key = cwd or ""
        if key not in self._scope_cache:
            self._scope_cache[key] = scope.project_scope(cwd, self.config, data_root=self.root)
        return self._scope_cache[key]

    def _next_ordinal(self, sid: str, branch: str | None) -> int:
        key = (sid, branch)
        if key not in self._ordinals:
            row = self.store.conn.execute(
                "SELECT COALESCE(MAX(ordinal), -1) + 1 FROM message WHERE source_id = ? AND branch = ?",
                (sid, "0" if branch is None else branch),
            ).fetchone()
            self._ordinals[key] = row[0]
        return self._ordinals[key]

    def _seen_ids(self, sid: str) -> set[str]:
        if sid not in self._seen:
            rows = self.store.conn.execute(
                "SELECT json_extract(meta, '$.spool_id') FROM message WHERE source_id = ?", (sid,)
            ).fetchall()
            self._seen[sid] = {r[0] for r in rows if r[0]}
        return self._seen[sid]

    def _append(self, m: Message, fidelity: str) -> bool:
        """Append with the next ordinal. The caller builds the message with ordinal 0 and an empty id."""
        branch = m.branch
        ordinal = self._next_ordinal(m.source_id, branch)
        m.ordinal = ordinal
        m.id = f"{m.source_id}:{ordinal}" if branch is None else f"{m.source_id}:{branch}:{ordinal}"
        try:
            new = self.store.append_message(m, fidelity=fidelity)
        except BaseException:
            self._ordinals.pop((m.source_id, branch), None)
            raise
        if new:
            self._ordinals[(m.source_id, branch)] = ordinal + 1
        return new

    def _message(
        self, rec: spool.SpoolRecord, speaker: str, origin: str, text: str, *, branch: str | None = None,
        model_family: str | None = None, **meta: Any,
    ) -> Message:
        return Message(
            id="", source_id=rec.session_id, ordinal=0, speaker=speaker, text=self.scrub(text),
            occurred_at=rec.occurred_at, origin=origin, agent=APP, model_family=model_family, branch=branch,
            meta={"spool_id": rec.id, "event": rec.event, **meta},
        )

    # --- one spool record ---

    def apply(self, rec: spool.SpoolRecord) -> None:
        self.result.records += 1
        if not rec.scrub:
            self.result.errors += 1
            spool.log("ingest", f"record {rec.id} was not scrubbed and was not ingested", root=self.root)
            return
        if rec.event not in HANDLED:
            self.result.skipped += 1
            return
        project = self._project_scope(rec.cwd)
        if project is None:  # the scope gate again: a folder removed from the personal folders since
            self.result.out_of_scope += 1
            return
        sid = rec.session_id
        self._ensure_source(rec, project)
        self._touch(rec)
        if rec.id in self._seen_ids(sid):
            self.result.duplicates += 1
            return
        messages = self._build(rec)
        if not messages:
            self.result.skipped += 1
            return
        if self._delivered_twice(rec, messages[0]):  # the hook ran twice for one event (a retry, a double registration)
            self.result.duplicates += 1
            return
        self.state.sessions[sid]["work_done"] = False  # something new happened: its commits are read again when it settles
        for message in messages:
            try:
                if self._append(message, "verbatim"):
                    self._seen_ids(sid).add(rec.id)
                    self.result.messages += 1
            except (HistoryConflict, ValueError, sqlite3.IntegrityError) as err:  # this record only: never block the rest
                self.result.errors += 1
                spool.log("ingest", f"record {rec.id}: {type(err).__name__}: {err}", root=self.root)

    def _ensure_source(self, rec: spool.SpoolRecord, project: str) -> None:
        sid = rec.session_id
        if sid in self._known:
            return
        info = self.store.get_source_info(sid)
        if info is None:
            payload = rec.payload
            fresh = rec.event == "SessionStart" and payload.get("source") in ("startup", "clear")
            meta: dict[str, Any] = {"first_event": rec.event, "capture_from": "" if fresh else rec.occurred_at}
            if rec.event == "SessionStart":
                meta["start_kind"] = payload.get("source")
                meta["model"] = payload.get("model")
            source = Source(id=sid, kind="chat", app=APP, project=rec.cwd, started_at=rec.occurred_at, meta=meta)
            if self.store.add_source(source, scope=project):
                self.result.sources += 1
        self._known.add(sid)

    def _touch(self, rec: spool.SpoolRecord) -> None:
        entry = self.state.sessions.setdefault(rec.session_id, {})
        entry["last_at"] = max(entry.get("last_at", 0.0), _epoch(rec.recorded_at) or 0.0)
        entry["ended"] = rec.event == "SessionEnd"
        entry["ended_at"] = rec.occurred_at if rec.event == "SessionEnd" else None
        entry["rec_sig"] = None
        entry["cwd"] = rec.cwd  # a folder the scope gate has just accepted
        if rec.transcript_path:
            entry["transcript_path"] = rec.transcript_path

    def _delivered_twice(self, rec: spool.SpoolRecord, message: Message) -> bool:
        """Whether this record is a second delivery of an event already stored (a UserPromptSubmit or Stop only)."""
        if rec.event not in ("UserPromptSubmit", "Stop"):
            return False
        conn, sid = self.store.conn, rec.session_id
        prompt_id = rec.payload.get("prompt_id")
        if isinstance(prompt_id, str) and prompt_id:
            rows = conn.execute(
                "SELECT text FROM message WHERE source_id = ? AND json_extract(meta, '$.event') = ?"
                " AND json_extract(meta, '$.prompt_id') = ?",
                (sid, rec.event, prompt_id),
            ).fetchall()
            if rec.event == "UserPromptSubmit":
                return bool(rows)  # one prompt, one record
            return any(r[0] == message.text for r in rows)  # a prompt can end in more than one Stop: only the same words repeat
        when = _epoch(message.occurred_at)
        if when is None:
            return False
        rows = conn.execute(
            "SELECT occurred_at FROM message WHERE source_id = ? AND json_extract(meta, '$.event') = ? AND speaker = ? AND text = ?",
            (sid, rec.event, message.speaker, message.text),
        ).fetchall()
        return any((then := _epoch(r[0])) is not None and abs(when - then) <= DUPLICATE_WITHIN_S for r in rows)

    def _build(self, rec: spool.SpoolRecord) -> list[Message]:
        p = rec.payload
        known: dict[str, Any] = {"uuid": p["uuid"]} if isinstance(p.get("uuid"), str) and p["uuid"] else {}
        if rec.event == "UserPromptSubmit":
            prompt = p.get("prompt")
            # Scrubbed before it is split, so the paste offsets and Northstar's blocks are those of the text kept.
            turns = split_prompt(self.scrub(prompt) if isinstance(prompt, str) else prompt)
            ids = {"prompt_id": p["prompt_id"]} if isinstance(p.get("prompt_id"), str) and p["prompt_id"] else {}
            # A block Northstar delivered is its own message (speaker "northstar"), never the user's words (I24).
            return [self._message(rec, t.speaker, t.origin, t.text, **t.meta, **ids, **known) for t in turns]
        if rec.event in ("Stop", "SubagentStop"):
            text = p.get("last_assistant_message")
            if not isinstance(text, str) or not text.strip():
                return []
            if rec.event == "Stop":
                ids = {"prompt_id": p["prompt_id"]} if isinstance(p.get("prompt_id"), str) and p["prompt_id"] else {}
                return [self._message(rec, "assistant", "assistant_output", text, model_family=FAMILY, **ids, **known)]
            agent_id = p.get("agent_id") if isinstance(p.get("agent_id"), str) and p.get("agent_id") else "agent"
            return [self._message(
                rec, "assistant", "assistant_output", text, branch=f"sidechain:{agent_id}", model_family=FAMILY,
                sidechain=True, agent_id=agent_id, agent_type=p.get("agent_type"), **known,
            )]
        if rec.event in ("PreCompact", "PostCompact"):
            trigger = p.get("trigger") if isinstance(p.get("trigger"), str) else "unknown"
            started = rec.event == "PreCompact"
            meta = {"marker": "compaction_started" if started else "compaction_finished", "trigger": trigger}
            for key in ("compact_summary_sha256", "compact_summary_chars", "has_custom_instructions"):
                if key in p:
                    meta[key] = p[key]
            text = f"[claude-code] context compaction {'started' if started else 'finished'} ({trigger})"
            return [self._message(rec, "system", "tool_output", text, **meta)]
        if rec.event == "SessionEnd":
            reason = p.get("reason") if isinstance(p.get("reason"), str) else "unknown"
            return [self._message(
                rec, "system", "tool_output", f"[claude-code] session ended ({reason})", marker="session_ended", reason=reason
            )]
        return []  # SessionStart: it makes the source, not a message

    # --- reconciliation (§12) ---

    def reconcile_settled(self, now: float, grace_s: float) -> None:
        for sid, entry in list(self.state.sessions.items()):
            settled = entry.get("ended") or now - entry.get("last_at", now) >= grace_s
            path = Path(entry["transcript_path"]) if entry.get("transcript_path") else None
            if not settled or path is None or path.suffix != ".jsonl":
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            sig = f"{stat.st_size}:{stat.st_mtime_ns}"
            if entry.get("rec_sig") == sig or not path.is_file():
                continue
            try:
                self.reconcile(sid, path)
                entry["rec_sig"] = sig
            except sqlite3.Error:
                raise
            except Exception as err:  # an unreadable or unexpected transcript: audit only, capture is unaffected
                spool.log("ingest", f"reconcile {sid}: {type(err).__name__}: {err}", root=self.root)

    def _cwd_allowed(self, cwd: str | None) -> bool:
        """The scope gate for one transcript line's own folder (§7): a turn typed after a `cd` out of the personal folders
        is not captured. A line with no folder is the session's, which the gate already accepted."""
        if not cwd:
            return True
        if cwd not in self._line_scope:
            self._line_scope[cwd] = scope.in_scope(cwd, self.config, data_root=self.root)
        return self._line_scope[cwd]

    def _transcript_turns(self, parsed: Any, raw: Any, cutoff: float | None) -> list[_TurnRef]:
        """The transcript's turns: each user line with the assistant texts that follow it, the scope gate applied to
        every line's own folder, and the user's words split by origin as live capture splits them."""
        turns: list[_TurnRef] = []
        for m in parsed.source.messages:
            if m.speaker not in ("user", "assistant"):
                continue
            uuid = m.meta.get("uuid")
            line = raw.lines.get(uuid) if isinstance(uuid, str) else None
            allowed = self._cwd_allowed(line.cwd if line else None)
            if m.speaker == "assistant":
                if turns and allowed and not turns[-1].dropped:
                    m.text = self.scrub(m.text)
                    turns[-1].texts.append(m)
                continue
            north: list[str] = []
            if allowed:
                if line is not None and line.user_text is not None:
                    parts = origin.split_turn(self.scrub(line.user_text))
                    meta = {k: v for k, v in m.meta.items() if k in ("uuid", "images")}
                    if parts.command:
                        meta["command"] = parts.command
                    if parts.paste_ranges:
                        meta["paste_ranges"] = [list(r) for r in parts.paste_ranges]
                    m.text, m.origin, m.meta, north = parts.user_text, parts.user_origin, meta, parts.northstar  # type: ignore[assignment]
                else:  # no raw line to split (should not happen): the parser's text, which already has wrappers removed
                    scrubbed = self.scrub(m.text)
                    if scrubbed != m.text:
                        m.meta.pop("paste_ranges", None)  # their offsets were for the text before secrets were replaced
                    m.text = scrubbed
            turns.append(_TurnRef(m, [], _epoch(m.occurred_at), None, north=north, dropped=not allowed))
        for a, b in zip(turns, turns[1:]):
            a.end = b.start
        turns = [t for t in turns if not t.dropped]  # after the boundaries: a dropped turn still ends the one before it
        if cutoff is not None:
            turns = [t for t in turns if t.start is None or t.start >= cutoff]
        return turns

    def reconcile(self, sid: str, transcript: Path) -> None:
        info = self.store.get_source_info(sid)
        if info is None:
            return
        from northstar_agent_memory.capture import backfill  # its raw reader: each line's own folder (loaded only here)

        capture_from = info["meta"].get("capture_from")
        began = _epoch(capture_from) if capture_from else None
        cutoff = None if began is None else began - CAPTURE_SLACK_S

        turns = self._transcript_turns(parse_session(transcript), backfill._read_raw(transcript), cutoff)

        # In the order said, not the order captured: a reconciled turn is appended after later ones (see the docstring).
        stored = [s.message for s in self.store.messages_for_source(sid)]
        main = [m for m in stored if m.branch is None]
        main.sort(key=lambda m: (_epoch(m.occurred_at) if _epoch(m.occurred_at) is not None else float("inf"), m.ordinal))
        hooked_users = [m for m in main if m.speaker == "user"]
        hooked_replies = [m for m in main if m.speaker == "assistant"]
        # What is stored already, by transcript line (and the part of it): live capture has none, the backfill and an
        # earlier reconciliation have.
        have = {(u, m.meta.get("part", "")) for m in stored for u in (m.meta.get("transcript_uuid"), m.meta.get("uuid")) if u}
        have_uuids = {u for u, part in have if not part}
        live_northstar = Counter(m.text for m in stored if m.speaker == "northstar")

        # Which transcript turns the hooks missed (no hooked user turn), and which differ from the hooked one.
        # Hooked turns the transcript lacks are left alone: a rewind, or a transcript that lags. A turn with no words of
        # the user's (an image, Northstar's block alone) has no hooked turn to pair with.
        worded = [i for i, t in enumerate(turns) if t.user.text.strip()]
        missed: list[int] = []
        matcher = SequenceMatcher(
            None, [_norm(turns[i].user.text) for i in worded], [_norm(m.text) for m in hooked_users], autojunk=False
        )
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "delete":
                missed.extend(worded[i] for i in range(i1, i2))
            elif tag == "replace":
                free = list(range(j1, j2))
                for i in range(i1, i2):
                    turn = turns[worded[i]]
                    near = next((j for j in free if self._close(turn.start, _epoch(hooked_users[j].occurred_at))), None)
                    if near is None:
                        missed.append(worded[i])
                        continue
                    free.remove(near)
                    self._mismatch(sid, "user", hooked_users[near].text, turn.user.text)
        missed_set = set(missed)

        additions: list[tuple[Message, str]] = []  # (transcript message, its part)
        for i, turn in enumerate(turns):
            uuid = turn.user.meta.get("uuid")
            # An image-only prompt has no words: the hook makes no turn for it, so reconciliation adds no blank one.
            if i in missed_set and uuid not in have_uuids:
                additions.append((turn.user, ""))
            for k, block in enumerate(turn.north):  # Northstar's own text, in its own messages and never the user's
                if (uuid, f"n{k}") in have:
                    continue
                if live_northstar[block] > 0:  # live capture stored it without the transcript line's uuid
                    live_northstar[block] -= 1
                    continue
                additions.append((Message(
                    id="", source_id=sid, ordinal=0, speaker="northstar", text=block, occurred_at=turn.user.occurred_at,
                    origin="northstar_injected", agent=APP, meta={"uuid": uuid},
                ), f"n{k}"))
            if not turn.texts or turn.start is None:
                continue
            final = turn.texts[-1]
            window = [
                m for m in hooked_replies
                if (t := _epoch(m.occurred_at)) is not None and turn.start - 2 <= t and (turn.end is None or t < turn.end)
            ]
            if not window:  # the Stop hook was lost: everything the assistant said in the turn is added
                additions.extend((m, "") for m in turn.texts if m.meta.get("uuid") not in have_uuids)
                continue
            known = [_norm(m.text) for m in turn.texts]
            for hooked in window:
                h = _norm(hooked.text)
                if not any(h in t or t in h for t in known):
                    self._mismatch(sid, "assistant", hooked.text, final.text)
            # What the assistant said before its tool calls: the hooks carry only the final text of a turn.
            said = {_norm(m.text) for m in window}
            additions.extend(
                (m, "") for m in turn.texts[:-1] if m.meta.get("uuid") not in have_uuids and _norm(m.text) not in said
            )

        if not additions:
            return
        with self.store.batch():
            for source_msg, part in additions:
                meta = {k: v for k, v in source_msg.meta.items() if k in ("command", "paste_ranges", "images")}
                uuid = source_msg.meta.get("uuid")
                meta.update(reconciled=True, transcript_uuid=uuid, uuid=uuid, event="transcript")
                if part:
                    meta["part"] = part
                new = Message(
                    id="", source_id=sid, ordinal=0, speaker=source_msg.speaker, text=source_msg.text,
                    occurred_at=source_msg.occurred_at, origin=source_msg.origin, agent=APP,
                    model_family=FAMILY if source_msg.speaker == "assistant" else None, meta=meta,
                )
                try:
                    if self._append(new, "reconciled"):
                        self.result.reconciled += 1
                except HistoryConflict as err:
                    self.result.errors += 1
                    spool.log("ingest", f"reconcile {sid}: {err}", root=self.root)

    # --- work events (§2.2) ---

    def record_work(self, now: float, grace_s: float) -> None:
        """Record the commits each ended or settled session made, once per stretch of activity. Git is read after the
        messages are committed, never inside their transaction; a failure of git is retried a few times, then let go."""
        from northstar_agent_memory.capture import work_events

        for sid, entry in list(self.state.sessions.items()):
            last_at = entry.get("last_at")
            if entry.get("work_done") or not entry.get("cwd") or last_at is None:
                continue
            if not (entry.get("ended") or now - last_at >= grace_s):
                continue
            info = self.store.get_source_info(sid)
            if info is None:
                continue
            until = entry.get("ended_at") if entry.get("ended") else _iso(last_at + grace_s)
            try:
                # The folder is the one the scope gate accepted for the session's last event; record_commits asks again.
                report = work_events.record_commits(
                    self.store, sid, entry["cwd"], session_started_at=info["started_at"], session_ended_at=until,
                    config=self.config, data_root=self.root,
                )
            except sqlite3.Error:
                raise
            except Exception as err:  # git is no reason to stop capture
                spool.log("ingest", f"work events {sid}: {type(err).__name__}: {err}", root=self.root)
                entry["work_tries"] = entry.get("work_tries", 0) + 1
                entry["work_done"] = entry["work_tries"] >= WORK_TRIES
                continue
            self.result.work_events += report.recorded
            if report.error is not None:
                spool.log("ingest", f"work events {sid}: {report.error}", root=self.root)
                entry["work_tries"] = entry.get("work_tries", 0) + 1
            entry["work_done"] = report.error is None or entry.get("work_tries", 0) >= WORK_TRIES
            if entry["work_done"]:
                entry["work_tries"] = 0

    @staticmethod
    def _close(a: float | None, b: float | None) -> bool:
        return a is not None and b is not None and abs(a - b) <= PAIR_WITHIN_S

    def _mismatch(self, sid: str, kind: str, hooked: str, transcript: str) -> None:
        self.result.mismatches += 1
        spool.log(
            "ingest",
            f"mismatch session={sid} kind={kind} hook={_digest(hooked)}/{len(hooked)} transcript={_digest(transcript)}/{len(transcript)}",
            level="warn", root=self.root,
        )


# --- draining --------------------------------------------------------------------------------------------------


def drain(
    root: Path | None = None,
    *,
    config: Mapping[str, Any] | None = None,
    reconcile: bool = True,
    grace_s: float = GRACE_S,
    now: float | None = None,
) -> DrainResult:
    """Ingest every spool record not yet ingested, then reconcile settled sessions. The caller holds the lock (`run`).

    A record the store refuses is logged and skipped. A failure of the store itself (locked, unencrypted volume)
    stops the drain with the spool untouched: the next drain starts from the same watermark.
    """
    result = DrainResult()
    now = time.time() if now is None else now
    config = config_module.load() if config is None else config
    loaded = spool.load_scrubber()
    if loaded is None:
        spool.log("ingest", "the secret scrubber could not be loaded: nothing was written", root=root)
        return result
    scrub = loaded[0]
    state = State(root)
    with SQLiteHistoryStore(root) as store:
        writer = _Writer(store, config, state, scrub, root, result)
        for path in spool.spool_files(root):
            records, end, corrupt = spool.read_file(path)
            result.corrupt += corrupt
            if records:
                with store.batch():
                    for rec in records:
                        writer.apply(rec)
            if records or corrupt or end != spool.watermark(path):
                spool.set_watermark(path, end)
                state.save(now)
        if reconcile:
            writer.reconcile_settled(now, grace_s)
        writer.record_work(now, grace_s)
        state.save(now)
    spool.prune(root, now=now)
    return result


def _complete_line_waiting(root: Path | None) -> bool:
    """Whether a complete line lies past a watermark: a hook wrote after the drain read, even if the drain read nothing."""
    for path in spool.spool_files(root):
        records, _, corrupt = spool.read_file(path)
        if records or corrupt:
            return True
    return False


def run(root: Path | None = None, **kwargs: Any) -> DrainResult | None:
    """`drain` under the ingester lock. None if another ingester holds it. Drains again if a hook wrote while the
    lock was being let go, so a record is never left waiting for the next event."""
    total: DrainResult | None = None
    for _ in range(MAX_ROUNDS):
        fd = spool.try_lock(spool.lock_path(root))
        if fd is None:
            break
        try:
            if total is None:
                total = DrainResult()
            round_result = drain(root, **kwargs)
            total.add(round_result)
        finally:
            spool.unlock(fd)
        if not spool.has_pending(root) or not _complete_line_waiting(root):
            break  # nothing is waiting, or only a torn last line is (it waits until finished, and is no reason to go on)
    return total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m northstar_agent_memory.capture.ingest")
    parser.add_argument("--drain", action="store_true", help="ingest the spool, reconcile settled sessions, and exit")
    parser.add_argument("--grace-s", type=float, default=GRACE_S, help="quiet seconds before a session's transcript is reconciled")
    parser.add_argument("--no-reconcile", action="store_true", help="skip the transcript reconciliation")
    args = parser.parse_args(argv)
    if not args.drain:
        parser.print_usage(sys.stderr)
        return 2
    if scope.hidden_run():
        return 0
    try:
        result = run(reconcile=not args.no_reconcile, grace_s=args.grace_s)
    except EncryptionRequired as err:
        spool.log("ingest", f"not ingesting: {err}")
        return 1
    except Exception as err:
        spool.log("ingest", f"{type(err).__name__}: {err}")
        return 1
    if result is not None and result.notable:
        spool.log("ingest", "drained " + " ".join(f"{k}={getattr(result, k)}" for k in result.__slots__), level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
