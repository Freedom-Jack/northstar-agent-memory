# Personal knowledge management in practice: what works, what fails, and why

Track 02. Research note, 2026-10-07.

Method note: this was written from prior knowledge plus web verification. WebSearch ran out of budget partway through, so later checks used WebFetch on known URLs only. Claims I could not re-check are marked "(unverified)" or "(from memory)". Where a source is a secondary blog or aggregator, I say so.

---

## Scope and questions

This track covers what real people have done to manage personal knowledge, and what the evidence says about why those systems succeed or fail. It covers commonplace books, Luhmann's Zettelkasten, Matuschak's evergreen notes, Forte's Building a Second Brain, the networked-notes tools (Roam, Obsidian, Logseq, Tana, Notion, Heptabase, Capacities, Reflect, Mem, Readwise), spaced repetition (SuperMemo, Anki, the mnemonic medium), digital gardens and lab notebooks. It then covers the failure literature and the AI features that PKM tools shipped in 2024-2026.

The questions:

1. **What actually turns fragments into understanding for real people?** Which mechanism does it, as opposed to which ritual or which tool?
2. **What predicts sustained use and what predicts abandonment?**
3. **What did AI features in PKM tools change, and did they help?**
4. **What does this mean for a system that has to serve both a person and AI agents over years?**

A note on evidence quality. The PKM field has a lot of practitioner writing and very little outcome data. No study I found measures long-term abandonment of PKM tools. Most of the hard evidence comes from neighbouring fields: personal information management (PIM) field studies in HCI, learning science, and the archival study of Luhmann's actual card index. I lean on those and flag where I am reasoning from anecdote.

---

## Key findings

### 1. Luhmann's Zettelkasten worked because integration happened at write time. The popular picture of it is partly a myth.

**Mechanism.** Luhmann did not file reading notes directly. Each evening he rewrote the day's rough notes into new cards, and he read with one question in mind: how could this material be fitted into the cards he had already written? Where to put a card was decided while preparing it, and usually more than one place would have worked. Schmidt reports that Luhmann thought a note's usefulness could only be judged by relating it to other notes, often much later. So the thinking happened in the act of relating, not in the storing.

**Evidence (Schmidt 2018, from the Bielefeld archive):**
- About 90,000 cards in two collections. ZK I (1951-1962) has about 23,000 cards in 108 topical sections, with a keyword index of about 1,250 entries. ZK II (1963-1997) has about 67,000 cards under 11 top-level sections and about 100 subsections, with a keyword index of 3,200 entries.
- **Linking was sparse, not dense.** A sample count suggests about 20,000 references in ZK I and about 30,000 in ZK II. That is roughly one link per card in ZK I and one per two cards in ZK II. Much of the linking sat on "collective reference" hub cards listing up to 25 targets. This contradicts the modern reading of "densely linked atomic notes".
- **The index was a set of entry points, not a catalogue.** It typically listed one to four cards per keyword. From there, Luhmann relied on the internal links to reach everything else.
- **Structure was topical at the top and emergent below.** The top-level sections were real topics, a historical product of his 1960s interests. Below that, branches drifted away from the parent topic through insertion.
- **Fixed addresses allowed insertion anywhere.** A card's number (for example 21/3a1p5c4fB1a, up to 13 characters) fixed its position permanently. A new thought branching off card 1/1 became 1/1a and was filed between 1/1 and 1/2. Luhmann called this the collection's "capacity for internal ramification".
- **History was never deleted.** Superseded cards stayed in place, and revisions were added as new cards. Schmidt calls the collection Luhmann's "intellectual autobiography".
- **Upkeep was heavy and ongoing.** Luhmann regularly added back-references to old cards when new cards made them necessary. He rebuilt the ZK II keyword index four times when its alphabetical order became too messy.
- **Poorly linked regions went dead.** Schmidt describes "black holes": poorly linked parts of the file stayed isolated and faded, and some small sections appear untouched since they were written.

**Myths to drop.** The fleeting / literature / permanent note taxonomy comes from Sönke Ahrens (2017), not Luhmann. Strict atomicity, dense linking and the absence of topics are not what the archive shows. One more claim is plausible but unverified: Luhmann apparently made fewer cards in later years and wrote more directly in manuscripts. It traces to Schmidt via a forum thread.

**Sources:** Schmidt 2018 (Sociologica 12(1)); Luhmann 1981; Zettelkasten forum thread.

### 2. Organizing in advance mostly does not pay off for retrieval. Navigation by recognition still matters.

**Mechanism.** Filing is a bet that you will look for something along the dimension you filed it under. Search and threading postpone that decision until you are actually looking, when you know what you need.

**Evidence.**
- Whittaker et al. (CHI 2011) instrumented an email client for 345 long-term users and 85,000+ refinding actions. Heavy filers were no more successful at refinding than light filers, and their preparatory filing was inefficient. Search and threading were more effective.
- Bergman & Whittaker (2016, MIT Press) report the counterweight. People still prefer navigating folders for their own files. Navigation uses recognition and location memory, and a self-made structure carries the user's own context. They propose a "user-subjective" approach: personal information should be organized around the user's own projects and context.

**Reconciliation.** People should not be required to organize up front. When they do browse, they need recognizable, self-meaningful landmarks. Search handles "I know what I want". Navigation handles "show me my world".

### 3. Most notes are write-only. Capture is fast and terse, and revision is rare.

**Mechanism.** Capture has an immediate payoff (relief from the fear of losing something). Revisiting has a delayed and uncertain one. Without a reason to come back, notes are not touched again.

**Evidence.**
- Van Kleek et al. ("Note to Self", CHI 2009 venue from memory) ran a 10-day study of 42 users of the List.it notes tool.
  - 50% of notes were captured in 10 seconds or less. The median note was 7 words.
  - **75% of notes were never edited after capture.** Most edits that did happen were typos or emphasis.
  - Only 28% were deleted.
  - Users self-reported that 34% of notes were intentionally re-found at least once.
- Caveats: the study was short and 69% of the notes were to-dos. It is evidence about raw capture behaviour, not long-term knowledge work.
- Bernstein et al. (2008, ACM TOIS) on "information scraps" makes the same point at larger scale. A lot of personal information escapes structured tools because the cost of putting it into them is too high at the moment of capture.

### 4. Collecting is not learning. The techniques people enjoy most are the least effective.

**Mechanism.** Saving, highlighting and rereading feel like progress and produce visible artifacts, but they need little generative processing. Retrieval, self-explanation and spacing need effort, and they are what produce durable understanding.

**Evidence.**
- Tietze's "Collector's Fallacy" (zettelkasten.de, 2014) names the confusion between knowing *about* something and knowing it. He notes that copying and bookmarking are rewarded immediately. His remedy is short research cycles: collect for a time-boxed period, then process everything before collecting more.
- From learning science (Dunlosky et al. 2013, *Psychological Science in the Public Interest*, from memory):
  - Practice testing and distributed practice rate as high utility.
  - Highlighting, rereading and summarization rate as low utility. Summarization is low partly because people summarize badly without training.
  - Elaborative interrogation and self-explanation rate as moderate.
- Matuschak's evergreen-notes stance applies this to note systems. He says "better note-taking" misses the point and that what matters is better thinking. He also observes that most people take only transient notes.

**Contradiction with popular belief.** Readwise-style highlight pipelines and Forte's Layer 2-3 bolding and highlighting are, mechanically, the low-utility end of the evidence base. Their defensible use is *wayfinding* (finding a note again later), not learning.

### 5. Spaced repetition works well for those who keep doing it. Adherence and card-writing skill are the bottleneck.

**Mechanism.** Reviewing at expanding intervals turns forgetting into a scheduled, cheap maintenance cost. Nielsen (2018) estimates 4-7 minutes of total review time per card over 20 years, and puts it as "Anki makes memory a choice".

**Evidence.**
- Quantum Country, the "mnemonic medium" with review prompts embedded in an essay:
  - Once a reader had shown 5 days of retention on a question, the median reader's accuracy from then on was about 95%.
  - The 53 readers who reviewed every card for a full year did a median of about 463 reviews, with lapses under about 2% of repetitions.
  - These are self-selected survivors. The numbers show the method works *conditional on continuing*.
- Matuschak & Nielsen (2019) say people often abandon Anki claiming it "doesn't work". The usual causes are poorly written questions and missing motivation. Writing good cards is a hard skill.
- Nielsen warns about "orphan" questions that are not tied to a real interest; these decay. He also advises qualifying claims by attributing them to their source, rather than memorizing contested statements as fact.
- Wozniak's SuperMemo "incremental reading" (from memory) goes further. It is a priority queue across many articles. You extract passages, turn extracts into cloze items over time, and let low-priority material slip. Overload is handled by prioritization rather than by trying to finish.
- Anki added the FSRS scheduler in 23.10 (2023, from memory).
- In February 2026, Damien Elmes announced that Anki's stewardship would pass to AnkiHub, citing burnout from years of solo maintenance. A one-person tool for long-term memory had a bus-factor problem.

### 6. Material sticks when it is pulled in by a live question or project. Topic-sorted collections drift.

**Mechanism.** A current question supplies a criterion for relevance and a place to integrate new material. Without one, every item is "potentially useful someday", and that is the collector's fallacy again.

**Evidence (mixed strength).**
- Luhmann read with the integration question in mind (Finding 1).
- Forte's PARA (Projects, Areas, Resources, Archives) organizes by actionability rather than subject. Its argument is that topic categories have no finish line and no link to current work.
- Barreau & Nardi (1995, from memory) found people distinguish ephemeral, working and archived information. The working set is what gets used.
- Malone (1983, from memory) found that office "piles" exist because they *remind*. Filing removes the reminder.
- Nielsen's "orphan questions decay" points the same way.
- Matuschak & Nielsen argue that serious tools for thought come from an "insight-through-making loop" tied to real, demanding use.
- This is mostly practitioner and qualitative evidence, but it converges from independent directions.

### 7. Fixed taxonomies decay. Systems that last make structure cheap to rebuild.

**Mechanism.** A person's categories change faster than their content. A structure fixed in advance turns into a record of past interests, and maintaining it becomes meta-work.

**Evidence.**
- Commonplace books were organized under predetermined "heads" (loci communes) from the Erasmus tradition. Locke's 1686/1706 method replaced fixed heads with an index keyed by a word's first letter and first vowel. That gave retrieval without committing to a taxonomy (from memory; Blair 2010 is the standard history).
- Luhmann had no master table of contents. The archive's own subject overview of his collection now runs to about 150 pages. He rebuilt the index four times, and his top-level sections reflect his 1960s interests (Finding 1).
- In a small 2025 qualitative study of researchers using Obsidian (Ferreira et al., IBM Research Brazil, arXiv 2509.20187):
  - Users' intended *retrieval* strategy shaped how they organized.
  - Organization changed continually.
  - Users wanted a starting structure because a blank page was overwhelming.
  - The retrieval strategies the authors identified were search, tags and in-note links. The graph view did not appear among them.

### 8. Tools churn and companies fail. Plain files outlast apps.

**Mechanism.** A knowledge system has to outlive the tool it is kept in. Proprietary stores tie the knowledge's lifespan to one company's runway and roadmap.

**Evidence.**
- **Roam** was the 2020 breakout app. By most accounts, its development slowed from about 2021, it had performance problems on large graphs, and users left for Obsidian, Logseq and Tana. The sources here are low-quality secondary write-ups, so treat this as directional.
- **Mem** marketed itself as an AI-first, self-organizing notes app; the "self-organizing workspace" tagline is from memory. It reportedly raised a round led by the OpenAI Startup Fund in 2022 (unverified). In October 2025 it relaunched as "Mem 2.0", rebuilt from the ground up and repositioned as an "AI Thought Partner". Its 2024 review lists fixes to "lag, skipping cursors, flaky undo/redo", which implies those were the earlier user experience.
- **Obsidian** stores everything as local Markdown files. It made commercial use free in February 2025, added Bases (database-style views over the files), and shipped an official CLI in February 2026. Agents such as Claude Code can now script against a vault's link graph, backlinks and orphan notes.
- **Digital gardens** (Appleton's history of the idea) list independent ownership in open formats as one of their core patterns.

### 9. AI features in 2024-2026 moved from autocomplete to agents that act on the store. Retrieval clearly improved. Better understanding is unproven, and there is direct evidence of risk.

**What shipped:**
- **Notion 3.0** (18 September 2025) rebuilt Notion AI as Agents. They run multi-step work, keep memory as Notion pages and databases, and pull context from connected tools.
- **Mem 2.0** (October 2025) added "Heads Up", which resurfaces notes contextually, plus Deep Search and an Agentic Chat that creates and edits notes.
- **Obsidian** has no first-party AI. The community uses plugins and, increasingly, coding agents pointed at the vault, made easier by the 2026 CLI.
- **Tana** is an AI-native outliner whose "supertags" turn nodes into typed objects with fields. It had a Series A in early 2025 ($14M per an aggregator, unverified).
- **Karpathy's "llm-wiki" gist** (April 2026, verified only via secondary write-ups) became a reference pattern:
  - Three layers: immutable raw sources, a Markdown wiki written and maintained by the LLM, and a schema/instructions file.
  - Three operations: *ingest* (one source can update 10-15 pages), *query*, and *lint* (find contradictions, orphans, gaps and stale claims).
  - Commenters raised silent drift ("staleness looks like misinformation"), missing provenance, an unclear rule for which source wins in a conflict, and the question of who actually understands the material.

**What the evidence on understanding says:**
- Lee et al. (CHI 2025) surveyed 319 knowledge workers. Higher confidence in GenAI was associated with *less* self-reported critical thinking. GenAI shifted effort toward verifying and integrating outputs.
- Kosmyna et al. (MIT Media Lab, arXiv 2506.08872) is a preprint with 54 participants, and only 18 in the crossover session.
  - LLM-assisted essay writers showed the weakest neural connectivity.
  - They struggled to quote their own essays and reported the lowest sense of ownership.
  - Participants who wrote unaided first and then used the LLM did better than the reverse order.
  - Both papers are early and limited, but they point the same way: delegating synthesis lowers what the person retains.
- I found no study measuring whether AI auto-linking, auto-tagging or chat over notes improves users' understanding or how long they keep using the tool. Practitioner pieces such as Arango's "Robots in the garden" (March 2026) settle on AI as an amanuensis: tutor, connector, adversary, mapper. The AI helps the person think and does not do the thinking for them.

### 10. Abandonment is under-measured. The anecdotes are consistent: people abandon when the system replaces thinking and turns maintenance into the hobby.

**Evidence.**
- There are no rigorous abandonment rates for PKM tools. I could find no public cohort data, and vendor numbers are marketing.
- Qualitative signals are consistent:
  - Westenberg's widely shared "I Deleted My Second Brain" (June 2025) describes deleting about 10,000 notes from 7 years. The system had become "a mausoleum" of past selves. Reading had turned into extraction, and filing had deferred real reflection.
  - The "productivity porn" critique is a common practitioner label, not a study. It points at people optimizing the system, watching workflow videos and switching tools instead of producing work.
  - Inbox bankruptcy recurs: capture queues outgrow processing capacity until the user declares bankruptcy.
- **Predictors of sustained use, inferred and to be tested:**
  - A real output need: writing, research or decisions.
  - Capture cost close to zero.
  - Upkeep that piggybacks on use (Forte's "opportunistic" compression; Luhmann adding links while writing).
  - Value returned in the flow of current work.
  - Data that outlives the tool.
- **Predictors of abandonment, inferred:**
  - Upkeep that is separate from use.
  - A taxonomy that must be kept current.
  - A backlog that grows visibly.
  - A store that shows the user their past rather than helping them now.

---

## Ideas worth stealing

Concrete mechanisms, with where each one comes from.

1. **Stable addresses separate from content and position.** *Luhmann's numbering.* Every unit gets a permanent ID that never changes when it is retitled, moved or reorganized. A unit can be inserted "after" any other to continue a line of thought. AI citations and human links both depend on this.
2. **"Continues / branches from" as a first-class relation, separate from "relates to".** *Folgezettel.* It keeps trains of argument intact, which a plain graph loses. Whether this matters digitally is debated in the Zettelkasten community, so test it rather than assume it.
3. **Entry points instead of exhaustive tagging.** *Luhmann's keyword index (1-4 entries per term).* Keep a small index of *where to start* on a concept, and let links and search do the rest.
4. **Hub and structure notes, generated per question.** *Luhmann's collective-reference cards; zettelkasten.de "hubs".* With AI these can be regenerated on demand for a question instead of hand-maintained.
5. **Supersede, never overwrite.** *Luhmann kept superseded cards; lab notebooks keep dated entries, never erase, and strike through with a single line.* A revision is a new version that points at the old one, so the history of a belief stays readable.
6. **A daily integration pass.** *Luhmann's evening transcription.* Raw captures go to a holding area. A short, regular session turns them into integrated units and answers "where does this connect, and what does it change?"
7. **Read and ingest against a question.** *Luhmann's "how can this be integrated"; Tietze's short research cycles.* Ingestion should require or propose a relation to existing material or to an active question. Cap unprocessed intake with a work-in-progress limit.
8. **Opportunistic compression.** *Forte's progressive summarization.* Summarize or refine a unit only when it is revisited for real work, so upkeep piggybacks on use.
9. **Organize the working set by actionability.** *PARA; Barreau & Nardi's working vs. archived; Malone's piles as reminders.* Active projects and questions are the main context. Everything else is reached by search and links.
10. **Titles as claims or APIs.** *Matuschak's concept-oriented evergreen notes (his phrase "titles are like APIs" is from memory).* A note titled with the claim it makes is easier for humans and AI to reference and check than one titled with a topic.
11. **Epistemic status labels.** *Digital gardens (seedling / budding / evergreen); Gwern's confidence tags (from memory).* Each unit says how mature and how confident it is, which both humans and AI need.
12. **Attribute contested claims.** *Nielsen's advice to "qualify the claim".* Store "X says Y (source, date)" rather than bare Y, unless the person has adopted Y as a belief.
13. **Priority queues instead of finish-everything.** *SuperMemo incremental reading.* Overload is managed by priority and postponement, not guilt. Low-priority items are allowed to slip.
14. **Lint as a maintenance operation.** *Karpathy's llm-wiki.* A periodic pass flags contradictions, orphans, gaps and stale claims. The human decides what to do about them.
15. **Contextual resurfacing.** *Mem 2.0 "Heads Up"; Readwise daily review (from memory).* Bring back relevant prior material when the current context makes it useful, not only on a fixed schedule.
16. **Typed nodes for the few types that matter.** *Tana supertags; Capacities object types (from memory).* Decision, Belief, Question and Goal should get schemas. Most content should not.
17. **Retention prompts as an optional layer.** *Mnemonic medium.* Only for claims the person explicitly wants to keep in their head.
18. **A local-first, plain-file substrate that agents can script.** *Obsidian vault + CLI; digital gardens' independent ownership.*

---

## Pitfalls and anti-patterns

1. **The collector's fallacy and the capture-synthesis gap.** Capture is quick and rewarding; synthesis is slow and has no external trigger. Systems optimized for capture (web clippers, highlight sync, voice notes, AI auto-ingest) widen the gap. Every capture channel added without a matching integration step makes the store more of a bucket.
2. **Mistaking low-utility rituals for learning.** Highlighting, rereading and bulk summarizing produce artifacts but little understanding (Dunlosky et al.). AI summarization is the extreme case: zero effort, so the user remembers nothing (Kosmyna et al.).
3. **Taxonomy decay.** Predetermined heads (commonplace books), deep folder trees and sprawling tag vocabularies become a record of past interests. Luhmann's own top-level sections are historical. Plan for structure to be rebuilt, not maintained forever.
4. **Graph-view hairballs.** A global graph of thousands of nodes shows that links exist, not what they mean. In the one empirical study I found, the graph view was not a retrieval strategy. Luhmann's value came from deliberate local links (about one per card or fewer) and hub cards, not density. Untyped, auto-generated "related" links add noise unless their precision is measured.
5. **Maintenance becomes the hobby ("productivity porn").** Effort moves from producing work to tuning the system: templates, plugins, tool migrations, workflow videos. This feels productive and crowds out the output that justifies the system.
6. **Inbox bankruptcy.** Capture queues that outgrow processing capacity end in a declared bankruptcy, and with it the user's trust in the system. A visible, growing backlog is a churn signal.
7. **Black holes and the write-only store.** Poorly connected material is never found again (Luhmann's black holes; List.it's 75% never edited). Storing it costs little, but cluttering search results and the user's sense of the store has a cost.
8. **The mausoleum effect.** A store that faithfully preserves past selves can weigh on present thinking (Westenberg). Keeping every bit of history is not automatically good. History must be available without being in the way.
9. **AI over-promising.** "Self-organizing" (Mem 1.x) did not remove the need for the user to do the integrating, and the company rebuilt the product. LLM-written wikis drift silently and erase whose understanding they represent. The risk is a store that looks coherent while the person's understanding shrinks.
10. **Cargo-culting Luhmann.** Copying his forms (atomic cards, folgezettel IDs, three note types) without his conditions fails. He had one lifelong theoretical project, wrote for publication constantly, and spent a lot of time on upkeep. Most people have none of these.
11. **Fragile tools.** Proprietary stores, stalled vendors (Roam), forced rebuilds (Mem) and single-maintainer projects (Anki before 2026) all put long-lived knowledge at risk.
12. **Bad retention prompts.** Spaced repetition fails when cards are vague, orphaned or unwanted. It is also the most common reason people say "Anki doesn't work".

---

## Implications for this project

Each implication is meant to be testable with this project's own prototype and dogfooding.

1. **Make integration the core operation, not capture.** Ingesting anything must produce a proposed *delta* against existing knowledge: supports, contradicts, refines, answers a question, or new. The person confirms or edits it. *Test:* after 8 weeks of dogfooding, at least 60% of ingested items should be connected to at least one existing unit or active question. Below about 30% means the system is a bucket, whatever the UI looks like.

2. **Two layers with different rules.**
   - (a) An append-only evidence/event log for sources, captures and conversations. It is immutable, timestamped and attributed, like a lab notebook or Karpathy's raw layer.
   - (b) A mutable synthesized layer of claims, beliefs, decisions, questions and goals. Every change in (b) creates a new version linked to the old one and to the evidence in (a) that prompted it.
   - *Test:* for any current belief, the system can show its full revision history and the evidence behind each revision.

3. **Stable IDs for every unit, independent of title, location or cluster.** Links, AI citations and human references survive reorganization. *Test:* a full re-clustering or reorganization breaks zero references.

4. **No user-maintained taxonomy.** Provide (a) search and semantic retrieval, (b) a small entry-point index, and (c) views and hubs generated on demand per question or project, with an option to pin a view the person finds useful. *Test:* users can answer "what do I think about X and why?" without having filed or tagged anything. Pinned views stay under about 20 per active project.

5. **Active questions and projects are first-class objects and the main organizing context.** New material is evaluated against them. Resurfacing is driven mainly by the active context, not only by a schedule. *Test:* resurfaced items are rated useful more than 50% of the time (thumbs up/down). If not, the trigger is wrong.

6. **Keep the person in the generative loop for the belief layer.** The AI may draft. A unit only becomes "the person's belief" when the person writes or explicitly endorses it, ideally in their own words. Provenance is mandatory on every unit: human-authored, AI-drafted & human-endorsed, AI-inferred, or quoted-from-source. *Test:* compare explanation recall on topics integrated with human rewriting against topics integrated by pure AI summarization. Predicted from Dunlosky, Kosmyna and Lee: human rewriting wins.

7. **AI handles upkeep. The person handles judgment.** AI does linking proposals, linting (contradictions, orphans, stale claims, duplicates), hub generation and opportunistic compression. Resolving contradictions and adopting beliefs stays with the person. *Test:* track the acceptance rate of AI link and lint proposals. Below about 40% acceptance means the proposals are noise and should be throttled.

8. **Budget upkeep explicitly.** The daily integration pass must fit in about 10 minutes. Unprocessed captures above a work-in-progress limit trigger triage, not a growing backlog. Low-priority items are allowed to decay into the archive with no guilt UI. *Test:* the median daily pass is 15 minutes or less, and the backlog does not grow monotonically over 4 weeks.

9. **Designed forgetting, not total recall.** Units carry salience and last-touched metadata. Unused, unlinked material fades from default views but stays in the log and in search. *Test:* default views stay focused, with a stable count of surfaced units even as the store grows.

10. **Epistemic status on every synthesized unit.** Maturity (seedling to evergreen), confidence, last-reviewed date, and open contradictions. Both humans and AI consumers need these to avoid treating stale or contested content as settled.

11. **Plain-file, local-first substrate that agents can script.** The source of truth should be readable without the app (for example Markdown/JSON plus an append-only log), so the knowledge outlives this prototype. Integration with ChatGPT, Claude and Codex then reduces to file access, CLI access or a thin protocol layer later.

12. **Instrument the system from day one, because the field has no outcome data.** Log: capture events, integration events, revisits, edits after capture (List.it baseline: 75% never edited), resurfacing feedback, time spent on upkeep, and days active. Run a dogfood period of at least 8 weeks before deciding on scale-up. This is the only way this project will learn what predicts its own abandonment.

13. **Spaced repetition is optional and opt-in per unit.** It is not part of the core loop. Offer it only for claims the person flags as "I want to know this without looking".

---

## Tensions and open questions

1. **Friction vs. learning.** Learning science says effort at encoding produces understanding. Adoption research says friction kills use. Hypothesis: make capture effortless and put a *small, bounded* effort at integration time, since that is where the generation effect pays. How small can it be and still work?

2. **Who writes the synthesized layer?** Options:
   - (a) The person writes everything. Best for understanding, worst for upkeep.
   - (b) The AI writes and the person endorses. Risks cognitive debt.
   - (c) A split: the AI writes the AI-facing context, and the person writes the beliefs.

   This is probably the single most important design decision and should be A/B tested inside the dogfood period.

3. **Does the AI-facing representation differ from the human-facing one?** Humans need narrative, recognizable landmarks and their own words. AI consumers need compact, current, explicit, attributed statements with status metadata. A plausible design: one canonical store of versioned units plus provenance, with *compiled* views for each audience. Is a compiled AI view stable enough to trust, or does it drift like the llm-wiki?

4. **Granularity.** Matuschak says atomic, but Luhmann's cards were not consistently atomic. Claims are good for AI and contradiction detection. Short essays are better for human reasoning chains. Do we need both claim-level units and argument-level sequences (folgezettel-like)?

5. **How much typed structure?** Typing Decision, Belief, Question and Goal gives AI and humans leverage. Every schema is also a small taxonomy that can decay. Where is the line?

6. **What to resurface, and when?** Context-triggered resurfacing, scheduled review and question-driven retrieval each have different failure modes: missed items, nagging, and only finding what you already knew to ask for.

7. **History vs. the mausoleum.** The system must keep useful history, such as why a belief changed, without making past selves the default view. What decay policy keeps views useful without losing provenance?

8. **Contradictions as signal vs. noise.** Many apparent contradictions are context-dependent ("X is true for small teams"). Automatic contradiction linting may produce floods of false positives. Measure precision before trusting it.

9. **How do we measure "understanding"?** Candidate proxies:
   - Explaining a topic from memory.
   - Decision quality in hindsight.
   - Time to recover context after a gap.
   - Whether AI agents given the store make fewer wrong assumptions about the person.

   None is clean. The evaluation design is itself an open problem.

10. **Is the problem the store at all?** Westenberg's deletion suggests that for some people the best system is a minimal one. If dogfooding shows most value comes from the question/project layer and the AI-context compile, the "knowledge store" should shrink to support those rather than grow into another PKM app.

---

## Challenges to the framing

These are recorded so the design phase can weigh them.

- **"Fragments" are not the enemy.** Luhmann's cards are fragments. What turns fragments into understanding is the *act of relating* them to existing thought and to a live question. A system that merges fragments into coherent-looking documents without that act may produce coherence in the store and none in the person.
- **Understanding lives in the person.** A store can only scaffold it. Success metrics must target the person's capability (and the AI's accuracy about the person), not how tidy the store is.
- **Not everything should be kept forever.** Most captured material is never revisited, and keeping everything can hinder present thinking. Forgetting should be designed in.
- **The user, not the content, is the bottleneck.** Every famous method failed for most adopters because upkeep competed with real work. The AI-era opportunity is to move *upkeep* (linking, linting, compiling, resurfacing) to AI while keeping *judgment and articulation* with the person. That is a narrower and more defensible goal than "AI organizes your knowledge".
- **There are already many PKM editors.** The differentiated value is more likely in belief and decision evolution with provenance, and in a trustworthy AI-facing context compiled from it, than in another note editor. The prototype may not need an editor at all and could sit on top of plain files.

---

## Sources

**Luhmann and Zettelkasten**
- Schmidt, J.F.K. (2018). "Niklas Luhmann's Card Index: The Fabrication of Serendipity." *Sociologica* 12(1). https://doi.org/10.6092/issn.1971-8853/8350 (revised from Schmidt 2016, in Cevolini (ed.), *Forgetting Machines*, Brill.)
- Niklas Luhmann-Archiv, Bielefeld University. https://www.uni-bielefeld.de/soz/luhmann-archiv/
- Luhmann, N. (1981). "Kommunikation mit Zettelkästen. Ein Erfahrungsbericht." In Baier et al. (eds.), *Öffentliche Meinung und sozialer Wandel*, pp. 222-228 (cited via Schmidt).
- Chiang, E. (2025). "Niklas Luhmann's Original Zettelkasten." https://www.ernestchiang.com/en/posts/2025/niklas-luhmann-original-zettelkasten-method/ (secondary)
- Zettelkasten forum thread on Luhmann's later card production. https://forum.zettelkasten.de/discussion/comment/20850/ (secondary, unverified claim)
- Ahrens, S. (2017). *How to Take Smart Notes* (from memory)

**Collecting, notes and learning**
- Tietze, C. (2014-01-20). "The Collector's Fallacy." https://zettelkasten.de/posts/collectors-fallacy
- Matuschak, A. "Evergreen notes." https://notes.andymatuschak.org/Evergreen_notes
- Matuschak, A. "Quantum Country users rarely forget after demonstrating five-day retention." https://notes.andymatuschak.org/zS5uKLsoTbkJSadTv2U3Z4G3uEBrFxTLy5E
- Matuschak, A. & Nielsen, M. (2019). "How can we develop transformative tools for thought?" https://numinous.productions/ttft/
- Nielsen, M. (2018). "Augmenting Long-term Memory." http://augmentingcognition.com/ltm.html
- Wozniak, P. SuperMemo incremental reading and "20 rules of formulating knowledge" (from memory). https://help.supermemo.org/wiki/Incremental_reading (fetch blocked)
- Dunlosky, J., Rawson, K., Marsh, E., Nathan, M., Willingham, D. (2013). "Improving Students' Learning With Effective Learning Techniques." *Psychological Science in the Public Interest* 14(1) (from memory; not re-fetched)

**Forte and digital gardens**
- Forte, T. "The PARA Method." https://fortelabs.com/blog/para/
- Forte, T. "Progressive Summarization." https://fortelabs.com/blog/progressive-summarization-a-practical-technique-for-designing-discoverable-notes/
- Appleton, M. "A Brief History & Ethos of the Digital Garden." https://maggieappleton.com/garden-history (cites Caulfield 2015, "The Garden and the Stream"; Bernstein 1998, "Hypertext Gardens")

**Personal information management (HCI)**
- Whittaker, S., Matthews, T., Cerruti, J., Badenes, H., Tang, J. (2011). "Am I wasting my time organizing email? A study of email refinding." CHI 2011. https://research.ibm.com/publications/am-i-wasting-my-time-organizing-email-a-study-of-email-refinding
- Bergman, O. & Whittaker, S. (2016). *The Science of Managing Our Digital Stuff.* MIT Press. https://muse.jhu.edu/book/48837
- Van Kleek, M., Bernstein, M., Panovich, K., Vargas, G., Karger, D., schraefel, m.c. "Note to Self: Examining Personal Information Keeping in a Lightweight Note-Taking Tool." (CHI 2009, venue from memory) https://people.csail.mit.edu/emax/papers/listit-camera.pdf
- Bernstein, M., Van Kleek, M., Karger, D., schraefel, m.c. (2008). "Information Scraps." *ACM TOIS.* https://hci.stanford.edu/publications/paper.php?id=236
- Ferreira, J.J., Segura, V., Souza, J.G., Brasil, J.H.G. (2025). "How People Manage Knowledge in their 'Second Brains': A Case Study with Industry Researchers Using Obsidian." arXiv 2509.20187. https://arxiv.org/abs/2509.20187
- Malone, T.W. (1983). "How do people organize their desks?" *ACM TOIS* (from memory)
- Barreau, D. & Nardi, B. (1995). "Finding and reminding." *SIGCHI Bulletin* (from memory)
- Blair, A. (2010). *Too Much to Know: Managing Scholarly Information before the Modern Age.* Yale UP (from memory; also covers Locke's commonplace method)

**AI and cognition**
- Lee, H., Sarkar, A., Tankelevitch, L., Drosos, I., Rintel, S., Banks, R., Wilson, N. (2025). "The Impact of Generative AI on Critical Thinking." CHI 2025. https://advait.org/files/lee_2025_ai_critical_thinking_survey.pdf
- Kosmyna, N. et al. (2025). "Your Brain on ChatGPT: Accumulation of Cognitive Debt when Using an AI Assistant for Essay Writing Task." arXiv 2506.08872 (preprint). https://arxiv.org/abs/2506.08872
- Westenberg, J. (2025-06). "I Deleted My Second Brain." https://westenberg.beehiiv.com/p/i-deleted-my-second-brain
- Arango, J. (2026-03-27). "Robots in the Garden." https://jarango.com/2026/03/27/robots-in-the-garden/
- Karpathy, A. (2026-04). "llm-wiki" gist (verified via secondary write-ups only). https://aksel.mataroa.blog/blog/karpathys-llm-wiki-full-analysis-with-comments/ and https://denser.ai/blog/llm-wiki-karpathy-knowledge-base/

**Tools and products**
- Mem. "Mem 2.0" announcement (2025-10). https://get.mem.ai/blog/mem-2-dot-0 ; 2024 year in review: https://get.mem.ai/blog/2024-year-in-review ; AlternativeTo coverage: https://alternativeto.net/news/2025/10/mem-2-0-relaunches-with-smarter-note-taking-tools-offline-support-and-a-new-agentic-chat
- Notion. "Notion 3.0" release notes (2025-09-18). https://www.notion.com/releases/2025-09-18
- Obsidian. "Free for work" (2025-02). https://obsidian.md/blog/free-for-work/ ; Desktop v1.12.4 changelog with the CLI (2026-02-27): https://obsidian.md/changelog/2026-02-27-desktop-v1.12.4/
- Anki forums. "Anki's Growing Up" (handover to AnkiHub, 2026-02). https://forums.ankiweb.net/t/ankis-growing-up/68610
- Tana Series A (2025-02), aggregator source. https://startupintros.com/news/2025-02-01-tana-series-a (unverified figures)
- Roam decline, low-quality secondary source. https://www.usecarly.com/blog/roam-vs-obsidian/ (directional only)
