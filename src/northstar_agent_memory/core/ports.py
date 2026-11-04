"""The seven ports of MEMORY-ARCHITECTURE §3.2, and the records that cross them.

Every component reaches storage through a port. There is a SQLite adapter now and a Postgres adapter later, with
one contract test suite for both (§3.2). Reads return rows as dicts whose keys are the column names of the schema
files; writes take explicit arguments. Nothing here calls a model.

The protocols list every method a caller outside the adapter may use, reads included, so an adapter that matches its
protocol (test_contract checks the names and the parameters) can be swapped for another (§3.2).

Rules that hold for every adapter:
- Each store has one writer. The write gate is the only caller of `MemoryWriter` (§3.2).
- Every method takes and stores `tenant_id` 'local' unless an adapter is built for another tenant (§3.3).
- A write method is atomic: it commits all of its rows or none (db.transaction).
- Reading never changes a store.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Any, Iterable, Literal, Protocol, Sequence, runtime_checkable

from northstar_agent_memory.core.events import EventEnvelope, max_tier, risk_tier
from northstar_agent_memory.core.ids import new_id
from northstar_agent_memory.transcript import Message, Source

Tier = Literal["low", "medium", "high"]
Row = dict[str, Any]

# --- records shared by the builders ------------------------------------------------------------------------------


@dataclass(slots=True)
class EvidenceQuote:
    """An exact quote the proposer relies on, with its place in chat history. The gate checks it (I1, I2)."""

    message_id: str
    start_char: int
    end_char: int
    quote: str


@dataclass(slots=True)
class Verdict:
    """One check of a proposal (§5.9). `rules` lists what was checked: meaning both ways, attribution, scope, hedge.

    `independent` is False when no other model family was left to check, and the result is then labelled
    "not independent" (DESIGN §1.2); the change still applies, with the label recorded. `checker_family` is 'code'
    for the gate's own code checks. A verdict counts for the gate only as the run store recorded it: it names the
    recorded model call that made it (`model_call_id`), and the family it states is that call's family (§5.9).
    What a proposal carries in `Proposal.verdicts` is a claim; `RunStore.verdicts_for` is the record.
    """

    checker_family: str
    rules: list[str]
    outcome: Literal["pass", "fail"]
    independent: bool
    model_call_id: str | None = None
    notes: str = ""
    id: str = field(default_factory=new_id)

    @property
    def passed(self) -> bool:
        return self.outcome == "pass"


@dataclass(slots=True)
class Proposal:
    """What a stage hands the write gate: events to append in one transaction, with their evidence and checks.

    `ops` are unstamped drafts (`validate(op, draft=True)` passes): each carries this run_id, this proposal_id and
    its own index_in_proposal, so applying the proposal twice changes nothing (I14). `inputs` are the
    `object@version` strings the proposer read; the gate re-queues the proposal if any has changed (§5.9 step 2).
    `risk_tier` is that of the riskiest op; `verdicts` are the checks already done, as the proposer says. The gate
    trusts none of it: it works out the tier from the ops and, with a run store, reads the verdicts from there.
    """

    run_id: str
    proposal_id: str
    ops: list[EventEnvelope]
    evidence: list[EvidenceQuote] = field(default_factory=list)
    inputs: list[str] = field(default_factory=list)
    abstentions: list[str] = field(default_factory=list)  # moves the proposer declined to record, with a reason
    risk_tier: Tier = "low"
    verdicts: list[Verdict] = field(default_factory=list)

    @classmethod
    def build(
        cls,
        run_id: str,
        ops: Sequence[EventEnvelope],
        *,
        proposal_id: str | None = None,
        evidence: Sequence[EvidenceQuote] = (),
        inputs: Sequence[str] = (),
        abstentions: Sequence[str] = (),
    ) -> "Proposal":
        """Number the ops, set their run and proposal, and take the riskiest op's tier."""
        pid = proposal_id or new_id()
        drafts = list(ops)
        for index, op in enumerate(drafts):
            op.run_id, op.proposal_id, op.index_in_proposal = run_id, pid, index
            if not op.inputs:
                op.inputs = list(inputs)
        tier = max_tier([risk_tier(op) for op in drafts])
        return cls(run_id, pid, drafts, list(evidence), list(inputs), list(abstentions), tier)  # type: ignore[arg-type]


@dataclass(slots=True)
class Rejection:
    """One reason the gate refused a proposal. `invariant` is 'I2' and so on (a cap is I13, a rollback of your marks
    I21), or the gate step that refused it: 'authority', 'fencing', 'freshness', 'freeze', 'verification', 'projection'."""

    invariant: str
    reason: str
    op_index: int | None = None  # which op, when one op is to blame


@dataclass(slots=True)
class ApplyResult:
    """The outcome of MemoryWriter.apply.

    status 'applied': `applied_seqs` are the new events' seqs, in op order.
    status 'duplicate': the proposal was applied before (I14); `applied_seqs` are the seqs it got then.
    status 'requeued': an input changed since the proposer read it (freshness); nothing applied and nothing failed.
    status 'held': the run is held for a second check (loss bound); nothing applied.
    status 'rejected': `rejections` say why; nothing applied.
    """

    status: Literal["applied", "duplicate", "requeued", "held", "rejected"]
    applied_seqs: list[int] = field(default_factory=list)
    rejections: list[Rejection] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status in ("applied", "duplicate")


@runtime_checkable
class Projector(Protocol):
    """Writes current-state rows and row history for events that are already validated and appended.

    `apply` is called by the gate inside its transaction on memory.db, after the events are inserted (so each has
    its `seq`), in seq order. It must be deterministic, read nothing but `conn`, make no model call, and archive a
    row with `db.archive_row` before it changes or deletes it. Replaying the log through a projector on empty
    tables must give the same rows (I18).
    """

    def apply(self, conn: sqlite3.Connection, envelopes: Sequence[EventEnvelope]) -> None: ...


@dataclass(slots=True)
class Watermark:
    """How far capture has written: the last `message.seq` and `work_event.seq` (0 when empty)."""

    message_seq: int = 0
    work_event_seq: int = 0


@dataclass(slots=True)
class StoredMessage:
    """A message as stored in history.db: the neutral record plus what the store adds."""

    message: Message
    seq: int
    fidelity: Literal["verbatim", "model_reported", "reconciled"]
    content_hash: str


@dataclass(slots=True)
class WorkEvent:
    """Anything you got your hands on, as capture saw it (§2.2). `evidence`: strong when you authored, committed or
    decided; medium when an AI edited it in your session; weak when you only opened it."""

    id: str
    source_id: str
    kind: Literal["commit", "file_version", "render", "diagram", "decision_record"]
    ref: str
    evidence: Literal["strong", "medium", "weak"]
    snapshot_sha256: str | None = None
    occurred_at: str | None = None
    meta: dict = field(default_factory=dict)


@dataclass(slots=True)
class Subgraph:
    """Items and the links among them, a step or two out from some items."""

    items: dict[str, Row] = field(default_factory=dict)  # item id -> item row
    links: list[Row] = field(default_factory=list)  # link rows with both ends in `items`, or a work end


@dataclass(slots=True)
class SearchQuery:
    """One search for every way in (§4.2). `direction` sets the rules: 'push' is what Northstar may put in a chat
    (active, facts only, scope must cover this chat); 'pull' is what your AI may ask for (every scope you allowed,
    facts and views). The index never uses who said it or which product (I23)."""

    text: str
    direction: Literal["push", "pull"] = "push"
    project: str | None = None  # the chat's project: its scope is project:<project>
    thread_id: str | None = None  # the routed work thread, for the links list (L1)
    goal_ids: list[str] = field(default_factory=list)
    allowed_scopes: list[str] | None = None  # pull: scopes you allowed; None means every scope that is not held
    exclude_item_ids: list[str] = field(default_factory=list)  # already given in this chat (receipts)
    time_query: bool = False  # turn on the time list (L4)
    top_n: int = 12
    as_of_seq: int | None = None  # pull: earlier versions, when the AI asks how something changed


@dataclass(slots=True)
class SearchHit:
    """One result: the item version, its rendered line and which of the lists found it (links, words, meaning, time)."""

    item_id: str
    version: int
    line_text: str
    score: float  # the fused score
    found_by: list[Literal["links", "words", "meaning", "time"]]
    scope: str
    kind: str


@dataclass(slots=True)
class Job:
    """A leased unit of maintenance work (§2.12)."""

    id: str
    run_id: str
    stage: Literal["trigger", "replay", "extract", "integrate", "refresh", "check", "weekly", "rebuild", "log"]
    idempotency_key: str
    payload: dict
    attempts: int
    lease_owner: str
    lease_until: str


@dataclass(slots=True)
class ModelCall:
    """A recorded model call (§2.12). `input_ids` name what went in; the assembled prompt is never stored.
    The raw output is recorded before anyone reads it, and a call is never regenerated (§5.12)."""

    provider: str
    model: str
    family: str
    prompt_hash: str
    input_ids: list[str]
    run_id: str | None = None
    job_id: str | None = None
    raw_output: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost: float | None = None
    status: Literal["ok", "error", "timeout"] = "ok"
    id: str = field(default_factory=new_id)
    called_at: str = ""  # set on record


# --- the seven ports (§3.2) -------------------------------------------------------------------------------------


@runtime_checkable
class HistoryStore(Protocol):
    """history.db and blobs/. Writer: capture. Append-only (I6); idempotent by id, so a replayed capture adds nothing."""

    def add_source(self, source: Source, *, scope: str, sensitivity: str = "normal", account: str | None = None) -> bool:
        """Store a source's own fields (not its messages). `scope` is personal, project:<id>, work:<org> or session:<id>.
        Returns False if the id exists. Messages are added with append_message."""

    def append_message(self, message: Message, *, fidelity: str = "verbatim") -> bool:
        """Append one turn word for word, with content_hash set by the store. Returns False if the id exists.
        Speaker and origin are stored as given by capture's role map (I3, I20)."""

    def append_messages(self, messages: Iterable[Message], *, fidelity: str = "verbatim") -> int:
        """Append several messages in one transaction and return how many were new. One conflict refuses all."""

    def append_work_event(self, event: WorkEvent) -> bool:
        """Append a work event. Returns False if the id exists."""

    def put_blob(self, data: bytes, media_type: str | None = None) -> str:
        """Store a snapshot under blobs/ named by its content hash and return the sha256. Idempotent."""

    def get_blob(self, sha256: str) -> bytes | None: ...

    def record_reconciliation(
        self,
        reported_message_id: str,
        verbatim_message_id: str | None,
        method: Literal["hash", "tag", "fuzzy", "none"],
        score: float | None,
        outcome: Literal["matched", "reported_only", "could_not_confirm"],
    ) -> str:
        """Record the outcome of matching a model-reported turn to word-for-word text (§2.2); every outcome is kept."""

    def get_source(self, source_id: str) -> Source | None:
        """The source with its messages in (branch, ordinal) order."""

    def get_message(self, message_id: str) -> StoredMessage | None: ...

    def messages_for_source(self, source_id: str) -> list[StoredMessage]:
        """A source's messages in (branch, ordinal) order."""

    def messages_since(self, seq: int, limit: int = 1000) -> list[StoredMessage]:
        """Messages with message.seq greater than `seq`, in seq order: the maintenance run's replay."""

    def watermark(self) -> Watermark: ...

    def authorize_purge(self, purge_id: str, targets: Sequence[tuple[str, str]]) -> None:
        """Record (target table, target id) pairs a purge will remove, before removing anything (§3.4)."""

    def purge_authorized(self, purge_id: str) -> int:
        """Delete every row (and blob file) this purge authorized. Returns the number of rows deleted."""


@runtime_checkable
class SourceInfoReader(Protocol):
    """The part of a history store the write gate reads for the kind and scope of a source (I24, scope checks).

    `get_source_info` returns the source's stored row (at least `kind` and `scope`), or None if the source is
    unknown. It is a protocol of its own so a history adapter can add it without changing `HistoryStore`.
    """

    def get_source_info(self, source_id: str) -> Row | None: ...


@runtime_checkable
class MemoryWriter(Protocol):
    """memory.db's one writer, called only by the write gate (§3.2, §5.9).

    `apply` is the door for automated proposers: it never takes the proposal's word for who acted, for its risk
    tier or for its verdicts (principle 4). Your own marks come through the gate's `apply_user(proposal, authority)`,
    where `authority` is a `UserAuthority` that only capture, the UI and the CLI construct.
    """

    def apply(self, proposal: Proposal) -> ApplyResult:
        """Check the proposal in the gate's order (fencing, freshness, freezes, code checks, the verification its tier
        needs), then append its events, stamp them, project them and commit in one transaction. Applying the same
        run_id, proposal_id and indexes again returns status 'duplicate' and changes nothing (I14)."""

    def apply_user(self, proposal: Proposal, authority: Any) -> ApplyResult:
        """Check and apply ops that are yours (your marks, and the changes they make) on the `UserAuthority` that your
        capture, overview or command line constructed for the act (core.gate.UserAuthority). No model verdict is
        needed, and caps and freezes do not apply; the code checks all do. Without a real `UserAuthority` the result
        is status 'rejected' (step 'authority')."""


@runtime_checkable
class MemoryReader(Protocol):
    """Read-only views of memory.db. `as_of_seq` and `as_of` give a past state from row history (§2.3)."""

    def watermark(self) -> int:
        """The highest event seq, or 0."""

    def seq_at(self, as_of: str) -> int:
        """The highest event seq recorded at or before an ISO 8601 time, or 0."""

    def get(self, kind: str, row_id: str, as_of: int | str | None = None) -> Row | None:
        """One row of any current-state kind (item, evidence, link, supersession, conflict, work, style_line,
        correction, scope, topic, placement, stance), now or as of a seq (int) or an ISO 8601 time (str)."""

    def get_item(self, item_id: str, *, as_of_seq: int | None = None, as_of: str | None = None) -> Row | None:
        """The item row now, or as it stood at that seq or time. Not both `as_of_seq` and `as_of`."""

    def get_item_version(self, item_id: str, version: int) -> Row | None:
        """A specific version, current or from history (supersession keeps the old version readable)."""

    def item_versions(self, item_id: str) -> list[Row]:
        """Every version, oldest first, each as its last stored state."""

    def evidence_for(self, subject_id: str) -> list[Row]:
        """Evidence rows citing an item, style line or correction."""

    def changed_since(self, seq: int) -> list[str]:
        """Ids of items touched by events after `seq` (as event subjects), for incremental rebuilds."""

    def subgraph(self, item_ids: Sequence[str], depth: int = 1, *, statuses: Sequence[str] = ("applied", "confirmed")) -> Subgraph:
        """The items, and links of the given statuses, up to `depth` steps out."""

    def events_since(self, seq: int, limit: int = 1000, types: Sequence[str] | None = None) -> list[EventEnvelope]:
        """Events after `seq` in seq order, as stored (stamped, with seq)."""

    def get_event(self, event_id: str) -> EventEnvelope | None: ...


@runtime_checkable
class WorkingStore(Protocol):
    """working.db: pieces of work in progress (§2.9). Writer: the live writer. Never a source for memory."""

    def open_thread(
        self,
        title: str,
        *,
        scope: str,
        project: str | None = None,
        goal_text: str | None = None,
        goal_message_id: str | None = None,
        goal_basis: Literal["stated", "reused"] | None = None,
        thread_id: str | None = None,
    ) -> str:
        """Create an active thread and return its id."""

    def get_thread(self, thread_id: str) -> Row | None: ...

    def threads(self, *, project: str | None = None, status: str | None = None) -> list[Row]: ...

    def set_thread_status(self, thread_id: str, status: Literal["active", "paused", "closed"]) -> None: ...

    def touch_thread(self, thread_id: str, at: str) -> None:
        """Set last_active."""

    def start_session(
        self, session_id: str, *, app: str | None, project: str | None, thread_id: str | None = None, started_at: str
    ) -> None: ...

    def attach_session(self, session_id: str, thread_id: str) -> None: ...

    def set_context_used(self, session_id: str, tokens: int) -> None: ...

    def record_version(
        self,
        thread_id: str,
        artifact: str,
        *,
        artifact_kind: Literal["git_ref", "render", "file"] = "git_ref",
        parent_id: str | None = None,
        made_at_turn: int | None = None,
    ) -> str:
        """Record a version of the work and return its id."""

    def add_feedback(self, version_id: str, your_quote: str, message_id: str) -> str:
        """Attach your next message to a version as feedback."""

    def set_best(self, thread_id: str, version_id: str) -> None:
        """Make this the thread's one best version (your pick, or your last approval in your own words)."""

    def versions(self, thread_id: str) -> list[Row]:
        """Versions oldest first, each with a `feedback` list of {your_quote, message_id}."""

    def best_version(self, thread_id: str) -> Row | None: ...

    def add_live_decision(
        self, thread_id: str, kind: Literal["decided", "ruled_out", "constraint"], line: str, your_quote: str, message_id: str
    ) -> str:
        """Note a decision from one of your own turns."""

    def live_decisions(self, thread_id: str, status: str | None = "live") -> list[Row]: ...

    def set_decision_status(self, decision_id: str, status: Literal["live", "in_memory", "dropped"]) -> None: ...

    def add_side_topic(self, thread_id: str, line: str, opened_at_message: str | None = None) -> str: ...

    def set_side_topic_status(self, side_topic_id: str, status: Literal["open", "split_off", "closed"]) -> None: ...

    def side_topics(self, thread_id: str, status: str | None = "open") -> list[Row]: ...

    def record_receipt(
        self, session_id: str, kind: Literal["start_note", "facts", "refill", "focus_note", "recall"],
        items: Sequence[str], text_hash: str, fingerprints: Sequence[str], at: str | None = None,
    ) -> str:
        """Note what Northstar gave an AI: item@version strings, the text hash and its 8-word fingerprints."""

    def receipts(self, session_id: str | None = None, *, since: str | None = None) -> list[Row]: ...

    def delivered_fingerprints(self, session_id: str) -> set[str]:
        """Every fingerprint Northstar delivered into one session, for the echo check (I11)."""


@runtime_checkable
class IndexPort(Protocol):
    """index.db: the AI index (§2.10). Written by the maintenance rebuild; read by delivery and recall."""

    def search(self, query: SearchQuery) -> list[SearchHit]:
        """Fuse the four lists by reciprocal rank (constant 60), filter by status, scope and class for the query's
        direction, drop near-duplicates, and return the top N (§4.2)."""

    def goal_card(self, card_id: str) -> Row | None: ...

    def goal_cards(self, *, project: str | None = None) -> list[Row]:
        """Cards of active goals and threads, for routing (§4.3)."""

    def start_note(self, thread_id: str) -> Row | None:
        """The built start note: text, items, built_at, watermark."""

    def record_use(self, item_id: str, kind: Literal["delivered", "recalled", "viewed", "built_on"], context: str, at: str | None = None) -> None: ...

    def use_summary(self, item_id: str) -> Row | None: ...

    def gate_bar(self, project: str) -> float | None:
        """The project's current bar, or None if it has none yet."""

    def move_gate_bar(
        self, project: str, direction: Literal["lower", "raise"], reason: Literal["re_explanation", "presumption", "leak"],
        *, step: float, floor: float, ref: str | None = None,
    ) -> float:
        """Move the bar one step, never below `floor`; log the move; return the new bar."""


@runtime_checkable
class OverviewStore(Protocol):
    """overview.db: the human structure (§2.11). Rebuilt each run, except layout and marks."""

    def topics(self, *, parent_id: str | None = None) -> list[Row]:
        """Topic views (top level when parent_id is None)."""

    def topic_view(self, topic_id: str) -> Row | None: ...

    def idea_view(self, item_id: str) -> Row | None: ...

    def open_items(self, *, topic_id: str | None = None) -> list[Row]: ...

    def left_off(self, thread_id: str) -> Row | None: ...

    def suggestions(self, status: str = "waiting") -> list[Row]:
        """Links Northstar found, waiting for your confirmation (I27)."""

    def layout(self) -> list[Row]: ...

    def set_layout(self, nodes: Sequence[Row], seed: int) -> None:
        """Replace positions; each node's previous position becomes prev_x, prev_y."""

    def mark_seen(self, item_id: str, version: int, at: str | None = None) -> None: ...

    def set_pinned(self, item_id: str, pinned: bool) -> None: ...

    def record_hidden_open(self, topic_id: str, at: str | None = None) -> None:
        """You opened a topic's hidden entries; this feeds the split bar (§5.8)."""


@runtime_checkable
class RunStore(Protocol):
    """runs.db: maintenance run records (§2.12). Writer: maintenance.

    The gate reads it for fencing (`get_run`, `runs`), freezes (`is_frozen`), the model call behind a stage's work
    (`recorded_call`, `get_call`), the stored proposal and the verdicts that count (`get_proposal`, `verdicts_for`;
    `verdicts` is the same record as rows).
    """

    def start_run(self, trigger: Literal["idle", "nightly", "weekly", "manual"], watermark_from: int = 0) -> str: ...

    def get_run(self, run_id: str) -> Row | None: ...

    def runs(self, state: str | None = None) -> list[Row]:
        """Runs, newest first."""

    def finish_run(
        self, run_id: str, state: Literal["applied", "held", "failed", "cancelled", "undone"], *,
        watermark_to: int | None = None, result: dict | None = None, safety_copy: str | None = None,
    ) -> None: ...

    def enqueue(self, run_id: str, stage: str, idempotency_key: str, payload: dict | None = None) -> str:
        """Add a job; the same idempotency_key returns the existing job's id and adds nothing."""

    def lease(self, owner: str, stages: Sequence[str], ttl_seconds: int, now: str | None = None) -> Job | None:
        """Lease the oldest queued job of those stages, or one whose lease expired, and add one attempt. A job that
        has had the configured number of attempts is quarantined instead of leased."""

    def jobs(self, run_id: str, state: str | None = None) -> list[Row]:
        """The jobs of a run, oldest first."""

    def mark_running(self, job_id: str, *, owner: str | None = None) -> None:
        """The leased job has begun: its state is 'running'."""

    def complete(self, job_id: str, *, owner: str | None = None) -> None: ...

    def fail(self, job_id: str, error: str, *, retry: bool, owner: str | None = None) -> str:
        """Requeue the job (retry), mark it failed, or, when a retry has no attempts left, quarantine it. Returns the
        new state."""

    def record_call(self, call: ModelCall) -> str:
        """Record a model call and return its id. Call before reading the output."""

    def get_call(self, call_id: str) -> Row | None: ...

    def calls_for_job(self, job_id: str) -> list[Row]:
        """Every call recorded under a job: when a proposal was saved with that job, these calls did its work."""

    def recorded_call(self, prompt_hash: str, run_id: str | None = None) -> Row | None:
        """The latest call that worked for this prompt hash (in this run, if given): reused, never regenerated."""

    def save_proposal(self, proposal: Proposal, *, job_id: str | None = None) -> None:
        """Store a proposal (ops, evidence, abstentions, inputs, tier) as pending, and its verdicts."""

    def get_proposal(self, proposal_id: str) -> Row | None:
        """The stored proposal as a row (ops, evidence, inputs, risk tier, state)."""

    def load_proposal(self, proposal_id: str) -> Proposal | None:
        """The stored proposal, with the verdicts recorded for it."""

    def record_verdict(self, proposal_id: str, verdict: Verdict) -> str:
        """Record a check. A verdict that names a model call must name a call of the proposal's run and of the family
        it states (else ValueError). `independent` False is the 'not independent' label."""

    def verdicts_for(self, proposal_id: str) -> list[Verdict]:
        """The verdicts recorded for a proposal, oldest first: what the gate counts, never `Proposal.verdicts`."""

    def verdicts(self, proposal_id: str) -> list[Row]:
        """The same verdicts as stored rows."""

    def set_proposal_state(self, proposal_id: str, state: Literal["applied", "rejected", "quarantined", "requeued"]) -> None: ...

    def quarantine(self, target_kind: Literal["proposal", "item", "link"], target_id: str, reason: str, deadline: str | None = None) -> str:
        """Set a failing target aside; a repeat for the same target adds an attempt, up to the configured number."""

    def get_quarantine(self, quarantine_id: str) -> Row | None: ...

    def exit_quarantine(self, quarantine_id: str, exit: Literal["fresh_call", "re_extracted", "discarded", "applied"]) -> None: ...

    def budget(self, change_type: str) -> Row | None:
        """The audited error rate and frozen flag of a change type."""

    def is_frozen(self, change_type: str) -> bool: ...

    def record_audit(
        self, change_type: str, *, n: int, errors: int, freeze_above: float | None = None, min_sample: int | None = None
    ) -> Row:
        """Add audited changes and errors; freeze the type when the rate passes `freeze_above` (§5.9), once at least
        `min_sample` changes were audited. Both default to the config. Returns the row."""

    def log_change(
        self, run_id: str, change_type: str, line: str, event_ids: Sequence[str], undo_handle: str | None = None
    ) -> str:
        """One plain line per change, with its undo. Never read back as an input (I7)."""

    def read_change_log(self, run_id: str | None = None) -> list[Row]:
        """The log in order, for you and for audits. Typed input assembly never calls it (I7)."""
