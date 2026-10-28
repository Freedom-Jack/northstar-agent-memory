# 0001. Framing: a practice around a small record of what Jack holds, built on the thin-layer base

- **Status:** Proposed
- **Date:** 2026-10-07
- **Revised 2026-10-07 after review:** the record now explicitly covers learned understanding (positions on "How does X work?" questions, captured by takeaway cards), aims, revisable notes and a monthly consolidation; the scope and the bounded-integration trade are stated for Jack to approve (DESIGN §1.2, Q0). See `docs/design/REVIEW.md` (problem-fit-1, -5, -7, -9).

## Context

The brief describes knowledge that piles up as disconnected fragments and asks for a "coherent, evolving understanding". The research ([SYN] §2) gives three reasons why "build a knowledge base" is the wrong frame:
- Raw logs plus search already handle recall (a files-plus-grep agent beat Mem0 on LoCoMo).
- Fluent AI synthesis raises felt understanding while lowering learning [01].
- The unsolved problems are on the write path (attribution, updates, conflicts) and in the human loop (integration, review, ownership).

The disk adds two facts: Claude Code deletes logs after 30 days and nothing else keeps them; and today's corpus is two days old, mostly the Northstar build itself, so it is unrepresentative of the learning and reading the brief describes (DESIGN §1.1).

Five proposals answered this and three judges scored them (`docs/design/JUDGING.md`). C, the thin layer, ranked first with every judge; D, the integration ritual, second. The review found that v0.1 over-corrected from "don't store AI-written synthesis" to "don't represent learned knowledge at all", dropping the learning hooks B, C and D all carried and the research's call for person-authored explanations of core models [01 implication 12; SYN T4].

## Decision

1. **Frame.** Northstar is *a loop, not a store*: a permanent archive (infrastructure); a small, append-only record of what Jack holds (questions and aims; positions, **including Jack's understanding of how something works**; decisions; notes), each with where it came from; an **integration loop** (the weekly Session with a monthly review, plus in-flow captures); and a **compilation loop** (packs and on-demand records for AI tools). Coherence lives in Jack; the record is a legible, attributed witness the present cannot rewrite.
2. **Scope, stated plainly.** DESIGN §1.2 lists each brief item as in, partly in, or deferred, and why. Evolution without fragments is answered at a bounded rate: about 7 integrations a week plus a monthly consolidation in Jack's words, with everything else kept searchable and uncondensed. Jack approves this trade at Q0.
3. **Base.** C's architecture: archive first, JSONL ledgers outside git, a disposable index, deterministic views, a ladder of triggered rungs. **C's human loop is replaced by D's integration Session** (ADR-0009).
4. **Grafts.** A's recoverability fields (ADR-0005, -0006, -0007); E's in-flow decision capture, verified by pulling the reply from the transcript (ADR-0010); B's quote-cutting by code and exposure discipline, now an origin rule (ADR-0016).
5. **Non-goals.** A knowledge base of what sources say, a wiki, an AI profile, stored syntheses, a note editor, instruction management, automatic belief updates.
6. **The failure condition, explicit.** A design that improves the record at Jack's expense has failed, even if it scores well on probes.

## Alternatives considered

- **D as the base, trimmed to C's core.** Converges on nearly the same system; rejected as the framing because C's substrate and ladder are the parts hard to retrofit.
- **A as the base.** Best on epistemic correctness, but proposition identity is on its critical path.
- **B as the base.** Editable canonical Markdown turns invariants into lint conventions and forces excision to rewrite git history.
- **E as the base.** Hooks and undocumented fields on the critical path; AI-drafted wording as the main way beliefs enter.
- **A knowledge base of AI-maintained topic pages.** Rejected for v0 on the learning evidence [01]; available only through rung R6 with E7 as its gate, and re-reviewed if Jack answers Q0 "no".
- **Averaging all five.** A system with every mechanism and no thesis.

## Consequences

- The value depends on Jack's bounded weekly practice and on in-flow decision capture, not on mining volume.
- v0 needs no LLM at all (ADR-0011).
- Learned understanding enters only in Jack's words, recall before reveal; what Jack read stays raw until Jack says what Jack took from it.
- Any new structure must name a failing probe (ADR-0014); the P3 fields are exempt (ADR-0007).

## Deciding evidence or experiment

- **Q0 at approval:** Jack confirms or rejects the frame.
- **G0** (DESIGN §12.1): two hand-built Sessions on export material, including a learning conversation.
- **Coverage** (DESIGN §10.4): more than 20% of close-card notes with no home is a pre-registered signal to revisit the kinds.
- **E3** (DESIGN §10.4): the typed ledger against the same records rendered as a journal.
