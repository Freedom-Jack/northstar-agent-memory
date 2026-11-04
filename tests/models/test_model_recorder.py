import hashlib
import json
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

import model_fakes as f
from northstar_agent_memory.models.budget import billed_result, resolve_model
from northstar_agent_memory.models.harness import HarnessResult
from northstar_agent_memory.models.port import ModelError, ModelRefused, ModelResult, Usage
from northstar_agent_memory.models.recorder import RecordingPort, request_key
from northstar_agent_memory.models.stub import StubModel


class Counting:
    """An inner port that counts live calls."""

    def __init__(self, handler=None):
        self.stub = StubModel(handler)

    @property
    def n(self):
        return len(self.stub.calls)

    def complete(self, req):
        result = self.stub.complete(req)
        result.cost_usd = 0.25
        return result


def port(tmp_path, inner, mode="record", **kw):
    return RecordingPort(inner, tmp_path / "rec.sqlite", mode=mode, **kw)


def test_miss_then_hit(tmp_path):
    inner = Counting()
    rec = port(tmp_path, inner)
    req = f.make_req(family="stub")
    first = rec.complete(req)
    second = rec.complete(req)
    assert inner.n == 1
    assert not first.from_record and second.from_record
    assert second.text == first.text and second.usage == first.usage and second.cost_usd == 0.25
    assert isinstance(second.usage, Usage) and rec.count() == 1


def test_hit_survives_a_new_port_object(tmp_path):
    inner = Counting()
    port(tmp_path, inner).complete(f.make_req())
    assert port(tmp_path, inner).complete(f.make_req()).from_record
    assert inner.n == 1


def test_purpose_and_metadata_not_in_key_but_sample_is(tmp_path):
    inner = Counting()
    rec = port(tmp_path, inner)
    rec.complete(f.make_req(purpose="a", metadata={"x": 1}))
    assert rec.complete(f.make_req(purpose="b", metadata={"x": 2})).from_record
    assert not rec.complete(f.make_req(sample=1)).from_record
    assert inner.n == 2


@pytest.mark.parametrize(
    "change",
    [
        {"system": "other"},
        {"messages": [{"role": "user", "content": "bye"}]},
        {"schema": f.SCHEMA},
        {"max_tokens": 10},
        {"effort": "high"},
        {"sample": 2},
        {"family": "openai"},
        {"allow_fallback": False},
    ],
)
def test_every_input_changes_the_key(change):
    assert request_key(f.make_req(), "m") != request_key(f.make_req(**change), "m")


def test_key_is_stable_and_order_insensitive():
    a = f.make_req(schema={"type": "object", "properties": {}, "required": [], "additionalProperties": False})
    b = f.make_req(schema={"additionalProperties": False, "required": [], "properties": {}, "type": "object"})
    assert request_key(a, "m") == request_key(b, "m")
    assert len(request_key(a, "m")) == 64
    assert request_key(a, "m") != request_key(a, "m2")


def test_config_model_change_is_a_different_key(tmp_path, config):
    inner = Counting()
    rec = port(tmp_path, inner, resolver=lambda req: resolve_model(config, req))
    req = f.make_req()
    rec.complete(req)
    assert rec.complete(req).from_record
    config["models"]["anthropic"]["judge"] = "claude-sonnet-5-5"
    assert not rec.complete(req).from_record
    assert inner.n == 2
    # an explicit req.model overrides config
    assert rec.complete(f.make_req(model="claude-sonnet-5-5")).from_record


def test_replay_miss_raises_and_hit_returns(tmp_path):
    inner = Counting()
    port(tmp_path, inner).complete(f.make_req())
    replay = port(tmp_path, inner, mode="replay")
    assert replay.complete(f.make_req()).from_record
    with pytest.raises(ModelError, match="no recording"):
        replay.complete(f.make_req(system="new"))
    assert inner.n == 1


def test_live_always_calls_and_replaces(tmp_path):
    inner = Counting(lambda req: f"answer {len(inner.stub.calls)}")
    port(tmp_path, inner).complete(f.make_req())
    live = port(tmp_path, inner, mode="live")
    assert live.complete(f.make_req()).text == "answer 2"
    assert live.complete(f.make_req()).text == "answer 3"
    assert port(tmp_path, inner, mode="replay").complete(f.make_req()).text == "answer 3"


def test_will_call_live(tmp_path):
    inner = Counting()
    rec = port(tmp_path, inner)
    req = f.make_req()
    assert rec.will_call_live(req)
    rec.complete(req)
    assert not rec.will_call_live(req)
    assert port(tmp_path, inner, mode="live").will_call_live(req)
    assert not port(tmp_path, inner, mode="replay").will_call_live(f.make_req(system="new"))


def test_request_copy_is_stored_for_audit(tmp_path):
    import json
    import sqlite3

    rec = port(tmp_path, Counting())
    rec.complete(f.make_req(purpose="audit.me", metadata={"item": 3}))
    row = sqlite3.connect(tmp_path / "rec.sqlite").execute("SELECT purpose, request_json, cost_usd FROM recordings").fetchone()
    request = json.loads(row[1])
    assert row[0] == "audit.me" and row[2] == 0.25
    assert request["system"] == "Be brief." and request["metadata"] == {"item": 3}


def test_wal_mode(tmp_path):
    import sqlite3

    port(tmp_path, Counting())
    assert sqlite3.connect(tmp_path / "rec.sqlite").execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_billed_refusal_is_recorded_and_replayed_as_refusal(tmp_path):
    billed = ModelResult("", None, Usage(10, 5), 0.5, 0.1, "anthropic", "m", "m", "refusal")

    class Refusing:
        n = 0

        def complete(self, req):
            self.n += 1
            err = ModelRefused("declined")
            err.result = billed
            raise err

    inner = Refusing()
    rec = port(tmp_path, inner)
    with pytest.raises(ModelRefused):
        rec.complete(f.make_req())
    with pytest.raises(ModelRefused, match="declined") as info:
        rec.complete(f.make_req())
    assert inner.n == 1
    assert billed_result(info.value).from_record


def test_errors_without_a_billed_result_are_not_recorded(tmp_path):
    class Down:
        def complete(self, req):
            raise ModelError("network")

    rec = port(tmp_path, Down())
    with pytest.raises(ModelError):
        rec.complete(f.make_req())
    assert rec.count() == 0


def test_bad_mode(tmp_path):
    with pytest.raises(ValueError):
        port(tmp_path, Counting(), mode="nope")


def test_threads_write_safely(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    rec = port(tmp_path, Counting())
    with ThreadPoolExecutor(8) as pool:
        list(pool.map(lambda i: rec.complete(f.make_req(sample=i)), range(40)))
    assert rec.count() == 40


def test_key_ignores_the_cache_flag_and_keeps_old_keys_when_fallback_is_on():
    base = f.make_req()
    assert request_key(base, "m") == request_key(f.make_req(cache=True), "m")
    assert request_key(base, "m") == request_key(f.make_req(allow_fallback=True), "m")
    # the key recorded before the new fields existed
    legacy = json.dumps(
        {"family": "anthropic", "model": "m", "system": "Be brief.", "messages": [{"role": "user", "content": "hello"}],
         "schema": None, "max_tokens": 4096, "effort": None, "sample": 0},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    )
    assert request_key(base, "m") == hashlib.sha256(legacy.encode("utf-8")).hexdigest()


class Slow:
    """An inner port whose first call waits until released, so a second thread can arrive meanwhile."""

    def __init__(self):
        self.calls = 0
        self.started = threading.Event()
        self.release = threading.Event()
        self._lock = threading.Lock()

    def complete(self, req):
        with self._lock:
            self.calls += 1
        self.started.set()
        assert self.release.wait(10)
        return ModelResult("slow", None, Usage(10, 5), 0.25, 0.1, "anthropic", "m", "m", "end_turn")


def test_same_uncached_request_from_two_threads_calls_live_once(tmp_path):
    inner = Slow()
    rec = port(tmp_path, inner)
    req = f.make_req()
    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(rec.complete, req)
        assert inner.started.wait(10)
        second = pool.submit(rec.complete, req)
        time.sleep(0.2)  # the second thread is now waiting on the first's lock
        assert inner.calls == 1 and not second.done()
        inner.release.set()
        a, b = first.result(10), second.result(10)
    assert inner.calls == 1 and rec.count() == 1
    assert not a.from_record and b.from_record
    assert a.text == b.text and b.cost_usd == 0.25
    assert rec._key_locks == {}


def test_waiting_thread_replays_a_billed_failure_too(tmp_path):
    billed = ModelResult("", None, Usage(10, 5), 0.5, 0.1, "anthropic", "m", "m", "refusal")
    started, release = threading.Event(), threading.Event()
    calls = []

    class Refusing:
        def complete(self, req):
            calls.append(1)
            started.set()
            release.wait(10)
            err = ModelRefused("declined")
            err.result = billed
            raise err

    rec = port(tmp_path, Refusing())
    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(rec.complete, f.make_req())
        assert started.wait(10)
        second = pool.submit(rec.complete, f.make_req())
        time.sleep(0.2)
        release.set()
        for future in (first, second):
            with pytest.raises(ModelRefused, match="declined"):
                future.result(10)
    assert len(calls) == 1


def test_different_keys_do_not_block_each_other(tmp_path):
    inner = Slow()
    rec = port(tmp_path, inner)
    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(rec.complete, f.make_req(sample=1))
        assert inner.started.wait(10)
        second = pool.submit(rec.complete, f.make_req(sample=2))
        deadline = time.monotonic() + 10
        while inner.calls < 2 and time.monotonic() < deadline:
            time.sleep(0.01)
        assert inner.calls == 2  # both are inside the inner port at once
        inner.release.set()
        first.result(10), second.result(10)
    assert rec.count() == 2


def test_a_failure_with_no_billed_result_lets_the_waiter_try_again(tmp_path):
    started, release = threading.Event(), threading.Event()
    calls = []

    class FlakyOnce:
        def complete(self, req):
            calls.append(1)
            if len(calls) == 1:
                started.set()
                release.wait(10)
                raise ModelError("network")
            return ModelResult("ok", None, Usage(1, 1), 0.1, 0.1, "anthropic", "m", "m", "end_turn")

    rec = port(tmp_path, FlakyOnce())
    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(rec.complete, f.make_req())
        assert started.wait(10)
        second = pool.submit(rec.complete, f.make_req())
        time.sleep(0.2)
        release.set()
        with pytest.raises(ModelError, match="network"):
            first.result(10)
        assert second.result(10).text == "ok"
    assert len(calls) == 2


def test_a_harness_result_is_stored_with_its_extra_field_and_replayed_as_a_plain_result(tmp_path):
    class Harnessed:
        n = 0

        def complete(self, req):
            self.n += 1
            return HarnessResult("t", None, Usage(10, 5), 0.0, 0.1, "anthropic", "m", "m", "end_turn", api_equivalent_usd=0.3)

    inner = Harnessed()
    rec = port(tmp_path, inner)
    first = rec.complete(f.make_req())
    assert isinstance(first, HarnessResult) and first.api_equivalent_usd == 0.3
    again = rec.complete(f.make_req())
    assert inner.n == 1 and again.from_record and type(again) is ModelResult  # the extra field is not part of the port's result
    assert again.text == "t" and again.usage == Usage(10, 5) and again.cost_usd == 0.0
    with sqlite3.connect(tmp_path / "rec.sqlite") as conn:
        (stored,) = conn.execute("SELECT result_json FROM recordings").fetchone()
    assert json.loads(stored)["api_equivalent_usd"] == 0.3  # but a recording keeps it, for audit


def test_a_harness_recording_never_replays_on_the_api_route_or_the_reverse():
    from northstar_agent_memory.models.port import ModelRequest
    from northstar_agent_memory.models.recorder import request_key

    req = ModelRequest(purpose="t", role="judge", family="anthropic", system="s", messages=[{"role": "user", "content": "q"}])
    api = request_key(req, "claude-opus-5-5")
    assert request_key(req, "claude-opus-5-5", "api") == api  # API keys are unchanged
    assert request_key(req, "claude-opus-5-5", "harness") != api
    stub = ModelRequest(purpose="t", role="judge", family="stub", system="s", messages=[{"role": "user", "content": "q"}])
    assert request_key(stub, "stub-judge", "harness") == request_key(stub, "stub-judge", "api")
