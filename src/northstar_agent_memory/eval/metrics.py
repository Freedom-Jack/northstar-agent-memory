"""Scoring for the measurement harness: pure code, no model calls (DESIGN §8; note 09).

- Each memory operation is scored on its own, HaluMem-style: extraction, update and
  answering, each as correct, hallucinated or omitted (note 09, "Ideas worth stealing").
- Citations are scored ALCE-style, as precision and recall (Gao et al. 2023).
- A quote must match its message exactly, after normalizing spaces and Unicode (I2).
- Each score comes with its cost, and comparisons with a paired bootstrap interval.

Judgments that need a model (is this the same memory? does this text support that
claim?) come in as callables, so nothing here calls one.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Callable, Iterable, Mapping, Sequence

import numpy as np

from northstar_agent_memory.eval.types import (
    GoldMemory,
    GoldUpdate,
    Judgement,
    OpScore,
    Outcome,
    Prediction,
    QAItem,
    SystemMemory,
)
from northstar_agent_memory.models.port import Usage
from northstar_agent_memory.transcript import Message

Same = Callable[[GoldMemory, SystemMemory], bool]
Entails = Callable[[str, str], bool]  # (premise, hypothesis)

# Statuses that mean a memory was recorded; a quarantined proposal never applied.
RECORDED = ("active", "superseded")


def _ratio(num: float, den: float) -> float | None:
    return num / den if den else None


def _add(score: OpScore, outcome: Outcome) -> None:
    setattr(score, outcome, getattr(score, outcome) + 1)


# --- Answering -------------------------------------------------------------------------


@dataclass(slots=True)
class QAScores:
    """One system's answering scores (DESIGN §8, Memory; LongMemEval's question types)."""

    system: str
    overall: OpScore
    by_type: dict[str, OpScore]  # by question_type as given; abstention items stay in theirs
    answerable: OpScore  # items whose answer is in the history
    abstention: OpScore  # items whose right answer is that the history does not say
    missing: list[str] = field(default_factory=list)  # items with no judgement: omitted

    @property
    def answer_accuracy(self) -> float | None:
        return _ratio(self.answerable.correct, self.answerable.total)

    @property
    def abstention_accuracy(self) -> float | None:
        """Correct abstentions over abstention items."""
        return _ratio(self.abstention.correct, self.abstention.total)


def qa_scores(judgements: Iterable[Judgement], items: Iterable[QAItem]) -> dict[str, QAScores]:
    """Scores per system over exactly `items`.

    An item a system has no judgement for counts as omitted, so failing to answer
    never raises a score. Judgements of other items are ignored: to score one split or
    one type, pass only its items.
    """
    items = list(items)
    wanted = {item.id for item in items}
    if len(wanted) != len(items):
        raise ValueError("duplicate item ids")
    judged: dict[str, dict[str, Judgement]] = defaultdict(dict)
    for j in judgements:
        if j.item_id not in wanted:
            continue
        if j.item_id in judged[j.system]:
            raise ValueError(f"{j.system} has two judgements of {j.item_id}")
        judged[j.system][j.item_id] = j
    scores: dict[str, QAScores] = {}
    for system, by_item in judged.items():
        s = QAScores(system, OpScore("qa"), {}, OpScore("qa"), OpScore("qa"))
        for item in items:
            j = by_item.get(item.id)
            if j is None:
                s.missing.append(item.id)
            outcome = j.outcome if j else "omitted"
            _add(s.overall, outcome)
            _add(s.by_type.setdefault(item.question_type, OpScore("qa")), outcome)
            _add(s.abstention if item.abstention else s.answerable, outcome)
        scores[system] = s
    return scores


# --- Extraction ------------------------------------------------------------------------


def _by_key(gold: Iterable[GoldMemory]) -> dict[str, GoldMemory]:
    by_key: dict[str, GoldMemory] = {}
    for g in gold:
        if g.key in by_key:
            raise ValueError(f"two gold memories have the key {g.key}")
        by_key[g.key] = g
    return by_key


def _match_table(
    gold: Iterable[GoldMemory], system: Sequence[SystemMemory], same: Same
) -> dict[str, list[SystemMemory]]:
    """The system memories that match each gold memory; `same` runs once per pair."""
    return {g.key: [m for m in system if same(g, m)] for g in gold}


@dataclass(slots=True)
class ExtractionScore:
    """Extraction against a scripted scenario's hidden record (note 09 §3, §4).

    `score` counts gold memories (correct, omitted) and recorded system memories
    (hallucinated), so its total mixes the two. DESIGN §8's bars read `recall` and
    `hallucination_rate`.
    """

    score: OpScore
    matched: dict[str, list[str]]  # must-record gold key -> recorded memories that match it
    omitted_keys: list[str]
    hallucinated_ids: list[str]  # recorded memories that match no must-record gold memory
    distractors_recorded: list[str]  # distractor keys that some recorded memory matches
    n_distractors: int
    n_recorded: int
    duplicates: int  # recorded memories beyond the first that match the same gold memory
    attribution_errors: list[tuple[str, str]]  # (gold key, memory id): yours vs adopted wrong

    @property
    def recall(self) -> float | None:
        return _ratio(self.score.correct, self.score.correct + self.score.omitted)

    @property
    def hallucination_rate(self) -> float | None:
        return _ratio(self.score.hallucinated, self.n_recorded)

    @property
    def false_memory_resistance(self) -> float | None:
        """1 - distractors recorded / distractors (HaluMem)."""
        if not self.n_distractors:
            return None
        return 1 - len(self.distractors_recorded) / self.n_distractors


def extraction_scores(
    gold: Iterable[GoldMemory], system: Iterable[SystemMemory], same: Same
) -> ExtractionScore:
    """Score what the system recorded against the scenario's complete gold record.

    - correct: a must-record gold memory matched by an active or superseded memory;
    - omitted: a must-record gold memory nothing recorded matches;
    - hallucinated: a recorded memory that matches no must-record gold memory, whether
      it matches a distractor (someone else's view, a hypothetical, an AI idea never
      adopted) or nothing at all.

    `same` runs once for each pair of gold and recorded memory; when it calls a model,
    give it a code prefilter.
    """
    by_key = _by_key(gold)
    recorded = [m for m in system if m.status in RECORDED]
    if len({m.id for m in recorded}) != len(recorded):
        raise ValueError("duplicate system memory ids")
    table = _match_table(by_key.values(), recorded, same)
    must = [g for g in by_key.values() if g.must_record]
    distractors = [g for g in by_key.values() if not g.must_record]

    matched = {g.key: [m.id for m in table[g.key]] for g in must if table[g.key]}
    omitted = [g.key for g in must if not table[g.key]]
    good = {i for ids in matched.values() for i in ids}
    hallucinated = [m.id for m in recorded if m.id not in good]
    attribution_errors = [
        (g.key, m.id)
        for g in must
        for m in table[g.key]
        if (g.adopted_from is not None) != m.origin.startswith("adopted")
    ]
    return ExtractionScore(
        score=OpScore(
            "extraction",
            correct=len(matched),
            hallucinated=len(hallucinated),
            omitted=len(omitted),
        ),
        matched=matched,
        omitted_keys=omitted,
        hallucinated_ids=hallucinated,
        distractors_recorded=[g.key for g in distractors if table[g.key]],
        n_distractors=len(distractors),
        n_recorded=len(recorded),
        duplicates=sum(len(ids) - 1 for ids in matched.values()),
        attribution_errors=attribution_errors,
    )


# --- Updates ---------------------------------------------------------------------------


@dataclass(slots=True)
class UpdateScore:
    """Scripted updates against the system's memory (note 09, finding 3 and §4).

    Each update ends as one of:
    - correct: the new memory is active and the old one is not;
    - stale: both are active, so an outdated value is still presented as current;
      counted as omitted in `score` and reported as the stale-assertion rate;
    - omitted: the new memory is missing;
    - wrong_value: the old memory was replaced by one that does not match the new;
      counted as hallucinated.
    Collateral damage also counts as hallucinated: a recorded gold memory that no
    update touched, superseded or retracted all the same (note 09, finding 4).
    """

    score: OpScore
    outcomes: dict[str, str]  # update key -> correct | stale | omitted | wrong_value
    collateral: list[str]  # gold keys
    n_untouched: int  # recorded gold memories that no update touched

    def _share(self, *names: str) -> float | None:
        return _ratio(sum(o in names for o in self.outcomes.values()), len(self.outcomes))

    @property
    def correct_rate(self) -> float | None:
        return self._share("correct")

    @property
    def omitted_rate(self) -> float | None:
        """Missed updates, stale ones included."""
        return self._share("omitted", "stale")

    @property
    def stale_assertion_rate(self) -> float | None:
        return self._share("stale")

    @property
    def collateral_damage_rate(self) -> float | None:
        return _ratio(len(self.collateral), self.n_untouched)


def update_scores(
    updates: Sequence[GoldUpdate],
    gold: Iterable[GoldMemory],
    system: Sequence[SystemMemory],
    same: Same,
) -> UpdateScore:
    """Score the updates that took effect before the snapshot `system` was taken.

    Pass `updates` in time order. When a later update supersedes an earlier one's new
    memory (A to B, then B to C), the earlier update needs its new memory recorded,
    not active. An A-to-B-to-A reversal ends where it began, so also score a snapshot
    taken between the two. `same` runs once for each pair of gold and system memory.
    """
    by_key = _by_key(gold)
    for u in updates:
        for key in (u.old_key, u.new_key):
            if key not in by_key:
                raise KeyError(f"update {u.key} names no gold memory {key!r}")
    if len({u.key for u in updates}) != len(updates):
        raise ValueError("duplicate update keys")
    touched = {k for u in updates for k in (u.old_key, u.new_key)}
    wanted = [g for g in by_key.values() if g.key in touched or g.must_record]
    table = _match_table(wanted, system, same)

    expected: dict[str, bool] = {}  # whether each touched key should end active
    for u in updates:
        expected[u.old_key] = False
        expected[u.new_key] = True

    outcomes: dict[str, str] = {}
    for u in updates:
        new, old = table[u.new_key], table[u.old_key]
        if expected[u.new_key]:
            new_ok = any(m.status == "active" for m in new)
        else:  # a later update superseded it
            new_ok = any(m.status in RECORDED for m in new)
        old_active = not expected[u.old_key] and any(m.status == "active" for m in old)
        if new_ok:
            outcomes[u.key] = "stale" if old_active else "correct"
        elif old_active:
            outcomes[u.key] = "omitted"
        else:
            old_ids = {m.id for m in old}
            replaced = any(m.status == "active" and m.supersedes in old_ids for m in system)
            outcomes[u.key] = "wrong_value" if replaced else "omitted"

    collateral: list[str] = []
    n_untouched = 0
    for g in wanted:
        mems = table[g.key]
        if g.key in touched or not any(m.status in (*RECORDED, "retracted") for m in mems):
            continue
        n_untouched += 1
        if not any(m.status == "active" for m in mems):
            collateral.append(g.key)

    counts = Counter(outcomes.values())
    score = OpScore(
        "update",
        correct=counts["correct"],
        hallucinated=counts["wrong_value"] + len(collateral),
        omitted=counts["omitted"] + counts["stale"],
    )
    return UpdateScore(score, outcomes, collateral, n_untouched)


# --- Citations and quotes --------------------------------------------------------------


@dataclass(slots=True)
class Claim:
    """One claim (a memory line, or one statement of an answer) and what it cites."""

    text: str
    cited_message_ids: list[str]


@dataclass(slots=True)
class CitationScore:
    """ALCE citation recall and precision (Gao et al. 2023; DESIGN §8)."""

    n_claims: int
    supported: int  # claims that their cited texts, together, entail
    n_citations: int
    precise: int  # citations of supported claims that are not irrelevant
    unsupported: list[int]  # claim indexes
    irrelevant: list[tuple[int, str]]  # (claim index, message id)
    dangling: list[tuple[int, str]]  # citations of messages that do not exist (I1)

    @property
    def recall(self) -> float | None:
        return _ratio(self.supported, self.n_claims)

    @property
    def precision(self) -> float | None:
        if not self.n_claims:
            return None
        return self.precise / self.n_citations if self.n_citations else 0.0


def cited_text(message: Message) -> str:
    """A cited turn as the entailment check reads it: the speaker, from capture, first."""
    return f"{message.speaker}: {message.text}"


def citation_scores(
    claims: Sequence[Claim], messages_by_id: Mapping[str, Message], entails: Entails
) -> CitationScore:
    """Citation recall and precision over `claims`, checked against the raw turns.

    Following ALCE:
    - a claim is supported if the cited texts, joined, entail it; a claim with no
      citations is unsupported;
    - a citation of a supported claim is irrelevant if it alone does not entail the
      claim and the claim's other citations still do; every citation of an
      unsupported claim counts against precision.
    A citation of a message that does not exist leaves its claim unsupported and
    counts against precision (ALCE drops such citations; for us they break I1).
    Repeated citations of one message count once.
    """
    supported = n_citations = precise = 0
    unsupported: list[int] = []
    irrelevant: list[tuple[int, str]] = []
    dangling: list[tuple[int, str]] = []
    for index, claim in enumerate(claims):
        ids = list(dict.fromkeys(claim.cited_message_ids))
        n_citations += len(ids)
        missing = [i for i in ids if i not in messages_by_id]
        dangling.extend((index, i) for i in missing)
        if not ids or missing:
            unsupported.append(index)
            continue
        texts = {i: cited_text(messages_by_id[i]) for i in ids}
        if not entails("\n\n".join(texts.values()), claim.text):
            unsupported.append(index)
            continue
        supported += 1
        if len(ids) == 1:
            precise += 1
            continue
        for i in ids:
            if entails(texts[i], claim.text):
                precise += 1
            elif entails("\n\n".join(t for j, t in texts.items() if j != i), claim.text):
                irrelevant.append((index, i))
            else:
                precise += 1
    return CitationScore(
        len(claims), supported, n_citations, precise, unsupported, irrelevant, dangling
    )


_SPACE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """NFC, with every run of whitespace collapsed to one space (I2)."""
    return _SPACE.sub(" ", unicodedata.normalize("NFC", text)).strip()


def quote_exact(quote: str, text: str) -> bool:
    """Whether `quote` is an exact substring of `text`, after normalizing (I2).

    An empty quote carries no evidence, so it never matches.
    """
    q = normalize_text(quote)
    return bool(q) and q in normalize_text(text)


# --- Cost ------------------------------------------------------------------------------


@dataclass(slots=True)
class CostSummary:
    """What one system's answers cost (DESIGN §8: each score comes with its cost)."""

    system: str
    n: int
    mean_context_tokens: float
    total_cost_usd: float
    mean_cost_usd: float
    p50_latency_s: float
    p95_latency_s: float
    calls: int
    usage: Usage


def cost_summary(predictions: Iterable[Prediction]) -> dict[str, CostSummary]:
    groups: dict[str, list[Prediction]] = defaultdict(list)
    for p in predictions:
        groups[p.system].append(p)
    out: dict[str, CostSummary] = {}
    for system, preds in groups.items():
        latency = np.array([p.latency_s for p in preds], dtype=float)
        total = float(sum(p.cost_usd for p in preds))
        out[system] = CostSummary(
            system=system,
            n=len(preds),
            mean_context_tokens=float(np.mean([p.context_tokens for p in preds])),
            total_cost_usd=total,
            mean_cost_usd=total / len(preds),
            p50_latency_s=float(np.percentile(latency, 50)),
            p95_latency_s=float(np.percentile(latency, 95)),
            calls=sum(p.calls for p in preds),
            usage=sum((p.usage for p in preds), Usage()),
        )
    return out


# --- Intervals -------------------------------------------------------------------------


@dataclass(slots=True)
class Interval:
    """An estimate with its 95% interval."""

    estimate: float
    low: float
    high: float
    n: int


def bootstrap_ci(values: Sequence[float], n_resamples: int = 2000, *, seed: int) -> Interval:
    """The mean with a 95% percentile-bootstrap interval; one seed, one interval."""
    data = np.asarray(values, dtype=float)
    if data.size == 0:
        raise ValueError("no values to resample")
    rng = np.random.default_rng(seed)
    means = data[rng.integers(0, data.size, size=(n_resamples, data.size))].mean(axis=1)
    low, high = np.percentile(means, [2.5, 97.5])
    return Interval(float(data.mean()), float(low), float(high), int(data.size))


@dataclass(slots=True)
class PairedDifference:
    """System A's accuracy minus system B's, over the items both answered."""

    system_a: str
    system_b: str
    n: int
    accuracy_a: float
    accuracy_b: float
    difference: Interval  # mean of (a correct) - (b correct) per item


def _correct_by_item(judgements: Iterable[Judgement], system: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for j in judgements:
        if j.system != system:
            continue
        if j.item_id in out:
            raise ValueError(f"{system} has two judgements of {j.item_id}")
        out[j.item_id] = 1.0 if j.outcome == "correct" else 0.0
    return out


def paired_difference(
    judgements: Iterable[Judgement],
    system_a: str,
    system_b: str,
    seed: int,
    n_resamples: int = 2000,
) -> PairedDifference:
    """The accuracy difference with a paired bootstrap interval (items resampled)."""
    judgements = list(judgements)
    a = _correct_by_item(judgements, system_a)
    b = _correct_by_item(judgements, system_b)
    common = sorted(a.keys() & b.keys())
    if not common:
        raise ValueError(f"{system_a} and {system_b} have no judged item in common")
    xa = np.array([a[i] for i in common])
    xb = np.array([b[i] for i in common])
    return PairedDifference(
        system_a,
        system_b,
        len(common),
        float(xa.mean()),
        float(xb.mean()),
        bootstrap_ci(xa - xb, n_resamples, seed=seed),
    )


def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """The Wilson score interval for k of n (95% by default)."""
    if n <= 0:
        raise ValueError("n must be positive")
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)
