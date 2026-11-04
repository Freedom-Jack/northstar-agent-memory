"""Scoring tests: every metric's edge cases, with invented data and no model calls."""

from __future__ import annotations

import pytest

from northstar_agent_memory.eval.metrics import (
    Claim,
    bootstrap_ci,
    citation_scores,
    cost_summary,
    extraction_scores,
    normalize_text,
    paired_difference,
    qa_scores,
    quote_exact,
    update_scores,
    wilson_interval,
)
from northstar_agent_memory.eval.types import (
    GoldMemory,
    GoldUpdate,
    Judgement,
    Prediction,
    QAItem,
    SystemMemory,
)
from northstar_agent_memory.models.port import Usage
from northstar_agent_memory.transcript import Message


# --- helpers ---------------------------------------------------------------------------


def item(id: str, qtype: str = "multi-session", abstention: bool = False) -> QAItem:
    return QAItem(id, "own:test", f"question {id}?", "gold", qtype, [], abstention=abstention)


def judgement(item_id: str, system: str, outcome: str, abstained: bool = False) -> Judgement:
    return Judgement(item_id, system, outcome, abstained, "code", "")


def gold(key: str, must: bool = True, **kw) -> GoldMemory:
    holder = "user" if must else "other_person"
    return GoldMemory(key, f"line {key}", "decision", holder, [f"m-{key}"], must, **kw)


def mem(id: str, key: str, status: str = "active", **kw) -> SystemMemory:
    """A system memory whose line is the gold line of `key`."""
    return SystemMemory(id, f"line {key}", status, **kw)


def same_line(g: GoldMemory, m: SystemMemory) -> bool:
    return g.line == m.line


# --- qa_scores -------------------------------------------------------------------------


def test_qa_scores_overall_by_type_and_abstention():
    items = [
        item("a", "knowledge-update"),
        item("b", "knowledge-update"),
        item("c", "temporal-reasoning"),
        item("d", "multi-session", abstention=True),
        item("e", "multi-session", abstention=True),
    ]
    js = [
        judgement("a", "B1", "correct"),
        judgement("b", "B1", "hallucinated"),
        judgement("c", "B1", "omitted", abstained=True),
        judgement("d", "B1", "correct", abstained=True),
        judgement("e", "B1", "hallucinated"),
    ]
    s = qa_scores(js, items)["B1"]
    assert (s.overall.correct, s.overall.hallucinated, s.overall.omitted) == (2, 2, 1)
    assert s.by_type["knowledge-update"].correct == 1
    assert s.by_type["knowledge-update"].hallucinated == 1
    assert s.by_type["temporal-reasoning"].omitted == 1
    assert s.by_type["multi-session"].total == 2  # abstention items stay in their type
    assert s.abstention_accuracy == pytest.approx(0.5)
    assert s.answer_accuracy == pytest.approx(1 / 3)
    assert s.answerable.total == 3 and s.abstention.total == 2


def test_qa_scores_missing_judgement_counts_as_omitted():
    items = [item("a"), item("b")]
    s = qa_scores([judgement("a", "B0", "correct")], items)["B0"]
    assert s.missing == ["b"]
    assert s.overall.omitted == 1
    assert s.overall.rate("correct") == 0.5


def test_qa_scores_ignores_other_items_and_keeps_systems_apart():
    js = [
        judgement("a", "B0", "correct"),
        judgement("a", "B1", "hallucinated"),
        judgement("zzz", "B0", "correct"),  # not in the scored items
    ]
    scores = qa_scores(js, [item("a")])
    assert set(scores) == {"B0", "B1"}
    assert scores["B0"].overall.total == 1
    assert scores["B1"].overall.correct == 0


def test_qa_scores_empty_and_no_abstention_items():
    assert qa_scores([], [item("a")]) == {}
    s = qa_scores([judgement("a", "B0", "correct")], [item("a")])["B0"]
    assert s.abstention_accuracy is None
    assert s.answer_accuracy == 1.0


def test_qa_scores_rejects_duplicates():
    with pytest.raises(ValueError, match="two judgements"):
        qa_scores([judgement("a", "B0", "correct"), judgement("a", "B0", "omitted")], [item("a")])
    with pytest.raises(ValueError, match="duplicate item ids"):
        qa_scores([], [item("a"), item("a")])


# --- extraction_scores -----------------------------------------------------------------


def test_extraction_empty_everything():
    r = extraction_scores([], [], same_line)
    assert r.score.total == 0
    assert r.recall is None and r.hallucination_rate is None
    assert r.false_memory_resistance is None


def test_extraction_all_omitted():
    gold_set = [gold("a"), gold("b"), gold("x", must=False)]
    r = extraction_scores(gold_set, [], same_line)
    assert (r.score.correct, r.score.hallucinated, r.score.omitted) == (0, 0, 2)
    assert r.omitted_keys == ["a", "b"]
    assert r.recall == 0.0
    assert r.hallucination_rate is None  # nothing recorded
    assert r.false_memory_resistance == 1.0  # recording nothing resists every distractor


def test_extraction_distractor_recorded_is_hallucinated():
    gold_set = [gold("a"), gold("x", must=False), gold("y", must=False)]
    system = [mem("m1", "a"), mem("m2", "x")]
    r = extraction_scores(gold_set, system, same_line)
    assert (r.score.correct, r.score.hallucinated, r.score.omitted) == (1, 1, 0)
    assert r.hallucinated_ids == ["m2"]
    assert r.distractors_recorded == ["x"]
    assert r.false_memory_resistance == pytest.approx(0.5)
    assert r.hallucination_rate == pytest.approx(0.5)


def test_extraction_memory_matching_no_gold_is_hallucinated():
    r = extraction_scores([gold("a")], [mem("m1", "a"), mem("m2", "nowhere")], same_line)
    assert r.hallucinated_ids == ["m2"]
    assert r.recall == 1.0


def test_extraction_superseded_counts_but_retracted_and_quarantined_do_not():
    gold_set = [gold("a"), gold("b"), gold("c")]
    system = [
        mem("m1", "a", "superseded"),
        mem("m2", "b", "retracted"),
        mem("m3", "c", "quarantined"),
    ]
    r = extraction_scores(gold_set, system, same_line)
    assert r.score.correct == 1
    assert sorted(r.omitted_keys) == ["b", "c"]
    assert r.n_recorded == 1 and r.hallucinated_ids == []


def test_extraction_duplicates_and_attribution_errors():
    gold_set = [gold("a"), gold("b", adopted_from="openai")]
    system = [
        mem("m1", "a"),
        mem("m2", "a"),  # a second memory of the same gold point
        mem("m3", "b"),  # the user adopted b from an AI, but the system calls it theirs
    ]
    r = extraction_scores(gold_set, system, same_line)
    assert r.score.correct == 2 and r.score.hallucinated == 0
    assert r.duplicates == 1
    assert r.attribution_errors == [("b", "m3")]
    ok = extraction_scores(gold_set, [mem("m3", "b", origin="adopted from codex")], same_line)
    assert ok.attribution_errors == []


def test_extraction_same_runs_once_per_pair():
    calls = []

    def same(g, m):
        calls.append((g.key, m.id))
        return g.line == m.line

    extraction_scores([gold("a"), gold("b")], [mem("m1", "a"), mem("m2", "b")], same)
    assert len(calls) == len(set(calls)) == 4


def test_extraction_rejects_duplicate_keys_and_ids():
    with pytest.raises(ValueError, match="key"):
        extraction_scores([gold("a"), gold("a")], [], same_line)
    with pytest.raises(ValueError, match="ids"):
        extraction_scores([gold("a")], [mem("m1", "a"), mem("m1", "a")], same_line)


# --- update_scores ---------------------------------------------------------------------


def upd(key="u1", old="old", new="new") -> GoldUpdate:
    return GoldUpdate(key, old, new, "m-9", "user_later_statement")


def test_update_correct():
    gold_set = [gold("old"), gold("new")]
    system = [mem("m1", "old", "superseded"), mem("m2", "new", supersedes="m1")]
    r = update_scores([upd()], gold_set, system, same_line)
    assert r.outcomes == {"u1": "correct"}
    assert (r.score.correct, r.score.hallucinated, r.score.omitted) == (1, 0, 0)
    assert r.correct_rate == 1.0 and r.stale_assertion_rate == 0.0


def test_update_omitted_old_stays_active_and_new_missing():
    r = update_scores([upd()], [gold("old"), gold("new")], [mem("m1", "old")], same_line)
    assert r.outcomes == {"u1": "omitted"}
    assert r.score.omitted == 1 and r.omitted_rate == 1.0
    assert r.stale_assertion_rate == 0.0


def test_update_stale_when_both_active():
    system = [mem("m1", "old"), mem("m2", "new")]
    r = update_scores([upd()], [gold("old"), gold("new")], system, same_line)
    assert r.outcomes == {"u1": "stale"}
    assert r.score.omitted == 1 and r.score.correct == 0  # stale counts as omitted
    assert r.stale_assertion_rate == 1.0
    assert r.omitted_rate == 1.0


def test_update_everything_missing_is_omitted():
    r = update_scores([upd()], [gold("old"), gold("new")], [], same_line)
    assert r.outcomes == {"u1": "omitted"}


def test_update_new_recorded_old_never_was_is_correct():
    r = update_scores([upd()], [gold("old"), gold("new")], [mem("m2", "new")], same_line)
    assert r.outcomes == {"u1": "correct"}


def test_update_wrong_value_is_hallucinated():
    system = [mem("m1", "old", "superseded"), mem("m2", "something else", supersedes="m1")]
    r = update_scores([upd()], [gold("old"), gold("new")], system, same_line)
    assert r.outcomes == {"u1": "wrong_value"}
    assert r.score.hallucinated == 1


def test_update_retracted_old_without_new_is_omitted():
    system = [mem("m1", "old", "retracted")]
    r = update_scores([upd()], [gold("old"), gold("new")], system, same_line)
    assert r.outcomes == {"u1": "omitted"}


def test_update_collateral_damage():
    gold_set = [gold("old"), gold("new"), gold("keep1"), gold("keep2"), gold("keep3")]
    system = [
        mem("m1", "old", "superseded"),
        mem("m2", "new"),
        mem("m3", "keep1", "superseded"),  # damaged
        mem("m4", "keep2", "retracted"),  # damaged
        mem("m5", "keep3"),  # fine
    ]
    r = update_scores([upd()], gold_set, system, same_line)
    assert r.outcomes == {"u1": "correct"}
    assert r.collateral == ["keep1", "keep2"]
    assert r.n_untouched == 3
    assert r.collateral_damage_rate == pytest.approx(2 / 3)
    assert r.score.hallucinated == 2 and r.score.correct == 1


def test_update_untouched_gold_never_recorded_is_not_collateral():
    r = update_scores([upd()], [gold("old"), gold("new"), gold("keep")], [mem("m2", "new")], same_line)
    assert r.collateral == [] and r.n_untouched == 0
    assert r.collateral_damage_rate is None


def test_update_distractor_gold_is_not_counted_as_untouched():
    gold_set = [gold("old"), gold("new"), gold("x", must=False)]
    system = [mem("m2", "new"), mem("m3", "x", "superseded")]
    r = update_scores([upd()], gold_set, system, same_line)
    assert r.collateral == [] and r.n_untouched == 0


def test_update_chain_scores_earlier_step_on_recorded_not_active():
    gold_set = [gold("a"), gold("b"), gold("c")]
    updates = [upd("u1", "a", "b"), upd("u2", "b", "c")]
    system = [
        mem("m1", "a", "superseded"),
        mem("m2", "b", "superseded", supersedes="m1"),
        mem("m3", "c", supersedes="m2"),
    ]
    r = update_scores(updates, gold_set, system, same_line)
    assert r.outcomes == {"u1": "correct", "u2": "correct"}
    assert r.collateral == []


def test_update_no_updates_still_finds_collateral():
    r = update_scores([], [gold("keep")], [mem("m1", "keep", "retracted")], same_line)
    assert r.outcomes == {} and r.collateral == ["keep"]
    assert r.correct_rate is None and r.stale_assertion_rate is None


def test_update_unknown_key_and_duplicate_update_keys():
    with pytest.raises(KeyError):
        update_scores([upd(new="ghost")], [gold("old")], [], same_line)
    with pytest.raises(ValueError, match="duplicate update"):
        update_scores([upd(), upd()], [gold("old"), gold("new")], [], same_line)


# --- citation_scores -------------------------------------------------------------------


def msgs(**texts: str) -> dict[str, Message]:
    return {
        id: Message(id, "s", n, "user", text, None) for n, (id, text) in enumerate(texts.items())
    }


def keyword_entails(premise: str, hypothesis: str) -> bool:
    """Entailed when every word of the hypothesis (as a keyword) appears in the premise."""
    return all(w in premise.lower() for w in hypothesis.lower().split())


def test_citation_empty_claims():
    r = citation_scores([], {}, keyword_entails)
    assert r.recall is None and r.precision is None


def test_citation_single_supported_claim():
    m = msgs(m1="we use sqlite")
    r = citation_scores([Claim("sqlite", ["m1"])], m, keyword_entails)
    assert (r.recall, r.precision) == (1.0, 1.0)
    assert r.irrelevant == []


def test_citation_alce_precision_example_with_redundant_citation():
    # Two citations each entail the claim alone: neither is needed, so neither is
    # irrelevant. A third that adds nothing is irrelevant.
    m = msgs(m1="we chose postgres", m2="postgres it is", m3="lunch at noon")
    r = citation_scores([Claim("postgres", ["m1", "m2", "m3"])], m, keyword_entails)
    assert r.recall == 1.0
    assert r.irrelevant == [(0, "m3")]
    assert r.n_citations == 3 and r.precise == 2
    assert r.precision == pytest.approx(2 / 3)


def test_citation_both_needed_jointly_are_precise():
    m = msgs(m1="the db is postgres", m2="hosted on fly", m3="unrelated")
    claim = Claim("postgres fly", ["m1", "m2"])
    r = citation_scores([claim], m, keyword_entails)
    assert r.recall == 1.0 and r.precision == 1.0
    assert r.irrelevant == []


def test_citation_joint_support_with_extra_irrelevant_message():
    m = msgs(m1="the db is postgres", m2="hosted on fly", m3="unrelated")
    r = citation_scores([Claim("postgres fly", ["m1", "m2", "m3"])], m, keyword_entails)
    assert r.recall == 1.0
    assert r.irrelevant == [(0, "m3")]
    assert r.precision == pytest.approx(2 / 3)


def test_citation_no_citations_is_unsupported():
    r = citation_scores([Claim("anything", [])], msgs(m1="anything"), keyword_entails)
    assert r.recall == 0.0 and r.unsupported == [0]
    assert r.precision == 0.0  # claims but no citations


def test_citation_unsupported_claim_citations_count_against_precision():
    m = msgs(m1="we chose postgres")
    r = citation_scores([Claim("mysql", ["m1"])], m, keyword_entails)
    assert r.recall == 0.0 and r.precision == 0.0
    assert r.n_citations == 1 and r.precise == 0


def test_citation_dangling_id_breaks_the_claim():
    m = msgs(m1="we chose postgres")
    r = citation_scores([Claim("postgres", ["m1", "m404"])], m, keyword_entails)
    assert r.recall == 0.0
    assert r.dangling == [(0, "m404")]


def test_citation_repeated_ids_count_once_and_speaker_is_in_the_premise():
    seen = []

    def entails(premise, hypothesis):
        seen.append(premise)
        return True

    m = msgs(m1="hello")
    r = citation_scores([Claim("x", ["m1", "m1"])], m, entails)
    assert r.n_citations == 1
    assert seen == ["user: hello"]


def test_citation_mixed_claims():
    m = msgs(m1="we chose postgres")
    claims = [Claim("postgres", ["m1"]), Claim("redis", ["m1"])]
    r = citation_scores(claims, m, keyword_entails)
    assert r.recall == 0.5
    assert r.precision == 0.5
    assert r.unsupported == [1]


# --- quote_exact -----------------------------------------------------------------------


def test_quote_exact_normalizes_whitespace_and_unicode():
    text = "We decided   to use\nSQLite\tfor now. Café stays."
    assert quote_exact("decided to use SQLite", text)
    assert quote_exact("Café stays", text)  # decomposed e + accent equals the NFC form
    assert quote_exact("  for now.  ", text)


def test_quote_exact_is_otherwise_exact():
    text = "We decided to use SQLite."
    assert not quote_exact("we decided", text)  # case matters
    assert not quote_exact("decided to use Postgres", text)
    assert not quote_exact("decided use", text)  # a skipped word is not a quote
    assert not quote_exact("", text)
    assert not quote_exact("   ", text)


def test_normalize_text():
    assert normalize_text(" a \n\t b ") == "a b"


# --- cost_summary ----------------------------------------------------------------------


def pred(system, tokens, cost, latency, calls=1, usage=None) -> Prediction:
    return Prediction("i", system, "a", context_tokens=tokens, cost_usd=cost, latency_s=latency,
                      calls=calls, usage=usage or Usage())


def test_cost_summary_per_system():
    preds = [pred("B1", 100, 0.5, float(s), 2, Usage(10, 5)) for s in range(1, 6)]
    preds += [pred("B0", 8000, 0.0, 0.2)]
    out = cost_summary(preds)
    b1 = out["B1"]
    assert b1.n == 5
    assert b1.mean_context_tokens == 100
    assert b1.total_cost_usd == pytest.approx(2.5)
    assert b1.mean_cost_usd == pytest.approx(0.5)
    assert b1.p50_latency_s == 3.0
    assert b1.p95_latency_s == pytest.approx(4.8)
    assert b1.calls == 10
    assert b1.usage == Usage(50, 25)
    assert out["B0"].p50_latency_s == out["B0"].p95_latency_s == 0.2


def test_cost_summary_empty():
    assert cost_summary([]) == {}


# --- bootstrap_ci and paired_difference ------------------------------------------------


def test_bootstrap_is_deterministic_for_a_seed():
    values = [0.1, 0.9, 0.4, 0.35, 0.8, 0.05, 0.6, 0.7, 0.2, 0.95]
    a = bootstrap_ci(values, seed=7)
    b = bootstrap_ci(values, seed=7)
    c = bootstrap_ci(values, seed=8)
    assert a == b
    assert a != c
    assert a.estimate == pytest.approx(0.505)
    assert a.low <= a.estimate <= a.high
    assert a.n == 10


def test_bootstrap_constant_values_and_empty():
    r = bootstrap_ci([1.0] * 5, seed=1)
    assert r.low == r.high == r.estimate == 1.0
    with pytest.raises(ValueError):
        bootstrap_ci([], seed=1)


def test_paired_difference_uses_common_items_only():
    js = []
    for i in range(20):
        js.append(judgement(f"i{i}", "A", "correct"))
        js.append(judgement(f"i{i}", "B", "correct" if i % 2 else "hallucinated"))
    js.append(judgement("only-a", "A", "hallucinated"))
    d = paired_difference(js, "A", "B", seed=3)
    assert d.n == 20
    assert d.accuracy_a == 1.0 and d.accuracy_b == 0.5
    assert d.difference.estimate == pytest.approx(0.5)
    assert d.difference.low > 0  # A is reliably better on these items
    assert d == paired_difference(js, "A", "B", seed=3)


def test_paired_difference_interval_spans_zero_when_even():
    js = []
    for i in range(10):
        js.append(judgement(f"i{i}", "A", "correct" if i % 2 else "omitted"))
        js.append(judgement(f"i{i}", "B", "omitted" if i % 2 else "correct"))
    d = paired_difference(js, "A", "B", seed=3)
    assert d.difference.estimate == 0.0
    assert d.difference.low < 0 < d.difference.high


def test_paired_difference_without_common_items():
    with pytest.raises(ValueError, match="in common"):
        paired_difference([judgement("a", "A", "correct"), judgement("b", "B", "correct")], "A", "B", seed=1)


def test_wilson_interval():
    low, high = wilson_interval(0, 10)
    assert low == 0.0 and 0.2 < high < 0.35
    low, high = wilson_interval(10, 10)
    assert high == 1.0 and low > 0.65
    with pytest.raises(ValueError):
        wilson_interval(0, 0)
