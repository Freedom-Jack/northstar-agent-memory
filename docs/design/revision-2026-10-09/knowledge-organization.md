# Knowledge organization: integration, subdivision and consolidation

**Status:** proposal, revision of 2026-10-09, answering your comment 3 (GOAL §1, §2). It describes a method, not an implementation. Nothing is approved or built; the approval process is unchanged (GOAL §7).

**Authority:** [GOAL.md](../../GOAL.md) overrides this document; your answers of 2026-10-09 override everything earlier. It changes only the HOW. §10 lists the spec sections it would replace.

**Reads with:** [ARCHITECTURE.md](../ARCHITECTURE.md) §3, §4, §8; [TEXTBOOK.md](../foundations/TEXTBOOK.md) [TB] §4, §7–§9, §13; [maintainer.md](../components/maintainer.md) [MT] §4; [core-data-model.md](../components/core-data-model.md) [CDM] §2.2; and [personal-relevance.md](personal-relevance.md) [PR], this revision's relevance design. [PR] decides *whether* material is organized; this document decides *where and at what level*, and how that changes over time.

**Conventions:** "(estimate)" marks a starting value, calibrated once on the golden book, then frozen (TB §13.1). Sample content is invented. No product facts are used, so nothing is labelled (Unv). Tags [01]–[14] point to `docs/research/`.

---

## 0. The short answer

**Can the method evolve the structure in both directions?** Partly today: it splits and merges chapters by size and merges two names for one idea, but cannot grow a section into a subsection or a page into a chapter, fold back, merge overlapping branches or generalize across branches (§8). With these changes, yes, with one limit: Northstar cannot state a broader principle that nobody stated. Across branches it can show what related pages share, in sentences that each cite their pages ("In 4.2.3, 3.2.2 and 5.1.6, derived state is rebuilt from its inputs"), but a general claim of its own needs a source, yours or an AI's, that states it (§5.3).

**The method.**
1. **Two layers.** The core holds *what the ideas are* (concepts, narrower and broader links). The Book holds *how they are presented* (section, subsection, page, chapter). Identity changes are rare, high-risk and audited; presentation changes are computed, budgeted and reversible.
2. **A ladder:** leaf → section → subsection → page → chapter → part. Material moves up when it grows a distinct thread, down when it thins out.
3. **Placement follows your thinking:** an explicit reference, the question or problem it serves, the claim it argues with, the reasoning it continues, then shared concepts. Code decides; models only propose links.
4. **Subdivision needs evidence, not size alone:** cohesive, separable, recurring across conversations, and either large or anchored on its own question, problem or viewpoint.
5. **Consolidation in four forms:** merge two names for one idea; fold a thinned subsection back; merge overlapping branches; **generalize** a principle that emerges across branches.
6. **Overviews never summarize summaries.** Every overview, from a page with subsections to a cross-branch theme, is written from source items selected across its children, at least one per child, with citations. Northstar's own delivered text never comes back as evidence for one.
7. **Stability:** enter high, exit low; triggers must persist; nothing reverses within four editions; inactivity never restructures; every change has a redirect, a reason, an undo and an audit.
8. **Personal relevance gates structure.** Only topics anchored in your thinking, and material that directly supports them, can create or grow structure, and only your agenda can anchor a chapter. Generic material stays in memory, attributed and searchable, but never becomes a page, branch, anchor or theme.

**When unsure,** do what is cheapest to reverse: link rather than move, keep a section rather than split it, keep two ideas apart rather than merge them, wait rather than restructure.

**Platform:** pure core logic, the same on Windows and Mac; one core computes one structure for every machine and phone sharing the memory (GOAL §2, 2026-10-09).

---

## 1. Requirements, and what this uses from [PR]

**Requirements:** connect, extend, subdivide, merge and summarize at a broader level, and explain how (GOAL §2, 2026-10-09); no fragment pile-up, lost history or summaries of summaries (GOAL §1, §5); AI-managed, correction optional (GOAL §4.1, §4.3); relevance decides what is organized (GOAL §3.2); correct when one agent loses focus (GOAL §4.7).

**From [PR]** (computed by code from your acts, never by a model guessing about you, [PR] §2.6):
- **Topic roles** with reasons: **anchored** (part of your thinking), **supporting** (objective material serving it) or **background** ([PR] §2.4). Weak acts must recur on two nightly runs before they anchor a topic.
- **Item roles** inside a topic: **linked** (tied to your act or anchor) or **context** ([PR] §2.4).
- **Anchors**, your intellectual agenda: goals, pursued questions, problems, decisions, issues, interests, projects, pins ([PR] §2.3).
- **`reasoning_thread`**: the chain of answers, reasons, objections, refinements and responses around one of your stances, across products ([PR] §5.1).

Below, a **thread** means an anchor together with its reasoning thread.

---

## 2. The method in one picture

| Layer | Holds | Changed by |
|---|---|---|
| **Core concept graph** | Concepts, aliases, narrower and broader links (several parents allowed), item-to-concept links with one primary | J3, J5, J8c (before each edition), only through Apply; identity changes are high tier |
| **Book outline** | Which concepts get a page, subsection, section or short note; chapters, parts, numbers | J8 (code), from the core graph, roles and growth features, at editions (daily for 14 days, then weekly) |

A concept can live in the core without its own page: as a short note, or as a **section** in its broader idea's page. So the Book can change granularity without changing what the ideas are.

**The ladder:** leaf (one item) → **section** (a page segment: a persistent sub-topic group, optionally backed by a narrower concept; `3.1.4#position`) → **subsection** (a nested sub-page for one narrower idea, one level only, Q-KO-1; `3.1.4.1`) → page (one idea; `3.1.4`) → **chapter, the branch** (3–15 pages anchored on a goal, a thread or an anchored concept; `3.1`) → part (at most 9, plus Part 0 and the Casebook).

| Direction | Operation | Layer |
|---|---|---|
| Integrate | **Attach** a leaf to a section; **extend** a page with a new section (§3) | Core link; Book |
| Subdivide | **Spin off** section → subsection (§4) | Core `MINT_NARROWER` if needed; Book |
| Subdivide | **Branch** page → chapter; chapter → two or → part | Book |
| Subdivide | **Split meaning** (exists, TB §7.9) | Core `SPLIT_CONCEPT` |
| Consolidate | **Merge same idea** (exists, I12) (§5) | Core `SAME_AS` |
| Consolidate | **Fold back** subsection → section; **merge branches** | Book |
| Consolidate | **Generalize**: a broader idea plus an overview page | Core `MINT_BROADER`; Book |
| Either | **Re-parent** (exists) | Core `REPARENT` |

Core operations pass Apply with full high-tier checks: code checks, blind re-labels, a fresh verifier of another family, the daily audit on 100% ([MT] §4.3). Book operations are code, replayable, inside the edition gate (TB §7.2–§7.3).

---

## 3. Where new material belongs

### 3.1 Signals

Each new item arrives with its conversation, its speaker (set by the capture channel, never a model) and its topic's role. Code weights these signals by a fixed table (estimate), like TB §7.2's edges.

| Signal | What it is | Weight |
|---|---|---|
| **Explicit reference** | Your typed words name a page title, label or alias, or quote a stored item; or the item follows a card, slice or pack item on that concept delivered in this chat (context receipts, TB §5.9). AI text counts only when a receipt grounds it, so echoes cannot steer | Very high |
| **Question or problem it serves** | `answers` a pursued question, problem or decision; `advances_goal`; the goal the router gave this chat | High |
| **Claim it argues with** | `refines`, `supports`, `rebuts`, `undercuts`, `responds_to`, `example_of` or `supersedes` an item: it belongs where that claim lives | High |
| **Reasoning it continues** | It joins a `reasoning_thread`; or recent turns of the same chat were on the concept. Decays with turn distance | Medium–high |
| **Shared concepts** | J3's concept tags and primary concept; alias matches | Medium |
| **Similarity** | Full-text and embedding neighbours | Low: finds candidates, never decides |

So placement follows your lines of thought, not surface vocabulary.

### 3.2 The decision ladder

Code walks it for each new item, after Apply has applied its links.

1. **Not organized.** Its topic is background: kept in the core, attributed, searchable, in its conversation's sources-register entry ([PR] §3.4). Stop.
2. **Attach.** Its primary concept has a page and the item fits a section: a J5 relation to a leaf there. Similarity alone (start: cosine 0.75) may pick the section only among the sections of a page already chosen by signals 1–5; it never chooses the page. With neither, the item goes to step 3 (extend) or is placed "tentative". "Just in" rail first, woven in at the next printing.
3. **Extend.** Its concept has a page but no section fits: a new section with a new persistent sub-topic ID.
4. **New narrower idea.** Its concept has a direction-checked `part_of` or `broader` link (≥ 0.7) to a paged concept. It goes under that page: as a **subsection** if it earns its own page ([PR] §4.1, which keeps one-chat AI explanations of anchored topics at full-page parity), otherwise as a **section** (for example, supporting material: [PR]'s "Background used here"). A section grows into a subsection only under §4.
5. **New page.** It earns a page under [PR] §4.1 and has no paged broader idea. Code places it in the best-scoring chapter if that passes a floor and beats the runner-up by 1.5× (estimate); otherwise best guess, "placement tentative", "Also in" the runner-up. Issue and question pages ([PR] §5.2) are placed the same way, by their subject.
6. **New branch.** No chapter passes the floor and the page is anchored on a new thread (a goal, pursued question, problem, decision or issue). Tentative until the next edition, where J8 opens a chapter with an insertion number (3.4a), free against the churn budget.

[PR]'s "Why it's here" line gains the top two placement reasons, in code-written words: "Placed here because it answers your question 'Why do my long AI chats lose focus?' (2 Sep) and continues the chat of 14 Sep." A wrong placement is visible and one click from "Move to…".

### 3.3 Code and models

- **Code computes and decides:** candidate concepts (full-text, embeddings, aliases, the chat's active concepts and goal stack, receipts); the direction gate (≥ 0.7), cycle removal, transitive reduction; signal scores, floor, margin and ladder; growth features (§4.1); every threshold, cap and budget; identity-key matches; bridging counts; overview leaf selection, validators and the entailment gate. Roles come from [PR]'s code.
- **Models propose; another family verifies:** J3 picks a primary concept, proposes a new one or abstains, and tags `generalization`; J5 proposes relations; J8c judges "narrower" against "does not fit" and proposes labels (code-checked: words from member leaves, distinct from siblings, TB §7.2); two families must agree that two names are one idea (I12); the Book writer drafts overview prose from selected leaves only.

### 3.4 Ambiguity

- **Which concept?** J3 may link several with one primary, or abstain. An item with no concept stays with its conversation and thread, shows in "Just in" of the thread's chapter, and is revisited by J5's omission probe and J8c.
- **Which page or chapter?** Tentative placement plus "Also in"; clustering settles it at the next edition; no inbox; a sentinel fires on any older than 14 days.
- **One idea or two?** Kept apart as a duplicate candidate until an identity key or two families agree. A false merge hides an idea; a missed one only duplicates it.
- **Section or subsection?** Material that does not earn its own page stays a section until §4's triggers persist.
- **Relevant or generic?** [PR]'s hysteresis decides; while a topic waits, its items are kept, and [PR]'s retro-attach job brings them in if it rises.

### 3.5 Example A: attach and extend

Page 3.1.4 "Why long chats drift" sits in chapter 3.1, anchored on your question "Why do my long AI chats lose focus?" (2 Sep). In a new ChatGPT Desktop chat (3 Oct) you ask whether it matters where your constraints sit in a prompt. ChatGPT explains, in about 180 words, that models use the middle of a long context least. You reply: "so I should restate constraints at the end".

*Signals:* your question follows up your 2 Sep question, and J5 proposes `answers` to it; your reply `responds_to` the explanation; J3's primary concept is an alias of 3.1.4's. The topic is anchored; the explanation is a linked item. *Decision:* no section is close enough, so code **extends** 3.1.4 with "The middle of a long context is used least". Your reply goes under "Your own words"; your question shows "partly answered (ChatGPT, 3 Oct)".

---

## 4. When a topic subdivides

### 4.1 Triggers

Code computes these nightly for each section on the page's **leaf graph** (its leaves, linked by TB §7.2's edge table at leaf level). Fixed-seed clustering, starting from the persistent sections, finds candidate sub-threads.

| Trigger | Measure | Start (estimate) |
|---|---|---|
| **Size** | Active linked leaves (context leaves do not count) | ≥ 8 |
| **Distinct thread** | An anchor specific to it: your pursued question, problem, decision or issue, a goal target, an AI-raised question you took up; or questions about it in ≥ 2 independent conversations (echoes count once, I11) | ≥ 1 |
| **Cohesion vs separation** | Outside-link share: the share of its link weight going to the rest of the page | ≤ 0.35 |
| **Persistence** | Independent conversations; consecutive nightly runs | ≥ 2; 2 runs |
| **Relevance** | Topic role | Anchored or supporting |

**Rule:** spin off when relevance, persistence and cohesion hold, **and** either size ≥ 8 or a distinct thread with ≥ 4 linked leaves. Size alone never splits an incoherent page; a distinct thread alone never makes a thin subsection. **Size pressure:** a page with more than 5 sections for 2 editions lowers the size bar to 4 for its most separable section.

### 4.2 Kinds of subdivision

- **Section → subsection.** At the next edition after §4.1 holds. If the section has no concept, J8c proposes `MINT_NARROWER` (label from its leaves, `part_of` the page's concept, direction-checked), and its leaves take it as primary concept. The parent keeps its general leaves and gains "Sections of this idea".
- **Page → chapter.** A page has ≥ 3 subsections, and clustering separates its subtree from the chapter above the landmark-weighted threshold for 2 editions. A new chapter with an insertion number; the page becomes its anchor page; subsections become pages. **Page IDs stay**; numbers redirect. Code records the chapter's **formation overlap ratio** (§5.1's overlap measure against the chapter it left), which sets its exit bar (§6.1).
- **Chapter → two** (exists): over 15 pages, or a split that beats the stability cost (TB §7.2).
- **Split meaning** (exists): anomaly marks pass a threshold; new concepts; the old page becomes a chooser, then redirects (TB §7.9).

**Narrower or different?** If the leaves fit the page's key idea and a verified `part_of` holds, it is a narrower idea: spin off. If they contradict or do not fit it (J5 `misfits`), it is a different idea: split meaning or re-parent.

**Depth:** Part › Chapter › Page › Subsection. A subsection's own sub-thread stays a section until its parent page becomes a chapter.

### 4.3 Example B: section → subsection

Over three weeks the section "Pinning state outside the transcript" on 3.1.4 grows to 11 linked leaves from 4 conversations (Claude Code, Codex, Claude Desktop chat). It holds your question "How small can a pin be before it stops helping?", an open question Claude raised that you took up, and your view "pins should be third-person facts". All triggers hold (outside-link share 0.22). J8c proposes `MINT_NARROWER` "State pins"; another family checks it; Apply applies it at high tier.

```
3.1.4    Why long chats drift
3.1.4.1  State pins                                 new subsection · edition 9
EDITION 9 · 3.1.4 grew a separate thread on pinning state (11 sources, 4
conversations, your question of 22 Sep). It now has its own subsection. [Put it back]
```

3.1.4 is recompiled from its remaining leaves plus leaves linked to both (§5.3). `3.1.4#pinning` redirects to 3.1.4.1.

### 4.4 Example C: page → chapter

Two months later 3.1.4 has three subsections, all targets of your goal "build a system that keeps long chats on goal" (20 Sep). Clustering separates the subtree from chapter 3.1 at two editions running:

```
3.1a  Keeping long chats on goal       your goal, 20 Sep · new chapter, edition 14
      3.1a.1 Why long chats drift  (was 3.1.4; same page, same address)
      3.1a.2 State pins (was 3.1.4.1) · 3.1a.3 Drift checks · 3.1a.4 Restarting
```

The goal's targets are at least half the chapter, so it gets a goal anchor (TB §7.2 step 5). It counts as one chapter split.

---

## 5. When branches consolidate

### 5.1 Triggers

| Trigger | Measure; start (estimate) | Leads to |
|---|---|---|
| **Duplication** | Identity key; or shared aliases, near-identical definitions and overlapping leaves, confirmed by two families (I12) | Merge same idea |
| **Thinning** | < 3 active linked leaves (after supersession, merges, rejections) or outside-link share ≥ 0.6, for 4 editions; its anchor closed or none; landmark weight below the move threshold | Fold back |
| **Overlap** | Link weight between two chapters ≥ 0.6 of the smaller one's internal weight, or ≥ 50% of its pages linking strongest into the other, for 2 editions. A chapter formed by page → chapter merges back only at ≥ max(0.6, its formation ratio + 0.15) | Merge branches |
| **Broader principle** | ≥ 3 anchored concepts in ≥ 2 chapters, each linked to an **eligible** general-claim leaf (below) or to your view or question naming the theme; ≥ 2 independent conversations; each `broader` link direction-checked; ≤ 2 new broader ideas a week, inside I13's 20 | Generalize |

**Eligible general-claim leaf** (here, in §5.3 and in §6.1): (a) said by you, with an act that is not an echo (I24; lineage `northstar_echo`); or (b) said by an AI in a chat whose context receipts (TB §5.9) hold **no** Northstar text on that concept or its children, at any overlap. TB §5.9's echo tag uses n-gram containment ≥ 0.6, so a paraphrase of a delivered key idea or "Part of a broader idea" line could escape it; the receipt rule closes that path. The cost: an AI's general claim in a chat where Northstar was already active on the topic cannot seed or keep an overview; §7.3's structural parity watches whether that falls mostly on AI-said material.

**Inactivity never consolidates.** An untouched topic keeps its place and only folds in the contents ("dormant since …", TB §7.4; [PR] §2.7).

### 5.2 Operations

- **Merge same idea** (exists): `SAME_AS`. The page with the higher landmark weight, then the older, survives; the other redirects; "merged from" shows; the old label stays a search alias. Undo: "These are different".
- **Fold back** (new, Book only): the subsection renders again as a section of its parent. **The narrower concept stays in the core**: it is still a valid idea. Its address redirects to the section, whose persistent ID is unchanged.
- **Merge branches** (extends TB §7.2 step 4, which merges only below 3 pages): into the chapter with the stronger anchor; the other retires with `merged_into` and a redirect.
- **Generalize** (new): J8c proposes `MINT_BROADER`, with a `broader` link from each child; the Book adds an **overview page**, homed by §3.2. The children **stay put** and gain "Part of a broader idea: …" in "Where this fits". Clustering may regroup them later, inside the churn budget (Q-KO-2).

### 5.3 Overviews without summarizing summaries

One function, `overview_leaves(node)`, serves a parent page with subsections, a chapter or part big picture, and a cross-branch overview page. It generalizes TB §4.5 ("leaves linked to two or more of the chapter's pages").

1. **Candidates:** active, in-scope leaves of anchored or supporting topics, linked to ≥ 2 of the node's children, or tagged `generalization` and linked to the node's concept; a `generalization` leaf counts only if eligible (§5.1). Echoes (I11) are never candidates. Linked items first; context items only fill ([PR] §4.1).
2. **Stratify:** at least one leaf per child (its top leaf linked to the theme, by the speaker-neutral rank), up to 7 children.
3. **Rank the rest** by children bridged, speaker-neutral rank, and a link to your question, problem or view. **Cap:** 12 leaves, 5 written sentences.
4. **Your views** are quoted by code under "Your own words"; model prose never writes about you (TB §5.7).
5. **Never as input:** page text, key ideas, section prose or another overview; the input assembler type-checks it (B2, I7). Lists such as "Sections of this idea" transclude each child's key idea word for word and are never fed to a model.
6. **What prose may say, by node.**
   - **Parent pages with subsections, chapter and part big pictures** keep TB §4.5: up to 5 B sentences, each jointly entailed by its cited leaves, with the top-leaf fallback for a young chapter or part. No general-claim leaf is required.
   - **Cross-branch overview pages** may state a general claim only when an eligible general-claim leaf (§5.1) states it. Otherwise they may use **conjunctive** B sentences jointly entailed by their leaves ("In 4.2.3, 3.2.2 and 5.1.6, derived state is rebuilt from its inputs"), never a universal claim. Under 2 bridging leaves: no prose, only the code-built list. A theme is never invented.

Overview sentences pass the 15 code validators, 100% entailment by another family and the daily audit (TB §8.5–§8.6). That makes "never summarize summaries" checkable [12 F4]. **The limit, stated plainly:** Northstar can show what your pages share, but it cannot state a principle that nobody stated; that waits for you or an AI to say it.

### 5.4 Example D: merge same idea

"Memory poisoning" (a page, from ChatGPT Desktop chat) and "Prompt injection through stored memory" (a short note, from Claude Code) share near-identical definitions and three claims. Two families agree they are one idea: the page survives, the note's leaves join it, its label becomes an alias; undo is "These are different".

### 5.5 Example E: a principle across branches

Claude explained in 4.2.3 Event sourcing (Claude Code, 12 Sep) "a projection is disposable; rebuild it from the log". You said in 3.2.2 Memory ledger (Codex, 30 Sep) "every derived thing should be disposable; I keep relearning this". ChatGPT explained in 5.1.6 Build caches (3 Oct) invalidation as recomputing from inputs. J3 tags your sentence `generalization`; J5 links it to all three concepts. The trigger holds (3 anchored concepts, 3 chapters, 3 conversations, a general claim that is your view), and J8c proposes `MINT_BROADER` "Derived state is disposable".

```
3.2.5  Derived state is disposable                       overview · edition 21
Explained by Northstar from 6 sources: ◆ Claude 2 · ◆ ChatGPT 2 · ● you 2
KEY IDEA        Anything computed from a record can be dropped and rebuilt from it.
YOUR OWN WORDS  You said (Codex, 30 Sep): "every derived thing should be disposable…"
THE EXPLANATION (written only from the 6 selected leaves, at least 1 per child)
WHERE THIS SHOWS UP IN YOUR BOOK   4.2.3 · 3.2.2 · 5.1.6   (key ideas transcluded)
```

Each child gains "Part of a broader idea: 3.2.5". No page moves; no sentence comes from the children's pages.

---

## 6. Stability, reversibility and corrections

### 6.1 Hysteresis, persistence, dwell

- **Enter high, exit low.** A section spins off at ≥ 8 linked leaves (or ≥ 4 with an anchor) and outside-link share ≤ 0.35, held 2 runs; it folds back only below 3 or at share ≥ 0.6, anchor closed, held 4 editions. A branch forms on a separation gain held 2 editions and merges back only at overlap ≥ max(0.6, its formation ratio + 0.15), held 2 editions after the dwell, or below 3 pages; so a chapter that left its parent at a high overlap cannot merge straight back (A→B→A). An overview retires when its eligible general-claim leaves (§5.1) are superseded or rejected and fewer than 2 children stay linked, held 4 editions; echo-derived leaves never keep one alive. A merge is undone only by your "These are different" or a later two-family split.
- **Dwell (new invariant B17):** no automatic operation reverses a structural change within 4 editions. Your undo and excision are exempt; the A→B→A sentinel stays (TB §8.12).
- **Landmark weight** (opens, in-chat references, corrections; TB §7.2) scales every threshold to fold or move a page; opens from every device add into one weight. It affects only movement, never relevance or placement ([PR] §3.2).

### 6.2 Churn accounting

- **Free, as today (TB §7.3):** new pages, subsections for new concepts, overview pages and chapters; the growth regime (young pages, tentative placements, daily editions for 14 days).
- **Spin-off** moves no page; capped at 3 per edition (estimate), since the parent's text changes.
- **Fold-back** counts as a merge, inside "≤ 2 splits or merges".
- **Page → chapter and merge branches** count as one chapter split or merge; moved pages, and pages regrouped under a theme, count toward "≤ 5% of pages change chapter".
- **Merge same idea** is a redirect, not a move, inside J8c's 20 concepts a week (I13). **A page retired by [PR]'s loss of basis** ([PR] §2.7) redirects to its search answer page and counts as a retire.

An edition over budget is held, never queued; the previous one stays live and the next run retries with a higher stability weight.

### 6.3 Addresses, reversal and audit

- **Page IDs never change**: a spin-off mints an ID for the subsection; a branch changes only numbers. Section anchors are persistent sub-topic IDs; numbers are frozen between editions (TB §7.2); every retired address redirects with a typed `merged_into`, `split_into` or `folded_into` event (B8).
- **Every change is a typed event** with before, after, trigger values and reasons (new invariant B18), shown in plain words in the edition note.
- **Core changes** are high tier: the family rule, the daily audit on 100% within 24 hours, a 2% error budget that freezes the operation type, and rollback by compensating events ([MT] §4.3, §7.3–§7.4). **Book changes** replay hash-identically (B10); rollback is a compensating edition with redirects (TB §8.14). Any page, chapter or the contents can be read as of a date.

### 6.4 Your corrections constrain it

Corrections stay optional, one click, permanent and undoable (I21). Rename, Move to…, Keep it here, Same as…, These are different, Put it back and Doesn't build on this already bind the structure (TB §9.1). Four are added:
- **Give this its own page** (on a section): forced spin-off, never folded back automatically.
- **Keep this on one page** (on a page): no automatic spin-off from it or fold-back into it.
- **Fold this back** (on a subsection): forced fold-back, never spun off again automatically.
- **Not part of this idea** (on an overview's child): its `broader` link is rejected and never re-proposed.

[PR]'s "This matters to me" and "Not part of my thinking" ([PR] §2.8) act here through the gate (§7).

### 6.5 Example F: what folds and what does not

Subsection 4.2.3.1 "Snapshot interval" was spun off when Claude and ChatGPT disagreed and you asked twice. You then settle on fixed 100-event snapshots: the disagreement resolves, 6 of its 8 leaves are superseded, your question is answered. After 4 editions at 2 active leaves, with few opens, it folds back into 4.2.3 as a section; 4.2.3.1 redirects there; history keeps the subsection. By contrast, 3.3.2 "CRDT basics", untouched for five months, is only dormant: folded in the contents, **not moved, not merged**.

### 6.6 When one agent loses focus

- **A linker that links everything:** another family verifies every relation, and triggers read verified links only; merges need two families (I12); caps (I13).
- **A reorganizer proposing many spin-offs or themes:** code triggers decide, not proposals; per-edition caps; rate sentinels against the golden baseline freeze the operation type.
- **A writer inventing a theme:** prose only from selected leaves; on cross-branch overviews no general claim without an eligible general-claim leaf, only conjunctive sentences; 100% entailment; else the code-built list.
- **Wrong roles** (from wrong act records, [PR] §2.6): a sentinel on the background share and on the AI-said share of new structure freezes new structural operations; existing structure stays.

[MT] §8 gains three faults: over-splitting, over-generalizing, a role flip. Each passes when no structural rule breaks and you take no action.

---

## 7. Personal relevance gates what is organized

### 7.1 The gate on structure

[PR] §4.1 decides which topics earn a page, section or note. This document adds the gate on every structural act:

| Act | Anchored | Supporting | Background |
|---|---|---|---|
| Kept in core, attributed, searchable | Yes | Yes | **Yes** |
| Page or subsection | Yes ([PR] §4.1) | A section of the page it supports, or a short note; its own page only if it supports ≥ 2 anchored topics on different pages ([PR] §4.1) | **No** |
| Anchors a chapter; becomes a broader idea | Yes | No | **No** |
| Counts toward split, merge and theme triggers | Yes | Yes (linked leaves) | No |
| Node in the clustering graph | Full weight | Full; links among supporting concepts halved | **Excluded** |

**Nothing is discarded.** The gate decides what the Book organizes, not what memory keeps. A topic that rises later is promoted then, with its earlier records attached ([PR] §2.7, §6).

### 7.2 Structure follows your agenda

- **Chapter anchors** are typed in order: a goal; then a **thread anchor** (a pursued question, problem, decision or issue, [PR] §2.3); then an anchored concept, including an interest. TB's "question anchor" becomes the thread anchor, with the same rule (≥ 3 linked pages, ≥ 40% of the chapter). Projects keep their Casebook chapters.
- **No chapter without a personal anchor.** A candidate chapter whose only possible anchor is a supporting concept merges into its strongest neighbour that has one. Objective material cannot form a chapter of its own, so the Book does not become an encyclopedia.
- **Supporting material lives with what it supports**, placed by the thread it serves (§3.1).
- **Hub dampening:** co-occurrence and similarity links are normalized by each concept's degree, so a term that appears everywhere cannot glue chapters together. [PR] §2.4 applies the same damping to relevance (an inverse-frequency rule over conversations): a hub concept never anchors by recurring weak acts, and a generic prerequisite never becomes supporting or a gap.

This matches the research definition of a personal knowledge graph: knowledge "of personal, rather than general, importance" (Balog and Kenter, 2019 [12 F1]).

### 7.3 AI-said knowledge stays first-class

[PR] §3.1 makes relevance authorship-blind: building on, accepting or applying an AI explanation counts exactly as stating your own view. **The author of the content is never an input** to placement or triggers, and an AI-raised question you took up counts as a distinct-thread anchor. Two deliberate asymmetries remain, stated openly: acts come only from your turns (what "personal" means), and the explicit-reference signal (§3.1) counts AI text only when a delivery receipt grounds it, to stop echoes; §5.1's eligibility rule for general claims is the same kind of echo guard. Parity extends to structure: the AI-said share of subsections, overview leaves, spin-offs and explicit-reference placements stays within 5 points of the eligible share among anchored topics (TB B11, extended). The speaker-swap test holds acts fixed, so it cannot see these asymmetries; this parity check can.

### 7.4 Example G: generic, supporting, background

- **"LLM"** appears in 60 conversations from both speakers; you once asked ChatGPT "What is an LLM?" and moved on, and you type the word in passing in many chats. Today it would become a dangling-term underline, a frontier item and a hub pulling chapters together. Here it is background, by four named rules: your question was a lookup ([PR] §2.5); your other uses are `named`, which is not an act ([PR] §2.2); it is a hub concept, so recurring weak acts cannot anchor it ([PR] §2.4); and, as a prerequisite of many anchored topics that you never asked about or said you did not follow, it is generic, so it is never supporting, a needed term or a next step ([PR] §2.4, §4.2). So: no page, section, anchor, theme or graph node. [PR]'s "Looked up" list and search still find it.
- **A KV-cache explanation.** Working on your drift problem, you ask Claude why 80-turn chats get slow and costly; Claude explains the KV cache. It answers your pursued problem, so it is supporting: a section of 3.1a.1 ("Background used here"), homed with the problem it serves, never a chapter of LLM internals.
- **An unprompted lecture** on the history of transformer models that you never follow up is background: kept and attributed, answering "what did Claude tell me about transformers?", and organized only if you later build on it.

---

## 8. The current design: supports, gaps, changes

**Already supports this** (kept): J3 concept links and J5 relations; the congruence router with tentative placement and no inbox; persistent sub-topic groups; Leiden chapters with warm start, stability cost, landmark weights and size bounds; `SAME_AS` under I12, the duplicate sentinel and the omission probe; meaning split from anomaly marks; chapter and part big pictures from leaves linked to ≥ 2 children; editions, churn budget, permanent IDs, insertion numbers, redirects, as-of views; corrections as hard constraints (TB §4.5, §7, §8.3, §9; [MT] §4.4–§4.5).

| Missing or wrong | Change |
|---|---|
| Placement ignores the reasoning an item continues, explicit references and the claim it argues with; no rule for extend vs new section vs branch | §3 signals and ladder; placement reasons shown |
| Sections group by kind first (definition, mechanism…), so a sub-thread is spread across segments and cannot be measured or spun off | **Sub-topic first, kind second** |
| No subsection level; size rules only warn (V10); a page with sub-threads never becomes a branch | Subsections, spin-off, `MINT_NARROWER`; page → chapter rule (§4) |
| Meaning split conflates "a different idea" with "a more detailed aspect" | Narrower-or-different check |
| Chapters merge only for size; a thinned subsection has no way back; no broader idea can emerge across branches | Overlap trigger; Book-only fold-back; `MINT_BROADER` and overview pages (§5) |
| No split/fold hysteresis, dwell, budget rows or gestures for the new operations | §6; B17, B18; four gestures |
| Generic hubs can anchor or glue chapters; clustering includes every concept | §7 gate, agenda anchors, hub dampening (with [PR] §4) |
| No misplacement, missed-split, missed-merge or structural leakage measures; a syllabus bar rewards encyclopedia shape | §9; scored against each persona's own agenda |

---

## 9. How we test it

### 9.1 Growth scenarios

The golden book's hidden world ledger (TB §13.1) gains a **structure timeline**: per persona, a gold organization that changes on known simulated days, labelled by a family other than the system's and spot-checked by the builder. Planted: **G-ATTACH, G-EXTEND** (gold home is an existing or new section); **G-SPLIT** (sub-threads crossing the gold "own subsection" point, by size or by a distinct question or view) and **G-NOSPLIT** (long, cohesive pages); **G-BRANCH**; **G-DUP** (one idea under two names, often across vendors); **G-CONVERGE** (a principle stated after ≥ 3 topics in ≥ 2 chapters) and **G-FALSE-CONVERGE** (similar vocabulary, no shared principle); **G-FADE** (sub-threads that resolve and thin) and **G-DORMANT** (topics that only go quiet); **G-GENERIC-HUB** (generic terms used everywhere, including a term the persona names in passing in ≥ 2 chats on ≥ 2 days: expected background, no page, no gap, counted in glossary leakage) and **G-SUPPORT** (objective explanations serving a persona's problem); **G-ECHO-THEME** (an AI paraphrases a delivered overview key idea or "Part of a broader idea" line below the 0.6 echo threshold, in later chats on several topics). These join [PR] §7.1's relevance cases.

### 9.2 Measures and starting bars

Estimates, pre-registered, recalibrated once after the pilot, then frozen; each reported for AI-said and user-said material separately.

| Measure | Starting bar |
|---|---|
| **Misplacement:** new organized items homed outside the gold acceptable set after the next edition | Page ≤ 10%; chapter ≤ 15% |
| Tentative placements; settled correctly at the next edition | ≤ 15%; ≥ 80% |
| Signal value: misplacement with each signal ablated | Each signal must help, or it is cut |
| **Missed splits:** G-SPLIT spun off within 2 editions of the gold point (median delay reported) | ≥ 80% |
| Split quality (B-cubed F1 against gold); false splits on G-NOSPLIT | ≥ 0.8; ≤ 10% |
| **Missed merges:** G-DUP merged within 2 editions; false merges | ≥ 80%; ≤ 5% ([MT] §6.5) |
| **Missed themes:** G-CONVERGE overviews within 2 editions; invented themes on G-FALSE-CONVERGE | ≥ 70%; ≤ 10% |
| Overview: gold children covered; sentences entailed; non-leaf inputs | ≥ 90%; 100% (hard); 0 (hard) |
| Echo themes: overviews created or kept on echo-derived leaves (G-ECHO-THEME) | 0 (hard) |
| Branch oscillation: G-BRANCH chapters reversed (A→B→A) within 12 editions | 0 |
| Fold-back: G-FADE folded; G-DORMANT moved or merged | ≥ 70%; 0 |
| **Churn:** T-STAB bars (TB §13.2 F); automatic reversals within 4 editions; landmark survival; broken redirects | As TB; 0; ≥ 95%; 0 |
| Reversibility: after any undo, the as-of projection equals the pre-operation one | 100% |
| Path dependence: gold agreement (AMI) of the day-60 evolved structure vs a fresh clustering of the same data | Within 0.05 |
| **Structural leakage:** chapters, anchors or overviews built on background or supporting-only material; G-SUPPORT homed with its problem | ≤ 5%; ≥ 85% |
| Navigation: T-NAV (TB §13.2 E) for "where does my thinking on X stand?" at days 7, 30, 60, moved pages included | ≥ 85% in ≤ 3 hops |

[PR] §3.1 and §7.2 own page-level relevance measures (relevance recall, glossary leakage, speaker-swap parity).

### 9.3 Baselines and ablations

S0 no evolution (bootstrap structure frozen, pages appended); S1 subdivision only; S2 consolidation only; S3 no hysteresis or dwell; S4 relevance gate off (today's design); S5 fresh clustering every edition (the churn ceiling); BK3, a RAPTOR- or Clio-style tree with summaries of summaries (TB §13.3), for overview faithfulness.

### 9.4 Real data and the baseline-first benchmark

The real-topic, baseline-first benchmark belongs to this revision's evaluation plan; this section supplies structure measures for it.
- **Baseline, without Northstar:** on 3–5 of your real topics, a short timed task, "where does your thinking on X stand, and what changed?", using your chat histories, vendor memory and projects, and any notes. Time, success, a 1–5 rating.
- **With Northstar:** the same task on the Book after the same period of use.
- **A 5-minute add-on to [PR]'s session 2** (short sessions allowed, GOAL §2, 2026-10-09): you mark 10 placements, 3 subdivisions and 3 consolidations from your own Book as right, acceptable or wrong. It is the only real-data misplacement estimate, labelled as a small sample.
- **Passively:** structural corrections per 100 structural operations; reported, not a bar.

---

## 10. Supersedes

Proposed replacements; no spec is edited. Where [PR] replaces the same section (TB §4.7, §6), [PR]'s text stands and this document adds only what is listed.

| File | Section | What changes |
|---|---|---|
| foundations/TEXTBOOK.md | §4.1 Units; §4.3 Page types; §4.4 Concept page | Adds the **subsection** (one nested level, 4.2.3.1) and the **overview page**; a **section** is a segment backed by a persistent sub-topic group, optionally a narrower concept; adds code-built "Sections of this idea" and "Part of a broader idea" in "Where this fits" |
| foundations/TEXTBOOK.md | §4.5; §7.2 step 5 Anchor typing | "Question anchor" becomes "thread anchor" ([PR] anchors); concept anchors only on anchored concepts; no chapter without a goal, thread or anchored-concept anchor |
| foundations/TEXTBOOK.md | §4.7, as replaced by [PR] §4.1 | Adds the nesting rule: a concept with a paged broader idea renders under it, as a subsection if it earns a page, else as a section (§3.2 step 4) |
| foundations/TEXTBOOK.md | §7.2 Graph; steps 4–5; "Placement between editions" | Background excluded; degree-normalized co-occurrence and similarity; links among supporting concepts halved; overlap merge; page → chapter rule; the placement paragraph is replaced by §3 here |
| foundations/TEXTBOOK.md | §7.3; §7.5; §7.9 | §6.1 hysteresis and dwell; §6.2 accounting; rendering rows for spin-off, fold-back, branch and overview; split candidates also from growth features, spin-off told apart from meaning split |
| foundations/TEXTBOOK.md | §8.3 rows "Explanation", "Chapter big picture", "Part big picture" | Sub-topic first, kind second; one stratified `overview_leaves` (§5.3) for parent pages, chapters, parts and overview pages. Parent pages, chapters and parts keep TB §4.5's sentence rule and top-leaf fallback; only cross-branch overviews need an eligible general-claim leaf for a general claim |
| foundations/TEXTBOOK.md | §5.9 | Context receipts also gate general-claim eligibility (§5.1): an AI general claim in a chat that received Northstar text on the concept or its children never seeds or keeps an overview |
| foundations/TEXTBOOK.md | §8.11 B5, B7; new B17, B18; §8.12 | B5 eligibility excludes background; B7 tree with one subsection level; B17 dwell; B18 trigger record; sentinels for spin-off, fold-back and overview rates and the background share of new structure |
| foundations/TEXTBOOK.md | §9.1 Corrections | Four new gestures (§6.4) |
| foundations/TEXTBOOK.md | §13.1; §13.2 C "Structure against the syllabus", F; §13.3 | §9 scenarios and measures; structure scored against each persona's agenda-first gold organization, the syllabus only for prerequisite order; arms S0–S5 |
| components/maintainer.md | §4.2 op list; §4.3 tiers | Adds `MINT_NARROWER` and `MINT_BROADER`, high tier |
| components/maintainer.md | §4.4 J3, J5 | J3 adds the `generalization` tag; J5 inputs add the chat's `reasoning_thread`, context receipts and explicit-reference features |
| components/maintainer.md | §3.7; §4.5 J8c; §7.2; §8 | J8c runs before every edition (following the growth regime), not only Sundays, with growth features and generalization candidates as inputs; I13 cap unchanged; the new sentinels; faults over-split, over-generalize, role flip |
| components/core-data-model.md | §2.2 rows 21–22; `index.db` | `MINT_NARROWER` → `concept.created` (with broader parent) + `concept.split` with `mode: partial`; `MINT_BROADER` → `concept.created` + `concept.reparented` per child; no new event type (CDM to confirm); a derived, rebuildable `subthread_facts` table |
| ARCHITECTURE.md | §3 "Consolidation"; §4 "A growing Book"; §15 rows GOAL §1, §3.4 | Summarize this method; the §15 rows stay Partial until §9's measures pass |

---

## 11. Open questions for the user

**Q-KO-1. How deep may the structure nest?** (a) One subsection level (Part › Chapter › Page › Subsection); deeper growth turns the page into a chapter. (b) Unlimited nesting. *Recommendation: (a).* It reads like a textbook, keeps addresses short and stable, and does not bury ideas. Cost: a page with many sub-threads becomes a chapter sooner.

**Q-KO-2. When a principle emerges across branches, should the related pages move together?** (a) Link first: an overview page, pages left in place; regroup only when clustering independently agrees, inside the churn budget. (b) Always regroup. *Recommendation: (a).* You keep your landmarks, and the theme is visible from every page.

**Q-KO-3. How visible should structural changes be?** (a) One line on the first screen plus a note with "Put it back" on each affected page. (b) Page notes only. *Recommendation: (a).* It asks nothing of you, and you will not lose a page that moved.

**Q-KO-4. How fast may an established Book's structure change?** (a) Weekly editions under the churn budget, after daily editions in the first 14 days. (b) Monthly. (c) As soon as triggers hold. *Recommendation: (a).* (b) delays useful subsections by weeks; (c) erodes location memory.

---

## 12. Risks

| ID | Risk | Threat (GOAL) | Mitigation |
|---|---|---|---|
| RISK-KO-1 | AI-taught structure is under-built, because engagement with AI teaching is quieter than your own statements ([PR] RISK PR-2) | §4.2 | Speaker never an input; structural parity (§7.3); nothing discarded, so structure can grow later |
| RISK-KO-2 | Thresholds tuned on synthetic growth misfit your real topics: premature or missed subdivisions | §2 (2026-10-09), §3.2 | Hysteresis, dwell; passive correction rate; the session add-on; one recalibration after the pilot |
| RISK-KO-3 | Path dependence: incremental evolution settles worse than a fresh clustering (cf. drifting incremental communities [12 F3]) | §3.2 | Path-dependence measure; a monthly shadow fresh clustering; a budgeted part-level re-layout when the gap exceeds the bar |
| RISK-KO-4 | Overviews over-generalize, or Northstar's own text returns as their evidence | §3.2 traceability; §5 | Eligible general-claim leaf required for a general claim (§5.1: no echoes, no chats that received Northstar text on the topic); conjunctive sentences otherwise; one leaf per child; 100% entailment; code-list fallback; G-ECHO-THEME. Limit: no principle that nobody stated |
| RISK-KO-5 | The churn budget delays a needed subdivision | §2 (2026-10-09) | Spin-offs move no page; growth regime; delay measured |
| RISK-KO-6 | Coupling: if [PR]'s roles or anchors change, the gate and anchor typing must change with them | §2 (2026-10-09) | One shared interface (§1); both designs reviewed together |
| RISK-KO-7 | Claude and ChatGPT name one idea differently | §1 no pile-up | `SAME_AS` with two families; duplicate sentinel; G-DUP |
| RISK-KO-8 | Build effort: two core operations, a subsection level, triggers, tests | §4.8 | About 1.5–2.5 builder-weeks (estimate), inside Stage 1 (Book v1) |

---

## 13. Goal-fidelity check

| GOAL item | How this touches it | Status |
|---|---|---|
| §1 foundation 2: evolution without pile-up or lost history | Both directions; duplicates merged; every change typed, redirected, viewable as of a date | Partial: missed splits and merges bounded statistically (RISK-KO-2, RISK 6) |
| §2 (2026-10-09) Knowledge organization | §3–§5, seven worked examples | Met by design (method), with one stated limit: a broader principle needs a source that states it (§5.3); quality measured in §9 |
| §2 (2026-10-09) Personal relevance | §7 structural gate, agenda anchors, hub dampening; page rules in [PR] | Partial: shared with [PR] (RISK-KO-1, -6) |
| §2 (2026-10-09) Evaluation | §9; real-topic baseline; a session add-on | Planned |
| §2 (2026-10-09) Platforms, devices; §4.5 | Pure core logic; AI side unchanged | Not affected |
| §3.2 Learned, what to learn; textbook; traceable | Textbook-shaped levels; overviews cite leaves; placement reasons shown | Partial: as ARCHITECTURE §15 (H3, H7) |
| §3.4, §4.3, §4.7 AI-managed, robust | Code decides, models propose; high tier; caps; budgets; new faults | Partial: RISK 6, RISK-KO-2 |
| §4.1 No rituals | Nothing waits on you | Met by design |
| §4.2 AI-said first-class | Content author never an input; two stated echo-guard asymmetries (§7.3); structural parity | Partial: RISK-KO-1 |
| §4.4 Two architectures; §4.6 product-agnostic | Concept graph shared, outline human-side; no product logic | Met by design |
| §4.8 Built and evaluated | §9; RISK-KO-8 | Planned |
| §5 Supersede; never summarize summaries | Overviews from leaves only; echo-derived leaves never seed or keep one (§5.1); fold-back keeps concepts | Met by design; G-ECHO-THEME tests it |
| §7 Reframing needs the user | No reframe; four HOW choices asked (§11) | Checked |
