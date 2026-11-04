"""Measures from normal use, on invented transcripts (tests/eval/fixtures/claude_code)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from northstar_agent_memory.eval import normal_use as nu
from northstar_agent_memory.eval.claude_code import Compaction, ParsedSession, TurnUsage, parse_projects
from northstar_agent_memory.models.schema import assert_strict
from northstar_agent_memory.models.stub import StubModel
from northstar_agent_memory.paths import eval_root
from northstar_agent_memory.transcript import Message, Source

FIXTURES = Path(__file__).parent / "fixtures" / "claude_code"
UTC = nu.Params(tz="UTC")


@pytest.fixture(scope="module")
def sessions():
    return parse_projects(FIXTURES)


@pytest.fixture(scope="module")
def by_name(sessions):
    """The fixture sessions by file: ledger1..4, garden1, garden2."""
    names = {"ledger_s1": "l1", "ledger_s2": "l2", "ledger_s3": "l3", "ledger_s4": "l4",
             "garden_s1": "g1", "garden_s2": "g2"}
    return {names[Path(s.path).stem]: s for s in sessions}


def fake(project, start, end, turns=("hello there",), *, tokens=0, model="claude-opus-5-5", compacted=False, sid=None):
    """A session built by hand, for cases the fixtures do not cover."""
    sid = sid or f"fake-{project}-{start}"
    messages = [
        Message(f"{sid}:{i}", sid, i, "user", t, start, "typed", "claude-code") for i, t in enumerate(turns)
    ]
    usage = [TurnUsage("m1", end, model, input_tokens=tokens)] if tokens else []
    return ParsedSession(
        source=Source(sid, "chat", "claude-code", project, None, start, messages),
        path=f"/fake/{sid}.jsonl",
        usage=usage,
        compactions=[Compaction(end, "auto")] if compacted else [],
        first_timestamp=start,
        last_timestamp=end,
    )


# --- context used ---------------------------------------------------------------------------


def test_window_for_uses_table_then_default():
    assert nu.window_for("claude-opus-5-5") == 1_000_000
    assert nu.window_for("some-other-model") == 1_000_000
    assert nu.window_for(None) == 1_000_000
    p = nu.Params(window_tokens=128_000, window_table={"claude-haiku": 200_000, "claude-opus-5": 500_000})
    assert nu.window_for("claude-haiku-5-5", p) == 200_000
    assert nu.window_for("claude-opus-5-5", p) == 500_000  # the longest prefix wins
    assert nu.window_for("claude-sonnet-5-5", p) == 1_000_000  # the built-in table
    assert nu.window_for("gpt-x", p) == 128_000


def test_context_used_timeline_and_thresholds(by_name):
    ctx = nu.context_used(by_name["l1"])
    assert [p.tokens for p in ctx.timeline] == [12003, 12805, 150605, 300905, 522010, 40004, 40504]
    assert ctx.timeline[0].timestamp == "2026-03-02T09:00:20.000Z"
    assert ctx.max_tokens == 522010  # the sidechain's 900,000 is not counted
    assert ctx.max_share == pytest.approx(0.52201)
    assert (ctx.passed_half_window, ctx.passed_two_thirds, ctx.window_exceeded) == (True, False, False)
    l4 = nu.context_used(by_name["l4"])
    assert (l4.max_tokens, l4.passed_half_window, l4.passed_two_thirds) == (700003, True, True)
    l3 = nu.context_used(by_name["l3"])
    assert (l3.max_tokens, l3.passed_half_window) == (100503, False)


def test_context_used_window_is_a_parameter(by_name):
    small = nu.Params(window_table={"claude-": 400_000})
    l3 = nu.context_used(by_name["l3"], small)
    assert l3.window_tokens == 400_000 and l3.max_share == pytest.approx(100503 / 400_000)
    assert not l3.passed_half_window
    too_small = nu.context_used(by_name["l1"], nu.Params(window_table={"claude-": 100_000}))
    assert too_small.window_exceeded and too_small.max_share == 1.0 and too_small.passed_two_thirds


def test_context_used_with_no_usage():
    ctx = nu.context_used(fake("/p", "2026-03-01T10:00:00Z", "2026-03-01T11:00:00Z"))
    assert (ctx.timeline, ctx.max_tokens, ctx.max_share, ctx.passed_half_window) == ([], 0, 0.0, False)


# --- session statistics ---------------------------------------------------------------------


def test_session_stats(by_name):
    st = nu.session_stats(by_name["l1"], UTC)
    assert (st.typed_user_turns, st.assistant_turns, st.model_responses, st.tool_calls) == (4, 6, 7, 2)
    assert st.duration_s == 9025.0  # 09:00:05 to 11:30:30
    assert st.compactions == 1
    assert st.max_context_share == pytest.approx(0.52201) and st.passed_half_window and not st.passed_two_thirds
    assert (st.active_days, st.active_dates) == (1, ["2026-03-02"])
    assert (st.project, st.git_branch, st.models) == ("/home/demo/work/ledger-sync", "main", ["claude-opus-5-5"])
    l2 = nu.session_stats(by_name["l2"], UTC)
    assert (l2.typed_user_turns, l2.tool_calls, l2.compactions) == (6, 2, 0)


def test_active_days_follow_the_time_zone():
    s = fake("/p", "2026-03-01T23:30:00+00:00", "2026-03-02T00:30:00+00:00")
    assert nu.session_stats(s, UTC).active_days == 2
    assert nu.session_stats(s, nu.Params(tz="Pacific/Auckland")).active_dates == ["2026-03-02"]


# --- continuity -----------------------------------------------------------------------------


def test_continuity_on_the_fixtures(sessions):
    records = nu.continuity(sessions, UTC)
    by_start = {(r.project.rsplit("/", 1)[1], r.started_at[:13]): r for r in records}
    expected = {
        ("ledger-sync", "2026-03-02T09"): ("fresh", False),
        ("ledger-sync", "2026-03-02T13"): ("continuing", True),  # 1.5 h after a session that compacted
        ("garden-notes", "2026-03-03T08"): ("fresh", False),
        ("garden-notes", "2026-03-03T11"): ("continuing", False),  # soon after, but the last was small
        ("ledger-sync", "2026-03-20T10"): ("fresh", False),  # 17.8 days after the last
        ("ledger-sync", "2026-03-25T10"): ("continuing", False),  # 5 days
    }
    assert {k: (r.status, r.restart) for k, r in by_start.items()} == expected
    restart = by_start[("ledger-sync", "2026-03-02T13")]
    assert restart.gap_hours == pytest.approx(1.4916, abs=1e-3)
    assert restart.previous_passed_half and restart.previous_compacted
    assert by_start[("ledger-sync", "2026-03-20T10")].gap_hours == pytest.approx(427.0)
    assert by_start[("ledger-sync", "2026-03-02T09")].previous_session_id is None


def test_continuity_is_per_project(sessions, by_name):
    records = {r.session_id: r for r in nu.continuity(sessions, UTC)}
    assert records[by_name["g2"].id].previous_session_id == by_name["g1"].id
    assert records[by_name["l3"].id].previous_session_id == by_name["l2"].id
    assert records[by_name["g1"].id].status == "fresh"  # the ledger sessions before it do not count


def test_continuity_parameters(sessions):
    def statuses(p):
        return [(r.status, r.restart) for r in nu.continuity(sessions, p)]

    base = statuses(UTC)
    wider = statuses(nu.Params(tz="UTC", continue_days=30))
    assert wider[4] == ("continuing", False) and base[4] == ("fresh", False)
    tight = statuses(nu.Params(tz="UTC", restart_hours=1))
    assert tight[1] == ("continuing", False)
    ctx_only = statuses(nu.Params(tz="UTC", window_table={"claude-": 400_000}))
    assert ctx_only[1][1] is True


def test_restart_needs_a_full_or_compacted_previous_session():
    day = "2026-03-10T"
    full = fake("/p", day + "08:00:00+00:00", day + "09:00:00+00:00", tokens=600_000)
    compacted = fake("/p", day + "08:00:00+00:00", day + "09:00:00+00:00", compacted=True)
    small = fake("/p", day + "08:00:00+00:00", day + "09:00:00+00:00", tokens=10_000)
    after = fake("/p", day + "12:00:00+00:00", day + "13:00:00+00:00")
    late = fake("/p", day + "16:00:00+00:00", day + "17:00:00+00:00")
    assert [r.restart for r in nu.continuity([full, after])] == [False, True]
    assert [r.restart for r in nu.continuity([compacted, after])] == [False, True]
    assert [r.restart for r in nu.continuity([small, after])] == [False, False]
    assert [r.restart for r in nu.continuity([full, late])] == [False, False]  # 7 hours later
    assert [r.status for r in nu.continuity([full, late])] == ["fresh", "continuing"]


def test_continuity_overlapping_sessions_and_no_project():
    a = fake("/p", "2026-03-10T08:00:00+00:00", "2026-03-10T12:00:00+00:00")
    b = fake("/p", "2026-03-10T09:00:00+00:00", "2026-03-10T10:00:00+00:00")
    r = nu.continuity([b, a])  # input order does not matter
    assert [x.session_id for x in r] == [a.id, b.id]
    assert r[1].status == "continuing" and r[1].gap_hours == 0.0
    x, y = fake(None, "2026-03-10T08:00:00+00:00", "2026-03-10T09:00:00+00:00"), fake(
        None, "2026-03-11T08:00:00+00:00", "2026-03-11T09:00:00+00:00"
    )
    assert [r.status for r in nu.continuity([x, y])] == ["fresh", "continuing"]


# --- re-explanation candidates ---------------------------------------------------------------


def msg(text, **meta):
    return Message("m:0", "m", 0, "user", text, None, "typed", "claude-code", meta=meta)


def test_split_units_sentences():
    units = nu.split_units(msg("Fix the build. It fails on CI!\n- keep the cache\nOk. What about v2.1? Yes."))
    assert [u[0] for u in units] == ["Fix the build.", "It fails on CI!", "- keep the cache", "What about v2.1?"]
    assert all(u[1:] == ("sentence", False) for u in units)  # "Ok." and "Yes." are under two words


def test_split_units_pasted_text_becomes_paragraphs():
    text = "My notes:\nFirst point about sync.\n\nSecond point, with more detail.\nStill the second."
    start = text.index("First")
    units = nu.split_units(msg(text, paste_ranges=[[start, len(text)]]))
    assert units == [
        ("My notes:", "sentence", False),  # two words, kept
        ("First point about sync.", "paragraph", True),
        ("Second point, with more detail.\nStill the second.", "paragraph", True),
    ]
    long_text = ("A long paragraph of words. " * 40 + "\n\n") * 3
    long_units = nu.split_units(msg(long_text), nu.Params(long_text_chars=500))
    assert len(long_units) == 3 and all(u[1:] == ("paragraph", True) for u in long_units)


def test_unit_cap_and_k_turns():
    turns = [f"Sentence number {i} about topic. Another one {i} follows here." for i in range(8)]
    s1 = fake("/p", "2026-03-01T08:00:00+00:00", "2026-03-01T09:00:00+00:00", turns[:1])
    s2 = fake("/p", "2026-03-02T08:00:00+00:00", "2026-03-02T09:00:00+00:00", turns)
    out = nu.reexplanation_candidates([s1, s2], nu.Params(k_turns=3, max_units=4))
    assert [u.unit.session_id for u in out] == [s2.id] * 4
    assert [u.unit.turn_index for u in out] == [0, 0, 1, 1]
    assert {u.unit.session_units for u in out} == {6}  # three turns, two units each, before the cap
    assert nu.reexplanation_candidates([s1, s2], nu.Params(k_turns=1))[-1].unit.turn_index == 0


def test_candidates_cover_only_continuing_sessions(sessions, by_name):
    out = nu.reexplanation_candidates(sessions, UTC)
    assert {u.unit.session_id for u in out} == {by_name[k].id for k in ("l2", "l4", "g2")}


def test_candidates_come_from_earlier_sessions_of_the_same_project(sessions, by_name):
    out = nu.reexplanation_candidates(sessions, UTC)
    l2 = [u for u in out if u.unit.session_id == by_name["l2"].id]
    assert l2 and {h.session_id for u in l2 for h in u.hits} == {by_name["l1"].id}
    g2 = [u for u in out if u.unit.session_id == by_name["g2"].id]
    first = g2[0]
    assert first.unit.text.startswith("We decided per-device operation logs")
    assert first.hits == []  # said in the ledger project, not in this one
    assert g2[1].hits[0].session_id == by_name["g1"].id
    l4 = [u for u in out if u.unit.session_id == by_name["l4"].id]
    assert {h.session_id for u in l4 for h in u.hits} >= {by_name["l3"].id, by_name["l2"].id}


def test_a_restated_decision_finds_the_message_that_said_it(sessions, by_name):
    out = nu.reexplanation_candidates(sessions, UTC)
    unit = next(u for u in out if u.unit.text.startswith("We decided on per-device operation logs"))
    assert len(unit.hits) == 4 <= nu.Params().top_k
    top = unit.hits[0]
    assert (top.session_id, top.ordinal, top.speaker) == (by_name["l1"].id, 0, "user")
    scores = [h.score for h in unit.hits]
    assert scores == sorted(scores, reverse=True) and scores[0] > 0
    assert "[" in top.excerpt and top.occurred_at == "2026-03-02T09:00:05.000Z"
    assistant_hits = [h for u in out for h in u.hits if h.speaker == "assistant"]
    assert assistant_hits  # assistant text is searched too
    tombstone = next(u for u in out if u.unit.text == "Tombstones stay for 30 days.")
    assert tombstone.hits[0].speaker == "assistant"


def test_top_k_is_a_parameter(sessions):
    out = nu.reexplanation_candidates(sessions, nu.Params(tz="UTC", top_k=2))
    assert max(len(u.hits) for u in out) == 2


def test_pasted_paragraphs_are_flagged(sessions, by_name):
    out = [u for u in nu.reexplanation_candidates(sessions, UTC) if u.unit.session_id == by_name["l2"].id]
    pasted = [u for u in out if u.unit.pasted]
    assert [u.unit.text[:20] for u in pasted] == [
        "The oplog format is ", "Every operation carr", "Replicas exchange on",
    ]
    assert all(u.unit.kind == "paragraph" and not u.reference for u in pasted)


def test_only_the_first_k_turns_are_scanned(sessions, by_name):
    out = nu.reexplanation_candidates(sessions, UTC)
    l2_turns = {u.unit.turn_index for u in out if u.unit.session_id == by_name["l2"].id}
    assert l2_turns == {0, 1, 2, 3, 4}  # the sixth turn, the correction, is not scanned
    assert not any("Go back" in u.unit.text for u in out)


def test_short_mentions_by_name_are_references(sessions, by_name):
    out = nu.reexplanation_candidates(sessions, UTC)
    refs = {u.unit.text: u.reference for u in out if u.unit.session_id == by_name["l2"].id}
    assert refs["Continue with the tie-break rule."] is True
    assert refs["Pick up the sync engine again."] is True
    assert refs["What did we decide about tombstone retention?"] is False  # words the record lacks
    assert refs["Now add a retry to the uploader."] is False
    assert refs["We decided on per-device operation logs with Lamport clocks, and the lowest device id "
                "wins a tie."] is False  # 17 words
    l4 = {u.unit.text: u.reference for u in out if u.unit.session_id == by_name["l4"].id}
    assert l4["Back to the export screen for monthly statements."] is True
    assert l4["Statements are grouped by month and each month shows a total."] is False  # a statement


def test_reference_rule_parameters(sessions, by_name):
    p = nu.Params(tz="UTC", reference_words=6)
    refs = {u.unit.text: u.reference for u in nu.reexplanation_candidates(sessions, p)
            if u.unit.session_id == by_name["l2"].id}
    assert refs["Continue with the tie-break rule."] is True  # five words, under the bar of six
    p = nu.Params(tz="UTC", reference_words=5)  # under 5 words: five is no longer short
    refs = {u.unit.text: u.reference for u in nu.reexplanation_candidates(sessions, p)
            if u.unit.session_id == by_name["l2"].id}
    assert refs["Continue with the tie-break rule."] is False


def test_search_survives_query_syntax_in_the_text():
    idx = nu._Index(nu.Params())
    idx.add(fake("/p", "2026-03-01T08:00:00+00:00", "2026-03-01T09:00:00+00:00",
                 ["NOT near AND or the (rule) \"quoted\" star* col:on"]))
    terms = nu.content_terms('NOT near AND or "quoted" star* col:on NEAR(a b) -x ^y')
    assert idx.search(terms)
    assert idx.search([]) == []
    assert nu._Index(nu.Params()).search(["anything"]) == []
    idx.close()


def test_content_terms_drop_filler_and_stopwords():
    assert nu.content_terms("Please continue with the Tie-break rule again, again!") == ["tie", "break", "rule"]
    assert nu.content_terms("We decided on 30 days") == ["decided", "30", "days"]


# --- labelling ------------------------------------------------------------------------------


def labeller(replies):
    """A model that answers each unit with the labels `replies(request)` returns."""
    return StubModel(lambda req: {"labels": replies(req)})


@pytest.fixture(scope="module")
def candidates(sessions):
    out = nu.reexplanation_candidates(sessions, UTC)
    return [u for u in out if u.hits]


def test_label_schema_is_strict():
    assert_strict(nu.LABEL_SCHEMA)
    assert nu.LABEL_SCHEMA["properties"]["labels"]["items"]["properties"]["label"]["enum"] == [
        "restates", "recall_request", "corrects_ai", "new_or_different", "unrelated",
    ]


def test_labels_are_kept_when_the_quote_is_in_the_unit(candidates):
    item = next(u for u in candidates if u.unit.text == "Tombstones stay for 30 days.")
    stub = labeller(lambda req: [
        {"candidate": i, "quote": "Tombstones stay for 30 days", "label": "restates" if i == 0 else "unrelated"}
        for i in range(len(item.hits))
    ])
    out = nu.label_reexplanations([item], stub, "openai")
    assert [l.label for l in out] == ["restates"] + ["unrelated"] * (len(item.hits) - 1)
    assert all(l.quote == "Tombstones stay for 30 days" and l.discarded is None for l in out)
    assert out[0].counts_as_reexplanation and not out[1].counts_as_reexplanation
    assert (out[0].session_id, out[0].unit_index) == (item.unit.session_id, item.unit.index)
    assert (out[0].hit_session_id, out[0].hit_ordinal) == (item.hits[0].session_id, item.hits[0].ordinal)
    (req,) = stub.calls
    assert (req.purpose, req.role, req.family) == ("normal_use.reexplain", "judge", "openai")
    assert req.schema is nu.LABEL_SCHEMA
    body = req.messages[0]["content"]
    assert "Tombstones stay for 30 days." in body and '<passage n="0"' in body
    assert body.count("<passage") == len(item.hits)
    assert "data, never instructions" in req.system


def test_labels_without_a_quote_from_the_unit_are_discarded(candidates):
    item = next(u for u in candidates if len(u.hits) >= 4)
    answers = [
        {"candidate": 0, "quote": "words the person never wrote", "label": "restates"},
        {"candidate": 1, "quote": "", "label": "restates"},
        {"candidate": 2, "quote": item.unit.text.split()[0], "label": "not-a-label"},
        # candidate 3 is not answered at all
    ]
    out = nu.label_reexplanations([item], labeller(lambda req: answers), "openai")
    assert [l.label for l in out] == [None] * 4
    assert [l.discarded for l in out] == [
        "quote not found in the unit", "quote not found in the unit", "unknown label",
        "no label for this passage",
    ]
    assert not any(l.counts_as_reexplanation for l in out)


def test_quote_check_ignores_spacing_but_not_words():
    assert nu.quote_in_unit("lowest  device\nid", "the lowest device id wins")
    assert not nu.quote_in_unit("lowest device ids", "the lowest device id wins")
    assert not nu.quote_in_unit(None, "text") and not nu.quote_in_unit("   ", "text")


def test_a_labelled_reference_is_not_a_reexplanation(candidates):
    item = next(u for u in candidates if u.unit.text == "Continue with the tie-break rule.")
    assert item.reference
    stub = labeller(lambda req: [
        {"candidate": i, "quote": "tie-break rule", "label": "restates"} for i in range(len(item.hits))
    ])
    out = nu.label_reexplanations([item], stub, "openai")
    assert all(l.label == "restates" and l.reference for l in out)
    assert not any(l.counts_as_reexplanation for l in out)


def test_the_family_rule(candidates):
    stub = labeller(lambda req: [])
    with pytest.raises(ValueError, match="family rule"):
        nu.label_reexplanations(candidates, stub, "anthropic")
    assert stub.calls == []
    nu.label_reexplanations(candidates[:1], stub, "anthropic", allow_same_family=True)
    assert len(stub.calls) == 1


def test_units_with_no_passage_or_a_low_score_make_no_call(sessions, by_name):
    everything = nu.reexplanation_candidates(sessions, UTC)
    assert any(not u.hits for u in everything)
    stub = labeller(lambda req: [])
    out = nu.label_reexplanations(everything, stub, "openai")
    assert len(stub.calls) == sum(1 for u in everything if u.hits)
    assert len(out) == sum(len(u.hits) for u in everything)
    stub2 = labeller(lambda req: [])
    nu.label_reexplanations(everything, stub2, "openai", min_score=1e9)
    assert stub2.calls == []


def test_no_structured_output_discards_the_labels(candidates):
    out = nu.label_reexplanations(candidates[:1], StubModel(lambda req: {"other": 1}), "openai")
    assert out and all(l.label is None for l in out)


# --- corrections ------------------------------------------------------------------------------


def test_correction_candidates_on_the_fixtures(sessions, by_name):
    found = nu.correction_candidates(sessions, UTC)
    assert [(c.session_id, c.pattern) for c in found] == [
        (by_name["l2"].id, "go back"),
        (by_name["l4"].id, "i told you"),
    ]
    assert found[0].text.startswith("Go back to the previous version of the merge function")
    assert found[0].project == "/home/demo/work/ledger-sync" and found[0].occurred_at.startswith("2026-03-02T14:30")


@pytest.mark.parametrize(
    "text",
    [
        "Revert that change please.",
        "Undo the last edit.",
        "That's not what I asked for.",
        "That’s not what I meant.",
        "That is not what I wanted.",
        "We already decided this last week.",
        "As I said, keep it simple.",
        "I told you to use Lamport clocks.",
        "I already told you.",
        "Use the previous version instead.",
        "Can you go back to the old version?",
        "Roll back the migration.",
        "Put it back the way it was.",
        "We ruled that out on Monday.",
        "I didn't ask for a rewrite.",
    ],
)
def test_correction_phrases(text):
    s = fake("/p", "2026-03-01T08:00:00+00:00", "2026-03-01T09:00:00+00:00", [text])
    assert len(nu.correction_candidates([s])) == 1


@pytest.mark.parametrize(
    "text",
    [
        "Please add a retry to the uploader.",
        "We decided per-device operation logs with Lamport clocks.",
        "Go to the settings page.",
        "I said hello to the new teammate.",
        "Looks good, thanks.",
    ],
)
def test_ordinary_turns_are_not_corrections(text):
    s = fake("/p", "2026-03-01T08:00:00+00:00", "2026-03-01T09:00:00+00:00", [text])
    assert nu.correction_candidates([s]) == []


def test_pasted_text_is_not_searched_for_corrections():
    text = "Here is a summary:\nAs I said, revert it. We already decided this."
    start = text.index("As I said")
    pasted = fake("/p", "2026-03-01T08:00:00+00:00", "2026-03-01T09:00:00+00:00", [text])
    pasted.source.messages[0].meta["paste_ranges"] = [[start, len(text)]]
    assert nu.correction_candidates([pasted]) == []


def test_correction_text_is_capped():
    s = fake("/p", "2026-03-01T08:00:00+00:00", "2026-03-01T09:00:00+00:00", ["Revert it. " + "x" * 5000])
    (c,) = nu.correction_candidates([s], nu.Params(correction_chars=100))
    assert len(c.text) == 100


# --- the report ---------------------------------------------------------------------------------


NOW = datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc)


def test_report_window_params_and_totals(sessions):
    report = nu.build_report(sessions, UTC, since="2026-03-01", now=NOW)
    assert report.window == {
        "first_start": "2026-03-02T09:00:05+00:00",
        "last_end": "2026-03-25T11:30:00+00:00",
        "first_day": "2026-03-02",
        "last_day": "2026-03-25",
        "days": 4,
        "sessions": 6,
    }
    assert report.since == "2026-03-01" and report.generated_at == NOW.isoformat()
    assert report.params["continue_days"] == 14 and report.params["restart_hours"] == 6
    assert report.params["k_turns"] == 5 and report.params["tz"] == "UTC"
    assert report.params["window_tokens"] == 1_000_000
    assert len(report.sessions) == len(report.context) == len(report.continuity) == 6
    assert report.skipped_lines["unknown:progress"] == 1 and report.skipped_lines["sidechain"] >= 2
    assert report.labels is None and len(report.corrections) == 2


def test_weekly_before_and_after_labelling(sessions):
    report = nu.build_report(sessions, UTC, now=NOW)
    weeks = report.weekly()
    assert [w.week_start for w in weeks] == ["2026-03-02", "2026-03-16", "2026-03-23"]
    w1, w2, w3 = weeks
    assert (w1.sessions, w1.continuing, w1.fresh, w1.restarts) == (4, 2, 2, 1)
    assert (w1.typed_user_turns, w1.assistant_turns, w1.tool_calls, w1.compactions) == (13, 12, 4, 1)
    assert (w1.active_days, w1.passed_half_window, w1.passed_two_thirds) == (2, 1, 0)
    assert (w1.correction_candidates, w1.units, w1.references) == (1, 12, 2)
    assert (w2.sessions, w2.continuing, w2.units) == (1, 0, 0)
    assert (w3.sessions, w3.continuing, w3.passed_two_thirds, w3.correction_candidates) == (1, 1, 1, 1)
    assert w1.reexplanations is None and w1.reexplanations_per_continuing is None and w1.labelled is None

    def answer(req):
        n = req.messages[0]["content"].count("<passage")
        return [{"candidate": i, "quote": "the", "label": "restates"} for i in range(n)]

    stub = labeller(answer)
    # "the" is not in every unit, so some labels are discarded
    report.labels = nu.label_reexplanations(report.units, stub, "openai")
    labelled = report.weekly()
    assert all(w.labelled is not None for w in labelled)
    total_kept = sum(1 for l in report.labels if l.label)
    assert sum(w.labelled for w in labelled) == total_kept > 0
    kept_restates = {(l.session_id, l.unit_index) for l in report.labels if l.counts_as_reexplanation}
    assert sum(w.reexplanations for w in labelled) == len(kept_restates)
    first = labelled[0]
    assert first.reexplanations_per_continuing == first.reexplanations / first.continuing
    assert labelled[1].reexplanations == 0 and labelled[1].reexplanations_per_continuing is None


def test_weekly_counts_re_explanations_per_continuing_session(sessions, by_name):
    report = nu.build_report(sessions, UTC, now=NOW)
    # One kept "restates" label on a non-reference unit in the first week's continuing sessions.
    target = next(u for u in report.units if u.unit.text == "Tombstones stay for 30 days.")
    other = next(u for u in report.units if u.reference)
    labels = nu.label_reexplanations(
        [target, other],
        labeller(lambda req: [{"candidate": 0, "quote": "Tombstones stay" if "Tombstones" in req.messages[0]["content"]
                               else "tie-break rule", "label": "restates"}]),
        "openai",
    )
    report.labels = labels
    first = report.weekly()[0]
    assert first.reexplanations == 1  # the reference is not counted
    assert first.continuing_with_reexplanation == 1
    assert first.reexplanations_per_continuing == 0.5  # two continuing sessions that week


def test_weeks_follow_the_time_zone():
    a = fake("/p", "2026-03-01T23:30:00+00:00", "2026-03-01T23:50:00+00:00")  # Sunday in UTC
    assert nu.build_report([a], UTC).weekly()[0].week_start == "2026-02-23"
    assert nu.build_report([a], nu.Params(tz="Pacific/Auckland")).weekly()[0].week_start == "2026-03-02"


def test_report_json(sessions):
    report = nu.build_report(sessions, UTC, now=NOW)
    data = json.loads(report.to_json())
    assert set(data) >= {
        "generated_at", "since", "window", "params", "sessions", "context", "continuity",
        "units", "corrections", "skipped_lines", "labels", "weeks",
    }
    assert data["params"]["continue_days"] == 14 and data["window"]["sessions"] == 6
    assert "timeline" not in data["context"][0]
    assert json.loads(report.to_json(timelines=True))["context"][0]["timeline"][0]["tokens"] == 12003
    assert data["weeks"][0]["week_start"] == "2026-03-02" and data["labels"] is None
    assert data["units"][0]["unit"]["text"] and "hits" in data["units"][0]
    json.dumps(data)  # nothing left that cannot be written


def test_report_is_saved_under_the_evaluation_root_by_default(sessions):
    report = nu.build_report(sessions, UTC, now=NOW)
    path = report.save()
    assert path.is_file() and eval_root() in path.parents
    assert path.parent.name == "normal_use" and path.suffix == ".json"
    assert json.loads(path.read_text(encoding="utf-8"))["window"]["sessions"] == 6
    elsewhere = report.save(path.parent / "chosen.json")
    assert elsewhere.name == "chosen.json"
    assert nu.default_report_path(NOW).name == "claude-code-20260401T120000Z.json"
    assert eval_root() in nu.default_report_path(NOW).parents


def test_analyse_reads_a_folder_end_to_end():
    report = nu.analyse(FIXTURES, UTC, now=NOW)
    assert report.window["sessions"] == 6 and len(report.units) > 0
    later = nu.analyse(FIXTURES, UTC, since="2026-03-10", now=NOW)
    assert later.window["sessions"] == 2 and later.since == "2026-03-10"
    # The earlier sessions are gone from the folder view, so nothing continues from them.
    assert [r.status for r in later.continuity] == ["fresh", "continuing"]


def test_two_periods_compare_on_the_same_parameters(sessions):
    first = nu.build_report([s for s in sessions if s.started < datetime(2026, 3, 10, tzinfo=timezone.utc)], UTC)
    second = nu.build_report([s for s in sessions if s.started >= datetime(2026, 3, 10, tzinfo=timezone.utc)], UTC)
    assert first.params == second.params
    assert first.window["last_end"] < second.window["first_start"]


def test_a_unit_restating_several_passages_counts_once(sessions):
    report = nu.build_report(sessions, UTC, now=NOW)
    target = next(u for u in report.units if u.unit.text == "Tombstones stay for 30 days.")
    assert len(target.hits) >= 2
    n = len(target.hits)
    report.labels = nu.label_reexplanations(
        [target],
        labeller(lambda req: [{"candidate": i, "quote": "Tombstones stay", "label": "restates"} for i in range(n)]),
        "openai",
    )
    assert sum(l.counts_as_reexplanation for l in report.labels) == n
    assert report.weekly()[0].reexplanations == 1
