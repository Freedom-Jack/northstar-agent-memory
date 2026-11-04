"""Records the measurement harness passes between its parts (DESIGN §8; note 09).

Scoring follows HaluMem: each memory operation (extraction, update, answering) is
scored on its own, and every outcome is correct, hallucinated or omitted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from northstar_agent_memory.models.port import Usage
from northstar_agent_memory.transcript import Source

Outcome = Literal["correct", "hallucinated", "omitted"]
Split = Literal["dev", "test"]


@dataclass(slots=True)
class QAItem:
    """One question asked of a memory system, with its gold answer and history."""

    id: str
    dataset: str  # "longmemeval_s", "scenario:<persona>", "own:<set>"
    question: str
    gold_answer: str
    question_type: str  # LongMemEval's types, or a scenario probe kind
    haystack: list[Source]  # the history the system may use, oldest first
    evidence_message_ids: list[str] = field(default_factory=list)  # gold evidence
    question_date: str | None = None
    abstention: bool = False  # the right answer is that the history does not say
    split: Split = "dev"
    meta: dict = field(default_factory=dict)


@dataclass(slots=True)
class Prediction:
    """What one system answered for one QAItem, with what it cost."""

    item_id: str
    system: str  # "B0" | "B1" | "B2" | "B3" | "northstar@<version>"
    answer: str
    cited_message_ids: list[str] = field(default_factory=list)
    context_tokens: int = 0  # tokens of history or memory given to the answerer
    usage: Usage = field(default_factory=Usage)
    cost_usd: float = 0.0
    latency_s: float = 0.0
    calls: int = 0
    meta: dict = field(default_factory=dict)


@dataclass(slots=True)
class Judgement:
    """The judged outcome of one Prediction."""

    item_id: str
    system: str
    outcome: Outcome  # correct; hallucinated (a wrong answer); omitted (no answer when one exists)
    abstained: bool  # the system said the history does not tell
    judge_family: str  # "code" when scored without a model
    judge_model: str
    rationale: str = ""


@dataclass(slots=True)
class GoldMemory:
    """A memory point in a scripted scenario's hidden record (note 09 §3)."""

    key: str
    line: str  # the canonical statement
    kind: str  # MEMORY-ARCHITECTURE §2.4 kinds: decision, ruled_out, result, ...
    holder: Literal["user", "other_person", "ai_unadopted", "hypothetical"]
    evidence_message_ids: list[str]
    must_record: bool  # False for distractors that must NOT become the user's memory
    scope: str = "personal"  # "project:<id>" | "personal"
    adopted_from: str | None = None  # the AI family, when the user adopted an AI's idea
    meta: dict = field(default_factory=dict)


@dataclass(slots=True)
class GoldUpdate:
    """A scripted change: `new_key` supersedes `old_key` at a message."""

    key: str
    old_key: str
    new_key: str
    at_message_id: str
    reason: str  # "user_later_statement" | "ai_self_correction" | "implicit" | ...


@dataclass(slots=True)
class SystemMemory:
    """One memory as the system under test recorded it."""

    id: str
    line: str
    status: str  # "active" | "superseded" | "retracted" | ...
    evidence_message_ids: list[str] = field(default_factory=list)
    quotes: list[str] = field(default_factory=list)
    origin: str = "yours"  # "yours" | "adopted from <agent>"
    scope: str = "personal"
    supersedes: str | None = None  # the id of the memory this one replaced


@dataclass(slots=True)
class OpScore:
    """HaluMem-style counts for one operation."""

    operation: Literal["extraction", "update", "qa"]
    correct: int = 0
    hallucinated: int = 0
    omitted: int = 0

    @property
    def total(self) -> int:
        return self.correct + self.hallucinated + self.omitted

    def rate(self, outcome: Outcome) -> float:
        return getattr(self, outcome) / self.total if self.total else 0.0
