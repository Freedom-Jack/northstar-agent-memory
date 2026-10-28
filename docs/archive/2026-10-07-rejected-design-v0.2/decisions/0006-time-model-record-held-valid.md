# 0006. Time model: record time, held time with a bound qualifier, and valid time only for world changes

- **Status:** Proposed
- **Date:** 2026-10-07
- **Revised 2026-10-07 after review:** every new position, including one created by a revision, carries `held_from` with its qualifier; normative fold rules replace the implicit semantics (DESIGN §5.6); as-of is three-valued and prints its bounds; `last_confirmed` is derived from Jack's live acts; decisions carry `decided_at_q`, and integrity is computed, never stored; partial dates are intervals; confidence is shown only from when it was first recorded; the fixture has 12 scenarios written from the rules. See `REVIEW.md` (engineering-2; epistemics-2, -3, -8, -13).

## Context

"Evolving" covers four kinds of change [SYN §1.3]; the two that matter here are *the world changed* and *my mind changed*. Capture time is only an upper bound on belief time [06], and belief onset cannot be reconstructed later unless there is a field for it now [A].

The review found v0.1's time model right in concept and wrong in detail: revisions had no `held_from`, so every change of mind was dated to the Session; `no_later_than` was read as exact, so queries before a capture returned "no position" instead of "unknown"; confidence was shown at dates before it was recorded; Session decisions were graded "contemporaneous" by default; and no rule said what happens with retroactive links, splits, several heads or partial dates.

## Decision

- **Clocks.** `at` (record time) on every event; `said_at` on spans, encounters and notes; `held_from` with `held_from_q ∈ {exact, approx, no_later_than, unknown}` on every new position; `held_to` and `last_confirmed` derived; `valid_to` set only by "the world changed" and display-only in v0.
- **Defaults.** `held_from` and `decided_at` default to `no_later_than` the earliest dated self evidence on the card (else the Session date). The Session shows the bound and Jack accepts it with Enter or chooses today.
- **Decisions** carry `decided_at`, `decided_at_q` and `frozen.typed_at`. **Integrity is computed** (DESIGN §5.6 rule 13): endorsed, episode-sourced, contemporaneous (expectation typed within 24 hours of the latest possible decision time) or retrospective. Calibration uses only the middle two.
- **The fold rules in DESIGN §5.6 are normative**, in particular: supersession links existing records in any order; heads may be several; for a change of mind the old `held_to` equals the new `held_from`; a world change sets `valid_to` instead; Jack's live acts confirm a record and tighten bounds; as-of is held / not held / indeterminate per record with printed bounds; corrections apply on the belief clock and appear on the record clock only from their `at`; reinstatement clears derived "no longer held" lines.
- **Both clocks.** `ns asof <D>` (belief time, everything recorded so far) and `ns asof <D> --recorded-by <R>` (what the record said then).
- **Backfill** is sandboxed by said or held time (ADR-0010).
- **The fixture is the spec:** 12 scenarios in v0 (DESIGN §10.1), more with backfill.

## Alternatives considered

- **C's two clocks with a derived held interval.** Cannot express "since about 2022" or a correction that leaves belief time alone; fatal to J2.
- **A's three clocks with credence intervals, or full bitemporality on everything (E).** More than needed, with more clock bugs.
- **Exact-or-nothing onsets.** Reads `no_later_than` as exact and produces false negatives for every query before capture.

## Consequences

- `ns changes` lists changes of mind, world changes and retractions, never corrections.
- History pages are honest about uncertainty ("held since no later than 9 Nov"; "changed between 6 and 9 Nov").
- Clock logic is subtle; the fixture and a replay-order property test carry it.
- If no probe ever distinguishes held from recorded time, the cost is two fields, hidden from views.

## Deciding evidence or experiment

- The fold fixture in CI.
- E3's history probes (DESIGN §10.4).
- Mechanism ledger: `held_from` is never cut; hidden from views if unused for 8 weeks.
