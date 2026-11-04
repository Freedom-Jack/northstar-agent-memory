"""SQLiteRunStore: runs, leased jobs, model calls, proposals, quarantine, error budgets and the change log (§2.12, §5.9)."""

from __future__ import annotations

import sqlite3

import pytest

from northstar_agent_memory.core import ports, runs
from northstar_agent_memory.core.ids import is_ulid, utc_now
from northstar_agent_memory.core.ports import EvidenceQuote, ModelCall, Proposal, Verdict
from northstar_agent_memory.core.runs import LeaseLost, SQLiteRunStore

T0 = "2026-03-02T09:00:00.000Z"


@pytest.fixture
def store(open_all):
    return SQLiteRunStore(open_all["runs"])


@pytest.fixture
def run(store):
    return store.start_run("nightly", watermark_from=10)


def test_it_is_a_run_store(store):
    assert isinstance(store, ports.RunStore)


def test_open_from_a_root_and_the_default_root(store_root, isolated_home):
    s = SQLiteRunStore.open(store_root)
    assert (store_root / "runs.db").is_file()
    s.close()
    from northstar_agent_memory import paths

    s = SQLiteRunStore.open()
    assert (paths.data_root() / "runs.db").is_file()
    s.close()


# --- runs ---


def test_start_run(store):
    rid = store.start_run("idle")
    row = store.get_run(rid)
    assert is_ulid(rid) and row["trigger"] == "idle" and row["state"] == "running"
    assert row["watermark_from"] == 0 and row["watermark_to"] is None and row["budget_used"] == {}
    assert row["safety_copy"] is None and row["result"] is None and row["ended_at"] is None and row["tenant_id"] == "local"


def test_start_run_refuses_bad_input(store):
    with pytest.raises(ValueError):
        store.start_run("hourly")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        store.start_run("manual", watermark_from=-1)


def test_finish_run_records_watermark_result_and_safety_copy(store, run):
    store.set_safety_copy(run, "/tmp/northstar-run/copy")
    store.finish_run(run, "applied", watermark_to=42, result={"events": 7, "items": ["m1"]})
    row = store.get_run(run)
    assert row["state"] == "applied" and row["watermark_to"] == 42
    assert row["result"] == {"events": 7, "items": ["m1"]} and row["ended_at"] is not None
    assert row["safety_copy"] == "/tmp/northstar-run/copy"


def test_finish_run_can_name_the_safety_copy(store, run):
    store.finish_run(run, "failed", safety_copy="/x/y")
    assert store.get_run(run)["safety_copy"] == "/x/y"


def test_a_held_run_has_no_end_and_can_be_applied_later(store, run):
    store.finish_run(run, "held", watermark_to=12, result={"reason": "loss bound"})
    held = store.get_run(run)
    assert held["state"] == "held" and held["ended_at"] is None
    store.finish_run(run, "applied")
    done = store.get_run(run)
    assert done["state"] == "applied" and done["ended_at"] is not None
    assert done["watermark_to"] == 12 and done["result"] == {"reason": "loss bound"}  # kept when not given again


def test_run_state_moves(store):
    r = store.start_run("manual")
    store.finish_run(r, "cancelled")
    with pytest.raises(ValueError):
        store.finish_run(r, "applied")  # a cancelled run stays cancelled
    r2 = store.start_run("manual")
    with pytest.raises(ValueError):
        store.finish_run(r2, "undone")  # only an applied run can be undone
    store.finish_run(r2, "applied")
    store.finish_run(r2, "undone")
    assert store.get_run(r2)["state"] == "undone"
    with pytest.raises(ValueError):
        store.finish_run(r2, "applied")
    with pytest.raises(KeyError):
        store.finish_run("nope", "applied")


def test_finish_run_refuses_a_watermark_going_backwards(store, run):
    with pytest.raises(ValueError):
        store.finish_run(run, "applied", watermark_to=9)
    assert store.get_run(run)["state"] == "running"


def test_runs_listing(store):
    a = store.start_run("idle")
    b = store.start_run("nightly")
    store.finish_run(a, "failed")
    assert [r["id"] for r in store.runs()] == [b, a]
    assert [r["id"] for r in store.runs("failed")] == [a]
    assert store.get_run("nope") is None


def test_usage_adds_up(store, run):
    assert store.add_usage(run, {"calls": 2, "usd": 0.5}) == {"calls": 2, "usd": 0.5}
    assert store.add_usage(run, {"calls": 1, "tokens": 900}) == {"calls": 3, "usd": 0.5, "tokens": 900}
    assert store.get_run(run)["budget_used"] == {"calls": 3, "usd": 0.5, "tokens": 900}
    for bad in ({"usd": -1}, {"usd": "a"}, {"usd": True}):
        with pytest.raises(ValueError):
            store.add_usage(run, bad)  # type: ignore[arg-type]
    assert store.get_run(run)["budget_used"]["calls"] == 3
    with pytest.raises(KeyError):
        store.add_usage("nope", {"calls": 1})


# --- jobs and leases ---


def test_enqueue_and_the_idempotency_key(store, run):
    a = store.enqueue(run, "extract", "run1:extract:chunk1", {"chunk": 1})
    again = store.enqueue(run, "extract", "run1:extract:chunk1", {"chunk": 99})
    assert a == again and is_ulid(a)
    assert len(store.jobs(run)) == 1
    job = store.get_job(a)
    assert job["payload"] == {"chunk": 1} and job["state"] == "queued" and job["attempts"] == 0
    assert job["lease_owner"] is None and job["lease_until"] is None


def test_the_idempotency_key_is_unique_across_runs(store, run):
    other = store.start_run("idle")
    a = store.enqueue(run, "replay", "k")
    assert store.enqueue(other, "replay", "k") == a
    assert store.jobs(other) == []


def test_enqueue_refuses_bad_input(store, run):
    with pytest.raises(ValueError):
        store.enqueue(run, "dream", "k")
    with pytest.raises(ValueError):
        store.enqueue(run, "extract", "")
    with pytest.raises(KeyError):
        store.enqueue("nope", "extract", "k")


def test_lease_takes_the_oldest_queued_job_of_those_stages(store, run):
    a = store.enqueue(run, "extract", "k1", {"n": 1})
    b = store.enqueue(run, "integrate", "k2")
    c = store.enqueue(run, "extract", "k3")
    job = store.lease("worker-1", ["extract"], 60, now=T0)
    assert isinstance(job, ports.Job)
    assert (job.id, job.run_id, job.stage, job.idempotency_key) == (a, run, "extract", "k1")
    assert job.payload == {"n": 1} and job.attempts == 1 and job.lease_owner == "worker-1"
    assert job.lease_until == "2026-03-02T09:01:00.000Z"
    assert store.lease("worker-2", ["extract"], 60, now=T0).id == c
    assert store.lease("worker-3", ["extract"], 60, now=T0) is None
    assert store.lease("worker-3", ["integrate", "check"], 60, now=T0).id == b
    row = store.get_job(a)
    assert row["state"] == "leased" and row["lease_owner"] == "worker-1" and row["attempts"] == 1


def test_lease_with_no_stages_or_no_jobs(store, run):
    store.enqueue(run, "extract", "k")
    assert store.lease("w", [], 60) is None
    assert store.lease("w", ["rebuild"], 60) is None


def test_lease_refuses_bad_input(store):
    with pytest.raises(ValueError):
        store.lease("", ["extract"], 60)
    with pytest.raises(ValueError):
        store.lease("w", ["extract"], 0)
    with pytest.raises(ValueError):
        store.lease("w", ["dream"], 60)


def test_a_live_lease_is_not_taken(store, run):
    store.enqueue(run, "extract", "k")
    store.lease("w1", ["extract"], 60, now=T0)
    assert store.lease("w2", ["extract"], 60, now="2026-03-02T09:00:59.999Z") is None


def test_an_expired_lease_is_leased_again_with_another_attempt(store, run):
    jid = store.enqueue(run, "extract", "k")
    store.lease("w1", ["extract"], 60, now=T0)
    again = store.lease("w2", ["extract"], 60, now="2026-03-02T09:01:00.000Z")  # lease_until is inclusive
    assert again.id == jid and again.attempts == 2 and again.lease_owner == "w2"
    assert again.lease_until == "2026-03-02T09:02:00.000Z"
    third = store.lease("w3", ["extract"], 30, now="2026-03-02T09:05:00.000Z")
    assert third.id == jid and third.attempts == 3
    assert store.get_job(jid)["attempts"] == 3


def test_the_first_worker_loses_its_lease(store, run):
    jid = store.enqueue(run, "extract", "k")
    store.lease("w1", ["extract"], 60, now=T0)
    store.lease("w2", ["extract"], 60, now="2026-03-02T09:02:00.000Z")
    with pytest.raises(LeaseLost):
        store.complete(jid, owner="w1")
    with pytest.raises(LeaseLost):
        store.fail(jid, "boom", retry=True, owner="w1")
    store.complete(jid, owner="w2")
    assert store.get_job(jid)["state"] == "done"


def test_a_running_job_with_an_expired_lease_is_also_leased_again(store, run):
    jid = store.enqueue(run, "check", "k")
    store.lease("w1", ["check"], 60, now=T0)
    store.conn.execute("UPDATE job SET state = 'running' WHERE id = ?", (jid,))
    assert store.lease("w2", ["check"], 60, now="2026-03-02T10:00:00.000Z").id == jid


def test_leases_order_by_age_across_queued_and_expired_jobs(store, run):
    a = store.enqueue(run, "extract", "k1")
    b = store.enqueue(run, "extract", "k2")
    store.lease("w1", ["extract"], 10, now=T0)  # a, expires at 09:00:10
    assert store.lease("w2", ["extract"], 10, now="2026-03-02T09:00:05.000Z").id == b
    assert store.lease("w3", ["extract"], 10, now="2026-03-02T09:00:11.000Z").id == a  # the older, expired one first


def test_complete_clears_the_lease(store, run):
    jid = store.enqueue(run, "extract", "k")
    store.lease("w1", ["extract"], 60, now=T0)
    store.complete(jid, owner="w1")
    row = store.get_job(jid)
    assert row["state"] == "done" and row["lease_owner"] is None and row["lease_until"] is None
    store.complete(jid)  # a done job stays done
    assert store.lease("w2", ["extract"], 60, now="2030-01-01T00:00:00.000Z") is None


def test_complete_needs_a_leased_job(store, run):
    jid = store.enqueue(run, "extract", "k")
    with pytest.raises(ValueError):
        store.complete(jid)
    with pytest.raises(KeyError):
        store.complete("nope")


def test_fail_with_retry_requeues_and_keeps_the_error(store, run):
    jid = store.enqueue(run, "extract", "k")
    store.lease("w1", ["extract"], 60, now=T0)
    store.fail(jid, "model timed out", retry=True)
    row = store.get_job(jid)
    assert row["state"] == "queued" and row["error"] == "model timed out" and row["lease_owner"] is None
    again = store.lease("w2", ["extract"], 60, now=T0)
    assert again.id == jid and again.attempts == 2


def test_fail_without_retry_ends_the_job(store, run):
    jid = store.enqueue(run, "extract", "k")
    store.lease("w1", ["extract"], 60, now=T0)
    store.fail(jid, "bad json", retry=False)
    assert store.get_job(jid)["state"] == "failed"
    assert store.lease("w2", ["extract"], 60, now="2030-01-01T00:00:00.000Z") is None
    with pytest.raises(ValueError):
        store.fail(jid, "again", retry=False)


def test_jobs_listing_by_state(store, run):
    a = store.enqueue(run, "extract", "k1")
    b = store.enqueue(run, "extract", "k2")
    store.lease("w", ["extract"], 60, now=T0)
    assert [j["id"] for j in store.jobs(run)] == [a, b]
    assert [j["id"] for j in store.jobs(run, "queued")] == [b]
    assert store.get_job("nope") is None


def test_shift_and_default_deadline():
    assert runs.shift("2026-03-02T09:00:00.000Z", seconds=90) == "2026-03-02T09:01:30.000Z"
    assert runs.shift("2026-03-02T09:00:00.000Z", days=7) == "2026-03-09T09:00:00.000Z"
    assert runs.default_deadline("2026-03-02T09:00:00.000Z") == "2026-03-09T09:00:00.000Z"
    assert runs.default_deadline() > utc_now()


# --- model calls ---


def make_call(**kw) -> ModelCall:
    base = dict(
        provider="harness", model="claude-test-1", family="claude", prompt_hash="ph-1",
        input_ids=["A4", "m3@1"], raw_output='{"ops": []}', tokens_in=1200, tokens_out=80, cost=0.0,
    )
    return ModelCall(**{**base, **kw})


def test_record_call_keeps_ids_and_raw_output_not_the_prompt(store, run):
    jid = store.enqueue(run, "extract", "k")
    call = make_call(run_id=run, job_id=jid)
    cid = store.record_call(call)
    row = store.get_call(cid)
    assert cid == call.id and row["called_at"] == call.called_at and row["called_at"].endswith("Z")
    assert row["input_ids"] == ["A4", "m3@1"] and row["raw_output"] == '{"ops": []}'
    assert (row["provider"], row["model"], row["family"], row["prompt_hash"]) == ("harness", "claude-test-1", "claude", "ph-1")
    assert (row["tokens_in"], row["tokens_out"], row["cost"], row["status"]) == (1200, 80, 0.0, "ok")
    assert row["run_id"] == run and row["job_id"] == jid
    columns = {r["name"] for r in store.conn.execute("PRAGMA table_info(model_call)")}
    assert not columns & {"prompt", "prompt_text", "input", "input_text", "messages"}


def test_input_ids_that_look_like_assembled_text_are_refused(store):
    for bad in (["please extract decisions from this chat"], ["x" * 201], [""]):
        with pytest.raises(ValueError):
            store.record_call(make_call(input_ids=bad))
    assert store.conn.execute("SELECT COUNT(*) FROM model_call").fetchone()[0] == 0


def test_a_failed_call_is_recorded_without_output(store, run):
    cid = store.record_call(make_call(run_id=run, raw_output=None, tokens_out=None, status="timeout"))
    row = store.get_call(cid)
    assert row["status"] == "timeout" and row["raw_output"] is None and row["tokens_out"] is None


def test_record_call_refuses_bad_input(store):
    with pytest.raises(ValueError):
        store.record_call(make_call(prompt_hash=""))
    with pytest.raises(KeyError):
        store.record_call(make_call(run_id="nope"))
    with pytest.raises(KeyError):
        store.record_call(make_call(job_id="nope"))
    with pytest.raises(sqlite3.IntegrityError):
        store.record_call(make_call(status="weird"))  # type: ignore[arg-type]
    with pytest.raises(sqlite3.IntegrityError):
        store.record_call(make_call(cost=-1.0))


def test_a_call_id_is_recorded_once(store):
    call = make_call()
    store.record_call(call)
    with pytest.raises(sqlite3.IntegrityError):
        store.record_call(call)


def test_calls_by_run_and_recorded_output_by_prompt_hash(store, run):
    other = store.start_run("idle")
    first = store.record_call(make_call(run_id=run, raw_output="first"))
    store.record_call(make_call(run_id=run, prompt_hash="ph-err", raw_output=None, status="error"))
    latest = store.record_call(make_call(run_id=other, raw_output="second"))
    assert [c["id"] for c in store.calls(run)][0] == first and len(store.calls(run)) == 2
    assert store.recorded_call("ph-1", run_id=run)["id"] == first
    assert store.recorded_call("ph-1")["id"] == latest
    assert store.recorded_call("ph-err") is None  # only a call that worked is reused
    assert store.recorded_call("ph-none") is None
    assert store.get_call("nope") is None


# --- proposals and verdicts ---


@pytest.fixture
def proposal(make_envelope, run):
    ops = [make_envelope("item.value_changed", draft=True), make_envelope("item.checked", draft=True)]
    quote = EvidenceQuote("A4", 5, 79, "keep 1-minute readings for 7 days")
    verdict = Verdict("code", ["scope", "attribution"], "pass", True)
    p = Proposal.build(run, ops, evidence=[quote], inputs=["m3@1"], abstentions=["no clear owner for m8"])
    p.verdicts.append(verdict)
    return p


def test_save_and_load_a_proposal(store, run, proposal):
    store.save_proposal(proposal)
    row = store.get_proposal(proposal.proposal_id)
    assert row["state"] == "pending" and row["run_id"] == run and row["risk_tier"] == proposal.risk_tier
    assert [op["type"] for op in row["ops"]] == ["item.value_changed", "item.checked"]
    assert row["evidence"] == [{"message_id": "A4", "start_char": 5, "end_char": 79, "quote": "keep 1-minute readings for 7 days"}]
    assert row["abstentions"] == ["no clear owner for m8"] and row["inputs"] == ["m3@1"]
    assert store.load_proposal(proposal.proposal_id) == proposal


def test_proposal_tier_is_stored(store, run, make_envelope):
    p = Proposal.build(run, [make_envelope("supersession.applied", draft=True)])
    assert p.risk_tier == "high"
    store.save_proposal(p)
    assert store.get_proposal(p.proposal_id)["risk_tier"] == "high"


def test_saving_a_proposal_twice_changes_nothing(store, run, proposal):
    store.save_proposal(proposal)
    store.set_proposal_state(proposal.proposal_id, "applied")
    store.save_proposal(proposal)
    assert store.get_proposal(proposal.proposal_id)["state"] == "applied"
    assert len(store.proposals(run)) == 1 and len(store.verdicts(proposal.proposal_id)) == 1


def test_save_proposal_with_a_job(store, run, proposal):
    jid = store.enqueue(run, "extract", "k")
    store.save_proposal(proposal, job_id=jid)
    assert store.get_proposal(proposal.proposal_id)["job_id"] == jid
    with pytest.raises(KeyError):
        store.save_proposal(Proposal.build(run, [], proposal_id="p2"), job_id="nope")


def test_save_proposal_needs_its_run(store, make_envelope):
    p = Proposal.build("no-such-run", [make_envelope("item.checked", draft=True)])
    with pytest.raises(KeyError):
        store.save_proposal(p)
    assert store.get_proposal(p.proposal_id) is None


def test_verdicts_are_kept_with_the_proposal(store, run, proposal):
    store.save_proposal(proposal)
    [v] = store.verdicts(proposal.proposal_id)
    assert (v["checker_family"], v["rules"], v["outcome"], v["independent"]) == ("code", ["scope", "attribution"], "pass", 1)
    assert v["id"] == proposal.verdicts[0].id


def test_record_a_later_verdict(store, run, proposal):
    store.save_proposal(proposal)
    call = store.record_call(make_call(run_id=run, family="openai"))
    later = Verdict("openai", ["meaning both ways", "hedge"], "fail", False, model_call_id=call)
    vid = store.record_verdict(proposal.proposal_id, later)
    assert vid == later.id
    verdicts = store.verdicts(proposal.proposal_id)
    assert [v["checker_family"] for v in verdicts] == ["code", "openai"]
    assert verdicts[1]["outcome"] == "fail" and verdicts[1]["independent"] == 0 and verdicts[1]["model_call_id"] == call
    assert [v.passed for v in store.load_proposal(proposal.proposal_id).verdicts] == [True, False]
    with pytest.raises(KeyError):
        store.record_verdict("nope", later)


def test_verdict_notes_are_stored(store, run, proposal):
    proposal.verdicts[0].notes = "checked twice"
    store.save_proposal(proposal)
    assert store.load_proposal(proposal.proposal_id).verdicts[0].notes == "checked twice"


def test_proposal_states(store, run, proposal):
    store.save_proposal(proposal)
    for state in ("quarantined", "requeued", "rejected", "applied"):
        store.set_proposal_state(proposal.proposal_id, state)
        assert store.get_proposal(proposal.proposal_id)["state"] == state
    assert [p["id"] for p in store.proposals(run, "applied")] == [proposal.proposal_id]
    assert store.proposals(run, "pending") == []
    with pytest.raises(ValueError):
        store.set_proposal_state(proposal.proposal_id, "pending")  # type: ignore[arg-type]
    with pytest.raises(KeyError):
        store.set_proposal_state("nope", "applied")
    assert store.get_proposal("nope") is None and store.load_proposal("nope") is None


# --- quarantine ---


def test_quarantine_sets_a_target_aside(store):
    qid = store.quarantine("proposal", "p1", "the checker disagreed", "2026-03-09T09:00:00.000Z")
    row = store.get_quarantine(qid)
    assert is_ulid(qid) and (row["target_kind"], row["target_id"], row["reason"]) == ("proposal", "p1", "the checker disagreed")
    assert (row["attempts"], row["state"], row["exit"], row["deadline"]) == (1, "open", None, "2026-03-09T09:00:00.000Z")
    assert [q["id"] for q in store.quarantines()] == [qid]


def test_a_repeat_adds_an_attempt_up_to_three(store):
    dl = "2026-03-09T09:00:00.000Z"
    qid = store.quarantine("item", "m5", "first", dl)
    assert store.quarantine("item", "m5", "second", "2030-01-01T00:00:00.000Z") == qid
    row = store.get_quarantine(qid)
    assert row["attempts"] == 2 and row["reason"] == "second" and row["deadline"] == dl  # the clock is not restarted
    assert store.quarantine("item", "m5", "third", dl) == qid
    assert store.get_quarantine(qid)["attempts"] == 3 and store.get_quarantine(qid)["state"] == "open"
    assert len(store.quarantines(None)) == 1


def test_a_fourth_repeat_discards_it(store):
    dl = "2026-03-09T09:00:00.000Z"
    qid = store.quarantine("link", "l1", "r", dl)
    for _ in range(2):
        store.quarantine("link", "l1", "r", dl)
    assert store.quarantine("link", "l1", "r", dl) == qid
    row = store.get_quarantine(qid)
    assert (row["state"], row["exit"], row["attempts"]) == ("exited", "discarded", 3)
    assert store.quarantines() == []


def test_targets_are_quarantined_separately(store):
    dl = "2026-03-09T09:00:00.000Z"
    a = store.quarantine("proposal", "x", "r", dl)
    b = store.quarantine("item", "x", "r", dl)
    c = store.quarantine("proposal", "y", "r", dl)
    assert len({a, b, c}) == 3


@pytest.mark.parametrize("exit_", ["fresh_call", "re_extracted", "discarded", "applied"])
def test_quarantine_exits(store, exit_):
    qid = store.quarantine("proposal", "p1", "r", "2026-03-09T09:00:00.000Z")
    store.exit_quarantine(qid, exit_)
    row = store.get_quarantine(qid)
    assert (row["state"], row["exit"]) == ("exited", exit_)
    assert store.quarantines() == [] and [q["id"] for q in store.quarantines("exited")] == [qid]
    with pytest.raises(ValueError):
        store.exit_quarantine(qid, "discarded")  # it has exited already


def test_a_target_can_be_quarantined_again_after_it_exited(store):
    dl = "2026-03-09T09:00:00.000Z"
    first = store.quarantine("proposal", "p1", "r", dl)
    store.exit_quarantine(first, "re_extracted")
    second = store.quarantine("proposal", "p1", "r", dl)
    assert second != first and store.get_quarantine(second)["attempts"] == 1


def test_quarantine_refuses_bad_input(store):
    with pytest.raises(ValueError):
        store.quarantine("run", "r1", "why", "2026-03-09T09:00:00.000Z")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        store.quarantine("item", "m1", "  ", "2026-03-09T09:00:00.000Z")
    with pytest.raises(ValueError):
        store.exit_quarantine(store.quarantine("item", "m1", "r", "2026-03-09T09:00:00.000Z"), "forgotten")  # type: ignore[arg-type]
    with pytest.raises(KeyError):
        store.exit_quarantine("nope", "discarded")
    assert store.get_quarantine("nope") is None


def test_expired_quarantines_are_discarded(store):
    soon = store.quarantine("item", "m1", "r", "2026-03-05T00:00:00.000Z")
    later = store.quarantine("item", "m2", "r", "2026-03-09T00:00:00.000Z")
    done = store.quarantine("item", "m3", "r", "2026-03-01T00:00:00.000Z")
    store.exit_quarantine(done, "applied")
    assert store.expire_quarantines("2026-03-04T00:00:00.000Z") == []
    assert store.expire_quarantines("2026-03-05T00:00:00.000Z") == [soon]
    assert store.get_quarantine(soon)["exit"] == "discarded"
    assert store.get_quarantine(later)["state"] == "open"
    assert store.get_quarantine(done)["exit"] == "applied"  # an exit already taken is not overwritten
    assert store.expire_quarantines("2030-01-01T00:00:00.000Z") == [later]
    assert store.quarantines() == []


def test_open_quarantines_come_by_deadline(store):
    b = store.quarantine("item", "b", "r", "2026-03-09T00:00:00.000Z")
    a = store.quarantine("item", "a", "r", "2026-03-05T00:00:00.000Z")
    assert [q["id"] for q in store.quarantines()] == [a, b]


# --- error budgets ---


def test_a_new_change_type_has_no_budget_row(store):
    assert store.budget("merge") is None
    assert not store.is_frozen("merge")


def test_the_starting_error_budget_is_2_percent(store):
    assert store.freeze_above == 0.02 and runs.DEFAULT_ERROR_BUDGET == 0.02
    assert runs.error_budget_start({}) == 0.02
    assert runs.error_budget_start({"maintenance": {}}) == 0.02


def test_the_error_budget_is_read_from_the_config_if_present(isolated_home, open_all):
    from northstar_agent_memory import config

    assert runs.error_budget_start({"maintenance": {"error_budget": 0.05}}) == 0.05
    assert runs.error_budget_start({"maintenance": {"error_budget": 1}}) == 1.0
    for bad in (-0.1, 1.5, "2%", True):
        with pytest.raises(ValueError):
            runs.error_budget_start({"maintenance": {"error_budget": bad}})
    settings = config.settings_path()
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text("[maintenance]\nerror_budget = 0.1\n", encoding="utf-8")
    assert SQLiteRunStore(open_all["runs"]).freeze_above == 0.1
    assert SQLiteRunStore(open_all["runs"], freeze_above=0.03).freeze_above == 0.03


def test_audits_add_up_and_the_rate_is_errors_over_changes(store):
    row = store.record_audit("link_inferred", n=100, errors=1)
    assert (row["audited_n"], row["audited_errors"], row["frozen"]) == (100, 1, 0)
    assert row["audited_error_rate"] == pytest.approx(0.01)
    row = store.record_audit("link_inferred", n=100, errors=2)
    assert (row["audited_n"], row["audited_errors"]) == (200, 3)
    assert row["audited_error_rate"] == pytest.approx(0.015) and not row["frozen"]


def test_a_type_freezes_when_its_rate_passes_the_budget(store):
    store.record_audit("merge", n=100, errors=2)  # exactly 2%: not above
    assert not store.is_frozen("merge")
    row = store.record_audit("merge", n=1, errors=1)  # 3 of 101
    assert row["frozen"] == 1 and row["frozen_at"] is not None and store.is_frozen("merge")


def test_a_frozen_type_stays_frozen_and_keeps_its_freeze_time(store):
    first = store.record_audit("merge", n=20, errors=10)
    assert first["frozen"] == 1
    later = store.record_audit("merge", n=10000, errors=0)  # the rate falls below 2%
    assert later["audited_error_rate"] < 0.02
    assert later["frozen"] == 1 and later["frozen_at"] == first["frozen_at"]


def test_the_limit_can_be_given_per_call(store):
    assert not store.record_audit("a", n=20, errors=2, freeze_above=0.5)["frozen"]
    assert store.record_audit("b", n=20, errors=2, freeze_above=0.05)["frozen"]


def test_a_store_built_with_its_own_budget(open_all):
    s = SQLiteRunStore(open_all["runs"], freeze_above=0.2)
    assert not s.record_audit("x", n=10, errors=2)["frozen"]
    assert s.record_audit("x", n=0, errors=0)["frozen"] == 0
    assert s.record_audit("x", n=10, errors=4)["frozen"] == 1


def test_a_types_budgets_are_separate(store):
    store.record_audit("merge", n=20, errors=10)
    store.record_audit("evidence", n=20, errors=0)
    assert store.is_frozen("merge") and not store.is_frozen("evidence")


def test_an_audit_of_nothing(store):
    row = store.record_audit("evidence", n=0, errors=0)
    assert row["audited_n"] == 0 and row["audited_error_rate"] == 0 and not row["frozen"]


def test_audit_refuses_nonsense(store):
    for n, errors in ((5, 6), (-1, 0), (5, -1)):
        with pytest.raises(ValueError):
            store.record_audit("merge", n=n, errors=errors)
    with pytest.raises(ValueError):
        store.record_audit("", n=1, errors=0)


def test_a_sentinel_can_freeze_a_type(store):
    row = store.freeze("link_inferred")
    assert row["frozen"] == 1 and row["audited_n"] == 0 and store.is_frozen("link_inferred")
    store.record_audit("merge", n=100, errors=0)
    assert store.freeze("merge")["audited_n"] == 100


def test_thaw_needs_a_passing_test_run(store):
    store.record_audit("merge", n=20, errors=10)
    with pytest.raises(ValueError):
        store.thaw("merge", test_passed=False)
    assert store.is_frozen("merge")
    row = store.thaw("merge", test_passed=True)
    assert row["frozen"] == 0 and row["frozen_at"] is None
    assert (row["audited_n"], row["audited_errors"], row["audited_error_rate"]) == (0, 0, 0)
    assert not store.record_audit("merge", n=100, errors=1)["frozen"]  # the old errors do not freeze it again
    with pytest.raises(KeyError):
        store.thaw("never-audited", test_passed=True)


# --- change log ---


def test_log_change_keeps_one_plain_line_with_its_undo(store, run):
    cid = store.log_change(run, "supersession", "Replaced the 7-day rule with the 14-day rule: you said so on 9 March", ["e1", "e2"], undo_handle="undo:s1")
    [row] = store.read_change_log(run)
    assert row["id"] == cid and row["run_id"] == run and row["change_type"] == "supersession"
    assert row["line"].startswith("Replaced the 7-day rule") and row["event_ids"] == ["e1", "e2"]
    assert row["undo_handle"] == "undo:s1" and row["undone_at"] is None and row["at"].endswith("Z")


def test_a_change_with_nothing_to_undo(store, run):
    store.log_change(run, "evidence", "Added a quote to m3", ["e1"])
    assert store.read_change_log(run)[0]["undo_handle"] is None


def test_the_log_reads_in_order_and_by_run(store, run):
    other = store.start_run("idle")
    a = store.log_change(run, "evidence", "one", [])
    b = store.log_change(other, "evidence", "two", [])
    c = store.log_change(run, "refresh", "three", [])
    assert [r["id"] for r in store.read_change_log()] == [a, b, c]
    assert [r["id"] for r in store.read_change_log(run)] == [a, c]


def test_log_change_refuses_bad_input(store, run):
    with pytest.raises(ValueError):
        store.log_change(run, "evidence", "  ", [])
    with pytest.raises(KeyError):
        store.log_change("nope", "evidence", "line", [])


def test_the_log_is_append_only_and_undo_is_marked_once(store, run):
    cid = store.log_change(run, "merge", "Merged m5 into m3", ["e9"], undo_handle="undo:merge-1")
    store.mark_undone(cid, at="2026-03-03T00:00:00.000Z")
    assert store.read_change_log(run)[0]["undone_at"] == "2026-03-03T00:00:00.000Z"
    with pytest.raises(ValueError):
        store.mark_undone(cid)
    with pytest.raises(KeyError):
        store.mark_undone("nope")
    public = {n for n in dir(SQLiteRunStore) if not n.startswith("_")}
    assert not {n for n in public if "change" in n and any(w in n for w in ("delete", "remove", "edit", "update", "rewrite"))}


def test_the_change_log_has_one_read_and_nothing_else_calls_it():
    """I7: only the user's view and audits read the log. The store's own methods never do."""
    import inspect

    source = inspect.getsource(SQLiteRunStore)
    assert source.count("read_change_log") == 1  # its own definition only


# --- tenants, reopening ---


def test_every_table_row_carries_the_tenant(store, run):
    jid = store.enqueue(run, "extract", "k")
    assert store.get_run(run)["tenant_id"] == "local" and store.get_job(jid)["tenant_id"] == "local"


def test_another_tenant_sees_nothing(open_all, run):
    other = SQLiteRunStore(open_all["runs"], tenant_id="acme")
    assert other.get_run(run) is None and other.runs() == []
    with pytest.raises(KeyError):
        other.enqueue(run, "extract", "k")
    own = other.start_run("manual")
    assert other.get_run(own)["tenant_id"] == "acme"
    other.enqueue(own, "extract", "k2")
    assert other.lease("w", ["extract"], 60).run_id == own
    assert SQLiteRunStore(open_all["runs"]).lease("w", ["extract"], 60) is None


def test_state_survives_reopening(store_root):
    s = SQLiteRunStore.open(store_root)
    r = s.start_run("weekly")
    jid = s.enqueue(r, "weekly", "k")
    s.lease("w", ["weekly"], 60, now=T0)
    s.close()
    again = SQLiteRunStore.open(store_root)
    assert again.get_job(jid)["state"] == "leased"
    assert again.lease("w2", ["weekly"], 60, now="2026-03-02T10:00:00.000Z").attempts == 2
    again.close()


# --- review fixes ---


def test_times_without_milliseconds_compare_by_time_not_by_text(store, run):
    jid = store.enqueue(run, "extract", "k")
    store.lease("w1", ["extract"], 60, now=T0)  # until 09:01:00.000Z
    assert store.lease("w2", ["extract"], 60, now="2026-03-02T09:00:30Z") is None  # "…30Z" sorts after "…00.000Z" as text
    assert store.lease("w2", ["extract"], 60, now="2026-03-02T09:01:00Z").id == jid
    q = store.quarantine("item", "m1", "r", "2026-03-05T00:00:00Z")
    assert store.get_quarantine(q)["deadline"] == "2026-03-05T00:00:00.000Z"
    assert store.expire_quarantines("2026-03-04T23:59:59Z") == []
    assert store.expire_quarantines("2026-03-05T00:00:00Z") == [q]


def test_an_applied_proposal_does_not_change_state(store, run, proposal):
    store.save_proposal(proposal)
    store.set_proposal_state(proposal.proposal_id, "applied")
    store.set_proposal_state(proposal.proposal_id, "applied")
    for state in ("rejected", "quarantined", "requeued"):
        with pytest.raises(ValueError):
            store.set_proposal_state(proposal.proposal_id, state)
    assert store.get_proposal(proposal.proposal_id)["state"] == "applied"


# --- hardening: the starting values come from the config (I19) ---


def _cfg(**values) -> dict:
    return {"maintenance": values}


def test_the_shipped_config_has_a_maintenance_block_with_the_starting_values():
    from northstar_agent_memory import config

    block = config.defaults()["maintenance"]
    assert block["quarantine_attempts"] == runs.MAX_QUARANTINE_ATTEMPTS == 3
    assert block["quarantine_days"] == runs.QUARANTINE_DAYS == 7
    assert block["error_budget"] == runs.DEFAULT_ERROR_BUDGET == 0.02
    assert block["error_budget_min_sample"] == runs.ERROR_BUDGET_MIN_SAMPLE == 20
    assert block["max_job_attempts"] == runs.MAX_JOB_ATTEMPTS == 3
    assert block["idle_trigger_minutes"] == runs.IDLE_TRIGGER_MINUTES == 30
    assert block["loss_bound"] == 0.05
    assert runs.RunSettings.from_config(config.defaults()) == runs.RunSettings()


def test_a_missing_key_falls_back_to_the_same_number():
    assert runs.RunSettings.from_config({}) == runs.RunSettings()
    assert runs.RunSettings.from_config(_cfg(error_budget=0.1)).error_budget == 0.1
    assert runs.RunSettings.from_config(_cfg(error_budget=0.1)).max_job_attempts == 3


@pytest.mark.parametrize(
    "key, bad",
    [
        ("quarantine_attempts", 0), ("quarantine_attempts", 4), ("quarantine_attempts", 1.5), ("quarantine_attempts", True),
        ("quarantine_days", 0), ("quarantine_days", -1), ("quarantine_days", "7"),
        ("max_job_attempts", 0), ("max_job_attempts", 2.5),
        ("error_budget", -0.1), ("error_budget", 1.5),
        ("error_budget_min_sample", -1), ("error_budget_min_sample", 1.5),
        ("idle_trigger_minutes", 0),
    ],
)
def test_a_bad_maintenance_value_is_refused(key, bad):
    with pytest.raises(ValueError, match=key):
        runs.RunSettings.from_config(_cfg(**{key: bad}))


def test_the_store_reads_its_settings_from_the_user_config(isolated_home, open_all):
    from northstar_agent_memory import config

    settings = config.settings_path()
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text("[maintenance]\nmax_job_attempts = 2\nquarantine_days = 3\nerror_budget_min_sample = 5\n", encoding="utf-8")
    s = SQLiteRunStore(open_all["runs"])
    assert (s.settings.max_job_attempts, s.settings.quarantine_days, s.min_sample) == (2, 3, 5)
    assert s.default_deadline("2026-03-02T09:00:00.000Z") == "2026-03-05T09:00:00.000Z"
    assert runs.default_deadline("2026-03-02T09:00:00.000Z") == "2026-03-05T09:00:00.000Z"
    assert runs.default_deadline("2026-03-02T09:00:00.000Z", {}) == "2026-03-09T09:00:00.000Z"


def test_a_quarantine_without_a_deadline_gets_the_default_one(store):
    qid = store.quarantine("item", "m1", "unclear")
    assert store.get_quarantine(qid)["deadline"] > utc_now()


def test_the_quarantine_attempts_come_from_the_config(open_all):
    s = SQLiteRunStore(open_all["runs"], config=_cfg(quarantine_attempts=1))
    qid = s.quarantine("item", "m1", "first", "2999-01-01T00:00:00.000Z")
    assert s.get_quarantine(qid)["state"] == "open"
    s.quarantine("item", "m1", "second", "2999-01-01T00:00:00.000Z")  # one attempt was all it had
    assert s.get_quarantine(qid)["exit"] == "discarded"


# --- hardening: an attempt cap on jobs, and the running and quarantined states ---


def test_a_job_leased_too_often_is_quarantined_not_leased_again(store, run):
    """The attack: a job whose worker keeps dying was leased for ever; it had no cap."""
    jid = store.enqueue(run, "extract", "k")
    for n in range(3):  # three attempts, each lease running out
        assert store.lease("w", ["extract"], 60, now=f"2026-03-02T0{n}:00:00.000Z").attempts == n + 1
    assert store.lease("w", ["extract"], 60, now="2026-03-02T09:00:00.000Z") is None
    row = store.get_job(jid)
    assert row["state"] == "quarantined" and row["attempts"] == 3 and row["lease_owner"] is None and row["lease_until"] is None
    assert "quarantined after 3 attempts" in row["error"]
    assert [j["id"] for j in store.jobs(run, "quarantined")] == [jid]
    assert store.lease("w", ["extract"], 60, now="2030-01-01T00:00:00.000Z") is None  # and it stays set aside


def test_the_cap_skips_to_the_next_job(store, run):
    a = store.enqueue(run, "extract", "k1")
    b = store.enqueue(run, "extract", "k2")
    for n in range(3):  # the oldest job is leased three times, its lease running out each time
        assert store.lease("w", ["extract"], 10, now=f"2026-03-02T0{n}:00:00.000Z").id == a
    got = store.lease("w2", ["extract"], 10, now="2026-03-02T09:00:00.000Z")
    assert got.id == b and got.attempts == 1  # a is set aside and the next job is leased
    assert store.get_job(a)["state"] == "quarantined" and store.get_job(b)["state"] == "leased"


def test_a_retry_with_no_attempts_left_quarantines_the_job(store, run):
    jid = store.enqueue(run, "extract", "k")
    for n in range(2):
        store.lease("w", ["extract"], 60, now=T0)
        assert store.fail(jid, f"timeout {n}", retry=True) == "queued"
    assert store.lease("w", ["extract"], 60, now=T0).attempts == 3
    assert store.fail(jid, "timeout again", retry=True) == "quarantined"
    row = store.get_job(jid)
    assert row["state"] == "quarantined" and row["error"] == "quarantined after 3 attempts: timeout again"
    assert store.lease("w", ["extract"], 60, now="2030-01-01T00:00:00.000Z") is None


def test_fail_says_what_became_of_the_job(store, run):
    a, b = store.enqueue(run, "extract", "k1"), store.enqueue(run, "extract", "k2")
    store.lease("w", ["extract"], 60, now=T0)
    store.lease("w", ["extract"], 60, now=T0)
    assert store.fail(a, "retry me", retry=True) == "queued"
    assert store.fail(b, "give up", retry=False) == "failed"


def test_the_attempt_cap_comes_from_the_config(open_all):
    s = SQLiteRunStore(open_all["runs"], config=_cfg(max_job_attempts=1))
    r = s.start_run("manual")
    jid = s.enqueue(r, "extract", "k")
    assert s.lease("w", ["extract"], 60, now=T0).attempts == 1
    assert s.fail(jid, "boom", retry=True) == "quarantined"
    wide = SQLiteRunStore(open_all["runs"], config=_cfg(max_job_attempts=5))
    again = wide.enqueue(r, "extract", "k2")
    for n in range(4):
        assert wide.lease("w", ["extract"], 10, now=f"2026-03-02T0{n}:00:00.000Z").id == again
    assert wide.lease("w", ["extract"], 10, now="2026-03-02T05:00:00.000Z").attempts == 5


def test_a_leased_job_can_be_marked_running(store, run):
    jid = store.enqueue(run, "extract", "k")
    with pytest.raises(ValueError):
        store.mark_running(jid)  # nobody leased it
    store.lease("w1", ["extract"], 60, now=T0)
    with pytest.raises(LeaseLost):
        store.mark_running(jid, owner="w2")
    store.mark_running(jid, owner="w1")
    assert store.get_job(jid)["state"] == "running"
    store.mark_running(jid, owner="w1")  # saying so again changes nothing
    assert store.lease("w2", ["extract"], 60, now="2026-03-02T09:00:30.000Z") is None  # still leased
    again = store.lease("w2", ["extract"], 60, now="2026-03-02T09:01:00.000Z")  # a running job's lease runs out too
    assert again.id == jid and again.attempts == 2
    store.mark_running(jid, owner="w2")
    store.complete(jid, owner="w2")
    assert store.get_job(jid)["state"] == "done"


def test_a_running_job_can_fail_and_retry(store, run):
    jid = store.enqueue(run, "extract", "k")
    store.lease("w1", ["extract"], 60, now=T0)
    store.mark_running(jid)
    assert store.fail(jid, "model error", retry=True, owner="w1") == "queued"


# --- hardening: the error budget freezes only after a minimum audited sample ---


def test_one_early_miss_does_not_freeze_a_type(store):
    """The attack: a first audit of 1 error in 5 changes (20%) froze the type for good."""
    row = store.record_audit("merge", n=5, errors=1)
    assert not row["frozen"] and row["audited_error_rate"] == pytest.approx(0.2)
    assert not store.is_frozen("merge")
    row = store.record_audit("merge", n=14, errors=0)  # 19 audited: still under the minimum
    assert not row["frozen"]
    row = store.record_audit("merge", n=1, errors=0)  # 20 audited, 1 error: 5% is above 2%
    assert row["frozen"] == 1 and row["frozen_at"] is not None


def test_a_sample_at_the_minimum_within_budget_stays_thawed(store):
    assert not store.record_audit("merge", n=50, errors=1)["frozen"]  # exactly 2%


def test_the_minimum_sample_can_be_given_per_call_or_per_store(store, open_all):
    assert store.record_audit("a", n=5, errors=5, min_sample=5)["frozen"]
    assert not store.record_audit("b", n=5, errors=5, min_sample=6)["frozen"]
    quick = SQLiteRunStore(open_all["runs"], min_sample=1)
    assert quick.record_audit("c", n=1, errors=1)["frozen"]
    configured = SQLiteRunStore(open_all["runs"], config=_cfg(error_budget_min_sample=3, error_budget=0.5))
    assert not configured.record_audit("d", n=2, errors=2)["frozen"]
    assert configured.record_audit("d", n=1, errors=0)["frozen"]  # 3 audited, 2 wrong
    for bad in (-1, 1.5, True):
        with pytest.raises(ValueError):
            SQLiteRunStore(open_all["runs"], min_sample=bad)  # type: ignore[arg-type]


def test_a_sentinel_freeze_does_not_wait_for_a_sample(store):
    assert store.freeze("link_inferred")["frozen"] == 1


# --- hardening: verdicts are recorded here, and what they say about themselves is checked ---


def test_a_verdict_names_the_call_of_its_own_family(store, run, proposal):
    """The attack: a verdict said 'openai' but named a claude call (or a call of another run); it was stored as is."""
    store.save_proposal(proposal)
    claude_call = store.record_call(make_call(run_id=run, family="claude"))
    forged = Verdict("openai", list(("meaning_both_ways", "attribution", "scope", "hedge")), "pass", True, model_call_id=claude_call)
    with pytest.raises(ValueError, match="claude"):
        store.record_verdict(proposal.proposal_id, forged)
    assert len(store.verdicts(proposal.proposal_id)) == 1  # only the code verdict that came with it


def test_a_verdict_cannot_name_a_call_of_another_run(store, run, proposal):
    store.save_proposal(proposal)
    other = store.start_run("idle")
    elsewhere = store.record_call(make_call(run_id=other, family="openai"))
    with pytest.raises(ValueError, match="not made in run"):
        store.record_verdict(proposal.proposal_id, Verdict("openai", ["scope"], "pass", True, model_call_id=elsewhere))
    nowhere = store.record_call(make_call(run_id=None, family="openai", prompt_hash="ph-free"))
    with pytest.raises(ValueError, match="not made in run"):
        store.record_verdict(proposal.proposal_id, Verdict("openai", ["scope"], "pass", True, model_call_id=nowhere))


def test_a_verdict_cannot_rest_on_a_call_that_did_not_finish(store, run, proposal):
    store.save_proposal(proposal)
    broken = store.record_call(make_call(run_id=run, family="openai", raw_output=None, status="timeout", prompt_hash="ph-t"))
    with pytest.raises(ValueError, match="did not finish"):
        store.record_verdict(proposal.proposal_id, Verdict("openai", ["scope"], "pass", True, model_call_id=broken))


def test_a_verdict_naming_a_call_that_is_not_recorded_is_refused(store, run, proposal):
    store.save_proposal(proposal)
    with pytest.raises(KeyError):
        store.record_verdict(proposal.proposal_id, Verdict("openai", ["scope"], "pass", True, model_call_id="no-such-call"))


def test_a_proposal_cannot_smuggle_forged_verdicts_in_through_save(store, run, make_envelope):
    """The attack: Proposal.verdicts was stored as recorded fact. Now each is checked, and a bad one stores nothing."""
    claude_call = store.record_call(make_call(run_id=run, family="claude"))
    made = Proposal.build(run, [make_envelope("item.checked", draft=True)])
    made.verdicts = [Verdict("code", ["scope"], "pass", True), Verdict("openai", ["scope"], "pass", True, model_call_id=claude_call)]
    with pytest.raises(ValueError):
        store.save_proposal(made)
    assert store.get_proposal(made.proposal_id) is None and store.verdicts_for(made.proposal_id) == []


def test_verdicts_for_returns_what_was_recorded(store, run, proposal):
    store.save_proposal(proposal)
    call = store.record_call(make_call(run_id=run, family="openai", prompt_hash="ph-v"))
    mine = Verdict("openai", ["meaning_both_ways", "hedge"], "pass", False, model_call_id=call, notes="no other family was left")
    store.record_verdict(proposal.proposal_id, mine)
    code, checked = store.verdicts_for(proposal.proposal_id)
    assert isinstance(checked, Verdict) and code.checker_family == "code"
    assert (checked.checker_family, checked.model_call_id, checked.outcome) == ("openai", call, "pass")
    assert checked.independent is False  # the 'not independent' label is kept
    assert checked.rules == ["meaning_both_ways", "hedge"] and checked.notes == "no other family was left" and checked.id == mine.id
    assert store.verdicts(proposal.proposal_id)[1]["independent"] == 0
    assert store.verdicts_for("nope") == []


def test_a_verdict_id_is_recorded_once_and_the_same_verdict_again_adds_nothing(store, run, proposal):
    store.save_proposal(proposal)
    call = store.record_call(make_call(run_id=run, family="openai", prompt_hash="ph-v"))
    v = Verdict("openai", ["scope"], "pass", True, model_call_id=call)
    assert store.record_verdict(proposal.proposal_id, v) == v.id
    assert store.record_verdict(proposal.proposal_id, v) == v.id
    assert len(store.verdicts_for(proposal.proposal_id)) == 2
    flipped = Verdict("openai", ["scope"], "fail", True, model_call_id=call, id=v.id)
    with pytest.raises(ValueError, match="recorded already"):
        store.record_verdict(proposal.proposal_id, flipped)  # the old code ignored this one silently
    other = Proposal.build(run, [], proposal_id="p-other")
    store.save_proposal(other)
    with pytest.raises(ValueError, match="recorded already"):
        store.record_verdict("p-other", v)
    assert [x.outcome for x in store.verdicts_for(proposal.proposal_id)] == ["pass", "pass"]


def test_a_verdict_without_a_call_is_stored_but_names_nothing(store, run, proposal):
    store.save_proposal(proposal)
    store.record_verdict(proposal.proposal_id, Verdict("openai", ["scope"], "pass", True))
    last = store.verdicts_for(proposal.proposal_id)[-1]
    assert last.model_call_id is None and last.checker_family == "openai"  # the gate counts a verdict only with a call


def test_a_verdict_needs_an_outcome_and_a_family(store, run, proposal):
    store.save_proposal(proposal)
    for bad in (Verdict("openai", [], "maybe", True), Verdict("", [], "pass", True)):  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            store.record_verdict(proposal.proposal_id, bad)


def test_runs_db_keeps_verdicts_and_calls_final(store, run, proposal):
    store.save_proposal(proposal)
    call = store.record_call(make_call(run_id=run, family="openai", prompt_hash="ph-f"))
    v = Verdict("openai", ["scope"], "pass", True, model_call_id=call)
    store.record_verdict(proposal.proposal_id, v)
    with pytest.raises(sqlite3.DatabaseError):
        store.conn.execute("UPDATE verdict SET outcome = 'pass' WHERE id = ?", (v.id,))
    with pytest.raises(sqlite3.DatabaseError):
        store.conn.execute("DELETE FROM model_call WHERE id = ?", (call,))


def test_two_tenants_may_use_the_same_ids(open_all):
    a, b = SQLiteRunStore(open_all["runs"]), SQLiteRunStore(open_all["runs"], tenant_id="acme")
    ra, rb = a.start_run("manual"), b.start_run("manual")
    assert a.enqueue(ra, "extract", "same-key") != b.enqueue(rb, "extract", "same-key")
    assert a.lease("w", ["extract"], 60).run_id == ra and b.lease("w", ["extract"], 60).run_id == rb


def test_calls_for_job_lists_every_call_recorded_under_a_job_whatever_its_status(store):
    run = store.start_run("manual")
    job = store.enqueue(run, "extract", "k-calls")
    other = store.enqueue(run, "check", "k-other")
    a = store.record_call(ModelCall("p", "m", "claude", "h1", ["S1:0"], run_id=run, job_id=job, raw_output="{}"))
    b = store.record_call(ModelCall("p", "m", "claude", "h2", ["S1:0"], run_id=run, job_id=job, status="error"))
    store.record_call(ModelCall("p", "m", "openai", "h3", ["S1:0"], run_id=run, job_id=other, raw_output="{}"))
    assert sorted(c["id"] for c in store.calls_for_job(job)) == sorted([a, b])
    assert store.calls_for_job("no-such-job") == []
