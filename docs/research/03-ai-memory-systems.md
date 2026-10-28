# AI/LLM Memory Systems, 2023–2026: Mechanisms, Results, and What They Miss About a Person

Track 03 research note. Written 2026-10-07. Sources were checked on the web where possible: the papers' own abstracts and HTML, vendor posts and docs. The web search budget ran out partway through, so some claims about products rest on secondary sources. Those claims are marked "(unverified)" or "(secondary source)". Any number that comes from a vendor about its own system should be read as a claim, not as an independent result.

## Scope and questions

This note covers memory for LLMs and agents: research systems, shipped products, benchmarks, and known failure modes. It does not cover classical personal knowledge management (PKM), cognitive science, or knowledge representation theory, because other tracks handle those. For every system, it asks four questions:

1. **What is the unit of memory?** A raw message, an atomic fact, a note, a graph edge, a summary block, a file, or a skill.
2. **What is the update operation?** Append, overwrite, delete, invalidate, merge, link, or rewrite. Who triggers it, and when: on the hot path during a conversation, or offline?
3. **What does the evidence say?** Specifically, measured results against the simple baselines: full context, plain retrieval-augmented generation (RAG), and files plus search.
4. **What do these systems systematically miss?** The comparison is with a *person's* evolving understanding: beliefs with reasons, uncertainty, decisions, open questions, contradictions, and the history of changing one's mind.

The short answer to question 4 drives most of this note. Almost every system here is built to model *the user* so that an assistant can personalize its replies. None of them is built to hold *the user's understanding of the world*. The usual unit is a third-person assertion such as "User prefers X" or "User lives in Y". Its update semantics are "newest wins". Its success measure is recall on synthetic chat logs. That is a different object from what this project wants to build.

## Key findings

### 1. Full context is the baseline to beat, and on the best-known benchmark it often wins

- **Mechanism.** An external memory system is a lossy compression and attention-focusing layer. It wins when the history is bigger than the model's *effective* context, or when cost and latency matter. When the whole history fits and the model attends to it well, it loses.
- **Evidence, LoCoMo.** In Mem0's own paper, the LLM-as-judge (J) scores were: full context **72.90**, Mem0 **66.88**, Mem0 with a graph **68.44**, Zep 65.99 (as Mem0 measured it), LangMem 58.10, best RAG configuration 60.97, OpenAI memory 52.90, A-Mem 48.38. Mem0's case rests on latency and tokens rather than accuracy. Full context used about 26K tokens per conversation with a p95 latency of about 17 s. Mem0 used about 7K tokens with a p95 latency of 1.44 s.
- **A plain-files baseline also beats the specialized systems.** Letta put the LoCoMo conversations into files and gave a gpt-4o-mini agent `grep`, semantic search, and open/close tools. It scored **74.0%**, above every specialized memory layer in Mem0's table.
- **The picture flips on LongMemEval.** Its histories are about 115K tokens long (LongMemEval_S). Long-context models lose 30–60% relative to an oracle that sees only the relevant sessions. Here, memory layers *do* beat full context. Zep reports +18.5% with gpt-4o. Mastra's Observational Memory reports 84.23% with gpt-4o, which it says is about 24 points above full context. It reports 94.87% with gpt-5-mini.
- **Takeaway.** Whether memory helps recall depends on the regime. For one person's lifetime corpus, which will exceed any context window, some selection is unavoidable. But **recall is not where this project's value will come from**. Raw logs plus a strong model plus search already handle much of it.

### 2. Extraction is where most errors start, and it fails in predictable ways

- **Mechanism.** Most systems turn raw dialogue into "facts" at write time. Anything the extractor drops or distorts cannot be recovered later. Systems that also discard the source make this worse.
- **LongMemEval design study.** Splitting sessions into *rounds* helps. Using extracted facts *as the stored values* "harms overall performance due to information loss". Using extracted facts as *extra index keys* while keeping the raw round as the value improves recall@k by 9.4% and final accuracy by 5.4% on average. Time-aware query expansion improves temporal reasoning by 11.3%.
- **HaluMem (Nov 2025)** grades each memory operation separately:
  - Most systems recall under 60% of the memory points they should extract. Mem0 recalls 42.9% on HaluMem-Medium and **3.2%** on HaluMem-Long. MemOS is the outlier at 74–82%.
  - Update accuracy is under 50% everywhere. Omissions exceed 50%, mostly because extraction missed the item upstream.
  - End-to-end QA accuracy is under 70%.
- **Zep's per-category results** show the same blind spot. Zep improved most LongMemEval categories but *dropped 17.7%* on "single-session-assistant" questions. Those ask about something *the assistant* said, and an entity/fact extractor focused on the user does not capture it.
- **Takeaway.** For this project, the AI's contributions to a conversation matter as much as the user's statements. An extractor centred on "facts about the user" is the wrong tool.

### 3. The standard update operation is moving from overwriting to non-destructive supersession, but the evidence on when to resolve conflicts is mixed

- **Mem0, 2025.** For each candidate fact, the system retrieves the top 10 similar memories. An LLM then picks **ADD / UPDATE / DELETE / NOOP** through a tool call. The graph variant (Mem0^g) marks conflicting relations as invalid instead of removing them.
- **Zep/Graphiti.** Every fact edge carries four timestamps:
  - `t_valid` and `t_invalid`: when the fact was true in the world.
  - `t'_created` and `t'_expired`: when the system learned the fact and when it retired it.

  When an LLM finds a contradicting edge whose time ranges overlap, it sets the old edge's `t_invalid` to the new edge's `t_valid`. Nothing is deleted, so you can ask both "what did the system believe on date D?" and "what was true on date D?".
- **Mem0, 2026.** Mem0 changed its algorithm to **ADD-only** extraction: one LLM call, no overwrite or delete step, so "history survives intact" and extraction is about twice as fast. Staleness is handled at *retrieval* time through temporal reranking, recency decay, and entity linking. The leading vendor of the ADD/UPDATE/DELETE/NOOP design dropped destructive updates. That is strong practical evidence against them.
- **Counter-evidence: MERIT (Jul 2026), a task benchmark.**
  - "Update-on-write" structured fact stores scored 0.70–1.00 on tasks that depend on updated facts.
  - Embedding retrieval ranged from 0.30 to 0.95 depending on the model.
  - Agents acted correctly on a retrieved value only 55% of the time.
  - Swapping the memory implementation changed task success by up to 60 points.

  So resolving conflicts lazily at read time leaves the model to choose among stale and current versions, and models do that poorly.
- **Synthesis.** Keep an append-only log, *and* materialize a "current view" whose links say which entry superseded which. The two answer different questions.

### 4. Repeatedly rewriting one summary destroys information ("context collapse")

- **ACE (ICLR 2026)** found that letting an LLM rewrite its accumulated context as one block causes **brevity bias** and **context collapse**. In one AppWorld run, an 18,282-token context with 66.7% accuracy was rewritten to **122 tokens** in a single step. Accuracy fell to 57.1%, *below* the 63.7% baseline with no context at all.
- **ACE's fix** is an itemized "playbook":
  - Each bullet has an ID and counters for how often it proved helpful or harmful.
  - Updates are *deltas*: add or modify specific bullets.
  - A separate grow-and-refine step removes duplicates.

  This gave +10.6% on agent tasks and +8.6% on finance tasks.
- **Why this matters.** Products are moving toward one synthesized, regularly rewritten summary: ChatGPT "Dreaming" and Claude's memory summary, which secondary sources describe as re-synthesized about every 24 hours. That design has exactly this failure mode. It also has the human-legibility problem a person would notice: who checks that nuance survived the rewrite?

### 5. Simple substrates that models already know how to use are surprisingly competitive, but structure may pay off over long timescales

- **Evidence for simple substrates:**
  - Letta's filesystem agent scored 74% on LoCoMo, which Letta attributes to models being post-trained heavily on file and grep tools.
  - Anthropic's memory tool is a client-side `/memories` directory with view/create/str_replace/insert/delete/rename commands.
  - Claude Code's auto memory is a `MEMORY.md` index plus one Markdown file per memory, typed `user` / `feedback` / `project` / `reference`. Each file gets a `modified` timestamp, and only the first 200 lines or 25KB of the index load at startup.
  - AGENTS.md is used by more than 60K repositories.
  - Mastra's Observational Memory, the current top LongMemEval result, uses **no retrieval at all**. It keeps a dated, prioritized observation log in a stable prompt prefix that can be cached.
- **Mechanism.** An agent that can search its own memory step by step makes up for weak indexing. Structures the model does not know well, such as custom graph query languages, go underused.
- **Counter-evidence on timescale: "Ground Truth First" (Jul 2026, one author, 6 users).** This paper reports a **tenure crossover**:
  - A budgeted, curated memory map led at 3 weeks, but its recall fell from 96% to 72% by 9 weeks.
  - A provenance-typed graph *rose* to 90% at 9 weeks.
  - A layered design was best at both horizons.

  The sample is small, so this is suggestive only. But it is exactly this project's regime: years, not one 26K-token conversation. Evaluations that last a few days will pick the wrong architecture.

### 6. Consolidation is moving offline ("sleep"), and that separation is the most widely shared idea in the field

- **Generative Agents (2023)** introduced the core loop:
  - A memory stream of timestamped observations.
  - A retrieval score that adds recency (exponential decay, factor 0.995 per game hour), LLM-rated importance on a 1–10 scale, and embedding relevance.
  - Reflection, triggered when the summed importance of recent events passes 150. Reflection writes higher-level insights that *cite the memories they came from*, so it builds trees of abstraction.

  Removing reflection, planning, or observation each made the agents' behaviour noticeably less believable.
- **Letta's sleep-time compute paper (Apr 2025):**
  - Precomputing over the context before any query cut test-time compute about 5× at equal accuracy and raised accuracy 13–18%.
  - Sharing the precomputed work across related queries cut cost per query 2.5×.
  - Crucially, the benefit *tracks how predictable the queries are*.

  In Letta's product, the primary agent cannot edit memory. A separate sleep-time agent owns the memory blocks.
- **Others with the same split:**
  - Mastra uses an Observer that compresses messages into dated observations at a token threshold, and a Reflector that condenses observations at a second threshold.
  - ChatGPT's "Dreaming" (June 2026) is a background process that synthesizes memory across chats and rewrites time-sensitive items. Its example: "going to Singapore in July" becomes "went to Singapore in July 2026". OpenAI reports internal factual recall rising from 41.5% (2024 saved memories) to 82.8%, preference adherence at 71.3%, and time-sensitive accuracy at 75.1%. These are internal evals that cannot be reproduced.
- **Mechanism.** The hot path stays cheap and append-only. Reorganization runs with more compute and a wider view, where mistakes can be batched and reviewed.

### 7. Hierarchies and abstraction layers answer "big picture" questions, but they were built for static document sets

- **RAPTOR** recursively clusters and summarizes chunks into a tree and retrieves across all levels. With GPT-4 it gained 20 points of absolute accuracy on QuALITY.
- **GraphRAG** extracts entities and relations, finds communities with the Leiden algorithm, and pre-writes community reports. It then map-reduces those reports to answer global sense-making questions, where it beats plain RAG on comprehensiveness and diversity.
- **HippoRAG / HippoRAG 2** build a schema-free knowledge graph with open information extraction (OpenIE). At query time they run Personalized PageRank (PPR) seeded from the query's entities, after hippocampal indexing theory. HippoRAG 2 gains about 7 points over strong embedding retrievers on associative (multi-hop) memory tasks without losing factual QA. It describes itself as "non-parametric continual learning", meaning memory grows by adding to the index rather than changing model weights.
- **Zep** adds a community subgraph above its entity graph.
- **The catch.** All of these assume a corpus that is indexed in batches. Incremental maintenance is weak or costly: GraphRAG re-indexes, and RAPTOR rebuilds clusters. None of them *revises* old content when new evidence arrives. They only add.
- **Relevance here.** A person wants to ask "what are my main themes?" and "how does X relate to Y in my thinking?". Those need this layer, but it has to be maintained incrementally and must keep links back to its evidence.

### 8. The products converged on scoped, readable, editable memory plus search over raw history; their complaints are about context bleeding into unrelated chats and loss of control

**What each product ships:**

- **ChatGPT.** In 2024–2025 it had "saved memories" (short sentences) plus "reference chat history" (April 2025). In June 2026 "Dreaming" added a viewable, editable memory summary, settings for which topics to prioritize, and a way to revert to manual-only memory.
- **Claude.** Memory launched for Team/Enterprise in Sept 2025 and for Pro/Max in Oct 2025. It is project-scoped: "Claude creates a separate memory for each project". It has an editable summary, incognito chats, import/export from other assistants, and a separate tool for searching past chats.
- **Gemini.** "Personal context" (memory of past chats) is on by default. "Personal Intelligence" is opt-in and connects Gmail, Photos, Search, and YouTube. It launched January 2026 (secondary sources).
- **Coding agents** use files a human writes (CLAUDE.md, AGENTS.md, Cursor rules) with scoping rules. For AGENTS.md, the nearest file to the code being edited wins and explicit user prompts override everything.
- **Cursor** shipped auto-generated "Memories" in 2025. Its memories documentation URL now serves the Rules page, which suggests the feature was folded back into human-written rules (unverified).

**What users complained about:**

- Simon Willison got an image of his dog in a pelican costume that included a "Half Moon Bay" sign, pulled from his chat history. He extracted the hidden "dossier" ChatGPT keeps on him: response preferences, topic highlights, user insights, and interaction metadata. His objection was that the system silently decided which context to inject.
- Users found it creepy when ChatGPT started using their names unprompted (April 2025).
- The Wall Street Journal reported, via secondary sources, a user whose divorce kept being brought up across months of conversations.
- The overly sycophantic GPT-4o release came out the same month as the expanded memory, and critics argued memory amplified it.

**Mechanism.** A global profile injected without checking relevance produces context bleed and over-personalization. Each fix the vendors shipped (project scoping, a visible summary, incognito mode, "prioritize topics" settings) restores *scoping and legibility*, not recall.

### 9. Persistent memory makes prompt injection persistent too

- **Johann Rehberger's "SpAIware" (2024)** used indirect prompt injection to write instructions into ChatGPT's memory, which then leaked data from *all future* conversations.
- **MINJA (NeurIPS 2025)** showed that an attacker who can only send ordinary queries can still plant malicious records in an agent's memory bank, which are later retrieved for other users.
- **Defenses.** The "Nous" belief-memory paper (Jun 2026) proposes a cap based on provenance: how much an item is trusted depends on where it came from, not on how confident its text sounds. Its reported result is that this resists poisoning by volume.
- **Why this matters here.** This project's main inputs are AI conversations and web research, so most incoming text is untrusted. Provenance has to be a first-class field, not metadata added later.

### 10. Benchmarks are weak measuring tools and the published numbers are disputed

**LoCoMo** (ACL 2024) has several problems:

- Conversations are only 16–26K tokens long.
- Its adversarial category, about 22% of the questions, is usually excluded. One community audit reports that the standard judge accepts many deliberately wrong answers and that errors in the answer key cap honest scores around 94% (unverified).
- Self-reported scores now sit at 92–96 (Mem0 92.5; Zep claims 94.7), so the benchmark is close to saturated.

**The numbers are disputed:**

- Mem0 measured Zep at 65.99. Zep re-ran itself at **75.14** and blamed Mem0's setup: both speakers were mapped to "user", timestamps were appended to the message text, and searches ran one after another instead of in parallel.
- A-Mem scored 48.38 in Mem0's run, far below its own paper's claims.
- MemPalace's claims of 100% on LongMemEval and LoCoMo turned out to be fixes targeted at known test questions, `top_k=50` on conversations with at most 32 sessions, and retrieval recall reported as if it were QA accuracy.
- Strict token-F1 and LLM-as-judge scoring can differ by **27.5 points** on the same outputs (Nous paper).

**Newer benchmarks fix part of this:**

- **LongMemEval** (ICLR 2025) tests five abilities, including knowledge updates and abstention.
- **BEAM** scales to 1M and 10M tokens and includes contradiction resolution and event ordering. As described by Mem0, it is not saturated: Mem0 scores 64.1 at 1M and 48.6 at 10M.
- **HaluMem** grades each memory operation separately.
- **LongMemEval-V2** targets web-agent histories of more than 100M tokens.
- **MERIT, STATE-Bench, and DolphinBench** measure whether tasks get done, not whether trivia is recalled.

**What none of them measure:** whether a system correctly represents *what a person believes and why*, how that changed, what is unresolved, or whether the person finds it useful.

### 11. The unit of memory across the field is a fact about the user, and the newest work is only starting to model beliefs

| System | Unit of memory | Update operation | History kept? | Epistemic status? |
|---|---|---|---|---|
| MemGPT/Letta | Labeled core-memory text blocks (size-limited) + archival passages + message log | Agent calls `core_memory_append` / `core_memory_replace`, archival insert; in later versions a sleep-time agent rewrites blocks | Message log yes; block edits overwrite (unverified whether versioned) | No |
| Generative Agents | Natural-language observation + importance + timestamp; reflections citing evidence | Append only; reflection adds higher-level nodes | Yes (never deletes) | No (importance ≠ confidence) |
| Mem0 (2025) | Atomic fact string (+ graph triples in Mem0^g) | LLM picks ADD/UPDATE/DELETE/NOOP against the top 10 similar memories | No for the vector store; graph marks invalid | No |
| Mem0 (2026) | Atomic fact, entity-linked | ADD only; resolve conflicts at retrieval | Yes | No |
| Zep/Graphiti | Episode (raw) → entity nodes + fact edges → communities | Extract, resolve entities, invalidate edges using both timelines | Yes (two timelines) | No |
| A-MEM | Zettelkasten-style note: content, keywords, tags, context description, embedding, links | Add note, link it, "evolve" neighbours (rewrite their context and tags) | Neighbour rewrites overwrite | No |
| LangMem | Semantic (fact collections or a profile document), episodic (examples), procedural (prompt rules) | Memory manager creates, updates, deletes; prompt optimizer rewrites instructions | Mostly no | No |
| HippoRAG 2 / GraphRAG / RAPTOR | Passages + OpenIE triples / communities / summary tree | Batch index; add only | Not applicable (static corpus) | No |
| MemoryBank | Conversation memories + daily summaries + personality profile | Ebbinghaus decay (retention = e^(−t/S); strength S grows when recalled) | Decays away | No |
| Reflexion / ReasoningBank / ACE | Verbal lessons / strategy items / playbook bullets with helpful and harmful counts | Append; ACE applies deltas and removes duplicates | Partial | Counters approximate reliability |
| Voyager | Executable skill (code), keyed by an embedding of its description | Add only after self-verification succeeds | Yes | Verified or not |
| ChatGPT / Claude / Gemini | Short sentences + a synthesized profile or summary + raw chat search | Background synthesis; user edits | Raw chats yes; summary overwritten | No |
| BeliefMem (2026), Nous (2026) | *Several candidate conclusions with probabilities* / categorical belief distributions | Noisy-OR / Bayesian updates weighted by source reliability | Yes | **Yes** |

**What the field systematically leaves out,** compared with a person's evolving understanding:

1. **Justification.** Facts are stored without the reasons for them, so a belief cannot be revised when its reason is undermined. There is no dependency tracking of the kind truth-maintenance systems did.
2. **Kind of statement.** "I believe X", "I decided X", "I want X", "I'm unsure whether X", and "the AI told me X" all collapse into "User: X".
3. **Contradictions.** They are treated as errors to fix, usually by letting the newer statement win. Often a contradiction is a productive open tension, a difference of context ("true at work, not at home"), or a mistake in the new information.
4. **Why the person changed their mind.** Even Zep's two timelines record *when*, not *why*.
5. **Open questions and goals.** These are not first-class. Only coding tools have something close: decision records and to-do files.
6. **Who the memory serves.** It exists so the *assistant* can personalize. Being legible to the person is an afterthought, which the 2025–2026 summary views are now patching.

The 2026 belief papers are the first to touch item 2 and to represent uncertainty. Their results are telling:

- **Nous.** Bayesian updating gives "minimal benefit … on standard benchmarks" but helps substantially when sources differ in trustworthiness. Standard benchmarks simply do not test what beliefs are for.
- **"Beyond Recall" (2026).** An interpretive "behavioral specification" layer compressed context about 25× and helped on questions that depend on interpretation, but "can interfere" on questions that require recall. An interpretive layer and a factual memory are different objects, and you need both.

## Ideas worth stealing

1. **Keep the raw input as a lossless layer that everything derived points back to.** From Zep's episode subgraph and Mastra's original messages. Every derived claim cites its source spans, so derivations can be checked and regenerated.
2. **Two timelines, and invalidation instead of deletion.** From Zep/Graphiti (`t_valid`/`t_invalid` plus `t'_created`/`t'_expired`). This project should add a third: *when the person held the belief*. That can differ from when the world-fact was true and from when the system recorded it.
3. **Raw values, enriched keys.** From the LongMemEval design study. Index by extracted facts, entities, and time, but return the original passage at a sensible granularity.
4. **Three dates on every observation.** From Mastra: when it was observed, the date it refers to, and that date relative to now. Add a priority marker and keep a stable, cacheable prefix.
5. **Choose the operation against nearby memories.** From Mem0: retrieve the top-k similar memories, then have an LLM choose the operation. The skeleton is good. This project needs a richer set of operations (Implication 4), and DELETE should become supersession.
6. **Itemized entries updated by delta, with usefulness counters.** From ACE, so the system never rewrites a whole summary in one go. Each entry has an ID and helpful/harmful counts, and duplicates are removed in a separate step.
7. **Reflection triggered by accumulated importance, with citations to evidence.** From Generative Agents. Higher-level insights become nodes that point back to their evidence, giving a tree of abstraction rather than a flat summary.
8. **A separate offline worker that owns memory writes.** From Letta (sleep-time agent) and Mastra (Observer/Reflector). The conversation-facing agent reads; the consolidation agent writes. This also enforces privilege separation against injection.
9. **New notes update their neighbours.** From A-MEM. When a new note links to old ones, the old notes' context is updated too. This should be done as *proposed* changes with history, not overwrites.
10. **Personalized PageRank seeded from the query's concepts.** From HippoRAG, for associative questions like "what else in my thinking connects to this?", which pure embedding retrieval handles poorly.
11. **Community summaries and recursive summary trees.** From GraphRAG and RAPTOR, for "what are my main themes and how have they shifted?". They must be maintained incrementally and must cite their members.
12. **A size-limited index file plus topic files read on demand.** From Claude Code auto memory: memory types, a `modified` timestamp, and a warning when the index grows past its limit. It is cheap, readable by humans and models, and diffable in git.
13. **Scoped instruction files where the nearest one wins.** From AGENTS.md and CLAUDE.md. Scopes such as project, domain, and life area stop context bleeding into unrelated work.
14. **Rewrite time-sensitive statements.** From ChatGPT Dreaming: "going to X in July" becomes "went to X in July" once the date passes. Generalize this to statements that are planned, intended, or expected.
15. **Add only what has been verified, and reuse it.** From Voyager's skill library. The analogue here: promote a claim to "established" only after the person confirms it or independent evidence agrees.
16. **Several candidate conclusions with probabilities; updates weighted by source reliability; trust capped by provenance.** From BeliefMem and Nous. This is the most direct prior art for representing uncertainty.
17. **Spaced-repetition-style strength that grows each time a memory is used.** From MemoryBank. Use it to decide *what to surface* to the person, never to delete.
18. **Visible, editable memory, incognito mode, and import/export.** From the Claude and ChatGPT products. This is the minimum users now expect.

## Pitfalls and anti-patterns

- **Claiming accuracy gains when the history fits in context.** On LoCoMo, full context (72.9) beat Mem0 (66.9 and 68.4). Memory layers there trade accuracy for cost and latency. Always report the full-context and files-plus-grep baselines.
- **Destructive updates.** Mem0's DELETE operation erases history, and Mem0 itself moved to ADD-only in 2026. A person's knowledge base that loses "what I used to think" fails at the core purpose.
- **Rewriting one summary in a loop.** ACE showed the summary can collapse from 18K to 122 tokens and end up *below* the no-memory baseline. Every "dreaming" or "synthesize the profile" design has to defend against this.
- **Extraction that discards the source.** Per HaluMem, extraction recall is often under 60% and Mem0 falls to 3% on long histories. Per LongMemEval, storing facts as the values hurts overall accuracy. If the raw text is gone, those losses are permanent.
- **Extraction that only looks at the user.** It drops what the assistant contributed (Zep −17.7% on single-session-assistant questions). Here that would discard the AI explanations a person actually learned from.
- **Global profile injected without a relevance check.** This produced the Half Moon Bay sign in the pelican image, the divorce brought up for months, and the unprompted names. Memory needs a relevance gate and scopes, and the person needs to see what was injected.
- **Personalization feeding sycophancy.** A system that remembers and then mirrors what you believe entrenches your views. For a knowledge system that should *improve* understanding, this is a failure of purpose, not a cosmetic issue.
- **Treating everything written to memory as trusted.** SpAIware and MINJA show that one injection can last forever. Separating instructions from content and capping trust by provenance are required, not optional.
- **Elaborate structures the model can't navigate.** Letta's result, and Zep's memory footprint of more than 600K tokens per conversation in Mem0's (disputed) measurement, both warn against structure that doesn't pay for itself.
- **Evaluating on short tenure.** The "tenure crossover" result shows rankings can flip between 3 and 9 weeks of use.
- **Benchmark theatre.** Comparing your own system against badly configured competitors (Mem0 on Zep). Tuning on test questions, inflating `top_k`, and reporting retrieval recall as QA accuracy (MemPalace). Mixing scoring methods that differ by 27.5 points. Trust only our own held-out, longitudinal evaluation.
- **Using importance or recency decay to *forget* a person's knowledge.** MemoryBank-style decay makes sense for a companion bot's small talk. For a person's intellectual history, decay should lower *salience*, never delete.
- **Leaving it to the model to pick between stale and current versions at read time.** MERIT found agents acted correctly on retrieved values only 55% of the time. If supersession is known, record it explicitly. Don't make the model guess.

## Implications for this project

1. **Build the baselines before any architecture.** Baseline A: raw transcripts and notes as files, with an agent using `grep` and semantic search (Letta-style). Baseline B: full context with a long-context model on the most recent N tokens. Baseline C: an append-only dated observation log (Mastra-style). *Falsifiable:* any structured design must beat the best of A, B, and C on our own evaluation by a margin set in advance (e.g., ≥10 points on belief and evolution questions) at similar cost. Otherwise, use the simpler design.
2. **Make the raw source layer immutable, and require every derived item to cite it.** Store conversations, notes, and readings verbatim with stable IDs and spans. *Test:* 100% of derived claims resolve to at least one source span. Throwing away all derived layers and regenerating them from sources produces a substantially similar current view.
3. **Make the core unit a *claim with epistemic metadata*, not a fact about the user.** Minimum fields:
   - kind: belief, observation, decision, goal, question, hypothesis, preference, or instruction
   - content in the person's own framing
   - scope or context
   - confidence, categorical to start
   - status: active, tentative, superseded, retracted, or contested
   - justification links ("because" → other claims or sources)
   - provenance: who asserted it — the person, the AI, or an external source — and whether the person endorsed it
   - three timelines: valid-time, record-time, and held-time

   *Test:* a hand-labelled sample of 200 claims from real sessions fits this schema with fewer than 10% needing an "other" kind.
4. **Replace ADD/UPDATE/DELETE with operations that keep history.** The set: ADD, SUPPORT (new evidence for an existing claim), CHALLENGE (counter-evidence), REFINE (narrow scope or sharpen wording, keeping a link to the old version), SUPERSEDE (with a reason), RETRACT (with a reason), MERGE (deduplicate, keeping aliases), and LINK-AS-TENSION (record a contradiction and leave it open). Hard delete exists only as a privacy action the user starts. *Test:* nothing an operation does loses information. Replaying the operation log rebuilds any past state.
5. **Separate append-on-the-hot-path from offline consolidation, and have consolidation produce reviewable *proposals*.** Capture is cheap and immediate. A background consolidator proposes merges, supersessions, tensions, and theme summaries as diffs, which the person accepts or rejects, at least at first. *Measure* the acceptance rate and review time per week. If the person won't spend about 10 minutes a week reviewing, automate the high-confidence classes and keep review only for belief-level changes.
6. **Never rewrite a summary as one block.** Human-readable topic pages and the AI-facing profile are *generated views* over itemized claims with IDs, updated by deltas in the ACE style. *Test:* across 50 consolidation cycles on a fixed corpus, the number of claims the views cover never drops unless a recorded RETRACT or MERGE explains the drop.
7. **Build an evaluation suite about understanding, not trivia recall.** Questions such as:
   - "What do I currently believe about X, and why?"
   - "When and why did I change my mind about Y?"
   - "What tensions exist in my views on Z?"
   - "What open questions am I carrying on topic T?"
   - "What did I decide about D, and what was the reasoning?"

   Also include abstention ("I never formed a view on that"), statements that have gone stale, and a split for questions about what the AI said. Run it *longitudinally* on the user's own data over 8 weeks or more because of the tenure crossover. Keep LongMemEval and LoCoMo only as sanity checks.
8. **Give humans and AI different views over the same claim store.**
   - The human view: topic pages, a timeline of changes of mind, and an inbox of open tensions and questions.
   - The AI view: a size-limited, scoped index in a stable prefix (Claude Code `MEMORY.md` pattern plus Mastra cacheability), with on-demand retrieval tools that return claims, their justifications, *and* raw source passages.

   *Test:* the same evaluation answered through each view. The human view should win on the person's own judgment of usefulness, and the AI view should win on cost per correct answer.
9. **Make provenance carry trust.** Separate "the AI said X" from "I endorsed X" from "I believe X". Content from AI conversations and the web never becomes an *instruction* to the AI-facing layer without the person's explicit endorsement. *Test:* a red-team set of injected instructions planted in imported conversations; target 0 of them reaching the instruction layer.
10. **Scope by default.** Every claim has a scope: project, domain, life area, or global. The AI-facing context includes only claims for the active scope and anything explicitly global, which avoids the Half Moon Bay problem. *Test:* count how often injected memory is judged irrelevant on a sample of real sessions, aiming for under 10%.

## Tensions and open questions

- **Resolve conflicts at write time or read time?** Mem0 (2026) chose read time, for history and speed. MERIT's evidence favours write time for updated facts. The proposed answer is both: an append-only log plus a materialized current view. That still has to be tested on our data. Is the materialized view kept consistent enough to trust?
- **How fine-grained should a unit be?** Atomic claims lose context (LongMemEval found fact values hurt accuracy). Pages are hard to update surgically. Candidate: claims as the unit of *update*, passages and pages as the unit of *reading*. Is a claim schema too heavy for a person to use in practice?
- **Automatic versus human-curated consolidation.** The products (Dreaming, Claude memory) went fully automatic for scale. A personal system may want the person in the loop, because synthesis is how understanding forms. Should the AI *propose* syntheses for the person to write or accept, rather than doing them? This tension sits on the line between memory and learning, and it needs a user study (n=1 is fine here).
- **Is a graph worth it?** File and grep agents are competitive on recall. Graphs help with associative and multi-hop questions (HippoRAG) and maybe with long tenure ("Ground Truth First"). Should links be stored as plain text in Markdown, a typed graph database, or both? Decide only after the baselines in Implication 1.
- **How to represent uncertainty.** Probabilities (BeliefMem, Nous) or categories (sure / leaning / unsure / contested)? People are poorly calibrated, and so are LLMs asked for confidence. What is the confidence *for*: retrieval ranking, deciding what to show the person, or telling the AI how to hedge?
- **Forgetting.** For a person, what should fade? Proposed answer: salience decays, existence does not. Should superseded beliefs still appear in AI context, for example "you used to think X"? When is that helpful and when is it creepy?
- **Should the AI's statements become the person's knowledge?** Much of a person's learning starts as AI explanations. When does "the AI said X" become "I believe X"? On explicit endorsement, on repeated use, or never automatically?
- **Coherence versus faithfulness.** The project's motivation is turning fragments into "coherent understanding", but forcing coherence destroys real contradictions. The system has to keep coherence (a synthesized view) separate from consistency (no unresolved tensions) and should not optimize for the latter.
- **Sycophancy and lock-in.** A memory of the person's beliefs, fed to an assistant, may strengthen the assistant's tendency to agree. Should the AI-facing view deliberately include counter-evidence and the person's own past doubts?
- **Portability.** The vendors now support memory import/export, but formats are ad hoc. Is a plain-text, git-able canonical format (Markdown plus front-matter) enough as the system of record, with indexes as caches that can be rebuilt?
- **Evaluation ground truth.** Who labels "what I believe and why" over time? Probably the user, through periodic review. How do we keep the evaluation from being contaminated by the system's own suggestions?

## Sources

- Packer et al., "MemGPT: Towards LLMs as Operating Systems" (2023). https://arxiv.org/abs/2310.08560
- Letta, "Sleep-time Compute" blog and paper: Lin, Snell, Wang, Packer, Wooders, Stoica, Gonzalez, "Sleep-time Compute: Beyond Inference Scaling at Test-time" (Apr 2025). https://www.letta.com/blog/sleep-time-compute ; https://arxiv.org/abs/2504.13171
- Letta, "Benchmarking AI Agent Memory: Is a Filesystem All You Need?" (Aug 2025). https://www.letta.com/blog/benchmarking-ai-agent-memory
- Park et al., "Generative Agents: Interactive Simulacra of Human Behavior" (UIST 2023). https://arxiv.org/abs/2304.03442
- Chhikara et al., "Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory" (Apr 2025). https://arxiv.org/abs/2504.19413
- Mem0 research page (2026 ADD-only algorithm; LoCoMo 92.5 / LongMemEval 94.4 self-reported). https://mem0.ai/research
- Mem0, "LoCoMo vs. LongMemEval vs. BEAM: The 2026 AI Memory Benchmark Guide" (vendor summary; source for BEAM, STATE-Bench, DolphinBench descriptions). https://mem0.ai/blog/ai-memory-benchmarks-in-2026
- Rasmussen et al., "Zep: A Temporal Knowledge Graph Architecture for Agent Memory" (Jan 2025). https://arxiv.org/abs/2501.13956
- Zep, "Lies, Damn Lies, & Statistics: Is Mem0 Really SOTA in Agent Memory?" https://www.getzep.com/blog/lies-damn-lies-statistics-is-mem0-really-sota-in-agent-memory/
- Xu et al., "A-MEM: Agentic Memory for LLM Agents" (NeurIPS 2025). https://arxiv.org/abs/2502.12110
- Gutiérrez et al., "HippoRAG" (NeurIPS 2024) https://arxiv.org/abs/2405.14831 and "From RAG to Memory: Non-Parametric Continual Learning for Large Language Models" (HippoRAG 2, ICML 2025) https://arxiv.org/abs/2502.14802
- Edge et al., "From Local to Global: A Graph RAG Approach to Query-Focused Summarization" (2024). https://arxiv.org/abs/2404.16130
- Sarthi et al., "RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval" (ICLR 2024). https://arxiv.org/abs/2401.18059
- Zhong et al., "MemoryBank: Enhancing Large Language Models with Long-Term Memory" (2023). https://arxiv.org/abs/2305.10250
- Shinn et al., "Reflexion: Language Agents with Verbal Reinforcement Learning" (2023). https://arxiv.org/abs/2303.11366
- Wang et al., "Voyager: An Open-Ended Embodied Agent with Large Language Models" (2023). https://arxiv.org/abs/2305.16291
- Zhang et al., "Agentic Context Engineering: Evolving Contexts for Self-Improving Language Models" (ICLR 2026). https://arxiv.org/abs/2510.04618
- Ouyang et al. (Google), "ReasoningBank: Scaling Agent Self-Evolving with Reasoning Memory" (2025). https://arxiv.org/abs/2509.25140
- "Memory-R1: Enhancing LLM Agents to Manage and Utilize Memories via Reinforcement Learning" (2025; ACL 2026). https://arxiv.org/abs/2508.19828
- "Mem-α: Learning Memory Construction via Reinforcement Learning" (2025). https://arxiv.org/abs/2509.25911
- "MemOS: An Operating System for Memory-Augmented Generation" (2025). https://arxiv.org/abs/2505.22101 ; https://arxiv.org/abs/2507.03724
- "Memory in the Age of AI Agents" (survey, Dec 2025). https://arxiv.org/abs/2512.13564
- Maharana et al., "Evaluating Very Long-Term Conversational Memory of LLM Agents" (LoCoMo, ACL 2024). https://arxiv.org/abs/2402.17753
- Wu et al., "LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory" (ICLR 2025). https://arxiv.org/abs/2410.10813
- "LongMemEval-V2: Evaluating Long-Term Agent Memory Toward Experienced Colleagues" (2026). https://arxiv.org/abs/2605.12493
- "HaluMem: Evaluating Hallucinations in Memory Systems of Agents" (Nov 2025). https://arxiv.org/abs/2511.03506
- Mishra & Mishra, "When Does Memory Help? A Cost-Aware Evaluation of Long-Term Memory in Tool-Using LLM Agents" (MERIT, Jul 2026). https://arxiv.org/abs/2609.05441
- Spencer, "Ground Truth First: A Longitudinal Evaluation Instrument for Agent Memory, and the Tenure Crossover in Memory-Architecture Rankings" (Jul 2026). https://arxiv.org/abs/2607.21962
- Liao et al., "Belief Memory: Agent Memory Under Partial Observability" (May 2026). https://arxiv.org/abs/2605.05583
- Singh, "When Does Belief-Based Agent Memory Help? Reliability-Conditional Updating and Provenance-Capped Poisoning Defense" (Jun 2026). https://arxiv.org/abs/2606.22030
- Gulaya, "Beyond Recall: Behavioral Specification as an Interpretive Layer for AI Personalization" (May 2026). https://arxiv.org/abs/2605.28969
- Mastra, "Observational Memory: 95% on LongMemEval." https://mastra.ai/research/observational-memory
- Vectorize, "MemPalace Benchmarks Debunked." https://vectorize.io/articles/mempalace-benchmarks
- D'Erme, "The AI memory benchmark everyone quotes forbids saying 'I don't know'" (community audit of LoCoMo; claims unverified). https://dev.to/gde03/the-ai-memory-benchmark-everyone-quotes-forbids-saying-i-dont-know-o1n
- Dong et al., "Memory Injection Attacks on LLM Agents via Query-Only Interaction" (MINJA, NeurIPS 2025). https://arxiv.org/abs/2503.03704
- The Hacker News, on Rehberger's "SpAIware" ChatGPT memory exploit (Sept 2024). https://thehackernews.com/2024/09/chatgpt-macos-flaw-couldve-enabled-long.html
- OpenAI, "Memory and new controls for ChatGPT" (updated through 2025). https://openai.com/index/memory-and-new-controls-for-chatgpt/
- OpenAI, "Dreaming: Better memory for a more helpful ChatGPT" (Jun 4, 2026; page returned 403, details via secondary coverage). https://openai.com/index/chatgpt-memory-dreaming ; https://gigazine.net/gsc_news/en/20260605-chatgpt-memory-dreaming-v3 ; https://letsdatascience.com/news/openai-upgrades-chatgpt-memory-architecture-for-fresher-pers-b26b51d5
- Simon Willison, "I really don't like ChatGPT's new memory dossier" (May 2025). https://simonwillison.net/2025/May/21/chatgpt-new-memory/
- TechCrunch, "ChatGPT is referring to users by their names unprompted, and some find it creepy" (Apr 2025). https://techcrunch.com/2025/04/18/chatgpt-is-referring-to-users-by-their-names-unprompted-and-some-find-it-creepy
- Anthropic/Claude, "Memory" announcement (Sept–Oct 2025). https://claude.com/blog/memory
- Anthropic, Memory tool documentation. https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool
- Claude Code docs, "How Claude remembers your project" (CLAUDE.md, auto memory). https://code.claude.com/docs/en/memory
- AGENTS.md (Agentic AI Foundation / Linux Foundation). https://agents.md/
- Cursor Rules docs (memories URL now serves Rules). https://cursor.com/docs/context/memories
- Gemini "Personal Intelligence" (Jan 2026) and personal context: secondary coverage, e.g. https://mexicobusiness.news/cloudanddata/news/google-launches-gemini-personal-intelligence (unverified against Google primary source)
