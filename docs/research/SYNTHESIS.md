# Research synthesis: foundations for a personal knowledge & memory system

> **Superseded framing (2026-10-07).** The reframing in this document, "a loop, not a store" and a commitment ledger plus a weekly ritual (§1.4 priorities, §2.1 composite frame, §8 kill signals that favour ritual), was **rejected by the user**. [`docs/GOAL.md`](../GOAL.md) is authoritative. The individual findings, principles and failure modes remain valid as **constraints on how** the system is built: attribution, supersession, never summarising summaries, context rot, sycophancy, injection, and evaluation methods.

*Synthesis of nine research tracks, 2026-10-07. This document turns the research into inputs for design. It restates the problem, challenges the framing, extracts principles, maps the tensions and the design space, drafts requirements, and names the experiments to run before committing to an architecture. It does not choose the design. That is the next document's job.*

**Citation key.**

| Key | File |
|---|---|
| [01] | `01-human-memory-and-learning.md` |
| [02] | `02-pkm-practice-and-failure.md` |
| [03] | `03-ai-memory-systems.md` |
| [04] | `04-epistemic-representation.md` |
| [05] | `05-reasoning-decisions-goals-questions.md` |
| [06] | `06-time-history-and-consolidation.md` |
| [07] | `07-human-vs-ai-consumers.md` |
| [08] | `08-ingestion-and-extraction.md` |
| [09] | `09-evaluation-and-failure-modes.md` |

Numbers are quoted from the track notes, which mark anything they could not re-verify. Vendor-reported figures are claims, not independent results.

**Summary.**

1. **The bottleneck is not storage or recall.** Raw logs, a strong model and search already handle recall. A gpt-4o-mini agent using grep over plain files scored 74.0 on LoCoMo, against 66.9 for Mem0 [03][09]. Two parts remain unsolved:
   - **The write path:** attribution, updates and conflicts. HaluMem measured update omission at 52–94% [09].
   - **The human loop:** integration, review and ownership.
2. **The thing to build is a loop around a commitment ledger, not a knowledge base.** The ledger records what the person explicitly holds, has decided, and is asking. AI bookkeeping keeps it current. It changes only through reasoned, reviewable events. Separate views of it are compiled for the person and for AI tools.
3. **All nine tracks independently reached the same skeleton:**
   - immutable sources, then an append-only ledger of typed events, then disposable views;
   - supersede, never overwrite;
   - "the AI said X" is not "I believe X";
   - link conflicts instead of resolving them automatically;
   - rebuild syntheses from items anchored in sources, never from earlier summaries.
4. **The three riskiest assumptions can each be tested in days, before any architecture is built:**
   - the user's AI conversations contain enough extractable commitments;
   - stance can be attributed correctly;
   - the user will do a bounded amount of review.

---

## 1. The problem, restated precisely

### 1.1 What makes something a "fragment"

A captured item is a fragment if it lacks any of the following five properties.

1. **Demand.** Nothing links it to a question, goal, decision or project that makes it relevant [02][05].
2. **Relation.** It has no stated relation to existing commitments: supports, contradicts, refines, supersedes or answers [01][02][04].
3. **Attribution.** It is unclear who asserted it (the person, an AI, an author, a colleague) and whether the person holds it [04][08].
4. **Status and time.** It is unclear whether it is current, superseded, tentative or contested, and since when [03][06].
5. **Grounding.** Nothing points back to the source span that justifies it [03][06].

Size is not the issue. Luhmann's cards were small, but each was related to existing cards when he wrote it, so none was a fragment in this sense [02]. Items that never gain these properties go dead:
- In the List.it study, 75% of notes were never edited after capture.
- Luhmann's own index had "black holes" of poorly linked cards that faded [02].

### 1.2 What "coherent, evolving understanding" means

The brief merges two different things.

- **In the record.** Every retained commitment is placed relative to the person's agenda and their other commitments. It carries attribution, status, confidence and grounds. Its change history can answer "what did I hold on date D, and why did that change?"
  - *Coherence* here means legible structure, *including visible open conflicts*. It does not mean consistency [03][04].
  - *Evolution* means change through typed, reasoned events, not overwrites [04][06].
- **In the person.** The person can reconstruct, explain, predict and apply without looking, with calibrated confidence [01]. Track 01 gives six conditions:
  - compressed generative structure;
  - grounding that indexes back to the sources;
  - consistency that is maintained, or conflict that is deliberately held open;
  - calibrated metacognition;
  - revision driven by prediction error;
  - live use.

A system can guarantee the first. It can only scaffold the second. The evidence that the two come apart is unusually clear: fluent AI synthesis raises *felt* understanding while lowering actual learning [01].
- In Bastani et al., students who had used unrestricted GPT-4 scored 17% lower on exams once access was removed.
- In Melumad & Yun (n=10,462), LLM syntheses produced shallower knowledge than web search.

A design that improves the record at the person's expense has failed, even if it passes every benchmark.

### 1.3 Four kinds of change

"Evolving" covers four kinds of change, each needing its own mechanism. A single version field cannot carry all four [06].

| What changes | Example | Mechanism |
|---|---|---|
| The world | A fact stops being true | Valid time |
| The person's mind | They change their view, or discover an error | Stance records; revision kept separate from update [04] |
| The representation | Schemas, IDs, merges | Identity and obsoletion rules |
| The machinery | Models retired, embeddings invalidated | LLM outputs recorded as events; embeddings treated as caches |

### 1.4 Jobs to be done

| # | Job | Question | Served today? |
|---|---|---|---|
| J1 | Position | "Where do I stand on X, why, and how sure am I?" | Poorly. No product stores grounds or stance [03] |
| J2 | History | "When and why did I change my mind about Y?" | Not at all. It has to be generated from revision events, because people misremember their past views (Markus 1986) [05] |
| J3 | Decisions | "What did I decide and reject, and was it a good decision given what I knew then?" | Only ADRs in code, and those are thinly adopted [05] |
| J4 | Agenda | "What am I still figuring out, and does this new item bear on it?" | No [05] |
| J5 | AI context | "Don't make me re-explain. Don't re-suggest what I rejected. Don't flatter me." | Partly, by vendor memory, which is opaque, unscoped and increases sycophancy [03][07] |
| J6 | Honesty | "Which of my beliefs rest only on what an AI said? Where am I overconfident?" | No [01][04] |
| J7 | Internalise | "Help me *know* this, not just *have* it." | Spaced repetition works for those who stick with it, but it is not integrated with anything else [01][02] |
| J8 | Refind | "Where was that thing?" | Largely solved by search over raw text [02][03][07] |
| J9 | Resume | "Get me back up to speed on project P after three weeks away." | Partly, by vendor project memory [03] |

Where the opportunity lies:
- Most products compete on J8, which has the least value left to capture.
- J1–J4 and J6 are the gap.
- J5 is valuable but carries the most risk: sycophancy, injection and leakage.
- J7 has the strongest evidence behind it and the weakest adoption.

---

## 2. Challenging the framing

### 2.1 Is "knowledge base" the right frame?

| Frame | What it gets right | What it gets wrong |
|---|---|---|
| **Store / archive** ("second brain") | Durability, search, provenance | Optimises capture and organising, which learning research rates low-utility. Most notes are write-only. Heavy filing did not improve refinding across 345 email users. Such stores tend to become a "mausoleum" [01][02] |
| **Living documents** (AI-maintained wiki, e.g. Karpathy's llm-wiki) | Readable syntheses; a lint pass | Drifts silently. In ACE, a single rewrite collapsed an 18,282-token context to 122 tokens. Unclear whose understanding the pages represent [02][03][06] |
| **Model of the person** (vendor AI memory) | Directly useful to AI tools | Stores third-person facts where newest wins. Models over-infer 35–49% of user attributes. Memory profiles raised agreement sycophancy by up to 45% [03][07]. It models the user *for the AI*, while the brief wants the user's own understanding of the world |
| **Practice / process** (Luhmann's evening integration) | Integration is where understanding forms [02] | Decays without infrastructure. Most adopters never sustain it |
| **Question-driven agenda** (Feynman, Hamming) | Supplies relevance, and gives conflicts a home [04][05] | Ideas often arrive before a question for them exists. Untested whether people navigate by questions |
| **Commitment ledger / belief base** | Honest about what can be modelled: expressed commitments, not the mind [04]. Supports as-of history [06] | On its own it is just another store |
| **Review and feedback instrument** (decision journal plus calibration) | Possibly where the biggest personal payoff is [05] | Narrow. Ignores reading and learning |

**Proposed composite frame (to confirm in design): a loop, not a store.** The core is a ledger of the person's explicit commitments (positions, decisions, questions, predictions, goals) and of the evidence they encountered.
- It is organised around a short agenda of open questions.
- AI bookkeeping keeps it current.
- It changes only through attributed, reasoned events.

It is used through two loops:
1. An **integration loop**: in bounded sessions, the person relates new material to their commitments.
2. A **compilation loop**: the system produces scoped, budgeted context for AI tools.

The archive is necessary infrastructure, not the product.

### 2.2 What would make this fail even if built well

1. **Abandonment.** This is the base rate for PKM systems. Upkeep separates from use and the backlog grows visibly [02]. No benchmark measures it [09].
2. **Understanding moves out of the person and into the store.** If the AI does the consolidation, the store becomes coherent while the person does not, and the person *feels* smarter regardless (Fisher 2015; Ward 2021) [01][07].
3. **The simple baseline wins.** Suppose raw logs, a frontier model and hybrid search answer the user's real questions nearly as well. Then the structured layer is cost without margin. Long-context gains push in this direction: on MRCR 8-needle at 1M tokens, scores went from 18.5% to 76% in one model generation [07].
4. **Review turns into rubber-stamping.** Low-precision queues train people to click "accept". Clinicians override drug alerts 49–96% of the time (recalled figure) [08]. A store that has been rubber-stamped carries false authority, which is worse than a store honestly labelled unreviewed.
5. **The sources don't contain the knowledge.** In this machine's agent logs, plain user text was about 2.5% of characters, and explicit endorsement in chats runs at about 1% [08]. Much of what a person believes lives only in behaviour, or is never expressed at all.
6. **The builder's trap.** The user is an engineer building a tool for their own use. Bitemporal ledgers and three-model evaluation harnesses are satisfying to build. Track 02's "maintenance becomes the hobby" applies to building as much as to note-keeping. The guard is an early trial on the user's own data.
7. **The schema decays like a taxonomy.** Every typed object model is a small taxonomy. Formal structure demanded up front is the best-documented failure in this area [02][04][05].
8. **A trust incident.** Any of these would break trust:
   - a persistent prompt injection (SpAIware; MINJA, 98.2% success under idealised conditions);
   - wrong-context disclosure (ConfAIde: 39%);
   - an AI narration ("you used to believe…") that implants a false memory (Chan et al.) [01][07][09].
9. **Circular evaluation.** The designer, the user and the labeller are the same person. Satisfaction metrics actively mislead [01][09].

### 2.3 What the user is probably underestimating

- **Attribution is the hardest problem, and it starts at the source adapters.** In agent logs, `role=user` is not the user. Production memory systems absorb 43–55% of assistant-introduced distractors as user memory [08]. In the AI era, a growing share of what someone "knows" is AI testimony they never examined.
- **The payoff is in review and integration, and those cost the person's time.** AI can make them cheaper. It cannot remove them without also removing the benefit [01][02][05].
- **Recall is mostly solved.** Differentiation has to come from revision with reasons, attribution, uncertainty, legibility and trust [03].
- **Evaluation is a workstream, not a phase.**
  - No public benchmark tests reasons, dissent, open questions or attribution [09].
  - In one small study, architecture rankings flipped between week 3 and week 9 of use [03].
- **Deletion is a day-one requirement.** It must reach every derived store. Datomic shipped a critical fix for exactly this in October 2025 [06].
- **Integration on the capture side cannot wait.** A pre-outcome record only has value if it is captured at the time, which means inside the AI conversations where decisions are made [05][07]. Integration on the read side (files, CLI, MCP) can wait.

### 2.4 What holds up

- **Fragmentation is real, but the fix is relating, not merging.** Forced reconciliation produces "synthetic models" that are wrong in new ways. Some knowledge is legitimately context-bound [01][06].
- **Evolution without destroying history is well supported and cheap.** The real risk is *burying* history so that it never resurfaces at decision points [06].
- **Human and AI needs do differ, but two other axes matter more.** One is **authority and endorsement**: who asserted something, and whether the person endorsed it. The other is **task scope** [07].
  - There is also a third consumer: the maintenance process itself [04].
  - The tracks converge on different *views* of one canonical record [02][03][04][07].
- **Not assuming an architecture is vindicated.** Plain substrates compete with elaborate graphs [03][07].
- **Researching before building was right.** The research has now converged enough to start narrow experiments.

---

## 3. Cross-cutting principles

1. **Separate layers by update rule.**
   - Sources: immutable and content-addressed.
   - Ledger: append-only, recording typed events.
   - Views: disposable and deterministic.

   This is the strongest convergence across the research, and it echoes the brain's split between fast capture and slow integration. [01][02][03][06][07][08]

2. **Supersede, never overwrite; deprecate with a reason; excise only for privacy.**
   - Destructive updates conflate "the world changed" with "I was wrong". Even Mem0 moved to ADD-only extraction in 2026.
   - Deprecated records act as antibodies against re-ingesting errors that were already corrected (as in Wikidata).
   - Excision is a separate, tested operation that propagates to every derived store.

   [01][03][04][05][06][08]

3. **Integration is the core operation, not capture.** Every ingested item yields a proposed relation to an existing commitment or an open question: supports, contradicts, refines, answers, or new. Luhmann related cards at write time. In the KReC model of knowledge revision, revision requires the old and new knowledge to be active together and linked. [01][02][05]

4. **Attribution and endorsement are first-class.**
   - Record three things: who said it, whose view it is, and the person's stance toward it.
   - Assistant assertions default to *encountered*.
   - AI-inferred rationale and credence are never stored as the person's own. LLM-generated rationale matched the actual rationale with precision of only about 0.27.

   [03][04][05][06][07][08][09]

5. **Count independent lineages, not mentions.** AI restatements, echoes of the person's own claims, and summaries of summaries each count as one lineage. Illusory truth, citogenesis and Greenberg's citation-network analysis all show echoes manufacturing authority. [01][04][06]

6. **Link conflicts explicitly; never resolve them automatically.**
   - Leaving reconciliation to read time fails: STALE's best model scored 55.2%, and agents in MERIT acted correctly on retrieved values only 55% of the time.
   - Forced resolution produces synthetic blends.
   - Most "contradictions" are scope or time mismatches, so conflicts need types: rebut, undercut, scope, temporal.

   [01][03][04][06][09]

7. **Never summarise summaries.** Syntheses are views, regenerated from itemised claims anchored in sources and updated by deltas. Evidence:
   - ACE's context collapse dropped accuracy below the no-context baseline.
   - Telephone-game experiments show chained summaries drifting toward attractors.
   - Rare details vanish first.
   - Generative consolidation pulls memories toward the existing schema.

   [01][03][06][09]

8. **The AI keeps the books; the person makes the meaning.**
   - AI: detection, linking, provenance, scheduling, drafting.
   - Person: resolving conflicts, adopting beliefs, restructuring, and explaining their core models in their own words.

   This is a hypothesis to test, not a finding (T4). [01][02][04][05][07]

9. **Organise by demand, not by topic.** Questions, decisions, goals and projects are the anchors. Topics are secondary tags. The person never maintains a taxonomy. [01][02][04][05]

10. **Formalise incrementally.** Capture is free text. Structure is proposed later and confirmed lazily. The failures of IBIS and QOC, and the 63% of ADRs created already marked "accepted", show what upfront formality costs. [02][04][05][07]

11. **Make time explicit.** Keep valid time, recorded time and held (belief) time separate, and keep a proposition separate from the person's stance toward it. The time something was captured is only an upper bound on when it started being believed. [03][04][06][07]

12. **Freeze what was believed before the outcome.** Expectations, reasons, confidence and assumption versions are locked at the moment of commitment. Reviews compare memory against that record, which counters hindsight and consistency bias. [01][05][06]

13. **One canonical record, many compiled views.** Human views and AI views are both projections of the record. Nothing is edited in two places. [02][03][04][07]

14. **For AI, a small, scoped, labelled context beats a large one.**
    - Context rot is worst with semantically similar distractors, which is exactly what a personal corpus is full of.
    - On OP-Bench, memory-augmented agents scored 26–61% worse than memory-free ones on appropriateness.
    - The vendors' fixes for complaints were scoping and legibility, not better recall.

    The answer is a core pack, an index, and just-in-time tools. [03][07][09]

15. **Untrusted content never becomes an instruction.** Memory turns a one-off injection into a standing one. External and AI-generated text is stored as quoted data. Only the person can create instructions. [03][07][08][09]

16. **Budget human attention.** Size review queues by time, not volume, and rank items by value of information. The acceptance rate has both a floor (below it, proposals are noise) and a ceiling (above it, review is rubber-stamping). [02][03][05][07][08][09]

17. **Salience decays; existence does not.** Ranking blends recency-and-use activation, similarity and demand. Only an explicit excision removes data. [01][03][06]. This is contested by [02][05]; see disagreement 6 in §4.12.

18. **Beat the simple baselines on the write path, and measure the person.** Success is judged by what the person can do and would sign, not by satisfaction or recall. [01][03][07][09]

---

## 4. The core tensions and trade-offs

**T1. Capture cost vs structure.**
- *Options:*
  - Rich typed capture.
  - Free text, with structure proposed later.
  - No stored structure; extract at query time.
- *Evidence:*
  - Formal capture fails [04][05].
  - Query-time reconciliation also fails, scoring around 55% on STALE and MERIT [03][04].
  - Extraction errors are mostly omissions [08][09].
- *Points toward:* zero-friction raw capture, batch extraction of typed *candidates*, and lazy confirmation.
- *Open:* does eager extraction beat episode digests plus raw spans at query time [08]? Test it in E3.

**T2. Fidelity vs consolidation.**
- *Evidence:*
  - In LongMemEval, storing extracted facts *as the stored values* hurt accuracy. Using them as extra *index keys* over raw text improved recall@k by 9.4% [03].
  - Summaries can collapse (ACE) [03].
  - When generated data replaces originals, the tails are lost. Keeping originals bounds the error [06].
  - In the Go-CLS model, only consolidations that generalise are worth making [01].
- *Points toward:*
  - Sources are the only truly immutable layer. Claims are versioned interpretations of them.
  - Promote a generalisation only when at least two independent episodes support it.
  - Leave some fragments unconsolidated on purpose [06].

**T3. Human legibility vs machine structure.**
- *Evidence:*
  - Atomising text strips out the "because" and "unless" [08].
  - Proposition-level indexing helps retrieval [08].
  - People review narratives, not 400 separate facts [08].
  - Models use explicit, checkable statements well [05].
- *Points toward:*
  - Claims as the unit of update and citation; passages and pages as the unit of reading [03].
  - The human view is its own projection.
- *Open:* can a single "claim block" serve both readers [07]?

**T4. Automation vs ownership. This is the central tension.**
- *Options:*
  - (a) The person writes the belief layer.
  - (b) The AI drafts and the person signs.
  - (c) The AI writes the AI-facing context and the person writes the beliefs.
  - (d) The AI writes everything and the person audits.
- *Evidence for keeping the person in:*
  - The generation effect.
  - Bastani, Kreijkes, and Melumad & Yun on learning losses.
  - Kosmyna on ownership.
  - Lee on critical thinking.

  [01][02][07]
- *Evidence against:*
  - Upkeep is the bottleneck [02].
  - Review clicks are noisy: people endorse in hindsight, and fluent text gets accepted. Behavioural signals may be better evidence [08].
- *Points toward:* split by layer.
  - The AI may write anything that is *labelled as AI*: digests, candidate links, compiled context.
  - Only items the person has confirmed enter "my position".
  - The person writes explanations only for the few models they want to internalise.
- This is the most important A/B test [02].

**T5. History vs evolution and forgetting.**
- *Evidence:*
  - Belief history is where the system adds the most over human memory, which suffers from consistency and hindsight bias [01][05].
  - On the other side: the mausoleum effect, and the fact that most stores are write-only [02].
  - Storage is not a constraint [06].
- *Points toward:*
  - Keep everything in the ledger, but hide superseded items from default views using Wikidata-style ranks.
  - Resurface history at decisions and conflicts, as quoted, dated records rather than narrative [01].

**T6. Precision vs privacy.**
- *Evidence:*
  - Accurate memory surfaced in the wrong context is a leak [09].
  - Users accept inferences they can see, but not third-party access to them [07].
  - Agent logs contain secrets [08].
  - Context already sent to a provider cannot be recalled [06].
- *Points toward:*
  - Deterministic secret and PII scanning before any model call.
  - Sensitivity tags that gate export.
  - Context receipts.
  - Scoped packs.
- The user's stance decides the rest.

**T7. Update speed vs drift resistance; resolving at write time vs read time.**
- *Evidence:*
  - BeliefShift reports that models which personalise aggressively resist drift poorly, while factually grounded models miss real updates [09].
  - MERIT favours resolving at write time; Mem0's 2026 design chose read time [03].
  - Omission dominates [09].
- *Points toward:*
  - Link at write or consolidation time.
  - Auto-apply only unambiguous, dated world-changes.
  - Route stance changes to review.
  - Report false updates and missed updates separately.

**T8. Learning friction vs adoption.**
- *Evidence:*
  - Learners prefer the fluent option even when it works worse; in Kreijkes et al., students preferred the LLM.
  - Metacognitive feedback reduced offloading (Maier 2026, preprint) [01].
  - Spaced repetition works only for those who keep doing it [02].
- *Points toward:* generation-first only for items flagged "want to know". Everything else only needs to be findable (E9).

**T9. Personalisation vs critique.**
- *Evidence:*
  - Memory profiles raised sycophancy by up to 45%.
  - Memory hurt appropriateness on OP-Bench [07].
- *Points toward:*
  - Present beliefs to the AI as positions, with confidence and the strongest counterargument.
  - A critique-mode pack that leaves beliefs out.
  - "Do not assume" cards and rejected-option cards [04][05][07].

**T10. In-the-moment capture vs batch extraction.** [05] and [08] disagree.
- **[05]:** draft-and-confirm at the moment of commitment, to lock the pre-outcome fields.
- **[08]:** extract in batch after the episode, because stance belongs to the whole episode and per-turn guesses come too early.

*Partial dissolution.* Raw episodes are immutable and timestamped. Batch extraction from *the episode alone*, without later context, still recovers what was said at the time. Hindsight contamination enters only when the person reconstructs from memory or the extractor sees later material. What cannot be recovered later is what was never said: expectations and confidence.

*Points toward:*
- Batch by default.
- An in-the-moment prompt only for expectation and confidence at decisions (as [05] itself suggests), at most once per session (as [08] suggests).

**T11. Rich ontology vs minimal kinds.** The tracks propose four type systems.

| Track | Proposed types |
|---|---|
| [04] | Proposition, Attribution, Stance, Relation, Question, Tension |
| [05] | Question, Decision, Prediction, Goal, Principle, Log entry |
| [03] | claim.kind ∈ {belief, observation, decision, goal, question, hypothesis, preference, instruction} |
| [07] | entry.kind ∈ {instruction, preference, fact, belief, decision, goal, open-question, event} |

They sit at different levels rather than competing:
- [04] describes the epistemic *mechanism*: how anything is asserted and held.
- [05] lists *practical objects*.
- [03] and [07] are *consumer-facing kinds*.

But their union is about 15 types, which is the rich-schema failure. *Points toward:*
- A small core: source/episode, an item with a kind, stance and attribution, typed relations, and question.
- A coverage test on 50 real conversations (E1). [05] says fewer than 15% of items should be inexpressible; [03] says fewer than 10% should need an "other" kind.

### 4.12 Direct disagreements between tracks

| # | Issue | Position A | Position B | How to settle |
|---|---|---|---|---|
| 1 | **Canonical substrate** | [06]: SQLite is canonical (the Library of Congress lists it as "preferred"), with a JSONL ledger mirror. Markdown is only an export, and the Library of Congress does not list Markdown at all | [07][02]: Markdown files with YAML frontmatter are canonical and editable. A database is only a rebuildable projection | Decide by *who edits what*. Pages the person edits must be canonical files. The event ledger can be SQLite or JSONL either way |
| 2 | **Proposition identity** | [04]: id = hash(text) | [06]: IDs name meanings (OBO Principle 19). Rewording keeps the ID; a change of referent mints a new one | Use hashes for immutable spans and versions. Use minted stable IDs for ideas. [04]'s own open question about paraphrase identity agrees |
| 3 | **Regenerating derived layers** | [03][08]: every derived layer must be regenerable from sources, for example by a better extractor | [06]: LLM outputs are non-deterministic decisions, so they are recorded and replay never calls a model | Both, because they are different properties. *Replay* reproduces what the person saw. *Re-extraction* is a new recorded batch of proposals, never a silent overwrite |
| 4 | **Human time budget** | [02]: a daily pass of 10–15 min, about 70–105 min a week | [03]: about 10 min a week. [08]: 15 min a week or less. [07]: under 5 min a day. [09]: stop if over 30 min a week. [05]: 20 s or less per object | The tracks disagree by about 10× on the core cost. Only the user can answer (Q3). Measure it in E4 |
| 5 | **Acceptance-rate thresholds** | [02]: throttle below about 40%. [04]: below about 50%, the schema is wrong | [05]: 70% or more of drafts accepted. [08]: healthy between about 60% and 90%; above 95% is rubber-stamping | Use a band with a floor and a ceiling (about 50–90%) and calibrate it in Stage 0 |
| 6 | **Forgetting** | [01][03][06]: nothing is deleted for relevance; only salience is demoted | [02]: "not everything should be kept forever". [05]: fragments attached to no question, goal or decision "may be legitimately disposable" | The real question is existence vs visibility. The ledger keeps everything, default views drop items, and the person can excise in bulk. Whether auto-archiving needs consent is open |
| 7 | **Review as ground truth** | [01][02][04]: what the person endorses is the gold standard for "my belief" | [08]: review clicks are noisy. Behaviour (commits, reuse) may deserve more weight | Record both as separate stance signals. Neither silently overrides the other |
| 8 | **Uncertainty** | [04]: five ordinal levels with numeric brackets, plus resilience, plus optional forecasts | [03]: categories to start. [04] itself asks whether structural uncertainty (open questions, unanswered attacks) is enough | Start with structure plus three levels. Add levels only if re-rating agreement holds up [04] |
| 9 | **Eager vs lazy extraction** | [04][05]: rich typed objects, extracted up front and maintained | [08]: digests plus raw spans plus query-time extraction may suffice. [03]: raw search already solves recall | Run them head to head on the user's own probes (E3) |
| 10 | **AI-inferred stances in AI context** | [04]: allowed, labelled "inferred, unconfirmed" | [07]: kept out of the always-loaded core until confirmed | Never in the core pack. Allowed in on-demand retrieval, with the label |

---

## 5. The design space: independent decisions, not yet chosen

| # | Dimension | Realistic options | Constraint from evidence | Settled by |
|---|---|---|---|---|
| D1 | Canonical substrate | (a) Markdown and frontmatter, plus a log; (b) SQLite, plus a JSONL ledger and an export; (c) hybrid: a SQLite/JSONL ledger, with Markdown for text the person writes; (d) a graph DB | Nothing in the research supports (d). (a) vs (b) is disagreement 1 | D14, Q8 |
| D2 | Immutable unit | Sources only; or sources plus extracted claims | Extraction output varies between runs and models [08] | Design argument |
| D3 | Unit of update and citation | Atomic claim; proposition plus stance; typed object; page | Update claims, read pages [03][07] | E1, E3 |
| D4 | Number of types | About 4, about 8, or about 15 | T11 | E1 |
| D5 | Identity | Minted IDs that carry meaning semantics; content hashes; both | Disagreement 2 | Design argument |
| D6 | Primary anchor | Questions; goals and projects; chronology; emergent clusters | Questions are favoured but unvalidated [02][04][05] | E5 |
| D7 | Extraction timing | Hot path; batch after the episode, with a re-evaluation window; at query time; hybrid | Batch is favoured [08] | E2, E3 |
| D8 | Who can apply consolidation, per class of change | Auto-apply; auto-apply reversibly plus a digest; propose and confirm; person-authored only | With no one watching, auto-applied changes drift unnoticed [06] | E4, E6 |
| D9 | Who writes the belief layer | The person; an AI draft that the person signs; the AI, with an endorsement flag | T4 | E9, A/B test |
| D10 | Conflict policy | Newest wins; typed link plus review; resolve at read time | "Newest wins" is effectively ruled out [03][04][06] | E6 |
| D11 | Uncertainty representation | Structural only; 3 levels; 5 levels with brackets and resilience; probabilities | Disagreement 8 | Re-rating test |
| D12 | Temporal model | One timestamp; bitemporal; bitemporal plus held time | Cheap if built in from the start [06] | Fixture of about 30 scenarios |
| D13 | AI retrieval | Full preload; core pack plus index plus just-in-time tools; vector top-k; agentic file search plus semantic search | Hybrid beats either alone [07] | E3, E10 |
| D14 | Human surface | An existing editor over files; CLI plus generated pages; a local web app; inside AI chats | [02]: don't build an editor. [05]: review should happen in the conversation flow | Q3, Q8 |
| D15 | Review cadence | Daily; weekly; opportunistically, inside conversations; triggered by events | Disagreement 4 | E4 |
| D16 | Learning loop | None; opt-in generation prompts; generation-first by default; opt-in spaced repetition | T8 | E9, Q2 |
| D17 | Forgetting | Salience only; auto-archive unattached items; excision on request | Disagreement 6 | Q10 |
| D18 | Where models run | Cloud; tiered by sensitivity; local only | T6 | Q5, Q6 |
| D19 | First sources | Chat exports; agent logs plus git; own notes; highlights; email and meetings | [08] says start with chats, agent logs and git | Q1 |
| D20 | Capture integration | Import exports afterwards; a live tool or MCP inside conversations; both | T10 | E1, Q9 |

**How the dimensions couple:**
- D1 follows from D14.
- D9 constrains D8.
- D7 constrains D20.
- D3 drives D5.
- D18 can veto cloud options in D13 for sensitive scopes.

---

## 6. What existing systems get wrong, and what to reuse

### 6.1 The gap

- **AI memory systems** (Mem0, Zep, Letta, ChatGPT and Claude memory) personalise an assistant.
  - The unit is "User: X", and the newest value wins.
  - They drop justification, the kind of statement, contradictions, and why the person changed their mind [03].
  - They absorb assistant-introduced content as the user's own and omit most updates [08][09].
  - They are opaque by default, and they make injections persistent [07].
- **PKM tools** (Obsidian, Notion, Roam, Mem, Tana) centre on capture and organisation.
  - They carry no epistemic status and no belief history.
  - Their AI features do the synthesis for the person. There is no evidence this improves understanding, and early evidence that it reduces ownership [02].
- **LLM-maintained wikis** (Karpathy's llm-wiki) are closest in spirit. They lack attribution, a conflict policy and drift control [02].
- **Argument and discourse tools** (discourse graphs, IBIS, Kialo) separate evidence, claim and question correctly, but depend on manual formalisation [04][05].
- **Decision and forecasting tools** (ADRs, Fatebook) get supersession and calibration right, but sit isolated from everything else the person knows [05].

**The unclaimed combination** is a pipeline of four parts, none of which existing systems join up:
1. Ingest AI conversations with attribution, keeping "the AI said" separate from "I hold".
2. Keep a ledger of the person's commitments, with typed, reasoned revisions and as-of history.
3. Integrate through human review at bounded cost.
4. Compile scoped AI context that resists sycophancy.

No system found by any track does step 1 well. None treats a change of mind as a first-class event that can be queried.

### 6.2 Solved well enough to reuse

| Need | Reuse |
|---|---|
| Storage and query | SQLite with FTS5; JSONL. Git only for transport and backup [06] |
| Bitemporal history | Four timestamp columns in SQLite. No need for XTDB or Datomic [06] |
| Search | ripgrep, plus an off-the-shelf embedding model treated as a cache. Hybrid search wins [07] |
| Agentic retrieval | Existing coding agents (Claude Code, Codex) working over files [03][07] |
| Human reading and editing | An existing Markdown editor, not a custom one [02] |
| Interop | Markdown export, an AGENTS.md-style snippet, MCP resources and tools, a paste-able summary. Skip llms.txt [07] |
| Provenance and status | W3C PROV concepts; Web Annotation quote anchors; Wikidata-style ranks with reasons [04][06] |
| Secret and PII scanning | Gitleaks/trufflehog-style regex plus entropy checks; Presidio-like recognisers [08] |
| Export parsing | The documented export formats of ChatGPT, Claude, Readwise, Claude Code and Codex [08] |
| Calibration; spaced repetition | Brier scoring and a Fatebook-style loop [05]; the FSRS scheduler, if J7 is in scope [02] |
| Evaluation scaffolding | LongMemEval_S subsets; HaluMem-style scoring of each memory operation; ALCE citation metrics; FActScore-style atomic checking [09] |

### 6.3 Unsolved, and where this project's own work goes

- Inferring stance and attribution.
- Detecting and typing conflicts in personal text.
- Deciding when two statements are the same proposition.
- Consolidating without drift.
- Ranking review items by value of information.
- Measuring understanding.

---

## 7. Requirements draft

Priorities are MUST, SHOULD or COULD. **[H]** marks a hypothesis to test before the requirement is locked. All targets are initial values, to be recalibrated after Stage 0.

### Functional

| ID | Pri. | Requirement |
|---|---|---|
| **Capture and ingestion** | | |
| FR1 | MUST | Store raw sources immutably and content-addressed, with stable IDs and span anchors. Re-ingesting the same source is idempotent |
| FR2 | MUST | Classify each item's true speaker before extraction: self-typed, self-pasted, assistant, tool, system-injected, or third party. [H] After filtering, self-typed text is under 10% of the characters in agent logs |
| FR3 | MUST | Segment sources into episodes. Give each a digest: aim, conclusions, what stayed open, what was rejected |
| FR4 | MUST | Emit candidates with kind, speaker, holder, stance and the supporting span. Assistant claims default to *encountered*. [H] False-endorsement rate of 5% or less, against roughly 40–55% for a naive extractor |
| FR5 | MUST | Scan deterministically for secrets and PII before any model call, and tag sensitivity. Seeded secrets: 0 leaks |
| FR6 | MUST | Keep imperatives from external or AI sources out of instruction space. Planted instructions: 0 persist |
| FR7 | SHOULD | Record free stance signals as evidence: abandoned branches, thumbs ratings, commits, reuse |
| FR8 | COULD | In-conversation capture at moments of commitment, recording only expectation and confidence. [H] Median 20 s or less; at least 70% accepted |
| **Knowledge layer** | | |
| FR9 | MUST | Record every change as a typed ledger event with its actor (the person, or a model@version plus a prompt hash), inputs and reason. Views rebuild without model access |
| FR10 | MUST | Support these typed changes: add, support, challenge, refine, supersede (update, correction or stance change), retract, merge and split (as reversible aliases), and link as tension. Excise is the only destructive operation |
| FR11 | MUST | Keep a proposition separate from the person's stance. Answer as-of queries in both belief time and record time, verified against a fixture of about 30 scenarios |
| FR12 | MUST | Represent open tensions, with their members and type. Never auto-resolve a stance conflict |
| FR13 | MUST | Make Questions and Decisions first-class. Decisions freeze their pre-outcome fields and carry a revisit date |
| FR14 | SHOULD | Count independent lineages. Flag support that comes only from AI, or only from the person's own echoes |
| FR15 | SHOULD | Propagate "upstream changed" review flags, never retractions. At most 3 load-bearing assumptions per decision. [H] At least 50% of flags worth reviewing |
| FR16 | SHOULD | Scopes: global, domain, project. Global is opt-in |
| FR17 | SHOULD | Predictions with resolution dates and Brier scoring |
| FR18 | COULD | Goals as a DAG; Principles linked to the cases they came from; restructuring proposals triggered by accumulated anomalies |
| **Human use** | | |
| FR19 | MUST | A review queue with a time budget, ranked by value of information, made of episode-level cards. Skipping makes no change. Unreviewed items stay usable, with a label |
| FR20 | MUST | Question pages showing position, evidence, open tensions and a timeline of stance changes. A "what changed my mind" feed built from revision events |
| FR21 | MUST | A "what the system thinks about me" view, with confirm, correct, forget and scope actions |
| FR22 | SHOULD | Show past beliefs as quoted, dated records, not narrative |
| FR23 | SHOULD | Generation-first prompts for items flagged "want to know". [H] |
| **AI use** | | |
| FR24 | MUST | A scoped, budgeted context pack: highest-ranked items only, kind and age labelled, hedges kept verbatim, a list of rejected options and things not to assume, all wrapped as data. [H] At least as correct as full preload, less over-personalised, using under 10% of the tokens |
| FR25 | MUST | Context receipts recording which item versions went to which AI session |
| FR26 | SHOULD | Search, get-by-ID and propose-update for clients that can call tools. Files and CLI first, MCP later |
| FR27 | COULD | A critique-mode pack: no beliefs or profile, open tensions instead |
| **Data rights** | | |
| FR28 | MUST | Excise across ledger, views, indexes, embeddings, caches and exports, leaving a tombstone. A grep for the excised content returns 0 hits |
| FR29 | MUST | A plain export bundle (Markdown with ordinary links, JSON, a README) readable without the app |

### Non-functional

| ID | Pri. | Requirement |
|---|---|---|
| NFR1 | MUST | Local-first. The person owns the data, and nothing depends on a single vendor |
| NFR2 | MUST | Total maintenance stays within the user's stated budget. [H] Stop line: 30 min a week |
| NFR3 | MUST | Model-agnostic. [H] Swapping the LLM changes probe scores by 5 points or less |
| NFR4 | MUST | Instrumented from day one: captures, integrations, review minutes, acceptance rate, edits after capture, active days |
| NFR5 | MUST | A small, versioned event vocabulary (`schema_v`), migrated by copy-and-transform |
| NFR6 | MUST NOT | Require the person to maintain a taxonomy or fill in required fields at capture |
| NFR7 | SHOULD | Full re-extraction is affordable: tens of dollars per pass over the archive [08] |
| NFR8 | SHOULD | Runs on a laptop at about 10⁶ events |
| NFR9 | SHOULD | The AI core pack is deterministic and cacheable, about 1.5–3k tokens [07] |

---

## 8. Riskiest assumptions and the cheapest experiments

E1–E4 decide *whether*, and how much, to build. E5–E10 refine the design. Each takes 1–3 days, except E4 and E9, which run for a week in the background.

| # | Assumption | Cheapest experiment | Kill or pivot signal |
|---|---|---|---|
| E1 | **Yield and coverage.** The user's real conversations and notes contain enough commitments worth keeping, and a small set of types covers them. Risky because self-typed text is about 2.5% of agent-log characters, and explicit endorsement about 1% [08] | Sample 30–50 conversations, stratified. An LLM drafts candidates; the user marks which are worth keeping and assigns kinds. Build takes a day, plus 4–8 hours of the user's time. Measure yield, the mix of kinds, and the share that cannot be expressed | Under about 1 commitment per 3 conversations: lean on deliberate capture, not ingestion. Over 15% inexpressible: revise the types |
| E2 | **Attribution.** Stance can be inferred well enough | On the E1 gold set, compare a naive "facts about the user" extractor with speaker-filtered, stance-aware extraction. Measure the false-endorsement rate and missed commitments | False endorsement stays above 15% after two prompt iterations: keep everything as *encountered* and require explicit confirmation before anything becomes a belief |
| E3 | **Margin over baselines.** Structure beats raw retrieval on the user's own questions | Write about 40 probes from real data *before building*: position and why, change of mind, open questions, decisions and rejected options, abstention, stale premise. Run B0 full context, B1 raw-chunk hybrid retrieval, B2 a grep-plus-semantic-search agent, B4 a dated observation log, and an oracle | If B2 or B4 already scores high, the structure must justify itself on the human-side jobs (J2, J3, J6), not on AI answers |
| E4 | **Review.** The user will do bounded review without rubber-stamping | Wizard-of-Oz for 7 days: each day, 10–20 episode cards as a Markdown file or in a CLI. Log minutes, completion, and accept, edit or reject | Median time over 2× the stated budget; acceptance above 95% with few edits; or 3 or more skipped days |
| E5 | **Question anchor.** Questions work as the primary anchor | The user writes 12–30 open questions (about 30 minutes). An LLM attaches 200 fragments from the backlog; the user verifies a sample | Under 40% attach: questions are a secondary anchor. Over 60%: they can be primary |
| E6 | **Conflicts.** LLM conflict detection is precise enough, and LLM merges produce synthetic blends | (a) An LLM proposes typed tensions; the user labels 50. (b) Merge 20 known-contradictory pairs and count the blends | Precision under 60%: change the granularity or prompt before building a review queue on it |
| E7 | **Drift.** Incremental rewriting drifts; regenerating from leaves does not | 10 consolidation cycles over a seeded corpus with planted rare details and hedges. Measure how many facts, rare details and hedges survive. Fully automatic | If both stay flat with current models, relax principle 7 and record why |
| E8 | **Value of history.** This user values a record of changes of mind | With LLM help, reconstruct "what I changed my mind about" over the past 6 months of chats. The user rates each item, and signature-tests 5 topic summaries | Fewer than 3 genuine changes, or low rated value: de-prioritise J2 |
| E9 | **Ownership and learning.** Integration the person authors beats reading an AI synthesis | n-of-1: 10 topics where the user predicts or explains first, 10 where they read a summary. One week later, the user explains each unaided; score blind | No gap: don't impose generation friction |
| E10 | **AI pack effect.** A compiled pack helps the assistant without raising sycophancy | Agreement rate on 30 contested prompts, with and without the belief pack. Re-proposal rate of rejected options, with and without rejected-option cards | Agreement rises, or re-proposals don't fall: redesign the pack |

**Order of work:**
1. E1 and E2 together (they share a gold set).
2. E3.
3. E4, running in the background.
4. E7, which is automatic.
5. E5, E6, E8 and E10.
6. E9.

Red-teaming for prompt injection (20 planted "remember that…" strings) is cheap enough to go straight into CI.

---

## 9. Evaluation approach

Track [09] lays out a strong base plan:
- Build the harness first.
- Keep a hidden structured world ledger that generates the transcripts.
- Score each memory operation separately.
- Script 18 scenarios.
- Stage the evaluation.
- Run ablations.
- Have the user take a weekly signature test.

The rest of this section sharpens that plan.

1. **Two questions, two instruments.**
   - *Is the write path correct?* Answer with synthetic personas and operation-level CI tests.
   - *Does it help this person, and will they keep using it?* Answer with an n-of-1 trial on real data.

   [09] puts the second at Stage 4. Run them in parallel instead, with a crude prototype in the user's hands from week 1. Abandonment is the dominant real-world failure and takes weeks to show up, and in one small study architecture rankings flipped between weeks 3 and 9 [03].
2. **A lean Stage 0.**
   - One persona of about 30 sessions.
   - The E3 real-data probes.
   - The baselines.
   - A meta-evaluation of the LLM judge: it must accept fewer than 10% of deliberately wrong answers.

   Defer the full five-persona, three-model-family pipeline until there is a design worth testing at scale. The harness must not become the hobby.
3. **Unified baselines** (the union of [03], [07] and [09]), all implemented by us at matched budgets:
   - B0: full context.
   - B1: raw-chunk hybrid retrieval.
   - B2: agentic grep plus semantic search over raw files.
   - B3: oracle evidence.
   - B4: an append-only dated observation log. This is the cheapest serious competitor and the one most likely to win.
4. **Decision rule.** The structured design must beat the best of B1, B2 and B4 by at least 10 points on update and belief-evolution metrics, at an 8K-token budget [03][09]. Otherwise the simpler design wins. Thresholds are fixed after Stage 0 and before Stage 2.
5. **Headline system metrics:**
   - stale-assertion rate;
   - missed-update and false-update rates, reported separately;
   - false-endorsement rate and attribution accuracy [08];
   - dissent and hedge retention after N consolidations;
   - citation precision and recall;
   - change in over-personalisation and sycophancy for the AI view [07];
   - over-retention: superseded or irrelevant items surfaced unprompted [09].
6. **Person metrics.** Combine [09]'s signature test with [01]'s learning measures.
   - Stop criteria:
     - fewer than 50% of summaries signable at week 4;
     - more than 30 minutes of maintenance per week;
     - two consecutive weeks of non-use.
   - Also track:
     - a log of surprising resurfaced items;
     - time to answer "what do I think about X?";
     - calibration on resolved predictions;
     - unaided explanation probes;
     - how accurately the user can name a belief's source *before* the system reveals its provenance [01].
   - Satisfaction and perceived usefulness are explicitly *not* success measures [01].
7. **Mitigating the builder-as-user bias.**
   - Write probes before the representation exists [07].
   - Let the system choose the signature-test topics.
   - Record ratings before looking at the system's internals.
   - Use separate model families for generating data, running the system, and judging [09].
8. **Ablate and cut.** Remove any component whose removal moves no metric. Apply this hardest to the expensive components: provenance, bitemporality, dependency links and the review gate [09].
9. **Portability and security.**
   - Export the data, rebuild a fresh instance, and swap the model. Scores must stay within 5 points.
   - A fresh reader with only the export must answer about 20 history questions [06].
   - CI runs injection, seeded-secret and wrong-context disclosure probes.

**Time horizon.** The n-of-1 trial runs at least 8 weeks, with checkpoints at weeks 3 and 8 [02][03][09].

---

## 10. Open questions for the user

1. **Sources.** Which of these do you actually produce in bulk, roughly how much, and can you export them? ChatGPT, Claude.ai, Claude Code, Codex, a notes app, Readwise/Kindle, email, meetings or voice, git.
2. **Jobs.** Rank J1–J9 (§1.4). Is this mainly for *you to think better*, for *your AI tools to know you*, or for *learning*? Each pulls the design a different way.
3. **Review appetite.** How many minutes per day or per week will you realistically give this? In what form: a daily ritual, a weekly session, or prompts inside conversations you are already having? The tracks disagree on this by about 10×.
4. **Writing appetite.** For your core topics, will you restate positions in your own words, or do you want AI drafts that you sign?
5. **Privacy.** May personal material go to cloud LLMs? Which categories must never leave the device (health, relationships, finances, other people's information)? Would you accept weaker local models for those?
6. **Work material.** Is material from your job in scope? Are there confidentiality rules about what can be stored, or sent to which providers?
7. **Your open questions.** Can you list the 12–30 questions or projects you are carrying now? E5 needs them, and they show your domains.
8. **Interface.** Do you already live in an editor (Obsidian, VS Code, Notion)? For the prototype, is a CLI plus generated Markdown pages acceptable, or must it live inside your AI chats?
9. **AI consumers.** Which AI tools must read this first? Can they call tools (Claude Code, Codex, MCP), or only accept pasted text? The answer decides whether we need one pack format or two.
10. **History and forgetting.** Are you comfortable with a permanent, timestamped record of your past beliefs? What should be truly deleted rather than hidden, and when?
11. **Decisions and predictions.** Do you want decision journaling with revisit dates, and calibration tracking? Track [05] rates these as the highest-payoff features, and they add capture prompts.
12. **Success at 3 months.** What outcome would make you say it worked? Examples: "I stopped re-explaining context to Claude", "I can see how my view on X evolved", "I repeat fewer mistakes".
13. **Evaluation time.** Will you spend 4–8 hours annotating a gold set of about 30 conversations, and run an 8-week self-trial with a 10-minute signature test each week?

---

## Appendix: index of research notes

| File | One-line summary |
|---|---|
| `01-human-memory-and-learning.md` | Understanding lives in the person and comes from effortful processing. Pair fast episodic capture with slow, selective integration, and never force coherence. The external system's value is where it beats the brain: provenance that doesn't decay, history that can't be rewritten, and counting independent sources. |
| `02-pkm-practice-and-failure.md` | Luhmann succeeded through integration at write time and sparse links. Organising in advance doesn't pay off, and most notes are write-only. Collecting is not learning, and upkeep kills systems. The AI should do the upkeep and the person the judgement, on top of plain files. |
| `03-ai-memory-systems.md` | Full context and files-plus-grep are the baselines to beat. Extraction and destructive updates cause most errors, and rewriting one summary as a block destroys information. The field models "facts about the user" and loses justification, the kind of statement, contradictions and changes of mind. |
| `04-epistemic-representation.md` | AGM belief revision supplies vocabulary but can't be the engine. Separate proposition, attribution and stance, and separate revision from update. Deprecate rather than delete, and link conflicts without resolving them. Questions form the spine. Count lineages, not citations. |
| `05-reasoning-decisions-goals-questions.md` | Formal rationale capture failed. A record's value comes from its pre-outcome timestamp, and AI-generated rationale is plausible rather than actual. Proposes a six-type, question-centred model. Calibration needs resolvable predictions, and the payoff lies in review. |
| `06-time-history-and-consolidation.md` | Two clocks plus a separate record of stance. Three tiers of mutability. LLM outputs are recorded events, not projections. Use typed supersession, and IDs that name meanings. Deletion must reach every derived store. Prefer SQLite to Markdown for archiving. |
| `07-human-vs-ai-consumers.md` | Context rot and sycophancy make "more memory" harmful. Use a core pack, an index and just-in-time retrieval, and mark authorship and obligation explicitly. Visible memory beats opaque memory. One canonical store with separate projections, and a locked-down write path. |
| `08-ingestion-and-extraction.md` | `role=user` is not the user, and what the human wrote is not necessarily what they believe. Production systems absorb about half of assistant-introduced distractors, and omission dominates fabrication. Use the episode as the unit and record speaker, holder and stance. Extract in batch, review on a time budget, and scan for secrets deterministically. |
| `09-evaluation-and-failure-modes.md` | Benchmarks test recall, not understanding, and LoCoMo is broken. Updates fail by omission. Build the harness and baselines first, with a hidden world ledger and 18 scenarios, a staged plan and an n-of-1 signature test. Abandonment is the dominant failure, and nothing measures it. |
