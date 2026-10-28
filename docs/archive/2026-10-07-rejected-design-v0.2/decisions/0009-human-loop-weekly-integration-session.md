# 0009. Human loop: a timed weekly integration Session, held in a terminal

- **Status:** Proposed
- **Date:** 2026-10-07
- **Revised 2026-10-07 after review:** the Session runs in a terminal (the desktop app's terminal panel), not relayed through Claude Code chat (now rung R17); cards are built without any model; takeaway cards and a monthly review card are added; options are numbered with no preselected semantic answer and every card can be undone; a calendar file and a notification cue the slot, with prep run beforehand; ranking weights, self-adjusting load and re-entry move to v0.5; fresh-start is subsumed by the monthly review; catch trials are cut; G0 becomes two hand-built Sessions on non-Northstar material that gate only the runner; triggers are pause-aware. See `REVIEW.md` (engineering-5; human-4, -5, -6, -8, -10, -11; scope-simplicity-7, -8; problem-fit-1, -7, -8).

## Context

The payoff is in integration, which costs the person time [SYN §2.3]; abandonment is the PKM base rate [02]; queues of AI proposals train people to click "accept" [08]. D's timed weekly Session of recall, relate, due and close cards with no carry-over won over C's signing queue, and all judges asked for D's week-0 Wizard-of-Oz test. A weekly review is reportedly the first habit people drop [05].

The review found that relaying cards through chat could not support Enter defaults or single keys, added model latency to every prompt (40–60 round trips per Session), moved prep into the 20 minutes, and needed verification that was both vacuous and fragile. Nothing cued the slot, keys collided across adjacent prompts with no undo, and v0.1's G0 tested a novelty Session on Northstar material and passed on stated willingness.

## Decision

1. **The Session is the one scheduled human loop** (DESIGN §7.2): weekly at a fixed slot, a 20-minute timer as a hard cap (the current card finishes, then close), 8–10 cards in fixed segments: recall; due (sort unsorted chats, keep or void this week's in-flow decisions, the monthly review); relate; capture or **takeaway**; close (a note, then a 5-line "what changed this week").
2. **Fixed stems, numbered options, no preselected semantic answer**; Enter defaults only for bookkeeping. Every keystroke becomes a person event; each card's events are buffered with an undo.
3. **In a terminal.** Real keys, no latency, nothing to verify. Chat-mode Sessions are R17, triggered only if Jack skips Sessions because of the venue.
4. **Cue.** `ns setup` writes a calendar file; an hour before the slot the scheduled job archives, builds cards and posts one notification. A missed slot gets no follow-up. `ns pause <weeks>` stops every clock.
5. **No carry-over.** Unshown cards expire; a missed week never enlarges the next Session; `ns session --five` is a 5-minute floor. In v0, order is fixed segments, self-sourced before AI-sourced, newest first. Ranking weights, self-adjusting load and re-entry arrive in v0.5 behind triggers.
6. **Instrumentation without an audit posture.** Cards are timed and classed thinking or clerical; supports share and other measures stay in `ns metrics`, never on Jack's page. No catch trials.
7. **G0** (DESIGN §12.1): two hand-built Sessions in weeks 0 and 1, from material outside the Northstar build, including export conversations and a learning conversation. The weekly Session runner is built only if both are held at the slot within 25 minutes; otherwise B4 builds the runner-up configuration (DESIGN §12.3).
8. **Budget:** about 25 minutes a week of Session plus capture time, stop line 30; evaluation has its own budget (ADR-0014).

## Alternatives considered

- **Claude Code chat as the default venue (v0.1).** See Context. R17.
- **C's signing queue; E's in-flow confirmations as the main loop; B's Markdown deck.** Classifying AI output is a chore and trains rubber-stamping.
- **A daily ritual.** Doubles the cost; a split cadence is offered if Jack prefers.

## Consequences

- Understanding, including learned understanding, is built in Jack through recall, takeaway, relate and revise, and the record grows from Jack's words.
- The product depends on a habit. Mitigations: G0 before the runner, a cue, pause, in-flow decisions paying off between Sessions, and the degradation ladder (DESIGN §12.3).

## Deciding evidence or experiment

- **G0** gates the runner.
- **T1 and T2** (DESIGN §10.7): disuse and load triggers, pause-aware, with no threshold on 3–4 events.
- **The mechanism ledger** cut rules for takeaway cards and the monthly review.
