"""LongMemEval_S as QAItems, and the fixed subsets we report on (DESIGN §8 "Published sets";
note 09, Implications §1 and §7, Stage 3; SYNTHESIS §9).

LongMemEval (Wu et al., ICLR 2025; MIT licence): 500 questions, each over about 115K
tokens of chat history. We use the cleaned release. What the files hold, checked on
2026-10-28 against the hashes below:
- `answer` is a number in 32 records; it becomes a string.
- Sessions are not in date order in 211 records; the haystack is sorted by date.
- Session ids carry the answer: evidence sessions are named "answer_<id>", filler sessions
  "sharegpt_*" or "ultrachat_*". A system must never see them, so every session gets an
  opaque id by date order within the item ("s001", "s002", ...; ties keep the file's
  order) and each turn "s001:0", "s001:1", ...; the original id stays in
  Source.meta["lme_session_id"]. Nothing else that could carry the answer is rendered
  (no `has_answer`, no question id).
- 13 records repeat a filler session under the same id, with another date; opaque ids
  keep them apart, and the later copies are listed in meta["repeated_sessions"].
- `has_answer` appears only on the turns of evidence sessions.
- 32 records that are not abstention questions list answer sessions with no turn marked
  `has_answer`; they are kept in meta["unmarked_answer_sessions"] (opaque ids).
- 76 records have sessions dated up to 24 hours after the question (1,475 sessions, 75
  of them evidence sessions); they are kept, as the benchmark has them.
- 1,942 sessions open with an assistant turn.
Dates become ISO 8601 (no offset is known); the raw strings stay in meta.
"""

from __future__ import annotations

import hashlib
import json
import random
from collections.abc import Mapping
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from northstar_agent_memory.eval.types import QAItem
from northstar_agent_memory.paths import bench_root
from northstar_agent_memory.transcript import Message, Source

S_FILE = "longmemeval_s_cleaned.json"
ORACLE_FILE = "longmemeval_oracle.json"
SHA256 = {
    S_FILE: "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442",
    ORACLE_FILE: "821a2034d219ab45846873dd14c14f12cfe7776e73527a483f9dac095d38620c",
}
DATE_FORMAT = "%Y/%m/%d (%a) %H:%M"  # e.g. "2023/05/20 (Sat) 02:21"
SPEAKERS = {"user": "user", "assistant": "assistant"}  # the benchmark's role map


def default_path(name: str = S_FILE) -> Path:
    return bench_root() / "longmemeval" / name


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(path: Path) -> None:
    """Raise ValueError unless `path` is one of the published files, byte for byte."""
    path = Path(path)
    expected = SHA256.get(path.name)
    if expected is None:
        raise ValueError(f"no published checksum for {path.name!r}")
    actual = sha256_of(path)
    if actual != expected:
        raise ValueError(f"{path.name}: sha256 {actual} is not the published {expected}")


def load(path: Path) -> list[dict]:
    """The raw records. A file with a published name is verified first."""
    path = Path(path)
    if path.name in SHA256:
        verify(path)
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def parse_date(raw: str) -> datetime:
    return datetime.strptime(raw, DATE_FORMAT)


def to_items(records: list[dict], dataset: str = "longmemeval_s") -> list[QAItem]:
    return [_to_item(record, dataset) for record in records]


def _to_item(rec: dict, dataset: str) -> QAItem:
    triples = list(zip(rec["haystack_session_ids"], rec["haystack_dates"], rec["haystack_sessions"], strict=True))
    triples.sort(key=lambda t: parse_date(t[1]))  # stable: ties keep the file's order
    question_at = parse_date(rec["question_date"])
    answer_raw = list(rec["answer_session_ids"])
    answer_set = set(answer_raw)

    haystack: list[Source] = []
    evidence: list[str] = []
    marked: set[str] = set()
    answer_sids: list[str] = []
    repeated: list[str] = []
    seen_raw: set[str] = set()
    after_question = 0
    for n, (raw_id, raw_date, turns) in enumerate(triples, start=1):
        sid = f"s{n:03d}"  # opaque: the original id says whether the session holds the answer
        if raw_id in seen_raw:
            repeated.append(sid)
        seen_raw.add(raw_id)
        if raw_id in answer_set:
            answer_sids.append(sid)
        when = parse_date(raw_date)
        if when > question_at:
            after_question += 1
        iso = when.isoformat()
        messages = []
        for k, turn in enumerate(turns):
            speaker = SPEAKERS.get(turn["role"])
            if speaker is None:
                raise ValueError(f"{rec['question_id']}: unknown role {turn['role']!r}")
            mid = f"{sid}:{k}"
            messages.append(
                Message(
                    id=mid,
                    source_id=sid,
                    ordinal=k,
                    speaker=speaker,
                    text=turn["content"],
                    occurred_at=iso,
                    origin="typed" if speaker == "user" else "assistant_output",
                )
            )
            if turn.get("has_answer"):
                evidence.append(mid)
                marked.add(sid)
        meta = {"date_raw": raw_date, "lme_session_id": raw_id}
        haystack.append(Source(id=sid, kind="chat", app="longmemeval", started_at=iso, messages=messages, meta=meta))

    return QAItem(
        id=rec["question_id"],
        dataset=dataset,
        question=rec["question"],
        gold_answer=str(rec["answer"]),
        question_type=rec["question_type"],
        haystack=haystack,
        evidence_message_ids=evidence,
        question_date=question_at.isoformat(),
        abstention=rec["question_id"].endswith("_abs"),
        meta={
            "question_date_raw": rec["question_date"],
            "answer_session_ids": answer_sids,
            "lme_answer_session_ids": answer_raw,
            "unmarked_answer_sessions": [s for s in answer_sids if s not in marked],
            "sessions_after_question": after_question,
            "repeated_sessions": repeated,
        },
    )


def select(items: list[QAItem], config: dict, seed: int) -> dict[str, list[QAItem]]:
    """Fixed dev and test subsets, stratified by question type ([eval.longmemeval]).

    Each split takes `per_type_*` items of every type in `types` (a number for every
    type, or a table with one number per type), and `abstention_*` abstention items drawn
    in turn from those types. The draw depends only on the items' ids and `seed`, never
    on their order, and no item is in both splits. The test split lists the types in
    `types` order, each in draw order, then the abstention items.
    """
    if len({i.id for i in items}) != len(items):
        raise ValueError("item ids are not unique")
    types = list(config["types"])
    dev: list[QAItem] = []
    test: list[QAItem] = []
    for qtype in types:
        n_dev = _per_type(config["per_type_dev"], qtype, "per_type_dev")
        n_test = _per_type(config["per_type_test"], qtype, "per_type_test")
        pool = _shuffled([i for i in items if i.question_type == qtype and not i.abstention], f"{seed}:{qtype}")
        if len(pool) < n_dev + n_test:
            raise ValueError(f"{qtype}: {len(pool)} items, {n_dev + n_test} needed")
        dev += pool[:n_dev]
        test += pool[n_dev : n_dev + n_test]

    pools = [_shuffled([i for i in items if i.question_type == t and i.abstention], f"{seed}:abs:{t}") for t in types]
    rounds = max((len(p) for p in pools), default=0)
    interleaved = [p[k] for k in range(rounds) for p in pools if k < len(p)]
    a_dev, a_test = config["abstention_dev"], config["abstention_test"]
    if len(interleaved) < a_dev + a_test:
        raise ValueError(f"abstention: {len(interleaved)} items, {a_dev + a_test} needed")
    dev += interleaved[:a_dev]
    test += interleaved[a_dev : a_dev + a_test]
    return {"dev": [replace(i, split="dev") for i in dev], "test": [replace(i, split="test") for i in test]}


def _per_type(value: int | Mapping[str, int], qtype: str, name: str) -> int:
    if isinstance(value, Mapping):
        if qtype not in value:
            raise ValueError(f"{name}: no count for {qtype!r}")
        return int(value[qtype])
    return int(value)


def b0_subset(items: list[QAItem], config: dict) -> list[QAItem]:
    """The test items B0 runs on: all abstention items and the first `b0_test_per_type` of each type.

    `items` are the test split in selection order (select()["test"]); an item of another
    split is ignored. B0 sends the whole history, so it is run on a reference subset to
    bound its cost (DESIGN §8). The result keeps the input order and depends on nothing else.
    """
    n = int(config["b0_test_per_type"])
    taken: dict[str, int] = {}
    out: list[QAItem] = []
    for item in items:
        if item.split != "test":
            continue
        if item.abstention:
            out.append(item)
        elif taken.get(item.question_type, 0) < n and item.question_type in config["types"]:
            taken[item.question_type] = taken.get(item.question_type, 0) + 1
            out.append(item)
    return out


def _shuffled(items: list[QAItem], seed: str) -> list[QAItem]:
    out = sorted(items, key=lambda i: i.id)
    random.Random(seed).shuffle(out)  # a str seed is hashed with SHA-512: stable across runs
    return out


def write_manifest(selection: dict[str, list[QAItem]], path: Path, meta: dict | None = None) -> None:
    """Record a selection by item ids only, so the same subsets are used on every run."""
    datasets = sorted({i.dataset for split in selection.values() for i in split})
    data = {"datasets": datasets, "meta": meta or {}}
    data.update({split: [i.id for i in split_items] for split, split_items in selection.items()})
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def load_selection(path: Path, items: list[QAItem]) -> dict[str, list[QAItem]]:
    """The selection a manifest names, in its order, with each item's split set."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    by_id = {i.id: i for i in items}
    out: dict[str, list[QAItem]] = {}
    for split in ("dev", "test"):
        ids = data.get(split, [])
        missing = [i for i in ids if i not in by_id]
        if missing:
            raise KeyError(f"{split}: {len(missing)} ids not in the items, e.g. {missing[:3]}")
        out[split] = [replace(by_id[i], split=split) for i in ids]
    return out
