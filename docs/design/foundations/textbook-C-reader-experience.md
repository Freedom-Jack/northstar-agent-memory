# Human architecture: the textbook (Design C, reader experience first)

**Status.** Design draft. It goes to adversarial review, then to the user-approval gate (GOAL §7). It is not approved, and nothing is built from it yet.

**Date.** 2026-10-08.

**Angle.** Reader experience first. The design starts from the person opening the book and works back to the core. Two other designers cover the same brief from other angles.

**Authority.** [`docs/GOAL.md`](../../GOAL.md) overrides this document. Where they disagree, GOAL wins and this document is wrong.

**Conventions.**
- Round-2 evidence: [10]–[14] and the synthesis, cited "SYN §x". Round-1 notes [01], [02], [07] are used for evidence only.
- Invariants I1–I20 and jobs J0–J11 are from [13]. I21 is the correction-precedence invariant proposed in SYN §3.2.
- Product facts carry an ID, P1–P14. Each ID resolves to a URL and the date it was checked, in §19. "(Unv)" marks an unverified product fact.
- Numbers marked "estimate" are this design's own, not measured.
- No personal data appears here. Examples use invented content.

---

## 0. The design on one page

- **What it is.** The human side is a **book the AI writes and keeps current**. It has parts, chapters, sections and short entries, compiled from the shared core's leaf items. The person reads it. Nothing asks them to do anything.
- **Where it is read.**
  - Primary: **the Reader**, a local web app served by the core on 127.0.0.1. The same app runs behind sign-in when the core moves to the cloud.
  - In chat: **book cards** built from the same components. They are MCP Apps in Claude Desktop and, pending a spike, ChatGPT Desktop. In Claude Code and Codex they are short text slices plus clickable links.
  - A one-way Markdown export keeps the book readable without the app.
- **The first screen** answers three questions in about five seconds. What changed since I last looked? What am I working toward, and what is next? What did I learn recently? Each block shows at most 7 items.
- **Every sentence names who said it.** A margin rail and short markers show **You**, **an AI** (with model and product) or **an outside source**. Two clicks reach the verbatim span in the conversation. AI-taught knowledge sits in the main text with the same weight as the user's own.
- **What to learn** lives on **learning paths**, one per stated goal. A path shows what was explained, what you used, the next 4–7 things to learn with a reason for each, and the open questions. The same items also appear inside the chapters they belong to.
- **Landmarks stay put.** The table of contents changes only at **editions**, at most weekly. Each edition has notes, redirects and undo. Between editions, new content flows into sections and new sections are appended. Paragraphs whose sources did not change keep identical text.
- **The AI writes it reliably.** The compiler (J7) sees only leaf items. Code rejects any sentence that has no citation, quotes text that is not verbatim, names the wrong speaker, or states a number its sources lack. A verifier of a different model family spot-checks entailment. A section that keeps failing falls back to a plain cited list, never to uncited prose.
- **Corrections take one click**, in the Reader or in a chat card. They are stored as user events that no automated job may undo (I21).
- **Remembering without quizzes.** Gist first; worked examples in the speaker's own words; "how this changed" boxes; time and source cues; stable places; re-encounters through the AI side. One optional aid, a recall fold, is off by default.
- **Cost.** About $15 a month of model calls for the book, at about 36K events a year (estimate, ±2×). This is on top of the core's own maintenance.
- **Evaluation needs no user sessions.** Hard gates (citations, correction survival), AI-said parity, stability, and a simulated reader that must answer "what have I learned about X, and from whom?" from the book better than from raw chats.

### Where each required topic is covered

| Required topic | Section |
|---|---|
| 1. Anatomy of the book | §4 |
| 2. What has been learned | §5 |
| 3. What to learn | §6 |
| 4. Evolution | §7 |
| 5. How the AI writes it | §8 |
| 6. Corrections | §9 |
| 7. Interface and medium | §3, §10 |
| 8. Non-goals | §12, with the optional aid in §11 |
| 9. Core contract and evaluation | §13, §14 |
| 10. Questions and risks | §16, §17 |

---

## 1. What this design must deliver

GOAL §3.2, verbatim:

> **It reads like a textbook.** The AI organizes the knowledge and explains it so the person **understands and remembers** it when they read. Every explanation stays traceable to its sources: who said it, and in which conversation. It is not a quiz or a mastery score.

The user, 2026-10-08, verbatim:

> "the key is to help human understand and remember their knowledge, just like textbooks."

Read as requirements:

| # | Requirement | GOAL anchor |
|---|---|---|
| H1 | Show **what has been learned**, from the user's own thinking and from what AIs taught | §3.2, §4.2 |
| H2 | Show **what to learn**: goals, gaps, open questions, next steps | §3.2, §2 |
| H3 | **Read like a textbook**: organized and explained so the person understands and remembers | §3.2, §2 (2026-10-08), §6 |
| H4 | Every explanation is **traceable** to who said it and in which conversation | §3.2, §6 |
| H5 | The AI builds and reorganizes it. The user may browse and correct. **Nothing is required** | §3.2, §4.1, §4.3 |
| H6 | **Not a quiz, not a mastery score** | §3.2, §2 |
| H7 | A projection over the **shared core**, separate from the AI-facing representation | §4.4 |
| H8 | Works with the **first connectors**, **local now and cloud later** | §4.6 |
| H9 | Stays correct when **one agent loses focus** | §4.7 |

---

## 2. The reader's moments

The design starts from what a person does when they open the book. Each moment drives part of the design and has a test in §14.

| # | Moment | What the reader sees | Design | Test |
|---|---|---|---|---|
| M1 | Opening the book after days away | What changed, what they are working toward, what they learned recently | §10.1 | T-NAV, T-NEW |
| M2 | "What have I learned about X, and from whom?" | An answer page: the best section, a who-taught line, key points with markers, the conversations | §10.3 | SR-1, T-NAV |
| M3 | Reading a chapter to understand it | Sections in prerequisite order; each with a gist, an explanation, examples in the speaker's own words, key ideas | §4.3, §4.4 | T-TEXT |
| M4 | Checking a source | Two clicks from any sentence to the verbatim span, highlighted in its conversation | §5.4 | T-PROV, T-CITE |
| M5 | Telling AI-taught from self-stated at a glance | Margin rail and markers on every sentence; a who-taught line per section | §5.2, §5.3 | T-ATTR, T-PARITY |
| M6 | Seeing what is new | "Since you last opened" on the first screen; new and changed sentences marked inside sections | §7.4 | T-NEW |
| M7 | Seeing what to learn next | A learning path per goal: next 4–7 items, each with a reason | §6 | T-LEARN |
| M8 | Fixing a mistake | One click on the sentence, marker or heading; undo | §9 | T-CORR |
| M9 | Glimpsing the book inside a chat | A card or slice showing the relevant section and what Northstar gave this chat | §10.6 | T-SLICE |
| M10 | "What did I get out of that chat?" | The Sources page lists each conversation and the sections it fed | §10.2 | SR-2 |
| M11 | Seeing how my understanding changed | "How this changed" boxes, a History tab, the book as of a date | §7.5, §7.6 | SR-3 |
| M12 | Never opening it | Nothing breaks. The book stays current, and the AI side still benefits | §8.7 | T-RITUAL |

M12 matters as much as the others. GOAL §4.1 says the system delivers value without rituals. The book is a place to read, not a place that waits for the reader.

---

## 3. The medium: where the book is read

### 3.1 Options compared

| Criterion | (a) Local web app served by the core ("Reader") | (b) Generated static site | (c) Obsidian-compatible vault | (d) MCP App panels only | (e) Published claude.ai artifact page |
|---|---|---|---|---|---|
| Reading quality: typography, markers, hover provenance, side drawer | High | High | Medium. Markdown footnotes; markers and drawers need plugins | Low inline (a card holds 4–5 data points, no drill-ins [P2]); medium in fullscreen | High |
| One-click correction, stored with user origin | Yes. A local write endpoint | No server to receive it | No. File edits cannot be typed as corrections, and two writable copies diverge [07 pitfall 6] | Yes, through app-only tools [P3] | No reliable path; the data lives on claude.ai |
| Freshness | Live from the core | Rebuild needed | Rebuild or sync needed | Live | Republish needed |
| Inside a chat | No (link out) | No | No | Yes: Claude Desktop [P1]; ChatGPT Desktop (Unv) | No |
| Local now | Yes | Yes | Yes | Yes for Claude Desktop through a local stdio server [P13] | No. Personal data leaves the Mac |
| Cloud later | Same code behind sign-in | Host the files; private hosting needed | Third-party sync or publish | Same server, remote | Already vendor-hosted |
| Durability without the app | Needs an export | Plain files | Plain files (best) [02 F8] | None | Vendor-held |
| Risk of turning into an editor | Low | None | High: users edit generated files | Low | Low |
| Build cost for the prototype | Medium | Low | Low | Medium | Low |

### 3.2 Decision

Use three pieces, all fed from one projection in the core.

1. **The Reader (primary).** A local web app served by the core process on 127.0.0.1. It is the only full reading surface. It is also the only place, besides chat cards, that writes corrections.
2. **Book cards (in chat).** One component library renders the Reader's pages. The same components, packaged as MCP App resources, render small cards and a fullscreen book inside Claude Desktop and, pending a spike, ChatGPT Desktop. In terminals (Claude Code, Codex) the slice is text with clickable links (§10.6).
3. **Book export (one-way).** A nightly Markdown export, one file per section, with front matter holding stable IDs and citations as footnotes. It follows Obsidian-compatible conventions, so it opens in Obsidian or any editor, and agents can grep it [07 F12]. Each file starts with "Generated by Northstar. Edits here are not read back." It goes to a folder the user chooses, never the repo.

**Why not a vault as the primary surface.** It is the most durable option, but it fails one-click correction and invites editing. Two writable copies of the same knowledge diverge [07 pitfall 6], and file edits cannot be told apart from accidents or turned into typed corrections. The export keeps the durability benefit without the second writable copy.

**Why not a static site.** It cannot receive corrections and goes stale between builds. The Reader can still produce static snapshots later, for example to share one chapter.

**Why not a claude.ai artifact.** It would put personal knowledge on a vendor's servers. That breaks "local now" for no gain.

**Why not MCP Apps only.** Inline cards are designed for short, focused content, with at most two actions and no deep navigation [P2][P5]. A textbook needs a table of contents, a reading column and a source drawer. Fullscreen MCP Apps can hold those, but only after the model has called a tool in that chat [10 F2], and ChatGPT Desktop support is unverified. The Reader must exist independently of any vendor app.

**One component library, two data adapters.** The Reader fetches JSON from the core's HTTP read API. The MCP App bundle fetches the same JSON through `tools/call` to the Northstar MCP server [P3]. An MCP App never fetches from localhost directly, so it works the same against a local or a cloud core. The framework is an implementation choice; Python 3.14 library support is unverified (SYN §6).

### 3.3 Local now, cloud later, enterprise later

| Stage | Reader | Book cards | Export |
|---|---|---|---|
| Local now | Core on the Mac serves the Reader at `http://127.0.0.1:<port>` | Claude Desktop: from the local `.mcpb` stdio server, so no public endpoint is needed [P13]. ChatGPT Desktop: from whatever endpoint the ChatGPT connector uses (connector design; Unv) | Local folder |
| Cloud later | Cloud core serves the same app over HTTPS behind sign-in | Remote MCP server serves the same `ui://` resources | Download on request |
| Enterprise later | Per-user books, SSO, admin retention policy. Not designed here. Nothing in this design blocks it | Same | Policy-controlled |

The Reader talks to the core only through its read API and correction API, never to SQLite directly. That is what lets it move to the cloud unchanged.

### 3.4 Safety of a local web app

- Bind to 127.0.0.1 only, on a random high port.
- `northstar open` launches the browser with a one-time token that sets a session cookie. No cookie, no data.
- Check the `Host` header on every request (DNS-rebinding guard). No CORS. Write endpoints need a CSRF token and same-origin.
- Treat all captured text as untrusted. AI replies, pasted text and web content can contain HTML or script. Render Markdown through a sanitizer. This is the human-side twin of prompt injection through stored memory (GOAL §5; SYN §5 item 8).
- Respect scopes and sensitivity tiers (I17). Excision (SYN §5 item 9) purges compiled pages, caches, exports and search indexes; a grep afterwards returns 0 hits.

---

## 4. Anatomy of the book

### 4.1 Units

| Unit | What it is | What it contains | Size (estimate, tuned in the pilot) |
|---|---|---|---|
| **Book** | Everything the core holds for this person and scope | Front matter, parts, back matter (§4.2) | One per scope |
| **Part** | A broad domain | A one-line description and its chapters | 4–9 per book |
| **Chapter** | One theme, anchored on a concept, a question or a goal | Opener, sections in reading order, short entries, key ideas, open questions, sources | 3–12 sections |
| **Section** | One concept, explained | The blocks in §4.4 | 150–600 words of body |
| **Short entry** | A concept with little content so far | Label, gist, markers, links. Listed at the end of its chapter, like a glossary entry | One line to one short paragraph |
| **Leaf item** | A Statement or Passage in the core (SYN §3.1) | Not a page. Each sentence on a page cites one or more leaves | n/a |
| **Span** | The verbatim words in a conversation or document | Shown in the source drawer (§5.4) | n/a |

A concept becomes a section when it has enough content (proposed: 5 or more leaf items) or is linked to an active goal. Below that it stays a short entry. This keeps the book from filling with hundreds of thin pages, which is the fragment pile-up the brief warns about (GOAL §1, foundation 2).

### 4.2 Front matter and back matter

| Page | Purpose | Moment |
|---|---|---|
| **Where you are** (first screen) | Since you last opened; working toward; recently learned; contents | M1 |
| **Contents** | Parts, chapters, sections as a collapsible tree | M1, M3 |
| **Learning paths** | One per active goal (§6) | M7 |
| **Open questions** | All unresolved questions, grouped by chapter | M7 |
| **What's new** | The full change feed, by date and chapter | M6 |
| **Index** | A–Z of concept labels and aliases, each pointing to one to four entry points [02 F1] | M2 |
| **Glossary** | Definitions, each with its speaker. Differing definitions sit side by side | M3, M5 |
| **Sources** | Every conversation and document, by product and date, each listing the sections it fed | M10 |
| **Timeline** | Learned this week, this month; supersessions; goal changes | M11 |
| **Edition notes** | What each edition reorganized, with undo | M1, M11 |

### 4.3 Chapter anatomy

```
Part I  Building software                          Chapter 3  Event sourcing
------------------------------------------------------------------------------
What this chapter covers   (one cited paragraph, compiled from leaf items)
Connects to your goals     "Ship the prototype": 3 sections here are on that path
Changed since you last read  2 sections changed, 1 new   [show]

  3.1  Event logs                     C C Y
  3.2  Projections          new: 2    C G Y
  3.3  Snapshots                      C
  3.4  Replay and repair              G Y
  Short entries: Idempotency key, Watermark, Compensating event

Key ideas of this chapter   (5-7 cited sentences; leaves picked by code)
Open questions in this chapter   (3)
Where sources disagree           (1)
Sources for this chapter         (9 conversations)
```

- Sections are in **reading order**: prerequisite order first, then the date the user first met each concept. That makes the chapter tell the story of how they learned it, where prerequisites allow.
- **Key ideas** are compiled from leaf items that code picks (most cited, most independent lineages, goal-linked). They are never written from the section text (I7).
- Markers after each section title (C, G, Y) show at a glance who taught it (§5.2).

### 4.4 Section anatomy

Blocks appear only when they have content.

| Block | Content | Voice | Why |
|---|---|---|---|
| Title and gist | Concept label; one cited sentence, "In one line" | Northstar's wording, cited | Gist persists in memory [01 F1] |
| Who taught this | "Claude 6 · ChatGPT 2 · You 2 · sources 1" | Counts of cited leaves by speaker | At-a-glance attribution (M5) |
| Explanation | Paragraphs of compiled prose. Every sentence carries markers | Northstar's wording, every sentence cited | The textbook body (H3) |
| In their words | One to three verbatim excerpts: an AI's worked example, analogy or procedure, or the user's own statement | **Verbatim**, with speaker, model, product, date | Worked examples; keeps AI teaching as passages [12 decision 2] |
| Your own thinking | What the user stated or concluded, quoted and dated | Verbatim | Keeps the user's words distinct (H1) |
| How this changed | Refutation-style box: what was held, what replaced it, why, and why the old view seemed right | Cited | Old beliefs persist unless co-activated and explained [01 F5] |
| Where sources disagree | "Claude said A (12 Sep). ChatGPT said B (3 Oct). Unresolved." Both sides attributed | Cited | Contested items are never hidden (SYN §3.1 step 5) |
| Builds on / Leads to | Prerequisite links. Low-confidence direction shows as "Related" | Structure | Integration links [01 F7]; reading order |
| Open questions here | The user's unresolved questions, and questions spawned by disagreements | Verbatim question, dated | Gaps are first-class (§6.3) |
| How you engaged | Encountered, explained to you, asked about, used, restated, confused; each with links to evidence | Plain words, no numbers or bars | Engagement, not mastery [12 F10] |
| New, not yet woven in | Leaf items that arrived after the last compile, shown as cited lines | Leaf gist, cited | Freshness without waiting for the nightly compile (§8.7) |
| Sources | The conversations and documents this section cites | List | Traceability (H4) |

```
Part I > Ch 3 Event sourcing > 3.2 Projections              [History] [...]
------------------------------------------------------------------------------
Projections                       Taught by: Claude 6 · ChatGPT 2 · You 2
In one line: a projection is a read model rebuilt from the event log.   [C]

 C | A projection reads the event log in order and builds a table      [C]
   | shaped for one kind of question.
 C | Because it is derived, it can be dropped and rebuilt at any time.  [C][G]
 Y | You concluded that the reading view and the AI's context should    [Y]
   | be two projections over one log.

 +- In their words - Claude (Opus 5.5) in Claude Code, 12 Sep, verbatim -----+
 | "Think of the log as the bank statement and each projection as a          |
 |  budget you can redo from the statement whenever you like."               |
 +---------------------------------------------------------------------------+
 +- How this changed --------------------------------------------------------+
 | Before (you, 2 Sep): "Pages should be edited in place."                   |
 | Now: pages are rebuilt from the log. Why: in-place edits drift. [C][G]    |
 +---------------------------------------------------------------------------+
Builds on 3.1 Event logs  ·  Leads to 3.3 Snapshots (on your path)
Open question here: "When should a projection be snapshotted?" (you, 3 Oct)
How you engaged: explained to you, asked about, used
Sources: 4 conversations
```

### 4.5 Why this shape helps understanding and remembering

| Book feature | Why it helps | Evidence |
|---|---|---|
| A tree of parts, chapters and sections; 4–7 items per overview block | Working memory holds about 4 chunks; chunked overviews with drill-down reduce load | [01 F9] (Cowan 2001), [01 Impl 9], [12] Model C views |
| Chapters anchored on a concept, question or goal, in prerequisite order | Experts organize by principle, not surface topic. Material sticks when a live question pulls it in | [01 F9] (Chi et al. 1981), [02 F6], [12 F11] |
| Gist line first, verbatim excerpt alongside | Gist and verbatim traces are stored in parallel. Gist persists; verbatim lets you re-interpret | [01 F1] |
| Worked examples kept as verbatim AI passages | Most AI teaching is explanation, procedure, example or comparison; atomizing it loses it | [12 decision 2], [12 F3] |
| "How this changed" in refutation form | Old beliefs are not erased. Revision needs co-activation, an explicit link and a causal alternative | [01 F5], [01 idea 5] |
| Builds on, leads to, see also | Integration links reduce retrieval-induced forgetting among related items | [01 F7] |
| Stable places, titles and addresses | People re-find by recognition and location. Churn destroys that | [02 F2], [07 F10], [12 F16], [02 idea 1] |
| Dates, products and conversation titles on markers; a timeline | Time and people are major retrieval cues | [12 F15] (Dumais et al. 2003) |
| Sources one click away; verification status visible | Sources reduced over-reliance on wrong AI answers. Explanations alone raised it | [12 F8] (Kim et al. 2025) |
| Trees, outlines, timelines. A local graph is optional. No global graph | Global graphs lack evidence and become hairballs; trees and local graphs have support | [12 F15], [02 pitfall 4] |
| An index of a few entry points, not exhaustive tags | Luhmann's index listed one to four entry cards per keyword, then relied on links | [02 F1], [02 idea 3] |
| A visible "what Northstar gave this chat" | People react with curiosity to visible memory and with discomfort to opaque memory | [07 F9] |

The limit is honest. The user reads a structure the AI built, which helps learning less than building it (g = 0.43 against 0.72) [12 F14]. GOAL §4.3 chose AI management, so this design does not shift the work to the user. It is RISK 17 (§17).

### 4.6 How the structure is chosen

The structure is a projection maintained by J8, under the rules in SYN §3.2 and [12 decision 8].

- **Clustering.** Concepts are clustered into chapters and parts with evolutionary clustering: a quality term plus a stability cost that penalizes departure from the current structure [12 F16]. Matched clusters keep their IDs.
- **Anchors.** Each chapter gets an anchor type: concept (default), question (when an open question gathers many items) or goal (when a goal's subgraph is the clearest theme). This follows "organize around questions, principles and models, not topics" [01 Impl 9].
- **One home, many links.** A concept may belong to several chapters, but the book shows one home section. Other chapters list it as an "Also in" cross-reference, never duplicated text [12 decision 5].
- **Labels.** Part and chapter labels are navigation labels, not claims [12 F4]. An LLM proposes them. A code check requires each label's content words to come from member concept labels or aliases, so a label cannot invent a topic. User-fixed labels always win (I21).
- **Reading order.** Topological order over prerequisite edges whose direction was checked and whose confidence is above a threshold. Ties break by first-encounter date. The order is frozen between editions.
- **Blast radius.** An edition may move at most a set share of sections (proposed: 5%), under I13. A larger change is split across editions or quarantined.

---

## 5. What has been learned: attribution on the page

### 5.1 Three speakers and one narrator

The book has four voices, and the reader can always tell them apart.

| Voice | Who | Where it appears | Rule |
|---|---|---|---|
| **You** | The user's typed words (`user_typed`) | Markers, "Your own thinking", "In their words" | A sentence that says "you concluded" or "you hold" must cite a user-typed leaf (§8.4) |
| **You pasted** | Text the user pasted from elsewhere (`user_pasted`) | Markers say "You pasted (from …)" | Never shown as the user's own thinking [12 R8] |
| **An AI** | `assistant(model, product)` | Markers, "In their words" | Shown as AI-said, with model and product. Same weight as the user's items (§5.6) |
| **A source** | An external document or page (`external_source`) | Markers, "In their words" | Shown with its title and locator |
| **Northstar** (narrator) | The compiler's own wording | The explanation prose | Never a source. It adds no content beyond its cited leaves. The section header says "Explained by Northstar from 11 sources" |

The narrator is named because it is also an AI. Hiding that would blur exactly the line GOAL §3.2 asks the book to keep: who said what.

### 5.2 Markers and chips

| Element | Looks like | Holds | On hover or click |
|---|---|---|---|
| Speaker marker | `[C]` `[G]` `[Y]` `[S]` after each sentence; a margin rail letter per sentence group | Speaker of each cited leaf. C = Claude model, G = OpenAI model, Y = you, S = outside source. Later agents get their vendor's letter | Full chip: "Claude Opus 5.5 · Claude Code · 'Northstar core design' · 12 Sep" |
| Verification chip | Small text: `checked`, `contradicted`, `mixed`, `unchecked`, `opinion`, `AI-cited, unchecked` | The verification axis, separate from speaker [12 decision 1] | Verifier model, query, evidence, date |
| Stance chip | `you accepted`, `you questioned`, `you disputed`, `you rejected` | The user-stance axis | The span where the user reacted |
| Capture chip | `verbatim`, `model-reported`, `reconciled` | Capture fidelity (SYN §3.1) | Which channel captured it (§5.5) |
| Status chip | `provisional`, `contested`, `superseded`, `you marked wrong` | Rank and correction state | Reason and date |

**Never colour alone.** Every marker is a letter and every chip is a word. Colour is a second cue, and both themes are supported.

**Density.** The default shows one marker per cited speaker per sentence and chips only when they say something unusual (for example `unchecked` on an AI-said claim, or `contested`). "Show all chips" is a reader setting. Attribution can be made quieter, but never removed.

### 5.3 Telling AI-taught from self-stated at a glance

Three levels, from coarse to fine:

1. **Contents and chapter pages.** Markers after each section title show who taught it (C C Y).
2. **Section header.** "Taught by: Claude 6 · ChatGPT 2 · You 2 · sources 1." These are counts of cited leaves, not a score.
3. **Margin rail and sentence markers.** Each sentence group shows the speaker letter in the margin. Mixed sentences show several markers.

### 5.4 From any sentence to the verbatim span

The path is at most two clicks.

1. Click a marker. The **source drawer** opens beside the text.
2. The drawer lists each cited leaf. For each it shows the speaker, model, product, conversation title, date, capture fidelity and verification. It shows the anchored quote highlighted inside its conversation excerpt, with the turns around it.
3. "Open full conversation" opens the core's own copy of the transcript at that message. It comes from the immutable source store, so it works without the vendor app.
4. "Open in product" is a convenience link where a deep link exists: `claude --resume <session>` for Claude Code [10 F5]; a conversation URL for Claude or ChatGPT chats (Unv); `codex resume <id>` for Codex (Unv).

```
+- Source --------------------------------------------------------------+
| "Because it is derived, it can be dropped and rebuilt at any time."   |
| Cites 2 items                                                          |
| 1  Passage · AI-said · Claude Opus 5.5 · Claude Code                   |
|    "Northstar core design" · 12 Sep 14:03 · verbatim · opinion         |
|    You: "so can I just delete it?"                                     |
|    Claude: "Yes. [A projection is disposable; rebuild it from the      |
|    log] whenever the schema changes."                                  |
|    [Open full conversation]  [Open in Claude Code]                     |
| 2  Statement · AI-said · GPT model · ChatGPT Desktop · 3 Oct           |
|    model-reported (verbatim not yet available) · unchecked             |
|    ...                                                                 |
| [Not right]  [Wrong speaker]  [Wrong conversation]                     |
+------------------------------------------------------------------------+
```

The drawer shows the anchor exactly as the core holds it: `{source_type, source_id, locator, quote, prefix, suffix}` (SYN §3.1). Quotes are exact substrings of the span (I2). A non-chat source shows its document title and page or character range in the same drawer, with no special case. That is how the book takes in reading and work later (GOAL §3.1).

### 5.5 Capture fidelity on the desktop chat surfaces

The 2026-10-08 answer makes Claude Desktop chat and ChatGPT Desktop chat first connectors. On both, live capture is the model's own paraphrase through MCP. Verbatim text arrives later, or not at all (SYN Table A; RISK 4). Solving capture is the core and connector designers' job. The human side has three duties:

1. **Never show a paraphrase as a quote.** "In their words" boxes and the drawer's highlighted quote use only `verbatim` or `reconciled` spans. A `model-reported` item shows as "Claude's own account of what it said, not verbatim".
2. **Upgrade in place.** When verbatim text arrives (sync, export backfill, reconciliation by message ID), the item keeps its ID. The chip changes to `reconciled`, and the next compile may quote it.
3. **Show the gap.** The Sources page shows, per conversation, how much was captured verbatim. A desktop chat with only model-reported capture says so.

One dependency is unverified. "Which conversation" attribution on desktop chats needs the connector to learn a conversation identity during the chat. If MCP calls do not carry one (Unv), the core must assign a provisional episode ID and reconcile it later. Until then the drawer shows "Claude Desktop chat, 3 Oct, conversation not yet identified" (§15, S-R7).

### 5.6 AI-taught knowledge stays first-class

GOAL §4.2 is the rule. These mechanisms enforce it on the page:

- AI-said leaves are cited in the main explanation, not in an appendix or a collapsed "AI said" block.
- "In their words" boxes favour AI worked examples, because explanations and examples are what AIs mostly teach [12 decision 2].
- Rank, not speaker, decides what the body cites. For claims about the world, speaker is not a ranking factor (SYN §3.1 step 3). Speaker decides only for what the user holds about themselves.
- Unchecked AI claims stay in the body with an `unchecked` chip. They are not hidden.
- A contradicted AI claim moves to "How this changed" or "Where sources disagree", with its reason. It is never silently dropped (I9).
- **AI-said parity check** (T-PARITY, §14). The AI-said share of leaves cited in section bodies must track the AI-said share of promoted leaf items. A drop is an alert, like the core's AI-said share sentinel [13].

### 5.7 Past beliefs as quoted, dated records

A system that narrates someone's past beliefs in fluent prose can implant false memories. An LLM interviewer produced more than three times the false memories of a control, and they persisted at one week [01 F11] (Chan et al. 2024). So:

- Statements about what the user believed, concluded or decided are **quoted and dated**, not paraphrased: 'In your words, 2 Sep: "Pages should be edited in place."'
- The compiler may write "you concluded that…" only when the cited leaf is user-typed with stance `asserted` (§8.4).
- The compiler never infers the user's reasons. Inferred rationale matched the real one with a precision of only about 0.27 (SYN §5 item 1).

---

## 6. What to learn

### 6.1 Goals and learning paths

Each **active goal** has a learning path. Goals are only those the user stated. Inferred interests are kept apart as "possible interests" and decay, because models over-infer 35–49% of user attributes [07 F7] [12 decision 7].

```
Learning path: "Ship the Northstar prototype"
Your goal, stated 7 Oct in Claude Code ("I want to ship ...")       [Not my goal] [Done]
------------------------------------------------------------------------------
Next to learn (5)
  1  MCP Apps model context    Why: 2 open questions depend on it; Claude used
                               the term 3 times without explaining it
  2  Batch API                 Why: builds on 3.2 Projections, which was explained to you
  3  ...
Explained to you (12)    3.1 Event logs, 3.2 Projections, ...            [show]
You have used (5)        3.2 Projections, ...                            [show]
Later: needs something first (8)                                         [show]
Open questions on this path (4)                                          [show]
```

- A path is an **ordered outline**, not a graph. It groups the goal's concepts by how the user engaged with them.
- It shows **no percentages, progress bars or completion scores** (H6).
- Each item links to its section. If no section exists yet, it links to a **stub**: what the core already holds on it (cited) and why it is next.

### 6.2 The frontier and next steps

- **Frontier.** The outer fringe of the goal's subgraph: concepts whose prerequisites have all reached at least "explained to you", and which have not reached it themselves [12 F11] [12] Model C step 4. It is computed by code. The path shows 4–7 of them [01 F9].
- **Ranking.** Code ranks frontier items by goal relevance, how much they unblock, open questions that depend on them, recency and the need for verification [12] Model C step 6.
- **Reasons are always shown**, in plain words, from a fixed set: prerequisite gap, open question, used without being explained, relied on while unverified, sources disagree [12] Model C `NextStep.reason`. A reader can judge an item whose reason they can see.
- **Next steps are not tasks.** Nothing is assigned, due or counted. The AI side carries frontier items into new chats through the pack (SYN §3.4), so the next step happens in normal work.
- **"I already know this"** is a one-click override (§9). It records a user engagement override [12] Model C and removes the item from the frontier.

### 6.3 Open questions and gaps

| Kind | Source | Shown as |
|---|---|---|
| Your open questions | Questions the user asked that never got a satisfying answer. The best free signal of a gap [12 F12] | The question in the user's words, dated, linked to the chapter |
| Questions from disagreement | A contested Tension spawns a Question (SYN §3.1 step 5) | "Claude and ChatGPT disagree on X" with both sides |
| Used but never explained | Concepts an AI used in explanations but never explained, or that the user later asked about [12] Model C step 5 | "Came up 3 times, never explained" |
| Relied on while unverified | AI-said, unchecked, then used by the user | `unchecked` chip plus "you used this" |

Open questions are a **record of real gaps**, not a to-do list. They close automatically when a later answer resolves them, or with one click ("Answered", "Not a question any more").

### 6.4 How "to learn" connects to "learned"

| From | To | Link |
|---|---|---|
| Goal | Path | One path per active goal |
| Path item | Section or stub | Each item opens its section |
| Section | Path | "On your path to <goal>" banner; "Leads to" links |
| Section | Open questions | "Open questions here" block |
| Open question | Answering items | When answered, the question shows the cited answer and moves to History |
| Disagreement | Question | Spawned automatically, linked both ways |
| First screen | Paths | "Working toward" block with the top frontier items |

### 6.5 Handling noisy prerequisites

LLM prerequisite extraction reaches only F1 70.2–76.2, and reversed direction is a main error [12 F11]. The design limits the damage:

- Direction is checked in a separate pass. An edge that fails the check renders as "Related", not "Builds on".
- Paths show each item's reason, so a wrong edge is visible.
- One click rejects an edge ("Doesn't build on this"), stored as a correction (§9).
- Frontier predictive validity is measured passively (T-LEARN, §14). If it does not beat a popularity baseline, the frontier is redesigned, never removed (SYN §7, ablation rule). That is RISK C9.

---

## 7. Evolution without losing the landmarks

### 7.1 What may change, and when

| Change | Between editions | At an edition |
|---|---|---|
| New leaf appears in a section | Yes: at once in "New, not yet woven in"; woven at the next compile | n/a |
| Section text recompiled | Yes, only paragraphs whose leaf group changed (§7.3) | Same |
| New section (entry promoted) | Yes: appended at the end of its chapter, marked "new" | Moved to its reading-order place |
| New chapter | Yes: appended at the end of its part, marked "new" | Placed properly |
| Section moves chapter, chapters merge or split, parts change | No | Yes, within the blast-radius cap |
| Labels renamed | No, unless the user renames | Yes, if the stability rule allows |
| A user's move, rename or pin | Yes, at once (user actions never wait) | Kept as a hard constraint (I21) |

New material is inserted without moving old material, much as Luhmann branched a new card after an existing one without renumbering the rest [02 F1].

### 7.2 Editions

- **Cadence.** At most one edition a week. An edition runs only if the reorganization gain beats the stability cost by a threshold, calibrated on the golden set.
- **Edition notes.** Every edition writes a page: what moved, merged, split or was renamed, and why. It lists every change with a one-click "Undo this change".
- **Redirects.** Every old address keeps working. A merged or moved section redirects to its new home and shows "Moved here from Chapter 4 in edition 12".
- **Undo.** Every reorganization is a typed event with before and after, undone by a compensating event (SYN §3.2). Undo by the user also records a placement constraint, so the next edition does not redo it.
- **Stable addresses.** URLs use permanent IDs (`/s/<section-id>`). Display numbers like "3.2" are for reading and may change at editions [02 idea 1].

### 7.3 Text stability: paragraph memoization

Recompiling a page with an LLM rewords it every time. That would make everything look changed and erode recognition. The fix:

- Each compiled paragraph records the hash of its **leaf group**: the leaf IDs and versions it cites, the model and the prompt hash.
- When a section is recompiled, the compiler receives the **paragraph plan** of the last version: ordered lists of leaf IDs, never prose.
- Code keeps, byte for byte, every paragraph whose leaf group is unchanged. The LLM writes only paragraphs whose leaf group changed.
- This is reuse of a recorded output for an identical input (I14, I18), not summarizing a summary. The generator never receives earlier page text (I7).
- Result: a section whose sources did not change keeps identical text. Measured by T-STAB (§14).

### 7.4 What changed since you last read

- The core keeps a **last-read watermark** per section for each reader: local, private and never used for any score.
- Changes are computed from **cited leaf sets**, not from text diffs:
  - **new**: a sentence cites a leaf the reader has not seen;
  - **changed**: a paragraph's leaf group changed;
  - **gone**: a leaf was superseded, contradicted or marked wrong. It now appears in "How this changed".
- Inside a section, new and changed sentences carry a quiet left bar until the reader scrolls past them.
- On the first screen, "Since you last opened" lists at most 5 changes, grouped by chapter, in this order:
  1. changes to things **the user held** (user-said or user-accepted items that were superseded or contested), because co-activating old and new is what updates a person [01 F5];
  2. new disagreements between AIs;
  3. new knowledge, with speaker counts ("Event sourcing: 4 new ideas, 3 from Claude in Claude Code, 1 yours").
- A reader who has never opened a section sees "new" relative to their last visit to the Reader overall.

### 7.5 How this changed, and contested knowledge

- **How this changed** boxes use the refutation form: old claim, new claim, what refuted it, why the old one seemed right, and the evidence [01 idea 5]. The core must hold these fields (§13).
- The box shows in the section body the first few times the reader opens it after the change (proposed: three visits or 30 days). Then it folds into History. Old and new are co-activated for a while, and then the past steps out of the way.
- **Contested** items show both sides with attribution and the spawned Question (SYN §3.1 step 5). They are content, never a task.
- **Superseded** items are never deleted. They remain in History and in the as-of view (§7.6) as antibodies (SYN §5 item 3).

### 7.6 How understanding evolved over time

- **History tab** on every section: a dated list of events. First encountered (conversation, product); explained by; you asked; you restated; superseded; contested; verified; moved at an edition; corrected by you.
- **The book as of a date.** The Reader can render any section, chapter or the contents as of a past date, from recorded page versions and the ledger's as-of queries (SYN §5 item 3). Nothing is regenerated for this.
- **Timeline** page: what was learned each week and month, supersessions, and goal changes.
- All three show past beliefs as quoted, dated records (§5.7).

### 7.7 Dormancy and the archive shelf

A store that faithfully preserves every past self can weigh on the present [02 pitfall 8]. So:

- A chapter with no new leaves for a set time (proposed: 6 months) and no link to an active goal moves to an **Archive shelf** at the end of the contents. This happens at an edition, under a fixed rule.
- Its address does not change. It stays searchable, and new activity brings it back at the next edition.
- The first screen never shows archived chapters unless something in them changed.

---

## 8. How the AI writes the book reliably

### 8.1 Pipeline

```
 core ledger (leaf items, best rank, attribution axes, corrections)
        |
        v
 J8  structure (editions)  ---->  book nodes: parts, chapters, sections, entries
        |
        v
 dirty tracker (code): leaf change -> concept membership -> section, chapter
        |
        v
 input assembler (code, I7): leaf items + spans + paragraph plan (IDs only)
        |
        v
 J7 compile worker (LLM, stateless, schema-constrained proposal)
        |
        v
 validators (code, 100%)  --fail-->  drop sentence | re-run fresh | fall back to cited list
        |
        v
 entailment spot-check (verifier of a different family, sampled)
        |
        v
 recorded page version (inputs, model, prompt hash, sentences with citations)
        |
        v
 Reader / book cards / export   (render only; no generation at read time)
```

### 8.2 Inputs: leaf items only

- The input assembler type-checks that it receives only leaf items (Statements, Passages, Agenda items) at best rank, their spans, their attribution, stance and verification axes, and active corrections. It never passes earlier page text, chapter text or another section's prose (I7).
- **Chapter "Key ideas"** and **"What this chapter covers"** are compiled from leaf items that code selects. They are never compiled from section text. No level of the book summarizes a lower level's prose. This avoids the summary-of-summaries trap of GraphRAG and RAPTOR, where 4% of RAPTOR summary nodes were hallucinated [12 F4].
- **Part descriptions** are one line each, compiled from the leaves behind the part's most-cited concepts, or left as navigation labels.
- **The paragraph plan** (ordered leaf-ID groups from the last version) is the only structural carry-over. It contains no prose.

### 8.3 Output contract

The worker returns a schema-constrained proposal:

```yaml
section_id: s_7Q3
version_of_plan: 41
paragraphs:
  - plan_id: p1                    # reused id when the group is unchanged
    leaf_group: [st_91K@3, ps_7Q2@1]
    sentences:
      - text: "Because it is derived, it can be dropped and rebuilt at any time."
        cites: [ps_7Q2, st_91K]
        role: explain              # define | explain | example_ref | contrast | change | dispute
```

Structured outputs guarantee syntax only [13 F6]. Everything else is checked by code below. Whether J7 uses the Citations API or structured outputs with code-checked IDs is spike S7 (SYN §4).

### 8.4 Validators (code, on 100% of sentences)

| # | Check | Rejects | Basis |
|---|---|---|---|
| V1 | Every sentence cites at least one leaf | Uncited sentences | I8 |
| V2 | Every cited ID is in the input set and active, or explicitly historical in a "How this changed" sentence | Invented or stale citations | I8, I7 |
| V3 | Text in quotation marks is an exact substring of a cited verbatim span | Fabricated or altered quotes | I2 |
| V4 | Speaker phrases ("Claude explained", "you concluded", "ChatGPT said") match the speaker axis of the cited leaves | Misattribution | I3 |
| V5 | "You concluded / believe / decided" requires a user-typed leaf with stance `asserted` | AI-said or pasted text credited to the user; false-memory narration | I4, §5.7 |
| V6 | Every number, date and proper name in the sentence appears in a cited leaf or span | Invented specifics | Design rule; generated summaries invent details (4% of RAPTOR summary nodes) [12 F4] |
| V7 | If a cited leaf carries a hedge, the sentence carries one | Lost hedges | I10 |
| V8 | Unchecked or contradicted AI-said claims keep their chip in rendering | Hidden uncertainty | §5.6 |
| V9 | The section still covers every leaf it covered before, unless a recorded event explains the drop | Silent coverage collapse | I9 |
| V10 | No leaf hidden or marked wrong by the user is cited, except in History | Corrections undone by the compiler | I21 |
| V11 | Length and structure bands per block (gist one sentence; body 150–600 words) | Bloat, fragment dumps | §4.1 |

### 8.5 Entailment spot-checks

- A verifier of a **different model family** checks whether the cited leaves entail each sampled sentence. The working assumption is a local open-weight model on the Mac (SYN §3.5, spike S10).
- Sampling: 100% of sentences that cite AI-said unchecked or contested leaves; 100% of sentences in "How this changed" and "Where sources disagree"; 20% of the rest (proposed, recalibrated in the pilot).
- A failed sentence is removed and the section is flagged. Failure rates feed the error budget [13]. The daily L4 audit by the strongest model samples compiled sections too.
- **Faithfulness over regenerations.** Hedges and rare details must survive N regenerations of the same section [S1 E7] (SYN §7.3).
- If the local verifier fails its calibration bar, entailment checks are not independent of the writer's family. That is RISK 18, inherited, and the user is told (§17).

### 8.6 Failure handling and graceful fallback

1. A rejected sentence is dropped. If the remaining text still covers the leaves, the paragraph is kept.
2. If more than a set share of sentences in a section fail (proposed: 20%), the section is re-run in a fresh call, possibly on another model.
3. After 3 failed attempts, the section renders in **plain-list mode**: its leaf items as cited lines (gist, markers, chips), in reading order. It is less readable, but always correct.
4. The book never shows uncited prose. A degraded section says so quietly: "Shown as a list while the explanation is rebuilt."
5. The fallback rate is a monitored metric (T-FALLBACK, §14).

### 8.7 Incremental recompile and freshness

| Stage | When | Path |
|---|---|---|
| Provisional item from a live chat | Within about a minute on hook surfaces | Shown only on the first screen's "Today, provisional" strip, labelled provisional (SYN §3.3, AD10) |
| Leaf item promoted by the slow lane | About 2 hours after the chat [13] | Appears at once in its section's "New, not yet woven in" block |
| Woven into prose | Nightly compile, on the Batch API | Paragraph memoization keeps everything else identical |
| User correction | Within about a minute | A non-batch "fast refresh" of affected sections only |
| Edition | At most weekly | J8 within the blast-radius cap |

- Dirty tracking runs from leaf to concept membership to section and chapter. Each dirty section is compiled at most once per nightly batch.
- If the reader never opens the book, all of this still runs. The AI side uses the same leaves and does not depend on the book (M12).

### 8.8 Cost at about 36K events a year

| Quantity | Value | Basis |
|---|---|---|
| Ledger events | About 36K a year, about 100 a day | SYN §3.1 |
| New leaf items | About 30 a day, about 11K a year | Estimate |
| Book at year end | About 1.2K concepts, 400 sections, 50 chapters, 5–9 parts | Estimate (§4.1 thresholds) |
| Dirty sections | About 20 a day | Estimate: daily work clusters in a few topics |
| Tokens per section compile | About 6K in (2K of it a cached prefix), about 2.5K out including thinking | Estimate from block sizes |
| Writer model | Sonnet 5.5 on the Batch API: $1 in, $5 out per million tokens; cached reads $0.05 after the batch discount | [13] assigns J7 to Sonnet 5.5; prices [P12] |

| Item | Per day | Per month |
|---|---|---|
| Section compiles: 20 × about $0.017 | $0.34 | about $10 |
| Chapter key ideas and overviews: about 5 × $0.01 | $0.05 | about $1.50 |
| Labels at editions | n/a | under $0.50 |
| Fast refreshes after corrections: about 3 a day at standard (non-batch) price | $0.10 | about $3 |
| Entailment checks on a local verifier | $0 API | $0 (about $0.30 if run on Haiku 5.5 batch instead) |
| **Total** | | **about $15 (±2×)** |

- With Opus 5.5 as the writer ($2 in, $10 out on batch [P12]), the total is about $30 a month.
- A **full rebuild** of about 450 sections and chapters costs about $8 on Sonnet 5.5 batch. It runs after a prompt or model change, once canaries pass.
- Search embeddings run locally (model choice open).
- These costs are on top of the core's capture and maintenance, which [13 F11] estimated at about $12–40 a month at older prices.

### 8.9 What the maintainer checks

| Sentinel | Alert when | Why |
|---|---|---|
| Citation closure | Any rendered sentence lacks a valid citation | Hard gate; should be impossible after V1–V2 |
| Validator reject rate | Rises above its baseline | A worker is losing focus or a prompt broke |
| Entailment failure rate | Above budget on a rolling 7 days | Semantic drift in the writer |
| AI-said parity | AI-said share of cited body leaves falls more than 10 points below the promoted-leaf share | AI-taught knowledge quietly demoted (§5.6) |
| Plain-list fallback rate | Above 5% of sections | Compile quality falling |
| Stale sections | Any section dirty for more than 48 hours | Book falling behind |
| Text churn without leaf change | Any | Memoization broken (§7.3) |
| Edition churn | Over the blast-radius cap; any A→B→A oscillation within 4 editions | Landmarks eroding (RISK 15) |
| Correction survival | Any active correction violated in any rendered page | Hard gate (I21) |
| Unplaced pool | Grows week on week, or any item older than 7 days | Fragment pile-up |
| Compile cost | Above the monthly budget | Churn or runaway retries |

All sentinels are code. None asks the user to do anything (SYN §3.5).

### 8.10 When one worker loses focus

- Workers are stateless. Each compile sees one section's leaves and nothing else, so an error stays local.
- Every structural rule is code (V1–V11, I7–I10, I13, I21). A degraded worker can produce bad prose, but not uncited, misattributed, misquoted or correction-violating prose.
- Semantic errors (a cited sentence that subtly misstates its leaf) are caught only statistically, by entailment sampling and the daily audit. That is RISK 6, inherited.
- Rollback by job, batch or model re-renders affected pages from recorded outputs, hash-identical (I18). Fault injection tests this (§14.5).

---

## 9. Corrections

### 9.1 One click in the Reader

Controls are visible on hover, not buried in menus. Every correction applies at once and shows an Undo notice. An optional note field records the user's words as a user-typed item (I20).

| Target | One-click verb | Event kind (SYN §3.2) | Effect |
|---|---|---|---|
| A cited leaf (from the drawer, or from a sentence with one leaf) | **Not right** | Reject content | Leaves the book body and the AI packs. History shows it as "you marked this wrong". Optional "What's right?" text creates a user item that supersedes it, `reason: user_correction` |
| Speaker marker | **Wrong speaker** (then pick You, AI or Source) | Fix attribution | The speaker is overridden for display and packs. The original adapter role is kept |
| Conversation chip | **Wrong conversation** | Dispute anchor | Marked disputed; the core re-anchors by re-extraction |
| Section | **Doesn't belong here** / **Move to…** | Fix placement (cannot / must) | A move applies at once; a cannot-link constraint binds J8 |
| Section or chapter title | **Rename** (inline) | Rename | The label is fixed |
| Section | **These are different things** | Unmerge | The alias is removed and the concepts split |
| Section | **Same as…** (search) | Must-link merge | Merged as a reversible alias |
| Chapter | **Keep where it is** | Fix placement (pin) | J8 hard constraint |
| Any item | **Hide from book** | Hide | Not shown in the book. Still in the core and packs |
| Prerequisite link | **Doesn't build on this** | Reject relation | Edge rejected; frontier recomputed |
| Goal | **Not my goal** / **Done** / **Paused** | Goal status | Path archived or updated |
| Question | **Answered** / **Not a question** | Agenda status | Moves to History |
| Frontier item | **I already know this** | Engagement override | Removed from the frontier; shown as "you said you know this" |

### 9.2 Through chat

| Surface | How the user corrects | How origin is bound |
|---|---|---|
| Claude Code, Codex | Says so ("that's wrong about X") or runs `/northstar:correct`. The model calls `northstar_correct` with the target ID and the quote of the user's words | Code checks the quote is an exact substring of the hook-captured user prompt (I2, I20) [10 F5][P14]. If it matches, the correction applies |
| Claude Desktop chat | The model calls `northstar_correct`. The result renders a **confirm card** with one button, "Apply", which calls `northstar_apply_correction` | That tool has app-only visibility, so the model cannot call it. Only the user's click in the card applies it [P3]. Support for app-only tools in Claude Desktop is (Unv), spike S-R1 |
| ChatGPT Desktop chat | Same as Claude Desktop, through the ChatGPT plugin | Rendering and app-only tools on ChatGPT Desktop (Unv), spike S-R2 |
| Any surface, as fallback | The model replies with a link to the exact sentence in the Reader | The click in the Reader is the correction |

If a card cannot render, the proposed correction is shown on the affected sentence in the Reader ("You asked to change this in chat on 3 Oct. Apply?") and expires after 7 days. It is never collected into a queue or counted on a badge.

### 9.3 Persistence and precedence (I21)

- A correction is a typed ledger event with holder `user` and origin bound at write time: `reader_click`, `app_click` or `chat_verbatim` (I20).
- **No automated event may undo or contradict an active user correction** (I21, SYN §3.2).
  - J8 takes corrections as hard constraints: must-link, cannot-link, fixed parents, fixed labels.
  - J7 never cites a leaf the user hid or marked wrong (V10). Compiles replay corrections after every rebuild.
  - The pack compiler (J9) carries "marked wrong by the user" items as "do not re-assert".
- A correction is lifted only by the user (Undo) or by excision of its target.
- Corrections become L6 labels for the maintainer (SYN §3.5). Correction survival is a hard gate (T-CORR).

### 9.4 When later evidence conflicts with a correction

The correction stands. The conflict shows as a chip: "A verifier found support for this on 9 Oct. Your correction stands." It is never escalated to the user as a task (SYN §3.2).

### 9.5 Corrections are not in-chat pushback

- **Pushback in a conversation** ("no, I don't think so") is captured by the AI side as a stance event (`disputed`). It does not change verification, because pressure is not evidence and challenged models flip 46% of the time [11 F4] (SYN §5 item 7). The book shows it as a `you disputed` chip.
- **A deliberate correction** through the Reader, a card or `/northstar:correct` is a correction event with I21 precedence.
- The two are kept separate so that the book stays honest about the user's stance without letting casual pushback rewrite knowledge.

---

## 10. The interface

### 10.1 The first screen

```
+--------------------------------------------------------------------------+
| Northstar · Your book       [ What have I learned about ...          ]   |
| 412 sections in 38 chapters · compiled 2 h ago                           |
+------------------+-------------------------------------------------------+
| CONTENTS         | Since you last opened (12 days ago)                   |
| I  Building      |  * Something you held changed: pages are now rebuilt, |
|    software      |    not edited in place                [Y -> C G]      |
|   3 Event        |  * Event sourcing: 4 new ideas        [C C C Y]       |
|     sourcing  2  |  * Claude and ChatGPT disagree on WAL mode   [C | G]  |
|   4 ...          |                                                       |
| II Learning      | Working toward                                        |
|    science       |  "Ship the Northstar prototype" (you, 7 Oct)          |
| ...              |   Next: MCP Apps model context · Batch API · ...      |
|                  |                                                       |
| Learning paths   | Recently learned (7 days)                             |
| Open questions 9 |  * Projections can be dropped and rebuilt   [C] 5 Oct |
| What's new       |  * Your rule: one writer per table          [Y] 6 Oct |
| Index · Sources  |                                                       |
| Timeline         | Today, provisional                                    |
|                  |  * 2 items from this morning's Claude Code session    |
+------------------+-------------------------------------------------------+
```

- Each block holds at most 5–7 items [01 F9].
- The first screen covers both halves of the goal: what was learned ("Since you last opened", "Recently learned") and what to learn ("Working toward").
- Counts describe the book, not the reader. There are no streaks, scores, badges or "items to review".
- A footer line shows maintenance state in neutral words ("Compiled 2 h ago · all checks passing"). It links to a read-only page. It never asks for action.

### 10.2 Navigation

- **Contents tree** on the left: parts, chapters, sections. Chapters with changes show a quiet count.
- **Breadcrumbs** and **previous / next** within a chapter, in reading order.
- **Builds on / Leads to / Also in** links in every section.
- **Index**: A–Z concept labels and aliases, with one to four entry points each [02 F1].
- **Sources**: by product (Claude Desktop, Claude Code, ChatGPT Desktop, Codex, documents), by date and by conversation. Each conversation lists "what came out of this chat": the sections and items it fed (M10).
- **Timeline** and **Edition notes**.
- **Local graph** (optional, per section): two hops, filtered by relation type. There is no global graph [12 F15].
- Full keyboard navigation.

### 10.3 Search: "What have I learned about X, and from whom?"

Search is hybrid (full-text plus embeddings) over concepts, aliases, leaf items and spans. The result is an **answer page**, built deterministically from the projection, with no LLM at read time:

```
What have I learned about "projections"?
Best match: 3.2 Projections (Chapter 3 Event sourcing)
From whom:  Claude 6 (Claude Code 5, Claude Desktop 1) · ChatGPT 2 · You 2 · sources 1
Key points
  * A projection is a read model rebuilt from the event log.            [C] 12 Sep
  * The reading view and AI context are two projections of one log.     [Y]  6 Oct
  * Projections should be versioned with the schema.        [G] unchecked  3 Oct
Also mentioned in: 3.3 Snapshots · 7.1 Search indexes
Conversations (5) ·  Open questions (1) ·  Changes (1)
```

An optional "Ask your book" mode (later, not P1) could answer free questions with an LLM. If built, it must pass the same citation validators as J7.

### 10.4 Reading a chapter

- A reading column of about 70 characters, a margin rail for speaker letters, and a source drawer that slides in from the right.
- The chapter opener tells the reader what the chapter covers and how it connects to their goals.
- Sections follow in reading order. Short entries close the chapter like a glossary.
- Key ideas, open questions, disagreements and sources close the chapter.

### 10.5 Inspecting a source

See §5.4. The drawer keeps the reader in place. "Open full conversation" opens the core's transcript view in a new tab, scrolled to the message, with the quote highlighted.

### 10.6 Glimpses inside a chat

The glimpse is optional. It adds value, and nothing depends on it.

**What a glimpse shows.**
- **"This chat draws on" card**: rendered when the model fetches the chat-start pack (`northstar_resume`). It names the goal and the items Northstar delivered, by chapter and speaker ("5 items: 3 AI-taught, 2 yours, from 3.2 Projections and 4.1 …"). This is the context receipt made visible [07 F9][10 Impl 11].
- **Book card**: on request ("show my book on projections"), the section's gist, up to 3 key points with markers, and two actions: **Open in book** and **Correct…** [P2][P5].
- **Fullscreen book**: the Reader's components in an MCP App fullscreen view, with contents in a collapsible sidebar [P2].
- **Confirm card** for corrections (§9.2).

**Per product.**

| Product | Channel | How it appears | Status |
|---|---|---|---|
| **Claude Desktop chat** | MCP App from the local `.mcpb` server: inline card, fullscreen | The model calls a Northstar tool that declares a `ui://` resource. Claude asks once to display it; "Always allow" removes the prompt for later chats [P1]. "Open in book" uses `ui/open-link`, which opens the Reader in the default browser [P3] | Local MCP Apps render inline in Claude Desktop [P1]. App-only tools in Desktop (Unv). The card appears only after a tool call, which is model-dependent [10 F2] |
| **ChatGPT Desktop chat** | MCP App or Apps SDK widget: inline, fullscreen. A thread side panel through OpenAI's MCP Extensions is possible later | The plugin is invoked with `@` or chosen by ChatGPT for the task [P6]. The endpoint must be reachable (connector design) | ChatGPT is listed as an MCP Apps host [P4]; plugins work on desktop [P6]; widget rendering on desktop and app-only tools (Unv). Extension support table lists Desktop without separating Chat from Work mode (Unv) [P7] |
| **Claude Code** (terminal, IDE, Desktop Code tab) | Text slices and links | `/northstar:page <topic>` and `/northstar:new` as MCP prompts, listed as `/northstar:page (MCP)` [P8]. A status-line segment, "Northstar · 3.2 Projections · 2 new", as an OSC 8 link to the Reader [P9]. Northstar IDs in output become clickable through `footerLinksRegexes` [P10] | Prompts and status line documented [P8][P9]. `footerLinksRegexes` format (Unv). MCP App rendering in the Desktop Code tab (Unv). Prompt results enter the model's context [P8], so slices stay under about 600 tokens and are labelled as Northstar data |
| **Codex** (CLI, IDE, ChatGPT Desktop Codex threads) | Text slices and links | A skill `northstar-page` that calls the Northstar MCP tool and prints the slice. Markdown links become clickable OSC 8 links in supporting terminals [P11] | Link rendering from a third-party source (Unv). MCP App rendering in Codex threads (Unv) |

**Relevance without user action.** On hook surfaces the core knows the session's goal from the AI side's goal router (SYN §3.4). The status line can show the most relevant section without being asked. On desktop chats, the "draws on" card appears whenever the model fetches the pack.

**Build order for the glimpses** (a suggestion; connector order belongs to the core design): Claude Code and Codex text slices first (cheapest, documented), then Claude Desktop cards (local, documented rendering), then ChatGPT Desktop cards (endpoint and rendering unverified).

### 10.7 Getting to the Reader

- `northstar open` in a terminal (it sets the session cookie, §3.4).
- "Open in book" from any card or slice.
- A browser bookmark, or a menu-bar icon later.
- Cloud later: a normal HTTPS address behind sign-in, usable on a phone.

### 10.8 Accessibility and theming

- Text labels on every marker and chip; colour is never the only cue.
- WCAG AA contrast; light and dark themes. Inside Claude, cards use the host's style variables [P2].
- Readable without JavaScript for the main reading column; drawers and corrections need it.

---

## 11. Remembering without quizzes

The 2026-10-08 answer asks the book to help the person **remember**, as a textbook does. A textbook helps memory through its structure and explanations, not by testing. These mechanisms do that, and none requires a routine:

| Mechanism | How it helps remembering | Evidence |
|---|---|---|
| Gist first, then explanation, then the speaker's own example | Gist persists; verbatim and episode detail support re-interpretation | [01 F1] |
| Key ideas at the end of each chapter | A small set of principles reconstructs specifics | [01 synthesis, condition 1], [01 F9] |
| Episode cues on every marker: product, conversation title, date | Source, time and people are strong recall cues; source memory fades without them | [12 F15], [01 F11] |
| "How this changed" boxes | Co-activating old and new is what updates a person | [01 F5] |
| Integration links | Reduce interference among related items | [01 F7] |
| Stable places and titles | Recognition and location memory | [02 F2], [12 F16] |
| Re-encounter chips: "came up again in 3 chats" | Natural spaced re-exposure through the AI side's packs, not a schedule | [02 idea 15], [01 F7] |
| "Welcome back" opener on a chapter not read for a while: "Last time you were here (14 Aug) …; since then …" | Re-orientation after a gap, built from the change log | [07 Impl 10] |

**One optional aid: the recall fold.** It is **off by default**. When the reader turns it on, Key ideas boxes start folded behind "Show key ideas", so the reader may try to recall them first. It records nothing, scores nothing and never prompts. It is offered because generation and retrieval improve retention [01 F8]. The book delivers its full value with it off; every test in §14 runs with it off. Whether to offer it at all touches "not a quiz", so it is Q2 for the user (§16).

---

## 12. Non-goals

- **No quizzes, exercises, flashcards or check-yourself prompts** as part of the product. The optional recall fold (§11) is off by default and asks nothing.
- **No mastery, knowledge or progress scores**: no percentages, levels, bars, streaks or badges. "How you engaged" uses plain words with evidence links [12 F10].
- **No required routine**: no review queue, inbox, daily digest to clear, or "items need your attention" badge. Nothing waits on the user (GOAL §4.1, §4.3).
- **No editor.** The user does not write or edit pages. They correct through typed actions (§9). An optional note in a correction becomes a user-typed item.
- **No global graph view** by default [12 F15].
- **No narrative profile of the user** ("you are the kind of person who…") [07 F7], [01 pitfall 4].
- **No notifications** asking the user to read. Read-only status may appear in chat slices.
- **No generation at read time** for the core pages. Search answers are deterministic.
- **No second writable copy.** The export is one-way.

---

## 13. What the core must hold

The system spine must provide these, so the book can be compiled and rendered.

### 13.1 Data

| Entity | Fields the book needs | Used for |
|---|---|---|
| Source, message, span | Source type; product (surface); conversation ID and title; message ID; branch path; model; browsing flag; timestamps; anchor `{source_type, source_id, locator, quote, prefix, suffix}`; capture fidelity; deep-link template | Drawer, Sources page, episode cues (§5.4, §5.5) |
| Leaf item | Role (Statement, Passage, Agenda); kind tags; text; gist; qualifiers; concept refs; rank and reason; valid, recorded and held time | Section content |
| Attribution | Speaker; speaker ID (model and product); modality; `hedge_verbatim`; lineage origin | Markers, V4, V5, V7 |
| Stance, verification | Holder, attitude, evidence span; checkability, status, verifier, evidence, dates | Chips |
| Supersession | Old item, new item, reason, the refuting evidence, **why the old view seemed right** (causal alternative), date | "How this changed" (§7.5) |
| Tension | Both sides, state (`contested`, resolved), spawned Question | "Where sources disagree" |
| Relation | Type (explains, example_of, defines, prerequisite_of, supersedes, same_as, answers); confidence; `direction_checked`; status | Builds on / leads to; paths |
| Concept | Stable ID, label, aliases, memberships | Sections, index |
| Goal, question, engagement | Goal: user span, explicit flag, status. Question: raised_by, status, answers. Engagement events derived by code, with user override | Paths, frontier (§6) |
| Correction | Kind, target, payload, holder `user`, origin, span (if from chat), active, created, lifted | §9, I21 |
| Context receipt | Chat reference, product, items delivered, time | "This chat draws on" card |
| Scope and sensitivity | Per item (I17) | Reader filtering; cloud later |
| Excision tombstone | Target and scope | Purge pages, caches, exports, indexes |

### 13.2 Book projection tables (owned by the human architecture, stored in the core)

```yaml
BookNode:    {id, kind: part|chapter|section|entry, label, label_source: compiled|user,
              parent_id, also_in[], order_key, anchor: concept|question|goal,
              edition, status: active|dormant|archived|redirected, redirect_to?}
Edition:     {id, at, events[], notes_node_id, metrics: {moved, merged, split, renamed}}
PageVersion: {node_id, version, edition, inputs: [item_id@version], model, prompt_hash,
              paragraphs: [{plan_id, leaf_group_hash, sentences: [{text, cites[], role}]}],
              validator_report, entailment_sample[], fallback: bool, recorded_at}
ReaderState: {reader_id, node_id, last_read_at, last_read_version}   # local, private
```

### 13.3 Interfaces

| Interface | Direction | Notes |
|---|---|---|
| Read API (HTTP JSON) | Core to Reader | Contents, section render, drawer, search, paths, what's new, history, as-of |
| Correction API (HTTP) | Reader to core | User origin only; CSRF-protected; returns the event ID for undo |
| MCP tools | Model and app to core | `northstar_page`, `northstar_resume` (shared with the AI side), `northstar_correct` (model-visible, proposes); `northstar_apply_correction`, `northstar_book_data` (app-only visibility) [P3] |
| MCP prompts | User to core | `northstar:page`, `northstar:new`, `northstar:correct` [P8] |
| Export job | Core to disk | Nightly, one-way, user-chosen folder |

The book shares item IDs with the AI side's packs. A chat can mention an item or section ID, and the reader can click it into the book.

---

## 14. Evaluation

### 14.1 Principles

- **No required user sessions.** Every check is automatic. User input is optional, one-off consent to use real data (SYN §7).
- **Golden set**: synthetic personas with a hidden world ledger (SYN §7.4), plus an optional consented slice of real chats. It includes AI-taught and user-stated knowledge, supersessions, disagreements, goals, open questions, and at least one non-chat document.
- **Judges from a different model family** from the writer. Judges must accept fewer than 10% of wrong but on-topic answers (SYN §7).
- **Bars are pre-registered**, recalibrated once after a pilot and then frozen.
- **Proxies are labelled as proxies.** A simulated reader measures whether the book makes knowledge findable and understandable. It does not measure the person's memory directly.

### 14.2 Automatic checks

| ID | Check | Measure | Bar (proposed) |
|---|---|---|---|
| T-PROV | Provenance completeness | Share of rendered items that resolve to a source span | 100% (hard gate) |
| T-CITE | Citation closure and faithfulness | Rendered sentences with a valid citation; sampled entailment pass rate; hedges and rare details kept after N regenerations | 100% closure (hard gate); ≥97% entailment |
| T-ATTR | Attribution accuracy | Speaker-phrase mismatches after validation; sampled audit of markers against the golden ledger | 0 mismatches; false endorsement ≤5% (SYN §7.3) |
| T-PARITY | AI-said parity | AI-said share of cited body leaves against the promoted-leaf and golden shares | Within 10 points |
| T-COVER | What-has-been-learned coverage | Golden knowledge items, user-stated and AI-taught, reachable within 3 clicks of the first screen, with sources | ≥90% each; AI-taught within 10 points of user-stated |
| T-TEXT | Reads like a textbook | Pairwise preference by a calibrated judge on a rubric: defines before use; prerequisite order; examples present where leaves have them; coherent paragraphs, not fragment dumps; key ideas present; attribution visible without clutter; nothing beyond the sources | Book beats each baseline (§14.4) in ≥70% of pairs |
| T-STAB | Stability | Text changes in sections whose leaf set did not change; sections moved per edition; label churn; A→B→A within 4 editions; broken links | 0; ≤5%; ≤5%; 0; 0 |
| T-CORR | Correction survival | Active corrections still in force after N rebuilds and editions; corrected content absent from bodies and packs | 100% (hard gate, I21) |
| T-LEARN | What-to-learn validity | Prerequisite precision and direction on curated subsets; open-question precision; frontier predictive validity: share of frontier items the user later engages with in normal chats, against random and popularity baselines | Beats both baselines |
| T-NEW | Change visibility | Golden changes (new knowledge, supersessions of held items, disagreements) that appear in "Since you last opened" | ≥95% of held-item changes; ≥90% overall |
| T-FRESH | Freshness | Leaf promotion to visible in "New, not yet woven in"; to woven prose | ≤5 min; ≤24 h |
| T-FALLBACK | Graceful degradation | Sections in plain-list mode | ≤5% |
| T-SLICE | Glimpse correctness | Slices and cards match the Reader's content and markers; size limits respected; "draws on" card matches the context receipt | 100% match |
| T-RITUAL | No-ritual check | With zero reads and zero corrections for 30 simulated days, the book stays current and every sentinel stays green | Pass |
| T-COST | Cost | Model spend for the book per month at golden-set volume | ≤$30 with Sonnet 5.5 as the writer |

### 14.3 The simulated-reader protocol

A reader model from a different family from the writer gets **one representation** under a fixed budget (8K tokens of content, plus navigation by tool calls). It answers pre-registered questions. Scoring checks the content **and** the attribution against the hidden ledger.

| ID | Question type | Example |
|---|---|---|
| SR-1 | What have I learned about X, and from whom? | "What have I learned about projections, and from whom?" |
| SR-2 | What did a given AI teach me, and when? | "What did ChatGPT explain about WAL mode in October?" |
| SR-3 | How did my understanding change? | "What did I believe about editing pages in September, what replaced it, and why?" |
| SR-4 | What should I learn next for a goal, and why? | "For the prototype goal, what is next and why?" |
| SR-5 | Where do my sources disagree? | "Where do Claude and ChatGPT disagree, and has it been settled?" |
| SR-6 | Re-orientation after a gap | After 30 simulated days of new events: "What is current about X, and what changed?" |

**Navigation run (T-NAV).** An agent drives the real Reader through its accessibility tree and answers SR-1 questions. Measures: clicks, time and correctness with attribution. Baseline: searching the raw transcripts. Bar (proposed): median ≤3 clicks, ≥90% correct with attribution, and better than the baseline. The optional one-off human navigability test in SYN §7.3 stays optional.

**Bars (proposed).**
- The book beats the flat item list and raw transcripts by at least 15 points on SR-1 to SR-5 at the matched budget.
- AI-said questions (SR-2) score within 10 points of user-said questions.
- On SR-6, refutation-style boxes beat plain replacement on stating current belief **and** reason.

### 14.4 Baselines

| Baseline | What it is |
|---|---|
| BK0 | Raw transcripts, searchable |
| BK1 | A flat chronological list of leaf items with chips |
| BK2 | An LLM wiki: pages written and revised in place, without citations (Karpathy-style [12 F7]) |
| BK3 | The book without paragraph memoization and editions (stability ablation) |
| BK4 | The book without "How this changed" boxes (refutation ablation) |

BK3 and BK4 are ablations of HOW layers. If a layer moves no metric it may be cut. A component GOAL requires (the what-to-learn side, AI-said passages in the book, the human view itself) can only be redesigned, never cut (SYN §7).

### 14.5 Fault injection (GOAL §4.7)

Degrade one J7 worker at a time: a weak model, shuffled citations, a missing leaf, padding noise, a prompt bug that drops speaker names.

- Structural errors blocked by validators: target 100% (uncited, misquoted, misattributed, correction-violating).
- Semantic errors caught by entailment sampling and audit: measured and reported.
- Time until the error budget trips.
- Rollback by job, batch or model re-renders hash-identical pages (I18).

### 14.6 Passive signals from real use (optional)

If the user consents, the Reader logs locally: opens, sections read, marker clicks, drawer opens, corrections, and Undo. These calibrate defaults (for example marker density). They are never shown to the user as a score and never used to estimate what the user knows.

---

## 15. Spikes for unverified facts

| Spike | Question | Decides |
|---|---|---|
| S-R1 | In Claude Desktop, does a local `.mcpb` server's MCP App render inline and fullscreen; can it call app-only tools; does `ui/open-link` open a `127.0.0.1` URL? | Claude Desktop cards and the confirm card (§9.2, §10.6) |
| S-R2 | In ChatGPT Desktop **Chat** mode, does a developer-mode plugin's MCP App render; are app-only tools honoured; what endpoint is needed; does a thread side panel work in Chat mode? | ChatGPT Desktop cards |
| S-R3 | Claude Code: the `footerLinksRegexes` format; status-line OSC 8 links in the user's terminal; whether the Desktop Code tab renders MCP Apps | Claude Code glimpses |
| S-R4 | Codex: link rendering; a way to show a slice to the user without adding it to model context | Codex glimpses |
| S-R5 | Deep-link formats into Claude Desktop, ChatGPT Desktop and Codex conversations | "Open in product" links (§5.4) |
| S-R6 | J7 on the golden set: validator reject rate, entailment pass rate with the local verifier (S10), tokens per section, fallback rate | §8 bars and cost |
| S-R7 | Whether MCP calls from desktop chats carry a conversation identity | "Which conversation" attribution on desktop chats (§5.5) |
| S-R8 | Calibrating the T-TEXT judge and the simulated reader on 30 builder-labelled sections (builder spot-checks during evaluation only, SYN §7) | §14 bars |

---

## 16. Questions for the user

Only questions that touch the WHAT are listed. Each has a working assumption, labelled "pending user answer". Silence is never taken as an answer (SYN §9).

1. **Engagement words.** Each section can show "how you engaged": explained to you, asked about, used, restated, confused, each with links to the chats. It never says you "know" something and shows no numbers. Do you want this shown, or hidden entirely so nothing resembles a score?
   *Working assumption (pending user answer):* show it in plain words, as described.
2. **The optional recall fold.** It folds each chapter's key ideas behind a "Show" button so you can try to recall them first. It is off by default, records nothing and never prompts. Should it exist at all, given "not a quiz"?
   *Working assumption (pending user answer):* include it, off by default. If you say no, it is removed with no other effect.
3. **Work sessions in your personal book.** Should Claude Code or Codex sessions on employer repositories appear in your personal book?
   *Working assumption (pending user answer):* the book shows only what the core captures under its allowlist, and employer-repository sessions are excluded until you say otherwise.

---

## 17. Risks

| # | Risk | Threatens | Mitigation |
|---|---|---|---|
| C1 | **The narrator's fluency is mistaken for understanding.** Polished AI prose raises felt understanding regardless of real understanding [01 F10][01 pitfall 6][07 F11] | H3, the user's real goal | Name the narrator; markers on every sentence; verbatim boxes; engagement in plain words, never "known"; no satisfaction metrics; the optional recall fold |
| C2 | **Desktop chat capture is model-reported for a while.** Content from Claude Desktop and ChatGPT Desktop chats may lack verbatim quotes, and "which conversation" may be unknown at first (SYN RISK 4; §5.5) | GOAL §4.2, H4 on desktop chats | Fidelity chips; never show paraphrase as a quote; upgrade in place on reconciliation; S-R7. The capture fix belongs to the core and connector designs |
| C3 | **Glimpses depend on the model or the user on desktop chats.** A card renders only after a tool call; ChatGPT needs `@` or its own choice of plugin; desktop rendering is unverified [10 F2][P6] | Value of M9 (optional, so no non-negotiable) | The Reader works independently; status-line glimpses on hook surfaces; spikes S-R1, S-R2 |
| C4 | **Reorganization churn erodes landmarks** (SYN RISK 15) | Usability vs GOAL §4.3 | Editions, blast-radius cap, paragraph memoization, redirects, undo, pins as hard constraints; T-STAB |
| C5 | **Studying an AI-built structure helps less than building one** (g = 0.43 vs 0.72) [12 F14] (SYN RISK 17) | No non-negotiable | Inform the user; refutation boxes, examples and cues that help readers; the optional fold. The user chose AI management (GOAL §4.3) |
| C6 | **Entailment checks are not independent** if the local verifier fails calibration (SYN RISK 18) | GOAL §4.7 | S10; if it fails, the user chooses between a second vendor key and accepting the risk |
| C7 | **AI-taught knowledge quietly demoted by curation.** Assistant text dominates chat bytes, and any selection can drop it [12 R4] | GOAL §4.2 | Rank without speaker for world claims; passages in "In their words"; T-PARITY sentinel; every passage reachable by search and drawer |
| C8 | **Local web server exposure** (other local sites, DNS rebinding, stored XSS from captured text); cloud exposure later (SYN RISK 13) | Privacy, trust | §3.4 controls; sanitizer; scopes and tiers; cloud behind sign-in |
| C9 | **Noisy prerequisites make the frontier untrustworthy** [12 F11][12 R3] | H2 usefulness | Direction checks, visible reasons, one-click rejection, T-LEARN against baselines; redesign rather than removal |
| C10 | **Compile cost runs away** through churn or retries | Budget | Memoization, nightly batch, dirty tracking, cost sentinel |
| C11 | **The book grows into a mausoleum** [02 pitfall 8] | Readability | Short entries; archive shelf; first screen limited to recent and goal-linked content |
| C12 | **Vendor deep links and UI hosts change** (MCP Apps is new; ChatGPT plugins are in flux) [10 F6][14] | M4 convenience links, M9 | The core's own transcript view; components behind one adapter; version pins |
| C13 | **Reading away from the Mac waits for the cloud stage** | Convenience | Accepted under "local now, cloud later" (GOAL §2). The export can be read anywhere the user copies it |

---

## 18. Goal-fidelity check

| GOAL item | How this design meets it | Where |
|---|---|---|
| §3.2 What has been learned, from the user and from AIs | Sections cite user-said and AI-said leaves alike; "Your own thinking" and "In their words" blocks | §4.4, §5 |
| §3.2 What to learn: goals, gaps, open questions, next steps | Learning paths, frontier with reasons, open questions, gaps, all linked into chapters | §6 |
| §3.2 Reads like a textbook; understand and remember | Parts, chapters, sections in reading order; gist, explanation, worked examples, key ideas, refutation boxes; remembering mechanisms | §4, §11 |
| §3.2 Traceable to who said it and in which conversation | Markers on every sentence; two clicks to the verbatim span; Sources page | §5.2–§5.4, §10.2 |
| §3.2 Not a quiz or a mastery score | Non-goals; engagement in plain words; optional fold off by default (Q1, Q2) | §11, §12 |
| §3.2 User browses and may correct; routines optional | The Reader; one-click corrections; nothing waits on the user; M12 | §9, §10, T-RITUAL |
| §4.1 A system, no rituals | All compile and reorganization is automatic; no queues or badges | §8, §12 |
| §4.2 AI-said knowledge first-class and attributed | AI leaves in the body; rank ignores speaker for world claims; parity sentinel and test | §5.6, T-PARITY |
| §4.3 The AI manages it; correction optional | J7 and J8 run unattended; corrections optional and persistent (I21) | §8, §9 |
| §4.4 Two architectures over one core | The book is its own projection; packs are separate; shared item IDs | §3.2, §13 |
| §4.5 Drift and continuity | Not this document's scope. The book shares IDs and receipts with the AI side and never replaces it | §10.6, §13.3 |
| §4.6 Product-agnostic core with connectors; first four connectors; local now, cloud later | One component library, two adapters; slices for all four products; Reader moves to the cloud unchanged | §3, §10.6 |
| §4.7 Robust maintainer | Leaf-only inputs; code validators; entailment by another family; fallback; rollback; fault injection | §8, §14.5 |
| §4.8 Prototype built and evaluated | Evaluation plan with hard gates, baselines and spikes | §14, §15 |
| §6 "Read their knowledge like a textbook … each item shows its sources … what they are working toward learning next" | First screen, sections, drawer, paths | §10.1, §4.4, §6 |

**Where the goal could be narrowed or is at risk.** This design narrows no requirement. It flags these:
- Desktop chats may lack verbatim AI-said text and conversation identity for a while (C2, S-R7).
- Glimpses on desktop chats depend on a tool call, and on ChatGPT on plugin selection (C3).
- Entailment independence depends on the local verifier (C6).
- An AI-built structure helps learning less than a self-built one (C5).

**Reframes considered and not adopted.** Round-1 notes argue that the person should write their own key syntheses [01 Impl 12][02 Impl 6]. That would shift work to the user and conflicts with GOAL §4.3. It is not adopted. The trade-off is recorded as C5.

---

## 19. Product facts used

All checked on 2026-10-08 unless noted.

| ID | Fact | Source |
|---|---|---|
| P1 | MCP Apps render inline in Claude Desktop. Example servers run locally through `claude_desktop_config.json`. Claude asks to display an app: Allow, or Always allow | https://claude.com/docs/connectors/building/mcp-apps/getting-started |
| P2 | Claude MCP App display modes: inline card, inline carousel, fullscreen; modes `inline`, `fullscreen`, `pip`. Inline cards: height fits content, at most 2 actions, 4–5 data points, no drill-ins or menus; the host caps inline height. Fullscreen keeps the composer visible and uses collapsible sidebars, tabs or pagination. Host style variables; light and dark | https://claude.com/docs/connectors/building/mcp-apps/design-guidelines |
| P3 | MCP Apps spec (2026-01-26, Stable): `ui/open-link` should open the user's default browser; tools with only `"app"` visibility are callable by the app and hidden from the model; `ui/update-model-context` overwrites the previous context and may be deferred to the next user message | https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/2026-01-26/apps.mdx |
| P4 | Supported MCP Apps clients include ChatGPT, Claude, VS Code and Goose; host support varies | https://github.com/modelcontextprotocol/ext-apps |
| P5 | ChatGPT app display modes: inline, fullscreen, picture-in-picture. Inline cards: at most two actions, no nested scrolling, no deep navigation. The page does not say which surfaces render apps (desktop: Unv) | https://developers.openai.com/plugins/concepts/ui-guidelines |
| P6 | ChatGPT plugins work in Chat and Work on web, desktop and mobile; invoked with `@` or chosen by ChatGPT from the described task | https://learn.chatgpt.com/docs/plugins |
| P7 | OpenAI MCP Extensions: a thread entrypoint opens an app in a conversation's side panel. Support table: Desktop, Web (the Work browser; classic ChatGPT excluded), iOS, Android. Composer mentions are desktop-only. Chat vs Work mode on desktop is not distinguished (Unv) | https://developers.openai.com/plugins/build/extensions ; https://github.com/openai/mcp-extensions/blob/main/docs/spec.md |
| P8 | Claude Code lists MCP prompts as `/server:prompt (MCP)`, also runnable as `/mcp__server__prompt`; prompt results are injected into the conversation. MCP resources are referenced with `@server:protocol://path`. MCP App UI resources do not appear in `@` suggestions. MCP output warns above 10,000 tokens and is limited to 25,000 by default | https://code.claude.com/docs/en/mcp |
| P9 | Claude Code status line: a script receives session JSON on stdin and prints the line; updates are debounced at 300 ms; `refreshInterval` adds a timer; OSC 8 links are clickable in iTerm2, Kitty and WezTerm, not Terminal.app | https://code.claude.com/docs/en/statusline |
| P10 | Claude Code setting `footerLinksRegexes`: "Make issue or review IDs in output into clickable links below the input box". Its exact format was not read (Unv) | https://code.claude.com/docs/en/settings-reference |
| P11 | Codex CLI renders Markdown links as clickable OSC 8 links in supporting terminals (third-party write-up of v0.150.0, dated 2026-08-26; Unv) | https://codex.danielvaughan.com/2026/08/28/codex-cli-v0150-tui-ergonomics-copy-picker-auto-titling-osc8-clickable-links/ |
| P12 | Anthropic API prices per million tokens. Sonnet 5.5: $2 in, $10 out; Batch $1 / $5; cache hits $0.10. Opus 5.5: $4 / $20; Batch $2 / $10; cache hits $0.20. Haiku 5.5 (prompts up to 100K): $0.10 / $0.50; Batch $0.05 / $0.25. Batch and caching discounts stack | https://platform.claude.com/docs/en/about-claude/pricing |
| P13 | Claude Desktop chat supports local stdio MCP servers (`.mcpb` or `claude_desktop_config.json`) that need no public HTTPS, and gets the same remote connectors and MCP Apps as the web. Checked by [10 F4] on 2026-10-07, not re-checked | [10 F4]; https://claude.com/docs/connectors/building/mcpb |
| P14 | Claude Code hooks (`UserPromptSubmit` with the verbatim prompt, `SessionStart`, `Stop` with `last_assistant_message`) and Codex hooks (`UserPromptSubmit`, `SessionStart`, `Stop`); the ChatGPT desktop app hosts Codex. Checked by [10 F5, F9] on 2026-10-07, not re-checked | [10 F5, F9]; https://code.claude.com/docs/en/hooks ; https://learn.chatgpt.com/docs/hooks |

**Research notes cited.** [01] `docs/research/01-human-memory-and-learning.md`; [02] `docs/research/02-pkm-practice-and-failure.md`; [07] `docs/research/07-human-vs-ai-consumers.md`; [10]–[14] and SYN in `docs/research/round2/`. Round-1 notes are used for evidence only; their reframing is superseded (GOAL §5).
