# 0015. v0 cut line, build order and gates

- **Status:** Proposed
- **Date:** 2026-10-07
- **Origin:** new after the 2026-10-07 review. See `REVIEW.md` (engineering-9; scope-simplicity-1, -3, -6, -7, -11, -12, -13, -14; human-2, -4; problem-fit-8).

## Context

v0.1 promised v0 in 10 part-time build sessions and about 3,000–3,500 lines. Reviewers estimated the specification at 6–8K lines: it combined C's whole v0, items C itself deferred, D's card engine, E's capture and verification, A's clocks and a six-arm evaluation runner. There was no cut order, so overruns would have cut whatever came last, which was the pack and in-flow capture, the AI-side payoff. Jack's first felt benefit was about two weeks away, and the build/use ratio rule would have stopped the build it was meant to discipline.

Any cut must keep the P3 fields (DESIGN §2), because they cannot be recovered later.

## Decision

1. **v0 is six build sessions** of 2–4 hours (DESIGN §12.1), about 2,000–2,500 lines:
   - **B1 Keep everything:** archive with the ingest transform, Claude Code adapter and speakers, scopes, index, `ns find`, launchd, `ns doctor`; Codex copied raw.
   - **B2 Decisions and the pack:** ledgers, a minimal fold, `ns q`, `ns note`, terminal `ns decide`, `ns pack`, receipts, and the import and environment spikes. Jack records 3–5 real decisions the same day.
   - **B3 Fold and history:** the normative rules and fixture, state/revise/correct/status/rescope, history/asof/changes/why/get/show, `now.md`.
   - **B4 The Session:** the terminal runner and the zero-LLM card sources, configured for the weekly Session if G0 passes and for the runner-up otherwise (DESIGN §12.3).
   - **B5 In-flow capture:** the transcript-pull `ns decide` path and the `northstar` skill.
   - **B6 Checks:** CI, source excision, metrics, `ns eval`, the committed protocol.
2. **Critical path:** B1 → B3 → B4; B2 branches off early for the same-day payoff.
3. **Cut order** if a session overruns by more than 1.5×: monthly review card, takeaway reveal text, `ns show` pages, the in-flow agent path, relate cards. **Never cut:** B1, the ledger with every P3 field, the fold fixture, terminal `ns decide` and the pack, recall/capture/close cards, and the core CI subset.
4. **Gates.** G0 (two hand-built Sessions in weeks 0–1 on material outside the Northstar build, including exports and a learning conversation) gates only B4. G1 at day 14. **The v0.5 gate:** two consecutive used weeks, checked by `ns metrics --gate`. After G1, building happens only in weeks with use (T3, replacing the 3× ratio, which would have fired on the v0 build itself). The E8 hand-run report is exempt.
5. **v0.5** (about 4 build sessions) holds the deferred work, each item behind a recorded trigger: export adapters; the maintainer spike and agent prep; the Codex parser; `ns context`; position-to-position cards and lint; ranking weights, load rules and re-entry; the vendor-memory scan; the notes adapter. **v1** holds E10, E3 and its runner, revisit cards, backfill, critique and paste packs, `ns check`, the export bundle, and record and pattern excision.
6. **After approval**, §12 is extracted into `BUILD-v0.md` (≤250 lines) and the repo `CLAUDE.md` points build agents only at that file.

## Alternatives considered

- **v0.1's ten-session plan.** Twice its budget with no cut order.
- **Five sessions (scope-simplicity-1).** Would push CI and source excision out of v0, which three reviewers asked to keep, and would not separate out the same-day pack.
- **Hold all building until G0 (v0.1).** The archive is needed either way and logs are being deleted.
- **Keep the 3× build/use ratio.** Meaningless during the build; T3 keeps its intent.

## Consequences

- Jack's first payoff is on build day 2; the first Session on the tool follows B4.
- Overruns cut the least essential mechanism first, never a P3 field.
- Build agents follow one short spec.

## Deciding evidence or experiment

- G1 acceptance (DESIGN §12.1) and the B1–B6 acceptance tests.
- T3 and the v0.5 gate in `ns metrics --gate`.
