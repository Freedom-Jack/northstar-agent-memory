# Round-2 synthesis: inputs for the Northstar architecture

Written 2026-10-07.

**Status.** This note is decision input for the architecture. It makes a choice only where the evidence settles it, and those places are labelled **Decisive**. [`docs/GOAL.md`](../../GOAL.md) overrides this note. Where the evidence shows that part of the goal is infeasible or risky, the gap is recorded as a **RISK** (§8). The goal itself is not changed.

**Where this note sits in the process** (GOAL §7: research → design → review → user approval → build). This note is research output. The design built from it goes to review and then to the **user-approval gate**. The §9 questions are answered at that gate, and nothing is built before it. No §9 answer is assumed because the user did not reply.

**Sources and conventions.**
- **Round-2 notes** (in `round2/`): [10] integration surfaces, [11] in-session drift, [12] knowledge structure, [13] robust maintenance, [14] memory-layer landscape.
- **Round 1:** notes [01]–[09], and the round-1 synthesis [S1]. Only [S1]'s findings are used; its reframing is superseded.
- **Numbers** are quoted from the notes and keep their labels: (vendor), (secondary), and (Unv) for unverified.
- **Product facts** are as of 2026-10-07.

---

## 1. The goal

Quoted verbatim from `docs/GOAL.md`.

> ## 3. What we are building
>
> A **memory system**: an architected product, not a practice. It has these parts.
>
> 1. **A shared knowledge core.** It captures conversations **on both sides**: what the user said and what the AI said, told or taught. Over time it can take in other sources such as reading and work. It keeps knowledge structured, attributed (who said it, and where it came from) and evolving, without destroying history.
> 2. **The human architecture: a structural memory.** A navigable structure the AI maintains, covering:
>    - **what has been learned**, from the user's own thinking and from what AIs taught;
>    - **what to learn**: goals, gaps, open questions, next steps.
>
>    The user browses it and can correct it. Any human routine is an optional way of using it, never a requirement.
> 3. **The AI architecture: a memory system for AI assistants** that goes beyond memory files. It serves the following, **equally weighted**:
>    - **In-session focus.** In a long chat, the AI's answers keep serving the user's goal. They don't drift away from what was already established, whether the user or the AI established it.
>    - **Cross-session continuity.** A new chat starts with the relevant goals, knowledge and conclusions from earlier work, without the user re-explaining.
> 4. **AI-managed maintenance that holds up against its own attention loss.** The AI does all capture, structuring, consolidation and reorganization. The maintainer can itself lose focus, so the architecture must make maintenance reliable and checkable. It must not depend on one agent staying attentive.
>
> ## 4. Non-negotiables (the WHAT)
>
> Agents may not change any of these. If evidence shows one is infeasible or risky, **flag it explicitly as a risk for the user**. Do not silently replace it with something else.
>
> 1. **It is a system.** The product is software architecture. It must deliver value without requiring the user to do regular review sessions, journaling or rituals.
> 2. **AI-said knowledge is first-class.** What the AI explained or taught is part of the memory, attributed as AI-said. Memory is not limited to the user's own statements or commitments.
> 3. **The AI manages it.** Automatic capture, structuring and reorganization are the default. Human correction is available, never required.
> 4. **Two architectures, one human-facing and one AI-facing**, over a shared core. Their representations may differ.
> 5. **The AI side addresses both in-session drift and cross-session continuity.**
> 6. **Surfaces:** Claude.ai and ChatGPT web first, then the desktop apps and Claude Code.
> 7. **The maintainer is robust:** maintenance must stay correct even when an individual agent loses focus.
> 8. **We build and evaluate a working prototype.**

Two other parts of GOAL.md also bind this note:
- **§2, the user's answers:** both AI aims weigh equally; the web comes first; the map covers both what was learned and what to learn; the AI reorganizes and the user may correct it; the human interface is the design's call.
- **§6, the success criteria:** these are the rows of §2 and the targets of §7.

---

## 2. Feasibility by requirement and surface

**Legend.**

| Term | Meaning |
|---|---|
| **CAN** | Met |
| **PARTIAL** | Met in part, or only under conditions |
| **CANNOT** | No mechanism found |
| **ext** | With a Northstar browser extension, which is ToS-grey (RISK 1) |
| **sanct.** | With sanctioned channels only: MCP connector or plugin, MCP Apps, instructions, exports |

Evidence comes from [10] (matrix and adapter table), [11] F12 and [14] F4–F6.

**Table A: requirements that depend on the surface**

| Requirement | claude.ai web | chatgpt.com web | Claude Desktop chat | ChatGPT Desktop, Chat mode | Claude Code (incl. Desktop Code tab) | Codex; ChatGPT Desktop local Work/Codex threads |
|---|---|---|---|---|---|---|
| Capture user-said, verbatim (§3.1) | ext **CAN**: post-turn DOM or page-JSON read. sanct. **PARTIAL**: MCP paraphrase; verbatim only from a user-triggered export, which is backfill only because a recurring export is a user ritual (§4.1, RISK 19); none for Team/Ent members | ext **CAN**. sanct. **PARTIAL**: plan-gated MCP paraphrase; verbatim only from a user-triggered export that takes up to 7 days (backfill only, RISK 19) | **PARTIAL**: live, only an MCP paraphrase; verbatim later from the server-stored chat (inference, Unv) or an export | **PARTIAL**: as Claude Desktop chat | **CAN**: `UserPromptSubmit.prompt` | **CAN** (Work threads Unv) |
| Capture AI-said, verbatim, near real time (§4.2) | ext **CAN**. sanct. **CANNOT** live: the model paraphrases itself; verbatim only through user-triggered exports (RISK 19) | ext **CAN**. sanct. **CANNOT** live; with a read-only plugin (AD17) there is no live capture at all; verbatim only through user-triggered exports (RISK 19) | **CANNOT** live; **PARTIAL** later | **CANNOT** live; **PARTIAL** later | **CAN**: `Stop.last_assistant_message` | **CAN**, same hook (transcript format unstable) |
| Deterministic per-turn focus injection (§3.3) | ext **CAN**. sanct. **PARTIAL**: tools the model chooses to call; MCP App context after a first tool call (persistence Unv); static instructions decay | ext **CAN**. sanct. **CANNOT–PARTIAL**: plugin picked in each chat; hidden context not on classic chat | **PARTIAL** at best: model-pulled; MCP App (Unv) | **CANNOT–PARTIAL** | **CAN**: `additionalContext`, up to 10k chars | **CAN**: developer context |
| Check each reply and correct drift (§3.3) | ext **PARTIAL**: reply is judged after display, and the fix rides the next pin or an optional badge; weaker than Claude Code's `Stop` hook (RISK 20). sanct. **CANNOT** | ext **PARTIAL** (RISK 20). sanct. **CANNOT** | **CANNOT** live | **CANNOT** live | **CAN**: `Stop` hook, up to 8 continuations | **PARTIAL**: forced continuation Unv |
| Survive vendor compaction; consolidate and restart (§3.3) | **PARTIAL**: compaction is uncontrollable; state kept outside the transcript is re-injected; ext opens a fresh chat with a resume pack automatically (AD12; spike S11) | **PARTIAL**: truncation undocumented | **PARTIAL** | **PARTIAL** | **CAN**: `PreCompact` / `PostCompact`; `SessionStart` on compact, clear and fork | **CAN**: `SessionStart` on compact |
| New chat starts with prior goals, knowledge and conclusions (§3.3) | ext **CAN**: auto-insert. sanct. **PARTIAL**: boot line plus `northstar_resume`; MCP prompt | ext **CAN**. sanct. **PARTIAL–CANNOT**: plugin selected in each chat | **PARTIAL**: model-dependent | **PARTIAL–CANNOT** | **CAN**: `SessionStart` | **CAN** |
| No per-chat user action (§4.1, §4.3) | ext **CAN** after a one-time install. sanct. **PARTIAL**: per-chat toggle and approvals; "Always allow" exists; default-on Unv | ext **CAN**. sanct. **CANNOT**: `@` in each chat; write approval in each conversation | **PARTIAL** | **PARTIAL–CANNOT** | **CAN** | **CAN**, after hooks are trusted |
| Reachable on the user's plan or account (§4.6) | ext: any plan, if install is allowed. Connector: Free (1), Pro, Max. **Team/Ent: only an Owner adds connectors, and members cannot export** | ext: any plan. MCP: Business/Ent/Edu certain; Plus/Pro sources conflict; Projects reported broken; memory may be off | As claude.ai; a local `.mcpb` needs no public HTTPS | As web | Any plan | Any plan; hooks need trust review |
| Independent ground truth for the capture audit (§4.7) | ext **CAN**: page JSON vs DOM, plus export. sanct. **PARTIAL**: export only | ext **CAN**; export up to 7 days | **PARTIAL**: after the fact | **PARTIAL**: export | **CAN**: transcript vs `last_assistant_message` | **CAN** |
| Measure drift against the same chat without Northstar (§6) | **PARTIAL**: ext shadow mode; ext paired-branch probe gives a same-chat comparison per sampled turn only (spike S9); API replay with the published Claude.ai system prompt; about 30% run-to-run noise. A whole-chat same-chat comparison inside the app is not available (RISK 21) | **PARTIAL**: as claude.ai, with lower replay fidelity (no published prompt) (RISK 21) | **PARTIAL**: replay only | **PARTIAL**: replay only | **CAN**: hooks switched on and off at random | **CAN** |

**Table B: requirements that do not depend on the surface**

| Requirement | Feasibility | Mechanism and evidence |
|---|---|---|
| §4.1 System, no rituals | **CAN** | Code and model jobs do all maintenance; correction is optional [13]. Surface caveats are in Table A |
| §4.2 AI-said is first-class in the core | **CAN**, given capture | Every assistant span is kept as a passage, and statements are extracted from both sides [12][13] |
| §4.4 Two architectures, one core | **CAN** | One canonical ledger. The human map and the AI packs are separate compiled projections [12][14] |
| §6 Map of what was learned (self and AI), with sources and next steps | **CAN** | "What has been learned" is content: the knowledge the user stated or concluded and the knowledge AIs taught (Statements and Passages), each with its sources and speaker and verification chips. The core holds all of it [12][13]. Goals, questions and the frontier cover what to learn. Estimating *mastery* is a separate, optional addition the user may ask for (Q6); it is not part of this requirement. Chats alone cannot support it (error of 21 on a 0–100 scale) [12 F10], see RISK 8 |
| §4.7 and §6 Errors bounded, detectable, correctable | **CAN** for structural errors. **PARTIAL** for semantic errors | Invariants eliminate provenance, quote, speaker and instruction-promotion errors. Stance and supersession errors are only bounded statistically [13]. RISK 6. Verifier independence without a second vendor is RISK 18 |
| §4.8 Working prototype | **CAN with the extension; PARTIAL with sanctioned channels only** | A mechanism exists for every part of the first prototype slice (P1, §6.1) on claude.ai and chatgpt.com. Nothing is built yet: the repo is an empty Python ≥3.14 uv scaffold and API keys are still to be added. Without the extension, P1 cannot capture AI-said text live on the web (RISKS 1, 19) |

**Reading the matrix.**
- **With the extension**, both web-first surfaces meet all of Table A, except that correcting a reply before display (RISK 20) and a whole-chat, same-chat measurement inside the app (RISK 21) stay PARTIAL.
- **With sanctioned channels only**, claude.ai is PARTIAL on most rows and CANNOT capture AI-said text live. chatgpt.com does worse. Verbatim AI-said text would then arrive only through exports the user has to trigger again and again, which is a ritual under GOAL §4.1. Exports therefore count as backfill only, never as a path that meets the requirement. These are RISKS 1 and 19. They are not a reason to narrow the goal.
- **Desktop chat surfaces stay PARTIAL** whatever is built, unless MCP App context proves to persist (RISK 4).
- **Claude Code and Codex meet every row** through hooks. That makes them stronger than the web on per-reply correction. The web-first order still holds (GOAL §4.6), and the gap is RISK 20.

---

## 3. Findings by component

### 3.1 Shared core

**Evidence**
- **How shipped memory systems fail** [13][12][03]:
  - Omission: update omission is above 50%, against hallucination of 1.15% or less.
  - Misattribution: 43–55% of distractors the assistant introduced end up stored as user facts.
  - Lost assistant content: Zep scored 17.7% lower on questions about what the assistant said.
  - Corruption by rewriting: merge clustering scored 48.4% against 78.4% for raw RAG, and ACE shrank 18,282 tokens of context to 122.
- **What fixed it was append-only, deterministic and verified updates** [13]. Examples: Mem0's ADD-only extraction (vendor); Zep's deduplication on identity keys; TrustMem, which cut omission by 40.1%, corruption by 79.1% and hallucination by 50.0%.
- **Supersession is the field's weakest point** [14][03].
  - Multi-hop consolidation reaches at most 28% for any method, and 2–7% for memory systems.
  - Outdated stance persists in 25.7–51.4% of cases.
  - Stores that resolve updates when they write score 0.70–1.00.
- **Statements, raw text and origin** [12][S1][13].
  - Statements with metadata and ranks beat entity triples.
  - Keeping raw text as the value, with facts as index keys, gave +9.4% recall@k.
  - Origin must be bound when an item is written: laundering reached attack success of up to 1.000, and 0% when origin was bound.

**Mechanisms**
- **Layers** [13]: immutable sources, then an append-only ledger of typed events, then deterministic views. LLM outputs are recorded and never regenerated.
- **Item roles:** Concept, Statement, Passage and Agenda. Finer kinds emerge as tags.
- **Attribution is split into separate axes** [12][10]:
  - speaker, taken from the adapter's role;
  - stance;
  - verification;
  - capture fidelity: verbatim, model_reported or reconciled.
- **AI teaching is a Passage**: a verbatim span, a gist and `explains` links. Its checkable claims are children of the passage, never replacements for it.
- **Every item is anchored to a span**, and the anchor is source-generic, so the core can take in other sources later (GOAL §3.1: "reading and work"). An anchor is `{source_type, source_id, locator, quote, prefix, suffix}`.
  - For chats, the locator is the surface, conversation, message ID and branch path, plus the model and a browsing flag.
  - For documents, web pages, notes or work artifacts, the locator is a URI or file hash plus a page or character range.
  - The speaker axis already has `external source`. Capture fidelity, origin binding (I20) and J0 normalization apply to every source type in the same way.
  - The first prototype ingests chats only. Its golden set still includes one non-chat source, to show that the core and the map accept it with no schema change (§6.1, §7.4).
- **Supersession is resolved at write time**, with a reason. Packs see only the best rank.
- **Tensions are resolved automatically** (AD19). The AI does all consolidation (GOAL §3.4), and the user's correction is never required (§4.3). A conflict is therefore never left waiting for the user. J5 proposes, and code applies the resolution in this order:
  1. **Scope check.** If the two items differ in a qualifier (version, date, context or population), both stand, linked by scope. Most apparent contradictions are absorbed this way [12].
  2. **Explicit supersession signals**, applied at write time with a recorded reason:
     - the user's later statement about their own goals, decisions, preferences or plans supersedes their earlier one;
     - an AI self-correction in a later span ("I was wrong earlier") supersedes the earlier AI-said item, `reason: ai_self_correction`. A reversal that directly follows user pushback with no new evidence may be a sycophantic flip (models flip 46% of the time when challenged [11 F4]). It goes to the margin rule (step 4) instead of superseding directly;
     - a `contradicted` result with evidence, from a verifier of a different family than the speaker, supersedes an AI-said claim, `reason: verifier_contradicted`;
     - a user correction, which is optional, overrides any of these, `reason: user_correction`.
  3. **Ranking when there is no explicit signal.** Code computes the rank from the recorded axes; no model decides it. The order is:
     - verification status (supported, then mixed, then unchecked or not-checkable, then contradicted);
     - the number of independent lineages, with an AI echo counted once (I11);
     - grounding (spans with browsing or tools rank above ungrounded ones);
     - recency of valid time, for time-sensitive facts.

     Speaker is not a ranking factor for claims about the world, so AI-said knowledge is not demoted. Speaker decides only for items the user holds about themselves.
  4. **Margin rule.** If the rank margin is below a threshold calibrated on the golden set, code first sends the Tension to search-grounded verification by a different family, then re-ranks on the result.
  5. **Contested residue.** If the evidence is still balanced, or the claim is not checkable (opinion or advice), the item is marked `contested`.
     - Both sides are shown with attribution in the map and in packs, for example: "Claude said A on 12 Sep; ChatGPT said B on 3 Oct; unresolved".
     - A Question is spawned on the what-to-learn side. This records a real gap in knowledge; it is not a task for the user.
     - Re-ranking runs automatically on any new evidence or re-check date.
     - The count and age of contested items are monitored (§7.4). How many cannot be resolved automatically is RISK 22.
  6. **Safety.** A resolution is a high-risk event: invariants, a verifier from a different family, and a 100% L4 audit. Both sides stay visible; the outranked side is kept with its reason. Every resolution can be undone with a compensating event, and A→B→A oscillation is monitored.
- **One schema serves session and long-term scope.** About 36K events a year fits in SQLite [11][12][13].

### 3.2 Human structural memory

**Evidence**
- **No product exists for this.** None links "what to learn" to what was learned [14].
- **Mastery cannot be read from chats** [12 F10]. This matters only for the optional mastery estimate (Q6). The requirement, a map of what was learned with its sources, is built from content the core already holds.
  - The best estimate is off by 21 points on a 0–100 scale.
  - LLM learner models update in the wrong direction.
  - LLM labelling plus classical tracking does work.
- **"Ready to learn" has a formal definition but noisy inputs.** It is the outer fringe of a prerequisite structure, but LLM prerequisite extraction reaches only F1 70.2–76.2, and reversed direction is a main error [12 F11].
- **Gaps and learner models.** Questions the user asked and never resolved are the best free signal of a gap [12 F12]. Open learner models keep the learner's beliefs and the system's beliefs separate [12 F13].
- **Concept maps help less when they are only studied:** g = 0.58 overall; 0.72 when the learner builds the map, 0.43 when they only study it [12 F14].
- **Graphs and hierarchies** [12 F4, F15, F16].
  - Global graph views lack evidence, and turn into a hairball near 10k notes. Trees, local graphs, source-linked mind maps and time cues do have evidence.
  - Automatic hierarchies work (Clio: 94% against 5% for random), but they drift between rebuilds.
  - The upper levels of GraphRAG and RAPTOR summarize summaries; in RAPTOR, 4% of summary nodes were hallucinated.

**Mechanisms**
- **A learning map compiled over the ledger** [12]:
  - concepts that can have several parents;
  - **what has been learned**, which is the content itself: what the user stated or concluded, and what AIs explained or taught (Statements and Passages, including the verbatim AI passages). Each item shows its sources, with speaker and verification chips;
  - prerequisites proposed by an LLM, with a separate check on their direction;
  - a Question/Claim/Evidence layer;
  - per-concept engagement states (encountered, explained-to, asked-about, used, restated, confused), derived by code from events. These are an extra signal on each concept and are shown as "how you engaged". They do not redefine "learned".
- **What to learn** has four parts:
  - stated goals, kept apart from inferred interests, which decay;
  - open questions, taken from the user's unresolved questions and from conflicts;
  - the frontier, the outer fringe of the subgraph relevant to a goal;
  - ranked next steps.
- **Pages are compiled from leaf items only.** Every sentence cites a leaf, uncited sentences are rejected, and entailment is spot-checked.
- **Reorganization is stable and reversible.** IDs are stable, clustering pays a stability cost, and every reorganization is a typed event that can be undone. Merges are reversible aliases.
- **Views:**
  - goals with a frontier of 4–7 items;
  - a topic tree;
  - concept pages with speaker and verification chips;
  - a gap map, a timeline and open questions.

  There is no global graph by default [12][13][14].
- **User corrections are optional, and once made they persist** (GOAL §3.2, "can correct it"). Nothing waits on a correction.
  - A correction is a typed ledger event with holder `user` and origin bound as user-typed (I20). It can target an item, a relation, a label, a parent or a merge. Kinds: fix the attribution; fix the content (a new item that supersedes the old one, `reason: user_correction`); reject a relation; fix a placement ("must be under" or "must not be under"); rename; unmerge; hide.
  - The user can correct with one click in the human view, or in chat through an MCP write.
  - **Precedence (proposed invariant I21).** No automated event may undo or contradict an active user correction.
    - J8 reorganization takes corrections as hard constraints: must-link and cannot-link pairs, fixed parents and fixed labels.
    - J7 page rebuilds and deterministic view rebuilds replay corrections after clustering, so a correction survives every rebuild.
    - A correction is lifted only by the user, or by excision of its target.
  - If later evidence conflicts with a correction, the correction stands and the conflict is shown as a chip. It is not escalated to the user.
  - Corrections also become L6 labels (§3.5). Correction survival is a hard gate in §7.3.

### 3.3 AI in-session focus

**Evidence**
- **Long chats lose reliability more than ability** [11 F1]. Multi-turn chats score 39% lower: aptitude falls 16% while unreliability rises 112%, and about 30% unreliability remains even at temperature 0. One consolidated prompt (CONCAT) keeps 95.1%.
- **The transcript itself misleads the model** [11 F2–F3]:
  - premature answers (30.9 vs 64.4);
  - answers bloated by 20–300%;
  - neglected middle turns;
  - self-conditioning on earlier errors.

  Length alone costs 13.9–85%, instructions drift within 8 rounds, and content at the end of the context fares best.
- **What the AI established holds worst** [11 F4]. Version editing averages about 38.5, against 81.96 for recalling user facts. Challenged models flip their answer 46% of the time.
- **Models violate constraints they can restate** [11 F5][14].
  - Rates run from 8% to 99% depending on the model.
  - 74% of drift cases break a constraint by turn 2.
  - Checkpoints only cut non-compliance from 54% to 47%.
  - Compaction raised violations from 0% to 30%, and up to 59% for some models. Constraints pinned outside the compacted text stayed at 0%.
- **What helps, and by how much** [11 F6]:
  - RECAP recovers 44–52% of the loss; SNOWBALL recovers 18–31%;
  - a correction that names the specific behaviour cut drift by 87%, against 35–38% for re-injecting the instructions;
  - adaptive timing added nothing.

  Vendors use the same lever: Anthropic's `long_conversation_reminder` (Opus 5.5 system prompt, 2026-09-22).
- **Rebuilding beats appending.** Rebuilding from external state beats an append-only history in agent work. Web compaction is opaque, telling a pivot apart from drift is unsolved, and no existing product targets drift on these surfaces [11 F7–F10][14].

**Mechanisms** [11][13][10]
- **Session Ledger**: event-sourced, branch-aware JSON kept outside the transcript. It holds:
  - the goal stack;
  - constraints, which only the user can set;
  - items established by the user or by the AI, each with its reason and the user's reaction;
  - assumptions, open questions, rejected options and artifact versions.
- **Session Steward** (fast lane): an isolated call that sees only the ledger and the last two turn pairs, and emits typed operations. Validators enforce three rules:
  - every operation cites a verbatim span;
  - goals and constraints come only from user spans;
  - AI spans can create only `by: ai` items.
- **Context Composer**, at the end of each user turn:
  - a **pin** on every turn, about 80–150 tokens: goals, must-follow constraints and any pending correction. When the budget allows, it also carries the latest established decisions from either speaker;
  - a **card** on triggers, up to about 600 tokens: relevant items and items from the middle of the chat, assumptions, open questions and rejected options.

  Both are worded as attributed facts and labelled as Northstar state.
- **Items the AI established count from the turn they are made** (AD10). Fast-lane items from either speaker reach the pin, the card and the Drift Checker straight away, labelled "provisional, AI-said" or "provisional, you said". Slow-lane verification gates only their promotion to the long-term core. A provisional item is dropped from the next pin when the user rejects it or the AI corrects itself. This matters most for what the AI established, because that is what holds worst [11 F4].
- **Drift Checker**: deterministic checks first, then embeddings, then an isolated judge for each item. It covers items established by either speaker, provisional ones included. It produces specific corrections that cite item IDs.
- **Goal-Change Handler**: classifies each user turn before drift is judged, so that only user turns move goals.
- **Fork/Rebuild from the ledger**, never from the transcript. It runs automatically on every surface where it can (AD12). In Claude Code it runs at `SessionStart`. On the web, the extension opens a fresh chat with the resume pack and carries over the pending message (spike S11). The old chat stays available. If S11 shows the web path cannot be automatic, that is RISK 20.
- **Audit**: re-derives the ledger from raw transcript windows every K turns.

### 3.4 AI cross-session continuity

**Evidence**
- **No cross-surface continuity exists today.** Each vendor's memory stays inside that vendor. Claude's memory import is a one-shot paste that takes about 24 hours, and ChatGPT has no bulk import [14 F1–F2]. For this user, cross-session continuity is really *cross-surface* continuity: claude.ai, chatgpt.com and later Claude Code.
- **Vendor memory serves the user side only.** Claude memory stores topics about the user. ChatGPT's chat-history context surfaced only the user's messages, not the assistant's. User-centric extraction lost 17.7% on questions about what the assistant said [14 F1][03]. What the AI taught is therefore exactly what vendor memory does not carry into a new chat.
- **Retrieval must be goal-directed** [14 F3, F10].
  - Goal-directed selection beats goal-agnostic compression.
  - Similarity search misses goals stated early (LoCoMo-Plus), so goals need explicit links.
  - Agentic file search scored 72.5%, against 48.5% for RAG.
- **Supersession must already be resolved in the pack** [14 F11]. Memory layers score 2–7% on multi-hop consolidation, and outdated stance persists in 25.7–51.4% of cases. The model must not be left to choose among versions.
- **Small budgets win, and more memory can hurt** [14 F12][11 F11][07].
  - 2K tokens beat 32K-token histories; about 300 relevant tokens beat about 113K.
  - Memory raised sycophancy by up to 45%.
  - Third-person framing cut sycophancy by up to 63.8%.
- **The standard tests cover only part of this** [14 F13]. LongMemEval_S *single-session-assistant* is the only standard test of remembering what the assistant said. No benchmark measures re-explanation, so Northstar measures it itself (§7.2).

**Mechanisms**
- **One compiler (J9)** builds the chat-start pack, the resume pack and the maintainer charter [13].
- **The core pack** is deterministic, about 1.5–3k tokens [12][14][07]. Its contract has these slots:
  - active goals;
  - **relevant knowledge**: user-stated knowledge and AI-taught passages linked to the active goals. Each is given as a gist plus its passage ID, with speaker and verification chips. The verbatim passage is included when the budget allows, and otherwise is fetched by ID (`northstar_fetch`). This slot is part of the contract, because GOAL §3.3 names "knowledge". It is not left to the optional retrieval layer (AD13);
  - conclusions, with who established them (user or AI) and their verification status;
  - open questions;
  - rejected options, marked "do not re-propose";
  - disputed AI claims, marked "do not re-assert";
  - contested items, with both sides attributed (§3.1);
  - **recent provisional items**: what was established in the last sessions on any surface and not yet verified by the slow lane, labelled "provisional". A chat started ten minutes after another one ends would otherwise miss everything from it;
  - engagement state.

  It carries current items only, with IDs and as-of dates, and never inferred stances. AI-said and user-said items compete for the budget on relevance alone; speaker is not a filter.
- **A goal router** reads the first message and drives retrieval over explicit goal→item links, within a hard budget. It matches against open goals from every surface.
- **Cross-surface continuity by construction.** The core is vendor-neutral. The compiler renders the same item set for every surface, and each item carries the surface and model it came from. A chat on chatgpt.com starts with what was established on claude.ai, and the reverse. Nothing depends on either vendor's memory. When the consolidate-and-restart path runs (AD12), it can open the new chat on either vendor. It uses the same resume pack either way.
- **Continuity is checked from the first turn.** The pack's items enter the new session's ledger as established items. The Drift Checker (§3.3) runs from turn 1, so a re-proposed rejected option, a re-asserted disputed claim or a contradicted conclusion gets the same specific correction as in-session drift.
- **A re-explanation detector** flags early user turns that restate goals, knowledge or conclusions the core already holds. Each hit is a miss by the pack and feeds the §7.2 metric. It also feeds retrieval tuning, never a user prompt.
- **Delivery** uses each surface's strongest channel, with context receipts recording what was delivered. On the web the extension inserts the pack automatically. Without the extension, the pack depends on a boot line and the model calling `northstar_resume` (Table A). Vendor memory keeps personalization, and anything taken from it is recorded as assistant-asserted [10][S1].

### 3.5 Robust maintainer

**Evidence**
- **Errors compound in long-lived agents** [13 F1–F2].
  - Self-correction in the same context is weak: models miss 64.5% of their own errors.
  - Anthropic calls rule-based feedback "the best form", and LLM-as-judge "generally not a very robust method".
- **Independent checking has limits** [13 F3, F5].
  - Verifiers share errors (CAPA), so a verifier from the same family as the worker is not independent. With only Anthropic keys, this is RISK 18.
  - Semantic entropy misses errors a model makes consistently.
  - Statistical guarantees need labelled calibration data.
  - Memory reuses its own errors: contagion appeared at 20% contamination.
- **API guarantees are narrow** [13 F6–F8].
  - Structured outputs guarantee syntax only.
  - Non-default temperature is rejected, so outputs are recorded rather than regenerated.
  - Codex's memory pipeline is a production template.
  - Injection detectors fall to adaptive attacks more than 90% of the time.
- **Cost** [13 F11]: about $12 a month at 20 turns a day, up to about $40 at 100, using the Batch API (±2×).

**Mechanisms** [13][10]
- **Decisive: the orchestrator is code.** A SQLite job table with leases, idempotency keys, an outcome enum, backoff, watermarks and single-writer locks. No LLM picks jobs, writes, or judges invariants.
- **Workers are stateless functions.**
  - Their input is assembled by code, with the job card last.
  - Their output is a schema-constrained proposal.
  - They have no network, no writes and no delegation.
  - A failed job is retried in a fresh call, possibly on another model.
- **Two lanes.** The fast lane (JF) writes only provisional, session-scoped state, from both speakers. That state steers the live chat at once (AD10) and is carried into the next chat's pack labelled "provisional" (§3.4). Only verified items from the slow lane (J0–J11) reach the long-term core.
- **An independent verifier family, as the working assumption** (AD9; Q4, pending the user's answer). Extraction and the steward run on Anthropic models. L2 verification, J4, and the evaluation judge run on a local open-weight model of a different family, on this Mac. This needs no second vendor key, and no data leaves the machine for verification. A local model is weaker at judging [11 D2], so it must pass a calibration bar on the golden set first (spike S10). If it fails, §4.7 independence and the §7 bars cannot be certified without a second vendor key (RISK 18).
- **Twenty code invariants (I1–I20)** from [13], plus the proposed I21 (correction precedence, §3.2). They include:
  - the speaker is set by construction;
  - endorsement requires user evidence;
  - no non-user text is promoted to an instruction;
  - the ledger is append-only;
  - origin is bound at write time.
- **Verification is tiered by risk:**
  - L0: invariants, on 100% of items;
  - L1: self-consistency;
  - L2: a verifier in a fresh context;
  - L3: a calibrated cascade;
  - L4: a daily audit by the strongest model;
  - L5: golden and canary sets;
  - L6: optional user corrections, used as labels.
- **Recovery requires no human ritual:**
  - omission sentinels;
  - error-budget freezes;
  - compensating rollback;
  - quarantine as a holding state with automatic exits, not a review queue (below).

  Capture is audited against watermarks. Tool calls made by the chat model are treated as untrusted input.
- **Quarantine has automatic exits, so it is neither a review queue nor silent omission.** It holds *derived proposals* only. The source span, and for AI-said content the verbatim Passage captured by J0, is never quarantined. It stays searchable and is shown with an "uncertain" label wherever it is relevant [13]. A quarantined proposal leaves by one of these routes, all run by code:
  1. **Re-verification**, first by a fresh worker from a different family, then by the strongest model in the next daily L4 audit.
  2. **Time-boxed re-extraction** of the whole source window, with more context (±N turns), by a fresh worker on another model. This is capped at 3 attempts within 7 days (proposed, calibrated on the golden set).
  3. **Re-run after a fix.** When a prompt or model change that fixes the cause passes the canaries, every quarantined proposal in the affected windows is re-run.
  4. **Final disposition.** The proposal is either released as a normal event with its verification record, or discarded with a typed `discarded` event and a reason. Discarding removes only the derived proposal, never the passage or span.

  **Sentinels:** quarantine size and age (an alert when any item is older than 7 days or the pool grows week on week); the AI-said share of quarantine against its share of all proposals, because a skew toward AI-said content is an alert (§4.2); and episodes whose proposals are all quarantined, which count as omission-sentinel hits and are re-extracted by a second model. The user may look, or correct, but never has to.
- **Assume any single call can lose focus.** Structural correctness never depends on one call. Semantic correctness is bounded and measured (RISK 6).

### 3.6 Surface adapters

**Evidence** (details per surface are in §2) [10]
- **Claude.** One remote MCP connector covers web, Desktop, mobile, Claude Code and Cowork.
  - Limits: about 150k characters per result and 240 s per call.
  - MCP Apps' `ui/update-model-context` is the only sanctioned way to change context. It starts after a first tool call, and whether it persists is unverified.
  - In Claude Code, hooks cover both sides of every turn. Prior art: claude-mem, with about 97.8k stars.
- **ChatGPT.**
  - Plugins are picked in each chat, and writes are re-approved in each conversation.
  - Plan eligibility conflicts across [10], [11] and [14].
  - Hidden-context Extensions cover only Work and desktop.
  - Custom GPTs retire on 2026-12-11.
- **Browser extensions.**
  - They work through the page itself; Mem0's was archived on 2026-03-23.
  - Manifest V3 cannot read response bodies, so capture means reading the DOM or patching `fetch` in the MAIN world.
  - Safari needs an Xcode wrapper.
  - Both vendors' terms prohibit automated extraction. No enforcement was found, but that is absence of evidence, not permission.

**Mechanisms**
- **Adapter contract.** Each adapter has a control channel (MCP or plugin) and a fidelity channel (hooks or extension). Either may be missing on a given turn, and which ones were present is recorded [10][13]. The contract is source-generic: chat adapters are one kind of source adapter. Document, web-page, note and work-artifact adapters can later plug into the same J0 normalization and anchor format (§3.1) without a schema change.
- **One public MCP server**: Streamable HTTP, OAuth, `northstar_*` tool names, truthful `readOnlyHint`, few write tools. It ships as both a Claude plugin and a ChatGPT plugin.
- **The extension has two modules** [10][12]:
  - post-turn verbatim capture, covering branches, model, the AI's citations, paste detection, and skipping Incognito and Temporary chats;
  - injection, visible by default, with a shadow mode.

  The injection module also drives automatic consolidate-and-restart (AD12, S11) and the paired-branch measurement probe (S9).
- **One focus anchor**, rendered per channel: a target of about 1.5k tokens, under 10,000 characters [10][14].

---

## 4. Key architecture decisions and their options

Each decision has a status:
- **Decisive:** the evidence settles it.
- **Leaning:** the evidence favours one option without settling it.
- **Open:** not yet settled.

**AD1. Web capture and steering.**
- **Options:**
  - (a) an extension as the fidelity channel, an MCP plugin as the control channel, and exports as a one-off backfill of past history;
  - (b) the plugin plus exports;
  - (c) exports only.
- **Evidence:** only (a) captures AI-said text verbatim and injects on every turn. MCP capture is the model paraphrasing itself, and it fades in long chats [10][11][14]. Under (b) and (c), verbatim AI-said text arrives only when the user triggers an export, again and again. claude.ai exports are manual, with none for Team/Ent members, and ChatGPT exports take up to 7 days. That is a recurring user action, which GOAL §4.1 forbids, so (b) and (c) do not meet §4.1 or §4.2 (RISK 19). Exports are backfill only, never the path that meets the requirement.
- **Status: Decisive** that capture must be deterministic and that MCP is never the record. Whether to use the extension is the user's call (Q1, blocking). Q1 spells out what declining it costs.

**AD2. Extension capture method.**
- **Options:**
  - read the DOM after streaming;
  - fetch the page JSON after each turn, which gives branches and IDs but is the most ToS-exposed;
  - tee the live SSE stream, which is the most fragile.
- **Status: Leaning** toward a post-turn read. Spike S4 decides between DOM and JSON.

**AD3. Web injection.**
- **Options:** a visible composer block; an invisible request rewrite; MCP App context only.
- **Evidence:** placing context at the end of the turn works. Visible blocks may be absorbed into vendor memory. Persistence of MCP App context is unverified [10][11].
- **Status: Open**, leaning toward the visible block. Spikes S2 and S6 decide.

**AD4. Hosting.**
- **Options:**
  - a cloud core;
  - a local core behind a tunnel;
  - a local core plus a thin, always-on MCP relay;
  - local only, which gives up web MCP.
- **Evidence:**
  - web MCP needs an endpoint reachable from the internet;
  - laptops sleep;
  - a cloud core holds a copy of every chat;
  - a TLS-inspecting proxy may sit on the path;
  - the extension and hooks work with a local core [10][14].
- **Status: Open** (Q4, blocking).

**AD5. Canonical store.**
- **Options:**
  - (a) an owned SQLite ledger (Model A), with a compiled learning map (Model C) and a derived index;
  - (b) Graphiti or Hindsight as the core;
  - (c) SQLite with FTS5 and embeddings, as the baseline.
- **Evidence against (b)** [12][14]:
  - −17.7% on questions about what the assistant said;
  - "new wins" invalidation;
  - summaries rewritten in place;
  - re-ingestion required to retype;
  - no deletion path (LightRAG);
  - churn.
- **Status: Leaning strongly** toward (a). Retrieval tests pick the index.

**AD6. Attribution schema.**
- **Choice:** independent axes plus capture fidelity, with the speaker set by the adapter.
- **Status: Decisive.** One enum conflates stance with correctness. A speaker set by a model reproduces 43–55% misattribution [12][13].

**AD7. Promoting AI-said content.**
- **Options:** every sentence becomes a statement; all spans are kept as passages and promoted selectively; salience-filtered retention.
- **Status: Leaning** toward the middle option, gated by the AI-said recall probe (§7.2).

**AD8. Maintainer shape.**
- **Options:** a code orchestrator with stateless workers, or an agent.
- **Status: Decisive** for code [13]. Leaning toward SQLite jobs over Temporal or DBOS.

**AD9. Models for steward, judge, extractor and verifier.**
- **Options:** the chat model through tool calls; same-vendor API tiers; a cross-vendor verifier; local models.
- **Status:** the chat model as maintainer is **ruled out (Decisive)**: it misses 64.5% of its own errors and shows know-but-violate. The rest is **Open** (Q4, blocking). The golden set picks the tiers.
- **Working assumption, pending the user's answer:** Anthropic models for the steward and extractor; a local open-weight model of another family as verifier and judge, so independence does not need a second vendor key (§3.5, spike S10). A same-vendor tier as the only verifier does not count as independent (CAPA). If the local model fails its calibration bar, the §4.7 and §4.8 bars cannot be certified without a second family (RISK 18).

**AD10. Fast-lane influence on pins, cards and the Drift Checker.**
- **Options:**
  - (a) immediate for items from either speaker, labelled provisional with the speaker;
  - (b) only after slow-lane verification.
- **Evidence:**
  - focus needs state about one turn fresh, and the slow lane takes about 2 h [13];
  - what the AI established holds worst: version editing scores about 38.5 against 81.96 for user facts [11 F4];
  - GOAL §3.3 covers items "whether the user or the AI established it".

  An earlier draft proposed a hybrid in which AI-said items waited for the slow lane. It is withdrawn, because it would leave most long chats without the AI's items in the pin, the card or the drift checks.
- **Status: Leaning** toward (a). Session-scoped items from either speaker steer the live chat at once, labelled "provisional, AI-said" or "provisional, you said". Slow-lane verification gates only promotion to the long-term core. Goals and constraints still come only from user spans (I5). That is an injection rule, not a weighting of AI-said knowledge: AI-established decisions, facts and artifact versions are steered on just like the user's. Protocol B (§7.1) tests (a) against (b), scoring AI-established and user-established items separately.

**AD11. In-session injection shape.**
- **Options:** a pin plus a card on triggers plus specific corrections; a full card every turn; triggers only.
- **Evidence:** SNOWBALL (18–31%) did worse than RECAP (44–52%); specific corrections cut drift 87%; adaptive timing gained nothing [11].
- **Status: Leaning** toward the first. Protocol B tunes the sizes.

**AD12. Consolidate and restart.**
- **Options:** automatic; one ignorable suggestion; off.
- **Evidence:** the strongest lever (95.1%), but it breaks the thread.
- **Status: Leaning** toward automatic on every surface, with the same behaviour on the web and in Claude Code.
  - In Claude Code it runs through hooks (`SessionStart` on clear or fork).
  - On claude.ai and chatgpt.com the extension opens a fresh chat, inserts the resume pack and carries over the pending message. Spike S11 tests this.
  - The old chat stays available, and the user never has to use the new one.
  - If S11 shows the web path cannot be made automatic, the web-vs-Code gap is RISK 20, not a weaker default.
  - The user's preference is Q7.

**AD13. New-chat pack.**
- **Options:** core pack only; plus a goal router and hybrid retrieval; plus standing briefs; agentic search.
- **Status:** the core pack with explicit goal links and write-time supersession is **Decisive** [14]. Its knowledge slot (user-stated knowledge and AI-taught passages) is required by GOAL §3.3, so it is part of the pack contract and not optional (§3.4). The retrieval layer beyond the pack budget is **Open**, tested head to head (§7.2).

**AD14. Verifying AI-taught claims.**
- **Open questions:** which claim kinds; search over private content; verifier family; re-check cadence.
- **Status: Open.** What is **Decisive** [12]: verification is its own axis, never upgraded by acceptance or repetition.

**AD15. Human surface.**
- **Options:** an Obsidian-compatible vault; a local web app; a published artifact page; MCP Apps panels.
- **Evidence:** trees, outlines and timelines beat global graphs. Don't build an editor [12][02].
- **Status: Open**, leaning toward one primary view plus an in-chat slice.

**AD16. Vendor memory.**
- **Options:** on; off where Northstar runs; scoped via Projects.
- **Status: Open** (Q5). Evaluation runs both arms.

**AD17. ChatGPT write path.**
- **Options:** approvals in each conversation; or a read-only plugin, with writes going through the extension and hooks. Never a false `readOnlyHint`.
- **Status: Leaning** toward read-only, *if the extension is accepted*. If it is declined (Q1), a read-only plugin leaves chatgpt.com with no live capture at all. Writes would then need approval in each conversation, which is a per-chat user action (§4.3). Q1 states this.

**AD18. Build sequence.**
- **Options:** extension first; plugin first; or core and evaluation harness first, with the web adapters as the first adapters.
- **Fixed by GOAL §4.6:** the first evaluated prototype (P1, §6.1) targets claude.ai and chatgpt.com.
- **Question for the user (Q8, blocking):** may a Claude Code hook adapter be built *before* the web adapters, as a full-fidelity test bed for the core and the harness? This note does not assume it may. Until the user answers, the web adapters come first, and the Claude Code adapter follows the evaluation of P1.
- **Status: Open** on the coding order inside P1.

**AD19. Tension resolution.**
- **Options:** (a) automatic resolution by the ordered rules in §3.1, with a contested state for real residue; (b) Tensions left open until the user settles them.
- **Evidence:** stores that resolve updates when they write score 0.70–1.00. Memory systems that leave consolidation open score 2–7% on multi-hop consolidation [14]. GOAL §3.4 gives consolidation to the AI, and §4.3 says correction is never required. Option (b) would be a hidden review queue and would pile up fragments (brief, foundation 2).
- **Status: Leaning** toward (a). The rules are code over recorded axes (verification, lineage, grounding, recency, explicit self-correction and verifier results). They are reversible and audited. User correction stays an optional override. Residue that cannot be resolved is RISK 22.

**Spikes to run before the design freezes.**

| Spike | Question |
|---|---|
| S1 | Account facts: Team/Ent seat, connector access, ChatGPT plan, whether Developer mode turns memory off, whether connectors are on by default |
| S2 | Whether MCP App context persists across turns and reloads, and its size limit |
| S3 | How often the model calls `northstar_focus` unprompted over 40 turns |
| S4 | Extension capture vs exports on 20 chats; whether install is allowed; TLS-proxy effects, if a proxy is present |
| S5 | Whether Codex hooks run in Work threads, and whether `Stop` can force a continuation |
| S6 | Whether visible blocks get absorbed into vendor memory |
| S7 | Citations vs structured outputs for J3; model tiers |
| S8 | A pilot of protocol B, to size the effect |
| S9 | Paired-branch counterfactual on the web: on a sampled turn, can the extension get the vanilla reply to the same message in the same chat (through the vendor's edit or retry branch) and switch the visible branch back? Measure branch side effects, quota use and vendor-memory leakage |
| S10 | Local open-weight verifier and judge on this Mac: catch rate on the golden set, false-accept rate on wrong-but-on-topic negatives (bar: under 10%), latency and memory use |
| S11 | Extension-driven consolidate and restart on claude.ai and chatgpt.com: open a fresh chat, insert the resume pack and carry over the pending message with no user action; also whether a flagged reply can be followed by an automatic correction turn |

---

## 5. Constraints carried over from round 1 (on HOW)

I-numbers are the code invariants in [13].

1. **Attribution.** Speaker, holder and stance are separate fields, and assistant claims default to "encountered". Rationale the AI infers is never stored as the user's own; it matched the real rationale with a precision of only about 0.27 [S1]. *Enforced by* I3, I4 and paste detection.
2. **Provenance.** Every item resolves to an immutable span, and quotes are exact substrings (I1, I2). Origin is bound at write time (I20). Capture fidelity and context receipts are recorded.
3. **Supersede, never overwrite.**
   - Append-only storage (I6); typed supersession with reasons and ranks; deprecated items kept as antibodies.
   - Valid, recorded and held time are tracked separately, and as-of queries are supported.
   - Conflicts become typed Tensions and are never resolved *silently*: there is no hidden pick and no lost side [S1][12]. They are resolved *automatically* by the ordered, reversible rules in §3.1 (AD19). The outranked side stays visible with its reason. A disagreement between AIs also spawns a Question on the what-to-learn side. Only real residue stays `contested`, and it is monitored (RISK 22). User correction is an optional override, never the resolution path.
4. **Never summarize summaries.** Pages, briefs, packs and resume packets come from leaf items only (I7–I10, I18). In-session, the system rebuilds from the ledger, never from the drifted transcript.
5. **Count lineages.** A derived item never supports itself, and an AI echo counts once (I11).
6. **Context rot.** Context is small, scoped, labelled, and placed at the end of the window: the pin is about 80–150 tokens, the card at most about 600, and the core pack about 1.5–3k.
7. **Sycophancy.**
   - Claims are attributed and phrased in the third person, never as identity statements.
   - Packs contain no inferred stances, and disputed AI claims are marked "do not re-assert".
   - AI-said items are revised on evidence, not on pressure. The evidence may be an AI self-correction, a verifier result, a source with more independent lineages, or new evidence from the user. User pushback without evidence is recorded as stance (`disputed`, so the pack says "do not re-assert"). It does not change the verification axis.
   - Flips are measured.
8. **Injection.**
   - Only text the user typed can create instructions, goals or constraints (I5).
   - Injected blocks are delimited facts that never imitate vendor tags.
   - Workers follow the Rule of Two, with each episode isolated, and red-team tests run in CI.
   - The extension gets minimal permissions and holds no secrets in the MAIN world.
9. **Privacy and excision.**
   - A deterministic secret and PII scan runs before any model call.
   - Sensitivity tiers and scopes (I17) gate packs, exports and verifiers.
   - Incognito and Temporary chats are skipped, and capture is limited to an account allowlist.
   - Excision is started by the user, reaches every derived store, and leaves a tombstone; a grep afterwards returns 0 hits [S1 FR28][06].
   - What a vendor already received cannot be recalled, and Claude memories survive deletion of the chat [10].
10. **Formalize incrementally.** Four roles to start, with further kinds emerging as tags. There is no taxonomy for the user to maintain and no required fields.

**Superseded by GOAL §4.1 and §4.3:**
- the review queue (FR19);
- the review-time stop line (NFR2);
- the review experiment (E4);
- routing stance changes to review (T4, T7);
- the weekly signature test.

Their error-catching job moves to the verification layers, error budgets, quarantine with automatic exits, automatic Tension resolution, and optional corrections, which are used as labels.

---

## 6. Build vs reuse

| Need | Candidate | Pros | Cons | Leaning |
|---|---|---|---|---|
| Canonical core | Own SQLite ledger + FTS5; embeddings as a cache | Nothing else has the attribution, AI-said or what-to-learn semantics; small scale | Build effort | **Build** |
| Retrieval index | Graphiti (Apache-2.0) | Both roles; raw episodes; bitemporal; hybrid + graph | Graph-DB server (Kuzu deprecated); LLM-heavy; user-centric | Optional, behind an interface |
| | Hindsight (MIT) | Facts vs experiences; 4-way recall with token limit | Young; benchmarks reported by its authors; machine "observations" | Test |
| | Mem0 OSS | Mature; ADD-only | 2% on multi-hop consolidation; 51.4% outdated stance | Baseline arm |
| Orchestration | SQLite jobs + Python (Codex pattern); Temporal/DBOS | Simple and local; durable | Temporal/DBOS heavier | SQLite |
| Write protocol | Anthropic memory stores and Dreams; Letta MemFS | Versions, hash preconditions, consolidation into a new store | Beta or framework-bound | Borrow the design |
| MCP and in-chat UI | Official MCP SDKs; MCP Apps SDK | Sanctioned; one server for every Claude surface and ChatGPT | ChatGPT support partial | **Reuse** |
| Hook adapters | Claude Code and Codex hooks; claude-mem as reference | Deterministic; documented | Hook APIs evolve | Reuse the platform, build the adapter |
| Web extension | Mem0 extension (MIT, archived); open-source exporters | Shipped auto-augmentation; branch-tree endpoints | Stale selectors (Unv); facts, not turns; undocumented endpoints | Reference; mostly **build** |
| Human-readable view | Basic Memory conventions (AGPL-3.0) | Obsidian-compatible typed notes | AGPL obligations if modified and served | Adopt the conventions only |
| In-session log | Mastra Observational Memory | Only structural in-session design found | Framework-bound; vendor results | Borrow the pattern |
| Hygiene | gitleaks/trufflehog-style scans; Presidio-like recognizers | Solved problem | n/a | **Reuse** |
| Evaluation | `lost_in_conversation` (MIT), MultiChallenge, SYCON-Bench, FlipFlop, PrefEval, LongMemEval_S, LoCoMo-Plus, MemoryAgentBench, PersonaMem-v3 | Public and comparable | None measures the goal | Reuse, plus build our own |

**Summary.**
- **Build what nobody has:** the attributed core, the in-session subsystem, the learning map, the invariant-checked maintainer, and the capture extension.
- **Reuse** protocols, platforms, patterns and benchmarks.
- **Put every dependency behind an interface.** Churn is heavy: Rewind shut down; Mem0's extension was archived; Kuzu was deprecated; Claude memory was re-architected in July 2026 [14].
- **Fit with the repo.** The Python ≥3.14 scaffold suits the core, the maintainer and the MCP server. The extension is a separate JS/TS package. Library support for Python 3.14 is unverified.

### 6.1 First prototype scope (P1)

P1 is the smallest slice that meets all eight non-negotiables on claude.ai and chatgpt.com (GOAL §4.6, §4.8). It assumes the extension is accepted (Q1). If Q1 is answered no, P1 cannot meet §4.2 and §4.5 on the web. The user is told this as RISKS 1 and 19 before the build, and the slice is not quietly redesigned.

| Non-negotiable | What P1 contains |
|---|---|
| 1. A system | All maintenance runs as code jobs and stateless workers. After a one-time install there is no user step. The human view is optional to open |
| 2. AI-said first-class | The extension captures both sides verbatim on claude.ai and chatgpt.com. Every assistant span is kept as a Passage. AI-said recall is probed (§7.2), and quarantine is watched for AI-said skew (§3.5) |
| 3. AI manages it | J0–J11 run automatically, with automatic Tension resolution (AD19) and automatic quarantine exits. Corrections are optional, and they persist (I21) |
| 4. Two architectures, one core | A SQLite ledger with the four roles and the attribution axes. One primary human view (AD15): topic tree, concept pages with chips, goals with the frontier, open questions and a timeline. AI pins, cards and packs compiled from the same ledger |
| 5. Drift and continuity | In-session: Session Ledger, Steward, Composer, Drift Checker, Goal-Change Handler, and automatic consolidate-and-restart (S11). Cross-session: the core pack with its knowledge slot, the goal router, cross-surface continuity and the re-explanation detector |
| 6. Surfaces | claude.ai and chatgpt.com in a Chrome-family browser (pending Q2), through the extension, plus the Claude MCP connector for reads and explicit writes. The ChatGPT plugin is read-only, if Q1 is yes |
| 7. Robust maintainer | Code orchestrator; invariants I1–I21; L0, L2 from a different family (S10), L4 and L5; error budgets; rollback; attention-loss fault injection (§7.4) |
| 8. Built and evaluated | §7.1 protocols A, B and C (with S9); §7.2 offline and live, including cross-surface pairs; §7.3; §7.4 |

**Deferred to later stages.** Each later stage keeps all eight non-negotiables. Stages add surfaces and sources; they never remove a component GOAL requires.
- **P2:** Claude Code and the Claude Desktop Code tab through hooks; Claude Desktop chat through MCP (RISK 4).
- **P3:** ChatGPT Desktop and Codex.
- **P4:** non-chat sources such as reading and work. P1 already carries the source-generic anchor and one non-chat golden fixture (§3.1).
- **Also outside P1:** Safari; a retrieval layer beyond the pack, unless §7.2 selects one; mastery estimation, only if the user asks for it (Q6).

If the user answers yes to Q8, a hook test bed may be coded before the web adapters. P1 is still evaluated on the web.

---

## 7. How to evaluate it

**Ground rules** [11][13][14][S1]
- **Harness first.** Pre-register metrics and bars, recalibrate them once after a pilot, then freeze them.
- **Separate model families** for data, system and judge. Judges must accept fewer than 10% of wrong but on-topic answers (LoCoMo's judge accepted 62.81%).
  - *Without a second vendor key:* the system runs on Anthropic. The judge and the gold-ledger builder are a local open-weight family (S10). Synthetic data comes from a second open-weight family or from public benchmarks. The user's real chats come from Claude and ChatGPT.
  - If the local judge fails the 10% bar, the §7 bars cannot be certified without another family (RISK 18). The note says so rather than lowering the bar.
- **Repeated samples.** Run at least 8 samples per condition and report A90, U90–10 and bootstrap confidence intervals.
- **Matched-budget baselines:**

  | Baseline | Description |
  |---|---|
  | B0 | Full context |
  | B1 | Raw-chunk hybrid retrieval |
  | B2 | Agentic grep plus semantic search |
  | B3 | Oracle |
  | B4 | Dated observation log |

  Each runs with vendor memory on and off. The structure must beat the best of B1, B2 and B4 by at least 10 points on update metrics at an 8K budget.
- **No user sessions.** No metric needs them. User input is optional, one-off consent to use real data. Builder spot-checks happen only during evaluation.
- **Ablation applies to HOW layers only.** Examples: the card on triggers, the embeddings tier of the Drift Checker, L1 self-consistency, the retrieval layer, the goal router. Cut any of these if it moves no metric.
  - A component that GOAL §3 or §4 requires can only be redesigned, never cut. Examples: the what-to-learn side and the frontier; AI-said passages in the map; independent verification; either AI aim; the human view.
  - If no design of such a component meets its bar, it is flagged to the user as a RISK. It is not removed.

### 7.1 Drift in long chats (§6, criterion 1)

**Protocols.**
- **A. Public benchmarks:**
  - a Northstar mode in Laban's harness, compared with FULL, CONCAT, SHARDED, RECAP and SNOWBALL (the bar is to beat RECAP);
  - MultiChallenge;
  - SYCON-Bench and FlipFlop, to check sycophancy does not rise;
  - PrefEval;
  - pivot/refine sets;
  - a compaction scenario.
- **B. Prefix-probe replay** on exported chats at depths 10, 20, 40 and 80. It holds the same chat fixed, but runs through the API, which differs from the app (RISK 12).
  - Arms: vanilla; pin; card plus correction; fork-rebuild. AD10 is tested here: provisional items from both speakers applied at once, against only after verification.
  - Probes: the real next message; consistency probes from a gold ledger, covering both user-said and AI-said items; scripted pushback.
  - A different model family builds the gold ledger.
- **C. Live n-of-1 on claude.ai and chatgpt.com.** This is the primary live protocol, because the web comes first.
  - Injection is on in a random 50% of new chats; the rest are only logged.
  - Within injected chats, the web levers are randomized too: the specific correction carried in the next pin, and automatic consolidate-and-restart (S11).
  - Chats are judged afterwards, plus implicit signals. No ratings are asked for.
  - C compares different chats. For a same-chat comparison inside the real app, the **paired-branch probe** (S9) runs on sampled turns: the extension gets the vanilla reply to the same user message in the same chat, through an edit or retry branch, and switches the visible branch back.
  - Remaining gap: this measures the per-turn effect only, not the whole-chat trajectory, because the user's later turns answer the branch they saw. It also leaves visible branches and uses quota. A whole-chat same-chat comparison inside the app is not available (RISK 21).
- **D. Hook surfaces (phase 2).** The same as C, plus an arm that corrects through the Stop hook. Results from D never stand in for the web results under §6 criterion 1.

**Metrics.** Curves over depth, split into user-said and AI-said:
- goal-adherence AUC and slope;
- violations, including know-but-violate;
- contradictions of established items;
- unwarranted flips;
- version editing;
- premature answers and bloat;
- A90 / U90–10;
- re-explanation rate;
- goal-shift F1 and false alarms;
- steward precision and recall;
- tokens, latency, and $ per 100 turns.

**Bars,** at 40 turns or more [11], on chats from claude.ai and chatgpt.com (protocols B and C):
- at least 30% fewer contradictions than vanilla, met *separately* for user-established and AI-established items (not only pooled);
- adherence AUC at least 25% higher;
- no rise in flips;
- steward precision of at least 95%;
- audit disagreement of at most 5%;
- at most 600 injected tokens per turn.

### 7.2 Continuity across sessions (§6, criterion 2)

**Offline.**
- *Data:* continuation pairs from exports (a one-off backfill, not a recurring export).
  - Same-surface pairs.
  - **Cross-surface pairs:** claude.ai → chatgpt.com and the reverse. Natural pairs are used where the user continued a topic across vendors. Constructed pairs split one chat and continue it on the other vendor's model.
- *Arms:* vanilla; vendor memory; Northstar; Northstar plus vendor memory; B1, B2 and B4.
- *Probes,* written before the build: prior goals; knowledge the user stated; **knowledge the AI taught**; conclusions the user established; conclusions the AI established; rejected options; superseded facts; abstention.
- *Metrics:*
  - continuity recall and precision;
  - **re-explanation rate:** the share of probes in which the simulated user must restate something the core holds;
  - re-proposal of rejected options;
  - stale assertions;
  - **AI-said recall,** scored separately;
  - cross-surface recall, against same-surface recall;
  - over-personalization, and agreement on contested prompts;
  - tokens.

**Live** on claude.ai and chatgpt.com. The pack is randomized on or off per new chat. The metric is re-explanation in the first 5 turns, from the re-explanation detector (§3.4), split by same-surface and cross-surface starts. No ratings are asked for.

**Regression.**
- LongMemEval_S: single-session-assistant, knowledge-update and abstention subsets.
- LoCoMo-Plus.
- MemoryAgentBench FactConsolidation.
- PersonaMem-v3, outdated stance.

LoCoMo headline scores are not used.

**Bars.** These are initial pre-registered bars proposed by this note. Like §7.1's, they are recalibrated once after the pilot and then frozen.
- **Decision rule (round 1, [S1] §9).** The structured design must beat the best of B1, B2 and B4 by at least 10 points on update and belief-evolution metrics (knowledge update, superseded facts, stale assertions) at an 8K-token budget. Otherwise the simpler design wins for that *retrieval layer*. That is a HOW choice: the pack contract and its slots stay.
- **Re-explanation:** at least 30% fewer re-explanations in the first 5 turns than with the pack off, live and offline.
- **Continuity recall** of prior goals, knowledge and conclusions: at least 80%, and at least 10 points above vanilla plus vendor memory.
- **AI-said recall** (AI-taught knowledge and conclusions the AI established): at least 75%, and no more than 10 points below user-said recall.
- **Cross-surface recall:** within 10 points of same-surface recall, in both directions.
- **Re-proposals of rejected options:** at least 50% fewer than vanilla [S1 E10].
- **Stale assertions** of superseded facts: at most 5%.
- **Sycophancy:** no rise in agreement on contested prompts against vanilla (95% bootstrap CI).
- **Budget:** a pack of at most about 3k tokens.

### 7.3 Quality of the human structure (§6, criterion 3)

Every check is automatic unless marked otherwise.

| Check | Measure |
|---|---|
| Provenance completeness | 100% of items resolve to a source (hard gate) |
| Attribution | Accuracy on the golden set; false endorsement at most 5% |
| What-has-been-learned coverage | Share of golden-set knowledge items, user-stated and AI-taught, that appear in the map with their sources |
| AI-said coverage | Assistant explanations reachable from the map; AI-said share against the golden baseline |
| Citation faithfulness | Sampled entailment checks; hedges and rare details kept after N regenerations [S1 E7] |
| Stability | Label and ID churn per week; nodes moved per reorganization; A→B→A oscillation |
| Fragmentation | Duplicate concepts and items against the golden set; size and age of the unplaced pool |
| Correction survival | 100% of user corrections still in force after N rebuilds and reorganizations (hard gate, I21) |
| What-to-learn validity | Precision and direction of prerequisites, against curated sources where they exist; open-question precision; **frontier predictive validity** (proposed): the share of frontier items the user later engages with, against random and popularity baselines |
| Navigability (optional, one-off test) | Time to answer "what have I learned about X, and from whom?" in the view, against searching raw chats |

### 7.4 Maintainer correctness (§6, criterion 4; §4.7)

- **Golden and canary sets.**
  - Built from a hidden world ledger: synthetic personas, plus an optional consented slice of real data.
  - Run nightly and on every prompt or model change.
  - Scored per operation: extraction precision and recall; attribution; false endorsement; update omission; stale assertions; wrong merges; retention of hedges and rare details.
  - Scored for under-merging and fragmentation too, not only over-merging (brief, foundation 2): duplicate rate (active items the golden set marks as one); missed merges; missed supersessions; wrong Tension resolutions.
  - Includes at least one non-chat source (a document), to check that the core accepts it with no schema change (§3.1).
- **Process signals:**
  - invariant violations before validation (zero after it);
  - audit disagreement, which drives the error budget;
  - disagreement between the fast and slow lanes;
  - sentinel hits;
  - **pile-up pools:** the count and age of open and contested Tensions, quarantined proposals and the unplaced pool, plus the AI-said share of quarantine.
- **Attention-loss fault injection** (proposed; tests §4.7 directly).
  - Degrade one worker at a time: a weak model, noisy padding, a missing job card, a prompt bug, shuffled offsets.
  - Measure the share of structural errors blocked (target 100%) and the time until the error budget trips.
  - Check that rollback by job, batch or model rebuilds views that are hash-identical.
- **Drills:**
  - broken selectors trip the watermark alarm within one daily canary cycle;
  - injection canaries never persist;
  - an excision grep returns 0 hits.
- **Bars:**
  - at most 2% audited error on high-risk events over a rolling 7 days;
  - steward precision of at least 95%;
  - audit disagreement of at most 5%;
  - no quarantined proposal older than 7 days;
  - the open-Tension and unplaced pools do not grow week on week once the golden-set stream is stable;
  - duplicate rate at most 5% (proposed, recalibrated after the pilot).

---

## 8. Risks to the goal (ranked)

Risk numbers are stable IDs, used for cross-references throughout this note. The rows are listed in rank order. Risks 18–22 were added by the fidelity audit.

| # | Risk | Threatens | Best known mitigation |
|---|---|---|---|
| 1 | On the web, verbatim capture of AI-said text and deterministic per-turn focus need a browser extension. It is ToS-grey under both vendors' terms and breaks when the UI changes | §4.2, §4.3, §4.5, §4.6 on the web | Two separable modules (post-turn capture; visible injection); minimal permissions; MCP as a labelled, degraded fallback; exports as one-off backfill only (RISK 19); watermarks and canaries; the user decides (Q1, blocking) |
| 19 | With sanctioned channels only, verbatim AI-said capture on the web depends on exports the user must trigger again and again. They are manual on claude.ai (none for Team/Ent members) and take up to 7 days on ChatGPT. That is a recurring user action. With a read-only ChatGPT plugin, chatgpt.com would have no live capture at all | §4.1, §4.2, §4.3 on the web | The extension (Q1). Exports are backfill only and never count as meeting §4.2. If the extension is declined, Q1 tells the user exactly what is lost, and the gap is reported rather than designed away |
| 2 | Account and environment. A Team or Enterprise seat on an employer account would allow no self-added connectors and no self-export. A managed Mac may block extensions, and a TLS-inspecting proxy, if present, inspects traffic. Personal data could end up in an employer-governed store | §4.6; privacy | Spike S1 first; a capture allowlist; a local-first core. Whether to capture an employer account is the user's call (Q3, blocking). If the user's main claude.ai or ChatGPT use is on an employer workspace and that workspace is excluded, §4.6 is narrowed for those surfaces. That is stated to the user, not assumed |
| 3 | Drift reduction on the web may be modest. Know-but-violate runs up to 99%; the best fixes recover about 20–50%; replies cannot be corrected before display; compaction is out of our control | §6 criterion 1 | Specific corrections (−87%); consolidate and restart (95.1%); pinned constraints (0% violation); web levers randomized in protocol C; size the effect early (S8); report results honestly |
| 20 | The web gets weaker drift levers than Claude Code. The `Stop` hook can check a reply and continue it before the user reads it. On the web the reply is judged after display, and the fix rides the next pin. Automatic consolidate-and-restart on the web depends on the extension (S11) | §4.5, §4.6, §6 criterion 1 | A specific correction in the next pin; an optional badge; an automatic correction turn after a flagged reply, if S11 shows it works; automatic restart through the extension (AD12). Web results are reported separately and never replaced by hook results (§7.1 D) |
| 21 | No whole-chat, same-chat comparison is possible inside the real web app. Protocol B holds the chat fixed but runs through the API. Protocol C runs inside the app but compares different chats. The paired-branch probe (S9) compares the same chat per turn only, leaves visible branches and uses quota | §6 criterion 1 ("measured against the same chat without the system") | Triangulate B, C and S9; report each with its fidelity gap; at least 8 samples. Never claim a whole-chat counterfactual inside the app |
| 4 | Desktop chat surfaces have no deterministic per-turn channel | §4.5, §4.6 (phase 2) | MCP App spike (S2); skill plus boot line; capture after the fact; hooks in Code, Codex and Work modes |
| 5 | ChatGPT's sanctioned path is plan-gated and unstable | §4.3, §4.6 | Extension as the primary channel; a read-only plugin if Q1 is yes (otherwise write approval in each conversation, RISK 19); check in S1 |
| 6 | Semantic errors in maintenance can only be bounded statistically, and omission dominates | §4.7, §4.2, §4.5 | Invariants, sentinels, canaries, audits, error budgets, rollback, quarantine with automatic exits and age sentinels, corrections used as labels. Expect measured error rates to understate the real ones |
| 18 | With one vendor's models only, the verifier and judge are not independent. Same-family verifiers share errors (CAPA), and §7 requires separate families for data, system and judge | §4.7, §4.8; §6 criterion 4 | Working assumption: a local open-weight model of another family as verifier and judge. It needs no second key, and no data leaves the Mac. It is calibrated in S10. If it fails the calibration bar, the §4.7 and §7 bars cannot be certified without a second vendor key, and the user is told so (Q4, blocking) |
| 7 | Errors in what the AI taught become authoritative memory | §4.2; §6 sources | Verification axis, including "not checkable"; model and browsing recorded; lineage counting; labels; "do not re-assert"; a verifier from another family (RISK 18); automatic supersession on an AI self-correction or a verifier result (AD19) |
| 22 | Some Tensions cannot be resolved automatically, because the evidence is balanced or the claim cannot be checked (opinion or advice). They stay `contested` | GOAL §3.4 (the AI does consolidation), §4.3; brief foundation 2 (no fragment pile-up) | Ordered automatic resolution (AD19); automatic re-ranking on new evidence or re-check dates; contested items shown with both sides attributed, never hidden; count-and-age sentinels and a non-growth bar (§7.4). Never routed to the user as a task. If the pool grows anyway, that is reported to the user as this risk |
| 9 | Injection and memory poisoning, amplified by per-turn re-injection and by an extension that sees every chat | §3.3; trust | Origin binding; instructions only from the user; quoted data; Rule-of-Two workers; red-team CI |
| 10 | Misattribution of pasted text, restated AI content, or echoes across AIs | §4.2 | Speaker by construction; paste detection; lineage counting; an attribution gate |
| 11 | Interference from vendor memory, including a self-poisoning loop | §3.3 | Labelled blocks; a policy per surface; evaluation arms; spike S6 |
| 12 | Measurement noise (about 30%), and the API differs from the app | §4.8, §6 | Three protocols; at least 8 samples; randomized n-of-1; the in-app gap is RISK 21 |
| 13 | Exposure through a cloud core or relay, a second vendor, or a tunnel | Privacy | Local-first core; a local verifier family as the working assumption (Q4); redaction; scoped packs; excision |
| 14 | Complexity (12 jobs, 6 layers, 21 invariants) and dependency churn | §4.7, §4.8 | A staged build in which every stage keeps all eight non-negotiables (§6.1); ablation of HOW layers only (§7); interfaces; an owned canonical record |
| 15 | Reorganization churn erodes the landmarks the user navigates by | §4.3 vs usability | Stability cost; stable IDs; undoable events; user corrections as hard constraints (I21) |
| 16 | No API keys yet; a lagging steward leaves pins stale | §3.3 | Pin-only fallback from the last validated state; a small fast-lane model; about $12–40 a month |
| 17 | A structure the AI builds helps learning less than one the user builds (g = 0.43 vs 0.72) | No non-negotiable | Inform the user; optional probes |
| 8 | Mastery (how well the user knows an item) cannot be inferred from chats | No non-negotiable. "What has been learned" is the content map, which is CAN (Table B). This bears only on an optional mastery estimate | Offered as an optional addition (Q6), with optional check-yourself probes. Engagement is never presented as mastery |

---

## 9. Questions only the user can answer

> **Answered by the user on 2026-10-08. See [`GOAL.md` §2](../../GOAL.md); GOAL.md wins over this section.**
> - **Q1, the extension:** not required. The first connectors are **Claude Desktop chat, Claude Code, ChatGPT Desktop chat and Codex**. The web is optional. RISKS 1 and 19 now apply only if a web connector is built. The desktop-chat gaps in Table A (RISK 4) become first-priority problems for the design to solve.
> - **Q3, accounts:** personal accounts first, enterprise later.
> - **Q4, data location:** local now, cloud later. Keys and verifier choices are a matter of HOW.
> - **Q6, mastery:** **no.** The human side is a **textbook-like** structure that helps the user understand and remember. RISK 8 is moot.
> - **Q8, build order:** the system is **product-agnostic**. ChatGPT, Claude and other agents are connectors, so the order of connectors is a design decision, not a question for the user.
> - **Q2 (browser), Q5 (vendor memory) and Q7 (fresh-chat handoff)** are left to the design.

Only questions that change the architecture are listed. They are answered at the **user-approval gate** (GOAL §7), before any build.
- **Silence is never taken as an answer.** Each question has a *working assumption*, labelled "pending user answer". It is used only for spikes and design drafts. Nothing ships on it, and it is never recorded as settled.
- **Blocking: Q1, Q3, Q4, Q6 and Q8.** The design cannot pass the approval gate without these answers, because each one accepts a risk or touches the scope of the goal.
- **Non-blocking: Q2, Q5 and Q7.** These tune behaviour. If the user answers "your call", the working assumption is adopted and recorded as the user's choice. Until there is an answer, the behaviour stays a setting, and evaluation runs the options as separate arms.

1. **Browser extension (blocking).** Will you accept a Northstar extension on claude.ai and chatgpt.com? Both vendors' terms prohibit automated extraction, so it is ToS-grey (RISK 1). It is also the only way found to meet §4.2 and §4.5 on the web.
   - *If you decline, you lose the following:*
     - **chatgpt.com:** no live capture of AI-said text. With a read-only plugin there is no live capture at all. A plugin that can write needs `@` and write approval in each conversation.
     - **claude.ai:** AI-said text is captured verbatim only through exports you trigger by hand, again and again, which is a ritual. On a Team/Ent seat there are none at all. Live, there is only the model's own paraphrase through MCP.
     - **Both:** no deterministic per-turn focus injection; no per-reply drift correction; no automatic consolidate-and-restart. The pack at chat start depends on the model calling a tool.
     - **The prototype:** P1 (§6.1) cannot meet §4.2 and §4.5 on the web. This is reported as RISKS 1 and 19, not designed away.
   - *Working assumption (pending user answer):* yes, with post-turn capture, visible injection and a shadow mode, plus a documented fallback that uses sanctioned channels only.
2. **Browser and install rights.** Which browser do you use? If this Mac is managed, may extensions be installed on it?
   - *Working assumption (pending user answer):* Chrome-family first; Safari later, through an Xcode app.
3. **Accounts and plans (blocking).** If you use an employer Claude account, is it a Team or Enterprise seat, and should Northstar capture it at all? Which ChatGPT plan are you on? On which accounts do you mainly use claude.ai and ChatGPT?
   - Suppose your main use is on an employer workspace and it is excluded. Northstar would then not serve those surfaces, which narrows §4.6 (RISK 2). If it is included, work conversations enter Northstar's store, under your employer's terms.
   - *Working assumption, for spikes only (pending user answer):* capture nothing from an employer account until you answer. Spike S1 finds the seat type.
4. **Data location and providers (blocking).** May conversations live in a cloud core or relay? May a second vendor verify claims? Will you add API keys?
   - *Working assumption (pending user answer):*
     - a local canonical core on this Mac;
     - a tunnel or thin relay only for MCP (the exposure is RISK 13);
     - Anthropic models for the steward and extractor;
     - a local open-weight model of another family as verifier and judge, so no second vendor key is needed (S10);
     - a cross-vendor verifier only if you allow it and supply a key.
   - If the local verifier fails its calibration bar, §4.7 and the §7 bars cannot be certified without a second family. You would then choose between a second vendor key and accepting RISK 18.
5. **Vendor memory.** Should vendor memory stay on in chats Northstar manages?
   - *Working assumption (pending user answer):* keep your current settings, label Northstar's blocks, and run both arms in evaluation. If self-poisoning is measured, Northstar proposes turning vendor memory off. It does not change your settings itself.
6. **Mastery estimate, an optional addition (blocking).** The map's "what has been learned" is the knowledge you stated or concluded and what AIs taught you, each with its sources. That is the requirement, and it does not change. Separately: do you also want an estimate of how well you know each item? Chats alone cannot support one (an error of 21 points on a 0–100 scale; RISK 8). It would therefore need optional check-yourself probes, which you could ignore.
   - *Working assumption (pending user answer):* no mastery estimate. The map shows the content with its sources and, as an extra signal, how you engaged with each concept.
7. **Fresh-chat handoff.** When drift thresholds are crossed, should Northstar open a new chat automatically, suggest one, or do nothing?
   - *Working assumption (pending user answer):* automatic on every surface, the web included through the extension (AD12, S11). The old chat stays available. If S11 shows the web cannot do this automatically, that is RISK 20.
8. **Hook test bed before the web (blocking).** May a Claude Code hook adapter be built before the web adapters, as a full-fidelity test bed for the core and the harness? Either way, the first evaluated prototype targets claude.ai and chatgpt.com (§6.1).
   - *Working assumption (pending user answer):* no. The web adapters are built first.

---

## Appendix: goal-fidelity check

| Non-negotiable | Where this note handles it |
|---|---|
| 1. A system | No user rituals; review queues superseded (§5); quarantine has automatic exits (§3.5); Tensions are resolved automatically (§3.1, AD19); exports are backfill only, because a recurring export is a ritual (RISK 19) |
| 2. AI-said first-class | Passage retention; AI-said rows in §2; AI-established items steer the live chat at once (AD10); AI-taught passages in the pack's knowledge slot (§3.4); AI-said bars in §7.1 and §7.2 and AI-said coverage in §7.3; AI-said items revised on evidence, including AI self-correction and verifier results (§5); Risks 1, 7, 10, 19 |
| 3. AI manages it | Automatic pipeline; automatic Tension resolution and quarantine exits; corrections optional and persistent (I21); per-chat user steps flagged in §2 |
| 4. Two architectures | §3.1 core; §3.2 human; §3.3–3.4 AI |
| 5. Drift and continuity | §3.3 and §3.4 at comparable depth, each with evidence, mechanisms and a checker; numeric pre-registered bars for both (§7.1, §7.2); cross-surface continuity (§3.4) |
| 6. Surfaces | P1 and its evaluation target claude.ai and chatgpt.com (§6.1, AD18); a hook test bed comes first only if the user agrees (Q8); the web-vs-Code lever gap is Risk 20; desktop gaps are Risk 4 |
| 7. Robust maintainer | §3.5; an independent verifier family as the working assumption (Q4, Risk 18); fault injection and pile-up sentinels (§7.4); Risk 6 |
| 8. Prototype | P1 scope (§6.1); the spikes; an evaluation-first plan (§7) |

Other GOAL parts: other sources such as reading and work (§3.1) are covered by source-generic anchors (§3.1, §3.6). The user's corrections (§3.2) are covered by the correction mechanism and I21 (§3.2). The user-approval gate (§7) is named in the Status and in §9.

**Where a requirement could be narrowed or is at risk.** This note narrows no requirement. An answer, a working assumption or the evidence could narrow one in these places. Each is tied to a risk or a blocking question:
- Declining the extension leaves the web without live AI-said capture and per-turn focus (§4.2, §4.5): RISKS 1 and 19; Q1.
- Excluding an employer account may remove the user's main claude.ai or ChatGPT surface (§4.6): RISK 2; Q3.
- Verification with one vendor's models is not independent (§4.7, §4.8): RISK 18; Q4.
- The web has weaker drift levers than Claude Code, and automatic restart on the web depends on S11 (§4.5, §4.6): RISK 20; Q7.
- A whole-chat, same-chat comparison inside the web app is not available (§6 criterion 1): RISK 21.
- Some Tensions cannot be resolved automatically (§3.4, §4.3): RISK 22.
- Semantic maintenance errors are bounded only statistically (§4.7): RISK 6.
- Desktop chat surfaces have no deterministic per-turn channel (§4.6, phase 2): RISK 4.
- Building a hook test bed before the web would change the build order (§4.6): Q8, working assumption "no".
- Mastery estimation is not part of the requirement and is offered only as an optional addition: Q6; RISK 8.

---

## Fidelity audit (2026-10-08)

A goal-fidelity audit of this note against `docs/GOAL.md` found drift. These fixes were made in place:
1. **Tensions.** Conflicts are now resolved automatically by ordered, reversible rules, and only real residue stays contested (§3.1, AD19, §5 item 3). AI-said items are revised on evidence, which includes an AI self-correction or a verifier result (§5 item 7). The residue is RISK 22.
2. **AD10.** The hybrid that held back AI-said items is withdrawn. Provisional items from both speakers steer pins, cards and drift checks at once, and only promotion to the long-term core waits for verification (§3.3, §3.5). AI-established items are scored separately (§7.1).
3. **§9 defaults.** Answers by silence are removed. Working assumptions are labelled "pending user answer"; Q1, Q3, Q4, Q6 and Q8 are blocking; the approval gate is named (Status, §9).
4. **"Learned".** It is the content map with sources and is CAN (Table B, §3.2). Mastery is an optional question (Q6), and RISK 8 is rewritten.
5. **Surface order.** The first evaluated prototype targets the web (AD18, §6.1), and a hook test bed first is a question (Q8). Restart on the web is automatic through the extension (AD12, Q7). The web-vs-Code gap is RISK 20, protocol C is web-first, and the appendix is corrected.
6. **Exports.** Exports are backfill only (RISK 19; AD1, AD17, Table A). Q1 lists what declining the extension costs.
7. **Ablation.** It is limited to HOW layers (§7).
8. **Verifier independence.** A local open-weight verifier and judge is the working assumption, pending Q4 (§3.5, AD9, S10). RISK 18 is added.
9. **Quarantine.** Automatic exits and sentinels are specified (§3.5, §7.4).
10. **Continuity.** §3.4 is expanded. Knowledge is a slot in the pack contract (AD13). Numeric bars are set, with the decision rule stated inline (§7.2).
11. **Same-chat measurement.** The paired-branch probe (S9) and RISK 21 are added (§7.1, Table A).
12. **Closing claim.** "No requirement has been narrowed" is replaced by the list above.

**Coverage gaps closed:**
- source-generic anchors for non-chat sources (§3.1, §3.6, §7.4);
- fragmentation metrics (§7.3, §7.4);
- a correction mechanism with precedence, I21 (§3.2, §7.3);
- the P1 scope (§6.1);
- cross-surface continuity and its probes (§3.4, §7.2);
- knowledge in the pack (§3.4);
- the approval gate (Status, §9).

---

## Review revisions (2026-10-08)

The adversarial review of the design set asked for these changes to this note. The full record is [`docs/design/REVIEW.md`](../../design/REVIEW.md).

| Finding | What changed |
|---|---|
| SEC-6 | Device and account facts became generic conditionals; the evidence is kept. AD4 now says a TLS-inspecting proxy *may* sit on the path. Spike S4 measures TLS-proxy effects only if a proxy is present. RISK 2 speaks of "an employer account" and a TLS-inspecting proxy "if present". Q2 asks whether extensions may be installed *if* this Mac is managed. Q3, its working assumption, and the appendix risk line speak of "an employer account". "This Mac" used only as a place (§3.5, S10, RISK 18, the local core in Q4) is unchanged. |
