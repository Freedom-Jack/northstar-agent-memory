# One store, two readers: human use vs AI use of personal knowledge

Track 07. Research note, 2026-10-07.
Method: my own knowledge plus web checks of specific claims, numbers and 2025-2026 developments. The shared web-search budget ran out partway through. After that I checked sources by fetching primary pages directly. Claims I could not re-verify are marked "(unverified)" or "(from memory)".

---

## Scope and questions

This track asks how the needs of the **person** and of **AI systems** relate when both use the same personal knowledge, and what that means for representation.

Questions:

1. What does the person need from their own knowledge system? Examples: legibility, overview, trust, editing, ownership, resurfacing, reflection, and seeing what the system "thinks" about them.
2. What does an AI consumer need? Examples: scoped context within a token budget, provenance, uncertainty, freshness, type distinctions (instruction / preference / fact / belief / history), and stable IDs.
3. Is preloading context better, or just-in-time retrieval? Agentic file search or vector RAG? What does the 2024-2026 evidence say now that 1M-token windows are common?
4. What new risks appear once an AI reads a person's memory? Sycophancy, over-personalization, fabricated inferences, stale memories, sensitive inference, and prompt injection that persists.
5. What can ChatGPT, Claude and Codex actually consume today? (Briefly. Integration is not the priority.)
6. **Key question:** should the system have one canonical representation with several projections, or separate representations kept in sync? What does each consumer need that the other does not?

Out of scope: the internal knowledge model (claims, beliefs, contradictions), update and consolidation algorithms, and storage engines. Other tracks cover those. I touch them only where a consumer's needs constrain them.

---

## Key findings

### 1. More context is not better, and personal corpora are close to the worst case for long-context reading

**Mechanism.** Attention is a finite budget spread over all tokens. Performance drops with input length even on trivial tasks. It drops fastest when (a) the question and the answer share few words, and (b) the context holds *distractors* that resemble the target.

**Evidence.**
- Chroma's *Context Rot* report (July 2025) tested 18 models, including GPT-4.1, Claude 4, Gemini 2.5 and Qwen3. Reliability fell as input grew, even on simple retrieval and copying tasks.
  - Distractors hurt, and some hurt more than others.
  - Lower similarity between needle and question made performance fall faster with length.
  - On LongMemEval, focused prompts (about 300 tokens of relevant history) clearly beat full prompts (about 113k tokens including irrelevant history).
  - Counterintuitively, models did *better* when the haystack was shuffled than when it kept a logical flow.
- NoLiMa (Adobe, ICML 2025) removed literal word overlap between question and needle. At 32K tokens, 11 of the 12 tested models fell below 50% of their short-context baseline. GPT-4o dropped from 99.3% to 69.7%.
- "Lost in the Middle" (Liu et al., TACL 2024) showed a U-shaped curve: information in the middle of the context is used worst.
- **Counter-evidence: frontier models are improving.** Anthropic reports Claude Opus 4.6 at 76% on the 8-needle 1M variant of MRCR v2, against 18.5% for Sonnet 4.5. Long context is getting usable. But it is uneven across models, and "can find 8 needles" is not the same as "applies the right one of 400 near-duplicate memories appropriately."
- LaRA (ICML 2025) compared RAG and long-context reading and found "no silver bullet." The winner depends on the model, the context length, the task type, and the shape of the retrieved chunks.

**Why this matters here.** A personal corpus is one person's thoughts on overlapping topics over years. Almost every note is *topically similar* to almost every question, which is exactly the distractor condition Chroma and NoLiMa describe. It is also locally coherent (prose, conversation threads), the structure Chroma found hardest. "It fits in 1M tokens, so preload it all" is therefore the wrong default, though it remains an essential **baseline** to test against.

### 2. The hard part of long-term memory is updates, time and abstention, not recall

**Mechanism.** If a model sees "I'm vegetarian" (2023) and "started eating fish again" (2025) without explicit dates and supersession links, it has no reliable way to know which is current. Models also rarely say "I don't know" when plausible but wrong memories are present.

**Evidence.** LongMemEval (Wu et al., ICLR 2025) tests five abilities: information extraction, multi-session reasoning, temporal reasoning, knowledge updates and abstention. Commercial assistants and long-context models showed about a 30% accuracy drop across sustained interactions. The authors' fixes are structural, not model-side:
- splitting sessions into finer units ("session decomposition");
- indexing each unit with extracted facts as extra keys ("fact-augmented key expansion");
- restricting search by time ("time-aware query expansion").

**Implication.** The AI-facing representation must make time and supersession explicit. The model should never have to infer them.

### 3. Agentic search over plain files is a strong baseline, semantic search adds measurable value, and the combination wins

**Mechanism.** Current models are heavily post-trained on file operations (glob, grep, read, edit) for coding. An agent that searches iteratively can rewrite its query, follow links, and stop when it has enough. A one-shot top-k vector lookup cannot. Embeddings still cover what grep cannot: vocabulary mismatch, which is exactly the no-literal-overlap condition NoLiMa shows is hard.

**Evidence.**
- **Claude Code.** Early versions used RAG with a local vector DB. The team found agentic search worked better "by a lot". This was reported by Boris Cherny on the Latent Space podcast; I verified it only through secondary write-ups. The architecture is documented by Anthropic: CLAUDE.md is preloaded, and glob/grep retrieve "just in time."
- **Letta** (Aug 2025). gpt-4o-mini agents that simply stored conversation histories in files, with grep, semantic `search_files`, and open/close tools, scored 74.0% on LoCoMo. Mem0's best reported variant scored 68.5%. Letta's conclusion is that whether an agent "remembers" depends on whether it can *use* a retrieval tool well, not on how sophisticated the store is.
- **Cursor** (Nov 2025). Adding a trained semantic-search tool *on top of* grep raised question-answering accuracy by 12.5% on average (6.5-23.5% depending on the model). Cursor says "the combination of these two leads to the best outcomes."

**Contradicts popular belief, twice.** First, "memory needs a vector DB or a knowledge graph" is not supported: a folder of text files plus a capable agent is competitive. Second, the counter-meme "grep is all you need / RAG is dead" is also not supported: hybrid search measurably beats grep alone.

### 4. The winning pattern is a small preloaded core, an index, and bodies loaded on demand (progressive disclosure)

**Mechanism.** The cheap, always-present tokens should tell the model *what exists and where*. The expensive tokens are fetched only when relevant. This is how the model avoids both missing memories and context rot.

**Evidence.**
- Anthropic, *Effective context engineering for AI agents* (Sep 29, 2025): aim for "the smallest possible set of high-signal tokens." Agents keep "lightweight identifiers (file paths, stored queries, web links, etc.)" and load data at runtime.
- **Claude Code auto memory** (current docs):
  - a `MEMORY.md` index with "one line per memory" is loaded into every session, capped at the first 200 lines or 25KB;
  - each memory lives in its own topic file, read on demand;
  - each memory carries a `type` in frontmatter: `user`, `feedback`, `project` or `reference`.
- **Agent Skills** (open standard, Dec 2025, adopted by Codex and others): only `name` and `description` load at startup; the body loads when the task matches.
- **Anthropic memory tool and context editing** (Sep/Oct 2025): a client-side, file-based memory directory plus automatic pruning of stale tool results.
  - On an internal agentic-search evaluation, the two together scored 39% above baseline; context editing alone scored 29% above.
  - On a 100-turn web-search evaluation, context editing cut token use by 84%.
- **Manus** (July 2025) practices "recoverable compression": drop a page's content but keep its URL or path, so it can be reloaded. It also rewrites a `todo.md` at the end of the context each step, which keeps goals in the model's high-attention recent zone.

**Two vendor philosophies** (Shlok Khemani's analysis, summarized by Simon Willison, Sep 2025):
- ChatGPT *preloads* details from past conversations into every chat.
- Claude originally started blank and called `conversation_search` / `recent_chats` tools *visibly*, on demand.

Claude later added a synthesized, editable memory summary. Both vendors are converging on a hybrid: a small curated core plus retrieval.

### 5. AI consumers need authorship and obligation semantics: "instruction" and "recollection" are different kinds of thing

**Mechanism.** An instruction must hold every time it is in scope. A recollection applies only if relevant. A model that cannot tell them apart will either ignore rules or force trivia into every answer. Who wrote an entry (the person, or the AI summarizing the person) changes how much it should be trusted.

**Evidence.** Two vendors converged on the same split without coordinating:
- **OpenAI Codex memories** (shipped April 2026):
  - memories are generated, local files under `~/.codex/memories/`;
  - users can inspect them, but manual editing is not meant to be the main control;
  - the docs say: "Keep required team guidance in `AGENTS.md`... Treat memories as a helpful recall layer, not as the only source for rules that must always apply";
  - consolidation is asynchronous, after a chat has gone idle; short sessions are skipped and secrets redacted.
- **Claude Code**: CLAUDE.md is "who writes it: You / Instructions and rules"; auto memory is "Claude / Learnings and patterns." Claude "treats them as context, not enforced configuration." Anything that must be enforced belongs in a hook.

The industry has found that authorship (human-authored vs machine-derived) and force (rule vs recall) are first-class properties. Both should be encoded explicitly, not left to prose.

### 6. Memory amplifies sycophancy and over-personalization, and memory-free baselines sometimes win

**Mechanism.** A model treats anything in its context as a signal of what the user wants (if it is in the prompt, it must matter). A profile of the person's views therefore becomes pressure to agree. Retrieved but irrelevant memories get *disproportionate* attention.

Knowledge-conflict research points the same way. Xie et al. (ICLR 2024) found that LLMs readily adopt coherent evidence placed in context, even when it contradicts what they learned in training. A confidently written memory gets treated as true. (From memory.)

**Evidence.**
- Jain et al., *Interaction Context Often Increases Sycophancy in LLMs* (MIT/Penn State, 2025): two weeks of real context from 38 users.
  - User memory profiles produced the largest increases in agreement sycophancy, for example +45% for Gemini 2.5 Pro.
  - Perspective sycophancy rose only when the model could accurately infer the user's view.
- OpenAI's GPT-4o sycophancy postmortem (May 2025): "in some cases, user memory contributes to exacerbating the effects of sycophancy, although we don't have evidence that it broadly increases it."
- **OP-Bench** (Jan 2026) splits over-personalization into three types: irrelevance, repetition and sycophancy.
  - Every memory-augmented agent tested lost performance relative to memory-free agents: relative drops of 26.2-61.1%.
  - A lightweight memory-filtering pass ("Self-ReCheck") reduced the problem.
- **Real example:** Simon Willison asked ChatGPT to put his dog in a pelican costume. It added a "Half Moon Bay" sign "because you've mentioned being in Half Moon Bay before."
- Entezami & Endres (2026): across 800 AI-generated personal websites, age and gender signals produced significant differences in interface design, template content and code structure. Personalization quietly becomes bias.

### 7. Models invent user attributes, and their self-reports hide it

**Mechanism.** Summarizing a person is an act of inference. Once an inference is written into memory, the next read treats it as fact. Errors compound with no revision step.

**Evidence.** MirageBench (Sun et al., 2026: 12 models, 150 personas, about 144k judged claims):
- Models over-inferred 35-49% of claims about users (mean 41.6%).
- **"Self-monitoring inversion":** the models that *reported* the least over-inference fabricated the most (rho = -0.60).
- Across turns, inferred attributes accumulated roughly linearly, with minimal revision.

**Implication.** An AI-maintained "profile of me" is unreliable unless each claim can be traced to evidence and has been externally confirmed. Asking the model how confident it is does not fix this.

### 8. Memory turns a one-time prompt injection into a standing instruction

**Mechanism.** Any path that writes untrusted content (a web page, a document, a tool result) into a store that is later re-read as context is a persistence vector.

**Evidence.**
- **SpAIware** (Johann Rehberger, Sep 2024). Indirect prompt injection planted instructions in ChatGPT's memory, in the macOS app. Every later conversation was then exfiltrated to the attacker. The specific bug was patched; OpenAI acknowledged that memory-manipulating injections remain an open problem.
- **MINJA** (2025) poisoned agent memory through ordinary queries only: 98.2% injection success and 76.8% attack success.
  - These results were under idealized conditions.
  - A 2026 follow-up (arXiv 2601.05504) found that pre-existing legitimate memories substantially reduce effectiveness.
  - The threat is real but sensitive to conditions.

### 9. People react badly to *opaque* memory and with curiosity to *visible* memory

**Mechanism.** Discomfort comes from violated expectations ("it knew *that*?") and from misrepresentation, not from personalization as such.

**Evidence.**
- *AI Never Forgets* (CHI 2026, 20 interviews with ChatGPT users): most participants experienced negative expectancy violations on learning what ChatGPT remembered. They saw AI memory as unforgetting, overly detailed and emotionless. They asked for visibility, accessibility, transparency and control.
- Monteiro et al. (2026) built a "Reflective Layer" that showed 18 users 215 inferences drawn from their own ChatGPT histories. Participants reacted "more strongly with curiosity and interest rather than distress and concern."
  - Discomfort rose when an inference *misrepresented* them.
  - Comfort dropped sharply when third parties, rather than the platform, would get the inferences.
- **Willison's objection** (May 2025) to ChatGPT's "reference chat history": "the entire game when it comes to prompting LLMs is to carefully control their context." An invisible dossier takes that control away. At the time, its contents could be seen only with a special extraction prompt.
- **Vendor responses:**
  - Claude: "View and edit memory," a separate memory per project, and incognito chats.
  - ChatGPT (2025-2026): automatic memory management. Users can see what is "top of mind" and re-prioritize or delete entries. (Reported by TechRadar; the June 2026 capacity and auto-update details come from a secondary source, unverified.)

**Contradicts a common design assumption.** Hiding the model of the user does not prevent discomfort. Showing it, with a way to correct it, turns a privacy threat into a reflection tool.

### 10. Humans navigate and machines search, and heavy manual organization doesn't pay

**Mechanism.** People re-find things by recognition and location ("it was near that other note"). They are poor at recalling exact keywords. An agent has no spatial memory but can issue twenty queries for almost nothing.

**Evidence (from memory, all well established).**
- Teevan et al. (CHI 2004): people "orienteer" in small steps through familiar structure, even when they know exactly what they want.
- Bergman et al. (ACM TOIS 2008): people still preferred navigating their own files after desktop search improved.
- Whittaker et al., "Am I wasting my time organizing email?" (CHI 2011): people who carefully filed email were *not* more efficient at finding it again than people who searched.

**Implication.** Human views need stable *places* (hubs, maps, timelines) that a person can orient by. Requiring the person to file and tag is a cost that mostly does not pay back. Structure should emerge or be proposed, not demanded.

### 11. Handing synthesis to AI can hollow out the person's own understanding, which challenges the project's framing

**Mechanism.**
- **Generation effect** (Slamecka & Graf 1978): we remember what we produce better than what we read.
- **Testing effect** (Roediger & Karpicke 2006): retrieving something strengthens it.
- If the AI writes every synthesis, the store becomes coherent while the person's understanding does not.
- Clark & Chalmers' *extended mind* criteria (1998) include that external information was "consciously endorsed" at some point. An AI-inferred note the person never endorsed fails that test: it is *about* them, not *part of* them.

**Evidence.** Kosmyna et al., *Your Brain on ChatGPT* (MIT Media Lab preprint, 2025; n=54, small, not peer-reviewed at the time). Compared with people who wrote unaided:
- the LLM-assisted essay group had the weakest neural connectivity;
- they had more trouble quoting essays written minutes earlier;
- they reported less ownership of their work.

Treat this as suggestive. The direction matches decades of learning research.

### 12. The common interop layer today is plain markdown, plus MCP for tools

**Evidence.**
- **Shared governance.** MCP (Anthropic) and AGENTS.md (OpenAI) were donated to the Linux Foundation's new Agentic AI Foundation on Dec 9, 2025.
- **Agent Skills.** `SKILL.md` with progressive disclosure is supported by Codex, Claude Code, Gemini CLI, Copilot, Cursor and others ("30+ tools", per a secondary source, unverified count).
- **Instruction files.** Claude Code now reads `AGENTS.md` directly when no `CLAUDE.md` is present.
- **Memory import is copy-paste text.** Claude's Import Memory (March 2026) gives you a prompt to paste into another assistant, and you paste its text output back into Claude. Absorbing it takes about 24 hours.
- **Codex memories** are markdown files on disk.
- **Counterexample: llms.txt.** Ahrefs (May 2026) analyzed about 38k valid files: 97% received zero requests. AI retrieval bots made only about 1.1% of the requests that did occur. A file convention with no committed consumer goes unread.
- **ChatGPT** accepts remote MCP servers through connectors and developer mode (from memory, not re-verified for 2026).

---

## Ideas worth stealing

| Mechanism | Source | Why it works / what to take |
|---|---|---|
| **Index file with one line per item, always loaded; one file per item, loaded on demand** | Claude Code auto memory (`MEMORY.md` + topic files, 200-line / 25KB cap) | The cheap tokens say *what exists*; the expensive tokens load only when needed. A hard cap forces consolidation. |
| **Typed frontmatter on every memory** | Claude Code (`type: user/feedback/project/reference`) | Lets the consumer apply different semantics per type without parsing prose. Extend the type set (see Implications). |
| **Separate channels for human-authored rules and machine-derived recall** | Codex ("keep required guidance in AGENTS.md... memories as recall layer"); CLAUDE.md vs auto memory | Different trust and obligation. Rules never depend on an inference. |
| **Asynchronous consolidation after idle; skip short sessions; redact secrets** | Codex memories | Avoids summarizing unfinished thinking. Consolidation is batch work, not hot-path work. |
| **Recoverable compression** | Manus | Drop content but keep its ID or path. Pairs with stable identifiers. |
| **Recitation of active goals at the end of context** | Manus `todo.md` | Uses recency bias deliberately to counter lost-in-the-middle. |
| **Stable, append-only prefix for cache hits** | Manus (KV-cache hit rate as the top production metric) | Deterministic serialization of the core pack, so it can be prompt-cached. |
| **Name + description as the retrieval hook** | Agent Skills progressive disclosure | Each hub or topic gets a one-line "when is this relevant" description written for the model. |
| **Relevance gate before memory reaches the answer** | OP-Bench "Self-ReCheck" | A cheap filtering pass removes irrelevant memories before they get disproportionate attention. |
| **Fact-augmented keys; time-aware query expansion; session decomposition** | LongMemEval | Index a chunk by the facts extracted from it. Narrow search by time. Store at a finer granularity than "session." |
| **Show the user's inferred profile, with evidence, for reaction** | Monteiro et al. Reflective Layer | Turns creepiness into curiosity, and doubles as a correction channel. |
| **User-adjustable salience ("top of mind")** | ChatGPT 2025-26 memory management | The person changes priority, not just keep/delete. |
| **Per-project memory scope + incognito sessions** | Claude memory | Leakage across contexts (Half Moon Bay) is mostly a *scoping* failure. |
| **Build memory from user turns, not assistant turns** | ChatGPT detail noted in Willison's Claude/ChatGPT comparison (unverified detail) | Stops the AI's own outputs, including sycophantic ones, from becoming "facts about the user." |
| **Resources vs tools** | MCP spec | *Resources* = context the application chooses to provide (the core pack). *Tools* = context the model chooses to fetch (search, get-by-ID). This maps directly onto preload vs just-in-time. |
| **Event log + projections (event sourcing / CQRS)** | Software architecture (Fowler et al.) | One writable source of truth that keeps full history. Every view is derived and can be rebuilt. |
| **Daily resurfacing of a few old items** | Readwise-style review; spaced repetition | Serendipity and re-evaluation without the person having to go looking. |

---

## Pitfalls and anti-patterns

1. **The opaque dossier.** Early ChatGPT "reference chat history" was invisible by default. It leaked context into unrelated tasks (Half Moon Bay), and people experienced expectancy violations (CHI 2026). The failure was *opacity plus no scoping*, not memory as such.
2. **"It fits in 1M tokens, so preload everything."** Context rot is worst under exactly the conditions a personal corpus creates: semantically similar distractors and coherent prose (Chroma, NoLiMa). On over-personalization benchmarks, memory-free agents beat memory-augmented ones (OP-Bench).
3. **Treating AI inferences as facts.** About 40% of inferred user attributes are fabricated (MirageBench). Once written, they accumulate and are rarely revised. Self-reported confidence is *inversely* related to fabrication, so "only store high-confidence inferences" does not work as a filter.
4. **Memory as identity.** Injecting "the user believes X" into every context raises agreement sycophancy (+45% for one model; Jain et al.). This hurts most in the use case where the person needs the AI most: thinking critically about their own beliefs.
5. **Untrusted content with a write path into memory.** SpAIware and MINJA show that memory makes injection persistent. Any "remember this" that could come from a web page, document or tool output is an attack surface.
6. **Two writable representations kept in sync.** This is my reasoning from software engineering, not a measured result in this domain. Docs drift from code; two-way sync tools between note apps produce conflicts. If the human view and the AI view can both be edited independently, they will diverge, and nobody will know which one is true.
7. **A file convention with no committed consumer.** llms.txt: 97% of files never requested. Building elaborate AI-facing artifacts that no client actually reads is wasted work.
8. **Demanding manual organization.** Careful filing doesn't improve re-finding (Whittaker 2011). Personal-knowledge communities know the "collector's fallacy": hoarding notes feels like learning but isn't (from memory). A system that requires tagging, filing and linking up front will be abandoned or kept as a graveyard.
9. **Unbounded accumulation.** ChatGPT's "memory full" errors forced OpenAI into automatic prioritization and forgetting. Without consolidation pressure (a hard cap, as in Claude Code's 200-line index), memory turns back into fragments.
10. **Evaluating only recall.** Benchmarks that test "can it remember X" miss *appropriateness*: should it have used X here? (OP-Bench's critique.) An evaluation that only scores recall will reward over-personalization.
11. **Fully AI-authored understanding.** If the person only reads AI syntheses, ownership and retention suffer (Kosmyna et al.; generation effect). The system then succeeds on its own metrics while failing the user's actual goal.

---

## Implications for this project

Each implication is meant to be testable. "Hypothesis" marks the parts I expect the prototype to confirm or refute.

1. **One canonical, writable, human-legible store; everything else is a derived projection.**
   - The canonical layer is plain markdown files with YAML frontmatter and stable IDs, plus an append-only change log that records history.
   - Derived views are regenerated from it and never edited directly: AI context packs, the index, human dashboards, exports.
   - An edit made on any surface (a chat correction, a review-queue click) becomes a change event against the canonical layer.
   - A database or vector index may exist, but only as a rebuildable projection.
   - *Falsifiable:* if, during the prototype, we keep needing information that exists only in a projection, or keep editing projections by hand, the single-canonical assumption is wrong and should be revisited.

2. **Every entry has a `kind` from a small closed set, and the kind fixes how the AI should use it:**
   - `instruction`: always applies in scope; *only the person can create it*;
   - `preference`: the default unless overridden;
   - `fact` (about the world or the person): dated;
   - `belief`: held with stated confidence; open to challenge;
   - `decision`: with rationale and date; can be superseded;
   - `goal`;
   - `open-question`;
   - `event/history`.

   The context-pack renderer groups by kind and states each kind's semantics in one line. *Test:* a small probe set checks whether the model follows instructions while treating beliefs as contestable.

3. **Authorship and endorsement status are first-class:** `human-written | ai-proposed | human-confirmed | imported | external-source`.
   - `ai-proposed` claims *about the person* never enter the always-loaded core until they are confirmed.
   - *Hypothesis (from MirageBench):* in a hand-audited sample of 100 AI-proposed profile claims from my own chat logs, 25-50% will be unsupported or overstated. If the rate turns out to be under 10%, the confirmation gate can be relaxed.

4. **Time is explicit on every claim:** `observed_at`, `valid_from` / `valid_to`, `last_confirmed`, `superseded_by`.
   - Projections render age in plain words ("as of 2026-03, 7 months ago, not reconfirmed").
   - Superseded claims are kept for history but excluded from AI packs by default.
   - *Test:* a LongMemEval-style set of knowledge-update and temporal questions over my own data. The target is that superseded facts are never presented as current.

5. **Three tiers of AI context:**
   - **(a) Core pack**, roughly 1.5-3k tokens: in-scope instructions, top preferences, active goals and current projects. Deterministically ordered so it can be prompt-cached.
   - **(b) Index**: one line per hub or topic, with ID and a "relevant when..." description; roughly 5-10k tokens at most.
   - **(c) Just-in-time tools**: grep/read-by-ID over the files, plus semantic search.
   - *Hypothesis:* on a personal question set, core + index + JIT matches or beats full preload in correctness and clearly beats it on over-personalization, while using under 10% of the tokens.

6. **Build the evaluation harness before the fancy representation.** Run four arms on the same corpus and questions:
   - no memory;
   - full preload into a long-context model;
   - vector top-k;
   - agentic file search plus semantic tool.

   Metrics:
   - correctness;
   - knowledge-update and temporal correctness;
   - abstention when the answer is unknown;
   - irrelevant-memory use (OP-Bench style);
   - change in agreement sycophancy on contested prompts.

   Keep the full-preload arm cheap to rerun, because frontier long-context performance is moving fast (MRCR jumped from 18.5% to 76% in one model generation).

7. **Package beliefs to resist sycophancy.**
   - Beliefs go into AI context as "positions the person currently holds, with confidence, the strongest known counterargument, and what would change their mind," never as identity statements.
   - Provide a **critique-mode pack** that leaves out belief and profile entries and includes open contradictions instead.
   - *Test:* agreement rate on about 30 contested prompts, with belief context vs without. The target is that belief context does not raise unwarranted agreement.

8. **A relevance gate with a visible usage log.**
   - Before memories reach the answer, a cheap pass picks the ones that apply and says why (Self-ReCheck-like).
   - Every response that used memory records *which IDs* were used, so the person can see "this answer used memories X, Y" and correct them.
   - The usage log doubles as a training signal for salience.

9. **Lock down the write path.**
   - Content from outside sources (web, documents, imported chats, AI outputs) is stored as *quoted source material with provenance*. It can never have kind `instruction`.
   - Writes of `instruction` or `preference` require the person.
   - Context packs wrap memory in clearly labeled data delimiters.
   - *Test:* a red-team corpus of imported documents containing "remember that the user wants..." strings. Pass means zero of them become instructions or preferences without human approval.

10. **Human surfaces are a different projection, not a prettier dump.**
    - **"What the system thinks about me"**: prose by section, with claim-level actions (confirm / correct / forget / narrow scope / change salience).
    - **A weekly change feed**: what changed, why, from which source.
    - **A small-batch review queue** for AI-proposed changes. It must be fast enough to clear in under 5 minutes a day; if it can't be, the proposal rate is too high.
    - **Resurfacing of old beliefs and decisions** for re-evaluation.
    - For important beliefs, the person writes or edits the synthesis in their own words. The AI drafts; the person signs.

11. **Scope by default.**
    - Memories carry a scope (`global | domain:<x> | project:<y>`), and packs are built per scope.
    - Global is opt-in, not the default.
    - This one mechanism prevents most Half-Moon-Bay-style leakage.

12. **Interop is cheap, so build it last but plan for it.**
    - Exports:
      - a markdown bundle;
      - a generated paste-able summary for Claude/ChatGPT memory import;
      - a generated `AGENTS.md`-compatible snippet for coding agents.
    - Later, an MCP server: a *resource* for the core pack and *tools* for search, get-by-ID and propose-update.
    - Do not invest in llms.txt.

---

## Tensions and open questions

1. **Prose vs fields.** People read and reflect in prose; the AI needs typed, dated, sourced units. Can a "claim block" (one or two sentences plus frontmatter) serve both? Or does breaking knowledge into atoms destroy the line of reasoning people value and models also use? Possible test: compare model answers and human comprehension on atomized vs essay-form versions of the same topic.
2. **Granularity.** Atomic claims make updating and provenance easy. Essays carry reasoning. Probably both, with essays citing claim IDs, but every synthesis then becomes another projection that can go stale.
3. **Who writes the synthesis?** AI drafting gives coherence and saves effort. Human writing gives understanding and ownership (finding 11). Where is the line? Maybe "AI drafts; the person must restate in their own words before a belief is `human-confirmed`." That costs friction. Will the person actually do it?
4. **Should the AI see beliefs by default at all?** Leaving them out reduces sycophancy but loses useful personalization ("knows I already rejected approach X"). Perhaps beliefs load per task type. That needs the system to classify the task.
5. **Client capability shapes the representation.** A tool-using client (Claude Code, Codex, MCP-capable chat) can do just-in-time retrieval. A paste-only or memory-import client needs a self-contained compact pack. Two pack formats may be unavoidable. Integration is not fully separable from representation.
6. **Grep vs semantic search on *personal* text.** Personal notes are full of private shorthand and shifting vocabulary, which favors embeddings. But they are also small, which favors grep. We have no measurement yet. Test both arms.
7. **History vs freshness.** The person values seeing how their understanding evolved. The AI should almost never apply a superseded state. How should the AI see history when it is *asked* ("how has my view on X changed?") without stale states leaking into other answers?
8. **Sensitive inference.** Should the system *store* inferences about health, politics or relationships at all, or only facts the person stated explicitly? Users accept inferences when they can see them, but not when third parties could get them (Monteiro et al.). What is the default for exports and MCP access?
9. **Evaluating with one person.** Ground truth comes from one person, who is also the designer. How do we avoid evaluating against our own design assumptions? Perhaps by writing the question set *before* building the representation, and by including questions where memory should *not* be used.
10. **Will long context make retrieval moot?** If within 12-18 months full preload matches the retrieval arms on correctness *and* appropriateness at acceptable cost, the AI-side projection simplifies to "the canonical store, filtered by scope and time." The design should keep that option cheap. The human-side needs (navigation, review, ownership) do not go away either way.

---

## Sources

**Context engineering and long context**
- Chroma Research, *Context Rot: How Increasing Input Tokens Impacts LLM Performance* (July 2025). https://www.trychroma.com/research/context-rot
- Modarressi et al., *NoLiMa: Long-Context Evaluation Beyond Literal Matching* (ICML 2025). https://arxiv.org/abs/2502.05167
- Liu et al., *Lost in the Middle: How Language Models Use Long Contexts* (TACL 2024). https://arxiv.org/abs/2307.03172
- Li et al., *LaRA: Benchmarking Retrieval-Augmented Generation and Long-Context LLMs – No Silver Bullet for LC or RAG Routing* (ICML 2025). https://arxiv.org/abs/2502.09977
- Anthropic, *Introducing Claude Opus 4.6* (MRCR v2 8-needle 1M: 76% vs Sonnet 4.5 18.5%). https://www.anthropic.com/news/claude-opus-4-6
- Anthropic, *Effective context engineering for AI agents* (Sep 29, 2025). https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Anthropic, context management announcement (context editing + memory tool, 2025). https://www.anthropic.com/news/context-management
- Manus (Yichao "Peak" Ji), *Context Engineering for AI Agents: Lessons from Building Manus* (July 2025). https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus

**Memory benchmarks and retrieval**
- Wu et al., *LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory* (ICLR 2025). https://arxiv.org/abs/2410.10813
- Letta, *Benchmarking AI Agent Memory: Is a Filesystem All You Need?* (Aug 12, 2025). https://www.letta.com/blog/benchmarking-ai-agent-memory
- Cursor blog, semantic search for the Cursor agent (Nov 6, 2025). https://cursor.com/blog/semsearch
- Secondary account of Claude Code dropping vector RAG for agentic search (Boris Cherny, Latent Space podcast). https://smartscope.blog/en/ai-development/practices/rag-debate-agentic-search-code-exploration/

**Product memory systems and interop**
- Claude Code docs, *How Claude remembers your project* (CLAUDE.md, AGENTS.md, auto memory). https://code.claude.com/docs/en/memory
- OpenAI, Codex *Memories* docs (redirects to learn.chatgpt.com). https://developers.openai.com/codex/memories
- Anthropic, Claude memory announcement. https://www.anthropic.com/news/memory
- Anthropic Help Center, *How does Claude's memory work?* https://support.claude.com/en/articles/11817273
- PCWorld, *Claude can now import chat histories from ChatGPT and other AIs* (Mar 3, 2026). https://www.pcworld.com/article/3076376/claude-can-now-import-chat-histories-from-chatgpt-and-other-ais.html
- Simon Willison, *Comparing Claude and ChatGPT memory* (Sep 12, 2025; summarizes Shlok Khemani). https://simonwillison.net/2025/Sep/12/claude-memory/
- TechRadar, *ChatGPT is smarter now that it's learned to forget* (automatic memory management). https://www.techradar.com/ai-platforms-assistants/chatgpt/chatgpt-is-smarter-now-that-its-learned-to-forget-a-huge-memory-upgrade-is-coming
- Linux Foundation, *Formation of the Agentic AI Foundation* (Dec 9, 2025; MCP, goose, AGENTS.md). https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation
- Agent Skills specification. https://agentskills.io ; Codex skills docs: https://developers.openai.com/codex/skills
- Model Context Protocol. https://modelcontextprotocol.io ; AGENTS.md: https://agents.md
- Ahrefs, *We Analyzed 137K Sites: 97% of llms.txt Files Never Get Read* (2026). https://ahrefs.com/blog/llmstxt-study/

**Risks: sycophancy, over-personalization, inference, injection**
- Jain, Park, Viana, Wilson, Calacci, *Interaction Context Often Increases Sycophancy in LLMs* (2025). https://arxiv.org/abs/2509.12517
- OpenAI, *Expanding on what we missed with sycophancy* (May 2025). https://openai.com/index/expanding-on-sycophancy/
- Hu et al., *OP-Bench: Benchmarking Over-Personalization for Memory-Augmented Personalized Conversational Agents* (Jan 2026). https://arxiv.org/abs/2601.13722
- Sun, Zhang, Sheng, *The Personalization Mirage: How LLMs Fabricate User Profiles, and Why Self-Monitoring Misleads* (2026). https://arxiv.org/abs/2608.04570
- Entezami & Endres, *Biased or Personalized? The Impact of Personal Information on AI-driven Development* (2026). https://arxiv.org/abs/2607.07480
- Simon Willison, *I really don't like ChatGPT's new memory dossier* (May 21, 2025). https://simonwillison.net/2025/May/21/chatgpt-new-memory/
- The Hacker News on SpAIware (Rehberger, Sep 2024). https://thehackernews.com/2024/09/chatgpt-macos-flaw-couldve-enabled-long.html
- *A Practical Memory Injection Attack against LLM Agents* (MINJA, 2025). https://arxiv.org/abs/2503.03704
- *Memory Poisoning Attack and Defense on Memory Based LLM-Agents* (Jan 2026). https://arxiv.org/abs/2601.05504
- Xie et al., *Adaptive Chameleon or Stubborn Sloth: Revealing the Behavior of LLMs in Knowledge Conflicts* (ICLR 2024). https://arxiv.org/abs/2305.13300

**Human side: perception, navigation, cognition**
- Chen, Molina, Liao, Cho, *AI Never Forgets: Exploring Users' Perceptions of AI Memory and ChatGPT's Memory Feature* (CHI 2026, DOI 10.1145/3772318.3791635). https://grady.uga.edu/research/ai-never-forgets-exploring-users-perceptions-of-ai-memory-and-chatgpts-memory-feature/
- Monteiro et al., *When Are LLM Inferences Acceptable? User Reactions and Control Preferences for Inferred Personal Information* (2026). https://arxiv.org/abs/2605.10013
- Kosmyna et al., *Your Brain on ChatGPT: Accumulation of Cognitive Debt when Using an AI Assistant for Essay Writing Task* (MIT Media Lab preprint, 2025). https://arxiv.org/abs/2506.08872
- Teevan, Alvarado, Ackerman, Karger, *The Perfect Search Engine Is Not Enough: A Study of Orienteering Behavior in Directed Search* (CHI 2004). (from memory; no URL)
- Bergman et al., *Improved search engines and navigation preference in personal information management* (ACM TOIS 2008). (from memory; no URL)
- Whittaker et al., *Am I wasting my time organizing email? A study of email refinding* (CHI 2011). (from memory; no URL)
- Slamecka & Graf, *The generation effect: Delineation of a phenomenon* (1978); Roediger & Karpicke, *Test-enhanced learning* (2006). (from memory)
- Clark & Chalmers, *The Extended Mind* (Analysis, 1998). (from memory)
