# Northstar human architecture: the textbook

**Status:** final design for the human side, synthesised on 2026-10-08 from three independent attempts (A, B, C) and three judges' verdicts. It has been through adversarial review and goes to the user-approval gate (GOAL §7). It is not approved. Nothing is built from it yet. Revised on 2026-10-08 after a goal-fidelity audit; the changes are listed at the end, under "Fidelity fixes (2026-10-08)". Revised again the same day for consistency with the rest of the design set, under "Consistency fixes (2026-10-08)". Revised a third time the same day after the adversarial review ([`REVIEW.md`](../REVIEW.md)), under "Review fixes (2026-10-08)".

**Authority:** [`docs/GOAL.md`](../../GOAL.md) overrides this file. The user's answers of 2026-10-08 (GOAL §2) override the round-2 synthesis where they conflict. This design changes only the HOW. Where it sees a risk to the goal, it says so in §16 or asks in §15. It adopts no reframe.

**How this design was made.** The three judges each picked a different winner, through different lenses: goal fidelity (C), learning science (A) and maintainability (B). Attempt A has the highest mean score (7.8, against 7.2 for C and 6.7 for B), and it is the only attempt no judge ranked last. So **A is the base**: its evidence-derived anatomy and memory rules stay. **B supplies the compiler**: sentence kinds, deterministic structure, invariants, fallback and forward chapters. **C supplies the reader experience**: the four voices and the named narrator, the medium and its safety, chapter anchors, paragraph memoization and the no-ritual test. Every must-fix defect from the judges is resolved. §18 lists where each idea came from and how each defect was fixed.

**Evidence:** round-2 notes [10]–[14] and SYNTHESIS (round 2) are the main base. Round-1 notes [01], [02] and [07] are used for evidence only; their reframing is superseded. Learning-science sources were looked up by attempt A on 2026-10-08 and are listed in Sources. Invariants I1–I20 come from [13 §C]; I21 from SYNTHESIS §3.2.

**Conventions:**
- "(Unv)" marks an unverified product fact. Each one names the spike that settles it (§14).
- Product facts carry a source URL and the date checked, in the Sources table. Facts checked for this synthesis say "checked 2026-10-08". Facts inherited from another note say whose check it was.
- "(estimate)" marks this design's own numbers. They are starting values, calibrated once on the golden book and then frozen.
- No personal data appears here. Every example uses invented content.

---

## 0. The design on one page

1. **The human side is a book the AI writes and keeps current.** Units: Book › Part › Chapter › Page › Block › Sentence, with front matter, a "Where you're going" part, forward chapters and back matter. A page holds one idea.
2. **Every concept page has a fixed anatomy drawn from learning science** (§3, §4): key idea; where this fits (before the explanation); the explanation in short segments under headings that state the idea; the AI's own worked examples, verbatim; examples from your own work; how this changed; what is still open; what to learn next; who taught you this; sources.
3. **The AI explains, in cited prose, and says so.** The body is explanatory prose written by a model from leaf items only. Every sentence cites its leaves. The page header names the narrator: "Explained by Northstar from 11 sources".
4. **Only code writes attribution.** Model prose never names a speaker, never says "you", and never narrates the user's past. Code adds "Claude explained (Claude Code, 12 Sep):" before a verbatim quote, and the speaker chips in the margin.
5. **Five voices, always distinct:** you; you pasted; an AI agent (any agent, from a generic registry); an outside source; and Northstar, the narrator, which is never a source.
6. **Two clicks from any sentence to the verbatim span** in Northstar's own copy of the conversation. On the desktop chats, the book shows capture fidelity, speaker fidelity and how well the conversation is identified, and never claims more than it knows. Text the chat model reported never fills a "you said" slot until verbatim text confirms it (§5.8).
7. **AI-taught knowledge is first-class.** Ranking ignores the speaker. Promotion to a page ignores the speaker, and one substantive AI explanation is enough to earn a page. Verification chips are speaker-neutral. AI-said share is checked at the promotion decision and in every featured slot, nightly on real data, not just in what is reachable.
8. **What to learn is part of the book.** Goals, open questions, gaps, AI-suggested next steps and the frontier sit in Part 0, in forward chapters of stub pages, in each chapter's "Ahead" box and on each page. A goal-independent frontier keeps "what to learn" filled when the user has stated no goal. Nothing is a task, and nothing is counted.
9. **Structure is computed, not written.** Clustering is deterministic (fixed seed, warm start, a stability cost weighted by landmarks), anchored on goals and open questions where they exist. Structure changes only in weekly editions under a churn budget. Numbers are frozen between editions. IDs never change.
10. **Wording is stable.** A paragraph whose leaves did not change keeps its exact text, even across model or prompt changes. The one exception is a recorded, labelled quality release (§8.9).
11. **The maintainer can lose focus and the book stays correct.** Leaf-only inputs, 15 code validators, 100% entailment checks on new model sentences by a different model family, an extractive fallback, and an error budget that freezes model prose automatically.
12. **Corrections are optional, one click, and permanent** (I21). A new kind, "Northstar misstated this", is kept apart from "this source is wrong". On the desktop chats, a correction gains precedence only from a user click or a later match against the user's verbatim words.
13. **Medium:** a local web app (the Reader) now; the same app behind sign-in later. Small in-chat slices on Claude Desktop chat, Claude Code, ChatGPT Desktop chat and Codex, from one MCP tool contract (`connectors-desktop-and-mcp.md` §2). ChatGPT Desktop chat needs a relay only if spike CS2 fails (SPINE §7.3; connector design CR4). Every flow of data off the Mac is listed in §8.15, and whether "local now" allows cloud model calls is Q7 (asked as ARCH DQ-3(a)).
14. **No quiz, no mastery score, no required routine.** No retrieval aid is built (ARCH R16, GOAL §2). Nothing infers how well the user knows anything. Re-encounters come only from relevance in normal work, never from a schedule.
15. **Evaluation needs no user sessions** and never tests the user. An optional one-off acceptance read lets the user judge real pages, and no gate depends on it (§13.5). Truth, attribution and correction survival are hard gates. Simulated readers test understanding with inference questions. The re-ask rate is a passive proxy for remembering. A 30-day no-reads test proves nothing depends on the user.
16. **Cost:** about $28 a month at 100 turns a day, about $6 at 20 (estimate, ±2×), on prices checked today.

---

## 1. What this design must deliver

From GOAL §3.2:

> **It reads like a textbook.** The AI organizes the knowledge and explains it so the person **understands and remembers** it when they read. Every explanation stays traceable to its sources: who said it, and in which conversation. It is not a quiz or a mastery score.

From the user, 2026-10-08:

> "the key is to help human understand and remember their knowledge, just like textbooks."

| # | Requirement | GOAL anchor |
|---|---|---|
| H1 | Show **what has been learned**, from the user's own thinking and from what AIs taught | §3.2, §4.2 |
| H2 | Show **what to learn**: goals, gaps, open questions, next steps | §3.2, §2 |
| H3 | **Read like a textbook**: organised and explained so the person understands and remembers | §3.2, §2 (2026-10-08), §6 |
| H4 | Every explanation is **traceable** to who said it and in which conversation | §3.2, §6 |
| H5 | The AI builds and reorganises it. The user may browse and correct. **Nothing is required** | §3.2, §4.1, §4.3 |
| H6 | **Not a quiz, not a mastery score**; no estimate of how well the user knows anything | §3.2, §2 (2026-10-08) |
| H7 | A projection over the **shared core**, separate from the AI-facing representation | §4.4 |
| H8 | **Product-agnostic**, with the four first connectors; **local now, cloud later**; personal first | §4.6 |
| H9 | Stays correct when **any single agent loses focus** | §4.7 |

---

## 2. The reader's moments

The design starts from what a person does when they open the book. Each moment has a design section and a test (§13).

| # | Moment | What the reader gets | Design | Test |
|---|---|---|---|---|
| M1 | Opening the book after days away | Where they are heading, where to continue, what changed | §10.4 | T-NAV, T-NEW |
| M2 | "What have I learned about X, and from whom?" | An answer page: best page, who taught it, key points, conversations | §10.7 | SR-1, T-NAV |
| M3 | Reading a chapter to understand it | Pages in prerequisite order, each with organiser, explanation, examples | §4.4, §4.5 | §13 C, D |
| M4 | Checking a source | Two clicks from any sentence to the verbatim span | §5.5 | T-PROV |
| M5 | Telling AI-taught from self-stated at a glance | Voices in the margin rail; who-taught line per page | §5.2–§5.4 | T-ATTR, parity |
| M6 | Seeing what is new | "Since you last opened"; change bars on pages | §7.7 | T-NEW |
| M7 | Seeing what to learn next | Goal pages, forward chapters, "Ahead" boxes, reasons shown | §6 | §13 G |
| M8 | Fixing a mistake | One click on a sentence, chip or heading; undo | §9 | T-CORR |
| M9 | Glimpsing the book inside a chat | A card or slice that matches the book word for word | §10.8 | T-SLICE |
| M10 | "What did I get out of that chat?" | The sources register lists each conversation and what it fed, with capture fidelity | §5.8 | SR-2 |
| M11 | Seeing how my understanding changed | Refutation blocks, history, timeline, the book as of a date | §7.6, §7.8 | SR-3 |
| M12 | Never opening the book | Nothing breaks. The book stays current. The AI side still benefits | §8, §11 | T-RITUAL |

M12 matters as much as the others. GOAL §4.1 says the system delivers value without rituals. The book is a place to read, not a place that waits for the reader.

---

## 3. Evidence, and the design rules it produces

The question for this section is narrow: **what makes expository text understandable and memorable when a person reads it?** Each row gives a finding, its size, where it stops working, and the rule this design takes from it. Sizes use Cohen's d or Hedges' g: about 0.2 is small, 0.5 medium, 0.8 large. "(secondary)" marks a number attempt A saw only in a summary.

### 3.1 Findings and rules

| # | Finding | Size | Limits | Design rule |
|---|---|---|---|---|
| E1 | **Advance organisers** that link new material to what the reader has help learning (Luiten et al. 1980; Stone 1983) | d ≈ 0.21 (secondary) | Early results mixed; best for unfamiliar, structured material | **D1.** Every part, chapter and page opens with an organiser. On a page, "Where this fits" comes **before** the explanation |
| E2 | **Signalling:** headings and previews improve memory for what they cue (Lorch 1989; Schneider et al. 2018) | g = 0.53 retention, 0.33 transfer (secondary) | Helps cued content only; misleading headings bias understanding | **D2.** Headings state the idea. A heading counts as a sentence: it cites leaves and must be entailed by them |
| E3 | **Coherence:** interesting but irrelevant material hurts learning (Rey 2012; Sundararajan & Adesope 2020) | g = −0.33 (secondary) | Size varies across reviews | **D3.** Nothing decorative. Provenance lives in the margin rail. Provenance-heavy blocks fold by default |
| E4 | **Cohesion and expertise reversal:** novices need explicit links; support that helps novices can hurt experts (McNamara et al. 1996; Kalyuga et al. 2003, [01 F9]) | Crossover interaction | Replication mixed | **D4.** Prose is written for a learner: explicit connectives, linked prerequisites. A compact reference view is a **reader toggle** only. It never switches automatically, because that would infer familiarity (GOAL §2, 2026-10-08) |
| E5 | **Segmenting and chunking:** learner-paced pieces are learned better (Rey et al. 2019); working memory holds about four chunks (Cowan 2001, [01 F9]) | Small to medium | Mostly multimedia studies | **D5.** One idea per page. Segments sized to their leaves, with a target of about 120–220 words, at most five per page. At most seven items in any first-screen list |
| E6 | **Worked and concrete examples** help (Barbieri et al. 2023); concrete examples paired with abstract statements help transfer (Rawson et al. 2015); comparing cases helps most when the principle follows (Alfieri et al. 2013) | g = 0.48 worked examples; d = 0.50 case comparison | Examples must be tied to the idea | **D6.** Each segment pairs its statement with a concrete instance. The AI's own worked examples stay verbatim ("In their words"). "From your work" shows two or three cases, then one line saying what they share |
| E7 | **Self-reference:** material related to oneself is remembered better (Symons & Johnson 1997; Liu et al. 2023) | g = 0.40 [0.18, 0.62] | Negative material reverses it; shallow personal detail distracts | **D7.** Examples come from the user's own conversations and projects, shown by code as dated quotes. Neutral or successful episodes only. Nothing tagged sensitive or distressing. Scopes respected. Model prose has no second person (§5.3), so this design does not claim the conversational-style effect |
| E8 | **Elaboration and schema fit** aid integration; surprising material is kept distinct (Dunlosky et al. 2013; Tse et al. 2007, [01 F4, F8]) | "Moderate" (qualitative) | Schema fit also produces false memories [01 F4] | **D8.** Each page links what it builds on and says why the idea holds. Material that contradicts existing pages is flagged, never blended in |
| E9 | **Diagrams** help when relevant (Lei et al. 2025; studied concept maps g = 0.43 [12 F14]) | Small to medium in independent reviews | No evidence for global graph views [12 F15] | **D9.** A picture only for a relational idea: a local map of up to nine nodes, a comparison table, a sequence or a timeline, drawn by code from relations |
| E10 | **Refutation text** changes misconceptions better than plain exposition (Schroeder & Kucera 2022); old beliefs must be out-competed (KReC, [01 F5]) | g = 0.41 [0.30, 0.51] | Short passages; few tests beyond a month | **D10.** When understanding changes, a refutation block, rendered by code from records, shows the earlier view, why it seemed right (only if recorded), what changed it, and the current view |
| E11 | **Spacing helps; rereading is weak.** Spaced rereading effects are small and inconsistent (Rawson & Kintsch 2005; Greving & Richter 2019); retrieval practice is the strongest lever (Rowland 2014) | Retrieval g ≈ 0.50 | Retrieval practice is a test; GOAL §3.2 says not a quiz | **D11.** Re-encounters come only from relevance in normal work: a card when a later chat uses the idea. No schedule. **D11b.** No retrieval aid is built (ARCH R16, GOAL §2) |
| E12 | **A conversational AI retelling a person's past can implant false memories** (Chan et al. 2024, [01 F11]). Narrative helps memory in general (Mar et al. 2021), but this design **does not claim** that effect, because it tells no story | Over 3× false memories in Chan et al. | | **D12.** The user's past is quoted, never retold. "Who taught you this" is a dated list of quoted records. Its job is source and time cues (E13, E15) |
| E13 | **Sources reduce over-reliance** on wrong AI answers; explanations alone increase it (Kim et al., CHI 2025, [12 F8]). Human source memory decays [01 F11] | Pre-registered, N = 308 | Provenance is not truth [12 R1] | **D13.** Every sentence can show who said it and whether it was checked, as separate chips, at a density that does not crowd the prose (§5.4) |
| E14 | **Fluency inflates felt understanding** (Fisher et al. 2015; Melumad & Yun 2025, [01 F10, F13]) | Robust | Main human-side risk of polished text | **D14.** What is not known is shown as prominently as what is known. The book never claims anything about the reader's state, such as "you have learned X", "covered" or "mastered". The user's own query phrasing ("What have I learned about …") and GOAL's section term "what has been learned" are allowed |
| E15 | **People re-find by recognition, place and time** ([07 F10]; Dumais et al. 2003, [12 F15]); churn destroys location memory [12 F16][02 F2] | Field studies | | **D15.** Stable parts and chapters, permanent addresses, frozen numbering, a timeline, search |
| E16 | **Reading against a live question:** material sticks when a current question or project pulls it in ([02 F6]); experts organise by principle, not surface topic ([01 F9, Impl 9]); unresolved questions are the best gap signal [12 F12] | Mostly qualitative | | **D16.** Chapters are **anchored** on a goal or an open question where one exists, else on a central concept (§4.5, §7.2) |

### 3.2 Limits of this evidence

- **Most studies used students, unfamiliar topics, short sessions and immediate tests.** A personal book is read in short visits over months, about topics the reader partly knows. Effects may be smaller here.
- **Effects do not add up.** Signalling, segmenting and examples share mechanisms.
- **Several numbers are secondary.** No rule depends on an exact value.
- **Reading alone is a weak memory technique.** Rereading is rated low utility, and the strongest levers, retrieval and generation, need the reader to act [01 F8][02 F4]. The book can make knowledge clear, findable and well connected. Through reading alone, it can make it more memorable only modestly. This is RISK H1. Q4, which asked about system-side levers rather than the user doing more, is settled as that risk (ARCH R16).
- **A book the AI builds helps less than one the person builds** (concept maps g = 0.43 studied against 0.72 built [12 F14]; SYNTHESIS RISK 17). The user chose AI management (GOAL §4.3), so this design shifts no work to the user.

---

## 4. The book's anatomy

### 4.1 Units

| Unit | What it holds | Why it helps understanding and remembering |
|---|---|---|
| **Book** | Everything the core holds for one person in one scope. Personal scope first; work scopes later (§10.2) | One place to orient; its contents page is the top-level organiser (D1, D15) |
| **Front matter** | The first screen (§10.4) and the contents | An organiser for "now": where you are heading, where to continue, what changed |
| **Part 0: Where you're going** | Goal pages; goals as reported by a chat model, not yet confirmed (kept apart, §6.1); the open-questions register, with questions from the user and from AIs; AI-suggested next steps; possible directions (inferred, kept apart); **New this week**: "Just in" gists of concepts that have no page or chapter yet (at most 7 items, no counts, no inbox; §10.4) | Reading against a live question (D16); keeps what to learn beside what was learned; new material is readable before it has a place |
| **Subject parts** (at most 9) | Broad areas, derived by clustering and held stable (§7.2) | Few stable landmarks fit recognition memory and the chunk limit (D5, D15) |
| **Casebook part** | One chapter per project or recurring context (a repository, a reading project). Its pages are cases | Supplies self-referential examples (D6, D7); keeps project facts apart from transferable knowledge (Q3) |
| **Chapter** | 3–15 related pages. Anchored on a goal, a question or a central concept. Opens with an organiser; closes with a recap and an "Ahead" box (§4.5) | Organiser plus recap brackets the material (D1, D2) |
| **Forward chapter** | One per active goal, at the end of the goal's home part: stub pages for what the goal needs and the book does not yet explain (§6.5) | What to learn lives inside the book's structure, next to what it builds on |
| **Page** | One idea. Types: concept, question, goal, case, stub (§4.3) | Segmenting (D5); a stable unit to cite and return to (D15) |
| **Block** | A typed part of a page's anatomy (§4.4) | Predictable layout (D2); the unit of compile, caching and validation (§8) |
| **Sentence** | The smallest cited unit. Four kinds: Q, R, B, T (§5.3) | The unit of provenance: every sentence leads to a verbatim span |
| **Short note** | A concept below the page threshold (§4.7): one cited line with chips, listed at its chapter's end like a glossary entry. It **expands in place** to show every leaf it holds, as verbatim passages (or labelled gists) with speaker, chips and sources. It is the home block of those leaves (B5) | Keeps the book from filling with thin pages, the fragment pile-up of GOAL §1, without hiding what any source said |
| **Back matter** | Glossary, index, sources register, timeline, open and contested register, editions and changes | Entry points (D15); the sources register is the bibliography that makes claims traceable (D13); the timeline uses time as a cue (E15) |

**One home, many links.** A page has one home chapter, which gives its address. Other chapters list it as "Also in", never as duplicated text [12 decision 5].

### 4.2 Size rules

Starting values (estimate), checked by validator V10 and calibrated on the golden book (§13). **V10 treats these limits as targets:** a breach is a warning, never a reject.

| Rule | Starting value |
|---|---|
| Key idea | 1–2 sentences, at most 45 words |
| Model-written sentence | at most 30 words |
| Explanation | 1–5 segments, each sized to its leaves, with no word floor; target about 120–220 words per segment. A concept with one explanatory leaf gets one short segment |
| "In their words" boxes | 1–3 per page; each excerpt at most 150 words, trimmed at sentence boundaries by code. A trimmed worked example expands in place to the full verbatim example |
| "From your work" cases | 1–3 shown; more behind "more cases" |
| Pages per chapter | 3–15 (target median 6); outside the bounds triggers a split or merge at the next edition. While the Book is below the size minimums, the "growing book" form applies instead (§7.3) |
| Chapters per part | 3–12, or the "growing book" form while the Book is small (§7.3) |
| Subject parts | at most 9 |
| Items per first-screen block, "Ahead" box or "Next from here" | at most 7 (5 for "Ahead" and "Since you last opened") |

### 4.3 Page types

| Type | Lives in | Holds |
|---|---|---|
| **Concept page** | Subject parts | One idea, with the anatomy in §4.4 |
| **Question page** | Part 0 while open; the chapter of its main concept once answered | The question verbatim, who asked and when; what is known so far; each answer with its speaker; status (open, answered, dormant). An answered question keeps its page and gains "answered on [date] by [speaker] in [conversation]". A concept promoted only by a user question has a question page (or a stub) until an explanatory leaf exists (§4.7) |
| **Goal page** | Part 0 | The goal in the user's words, dated; why, in the user's words if they said; the path (§6.4); open questions on the path. A goal known only from a chat model's report has the same page under "Reported goals, not yet confirmed", with the gist and its label instead of a quote, and a provisional path (§6.1) |
| **Case page** | Casebook | One episode or run of episodes in a project: what the user was doing, what was decided (quoted), which concept pages it illustrates |
| **Stub page** | A forward chapter | Template sentences and quotes only: why it is needed, what conversations said about it, what it builds on (§6.5). It graduates in place when explained |

### 4.4 The concept page

The block order is fixed, so a reader always knows where to look (D2, D15). Four blocks are always present: the header with key idea, where this fits, the explanation, and the sources line. The others appear only when they have content. Provenance-heavy blocks fold by default to a one-line summary, so the explanation dominates the page (D3).

| # | Block | Contents | Written by | Rule |
|---|---|---|---|---|
| 0 | **Header** | Number, title, edition and printing; "Explained by Northstar from 11 sources: Claude 6 · ChatGPT 2 · you 2 · 1 document". These are counts of sources by speaker, not a measure of the reader | Code (T) | D13; names the narrator (§5.2) |
| 1 | **Key idea** | The gist in 1–2 cited sentences | Model (R) | D1, D2; gist outlasts verbatim memory [01 F1] |
| 2 | **Where this fits** | "Builds on" (prerequisite pages), "Leads to", "Serves your goal". Comes **before** the explanation. With no direction-checked prerequisite at confidence ≥ 0.7, it falls back to the page's chapter neighbours, labelled "Nearby in this chapter", never as "Builds on" | Code (T) | D1, D8 |
| 3 | **The explanation** | 1–5 segments, each sized to its leaves (no word floor; about 120–220 words is a target, §4.2), each under a heading that states the idea. Each segment ends, where one exists, with an "e.g." line: a short dated quote from the user's own work or from an AI's worked example, pulled by code from a span | Model (R, B) for headings and prose; code (T, Q) for the e.g. line | D2–D6 |
| 4 | **In their words** | 1–3 verbatim excerpts: an AI's worked example, analogy, procedure or code; or a source excerpt. Favours AI worked examples, because explanation and example are what AIs mostly teach [12 decision 2] | Code (T label, Q quote) | D6; code is never paraphrased (V8) |
| 5 | **From your work** | 1–3 cases from the user's episodes, each with context and a short quote, then one cited line saying what they share | Code (T, Q); model (R) for the one "share" line | D6, D7 |
| 6 | **Picture** (optional) | Local map, comparison table, sequence or timeline, drawn from relations | Code | D9 |
| 7 | **Your own words** | What the user stated or concluded about this idea, quoted and dated, with stance chips | Code (T, Q) | D12; H1 |
| 8 | **How this changed** | Refutation blocks (§7.6). Inline for the first three opens after a change or 30 days, then folded in place. A field says "your view" only when the earlier item is a stance the user held, shown as the user's dated quote | Code (T, Q) only | D10 |
| 9 | **Still open** | Open questions on this idea, asked by the user or raised by an AI, each attributed; disagreements with both sides attributed; unchecked claims the user relied on, whoever made them; terms used here but not yet explained in the book | Code (T, Q) | D14, D16 |
| 10 | **Next from here** | Frontier pages this idea leads to, each with its reason (§6.4): from a goal's frontier when the page is on a goal's path, else from the goal-independent frontier (§6.3). AI-suggested next steps linked to this idea, attributed | Code (T, Q) | D16 |
| 11 | **Who taught you this** (folded) | Dated records of how the user met the idea: each source with a 1–2 sentence verbatim excerpt, date, product, model and verification chip. Folded summary: "First explained by Claude (12 Sep) · your words (14 Sep) · ChatGPT (3 Oct) · 4 conversations" | Code (T, Q) | D12, D13 |
| 12 | **Sources and history** (folded) | The conversations cited, with capture fidelity and identity state (§5.8); printing, edition, corrections; history tab; "as of a date" | Code (T) | D13 |
| — | **Just in** (rail) | Leaf items promoted since the last printing, as cited gists with chips, until the nightly compile weaves them in | Code (T, leaf gists) | Freshness without waiting (§7.1) |

**One home per leaf.** Each leaf has exactly one home block on the page (invariant B5, §8.11). A quote shown in a refutation block is not repeated in "Your own words". Two exceptions keep thin pages readable: an explanation leaf may be cited by the explanation's prose and also quoted once, at ≤ 150 words, in "In their words"; and the key idea may cite a leaf homed in another block. Validator V15 (§8.5) stops blocks from restating each other beyond that.

**Mock page** (invented content):

```
4.2.3  Event sourcing                                   edition 7 · printed 8 Oct
Part 4 Software architecture › 4.2 Keeping history                [History] [⋯]
Explained by Northstar from 11 sources: ◆ Claude 6 · ◆ ChatGPT 2 · ● you 2 · ■ 1 document

KEY IDEA                                                                   sources
  Every change is stored as an immutable event, and the current           ◆ Claude
  state is rebuilt by replaying the events.                               ◆ ChatGPT ✓

WHERE THIS FITS
  Builds on   4.1.2 Append-only logs · 4.1.4 Idempotency
  Leads to    4.2.4 Projections and CQRS
  Serves      your goal "Design an event-sourced ledger" (7 Oct)

THE EXPLANATION
  Events are the record; tables are views                                 ◆ Claude
    An event-sourced system never edits a row in place. It appends a      ◆ ChatGPT ✓
    fact, such as "item 42 renamed", to a log, and every table that is
    queried is computed from that log. Because the log is complete, any
    view can be dropped and rebuilt.
    e.g. In habit-tracker (Claude Code, 3 Sep) you wrote:
         "replaying the events rebuilt the stats view"
  Replaying every event is slow, so systems add snapshots                 ◆ ChatGPT ✓
    ...cited sentences...
  Deleting data is the hard case                                          ◆ Claude ○
    ...cited sentences, one hedged...

IN THEIR WORDS
  ◆ Claude explained (Claude Desktop chat, 12 Sep, reconciled):
    "Think of the event log as a bank statement. The balance is just a
     number you can always recompute from it."

FROM YOUR WORK
  habit-tracker (Claude Code, 3 Sep) · reading notes (ChatGPT Desktop chat, 20 Sep)
  What these share: the current state was derived, so it could be rebuilt.  ◆ ●

HOW THIS CHANGED
  You said (14 Sep, Claude Desktop chat, reconciled):   "tables are just caches"
  Why it seemed right (recorded):           ◆ Claude, 12 Sep: "any view can be rebuilt from the log"
  What changed it (a newer source):         ◆ ChatGPT, 3 Oct, ✓ supported:
                                            "replaying every event on each read is too slow"
  You now say (5 Oct, Claude Code):         "the log is the truth, snapshots make it usable"

STILL OPEN
  ?  Deleting personal data from an append-only log
       a question as reported by ChatGPT (ChatGPT Desktop chat, 4 Oct);
       wording and speaker not yet confirmed
  ⇄  Snapshot interval: Claude (12 Sep) "every 100 events"; ChatGPT (3 Oct) "depends on load". Unresolved.
  ┄  "crypto-shredding" is used here but not yet explained in your book  → Ahead

NEXT FROM HERE
  → 4.2.4 Projections and CQRS. Builds on this page and 4.1.2, both already in your book.
  → Event upcasting. Not yet explained in your book. Suggested by Claude (12 Sep):
       "you may also want to look at how upcasting handles old event versions"

WHO TAUGHT YOU THIS  First Claude (12 Sep) · your words (14 Sep) · ChatGPT (3 Oct) · 4 conversations  [open]
SOURCES AND HISTORY  4 conversations (1 ChatGPT Desktop chat identified by session only) · corrections 0  [open]
```

Chips: "✓ supported", "± mixed", "○ unchecked", "~ opinion or advice", "⇄ contested", "✗ contradicted" (history only). Speaker classes: "● you", "◐ you pasted", "◆ <agent name>", "■ <source title>". On model-reported desktop-chat items, a speaker-fidelity chip "↺ speaker as reported by the chat model" sits beside the speaker (§5.8). Each chip is a glyph plus a word, never colour alone.

### 4.5 Chapter and part anatomy

**Chapter opener** (D1, D16):
- the title and the **anchor line**, chosen by code (§7.2):
  - goal anchor: "This chapter serves your goal: 'Design an event-sourced ledger' (7 Oct)";
  - question anchor: "This chapter answers your question: 'How do I keep history without losing performance?' (3 Oct)", or, for a question an AI raised, "This chapter answers a question Claude raised (12 Sep): '…'";
  - concept anchor: "Central idea: 4.2.3 Event sourcing", with its key idea transcluded;
- the **big picture**: at most 5 cited sentences, compiled from leaf items that code selects (those linked to two or more of the chapter's pages), never from page text (§8.3). A young chapter with too few such cross-linked leaves falls back to the chapter's top leaves by the speaker-neutral rank, still leaves only;
- **In this chapter**: each page with its key idea, transcluded word for word with its citations;
- **Builds on**: the chapters it depends on;
- **Your goals here**: goals whose paths pass through this chapter, in the user's words;
- **Welcome back** (only when the reader returns after a gap): "Last time you opened this chapter: 14 Aug. Since then: your view on snapshots changed; 1 new disagreement; 2 pages have new material." Built by code from the change log.

**Chapter close:**
- **Recap**: the key ideas again, in reading order (bracketing, D2);
- **Short notes**: concepts below the page threshold, one cited line each;
- **Open questions** and **where sources disagree** in this chapter;
- **Ahead**: up to 5 frontier items that build on this chapter, with reasons (§6.4). They come from a goal's frontier when the chapter is on a goal's path, else from the goal-independent frontier (§6.3), so the box is filled even when the user has stated no goal. AI-suggested next steps linked to the chapter compete on the same score.

**Reading order** inside a chapter is a topological order over direction-checked prerequisites. Ties break by the date the user first met each concept, then by ID. Previous and next follow it.

**Part opener:** title; a **part big picture** of at most 5 cited sentences; its chapters with one line each; its goals. The big picture is compiled the same way as a chapter's: from leaf items that code selects (those linked to pages in two or more of the part's chapters), never from chapter or page text, so it is not a summary of summaries [12 F4]. With too few such leaves, it uses the same fallback as a chapter: the part's top leaves. It passes the same validators, 100% entailment and the L4 audit (§8.5, §8.6). Everything else in the opener is code.

### 4.6 The reference view

Expertise reversal (E4) means one density cannot suit both a new idea and a well-worn one. But choosing density from the user's engagement would be a hidden estimate of how well they know it, which the user rejected on 2026-10-08. So:

- **The default is the learning view** for every page: full prose, explicit connectives, prerequisite terms linked inline.
- **The reference view is a reader toggle**, per page or for the whole book. It shows the key idea, each segment's heading with the segment folded under it, one example and the sources. It is a view of the same compiled text, so nothing is compiled twice.
- **Nothing switches automatically.** The toggle is per-reader view state. It never enters the core or AI packs, and it is not a correction.
- The novice-reader arm in §13 D tests whether the default serves readers with less background, and BK7 ablates the toggle.

### 4.7 What earns a page

Promoting one-off items bloats the book [02 F10] and turns one-off events into general knowledge (Go-CLS, [01 F3]).

- **A concept gets a page** when any of these holds:
  - it appears in at least two independent episodes (a lineage group of echoes counts once, I11; Northstar echoes never count, §5.9);
  - it has **substantive teaching** from any speaker. The **substantive-teaching flag** is set when any of these holds (starting values, estimate, calibrated on the golden book): (a) an explanation or definition leaf of 120+ words; (b) any worked example or procedure; (c) on model-reported capture, two or more applied `explanation` items from one reply that share a `primary_concept`, or a reported explanation `body` of 120+ words. It is computed in code in C08 `concept_facts` and is speaker-free. This is how an AI usually teaches: one deep explanation in one chat;
  - it was the subject of a user question, open or answered. A concept promoted only by a user question has a question page (or a stub) until an explanatory leaf exists. A **project-bound** question (about how one repository or project is set up) goes to that project's Casebook chapter instead; the rule that decides "project-bound" is calibrated on the golden book's developer persona (§13.1);
  - it is a goal target; or the user pins it.
- A one-off **event** (a mention, a passing fact) still stays a short note, so one-off events do not become general knowledge (Go-CLS, [01 F3]). A one-off **explanation** is teaching, and earns a page.
- **Hysteresis applies only to the two-episode rule:** such a concept is promoted after it meets the rule in two consecutive nightly runs. Substantive teaching, a user question, a goal target or a pin promotes on the first night. A page is demoted only at an edition, and only if it has no active or historical leaves left.
- **Otherwise it is a short note**, in its chapter's short-notes list, the index and search. The short note is the home of its leaves and expands in place to show each one verbatim (or as a labelled gist) with its sources (§4.1, B5).
- **The speaker does not count, by construction.** The promotion function receives lineage counts, the substantive-teaching flag (computed in code from leaf kind, span or body size and reply grouping only), goal and question links and pins. Its input type has no speaker field, so it cannot use one. An idea an AI taught in two conversations, or once in depth, earns a page exactly as one the user raised twice does.
- **Monitored at the decision.** The share of promoted concepts whose support is mainly AI-said is compared with the same share among eligible concepts and in the golden book (promotion parity, §13 B). The check is also run on **single-episode concepts alone**, so a rule that quietly drops one-chat AI explanations shows up. A gap above 5 points is an alert [12 R4]. On the golden book, single-episode explanations captured from a desktop chat are also compared with the same explanations captured at hook tier (§13.2 B).
- The size bar adds pages. Book bloat stays bounded by the size rules and dormant folding (H12), and the bar is calibrated on the golden book's page count.

### 4.8 Why this anatomy helps understanding and remembering

| Feature | Helps by | Evidence |
|---|---|---|
| Key idea first, verbatim one click away | A gist to reason with; verbatim for re-interpretation | [01 F1], D1 |
| "Where this fits" before the explanation | Links new material to what the reader already has | E1, E8 |
| Headings that state the idea | Cue structure; checked against sources so they cannot mislead | E2 |
| Short segments, one idea per page | Fits the chunk limit | E5 |
| "e.g." lines, "In their words", "From your work" | Concrete instances, worked examples, self-reference, case comparison | E6, E7 |
| Refutation blocks | Co-activate old and new belief so the old one stops resurfacing | E10, [01 F5] |
| Disagreements kept as disagreements | Avoids wrong hybrids | [01 F6] |
| Who, product, conversation and date on every source | Time and people are strong cues; source memory decays without them | E13, E15, [01 F11] |
| Stable places, frozen numbers, permanent addresses | Recognition and location memory | E15 |
| Chapters anchored on goals and questions | Material pulled in by a live question sticks | E16 |
| Links between related pages | Integration links reduce retrieval-induced forgetting | [01 F7] |
| In-chat cards when a later chat uses the idea | Re-encounter during real work, with no schedule | D11, [02 idea 15] |
| What is not known shown as prominently as what is | Counters fluency illusions | E14 |

**The honest limit.** These features make knowledge clear, findable and connected. They help remembering only modestly, because reading is a weak memory technique and the reader did not build the structure (§3.2). The design says so to the user (H1; Q4, settled by ARCH R16) and measures remembering only through labelled proxies (§13 E).

---

## 5. What has been learned: attribution down to the verbatim span

### 5.1 What counts as learned content

"What has been learned" is the content itself (SYNTHESIS Table B, §3.2): what the user stated or concluded, and what AIs explained or taught, plus later sources such as documents. In core terms these are Statements and Passages, each with its attribution [12 decisions 1–2]. It is never an estimate of mastery (GOAL §2, 2026-10-08).

### 5.2 Five voices

The reader can always tell these apart.

| Voice | Who | Where it appears | Rule |
|---|---|---|---|
| **● You** | The user's typed words (`user_typed`) | "Your own words", e.g. lines, "From your work", refutation blocks, rail chips | Any statement about what the user believed, decided or concluded is a dated quote of a user-typed leaf (V4, §5.7). Only items whose speaker is set by construction or reconciled fill these slots. Items the chat model reported as the user's words appear only as labelled gists (§5.8) |
| **◐ You pasted** | Text the user pasted from elsewhere (`user_pasted`), from paste detection [12 R8] | Rail chips and labels: "You pasted (from an earlier ChatGPT reply)" | Never shown as the user's own thinking; where the paste's origin is known, it is attributed to that origin |
| **◆ An AI agent** | `assistant(agent_id)` from the **agent registry** | Rail chips, "In their words", "Who taught you this" | Shown as AI-said, with its display name, model and product. Same weight as the user's items (§5.6) |
| **■ A source** | An external document or web page (`external_source`) | Rail chips, "In their words" | Shown with its title and locator |
| **Northstar** (narrator) | The compiler's own wording | Model prose: key ideas, explanation segments, "share" lines, chapter big pictures | Never a source. Adds nothing beyond its cited leaves. Named in every page header: "Explained by Northstar from N sources" |

**The agent registry is generic and extensible.** Each agent is a row: `{agent_id, display_name, vendor, product, surface, model}`. A connector registers new agents when it first sees them. The book renders the class glyph (◆) plus the display name from the registry, so a new agent or LLM appears correctly with no change to the book. Nothing in the book hard-codes a vendor.

**Why the narrator is named.** Northstar is also an AI. Hiding that would blur exactly the line GOAL §3.2 asks the book to keep: who said what. Naming it also counters the fluency illusion (E14).

### 5.3 Four kinds of sentence, and why the model cannot misattribute

Misattribution is the dominant failure of shipped memory: 43–55% of AI-introduced distractors were stored as user facts [12 F8]. So attribution is never left to a model.

**What this section guarantees, and what it does not.** No sentence Northstar writes can misattribute, because only code writes attribution. But code can only copy the speaker the capture channel gives it. On Claude Code and Codex, hooks give the speaker by construction (I3). On the desktop chats' sanctioned layer, the chat model decides which text it reports as the user's words and which as its own reply, so the speaker of a model-reported item is set by a model, the failure SYNTHESIS AD6 warns about [12 F8]. Those items carry a speaker-fidelity chip and stay out of every user-voice slot until reconciled (§5.4, §5.8). This gap is part of RISK H8.

| Kind | Written by | Rule | Shown as |
|---|---|---|---|
| **Q, quote** | Code | An exact substring of a span with fidelity `verbatim` or `reconciled` (I2). The model may only choose a span ID; code pulls the text | Quotation styling, with a T label naming the speaker |
| **R, restated** | Model | Cites at least one leaf. Entailment-checked | Body prose under the narrator; markers in the rail say "sources", not "said" |
| **B, bridge** | Model | Cites at least two leaves and one relation item. Entailment-checked against the leaves together | Same as R |
| **T, template** | Code | Filled from core records only: attributions, structure, changes, stubs, refutation fields | Plain text, often with links |

- **Attribution lives only in T sentences and chips.** The model never writes "Claude said", "you concluded" or "as you realised".
- **Validator V4 enforces it** (§8.5). R and B sentences may not contain any first- or second-person pronoun ("I", "we", "you", "your") or any reference to the user's past. They may not use any registry agent, product or model name, or a generic agent noun (assistant, model, AI, user, author), as the subject of a speech or stance verb, or in an attribution pattern, whoever is cited. Names may appear as subject matter only when they occur in a cited leaf's text (V6), such as a sentence about what a product does, citing a leaf that says so. So "as the assistant suggested" fails, and so does "ChatGPT recommends X" in a sentence that cites a Claude leaf.
- **Restated wording is labelled as Northstar's.** Narrator prose carries a thin left rule and a hover label "Northstar's wording, based on: …". A rail chip beside it reads as "source", so "◆ Claude" next to a restated sentence means "based on what Claude said", never "Claude's words". Only Q sentences, in quotation styling with a T label, are anyone's own words.

### 5.4 What every sentence can show, and at what density

Chips render the core's independent attribution axes (SYNTHESIS §3.1, AD6). Code builds them.

| Chip | Values | Source record |
|---|---|---|
| Speaker | ● you · ◐ you pasted · ◆ agent (from the registry) · ■ source | Attribution.speaker, set by the adapter (I3) from the capture channel's role field |
| Speaker fidelity | by construction (no chip) · ↺ speaker as reported by the chat model · reconciled | Attribution.speaker_fidelity (**new**, §12.1). "As reported" applies to every model-reported item on the desktop chats' sanctioned layer |
| Product, model, date | e.g. "Claude Code · claude-opus-5-5 · 12 Sep" | Message, Episode |
| Your stance | asserted · accepted · questioned · disputed · rejected · none | Stance (I4) |
| Verification | ✓ supported · ± mixed · ○ unchecked · ~ opinion or advice · ✗ contradicted · ○ cites a source, unchecked. The same values and display apply to every speaker | Verification, with verifier and evidence on hover |
| Capture fidelity | verbatim · model-reported · reconciled | Attribution.capture_fidelity |
| Conversation identity | identified · session only · not identified (§5.8) | Episode.identity_state |
| Certainty | tentative, when the source hedged (I10) | Item.certainty |

**Density rule** (D3, D13):
- **One place, not two.** Speaker glyphs appear in the margin rail only, one per cited speaker per sentence group. There are no inline markers repeating the rail.
- **Chips appear only when unusual:** an unchecked checkable claim about the world, **whoever said it**; a contested item; model-reported capture or speaker; a conversation not yet identified; or a correction. Otherwise the rail shows only the speaker. The same claim gets the same chip from the user as from an AI.
- **A shared state is shown once per block.** When most sentences in a block share a fidelity state, the block shows it once as a **block note**, for example "Based on the chat models' own accounts in Claude Desktop chat; original wording not yet captured". Sentence chips then mark only the exceptions. Each sentence keeps its speaker glyph and its drawer, so nothing is less traceable.
- **"Show all chips"** is a reader setting. Attribution can be quieter, never absent.
- Chip density is tested in the comprehension A/B (§13 D, arm BK6).

Verification and stance are always separate chips. "You accepted it" never reads as "it is correct" [12 F8].

### 5.5 From any sentence to the verbatim source, in two clicks

| Step | The reader clicks | They see |
|---|---|---|
| 1 | A sentence or its rail glyph | The **source drawer** opens beside the text: each cited item with speaker, product, model, conversation, date, capture fidelity, identity state, stance and verification |
| 2 | An item | The anchored quote highlighted inside the stored conversation, with the turns around it, the branch if any, and the verification record (verifier, evidence, date) |
| 3 (optional) | "Open full conversation" or "Open in product" | Northstar's own transcript view at that message; or the vendor's conversation where a stable deep link exists (Unv per product, spike S-R5) |

```
+- Sources for this sentence ---------------------------------------------+
| "Because it is derived, it can be dropped and rebuilt at any time."     |
|  Northstar's wording, based on 2 items                                  |
| 1  Passage · ◆ Claude (claude-opus-5-5) · Claude Code                   |
|    "Northstar core design" · 12 Sep 14:03 · verbatim · ~ opinion        |
|    ● You: "so can I just delete it?"                                    |
|    ◆ Claude: "Yes. [A projection is disposable; rebuild it from the     |
|    log] whenever the schema changes."                                   |
|    [Open full conversation]  [Open in Claude Code]                      |
| 2  Statement · ◆ ChatGPT · ChatGPT Desktop chat · 3 Oct                 |
|    model-reported (original wording not yet captured) · ↺ speaker as    |
|    reported by the chat model · session only                            |
|    ○ unchecked                                                          |
| [Northstar misstated this]  [This source is wrong]  [Wrong speaker]     |
| [Wrong conversation]                                                    |
+-------------------------------------------------------------------------+
```

The drawer reads Northstar's immutable source store, so it works offline and does not depend on the vendor keeping the chat. Excised content shows a tombstone (SYNTHESIS §5 item 9). Document and web-page sources use the same drawer with a page or character range (source-generic anchors, SYNTHESIS §3.1).

### 5.6 AI-taught knowledge is first-class

GOAL §4.2 requires it. These rules make it hold in the book, not just in the store:

1. **Equal terms in the explanation.** Leaves compete for a page's prose on the speaker-neutral rank of SYNTHESIS §3.1 step 3: verification, independent lineages (an AI echo counts once, I11), grounding, then recency. Speaker is not a factor for claims about the world.
2. **Promotion ignores the speaker** (§4.7).
3. **AI worked examples get a verbatim home** in "In their words" (§4.4).
4. **Everything reachable.** Every AI passage linked to a concept is cited, quoted or listed under "More" on that concept's page, or, if the concept has a short note, shown in the note's expanded view (invariant B5). Passages with no concept link stay reachable under their conversation in the sources register and in search.
5. **Labelled, not hidden, and labelled the same way for every speaker.** An unchecked claim about the world stays in the body with its chip, whoever made it. Advice and opinion sit under a T label for every speaker: "Claude's advice (opinion, 12 Sep):" and "Your advice (opinion, 5 Oct):" alike. A contradicted claim, from any speaker, moves to "How this changed" with its reason. Nothing is silently dropped (I9).
6. **"What did ChatGPT tell me about X?" is a first-class query** (§10.7).
7. **Parity is measured where demotion would happen: in featured slots**, not in reachability (which B5 already guarantees). Featured slots are: citations in key ideas, citations in explanation prose, "In their words" boxes, chapter and part big pictures, first-screen items, what-to-learn items and in-chat slices. Two references are used:
   - **Live reference, on real data, nightly.** For each block, the AI-said share among the eligible active leaves assigned to it, weighted by the speaker-neutral rank. The featured share is compared with this reference across all blocks of a slot type. A gap above 5 points trips the parity sentinel (B11, §8.12). This catches a demotion of AI-said content after deployment, or after a model or prompt change, with no golden data.
   - **Golden reference, at evaluation.** The golden-set share for the same pages (§13 B).
8. **AI-said knowledge feeds what to learn too.** Questions an AI raised and left open, and next steps an AI suggested, are attributed what-to-learn items (§6.1). They never become goals (I5).

### 5.7 The user's past is quoted, not retold

A conversational AI that narrates someone's past can implant confident false memories (Chan et al. 2024, [01 F11]). Inferred rationale matched the real one with a precision of only about 0.27 (SYNTHESIS §5 item 1).

- **Rule:** any statement about what the user believed, decided, said or did is a T label plus a Q quote of the user's own words, with date and source. Model prose may write about the world. It may not write about the user.
- **V4 enforces it** (no second person, no references to the user's past in R or B sentences; the detector is defined in §8.5). Template sentences that mention the user ("you asked", "you wrote") must carry a quote and a date.
- **"Why the earlier view seemed right"** appears only when the core recorded a causal-alternative leaf for that supersession. It is shown as that leaf's quote or its verified gist, never written fresh (§7.6).

### 5.8 Desktop chats: capture fidelity, speaker, goals and "in which conversation"

The 2026-10-08 answers make Claude Desktop chat and ChatGPT Desktop chat first connectors. On both, the sanctioned live channel is MCP: the model's own report of what was said, and no verbatim AI text (SYNTHESIS Table A, RISK 4). For Claude, plugin hooks are "Ignored" in Chat (https://claude.com/docs/plugins/platform-support, checked 2026-10-08 by connector-claude-desktop-chat.md, V1). For ChatGPT, hooks are documented for "local-only Work and Codex threads" and Chat mode is not mentioned (https://learn.chatgpt.com/docs/extend/mcp.md and https://learn.chatgpt.com/docs/hooks, checked 2026-10-08 by connector-chatgpt-desktop-chat.md, V6 and V7), so the absence of a hook in Chat mode is (Unv), spike CS3 in that design. "No verbatim AI text" follows from these: no documented sanctioned channel delivers it. Solving capture belongs to the connector designs and the optional macOS observer. The book's duty is to be exact about what it knows, and to keep what to learn working on these surfaces.

**Capture fidelity.**
- Quote styling (Q sentences, "In their words", e.g. lines, refutation quotes, the drawer's highlight) uses only `verbatim` or `reconciled` spans.
- A `model-reported` item renders as a cited gist with the label "the assistant's own account during the chat, not its original wording". It can still be cited by R sentences, with its chip shown.
- A **reported explanation body** (at most 1,500 characters, [CX] §2.3) renders the same way: a labelled gist, never a quote. A body of 120+ words sets the substantive-teaching flag (§4.7 (c)).
- **A chat's last reply.** At L0, the points of a reply reach Northstar only on a later tool call in the same chat, and the last reply has no later call. The **closing report call** ([CX] §2.3 `this_reply_points`, made at the end of an explaining reply) is the only way a chat's last reply is captured at L0. It works only where its spike passes, and where the per-turn tool is read-only it records only through a declared write ([CX] §4.4 step 6). Without it, what the last reply taught is lost until verbatim text arrives (observer capture or export backfill). This is part of H8.
- When verbatim text arrives (observer capture, export backfill, or reconciliation), the item keeps its ID, its chip changes to `reconciled`, and the next printing may quote it. If the reconciler finds no match, the chip says "could not confirm wording".

**Speaker fidelity.** On the sanctioned layer, the chat model also decides which text is the user's and which is its own (§5.3). So:
- Every model-reported item carries the chip "↺ speaker as reported by the chat model" beside its speaker, until reconciled.
- A model-reported item never fills a **user-voice slot**: "Your own words", the "You said" and "You now say" fields of refutation blocks, "From your work" quotes, e.g. lines, or "In your words" on answer pages. It never fills "In their words" either. In those places it appears, if at all, as a labelled gist: "The chat model's account of your message (ChatGPT Desktop chat, 3 Oct), not your original wording: …" or "The assistant's own account during the chat, not its original wording: …".
- A model-reported user item never counts as a stance the user held, for "Since you last opened" item 1 (§7.7) or for "your view" wording (§7.6), until reconciled.
- When reconciliation finds the text under the other speaker, code moves the item to that speaker with a typed event, and the chip says "speaker corrected on reconciliation".

**Goals stated in a desktop chat.** Both desktop connector designs keep model-reported user text out of long-term goals until verbatim text confirms it (connector-claude-desktop-chat.md §0 and §4.2.5, step 3 "Fidelity gate"; connector-chatgpt-desktop-chat.md §6.2.6, "Session Steward"; I5). Without a fix, a goal stated only in a desktop chat would never reach Part 0, the frontier or the first screen. The book handles it with no ritual:
- A goal statement known only from the chat model's report becomes a **reported goal**. It appears in Part 0 and on the first screen under "Reported goals, not yet confirmed", kept apart from confirmed goals in the same way possible directions are. It shows the gist with the label "goal as reported by the chat model, not yet confirmed".
- A reported goal may anchor a **provisional frontier**, labelled as such (§6.3). It does not anchor chapters, so a later rejection causes no structural churn.
- It is confirmed **automatically** when verbatim text matches (observer capture, export join, reconciliation).
- It can also be confirmed by an **optional** click, "Yes, that's my goal", on the confirm card in the chat (`northstar_widget_action(action: confirm_goal)`, origin `app_click`, where cards render, S-R1 and S-R2) or in the Reader (`reader_click`). Nothing asks for the click, nothing counts unconfirmed goals, and nothing waits on it. A confirming click counts only from the widget or the Reader, and never on the turn the goal was reported. The card says that Northstar did not see the user type the goal.
- A reported goal never enters AI packs as a goal, constraint or instruction until a verbatim match confirms it (I5). Whether a user click may also confirm it for AI packs, given I5's rule that only typed text creates goals, is put to the user as Q6 (asked as ARCH DQ-10, expanded). Until then a click confirms it in the book only (Q6, working assumption). With a yes, a click-confirmed goal line reads "confirmed by your click; wording as reported by the chat model".
- "Not my goal" removes it, as for any goal (§9.1).

**Conversation identity.** Each episode carries an identity state, and every item shows it.

| State | When | What the book shows |
|---|---|---|
| **identified** | The vendor's conversation identity is known: hook surfaces (Claude Code and Codex hooks carry the session's transcript path, [10] F5, F9), the observer's chat identity, or an export join | Product, conversation title, date and time; "Open in product" where a link exists |
| **session only** | A stable per-conversation key is known but not joined to the vendor's chat. **ChatGPT** sends `_meta["openai/session"]`, "Anonymized conversation id for correlating tool calls within the same ChatGPT session", with tool calls (Apps SDK reference, checked 2026-10-08; whether Desktop Chat mode sends it is Unv, spike S-R7). **Claude** passes no conversation ID: "Neither `hostContext` nor the tool-call arguments include a Claude-provided conversation ID" (checked 2026-10-08), so the connector mints a session handle in the chat's first `northstar_context` result (connector-claude-desktop-chat.md §0; `connectors-desktop-and-mcp.md` §2.3) | "Claude Desktop chat · 3 Oct, 14:02–14:40 · Northstar session NS-4K2 · the app's chat title is not yet known". All items from that conversation are grouped together |
| **not identified** | Neither key is available | Grouped by product and time window, labelled "conversation not identified". A sentinel tracks the share; the bar is below 1% of items |

- **Upgrade in place.** A join is a typed, reversible event (`episode_joined`), made by code when content hashes align with observer or export text. The chip changes; nothing else moves.
- **Never claim more.** No item shows a conversation title or link it has not been joined to. Two sessions are never merged in the book without a join event. A wrong join is corrected with "Wrong conversation" (§9.1).
- **Per-conversation capture panel.** In the sources register, each conversation shows its identity state and the share of its turns captured verbatim, model-reported and reconciled. A desktop chat with only model-reported capture says so.

### 5.9 No self-citation loop

A slice shown in a chat can be repeated by the chat model and then captured as AI-said content. Without a guard, the book would confirm itself (SYNTHESIS RISK 11).

- The core keeps **context receipts**: which slices and pack items were delivered to which session, with text hashes.
- J5 tags an AI-said span with lineage `northstar_echo` when it follows a delivery and its overlap with the delivered text passes a threshold (n-gram containment, starting value 0.6; precision measured in spike S-R9). The delivery may be:
  - in the **same session**; or
  - in an **earlier session of the same `speaker_model_family` within 90 days**, when the span has no fresh grounding (such as a tool result or a cited source). Vendor memory can carry delivered text into later chats, where it would otherwise return as independent AI-said support (`ai-continuity.md` §9, D4; SYNTHESIS RISK 11).
- An echo stays visible as AI-said content. It **never** counts as an independent lineage, never raises verification, and never counts toward page promotion (invariant B15).
- The share of AI-said spans discounted as echoes is **reported by vendor family**, in §13.2 B and by the vendor-parity sentinel (SPINE SD-38). If one vendor's AI-said knowledge is discounted more than another's, that shows; it is never silent.

---

## 6. What to learn

### 6.1 The components

Built from [12] Model C and SYNTHESIS §3.2.

| Component | Source | How it is shown |
|---|---|---|
| **Goals** | The user's explicit statements of intent, verbatim and dated (Agenda items from user spans only, I5) | Goal pages in Part 0; "Where you're heading" on the first screen. **Possible directions** (inferred interests) are kept apart, labelled "inferred", and fade after 60 days without new evidence, because models over-infer user attributes [07 F7] |
| **Reported goals** | Goal statements known only from a chat model's report of the user's message, on the desktop chats' sanctioned layer (§5.8) | Part 0 and the first screen under "Reported goals, not yet confirmed", kept apart from goals like possible directions; a provisional frontier, labelled. Confirmed automatically by a verbatim match, or by an optional click (§5.8, Q6) |
| **Open questions** | Questions the user asked that no later item answers; **questions an AI raised and left open** ("one thing still to decide is whether …"), attributed to that agent; questions spawned from contested Tensions (SYNTHESIS §3.1 step 5) [12 F12] | The open-questions register in Part 0; each page's "Still open"; each chapter's close. An AI-raised question renders by code as a T label plus a Q quote: "Raised by Claude (12 Sep): '…'" |
| **AI-suggested next steps** | Next steps an AI recommended in a conversation ("you may want to learn X next"), as Agenda items with speaker `assistant(agent_id)` and their span. J3 tags a **`learning_suggestion`**, which must link a concept, apart from an **`offer`**, an offer to do work ("I can write the tests next"). An offer is never a what-to-learn item and never on the frontier | In next steps with reason code `suggested`, by code as a T label plus a Q quote: "Suggested by Claude (12 Sep): '…'". On the desktop chats, the labelled gist until reconciled (§5.8). **An AI suggestion never becomes a goal, a constraint or an instruction** (I5) |
| **Gaps** | (a) **dangling terms**: used in an explanation but never explained in the book; (b) **prerequisite gaps** on a goal's path; (c) **unchecked reliance**: an unchecked claim, from any speaker, that the user then used; (d) **disagreements** left contested | Inline where the term appears; on goal pages, stubs, chapter closes and "Still open" |
| **Frontier** | The outer fringe of the prerequisite structure [12 F11] (§6.3): over a goal's subgraph where a goal applies; over the whole concept graph otherwise (the **goal-independent frontier**); over each possible direction, labelled "inferred"; and over each reported goal, labelled "provisional" | "Next" on the first screen and goal pages (at most 7); "Ahead" boxes; "Next from here" |
| **Next steps** | A ranked view over frontier items, AI-suggested next steps, gaps and open questions (§6.4) | Same places, each with its reason |

### 6.2 Where it lives in the book

| Place | Shows | Size |
|---|---|---|
| First screen, "Where you're heading" | Each goal with its next 2–3 items; reported goals, apart and labelled; the newest open question. With no explicit goal, the goal-independent frontier instead (§10.4) | At most 7 lines |
| **Goal page** (Part 0) | The goal verbatim; the **path**: an ordered list of the pages and stubs it needs, each marked "already in your book" (with "explained to you on [date]") or "not yet explained"; next steps with reasons; open questions on the path | Collapsible; no counts |
| **Forward chapter** "Ahead: [goal]" at the end of the goal's home part (or Part 0 if it has none) | Stub pages for the goal's concepts the book does not yet explain, in prerequisite order | All |
| Chapter close, **"Ahead" box** | Frontier items that build on this chapter; its open questions | Up to 5 |
| Page, **"Still open"** and **"Next from here"** | Open questions, disagreements, unchecked reliance, dangling terms; frontier items this page leads to | All for that page |
| **Inline dangling terms** | A term used in prose that the book does not explain carries a dotted underline and a hover: "Not yet explained in your book", linking to its stub or gap | First occurrence per page only |
| Open-questions register | All open questions by part; answered ones with links to their answers | All |

**Links run both ways.** Every stub and frontier item lists the pages it builds on. Every page lists the frontier items that build on it. A reader can move from what they know to what is next, and back, at any point.

### 6.3 Defined in code, without a mastery score

The frontier needs a notion of "already explained". This design uses exposure, which the system can observe honestly [12 F10]:

- `explained(c)`: concept c has at least one active explanation or definition leaf, from any speaker, from the user's own conversations or sources, whose verification is not `contradicted`.
- `G(g)`: the target concepts of goal g plus their prerequisite ancestors.
- `frontier(g)`: concepts in G(g) that are not explained and whose prerequisites in G(g) are all explained.
- `later(g)`: concepts in G(g) that are not explained and have an unexplained prerequisite.

**The goal-independent frontier.** Many chats state no explicit goal. "What to learn" must not shrink to open questions in that case (GOAL §3.2; §2, 2026-10-07 "Both"). So code also computes:
- `mentioned(c)`: concept c is mentioned in at least one active leaf or span in the user's scope, **by any speaker**, Northstar echoes excluded (§5.9).
- `frontier_all`: concepts that are mentioned, not explained, and whose **direction-checked** prerequisites (over the whole concept graph) are all explained. A concept with no direction-checked prerequisite qualifies once it is mentioned and not explained.
- `later_all`: concepts that are mentioned, not explained, and have an unexplained direction-checked prerequisite.
- `frontier(d)` for each **possible direction** d (an inferred interest, §6.1): the same definition over G(d). Every item from it is labelled "inferred".
- `frontier(r)` for each **reported goal** r (§5.8): the same definition over G(r). Every item from it is labelled "provisional: from a goal as reported by the chat model".

**Which frontier a place uses.** A page or chapter on an explicit goal's path uses that goal's frontier. Otherwise "Next from here", "Ahead" and the first screen use `frontier_all`, restricted to concepts linked to that page or chapter, plus labelled items from directions and reported goals. So every place that can show a next step has a source of next steps, goal or no goal. An `offer` (§6.1) is never a frontier item on any of these frontiers.

**What the reader sees.** "Explained to you by Claude on 12 Sep" or "you stated it on 5 Oct", with a link to the record. Nothing claims anything about the reader's state: no "you have learned", "covered", "known" or "mastered" (D14). There are no counts of explained, used or remaining items, no fractions, no bars.

**Prerequisite edges are noisy** (F1 about 0.7, reversed direction common [12 F11]):
- Edges are LLM-proposed, with a separate direction check, cycles removed (drop the lowest-confidence edge) and transitive reduction [12 Model C].
- Only direction-checked edges above a confidence bar (starting value 0.7) order pages or define the frontier. Others render as "Related".
- Every frontier item shows its reason, so a wrong edge is visible. One click rejects it ("Doesn't build on this", §9.1).
- Frontier predictive validity is measured passively (§13 G). If it does not beat a popularity baseline, the frontier is redesigned, never removed (SYNTHESIS §7 ablation rule).

### 6.4 Next steps, with reasons

A deterministic score ranks frontier items, AI-suggested next steps, open questions and checks:

`score = 3·goal_relevant + 1·direction_relevant + 2·ready + 1.5·unblocks + 1·question_recency + 1·suggested + 1·relied_unchecked + 0.5·mention_breadth − 0.5·blocked`

- `goal_relevant` is 1 for an item on an explicit goal's path, 0.5 on a reported goal's path, else 0.
- `direction_relevant` is 1 for an item on a possible direction's path. Its weight is low because directions are inferred.
- `ready` is 1 only when a direction-checked prerequisite exists and is explained; otherwise 0.5. A concept with no known prerequisite is not shown as "builds on what you have".
- `suggested` is 1 when an AI (or the user) recommended the item as a next step in a conversation, as a `learning_suggestion` (§6.1). It counts once per concept per conversation, so a chat that repeats a suggestion does not inflate it. It counts suggestions from any speaker the same way. An `offer` never sets it.
- `relied_unchecked` covers an unchecked claim from any speaker that the user then used.
- `mention_breadth` is the number of independent episodes that mention the concept, capped at 3 and scaled to 0–1. It ranks goal-independent frontier items.

**The goal-independent first screen.** When no explicit goal applies (§10.4), items with mention breadth ≥ 2, a user question or an AI-raised question rank first. This is a ranking preference, not a filter: if too few items qualify, the block is filled from the rest of the ranked list, so it is never empty while any frontier item exists.

Weights are starting values, tuned once on frontier predictive validity (§13 G), then frozen. Each item shows one reason in plain words:

| Code | Shown as |
|---|---|
| ready | "Builds on 4.1.2 and 4.2.3, both already in your book" |
| asked | "You asked about this on 4 Oct (Claude Code)" |
| raised | "Raised by ChatGPT on 3 Oct and still open: '…'" |
| suggested | "Suggested by Claude (12 Sep): '…'" (a T label plus a Q quote; the labelled gist on a desktop chat until reconciled) |
| mentioned | "Mentioned in 3 conversations (Claude, ChatGPT, you), not yet explained in your book" |
| direction | "Fits a possible direction (inferred): event-driven systems" |
| unsettled | "Claude and ChatGPT disagree" |
| check | "You relied on an unchecked claim here" (any speaker's claim) |
| dangling | "Used in 3 explanations, never explained" |

These are possibilities, not tasks. Nothing is due, overdue, assigned or counted down.

### 6.5 Stubs: no invented teaching

A stub page holds only T and Q sentences (invariant B12):

- "You set this goal on 2 Oct (Claude Code): '…'."
- "You asked: '…' (Codex, 4 Oct). Not yet answered." From a desktop chat before reconciliation, the labelled gist instead: "A question as reported by ChatGPT (ChatGPT Desktop chat, 4 Oct), not your original wording: …".
- "Mentioned by Claude while explaining 3.2.1 (12 Sep): '…'."
- "Suggested by ChatGPT as a next step (3 Oct): '…'."
- "Builds on: 3.2.1, 3.2.3 (already in your book). Needed first: 3.2.5 (not yet explained)."

The compiler never writes an explanation of a concept no source explained. That would be teaching with no conversation behind it, which GOAL §3.2's traceability rules out. Whether the user wants such gap-filling is Q2.

**Graduation in place.** When a stub concept gets its first explanation leaf, its page graduates. It keeps its ID and address. Between editions it stays in the forward chapter, marked "now explained". At the next edition, clustering places it in a regular chapter, with a redirect. If most of a forward chapter graduates, the chapter becomes a regular chapter and keeps its ID (§7.2).

### 6.6 Not a task list

- No checkboxes, due dates, streaks, badges, progress bars or "items to review".
- **"Ask about this"** (optional) on any frontier item, stub or gap copies a short, neutral prompt naming the topic and the relevant page, which the user can paste into any connected product. If they do, that conversation is captured and becomes a new, attributed source, so the book grows with full traceability. Nothing records whether the user used it.
- **"Hide from next steps"** removes an item from the next-steps lists for that goal (or from the goal-independent lists). It says nothing about what the user knows. It is stored as a view correction and can be undone.
- **No knowledge-state labels.** The book does not show "confused", "I already know this", or any engagement state. Whether the user wants any engagement summary is Q5.
- An answered question is never deleted. It leaves the open register, and its page records when, by whom and where it was answered.
- **Frontier items travel to the AI side** through its pack (SYNTHESIS §3.4), so a next step can come up in normal work. The AI side decides relevance; the book adds nothing to the pack beyond item IDs.

---

## 7. Evolution without losing history or landmarks

### 7.1 Cadences

| Unit of change | What changes | How often | Reader sees |
|---|---|---|---|
| **Just in** | Leaf items promoted by the slow lane, shown as cited gists with chips in the page's rail | About 2 hours after the chat [13 §I] | A "Just in" rail, so nothing waits for the nightly compile |
| **Printing** | Content: new sentences, examples, chips, refutation blocks, short notes, new pages (with insertion numbers), graduations | Nightly, after compile and validation (§8) | Change bars; "new since you last read"; a printing date |
| **Edition** | Structure: membership, order, numbering, titles, splits and merges | A bootstrap edition at the first printing that has pages and after any export backfill; daily for the first 14 days; then at most weekly; part-level changes at most monthly outside the growth regime; only if the gate passes (§7.3) | An edition note on the first screen and on every affected page: what moved and why, with "Put it back" |
| **Correction** | Whatever the user changed (§9) | Seconds, by code | "Corrected by you on [date]", with undo |

The book body takes slow-lane items only [13 §B.5]. Provisional fast-lane items stay on the AI side and in the in-chat "this chat draws on" card (§10.8).

Every printing and edition is kept. The reader can open any page, chapter or the contents **as of a date**, from recorded block versions and the ledger's as-of queries (SYNTHESIS §5 item 3). Nothing is regenerated for this.

### 7.2 How the structure is computed (deterministic and replayable)

Structure is never a free-text model decision. Code computes it, so it is testable, reversible and replayable.

**Graph.** Nodes are page concepts, plus **anchor nodes** for active confirmed goals and open questions. Reported goals and possible directions are not anchor nodes, so a later rejection of one causes no structural churn (§5.8). Edge weights are a fixed table:

| Edge | Weight |
|---|---|
| prerequisite, part_of, broader | high |
| goal → its target concepts (`advances_goal`); question → concepts it asks about | high |
| compares, example_of; co-occurrence in one passage | medium |
| co-occurrence in one episode, decayed with age | low |
| embedding similarity above a threshold, top 5 neighbours (versioned cache keyed by concept version and embedding model) | low |

**Algorithm (J8.1).** Leiden with a fixed seed and a recorded library version.
1. **Level 1, chapters:** run Leiden on the graph, **warm-started** from the previous edition's membership. Resolution targets a median chapter of 6 pages.
2. **Stability cost** (evolutionary clustering [12 F16]): for each page the run moved, compute its own quality gain. Revert the move unless the gain beats a threshold scaled by the page's **landmark weight**.
3. **Constraints** (I21): pages with a "must be under" correction are fixed. "Must not be under" and "keep apart" pairs are forbidden. "Keep together" pairs are contracted to one node before the run.
4. **Size bounds:** chapters outside 3–15 pages are split by a sub-run or merged with their strongest neighbour. While the Book is below the size minimums, the "growing book" form applies instead (§7.3).
5. **Anchor typing**, by rule: a chapter gets a **goal anchor** if a goal node falls in it and that goal's targets make up at least half its pages; else a **question anchor** if an open-question node with at least 3 linked pages falls in it and those pages make up at least 40% of it; else a **concept anchor**, its most central concept. Anchor nodes shape the clusters but are not rendered as members: goals and questions live in Part 0.
6. **Level 2, parts:** repeat steps 1–4 on the graph of chapters. At most 9 subject parts, plus Part 0 and the Casebook.

**Landmark weight** raises the cost of moving a page the reader relies on. It comes from implicit signals only: page opens (a per-page open counter in `reader.db`), in-chat slice references, and corrections. No user action is needed to create it. Reader state stays local. The human compiler (C16) receives only the derived per-page weight vector from the Reader (C17), through `landmark_signals` (SPINE §6.3), and only that vector enters the book ledger.

**Identity matching.**

| Object | ID | Rule |
|---|---|---|
| Page | `pg_` + canonical concept ID | Never changes. A merge redirects the absorbed page to the survivor with a banner; an unmerge restores the old ID |
| Concept split (meaning changed) | New concept IDs, minted by the core's concept identity policy [12 decision 6] | The old page becomes a short chooser for two editions, then redirects |
| Chapter, part | `ch_` / `pt_` minted on first appearance | Matched across editions by weighted Jaccard overlap of members with Hungarian assignment; overlap ≥ 0.4 keeps the ID. An unmatched chapter retires with a typed `merged_into` or `split_into` event and a redirect |
| Block | hash(page ID, block type) | Stable while both exist |
| Sentence | hash(block ID, sorted citations, normalised text) | Stable while reused (§8.9) |

**Ordering and numbering.** Pages in a chapter, chapters in a part and parts in the book follow topological order of direction-checked prerequisites, ties by first-encounter date (pages) or creation date (chapters, parts), then ID. Numbering is **per part**: 4.2.3 means Part 4, chapter 2, page 3, so a change in Part 4 never renumbers Part 5. **Between editions numbers are frozen.** A new page takes an insertion number at its topological place, such as 4.2.3a, as Luhmann did with his cards [02 F1]. **Parts and chapters keep their numbers across editions too.** A new chapter or part takes an insertion number at chapter or part level, such as chapter 4.2a or Part 5a, so a growing book does not shift the numbers a reader has learned. Insertion numbers are cleaned up rarely, only at an edition and inside the churn budget (§7.3). Any renumbering counts against that budget, is listed in the edition notes, and old numbers redirect.

**Labels (J8.2).** A model proposes titles only for new chapters, or when membership has changed by more than 40% since the title was set. A deterministic check then requires: at most 6 words; every content word drawn from member concept labels, their aliases, or the anchor goal or question; clearly different from sibling titles. If the check fails twice, the title is the anchor concept's preferred term, chosen by code. A page's title is its concept's preferred term, which changes only when a new term has led in usage for two weeks. Old titles stay as aliases in search and the index. A title the user set is fixed (I21).

**Placement between editions.** A new page goes into the chapter where it has the most edge weight, if that is clearly above the next best (a congruence router [01 F4]); otherwise into the best guess, marked "placement tentative". Nothing waits in a visible inbox. A tentative placement is settled at the next edition. Tentative placements and their age are a sentinel (§8.12).

**Replay.** Every J8 input is snapshotted into the book ledger at the edition watermark: the graph, the previous outline, active corrections, the landmark weight vector, the embedding cache version, the seed and the library version. Replaying the book ledger rebuilds every edition hash-identical (invariant B10, I18). Structure is path-dependent by design, because history is part of the landmarks; "rebuild" means replay, not re-clustering from nothing.

### 7.3 The edition gate and churn budget (J8.3)

| Landmark | Rule |
|---|---|
| Page address and ID | Never changes; redirects on merge, retire or split |
| Page title | The concept's preferred term, with two-week hysteresis, or the user's rename |
| Page's chapter | Changes only at an edition, only if the move beats its landmark-weighted threshold |
| Chapter title | Changes only if membership moved more than 40%, or by the user's rename |
| Numbering | Frozen between editions; per part. Chapters and parts keep their numbers; new ones take insertion numbers (4.2a, 5a). Renumbering counts against the churn budget |
| First-screen layout | Fixed slots (§10.4) |

**Churn budget per edition** (starting values, calibrated on the golden book): at most 5% of pages change chapter; at most 3 chapter titles change; at most 2 chapter splits or merges; at most 1 part-level change a month. Any renumbering counts against the budget.

An edition over budget is **held**. Held is not a queue. The previous edition stays live, and the next scheduled run retries automatically with a higher stability weight. This is quarantine with an automatic exit (SYNTHESIS §3.5). Many weeks will publish no edition. A→B→A moves within four editions are a sentinel.

**Growth regime.** A new Book has few pages, and the budget above would freeze a structure built from a handful of chats. So:
- A **bootstrap edition** runs at the first printing that has pages, and after any export backfill. It is exempt from the churn budget.
- Editions run **daily for the first 14 days**, then weekly.
- Tentative placements, pages younger than 2 editions, and newly minted chapters or parts **never count against the budget**.
- The **part-level budget is free** while the Book has fewer than 60 pages, or grew more than 25% since the last edition.
- Below the size minimums (§4.2), the contents use a **"growing book" form**: one subject part, with chapters of one page or more. The usual bounds apply once the Book is large enough to meet them.

The growing-book form is how a small Book is shown; no edition is held or retried because the Book is small. Landmarks still hold throughout: page IDs never change, and moves are listed in edition notes with redirects.

### 7.4 Dormant topics fold in place

A store that keeps every past self can weigh on the present [02 pitfall 8]. A chapter with no new leaves, no opens and no link to an active goal for 120 days collapses in the contents with "dormant since [date]". **It is not moved.** Its number and place are kept, so location memory holds. It stays searchable, and new activity unfolds it.

### 7.5 How each kind of change is rendered

| Change in the core | In the book |
|---|---|
| New leaf on a page | "Just in" rail until the next printing, then woven into the explanation or examples, with a change bar until read or for 14 days |
| New concept | A page (if it meets §4.7) or a short note, placed by the congruence router |
| Supersession, with reason (SYNTHESIS §3.1 step 2) | The old leaf leaves current prose; the next printing's prose is built only from current leaves. A refutation block (§7.6) shows the change. No struck-through prose, because old prose is never input to anything |
| Tension resolved automatically (AD19) | As supersession, with the reason and the outranked side visible |
| Contested residue | Both sides in "Still open", each attributed, rendered by code from the Tension record; a spawned question in Part 0 |
| Verification change | The chip changes; an entry in the changes log. A claim that becomes contradicted moves to "How this changed" with the verifier's evidence |
| Capture upgraded or conversation joined | The chip changes in place (§5.8); a typed event in the changes log |
| Excision (started by the user) | Leaf and spans removed from every block, edition, export and slice cache; a tombstone "removed at your request on [date]"; a grep afterwards returns 0 hits (B16) |
| Merge | Both old addresses resolve to the merged page, which notes "merged from", with undo |
| Split | Each page notes "split from", with undo; the old address shows a short chooser |

### 7.6 Refutation blocks, rendered from records

When an item is superseded or contradicted, the page shows a block shaped like a refutation text (E10, [01 F5]). **Every field comes from a record. No model prose.**

| Field | Source | Shown as |
|---|---|---|
| **Earlier** | The superseded item | If the user held it, and its speaker and wording are by construction or reconciled: "You said (14 Sep, Claude Code): '…'". If it is a model-reported user item: "The chat model's account of your message (14 Sep, Claude Desktop chat), not your original wording: …" (§5.8). Otherwise: "Earlier, Claude explained (2 Sep): '…'". Quote if verbatim or reconciled, else its gist with the fidelity label |
| **Why it seemed right** | `Supersession.causal_alt_ref`, a recorded leaf | That leaf's quote or verified gist, attributed. **Omitted if no such leaf is recorded.** Never inferred |
| **What changed it** | `Supersession.reason` and the superseding evidence | A template per reason: "a newer source", "Claude corrected itself", "an independent check found it contradicts [source]", "you said later", "you corrected it", each with the evidence quoted and chipped |
| **Now** | The current item | The user's quote if theirs; otherwise the attributed quote or gist |

The block appears inline for the first three opens after the change, or 30 days, so old and new are co-activated (KReC [01 F5]). Then it folds in place under "How this changed". It is never deleted. Superseded and contradicted leaves feed only these blocks and history, never current prose (enforced by the input assembler and V2, §8).

### 7.7 What changed since you last read

- **Reader state** is per reader, local and private: the last printing seen for each page. It is stored apart from the knowledge ledger, never enters AI packs, is covered by excision, and can be switched off. Reading is never treated as learning.
- **Changes are computed from cited leaf sets, not text diffs:** "new" means a sentence cites a leaf the reader has not seen; "changed" means a paragraph's leaf group changed; "gone" means a leaf was superseded, contradicted or rejected and now appears in a refutation block.
- **First screen,** "Since you last opened": at most 5 lines, in this order (§10.4):
  1. changes to things **the user held** (user-said or user-accepted items that were superseded or contested, with speaker and stance by construction or reconciled, §5.8), because co-activating old and new is what updates a person [01 F5]. The line reads "A view you stated has changed" only for these; an earlier AI explanation that changed reads "An earlier explanation has changed";
  2. new disagreements between sources;
  3. new pages and pages with new material.

  Above these lines, a **state line** lists corrections applied from chat, or applied in the last 24 hours, each with one-click undo (§9.1, §9.2). It reports what changed; it asks for nothing.
- **Pages:** quiet change bars beside new or changed sentences until the reader scrolls past.
- **Chapters:** the "Welcome back" opener after a gap (§4.5).
- **Changes view:** every printing and edition, each change linked to its ledger event and its undo.

### 7.8 How understanding evolved over time

- **History tab** on every page: a dated list of events from the ledger: first met (conversation, product), explained by, you asked, you said, superseded, contested, verified, moved at an edition, corrected by you.
- **Timeline:** month by month, what entered the book, which questions opened and closed, which views changed, which goals started or ended. Generated by code. The user writes nothing.
- **As of a date:** any page, chapter or the contents, exactly as it was.
- All three show past beliefs as quoted, dated records (§5.7).

### 7.9 Restructuring, not just patching

Some conceptual change is a change of category, not an edit to one claim (Chi 2008, [01 F6]).

- Each page keeps an **anomaly count**: leaves the linker marked as contradicting or not fitting the page's key idea [01 idea 8].
- Past a threshold, the page becomes a **split candidate**. At the next edition, J8 tests a deterministic split (Leiden on the page's own leaf subgraph) and accepts it only if the objective gain beats the threshold and the churn budget allows it. A concept split mints new concept IDs through the core's high-risk path (different-family verifier, 100% L4 audit, [13 §D]).
- The edition note explains the split. The old structure stays viewable as of its date.

---

## 8. How the AI writes the book reliably

The maintainer can lose focus (GOAL §3.4, §4.7). So structural correctness never rests on one model call. Code assembles inputs, validates outputs and decides what is published [13 §A].

### 8.1 Pipeline

```
 core ledger (append-only)              book ledger (append-only)           output
 ─────────────────────────              ─────────────────────────           ──────
 items, spans, relations,     J7.1  snapshot at a watermark
 attributions, corrections ──────►   concept graph              J8.1–J8.3 (weekly edition)
                                     │                          cluster ► match IDs ► anchor ► order
                                     ▼                          ► label (model, checked) ► edition gate
                              J7.2  page eligibility + one home block per leaf + segment groups
                                     ▼
                              J7.3  leaf-group fingerprints ► dirty paragraphs and blocks
                                     ▼
                              J7.4  block writer (model, stateless, leaves only)
                                     ▼
                              J7.5  validators V1–V15 (code, 100%) + entailment (other family, 100% of new)
                                     │   fail twice ► extractive fallback (code)
                                     ▼
                              J7.6  assemble + render ────────────────────► Reader pages, slices,
                                     ▼                                       one-way export
                              J7.7  diff + change notes ──────────────────► "since you last opened"
```

These are sub-steps of SYNTHESIS's J7 (regenerate views) and J8 (reorganise). They run under the code orchestrator with leases, idempotency keys and recorded outputs [13 §A]. Workers are stateless, with no network, no writes and no delegation.

### 8.2 What the model writes, and what code writes

| Model writes (R and B sentences only) | Code writes (T and Q sentences, and everything else) |
|---|---|
| Key ideas | Headers, "Where this fits", e.g. labels and quotes, "In their words", "From your work" cases, "Your own words" |
| Explanation segments and their headings | Refutation blocks, "Still open", disagreements, "Next from here", stubs |
| The one "what these share" line after cases | "Who taught you this", sources, history, chips |
| Chapter and part big pictures (at most 5 sentences each) | Chapter and part openers and closes except the big picture; recaps (transcluded key ideas) |
| Chapter and part title proposals (checked, §7.2) | Contents, first screen, timeline, glossary, index, sources register, answer pages |

**No model prose is ever built from other prose.** Big pictures at chapter and part level are compiled from leaves, like every other model block (§8.3). There is no model prose above part level, and none in any block about change, disagreement or the user's past.

### 8.3 Inputs: leaf items only

J7.4's input assembler type-checks that it receives only leaf items and span text, never page text, chapter text or another block's prose (I7, invariant B2).

| Block | Built from |
|---|---|
| Key idea | The concept's definition leaf, if any, plus its top leaves by the speaker-neutral rank |
| Explanation | The page's top-ranked Statements and Passages, grouped in code in J7.2: first by J3 kind tag (definition, mechanism, comparison, caveats, applications, in that order), then within a kind by fixed-seed clustering with a stability term. Each group keeps a persistent per-concept sub-topic ID, and new leaves join an existing group by rule. Headings stay model-written and entailed. Also the paragraph plan (group IDs and leaf-ID groups from the last version, no prose) |
| e.g. lines, "From your work" | Episodes linked by `example_of` or `applied_in`, and their spans; the model returns a span ID, code pulls the quote |
| "What these share" | The leaves behind the chosen cases |
| Chapter big picture | Leaves linked to two or more of the chapter's pages, selected by code; with too few, the chapter's top leaves (§4.5) |
| Part big picture | Leaves linked to pages in two or more of the part's chapters, selected by code; with too few, the part's top leaves (§4.5) |

**Excluded before the model sees them** (not merely validated afterwards): superseded, contradicted, hidden and user-rejected items; items in another scope (I17); items whose scope does not allow processing by the writer's model vendor (§8.15); `northstar_echo` spans as support.

### 8.4 The output contract

Each J7.4 call returns structured output. Structured outputs guarantee syntax only [13 F6]; everything else is checked by code.

```yaml
page_id: pg_01J8...
block: explanation
plan_version: 41
paragraphs:
  - plan_id: p1                        # reused when the leaf group is unchanged
    group_id: sg_4                     # persistent sub-topic group from J7.2 (§8.3)
    leaf_group: [st_91K@3, ps_7Q2@1]
    heading: {text: "Events are the record; tables are views", cites: [st_91K, ps_7Q2]}
    sentences:
      - {kind: R, text: "...", cites: [ps_7Q2], role: explain}
      - {kind: B, text: "...", cites: [st_91K, ps_7Q2], relation: rl_55, role: contrast}
    example: {episode: ep_311, span: sp_9002}   # code pulls the quote from the span
```

Roles: `define`, `explain`, `contrast`, `caveat`, `connect`, `share`. The model never produces quotes, speaker names or chips. The paragraph plan records each paragraph's sub-topic group ID from J7.2, so segments keep their identity across printings; the model does not choose groups.

### 8.5 Code validators (100% of drafts)

A failure rejects the sentence or the draft and triggers the handling in §8.7. V10 is the exception: it warns and never rejects.

| # | Check | Rule | Ties to |
|---|---|---|---|
| V1 | Citation closure | Every R sentence and heading cites at least one leaf; every B sentence cites at least two leaves and one relation | I8 |
| V2 | Citation validity | Every citation is in the allowed set, in scope and active. Superseded, contradicted, hidden or user-rejected items never appear in current prose | I8, I17, I21 |
| V3 | Leaf-only input | The call's input contained no page text (assembler type check) | I7 |
| V4 | No attribution, no persons | R and B sentences contain no first- or second-person pronoun and no reference to the user's past. They may not use any registry agent, product or model name, or a generic agent noun (assistant, model, AI, user, author), as the subject of a speech or stance verb, or in an attribution pattern ("according to …", "as … suggested"), whoever is cited. Names may appear as subject matter only when they occur in a cited leaf's text (V6). Lexicon and detector below the table | I3, I4, §5.3, §5.7 |
| V5 | Quote fidelity | Every Q sentence is an exact substring of a `verbatim` or `reconciled` span (code inserts them; this re-checks) | I1, I2 |
| V6 | Grounded tokens | Every number, date, version, proper noun and code identifier in an R or B sentence appears in a cited leaf | invented details [12 F4] |
| V7 | Hedge and modality | If a cited leaf is tentative, the sentence keeps a hedge; if a leaf only suggests, the sentence keeps advisory modality; certainty boosters ("always", "proven") are rejected against tentative leaves | I10 |
| V8 | No code or formulas in prose | Code and maths appear only as verbatim quotes. Exception: an inline identifier or short formula (≤ 40 characters) that occurs verbatim in a cited leaf may appear in prose, rendered as code | code is never paraphrased |
| V9 | Coverage | Every leaf assigned to the block is cited, quoted or listed under "More"; no leaf is dropped without a recorded event | I9 |
| V10 | Size and anatomy | The limits in §4.2, as targets: a breach is a warning, never a reject | D5 |
| V11 | Correction compliance | Corrected attributions, labels and placements are used; no barred wording from a "Northstar misstated this" correction reappears (normalised similarity ≥ 0.9); blocks pinned to quote form stay in quote form | I21 |
| V12 | Coherence | No sentence opens with an anaphor ("This", "It", "They", "These"), or with a connective or definite reference from a lexicon ("However", "Instead", "As a result", "This approach", …), unless the sentence before it is in the same version of the same paragraph. After any sentence is dropped or reused, the whole paragraph is re-validated (V1–V11), and its heading must still be entailed by the remaining sentences. A paragraph whose reused sentence lost a neighbour is redrafted whole unless a paragraph-level coherence check passes | readability |
| V13 | Deterministic rebuild | Code-written parts rebuild hash-identical with model access off | I18 |
| V14 | Blast radius | Caps on blocks and pages touched per job | I13 |
| V15 | No restatement across blocks | No block restates another block's leaf above a similarity bar (start: cosine 0.9 or 0.6 containment), except as B5 allows; the later sentence is re-drafted | D3; B5 |

**V4's lexicon and detector.**
- **Speech and stance verbs** (starting lexicon, extended on the golden book): says, said, states, recommends, suggests, argues, claims, believes, thinks, explained, told, taught, warned, agreed, disagreed, prefers.
- **"Retells the user's past"** is detected as second person plus a past-tense verb of saying or learning, or a time phrase anchored to the user ("you said", "earlier you", "last week you"). World-history phrasing, such as a date when a technique became common, is allowed.
- **A prompt bug that inserts speaker names is still blocked:** a name as the subject of a speech verb or in an attribution pattern fails V4, and a name that no cited leaf contains fails V6.

**V6–V8 together.** V6 checks that every name, number, date, version and identifier in prose occurs in a cited leaf. V7 checks that prose keeps the leaf's hedges and modality. V8 checks that anything beyond an inline identifier or a short formula from a cited leaf is quoted, never paraphrased. A name that passes V6 can still fail V4 if it is used as a speaker.

### 8.6 Entailment checks (model, different family)

A verifier from a **different model family** judges each checked sentence against its cited leaves: entailed, not entailed, or contradicted. The working assumption is a local open-weight model on the Mac (SYNTHESIS AD9, spike S10), so entailment checks keep data on the machine. Other steps do not: the block writer and the L4 audit call a cloud API. §8.15 lists every flow off the Mac.

| Sentences | Coverage |
|---|---|
| Every **new** R and B sentence and heading | 100% |
| Every sentence transcluded into slices, cards, answer pages or the first screen | 100% (key ideas and big pictures are new sentences when first written, so this adds a re-check only when leaf versions changed) |
| A reused sentence | Keeps its recorded verdict **only** if its leaf versions are identical; otherwise re-checked |
| All sentences on a page after any failure on that page | 100% for its next 3 printings |
| Daily L4 audit by the strongest model, with full context | 5% of compiled blocks plus every chapter and part big picture |

Volume is about 200 checks a day at 100 turns a day (estimate), which a local model handles.

A verifier that wrongly rejects good sentences thins the explanation, so false rejects are bounded too: the verifier must meet a true-accept bar as well as a false-accept bar (§8.13), and a rejected sentence is re-drafted before it is dropped (§8.7).

### 8.7 When a check fails

1. A sentence the entailment check rejects is **re-drafted once** and re-checked by the same certified verifier. Only if the re-draft also fails is it dropped, and its paragraph re-validated as a whole (V12). This applies first to `contrast`, `connect` and `caveat` sentences, which carry the links between ideas. A second verifier route may decide a sentence only if that combined route is itself certified in S10 under the false-accept bar (§8.13). A sentence that fails a code validator is dropped, with its paragraph re-validated, except where the validator says otherwise (V10 only warns; V12 and V15 re-draft).
2. If the paragraph no longer covers its leaves or fails V12, the block is re-run once in a fresh call, possibly on another model [13 §A.3].
3. If that fails too, the block renders in **extractive fallback**: its leaves as verbatim excerpts and cited gists with chips, plus T sentences, in reading order. No model prose. The block says quietly: "Shown as cited excerpts while the explanation is rebuilt." This is a labelled degraded mode, not the design's normal page.
4. **Bar:** at most 5% of explanation blocks in fallback; an alert above 2% (T-FALLBACK).
5. The book never shows uncited or unchecked model prose, and never shows a hole.

### 8.8 The error budget and the automatic freeze

- **Trip condition, per block type** (key idea, explanation, share line, big picture): audited entailment errors among published sentences above 2% over a rolling 7 days, or any canary metric down more than a set margin.
- **On trip, without any user action:**
  - new and dirty blocks of that type render in extractive fallback;
  - every block of that type published since the last canary-passing baseline is re-verified at 100%; failures go to fallback;
  - if the trip lines up with a prompt or model change, that change is rolled back [13 §F.9].
- **Automatic exit:** when the golden-book canaries pass on the current model and prompt, and a fresh 100% re-verification sample of that block type passes, model prose resumes.
- This covers drift caused by the model itself, not only by a prompt change, because the freeze acts on output quality, not on a version number.

### 8.9 Text stability: paragraph memoization plus sentence reuse

Rewording a page on every rebuild would make everything look changed and erode recognition (E15). Wording is kept stable without ever feeding old text to the model.

- **Memo key** for a paragraph: hash of its sub-topic group ID (§8.3), its sorted cited leaf IDs and versions, the block type, and the corrections that affect those leaves. **The model and prompt hash are recorded but are not part of the key.**
- **Unchanged key:** the paragraph is kept byte for byte. No model call.
- **Changed key:** the writer drafts the paragraph fresh from leaves. Code then aligns draft sentences with the old version's sentences by **identical citation sets**, and keeps the old wording where the old sentence still passes V1–V12 and its recorded entailment verdict was on the same leaf versions. If fewer than half the draft's sentences would be reused, the new draft is taken whole. The paragraph is then re-validated as a whole (V12). A paragraph whose reused sentence lost a neighbour is redrafted whole, unless a paragraph-level coherence check passes, so reuse never leaves a patchwork paragraph.
- **Model or prompt migration** rewrites nothing by itself. A new model writes only paragraphs whose keys change. A deliberate full rebuild happens only if the L4 audit shows the old prose's error rate above the new model's by a set margin; it runs in shadow on the golden book first, then in stages [13 §F.13].
- **Quality release.** Frozen wording must not freeze weak prose for good. When a new prompt or model beats the old prose on the golden book by a pre-registered margin (rubric judge and reader A/B, run in shadow), pages are rewritten in stages as one labelled **"reworded" printing** with one edition note. Reworded sentences are new sentences, so they get 100% entailment checks. The release is a committed, golden-gated change (I19), never a silent drift.
- **T-STAB** (§13 F): no wording change without a leaf change or a recorded quality release, including across a model or prompt migration.
- Old text never enters the model (I7). Reuse is a deterministic choice between two texts, each checked against the leaves. It is not a summary of a summary.

### 8.10 Cost: one shared model at about 36K events a year

**Volumes** (estimate, ±2×). The three attempts assumed 11K, 15K and 36K leaves a year. This design uses one chain:
- about 100 turns and about 100 leaf candidates a day, about 36K ledger events a year [13 §I];
- after verification, deduplication and lineage grouping, about 40 new active leaves a day, about 15K a year;
- after a year, about 3,000 concepts, about 1,000 pages, about 2,000 short notes, about 120 chapters;
- about 20 dirty pages a night, because a day's work clusters in a few topics; at most 2 model calls each (key idea; changed explanation paragraphs), so about 40 calls, plus about 5 chapter big pictures and, on some nights, a part big picture (at most 9 parts, rebuilt only when their selected leaves change; under $0.50 a month, estimate);
- each call about 6K input tokens (2K a cached charter) and about 2K output, **including about 1.2K thinking tokens**.

**Prices** (checked 2026-10-08, https://platform.claude.com/docs/en/about-claude/pricing): Sonnet 5.5 batch $1 input and $5 output per million tokens; cache hits 0.05× the base input price, stacking with the batch discount; Opus 5.5 batch $2 and $10; Haiku 5.5 batch $0.05 and $0.25 (prompts up to 100K tokens).

| Item | Per day | Per month |
|---|---|---|
| Block writer, Sonnet 5.5 batch: 45 calls × about $0.014 | about $0.63 | about $19 |
| Retries and re-runs (+20%) | about $0.13 | about $4 |
| L4 audit, Opus 5.5 batch: about 7 blocks × (8K in, 1K out) | about $0.18 | about $5 |
| Titles at editions | under $0.01 | under $0.30 |
| Entailment on the local verifier (about 200 checks) | $0 API | $0 |
| Corrections (rendered by code through the extractive form) | $0 | $0 |
| **Total at 100 turns a day** | **about $0.95** | **about $28** |
| Same at 20 turns a day | about $0.20 | about $6 |
| Writer on Haiku 5.5 batch instead (quality unmeasured; needs the canary) | about $0.22 | about $7, mostly the audit |

- If the local verifier fails calibration (§8.13), the cost of the same-vendor fallback check follows [MT] §9.6's shared figure: about $52 a month at 100 turns a day and about $10 at 20. Opus 5.5 always thinks, so [MT] budgets about 300 output tokens per check. (An earlier figure here, $13, assumed 50.)
- A deliberate full rebuild or a quality release (§8.9) is about 2,100 calls, about $30, once, plus local entailment checks on every reworded sentence.
- **J7 flush rule** (as [MT] X22). Nightly printing never waits on a late batch. If a nightly batch has not returned by the printing's cut-off (starting value: 6 hours after submission, estimate), its unfinished calls are flushed to the standard API within the spend cap. Standard calls cost twice the batch price, so a flushed night costs at most about twice the writer's usual nightly cost.
- [13 §I] estimated the whole maintainer at about $40 a month at 100 turns a day, with "nightly regeneration" one of the two main costs. This table refines that share. It is higher than the attempts' figures ($5–17) mainly because it counts thinking tokens and the audit of book prose.
- Storage for a year of block versions and validation records is tens of megabytes. SQLite is enough [13 §I].
- These figures assume cloud API calls are allowed (Q7). If they are not, the writer and audit move to local models (§8.15): no API cost, quality unmeasured until the canary passes.

### 8.11 Book invariants (code)

| # | Invariant | On violation |
|---|---|---|
| B1 | Every R and B sentence and heading cites a leaf (I8) | Sentence rejected |
| B2 | Writers receive leaf IDs and span text only (I7) | Job refused by the input assembler |
| B3 | Every quote is exact and from a verbatim or reconciled span (I1, I2) | Quote rejected |
| B4 | No model-written attribution or persons (V4) | Sentence rejected |
| B5 | Every eligible active leaf has exactly one home block and is reachable; nothing disappears without a recorded event (I9). Two exceptions: an explanation leaf may be cited by the explanation's prose and also quoted once, at ≤ 150 words, in "In their words"; the key idea may cite a leaf homed in another block | Edition held; block re-run |
| B6 | Every active correction is honoured on every page (I21) | **That page** is withheld and repaired; the rest publishes (§9.4) |
| B7 | The outline is a tree; reading order is a valid topological order of the reduced prerequisite graph | Edition held |
| B8 | No page, chapter or part ID disappears without a typed event and a redirect | Edition held |
| B9 | Churn within budget per edition (I13) | Edition held; retried with a higher stability weight |
| B10 | Hash-identical replay with model access off (I18) | Alert; render frozen at the last good build |
| B11 | AI-said share in featured slots within 5 points of the **live reference** (the rank-weighted AI-said share among eligible active leaves assigned to the same blocks, §5.6 item 7), checked nightly on real data; at promotion, within 5 points of the eligible share, overall and for single-episode concepts. At evaluation, also within 5 points of the golden-set share | Alert, sentinel hit |
| B12 | Stub pages contain only T and Q sentences | Stub rejected |
| B13 | Grounded tokens (V6) and hedges (V7, I10) | Sentence rejected |
| B14 | Scope filter on every page, export and slice (I17) | Page withheld |
| B15 | Echo lineage, same-session or from a same-family session within 90 days with no fresh grounding (§5.9), never counts as support or toward promotion (I11) | Event refused |
| B16 | After excision, a grep over pages, export, block versions, editions and slice cache returns 0 hits | Excision job retried; alert |

### 8.12 What the maintainer watches

| Sentinel | Alert when |
|---|---|
| Citation closure, citation validity | Any rendered sentence lacks a valid citation (hard gate) |
| Validator reject rate per block type | Rises above its baseline (a worker losing focus, or a prompt bug) |
| Entailment failure rate | Above the error budget (§8.8) |
| Dropped sentences per block; B-sentence survival rate; explanation words lost to drops | Reported per verifier certificate. Alert when drops rise, or B-sentence survival falls, against the golden-book baseline for that certificate (§8.7) |
| AI-said parity (featured slots, promotion), nightly on real data | Gap above 5 points from the live reference (B11) |
| Warning-chip parity | AI-said and user-said shares of warning-chipped sentences differ from their shares of unchecked checkable claims by more than 5 points |
| Off-machine flows | Any model call or slice delivery that carries an item its scope does not allow to that vendor (§8.15) (hard gate) |
| Fallback blocks | Above 2% (alert), 5% (bar) |
| Stale pages | Any page dirty for more than 48 hours |
| Text churn without a leaf change or a recorded quality release | Any (memoization broken, §8.9) |
| Edition churn | Over budget; any A→B→A within 4 editions |
| Tentative placements | Any older than 14 days. Action: placement at the next edition (§7.2) |
| Correction survival | Any active correction violated on any rendered page (hard gate) |
| Conversation identity | Items "not identified" above 1%; session-only items unjoined after 30 days on a surface where a join path exists |
| Freshness | Fewer than 95% of new leaves in "Just in" within 3 hours, or in a printing within 30 hours |
| Compile cost | Above the monthly budget |

All sentinels are code. None asks the user to do anything (SYNTHESIS §3.5). **The Book's sentinels join [MT] §7.2's controller registry.** Each is registered there with its metric, threshold, hysteresis, automatic action (as this file states it, in the section cited) and precedence, so no two controllers act on one signal in conflicting ways. A footer line in the Reader shows the state in neutral words ("Printed 06:10 · all checks passing") and links to a read-only page.

### 8.13 If the local verifier fails calibration (RISK 18)

The local open-weight verifier must pass the pre-registered S10 bars on the golden book, as [MT] §6.5 sets them (ARCH R7: [MT] §6.5 wins). For entailment these are: the **Wilson 95% upper bound** of the false-accept rate on planted unsupported sentences below 5%; and the **entailment true-accept bar** of [MT] §6.5 (≥ 90%, stratified by R and B sentences), so the verifier neither passes bad sentences nor drops good ones (§8.7). If it fails, independence of the entailment check cannot be certified. The design then acts automatically, in this order (ARCH R12):
1. The same-vendor check runs at once, flagged not independent (table below).
2. A second local family is tried against S10. If one passes, it becomes the verifier and independence is restored.
3. ARCH DQ-12 (SPINE UQ-4) is asked: may another vendor's model check? Until a yes, only the same-vendor path runs.

| Check | Moves to |
|---|---|
| Entailment on new sentences | Still runs locally as a first screen, **plus** a second check on 100% of new R and B sentences by Opus 5.5 (same vendor, stronger model), flagged `independent: false`. Another vendor's model is used only after a yes to ARCH DQ-12, and only for items whose scope allows cross-vendor processing (I17) |
| L4 audit | Raised from 5% to 20% of compiled blocks |
| Error budget | Tightened from 2% to 1% |
| Reader footer | Says in plain words: "Checks partly use the same model vendor as the writer" |

**What the user is told.** The change takes effect automatically. Nothing waits on the user, and no action is needed. The user is informed once, in a read-only note linked from the Reader footer: which checks are no longer independent, for which items, what a second vendor would see, and that verifier choice is a design decision under GOAL §5 (models are HOW), which the design has made and reports. A second vendor sees memory only if the user said yes to ARCH DQ-12 (SPINE UQ-4); otherwise the same-vendor path runs.

**Synthetic thresholds understate real error** (SYNTHESIS RISK 6). Bars are calibrated on the synthetic golden book. Real-data error is estimated separately from L4 audits on real items and from corrections used as labels (L6), and is reported separately. Synthetic figures are never presented as real ones.

### 8.14 When one worker loses focus

- Workers are stateless. Each call sees one block's leaves and nothing else, so an error stays local.
- Every structural rule is code (V1–V15, B1–B16, I7–I10, I13, I21). A degraded worker can produce weak prose, but not uncited, misattributed, misquoted, unhedged or correction-violating prose.
- Semantic errors (a cited sentence that subtly misstates its leaf) are caught by the 100% entailment check and the daily audit, and bounded by the error budget. Automatic verification agrees with humans only about 72–76% of the time [12 F9], so this is bounded, not eliminated (RISK H16).
- Rollback by job, batch or model restores Book structure by a **compensating edition** with redirects, not hash-identically. Pages re-render from recorded outputs without the rolled-back job, so its faulty text does not come back. Fault injection tests it (§13 H).

### 8.15 Data that leaves the Mac

"Local now" (GOAL §2, 2026-10-08) holds for storage and services: the core, the ledgers, the Reader and the MCP server run on the Mac. Some book steps still send captured content off the machine. They are listed here so none is hidden. Whether "local now" allows cloud model calls on captured content at all is question **Q7**, and the risk is **H21**.

| Flow | What leaves | To whom | When | Gate |
|---|---|---|---|---|
| **Block writer** (J7.4) | Leaf text and span text of dirty blocks | Anthropic API (Sonnet 5.5, batch) | Nightly | Redaction first (SPINE §8.5); I17 scope, including cross-vendor scope, applied to the input |
| **L4 audit** (§8.6) | Sampled blocks with their leaves | Anthropic API (Opus 5.5, batch) | Daily | As the writer |
| **Title proposals** (J8.2) | Member concept labels and anchor text | Anthropic API | At editions | As the writer |
| **Fallback verifier** (§8.13) | New sentences with their leaves | Opus 5.5, or another vendor only with a yes to ARCH DQ-12 (SPINE UQ-4) | Only if S10 fails | As the writer |
| **Slices and cards** (§10.8) | Compiled book text | The vendor of the chat that shows it | On a tool call | I17 scope; cross-vendor only where scope allows |
| **ChatGPT Desktop chat relay**, only if spike CS2 fails (SPINE §7.3) | Tool calls, slices and the model's reports of the chat | A tunnel or an OpenAI-hosted relay (connector-chatgpt-desktop-chat.md CR4; SYNTHESIS RISK 13) | Every tool call on that surface | Stores nothing (SPINE C03); the relay choice is ARCH DQ-4(iii) (moved there from SPINE UQ-5 by ARCH R16) |

The core's own extraction and verification calls belong to the system design (SPINE §8), not here.

**Cross-vendor scope applies to the writer and the audit, not only to slices.** Content captured from ChatGPT or Codex is OpenAI content. Sending it to Anthropic's API is cross-vendor processing. So the input assembler (§8.3) removes every item whose scope does not allow processing by the writer's vendor. Its block then goes:
1. to a **local writer** (an open-weight model on the Mac), if one has passed the golden-book canary for that block type; otherwise
2. to the **extractive fallback** (§8.7), labelled as usual.

Items marked `private` go to local models only (SPINE §8.5). The fallback-share bar (§8.7) is reported separately for blocks held back by scope, so a scope rule never looks like a writer failure.

**If the answer to Q7 (ARCH DQ-3(a)) is no,** every model step in this table moves to local models, and the relay question stays with the connector design and ARCH DQ-4(iii). Until a local writer passes the canary, explanation blocks render in extractive fallback. That degrades "reads like a textbook" (H21). It weakens no non-negotiable: nothing waits on the user, and the book stays complete and traceable.

---

## 9. Corrections with precedence

Correction is optional. Nothing waits on it (GOAL §4.3). Once made, it persists with precedence (I21).

### 9.1 One click in the Reader

Controls appear on hover. Every correction applies at once and shows an undo notice. An optional note field records the user's words as a user-typed item. Corrections applied from chat, and any applied in the last 24 hours, also appear in "Since you last opened" as a state line with one-click undo (§7.7, §10.4), so a correction the user did not mean is easy to see and reverse. Rate limits and step-up for bulk changes are in §10.3.

| Where | Gesture | Recorded as | Effect |
|---|---|---|---|
| Sentence menu or drawer | **Northstar misstated this** | Correction `misstated` on that sentence's text hash and citations | The sentence is blocked at once; its block re-renders in quote form (extractive) within seconds. The wording and near-duplicates (normalised similarity ≥ 0.9) are barred for good (V11). Counts as an L6 label against J7's error budget. The next printing writes new prose; it must pass entailment and one stronger-model check before quote form lifts. **The cited leaves' verification and stance do not change** |
| Drawer, on a cited item | **This source is wrong** | Correction `reject_content` | The item leaves current prose and AI packs; history shows "you marked this wrong". An optional "What's right?" creates a user-typed item that supersedes it (`reason: user_correction`) |
| Rail chip or drawer | **Wrong speaker** (pick: you, you pasted, an agent, a source) | Attribution fix | Chips and T sentences use the corrected speaker; the adapter's original role is kept in the record |
| Drawer | **Wrong conversation** | Dispute of an episode join | Identity drops to "session only" or "not identified"; code retries the join |
| Chip on a user item | **Not what I think** | Stance fix | The item no longer renders as the user's view |
| Example | **This example doesn't fit** | Reject the `example_of` relation | Example removed; never re-proposed |
| Any item | **Hide from book** | Hide | Not shown in the book; still in the core and in search with a filter |
| Page header | **Rename** · **Move to…** · **Keep it here** · **Same as…** · **These are different** | Label, placement (must or must not be under), pin, must-link merge, unmerge | Hard constraints for J8 (§7.2) |
| Contents | Drag a page | Placement | As "Move to…" |
| Prerequisite link | **Doesn't build on this** | Reject relation | Edge removed from order and the frontier |
| Next-step item | **Hide from next steps** | View correction for that goal | Removed from next steps; says nothing about what the user knows |
| Goal | **Not my goal** · **Done** · **Paused** | Goal status | Path and frontier recomputed |
| Reported goal (§5.8) | **Yes, that's my goal** (optional; also on the in-chat confirm card) | Goal confirmation, origin `reader_click` or `app_click` (pending Q6, asked as ARCH DQ-10); never counted on the turn the goal was reported | Moves from "Reported goals" to goals in the book; its frontier stops being provisional; wording stays labelled "as reported by the chat model" until verbatim text matches. It reaches AI packs as a goal only after a verbatim match, or after a yes to Q6; then its line reads "confirmed by your click; wording as reported by the chat model" |
| Question | **Answered** · **Not a question any more** | Agenda status | Moves to answered or history |
| Edition note or page | **Put it back** | Placement constraint (must be under the old chapter) | The move is undone and cannot come back (I21) |

Every correction is a typed ledger event with holder `user` and origin bound at write time (I20). The page shows "Corrected by you on [date]", with undo. **Excision** (permanent removal) is separate, starts only from the user, and asks to confirm (SYNTHESIS §5 item 9).

### 9.2 Corrections through chat, and origin binding

A tool call made by a chat model is untrusted input (SYNTHESIS §3.5). A model-mediated call, including one auto-approved under "Always allow", must never by itself create a correction with I21 precedence.

**Origins, defined without naming a product.** The core knows only these origins. Each connector maps its own channels onto them, in the table below and in its own design:
- `reader_click`: a click in the Reader.
- `app_click`: a click on an app-only control in an in-chat card.
- `chat_verbatim`: the user's words match, as an exact substring, a verbatim user turn from the connector's **fidelity channel** (a channel that delivers the user's typed text by construction).
- `chat_verbatim_reconciled`: the same match, made later, when verbatim user text arrives by reconciliation.

**When a chat match applies at once.** A `chat_verbatim` or `chat_verbatim_reconciled` match gains I21 precedence at once only when all four hold:
1. the matched span is outside paste ranges and outside Northstar-block ranges (text Northstar placed in the user's message);
2. the target was delivered or cited in this session (context receipts, §5.9), or the user's words name it by ID or quote it;
3. an independent-family entailment check confirms that the user span expresses this correction kind on this target. If no verifier is certified (§8.13), the correction stays a proposal;
4. at most 3 such corrections apply per session.

Goal-status changes and `reject_content` on items with verbatim user authority also need the user's words to name or quote the item. There is no minimum length: a short correction applies when these conditions hold. A match that fails any condition stays a proposal. Every correction applied from chat shows in "Since you last opened" with one-click undo (§7.7).

| Surface | Path | Origin | Precedence |
|---|---|---|---|
| **Reader** | A click | `reader_click` (session cookie plus CSRF token, §10.3) | I21 at once |
| **Claude Code, Codex** | The model calls `northstar_note(kind: correction)` with the target ID and the user's words as `quote` (`connectors-desktop-and-mcp.md` §2.3). The connector's fidelity channel here is the hook-captured user prompt (`UserPromptSubmit`; [10] F5, F9; checked 2026-10-07 by [10]) | `chat_verbatim` | I21 at once if the words match and the four conditions above hold; otherwise only a proposal |
| **Claude Desktop chat, ChatGPT Desktop chat** | The model calls `northstar_note(kind: correction)`, which records a **proposal** only. Its result renders a **confirm card** with one button, "Apply", which calls `northstar_widget_action(action: apply_correction)` from a trusted click, carrying a single-use `action_nonce` bound to the card instance, session and target (`connectors-desktop-and-mcp.md` §2.4, §3.5). That tool has app-only visibility: the MCP Apps spec says "Host MUST NOT include tools in the agent's tool list when their visibility does not include `"model"`" (checked 2026-10-08). Whether each desktop host honours this is (Unv), spikes S-R1 and S-R2. A missing, reused or expired nonce leaves the correction a proposal; so does every card action on a host that spike CX-S1 shows passes result `_meta` to the model | `app_click` | I21 on the user's click |
| **Desktop chats, if no card renders** | (a) The proposal shows on the affected sentence in the Reader: "You asked to change this in chat on 3 Oct. Apply?" It expires silently after 7 days and is never collected into a queue or counted on a badge. (b) When verbatim user text later arrives (observer or export join), code matches the user's words | `reader_click`, or `chat_verbatim_reconciled` | I21 on the click, or on a match that meets the four conditions above; **none otherwise** |

The same confirm card, with one optional button "Yes, that's my goal" (`northstar_widget_action(action: confirm_goal)`, the same nonce rule), serves reported goals (§5.8). It needs no answer: an unclicked card changes nothing and is never shown again in that chat. A click confirming a reported goal counts only from the widget or the Reader, never on the turn the goal was reported. With a yes to Q6 (ARCH DQ-10), a click-confirmed goal line reads "confirmed by your click; wording as reported by the chat model".

**Injection guard.** The server rejects a correction whose "user words" match assistant or tool text rather than user text, where known. Only user-typed text can create corrections, as with instructions (I5).

### 9.3 Pushback is not a correction

- **Pushback in a conversation** ("no, I don't think so") is captured by the AI side as a stance event (`disputed`). It does not change verification, because pressure is not evidence and challenged models flip 46% of the time [11 F4] (SYNTHESIS §5 item 7). The book shows it as a "you disputed" chip. The item stays in prose, with the chip.
- **A deliberate correction** through the Reader, a confirm card or a hook-verified chat message is a correction event with I21 precedence.
- Keeping the two apart lets the book stay honest about the user's stance without letting a sycophantic exchange rewrite knowledge.

### 9.4 Precedence in every compile stage (I21)

| Stage | How corrections apply |
|---|---|
| J7.1 graph | Rejected relations removed; merges and unmerges applied |
| J7.2 assignment | Hidden and rejected items excluded from current blocks; attribution fixes applied |
| J7.4 writer | Rejected, hidden and barred items are not in the allowed input or citation set |
| J7.5 validate | V2 and V11 reject any draft that cites them or reuses barred wording |
| J8.1 cluster | Fixed parents, forbidden parents, keep-together and keep-apart as hard constraints |
| J8.2 labels | Fixed titles are never proposed |
| J7.6 render and J8.3 gate | A deterministic check, page by page, that every active correction holds |

**If the check fails on a page,** only that page is withheld from the new printing. It renders in extractive form with the correction applied, which honours corrections by construction because it uses no model prose. J11 then re-runs the page automatically. The rest of the printing publishes. Correction survival stays a hard gate per page (§13 H).

A correction is lifted only by the user (undo) or by excision of its target.

### 9.5 When later evidence disagrees

The correction stands. The block shows a chip, "Newer evidence since your correction (ChatGPT, 9 Oct)", linking to the leaf. Nothing is escalated to the user (SYNTHESIS §3.2). Every correction also becomes an L6 label for calibrating the maintainer [13 §D].

---

## 10. The interface and medium

### 10.1 Choosing the medium

| Option | For | Against | Verdict |
|---|---|---|---|
| **Local web app served by the core (the Reader)** | Full control of typography, margin rail and drawer; one-click corrections with user origin; search; works offline; the same code runs in the cloud later | The core must be running; Mac only for now | **Primary reading surface** |
| Obsidian-compatible vault | Plain files outlast apps [02 F8] | Users would edit derived files, which then diverge [07 pitfall 6]; file edits cannot become typed corrections; invites global graph views [12 F15] | **One-way export only** |
| MCP App panels only | Inside the chat | Inline cards hold little and allow no deep navigation; they appear only after a model tool call ([10] F2; vendor, indirect, see Sources; "only" is (Unv), spikes S-R1, S-R2); ChatGPT Desktop rendering is (Unv) | **In-chat slices only** (§10.8) |
| Static site | Simple | Cannot receive corrections; stale between builds | No |
| Vendor-hosted artifact page | Easy to share | Personal knowledge on a vendor's servers; breaks "local now" | No |
| Native Mac app | Polish | Build cost; does not move to the cloud | A later wrapper at most |

**Decision.** Three pieces, all fed from one projection in the core:
1. **The Reader**, at `http://northstar.localhost:<port>` (served on 127.0.0.1, §10.3), opened by `northstar open`, a menu-bar item later, or "Open in book" from any slice.
2. **In-chat slices and cards** on the four first connectors (§10.8).
3. **A one-way export**: nightly Markdown (one file per page, IDs in front matter, citations as footnotes, Obsidian-compatible) and EPUB, to a folder the user chooses, never the repo. Each file starts with "Generated by Northstar. Edits here are not read back." Sensitive scopes are excluded unless the user allows them. The Markdown mirror and the EPUB apply the Reader's renderer rules (no raw HTML, no remote images, no `javascript:` links) and, to captured text, the one rendering rule of [AC] §3.2 (third-person restatement; commands in inert, labelled code blocks), so another app that opens them cannot be steered by captured text.

### 10.2 Local now, cloud later; personal now, enterprise later

- **One component library, two data adapters.** The Reader fetches JSON from the core's HTTP read API. The MCP App bundle renders the same components and fetches the same JSON through `tools/call` to the Northstar MCP server, never from localhost directly. So cards work the same against a local or a cloud core.
- **The Reader talks to the core only through its read API and correction API**, never to SQLite directly. That is what lets it move to the cloud unchanged.
- **Local now:** the core, the compile jobs, the Reader and the MCP server run on the Mac. Claude Desktop, Claude Code, Codex and the ChatGPT desktop app's local Codex threads reach the server locally. ChatGPT Desktop **Chat** mode appears to reach only remote MCP tools (connector-chatgpt-desktop-chat.md V1, V5, V6, checked 2026-10-08 by that design; see Sources). That is (Unv) until spike CS2. **A relay is needed only if CS2 fails** (SPINE §7.3, UQ-5; connector-chatgpt-desktop-chat.md CR4, CS7). Then slices and cards for that surface leave the Mac through the relay (§8.15). If CS2 passes, that surface reaches the local server as Claude Desktop does. Either way it gets four tools of the one contract, including `northstar_book` (`connectors-desktop-and-mcp.md` §2.2, §2.5); its plan path is (Unv), CS1.
- **Cloud later:** the same API and Reader behind sign-in, over HTTPS. Reader state moves server-side per reader. Phone and tablet reading come with it. Nothing in the page format depends on where it runs.
- **Enterprise later:** one book per person per scope; work scopes get their own book or parts under that scope's rules (I17). Pages never cite across scopes. SSO and admin retention policy are not designed here, and nothing here blocks them.

### 10.3 Safety of the local Reader

Captured AI text, pasted text and web content are untrusted. Rendered carelessly, a poisoned conversation could run script in the Reader and forge corrections through the write API. This is the human-side twin of prompt injection through stored memory (GOAL §5; SYNTHESIS §5 item 8).

- Bind to 127.0.0.1 only, on a random high port. Serve the Reader on its own host name, `northstar.localhost:<port>`, so its cookie is not shared with other local sites.
- `northstar open` launches the browser with a one-time token that sets a **host-only** session cookie. No cookie, no data.
- Check the `Host` header on every request (DNS-rebinding guard). No CORS.
- Write endpoints need a CSRF token and a same-origin request.
- **Correction rate cap:** at most 10 corrections a minute; extras become proposals, shown on their sentences for a later click.
- **Step-up for bulk changes:** bulk moves and hides need an explicit confirmation step before they apply.
- **Nothing private in browser history:** search runs by POST or in the URL fragment, never in a query string, and every page has a neutral `<title>`.
- A separate browser cookie jar for the Reader is an option behind spike SP-PL-16.
- Render all captured text through a Markdown sanitiser: no raw HTML, no script, no event handlers, no remote images, no `javascript:` links. A strict Content Security Policy forbids inline script.
- Respect scopes and sensitivity tiers (I17). Excision purges pages, caches, exports, slice caches and search indexes; a grep afterwards returns 0 hits.
- Red-team tests run in CI (§13 H).

### 10.4 The first screen

The first screen invites reading. It answers "where am I heading, where was I, what changed?" in fixed slots of at most seven items. Change lists are capped and come after the reading blocks.

```
NORTHSTAR · your book                          [ What have I learned about ...      ]

WHERE YOU'RE HEADING
  "Design an event-sourced ledger"   your goal, Claude Code, 7 Oct
      Next: Projections and CQRS · Bitemporal data · Deleting from logs
  Reported goal, not yet confirmed: getting comfortable with Rust lifetimes
      as reported by ChatGPT (ChatGPT Desktop chat, 20 Sep)        [Yes, that's my goal]
      Next (provisional): Lifetime elision · Borrow-checker errors
  Newest open question: deleting personal data from an append-only log
      (as reported by ChatGPT, 4 Oct; wording not yet confirmed)

CONTINUE READING
  4.2.3 Event sourcing (a chat used it yesterday) · 7.1.2 Rust lifetimes · 4.1.4 Idempotency

NEW THIS WEEK (not yet on a page)
  Outbox pattern: publishing events reliably alongside a database write   ◆ Claude, 6 Oct
  Tokio: an async runtime for Rust                                        ◆ ChatGPT, 5 Oct

SINCE YOU LAST OPENED (3 days ago)                                       [all changes]
  Applied from chat (Claude Code, today): "Not my goal" on "Learn Kafka"         [Undo]
  A view you stated has changed: "tables are just caches" (you, 14 Sep; see 4.2.3)
  New disagreement: snapshot interval (Claude and ChatGPT)
  New pages: Bitemporal data · Snapshotting

CONTENTS
  0 Where you're going · 1 Software architecture · 2 Rust · 3 Data stores · ... · 9 Casebook

Printed 06:10 · all checks passing
```

- **If no explicit goal applies,** the first block is titled "Where your work is heading". It shows, at most 7 lines: the top items of the goal-independent frontier (§6.3), each with its reason ("Mentioned in 3 conversations, not yet explained in your book"; "Suggested by Claude (12 Sep): '…'"); the newest open question, whether the user asked it or an AI raised it; and possible directions and reported goals, each kept apart and labelled "inferred" or "not yet confirmed". It never invents goals. Items with mention breadth ≥ 2, a user question or an AI-raised question rank first, with a fallback that keeps the block filled (§6.4).
- **New this week** is a reading block, also in Part 0: at most 7 "Just in" gists of concepts that have no page or chapter yet, each with its speaker and sources. It has no counts and is not an inbox: an item leaves when its concept is placed in a chapter (as a page or a short note), or after 7 days. In a young Book this is where new material is read first (§7.3, H22).
- **Corrections applied from chat**, or applied in the last 24 hours, head "Since you last opened" as a state line with one-click undo (§7.7, §9.2).
- "Yes, that's my goal" is optional. Nothing on the first screen counts or nags about unconfirmed goals.
- **No counts that describe the reader:** no "6 covered", no "3 ahead", no open-question count, no streaks, no badges, no "items need your attention".
- The footer states maintenance in neutral words and links to a read-only page. It never asks for action.

### 10.5 Reading a page

- A reading column of about 70 characters, the margin rail for source glyphs, and the source drawer sliding in from the right (§5.5).
- Previous and next in reading order; breadcrumbs; permanent links (`/p/<page-id>`, `/p/<page-id>#<block>`, `/p/<page-id>#<sentence>`, `/e/<edition>/p/<page-id>` for an old edition).
- **Term links:** the first use of a glossary term on a page links to its definition, with a hover card, done by code from the alias dictionary. A term the book does not explain carries the dotted "not yet explained in your book" underline on its first occurrence on the page (§6.2).
- Folded blocks ("Who taught you this", "Sources and history") open in place.
- The reference-view toggle sits in the page header (§4.6).

### 10.6 Navigation

- **Contents tree** on the left: parts, chapters, pages, collapsible; dormant chapters folded in place (§7.4).
- **Where this fits** links on every page; **Also in** cross-references.
- **Local map** (optional, per page): up to nine nodes, one hop, filtered by relation type. No global graph [12 F15].
- **Back matter:** glossary (each term's cited definition; differing definitions side by side with their speakers), index (one to four entry points per term [02 F1]), sources register (by product, date and conversation; each lists what it fed, with its capture panel, §5.8), timeline, open and contested register, editions and changes.
- Full keyboard navigation.

### 10.7 Search: "What have I learned about X, and from whom?"

Search is hybrid: SQLite FTS5 keywords plus embeddings, over page titles, aliases, sentences, leaf items and all stored spans. Quarantined proposals' source spans are included, labelled "uncertain" (SYNTHESIS §3.5). The result is an **answer page**, assembled by code with no model at read time:

```
What have I learned about "projections"?
Best match: 4.2.4 Projections and CQRS (Chapter 4.2 Keeping history)
From whom:  ◆ Claude 6 (Claude Code 5, Claude Desktop chat 1) · ◆ ChatGPT 2 · ● you 2 · ■ 1 document
Key points  (transcluded key idea and segment headings, with their sources)
  * A projection is a read model rebuilt from the event log.               ◆ Claude, 12 Sep
  * Projections should be versioned with the schema.          ◆ ChatGPT ○ unchecked, 3 Oct
In your words  ● 6 Oct: "the reading view and the AI's context are two projections of one log"
Also in: 4.2.5 Snapshots · 7.1 Search indexes
Conversations (5) · Open questions (1) · Changes (1)
```

- **"In your words"** uses only user items whose speaker and wording are by construction or reconciled. Model-reported desktop items appear under "Conversations" as labelled gists (§5.8).
- **Filters:** speaker (any registry agent, you, you pasted, sources), product, model, date range, verification status, capture fidelity, speaker fidelity, conversation, goal.
- **Typed queries** map to filter presets: "what did ChatGPT tell me about X", "what did I conclude about X", "what's still open on X".
- A free-form "Ask your book" mode is not in the prototype. If built later, it must pass the same validators as J7.

### 10.8 In-chat slices on the four first connectors

A slice is compiled book content shown inside a chat. It is **never newly generated text**, so the chat and the book always agree (T-SLICE). Slices are optional. Nothing depends on them.

**Slice types** (all but the confirm card are `northstar_book` views, `connectors-desktop-and-mcp.md` §2.2):
- **Page card** (`page`): title, key idea, up to three segment headings with their sources, "Open in book" and "Correct…";
- **"What did I learn about X"** (`learned_about`): the answer page in compact form;
- **"What's next for goal G"** (`next_for_goal`): the goal's next steps with reasons, and its open questions;
- **"What changed since [date]"** (`changes_since`): the changes digest;
- **Contents** (`contents`): the book's parts and chapters;
- **"This chat draws on"** (`draws_on`): when the chat fetches the AI side's pack, a card names the goal and the items delivered, by page and speaker ("5 items: 3 AI-taught, 2 yours, from 4.2.4 and 4.1.2"). This is the context receipt made visible [07 F9];
- **Confirm card** for a chat correction or a reported goal, from `northstar_note` (§9.2).

**Rules for every slice:**
- at most about 400 words or 600 tokens, labelled as Northstar data and delimited as quoted facts, never as instructions (SYNTHESIS §5 items 6 and 8);
- captured text follows the one rendering rule of [AC] §3.2: third-person restatement, with commands in inert, labelled code blocks. Slices are model-requested, not auto-pushed, so spans flagged as possible injection may be quoted in them, under that rule. An unsolicited re-encounter card (below) is not model-requested, so it holds flagged spans back;
- every sentence in a slice has a 100% entailment verdict on its current leaf versions (§8.6);
- scope and sensitivity rules apply as for AI packs (I17). Content captured from one vendor goes to another vendor only if its scope allows cross-vendor use. The same rule governs the block writer and the audit, not only slices (§8.15);
- every delivery is recorded as a context receipt, for the echo guard (§5.9).

| Product | Channel | How the slice appears | Product facts |
|---|---|---|---|
| **Claude Desktop chat** | Local stdio MCP server (`.mcpb` or `claude_desktop_config.json`); no public endpoint | An MCP App card inline; fullscreen for the book. "Open in book" uses `ui/open-link` | Claude asks to display an app: "Click **Allow**, or **Always allow** … and the MCP App renders inline in the conversation" (getting-started, checked 2026-10-08). `ui/open-link`: "Host SHOULD open the URL in the user's default browser" (MCP Apps spec, checked 2026-10-08). Whether it opens a loopback address such as `northstar.localhost`, and whether app-only tools are honoured, is (Unv), spike S-R1. A card appears only after a model tool call: [10] F2 reports that each tool call that renders an app mounts a new widget instance (https://claude.com/docs/connectors/building/mcp-apps/instance-supersession, checked 2026-10-07 by [10]; vendor, indirect; that no other path shows a card is (Unv), S-R1). No conversation ID reaches the server (§5.8) |
| **Claude Code** (terminal, IDE, Desktop Code tab) | MCP tools and prompts from the same server; a plugin skill | A Markdown slice as the tool result, sources as footnotes, the Reader link. Optional status-line segment "Northstar · 4.2.3 Event sourcing" as a clickable link | MCP output: a warning above 10,000 tokens; default limit 25,000 (code.claude.com/docs/en/mcp, checked 2026-10-08). MCP prompts appear as slash commands and status-line OSC 8 links work in some terminals (checked 2026-10-08 by attempt C; not re-checked). MCP App rendering in the Desktop Code tab is (Unv), spike S-R3 |
| **ChatGPT Desktop chat** | The Northstar plugin: local MCP if spike CS2 passes; otherwise remote MCP through a relay (SPINE §7.3; connector design CR4; §8.15) | A widget card where the client renders one; otherwise the same Markdown slice | "Plugins work in Chat and Work across ChatGPT on the web, desktop, and mobile"; invoked by `@` or chosen by ChatGPT for the task (learn.chatgpt.com/docs/plugins, checked 2026-10-08). Tool calls carry `_meta["openai/session"]` (Apps SDK reference, checked 2026-10-08). Widget rendering and app-only tools in desktop Chat mode, and plan eligibility, are (Unv), spike S-R2 and connector design CS1 |
| **Codex** (CLI, IDE, Codex threads in the ChatGPT desktop app) | Local MCP server in `~/.codex/config.toml`; a skill | A Markdown slice with the Reader link | "The ChatGPT desktop app, Codex CLI, and IDE extension share this configuration" (learn.chatgpt.com/docs/extend/mcp, checked 2026-10-08). Link rendering in terminals is (Unv), spike S-R4 |

**Re-encounters come only from relevance.** When the AI side's composer selects a concept that has a page, for a chat in normal work (SYNTHESIS §3.3–§3.4), the connector may show its page card where a user-visible channel exists, with a line such as "In your book: 4.2.3 Event sourcing (first explained by Claude, 12 Sep)". At most one unsolicited card per chat; the same card is never repeated in a chat. It is a card, never a question. There is no elapsed-time schedule. Which channels can show an unsolicited card is (Unv) on several products, so this lever will be uneven (RISK H14). For evaluation only, cards are randomised on or off per concept (§13 E).

**Build order for the human side** (a HOW decision inside this component; the order of connectors overall belongs to the system design): (1) the compiler and the Reader, on the golden book, needing no connector; (2) `northstar_book` and `northstar_book_data`, on the one tool contract for all four connectors (`connectors-desktop-and-mcp.md` §2; local transports, plus a relay for ChatGPT Desktop chat only if CS2 fails, SPINE §7.3, SD-9); (3) Claude Code and Codex text slices, which also give the book its best verbatim data through hooks; (4) Claude Desktop cards and the confirm card, after S-R1; (5) ChatGPT Desktop cards, after S-R2.

### 10.9 Accessibility

- Every glyph has a word beside it; colour is never the only cue.
- WCAG AA contrast; light and dark themes. Inside Claude, cards use the host's style variables.
- Text resizes without breaking the margin rail. The main reading column works without JavaScript; the drawer and corrections need it.

---

## 11. Non-goals

- **No quiz.** No question is put to the reader to test them. **No retrieval aid is built** (no cover mode, no recall fold, no "explain it in your own words" prompt; ARCH R16, GOAL §2). Every evaluation passes with no aid.
- **No mastery score and no estimate of what the user knows,** visible or hidden. No levels, badges, percentages, progress bars, fractions or counts of what was explained, used or remains. No claim about the reader's state: no "you have learned", "covered", "known" or "mastered" (D14). The user's own query phrasing ("What have I learned about …") and GOAL's term "what has been learned" are allowed. No knowledge-state labels such as "confused" or "I already know this" (Q5, closed by ARCH R16).
- **No inferred familiarity, and no change to density or content from engagement.** Nothing estimates how well the user knows an idea. No page's prose, density or examples change because of how much the user has engaged with it, and reading order within a chapter stays the prerequisite order (§4.5). The reference view is a reader toggle.
- **Reading signals are used for navigation only, in these four places and no others:**

  | Use | Signal | Why it estimates no knowledge |
  |---|---|---|
  | Landmark weight (§7.2) | Page opens (a per-page open counter), slice references | It keeps an often-opened page where the reader looks for it. It changes where a page lives only at an edition, never what the page says |
  | Refutation fold (§7.6) | Three opens after a change, or 30 days | It marks a change notice as seen, as a mail client marks a message read. The block stays in place, one click away |
  | Dormant fold (§7.4) | No opens, together with no new leaves and no goal link for 120 days | It folds a contents entry. The chapter keeps its place and text |
  | "Since you last opened" and change bars (§7.7) | Last printing seen per page | It records what was displayed, never what was understood |

  Each records only that something was shown. None changes a page's prose, density or examples, and none is shown as a state of the reader.
- **No schedule.** No resurfacing based on elapsed time, no spaced-repetition timer, no reminders, no notifications asking the user to read.
- **No required routine.** No inbox, review queue, digest to clear, required correction or required reading. Held editions, tentative placements and frozen block types resolve automatically. Nothing degrades if the book is never opened (T-RITUAL).
- **No user-maintained structure:** no filing, tagging or linking by the user.
- **No editor and no second writable copy.** Corrections are typed events. The export is one-way.
- **No invented teaching:** nothing explains a concept no source explained (pending Q2, asked as ARCH DQ-7).
- **No model prose built from other prose,** none above part level, and none about change, disagreement or the user's past. Chapter and part big pictures are compiled from leaves (§4.5, §8.3).
- **No narrative profile of the user** ("you are the kind of person who…") [07 F7].
- **No global graph view by default** [12 F15].
- **No generation at read time** for pages, answer pages or slices.

---

## 12. What the core must hold

### 12.1 Records the book needs from the shared core

| Record | Fields the book needs | Used for | Status in SYNTHESIS |
|---|---|---|---|
| **Item** (Concept, Statement, Passage, Agenda) | Stable ID; role; kind tags (definition, explanation, example, comparison, procedure, claim, insight, decision, belief, question, goal, **suggestion**, which J3 splits into `learning_suggestion` and `offer`, §6.1); for model-reported explanations, the reported `body` (≤ 1,500 characters, §5.8); text; **gist verified against its span**; qualifiers; concept links; **one primary concept**; best rank and rank reason; version; certainty; span size (for the substantive-teaching flag, computed in C08 `concept_facts`, §4.7) | Every block; block assignment; promotion; AI-suggested next steps | §3.1; primary concept and `suggestion` tag **new**; passage kind tags must be guaranteed by J3 |
| **Attribution** | Speaker (I3); **speaker fidelity** (by construction, as reported by the chat model, reconciled); `agent_id`; span; modality; verbatim hedges; lineage origin, including `northstar_echo` | Voices, chips, user-voice slots (§5.8), V4, V7, B15 | AD6; echo tag and speaker fidelity **new** |
| **Agent registry** | `agent_id`, display name, vendor, product, surface, model | Generic speaker identity (§5.2) | **New** |
| **Stance** | Holder, attitude, evidence span, belief time | "Your own words", refutation blocks, "you disputed" chips | §3.1; I4 |
| **Verification** | Checkability, status, verifier model, independence flag, evidence, checked date, re-check date | Chips, rank, "Still open" | §3.1 |
| **Span and source** | Source type and ID; locator; quote, prefix, suffix; **capture fidelity**; branch path; model; browsing flag; conversation title and deep-link template where known | Drawer, quotes (V5), fidelity labels | §3.1; title and link template **new** |
| **Episode** | Product, surface, model, start and end time, project or repository; **identity state** (identified, session only, not identified); a generic `connector_session_key {connector_id, key}` (each connector says what its key is, §5.8); join events | "In which conversation" (§5.8), Casebook, sources register, timeline | Identity state and session key **new** (connector designs mint the keys) |
| **Relation** | Type, one of SPINE §5.2's 18 names (explains, defines, example_of, applied_in, part_of, broader, prerequisite_of, compares, supports, rebuts, undercuts, refines, answers, advances_goal, supersedes, contradicts, contests, same_as); confidence; `direction_checked`; status; creator | Where this fits, examples, frontier, pictures, clustering | [12 Model A, C]; names as SPINE §5.2 |
| **Supersession** | Old item, new item, reason, evidence, **causal-alternative leaf ref** | Refutation blocks (§7.6) | §3.1; causal-alternative ref **new** |
| **Tension** | Sides, resolution state, spawned question | "Still open", contested register | §3.1, AD19 |
| **Goal and question status** | Explicit, **reported** (from model-reported user text, not yet confirmed) or inferred; confirmation event and its origin (verbatim match, `reader_click`, `app_click`); active, paused, done, expired; open, answered, dormant; **who raised a question** (user or agent); targets; answering items; evidence spans | Part 0, frontier, anchors | [12 Model C]; reported state, confirmation and raised-by **new** |
| **Engagement events** | Concept, kind (explained-to, asked-about, used, restated), span, time | Dated, quoted entries in "Who taught you this" and the history tab; the frontier's `explained(c)` (§6.3) is computed from leaves, not from these. Never shown as a state, label or summary (Q5) | §3.2 |
| **Anomaly marks** | Item, page, kind | Split candidates (§7.9) | [01 idea 8] |
| **Correction** | Kind (including `misstated`, `reject_content` and goal confirmation), target, payload, holder `user`, origin (`reader_click`, `app_click`, `chat_verbatim`, `chat_verbatim_reconciled`, defined generically in §9.2), **proposed or applied**, active or lifted, barred-text hash | §9, I20, I21 | §3.2; `misstated`, goal confirmation and proposal state **new** |
| **Context receipt** | Session, product, items and slices delivered, text hashes, time | "This chat draws on" card; echo guard | §3.4 |
| **Scope and sensitivity** | On every item, span and page; a sensitive or distressing tag from J1 hygiene | Slices, exports, cross-vendor rules, example selection (D7) | I17; distress tag **new** |
| **Excision tombstones** | Target and scope | Tombstones; zero-hit grep | §5 item 9 |
| **Recorded model outputs** | Job, model, prompt hash, input fingerprint, raw output | Replay, audit | [13 §A.4] |

**Queries the book needs:** best-rank projection; as of any date; items changed since a watermark; the dirty set for a printing; relations by type over a subgraph; context receipts by session.

### 12.2 What the human architecture owns

Derived, append-only, never canonical knowledge:

```yaml
BookLedger:   append-only outline events: move, split, merge, rename, promote, demote,
              graduate, retire, join-shown; each with before, after, job, edition, objective gain
Edition:      {id, at, outline_snapshot, j8_inputs: {graph_hash, previous_outline, corrections,
              landmark_weights, embedding_cache_version, seed, library_version}, notes, metrics}
BlockVersion: {page_id, block, version, printing, edition,
              paragraphs: [{plan_id, memo_key, sentences: [{kind, text, cites[], role, sn_id}]}],
              model, prompt_hash, validator_report, entailment_verdicts[], fallback: bool, recorded_at}
ReaderState:  {reader_id, page_id, last_printing_seen, open_count, view_toggles}
              # in reader.db: local, private, excision-covered
```

Reader state is kept apart from the knowledge ledger, never enters AI packs, can be switched off, and is covered by excision. `open_count` is the per-page open counter behind landmark weight (§7.2). Only the derived landmark-weight vector reaches the human compiler (C16, through `landmark_signals`, SPINE §6.3) and the book ledger.

### 12.3 Interfaces

| Interface | Direction | Notes |
|---|---|---|
| Read API (HTTP JSON) | Core to Reader | Contents, page render, drawer, search, goal pages, changes, history, as-of |
| Correction API (HTTP) | Reader to core | Host-only session cookie, CSRF, same-origin; at most 10 corrections a minute, step-up for bulk moves and hides (§10.3); returns the event ID for undo |
| `landmark_signals` | Reader (C17) to human compiler (C16) | The derived per-page landmark-weight vector only, never reading events (SPINE §6.3) |
| MCP tools, model-visible | Model to core | One tool contract for every connector (`connectors-desktop-and-mcp.md` §1.2, §2.2). The book uses `northstar_book(view: page \| learned_about \| next_for_goal \| changes_since \| contents \| draws_on)` (read-only) and `northstar_note(kind: correction)` (applied at once only on a `chat_verbatim` match that meets §9.2's four conditions, otherwise a proposal). `northstar_context`, `northstar_fetch` and `northstar_restart` serve the AI side |
| MCP tools, app-only | Card to core | `northstar_widget_action(action: apply_correction \| confirm_goal \| reject_goal)`, bound to the user's click by a single-use `action_nonce` (origin `app_click`, `connectors-desktop-and-mcp.md` §3.5); `northstar_book_data` |
| MCP prompts | User to core | As `connectors-desktop-and-mcp.md` §2.8: `northstar_learned_about(topic)` ("What have I learned about …") and `northstar_next_for_goal(goal?)` ("What should I learn next for …") return those Book slices. `northstar_continue` belongs to the AI side |
| Export job | Core to disk | Nightly, one-way, user-chosen folder; the Reader's renderer rules apply (§10.1) |

The book shares item IDs with the AI side's packs. A chat can mention a page or item ID, and the reader can click it into the book.

---

## 13. Evaluation

### 13.1 Principles and the golden book

- **No required user sessions, and no test of the user.** Every gate is automatic. User input is optional: one-off consent to use real data (SYNTHESIS §7), and the optional one-off acceptance read (§13.5). Nothing measures what the user remembers, even in aggregate, and nothing is stored per concept about the user's recall.
- **The golden book:** synthetic personas generated from a hidden world ledger by a model family other than the system's (SYNTHESIS §7.4). Their chats span all four first connectors, with both speakers, including model-reported desktop capture and session-only conversations. **Part of each persona's knowledge comes from a known public syllabus**, so chapter structure and prerequisite order can be scored against a real textbook's. At least one non-chat document is included. The personas also include:
  - **one persona with zero explicit goals**, whose hidden ledger still holds the topics they go on to pursue, to test what to learn without goals;
  - goals stated **only in a desktop chat**, to test reported goals;
  - **planted speaker swaps** in model-reported desktop capture (user text reported as the AI's, and the reverse), to test speaker fidelity;
  - **single-conversation AI explanations** of concepts that appear nowhere else, to test promotion parity;
  - **AI-raised open questions and AI-suggested next steps**, to test what-to-learn parity;
  - **reflexive AI offers to do work** ("I can write the tests next"), to test that offers stay out of what to learn (§6.1);
  - **a desktop-only persona**, whose chats are all in Claude Desktop chat and ChatGPT Desktop chat at L0, for groups C and D and the BK6 chip-density arm;
  - **an AI-tools learner persona**, who learns mostly by asking AIs to explain things, so most of the Book is AI-taught;
  - **a developer persona** whose questions are often bound to one repository, to calibrate the project-bound rule (§4.7);
  - **single-conversation AI explanations captured both at hook tier and in a desktop chat**, with and without a modelled closing call, for the single-episode check (§13.2 B);
  - **a Q6-on case** (ARCH DQ-10 answered yes) with click-confirmed goals (§13.2 G).
- **Growth checkpoints.** Groups C, D, F and T-NAV run at simulated days 1, 7, 30 and 60, so a Book that reads well at day 60 but is thin in its first weeks shows up (H22).
- **Separate families** for data, writer and judges; judges must accept fewer than 10% of wrong but on-topic answers (SYNTHESIS §7).
- **Bars are pre-registered,** recalibrated once after a pilot, then frozen.
- **Proxies are labelled as proxies.**

### 13.2 Checks and bars

| Group | Check | Measure and starting bar |
|---|---|---|
| **A. Truth and attribution** (hard gates) | Provenance completeness | 100% of sentences resolve to a leaf and a span |
| | Citation faithfulness | 100% of new model sentences entailment-checked; audited entailment ≥ 97%; hedges and rare details kept after 5 regenerations ≥ 95% (SYNTHESIS §7.3) |
| | Model-written attribution | 0 (V4) |
| | Chip accuracy; false endorsement | ≥ 98%; ≤ 5% |
| | Autobiography violations (user's past not in quote form) | 0 |
| | Quotes from non-verbatim spans | 0 |
| | Conversation identity | 0 items show a conversation title or link they are not joined to; "not identified" < 1% |
| | Speaker fidelity on the desktop chats | On golden desktop chats with planted speaker swaps: 100% of model-reported items carry the speaker-fidelity chip; 0 model-reported items rendered in a user-voice slot or "In their words"; 0 model-reported user items counted as a held stance; the rate of speaker errors among model-reported items is measured against reconciled text and reported per connector. It is a measurement that sizes H8, not a bar |
| **B. AI-said first-class** | What-has-been-learned coverage | Golden items, user-stated and AI-taught, reachable with sources ≥ 95% each; AI-taught within 5 points of user-stated |
| | Explained coverage | Share of golden taught items that appear in unfolded prose or "In their words", not only in folded blocks or short notes: reported, with AI-taught within 5 points of user-said |
| | Single-episode check (desktop against hook) | The same single-episode AI explanations, captured in a desktop chat and at hook tier: promotion within 5 points, and content parity (simulated-reader inference on their pages within 10 points). The golden L0 renderer drops final-reply points unless a closing call is modelled, so the final-reply loss (§5.8) is measured, not hidden |
| | Featured-slot parity | AI-said share in key-idea citations, explanation citations, "In their words", chapter and part big pictures, first screen, what-to-learn items and slices within 5 points of the golden share for the same pages. The live-reference sentinel (B11) must agree with the golden comparison on the golden book, so it can be trusted on real data |
| | Promotion parity | Share of promoted concepts mainly supported by AI-said leaves within 5 points of the eligible and golden shares, overall and among single-episode concepts |
| | What-to-learn parity | AI-said share among what-to-learn items (open questions, suggested next steps, stub mention lines) within 5 points of the golden share |
| | Warning-chip parity | AI-said and user-said shares of warning-chipped sentences within 5 points of their shares of unchecked checkable claims |
| | Echo | Echo spans, same-session and cross-session (§5.9), counted as support or toward promotion: 0. Share of AI-said spans discounted as echoes, **by vendor family**: reported, here and by the SD-38 vendor-parity sentinel. It is a measurement, not a bar |
| **C. Reads like a textbook** (automatic) | Anatomy | Every concept page has key idea, where this fits, explanation and sources; examples wherever linked episodes or AI examples exist |
| | Sizes; heading fidelity | Within §4.2; 100% of headings entailed |
| | Organiser coverage | "Where this fits" before the explanation on 100% of pages; each chapter opener lists 100% of its pages |
| | Defined before used | ≥ 90% of terms on a page defined earlier in reading order or linked |
| | Prerequisite violations in reading order | 0 |
| | Self-reference rate | Share of pages with an example from the user's own work, where such episodes exist (reported) |
| | Structure against the syllabus | Adjusted mutual information ≥ 0.6 and above a flat topic-clustering baseline; section order Kendall tau above baseline |
| | Near-duplicate sentences | ≤ 2% |
| | Rubric judge | Calibrated on real textbook sections, wiki pages and chat logs; "reads more like a textbook chapter" in ≥ 70% of pairs against BK1 and BK2, at equal or better faithfulness |
| | Textbook style floor | Real textbook sections on the syllabus topics, as a style floor only: the Book preferred in ≥ 35% of pairs (pre-registered) |
| | Structure bars | A few pre-registered bars, set after the pilot and then frozen (§13.1): median explanation words per page; segment count; B-sentence share; chip glyphs per 100 words; block redundancy (V15); share of non-empty organisers ("Where this fits", big pictures) |
| | Fallback share | ≤ 5% of explanation blocks (alert at 2%) |
| **D. Helps understanding** (simulated readers) | Comprehension A/B | A reader model from a third family, given one rendering at equal length, answers held-out questions written from the hidden world's **gold leaves** (what was taught), not from extracted leaves, so a page that drops what was taught loses points: **textbase** (stated facts) and **inference and application** (combine two items; apply the idea to a new case). Renderings: the book page; BK1; BK2; BK0 excerpts. **Bars:** the book beats BK1 by ≥ 10 points on inference with no loss on textbase, and matches BK2 on inference with higher faithfulness. **BK0 bar:** the book page is at least as good as its cited source excerpts on inference questions, at equal or shorter reading length |
| | Novice reader | The same with a smaller reader model, standing in for low prior knowledge; tests the learning-view default |
| | Attribution and change questions | SR-1 "what have I learned about X, and from whom?"; SR-2 "what did a given AI teach me, and when?"; SR-3 "what did I believe, what replaced it, and why?"; SR-5 "where do my sources disagree?"; SR-6 re-orientation after 30 simulated days. **Bars:** book beats BK0 and BK1 by ≥ 15 points; SR-2 within 10 points of user-said questions; on SR-3 and SR-6 refutation blocks beat plain replacement (BK5) on stating the current belief **and** its reason |
| | Chip density | Rail-only default against all chips (BK6): no loss on inference questions, attribution accuracy kept |
| | Desktop-only cell | Groups C and D and the BK6 arm also run on the desktop-only persona (§13.1), with block notes (§5.4), and are reported apart |
| **E. Helps remembering** (passive proxies, labelled) | Re-ask rate | Share of user turns asking an AI to re-explain something the book has held for ≥ 7 days, before and after a page exists, and between concepts randomised to re-encounter cards on or off. Deeper follow-ups are classified apart and not counted. **Bar:** ≥ 20% fewer re-asks with cards on. **Reported as a combined findability-and-retention proxy:** fewer re-asks can mean the user looked it up, not that they remembered it |
| | Navigation (T-NAV) | An agent drives the real Reader through its accessibility tree with contents and index only (no search): reaches the answering page in ≤ 3 hops in ≥ 85% of cases, and beats searching raw transcripts |
| **F. Stability and evolution** | T-STAB | No wording change without a leaf change or a recorded quality release (§8.9): 0 text changes otherwise, **including across a model or prompt migration**; pages moved per edition ≤ 5%; title changes ≤ 3 per edition; A→B→A within 4 editions 0; broken links 0; landmark survival (most-opened pages keep chapter, title and number over four editions) ≥ 95%; number survival of chapters and parts reported |
| | Change log precision | Every "what changed" entry maps to a ledger event; every page-changing event appears |
| | T-NEW | ≥ 95% of golden changes to held items, ≥ 90% overall, appear in "Since you last opened" |
| | Replay | Book ledger replay rebuilds every edition and printing hash-identical |
| **G. What-to-learn validity** | Prerequisites | Precision ≥ 0.8 and direction on edges used for ordering, against the syllabus |
| | Questions and gaps | Open-question precision, for user-asked and AI-raised questions separately; dangling-term precision |
| | Frontier predictive validity | Share of frontier items the user later engages with in normal chats (passive), above random and popularity baselines; reported separately for goal frontiers and the goal-independent frontier |
| | What to learn without goals | For the zero-goal persona: the first screen's what-to-learn block is non-empty; "Ahead" is non-empty on every chapter that has a mentioned, unexplained linked concept; "Next from here" likewise per page; every item shows a reason; goal-independent frontier precision against the persona's hidden later topics ≥ 0.6 (starting bar) and above the popularity baseline; 0 invented goals |
| | Offer leakage | AI offers to do work among what-to-learn items (mis-tagged as learning suggestions): ≤ 5% (starting bar); 0 offers on any frontier |
| | Reported goals | Goals stated only in golden desktop chats appear as reported goals within one printing ≥ 95%; 0 shown as confirmed without a verbatim match or a click; 0 reach an AI pack as a goal, constraint or instruction before a verbatim match, or before a click plus a yes to Q6 (I5) |
| | Q6-on case (ARCH DQ-10 yes) | Click-confirmed goals: 100% confirmed only by a widget or Reader click, never on the reporting turn; 100% render "confirmed by your click; wording as reported by the chat model"; they reach AI packs as goals with that label |
| **H. Maintainer** | Correction survival (T-CORR) | 100% of active corrections in force after 10 rebuilds and editions, per page (hard gate, I21) |
| | T-RITUAL | 30 simulated days with zero reads and zero corrections: the book stays current and every sentinel stays green |
| | T-FRESH | ≥ 95% of new leaves in "Just in" within 3 hours and in a printing within 30 hours |
| | T-SLICE | Slices match the Reader word for word, with the same chips; "this chat draws on" matches the context receipt: 100% |
| | Fault injection | Degrade one J7 worker at a time (weak model, shuffled citations, padding, missing job card, a prompt bug that inserts speaker names). Structural errors blocked: 100%. Planted unsupported sentences caught by entailment: measured. Error budget trips within one daily cycle. Rollback restores structure by a compensating edition with redirects, and re-rendered pages contain no text from the rolled-back job (§8.14) |
| | Security | A script planted in a captured AI reply never executes in the Reader; a forged correction request without the token is rejected; injection canaries never persist; the Markdown mirror and EPUB carry no raw HTML, remote images or `javascript:` links; a planted chat correction that fails any §9.2 condition stays a proposal |
| | Excision | Grep over every derived store: 0 hits |
| | Scope egress (§8.15) | Planted items whose scope forbids a vendor never appear in that vendor's writer, audit or slice inputs (recorded model inputs and context receipts): 0 |
| | Cost | Monthly book spend at golden-book volume within the §8.10 estimate ×2 |

### 13.3 Baselines and ablations

| ID | What it is |
|---|---|
| BK0 | Raw transcripts and excerpts, searchable |
| BK1 | A chronological feed of leaf items with chips |
| BK2 | An uncited wiki the model rewrites in place on each ingest (Karpathy-style [12 F7]) |
| BK3 | A RAPTOR- or Clio-style topic tree with summaries of summaries at upper levels [12 F4, F16] |
| BK4 | The book without paragraph memoization and editions (stability ablation) |
| BK5 | The book without refutation blocks (plain replacement) |
| BK6 | The book with all chips shown inline |
| BK7 | The book with the reference view as default |
| BK8 | The book with a verbatim body: single-source pages show their leaves verbatim instead of model prose. **An ablation arm only**, never a page form: it is close to the labelled degraded mode (§8.7), and GOAL §3.2 asks the AI to explain |

Ablation applies to HOW layers only. A layer that moves no metric may be cut. A component GOAL requires (the what-to-learn side, AI-said passages in the book, source traceability, the human view itself) can be redesigned but never cut (SYNTHESIS §7).

### 13.4 What cannot be measured without the user

Whether reading the book improves the user's own unaided recall cannot be measured without asking the user to recall something, which this design does not do. It measures labelled proxies and says so. The goal is not lowered: "helps understand and remember" stays the target, and the gap is RISK H1 (Q4, settled as that risk by ARCH R16).

Whether the book reads like a textbook **to the user**, and is easy for them to understand, is different: the user can judge that by reading, with no recall test. §13.5 offers that check, once and optionally.

### 13.5 Optional acceptance read (one-off)

The synthetic checks above can all pass while the book still does not read like a textbook to its one real reader. That is the drift pattern that sank the first design (GOAL §7). So the prototype offers one optional check by the user, on real data.

- **When:** once, when the prototype has run on real data for long enough to fill a few chapters. It is offered in the Reader footer and in the evaluation report. It is never repeated on a schedule, and nothing reminds the user.
- **What:** the user reads a small sample of real pages (starting value: 5 concept pages and 1 chapter opener, chosen by code to cover AI-taught and self-stated material and at least one desktop-chat source). For each, they answer two questions: "Does this read like a textbook?" and "Is it easy to understand?" (yes, partly, no, with an optional note).
- **What it is not:** no recall test, no quiz, nothing stored per concept, nothing about how well the user knows anything. The answers are stored as one evaluation record, not in the knowledge ledger, and never enter AI packs.
- **How it is used:** a "no" or "partly" is treated like a failed rubric-judge case: the page is a labelled finding for the design, and the synthetic judges are re-checked against it (S-R8). It never changes the user's book by itself.
- **Gates do not depend on it.** Every gate in §13.2 is passable without it, and skipping it is never recorded as a failure. If it is skipped, §17 keeps "reads like a textbook" and "helps understand" at **At risk** on simulated evidence only (H3, H7).

---

## 14. Spikes for unverified facts

| Spike | Question | Decides |
|---|---|---|
| S-R1 | Claude Desktop with a local stdio server: do MCP App cards render inline and fullscreen; are app-only tools honoured; does `ui/open-link` open a loopback address (`northstar.localhost`, 127.0.0.1)? | Claude Desktop cards and the confirm card (§9.2, §10.8) |
| S-R2 | ChatGPT Desktop **Chat** mode: does a plugin widget render; are app-only tools honoured; which endpoint and plan are needed? | ChatGPT Desktop cards and confirm card |
| S-R3 | Claude Code: status-line links in the user's terminal; MCP App rendering in the Desktop Code tab | Claude Code glimpses |
| S-R4 | Codex: link rendering; a way to show a slice to the user without adding it to model context | Codex glimpses |
| S-R5 | Deep-link formats into Claude Desktop, ChatGPT Desktop and Codex conversations | "Open in product" (§5.5) |
| S-R6 | J7 on the golden book: validator reject rate, entailment pass rate, tokens per call, fallback rate, cost | §8 bars and §8.10 |
| A12 / CS6, extended | Copy fidelity of model-reported explanation bodies and reply lengths, measured against export text (the existing A12 and CS6 copy-fidelity checks, extended) | Whether the optional reported reply length ([CX] §2.3) is used in the substantive-teaching flag (§4.7 (c)). This is decided here, not by S-R6 |
| S-R7 | Conversation identity: does ChatGPT Desktop Chat send `_meta["openai/session"]` and is it stable across app restarts; how often does the model copy the Claude Desktop session handle correctly; join precision against observer or export text | §5.8 |
| S-R8 | Calibrate the rubric judge and the simulated readers on builder-labelled sections (builder spot-checks during evaluation only, SYNTHESIS §7) | §13 C, D |
| S-R9 | Echo detection precision and recall at the 0.6 containment threshold, within a session and across same-family sessions (with `ai-continuity.md` SP-AC-6) | §5.9 |
| S10 | The local different-family verifier's calibration (SYNTHESIS) | §8.6, §8.13 |
| S-R10 | A local open-weight block writer on the golden book: canary pass rate per block type, fallback rate, speed on this Mac | Blocks held back by cross-vendor scope; the whole writer if Q7 is answered no (§8.15) |
| SP-PL-16 | A separate browser cookie jar for the Reader ([PL]) | Whether the Reader gets its own cookie jar (§10.3) |

---

## 15. Questions for the user

Only questions that touch the WHAT or accept a risk. Each has a working assumption, **pending your answer**. Silence is never taken as an answer. Since the review of 2026-10-08, the user answers these in ARCHITECTURE §14 (or SPINE §11.2), not here. The Status column says where each one went; the text below is kept as the record of what was asked.

| # | Question | Working assumption (pending your answer) | Status |
|---|---|---|---|
| **Q1** | GOAL says the human side "is not a quiz". Retrieval is the strongest memory lever in the evidence (§3, E11). Do you want **no retrieval aid at all**, or one of these optional aids, off by default, scoring nothing and recording nothing: (a) **cover mode**, which folds each explanation segment under its heading so you can try to recall it first; (b) an **"explain it in your own words"** margin prompt? | No aid is built. All evaluation runs without one. If you choose one, it is added as a reader toggle with no other effect | Settled or closed (ARCH R16); user override only |
| **Q2** | Every sentence must trace to who said it and in which conversation. So the book will **not** write explanations of its own when your sources leave a gap. It shows the gap under "what to learn", with an optional "Ask about this" prompt. Is that right? Or do you want (a) short Northstar-written glosses, clearly labelled as not from your conversations, or (b) Northstar asking an AI to explain the gap and filing that as a new, attributed conversation? | No glosses and no automatic asking | Asked as ARCH DQ-7 |
| **Q3** | Should **project-specific knowledge** (for example how one repository is set up, from Claude Code or Codex sessions) be in the book? This design puts it in a **Casebook** part and uses it for examples. And should sessions on **employer repositories**, or in folders declared neither personal nor employer, appear in your personal book? (One question in SPINE §11.2, merged with `connectors-claude-code-and-codex.md` UQ-HK-1) | Casebook yes, for personal projects. **A non-allowlisted account is skipped in both directions**: nothing is captured and nothing is injected (SPINE UQ-3). **On an allowlisted personal account**, employer and unclassified repositories are **still captured**, into `work:<org>` or `unclassified:<repo_hash>` scope under I17 (`platform-security-privacy.md` §6.6; unclassified is treated as work). Those sessions get no personal-scope content injected, nothing leaves beyond "no new exposure" (`platform-security-privacy.md` §6.3; §8.15), and their items stay out of the personal book and AI packs. A later "yes" applies retroactively, so nothing learned at work on a personal account is lost while this question is open | Asked as SPINE UQ-13 |
| **Q4** | The evidence says reading, even well-designed reading, helps memory only modestly (§3.2). This design uses the system-side levers it can: self-reference examples from your own work (D7), refutation blocks (D10), source and time cues (D12, D13), stable places (D15), and in-chat re-encounter cards when a later chat uses an idea (D11). It measures remembering only through passive proxies. More system-side levers exist, each with a cost: the optional aids in Q1; more re-encounter cards per chat; or cards on more surfaces once spikes S-R1 to S-R4 pass. Do you accept the current levers, given that "remember" may be helped only modestly? Or do you want one of the other system-side levers explored? | **No acceptance assumed.** "Remember" stays a target with status At risk (H1), and proxy results are never reported as meeting it | Settled or closed (ARCH R16); user override only. Kept as risk H1 |
| **Q5** | Should the book show any **engagement summary** for an idea, such as "explained to you, you asked about it, you used it", or a one-click **"I already know this"** on next steps? Either could read like a measure of what you know. | Neither. Engagement appears only as dated, quoted records in "Who taught you this". "Hide from next steps" is offered instead, and it says nothing about what you know | Settled or closed (ARCH R16); user override only |
| **Q6** | On Claude Desktop chat and ChatGPT Desktop chat, a goal you state may be known only from the chat model's report of your message. Invariant I5 says only text you typed can create goals. This design shows such a goal as "reported, not yet confirmed" and confirms it automatically when your verbatim text arrives. It also offers an optional one-click "Yes, that's my goal" (§5.8). May that click confirm a reported goal, so it counts as your goal and can reach AI packs as one? A yes would also relax the rule in both desktop connector designs, which today accept only verbatim text | Until you answer: the click confirms it **in the book only** (it moves to goals, and its frontier stops being provisional), with your origin bound at write time (I20), as a correction click does. It does **not** reach AI packs as a goal until a verbatim match or your yes to this question, so the connector designs' rule and I5 hold meanwhile. The wording stays labelled "as reported by the chat model" until verbatim text matches. If you say no, only a verbatim match confirms, and the click is removed | Asked as ARCH DQ-10 (expanded) |
| **Q7** | GOAL says "local now, cloud later". The book's storage and services run on your Mac, but its writer and audit send captured content, including ChatGPT and Codex content, to Anthropic's cloud API each night, and ChatGPT Desktop chat needs a relay if spike CS2 fails (§8.15). Does "local now" allow **cloud model API calls** on captured content? | For design only: yes, under scope rules, matching the system design's default model profile (SPINE §8.4). Items whose scope forbids a vendor never reach it, `private` items stay on local models, and Northstar stores nothing off the Mac (the API provider's own retention terms apply and are not checked here, Unv). **No real captured content is sent to a cloud API until you answer**, at the approval gate. If you say no, every model step moves to local models, and pages render as cited excerpts until a local writer passes its canary (S-R10) | Asked as ARCH DQ-3(a) |

---

## 16. Risks

| # | Risk | Threatens | Mitigation |
|---|---|---|---|
| **H1** | **The memory ceiling of reading.** Rereading is low utility; spaced rereading effects are small; retrieval and generation need the reader to act; an AI-built structure helps less than a self-built one (SYNTHESIS RISK 17) | GOAL §3.2 "remembers" | Self-reference (D7), refutation blocks (D10), source and time cues (D12, D13), relevance-driven re-encounters (D11); passive proxies (§13 E). Q1 and Q4 are settled by ARCH R16: no retrieval aid, and this stays a risk needing no answer. More system-side levers (more cards per chat; cards on more surfaces once S-R1 to S-R4 pass) are tried against the §13 E proxies |
| **H2** | **A polished book makes AI errors look authoritative.** Fluency raises felt understanding; textbook typography adds authority (SYNTHESIS RISK 7) | §4.2 with §6 "each item shows its sources" | Named narrator; verification chips; unknowns shown as prominently as knowns (D14); contradicted claims in history, not hidden |
| **H3** | **The evidence may not transfer.** Lab effects with students; several numbers secondary; effects do not add | All D-rules | Rules treated as hypotheses; §13 C and D test them; ablate HOW layers that move nothing |
| **H4** | **Provenance against coherence.** Chips can add load | D3 against D13 | Rail-only default, chips only when unusual, folded provenance blocks; BK6 arm |
| **H5** | **Landmark churn** from automatic reorganisation (SYNTHESIS RISK 15) | Navigation | Permanent IDs, frozen numbering, editions, churn budget, landmark-weighted stability cost, fold in place, user pins (I21), undo |
| **H6** | **Self-reference examples expose or upset.** Work content may be sensitive; negative episodes reverse the effect | Privacy; D7 | Scope and sensitivity tags; distressing episodes never used; "This example doesn't fit"; Q3 |
| **H7** | **Simulated readers are not people** | §13 validity; GOAL §3.2 "helps the person understand" | Used only for relative comparisons between renderings; S-R8 calibration; the optional one-off acceptance read by the user (§13.5) |
| **H8** | **Desktop chat fidelity, speaker, identity and goals.** On Claude Desktop chat and ChatGPT Desktop chat, with only the sanctioned layer: (a) **wording**: AI-said and user-said text is model-reported until reconciled; (b) **speaker**: the chat model decides what it reports as the user's words and what as its own, so the speaker itself is model-set, the failure behind 43–55% misattribution [12 F8] (SYNTHESIS AD6); (c) **identity**: conversations may stay "session only", a join may need the optional observer or an export (exports are backfill only, SYNTHESIS RISK 19), and a badly copied session handle could merge two chats (connector-claude-desktop-chat.md, CD-6); (d) **goals**: both connector designs keep model-reported goals out of long-term goals until verbatim text confirms them, so a goal stated only there reaches the book as a reported goal, not a goal; (e) **featured slots**: until reconciled, AI-said text from these chats cannot fill "In their words" or e.g. lines. If the user declines the observer (SPINE UQ-1), verbatim text arrives only through export backfill, so for long stretches these two connectors may supply **no AI worked examples** to the book; (f) **the final reply**: at L0 a chat's last reply is captured only by the closing report call (§5.8), which depends on a spike; where it fails, what the last reply taught is lost until verbatim text arrives | GOAL §3.2 "who said it" and "in which conversation"; §3.2 what to learn; §4.2 AI-said first-class; on two of four first connectors (SYNTHESIS RISK 4) | Identity states and speaker-fidelity chips on every item; quotes and user-voice slots only from verbatim or reconciled spans; reported goals with a provisional frontier and an optional one-click confirm (§5.8, Q6); the closing report call, reported explanation bodies and the code-computed substantive-teaching flag (§4.7 (c), §5.8), with the desktop-against-hook single-episode check (§13.2 B); never claim an unjoined title; per-conversation capture panel; "Wrong speaker" and "Wrong conversation" corrections; S-R7; speaker-error measurement (§13 A). The capture fix belongs to the connector designs and the observer, whose acceptance is the user's decision there (SPINE UQ-1) |
| **H9** | **The leaf-only rule leaves explanatory holes.** Some pages use terms the book never explains | "Reads like a textbook" | Dangling terms shown inline and in what to learn; "Ask about this"; Q2 |
| **H10** | **A noisy frontier** loses trust: prerequisite F1 about 0.7, reversed direction common [12 F11]. The goal-independent frontier has no goal to focus it, so it may be noisier still | What to learn | Direction check, confidence bar, reasons shown, one-click rejection, predictive-validity metric reported separately for goal and goal-independent frontiers (§13 G); redesign rather than removal |
| **H11** | **Contested items crowd pages** (SYNTHESIS RISK 22) | Readability | "Still open" shows at most 3 per page with "more"; count-and-age sentinels |
| **H12** | **Book bloat** toward a mausoleum [02 pitfall 8]. Promoting single-episode explanations (§4.7) adds pages | Navigation | Promotion gate with hysteresis and a calibrated size bar, short notes, dormant folding, size bounds |
| **H13** | **Slices send book content to vendors** | Privacy | Slices follow pack scope rules; cross-vendor only where scope allows; see also H21 |
| **H14** | **Uneven in-chat support.** Desktop widget rendering, app-only tools, `ui/open-link` to localhost and unsolicited cards are unverified on several products | Re-encounter lever; confirm cards | Markdown fallback everywhere; Reader fallback for corrections; spikes S-R1 to S-R4; results reported per product |
| **H15** | **Verifier independence and calibration.** If the local verifier fails S10, entailment is not fully independent (SYNTHESIS RISK 18). Thresholds calibrated on synthetic data understate real error (SYNTHESIS RISK 6) | GOAL §4.7 | §8.13: automatic same-vendor check flagged not independent, higher audit rate, tighter budget, then a second local family, then ARCH DQ-12; the user told; real-data error reported separately |
| **H16** | **Restated prose can distort meaning in ways entailment checks miss.** Automatic verification agrees with humans only about 72–76% of the time [12 F9] | Traceability | 100% entailment on new sentences; grounded tokens and hedges in code; daily audit; error-budget freeze; "Northstar misstated this" as a label |
| **H17** | **Local web server exposure** (other local sites, DNS rebinding, stored XSS); cloud exposure later (SYNTHESIS RISK 13) | Privacy, trust; correction integrity | §10.3 controls; security tests in CI; cloud behind sign-in |
| **H18** | **Two benefits given up on purpose.** Banning "you" in model prose gives up the conversational-style effect (d = 0.30, Ginns et al. 2013). Making the reference view a toggle gives up automatic expertise-reversal adaptation (E4) | Some reading ease | Self-reference comes from quoted examples instead; the toggle is one click; the novice-reader and BK7 arms measure the cost |
| **H19** | **Reader state records what you read** | Privacy | Local only, apart from knowledge, never in packs, switchable off, covered by excision; only a derived landmark weight enters the book ledger |
| **H20** | **Compile cost runs away** through churn or retries | Budget | Memoization, nightly batch, dirty tracking, cost sentinel |
| **H21** | **Captured content leaves the Mac.** The writer, the L4 audit and title proposals call Anthropic's API on captured content each night, including ChatGPT and Codex captures; slices go to the chat's vendor; if spike CS2 fails, ChatGPT Desktop chat needs a relay that carries conversation text in transit (SPINE §7.3; connector-chatgpt-desktop-chat.md CR4; SYNTHESIS RISK 13). If "local now" excludes cloud model calls, moving to local models leaves explanation blocks in extractive fallback until a local writer passes its canary, which degrades "reads like a textbook" | GOAL §4.6 "local now"; §3.2 "reads like a textbook" if local models fall short | §8.15: every flow listed; I17 cross-vendor scope applied to writer and audit inputs; `private` items local only; redaction first; scope-egress test (§13 H); no real content sent before Q7 is answered; S-R10 |
| **H22** | **The Book's first weeks are thin.** Early on there are few pages, chapters of one or two pages, short explanations from single leaves, and empty organisers. A first impression of a thin, unstable book could mislead about what the Book will become, or hide new material | GOAL §3.2 "reads like a textbook" in the first weeks; "organises" | The growth regime (§7.3): a bootstrap edition, daily editions for 14 days, budget exemptions and the "growing book" form; first-night promotion for strong signals (§4.7); one segment sized to its leaves (§4.2); organiser fallbacks (§4.4, §4.5); "New this week" (§10.4); growth checkpoints at simulated days 1, 7, 30 and 60 (§13.1) |

---

## 17. Goal-fidelity check

Status values: **Met by design** (a mechanism exists and a test checks it, and no listed risk admits it may fail); **At risk** (a mechanism exists, but evidence or an unverified fact may stop it working; see the risk); **Planned** (to be shown by the prototype). A row is never marked Met while a risk in §16 admits the clause may not be met (must-fix #12). Where a clause is met on some connectors and at risk on others, the row says which.

| GOAL clause | Where this design meets it | Status |
|---|---|---|
| §3.2 what has been learned, from the user and from AIs | §4.4, §5; AI-taught first-class §5.6; promotion ignores speaker and promotes single-episode explanations §4.7; short notes expand in place §4.1 | Met by design on Claude Code and Codex. **At risk** on the two desktop chats (H8): their content appears as labelled gists until reconciled, and at L0 a chat's last reply is captured only if the closing report call works (§5.8, H8 (f)); the desktop-against-hook check measures the gap (§13.2 B) |
| §3.2 what to learn: goals, gaps, open questions, next steps | §6; Part 0, forward chapters, "Ahead", "Next from here"; AI-raised questions and AI-suggested next steps §6.1; links both ways | Mechanisms met by design. **At risk** for frontier quality (H10) and **at risk on the desktop chats** (H8: goals stated there arrive as reported goals, not goals) |
| §3.2 what to learn when the user has stated no explicit goal | Goal-independent frontier, directions and reported goals §6.3; first-screen fallback §10.4; zero-goal persona check §13 G | Presence met by design (the §13 G check requires non-empty, reasoned items). **At risk** for quality (H10) |
| §3.2 what to learn from goals stated in a desktop chat | Reported goals with a provisional frontier, automatic confirmation by verbatim match, optional one-click confirm §5.8; reported-goal checks §13 G | **At risk** (H8); Q6 (ARCH DQ-10) |
| §3.2 reads like a textbook; the AI organises and explains | Cited explanatory prose with a named narrator §4.4, §5.3; anatomy from evidence §3; anchored chapters §7.2; chapter and part big pictures §4.5; §13 C, D; optional acceptance read §13.5 | **At risk**: explanatory holes from the leaf-only rule (H9, Q2); evidence may not transfer (H3); local-only writing if Q7 (ARCH DQ-3(a)) is no (H21); a thin Book in its first weeks (H22), handled by the growth regime (§7.3) and checked at simulated days 1, 7, 30 and 60. Extractive fallback bounded at 5% (§8.7) |
| §3.2 helps the person understand | §3, §4; comprehension A/B with inference questions §13 D; optional acceptance read §13.5 | **At risk** (H7): simulated-reader evidence only, unless the user takes the optional acceptance read |
| §3.2 helps the person remember | §3.1 rules D6, D7, D10–D13; re-encounters §10.8; re-ask proxy §13 E | **At risk** (H1; Q4 settled as this risk by ARCH R16). Proxy results are never reported as meeting it |
| §3.2 traceable to who said it | Code-only attribution §5.3; voices §5.2; two-click drawer §5.5; speaker-fidelity chips and user-voice slot rule §5.8; speaker-error measurement §13 A | Met by design on Claude Code and Codex. **At risk** on the two desktop chats (H8): the speaker of a model-reported item is set by the chat model until reconciled |
| §3.2 traceable to which conversation | Identity states and capture panel §5.8 | Met by design on Claude Code and Codex. **At risk** on the two desktop chats (H8) |
| §3.2 not a quiz or a mastery score | §11; no aid built (ARCH R16); no counts; no inferred familiarity §4.6; reading signals for navigation only §11 | Met by design |
| §3.2 browse and correct; routines optional | §9, §10; T-RITUAL | Met by design |
| §4.1 a system, no rituals | All maintenance is code and stateless jobs; held editions and freezes exit automatically; reported-goal confirmation and the acceptance read are optional and one-off; nothing waits on the user | Met by design |
| §4.2 AI-said knowledge first-class and attributed | §5.6; speaker-neutral chips §5.4; featured-slot parity nightly on real data (B11); promotion, what-to-learn and warning-chip parity §13 B; echo guard §5.9 | Met by design on Claude Code and Codex. **At risk** on the two desktop chats (H8): their AI-said text cannot fill "In their words" or e.g. lines until reconciled, and may supply none for long stretches if the observer is declined |
| §4.3 the AI manages it; correction optional | J7, J8 automatic §7, §8; corrections optional and persistent §9 | Met by design |
| §4.4 two architectures over one core | The book is a projection of the shared core §12; reader state stays human-side; packs untouched | Met by design |
| §4.5 drift and continuity | Owned by the AI side. The book adds nothing to its packs beyond IDs, shares context receipts, and shows "this chat draws on" | Not weakened |
| §4.6 product-agnostic core with connectors | Generic agent registry §5.2; generic session key and correction origins §9.2, §12.1; one MCP tool contract with per-connector transports and profiles §10.2, §10.8 | Met by design for the core. **At risk** for reach: in-chat slices on the desktop chats depend on spikes S-R1, S-R2 (H14); ChatGPT Desktop chat needs a plan path (connector design CR3; CS1) and, only if CS2 fails, a relay (CR4; SPINE §7.3) |
| §4.6 local now, cloud later; personal first | §10.1, §10.2; every off-machine flow listed §8.15 | Local now: **At risk** (H21): the writer and audit call a cloud API, and ChatGPT Desktop chat needs a relay if CS2 fails. Q7 is asked as ARCH DQ-3(a), where a "No" selects all-local models and may weaken the Book's prose, focus and continuity until local models pass; the relay is asked as ARCH DQ-4(iii). Cloud later and personal first: met by design |
| §4.7 robust maintainer | Leaf-only inputs, V1–V15, B1–B16, 100% entailment, fallback, automatic freeze, replay, fault injection §8, §13 H | Met by design for structural errors. **At risk** for semantic errors, bounded statistically (H15, H16) |
| §4.8 built and evaluated | §13, §14; build order §10.8 | Planned |
| §5 constraints: provenance, supersede not overwrite, never summarise summaries, context rot, sycophancy, injection | §5; §7.5–§7.6; §8.3, §8.9; big pictures from leaves only §4.5; slices ≤ 600 tokens §10.8; pushback kept apart §9.3; §9.2, §10.3 | Met by design |
| §6 "each item shows its sources, and the view shows what they are working toward learning next" | Rail and drawer §5.4, §5.5; first screen §10.4 with the goal-independent frontier §6.3 | Sources shown: met by design (speaker on desktop items at risk, H8). What they are working toward next: present with or without goals; **at risk** for quality (H10) and for goals stated in desktop chats (H8) |
| §6 "maintains itself … errors bounded, detectable and correctable" | §8.6–§8.14; parity sentinels on real data §8.12; §9 | Met by design for detection and correction. **At risk** for semantic error, bounded statistically (H16) |
| §3.1 other sources such as reading and work | Source-generic anchors; "■ source" voice; a document in the golden book; employer and unclassified repository sessions on an allowlisted personal account captured into their own work scope (Q3) | Met by design |

**Where this design is at risk, and how it is handled.** No requirement is narrowed on purpose: every clause keeps its full target, and none is marked Met while a risk admits it may fail. These clauses are at risk. Each goes to the user as a risk in §16 or a question in §15 (now asked in ARCHITECTURE §14 or SPINE §11.2):
- **Helps the person remember:** reading is a modest memory technique (H1; Q4 settled as this risk, ARCH R16).
- **Reads like a textbook:** explanatory holes from the leaf-only rule (H9, Q2); evidence that may not transfer (H3); local-only writing if cloud calls are ruled out (H21, Q7); a thin Book in its first weeks (H22).
- **Helps the person understand:** simulated readers only, unless the user takes the optional acceptance read (H7, §13.5).
- **On Claude Desktop chat and ChatGPT Desktop chat:** who said it, which conversation, AI-said content in featured slots, a chat's last reply, and goals (H8, Q6).
- **What to learn:** frontier quality, with and without explicit goals (H10).
- **Local now:** cloud model calls on captured content and, if CS2 fails, the ChatGPT relay (H21; Q7 as ARCH DQ-3(a); the relay as ARCH DQ-4(iii)).
- **Product-agnostic reach:** in-chat cards and the ChatGPT plan path depend on unverified channels (H14).
- **Robust maintainer and bounded errors:** verifier independence and semantic error (H15, H16).

---

## 18. Provenance of this design

### 18.1 The base, and why

The judges disagreed: one picked C (goal fidelity), one A (learning science), one B (maintainability). Mean scores were A 7.8, C 7.2, B 6.7. A was the only attempt no judge ranked last, and its evidence-derived anatomy answers the user's 2026-10-08 words most directly ("help human understand and remember … just like textbooks"). So A is the base. B's and C's strengths are grafted where they fix A's weaknesses: B's compiler and deterministic structure (A's weakest area per the maintainability judge) and C's voices, medium and reader moments (A's gaps per the goal-fidelity judge).

### 18.2 Ideas taken from each attempt

**From A (learning science):** the evidence table and rules D1–D16 with their limits; the units, including Part 0 and the Casebook; the fixed page anatomy with "Where this fits" before the explanation; idea-stating headings that must be entailed; segment and sentence limits; e.g. lines and "From your work" with its "share" line; "Who taught you this" as quoted records; refutation-block fields; the quote-not-retell rule (V11 → V4); code-pulled example quotes chosen by span ID; printings, editions and "Just in"; dormant chapters folded in place; anomaly-driven restructuring; the tiered re-check after a failure; the grounded-specifics check; freshness bars; the comprehension A/B with textbase and inference questions and the novice reader; the re-ask proxy with randomised cards; the what-to-learn components with fading possible directions; "Ask about this"; exposure-based "explained"; reconciling desktop corrections against verbatim text; questions Q2–Q4; the sources register, timeline and as-of views; one renderer locally and in the cloud; accessibility.

**From B (knowledge architecture):** the Q, R, B and T sentence kinds, with attribution only in T sentences and chips; the J7.1–J7.7 and J8.1–J8.3 pipeline; deterministic Leiden with a fixed seed, warm start, landmark-weighted revert, constraints and size bounds; weighted-Jaccard and Hungarian ID matching; page ID equal to concept ID; per-part numbering frozen between editions with insertion numbers; promotion hysteresis; the churn budget with automatic retry; invariants B1–B16; one home block per leaf; lineage groups; sentence reuse by citation set with the anaphora rule; the extractive fallback; the per-block-type error-budget freeze; 100% entailment on new sentences; grounded-token, hedge-and-modality and no-code-in-prose validators; forward chapters, stubs, graduation in place and the "Ahead" box; frontier sets defined in code; the next-step score and reason codes; the echo tag; hover definitions; defined-before-used; the syllabus-based golden book and the calibrated rubric judge; the topic-tree baseline; the determinism and replay rules; the causal-alternative and primary-concept fields.

**From C (reader experience):** the reader moments, including M12 and the T-RITUAL test; the Reader, cards and one-way export; one component library with two data adapters and MCP Apps fetching through `tools/call`; hardening of the local server; the voices with "You pasted" and the named narrator; the density rule; the source drawer; never showing a paraphrase as a quote; the per-conversation capture panel; the "conversation not identified" state (S-R7); chapter anchor types; the label content-word check; paragraph memoization with leaf-ID plans; "Since you last opened" with held beliefs first; the "Welcome back" opener; the deterministic answer page; the "this chat draws on" card; the confirm card with an app-only "Apply"; pushback kept apart from correction; the sentinel table; the block-version audit record; T-SLICE, T-STAB, T-NEW and T-FRESH; SR-1 to SR-6; the refutation ablation; spikes S-R1 to S-R8; the question on employer sessions; status-line glimpses; "Wrong conversation".

**Considered and not adopted:** A's automatic register switch, its 7/21/60-day re-encounter timer, cover mode as a working default, the natural-restatement metric, the optional explain-from-memory test, the struck-through old sentence, section-level rebuilds and 20% entailment sampling. B's verbatim-only explanation block, facts grouped under a voice header per speaker, "explained to you n times", progress counts on the home screen, the missing "You pasted" voice, the whole-book publish stall and the reachability-based parity check. C's model-written speaker phrases, model-written "How this changed" and "Where sources disagree" (the block title "How this changed" is now used, but its content is rendered by code, §7.6), vendor letters as speaker markers, the archive shelf, the recall fold as a working default, "confused" and "I already know this", path groups with counts, a memo key that includes the model and prompt, an alert-only error budget, a model call in the correction path, and the "Today, provisional" strip on the first screen.

### 18.3 How each must-fix defect was resolved

J1 is the goal-fidelity judge, J2 the learning-science judge, J3 the maintainability judge.

| # | Must-fix | From | Resolution | Where |
|---|---|---|---|---|
| 1 | No inferred familiarity, even silent (A's register switch) | J1 | The reference view is a reader toggle only; nothing switches automatically | §4.6, D4, §11 |
| 2 | No knowledge-state labels ("confused", "I already know this") unless approved | J1 | Not shown; neutral "Hide from next steps" instead; put to the user | §6.6, Q5 |
| 3 | No counts that work as progress meters | J1 | Removed from goal pages, the first screen and pages; source counts by speaker kept as attribution only | §6.2, §6.3, §10.4, Q5 |
| 4 | No retrieval aid until the user answers; evaluations pass with it off | J1 | None built; all checks run without one | §11, Q1 |
| 5 | Re-encounters from relevance only, never an elapsed-time schedule | J1 | Composer relevance only; one card per chat; no timer | §10.8, D11 |
| 6 | Code renders all attribution; keep "You pasted"; label Northstar's wording | J1, J3 | Q/R/B/T kinds; V4 bans names, pronouns, attribution verbs and the user's past in model prose; five voices; narrator named and its prose marked "Northstar's wording" | §5.2, §5.3, §8.5 |
| 7 | Guarantee "in which conversation" on the desktop chats | J1 | Identity states per episode, using the verified `openai/session` key and the Claude session handle; never claim an unjoined conversation; per-conversation capture panel | §5.8, H8, S-R7 |
| 8 | Cited explanatory prose is the default; fallback only on failure | J1, J2 | Model-written segmented body; extractive fallback labelled as degraded, bar 5%, alert 2% | §4.4, §8.7 |
| 9 | A passive proxy for remembering | J1 | Re-ask rate with randomised cards, labelled as combined findability and retention | §13 E |
| 10 | Speaker neutrality at promotion; monitor AI-said share there | J1 | The promotion function's input has no speaker field; promotion parity check | §4.7, §13 B |
| 11 | Never test the user, even in aggregate | J1 | Restatement metric and explain-from-memory test dropped | §13.1, §13 E |
| 12 | No "Met" while a risk admits it may not be met | J1 | Status column with "At risk" pointing to the risk | §17 |
| 13 | Generic, extensible speaker identity | J1 | Agent registry; class glyph plus display name; no vendor letters | §5.2, §12.1 |
| 14 | Do not organise only by topic; anchor on goals and questions | J2 | Goal and question anchor nodes in the clustering graph, plus anchor typing by rule | §7.2, §4.5, D16 |
| 15 | Advance organiser before the explanation on every page | J2 | "Where this fits" is block 2; checked at 100% | §4.4, §13 C |
| 16 | Manage provenance density; no redundant markers; fold provenance blocks; test density | J2 | Rail only, chips only when unusual, folded blocks, BK6 arm | §5.4, §4.4, §13 D |
| 17 | Wording stable at paragraph or sentence level | J2, J3 | Paragraph memoization plus sentence reuse, keyed on leaves | §8.9 |
| 18 | Idea-stating headings supported by sources; chunk limits | J2 | Headings are cited sentences, 100% entailed; size rules | §4.2, §8.5, §8.6 |
| 19 | Verbatim home for AI worked examples; code never paraphrased | J2 | "In their words"; V8 | §4.4, §8.5 |
| 20 | Do not overclaim memory effects | J2 | Narrative effect not claimed; "Who taught you this" justified by source and time cues; re-encounters uneven (H14); ceiling put to the user; proxies labelled | §3.1 E12, §13 E, Q4 |
| 21 | Inference and application questions; feed, wiki and excerpt baselines; novice reader; refutation ablation | J2 | All in the comprehension A/B and SR set; BK5 | §13 D, §13.3 |
| 22 | Dangling terms visible where used; hover definitions; glosses question kept | J2 | Dotted "not yet explained" underline; hover cards; Q2 | §6.2, §10.5, Q2 |
| 23 | Fold dormant topics in place | J2 | Fold after 120 days; never moved | §7.4 |
| 24 | First screen invites reading; changes capped and secondary | J2 | Heading, continue reading, then at most 5 changes, then contents | §10.4 |
| 25 | Examples avoid distressing episodes; respect scopes; employer sessions out | J2 | D7 with a distress tag from hygiene; scopes; Q3 | §3.1, §12.1, Q3 |
| 26 | Never mention mastery, progress or scores; "explained to you on <date>" | J2 | Wording rule; banned words | §6.3, §11 |
| 27 | Superseded and contested knowledge rendered by code; causal alternative only from a leaf; no strike-through | J3 | Refutation blocks and disagreements are T and Q only; `causal_alt_ref`; superseded leaves excluded from current prose | §7.5, §7.6, §8.3 |
| 28 | Define what happens when the error budget trips | J3 | Per block type: freeze to fallback, re-verify the window, roll back a matching change, exit automatically | §8.8 |
| 29 | Entailment on 100% of new and transcluded sentences; reuse keeps a verdict only on identical leaf versions | J3 | As stated, plus the post-failure re-check from A | §8.6 |
| 30 | Parity on featured slots, not reachability | J3 | Featured-slot parity; B11 rewritten | §5.6, §8.11, §13 B |
| 31 | "Northstar misstated this source", separate from "the source is wrong" | J3 | New correction kind: blocks the sentence, pins quote form, bars the wording, counts against J7, never touches the leaf | §9.1, V11 |
| 32 | Correction origin binding on the desktop chats | J3 | Model calls only propose; I21 needs a card click, a Reader click or a later verbatim match | §9.2 |
| 33 | Validators block hidden and rejected items; a failed correction check withholds only the affected pages | J3 | Excluded at input and by V2 and V11; per-page withholding with extractive rendering and automatic repair | §8.3, §8.5, §9.4, B6 |
| 34 | Harden the local Reader against XSS and CSRF | J3 | Loopback bind, token cookie, Host check, CSRF, sanitiser, CSP, CI tests | §10.3, §13 H |
| 35 | Echo-loop guard | J3 | Context receipts and the `northstar_echo` lineage tag; never counts as support or toward promotion | §5.9, B15 |
| 36 | Deterministic, replayable structure; snapshot every J8 input | J3 | Algorithm, seed, warm start, matching, numbering, hysteresis and churn budget specified; inputs snapshotted per edition | §7.2, §7.3, §12.2 |
| 37 | Text stability across model and prompt migrations | J3 | Memo key excludes model and prompt; migrations rewrite nothing by themselves; T-STAB covers migrations | §8.9, §13 F |
| 38 | Coherence rule when sentences are dropped or reused | J3 | V12: anaphora rule and whole-paragraph re-validation, heading re-entailed | §8.5 |
| 39 | One shared cost model; thinking tokens; checked prices | J3 | One volume chain at 36K events a year; thinking tokens counted; prices checked 2026-10-08 | §8.10 |
| 40 | RISK 18 and synthetic-calibration understatement | J3 | Which checks move where, what the user is told; real-data error reported separately | §8.13, H15 |

---

## Sources

### Research notes in this repository
- [10] `docs/research/round2/10-integration-surfaces.md`; [11] `11-in-session-drift.md`; [12] `12-knowledge-structure.md`; [13] `13-robust-ai-maintenance.md`; [14] `14-memory-layer-landscape.md`; SYNTHESIS = `docs/research/round2/SYNTHESIS.md` (§3.1, §3.2, §3.4, §3.5, §5, §7, §7.3, §7.4; RISKS 4, 6, 7, 11, 13, 15, 17, 18, 19, 22).
- Round 1, evidence only: [01] `docs/research/01-human-memory-and-learning.md`; [02] `02-pkm-practice-and-failure.md`; [07] `07-human-vs-ai-consumers.md`.
- Inputs to this synthesis: `docs/design/foundations/textbook-A-learning-science.md`, `textbook-B-knowledge-architecture.md`, `textbook-C-reader-experience.md`; sibling designs `connector-claude-desktop-chat.md`, `connector-chatgpt-desktop-chat.md`, `desktop-observer-macos.md` (for session identity only); `SPINE.md` (the system design), cited for its model-call rules (§8.4, §8.5), relay (C03, SD-9) and user questions (UQ-1, UQ-4, UQ-5) only.
- Cited by the consistency fixes: `SPINE.md` §5.2 (relation types), §7.3 (relay only if CS2 fails), §11.2 (UQ-3, merged Q3), SD-38; `docs/design/components/connectors-desktop-and-mcp.md` §1.2, §2, §3.5 (the one MCP tool contract); `platform-security-privacy.md` §6.3, §6.6 (work scopes, "no new exposure"); `ai-continuity.md` §9, D4 (cross-session echo); `connectors-claude-code-and-codex.md` §7 and UQ-HK-1 (merged into Q3).
- Cited by the review fixes, with these short names: ARCH = `docs/design/ARCHITECTURE.md` (§12.2 resolutions R7, R12, R14, R16; §14 decisions DQ-3, DQ-4, DQ-7, DQ-10, DQ-12); REVIEW = `docs/design/REVIEW.md`; in `docs/design/components/`: [MT] = `maintainer.md` (§6.5 S10 bars, §7.2 controller registry, §9.6 cost, X22); [CX] = `connectors-desktop-and-mcp.md` (§2.3 reported points, bodies and reply length; §4.4 step 6, the closing call); [AC] = `ai-continuity.md` (§3.2 rendering rule); [IS] = `ai-in-session.md` (§5 item-level output); [EV] = `evaluation-and-build-plan.md` (A12); [CDM] = `core-data-model.md`; [PL] = `platform-security-privacy.md` (SP-PL-16); SPINE §6.3 (`landmark_signals`), UQ-4, UQ-13; `connector-chatgpt-desktop-chat.md` CS6.

### Learning-science sources
Looked up by attempt A on 2026-10-08 and not re-checked for this synthesis. Full citations and URLs are in `textbook-A-learning-science.md`, Sources. Key works: Schneider et al. 2018 and Lorch 1989 (signalling); Rey 2012 and Sundararajan & Adesope 2020 (coherence); Rey et al. 2019 (segmenting); McNamara et al. 1996 and Kalyuga et al. 2003 (cohesion, expertise reversal); Barbieri et al. 2023, Rawson et al. 2015 and Alfieri et al. 2013 (examples); Symons & Johnson 1997 and Liu et al. 2023 (self-reference); Ginns, Martin & Marsh 2013 (conversational style); Lei et al. 2025 (illustrations); Schroeder & Kucera 2022 (refutation text, https://pmc.ncbi.nlm.nih.gov/articles/PMC8784251); Rawson & Kintsch 2005 and Greving & Richter 2019 (spaced rereading, https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6333692/); Mar et al. 2021 (narrative, https://pmc.ncbi.nlm.nih.gov/articles/PMC8219577/); Rowland 2014 (retrieval practice); Luiten et al. 1980 and Stone 1983 (advance organisers); Chan et al. 2024, Kim et al. 2025 and Dumais et al. 2003 via [01] and [12].

### Product facts

| Fact | Source | Checked |
|---|---|---|
| Claude passes no conversation ID to MCP servers or apps: "Neither `hostContext` nor the tool-call arguments include a Claude-provided conversation ID." Model-context updates feed "Claude's context for the next turn" | https://claude.com/docs/connectors/building/mcp-apps/instance-supersession | 2026-10-08 |
| Claude Desktop runs local example servers from `claude_desktop_config.json`; "Claude asks for permission to display the app. Click **Allow**, or **Always allow** … and the MCP App renders inline in the conversation" | https://claude.com/docs/connectors/building/mcp-apps/getting-started | 2026-10-08 |
| MCP Apps spec: "app" visibility means the tool "is callable by the app from the same server connection only"; "Host MUST NOT include tools in the agent's tool list when their visibility does not include `"model"`"; `ui/open-link`: "Host SHOULD open the URL in the user's default browser or a new tab" | https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/2026-01-26/apps.mdx | 2026-10-08 |
| OpenAI Apps SDK: tool calls carry `_meta["openai/session"]`, "Anonymized conversation id for correlating tool calls within the same ChatGPT session"; `_meta.ui.visibility` defaults to `["model", "app"]`; widgets can call tools | https://developers.openai.com/apps-sdk/reference | 2026-10-08 |
| ChatGPT plugins "work in Chat and Work across ChatGPT on the web, desktop, and mobile"; invoked with `@` or chosen by ChatGPT | https://learn.chatgpt.com/docs/plugins | 2026-10-08 |
| Codex MCP configuration lives in `~/.codex/config.toml`; "The ChatGPT desktop app, Codex CLI, and IDE extension share this configuration"; the page does not say whether locally configured servers work in desktop Chat mode | https://learn.chatgpt.com/docs/extend/mcp | 2026-10-08 |
| Claude Code MCP output: warning above 10,000 tokens; default limit 25,000; `MAX_MCP_OUTPUT_TOKENS` | https://code.claude.com/docs/en/mcp | 2026-10-08 |
| Claude Code `Stop` hook provides `last_assistant_message` | https://code.claude.com/docs/en/hooks | 2026-10-08 |
| Claude Code `UserPromptSubmit` receives the verbatim prompt; Codex hooks receive `prompt` and `last_assistant_message`; hooks carry `transcript_path` | [10] F5, F9; https://code.claude.com/docs/en/hooks ; https://learn.chatgpt.com/docs/hooks | 2026-10-07 by [10]; not re-checked |
| Anthropic prices per million tokens: Sonnet 5.5 $2 / $10, batch $1 / $5; Opus 5.5 $4 / $20, batch $2 / $10; Haiku 5.5 (prompts up to 100K) $0.10 / $0.50, batch $0.05 / $0.25; cache hits on Opus 5.5 and Sonnet 5.5 at 0.05× base input; batch and caching discounts stack | https://platform.claude.com/docs/en/about-claude/pricing | 2026-10-08 |
| MCP prompts as Claude Code slash commands; status-line OSC 8 links in some terminals | https://code.claude.com/docs/en/mcp ; https://code.claude.com/docs/en/statusline | 2026-10-08 by attempt C; not re-checked |
| Claude Desktop local `.mcpb` servers need no public HTTPS | [10] F4; https://claude.com/docs/connectors/building/mcpb | 2026-10-07 by [10]; not re-checked |
| Widget rendering and app-only tools in ChatGPT Desktop Chat mode; `ui/open-link` to a loopback address in Claude Desktop; deep links into desktop conversations; `openai/session` in desktop Chat mode | none found | (Unv), spikes S-R1, S-R2, S-R5, S-R7 |
| Price of a second vendor's verifier model (fallback in §8.13) | not checked | (Unv) |
| Claude: in Chat (web, desktop, mobile), plugin hooks, agents and local MCP servers are "Ignored"; skills load (§5.8) | https://claude.com/docs/plugins/platform-support | 2026-10-08 by connector-claude-desktop-chat.md (V1); not re-checked here |
| ChatGPT: hooks are documented for local-only Work and Codex threads; desktop Chat mode is not mentioned (§5.8) | https://learn.chatgpt.com/docs/extend/mcp.md ; https://learn.chatgpt.com/docs/hooks | 2026-10-08 by connector-chatgpt-desktop-chat.md (V6, V7); not re-checked here. No hook in Chat mode is (Unv), spike CS3 |
| On both desktop chats, the sanctioned live channel gives the model's own report of the chat and no verbatim AI text (§5.8) | Derived from the two rows above and SYNTHESIS Table A | Derived; (Unv) for ChatGPT until CS3 |
| MCP App cards render when a tool call renders an app; each such call mounts a new widget instance (§10.1, §10.8) | [10] F2; https://claude.com/docs/connectors/building/mcp-apps/instance-supersession ; https://github.com/modelcontextprotocol/ext-apps | 2026-10-07 by [10]; not re-checked. Vendor, indirect. "Only after a model tool call" is (Unv), spikes S-R1, S-R2 |
| ChatGPT Chat appears to reach only remote MCP tools, so a local core needs a relay only if spike CS2 fails (§8.15, §10.2; SPINE §7.3) | connector-chatgpt-desktop-chat.md V1, V5, V6: https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt ; https://learn.chatgpt.com/docs/plugins.md ; https://learn.chatgpt.com/docs/extend/mcp.md | 2026-10-08 by that design; not re-checked here. Local MCP in Chat is (Unv), spike CS2 |
| Retention of content sent to the Anthropic API (§8.15, Q7) | not checked | (Unv) |

---

## Fidelity fixes (2026-10-08)

An independent goal-fidelity audit of this file (verdict: pass with fixes) found 10 major and 10 minor issues. All are fixed below. Each fix changes the design only as far as the issue requires, and none weakens a non-negotiable (GOAL §4). Two fixes needed the user's decision on a point that touches the WHAT or an invariant; those went to §15 as questions (Q6, Q7) instead of being decided here.

| # | Severity | Issue | What changed |
|---|---|---|---|
| 1 | Major | The frontier existed only over a goal's subgraph, so with no explicit goal "what to learn" shrank to open questions and dangling terms | Added a **goal-independent frontier** (`mentioned`, `frontier_all`, `later_all`) over the whole concept graph, by any speaker, using direction-checked prerequisites; plus labelled frontiers for possible directions ("inferred") and reported goals ("provisional") (§6.3). "Next from here", "Ahead" and the first screen use it when no explicit goal applies (§4.4 block 10, §4.5, §6.1, §10.4). New score terms `direction_relevant` and `mention_breadth`, reason codes `mentioned` and `direction` (§6.4). Golden persona with zero explicit goals and a §13 G check that what to learn is non-empty, reasoned and valid for it (§13.1, §13.2 G). H10 notes the extra noise |
| 2 | Major | AI-said knowledge did not feed "what to learn": no AI-raised open questions, no AI-suggested next steps | Added **AI-raised open questions** and **AI-suggested next steps** as attributed what-to-learn items, rendered by code as a T label plus a Q quote ("Suggested by Claude (12 Sep): '…'"), gist on desktop chats until reconciled (§6.1, §5.6 item 8). New score term `suggested` and reason codes `suggested` and `raised` (§6.4); stub line (§6.5); mock (§4.4); question anchors for AI-raised questions (§4.5). An AI suggestion never becomes a goal, constraint or instruction (I5). New `suggestion` kind tag and raised-by field (§12.1). §13 B what-to-learn parity check |
| 3 | Major | Goals stated in Claude Desktop chat or ChatGPT Desktop chat never reached Part 0, anchors or the frontier, because both connector designs hold model-reported goals back; the book did not say so and its mock showed such a goal as confirmed | Designed **reported goals** (§5.8, §6.1): shown in Part 0 and on the first screen under "Reported goals, not yet confirmed", kept apart like possible directions; may anchor a provisional frontier, not chapters (§7.2); confirmed automatically by a verbatim match, or by an optional one-click "Yes, that's my goal" via the confirm card (`app_click`) or the Reader (`reader_click`) (§9.1, §9.2, §12.3). A reported goal reaches AI packs as a goal only after a verbatim match; whether a click may also confirm it for AI packs (I5) is **Q6**, and until then a click confirms it in the book only. Mock first screen now shows the reported state (§10.4). Added to H8; §17 what-to-learn row marked at risk on the desktop chats; new §17 row for desktop-chat goals; §13 G reported-goal checks; §12.1 reported state and confirmation event |
| 4 | Major | On the desktop chats' sanctioned layer the speaker of a model-reported item is set by the chat model, yet the book rendered such items in "you" slots and §17 said "who said it" was met | Added a **speaker-fidelity** axis and chip "speaker as reported by the chat model" (§4.4 legend, §5.4, §12.1). §5.3 now states what code-only attribution does and does not guarantee. Model-reported items never fill user-voice slots ("Your own words", "You said", "You now say", "From your work", e.g. lines, "In your words") or "In their words", and never count as a held stance, until reconciled; they show as labelled gists (§5.2, §5.8, §7.6, §7.7, §10.7). H8 extended to speaker; §17 "who said it" now **At risk on the desktop chats (H8)**; §13 A speaker-fidelity check with planted speaker swaps (§13.1) |
| 5 | Major | A page needed two episodes, a goal, an open question or a pin, so a one-chat AI explanation became a one-line short note, and where its passages lived was unspecified | §4.7 now also promotes a concept with one **substantive teaching leaf** from any speaker (explanation or definition of at least 120 words, or any worked example or procedure; estimate, calibrated) or that was the subject of a user question, open or answered. The promotion input gains a speaker-free substantive-teaching flag. Short notes **expand in place** and are the home block of their leaves (§4.1, §4.7, §5.6 item 4). Promotion parity now also runs on single-episode concepts (§4.7, B11, §13 B). H12 notes the extra pages |
| 6 | Major | Warning chips and gap detection singled out AI claims, against §5.6 item 1 | Verification display is now **speaker-neutral**: the density rule chips any unchecked checkable claim whoever said it (§5.4); verification values apply to every speaker; "AI-cited, unchecked" renamed "cites a source, unchecked"; unchecked reliance and the `check` reason cover any speaker (§4.4 block 9, §6.1, §6.4); advice and opinion labels apply to every speaker (§5.6 item 5). §13 B warning-chip parity check and §8.12 sentinel |
| 7 | Major | Featured-slot parity had a reference only on the synthetic golden book, so demotion of AI-said content on real data was undetectable | Defined a **live reference**: the rank-weighted AI-said share among eligible active leaves assigned to the same blocks (§5.6 item 7). B11 runs against it nightly on real data as a sentinel (§8.11, §8.12); the golden comparison is kept for evaluation, and the two must agree on the golden book (§13 B) |
| 8 | Major | Writer and audit sent all captured content, including ChatGPT and Codex captures, to Anthropic's API nightly; cross-vendor scope applied only to slices; the ChatGPT relay was not acknowledged; §17 said "local now" was met | New **§8.15** lists every off-machine flow (writer, audit, titles, fallback verifier, slices, ChatGPT relay). I17 cross-vendor scope now applies to writer and audit inputs; held-back items go to a local writer that passed its canary, else extractive fallback (§8.3, §8.15; new spike S-R10). §8.6 no longer says no data leaves the machine. §0 item 13, §10.2, §10.8 note the relay. New risk **H21** and question **Q7** (does "local now" allow cloud model calls on captured content?); no real content is sent before Q7 is answered. §17 "local now" now **At risk (H21)**. §13 H scope-egress test |
| 9 | Major | §17 marked clauses Met while risks admitted they might fail, against must-fix #12, and said "It narrows no requirement" | §17 rewritten. Now **At risk**: reads like a textbook (H9, H3, H21); helps understand (H7); who said it, which conversation, what has been learned and AI-said first-class on the desktop chats (H8); local now (H21); product-agnostic reach (H14, CR3, CR4); semantic maintainer errors (H15, H16). New rows for what to learn without explicit goals and for desktop-chat goals. The closing paragraph now lists every at-risk clause with its risk and question |
| 10 | Major | Every check of "reads like a textbook … easy to understand" was synthetic; no optional check by the actual user | Added **§13.5, an optional one-off acceptance read**: the user reads a small sample of real pages and says whether they read like a textbook and are easy to understand. No recall test, nothing stored per concept, no reminder, and every gate passes without it (§0 item 15, §13.1, §13.4, H7) |
| 11 | Minor | Q4 assumed "Accept" pending an answer, and framed remembering as the user's practice | Q4 now lists the system-side levers and the further ones available, and asks which the user wants. Working assumption: **no acceptance assumed**; "remember" stays At risk and proxies are never reported as meeting it. §3.2 wording changed to match |
| 12 | Minor | Q3 did not say whether employer-repository sessions were excluded from capture or only from the book | Q3 now says they are still captured, into a separate work scope under I17, and kept only out of the personal book; a later "yes" applies retroactively |
| 13 | Minor | The book banned the word "learned", yet its own search box, answer page, slice and MCP prompt use it, as does GOAL §3.2 | D14, §6.3 and §11 now ban only claims about the reader's state ("you have learned X", "covered", "mastered") and allow the user's query phrasing and GOAL's term |
| 14 | Minor | §11 forbade any engagement-based change, while reading signals drive folding, dormancy and landmark weight | §11 now forbids inferred familiarity and changes to density or content, and lists the four allowed navigation-only uses of reading signals with why none estimates knowledge |
| 15 | Minor | The block title "How your understanding changed" asserted something about the user's mind | Renamed **"How this changed"** everywhere (§0, §4.4, mock, §5.6, §7.5, §7.6). "Your view" or "you said" appears only for a stance the user held, as their dated quote; the first-screen change line reads "A view you stated has changed" only then (§7.7, §10.4) |
| 16 | Minor | The mock page showed desktop-chat items as verbatim | Mock items from Claude Desktop chat are now labelled "reconciled"; a ChatGPT Desktop chat question shows the model-reported gist with its label (§4.4); the stub example no longer quotes a desktop-chat question as verbatim (§6.5) |
| 17 | Minor | "No model prose above chapter level, because it would summarise summaries" was false: parts could compile from leaves as chapters do | Added a **part big picture** compiled from code-selected leaves (linked to pages in two or more of the part's chapters), under the same validators, 100% entailment and the L4 audit (§4.5, §8.2, §8.3, §8.6, §8.10, §11) |
| 18 | Minor | Connector specifics leaked into core records: the Episode record named `openai/session`, and the `chat_verbatim` origin was defined by the `UserPromptSubmit` hook | Episode now has a generic `connector_session_key {connector_id, key}` (§12.1). §9.2 defines all correction origins generically; `chat_verbatim` means a match against a verbatim user turn from the connector's fidelity channel. Product and hook names stay in per-connector rows only |
| 19 | Minor | §8.13 cited GOAL §2 for verifier choice, and "told before the change takes effect" could read as waiting on the user | Now cites GOAL §5; the change takes effect automatically and the user is informed once, with no action needed |
| 20 | Minor | Two product-behaviour claims had no URL or check date: the desktop chats' sanctioned channel gives no verbatim AI text; a card appears only after a model tool call | Both now carry URLs and check dates inline (§5.8, §10.1, §10.8) and in the Sources product-facts table, with inherited checks marked as such and the unverified parts labelled (Unv) with their spikes (CS3, S-R1, S-R2). Added rows for the ChatGPT relay basis and for API retention (Unv) |

**Audit coverage gaps noted, not fixed here** (they lie outside this file), with their status after the review of 2026-10-08:
- Equal depth of in-session focus and continuity (AI side): **handled** by [IS], [AC] and [EV].
- Measured drift and continuity (GOAL §6 bullets 1–2): **handled** by [IS], [AC] and [EV].
- Reconciling this file's tool names with the ChatGPT connector's tool profile: **closed** by X01 (Consistency fixes, below).
- How the core detects a misclassified goal or a wrongly "answered" question: **handled** by [IS] §5's item-level output (the Goal-Change Handler).
- Whether SPINE's core accepts the new fields in §12.1: **closed**; SPINE accepts them, as [CDM] specifies.
- The coverage gap on a declined observer is now part of H8.

---

## Consistency fixes (2026-10-08)

A cross-document review found five issues where this file disagreed with the rest of the design set. Each resolution below was adopted as given, with minimal local edits. None weakens a non-negotiable (GOAL §4), and none departs from SPINE.

| ID | Issue | What changed |
|---|---|---|
| **X01** | Three incompatible MCP tool catalogs; this file used `northstar_page`, `_learned`, `_to_learn`, `_changes`, `_toc`, `northstar_correct` and app-only `northstar_apply_correction` | Adopted the one contract of `connectors-desktop-and-mcp.md` §1.2, §2. §9.2: chat corrections go through `northstar_note(kind: correction)`; the card's **Apply** and **Yes, that's my goal** call `northstar_widget_action(action: apply_correction / confirm_goal)` with a single-use `action_nonce` (the one name for the click credential, §3.5 there). §12.3: book reads are `northstar_book(view: …)`; prompts as §2.8 there. §5.8: confirm click and the session handle in the first `northstar_context` result. §10.2, §10.8: views per slice type, ChatGPT tool set, build order. §0 item 13 cites the contract |
| **X03** | Q3 said employer-repository sessions are captured; `connectors-claude-code-and-codex.md` UQ-HK-1 said skip | One rule in Q3, now one SPINE §11.2 question merged with UQ-HK-1: a non-allowlisted account is skipped in both directions (UQ-3); on an allowlisted personal account, employer and unclassified repositories are captured into `work:<org>` / `unclassified:<repo_hash>` (`platform-security-privacy.md` §6.6), with no personal-scope injection, egress only under "no new exposure", and nothing in the personal book or packs. §17 §3.1 row updated |
| **X17** | §5.9 and B15 limited `northstar_echo` to one session; `ai-continuity.md` D4 extends it | §5.9: an echo may follow a delivery in the same session or in a same-`speaker_model_family` session within 90 days, when the span has no fresh grounding. B15 and S-R9 updated. §5.9 and §13.2 B: the share of AI-said spans discounted as echoes is reported by vendor family, also by the SD-38 vendor-parity sentinel |
| **X28** | §0 item 13, §10.2, Q7 and H21 said ChatGPT Desktop chat "needs a relay" | Now "a relay only if CS2 fails" (SPINE §7.3) in those places and in §8.15, §10.8, §17 and the Sources row |
| **X29** | §12.1 used `advances-goal` and omitted `undercuts` and `contradicts` | §12.1 lists SPINE §5.2's 18 relation types; §7.2 uses `advances_goal` |

---

## Review fixes (2026-10-08)

The adversarial review of the whole design set ([`REVIEW.md`](../REVIEW.md), which holds the full record, the verdicts and the fixes not adopted) raised the findings below for this file. Each was applied as the review resolved it, with local edits only. None weakens a non-negotiable (GOAL §4), and none changes the WHAT: questions that touch the goal stay with the user, now in ARCHITECTURE §14.

| ID | Issue | What changed |
|---|---|---|
| **BOOK-1** | Cold start and growth were not designed | **Growth regime** (§7.3): a bootstrap edition at the first printing with pages and after any export backfill, exempt from the churn budget; daily editions for 14 days, then weekly; tentative placements, pages younger than 2 editions and new chapters or parts never count against the budget; the part-level budget is free below 60 pages or after 25% growth; a "growing book" form below the size minimums (§4.2, §7.1, §7.2). Hysteresis now applies only to the two-episode rule; strong signals promote on the first night (§4.7). Tentative placements are settled at the next edition (§7.2, §8.12). "New this week" in Part 0 and on the first screen (§4.1, §10.4). New risk **H22**. No size-violation retry rule was added |
| **BOOK-2** | At desktop L0 a chat's last reply was never captured, and one-chat AI explanations could not earn a page | Substantive-teaching flag rewritten with case (c) for model-reported capture, computed in code in C08 `concept_facts`, speaker-free (§4.7, §12.1). Reported explanation bodies (≤ 1,500 characters) render as labelled gists; the closing report call ([CX] §2.3 `this_reply_points`) is the only L0 capture of a chat's last reply (§5.8); H8 gains (f), the final-reply loss. §13.2 B single-episode check, desktop against hook, with content parity; golden personas for it (§13.1) |
| **BOOK-3** | The page anatomy could not be filled from one-leaf evidence | The explanation has 1–5 segments sized to their leaves, with no word floor; V10 limits are targets that warn (§4.2, §4.4, §8.5). B5 allows one quoted reuse of an explanation leaf in "In their words" and a key idea citing a leaf homed elsewhere (§4.4, §8.11). Question-only concepts get a question page or stub (§4.3, §4.7). New validator **V15** against restatement across blocks (§8.5; counts in §0, §8.1, §8.14, §17). Verbatim body only as ablation **BK8** (§13.3) |
| **BOOK-4** | Entailment false rejects were unbounded | A rejected sentence is re-drafted once and re-checked by the same certified verifier before it is dropped, first for `contrast`, `connect` and `caveat`; a second verifier route only if certified in S10 (§8.6, §8.7). Survival sentinels per verifier certificate (§8.12). §8.13 points to [MT] §6.5's entailment true-accept bar |
| **BOOK-5** | Evaluation could not catch a correct but useless Book | D questions from the hidden world's gold leaves; a BK0 bar (§13.2 D). Textbook sections as a style floor; structural bars (§13.2 C). Explained coverage (§13.2 B). Growth checkpoints at simulated days 1, 7, 30 and 60; desktop-only and AI-tools learner personas (§13.1) |
| **BOOK-6** | Explanation segments had no producer | Segments are grouped in code in J7.2 by J3 kind tag, then fixed-seed clustering, with persistent sub-topic IDs (§8.1, §8.3). The paragraph plan records group IDs (§8.4); memo keys use them (§8.9) |
| **BOOK-7** | V4 banned product names and reporting verbs; V8 banned formulas | V4 now bans registry names and generic agent nouns as speakers of claims, whoever is cited; names may appear as subject matter when a cited leaf contains them (§5.3, §8.5). Starting verb lexicon; "retells the user's past" detector defined; a prompt bug inserting speaker names is still blocked. V8 allows short identifiers and formulas from a cited leaf, as code; V6–V8 explained together (§8.5) |
| **BOOK-8** | Frozen wording had no quality path; reuse could make patchwork paragraphs | A staged, labelled "reworded" printing as a quality release, with 100% entailment on reworded sentences (I19) (§8.9, §0 item 10, §8.10). T-STAB redefined (§8.9, §8.12, §13.2 F). V12 extended to connectives and definite references; a paragraph that lost a neighbour is redrafted whole unless a coherence check passes (§8.5, §8.9) |
| **BOOK-9** | Chips could flood desktop-heavy pages | A block-level fidelity note; sentence chips mark only exceptions; each sentence keeps its glyph and drawer (§5.4). BK6 also runs on the desktop-only persona (§13.2 D) |
| **BOOK-10** | What to learn could fill with reflexive offers | J3 tags `offer` apart from `learning_suggestion`; offers never on a frontier (§6.1, §6.3, §12.1). `suggested` counts once per concept per conversation; `ready` defined; first-screen ranking preference with a fill fallback (§6.4, §10.4). Offer-leakage bar (§13.2 G) |
| **BOOK-11** | Frozen numbers were not frozen while the Book grows | Chapters and parts keep their numbers; insertion numbers at chapter and part level (4.2a, 5a); renumbering counts against the churn budget (§7.2, §7.3). Number survival in the landmark bar (§13.2 F) |
| **CONS-2** | A yes to DQ-10 left click-confirmed goals unlabelled | A click-confirmed goal line reads "confirmed by your click; wording as reported by the chat model" (§5.8, §9.1, §9.2). Q6-on case in §13.1 and §13.2 G |
| **CONS-4** | The R14 rule was not in the specs, and a model would set a promotion input | Merged with BOOK-2: the flag is computed in C08 (§4.7). The reported reply-length option is decided by an extension of A12/CS6, not S-R6 (§14) |
| **CONS-7** | R7 and R12 lived only in ARCHITECTURE | §8.13: the S10 bar is [MT] §6.5's Wilson upper bound; on failure, the same-vendor check, then a second local family, then ARCH DQ-12 (also §8.15, H15). §8.10: S10-failure cost follows [MT] §9.6 (about $52 a month at 100 turns a day, not $13) |
| **CONS-10** | Landmark-weight inputs had no owner | Inputs are page opens (a per-page open counter in `reader.db`), slice references and corrections; C16 gets only the derived vector through `landmark_signals` (§7.2, §11, §12.2, §12.3). "Bookmarks" dropped: the Reader has no bookmark feature. ReaderState gains `open_count` |
| **CONS-11** | ARCH R16 was not propagated | §0 item 14, D11b and §11: no retrieval aid is built (ARCH R16, GOAL §2). §15 gains a Status column: Q1, Q4 and Q5 settled or closed (ARCH R16), user override only; Q2 → DQ-7; Q3 → SPINE UQ-13; Q6 → DQ-10 (expanded); Q7 → DQ-3(a). The relay choice points to DQ-4(iii) (§8.15). References to Q1, Q4, Q5 updated (§3.2, §4.8, §13.4, H1, §17) |
| **MR-8** | Rollback was claimed hash-identical | Rollback restores Book structure by a compensating edition with redirects, not hash-identically; pages re-render without the rolled-back job (§8.14, §13.2 H) |
| **SEC-2** | Chat corrections gained I21 on any substring of a user turn | Four conditions for `chat_verbatim` and `chat_verbatim_reconciled`: outside paste and Northstar-block ranges; target delivered, cited, named or quoted; an independent-family entailment check; at most 3 a session. Goal-status changes and `reject_content` on items with verbatim user authority need the item named or quoted. No minimum length. Goal-confirming clicks only from the widget or Reader, never on the reporting turn (§5.8, §9.2, §12.3) |
| **SEC-4** | Captured text could reach agents verbatim through slices and exports | Slices and exports apply [AC] §3.2's one rendering rule; slices are model-requested, so flagged spans may be quoted there, while unsolicited cards hold them back (§10.8, §10.1). The Markdown mirror and EPUB apply the Reader's renderer rules (§10.1, §12.3, §13.2 H) |
| **SEC-11** | Reader authority trusted any click in the everyday browser profile | Reader on `northstar.localhost:<port>` with a host-only cookie; at most 10 corrections a minute; step-up for bulk moves and hides; search by POST or URL fragment; neutral page titles; a separate cookie jar behind SP-PL-16 (§10.1, §10.3, §12.3, §14). Corrections from chat or from the last 24 hours show in "Since you last opened" with one-click undo (§7.7, §9.1, §10.4) |
| **CLR-8** | The mock page's explanation was a placeholder | The mock now shows the invented event-sourcing explanation used in ARCHITECTURE §4, with "you query" rewritten as "is queried" so the sample itself passes V4 (§4.4) |
| **CPLX-8** | Control loops lacked precedence | The Book's sentinels join [MT] §7.2's controller registry with metric, threshold, hysteresis, action and precedence (§8.12) |
| Smaller issues (BOOK, SEC) | One-liners in REVIEW §10 | A trimmed worked example expands in place (§4.2); "Where this fits" falls back to labelled chapter neighbours (§4.4); big pictures fall back to top leaves (§4.5, §8.3); the dotted underline marks the first occurrence per page (§6.2, §10.5); project-bound questions go to the Casebook, calibrated on a developer persona (§4.7, §13.1); a J7 flush rule as [MT] X22 (§8.10); exports sanitised; search kept out of browser history (§10.3) |
| Carried task (c) | Open items in "Fidelity fixes" | Each audit coverage gap now has a status (end of "Fidelity fixes"). §17 rows updated for what has been learned (final-reply loss), reads like a textbook (H22) and local now (DQ-3(a), DQ-4(iii)) |
