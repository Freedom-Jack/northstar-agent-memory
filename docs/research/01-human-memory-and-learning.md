# Human Memory, Learning, and Understanding: What an External Knowledge System Should Mirror, and What It Should Refuse to Mirror

Research track 01 (cognitive science). Written 2026-10-07.

Method note: this draws on my own knowledge plus web verification. The web search budget for this session ran out partway through. Claims checked against a live source are cited with a URL. Claims from memory that I could not re-check are marked "(unverified)" where a specific number or detail matters. The track's other half, the AI-memory literature (RAG, agent memory, knowledge graphs), belongs to other tracks. I touch it only where cognitive science directly constrains it.

---

## Scope and questions

The project wants to turn scattered fragments (AI chats, reading, work, one's own thinking) into "a coherent and evolving understanding." This note asks what human cognition says about that goal:

1. **What kinds of memory exist, and do they follow different update rules?** Episodic, semantic and procedural memory; verbatim versus gist.
2. **How do new experiences become integrated knowledge?** Complementary learning systems, systems consolidation, offline replay, and schemas.
3. **How do beliefs and concepts actually change?** Reconsolidation, knowledge revision, assimilation versus accommodation, and conceptual change.
4. **Why does memory forget, and when is forgetting useful?** Interference, retrieval-induced forgetting, and the gap between storage strength and retrieval strength.
5. **Which processes produce durable, usable understanding, as opposed to the feeling of it?** Testing, generation, elaboration, spacing, chunking, expertise, and metacognition.
6. **Where does human memory systematically fail?** Source amnesia, illusory truth, hindsight and consistency bias, suggestibility.
7. **What happens when memory is offloaded to external systems, LLMs in particular?** Extended mind, transactive memory, the Google effect, and the 2024-2026 evidence on LLMs.

The central question is **what "coherent and evolving understanding" means mechanistically**, and which processes create it. My answer is in the synthesis at the end of the Key findings. In short, understanding is not a property of a store. It is a person's ability to reconstruct, explain, predict and apply, and it comes from effortful processes the person performs. An external system can schedule, scaffold and audit those processes. If it performs them on the person's behalf, it can quietly remove them.

---

## Key findings

### 1. Memory is several systems with different update rules, and gist and verbatim are stored in parallel

- **Mechanism.** Episodic memory stores events tied to time, place and source. Semantic memory holds knowledge abstracted across episodes. Procedural memory is updated by practice, not by being told.
- **Fuzzy-trace theory** (Reyna & Brainerd) adds that verbatim and gist traces are encoded in parallel. Verbatim fades fast, gist persists, and most reasoning runs on gist.
- **Multiple-trace and transformation accounts** (Nadel & Moscovitch 1997; Winocur & Moscovitch 2011) hold that consolidation extracts a schematic version while detailed episodic traces remain.
- **Design relevance.** The brain does not replace episodes with summaries. It keeps both: gist for fast inference, episodes for re-interpretation when the gist proves wrong.

### 2. Complementary Learning Systems: fast capture and slow integration exist because fast integration destroys structure

- **Mechanism.** McClelland, McNaughton & O'Reilly (1995) showed that a single distributed network learning quickly suffers catastrophic interference: new learning overwrites the shared weights that encode old structure.
- **The brain's answer is two systems.** The hippocampus encodes episodes quickly with sparse codes. The neocortex learns slowly, from interleaved replay of old and new experiences.
- **Hippocampal indexing theory** (Teyler & DiScenna 1986): the hippocampus stores pointers to cortical content, not the content itself.
- **The 2016 update** (Kumaran, Hassabis & McClelland): fast cortical learning is possible for schema-consistent information, and replay can be prioritized.
- **Design relevance.** This is a real computational constraint on any shared, compressed representation, LLM-written synthesis pages included. If every conversation immediately rewrites the "understanding" layer, it drifts toward the most recent input.

### 3. Consolidation should be selective, and consolidation itself distorts

- **Go-CLS.** Sun, Advani, Spruston, Saxe & Fitzgerald (Nature Neuroscience 2023) show that unregulated transfer of every memory into the neocortex overfits when the world is partly unpredictable: noise is learned as structure. Their remedy is to consolidate only when doing so improves generalization, and to leave idiosyncratic memories episodic.
- **Generative consolidation.** Spens & Burgess (Nature Human Behaviour 2024) model consolidation as replay training a generative model (a VAE) in the neocortex.
  - Recall becomes reconstruction: predictable features are regenerated from the schema, and only surprising features need episodic storage.
  - The model reproduces schema-based distortions that grow as consolidation proceeds.
- **Design relevance.** This closely describes LLM-maintained notes. An LLM that rewrites a person's notes into a "consolidated" summary reconstructs from its prior. It regularizes idiosyncratic content toward the typical, and does so more with each rewrite. The remedy is to consolidate selectively, keep the originals, and measure drift.

### 4. Schemas change how fast and how faithfully new information is learned

- **Tse et al. (Science 2007).** Rats with a prior schema of six flavor-place associations learned new ones in one trial.
  - Those memories became hippocampus-independent within 48 hours: lesions at 48 hours spared them, while lesions at 3 hours abolished them.
  - Normally this takes weeks.
- **SLIMM** (van Kesteren, Ruiter, Fernández & Henson, Trends in Neurosciences 2012).
  - Congruent information is integrated quickly via the mPFC and cortex.
  - Incongruent information is encoded as a distinct episode via the hippocampus.
  - Both extremes are remembered better than middling items.
- **A 2026 complication.** Yacoby, Greve, Schaverien, Shtoots, Henson & Levy (Memory & Cognition 2026) found that item recognition favored expected items, while the U-shape appeared in source memory. The congruence effect is real, but less uniform than SLIMM predicts.
- **The cost of fluency.** Schema-consistent lures, things that fit but were never encountered, are falsely "remembered."
- **Design relevance.** Route new input by fit:
  - **Congruent:** attach cheaply.
  - **Incongruent:** keep as a distinct, source-tagged anomaly and never force-merge it.
  - **Middling:** handled well by neither path, so it is the most likely to be lost.

  Congruent attachment also needs a guard against schema-driven confabulation.

### 5. Updating does not overwrite: old knowledge persists and must be out-competed

- **Reconsolidation.** Reactivating a consolidated memory can make it labile and modifiable (Nader, Schafe & LeDoux, Nature 2000). This happens mainly when retrieval involves prediction error (Sinclair & Barense 2019; Lee, Nader & Schiller 2017).
- **A popular claim that failed.** The idea that reconsolidation can erase human memories failed a high-powered registered replication (Chalkia et al., Cortex 2020). That replication found no benefit over ordinary extinction, and documented misreported exclusion criteria in the original study.
- **KReC.** Kendeou & O'Brien (2014) assume that information in long-term memory is never erased and is passively reactivated. Revision therefore needs three things:
  - co-activation of the old belief and the correction;
  - integration, meaning explicit linkage between them;
  - competing activation, where the new information gains strength until it dominates.

  Refutation texts work because they state the misconception, refute it, and explain.
- **The continued-influence effect.** Retracted misinformation keeps shaping reasoning unless a causal alternative replaces it (Johnson & Seifert 1994; Lewandowsky, Ecker et al. 2012; Ecker et al. 2022).
- **Design relevance.**
  1. Silently overwriting an outdated note does not update the person. The old belief resurfaces, and the system and the mind diverge.
  2. The right primitive is a supersession record: "A was believed because X; B replaces it because Y; here is why A seemed right."
  3. Prediction error, not mere retrieval, should be what opens a belief for revision.

### 6. Conceptual change comes in kinds, and some cannot be done by editing items

- **Assimilation versus accommodation.** Piaget distinguished fitting new input into a schema from changing the schema.
- **Posner, Strike, Hewson & Gertzog (1982)** gave four conditions for replacing a conception: dissatisfaction with the current one, and a new one that is intelligible, plausible and fruitful. Anomalies must accumulate and be noticed first.
- **Chi (2008)** separates three kinds of change:
  - belief revision of a single proposition, which is easy;
  - mental-model transformation;
  - categorical shift, such as heat "as a substance" becoming heat "as an emergent process." This is very hard, and many robust misconceptions are miscategorizations that piecemeal correction cannot fix.
- **Carey (2009)** argues that some successor concepts are partly incommensurable with their predecessors and must be bootstrapped.
- **Synthetic models.** Vosniadou & Brewer (1992) found that children reconcile conflicting inputs into hybrids, such as a flat disc or hollow-sphere earth, that are wrong in new ways.
- **Knowledge in pieces.** diSessa holds that naive knowledge is a loose set of context-cued fragments, and that expertise is their progressive organization into a systematically applied whole.
- **Design relevance.**
  - "Fragments becoming coherent" is a studied phenomenon.
  - The worst failure is forced coherence. An LLM asked to merge contradictory notes is a synthetic-model generator.
  - Item-level edits (add, edit, link) cannot express a categorical shift, so restructuring must be a first-class operation.

### 7. Forgetting is adaptive, and the right model is two strengths, not one

- **The new theory of disuse** (Bjork & Bjork 1992).
  - Storage strength, how well something is learned, never decreases.
  - Retrieval strength, how accessible it is now, decays with disuse.
  - The difficulty of a retrieval determines how much storage strength it adds.
- **Rational analysis** (Anderson & Schooler 1991). The probability of recall tracks how often and how recently such items are needed in the environment. ACT-R's base-level activation formalizes this.
- **Richards & Frankland (Neuron 2017)** argue that memory serves decisions, not fidelity, and that active forgetting removes outdated detail and aids generalization.
- **Retrieval-induced forgetting** (Anderson, Bjork & Bjork 1994). Retrieving some items impairs related, unpracticed competitors. Restudy does not produce this, and semantic integration of the items reduces it.
- **Design relevance.**
  - Never hard-delete for relevance. Model accessibility separately from existence.
  - Expect a retrieval-induced-forgetting-like monoculture when retrieval keeps surfacing the same top-k items.
  - Integration links are a defense against it.

### 8. Durable learning comes from effortful generation, and learners prefer what feels easy

- **Retrieval practice beats restudy.** Roediger & Karpicke (2006) found one-week recall of roughly 61% after repeated testing versus 40% after repeated study, while students predicted the reverse (numbers from memory, unverified).
- **Generation and self-explanation.** Generation (Slamecka & Graf 1978), self-explanation (Chi et al. 1989) and spacing (Cepeda et al. 2006) all improve durable learning.
- **The Dunlosky et al. (2013) review** rated:
  - practice testing and distributed practice as "high utility";
  - elaborative interrogation, self-explanation and interleaving as "moderate";
  - highlighting, summarization and rereading as "low."
- **The learner's illusion.** Desirable difficulties (Bjork 1994) slow apparent learning but improve retention and transfer. Learners nonetheless prefer fluent, massed study (Kornell & Bjork 2008), and rereading is the most popular strategy (Karpicke, Butler & Roediger 2009).
- **Contradicts popular belief.** The staple practices of personal knowledge management (highlight capture, clipping, auto-summaries) are exactly the low-utility techniques. Organizing them better does not change that.
- **Design relevance.** Understanding is produced mostly by what the person does: retrieve, generate, explain, compare. The system should create occasions for these activities, not perform them on the person's behalf.

### 9. Expertise is chunked, principle-organized, and retrieval-structured

- **Chunking.** Chess masters' memory advantage comes from chunks of meaningful patterns, and largely disappears for random positions (Chase & Simon 1973).
- **Deep versus surface organization.** Physics experts sort problems by deep principle, novices by surface features (Chi, Feltovich & Glaser 1981).
- **Retrieval structures.** Experts extend working memory with learned retrieval structures (Ericsson & Kintsch 1995).
- **Working-memory limit.** Working memory holds about 4 chunks (Cowan 2001).
- **The expertise reversal effect.** Support that helps novices hurts experts (Kalyuga et al. 2003).
- **Design relevance.**
  - Topic folders are a novice organization. Organize around principles, causal models and questions instead.
  - Human-facing views should show a handful of expandable chunks.
  - The best human view changes as expertise grows, while the AI-facing view can carry full detail.

### 10. Metacognition is the weak link, and external access inflates it

- **Feelings of knowing are inferences, not readouts.** They are drawn from cue familiarity and partial accessibility (Koriat 1993), and they feed study decisions (Nelson & Narens 1990).
- **The illusion of explanatory depth.** Confidence in understanding everyday mechanisms collapses when people try to explain them (Rozenblit & Keil 2002).
- **Search inflates self-assessed knowledge.**
  - Fisher, Goddu & Keil (JEP: General 2015; 9 experiments) found that searching the internet for explanations raised people's ratings of their own internal knowledge, even on unrelated questions.
  - Ward (PNAS 2021; 8 experiments, n = 1,917) found that people who googled to fill gaps took the knowledge to be their own and over-predicted their unaided performance.
- **The hypercorrection effect.** High-confidence errors, once corrected, are corrected more durably (Butterfield & Metcalfe 2001).
- **Design relevance.**
  - An always-available, fluent knowledge system will raise felt understanding regardless of real understanding. This is the project's biggest human-side risk.
  - Calibration must be measured with "explain it without looking" probes.
  - Confident-but-wrong beliefs are the highest-value targets for surfacing contradictions.

### 11. Memory loses the source and rewrites its own history

- **Source is not stored reliably.** It is inferred at retrieval (Johnson, Hashtroudi & Lindsay 1993).
  - **The sleeper effect.** Content outlives its discounted source (Kumkale & Albarracín 2004).
  - **Illusory truth.** Repetition raises judged truth even when people know better (Fazio et al. 2015).
  - **Salience distorts source.** Later salience retroactively strengthens memory for related earlier items (Dunsmoor, Murty, Davachi & Phelps, Nature 2015), and a follow-up found this also distorts source attribution (Learning & Memory 2021).
- **People rewrite their past beliefs.** Consistency bias makes past attitudes seem closer to current ones (Goethals & Reckman 1973). Hindsight bias produces "knew it all along" (Fischhoff 1975).
- **AI as a source of false memories.** Chan, Pataranutaporn, Suri, Zulfikar, Maes & Loftus (2024; N = 200) found that a generative LLM interviewer induced more than three times the immediate false memories of the control, and about 1.7 times those of a survey with the same misleading questions. The false memories persisted at one week, held with higher confidence than in the control.
- **Design relevance.** This is the clearest "do NOT mirror" area. The external system's distinctive value is what the brain cannot do:
  - provenance that does not decay;
  - a belief history the present cannot rewrite;
  - counting independent sources rather than exposures.

  A system that narrates your past beliefs back in fluent prose is a suggestive interviewer.

### 12. Offloading is a trade, not a harm, and the Google effect is weaker than its fame

- **The extended mind** (Clark & Chalmers 1998). An external resource such as Otto's notebook is part of cognition when it is:
  - reliably available,
  - readily accessed,
  - automatically endorsed,
  - and its contents were previously endorsed.
- **Transactive memory** (Wegner 1987). Groups remember through a shared directory of who knows what, and the key individual knowledge is the directory.
- **Replication record.** Sparrow, Liu & Wegner (Science 2011) is widely cited for "expected access lowers recall."
  - Its Experiment 1, the "Google Stroop" priming result, failed in the Social Science Replication Project (Camerer et al., Nature Human Behaviour 2018), and again in a 2020 replication that followed the original authors' protocol feedback (PeerJ).
  - Its other findings were not part of that replication.
  - The saving effect reportedly appears only when people trust that saved information stays available (Schooler & Storm; via a secondary source).
- **Real benefits.** Saving one file before studying the next improves learning of the next ("saving-enhanced memory," Storm & Stone 2015).
- **Real costs.** Offloading boosts performance while reducing memory for the offloaded content (Grinschgl et al. 2021; review in Risko & Gilbert 2016).
- **Design relevance.** Decide which knowledge should be internalized and which only findable, and keep an accurate directory of the difference.

### 13. LLM offloading (2024-2026): using the tool improves performance but not learning, unless the interaction forces generation

**Performance improved while learning did not:**

- **Bastani et al. (PNAS 2025).** In a field experiment with roughly 1,000 high-school math students:
  - Unrestricted GPT-4 raised practice grades 48%.
  - After access was removed, exam grades were 17% lower than those of students who never had access.
  - A version with tutoring guardrails raised practice grades 127% and largely removed the harm.
- **Melumad & Yun (PNAS Nexus 2025; 7 experiments, n = 10,462).** Learning a topic from LLM syntheses produced shallower knowledge than learning from web links, even with the same facts and with links attached. The mechanism they propose: the LLM does the discovery and synthesis steps that create depth.
- **Kreijkes et al. (Computers & Education 2025).** In a preregistered RCT with 405 students aged 14-15, note-taking, alone or combined with an LLM, beat LLM-only use on retention and comprehension at three days. Students nonetheless preferred the LLM.
- **Kosmyna et al. (arXiv 2025).** In 54 participants, EEG connectivity scaled down with tool support, and LLM users could not quote essays they had just written as well as others. The sample is small and the work is not peer reviewed, so I treat it as suggestive.

**Confidence and critical thinking:**

- **Lee et al. (CHI 2025; 319 workers, 936 tasks).** Confidence in GenAI predicted less critical thinking, while self-confidence predicted more.
- Gerlich (Societies 2025) found a negative association between AI use and critical thinking, but the study is correlational.

**Design moves the outcome:**

- **Maier, Schwabe, Schneider & Feuerriegel (arXiv preprint, September 2026; N = 704).** Metacognitive feedback that made the consequences of offloading explicit reduced answer offloading (OR 0.47) and improved later unaided test scores (OR 1.51). An effort-based reward did nothing.
- **Eleftheriou, Pallis & Constantinides (arXiv preprint 2026; n = 85).** A standard LLM baseline gave high perceived understanding with the lowest actual learning. "Future-self explanation" prompts gave the best calibration, and guided hints gave the largest gains.

**Takeaway.** The harm follows from designs in which the AI generates and the human consumes. It is not inherent to AI.

### 14. Sleep and offline replay: a good engineering metaphor with weaker human evidence than its reputation

- **Theory.** Replay is proposed to:
  - extract shared structure across memories (Lewis & Durrant 2011);
  - "triage" what gets consolidated (Stickgold & Walker 2013).
- **Evidence for relevance-selection.** Wilhelm et al. (J Neurosci 2011) found that sleep helped only memories people expected to be tested on.
- **Contradicts popular belief.** Ashton & Cairney (PLoS ONE 2021) failed in two attempts to replicate this, and other replications were also weak. Cordi & Rasch (2021) review how much less robust sleep-memory effects are than assumed. Targeted memory reactivation works on average, but modestly (Hu et al. 2020; g around 0.29, unverified).
- **What is more robust.** Retroactive salience: later significance strengthens earlier related items (Dunsmoor et al. 2015).
- **Design relevance.** A scheduled offline consolidation pass is justified computationally, by CLS and Go-CLS, not by "the brain does it during sleep." How to choose what gets consolidated is a design choice to test.

### 15. Experience is segmented into events at prediction-error boundaries

- **Mechanism.** Event segmentation theory (Zacks et al. 2007): people cut continuous experience into events where prediction error spikes, and memory is organized around these boundaries.
- **Uptake in AI.** EM-LLM (Fountas et al. 2024) applies surprise-based segmentation to LLM episodic memory.
- **Design relevance.** The capture unit for a long AI conversation should be the event (a span bounded by a shift in topic, goal or surprise), not the whole chat or a fixed-size chunk.

### Synthesis: what "coherent and evolving understanding" means mechanistically

Understanding is coherent and evolving when six conditions hold:

1. **Compressed generative structure.** A small set of principles and causal models can reconstruct specifics and predict new cases (Chi; Spens & Burgess).
2. **Indexed grounding.** Every part of that structure points to the episodes and sources that justify it, and those episodes stay retrievable so the structure can be re-derived (CLS, indexing theory, multiple-trace theory).
3. **Maintained consistency.** Conflicts are surfaced by co-activating related items, and are then either resolved or explicitly held open (KReC; Posner).
4. **Calibrated metacognition.** There is an accurate map of what is known, uncertain, contested, and held only externally (Nelson & Narens; transactive memory).
5. **Prediction-error-gated evolution.** Small mismatches revise beliefs. Accumulated anomalies trigger restructuring. One-off events are not promoted into general beliefs (reconsolidation, Posner/Chi, Go-CLS).
6. **Live use.** The person can actually explain and predict, and this is maintained by retrieval, generation and spaced use. Without it, the understanding belongs to the system, not the person.

The **creating processes** are elaboration at encoding, retrieval practice, self-explanation, interleaved comparison across episodes, confrontation of contradictions, abstraction that keeps exceptions, and demotion of what is no longer needed.

**Operational tests:**

- Is a concept applied consistently across contexts?
- Can the person explain it without looking?
- Can they predict a new case?
- Can any belief be traced to its grounds and to what it replaced?

---

## Ideas worth stealing

1. **Two-speed memory with interleaved integration** (CLS; McClelland et al. 1995).
   - An append-only fast store captures episodes immediately.
   - A separate slow, scheduled integration pass updates the semantic layer.
   - Each integration batch mixes new episodes with a sample of older related material, so the semantic layer is fitted to the whole history, not to the last session.

2. **Index, don't copy; keep verbatim and gist together** (hippocampal indexing; fuzzy-trace theory).
   - Episodic records point to the original source (transcript span, page, file) and carry context: time, project, goal, and the conversation partner, AI or human.
   - Each also has a short gist.
   - The gist is what gets reasoned over. The pointer is what makes re-interpretation possible.

3. **A congruence router** (SLIMM; Tse et al.). On ingest, score how well a new item fits existing structure.
   - High fit: attach to the existing node as supporting evidence, cheaply.
   - Low fit: create a distinct "anomaly/novel" item with full context and a visible flag. Never auto-merge it.
   - Middling fit: queue for human attention, because this is where things get lost.

4. **Prediction-error-gated revision on access** (reconsolidation boundary conditions; Sinclair & Barense 2019).
   - An existing belief is opened for revision only when it is retrieved in a context where new evidence conflicts with it.
   - The revision is recorded as an event.
   - Merely reading a belief does not mutate it.

5. **Supersession records shaped like refutation texts** (KReC; continued-influence research). A change of belief is a record with these fields:
   - old claim
   - new claim
   - what refuted the old claim
   - the causal alternative ("why the old one seemed right")
   - evidence links

   The UI shows old and new together the first few times the topic resurfaces. This makes co-activation and integration happen in the person's head, not just in the database.

6. **Generalization-gated promotion** (Go-CLS; Sun et al. 2023).
   - A pattern is promoted from episodic to semantic ("I tend to...", "X generally causes Y") only when it recurs across independent episodes, or predicts a held-out one.
   - One-off events stay episodic.
   - This directly targets spurious "themes" that LLMs find in note collections.

7. **Separate storage strength from retrieval strength** (Bjork & Bjork 1992; Anderson & Schooler 1991; ACT-R base-level activation).
   - Nothing is hard-deleted for relevance.
   - Each item carries an activation that decays with disuse and rises with retrieval, especially effortful retrieval.
   - Ranking uses activation as well as similarity.
   - "Forgetting" means demotion, and it is reversible.

8. **An anomaly ledger with a restructuring trigger** (Posner et al. 1982; Chi 2008; Carey 2009).
   - Each schema or model node accumulates the anomalies that do not fit it.
   - Past a threshold, the system proposes a restructuring session (split, re-categorize, replace the model) instead of more piecemeal patches.
   - Restructurings are versioned, so the old structure is still inspectable.

9. **Retroactive tagging** (behavioral tagging; Dunsmoor et al. 2015). When something becomes salient, older related fragments are retroactively re-scored and resurfaced. Examples: a new goal, a decision, a surprising failure. This is how a scrap from eight months ago becomes relevant today.

10. **Belief time-series and decision snapshots** (anti-consistency-bias and anti-hindsight-bias).
    - Beliefs carry a dated history of stance and confidence.
    - Decisions capture, at the time, what was believed, the options, the expected outcomes, and the confidence.
    - Neither can be edited after the fact; they can only be annotated.

11. **Provenance with independence counting** (source monitoring; illusory truth). Every claim records:
    - origin type: own reasoning, AI conversation, reading, direct observation, or another person;
    - the chain of where it came from;
    - how many independent sources support it.

    Repeated AI restatements of the same claim count as one source. Beliefs whose only support is AI conversation are visibly flagged.

12. **Generation-first interaction** (testing effect, generation effect, self-explanation; GPT Tutor in Bastani et al.; Maier et al. 2026). Before the system shows its synthesis on a topic the person cares about internalizing, it asks for one of:
    - a prediction,
    - a recall attempt,
    - a one-line explanation.

    It then shows the comparison: "you said / your notes say / sources say." The friction is a single short prompt, and the comparison itself is the feedback.

13. **Calibration probes** (illusion of explanatory depth; hypercorrection). Occasionally ask "explain X without looking" for items the person rated as known. Prioritize high-confidence items that have accumulated conflicting evidence, since correcting those gives the largest payoff.

14. **Event-boundary segmentation of captures** (event segmentation theory; EM-LLM). Cut AI conversations and long work sessions into events at shifts in topic, goal or surprise. Each event is the unit of capture, provenance and citation.

15. **A transactive directory** (Wegner 1987; Ward 2021).
    - The system keeps a map of what the person has internalized (it passes recall probes) versus what is only stored externally.
    - The person can see the map.
    - It gives the person an accurate "I know where, not what" and counters the illusion that the system's knowledge is their own.

---

## Pitfalls and anti-patterns

1. **Capture as learning.** Collecting highlights, clippings, chat logs and AI summaries feels productive, but these are the techniques rated lowest in Dunlosky et al. (2013). They also show the LLM-only pattern of Kreijkes et al. (2025): preferred by users, worse for retention. In the PKM community this is known as the "collector's fallacy." A system whose main loop is ingest-and-organize will produce a large, tidy archive and little understanding.

2. **Overwrite-on-update.** Silently replacing an outdated note destroys the record of what was believed, and KReC and continued-influence research show it does not update the person anyway. The old belief persists in memory and later resurfaces, while the system now claims something the person does not fully hold.

3. **Summarize-and-discard.** Replacing episodes with LLM summaries reproduces Spens & Burgess's generative-consolidation distortion: content regresses toward the prior, idiosyncratic detail is lost, and the loss grows with each re-summarization. Once the original is gone, nothing can be re-interpreted.

4. **Consolidate everything.** Go-CLS shows that indiscriminate consolidation of a noisy world overfits. In this context, that means an LLM inventing "recurring themes," "your core values" or "patterns in your thinking" from coincidences. These summaries are flattering and plausible, and they may be false.

5. **Forced coherence, or the synthetic model.** Asking an LLM to reconcile two contradictory notes produces a hybrid that neither supports, the analogue of Vosniadou's "hollow-earth" children. Contradictions that are not yet resolved are information, not dirt.

6. **Fluency read as understanding.** Polished, always-available, coherent text inflates felt knowledge (Fisher et al. 2015; Ward 2021; Eleftheriou et al. 2026) and reduces depth (Melumad & Yun 2025). A system that makes the person feel smarter is not evidence that it made them smarter. Evaluations based on satisfaction or perceived usefulness are therefore actively misleading.

7. **Neuroscience as justification.** Several famous mechanisms are weaker than their reputation:
   - human reconsolidation-based memory erasure (failed registered replication, Chalkia et al. 2020);
   - sleep selectively consolidating future-relevant memories (failed replications, Ashton & Cairney 2021);
   - the Google-Stroop effect (failed replication, Camerer et al. 2018);
   - the Zeigarnik effect for unfinished tasks, which a recent meta-analysis reportedly did not support (unverified).

   Brain analogies are useful as engineering hypotheses. They are not evidence that a design will work.

8. **Retrieval monoculture.** Similarity-based retrieval that keeps surfacing the same top-k items produces retrieval-induced-forgetting-like effects in both the person and the ranking. Neglected but relevant knowledge decays in accessibility. Countermeasures: diversity in retrieval, and integration links that make related items support each other rather than compete.

9. **The AI as suggestive interviewer.** Chan et al. (2024) showed that LLM conversation can implant persistent, confident false memories. A system that asks leading questions about past events, or narrates "as you concluded last spring...", can rewrite the person's autobiographical record. Past beliefs should be shown as quoted, dated, sourced records, not paraphrased narrative.

10. **Topic-folder taxonomies.** Organizing by subject is novice surface organization (Chi et al. 1981). It hides the cross-cutting principles and questions that make knowledge transferable.

11. **Designing for automatic endorsement.** Clark & Chalmers' criteria describe when an external store becomes part of cognition. "Automatically endorsed" is exactly what Lee et al. (2025) associate with less critical thinking when confidence in the AI is high. The system should earn trust through visible provenance and status. It should not simply accumulate trust.

---

## Implications for this project

Each implication is stated so it can be built and, where possible, tested.

1. **Separate the layers by update rule.** The data model needs at least three layers:
   - an append-only episodic/source layer, never edited;
   - a revisable semantic layer of claims, beliefs, models, decisions, goals and questions, where every change is a versioned event;
   - a metacognitive layer covering confidence, status (held, tentative, contested, superseded), open contradictions, and internalized-versus-external.

   *Test:* for a random sample of 20 claims, the system can answer "what did I believe about X on date D, and why" in a way that matches a manual audit of the sources in at least 90% of cases.

2. **Make integration a scheduled, interleaved, gated pass, not a write-on-ingest.** Ingest only writes episodes and lightweight attachments. A periodic consolidation job proposes semantic changes, sampling old related material with the new. Promotion of generalizations requires at least two independent episodes.

   *Test:* run gated and ungated consolidation on the same 4-8 weeks of real data. The person blind-rates proposed generalizations. The prediction is that the gated version has a substantially lower rate of "false or unsupported" ratings.

3. **Treat contradictions as first-class objects that are never auto-resolved.** The LLM may detect and describe a conflict and propose resolutions. Resolution requires evidence or the person's decision.

   *Test:* ask an LLM consolidation step to merge known-contradictory note pairs, and count synthetic blends (outputs both sources would reject). If the rate is non-trivial, as I expect, this confirms the rule.

4. **Make the belief update primitive a supersession record** (old, new, refuter, causal alternative, evidence). Show it with co-activation on the next few retrievals.

   *Test (self-experiment):* one week after a belief changes, check whether the person states the current belief and the reason more accurately when the change was recorded as a refutation-style record than as a plain replacement.

5. **Never hard-delete for relevance; rank with activation.** Use an ACT-R-style base-level activation (recency × frequency of use) blended with semantic similarity, plus deliberate diversity in what gets resurfaced.

   *Test:* on held-out real queries, compare blended ranking with pure embedding similarity, using the person's relevance judgments.

6. **Make the human-facing loop generation-first for anything marked "want to know," not just "want to find."**

   *Test:* this is the core human-side evaluation. Compare items engaged via predict-then-compare with items engaged via reading the AI synthesis, on unaided explanation one week later. Bastani, Kreijkes and Melumad & Yun predict a measurable gap in favor of predict-first. If no gap appears, the friction is not earning its cost.

7. **Store provenance and independence on every claim, and flag "AI-only" beliefs.**

   *Test:* before revealing provenance, ask the person where they got a sample of beliefs. Measure their source-attribution accuracy. This is a source-amnesia baseline, and the system's value is the size of that gap.

8. **Evaluate the person, not just the system.** Metrics must include:
   - calibration (stated confidence versus performance on self-explanation probes);
   - explanation quality without the system;
   - belief-change traceability.

   System-only metrics such as retrieval precision and user satisfaction can rise while understanding falls. This is the central lesson of the 2024-2026 LLM evidence.

9. **Organize around questions, principles and models, not topics.** The primary semantic units should be "questions I'm working on," "models I hold," "decisions," and "goals," with topics as secondary tags. Human views show about 4-7 chunks with drill-down. The AI-facing projection can be dense, but it must carry status, confidence, provenance and open contradictions, because an AI that cannot tell held from contested will repeat superseded beliefs back as fact.

10. **Capture AI conversations as segmented events**, cut at topic, goal or surprise shifts, each with a gist, a pointer to the source span, and the conversational role: user claim, AI claim, or jointly reasoned.

11. **Make restructuring operations first-class and versioned:** split concept, merge, re-categorize, replace model. An anomaly count per model node triggers a restructuring proposal.

    *Test:* at least one real restructuring happens within the first months of use, and it can later be inspected (before and after, and why).

12. **Use one underlying record and two projections, but let the human author their own key representations.** The AI projection optimizes for completeness, provenance and explicit uncertainty. The human projection optimizes for chunking, the person's own wording, and prompts that elicit generation. At least the person's explanations of their core models should be written by the person, with AI drafts treated as scaffolds. Otherwise the generation effect is lost and the person's model and the system's model silently diverge.

---

## Tensions and open questions

1. **Internalize or offload?** Offloading frees capacity (Storm & Stone 2015) and is rational for look-up knowledge. It harms learning for knowledge one needs to reason with (Bastani; Kreijkes; Melumad & Yun). Open questions: who decides each item's "know vs. find" status, the person or the system by usage? And can that status change automatically?

2. **Friction versus adoption.** The effective techniques feel worse (Kornell & Bjork 2008; Kreijkes et al. 2025, where students preferred the LLM). A generation-first system risks abandonment. What is the minimum effective friction? Maier et al. (2026) suggest metacognitive feedback ("here is what offloading costs you") may beat both forced effort and rewards. That needs testing in this setting.

3. **Whose model is the semantic layer?** It could be a mirror of what the person actually believes, including half-retracted beliefs, or a record of what the evidence in the store supports. These diverge: per KReC and continued influence, the person still half-holds superseded beliefs. The project probably needs both, as "my stance" versus "evidence state," and a way to show the gap without being preachy.

4. **AI consolidation versus human consolidation.** AI consolidation scales and catches cross-episode connections the person would miss. It also removes the generative work that builds understanding, and it introduces generative distortion. Where is the line? A candidate rule: the AI does bookkeeping (detection, linking, provenance, scheduling, conflict surfacing), and the human does meaning-making (explanations, resolutions, restructurings). This is a hypothesis, not a finding.

5. **Should the system ever truly forget?** Immutable history defeats hindsight bias and enables re-interpretation. But people also need to outgrow old selves, and privacy matters. Demotion may be enough, or explicit, user-initiated deletion of some kinds of content may be needed.

6. **What counts as an independent source** when much input flows through LLMs that themselves summarize the same web? Independence counting may need source-lineage heuristics that are hard to get right.

7. **Granularity.** Is the unit of semantic knowledge a claim, a model, a question, or a page? Chi's categorical shifts and Carey's incommensurability suggest that models, not claims, are what change in deep learning. But claims are what can be tracked and cited. The design may need both, with explicit containment.

8. **Restructuring thresholds.** How many anomalies justify proposing a restructure? Too eager produces churn. Too lax produces Ptolemaic epicycles. This is unknown and needs empirical tuning.

9. **The evaluation horizon.** Learning, calibration and belief-evolution effects show up over weeks to months. A practical prototype needs proxy metrics usable within days, such as one-week delayed explanation probes, without mistaking proxies for the target.

10. **Is coherence even the goal for every domain?** diSessa's work suggests some useful knowledge stays context-bound and fragmentary even in experts. Forcing every domain into a coherent model may be its own error. The system should be able to hold "I have several partial views here, and they don't yet fit."

11. **Recapping the person's past without implanting false memories** (Chan et al. 2024). Presenting history as quoted, dated records is safer than narrative, but less pleasant to read. How to balance faithfulness with readability is a UX question with an epistemic cost.

---

## Sources

Verified against a web source during this research:

- Bastani, H., Bastani, O., Sungu, A., Ge, H., Kabakcı, Ö., & Mariman, R. (2025). Generative AI without guardrails can harm learning: Evidence from high school mathematics. *PNAS* 122. https://papers.ssrn.com/abstract=4895486 ; summary: https://knowledge.wharton.upenn.edu/article/without-guardrails-generative-ai-can-harm-education/ (author list beyond Bastani from memory, unverified)
- Melumad, S., & Yun, J. H. (2025). Experimental evidence of the effects of large language models versus web search on depth of learning. *PNAS Nexus*. https://scale.stanford.edu/ai/repository/experimental-evidence-effects-large-language-models-versus-web-search-depth-learning
- Kreijkes, P., Kewenig, V., Kuvalja, M., Lee, M., Hofman, J., Vitello, S., Sellen, A., Rintel, S., Goldstein, D. G., Rothschild, D., Tankelevitch, L., & Oates, T. (2025). Effects of LLM use and note-taking on reading comprehension and memory: A randomised experiment in secondary schools. *Computers & Education* 243. https://www.microsoft.com/en-us/research/publication/effects-of-llm-use-and-note-taking-on-reading-comprehension-and-memory-a-randomised-experiment-in-secondary-schools/
- Kosmyna, N., et al. (2025). Your Brain on ChatGPT: Accumulation of Cognitive Debt when Using an AI Assistant for Essay Writing Task. arXiv:2506.08872. https://arxiv.org/abs/2506.08872
- Lee, H.-P., Sarkar, A., Tankelevitch, L., Drosos, I., Rintel, S., Banks, R., & Wilson, N. (2025). The Impact of Generative AI on Critical Thinking. *CHI '25*. https://advait.org/files/lee_2025_ai_critical_thinking_survey.pdf
- Maier, S., Schwabe, K., Schneider, M., & Feuerriegel, S. (2026). Designing Against Deskilling: Metacognitive Feedback Reduces Cognitive Offloading to LLM Assistants. arXiv:2609.20143 (preprint). https://arxiv.org/abs/2609.20143
- Eleftheriou, E., Pallis, G., & Constantinides, M. (2026). Confidence Without Competence in AI-Assisted Knowledge Work. arXiv:2604.09444 (preprint). https://arxiv.org/abs/2604.09444
- Chan, S., Pataranutaporn, P., Suri, A., Zulfikar, W., Maes, P., & Loftus, E. F. (2024). Conversational AI Powered by Large Language Models Amplifies False Memories in Witness Interviews. arXiv:2408.04681. https://arxiv.org/abs/2408.04681
- Spens, E., & Burgess, N. (2024). A generative model of memory construction and consolidation. *Nature Human Behaviour*. https://discovery.ucl.ac.uk/id/eprint/10186145/
- Sun, W., Advani, M., Spruston, N., Saxe, A., & Fitzgerald, J. E. (2023). Organizing memories for generalization in complementary learning systems. *Nature Neuroscience*. https://pmc.ncbi.nlm.nih.gov/articles/PMC10400413/
- Tse, D., et al. (2007). Schemas and memory consolidation. *Science* 316. https://www.research.ed.ac.uk/en/publications/schemas-and-memory-consolidation/
- van Kesteren, M. T. R., Ruiter, D. J., Fernández, G., & Henson, R. N. (2012). How schema and novelty augment memory formation. *Trends in Neurosciences* 35(4), 211-219. https://www.mrc-cbu.cam.ac.uk/personal/rik.henson/personal/VanKesterenEtAl_12_TINS_schema_novelty_memory.pdf
- Yacoby, A., Greve, A., Schaverien, E., Shtoots, L., Henson, R. N., & Levy, D. A. (2026). Dissociable effects of schema congruency on item recognition and source memory across levels of expectedness and surprise. *Memory & Cognition*. https://www.mrc-cbu.cam.ac.uk/wp-content/uploads/www/sites/3/2026/09/Yacoby-et-al.-2026-Dissociable-effects-of-schema-congruency-on-item-recognition-and-source-memory-across-levels-of-expe.pdf (summary via search; full text not parsed)
- Chalkia, A., et al. (2020). No persistent attenuation of fear memories in humans: A registered replication of the reactivation-extinction effect. *Cortex* 129, 496-509. https://pmc.ncbi.nlm.nih.gov/articles/PMC7115861
- Ward, A. F. (2021). People mistake the internet's knowledge for their own. *PNAS* 118(43). https://pmc.ncbi.nlm.nih.gov/articles/PMC8612631
- Fisher, M., Goddu, M. K., & Keil, F. C. (2015). Searching for explanations: How the Internet inflates estimates of internal knowledge. *Journal of Experimental Psychology: General* 144(3). https://www.sciencedaily.com/releases/2015/08/150812165920.htm (news summary)
- Sparrow, B., Liu, J., & Wegner, D. M. (2011). Google effects on memory. *Science* 333. Replication record: https://forrt.org/flora-replication-atlas/doi/10.1126/science.1207745/ ; https://peerj.com/articles/10325 ; overview incl. Schooler & Storm and a 2024 meta-analysis: https://en.wikipedia.org/wiki/Google_effect ; https://www.mcgill.ca/oss/article/critical-thinking-technology/digital-amnesia-has-been-exaggerated
- Camerer, C. F., et al. (2018). Evaluating the replicability of social science experiments in Nature and Science between 2010 and 2015. *Nature Human Behaviour* 2, 637-644.
- Wilhelm, I., Diekelmann, S., Molzow, I., Ayoub, A., Mölle, M., & Born, J. (2011). Sleep selectively enhances memory expected to be of future relevance. *Journal of Neuroscience* 31(5), 1563-1569. https://pubmed.ncbi.nlm.nih.gov/21289163/
- Ashton, J. E., & Cairney, S. A. (2021). Future-relevant memories are not selectively strengthened during sleep. *PLoS ONE*. https://pmc.ncbi.nlm.nih.gov/articles/PMC8568116/
- Cordi, M. J., & Rasch, B. (2021). How robust are sleep-mediated memory benefits? *Current Opinion in Neurobiology* 67, 1-7. https://pmc.ncbi.nlm.nih.gov/articles/PMC8361329
- Dunsmoor, J. E., Murty, V. P., Davachi, L., & Phelps, E. A. (2015). Emotional learning selectively and retroactively strengthens memories for related events. *Nature* 520. https://sites.utexas.edu/dunsmoorlab/files/2017/07/2015-Nature-Dunsmoor-Murty-Davachi-Phelps.pdf
- (2021). Emotional learning retroactively enhances item memory but distorts source attribution. *Learning & Memory* 28(6), 178. https://learnmem.cshlp.org/content/28/6/178.short (authors unverified)
- Richards, B. A., & Frankland, P. W. (2017). The persistence and transience of memory. *Neuron* 94(6). https://neurosciencenews.com/forgetting-smarter-6947/ (news summary)
- Kendeou, P., & O'Brien, E. J. (2014). The Knowledge Revision Components (KReC) framework. In Rapp & Braasch (Eds.), *Processing Inaccurate Information*. MIT Press. Overview: https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2023.1112804
- Anderson, M. C., Bjork, R. A., & Bjork, E. L. (1994). Remembering can cause forgetting. *JEP: Learning, Memory, and Cognition* 20. Overview: https://en.wikipedia.org/wiki/Retrieval-induced_forgetting

From knowledge, not re-verified this session (standard, widely cited works):

- McClelland, J. L., McNaughton, B. L., & O'Reilly, R. C. (1995). Why there are complementary learning systems in the hippocampus and neocortex. *Psychological Review* 102(3).
- Kumaran, D., Hassabis, D., & McClelland, J. L. (2016). What learning systems do intelligent agents need? Complementary learning systems theory updated. *Trends in Cognitive Sciences* 20(7).
- Teyler, T. J., & DiScenna, P. (1986). The hippocampal memory indexing theory. *Behavioral Neuroscience* 100(2).
- Nadel, L., & Moscovitch, M. (1997). Memory consolidation, retrograde amnesia and the hippocampal complex. *Current Opinion in Neurobiology* 7. Winocur, G., & Moscovitch, M. (2011). Memory transformation and systems consolidation. *JINS* 17.
- Reyna, V. F., & Brainerd, C. J. (1995). Fuzzy-trace theory: An interim synthesis. *Learning and Individual Differences* 7.
- Nader, K., Schafe, G. E., & LeDoux, J. E. (2000). Fear memories require protein synthesis in the amygdala for reconsolidation after retrieval. *Nature* 406.
- Sinclair, A. H., & Barense, M. D. (2019). Prediction error and memory reactivation: How incomplete reminders drive reconsolidation. *Trends in Neurosciences* 42(10).
- Lee, J. L. C., Nader, K., & Schiller, D. (2017). An update on memory reconsolidation updating. *Trends in Cognitive Sciences* 21(7).
- Johnson, H. M., & Seifert, C. M. (1994). Sources of the continued influence effect. *JEP: LMC* 20. Lewandowsky, S., Ecker, U. K. H., et al. (2012). Misinformation and its correction. *Psychological Science in the Public Interest* 13(3). Ecker, U. K. H., et al. (2022). The psychological drivers of misinformation belief and its resistance to correction. *Nature Reviews Psychology* 1.
- Posner, G. J., Strike, K. A., Hewson, P. W., & Gertzog, W. A. (1982). Accommodation of a scientific conception. *Science Education* 66(2).
- Chi, M. T. H. (2008). Three types of conceptual change. In S. Vosniadou (Ed.), *International Handbook of Research on Conceptual Change*. Chi, M. T. H., Feltovich, P. J., & Glaser, R. (1981). Categorization and representation of physics problems by experts and novices. *Cognitive Science* 5. Chi, M. T. H., et al. (1989). Self-explanations. *Cognitive Science* 13.
- Carey, S. (2009). *The Origin of Concepts*. Oxford University Press.
- Vosniadou, S., & Brewer, W. F. (1992). Mental models of the earth. *Cognitive Psychology* 24. diSessa, A. A. (1993). Toward an epistemology of physics. *Cognition and Instruction* 10.
- Bjork, R. A., & Bjork, E. L. (1992). A new theory of disuse and an old theory of stimulus fluctuation. In *From Learning Processes to Cognitive Processes*. Bjork, R. A. (1994). Memory and metamemory considerations in the training of human beings.
- Anderson, J. R., & Schooler, L. J. (1991). Reflections of the environment in memory. *Psychological Science* 2(6).
- Roediger, H. L., & Karpicke, J. D. (2006). Test-enhanced learning. *Psychological Science* 17(3).
- Slamecka, N. J., & Graf, P. (1978). The generation effect. *JEP: Human Learning and Memory* 4.
- Dunlosky, J., Rawson, K. A., Marsh, E. J., Nathan, M. J., & Willingham, D. T. (2013). Improving students' learning with effective learning techniques. *Psychological Science in the Public Interest* 14(1).
- Cepeda, N. J., et al. (2006). Distributed practice in verbal recall tasks. *Psychological Bulletin* 132(3).
- Kornell, N., & Bjork, R. A. (2008). Learning concepts and categories: Is spacing the "enemy of induction"? *Psychological Science* 19(6). Karpicke, J. D., Butler, A. C., & Roediger, H. L. (2009). Metacognitive strategies in student learning. *Memory* 17(4).
- Kintsch, W. (1988). The role of knowledge in discourse comprehension: A construction-integration model. *Psychological Review* 95. McNamara, D. S., Kintsch, E., Songer, N. B., & Kintsch, W. (1996). Are good texts always better? *Cognition and Instruction* 14.
- Chase, W. G., & Simon, H. A. (1973). Perception in chess. *Cognitive Psychology* 4. Ericsson, K. A., & Kintsch, W. (1995). Long-term working memory. *Psychological Review* 102. Cowan, N. (2001). The magical number 4 in short-term memory. *Behavioral and Brain Sciences* 24. Kalyuga, S., Ayres, P., Chandler, P., & Sweller, J. (2003). The expertise reversal effect. *Educational Psychologist* 38.
- Nelson, T. O., & Narens, L. (1990). Metamemory: A theoretical framework and new findings. Koriat, A. (1993). How do we know that we know? *Psychological Review* 100. Rozenblit, L., & Keil, F. (2002). The misunderstood limits of folk science: An illusion of explanatory depth. *Cognitive Science* 26.
- Butterfield, B., & Metcalfe, J. (2001). Errors committed with high confidence are hypercorrected. *JEP: LMC* 27.
- Johnson, M. K., Hashtroudi, S., & Lindsay, D. S. (1993). Source monitoring. *Psychological Bulletin* 114. Kumkale, G. T., & Albarracín, D. (2004). The sleeper effect in persuasion: A meta-analytic review. *Psychological Bulletin* 130. Fazio, L. K., Brashier, N. M., Payne, B. K., & Marsh, E. J. (2015). Knowledge does not protect against illusory truth. *JEP: General* 144.
- Goethals, G. R., & Reckman, R. F. (1973). The perception of consistency in attitudes. *JESP* 9. Fischhoff, B. (1975). Hindsight ≠ foresight. *JEP: HPP* 1.
- Clark, A., & Chalmers, D. (1998). The extended mind. *Analysis* 58(1). Wegner, D. M. (1987). Transactive memory. In *Theories of Group Behavior*. Hutchins, E. (1995). *Cognition in the Wild*.
- Risko, E. F., & Gilbert, S. J. (2016). Cognitive offloading. *Trends in Cognitive Sciences* 20(9). Storm, B. C., & Stone, S. M. (2015). Saving-enhanced memory. *Psychological Science* 26(2). Grinschgl, S., Papenmeier, F., & Meyerhoff, H. S. (2021). Consequences of cognitive offloading. *Quarterly Journal of Experimental Psychology* 74(9).
- Gerlich, M. (2025). AI tools in society: Impacts on cognitive offloading and the future of critical thinking. *Societies* 15(1), 6 (correlational).
- Lewis, P. A., & Durrant, S. J. (2011). Overlapping memory replay during sleep builds cognitive schemata. *Trends in Cognitive Sciences* 15(8). Stickgold, R., & Walker, M. P. (2013). Sleep-dependent memory triage. *Nature Neuroscience* 16. Hu, X., Cheng, L. Y., Chiu, M. H., & Paller, K. A. (2020). Promoting memory consolidation during sleep: A meta-analysis of targeted memory reactivation. *Psychological Bulletin* 146(3) (effect size from memory).
- Zacks, J. M., Speer, N. K., Swallow, K. M., Braver, T. S., & Reynolds, J. R. (2007). Event perception: A mind-brain perspective. *Psychological Bulletin* 133. Fountas, Z., et al. (2024). Human-like episodic memory for infinite context LLMs (EM-LLM). arXiv:2407.09450 (venue unverified).
- Bartlett, F. C. (1932). *Remembering*. Cambridge University Press.
