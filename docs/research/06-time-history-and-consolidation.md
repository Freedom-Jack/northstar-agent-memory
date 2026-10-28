# Time, History, Provenance, and Consolidation Mechanics

Research track 06. Written 2026-10-07. I used web search and fetch to check the specific claims, numbers, and dates in this note. The shared search budget ran out partway through, so a few background claims come from prior knowledge. Those are marked "(not re-verified here)" where it matters.

---

## Scope and questions

This track covers how a personal knowledge store changes over time without losing useful history, and how fragments get consolidated. The structure tracks decide *what kinds* of things the store holds. This track decides how any of them are timestamped, versioned, superseded, merged, summarized, attributed, synced, deleted, and kept readable for decades.

Questions this note tries to answer:

1. **What must be immutable, and what can be derived?** Which layer is the source of truth, and which layers can be thrown away and rebuilt?
2. **How can consolidation stay reversible and auditable?** Consolidation means merging, abstracting, and reorganizing.
3. **How do you version meaning, not just text?** A wording edit and a change of mind are different events. A diff tool cannot tell them apart.
4. **"What did I believe, and when?"** What temporal model does this question actually need?
5. **What survives 10 or more years?** This covers formats, schemas, identifiers, and model-dependent artifacts.

---

## Key findings

### 1. "What did I believe when" needs at least two clocks, plus a separate record of the person's own stance

**Mechanism.** Bitemporal modeling separates two times. **Valid time** is when a fact holds in the world. **Transaction time** is when the system recorded or stopped asserting it. Snodgrass formalized this, and SQL:2011 standardized it as application-time periods plus system-versioned tables. Martin Fowler calls the two axes "actual history" and "record history." His example is a payroll system that learns on 15 March about a pay-rate change that took effect on 15 February. Without both axes you cannot say what the payroll run on 25 February *should* have paid, or what it *did* pay given what was known then.

A personal system needs a third distinction. A proposition ("X is true") is different from the person's stance toward it ("I held X, at confidence c, from t1 to t2"). The stance is itself a fact about the person, so it has its own valid time. When the system captured that stance is a different time again. Capture time only bounds belief time from above. Someone may have believed X for years before mentioning it.

**Evidence.** XTDB 2.0 reached general availability on 12 June 2025. It makes *every* table bitemporal and follows SQL:2011 semantics. Zep's Graphiti engine (arXiv 2501.13956, January 2025) brought the same idea to agent memory. Each edge carries four timestamps: `t_valid` and `t_invalid` for the world, and `t_created` and `t_expired` for the system. When a contradiction arrives, the engine sets an invalidation time instead of deleting the edge. XTDB's James Henderson adapts Greenspun's rule: any sufficiently complicated schema contains an ad hoc, half-finished bitemporal database. He also admits that "most people don't need most of the power of bitemporality."

**Implication.** Build the two clocks in from day one. Four timestamp columns cost almost nothing. Adding them later means rewriting history you have already flattened.

### 2. Retraction is not deletion, and real deletion in an immutable system is hard

**Mechanism.** Datomic and XTDB never overwrite. A "delete" is a retraction: a new fact saying the old fact stopped being asserted at time T. As-of queries can still see the old fact. That serves auditing well, but it conflicts with privacy, and with a person simply wanting something gone. Both systems therefore have a separate operation for physical removal. Datomic calls it *excision* and XTDB calls it `ERASE`.

**Evidence.** Datomic's excision documentation describes it as complete removal of matching datoms. Its stated uses are privacy and retention limits, as opposed to retraction, which corrects errors while keeping history. On 23 October 2025 Datomic shipped a "critical release" (1.0.7469). It fixed a bug where "excisions may not be completely applied to as-of or history database values." Even a mature immutable database missed a derived index. Deletion has to reach *every* one of them, and they multiply. Practitioners also name data privacy as a top event-sourcing challenge (Overeem et al., finding 3).

**Implication.** The design needs three distinct verbs. *Supersede* keeps history. *Retract* says "I no longer assert this" and keeps a record. *Excise* removes content physically, everywhere, leaving only a tombstone. Excision has to propagate through every projection, including search indexes, embeddings, caches, and logs of what was sent to AI tools, and it needs tests.

### 3. Event sourcing's "replay the log to rebuild" promise assumes deterministic projections, and LLM consolidation breaks that

**Mechanism.** Event sourcing and CQRS keep an immutable log of events. Every read model is a *projection* that can be rebuilt by replaying the log. That works only if the projection is a pure function of the log and the code. An LLM-based consolidation fails that condition. It is non-deterministic, depends on the model and the prompt, and the model may be retired. Regenerating a summary of 300 notes with a 2031 model will not give back the 2026 summary that the person read and acted on.

**Evidence.** Overeem et al. interviewed 25 engineers about 19 event-sourced systems (Journal of Systems and Software, 2021). They found five challenges: event system evolution, a steep learning curve, missing technology, *rebuilding projections*, and data privacy. They also found five evolution tactics: versioned events, weak schema, upcasting, in-place transformation, and copy-and-transform. Greg Young's *Versioning in an Event Sourced System* covers the same tactics. Standard event-sourcing advice already warns against calling non-deterministic external services during replay, and an LLM consolidation step *is* such a call.

**Implication.** Treat LLM outputs as *decisions recorded in the log*, not as projections. A consolidation run is an event whose payload is its output text, along with the inputs it used, the model, and a hash of the prompt. Replay reads that recorded output and does not call the model again. Only deterministic views (indexes, full-text search, graph adjacency, rendered pages) count as disposable projections.

### 4. Current AI memory systems default to destructive updates, and benchmarks show they handle conflicts badly

**Mechanism.** In Mem0, the most widely copied pattern, an LLM chooses ADD, UPDATE, DELETE, or NOOP for each incoming fact. On contradiction the newer fact wins and the old one is deleted. That erases history, treats "the world changed" and "I was wrong" as the same thing, and hands an irreversible decision to a single LLM call.

**Evidence.** MemoryAgentBench (Hu, Wang, McAuley; ICLR 2026) tests "selective forgetting" with a FactConsolidation dataset. The authors report that "all methods fail on the multi-hop situation (with achieving at most 7% accuracy)." o4-mini dropped from 80% on 6K-token contexts to 14% on 32K. A June 2026 single-author preprint ("Control-Plane Placement Shapes Forgetting," arXiv 2606.15903) argues that "production failures are predominantly forgetting failures rather than recall failures, yet existing benchmarks measure only recall." Treat that as a preprint claim. The 2026 direction moves away from overwriting. ROAM (arXiv 2609.09778, September 2026) classifies each new and stored pair of memories as independent, equivalent, subsuming, or conflicting. It keeps the losing memories as "Evidence" behind a "Primary" view and reports up to 29.8 points better answer accuracy. Graphiti's invalidation-with-timestamps (finding 1) points the same way.

**Implication.** The prevailing "memory = CRUD over facts" model is the wrong default for a long-term personal system. Contradictions are information. Track them as typed relations, not overwrites.

### 5. Iterated summarization drifts toward attractors and loses the tails; keeping the originals bounds the damage

**Mechanism.** Each summarization step is a lossy, biased transformation. Applying it repeatedly compounds the bias, and the output converges on the model's defaults (an "attractor") instead of on the source. Rare, idiosyncratic details are the first to go. In a *personal* knowledge base those are often the most valuable content: unusual hunches, minority positions, specific numbers.

**Evidence.** Perez et al., "When LLMs Play the Telephone Game" (arXiv 2407.04503, revised January 2026), ran transmission chains of LLM agents. Text properties drifted toward attractors. More open-ended instructions produced stronger attraction than constrained tasks. Shumailov et al. (Nature 631, 2024) showed that when generated data *replaces* the original data across generations, the "tails of the original content distribution disappear." Gerstgrasser et al. (ICML 2024) showed that *accumulating* the originals alongside the generated data gives a test error with a finite upper bound, independent of the number of iterations.

**Caveat.** Those two papers are about training data, not summary chains, so this is an analogy. Still, the mechanism carries over cleanly. Replacing sources with summaries compounds error. Keeping sources and regenerating from them does not.

**Implication.** Never build a summary from summaries without the leaves. Every synthesis should be regenerable from source-anchored claims. Use constrained, extractive consolidation prompts, not "summarize your understanding."

### 6. Corrections do not reach dependents unless something carries them there

**Mechanism.** When a claim is retracted, everything derived from it is now suspect. Unless dependency links exist and someone traverses them, the derived material keeps circulating as if nothing happened.

**Evidence.** Hsiao and Schneider (Quantitative Science Studies, 2021) examined 13,252 post-retraction citation contexts in biomedicine. Only 722 (5.4%) acknowledged the retraction. Science's institutional fix is Crossref Crossmark. Its 12 typed update kinds (for example correction, erratum, expression of concern, partial retraction, retraction, withdrawal, new version) are registered as linked records, so any copy can check its current status. The Gene Ontology never deletes a term. It marks the term obsolete and adds either `replaced_by` (safe to migrate automatically) or `consider` (a human must choose). Even careful research needs supersession links. Kleppmann et al.'s 2019 interleaving-anomalies paper (finding 10) now carries an erratum that points to the later Fugue paper.

**Implication.** Every derived artifact needs explicit `derived_from` links. Superseding a claim should flag everything downstream as "upstream changed," the way a Crossmark status does. Supersession types should separate automatic from human-reviewed migration, the way GO separates `replaced_by` from `consider`.

### 7. Circular reporting: once the AI writes into the store and later reads from it, it can confirm itself

**Mechanism.** In *citogenesis* (a term from a 2011 xkcd comic), an unsourced Wikipedia claim is repeated by a "reliable" outlet, which is then cited back as proof. The general failure is circular reporting: one origin looks like several independent sources. A personal AI memory is built to produce exactly this loop. An AI infers "you prefer X," writes it down, retrieves it next month as "known," and repeats it in three summaries. Now X has four "sources," and all of them are the same inference.

**Evidence.** The Wikipedia article on circular reporting describes the pattern. W3C PROV defines `hadPrimarySource` and separates `wasQuotedFrom` from `wasDerivedFrom`, which is exactly what an independence check needs.

**Implication.** Count support by *distinct primary sources*, never by the number of derived mentions. AI-inferred content must never count as evidence for itself, or for its own inputs.

### 8. Versioning meaning is mostly a problem of identity, and text tools have none

**Mechanism.** Git is a content-addressed Merkle DAG. It is excellent for integrity, deduplication, and syncing bytes. It stores *no identity* for a file across renames, though. Renames are guessed after the fact by content similarity (default threshold 50%). Its diffs and merge conflicts work on lines, not meaning. A reworded belief and a reversed belief can produce the same diff size. A concept that moves between files loses its lineage.

The ontology community solved this decades ago, without any tooling magic. **The identifier names the meaning, not the text.** OBO Foundry Principle 19 ("Stability of Term Meaning") says that if a change would "substantially change its referents," a "new term with new IRI and definition MUST instead be created" and the old one obsoleted. Rewording that leaves the referent alone keeps the ID.

**Evidence on merges.** Wikidata merges items by moving statements and turning one item into a redirect. Undoing that is manual work, because links added after the merge now point at the combined item and someone has to reassign them. Author-name-disambiguation research shows that merge errors and split errors cost different things. Merging distorts relational analyses badly, while splitting mostly hurts counting. Simple initial-based heuristics achieved low splitting error (1.17% to 3.52%) but merging error of 17.98% to 29.30%. These figures come from Jinseok Kim and colleagues' work on initial-based disambiguation of coauthorship data; I did not re-verify which exact paper reports them.

**Implication.** Mint stable IDs for ideas. A wording edit keeps the ID. A change of referent mints a new ID and adds a supersedes link. Model merges as reversible alias assertions, not physical merges. When unsure, prefer leaving things unmerged.

### 9. Wikipedia and Wikidata separate the current synthesis, the full history, and the deliberation, and that separation is what makes consolidation work

**Mechanism.** A Wikipedia article is the current consolidated synthesis. The revision history is complete and immutable, so any version can be viewed or reverted. The *talk page* holds the reasoning, the disputes, and the open questions. They are kept out of the article but stay attached to it.

Wikidata adds **statement ranks**. *Preferred* marks current or consensus values, *normal* is the default, and *deprecated* marks known errors or outdated values. Deprecated statements are kept but never returned by default queries. Wikidata also has *qualifiers* such as start time (P580), end time (P582), and point in time (P585), which give valid time per statement.

As far as I know, Wikidata's *transaction* history lives only in page revisions and cannot be queried through SPARQL. This project should avoid that gap.

**Evidence.** Kittur and Kraut (CSCW 2008) found that adding editors improves article quality only when coordination is adequate. Explicit coordination on talk pages helps less as the number of editors grows, while concentrated, implicit coordination keeps working.

**Implication.** For one person working with several AI writers, the useful pattern is a current synthesis, plus immutable revisions, plus an attached deliberation log of open contradictions, rationale, and what was dropped and why. The AI writers have to coordinate through that structure, not through overwrites.

### 10. For multi-device and multi-agent sync, an append-only log merges trivially; CRDTs guarantee convergence, not sense

**Mechanism.** Local-first software is defined by seven ideals (Kleppmann, Wiggins, van Hardenberg, McGranaghan; Onward! 2019): fast, multi-device, offline, collaboration, longevity, privacy, and user control. Longevity and user control matter most here. CRDTs guarantee that replicas *converge*. They do not guarantee that the converged result is *meaningful*: in several published text algorithms, concurrent inserts interleave into nonsense (Kleppmann et al., PaPoC 2019). An append-only set of uniquely identified events is the simplest CRDT there is, a grow-only set, so merging two devices' logs is just set union. Conflicts then show up where they belong, at the *semantic* layer. Two concurrent supersessions of the same claim are a fork to surface, not text to splice together.

**Evidence.** Automerge 3.0 (July 2025) cut memory by more than 10x. Its example: Moby Dick pasted into a document used 700 MB in Automerge 2 and 1.3 MB in Automerge 3, and one load time went from 17 hours to 9 seconds. Full-history CRDTs have only recently become affordable. Ink & Switch's Patchwork project (2024 to 2026) is still researching "universal version control" that non-programmers can use, so that remains unsolved.

**Implication.** The real concurrency here is not a person on two laptops. It is Claude, ChatGPT, Codex, and the person all writing at once. A shared append-only ledger with semantic fork detection handles that with no CRDT library. A text CRDT for collaboratively editing the synthesis pages can wait.

### 11. Long-term formats: the evidence favors SQLite more than folk wisdom does, and Markdown less

**Mechanism.** Formats survive when they are openly documented, widely adopted, readable with basic tools, self-describing, and free of external dependencies. These are the Library of Congress sustainability factors.

**Evidence.** The LoC Recommended Formats Statement lists SQLite (`.db`, `.sqlite`, and so on) as a *preferred* dataset format alongside CSV/TSV and XML. JSON appears as *acceptable* (page fetched October 2026). For textual works, LoC prefers XML-with-schema, EPUB3, and PDF/A. Plain text is only "acceptable" and **Markdown is not listed at all.**

That contradicts the popular "Markdown is the archival format" belief, with one nuance. LoC is judging fidelity for published works, not personal notes. Markdown's real risk is *dialect lock-in*. Wiki-links, block references, embeds, and front-matter conventions mean nothing outside the app that defined them, so the *structure* lives in app conventions, not in the file format.

One more artifact is not archival at all: **embeddings.** They are tied to a specific model and become meaningless once that model is gone.

**Implication.** Store the canonical data in SQLite with the schema documented *inside* it. Keep an append-only JSONL ledger that is line-oriented and greppable. Periodically export a human-readable bundle (plain Markdown with ordinary links, JSON, and a README describing the schema). Treat embeddings as disposable caches.

---

## Ideas worth stealing

1. **Four timestamps per assertion** (`valid_from`, `valid_to`, `recorded_at`, `retracted_at`). *From:* Snodgrass and SQL:2011; Graphiti's `t_valid`, `t_invalid`, `t_created`, and `t_expired`; XTDB v2.
2. **Stance as a separate, timed record.** Keep `proposition` and `stance(holder, attitude, confidence, valid_from, valid_to)` apart. "I believed X in 2023" and "X was true in 2023" become different queries. *From:* bitemporal valid time applied to belief.
3. **Typed supersession that maps onto the time axes.** *From:* Crossmark update types and GO obsoletion. The type tells you what the change *means*:

| Change type | What it means | Effect on the old version |
|---|---|---|
| `update` (world changed) | Was true, no longer is | Close its `valid_to`; still true historically |
| `correction` | Was never true | Close its transaction time; rank becomes *deprecated* with a reason |
| `refinement` | Compatible but more precise | Superseded; still entailed |
| `reinterpretation` | Same evidence, new framing | Mint a new ID if the referent changed (OBO P19) |
| `retraction` | Withdrawn, nothing replaces it | Deprecated |
| `stance_change` | I changed my mind | Close the *stance* record's `valid_to`; the proposition is untouched |
| `merge` / `split` | Identity judgment | Alias assertion added or retracted; no data moves |

4. **`replaced_by` vs `consider`.** Auto-migrate dependents when the replacement is unambiguous. Queue them for human review when it is not. *From:* Gene Ontology.
5. **IDs name meanings.** Rewording keeps the ID; a change of referent mints a new one. *From:* OBO Foundry Principle 19.
6. **Ranks with default filtering** (preferred, normal, deprecated with a reason). Default retrieval for AI context skips deprecated items. History queries include them. *From:* Wikidata.
7. **Article + revisions + talk page.** Every synthesis page has immutable revisions and an attached deliberation log of open contradictions, consolidation rationale, and what was dropped. *From:* Wikipedia.
8. **Evidence cutoff on every synthesis.** Each synthesis records "built from inputs up to T, using input set S." Staleness is defined as relevant inputs arriving after T. *From:* systematic and living reviews in science, which state a search date (not re-verified here).
9. **Status lookup that follows dependencies.** Superseding or retracting a node sets "upstream changed" on everything derived from it. *From:* Crossmark.
10. **PROV vocabulary, not PROV serialization.** Model each consolidation as an *Activity* with an *Agent* (`user`, or `model@version` plus a prompt hash), `used` inputs, and `generated` outputs. Use `hadPrimarySource` to count independence, and *Bundles* for the provenance of whole consolidation runs. *From:* W3C PROV-DM (2013).
11. **Excision with a tombstone.** Remove the content physically and keep a hash and reason, so references fail visibly instead of silently. *From:* Datomic excision and XTDB `ERASE`.
12. **Merge as a reversible alias.** Both IDs persist and a `same_as` assertion carries confidence and provenance. Each link records its *intended* referent at creation time, so unmerging reassigns links automatically. *From:* the pain of Wikidata redirects and unmerges, inverted.
13. **The ledger as a grow-only set.** Use globally unique event IDs (ULIDs or similar) and sync by set union. Concurrent supersessions of one node become a visible fork. *From:* CRDT theory and the local-first ideals.
14. **Primary vs evidence roles.** Superseded or redundant items stay as *evidence* behind one *primary* view, so they don't compete during retrieval. *From:* ROAM (2026).
15. **Weak-schema events plus copy-and-transform.** Use tolerant JSON events with a `schema_v` field. When the vocabulary has to change, write a new ledger from the old one and archive the original, rather than accumulating upcaster chains. *From:* Greg Young; Overeem et al.
16. **Content-addressed sources.** Hash raw captures for deduplication, integrity, and stable citation anchors (source hash plus span). *From:* git's object model, used only for that.
17. **Context receipts.** Log which node versions were served to which AI session. You can later answer "what did the assistant know when it told me Y," and you know what to recall when something is retracted. *From:* combining PROV `used` with as-of queries; I have not seen this done elsewhere.

---

## Pitfalls and anti-patterns

Items 1 to 5 and 9 to 11 expand on the findings above, so they are kept short.

1. **LLM-routed DELETE on contradiction (Mem0).** The least reliable component (at most 7% on multi-hop FactConsolidation) makes an irreversible decision and conflates "changed" with "wrong."
2. **Treating LLM output as a rebuildable projection.** Replay silently produces knowledge that differs from what the person saw. Model deprecation makes the original unrecoverable.
3. **Incrementally rewriting one living summary.** "Update the summary with today's notes" is a one-player telephone game. Because the originals are no longer consulted, nobody notices the drift.
4. **Counting derived mentions as support.** This is citogenesis inside a single system, and it is worst for AI-inferred traits about the user.
5. **Premature or physical merging.** Unmerging after new links have been added is manual forensics, as on Wikidata.
6. **Using git as the semantic history model.** Line diffs, rename heuristics, syntactic conflicts, and history-rewriting commands (rebase, force-push) all fail here. Git is fine as *transport and backup* for exported files.
7. **A rigid upfront ontology.** A person's categories at 30 will not match their categories at 45. Types baked into paths or table names make re-typing a migration. Types stored as assertions make it one more event.
8. **Upcaster chains that grow forever.** After ten years of schema changes, every replay runs a stack of transformations that no one fully understands.
9. **Deletion that only reaches the main table.** Embeddings, indexes, caches, exports, and prompts already sent to third-party AI providers are all derived stores. The last one cannot be recalled, only recorded. Datomic's 2025 bug is the cautionary example.
10. **Embeddings or app-dialect Markdown as the archival layer.** Vectors die with their model. Block references die with their app.
11. **Treating capture time as belief time.** "First mentioned" is only a bound, and retrospective reconstruction of beliefs suffers from hindsight bias (Fischhoff, 1975; not re-verified here). The system's unique value is *contemporaneous* capture, so it must keep the original wording verbatim, not only a normalized claim.

---

## Implications for this project

Each item is phrased so the prototype can confirm or refute it.

1. **Use three tiers of mutability.**
   - **Sources** are immutable, content-addressed, and excisable.
   - **Ledger** is an append-only log of typed events covering every assertion, stance, link, supersession, merge, and consolidation output.
   - **Views** are disposable and deterministic.

   *Test:* delete every view and rebuild from the ledger. Deterministic views should come back hash-identical, with no network or LLM access during the rebuild.
2. **LLM outputs live in the ledger.** Store the consolidation text, input IDs, model ID, and prompt hash as an event payload. *Test:* replaying with all model access disabled reproduces every synthesis page byte-for-byte.
3. **Use four timestamps plus typed supersession,** following the table in "Ideas worth stealing." *Test:* write a scenario fixture of about 30 dated events, covering a world change, a correction, a stance change, and retroactive capture. Then check that `as_of(valid=D1, tx=D2)` queries return the expected answers. The suite should separate "I was wrong" from "it changed" from "I changed my mind."
4. **Keep proposition and stance separate.** "What did I believe in March 2027" queries stance valid time. "What did the system think I believed on March 2027" queries transaction time. *Test:* both are answerable, and they differ when a belief was captured retroactively.
5. **Use stable meaning IDs under OBO Principle 19.** The AI may *propose* "this looks like a change of referent, mint a new ID?" The default is to keep the ID. *Test:* across a 3-month dogfooding period, count the follow-up corrections needed after each suggestion. Fewer than 10% of mint or keep decisions should need reversal.
6. **Make merges non-destructive aliases** and record each link's intended referent. *Test:* merge A and B, add 5 links to the merged entity, then split. Every original link and every post-merge link should resolve to the intended referent with no manual work.
7. **Do not summarize summaries without the leaves.** Every synthesis cites source-anchored claims (source hash plus span) and is regenerated from them, not incrementally edited. *Experiment (high priority):*
   - Run 10 consolidation cycles over a seeded corpus that has planted rare details.
   - Compare "incremental rewrite of the previous summary" against "regenerate from leaves."
   - Measure (a) the fact-preservation rate against the sources and (b) the rare-detail retention rate.

   *Hypothesis:* incremental rewriting degrades monotonically over the cycles, while regenerating from leaves stays roughly flat. If both stay flat with current models, relax the rule and record that.
8. **Track provenance agent classes:** `user_asserted`, `user_confirmed`, `ai_inferred`, `external_source`, and `ai_conversation_claim`. AI-inferred items never become user-asserted without an explicit confirmation event. Support counts only distinct primary sources. *Test:* re-ingest an AI-generated synthesis. No claim's support count should go up.
9. **Propagate staleness downstream.** Superseding or retracting a node marks every transitive dependent "upstream changed." *Test:* 100% of dependent syntheses are flagged within one rebuild cycle. This is the counter-example to science's 5.4%.
10. **Make excision first-class and tested.** It reaches the ledger payload, views, full-text index, embeddings, caches, and exports, and leaves a tombstone of hash, reason, and time. *Test:* after excising a planted secret, grep the whole data directory plus a rebuilt export and get zero hits.
11. **Log context receipts.** Record which node IDs and versions went to each AI session. *Test:* given a past AI answer, the system can list the knowledge versions it saw, and after a later retraction it can list the sessions that were exposed.
12. **Storage:** SQLite as the canonical store with a `schema_doc` table; JSONL ledger mirror; a periodic plain export (CommonMark with ordinary relative links, JSON, and a README). Embeddings are caches only. *Longevity test:* give a fresh model or person *only* the export and README, and they answer about 20 history questions correctly ("when did my view on X change, and why").
13. **Sync:** merge the ledger by set union and surface semantic forks for review. Add a text CRDT only if dogfooding shows real concurrent page edits.
14. **Retrieval defaults to ranked views:** preferred, then normal; deprecated items appear only in history queries. *Test:* the AI context builder never emits a deprecated item unless asked for history.
15. **Scale sanity check.** Fifty events a day for 20 years is about 365,000 events. Even 50,000 words a day of raw conversation is roughly 2 GB of text over 20 years. Storage is not the constraint, so "forgetting" should mean *lower retrieval salience*, not deletion. Excision is reserved for privacy or explicit user intent.

---

## Tensions and open questions

1. **What is the immutable unit?** Raw sources are unambiguous but coarse. Extracted "atomic claims" are useful, but extraction is already an interpretive, lossy LLM step. My position is that sources are the only truly immutable layer and claims are versioned interpretations of them. That doubles the storage model. Is the cost worth it?
2. **How much review burden is acceptable?** Fork review, `consider` queues, merge confirmations, and P19 prompts all cost attention. Set a budget (perhaps about 10 items a week), rank review by risk, and auto-apply the rest reversibly. Measure the right number in dogfooding.
3. **Who decides that meaning changed?** P19 assumes curators who agree on referents. For a single person, meaning is partly in their head. Can the AI's "the referent shifted" suggestions be trusted? If not, an ID-per-meaning scheme collapses into ID-per-text.
4. **Should consolidation be auto-applied and reversible, or proposed and confirmed?** Wikipedia works because edits are cheap to revert *and* someone is watching. With no watcher, auto-applied consolidation can drift unnoticed.
5. **How do event schemas evolve over 10 years?** How small can the event vocabulary be (about a dozen verbs?) while still capturing meaning? Should the ledger be rewritten with copy-and-transform every few years, or kept as one log with upcasters?
6. **Should contradictions be resolved or kept?** Some contradictions are errors. Others are productive tensions the person deliberately holds. The data model must represent "unresolved, intentionally" so consolidation does not "fix" it.
7. **Deletion versus the AI ecosystem.** Once context has been sent to an external model provider, excision is local only. Is a context receipt a sufficient mitigation, or should sensitive tiers never leave the device?
8. **Bitemporal on every row, or only on claims?** Structural edits (re-parenting, re-clustering) may only need transaction time.
9. **Should synthesis pages have stable identity?** A page ID that persists across regenerations mirrors Wikipedia, but it lets a page's topic drift silently.
10. **Can drift be measured continuously?** The experiment in implication 7 runs offline. Could spot-verifying N random synthesis sentences against their anchors on each rebuild serve as an ongoing integrity alarm?

### Challenges to the framing

- **"Without destroying useful history" is not the main risk; burying it is.** Storage is cheap, and append-only is easy. The hard parts are history that is never consulted, defaults that surface stale items, and "what changed and why" being impossible to ask. Design the queries over history, not only its retention.
- **"Evolving knowledge" mixes four different kinds of change:** the world changes; the person's understanding changes; the system's *representation* changes (schema, ontology, IDs); and the *machinery* changes (models get replaced). Each needs its own mechanism: valid time; stance records; P19 identity and obsoletion; recorded LLM outputs and disposable embeddings. One "version" field cannot carry all four.
- **Fragments are not inherently bad.** Premature consolidation destroys optionality and minority ideas, which are the tails that recursive summarization erases first. Some fragments should stay unconsolidated on purpose.
- **Immutability is a means, not a value.** A personal system needs real, propagating deletion from day one, for privacy, for third parties mentioned in notes, and for regret.
- **"Version meaning, not text" is only partly achievable.** The system can version propositions, stances, identities, and relations, and make meaning change an *explicit act*. It cannot detect meaning change by itself with any reliability.

---

## Sources

- Snodgrass, R. T., *Developing Time-Oriented Database Applications in SQL*, Morgan Kaufmann, 2000. https://shop.elsevier.com/books/developing-time-oriented-database-applications-in-sql/snodgrass/978-0-08-050422-3 ; https://www2.cs.arizona.edu/~rts/sql3.html
- Fowler, M., "Bitemporal History," 7 April 2021. https://martinfowler.com/articles/bitemporal-history.html
- XTDB, "Launching XTDB v2" (GA 12 June 2025). https://www.xtdb.com/blog/launching-xtdb-v2 ; "Time in XTDB": https://docs.xtdb.com/about/time-in-xtdb.html
- Henderson, J., "But bitemporality always introduces complexity," XTDB blog, 8 August 2023. https://xtdb.com/blog/but-bitemporality-always-introduces-complexity
- Datomic, Excision docs. https://docs.datomic.com/operation/excision.html ; time filters: https://docs.datomic.com/pro/time/filters.html ; "Critical Release Datomic 1.0.7469 Pro" (23 October 2025): https://forum.datomic.com/t/critical-release-datomic-1-0-7469-pro-now-available/2598
- Rasmussen, P. et al., "Zep: A Temporal Knowledge Graph Architecture for Agent Memory," arXiv 2501.13956, January 2025. https://arxiv.org/abs/2501.13956 ; Graphiti: https://pypi.org/project/graphiti-core
- Overeem, M., Spoor, M., Jansen, S., Brinkkemper, S., "An empirical characterization of event sourced systems and their schema evolution — Lessons from industry," Journal of Systems and Software, 2021. https://arxiv.org/abs/2104.01146
- Young, G., *Versioning in an Event Sourced System*, Leanpub. https://leanpub.com/esversioning
- Mem0 memory operations (ADD, UPDATE, DELETE, NOOP), described in Mem0 docs and blog. https://mem0.ai/blog/programmatic-memory-management-for-ai-agents-with-mem0
- Hu, Y., Wang, Y., McAuley, J., "Evaluating Memory in LLM Agents via Incremental Multi-Turn Interactions" (MemoryAgentBench), arXiv 2507.05257, ICLR 2026. https://arxiv.org/abs/2507.05257
- Yang, D., "Control-Plane Placement Shapes Forgetting: An Architectural Study of Agent Memory Across Thirteen System Configurations," arXiv 2606.15903, June 2026 (preprint). https://arxiv.org/abs/2606.15903
- Zheng, J. et al., "ROAM: Robust Organization of Atomic Memories for Agents through Semantic Relations," arXiv 2609.09778, September 2026 (preprint). https://arxiv.org/abs/2609.09778
- Ye, C. et al., "Auto-Dreamer: Learning Offline Memory Consolidation for Language Agents," arXiv 2605.20616, May 2026 (consulted as context; not cited for a specific claim above). https://arxiv.org/abs/2605.20616
- Letta, "Sleep-time compute" (asynchronous memory consolidation agent; consulted as context). https://letta.com/blog/sleep-time-compute
- Perez, J. et al., "When LLMs Play the Telephone Game: Cumulative Changes and Attractors in Iterated Cultural Transmissions," arXiv 2407.04503 (v3, January 2026). https://arxiv.org/abs/2407.04503
- Shumailov, I. et al., "AI models collapse when trained on recursively generated data," Nature 631, 755–759 (2024). https://www.nature.com/articles/s41586-024-07566-y
- Gerstgrasser, M. et al., "Is Model Collapse Inevitable? Breaking the Curse of Recursion by Accumulating Real and Synthetic Data," ICML 2024, arXiv 2404.01413. https://arxiv.org/abs/2404.01413
- Hsiao, T.-K., Schneider, J., "Continued use of retracted papers: Temporal trends in citations and (lack of) awareness of retractions shown in citation contexts in biomedicine," Quantitative Science Studies, 2021. https://pmc.ncbi.nlm.nih.gov/articles/PMC9520488/
- Crossref Crossmark update types (summarized via publisher policy pages and the CASRAI dictionary). https://www.casrai.org/dictionary/term/crossmark
- Gene Ontology, obsoleting terms (`replaced_by`, `consider`). https://go-ontology.readthedocs.io/en/latest/ObsoleteTerm.html
- OBO Foundry Principle 19, "Stability of Term Meaning." https://obofoundry.org/principles/fp-019-term-stability.html
- W3C, "PROV-DM: The PROV Data Model," W3C Recommendation, 30 April 2013. https://www.w3.org/TR/prov-dm/
- Wikidata statement ranks and temporal qualifiers. https://www.wikidata.org/wiki/Property:P582 ; rank semantics as described in Wikibase RDF materials: https://courses.cs.umbc.edu/graduate/691/fall22/kg/notes/24_wikidata/wikibase.pdf ; merge and unmerge discussion: https://phabricator.wikimedia.org/T237262
- Kittur, A., Kraut, R., "Harnessing the wisdom of crowds in Wikipedia: quality through coordination," CSCW 2008 (finding summarized via secondary sources; not re-fetched). https://acawiki.org/Cooperation_and_Quality_in_Wikipedia
- Wikipedia, "Circular reporting" (citogenesis; xkcd, November 2011). https://en.wikipedia.org/wiki/Circular_reporting
- Kim, J. and colleagues, author-name-disambiguation merging vs splitting errors. Related work includes "Evaluating author name disambiguation for digital libraries: A case of DBLP," arXiv 1806.10540 (https://arxiv.org/abs/1806.10540) and the Bayesian merging-error model at arXiv 1711.01406 (https://arxiv.org/abs/1711.01406). The exact source of the 17.98% to 29.30% figure was not re-verified.
- Git rename detection (similarity index, default 50%), via JGit implementation notes and git diff documentation. https://gerrit.googlesource.com/jgit/+/978535b09080edcc01302e80b37b9e1263c21db3
- Kleppmann, M., Wiggins, A., van Hardenberg, P., McGranaghan, M., "Local-first software: You own your data, in spite of the cloud," Onward! 2019. https://www.inkandswitch.com/local-first/
- Kleppmann, M. et al., "Interleaving anomalies in collaborative text editors," PaPoC 2019 (with later errata). https://martin.kleppmann.com/2019/03/25/papoc-interleaving-anomalies.html
- Automerge, "Automerge 3.0" (July 2025). https://automerge.org/blog/automerge-3/
- Ink & Switch, Patchwork / Universal version control notebook. https://www.inkandswitch.com/patchwork/notebook/01
- Library of Congress, Recommended Formats Statement: Datasets. https://www.loc.gov/preservation/resources/rfs/data.html ; Textual works: https://www.loc.gov/preservation/resources/rfs/text.html ; SQLite's summary: https://sqlite.org/locrsf.html
