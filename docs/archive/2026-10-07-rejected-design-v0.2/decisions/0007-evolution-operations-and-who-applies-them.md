# 0007. Evolution operations and who applies them: nothing semantic is auto-applied

- **Status:** Proposed
- **Date:** 2026-10-07
- **Revised 2026-10-07 after review:** the change question has three options plus "not sure", which still records the new view (`sharpen` folded into "my view changed"); a kind-agnostic `supersede` op links existing records; `record.correct`, `record.status` and `record.rescope` replace position-only ops; reinstatement and undoing a correction are possible; the P3 list adds `basis` and `decided_at_q` and drops the stored integrity grade (now computed); consolidation includes a monthly review card; R13 no longer depends on catch trials. See `REVIEW.md` (epistemics-6, -7; human-8, -9; engineering-2, -3; problem-fit-7; scope-simplicity-8).

## Context

The research converges on supersede, never overwrite, and on deprecating with a reason rather than deleting [SYN P2]. Typed changes (FR10) must keep apart *the world changed*, *I changed my mind* and *the record was wrong*; only A kept the last apart, and without it extraction errors fill the change feed. Unwatched automatic changes drift [06]. C's ladder cannot protect data whose absence never fails a probe [research judge].

The review found v0.1's six-way change question asked a distinction its own worked example could not apply (mind vs sharpen), that `?` lost the new view, that "unclassified" had no op, and that reversals, un-retractions and undone corrections could not be represented.

## Decision

1. **Authority.** Code applies bookkeeping (archive, classify, redact, index, views, packs, expiry, excision execution). AI and code only *propose*. **Only Jack records**: stating, superseding, correcting, retracting, reinstating, rewording, relating, opening, closing, holding or nesting questions, committing and reviewing decisions, verdicts, alias, rescope, excise. Nothing is auto-applied in v0.
2. **The change question, unanchored** (DESIGN §5.3): `1` my view changed (including sharpening or narrowing; the because-line carries the nuance) → `supersede/mind`; `2` the world changed → `supersede/world`, setting `valid_to`; `3` the record was wrong → `record.correct`, with one follow-up (never held anything like it / held something else), record time only, never in the feed; `4` not sure → `supersede/unknown`, still recording the new view. Rewording comes from the recall card; retraction from "drop it" or `ns status`. The same `change` enum types decision supersession.
3. **The recoverability exemption** [A]. Captured strictly from v0 (DESIGN P3): Jack's verdicts and because-lines; change type; `held_from` and its qualifier on every new position; `basis`; `decided_at` and its qualifier; the frozen expectation and confidence with `typed_at`; receipts. Everything recomputable stays loose.
4. **Kind-agnostic corrections and status.** `record.correct {id, field, value, because}` fixes any field, including `never_held` (true or false) and a supersession's `change`; `record.status` retracts, lapses or reinstates; `reinstates` on a new position records a return to an earlier view. Derived "no longer held" lines and antibodies skip reinstated views.
5. **Verdicts are Jack's acts**, with a one-key reason (hypothetical, not mine, trivial, doesn't fit, misquoted). The latest verdict on a candidate wins, so a rejection can be reversed.
6. **Consolidation never rewrites text.** It is Jack's act: weekly relate, supersede and takeaway cards, and a monthly review card that keeps, parks, answers, dissolves, merges (`alias`) or nests (`part_of`) questions and ends with an unaided recall (DESIGN §5.2).
7. **Recall before reveal** on every revision flow [01].
8. **Promotion to auto-apply** only through rung R13: a class with >95% acceptance and <5% edits for 6 weeks, labelled and undoable.

## Alternatives considered

- **A's auto-applied world updates; E's auto-applied relations.** Premature; modality errors are unmeasured.
- **Keeping `sharpen` (v0.1, epistemics-6).** Not reliably separable from a change of mind; P3 would make the noise permanent.
- **Untyped `supersedes` with an `is_correction` flag.** The fallback if the typed question fails.

## Consequences

- The change feed holds changes of mind (including "type unsure"), tagged world changes and retractions; never corrections.
- Each change costs Jack a few seconds; "not sure" never loses the view.
- Mis-keys are recoverable: an undo buffer per card, and record-time corrections for anything later.

## Deciding evidence or experiment

- Mechanism-ledger cut rule: more than 30% "not sure" → collapse to `supersedes` plus `is_correction`. The correction split is never cut.
- E6 (v0.5): the prep model's hidden guess against Jack's answer.
- E8: whether J2 views stay primary.
