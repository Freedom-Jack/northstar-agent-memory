"""Baseline tests: a fake port returns scripted replies; nothing touches the network."""

from __future__ import annotations

import json
import re
import threading
from dataclasses import replace
from pathlib import Path

import pytest

from northstar_agent_memory.eval import baselines as B
from northstar_agent_memory.eval import longmemeval as L
from northstar_agent_memory.eval.tokens import estimate_tokens
from northstar_agent_memory.models.budget import attach
from northstar_agent_memory.models.port import ModelError, ModelRefused, ModelRequest, ModelResult, Usage
from northstar_agent_memory.models.schema import assert_strict

FIXTURE = Path(__file__).parent / "fixtures" / "lme_tiny.json"
ITEMS = {i.id: i for i in L.to_items(L.load(FIXTURE))}
USAGE = Usage(input_tokens=100, output_tokens=10)
REAL = L.default_path()  # read at import: tests move the data root, and this file is public


class FakePort:
    """Calls `handler(req)`; a dict or str reply becomes a ModelResult with fixed usage."""

    def __init__(self, handler):
        self.handler = handler
        self.requests: list[ModelRequest] = []
        self.lock = threading.Lock()

    def complete(self, req: ModelRequest) -> ModelResult:
        with self.lock:
            self.requests.append(req)
        reply = self.handler(req)
        parsed = reply if isinstance(reply, dict) else None
        text = json.dumps(reply) if parsed is not None else str(reply)
        return ModelResult(
            text=text, parsed=parsed, usage=USAGE, cost_usd=0.01, latency_s=0.5, family=req.family,
            model="fake-model", served_model="fake-served", stop_reason="end_turn",
        )

    def of(self, purpose: str) -> list[ModelRequest]:
        return [r for r in self.requests if r.purpose == purpose]


def answer_reply(answer="Teal", cited=()):
    return {"answer": answer, "cited": list(cited)}


def action(kind, **kw):
    base = {"action": kind, "pattern": None, "session_id": None, "start": None, "end": None, "answer": None, "cited": []}
    return {**base, **kw}


def context_of(req: ModelRequest) -> str:
    return req.messages[0]["content"]


# --- shared answering prompt --------------------------------------------------------------------


def test_schemas_are_strict():
    for schema in (B.ANSWER_SCHEMA, B.ACTION_SCHEMA, B.FINAL_SCHEMA, B.OBSERVE_SCHEMA):
        assert_strict(schema)


def test_action_schema_has_the_agreed_fields():
    assert list(B.ACTION_SCHEMA["properties"]) == ["action", "pattern", "session_id", "start", "end", "answer", "cited"]
    assert B.ACTION_SCHEMA["properties"]["action"]["enum"] == ["search", "read", "answer"]
    assert B.FINAL_SCHEMA["properties"]["action"]["enum"] == ["answer"]


def test_every_baseline_uses_the_same_prompt_model_settings_and_wording():
    item = ITEMS["su_001"]
    port = FakePort(lambda req: answer_reply())
    B.FullHistory(port, "anthropic").answer(item)
    B.KeywordSearch(port, "anthropic").answer(item)
    B.Oracle(port, "anthropic").answer(item)
    reqs = port.of("lme.answer")
    assert len(reqs) == 3
    assert len({(r.system, r.role, r.family, r.max_tokens, r.model, r.schema is B.ANSWER_SCHEMA) for r in reqs}) == 1
    assert reqs[0].role == "answerer" and reqs[0].model is None
    assert "I don't know" in reqs[0].system
    msg = context_of(reqs[0])
    assert "Current date: 2023-10-05 (Thu) 21:10" in msg and f"Question: {item.question}" in msg
    assert "## Session s001, 2023-09-20 (Wed) 16:00" in msg
    assert "[s001:0] user: I finally painted the bookshelf teal" in msg


# --- B0 ------------------------------------------------------------------------------------------


def test_b0_sends_every_session_in_time_order():
    item = ITEMS["ku_001"]
    port = FakePort(lambda req: answer_reply("Senior analyst", ["s003:0", "bogus:9"]))
    pred = B.FullHistory(port, "openai").answer(item)
    msg = context_of(port.requests[0])
    assert msg.index("s001") < msg.index("s002") < msg.index("s003")
    assert pred.system == "B0" and pred.answer == "Senior analyst"
    assert pred.cited_message_ids == ["s003:0"]  # an id that is not in the context is dropped
    assert pred.meta == {
        "family": "openai", "model": "fake-served", "baseline": "B0",
        "sessions_total": 3, "dropped_sessions": [], "max_context": B.DEFAULT_MAX_CONTEXT,
        "context_message_ids": [m.id for s in item.haystack for m in s.messages],
    }


def test_b0_drops_the_oldest_sessions_past_the_max_context():
    item = ITEMS["ku_001"]
    port = FakePort(lambda req: answer_reply("x", ["s001:0", "s003:0"]))
    pred = B.FullHistory(port, "anthropic", max_context=150).answer(item)
    msg = context_of(port.requests[0])
    assert pred.meta["dropped_sessions"][0] == "s001"
    assert "s001" not in msg and "s003" in msg
    assert pred.cited_message_ids == ["s003:0"]
    assert pred.context_tokens <= 250


# --- B1 ------------------------------------------------------------------------------------------


def test_bm25_rank_finds_the_matching_round_and_survives_hostile_queries():
    texts = ["user: I painted the bookshelf teal", "user: basil needs sun", "user: sourdough hydration"]
    assert B.bm25_rank(texts, "What color did I paint the bookshelf?")[0] == 0
    assert B.bm25_rank(texts, "") == [] and B.bm25_rank([], "bookshelf") == []
    for query in ['He said "NEAR(a b)" AND OR * -x: ^foo (bar', "col:val NOT a", "'; DROP TABLE docs; --", "\"\"\""]:
        B.bm25_rank(texts, query)  # must not raise
    assert B.bm25_rank(texts, "bookshelf basil", limit=1) in ([0], [1])


def test_rounds_pair_a_user_turn_with_the_assistant_turn_after_it():
    source = next(s for s in ITEMS["su_001"].haystack if s.id == "s001")
    rounds = B.rounds_of(source)
    assert [r.message_ids for r in rounds] == [["s001:0", "s001:1"], ["s001:2", "s001:3"]]
    lead = B.rounds_of(next(s for s in ITEMS["ms_001"].haystack if s.id == "s002"))
    assert [r.message_ids for r in lead] == [["s002:0"], ["s002:1", "s002:2"]]  # opens with the assistant


def test_b1_finds_the_evidence_round_within_a_tight_budget():
    item = ITEMS["su_001"]
    port = FakePort(lambda req: answer_reply("Teal", ["s001:0", "s002:0"]))
    pred = B.KeywordSearch(port, "anthropic", token_budget=60).answer(item)
    msg = context_of(port.requests[0])
    assert "bookshelf teal" in msg and "basil" not in msg
    assert pred.meta["rounds_included"] == 1 and pred.meta["rounds_total"] == 4
    assert pred.cited_message_ids == ["s001:0"]
    assert pred.context_tokens <= 60
    assert pred.meta["vector_search"] is False and pred.meta["baseline"] == "B1"


def test_b1_shows_chosen_rounds_in_time_order_and_respects_the_budget():
    item = replace(ITEMS["ms_001"], question="Which dogs and which cat do I have?")
    port = FakePort(lambda req: answer_reply("3"))
    pred = B.KeywordSearch(port, "anthropic", token_budget=8000).answer(item)
    msg = context_of(port.requests[0])
    assert msg.index("s001") < msg.index("s003") and "basil" not in msg
    assert pred.meta["rounds_included"] >= 2 and pred.context_tokens <= 8000
    small = B.KeywordSearch(port, "anthropic", token_budget=60).answer(item)
    assert small.context_tokens <= 60 and small.meta["rounds_included"] < pred.meta["rounds_included"]


def test_b1_default_budget_comes_from_config():
    assert B.KeywordSearch(FakePort(lambda r: answer_reply()), "anthropic").token_budget == 8000


def test_b1_embedder_hook_is_optional_and_recorded():
    item = ITEMS["su_001"]

    class Fake:
        def embed(self, texts):
            return [[1.0, 0.0] if "teal" in t or "color" in t else [0.0, 1.0] for t in texts]

    port = FakePort(lambda req: answer_reply("Teal"))
    pred = B.KeywordSearch(port, "anthropic", token_budget=100, embedder=Fake()).answer(item)
    assert pred.meta["vector_search"] is True
    assert "bookshelf teal" in context_of(port.requests[0])


# --- B3 ------------------------------------------------------------------------------------------


def test_b3_holds_only_the_evidence_rounds_in_time_order():
    item = ITEMS["tr_001"]
    port = FakePort(lambda req: answer_reply("12", ["s001:0", "s003:0", "s002:0"]))
    pred = B.Oracle(port, "anthropic").answer(item)
    msg = context_of(port.requests[0])
    assert msg.index("pottery class") < msg.index("small kiln")
    assert "sourdough" not in msg and "lopsided bowl" in msg
    assert pred.system == "B3" and pred.meta["evidence_rounds"] == 2
    assert pred.cited_message_ids == ["s001:0", "s003:0"]


def test_b3_with_no_evidence_has_an_empty_context():
    item = ITEMS["ku_002_abs"]
    port = FakePort(lambda req: answer_reply("I don't know"))
    pred = B.Oracle(port, "anthropic").answer(item)
    assert "(no excerpts)" in context_of(port.requests[0]) and "sourdough" not in context_of(port.requests[0])
    assert pred.context_tokens == 0 and pred.cited_message_ids == []


def test_b3_fits_the_evidence_to_the_budget():
    item = ITEMS["tr_001"]
    port = FakePort(lambda req: answer_reply("12"))
    pred = B.Oracle(port, "anthropic", token_budget=70).answer(item)
    assert pred.context_tokens <= 70 and pred.meta["rounds_included"] < pred.meta["evidence_rounds"]


# --- B2 ------------------------------------------------------------------------------------------


def test_b2_search_read_answer_loop():
    item = ITEMS["su_001"]
    script = [
        action("search", pattern="paint(ed)?"),
        action("read", session_id="s001", start=0, end=1),
        action("answer", answer="Teal", cited=["s001:0", "not:real"]),
    ]
    port = FakePort(lambda req: script.pop(0))
    pred = B.GrepAgent(port, "anthropic").answer(item)
    assert pred.answer == "Teal" and pred.cited_message_ids == ["s001:0"]
    assert pred.calls == 3 and pred.usage == USAGE + USAGE + USAGE
    assert pred.cost_usd == pytest.approx(0.03) and pred.latency_s == pytest.approx(1.5)
    assert pred.meta["steps"] == ["search", "read", "answer"] and pred.meta["forced"] is False
    third = port.requests[2].messages
    assert [m["role"] for m in third] == ["user", "assistant", "user", "assistant", "user"]
    assert "[s001:0] 2023-09-20 (Wed) 16:00 user: I finally painted the bookshelf teal" in third[2]["content"]
    assert "## Session s001" in third[4]["content"] and "[s001:1] assistant" in third[4]["content"]
    assert json.loads(third[1]["content"])["action"] == "search"
    assert all(r.schema is B.ACTION_SCHEMA for r in port.requests)
    seen = [m["content"].split("\n(Steps left")[0] for m in third[2::2]]
    assert pred.context_tokens == sum(estimate_tokens(t) for t in seen)
    assert "(Steps left before you must answer: 6.)" in third[4]["content"]


def test_b2_search_snippets_are_capped_and_a_bad_regex_is_a_substring():
    item = ITEMS["ku_001"]
    agent = B.GrepAgent(FakePort(lambda r: None), "anthropic")
    text, ids = agent._search("a", item)
    assert len(ids) == B.SEARCH_HITS and "showing the first 10" in text
    text, ids = agent._search("(unclosed", item)
    assert ids == [] and "No turn matches" in text
    text, ids = agent._search("PROMOTED TO SENIOR", item)
    assert ids == ["s003:0"]
    assert agent._search(None, item)[1] == []


def test_b2_read_clamps_and_reports_errors():
    item = ITEMS["su_001"]
    agent = B.GrepAgent(FakePort(lambda r: None), "anthropic")
    by_id = {s.id: s for s in item.haystack}
    text, ids = agent._read(action("read", session_id="s001", start=2, end=99), by_id)
    assert ids == ["s001:2", "s001:3"]
    assert "no session" in agent._read(action("read", session_id="nope"), by_id)[0]
    assert "has 4 turns" in agent._read(action("read", session_id="s001", start=9, end=12), by_id)[0]


def test_b2_must_answer_once_the_reading_budget_is_used():
    item = ITEMS["su_001"]
    schemas = []

    def handler(req):
        schemas.append(req.schema)
        if req.schema is B.ACTION_SCHEMA:
            return action("search", pattern="a")
        return action("answer", answer="Teal", cited=[])

    port = FakePort(handler)
    pred = B.GrepAgent(port, "anthropic", token_budget=40).answer(item)
    assert [s is B.FINAL_SCHEMA for s in schemas] == [False, True]
    assert pred.calls == 2 and pred.meta["forced"] is True and pred.answer == "Teal"
    assert pred.context_tokens == 40
    last = port.requests[1].messages[-1]["content"]
    assert 'next action must be "answer"' in last and "[cut:" in last
    assert port.requests[1].purpose == "b2.answer"


def test_b2_forces_an_answer_after_eight_steps():
    item = ITEMS["su_001"]

    def handler(req):
        if req.schema is B.FINAL_SCHEMA:
            return action("answer", answer="I don't know", cited=[])
        return action("search", pattern="zzz")

    port = FakePort(handler)
    pred = B.GrepAgent(port, "anthropic").answer(item)
    assert pred.calls == 9 and len(port.of("b2.step")) == 8 and len(port.of("b2.answer")) == 1
    assert pred.meta["forced"] is True and pred.answer == "I don't know"


def test_b2_a_malformed_step_is_an_error_for_run_baseline_to_record():
    port = FakePort(lambda req: "not json")
    with pytest.raises(ModelError):
        B.GrepAgent(port, "anthropic").answer(ITEMS["su_001"])


# --- B4 ------------------------------------------------------------------------------------------

LOG = {
    "s001": [{"text": "Started as a junior analyst at a shipping firm.", "message_ids": ["s001:0", "ghost:1"]}],
    "s003": [{"text": "New job title: senior analyst, promoted last week.", "message_ids": ["s003:0"]}],
}


def observer(req: ModelRequest):
    sid = re.search(r"## Session (\S+),", context_of(req)).group(1)
    return {"observations": LOG.get(sid, [])}


def b4_port(final="Senior analyst", cited=()):
    return FakePort(lambda req: observer(req) if req.purpose == B.OBSERVE_PURPOSE else answer_reply(final, cited))


def test_b4_builds_an_append_only_log_in_time_order_with_session_ids_only():
    item = ITEMS["ku_001"]
    port = b4_port()
    agent = B.ObservationLog(port, "anthropic")
    log = agent.build_log(item, B.Tally())
    assert [o.session_id for o in log] == ["s001", "s003"]  # time order, not file order
    assert log[0].message_ids == ["s001:0"]  # the id from another session is dropped
    obs_reqs = port.of(B.OBSERVE_PURPOSE)
    assert len(obs_reqs) == 3 and all(r.role == "worker_small" and r.family == "anthropic" for r in obs_reqs)
    assert all(r.schema is B.OBSERVE_SCHEMA for r in obs_reqs)
    # an observation request depends on its session alone, so the recorder can replay repeats
    again = B.ObservationLog(b4_port(), "anthropic")
    again.build_log(ITEMS["ku_001"], B.Tally())
    assert [r.messages for r in again.answerer.port.of(B.OBSERVE_PURPOSE)] == [r.messages for r in obs_reqs]


def test_b4_passes_the_whole_log_when_it_fits():
    item = ITEMS["ku_001"]
    port = b4_port(cited=["o2", "o9"])
    pred = B.ObservationLog(port, "anthropic", token_budget=8000).answer(item)
    msg = context_of(port.of("lme.answer")[0])
    assert msg.index("junior analyst") < msg.index("senior analyst")
    assert "[o2] 2023-06-10 (Sat) 18:30: New job title" in msg
    assert pred.meta["mode"] == "whole_log" and pred.meta["log_entries"] == 2
    assert pred.cited_message_ids == ["s003:0"]  # the turns behind the observation it cited, not every turn in the log
    assert pred.meta["cited_observation_ids"] == ["o2"]  # an id that is not in the log is dropped
    assert pred.meta["context_message_ids"] == ["s001:0", "s003:0"]
    assert pred.system == "B4" and pred.answer == "Senior analyst"
    assert pred.context_tokens == estimate_tokens(msg.split("Excerpts:\n\n")[1].split("\n\nQuestion:")[0])


def test_b4_switches_to_bm25_when_the_log_is_over_budget():
    item = ITEMS["ku_001"]
    port = b4_port(cited=["o1", "o2"])
    pred = B.ObservationLog(port, "anthropic", token_budget=25).answer(item)
    msg = context_of(port.of("lme.answer")[0])
    assert pred.meta["mode"] == "bm25" and pred.meta["entries_included"] == 1
    assert "junior analyst" not in msg and "senior analyst" in msg
    assert pred.cited_message_ids == ["s003:0"]  # o1 was not in the context, so it cannot be cited
    assert pred.meta["context_message_ids"] == ["s003:0"] and pred.meta["truncated"] is False
    assert pred.context_tokens <= 25


def test_b4_counts_every_call():
    item = ITEMS["ku_001"]
    pred = B.ObservationLog(b4_port(), "anthropic").answer(item)
    assert pred.calls == 4  # three sessions and the answer
    assert pred.usage == Usage(400, 40) and pred.cost_usd == pytest.approx(0.04)
    assert pred.latency_s == pytest.approx(2.0)


# --- accounting and running ------------------------------------------------------------------


def test_prediction_accounting_for_a_single_call_baseline():
    port = FakePort(lambda req: answer_reply("Teal"))
    pred = B.KeywordSearch(port, "openai").answer(ITEMS["su_001"])
    assert pred.calls == 1 and pred.usage == USAGE and pred.cost_usd == 0.01 and pred.latency_s == 0.5
    assert pred.item_id == "su_001" and pred.meta["family"] == "openai" and pred.meta["model"] == "fake-served"
    ctx = context_of(port.requests[0]).split("Excerpts:\n\n")[1].split("\n\nQuestion:")[0]
    assert pred.context_tokens == estimate_tokens(ctx)


def test_run_baseline_keeps_order_and_isolates_failures():
    def handler(req):
        if "pottery" in req.messages[0]["content"]:
            raise ModelError("boom")
        return answer_reply("ok")

    port = FakePort(handler)
    items = [ITEMS[k] for k in ("su_001", "tr_001", "ku_001", "ms_001", "ku_002_abs")]
    preds = B.run_baseline(items, B.FullHistory(port, "anthropic"), max_workers=3)
    assert [p.item_id for p in preds] == [i.id for i in items]
    failed = preds[1]
    assert failed.answer == "" and failed.meta["error"] == "ModelError: boom"
    assert failed.meta["baseline"] == "B0" and failed.meta["family"] == "anthropic"
    assert all(p.answer == "ok" and "error" not in p.meta for p in preds if p is not failed)


def test_run_baseline_on_an_empty_list():
    assert B.run_baseline([], B.FullHistory(FakePort(lambda r: answer_reply()), "anthropic")) == []


# --- review fixes ----------------------------------------------------------------------------------


def test_b2_ids_in_the_cut_part_of_an_observation_cannot_be_cited():
    item = ITEMS["su_001"]
    seen_text = []

    def handler(req):
        if req.schema is B.ACTION_SCHEMA:
            return action("search", pattern="a")
        seen_text.append(req.messages[-1]["content"])
        shown = re.findall(r"\[([^\]\s]+:\d+)\]", seen_text[0])
        return action("answer", answer="x", cited=shown + ["su_001_missing:9"] + [m.id for s in item.haystack for m in s.messages])

    pred = B.GrepAgent(FakePort(handler), "anthropic", token_budget=40).answer(item)
    shown = set(re.findall(r"\[([^\]\s]+:\d+)\]", seen_text[0]))
    assert set(pred.cited_message_ids) == shown


def test_b4_observer_has_room_for_a_long_log_but_the_answerer_keeps_the_shared_limit():
    port = b4_port()
    B.ObservationLog(port, "anthropic").answer(ITEMS["ku_001"])
    assert all(r.max_tokens == B.OBSERVE_MAX_TOKENS for r in port.of(B.OBSERVE_PURPOSE))
    assert all(r.max_tokens == B.MAX_TOKENS for r in port.of("lme.answer"))


# --- no answer in what a system is shown -------------------------------------------------------------

LEAKS = ("answer_", "sharegpt_", "ultrachat_")
SYSTEMS = {"none": B.ClosedBook, "B0": B.FullHistory, "B1": B.KeywordSearch, "B2": B.GrepAgent, "B3": B.Oracle, "B4": B.ObservationLog}


def scripted_handler():
    """A reply for every kind of request: B2 searches once and answers, B4's observer reads its session."""
    state = {"steps": 0}

    def handler(req):
        if req.purpose == B.OBSERVE_PURPOSE:
            return observer(req)
        if req.schema is B.ACTION_SCHEMA:
            state["steps"] += 1
            return action("search", pattern="the")
        if req.schema is B.FINAL_SCHEMA:
            return action("answer", answer="x", cited=[])
        return answer_reply("x", [])

    return handler


def requests_of(system: str, item) -> list[ModelRequest]:
    port = FakePort(scripted_handler())
    SYSTEMS[system](port, "anthropic").answer(item)
    return port.requests


def wire(req: ModelRequest) -> str:
    """Everything of a request a model could read."""
    return json.dumps([req.system, req.messages, req.schema], sort_keys=True)


def test_no_baseline_shows_a_session_id_that_names_the_answer():
    for item in ITEMS.values():
        for system in SYSTEMS:
            reqs = requests_of(system, item)
            assert reqs, system
            for req in reqs:
                text = wire(req)
                assert not any(leak in text for leak in LEAKS), (item.id, system)
                assert item.id not in text  # nor the question id, which ends in "_abs" on abstention questions


def test_the_requests_do_not_depend_on_the_evidence_except_in_b3():
    item = ITEMS["tr_001"]
    other = replace(item, evidence_message_ids=["s002:0"])
    assert other.evidence_message_ids != item.evidence_message_ids
    for system in ("none", "B0", "B1", "B2", "B4"):
        assert requests_of(system, item) == requests_of(system, other), system
    assert requests_of("B3", item) != requests_of("B3", other)


def test_the_real_file_shows_no_answer_in_a_session_id():
    """20 items spread over the file, B0's rendering."""
    if not REAL.exists():
        pytest.skip("LongMemEval_S is not downloaded")
    raw = {r["question_id"]: r for r in L.load(REAL)}
    items = L.to_items([raw[q] for q in sorted(raw)[::25]][:20])
    assert len(items) == 20
    for item in items:
        port = FakePort(lambda req: answer_reply("x"))
        pred = B.FullHistory(port, "anthropic").answer(item)
        context = context_of(port.requests[0]).split("Excerpts:\n\n")[1].split("\n\nQuestion:")[0]
        headers = re.findall(r"^## Session (\S+),", context, flags=re.M)
        labels = re.findall(r"^\[([^\]\s]+)\] (?:user|assistant):", context, flags=re.M)
        assert headers == [s.id for s in item.haystack] and all(re.fullmatch(r"s\d{3}", h) for h in headers)
        assert all(re.fullmatch(r"s\d{3}:\d+", label) for label in labels)
        assert not any(leak in h for h in headers for leak in LEAKS)
        # what the chats themselves say is left alone: the rendering adds no marker of its own
        said = "\n".join(m.text for s in item.haystack for m in s.messages)
        for leak in LEAKS:
            assert context.count(leak) == said.count(leak), (item.id, leak)
        assert "question_id" not in context and "has_answer" not in context
        assert len(pred.meta["context_message_ids"]) == len(labels)


def test_baseline_requests_leave_prompt_caching_off():
    for system in SYSTEMS:
        assert all(r.cache is False for r in requests_of(system, ITEMS["ku_001"])), system


# --- closed book -------------------------------------------------------------------------------------


def test_closed_book_asks_the_same_answerer_with_no_history():
    item = ITEMS["su_001"]
    port = FakePort(lambda req: answer_reply("Blue", ["s001:0"]))
    pred = B.ClosedBook(port, "anthropic").answer(item)
    (req,) = port.requests
    assert req.purpose == "lme.answer" and req.role == "answerer" and req.model is None
    assert req.schema is B.ANSWER_SCHEMA and req.max_tokens == B.MAX_TOKENS and req.cache is False
    msg = context_of(req)
    assert "(no excerpts)" in msg and f"Question: {item.question}" in msg and "teal" not in msg.lower()
    assert "guess" in req.system  # it may guess, or it would fail every question by refusing
    assert pred.system == "none" and pred.answer == "Blue"
    assert pred.cited_message_ids == []  # nothing was shown, so nothing can be cited
    assert pred.meta["context_message_ids"] == [] and pred.context_tokens == 0 and pred.calls == 1


# --- citations ---------------------------------------------------------------------------------------


def test_a_plain_text_reply_is_the_answer_with_no_citations():
    port = FakePort(lambda req: "  Teal.  ")  # no structured output, as from the stub
    pred = B.KeywordSearch(port, "anthropic").answer(ITEMS["su_001"])
    assert pred.answer == "Teal." and pred.cited_message_ids == []
    assert pred.meta["context_message_ids"]  # what was shown is still recorded


def test_a_structured_reply_without_answer_text_is_an_error():
    port = FakePort(lambda req: {"cited": []})
    with pytest.raises(ModelError):
        B.KeywordSearch(port, "anthropic").answer(ITEMS["su_001"])


def test_every_baseline_records_what_it_showed_and_what_was_cited():
    item = ITEMS["su_001"]
    script = [action("read", session_id="s001", start=0, end=1), action("answer", answer="Teal", cited=["s001:1", "s002:0"])]
    b2 = B.GrepAgent(FakePort(lambda req: script.pop(0)), "anthropic").answer(item)
    assert b2.meta["context_message_ids"] == ["s001:0", "s001:1"] and b2.cited_message_ids == ["s001:1"]
    port = FakePort(lambda req: answer_reply("Teal", ["s001:2", "s002:0"]))
    b1 = B.KeywordSearch(port, "anthropic", token_budget=8000).answer(item)
    shown = b1.meta["context_message_ids"]
    assert shown[:4] == ["s001:0", "s001:1", "s001:2", "s001:3"] and "s002:2" in shown  # time order; only rounds that match
    assert b1.cited_message_ids == ["s001:2"]  # s002:0 was not in the context
    b3 = B.Oracle(port, "anthropic").answer(item)
    assert b3.meta["context_message_ids"] == ["s001:0", "s001:1"] and b3.cited_message_ids == []


# --- a failed item keeps its cost --------------------------------------------------------------------


def billed(usage=Usage(70, 5), cost=0.02, latency=0.4) -> ModelResult:
    return ModelResult("", None, usage, cost, latency, "anthropic", "fake-model", "fake-served", "refusal")


def test_a_failed_item_keeps_what_it_spent():
    script = [action("search", pattern="a"), action("search", pattern="b")]

    def handler(req):
        if script:
            return script.pop(0)
        raise ModelError("boom")

    pred = B.run_baseline([ITEMS["su_001"]], B.GrepAgent(FakePort(handler), "openai"))[0]
    assert pred.answer == "" and pred.meta["error"] == "ModelError: boom"
    assert pred.calls == 2 and pred.usage == USAGE + USAGE
    assert pred.cost_usd == pytest.approx(0.02) and pred.latency_s == pytest.approx(1.0)
    assert pred.meta["family"] == "openai" and pred.meta["baseline"] == "B2" and pred.meta["model"] == "fake-served"


def test_a_call_the_vendor_billed_but_failed_is_counted():
    def handler(req):
        raise attach(ModelRefused("declined"), billed())

    pred = B.run_baseline([ITEMS["su_001"]], B.FullHistory(FakePort(handler), "anthropic"))[0]
    assert pred.meta["error"].startswith("ModelRefused") and pred.calls == 1
    assert pred.usage == Usage(70, 5) and pred.cost_usd == pytest.approx(0.02) and pred.latency_s == pytest.approx(0.4)


def test_a_reply_that_cannot_be_read_still_counts_its_call():
    pred = B.run_baseline([ITEMS["su_001"]], B.GrepAgent(FakePort(lambda req: "not json"), "anthropic"))[0]
    assert "error" in pred.meta and pred.calls == 1 and pred.usage == USAGE and pred.cost_usd == pytest.approx(0.01)


def test_a_failed_b4_item_adds_the_log_it_built_to_the_answer_call():
    def handler(req):
        if req.purpose == "lme.answer":
            raise ModelError("boom")
        return observer(req)

    pred = B.run_baseline([ITEMS["ku_001"]], B.ObservationLog(FakePort(handler), "anthropic"))[0]
    assert pred.calls == 3 and pred.usage == USAGE + USAGE + USAGE
    assert pred.cost_usd == pytest.approx(0.03)


def test_an_item_that_fails_before_any_call_costs_nothing():
    class Broken:
        system, family = "B9", "anthropic"

        def answer(self, item):
            raise RuntimeError("no model was called")

    pred = B.run_baseline([ITEMS["su_001"]], Broken())[0]
    assert pred.calls == 0 and pred.cost_usd == 0 and pred.usage == Usage()


# --- B4 build and query ------------------------------------------------------------------------------


def test_b4_records_the_cost_of_the_log_apart_from_the_query():
    pred = B.ObservationLog(b4_port(), "anthropic").answer(ITEMS["ku_001"])
    assert pred.meta["build_cost_usd"] == pytest.approx(0.03) and pred.meta["build_latency_s"] == pytest.approx(1.5)
    assert pred.meta["query_cost_usd"] == pytest.approx(0.01) and pred.meta["query_latency_s"] == pytest.approx(0.5)
    assert pred.meta["build_cost_usd"] + pred.meta["query_cost_usd"] == pytest.approx(pred.cost_usd)
    assert pred.meta["build_latency_s"] + pred.meta["query_latency_s"] == pytest.approx(pred.latency_s)


# --- a first block too big for the budget ------------------------------------------------------------


def test_b1_cuts_its_best_round_when_it_alone_is_over_the_budget():
    item = ITEMS["su_001"]
    port = FakePort(lambda req: answer_reply("Teal", ["s001:0", "s001:2"]))
    pred = B.KeywordSearch(port, "anthropic", token_budget=30).answer(item)
    msg = context_of(port.requests[0])
    ctx = msg.split("Excerpts:\n\n")[1].split("\n\nQuestion:")[0]
    assert ctx.endswith("[truncated]") and "bookshelf" in ctx
    assert pred.meta["truncated"] is True and pred.meta["rounds_included"] == 1
    assert pred.context_tokens <= 30
    shown = pred.meta["context_message_ids"]
    assert "s001:0" in shown and "s001:2" not in shown and pred.cited_message_ids == ["s001:0"]


def test_b1_and_b3_say_when_nothing_was_cut():
    port = FakePort(lambda req: answer_reply("Teal"))
    assert B.KeywordSearch(port, "anthropic").answer(ITEMS["su_001"]).meta["truncated"] is False
    assert B.Oracle(port, "anthropic").answer(ITEMS["su_001"]).meta["truncated"] is False


def test_b3_cuts_an_evidence_round_that_is_over_the_budget():
    port = FakePort(lambda req: answer_reply("12"))
    pred = B.Oracle(port, "anthropic", token_budget=20).answer(ITEMS["tr_001"])
    assert pred.meta["truncated"] is True and pred.context_tokens <= 20
    assert context_of(port.requests[0]).count("[truncated]") == 1
