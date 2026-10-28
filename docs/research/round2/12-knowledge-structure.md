# Structural memory: representing what was learned (from the user and from AI) and what to learn

Track 12, round 2. Status: research note, 2026-10-07. It feeds design and decides nothing. [`docs/GOAL.md`](../../GOAL.md) is authoritative. This note takes its WHAT as fixed and argues only about HOW.

**How this was verified.** Claims were checked with web search and fetch on 2026-10-07. Primary sources were read where they could be reached: arXiv full text for Zep, GraphRAG, RAPTOR and Clio; the Karpathy gist itself; the Graphiti README and docs. Where only abstracts or secondary write-ups were reachable, the note says so. Anything not re-verified is marked "(unverified)". Product facts carry the date they were observed. Round-1 notes are cited as [01], [02], [04], [06], [07] and [08]. Their numbers are quoted from those notes, not re-checked here.

---

## Questions this track answers (tied to GOAL.md)

| # | Question | GOAL.md anchor |
|---|---|---|
| Q1 | What is the unit and schema of the shared core, so that what the user said **and** what the AI said or taught are both first-class, attributed, linked to their conversation spans, and able to evolve without losing history? | §3.1, §4.2 |
| Q2 | How should the correctness risk of AI-taught content be represented, and checked automatically, without making the user review it? | §3.1, §4.2, §4.3 |
| Q3 | What structure represents **what has been learned**, and what can a system honestly claim about learning from conversations? | §3.2, §6 |
| Q4 | What structure represents **what to learn** (goals, gaps, prerequisites, open questions, next steps), and how can it be inferred automatically? | §3.2, §2 ("Both") |
| Q5 | How does the structure reorganize itself (merge and split concepts, re-parent topics) with history and without the user maintaining it? | §3.2, §3.4, §4.3 |
| Q6 | Which human views actually help people navigate a large personal knowledge structure? | §3.2, §6 |
| Q7 | What does this structure give the AI-facing architecture, both in-session and cross-session? | §3.3, §4.4, §4.5 |
| Q8 | Which organization algorithms can be checked, so that a maintainer that loses focus cannot silently corrupt the structure? | §3.4, §4.7 |

Out of scope here, because other tracks cover them: storage engines, capture mechanics per surface, prompt-pack formats, and the evaluation harness.

---

## Key findings

**F1. Personal knowledge graph research converged on statements with rich metadata, not entity graphs. It never modelled an AI as a speaker.**
- *Mechanism.* Balog and Kenter (ICTIR 2019) define a PKG as structured knowledge about entities, and the relations between them, that are "of personal, rather than general, importance".
- *Survey.* Skjæveland, Balog et al.'s ecosystem survey (*AI Open* 5, 2024) says a PKG must hold objective facts, personal beliefs and "beliefs attributed to others". Each statement needs context: where, when and how it arose, who holds it true, and to what degree. The authors expect this metadata to *exceed* the actual data in size. For statement-level representation they name reification, named graphs and RDF-star.
- *Practice.* PKG API (Bernard et al., WWW '24 Companion) lets users manage the graph through **natural-language statements**, mapped to an RDF vocabulary with provenance and access-rights properties.
- *Implication.* Make the statement the core unit, not the entity triple. No PKG work found treats "an assistant said this in a chat" as a speaker class. Northstar has to add that itself.

**F2. Wikidata's statement model already separates the value, its scope, its grounds and its standing.**
- A Wikibase statement is a claim (property plus value), qualifiers (scope, such as time), references and a rank: preferred, normal or deprecated.
- The query service returns preferred values if any exist, otherwise normal ones, and never deprecated ones.
- Property P2241 records the *reason for* a deprecated rank.
- Nanopublications and discourse graphs make the same split between assertion, provenance and evidence [04].
- *Implication.* A "best-rank projection" gives a clean current view over a store that keeps everything. Qualifiers absorb most apparent contradictions as scope differences (version, context, date) [04].

**F3. Graphiti/Zep shows the temporal-graph pattern working, and also shows entity-centric extraction losing what the assistant said.**
- *Structure.* The Zep paper (arXiv 2501.13956, Jan 2025) defines three tiers:
  - an **episode** subgraph: raw messages, "non-lossy";
  - a **semantic entity** subgraph: entities, plus fact edges carrying four timestamps;
  - a **community** subgraph.
- *Updates.* Contradicted edges are invalidated, not deleted. The rule is that new information wins: the old edge's `t_invalid` is set to the new edge's `t_valid`.
- *Communities.* These use label propagation so they can be extended incrementally. The authors concede they "gradually diverge" from a full recomputation, so "periodic community refreshes remain necessary".
- *Results.* On LongMemEval with gpt-4o, Zep beat full context, 71.2% against 60.2%, with about 90% lower latency. But accuracy on the **single-session-assistant** category, questions about what the *assistant* said, **declined** (the paper reports −17.7% for gpt-4o and −9.06% for gpt-4o-mini). An extraction pipeline built around entities and user facts drops AI-said content. That is direct evidence for GOAL §4.2's concern.
- *Product facts (README and docs, observed 2026-10-07):*
  - entity and edge types are Pydantic models, constrained by an `edge_type_map`;
  - "existing episodes are not reclassified when you add types", so applying new types means re-ingesting into a new graph;
  - "entities evolve over time with updated summaries";
  - supported back ends are Neo4j, FalkorDB and Neptune, with Kuzu deprecated.

**F4. Hierarchical summary structures (GraphRAG, RAPTOR, MemTree) build upper levels by summarizing summaries.**
- *GraphRAG* (Edge et al., arXiv 2404.16130):
  - Leiden builds a hierarchy of mutually exclusive partitions.
  - Leaf communities are summarized from element summaries, which are themselves LLM summaries.
  - At higher levels, when the input exceeds the context window, GraphRAG will "iteratively substitute sub-community summaries … for their associated element summaries".
  - Root-level summaries used about 2.3–2.6% of the tokens needed to summarize the source text.
  - Its incremental `update` command reruns community detection over the whole graph and regenerates reports (docs mirror, observed 2026-10-07).
- *LazyGraphRAG* (Microsoft Research, Nov 2024, updated Jun 2025) defers all summarization to query time. Its indexing costs 0.1% of full GraphRAG.
- *RAPTOR* (ICLR 2024):
  - Recursively clusters roughly 100-token chunks: UMAP, then GMM soft clustering with BIC choosing the number of clusters. Each cluster is summarized with gpt-3.5-turbo.
  - Retrieval over the "collapsed tree", which flattens all levels into one pool, worked best.
  - A manual check found hallucinations in 4% of sampled summary nodes. They were minor and did not propagate upward.
  - The paper does not describe incremental updates.
- *MemTree* (ICLR 2025) inserts new conversation content top-down and updates parent nodes as it goes.
- *Implication.* These hierarchies are excellent as navigation and retrieval indexes. Their upper-level text is exactly the "summary of summaries" that round 1 ruled out [06]. Upper levels must either be regenerated from leaf items, or be treated as uncited navigation labels.

**F5. Graph retrieval helps associative recall only if passages stay in the loop.**
- HippoRAG 2 (ICML 2025) runs Personalized PageRank over an OpenIE triple graph *with passage nodes integrated*.
  - The authors note that earlier graph-augmented RAG "drops considerably below standard RAG" on basic factual tasks.
  - HippoRAG 2 reports about +7% on associative tasks over the strongest embedding baseline, while staying strong on factual ones.
- LightRAG (EMNLP 2025 Findings) pairs entity-level and theme-level retrieval with an incremental insert algorithm. The abstract and search results describe no deletion path (unverified in the code).
- *Implication.* The concept graph should be an index that points at anchored passages and items. It should not replace them.

**F6. "Memory evolution" in agent memories means rewriting old notes in place.**
- A-MEM (NeurIPS 2025) gives each memory a note with keywords, tags and a context description. It links new notes to similar old ones, and lets new memories "trigger updates to the contextual representations and attributes of existing" notes.
- Graphiti rewrites entity summaries in the same way (F3).
- Cognee's `add` / `cognify` / `memify` pipeline enriches its graph after construction. This is secondhand: only its README and vendor pages were reachable.
- *Implication.* Linking at write time is the Luhmann lesson [02], and it is worth keeping. Rewriting earlier notes' text is the incremental-rewrite drift that round 1 warns about [06]. Keep the link proposals, and version every attribute change as an event.

**F7. Karpathy's llm-wiki is a pattern for human-readable pages, not an epistemic store. Verified against the gist itself.**
- The gist was created 4 April 2026. It defines three layers:
  - immutable raw sources;
  - an LLM-maintained Markdown wiki that the LLM "owns … entirely";
  - a schema file (CLAUDE.md or AGENTS.md).
- It defines three operations:
  - **ingest:** one source can touch 10–15 pages;
  - **query:** answers can be filed back into the wiki as pages;
  - **lint:** checks for contradictions, stale claims, orphans, missing concept pages and data gaps.
- Two files hold the structure. `index.md` is a content catalogue that the LLM reads first. `log.md` is an append-only, greppable log of ingests, queries and lints.
- Karpathy says the index approach suits "moderate scale (~100 sources, hundreds of pages)". Contradictions are handled by having the LLM "revise or challenge" existing pages.
- There is no attribution model, no rank or deprecation, and no rule for which source wins.
- *Implication.* Concept pages plus an index plus a log are the right shape for the *human* view, and the log is a ledger in miniature. The pages have to be compiled projections with citations down to items and spans. They cannot be the canonical store.

**F8. AI-taught content is wrong often enough that storing it unflagged would manufacture false authority.**
- *Vendor figures.* OpenAI's GPT-5 system card (arXiv 2601.03267) reports claim-level hallucination rates 26% lower than GPT-4o (gpt-5-main) and 65% lower than o3 (gpt-5-thinking), graded by an LLM with web access. Its agreement with humans was about 75%.
  - Secondary readings of the same card give raw browsing-enabled claim error rates of 9.6% (gpt-5-main) and 4.5% (gpt-5-thinking) (unverified against the tables).
  - Without browsing, SimpleQA hallucination rates were about 0.40–0.52 (unverified).
- *Teaching content.* In tutoring, ChatGPT-generated algebra and statistics help failed quality checks on 32% of problems (Pardos and Bhandari, *PLOS ONE*, 2024). Self-consistency cut that to about 0% for algebra but left 13% for statistics.
- *Effect on people.* Users are poor detectors. In a pre-registered study (Kim et al., CHI 2025, N=308):
  - explanations increased reliance on **incorrect** answers as well as correct ones;
  - **sources reduced over-reliance** on incorrect answers.
- *Effect on memory systems.* Production memory systems absorbed roughly 43–55% of assistant-introduced distractors as user memory [08].
- *Implication.* "AI-said" must carry a verification status. "The user accepted it" must never be read as "it is correct".

**F9. Automatic verification is partial, has its own error rate, and misses errors that are consistent.**
- *SAFE* (Wei et al., 2024) splits long-form answers into atomic facts and checks each one with Google Search. It agreed with crowd annotators on 72% of about 16k facts. On 100 disagreements it was right 76% of the time, at more than 20× lower cost than human annotation.
- *Semantic entropy* (Farquhar et al., *Nature* 630, 2024) detects confabulations by sampling several answers and clustering them by meaning. It costs several times more compute and, by construction, cannot catch errors a model makes consistently.
- *Implication.* Verification is a probabilistic, recorded judgement made by a named verifier. It needs a "not checkable" outcome for opinions, design advice and value judgements, which make up much of what AIs teach. It also needs independence rules: the same model family checking itself is weak evidence.

**F10. What a person has *learned* cannot be read off their conversations with any precision.**
- *Inferring knowledge from logs.* LLMs estimating people's domain knowledge from 27,188 Slack messages had a best mean absolute error of 21 points on a 0–100 scale (Watanabe and Ishimaru, arXiv 2605.22971, May 2026). More text did not reliably help.
- *LLMs as learner models.* An LLM used as a learner model gave "wrong-direction" mastery updates. Deep knowledge tracing (AUC 0.83) beat it in every setting (Hooshyar et al., arXiv 2512.23036, Dec 2025).
- *Tutoring studies.* In 44 tutoring sessions, the quality of students' *answers* was the most reliable sign of understanding. Their questions were only a marginal indicator, and their replies to "Do you understand?" were "very misleading" (Person et al., 1994).
- *A route that works.* LLMKT (Scarlatos, Baker and Lan, LAK 2025) used an LLM to label the skills and correctness in each turn of a tutoring dialogue. Classical knowledge tracing on top of those labels outperformed prior methods.
- *Implication.* Mastery needs performance evidence. A system that only watches chats can honestly report **engagement and exposure**: what was explained to the user, what they asked, used, restated or disputed. It cannot honestly report "learned".

**F11. "What to learn next" has a clean formal core: the outer fringe of a prerequisite structure.**
- *Knowledge space theory* (Doignon and Falmagne, 1985) represents a learner's state as the set of items they have mastered. The **outer fringe** is the set of items whose prerequisites are all in the state, which ALEKS reports as "ready to learn". The **inner fringe** is the set of items most likely learned recently. The Fringe Theorem says the two fringes determine the state.
- *Math Academy* runs two graphs:
  - a prerequisite DAG;
  - an **encompassing** graph with weights for how much a harder topic implicitly practises a simpler one. Its spaced-repetition model (FIRe) credits those implicit repetitions.
  - Both graphs are hand-built. The developer reports about 8 hours a day for a month, covering roughly 1,500 topics × 5 prerequisites each (developer-reported).
- *Automatic extraction is mediocre.* LLM prerequisite extraction from course material reached F1 70.2 zero-shot and 76.2 few-shot (Capture-Calibrate-Coach, arXiv 2605.25419, 2026). Expert review of another pipeline found 7% of extracted prerequisites wrong, mostly weak relatedness or **reversed direction** (Scientific Contribution Graph, arXiv 2605.15011).
- *Implication.* The fringe computation is cheap and deterministic. The prerequisite edges it runs on are noisy, especially in personal, uncurated domains.

**F12. The user's own questions are the best free signal of gaps. Contradictions generate new questions.**
- Students partly self-regulate by spotting knowledge deficits and asking questions to repair them (Graesser and Person, *AERJ*, 1994).
- The PREG model holds that questions arise from cognitive disequilibrium: contradictions, obstacles and anomalies (Otero and Graesser, *Cognition and Instruction* 19(2), 2001; not re-read).
- *Implication.* A question the user asked that never got a satisfying answer is a high-precision "what to learn" item. A contradiction between sources, or between AIs, should spawn an open question automatically.

**F13. Open learner models are the established answer to "show the learner a model of their knowledge, and let them contest it".**
- Bull and Kay's SMILI framework puts open learner models on a scale from *inspectable* to *editable* to *persuadable* to *negotiated*.
- A negotiated model keeps **separate belief bases for the learner and the system**. The learner edits their own and inspects the system's. This is argued to improve both model accuracy and metacognition (Bull, *RPTEL* 2016).
- A systematic review found that 81% of OLM papers were interactive and 76% reported evaluations (Bodily, Kay et al., 2018).
- No pooled effect size for OLMs on learning was found.
- *Implication.* The human structure should be an open learner model: the system's claims about the user, inspectable and contestable, with the user's own corrections as a separate, optional layer.

**F14. Concept maps help learning, but less when the learner only studies them. AI-made maps look acceptable to learners.**
- A meta-analysis of 142 effect sizes (n = 11,814) found g = 0.58 overall (Schroeder, Nesbit, Anguiano and Adesope, *Educational Psychology Review*, 2018). *Constructing* maps gave g = 0.72; *studying* them gave g = 0.43.
- Secondary students rated ChatGPT-generated concept maps comparable to teacher-made ones (Schicchi et al., 2025; perception data only).
- *Implication.* Under GOAL §4.3 the AI builds the map, so the user is in the "studying" condition. That is still a positive effect, but the smaller one (see Risk R6).

**F15. Global graph views lack supporting evidence. Trees, local neighbourhoods, source-linked nodes and time cues have it.**
- *Graph views.*
  - No controlled study was found showing that whole-graph views help PKM users.
  - In a 2025 qualitative study of researchers using Obsidian, retrieval relied on search, tags and in-note links, not the graph [02].
  - Practitioner reports converge: a filtered or local graph is useful, while a global graph becomes a "hairball" around 10k notes (practitioner blogs and forum threads).
  - Argument-mapping studies found no consistent advantage of maps over hierarchical outlines [04].
- *Overviews in hypertext.* Graphical overviews reduce disorientation modestly, more so for people with prior knowledge (Müller-Kalthoff and Möller, 2003, as summarized). Strong navigation support removed the usual penalty of network structures for novices (Jáñez et al., 2021, as summarized).
- *Mind maps in a product.* NotebookLM's Mind Map (launched March 2025) is a collapsible tree generated from sources. Each node records the passages behind it, and clicking a node asks the assistant about it. A May 2026 update added prompt steering and renaming (per NotebookLM's X account, secondary).
- *Time as a cue.* In Stuff I've Seen (Dumais et al., SIGIR 2003; more than 230 users), "time and people" were major retrieval cues. Later slides report that users sorted by date far more than by anything else.
- *Implication.* The defaults should be trees, outlines and timelines. A local graph can be an option. A global force-directed graph should not be a default view.

**F16. Automatic topic hierarchies over conversations work. Their stability over time is a separate problem.**
- *Clio* (Anthropic, arXiv 2412.13678) builds a hierarchy over conversations in four steps:
  1. extract a facet, such as topic;
  2. embed it and cluster with k-means;
  3. have a model write cluster titles;
  4. recursively build higher levels by combining k-means with prompting.

  On a synthetic set of 19,476 transcripts it reconstructed the ground-truth categories with 94% accuracy, against 5% for random guessing. It warns that the hierarchy "might oversimplify complex relationships".
- *TnT-LLM* (Microsoft, KDD 2024) generates and iteratively refines a label taxonomy from sampled Bing Copilot conversations. The LLM's labels then train a cheap classifier.
- *Stability.* Neither method addresses stability across re-runs. *Evolutionary clustering* (Chakrabarti, Kumar and Tomkins, KDD 2006) trades a "snapshot quality" term against a "history cost" term, which penalizes departure from the previous clustering. Graphiti's communities drift without such a term (F3).
- *Why it matters.* People navigate by recognition and location memory (Bergman and Whittaker [02]). Churn in labels and placement destroys exactly that.

**F17. PKM tool lessons: emergent schema works, and spatial structure is something the user builds.**
- *Tana* (docs, observed 2026-10-07): a supertag turns a node into a typed object. When the same ad-hoc field appears on a second node with the same tag, it becomes an optional template field automatically. With AI enabled, fields are suggested for new supertags. This is incremental formalization [04] in a shipping product.
- *Heptabase*'s core is cards on whiteboards that the user lays out. AI actions on whiteboard cards shipped in December 2025 (changelog). Reviews call AI-suggested connections "cluttered" (secondary).
- *Discourse Graphs* (Joel Chan et al.) brings Question, Claim, Evidence and Source node types to Obsidian; the plugin is out of beta. Users report the manual typing as friction.
- *Implication.* The AI should do the typing (QCE-style) and let kinds emerge. Spatial canvases are a poor fit for an AI-maintained structure, because the layout is the user's own meaning.

---

## What this means for the Northstar architecture

1. **[core] Make the statement-level item the unit, and keep attribution as three independent axes rather than one label** (F1, F2, F8). The labels requested in the brief are combinations of these axes, not values of one field.
   - **Speaker:** user-typed, user-pasted, `assistant(model, surface)`, external source, or system-inferred.
   - **User stance:** asserted, accepted, questioned, disputed, rejected, or none.
   - **Verification:** unchecked, not-checkable, supported, contradicted, mixed, or AI-cited-unchecked, each with its evidence references.

   The brief's labels map onto these axes:

   | Brief's label | Speaker | Stance | Verification |
   |---|---|---|---|
   | AI-said, user accepted | assistant | accepted | any |
   | Verified by source | any | any | supported, with references |

   One enum would conflate stance with verification, which is exactly the error F8 warns about.
2. **[core] Store AI teaching as anchored passages, not only atomized claims** (F3, F5, round-1 T3). Most of what an AI teaches is explanation, procedure, example or comparison.
   - Store each as a *passage item* holding the verbatim span reference, a gist, and the concepts it `explains`.
   - Extract checkable claims from it as children, used for verification and conflict detection.
   - Never let the children replace the passage.

   This directly answers Zep's assistant-recall drop.
3. **[core] Anchor every item to an exact span.** A span is `{surface, conversation_id, message_id, branch_path, quote, prefix, suffix}`.
   - For ChatGPT, the branch path matters. An abandoned regeneration or edited-away branch is a rejection signal [08].
   - Assistant messages also record the model ID and whether browsing or tools were used, since the error rate differs by roughly 2–5× (F8).
4. **[core] Keep a small kind vocabulary with two tiers** (F17, round-1 T11).
   - Tier 1 has four structural roles:
     - **Concept:** a node with stable identity;
     - **Statement:** fact or claim, definition, insight, decision;
     - **Passage:** explanation, procedure, example, comparison;
     - **Agenda:** question, goal, next step.
   - Tier 2 kinds are tags, and new ones are admitted Tana-style: after recurring use, never up front.
5. **[maintainer] Make verification a separate, recorded, budgeted job** (F8, F9).
   - Route each AI-said statement by checkability. Checkable facts go to search-grounded verification by a model family *different* from the one that said them.
   - Version- or time-sensitive facts get a re-check date.
   - Opinions and advice are marked not-checkable and labelled as AI opinion.
   - Record the verifier model, its query and its evidence.
   - Never upgrade verification because the user accepted something, or because a second AI repeated it. Count lineages [04][06].
6. **[human structure] Report what the user engaged with, not what they "learned"** (F10, F13). Each concept carries a per-user **engagement state** derived from events:
   - encountered;
   - explained-to-user;
   - asked-about;
   - used or applied;
   - restated-by-user;
   - confused or disputed.

   Show this as the system's model, labelled as inferred: the negotiated-OLM split. "Learned" in the UI means "engaged with, with this evidence", never "mastered".
7. **[human structure] Represent the "what to learn" side explicitly** (F11, F12). It has four parts:
   - **Goals:** explicit user statements of intent. Inferred goals are kept apart as "possible interests" with a decay, because models over-infer 35–49% of user attributes [07].
   - **Open questions:** questions the user asked that were not resolved, plus questions spawned automatically from conflicts.
   - **A prerequisite layer:** LLM-proposed edges with confidence and a direction check.
   - **A frontier:** the outer fringe over the goal-relevant subgraph.
8. **[maintainer] Treat topic hierarchy, communities and concept pages as versioned projections with stable IDs** (F3, F4, F16).
   - Reorganization runs as evolutionary clustering with an explicit stability cost.
   - Matched clusters keep their IDs.
   - Every split, merge, move or rename is a typed event with before and after, so it can be inspected and undone.
9. **[maintainer] Compile pages only from leaves** (F4, F6, F7).
   - Concept pages are regenerated from current best-rank items and passages, never by editing the previous page text.
   - Every synthesized sentence cites item IDs.
   - A deterministic validator rejects uncited sentences.
   - A second-model entailment check is sampled on every rebuild. This is round 1's "never summarize summaries", made checkable.
10. **[maintainer] Enforce checkable invariants on every write.** This is what keeps the maintainer correct when one agent loses focus (GOAL §4.7). Examples:
    - an assistant-speaker item can never carry stance `asserted`;
    - deprecated items never enter a pack;
    - every concept-membership change is an event;
    - the alias graph is acyclic;
    - a reorganization preserves the multiset of item-to-concept links;
    - every page sentence has at least one citation.

    The invariants are deterministic code, not prompts.
11. **[AI in-session] Use the same item schema for what is "established in this chat"** (Q7).
    - Conclusions, definitions and decisions that either party establishes become session-scoped items with speaker and stance.
    - The session goal is an Agenda item.
    - A drift check compares new answers against established items and against the goal's concept neighbourhood.

    The schema makes in-session focus possible. The drift mechanism belongs to another track.
12. **[AI cross-session] Compile a pack from the structure.** It contains:
    - active goals and the frontier;
    - relevant concept cards with speaker and verification labels;
    - disputed AI claims, as "do not re-assert";
    - engagement state, so the assistant neither re-explains basics nor skips missing prerequisites.

    Unverified AI-said items are always labelled. Per round 1, inferred stances never enter the always-loaded core [07].
13. **[surface adapters] Capture the extra context that AI-said items need.** Web surfaces must capture:
    - the full text of assistant messages, including artifacts and code blocks;
    - the model name, which affects error rates (F8);
    - any citations the AI gave, as AI-cited references, not as verification;
    - branch and regeneration structure;
    - thumbs feedback, where the surface exposes it.

    Pastes inside user turns must be classified as third-party, or AI text gets misattributed to the user [08].

---

## Options and trade-offs the design must decide

### Candidate knowledge models

All three candidates share the round-1 substrate: immutable episodes and spans, an append-only event ledger, typed supersession, four timestamps, ranks with reasons, and excision [04][06]. The base records are:

```yaml
Episode: {id, surface: claude.ai|chatgpt|claude-code|..., conversation_id, branch_path, started_at, content_hash}
Message: {id, episode, role, speaker: user_typed|user_pasted|assistant|tool|system, model?, browsing?: bool, ts}
Span:    {id, message, quote, prefix, suffix, start, end}            # W3C TextQuoteSelector-style
Event:   {id(ULID), type, actor: user|model@version+prompt_hash, inputs[], payload, reason, recorded_at}
```

#### Model A: Attributed statement ledger with compiled concept pages

*Shape.* This is Wikidata or nanopublication statements, plus Karpathy-style pages as projections. The canonical layer is a set of statements. Navigation structure is derived from it.

```yaml
Item:         {id, role: concept|statement|passage|agenda, kind_tags[], text, gist?,
               qualifiers: {valid_time?, context?, version?, population?}, concept_refs[], rank, rank_reason?}
Attribution:  {id, item, speaker, speaker_id ("user" | "claude-opus-x@claude.ai" | uri), span,
               modality: asserts|explains|suggests|asks|denies, hedge_verbatim?, lineage_origin}
Stance:       {id, item, holder: user, attitude: asserted|accepted|questioned|disputed|rejected,
               evidence: explicit|behavioural(branch_abandoned|thumbs|reused|restated), span?, belief_time{from,to?}}
Verification: {id, item, checkability: checkable|time_sensitive|not_checkable, status: unchecked|supported|
               contradicted|mixed|ai_cited_unchecked, verifier: model@version, independent_of_speaker: bool,
               evidence_refs[], checked_at, recheck_after?}
Relation:     {id, from, to (item|relation), type: explains|example_of|defines|part_of|prerequisite_of|
               supports|rebuts|undercuts|refines|answers|compares|supersedes|same_as,
               confidence, created_by, status: proposed|applied|user_confirmed|user_rejected}
Page:         {concept, version, built_from: [item@version], model, prompt_hash, sentences: [{text, cites[]}]}
```

*Organization algorithms:*
1. **Segment** episodes at topic or goal shifts [01].
2. **Extract** in batch per episode. Each candidate carries speaker, stance, role, kind and span, using a stance-aware prompt [08].
3. **Canonicalize concepts.**
   - Retrieve candidates by lexical and embedding similarity.
   - An LLM judges whether two are equivalent.
   - The outcome is a `same_as` alias assertion, never a physical merge. When unsure, leave them split, because merge errors cost more than split errors [06].
4. **Route integration** with a congruence router [01]:
   - a high-fit item attaches to an existing concept;
   - a low-fit item becomes a new concept, flagged as novel;
   - a middling item goes to an *unplaced* pool, which is retried automatically with more context and never queued for a human.
5. **Propose relations**, including typed conflicts (rebut, undercut, scope, temporal) [04]. Auto-apply only unambiguous, dated supersessions.
6. **Verify** (implication 5).
7. **Cluster topics** over the concept relation graph, using Leiden with a fixed seed plus a stability cost (Model C details the reorganization).
8. **Compile pages** from leaves, with citations (implication 9).
9. **Lint:** orphans, dangling references, AI-only support, stale time-sensitive facts.

*Recommended human views:*
- concept pages, wiki-style, with attribution and verification chips on every claim;
- an index;
- a chronological "learned" feed;
- question pages.

*Strengths:*
- the highest-fidelity attribution;
- conflicts are first-class;
- it maps directly onto the round-1 requirements.

*Weaknesses:*
- the "what to learn" side is weak: prerequisites and the frontier are bolted on;
- the item volume is large;
- pages look like a wiki, not a map of learning progress.

#### Model B: Temporal concept graph (Graphiti-style, extended)

*Shape.* Concepts are nodes. Facts are time-bounded edges. Episodes keep provenance, and communities provide the hierarchy. It could be built on Graphiti's custom entity and edge types.

```yaml
ConceptNode:   {id, name, aliases[], kind: concept|entity|skill|tool|person, summary_view(compiled), created_at}
FactEdge:      {id, src, dst, predicate, fact_text, speaker, stance, verification,
                t_valid, t_invalid, t_created, t_expired, episodes[], supersedes?, supersession_type}
PassageNode:   {id, span, gist, explains: [concept]}          # added: Graphiti has no passage tier
CommunityNode: {id, level, members[], label, version, matched_from?}
```

*Organization algorithms:*
1. Extract entities and edges per episode with a typed `edge_type_map`.
2. Resolve entities by embedding plus full-text candidates, with an LLM deciding.
3. **Change edge invalidation.** Graphiti's "new wins" rule is replaced: only world-change supersessions auto-apply, and a change of stance becomes a stance event, not an invalidation.
4. Assign communities incrementally by label propagation. Periodically recompute with Leiden and match the result to the old communities to keep IDs stable.
5. For AI retrieval, use Personalized PageRank from query-linked concepts, with passages included, as in HippoRAG 2.

*Recommended human views:*
- a community tree;
- a concept page with a local neighbourhood graph of up to 2 hops, filtered by relation;
- a timeline of each concept's edges.

*Strengths:*
- off-the-shelf parts: Graphiti, its MCP server, and Neo4j or FalkorDB;
- strong associative retrieval;
- native bi-temporality.

*Weaknesses:*
- it is entity-centric, which loses explanations unless passages are added (F3);
- entity summaries are rewritten incrementally (F6);
- changing the schema requires re-ingesting (F3);
- it needs a graph-database dependency;
- edges between pairs of entities fit procedures, comparisons and open questions poorly.

#### Model C: Learning map (concept DAG + discourse layer + engagement overlay)

*Shape.* A SKOS-like concept scheme with prerequisite edges. Over it sit a Question / Claim / Evidence discourse layer and a per-user engagement overlay: an open learner model. This model is built for the "learned / to learn" structure.

```yaml
Concept:      {id, label, aliases[], definition_item?, broader[] (polyhierarchy), related[]}
Prerequisite: {from, to, weight, encompassing_weight?, source: llm|curated|user, confidence, direction_checked: bool}
Question:     {id, text, raised_by: user|ai|conflict, status: open|answered|dormant, answers: [statement],
               concept_refs[], span}
Goal:         {id, text, explicit: bool, status: active|paused|done|expired, target_concepts[], evidence_spans[]}
Statement / Passage / Attribution / Stance / Verification: as in Model A   # the QCE "claim/evidence" layer
Engagement:   {concept, state: encountered|explained_to|asked_about|used|restated|confused,
               evidence_events[], first_at, last_at, inferred_by, user_override?}
NextStep:     {id, concept|question, reason: prerequisite_gap|open_question|unverified_reliance|conflict,
               score, computed_at}   # a view, regenerated
```

*Organization algorithms:*
1. Extract and canonicalize concepts, as in Model A.
2. **Propose prerequisite edges.**
   - An LLM judges candidate pairs: concepts that co-occur in passages, or whose definitions mention one another.
   - A second pass checks direction separately, because reversed direction is the main error (F11).
   - Remove cycles by dropping the lowest-confidence edge, then apply transitive reduction.
   - For mainstream domains, seed edges from public curricula or knowledge bases (unverified feasibility).
3. **Update engagement** deterministically from stance and attribution events. Never take it from an LLM's opinion of the user's knowledge, because that is where wrong-direction updates come from (F10).
4. **Compute the frontier.** Restrict the graph to the ancestors of active goals. The frontier is every concept whose prerequisites all have engagement of at least "explained_to", and which has not itself reached that level.
5. **Detect gaps:**
   - prerequisite gaps;
   - dangling references: concepts used in AI explanations and never explained, or later asked about;
   - reliance on unverified claims: AI-said, unchecked, then used by the user;
   - open tensions.
6. **Rank next steps** by goal relevance, readiness, how much they unblock, recency, and the need for verification.
7. **Reorganize the hierarchy** by evolutionary clustering with stable IDs. Polyhierarchy is allowed, following RAPTOR's soft membership.

*Recommended human views:*
- a home page of goals and the frontier, showing 4–7 items [01];
- a topic tree with engagement badges;
- concept pages, as in Model A, plus prerequisites and "what you asked";
- a gap map, a matrix of goal concepts against engagement state;
- a "learned this month" timeline;
- an open-questions list.

*Strengths:*
- it serves both halves of GOAL §3.2 directly;
- the structure is legible;
- the frontier is deterministic and explainable.

*Weaknesses:*
- the prerequisite graph is noisy (F11);
- engagement is only a proxy for learning (F10);
- the model is the most complex of the three.

#### Comparison

| Criterion (GOAL anchor) | A: statement ledger + pages | B: temporal concept graph | C: learning map |
|---|---|---|---|
| AI-said first-class (§4.2) | Strong (passages, speaker axis) | Weak unless passages added | Strong (inherits A) |
| Attribution and verification (§3.1) | Strong | Medium (edge metadata) | Strong |
| "What was learned" view (§3.2) | Medium (pages, feed) | Medium (community tree) | Strong (engagement overlay) |
| "What to learn" view (§3.2) | Weak | Weak | Strong (goals, frontier, gaps) |
| Reorganization with history (§3.2) | Good (events, aliases) | Partial (communities drift; re-ingest for schema) | Good |
| Maintainer checkability (§4.7) | High (invariants, cited pages) | Medium (LLM invalidation inside the library) | High |
| AI retrieval (§3.3) | Needs an index | Strong (PPR, hybrid) | Needs an index |
| Build cost for the prototype (§4.8) | Medium | Low–medium (library) | High |

**Recommendation for the design phase.** This is a HOW choice. Use **A as the canonical core and C as the human-facing structure compiled over it**. Borrow B's mechanisms (temporal edges, communities, PPR) as a *derived retrieval index* for the AI side, not as the store. Building the canonical store on Graphiti would bring in the "new wins" invalidation rule, rewritten summaries, schema changes that need re-ingesting, and the assistant-recall weakness.

### Other decisions the design must make

1. **Promotion threshold for AI-said content.** Assistant text dominates chat bytes. Keeping every assistant sentence as an item would flood the structure.
   - Proposed HOW: *all* assistant spans stay retrievable and attributed, at the passage level. Only content that is salient, linked to a concept, or later relied on is promoted to typed statements.
   - This must not quietly become "AI-said is second-class" (Risk R4).
2. **The verification budget and the verifier.**
   - Which kinds get external checks?
   - Is web search allowed for private content? That is a privacy question.
   - Must the checking model be from a different vendor?
   - How often are time-sensitive facts re-checked?
3. **The engagement vocabulary shown to the user,** and whether to offer *optional* generation probes ("explain X in one line?"). They are the only route to real evidence of learning (F10, F14), and they must never be required (GOAL §4.1).
4. **The source of prerequisite edges:** LLM only, or LLM plus seeding from curated sources for mainstream topics. Also the direction-check threshold.
5. **Hierarchy shape:** a single tree, or a polyhierarchy shown as a tree with "also in" links. Also the stability weight: how much better a new clustering must be before the system reorganizes.
6. **Concept identity policy:** when the AI may mint a new ID because the meaning changed, and when it must alias (OBO Principle 19 [06]).
7. **Page regeneration policy:** regenerate the whole page when inputs change, or regenerate per section with leaf citations. Both must avoid editing previous text.
8. **Human surface** (shared with the surfaces track): generated Markdown or a static site readable in an existing editor; a local web app; or a published artifact page. Whichever is chosen, a global graph view is not a default.
9. **Cross-AI disagreement policy.** When Claude and ChatGPT teach conflicting things, the default should be an automatic open Tension plus a spawned Question, never a silent pick.

---

## Risks to the goal

- **R1. AI-taught errors become authoritative memory.** This threatens §4.2 and §6, "each item shows its sources".
  - Claim-level error rates are non-trivial, and much higher without browsing (F8).
  - Automatic verification agrees with humans only about 72–75% of the time and misses consistent errors (F9).
  - Much AI teaching cannot be checked at all.
  - Showing "source: Claude, 12 Sep" makes provenance visible but is not evidence of truth.
  - *Residual risk:* some wrong AI-taught content will sit in the structure labelled "unchecked" or "AI opinion". The flags reduce over-reliance, since sources reduced it in Kim et al., but do not remove it.
- **R2. "What has been learned" cannot be measured from chats alone.** This threatens the §6 criterion "a structured map of what they have learned".
  - The evidence (F10) says passive inference of a person's knowledge carries large errors.
  - Without performance evidence, which would come from probes the user may never answer, the system can show engagement, not learning.
  - Calling engagement "learned" would be a quiet re-scope of the goal. This note flags it instead: **the system will show "learned" as engagement with evidence. Whether that satisfies the user's intent is a question for the user.**
- **R3. Inferred "what to learn" may be noisy enough to ignore.** Prerequisite F1 is about 0.7, with reversed direction a common error (F11). Inferred goals over-reach [07]. In uncurated personal domains the frontier may be wrong often enough that the user stops trusting it. It is detectable but not yet quantified for this user.
- **R4. Volume gating could make AI-said knowledge second-class in practice** (§4.2). Any salience filter on assistant content risks dropping what the AI taught. The mitigation is passage-level retention of all assistant content plus an evaluation probe ("what did the AI tell me about X?") scored separately, as LongMemEval's single-session-assistant category does.
- **R5. Automatic reorganization against stable landmarks** (§4.3 against usable navigation). GOAL makes AI reorganization the default. Users navigate by recognition and location, and churn erodes that (F16, [02]). The stability cost and the change log reduce churn, but the tension between them is real.
- **R6. AI-built structure helps learning less than self-built structure.** Studying maps gives g = 0.43 against 0.72 for constructing them (F14). Fluent AI synthesis inflates felt understanding [01]. This does not violate a non-negotiable, because the user chose AI management, but the user should know the trade-off. Optional generation probes are the only mitigation that does not require a ritual.
- **R7. Drift in the maintainer's own projections** (§4.7). Community summaries, entity summaries and page rewrites all drift when they are built incrementally (F3, F4, F6). If leaf-only compilation and citation validators are skipped to save cost, maintenance errors stop being detectable.
- **R8. Misattribution at capture** (§4.2). Pasted AI output in user turns, users restating what an AI said, and cross-AI echoes can all turn AI-said content into "user-said". This is the error that HaluMem measures at 43–55% in production systems [08].
- **R9. Lock-in from off-the-shelf graph stores.** Graphiti needs a re-ingest to retype old data, and LightRAG documents no deletion path. Either conflicts with the evolving schema and the excision requirement (round-1 FR28).

---

## Sources

*Round-1 notes (constraints on HOW):* `docs/research/01-human-memory-and-learning.md`, `02-pkm-practice-and-failure.md`, `04-epistemic-representation.md`, `06-time-history-and-consolidation.md`, `07-human-vs-ai-consumers.md`, `08-ingestion-and-extraction.md`, `SYNTHESIS.md`.

**Personal knowledge graphs and statement models**
- Balog and Kenter, "Personal Knowledge Graphs: A Research Agenda", ICTIR 2019, DOI 10.1145/3341981.3344241: https://research.google/pubs/personal-knowledge-graphs-a-research-agenda/
- Skjæveland, Balog, Bernard, Łajewska and Linjordet, "An Ecosystem for Personal Knowledge Graphs: A Survey and Research Roadmap", *AI Open* 5 (2024): https://arxiv.org/abs/2304.09572
- Bernard et al., "PKG API: A Tool for Personal Knowledge Graph Management", WWW '24 Companion: https://arxiv.org/abs/2402.07540
- Wikidata, Help:Ranking: https://www.wikidata.org/wiki/Help:Ranking ; P2241: https://www.wikidata.org/wiki/Property:P2241 ; Wikibase statement model (lecture notes): https://courses.cs.umbc.edu/graduate/691/fall22/kg/notes/24_wikidata/wikibase.pdf

**LLM-built knowledge structures**
- Rasmussen et al., "Zep: A Temporal Knowledge Graph Architecture for Agent Memory" (Jan 2025): https://arxiv.org/abs/2501.13956
- Graphiti README (observed 2026-10-07): https://github.com/getzep/graphiti ; Custom entity and edge types: https://help.getzep.com/graphiti/core-concepts/custom-entity-and-edge-types
- Edge et al., "From Local to Global: A Graph RAG Approach to Query-Focused Summarization" (2024): https://arxiv.org/abs/2404.16130 ; GraphRAG `update` docs (third-party mirror, observed 2026-10-07): https://www.mintlify.com/microsoft/graphrag/cli/update
- Microsoft Research, "LazyGraphRAG" (Nov 2024, updated Jun 2025): https://www.microsoft.com/en-us/research/blog/lazygraphrag-setting-a-new-standard-for-quality-and-cost/
- Sarthi et al., "RAPTOR", ICLR 2024: https://arxiv.org/abs/2401.18059
- Rezazadeh et al., "From Isolated Conversations to Hierarchical Schemas: Dynamic Tree Memory Representation for LLMs" (MemTree), ICLR 2025: https://arxiv.org/abs/2410.14052
- Gutiérrez et al., "From RAG to Memory: Non-Parametric Continual Learning for LLMs" (HippoRAG 2), ICML 2025: https://arxiv.org/abs/2502.14802
- Guo et al., "LightRAG", EMNLP 2025 Findings: https://arxiv.org/abs/2410.05779
- Xu et al., "A-Mem: Agentic Memory for LLM Agents", NeurIPS 2025: https://arxiv.org/abs/2502.12110
- Cognee repository (README and vendor pages only): https://github.com/topoteretes/cognee
- Karpathy, "LLM Wiki" gist (created 2026-04-04; read directly): https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

**Topic hierarchies and stability**
- Tamkin et al., "Clio: Privacy-Preserving Insights into Real-World AI Use" (Dec 2024): https://arxiv.org/abs/2412.13678
- Wan et al., "TnT-LLM: Text Mining at Scale with Large Language Models", KDD 2024: https://arxiv.org/abs/2403.12173
- Chakrabarti, Kumar and Tomkins, "Evolutionary Clustering", KDD 2006 (full text not re-read; framing via the survey): https://arxiv.org/abs/1401.3516

**Learning structures, learner models, what to learn**
- Falmagne et al., "Knowledge Spaces and Learning Spaces": https://arxiv.org/abs/1511.06757 ; ALEKS learning-space chapter: https://www.mheducation.com/content/dam/mhe/research/prek-12/essa-tier-4/aleks-assessing-learning-space.pdf ; Knowledge space overview: https://en.wikipedia.org/wiki/Knowledge_space
- Skycak, "How Math Academy Creates its Knowledge Graph" (developer-authored): https://justinmath.com/how-math-academy-creates-its-knowledge-graph/ ; summary of *The Math Academy Way*: https://frankhecker.com/2025/02/14/math-academy-part-7/
- Capture-Calibrate-Coach (2026): https://arxiv.org/abs/2605.25419 ; Scientific Contribution Graph (2026): https://arxiv.org/abs/2605.15011 ; Le and Abel, LLM prerequisite prediction (2025): https://arxiv.org/abs/2507.18479
- Scarlatos, Baker and Lan, "Exploring Knowledge Tracing in Tutor-Student Dialogues using LLMs", LAK 2025: https://arxiv.org/abs/2409.16490
- Hooshyar et al., "Problems With Large Language Models for Learner Modelling" (Dec 2025): https://arxiv.org/abs/2512.23036
- Watanabe and Ishimaru, "Can AI Guess What You Know?" (May 2026): https://arxiv.org/abs/2605.22971
- Graesser and Person (1994), *AERJ*: https://talkbank.org/class/access/0docs/graesser1994.pdf ; Person et al. (1994): https://talkbank.org/class/access/0docs/person1994.pdf ; Otero and Graesser (2001), PREG, *Cognition and Instruction* 19(2) (not re-read)
- Bull, "Negotiated learner modelling to maintain today's learner models", *RPTEL* (2016): https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6302918/ ; Bull and Kay, SMILI: https://research.birmingham.ac.uk/en/publications/smili-a-framework-for-interfaces-to-learning-data-in-open-learner/ ; Bodily, Kay et al. (2018): https://research.ou.nl/en/publications/open-learner-models-and-learning-analytics-dashboards-a-systemati/
- Schroeder, Nesbit, Anguiano and Adesope (2018), *Educational Psychology Review* 30(2): https://link.springer.com/article/10.1007/s10648-017-9403-9 ; Nesbit and Adesope (2006): https://www.sfu.ca/~jcnesbit/research/nesbitadesope2006.htm ; Schicchi et al. (2025), ChatGPT concept maps: https://iris.uniroma3.it/handle/11590/511000

**AI-taught content correctness and verification**
- OpenAI GPT-5 System Card (arXiv copy): https://arxiv.org/abs/2601.03267 ; secondary summary of raw rates (unverified): https://www.implicator.ai/gpt-5-cuts-claim-errors-to-9-6-with-browsing-system-card-shows.md
- Pardos and Bhandari (2024), *PLOS ONE* 19(5), DOI 10.1371/journal.pone.0304013: https://doi.org/10.1371/journal.pone.0304013
- Kim et al., "Fostering Appropriate Reliance on Large Language Models", CHI 2025: https://arxiv.org/abs/2502.08554
- Wei et al., "Long-form factuality in large language models" (SAFE), 2024: https://arxiv.org/abs/2403.18802
- Farquhar, Kossen, Kuhn and Gal, "Detecting hallucinations in large language models using semantic entropy", *Nature* 630 (2024): https://www.nature.com/articles/s41586-024-07421-0

**Human views and tools**
- Ferreira et al., Obsidian case study (2025): https://arxiv.org/abs/2509.20187 ; Obsidian forum thread on graph view: https://forum.obsidian.md/t/whats-the-point-of-the-graph-view-how-are-you-using-it/71316 ; Konik, "In Defense of Obsidian's Graph View": https://www.eleanorkonik.com/its-not-just-a-pretty-gimmick-in-defense-of-obsidians-graph-view
- Amadieu et al. (2009), *Learning and Instruction* 19(5): https://research.ou.nl/en/publications/effects-of-prior-knowledge-and-concept-map-structure-on-disorient/ ; Jáñez and Rosales, hypertext disorientation: https://ajet.org.au/index.php/AJET/article/view/4617 ; Müller-Kalthoff and Möller (2003) (secondary summary only)
- Google, "Use Mind Maps in NotebookLM": https://support.google.com/notebooklm/answer/16212283 ; launch coverage (Mar 2025): https://9to5google.com/2025/03/27/notebooklm-mind-map/
- Dumais et al., "Stuff I've Seen", SIGIR 2003: https://www.cs.odu.edu/~sampath/courses/w17/cs599/papers/SISCore-SIGIR2003-Final.pdf
- Tana supertags docs (observed 2026-10-07): https://tana.inc/docs/supertags ; Heptabase changelog 2025: https://wiki.heptabase.com/changelog/2025
- Discourse Graphs Obsidian plugin: https://community.obsidian.md/plugins/discourse-graphs ; Chan et al., "Steps Towards an Infrastructure for Scholarly Synthesis" (2024): https://arxiv.org/abs/2407.20666
