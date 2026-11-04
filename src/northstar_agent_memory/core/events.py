"""The event log's types, envelope and validation (MEMORY-ARCHITECTURE §2.3-§2.8, §5.9, invariants I3, I5, I14, I15).

There are 42 event types in 12 families, exactly as §2.3's table lists them. Each type has a payload dataclass
that names its required fields; fields §2.3-§2.8 do not spell out are the smallest set the type needs, and each
docstring says which those are. `validate` rejects an unknown type, a missing, unknown or wrongly typed field, and
a payload that does not match its schema version (I15).

Two kinds of payload field are not a proposal's to set (I3, I20): the speaker, agent, model family, origin and
context that the gate copies from chat history ("stamped" fields). A draft carries none of them; the gate stamps them
before the event is appended, so the log is self-contained and replays without reading chat history (I18).

Class and certainty are not payload fields: the item's class follows from its kind (`ITEM_CLASS_OF_KIND`).
"""

from __future__ import annotations

import json
import re
import types
from dataclasses import MISSING, asdict, dataclass, field, fields
from typing import Any, ClassVar, Literal, Mapping, Union, get_args, get_origin, get_type_hints

from northstar_agent_memory.core.ids import is_ulid, new_id

# --- enumerations (each is also a CHECK constraint in the schema files; test_schema keeps them in step) -----------

ITEM_KINDS = (
    "decision", "ruled_out", "result", "conclusion", "definition", "plan",
    "principle", "approach", "position", "goal", "question",
)  # fmt: skip
PLAIN_ITEM_KINDS = tuple(k for k in ITEM_KINDS if k not in ("goal", "question"))  # goals and questions have their own events
FACT_KINDS = ("decision", "ruled_out", "result", "conclusion", "definition", "plan")
# Class is set by kind; goals and questions are not facts, so they take the stricter class (§2.4: when unsure, view).
ITEM_CLASS_OF_KIND = {k: ("fact" if k in FACT_KINDS else "view") for k in ITEM_KINDS}
ITEM_CLASSES = ("fact", "view")
ITEM_VALUES = ("forming", "kept")
ITEM_STATUSES = ("active", "superseded", "retracted", "quarantined", "purged")
CHECK_STATUSES = ("not_needed", "unchecked", "checked", "contradicted", "not_independent")
VALUE_SIGNALS = ("later_day", "built_on", "used_in_work", "second_context", "your_keep")  # §2.4: the five signals
EVIDENCE_ROLES = ("primary", "adoption", "support", "reason", "scope")
LINEAGES = ("primary", "northstar_echo")
EVIDENCE_SUBJECT_KINDS = ("item", "style_line", "correction")
SPEAKERS = ("user", "assistant", "tool", "northstar", "system")
ORIGINS = ("typed", "pasted", "assistant_output", "tool_output", "model_reported", "northstar_injected")
STANCES = ("stated", "adopted", "ruled_out", "revised", "built_on")
LINK_TYPES = ("supports", "refines", "conflicts", "answers", "case_of", "advances", "used_in", "same_as")
LINK_STATED_BY = ("you", "northstar", "construction")
LINK_STATUSES = ("proposed", "applied", "confirmed", "rejected", "retracted")
LINK_TO_KINDS = ("item", "work")
SUPERSESSION_REASONS = (
    "your_later_statement", "ai_self_correction", "check_contradicted", "your_correction", "refresh", "scope_split",
)  # fmt: skip
SUPERSESSION_STATUSES = ("applied", "undone")
CONFLICT_KINDS = ("across_contexts", "same_context")
CONFLICT_STATES = ("both_stand", "open", "resolved", "contested", "undone")
GOAL_BASES = ("stated", "reported", "reused")
GOAL_STATUSES = ("active", "paused", "done", "dropped")
QUESTION_RAISED_BY = ("you", "ai_taken_up", "conflict")
QUESTION_STATUSES = ("open", "answered", "dormant")
WORK_KINDS = ("commit", "file_version", "render", "diagram", "decision_record")
WORK_EVIDENCE = ("strong", "medium", "weak")
WORK_LABEL_SOURCES = ("checked", "commit_message", "file_name")
STYLE_BASES = ("stated_default", "seen_in_sessions")
STYLE_STATUSES = ("active", "retracted")
CORRECTION_KINDS = (
    "not_what_i_think", "keep", "project_only", "rename", "move", "keep_together", "these_are_different",
    "give_own_topic", "fold_back", "not_part_of_this", "confirm_link", "reject_link", "pin", "purge",
)  # fmt: skip
CORRECTION_STATUSES = ("active", "lifted")
CORRECTION_VIA = ("typed", "click")
CORRECTION_LIFTED_REASONS = ("your_undo", "your_later_correction", "purge")
SCOPE_KINDS = ("personal", "project", "work", "session")
TOPIC_STATUSES = ("active", "dormant", "merged_into", "split_into", "folded_into")
PLACEMENT_ROLES = ("home", "also_in")
RISK_TIERS = ("low", "medium", "high")

_SCOPE_RE = re.compile(r"^(personal|(project|work|session):\S.*)$")

# --- the 42 types in 12 families (§2.3) ---------------------------------------------------------------------------

FAMILIES: dict[str, tuple[str, ...]] = {
    "evidence": ("evidence.anchored",),
    "items": (
        "item.created", "item.revised", "item.value_changed", "item.scope_widened", "item.status_changed",
        "item.checked",
    ),  # fmt: skip
    "your_moves": ("stance.recorded",),
    "links": ("link.proposed", "link.applied", "link.confirmed", "link.rejected", "link.retracted"),
    "supersession": ("supersession.applied", "supersession.undone"),
    "conflicts": ("conflict.opened", "conflict.resolved", "conflict.reopened", "conflict.undone"),
    "goals_and_questions": (
        "goal.created", "goal.status_changed", "goal.confirmed", "question.created", "question.status_changed",
    ),  # fmt: skip
    "your_work": ("work.registered", "work.labelled"),
    "working_style": ("style.recorded", "style.revised"),
    "corrections": ("correction.applied", "correction.lifted"),
    "structure": (
        "topic.created", "topic.split", "topic.branched", "topic.merged", "topic.folded_back", "topic.renamed",
        "topic.dormant", "idea.placed", "idea.moved",
    ),  # fmt: skip
    "maintenance_and_privacy": ("compensation.batch", "purge.applied", "scope.hold_changed"),
}
EVENT_TYPES: tuple[str, ...] = tuple(t for types_ in FAMILIES.values() for t in types_)
FAMILY_OF: dict[str, str] = {t: fam for fam, types_ in FAMILIES.items() for t in types_}

# --- payload dataclasses ------------------------------------------------------------------------------------------

Scope = str  # personal | project:<id> | work:<org> | session:<id>


def _literal(values: tuple) -> Any:
    return Literal[values]  # type: ignore[valid-type]


ItemKind = _literal(ITEM_KINDS)
PlainItemKind = _literal(PLAIN_ITEM_KINDS)

PAYLOADS: dict[tuple[str, int], type["Payload"]] = {}  # (type, schema version) -> payload class


class Payload:
    """Base of every payload. Subclasses are dataclasses registered with @event."""

    TYPE: ClassVar[str] = ""
    VERSION: ClassVar[int] = 1
    SUBJECTS: ClassVar[tuple[str, ...]] = ()  # fields (a str, or a list of str) whose values are the event's subjects
    STAMPED: ClassVar[tuple[str, ...]] = ()  # fields the gate copies from chat history; a draft leaves them None
    STAMPED_REQUIRED: ClassVar[tuple[str, ...]] = ()  # of those, the ones that must be set once stamped

    def check(self) -> list[str]:
        """Rules that span fields. Return problems; an empty list means fine."""
        return []

    def subjects(self) -> list[str]:
        out: list[str] = []
        for name in self.SUBJECTS:
            value = getattr(self, name)
            for v in value if isinstance(value, list) else [value]:
                if isinstance(v, str) and v and v not in out:
                    out.append(v)
        return out


def event(type_: str, *subjects: str, stamped: tuple[str, ...] = (), required: tuple[str, ...] = ()):
    """Make a class a payload dataclass and register it as the schema (version 1) of an event type."""

    def wrap(cls):
        if type_ not in EVENT_TYPES:
            raise ValueError(f"{type_} is not one of the 42 event types")
        cls = dataclass(cls)
        cls.TYPE, cls.SUBJECTS, cls.STAMPED, cls.STAMPED_REQUIRED = type_, subjects, stamped, required
        PAYLOADS[(type_, cls.VERSION)] = cls
        return cls

    return wrap


def _scope_problem(name: str, value: str) -> list[str]:
    return [] if _SCOPE_RE.match(value) else [f"{name} must be personal, project:<id>, work:<org> or session:<id>"]


# Evidence ---------------------------------------------------------------------------------------------------------

PERSONAL_CONTEXT = "personal"


def evidence_context(project: str | None) -> str:
    """The context of evidence taken from a source: its project, or "personal" for a chat outside any project.
    The gate calls this on the message's source when it stamps the evidence (§5.5); a proposal never names one."""
    return project.strip() if isinstance(project, str) and project.strip() else PERSONAL_CONTEXT



@event("evidence.anchored", "evidence_id", "subject_id", stamped=("speaker", "agent", "model_family", "origin", "context"),
       required=("speaker", "origin", "context"))  # fmt: skip
class EvidenceAnchored(Payload):
    """An exact quote from a captured message, anchored to the item, style line or correction it supports (§2.5).

    The quote and span are the proposal's; speaker, agent, model_family, origin and context are stamped by the gate
    from chat history (I3, I20). `context` is the project of the message's source, or "personal" for a chat outside
    a project (§5.5: a second context is another project, or a chat outside any project); the projector adds it to
    the item's `contexts_seen`. The subject's id may be assigned before its own event (§6.2 appends evidence first).
    """

    evidence_id: str
    subject_kind: _literal(EVIDENCE_SUBJECT_KINDS)
    subject_id: str
    message_id: str
    start_char: int
    end_char: int
    quote: str
    role: _literal(EVIDENCE_ROLES)
    lineage: _literal(LINEAGES) = "primary"
    speaker: _literal(SPEAKERS) | None = None
    agent: str | None = None
    model_family: str | None = None
    origin: _literal(ORIGINS) | None = None
    context: str | None = None

    def check(self):
        problems = []
        if self.context is not None and not self.context.strip():
            problems.append("context must name a project or 'personal'")
        if self.start_char < 0 or self.end_char <= self.start_char:
            problems.append("end_char must be greater than start_char, and start_char at least 0")
        if not self.quote.strip():
            problems.append("quote must not be empty")
        return problems


# Items ------------------------------------------------------------------------------------------------------------


@event("item.created", "item_id", stamped=("origin",), required=("origin",))
class ItemCreated(Payload):
    """A new item from one of your moves (§2.4). Goals and questions use goal.created and question.created.

    A new item is always forming, active and in the check state its origin implies (adopted claims start
    unchecked); class follows from kind. `origin` is computed by the gate from the evidence ("yours" or
    "adopted:<agent>"), never set by a proposal. `evidence_ids` must be non-empty (I1).
    """

    item_id: str
    kind: PlainItemKind
    line: str
    scope: Scope
    learned_in: str
    said_at: str
    evidence_ids: list[str]
    your_words: str = ""
    why: str = ""
    question_key: str = ""
    applies_when: str = "unknown"
    valid_from: str | None = None
    valid_to: str | None = None
    time_bound: bool = False
    origin: str | None = None

    def check(self):
        problems = _scope_problem("scope", self.scope)
        if self.scope.startswith("session:"):
            problems.append("an item's scope is personal, project:<id> or work:<org>")
        if not self.evidence_ids:
            problems.append("I1: an item cites at least one piece of evidence")
        if not self.line.strip():
            problems.append("line must not be empty")
        if self.origin is not None and not (self.origin == "yours" or re.match(r"^adopted:\S", self.origin)):
            problems.append("origin must be 'yours' or 'adopted:<agent>'")
        return problems


@event("item.revised", "item_id")
class ItemRevised(Payload):
    """A new version of an item: the version rises by one and the old version stays readable (§2.4, §5.7).

    `base_version` is the version the proposer read (freshness, §5.9). A field left None is unchanged.
    `scope` here only narrows or sets a scope you chose ("project only"); widening is item.scope_widened.
    """

    item_id: str
    base_version: int
    line: str
    reason: _literal(("refresh", "restated", "your_revision", "project_only"))
    your_words: str | None = None
    why: str | None = None
    question_key: str | None = None
    applies_when: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    time_bound: bool | None = None
    scope: Scope | None = None
    evidence_ids: list[str] = field(default_factory=list)

    def check(self):
        problems = _scope_problem("scope", self.scope) if self.scope is not None else []
        if self.base_version < 1:
            problems.append("base_version must be at least 1")
        return problems


@event("item.value_changed", "item_id")
class ItemValueChanged(Payload):
    """Value moves one way only, forming to kept, on one of five signals (§2.4). Code writes it."""

    item_id: str
    from_value: _literal(("forming",))
    to_value: _literal(("kept",))
    signal: _literal(VALUE_SIGNALS)
    evidence_ids: list[str] = field(default_factory=list)  # for later_day, built_on, second_context; your_keep has none


@event("item.scope_widened", "item_id")
class ItemScopeWidened(Payload):
    """A scope widened to personal, on evidence in a second context (§5.5 step 6). High tier. Never narrows."""

    item_id: str
    base_version: int
    from_scope: Scope
    to_scope: _literal(("personal",))
    evidence_ids: list[str]  # the second context's evidence

    def check(self):
        problems = _scope_problem("from_scope", self.from_scope)
        if self.from_scope == "personal":
            problems.append("from_scope is already personal")
        if not self.evidence_ids:
            problems.append("widening needs evidence in a second context")
        return problems


@event("item.status_changed", "item_id")
class ItemStatusChanged(Payload):
    """A change of status (§2.4): superseded, retracted, quarantined, or active again after an exit or an undo.

    A purge uses purge.applied. `reason` is one plain line; `ref` names the event, correction or check behind it.
    """

    item_id: str
    from_status: _literal(ITEM_STATUSES)
    to_status: _literal(ITEM_STATUSES)
    reason: str
    ref: str | None = None

    def check(self):
        return ["from_status and to_status are the same"] if self.from_status == self.to_status else []


@event("item.checked", "item_id")
class ItemChecked(Payload):
    """The check state of an adopted AI claim (§2.4, §5.9). The verdict itself is stored in runs.db.

    "Contradicted" needs evidence of its own; the checker's opinion alone is never enough.
    """

    item_id: str
    check_status: _literal(CHECK_STATUSES)
    checker_family: str | None = None  # None only for not_needed
    evidence_ids: list[str] = field(default_factory=list)

    def check(self):
        problems = []
        if self.check_status == "contradicted" and not self.evidence_ids:
            problems.append("contradicted needs evidence of its own")
        if self.check_status in ("checked", "contradicted") and not self.checker_family:
            problems.append("a check names the family that made it")
        return problems


# Your moves -------------------------------------------------------------------------------------------------------


@event("stance.recorded", "item_id")
class StanceRecorded(Payload):
    """What you did with an item: stated, adopted, ruled out, revised or built on it (§2.3, §5.4).

    Adoption needs words you typed (I4), so `evidence_ids` must be non-empty; the gate checks they are yours.
    """

    item_id: str
    stance: _literal(STANCES)
    evidence_ids: list[str]

    def check(self):
        return [] if self.evidence_ids else ["a stance cites the words that show it (I4)"]


# Links ------------------------------------------------------------------------------------------------------------


@dataclass
class _LinkFields(Payload):
    """Fields shared by link.proposed and link.applied. `to_kind` is 'work' only for used_in. One line of reason."""

    link_id: str
    from_id: str
    to_id: str
    link_type: _literal(LINK_TYPES)
    reason: str
    stated_by: _literal(LINK_STATED_BY)
    to_kind: _literal(LINK_TO_KINDS) = "item"
    checked_by: list[str] = field(default_factory=list)  # families; conflicts and cross-context links need two

    def check(self):
        problems = []
        if (self.link_type == "used_in") != (self.to_kind == "work"):
            problems.append("used_in points at a piece of work, and only used_in does")
        if self.to_kind == "item" and self.from_id == self.to_id:
            problems.append("a link joins two different items")
        if not self.reason.strip():
            problems.append("a link carries one line of reason")
        return problems


@event("link.proposed", "link_id", "from_id", "to_id")
class LinkProposed(_LinkFields):
    """A link a model proposes; it waits for its check and is not shown to you (I27)."""


@event("link.applied", "link_id", "from_id", "to_id")
class LinkApplied(_LinkFields):
    """A link that passed its checks, or was made by construction or by your words. Carries every link field, so it
    needs no earlier link.proposed. A `same_as` link is a merge: the gate's projector marks `from_id` as merged into
    `to_id`, moves its evidence, and keeps its line as an alias (§5.8)."""


@event("link.confirmed", "link_id")
class LinkConfirmed(Payload):
    """You confirmed a link Northstar found; only now may it be shown (I27). `evidence_id` holds your typed words."""

    link_id: str
    via: _literal(CORRECTION_VIA)
    evidence_id: str | None = None

    def check(self):
        return ["typed confirmation needs your words"] if self.via == "typed" and not self.evidence_id else []


@event("link.rejected", "link_id")
class LinkRejected(Payload):
    """You rejected a link; it is never proposed again (I21)."""

    link_id: str
    via: _literal(CORRECTION_VIA)
    evidence_id: str | None = None

    def check(self):
        return ["typed rejection needs your words"] if self.via == "typed" and not self.evidence_id else []


@event("link.retracted", "link_id")
class LinkRetracted(Payload):
    """A link withdrawn, e.g. when an item it joins is retracted."""

    link_id: str
    reason: str


# Supersession -----------------------------------------------------------------------------------------------------


@event("supersession.applied", "supersession_id", "old_item", "new_item")
class SupersessionApplied(Payload):
    """A newer view replaces an older one; the old version stays readable (§2.6). High tier.

    `new_version` is set when the new state is a version of the same item (a refresh): then old_item == new_item.
    """

    supersession_id: str
    old_item: str
    old_version: int
    new_item: str
    reason: _literal(SUPERSESSION_REASONS)
    new_version: int | None = None
    evidence_ids: list[str] = field(default_factory=list)

    def check(self):
        if self.old_item == self.new_item and self.new_version is None:
            return ["a new version of the same item names its version"]
        if self.old_item == self.new_item and self.new_version <= self.old_version:
            return ["new_version must be greater than old_version"]
        return []


@event("supersession.undone", "supersession_id")
class SupersessionUndone(Payload):
    """A supersession undone, restoring the earlier state. The envelope's `compensates` names the event it undoes."""

    supersession_id: str
    reason: str


# Conflicts --------------------------------------------------------------------------------------------------------


@event("conflict.opened", "conflict_id", "side_a_item", "side_b_item")
class ConflictOpened(Payload):
    """Two items disagree (§2.6). High tier. `state` starts as both_stand (different contexts), contested (same
    context, no later statement) or open. A contested conflict raises an open question (`question_id`)."""

    conflict_id: str
    side_a_item: str
    side_a_version: int
    side_b_item: str
    side_b_version: int
    kind: _literal(CONFLICT_KINDS)
    state: _literal(("both_stand", "open", "contested"))
    question_id: str | None = None
    link_id: str | None = None
    recheck_after: str | None = None

    def check(self):
        return ["a conflict has two different items"] if self.side_a_item == self.side_b_item else []


@event("conflict.resolved", "conflict_id")
class ConflictResolved(Payload):
    """A conflict settled by the order of §2.6: step 0 your correction, 1 differing scope (both stand), 2 a later
    statement (a winner), 3 contested. `resolution_inputs` are the event or item ids the step used."""

    conflict_id: str
    step: _literal((0, 1, 2, 3))
    state: _literal(("both_stand", "resolved", "contested"))
    rule_version: str
    resolution_inputs: list[str] = field(default_factory=list)
    winner: str | None = None  # an item id, for steps 0 and 2
    question_id: str | None = None
    recheck_after: str | None = None

    def check(self):
        expected = {0: "resolved", 1: "both_stand", 2: "resolved", 3: "contested"}[self.step]
        problems = [] if self.state == expected else [f"step {self.step} ends in state {expected}"]
        if self.step in (0, 2) and not self.winner:
            problems.append(f"step {self.step} names a winner")
        if self.step in (1, 3) and self.winner:
            problems.append(f"step {self.step} has no winner")
        return problems


@event("conflict.reopened", "conflict_id")
class ConflictReopened(Payload):
    """A resolved or both-stand conflict opened again, e.g. when the audit disagrees or a recheck date passes."""

    conflict_id: str
    reason: str
    state: _literal(("open", "contested")) = "open"
    recheck_after: str | None = None


@event("conflict.undone", "conflict_id")
class ConflictUndone(Payload):
    """A conflict event undone. Undoing a conflict.opened sets its state to 'undone'; undoing a resolution or a
    reopening restores the state before it from row history. `compensates` names the event undone."""

    conflict_id: str
    reason: str


# Goals and questions ----------------------------------------------------------------------------------------------


@event("goal.created", "item_id", stamped=("origin",), required=("origin",))
class GoalCreated(Payload):
    """A goal, an item of kind goal (§2.7). Only a goal you stated sets a goal (I5): basis 'stated' needs your typed
    words in `evidence_ids`; a chat app's report is 'reported' and carries no authority; 'reused' is carried over
    from an earlier chat of the same work. `work_id` is the piece of work in working memory."""

    item_id: str
    line: str
    scope: Scope
    learned_in: str
    said_at: str
    basis: _literal(GOAL_BASES)
    evidence_ids: list[str]
    work_id: str | None = None
    your_words: str = ""
    why: str = ""
    applies_when: str = "unknown"
    origin: str | None = None

    def check(self):
        problems = _scope_problem("scope", self.scope)
        if not self.evidence_ids:
            problems.append("I1: a goal cites evidence")
        return problems


@event("goal.status_changed", "item_id")
class GoalStatusChanged(Payload):
    """A goal moves between active, paused, done and dropped; done and dropped come from your words."""

    item_id: str
    from_status: _literal(GOAL_STATUSES)
    to_status: _literal(GOAL_STATUSES)
    evidence_ids: list[str] = field(default_factory=list)

    def check(self):
        return ["from_status and to_status are the same"] if self.from_status == self.to_status else []


@event("goal.confirmed", "item_id")
class GoalConfirmed(Payload):
    """You confirmed a reused or reported goal in your own typed words, so its basis becomes 'stated' (I5)."""

    item_id: str
    evidence_ids: list[str]

    def check(self):
        return [] if self.evidence_ids else ["a confirmed goal cites your typed words"]


@event("question.created", "item_id", stamped=("origin",), required=("origin",))
class QuestionCreated(Payload):
    """An open question, an item of kind question (§2.7): one you pursue, an AI's you took up, or a conflict's."""

    item_id: str
    line: str
    scope: Scope
    learned_in: str
    said_at: str
    raised_by: _literal(QUESTION_RAISED_BY)
    evidence_ids: list[str]
    your_words: str = ""
    question_key: str = ""
    origin: str | None = None

    def check(self):
        problems = _scope_problem("scope", self.scope)
        if not self.evidence_ids:
            problems.append("I1: a question cites evidence")
        return problems


@event("question.status_changed", "item_id")
class QuestionStatusChanged(Payload):
    """A question moves between open, answered and dormant; `answered_by` lists the items that answer it. The projector
    stores the list on the question (`item.answered_by`) and refuses an item that does not exist or is purged."""

    item_id: str
    from_status: _literal(QUESTION_STATUSES)
    to_status: _literal(QUESTION_STATUSES)
    answered_by: list[str] = field(default_factory=list)

    def check(self):
        problems = []
        if self.from_status == self.to_status:
            problems.append("from_status and to_status are the same")
        if self.to_status == "answered" and not self.answered_by:
            problems.append("an answered question names its answers")
        if self.to_status != "answered" and self.answered_by:
            problems.append("only an answered question names its answers")
        if self.item_id in self.answered_by:
            problems.append("a question cannot answer itself")
        if len(set(self.answered_by)) != len(self.answered_by):
            problems.append("answered_by names each item once")
        return problems


# Your work --------------------------------------------------------------------------------------------------------


@event("work.registered", "work_id")
class WorkRegistered(Payload):
    """A pointer to your work, from a work event in chat history (§2.7). The label starts as the commit message or
    file name and may later be improved by work.labelled."""

    work_id: str
    kind: _literal(WORK_KINDS)
    ref: str
    evidence: _literal(WORK_EVIDENCE)
    work_event_id: str
    label: str = ""
    project: str | None = None
    snapshot_sha256: str | None = None
    occurred_at: str | None = None
    label_source: _literal(WORK_LABEL_SOURCES) = "commit_message"


@event("work.labelled", "work_id")
class WorkLabelled(Payload):
    """One line on what the work shows; 'checked' means the other family confirmed it."""

    work_id: str
    label: str
    label_source: _literal(WORK_LABEL_SOURCES)


# Working style ----------------------------------------------------------------------------------------------------


@event("style.recorded", "style_id")
class StyleRecorded(Payload):
    """A working-style line, kept where learned (§2.7): stated as a default, or seen in 2 or more sessions. It
    needs words you typed (I5) or, for seen_in_sessions, the evidence from each session."""

    style_id: str
    line: str
    scope: Scope
    basis: _literal(STYLE_BASES)
    evidence_ids: list[str]

    def check(self):
        problems = _scope_problem("scope", self.scope)
        if not self.evidence_ids:
            problems.append("I5: a working-style line cites evidence")
        return problems


@event("style.revised", "style_id")
class StyleRevised(Payload):
    """A style line reworded, or retracted. A field left None is unchanged."""

    style_id: str
    reason: str
    line: str | None = None
    status: _literal(STYLE_STATUSES) | None = None
    evidence_ids: list[str] = field(default_factory=list)

    def check(self):
        return ["a revision changes the line or the status"] if self.line is None and self.status is None else []


# Corrections ------------------------------------------------------------------------------------------------------


@event("correction.applied", "correction_id")
class CorrectionApplied(Payload):
    """One of your one-step marks (§2.7, §5.8). `target` is the id it applies to; `params` holds its arguments
    (the new label, the topic moved to, ...); `constraint` is the rule the gate enforces from then on (I21).
    Typed corrections cite your words (I5); a click in the overview has none."""

    correction_id: str
    kind: _literal(CORRECTION_KINDS)
    target: str
    via: _literal(CORRECTION_VIA)
    at: str
    constraint: dict
    evidence_id: str | None = None
    params: dict = field(default_factory=dict)

    def check(self):
        return ["I5: a typed correction cites your words"] if self.via == "typed" and not self.evidence_id else []


@event("correction.lifted", "correction_id")
class CorrectionLifted(Payload):
    """A correction lifted: only by your undo, your later correction, or a purge. Later evidence never lifts it."""

    correction_id: str
    reason: _literal(CORRECTION_LIFTED_REASONS)


# Structure --------------------------------------------------------------------------------------------------------


@event("topic.created", "topic_id", "parent_id", "anchor_id")
class TopicCreated(Payload):
    """A new topic, or a new sub-topic when `parent_id` is set (a spin-off, §5.8). Its ideas arrive by idea.placed
    or idea.moved. `label` is in your words; `anchor_id` is your goal, a question you pursue or an idea of yours."""

    topic_id: str
    label: str
    anchor_id: str
    parent_id: str | None = None
    label_fixed: bool = False
    formation_overlap: float | None = None  # set when the topic comes from a split, to make merging back harder

    def check(self):
        problems = []
        if self.parent_id == self.topic_id:
            problems.append("a topic is not its own parent")
        if not self.label.strip():
            problems.append("label must not be empty")
        return problems


@event("topic.split", "topic_id")
class TopicSplit(Payload):
    """A topic retires into two or more new topics (status split_into, redirecting to `redirect_to`, one of the new
    ones). `new_topics` are objects with `topic_id`, `label` and `anchor_id`; `formation_overlap` is how much of the
    old topic each part kept, used to make merging back harder."""

    topic_id: str
    new_topics: list[dict]
    redirect_to: str
    formation_overlap: float
    reason: str

    def check(self):
        problems = []
        ids = []
        if len(self.new_topics) < 2:
            problems.append("a split makes at least two topics")
        for t in self.new_topics:
            for key in ("topic_id", "label", "anchor_id"):
                if not isinstance(t.get(key), str) or not t.get(key):
                    problems.append(f"each new topic has a {key}")
            ids.append(t.get("topic_id"))
        if self.redirect_to not in ids:
            problems.append("redirect_to is one of the new topics")
        if not 0 <= self.formation_overlap <= 1:
            problems.append("formation_overlap is between 0 and 1")
        return problems


@event("topic.branched", "topic_id", "old_parent_id")
class TopicBranched(Payload):
    """A sub-topic becomes a topic: its parent is cleared. IDs are kept, so the old address still works."""

    topic_id: str
    old_parent_id: str
    reason: str


@event("topic.merged", "from_topic_id", "into_topic_id")
class TopicMerged(Payload):
    """Two topics say the same: `from_topic_id` retires (status merged_into, redirecting to `into_topic_id`)."""

    from_topic_id: str
    into_topic_id: str
    reason: str

    def check(self):
        return ["a topic is not merged into itself"] if self.from_topic_id == self.into_topic_id else []


@event("topic.folded_back", "topic_id", "into_parent_id")
class TopicFoldedBack(Payload):
    """A thinned sub-topic returns to its parent (status folded_into); its ideas are unchanged and now sit in the
    parent."""

    topic_id: str
    into_parent_id: str
    reason: str


@event("topic.renamed", "topic_id")
class TopicRenamed(Payload):
    """A new label in your words. `label_fixed` is true when you set it, so no model changes it again."""

    topic_id: str
    old_label: str
    label: str
    label_fixed: bool
    reason: str


@event("topic.dormant", "topic_id")
class TopicDormant(Payload):
    """No activity for 21 days (start): the topic is shown folded and nothing moves. `to_status` active wakes it."""

    topic_id: str
    to_status: _literal(("dormant", "active"))
    reason: str


@event("idea.placed", "item_id", "topic_id")
class IdeaPlaced(Payload):
    """An idea gets a place in a topic (§2.8, §5.6). Placing an item that already has this place settles it: the
    same event with `tentative` false makes a tentative placement final. Every idea has one home and up to two
    'also_in' places. `reasons` are the top two placement signals, in words."""

    placement_id: str
    item_id: str
    topic_id: str
    role: _literal(PLACEMENT_ROLES)
    tentative: bool
    reasons: list[str]

    def check(self):
        return ["give the top two placement signals at most"] if len(self.reasons) > 2 else []


@event("idea.moved", "item_id", "from_topic_id", "to_topic_id")
class IdeaMoved(Payload):
    """An idea moves between topics (your 'move' correction, or the weekly run). High tier. The moved place keeps
    its role; a move of the home place makes `to_topic_id` home."""

    item_id: str
    from_topic_id: str
    to_topic_id: str
    role: _literal(PLACEMENT_ROLES)
    tentative: bool
    reason: str

    def check(self):
        return ["an idea moves to a different topic"] if self.from_topic_id == self.to_topic_id else []


# Maintenance and privacy ------------------------------------------------------------------------------------------


@event("compensation.batch", "batch_id")
class CompensationBatch(Payload):
    """Marks a set of compensating events (rollback, §5.9): each of those carries `compensates`; this event groups
    them. `run_id_undone` is set when a whole run is undone."""

    batch_id: str
    reason: str
    compensated_event_ids: list[str]
    run_id_undone: str | None = None

    def check(self):
        return [] if self.compensated_event_ids else ["a batch compensates at least one event"]


@event("purge.applied", "purge_id", "item_ids")
class PurgeApplied(Payload):
    """Only you start a purge (§3.4). The listed items become 'purged' and leave a stub ("removed at your request
    on <date>"); their evidence quotes are scrubbed under purge_authorization. `item_ids` lists items only; other
    stores' parts of the purge are tracked by the purge saga, not by this event."""

    purge_id: str
    item_ids: list[str]
    requested_at: str


@event("scope.hold_changed", "scope_id")
class ScopeHoldChanged(Payload):
    """A scope is held (captured, never delivered or shown) or released. The scope row is created if it is new."""

    scope_id: Scope
    held: bool
    reason: str

    def check(self):
        return _scope_problem("scope_id", self.scope_id)


# --- the event envelope -------------------------------------------------------------------------------------------

SUPPORTED_SCHEMA_VERSIONS = {t: tuple(v for (tt, v) in PAYLOADS if tt == t) for t in EVENT_TYPES}
_ACTOR_RE = re.compile(r"^(user|code:\S+|model:\S+)$")
_INPUT_RE = re.compile(r"^[^@\s]+@[^@\s]+$")


@dataclass
class EventEnvelope:
    """One event as appended to memory.db (§2.3). A draft has no seq and an empty recorded_at; the gate sets them.

    `actor` is `user`, `code:<module>` or `model:<name>@<version>#<prompt hash>`. `inputs` are the objects the
    proposer read, as `object@version` strings. `config_version` names the starting-value files in force (I19).
    """

    type: str
    payload: dict
    actor: str
    config_version: str
    subjects: list[str] = field(default_factory=list)
    id: str = field(default_factory=new_id)
    schema_version: int = 1
    run_id: str | None = None
    proposal_id: str | None = None
    index_in_proposal: int | None = None
    inputs: list[str] = field(default_factory=list)
    compensates: str | None = None
    recorded_at: str = ""
    seq: int | None = None


class EventValidationError(ValueError):
    """An envelope the gate must reject (I15). `problems` lists every reason found."""

    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


def payload_class(type_: str, schema_version: int = 1) -> type[Payload] | None:
    return PAYLOADS.get((type_, schema_version))


def to_dict(envelope: EventEnvelope) -> dict:
    return asdict(envelope)


def from_dict(data: Mapping[str, Any]) -> EventEnvelope:
    known = {f.name for f in fields(EventEnvelope)}
    extra = set(data) - known
    if extra:
        raise EventValidationError([f"unknown envelope field {k!r}" for k in sorted(extra)])
    return EventEnvelope(**dict(data))


def to_json(envelope: EventEnvelope) -> str:
    """Canonical JSON: sorted keys, no spaces, so the same event always has the same text."""
    return json.dumps(to_dict(envelope), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def from_json(text: str) -> EventEnvelope:
    data = json.loads(text)
    if not isinstance(data, dict):
        raise EventValidationError(["an event is a JSON object"])
    return from_dict(data)


def make_event(
    type_: str,
    payload: Payload | Mapping[str, Any],
    *,
    actor: str,
    config_version: str,
    subjects: list[str] | None = None,
    **envelope_fields: Any,
) -> EventEnvelope:
    """Build a draft envelope from a payload dataclass or dict. Subjects default from the payload's subject fields.

    The payload dict holds every field, defaults filled in, so a stored event does not depend on later default changes.
    Does not validate: call `validate(envelope, draft=True)`.
    """
    cls = payload_class(type_, envelope_fields.get("schema_version", 1))
    if isinstance(payload, Payload):
        body, instance = asdict(payload), payload
    else:
        body = dict(payload)
        instance = cls(**body) if cls else None
        if instance is not None:
            body = asdict(instance)
    if subjects is None:
        subjects = instance.subjects() if instance is not None else []
    return EventEnvelope(type=type_, payload=body, actor=actor, config_version=config_version, subjects=subjects, **envelope_fields)


# --- validation (I15) ---------------------------------------------------------------------------------------------

_NONE = type(None)


def _type_problems(value: Any, hint: Any, path: str) -> list[str]:
    if hint is Any:
        return []
    origin = get_origin(hint)
    if origin is Literal:
        ok = any(value == a and type(value) is type(a) for a in get_args(hint))
        return [] if ok else [f"{path}: {value!r} is not one of {list(get_args(hint))}"]
    if origin in (Union, types.UnionType):
        options = get_args(hint)
        if any(not _type_problems(value, o, path) for o in options):
            return []
        names = " or ".join("null" if o is _NONE else getattr(o, "__name__", str(o)) for o in options)
        return [f"{path}: expected {names}, got {type(value).__name__}"]
    if hint is _NONE:
        return [] if value is None else [f"{path}: expected null"]
    if origin is list or hint is list:
        if not isinstance(value, list):
            return [f"{path}: expected a list, got {type(value).__name__}"]
        args = get_args(hint)
        out: list[str] = []
        if args:
            for i, v in enumerate(value):
                out += _type_problems(v, args[0], f"{path}[{i}]")
        return out
    if origin is dict or hint is dict:
        return [] if isinstance(value, dict) else [f"{path}: expected an object, got {type(value).__name__}"]
    if hint is bool:
        return [] if isinstance(value, bool) else [f"{path}: expected a boolean, got {type(value).__name__}"]
    if hint is int:
        return [] if isinstance(value, int) and not isinstance(value, bool) else [f"{path}: expected an integer, got {type(value).__name__}"]
    if hint is float:
        ok = isinstance(value, (int, float)) and not isinstance(value, bool)
        return [] if ok else [f"{path}: expected a number, got {type(value).__name__}"]
    if hint is str:
        return [] if isinstance(value, str) else [f"{path}: expected a string, got {type(value).__name__}"]
    return []


def payload_problems(cls: type[Payload], data: Any, *, draft: bool) -> list[str]:
    """Problems with a payload dict against a schema class. In a draft, stamped fields must be absent or null (I3)."""
    if not isinstance(data, dict):
        return ["payload must be an object"]
    spec = {f.name: f for f in fields(cls)}  # type: ignore[arg-type]
    hints = get_type_hints(cls)
    problems = [f"unknown field {key!r}" for key in data if key not in spec]
    for name, f in spec.items():
        if name not in data:
            if f.default is MISSING and f.default_factory is MISSING:
                problems.append(f"missing field {name!r}")
            continue
        problems += _type_problems(data[name], hints[name], name)
    if problems:
        return problems
    for name in cls.STAMPED:
        value = data.get(name)
        if draft and value is not None:
            problems.append(f"I3: {name} comes from capture, not from a proposal")
        if not draft and value is None and name in cls.STAMPED_REQUIRED:
            problems.append(f"{name} must be stamped from capture before the event is appended")
    if problems:
        return problems
    return cls(**data).check()


def problems(envelope: EventEnvelope, *, draft: bool = False) -> list[str]:
    """Every reason the envelope is invalid, or an empty list. `draft=True` is a proposal's unstamped op."""
    out: list[str] = []
    if not isinstance(envelope.type, str) or envelope.type not in EVENT_TYPES:
        return [f"unknown event type {envelope.type!r}"]
    if not isinstance(envelope.schema_version, int) or isinstance(envelope.schema_version, bool):
        return ["schema_version must be an integer"]
    cls = payload_class(envelope.type, envelope.schema_version)
    if cls is None:
        out.append(
            f"I15: {envelope.type} has no schema version {envelope.schema_version}"
            f" (supported: {list(SUPPORTED_SCHEMA_VERSIONS[envelope.type])})"
        )
    else:
        out += [f"payload: {p}" for p in payload_problems(cls, envelope.payload, draft=draft)]
    if not is_ulid(envelope.id):
        out.append("id must be a ULID")
    if not isinstance(envelope.actor, str) or not _ACTOR_RE.match(envelope.actor):
        out.append("actor must be 'user', 'code:<module>' or 'model:<name>@<version>#<prompt hash>'")
    if not isinstance(envelope.config_version, str) or not envelope.config_version:
        out.append("config_version must be a non-empty string")
    if not isinstance(envelope.subjects, list) or not envelope.subjects or not all(isinstance(s, str) and s for s in envelope.subjects):
        out.append("subjects must be a non-empty list of ids")
    if not isinstance(envelope.inputs, list) or not all(isinstance(i, str) and _INPUT_RE.match(i) for i in envelope.inputs):
        out.append("inputs must be a list of object@version strings")
    if (envelope.proposal_id is None) != (envelope.index_in_proposal is None):
        out.append("proposal_id and index_in_proposal come together (I14)")
    if envelope.proposal_id is not None and not envelope.run_id:
        out.append("an event in a proposal names its run_id (I14)")
    if envelope.index_in_proposal is not None and (not isinstance(envelope.index_in_proposal, int) or envelope.index_in_proposal < 0):
        out.append("index_in_proposal must be an integer from 0")
    if envelope.compensates is not None and not is_ulid(envelope.compensates):
        out.append("compensates must be the ULID of the event it undoes")
    if draft:
        if envelope.seq is not None:
            out.append("a draft has no seq")
    elif not envelope.recorded_at:
        out.append("recorded_at must be set once the gate stamps the event")
    return out


def validate(envelope: EventEnvelope, *, draft: bool = False) -> EventEnvelope:
    """Raise EventValidationError unless the envelope is valid (I15); return it otherwise.

    `draft=True` for a proposal's ops: stamped fields must be unset and recorded_at may be empty.
    The default is the stamped event the gate is about to append (seq is assigned on append).
    """
    found = problems(envelope, draft=draft)
    if found:
        raise EventValidationError(found)
    return envelope


# --- risk tiers (§5.9) --------------------------------------------------------------------------------------------

# Change type -> tier, from §5.9's table. Low: code checks, sampled in the nightly audit. Medium: plus one check by
# the other family. High: plus a full-effort check, audited the next night; a disagreement undoes the change.
RISK_TIER: dict[str, str] = {
    # low
    "evidence": "low",
    "refresh": "low",
    "value_kept": "low",
    "placement": "low",  # placement in an existing topic, tentative or not
    "work_label": "low",
    "stance": "low",
    "link_construction": "low",  # advances and used_in made by code
    "link_decision": "low",  # your confirm, reject, or a retraction
    "goal_status": "low",
    "question_status": "low",
    "correction": "low",  # your own one-step marks
    "scope_hold": "low",
    # medium
    "new_item": "medium",  # a new item from your move, a goal or a question
    "adoption": "medium",
    "link_supports": "medium",
    "link_refines": "medium",
    "link_answers": "medium",
    "link_inferred": "medium",  # advances or used_in inferred by a model
    "adopted_claim_check": "medium",
    "style": "medium",
    # high
    "supersede": "high",
    "retire": "high",  # an item retracted or quarantined
    "merge": "high",
    "conflict_opened": "high",
    "conflict_resolved": "high",
    "scope_widened": "high",
    "broader_idea": "high",
    "topic_change": "high",  # any topic event, and idea.moved
    "claim_contradicted": "high",
    "rollback": "high",
    "purge": "high",
}

_EVENT_CHANGE_TYPE = {
    "evidence.anchored": "evidence",
    "item.created": "new_item",
    "item.value_changed": "value_kept",
    "item.scope_widened": "scope_widened",
    "item.status_changed": "retire",
    "stance.recorded": "stance",
    "link.confirmed": "link_decision",
    "link.rejected": "link_decision",
    "link.retracted": "link_decision",
    "supersession.applied": "supersede",
    "supersession.undone": "rollback",
    "conflict.opened": "conflict_opened",
    "conflict.resolved": "conflict_resolved",
    "conflict.reopened": "conflict_opened",
    "conflict.undone": "rollback",
    "goal.created": "new_item",
    "goal.status_changed": "goal_status",
    "goal.confirmed": "goal_status",
    "question.created": "new_item",
    "question.status_changed": "question_status",
    "work.registered": "work_label",
    "work.labelled": "work_label",
    "style.recorded": "style",
    "style.revised": "style",
    "correction.applied": "correction",
    "correction.lifted": "correction",
    "topic.created": "topic_change",
    "topic.split": "topic_change",
    "topic.branched": "topic_change",
    "topic.merged": "topic_change",
    "topic.folded_back": "topic_change",
    "topic.renamed": "topic_change",
    "topic.dormant": "topic_change",
    "idea.placed": "placement",
    "idea.moved": "topic_change",
    "compensation.batch": "rollback",
    "purge.applied": "purge",
    "scope.hold_changed": "scope_hold",
}
_LINK_CHANGE_TYPE = {
    "supports": "link_supports",
    "refines": "link_refines",
    "answers": "link_answers",
    "conflicts": "conflict_opened",
    "case_of": "broader_idea",
    "same_as": "merge",
}


def change_type(envelope: EventEnvelope) -> str:
    """The change type of an event, the key into RISK_TIER. Falls back to the stricter reading when unsure."""
    t, p = envelope.type, envelope.payload
    if t == "item.revised":
        return "refresh" if p.get("reason") == "refresh" else "new_item"
    if t == "item.checked":
        return "claim_contradicted" if p.get("check_status") == "contradicted" else "adopted_claim_check"
    if t == "stance.recorded" and p.get("stance") == "adopted":
        return "adoption"
    if t in ("link.proposed", "link.applied"):
        lt = p.get("link_type")
        if lt in ("advances", "used_in"):
            return "link_construction" if p.get("stated_by") == "construction" else "link_inferred"
        return _LINK_CHANGE_TYPE.get(lt, "merge")
    if t not in _EVENT_CHANGE_TYPE:
        raise ValueError(f"unknown event type {t!r}")
    return _EVENT_CHANGE_TYPE[t]


# A purge or a rollback you start yourself is your word, not a model's change: no other family can check it (§3.4, §5.9).
# One a model proposes keeps the high tier of its change type, and I5 and I21 refuse it at the gate.
YOUR_OWN_COMMANDS = ("purge.applied", "compensation.batch")


def risk_tier(envelope: EventEnvelope) -> str:
    if envelope.type in YOUR_OWN_COMMANDS and envelope.actor == "user":
        return "low"
    return RISK_TIER[change_type(envelope)]


def max_tier(tiers: list[str]) -> str:
    """The highest tier in a list; a proposal takes the tier of its riskiest op. An empty list is low."""
    return max(tiers, key=RISK_TIERS.index, default="low")
