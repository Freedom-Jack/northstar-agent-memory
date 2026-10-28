# Judging the five proposals

*2026-10-07. This records how three judges scored proposals A–E (`docs/design/proposals/`) and how the lead architect chose the design in `DESIGN.md`.*

## 1. The proposals

| | Proposal | Lens | One-line thesis |
|---|---|---|---|
| A | Epistemic ledger | Rigor first | A bitemporal SQLite belief base that keeps proposition, attribution and stance as separate records, with typed changes. Rigor goes only where loss is permanent |
| B | Living pages | Legibility first | Git-tracked Markdown pages with Now, Digest and Log zones. The AI only proposes; a linter enforces the protocol |
| C | Thin layer | Baseline-first minimalism | A raw archive, a signed JSONL notebook, and a cited query-time "ask". No structure until a pre-registered probe fails |
| D | Integration ritual | Human loop first | A timed weekly Session in which Jack recalls, relates and revises in their own words. The AI is a clerk that never writes beliefs |
| E | Minutes | AI consumer first | An in-conversation clerk drafts quoted "minutes", which Jack confirms with two keys. Briefs are pushed by hooks |

## 2. Criteria

The judges scored C1–C9 on a 1–10 scale. The judges' output did not include labels for the criteria, so the labels below are reconstructed from their rationales:

| | Criterion |
|---|---|
| C1 | Serves the goal: coherent, evolving understanding *in the person*, across jobs J1–J9 |
| C2 | Epistemic correctness: attribution, stance, time, change types |
| C3 | Human sustainability: effort, fatigue, ownership, legibility |
| C4 | AI-side value and safety: packs, injection, sycophancy, privacy |
| C5 | Buildability: a v0 in about two part-time weeks, with no API key |
| C6 | Evaluability and falsifiability |
| C7 | Longevity and portability |
| C8 | Simplicity, measured by number of mechanisms |
| C9 | Graceful degradation when experiments come back negative |

## 3. Scores

### 3.1 Judge 1: user advocate

| | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 | C9 | Total |
|---|---|---|---|---|---|---|---|---|---|---|
| A | 7 | 10 | 5 | 8 | 4 | 9 | 7 | 3 | 6 | 59 |
| B | 8 | 8 | 7 | 7 | 5 | 7 | 9 | 5 | 8 | 64 |
| C | 6 | 7 | 7 | 8 | 9 | 9 | 8 | 9 | 9 | **72** |
| D | 9 | 8 | 7 | 7 | 7 | 8 | 8 | 6 | 8 | 68 |
| E | 6 | 8 | 7 | 9 | 5 | 9 | 7 | 5 | 7 | 63 |

### 3.2 Judge 2: principal engineer

| | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 | C9 | Total |
|---|---|---|---|---|---|---|---|---|---|---|
| A | 8 | 10 | 6 | 8 | 4 | 8 | 8 | 3 | 7 | 62 |
| B | 8 | 8 | 7 | 8 | 5 | 7 | 6 | 4 | 7 | 60 |
| C | 7 | 7 | 8 | 8 | 9 | 9 | 9 | 9 | 9 | **75** |
| D | 8 | 8 | 7 | 8 | 8 | 9 | 8 | 7 | 6 | 69 |
| E | 6 | 8 | 7 | 9 | 5 | 8 | 6 | 4 | 7 | 60 |

### 3.3 Judge 3: research scientist

| | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 | C9 | Total |
|---|---|---|---|---|---|---|---|---|---|---|
| A | 8 | 9 | 6 | 8 | 5 | 8 | 8 | 4 | 7 | 63 |
| B | 8 | 8 | 8 | 8 | 5 | 7 | 7 | 5 | 7 | 63 |
| C | 6 | 6 | 8 | 9 | 9 | 9 | 9 | 9 | 9 | **74** |
| D | 8 | 8 | 6 | 8 | 8 | 8 | 8 | 7 | 6 | 67 |
| E | 7 | 8 | 7 | 9 | 6 | 8 | 7 | 6 | 7 | 65 |

### 3.4 Averages across judges

| | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 | C9 | Mean | Mean total |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 7.67 | **9.67** | 5.67 | 8.00 | 4.33 | 8.33 | 7.67 | 3.33 | 6.67 | 6.82 | 61.3 |
| B | 8.00 | 8.00 | 7.33 | 7.67 | 5.00 | 7.00 | 7.33 | 4.67 | 7.33 | 6.93 | 62.3 |
| C | 6.33 | 6.67 | **7.67** | 8.33 | **9.00** | **9.00** | **8.67** | **9.00** | **9.00** | **8.19** | **73.7** |
| D | **8.33** | 8.00 | 6.67 | 7.67 | 7.67 | 8.33 | 8.00 | 6.67 | 6.67 | 7.56 | 68.0 |
| E | 6.33 | 8.00 | 7.00 | **9.00** | 5.33 | 8.33 | 6.67 | 5.00 | 7.00 | 6.96 | 62.7 |

**The pattern.**
- Every judge ranked **C first and D second on total**, including the judge who recommended D as the base.
- C's lead comes from the properties that are hardest to retrofit: buildability, longevity, simplicity and degradation.
- C's weaknesses are C1 and C2: coherence lives in model output, and some non-recoverable fields are missing.
- On exactly those two criteria, D (C1) and A (C2) lead.
- E leads on the AI surface (C4).
- B sits in the middle on almost everything and leads on nothing on average. It is the most legible design, but legibility comes at a high engineering cost.

## 4. What each judge recommended

### 4.1 Judge 1 (user advocate): base D, with major changes

**Why D.** D is the only proposal whose core loop makes Jack do the integrating:
- unaided recall before the record is revealed;
- relating new material to their positions, in their own words;
- revisiting decisions before seeing the frozen record.

D also reaches zero false endorsement by construction, carries no backlog by design, and tests its riskiest assumption in week 0 at almost no cost.

**Required changes:**
- Cut v0 down to C's thin core.
- Hold Sessions in Claude Code chat, verified against the transcript.
- Add E's in-flow decision capture, so the AI-side payoff does not depend on Jack attending Sessions.
- Leave positions out of the default pack.
- Add B's edit-then-classify for one Markdown section per question that Jack owns.
- Add A's split between correcting the record and revising a belief.

**Runner-up.** C, with D's own-words and recall cards grafted onto it.

### 4.2 Judge 2 (principal engineer): base C, with major changes

**Why C.**
- It is the only v0 a part-time builder can credibly ship in two weeks with no API key: stdlib only, about 3–4K lines, one LLM step behind an agent-mode job protocol, and no unsolved research problem on the critical path.
- It has the best longevity: two plain JSONL ledgers kept out of git, so excision does not require rewriting history.
- It gets the most urgent fact right: logs are being pruned, so archive first.

**Required changes:**
- A's `held_from` qualifier and decision integrity grade.
- The as-of fixture and excision in v0.
- E's transcript-verified authorship and wording tier.
- B's "no new exposure" provider policy and quotes cut by code.
- D's Wizard-of-Oz week 0, use gate and plain-journal (B5) baseline.
- Deterministic question pages.

### 4.3 Judge 3 (research scientist): base C, with major epistemic changes

**Why C.** It is the best experimental platform:
- learning from real data within days;
- a pre-registered trigger for every addition to the structure;
- an A0 no-memory arm, a check on the LLM judge, catch trials, and an audit of signed entries.

The corpus on disk is two days of building Northstar, so cheap, adaptable structure is the rational bet.

**Required changes.** C's ladder rule ("build only when a probe fails") cannot detect the absence of data that was never recorded. **A's recoverability principle must therefore exempt the non-recoverable fields from the ladder**:
- change type, including record correction;
- the because-line;
- `held_from` and its qualifier;
- the integrity grade;
- receipts;
- frozen expectations.

Plus D's recall-before-reveal and B5 baseline, E's two-key confirmation and randomized pack trial, and B's `missed:` lines.

### 4.4 Key grafts the judges converged on

These were recommended by two or more judges:

| Graft | From | Judges |
|---|---|---|
| Archive raw logs first (days 1–3) | C | 1, 2, 3 |
| Positions out of the default pack; decisions and rejected options in | C | 1, 2, 3 |
| Pre-registered ladder; ratchet; mechanism ledger with cut rules | C, B, A | 1, 2, 3 |
| Correction kept separate from revision; unanchored change-type question | A | 1, 2, 3 |
| `held_from` with a bound qualifier; decision integrity grade | A | 1, 2, 3 |
| As-of sandbox for backfill extraction | A | 1, 2, 3 |
| In-flow decision capture through a skill with no hooks; Jack types expectation and confidence | E | 1, 2, 3 |
| Authorship verified against the vendor transcript | E | 1, 2, 3 |
| Randomized cold-pack trial | E | 1, 2, 3 |
| `project:northstar` excluded from metrics | E | 1, 2, 3 |
| `wording_by` tier and ventriloquism index | E | 1, 2, 3 |
| No new exposure; work defaults to no LLM | B | 1, 2, 3 |
| Week-0 Wizard-of-Oz; use-gated build | D | 1, 2, 3 |
| B5 plain-journal baseline | D | 2, 3 |
| Recall before reveal | D | 1, 3 |
| Edit-then-classify | B | 1, 3 (judge 3 via `ns`, not files) |
| One-key reject reasons; `missed:` and "doesn't fit" lines | C, B | 1, 3 |

### 4.5 Fatal flaws named

| Proposal | Flaw | Named by |
|---|---|---|
| A | Proposition identity (unsolved, SYNTHESIS §6.3) sits on the v0 critical path, inside about 40 build-days. Stances are auto-applied from extraction before false endorsement has been measured | 1, 2, 3 |
| B | Editable Markdown as canonical makes append-only a lint convention. It needs a round-trip parser and a merge driver. Excision rewrites git history. The v0 plan assumed about 300 episodes, but about 12 exist | 1, 2, 3 |
| C | Coherence lives in model output, and Jack's acts are signing in a terminal. The ladder cannot protect data that was never recorded | 1, 3 |
| D | A single behavioral bet on the habit people drop first. If Sessions lapse, nothing is integrated. "≈0 false endorsement" holds only by definition, since a paraphrase of AI text would pass | 1, 2, 3 (conditional) |
| E | Undocumented hook and transcript behavior on the critical path. In-flow confirmations of AI-drafted wording are the most rubber-stamp-prone surface | 1, 2, 3 |

### 4.6 Where the judges disagreed

| Issue | Judge 1 | Judges 2 and 3 | Resolution in DESIGN.md |
|---|---|---|---|
| Base | D | C | C's architecture, with D's Session replacing C's review queue (§5 below) |
| Who writes positions | Own words only (D) | Jack signs drafts; wording tier recorded; own words for core items | Typed or verbatim-quoted by default. AI paraphrase only on request, and labelled. E9 decides (ADR-0005) |
| Human anchor | Questions (≤12) | Scope and chronology, with asks seeded on day 0 | Questions for Jack, scope for AI packs. E5 can demote questions |
| Cadence | Weekly Session | Daily for 14 days, then weekly (judge 3) | Weekly. Daily micro-review measures a different habit from the one under test (ADR-0009) |
| Raw retention for work | Archive raw; no LLM | Metadata only until Q6 (judge 2) | Metadata only until Q6 is answered. Q6 is a build gate |
| Tensions | Typed link with `held` | Tension as a question (C) | Tension as a question with a type and a `held` status (ADR-0008) |

## 5. Final call

**Base: C (Thin layer). One component is replaced wholesale: C's queue of AI proposals for Jack to sign becomes D's timed integration Session. Grafts come from A, E and B. Everything else is cut or put on the ladder.**

Six reasons:

1. **C wins where retrofits are expensive.** All three judges ranked it first. Its substrate is plain JSONL outside git, raw bytes are archived, the index is disposable, and the core is stdlib only. Its discipline (no rung without a trigger) is what keeps a single engineer building for their own use from turning the build into the hobby. Those properties cannot be bolted on later. C's two weaknesses can be fixed with bounded grafts.

2. **C1 is fixed by D's Session, as a module rather than a new architecture.** D's own substrate is almost identical to C's: JSONL canonical, not in git, a SQLite projection, agent-mode clerk jobs. So the Session drops in as a replacement for C's review loop. It writes the same records to the same ledger. The research is unusually clear that understanding forms through effortful, generative integration, not through reading fluent synthesis [01]. D is the only proposal whose core operation is that integration.

3. **The Session also suits the data that actually exists.** C's daily review of AI proposals would be nearly empty in weeks 1–2. Jack's own words in the agent logs total about 10K tokens, mostly about building Northstar. Recall and due cards need no logs, and capture cards need only a few. So the Session works on thin data, and C's queue does not.

4. **D's single point of failure is contained, not ignored.**
   - Week 0 tests the ritual before any code is written (G0).
   - E's in-flow decision capture fills the pack whether or not Sessions happen.
   - A written degradation ladder ends in C's own ritual-free loop: in-flow capture plus sign-on-use. That is a configuration change, not a rebuild.

5. **C2 is fixed by A's recoverability principle, which overrides C's ladder for six fields.**
   - The fields: change type (with "the record was wrong" kept out of the change feed), the because-line, `held_from` with its qualifier, the decision integrity grade, the frozen expectation and confidence, and receipts.
   - The cost is a few fields, not mechanisms.
   - A's machinery is rejected: proposition tables, auto-applied stances, credence intervals, 28 event types. A's critical path depended on an unsolved problem.

6. **The AI surface takes E's best ideas without E's coupling.**
   - Taken: skill-driven decision capture; Jack types the fields only Jack can supply; authorship verified against the transcript after the fact; a randomized cold-pack trial; provider-filtered, default-closed scopes.
   - Kept off the critical path: hooks. They are ladder rung R9.
   - Positions stay out of the default pack, because memory profiles raised agreement sycophancy by up to 45% [07]. E10 and the trial can overturn this.

**What was not averaged.**
- The human loop is D's alone. C's queue and daily micro-reviews are not kept alongside it.
- The substrate is C's alone. B's editable pages and A's SQLite canonical store are rejected.
- Capture timing is a batch weekly prep plus in-flow capture for decisions only. E's always-on clerk is rejected.
- Where evidence cannot decide, the choice is cheap to reverse and names its deciding experiment:
  - own words vs drafts: E9;
  - questions vs scope as the anchor: E5;
  - positions in the pack: E10 and the trial;
  - whether typed structure beats a plain journal: E3 against B5.

**Runner-up configuration.** If G0 or G2 shows that Jack will not sit Sessions, the system runs as "ledger without ritual": C's sign-on-use, plus E-style in-flow capture, plus a monthly 10-minute Session. The architecture does not change.
