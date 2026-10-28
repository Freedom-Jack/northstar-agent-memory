# Northstar design review (2026-10-08)

**Status:** the record of the adversarial review of the design set, and the plan for revising it. Written 2026-10-08. Nothing is approved and nothing is built.

**Authority:** [GOAL.md](../GOAL.md) overrides this record. Every change below is a HOW change. Where a fix would touch the WHAT (GOAL §3, §4, §6), it became a question for you (§8), not a change.

**Scope:** [ARCHITECTURE.md](ARCHITECTURE.md), [README.md](README.md), the five foundations in `foundations/` and the eight component specs in `components/`. Evidence is `docs/research/round2/`. The rejected design in `docs/archive/` was not read or used.

---

## 1. Purpose

The review had two jobs:
- find where the design would fail the goal, break under real products, or mislead you at approval;
- turn each surviving finding into an exact change, or into a question for you when only you can decide.

---

## 2. Method

**Eight lenses.** Each lens read the whole design set with one question in mind.

| Code | Lens | Question asked |
|---|---|---|
| FEAS | Product feasibility | Do the vendor products behave as the design assumes? Checked against official pages on 2026-10-08 |
| ROB (MR-) | Maintainer robustness | Does maintenance stay correct, and does every hold have an exit, when one agent loses focus? |
| SEC | Security and privacy | Can an attacker, a confused agent or a leak break authority, privacy or "local now"? |
| AIS (AIE-) | AI side | Do in-session focus and continuity work as claimed, equally, without over-steering? |
| BOOK | Human side | Will the Book read like a textbook and help you understand and remember, from day 1? |
| BUILD (CPLX-) | Build and complexity | Can it be built, run on a laptop and evaluated in the time stated? |
| CONS | Cross-document consistency | Do the specs agree with each other and with ARCHITECTURE's resolutions? |
| CLAR (CLR-) | Clarity for approval | Can you approve ARCHITECTURE.md knowing what you are approving? |

**Independent refutation.** A separate skeptic tried to refute every finding. The skeptic re-read the cited sections and re-checked product claims against official sources (Appendix B). Each finding got a verdict (confirmed, partly, refuted), a severity after verification, and a judgment on whether the proposed fix was right.

**Triage (this record).** Findings that describe the same defect were merged. Each finding then got one disposition:
- **Fix:** the proposed fix is adopted, with the skeptic's corrections.
- **Fix differently:** the defect is real but the proposed fix was wrong or too broad; §6 says why and what is done instead.
- **Question:** the fix would change the WHAT; it goes to you (§8). Some findings are "Fix + question": the HOW part is fixed and the WHAT part is asked.

**Smaller issues.** Each lens also listed unverified one-liners. They are in §10, each with a disposition. Those adopted were spot-checked against the files first.

---

## 3. Results at a glance

| Lens | Findings | Critical | Major | Minor | Confirmed | Partly | Refuted |
|---|---|---|---|---|---|---|---|
| FEAS | 7 | 0 | 2 | 5 | 2 | 5 | 0 |
| ROB | 12 | 0 | 7 | 5 | 4 | 8 | 0 |
| SEC | 12 | 0 | 9 | 3 | 5 | 7 | 0 |
| AIS | 12 | 0 | 3 | 9 | 2 | 10 | 0 |
| BOOK | 11 | 1 | 3 | 7 | 1 | 10 | 0 |
| BUILD | 11 | 0 | 4 | 7 | 1 | 10 | 0 |
| CONS | 12 | 0 | 1 | 11 | 3 | 9 | 0 |
| CLAR | 12 | 0 | 4 | 8 | 3 | 9 | 0 |
| **Total** | **89** | **1** | **33** | **55** | **21** | **68** | **0** |

Severity is after verification. Ten findings were rated critical by their lens. After verification one stays critical (BOOK-2), eight became major (MR-1, MR-2, SEC-1, AIE-1, AIE-2, BOOK-1, CPLX-1, CLR-2) and one minor (CLR-1).

**Dispositions:** 63 Fix, 18 Fix differently, 8 Fix + question. No finding was dropped.

**What matters most.**
1. **The per-turn tool was not honestly read-only** (FEAS-1, SEC-7). Decided: No, as specified. It becomes stateless. You are told the cost in DQ-4(ii).
2. **A desktop chat's last reply was never captured** (BOOK-2, critical). A closing call, longer reported explanations and a code-computed R14 fix it, if spikes pass.
3. **Hook-tier authority failed open** when the transcript reader broke (MR-4, SEC-3). It now fails closed and can be revoked.
4. **Omission, the commonest real error, had no production measure** (MR-1), and **audits were confirmed by the verifier that passed the error** (MR-2). Both now have detectors and tie-breaks by another route.
5. **A prompt-injected coding agent running as you was out of scope** (SEC-1), and stored text reached tool-using agents verbatim (SEC-4). Destructive commands now need Touch ID or your password; one rendering rule covers every model-facing text; GOAL §5 is rated Partial, not Met.
6. **Device-specific security facts sit in the repo** (SEC-6, CONS-6). They become generic conditionals; measured values move to local `northstar doctor` output. Residue in round-2 notes 10 and 11 was found and removed at the final gate (§9(b)).
7. **ARCHITECTURE.md was hard to approve from** (CLR-2, CLR-4, CLR-6, CLR-8). It gains plain per-app summaries, a glossary, concrete examples and rewritten decisions.

---

## 4. Decisions on questions the design left open

| Open question | Decision | Findings |
|---|---|---|
| Does the in-memory held-content cache keep `northstar_context` truthfully read-only? ([CX] §2.5, [GD] §6.2.2, ARCH §7) | **No.** Under OpenAI's and MCP's definitions, keeping content that changes later results, hashing it, minting session state or queueing work is not read-only. The `per_turn_readonly` profile becomes **stateless**: it computes the pin from stored items and the widget's own state, keeps no copy or hash of your message, writes nothing, and makes no model call. Content persists only through a declared write (the widget's record, a save carrying its content, a note). With that, the label is honest and the flag closes | FEAS-1, SEC-7, CONS-9 |
| SD-36: keep desktop-reported goals long-term? | **Keep** them as labelled `reported` items with no authority, with guards: provenance, rate caps, decay, injection-safe rendering, stricter confirmation and a fabrication sentinel. Whether a reported goal may also **steer** later chats, and whether reported constraints may persist, changes I22, so it goes to you in DQ-10 | SEC-5, AIE-2, CLR-3, CONS-2 |
| J10e automatic threshold recalibration | **Dropped for the prototype.** Thresholds change only through committed, golden-gated bundles at stage gates (I19). This removes the one-way ratchet | CPLX-8, MR-1 |
| Stage order | **Stage 0 splits into 0a** (2–3 weeks: account spikes on a throwaway server, SP-1, SP-2, S10 screening) **and 0b** (6–7 weeks: a thin vertical slice on Claude Code plus the SDK fixture). Totals unchanged | CPLX-2, CPLX-3 |
| Recalibration | One pre-registered pilot and one recalibration **per cell family**, each before that family's main data | CPLX-7 |
| Ten SQLite files | **Kept.** Ledger-side idempotency (MR-3) closes the main crash seam. Postgres triggers and the Postgres CI matrix move to the cloud-adapter stage | CPLX-9, MR-3 |

---

## 5. Every finding and its disposition

**File codes:** ARCH ARCHITECTURE.md · README · SPINE · TB TEXTBOOK.md · CD connector-claude-desktop-chat.md · GD connector-chatgpt-desktop-chat.md · OBS desktop-observer-macos.md · CDM core-data-model.md · SQL core-data-model.sql · MT maintainer.md · IS ai-in-session.md · AC ai-continuity.md · HK connectors-claude-code-and-codex.md · CX connectors-desktop-and-mcp.md · PL platform-security-privacy.md · EV evaluation-and-build-plan.md · RES research/round2 notes · PYPROJECT the repo's pyproject.toml.

| ID | Lens | Sev. | Title | Verdict | Disposition | Files |
|---|---|---|---|---|---|---|
| FEAS-1 | FEAS | Major | Per-turn tool's held-content cache is not truthfully read-only | Confirmed | **Fix + question.** Stateless `per_turn_readonly`; C2 records the call's own arguments from tool-input; A saves by `save_chat` carrying content or a widget click; arm and routing ride the echoed tag; DQ-4(ii) re-briefed with a "declared write" option. Merged with SEC-7, CONS-9 | CX, GD, SPINE, IS, AC, CDM, SQL, EV, ARCH |
| FEAS-2 | FEAS | Minor | ChatGPT routes: PK-1 and PK-2 are one route; official sources conflict on plans | Partly | **Fix differently** (§6). Merge PK-1/PK-2; record a conflict of official sources, not a read-only prior; CS1 on day 1; Sites check in Stage 0 always; observer stays optional | GD, CX, SPINE, EV, ARCH |
| FEAS-3 | FEAS | Minor | ChatGPT plugin selection is per message and gated by relevance | Partly | **Fix + question.** "Per message" wording; CS1 scripted tool-list turn; CS5 splits "not offered" from "not called"; DQ-4(i) trigger includes `@` on every message | CX, GD, IS, EV, ARCH |
| FEAS-4 | FEAS | Major | ChatGPT permissions: Always allow needs a connected account; approvals reset on reload | Confirmed | **Fix.** OAuth tested as a CS1 arm before adoption; default-permission checks; per-app low-risk preferred; Northstar only advises; path A restated | GD, CX, PL, EV, ARCH |
| FEAS-5 | FEAS | Minor | Widget-context pushes gated on visibility; delivery never measured | Partly | **Fix.** Push on every host signal; best-effort timer; separate widget tag echoed by the model; delivery probe; tighter CD-S2 and CS4 rules. Merged with AIE-11 | CX, CD, GD, IS, SPINE, EV |
| FEAS-6 | FEAS | Minor | Claude boot line invites skips under Auto tool loading; Tool access is per conversation | Partly | **Fix.** New wording tested as a CD-S3 arm on desktop, web and mobile; Tool access corrected to per conversation; CD-S1 checks a per-connector setting | CD, CX, EV, ARCH |
| FEAS-7 | FEAS | Minor | No fallback if standalone `.mcpb` extensions are restricted | Partly | **Fix.** Named trigger; remote-connector fallback through the relay listener; spike only on synthetic data, when the trigger fires; needs relay consent | CD, CX, SPINE, ARCH |
| MR-1 | ROB | Major | Omission (missed updates, merges, duplicates) has no production bound | Partly | **Fix**, with the skeptic's changes: sampled update-omission probe, duplicate sentinel, canary margins, sequential test with published delay, episode-level coverage audit; omission trips re-route, never freeze J3 | MT, EV, CDM, ARCH |
| MR-2 | ROB | Major | Error budgets confirmed by the verifier that passed the error | Partly | **Fix.** Confirmer never the gating route; tie-break by V2 or a permitted remote family; probable-error budget; audited error per speaker family; sentinel #8 action defined; no two-rater latent-class model | MT, EV, ARCH |
| MR-3 | ROB | Major | Apply↔jobs protocol: DDL gaps, crash duplicates, no-op prompt-fix reruns, restore loses corrections | Partly | **Fix.** DDL epoch and states; lease reclaim; one `idem_key`; `applied_job` in the ledger; `synchronous=FULL` on jobs.db; durable journal for non-model ledger writers; ledger→jobs orphan check | MT, CDM, SQL, PL, SPINE |
| MR-4 | ROB | Major | Hook-tier authority fails open when the transcript reader breaks; never revoked | Confirmed | **Fix.** `confirmed_degraded`: steers live, no long-term authority until confirmed or templates re-certified; revocation on a later `not_confirmed`; sweep rule. Merged with SEC-3 | SPINE, HK, CDM, SQL, MT, IS, PL, ARCH |
| MR-5 | ROB | Major | Excision is not crash-safe; lexical closure misses paraphrases | Partly | **Fix.** Resumable saga with tombstone and needles written first; connection-scoped trigger bypass; lock lease; one haystack rule; provenance closure bounded to text-bearing derivations | CDM, SQL, MT, PL |
| MR-6 | ROB | Major | Steward and high-risk freeze exits cannot be met | Confirmed | **Fix.** Frozen or degraded primary runs in shadow; exits sized to volume; structural ops never sent to J11x; 7-day escalation with automatic re-freeze | MT, IS |
| MR-7 | ROB | Minor | Quarantine day-7 exit undefined; discards unaudited | Partly | **Fix.** Exit 4 by tier; discards recorded, sampled and fed to sentinels per speaker family; CDM aligned to `awaiting_verify`; DDL keys | MT, CDM, SQL |
| MR-8 | ROB | Minor | Rollback not hash-identical; misses omissions; never reaches live sessions | Partly | **Fix.** Canonical active-state projection; Book restored by compensating edition; bounded job closure; `items.retracted` to the session applier | MT, TB, CDM, SPINE, IS, AC, ARCH |
| MR-9 | ROB | Major | A worker-set `atomic_group` decides which ops apply together | Confirmed | **Fix.** Apply derives dependency closures in code; relation-endpoint check; an FK abort is a code fault | MT, CDM, SQL |
| MR-10 | ROB | Minor | Weekly consolidation (J8c) can be starved or discarded silently | Partly | **Fix differently** (§6). Per-op freshness, re-queue counter, no locks across batch waits, sentinels; truncate only modest overruns | MT, TB |
| MR-11 | ROB | Minor | Same-code replay cannot catch Apply bugs; event-type freeze can block repair | Partly | **Fix differently** (§6). Independent reference projector and Apply-mutant fault F22; freeze the producing job type, not the event type | MT, CDM, EV |
| MR-12 | ROB | Minor | Audit-undone tension resolutions flip daily and end unflagged | Confirmed | **Fix.** Audit dissent is a resolution input; an undone resolution becomes contested with a question and recheck date | CDM, MT, ARCH |
| SEC-1 | SEC | Major | A prompt-injected coding agent running as you is out of scope | Partly | **Fix**, ranked: Touch ID or password for destructive and policy commands; threat T14; RT-17; file deny rules at install; service-account separation as a spiked option; GOAL §5 rated Partial | PL, HK, SPINE, EV, ARCH |
| SEC-2 | SEC | Major | Chat corrections gain I21 on any substring of a user turn | Partly | **Fix**, without the 6-word minimum: outside paste ranges; target delivered or named; independent entailment check; at most 3 a session; listed with undo | TB, HK, CX, PL, ARCH |
| SEC-3 | SEC | Major | Hook-tier authority fails open for pastes, agent messages and reader outages | Confirmed | **Fix**, merged with MR-4, plus: self-started classification while agent tasks are pending; per-segment paste heuristics for every authority kind (a URL alone does not demote); overlap sentinel | HK, IS, SPINE, MT |
| SEC-4 | SEC | Major | Captured text re-delivered verbatim to tool-using agents; labels the only defence | Confirmed | **Fix differently** (§6). One rendering rule; third-person restatement and inert code blocks; flagged spans held back from auto-pushed channels only; taint by measured overlap; CK-10; agentic red-team payloads | AC, IS, TB, PL, HK, CX, ARCH |
| SEC-5 | SEC | Minor | SD-36: keep reported goals, with guards | Partly | **Fix differently** (§6). Keep SD-36; adopt G2, G4, G5, G6 and the sentinel; narrow G1 and G3. Merged with AIE-2 | AC, SPINE, TB, ARCH |
| SEC-6 | SEC | Major | Device-specific security and account facts in the repo | Confirmed | **Fix.** Generic conditionals; measured values to local `doctor` output; README corrected; targeted lint. Merged with CONS-6 and carried task (b) | SPINE, PL, OBS, CD, GD, HK, MT, EV, CDM, ARCH, README, RES, PYPROJECT |
| SEC-7 | SEC | Major | Held-content cache sends turn text off the Mac and persists it | Partly | **Fix differently** (§6), merged into FEAS-1: stateless, not a kept cache; no model call on unrecorded turns; content-free records; DQ-4(ii) reworded; `openWorldHint` stays false | CX, GD, SPINE, ARCH |
| SEC-8 | SEC | Major | Excision misses the hook pin cache; report omits vendor-transcript copies | Confirmed | **Fix.** Pin cache registered, purged and expired; fail-closed excision epoch check; one haystack rule; delivered-session list in the report | HK, PL, CDM, SPINE |
| SEC-9 | SEC | Major | ARCH misdescribes what crosses the relay; vendor choice settled as HOW | Confirmed | **Fix + question.** DQ-4(iii) lists exactly what crosses under each option; the vendor choice moves from R16 into DQ-4(iii); Option B carries only OpenAI-held items by default | ARCH, PL, SPINE, CX |
| SEC-10 | SEC | Major | No write or call budgets on model-callable tools | Partly | **Fix.** Per-credential and per-session budgets; intake de-duplication on local embeddings; honest over-budget line; per-connector spend share; fault F23 | PL, CX, MT, EV, HK |
| SEC-11 | SEC | Minor | Reader authority trusts any click in the everyday browser profile | Partly | **Fix**, cheap parts: dedicated host and host-only cookie; correction rate cap; state line with undo; step-up for bulk changes; separate cookie jar as a spike | PL, TB, CX |
| SEC-12 | SEC | Minor | Hook and MCP processes share one `verbatim_live` credential | Partly | **Fix.** Per-channel fidelity ceiling in C04; split credentials as defence in depth; ignore a model-supplied speaker only on the hook-tier MCP credential | PL, HK, CX |
| AIE-1 | AIS | Major | Corrections ignore your current turn (reversals, reopenings, self-corrections) | Partly | **Fix**, with the skeptic's changes: item-level Goal-Change Handler output; tier 2 may overrule tier 0; grounded self-corrections become contested; correction age from verdict time | IS, HK, AC, ARCH |
| AIE-2 | AIS | Major | Reported desktop goals not delivered as goals; constraints uncovered | Partly | **Fix + question.** Neutral wording, larger slot, new EV probe adopted; steering at reported strength and long-term reported constraints amend I22, so they go to DQ-10 | AC, IS, SPINE, TB, EV, ARCH |
| AIE-3 | AIS | Minor | AI-established items get weaker protection than user ones | Partly | **Fix differently** (§6). Only a user-accepted seeded AI conclusion keeps High; report by speaker and vendor; speaker-blind severity as an ablation arm | AC, IS, EV |
| AIE-4 | AIS | Major | Coding-agent tool actions unchecked; one pin per long agentic turn | Confirmed | **Fix.** `tool_action` observations; tier-0 diff checks; PostToolUse feedback; mid-turn pin refresh within the cumulative budget; edit-level probes | IS, HK, EV, SPINE, ARCH |
| AIE-5 | AIS | Minor | A mid-chat return to an earlier goal gets no continuity | Partly | **Fix.** Router runs on a confident goal change toward a goal not on the stack; goal section delivered and seeded; a "mid-chat switch" detector cell | IS, AC, EV, ARCH |
| AIE-6 | AIS | Minor | Seeds over-steer: off-route constraints, embedding-only guard hits | Partly | **Fix.** No tier-1-only guard corrections; tighter caps; SP-AC-7 becomes a bar; off-route rejected and disputed seeds demoted; constraints sharing the session's context keep severity | AC, EV |
| AIE-7 | AIS | Minor | Without a certified local judge, Claude sessions lose the brake and drift restart | Partly | **Fix.** Tier-0 counts as independent; continuations need tier-0 when no re-judge exists; label-free proxies; judge status per connector; drift judge certified separately | IS, MT, SPINE |
| AIE-8 | AIS | Minor | Per-turn call cost unbudgeted; nothing adapts when call rate falls | Partly | **Fix differently** (§6). Time-to-first-token measured; restart depth per connector from measured call rate; arguments not shrunk | EV, IS, CD, GD, CX, ARCH |
| AIE-9 | AIS | Minor | Northstar's own blocks pile up in context unmeasured | Partly | **Fix.** Cumulative-share metric and stale-block probe; "supersedes earlier blocks" in every header; `pin_delta` ablation; length trigger on total context | IS, AC, HK, CX, EV, ARCH |
| AIE-10 | AIS | Minor | Continuity evaluated with less depth than focus | Partly | **Fix.** Real-CLI protocol D-syn-C; SP-AC-7 bar; AI-said recall ≥ 80% within 5 points; a co-primary metric as a recorded exception | EV, AC, ARCH |
| AIE-11 | AIS | Minor | Widget-context delivery unobservable in production | Partly | **Fix**, merged with FEAS-5: delivered `true` on an echo, else `unknown`, never `false`; demotion threshold calibrated on S-R7 | CX, IS, SPINE, EV |
| AIE-12 | AIS | Minor | Old supersessions get no note while vendor memory may hold them | Confirmed | **Fix.** Supersession note for the latest superseded version said in a captured chat on a `vendor_memory_possible` connector; sentinel | AC, SPINE, EV |
| BOOK-1 | BOOK | Major | Cold start and growth are not designed | Partly | **Fix**, without the size-retry part: bootstrap edition; daily early editions; budget exemptions; "growing book" form; first-night promotion for strong signals; "New this week"; early checkpoints | TB, MT, EV, ARCH |
| BOOK-2 | BOOK | Critical | Desktop L0 never captures a chat's final reply; R14 cannot fill pages | Confirmed | **Fix.** Closing report call (spiked); reported explanation body ≤ 1,500 chars; R14 flag computed in code; content-parity check; final-reply sentinel; ARCH no longer calls R14 sufficient. Merged with CONS-4 and part of CLR-2 | CX, CD, GD, IS, MT, CDM, TB, EV, SPINE, ARCH |
| BOOK-3 | BOOK | Major | Page anatomy cannot be filled from one-leaf evidence | Partly | **Fix differently** (§6). One segment sized to its leaves; one quoted reuse allowed; question-only concepts to question pages; redundancy validator V15; verbatim body only as an ablation | TB, EV |
| BOOK-4 | BOOK | Minor | Entailment false rejects unbounded | Partly | **Fix differently** (§6). True-accept bar stratified by sentence type; re-draft before drop with the same certified verifier; survival sentinels | TB, MT, EV |
| BOOK-5 | BOOK | Minor | Evaluation cannot catch a correct but useless Book | Partly | **Fix.** Questions from gold leaves; a BK0 bar; textbook sections as a style floor only; explained coverage; few structural bars; growth checkpoints; desktop-only persona | TB, EV, ARCH |
| BOOK-6 | BOOK | Minor | Explanation segments have no producer | Partly | **Fix.** Segmenting is a code step by J3 kind tags with persisted sub-topic IDs and an order rule | TB |
| BOOK-7 | BOOK | Major | V4 bans product names and reporting verbs; V8 bans formulas | Partly | **Fix differently** (§6). Ban registry names as speakers of claims, whoever is cited; keep generic agent nouns; allow names and short formulas that occur in a cited leaf | TB, CDM |
| BOOK-8 | BOOK | Minor | Frozen wording has no quality path; reuse makes patchwork paragraphs | Partly | **Fix.** A staged, labelled "reworded" printing under I19; T-STAB redefined; V12 extended to connectives; paragraph redraft when neighbours change | TB, EV, ARCH |
| BOOK-9 | BOOK | Minor | Chips flood desktop-heavy pages | Partly | **Fix.** Block-level fidelity note; sentence chips for exceptions; BK6 on a desktop-only persona | TB, EV |
| BOOK-10 | BOOK | Minor | What to learn fills with reflexive offers | Partly | **Fix differently** (§6). Offer vs learning-suggestion tags; `ready` rule; breadth as a ranking preference with a fill fallback | TB, MT, EV |
| BOOK-11 | BOOK | Minor | Frozen numbers are not frozen while the Book grows | Partly | **Fix differently** (§6). Insertion numbers at chapter and part level; renumbering counted in the churn budget; number survival in the landmark bar | TB, EV |
| CPLX-1 | BUILD | Major | The single local model slot is oversubscribed | Partly | **Fix differently** (§6). Per-role load model incl. drift re-judge, tested in Stage 0; co-resident embedder; re-judge priority; one V1 chosen by S10; async Claude judgments directly on V1 | MT, IS, SPINE, EV, ARCH |
| CPLX-2 | BUILD | Minor | The deciding spikes run after the core is built | Partly | **Fix.** Track A sprint in weeks 1–2 beside track L on a throwaway server; DQ answers asked as spikes fail | EV, ARCH |
| CPLX-3 | BUILD | Minor | Stage 0 overloaded; labour not estimated | Partly | **Fix.** Stage 0a and 0b; labelling and typing hours on their own line; recorded as a departure | EV, SPINE, ARCH |
| CPLX-4 | BUILD | Minor | S10 is huge and tied to hardware DQ-5 may change | Partly | **Fix.** Screen then confirm; failure-only early stopping; R12 as development mode; hardware floor in DQ-5 | MT, EV, ARCH |
| CPLX-5 | BUILD | Major | A "No" to DQ-3(a) (Profile D) is not shown feasible | Partly | **Fix + question.** DQ-3(a) asked now with estimated effects; Profile D capacity spike in Stage 0; degradations listed as risks. Merged with CLR-4 | SPINE, MT, EV, ARCH |
| CPLX-6 | BUILD | Major | Eval and test runs assume live calls the laptop cannot supply | Partly | **Fix.** Replay-first; fault matrix at stage gates with a nightly smoke subset; B-sim state in code; compute budget pre-registered. A hosted third-vendor key is not adopted | EV, MT |
| CPLX-7 | BUILD | Major | The single recalibration is spent before the levers exist | Confirmed | **Fix.** One pilot and one recalibration per cell family; Stage 0 harness smoke pilot | EV, ARCH |
| CPLX-8 | BUILD | Minor | Control loops lack precedence; J10e ratchets; no layer ablations | Partly | **Fix.** Controller registry with precedence; J10e dropped for the prototype; HOW-layer ablations | MT, TB, EV |
| CPLX-9 | BUILD | Minor | Ten SQLite files without cross-file atomicity | Partly | **Fix differently** (§6). No merge; ledger-side idempotency; Postgres triggers and CI deferred to the cloud-adapter stage | SPINE, CDM, PL, EV, ARCH |
| CPLX-10 | BUILD | Minor | No agent-runnable test loop for the desktop connectors | Partly | **Fix.** Host emulator from traces of sanctioned spikes; fixed in-app checkpoints; text-free self-test record | EV, OBS, CX |
| CPLX-11 | BUILD | Minor | Native dependencies missing from SP-1; modeld tied to Python 3.14 | Partly | **Fix.** Packages added to SP-1; separate modeld interpreter only if SP-1 finds a gap; stdlib-only hook client measured | SPINE, EV, MT |
| CONS-1 | CONS | Minor | Window close has no event; `session.ended` has two meanings | Partly | **Fix**, without the size cap: internal `window.closed` event; `session.ended` for the lifecycle only | SPINE, IS, MT |
| CONS-2 | CONS | Minor | A yes to DQ-10 makes goal packs fail CK-3 | Partly | **Fix.** Slot 2 and CK-3 test recorded authority; labelled click-confirmed lines; Q6-on persona | AC, IS, TB, EV |
| CONS-3 | CONS | Minor | R13 not in the specs; no input for cache-held sessions | Partly | **Fix.** R13 propagated; with FEAS-1 there are no cache-held sessions; path B reported "no audit" | IS, MT, SPINE |
| CONS-4 | CONS | Minor | R14 not in the specs; a model would set a promotion input | Partly | **Fix**, merged with BOOK-2: flag computed in C08; R14 decision re-cited to A12/CS6 | TB, MT, CDM, CX, EV |
| CONS-5 | CONS | Minor | Default spend cap below design cost; hard cap undefined | Partly | **Fix**, merged with CLR-9: one base; hard-cap behaviour; defer, never skip; projected-cost sentinel; DQ-11 table | MT, SPINE, ARCH |
| CONS-6 | CONS | Major | Device facts still in the repo | Confirmed | **Fix**, merged into SEC-6 | as SEC-6 |
| CONS-7 | CONS | Minor | R12 and R15 exist only in ARCHITECTURE | Partly | **Fix** (carried task a) | MT, SPINE, EV, TB, HK, IS |
| CONS-8 | CONS | Minor | DQ-8 default differs from SPINE UQ-7 | Confirmed | **Fix.** UQ-7 working assumption: not offered until answered | SPINE |
| CONS-9 | CONS | Minor | `persist_policy` has no producer | Partly | **Fix**, with FEAS-1: C04 derives `full`, `none` or `on_write` from `capture_mode`; per-turn trigger | CDM, SQL, SPINE, IS, AC, CX |
| CONS-10 | CONS | Minor | Landmark-weight inputs have no owner | Confirmed | **Fix.** Open counter in reader.db; derived-only `landmark_signals` C17→C16 | TB, SPINE, CDM, SQL |
| CONS-11 | CONS | Minor | R16 not propagated | Partly | **Fix** (carried task a): relabel as settled HOW with override | SPINE, TB |
| CONS-12 | CONS | Minor | README misstates decision and risk counts | Partly | **Fix**, merged with CLR-12 | README |
| CLR-1 | CLAR | Minor | Claude Desktop can also land in the save-or-nothing choice | Partly | **Fix + question.** DQ-4(ii) covers either desktop app | ARCH, CX, SPINE |
| CLR-2 | CLAR | Major | §0 overstates desktop capture and delivery | Partly | **Fix.** Plain per-app summaries; attribution claim qualified; terms defined; last-reply loss stated | ARCH |
| CLR-3 | CLAR | Minor | What happens to desktop-stated goals is not said plainly | Partly | **Fix + question**, folded into the DQ-10 rewrite and a §0 sentence | ARCH |
| CLR-4 | CLAR | Major | DQ-3(a) gives only the Book consequence of "No" | Confirmed | **Fix + question**, merged with CPLX-5 | ARCH, SPINE |
| CLR-5 | CLAR | Minor | The "Touches the goal" tag is inconsistent | Partly | **Fix differently** (§6). Tag DQ-3(b); not DQ-1(a) or DQ-5(b); lists in §0 and §15 match §14 | ARCH |
| CLR-6 | CLAR | Major | §0 and §14 need internal IDs decoded | Confirmed | **Fix.** §0.1 glossary; plain words first; terms defined, not renamed | ARCH |
| CLR-7 | CLAR | Minor | Label collisions (L0–L6, V1, C1/C2, A, bare §n) | Partly | **Fix.** "GOAL §n" prefix; "the local verifier"; ARCH calls verification tiers "checks 0–6"; connector layer names kept | ARCH |
| CLR-8 | CLAR | Major | The textbook and AI side are not shown concretely | Partly | **Fix.** Filled explanation block; desktop variant; first-screen mock; example pin and pack; evidence column | ARCH, TB |
| CLR-9 | CLAR | Minor | The cost estimate and the recommended cap conflict | Partly | **Fix**, merged with CONS-5 | ARCH, MT |
| CLR-10 | CLAR | Minor | The 40-minute reading claim is unrealistic | Partly | **Fix differently** (§6). Approver's path keeps §13 and §15; changelog moved here | ARCH, README |
| CLR-11 | CLAR | Minor | §14 mixes settings with decisions; numbering | Partly | **Fix differently** (§6). Numbers kept stable; DQ-8 settled as HOW with override; DQ-11 under "Settings with defaults" | ARCH, README |
| CLR-12 | CLAR | Minor | README gives stale counts | Confirmed | **Fix**, merged with CONS-12 | README |

---

## 6. Fixed differently: what was not adopted, and why

| ID | Not adopted | Why | Done instead |
|---|---|---|---|
| FEAS-2 | "Personal plans get read/fetch at best" as the prior; the observer as a first-rank ChatGPT route | The official developer guide says custom servers support read and write tools and land in personal plugins with no plan gate, so official sources conflict. Ranking the observer first would pre-empt DQ-1, a ToS-grey choice that is yours | Record the conflict; CS1 decides on day 1 of Stage 0; the Sites check runs in Stage 0 whatever CS2 shows; the observer stays an option |
| MR-10 | Enforcing I13 by truncation in every case | It hides the runaway signal I13 exists for; a reorganiser far over its cap has likely lost focus | Truncate to the top N by evidence only for overruns up to 2× the cap; quarantine the whole job above that; count every overrun |
| MR-11 | "Events keep appending; the faulty transition is deferred" | Events and state commit in one transaction and Apply's gate reads current state; deferral would validate later proposals against stale state and break I18 | Align MT §7.3 with CDM §9.3: freeze the producing job type; exempt capture, correction and compensation events |
| SEC-1 | Signing pin-cache entries; Bash pattern denies; a mandatory service account | Same-user code can read a signing key; pattern denies are bypassable and block `northstar status`; a role account needs admin rights and a LaunchDaemon that managed Macs may refuse, and its peer check cannot tell the real hook client from the same launcher run by an agent | Touch ID or password for destructive commands; file deny rules on the data root; T14; RT-17; the service account as a spiked option (SP-PL-17) |
| SEC-2 | A 6-word or half-the-turn minimum | It turns genuine short corrections ("that's done") into proposals that need a Reader click | Target binding, an independent entailment check, paste exclusion and a per-session cap do the work |
| SEC-4 | Every imperative or markup span shown as "(quoted text, see ID)"; taint for any turn that used a tool | That strips procedures and code, most of what coding agents teach, and nearly every coding turn would be tainted, a speaker asymmetry parity cannot see | Third-person restatement with commands in inert, labelled code blocks; flagged spans held back only from auto-pushed channels; taint by measured overlap with tool or web output |
| SEC-5 | G1's "no imperative" test; G3's cap on every reported goal | "Help me design…" is an imperative; capping every reported goal at p 0.6 means a desktop chat about your real goal never routes to it | G1 keeps only URL, command, tool-call and Northstar-text exclusions; G3 applies to first-session, unreconciled reported goals and lifts after recurrence |
| SEC-7 | Keeping the held-content cache with local-only processing; `openWorldHint: true` | Content held to change later pins is still state under OpenAI's guidance; a bounded private store is not open-world, so `true` would only invite prompts | The stateless profile (FEAS-1); no model call on unrecorded turns; content-free records |
| AIE-2 | Seeding reported goals on later goal stacks and keeping reported constraints long-term, adopted silently | Both amend I22 and contradict DQ-10's text; they raise RISK 25 exposure | Safe parts adopted; the rest asked in DQ-10 |
| AIE-3 | High severity for every unknown-reaction AI item; no verification term in seed severity | Works against RISK 7 and the sycophancy constraint; raises false continuations | A user-accepted seeded AI conclusion keeps High; speaker-blind severity tested as an ablation arm |
| AIE-8 | Truncating long messages to head and tail; 3 points by default | At L0 the model's copy and points are the only capture; truncation drops goals and knowledge from the middle and cuts AI-said capture | Measure time-to-first-token first; shrink only if needed and only in a way capture-recall tests show is lossless |
| BOOK-3 | Verbatim chat text as the default page body for single-source pages | That is the labelled degraded mode, explicitly rejected in the textbook synthesis; GOAL §3.2 asks the AI to explain | One segment sized to its leaves; one quoted reuse; question-only concepts to question pages; verbatim body as an ablation arm |
| BOOK-4 | A second verifier consulted before dropping a sentence | "Either accepts" raises false accepts and bypasses S10's certified bar | Re-draft and re-check with the same certified verifier; an OR-route only if certified in S10 |
| BOOK-7 | Banning a name only where it names a cited leaf's speaker; narrowing the verb subjects to registry agents | "ChatGPT recommends X" would pass in a sentence citing a Claude leaf; "as the assistant suggested" would reopen | Ban any registry name, and generic agent nouns, as the subject of a speech or stance verb, whoever is cited |
| BOOK-10 | A hard breadth filter on the first screen | It can empty "what to learn" for a quiet user, which group G forbids | Breadth is a ranking preference with a fallback that keeps the block filled |
| BOOK-11 | Pure creation-order numbering | Numbers would stop following reading order, weakening the contents as an organiser | Insertion numbers at chapter and part level, cleaned up rarely and inside the churn budget |
| CPLX-1 | A MoE screen plus a dense stage-2 model; drift re-judging only failing verdicts | Two verifier-class models cannot both stay resident; the re-judge exists for Haiku's same-family misses | One V1 chosen by S10; async Claude-reply judgments run directly on V1; in-turn verdicts are re-judged |
| CPLX-9 | Merging intake, ledger, session, jobs and ops into one file | It puts the latency-critical capture path behind maintainer write locks, which SD-3 exists to avoid | Keep the files; ledger-side idempotency (MR-3); defer Postgres triggers and CI |
| CLR-5 | Tagging DQ-1(a) and DQ-5(b) | Declining the observer does not narrow the goal (GOAL §4.6 does not require ToS-grey means); tagging it would pressure the answer | Tag DQ-3(b); keep tags only where an answer narrows or widens GOAL |
| CLR-10 | Putting §13 and §15 under "skip on first read" | GOAL §4 requires risks to reach you, and the fidelity check supports approval | Approver's path is §0, §0.1, §13, §14 and §15's status column |
| CLR-11 | Renumbering the decisions in reading order | This record, the findings and your earlier reading cite DQ numbers | Numbers kept; DQ-8 settled as HOW with an override; DQ-11 moved under "Settings with defaults" |
| CPLX-6 (part) | A hosted third-vendor key for the simulated user and reader | It adds an account and cost; replay-first should cut compute enough | Revisit only if the pre-registered compute budget fails |

---

## 7. Refuted findings

None. Every finding survived at least in part. The parts the skeptics refuted are folded into the verdicts in §5 and the rejected fixes in §6. The main ones:
- MR-5: `goal_card` is not missed by excision; index.db is rebuilt from the excised ledger.
- MR-8: TB §8.14 re-renders without the rolled-back job, so it does not reproduce faulty text; Book structure is reversible, just not hash-identically.
- AIE-7: R12's Opus fallback applies to the verifier role, not the drift judge; V1 stays an uncertified first screen after an S10 failure.
- CPLX-4: C14 is never blocked in Stage 0; the R12 path already exists.
- CONS-12: each DQ heading already names its UQ and Q numbers; no separate map is needed.
- SEC-7: path B is chosen to avoid clicks, not for privacy, and DQ-3(a) already covers ChatGPT content reaching Anthropic.

---

## 8. Questions for you (changes to ARCHITECTURE §14)

These change what §14 asks. Full text is in the revision plan for ARCHITECTURE.md.

1. **DQ-10, expanded** (AIE-2, CLR-3, CONS-2, SEC-5). *Touches the goal.* (a) May one click make a reported desktop goal act like a typed one in later chats? (b) Without a click, may a routed reported goal steer later chats at reported strength, and may constraints you stated in desktop chat persist beyond 14 days as labelled, guard-only items? Recommendation: yes to (a); yes to (b) for goals; constraints only as guard-only.
2. **DQ-4(ii), widened and re-briefed** (FEAS-1, FEAS-4, CLR-1). *Touches the goal.* It now covers either desktop app. It says that an honestly read-only tool keeps nothing within a chat without the widget, restates path A's approvals (per chat if remembered, again after a reload, else per save), and adds option W: declare the per-turn tool a write, one approval per chat and per reload.
3. **DQ-4(i), trigger widened** (FEAS-2, FEAS-3). It also fires when the only ChatGPT route needs `@` on every message. It is asked right after CS1 on day 1 of Stage 0, not at Stage 3.
4. **DQ-4(iii), rewritten** (SEC-9). It lists what crosses the relay and asks (a) OpenAI's tunnel only, or (b) also a Cloudflare fallback that can read it in transit, with Option B carrying only OpenAI-held items by default.
5. **DQ-3(a), consequences of "No"** (CLR-4, CPLX-5). A "No" selects all-local models: focus, continuity and the Book may all weaken, not only the Book. Asked now with estimates; a Stage 0 spike updates them.
6. **DQ-3(b), tagged "Touches the goal"** (CLR-5).
7. **DQ-5(a), hardware floor** (CPLX-4, SEC-6). Independent checking needs an Apple-silicon Mac with enough memory for the local verifier (about 48 GB today); wording made generic.
8. **DQ-1(c), what a visible block means** (SEC smaller issue). The block sits in your own message, so the AI and vendor memory read it with your voice's weight; Northstar limits it to your typed goals and constraints and pending corrections.
9. **DQ-6(b), API replay** (SEC smaller issue). Offline replay sends your chats to each vendor's own API, so DQ-3 must also allow it.
10. **DQ-11 moved to "Settings with defaults"** (CONS-5, CLR-9, CLR-11), with a table of what the default cap does at each use level and a defined hard cap.
11. **DQ-8 removed from §14** (CLR-11). Settled as HOW at its default (not offered), with an override in §12.1.
12. **DQ-2 wording** (CLAR smaller issue; corrected at the final gate). Claude Desktop chat runs on synthetic data only until CD-S1 (and CD-S13, if CD-S1 fails) has a record. It then ships at L0 on the save path those spikes select, or waits for DQ-4(ii) if they fail. ChatGPT Desktop chat does not ship until its spikes, and DQ-4 if they fail, are settled.

Not raised as questions: the closing report call (BOOK-2), the service-account option (SEC-1) and the separate Reader cookie jar (SEC-11). Each is a HOW option behind a spike.

---

## 9. Carried-over tasks

**(a) Propagate ARCHITECTURE §12.2 resolutions into the specs.**
- R12 (S10 failure order): [MT] §6.3, SPINE §8.3 and UQ-4, [EV] L3, [TB] §8.13 (Wilson bound; S10-failure cost aligned with [MT]'s $52 at 100 turns a day).
- R13 (steward audit at desktop L0): [IS] §4.6, [MT] §2, §4.6, §7.3, SPINE §8.1. Applies only to recorded content (FEAS-1).
- R14 (one-chat AI explanations): as amended by BOOK-2 and CONS-4, into [TB] §4.7, §13.2 B, [MT] J3, [CDM] §6, [CX] §2.3; the reply-length decision re-cited to an extension of A12/CS6, not S-R6.
- R15 (continuation false-positive gate): [HK] §9.1 and §15 manifest, [IS] §6.4 and §11, RISK-HK-4.
- R16 (settled HOW): SPINE §11.2 and [TB] §15 items relabelled "Settled as HOW (ARCH R16); user override only"; the relay vendor moves to DQ-4(iii).
- R1–R11 residue: [MT] §0 item 10, §9.6, UQ-MT-1 and X23 lose the $42 nightly golden run; [EV] §6 UQ-HK-1 row says "work scope"; [AC] §6.4 and UQ-AC-1 follow SPINE UQ-12; local UQ IDs become SPINE IDs in [EV] §6, [HK] §22, [MT] §14, [PL] §13; [AC] D4 label; SPINE SD-18 stages, SPINE §8.1 `cascade_first`, SPINE §5.2 Item `rank` fields.

**(b) Remove device-specific security facts.** Every statement about this machine's disk-encryption state, management enrolment, security agents, TLS proxy vendor, installed privacy profiles, admin status, Time Machine destination, exact OS build and installed app or CLI versions, and the account's email domain, becomes a generic conditional ("If FileVault is off at install…", "On an employer-managed Mac…", "If a TLS-inspecting proxy is on the path…", "If the declared account is an employer account…"). Install-time checks stay. Measured values move to `northstar doctor` output in the data root. A generic hardware class may stay where model sizing depends on it. "This Mac" as a place is fine. Files: SPINE, PL, OBS, CD, GD, HK, MT, EV, CDM, ARCH, README, the round-2 notes 10, 11, 13, 14 and SYNTHESIS (evidence kept), and the repo's pyproject.toml (personal author email). The device-specific answers behind UQ-PL-2 and DQ-5 go to you in chat, never in the repo. The first commit already holds the pyproject email; whether to rewrite history is your call.

**Residue found at the final gate (2026-10-08).** The fidelity audit found device and network facts this task had missed: round-2 note 11's Method paragraph (a named TLS-proxy product and a corporate proxy) and note 10's finding 16 and D3 (a proxy that blocked a code host; "the corporate proxy"). They were removed or made generic conditionals. ARCHITECTURE DQ-5(a) and §11, which implied this Mac's posture, became generic conditionals. design/README no longer claims a CI check exists; it will be built ([EV] §6).

**(c) Close the open items in each file's "Fidelity fixes" and "Consistency fixes".**
- SPINE "Coverage gaps": the Claude Code and Codex designs now exist ([HK]); mark that item closed.
- [TB] "Audit coverage gaps": tool names reconciled (X01); misclassified-goal detection handled by AIE-1's item-level Goal-Change Handler; mark each.
- [MT] X10 "Open for CDM": closed by decision; attribution errors are compensated at item level (retract and re-derive); no new event type, so the catalog stays at 51.
- [MT] X23: superseded by R1.
- [CDM] §9.4 and the SQL header "to re-run": the DDL checks are re-run as a Stage 0a task, after this revision's DDL edits; the text says "not yet re-run" until then.
- ARCHITECTURE "Left for the next consistency pass": done by this revision; the section moves to Appendix A here.

---

## 10. Smaller issues (unverified one-liners)

Each was triaged. "Adopted" items were spot-checked against the files first. "Noted" means recorded with no edit now.

| Lens | Issue | Disposition |
|---|---|---|
| FEAS | Claude Code Stop `additionalContext` continues the turn without an error notice | Adopted: default in [HK] §9.2; settles part of HK-S5 |
| FEAS | Codex Stop continuation becomes a user-role prompt; `last_assistant_message` optional | Adopted: label the prompt as Northstar-authored; measure vendor-memory uptake (A14); sweep backfills missing replies |
| FEAS | Codex `additionalContextLimit` is approximate tokens; `systemMessage` shows as a warning | Adopted: units settled (HK-S13); notices kept minimal |
| FEAS | Codex hook trust via `/hooks`, but no `codex` on PATH | Adopted: [HK] §14.3 uses the bundled binary path or a confirmed in-app trust UI |
| FEAS | AGENTS.md doc covers only the TUI and `exec` | Adopted: HK-S10 stays open; the pointer is not relied on for app threads |
| FEAS | Secure MCP Tunnel facts (personal Platform org; Plugins → Tunnel; auth server not tunneled) | Adopted: [GD] CS7, [PL] §3.2, FEAS-4 plan |
| FEAS | OpenAI hidden context rides as composer attachments | Adopted: CR9 and RISK 11 reasoning marked unproven; A14/CS10 measures the hidden channel |
| FEAS | A personal plugin can include local MCP apps on desktop | Adopted: CS2 tests it in Chat mode |
| FEAS | MCP Apps CSP default vs example | Adopted: [CX] §3.6 declares the CSP explicitly |
| FEAS | "Always available" loads all connectors | Adopted: [CD] §4.7 corrected (with FEAS-6) |
| FEAS | Claude MCP tunnels are Enterprise-only | Adopted as a fact (SPINE Appendix B); not a near-term option |
| FEAS | Verified-correct facts list | Adopted into SPINE Appendix B as new rows |
| FEAS | Codex start 2,500 vs 3,000 tokens; HP24; HP12 wording | Adopted: one value (about 2,500 tokens) in [CX] §2.7 and [HK] §15; HP24 and HP12 noted for re-check |
| ROB | DDL/MD naming drift (`contradicted`, `template_fallback`, `account_source`, lanes) | Adopted: CDM text uses the DDL names |
| ROB | Missing `*_no_del` guards | Adopted: [CDM] §4.6 and SQL |
| ROB | Forward FK order breaks Postgres | Noted: CDM-S4 checks it once now (Stage 0a); Postgres triggers and CI come at the cloud-adapter stage |
| ROB | CDM §9.4 test status contradicts itself | Adopted: carried task (c) |
| ROB | `message_slot` index misses desktop `call_index` | Adopted: unique index on session and call index |
| ROB | Excising a winner hides the loser | Adopted: restore or re-resolve the loser; new sweep check |
| ROB | Steward V12 and J3 caps turn dense windows into total loss | Adopted: dense windows are split, not discarded |
| ROB | "Freeze the producing job type" undefined for capture | Adopted: capture violations alert and route to a C06 fix; capture never freezes |
| ROB | Live tagged canaries share the production Apply gate | Adopted: canaries go through a shadow Apply |
| ROB | PL X9 vs CDM §10.2 retry; "only the user starts it" vs policy excision | Adopted (MR-5) |
| ROB | Lease heartbeat can keep a hung worker alive | Adopted: maximum lease age |
| ROB | Recent-provisional items spread before lane disagreement acts | Noted: R13 and AIE-1 reduce it; watched by sentinel #5 |
| ROB | B11 and parity compare against the same capture | Noted: covered by MR-1's coverage audit and BOOK-5's gold-leaf questions |
| ROB | `idem_key` collision on J11x after a prompt fix | Covered by MR-3 |
| ROB | J1r `reconciled_absent` on incomplete verbatim capture | Adopted: outcome `could_not_confirm`, no supersession |
| SEC | Observer peer check by PID is racy | Adopted: audit token plus code-signing check on every message |
| SEC | L2-inject carries state with user-role weight | Adopted: limited to typed goals, constraints and pending corrections; DQ-1(c) says so |
| SEC | Markdown mirror and EPUB not sanitised | Adopted: Reader renderer rules at export |
| SEC | Reader search and titles enter browser history | Adopted: POST or fragment search; neutral `<title>` |
| SEC | Eval egress opens before DQ-3 | Adopted: eval egress gated on DQ-3; DQ-6(b) says so |
| SEC | Spool written before the secret scan | Adopted: scan before spooling |
| SEC | Grounding stores full URLs | Adopted: host plus a hash of the path |
| SEC | Relay consent by email code | Adopted as an option in SP-PL-13: passkey or device-bound consent |
| SEC | RT-4 "never persist" contradicts AI-said passages | Adopted: "never gain authority and never render unneutralised" |
| SEC | Step-up accepts any recent launch token | Adopted: step-up bound to an explicit destructive-action confirmation |
| SEC | Multi-party chats may receive packs | Adopted: multi-participant sessions treated as non-allowlisted; CS1 checks |
| SEC | `.mcpb` credential fallback may sit in plaintext | Adopted: `model_reported` ceiling and short rotation |
| SEC | ARCH fidelity note names the wrong files | Moot: the section moves to Appendix A |
| AIS | No install-time backfill of local coding transcripts | Adopted: one-off backfill within declared scopes after DQ-3 and DQ-5; live metric stratified by prior sessions |
| AIS | No separate hook turn-1 budget | Adopted: turn-1 budget measured in SP-AC-4 |
| AIS | Steward ledger index overflows in long chats | Adopted: index ordered by goal link and recency, with a code lookup for older IDs |
| AIS | L0 regenerate heuristic forks on "continue" | Adopted: short repeated messages never fork; SP-IS-7 |
| AIS | Expired weak L0 corrections drive restart offers | Adopted: they do not count |
| AIS | Pending-resume registry lasts 24 h | Noted: adoption-miss measured; TTL unchanged |
| AIS | Suspected compaction at L0 is a weak signal | Noted: RISK stands |
| AIS | No-route goal menu may prompt the model to ask | Adopted: stated as data; not delivered on `new_topic` |
| AIS | Codex continuation cap if severity rises | Noted: AIE-3's narrow fix does not raise rates materially |
| BOOK | "In their words" trims worked examples | Adopted: expands in place to the full example |
| BOOK | "Where this fits" often empty | Adopted: falls back to labelled chapter neighbours |
| BOOK | Big pictures missing for young chapters | Adopted: fallback to the chapter's top leaves |
| BOOK | Dotted underline on every occurrence | Adopted: first occurrence per page |
| BOOK | Project-bound questions bloat the Book | Adopted: routed to the Casebook; calibrated on the developer persona |
| BOOK | No flush rule for nightly printing | Adopted: J7 flush rule as MT X22 |
| BOOK | Stage 1 bundles all of Book v1 | Covered by CPLX-3's recut |
| BOOK | Re-encounter cards at hook tier unverified | Noted: S-R3, S-R4 stand |
| BOOK | V4 "user's past" detector undefined | Adopted: specified in [TB] §8.5 |
| BOOK | ARCH §4 hides the thin-page trade-off | Adopted (BOOK-2, CLR-8) |
| BUILD | Error budgets lack power at personal scale | Adopted: claim limit in [EV] §2.4 and §6 |
| BUILD | README stale | Covered by CONS-12 |
| BUILD | $42 nightly golden run residue | Covered by carried task (a) |
| BUILD | "Two processes under launchd" | Adopted: SPINE §0 item 4 says three LaunchAgents |
| BUILD | `hookclient/` missing from SPINE layout | Adopted: SPINE §9 |
| BUILD | CDM DDL checks must be re-run | Covered by carried task (c) |
| BUILD | Device facts; personal email in pyproject | Device facts: covered by carried task (b). Email: left unchanged, raised with the user (project metadata is the user's call) |
| BUILD | ARCH cost omits local compute and labelling | Adopted: §0 and §11 |
| BUILD | T-RITUAL could fail on the optional read | Adopted: "no read required" |
| BUILD | Four local model families | Adopted: R fixed to V's family for the prototype |
| CONS | 22 alignment items (agenda status vs basis, partial-copy size, `adopted_via` names, `seeded_from` key, J12 role, process count, pin-cache owner, Codex budget units, R1–R7 residue, OBS §6.1 item 7, MT §4.2 hedge, UQ-5 working assumption, ops.db writer, `agenda.kind 'suggestion'`, `relation.status 'retracted'`, HK §9.1 hourly cap in IS) | Adopted: each is an edit in the revision plan |
| CLAR | Pin and pack size units switch | Adopted: characters throughout ARCH, tokens in brackets |
| CLAR | Builder-week undefined; who types the runs | Adopted: glossary; typing hours shown separately |
| CLAR | §12.1 override does not state alternatives | Adopted |
| CLAR | Approval while SD-17, SD-24, SD-36 are open | Adopted: SD-17 and SD-36 decided here; SD-24 settled as HOW |
| CLAR | API spend is on top of subscriptions | Adopted: §0 cost line |
| CLAR | "The merged app" undefined | Adopted: glossary |
| CLAR | §5 in-turn judge wording | Adopted |
| CLAR | DQ-1 wording of L2-auto | Adopted |
| CLAR | "One keystroke" restart unclear | Adopted |
| CLAR | DQ-2 vs DQ-4 shipping wording | Adopted |
| CLAR | SPINE still records device facts | Covered by carried task (b) |

---

## 11. What the review changed

- **Honest tools.** The per-turn tool on hosts that ask for approval is now truly read-only: stateless, content-free, no model calls. Anything kept goes through a declared write you can see.
- **Desktop chat capture.** A chat's last reply is no longer silently lost if the closing-call spike passes; reported explanations can carry a short body; R14 is computed in code and checked for content parity.
- **Authority.** Hook-tier authority fails closed and can be revoked. Chat corrections need your words to name the item and an independent check. Reported desktop goals stay long-term under guards; whether they steer is your call.
- **Maintainer.** Omission is measured; audits break ties by another route; every freeze has a reachable exit; quarantine exits are defined; Apply derives atomic groups; excision is a resumable saga; rollback reaches live sessions; J10e is dropped.
- **Security and privacy.** A prompt-injected coding agent is in the threat model; destructive commands need Touch ID or your password; one rendering rule covers all model-facing text; write budgets stop a looping agent; the relay question says exactly what crosses; device facts leave the repo.
- **AI side.** Corrections check your latest turn first; coding agents' edits are checked; mid-chat returns to earlier goals get continuity; Northstar's own context load is measured.
- **Book.** It has a growth regime from day 1, page forms that fit thin evidence, a quality path for wording, and evaluation that can catch a correct but useless Book.
- **Build.** A spike sprint comes first, then a thin slice on Claude Code; one pilot per cell family; replay-first testing; a per-role load model for the local verifier.
- **Approval document.** Plain per-app summaries, a glossary, concrete examples, decisions rewritten with their real consequences, and a realistic reading time.

---

## Appendix A. ARCHITECTURE fidelity fixes of 2026-10-08 (moved here)

Moved from ARCHITECTURE.md so the approval document stays short. Two independent goal-fidelity audits. Each fix changes the design only as far as it needs and weakens no non-negotiable.
- **§0:** source and maintainer claims made exact; hook facts labelled; table rows corrected (visible follow-up, L0+ delivery unconfirmed, ChatGPT plan gating, "gets the pack", L1 delivery, cloud sessions); risks added for per-chat actions and plan gating; decision groups match §14.
- **§1:** four parts; GOAL §3.1, §3.3, §4.6, §6 wording restored. **§3:** consolidation (J5, J8c, I12, I13); I22 row.
- **§4:** understand-and-remember table with tests; honest limit (H1); re-encounter cards (H14); speaker-neutral promotion and the desktop gap (R14); forward chapters per DQ-7.
- **§5, §6:** same-family in-turn judge (R15); "corrected before control returns"; ChatGPT L0 restart suggested; no desktop L0 steward audit (R13); sycophancy and stale-assertion bars; Developer mode (CR15).
- **§7:** "Always allow" (Unv, CD-S1) and CD-7; PK-1 Developer mode; held-content cache review; web apps; C1 at L0, C2 at L0+; level table by reference to [CX] §8.
- **§8:** independence fallback; S10 path (R12); budgets 2/5/8%; rollback by compensating events; steward and extractor limits.
- **§9–§11:** device facts made generic; future tense for CI, seams, red-team tests; provider retention; BK2 parity and rubric judge; revision refusals and the R15 rate; "in force" defined; S10 cost.
- **§12:** register cut to what you would notice, plus HOW settled here with an override; R1 detection; R12–R16.
- **§13:** top 14, adding per-chat actions, continuity, RISK 20, the no-route outcome and the S10 path. All other risk IDs are in SPINE §11.1, TEXTBOOK §16 and each spec's Risks section. None threatens a GOAL item beyond those listed here ("Also tracked" was completed at the final gate).
- **§14:** grouped now, later, only-if-a-spike-fails; "until you answer" on every decision. Old DQ-8 (remembering) removed (R16). Old DQ-10 split into DQ-8, DQ-9, DQ-11, DQ-12. DQ-1, DQ-2, DQ-4, DQ-6, DQ-7, DQ-10 reworded.
- **§15:** "Met by design"; §4.8 "Planned"; rows for GOAL §1, §3.2 organise and explain, §3.3 beyond files, §3.4 consolidation, §5, §7; at-risk surfaces named.
- **Size:** appendix map moved to README.md; restated spec detail cut by reference.
- **Left for the next consistency pass** (closed by this review's revision): device facts in SPINE §11.2 and [PL] (and, the review found, in OBS, CD, GD, HK, MT, EV, CDM); the questions R16 settles; R12–R15 adoption in [IS], [MT], [TB], [CX], [HK].

---

## Appendix B. Official sources re-checked during the review (2026-10-08)

- OpenAI Apps SDK reference: https://developers.openai.com/apps-sdk/reference (`readOnlyHint` meaning; tool input for approval-gated calls)
- OpenAI plugin guidelines, "Correct annotation": https://developers.openai.com/plugins/plugin-guidelines
- OpenAI app review: https://developers.openai.com/plugins/deploy/app-review
- OpenAI custom MCP server guide: https://developers.openai.com/api/docs/guides/custom-mcp-server
- OpenAI Secure MCP Tunnels: https://developers.openai.com/api/docs/guides/secure-mcp-tunnels
- OpenAI MCP extensions spec: https://github.com/openai/mcp-extensions/blob/main/docs/spec.md
- ChatGPT help 12584461 (Developer mode and MCP apps), 20001256 (plugins), 20001495 (app permissions), 20001519 (plugin use)
- MCP schema 2025-11-25: https://modelcontextprotocol.io/specification/2025-11-25/schema
- MCP Apps spec 2026-01-26: https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/2026-01-26/apps.mdx
- Claude connector review criteria: https://claude.com/docs/connectors/building/review-criteria
- Claude MCP Apps instance supersession: https://claude.com/docs/connectors/building/mcp-apps/instance-supersession
- Claude MCPB: https://claude.com/docs/connectors/building/mcpb
- Claude plugin platform support: https://claude.com/docs/plugins/platform-support
- Claude MCP tunnels: https://claude.com/docs/connectors/mcp-tunnels/overview
- Claude connectors, getting started: https://claude.com/docs/connectors/getting-started
- Claude tool access: https://support.claude.com/en/articles/13730515-manage-claude-s-tool-access
- Claude Code hooks: https://code.claude.com/docs/en/hooks
- Claude Code permissions: https://code.claude.com/docs/en/permissions
- Codex hooks: https://learn.chatgpt.com/docs/hooks
- Codex AGENTS.md: https://learn.chatgpt.com/docs/agent-configuration/agents-md.md
- PyPI wheel listings for `mlx` and `leidenalg` (CPLX-11)

---

## Final-gate fixes (2026-10-08)

After this revision, a final gate checked the whole set three ways: design, fidelity to this review, and fidelity to GOAL.md. It found three kinds of issue. Every fix is HOW or a more honest statement; no non-negotiable was weakened, and no fix had to become a new question. Each edited file ends with its own "Final-gate fixes" section.

**1. Decided review fixes that had not reached every spec.**

| Finding | Where it now lands |
|---|---|
| FEAS-1, CONS-9 | [CDM] and SQL: no `hash_only` observation, no `observation.persist_policy`; path B writes no observation. [AC]: no session cache; seeds wait for a declared write. [EV]: GD-L0 rows per path C1, C2, A, B, W |
| BOOK-2 | [CDM] and SQL `reported_point.body` and `reply_scope`; SPINE §4.2, §4.4; [GD] §6.2.2 arguments and a rewritten result example |
| MR-4, SEC-3 | [IS] §4.3 fails closed (`confirmed_degraded`); [IS] RISK-IS-6 and ARCH §13 use per-segment paste demotion; [MT] §5.3 authority gate |
| MR-8, MR-12, CPLX-11 | [IS] handles `items.retracted`, V12 splits dense windows; [MT] J10b re-resolves an audit-undone tension as contested; [MT] §6.4 modeld interpreter rule |
| SEC-4, SEC-8, SEC-11, SEC smaller issues | [CX] rendering rule, Reader host and cookie, peer check by audit token; SPINE §6.1 pin cache; the L2-inject content rule in [IS], [AC] and SPINE |
| AIE-9, AIE-12, CLR-1 | Supersession line in [AC] and ARCH examples; [EV] vendor-memory staleness probe; C16 and SPINE UQ-8 cover either desktop app |
| CPLX-8, CPLX-9, BOOK-3, FEAS-2, carried task (a) | J10e dropped in SPINE I19 and [AC] §7.4; [EV] C3 checks Postgres once now; V1–V15 in [MT] and [EV]; PK-1 naming in ARCH, [GD] and SPINE; [PL] uses SPINE UQ IDs |

**2. Approval-document honesty (ARCHITECTURE.md).** DQ-2 no longer lets Claude Desktop chat ship before CD-S1 (and CD-S13) select its save path. The privacy claim says names and free-text facts are not masked (RISK-PL-4). Hidden user actions are listed (one "Always allow", path-W approvals, upgrade steps, RISK-PL-12). §13 now lists every risk that threatens a GOAL item. DQ-4(ii) names its effect on in-session focus and why A is recommended over W. §1 restores GOAL's wording. §15 rates GOAL §3.4 Partial and covers cloud and enterprise later. §14 states one rule for defaults. §12.1 shows TEXTBOOK Q1, Q4 and Q5 with their overrides.

**3. Device-fact residue** in round-2 notes 10 and 11, ARCHITECTURE DQ-5(a) and §11 and design/README (§9(b)). `pyproject.toml` was restored unchanged; its author email is raised with the user.

**Fewer questions.** DQ-6(c) (UQ-17) is settled as HOW at its working assumption, with an override in ARCHITECTURE §12.1. DQ-12 is merged into DQ-3(d); its number stays reserved.

**Status.** The design passed design, adversarial review and goal-fidelity checks on 2026-10-08 and awaits your approval of ARCHITECTURE.md.

---

## Appendix B. Change logs moved from ARCHITECTURE.md

These logs record how the approval document changed during the review and the final gate. They moved here so the approval document holds only the design.

### ARCHITECTURE.md: review revisions (2026-10-08)

Full record: [REVIEW.md](REVIEW.md). Every change is HOW; fixes that would change the WHAT became questions in §14. The earlier fidelity-fix log is in REVIEW.md Appendix A.

| Findings | What changed |
|---|---|
| CLR-2, 3, 6, 7, 10 | Reading path; "GOAL §n"; exact maintenance claim; per-app summaries (§0); glossary (§0.1); checks 0–6; words before IDs |
| CLR-8 | Examples: explanation, reported variant, first screen (§4), pin (§5), pack (§6); evidence column |
| CLR-1, FEAS-1, SEC-7 | Stateless, truly read-only per-turn tool; declared writes only (§7); DQ-4(ii) for either app, option W |
| FEAS-2 to 7, AIE-11 | One ChatGPT route; CS1 on day 1; `@` per message; approvals after reload; Tool access per conversation; delivery measured; boot-line test; extension fallback |
| BOOK-2, CONS-4 | Closing call; reported explanation bodies; R14 in code with content parity |
| BOOK-1, 3, 4, 5, 7, 8 | Growing Book; pages sized to evidence; re-draft before drop; 15 validators; no product as speaker; "reworded" printings; BK0 bar |
| MR-1, 2, 5, 6, 8, 11, 12 | Omission probe, duplicate sentinel and budget; tie-breaks; excision saga; reachable freeze exits; canonical rollback; reference projector; contested after audit dissent |
| MR-4, SEC-3 | Hook authority fails closed, revocable (§3) |
| SEC-1, 10 | T14, RT-17; Touch ID or password; write budgets; two §8 rows; 23 faults |
| SEC-2, 11 | Chat corrections need your naming words and an independent check; Reader on `northstar.localhost` |
| SEC-5, AIE-2, CONS-2 | SD-36 kept with guards; reported goals labelled; DQ-10 expanded |
| SEC-9 | Relay contents in §9 and DQ-4(iii); vendor choice moved from R16 |
| SEC-6, CPLX-4 | DQ-5(a) hardware floor, generic |
| AIE-1, 4 to 10 | Latest-turn check; edit and command checks; tier-0 independent; mid-chat goal switch; seed guards; context-share and latency metrics; length trigger; continuity bars; real-CLI runs |
| CONS-3 | R13 audit on recorded turns |
| CONS-5, CLR-9, 11 | Cost line; DQ-11 table under settings; DQ-8 settled in §12.1 |
| CLR-4, 5, CPLX-5 | DQ-3(a) effects of No; DQ-3(b) touches the goal; §0 lists all such |
| CPLX-1 to 3, 7 to 9 | Load model; spike sprint; Stages 0a, 0b; labour hours; per-family pilots; J10e dropped; sentinel precedence; Postgres CI later |
| Smaller issues | DQ-1(c), DQ-6(b), DQ-2 wording; "no reads required"; restart and L2-auto wording; override alternatives |
| Carried tasks (a), (c) | §12.2 compacted, resolutions in the specs; fidelity log moved |

---

### ARCHITECTURE.md: final-gate fixes (2026-10-08)

The final gate (design, adversarial review and goal-fidelity checks) found the issues below. Every change is HOW or a more honest statement of the design; no non-negotiable is weakened and no WHAT is re-scoped. No fix needed to become a new question; two questions were merged or settled to keep §14 short (last two rows).

| Issue | What changed |
|---|---|
| Status | The status line says the document passed design, adversarial review (REVIEW.md) and goal-fidelity checks on 2026-10-08 and awaits your approval |
| Claude Desktop chat shipped without its save path | DQ-2: Claude Desktop chat runs on synthetic data only until CD-S1 (and CD-S13 if CD-S1 fails) has a record; it then ships on the save path they select, or waits for DQ-4(ii). Same rule in §0, §7, §11 Stage 2, [CX] §4.1, [EV] §5.1 |
| Privacy claim overstated | §9, its table and DQ-3(a): only secrets and structured personal data are masked; names and free-text personal facts are sent as written unless an item is private (RISK-PL-4, now in §13 row 11) |
| Risks missing from §13 | "Also tracked" lists every spec risk that threatens a GOAL item, with threat, GOAL reference and mitigation, and ends with a true completeness sentence. RISK-IS-6 uses the paste-demotion rule |
| Hidden user actions | §0: one "Always allow" click; ChatGPT sign-in where CS1 shows it is needed; path-W approvals; upgrade steps (RISK-PL-12). §13 row 3 and §15 GOAL §4.1 row match |
| DQ-4(ii) briefing | Tagged GOAL §3.3 and §4.5 too; one line per option on in-session focus; the reason for A over W; trigger names CD-S13. §13 row 2 and §15 GOAL §3.3 row add in-session focus (RISK 33) |
| Goal restatement | §1 restores GOAL wording: structured; learned from you and from AIs; what to learn (goals, gaps, open questions, next steps); understand and remember like a textbook; what was established, not "the goal"; the AI does all capture, structuring, consolidation and reorganisation; any connected product |
| §15 status honesty | GOAL §3.4 consolidation is Partial (RISK 6, MR-1; RISK 15, TB H5). GOAL §4.6 row covers cloud later and enterprise later. GOAL §7 row lists every possible narrowing |
| Device facts by implication | DQ-5(a) and §11 are generic conditionals (ground rule 6) |
| Exactness | §3 attribution and "captured" assistant spans at desktop L0; §5 evidence for specific corrections carries its transfer caveat; §5 restart-trigger counting matches [IS] §6.4; §5 discloses medium-severity guarding of unaccepted AI items ([IS] §6.5); §4 gaps and the non-goal on inferred directions; §0 and §6 path B covers either app; §6 ten pack checks; §11 Stage 0a scope (A1–A12, A7 Sites, SP-MT-7) |
| Supersession line (AIE-9) | The §5 pin and §6 pack examples state that they supersede earlier Northstar blocks |
| Stale names | PK-1 is the one ChatGPT route; SPINE Appendix B is P1–P37; the §4 sample says "every table that is queried" |
| One rule for defaults | §14 states one rule: decisions needed now block real data; a narrowing default ships labelled and is reported as narrowed, never as met; where no option is assumed (DQ-4), the app does not ship. DQ-7, DQ-9 and DQ-10 say which applies; DQ-9 names its stage |
| Settled as HOW, now visible | §12.1 names [TB] Q1 (no retrieval aid), Q4 (current memory levers, risk H1) and Q5 (no engagement summary), each with its override; §4 points to them |
| Desktop goals | DQ-10 and §0 no longer ask you to restate goals or move to another product mode |
| Fewer questions | DQ-6(c) (real-window labelling, UQ-17) is settled as HOW at its working assumption, with an override (§12.1). DQ-12 is merged into DQ-3(d); its number stays reserved |
