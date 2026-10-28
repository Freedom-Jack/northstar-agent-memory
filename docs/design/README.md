# Northstar design documents

> **Status 2026-10-25:** the current proposal is [`revision-2026-10-23/DESIGN.md`](revision-2026-10-23/DESIGN.md), version 3.2 of the three-job design (focus, memory, maintenance over one core), with its review page [`revision-2026-10-23/review.html`](revision-2026-10-23/review.html). The user approved it with changes twice on 2026-10-24 and answered a third round on 2026-10-25. Northstar is a memory and focus layer that works with the AIs the user already uses; ChatGPT's Dreaming memory system is the reference. The next step is the overview sketch round ([`revision-2026-10-23/overview-sketch-round.md`](revision-2026-10-23/overview-sketch-round.md)). Everything else in this folder is the earlier proposal of 2026-10-09, kept as a component library; DESIGN.md §12 says what is kept, replaced and dropped.
>
> **Status 2026-10-14:** this is an earlier proposal. The design is being re-explored and is not settled; start from [`docs/GOAL.md`](../GOAL.md) and [`docs/EXPLORATION.md`](../EXPLORATION.md).

This folder holds the design of Northstar. [`docs/GOAL.md`](../GOAL.md) overrides every document here.

**Status (2026-10-09):** the 2026-10-08 design passed design, adversarial review ([`REVIEW.md`](REVIEW.md)) and goal-fidelity checks. On 2026-10-09 it was revised after your comments on [`ARCHITECTURE.md`](ARCHITECTURE.md): five revision documents in [`revision-2026-10-09/`](revision-2026-10-09/) were integrated into ARCHITECTURE.md, with the fixes from an internal check of the same day, and [`CHANGES.md`](revision-2026-10-09/CHANGES.md) explains what changed (its §9 lists the check fixes). The revised design awaits your approval; the decisions we need from you are in ARCHITECTURE §14. Nothing is approved and nothing is built.

**Revision precedence:** where a document in `revision-2026-10-09/` conflicts with an older spec in `foundations/` or `components/`, the revision document wins until the specs are updated after approval. CHANGES.md §8 lists the superseded sections.

## Read order

1. [`../GOAL.md`](../GOAL.md) is the goal and your answers, including those of 2026-10-09. It is authoritative.
2. [`revision-2026-10-09/CHANGES.md`](revision-2026-10-09/CHANGES.md) (about 10 minutes): what the proposal now says for each of your comments 1–5, what changed and why; the unresolved questions and tradeoffs; the superseded spec sections.
3. [`ARCHITECTURE.md`](ARCHITECTURE.md) is **the approval document**: about 30 minutes for the approver's path (§0, §0.1, §13, §14), about 70 for everything.
   - "What changed on 2026-10-09" sits right after the status lines.
   - §0 is the one-page summary, by platform (Windows, iOS, Mac) and by product.
   - §14 lists the decisions we need from you.
   - Every other section links to the specs behind it.
4. For detail on one of your comments, read its revision document:
   - comment 1, [`platform-and-devices.md`](revision-2026-10-09/platform-and-devices.md);
   - comment 2, [`connector-strategy.md`](revision-2026-10-09/connector-strategy.md);
   - comments 3 and 4, [`knowledge-organization.md`](revision-2026-10-09/knowledge-organization.md) and [`personal-relevance.md`](revision-2026-10-09/personal-relevance.md), which share one interface and are best read together;
   - comment 5, [`benchmark-v0.md`](revision-2026-10-09/benchmark-v0.md).
5. [`REVIEW.md`](REVIEW.md) records the adversarial review of the 2026-10-08 design: every finding, how it was handled, and the questions it raised.
6. For more depth, read the older specs below, foundations first, then components. Where a revision document supersedes a section, read the revision document instead.

## Index

| Document | What it holds | Status |
|---|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | The integrated design and the decision page: what you get per platform and connector; core, Book, in-session focus, continuity, connectors, maintainer, platforms and devices, evaluation, build plan; decision register and resolved conflicts; top risks; the decisions we need from you (§14); goal-fidelity matrix | Revised 2026-10-09 after your comments; awaits your approval |
| [REVIEW.md](REVIEW.md) | The adversarial review of 2026-10-08: method, every finding with its verdict and disposition, rejected fixes, questions for you, smaller issues, and the earlier ARCHITECTURE fidelity fixes | Record of the 2026-10-08 design |
| **Revision of 2026-10-09** (wins over older specs where they conflict) | | |
| [revision-2026-10-09/CHANGES.md](revision-2026-10-09/CHANGES.md) | The concise explanation of the changes per comment; unresolved questions and tradeoffs (merged into DQ-13 to DQ-19 and DQ-1); where the five documents disagreed and how it was resolved (R17–R25); superseded spec sections; the check fixes | Revision proposal; awaits your approval with ARCHITECTURE.md |
| [revision-2026-10-09/platform-and-devices.md](revision-2026-10-09/platform-and-devices.md) | Comment 1: every Mac dependency and its Windows equivalent; what cannot exist on iOS; one core and many edges; "self-hosted now"; the verifier node; the Reader on every device; stage order Windows, iOS, Mac; facts W1–W24; spikes SP-PF | Revision proposal; awaits your approval with ARCHITECTURE.md |
| [revision-2026-10-09/connector-strategy.md](revision-2026-10-09/connector-strategy.md) | Comment 2: mechanisms rated by capability; what MCP achieves alone; where product-specific code is needed; shared engines and thin adapters; per product and platform; facts N1–N19; spikes CN-S | Revision proposal; awaits your approval with ARCHITECTURE.md |
| [revision-2026-10-09/knowledge-organization.md](revision-2026-10-09/knowledge-organization.md) | Comment 3: placement signals and ladder; subdivision and consolidation triggers; overviews from leaves only; stability; the relevance gate on structure; growth scenarios and measures | Revision proposal; awaits your approval with ARCHITECTURE.md |
| [revision-2026-10-09/personal-relevance.md](revision-2026-10-09/personal-relevance.md) | Comment 4: acts, anchors and roles; the lookup rule; what earns a page; what to learn; "Where you stand"; guardrails against profiles and sycophancy; relevance measures | Revision proposal; awaits your approval with ARCHITECTURE.md |
| [revision-2026-10-09/benchmark-v0.md](revision-2026-10-09/benchmark-v0.md) | Comment 5: the baseline-first benchmark: Phase B and Phase N, Part A (AI assistance) and Part B (your sessions, in one of three formats), thresholds, verdicts, cost; the fate of the older protocols | Revision proposal; awaits your approval with ARCHITECTURE.md |
| **Foundations** (binding inputs, except where superseded) | | |
| [foundations/SPINE.md](foundations/SPINE.md) | The shared skeleton: components C01–C23, connector contract and capability levels, entity model, invariants I1–I24, stores and single writers, topology, model runtime, repo layout, decisions SD-1–SD-38, risks, questions UQ-1–UQ-22, product facts P1–P37 | 2026-10-08; parts of §4, §5.2 and §7 superseded by the revision (CHANGES §8) |
| [foundations/TEXTBOOK.md](foundations/TEXTBOOK.md) | The human architecture: the Book's anatomy, attribution, what to learn, evolution, compile pipeline and validators, corrections, Reader, evaluation, questions Q1–Q7 | 2026-10-08; §4, §6, §7, §8, §10–§13 partly superseded by [PR], [KO] and [BM] (CHANGES §8) |
| [foundations/connector-claude-desktop-chat.md](foundations/connector-claude-desktop-chat.md) | Claude Desktop chat strategy by layer (L0 to L2), product facts, spikes CD-S | 2026-10-08; contract superseded by SPINE §4; spikes re-run on Windows (SP-PF-14) |
| [foundations/connector-chatgpt-desktop-chat.md](foundations/connector-chatgpt-desktop-chat.md) | ChatGPT Desktop chat strategy by layer, plan paths, write paths, spikes CS | 2026-10-08; contract superseded by SPINE §4; spikes re-run on Windows; the relay replaced by DQ-13's endpoint from the iOS stage |
| [foundations/desktop-observer-macos.md](foundations/desktop-observer-macos.md) | The optional macOS Accessibility observer: capture, visible injection, automation, terms, security, spikes DS | 2026-10-08; now the Mac backend of one observer core; use gated by DQ-1 |
| [foundations/textbook-A-learning-science.md](foundations/textbook-A-learning-science.md), [-B-knowledge-architecture](foundations/textbook-B-knowledge-architecture.md), [-C-reader-experience](foundations/textbook-C-reader-experience.md) | The three drafts that TEXTBOOK.md was synthesised from | Superseded; cited only for where an idea came from |
| **Components** (specs behind ARCHITECTURE.md) | | |
| [components/core-data-model.md](components/core-data-model.md) and [core-data-model.sql](components/core-data-model.sql) | Store schemas, 51 event types, invariant checks, tension resolution, excision, volume; the full portable DDL | 2026-10-08; index additions and event mapping per [PR], [KO] |
| [components/maintainer.md](components/maintainer.md) | Orchestrator, Apply, job catalog, verification L0–L6, quarantine, sentinels, budgets, fault injection, model runtime, the one cost model | 2026-10-08; new operations, jobs and faults per [KO], [PR]; verifier node and the late-spool fault per [PF] |
| [components/ai-in-session.md](components/ai-in-session.md) | In-session focus: session ledger, steward, Goal-Change Handler, Drift Checker, corrections, composer, restart | 2026-10-08; §6.5, §8.1 per [PR]; §11 per [BM] |
| [components/ai-continuity.md](components/ai-continuity.md) | Cross-session continuity: pack contract, goal router, seeding, re-explanation detector, delivery by level | 2026-10-08; §3 per [PR]; §11 per [BM] |
| [components/connectors-claude-code-and-codex.md](components/connectors-claude-code-and-codex.md) | Hook-tier connectors: hook client, hook maps, scope gate, turn origin, in-turn check, packaging | 2026-10-08; Windows launcher and surfaces per [CN], [PF]; hook-tier tool read scope per [PF] |
| [components/connectors-desktop-and-mcp.md](components/connectors-desktop-and-mcp.md) | The MCP tool contract, the widget, both desktop-chat connectors, the observer interface, install, the full level table | 2026-10-08; `win32`, remote connector and per-OS rows per [CN], [PF] |
| [components/platform-security-privacy.md](components/platform-security-privacy.md) | Processes, storage and backups, local auth, relay, cloud swap, scopes and egress, excision, threats | 2026-10-08; becomes the macOS adapter of OS ports per [PF]; RT-17 and the endpoint's own hostname per [PF] |
| [components/evaluation-and-build-plan.md](components/evaluation-and-build-plan.md) | Protocols and bars per success criterion, harness, consolidated spikes, stages, the prototype checklist | 2026-10-08; first evaluation and stage order replaced by [BM] and [PF] |

## Conventions

- **IDs.** IDs such as C01–C23, I1–I24, SD-n, RISK n and UQ-n are defined in SPINE. The revision adds RISK-PF, -CN, -KO, PR-n and -BM risks; spikes SP-PF, CN-S and BM-S; and resolutions R17–R25 (ARCHITECTURE §12.2, CHANGES §7).
- **User decisions.** ARCHITECTURE §14 groups the user questions as numbered DQs; each DQ heading names its source question IDs (SPINE UQ, TEXTBOOK Q, and the revision's PQ, CN-Q, Q-KO, Q-PR and BQ). DQ numbers are stable: DQ-8 is settled as HOW, DQ-12 is merged into DQ-3(d), and DQ-13 to DQ-19 are new on 2026-10-09.
- **Product facts.** "(Unv)" marks an unverified product fact and names the spike that settles it. Verified facts carry a source URL and the date checked (SPINE P1–P37; [PF] W1–W24; [CN] N1–N19; [BM]'s fact list).
- **Open conflicts.** ARCHITECTURE §12.2 records cross-document resolutions: R1–R16 are carried by the specs (REVIEW.md §9); R17–R25 are recorded in CHANGES §7 and reach the specs when they are updated after approval.
- **Evidence.** The evidence base is in [`../research/round2/`](../research/round2/). `docs/archive/` holds a rejected design and is never used.
- **No personal data and no device-specific security facts.** Every example is invented. Facts measured on your machines (disk encryption, management, which machine passes the verifier test, exact OS and app versions) are written by `northstar doctor` to the data root, never to the repo. Benchmark material on your real topics stays in a local bench folder. A CI check will enforce this ([EV] §6); nothing is built yet.

## Records of 2026-10-08

The full review record is [`REVIEW.md`](REVIEW.md). The README changes made then are kept below as a record.

| Finding | What changed here |
|---|---|
| CONS-12, CLR-12 | Stale counts removed; REVIEW.md added to the read order and the index, with status "Record" |
| CLR-10 | The reading-time claim names the approver's path |
| CLR-11 | DQ numbers stay stable; DQ-8 is settled as HOW (ARCHITECTURE §12.1) |
| CONS-12 | The "Open conflicts" convention says the specs carry the §12.2 resolutions (REVIEW.md §9) |
| SEC-6 | "No personal data" widened to "no device-specific security facts"; measured machine facts go to `northstar doctor` output in the data root |
| Final gate | Status lines; SPINE's product facts are P1–P37; the CI check for device facts is stated as future ("nothing is built yet") |
