"""The invariants of MEMORY-ARCHITECTURE §7, as checks the write gate runs on every proposal and a read-only sweep runs
over whole stores (§3.1 integrity, §5.9 "code checks every proposal", §5.12 caps).

`INVARIANTS` lists every id of §7 with what enforces it: the gate, the sweep, a database trigger or constraint, a
lint, or the later build step that owns it (capture, extraction, rebuild, replay, delivery, structure).

Each check takes a `Context` (one proposal, read through `MemoryRead` and `HistoryRead`) and returns `Violation`s
that carry the invariant id and a plain reason. A check never writes and never calls a model. The gate decides
what a violation means: a failed intake or code check rejects the proposal, a run over its loss bound holds it.

Nothing a proposal says about itself is believed (principle 4, §5.12). Who said a quote, in which source, when, which
family said a claim, whether a value moved for a stated reason, and whose authority a mark carries are all read from
chat history, memory.db and the gate's own call, never from the proposal's fields.
"""

from __future__ import annotations

import json
import math
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Mapping, Sequence

from northstar_agent_memory.core import events
from northstar_agent_memory.core.db import DEFAULT_TENANT
from northstar_agent_memory.core.events import EventEnvelope
from northstar_agent_memory.core.ids import normalize_text
from northstar_agent_memory.core.ports import Proposal

# --- the table of §7 ----------------------------------------------------------------------------------------------

ENFORCERS = ("gate", "sweep", "trigger", "lint", "capture", "extraction", "rebuild", "replay", "delivery", "structure")

# I8 (every Book sentence cites its sources) is dropped with the Book, and I22 is merged into I5 (§7).
INVARIANTS: dict[str, tuple[str, ...]] = {
    "I1": ("gate", "sweep"),  # every item cites evidence that exists in chat history
    "I2": ("gate", "sweep"),  # every quote is an exact substring of its message; your_words are your typed words
    "I3": ("gate", "trigger", "sweep"),  # speaker, agent and origin come from capture
    "I4": ("gate", "trigger", "sweep"),  # "adopted" needs words you typed
    "I5": ("gate", "trigger", "sweep"),  # goals, style lines and corrections need words you typed
    "I6": ("trigger", "sweep"),  # append-only; the sweep checks that the triggers are installed
    "I7": ("gate", "extraction", "sweep"),  # no derived input
    "I9": ("rebuild",),  # nothing leaves the index or the structure without a recorded reason
    "I10": ("extraction", "lint"),  # a hedge in your words caps certainty
    "I11": ("extraction", "gate", "sweep"),  # Northstar's own delivered text never counts as evidence
    "I12": ("gate", "sweep"),  # a merge needs an exact key or two agreeing families
    "I13": ("gate",),  # each run's changes are capped, including the loss bound
    "I14": ("gate", "trigger", "sweep"),  # replaying a run applies nothing twice
    "I15": ("gate", "sweep"),  # proposals match a versioned schema
    "I16": ("gate", "sweep"),  # said before recorded, valid times consistent
    "I17": ("gate", "sweep", "delivery"),  # everything has a scope
    "I18": ("replay",),  # replaying the event log rebuilds memory identically
    "I19": ("lint",),  # rules, starting values and prompts are versioned files
    "I20": ("gate", "trigger", "sweep"),  # origin is set at capture and never changes
    "I21": ("gate", "sweep"),  # your corrections are constraints no automated change may break
    "I23": ("lint",),  # the core is product-blind
    "I24": ("capture", "gate", "sweep"),  # Northstar's own text is marked at capture
    "I25": ("delivery",),  # views, principles and working style are never pushed
    "I26": ("structure",),  # no automatic structural change is reversed within its dwell
    "I27": ("rebuild",),  # links Northstar found are not shown until you confirm them
}

# --- records ------------------------------------------------------------------------------------------------------


@dataclass(slots=True)
class Violation:
    """One broken invariant. `op_index` names the op to blame; `ref` names the stored row, in a sweep."""

    invariant: str
    reason: str
    op_index: int | None = None
    ref: str | None = None


@dataclass(slots=True)
class Msg:
    """A captured message as the checks need it."""

    id: str
    source_id: str
    speaker: str
    agent: str | None
    model_family: str | None
    origin: str
    text: str
    occurred_at: str | None
    fidelity: str = "verbatim"


@dataclass(slots=True)
class Evidence:
    """One piece of evidence, in this proposal or stored. Speaker, agent, family and origin are copied from the message."""

    id: str
    subject_kind: str
    subject_id: str
    message_id: str
    start_char: int
    end_char: int
    quote: str
    role: str
    lineage: str
    speaker: str | None
    agent: str | None
    model_family: str | None
    origin: str | None
    source_id: str | None = None
    context: str | None = None  # the message's source project, or 'personal' outside a project (stamped by the gate)

    @property
    def typed_by_you(self) -> bool:
        """Words you typed: your speaker and a typed origin. Pasted text and a model's report of your turn do not count."""
        return self.speaker == "user" and self.origin == "typed"


@dataclass(frozen=True, slots=True)
class Limits:
    """Caps per run, and the loss bound (§5.9, §5.12, §5.13). Starting values; `[maintenance]` in the config moves them."""

    loss_bound: float = 0.05  # a run may retire at most this share of active items
    loss_bound_min: int = 1  # ...but always at least this many, so a small store can still correct itself
    max_ops_per_proposal: int = 60  # extraction: 60 changes per window
    max_structure_changes_per_run: int = 2  # weekly: at most 2 splits or merges of topics
    max_label_changes_per_run: int = 3  # ...and 3 labels changing
    idea_move_share: float = 0.05  # ...and 5% of ideas moving

    @classmethod
    def from_config(cls, config: Mapping[str, Any] | None) -> "Limits":
        section = (config or {}).get("maintenance", {})
        values: dict[str, Any] = {}
        for f in cls.__dataclass_fields__:
            if f in section:
                value = section[f]
                if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
                    raise ValueError(f"[maintenance] {f} must be a number of zero or more, got {value!r}")
                values[f] = value
        return cls(**values)


@dataclass(slots=True)
class LossBound:
    """What a run has retired against what it may retire (I13)."""

    retired: set[str]  # items this proposal retires, not counting ones the run retired before
    before: set[str]  # items this run retired in earlier proposals
    active: int  # active items at the start of the run, as far as the store shows
    allowed: int

    @property
    def total(self) -> int:
        return len(self.retired | self.before)

    @property
    def exceeded(self) -> bool:
        return self.total > self.allowed


# --- reading memory.db and history.db -----------------------------------------------------------------------------


def _rows(cursor: sqlite3.Cursor) -> list[dict[str, Any]]:
    names = [d[0] for d in cursor.description or ()]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


class MemoryRead:
    """Read-only lookups on memory.db. Never writes."""

    # Objects an input may name, and the table whose `seq_from` is their version (items have a version of their own).
    VERSIONED = {
        "link": "link", "conflict": "conflict", "topic": "topic", "work": "work", "correction": "correction",
        "style_line": "style_line", "supersession": "supersession", "placement": "placement", "scope": "scope",
    }  # fmt: skip

    def __init__(self, conn: sqlite3.Connection, tenant_id: str = DEFAULT_TENANT) -> None:
        self.conn = conn
        self.tenant_id = tenant_id

    def _all(self, sql: str, args: Sequence[Any] = ()) -> list[dict[str, Any]]:
        return _rows(self.conn.execute(sql, tuple(args)))

    def _one(self, sql: str, args: Sequence[Any] = ()) -> dict[str, Any] | None:
        rows = self._all(sql, args)
        return rows[0] if rows else None

    def item(self, item_id: str) -> dict[str, Any] | None:
        return self._one("SELECT * FROM item WHERE id = ? AND tenant_id = ?", (item_id, self.tenant_id))

    def items(self, where: str = "1=1") -> list[dict[str, Any]]:
        return self._all(f"SELECT * FROM item WHERE tenant_id = ? AND {where} ORDER BY created_seq", (self.tenant_id,))

    def evidence(self, evidence_id: str) -> dict[str, Any] | None:
        return self._one("SELECT * FROM evidence WHERE id = ? AND tenant_id = ?", (evidence_id, self.tenant_id))

    def evidence_for(self, subject_id: str) -> list[dict[str, Any]]:
        return self._all("SELECT * FROM evidence WHERE subject_id = ? AND tenant_id = ? ORDER BY created_seq", (subject_id, self.tenant_id))

    def all_evidence(self) -> list[dict[str, Any]]:
        return self._all("SELECT * FROM evidence WHERE tenant_id = ? ORDER BY created_seq", (self.tenant_id,))

    def link(self, link_id: str) -> dict[str, Any] | None:
        return self._one("SELECT * FROM link WHERE id = ? AND tenant_id = ?", (link_id, self.tenant_id))

    def row(self, table: str, row_id: str) -> dict[str, Any] | None:
        return self._one(f"SELECT * FROM {table} WHERE id = ? AND tenant_id = ?", (row_id, self.tenant_id))

    def exists(self, kind: str, row_id: str) -> bool:
        table = {"item": "item", "style_line": "style_line", "correction": "correction"}[kind]
        return self.row(table, row_id) is not None

    def version_of(self, kind: str, object_id: str) -> int | None:
        """The current version of an input object: an item's version, else the seq of the event that made its state."""
        if kind == "item":
            row = self.item(object_id)
            return None if row is None else row["version"]
        row = self.row(self.VERSIONED[kind], object_id)
        return None if row is None else row["seq_from"]

    def active_corrections(self) -> list[dict[str, Any]]:
        rows = self._all("SELECT * FROM correction WHERE status = 'active' AND tenant_id = ? ORDER BY created_seq", (self.tenant_id,))
        for row in rows:
            row["params"] = json.loads(row["params"] or "{}")
        return rows

    def event_exists(self, event_id: str) -> bool:
        return self._one("SELECT 1 AS x FROM event WHERE id = ?", (event_id,)) is not None

    def run_events(self, run_id: str) -> list[dict[str, Any]]:
        """Events already appended by a run: type, actor and parsed payload."""
        rows = self._all("SELECT type, actor, payload FROM event WHERE run_id = ? ORDER BY seq", (run_id,))
        for row in rows:
            row["payload"] = json.loads(row["payload"])
        return rows

    def active_item_count(self) -> int:
        return self._one("SELECT COUNT(*) AS n FROM item WHERE status = 'active' AND tenant_id = ?", (self.tenant_id,))["n"]  # type: ignore[index]

    def placement_count(self) -> int:
        return self._one("SELECT COUNT(*) AS n FROM placement WHERE tenant_id = ?", (self.tenant_id,))["n"]  # type: ignore[index]

    def has_event_about(self, subject_id: str, event_type: str) -> bool:
        sql = "SELECT 1 AS x FROM event_subject s JOIN event e ON e.seq = s.seq WHERE s.subject_id = ? AND e.type = ? LIMIT 1"
        return self._one(sql, (subject_id, event_type)) is not None


class HistoryRead:
    """Read-only lookups on chat history: messages, and each source's kind and scope.

    Built from a history store (anything with `get_message`; the SQLite store's `conn` adds source kind and scope)
    or from a connection to history.db. Without a connection, source lookups return None and the checks that need a
    source's kind or scope are skipped.
    """

    def __init__(self, store_or_conn: Any, tenant_id: str = DEFAULT_TENANT) -> None:
        self.tenant_id = tenant_id
        if isinstance(store_or_conn, sqlite3.Connection):
            self.store, self.conn = None, store_or_conn
        else:
            self.store, self.conn = store_or_conn, getattr(store_or_conn, "conn", None)
        self._messages: dict[str, Msg | None] = {}
        self._sources: dict[str, dict[str, Any] | None] = {}

    def message(self, message_id: str) -> Msg | None:
        if message_id in self._messages:
            return self._messages[message_id]
        found: Msg | None = None
        if self.store is not None:
            stored = self.store.get_message(message_id)
            if stored is not None:
                m = stored.message
                found = Msg(m.id, m.source_id, m.speaker, m.agent, m.model_family, m.origin, m.text, m.occurred_at, stored.fidelity)
        elif self.conn is not None:
            rows = _rows(self.conn.execute("SELECT * FROM message WHERE id = ? AND tenant_id = ?", (message_id, self.tenant_id)))
            if rows:
                r = rows[0]
                found = Msg(r["id"], r["source_id"], r["speaker"], r["agent"], r["model_family"], r["origin"], r["text"], r["occurred_at"], r["fidelity"])
        self._messages[message_id] = found
        return found

    def source(self, source_id: str) -> dict[str, Any] | None:
        """{'kind', 'scope', 'project'} of a source, or None if unknown or not readable."""
        if source_id in self._sources:
            return self._sources[source_id]
        found = None
        if self.conn is not None:
            rows = _rows(self.conn.execute("SELECT kind, scope, project FROM source WHERE id = ? AND tenant_id = ?", (source_id, self.tenant_id)))
            found = rows[0] if rows else None
        self._sources[source_id] = found
        return found

    def context_of(self, source_id: str | None) -> str | None:
        """The context a source's evidence belongs to: its project, or 'personal' outside a project. None if the
        source is not readable."""
        source = self.source(source_id) if source_id else None
        if source is None:
            return None
        return events.evidence_context(source.get("project"))

    def work_event(self, work_event_id: str) -> dict[str, Any] | None:
        """A captured work event (kind, ref, evidence, snapshot_sha256, occurred_at, source_id), or None if unknown or
        not readable."""
        if self.conn is None:
            return None
        rows = _rows(self.conn.execute(
            "SELECT kind, ref, evidence, snapshot_sha256, occurred_at, source_id FROM work_event WHERE id = ? AND tenant_id = ?",
            (work_event_id, self.tenant_id),
        ))
        return rows[0] if rows else None

    def said_time(self, message_id: str) -> datetime | None:
        """When a captured message was said, as an aware time, or None if it carries none."""
        msg = self.message(message_id)
        return parse_time(msg.occurred_at) if msg else None

    def northstar_marked(self, msg: Msg) -> bool:
        """Northstar's own text: marked by speaker or origin at capture, or inside a Northstar output source (I24)."""
        source = self.source(msg.source_id)
        return msg.speaker == "northstar" or msg.origin == "northstar_injected" or bool(source and source["kind"] == "northstar_output")


# --- small helpers ------------------------------------------------------------------------------------------------

CREATES = {
    "item.created": ("item", "item_id"),
    "goal.created": ("item", "item_id"),
    "question.created": ("item", "item_id"),
    "style.recorded": ("style_line", "style_id"),
    "correction.applied": ("correction", "correction_id"),
    "topic.created": ("topic", "topic_id"),
    "work.registered": ("work", "work_id"),
    "link.applied": ("link", "link_id"),
    "link.proposed": ("link", "link_id"),
    "conflict.opened": ("conflict", "conflict_id"),
    "supersession.applied": ("supersession", "supersession_id"),
}
ITEM_CREATES = ("item.created", "goal.created", "question.created")
_INVARIANT_IN_TEXT = re.compile(r"\bI(\d{1,2})\b")
# What an input may name. Anything built from other text (overview, start notes, the change log, a model's output)
# is derived, and no stage reads it (I7). Unknown names are refused too: inputs are typed.
INPUT_KINDS = ("item", "message", *MemoryRead.VERSIONED)
DERIVED_INPUT_KINDS = (
    "overview", "view", "topic_view", "idea_view", "start_note", "goal_card", "change_log", "model_output", "model_call",
    "summary", "index",
)  # fmt: skip


def invariant_of(problem: str) -> str:
    """The invariant a validation problem names ('I3: ...'), else I15 (the proposal does not match its schema)."""
    found = _INVARIANT_IN_TEXT.search(problem)
    return f"I{found.group(1)}" if found and f"I{found.group(1)}" in INVARIANTS else "I15"


def parse_input(text: str) -> tuple[str, str, str]:
    """'item:m3@2' or 'm3@2' (an item) to ('item', 'm3', '2')."""
    obj, _, version = text.rpartition("@")
    kind, sep, rest = obj.partition(":")
    return (kind, rest, version) if sep else ("item", obj, version)


def evidence_refs(op: EventEnvelope) -> list[str]:
    """The evidence ids an op cites."""
    p = op.payload
    refs = list(p.get("evidence_ids") or [])
    if p.get("evidence_id"):
        refs.append(p["evidence_id"])
    return refs


_ITEM_FIELDS = ("item_id", "old_item", "new_item", "from_id", "to_id", "side_a_item", "side_b_item", "winner", "anchor_id", "question_id")
_ITEM_LISTS = ("answered_by", "item_ids")


def touched_items(op: EventEnvelope) -> list[str]:
    """The item ids an op names: its item, an old or new item, a link's ends (not a piece of work), a conflict's sides,
    the items a question is answered by or a purge removes, and the item evidence is anchored to."""
    p = op.payload if isinstance(op.payload, dict) else {}
    found: list[str] = []
    for name in _ITEM_FIELDS:
        value = p.get(name)
        if isinstance(value, str) and value and not (name == "to_id" and p.get("to_kind") == "work"):
            found.append(value)
    for name in _ITEM_LISTS:
        value = p.get(name)
        if isinstance(value, list):
            found += [v for v in value if isinstance(v, str)]
    if op.type == "evidence.anchored" and p.get("subject_kind") == "item" and isinstance(p.get("subject_id"), str):
        found.append(p["subject_id"])
    return list(dict.fromkeys(found))


def parse_time(value: Any) -> datetime | None:
    """An ISO 8601 time as an aware datetime (a time with no offset is read as UTC), or None."""
    if not isinstance(value, str) or not value:
        return None
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def quote_problem(text: str, start: int, end: int, quote: str) -> str | None:
    """Why a quote is not the text at its span (I2), or None. Both are normalized: spaces collapsed, Unicode NFC."""
    if not 0 <= start < end <= len(text):
        return f"the span {start}-{end} lies outside the message ({len(text)} characters)"
    if not normalize_text(quote):
        return "the quote is empty"
    if normalize_text(text[start:end]) != normalize_text(quote):
        return "the quote is not the text of the message at its span"
    return None


def origin_of(evidence: Sequence[Evidence]) -> str | None:
    """An item's origin, computed from its evidence and never set by a model (§2.5): 'adopted:<agent>' when an AI's
    span is the primary evidence, 'yours' when your own words are, None when neither speaker is there."""
    ai = [e for e in evidence if e.speaker == "assistant" and e.role == "primary"]
    if ai:
        return "adopted:" + (ai[0].agent or ai[0].model_family or "assistant")
    return "yours" if any(e.speaker == "user" for e in evidence) else None


def _norm_key(text: str | None) -> str:
    return normalize_text(text or "").casefold()


def exact_key(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    """Two items share an exact key: the same scope and kind, and the same line or the same words of yours. A
    different scope is a link and never a merge (§5.5)."""
    if a["scope"] != b["scope"] or a["kind"] != b["kind"]:
        return False
    if _norm_key(a["line"]) == _norm_key(b["line"]):
        return True
    words = _norm_key(a.get("your_words"))
    return bool(words) and words == _norm_key(b.get("your_words"))


def scope_covers(item_scope: str, source_scope: str) -> bool:
    """An item is no wider than where it was learned (§5.5 step 6): its scope is that of its source, or narrower than
    a personal source. A session source sets no bar."""
    return source_scope.startswith("session:") or item_scope == source_scope or source_scope == "personal"


# --- the context one proposal is checked in -----------------------------------------------------------------------


class Context:
    """One proposal, with what the checks read. `ops` are drafts (the gate passes copies and stamps them later).

    `work_families` are the families that did the work; `claim_families` the families of the AI whose words are cited
    or whose words an op's items already rest on; `verdict_families` those of the passing, independent verdicts that
    count (read from runs.db by the gate). Together they decide I12. `user_authority` is True only when the gate was
    handed a `UserAuthority`: it makes the ops yours and lifts the verdict tiers, never anything a proposal says.
    """

    def __init__(
        self,
        proposal: Proposal,
        ops: list[EventEnvelope],
        memory: MemoryRead,
        history: HistoryRead,
        recorded_at: str,
        *,
        limits: Limits | None = None,
        work_families: Iterable[str] = (),
        verdict_families: Iterable[str] = (),
        user_authority: bool = False,
    ) -> None:
        self.proposal, self.ops, self.memory, self.history, self.recorded_at = proposal, ops, memory, history, recorded_at
        self.limits = limits or Limits()
        self.work_families = frozenset(work_families)
        self.verdict_families = frozenset(verdict_families)
        self.user_authority = user_authority  # set by the gate from an authority it was handed, never from a proposal
        self._claims: frozenset[str] | None = None
        self.created: dict[str, tuple[str, int, EventEnvelope]] = {}  # id -> (kind, op index, op) made by this proposal
        self.new_evidence: dict[str, Evidence] = {}
        self._stored: dict[str, Evidence | None] = {}
        for index, op in enumerate(ops):
            spec = CREATES.get(op.type)
            payload = op.payload if isinstance(op.payload, dict) else {}
            if spec and isinstance(payload.get(spec[1]), str):
                self.created.setdefault(payload[spec[1]], (spec[0], index, op))
            if op.type == "evidence.anchored" and isinstance(payload.get("evidence_id"), str):
                self.new_evidence.setdefault(payload["evidence_id"], self._anchored(payload))

    # evidence

    def _anchored(self, p: Mapping[str, Any]) -> Evidence:
        """A proposal's evidence with who said it taken from the message (stamped), as the gate will store it."""
        message_id = p.get("message_id") if isinstance(p.get("message_id"), str) else ""
        msg = self.history.message(message_id)
        return Evidence(
            p["evidence_id"], p.get("subject_kind", ""), p.get("subject_id", ""), message_id,
            p.get("start_char", 0), p.get("end_char", 0), p.get("quote", ""), p.get("role", ""), p.get("lineage", "primary"),
            msg.speaker if msg else None, msg.agent if msg else None, msg.model_family if msg else None,
            msg.origin if msg else None, msg.source_id if msg else None,
            self.history.context_of(msg.source_id) if msg else None,
        )  # fmt: skip

    def evidence(self, evidence_id: str) -> Evidence | None:
        if evidence_id in self.new_evidence:
            return self.new_evidence[evidence_id]
        if evidence_id not in self._stored:
            row = self.memory.evidence(evidence_id)
            self._stored[evidence_id] = evidence_from_row(row, self.history) if row else None
        return self._stored[evidence_id]

    def evidences(self, ids: Iterable[str]) -> list[Evidence]:
        return [e for e in (self.evidence(i) for i in ids) if e is not None]

    # items and other subjects

    def item(self, item_id: str) -> dict[str, Any] | None:
        """The item as stored, or as this proposal creates it (version 1, active)."""
        stored = self.memory.item(item_id)
        if stored is not None:
            return stored
        made = self.created.get(item_id)
        if made is None or made[0] != "item":
            return None
        p = made[2].payload
        return {
            "id": item_id, "version": 1, "status": "active", "kind": "goal" if made[2].type == "goal.created" else (
                "question" if made[2].type == "question.created" else p.get("kind")),
            "line": p.get("line", ""), "your_words": p.get("your_words", ""), "scope": p.get("scope", ""),
            "said_at": p.get("said_at"), "learned_in": p.get("learned_in"), "goal_status": "active", "question_status": "open",
            "new_in_proposal": True,
        }  # fmt: skip

    def made_here(self, object_id: str) -> bool:
        return object_id in self.created

    def subject_exists(self, kind: str, subject_id: str) -> bool:
        if self.memory.exists(kind, subject_id):
            return True
        made = self.created.get(subject_id)
        return made is not None and made[0] == kind

    def claim_families(self) -> frozenset[str]:
        """Families of the AIs whose words this proposal rests on (the work's checker may not be one of them): the AI
        evidence it anchors or cites, and every stored AI evidence row of every item an op touches (an item, an old
        item, a link's ends, a conflict's sides), whatever proposal brought it in."""
        if self._claims is None:
            found: set[str] = set()

            def take(speaker: str | None, family: str | None) -> None:
                if speaker == "assistant" and family:
                    found.add(family)

            for ev in self.new_evidence.values():
                take(ev.speaker, ev.model_family)
            for op in self.ops:
                for ev in self.evidences(evidence_refs(op)):
                    take(ev.speaker, ev.model_family)
                for item_id in touched_items(op):
                    for row in self.memory.evidence_for(item_id):
                        take(row["speaker"], row["model_family"])
            self._claims = frozenset(found)
        return self._claims

    def agreeing_families(self) -> frozenset[str]:
        """The families that agree with a merge: the one that proposed it and those that checked it (I12)."""
        return self.work_families | self.verdict_families

    def op_origin(self, op: EventEnvelope) -> str | None:
        return origin_of(self.evidences(op.payload.get("evidence_ids") or []))


def evidence_from_row(row: Mapping[str, Any], history: HistoryRead | None) -> Evidence:
    msg = history.message(row["message_id"]) if history else None
    context = row.get("context") if hasattr(row, "get") else None
    if context is None and history is not None and msg is not None:
        context = history.context_of(msg.source_id)  # rows stored before the column existed
    return Evidence(
        row["id"], row["subject_kind"], row["subject_id"], row["message_id"], row["start_char"], row["end_char"], row["quote"],
        row["role"], row["lineage"], row["speaker"], row["agent"], row["model_family"], row["origin"], msg.source_id if msg else None,
        context,
    )  # fmt: skip


# --- intake: the proposal's shape (I3, I14, I15) ------------------------------------------------------------------


def check_schema(ctx: Context) -> list[Violation]:
    """Every op matches its versioned schema (I15), a draft carries no stamped field (I3), and a payload's own rules
    hold (the invariant a problem names, else I15)."""
    out: list[Violation] = []
    if not ctx.ops:
        out.append(Violation("I15", "a proposal has at least one op"))
    if not ctx.proposal.run_id or not ctx.proposal.proposal_id:
        out.append(Violation("I14", "a proposal names its run and its own id"))
    seen_compensates = {op.id for op in ctx.ops}
    for index, op in enumerate(ctx.ops):
        for problem in events.problems(op, draft=True):
            out.append(Violation(invariant_of(problem), problem, index))
        if op.compensates and op.compensates not in seen_compensates and not ctx.memory.event_exists(op.compensates):
            out.append(Violation("I15", f"compensates names no event: {op.compensates}", index))
    return out


def check_i3(ctx: Context) -> list[Violation]:
    """Speaker, agent, family and origin come from capture: a draft carries none of them."""
    return [v for v in check_schema(ctx) if v.invariant == "I3"]


def check_i15(ctx: Context) -> list[Violation]:
    """Proposals match a versioned schema."""
    return [v for v in check_schema(ctx) if v.invariant == "I15"]


def check_i14(ctx: Context) -> list[Violation]:
    """Replaying a run applies nothing twice: every op carries this run's key, indexes run 0..n-1, and nothing is
    created that already exists. A proposal applied before is found by the gate before it gets here."""
    out: list[Violation] = []
    ids: set[str] = set()
    for index, op in enumerate(ctx.ops):
        if op.run_id != ctx.proposal.run_id or op.proposal_id != ctx.proposal.proposal_id:
            out.append(Violation("I14", "an op carries another run or proposal than the one it is applied in", index))
        if op.index_in_proposal != index:
            out.append(Violation("I14", f"op {index} says it is index {op.index_in_proposal}", index))
        if op.id in ids or ctx.memory.event_exists(op.id):
            out.append(Violation("I14", f"event {op.id} exists already", index))
        ids.add(op.id)
        spec = CREATES.get(op.type)
        if spec and spec[0] == "item" and isinstance(op.payload.get(spec[1]), str) and ctx.memory.item(op.payload[spec[1]]):
            out.append(Violation("I14", f"item {op.payload[spec[1]]} exists already", index))
    return out


# --- I1, I2: evidence exists and quotes are exact -----------------------------------------------------------------


def check_i1(ctx: Context) -> list[Violation]:
    """Every item cites evidence that exists in chat history."""
    out: list[Violation] = []
    for quote in ctx.proposal.evidence:
        if ctx.history.message(quote.message_id) is None:
            out.append(Violation("I1", f"the proposal quotes message {quote.message_id}, which is not in chat history"))
    for index, op in enumerate(ctx.ops):
        p = op.payload
        if op.type == "evidence.anchored":
            if ctx.history.message(p["message_id"]) is None:
                out.append(Violation("I1", f"evidence cites message {p['message_id']}, which is not in chat history", index))
            if not ctx.subject_exists(p["subject_kind"], p["subject_id"]):
                out.append(Violation("I1", f"evidence is for a {p['subject_kind']} that does not exist: {p['subject_id']}", index))
        for eid in evidence_refs(op):
            if ctx.evidence(eid) is None:
                out.append(Violation("I1", f"{op.type} cites evidence {eid}, which does not exist", index))
        if op.type in ITEM_CREATES or op.type == "style.recorded":
            subject = p[CREATES[op.type][1]]
            for ev in ctx.evidences(p["evidence_ids"]):
                if ev.subject_id != subject:
                    out.append(Violation("I1", f"evidence {ev.id} supports {ev.subject_id}, not {subject}", index))
    return out


# Ops that carry words presented as yours: the shortest exact quote of yours in `your_words`, and a `why` that may quote
# you. (A style line has neither field today, so nothing is checked until one carries them.) A typed correction's label is
# your word for a thing too (§2.7).
YOUR_WORDS_OPS = ("item.created", "item.revised", "goal.created", "question.created", "style.recorded", "style.revised")
_QUOTE_LABEL_KEYS = ("label", "your_words", "quote")
_QUOTED = re.compile(r'"([^"]{2,})"|\u201c([^\u201d]{2,})\u201d|\u00ab([^\u00bb]{2,})\u00bb')


def quoted_spans(text: str | None) -> list[str]:
    """What a line of reasoning presents as a quote: the text inside its quotation marks."""
    return [next(g for g in m.groups() if g) for m in _QUOTED.finditer(text or "")]


def typed_text_problem(words: str, evidence: Iterable[Evidence], history: HistoryRead) -> str | None:
    """Why `words` are not words you typed in the cited evidence, or None. After normalizing spaces and Unicode, the
    words must be a substring of a cited span, or of the cited message, whose speaker is you and whose origin is typed:
    a report of your turn, pasted text and an AI's words do not count."""
    needle = normalize_text(words)
    if not needle:
        return None
    typed = [e for e in evidence if e.typed_by_you]
    if not typed:
        return "no cited evidence is words you typed"
    for ev in typed:
        msg = history.message(ev.message_id)
        if normalize_text(ev.quote).find(needle) >= 0 or (msg is not None and normalize_text(msg.text).find(needle) >= 0):
            return None
    return "they appear nowhere in the words you typed that it cites"


def your_words_problems(words: str | None, why: str | None, evidence: Sequence[Evidence], history: HistoryRead) -> list[str]:
    """Reasons your_words, and each quote inside `why`, are not your typed words in the evidence cited (I2)."""
    out: list[str] = []
    if words and normalize_text(words):
        problem = typed_text_problem(words, evidence, history)
        if problem:
            out.append(f"your_words {words!r}: {problem}")
    for quote in quoted_spans(why):
        problem = typed_text_problem(quote, evidence, history)
        if problem:
            out.append(f"the why quotes {quote!r}: {problem}")
    return out


def _evidence_for_words(ctx: "Context", op: EventEnvelope) -> list[Evidence]:
    """The evidence an op's words are judged against: what it cites, and for a revision what its item rests on."""
    p = op.payload
    found = {e.id: e for e in ctx.evidences(evidence_refs(op))}
    if op.type == "item.revised":
        for row in ctx.memory.evidence_for(p["item_id"]):
            ev = ctx.evidence(row["id"])
            if ev is not None:
                found.setdefault(ev.id, ev)
        for ev in ctx.new_evidence.values():
            if ev.subject_id == p["item_id"]:
                found.setdefault(ev.id, ev)
    return list(found.values())


def check_i2(ctx: Context) -> list[Violation]:
    """Every quote is an exact substring of its message, at the span it names, after normalizing spaces and Unicode.
    The words an item presents as yours (`your_words`, a quote in its `why`, a typed correction's label) are in the
    typed words of yours that it cites; an item whose words appear nowhere in them is refused."""
    out: list[Violation] = []
    for index, op in enumerate(ctx.ops):
        p = op.payload
        if op.type == "evidence.anchored":
            msg = ctx.history.message(p["message_id"])
            problem = quote_problem(msg.text, p["start_char"], p["end_char"], p["quote"]) if msg else None
            if problem:
                out.append(Violation("I2", f"evidence {p['evidence_id']}: {problem}", index))
        elif op.type in YOUR_WORDS_OPS:
            evs = _evidence_for_words(ctx, op)
            out += [Violation("I2", f"{op.type}: {text}", index) for text in your_words_problems(p.get("your_words"), p.get("why"), evs, ctx.history)]
        elif op.type == "correction.applied" and p.get("via") == "typed":
            evs = ctx.evidences([p["evidence_id"]] if p.get("evidence_id") else [])
            for key in _QUOTE_LABEL_KEYS:
                value = (p.get("params") or {}).get(key)
                problem = typed_text_problem(value, evs, ctx.history) if isinstance(value, str) else None
                if problem:
                    out.append(Violation("I2", f"correction.applied: its {key} {value!r}: {problem}", index))
    for quote in ctx.proposal.evidence:
        msg = ctx.history.message(quote.message_id)
        problem = quote_problem(msg.text, quote.start_char, quote.end_char, quote.quote) if msg else None
        if problem:
            out.append(Violation("I2", f"quote from {quote.message_id}: {problem}"))
    return out


# --- I3, I20: who said it comes from capture ----------------------------------------------------------------------


def check_i20(ctx: Context) -> list[Violation]:
    """Evidence is frozen once anchored: its speaker, agent, family and origin are the message's and never change. The
    gate stamps them from chat history, so the only way to break this is to anchor an id that exists already."""
    out: list[Violation] = []
    for index, op in enumerate(ctx.ops):
        if op.type == "evidence.anchored" and ctx.memory.evidence(op.payload["evidence_id"]) is not None:
            out.append(Violation("I20", f"evidence {op.payload['evidence_id']} is anchored already and never changes", index))
    return out


# --- I4, I5: your typed words -------------------------------------------------------------------------------------


def _typed(evidence: Iterable[Evidence]) -> bool:
    return any(e.typed_by_you for e in evidence)


def check_i4(ctx: Context) -> list[Violation]:
    """'Adopted' needs words you typed: an adoption span, and the stance 'adopted', rest on them."""
    out: list[Violation] = []
    for ev in ctx.new_evidence.values():
        if ev.role == "adoption" and not ev.typed_by_you:
            out.append(Violation("I4", f"evidence {ev.id} is an adoption, but its words are not words you typed ({ev.speaker}, {ev.origin})"))
    for index, op in enumerate(ctx.ops):
        p = op.payload
        if op.type in ("item.created", "question.created"):
            evs = ctx.evidences(p["evidence_ids"])
            origin = origin_of(evs)
            if evs and origin is None:
                out.append(Violation("I4", "the item rests on words that neither you nor an AI idea you adopted supplied", index))
            elif origin and origin.startswith("adopted:") and not any(e.role == "adoption" and e.typed_by_you for e in evs):
                out.append(Violation("I4", "the item is an AI idea, and no words you typed adopt it", index))
            if op.type == "question.created" and p["raised_by"] == "ai_taken_up" and not _typed(evs):
                out.append(Violation("I4", "a question an AI raised needs words you typed taking it up", index))
        if op.type == "stance.recorded" and p["stance"] == "adopted" and not _typed(ctx.evidences(p["evidence_ids"])):
            out.append(Violation("I4", "an adoption needs words you typed", index))
    return out


# Marks that are yours to make: no proposal, whoever it names as its actor, may carry them (a purge is only yours, §2.4; a
# correction is your one-step mark, §2.7). They reach memory only through `WriteGate.apply_user`, on an authority that
# your own capture, overview or command line hands the gate, and they are recorded under the actor `user`.
YOUR_MARKS = (
    "correction.applied", "correction.lifted", "purge.applied", "link.confirmed", "link.rejected", "goal.confirmed",
    "scope.hold_changed",
)  # fmt: skip
# What your authority may carry: your marks, and the changes they and your own edits make (a retraction, a restored
# status, your keep, a move in the overview, your own rollback). Items, links, supersessions and conflicts that a model
# judges are never carried by it: they go through `apply` and its checks.
USER_AUTHORITY_OPS = (
    *YOUR_MARKS, "evidence.anchored", "stance.recorded", "item.status_changed", "item.value_changed", "item.revised",
    "item.scope_widened", "goal.status_changed", "question.status_changed", "link.retracted", "supersession.undone",
    "conflict.undone", "compensation.batch", "topic.created", "topic.split", "topic.branched", "topic.merged",
    "topic.folded_back", "topic.renamed", "topic.dormant", "idea.placed", "idea.moved",
)  # fmt: skip


def check_authority(ctx: Context) -> list[Violation]:
    """Whose ops these are comes from the authority the gate was handed, never from a proposal's actor field. Through
    `apply`, an op under the actor `user`, or any of your marks, is refused whatever actor it names. Through
    `apply_user`, every op is yours (the gate records a `code:` module acting on your click as `user`), a model's is
    refused, and so is a type your authority does not carry."""
    out: list[Violation] = []
    for index, op in enumerate(ctx.ops):
        actor = op.actor if isinstance(op.actor, str) else ""
        if not ctx.user_authority:
            if actor == "user":
                out.append(Violation("I5", "the actor 'user' is yours; an op under it goes through apply_user with your authority, not through apply", index))
            elif op.type in YOUR_MARKS:
                out.append(Violation("I5", f"{op.type} is your mark; only your own click or typed words make it, and a proposal cannot", index))
        elif actor != "user":  # (the gate has already recorded a `code:` module acting on your click as `user`)
            out.append(Violation("I5", "an op under your authority is yours: a model's op is not, and goes through apply", index))
        elif op.type not in USER_AUTHORITY_OPS:
            out.append(Violation("I5", f"{op.type} is judged by the checks and goes through apply; your authority carries your own marks", index))
        if op.type in ("link.proposed", "link.applied") and not ctx.user_authority:
            # who stated a link is a claim that sets its risk tier and who may undo it: it is found, not read
            stated = op.payload.get("stated_by")
            if stated == "you":
                out.append(Violation("I5", "stated_by 'you' is yours: a proposal cannot say you stated a link", index))
            elif stated == "construction" and not actor.startswith("code:"):
                out.append(Violation("I5", "a link made by construction is code's; a model's link says stated_by 'northstar'", index))
    return out


def check_work(ctx: Context) -> list[Violation]:
    """A work row says what it is from capture: its kind, reference and strength are those of the work event it names
    (I3). A proposal's word for how strong the evidence is would otherwise let a made-up commit count as 'used in work'
    and move a value to kept (§2.4)."""
    out: list[Violation] = []
    for index, op in enumerate(ctx.ops):
        if op.type != "work.registered":
            continue
        p = op.payload
        captured = ctx.history.work_event(p["work_event_id"])
        if captured is None:
            out.append(Violation("I3", f"work event {p['work_event_id']} is not in chat history, so nothing shows this work exists", index))
            continue
        for name in ("kind", "ref", "evidence"):
            if p[name] != captured[name]:
                out.append(Violation("I3", f"the work's {name} is {p[name]!r}; the captured work event says {captured[name]!r}", index))
        for name in ("snapshot_sha256", "occurred_at"):
            if p.get(name) is not None and p[name] != captured[name]:
                out.append(Violation("I3", f"the work's {name} is not the captured work event's", index))
    return out


def _purge_marked(ctx: Context, item_id: str) -> bool:
    """You asked for this purge in your own typed words or by a click: a purge correction on the item, stored or made
    in this proposal. (A typed one is held to I5's typed-words rule where it is made.)"""
    for row in ctx.memory.active_corrections():
        if row["kind"] == "purge" and row["target"] == item_id and (row["via"] == "click" or row["evidence_id"]):
            return True
    return any(
        op.type == "correction.applied" and op.payload["kind"] == "purge" and op.payload["target"] == item_id
        and (op.payload["via"] == "click" or op.payload.get("evidence_id"))
        for op in ctx.ops
    )


def check_i5(ctx: Context) -> list[Violation]:
    """Goals, working-style lines and corrections need words you typed; a chat model's report stays 'reported'. A purge
    needs your typed words or a recorded click correction. (That your marks are never a proposal's to make is
    `check_authority`'s: it runs at intake.)"""
    out: list[Violation] = []

    def need_typed(index: int, evs: list[Evidence], what: str) -> None:
        if not _typed(evs):
            out.append(Violation("I5", f"{what} needs words you typed; a report, an AI's words or pasted text do not count", index))

    for index, op in enumerate(ctx.ops):
        p = op.payload
        if op.type == "purge.applied":
            for item_id in p["item_ids"]:
                if not _purge_marked(ctx, item_id):
                    out.append(Violation("I5", f"a purge of {item_id} needs your typed words or a recorded click correction asking for it", index))
        if op.type == "goal.created":
            evs = ctx.evidences(p["evidence_ids"])
            if p["basis"] == "stated":
                need_typed(index, evs, "a stated goal")
            elif not any(e.speaker == "user" for e in evs):
                out.append(Violation("I5", f"a {p['basis']} goal rests on your words, and none are cited", index))
            if evs and any(e.speaker == "assistant" and e.role == "primary" for e in evs):
                out.append(Violation("I5", "only a goal you stated sets a goal; an AI's suggestion does not", index))
        elif op.type == "goal.confirmed":
            need_typed(index, ctx.evidences(p["evidence_ids"]), "confirming a goal")
        elif op.type == "goal.status_changed" and p["to_status"] in ("done", "dropped"):
            need_typed(index, ctx.evidences(p["evidence_ids"]), f"a goal that is {p['to_status']}")
        elif op.type == "question.created" and p["raised_by"] == "you" and not any(e.speaker == "user" for e in ctx.evidences(p["evidence_ids"])):
            out.append(Violation("I5", "a question you pursue rests on your words, and none are cited", index))
        elif op.type == "style.recorded":
            evs = ctx.evidences(p["evidence_ids"])
            if p["basis"] == "stated_default":
                need_typed(index, evs, "a working-style default")
            else:
                sessions = {e.source_id for e in evs if e.speaker == "user" and e.source_id}
                if len(sessions) < 2:
                    out.append(Violation("I5", "a working-style line seen in sessions needs your words from two or more sessions", index))
        elif op.type == "style.revised" and not any(e.speaker == "user" for e in ctx.evidences(p["evidence_ids"])):
            out.append(Violation("I5", "revising a working-style line needs your words", index))
        elif op.type == "correction.applied" and p["via"] == "typed":
            need_typed(index, ctx.evidences([p["evidence_id"]] if p.get("evidence_id") else []), "a typed correction")
        elif op.type in ("link.confirmed", "link.rejected") and p["via"] == "typed":
            need_typed(index, ctx.evidences([p["evidence_id"]] if p.get("evidence_id") else []), "a typed confirmation or rejection")
    return out


# --- I3, I16: where and when it was said come from the cited messages ---------------------------------------------------


def learned_in_problem(learned_in: str, evidence: Iterable[Evidence], history: HistoryRead) -> str | None:
    """Why `learned_in` is not where the cited evidence was said, or None: it is the source of a cited message, or that
    source's project, scope or context. A proposal's own word for where it learned something is never taken."""
    allowed: set[str] = set()
    for ev in evidence:
        if ev.source_id:
            allowed.add(ev.source_id)
            source = history.source(ev.source_id)
            if source:
                allowed.update(v for v in (source.get("project"), source.get("scope")) if v)
        if ev.context:
            allowed.add(ev.context)
    if allowed and learned_in not in allowed:
        return f"learned_in {learned_in!r} is not the source or context of the evidence it cites ({', '.join(sorted(allowed))})"
    return None


def said_at_problem(said_at: str | None, origin: str | None, evidence: Iterable[Evidence], history: HistoryRead) -> str | None:
    """Why `said_at` is not when you said it, or None: it equals the time of a cited message of yours or, for an item
    adopted from an AI, of your adoption message. A message with no time sets no bar."""
    adopted = bool(origin and origin.startswith("adopted:"))
    times = []
    for ev in evidence:
        if ev.speaker == "user" and (ev.role == "adoption" or not adopted):
            moment = history.said_time(ev.message_id)
            if moment is not None:
                times.append(moment)
    moment = parse_time(said_at)
    if times and moment is not None and moment not in times:
        return f"said_at {said_at} is not when the message of yours that it cites was said ({', '.join(sorted(t.isoformat() for t in set(times)))})"
    return None


def check_learned_in(ctx: Context) -> list[Violation]:
    """`learned_in` is the source (or its context) of the evidence an item cites."""
    out: list[Violation] = []
    for index, op in enumerate(ctx.ops):
        if op.type in ITEM_CREATES:
            problem = learned_in_problem(op.payload["learned_in"], ctx.evidences(op.payload["evidence_ids"]), ctx.history)
            if problem:
                out.append(Violation("I3", problem, index))
    return out


# --- value: forming to kept on one of five signals, verified by code ----------------------------------------------------


def _item_evidence(ctx: Context, item_id: str) -> dict[str, Evidence]:
    """Every piece of evidence an item rests on: stored, and anchored to it in this proposal."""
    found: dict[str, Evidence] = {}
    for row in ctx.memory.evidence_for(item_id):
        ev = ctx.evidence(row["id"])
        if ev is not None:
            found[ev.id] = ev
    for ev in ctx.new_evidence.values():
        if ev.subject_kind == "item" and ev.subject_id == item_id:
            found[ev.id] = ev
    return found


def _your_statements(ctx: Context, evidence: Iterable[Evidence]) -> list[tuple[Evidence, datetime]]:
    """Your typed, primary-lineage evidence with the time of its message."""
    out = []
    for ev in evidence:
        moment = ctx.history.said_time(ev.message_id)
        if ev.typed_by_you and ev.lineage == "primary" and moment is not None:
            out.append((ev, moment))
    return out


def _work_evidence(ctx: Context, work_id: str) -> str | None:
    row = ctx.memory.row("work", work_id)
    if row is not None:
        return row["evidence"]
    made = ctx.created.get(work_id)
    return made[2].payload.get("evidence") if made and made[0] == "work" else None


def value_signal_problem(ctx: Context, op: EventEnvelope) -> str | None:
    """Why an item.value_changed does not show the signal it states, or None (§2.4)."""
    p = op.payload
    item_id, signal = p["item_id"], p["signal"]
    item = ctx.item(item_id)
    if item is None:
        return f"item {item_id} does not exist"
    own = _item_evidence(ctx, item_id)
    for ev in ctx.evidences(p["evidence_ids"]):
        if ev.id not in own:
            return f"it cites evidence {ev.id}, which is not evidence of {item_id}"
    statements = _your_statements(ctx, own.values())
    if signal == "later_day":
        days = {moment.astimezone(timezone.utc).date() for _, moment in statements}
        return None if len(days) >= 2 else f"later_day needs your words on two different days; {item_id} has {len(days)}"
    if signal == "second_context":
        contexts = {ev.context for ev, _ in statements if ev.context}
        return None if len(contexts) >= 2 else f"second_context needs your words in two contexts; {item_id} has {len(contexts)}"
    if signal == "your_keep":
        kept = any(c["kind"] == "keep" and c["target"] == item_id for c in ctx.memory.active_corrections())
        kept = kept or any(o.type == "correction.applied" and o.payload["kind"] == "keep" and o.payload["target"] == item_id for o in ctx.ops)
        return None if kept else f"your_keep needs a keep correction of yours on {item_id}"
    if signal == "built_on":
        said = parse_time(item.get("said_at"))
        stances = [json.loads(r["evidence_ids"]) for r in ctx.memory._all(
            "SELECT evidence_ids FROM stance WHERE item_id = ? AND stance = 'built_on' AND tenant_id = ?", (item_id, ctx.memory.tenant_id))]  # fmt: skip
        stances += [o.payload["evidence_ids"] for o in ctx.ops if o.type == "stance.recorded" and o.payload["item_id"] == item_id and o.payload["stance"] == "built_on"]
        for ids in stances:
            for _, moment in _your_statements(ctx, ctx.evidences(ids)):
                if said is not None and moment > said:
                    return None
        return f"built_on needs a later stance of yours that builds on {item_id}"
    if signal == "used_in_work":
        links = [(r["to_id"], r["status"]) for r in ctx.memory._all(
            "SELECT to_id, status FROM link WHERE from_id = ? AND type = 'used_in' AND to_kind = 'work' AND tenant_id = ?", (item_id, ctx.memory.tenant_id))]  # fmt: skip
        links = [(w, st) for w, st in links if st in ("applied", "confirmed")]
        links += [(o.payload["to_id"], "applied") for o in ctx.ops if o.type == "link.applied" and o.payload["link_type"] == "used_in" and o.payload["from_id"] == item_id]
        if any(_work_evidence(ctx, work) in ("medium", "strong") for work, _ in links):
            return None
        return f"used_in_work needs a used_in link from {item_id} to work with medium or strong evidence"
    return f"{signal} is not a signal of §2.4"


def check_value(ctx: Context) -> list[Violation]:
    """Value moves from forming to kept only when code finds the stated signal in the evidence. It never moves back by
    itself: the schema has no event for that."""
    out: list[Violation] = []
    for index, op in enumerate(ctx.ops):
        if op.type == "item.value_changed":
            problem = value_signal_problem(ctx, op)
            if problem:
                out.append(Violation("I1", f"the value of {op.payload['item_id']} does not move: {problem}", index))
    return out


# --- I7: no derived input -----------------------------------------------------------------------------------------


def input_problem(text: str) -> str | None:
    kind, _, _ = parse_input(text)
    if kind in DERIVED_INPUT_KINDS:
        return f"{text} is derived (a {kind}): overview text, start notes, the change log and earlier model outputs are never inputs"
    if kind not in INPUT_KINDS:
        return f"{text} is not a typed input; inputs name an item, link, conflict, topic, work, correction, style line, supersession, placement, scope or message"
    return None


def check_i7(ctx: Context) -> list[Violation]:
    out: list[Violation] = []
    reported: set[str] = set()
    for text in ctx.proposal.inputs:
        problem = input_problem(text)
        if problem and text not in reported:
            reported.add(text)
            out.append(Violation("I7", problem))
    for index, op in enumerate(ctx.ops):
        for text in op.inputs:
            problem = input_problem(text)
            if problem and text not in reported:
                reported.add(text)
                out.append(Violation("I7", problem, index))
    return out


# --- I12: a merge ------------------------------------------------------------------------------------------------


def merge_problem(a: Mapping[str, Any] | None, b: Mapping[str, Any] | None, families: Iterable[str], checked_by: Iterable[str] = ()) -> str | None:
    """Why a same_as merge of two items is refused (I12), or None."""
    if a is None or b is None:
        return "a merge names an item that does not exist"
    if a["scope"] != b["scope"]:
        return "the items have different scopes; a different scope means a link, never a merge"
    agreeing = set(families)
    if not exact_key(a, b) and len(agreeing) < 2:
        return "a merge needs an exact key (the same line or the same words of yours) or two agreeing model families"
    unbacked = set(checked_by) - agreeing
    if unbacked and not exact_key(a, b):
        return f"the link says it was checked by {sorted(unbacked)}, and no verdict backs that"
    return None


def check_i12(ctx: Context) -> list[Violation]:
    out: list[Violation] = []
    for index, op in enumerate(ctx.ops):
        if op.type == "link.applied" and op.payload["link_type"] == "same_as":
            p = op.payload
            problem = merge_problem(ctx.item(p["from_id"]), ctx.item(p["to_id"]), ctx.agreeing_families(), p.get("checked_by") or ())
            if problem:
                out.append(Violation("I12", problem, index))
    return out


# --- I13: caps per run and the loss bound -------------------------------------------------------------------------

RETIRING_STATUSES = ("superseded", "retracted", "quarantined")


def retired_by(op_type: str, payload: Mapping[str, Any]) -> str | None:
    """The item an event retires (superseded, merged, retracted or quarantined), or None. A refresh, or a new version
    of the same item, retires nothing."""
    if op_type == "supersession.applied" and payload.get("old_item") != payload.get("new_item"):
        return payload.get("old_item")
    if op_type == "link.applied" and payload.get("link_type") == "same_as":
        return payload.get("from_id")
    if op_type == "item.status_changed" and payload.get("from_status") == "active" and payload.get("to_status") in RETIRING_STATUSES:
        return payload.get("item_id")
    return None


def _automated(actor: str) -> bool:
    return actor != "user"  # your own marks do not count against a run's caps


def batch_losses(memory: MemoryRead, payload: Mapping[str, Any], *, applied: bool = False) -> set[str]:
    """The items a compensation.batch removes or retires (§5.9 rollback): the items its undone events created, and the
    items an undone event had brought back (a restored status, an undone supersession, a retracted merge). Only items
    still in force count, unless the batch is `applied` already (then nothing is in force that it took away). Undoing
    a whole run (`run_id_undone`) undoes the items that run created."""
    rows: list[dict[str, Any]] = []
    for event_id in payload.get("compensated_event_ids") or []:
        row = memory._one("SELECT type, payload FROM event WHERE id = ?", (event_id,))
        if row:
            rows.append(row)
    if payload.get("run_id_undone"):
        rows += memory._all("SELECT type, payload FROM event WHERE run_id = ? ORDER BY seq", (payload["run_id_undone"],))
    lost: set[str] = set()
    for row in rows:
        p = json.loads(row["payload"]) if isinstance(row["payload"], str) else row["payload"]
        if row["type"] in ITEM_CREATES:
            lost.add(p["item_id"])
        elif row["type"] == "item.status_changed" and p["to_status"] == "active" and p["from_status"] in RETIRING_STATUSES:
            lost.add(p["item_id"])
        elif row["type"] == "supersession.undone":
            old = memory.row("supersession", p["supersession_id"])
            if old and old["old_item"] != old["new_item"]:
                lost.add(old["old_item"])
        elif row["type"] in ("link.retracted", "link.rejected"):
            link = memory.link(p["link_id"])
            if link and link["type"] == "same_as":
                lost.add(link["from_id"])
    if applied:
        return lost
    return {i for i in lost if (item := memory.item(i)) is not None and item["status"] == "active"}


def loss_bound(ctx: Context) -> LossBound:
    """Items this run has retired or removed, against 5% (start) of the active items it started with (§5.9). A
    compensation.batch counts the items it removes or retires, as an op does."""
    before: set[str] = set()
    for row in ctx.memory.run_events(ctx.proposal.run_id):
        if not _automated(row["actor"]):
            continue
        item = retired_by(row["type"], row["payload"])
        if item:
            before.add(item)
        if row["type"] == "compensation.batch":
            before |= batch_losses(ctx.memory, row["payload"], applied=True)
    now: set[str] = set()
    for op in ctx.ops:
        if not _automated(op.actor):
            continue
        item = retired_by(op.type, op.payload)
        if item:
            now.add(item)
        if op.type == "compensation.batch":
            now |= batch_losses(ctx.memory, op.payload)
    active = ctx.memory.active_item_count() + len(before)
    allowed = max(ctx.limits.loss_bound_min, math.floor(ctx.limits.loss_bound * active))
    return LossBound(now - before, before, active, allowed)


def check_i13(ctx: Context) -> list[Violation]:
    """Caps per run: ops in a proposal, topic splits and merges, label changes and idea moves. (The loss bound holds
    a run instead of refusing it; see `loss_bound`.) Your own marks are exempt."""
    out: list[Violation] = []
    lim = ctx.limits
    if len(ctx.ops) > lim.max_ops_per_proposal:
        out.append(Violation("I13", f"a proposal may hold {lim.max_ops_per_proposal} ops, this one holds {len(ctx.ops)}"))
    prior = [r for r in ctx.memory.run_events(ctx.proposal.run_id) if _automated(r["actor"])]
    mine = [op for op in ctx.ops if _automated(op.actor)]

    def count(types: tuple[str, ...]) -> int:
        return sum(1 for r in prior if r["type"] in types) + sum(1 for op in mine if op.type in types)

    structure = count(("topic.split", "topic.merged"))
    if structure > lim.max_structure_changes_per_run:
        out.append(Violation("I13", f"a run may split or merge {lim.max_structure_changes_per_run} topics, this one would {structure}"))
    labels = count(("topic.renamed",))
    if labels > lim.max_label_changes_per_run:
        out.append(Violation("I13", f"a run may change {lim.max_label_changes_per_run} topic labels, this one would {labels}"))
    moves = count(("idea.moved",))
    allowed_moves = max(1, math.floor(lim.idea_move_share * ctx.memory.placement_count()))
    if moves > allowed_moves:
        out.append(Violation("I13", f"a run may move {allowed_moves} ideas, this one would move {moves}"))
    return out


# --- I16: time order ----------------------------------------------------------------------------------------------

_TIME_FIELDS = ("said_at", "at", "requested_at", "occurred_at")


def later_statement_problem(ctx: Context, p: Mapping[str, Any]) -> str | None:
    """Why a 'your_later_statement' supersession is not later by message time, or None. The time of each statement is
    that of your typed words in the evidence (the new item's, and what the supersession cites), never a field the
    proposal sets; an old item with no words of yours on file falls back on its said_at, which the gate checked against
    the message when it was made."""
    evs = {**_item_evidence(ctx, p["new_item"]), **{e.id: e for e in ctx.evidences(p["evidence_ids"])}}
    newest = [moment for _, moment in _your_statements(ctx, evs.values())]
    oldest = [moment for _, moment in _your_statements(ctx, _item_evidence(ctx, p["old_item"]).values())]
    if not oldest:
        then = parse_time((ctx.item(p["old_item"]) or {}).get("said_at"))
        oldest = [then] if then else []
    if not newest:
        return "a later statement needs your typed words, and none are cited for the item that replaces it"
    if not oldest or max(newest) <= max(oldest):
        return "a later statement of yours was not said after the one it replaces, by the time of the messages"
    return None


def check_i16(ctx: Context) -> list[Violation]:
    """Said before recorded, and valid times consistent."""
    out: list[Violation] = []
    recorded = parse_time(ctx.recorded_at)
    for index, op in enumerate(ctx.ops):
        p = op.payload
        for name in _TIME_FIELDS:
            if p.get(name) is None:
                continue
            moment = parse_time(p[name])
            if moment is None:
                out.append(Violation("I16", f"{name} is not an ISO 8601 time: {p[name]!r}", index))
            elif recorded and moment > recorded:
                out.append(Violation("I16", f"{name} {p[name]} is after the time it is recorded, {ctx.recorded_at}", index))
        if op.type in ("item.created", "item.revised"):
            row = ctx.memory.item(p["item_id"]) if op.type == "item.revised" else None
            start = p.get("valid_from") if p.get("valid_from") is not None else (row or {}).get("valid_from")
            end = p.get("valid_to") if p.get("valid_to") is not None else (row or {}).get("valid_to")
            starts, ends = parse_time(start), parse_time(end)
            if (start and starts is None) or (end and ends is None):
                out.append(Violation("I16", "valid_from and valid_to are ISO 8601 times", index))
            elif starts and ends and starts > ends:
                out.append(Violation("I16", f"valid_from {start} is after valid_to {end}", index))
        if op.type in ITEM_CREATES:
            problem = said_at_problem(p["said_at"], ctx.op_origin(op), ctx.evidences(p["evidence_ids"]), ctx.history)
            if problem:
                out.append(Violation("I16", problem, index))
        if op.type == "supersession.applied" and p["reason"] == "your_later_statement" and p["old_item"] != p["new_item"]:
            problem = later_statement_problem(ctx, p)
            if problem:
                out.append(Violation("I16", problem, index))
    for ev in ctx.new_evidence.values():
        msg = ctx.history.message(ev.message_id)
        said = parse_time(msg.occurred_at) if msg else None
        if said and recorded and said > recorded:
            out.append(Violation("I16", f"evidence {ev.id} is from a message dated after it is recorded"))
    return out


# --- I5, I16, I1: the reason a supersession or a conflict resolution gives is found, not read ------------------------------

# Corrections of yours that settle a question about an item: you said it is not what you think, or you said to keep it.
SETTLING_CORRECTIONS = ("not_what_i_think", "keep")


def _corrected(ctx: Context, kinds: Iterable[str], target: str) -> bool:
    """You made one of these corrections on an item (a lifted one does not count): on file, or in this proposal."""
    kinds = tuple(kinds)
    if any(c["kind"] in kinds and c["target"] == target for c in ctx.memory.active_corrections()):
        return True
    return any(o.type == "correction.applied" and o.payload["kind"] in kinds and o.payload["target"] == target for o in ctx.ops)


def _conflict_sides(ctx: Context, conflict_id: str) -> tuple[str, str] | None:
    row = ctx.memory.row("conflict", conflict_id)
    if row is not None:
        return row["side_a_item"], row["side_b_item"]
    made = ctx.created.get(conflict_id)
    if made and made[0] == "conflict":
        return made[2].payload["side_a_item"], made[2].payload["side_b_item"]
    return None


def check_precedence(ctx: Context) -> list[Violation]:
    """What decides a replacement or a conflict is found in the stores, whatever the proposal says it was (§2.6). A
    supersession 'by your correction' needs a correction of yours on one of the two items; 'check contradicted' needs the
    item's check to be contradicted; a conflict settled at step 0 needs your correction on a side, and at step 2 the winner
    must have been said later by the time of the messages. (A 'later statement' supersession is I16's, above.)"""
    out: list[Violation] = []
    for index, op in enumerate(ctx.ops):
        p = op.payload
        if op.type == "supersession.applied" and p["old_item"] != p["new_item"]:
            if p["reason"] == "your_correction" and not (
                _corrected(ctx, ("not_what_i_think",), p["old_item"]) or _corrected(ctx, ("keep",), p["new_item"])
            ):
                out.append(Violation("I5", f"'your_correction' needs a correction of yours on {p['old_item']} or {p['new_item']}, and none is on file", index))
            elif p["reason"] == "check_contradicted":
                old = ctx.item(p["old_item"]) or {}
                said_here = any(o.type == "item.checked" and o.payload["item_id"] == p["old_item"] and o.payload["check_status"] == "contradicted" for o in ctx.ops)
                if old.get("check_status") != "contradicted" and not said_here:
                    out.append(Violation("I1", f"'check_contradicted' needs the check of {p['old_item']} to be contradicted, and it is not", index))
        elif op.type == "conflict.resolved" and p["step"] in (0, 2):
            sides = _conflict_sides(ctx, p["conflict_id"])
            if sides is None or p["winner"] not in sides:
                out.append(Violation("I1", f"the winner {p['winner']} is not a side of conflict {p['conflict_id']}", index))
                continue
            loser = sides[1] if p["winner"] == sides[0] else sides[0]
            if p["step"] == 0 and not (_corrected(ctx, ("not_what_i_think",), loser) or _corrected(ctx, ("keep",), p["winner"])):
                out.append(Violation("I5", f"step 0 is your correction, and none of yours on {p['winner']} or {loser} is on file", index))
            elif p["step"] == 2:
                problem = later_statement_problem(ctx, dict(new_item=p["winner"], old_item=loser, evidence_ids=[]))
                if problem:
                    out.append(Violation("I16", f"step 2 is a later statement: {problem}", index))
    return out


# --- I17: scope ---------------------------------------------------------------------------------------------------


def check_i17(ctx: Context) -> list[Violation]:
    """Everything has a scope, and a new scope is no wider than where the item was learned. A scope widens only
    through item.scope_widened, on evidence from a second context."""
    out: list[Violation] = []
    for index, op in enumerate(ctx.ops):
        p = op.payload
        if op.type in ITEM_CREATES:
            for ev in ctx.evidences(p["evidence_ids"]):
                source = ctx.history.source(ev.source_id) if ev.source_id else None
                if source and not scope_covers(p["scope"], source["scope"]):
                    out.append(Violation("I17", f"scope {p['scope']} is wider than, or not, the scope it was learned in ({source['scope']})", index))
                    break
        elif op.type == "item.revised" and p.get("scope") is not None:
            row = ctx.memory.item(p["item_id"])
            if row and row["scope"] != "personal" and p["scope"] != row["scope"]:
                out.append(Violation("I17", "a revision may narrow a personal item to a project; widening goes through item.scope_widened", index))
        elif op.type == "item.scope_widened":
            row = ctx.item(p["item_id"])
            second = False
            own = _item_evidence(ctx, p["item_id"])
            for ev in ctx.evidences(p["evidence_ids"]):
                if ev.id not in own or not ev.typed_by_you:  # words of yours that the item rests on, not any message at all
                    out.append(Violation("I17", f"widening needs your typed words that {p['item_id']} rests on; {ev.id} is not", index))
                    continue
                source = ctx.history.source(ev.source_id) if ev.source_id else None
                if source is None:
                    second = True  # scope not readable: the gate cannot say it is the same context
                else:
                    second = second or source["scope"] != p["from_scope"]
            if row and row["scope"] != p["from_scope"]:
                out.append(Violation("I17", f"the item's scope is {row['scope']}, not {p['from_scope']}", index))
            if not second:
                out.append(Violation("I17", "a scope widens only on evidence from a second context", index))
    return out


# --- I21: corrections are constraints -----------------------------------------------------------------------------

_SYMMETRIC_LINKS = ("conflicts", "same_as")


def correction_break(correction: Mapping[str, Any], op_type: str, p: Mapping[str, Any], memory: MemoryRead) -> str | None:
    """Why an automated op breaks an active correction (I21), or None. `correction` has kind, target and params."""
    kind, target, params = correction["kind"], correction["target"], correction.get("params") or {}
    other = params.get("with")
    if kind == "not_what_i_think":
        if op_type == "item.status_changed" and p["item_id"] == target and p["to_status"] == "active":
            return "you said this is not what you think; it stays retracted"
        if op_type == "item.revised" and p["item_id"] == target:
            return "you said this is not what you think; it is not revised"
    elif kind == "project_only" and op_type == "item.scope_widened" and p["item_id"] == target:
        return "you made this project-only; it is not widened"
    elif kind == "rename" and op_type == "topic.renamed" and p["topic_id"] == target:
        return "you named this topic; its label is fixed"
    elif kind == "move" and op_type == "idea.moved" and p["item_id"] == target:
        return "you moved this idea; it stays where you put it"
    elif kind == "keep_together" and op_type == "topic.split" and p["topic_id"] == target:
        return "you asked to keep this topic together; it is not split"
    elif kind == "these_are_different":
        pair = {target, other}
        if op_type in ("link.applied", "link.proposed") and p["link_type"] == "same_as" and {p["from_id"], p["to_id"]} == pair:
            return "you said these are different; they are not merged"
        if op_type == "topic.merged" and {p["from_topic_id"], p["into_topic_id"]} == pair:
            return "you said these topics are different; they are not merged"
    elif kind == "give_own_topic":
        if (op_type == "topic.folded_back" and p["topic_id"] == target) or (op_type == "topic.merged" and p["from_topic_id"] == target):
            return "you gave this its own topic; it is not folded back or merged"
    elif kind == "fold_back" and op_type in ("topic.branched", "topic.split") and p["topic_id"] == target:
        return "you folded this topic back; it is not spun off again"
    elif kind == "not_part_of_this":
        topic = params.get("topic")
        if op_type == "idea.placed" and p["item_id"] == target and p["topic_id"] == topic:
            return "you said this idea is not part of that topic"
        if op_type == "idea.moved" and p["item_id"] == target and p["to_topic_id"] == topic:
            return "you said this idea is not part of that topic"
    elif kind == "confirm_link" and op_type == "link.retracted" and p["link_id"] == target:
        return "you confirmed this link; it is not retracted"
    elif kind == "reject_link" and op_type in ("link.applied", "link.proposed"):
        link = memory.link(target)
        if link and p["link_type"] == link["type"]:
            same = (p["from_id"], p["to_id"]) == (link["from_id"], link["to_id"])
            flipped = (p["from_id"], p["to_id"]) == (link["to_id"], link["from_id"]) and link["type"] in _SYMMETRIC_LINKS
            if same or flipped:
                return "you rejected this link; it is never proposed again"
    elif kind == "purge" and op_type != "purge.applied" and target in _subjects_of(op_type, p):
        return "you purged this; nothing automated touches it again"
    return None


def _subjects_of(op_type: str, payload: Mapping[str, Any]) -> list[str]:
    cls = events.payload_class(op_type)
    return cls(**payload).subjects() if cls else []  # type: ignore[arg-type]


def compensation_break(memory: MemoryRead, payload: Mapping[str, Any]) -> str | None:
    """Why an automated compensation.batch undoes your own mark (I21, I5), or None: a rollback would remove a
    correction or a purge's record, or reverse a confirmation, which no automated change may do."""
    for event_id in payload.get("compensated_event_ids") or []:
        row = memory._one("SELECT type, actor FROM event WHERE id = ?", (event_id,))
        if row and (row["type"] in YOUR_MARKS or row["actor"] == "user"):
            return f"event {event_id} ({row['type']}) is your own mark; an automated rollback cannot undo it"
    return None


def _same_link(link: Mapping[str, Any], link_type: str, from_id: str, to_id: str, to_kind: str) -> bool:
    """The same link: the same type and ends, either way round for a symmetric type."""
    if link["type"] != link_type or link["to_kind"] != to_kind:
        return False
    ends, wanted = (link["from_id"], link["to_id"]), (from_id, to_id)
    return ends == wanted or (link_type in _SYMMETRIC_LINKS and ends == wanted[::-1])


def link_break(memory: MemoryRead, op_type: str, p: Mapping[str, Any]) -> str | None:
    """Why an automated op breaks your word about a link (I21), or None. The link table is read, not only correction
    rows: a link you rejected is not applied or proposed again (the same type and ends; either way round for a
    symmetric type), and a link you confirmed is not retracted."""
    if op_type in ("link.applied", "link.proposed"):
        for link in memory._all("SELECT * FROM link WHERE status = 'rejected' AND tenant_id = ?", (memory.tenant_id,)):
            if _same_link(link, p["link_type"], p["from_id"], p["to_id"], p.get("to_kind", "item")):
                return f"you rejected this link ({link['id']}); it is never applied or proposed again"
    elif op_type == "link.retracted":
        link = memory.link(p["link_id"])
        if link and link["status"] == "confirmed":
            return f"you confirmed this link ({link['id']}); it is not retracted"
    return None


def check_i21(ctx: Context) -> list[Violation]:
    """Your corrections are constraints that no automated change may break."""
    corrections = ctx.memory.active_corrections()
    out: list[Violation] = []
    for index, op in enumerate(ctx.ops):
        if op.type == "compensation.batch" and _automated(op.actor):
            reason = compensation_break(ctx.memory, op.payload)
            if reason:
                out.append(Violation("I21", reason, index))
        if not _automated(op.actor) or op.type.startswith("correction."):
            continue
        for correction in corrections:
            reason = correction_break(correction, op.type, op.payload, ctx.memory)
            if reason:
                out.append(Violation("I21", f"{reason} (correction {correction['id']})", index))
        reason = link_break(ctx.memory, op.type, op.payload)
        if reason:
            out.append(Violation("I21", reason, index))
    return out


# --- I24, I11: Northstar's own text -------------------------------------------------------------------------------


def check_i24(ctx: Context) -> list[Violation]:
    """Northstar's own text never counts as evidence (I24, I11): evidence is not anchored on a message Northstar's
    own capture marked, and an item cannot rest on echoes of Northstar's text alone."""
    out: list[Violation] = []
    for index, op in enumerate(ctx.ops):
        if op.type != "evidence.anchored":
            continue
        msg = ctx.history.message(op.payload["message_id"])
        if msg and ctx.history.northstar_marked(msg):
            out.append(Violation("I24", f"message {msg.id} is Northstar's own text; it is never evidence", index))
    for index, op in enumerate(ctx.ops):
        if op.type in ITEM_CREATES:
            evs = ctx.evidences(op.payload["evidence_ids"])
            if evs and all(e.lineage == "northstar_echo" for e in evs):
                out.append(Violation("I11", "an item cannot rest on echoes of Northstar's own text alone", index))
    return out


# --- the checks the gate runs -------------------------------------------------------------------------------------

# Run before anything else: if the shape is wrong, the other checks cannot read the payloads.
INTAKE: list[tuple[tuple[str, ...], Callable[[Context], list[Violation]]]] = [
    (("I1", "I3", "I4", "I5", "I14", "I15", "I16", "I17", "I20"), check_schema),
    (("I14",), check_i14),
    (("I5",), check_authority),
]
CODE_CHECKS: list[tuple[tuple[str, ...], Callable[[Context], list[Violation]]]] = [
    (("I1",), check_i1),
    (("I1",), check_value),
    (("I2",), check_i2),
    (("I3",), check_learned_in),
    (("I3",), check_work),
    (("I20",), check_i20),
    (("I4",), check_i4),
    (("I5",), check_i5),
    (("I7",), check_i7),
    (("I12",), check_i12),
    (("I16",), check_i16),
    (("I5", "I16", "I1"), check_precedence),
    (("I17",), check_i17),
    (("I21",), check_i21),
    (("I24", "I11"), check_i24),
]
# I13 (caps) runs after the verdicts, and the loss bound holds the run: see gate.py.
GATE_CHECKS = INTAKE + CODE_CHECKS + [(("I13",), check_i13)]


def run_checks(checks: Sequence[tuple[tuple[str, ...], Callable[[Context], list[Violation]]]], ctx: Context) -> list[Violation]:
    out: list[Violation] = []
    for _, check in checks:
        out.extend(check(ctx))
    return out


# --- the nightly read-only sweep ----------------------------------------------------------------------------------

# Every trigger that keeps a store append-only or an identity frozen (I3, I6, I14, I20): the sweep checks each is still
# installed. A test reads the schema files and fails when one gains a trigger this table does not name. Limits that are
# not append-only (two topic levels, two also_in places) are left out.
_HISTORY_TABLES = (
    "item", "evidence", "link", "supersession", "conflict", "work", "style_line", "correction", "scope", "topic", "placement",
)
REQUIRED_TRIGGERS = {
    "memory": (
        "event_subject_no_update", "event_subject_no_delete", "purge_authorization_no_update", "purge_authorization_no_delete",
        "event_frozen", "event_no_update", "event_no_delete", "evidence_frozen", "evidence_no_delete",
        "stance_no_update", "stance_no_delete",
        *(f"{table}_history_{kind}" for table in _HISTORY_TABLES for kind in ("no_update", "no_delete")),
    ),
    "history": (
        "purge_authorization_no_update", "purge_authorization_no_delete", "source_identity_frozen", "source_sensitivity_only_rises",
        "source_no_delete", "message_identity_frozen", "message_no_update", "message_no_delete", "work_event_identity_frozen",
        "work_event_no_update", "work_event_no_delete", "blob_no_update", "blob_no_delete", "reconciliation_no_update",
        "reconciliation_no_delete",
    ),
    "runs": (
        "model_call_no_update", "model_call_no_delete", "proposal_applied_final_update", "proposal_applied_final_delete",
        "verdict_no_update", "verdict_no_delete", "change_log_frozen", "change_log_undone_once", "change_log_no_delete",
    ),
}  # fmt: skip


def _env_from_row(row: Mapping[str, Any]) -> EventEnvelope:
    return EventEnvelope(
        type=row["type"], payload=json.loads(row["payload"]), actor=row["actor"], config_version=row["config_version"],
        subjects=json.loads(row["subjects"]), id=row["id"], schema_version=row["schema_version"], run_id=row["run_id"],
        proposal_id=row["proposal_id"], index_in_proposal=row["index_in_proposal"], inputs=json.loads(row["inputs"]),
        compensates=row["compensates"], recorded_at=row["recorded_at"], seq=row["seq"],
    )  # fmt: skip


def _merge_targets(mem: MemoryRead) -> set[str]:
    """Items that absorbed another by a merge: their evidence now includes the merged item's, so origin is not recomputed."""
    rows = mem._all("SELECT to_id FROM link WHERE type = 'same_as' AND status IN ('applied', 'confirmed') AND tenant_id = ?", (mem.tenant_id,))
    return {r["to_id"] for r in rows}


def sweep(stores: Mapping[str, sqlite3.Connection], *, tenant_id: str = DEFAULT_TENANT) -> list[Violation]:
    """Check every invariant that can be checked after the fact, over whole stores, and change nothing.

    `stores` maps store names to open connections ('memory' is required; 'history' lets the quote, speaker, origin and
    scope checks run). Returns every violation found; an empty list means the stores are sound.
    """
    mem = MemoryRead(stores["memory"], tenant_id)
    hist = HistoryRead(stores["history"], tenant_id) if "history" in stores else None
    out: list[Violation] = []
    for part in (
        _sweep_triggers, _sweep_evidence, _sweep_items, _sweep_goals_style_corrections, _sweep_events, _sweep_merges,
        _sweep_corrections,
    ):
        out.extend(part(mem, hist, stores))
    if hist is not None:
        out.extend(_sweep_history(hist))
    return out


def _sweep_triggers(mem: MemoryRead, hist: HistoryRead | None, stores: Mapping[str, sqlite3.Connection]) -> list[Violation]:
    """I6: append-only is a trigger. The sweep checks that the triggers are still installed."""
    out: list[Violation] = []
    for name, wanted in REQUIRED_TRIGGERS.items():
        if name not in stores:
            continue
        present = {r["name"] for r in _rows(stores[name].execute("SELECT name FROM sqlite_master WHERE type = 'trigger'"))}
        out.extend(Violation("I6", f"the {name} trigger {t} is missing", ref=f"{name}:{t}") for t in wanted if t not in present)
    return out


def _sweep_evidence(mem: MemoryRead, hist: HistoryRead | None, stores: Mapping[str, sqlite3.Connection]) -> list[Violation]:
    """I1, I2, I3, I20: every evidence row points at a real message, quotes it exactly, and carries who said it."""
    out: list[Violation] = []
    if hist is None:
        return out
    purged = {r["id"] for r in mem.items("status = 'purged'")}
    for row in mem.all_evidence():
        if row["subject_id"] in purged:
            continue
        ref = f"evidence:{row['id']}"
        msg = hist.message(row["message_id"])
        if msg is None:
            out.append(Violation("I1", f"evidence cites message {row['message_id']}, which is not in chat history", ref=ref))
            continue
        problem = quote_problem(msg.text, row["start_char"], row["end_char"], row["quote"])
        if problem:
            out.append(Violation("I2", problem, ref=ref))
        if (row["speaker"], row["agent"], row["model_family"], row["origin"]) != (msg.speaker, msg.agent, msg.model_family, msg.origin):
            out.append(Violation("I3", "who said it differs from the message (speaker, agent, family or origin)", ref=ref))
            out.append(Violation("I20", "evidence stamps changed after capture", ref=ref))
        if row["role"] == "adoption" and not (msg.speaker == "user" and msg.origin == "typed"):
            out.append(Violation("I4", "an adoption span is not words you typed", ref=ref))
        if hist.northstar_marked(msg) and row["lineage"] != "northstar_echo":
            out.append(Violation("I24", f"evidence rests on Northstar's own text, message {msg.id}", ref=ref))
    return out


def _sweep_items(mem: MemoryRead, hist: HistoryRead | None, stores: Mapping[str, sqlite3.Connection]) -> list[Violation]:
    """I1, I4, I11, I16, I17 and the origin of I3/I20, over every item."""
    out: list[Violation] = []
    merged = _merge_targets(mem)
    for item in mem.items("status <> 'purged'"):
        ref = f"item:{item['id']}"
        rows = mem.evidence_for(item["id"])
        if item["merged_into"] and not rows:
            continue  # merged into another item: its evidence moved to the kept item (§5.8)
        if not rows:
            out.append(Violation("I1", "the item cites no evidence", ref=ref))
            continue
        evs = [evidence_from_row(r, hist) for r in rows]
        if all(e.lineage == "northstar_echo" for e in evs):
            out.append(Violation("I11", "the item rests on echoes of Northstar's own text alone", ref=ref))
        if item["id"] not in merged:
            computed = origin_of(evs)
            if computed != item["origin"]:
                out.append(Violation("I20", f"the item's origin is {item['origin']}, its evidence says {computed}", ref=ref))
            if item["origin"].startswith("adopted:") and not any(e.role == "adoption" and e.typed_by_you for e in evs):
                out.append(Violation("I4", "an adopted item has no adoption span of words you typed", ref=ref))
        said, recorded = parse_time(item["said_at"]), parse_time(item["recorded_at"])
        if said is None or recorded is None or said > recorded:
            out.append(Violation("I16", f"said_at {item['said_at']} is not before recorded_at {item['recorded_at']}", ref=ref))
        if hist is not None and item["id"] not in merged:
            problem = said_at_problem(item["said_at"], item["origin"], evs, hist)
            if problem:
                out.append(Violation("I16", problem, ref=ref))
            problem = learned_in_problem(item["learned_in"], evs, hist)
            if problem:
                out.append(Violation("I3", problem, ref=ref))
            for text in your_words_problems(item["your_words"], item["why"], evs, hist):
                out.append(Violation("I2", text, ref=ref))
        start, end = parse_time(item["valid_from"]), parse_time(item["valid_to"])
        if start and end and start > end:
            out.append(Violation("I16", "valid_from is after valid_to", ref=ref))
        if hist is not None:
            scopes = []
            for e in evs:
                source = hist.source(e.source_id) if e.source_id else None
                if source:
                    scopes.append(source["scope"])
            widened = mem.has_event_about(item["id"], "item.scope_widened")
            bad = [s for s in scopes if not scope_covers(item["scope"], s)]
            if bad and not (widened and item["scope"] == "personal"):
                out.append(Violation("I17", f"scope {item['scope']} is wider than, or not, the scope it was learned in ({bad[0]})", ref=ref))
    for stance in mem._all("SELECT * FROM stance WHERE stance = 'adopted' AND tenant_id = ?", (mem.tenant_id,)):
        ids = json.loads(stance["evidence_ids"])
        evs = [evidence_from_row(r, hist) for r in (mem.evidence(i) for i in ids) if r]
        if hist and not any(e.typed_by_you for e in evs):
            out.append(Violation("I4", "an adoption stance has no words you typed", ref=f"stance:{stance['id']}"))
    return out


def _typed_evidence(mem: MemoryRead, hist: HistoryRead | None, evidence_ids: Iterable[str]) -> bool | None:
    """True if any cited evidence is words you typed; None if history is not available to say."""
    if hist is None:
        return None
    return any(evidence_from_row(r, hist).typed_by_you for r in (mem.evidence(i) for i in evidence_ids) if r)


def _sweep_goals_style_corrections(mem: MemoryRead, hist: HistoryRead | None, stores: Mapping[str, sqlite3.Connection]) -> list[Violation]:
    """I5: stated goals, working-style defaults and typed corrections rest on words you typed."""
    out: list[Violation] = []
    for item in mem.items("kind = 'goal' AND status <> 'purged'"):
        ids = [r["id"] for r in mem.evidence_for(item["id"])]
        if item["goal_basis"] == "stated" and _typed_evidence(mem, hist, ids) is False:
            out.append(Violation("I5", "a stated goal has no words you typed", ref=f"item:{item['id']}"))
        if item["origin"] != "yours":
            out.append(Violation("I5", "a goal that is not yours", ref=f"item:{item['id']}"))
    for line in mem._all("SELECT * FROM style_line WHERE tenant_id = ?", (mem.tenant_id,)):
        rows = mem.evidence_for(line["id"])
        if not rows:
            out.append(Violation("I5", "a working-style line cites no evidence", ref=f"style_line:{line['id']}"))
        elif line["basis"] == "stated_default" and _typed_evidence(mem, hist, [r["id"] for r in rows]) is False:
            out.append(Violation("I5", "a working-style default has no words you typed", ref=f"style_line:{line['id']}"))
    for corr in mem._all("SELECT * FROM correction WHERE via = 'typed' AND tenant_id = ?", (mem.tenant_id,)):
        if corr["evidence_id"] is None or _typed_evidence(mem, hist, [corr["evidence_id"]]) is False:
            out.append(Violation("I5", "a typed correction has no words you typed", ref=f"correction:{corr['id']}"))
    return out


def _sweep_events(mem: MemoryRead, hist: HistoryRead | None, stores: Mapping[str, sqlite3.Connection]) -> list[Violation]:
    """I7, I14, I15 over the event log."""
    out: list[Violation] = []
    contiguous: dict[tuple[str, str], list[int]] = {}
    for row in mem._all("SELECT * FROM event WHERE tenant_id = ? ORDER BY seq", (mem.tenant_id,)):
        ref = f"event:{row['id']}"
        env = _env_from_row(row)
        for problem in events.problems(env, draft=False):
            out.append(Violation("I15", problem, ref=ref))
        for text in env.inputs:
            problem = input_problem(text)
            if problem:
                out.append(Violation("I7", problem, ref=ref))
        if env.proposal_id is not None:
            contiguous.setdefault((env.run_id or "", env.proposal_id), []).append(env.index_in_proposal or 0)
    for (run_id, proposal_id), indexes in contiguous.items():
        if sorted(indexes) != list(range(len(indexes))):
            out.append(Violation("I14", f"proposal {proposal_id} of run {run_id} has events {sorted(indexes)}, not 0..{len(indexes) - 1}", ref=f"proposal:{proposal_id}"))
    return out


def _sweep_merges(mem: MemoryRead, hist: HistoryRead | None, stores: Mapping[str, sqlite3.Connection]) -> list[Violation]:
    """I12: every merge in force has an exact key or two agreeing families."""
    out: list[Violation] = []
    for link in mem._all("SELECT * FROM link WHERE type = 'same_as' AND status IN ('applied', 'confirmed') AND tenant_id = ?", (mem.tenant_id,)):
        families = set(json.loads(link["checked_by"]))
        problem = merge_problem(mem.item(link["from_id"]), mem.item(link["to_id"]), families)
        if problem and "checked by" not in problem:
            out.append(Violation("I12", problem, ref=f"link:{link['id']}"))
    return out


def _sweep_corrections(mem: MemoryRead, hist: HistoryRead | None, stores: Mapping[str, sqlite3.Connection]) -> list[Violation]:
    """I21 and I5: your marks are recorded under you and nothing else; no automated event after an active correction
    breaks it; no automated event applies a link you rejected or retracts one you confirmed; and no automated rollback
    undoes your marks."""
    out: list[Violation] = []
    for row in mem._all("SELECT * FROM event WHERE type = 'compensation.batch' AND tenant_id = ? ORDER BY seq", (mem.tenant_id,)):
        reason = compensation_break(mem, json.loads(row["payload"])) if _automated(row["actor"]) else None
        if reason:
            out.append(Violation("I21", reason, ref=f"event:{row['id']}"))
    for row in mem._all("SELECT * FROM event WHERE tenant_id = ? ORDER BY seq", (mem.tenant_id,)):
        if row["type"] in YOUR_MARKS and _automated(row["actor"]):
            out.append(Violation("I5", f"{row['type']} is your mark and was recorded under {row['actor']}, not under you", ref=f"event:{row['id']}"))
    for correction in mem.active_corrections():
        rows = mem._all("SELECT * FROM event WHERE seq > ? AND tenant_id = ? ORDER BY seq", (correction["created_seq"], mem.tenant_id))
        for row in rows:
            if not _automated(row["actor"]) or row["type"].startswith("correction."):
                continue
            reason = correction_break(correction, row["type"], json.loads(row["payload"]), mem)
            if reason:
                out.append(Violation("I21", f"{reason} (correction {correction['id']})", ref=f"event:{row['id']}"))
    for link in mem._all("SELECT * FROM link WHERE status IN ('rejected', 'confirmed') AND tenant_id = ?", (mem.tenant_id,)):
        later = mem._all(
            "SELECT * FROM event WHERE seq > ? AND type IN ('link.applied', 'link.proposed', 'link.retracted') AND tenant_id = ? ORDER BY seq",
            (link["seq_from"], mem.tenant_id),
        )
        for row in later:
            if not _automated(row["actor"]):
                continue
            payload = json.loads(row["payload"])
            if link["status"] == "rejected" and row["type"] != "link.retracted":
                broken = _same_link(link, payload["link_type"], payload["from_id"], payload["to_id"], payload.get("to_kind", "item"))
            else:
                broken = link["status"] == "confirmed" and row["type"] == "link.retracted" and payload["link_id"] == link["id"]
            if broken:
                out.append(Violation("I21", f"an automated {row['type']} breaks your word about link {link['id']} ({link['status']})", ref=f"event:{row['id']}"))
    return out


def _sweep_history(hist: HistoryRead) -> list[Violation]:
    """I24: a message in one of Northstar's own output sources is marked as Northstar's."""
    out: list[Violation] = []
    if hist.conn is None:
        return out
    rows = _rows(hist.conn.execute(
        "SELECT m.id, m.speaker, m.origin FROM message m JOIN source s ON s.id = m.source_id WHERE s.kind = 'northstar_output'"
    ))  # fmt: skip
    for row in rows:
        if row["speaker"] != "northstar" and row["origin"] != "northstar_injected":
            out.append(Violation("I24", "a message in a Northstar output source is not marked as Northstar's", ref=f"message:{row['id']}"))
    return out
