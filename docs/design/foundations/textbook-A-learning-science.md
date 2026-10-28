# Human architecture, design A: a textbook built from learning science

**Status:** design proposal, written 2026-10-08. It has not been reviewed, approved or built.
**Angle:** learning-science-first. This is one of three independent designs for the human side. Judges will compare them.
**Authority:** [`docs/GOAL.md`](../../GOAL.md) overrides this file. This design changes only the HOW. Where it sees a risk to part of the goal, it says so in §14 and §15 and keeps designing for the goal as written.
**Evidence base:** round-2 notes [10]–[14] and SYNTHESIS (round 2); round-1 notes [01], [02] and [07] for evidence only; and targeted lookups of instructional-design research, listed in Sources with the date checked.
**Conventions:** "(Unv)" marks an unverified product fact. "(secondary)" marks a number I saw only in a summary of the paper, not in the paper itself. "(from memory)" marks a well-known finding I did not re-check today.

---

## 1. The goal this design serves

From GOAL §3.2:

> **It reads like a textbook.** The AI organizes the knowledge and explains it so the person **understands and remembers** it when they read. Every explanation stays traceable to its sources: who said it, and in which conversation. It is not a quiz or a mastery score.

From the user, 2026-10-08:

> "the key is to help human understand and remember their knowledge, just like textbooks."

The human side covers two things (GOAL §3.2, §2 "Both"):
- **what has been learned**, from the user's own thinking and from what AIs explained or taught, each attributed;
- **what to learn**: goals, gaps, open questions and next steps.

The AI builds and reorganises it. The user browses it and may correct it. Nothing requires a routine (GOAL §4.1, §4.3).

---

## 2. The design in one screen

1. **Start from what makes read text understood and remembered.** §3 turns sixteen findings into sixteen design rules (D1–D16), each with its effect size and its limits.
2. **The book has six units:** book, part, chapter, page, section, plus front and back matter. A page holds one idea: one concept, one question, one goal or one project case. This follows the segmenting and chunking evidence (D5).
3. **Every concept page has the same fixed anatomy:** key idea, where this fits, the explanation, examples from your own work, who taught you this, how your understanding changed, still open, next from here, sources. Each part exists because a finding supports it.
4. **Examples come from the reader's own conversations and projects.** This uses the self-reference effect (g = 0.40) and concrete-example evidence, within their limits (D6, D7).
5. **AI-taught knowledge is first-class.** It is written into the explanation on equal terms with what the user said, ranked by relevance, never by speaker. Every sentence carries speaker and verification chips.
6. **Code writes the attribution, not the model.** The writing model produces neutral, cited sentences. A renderer adds "Claude explained, 12 Sep" from the records. Claims about the user's own past beliefs are shown as dated quotes, never retold.
7. **Any sentence leads to its verbatim source in two clicks:** sentence → cited item → highlighted span in the stored conversation.
8. **"What to learn" is a part of the book, not a to-do list.** Part 0, "Where you're going", holds goals, open questions, gaps and the frontier. Every chapter and page links back to it.
9. **The book evolves in printings and editions.** Content updates nightly ("printings"). Structure changes at most weekly ("editions"), under a stability budget. Page IDs and links never change. Every change can be undone.
10. **When understanding changes, the page says so in refutation form:** what you thought, why it seemed right, what changed it, what you think now (g = 0.41 for refutation texts).
11. **Pages are compiled from leaf items only.** Every sentence cites a leaf. Thirteen deterministic validators reject bad output. A model from a different family spot-checks entailment. A failed section falls back to a plain cited list, so the book is never wrong to look nicer. Cost is about $15–20 a month at 36K events a year (±2×).
12. **The reader reads it in a local web app now, the same app in the cloud later.** Small in-chat slices appear in Claude Desktop chat, ChatGPT Desktop chat, Claude Code and Codex.
13. **No quizzes, no scores, no schedule.** One optional aid ("cover mode") exists, off by default, with no scoring and no record kept. The book delivers its value without it.
14. **Evaluation needs no user sessions.** Truth and attribution are hard gates. Simulated readers compare the textbook against plainer renderings. Passive behaviour, such as how often the user re-asks an AI to explain something already in the book, stands in for remembering.

---

## 3. The evidence, and the design rules it produces

The question for this angle is narrow: **what makes expository text understandable and memorable when a person reads it?** Each row below gives a finding, its size, where it stops working, and the rule this design takes from it.

Effect sizes use Cohen's d or Hedges' g. As a rough guide, 0.2 is small, 0.5 is medium and 0.8 is large.

### 3.1 Findings and rules

| # | Finding | Size | Boundary conditions | Design rule |
|---|---|---|---|---|
| E1 | **Advance organisers.** A short overview that links new material to what the reader already knows helps learning and retention (Luiten, Ames & Ackerson 1980; Stone 1983). | Small: d ≈ 0.21, rising with delay (secondary, via Hattie) | Early research was inconclusive (Mahar 1992). Works best for unfamiliar, structured material. | **D1.** Every part, chapter and page opens with an organiser: the key idea plus links to what the reader already has. |
| E2 | **Signalling.** Headings, previews and cues that show structure improve memory for what they cue (Lorch 1989). Meta-analysis: Schneider et al. 2018. | g = 0.53 retention, 0.33 transfer (secondary); d = 0.38 in a second meta-analysis (Alpizar et al. 2020, secondary) | Signals help the cued content, not the rest (Lorch 1989). They can weaken memory for minor and verbatim detail (Loman & Mayer 1983, secondary). Headings helped unfamiliar topics, not familiar ones (Lorch & Lorch 1996). Misleading headings bias understanding (Kozminsky 1977, secondary). | **D2.** Headings state the idea. A heading counts as a sentence and must be supported by the section's sources. Minor and verbatim detail stays one click away in the sources. |
| E3 | **Coherence.** Interesting but irrelevant material ("seductive details") hurts learning (Rey 2012; Sundararajan & Adesope 2020). | g = −0.33 (Sundararajan & Adesope); a newer abstract reports g = −0.16 | Size varies across reviews; most studies were 6–12-minute sessions. | **D3.** No decorative images, asides or anecdotes that do not explain the idea. Provenance lives in a margin rail and opens on demand, so it does not crowd the prose. |
| E4 | **Cohesion depends on prior knowledge.** Readers new to a topic understand explicit, well-connected text better. Readers who know a topic can learn more from text that leaves links for them to make (McNamara et al. 1996). Support that helps novices can hurt experts (Kalyuga et al. 2003, [01 F9]). | Crossover interaction, not one pooled size | Replication is mixed (secondary). Reading skill also matters. | **D4.** New topics get a "learning register": full connectives and explicit links to prerequisites. Topics the user has used and restated many times get a terser "reference register". The switch uses event counts, not a mastery estimate (§4.6). |
| E5 | **Segmenting and chunking.** Material split into learner-paced pieces is learned better (Rey et al. 2019: 56 investigations, 88 comparisons). Working memory holds about four chunks (Cowan 2001, [01 F9]). | Small to medium, retention and transfer | High-prior-knowledge learners gained more on retention. Mostly multimedia studies. | **D5.** One idea per page. Explanation segments of about 120–220 words, at most five per page. At most seven items in any list on the first screen. |
| E6 | **Worked and concrete examples.** Studying worked examples helps (Barbieri et al. 2023). Concrete examples paired with abstract definitions help people recognise new cases (Rawson, Thomas & Jacoby 2015; replication d = 0.30). Comparing cases helps, most when the principle comes after the comparison (Alfieri et al. 2013). | g = 0.48 worked examples (maths; I² ≈ 94%); d = 0.50 case comparison | Expertise reversal: examples help novices most. Examples must be tied explicitly to the idea. | **D6.** Each explanation segment pairs its abstract statement with a concrete instance. "From your work" shows two or three cases, then states what they share. |
| E7 | **Self-reference.** Material related to oneself is remembered better (Symons & Johnson 1997). In education: Liu et al. 2023. Personal, conversational wording helps too (Ginns, Martin & Marsh 2013). | g = 0.40 [0.18, 0.62] self-referential techniques (13 studies); d = 0.30 retention, 0.54 transfer for conversational style | The advantage is larger against plain semantic processing than against thinking about a close other person. Negative material reverses it (Liu et al.). Conversational style had small effects in sessions over 35 minutes. Shallow personal details that do not connect to the idea distract (Walkington et al., secondary). | **D7.** Examples come from the reader's own conversations and projects, written in the second person. Prefer neutral or successful episodes. Never use distressing personal material as an example. Personal detail appears only when it illustrates the idea (D3). |
| E8 | **Elaboration and prior knowledge.** Explaining why something is true, and linking it to an existing schema, aids integration. Elaborative interrogation is rated "moderate" (Dunlosky et al. 2013, [01 F8]). Schema-consistent material integrates fast; surprising material is kept distinct (Tse et al. 2007; SLIMM, [01 F4]). | Moderate (qualitative rating) | Schema fit also produces false "memories" of things that fit but never happened [01 F4]. | **D8.** Each page links to what it builds on and says why the idea holds. Material that contradicts the reader's existing pages is flagged as surprising, never blended in. |
| E9 | **Dual coding and diagrams.** Words plus relevant pictures beat words alone. Mayer's lab reports a median d ≈ 1.39 on transfer. Independent meta-analyses find less: g = 0.23 for illustrations in science texts (Lei et al. 2025), g = 0.52 for organisational pictures in problem solving (Hu et al., secondary). Studying a ready-made concept map: g = 0.43 [12 F14]. | Small to medium in independent reviews | No evidence that global graph views help [12 F15]. Decorative pictures are seductive details (E3). | **D9.** A diagram appears only when the idea is relational: a local concept map of up to nine nodes, a comparison table, a sequence or a timeline. Code draws it from recorded relations. No global graph by default. |
| E10 | **Refutation text.** Text that states the old view, refutes it and explains the new one changes misconceptions better than plain exposition (Schroeder & Kucera 2022). Old beliefs are not erased; they must be out-competed (KReC; continued influence, [01 F5]). | g = 0.41 [0.30, 0.51]; 0.28 after trim-and-fill | Passages were short (longest 1,542 words). Only two studies tested beyond a month. | **D10.** When understanding changes, the page shows a refutation block: what you thought, why it seemed right, what changed it, what you think now. It shows on the next few visits, then folds into the page history. |
| E11 | **Spacing, and its limits for rereading.** Spaced study beats massed study (Cepeda et al. 2006, [01 F8]). Spaced rereading beat massed rereading on a two-day delayed test but not an immediate one (Rawson & Kintsch 2005). A classroom study with seventh-graders found no benefit even when delayed (Greving & Richter 2019). Rereading is "low utility" overall (Dunlosky et al. 2013). The strongest memory lever is retrieval practice (g = 0.50, Rowland 2014; g ≈ 0.61, Adesope et al. 2017, secondary). | Spaced rereading: small and inconsistent | Retrieval practice is a test, and GOAL §3.2 says the product is not a quiz. | **D11.** Create spaced re-encounters out of what the user already does: a short page card when a later chat touches the idea, and a "what changed" digest. No schedule. **D11b.** Any retrieval aid is optional and off by default (§11). |
| E12 | **Narrative.** Stories are understood and remembered better than essays (Mar et al. 2021, 37 studies). | g = 0.55 overall; 0.48 comprehension; 0.72 memory | Genre is often confounded with topic. A conversational AI retelling a person's past can implant false memories (Chan et al. 2024, [01 F11]). | **D12.** Each page carries a short, dated story of how the user met the idea. It is built only from quoted, dated records, never a retelling. |
| E13 | **Sources reduce over-reliance.** Showing sources reduced reliance on incorrect AI answers; explanations alone increased it (Kim et al., CHI 2025, [12 F8]). Human memory loses sources (sleeper effect, illusory truth, [01 F11]). | Pre-registered, N = 308 | Provenance is not truth: "source: Claude, 12 Sep" is not evidence [12 R1]. | **D13.** Every sentence shows who said it and its verification status. Speaker and correctness are separate chips. |
| E14 | **Fluency inflates felt understanding.** Searching and fluent AI synthesis raise people's sense of what they know without raising what they know (Fisher et al. 2015; Ward 2021; Eleftheriou et al. 2026; Melumad & Yun 2025, [01 F10, F13]). | Robust across studies | This is the main human-side risk of any polished text [01 F10]. | **D14.** What is not known (open questions, contested claims, unchecked AI claims the user relied on) is shown as prominently as what is known. The book never says "mastered". |
| E15 | **People navigate by recognition, place and time.** Users re-find by orienteering through familiar structure ([07 F10]); time and people are strong cues (Dumais et al. 2003, [12 F15]); churn destroys location memory [12 F16][02 F2]. | Field studies | Heavy filing does not pay [02 F2]. | **D15.** Stable parts and chapters, permanent page addresses, a timeline view and search. Structure changes are rationed (§7). |
| E16 | **Reading against a live question.** Material sticks when a current question or project pulls it in; orphaned material decays ([02 F6]). The user's own unresolved questions are the best free signal of a gap [12 F12]. | Mostly qualitative, convergent | | **D16.** Goals and open questions frame each chapter, the way learning objectives frame a textbook chapter. They come from the user's own words. |

### 3.2 Limits of this evidence

- **Most studies used students, unfamiliar topics, short sessions and immediate tests.** A personal book is read in short visits over months, about topics the reader partly knows. Effects may be smaller here.
- **Effects do not add up.** Signalling, segmenting and examples share mechanisms. A page that uses all of them will not get the sum of their effect sizes.
- **Several numbers are secondary.** The signalling, seductive-details and advance-organiser figures come from summaries. None of the design rules depends on the exact value.
- **Reading alone is a weak memory technique.** Rereading is rated low utility, and the strongest levers, retrieval and generation, require the reader to act [01 F8][02 F4]. The book can make knowledge clear, findable and well connected. It can make it more memorable only modestly unless the reader chooses to do more. This is RISK H1 (§15) and question Q4 (§14).
- **A book the AI builds helps less than one the person builds** (concept maps: g = 0.43 studied against 0.72 built [12 F14]; SYNTHESIS RISK 17). The user chose AI management, so this design does not shift work to the user. It uses self-reference, refutation and re-encounter to recover part of the gap.

---

## 4. The book's anatomy

### 4.1 The units

| Unit | What it holds | Why it helps understanding and remembering |
|---|---|---|
| **Book** | All of one person's knowledge in one scope. Personal scope first; work scopes later (§10.6). | One place to orient. Its contents page is the top-level organiser (D1, D15). |
| **Front matter** | The **front page** (§10.4) and the **contents**. | The front page is an organiser for "now": goals, what changed, where to continue (D1, D11, D16). |
| **Part 0: Where you're going** | Goal pages, the open-questions register, gaps and the frontier (§6). | Reading against a live question (D16). Keeps "what to learn" beside "what was learned". |
| **Subject parts** (at most 9) | Broad areas of knowledge, such as "Software architecture" or "Rust". Derived by clustering, then held stable (§7). | Few, stable landmarks fit recognition memory and the 4–7 chunk limit (D5, D15). Luhmann's second card index had 11 top sections [02 F1]. |
| **Casebook part** | One chapter per project or recurring context (a repository, a reading project, a long-running chat topic). Its pages are cases. | Supplies the self-referential, concrete examples the subject pages cite (D6, D7). Keeps project-specific facts apart from transferable knowledge. See Q3. |
| **Chapter** | A cluster of related pages, usually 5–25. Opens with an organiser and ends with a recap and open questions (§4.5). | Organiser plus recap brackets the material (D1, D2). The recap is assembled from page key ideas, so it adds no new generated claims (§8.5). |
| **Page** | One idea. Four types: concept, question, goal, case (§4.3). | Segmenting (D5). A stable unit to cite, link and return to (D15). |
| **Section** | One part of a page's fixed anatomy (§4.4). The explanation section has 2–5 short segments, each with a heading. | Signalling and segmenting (D2, D5). Also the unit of incremental recompilation (§8.6). |
| **Back matter** | **Glossary** (each term's cited definition), **index** (a few entry points per term [02 F1]), **sources register** (one entry per conversation or document), **timeline** (what entered or changed, by month), **changes** (printings, editions, corrections) and the **open and contested register**. | Index and glossary are entry points for "I know what I want" (D15). The sources register is the bibliography that makes every claim traceable (D13). The timeline uses time as a retrieval cue (E15) and shows how understanding evolved (§7.5). |

**Polyhierarchy.** A page has one home chapter, which gives its address. It can also be listed in other chapters as "also in" (soft membership [12 F4]; [12] decision 5).

### 4.2 Size rules

These follow D5 and are checked by validators (§8.4). They are starting values, to be calibrated on the golden book (§13).

| Rule | Starting value |
|---|---|
| Key idea | 1–2 sentences, at most 45 words |
| Sentence length | at most 35 words |
| Explanation segment | about 120–220 words; at most 5 segments per page |
| Sections per concept page | 4 always present (key idea, where this fits, explanation, sources); up to 10 when optional sections have content |
| Examples per page | 1–3 shown; more behind "more cases" |
| Pages per chapter | target 5–25; over 30 triggers a split proposal |
| Chapters per part | target 3–12 |
| Subject parts | at most 9 |
| Items per front-page block | at most 7 |

### 4.3 Page types

| Type | Lives in | Holds |
|---|---|---|
| **Concept page** | Subject parts | One idea, with the full anatomy in §4.4. |
| **Question page** | Part 0 (open) or the chapter of its main concept (answered) | The question verbatim, who asked and when; what is known so far; each answer with its speaker; status (open, answered, dormant). An answered question keeps its page and gains "answered on [date] by [speaker] in [conversation]". |
| **Goal page** | Part 0 | The goal in the user's words, with date; why, in the user's words if they said; the path of prerequisite pages (§6.4); what is covered; what is next; related questions. |
| **Case page** | Casebook | One episode or a run of episodes in a project: what the user was doing, what was decided and why (quoted), which concept pages it illustrates, what was learned. |

Each conversation or document also has an entry in the **sources register**: title, product, model, date, and the pages that cite it. That entry is how a reader goes from a page to a conversation and back.

### 4.4 The concept page

The order is fixed, so a reader always knows where to look (D2, D15). Each section exists because of a finding.

| # | Section | Contents | Rule |
|---|---|---|---|
| 1 | **Key idea** | The gist in 1–2 cited sentences, under the title. | D1, D2. Gist outlasts verbatim memory [01 F1]. |
| 2 | **Where this fits** | Breadcrumb. "Builds on" (prerequisite pages), "Leads to" (pages that build on this one), "Serves your goal" (goal pages). Rendered by code from relations. | D1, D8 |
| 3 | **The explanation** | 2–5 segments with idea-stating headings. Each segment ends, where one exists, with an "e.g." line from the user's own work, shown as a short quote with date. | D2, D3, D4, D5, D6 |
| 4 | **From your work** | 1–3 cases from the user's conversations and projects, each with context and a short verbatim excerpt, then one cited line stating what they share. | D6, D7 |
| 5 | **Picture** (optional) | A local concept map (up to 9 nodes), comparison table, sequence or timeline, drawn by code from relations. Only when the idea is relational. | D9 |
| 6 | **Who taught you this** | The dated story of how the user met the idea, as quoted records: each source (you, Claude, ChatGPT, Codex, a document) with a 1–2 sentence verbatim excerpt, date, product and model, and verification chip. In date order. | D12, D13 |
| 7 | **How your understanding changed** (when it did) | Refutation blocks (§7.4). | D10 |
| 8 | **Still open** | Open questions on this idea; contested claims with both sides attributed; unchecked AI claims the user went on to rely on. | D14, D16 |
| 9 | **Next from here** | Frontier pages that this idea unlocks, each with its reason (§6.4). | D16 |
| 10 | **Sources and history** | The conversations cited, the printing and edition, corrections. | D13 |

A mock page, with fictional content:

```
4.2.3  Event sourcing                                  edition 7 · printed 2026-10-08
Part 4 Software architecture › 4.2 Keeping history

KEY IDEA
  Store every change as an immutable event, and rebuild the current state       │ Claude ○
  by replaying the events.                                                     │ ChatGPT ✓

WHERE THIS FITS
  Builds on   4.1.2 Append-only logs · 4.1.4 Idempotency
  Leads to    4.2.4 Projections and CQRS  (ready to learn)
  Serves      Goal: "Design an event-sourced ledger" (you, 7 Oct)

THE EXPLANATION
  Events are the record; tables are views                                        │ Claude ○
    ...three or four cited sentences...                                          │ you
    e.g. habit-tracker, 3 Sep: "replaying the events rebuilt the stats view"     │ you (quote)
  Rebuilding state takes snapshots as well as replay                             │ ChatGPT ✓
    ...cited sentences...                                                        │ Claude ○
  Deleting data is the hard case                                                 │ Claude ◇
    ...cited sentences, one marked (tentative)...

FROM YOUR WORK
  Case 1  habit-tracker (Claude Code), 3 Sep — "replaying the events rebuilt the stats view"
  Case 2  reading notes (ChatGPT Desktop), 20 Sep — "the bank statement is an event log"
  What these share: the current state was derived, so it could be rebuilt.       │ cited

WHO TAUGHT YOU THIS
  12 Sep  Claude (Claude Desktop) "An event store keeps every change as a fact..."  ○ unchecked
  14 Sep  You                     "So the log is the truth and tables are caches."  your words
  3 Oct   ChatGPT (Desktop)       "Most systems also snapshot every N events..."    ✓ supported

HOW YOUR UNDERSTANDING CHANGED
  You thought (14 Sep):   "tables are just caches"
  Why it seemed right:    views can be rebuilt from the log            (Claude, 12 Sep)
  What changed it:        replay alone was too slow; snapshots needed  (ChatGPT, 3 Oct)
  You now hold (5 Oct):   "the log is the truth, snapshots make it usable"

STILL OPEN
  ?  "How do I delete personal data from an append-only log?"  you asked ChatGPT, 3 Oct
  ⇄  Snapshot frequency: Claude said every 100 events; ChatGPT said it depends on load

NEXT FROM HERE
  →  4.2.4 Projections and CQRS — ready: you have covered 4.1.2 and 4.2.3

SOURCES  4 conversations · 11 items · history · corrections (0)
```

Chips: "○ unchecked", "✓ supported", "◇ opinion or advice, not checkable", "⇄ contested", "✗ contradicted" (only in history). Each chip is a glyph plus a word, never colour alone.

### 4.5 Chapter and part anatomy

**Chapter opener** (D1, D16):
- the chapter title and a one-paragraph "big picture", compiled from leaf items that link to two or more of the chapter's pages (§8.5);
- "In this chapter": each page with its key idea, transcluded word for word with its citations;
- "Builds on": the chapters it depends on;
- "Your goals here": the goals whose paths pass through this chapter, in the user's words.

**Chapter close:**
- "Recap": the key ideas again, in reading order (bracketing, D2);
- "Open questions in this chapter" and "Next in this chapter".

**Reading order** inside a chapter follows prerequisites (a topological order), so "previous" and "next" make sense. Ties break by first-encounter date.

**Part opener:** the part title, its chapters with one line each, and its goals. No generated prose beyond chapter big pictures.

### 4.6 Two registers: learning and reference

Expertise reversal (E4) means a single density cannot suit both a new idea and a well-worn one.

- **Learning register**, the default: full connectives, prerequisite terms linked inline to their glossary entries, two examples where available.
- **Reference register**: the key idea, a compact list of the main cited statements, one example, and the sources.
- **The switch** is a deterministic rule over engagement events from the core (SYNTHESIS §3.2): for example, the user restated or applied the idea in at least three separate episodes. It is not shown as a level or score. The reader can flip any page with one click, and that choice is a per-reader view setting, not a correction.

### 4.7 What earns a page

Not every item deserves a page. Promoting one-off items creates a bloated, fragmented book [02 F10 "mausoleum"], and one-off events should not become general knowledge (Go-CLS, [01 F3], [01] idea 6).

- **A concept gets its own page** when it appears in at least two independent episodes, or links to an active goal or open question, or the user asks for it.
- **Otherwise it is a short note**: one cited line, with chips, in its chapter's "Short notes" list and in the index and search. It is promoted when it meets the rule.
- **Speaker does not count.** An idea taught by an AI in two conversations earns a page exactly as one the user raised twice does. The AI-said share of pages is monitored against the golden set (§13), so the gate cannot quietly demote AI-taught knowledge [12 R4].

---

## 5. What has been learned: attribution down to the verbatim span

### 5.1 What counts as learned content

"What has been learned" is the content itself (SYNTHESIS Table B, §3.2): what the user stated or concluded, and what AIs explained or taught, plus later sources such as documents. In core terms these are Statements and Passages, each with its attribution [12] decision 1–2. It is not an estimate of mastery (GOAL §2, 2026-10-08).

### 5.2 What every sentence shows

Every sentence in the book can show four separate things. They come from the core's independent attribution axes (SYNTHESIS §3.1, AD6).

| Shown as | Meaning | Values |
|---|---|---|
| **Speaker** | Who said it | You (typed), You (pasted), Claude, ChatGPT, Codex, a named document, Northstar (system-inferred, rare) |
| **Product and model** | Where and with what | e.g. "Claude Desktop chat, Opus", "Codex, gpt-5", "Claude Code" |
| **Your stance** | What you did with it | asserted, accepted, questioned, disputed, rejected, none |
| **Verification** | Whether it was checked, by whom | supported, mixed, unchecked, not checkable (opinion or advice), contradicted, AI-cited-unchecked |

A fifth, **capture fidelity**, appears only when it is not "verbatim": "paraphrased capture, verbatim pending" or "reconciled" (§5.7).

The margin rail shows the speaker glyph and verification glyph per sentence group. Hover or tap opens the full record. This keeps the prose clean (D3) while every claim stays one step from its source (D13).

### 5.3 Code writes attribution; the model does not

Misattribution is a common failure of shipped memory: 43–55% of AI-introduced distractors were stored as user facts [12 F8]; models over-infer user attributes [07 F7].

- **The writing model never names a speaker.** Its sentences are neutral propositions with citations. A validator rejects any sentence that contains a speaker name or an attribution verb such as "you decided" or "Claude said" (V4, §8.4).
- **The renderer adds attribution** from the cited items' records: the margin chips, and, where prose needs it, a fixed phrase such as "Claude explained (12 Sep)" or "you concluded (14 Sep)".
- **"You" sentences need your words.** A sentence stating what the user believes, decided or concluded must cite a user-spoken item with stance asserted or accepted (V5; core invariants I3, I4 [13]). An AI-said item the user never endorsed can only be rendered as "Claude explained", never as "you concluded".

### 5.4 The path from any sentence to the verbatim source

| Step | The reader clicks | They see |
|---|---|---|
| 1 | A sentence or its chip | The cited items: gist, speaker, stance, verification, date |
| 2 | An item | The **source viewer**: the stored conversation or document with the exact span highlighted, ±5 turns of context, the branch if there was one, the product and model, and the verification record (verifier model, evidence, date) |
| 3 | "Open original" (where available) | The conversation in its product, when the product exposes a stable link (Unv for the desktop apps; see the unverified list) |

The source viewer reads Northstar's own stored copy, so it works offline and does not depend on the vendor keeping the chat. Excised content shows a tombstone (SYNTHESIS §5 item 9).

### 5.5 AI-taught knowledge is first-class

GOAL §4.2 requires it. These rules make it hold in the book, not just in the store:

1. **AI passages are written into the explanation on equal terms.** Items compete for a page's space on relevance to the concept, centrality and recency. Speaker is not a factor (as in SYNTHESIS §3.4's pack rule).
2. **Every assistant passage stays reachable.** The core keeps every assistant span as a passage [12] decision 2. Each passage linked to a concept appears in that page's "Who taught you this" or in its "more" list. Search covers all of them.
3. **Verification labels inform; they do not hide.** An unchecked AI claim appears in the explanation with its "○ unchecked" chip. A contradicted one moves to the page's history with its reason. "Opinion or advice" is labelled as such, which is what much AI teaching is [12 F9].
4. **"What did ChatGPT tell me about X?"** is a first-class query: search filters by speaker, product and model (§10.3).
5. **Monitored.** The AI-said share of cited items, pages and examples is compared with the golden set (§13). A drop is an alert, because shipped extractors drop assistant content [12 F3].

### 5.6 The user's own past is quoted, not retold

A conversational AI that narrates someone's past can implant confident false memories (Chan et al. 2024, [01 F11]). People also rewrite their past beliefs to match their present ones [01 F11].

- **Rule:** any claim about what the user believed, decided, said or did is rendered as a dated quote of the user's own words, with its source. The model may write about the world; it does not write about the user's past.
- **Validator V11** detects sentences citing the user's stance, decision or goal items and requires the quote form.
- This is also why "Who taught you this" is a list of quoted records (D12): it keeps the memory benefit of a story without retelling.

### 5.7 Desktop chat capture and the book

On Claude Desktop chat and ChatGPT Desktop Chat mode, live capture is only the model's own paraphrase through MCP. Verbatim text arrives later, if at all, through sync or export (SYNTHESIS Table A, RISK 4; [10] adapter table, checked 2026-10-07).

- Items captured from those surfaces carry fidelity `model_reported`. Their sentences show "paraphrased capture, verbatim pending".
- When the verbatim text arrives, the core reconciles the span (SYNTHESIS §3.1). The page's next printing drops the label, or flags "could not confirm wording" if the reconciler finds no match.
- The book never presents a paraphrase as a quote. Quote blocks (§5.6) require verbatim or reconciled fidelity.

---

## 6. What to learn

### 6.1 The five components

Built from [12] Model C and SYNTHESIS §3.2:

| Component | Source | How it is shown |
|---|---|---|
| **Goals** | The user's explicit statements of intent, verbatim, with date (Agenda items) | Goal pages in Part 0. **Possible directions** (inferred interests) are kept apart, labelled "inferred", and fade after 60 days without new evidence, because models over-infer user attributes [07 F7] |
| **Open questions** | Questions the user asked that no later item answers; questions spawned automatically from contested claims [12 F12] | The open-questions register in Part 0; each page's "Still open" |
| **Gaps** | (a) **dangling terms**: used in an explanation but never explained in the book; (b) **prerequisite gaps** on a goal's path; (c) **unchecked reliance**: an unchecked AI claim the user then used | On goal pages, chapter closes and page "Still open" sections |
| **Frontier** | The outer fringe of the prerequisite structure over the goal's subgraph: pages whose prerequisites are covered and which are not yet covered themselves [12 F11] | "Ready to learn next" on the front page (at most 7) and on goal pages |
| **Next steps** | A ranked view over the frontier, gaps and open questions: goal relevance, readiness, how much it unblocks, recency, and need for verification [12] Model C step 6 | "Next from here" on each page; "Next in this chapter" |

### 6.2 How it connects to what was learned

Every what-to-learn item links three ways:
- **to the learned pages it builds on**, for example "ready because you have covered 4.1.2 and 4.2.3";
- **to the conversation where it arose**, for example "you asked ChatGPT on 3 Oct" with the span;
- **to why it is ranked**, in one plain line.

Every learned page links forward: "Leads to", "Serves your goal" and "Next from here". So a reader can move from what they know to what is next, and back, at any point.

### 6.3 Not a task list

- No checkboxes, due dates, streaks or progress bars.
- Next steps are phrased as possibilities: "Ready to learn: Projections and CQRS".
- Each carries an optional **"Ask about this"** action. It copies a short, neutral prompt naming the topic and the relevant page, which the user can paste into any connected product. If they do, that conversation is captured and becomes a new source, so the book grows with full traceability. Ignoring it costs nothing.
- An answered question is never deleted. It moves out of the open register and its page records when, by whom and where it was answered.

### 6.4 "Covered" and the frontier, without a mastery score

The frontier needs a notion of "covered". This design uses exposure, which the system can observe honestly [12 F10]:
- a concept is **covered** when the core holds at least one explanation of it that reached the user (explained-to) or the user stated it themselves;
- this is shown as "covered: explained to you on 12 Sep", never as "learned" or "mastered";
- prerequisite edges are proposed by a model, with a separate direction check, and carry confidence [12 F11]. Frontier items whose edges are below a confidence threshold are labelled "suggested".

The goal page's **path** is the prerequisite chain from covered pages to the goal's target concepts, shown as a short ordered list. It is not a schedule.

---

## 7. Evolution: change without losing history or landmarks

### 7.1 Printings and editions

Textbooks already solve this: they have printings, editions, errata and revision histories.

| Unit of change | What changes | How often | Reader sees |
|---|---|---|---|
| **Printing** | Content only: new sentences, new examples, verification chips, refutation blocks, new short notes, new pages added at the end of their chapter's reading order | Nightly, after compilation and validation (§8) | "New since you last read" marks; a printing date |
| **Edition** | Structure: pages moved, chapters split or merged, relabelled; parts changed | At most weekly; part-level changes at most monthly | An "edition note" on the front page and on every affected page: what moved, why, and an undo button |
| **Correction** | Whatever the user changed (§9) | When the user acts | "Corrected by you on [date]" |
| **Just in** | Items added since the last printing, shown raw (gist, chips, link) at the top of the relevant section | About 2 hours after capture, from the slow lane (SYNTHESIS §3.5) | A small "Just in" strip, so nothing waits for the nightly compile |

Every printing and edition is kept. The reader can open any page "as of" a date (core as-of queries, SYNTHESIS §5 item 3).

### 7.2 Landmark stability

People navigate by recognition and place, and churn destroys that [12 F16][02 F2]. GOAL makes AI reorganisation the default (§4.3). The tension is real (SYNTHESIS RISK 15). These rules ration change:

1. **Permanent IDs and links.** Every page, chapter and part has a permanent ID. Its link never changes. Display numbers ("4.2.3") change only in an edition, and old numbers redirect with a "moved on [date]" note (Luhmann's fixed addresses [02 F1]).
2. **Evolutionary clustering with a history cost.** The weekly reorganiser (J8 [13]) scores a proposed structure on quality minus a penalty for departing from the current one (Chakrabarti et al. 2006, [12 F16]). It applies the proposal only if the net gain clears a threshold.
3. **A stability budget per edition** (starting values, calibrated on the golden book):
   - at most 5% of pages moved;
   - at most 2 chapter splits or merges;
   - at most 1 part-level change per month;
   - a rename only if the new label beats the old one by a set margin in a pairwise judgement, and the old label stays as an alias in search and the index.
4. **Matched clusters keep their IDs and labels.** A chapter that survives with most of its pages keeps its identity.
5. **User placements are hard constraints** (I21; §9).
6. **Dormant topics fold in place.** A chapter untouched for 120 days collapses in the contents with "dormant since [date]". It is not moved, so its place is kept, and it does not crowd current work (mausoleum effect [02] pitfall 8).

### 7.3 How each kind of change is rendered

| Change in the core | In the book |
|---|---|
| New item linked to a page | "Just in" until the next printing, then woven into the explanation or examples, marked "new" until read or for 14 days |
| Supersession (SYNTHESIS §3.1 step 2) | The old sentence is struck through but stays visible, linked to a refutation block (§7.4) |
| Verification change | The chip changes. A "corrected" errata entry goes to the changes log. If a claim becomes contradicted, it moves to the page's history with its reason |
| Contested claim (§3.1 step 5) | Both sides in "Still open", each attributed; a spawned question in Part 0 |
| Excision (user-started) | A tombstone: "removed at your request on [date]" with no content |
| Merge of two concepts | An alias: both old links resolve to the merged page, which notes "merged from" with undo |
| Split | Two pages, each noting "split from" with undo; the old link shows a short chooser |

### 7.4 Refutation blocks for changed understanding

When an item the user held is superseded, the page shows a block shaped like a refutation text (E10, [01] idea 5):

| Field | Source |
|---|---|
| **You thought** | The superseded item, quoted, with date |
| **Why it seemed right** | The cited reasons the old item had (its supporting items), if any. If none are recorded, the block omits this line rather than inventing one |
| **What changed it** | The superseding evidence: an AI self-correction, a verifier result, a new source, or the user's own later statement, each attributed |
| **You now hold** | The new item, quoted if it is the user's own, otherwise attributed |

The block appears inline on the next three visits to the page (co-activation of old and new, KReC [01 F5]). Then it folds into "How your understanding changed" further down. It is never deleted.

### 7.5 "What changed since you last read" and how understanding evolved

- **Read markers** are per reader and local: the last printing seen for each page. They are human-side state only. They never enter AI packs, and reading is never treated as learning.
- **Front page:** "Since you last opened Northstar (3 days ago)", with counts and at most seven links: new pages, changes of understanding, new disagreements, pages with new material.
- **Pages:** change bars in the margin beside new or changed sentences.
- **Changes view:** every printing and edition, with each change linked to its ledger event and its undo.
- **Per page:** "Who taught you this" and "How your understanding changed" together form the idea's history, as quoted records.
- **Timeline view:** month by month, what entered the book, which questions opened and closed, and which views changed. This is the book-level answer to "how did my understanding evolve?". It is generated; the user writes nothing.

### 7.6 Restructuring, not just patching

Some conceptual change is a change of category, not an edit to one claim (Chi 2008, [01 F6]). Item-level edits cannot express it.

- Each page keeps an **anomaly count**: items attached to it that the linker marked as contradicting or not fitting its key idea [01] idea 8.
- Past a threshold, J8 proposes a restructure for the next edition: split the page, re-categorise it, or replace its key idea. The proposal goes through the same stability budget and blast-radius cap (I13).
- The edition note explains the restructure, and the old structure stays viewable as of its date.

---

## 8. How the AI writes the book reliably

The maintainer can lose focus (GOAL §3.4, §4.7). So structural correctness never rests on one model call. Code assembles inputs, validates outputs and decides what is published [13].

### 8.1 Pipeline

1. **J5–J6** (core) link and apply items. Each applied event names the items it touched.
2. **Dirty marking** (code): a dependency index maps each item to the page sections that cite it or should. Relation changes mark the "Where this fits" and "Next" sections of both endpoints.
3. **J7 compile** (nightly, batch): one stateless call per dirty prose section, from leaves only.
4. **Validators** V1–V13 (code), then **entailment sampling** (a different-family model).
5. **Publish** the printing atomically. The previous printing stays.
6. **J8 reorganise** (weekly): proposes an edition under the stability budget; code applies it or rejects it.
7. **J10 audit and J11 repair**: metrics, error budgets, rollback by job, batch or model [13].

### 8.2 Inputs: leaf items only

J7's input assembler type-checks that it receives only leaf items and source spans, never earlier page text (I7 [13]). This is "never summarise summaries" made checkable (GOAL §5; [12 F4]).

| Section | Built from |
|---|---|
| Key idea | The concept item's definition item, if any, plus the top items by centrality and support |
| Explanation segments | The page's best-rank Statements and Passages, grouped by the linker's sub-topic labels |
| "e.g." lines and From your work | Episodes linked to the concept with `example_of` or `applied_in` relations, and their spans |
| Who taught you this | Attribution records and spans; rendered by code, no model |
| How your understanding changed | Supersession records and their items; rendered by code, no model |
| Still open, Next from here, Where this fits | Agenda items, relations and frontier computation; rendered by code, no model |
| Chapter big picture | Leaf items linked to two or more of the chapter's pages, selected by code |

Only three kinds of section are model-written: key ideas, explanation segments (with their headings), and the "what these share" line. Everything else is deterministic rendering of records.

### 8.3 The output contract

Each J7 call returns structured output. Each sentence carries its citations and a role:

```yaml
section: explanation
segments:
  - heading: {text: "Events are the record; tables are views", cites: [it_81, it_92]}
    sentences:
      - {text: "...", cites: [it_81], role: explain}
      - {text: "...", cites: [it_92, it_95], role: contrast}
      - {text: "...", cites: [it_97], role: caveat}
    example: {episode: ep_311, span: sp_9002}   # quote is pulled by code from the span
```

Roles: `explain`, `contrast`, `caveat`, `connect`, `share` (the line after cases). The model chooses which span to use as an example. Code pulls the quote text, so a quote can never be invented.

### 8.4 Deterministic validators

All run on every compiled section. A failure rejects the section and triggers one retry in a fresh call, possibly on another model [13].

| # | Check | Ties to |
|---|---|---|
| V1 | **Citation closure:** every sentence and heading cites at least one item | I8 |
| V2 | **Citation validity:** cited items exist, are in scope, and are active or explicitly historical; deprecated items appear only in history blocks | I17, SYNTHESIS §3.1 |
| V3 | **Leaf-only input:** the call's input contained no page text | I7 |
| V4 | **No attribution in model text:** no speaker names, product names or attribution verbs | §5.3 |
| V5 | **Speaker voice:** a second-person belief or decision sentence cites a user-spoken item with stance asserted or accepted | I3, I4 |
| V6 | **Hedge cap:** if a cited item is tentative, the sentence keeps a hedge, or the renderer adds "(tentative)" | I10 |
| V7 | **Specifics check:** every number, date, version, proper noun and code identifier in a sentence appears in its cited items or spans | catches invented details |
| V8 | **Quote fidelity:** every quote is an exact substring of its span | I2 |
| V9 | **Coverage monotonicity:** a rebuilt section does not drop a cited item unless an event explains it | I9 |
| V10 | **Size and anatomy:** the limits in §4.2 | D5 |
| V11 | **Autobiography rule:** claims about the user's past beliefs or decisions use the quote form | §5.6 |
| V12 | **Deterministic parts rebuild identically** with model access disabled | I18 |
| V13 | **Blast radius:** caps on sections and pages touched per job | I13 |

### 8.5 Upper levels never summarise lower levels

- **Chapter "In this chapter" and "Recap"** transclude each page's key idea word for word, with its citations. No new prose.
- **Chapter big picture** is compiled from leaf items selected by code (those linked to two or more of the chapter's pages), never from page text.
- **Part openers, the contents, the front page and the timeline** are deterministic assemblies.
- **Glossary entries** are the cited definition items, rendered by code.

### 8.6 Incremental recompilation

- **Section granularity.** Each section records its `built_from` set: item IDs and versions. A section is rebuilt only when that set changes. Untouched sections keep their exact text, which also keeps familiar wording stable for the reader.
- **Key ideas** rebuild only when their cited items change, or when a new item enters the concept's top items.
- **Chapter big pictures** rebuild only when their cross-cutting item set changes.
- **Nightly batch.** Dirty sections are deduplicated across the day's events and compiled in one batch. Opening a dirty page shows the last good printing plus the "Just in" strip; it never blocks on the model.
- **Full rebuilds** happen only after a prompt or model change. They run on the golden book first, then in stages (§8.9).

### 8.7 Entailment spot-checks

A model from a different family checks whether each sampled sentence follows from its cited items. The working assumption is a local open-weight model on the Mac (SYNTHESIS AD9, spike S10), so no data leaves the machine.

| Sentences | Sample rate |
|---|---|
| Key ideas (they are transcluded upward and into in-chat slices) | 100% |
| Headings | 100% |
| Sentences in a page's first printing | 100% |
| Sentences citing contested, superseded or user-stance items | 100% |
| Other changed sentences | 20% |
| All sentences on a page after any failure on it | 100% for its next 3 printings |

- **On failure:** the sentence is removed and its section is rebuilt once in a fresh call. If the rebuild fails too, the section is published in its **fallback form**: a plain bulleted list of its cited items' gists, with chips. It is less pleasant to read, but every line is true.
- **Error budget:** if the sampled failure rate exceeds 3% over 7 days (starting bar), J7 freezes on its last good prompt and model, and pages keep their last good printing (J10, J11 [13]).
- **Audit:** the daily L4 audit by the strongest model samples 1% of published sentences with full context (SYNTHESIS §3.5).
- Volume is about 100–150 checks a day at full load, which a local model handles.

### 8.8 Cost at about 36K events a year

Assumptions (mine; ±2×): about 100 events a day [13 §I]; after deduplication about 50 dirty prose sections a night; about 8 chapter big pictures a night; each section call about 6K input tokens (2K of them a cached charter) and 0.6K output; prices as in [13 F11] (Sonnet 5.5 batch: $1 per million input, $5 per million output).

| Item | Per day | Per month |
|---|---|---|
| Section compiles: 50 × ~$0.0072 | ~$0.36 | ~$11 |
| Chapter big pictures: 8 × ~$0.012 | ~$0.10 | ~$3 |
| Retries and fallbacks (+20%) | ~$0.09 | ~$3 |
| Entailment checks on a local model | $0 | $0 |
| **Total, Sonnet batch** | **~$0.55** | **~$17** |
| Same on Haiku 5.5 batch (quality unmeasured) | ~$0.03 | under $1 |
| Same at 20 turns a day instead of 100 | ~$0.11 | ~$4 |

- A full rebuild after a prompt or model change: about 1,500 pages × 5 sections ≈ 7,500 calls ≈ $55 once, on batch.
- Storage: section build records for one year are tens of megabytes. SQLite is enough [13 §I].
- If the user later allows a cross-vendor checker instead of the local one (gpt-5-mini batch), entailment adds about $1 a month.
- Page count assumption: about 15K active leaf items a year, giving about 800–1,500 concept pages and 2,000–4,000 short notes after the promotion gate (§4.7).

### 8.9 What the maintainer checks

| Signal | Bar or alert (starting values) |
|---|---|
| Citation closure, citation validity | 100% (hard gate; V1, V2) |
| Sampled entailment failure | ≤ 3% over 7 days, else freeze |
| Speaker-voice and autobiography violations after validation | 0 |
| AI-said share of cited items, pages and examples | within 10 points of the golden-set share |
| Fallback sections | alert if more than 2% of sections are in fallback form |
| Freshness | 95% of new items appear in "Just in" within 3 hours and in a printing within 30 hours |
| Landmark churn | within the stability budget (§7.2); A→B→A oscillation alerts |
| Correction survival | 100% after every printing and edition (hard gate, I21) |
| Short-note pool | promotion and fold rates stable week on week |
| Prompt or model change | golden-book canary passes before any full rebuild |

---

## 9. Corrections

Correction is optional. Nothing waits on it (GOAL §4.3). Once made, it persists with precedence (SYNTHESIS §3.2, I21).

### 9.1 One click in the book

| Where the reader acts | One gesture | Recorded as |
|---|---|---|
| Sentence menu | "Not right" | The cited item gets user stance `disputed`; with an optional "what's right?" text, a new user-typed item supersedes it (`reason: user_correction`) |
| Chip menu | "Someone else said this" | Attribution fix |
| Chip menu | "Not what I think" | Stance fix on a user item |
| Sentence or example menu | "Hide" or "This example doesn't fit" | Hide, or reject the `example_of` relation |
| Page header | "Rename", "Move to…", "Pin here", "Undo merge" or "Undo split" | Label, placement (must be under or must not be under), pin, unmerge |
| Contents | Drag a page to another chapter | Placement correction |
| Changes view | "Undo" on any edition change | Placement and structure constraints |

Every correction is a typed ledger event with holder `user` and origin bound as user-typed (I20). The page shows "Corrected by you on [date]", with undo.

### 9.2 Through chat

- **A write tool, `northstar_correct`,** on the Northstar MCP server, taking a target (page, sentence, item, or a plain-language reference resolved by the server against the page), a kind, and the user's own words.
- **Hook surfaces (Claude Code, Codex):** the adapter matches the user's words against the verbatim prompt from `UserPromptSubmit`. A match binds the correction as user-typed ([10] F5, F9; https://code.claude.com/docs/en/hooks and https://learn.chatgpt.com/docs/hooks, checked 2026-10-07 by [10]).
- **Desktop chat surfaces:** the tool call is model-mediated. It needs the user's approval in the product's own prompt ("Allow once" on Claude, per-conversation confirmation on ChatGPT; [10] F1, F6, checked 2026-10-07). That approval is the user acting, so it is not a routine. The correction is applied at once with fidelity `model_reported`, then reconciled against the verbatim transcript when it arrives (§5.7). If the user's words cannot be found there, the correction is kept but marked "unconfirmed wording" and loses its precedence.
- **Injection guard:** the server rejects a correction whose "user words" match assistant or tool text rather than user text, where known. Only user-typed text can create corrections, as with instructions (I5).

### 9.3 Precedence

- No automated event may undo or contradict an active correction (I21).
- J8 takes placements, pins, labels and merge refusals as hard constraints. J7 and the deterministic views replay corrections after every rebuild, so they survive every printing and edition.
- Only the user, or excision of the target, lifts a correction.
- If later evidence disagrees with a correction, the correction stands and a chip says "newer evidence disagrees". Nothing is escalated to the user.
- Corrections also become L6 labels for calibrating the maintainer (SYNTHESIS §3.5). Their survival is a hard gate (§13).

---

## 10. The interface

### 10.1 Medium: a local web app now, the same app in the cloud later

| Option | For | Against | Verdict |
|---|---|---|---|
| **Local web app** served by the Northstar core on localhost | Full control of typography, margins and chips (D2, D3, D13); one-click corrections; search; works offline; the same renderer can be hosted later | The core must be running; Mac only for now | **Primary reading surface** |
| Markdown vault (Obsidian-compatible) | Durable plain files [02 F8]; familiar | Readers would edit derived pages, which then diverge from the core ([07] pitfall 6); chips and one-click corrections are hard; invites global graph views [12 F15] | **Read-only export only** |
| MCP App panels only | Inside the chat | Small viewport; not for long reading; ChatGPT Desktop support is unverified | **In-chat slices only** (§10.5) |
| Native Mac app | Polish | Build cost; does not move to cloud | A later wrapper at most |
| EPUB or PDF export | Reading on any device, offline | Static; no corrections | **Export** |
| Hosted cloud page | Phone and tablet reading | Data leaves the Mac | **Cloud phase** |

**Local now.** The core renders each printing to static HTML pages plus a small JSON index. A thin local server adds search, the source viewer, corrections and read markers. Opening the book means opening a localhost address, from a menu-bar item, a command (`northstar open`), or a link in an in-chat slice.

**Cloud later.** The same renderer and API run behind authentication. Read markers move server-side per reader. Phone reading comes with it. Enterprise later adds single sign-on and scopes (§10.6). Nothing in the page format depends on where it runs.

**Exports.** Markdown and EPUB, read-only, regenerated each printing, so the knowledge outlives the app [02 F8].

### 10.2 Navigation

- **Contents sidebar:** parts and chapters as a collapsible tree (trees and outlines have evidence; global graphs do not [12 F15]).
- **Breadcrumbs** and **permanent links** on every page.
- **Previous and next** within a chapter, in prerequisite order (§4.5).
- **Builds on, Leads to, Serves your goal** links on every page.
- **Local map** on pages with relational structure: up to 9 nodes, one hop, filtered by relation type (D9).
- **Timeline view** (§7.5) and **changes view** (§7.1).
- **Index and glossary;** glossary terms show their cited definition on hover.

### 10.3 Search

- **Hybrid:** SQLite FTS5 keyword search plus embeddings, over pages, short notes, items and all stored spans, including quarantined proposals' source spans, which are labelled "uncertain" (SYNTHESIS §3.5).
- **Results grouped by page,** each showing the matching sentence with its chips.
- **Filters:** speaker (you, Claude, ChatGPT, Codex, documents), product, model, date range, verification status, conversation, goal.
- **Typed queries:** "what did ChatGPT tell me about X", "what did I conclude about X", "what's still open on X" map to filter presets.

### 10.4 The first screen

The front page answers "where am I going, what changed, where was I?" in four blocks of at most seven items each (D1, D5, D11, D16):

```
NORTHSTAR — your book                                        Search [            ]

WHERE YOU'RE HEADING
  Goal  "Design an event-sourced ledger"  (you, 7 Oct)
        Ready to learn next: Projections and CQRS · Bitemporal data · Deleting from logs
  Goal  "Get comfortable with Rust lifetimes"  (you, 20 Sep)
        Ready to learn next: Lifetime elision · The borrow-checker errors you hit
  Open questions you asked: 6   newest: "How do I delete personal data from an append-only log?"

SINCE YOU LAST OPENED  (3 days ago)
  New pages            Bitemporal data · Snapshotting
  Understanding changed  Event sourcing: "tables are just caches" → "snapshots make the log usable"
  New disagreement     Snapshot frequency (Claude vs ChatGPT)
  New material on 5 pages                                              → all changes

CONTINUE READING
  Event sourcing (a chat touched it yesterday) · Rust lifetimes · Idempotency

CONTENTS
  0 Where you're going · 1 Software architecture · 2 Rust · 3 Data stores · ... · 9 Casebook
```

If the user has no explicit goals yet, the first block shows "Most active topics this month" and the open questions instead. It never invents goals.

### 10.5 In-chat slices on the connected products

A slice is a compiled section of the book, shown inside a chat. It is never newly generated text, so the chat and the book always agree. A slice is at most about 400 words (D5), carries its chips, and links to the full page.

**Slice types:**
- **page card:** key idea, up to three cited points, the sources line, "open in book";
- **"what did I learn about X":** the matching page cards, or short notes if no page exists;
- **"what's next for goal G":** the goal's frontier and open questions;
- **"what changed since [date]":** the changes digest.

| Product | Channel | How the slice appears | Facts and status |
|---|---|---|---|
| **Claude Desktop chat** | A local stdio MCP server configured in Claude Desktop, so no public endpoint is needed now | An **MCP App** card rendered inline after the user allows it; "open in book" uses the SDK's `openLink` | Claude Desktop runs local servers from its config file, and MCP Apps "render inline in the conversation" after **Allow** (https://claude.com/docs/connectors/building/mcp-apps/getting-started, checked 2026-10-08). The App SDK lists `openLink` (https://apps.extensions.modelcontextprotocol.io/api/classes/app.App.html, checked 2026-10-08). Whether `openLink` may open a localhost address is (Unv). |
| **Claude Code** (terminal and the Desktop Code tab) | MCP tool, plus a plugin skill | A Markdown slice as the tool result, citations as footnotes, with the localhost link | Claude Code takes MCP output up to 25K tokens by default (https://claude.com/docs/connectors/building/index, checked 2026-10-07 by [10]). |
| **ChatGPT Desktop, Chat mode** | Northstar plugin (MCP server) | A widget card where the client renders app widgets; otherwise the same Markdown slice | Chat mode uses plugins as on the web, selected per chat, with plan eligibility unclear ([10] F6, F9; https://learn.chatgpt.com/docs/plugins and https://til.simonwillison.net/llms/mcp-in-claude-and-chatgpt, checked 2026-10-07 by [10]). Apps SDK docs say components "run inside an iframe in ChatGPT" but name no platforms (https://developers.openai.com/apps-sdk/build/state-management, checked 2026-10-08). Widget rendering in Desktop Chat mode is (Unv). |
| **Codex** (CLI and ChatGPT Desktop local threads) | Local MCP server via `~/.codex/config.toml` | Markdown slice with the localhost link | The desktop app shares MCP configuration with the Codex host ([10] F9; https://learn.chatgpt.com/docs/extend/mcp, checked 2026-10-07 by [10]). |

**Slices as spaced re-encounters (D11).** The AI side's context composer already selects relevant items for each chat (SYNTHESIS §3.3–3.4). When it selects a concept that has a page, and the reader has not opened that page for at least 7 days, the product may show the page card where a user-visible channel exists, with a line such as "you first met this with Claude on 12 Sep". The gap grows each time (7, 21, then 60 days), roughly following the spacing evidence (Cepeda et al., [01 F8]). At most one unsolicited card appears per chat. It is a card, never a question. Which channels can show a card the user sees, unprompted, is (Unv) on several products, so this lever will be uneven (§15).

**Privacy of slices.** A slice shown in a chat enters that vendor's model context. Slices follow the same scope and sensitivity rules as AI packs (I17; SYNTHESIS §5 item 9). Content captured from one vendor goes to another vendor only if its scope allows cross-vendor use, which is the AI side's policy too.

### 10.6 Accounts, scopes and later stages

- **Personal first.** One book per personal scope.
- **Enterprise later.** A work scope gets its own book, or its own parts, governed by that scope's rules. Pages never cite across scopes (I17). Work-scope Casebook chapters stay inside the work book.
- **Accessibility.** Chips use glyph plus word, not colour alone. Light and dark themes. Keyboard navigation through contents and pages. Text resizes without breaking the margin rail.

---

## 11. Non-goals, and the one optional aid

### 11.1 Non-goals

- **No quizzes** as part of the product. No question is put to the reader to test them.
- **No mastery scores**, levels, badges, progress percentages or "known/unknown" ratings. Engagement events drive only the frontier and the register switch, and are shown as plain history ("explained to you on 12 Sep"), never as a measure.
- **No required routine:** no review queue, inbox, daily digest to clear, streaks or reminders. Nothing degrades if the book is never opened.
- **No user-maintained structure:** no filing, tagging or linking by the user.
- **No editor for the book's prose.** Derived pages are not edited directly; corrections are the path ([07] pitfall 6).
- **No global graph view by default** [12 F15].
- **No background explanations written by Northstar itself** that are not drawn from the user's sources (§8.2; see Q2).

### 11.2 The optional aid: cover mode

Retrieval practice is the largest memory lever in the evidence (g = 0.50–0.61, E11). The book can offer it without becoming a quiz:

- **What it is:** a toggle on any page that collapses each explanation segment under its heading. The reader can try to recall what follows, then open it.
- **Off by default.** It must be switched on per page or for the whole book.
- **No scoring and no record.** Northstar does not ask whether the reader remembered, does not log what was opened in cover mode, and does not schedule anything.
- **The product does not depend on it.** Every rule except D11b works with it off. All evaluation (§13) runs with it off.

Whether to include even this is a question for the user (Q1).

---

## 12. What the core must hold for the book

The system spine provides the core. This is what the book needs from it.

| Record | Fields the book needs | Used for |
|---|---|---|
| **Item** (Concept, Statement, Passage, Agenda) | stable ID, role, kind tags, text, gist, qualifiers, concept links, best rank and rank reason, version | Every section |
| **Attribution** | speaker by construction, speaker ID (model, product, surface), span, modality, verbatim hedges, lineage origin | Chips, V4–V6, §5.3 |
| **Stance** | holder, attitude, evidence, span, belief time | "You" sentences (V5), refutation blocks, corrections |
| **Verification** | checkability, status, verifier model, independence flag, evidence, checked date, re-check date | Chips, ranking, "Still open" |
| **Span and source** | source type and ID, locator, quote, prefix, suffix, capture fidelity, branch path, model, browsing flag; conversation title and product link where available | Source viewer, quotes (V8), fidelity labels |
| **Episode** | product, surface, model, start and end time, title, project or repository or working directory | Examples, Casebook, sources register, timeline |
| **Project or context** | stable ID, name, kind, episodes | Casebook chapters, "e.g." lines |
| **Relation** | type (explains, defines, example_of, applied_in, part_of, prerequisite_of, compares, supports, rebuts, refines, answers, supersedes, same_as, contests), confidence, status, creator | Where this fits, examples, frontier, pictures, gaps |
| **Supersession** | old item, new item, reason, the old item's supporting items | Refutation blocks (§7.4) |
| **Tension** | sides, resolution state, spawned question | "Still open", contested register |
| **Engagement events** | concept, kind (explained-to, asked-about, used, restated, disputed), span, time | Covered (§6.4), register switch (§4.6), re-ask and restatement metrics (§13 D) |
| **Anomaly marks** | item, page, kind (contradicts or does not fit the key idea), from the linker | Restructure proposals (§7.6) |
| **Goal and question status** | explicit or inferred, active, paused, done, expired; open, answered, dormant; answering items | Part 0, frontier |
| **Correction** | target, kind, payload, origin, fidelity, active flag | §9, I21 |
| **Structure events** | split, merge, move, rename, pin, with before and after | Editions, undo, changes view |
| **Landmark registry** | part, chapter and page IDs; current and past labels and display numbers; redirects | Permanent links, aliases in search |
| **Build records** | page, section, sentences with cites, `built_from` item versions, model, prompt hash, printing ID, check results | Incremental rebuilds, as-of views, audits |
| **Scope and sensitivity** | on every item, span and page | Slices, exports, cross-vendor rules |
| **Excision tombstones** | target, date | Tombstones in the book; zero-hit grep |

**Queries the book needs:** best-rank projection; as-of any date; items changed since a watermark; the dirty set for a printing; relations by type over a subgraph (for the frontier).

**Kept on the human side, not in the core:** read markers, register and cover-mode settings, and the last-visit times used for the re-encounter gaps. These are per-reader view state. They never enter AI packs.

---

## 13. Evaluation

This adapts SYNTHESIS §7.3. Every check runs without user sessions. User input is optional and one-off.

### 13.1 The golden book

- **Data:** synthetic personas whose chats span all four first connectors, with both speakers, generated from a hidden "world ledger" by a model family other than the system's (SYNTHESIS §7 ground rules). It includes at least one document source.
- **Gold:** an expected outline (parts, chapters, page assignments), expected key ideas, expected supersessions and contested items, and expected attributions.
- **Use:** calibrates the starting values in §4.2, §7.2 and §8.9, then they are frozen; runs nightly and before any full rebuild.

### 13.2 Checks

| Group | Check | Measure and starting bar |
|---|---|---|
| **A. Truth and attribution** (hard gates) | Provenance completeness | 100% of sentences resolve to an item and a span |
| | Citation faithfulness | Sampled entailment ≥ 97%; hedges and rare details kept after N regenerations (SYNTHESIS §7.3) |
| | Attribution | Golden-set accuracy; false endorsement ≤ 5%; speaker-voice and autobiography violations 0 |
| | AI-said coverage | Share of golden AI-taught items reachable from the book; AI-said share within 10 points of gold |
| | Correction survival | 100% after N printings and editions (I21) |
| **B. Reads like a textbook** (automatic) | Anatomy completeness | Every concept page has key idea, explanation and sources; examples present wherever linked episodes exist |
| | Segment and sentence sizes | Within §4.2 limits |
| | Heading fidelity | Headings entailed by their segment's citations (100% sampled) |
| | Cohesion | Adjacent-sentence overlap and connective density in the learning register above the reference register (Coh-Metrix-style indices) |
| | Organiser coverage | Each chapter opener links ≥ 80% of its pages; every page links to at least one prerequisite or is marked foundational |
| | Self-reference rate | Share of concept pages with an example from the user's own work, where such episodes exist |
| | Outline quality | Agreement with the gold outline (adjusted mutual information), duplicate pages ≤ 5% |
| **C. Helps understanding** (simulated readers) | Comprehension A/B | A reader model from a third family, given only one rendering at equal length, answers held-out questions written from the leaf items. Two kinds: **textbase** (stated facts) and **inference** (combine two items, or apply the idea to a held-out case). Renderings: (1) the textbook page; (2) a date-ordered list of the same items; (3) an uncited wiki page compiled without the anatomy (Karpathy-style [12 F7]); (4) raw excerpts. **Bar:** (1) beats (2) by ≥ 10 points on inference questions with no loss on textbase questions; (1) matches (3) on inference with higher faithfulness |
| | Novice reader | The same with a smaller reader model, standing in for low prior knowledge; tests the learning register (E4) |
| **D. Helps remembering** (passive proxies) | Re-ask rate | Share of user turns asking an AI to re-explain something the book has held for ≥ 7 days. Compared before and after a page exists, and between concepts randomised to re-encounter cards on or off. **Bar:** ≥ 20% fewer re-asks with cards on. Follow-ups that go deeper are classified apart and not counted |
| | Natural restatements | When the user restates an idea unprompted in a chat, does it agree with the page's key idea? Reported only as an aggregate over all concepts, never per concept, never stored on a page |
| | Navigation | Search followed by a page open with no repeat search; time from opening the book to reaching a page |
| | Optional one-off check | If the user volunteers: explain three topics from memory, one week after reading their pages, against three unread topics. Never required |
| **E. Stability and evolution** | Churn | Label and ID changes per edition within budget; A→B→A oscillation; share of part and chapter IDs and labels unchanged over 30 days |
| | Change log precision | Every "what changed" entry maps to a ledger event; every event that changes a page appears |
| | As-of reproducibility | Rebuilding a past printing's deterministic parts is hash-identical |
| **F. What-to-learn validity** | From SYNTHESIS §7.3 | Prerequisite precision and direction against curated sources where they exist; open-question precision; dangling-term precision; frontier predictive validity (share of frontier items the user later engages with) against random and popularity baselines |
| **G. Fault injection** | Degrade J7 | Weak model, shuffled citations, padded input, missing job card, prompt bug. Measure: structural errors blocked (target 100%); planted unsupported sentences caught by entailment; time until the error budget trips; rollback restores hash-identical deterministic parts |

**Ablation** applies to HOW layers only, such as the register switch, the re-encounter cards or the picture section. A component GOAL requires, such as the what-to-learn side, AI-said passages or source traceability, can be redesigned but never cut (SYNTHESIS §7).

---

## 14. Questions for the user

Only questions that touch the WHAT or accept a risk. Each has a working assumption, pending your answer. Silence is not taken as an answer.

| # | Question | Working assumption (pending your answer) |
|---|---|---|
| **Q1** | GOAL says the human side "is not a quiz". Do you want the one optional aid, **cover mode** (§11.2): off by default, no scoring, nothing recorded? Or no retrieval aid at all? | Include it, off by default |
| **Q2** | Every sentence must trace to who said it and in which conversation. So the book will **not** add background explanations of its own when your sources leave a gap; it will list the gap under "what to learn" with an optional "Ask about this" prompt (§6.3). Is that right, or do you want short Northstar-written glosses, clearly labelled as not from your conversations? | No Northstar-written glosses |
| **Q3** | Should **project-specific knowledge** (for example, how one repository is set up, from Claude Code or Codex sessions) be part of the book? This design puts it in a **Casebook** part and uses it as examples, apart from transferable knowledge. | Yes, in the Casebook part |
| **Q4** | The evidence says reading, even well-designed reading, gives modest memory gains; the strongest memory levers need the reader to act (§3.2). The design adds self-reference, refutation blocks and re-encounter cards, and measures remembering only through proxies. Do you accept that "remember" will be helped modestly unless you choose to do more? | Accept, and report the proxy results honestly |

---

## 15. Risks

| # | Risk | Threatens | Mitigation |
|---|---|---|---|
| **H1** | **The memory ceiling of reading.** Rereading is low utility; spaced rereading effects are small and inconsistent; retrieval and generation are optional. Related to SYNTHESIS RISK 17 | GOAL §3.2 "remembers" | Self-reference (D7), refutation blocks (D10), quoted stories (D12), re-encounter cards (D11), optional cover mode; proxy metrics (§13 D); Q4 |
| **H2** | **A polished book makes AI errors look authoritative.** Fluency raises felt understanding; textbook typography adds authority | GOAL §4.2 with §6 "each item shows its sources"; SYNTHESIS RISK 7 | Speaker and verification chips on every sentence (Kim et al.); "Still open" given equal weight (D14); never "mastered"; contradicted claims shown in history, not hidden |
| **H3** | **The evidence may not transfer.** Effect sizes come from short lab sessions with students; several are secondary; effects do not add | All design rules | Treat rules as hypotheses; §13 B and C test them; ablate HOW layers that move nothing |
| **H4** | **Provenance against coherence.** Chips on every sentence can add load like seductive details | D3 vs D13 | Margin rail and on-demand detail; compare chip densities in the simulated-reader A/B |
| **H5** | **Landmark churn** from automatic reorganisation | Navigation; SYNTHESIS RISK 15 | Permanent IDs, editions, stability budget, history cost, folding in place, user pins (I21), undo |
| **H6** | **Self-reference examples expose or upset.** Work content may be sensitive; negative episodes reverse the self-reference effect | Privacy; D7 | Scope and sensitivity tiers; prefer neutral episodes; never distressing material; "This example doesn't fit" correction |
| **H7** | **Simulated readers are not people.** §13 C may not predict human comprehension | §13 validity | Use C only for relative comparisons; optional one-off human check (§13 D) if the user volunteers |
| **H8** | **Desktop chat lag.** Pages built from Claude Desktop chat and ChatGPT Desktop chat cite paraphrased spans until verbatim text arrives, and some may never be reconciled | GOAL §3.2 traceability; SYNTHESIS RISK 4 | Fidelity labels; quotes only from verbatim or reconciled spans; reconciliation metrics |
| **H9** | **The leaf-only rule leaves explanatory holes.** Without background glosses, some pages will use terms the book never explains | "Reads like a textbook" | Dangling terms become gaps with "Ask about this" (§6); Q2 |
| **H10** | **A noisy frontier** loses trust. Prerequisite extraction is about F1 0.7, with reversed direction common [12 F11] | "What to learn" | Direction check, confidence labels, "suggested" marking, frontier predictive-validity metric (§13 F); SYNTHESIS R3 |
| **H11** | **Contested items crowd pages** | Readability; SYNTHESIS RISK 22 | "Still open" holds at most 3 per page with "more"; count-and-age sentinels |
| **H12** | **Book bloat.** About 1,000+ pages a year | Navigation, "mausoleum" [02] | Promotion gate (§4.7), short notes, dormant folding, chapter split proposals |
| **H13** | **Slices send book content to vendors** | Privacy | Slices follow pack scope rules; cross-vendor only where scope allows |
| **H14** | **Uneven in-chat support.** ChatGPT Desktop widget rendering, `openLink` to localhost, and user-visible unsolicited cards are unverified on several products | Re-encounter lever; in-chat slices | Markdown fallback everywhere; spikes listed below; report per product |
| **H15** | **Compile cost or quality drift** on cheaper models | §8 | Golden-book canary before switching models; error budget freeze; fallback form |

---

## 16. Goal-fidelity check

| GOAL clause | Where this design meets it |
|---|---|
| §3.2 "what has been learned, from the user's own thinking and from what AIs taught" | §5; AI-taught first-class rules §5.5; promotion gate ignores speaker §4.7 |
| §3.2 "what to learn: goals, gaps, open questions, next steps" | §6; Part 0 §4.1; links both ways §6.2 |
| §3.2 "reads like a textbook … understands and remembers" | Evidence-derived anatomy §3–§4; registers §4.6; evolution as editions §7; evaluation §13 B–D; memory limits stated §3.2, Q4 |
| §3.2 "traceable to its sources: who said it, and in which conversation" | Chips §5.2; code-written attribution §5.3; two-click path §5.4; sources register §4.1 |
| §3.2 "not a quiz or a mastery score" | §11.1; covered-as-exposure §6.4; register switch not shown as a level §4.6 |
| §3.2 "browses it and can correct it"; "any routine is optional" | Interface §10; corrections §9; cover mode optional §11.2 |
| §4.1 a system, no rituals | All maintenance is code and stateless jobs §8; nothing waits on the user; "Just in" strip removes any need to visit |
| §4.2 AI-said first-class | §5.5; AI-said share monitored §8.9, §13 A |
| §4.3 AI manages it; correction optional | J7, J8 automatic §8, §7; corrections optional and persistent §9 |
| §4.4 two architectures over one core | The book is a projection of the shared core §12; read markers stay human-side |
| §4.5 drift and continuity | Owned by the AI side. The book reuses the AI side's relevance selection for re-encounter cards §10.5 and adds nothing to its packs |
| §4.6 product-agnostic, connectors; local now, cloud later; personal first | Slices for all four first connectors §10.5; local web app now, same renderer in cloud §10.1; scopes §10.6 |
| §4.7 robust maintainer | Leaf-only inputs, 13 validators, different-family entailment, fallback form, error budget, fault injection §8, §13 G |
| §4.8 built and evaluated | Evaluation without user sessions §13; golden book §13.1 |
| §5 constraints: provenance, supersede not overwrite, never summarise summaries, sycophancy, injection | §5, §7.3, §8.2, §8.5, §9.2 |
| §6 "each item shows its sources, and the view shows what they are working toward learning next" | Chips §5.2; front page §10.4 |
| §6 "maintains itself … errors bounded, detectable and correctable" | §8.7–§8.9; corrections §9 |
| §3.1 other sources such as reading and work | Document sources in the sources register and chips; golden book includes a document §13.1 |

**Where this design could narrow the goal, and how it is handled:**
- "Remembers" may be met only modestly by reading: stated as H1 and Q4, not designed away.
- Background glosses are excluded to keep traceability: Q2.
- In-chat slices and re-encounter cards depend on unverified product channels: H14.
- Desktop chat traceability lags until verbatim capture: H8.

---

## Sources

### Research notes in this repository
- [01] `docs/research/01-human-memory-and-learning.md`; [02] `docs/research/02-pkm-practice-and-failure.md`; [07] `docs/research/07-human-vs-ai-consumers.md` (round 1; evidence only).
- [10] `docs/research/round2/10-integration-surfaces.md`; [12] `docs/research/round2/12-knowledge-structure.md`; [13] `docs/research/round2/13-robust-ai-maintenance.md`; SYNTHESIS = `docs/research/round2/SYNTHESIS.md`.

### Learning-science sources looked up for this design (checked 2026-10-08)
Where I could reach only an abstract or summary, the entry says so.
- Schneider, Beege, Nebel & Rey (2018), signalling meta-analysis, *Educational Research Review* 23, 1–24, DOI 10.1016/j.edurev.2017.11.001. Figures via secondary summaries: https://www.qic-wd.org/sites/default/files/Umbrella%20Summary%20-%20Signaling%20in%20Training%20111021.pdf ; https://ksvi.mff.cuni.cz/amulab/wp-content/uploads/2018/11/MultimLn3_BromHannemann_181117.pdf
- Alpizar, Adesope & Wong (2020), signalling meta-analysis (abstract via secondary): https://rex.libraries.wsu.edu/esploro/outputs/journalArticle/A-meta-analysis-of-signaling-principle-in/99900601052901842
- Richter, Scheiter & Eitel (2016), text–picture signalling meta-analysis, *Educational Research Review* 17 (via the summaries above).
- Lorch (1989), text-signalling devices review, *Educational Psychology Review* 1: https://link.springer.com/doi/10.1007/BF01320135 ; Lorch & Lorch (1996) and Loman & Mayer (1983), via Naumann et al. (2007): https://www.psychologie.uni-heidelberg.de/ae/allg/mitarb/uc/Naumann_Richter_Flender_Christmann_2007_Signaling.pdf
- Rey (2012), seductive details, *Educational Research Review* 7(3), 216–237 (secondary): https://en.wikipedia.org/wiki/Seductive_details ; Sundararajan & Adesope (2020), "Keep it Coherent", *Educational Psychology Review* 32(3), 707–734 (secondary): https://www.e-teaching.org/materialien/literatur/sundararajan-adesope-2020
- Rey, Beege, Nebel, Wirzberger, Schmitt & Schneider (2019), segmenting meta-analysis, *Educational Psychology Review* 31, 389–419 (abstract): https://is.tuebingen.mpg.de/publications/rey2018segmenting
- McNamara, Kintsch, Songer & Kintsch (1996), *Cognition and Instruction* 14(1), 1–43, DOI 10.1207/s1532690xci1401_1 (abstract and secondary): https://soletlab.asu.edu/cohesion-publications/
- Barbieri, Miller-Cotto, Clerjuste & Chawla (2023), worked examples meta-analysis, *Educational Psychology Review* 35, 11 (abstract): https://oaks.kent.edu/hcri/meta-analysis-worked-examples-effect-mathematics-performance
- Rawson, Thomas & Jacoby (2015), *Educational Psychology Review* 27, 483–504, DOI 10.1007/s10648-014-9273-3; replication d = 0.30 by Micallef & Newton: https://cronfa.swan.ac.uk/Record/cronfa59139
- Alfieri, Nokes-Malach & Schunn (2013), case comparisons meta-analysis, *Educational Psychologist* 48(2), 87–113: https://www.lrdc.pitt.edu/Schunn/papers/ContrastingCasesMeta-AlfieriEtAl2013.pdf
- Symons & Johnson (1997), self-reference meta-analysis, *Psychological Bulletin* 121(3), 371–394 (summary only): https://surface.syr.edu/psy_etd/101
- Liu, Wen, Liu & Hu (2023), self-referential encoding in education meta-analysis, *British Journal of Educational Psychology*, DOI 10.1111/bjep.12636 (abstract): https://ngdc.cncb.ac.cn/openlb/publication/OLB-PM-37722845
- Ginns, Martin & Marsh (2013), conversational style meta-analysis, *Educational Psychology Review* 25, 445–472 (abstract and summary): https://researchers.westernsydney.edu.au/en/publications/designing-instructional-text-in-a-conversational-style-a-meta-ana/
- Walkington and colleagues on context personalisation, as summarised in a 2026 preprint: https://arxiv.org/pdf/2602.15876
- Mayer, multimedia principle (median effects) and independent estimates incl. Lei et al. (2025): https://www.unh.edu/teaching-learning-resource-hub/sites/default/files/media/2023-06/itow-research-based-principles-for-designing-multimedia-instruction-mayer.pdf ; https://pure.ecnu.edu.cn/en/publications/effects-of-adding-illustrations-to-texts-on-students-science-achi/
- Schroeder & Kucera (2022), "Refutation Text Facilitates Learning", *Educational Psychology Review* 34(2), 957–987 (read directly): https://pmc.ncbi.nlm.nih.gov/articles/PMC8784251
- Rawson & Kintsch (2005), *Journal of Educational Psychology* 97(1), 70–80, and Greving & Richter (2019), via the latter (read directly): https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6333692/
- Mar, Li, Nguyen & Ta (2021), narrative vs expository meta-analysis, *Psychonomic Bulletin & Review* 28, 732–749 (read directly): https://pmc.ncbi.nlm.nih.gov/articles/PMC8219577/
- Rowland (2014), *Psychological Bulletin* 140(6), 1432–1463; Adesope, Trevisan & Sundararajan (2017), *Review of Educational Research* 87(3), 659–701 (abstracts and secondary): https://journals.sagepub.com/doi/10.3102/0034654316689306
- Luiten, Ames & Ackerson (1980), *AERJ* 17, 211–218; Stone (1983), *Journal of Experimental Education* 51, 194–199; Mahar (1992): https://www.ideals.illinois.edu/items/20405 (effect size via a secondary note on Hattie's *Visible Learning*)
- From memory, not re-checked today: Cepeda et al. (2006); Cowan (2001); Kalyuga et al. (2003); Dunlosky et al. (2013); Chi (2008); Chakrabarti, Kumar & Tomkins (2006); Kozminsky (1977). Each is also cited in [01], [02] or [12].

### Product documentation (checked on the date shown)
- Claude MCP Apps, getting started (Claude Desktop renders MCP Apps inline after Allow; local servers via config file), checked 2026-10-08: https://claude.com/docs/connectors/building/mcp-apps/getting-started
- MCP Apps SDK, `App` class (`openLink`, `sendMessage`, `updateModelContext` listed), checked 2026-10-08: https://apps.extensions.modelcontextprotocol.io/api/classes/app.App.html
- OpenAI Apps SDK, state management (`modelContent`, `ui/update-model-context`; no platform list), checked 2026-10-08: https://developers.openai.com/apps-sdk/build/state-management
- Via [10], checked 2026-10-07, not re-checked here: Claude connector limits https://claude.com/docs/connectors/building/index ; Claude Code hooks https://code.claude.com/docs/en/hooks ; ChatGPT plugins https://learn.chatgpt.com/docs/plugins ; Codex MCP https://learn.chatgpt.com/docs/extend/mcp ; Codex hooks https://learn.chatgpt.com/docs/hooks ; Willison TIL https://til.simonwillison.net/llms/mcp-in-claude-and-chatgpt
