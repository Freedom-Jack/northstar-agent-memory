"""Baselines B0-B4: the systems Northstar must beat, without Northstar (DESIGN §8 "Baselines
we run ourselves"; note 09, Implications §2; SYNTHESIS §9 item 3).

Every baseline answers a QAItem through the ModelPort with one fixed answering prompt, the
same model and the same max_tokens, so that only the context differs:
- B0 FullHistory: the whole history, oldest sessions dropped if it passes a maximum context.
- B1 KeywordSearch: BM25 over rounds (a user turn and the assistant turn after it, the
  retrieval unit LongMemEval found best) within the token budget. Vector search is a hook.
- B2 GrepAgent: the model searches and reads the history itself in a JSON-action loop,
  with no vendor tool calling, so the same loop runs on every family.
- B3 Oracle: only the rounds that hold the gold evidence; an upper bound on retrieval.
- B4 ObservationLog: an append-only dated log of observations, written session by session
  by a small model, the cheapest serious competitor.
- "none" ClosedBook: the same answerer with no history at all, to find the questions that
  need memory (DESIGN §8 "Questions that need memory").
Context is counted with the offline estimate in tokens.py; exact counts are in Usage.

What a system is shown carries nothing of the answer: the sessions come with opaque ids
(longmemeval.py), no baseline prints the item's id or its evidence, and only B3 reads the
evidence ids to choose what to show. Every Prediction lists what it put in the context
(meta["context_message_ids"]) and what the model cited (cited_message_ids). Requests leave
`cache` off, since nothing is reused soon enough for a cache to pay.
"""

from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Collection, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

import numpy as np

from northstar_agent_memory import config as northstar_config
from northstar_agent_memory.eval.tokens import Fitted, cut_to_tokens, estimate_tokens, fit_to_budget
from northstar_agent_memory.eval.types import Prediction, QAItem
from northstar_agent_memory.models.budget import billed_result
from northstar_agent_memory.models.port import (
    Family,
    ModelError,
    ModelPort,
    ModelRequest,
    ModelResult,
    Role,
    Usage,
)
from northstar_agent_memory.transcript import Message, Source

DEFAULT_MAX_CONTEXT = 900_000  # estimated tokens B0 may send
MAX_QUERY_TERMS = 64
MAX_STEPS = 8  # B2's free steps; a forced answer step follows if it has not answered
SEARCH_HITS = 10
READ_TURNS = 20

# --- the one answering prompt ------------------------------------------------------------

RULES = (
    "You answer a question about a user from excerpts of their earlier conversations with an AI assistant. "
    "Use only the excerpts. Each excerpt is labelled with its date; work out relative times such as "
    "'last week' from the date of the excerpt they were said in, and take the current date from the question. "
    "When excerpts disagree because the user's situation changed, the latest one is the current state. "
    "Answer concisely, in a short phrase or sentence. "
    "If the excerpts do not contain the answer, answer \"I don't know\"; do not guess."
)
ANSWER_SYSTEM = (
    RULES + " Give the ids shown in square brackets of the excerpts your answer rests on in `cited`; "
    "cite only ids that appear in the excerpts, and use an empty list when none are shown or none apply."
)
CLOSED_BOOK_SYSTEM = (  # no history: it must be allowed to guess, or it would "fail" every question by refusing
    "You answer a question about a user. You have no access to their earlier conversations, so no excerpts are "
    "shown. Answer as well as you can from general knowledge and from the question itself; take the current date "
    "from the question. When you cannot tell, give your best guess rather than refusing. "
    "Answer concisely, in a short phrase or sentence. Set `cited` to an empty list."
)
ANSWER_SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "string"}, "cited": {"type": "array", "items": {"type": "string"}}},
    "required": ["answer", "cited"],
    "additionalProperties": False,
}
MAX_TOKENS = 1024


def format_date(iso: str | None) -> str:
    if not iso:
        return "undated"
    try:
        return datetime.fromisoformat(iso).strftime("%Y-%m-%d (%a) %H:%M")
    except ValueError:
        return iso


def question_message(item: QAItem, context: str) -> str:
    excerpts = context if context.strip() else "(no excerpts)"
    return f"Current date: {format_date(item.question_date)}\n\nExcerpts:\n\n{excerpts}\n\nQuestion: {item.question}"


def render_turns(source_id: str, date: str | None, messages: list[Message]) -> str:
    """One labelled excerpt: the session and date, then each turn with its id."""
    head = f"## Session {source_id}, {format_date(date)}"
    return "\n".join([head] + [f"[{m.id}] {m.speaker}: {m.text}" for m in messages])


# --- rounds, tally, answerer --------------------------------------------------------------


@dataclass(slots=True)
class Round:
    """A user turn and the assistant turn that follows it; the unit baselines retrieve."""

    source_id: str
    date: str | None
    messages: list[Message]

    @property
    def message_ids(self) -> list[str]:
        return [m.id for m in self.messages]

    @property
    def text(self) -> str:
        return "\n".join(f"{m.speaker}: {m.text}" for m in self.messages)

    def render(self) -> str:
        return render_turns(self.source_id, self.date, self.messages)


def rounds_of(source: Source) -> list[Round]:
    """A user turn takes the assistant turn after it; any other turn is a round alone."""
    out: list[Round] = []
    msgs = source.messages
    k = 0
    while k < len(msgs):
        group = [msgs[k]]
        if msgs[k].speaker == "user" and k + 1 < len(msgs) and msgs[k + 1].speaker == "assistant":
            group.append(msgs[k + 1])
        out.append(Round(source.id, source.started_at, group))
        k += len(group)
    return out


def all_rounds(item: QAItem) -> list[Round]:
    return [r for source in item.haystack for r in rounds_of(source)]


def render_rounds(rounds: list[Round]) -> str:
    return "\n\n".join(r.render() for r in rounds)


@dataclass(slots=True)
class Tally:
    """What one item cost, summed over its model calls."""

    usage: Usage = field(default_factory=Usage)
    cost_usd: float = 0.0
    latency_s: float = 0.0
    calls: int = 0
    model: str = ""

    def add(self, result: ModelResult) -> None:
        self.usage = self.usage + result.usage
        self.cost_usd += result.cost_usd
        self.latency_s += result.latency_s
        self.calls += 1
        self.model = result.served_model or result.model

    def merge(self, other: "Tally") -> None:
        self.usage = self.usage + other.usage
        self.cost_usd += other.cost_usd
        self.latency_s += other.latency_s
        self.calls += other.calls
        self.model = other.model or self.model


@contextmanager
def keeps_tally(*tallies: Tally) -> Iterator[None]:
    """When the body fails, put what was spent so far on the exception as `err.tally`.

    `run_baseline` writes it into the failed item's Prediction, so that a failed item still
    shows its cost. The tally rides on the exception, not on the baseline, because one
    baseline answers several items at once.
    """
    try:
        yield
    except Exception as err:
        if not hasattr(err, "tally"):
            total = Tally()
            for tally in tallies:
                total.merge(tally)
            err.tally = total  # type: ignore[attr-defined]
        raise


def parsed_of(result: ModelResult, purpose: str) -> dict:
    if not isinstance(result.parsed, dict):
        raise ModelError(f"{purpose}: the reply holds no structured output")
    return result.parsed


class Answerer:
    """The one answering call every baseline shares: same prompt, model and max_tokens."""

    def __init__(self, port: ModelPort, family: Family, role: Role = "answerer") -> None:
        self.port = port
        self.family = family
        self.role = role

    def request(
        self,
        purpose: str,
        system: str,
        messages: list[dict],
        schema: dict | None = None,
        role: Role | None = None,
        max_tokens: int = MAX_TOKENS,
    ) -> ModelRequest:
        return ModelRequest(
            purpose=purpose,
            role=role or self.role,
            family=self.family,
            system=system,
            messages=messages,
            schema=schema,
            max_tokens=max_tokens,
        )

    def call(self, tally: Tally, req: ModelRequest) -> ModelResult:
        try:
            result = self.port.complete(req)
        except ModelError as err:
            billed = billed_result(err)  # a refusal or cut-off reply was still paid for
            if billed is not None:
                tally.add(billed)
            raise
        tally.add(result)
        return result

    def answer(
        self, item: QAItem, context: str, allowed_ids: Collection[str], tally: Tally, system: str = ANSWER_SYSTEM
    ) -> tuple[str, list[str]]:
        """The answer, and the cited ids that really were in the context.

        The reply is strict JSON {"answer", "cited"}; ids not in `allowed_ids` are dropped. A
        plain-text reply (no structured output) is the answer, with no citations.
        """
        req = self.request(
            "lme.answer", system, [{"role": "user", "content": question_message(item, context)}], ANSWER_SCHEMA
        )
        result = self.call(tally, req)
        if result.parsed is None:
            return result.text.strip(), []
        parsed = parsed_of(result, "lme.answer")
        answer = parsed.get("answer")
        if not isinstance(answer, str):
            raise ModelError("lme.answer: the reply holds no answer text")
        return answer, _valid_ids(parsed.get("cited"), allowed_ids)


def _valid_ids(raw: object, allowed: Collection[str]) -> list[str]:
    ids = raw if isinstance(raw, list) else []
    return list(dict.fromkeys(i for i in ids if isinstance(i, str) and i in allowed))


# --- BM25 over SQLite FTS5 -----------------------------------------------------------------


def query_terms(query: str) -> list[str]:
    """Unique word terms of a query. Only word characters survive, so quoting them is safe."""
    seen = dict.fromkeys(re.findall(r"\w+", query.lower()))
    return list(seen)[:MAX_QUERY_TERMS]


def bm25_rank(texts: list[str], query: str, limit: int | None = None) -> list[int]:
    """Indexes of `texts` that match the query, best BM25 first (in-memory FTS5)."""
    terms = query_terms(query)
    if not terms or not texts:
        return []
    match = " OR ".join(f'"{t}"' for t in terms)
    con = sqlite3.connect(":memory:")
    try:
        con.execute("CREATE VIRTUAL TABLE docs USING fts5(body, tokenize='porter unicode61')")
        con.executemany("INSERT INTO docs(rowid, body) VALUES (?, ?)", enumerate(texts))
        rows = con.execute(
            "SELECT rowid FROM docs WHERE docs MATCH ? ORDER BY bm25(docs), rowid LIMIT ?",
            (match, limit if limit is not None else len(texts)),
        ).fetchall()
    finally:
        con.close()
    return [r[0] for r in rows]


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


# --- baselines ------------------------------------------------------------------------------


class Baseline(Protocol):
    system: str
    family: str

    def answer(self, item: QAItem) -> Prediction: ...


class _Base:
    system = ""

    def __init__(self, port: ModelPort, family: Family, token_budget: int | None = None) -> None:
        self.answerer = Answerer(port, family)
        self.family = family
        self.token_budget = token_budget if token_budget is not None else _default_budget()

    def _prediction(
        self,
        item: QAItem,
        answer: str,
        cited: list[str],
        context_tokens: int,
        tally: Tally,
        meta: dict,
        context_ids: list[str],
    ) -> Prediction:
        return Prediction(
            item_id=item.id,
            system=self.system,
            answer=answer,
            cited_message_ids=cited,
            context_tokens=context_tokens,
            usage=tally.usage,
            cost_usd=tally.cost_usd,
            latency_s=tally.latency_s,
            calls=tally.calls,
            meta={
                "family": self.family,
                "model": tally.model,
                "baseline": self.system,
                "context_message_ids": context_ids,
                **meta,
            },
        )

    def _answer_from(
        self, item: QAItem, context: str, context_ids: list[str], meta: dict, system: str = ANSWER_SYSTEM
    ) -> Prediction:
        """One answering call over `context`, which shows the turns `context_ids`."""
        tally = Tally()
        with keeps_tally(tally):
            answer, cited = self.answerer.answer(item, context, set(context_ids), tally, system)
        return self._prediction(item, answer, cited, estimate_tokens(context), tally, meta, context_ids)


def _shown(messages: list[Message], text: str) -> list[str]:
    """The ids of `messages` that `text` shows (a turn cut off the end of a truncated block is not shown)."""
    return [m.id for m in messages if f"[{m.id}]" in text]


def _default_budget() -> int:
    return int(northstar_config.load()["eval"]["token_budget"])


def _context_of(picked: list[Round], fitted: Fitted) -> tuple[str, list[str]]:
    """The context for the rounds a fit kept, and the turn ids it shows. A truncated round is cut."""
    if fitted.truncated:
        return fitted.text or "", _shown(picked[0].messages, fitted.text or "")
    return render_rounds(picked), [i for r in picked for i in r.message_ids]


class FullHistory(_Base):
    """B0: every session in time order; the oldest are dropped past `max_context`."""

    system = "B0"

    def __init__(
        self, port: ModelPort, family: Family, max_context: int = DEFAULT_MAX_CONTEXT, token_budget: int | None = None
    ) -> None:
        super().__init__(port, family, token_budget)
        self.max_context = max_context

    def answer(self, item: QAItem) -> Prediction:
        blocks = [render_turns(s.id, s.started_at, s.messages) for s in item.haystack]
        costs = [estimate_tokens(b + "\n\n") for b in blocks]
        total = sum(costs)
        dropped = 0
        while total > self.max_context and dropped < len(blocks):
            total -= costs[dropped]
            dropped += 1
        kept = item.haystack[dropped:]
        ids = [m.id for s in kept for m in s.messages]
        meta = {
            "sessions_total": len(blocks),
            "dropped_sessions": [s.id for s in item.haystack[:dropped]],
            "max_context": self.max_context,
        }
        return self._answer_from(item, "\n\n".join(blocks[dropped:]), ids, meta)


class KeywordSearch(_Base):
    """B1: BM25 over rounds, best first, until the token budget; shown in time order.

    `embedder` is the hook for vector search: when given, its cosine ranking is fused with
    BM25 by reciprocal rank. It is unused by default, and meta says which was run.
    """

    system = "B1"

    def __init__(
        self, port: ModelPort, family: Family, token_budget: int | None = None, embedder: Embedder | None = None
    ) -> None:
        super().__init__(port, family, token_budget)
        self.embedder = embedder

    def _ranked(self, rounds: list[Round], question: str) -> list[int]:
        ranked = bm25_rank([r.text for r in rounds], question)
        if self.embedder is None or not rounds:
            return ranked
        vectors = np.asarray(self.embedder.embed([question] + [r.text for r in rounds]), dtype=float)
        norms = np.linalg.norm(vectors, axis=1)
        norms[norms == 0] = 1.0
        sims = (vectors[1:] / norms[1:, None]) @ (vectors[0] / norms[0])
        by_vector = [int(k) for k in np.argsort(-sims, kind="stable")]
        score: dict[int, float] = {}
        for ranking in (ranked, by_vector):
            for position, k in enumerate(ranking):
                score[k] = score.get(k, 0.0) + 1.0 / (60 + position)
        return sorted(score, key=lambda k: (-score[k], k))

    def answer(self, item: QAItem) -> Prediction:
        rounds = all_rounds(item)
        order = self._ranked(rounds, item.question)
        fitted = fit_to_budget(order, self.token_budget, key=lambda k: rounds[k].render() + "\n\n")
        picked = [rounds[k] for k in sorted(fitted.blocks)]
        context, ids = _context_of(picked, fitted)
        meta = {
            "rounds_total": len(rounds),
            "rounds_included": len(picked),
            "token_budget": self.token_budget,
            "vector_search": self.embedder is not None,
            "truncated": fitted.truncated,
        }
        return self._answer_from(item, context, ids, meta)


class Oracle(_Base):
    """B3: the rounds holding the gold evidence, in time order, within the token budget."""

    system = "B3"

    def answer(self, item: QAItem) -> Prediction:
        gold = set(item.evidence_message_ids)
        rounds = [r for r in all_rounds(item) if gold.intersection(r.message_ids)]
        fitted = fit_to_budget(rounds, self.token_budget, key=lambda r: r.render() + "\n\n")
        picked = fitted.blocks
        context, ids = _context_of(picked, fitted)
        meta = {
            "evidence_rounds": len(rounds),
            "rounds_included": len(picked),
            "token_budget": self.token_budget,
            "truncated": fitted.truncated,
        }
        return self._answer_from(item, context, ids, meta)


class ClosedBook(_Base):
    """"none": the answering call with no history at all; what the model knows without memory."""

    system = "none"

    def answer(self, item: QAItem) -> Prediction:
        return self._answer_from(item, "", [], {"history": "none"}, CLOSED_BOOK_SYSTEM)


# B2 ---------------------------------------------------------------------------------------

ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["search", "read", "answer"]},
        "pattern": {"type": ["string", "null"]},
        "session_id": {"type": ["string", "null"]},
        "start": {"type": ["integer", "null"]},
        "end": {"type": ["integer", "null"]},
        "answer": {"type": ["string", "null"]},
        "cited": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["action", "pattern", "session_id", "start", "end", "answer", "cited"],
    "additionalProperties": False,
}
FINAL_SCHEMA = {
    **ACTION_SCHEMA,
    "properties": {**ACTION_SCHEMA["properties"], "action": {"type": "string", "enum": ["answer"]}},
}
GREP_SYSTEM = (
    RULES + "\n\nYou cannot see the history yet. Look through it with these actions; reply with one JSON action each time. "
    'Set the fields an action does not use to null, and `cited` to [].\n'
    '- {"action": "search", "pattern": ...}: find turns matching a case-insensitive word or regular expression; '
    f"you get up to {SEARCH_HITS} snippets with turn ids and dates.\n"
    '- {"action": "read", "session_id": ..., "start": ..., "end": ...}: read the turns of one session from index '
    f"`start` to `end`, both inclusive, at most {READ_TURNS} turns.\n"
    '- {"action": "answer", "answer": ..., "cited": [...]}: give the final answer, and in `cited` the ids of the '
    "turns it rests on, taken from what you have seen.\n"
    f"You have at most {MAX_STEPS} steps and a limited amount of text to read in total; answer before they run out."
)


class GrepAgent(_Base):
    """B2: the model searches and reads the history itself, as JSON actions."""

    system = "B2"

    def __init__(
        self, port: ModelPort, family: Family, token_budget: int | None = None, max_steps: int = MAX_STEPS
    ) -> None:
        super().__init__(port, family, token_budget)
        self.max_steps = max_steps

    def answer(self, item: QAItem) -> Prediction:
        tally = Tally()
        with keeps_tally(tally):
            return self._loop(item, tally)

    def _loop(self, item: QAItem, tally: Tally) -> Prediction:
        by_id = {s.id: s for s in item.haystack}
        dates = [s.started_at for s in item.haystack if s.started_at]
        span = f", from {format_date(dates[0])} to {format_date(dates[-1])}" if dates else ""
        opening = (
            f"Current date: {format_date(item.question_date)}\n"
            f"The history has {len(item.haystack)} sessions{span}.\n\nQuestion: {item.question}"
        )
        messages = [{"role": "user", "content": opening}]
        seen: dict[str, None] = {}  # the turn ids it was shown, in the order shown
        used = 0
        must_answer = False
        trail: list[str] = []
        for step in range(self.max_steps + 1):
            final = must_answer or step == self.max_steps
            req = self.answerer.request(
                "b2.answer" if final else "b2.step", GREP_SYSTEM, messages, FINAL_SCHEMA if final else ACTION_SCHEMA
            )
            result = self.answerer.call(tally, req)
            action = parsed_of(result, req.purpose)
            kind = action.get("action")
            trail.append(str(kind))
            if kind == "answer" or final:
                answer = action.get("answer") or ""
                cited = _valid_ids(action.get("cited"), seen)
                meta = {"steps": trail, "forced": final, "token_budget": self.token_budget}
                return self._prediction(item, answer, cited, used, tally, meta, list(seen))
            observation, ids = self._observe(action, item, by_id)
            room = self.token_budget - used
            cost = estimate_tokens(observation)
            if cost >= room:
                observation = cut_to_tokens(observation, room) + "\n[cut: the reading budget is used up]"
                used = self.token_budget
                must_answer = True
                observation += "\nYour next action must be \"answer\"."
                ids = [i for i in ids if f"[{i}]" in observation]  # ids in the cut part were not shown
            else:
                used += cost
            seen.update(dict.fromkeys(ids))
            observation += f"\n(Steps left before you must answer: {self.max_steps - step - 1}.)"
            messages.append({"role": "assistant", "content": result.text or json.dumps(action)})
            messages.append({"role": "user", "content": observation})
        raise AssertionError("unreachable: the last step always answers")

    def _observe(self, action: dict, item: QAItem, by_id: dict[str, Source]) -> tuple[str, list[str]]:
        if action.get("action") == "search":
            return self._search(action.get("pattern"), item)
        return self._read(action, by_id)

    def _search(self, pattern: object, item: QAItem) -> tuple[str, list[str]]:
        if not isinstance(pattern, str) or not pattern.strip():
            return 'Error: "search" needs a pattern.', []
        try:
            rx = re.compile(pattern, re.IGNORECASE)
        except re.error:
            rx = re.compile(re.escape(pattern), re.IGNORECASE)
        hits: list[tuple[Source, Message, str]] = []
        total = 0
        for source in item.haystack:
            for m in source.messages:
                found = rx.search(m.text)
                if found is None:
                    continue
                total += 1
                if len(hits) < SEARCH_HITS:
                    lo, hi = max(0, found.start() - 80), min(len(m.text), found.end() + 160)
                    snippet = " ".join(m.text[lo:hi].split())
                    hits.append((source, m, ("..." if lo else "") + snippet + ("..." if hi < len(m.text) else "")))
        if not hits:
            return f"No turn matches {pattern!r}.", []
        lines = [f"{total} turns match {pattern!r}; showing the first {len(hits)} in date order."]
        lines += [f"[{m.id}] {format_date(s.started_at)} {m.speaker}: {snip}" for s, m, snip in hits]
        return "\n".join(lines), [m.id for _, m, _ in hits]

    def _read(self, action: dict, by_id: dict[str, Source]) -> tuple[str, list[str]]:
        source = by_id.get(action.get("session_id") or "")
        if source is None:
            return f'Error: no session {action.get("session_id")!r}.', []
        start = max(0, action.get("start") or 0)
        end = action.get("end")
        end = start + READ_TURNS - 1 if end is None else min(end, start + READ_TURNS - 1)
        turns = source.messages[start : end + 1]
        if not turns:
            return f"Session {source.id} has {len(source.messages)} turns (indexes 0 to {len(source.messages) - 1}).", []
        return render_turns(source.id, source.started_at, turns), [m.id for m in turns]


# B4 ---------------------------------------------------------------------------------------

OBSERVE_SCHEMA = {
    "type": "object",
    "properties": {
        "observations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"text": {"type": "string"}, "message_ids": {"type": "array", "items": {"type": "string"}}},
                "required": ["text", "message_ids"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["observations"],
    "additionalProperties": False,
}
OBSERVE_SYSTEM = (
    "You keep a dated log about a user. You read one conversation between the user and an AI assistant and write "
    "short observations about the user from it alone: facts about them, what they own, did, plan or prefer, "
    "decisions, and changes in their situation. One fact per observation, in one sentence, in your own words; "
    "keep any time the user mentions (such as 'last week') as they said it, since the session date anchors it. "
    "Skip small talk and what only the assistant said. Write nothing the conversation does not support. "
    "In `message_ids`, list the ids shown in square brackets of the turns that support the observation."
)
OBSERVE_PURPOSE = "b4.observe"
OBSERVE_MAX_TOKENS = 4096  # a long session yields many observations; 1024 would cut the JSON off


@dataclass(slots=True)
class Observation:
    session_id: str
    date: str | None
    text: str
    message_ids: list[str]  # the turns behind it
    id: str = ""  # what an answer cites: "o1", "o2", ... in log order

    def render(self) -> str:
        return f"[{self.id}] {format_date(self.date)}: {self.text}"


class ObservationLog(_Base):
    """B4: an append-only dated observation log, one small-model pass per session.

    The log is only ever appended to. At answer time the whole log goes in when it fits
    the token budget; otherwise BM25 over the observations picks by rank until it does.
    """

    system = "B4"

    def build_log(self, item: QAItem, tally: Tally) -> list[Observation]:
        log: list[Observation] = []
        for source in item.haystack:
            content = render_turns(source.id, source.started_at, source.messages)
            req = self.answerer.request(
                OBSERVE_PURPOSE, OBSERVE_SYSTEM, [{"role": "user", "content": content}], OBSERVE_SCHEMA, role="worker_small",
                max_tokens=OBSERVE_MAX_TOKENS,
            )
            parsed = parsed_of(self.answerer.call(tally, req), OBSERVE_PURPOSE)
            in_session = {m.id for m in source.messages}
            for raw in parsed["observations"]:
                text = str(raw["text"]).strip()
                if text:
                    ids = _valid_ids(raw.get("message_ids"), in_session)
                    log.append(Observation(source.id, source.started_at, text, ids, f"o{len(log) + 1}"))
        return log

    def answer(self, item: QAItem) -> Prediction:
        build, query = Tally(), Tally()  # building the log is paid once per history; the query is what a question adds
        with keeps_tally(build, query):
            log = self.build_log(item, build)
            lines = [o.render() for o in log]
            whole = estimate_tokens("\n".join(lines)) <= self.token_budget
            truncated = False
            if whole:
                chosen = list(range(len(log)))
                context = "\n".join(lines)
            else:
                order = bm25_rank([o.text for o in log], item.question)
                fitted = fit_to_budget(order, self.token_budget, key=lambda k: lines[k] + "\n")
                chosen = sorted(fitted.blocks)
                truncated = fitted.truncated
                context = fitted.text if truncated else "\n".join(lines[k] for k in chosen)
            shown = [log[k] for k in chosen if f"[{log[k].id}]" in context]
            context_ids = list(dict.fromkeys(i for o in shown for i in o.message_ids))
            answer, cited_obs = self.answerer.answer(item, context, [o.id for o in shown], query)
            by_obs = {o.id: o for o in shown}
            cited = list(dict.fromkeys(i for oid in cited_obs for i in by_obs[oid].message_ids))
        total = Tally()
        total.merge(build)
        total.merge(query)
        meta = {
            "mode": "whole_log" if whole else "bm25",
            "log_entries": len(log),
            "entries_included": len(chosen),
            "token_budget": self.token_budget,
            "observer_role": "worker_small",
            "truncated": truncated,
            "cited_observation_ids": cited_obs,
            "build_cost_usd": build.cost_usd,
            "build_latency_s": build.latency_s,
            "query_cost_usd": query.cost_usd,
            "query_latency_s": query.latency_s,
        }
        return self._prediction(item, answer, cited, estimate_tokens(context), total, meta, context_ids)


# --- running ---------------------------------------------------------------------------------


def run_baseline(items: list[QAItem], baseline: Baseline, max_workers: int = 4) -> list[Prediction]:
    """Predictions in input order. One item's failure is recorded and does not stop the run."""

    def one(item: QAItem) -> Prediction:
        try:
            return baseline.answer(item)
        except Exception as err:  # noqa: BLE001 - isolate each item
            meta = {"family": baseline.family, "baseline": baseline.system, "error": f"{type(err).__name__}: {err}"}
            spent: Tally | None = getattr(err, "tally", None)  # what the item cost before it failed
            if spent is None:
                return Prediction(item.id, baseline.system, "", meta=meta)
            meta["model"] = spent.model
            return Prediction(
                item.id, baseline.system, "", usage=spent.usage, cost_usd=spent.cost_usd, latency_s=spent.latency_s,
                calls=spent.calls, meta=meta,
            )

    with ThreadPoolExecutor(max_workers=max(1, max_workers)) as pool:
        return list(pool.map(one, items))
