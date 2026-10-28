# 0010. Capture timing: deterministic weekly cards, in-flow capture for decisions only, sandboxed backfill, no hooks

- **Status:** Proposed
- **Date:** 2026-10-07
- **Revised 2026-10-07 after review:** v0's weekly cards come from a deterministic, zero-LLM floor (cue extractor, takeaway trigger, BM25 relate, recall rotation); agent prep moves to v0.5 behind a trigger and a spike; in-flow decisions use a pull protocol (the agent writes no field text; Jack's reply is read from the transcript after a nonce), capped at one offer a day and three a week; backfill is seeded by question; the E8 report is hand-run in weeks 1–2; the notes folder waits for Jack to ask. See `REVIEW.md` (scope-simplicity-6; ai-safety-privacy-1; engineering-4; human-2, -14; problem-fit-1, -7).

## Context

T10 in the synthesis: draft and confirm at the moment of commitment so pre-outcome fields are locked [05], or extract in batch after the episode because stance belongs to the whole episode [08]. Batch extraction from the episode recovers what was said; what cannot be recovered is what was never said: expectations and confidence. E's hook-based in-moment capture put undocumented vendor behaviour on the critical path. Backfilling exports risks hindsight leakage [A].

The review found v0.1's LLM prep pipeline had almost nothing to process in v0's first weeks and relied on maintainer isolation that does not exist as described, and that in-flow verification could be satisfied by agent-worded fields.

## Decision

1. **Weekly cards, v0: deterministic** (DESIGN §6.5), built an hour before the slot from triaged episodes: commitment cues for capture cards; a takeaway trigger for learning conversations (most self turns are questions and the assistant wrote ≥5× more); BM25 matches of self spans, recent notes and assistant spans against Jack's positions for relate cards; recall rotation; due items. `project:northstar` contributes at most one card.
2. **Agent prep, v0.5**, when the floor yields fewer than 5 non-recall cards a Session for 2 weeks or Jack asks for counterpoints: a `tools: Read` maintainer subagent, gated at submit (DESIGN §6.5), with only same-account episodes (ADR-0016).
3. **In-flow capture, for decisions only, through a skill, with no hooks** (DESIGN §8.4). The skill offers at most once a day and three times a week, as one non-blocking line, in personal folders, on Jack's own commitment language. The agent supplies pointers to Jack's quotes and no text of its own; `ns` prints a card with a nonce; Jack replies in chat; `ns decide --confirm <nonce>` reads the reply from the transcript named by the session ID and writes the decision only if verified. A bare "yes" records `endorsed` with no frozen fields. A miss becomes a capture candidate.
4. **Backfill (v1), as-of sandboxed and seeded by question.** A job sees only its episode, Jack's records held or said before its end, and candidates rejected by then; it draws at most 3 historical spans per open question, delivered once as history recall cards. Decisions are episode-sourced; expectations only from quoted text.
5. **E8, weeks 1–2:** a same-origin agent reads a 30–50 conversation export sample by hand and writes a quoted change-of-mind report, exempt from the build gate.
6. **Notes folder** only if Jack asks for phone capture (Q8). **Web chats:** exports via v0.5 adapters; a web clerk is R15.

## Alternatives considered

- **Hooks as the primary route (E).** Rung R9.
- **LLM prep in v0 (v0.1).** Built before there is data; isolation unverified.
- **An agent-written agenda in v0 (scope-simplicity-6).** Deferred with the subagent spike; G0's hand-built agendas show what it adds.
- **Unsandboxed or lottery-pool backfill.** Hindsight contamination; years to integrate.

## Consequences

- Pre-outcome fields are captured when they exist, for the highest-payoff object [05]; other commitments wait at most a week.
- Capture does not depend on Sessions, so the pack grows in skipped weeks.
- v0 runs with no model and no key.

## Deciding evidence or experiment

- E1 yield from card verdicts; E11 (v0.5) in-flow recall, below 40% → consider R9.
- Mechanism ledger: fewer than 1 in-flow capture a week for 4 weeks → terminal `ns decide` only.
- E12: in-flow verification misses.
