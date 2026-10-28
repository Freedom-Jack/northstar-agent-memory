# Benchmark v0: baseline first

**Status:** proposal for your approval, revision of 2026-10-09. It answers your comment 5. Nothing is built or run. Written 2026-10-09.
**Authority:** [GOAL.md](../../GOAL.md) overrides this document; your answers of 2026-10-09 override everything earlier. It changes only the HOW of evaluation. Existing specs are not edited; "Supersedes" lists what changes.
**Reads with:** [ARCHITECTURE.md](../ARCHITECTURE.md) §10–§11; [EV] [evaluation-and-build-plan.md](../components/evaluation-and-build-plan.md) §1–§3; [TB] [TEXTBOOK.md](../foundations/TEXTBOOK.md) §13; this folder's [personal-relevance.md](personal-relevance.md) [PR] §7, [knowledge-organization.md](knowledge-organization.md) [KO] §9.4 and [connector-strategy.md](connector-strategy.md) [CN] §8; evidence [11] and [14] in `docs/research/round2/`.
**Labels:** (Unv) = unverified product fact, with the spike that settles it (BM-S, §13). Verified facts are listed at the end with URL and date. New IDs: measures F (focus), K (continuity), U (the human side); risks RISK-BM; questions BQ. Every number is a starting value (estimate) until the pilot, then frozen.

---

## 0. On one page

- **What it is.** One benchmark in two parts, run twice: **Phase B** without Northstar, then **Phase N** with it, on the same scripts from your real topics, in the same products, on the same Windows machine.
- **Part A, AI assistance.** Scripted chats in the real apps (typed by the builder in the desktop apps, driven by code on the CLIs). **Drift:** 40-turn chats with planted goals, constraints, rejected options and views (yours) and explanations and recommendations (the AI's), probed at turns 31–40. **Continuity:** two seed chats, a wait, then a new chat that needs what they established; we count what it knows without being told, and how often you would have had to re-explain.
- **Part B, the human side.** About 2 hours with you, before (your current means: chat search, vendor memory, notes) and after (the Northstar Book), in four sittings of about 30 minutes or two of about an hour; a short format takes about 1 hour (§5.4, DQ-14(e)). Open-book tasks from your real record, such as "what did I conclude about X, and why?". The sessions also carry this revision's relevance and structure checks ([PR] §7, [KO] §9.4).
- **Comparable by construction** (§2): fresh chats, randomized order, the same driver and waits, and vendor memory treated identically, in separate bench accounts that keep your own memory untouched (BQ-2). Phase N also re-runs a full-size **late baseline** with Northstar off. Phase B is the pre-registered baseline and headroom check; the late baseline is the comparison whenever model versions changed, which a months-long build makes likely (§7).
- **Mechanism, on the same product:** on the CLIs, an automated arm M runs Northstar through MCP only (hooks off), next to the hook arm (§4.7).
- **Improvement is defined before any data** (§6): a meaningful threshold and guards per measure, and six verdicts (§7).
- **Scoring:** written rubrics; a local judge of a third family (neither Anthropic nor OpenAI), blind to phase; every failure quotes the reply; the builder re-labels 20%.
- **Reported per connector and per OS**, never pooled: Claude Desktop chat, ChatGPT Desktop chat, Claude Code and Codex on Windows; iOS and Mac follow (§11).
- **Cost:** about 2 hours of your time if someone else builds (about 1 hour in the short format). If you build, also about 125–145 builder hours (±50%; about 42 of them typing), plus about 35–45 hours of labelling if no local judge passes (BQ-4). Lite: about 60–70 builder hours. About $250–650 of API (±2×), mostly the backfill the Book needs anyway.
- **Phase B can start before Northstar is built**, once you approve this plan (BQ-3).
- **Limits** (§12): one user, small samples, scripted chats, open-book tasks; unaided remembering stays unmeasured.

### 0.1 Words used here

- **Builder:** whoever builds Northstar (a developer with AI coding agents); possibly you (§5.6).
- **Scenario:** one real topic, written as one drift script and one continuity chain.
- **Item:** something established in a chat. Yours: a goal, constraint, rejected option, or view with its reason. The AI's: an explanation, recommendation or conclusion. An **item-check** judges one reply against one item.
- **Prompter:** a local tool that shows the builder the next scripted turn, puts it on the clipboard and stores the reply the builder copies back. It never operates a vendor app.
- **Late baseline (arm BL):** Phase N runs with Northstar switched off. **Arm M:** Phase N runs on the CLIs with Northstar through MCP only, hooks off.
- **Session 1, session 2:** the before and after parts of Part B, whatever the sitting format (§5.4).
- **Record:** your real chat history up to cutoff date C (one local export of your Claude and ChatGPT chats, plus local Claude Code and Codex transcripts).
- **Bench accounts:** one extra personal account per vendor, on your plan, used only for Part A (§4.5, BQ-2).

---

## 1. What it answers

| Question (GOAL §6; comment 5) | Part | Primary measure |
|---|---|---|
| Late in a long chat, do answers still serve the goal and respect what you and the AI established? | A | F1 late item errors |
| Does a new chat start with your goals, views, reasoning, AI-taught knowledge and conclusions, without re-explaining? | A | K1 continuity recall |
| Does the Book help you find, understand and trace your own thinking better than your current means? | B | U1 answer correctness |
| Is what Northstar organizes about your thinking, and not a generic glossary? | B | U6 relevance precision ([PR] §7) |

In-session focus and continuity each have their own primary measure, so they carry equal weight (GOAL §4.5). Secondary measures and guards are in §6.

---

## 2. What is held equal in both phases

| What | Rule |
|---|---|
| Scripts, chats | Scripts frozen before Phase B, the same text in both phases, never used to tune Northstar (RISK-BM-8). Every run uses fresh chats |
| Products, platform, models | The same four products on one Windows machine, in a separate Windows user account for the benchmark; the same model choice while offered; versions recorded per run |
| Driver, waits | The same builder and prompter (desktop), the same driver code (CLIs), no improvising; the same wait W before each new chat, set by BM-S1 (§4.4) |
| Memory | Vendor memory on, starting empty, isolated per run (§4.5). The only prior history any memory may use is the run's own seed chats ("equal information") |
| Order | A random schedule from a recorded seed; in Phase N, Northstar-on and late-baseline sittings alternate at random |
| Scoring | The same rubrics, judge and blinding (§4.6) |
| Record (Part B) | The same record up to C: your current means see it in session 1; the Book is built from the same export |

---

## 3. Structure and timeline

| Step | Who | Needs |
|---|---|---|
| 1. Answer DQ-14 (this plan, BQ-1 to BQ-6 and BQ-10, including BQ-3 = DQ-14(c)), DQ-2 and DQ-5(a) | You | — |
| 2. Session 1 (§5.3); the export is taken that day, date C | You | Step 1; **bench-folder encryption that needs no Northstar code:** BitLocker or Device Encryption on the bench machine, or an established encrypted container for the bench folder |
| 3. Cards and scripts from your script topics; tools; an unscored pilot per connector; judge calibration and the unblinding check; BM-S1's latency probe; pre-registration (with the topic partition and label allocation) frozen | Builder | Step 2 |
| 4. Phase B runs | Builder | Bench accounts (BQ-2); wait W |
| 5. Northstar is built (ARCH §11, as revised) | Builder | Design approval |
| 6. Backfill of the record to C, in date order, so the Book grows as it would have | Northstar | DQ-3(a) |
| 7. Phase N, per connector as each is ready | Builder | Its spikes |
| 8. Session 2 (§5.4), once the Book holds the backfill and ≥ 2 weekly editions | You | Step 6 |
| 9. Report | Builder | — |

Phase B needs no Northstar code. Steps 1–4 build only benchmark tooling (prompter, bench app, CLI drivers, scoring scripts; about 20–30 hours) before design approval. That changes GOAL §7's order for evaluation only, and it is asked (BQ-3, DQ-14(c)), not assumed. Your real data enters Northstar's store only after design approval, DQ-2, DQ-3(a) and DQ-5. A late connector delays only its own row.

---

## 4. Part A: AI assistance

### 4.1 Cells, and who drives

- **Claude Desktop chat and ChatGPT Desktop chat:** the builder types, with the prompter. Vendor terms bar automating the chat apps, and UQ-22 (ARCH §12.1) settled that a person types in-app runs.
- **Claude Code and Codex:** driver code through their sanctioned headless modes (`claude -p` resumed per turn; `codex exec` and its resume). Repeats are cheap.
- All four run natively on Windows (facts at the end). Headless multi-turn runs with hooks firing and a per-run home are (Unv) on Windows: BM-S2.
- **Not you, and no simulated LLM user in v0.** Fixed scripts keep both phases identical; an adaptive simulated user comes in v1. **No improvising:** if a reply asks a question, the next scripted turn proceeds anyway, and scripts are written so this stays natural.

### 4.2 Scenarios from your real topics

- From the **script topics** of your session-1 list (the partition, §5.3), the builder writes one **scenario card** per topic: your goal; 2–3 constraints; an option you reject, with your reason; one of your views with its reasoning, and a request for the AI's strongest objection to it; a concept for the AI to explain; two decisions for the AI to recommend; a pivot; a later change of view. Cards and scripts stay in the local bench folder. You may glance at the cards (optional, about 10 minutes).
- **Chat track:** 4 scenarios, the same scripts on both desktop apps. **Code track:** 2 scenarios on a copy of a personal repository (or a small one themed on your topic), the same scripts on both CLIs.
- **The AI's items cannot be scripted.** The script **elicits** them with a forced choice ("Give one clear recommendation, A or B, and why"), and your next turn **accepts** them. The judge records that run's item as an exact quote; later checks use it. An elicitation with no clear item is dropped and counted.

### 4.3 The drift script (40 turns)

| Turns | What happens (what it tests) |
|---|---|
| 1–7 | Your goal G1, constraints K1 and K2 (t1); your view V1 with its reason (t4); you ask for the strongest objection to V1 by forced choice and the AI gives O1, quoted as an AI item, which you leave unanswered (t5–6); you reject option R1, with a reason (t7) |
| 9–13 | The AI explains E1 and you build on it (AI-taught); the AI recommends D1 and you accept (AI conclusion) |
| 16–23 | A new constraint K3 mid-chat (loss of middle turns [11 F2]); a legitimate pivot, G1 refined to G2 (t20, over-steering guard); the AI recommends D2 and you accept |
| 26–30 | Pushback on D1 without evidence (unwarranted flip [11 F4]); a related tangent, for distance |
| 31–37 | **Late probes.** P1 a task (draft the plan; must respect K1–K3, R1, D1, D2, G2); P2 an option question that tempts R1; P3 a task needing E1; **P4** a question where V1, its reason and O1 matter, and **P4b** a leading prompt inviting agreement with V1 (both contested-position probes, F6); P5 "list what we settled, who proposed each, what we ruled out and why". Task probes come first so recall does not prime them |
| 38–40 | You revise D2 **with new evidence** (a legitimate change, F4); P6 a task that must use the new D2 (stale content) |

### 4.4 The continuity chain

| Chat | Content |
|---|---|
| S1, ~10 turns | Goal G1; constraint K1; your view V1 with its reason; AI explanation E1; AI recommendation D1, accepted; option R1, rejected with a reason |
| S2, ~8 turns, ≥ 1 hour later | You change V1 to V1′, with a reason; the AI gives the strongest objection O1′ to V1′ by forced choice, which you leave unanswered; the AI explains E2, which you do not act on; an open question Q1 is raised |
| Wait W | Set by BM-S1's latency probe: the longest latency measured at 1, 3 and 24 hours, and at least 24 hours if a bench account has Claude's legacy memory, whose synthesis "is updated every 24 hours" (fact list). The same W in both phases. It lengthens the calendar, not the typing |
| T, a new chat, 8 turns | t1 "Let's continue with [topic]. Where were we, and what's next?" (needs G1, D1, Q1); t2 a task needing K1; t3 an option question that tempts R1; t4 a question where V1′ and O1′ matter (V1 is stale; a contested-position probe, F6); t5 a task building on E1, E2; t6–t7 recall probes ("What did you explain to me about …?", "Why did I change my mind about …?"); t8 asks about a decision never made (correct: "we did not decide that") |

- **Re-explanations needed (K2):** t1–t5 have their needed items mapped in advance. A needed item that is missing or wrong counts as one re-explanation you would have had to make, so fixed scripts give a counterfactual count. The new chat names the topic, never the content.
- **Cross-product chains (optional, K5; BQ-7):** S1 and S2 in Claude Desktop chat, T in ChatGPT Desktop chat, and the reverse. Vendor memory cannot cross vendors, so the baseline is near zero.

### 4.5 Vendor memory, treated the same way

- **Default (BQ-2): bench accounts.** One extra personal account per vendor, on your plan. Vendor memory is on, as you use it, and starts empty. So vendor memory sees exactly the seed chats Northstar sees; your real memory neither helps nor gets polluted; the builder never sees your history.
- **Isolation per run.** Each run lives in a fresh Project. A Claude Project has its own memory (verified); ChatGPT's project-only memory is (Unv). BM-S1 tests both directions. If isolation fails, the builder clears the account's memory and chats between runs, checks the reset with a planted-fact probe, and runs sequentially.
- **Northstar side.** A separate Northstar install in the benchmark Windows account, with a fresh store per run, switched before each sitting. Your live Northstar memory is never used or written.
- **CLIs.** A fresh repository copy and per-run home (Claude Code's configuration; Codex's `CODEX_HOME`); each tool's own memory (CLAUDE.md, auto memory, AGENTS.md) at its defaults (Unv on Windows: BM-S2).
- **Late-baseline sittings.** Boot line removed, connector disabled (plugin and hooks off on the CLIs). Receipts must show zero Northstar calls, or the run is redone.
- **Setup steps count.** Boot lines pasted per Project (ARCH CR10) are reported under F5 as steps you would do. If Northstar's ChatGPT route switches ChatGPT memory off (Developer mode; Unv, CS1; ARCH §6), that is part of the treatment, and the report says so.
- **Not measured here:** Northstar next to your real, months-old vendor memory. K6 (§5.5) covers that.

### 4.6 Scoring

- **Rubrics,** fixed in the pre-registration:
  - *Item-check:* one label per item and reply: consistent; not addressed; contradicts; violates (constraints); re-proposes (rejected options); stale (states the superseded version). A failure label must quote the reply; code checks the quote is exact, else the label becomes "not addressed".
  - *View items* (V1, V1′), at the probes where the view matters: **acknowledged** (agrees, or disagrees with reasons while engaging the view) passes; **ignored** (proceeds as if no view were recorded) and **contradicted without acknowledgement** (asserts the opposite and ignores the view) fail. A reasoned disagreement is never labelled "contradicts", so disagreeing with you is not scored as drift.
  - *Contested-position probes* (P4, P4b, chain t4) also get: **endorses without engaging the objection** (agrees with the view and does not mention O1 or O1′) or not (F6).
  - *Which reply:* on hook connectors a high-severity breach gets one visible follow-up correction. F1 scores the **first** reply; "corrected before control returned" is reported separately (F1c).
  - *Goal service:* 1–5 with anchors (5 advances the active goal within the constraints; 3 generic; 1 works against it or serves a dropped goal).
  - *Continuity:* per needed item: correct without being told; partial; absent; wrong. *Flip:* abandons an AI item after pushback with no new evidence.
- **Judge:** one local open-weight model of a third family for every cell ([EV] §1.3), on whichever of your machines has the capacity. Which family passes, on what hardware, is (Unv): BM-S4.
- **Calibration** before Phase B is scored: ≥ 60 builder-labelled checks from the pilot, 20 of them planted wrong-but-on-topic replies and 10 reasoned disagreements with a view (which must pass). Pass: misses ≤ 15%, false alarms ≤ 10%. Judges are lenient: one accepted 63% of on-topic wrong answers [11 F9]; LoCoMo's, 62.81% [14 F13].
- **Blind to phase:** Northstar blocks, tool-call text, the word "Northstar", item-ID patterns (such as G12, D7, V4, R4) and the fixed phrases of the correction templates are removed or masked. **Unblinding check:** before scoring, the judge guesses the phase of 40 masked samples; it must be right at most 60% of the time, or the masks are extended and the check repeated.
- **A person spot-checks:** the builder re-labels a 20% sample, stratified by connector, phase and label, failures oversampled, blind to phase. Agreement per metric family must be ≥ 85% (kappa ≥ 0.6); otherwise the builder labels that metric in full (about 2,100 checks in all, about 35–45 hours) or BQ-4 applies.

### 4.7 Sizes per connector and arm

| | Claude Desktop chat | ChatGPT Desktop chat | Claude Code | Codex |
|---|---|---|---|---|
| Drift: scripts × runs | 4 × 2 | 4 × 2 | 2 × 4 | 2 × 4 |
| Chains: scripts × runs | 4 × 2 | 4 × 2 | 2 × 4 | 2 × 4 |
| Late baseline in Phase N | 4 × 2 of each | 4 × 2 of each | 2 × 4 of each | 2 × 4 of each |
| Arm M (MCP only) in Phase N | — | — | 2 × 4 of each | 2 × 4 of each |
| Late item-checks per arm (about) | 100 | 100 | 100 | 100 |

The late baseline is **full-size by default** for every connector (§7). **Arm M** runs on the CLIs only: hooks off; Northstar's MCP server with its server instructions and a boot line in CLAUDE.md or AGENTS.md; the same scripts, automated. It compares mechanisms on the same product: F1, K1, the verbatim share of AI-said capture, and the call and first-call rates are reported next to the hook arm, with the difference and its 90% interval and no pre-set threshold (secondary). The chat apps offer only MCP, so their cells compare MCP plus the widget with no Northstar; observer against MCP is measured only if DQ-1 is yes.

### 4.8 The per-connector report

One table per connector, with columns Phase B, late baseline, Phase N, change, 90% interval, threshold and verdict. It also gives the connector's layer and [CN] §8's diagnostics: call rate, first-call rate (with the K0 gate), widget delivery, verbatim share of AI-said text, your actions per 100 chats, added latency. The CLI tables add an arm M column.

---

## 5. Part B: the human-facing organization

### 5.1 The record and the answer keys

- **The record** is defined in §0.1; what the exports contain is (Unv): BM-S3.
- **The task pool:** drawn **only from task topics** (the partition, §5.3), so no task asks about a topic the builder typed scripts on. A local model drafts about 30 candidate tasks, each with 2–4 key points, exact quotes (checked by code), product, speaker and date; material ≥ 30 days old is preferred, so tasks are not trivial.
- **Matched pairs:** code pairs candidates by topic and type; a random draw sends one of each pair to session 1, the other to session 2. You see no key before answering (§5.6).

### 5.2 Task types (10 matched pairs)

| Type | Example | Pairs | Key |
|---|---|---|---|
| T1 Conclusion and why | What did I conclude about X, and why? | 2 | The conclusion and its reasons |
| T2 Change of view | How did my view on Y change, and what changed it? (this is [KO] §9.4's "where does your thinking stand, and what changed?") | 2 | Earlier view, later view, the cause |
| T3 Still open | What is still open on Z? | 2 | Recorded open questions, not since resolved |
| T4 What next | What should I explore next for problem P? | 2 | Recorded open threads and next steps for P, plus your usefulness rating |
| T5 Who and where | Who explained this to me, and where? | 2 | Speaker, product, date (±3 days), conversation |

### 5.3 What the two parts hold, budgeted at the caps

Minutes are typical, then worst case: every task at its 4-minute cap plus about 30 seconds of ratings. A small local bench app shows and times every module and stores your answers.

**Session 1, before Northstar** (date C, the export day):

| Module | Typical | Worst |
|---|---|---|
| Introduction; consent confirmed | 3 | 3 |
| **Your reference list, unaided** ([PR] §7.1): questions and problems you are exploring; 3–5 views (and any you changed); interests; **2–4 things an AI explained to you that you now rely on or use**. You mark topics unsuitable for scripts, and which have a personal code repository. The bench app then **partitions** the topics at random (recorded seed) into **script topics** (Part A only) and **task topics** (Part B only) | 15 | 15 |
| **Pickup probe without Northstar (K6):** two scripted prompts in a fresh chat in each desktop app, your own account, vendor memory as it is ("What am I working through at the moment?", "Where do I stand on …, and why?"); replies copied into the bench app | 5 | 5 |
| **10 open-book tasks** on task topics, with your current means (chat search, asking Claude or ChatGPT with their memory, notes, your own memory). Per task: a short answer; what you used; whether you reached the original source; confidence and usefulness (1–5). 4-minute cap; "give up" allowed | 30 | 45 |
| Keys shown. Per task: agree; key wrong; or "outdated, I have changed my mind since" | 5 | 5 |
| **Total** | **58** | **73** |

**Session 2, after Northstar** (after the backfill and ≥ 2 weekly editions):

| Module | Typical | Worst |
|---|---|---|
| Introduction | 2 | 2 |
| **Pickup probes (K6), twice:** the same prompts with Northstar off (vendor memory as it is then), then on | 6 | 6 |
| **10 tasks:** 8 with the Book only (the Reader and its search), 2 with your current means as a control; two blocks in random order. During the control block Northstar runs in shadow mode (records, delivers nothing) | 30 | 45 |
| **Relevance labels** ([PR] §7.1): 50 shuffled topics, source hidden, at least 15 seconds each: part of my thinking; useful support; generic. Allocation fixed in the pre-registration: ≥ 25 from Northstar's organized set; ≥ 15 from its background, of which ≥ 10 are background topics with an AI explanation of 120+ words that you replied to (the AI-taught stratum, U10); ≥ 10 found only in the comparators' sets. An overlap is labelled once and counts for every set | 13 | 13 |
| **Three issue pages** ([PR] §7.1, with [TB] §13.5's acceptance read folded in): position right? reasons and objections right? reads like a textbook? easy to understand? | 5 | 5 |
| **Structure check** ([KO] §9.4): 10 placements, 3 subdivisions, 3 consolidations from your Book's edition log: right, acceptable or wrong | 8 | 8 |
| Keys and disputes | 5 | 5 |
| **Total** | **69** | **84** |

### 5.4 Sitting formats (your choice: DQ-14(e), BQ-10)

You allowed short one-off sessions. We do not assume an hour counts as short, so three formats are offered.

| Format | Sittings | Effect on measures |
|---|---|---|
| **A. Four short sittings** (recommended) | Before: **1a** introduction, reference list, probe, 2 tasks (about 29 minutes, at most 32); **1b** within 7 days, 8 tasks and keys (about 29, at most 41). After: **2a** introduction, probes, 7 tasks, issue pages (about 34, at most 45); **2b** within 7 days, 3 tasks, labels, structure check, keys (about 35, at most 40) | All of §5.3, as planned |
| **B. Two sessions of about an hour** | Before about 58 minutes (at most 73); after about 69 (at most 84) | All of §5.3, as planned |
| **C. Short** | Two sessions of about 30 minutes (at most about 40): a shorter reference list (8 minutes), the probes, **6 task pairs** (5 Book, 1 control) with 3-minute caps, **30 labels** (≥ 15 organized, ≥ 10 background with ≥ 6 in the AI-taught stratum, ≥ 5 comparator-only), keys. Issue pages and the structure check become an optional 10-minute add-on | U1–U5 rest on 5 Book pairs, pre-registered as indicative, so they read "directional" at best; U6, U7 and U10 have wider intervals; without the add-on, U8 and U9 are "not run" |

Total: A or B, about 2 hours (about 2.6 at worst-case caps); C, about 1 hour (about 1.3).

### 5.5 Where this revision's modules fit

- **Relevance (U6, U7, U10)** is [PR] §7's module, with its comparators B1 (the 2026-10-08 rules: glossary, dangling terms), B2 (frequency) and B3 (one model call) and its thresholds. This plan fixes only its place, its label allocation and its verdict rules; at v0's sizes the comparison with B1–B3 is secondary.
- **Structure (U8)** is [KO] §9.4's module: the only real-data misplacement estimate, so indicative.
- **Timing:** every module is budgeted at worst-case caps, and each label gets at least 15 seconds; the format, not squeezed slots, keeps each sitting short (R21, as revised).
- **Pickup (K6)** is [PR] §7.2's "AI picks up your thinking". Unlike K1 it uses your real history. Session 2 runs it twice, Northstar off (your vendor memory as it is then) and on, and K6 is scored against the off run, so months of vendor change cannot pass for an effect; session 1's run is reported as history. You run it, so nobody else sees your memory.
- **Your session-1 list is evaluation data.** It never enters the Book, a pack or any Northstar store.

### 5.6 Blinding and privacy

- Keys are drafted by a local model, checked by code, and shown to you only after you answer.
- **If you are the builder,** you never see the task pool or keys; a script runs the draw; the judge scores your answers; your review settles disputes. **If someone else builds,** they see scores and labels, not your record, keys, answers or real accounts; Part A runs only in the bench accounts.
- **If you are the builder, you also type scripts on your own topics**, which could rehearse the answers to tasks. The topic partition (§5.3) prevents this: scripts use only script topics and tasks only task topics.
- You cannot be blind to the condition. The control tasks and matched pairs carry that weight.
- **Open-book only:** nothing tests unaided remembering (BQ-9), and nothing from your answers enters Northstar.

---

## 6. Measures, and what counts as meaningful improvement

Thresholds compare Northstar with the baseline (§7 says which). A guard must not get worse by more than stated. "Min" is the minimum sample per arm and connector; below it, a cell reads "underpowered".

**Part A, in-session focus**

| ID | Measure | Meaningful improvement | Guard | Min |
|---|---|---|---|---|
| F1 | **Late item errors:** share of item-checks at turns 31–40 whose first reply fails (contradiction, violation, re-proposal, stale; for view items, ignored or contradicted without acknowledgement, §4.6), split by who established the item, you or the AI | ≥ 30% fewer **and** ≥ 5 points fewer, in **each** split ([EV] §2.1's 30% bar) | — | 8 chats; 40 checks per split |
| F1c | Corrected before control returned (hook cells): failing first replies fixed by the one follow-up correction | Reported | — | — |
| F2 | Goal service: share of late task probes rated ≥ 4 | ≥ +15 points | — | 24 probes |
| F3 | Unwarranted flips (turn 26 and P2) | ≥ 50% fewer | No rise | 16 probes; directional at best |
| F4 | Legitimate change handled (pivot at turn 20, revision at turn 38) | — | Not > 10 points worse | 16 probes |
| F5 | Your cost: steps per chat; added time per turn | — | No required step per chat beyond one-time setup (GOAL §4.1); time reported | All runs |
| F6 | **Agreement on contested positions** (P4, P4b, chain t4): replies that endorse your view without engaging its open objection (O1, O1′) | — | Not up > 5 points against the baseline (secondary, pre-registered; [PR] §7.2's 2-point bar stays synthetic, since one reply is about 4 points here) | 24 probes |

**Part A, cross-session continuity**

| ID | Measure | Meaningful improvement | Guard | Min |
|---|---|---|---|---|
| K0 | **First-call gate** (MCP cells): fresh chats that call Northstar before the first reply | Gate ≥ 90%, reported next to K1; a miss is stated with K1's verdict | — | All fresh chats in Phase N (about 32 per chat app) |
| K1 | **Continuity recall:** share of needed items used or recalled correctly without being told. By class: your goals and constraints; your views and reasoning; AI-taught knowledge; AI conclusions; rejected options. Sub-class reported separately: **AI explanations you did not act on** (E2) | ≥ +20 points overall; ≥ +15 points for the AI-said classes and for your views and reasoning | In Phase N, AI-said recall within 10 points of user-said; the "not acted on" sub-class not > 10 points below the baseline | 8 new chats; 40 needed items |
| K2 | Re-explanations needed in turns 1–5 | ≥ 30% fewer **and** ≥ 1 fewer per chat | — | 8 new chats |
| K3 | Stale assertions (V1 stated as current) | ≥ 50% fewer | No rise | 8 new chats |
| K4 | False or intrusive memory (t8; unrelated personal details) | — | No rise > 3 points | 8 new chats |
| K5 | Cross-product recall (optional) | ≥ +30 points | — | 2 chains × 2 runs per direction |
| K6 | Pickup of your real thinking ([PR] §7.2), per desktop app | ≥ +30 points over the Northstar-off run in session 2 ([PR]'s bar) | — | Your list |

**Part B, the human side**

| ID | Measure | Meaningful improvement | Guard | Min |
|---|---|---|---|---|
| U1 | **Answer correctness:** key-point score 0–100, the Book against current means, paired by matched task | ≥ +20 points | No task type > 10 points worse | 8 pairs |
| U2 | Time per task (median; a capped task counts 240 s) | ≥ 40% less | — | 8 pairs |
| U3 | Confidence (1–5); confidently wrong (confidence ≥ 4, score < 50) | Confidence ≥ +0.75 | Confidently wrong not up > 5 points | 8 pairs |
| U4 | Usefulness (1–5) | ≥ +1.0 | — | 8 pairs |
| U5 | Reached the original source | ≥ +25 points | — | 8 pairs |
| U6 | **Relevance precision** of Northstar's organized set ([PR] §7.2–§7.3). Secondary: ≥ 15 points above B1 and B2 at equal or better recall (directional at these sizes) | ≥ 0.80 | — | 25 organized labels |
| U7 | Relevance recall: listed items (from session 1) that appear in the record and are organized in the Book ([PR] §7.2); reported separately for the AI-taught items you listed | ≥ 0.80 | AI-taught recall within 15 points of user-stated (indicative, pre-registered) | Your list |
| U8 | Structure changes judged wrong ([KO] §9.4) | ≤ 15% wrong (indicative; [KO] §9.2's misplacement bar) | — | 16 items |
| U9 | Issue pages: position right; reads like a textbook; easy to understand | ≥ 2 of 3 yes on each (indicative) | — | 3 pages |
| U10 | **AI-taught false negatives:** topics in the AI-taught stratum (background, with a replied-to AI explanation of 120+ words) that you label "part of my thinking" | — | ≤ 20% (indicative, pre-registered) | 10 labels |

**Why these thresholds.** Each is large enough that you would notice it in daily use, and large enough to beat run-to-run noise at these sizes. Smaller real effects may exist. v0 reports them as "no meaningful change", never as "no effect". The fuller bars of [EV] §2 stay as v1 targets (§10).

---

## 7. Handling noise without SWE-level rigor

- **Unit:** the conversation (Part A) or matched pair (Part B). Probes within a chat correlate, so whole units are resampled (cluster bootstrap, 5,000 resamples, 90% intervals).
- **Repeats:** 2 runs per script in the apps, 4 on the CLIs. Multi-turn loss is mostly unreliability, so one run is not a measurement [11 F1]; the spread is reported.
- **Verdicts,** per measure and connector:

| Verdict | Rule |
|---|---|
| Clear improvement | The estimate meets the threshold, and the 90% interval excludes zero |
| Directional | The estimate meets the threshold; the interval includes zero |
| No meaningful change | The estimate misses the threshold; guards hold |
| Worse | A guard is broken, or the interval lies wholly below zero |
| No headroom | The baseline is already near the ceiling (F1 < 10%, K1 > 85%, U1 > 85%) |
| Underpowered | Fewer units than the minimum in §6 |

- **Late baseline:** full-size by default for every connector, because Phase N runs months after Phase B and model versions will almost surely change. **Phase B is the pre-registered baseline and the headroom check.** When versions are unchanged and the two agree (the interval of the difference includes zero and the difference is under half the threshold), they are pooled; otherwise the late baseline alone is the comparison, and Phase B is reported as history.
- **F6 guards F1:** if F6 (agreement on contested positions) rises more than 5 points against the baseline, F1's verdict for items you established reads "worse", whatever its estimate, so echoing your views cannot pass for focus.
- **Session control:** the control-pair gain is reported next to U1 in every case. If the 2 control pairs gain at least half the Book's gain on U1 or U2 (practice, time), the Book's verdict is capped at "directional".
- **Pre-registration:** script hashes, rubrics, thresholds, sizes, the topic partition, the label allocation and analysis, frozen before Phase B. Scripts may change once after the pilot; thresholds never.
- **No pooling across connectors** ("3 of 4 connectors improved" is allowed; one pooled number is not). Secondary measures never claim success alone.

---

## 8. Effort and cost

### 8.1 Your time

| When | What | Minutes |
|---|---|---|
| Before Phase B | Session 1 (two sittings in format A) | about 58, at most 73 |
| Optional | A look at the scenario cards | ~10 |
| After the backfill | Session 2 (two sittings in format A) | about 69, at most 84 |
| | **Total** | **about 2 hours (at most about 2.6); format C about 1 hour (at most 1.3)** |

Nothing else: no ratings in daily use, and Phase N runs with no corrections from you.

### 8.2 Builder hours (±50%)

| Work | Before the build | After the build |
|---|---|---|
| Tools: prompter, bench app, CLI drivers, scoring and report scripts | 20–30 | — |
| Scenario cards and scripts; the pilot | 16–20 | — |
| Task pool and key pipeline (local model) | 8–12 | — |
| Judge setup, calibration and the unblinding check (BM-S4) | 7–11 | — |
| Typed desktop runs: about 7 hours per app per full arm | 14 | 28 (N and a full-size late baseline) |
| CLI supervision (arms B, N, BL, M); bench accounts, Projects and stores | 4 | 8 |
| Spot-checks; analysis and report | 5 | 12 |
| **Total** | **about 75–95** | **about 48** |

**In all: about 125–145 builder hours, about 42 of them typing.** The full-size late baseline is the expected top-up, budgeted here rather than left to chance: the build spans months, so model versions will almost surely change. **If no local judge passes** (BQ-4(a)): about 2,100 checks, about 35–45 more hours. A 40-turn chat takes about 30 minutes with the prompter (about 45 seconds a turn, mostly waiting); a chain about 22 minutes. If you are the builder, the typing and labelling are your time (BQ-5).

### 8.3 API and other costs (±2×)

| Item | Estimate |
|---|---|
| Bench accounts | Your plan's price per vendor for about 2 months of runs (prices Unv) |
| Desktop runs | Inside the bench plans: about 530 messages per app per arm, spread over ≥ 4 days (usage limits Unv; the pilot measures them) |
| CLI runs | The bench plans, or about $270–330 on API keys for arms B, N, BL and M |
| Judge | Local; no API cost; hardware hours sized by BM-S4 |
| Northstar in Phase N | About 2,500 turns, arm M included, at $0.025–0.04 a turn (from ARCH §0's estimate): $60–100 |
| Backfill of your record | Same rate; 5,000 turns cost about $125–200. The Book needs it anyway |
| Comparators B1–B3 ([PR] §7.3) | About $20–60 |
| **Total API** | **About $250–650**, less if the CLIs run on the bench plans |

### 8.4 What is automated

**Automated:** CLI runs, reply capture and timing, quote checks, judge scoring, task and key drafting, schedules, statistics and the report. **Manual by design:** typing in the desktop apps (vendor terms; UQ-22), Project and store setup, spot-checks, your two sessions.

### 8.5 A Lite option

3 chat scenarios × 1 run; the code track and arm M at 1 scenario × 4 runs; a late baseline at the same size, since versions will likely change over the build. About 60–70 builder hours. Only large effects can show, so most cells would read "directional" at best (BQ-5).

---

## 9. Data and consent

- **Stays on your machines:** cards, scripts, transcripts, the export, tasks and keys, your answers, judge outputs and reports, in a bench folder, encrypted at rest without Northstar code: BitLocker or Device Encryption on the bench machine, or an established encrypted container for the bench folder (DQ-5(a), DQ-14). Northstar's own store encryption (SP-PF-4) is not needed for Phase B.
- **Leaves, as in normal use:** scripted chats go to Claude and ChatGPT in the bench accounts. In Phase N, Northstar's worker calls, the backfill and the comparators follow DQ-3(a). No new recipient.
- **The repo** holds code, templates, synthetic examples and the pre-registration without topic text; a numbers-only summary only with your yes.
- **Afterwards** the bench folder is kept for v1 or excised on request; the bench accounts can be closed.
- **Consent (BQ-1):** real topics in scripted chats; one local export; local drafting of tasks and keys. For v0 this replaces ARCH DQ-6(b): no vendor-API replay of your chats.

---

## 10. What happens to the previous evaluation plan

| Fate | Previous parts |
|---|---|
| **Kept** | Per-cell reporting ([EV] §1.2), now also per OS. Criterion 4 (goldens, canaries, fault injection, [EV] §2.4) and [TB] §13.2 groups A, F, H, as build gates. [TB] groups C, D (simulated readers) as CI regression |
| **Kept, lighter** | Pre-registration ([EV] §1.1): one v0 file. Family rules ([EV] §1.3): one local third-family judge |
| **Folded in** | D-syn and D-syn-C, as the CLI track. Continuity protocols O and S, as the chains. The cross-surface matrix, partly, as K5. [TB] §13.5, as U9. [TB] group G, partly, as U6 and U7 |
| **Replaced for v0** | [EV] §1.4's statistics, by §7. The bars of [EV] §2.1–§2.3, [IS] §11 and [AC] §11, by §6; they become v1 targets |
| **Deferred to v1** | Protocols A and R (public benchmarks), as regression; B and B-sim, as an API mirror; D-fork; the full cross-surface matrix |
| **Deferred to v2** | Live arms C, D, L (ARCH DQ-6(a)); [TB] group E (re-ask rate) |
| **Superseded** | "No user sessions" ([TB] §13.1; SYN §7), for evaluation only, by your 2026-10-09 answer; still no product routine |

---

## 11. How it grows after v0

- **v0.1, platforms** (order Windows, iOS, Mac). iOS: chains with seeds on Windows and the new chat on the phone, testing "many machines and phones, one memory"; needs [CN]'s iOS route (CN-Q1). Mac: the same scripts.
- **v0.2, rotation.** A third of the scenarios rotate as your topics change; a frozen anchor set keeps trends comparable.
- **v1, depth.** ≥ 8 scenarios per connector; an API mirror with ≥ 8 repeats and curves at depths 10–80; an adaptive simulated user; D-fork; the cross-surface matrix; public regression suites (LongMemEval_S, MemoryAgentBench, PersonaMem-v3); [EV]'s bars and 95% rules.
- **v2, live.** Randomized live arms on your real use (DQ-6(a)); the passive re-ask rate and frontier validity ([TB] E, G).
- **Every release** re-runs the automated parts as regression; typed runs repeat at major releases only.

---

## 12. Limits, stated honestly

- **One user, small samples.** Only large effects show; nothing generalizes to other people.
- **Scripted chats** cannot adapt, and the builder's typing is not your style. Live arms (v2) close this.
- **Equal information** keeps your real history out of K1–K5. K6 covers it, with one probe per desktop app.
- **Vendor changes** between phases are absorbed by the late baseline, not removed.
- **The judge** can err; the quote rule, calibration and spot-checks bound this.
- **Open-book tasks** measure finding, understanding and tracing your thinking, not unaided remembering (TB H1 stays at risk; BQ-9).
- **Part B is small:** 8 Book pairs, 2 controls (5 and 1 in format C), one person who knows the condition.
- **Keys come from the record:** thinking you never wrote down is invisible.
- **The AI's items vary per run,** which adds noise.
- **Not covered:** maintainer correctness, injection and security (build gates); iOS and Mac until v0.1.

---

## 13. Spikes

| Spike | Question | Decides |
|---|---|---|
| BM-S1 | On the Windows apps and your plan tier, do a Claude Project and a ChatGPT project-only Project keep memory and chat search inside, both ways? (Plant a fact inside, probe outside and in a sibling; the reverse; 5 probes each.) **Latency probe:** plant a fact, then probe a new chat in the Project at 1, 3 and 24 hours | Per-run Projects or resets (§4.5); the wait W (§4.4) |
| BM-S2 | On Windows: `claude -p` resumed per turn, and `codex exec` with resume, each with hooks firing and a per-run home (extends [EV] L13) | The CLI driver |
| BM-S3 | Do the Claude and ChatGPT exports hold both sides, timestamps, conversation IDs and Projects? Where are local Claude Code and Codex transcripts on Windows? | Task pool; backfill input |
| BM-S4 | Which third-family open-weight model passes judge calibration on your hardware, at what speed? | The judge, or BQ-4 |
| BM-S5 | Does each Windows app's copy button give the reply exactly, without tool-call text? | Prompter capture |
| BM-S6 | Once connectors exist: does a late-baseline sitting produce zero Northstar calls? | Late-baseline validity |

---

## Supersedes

| File | Section | What changes |
|---|---|---|
| [ARCHITECTURE.md](../ARCHITECTURE.md) | §10 | The first evaluation is this benchmark. §10's protocols move to v1 and v2 (§10 here). "Whether the Book reads well to you" is measured in session 2 |
| ARCHITECTURE.md | §11; §0 "Cost and effort" | Session 1 and Phase B run before Stage 0b, after DQ-14 (including (c)), DQ-2, DQ-5(a) and bench-folder encryption, not after design approval. The benchmark adds about 125–145 builder hours and $250–650 of API (backfill included), outside the stages' builder-weeks. Stage 5 opens with Phase N; "your optional read" becomes session 2 |
| ARCHITECTURE.md | §14 DQ-6 | (a) Live arms deferred to v2, asked then. (b) For v0, replaced by BQ-1: a local export, no vendor-API replay |
| ARCHITECTURE.md | §15, rows GOAL §4.8, §6.1–§6.3 | First evidence: v0 verdicts per connector and for the human side |
| [evaluation-and-build-plan.md](../components/evaluation-and-build-plan.md) | §0 items 1–4; §2.1–§2.3 | v0 is the first evaluation. The protocols are kept, folded in or deferred per §10 here; their bars become v1 targets |
| evaluation-and-build-plan.md | §1.1, §1.4 | For v0: one pre-registration frozen before Phase B (no per-family recalibration), and §7's statistics (90% intervals, verdict scale, late baseline) |
| evaluation-and-build-plan.md | §1.5, §1.6 | New rows. Session 1 and Phase B need DQ-14 (including (c)), DQ-2, DQ-5(a) and bench-folder encryption without Northstar code, not design approval. Claims: Part A can claim an in-app effect per connector on your topics, not your natural use; Part B can claim usefulness to you, not unaided recall |
| evaluation-and-build-plan.md | §3.2, §3.3, §3.5 | Adds a separate Northstar install on the bench machine with a fresh store per run, arms N and BL, the prompter and the bench app |
| evaluation-and-build-plan.md | §5.1 Stage 5, §5.4, §6 | Stage 5 opens with Phase N; costs add §8 here; "built and evaluated" adds a v0 report with a verdict per connector and for the human side |
| [TEXTBOOK.md](../foundations/TEXTBOOK.md) | §13.1 first bullet; §13.4 second paragraph | "No required user sessions" becomes two one-off evaluation sessions (your 2026-10-09 answer); still no product routine and no unaided recall test. Whether the Book reads like a textbook to you is measured in session 2 |
| TEXTBOOK.md | §13.5 | Folded into session 2 (U9): 3 issue pages instead of 5 pages and a chapter opener, judged with [PR]'s position check |
| [ai-in-session.md](../components/ai-in-session.md), [ai-continuity.md](../components/ai-continuity.md) | §11 | Their metrics feed v1; v0 uses F1–F6 (with F1c) and K0–K6 |

[PR] §7, [KO] §9.4 and [CN] §8 are adopted unchanged; this plan fixes only their place in the sessions and their verdict rules.

---

## Open questions for the user

| ID | Question | Recommendation |
|---|---|---|
| BQ-1 | **Consent:** your real topics in scripted chats (bench accounts only), one local export of your chats, local drafting of tasks and keys. No person but you sees the record. The v0 form of ARCH DQ-6(b) | **Yes.** It is the only way to measure on your real topics; the data stays on your machines |
| BQ-2 | **Accounts and vendor memory:** (a) bench accounts, one per vendor on your plan, memory on, isolated per run; (b) your own accounts, a Project per run (needs BM-S1; the typist sees your account); (c) memory off in both phases | **(a):** equal information, your memory untouched and unseen; costs one plan per vendor for about 2 months. (b) only if you type the runs yourself |
| BQ-3 | May session 1 and Phase B start once you approve this plan, before the revised design is approved? This changes GOAL §7's order for evaluation only; it is asked, not assumed. Only benchmark tooling is built | **Yes.** No Northstar code is built, and the baseline exists before the design is final |
| BQ-4 | If no local judge passes (BM-S4): (a) the builder labels everything; (b) a third vendor's API judges, seeing transcripts on your topics | **(a)** at v0 size (about 2,100 checks, about 35–45 hours); (b) only with your explicit yes |
| BQ-5 | Standard (about 125–145 builder hours) or Lite (about 60–70, §8.5)? If you are the builder, the typed runs (about 42 hours) are your time | **Standard;** Lite only if time forces it. A helper may type; nobody automates the apps (UQ-22) |
| BQ-6 | Accept §6's thresholds as the definition of meaningful improvement? | **Yes.** Frozen before Phase B; smaller effects are still reported |
| BQ-7 | Include the cross-product chains (K5)? They need DQ-3(b) yes | **Yes**, if DQ-3(b) is yes; vendor memory cannot do this at all |
| BQ-8 | Session 2: the Book only, or the Book plus your current means? | **Book only.** It isolates the organization; real use combines them |
| BQ-10 | **Sitting format** (§5.4): you allowed short sessions. Does an hour count as short for you? (A) four sittings of about 30 minutes; (B) two of about an hour; (C) short, two of about 30 minutes, with less power | **A:** the full content, each sitting short. C if your time matters more than clear verdicts |
| BQ-9 | **Unaided remembering:** v0 has no closed-book task, so "helps you remember" stays unmeasured (TB H1). A 5-minute closed-book block would test you, which [TB] §13.1 ruled out | **Not in v0.** It touches the "no quiz" spirit, so it is your call; revisit after v0 |

---

## Risks

| ID | Risk | Mitigation |
|---|---|---|
| RISK-BM-1 | Vendor updates between phases fake or hide an effect | The full-size late baseline, the comparison whenever versions changed; K6 scored against a Northstar-off run in session 2; versions recorded; §7's pooling rule |
| RISK-BM-2 | Samples too small for anything but large effects | Large thresholds; the verdict scale; "underpowered" always shown; v1 adds depth |
| RISK-BM-3 | Project isolation leaks (secondary reports describe ChatGPT leakage) or is missing on your plan | BM-S1; verified memory resets; bench accounts keep any leak away from you |
| RISK-BM-4 | Scripted chats are unlike yours | Real topics; your card check; K6 on real history; live arms in v2 |
| RISK-BM-5 | The local judge is weak on your hardware | Calibration; the quote rule; the 20% spot-check; BQ-4 |
| RISK-BM-6 | Typing errors or fatigue | The prompter checks sent text; no improvising; runs spread over days; Lite |
| RISK-BM-7 | Practice, time or task difficulty confound Part B; you are also the builder, typing scripts on your own topics | **The topic partition is the rehearsal control:** scripts use only script topics, tasks only task topics (§5.3). Also matched pairs, random draw, in-session control with its gain reported next to U1, §7's cap; task pool and keys hidden from you |
| RISK-BM-8 | Northstar gets tuned to the benchmark | v0 scenarios are a sealed test set; tuning uses the synthetic golden world; post-result changes re-tested on rotated scenarios |
| RISK-BM-9 | The Book looks relevant by showing little | U7 and U1 count against it; [PR]'s "equal or better recall" rule |
| RISK-BM-10 | Personal data reaches the repo or a new recipient | Topic text only in the local bench folder; a local judge |
| RISK-BM-11 | Usage limits or vendor terms bite | People type; runs spread over days; sanctioned CLI modes; terms for a second personal account (Unv) |
| RISK-BM-12 | Connectors are late on Windows; the AI's items are not cleanly elicited | Per-connector Phase N ("not run" with reason); forced choice, failures counted per phase |
| RISK-BM-13 | Shadow mode or a late-baseline sitting leaks Northstar help | Receipts must show zero deliveries; contaminated runs redone (BM-S6) |

---

## Goal-fidelity check

| GOAL item | How this plan treats it | Status |
|---|---|---|
| §2 (2026-10-09) evaluation: baseline first, comparable, improvement defined, manageable, meaningful, both sides, real topics, short sessions | Phase B before the build; §2's rules; §6; about 2 hours of your time; Parts A and B; your session-1 list | Partial: about 2 hours in four sittings of about 30 minutes or two of about an hour; a short format (about 1 hour, more "directional" verdicts) is offered; whether an hour counts as short is asked (BQ-10) |
| §2 Windows first, then iOS, then Mac; many machines and phones | Windows in v0; iOS chains (seed on Windows, new chat on the phone) and Mac in v0.1 | Partial: iOS and Mac planned |
| §2 Connectors by effectiveness | Per-connector verdicts with [CN] §8's diagnostics; arm M compares MCP-only with hooks on the CLIs; the K0 first-call gate | Met by design; on chat apps product and mechanism cannot be separated |
| §2 Structure evolves both ways; personal relevance | U8 (indicative); U6, U7, K6 | Partial (U8 is a small sample) |
| §3.1, §4.2 Both sides; AI-said first-class | AI-said items scored separately (F1, K1 and its "not acted on" sub-class); a parity guard; U7's AI-taught split; U10 | Met by design |
| §3.2 Textbook: understand, remember, what to learn, sources; no quiz | U1–U5, U9; T3, T4; open-book only. Unaided remembering not measured (H1; BQ-9) | Partial |
| §3.3, §4.5 Focus and continuity, equally | F1 and K1, each primary, same rigor | Met by design |
| §3.4, §4.7 Robust maintainer | Not measured here; [EV] §2.4's build gates stay | Unchanged |
| §4.1 No rituals; §4.3 the AI manages it | One-off evaluation sessions; Phase N with zero corrections; F5 reports any step per chat | Met by design |
| §4.4 Two architectures | Parts A and B | Met by design |
| §4.6 Product-agnostic; four connectors; personal accounts | The same scripts on every connector; bench accounts are personal accounts | Met by design |
| §4.8 Built and evaluated; §6 success | v0 is the first evaluation; criteria 1–3 baseline first; criterion 4 stays with the build gates | Planned |
| §5 Constraints | Sycophancy F3 (flips) and F6 (agreement on contested positions); staleness F1, K3; injection: build gates only | Partial |
| §7 Order; reframing | Plan stage only. Phase B before design approval changes GOAL §7's order for evaluation only and is asked (BQ-3, DQ-14(c)); BQ-9 puts the "remember" versus "no quiz" tension to you. No reframe adopted | Checked |

---

## Facts checked for this document (2026-10-09)

| Fact | Source |
|---|---|
| Claude Code runs natively on Windows 10 1809+ or Windows Server 2019+, from PowerShell or CMD; WSL is optional; the Claude Desktop app exists for Windows | https://code.claude.com/docs/en/setup |
| "Claude creates a separate memory for each project"; incognito chats are not saved to memory; memory reached Pro and Max on 2025-10-23 | https://claude.com/blog/memory |
| Codex runs on Windows natively, in the ChatGPT desktop app, the CLI or the IDE extension, with a native sandbox; WSL is optional; `CODEX_HOME` is named | https://learn.chatgpt.com/docs/windows/windows-sandbox |
| The ChatGPT desktop app runs on Windows ([CN] N10) | https://learn.chatgpt.com/docs/app |
| Claude memory: the current experience "saves memory … as you chat"; under the legacy experience "This synthesis is updated every 24 hours"; "Each project has its own separate memory space" | https://support.claude.com/en/articles/11817273-how-does-claude-s-memory-work |
| ChatGPT project-only memory: OpenAI's help page returned 403 today; only secondary sources (for example TechRadar) describe it, some reporting leakage | **(Unv)**, BM-S1 |
