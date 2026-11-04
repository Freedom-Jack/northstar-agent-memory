"""LongMemEval loading and selection: a tiny invented file in the real format, plus the real
file when it is present."""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from northstar_agent_memory import config
from northstar_agent_memory.eval import longmemeval as L
from northstar_agent_memory.eval.types import QAItem
from northstar_agent_memory.transcript import Source

FIXTURE = Path(__file__).parent / "fixtures" / "lme_tiny.json"


@pytest.fixture(scope="module")
def items() -> list[QAItem]:
    return L.to_items(L.load(FIXTURE))


def by_id(items, qid) -> QAItem:
    return next(i for i in items if i.id == qid)


def test_loads_five_items(items):
    assert [i.id for i in items] == ["ku_001", "tr_001", "ms_001", "su_001", "ku_002_abs"]
    assert {i.dataset for i in items} == {"longmemeval_s"}
    assert {i.question_type for i in items} >= {"knowledge-update", "temporal-reasoning", "multi-session"}


def test_sessions_become_sources_with_message_ids(items):
    item = by_id(items, "su_001")
    first = item.haystack[0]
    assert isinstance(first, Source)
    assert first.id == "s001" and first.app == "longmemeval"
    assert first.meta["lme_session_id"] == "answer_280352e9" and first.meta["date_raw"] == "2023/09/20 (Wed) 16:00"
    assert [m.id for m in first.messages] == [f"s001:{k}" for k in range(4)]
    assert all(m.source_id == "s001" for m in first.messages)
    assert [m.speaker for m in first.messages] == ["user", "assistant", "user", "assistant"]
    assert all(m.model_family is None for s in item.haystack for m in s.messages)
    assert first.started_at == "2023-09-20T16:00:00"


def test_haystack_is_sorted_by_date_even_when_the_file_is_not(items):
    item = by_id(items, "ku_001")
    assert [s.id for s in item.haystack] == ["s001", "s002", "s003"]  # ids follow the date order
    assert [s.meta["lme_session_id"] for s in item.haystack] == [
        "sharegpt_Qm2xKa1_0", "ultrachat_231069", "answer_4be1b6b4_1",
    ]  # the file listed the last one first
    dates = [s.started_at for s in item.haystack]
    assert dates == sorted(dates)


def test_evidence_ids_come_from_has_answer_turns(items):
    assert by_id(items, "su_001").evidence_message_ids == ["s001:0"]
    assert by_id(items, "ku_001").evidence_message_ids == ["s003:0"]
    assert by_id(items, "tr_001").evidence_message_ids == ["s001:0", "s003:0"]
    assert by_id(items, "ms_001").evidence_message_ids == ["s001:0", "s003:0"]


def test_abstention_flag_follows_the_suffix(items):
    assert [i.abstention for i in items] == [False, False, False, False, True]
    assert by_id(items, "ku_002_abs").evidence_message_ids == []


def test_numeric_answers_become_strings_and_dates_iso(items):
    item = by_id(items, "tr_001")
    assert item.gold_answer == "12"
    assert item.question_date == "2023-05-01T20:00:00"
    assert item.meta["question_date_raw"] == "2023/05/01 (Mon) 20:00"


def test_a_repeated_session_id_keeps_message_ids_unique(items):
    item = by_id(items, "tr_001")
    ids = [m.id for s in item.haystack for m in s.messages]
    assert len(ids) == len(set(ids))
    assert item.meta["repeated_sessions"] == ["s004"]
    first, later = (s for s in item.haystack if s.meta["lme_session_id"] == "sharegpt_yywfIrx_0")
    assert (first.id, later.id) == ("s002", "s004") and later.started_at > first.started_at


def test_session_and_message_ids_are_opaque_and_say_nothing_of_the_answer(items):
    for item in items:
        ids = [s.id for s in item.haystack]
        assert ids == [f"s{n:03d}" for n in range(1, len(ids) + 1)]
        for source in item.haystack:
            assert [m.id for m in source.messages] == [f"{source.id}:{k}" for k in range(len(source.messages))]
        shown = json.dumps([[s.id, [m.id for m in s.messages]] for s in item.haystack])
        assert not any(leak in shown for leak in ("answer_", "sharegpt_", "ultrachat_"))
        assert item.id not in shown


def test_evidence_and_answer_sessions_are_mapped_to_the_new_ids(items):
    for item in items:
        by_new = {s.id: s.meta["lme_session_id"] for s in item.haystack}
        assert item.meta["answer_session_ids"] == [n for n, raw in by_new.items() if raw.startswith("answer_")]
        assert sorted(item.meta["lme_answer_session_ids"]) == sorted(r for r in by_new.values() if r.startswith("answer_"))
        for mid in item.evidence_message_ids:
            assert by_new[mid.split(":")[0]].startswith("answer_")
    assert by_id(items, "ms_001").meta["answer_session_ids"] == ["s001", "s003"]
    assert by_id(items, "ms_001").meta["unmarked_answer_sessions"] == []
    assert by_id(items, "ku_002_abs").meta["answer_session_ids"] == []


def record(qid, sessions):
    """A record in the file's shape; `sessions` is [(id, date, has_answer)]."""
    return {
        "question_id": qid, "question_type": "multi-session", "question": "q?", "answer": "a",
        "question_date": "2023/12/01 (Fri) 09:00", "answer_session_ids": [i for i, _, ans in sessions if ans],
        "haystack_session_ids": [i for i, _, _ in sessions], "haystack_dates": [d for _, d, _ in sessions],
        "haystack_sessions": [
            [{"role": "user", "content": f"hello from {i}", **({"has_answer": True} if ans else {})}] for i, _, ans in sessions
        ],
    }


def test_sessions_with_the_same_date_keep_the_file_order_and_get_ids_in_turn():
    same = "2023/05/20 (Sat) 02:21"
    rec = record("t1", [("sharegpt_b", same, False), ("answer_x", same, True), ("ultrachat_1", "2023/05/01 (Mon) 10:00", False)])
    (item,) = L.to_items([rec])
    assert [s.meta["lme_session_id"] for s in item.haystack] == ["ultrachat_1", "sharegpt_b", "answer_x"]
    assert [s.id for s in item.haystack] == ["s001", "s002", "s003"]
    assert item.evidence_message_ids == ["s003:0"] and item.meta["answer_session_ids"] == ["s003"]


def test_an_answer_session_with_no_marked_turn_is_listed_under_its_new_id():
    rec = record("t2", [("sharegpt_b", "2023/05/01 (Mon) 10:00", False), ("answer_y", "2023/05/02 (Tue) 10:00", True)])
    rec["haystack_sessions"][1][0].pop("has_answer")
    (item,) = L.to_items([rec])
    assert item.evidence_message_ids == [] and item.meta["unmarked_answer_sessions"] == ["s002"]


def test_verify_rejects_unknown_and_changed_files(tmp_path):
    with pytest.raises(ValueError, match="no published checksum"):
        L.verify(FIXTURE)
    fake = tmp_path / L.ORACLE_FILE
    fake.write_text("[]")
    with pytest.raises(ValueError, match="not the published"):
        L.verify(fake)
    with pytest.raises(ValueError):
        L.load(fake)


# --- selection ---------------------------------------------------------------------------------

TYPES = ["knowledge-update", "temporal-reasoning", "multi-session", "single-session-user"]
SEL = {"types": TYPES, "per_type_dev": 3, "per_type_test": 2, "abstention_dev": 2, "abstention_test": 1}


def synthetic(n_per_type=12, n_abs_per_type=3) -> list[QAItem]:
    out = []
    for t in TYPES + ["single-session-assistant"]:
        for k in range(n_per_type):
            out.append(QAItem(f"{t}-{k}", "longmemeval_s", "q?", "a", t, []))
        for k in range(n_abs_per_type):
            out.append(QAItem(f"{t}-{k}_abs", "longmemeval_s", "q?", "a", t, [], abstention=True))
    return out


def test_select_is_stratified_and_disjoint():
    sel = L.select(synthetic(), SEL, seed=7)
    dev, test = sel["dev"], sel["test"]
    assert len(dev) == 3 * 4 + 2 and len(test) == 2 * 4 + 1
    assert not {i.id for i in dev} & {i.id for i in test}
    assert all(i.split == "dev" for i in dev) and all(i.split == "test" for i in test)
    plain = [i for i in dev if not i.abstention]
    assert {t: sum(i.question_type == t for i in plain) for t in TYPES} == {t: 3 for t in TYPES}
    assert sum(i.abstention for i in dev) == 2 and sum(i.abstention for i in test) == 1
    assert all(i.question_type in TYPES for i in dev + test)


def test_select_is_deterministic_and_ignores_input_order():
    items = synthetic()
    a = L.select(items, SEL, seed=7)
    shuffled = list(items)
    random.Random(1).shuffle(shuffled)
    b = L.select(shuffled, SEL, seed=7)
    assert [i.id for i in a["dev"]] == [i.id for i in b["dev"]]
    assert [i.id for i in a["test"]] == [i.id for i in b["test"]]
    c = L.select(items, SEL, seed=8)
    assert [i.id for i in a["dev"]] != [i.id for i in c["dev"]]


def test_select_refuses_when_there_are_too_few_items():
    with pytest.raises(ValueError, match="needed"):
        L.select(synthetic(n_per_type=4), SEL, seed=7)
    with pytest.raises(ValueError, match="abstention"):
        L.select(synthetic(n_abs_per_type=0), SEL, seed=7)


def test_manifest_holds_ids_only_and_round_trips(tmp_path):
    items = synthetic()
    sel = L.select(items, SEL, seed=7)
    path = tmp_path / "out" / "manifest.json"
    L.write_manifest(sel, path, meta={"seed": 7})
    data = json.loads(path.read_text())
    assert set(data) == {"datasets", "meta", "dev", "test"}
    assert data["dev"] == [i.id for i in sel["dev"]]
    assert "q?" not in path.read_text()
    again = L.load_selection(path, items)
    assert [i.id for i in again["test"]] == [i.id for i in sel["test"]]
    assert all(i.split == "test" for i in again["test"])
    with pytest.raises(KeyError):
        L.load_selection(path, items[:3])


TABLE = {**SEL, "per_type_test": {"knowledge-update": 4, "temporal-reasoning": 3, "multi-session": 2, "single-session-user": 1}}


def test_per_type_test_may_be_a_table_per_type():
    sel = L.select(synthetic(), TABLE, seed=7)
    dev, test = sel["dev"], sel["test"]
    plain = [i for i in test if not i.abstention]
    assert {t: sum(i.question_type == t for i in plain) for t in TYPES} == TABLE["per_type_test"]
    assert len(test) == 4 + 3 + 2 + 1 + 1 and len(dev) == 14
    assert not {i.id for i in dev} & {i.id for i in test}
    again = L.select(synthetic(), TABLE, seed=7)
    assert [i.id for i in again["test"]] == [i.id for i in test]


def test_a_table_agrees_with_the_number_it_repeats():
    same = {**SEL, "per_type_test": {t: 2 for t in TYPES}}
    a, b = L.select(synthetic(), SEL, seed=7), L.select(synthetic(), same, seed=7)
    assert [i.id for i in a["test"]] == [i.id for i in b["test"]]


def test_a_table_must_name_every_type_and_each_type_needs_its_own_count():
    short = {**SEL, "per_type_test": {"knowledge-update": 2}}
    with pytest.raises(ValueError, match="per_type_test"):
        L.select(synthetic(), short, seed=7)
    big = {**SEL, "per_type_test": {**TABLE["per_type_test"], "single-session-user": 10}}
    with pytest.raises(ValueError, match="single-session-user: 12 items, 13 needed"):
        L.select(synthetic(), big, seed=7)


B0 = {**TABLE, "b0_test_per_type": 2}


def test_b0_subset_is_every_abstention_item_and_the_first_few_of_each_type():
    test = L.select(synthetic(), B0, seed=7)["test"]
    subset = L.b0_subset(test, B0)
    plain = [i for i in subset if not i.abstention]
    assert sum(i.abstention for i in subset) == sum(i.abstention for i in test) == 1
    assert {t: sum(i.question_type == t for i in plain) for t in TYPES} == {
        "knowledge-update": 2, "temporal-reasoning": 2, "multi-session": 2, "single-session-user": 1,
    }
    for t in TYPES:  # the first of each type in selection order
        mine = [i.id for i in test if i.question_type == t and not i.abstention]
        assert [i.id for i in plain if i.question_type == t] == mine[:2]
    assert [i.id for i in subset] == [i.id for i in test if i in subset]  # selection order
    assert all(i.split == "test" for i in subset)


def test_b0_subset_is_deterministic_and_leaves_out_other_splits():
    sel = L.select(synthetic(), B0, seed=7)
    assert [i.id for i in L.b0_subset(sel["test"], B0)] == [i.id for i in L.b0_subset(sel["test"], B0)]
    assert L.b0_subset(sel["dev"], B0) == [] and L.b0_subset([], B0) == []
    mixed = L.b0_subset(sel["dev"] + sel["test"], B0)
    assert [i.id for i in mixed] == [i.id for i in L.b0_subset(sel["test"], B0)]
    assert len(L.b0_subset(sel["test"], {**B0, "b0_test_per_type": 0})) == 1  # abstention only


def test_default_config_selection_fits_the_published_file_counts():
    cfg = config.load()["eval"]["longmemeval"]
    # LongMemEval_S has 72 knowledge-update, 127 temporal, 121 multi-session and 64
    # single-session-user questions that are not abstention, and 6/6/12/6 that are.
    available = {"knowledge-update": 72, "temporal-reasoning": 127, "multi-session": 121, "single-session-user": 64}
    assert set(cfg["per_type_test"]) == set(cfg["types"]) == set(available)
    for t, n in available.items():
        assert cfg["per_type_dev"] + cfg["per_type_test"][t] <= n
    assert cfg["abstention_dev"] + cfg["abstention_test"] <= 30
    assert cfg["per_type_test"]["knowledge-update"] == 62 and cfg["per_type_test"]["temporal-reasoning"] == 60
    assert cfg["b0_test_per_type"] == 10


# --- the real file ---------------------------------------------------------------------------


REAL = L.default_path()


@pytest.mark.skipif(not REAL.exists(), reason="LongMemEval_S is not downloaded")
def test_real_file_counts_per_type():
    from collections import Counter

    items = L.to_items(L.load(REAL))
    assert len(items) == 500
    counts = Counter(i.question_type for i in items)
    assert counts == {
        "temporal-reasoning": 133,
        "multi-session": 133,
        "knowledge-update": 78,
        "single-session-user": 70,
        "single-session-assistant": 56,
        "single-session-preference": 30,
    }
    assert sum(i.abstention for i in items) == 30
    assert all(i.evidence_message_ids for i in items if not i.abstention and not i.meta["unmarked_answer_sessions"])
    for i in items[:50]:  # message ids are unique within an item
        mine = [m.id for s in i.haystack for m in s.messages]
        assert len(mine) == len(set(mine))

    cfg = config.load()["eval"]
    sel = L.select(items, cfg["longmemeval"], cfg["seed"])
    lme_cfg = cfg["longmemeval"]
    assert len(sel["dev"]) == 4 * lme_cfg["per_type_dev"] + lme_cfg["abstention_dev"] == 50
    assert len(sel["test"]) == sum(lme_cfg["per_type_test"].values()) + lme_cfg["abstention_test"] == 202
    assert not {i.id for i in sel["dev"]} & {i.id for i in sel["test"]}
    again = L.select(items, lme_cfg, cfg["seed"])
    assert [i.id for i in again["test"]] == [i.id for i in sel["test"]]
    subset = L.b0_subset(sel["test"], lme_cfg)
    assert len(subset) == lme_cfg["abstention_test"] + 4 * lme_cfg["b0_test_per_type"] == 60
    assert sum(i.abstention for i in subset) == 20


@pytest.mark.skipif(not REAL.exists(), reason="LongMemEval_S is not downloaded")
def test_real_file_session_ids_are_opaque_and_evidence_follows_the_mapping():
    import re

    items = L.to_items(L.load(REAL))
    for item in items:
        assert [s.id for s in item.haystack] == [f"s{n:03d}" for n in range(1, len(item.haystack) + 1)]
        by_new = {s.id: s.meta["lme_session_id"] for s in item.haystack}
        for mid in item.evidence_message_ids:
            assert re.fullmatch(r"s\d{3}:\d+", mid) and by_new[mid.split(":")[0]].startswith("answer_")
        assert all(by_new[s].startswith("answer_") for s in item.meta["answer_session_ids"])
