# Architecture Decision Records

These ADRs record the major decisions in `docs/design/DESIGN.md` (Northstar design v0.2, reviewed, pending approval). How the base design was chosen is recorded in `docs/design/JUDGING.md`; the adversarial review of v0.1, with every finding and its disposition, is `docs/design/REVIEW.md`.

All ADRs are **Proposed** (2026-10-07). ADRs 0001–0014 were revised in place after the review, each with a "Revised 2026-10-07 after review" line; 0015 and 0016 are new. They become Accepted once Jack approves the design. Results from the gates (G0–G3) may later supersede them; the evidence that decides each one is named in the table and inside the ADR. ADRs cite DESIGN sections for thresholds rather than restating them.

| ADR | Decision | Deciding evidence |
|---|---|---|
| [0001](0001-framing-practice-around-a-commitment-ledger.md) | Northstar is a practice around a small record of what Jack holds (questions and aims, positions including learned understanding, decisions, notes), not a knowledge base. The base is C (thin layer), with D's Session replacing C's review queue. Scope and the bounded-integration trade are approved at Q0 | Q0; G0; coverage; E3 |
| [0002](0002-canonical-substrate-append-only-jsonl-outside-git.md) | Two append-only JSONL ledgers are canonical (`person`, `machine`), outside git. Reads never write or lock. Index, `now.md` and pack are disposable; derived state is never stored | Dead-tool test; replay at 10⁶ events |
| [0003](0003-archive-raw-agent-logs-first.md) | Archive agent logs first, including desktop scratch chats, with secrets redacted and tool payloads stubbed at ingest. Retention is decoupled from scope; work is ignored | B1 acceptance; Q6 |
| [0004](0004-record-kinds-units-and-identity.md) | Four kinds on Jack's side; a position can be understanding of how something works; a question can be an aim; encounters from any speaker. No proposition table. Short IDs, renamed on a future merge | Coverage; E1; R2 trigger |
| [0005](0005-attribution-authorship-and-wording.md) | Deterministic per-block speakers. Every text field is Jack's typed reply, a code-cut quote or a template. `basis` records where a view came from. Terminal Sessions; in-flow decisions verified by pulling the reply from the transcript. Explicit threat model | B1 speaker tests; week-4 audit; E12 |
| [0006](0006-time-model-record-held-valid.md) | `held_from` with a qualifier on every new position; normative fold rules; three-valued as-of; `last_confirmed`; `decided_at_q`; integrity computed | Fold fixture; history probes |
| [0007](0007-evolution-operations-and-who-applies-them.md) | Nothing semantic is auto-applied. The change question: my view changed / the world changed / the record was wrong / not sure. Kind-agnostic correct, status and supersede ops; reinstatement; monthly consolidation by Jack | Cut rule; E6; E8 |
| [0008](0008-conflicts-as-held-open-questions.md) | A tension is a question with `about` and a type (`rebut`, `context`, `temporal`, `unknown`), held open on purpose if Jack wishes, never resolved automatically. Position-to-position cards in v0.5 | E6; R4 trigger |
| [0009](0009-human-loop-weekly-integration-session.md) | A timed weekly 20-minute terminal Session (recall, due, relate, capture or takeaway, close) with numbered keys, undo, a cue and no carry-over; a monthly review card | G0; T1, T2 |
| [0010](0010-capture-timing-weekly-prep-plus-in-flow-decisions.md) | Deterministic weekly cards in v0; agent prep in v0.5; in-flow capture for decisions only, with a pull protocol and caps; backfill sandboxed and seeded by question; no hooks | E1; E11; E12 |
| [0011](0011-llm-access-agent-as-maintainer.md) | v0 needs no model. From v0.5, a `tools: Read` maintainer subagent behind one job protocol; an optional API backend (default `claude-opus-5-5`) | v0.5 trigger and spike; golden set |
| [0012](0012-ai-pack-decisions-not-positions.md) | The pack holds decisions, rejected options, views no longer held, open questions and aims, and a title index, verbatim; imported through parent-folder `CLAUDE.md`, not globally; positions on demand under a fetch rule | B2 spikes; E10 |
| [0013](0013-privacy-scopes-and-excision.md) | Scopes `ignore`, `private`, `unsorted`, `personal`, most restrictive wins; work ignored until opted in; source excision verified through the decode path | Q6; CI |
| [0014](0014-evaluation-decision-rule-and-build-gates.md) | E3 (typed ledger against the same ledger as a journal, ~100 generated probes) and scripted E10; three pause-aware triggers; an LLM judge; ≤2 hours of Jack's time | Defines the evidence for the others |
| [0015](0015-v0-cut-line-build-order-and-gates.md) | v0 is six build sessions with a critical path, a cut order and a never-cut list; G0 gates only the Session runner; the v0.5 gate and T3 replace the build/use ratio | G1; `ns metrics --gate` |
| [0016](0016-egress-control-origin-account-and-scope-policy.md) | Archive text goes only to the account it came from; Jack's records follow a per-scope policy; one `egress.allowed` choke point. Replaces "no new exposure" | Q5; Q6; CI egress fixtures |

**Format.** Each ADR has Title, Status, Date, a revision or origin line, Context, Decision, Alternatives considered, Consequences, and Deciding evidence or experiment.

**Changing a decision.** Before approval, Proposed ADRs are revised in place with a dated line. After approval, add a new ADR that supersedes the old one; do not edit an Accepted ADR in place.
