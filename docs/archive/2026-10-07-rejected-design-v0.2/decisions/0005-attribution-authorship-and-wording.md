# 0005. Attribution, authorship and wording: the AI said X is never I hold X

- **Status:** Proposed
- **Date:** 2026-10-07
- **Revised 2026-10-07 after review:** speaker rules fixed to the real log shapes (per content block, queued messages, tags denied by default); `basis` restored as a P3 field and "rests only on AI" redefined on it; echo by order replaces lexical overlap; the `auth` field and the pending/verified state machine are removed: Sessions run in a terminal, and the only agent path, `ns decide`, verifies synchronously by pulling Jack's reply from the transcript; an explicit threat model and a write guard; no AI drafts in v0. See `REVIEW.md` (engineering-4, -6; epistemics-4, -5; ai-safety-privacy-1, -6; human-7).

## Context

In agent logs, `role=user` is not the user: 94% of session files here are orchestrated subagents, and memory systems absorb many assistant-introduced distractors as user memory [08]. LLM rationale matched actual rationale with about 0.27 precision [05]. T4 asks whether the person writes the belief layer or signs AI drafts; the generation and ownership evidence favours writing [01][07].

The review found v0.1's verification weak and fragile at once: single-key answers matched any human turn; shell relay corrupted text; about 7% of Jack's messages exist only as `queued_command` attachments; a subagent's call resolved to the parent's transcript; `auth: tty` was obtainable from any agent shell; and the main way AI shapes a belief (Jack adopting a suggestion in Jack's own words) was invisible because `basis` had been dropped.

## Decision

1. **Speaker is deterministic and set before any use**, per content block (DESIGN §6.3). Whole subagent files are `orchestrator`; `queued_command` attachments from a human are `self`; blocks that begin with a tag are `system` unless allowlisted.
2. **The holder of every record is Jack.** Others' claims exist only as archive quotes, or as encounters Jack related.
3. **Every text field on a person event is Jack's typed reply, a code-cut quote of Jack's own words, or a fixed template**, recorded per field in `wording_by`. CI asserts it.
4. **`basis`** on every position and decision: a set of reasoning, experience, ai, reading, person, or unknown, one keypress. "Rests only on AI" = `basis ⊆ {ai}` and no non-AI support. Lineage follows the speaker first; assistant spans are always `ai:<provider>`.
5. **Echo by order:** an assistant span is `echo:` when an earlier self turn in the same session grounds the record. Echo through packs and `ns get` is rung R5.
6. **Own words is the fixed default.** v0 offers no AI paraphrase; from v0.5 Jack may ask for one, recorded `ai_edited` or `ai_endorsed`.
7. **Sessions run in a terminal**, so no answer is relayed and nothing needs verifying.
8. **In-flow decisions: pull, don't relay** (DESIGN §8.4). The agent points at Jack's quotes and writes no field text; `ns` prints a card with a nonce; after Jack replies, `ns decide --confirm <nonce>` (no text argument) reads the transcript named by `CLAUDE_CODE_SESSION_ID`, checks the card was displayed, and takes the first human-origin entry after it. It refuses in child sessions. Only verified events reach `person.jsonl`; there is no `auth` field.
9. **Threat model.** These checks defend against content-borne forgery and relay error, not against a compromised local agent with shell access. A write guard refuses person-writes in agent shells, `ns setup` prints deny rules, and a weekly due card lets Jack keep or void each in-flow decision (DESIGN §8.5).

## Alternatives considered

- **Agent-relayed Sessions with after-the-fact verification (v0.1).** Vacuous for single keys, fragile for text, and slow (ADR-0009).
- **AI drafts signed with a tier (B, C, E).** The default path becomes fluent text Jack accepts.
- **Own words only with a near-copy check (D).** A difflib check blocks copies, not paraphrases.
- **Prompt hooks as the first key (E).** Undocumented desktop behaviour; rung R9.

## Consequences

- Attribution and authorship are auditable from the ledger alone.
- About a second per position for `basis`; positions are few.
- In-flow capture never leaves Jack with "pending" items; a miss is a candidate for the next Session and a count in `ns doctor`.

## Deciding evidence or experiment

- B1 speaker acceptance and the running `not mine` / `misquoted` rates (DESIGN §6.3).
- The week-4 audit of 30 recorded entries; each entry resting on a non-self span is an incident (DESIGN §10.5, E2).
- E12: every unexplained `ns decide` miss is an incident.
