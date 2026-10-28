# Representing Beliefs, Uncertainty, Contradiction, and Argument: what a personal epistemic store should borrow, and what it should avoid

Track 04. Date: 2026-10-07. Status: research note. It feeds the design phase and is not a decision.

How this was verified: I checked specific claims, numbers and 2025-2026 developments with web search and fetch until the shared search budget ran out partway through. Anything I could not re-check this session comes from background knowledge and is marked "(unverified)" wherever a precise number, title or date matters.

---

## Scope and questions

This track asks how to represent an epistemic state that changes over time: what a person believes, how strongly, on what grounds, against what objections, and how that has changed. The project's other foundations sit on top of this. The "coherent and evolving understanding" in the brief is a claim about epistemic state, so if this layer is wrong, no amount of retrieval or UI fixes it.

Questions this note tries to answer:

1. **Atomic unit.** Is the basic unit a note, a claim, a triple, or a statement with qualifiers? Is there one unit at all?
2. **Revisable belief.** How should "I believe X with moderate confidence because A and B, though C conflicts" be stored so that later revisions are cheap, explicit and lossless?
3. **Contradiction.** How can contradictions be held without forcing early resolution, and without the system silently picking a winner?
4. **Source and person.** How do we keep what a *source* asserts (including what an AI asserted in a chat) separate from what the *person* believes?
5. **Uncertainty.** Should uncertainty be numeric, verbal, structural, or some mix, given that people are poor at producing numbers?
6. **Formal frameworks.** Which ones (AGM, TMS, Dung, ASPIC+, Bayesian credences, paraconsistent logic) carry over into a working system, and which are traps?

Out of scope (other tracks cover these): storage engines, retrieval, capture pipelines, integration with specific AI products, and the cognitive science of human memory.

---

## Key findings

**1. AGM gives the right vocabulary but cannot be the engine.**
- *Mechanism.* AGM (Alchourrón, Gärdenfors and Makinson, 1985) defines three operations on a belief set:
  - **Expansion:** add a belief.
  - **Contraction:** remove a belief.
  - **Revision:** add a belief while keeping the set consistent.
  
  These are governed by rationality postulates, with minimal change achieved through an *epistemic entrenchment* ordering: give up the least entrenched beliefs first.
- *Practical limits:*
  - Belief sets are logically closed, which makes them infinite.
  - It needs a total entrenchment ordering that nobody can elicit.
  - It is single-step. Iterated revision needed extra postulates (Darwiche and Pearl, 1997).
  - Propositional revision is computationally hard, at the second level of the polynomial hierarchy for many operators (Eiter and Gottlob, 1992) (unverified exact class).
  - Most importantly, it assumes a logic in which "does A conflict with B" is decidable. Natural-language claims have no such logic.
- *What survives:*
  - **Hansson-style belief bases.** Revise the finite set of explicitly held commitments, not their closure.
  - **Minimal change** as a heuristic.
  - **Entrenchment as an ordering** that can be approximated from structure (how much depends on a belief, how explicitly it was endorsed).
- *Evidence from 2026.* Several preprints map AGM onto agent-memory graphs. Kumiho (Park, arXiv 2603.17244, March 2026) proves that its versioned property-graph operations satisfy AGM K\*2–K\*6 and Hansson's Relevance and Core-Retainment. The hard judgement in such systems, whether two natural-language statements actually conflict, is still handed to an LLM. **The formal guarantees cover the bookkeeping, not the judgement.** Also note that the AGM recovery postulate fails for belief bases. In practice, an append-only history is what makes "recovery" possible: you can reinstate a stance you dropped.

**2. "I was wrong" and "the world changed" are different operations, and most AI memory systems merge them.**
- *Mechanism.* Katsuno and Mendelzon (1991) separated *revision* (better information about a static world) from *update* (the world itself changed) (unverified exact citation).
  - After an update, the old belief stays true *of the past*.
  - After a revision, the old belief was never true. It was only *held*.
  
  These need different history semantics. Update needs **valid time**: when the proposition held in the world. Revision needs **belief time**: when the person held the stance.
- *Evidence.*
  - Mem0 (Chhikara et al., 2025) resolves a contradiction with a **DELETE**, defined as "removal of memories contradicted by new information". Its graph variant, Mem0g, instead marks relationships "invalid rather than physically removing them".
  - Zep/Graphiti (arXiv 2501.13956) uses a bi-temporal model with `valid_at`/`invalid_at` (world time) and `created_at`/`expired_at` (system time), and invalidates rather than deletes.
  
  Neither system types *why* the old fact stopped being current. The bi-temporal fields can express the difference, but no operation names it.

**3. Truth maintenance offers the right dependency mechanics, built on the wrong assumption about completeness.**
- *Mechanism.*
  - Doyle's JTMS (1979) records a *justification* for each belief. When a premise is retracted, *dependency-directed* retraction removes exactly the beliefs that lost all support.
  - de Kleer's ATMS (1986) labels each belief with the minimal sets of *assumptions* (environments) under which it holds, and records *nogoods* (assumption sets known to be contradictory). This lets many mutually inconsistent contexts coexist. The paper's own phrase is that "context switching is free".
- *Limits.*
  - The ATMS can blow up exponentially: n assumptions give 2^n environments.
  - Both systems assume that **the inference engine supplied every justification**. A person's recorded reasons are always a subset of their actual reasons. Automatic retraction would therefore be unsound in a personal store: deleting a belief because its only *recorded* support fell would be wrong when unrecorded support exists.
- *Conclusion.* Keep the dependency graph, but **propagate review flags, not truth values**.

**4. Dung-style acceptability tells you what was recorded, not what is true. Gradual semantics are more useful.**
- *Mechanism.* Dung (1995) reduces non-monotonic reasoning to an attack graph over abstract arguments, and defines which sets of arguments are jointly acceptable (grounded, preferred and stable extensions). It is elegant, and it unifies a lot of non-monotonic logic.
- *Limit.* In a sparse, partly recorded personal graph, an argument is "undefeated" mainly because nobody wrote down its counter-argument. **The verdict measures recording effort.**
- *Better fit.* Bipolar (support and attack) frameworks with *gradual* semantics compute a continuous strength from base scores. Argumentative LLMs (Freedman et al., AAAI 2025) have an LLM generate pro and con arguments and assign base strengths, then a deterministic gradual semantics computes the claim's strength. On three fact-verification benchmarks this matched chain-of-thought accuracy, and it was "provably contestable": change one base score and you can see exactly how the verdict moves. **That property, an explainable and contestable aggregate, is what a personal system needs.** It should be a diagnostic, not an oracle.

**5. Kinds of attack matter, and binary "supports/contradicts" creates false contradictions.**
- *Mechanism.* Pollock distinguished two kinds of defeater:
  - **Rebutting defeaters** argue for the opposite conclusion.
  - **Undercutting defeaters** sever the inference without denying the conclusion. The standard example: "it looks red, but the lighting is red".
  
  ASPIC+ (Prakken) adds **undermining**, which attacks a premise. That gives three distinct attack types (SEP, "Defeasible Reasoning").
- *Why it matters here.* Much real-world "contradiction" between notes is not rebuttal. It is a scope or condition mismatch: "that study was on students", "that advice applies to early-stage startups", "that was before the API changed". If the only relation available is `contradicts`, every scope restriction looks like a conflict that must be resolved. An `undercuts` edge, or a context qualifier, dissolves it while keeping both claims. This is my inference from the formal distinction plus Wikidata practice (Finding 9), not an empirically measured rate.

**6. Formal structure fails when people have to supply it up front. This is the strongest documented failure in the area.**
- *Mechanism.* Shipman and Marshall's "Formality Considered Harmful" (CSCW journal, 1999) attributes the failure of formal representations in interactive systems to four causes:
  - **Cognitive overhead:** extra decisions about chunking, linking and labelling.
  - **Tacit knowledge:** articulating it "interrupts the task".
  - **Premature structure:** users rationally avoid committing to categories they may later regret.
  - **Situational structure:** the right schema depends on the task.
- *Evidence from IBIS and gIBIS:*
  - People disagree about discourse roles: "what one person thinks is an argument may be an issue to someone else".
  - People produce positions with arguments embedded in them.
  - People apply link semantics inconsistently.
- *Remedy proposed by the same authors.* **Incremental, system-assisted formalization** (Shipman and McCall, CHI 1994, the Hyper-Object Substrate). LLMs make this far more feasible in 2026 than it was in 1994.

**7. The evidence for argument mapping is real but narrower than the usual claim.**
- *Evidence.*
  - Álvarez Ortiz's 2007 meta-analysis (as summarised secondhand) found the largest critical-thinking gain over controls for philosophy courses with "lots of argument mapping practice", about d = 0.63, against d = 0.09 for some other approaches.
  - Twardy (2004) reported computer-based mapping roughly tripling gains.
  - Caveats:
    - Most studies are pre/post or quasi-experimental.
    - Many come from the mapping tools' own advocates (the Melbourne/Rationale group).
    - Van Gelder's own phrase is "lots means lots": the effect depends on heavy practice with feedback.
    - Galway studies (Dwyer, Hogan and Stewart) found mapping groups improved on some critical-thinking subscales, but other comparisons found **no significant difference between argument maps and hierarchical outlines**.
    - Cullen et al. (npj Science of Learning, 2018) reported gains from argument visualisation in Princeton seminars (unverified details).
- *Mechanism (my reading).* The benefit comes from **making reasons explicit and decomposed, plus practice and feedback**. The two-dimensional diagram itself matters less.
- *Popular belief contradicted.* "Argument maps make people reason better" is overstated. "Practising explicit decomposition of reasons improves reasoning" is better supported.

**8. Numbers versus words: both fail, in different ways. Uncertainty also has two dimensions, not one.**
- **Words are ambiguous.** Wintle et al. (PLoS ONE, 2019) tested interpretation of verbal probabilities against the ICD 203 intelligence standard. Correspondence was 32% in the control condition. Only bracketing the numeric range in the text lifted it substantially, to 66%.
- **Coarse buckets throw away information.** Friedman et al. (International Studies Quarterly, 2018) analysed 888,328 geopolitical forecasts and found that coarsening numbers into qualitative-style bins "consistently sacrifices predictive accuracy". The biggest losses were for small probabilities.
- **Numbers are hard for most people.** Untrained people find them hard and dislike giving them. The calibration literature (Tetlock and the Good Judgment Project) shows calibration is trainable but needs **resolvable questions and feedback**. Most personal beliefs ("my team's process is bad") never resolve.
- **One number cannot carry both dimensions.** The imprecise-probability tradition (Walley, 1991) points out that 0.5 from ignorance and 0.5 from balanced strong evidence are different epistemic states. *Credence* (how likely) and *resilience* (how much evidence, and how stable) are separate dimensions.
- **AI makes this worse.**
  - Zhou et al. (2024) found LLMs reluctant to express uncertainty. High-confidence responses still had an average 47% error rate, and users relied on both marked and unmarked certainty.
  - A 2025 follow-up found the same over-reliance across languages (arXiv 2507.06306).
  - A 2026 study of 19 LLMs found they reproduce human mappings from verbal phrases to numbers, but assign systematically *higher* probabilities to negative phrases such as "unlikely" (Petridis et al., arXiv 2608.26327).
  
  So confidence labels that an AI extracts from text are a second source of miscalibration stacked on top of human vagueness.

**9. Several independent communities ended up with the same separation between what a source says and what is believed. That is a strong signal.**
- **Wikidata** calls itself a "secondary knowledge base": it collects *claims with references* rather than asserting facts. Each statement is a value plus *qualifiers* (temporal and contextual scope), *references* and a *rank*. Ranks are preferred, normal or deprecated.
- **Nanopublications** split each unit into three named graphs: *assertion*, *provenance* and *publication info*. Each unit is immutable and addressed by a content hash (a "Trusty URI").
- **Micropublications** (Clark, Ciccarese and Goble, J. Biomed. Semantics, 2014) take the minimal unit to be a claim plus its attribution. The full form is a network of statements, data, methods, and support or challenge relations.
- **Discourse graphs** (Joel Chan et al.) separate *Evidence* (a source-bound observation: "in this study, under these conditions, X was observed") from *Claim* (a generalisable assertion), organised under *Questions* and linked to *Sources*. The stated aim is to "separate observations from interpretations" so that knowledge can be updated "without flattening disagreement". The Obsidian plugin is now out of beta in the community plugin browser. Chan et al.'s 2024 synthesis-infrastructure paper (arXiv 2407.20666) reports three years of research through design and field deployment.

These communities (open knowledge bases, scientific publishing, biomedical annotation, HCI and synthesis research) arrived at the same move independently: **the content of a proposition, the act of asserting it, and the grounds for it are separate objects.**

**10. Deprecating beats deleting. The field converged on this in 2025-2026, for good reasons.**
- *Wikidata's rules.* Wikidata's Help:Ranking says to deprecate wrong or outdated statements rather than delete them. Deprecation should come with a `reason for deprecated rank` (P2241), and there is a matching `reason for preferred rank` (P7452). Wikidata gives three reasons:
  1. Deprecation **prevents others from re-adding the value**.
  2. It documents how knowledge evolved.
  3. It fits the role of a secondary knowledge base.
- *The same pattern in AI memory:*
  - Graphiti invalidates instead of deleting.
  - Mem0g marks relationships invalid.
  - Kumiho uses immutable revisions with movable tag pointers.
  - BeliefMem (Liao et al., arXiv 2605.05583, May 2026) "retains multiple candidate conclusions with their probabilities" and updates them by Noisy-OR rules instead of committing to one conclusion per observation.
- *The underrated reason.* Reason 1 is the most important one for an AI-fed system. Old chats and documents get re-ingested repeatedly. Without a deprecated record acting as an antibody, a corrected error comes back on the next import.

**11. Summarization and citation chains turn hypotheses into facts, and AI chats are citation chains.**
- *Evidence.* Greenberg (BMJ, 2009) traced a biomedical belief through 242 papers, 675 citations and 220,553 citation paths. Unfounded authority grew through three processes:
  - **Citation bias** against refuting papers.
  - **Amplification** by papers that presented no data of their own.
  - **Invention**, including "conversion of hypothesis into fact through citation alone".
- *Mechanism in this project.*
  - Every chat-to-memory summarisation step is a citation hop that can drop hedges, and LLMs prefer certainty markers (Finding 8).
  - A second loop is specific to AI. The person states a belief, the AI echoes it (sycophancy is well documented, e.g. Sharma et al., 2023, unverified ID), and the echo gets stored as a "supporting source".
  - Five blog posts restating one study, or one AI restating the person, are **one lineage, not five pieces of evidence**.

**12. LLMs still fail at implicit conflict, so reconciliation at read time is unreliable.**
- *Evidence.* STALE (Chao et al., arXiv 2605.06527, 2026) tests 400 expert-validated scenarios where a later observation makes an earlier memory invalid by implication, without explicitly negating it. The best model scored 55.2% overall. A common failure: the model *retrieves* the updated evidence but *still* accepts outdated assumptions embedded in the user's query.
- *Implication.* Dumping all relevant memories into context and trusting the model to reconcile them is roughly a coin flip on the hard cases. Conflict links have to be made explicit **at write or consolidation time**, even if they stay unresolved.

**13. Contradiction can be tolerated locally, and the practical risk is silent inconsistency, not logical explosion.**
- *Mechanism.* Paraconsistent logics block "from a contradiction, anything follows". Belnap's four-valued logic was designed for exactly this situation: a computer hearing from several sources. Each proposition can be *told true*, *told false*, *told both* or *told neither*.
  - The ATMS holds inconsistency in separate environments.
  - Wikidata holds it as several referenced values for the same property.
- *In practice.* Nobody's notebook derives arbitrary conclusions from a contradiction, so explosion is not the real risk. The real risk is that **an AI reading the store quietly picks one side** and presents it as the person's view. Tolerating contradiction therefore means two things: making it *visible and local*, attached to a proposition or question, and making sure consumers see it.

**14. Questions are the most durable organising unit, and they give contradictions a legitimate home.**
- *Mechanism.* IBIS (Kunz and Rittel, 1970) organises discourse as Issues, then Positions, then Arguments. Discourse graphs put Questions at the root too.
  - A question persists while its answers change, so it is the natural anchor for an evolving understanding.
  - Two contradictory claims that answer the same question are *competing positions*, which is a normal state, rather than a data error.
- *Proof standards.* Carneades (Gordon, Prakken and Walton, 2007) attaches a *proof standard* to each issue: scintilla of evidence, preponderance, beyond reasonable doubt. Different questions need different bars before acting. "Which laptop?" needs preponderance. "Should I change careers?" needs more.
- *Lesson from gIBIS and Compendium.* The structure worked in facilitated "dialogue mapping", where a skilled human mapper did the classification in real time. It failed when ordinary participants had to classify their own contributions (Finding 6).

---

## Ideas worth stealing

Each item: the mechanism, then where it comes from.

1. **Statement = proposition + qualifiers + references + rank, with a reason on every rank change.** Qualifiers carry scope (time, population, context), which is how most apparent contradictions dissolve. *Source: Wikidata statement model and Help:Ranking (P2241, P7452).*
2. **A "best-rank" projection.** Wikidata's query service returns preferred values if any exist, otherwise normal ones, and never deprecated ones. That gives a clean way to compile the "current view" from a store that keeps everything. *Source: Wikidata Query Service rank semantics.*
3. **Deprecated records as antibodies.** When the extractor finds a proposition that matches a deprecated one, it links to the deprecation instead of re-adding it. *Source: Wikidata's "prevents others from re-adding" rationale.*
4. **Split each unit into assertion, provenance and publication info, with content-hashed, immutable IDs.** An edit creates a new version with a `supersedes` pointer and never mutates the old one. *Source: nanopublications and Trusty URIs.*
5. **Separate Evidence from Claim.** Evidence is a source-bound observation that carries its context ("in study S, n=40 students, X was observed"). A Claim is a generalisation the person or field makes from evidence. Questions sit at the root. *Source: discourse graphs (Chan); micropublications (Clark et al.).*
6. **Anchors that survive document drift.** Anchor each attribution with an exact quote plus prefix and suffix (`TextQuoteSelector`), refined from a coarser selector via `refinedBy`, with a `TimeState` and a cached copy of the source as it was read. W3C's typed annotation *motivations* (assessing, questioning, commenting, and so on) are a ready-made vocabulary for "my reaction to this source". *Source: W3C Web Annotation Data Model (Recommendation, 23 Feb 2017).*
7. **Three attack types: rebut, undermine, undercut.** An undercut targets the *inference edge*, not a node, so edges need IDs. *Source: Pollock; ASPIC+ (Prakken).*
8. **Explicit assumptions with labels.** Mark some stances as assumptions ("assuming remote work stays the norm"). Every belief carries the set of assumptions it rests on, so "what would I believe if A were false?" is just a filter. *Source: de Kleer's ATMS (environments, nogoods).*
9. **Dependency-directed *review*, not retraction.** When a source is discredited or an assumption dropped, flag every stance whose recorded grounds include it, and let the person decide. *Source: Doyle's JTMS, adapted to incomplete justifications.*
10. **Belnap status per proposition, computed from sources alone.** Told-true, told-false, both or neither is shown *next to* the person's own stance. It separates "what my sources say" from "what I think" in one glance. *Source: Belnap's four-valued logic.*
11. **Distinct revision and update operations, stored bi-temporally.** *Source: Katsuno and Mendelzon (operations); Graphiti/Zep (storage pattern).*
12. **Verbal confidence labels always shown with numeric brackets.** For example "likely (60-80%)". This roughly doubled correct interpretation in Wintle et al. *Source: ICD 203 and Wintle et al. 2019.*
13. **Rate relevance on the edge, not the node.** Kialo users vote on how impactful a claim is *for its parent claim* on a five-point scale. That separates "is this true?" from "does this bear on that?". *Source: Kialo, as described in the Kialo argument-impact dataset papers (47,219 claims over 741 topics).*
14. **Gradual semantics as a contestable "argument health" readout.** Compute a strength from recorded supports and attacks and show *why*. Let the person change one base score and see the effect. *Source: QBAF gradual semantics; Argumentative LLMs (Freedman et al., 2025).*
15. **Incremental formalization.** Capture is free text. Structure (claims, relations, types) is *suggested* by the system and confirmed lazily, ideally at moments when it pays off. *Source: Shipman and Marshall 1999; Shipman and McCall 1994.*
16. **Toulmin fields as optional slots.** Use the *qualifier* (strength and scope) and the *rebuttal* (conditions of exception). The *warrant*, the general rule that makes A count for X, is the most informative and most costly part, so prompt for it only when someone attacks the inference. *Source: Toulmin, The Uses of Argument (1958).*
17. **Per-question proof standards and "status".** Exploring, working hypothesis, good enough to act on, settled, or rejected. These are judged against a bar set for that question, not as a global scalar. *Source: Carneades.*
18. **Ordinal belief strength that supports iteration.** Spohn's ranking functions (integer degrees of disbelief) give a formally sound ordinal scale with a well-defined iterated-revision rule. This is an option if coarse levels ever need composing. *Source: Spohn, ordinal conditional functions (1988) (unverified year).*
19. **Resolvable predictions as a calibration side-channel.** A small subset of beliefs can be phrased as forecasts that resolve. Brier scores on those give the person, and the system, real feedback on what "likely" means for this person. *Source: Good Judgment Project and forecasting literature.*

---

## Pitfalls and anti-patterns

1. **Up-front classification by users (gIBIS, design rationale).** People disagree about issue, position and argument roles. Capture costs are paid now and benefits arrive later, often to someone else (Grudin's design-capture critique, unverified citation). In a personal system the "someone else" is the future self, but the time gap still kills motivation. **Do not ask the person to type their thoughts at capture time.**
2. **Overwrite-on-contradiction ("latest wins").** Mem0's DELETE is the canonical example. It conflates revision with update, destroys exactly the history that makes understanding legible, and lets a single hallucinated or out-of-context extraction erase a well-grounded belief.
3. **Automatic truth propagation over incomplete justifications.** A JTMS-style auto-retract on a personal graph will retract beliefs the person still holds for unrecorded reasons. Users then stop trusting the system.
4. **Treating computed acceptability as truth.** Dung extensions and QBAF strengths over sparse personal graphs mostly reflect what was written down. Present them as diagnostics ("this belief has no recorded support"), not verdicts.
5. **One scalar for "confidence".** It conflates credence with resilience, and the person's confidence with the AI's confidence. Forcing precise numbers on non-forecasters produces noise. Pure verbal labels produce ambiguity (32% correspondence).
6. **Counting echoes as evidence.** Restatements of one study, AI paraphrases of the person's own earlier claim, and the AI's agreement during a chat are all one lineage. Greenberg's citation network shows how such amplification produces "unfounded authority".
7. **Hedge stripping in summarisation.** "Study S suggests X may hold in mice" becomes "X". Each AI summarisation hop is a chance to drop modality, and LLMs lean toward certainty (Zhou et al. 2024).
8. **Graph UI as the centrepiece.** The argument-mapping evidence does not show diagrams beating outlines. Large personal graphs become unreadable tangles. Trees (Kialo) read well but force shared premises to be duplicated. The graph should be the data model. The views should be mostly outlines, question pages and timelines.
9. **Formal-logic encodings (full AGM, description logics) of personal beliefs.** The cost of encoding is prohibitive and the consistency check is the part that matters least. The real judgement ("do these two sentences conflict, or do they differ in scope?") is not logical.
10. **Leaving reconciliation to the LLM at read time.** STALE's 55.2% best score and the habit of accepting stale premises from the user's query mean conflicts must already be explicit in what the model is given.
11. **Benchmarking epistemic memory on QA recall alone.** LoCoMo-style scores (which the 2026 AGM-memory papers report) do not measure calibration, hedge preservation, provenance correctness, or whether contradictions are preserved or wrongly collapsed.

---

## Implications for this project

These are concrete, and most come with a test that could prove them wrong.

**1. Use different units for different jobs.**
- **Capture unit:** the raw *note or excerpt*, immutable.
- **Revision unit:** the *Stance*, the person's dated attitude toward a Proposition.
- **Organisation unit:** the *Question*.

Propositions are short, content-hashed sentences that nobody necessarily believes. Attributions record that a source asserted a proposition. Stances record that the person holds one. *Test:* the representation fixture below and three revisions of it must round-trip through the store and the views with no loss of history or grounds.

**2. Core object types, provisional (with relations as first-class edges that have IDs):**

```yaml
Proposition:  {id: hash(text), text, scope_qualifiers: {time?, population?, context?}}
Attribution:  {id, proposition, agent: source|person|ai_model, modality: asserts|suggests|denies|asks,
               anchor: {source_ref, quote, prefix, suffix, cached_at}, lineage_origin, observed_at}
Stance:       {id, holder: person, proposition, credence: ordinal+bracket, resilience: none|hunch|some|strong,
               status: exploring|working|act-on|settled|rejected, grounds: [edge ids], acknowledged_against: [edge ids],
               assumptions: [stance ids], belief_time: {from, to?}, cause: revision|update|initial,
               supersedes?, created_by: person|ai_suggested_unconfirmed}
Relation:     {id, from, to (node OR edge), type: supports|rebuts|undermines|undercuts|answers|refines|
               equivalent_to|supersedes|derived_from, warrant_text?, relevance?: 1-5, created_by, confirmed?}
Question:     {id, text, proof_standard?, status: open|resolved|dormant}
Tension:      {id, members: [proposition|stance ids], kind: rebut|scope|temporal|unknown, status: open|scoped|resolved}
```

Canonical case: "I believe X (moderate) because A and B, though C conflicts". It becomes:
- one Stance on X, with credence "likely (60-80%)", resilience "some", grounds [A→X, B→X] and acknowledged_against [C→X];
- A as the person's own Evidence attribution, and B and C as anchored source attributions;
- a Tension(X, C) left open.

A later "C turns out to be about large companies only" is an `undercuts` edge on C→X plus a scope qualifier. The Tension moves to `scoped`, and nothing is deleted.

**3. Revision and update are separate API verbs.**
- `revise(stance, ...)` means "I was wrong". The old stance gets an end date in belief time and the proposition's valid time is untouched.
- `update(proposition, ...)` means "it changed". The proposition's valid time is closed and a new proposition is created, while the old stance stays a true record of the past.

*Test:* on a hand-built set of about 30 scenarios, "what did I believe on date D?" and "what was true on date D (per my beliefs now)?" must give different, correct answers.

**4. Nothing epistemic is hard-deleted. Deprecation needs a reason.** A separate `redact` operation exists for privacy and is the only destructive operation. *Test (falsifiable):* re-ingest an old corpus containing N claims that were later corrected. The target is 0 resurrections, with every match linked to its deprecation. Measure the false-match rate (unrelated claims wrongly matched to deprecated ones).

**5. Write-time conflict *linking*, never write-time *resolution*.** The consolidation step proposes `Tension` objects and their type (rebut, scope, temporal). It only auto-applies `supersedes` when the cause is unambiguous and dated. *Test:* measure LLM precision and recall for conflict detection on the person's own data. Given STALE, expect implicit-conflict recall well below 80%, and size the review queue to the measured precision. If precision is below about 60%, the queue becomes noise and the detection prompt or granularity has to change.

**6. AI-proposed structure stays "suggested" until confirmed, and acceptance rate is the main health metric.** *Hypothesis:* if fewer than about half of AI-proposed propositions and relations are accepted when reviewed, extraction is too fine-grained or uses the wrong types. Fix the schema before scaling.

**7. Confidence: ordinal with brackets, plus resilience, plus an optional forecast.**
- Five levels, each shown with its numeric range.
- A separate resilience field.
- An optional resolvable prediction.
- Never store an AI-inferred credence as the person's.

*Test:* the person re-rates a random sample of their own stances after 2-4 weeks without seeing the original. If test-retest agreement is poor at five levels, collapse to three. If it is excellent, consider finer levels.

**8. Count lineages, not citations.** Every Attribution carries `lineage_origin`, the earliest traceable source. Support summaries say "3 independent lineages", not "7 sources". AI-chat attributions whose content traces back to the person's own earlier statements are marked `self-echo` and cannot ground a stance. *Test:* plant echo chains in a test corpus and check they collapse correctly.

**9. Two compiled views from one store:**
- **The AI view**, a "best-rank projection". Current stances with credence and status, open Tensions that touch the topic, hedges kept verbatim, and an explicit "do not assume" list of propositions the person rejected or deprecated.
- **The human view.** Question pages showing the positions, the evidence, and a timeline of stance changes.

*Test:* in a downstream LLM's answers, measure the hedge-preservation rate (the person's "working hypothesis" should not come out as fact) and the stale-premise acceptance rate. Compare against a baseline that just dumps flat notes into context. The projection should win on both.

**10. Dependency-directed review flags.** When an Attribution is deprecated or an assumption is dropped, flag every Stance whose grounds include it. *Test:* track flags per retraction. If one retraction routinely flags more than about 10 stances, grounds are being recorded too loosely, for example linking to whole documents instead of specific evidence.

**11. Questions are the spine.** Every Stance should, eventually, answer at least one Question, and the AI proposes Questions from clusters of claims. *Test:* compare the person's usefulness ratings of "where do I stand on Q?" pages built from questions against pages built from topic or tag clusters over the same data.

**12. Gradual-semantics "argument health" is optional, and only a diagnostic.** Implement it only if items 1-11 hold up. It is useful for flags such as "settled, but no recorded support" or "rated act-on, but its strongest attack is unanswered".

---

## Tensions and open questions

1. **Identity of propositions.** When are two paraphrases the same proposition? Embeddings put negations and scope variants close together. Merging is lossy and not merging fragments the store. Current lean: never auto-merge, link with `equivalent_to`, and let the person confirm. That needs testing for burden.
2. **Granularity.** One sentence-level claim per proposition, or per paragraph? Finer units give better revision but cost more to review and match the gIBIS problem of "positions with arguments embedded". This needs an empirical pilot on the person's real material.
3. **Write-time linking versus premature resolution.** Finding 12 says to make conflicts explicit early. Finding 13 says not to resolve them early. The design bets that *linking without resolving* satisfies both. The bet fails if Tension objects pile up unreviewed. How many open Tensions can a person live with?
4. **Not everything is a belief.** Goals, values and preferences are not true or false, so their change is preference change, not revision. A past decision is a commitment made on past information, and judging it on later information is hindsight bias. Decisions should probably be IBIS-style records (question, chosen position, rationale, assumptions) that are *superseded*, never *revised*. Do goals need their own revision semantics? Probably, but that is outside this track.
5. **Where entrenchment comes from.** It could be computed (number of dependents, age, how often it is retrieved), declared ("core belief"), or both. Computed entrenchment risks making the system defend whatever has been repeated most, which is the Greenberg failure applied to oneself.
6. **Does the person need numbers at all?** For non-resolvable personal beliefs, structural uncertainty (open questions, unanswered attacks, competing positions) might serve both humans and AI better than any credence label. This could be tested by building with and without credence fields and checking which the person actually maintains.
7. **How much the AI may infer about the person's stance.** An AI proposing "you seem to believe X" from chats is useful but dangerous: sycophancy and over-reading. Is an AI-inferred stance allowed in the AI view before confirmation? Current lean: yes, but labelled "inferred, unconfirmed" and with lower priority.
8. **Never deleting versus the right to forget.** An honest belief history contains embarrassing or private past beliefs. `redact` has to exist, but it breaks lineage and dependency graphs. What survives a redaction?
9. **Contradiction typing reliability.** The value of Tension objects depends on telling rebut, scope and temporal conflicts apart. Can an LLM do that reliably on personal notes? Unknown. It is a priority experiment.
10. **Is "coherence" the right goal?** An LLM can always produce a coherent-sounding synthesis from fragments. Coherence is cheap. Calibrated, traceable understanding with visible open questions is not. The evaluation plan should reward the second and penalise forced coherence.

**Challenges to the framing of the brief:**
- "Knowledge, ideas, beliefs, reasoning, decisions, goals" do not share one update logic.
- "Contradictions" are mostly scope or temporal mismatches, not logical contradictions.
- The store will only ever model the person's *expressed* commitments, which are a belief base, not their mind.
- The argument structure may mainly serve the *maintenance process* (AI-assisted revision) rather than either the human or the AI reader directly.

---

## Sources

Verified this session via web search or fetch unless marked (unverified) or (background).

**Belief revision, truth maintenance, defeasible reasoning, argumentation**
- Alchourrón, Gärdenfors, Makinson (1985), "On the logic of theory change: partial meet contraction and revision functions", *J. Symbolic Logic* 50(2) (background).
- Katsuno and Mendelzon (1991), "On the difference between updating a knowledge base and revising it", KR'91 (background). Overview of revision versus update and Darwiche-Pearl iteration: https://arxiv.org/pdf/1501.06206
- Darwiche and Pearl (1997), "On the logic of iterated belief revision", *Artificial Intelligence* 89 (background).
- Eiter and Gottlob (1992), complexity of propositional knowledge-base revision, *Artificial Intelligence* 57 (background; exact class unverified).
- Hansson (1999), *A Textbook of Belief Dynamics* (background).
- Almeida and Casals (2026), "From Doyle to AGM: A Survey and an Implementation Roadmap for Belief Change": https://arxiv.org/abs/2608.14567
- Doyle (1979), "A truth maintenance system", *Artificial Intelligence* 12(3) (background).
- de Kleer (1986), "An assumption-based TMS", *Artificial Intelligence* 28:127-162: https://www.dekleer.org/Publications/An%20Assumption-Based%20TMS.pdf
- Dung (1995), "On the acceptability of arguments and its fundamental role in nonmonotonic reasoning, logic programming and n-person games", *Artificial Intelligence* 77:321-357: https://cse-robotics.engr.tamu.edu/dshell/cs631/papers/dung95acceptability.pdf
- Stanford Encyclopedia of Philosophy, "Defeasible Reasoning" (Pollock's rebutting and undercutting defeaters; ASPIC+): https://plato.stanford.edu/entries/reasoning-defeasible/
- Gordon, Prakken, Walton (2007), "The Carneades model of argument and burden of proof", *Artificial Intelligence* 171 (background).
- Freedman, Dejl, Gorur, Yin, Rago, Toni (2025), "Argumentative Large Language Models for Explainable and Contestable Claim Verification", AAAI-25: https://ojs.aaai.org/index.php/AAAI/article/view/33637 (arXiv: https://arxiv.org/abs/2405.02079)
- Belnap (1977), "A useful four-valued logic" / "How a computer should think" (background).
- Walley (1991), *Statistical Reasoning with Imprecise Probabilities* (background).
- Spohn, ordinal conditional functions / ranking theory (background; year unverified).

**Argument structure, IBIS, mapping evidence**
- Kunz and Rittel (1970), "Issues as elements of information systems" (background); Conklin and Begeman (1988), gIBIS, *ACM TOIS* (background).
- Shipman and Marshall (1999), "Formality Considered Harmful", *CSCW* 8(4):333-352: https://people.engr.tamu.edu/shipman/formality-paper/harmful.html
- Shipman and McCall (1994), "Supporting Knowledge-Base Evolution with Incremental Formalization", CHI'94: https://people.engr.tamu.edu/shipman/chi94-hos/chi94hos_abstract.html
- Toulmin (1958), *The Uses of Argument* (background).
- Álvarez Ortiz (2007) meta-analysis, secondary summary: https://www.lesswrong.com/posts/MGtKNd5GBXN5oNj7p/to-learn-critical-thinking-study-critical-thinking ; van Gelder, "Lots means lots": https://timvangelder.com/2006/12/03/lots-means-lots
- Twardy (2004), "Argument maps improve critical thinking" (cogprints listing): https://web-archive.southampton.ac.uk/cogprints.org/3008/index.html
- Dwyer, Hogan, Stewart, Galway argument-mapping studies: https://research.universityofgalway.ie/en/publications/the-promotion-of-critical-thinking-skills-through-argument-mappin-6/
- Cullen, Fan, van der Brugge, Elga (2018), argument visualisation field study, *npj Science of Learning*, doi:10.1038/s41539-018-0038-5 (article exists; authors and findings unverified this session).
- Kialo argument-impact dataset (47,219 claims, 741 topics, five-level impact votes on claim-to-parent): https://arxiv.org/abs/2004.03034
- Grudin (1996), design-capture cost/benefit critique, in Moran and Carroll (eds.), *Design Rationale* (unverified).

**Uncertainty and calibration**
- Wintle, Fraser, Wills, Nicholson, Fidler (2019), "Verbal probabilities: Very likely to be somewhat more confusing than numbers", *PLoS ONE*: https://pmc.ncbi.nlm.nih.gov/articles/PMC6469752/
- Friedman, Baker, Mellers, Tetlock, Zeckhauser (2018), "The Value of Precision in Probability Assessment", *International Studies Quarterly* (author list partly unverified): https://www.hks.harvard.edu/publications/value-precision-probability-assessment-evidence-large-scale-geopolitical-forecasting
- Zhou et al. (2024), "Relying on the Unreliable: The Impact of Language Models' Reluctance to Express Uncertainty": https://arxiv.org/abs/2401.06730
- "Humans overrely on overconfident language models, across languages" (2025): https://arxiv.org/abs/2507.06306
- Petridis, Pelechrinis, Obradovic (2026), "How Unlikely Is 'Unlikely'? Assessing Verbal Probability Perception Across Large Language Models": https://arxiv.org/abs/2608.26327
- Sharma et al. (2023), "Towards Understanding Sycophancy in Language Models", arXiv 2310.13548 (ID unverified this session).

**Scholarly and statement models**
- Wikidata Help:Ranking: https://www.wikidata.org/wiki/Help:Ranking
- Clark, Ciccarese, Goble (2014), "Micropublications: a semantic model for claims, evidence, arguments and annotations in biomedical communications", *J. Biomed. Semantics* 5:28: https://doi.org/10.1186/2041-1480-5-28
- Nanopublications (assertion, provenance, pubinfo; Trusty URIs), Knowledge Pixels registry and Nanodash: https://registry.knowledgepixels.com/ ; Groth, Gibson, Velterop (2010), "The anatomy of a nanopublication" (background).
- Discourse Graphs project: https://discoursegraphs.com/ ; Obsidian plugin: https://community.obsidian.md/plugins/discourse-graphs
- Chan, Akamatsu, Vargas, Kawerau, Gartner (2024), "Steps Towards an Infrastructure for Scholarly Synthesis": https://arxiv.org/abs/2407.20666
- W3C Web Annotation Data Model (Recommendation, 23 Feb 2017): https://www.w3.org/TR/annotation-model/
- RDF 1.2 Concepts (triple terms for statements about statements; Candidate Recommendation stage in 2026): https://www.w3.org/TR/2026/WD-rdf12-concepts-20260128/
- Greenberg (2009), "How citation distortions create unfounded authority: analysis of a citation network", *BMJ*: https://pubmed.ncbi.nlm.nih.gov/19622839/

**AI memory systems (2025-2026)**
- Chhikara et al. (2025), "Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory" (ADD/UPDATE/DELETE/NOOP; Mem0g invalidation): https://arxiv.org/abs/2504.19413
- Rasmussen et al. (2025), "Zep: A Temporal Knowledge Graph Architecture for Agent Memory" (author list background): https://arxiv.org/abs/2501.13956
- Park (2026), "Graph-Native Cognitive Memory for AI Agents: Formal Belief Revision Semantics for Versioned Memory Architectures" (Kumiho): https://arxiv.org/abs/2603.17244
- Liao, Wang, Zhu, Du, Yan, Chen (2026), "Belief Memory: Agent Memory Under Partial Observability" (BeliefMem): https://arxiv.org/abs/2605.05583
- Chao, Bai, Sheng, Li, Sun (2026), "STALE: Can LLM Agents Know When Their Memories Are No Longer Valid?": https://arxiv.org/abs/2605.06527
