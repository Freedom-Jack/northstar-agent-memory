# Memory layers for ChatGPT and Claude in 2026, and how a new chat should be given context

Track 14, round 2. Written 2026-10-07. Status: a research note that feeds design. It does not decide anything.
Anchor: `docs/GOAL.md` §3 (all four parts) and non-negotiables 2 (AI-said knowledge is first-class), 5 (in-session drift and cross-session continuity, weighted equally), 6 (Claude.ai and ChatGPT web first) and 7 (a robust maintainer).
Method: I read round-1 notes 03 and 07 first and built on them rather than repeating them. I then checked current product states against primary sources: help centres, official docs, GitHub repositories, arXiv abstracts and full text. OpenAI's help centre and blog returned HTTP 403 to my fetcher, so ChatGPT facts from 2026 come from secondary coverage and are marked as such. Numbers a vendor reports about its own product are labelled vendor-reported. Anything I could not check is marked "(unverified)". Every product fact carries a date, because this field changes month to month.

---

## Questions this track answers (tied to GOAL.md)

1. **What exists** as of October 2026 that gives ChatGPT or Claude memory, or acts as a personal AI memory layer? The scope is vendor memory, extensions and MCP servers, developer engines, and personal-capture tools.
2. **For each:**
   - Does it capture **both sides** (§3.1), and does it keep turns or only extracted facts?
   - How is memory structured?
   - **When** does it inject: at the start, on every turn, or on a tool call?
   - Does it address **in-session drift** (§3.3)?
   - Attribution; human view; hosting and privacy; maturity; open source.
3. **What gap does Northstar fill** relative to §3 and §4, and what can be reused?
4. **Cross-session continuity** (§3.3, non-negotiable 5): how should the system choose what a *new* chat receives? This covers goal-conditioned retrieval, hybrid search, graphs, the profile / episodic / semantic split, budgets and recency.
5. **Evaluation** (§6, non-negotiable 8): what do LongMemEval, LoCoMo and the newer benchmarks measure, and what must Northstar measure itself?
6. **Reuse:** which engines, extensions and patterns could Northstar build on, with honest pros and cons?

---

## Key findings

### Landscape at a glance (state as of 2026-10-07)

| System | Captures (sides; turns or facts; attribution) | Structure | How and when it injects | In-session drift? | Human view | Hosting / OSS / maturity |
|---|---|---|---|---|---|---|
| **ChatGPT memory** (saved memories; chat-history reference; "Dreaming V3" from 2026-06-04) | Synthesized facts about the user. In Sep 2025, chat-history context surfaced **user messages only**. Whether V3 uses assistant turns is unpublished | Saved list plus a self-updating summary. Time-sensitive items are rewritten | **Preloaded** at chat start | None documented. Truncation of the oldest messages is reported (unverified) | Memory Summary: edit, correct, "Don't mention this again". It "will not include everything" | OpenAI cloud; closed; GA. Project-only memory since 2025-08-22 |
| **Claude memory** (+ chat search, projects, incognito, import) | Memory: **user-side topics** (role, projects, style, preferences); sensitive categories opt-in. Chat search: raw past chats, both sides | Since 2026-07 (secondary): individual topic entries written "as they happen", replacing a summary rebuilt every 24 h | Memory carried into new chats (mechanism undocumented). Search is a **visible tool call** | Automatic summarization of earlier messages (code execution on). Keeps chats alive, not focused | Settings → Memory → Topics | Anthropic cloud; closed; GA on all plans. Search on paid plans only; import "experimental" |
| **Claude Code auto memory** | Claude's own notes; kept separate from human-written CLAUDE.md | `MEMORY.md` index (200 lines / 25KB loaded) plus topic files | Index at session start; topic files on demand | Not by itself (hooks allow it; see implication 1) | Plain files | Local; GA. "Auto Dream" seen only in third-party reports (unverified) |
| **Mem0** (2026 algorithm) | Extracted facts; "agent-generated facts … alongside the user's" | Atomic, entity-linked facts; ADD-only since 2026-04-16 | Developer retrieves per turn | No | Dashboard | Apache-2.0, ~66.8k stars; mature. LoCoMo 92.5 / LongMemEval 94.4 (vendor, platform only) |
| **OpenMemory** (Mem0 MCP + extension) | MCP: whatever the model chooses to `add_memories` | Mem0 facts | MCP tool calls. Old extension: **automatic prompt augmentation** on ChatGPT; button or Ctrl+M on Claude | No | Local UI | Local Docker or hosted. Mem0 extension repo (MIT) **archived 2026-03-23** |
| **Supermemory** | Documents and memories extracted from them, linked to source IDs. Extension imports chats on request | Graph with `updates` / `extends` / `derives` and `isLatest`; static + dynamic profile; background "dreaming" | Hosted MCP (`memory`, `recall`, `context`). Extension: **suggestions while typing**, inserted with Tab (2026-07-22) | No | Graph viewer | MIT repo, ~31k stars; local binary or cloud; active |
| **MemoryPlugin** | "Key facts", not full logs; chat-history import | Buckets (Personal, Work, custom) | **Manual** injection button per chat; MCP for Claude Desktop | No | Extension panel | Closed paid SaaS (~$79–$180/yr; sources conflict) |
| **Letta Code** (MemFS) | Agent-written memory; git history | **Git-backed markdown**; root files every turn, `MEMORY.md` tree on demand | System-prompt files plus on-demand reads | Partly: always-loaded blocks; "dreaming" after N steps or at compaction | Desktop memory viewer | Apache-2.0; active. Server features deprecated Mar 2026 (secondary) |
| **Zep / Graphiti** | **Both roles ingested**; raw episodes kept; each fact traces to an episode | Temporal graph: episodes → entities → fact edges with 4 timestamps; custom Pydantic types | Context block per turn (p95 < 200 ms, vendor); Graphiti MCP | No | None built in | Graphiti Apache-2.0, ~31.5k stars; Neo4j / FalkorDB / Neptune (Kuzu deprecated); mature |
| **Hindsight** (Vectorize) | LLM-extracted facts, entities, time; **world facts vs the agent's experiences** | Plus evidence-backed observations and **mental models** (standing answers rewritten offline) | `recall` with a token limit; MCP per bank | No | None noted | MIT, ~46.9k stars; Postgres. LongMemEval 83.6% (20B) / 91.4% (Gemini-3 Pro), authors |
| **Basic Memory** | Only what the AI is told to `write_note`; importers for Claude and ChatGPT exports | Markdown: categorized observations plus `[[wikilink]]` relations | MCP tools pulled by the model | No | **Obsidian-compatible files** | AGPL-3.0, ~4.1k stars; local, or cloud at $15/mo (required for ChatGPT) |
| **Cognee** | Documents, code, conversations | Graph + vectors; ontologies; `remember` / `recall` / `improve` / `forget` | MCP or SDK | No | UI | Apache-2.0, ~31.6k stars; v1.6.1 (2026-09-24) |
| **Mastra Observational Memory** | **Both sides** (user statements, agent actions, tool results) | Dated, prioritized observation log; Observer and Reflector | **No per-turn retrieval**: stable, cacheable prefix | **Yes, structurally**: compresses the live chat at token thresholds | None | Framework (license not checked); vendor research, 2026-02-09 |
| **Anthropic memory stores + Dreams** (Managed Agents API) | Whatever the agent writes; versions attributed to sessions | Path-addressed files; immutable versions | Mounted as files at session start | No | Console | API beta (`agent-memory-2026-07-22`); Dreams in research preview since May 2026 |
| **Recall** (getrecall) | Saved web content, PDFs, videos | Cards, auto-linked graph, **spaced-repetition quizzes** | Chat with saved knowledge; resurfacing while browsing | No | Cards, graph | Closed SaaS with MCP/API; Recall 2.0 (2026-04-14) |

Pieces (on-device workflow memory), Limitless/Rewind (defunct) and Khoj (document search) are covered in finding 9. Sources for each row are under Sources. Star counts were read from GitHub on 2026-10-07.

### 1. Vendor memory converged on an editable, user-centric profile plus raw-chat search. Neither vendor treats what the AI taught as attributed knowledge.

- **Claude** (help centre, read 2026-10-07). Memory saves "a set of individual topics as you chat, rather than summarizing conversations after they end". Every listed category is about the user: role, projects, professional context, people and places, working style, technical preferences. Sensitive categories need an opt-in. Projects get "their own memory space"; incognito chats are neither saved nor searched. Chat search is a separate RAG feature whose searches "appear as tool calls", on paid plans only. Secondary sources date the change from a 24-hour rolling summary to topic entries to 2026-07-10; memory reached free users around 2026-03-02 (Bloomberg Law, via search snippet).
- **ChatGPT.** Two settings: "reference saved memories" and "reference chat history" (since 2025-04; it "doesn't retain every detail"). **Dreaming V3** began rolling out on 2026-06-04 to US Plus and Pro users. It is a background process that rebuilds memory from many chats, shown in an editable **Memory Summary**, which "will not include everything" (OpenAI, quoted by LaunchReady). Internal evals report factual recall of 82.8%, up from 41.5% or 67.9% depending on the outlet (vendor-reported, not reproducible). Since 2025-08-22 a project can use project-only memory. All 2026 ChatGPT details are secondary, because openai.com returned 403.
- **User side only, by design.** Shlok Khemani's reverse-engineering (Sep 2025, via Simon Willison) found that ChatGPT's chat-history context surfaced "only the user's messages … not the assistant's responses". That suits a *profile*, and it is the opposite of GOAL.md §3.1, which requires "what the AI said, told or taught" to be captured and attributed. Claude's chat search reaches both sides, but as retrieval over transcripts, not as attributed knowledge. Zep's results show what user-centric extraction costs: −17.7% on single-session-assistant questions (round-1 note 03).
- **Implication.** Vendor memory answers "who is this user?" Northstar must answer "what has this person learned, from whom, and what are they working toward?" Vendor memory is a source of interference, not a substitute.

### 2. Cross-vendor continuity does not exist natively. Portability is a one-shot, lossy import made by prompting.

- Claude's import, launched March 2026, has the user run a prompt in another assistant and paste the output back. Claude then needs up to 24 hours to absorb it, and Anthropic still labels the feature "experimental". ChatGPT has no bulk import, per secondary sources (2026).
- Each vendor's memory lives only in that vendor. Cowork and chat memory were unified on 2026-08-25, but that is *within* Anthropic.
- **The consequence for Northstar.** For a user on Claude.ai, ChatGPT and Claude Code (GOAL.md §2), cross-session continuity is really **cross-surface** continuity, and no vendor offers it. This is the clearest unclaimed ground on the AI side.

### 3. In-session drift is barely addressed by anyone. Where vendors act at all, they manage context capacity, and compaction drops constraints.

- **Claude.ai.** With code execution enabled, Claude "automatically manages long conversations" by summarizing earlier messages. The full history stays available for reference (help centre, 2026). This keeps the chat going. It does not keep the chat *on the goal*.
- **ChatGPT.** I found no documented in-session mechanism. Secondary sources say the oldest messages drop out silently (unverified).
- **Evidence that this is not enough:**
  - **Multi-turn loss** (Laban et al., ICLR 2026). Average performance falls 39% when information arrives over several turns. The cause is mostly unreliability: models "make assumptions in early turns … and do not recover".
  - **Compaction drops constraints** (Chen, "Governance Decay", arXiv 2606.22528, Jun 2026). In-context policy violations rose from 0% with full context to 30% after compaction, and up to 59% for some models (1,323 episodes, 7 model families). Violation stayed at 0% when the constraint *survived* the summary. "Constraint Pinning", which quarantines constraints from compaction, restored 0%.
  - **Recall is not compliance** (Kruthof, DRIFTBENCH, arXiv 2604.28031, Apr 2026). Models "can accurately restate constraints they are simultaneously violating". The rate of knowing-but-violating ranged from 8% to 99% across seven models. Structured checkpointing reduced the gap but did not close it.
- **Third-party layers do nothing for drift as such:**
  - *Per-turn injection.* Mem0's old extension on ChatGPT and Zep's per-turn context block re-inject *query-similar* memories every turn. That is an injection channel, not a focus mechanism.
  - *In-session compression.* Mastra's Observational Memory compresses the live conversation into a dated, prioritized log in a stable prefix. Letta keeps always-loaded memory blocks. These are the only *structural* in-session designs found. Both serve agent frameworks, not Claude.ai or ChatGPT.
- **Implication.** Northstar's in-session half (non-negotiable 5) has no off-the-shelf component to adopt. It also cannot rely on "retrieve the goal and show it again", because models restate goals and violate them anyway.

### 4. The "universal memory" extensions for ChatGPT and Claude are thin, fact-centred, and unstable.

- **Injection modes:**
  - automatic prompt augmentation: Mem0/OpenMemory on ChatGPT "quietly enhances your prompts"; Claude needed a button;
  - manual per-chat injection: MemoryPlugin "does not automatically inject memories";
  - suggestions while typing, inserted with Tab: Supermemory on Claude and Gemini, 2026-07-22;
  - one-click bucket injection: AI Context Flow, per its vendor's blog.
- **None captures both sides verbatim as attributed knowledge.** MemoryPlugin keeps "only key facts". Supermemory's extension stores data only "when the user actively clicks" (its privacy policy). The local-first "Personal AI Memory" extension does capture conversations into IndexedDB, but it had 260 users at v0.0.7 (2026-03-26).
- **Churn is high.** Mem0 archived its MIT extension on 2026-03-23. Rewind capture stopped on 2025-12-19 after Meta bought Limitless. ChatGPT moved its connectors under "Plugins" (2026; secondary).
- **Implication.** Only a browser extension sees both sides of every turn *deterministically* on the web surfaces and can inject *every turn*. It breaks when the sites change, and nobody maintains a reusable one.

### 5. MCP connectors are the official integration path on both web surfaces. They are pull-based and model-mediated, so they cannot be the capture path.

- **Claude.ai** (help centre, read 2026-10-07):
  - Remote-MCP custom connectors work on every plan (Free: one connector), on web, desktop and mobile.
  - The server must be "reachable over the public internet from Anthropic's IP ranges".
  - In normal chats, "Claude does not run tools automatically"; the user approves tool calls.
  - On Team and Enterprise, only Owners can add connectors.
- **ChatGPT.** Custom MCP needs **Developer mode** (beta since 2025-09).
  - Plan availability is contested. The help centre is quoted as limiting full read/write to Business, Enterprise and Edu, and the developer guide as granting it to Plus and Pro (coworker.ai, updated 2026-09-30; Peliqan, 2026-09-21).
  - Third parties report that **memory is disabled in Developer mode** and that it does not work inside Projects (unverified).
- **The mechanism problem.** Through MCP, Northstar sees only what the chat model chooses to send. Capture would depend on the chat model noticing, mid-conversation, that something is worth saving, and summarizing it faithfully. That is the attention-losing agent GOAL.md §1 warns about. Supermemory's own FAQ advises telling ChatGPT to use its tools "whenever its tools are available", which concedes the point.
- **Implication.** MCP is for *reading* (core pack, search, fetch by ID) and for explicit writes the user asks for. It cannot be the only capture path (non-negotiables 2 and 7).

### 6. MCP Apps (2026-01-26) give the system a supported UI channel inside both chats.

- Tools can return interactive HTML: a `ui://` resource, rendered in a sandboxed iframe. That UI can call server tools (`callServerTool`) and **push into the model's context** (`updateModelContext`). Hosts may require approval for tool calls the UI starts (MCP blog, 2026-01-26).
- At launch it worked in Claude web and desktop, with ChatGPT "rolling out" that week but missing some functions.
- **Implication.** This is a sanctioned place for a human-facing **goal and progress panel** inside a chat, and for a user-triggered "refocus" action. It is still pull/approve, not automatic.

### 7. The developer memory engines differ mainly in what they record about speakers and time. None models "the user learned X from the AI" or "what to learn next".

The table above gives the details. The differences that matter for GOAL.md:

- **Zep/Graphiti** is the closest fit to the shared core in §3.1. It ingests both roles, keeps raw episodes that every fact traces to, stores bitemporal fact edges and invalidates instead of deleting, supports custom types, and combines semantic, BM25 and graph retrieval. Costs: a graph database (Kuzu, the embedded backend, is deprecated) and structured-output LLM calls on every episode. Zep's docs say to put the context block in the provider's *untrusted-data* channel, not the system prompt. That is a good rule for injection hygiene.
- **Mem0 (2026)** captures agent facts "alongside the user's" with ADD-only extraction and hybrid retrieval. Independent benchmarks still put it at 2% on multi-hop fact consolidation (MemoryAgentBench), and with RAG it holds an outdated stance 51.4% of the time (PersonaMem-v3; GPT-5.5 with textual memory: 25.7%).
- **Hindsight** separates world facts from the agent's experiences. Its **mental models** are standing answers to questions you define, rewritten in the background and read without retrieval. Its `recall` runs semantic, BM25, graph and temporal search in parallel, fuses them by rank, reranks with a cross-encoder, and trims to a token limit. This is the nearest existing primitive to a goal-conditioned brief.
- **Supermemory** links memories by `updates` (the newer one wins; the old one is kept), `extends` and `derives`, and sends low-confidence derivations to review.
- **Letta Code** offers an "Agent reviews before applying" option: "a second background conversation" revises proposed memory updates without asking the user.
- **What none of them has:** a record of the form "the assistant asserted X in chat C, and the user engaged with it / endorsed it / ignored it", or a typed structure running goal → learned → next. Their unit is a fact about the user or about the agent's world.

### 8. Maintenance safeguards are appearing in products, but none checks invariants.

| Safeguard | Where it exists |
|---|---|
| Immutable version per write; optimistic concurrency (`content_sha256` precondition); read-only mounts; explicit warning that injected content written to memory becomes "trusted memory" in later sessions | Anthropic memory stores (API beta, 2026) |
| Consolidation writes a **new output store** and leaves the original untouched; approve-before-apply is optional | Anthropic Dreams (research preview, May 2026) |
| Git history plus a reviewer pass | Letta |
| Code measures the index against hard caps and tells the model to rewrite it | Claude Code (`MEMORY.md` over 200 lines / 25KB) |
| Low-confidence inferences go to review | Supermemory |

The one public account of a consolidator in the field shows the gap. Early users of Claude Code's "Auto Dream" reported misnamed files, unverified counts and **no changelog of what it modified** (GitHub issues cited by third-party blogs; unverified). Round-2 note 13 covers how to add invariant checks. This track's point is that the reusable *patterns* exist, while the *checks* do not.

### 9. Personal-capture and PKM-adjacent tools supply raw material or a human view, but not the structure GOAL.md asks for.

- **Pieces** (LTM-2.7): on-device workflow capture going back about 9 months, with an MCP server.
- **Recall** (2.0, 2026-04-14): saved content, an auto-linked graph, and spaced-repetition quizzes. It is the only product with a *learning* loop, but it works over saved web content, not chats.
- **Basic Memory:** Obsidian-compatible markdown with typed observations and relations. It is the best existing *human-readable* substrate. Capture happens only when the model calls `write_note`.
- **Khoj:** document search. I found no user-memory feature.
- **Limitless/Rewind:** gone (see finding 4).

No product found keeps **what to learn** (goals, gaps, open questions, next steps) as maintained structure linked to what was learned. GOAL.md §3.2 has no prior art to adopt. It has to be built.

### 10. Choosing what a new chat gets: goal-directed selection beats goal-agnostic compression, and similarity alone misses goals.

- **SUMER** (arXiv 2511.21726, Nov 2025). An RL-trained agent searching *uncompressed* logs beat goal-agnostic compression and full context on LoCoMo. The authors' argument: fixed pre-compression is lossy and biased toward particular tasks.
- **Goal-Mem** (arXiv 2605.12213, May 2026). It treats the utterance as a goal, splits it into subgoals, and retrieves again until each is resolved. It beat nine baselines, most on multi-hop and implicit inference (no numbers in the abstract).
- **LoCoMo-Plus** (arXiv 2602.10715, Feb 2026). It tests the "cue–trigger semantic disconnect": a goal stated early is semantically far from the turn where it matters, and "cognitive memory remains challenging" for every system tested. This is the GOAL.md §6 failure ("late answers still serve the goal set early"). **Similarity search over the current turn will not find the goal**, so goals must be linked and carried explicitly.
- **The other evidence:**
  - *Raw values, enriched keys.* Storing raw rounds indexed by facts and time works best (LongMemEval, round-1 note 03).
  - *Agentic search over files is strong.* In LongMemEval-V2 (May 2026; up to 115M tokens), a coding agent over files scored 72.5%, against 48.5% for the best RAG baseline.
  - *The 2026 default retrieval is hybrid fusion:* semantic + BM25 + graph + temporal (Hindsight), semantic + keyword + entity (Mem0), semantic + BM25 + graph distance (Graphiti).
  - *Retrieval-free can win when history compresses well.* Mastra's stable observation prefix reports 84–95% on LongMemEval_S and 82–96% on single-session-assistant questions (vendor-reported).

### 11. Supersession is still where memory layers fail most, so it must be resolved when items are written.

- **MemoryAgentBench** (ICLR 2026) FactConsolidation:
  - multi-hop accuracy is at most 28% for any method (GPT-5-mini, long context);
  - memory systems score Mem0 2%, Zep 3%, Cognee 3% and HippoRAG-v2 5%;
  - single-hop: Zep 7%, Mem0 18%, HippoRAG-v2 54%.
- **PersonaMem-v3**: outdated-stance rates of 25.7–51.4% (see finding 7). Mistake-prevention alerts were only 8–13% accurate.
- **MERIT** (round-1 note 03): structured "update-on-write" stores scored 0.70–1.00 on tasks that depend on updated facts.
- **Implication.** For both continuity and in-session focus, the item Northstar hands a chat must already say "current; supersedes X because Y". The model must not be left to choose among versions.

### 12. Budgets: the field injects a few thousand tokens, and less is often better.

| What | Tokens | Source |
|---|---|---|
| Mem0 average per retrieval | ~6.9–7K (against 25K+ for full context) | Vendor-reported |
| Supermemory added context | ~720 tokens at 95% Recall@15 on LongMemEval | Vendor-reported |
| PersonaMem-v2 agentic memory | 2K-token memory beat 32K histories (55% vs frontier models' 37–48%) | Paper |
| Claude Code index | 200 lines / 25KB | Docs |
| Focused vs full prompt | ~300 relevant tokens beat ~113K on LongMemEval | Chroma, round-1 note 07 |

Over-personalization (OP-Bench, round-1 note 07) and sycophancy grow with the amount of irrelevant memory present. The budget is therefore a quality control, not only a cost control.

### 13. Benchmarks: LoCoMo is unreliable, LongMemEval has the only standard "what the AI said" category, and nothing measures the goal.

- **LoCoMo.** Penfield's audit (DEV, Apr 2026; vendor, not peer-reviewed) found:
  - 99 score-corrupting errors in 1,540 questions (6.4%), which caps a perfect system at about 93.6%;
  - the standard gpt-4o-mini judge accepted 62.81% of deliberately wrong but topically adjacent answers.

  Self-reported vendor scores of 87–94 sit at or near that ceiling and come from incompatible harnesses.
- **LongMemEval_S** includes *single-session-assistant* questions, the only standard test of whether a system remembers what the assistant said.
- **Scale and other abilities:**
  - BEAM (ICLR 2026): 100 conversations, 2,000 questions, up to 10M tokens.
  - MemoryAgentBench: retrieval, test-time learning, long-range understanding, selective forgetting.
  - HaluMem: grades each memory operation separately (round 1).
  - PersonaMem-v3: outdated stance, appropriateness.
  - LoCoMo-Plus: latent constraints.
- **What none of them measures:**
  - drift reduction relative to a goal set earlier in the *same* chat (the closest proxies are Laban's sharded tasks, DRIFTBENCH and the Governance Decay compaction benchmark);
  - attribution of AI-taught knowledge;
  - the quality of a learned / to-learn structure.

  GOAL.md §6 requires all three. Northstar must build its own evaluation, and keep public benchmarks as regression checks only.

---

## What this means for the Northstar architecture

### The gap, stated against GOAL.md

| GOAL.md requirement | What exists (2026-10) | What is missing, i.e. Northstar's job |
|---|---|---|
| §3.1 Shared core capturing **both sides**, attributed, evolving without losing history | Zep/Graphiti episodes + bitemporal edges; Mem0 ADD-only; Supermemory `updates`; Hindsight facts vs experiences | Deterministic capture of web chats; speaker attribution decided by the adapter, not inferred; "AI asserted / user engaged / endorsed" stance; supersession *with reasons* across surfaces |
| §3.2 Human structure of **learned** and **to learn** | Profiles (ChatGPT summary, Claude topics), notes (Basic Memory), cards + spaced repetition (Recall) | A maintained map of goals → learned items (by source: self or AI) → gaps, open questions and next steps. No prior art |
| §3.3 In-session focus | Vendor compaction (keeps chats alive and drops constraints); Mastra OM and Letta blocks (agent frameworks only) | A goal anchor that survives the vendor's compaction, per-turn delivery on web surfaces, and a *check*, not just a reminder |
| §3.3 Cross-session continuity | Strong within one vendor; none across Claude.ai, ChatGPT and Claude Code | A cross-surface, goal-conditioned new-chat pack |
| §3.4 Robust maintainer | Versioning, new-store consolidation, reviewer passes, index caps | Invariant checks, error budgets, rollback (round-2 note 13) |

### Implications

1. **[surface adapters] Make capture deterministic. It must never depend on the chat model's attention.**
   - *Claude.ai and ChatGPT web:* a Northstar browser extension reads both sides of every turn from the page (message IDs, timestamps, model name) and sends them to the core as raw episodes.
   - *Backfill and reconciliation:* official exports, ingested idempotently (formats in round-1 note 08).
   - *Claude Code:* hooks. `Stop` provides `last_assistant_message`; `UserPromptSubmit` and `SessionStart` accept `additionalContext`; `PreCompact` can block or precede compaction; every hook receives `transcript_path`.
   - *MCP:* reading and explicit, user-requested writes only (findings 4, 5).
2. **[core] Raw turns from both roles are the record. The adapter sets the speaker.** Every derived item cites episode spans (the Zep/Graphiti episode model; LongMemEval's raw values with enriched keys). `asserted_by` (user / which AI / pasted / tool) comes from page structure, never from an LLM. Extraction then adds stance (encountered / engaged / endorsed), per round-1 note 08.
3. **[core] AI-taught knowledge is its own kind of record, not a line in a user profile.** It is a claim about the world, attributed to the AI and linked to the goals it serves. Hindsight's split between facts and experiences shows this is buildable. Vendor profiles show what is lost without it.
4. **[AI cross-session] Build the new-chat pack from goals, not from the person:**
   - **(a)** A deterministic **core pack** of a few thousand tokens at most: active goals and their state, established conclusions with who established them, open questions, in-scope instructions. Only current items, each with an ID and an "as of" date.
   - **(b)** A **goal router** on the first user message.
   - **(c)** Goal-conditioned retrieval: subgoal decomposition (Goal-Mem), *explicit* goal → item links (because of the LoCoMo-Plus disconnect), and four-way hybrid recall with fusion under a hard token budget.
   - **(d)** Optional per-goal **standing briefs** (like Hindsight's mental models), regenerated from items, never from earlier briefs.

   This is goal-directed selection (SUMER), not a preloaded, goal-agnostic profile.
5. **[AI in-session] Pin a small goal-and-conclusions block outside anything the vendor compacts. Re-deliver it every turn, and check answers against it.**
   - *Delivery:* on web, the extension augments each outgoing prompt, as Mem0's extension did; in Claude Code, `UserPromptSubmit`.
   - *Why pinning:* Constraint Pinning restored 0% violations.
   - *Why also a check:* DRIFTBENCH shows reminders are not enough. A cheap drift check compares each answer with the pinned block. It raises a signal (an MCP Apps panel or an extension badge) and offers a corrective re-prompt that the user may ignore. No ritual is required (non-negotiable 1).
6. **[AI in-session] Keep a Mastra-style live observation log on Northstar's side.** An Observer runs at token thresholds over the captured turns and records dated, prioritized observations from both speakers. These become episodes and feed the pinned block. A chat's early conclusions, whether the user's or the AI's, then survive vendor compaction (GOAL.md §3.3).
7. **[core / AI cross-session] Resolve supersession at write time.** Chats see only "current; supersedes X because Y", with history linked, never a set of versions to choose from. The evidence: PersonaMem-v3 outdated-stance rates of 25–51%, MemoryAgentBench consolidation of 2–7% for memory systems, and MERIT.
8. **[human structure] Build the learned / to-learn map. Project it as an Obsidian-compatible vault (Basic Memory conventions) and as MCP Apps views inside both chats.** Give it the controls users now expect from Claude Topics and ChatGPT's Memory Summary: view, correct, "don't mention this", delete. No product supplies the structure itself (finding 9).
9. **[maintainer] Adopt the product safeguards as primitives and add the invariant checks they lack.**
   - *Primitives:* immutable versions; hash-preconditioned writes; consolidation into a *new* store, swapped in only after checks pass (Dreams); git-style history with a reviewer pass (Letta); index caps enforced by code (Claude Code).
   - *Checks to add:* every citation resolves; coverage never drops without a recorded reason; a changelog for every run. Round-2 note 13 owns the detail.
10. **[core] An open-source engine may serve only as a derived, rebuildable index behind an interface.** Graphiti, Hindsight and Mem0 assume user-centric extraction, and the ecosystem churns (finding 4; risk 8). Northstar owns the canonical record: episodes, typed attributed items and events.
11. **[surface adapters] Deliver context as labelled data, never as instructions.** This follows Zep's untrusted-channel rule and round-1 notes 07 and 08. The extension reads model output, so it must resist injection from the page.
12. **[evaluation] Build the GOAL.md §6 evaluation first.**
    - *In-session:* Laban-style sharded goals, and constraint retention through compaction, on the user's own chat types.
    - *Cross-session:* "no re-explaining" tasks.
    - *Regression subsets:* LongMemEval_S single-session-assistant, knowledge-update and abstention; LoCoMo-Plus; MemoryAgentBench FactConsolidation; PersonaMem-v3 outdated stance.
    - *Arms:* vendor memory on; vendor memory off; Northstar.
    - *Do not use:* LoCoMo headline scores.

### Reuse candidates (honest pros and cons)

| Candidate | Use in Northstar | Pros | Cons |
|---|---|---|---|
| **Graphiti** (Apache-2.0) | Derived graph index, temporal queries, MCP read tools | Raw episodes, bitemporal edges, custom types (Goal, Claim, Question), hybrid + graph retrieval, active project | Needs a graph database server (the embedded Kuzu backend is deprecated); many LLM calls per episode; its entity resolution makes its own errors; user-centric defaults |
| **Hindsight** (MIT) | Retrieval engine and per-goal standing briefs (mental models) | Separates facts from experiences; four-way recall + fusion + reranker + token limit; mental models; MCP per bank; Postgres | Young (paper Dec 2025); benchmark claims come from the authors (independent reproduction claimed by a directory, unverified); its "observations" are machine-consolidated beliefs, so they must not count as the user's beliefs |
| **Mem0 OSS** (Apache-2.0) | Baseline arm; possibly retrieval | Mature, ADD-only, hybrid, large community | Facts as values lose context; weak on consolidation (2% multi-hop) and staleness (51.4% outdated); speaker attribution looks coarse (unverified) |
| **Supermemory** (MIT repo; hosted MCP) | Reference design for `updates/extends/derives`; quick ChatGPT/Claude MCP prototype | Working ChatGPT Developer-mode and Claude connector paths; relation types close to supersede/refine | Cloud by default; local server ships as a binary (how much of the engine is open is unclear); extension does not capture automatically |
| **Basic Memory** (AGPL-3.0) | Format and tooling for the human-readable markdown projection | Obsidian-compatible, typed observations and relations, hybrid search, MCP | AGPL obligations if modified and served; capture is model-mediated; no supersession semantics; ChatGPT needs its cloud |
| **Mem0 Chrome extension** (MIT, archived 2026-03-23) | Starting code for the web capture and injection adapter | Shipped automatic prompt augmentation on ChatGPT and Perplexity (manual on Claude; Grok added later); forkable | Unmaintained; DOM selectors are probably stale (unverified); it captured facts, not verbatim turns; Northstar inherits the whole maintenance burden |
| **Letta MemFS patterns** (Apache-2.0) | Maintainer: git-backed memory, worktree subagents, reviewer pass | Concrete, shipping design for consolidation by a separate agent | Built around coding agents; its reviewer is another LLM without invariants |
| **Anthropic memory-store semantics** | Maintainer write protocol (versions, sha256 preconditions, new-store consolidation) | Clean, documented primitives | API beta tied to Managed Agents. Borrow the design, not the dependency |
| **Mastra Observational Memory** | Pattern for the in-session observation log | The only published structural in-session design found; cacheable prefix; both speakers | Framework-bound; results vendor-reported; license not checked |
| **MCP Apps SDK** | In-chat goal panel and human view | Official; works in both Claude and ChatGPT | ChatGPT support partial at launch; actions need user approval |
| **Claude Code hooks** | Deterministic capture and per-turn injection on the Claude Code surface | Documented, local, full fidelity | Only for Claude Code; web surfaces have nothing comparable |

---

## Options and trade-offs the design must decide

1. **Capture channel on web** (non-negotiables 2, 6, 7). Three options:
   - **(a)** A browser extension: deterministic, both sides, live, but fragile and needing broad permissions.
   - **(b)** Exports: full fidelity, but delayed and manual today.
   - **(c)** MCP summaries: official, but model-mediated and lossy.

   The evidence favours (a) + (b) for capture and (c) for reading. The user must decide whether to accept a Northstar extension, and in which browser.
2. **Delivery into a web chat.** Three options:
   - automatic augmentation of every prompt: the strongest in-session lever, but it alters what is sent and costs tokens every turn;
   - model-pulled MCP calls: clean but unreliable;
   - user-triggered injection by button or Tab: reliable, but it turns delivery into a user step, which non-negotiable 1 rules out as a *requirement*.

   A likely mix: the pinned block is delivered automatically, and larger retrievals are pulled on demand.
3. **Vendor memory: on or off** while Northstar runs? On means redundancy, possible conflicts and more sycophancy pressure. Evaluation needs both conditions. If Developer mode disables ChatGPT memory, ChatGPT may decide this for us.
4. **Engine:**
   - **(a)** Own canonical store with an OSS engine as a rebuildable index (proposed above);
   - **(b)** Graphiti or Hindsight as the core;
   - **(c)** SQLite, FTS5 and embeddings only (round-1 baseline).

   The trade-off is build effort against semantic fit and lock-in.
5. **Hosting.** Both web surfaces need an internet-reachable MCP server. The choice is a local core behind a secure tunnel, or a small hosted relay.
6. **Core-pack composition.** How much profile (preferences, style) versus goal state (goals, conclusions, questions), within roughly 1–4K tokens? Recency changes salience only; nothing is deleted by decay.
7. **Retrieval:** four-way hybrid fusion, agentic file search (strong in LongMemEval-V2, but slower), or a retrieval-free stable prefix per goal. Test them side by side.
8. **Human view surface:** a vault, a Northstar web app, MCP Apps panels, or several of these as projections of one record.
9. **ChatGPT fallback** if Developer-mode MCP is unavailable on the user's plan: integration through the extension only.

---

## Risks to the goal

1. **ChatGPT web (non-negotiable 6) may not support the official integration on the user's plan.** Sources conflict on whether Plus or Pro can use custom MCP with write actions. Third parties report that Developer mode disables memory and is unavailable in Projects (unverified). If so, ChatGPT-first depends on a browser extension. That is feasible, but fragile, and a terms-of-service and store-review risk that Northstar has to own.
2. **Capture through MCP alone would break non-negotiables 2 and 7.** If the chat model has to decide what to save, the AI-said knowledge that gets captured is exactly as reliable as that model's attention mid-conversation. This is the self-convolution risk the user named. Avoiding it requires deterministic capture: extension, exports, hooks.
3. **In-session drift reduction on web surfaces may be smaller than hoped.** Northstar cannot control the vendor's compaction or truncation. Models violate goals they can restate (DRIFTBENCH: 8–99% across models). Per-turn injection plus checking is the best available lever, and its measured effect on Claude.ai and ChatGPT is unknown. This must be measured early, as GOAL.md §6 requires, not assumed.
4. **Extension maintenance and security.** The extension sees every chat. Site changes break it; Mem0 archived its extension, which is a signal of the burden. It is also a high-value target. A compromised or injected extension could exfiltrate or poison memory (SpAIware-class risk, round 1).
5. **Employer account.** If the declared Claude account is an employer Team or Enterprise seat:
   - only Owners can add custom connectors;
   - memory is admin-controlled;
   - exports and retention follow the employer's policy;
   - employer device or browser policies may block extensions.

   Personal learning could end up in an employer-governed store. The user needs to decide on personal/work separation before build.
6. **Vendor memory interference.** Native ChatGPT and Claude memory keep injecting their own user-centric context. It may contradict Northstar's current view (for example, a superseded conclusion) or amplify sycophancy. I found no API that would let Northstar read or edit those memories in order to reconcile them.
7. **There is no benchmark for the goal.** Public scores (LoCoMo 87–94) are near their ceiling, the judges are unreliable, and none measures goal-focused drift, attribution of AI-taught knowledge, or learned / to-learn structure. Without our own evaluation, built first, success claims would be unfalsifiable.
8. **Dependency churn.** In under a year: Rewind shut down, the Mem0 extension was archived, Kuzu was deprecated in Graphiti, Letta deprecated server features, ChatGPT renamed its integration surfaces, and Claude memory changed architecture (July 2026). Every reused component must sit behind an interface, with the canonical record owned by Northstar.
9. **Hosting exposure.** Both web surfaces reach only internet-reachable MCP servers. A local-first core therefore needs a tunnel or relay, which widens the attack surface for a store that holds a person's whole learning history.

---

## Sources

**Vendor memory: Claude / Anthropic**
- Anthropic Help Center, "Understanding Claude's memory" (read 2026-10-07). https://support.claude.com/en/articles/11817273-understanding-claude-s-memory
- Anthropic Help Center, "Getting started with custom connectors using remote MCP" (read 2026-10-07). https://support.claude.com/en/articles/11175166-getting-started-with-custom-connectors-using-remote-mcp
- Anthropic Help Center, usage and length limits / automatic context management. https://support.claude.com/en/articles/11647753-how-do-usage-and-length-limits-work ; https://support.claude.com/en/articles/12466728-troubleshoot-claude-error-messages
- SiliconANGLE, "Anthropic updates Claude's memory…" (2026-08-25). https://siliconangle.com/2026/08/25/anthropic-updates-claudes-memory-to-enhance-customization-and-protect-sensitive-topics/
- TechCrunch, "Claude Cowork finally remembers what you told the app in chat" (2026-08-25). https://techcrunch.com/2026/08/25/claude-cowork-finally-remembers-what-you-told-the-app-in-chat/
- Secondary, on the July 2026 topic-entry change: https://memx.app/blog/claude-memory-editable-entries-update/ ; https://konshus.ai/claude-memory-august-2026
- Bloomberg Law, "Anthropic Tries to Win Users From ChatGPT With Memory Feature" (Mar 2026; via search snippet). https://news.bloomberglaw.com/artificial-intelligence/anthropic-tries-to-win-users-from-chatgpt-with-memory-feature
- Claude Code docs, "How Claude remembers your project". https://code.claude.com/docs/en/memory
- Claude Code docs, Hooks reference. https://code.claude.com/docs/en/hooks
- Claude Platform docs, "Using agent memory" (memory stores, beta `agent-memory-2026-07-22`). https://platform.claude.com/docs/en/managed-agents/memory
- On Dreams for Managed Agents (May 2026; secondary): https://www.mindstudio.ai/blog/what-is-claude-dreaming-anthropic-managed-agents ; https://letsdatascience.com/news/anthropic-adds-dreaming-to-claude-managed-agents-3d6be7b5
- Claude Code "Auto Dream" (third-party, unverified): https://tessl.io/blog/anthropic-tests-auto-dream-to-clean-up-claudes-memory/
- Platform docs, Compaction (API). https://platform.claude.com/docs/en/build-with-claude/compaction

**Vendor memory: ChatGPT / OpenAI** (openai.com and help.openai.com returned 403 to my fetcher)
- OpenAI Help Center, Memory FAQ (search snippets). https://help.openai.com/en/articles/8590148-memory-faq
- OpenAI, "Dreaming: Better memory for a more helpful ChatGPT" (2026-06-04; not retrievable). https://openai.com/index/chatgpt-memory-dreaming
- Thurrott, "OpenAI is improving how ChatGPT's memory works" (Jun 2026). https://www.thurrott.com/a-i/337052/openai-is-improving-how-chatgpts-memory-works
- Digital Applied, Dreaming V3 guide (secondary, eval figures). https://www.digitalapplied.com/blog/chatgpt-memory-dreaming-v3-openai-2026-guide
- LaunchReady, "ChatGPT memory summary: read and edit" (2026; quotes OpenAI). https://launchready.ai/insights/ai-readiness/chatgpt-memory-summary-read-and-edit-2026
- Simon Willison, "Comparing Claude and ChatGPT memory" (2025-09-12; summarizes Shlok Khemani). https://simonwillison.net/2025/Sep/12/claude-memory/
- Simon Willison, "ChatGPT project memory" (2025-08-22). https://simonwillison.net/2025/Aug/22/project-memory/
- Manthan Gupta reverse-engineering, via llmrefs (Dec 2025). https://llmrefs.com/blog/reverse-engineering-chatgpt-memory
- ChatGPT Developer mode and MCP plan availability (conflicting secondary): https://coworker.ai/blog/chatgpt-mcp ; https://peliqan.io/blog/chatgpt-mcp/ ; https://x.com/OpenAIDevs/status/1965807401745207708 ; https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt
- Report that memory is disabled in Developer mode (third-party, unverified): https://www.jeffbullas.com/playbooks/how-to-set-up-chatgpt-developer-mode-and-connect-1000-apps/ ; https://hn.nuxt.dev/item/45715628

**Third-party memory layers and engines**
- Mem0 repo. https://github.com/mem0ai/mem0 ; Mem0 research page (2026 algorithm, vendor-reported). https://mem0.ai/research
- Mem0 Chrome extension repo (archived 2026-03-23). https://github.com/mem0ai/mem0-chrome-extension ; OpenMemory extension post. https://mem0.ai/blog/introducing-the-openmemory-chrome-extension
- OpenMemory MCP. https://mem0.ai/blog/introducing-openmemory-mcp ; https://docs.mem0.ai/openmemory
- Supermemory repo. https://github.com/supermemoryai/supermemory ; docs (MCP tools; ChatGPT web; how it works). https://supermemory.ai/docs/supermemory-mcp/technology.md ; https://supermemory.ai/docs/supermemory-mcp/chatgpt-web ; https://supermemory.ai/docs/concepts/how-it-works ; changelog (2026-07-22). https://supermemory.ai/changelog/browser-extension-support-for-claude-and-gemini.md ; privacy policy. https://supermemory.ai/privacy
- MemoryPlugin help: browser extension, buckets. https://help.memoryplugin.com/integrations/browser-extension ; https://help.memoryplugin.com/features/memory-buckets.md ; https://www.memoryplugin.com/
- Plurality Network, "Best AI Memory Extensions of 2026" (2026-07-10; publisher sells AI Context Flow). https://plurality.network/blogs/best-universal-ai-memory-extensions-2026/
- Personal AI Memory (Chrome Web Store). https://chromewebstore.google.com/detail/personal-ai-memory/cjkjgbddkaoogdbfffiooeppnmbplpnh
- Letta Code memory and MemFS docs. https://docs.letta.com/letta-code/memory ; https://docs.letta.com/letta-code/memfs ; sleep-time agents. https://docs.letta.com/guides/agents/architectures/sleeptime
- Graphiti repo. https://github.com/getzep/graphiti ; Zep concepts and context. https://help.getzep.com/v2/concepts ; https://help.getzep.com/retrieving-context
- Hindsight repo. https://github.com/vectorize-io/hindsight ; paper, "Hindsight is 20/20" (arXiv 2512.12818). https://arxiv.org/abs/2512.12818
- Basic Memory repo. https://github.com/basicmachines-co/basic-memory ; ChatGPT integration docs. https://development.docs.basicmemory.com/integrations/chatgpt
- Cognee repo. https://github.com/topoteretes/cognee
- MemOS repo. https://github.com/MemTensor/MemOS
- Mastra, "Observational Memory" (2026-02-09). https://mastra.ai/research/observational-memory
- Pieces docs and LTM-2. https://docs.pieces.app/products/core-dependencies/pieces-os ; https://pieces.app/blog/introducing-the-pieces-mcp-server
- 9to5Mac, Rewind/Limitless acquired by Meta (2025-12-05). https://9to5mac.com/2025/12/05/rewind-limitless-meta-acquisition/
- Khoj repo. https://github.com/khoj-ai/khoj
- Recall release notes (2026-04-14; 2026-05-15). https://feedback.recall.it/changelog/recall-release-notes-april-14-2026-recall-20 ; https://feedback.recall.it/changelog/recall-release-notes-may-15-2026-post-launch-improvements-fixes-and-bug-bashes

**Protocol**
- MCP blog, "MCP Apps" (2026-01-26). https://blog.modelcontextprotocol.io/posts/2026-01-26-mcp-apps/

**Benchmarks and research**
- Laban et al., "LLMs Get Lost In Multi-Turn Conversation" (ICLR 2026). https://arxiv.org/abs/2505.06120
- Chen, "Governance Decay: How Context Compaction Silently Erases Safety Constraints…" (arXiv 2606.22528, Jun 2026). https://arxiv.org/abs/2606.22528
- Kruthof, "Models Recall What They Violate: Constraint Adherence in Multi-Turn LLM Ideation" (arXiv 2604.28031, Apr 2026). https://arxiv.org/abs/2604.28031
- Zheng et al., "Goal-Directed Search Outperforms Goal-Agnostic Memory Compression…" (SUMER, arXiv 2511.21726). https://arxiv.org/abs/2511.21726
- Liang et al., "Goal-Oriented Reasoning for RAG-based Memory…" (Goal-Mem, arXiv 2605.12213). https://arxiv.org/abs/2605.12213
- Li et al., "Locomo-Plus: Beyond-Factual Cognitive Memory Evaluation…" (arXiv 2602.10715). https://arxiv.org/abs/2602.10715
- Wu et al., "LongMemEval-V2" (arXiv 2605.12493). https://arxiv.org/abs/2605.12493
- Wu et al., "LongMemEval" (ICLR 2025). https://arxiv.org/abs/2410.10813
- Tavakoli et al., "Beyond a Million Tokens" (BEAM, ICLR 2026). https://arxiv.org/abs/2510.27246
- Hu, Wang, McAuley, "Evaluating Memory in LLM Agents via Incremental Multi-Turn Interactions" (MemoryAgentBench, ICLR 2026; Table 3). https://arxiv.org/abs/2507.05257 ; https://arxiv.org/html/2507.05257
- Jiang et al., "PersonaMem-v3" (arXiv 2608.21381; §4.2–4.4). https://arxiv.org/html/2608.21381
- Jiang et al., "PersonaMem-v2" (arXiv 2512.06688). https://arxiv.org/abs/2512.06688
- Penfield Labs, LoCoMo audit (DEV, Apr 2026; vendor, not peer-reviewed). https://dev.to/penfieldlabs/we-audited-locomo-64-of-the-answer-key-is-wrong-and-the-judge-accepts-up-to-63-of-intentionally-33lg
- Zep, "Lies, Damn Lies, & Statistics: Is Mem0 Really SOTA in Agent Memory?" https://blog.getzep.com/lies-damn-lies-statistics-is-mem0-really-sota-in-agent-memory/
- Round-1 notes reused: `docs/research/03-ai-memory-systems.md` (MERIT, HaluMem, ACE, Zep −17.7% on single-session-assistant, Letta filesystem baseline), `docs/research/07-human-vs-ai-consumers.md` (context rot, OP-Bench, sycophancy, progressive disclosure), `docs/research/08-ingestion-and-extraction.md` (export formats, attribution).

---

## Review revisions (2026-10-08)

Changes from the adversarial design review. The full review record is `docs/design/REVIEW.md`.

| Finding | What changed |
|---|---|
| SEC-6 | Risks to the goal, item 5 (the review called it "Implication 5"): the lead now reads "**Employer account.** If the declared Claude account is an employer Team or Enterprise seat:". The four bullets and the closing sentence are unchanged. Nothing else changed. |

All other evidence is unchanged.
