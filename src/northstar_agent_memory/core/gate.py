"""The write gate: the only writer of memory.db (MEMORY-ARCHITECTURE §3.2, §5.9, §5.12, invariants I1-I24 of §7).

Code decides and models propose (principle 4). A stage hands the gate a `Proposal`; `WriteGate.apply` checks it in
this order and appends its events in one transaction, or returns why not. The gate never trusts a claim a proposal
makes about itself (GOAL §4.7: maintenance stays correct even when an agent loses focus): who may act, which checks
passed, who said a quote and when, and which family said a claim are all found by code, from the stores below.

0. replay: a proposal applied before returns 'duplicate' and changes nothing (I14);
1. intake: every op matches its versioned schema, carries no stamped field, and carries this run's key (I3, I14, I15);
   and no op claims to be yours. The actor `user`, and every one of your marks (corrections, a purge, a confirmation),
   is refused here: they reach the gate only through `apply_user`, on a `UserAuthority` that your own capture,
   overview or command line constructs. Your own marks need no model verdict and are exempt from caps and freezes;
2. fencing: the proposal's run is the current run in runs.db (skipped when the gate has no run store, as in tests, and
   for your own marks);
3. freshness: every input `object@version`, and every state an op builds on, is still as the proposer read it. If
   not, the result is 'requeued': nothing failed;
4. freezes: a change type frozen by its error budget or a sentinel is refused;
5. code checks: the invariants (I1, I2, I3, I4, I5, I7, I12, I16, I17, I20, I21, I24, I11 in invariants.py, and the
   evidence behind a value moving to kept);
6. the verdicts the proposal's risk tier needs. With a run store the verdicts are the ones recorded for this proposal
   in runs.db, and `Proposal.verdicts` is ignored: a verdict counts only if it names a recorded model call of this
   run, of the family it states, that is not the work's own call, and the ops are those the verdicts judged. Low needs
   none, medium one passing check by a family other than the work's and the claim's, high a full-effort check likewise
   (§5.9). The claim's families are those of every AI evidence row of every item an op touches, stored or new. Where no
   other family is left a check is labelled 'not independent' and the change still applies, with the label recorded
   (§5.9, DESIGN §1.2). A merge also needs an exact key or two agreeing families (I12);
7. caps per run, and the loss bound: a run may retire 5% of active items (start), counting what a rollback removes.
   Above it the proposal is 'held' until a second check releases it (I13);
8. one transaction: stamp who said it from chat history (I3, I20), append the events with their run key (I14), and
   call the projector. The whole of `apply` runs in one write transaction, so the checks and the append see one state.
   If the store or the projector refuses the change, nothing is written and the result is 'rejected' ('projection').

The gate reads chat history, memory.db and runs.db and writes only memory.db. It records nothing in runs.db: the
stage that called it records the proposal's outcome there, and the result's `labels` say what to record with it.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import sqlite3
from dataclasses import dataclass, field
from typing import Any, Iterable, Literal, Mapping, Sequence

from northstar_agent_memory import config as _config
from northstar_agent_memory.core import events
from northstar_agent_memory.core.db import DEFAULT_TENANT, transaction
from northstar_agent_memory.core.events import EventEnvelope
from northstar_agent_memory.core.ids import utc_now
from northstar_agent_memory.core.invariants import (
    CODE_CHECKS, INTAKE, ITEM_CREATES, Context, HistoryRead, Limits, MemoryRead, Violation, check_i13, loss_bound, parse_input,
    run_checks,
)  # fmt: skip
from northstar_agent_memory.core.ports import ApplyResult, Projector, Proposal, Rejection, Verdict
from northstar_agent_memory.core.projector import ProjectionError

# What a full-effort check covers (§5.9; the rules a Verdict lists): meaning both ways, attribution, scope, hedge.
FULL_RULES = ("meaning_both_ways", "attribution", "scope", "hedge")
# A passing check that lists this rule releases a run held for going over its loss bound ("held for a second check").
LOSS_BOUND_RULE = "loss_bound_review"
# The label a check carries when no other family was left to make it independent (§5.9, DESIGN §1.2).
NOT_INDEPENDENT = "not_independent"

_TIERS = events.RISK_TIERS
# Recording that a claim has no check at all is low risk. 'not_independent' is a check result, not the lack of one: it
# needs a verdict that backs it like 'checked' does, so a proposal cannot dress an unchecked claim as checked.
_UNCHECKED = ("not_needed", "unchecked")

# Who may hand the gate your authority: your own capture (typed words), your overview (a click) and your command line.
USER_SURFACES = ("capture", "ui", "cli")


@dataclass(frozen=True, slots=True, kw_only=True)
class UserAuthority:
    """Proof that an op is yours, handed to `WriteGate.apply_user` and never read from a proposal.

    Only your own capture, overview and command line construct one, at the moment you type or click. A stage, a model
    or a proposal never does, and a lint test fails when any other module of the package builds one. `user_action`
    is the explicit flag: it must be True, and its only honest value is "this call is the direct result of something
    you just typed or clicked". Tests may construct one.
    """

    surface: Literal["capture", "ui", "cli"]
    user_action: bool

    def __post_init__(self) -> None:
        if self.user_action is not True:
            raise ValueError("a UserAuthority is only made for an act of yours: user_action=True")
        if self.surface not in USER_SURFACES:
            raise ValueError(f"surface must be one of {USER_SURFACES}, got {self.surface!r}")


@dataclass(slots=True)
class GateResult(ApplyResult):
    """What `apply` returns: an `ApplyResult`, and the labels the caller records in runs.db with the proposal's outcome.
    `labels` holds 'not_independent' when the change applied on a check that no other family could make independent."""

    labels: list[str] = field(default_factory=list)


def op_tier(op: EventEnvelope) -> str:
    """An op's risk tier (§5.9). An op of yours (the actor `user`, which only `apply_user` accepts) is your word, not a
    model's change, and needs no check by another family, whatever its type. Recording that a claim has no independent
    check is low; the rest is events.risk_tier."""
    if op.actor == "user":
        return "low"
    if op.type == "item.checked" and op.payload.get("check_status") in _UNCHECKED:
        return "low"
    return events.risk_tier(op)


def proposal_tier(ops: Sequence[EventEnvelope]) -> str:
    """The tier of the riskiest op. The proposal's own `risk_tier` is never trusted."""
    return events.max_tier([op_tier(op) for op in ops])


def _rejected(violations: Sequence[Violation]) -> ApplyResult:
    return ApplyResult("rejected", rejections=[Rejection(v.invariant, v.reason, v.op_index) for v in violations])


def _refused(step: str, reason: str, status: str = "rejected") -> ApplyResult:
    return ApplyResult(status, rejections=[Rejection(step, reason)])  # type: ignore[arg-type]


@dataclass(slots=True)
class _Work:
    """What the gate learned about the model calls behind a proposal's ops (their `model:...#<hash>` actors)."""

    families: set[str] = field(default_factory=set)  # families of the recorded calls
    unrecorded: list[str] = field(default_factory=list)  # actors whose call is not recorded: the family is unknown
    call_ids: set[str] = field(default_factory=set)  # the work's own calls: no verdict may name one
    hashes: set[str] = field(default_factory=set)  # and no verdict may name a call of the same prompt


@dataclass(slots=True)
class _Verdicts:
    """The verdicts that count for a proposal. `labelled` is the part of `counted` that is not independent."""

    counted: list[Verdict] = field(default_factory=list)
    labelled: list[Verdict] = field(default_factory=list)
    failed: list[Verdict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def independent(self) -> list[Verdict]:
        return [v for v in self.counted if v not in self.labelled]


class WriteGate:
    """`MemoryWriter` for memory.db.

    `memory` is a connection to memory.db, `history` a history store (anything with `get_message`; the SQLite store's
    connection also gives each source's kind, scope and project), `projector` writes the current-state rows. `runs` is
    a run store (`get_run`, `runs`, `is_frozen`, `recorded_call`, `get_call`, `get_proposal`, `verdicts`) and may be
    None, as in tests; without it there is no fencing and no freezes, the family that did the work is unknown, and the
    verdicts a `Proposal` carries are taken as they stand. `config` holds `[maintenance]` caps. `families` are the model
    families the checks may be routed to; when given, a check by the work's own family is accepted as 'not independent'
    only if no other family is left. When None, the families come from `[maintenance] check_families` in the config
    (your settings.toml narrows it to the families you have; a single-family user lists one). When that key is absent
    too, the label recorded in runs.db stands.
    """

    def __init__(
        self,
        memory: sqlite3.Connection,
        history: Any,
        projector: Projector,
        *,
        runs: Any = None,
        config: Mapping[str, Any] | None = None,
        clock=utc_now,
        tenant_id: str = DEFAULT_TENANT,
        families: Iterable[str] | None = None,
    ) -> None:
        self.memory = memory
        self.projector = projector
        self.runs = runs
        self.clock = clock
        self.tenant_id = tenant_id
        settings = _config.load() if config is None else config
        if families is None:  # the families a check may be routed to: [maintenance] check_families, which you may narrow
            families = settings.get("maintenance", {}).get("check_families")
        if isinstance(families, str):
            raise ValueError("[maintenance] check_families must be a list of family names")
        self.families = None if families is None else frozenset(families)
        self.limits = Limits.from_config(settings)
        self._read = MemoryRead(memory, tenant_id)
        self._history = history
        self._unrecorded: list[str] = []

    # --- the two calls ---

    def apply(self, proposal: Proposal) -> ApplyResult:
        """Check and apply a proposal from an automated stage. Nothing in it is yours: an op under the actor `user`, or
        one of your marks, is refused (use `apply_user`)."""
        return self._guarded(proposal, None)

    def apply_user(self, proposal: Proposal, authority: UserAuthority) -> ApplyResult:
        """Check and apply ops that are yours: your marks and the changes they make, under the actor `user`. Needs the
        `UserAuthority` that your capture, overview or command line made for the act (an op's actor is `user`, or the
        `code:` module acting on your click; either is recorded as `user`). The code checks all still hold
        (your typed words, exact quotes, a purge's request); no model verdict is needed, and caps and freezes, which
        stop automation, do not apply."""
        if not isinstance(authority, UserAuthority):
            return _refused("authority", "apply_user needs the UserAuthority that your own capture, overview or command line made")
        return self._guarded(proposal, authority)

    def _guarded(self, proposal: Proposal, authority: UserAuthority | None) -> ApplyResult:
        try:
            with transaction(self.memory):
                return self._apply(proposal, authority)
        except (sqlite3.IntegrityError, ProjectionError) as err:  # the store or the projector refused it; nothing was written
            return _refused("projection", f"the change could not be projected: {err}")

    def _apply(self, proposal: Proposal, authority: UserAuthority | None) -> ApplyResult:
        ops = [copy.deepcopy(op) for op in proposal.ops]
        if authority is not None:  # your own surface acting on your click or typed words: recorded under you
            for op in ops:
                if isinstance(op.actor, str) and op.actor.startswith("code:"):
                    op.actor = "user"
        history = HistoryRead(self._history, self.tenant_id)  # a fresh message cache per proposal
        recorded_at = self.clock()
        work = self._work(proposal, ops)
        ctx = Context(
            proposal, ops, self._read, history, recorded_at, limits=self.limits, work_families=work.families,
            user_authority=authority is not None,
        )  # fmt: skip
        self._unrecorded = work.unrecorded

        replayed = self._replay(proposal, ops)  # 0
        if replayed is not None:
            return replayed
        for _, check in INTAKE:  # 1
            intake = check(ctx)
            if intake:
                return _rejected(intake)
        if authority is None:
            fenced = self._fence(proposal)  # 2
            if fenced is not None:
                return fenced
        stale = self._freshness(ctx)  # 3
        if stale is not None:
            return _refused("freshness", stale, "requeued")
        frozen = self._frozen(ops)  # 4
        if frozen is not None:
            return _refused("freeze", frozen)

        verdicts = self._verdicts(ctx, work)
        ctx.verdict_families = frozenset(v.checker_family for v in verdicts.independent)
        violations = run_checks(CODE_CHECKS, ctx)  # 5
        if violations:
            return _rejected(violations)
        labels: list[str] = []
        if authority is None:
            unverified, labels = self._verification(ctx, verdicts)  # 6
            if unverified:
                return ApplyResult("rejected", rejections=unverified)
        capped = check_i13(ctx)  # 7
        if capped:
            return _rejected(capped)
        bound = loss_bound(ctx)
        if bound.exceeded and not any(LOSS_BOUND_RULE in v.rules for v in verdicts.counted):
            reason = (
                f"this run would retire {bound.total} items; it may retire {bound.allowed} "
                f"({self.limits.loss_bound:.0%} of {bound.active} active items), so it is held for a second check"
            )
            return _refused("I13", reason, "held")
        return self._append(ctx, verdicts, labels)  # 8

    # --- 0 replay ---

    def _replay(self, proposal: Proposal, ops: list[EventEnvelope]) -> ApplyResult | None:
        rows = self._read._all(
            "SELECT seq, type, subjects, index_in_proposal FROM event WHERE run_id = ? AND proposal_id = ? ORDER BY index_in_proposal",
            (proposal.run_id, proposal.proposal_id),
        )
        if not rows:
            return None
        if len(rows) == len(ops) and all(
            r["index_in_proposal"] == i and r["type"] == op.type and sorted(json.loads(r["subjects"])) == sorted(_subjects(op))
            for i, (r, op) in enumerate(zip(rows, ops))
        ):
            return ApplyResult("duplicate", applied_seqs=[r["seq"] for r in rows])
        return _refused("I14", f"proposal {proposal.proposal_id} was applied before, with other events than these")

    # --- 2 fencing ---

    def _fence(self, proposal: Proposal) -> ApplyResult | None:
        if self.runs is None:
            return None
        run = self.runs.get_run(proposal.run_id)
        if run is None:
            return _refused("fencing", f"run {proposal.run_id} is not in runs.db")
        if run["state"] not in ("running", "held"):
            return _refused("fencing", f"run {proposal.run_id} is {run['state']}, not the current run")
        newer = [r["id"] for r in self.runs.runs("running") if r["id"] > proposal.run_id]
        if newer:
            return _refused("fencing", f"run {newer[0]} started after run {proposal.run_id}; this one is no longer current")
        return None

    # --- 3 freshness ---

    def _freshness(self, ctx: Context) -> str | None:
        """Why the proposal is stale, or None. Objects this proposal creates are fresh by definition."""
        seen: set[str] = set()
        for text in [*ctx.proposal.inputs, *(i for op in ctx.ops for i in op.inputs)]:
            if text in seen:
                continue
            seen.add(text)
            kind, object_id, version = parse_input(text)
            if ctx.made_here(object_id):
                continue
            if kind == "message":
                if ctx.history.message(object_id) is None:
                    return f"input {text}: that message is not in chat history yet"
            elif kind == "item" or kind in MemoryRead.VERSIONED:  # derived and unknown kinds are I7's to refuse
                current = ctx.memory.version_of(kind, object_id)
                if current is None:
                    return f"input {text}: {kind} {object_id} does not exist yet"
                if not version.isdigit() or int(version) != current:
                    return f"input {text}: {kind} {object_id} is now at version {current}"
        for index, op in enumerate(ctx.ops):
            problem = self._stale_op(ctx, op)
            if problem:
                return f"op {index} ({op.type}): {problem}"
        return None

    @staticmethod
    def _stale_op(ctx: Context, op: EventEnvelope) -> str | None:
        """An op names the state it builds on (a base version, a from-status): that state must still hold."""
        p = op.payload
        checks: list[tuple[str, str, Any, str]] = []  # (item id, field, expected, what)
        if op.type in ("item.revised", "item.scope_widened"):
            checks.append((p["item_id"], "version", p["base_version"], "version"))
        elif op.type == "item.value_changed":
            checks.append((p["item_id"], "value", p["from_value"], "value"))
        elif op.type == "supersession.applied":
            checks.append((p["old_item"], "version", p["old_version"], "version"))
        elif op.type == "item.status_changed":
            checks.append((p["item_id"], "status", p["from_status"], "status"))
        elif op.type == "goal.status_changed":
            checks.append((p["item_id"], "goal_status", p["from_status"], "goal status"))
        elif op.type == "question.status_changed":
            checks.append((p["item_id"], "question_status", p["from_status"], "question status"))
        elif op.type == "conflict.opened":
            checks += [(p["side_a_item"], "version", p["side_a_version"], "version"), (p["side_b_item"], "version", p["side_b_version"], "version")]
        for item_id, name, expected, what in checks:
            if ctx.made_here(item_id):
                continue
            row = ctx.memory.item(item_id)
            if row is None:
                return f"item {item_id} does not exist yet"
            if row[name] != expected:
                return f"item {item_id} is at {what} {row[name]}, not {expected}"
        return None

    # --- 4 freezes ---

    def _frozen(self, ops: Sequence[EventEnvelope]) -> str | None:
        if self.runs is None:
            return None
        for op in ops:
            if op.actor == "user":
                continue  # a freeze stops automation, never you
            kind = events.change_type(op)
            if self.runs.is_frozen(kind):
                return f"change type {kind} is frozen until a test run on sample data passes"
        return None

    # --- 6 verdicts ---

    def _work(self, proposal: Proposal, ops: Sequence[EventEnvelope]) -> _Work:
        """The families that did the work: those of every call recorded under the job the stage saved the proposal for
        (runs.db, not the proposal's say-so), and those of the recorded model calls behind the ops' `model:...#<hash>`
        actors, and the actors whose call is not recorded (a malformed actor is for intake to refuse)."""
        found = _Work()
        if self.runs is None:
            return found
        stored = self.runs.get_proposal(proposal.proposal_id)
        if stored is not None and stored.get("job_id"):  # the stage that saved it says which job made it: those calls did the work
            for call in self.runs.calls_for_job(stored["job_id"]):
                found.families.add(call["family"])
                found.call_ids.add(call["id"])
                found.hashes.add(call["prompt_hash"])
        for op in ops:
            if isinstance(op.actor, str) and op.actor.startswith("model:") and "#" in op.actor:
                prompt_hash = op.actor.rsplit("#", 1)[1]
                call = self.runs.recorded_call(prompt_hash, proposal.run_id) or self.runs.recorded_call(prompt_hash)
                if call:
                    found.families.add(call["family"])
                    found.call_ids.add(call["id"])
                    found.hashes.add(prompt_hash)
                elif op.actor not in found.unrecorded:
                    found.unrecorded.append(op.actor)
        return found

    def _recorded_verdicts(self, proposal: Proposal) -> tuple[list[Verdict], list[str]]:
        """The verdicts on record in runs.db for this proposal, as `Verdict`s, and why any were set aside. The ones the
        proposal carries are ignored. They count for these ops only: runs.db keeps the ops they judged."""
        stored = self.runs.get_proposal(proposal.proposal_id)
        if stored is None:
            return [], ["no proposal of this id is recorded in runs.db, so no check of it is on record"]
        if stored["run_id"] != proposal.run_id or not _same_ops(stored["ops"], proposal.ops):
            return [], ["the checks on record in runs.db judged other ops than these"]
        return [
            Verdict(
                checker_family=v["checker_family"], rules=list(v["rules"]), outcome=v["outcome"], independent=bool(v["independent"]),
                model_call_id=v["model_call_id"], notes=v["notes"], id=v["id"],
            )
            for v in self.runs.verdicts(proposal.proposal_id)
        ], []  # fmt: skip

    def _provenance(self, v: Verdict, proposal: Proposal, work: _Work) -> str | None:
        """Why a recorded verdict is not backed by a model call of its own, or None: it names a recorded, successful call
        of this run, of the family it states, that is neither the work's call nor of the work's prompt."""
        if not v.model_call_id:
            return f"a {v.checker_family} verdict names no model call"
        call = self.runs.get_call(v.model_call_id)
        if call is None or call["run_id"] != proposal.run_id:
            return f"a {v.checker_family} verdict names a model call that is not recorded for this run"
        if call["status"] != "ok":
            return f"a {v.checker_family} verdict names a model call that did not succeed"
        if call["family"] != v.checker_family:
            return f"the verdict names a model call that is not a {v.checker_family} call"
        if call["id"] in work.call_ids or call["prompt_hash"] in work.hashes:
            return f"a {v.checker_family} verdict names the call that did the work, which cannot check itself"
        return None

    def _other_family_left(self, barred: frozenset[str]) -> bool:
        """True if a family outside `barred` can still be asked to check. Unknown families count as none left: the label
        recorded with the verdict then stands."""
        return self.families is not None and any(f not in barred for f in self.families)

    def _verdicts(self, ctx: Context, work: _Work) -> _Verdicts:
        """Sort the verdicts for a proposal. With a run store only the ones recorded in runs.db are read, and each must be
        backed by a model call of its own. A passing verdict counts when its family is neither the work's nor the claim's
        and it is independent; when it is by one of those, or is labelled not independent, it counts as a check 'not
        independent' only where no other family is left (§5.9)."""
        out = _Verdicts()
        if self.runs is None:
            candidates = list(ctx.proposal.verdicts)
        else:
            candidates, out.notes = self._recorded_verdicts(ctx.proposal)
        barred = work.families | ctx.claim_families()
        for v in candidates:
            if not v.passed:
                out.failed.append(v)
            elif v.checker_family == "code":
                out.notes.append("a code verdict is not an independent check")
            elif self.runs is not None and (problem := self._provenance(v, ctx.proposal, work)):
                out.notes.append(problem)
            elif v.independent and v.checker_family in barred:
                out.notes.append(f"{v.checker_family} did the work or said the claim, so its verdict does not count")
            elif v.independent:
                out.counted.append(v)
            elif v.checker_family in barred and self._other_family_left(barred):
                out.notes.append(f"{v.checker_family} did the work or said the claim, and another family is left to check it")
            else:
                out.counted.append(v)
                out.labelled.append(v)
        return out

    def _verification(self, ctx: Context, verdicts: _Verdicts) -> tuple[list[Rejection], list[str]]:
        """The verdicts the tier needs, and the labels to record. Returns the rejections, and the labels."""
        out = [
            Rejection("verification", f"{v.checker_family} failed this proposal (checked: {', '.join(v.rules) or 'nothing listed'})")
            for v in verdicts.failed
        ]
        if out:
            return out, []
        tier = proposal_tier(ctx.ops)
        detail = f" ({'; '.join(verdicts.notes)})" if verdicts.notes else ""
        full = lambda vs: any(set(FULL_RULES) <= set(v.rules) for v in vs)  # noqa: E731
        labels: list[str] = []
        if tier == "medium" and not verdicts.counted:
            out.append(Rejection("verification", "a medium-risk proposal needs one passing check by another model family" + detail))
        elif tier == "high" and not full(verdicts.counted):
            out.append(Rejection("verification", "a high-risk proposal needs a passing full-effort check by another model family" + detail))
        elif tier == "medium" and not verdicts.independent or tier == "high" and not full(verdicts.independent):
            labels.append(NOT_INDEPENDENT)  # only a check no other family could make independent backs this change
        if tier != "low" and self._unrecorded:  # outputs are recorded before they are read (§5.12); no call, no known family
            out.append(Rejection("verification", f"no recorded model call behind {self._unrecorded[0]}, so the family that did the work is unknown"))
        families = {v.checker_family for v in verdicts.counted}
        for index, op in enumerate(ctx.ops):
            if op.type == "item.checked" and op.payload["check_status"] in ("checked", "contradicted", NOT_INDEPENDENT) and op.payload.get("checker_family") not in families:
                out.append(Rejection("verification", f"the check names {op.payload.get('checker_family')}, and no passing verdict of that family backs it", index))
        return out, labels if not out else []

    # --- 8 the transaction ---

    def _append(self, ctx: Context, verdicts: _Verdicts, labels: Sequence[str]) -> ApplyResult:
        """Stamp who said it, append every event with its run key, and project. Runs inside the open transaction."""
        problems: list[Violation] = []
        independent = {v.checker_family for v in verdicts.independent}
        for index, op in enumerate(ctx.ops):
            p = op.payload
            if op.type == "evidence.anchored":
                ev = ctx.new_evidence[p["evidence_id"]]
                p.update(speaker=ev.speaker, agent=ev.agent, model_family=ev.model_family, origin=ev.origin)  # I3, I20
                cls = events.payload_class(op.type, op.schema_version)
                if cls is not None and "context" in {f.name for f in dataclasses.fields(cls)}:
                    p["context"] = ev.context  # the message's source project, or 'personal' (I3, I20)
            elif op.type in ITEM_CREATES:
                p["origin"] = ctx.op_origin(op)  # computed from the evidence, never set by a model (§2.5)
            elif op.type == "item.checked" and p["check_status"] == "checked" and NOT_INDEPENDENT in labels and p["checker_family"] not in independent:
                p["check_status"] = NOT_INDEPENDENT  # the event carries the label: no other family was left to check it
            op.recorded_at = ctx.recorded_at
            op.subjects = _subjects(op)
            problems += [Violation("I15", f"{op.type}: {text}", index) for text in events.problems(op, draft=False)]
        if problems:  # nothing is written until every stamped event is valid
            return _rejected(problems)
        seqs: list[int] = []
        for op in ctx.ops:
            cursor = self.memory.execute(
                "INSERT INTO event (tenant_id, id, type, schema_version, subjects, payload, actor, run_id, proposal_id,"
                " index_in_proposal, inputs, compensates, config_version, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    self.tenant_id, op.id, op.type, op.schema_version, _json(op.subjects), _json(op.payload), op.actor, op.run_id,
                    op.proposal_id, op.index_in_proposal, _json(op.inputs), op.compensates, op.config_version, op.recorded_at,
                ),
            )  # fmt: skip
            op.seq = cursor.lastrowid
            seqs.append(op.seq)
            self.memory.executemany(
                "INSERT OR IGNORE INTO event_subject (tenant_id, subject_id, seq) VALUES (?, ?, ?)",
                [(self.tenant_id, subject, op.seq) for subject in op.subjects],
            )
        self.projector.apply(self.memory, ctx.ops)
        return GateResult("applied", applied_seqs=seqs, labels=list(labels))


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _same_ops(stored: Sequence[Mapping[str, Any]], ops: Sequence[EventEnvelope]) -> bool:
    """The ops runs.db kept for a proposal are the ops being applied (as drafts: same ids, types, payloads and actors)."""
    if len(stored) != len(ops):
        return False
    return all(_json(dict(a)) == _json(events.to_dict(b)) for a, b in zip(stored, ops))


def _subjects(op: EventEnvelope) -> list[str]:
    """An event's subjects, from its payload: the proposer's own list is not trusted."""
    cls = events.payload_class(op.type, op.schema_version)
    try:
        return cls(**op.payload).subjects() if cls else list(op.subjects)  # type: ignore[arg-type]
    except TypeError:
        return list(op.subjects)
