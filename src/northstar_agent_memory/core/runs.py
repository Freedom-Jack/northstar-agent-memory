"""runs.db: maintenance run records (MEMORY-ARCHITECTURE §2.12, §5.3, §5.9, §5.12, §3.2).

`SQLiteRunStore` implements the RunStore port: runs, jobs with leases, model calls, proposals and verdicts,
quarantine, error budgets and the change log. Its writer is maintenance. The core makes no model call: a model's
raw output is recorded here before anyone reads it, and a call is found again by its prompt hash, never regenerated
(§5.12).

Verdicts are the gate's evidence that another family checked a change, so they are recorded here, never taken from
the proposal (§5.9, principle 4): `record_verdict` refuses a verdict that names a model call this run did not make,
or one of another family than it states, and `verdicts_for` hands the gate what was recorded. A verdict that names no
call is stored, but it backs nothing. A check with no other family left is recorded as not independent (DESIGN §1.2).

The starting values (attempts, days, the error budget and its minimum sample, the idle trigger) come from the
`[maintenance]` block of the config (I19, §5.13); each falls back to its documented number if a key is missing.

Nothing in this store is an input to extraction, integration or abstraction (I7). Model calls keep input ids and
never the assembled text; the change log is written for you and for audits, and its one read is
`read_change_log`, which typed input assembly must never call.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Mapping, Sequence

from northstar_agent_memory import config as _config
from northstar_agent_memory.core import events
from northstar_agent_memory.core.db import DEFAULT_TENANT, maintenance_setting, open_store, transaction
from northstar_agent_memory.core.ids import new_id, utc_now
from northstar_agent_memory.core.ports import EvidenceQuote, Job, ModelCall, Proposal, Verdict

RUN_TRIGGERS = ("idle", "nightly", "weekly", "manual")
JOB_STAGES = ("trigger", "replay", "extract", "integrate", "refresh", "check", "weekly", "rebuild", "log")
PROPOSAL_STATES = ("applied", "rejected", "quarantined", "requeued")
QUARANTINE_TARGETS = ("proposal", "item", "link")
QUARANTINE_EXITS = ("fresh_call", "re_extracted", "discarded", "applied")

# Fallbacks for the `[maintenance]` block of defaults.toml (I19): the same numbers, used if a key is missing.
MAX_QUARANTINE_ATTEMPTS = 3  # §5.9 (start); the quarantine table allows at most 3
QUARANTINE_DAYS = 7  # §5.9 (start)
DEFAULT_ERROR_BUDGET = 0.02  # §5.9 (start): a change type whose audited error rate passes 2% is frozen
ERROR_BUDGET_MIN_SAMPLE = 20  # §5.9 (start): ...but only once this many of its changes were audited
MAX_JOB_ATTEMPTS = 3  # §2.12 (start): a job leased this often without finishing is quarantined
IDLE_TRIGGER_MINUTES = 30  # §5.13 (start): a session is idle after this long

# A run ends in one of these; `held` waits for a second check and can still be applied.
_RUN_MOVES = {
    "queued": ("applied", "held", "failed", "cancelled"),
    "running": ("applied", "held", "failed", "cancelled"),
    "held": ("applied", "held", "failed", "cancelled"),
    "applied": ("undone",),
}

_JSON_COLUMNS = ("budget_used", "result", "payload", "input_ids", "ops", "evidence", "abstentions", "inputs", "rules", "event_ids")


class LeaseLost(RuntimeError):
    """A worker tried to finish a job whose lease another worker holds now."""


@dataclass(frozen=True, slots=True)
class RunSettings:
    """The run store's starting values (§5.9, §5.13, I19), read from `[maintenance]` in the config."""

    quarantine_attempts: int = MAX_QUARANTINE_ATTEMPTS
    quarantine_days: float = QUARANTINE_DAYS
    max_job_attempts: int = MAX_JOB_ATTEMPTS
    error_budget: float = DEFAULT_ERROR_BUDGET
    error_budget_min_sample: int = ERROR_BUDGET_MIN_SAMPLE
    idle_trigger_minutes: float = IDLE_TRIGGER_MINUTES

    @classmethod
    def from_config(cls, config: Mapping[str, Any] | None = None) -> "RunSettings":
        """The settings in `config` (the loaded config if None); a missing key keeps its starting value."""
        cfg = _config.load() if config is None else config
        section = cfg.get("maintenance", {})
        return cls(
            quarantine_attempts=maintenance_setting(section, "quarantine_attempts", MAX_QUARANTINE_ATTEMPTS, whole=True, low=1, high=3),
            quarantine_days=maintenance_setting(section, "quarantine_days", QUARANTINE_DAYS, low_open=True),
            max_job_attempts=maintenance_setting(section, "max_job_attempts", MAX_JOB_ATTEMPTS, whole=True, low=1),
            error_budget=maintenance_setting(section, "error_budget", DEFAULT_ERROR_BUDGET, high=1),
            error_budget_min_sample=maintenance_setting(section, "error_budget_min_sample", ERROR_BUDGET_MIN_SAMPLE, whole=True),
            idle_trigger_minutes=maintenance_setting(section, "idle_trigger_minutes", IDLE_TRIGGER_MINUTES, low_open=True),
        )


def error_budget_start(config: Mapping[str, Any] | None = None) -> float:
    """The audited error rate above which a change type freezes: `[maintenance] error_budget` in the config if
    present, else 0.02 (§5.9)."""
    return RunSettings.from_config(config).error_budget


def _parse(iso: str) -> datetime:
    return datetime.fromisoformat(iso)


def _format(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def normalize_time(iso: str) -> str:
    """An ISO 8601 time in the one stored format (UTC, milliseconds, Z), so text comparison orders by time."""
    return _format(_parse(iso))


def shift(iso: str, *, seconds: float = 0, days: float = 0) -> str:
    """An ISO 8601 UTC time moved forward by some seconds or days, in the format of `ids.utc_now`."""
    return _format(_parse(iso) + timedelta(seconds=seconds, days=days))


def default_deadline(now: str | None = None, config: Mapping[str, Any] | None = None) -> str:
    """The deadline of a new quarantine: `[maintenance] quarantine_days` on (7 to start)."""
    return shift(now or utc_now(), days=RunSettings.from_config(config).quarantine_days)


def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    out = dict(row)
    for key in _JSON_COLUMNS:
        if key in out and out[key] is not None:
            out[key] = json.loads(out[key])
    return out


def _choice(value: str, allowed: Sequence[str], name: str) -> str:
    if value not in allowed:
        raise ValueError(f"{name} must be one of {allowed}, got {value!r}")
    return value


def _quote_dict(quote: EvidenceQuote) -> dict[str, Any]:
    return {"message_id": quote.message_id, "start_char": quote.start_char, "end_char": quote.end_char, "quote": quote.quote}


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


class SQLiteRunStore:
    """The RunStore port on runs.db. One writer; reads never change the store.

    `config` holds `[maintenance]` (the loaded config if None): the attempt cap on jobs, the quarantine limits, the
    error budget and its minimum sample. `freeze_above` and `min_sample` override the budget's two numbers for this
    store: the audited error rate above which a change type freezes, and how many changes must be audited first.
    A job leased `max_job_attempts` times without finishing is quarantined, not leased again (§5.9).
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        tenant_id: str = DEFAULT_TENANT,
        *,
        freeze_above: float | None = None,
        min_sample: int | None = None,
        config: Mapping[str, Any] | None = None,
    ) -> None:
        self.conn = conn
        self.tenant_id = tenant_id
        self.settings = RunSettings.from_config(config)
        self.freeze_above = self.settings.error_budget if freeze_above is None else freeze_above
        self.min_sample = self.settings.error_budget_min_sample if min_sample is None else min_sample
        if isinstance(self.min_sample, bool) or not isinstance(self.min_sample, int) or self.min_sample < 0:
            raise ValueError(f"min_sample is a whole number of zero or more, got {self.min_sample!r}")

    @classmethod
    def open(cls, root=None, tenant_id: str = DEFAULT_TENANT, **kwargs) -> "SQLiteRunStore":
        return cls(open_store("runs", root), tenant_id, **kwargs)

    def close(self) -> None:
        self.conn.close()

    # --- internals ---

    def _one(self, table: str, value: str, column: str = "id") -> dict[str, Any] | None:
        sql = f"SELECT * FROM {table} WHERE {column} = ? AND tenant_id = ?"
        return _row(self.conn.execute(sql, (value, self.tenant_id)).fetchone())

    def _need(self, table: str, id_: str) -> dict[str, Any]:
        row = self._one(table, id_)
        if row is None:
            raise KeyError(f"no {table} with id {id_!r}")
        return row

    def _all(self, sql: str, args: Sequence[Any]) -> list[dict[str, Any]]:
        return [_row(r) for r in self.conn.execute(sql, args).fetchall()]  # type: ignore[misc]

    # --- runs ---

    def start_run(self, trigger: Literal["idle", "nightly", "weekly", "manual"], watermark_from: int = 0) -> str:
        """Begin a run; it is `running` at once."""
        _choice(trigger, RUN_TRIGGERS, "trigger")
        if isinstance(watermark_from, bool) or watermark_from < 0:
            raise ValueError("watermark_from is a message seq: zero or more")
        rid = new_id()
        with transaction(self.conn):
            self.conn.execute(
                "INSERT INTO run (tenant_id, id, trigger, watermark_from, state, started_at) VALUES (?, ?, ?, ?, 'running', ?)",
                (self.tenant_id, rid, trigger, watermark_from, utc_now()),
            )
        return rid

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        return self._one("run", run_id)

    def runs(self, state: str | None = None) -> list[dict[str, Any]]:
        """Runs, newest first."""
        if state is None:
            return self._all("SELECT * FROM run WHERE tenant_id = ? ORDER BY id DESC", (self.tenant_id,))
        return self._all("SELECT * FROM run WHERE tenant_id = ? AND state = ? ORDER BY id DESC", (self.tenant_id, state))

    def set_safety_copy(self, run_id: str, path: str) -> None:
        """Note where the working copy of memory, index and overview is (§5.10)."""
        self._need("run", run_id)
        with transaction(self.conn):
            self.conn.execute("UPDATE run SET safety_copy = ? WHERE id = ? AND tenant_id = ?", (path, run_id, self.tenant_id))

    def add_usage(self, run_id: str, usage: Mapping[str, float]) -> dict[str, float]:
        """Add amounts (tokens, dollars, calls) to the run's `budget_used` and return the new totals."""
        self._need("run", run_id)
        with transaction(self.conn):
            used = json.loads(self.conn.execute("SELECT budget_used FROM run WHERE id = ? AND tenant_id = ?", (run_id, self.tenant_id)).fetchone()[0])
            for key, amount in usage.items():
                if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount < 0:
                    raise ValueError(f"usage of {key!r} must be a number of zero or more, got {amount!r}")
                used[key] = used.get(key, 0) + amount
            self.conn.execute("UPDATE run SET budget_used = ? WHERE id = ? AND tenant_id = ?", (_json(used), run_id, self.tenant_id))
        return used

    def finish_run(
        self,
        run_id: str,
        state: Literal["applied", "held", "failed", "cancelled", "undone"],
        *,
        watermark_to: int | None = None,
        result: dict | None = None,
        safety_copy: str | None = None,
    ) -> None:
        """Move a run to its next state. `held` is not an end: it has no end time and can be applied later."""
        with transaction(self.conn):
            run = self._need("run", run_id)
            if state not in _RUN_MOVES.get(run["state"], ()):
                raise ValueError(f"a run that is {run['state']} cannot become {state}")
            if watermark_to is not None and watermark_to < run["watermark_from"]:
                raise ValueError("watermark_to is below watermark_from")
            self.conn.execute(
                "UPDATE run SET state = ?, watermark_to = COALESCE(?, watermark_to), result = COALESCE(?, result),"
                " safety_copy = COALESCE(?, safety_copy), ended_at = ? WHERE id = ? AND tenant_id = ?",
                (
                    state, watermark_to, None if result is None else _json(result), safety_copy,
                    None if state == "held" else utc_now(), run_id, self.tenant_id,
                ),
            )

    def default_deadline(self, now: str | None = None) -> str:
        """The deadline of a new quarantine under this store's settings."""
        return shift(normalize_time(now) if now else utc_now(), days=self.settings.quarantine_days)

    # --- jobs with leases ---

    def enqueue(self, run_id: str, stage: str, idempotency_key: str, payload: dict | None = None) -> str:
        """Add a job. The same idempotency key returns the existing job's id and adds nothing."""
        _choice(stage, JOB_STAGES, "stage")
        if not idempotency_key:
            raise ValueError("a job needs an idempotency key")
        self._need("run", run_id)
        now = utc_now()
        with transaction(self.conn):
            existing = self.conn.execute("SELECT id FROM job WHERE idempotency_key = ? AND tenant_id = ?", (idempotency_key, self.tenant_id)).fetchone()
            if existing:
                return existing["id"]
            jid = new_id()
            self.conn.execute(
                "INSERT INTO job (tenant_id, id, run_id, stage, idempotency_key, payload, state, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?, 'queued', ?, ?)",
                (self.tenant_id, jid, run_id, stage, idempotency_key, _json(payload or {}), now, now),
            )
        return jid

    def lease(self, owner: str, stages: Sequence[str], ttl_seconds: int, now: str | None = None) -> Job | None:
        """Lease the oldest queued job of those stages, or one whose lease has expired, and count one attempt.

        A job that has had `max_job_attempts` attempts is not leased again: it is quarantined (state `quarantined`,
        its last error kept) and the next job is looked at instead.

        `now` is for tests and for a caller with its own clock; it is an ISO 8601 UTC time like `ids.utc_now`.
        """
        if not owner:
            raise ValueError("a lease needs an owner")
        if ttl_seconds <= 0:
            raise ValueError("a lease needs a positive time to live")
        if not stages:
            return None
        for stage in stages:
            _choice(stage, JOB_STAGES, "stage")
        now = normalize_time(now) if now else utc_now()
        until = shift(now, seconds=ttl_seconds)
        marks = ", ".join("?" for _ in stages)
        cap = self.settings.max_job_attempts
        with transaction(self.conn):
            while True:
                row = self.conn.execute(
                    f"SELECT * FROM job WHERE tenant_id = ? AND stage IN ({marks}) AND (state = 'queued'"
                    " OR (state IN ('leased', 'running') AND lease_until <= ?)) ORDER BY created_at, id LIMIT 1",
                    (self.tenant_id, *stages, now),
                ).fetchone()
                if row is None:
                    return None
                if row["attempts"] < cap:
                    break
                self._quarantine_job(row, now)  # tried enough times: set aside, and look at the next job
            self.conn.execute(
                "UPDATE job SET state = 'leased', lease_owner = ?, lease_until = ?, attempts = attempts + 1, updated_at = ?"
                " WHERE id = ? AND tenant_id = ?",
                (owner, until, now, row["id"], self.tenant_id),
            )
        return Job(
            id=row["id"], run_id=row["run_id"], stage=row["stage"], idempotency_key=row["idempotency_key"],
            payload=json.loads(row["payload"]), attempts=row["attempts"] + 1, lease_owner=owner, lease_until=until,
        )

    def _quarantine_job(self, row: sqlite3.Row, now: str) -> None:
        """Set a job aside for good: it was leased `max_job_attempts` times and never finished (§5.9)."""
        reason = f"quarantined after {row['attempts']} attempts"
        error = f"{reason}: {row['error']}" if row["error"] else reason
        self.conn.execute(
            "UPDATE job SET state = 'quarantined', error = ?, lease_owner = NULL, lease_until = NULL, updated_at = ? WHERE id = ? AND tenant_id = ?",
            (error, now, row["id"], self.tenant_id),
        )

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        return self._one("job", job_id)

    def jobs(self, run_id: str, state: str | None = None) -> list[dict[str, Any]]:
        """The jobs of a run, oldest first."""
        sql, args = "SELECT * FROM job WHERE run_id = ? AND tenant_id = ?", [run_id, self.tenant_id]
        if state is not None:
            sql, args = sql + " AND state = ?", args + [state]
        return self._all(sql + " ORDER BY created_at, id", args)

    def _held_job(self, job_id: str, owner: str | None) -> dict[str, Any]:
        job = self._need("job", job_id)
        if job["state"] not in ("leased", "running"):
            raise ValueError(f"job {job_id!r} is {job['state']}, not leased")
        if owner is not None and job["lease_owner"] != owner:
            raise LeaseLost(f"job {job_id!r} is leased by {job['lease_owner']!r}, not {owner!r}")
        return job

    def mark_running(self, job_id: str, *, owner: str | None = None) -> None:
        """The worker that leased the job has begun it: `leased` becomes `running`. The lease still runs out, so a
        worker that dies is replaced like any other. With `owner`, a worker that lost its lease gets LeaseLost."""
        with transaction(self.conn):
            self._held_job(job_id, owner)
            self.conn.execute(
                "UPDATE job SET state = 'running', updated_at = ? WHERE id = ? AND tenant_id = ?", (utc_now(), job_id, self.tenant_id)
            )

    def complete(self, job_id: str, *, owner: str | None = None) -> None:
        """Mark a leased job done. With `owner`, a worker that lost its lease gets LeaseLost. A done job stays done."""
        with transaction(self.conn):
            if self._need("job", job_id)["state"] == "done":
                return
            self._held_job(job_id, owner)
            self.conn.execute(
                "UPDATE job SET state = 'done', lease_owner = NULL, lease_until = NULL, updated_at = ? WHERE id = ? AND tenant_id = ?",
                (utc_now(), job_id, self.tenant_id),
            )

    def fail(self, job_id: str, error: str, *, retry: bool, owner: str | None = None) -> str:
        """Requeue the job (retry) or mark it failed; the error is kept either way. A retry of a job that has used up
        its attempts quarantines it instead. Returns the job's new state: queued, failed or quarantined."""
        with transaction(self.conn):
            job = self._held_job(job_id, owner)
            state = "failed"
            if retry:
                state = "queued" if job["attempts"] < self.settings.max_job_attempts else "quarantined"
            if state == "quarantined":
                error = f"quarantined after {job['attempts']} attempts: {error}"
            self.conn.execute(
                "UPDATE job SET state = ?, error = ?, lease_owner = NULL, lease_until = NULL, updated_at = ? WHERE id = ? AND tenant_id = ?",
                (state, error, utc_now(), job_id, self.tenant_id),
            )
        return state

    # --- model calls ---

    def record_call(self, call: ModelCall) -> str:
        """Record a model call and return its id. Call it with the raw output, before anything reads the output.

        `input_ids` name what went in; anything that looks like assembled text (spaces, over 200 characters) is
        refused, because the assembled input is never stored (§2.12).
        """
        for input_id in call.input_ids:
            if not isinstance(input_id, str) or not input_id or len(input_id) > 200 or any(c.isspace() for c in input_id):
                raise ValueError(f"input_ids must be ids, never assembled text: {str(input_id)[:40]!r}")
        if not call.prompt_hash:
            raise ValueError("a model call needs its prompt hash")
        if call.run_id is not None:
            self._need("run", call.run_id)
        if call.job_id is not None:
            self._need("job", call.job_id)
        call.called_at = call.called_at or utc_now()
        with transaction(self.conn):
            self.conn.execute(
                "INSERT INTO model_call (tenant_id, id, run_id, job_id, provider, model, family, prompt_hash, input_ids,"
                " raw_output, tokens_in, tokens_out, cost, status, called_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    self.tenant_id, call.id, call.run_id, call.job_id, call.provider, call.model, call.family,
                    call.prompt_hash, _json(list(call.input_ids)), call.raw_output, call.tokens_in, call.tokens_out,
                    call.cost, call.status, call.called_at,
                ),
            )
        return call.id

    def get_call(self, call_id: str) -> dict[str, Any] | None:
        return self._one("model_call", call_id)

    def calls(self, run_id: str) -> list[dict[str, Any]]:
        return self._all("SELECT * FROM model_call WHERE run_id = ? AND tenant_id = ? ORDER BY id", (run_id, self.tenant_id))

    def calls_for_job(self, job_id: str) -> list[dict[str, Any]]:
        """Every call recorded under a job, whatever its status. A proposal saved with a job id was made by those calls."""
        return self._all("SELECT * FROM model_call WHERE job_id = ? AND tenant_id = ? ORDER BY id", (job_id, self.tenant_id))

    def recorded_call(self, prompt_hash: str, run_id: str | None = None) -> dict[str, Any] | None:
        """The latest successful call for this prompt hash (in this run, if given). A recorded output is reused,
        never regenerated (§5.12)."""
        sql, args = "SELECT * FROM model_call WHERE prompt_hash = ? AND tenant_id = ? AND status = 'ok'", [prompt_hash, self.tenant_id]
        if run_id is not None:
            sql, args = sql + " AND run_id = ?", args + [run_id]
        return _row(self.conn.execute(sql + " ORDER BY id DESC LIMIT 1", args).fetchone())

    # --- proposals and verdicts ---

    def save_proposal(self, proposal: Proposal, *, job_id: str | None = None) -> None:
        """Store a proposal (ops, evidence, abstentions, inputs, tier) as pending, with the verdicts it carries.

        A proposal id that is stored already is left as it is.
        """
        self._need("run", proposal.run_id)
        if job_id is not None:
            self._need("job", job_id)
        with transaction(self.conn):
            if self.conn.execute("SELECT 1 FROM proposal WHERE id = ? AND tenant_id = ?", (proposal.proposal_id, self.tenant_id)).fetchone():
                return
            self.conn.execute(
                "INSERT INTO proposal (tenant_id, id, run_id, job_id, ops, evidence, abstentions, inputs, risk_tier, state, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)",
                (
                    self.tenant_id, proposal.proposal_id, proposal.run_id, job_id,
                    _json([events.to_dict(op) for op in proposal.ops]),
                    _json([_quote_dict(q) for q in proposal.evidence]), _json(proposal.abstentions), _json(proposal.inputs),
                    proposal.risk_tier, utc_now(),
                ),
            )
            for verdict in proposal.verdicts:  # the proposal's own claims are checked like any other record
                self._insert_verdict(proposal.proposal_id, proposal.run_id, verdict)

    def _insert_verdict(self, proposal_id: str, run_id: str, verdict: Verdict) -> str:
        """Store one verdict after checking what it says about itself against what is recorded here (§5.9)."""
        if verdict.outcome not in ("pass", "fail"):
            raise ValueError(f"a verdict's outcome is pass or fail, got {verdict.outcome!r}")
        if not isinstance(verdict.checker_family, str) or not verdict.checker_family:
            raise ValueError("a verdict names the family that checked")
        if verdict.model_call_id is not None:
            call = self._need("model_call", verdict.model_call_id)
            if call["run_id"] != run_id:
                raise ValueError(f"model call {verdict.model_call_id!r} was not made in run {run_id!r}")
            if call["family"] != verdict.checker_family:
                raise ValueError(
                    f"the verdict says {verdict.checker_family!r} checked, but its model call is a {call['family']!r} call"
                )
            if call["status"] != "ok":
                raise ValueError(f"model call {verdict.model_call_id!r} did not finish ({call['status']}), so it checked nothing")
        old = self._one("verdict", verdict.id)
        if old is not None:
            same = (old["proposal_id"], old["checker_family"], old["outcome"], old["model_call_id"], bool(old["independent"])) == (
                proposal_id, verdict.checker_family, verdict.outcome, verdict.model_call_id, bool(verdict.independent),
            )
            if not same:
                raise ValueError(f"verdict id {verdict.id!r} is recorded already, for something else")
            return verdict.id  # the same verdict again adds nothing
        self.conn.execute(
            "INSERT INTO verdict (tenant_id, id, proposal_id, checker_family, rules, outcome, independent,"
            " model_call_id, notes, at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                self.tenant_id, verdict.id, proposal_id, verdict.checker_family, _json(list(verdict.rules)),
                verdict.outcome, int(verdict.independent), verdict.model_call_id, verdict.notes, utc_now(),
            ),
        )
        return verdict.id

    def get_proposal(self, proposal_id: str) -> dict[str, Any] | None:
        return self._one("proposal", proposal_id)

    def proposals(self, run_id: str, state: str | None = None) -> list[dict[str, Any]]:
        sql, args = "SELECT * FROM proposal WHERE run_id = ? AND tenant_id = ?", [run_id, self.tenant_id]
        if state is not None:
            sql, args = sql + " AND state = ?", args + [state]
        return self._all(sql + " ORDER BY id", args)

    def load_proposal(self, proposal_id: str) -> Proposal | None:
        """The stored proposal as a `Proposal` again, with its verdicts, for the gate to re-check after a restart."""
        row = self.get_proposal(proposal_id)
        if row is None:
            return None
        verdicts = self.verdicts_for(proposal_id)
        return Proposal(
            run_id=row["run_id"], proposal_id=row["id"], ops=[events.from_dict(op) for op in row["ops"]],
            evidence=[EvidenceQuote(**q) for q in row["evidence"]], inputs=row["inputs"],
            abstentions=row["abstentions"], risk_tier=row["risk_tier"], verdicts=verdicts,
        )

    def record_verdict(self, proposal_id: str, verdict: Verdict) -> str:
        """Record a check of a proposal and return the verdict's id.

        The verdict keeps its model call's id, the family that checked and whether it was independent; `independent`
        False is the "not independent" label for a check made where no other family was left (DESIGN §1.2). A verdict
        that names a model call must name a call of this proposal's run, of the family it states, that finished: else
        ValueError. One that names no call is stored, and the gate counts it for nothing.
        """
        run_id = self._need("proposal", proposal_id)["run_id"]
        with transaction(self.conn):
            return self._insert_verdict(proposal_id, run_id, verdict)

    def verdicts_for(self, proposal_id: str) -> list[Verdict]:
        """The verdicts recorded for a proposal, oldest first, as `Verdict` records. This is where the gate reads
        them: the verdicts a proposal carries in memory are not trusted."""
        return [
            Verdict(
                checker_family=v["checker_family"], rules=v["rules"], outcome=v["outcome"],
                independent=bool(v["independent"]), model_call_id=v["model_call_id"], notes=v["notes"], id=v["id"],
            )
            for v in self.verdicts(proposal_id)
        ]

    def verdicts(self, proposal_id: str) -> list[dict[str, Any]]:
        return self._all("SELECT * FROM verdict WHERE proposal_id = ? AND tenant_id = ? ORDER BY at, id", (proposal_id, self.tenant_id))

    def set_proposal_state(self, proposal_id: str, state: Literal["applied", "rejected", "quarantined", "requeued"]) -> None:
        _choice(state, PROPOSAL_STATES, "state")
        with transaction(self.conn):
            current = self._need("proposal", proposal_id)["state"]
            if current == "applied" and state != "applied":
                raise ValueError(f"proposal {proposal_id!r} is applied; an applied proposal does not change state")
            if current == state == "applied":
                return  # applied is final (a table trigger holds it): saying so again changes nothing
            self.conn.execute("UPDATE proposal SET state = ? WHERE id = ? AND tenant_id = ?", (state, proposal_id, self.tenant_id))

    # --- quarantine ---

    def quarantine(
        self, target_kind: Literal["proposal", "item", "link"], target_id: str, reason: str, deadline: str | None = None
    ) -> str:
        """Set a failing target aside and return the quarantine id.

        A repeat for a target already open adds an attempt (the deadline stays), up to `quarantine_attempts` (3). One
        more repeat discards it: the quarantine exits as `discarded` (§5.9). `deadline` is the default one
        (`quarantine_days` on) if left out.
        """
        _choice(target_kind, QUARANTINE_TARGETS, "target_kind")
        if not reason.strip():
            raise ValueError("a quarantine needs a reason")
        deadline = normalize_time(deadline) if deadline else self.default_deadline()
        with transaction(self.conn):
            open_row = self.conn.execute(
                "SELECT * FROM quarantine WHERE tenant_id = ? AND target_kind = ? AND target_id = ? AND state = 'open'",
                (self.tenant_id, target_kind, target_id),
            ).fetchone()
            if open_row is None:
                qid = new_id()
                self.conn.execute(
                    "INSERT INTO quarantine (tenant_id, id, target_kind, target_id, reason, attempts, deadline, state, created_at)"
                    " VALUES (?, ?, ?, ?, ?, 1, ?, 'open', ?)",
                    (self.tenant_id, qid, target_kind, target_id, reason, deadline, utc_now()),
                )
                return qid
            if open_row["attempts"] >= self.settings.quarantine_attempts:
                self.conn.execute(
                    "UPDATE quarantine SET state = 'exited', exit = 'discarded' WHERE id = ? AND tenant_id = ?", (open_row["id"], self.tenant_id)
                )
            else:
                self.conn.execute(
                    "UPDATE quarantine SET attempts = attempts + 1, reason = ? WHERE id = ? AND tenant_id = ?", (reason, open_row["id"], self.tenant_id)
                )
            return open_row["id"]

    def get_quarantine(self, quarantine_id: str) -> dict[str, Any] | None:
        return self._one("quarantine", quarantine_id)

    def quarantines(self, state: str | None = "open") -> list[dict[str, Any]]:
        """Quarantines by deadline; `state=None` returns every one."""
        sql, args = "SELECT * FROM quarantine WHERE tenant_id = ?", [self.tenant_id]
        if state is not None:
            sql, args = sql + " AND state = ?", args + [state]
        return self._all(sql + " ORDER BY deadline, id", args)

    def exit_quarantine(self, quarantine_id: str, exit: Literal["fresh_call", "re_extracted", "discarded", "applied"]) -> None:
        _choice(exit, QUARANTINE_EXITS, "exit")
        with transaction(self.conn):
            if self._need("quarantine", quarantine_id)["state"] != "open":
                raise ValueError(f"quarantine {quarantine_id!r} has exited already")
            self.conn.execute(
                "UPDATE quarantine SET state = 'exited', exit = ? WHERE id = ? AND tenant_id = ?", (exit, quarantine_id, self.tenant_id)
            )

    def expire_quarantines(self, now: str | None = None) -> list[str]:
        """Discard every open quarantine whose deadline has passed; return their ids."""
        now = normalize_time(now) if now else utc_now()
        with transaction(self.conn):
            ids = [
                r["id"]
                for r in self.conn.execute(
                    "SELECT id FROM quarantine WHERE tenant_id = ? AND state = 'open' AND deadline <= ? ORDER BY deadline, id",
                    (self.tenant_id, now),
                )
            ]
            for qid in ids:
                self.conn.execute(
                    "UPDATE quarantine SET state = 'exited', exit = 'discarded' WHERE id = ? AND tenant_id = ?", (qid, self.tenant_id)
                )
        return ids

    # --- error budgets ---

    def budget(self, change_type: str) -> dict[str, Any] | None:
        """The audited error rate and frozen flag of a change type, or None before its first audit."""
        return self._one("budget", change_type, column="change_type")

    def is_frozen(self, change_type: str) -> bool:
        row = self.budget(change_type)
        return bool(row and row["frozen"])

    def record_audit(
        self, change_type: str, *, n: int, errors: int, freeze_above: float | None = None, min_sample: int | None = None
    ) -> dict[str, Any]:
        """Add audited changes and errors; freeze the type when its rate passes `freeze_above` (§5.9).

        The rate is all errors over all audited changes since the last thaw, and it freezes a type only once at least
        `min_sample` changes were audited (20 to start): below that the rate says too little, and one early miss
        would freeze a type on its first audit. Once frozen, a type stays frozen until `thaw` with a passing test
        run. Returns the budget row.
        """
        if not change_type:
            raise ValueError("a change type is needed")
        if n < 0 or errors < 0 or errors > n:
            raise ValueError(f"audited errors ({errors}) must be between 0 and audited changes ({n})")
        limit = self.freeze_above if freeze_above is None else freeze_above
        sample = self.min_sample if min_sample is None else min_sample
        now = utc_now()
        with transaction(self.conn):
            row = self.conn.execute(
                "SELECT * FROM budget WHERE tenant_id = ? AND change_type = ?", (self.tenant_id, change_type)
            ).fetchone()
            total = (row["audited_n"] if row else 0) + n
            wrong = (row["audited_errors"] if row else 0) + errors
            rate = wrong / total if total else 0.0
            was_frozen = bool(row and row["frozen"])
            frozen = was_frozen or (total >= sample and rate > limit)
            frozen_at = row["frozen_at"] if was_frozen else (now if frozen else None)
            self.conn.execute(
                "INSERT INTO budget (tenant_id, change_type, audited_n, audited_errors, audited_error_rate, frozen, frozen_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT (tenant_id, change_type) DO UPDATE SET audited_n = excluded.audited_n,"
                " audited_errors = excluded.audited_errors, audited_error_rate = excluded.audited_error_rate,"
                " frozen = excluded.frozen, frozen_at = excluded.frozen_at, updated_at = excluded.updated_at",
                (self.tenant_id, change_type, total, wrong, rate, int(frozen), frozen_at, now),
            )
        return self.budget(change_type)  # type: ignore[return-value]

    def freeze(self, change_type: str) -> dict[str, Any]:
        """Freeze a change type at once, as a sentinel does (§5.12). It thaws like any other."""
        now = utc_now()
        with transaction(self.conn):
            self.conn.execute(
                "INSERT INTO budget (tenant_id, change_type, frozen, frozen_at, updated_at) VALUES (?, ?, 1, ?, ?)"
                " ON CONFLICT (tenant_id, change_type) DO UPDATE SET frozen = 1, frozen_at = COALESCE(frozen_at, excluded.frozen_at),"
                " updated_at = excluded.updated_at",
                (self.tenant_id, change_type, now, now),
            )
        return self.budget(change_type)  # type: ignore[return-value]

    def thaw(self, change_type: str, *, test_passed: bool) -> dict[str, Any]:
        """Lift a freeze after a test run on sample data. Without a passing run the type stays frozen (ValueError).

        The audit counts start again from zero, so the old errors do not freeze the type at its next audit.
        """
        if self.budget(change_type) is None:
            raise KeyError(f"no budget for change type {change_type!r}")
        if not test_passed:
            raise ValueError(f"{change_type} stays frozen until a test run on sample data passes")
        with transaction(self.conn):
            self.conn.execute(
                "UPDATE budget SET frozen = 0, frozen_at = NULL, audited_n = 0, audited_errors = 0, audited_error_rate = 0,"
                " updated_at = ? WHERE tenant_id = ? AND change_type = ?",
                (utc_now(), self.tenant_id, change_type),
            )
        return self.budget(change_type)  # type: ignore[return-value]

    # --- change log ---

    def log_change(
        self, run_id: str, change_type: str, line: str, event_ids: Sequence[str], undo_handle: str | None = None
    ) -> str:
        """One plain line per change, with its undo. Append-only, and never read back as an input (I7)."""
        if not line.strip():
            raise ValueError("a change needs a plain line saying what changed and why")
        self._need("run", run_id)
        cid = new_id()
        with transaction(self.conn):
            self.conn.execute(
                "INSERT INTO change_log (tenant_id, id, run_id, at, change_type, line, event_ids, undo_handle)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (self.tenant_id, cid, run_id, utc_now(), change_type, line, _json(list(event_ids)), undo_handle),
            )
        return cid

    def read_change_log(self, run_id: str | None = None) -> list[dict[str, Any]]:
        """The log in order, for you and for audits. Typed input assembly never calls it (I7)."""
        if run_id is None:
            return self._all("SELECT * FROM change_log WHERE tenant_id = ? ORDER BY id", (self.tenant_id,))
        return self._all("SELECT * FROM change_log WHERE run_id = ? AND tenant_id = ? ORDER BY id", (run_id, self.tenant_id))

    def mark_undone(self, change_id: str, at: str | None = None) -> None:
        """Note that a change's undo was carried out. The only edit a log line ever gets, and only once."""
        with transaction(self.conn):
            row = self._need("change_log", change_id)
            if row["undone_at"] is not None:
                raise ValueError(f"change {change_id!r} was undone already")
            self.conn.execute(
                "UPDATE change_log SET undone_at = ? WHERE id = ? AND tenant_id = ?", (normalize_time(at) if at else utc_now(), change_id, self.tenant_id)
            )
