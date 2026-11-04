"""Judge tests: a fake port returns scripted dicts; nothing touches the network."""

from __future__ import annotations

import pytest

from northstar_agent_memory.eval import judge as J
from northstar_agent_memory.eval.judge import (
    EntailmentJudge,
    MemoryMatcher,
    MetaEval,
    ProbeAnswer,
    QAJudge,
    make_probe_answers,
    meta_evaluate,
    passes,
    qa_prompt,
    qa_rules,
    verdict,
)
from northstar_agent_memory.eval.metrics import Claim, citation_scores, extraction_scores
from northstar_agent_memory.eval.types import GoldMemory, Prediction, QAItem, SystemMemory
from northstar_agent_memory.models.port import ModelError, ModelRequest, ModelResult, Usage
from northstar_agent_memory.models.schema import assert_strict
from northstar_agent_memory.transcript import Message, Source


class FakePort:
    """Returns scripted dicts. `script` is a dict or a callable taking the request."""

    def __init__(self, script):
        self.script = script
        self.requests: list[ModelRequest] = []

    def complete(self, req: ModelRequest) -> ModelResult:
        self.requests.append(req)
        parsed = self.script(req) if callable(self.script) else self.script
        return ModelResult(
            text="", parsed=parsed, usage=Usage(), cost_usd=0.0, latency_s=0.0,
            family=req.family, model="fake-model", served_model="fake-served", stop_reason="end_turn",
        )


def qa_item(id="q1", qtype="multi-session", abstention=False, answer="Lisbon", haystack=None, evidence=None):
    return QAItem(
        id, "own:test", "Where did I move?", answer, qtype, haystack or [],
        evidence_message_ids=evidence or [], abstention=abstention,
    )


def pred(answer="Lisbon", family="openai", item_id="q1") -> Prediction:
    return Prediction(item_id, "B1", answer, meta={"family": family})


def label(name):
    return {"rationale": "because", "label": name}


# --- schemas and prompts ---------------------------------------------------------------


@pytest.mark.parametrize("schema", [J.QA_SCHEMA, J.ENTAIL_SCHEMA, J.MATCH_SCHEMA, J.PROBE_SCHEMA])
def test_schemas_are_strict(schema):
    assert_strict(schema)


def test_prompt_rules_follow_item_type():
    default = qa_prompt(qa_item(), "x")
    temporal = qa_prompt(qa_item(qtype="temporal-reasoning"), "x")
    update = qa_prompt(qa_item(qtype="knowledge-update"), "x")
    abstain = qa_prompt(qa_item(abstention=True), "x")
    assert "off-by-one" in temporal and "off-by-one" not in default
    assert "updated value" in update and "updated value" not in default
    assert "<correct_answer>" in default and "part of what the correct answer requires" in default
    assert "<explanation>" in abstain and "cannot be answered" in abstain
    assert "<correct_answer>" not in abstain


def test_scenario_probe_kinds_get_their_own_rules():
    updated = qa_rules(qa_item(qtype="knowledge-update"))
    for kind in ("current_state", "history"):
        assert qa_rules(qa_item(qtype=kind)) == updated  # the updated-value rule
    stale = qa_rules(qa_item(qtype="stale_premise"))
    assert "no longer true" in stale and "corrects that assumption" in stale and "updated value" not in stale
    assert qa_rules(qa_item(qtype="attribution")) == qa_rules(qa_item())  # no rule of its own
    assert qa_rules(qa_item(qtype="abstention", abstention=True)) == qa_rules(qa_item(abstention=True))
    assert "cannot be answered" in qa_rules(qa_item(qtype="abstention", abstention=True))
    assert "no longer true" in qa_prompt(qa_item(qtype="stale_premise"), "x")


def test_staleness_expected_asks_the_answer_to_say_the_topic_may_be_out_of_date():
    plain = qa_item(qtype="current_state")
    flagged = qa_item(qtype="current_state")
    flagged.meta["staleness_expected"] = True
    assert "out of date" not in qa_rules(plain)
    assert qa_rules(flagged).startswith(qa_rules(plain)) and "may be out of date" in qa_rules(flagged)
    other = qa_item(qtype="stale_premise")
    other.meta["staleness_expected"] = True
    assert "no longer true" in qa_rules(other) and "may be out of date" in qa_rules(other)
    flagged.meta["staleness_expected"] = False
    assert qa_rules(flagged) == qa_rules(plain)


def test_the_prompt_hash_follows_the_wording_and_the_rules(monkeypatch):
    base = J.prompt_hash()
    assert len(base) == 16 and base == J.prompt_hash()
    for name in ("QA_SYSTEM", "_UPDATED", "_STALE_PREMISE", "_STALENESS", "_UNANSWERABLE", "_LABELS", "_OFF_BY_ONE"):
        with monkeypatch.context() as m:
            m.setattr(J, name, getattr(J, name) + " Changed.")
            assert J.prompt_hash() != base, name
    with monkeypatch.context() as m:  # a change in which rule an item type gets
        m.setattr(J, "UPDATED_KINDS", ())
        assert J.prompt_hash() != base


# --- QAJudge ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "lbl, outcome, abstained",
    [("correct", "correct", False), ("wrong", "hallucinated", False), ("no_answer", "omitted", True)],
)
def test_qa_label_mapping(lbl, outcome, abstained):
    port = FakePort(label(lbl))
    j = QAJudge(port, "anthropic").judge(qa_item(), pred())
    assert (j.outcome, j.abstained) == (outcome, abstained)
    assert j.judge_family == "anthropic"
    assert j.judge_model == "fake-served"
    assert j.system == "B1" and j.item_id == "q1"
    assert j.rationale == "because"


@pytest.mark.parametrize(
    "lbl, outcome, abstained",
    [("correct", "correct", True), ("wrong", "hallucinated", False), ("no_answer", "omitted", False)],
)
def test_qa_label_mapping_on_abstention_items(lbl, outcome, abstained):
    j = QAJudge(FakePort(label(lbl)), "anthropic").judge(qa_item(abstention=True), pred())
    assert (j.outcome, j.abstained) == (outcome, abstained)


def test_qa_request_is_well_formed():
    port = FakePort(label("correct"))
    QAJudge(port, "anthropic", effort="low").judge(qa_item(), pred("It was Lisbon"))
    (req,) = port.requests
    assert req.purpose == "judge.qa" and req.role == "judge" and req.family == "anthropic"
    assert req.schema is J.QA_SCHEMA
    assert 0 < req.max_tokens <= 4096
    assert req.effort == "low"
    (msg,) = req.messages
    assert "Where did I move?" in msg["content"] and "It was Lisbon" in msg["content"]


def test_family_rule_refuses_same_family():
    port = FakePort(label("correct"))
    with pytest.raises(ValueError, match="family rule"):
        QAJudge(port, "anthropic").judge(qa_item(), pred(family="anthropic"))
    assert port.requests == []  # refused before any call


def test_family_rule_allow_same_family_marks_rationale():
    j = QAJudge(FakePort(label("correct")), "anthropic", allow_same_family=True).judge(
        qa_item(), pred(family="anthropic")
    )
    assert j.rationale.startswith("not independent")
    assert j.outcome == "correct"
    other = QAJudge(FakePort(label("correct")), "anthropic", allow_same_family=True).judge(
        qa_item(), pred(family="openai")
    )
    assert not other.rationale.startswith("not independent")


def test_family_rule_needs_a_known_family_and_handles_several():
    judge = QAJudge(FakePort(label("correct")), "anthropic")
    with pytest.raises(ValueError, match="no meta"):
        judge.judge(qa_item(), Prediction("q1", "B1", "Lisbon"))
    with pytest.raises(ValueError, match="family rule"):  # an answer written by both families
        judge.judge(qa_item(), pred(family=("openai", "anthropic")))  # type: ignore[arg-type]


def test_empty_answer_is_omitted_without_a_call():
    port = FakePort(label("correct"))
    j = QAJudge(port, "anthropic").judge(qa_item(), pred("  "))
    assert j.outcome == "omitted" and j.judge_family == "code"
    assert port.requests == []


def test_qa_rejects_mismatched_item_and_bad_output():
    with pytest.raises(ValueError, match="given with item"):
        QAJudge(FakePort(label("correct")), "anthropic").judge(qa_item(), pred(item_id="other"))
    with pytest.raises(ModelError):
        QAJudge(FakePort(None), "anthropic").judge(qa_item(), pred())
    with pytest.raises(ModelError, match="unknown label"):
        QAJudge(FakePort(label("maybe")), "anthropic").judge(qa_item(), pred())


# --- EntailmentJudge -------------------------------------------------------------------


def test_entails_maps_verdict_and_caches():
    port = FakePort({"rationale": "r", "verdict": "entailed"})
    judge = EntailmentJudge(port, "openai")
    assert judge.entails("user: we use sqlite", "they use sqlite") is True
    assert judge.entails("user: we use sqlite", "they use sqlite") is True
    assert len(port.requests) == 1
    (req,) = port.requests
    assert req.purpose == "judge.entail" and req.schema is J.ENTAIL_SCHEMA and req.max_tokens <= 4096
    not_entailed = EntailmentJudge(FakePort({"rationale": "r", "verdict": "not_entailed"}), "openai")
    assert not_entailed.entails("a", "b") is False


def test_entails_keeps_hedges_in_the_prompt():
    port = FakePort({"rationale": "r", "verdict": "not_entailed"})
    EntailmentJudge(port, "openai").entails("user: maybe we use sqlite", "We use sqlite")
    system = port.requests[0].system
    assert "hedge" in system and "only" in system and "negation" in system


def test_entails_edge_cases_and_family_rule():
    port = FakePort({"rationale": "r", "verdict": "entailed"})
    judge = EntailmentJudge(port, "openai")
    assert judge.entails("   ", "claim") is False  # no source, no support
    with pytest.raises(ValueError, match="empty claim"):
        judge.entails("premise", " ")
    assert port.requests == []
    with pytest.raises(ValueError, match="family rule"):
        EntailmentJudge(port, "openai", checks_family="openai")
    EntailmentJudge(port, "openai", checks_family="anthropic")
    with pytest.raises(ModelError):
        EntailmentJudge(FakePort({"rationale": "r", "verdict": "yes"}), "openai").entails("a", "b")


def test_entailment_judge_plugs_into_citation_scores():
    port = FakePort(lambda req: {"rationale": "r", "verdict": "entailed" if "sqlite" in req.messages[0]["content"].split("<claim>")[0] else "not_entailed"})
    judge = EntailmentJudge(port, "openai")
    messages = {"m1": Message("m1", "s", 0, "user", "we use sqlite")}
    r = citation_scores([Claim("sqlite is used", ["m1"])], messages, judge.entails)
    assert r.recall == 1.0


# --- MemoryMatcher ---------------------------------------------------------------------

ALL_TRUE = {"rationale": "r", "a_implies_b": True, "b_implies_a": True, "same_strength": True, "same_scope": True}


def test_match_needs_every_check():
    assert MemoryMatcher(FakePort(ALL_TRUE), "openai").same("A", "B") is True
    for check in ("a_implies_b", "b_implies_a", "same_strength", "same_scope"):
        port = FakePort({**ALL_TRUE, check: False})
        assert MemoryMatcher(port, "openai").same("A", "B") is False, check


def test_match_identical_lines_need_no_call_and_pairs_are_cached():
    port = FakePort(ALL_TRUE)
    m = MemoryMatcher(port, "openai")
    assert m.same("Use  SQLite.", "Use SQLite.") is True
    assert port.requests == []
    m.same("A", "B")
    m.same("A", "B")
    assert len(port.requests) == 1
    assert port.requests[0].purpose == "judge.match"
    assert port.requests[0].schema is J.MATCH_SCHEMA
    m.same("B", "A")  # a different order is a different pair
    assert len(port.requests) == 2


def test_match_family_rule():
    with pytest.raises(ValueError, match="family rule"):
        MemoryMatcher(FakePort(ALL_TRUE), "anthropic", checks_family="anthropic")


def test_match_plugs_into_extraction_scores():
    matcher = MemoryMatcher(FakePort({**ALL_TRUE, "same_scope": False}), "openai")
    gold = [GoldMemory("a", "Use SQLite", "decision", "user", ["m1"], True)]
    system = [SystemMemory("s1", "Use SQLite", "active"), SystemMemory("s2", "Always use SQLite", "active")]
    r = extraction_scores(gold, system, matcher.same_memory)
    assert r.score.correct == 1  # the identical line matches without a call
    assert r.hallucinated_ids == ["s2"]  # the model said the scope differs


# --- make_probe_answers ----------------------------------------------------------------


def probe_reply(**over):
    base = {
        "positive": "You relocated to the Portuguese capital.",
        "wrong_on_topic": "You moved to Madrid.",
        "partial": "You moved somewhere in Portugal.",
        "vague": "You might have moved to a few places.",
        "stale": None,
    }
    return {**base, **over}


def history(texts: dict[str, str]) -> list[Source]:
    return [Source("s1", messages=[Message(i, "s1", n, "user", t) for n, (i, t) in enumerate(texts.items())])]


def test_probes_cover_positive_and_three_negatives_for_a_plain_item():
    port = FakePort(probe_reply())
    probes = make_probe_answers([qa_item()], port, "openai")
    assert [(p.kind, p.family) for p in probes] == [
        ("positive", "openai"), ("wrong_on_topic", "openai"), ("partial", "openai"), ("vague", "openai"),
    ]
    (req,) = port.requests
    assert req.purpose.startswith("judge.meta") and req.family == "openai"
    assert req.schema is J.PROBE_SCHEMA and req.max_tokens <= 4096


def test_probe_stale_needs_a_knowledge_update_item_with_evidence_in_the_history():
    stale_reply = probe_reply(stale="You live in Berlin.")
    # not a knowledge-update item: stale is skipped even if the model returned one
    plain = make_probe_answers([qa_item()], FakePort(stale_reply), "openai")
    assert "stale" not in [p.kind for p in plain]
    # knowledge-update with no evidence in the history: skipped, and no excerpt sent
    port = FakePort(stale_reply)
    bare = make_probe_answers([qa_item(qtype="knowledge-update")], port, "openai")
    assert "stale" not in [p.kind for p in bare]
    assert "<history_excerpt>" not in port.requests[0].messages[0]["content"]
    # with evidence: the excerpt is shown and the stale answer is kept
    item = qa_item(
        qtype="knowledge-update",
        haystack=history({"m1": "I live in Berlin.", "m2": "Moved to Lisbon.", "m3": "unrelated"}),
        evidence=["m1", "m2"],
    )
    port = FakePort(stale_reply)
    probes = make_probe_answers([item], port, "openai")
    prompt = port.requests[0].messages[0]["content"]
    assert "I live in Berlin." in prompt and "unrelated" not in prompt
    assert [p.kind for p in probes][-1] == "stale"


def test_probe_stale_null_is_skipped():
    item = qa_item(qtype="knowledge-update", haystack=history({"m1": "I live in Berlin."}), evidence=["m1"])
    probes = make_probe_answers([item], FakePort(probe_reply(stale=None)), "openai")
    assert "stale" not in [p.kind for p in probes]


def test_probe_negative_that_contains_the_gold_answer_is_dropped():
    reply = probe_reply(wrong_on_topic="Not Lisbon, you moved to Madrid... or maybe Lisbon.", partial=None)
    probes = make_probe_answers([qa_item()], FakePort(reply), "openai")
    assert [p.kind for p in probes] == ["positive", "vague"]
    # a word that merely contains the gold answer does not count as containing it
    reply = probe_reply(wrong_on_topic="Lisbonne, I think.")
    assert "wrong_on_topic" in [p.kind for p in make_probe_answers([qa_item()], FakePort(reply), "openai")]


def test_probes_for_abstention_items():
    item = qa_item(abstention=True, answer="The history never says where you moved.")
    reply = probe_reply(positive="I can't tell from the history.", partial="should be skipped", stale="skip")
    port = FakePort(reply)
    probes = make_probe_answers([item], port, "openai")
    assert [p.kind for p in probes] == ["positive", "wrong_on_topic", "vague"]
    assert "<explanation>" in port.requests[0].messages[0]["content"]


def test_probe_empty_strings_are_skipped():
    probes = make_probe_answers([qa_item()], FakePort(probe_reply(vague="  ", partial=None)), "openai")
    assert [p.kind for p in probes] == ["positive", "wrong_on_topic"]


def test_probe_temporal_prompt_asks_for_a_count_that_differs():
    port = FakePort(probe_reply())
    make_probe_answers([qa_item(qtype="temporal-reasoning", answer="18 days")], port, "openai")
    assert "at least two" in port.requests[0].messages[0]["content"]


# --- meta_evaluate and passes ----------------------------------------------------------


def by_answer_judge(accepts: set[str], family="anthropic") -> QAJudge:
    """A judge whose fake model accepts exactly the responses in `accepts`."""

    def script(req):
        text = req.messages[0]["content"].split("<response>\n")[1].split("\n</response>")[0]
        return label("correct" if text in accepts else "wrong")

    return QAJudge(FakePort(script), family, batch_size=1)


def probe(kind, answer, item_id="q1") -> ProbeAnswer:
    return ProbeAnswer(item_id, kind, answer, "openai")


def test_meta_evaluate_arithmetic():
    items = [qa_item("q1"), qa_item("q2")]
    probes = [
        probe("positive", "p1"), probe("positive", "p2", "q2"),
        probe("wrong_on_topic", "w1"), probe("wrong_on_topic", "w2", "q2"),
        probe("partial", "pa1"), probe("partial", "pa2", "q2"),
        probe("vague", "v1"), probe("vague", "v2", "q2"),
        probe("stale", "s1"),
    ]
    # accepts one positive, one wrong, both partial: 3 of 7 negatives
    judge = by_answer_judge({"p1", "w2", "pa1", "pa2"})
    meta = meta_evaluate(judge, items, probes)
    assert (meta.n, meta.n_positives, meta.n_negatives) == (9, 2, 7)
    assert meta.true_accept_rate == pytest.approx(0.5)
    assert meta.false_accept_rate == pytest.approx(3 / 7)
    assert meta.false_accept_by_kind == {"wrong_on_topic": 0.5, "partial": 1.0, "vague": 0.0, "stale": 0.0}
    assert meta.n_by_kind == {"wrong_on_topic": 2, "partial": 2, "vague": 2, "stale": 1}
    assert meta.false_accepts == [("q2", "wrong_on_topic"), ("q1", "partial"), ("q2", "partial")]
    assert meta.judge_family == "anthropic" and meta.judge_model == "fake-served"
    assert 3 / 7 < meta.false_accept_upper95 <= 1.0


def test_meta_evaluate_clean_judge_passes_and_lenient_judge_fails():
    items = [qa_item("q1")]
    probes = [probe("positive", "p"), probe("wrong_on_topic", "w"), probe("vague", "v")]
    good = meta_evaluate(by_answer_judge({"p"}), items, probes)
    assert good.false_accept_rate == 0.0 and good.true_accept_rate == 1.0
    assert not passes(good, 0.10) and verdict(good, 0.10) == "insufficient"  # two wrong answers prove nothing
    lenient = meta_evaluate(by_answer_judge({"p", "w", "v"}), items, probes)
    assert lenient.false_accept_rate == 1.0
    assert not passes(lenient, 0.10)


def meta_of(rate, n_neg=60, true_rate=1.0):
    return MetaEval("anthropic", "m", n_neg + 10, 10, n_neg, true_rate, rate, None, {}, {})


def test_passes_bar_is_strict_and_defaults_to_config():
    assert passes(meta_of(0.0), 0.10) and verdict(meta_of(0.0), 0.10) == "passed"
    assert not passes(meta_of(0.10), 0.10)  # fewer than the bar, not equal to it
    assert verdict(meta_of(0.10), 0.10) == "failed"
    assert passes(meta_of(0.09))  # the default bar is eval.judge_false_accept_max = 0.10
    assert not passes(meta_of(0.10))
    assert not passes(meta_of(None, n_neg=0))  # no negatives tested: does not pass


def test_a_judge_tested_on_fewer_than_60_wrong_answers_is_insufficient():
    assert J.MIN_WRONG_PROBES == 60
    assert verdict(meta_of(0.0, n_neg=59), 0.10) == "insufficient" and not passes(meta_of(0.0, n_neg=59), 0.10)
    assert verdict(meta_of(0.0, n_neg=60), 0.10) == "passed"
    assert verdict(meta_of(None, n_neg=0), 0.10) == "insufficient"
    assert verdict(meta_of(0.5, n_neg=30), 0.10) == "insufficient"  # too few to say anything either way


def test_a_judge_must_accept_85_percent_of_the_gold_paraphrases():
    assert J.MIN_TRUE_ACCEPT == 0.85
    assert verdict(meta_of(0.0, true_rate=0.85), 0.10) == "passed"
    assert verdict(meta_of(0.0, true_rate=0.84), 0.10) == "failed"
    assert verdict(meta_of(0.0, true_rate=None), 0.10) == "failed"
    assert not passes(meta_of(0.0, true_rate=0.5), 0.10)


def test_meta_evaluate_reports_the_wilson_upper_bound_of_the_false_accept_rate():
    items = [qa_item(f"q{k}") for k in range(60)]
    probes = [probe("positive", "p")] + [probe("wrong_on_topic", f"w{k}", f"q{k}") for k in range(60)]
    accepted = {"p", "w0", "w1", "w2", "w3", "w4"}  # 5 of 60 wrong answers accepted
    meta = meta_evaluate(by_answer_judge(accepted), items, probes)
    assert meta.false_accept_rate == pytest.approx(5 / 60)
    assert meta.false_accept_upper95 == pytest.approx(J.wilson_interval(5, 60)[1]) and meta.false_accept_upper95 > 5 / 60
    assert verdict(meta, 0.10) == "passed"  # the point estimate is below the bar; the upper bound is reported, not the bar


def test_meta_evaluate_with_no_probes():
    meta = meta_evaluate(by_answer_judge(set()), [qa_item()], [])
    assert meta.n == 0 and meta.false_accept_rate is None and meta.true_accept_rate is None
    assert not passes(meta, 0.10)


def test_meta_evaluate_rejects_own_family_probes_and_unknown_items():
    with pytest.raises(ValueError, match="own family"):
        meta_evaluate(by_answer_judge(set(), "openai"), [qa_item()], [probe("positive", "p")])
    with pytest.raises(KeyError):
        meta_evaluate(by_answer_judge(set()), [qa_item()], [probe("positive", "p", "nope")])


def test_meta_evaluate_judges_abstention_probes_by_their_item():
    item = qa_item("q1", abstention=True, answer="The history never says.")
    port = FakePort(lambda req: label("correct" if "can't tell" in req.messages[0]["content"] else "wrong"))
    meta = meta_evaluate(QAJudge(port, "anthropic", batch_size=1), [item], [probe("positive", "I can't tell."), probe("vague", "Maybe Paris?")])
    assert meta.true_accept_rate == 1.0 and meta.false_accept_rate == 0.0


# --- batched judging -------------------------------------------------------------------


def bitem(id, qtype="multi-session", abstention=False, **meta) -> QAItem:
    item = qa_item(id, qtype=qtype, abstention=abstention, answer=f"gold of {id}")
    item.question = f"Question about {id}?"
    item.meta.update(meta)
    return item


def bpred(item_id, answer, family="openai", system="B1") -> Prediction:
    return Prediction(item_id, system, answer, meta={"family": family})


def pairs_in(req) -> dict[str, dict]:
    """Each pair of a batched request: local id -> its question, response and body."""
    import re

    out = {}
    for pair_id, body in re.findall(r'<pair id="(p\d+)">\n(.*?)</pair>', req.messages[-1]["content"], re.S):
        out[pair_id] = {
            "question": re.search(r"<question>\n(.*?)\n</question>", body, re.S).group(1),
            "response": re.search(r"<response>\n(.*?)\n</response>", body, re.S).group(1),
            "body": body,
        }
    return out


def batch_port(labels: dict[str, str], *, drop=(), repeat=(), rename=None, bad_label=()):
    """A fake judge: labels each pair by its response text; `drop`, `repeat`, `rename` and `bad_label` damage the
    reply for the listed local ids. A single-pair request is answered by `labels` too."""

    def script(req):
        if req.purpose == "judge.qa":
            response = req.messages[-1]["content"].split("<response>\n")[1].split("\n</response>")[0]
            return label(labels[response])
        verdicts = []
        for pair_id, pair in pairs_in(req).items():
            if pair_id in drop:
                continue
            name = (rename or {}).get(pair_id, pair_id)
            lbl = "maybe" if pair_id in bad_label else labels[pair["response"]]
            verdicts.append({"id": name, "rationale": f"batch {pair_id}", "label": lbl})
            if pair_id in repeat:
                verdicts.append({"id": name, "rationale": "again", "label": lbl})
        return {"verdicts": verdicts}

    return FakePort(script)


def test_the_batch_schema_is_strict_and_the_reply_is_a_list_of_verdicts():
    assert_strict(J.QA_BATCH_SCHEMA)
    item = J.QA_BATCH_SCHEMA["properties"]["verdicts"]["items"]
    assert list(item["properties"]) == ["id", "rationale", "label"]
    assert item["properties"]["label"]["enum"] == ["correct", "wrong", "no_answer"]


def test_a_batch_is_one_call_with_each_pair_its_own_question_answer_and_rule():
    items = [
        bitem("a"), bitem("b", "temporal-reasoning"), bitem("c", "knowledge-update"), bitem("d", abstention=True),
        bitem("e", "stale_premise"), bitem("f", "history", staleness_expected=True),
    ]
    port = batch_port({f"resp {i.id}": "correct" for i in items})
    judge = QAJudge(port, "anthropic", batch_size=8, effort="low")
    out = judge.judge_many([(i, bpred(i.id, f"resp {i.id}")) for i in items])
    (req,) = port.requests
    assert req.purpose == "judge.qa.batch" and req.role == "judge" and req.family == "anthropic" and req.effort == "low"
    assert req.schema is J.QA_BATCH_SCHEMA and 0 < req.max_tokens <= 4096 * 2
    assert "never relative to the other pairs" in req.system
    seen = pairs_in(req)
    assert list(seen) == ["p1", "p2", "p3", "p4", "p5", "p6"]
    for n, item in enumerate(items, 1):
        pair = seen[f"p{n}"]
        assert pair["question"] == item.question and pair["response"] == f"resp {item.id}"
        assert f"gold of {item.id}" in pair["body"]
        assert qa_rules(item) in pair["body"]  # the same rule text judge() uses
    assert "off-by-one" in seen["p2"]["body"] and "off-by-one" not in seen["p1"]["body"]
    assert "<explanation>" in seen["p4"]["body"] and "<correct_answer>" not in seen["p4"]["body"]
    assert "no longer true" in seen["p5"]["body"] and "may be out of date" in seen["p6"]["body"]
    assert [j.item_id for j in out] == [i.id for i in items]
    assert all(j.judge_family == "anthropic" and j.judge_model == "fake-served" and j.outcome == "correct" for j in out)
    assert out[0].rationale == "batch p1"


def test_batched_labels_map_as_judge_does():
    items = [bitem("a"), bitem("b"), bitem("c")]
    port = batch_port({"r a": "correct", "r b": "wrong", "r c": "no_answer"})
    out = QAJudge(port, "anthropic", batch_size=8).judge_many([(i, bpred(i.id, f"r {i.id}")) for i in items])
    assert [(j.outcome, j.abstained) for j in out] == [("correct", False), ("hallucinated", False), ("omitted", True)]


def test_batched_abstention_items_map_as_judge_does():
    items = [bitem("a", abstention=True), bitem("b", abstention=True), bitem("c", abstention=True)]
    port = batch_port({"r a": "correct", "r b": "wrong", "r c": "no_answer"})
    out = QAJudge(port, "anthropic", batch_size=8).judge_many([(i, bpred(i.id, f"r {i.id}")) for i in items])
    assert [(j.outcome, j.abstained) for j in out] == [("correct", True), ("hallucinated", False), ("omitted", False)]
    one = QAJudge(FakePort(label("correct")), "anthropic").judge(items[0], bpred("a", "r a"))
    assert (one.outcome, one.abstained) == (out[0].outcome, out[0].abstained)


def test_more_pairs_than_the_batch_size_go_in_several_calls_and_a_lone_pair_goes_through_judge():
    items = [bitem(k) for k in "abcde"]
    port = batch_port({f"r {k}": "correct" for k in "abcde"})
    out = QAJudge(port, "anthropic", batch_size=2).judge_many([(i, bpred(i.id, f"r {i.id}")) for i in items])
    assert [r.purpose for r in port.requests] == ["judge.qa.batch", "judge.qa.batch", "judge.qa"]
    assert [len(pairs_in(r)) for r in port.requests[:2]] == [2, 2]
    assert [j.item_id for j in out] == list("abcde")
    single = batch_port({"r a": "wrong"})
    (only,) = QAJudge(single, "anthropic", batch_size=8).judge_many([(items[0], bpred("a", "r a"))])
    assert [r.purpose for r in single.requests] == ["judge.qa"] and only.outcome == "hallucinated" and only.rationale == "because"
    assert QAJudge(single, "anthropic", batch_size=8).judge_many([]) == []


def test_code_scored_pairs_skip_the_model_and_the_rest_are_batched():
    leaky = bitem("a", forbidden_terms=["migraine"])
    plain = [bitem("b"), bitem("c")]
    port = batch_port({"r b": "correct", "r c": "wrong"})
    out = QAJudge(port, "anthropic", batch_size=8).judge_many(
        [(leaky, bpred("a", "A Migraine visit")), (plain[0], bpred("b", "r b")), (bitem("e"), bpred("e", "   ")), (plain[1], bpred("c", "r c"))]
    )
    assert [(j.outcome, j.judge_family) for j in out] == [("hallucinated", "code"), ("correct", "anthropic"), ("omitted", "code"), ("hallucinated", "anthropic")]
    assert out[0].rationale == "the answer contains a term the probe forbids" and out[2].rationale == "empty response"
    (req,) = port.requests
    assert sorted(p["question"] for p in pairs_in(req).values()) == [plain[0].question, plain[1].question]
    only_code = batch_port({})
    QAJudge(only_code, "anthropic").judge_many([(leaky, bpred("a", "migraine")), (bitem("e"), bpred("e", ""))])
    assert only_code.requests == []


@pytest.mark.parametrize(
    "damage, why",
    [
        ({"drop": ("p2",)}, "no verdict"),
        ({"repeat": ("p2",)}, "more than one verdict"),
        ({"rename": {"p2": "p9"}}, "no verdict"),
        ({"bad_label": ("p2",)}, "an unknown label"),
    ],
)
def test_a_pair_the_reply_misses_or_doubles_is_graded_alone(damage, why):
    items = [bitem("a"), bitem("b"), bitem("c")]
    port = batch_port({"r a": "correct", "r b": "wrong", "r c": "correct"}, **damage)
    out = QAJudge(port, "anthropic", batch_size=8).judge_many([(i, bpred(i.id, f"r {i.id}")) for i in items])
    assert [r.purpose for r in port.requests] == ["judge.qa.batch", "judge.qa"]  # only the damaged pair again
    assert "Question about b?" in port.requests[1].messages[0]["content"]
    assert [j.outcome for j in out] == ["correct", "hallucinated", "correct"]
    assert why in out[1].rationale and "graded alone" in out[1].rationale and out[1].rationale.endswith("because")
    assert out[0].rationale == "batch p1" and out[2].rationale == "batch p3"


def test_an_unknown_id_costs_nothing_when_every_pair_has_its_verdict():
    items = [bitem("a"), bitem("b")]
    port = batch_port({"r a": "correct", "r b": "correct"})
    base = port.script

    def extra(req):
        reply = base(req)
        reply["verdicts"].append({"id": "p7", "rationale": "x", "label": "wrong"})
        return reply

    port.script = extra
    out = QAJudge(port, "anthropic", batch_size=8).judge_many([(i, bpred(i.id, f"r {i.id}")) for i in items])
    assert len(port.requests) == 1 and [j.outcome for j in out] == ["correct", "correct"]


def test_a_reply_without_verdicts_is_an_error():
    port = FakePort({"verdicts": "nope"})
    with pytest.raises(ModelError, match="no verdicts"):
        QAJudge(port, "anthropic", batch_size=8).judge_many([(bitem("a"), bpred("a", "x")), (bitem("b"), bpred("b", "y"))])


def test_the_family_rule_holds_for_every_pair_of_a_batch():
    port = batch_port({"r a": "correct", "r b": "correct"})
    pairs = [(bitem("a"), bpred("a", "r a")), (bitem("b"), bpred("b", "r b", family="anthropic"))]
    with pytest.raises(ValueError, match="family rule"):
        QAJudge(port, "anthropic", batch_size=8).judge_many(pairs)
    assert port.requests == []  # refused before any call
    out = QAJudge(port, "anthropic", allow_same_family=True, batch_size=8).judge_many(pairs)
    assert [j.rationale.startswith("not independent") for j in out] == [False, True]
    assert out[1].rationale == "not independent: batch p2"
    with pytest.raises(ValueError, match="no meta"):
        QAJudge(port, "anthropic", batch_size=8).judge_many([(bitem("a"), Prediction("a", "B1", "x")), pairs[0]])


def test_a_fallback_keeps_the_not_independent_mark_first():
    port = batch_port({"r a": "correct", "r b": "correct"}, drop=("p1",))
    pairs = [(bitem("a"), bpred("a", "r a", family="anthropic")), (bitem("b"), bpred("b", "r b"))]
    out = QAJudge(port, "anthropic", allow_same_family=True, batch_size=8).judge_many(pairs)
    assert out[0].rationale.startswith("not independent: ") and "graded alone" in out[0].rationale


def test_a_pair_with_the_wrong_item_is_refused():
    with pytest.raises(ValueError, match="given with item"):
        QAJudge(batch_port({}), "anthropic", batch_size=8).judge_many([(bitem("a"), bpred("zzz", "x"))])


def test_the_batch_size_comes_from_the_config_and_defaults_to_eight():
    cfg = {"eval": {}}
    assert J.judge_batch_size(cfg) == 8 and J.DEFAULT_BATCH_SIZE == 8
    assert J.judge_batch_size({"eval": {"judge_batch_size": 5}}) == 5
    with pytest.raises(ValueError, match="at least 1"):
        J.judge_batch_size({"eval": {"judge_batch_size": 0}})
    with pytest.raises(ValueError, match="at least 1"):
        QAJudge(FakePort({}), "anthropic", batch_size=0)
    assert QAJudge(FakePort({}), "anthropic").batch_size == J.judge_batch_size()


def test_the_prompt_hash_covers_the_batch_template_and_the_batch_size(monkeypatch):
    base = J.prompt_hash()
    assert base == J.prompt_hash(J.judge_batch_size())
    sizes = {n: J.prompt_hash(n) for n in (1, 2, 8, 16)}
    assert len(set(sizes.values())) == 4  # a single-pair judge and a batched one are never the same judge
    for name in ("QA_BATCH_SYSTEM", "_BATCH_LABELS", "_BATCH_ABSTENTION_LABELS"):
        with monkeypatch.context() as m:
            m.setattr(J, name, getattr(J, name) + " Changed.")
            assert J.prompt_hash(8) != sizes[8], name
    with monkeypatch.context() as m:
        schema = {**J.QA_BATCH_SCHEMA, "description": "changed"}
        m.setattr(J, "QA_BATCH_SCHEMA", schema)
        assert J.prompt_hash(8) != sizes[8]


def test_pick_batch_takes_the_first_entries_with_distinct_items():
    entries = [("a", 1), ("a", 2), ("b", 1), ("c", 1), ("b", 2), ("d", 1)]
    assert J.pick_batch(entries, 3, lambda e: e[0]) == [0, 2, 3]
    assert J.pick_batch(entries, 10, lambda e: e[0]) == [0, 2, 3, 5]
    assert J.pick_batch([], 3, lambda e: e[0]) == []


def _probe_set(n_items=6):
    items = [bitem(f"q{k}") for k in range(n_items)]
    probes = [ProbeAnswer(i.id, kind, f"{kind} {i.id}", "openai") for i in items for kind in ("positive", "wrong_on_topic", "partial", "vague")]
    labels = {p.answer: ("correct" if p.kind == "positive" else "wrong") for p in probes}
    return items, probes, labels


def test_meta_evaluate_judges_the_probes_in_mixed_batches_of_distinct_items():
    items, probes, labels = _probe_set()
    port = batch_port(labels)
    meta = meta_evaluate(QAJudge(port, "anthropic", batch_size=4), items, probes, seed=7)
    assert meta.n == 24 and meta.true_accept_rate == 1.0 and meta.false_accept_rate == 0.0
    sizes, kinds_in_batch = [], []
    for req in port.requests:
        assert req.purpose == "judge.qa.batch"
        asked = pairs_in(req)
        questions = [p["question"] for p in asked.values()]
        assert len(set(questions)) == len(questions)  # never two answers to one item in a call
        sizes.append(len(asked))
        kinds_in_batch.append({p["response"].split()[0] for p in asked.values()})
    assert sum(sizes) == 24 and max(sizes) == 4 and sizes.count(4) >= 5
    assert any(len(k) > 1 for k in kinds_in_batch)  # a batch mixes kinds as well as items


def test_meta_evaluate_shuffles_with_the_seed_and_the_scores_do_not_depend_on_it():
    items, probes, labels = _probe_set()
    labels["partial q2"] = "correct"  # one false accept
    order = {}
    for seed in (1, 1, 2):
        port = batch_port(labels)
        meta = meta_evaluate(QAJudge(port, "anthropic", batch_size=4), items, probes, seed=seed)
        order.setdefault(seed, []).append([[p["response"] for p in pairs_in(r).values()] for r in port.requests])
        assert meta.false_accepts == [("q2", "partial")] and meta.n_negatives == 18
    assert order[1][0] == order[1][1] != order[2][0]
    single = meta_evaluate(by_answer_judge({p.answer for p in probes if labels[p.answer] == "correct"}), items, probes)
    assert single.n_by_kind == meta_evaluate(QAJudge(batch_port(labels), "anthropic", batch_size=4), items, probes).n_by_kind


def test_probe_batches_never_hold_one_item_twice_and_use_every_probe_once():
    _, probes, _ = _probe_set(3)
    for size in (1, 3, 5, 50):
        batches = J.probe_batches(probes, size, 0)
        assert sorted(k for b in batches for k in b) == list(range(len(probes)))
        assert all(len(b) <= size and len({probes[k].item_id for k in b}) == len(b) for b in batches)
