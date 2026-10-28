# Round 6 research (26): the best form for the overview, a synthesis

**Date:** 2026-10-27. **Why:** on 2026-10-27 the user chose neither overview sketch: "Leaning towards B but still not very helpful. I asked for a deep research on what is the best form, article/papers/published etc,." (GOAL §1, §2). This note brings together four deep notes written in parallel the same day:
- [26a](26a-refinding-and-resumption.md): re-finding and getting back into work, from HCI and personal information management; 45 sources.
- [26b](26b-visualizing-own-ideas.md): showing a person their own ideas, from knowledge visualization and learning science; 66 sources, 13 of them meta-analyses or reviews.
- [26c](26c-practitioner-writing.md): what practitioners and tool-builders have published; 50 sources.
- [26d](26d-products-and-use.md): what products do, and what is known about use; 52 sources.

It builds on [note 25](25-overview-display.md) and [note 20](../round4/20-index-expansion-capture.md).

**Tags:** [E] = a source shows it; [L] = inference. The strength of evidence is graded per need.

---

## Short answer

- **No study tests a person glancing at an AI-made overview of their own ideas.** All four notes confirm the gap, so every recommendation rests on neighbouring evidence.
- **The three needs want different forms, and no single view serves all three.** Products, research and practitioners agree on this [E]. The sketch round tested one display for all three. Both of the user's "Ask about this" tries were questions about their past (need 3), which a display does not answer.
- **Shape matters less than content and use.**
  - Studying a map beat an outline or list by g = 0.28 for students (k = 10), and by about nothing for high-ability learners [E].
  - A person is the expert on their own ideas, so the user's preference can choose the shape [L].
  - What decides usefulness:
    - few entries;
    - the person's own words, not an AI's rewording;
    - one piece of real work on each entry;
    - a way onward from every entry.
- **For questions about one's past (need 3), the forms converge most strongly:** ask in the chat, and get an answer that quotes the person's own record and shows where it came from [E].
  - Answers must come from the record itself. ChatGPT's memory answered 57.7% of questions correctly, against 91.8% for the same model reading the full history [E].
- **For getting back into work (need 2):** "where you left off". That is the work as it was left (its last state and last steps), what changed since, and the stated goal and next step. A summary is only a label [E, moderate].
- **For the big picture (need 1):** a small, stable layer of entry points, a few per topic, in the person's own words, each with one work cue. Conflicts appear as pairs, with "open" and "changed since you last looked" marked. Products, practitioners and research all support this [E, weak to moderate]. Whole graphs are supported only for seeing shape and following links at small size [E].
- **Direction [L]:** keep the map the user prefers, made smarter. It shows few entries in the user's own words, each with work. Lines are drawn for the idea in focus. Every entry is a door to "ask" or to "where you left off". A text hub becomes the version for Claude Code.
- **The one question for the user:** stay with the smarter map as the first view (their pick on 2026-10-15), or switch to a text hub with the map second.

---

## 1. What the four notes agree on

| Need | Best-supported form | Agreement | Strength |
|---|---|---|---|
| **1. See the big picture** | A small, stable entry layer: a few topics in the person's words, 2–4 one-line claims each (verbatim), one work cue per claim, conflicts as side-by-side pairs, "open" and "changed since you last looked" markers, everything else one step away | 26a: small stable structure in the person's topics. 26b: two-level outline of claims. 26c: practitioners' hubs, structure notes and maps of content. 26d: products' short topic overviews | **Weak to moderate.** Convergence, plus experiments on orientation, but no test of this view |
| **2. Get back into a piece of work** | "Where you left off": the work as it was left (last state, last few steps, what changed since), with the stated goal, next step and open questions; one step into the artifact; a summary only as a label | 26a: resumption research. 26c: Forte's bridge and Engelbart. 26d: Granola, Limitless and Pulse briefs. 26b: one idea opened in place with its work | **Moderate.** Mostly small or lab studies, many on programmers |
| **3. Answer a question about my past** | Ask in the chat. The answer quotes the person's own record, shows its place (chat, day, piece of work) and opens it. A "not found" says where it looked. Browsing by topic, person and rough time is the second route | 26a: asking is quicker. 26b: quote, don't reword. 26c: answers returned as a trail. 26d: the strongest product convergence | **Moderate.** Strong convergence; moderate use evidence; well-measured risks |

**Across the three needs** [L, from 26a and 26d]: one view with three ways in (browse the big picture, open "where you left off", ask). Two linked layers sit under it: ideas, and episodes of real work.

## 2. The evidence that decides the details

- **Topic and purpose beat time.** In email re-finding, people remembered an email's topic in 85.1% of tasks, the reason it was sent in 80.9%, the sender in 77.1%, and when in only 57.5% (Elsweiler et al., ACM TOIS 2008; checked in the paper). So topics come first, and time is a filter [E].
- **Shape matters little for experts.**
  - Maps beat outlines and lists by g = 0.28 for students (Nesbit & Adesope 2006, k = 10; figure checked via Schroeder et al.). For high-ability learners the effect was about g = 0.13, not significant (26b, from the paper's tables).
  - Given organizers can beat self-made ones (Stull & Mayer 2007), so an AI may build the structure [E].
- **An AI's wording is risky.**
  - Learning from an LLM synthesis left knowledge shallower than searching oneself (Melumad & Yun, PNAS Nexus 2025, n = 10,462; checked).
  - A summary with one wrong detail changed what people remembered: 44.8% against 83.6% recalled correctly (Sim, Eiger & Kohno, AIES 2026, n = 328; checked).
  - No study tests a rewording of a person's own ideas. Still, the safe default is the person's own words, verbatim [L].
- **Answers must come from the record.** ChatGPT's memory answered 57.73% correctly, against 91.84% for the same model reading the full history (LongMemEval pilot, ICLR 2025; checked). This backs Northstar's choice to keep the chat history word for word, with a recall tool over it [E].
- **Citations need to be real and checkable.**
  - Citations raised trust even when they were random, and checking them lowered it (Ding et al., AAAI 2025, n ≈ 300; checked).
  - A generative chatbot produced over three times the false memories of a control (Chan et al. 2024, n = 200, preprint; checked).
  - So answers quote the record and open the place itself [E].
- **Chat over one's past is not free.** Google paused Ask Photos in June 2025 over latency, quality and experience; it returned with ordinary results shown first (checked). So exact matches come first, then the AI's answer [E].
- **The one mass-market AI-made map turns a click into a question.** In NotebookLM, selecting a mind-map node asks about it in the chat (Google's help page; checked) [E].
- **Graphs are for shape, not understanding.**
  - No maker of a graph view has published how much it is used. In 2025 those makers built tables (Obsidian Bases) and chat over the canvas (Heptabase) (26d).
  - Practitioners defend graphs only for upkeep and for seeing shape (26c).
  - Node-link views lose to crossings as they grow, and spatial memory forms through use and self-placement. A layout an AI places, opened a few times a year, builds little of it (26b) [E].
- **Resurfacing has the largest usage numbers, but none for knowledge.** Facebook's On This Day had 60–90 million visitors a day and Google Photos Memories 500 million users a month (26d). Northstar's memory job already brings knowledge up in chat; a "changed since you last looked" line is the overview's share [L].

## 3. Why the two sketches fell short

These are hypotheses, not findings.
- **Sketch A** had a hub's shape, but listed everything, like a full table of contents, in AI-chosen words. The practitioners' hub lists only a few entry points (26c).
- **Sketch B** showed the shape, but not the meaning. It drew every line at once, and its entries led nowhere except a detail panel (26b, 26c).
- **Both** served need 1 only. The user's questions were need 3, about episodes of past work, not ideas (26a). The test also timed lookups of facts, the job asking does best, and that read as a quiz.

## 4. The direction [L]

**One overview with three doors:**
1. **The big picture, as a smarter map** (the user's pick of "Map" on 2026-10-15, and their lean toward B):
   - a few topic regions in the user's words, each with 2–4 entry claims in their own words and a work cue on each, and counts of the rest;
   - conflict pairs side by side; "open" and "changed since you last looked" marked;
   - lines drawn for the idea in focus, not all at once;
   - the layout kept stable between visits;
   - every entry opens a door below.
2. **"Where you left off"** for each piece of work in progress: last state, last few steps, what changed, next step and open questions, with one step into the work itself. These are Northstar's start notes, made visible.
3. **Ask:** a question in the chat, answered with exact matches and quotes from the record first, then a short answer with each source opening its place. "Not found" says where it looked.

**The text version for Claude Code** is the same entry layer as a two-level outline.

**Revisit or expand stays the user's call** (still "Not sure", 2026-10-27).
- Every product and practitioner applies knowledge in the chat, not in the overview.
- The evidence favours an expansion that starts from the person's own position and leaves them the next move (Melumad & Yun; Bastani et al. in 26b).
- So the overview stays revisit-only, and the chat door is where expansion happens if the user asks for it.

**What it keeps:** the human-view rows of GOAL §2 (2026-10-15): big picture first, grouped by topic, connect and conflict lines, real work bringing it back, one line per item, and the view in the assistant when asked. It adds the two doors that products pair with an overview.

## 5. The question for the user

The evidence says the shape matters less than the content and the doors, and the user picked "Map". So there are two options [L]:
- **A smarter map first.** The direction above, keeping the user's preference.
- **A text hub first, with the map as a second view.** This has the most practitioner support, and it reads anywhere, including Claude Code.

## 6. What to test next

- **A look-and-react round on the user's real material,** not a timed quiz. One view with the three doors, built from the same items as the sketches, so only the form changes.
- **What to record:** which door the user takes first; whether they recognize their ideas from their own words (the "not what I think" flags); and whether "ask" answers find the right place.
- **The timed comparison with the usual means** waits for the prototype, where DESIGN §8 runs it per need: a glance for need 1, time to the first useful action for need 2, and correct answers with sources for need 3.

## 7. Checks and limits

- **Checked against sources on 2026-10-27:** Elsweiler et al. 2008 (in the paper); Nesbit & Adesope g = 0.28 (via Schroeder et al.); Melumad & Yun; Sim, Eiger & Kohno; LongMemEval; Ding et al.; Chan et al.; the Ask Photos pause; NotebookLM's node-to-chat.
- **Not rechecked here:** the high-ability g = 0.13; Kidd 1994; Quantum Country's figures; the Facebook and Google Photos usage numbers. Each note flags its own unverified items.
- **Fixed in 26b:** two lines said "AI paraphrase". The studies tested AI summaries and syntheses, not paraphrases of a person's own ideas.
- **Corrections to note 25 and note 20, reported by 26d and 26b:**
  - A DOI in note 25 belongs to "AI Never Forgets" (Chen et al., CHI '26).
  - Note 20's row 1.1 figures come from Schroeder et al. 2018, not Nesbit & Adesope.
- **Evidence age and scope:** most re-finding evidence dates from 2001 to 2011, before LLM assistants. The resumption studies are small or lab-based, and the learning-science studies are about students learning set material, not people revisiting their own ideas.
- **Cost:** the four agents used about 1.19M tokens (0.36M, 0.31M, 0.26M and 0.26M); the checks and this synthesis ran in the main session.
