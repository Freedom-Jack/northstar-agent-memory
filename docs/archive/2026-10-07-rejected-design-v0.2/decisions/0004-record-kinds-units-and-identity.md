# 0004. Record kinds, units and identity: four kinds on Jack's side, no proposition table

- **Status:** Proposed
- **Date:** 2026-10-07
- **Revised 2026-10-07 after review:** a Position also holds Jack's understanding of how something works; a Question may have `form: aim`; Notes are rewordable and retractable; Encounters are quoted spans from any speaker, including Jack's own observations; a position can sit on several questions; splits are two `supersede` links; the claim that random IDs cannot collide under merge is dropped. See `REVIEW.md` (problem-fit-1, -4, -5; epistemics-9, -12; engineering-2, -10).

## Context

The research tracks proposed four overlapping type systems, about 15 types in all [SYN T11], which is the rich-schema failure [02][04][05]. Proposals ranged from C's 4 kinds to A's 8 kinds plus 5 attitudes with minted propositions. Judges 2 and 3 called A's dependence on proposition identity a fatal flaw; SYNTHESIS §6.3 lists that problem as unsolved.

The review showed v0.1's four kinds were the right count but too narrowly defined: learned understanding had no home, goals were forced into short-lived questions, and notes were write-once fragments by SYN §1.1's own definition.

## Decision

**Jack's side: four kinds** (DESIGN §3.2).

| Kind | Holds |
|---|---|
| Question `Q-` | Something Jack is working out; `form: aim` for something Jack is working toward (exempt from the open cap and park prompts, reviewed monthly) |
| Position `P-` | Jack's stance **or understanding of how something works**, in Jack's words, on one or more questions, with how sure and `basis`. Holder is always Jack |
| Decision `D-` | Chosen, rejected with why and reconsider-if, reasons, basis, frozen expectation and confidence, `decided_at` with qualifier, revisit |
| Note `N-` | A free thought; rewordable and retractable; cited by `prompted_by` when it grows into a position |

**A tension is a Question** with `about` and a type (ADR-0008).

**Archive side.** Source, Message (with speaker), Episode. An **Encounter** `X-` is a quoted span from any speaker, frozen verbatim with speaker and lineage, created only when Jack relates it. Jack's own observations are encounters with `self:experience`.

**No proposition table.** Position merges proposition and stance because the holder is fixed. Code-cut verbatim anchors in an immutable archive keep a later proposition layer possible; `basis` captures the per-position origin that would otherwise be lost (ADR-0005).

**Identity.**
- Short random IDs (kind prefix plus 4 Crockford base32 characters), unique per machine. A future merge across machines renames colliding IDs and writes an alias (R16).
- Rewording keeps the ID; a change of meaning mints a new record linked by `supersede` (OBO P19 [06]).
- Events are ULIDs, blobs sha256, spans native ID plus quote plus sha256.
- A merge is a reversible `alias`; a split is two `supersede` links from one old record.

**Units.** The unit of update and citation is the record; the unit of reading is `now.md` and `ns show <id>`.

## Alternatives considered

- **A's Proposition / Attribution / Stance split.** Most correct, but rests on proposition identity. Rung R5.
- **A separate Understanding or Knowledge kind.** Unnecessary: understanding revises, conflicts and ages exactly like a stance, and a new kind would duplicate every flow.
- **A Goal kind (C's `aim`).** `form: aim` gives aims their lifecycle at the cost of one field; a kind with horizon and cadence is rung R2.
- **D's Prediction and Tension kinds; E's `rule` kind.** R3; tension-as-question; no instruction channel.
- **Sequential or hash-based IDs.** Sequential IDs collide under merge; hashes name text, not meaning.

## Consequences

- The brief's central scenario, learning how something works, has a path into the record (takeaway cards, ADR-0009).
- J6 is served by `basis`, lineage on encounters and an AI-only flag, not by full lineage counting.
- Merges and splits never move data.

## Deciding evidence or experiment

- **Coverage** (DESIGN §10.4): close-card notes with no home above 20% → revisit the kinds.
- **E1** "doesn't fit" (`doesnt-fit`) verdicts.
- **R2's trigger:** ≥5 aims and Jack reports question statuses don't fit them.
