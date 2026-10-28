# 0014. Evaluation: two powered tests, three triggers, a plain-journal baseline, and a small budget for Jack

- **Status:** Proposed
- **Date:** 2026-10-07
- **Revised 2026-10-07 after review:** the v0.1 plan is replaced. E3 compares the typed ledger with the same ledger rendered as an untyped journal, on about 100 probes generated from recorded events, with a cluster bootstrap, one statistic for both branches and a stated detectable effect; no outcome can remove P3 fields. Scripted E10 is the only AI-side decision test. An LLM judge from the same provider (different model) grades; Jack spot-checks. Three pause-aware triggers replace the kill list. The signature test, catch trials, E9, the live pack trial, the cross-family judge, B0/B3/B4 as decision arms, three repeats and week-0 probes are cut. Jack's evaluation time is capped at 2 hours, budgeted apart from the use stop line. The 3× build/use ratio becomes T3. See `REVIEW.md` (evaluation-1 to -14; human-1, -3, -10; scope-simplicity-3, -8, -11).

## Context

- **Designer, user and rater are one person;** satisfaction misleads [01][09].
- **The simple baseline may win** [03][07].
- **The builder's trap** is the named failure mode [SYN §2.2].
- The review showed v0.1's rule could not decide anything: about 28 decision probes give a minimal detectable effect near 17 points, so a true 10–15 point advantage was usually lost and the journal-collapse branch fired on noise. Gold from archive spans is impossible for current and forward probes and circular where possible. The arms saw different information. Jack's grading and labelling came to an estimated 15–25 hours outside any budget, and several kill criteria rested on 3–4 events.

## Decision

1. **Write-path CI, automatic** (DESIGN §10.1), including a provenance assertion on every person event and the 12-scenario fold fixture.
2. **Pre-registration.** `eval/PROTOCOL.md` is committed to git before data. Gold sources per category: generated from recorded events where both arms share the information; export spans for past state, after backfill. Jack writes about 10 stems in week 3; a script instantiates about 100 probes at week 8, including a J7 (learned understanding) category reported separately.
3. **E3, week 8:** NS against B5 = the same ledger rendered as an untyped dated journal plus the same search, at the same total token budget. Keep typed retrieval and views on the AI path if NS − B5 ≥ 10 points and the 95% lower bound is above 0; otherwise the simpler arm wins. With fewer than 60 probes, the test moves to week 12. **No outcome removes capture of P3 fields.** A0 filters probes; B2 is reported once.
4. **E10, week 6:** scripted prompts (about 30 where a rejected option is the natural answer, 30 contested) × {no pack, default, default plus the skill, plus positions}, exact McNemar, pre-registered consequences (DESIGN §10.6).
5. **Grading:** a same-provider judge on a different model, passing a ≥30-item planted-answer meta-evaluation. Its score stands; Jack spot-checks.
6. **Triggers** (DESIGN §10.7), paused weeks excluded: **T1** disuse → the next ladder rung; **T2** load (Session plus capture minutes) → fewer cards; **T3** a build session in a week without use → building pauses; an **attribution incident** pauses that capture path. **Coverage:** close-card notes with no home above 20% → revisit the kinds.
7. **Jack's evaluation budget:** ≤2 hours over 8 weeks, itemized and timed by `ns eval`, outside the use stop line.
8. **Anti-builder's-trap rules**, in the repo `CLAUDE.md`: `ns metrics --gate` before v0.5 work (two consecutive used weeks); T3; no rung without a trigger in `eval/ladder.md`; features unused for 2 weeks are removed; every mechanism has a cut rule (DESIGN §10.8).

## Alternatives considered

- **v0.1's six arms, three repeats, Jack as primary grader.** Underpowered, unequal information, and the evaluation itself would cause abandonment.
- **A cross-family judge.** Breaks egress (ADR-0016).
- **Catch trials, the signature test, E9.** Nothing to catch when Jack writes the text; a self-contradictory kill; a null at n=10 could not justify reversing own words.
- **A live cold-pack trial.** Underpowered.
- **[09]'s full multi-persona harness.** The harness would become the hobby.

## Consequences

- Jack spends about 2 hours on evaluation in 8 weeks.
- The project can stop honestly at week 4 or week 8 with a written record, and no single noisy event can kill it.
- Building cannot outrun use without the build agents noticing.

## Deciding evidence or experiment

This ADR defines the evidence for the others. Thresholds may be recalibrated once, after week 4, and only toward stricter values.
