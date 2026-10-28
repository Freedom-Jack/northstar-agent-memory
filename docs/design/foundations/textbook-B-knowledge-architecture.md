# Human architecture, design B: the Book, compiled from the core

Status: design proposal, 2026-10-08. One of three independent designs of the human architecture. It goes to adversarial review and then to the user-approval gate (GOAL §7). Nothing here is built yet.

**Authority.** [`docs/GOAL.md`](../../GOAL.md) overrides this document. The user's answers of 2026-10-08 (GOAL §2) override the round-2 synthesis where they conflict. This design takes GOAL §3, §4 and §6 as fixed and argues only about HOW. Where it sees a risk to the goal, it says so in §16 or asks in §15. It adopts no reframe.

**Angle: knowledge-architecture-first.** The design starts from one question: how does the AI turn the attributed core (passages, statements, concepts, agenda items, relations) into a book that a person can read, understand and remember? The answer is a compiler. Code decides the structure. A language model writes only small, cited, checked pieces of prose. Everything else is deterministic.

**Evidence.** Round-2 notes are cited as [10]–[14] and the round-2 synthesis as SYNTHESIS. Round-1 notes [01], [02] and [07] are used for evidence only. Invariants I1–I20 come from [13 §C]; I21 from SYNTHESIS §3.2. Product facts carry a source URL and the date checked. Unverified facts are marked (Unv).

---

## 0. Summary

- **The human side is a Book.** Units: Book, Part, Chapter, Section, Block, Sentence. Plus front matter (goals, frontier, what changed), forward chapters ("Ahead"), and back matter (Glossary, Index, Sources, Timeline, Open questions, Editions).
- **One concept, one section.** A section's ID is its concept's stable ID. Its URL never changes. Merges redirect; unmerges restore.
- **Structure is computed, not written.** Chapters and parts come from deterministic clustering of the concept graph, with a fixed seed, a stability cost and user corrections as hard constraints. Order comes from a topological sort of prerequisite edges.
- **Prose is small, cited and checked.** A model writes only small pieces: a section's key idea, comparison and claim blocks, an optional lead sentence, chapter overviews, and chapter and part titles. Every such sentence cites leaf items. Code rejects uncited sentences, unknown numbers or names, lost hedges and any attribution wording. An independent model checks entailment.
- **Attribution is drawn by code, never by the writer.** Who said it (you, Claude, ChatGPT, Codex, a source), which model and product, which conversation and date, your stance, the verification status and the capture fidelity appear as chips built from core records. Any sentence opens a source card with the verbatim span.
- **AI-taught knowledge is the main text, not a footnote.** Explanations are chosen by a speaker-neutral rank. A parity check alerts if the book under-represents what AIs taught.
- **What to learn is part of the book.** Goals and the frontier lead the first screen. Each chapter ends with an "Ahead" box. Each goal has a forward chapter of stub sections. Stubs show only what conversations said about the gap; the compiler never invents teaching.
- **Two cadences protect landmarks.** Content updates nightly with frozen numbering. Structure changes only in weekly editions, under a churn budget. Every edition is a snapshot you can open, and every move is a reversible event.
- **Corrections are one click or one sentence in chat.** They become typed ledger events and hard constraints in every compile stage (I21). A compile that breaks a correction is not published.
- **Medium: a local web app now, the same renderer in the cloud later.** Pages are pre-rendered static HTML with a thin layer for search, corrections and provenance. A read-only Markdown mirror keeps the book usable without the app. In-chat slices reach all four first connectors through one MCP server.
- **Cost is small.** About 0.15M input and 0.02M output tokens a day at 100 turns a day, about an eighth of [13]'s total maintainer budget.
- **The maintainer can lose focus and the book stays correct.** If any model step fails validation, the block falls back to a deterministic rendering of verbatim excerpts. The book can be less fluent, but it is never unchecked.

---

## 1. What this design must deliver

From GOAL §3.2 and the 2026-10-08 answers:
- a navigable structure the AI maintains, covering **what has been learned** (from the user's own thinking and from what AIs taught) and **what to learn** (goals, gaps, open questions, next steps);
- it **reads like a textbook**: organized and explained so the person **understands and remembers** it;
- every explanation stays **traceable** to who said it and in which conversation;
- it is **not a quiz and not a mastery score**;
- the user browses it and **may** correct it; no routine is required.

The non-negotiables this design touches directly: §4.1 (no rituals), §4.2 (AI-said first-class), §4.3 (AI manages, correction optional), §4.4 (two architectures over one core), §4.6 (product-agnostic, connectors), §4.7 (robust maintainer), §4.8 (prototype). §17 checks each one.

---

## 2. Design principles

| # | Principle | Evidence |
|---|---|---|
| P1 | **Compile, don't author.** The book is a projection of the core. It is rebuilt from leaf items, never edited in place. | Rewriting drifts [01 F3][12 F6]; summaries of summaries hallucinate (4% of RAPTOR nodes) [12 F4]; ledger + projections [13 §A] |
| P2 | **Code decides structure; models fill small, checkable slots.** | Rule-based checks beat model judges; self-correction misses 64.5% of own errors (SYNTHESIS §3.5) |
| P3 | **Gist plus verbatim, side by side.** Each section opens with a short gist and shows the original words. | Gist and verbatim are stored in parallel; reasoning runs on gist, re-interpretation needs the episode [01 F1] |
| P4 | **Stable places.** IDs, titles and positions change rarely and visibly. | People navigate by recognition and location [02 F2][07 F10]; churn destroys it [12 F16]; Luhmann's fixed addresses [02 F1] |
| P5 | **Provenance that does not decay.** Who said it, where and when, on every sentence. | Human source memory fails [01 F11]; showing sources reduced over-reliance on wrong AI answers [12 F8] |
| P6 | **Show change as change.** Superseded knowledge appears as a refutation: old, new, why. Contested knowledge stays contested. | Old beliefs persist unless co-activated and refuted [01 F5]; forced merges create wrong hybrids [01 F6] |
| P7 | **Small chunks, expandable.** About four to seven items at any level of the first view. | Working memory holds about 4 chunks; experts use retrieval structures [01 F9] |
| P8 | **Organize around goals and questions where they exist.** | Material sticks when a live question pulls it in [02 F6]; questions are the best gap signal [12 F12] |
| P9 | **Trees, outlines and timelines by default; no global graph.** | No evidence for global graph views; trees, local graphs and time cues have it [12 F15][02 pitfall 4] |
| P10 | **Nothing waits for the user.** No inbox, no queue, no "due" list. | Visible backlogs drive abandonment [02 F10, pitfall 6]; GOAL §4.1, §4.3 |

---

## 3. The book's anatomy

### 3.1 Units

| Unit | What it is | Contains | Built by | Why it helps |
|---|---|---|---|---|
| **Book** | One per user and scope set | Front matter, parts, back matter | Code | One stable home for all knowledge |
| **Part** | A broad area, e.g. "Web performance" | 3–8 chapters (bounds 2–12), a forward chapter if a goal lives here | Code clusters; model proposes the title | A handful of top-level landmarks fits recognition-based navigation [02 F2][01 F9] |
| **Chapter** | A tight cluster of related concepts | Overview, "In this chapter" list, 4–9 sections (bounds 2–15), "Ahead" box, chapter sources | Code clusters and orders; model writes title and overview from leaves | A schema before details helps new material attach [01 F4]; a guiding goal or question gives relevance [02 F6] |
| **Section** | One concept: its anchor concept plus absorbed minor concepts | A fixed sequence of typed blocks (§3.2) | Code assigns leaves; model writes a few blocks | One idea per place; a predictable layout becomes a retrieval structure [01 F9] |
| **Block** | A typed part of a section, e.g. Explanation, Example, How it changed | Sentences of four kinds (§3.3) | Code or model, per block type | The unit of incremental recompile, caching and validation |
| **Sentence** | The smallest cited unit | Text plus citations to leaf items | Code or model | The unit of provenance: every sentence leads to a verbatim span |

A "page" is just a section rendered on screen. It is the reading unit and has one URL.

Minor concepts (few leaves, no explanation of their own) do not get sections. They render as a sub-heading inside the section of their closest parent concept and get a glossary entry. §6.3 gives the rule.

### 3.2 The section template

Every section has the same block order, so the reader always knows where to look. Empty blocks are omitted.

| # | Block | Leaves it takes | How it renders | Model prose? |
|---|---|---|---|---|
| 1 | **Key idea** | Top-ranked definition and explanation leaves | 1–2 restated sentences | Yes |
| 2 | **Definition** | Definition statements | Verbatim quote; "also called" line from aliases | No |
| 3 | **Explanation** | Passages of kind explanation, from any speaker | Top 2 verbatim excerpts with chips; optional one-sentence lead; "More explanations (n)" with leaf gists | Lead only |
| 4 | **Examples** | Passages of kind example, including code | Verbatim only; code is never paraphrased | No |
| 5 | **Comparison** | Comparison passages and `compares` relations | Restated or bridge sentences, or a small table | Yes |
| 6 | **How to** | Procedure passages | Verbatim steps | No |
| 7 | **Facts and claims** | Checkable statements not already shown in an excerpt | Restated list, grouped under a voice header per speaker | Yes |
| 8 | **Your conclusions** | User-spoken insights, decisions and beliefs | Verbatim with stance chips | No |
| 9 | **How your understanding changed** | Supersession chains | Refutation template: earlier, now, why it changed, why the earlier view seemed right (only if a leaf supports it) | No |
| 10 | **Unsettled** | Contested Tensions (SYNTHESIS §3.1 step 5) | Both sides, attributed, with a link to the spawned question | No |
| 11 | **Open questions** | Questions about this concept | Your words, date, product; "answered in §…" when answered | No |
| 12 | **Connections** | Prerequisite, part-of, used-in, see-also relations | "Builds on", "Used in", "See also" lists | No |
| 13 | **How you engaged** | Engagement events (SYNTHESIS §3.2) | One factual line: explained to you n times (by whom), asked, applied, restated. No score | No |
| 14 | **Sources** | Every span cited in the section | Numbered list of conversations and documents | No |

So model-written prose appears in only three block types (1, 5, 7), one optional lead sentence (3), and chapter overviews (§6.11). Everything else is code.

### 3.3 Four kinds of sentence

| Kind | Written by | Rule | Shown as |
|---|---|---|---|
| **Q, quote** | Code | An exact substring of a span (I2). Selected by code (§6.7) | Quotation with a chip |
| **R, restated** | Model | Cites at least one leaf. No attribution words. Entailment-checked | Plain prose with citation marks |
| **B, bridge** | Model | Cites at least two leaves and one relation item. Entailment-checked against the leaves together | Plain prose with citation marks |
| **T, template** | Code | Filled from core records only: attributions, structure, changes, stubs | Plain prose, often with links |

Attribution lives only in T sentences and chips. A model never writes "Claude said" or "you concluded". That removes misattribution by the writer entirely (I3, I4).

### 3.4 Front matter, forward chapters and back matter

| Part of the book | Contents | Built by |
|---|---|---|
| **Home (first screen)** | Goals, next to learn, since your last visit, continue reading, contents (§9.3) | Code |
| **Your goals** | Each explicit goal with covered sections, frontier, open questions. Inferred "possible interests" in a separate, decaying list [07 F7] | Code |
| **Ahead box** (end of each chapter) | Frontier concepts that build on this chapter; open questions about its concepts | Code |
| **Forward chapter** (end of a part) | One per active goal anchored in that part: stub sections for goal concepts not yet covered (§5.4). Goals with no home part go to a final part, "Ahead: new territory" | Code |
| **Glossary** | Every concept: preferred term, aliases, one-line definition (quote or leaf gist), link to its section | Code |
| **Index** | Terms to 1–4 entry-point sections, like Luhmann's keyword index [02 F1, idea 3] | Code |
| **Sources** | Every conversation and document: product, model, date, title, what it contributed, link to the transcript view. Filter by speaker: what you said, what Claude taught, what ChatGPT taught | Code |
| **Timeline** | Month by month: what was added, changed, superseded; goals opened and closed | Code |
| **Open questions** | All open questions, grouped by part; answered questions with links to their answers | Code |
| **Editions** | Every edition with its change notes; open any edition as it was | Code |

The Sources appendix is a "who taught me what" directory: a transactive memory for the person [01 F12, idea 15].

### 3.5 Why this helps understanding and remembering

| Feature | Helps by | Evidence |
|---|---|---|
| Key idea at the top of each section | Gives a gist to reason with; verbatim stays one click away | [01 F1] |
| Chapter overview before sections | Gives a schema first, so details attach faster | [01 F4] |
| Prerequisite order inside a chapter | Each section builds on ones already read; matches the "ready to learn" fringe | [12 F11][01 F4] |
| Examples and comparisons as their own blocks | Comparing cases is one of the processes that create understanding | [01 synthesis] |
| Refutation blocks for changed knowledge | Co-activates the old and new belief and explains the change, so the old one stops resurfacing | [01 F5] |
| Contested kept as contested | Avoids synthetic hybrids that are wrong in new ways | [01 F6, pitfall 5] |
| Episodic cues: who, which product, when | Time and people are strong retrieval cues; source memory decays without them | [12 F15][01 F11] |
| Stable places and numbering | Recognition and location memory work only if places stay put | [02 F2][07 F10][12 F16] |
| Small chunks, expandable | Fits the about-4-chunk limit | [01 F9] |
| Links between related sections | Integration links reduce retrieval-induced forgetting | [01 F7] |
| Goals and questions as organizing context | Material pulled in by a live question sticks | [02 F6][12 F12] |
| In-chat slices when a topic comes up (§9.5) | Re-encounters happen during real use, with no schedule | [02 idea 15, F10] |

**Honest limit.** Reading an AI-built structure helps less than building one yourself (concept maps: g = 0.43 studied vs 0.72 constructed) [12 F14], and rereading alone is a low-utility technique [01 F8]. This design does the best a no-ritual product can: strong structure, cues and in-context re-encounters. It does not claim more. RISK RB7 and question Q2 cover this.

### 3.6 Worked example of one section

The content is invented to illustrate the layout. It is not user data.

```
Part II  Web performance  ›  Chapter II.4  HTTP caching
§II.4.3  no-cache and no-store                                      sec_01J8…  · Edition 14

KEY IDEA
`no-cache` lets a cache store a response but requires a check with the server
before each reuse.[1] `no-store` forbids storing the response at all.[2]

EXPLANATION
Taught by Claude · claude-opus-5-5 · Claude Code · 14 Sep 2026 · verbatim · verified: supported
  "no-cache doesn't mean 'don't cache'. The response can be stored, but every reuse
   has to be revalidated with the origin first, usually with an If-None-Match request
   carrying the ETag."                                       [Read the full explanation]
More explanations (1): ChatGPT, 3 Oct: when to prefer no-store for private pages.

COMPARISON
  no-cache  stored; revalidated before each reuse.[1]
  no-store  never stored.[2]
Only no-store keeps a copy of a private page off the disk.[2][R7]

YOUR CONCLUSIONS
You · Claude Code · 15 Sep 2026 · you asserted
  "So for the account page we want no-store, not no-cache."

HOW YOUR UNDERSTANDING CHANGED
Earlier · ChatGPT · <model as recorded> · ChatGPT Desktop chat · 2 Sep 2026 · paraphrase-captured
  "no-cache means the browser never caches the response."
Now · Claude, 14 Sep (above).
Why it changed: an independent verifier found the earlier claim contradicts RFC 9111.[V3]
Why the earlier view seemed right: the name suggests "no caching".[1]

OPEN QUESTIONS
You · ChatGPT Desktop chat · 3 Oct 2026 · not yet answered
  "Does a CDN treat no-cache the same way as a browser?"

CONNECTIONS   Builds on §II.4.1 Cache-Control basics · §II.4.2 Validation with ETags
              Used in §II.6.2 Caching private pages
HOW YOU ENGAGED  Explained to you twice (Claude 1, ChatGPT 1). You asked once. You applied it in Claude Code on 15 Sep.
SOURCES  [1] Claude · Claude Code · "Dashboard caching" · 14 Sep 2026 · message 12 …
```

Each citation mark opens a source card (§4.3). The chips use the same visual weight for you and for an AI.

---

## 4. What has been learned: attribution in the book

### 4.1 Chips

Chips render the core's independent attribution axes (SYNTHESIS §3.1; AD6). Code builds them; no model touches them.

| Chip | Values | Source record |
|---|---|---|
| Speaker | You · Claude · ChatGPT · Codex · other agent · external source · system-inferred | Attribution.speaker, set by the adapter (I3) |
| Model and product | e.g. `claude-opus-5-5` · Claude Code | Message.model, Episode.surface |
| Date | When it was said; valid time if different | Message.ts, qualifiers |
| Your stance | asserted · accepted · questioned · disputed · rejected · none | Stance (I4: endorsement needs your evidence) |
| Verification | supported · mixed · unchecked · not checkable (opinion or advice) · contradicted · AI-cited, unchecked. Verifier and evidence on hover | Verification |
| Capture fidelity | verbatim · paraphrase-captured · reconciled | Attribution.capture_fidelity |
| Certainty | tentative when the source hedged (I10) | Item.certainty |

Verification and stance are separate chips. "You accepted it" never reads as "it is correct" [12 F8].

### 4.2 AI-taught knowledge is first-class

- **Same weight.** AI explanations are the main text of a section when they are the best explanation. They are not boxed off or shrunk.
- **Speaker-neutral choice.** Which explanation leads is a code rank: best rank, then verification, then independent lineages (an AI echo counts once, I11), then grounding (browsing or tools), then recency. Speaker is not a factor (SYNTHESIS §3.1 step 3). Your stance breaks ties for relevance only, never for truth.
- **Everything reachable.** Every AI passage linked to a concept is in the book: excerpted, cited or listed under "More explanations". Passages with no concept link stay reachable under their conversation in Sources. Coverage is checked (B5, §10).
- **Labelled, not hidden.** An unchecked AI claim carries its chip. Advice and opinion (not checkable) sit under a template header such as "Claude's advice (opinion, 12 Sep):", so restated sentences never present opinion as fact.
- **Parity alert.** The AI-said share of the book's leaves is compared with the AI-said share of eligible leaves in the core. A gap above 5 points is an alert (B11). This guards against soft demotion through selection ([12 R4]; SYNTHESIS AD7).

### 4.3 From any sentence to its verbatim source

```
sentence (sn_…)  ->  cites [item IDs]  ->  item  ->  attribution(s)  ->  span (quote, prefix, suffix)
     ->  message (speaker, model, ts)  ->  episode (product, conversation, title, date)  ->  transcript view
```

- **Source card.** Clicking a citation mark opens a side panel with the verbatim quote, the chips, the verifier and its evidence, your stance, and two links: "show in conversation" (Northstar's local transcript view, with the span highlighted and the surrounding turns) and "open in product" when the product has a stable chat link (Unv per product).
- **Restated sentences.** The card shows each cited leaf's quote, so the reader can compare the restatement with the original words.
- **Non-chat sources.** Document and web-page leaves use the same card with a page or character range (source-generic anchors, SYNTHESIS §3.1).

### 4.4 Capture fidelity on the desktop chat connectors

Claude Desktop chat and ChatGPT Desktop chat give no verbatim capture of AI text live; the sanctioned channel is the model's own paraphrase through MCP (SYNTHESIS Table A; [10] adapter table). Plugin hooks are ignored in chat (claude.com/docs/plugins/platform-support, per [10], checked 2026-10-07); whether Codex hooks run in ChatGPT Desktop Chat mode is (Unv) (learn.chatgpt.com/docs/hooks, per [10], checked 2026-10-07). This matters to the book because GOAL asks for a path to the verbatim source.

- The book shows such content with the chip **paraphrase-captured** and the note "as reported by the assistant during the chat, not its original wording".
- The anchor is the verbatim tool-call payload. It is an honest span of what was reported, not of what was said.
- When the spine later reconciles the original wording, the chip changes to **reconciled** and the excerpt is replaced. This is a typed event, so "what changed" shows it.
- The spine owns solving this gap (SYNTHESIS RISK 4). The book's job is never to hide it. RISK RB5 records the effect on the book.

---

## 5. What to learn

### 5.1 Inputs, all from the core

| Input | Where it comes from | Rule |
|---|---|---|
| **Goals** | Agenda items from user spans only (I5) | Explicit goals drive the frontier. Inferred interests stay in a separate "possible interests" list and decay [07 F7] |
| **Goal targets** | `advances-goal` links from J5. Often seeded by the AI's own reply to a stated goal, which usually names the topics needed, attributed as AI-said | Only concepts mentioned in conversations (see Q1) |
| **Open questions** | Your questions with no accepted `answers` link; questions spawned by contested Tensions (SYNTHESIS §3.1 step 5) | The best free gap signal [12 F12] |
| **Prerequisites** | LLM-proposed edges with a separate direction check, cycles removed, transitively reduced [12 Model C] | Used only if direction-checked and above a confidence bar (proposed 0.7, calibrated) |
| **Dangling references** | Concepts used in an explanation but never explained [12 Model C step 5] | Become gaps |
| **Relied-on but unchecked** | An AI claim that is unchecked, then used in your decision | Becomes a "worth checking" next step |

### 5.2 Coverage and the frontier, defined in code

The book defines "learned" as content, never as mastery (GOAL §2, 2026-10-08).

- `covered(c)`: concept c has at least one active explanation or definition leaf, from any speaker, whose verification is not `contradicted`.
- `G(g)`: the target concepts of goal g plus their prerequisite ancestors.
- `frontier(g)`: concepts in G(g) that are not covered and whose prerequisites in G(g) are all covered. This is the outer fringe of knowledge space theory, computed over content [12 F11].
- `later(g)`: concepts in G(g) that are not covered and have an uncovered prerequisite.

These sets are deterministic. Their inputs, the prerequisite edges, are noisy (F1 about 0.7, reversed direction common) [12 F11]. So every frontier item shows its reason, and you can reject an edge in one click (§8).

### 5.3 Where what-to-learn appears

| Place | Shows | Size |
|---|---|---|
| Home | Goals and "Next to learn" | 4–7 items [01 F9] |
| Your goals page | Per goal: covered sections, frontier, later, open questions | Unbounded, collapsible |
| Chapter "Ahead" box | Frontier concepts that build on this chapter; its open questions | Up to 5 |
| Section blocks | Open questions; Unsettled | All for that concept |
| Forward chapter | Stub sections for the goal's uncovered concepts, in prerequisite order | All |

What-to-learn is connected to what was learned by links in both directions: every stub lists the covered sections it builds on, and every covered section lists the frontier items that build on it.

### 5.4 Stub sections: no invented teaching

A stub contains only template sentences and quotes from leaves:

- "You set this goal on 2 Oct (Claude Code): '…'."
- "You asked: '…' (ChatGPT Desktop chat, 4 Oct). Not yet answered."
- "Mentioned by Claude while explaining §III.2.1 (12 Sep): '…'."
- "Builds on: §III.2.1, §III.2.3 (covered). Still needed first: §III.2.5 (not covered)."

The compiler never writes an explanation of an uncovered concept. That would be new teaching with no conversation behind it, which GOAL §3.2's traceability rules out. Whether the user wants such gap-filling is Q1.

### 5.5 Next steps

A deterministic score ranks frontier items, open questions and checks:

`score = 3·goal_relevant + 2·ready + 1.5·unblocks + 1·question_recency + 1·relied_unchecked − 0.5·blocked`

Weights are proposed and tuned on frontier predictive validity (§13). Each item shows a reason code in words:

| Code | Shown as |
|---|---|
| ready | "Builds on §… and §…, both covered" |
| asked | "You asked about this on 4 Oct" |
| unsettled | "Claude and ChatGPT disagree" |
| check | "You relied on an unchecked claim here" |
| dangling | "Used in an explanation, never explained" |

These are suggestions, not tasks. Nothing is "due", nothing is overdue, and nothing counts down.

### 5.6 Graduation

When a stub concept gets its first explanation leaf, its section graduates. It keeps its ID and URL. Between editions it stays in the forward chapter, marked "now covered". At the next edition, clustering places it in a regular chapter. If most of a forward chapter graduates, the chapter itself becomes a regular chapter and keeps its ID.

---

## 6. From core to book: the compile pipeline

### 6.1 Overview

```
 core ledger (append-only)            book ledger (append-only)            output
 ─────────────────────────            ─────────────────────────            ──────
 items, spans, relations,     J7.1    snapshot @ watermark
 attributions, corrections ─────────► concept graph                 J8.1–J8.3 (weekly edition)
                                      │                             cluster ► match IDs ► order
                                      ▼                             label (LLM) ► edition gate
                              J7.2    section eligibility + leaf assignment
                                      ▼
                              J7.3    fingerprints ► dirty blocks
                                      ▼
                              J7.4    block writer (LLM, stateless, leaves only)
                                      ▼
                              J7.5    validators V1–V9 (code) + V10 entailment (other family)
                                      │  fail twice ► extractive fallback (code)
                                      ▼
                              J7.6    assemble + render ───────────────────► static HTML, Markdown mirror,
                                      ▼                                        MCP slices
                              J7.7    diff + change notes ─────────────────► "since you last read"
```

The jobs are sub-steps of SYNTHESIS's J7 (regenerate views) and J8 (reorganize). They run under the code orchestrator with leases, idempotency keys and recorded outputs [13 §A]. Workers are stateless and have no writes (SYNTHESIS §3.5).

### 6.2 Stages

| Job | Kind | Input | Output | Checks | Cadence |
|---|---|---|---|---|---|
| J7.1 Snapshot and graph | Code | Core as of a ledger watermark; active corrections | Concept graph with typed, weighted edges | Alias graph acyclic; scope filter (I17) | Nightly |
| J7.2 Eligibility and assignment | Code | Graph, current outline | Sections; leaf-to-block map | Every eligible leaf has exactly one home block (B5) | Nightly |
| J7.3 Fingerprint | Code | Block inputs | Dirty block set | None needed | Nightly |
| J7.4 Block writer | Model | One block card, its leaves (quotes + metadata), allowed citation IDs, style card | Sentences with citations; nothing else | Schema (I15) | Per dirty block |
| J7.5 Validate | Code, then a model of another family | Draft, leaves | Accepted sentences or rejection | V1–V10 (§6.9) | Per draft |
| J7.6 Assemble and render | Code | Outline, accepted blocks, records | HTML, Markdown, slice cache | Hash-identical replay (I18) | Nightly; seconds after a correction |
| J7.7 Diff | Code | Previous and new render | Change notes; per-section diffs | None needed | Nightly |
| J8.1 Cluster, match, order | Code | Graph, previous outline, corrections, reader landmarks | Proposed outline | Tree shape, size bounds, constraints (B7) | Weekly, or when structure debt passes a threshold |
| J8.2 Label | Model | Changed chapters' member titles and key leaves | Titles | Label checks (§6.11) | With J8.1 |
| J8.3 Edition gate | Code | Proposed outline and labels | Published edition, or held | Churn budget (B9), corrections (B6), invariants | With J8.1 |

### 6.3 Section eligibility

A concept gets its own section if any of these holds:
- it is the primary concept of at least one explanation or definition leaf;
- it has at least 3 leaf groups, where a lineage group of echoes counts once (I11);
- it is a goal target or the subject of an open question;
- you pinned it or corrected its placement.

Otherwise it is a minor concept. It renders as a sub-heading in the section of its strongest `part_of` or `broader` parent, or else its most strongly linked neighbour in the same chapter.

Hysteresis prevents flicker. A minor concept is promoted after it meets the rule in two consecutive nightly runs. A section is demoted only at an edition and only if it has no active or historical leaves left, which in an append-only core is rare.

### 6.4 Clustering into chapters and parts

**Graph.** Nodes are section concepts. Edge weight is a fixed sum:
- structural relations (prerequisite, part_of, broader): high weight;
- `compares` and `example_of`: medium;
- co-occurrence as concepts of the same passage: medium;
- co-occurrence in the same episode, decayed with age: low;
- embedding similarity above a threshold, top 5 neighbours: low. Embeddings are a versioned cache, keyed by concept version and embedding model.

**Algorithm.** Leiden, with a fixed seed and a recorded library version.
1. Level 1 (chapters): run Leiden on the section graph, **warm-started** from the previous edition's membership. The resolution targets a median chapter size of 6.
2. **Stability cost** (evolutionary clustering [12 F16]): for each section the run moved, compute its individual quality gain. Revert the move unless the gain exceeds a threshold scaled by the section's landmark weight (below). This keeps snapshot quality while charging for departure from history.
3. **Constraints** (I21): sections with a "must be under" correction are fixed in place. "Must not be under" and "keep apart" pairs are forbidden. "Keep together" pairs are contracted to one node before the run.
4. **Size bounds:** chapters outside 2–15 sections are split by a sub-run or merged with their strongest neighbour.
5. Level 2 (parts): repeat steps 1–4 on the graph of chapters.

**Landmark weight** raises the cost of moving a section the reader relies on. It comes from implicit signals only: how often you opened the section, bookmarks, in-chat slice references, and corrections. No user action is required to create it.

**Daily placement between editions.** A new section goes into the chapter where it has the most edge weight, if that weight is clearly above the next best (a congruence router [01 F4]). Otherwise it still goes into the best guess, marked "placement tentative". Nothing is held in a visible inbox (P10). The core's own unplaced pool for items is retried automatically (SYNTHESIS §3.5); in the book, such items appear only under their conversation in Sources and in the "new since last compile" rail until placed.

**Why not let a model reorganize.** A model may still help: J8 can accept model-proposed "keep together" or "keep apart" hints, but code keeps a hint only if it improves the clustering objective. Structure itself is never a free-text model decision. That makes reorganization deterministic, testable and reversible.

### 6.5 Stable IDs and identity matching

| Object | ID | Lifetime rule |
|---|---|---|
| Section | `sec_` + canonical concept ULID | Never changes. Alias merge: the absorbed section redirects to the survivor with a banner. Unmerge: the old ID is restored, because concept IDs persist |
| Concept split (meaning changed) | New concept IDs minted [12 decision 6] | The old section becomes a disambiguation page for two editions, then redirects |
| Chapter | `ch_` ULID minted on first appearance | Matched across editions by weighted Jaccard overlap of members, with Hungarian assignment. Overlap ≥ 0.4 keeps the ID |
| Part | `pt_` ULID | Same matching rule over chapters |
| Block | `blk_` = hash(section ID, block type) | Stable while the section and block type exist |
| Sentence | `sn_` = hash(block ID, sorted citations, normalized text) | Stable while reused (§6.10) |
| Edition | `ed_` sequence number and date | Immutable |

An unmatched old chapter is retired with a typed event (`merged_into` or `split_into`) chosen from the overlaps, and its URL redirects. Deep links: `/s/{sec}`, `/s/{sec}#{blk}`, `/s/{sec}#{sn}`, `/c/{ch}`, and `/e/{edition}/s/{sec}` for an old edition.

### 6.6 Ordering and numbering

- **Sections in a chapter:** topological order over direction-checked prerequisite edges among members, after cycle removal (drop the lowest-confidence edge) and transitive reduction. Ties break by first-encountered date, then ID.
- **Chapters in a part, parts in the book:** topological order of the condensed prerequisite graph. Ties break by creation date, which never changes.
- **Numbering** is per part: `II.4.3` means Part II, chapter 4, section 3. An insertion in Part II never renumbers Part III.
- **Between editions numbers are frozen.** A new section takes an insertion number at its topological position, for example `II.4.2a`, as Luhmann did with his card addresses [02 F1]. New chapters work the same way (`II.4a`). Renumbering happens only at an edition and is listed in its notes.

### 6.7 Leaf assignment and selection

- **One home.** Each item has one primary concept (a core field, §12). Its home section is that concept's section, or the section absorbing that minor concept. Secondary concept links render as "See also".
- **Block by kind.** A fixed table maps an item's role and kind tag to a block (§3.2). The table is code.
- **Selection for prose.** Within a block, leaves are ranked by the speaker-neutral rank in §4.2. The top k feed prose (k = 2 for explanations, 3 for examples). The rest are listed with their leaf gists under "More". Nothing is dropped.
- **Lineage groups.** Near-duplicate leaves from different chats form one group. One is shown; the rest appear as "also said by ChatGPT on 3 Oct". This aids memory and keeps independence counting honest (I11).
- **Excerpt selection is code.** From a long passage, code picks the paragraph that best matches the concept's labels and the item's gist, then trims at sentence boundaries to at most 150 words. "Read the full explanation" expands the whole passage inline.
- **Superseded and contradicted leaves** go only to "How your understanding changed". **Contested** leaves go only to "Unsettled". This uses the best-rank projection [12 F2].

### 6.8 The block writer's contract

The block writer (J7.4) is a stateless function [13 §A]:
- **Input**, assembled by code: the maintainer charter (cached prefix), the block type's card, the leaves as quotes with IDs and metadata, the list of citation IDs it may use, and a style card. The style card asks for plain English, short sentences, the concept's preferred term, and no attribution.
- **It never sees** previous block text, other sections' text or chapter overviews. The input assembler type-checks that it receives only leaf IDs and span text (I7).
- **Output:** a list of `{kind: R | B, text, cites[], relation_id?}`. Quotes are not produced by the model; code inserts them.
- **Recorded:** model and version, prompt hash, input fingerprint, raw output (I14; [13 §A.4]).
- **No temperature tricks.** Outputs are recorded and replayed, never regenerated for the same fingerprint.

### 6.9 Validation and the fallback

Code validators run first, on 100% of drafts.

| # | Check | Rule | Invariant |
|---|---|---|---|
| V1 | Citation closure | Every R and B sentence cites at least one leaf; B cites at least two leaves and one relation; all citations are in the allowed set and active or explicitly historical | I8 |
| V2 | Quote exactness | Every quote is an exact substring of its span after normalization | I1, I2 |
| V3 | No attribution | R and B sentences contain no speaker names, product names, "you said", "I", or stance verbs (lexicon) | I3, I4 |
| V4 | Grounded tokens | Every number, date, version, code identifier and proper noun in an R or B sentence appears in a cited leaf | new |
| V5 | Hedge and modality | If a cited leaf is tentative, the sentence carries a hedge; if a cited leaf only suggests, the sentence uses advisory modality; certainty boosters ("always", "proven") are rejected against tentative leaves | I10 |
| V6 | No code or formulas in prose | Code and math appear only as verbatim quotes | new |
| V7 | Coverage | Every leaf assigned to the block is cited, quoted or listed under "More" | I9 |
| V8 | Plain English | R and B sentences at most 30 words; block at most 8 such sentences; key idea at most 2 | new |
| V9 | Corrections | No sentence cites an item you rejected as current; corrected attributions and labels are used | I21 |
| V10 | Entailment | A verifier from a different model family judges each new R and B sentence against its cited leaves: entailed, not entailed, or contradicted | L2 |

On failure, the failing draft is retried once in a fresh call, possibly on another model [13 §A.3]. If it fails again, the block renders by the **extractive fallback**: verbatim excerpts plus template sentences, with no model prose. The book can then read less smoothly, but it never shows unchecked prose and never shows a hole. The fallback is also the rendering used when the error budget freezes model prose (§10).

### 6.10 Prose stability by sentence reuse

Rewriting a whole block whenever one leaf changes would churn text the reader knows. This design keeps prose stable without ever feeding old text to the model:

1. The writer produces a fresh draft from leaves only.
2. Code aligns draft sentences with the previous version's sentences by **identical citation sets**.
3. Where they match, code keeps the old wording if the old sentence still passes V1–V9 and its recorded entailment verdict was on the same leaf versions (otherwise it is re-checked).
4. Sentences that begin with an anaphoric word ("This", "It", "They") are not reused, so reused text cannot dangle.
5. If fewer than half of the draft's sentences would be reused, the new draft is taken whole.

Old text is never input to the model, so this is not a summary of a summary. It is a deterministic choice between two texts that are each checked against the leaves.

### 6.11 Chapter overviews and labels

- **Overview input** (leaves only, I7): for each member section, its preferred term, its top definition leaf, its top explanation's leaf gist, the relations among members, and the chapter's guiding goal or question if one targets at least half the members. Output: 3–5 R or B sentences, validated like blocks.
- **"In this chapter"** is a code list of section titles with their glossary definitions.
- **Part introductions and the book contents are code only.** Upper levels never get model prose, because at that level any prose is a summary of summaries [12 F4].
- **Chapter titles** are proposed by the model for new chapters, or when membership has changed by more than 40% since the title was set. Checks: at most 6 words; a noun phrase, not a claim; it uses at least one member's term or alias, or a verifier from another family confirms it covers at least 70% of the members; it differs clearly from sibling titles. **Part titles** follow the same rules and change even more rarely.
- A title you set is fixed (I21).

### 6.12 Incremental recompile

Each block has an **input fingerprint**: a hash of its sorted leaf IDs and versions, their ranks and chips, the relation IDs it uses, the corrections that affect it, the block card version and the writer's model ID. A block is dirty only when its fingerprint changes. A clean block reuses its recorded output with no model call.

Chapter overviews have their own fingerprint over their inputs (§6.11). Template blocks, chips and back matter are re-rendered by code every run, which is cheap.

**Fresh between compiles.** If you open a section that has new leaves since the last compile, the page shows a "New since the last update" rail. It lists the new leaves' gists with chips, rendered by code. Provisional items from the fast lane appear there only, labelled "provisional, not yet checked"; the book body takes slow-lane items only [13 §B.5].

### 6.13 Determinism and replay

| Deterministic (code) | Model, recorded and replayed |
|---|---|
| Snapshot, graph, eligibility, assignment, clustering (fixed seed), matching, ordering, numbering, quotes, excerpts, chips, template sentences, back matter, frontier, next steps, rendering, diffs, validators V1–V9 | R and B sentences, chapter overviews, titles, V10 entailment verdicts |

With model access switched off, J7.6 rebuilds the published book hash-identical from recorded outputs (I18). The book's structure is path-dependent, because the stability cost depends on the previous edition. So "rebuild" means replaying the append-only book ledger, not re-clustering from nothing. That is deliberate: history is part of the landmarks.

### 6.14 Cost at about 36K events a year

Assumptions (this design's; the user's real distribution is unmeasured):

| Quantity | Value |
|---|---|
| Leaf candidates | about 100 a day, about 36K a year [13 §I] |
| Concepts after a year | about 3,000; about a third get sections, so about 1,000 sections |
| Blocks | about 4 per section, so about 4,000 |
| Dirty blocks a day | about 40 (a day's leaves cluster in a few sections) plus about 5 chapter overviews |
| Block call | about 3K input tokens (charter cached), about 400 output |
| New R and B sentences needing entailment | about 3 per dirty block after reuse |

| Job | Input tokens a day | Output tokens a day |
|---|---|---|
| J7.4 block writer | about 120K | about 16K |
| Chapter overviews | about 20K | about 2K |
| J8.2 titles (weekly, amortized) | about 2K | under 1K |
| V10 entailment (about 130 checks of about 700 tokens) | about 90K, on the local verifier | about 5K |
| L4 audit (5% of blocks, all overviews) | about 15K | about 2K |

API total: about 0.15M input and 0.02M output tokens a day. [13 §I] estimates its whole maintainer at about 1.1M input and 0.18M output a day at 100 turns a day, about $40 a month on the Batch API, ±2×. On the same model mix, the book is about an eighth of that: about $5 a month at 100 turns a day, ±2× (prices taken from [13 §I], not re-checked; (Unv)). Entailment on the local verifier costs compute, not money (AD9 working assumption).

A full rebuild, for a model migration or a prompt change, is about 4,000 blocks × 3.4K tokens, about 14M tokens. On [13 §I]'s mix that is about $15–20 on the Batch API, run over a few nights. Sentence reuse keeps the visible churn low.

---

## 7. Evolution

### 7.1 Two cadences

| Cadence | What can change | What cannot |
|---|---|---|
| **Nightly update** | Block content, new sections (with insertion numbers), graduations, chips, back matter | Numbering, chapter membership of existing sections, titles (except your renames) |
| **Weekly edition**, at most once a week and only if the gate passes | Membership, order, numbering, titles, splits and merges | Section IDs; anything a correction fixes |

Most weeks may publish no edition at all. Corrections do not wait: moves, renames and hides re-render affected pages in seconds by code; content corrections render through the extractive fallback at once and get prose in the next nightly run.

### 7.2 Added, superseded, contested

| Event in the core | What the book does |
|---|---|
| New leaf on an existing concept | Its block becomes dirty; it shows in the rail until the nightly run |
| New concept | Becomes a section or minor concept (§6.3), placed by the congruence router |
| Supersession (with reason, SYNTHESIS §3.1) | Old leaf moves to "How your understanding changed" as a refutation; the current leaf leads. "Why the earlier view seemed right" appears only if a leaf supports it [01 F5] |
| Tension resolved automatically (AD19) | Same as supersession, with the reason and the outranked side visible |
| Contested residue | "Unsettled" block with both sides attributed; a spawned question in Open questions and on the goal's frontier |
| Verification result | Chip changes; a contradicted AI claim moves to "How your understanding changed" with the verifier's evidence |
| Excision (user-started) | Leaf and its spans are removed from every block, edition and export; a tombstone remains (§10, B16) |

### 7.3 Landmark stability policy

| Landmark | Rule |
|---|---|
| Section URL and ID | Never changes; redirects on merge, retire or split |
| Section title | The concept's preferred term. Changes only when the preferred term changes, with hysteresis (the new term must lead in usage for two weeks) or by your rename |
| Section's chapter | Changes only at an edition, only if the move's gain beats the landmark-weighted threshold |
| Chapter title | Changes only if membership changed more than 40% since it was set, or by your rename |
| Numbering | Frozen between editions; per-part, so changes stay local |
| Home screen layout | Fixed slots (§9.3) |

**Churn budget per edition** (proposed, calibrated on the golden set): at most 5% of sections change chapter, at most 3 chapter titles change, at most 1 part is split or merged. An edition over budget is held. Held is not a queue: the previous edition stays live, and the next weekly run retries with a higher stability weight. This is quarantine with an automatic exit (SYNTHESIS §3.5).

**Dormant areas.** Parts with no new leaves and no reads for six months collapse in the contents under "Earlier topics". This is display state. IDs and numbers do not change. It keeps history available without being in the way [02 pitfall 8, impl 9].

### 7.4 Reversible reorganization

Every structural change is a typed event in the book ledger: `move`, `split`, `merge`, `rename`, `promote`, `demote`, `graduate`, `retire`. Each records before and after, the job and edition, and the objective gain that justified it. To reverse one, you click "put it back" on the section or in the edition notes. That becomes a correction ("must be under" the old chapter), so the move cannot come back (I21). The maintainer can also roll back a whole edition by compensating events selected by job or model [13 §F.10].

### 7.5 What changed since you last read

- **Reader state** (local, per user): for each section, the last time you viewed it and the block fingerprints you saw. It is stored in a separate reader table, never in the knowledge ledger, never in AI packs. It is covered by excision and can be switched off.
- **On a section page:** a banner such as "Changed since you read it on 2 Oct: 1 new explanation (ChatGPT, 5 Oct); 1 claim corrected." New and changed sentences are highlighted by comparing citation sets, which is deterministic.
- **On the home screen:** "Since your last visit" lists new sections, changed sections, moved sections, newly answered questions and new goals, at most 7 lines, with "see all".
- **In each edition's notes:** every move, split, merge, rename and renumbering, with links.

### 7.6 How understanding evolved over time

- **Section history tab:** every version of each block by edition, with a sentence diff.
- **Section timeline:** first encountered, each explanation and who gave it, your questions, your conclusions, supersessions, verification results, corrections. All from events, in order.
- **Book timeline:** month by month, what was added and changed, and which goals opened or closed.
- **Read as of a date:** open any past edition exactly as it was. Past beliefs are shown as quoted, dated records, never re-narrated in fluent prose, because narrating someone's past back to them can implant false memories [01 F11, pitfall 9].

---

## 8. Corrections

### 8.1 Kinds, in one click

Every sentence, block, section, chapter and part has a small menu. Each choice writes one typed correction event with holder `user` and origin bound as user-typed (I20).

| Menu choice | Correction | Effect |
|---|---|---|
| This is wrong | Content: either reject (no typing) or type the right statement | Rejected item leaves current blocks; a typed statement supersedes it with `reason: user_correction` |
| Wrong speaker / not mine | Attribution fix | Chips and template sentences use the corrected attribution |
| Outdated | Supersession by you | Moves to "How your understanding changed" |
| Move to… / Doesn't belong here | Placement: must be under / must not be under | Hard constraint in clustering |
| Rename | Fixed label | Title never changed by the maintainer |
| Same thing as… / Not the same | Merge (alias) / unmerge (keep apart) | Reversible alias event (I12) |
| Not a prerequisite / Wrong order | Reject a relation | Edge removed from ordering and the frontier |
| Not my goal / Done | Goal status | Frontier recomputed |
| Already answered | Question status | Moves to answered, optionally linked |
| Hide | Hidden from the book | Not deleted; still in the ledger and in search filters |
| Put it back | Undo a reorganization | "Must be under" the previous chapter |

Excision (permanent removal) is separate, starts only from you, and asks to confirm (SYNTHESIS §5.9).

### 8.2 Corrections through chat

- One MCP write tool, `northstar_correct(target_id, kind, payload, user_quote)`. The in-chat slice shows target IDs, so the chat model can name the target.
- Tool calls by the chat model are untrusted input (SYNTHESIS §3.5). So a chat correction must quote your message. On Claude Code and Codex, code checks the quote against the verbatim prompt that the `UserPromptSubmit` hook receives (code.claude.com/docs/en/hooks and learn.chatgpt.com/docs/hooks, per [10], checked 2026-10-07). On the desktop chat apps, the product's own tool-approval prompt is your explicit action, and the correction shows in the book as "correction via chat, from your message: '…'" with the capture fidelity chip.
- Claude asks permission before a tool call (Allow once or Always allow) (claude.com/docs/connectors/getting-started, per [10], checked 2026-10-07). ChatGPT asks for confirmation of write tools once per conversation (developers.openai.com/api/docs/guides/custom-mcp-server, per [10], checked 2026-10-07). A correction is an occasional, explicit act, so one approval is not a ritual.

### 8.3 Precedence in every compile stage (I21)

| Stage | How corrections apply |
|---|---|
| J7.1 graph | Rejected relations removed; merges and unmerges applied |
| J7.2 assignment | Hidden and rejected items excluded from current blocks; attribution fixes applied |
| J7.4 writer | Rejected items not in the allowed citation set |
| J7.5 validate | V9 rejects any draft that contradicts a correction |
| J8.1 cluster | Fixed parents, forbidden parents, keep-together and keep-apart as hard constraints |
| J8.2 labels | Fixed titles are never proposed |
| J8.3 gate and J7.6 render | A deterministic check that every active correction holds. If one fails, nothing is published (hard gate, B6) |

A correction is lifted only by you, or by excision of its target.

### 8.4 When later evidence disagrees with a correction

The correction stands. The block shows a chip: "New evidence since your correction (ChatGPT, 9 Oct)", linking to the leaf. Nothing is escalated to you (SYNTHESIS §3.2). Every correction also becomes an L6 label for calibration [13 §D].

---

## 9. The interface

### 9.1 Choosing the medium

| Option | For | Against | Verdict |
|---|---|---|---|
| **Local web app**, pre-rendered pages plus a thin script layer, served by the local core | Rich typography, side panels for provenance, search, one-click corrections; reads offline; same code later in the cloud; no editor to build (SYNTHESIS AD15) | Needs the local service running | **Primary** |
| Obsidian-compatible vault as the primary view | Existing editor and plugins; plain files outlast apps [02 F8] | Your edits would collide with compiled output; no structured corrections; the default graph view is a hairball [02 pitfall 4] | **Read-only mirror** only |
| Published artifact page | Easy to share | Hosted in the cloud, not local; not a live view of the core | No |
| MCP App panel as the primary view | Already inside the chat | Small, tied to one product, unverified persistence [10 F2] | **In-chat slice** only |
| Native desktop app | Polished | Build cost; no extra value now | Later, as a wrapper if needed |

**Decision.** The book is a local web app at a localhost address. J7.6 writes pre-rendered HTML for every section, chapter and appendix, so reading needs no model call and works offline. A small script layer adds search (SQLite FTS5 through the local API), the source card, corrections and reader state. J7.6 also writes a read-only Markdown mirror per edition (one file per section, IDs in front matter, citations as footnotes), so the knowledge outlives the app [02 F8].

### 9.2 Layout and navigation

- **Left:** contents tree (Parts, Chapters, Sections) with numbers, collapsible, current place highlighted, "also in" cross-references.
- **Centre:** the reading pane.
- **Right margin:** source cards, change markers, and an optional local map of the chapter (at most 2 hops, filtered by relation type). No global graph [12 F15].
- **Top bar:** search, Home, Goals, Since your last visit, edition selector.
- **Reading flow:** breadcrumbs, previous and next section in reading order, keyboard navigation.
- **Term links:** the first use of a glossary term in a section links to its definition, with a hover card. Code does this from the alias dictionary.
- **Back matter:** Glossary, Index, Sources, Timeline, Open questions, Editions.

### 9.3 The first screen

```
Northstar · Your book                         [ Search ]          Edition 14 · updated 06:10
───────────────────────────────────────────────────────────────────────────────────────────
WORKING TOWARD                                  NEXT TO LEARN
• Build an offline-first sync layer             1  CRDT basics — builds on §III.2.1, §III.2.3 (covered)
  (you, Claude Code, 2 Oct)                     2  Vector clocks — you asked on 4 Oct (ChatGPT); not answered
  6 sections covered · 3 ahead · 2 questions    3  Check: "IndexedDB has no size limit" (ChatGPT, 3 Oct)
• Understand HTTP caching (you, 12 Sep)            — unchecked, and you relied on it on 5 Oct
  9 sections covered · 1 ahead · 1 question     4  …
                                                
SINCE YOUR LAST VISIT (2 Oct)                   CONTINUE READING
• New  §III.2.4 Last-writer-wins (Codex, 6 Oct) §II.4.3 no-cache and no-store
• Changed  §II.4.3 — 1 claim corrected
• Answered  "Does a CDN treat no-cache…" → §II.4.5

CONTENTS
Part I  Foundations (4)   Part II  Web performance (6)   Part III  Data sync (4)   Ahead: new territory (1)
```

Counts are counts of content in the book, with no percentages, bars or scores. All four blocks have fixed slots and at most 7 lines each [01 F9][02 idea 9][12 F15].

### 9.4 Search

- Full-text over section titles, glossary terms and aliases, sentence text and verbatim spans.
- Facets: speaker (you, Claude, ChatGPT, Codex, sources), product, model, date range, verification status, part.
- Results are grouped by section, the landmark, with the matching snippet and its chip.
- Search is deterministic in the prototype. "Ask the book" in natural language is left to the connected chat products, through the slices below.

### 9.5 In-chat slices on the connected products

One MCP server serves all four first connectors. Its read tools return **compiled blocks**, never text written by the chat model, so the slice in a chat matches the book word for word.

| Tool or resource | Returns |
|---|---|
| `northstar_book_section(id or query)` | Section card: title, key idea, top excerpt with chips, sources, "open in book" link |
| `northstar_learned(topic, since?)` | What was learned about a topic, grouped by who taught it |
| `northstar_to_learn(goal?)` | Frontier, open questions and next steps with reasons |
| `northstar_changes(since)` | What changed |
| `northstar_book_toc(part?)` | Contents |
| `northstar_correct(…)` | Write a correction (§8.2) |
| Prompts | "What have I learned about …", "What should I learn next for …" |
| Resources | `northstar://book/section/{id}` |

| Connector | How the slice appears | Product facts (source, date checked) |
|---|---|---|
| **Claude Desktop chat** | MCP App card rendered inline; text tool results; prompts and resources | Claude supports MCP tools, prompts and resources; tool results up to about 150,000 characters on claude.ai and Desktop (claude.com/docs/connectors/building/index, checked 2026-10-08). MCP Apps render inline in Claude Desktop after the user clicks Allow or Always allow (claude.com/docs/connectors/building/mcp-apps/getting-started, checked 2026-10-08). Local servers can be packaged as `.mcpb` (claude.com/docs/connectors/building/mcpb, per [10], checked 2026-10-07) |
| **Claude Code** | Markdown card in the terminal plus the book link; same tools | MCP output defaults to 25,000 tokens, configurable with `MAX_MCP_OUTPUT_TOKENS` (claude.com/docs/connectors/building/index, checked 2026-10-08) |
| **ChatGPT Desktop chat** | Plugin tools; a thread side panel showing the book section for the current conversation | The MCP Extensions spec lists thread entrypoints and model context as Supported on Desktop; its Web column means the Work browser and excludes classic ChatGPT (github.com/openai/mcp-extensions/blob/main/docs/spec.md, checked 2026-10-08). Whether the panel appears in Desktop **Chat** mode, as opposed to Work: (Unv). Composer mentions are desktop-only (developers.openai.com/plugins/build/extensions, checked 2026-10-08) |
| **Codex** (CLI and Codex threads in ChatGPT Desktop) | Markdown card; same tools | The desktop app shares MCP configuration with the Codex host, including `~/.codex/config.toml` (learn.chatgpt.com/docs/extend/mcp, per [10], checked 2026-10-07) |

**Contextual resurfacing without a schedule.** When the AI side's goal router matches a section during a chat, the connector can show one line, "In your book: §II.4.3 no-cache and no-store (Claude, 14 Sep)". On surfaces with no per-turn channel (desktop chat), this depends on the model calling a tool (SYNTHESIS RISK 4). It is a convenience, never a requirement.

**No self-citation loop.** If a chat model repeats a slice in its reply, that reply is AI-said content like any other. Its lineage is tagged `northstar_echo`, so it never counts as an independent source for the item it repeats (I11; SYNTHESIS RISK 11).

### 9.6 Local now, cloud later; personal now, enterprise later

- **Local now:** the core, the compile jobs, the static pages and the MCP server run on the user's Mac. The book needs no public endpoint. Local MCP covers Claude Desktop, Claude Code, Codex and ChatGPT Desktop's local threads.
- **Cloud later:** the same jobs run next to a cloud core. The same pre-rendered pages are served with sign-in, which adds phone and tablet reading. Nothing in the book format changes.
- **Scopes:** the book compiles per scope (I17). Sensitive scopes stay out of the Markdown mirror and cloud sync unless the user allows them.
- **Enterprise later:** one book per person. Shared team scopes could add shared chapters later; the scope model already allows it. Out of scope for the prototype.

---

## 10. What the maintainer checks

### 10.1 Book invariants, enforced by code

| # | Invariant | On violation |
|---|---|---|
| B1 | Every R and B sentence cites a leaf (I8) | Sentence rejected |
| B2 | Writers receive leaf IDs and span text only (I7) | Job refused by the input assembler |
| B3 | Every quote is exact (I1, I2) | Quote rejected |
| B4 | No model-written attribution (V3) | Sentence rejected |
| B5 | Every eligible active leaf has exactly one home block and is reachable; no leaf disappears without a recorded event (I9) | Edition held; block re-run |
| B6 | Every active correction is honoured (I21) | Nothing published |
| B7 | The outline is a tree; reading order is a valid topological order of the reduced prerequisite graph | Edition held |
| B8 | No section, chapter or part ID disappears without a typed event and a redirect | Edition held |
| B9 | Churn within budget per edition (I13) | Edition held, retried next week with a higher stability weight |
| B10 | Hash-identical rebuild with model access off (I18) | Alert; render frozen at the last good build |
| B11 | AI-said share of book leaves within 5 points of the core's eligible share | Alert, sentinel hit |
| B12 | Stub sections contain only T and Q sentences | Stub rejected |
| B13 | Grounded tokens (V4) and hedges (V5, I10) | Sentence rejected |
| B14 | Scope filter on every page, export and slice (I17) | Page withheld |
| B15 | Echo lineage never counts as support (I11) | Event refused |
| B16 | After excision, a grep over pages, mirror, block versions, editions and slice cache returns 0 hits | Excision job retried; alert |

### 10.2 Model-based checks and audits

- **L2:** V10 entailment on every new R and B sentence, by a verifier of a different family. The working assumption is the local open-weight verifier (AD9, spike S10). If it fails its calibration bar, the fallback is 100% of B sentences and 20% of R sentences on a second vendor's API, if the user allows a second vendor (SYNTHESIS Q4 answered as a HOW decision; RISK 18).
- **L4:** each day the strongest model audits 5% of compiled blocks and every chapter overview against their leaves. Disagreement feeds the error budget.
- **L5:** golden and canary sets (§13) run nightly and on any prompt or model change.

### 10.3 Error budget, sentinels and fault injection

- **Error budget:** if audited entailment errors among published sentences exceed 2% over a rolling 7 days for a block type, model prose for that block type freezes. Those blocks render by the extractive fallback until a fix passes the canaries. Nothing waits for the user [13 §F.9].
- **Sentinels:** share of blocks on fallback; tentative placements and their age; held editions in a row; label churn; A→B→A moves within four editions; AI-said parity (B11); stubs older than 60 days with no new leaves.
- **Fault injection** (SYNTHESIS §7.4): degrade the block writer and the labeller one at a time: a weak model, padding, a missing card, a prompt bug, shuffled citation IDs. Targets: 100% of structural errors blocked by B1–B16; the fallback engages; the error budget trips within one daily cycle; rollback by job or model rebuilds hash-identical pages.

---

## 11. Non-goals

- **No quizzes, flashcards, mastery scores, progress percentages, streaks or "due" lists.** Not in the product, not hidden in the UI.
- **No required routine.** No inbox to process, no review queue, no required reading, no required corrections. Held editions and tentative placements resolve automatically.
- **No global graph view by default.**
- **No hand editing.** The book is not a notes editor. Corrections are structured events. The Markdown mirror is read-only.
- **No invented teaching.** The compiler explains structure and restates what was said, with citations. It does not write new explanations (pending Q1).
- **No model prose above the chapter level.**
- **Optional retention aid: not built in the prototype.** A possible later aid would be an "explain it in your own words" margin prompt, off by default, used only if the user asks for it (Q2). The book delivers its full value without it, and no evaluation in §13 depends on it.

---

## 12. What the core must hold

The system spine must provide these, so the book can be compiled.

| Need | Core record or field | Status in SYNTHESIS |
|---|---|---|
| Stable concept IDs, preferred term, aliases, reversible merges and splits | Concept; `same_as` alias events | §3.1; I12 |
| **One primary concept per item** | `Item.primary_concept` | **New** |
| Item role and kind tags, including definition, explanation, example, comparison, procedure, claim, insight, decision, belief | Item role + kind tags | §3.1 roles; **the passage kinds must be guaranteed tags from J3** |
| A leaf-level gist per item, verified against its span | `Item.gist` | [12 impl 2] |
| Attribution axes: speaker, model, product, stance, verification (with verifier and evidence), capture fidelity, certainty | Attribution, Stance, Verification | AD6; I3, I4, I10 |
| Span anchors with exact quote, prefix, suffix, and access to surrounding turns | Span; source-generic anchor | §3.1; I1, I2 |
| Episode metadata: product, conversation ID, **title**, start time, **deep link if any**, model and browsing flag per message | Episode, Message | §3.1; **title and deep link new** |
| Typed relations with status and confidence: prerequisite (direction-checked), part_of, broader, explains, example_of, compares, answers, advances-goal, supersedes, contradicts, same_as | Relation | [12 Model A] |
| Supersession reason and an optional **causal-alternative leaf** ("why the old view seemed right") | Supersession record | §3.1; **causal-alternative ref new** [01 F5] |
| Best rank, rank reason, contested flag, Tension records | Item, Tension | §3.1; AD19 |
| Goals (explicit or inferred, status, targets, evidence spans) and questions (raised_by, status, answers) | Agenda | [12 Model C] |
| Engagement events | Event | §3.2 |
| Corrections: kind, target, constraint form, active or lifted, origin span | Correction event | §3.2; I21; I20 |
| Lineage tags, including `northstar_echo` | Attribution.lineage_origin | I11; **echo tag new** |
| Scope and sensitivity | Item.scope | I17 |
| Ledger watermarks and as-of queries | Event ULIDs | I6; §5.3 |
| Excision tombstones that reach derived stores | Tombstone | §5.9 |
| Recorded model outputs (job, model, prompt hash, input fingerprint) | Job and output tables | [13 §A.4] |
| Embedding cache keyed by item or concept version and model | Cache | §6 |

**What the human architecture owns** (derived, append-only, never canonical knowledge): the book ledger of outline events; outline snapshots per edition; content-addressed block versions and sentences with citations; validation records; the render cache; and reader state, kept separate from knowledge and covered by excision.

---

## 13. Evaluation

Adapted from SYNTHESIS §7.3. Every check is automatic. **No user sessions are required.** Bars are proposed, recalibrated once after a pilot, then frozen (SYNTHESIS §7).

### 13.1 Golden set with a known textbook

The hidden-world golden set (SYNTHESIS §7.4) is extended: each synthetic persona's knowledge is generated from a known public syllabus. Its chapter structure and prerequisite order are therefore known, so structure quality can be scored. One non-chat document is included, to show the book accepts it unchanged.

### 13.2 Checks and bars

| Check | Measure | Bar |
|---|---|---|
| Provenance completeness | Sentences that resolve to a leaf and a span | 100% (hard gate) |
| Attribution | Model-written attributions | 0 (by V3) |
| | Chip accuracy on the golden set; false endorsement | ≥ 98%; ≤ 5% |
| Citation faithfulness | Entailment by an independent judge family, on sampled R and B sentences | ≥ 97% entailed |
| | Grounded tokens; hedges and rare details kept after 5 regenerations [S1 E7] | 100%; ≥ 95% |
| What-has-been-learned coverage | Golden knowledge items, user-stated and AI-taught, reachable in the book with sources | ≥ 95% |
| AI-said coverage | AI-taught coverage minus user-stated coverage | within 5 points |
| Structure quality | Chapter agreement with the known syllabus (adjusted mutual information); section-order agreement (Kendall tau) | Beats random and a flat topic-clustering baseline; target AMI ≥ 0.6 |
| Prerequisite validity | Precision and direction, against the syllabus | Precision ≥ 0.8 on edges used for ordering |
| Textbook form | Defined-before-used rate: terms used in a section that are defined earlier in reading order or linked | ≥ 90% |
| | Prerequisite violations in reading order | 0 |
| | Non-stub sections with a key idea and at least one explanation | 100% |
| | Sections whose core leaves include an example that show it | 100% |
| | Near-duplicate sentences across the book | ≤ 2% |
| | Rubric judge (independent family, calibrated on real textbook sections, wiki pages and chat logs), pairwise "reads more like a textbook chapter" | ≥ 70% wins vs a chronological feed and vs a self-rewriting wiki, at equal or better faithfulness |
| Helps understanding (proxy) | A simulated reader of another family, given only the rendered book at a matched token budget, answers golden questions: what, why, who taught it, how it changed, what is next. Baselines: raw transcripts, a flat fact list, a chronological feed | ≥ 15 points over the best baseline |
| Helps finding and remembering (proxy) | A navigation agent with contents and index only (no search) reaches the answering section | ≤ 3 hops in ≥ 85% of cases |
| Stability | Section moves per edition; title churn per week; broken IDs; A→B→A within four editions; landmark survival (top-viewed sections keep chapter and title over four editions) | ≤ 5%; ≤ 3; 0; 0; ≥ 95% |
| Correction survival | Active corrections honoured after 10 rebuilds and reorganizations | 100% (hard gate, I21) |
| Fragmentation | Duplicate sections against the golden set; tentative placements and their age | ≤ 5%; none older than 14 days |
| What-to-learn validity | Open-question precision; **frontier predictive validity**: share of frontier items you later engage with, against random and popularity baselines (passive, from events) | Above both baselines |
| Robustness | Fault injection (§10.3) | 100% structural errors blocked |
| Navigability (optional, one-off) | Time to answer "what have I learned about X, and from whom?" in the book vs raw chats | Optional; never required |

### 13.3 Baselines

- **B-feed:** a chronological feed of items with chips.
- **B-wiki:** Karpathy-style pages the model rewrites in place on each ingest [12 F7].
- **B-tree:** a RAPTOR- or Clio-style topic tree with summaries of summaries at upper levels [12 F4, F16].

The book should match their readability and beat them on faithfulness, stability and coverage of AI-taught content.

### 13.4 What cannot be measured without the user

Whether reading the book improves the user's own unaided recall cannot be measured without the user's participation. This design measures proxies and says so. It does not lower the goal: "helps understand and remember" stays the target, and the gap is RISK RB7.

---

## 14. Prototype scope for the human side

| In the prototype | Later |
|---|---|
| J7.1–J7.7 and J8.1–J8.3 with B1–B16, V1–V10, fallback, error budget | Model-proposed clustering hints |
| Local web app: home, contents, sections, source cards, goals and frontier, since your last visit, glossary, index, sources, timeline, open questions, editions | Cloud hosting and phone reading |
| One-click corrections and `northstar_correct` | Corrections by editing the Markdown mirror |
| Read-only Markdown mirror | Native wrapper |
| MCP read tools for all four connectors; MCP App card in Claude Desktop | ChatGPT Desktop thread panel (pending the Chat-mode check) |
| §13 evaluation with the golden set and baselines | Optional retention aid (only if Q2 says yes) |

Build order for the human side: the compiler and local web view first, because they need no connector and can run on the golden set. Then the MCP read tools, which serve all four connectors from one server. Then the Claude Desktop MCP App card. Then the ChatGPT Desktop panel. Claude Code and Codex give verbatim capture of both sides through hooks (`UserPromptSubmit.prompt`, `Stop.last_assistant_message`; code.claude.com/docs/en/hooks and learn.chatgpt.com/docs/hooks, per [10], checked 2026-10-07), so they give the book its best data first; the desktop chats arrive with paraphrase fidelity until the spine reconciles them (§4.4).

---

## 15. Questions for the user

Only questions that touch the WHAT. Each has a working assumption, used for design and spikes only, never treated as your answer.

1. **Gap-filling.** The book organizes and restates what you and the AIs actually said. For a topic on your frontier that no conversation has explained yet, should Northstar ever add an explanation, for example by asking an AI to explain it and filing that as a new, attributed conversation? Or suggest topic names that no conversation mentioned?
   - *Working assumption:* no. Stub sections show only what conversations said about the gap (§5.4). The AI's own replies to your goals usually name the topics you need, and those seed the frontier, attributed as AI-said.
2. **How strong "remember" must be.** The book helps remembering through structure, gists, episodic cues, refutation of changed beliefs and in-chat re-encounters. The evidence says reading an AI-built structure helps less than building or recalling it yourself (g = 0.43 vs 0.72 [12 F14]; rereading is low-utility [01 F8]). Is this passive design what you mean by "help me remember", or would you want an optional, off-by-default "explain it in your own words" aid? It would never be a quiz or a score.
   - *Working assumption:* passive design only; no aid built in the prototype; the trade-off is recorded as RISK RB7.

---

## 16. Risks

| # | Risk | Threatens | Mitigation | Links |
|---|---|---|---|---|
| RB1 | Restated prose can distort meaning in ways entailment checkers miss; automatic verification agrees with humans only about 72–76% of the time | §3.2 traceability; §6 "each item shows its sources" | Prose limited to three block types; quotes do the teaching; grounded-token and hedge checks; L4 audit; error budget with extractive fallback | [12 F9]; SYNTHESIS RISK 6 |
| RB2 | Strict citation rules and many quotes may read as choppy rather than like a textbook | §3.2 "reads like a textbook" | Key idea and bridge sentences; consistent template; textbook-form metrics and rubric judge; tune excerpt length | §13 |
| RB3 | Clustering of personal, uncurated topics may give odd chapters; prerequisite edges are noisy (F1 about 0.7, reversed direction common), so order can be wrong | Understandability | Direction check; order only within chapters and parts; reasons shown; one-click reject; golden-set structure bars | [12 F11, F16] |
| RB4 | Stability and freshness pull apart: weekly editions delay better structure, and new knowledge lands in tentative places | §4.3 vs usable landmarks | Two cadences; landmark weights; churn budget; tentative marker; the rail shows new leaves at once | SYNTHESIS RISK 15 |
| RB5 | On Claude Desktop chat and ChatGPT Desktop chat, AI-taught text arrives as the model's paraphrase until reconciled, so the "path to the verbatim span" may end at a paraphrase for a while | §4.2, §3.2 traceability, on two of the four first connectors | Capture-fidelity chip; honest anchor to the tool payload; automatic upgrade on reconciliation; the spine owns the fix | SYNTHESIS Table A, RISK 4 |
| RB6 | AI passages dominate volume; showing only the top k could become soft demotion of what AIs taught | §4.2 | Everything reachable; speaker-neutral rank; parity sentinel (B11); AI-said coverage bar | [12 R4]; AD7 |
| RB7 | A fluent, well-organized book raises felt understanding more than real understanding, and passive reading is the weaker way to learn | §3.2 "understand and remember" (no non-negotiable broken) | Sources and verification always visible; contested kept open; in-chat re-encounters; Q2 | [01 F10, pitfall 6][12 F14]; SYNTHESIS RISK 17 |
| RB8 | The book grows to thousands of sections and starts to feel like a mausoleum | Usability | Fixed home slots of at most 7; dormant parts collapse; search by speaker and date | [02 pitfall 8] |
| RB9 | Verifier independence: with one vendor, entailment checks are not independent | §4.7 | Local verifier of another family (S10); second vendor only if allowed | SYNTHESIS RISK 18 |
| RB10 | Reader state records what you read | Privacy | Local only, separate from knowledge, never in packs, can be switched off, covered by excision | SYNTHESIS §5.9 |
| RB11 | A model or prompt migration rewrites much prose at once | Stability | Sentence reuse; migrations run in shadow on the golden set first [13 §F.13] | §6.10 |
| RB12 | Path-dependent structure: two fresh builds from the same core can differ | Reproducibility | Rebuild means replaying the book ledger; this is recorded and tested (B10) | §6.13 |

---

## 17. Goal-fidelity check

| GOAL item | Where this design meets it | Status |
|---|---|---|
| §3.2 what has been learned, from you and from AIs | §3.2 blocks; §4 attribution; AI passages as main text | Met by design |
| §3.2 what to learn | §5: goals, questions, frontier, forward chapters, next steps | Met by design; frontier quality bounded by prerequisite noise (RB3) |
| §3.2 reads like a textbook; understand and remember | §3 anatomy; §3.5 evidence; §13 textbook metrics | Met by design; remembering measured by proxy only (RB7, Q2) |
| §3.2 traceable to who said it and which conversation | §4.3 source card; V1–V3; B1–B4 | Met; desktop chat paraphrase gap flagged (RB5) |
| §3.2 not a quiz or mastery score | §11; §5.2 defines learned as content | Met |
| §4.1 no rituals | No inbox or queue; held editions retry automatically; corrections optional | Met |
| §4.2 AI-said first-class | §4.2; B11 parity; coverage bar | Met; RB6 watched |
| §4.3 AI manages, correction optional and persistent | §6 automatic compile; §8; I21 hard gate | Met |
| §4.4 two architectures, one core | The book is a separate projection; §12 lists what it needs from the shared core; AI packs are not touched | Met |
| §4.5 drift and continuity | Out of scope for this document. The book adds no load to the AI side; its slices are read-only and tagged against echo loops | Not weakened |
| §4.6 product-agnostic, four first connectors, local now, cloud later, personal first | §9.5 one MCP server for all four; §9.6 | Met; ChatGPT Desktop Chat-mode panel (Unv) |
| §4.7 robust maintainer | §6.9 fallback; §10 invariants, audits, error budget, fault injection | Met for structure; semantic prose errors bounded statistically (RB1) |
| §4.8 prototype built and evaluated | §14 scope; §13 evaluation | Planned |
| §5 constraints: attribution, supersede not overwrite, never summarize summaries, context rot, sycophancy, injection | §4; §7.2; §6.8, §6.11; slices small and labelled; third-person chips, no attribution in prose; slices are quoted data, echo lineage tagged | Met |

No requirement is narrowed by this design. The places where the goal is at risk are RB1, RB5, RB6 and RB7, and the two questions in §15.

---

## Sources

**Project notes (local):** `docs/GOAL.md`; `docs/research/round2/SYNTHESIS.md` (§3.1, §3.2, §3.5, §5, §7.3, §7.4, RISKS 4, 6, 11, 15, 17, 18); `docs/research/round2/10-integration-surfaces.md`; `12-knowledge-structure.md`; `13-robust-ai-maintenance.md`; round-1 notes `01-human-memory-and-learning.md`, `02-pkm-practice-and-failure.md`, `07-human-vs-ai-consumers.md` (evidence only).

**Product facts checked for this design**

| Fact | Source | Checked |
|---|---|---|
| Claude supports MCP tools, prompts and resources; no resource subscriptions or sampling; tool results about 150,000 characters on claude.ai and Desktop; Claude Code MCP output 25,000 tokens by default | https://claude.com/docs/connectors/building/index | 2026-10-08 |
| MCP Apps render inline in Claude Desktop after Allow or Always allow; local example servers connect through `claude_desktop_config.json` | https://claude.com/docs/connectors/building/mcp-apps/getting-started | 2026-10-08 |
| ChatGPT MCP Extensions: thread entrypoint and model context Supported on Desktop; "Web refers to the Work browser; classic ChatGPT is excluded" | https://github.com/openai/mcp-extensions/blob/main/docs/spec.md | 2026-10-08 |
| Thread side-panel entrypoints (`type: "thread"`); composer mentions desktop-only; web extensions "coming soon" to Free and Go | https://developers.openai.com/plugins/build/extensions | 2026-10-08 |
| Claude Desktop local MCP via `.mcpb` | https://claude.com/docs/connectors/building/mcpb | 2026-10-07, via [10]; not re-checked |
| Claude asks before tool calls (Allow once, Always allow) | https://claude.com/docs/connectors/getting-started | 2026-10-07, via [10]; not re-checked |
| ChatGPT write tools need confirmation once per conversation | https://developers.openai.com/api/docs/guides/custom-mcp-server | 2026-10-07, via [10]; not re-checked |
| ChatGPT Desktop shares MCP configuration with the Codex host (`~/.codex/config.toml`) | https://learn.chatgpt.com/docs/extend/mcp | 2026-10-07, via [10]; not re-checked |
| Whether the ChatGPT Desktop thread panel appears in Chat mode | none found | (Unv) |
| Model prices behind the cost estimate | [13 §I] | Not re-checked (Unv) |
