# Personal relevance: keeping Northstar centred on your thinking

**Status:** proposal for the 2026-10-09 revision; not approved; nothing built. Answers user comment 4 (GOAL §1; GOAL §2 "Answers of 2026-10-09").
**Authority:** [GOAL.md](../../GOAL.md) overrides this document. Existing specs are not edited; changes to them are listed under "Supersedes".
**Reads with:** ARCHITECTURE §3–§6; TEXTBOOK §4.7, §6, §10.4–§10.6, §11, §13; [ai-continuity.md](../components/ai-continuity.md) §3; [ai-in-session.md](../components/ai-in-session.md) §6.5, §8.1; research [04], [05], [07] (`docs/research/`) and [14] (`docs/research/round2/`).
**Facts:** no product facts are used, so nothing here is (Unv). Every threshold and weight is a starting value (estimate), calibrated once on the golden book and your real-topic session (§7), then frozen (I19).

---

## 0. On one page

- **Relevance is a topic's role in your thinking**, computed by code from what you did with it: asked in pursuit of something, stated, argued, applied or revised a view, built on an explanation, came back to it. No model decides "this matters to you".
- **Your intellectual agenda is the anchor:** goals, pursued questions and problems, issues where you hold a view, interests, projects. Material is organized when it is part of that agenda or directly supports it, so objective information counts when it answers your question, is a reason or objection in your argument, or is a prerequisite you engaged with (asked about, followed up, or said you did not follow).
- **A term appearing is never a gap, and naming a term is never an act.** The dangling-terms rule and the generic glossary go; gaps exist only on the paths of your goals, questions, problems, interests and views, and only where you acted. Terms used across many unrelated conversations ("LLM", "API") are damped: only a strong act organizes them.
- **Authorship-blind:** an AI explanation you followed up, accepted, applied or relied on counts exactly as your own statement. **Role, not mastery:** relevance says why a topic is in your book, never how well you know it. **Interests are topics with evidence, not a profile.**
- **Nothing captured is deleted.** Non-relevant material stays in the record, index and search; a topic that matters later revives with its earlier records attached.
- **Your views and reasoning are first-class** ("Where you stand"), and objections travel with them, so the system does not echo you back to yourself.
- **Measured baseline first** (§7), against your own unaided list, on your real topics.

---

## 1. What this design must do

From user comment 4 (GOAL §2, 2026-10-09): **PR-1** centre on your evolving ideas, views, reasoning, interests, questions and problems, including understanding developed with AI; **PR-2** personal relevance, not subjective versus objective, decides what is organized and what is a gap; **PR-3** generic, searchable information is not organized or a gap merely because a term appeared; **PR-4** objective information matters when it directly supports your thinking; **PR-5** explain how the design avoids becoming an encyclopedia or glossary.

**What the current design gets wrong.** TEXTBOOK §4.7 gives a page to any concept with one long explanation, mentioned in two episodes by anyone, or the subject of any user question, "What is an LLM?" included. TEXTBOOK §6.1–§6.2 make every unexplained term a gap. TEXTBOOK §6.3 builds the goal-independent frontier from `mentioned(c)` by any speaker, and the back matter keeps a glossary of every term.

---

## 2. The relevance model

### 2.1 Three ideas

1. **Acts:** what you did with a topic, recorded from your own turns (speaker by construction, I3), typed (§2.2).
2. **Anchors:** the items of your intellectual agenda (§2.3).
3. **Roles:** code gives each topic a role, **anchored**, **supporting** or **background**, and each item on a topic a role, **linked** or **context** (§2.4). Every role carries its reasons, linked to evidence.

Evidence: goals and open questions are the demand side that decides what other knowledge is relevant [05 F8]; belief change must be produced by the system from revision events [05 F9]; AI-written rationale is plausible, not actual (precision about 0.27), so it is never stored as yours [05 F4]; models over-infer user attributes in 35–49% of claims, so relevance must not be a model's guess about you [07].

### 2.2 Acts

Code derives acts from records that already passed Apply (stances, relations, questions, episodes).

| Act | Meaning | Derived from | Strength |
|---|---|---|---|
| `asked` | A non-lookup question (§2.5), or any question you followed up, reopened or asked again | J3 question with `question_kind`; code follow-up detection | Strong |
| `stated` | You stated a view, claim, plan or explanation in your words | J3 statement on a user span, stance `asserted` | Strong |
| `accepted`, `disputed`, `rejected` | Your explicit attitude to an item **from any speaker** | Stance with a user evidence span | Strong |
| `argued` | You gave a reason for or against an item | J5 `supports`, `rebuts`, `undercuts` from a user-span item | Strong |
| `revised` | A view you held was superseded | Supersession of a user stance | Strong |
| `built_on` | Your later turn refines, extends, applies or follows up an earlier item from any speaker | J5 `refines`, `applied_in`; code follow-up on the concept | Strong |
| `applied` | You used the idea in your work: a decision, an instruction ("use a CRDT here"), a plan | `applied_in` on a user span; decision items | Strong |
| `took_up` | You acted on an AI-raised question or AI-suggested next step | Code: a later act on the concept the suggestion links | Strong |
| `set_goal`, `stated_interest` | A goal (existing rules); "I'm curious about X", "I want to understand X" | J3 Agenda item from a user span | Strong |
| `pinned` | "This matters to me" | Correction (I21) | Strong |
| `queried` | In work on an anchored topic, you followed up an answer that turned on one of its prerequisites, or said you did not follow it ("I don't get the merge step"). An act with your quote, never a stored state (V-PR-1) | J5 `responds_to` from your span to an item that uses the prerequisite; J3 modality `not_followed` on a user span; the concept is a direction-checked prerequisite of a topic anchored in that episode | Strong, for the prerequisite's supporting role and gaps only (§2.4, §4.2) |
| `looked_up` | A lookup question (§2.5) | J3 plus code conditions | Weak |
| `mentioned` | The topic is the **primary subject** of your turn, and the turn asks, states or argues something about it without reaching a stronger act (a hedged aside, a half-formed remark) | Concept refs on a user span where it is J3's primary concept, with modality ask, state or argue | Weak |
| `brought` | You pasted or attached material, **and** your turn asks, states or argues something about its topic | Origin `user_pasted` plus a user span on the same primary concept | Weak; a bare paste is `named` |
| `named` | You named the topic in passing: not the primary subject, or nothing said about it | Concept refs on a user span | **None** for roles; evidence for revival and retro-attachment only (§2.7, §6) |
| `acknowledged` | "Thanks", "ok" | J3 modality | None |
| AI-only activity | An AI mentions, explains or suggests (including boilerplate definitions given while explaining something else); you do nothing with it | — | None by itself |
| Echo | You repeat or acknowledge Northstar-delivered text | I24; lineage `northstar_echo` | None |

- **Independent episodes:** acts in one episode count once per kind; echoes never count (I11). A substantive act after a Northstar card (a new question, view or reason) counts normally, so Northstar cannot inflate relevance by showing things.
- **Product- and device-blind:** acts from any connector, machine or phone count the same once in the shared memory (I23).
- **Model-reported acts** (desktop chat at L0) count, labelled "as reported by the chat model". Relevance confers no authority, so I5 and I22 are unchanged.

### 2.3 Anchors: your intellectual agenda

| Anchor | Source | Active while (starting values) |
|---|---|---|
| Goal | Existing Agenda goal (reported goals labelled) | Active or paused |
| Pursued question | An `asked` act | Open, or answered with an act in the last 60 days |
| Problem | `question_kind: problem`: a difficulty you are working on | Open, or 60 days after its last act |
| Decision | `question_kind: decision`: you are weighing options | Until decided, then 60 days |
| Issue | A question (yours, or Northstar's labelled wording, §5.1) that one of your positions answers | An act in the last 180 days |
| Interest | `stated` (your words) or `recurring` (strong acts in ≥ 3 episodes on ≥ 3 days over ≥ 14 days) | An act in the last 120 days (stated) or 60 (recurring) |
| Project | A Casebook context with your acts | Activity in the last 120 days |
| Pin | Your pin | Until unpinned |

Interests replace TEXTBOOK's "possible directions": a recurring interest is a count of your acts on one topic, not a model's inference about you (§3.3).

### 2.4 Roles

**Topic roles** (per concept; C08, nightly and on commit):

| Role | Rule (any one suffices) | Organized? |
|---|---|---|
| **Anchored** | A strong act on it; or weak acts (§2.2: `looked_up`, `mentioned`, `brought`; never `named`) in ≥ 2 independent episodes on ≥ 2 days, unless it is a **hub concept**; or it is a target of an active anchor (a goal's target, a pursued question's or issue's subject) | Yes: a page, issue page, question page or stub |
| **Supporting** (objective information serving your thinking) | Not anchored, and: an item on it `answers` a pursued question or problem; or `supports`, `rebuts` or `undercuts` an item you hold; or it is a direction-checked prerequisite of an anchored topic, appears in that topic's linked items, **and** carries a `queried` or stronger act of yours; or it is a fact or constraint your project decision cites | Yes, under its anchor: a section or short note; its own page only if it supports ≥ 2 anchored topics on different pages |
| **Background** | Everything else, including prerequisites you never engaged with | No; it stays in the record, index and search, as plain text in pages |

**Hub damping** (the relevance form of [KO] §7.2's damping, an inverse-frequency rule over conversations). A concept is a **hub** when it appears, by any speaker, in ≥ 5% of your conversations and in ≥ 10 of them, or in ≥ 4 reasoning threads with no shared anchor (start values). A hub never anchors by recurring weak acts; it needs a strong act or an anchor link. A prerequisite of ≥ 3 anchored topics in ≥ 2 chapters with no act of yours on it is **generic**: never supporting, never a gap, never a next step. So a term you type in passing across many chats ("LLM", "token") stays background, and a lookup of it stays a lookup.

**Item roles** inside an anchored or supporting topic. An item is **linked** if, and only if, code finds one of: (i) it is on your span; (ii) a verified relation joins it to your act or an active anchor: it `answers` an anchor's question, problem or decision, `supports`, `rebuts` or `undercuts` an item you hold, or is the target of your `built_on`, `applied`, `accepted`, `disputed` or `responds_to`; (iii) it is an explanation of the topic given in an episode where you made a strong act on that topic. Everything else is **context** (for example a textbook definition in another chat). The Book puts linked leaves first and caps context at one explanation segment per page (§4.1). Because rule (iii) is code over episodes and verified relations, linked and context are reproducible on replay (I18).

**Hysteresis:** strong acts and anchor links organize a topic on the first night; anchoring by recurrence of weak acts must hold on two consecutive nightly runs, like TEXTBOOK's two-episode rule, which now counts your acts only, never mentions.

### 2.5 Lookups: a conservative rule

The **lookup label is defined by relevance, not form**: a context-free question with no stated purpose, answered in the episode and not followed up, whether it is phrased as what, how or why. "How does a KV cache work?" asked once and left is a lookup; "How does a KV cache work? My 80-turn chats get slow" states a purpose and is exploratory. A stated wish for depth is a purpose (Q-PR-1).

A question is a **lookup** only if all four hold; otherwise it is at least exploratory.
1. J3 tags it `lookup` under that definition, and an independent blind re-label (check 1, another family) agrees;
2. it has no first-person, project or prior-turn reference (code: pronouns, `context_ref` names, anaphora). "What is an LLM?" passes; "What is an LLM good for in my memory system?" fails;
3. it was answered in the same episode;
4. you made no further act on the topic in that episode.

`question_kind`: `lookup`, `exploratory` (open-ended; comparative for a purpose), `problem`, `decision`. A request for depth ("teach me Raft, in depth") is a `stated_interest`, pending Q-PR-1. Conditions 2–4 are code, so a mislabel can hide only a context-free question that was answered at once and never followed up, and the next act revives it (§2.7).

### 2.6 Who computes what

| Step | Proposed by | Verified by |
|---|---|---|
| `question_kind`, stance, holder, `stated_interest` | J3 extractor (model) | Check 0 code (§2.5 conditions; an interest needs a user span); check 1 blind re-label of `question_kind` as a key field; low risk tier |
| `supports`, `rebuts`, `undercuts`, `refines`, `applied_in`, `answers`, `responds_to` (§5.1) | J5 linker (model) | Existing J4f and Apply invariants; user-span endpoints quote exact substrings (I2) |
| Issue wording for a thread with no question | J5i (new, weekly, small) | Check 0: content words drawn from member items (as TEXTBOOK §7.2 titles); check 3 by another family ("do these positions answer this question?"); low tier; labelled "Northstar's wording" |
| Acts, anchors, roles, reasons, current relevance, decay, revival, retro-attachment | **Code** (C08: `user_act`, `relevance_facts` in `index.db`) | Hash-identical replay (I18); golden and canary runs; sentinels (§6) |
| "Is this relevant to the user?" | **No model, in production** | Asked of a model only in the blind coverage audit (§6) and evaluation (§7) |

A wrong role therefore traces to a wrong record, which the maintainer's checks, budgets and rollback already bound.

### 2.7 Rise, decay and revival

| Phase | Trigger | The Book | The AI side |
|---|---|---|---|
| **Rise** | A strong act; a second weak act in another episode on another day (not for hubs, §2.4); a new anchor link; a pin | Organized at the next printing; in "New this week" with its reason | `rel(c)` rises on commit |
| **Decay** | No act and no active anchor for τ (90 days; 180 for positions and issues); anchors close | **Nothing is removed.** Its items leave what to learn; its chapter folds as dormant after 120 days (TEXTBOOK §7.4) | `rel(c)` decays by exp(−age/τ); an active anchor holds it at 1 |
| **Revival** | Any new act or anchor link, on any product | Roles recomputed over full history; earlier records attach ("You first looked this up on 3 Sep, ChatGPT"); dormant chapters unfold | `rel(c)` restored at once |
| **Loss of basis** | Your "Not part of my thinking"; rollback of every reason's records | The page retires at the next edition, redirecting to its search answer page | `rel(c)` = 0 |

**Current relevance** (AI side): `rel(c)` = 1 for a target of an active goal, pursued question, problem, decision or pin; otherwise the maximum over its acts of `s·exp(−age/τ)`, with s = 0.8 strong, 0.3 weak, 0 for `named`; a supporting topic gets 0.6 × its anchor's `rel`. An item's relevance is `rel(c)` × 1.0 if linked, 0.5 if context. Each role change is a dated row in `relevance_facts`, so "as of a date" views show what was relevant then.

### 2.8 Corrections (optional, never required)

- **"Why is this here?"** on every page, note, next step and interest lists its reasons with links ("You asked on 4 Oct, Claude Code: '…'"). Code writes it.
- **"Not part of my thinking"** forces background (I21, reversible). If strong acts recur, "New this week" shows once: "Came up again in 2 conversations since you set it aside on 3 Sep [Restore]". No automatic restore (Q-PR-4).
- **"This matters to me"** pins it. **"Not an interest"** hides an interest. **"Not my view"** uses the existing `misstated` and `reject_content` corrections. Chat corrections follow TEXTBOOK §9.2.

### 2.9 Worked examples (invented)

| # | What happened | Role | What you see |
|---|---|---|---|
| 1 | You ask ChatGPT "What is an LLM?" and move on | Background (lookup) | Nothing organized, no gap; search and "Looked up" (§4.3) find it |
| 2 | Weeks later, in Claude Code: "How should my memory system keep an LLM focused in a long chat?" | Anchored (a problem with a project reference); example 1 attaches | A page or issue page; history "You first looked this up on 3 Sep (ChatGPT)"; the old definition may serve as context |
| 3 | Claude explains why CRDT merges converge; you say nothing; a week later you write "since merges commute, offline sync is safe" | Anchored; Claude's passage linked (`built_on`) | A page explained mainly from Claude's passage, your sentence under "Your own words" |
| 4 | During anchored CRDT work, Claude adds "you might also look at vector clocks"; you never respond | Background, unless vector clocks are a prerequisite or target on an active anchor's path | Never a gap. On the path: one line "Suggested by Claude (12 Sep), not taken up", ranked below your items; off the path: nothing |
| 5 | You argue "snapshot every 100 events because replay must stay under a second"; ChatGPT objects "it depends on load" | Anchored; an issue thread | An issue page with the objection marked "not answered"; an open-objection item in what to learn |
| 6 | Codex uses three libraries and `debounce` fixing "the reconnect bug" you reported | Project anchored; names only in the agent's turns are background | A Casebook case; no pages for library names |
| 7 | "Teach me how Raft works, in depth"; long answer; no follow-up | Anchored as a stated interest (pending Q-PR-1) | A page from the AI's explanation; Raft under "Interests" |

---

## 3. Guardrails

### 3.1 Authorship-blind (speaker-blind)

- **The relevance function sees acts and links, never who authored the content an act touches.** Acts are always yours (I3); content may be yours or an AI's. Its input type has no speaker or agent field for content, as TEXTBOOK §4.7's promotion input has none today.
- **Symmetry:** accepting, disputing, applying or building on an AI explanation counts exactly as stating your own view; a passing mention counts for neither speaker (an AI's mention is not an act, and your `named` mention is not one either). The one inherent asymmetry, stated openly: your substantive statement is itself an act, while an AI's statement needs an act of yours. That is what "personal" means.
- **Inside an organized topic, everything stays speaker-blind:** page content, explanation choice and pack ranking keep the existing speaker-free rules.
- **Checks:** a speaker-swap test holds your acts fixed and swaps who authored the content they touch (you or an AI, or one AI for another) in the golden set; no role may change. Promotion parity (TEXTBOOK §13.2 B) is re-based on relevant material: among topics the golden ledger marks as the persona's thinking, AI-taught and user-stated material are organized within 5 points. A live sentinel compares the AI-taught share among organized topics with the eligible share. A **leaf-level sentinel** does the same below topic level: the AI-said share of leaves dropped by the context cap (§2.4) against the AI-said share of eligible leaves on organized topics, and the AI-said share of items left out of the pack's knowledge slot (§4.4) against the eligible share; each fires above 10 points.
- **Known weak spot:** engagement with AI teaching is quieter than your own statements, so AI-taught understanding carries more false-negative risk, at topic level and in two quieter gates: the context cap (user statements are always linked, so it binds mostly AI or pasted text) and the pack's knowledge slot. §6 targets it (RISK PR-2).

### 3.2 Role, not mastery

- Reasons are a closed set of codes about acts and anchors. Validator V-PR-1 rejects any reason or label with knowledge-state words (known, learned, mastered, familiar, understood, covered), extending TEXTBOOK §6.3's rule.
- Relevance never changes prose density, examples or reading order (TEXTBOOK §11); only whether and where material is organized.
- Reader signals (page opens) are **not** relevance inputs; TEXTBOOK §11's four navigation-only uses stand, so the Book cannot reinforce what it already shows.
- A lookup is recorded as "looked up", never "known".

### 3.3 Interests: topics with evidence, not a profile

- An interest is `{concept refs, basis: stated | recurring | reported, evidence acts with dates and spans, status: active | dormant | hidden}`, labelled with the concept's preferred term by code.
- No traits, values, skill level or cross-topic generalisation ("you like systems design"); TEXTBOOK §11's ban on a narrative profile stands.
- Interests never enter a pack as a fact about you; they only weight selection (§4.4). Memory profiles raised agreement sycophancy by up to 45% [07]. Each interest shows its evidence and hides in one click.

### 3.4 Nothing captured is deleted

- Relevance gates **organization** only: pages, sections, gaps, next steps, first-screen slots, featured pack slots. Never capture, extraction, storage, indexing, search, `northstar_fetch` or retrieval.
- J3 still extracts every episode on both sides, so revival is lossless. "What have I learned about X?" still finds background material, labelled "looked up" or "mentioned". Pack retrieval still reaches it when a chat is about it (§4.4). Excision stays the only destructive operation.

---

## 4. How relevance governs each output

### 4.1 What earns a page or section (replaces TEXTBOOK §4.7)

| Topic | Form |
|---|---|
| Anchored, with an explanatory leaf | A concept page. Substantive teaching (120+ words, a worked example, or R14 on desktop) now decides **full page or short page**, not **whether** the topic is organized |
| Anchored by a pursued question, problem, decision or issue | An issue page (§5.2), or a question page before any position exists |
| Anchored, unexplained, on an anchor's path | A stub in a forward chapter (TEXTBOOK §6.5; no invented teaching) |
| Supporting | A section of the anchored page ("Background used here") or a short note; its own page only if it supports ≥ 2 anchored topics on different pages |
| Background | No page, note, gap or stub |

- A one-chat AI explanation of an anchored topic still earns a full page on the first night (single-episode parity, TEXTBOOK §13.2 B).
- The input assembler gives the writer linked leaves first; context fills at most one segment. "Where this fits" gains a code-written "Why it's here" line with the top two reasons.
- Project-bound questions still go to the Casebook; the project is the anchor.

### 4.2 What to learn and gaps (replaces TEXTBOOK §6.1 gaps and §6.3 `frontier_all`)

**Shown, always on the path of an active anchor:**
1. your goals, pursued questions, problems and open decisions;
2. **open objections** to positions you hold, not yet answered (new; disconfirming evidence first [05 F9]);
3. **tensions among your own positions** (new);
4. **needed terms**, replacing dangling terms: unexplained, direction-checked prerequisites on an anchor's path that appear in its linked items **and** carry a personal signal: you asked about it in work on that anchor, followed up an answer that turned on it, or said you did not follow it (`asked` or `queried`, §2.2). Without such an act the term is plain text: not supporting, not a what-to-learn item;
5. prerequisite gaps on any anchor's path, not only goals', under the same personal-signal rule;
6. unchecked reliance (unchanged; already personal);
7. disagreements between sources, on anchored topics only;
8. AI-raised questions and AI-suggested next steps you took up (`took_up`), as your items. An **untaken** AI suggestion appears only if its concept is a prerequisite or target on an active anchor's path; it is labelled "suggested by <AI>, not taken up", ranked below your own items, and never a gap. Otherwise it is background.

**Never a gap:** a term that merely appeared; a prerequisite you never engaged with; a lookup; a background topic; an untaken AI suggestion.

**Frontier:** for each active anchor a, G(a) is its targets plus direction-checked prerequisite ancestors, **minus generic prerequisites** (hub damping, §2.4); `frontier(a)` and `later(a)` keep TEXTBOOK §6.3's definitions. Path prerequisites stay ordered next steps on the path; they become gaps only under items 4 and 5. `mentioned(c)` is removed as an eligibility rule; `frontier_all` becomes `frontier_anchors`, the union over active anchors. With no goal, your questions, problems, issues, interests and projects still anchor it. With only lookups, the block says: "Nothing you're pursuing yet. Things you looked up are in the back matter."

**Next-step score** (replaces TEXTBOOK §6.4; starting weights):
`3·goal_relevant + 2·question_relevant + 1·interest_relevant + 2·ready + 1.5·unblocks + 1.5·objection_open + 1·question_recency + 1·suggested + 1·relied_unchecked + 0.5·act_breadth − 0.5·blocked`
- `question_relevant` 1 on a pursued question's, problem's or decision's path; `interest_relevant` 1 stated, 0.5 recurring (replaces `direction_relevant`); `act_breadth` = episodes with your acts, capped at 3, scaled (replaces `mention_breadth`); `objection_open` 1 for an unanswered objection to your position.
- New reason codes: `pursued` ("On the path of your question '…' (4 Oct)"), `objection` ("ChatGPT objected to your view on 3 Oct; not yet answered"), `needed` ("You asked about this while working on '…' (4 Oct); not yet explained in your book", or "Your follow-up of 4 Oct turned on this"), `interest` ("You came back to this in 4 conversations since 3 Sep"). Retired: `mentioned`, `dangling`, `direction`.

### 4.3 The glossary is replaced

| Was | Becomes |
|---|---|
| Back-matter glossary of every term | **Terms in your book:** only terms with a page, section or note, with the book's cited definition; differing definitions side by side |
| Dotted underline and hover card on every unexplained term | Underline only on **needed terms** (§4.2), which need an act of yours; other terms, generic prerequisites included, are plain text; term links go only to terms in the book |
| Lookups promoted as user questions | **Looked up** (back matter; Q-PR-2): a chronological list (date, your question verbatim, who answered, source link). Findability, like a history list, not organization: never on the first screen, never a gap, never in a pack. An entry moves into a page's history when its topic becomes anchored |

### 4.4 The AI side: pack, card, pin, retrieval

- **Core pack score** (ai-continuity §3.3): `0.40·link·p(g) + 0.20·sim + 0.15·rel + 0.10·rank + 0.10·ver + 0.05·rec`. `rel` (§2.7) has no speaker or product input, so CK-6 holds.
- **Knowledge slot:** items on anchored or supporting topics. A background item enters only through retrieval that closely matches the chat's first message, chipped "looked up on 3 Sep (ChatGPT)". The 35% floor is unchanged. AI explanations nobody acted on therefore reach new chats only through close retrieval; the leaf-level sentinel (§3.1) and benchmark v0's K1 sub-class "AI explanations not acted on" watch this.
- **New "Positions" slot** (cap 4, after conclusions): your positions on routed goals and issues, each paired with its strongest active objection or contradicting verification and its status (§5.3). New check **CK-11**: a position with an active objection carries it.
- **Open questions slot:** pursued questions, problems and decisions; never lookups.
- **Never in a pack** adds: interests as facts about you; relevance reasons; the "Looked up" list.
- **In-session card** (ai-in-session §8.1): "items relevant to U_t" ranked with `rel` added; positions and objections ride the card on triggers. **Pin:** slots unchanged; for "1–2 newest established items", ties go to items you reacted to or that link the session goal (your reaction, not the speaker). **Resume pack** "From the core" uses the same selection.
- **Router** unchanged: interests never become routing targets, so no chat is steered by an interest.
- **Re-encounter cards** only for anchored pages.

### 4.5 What the Reader shows first (replaces TEXTBOOK §10.4's first two blocks)

```
WHAT YOU'RE WORKING THROUGH
  Your goal (7 Oct): "ship the sync engine offline-first"       Next: Tombstone GC · Snapshots
  Your question (4 Oct, Claude Code): "how do I garbage-collect tombstones?"   open · 2 conversations
  A problem you described (6 Oct, Codex): "edits vanish after a reconnect"
YOUR VIEWS IN MOTION
  You changed your view (5 Oct): "tables are just caches" → "the log is the truth"
  Open objection to "snapshot every 100 events": ChatGPT (3 Oct) "it depends on load" · not answered
CONTINUE READING · NEW THIS WEEK (each with why it's here) · SINCE YOU LAST OPENED · CONTENTS
```

- TEXTBOOK §10.4's rules stay: at most 7 items a block, no counts, no tasks, no invented goals.
- "New this week" lists only anchored or supporting concepts, each with its reason; never lookups.
- Part 0 gains "Interests" (with evidence) and "Where you stand" (issue pages).

---

## 5. Viewpoints and reasoning as first-class structure

### 5.1 What the core records

| Element | Record | Status |
|---|---|---|
| **Position** (claim, belief, decision, insight), any author | Statement item | Existing |
| **Your attitude over time** | Stance {holder user, attitude, evidence span, `belief_time`} | Existing |
| **Issue** | Agenda question with `question_kind` exploratory, problem or decision; or a J5i issue in "Northstar's wording" | `question_kind`, J5i new |
| **Reason** | `supports` from a reason item to a position; who gave it comes from its attribution; `endorsed_by_user` derived (on your span, or you accepted it) | Endorsement derived, new |
| **Objection**, and your answer to it | `rebuts`, `undercuts`; an answer targets the objection relation (SPINE §5.2 allows relations as targets) | Existing |
| **Revision** | Supersession of your stance with `reason` and `causal_alternative_ref` | Existing |
| **Shaping exchange** | `responds_to`: from your span to the earlier item(s) it responds to; code proposes from adjacency and concept overlap, J5 confirms | **New relation type** |
| **Thread** | Projection: the component under {answers, supports, rebuts, undercuts, refines, supersedes, contests, responds_to} containing ≥ 1 of your stances, rooted at its issue, ordered by belief time across products | **New projection** `reasoning_thread` |

**Never store an AI's rationale as yours.** A reason shows as yours only if it is on your span or you explicitly accepted it ("offered by Claude; you agreed, 12 Sep"). No reason is inferred [05 F4].

### 5.2 In the Book: "Where you stand"

An **issue page** extends the question page (TEXTBOOK §4.3). Code renders every block from records, with quotes; no model prose about your views (TEXTBOOK §11).

| Block | Contents |
|---|---|
| The issue | Your question verbatim, or Northstar's labelled wording |
| Your position now | Quoted and dated, or "No position yet" |
| Your reasons | Quoted; accepted AI-offered reasons labelled |
| Objections | Every active objection, attributed, "answered" (your answer quoted) or "not answered"; as prominent as reasons |
| Other positions | From AIs and sources, attributed, with verification chips |
| How your view changed | Refutation blocks (TEXTBOOK §7.6) |
| What shaped it | Dated links to the exchanges your view responded to |
| Still open | Sub-questions; tensions with your other positions |

The timeline gains "What you changed your mind about", generated from revision events [05 F9]: a view, never a ritual.

### 5.3 Into chats

- A position reaches a chat only when it links the routed goal or issue, or the user turn (card). Views are never sent wholesale: irrelevant memory raises over-personalization and sycophancy ([07], [14]).
- Format: `V4 position — the user (Claude Code, 5 Oct) [recorded position]: snapshot every 100 events, because "replay must stay under a second". Open objection: ChatGPT (3 Oct) "it depends on load"; not answered by the user.` Never "the user believes" undated, never an instruction.

### 5.4 Against sycophancy and echo chambers

1. **Counter-evidence travels with the view:** CK-11 in packs; the objections block on issue pages.
2. **Disconfirming evidence first:** an objection to your position is always organized and in what to learn, even if it came once [05 F9].
3. **Views: engaged, and the severity of ignoring them is your choice (DQ-19).** In the drift checker (ai-in-session §6.5), a reply that engages your recorded position and disagrees with reasons or evidence is not drift: it addresses what was established. A reply that contradicts the position **without acknowledging it** is a drift verdict whose severity is put to you, because it weighs in-session focus (GOAL §3.3) against sycophancy (GOAL §5): (a) high, as for any accepted item (the 2026-10-08 rule, and the default until you answer); (b) medium, a correction in the next delivery, worded to ask for acknowledgement, not agreement ("Reply 14 states X without addressing V4 '…' or its open objection"); (c) a card only. Recommendation: (b). **Scope, exactly:** positions you hold on an issue (§2.3): a claim, belief or insight you stated, or an AI's claim you accepted, that answers an issue. Out of scope, with their existing guards: goals, constraints, decisions, rejected options, and AI explanations, definitions, facts and conclusions you accepted outside an issue thread (high when contradicted without new evidence).
4. **New "omitted counter-evidence" verdict** (low): a reply endorses your position while an active objection or `contradicted` verification goes unaddressed; the card brings the objection; counted in sycophancy metrics.
5. Your acceptance never upgrades verification (AD14); pushback stays stance, never evidence.
6. **Measured:** agreement on position-bearing contested prompts must not rise against no Northstar: synthetic (§7.2) and on your real topics (benchmark v0's guard F6).

---

## 6. False negatives: not dropping what matters

| Risk of dropping | Mechanism |
|---|---|
| A question asked once that matters later | Nothing deleted; full-history recomputation; a **retro-attach job** (code, on every role rise) attaches earlier records on the concept (refs, aliases, embedding near-matches confirmed by J5) to the page's history and inputs |
| A real question mislabelled as a lookup | §2.5: two independent labels plus three code conditions that fail toward "exploratory" |
| An AI explanation you relied on silently | **Silent-reliance detector:** your later span uses a concept whose explanations in your record before that span are all AI passages, any number of them (one AI or several, once or many times); code proposes `built_on` to the most similar passage, J5 confirms. Recurrence counts your later mentions across products |
| A topic you return to in small ways | Weak acts (the topic is the subject of your turn) in two episodes on two days anchor it, unless it is a hub |
| An objection to your view | Always organized (§5.4) |
| Turns unseen at desktop L0 | Export or observer backfill re-runs roles |
| A set-aside topic that comes back | The "came up again" line (§2.8) |
| Misses the rules do not foresee | **Relevance coverage audit** (J10f extended): a blind auditor of another family lists the topics in sampled windows that are part of the user's thinking; code compares with roles; misses feed the omission budget (MT §7.3) and become canary cases. Meanwhile search, fetch and retrieval still reach the material (§3.4) |

---

## 7. Measuring relevance

This is the relevance module of the baseline-first benchmark asked for in user comment 5, whose overall design is a separate deliverable of this revision.

### 7.1 Ground truth

**Synthetic (golden book).** The hidden world ledger labels each persona's topics **thinking**, **support** or **background**, with planted cases: generic lookups never built on; long AI explanations full of unexplained generic terms; a one-off question that becomes a goal weeks later; an AI explanation relied on silently; AI tangents ignored and some taken up; a view with an AI objection; a hidden revision; two of the persona's views in tension; a coding agent touching libraries the persona never discusses; desktop acts known only from the model's report. Added by the 2026-10-09 checks, each with its expected role:
- **G-GENERIC-HUB:** a generic term the persona names in passing in ≥ 2 chats on ≥ 2 days. Expected: background, no page, no gap; counted in glossary leakage.
- **Generic prerequisite:** a generic prerequisite used, unexplained, across several anchored topics, with no act of the persona's. Expected: plain text; **0 needed-term gaps and 0 sections** (hard bar), counted in needed-term precision and glossary leakage.
- **Generic how or why question:** context-free, no stated purpose, never followed up. Expected: background (a lookup).
- **Untaken AI suggestion on an anchor's path:** expected "suggested, not taken up", never a gap; off the path, background.

**Your real topics, baseline first** (short one-off sessions allowed on 2026-10-09; Q-PR-5). Timing, sitting format and label counts are set by benchmark v0 §5 and DQ-14(e):
- **Before Northstar:** unaided, you list the questions and problems you are exploring, 3–5 views you hold (and any you changed), your interests, and **2–4 things an AI explained to you that you now rely on or use**. This is the reference list. The no-Northstar probe runs then: a fresh chat, vendor memory as it is, scripted prompts asking what you are working through and where you stand on each listed issue.
- **After a period of use:** you blind-label shuffled topics (50 in the standard format: ≥ 25 organized by Northstar, ≥ 15 background in Northstar, of which ≥ 10 are background topics with an AI explanation of 120+ words that you replied to, and ≥ 10 from the comparators only; at least 15 seconds each) as "part of my thinking", "useful support" or "generic, don't need"; then you check 3 issue pages: your position, your reasons, the objections you faced.
- Recall against your list counts only items that appear in captured or backfilled conversations; the rest are reported as "never discussed". Probes on your accounts and use of real chats wait for DQ-2 and DQ-6, as today.

### 7.2 Metrics and starting bars

Pre-registered, recalibrated once after the pilot, then frozen.

| Metric | Definition | Synthetic bar | Your real topics |
|---|---|---|---|
| Relevance precision | Organized topics labelled thinking or support | ≥ 0.85 | Target ≥ 0.80 |
| Relevance recall | Thinking topics that are organized | ≥ 0.90 | Against your session-1 list ≥ 0.80 |
| Glossary leakage | Pages and what-to-learn items on background topics | ≤ 5% | Reported |
| Needed-term precision | Needed terms truly on an anchor's path and needed | ≥ 0.80 | — |
| Generic-prerequisite leakage | Needed-term gaps and sections on planted generic prerequisites | 0 (hard) | — |
| Encyclopedia share | Explanation segments citing only context leaves | ≤ 25% | Reported |
| AI-taught parity | Recall of AI-taught against user-stated thinking topics | Within 5 points | U7 split: within 15 points (indicative) |
| AI-taught false negatives | Background topics with a replied-to AI explanation of 120+ words that you label "part of my thinking" | — | ≤ 20% (indicative; benchmark U10) |
| Leaf and pack parity | AI-said share of leaves dropped by the context cap, and of items left out of the knowledge slot, against the eligible share | Within 10 points | Reported |
| Speaker-swap invariance | Roles changed by swapping content authorship | 0 | — |
| Revival | Later-important questions anchored within one printing of the reviving act, earlier records attached | 100% | — |
| Silent-reliance recall | Planted cases detected | ≥ 0.80 | — |
| Lookup precision | Questions tagged lookup that were truly passing | ≥ 0.90 | Reported |
| Lookup recall | Planted generic what, how and why questions, never followed up, kept out (lookup or background) | ≥ 0.80 | Reported |
| Mastery leakage | Reasons or labels with knowledge-state words | 0 | 0 |
| Interest validity | Evidence-linked; you agree it is an interest | 100%; ≥ 0.80 | Reported |
| Position fidelity | Positions and reasons shown as yours that rest on your span or acceptance | 100% | Session 2 |
| Counter-evidence carried | Delivered positions with an active objection that carry it (CK-11) | 100% | — |
| Sycophancy on positions | Agreement on position-bearing contested prompts, with against without Northstar | No rise (≤ 2 points) | Benchmark F6: not up > 5 points |
| Over-personalization | Replies using a delivered item where irrelevant (OP-Bench-style judge) | No rise | — |
| AI picks up your thinking | New chat states your listed questions and views correctly, with reasons and objections | ≥ 30 points over no Northstar | Session probes |

### 7.3 Baselines, and what counts as improvement

| ID | Baseline |
|---|---|
| B0 | No Northstar: transcripts and search (synthetic); vendor memory and app history (real) |
| B1 | The 2026-10-08 rules: TEXTBOOK §4.7, the glossary, dangling terms, `frontier_all` |
| B2 | Frequency: topics by mention count, cut at Northstar's page count |
| B3 | One model call: "list the topics, questions and views this person cares about", over the same transcripts; stands in for vendor-memory profiles and measures their unsupported claims |

**Improvement:** precision ≥ 15 points above B1 and B2 at equal or better recall; higher precision than B3 with no unsupported entries; the "AI picks up your thinking" bar against B0. On your real topics in benchmark v0 the comparison with B1–B3 is secondary: at v0's label counts its interval is too wide for a "clear" verdict.

---

## 8. Cost and build placement

- **Cost** (estimate): acts and roles are code; J3 adds one field; check 1 re-labels questions only; J5i makes about 30 small calls a week: under $2 a month at 100 turns a day.
- **Build** (estimate, builder-weeks ±50%; added on 2026-10-09 so the totals are complete). Relevance lives in the core, so it does not depend on Mac or Windows.

| Component | Stage | Builder-weeks |
|---|---|---|
| `user_act`, `relevance_facts`, roles, hub damping, the prerequisite-act rule, decay and revival | 0b | 1.0 |
| Lookup rule: `question_kind` in J3, the check-1 re-label, code conditions | 0b | 0.5 |
| The relevance gate in Book v0 and the pack; "Why it's here" | 0b | 0.5 |
| Issue pages ("Where you stand"), `reasoning_thread`, `responds_to`, J5i | 1 | 1.5 |
| What to learn: `frontier_anchors`, next-step score, reason codes, "Terms in your book", "Looked up" | 1 | 1.0 |
| Positions slot, CK-11, drift-check changes (DQ-19), omitted-counter-evidence verdict | 1 | 1.0 |
| Retro-attach, silent-reliance detector, coverage audit, sentinels | 1 | 1.0 |
| Golden-book relevance cases and the §7 measures | 1 | 0.5 |
| **Total** | | **About 2 in Stage 0b and 5 in Stage 1: about 7 (3.5–10.5)** |

---

## Supersedes

No spec is edited now. If approved, these change:

| File | Section | Change |
|---|---|---|
| ARCHITECTURE.md | §4 (learned, growing Book, what to learn, first screen, non-goals) | Page earning, gaps, frontier and first screen per §4 here; glossary and dangling terms replaced; "possible directions" become interests |
| ARCHITECTURE.md | §6 core pack | Score gains `rel`; "Positions" slot; CK-11 |
| foundations/TEXTBOOK.md | §4.1 | Part 0 "possible directions" → "Interests"; adds "Where you stand"; glossary → "Terms in your book" and "Looked up" |
| foundations/TEXTBOOK.md | §4.3 | Question page extends to the issue page; lookups earn no page |
| foundations/TEXTBOOK.md | §4.4 | Block 2 gains "Why it's here"; block 9 keeps needed terms only and adds open objections; linked leaves first, context capped at one segment |
| foundations/TEXTBOOK.md | §4.7 | Replaced by §4.1 here: relevance gate; substantive teaching decides page form only; the two-episode rule counts your weak acts (never a passing mention, never for hub concepts), not anyone's mentions |
| foundations/TEXTBOOK.md | §6.1–§6.4 | Gaps, frontier (`frontier_anchors`, `mentioned(c)` removed), interests for directions, score and reason codes per §4.2 |
| foundations/TEXTBOOK.md | §10.4–§10.6 | First screen per §4.5; term links, underlines and back matter per §4.3 |
| foundations/TEXTBOOK.md | §11 | Adds: no model-judged relevance; Reader signals not relevance inputs; interests never traits |
| foundations/TEXTBOOK.md | §12.1 | Engagement events become `user_act`; adds `question_kind`, interest, issue, `responds_to`, `reasoning_thread` |
| foundations/TEXTBOOK.md | §13.1, §13.2 | Planted cases of §7.1; group G "dangling-term precision" → needed-term precision; "Defined before used" counts needed terms only; group B parity re-based on relevant material; the zero-goal check accepts the honest empty state when only lookups exist; new group R (§7.2) |
| foundations/SPINE.md | §5.2 | Agenda adds `question_kind`, `interest`, J5i issue; relation `responds_to`; Engagement event → `user_act`; projections `relevance_facts`, `reasoning_thread` |
| components/core-data-model.md | §6 `index.db` | Adds `user_act`, `relevance_facts`, `reasoning_thread`; `concept_facts` no longer the sole promotion input; `derived_agenda` uses the §4.2 score |
| components/maintainer.md | §4.4–§4.6 | J3 emits `question_kind` (re-labelled at check 1) and interests; J5 proposes `responds_to`; new J5i; J10f adds the relevance coverage audit; J12 (if DQ-7(b) is yes) runs over all active anchors; new canaries |
| components/ai-continuity.md | §3.1–§3.3, §3.6 | Positions slot; knowledge eligibility; weights; CK-11; "never in a pack" additions |
| components/ai-in-session.md | §6.5, §8.1 | A reasoned disagreement that engages your position is not drift; the severity of contradicting it without acknowledgement follows DQ-19 (until answered, high, unchanged); omitted-counter-evidence verdict; card adds positions; pin tie-break |
| components/evaluation-and-build-plan.md | §2, §4 | Relevance metrics and real-topic sessions join the baseline-first benchmark; Stage 0b and 1 scope per §8 |

---

## Open questions for the user

| # | Question | Recommendation |
|---|---|---|
| Q-PR-1 | **Depth requests.** Should "teach me X in depth", with no follow-up, count as something you want to explore (organized), while a bare "What is X?" does not? | **Yes.** Asking for depth states an intent to understand; a bare definition request is a lookup unless you build on it |
| Q-PR-2 | **"Looked up" list.** Keep a chronological list of lookups in the back matter (findable, not organized), or search only? | **Keep it, back matter only.** It costs the main Book nothing and makes "I asked about this once" easy to find |
| Q-PR-3 | **Your views in new chats.** Only when the chat's goal or issue links them, always with objections; or always; or never? | **Only when linked, always with objections.** Broad profiles of your views raise agreement sycophancy; linked positions with objections keep continuity without it |
| Q-PR-4 | **Set-aside topics that come back.** One "came up again" line with Restore; stay hidden; or restore automatically? | **One line with Restore.** It respects your correction without silently losing a topic that became important |
| Q-PR-5 | **Real-topic relevance modules:** before Northstar, list your questions, views, interests and what AIs taught you that you rely on, unaided; after, label 50 topics and check 3 issue pages, within the short sessions you allowed for comment 5 (format: DQ-14(e)). Acceptable? | **Yes.** Without your own list, precision and recall on your real topics can only be guessed |
| Q-PR-6 | **When a reply contradicts your view without acknowledging it** (§5.4 item 3): high severity, medium, or a card only? *Touches the goal* (GOAL §3.3 focus against GOAL §5 sycophancy); asked as DQ-19 | **Medium**, worded to ask for acknowledgement, not agreement. Until you answer: high, as before |

---

## Risks

| ID | Risk | GOAL item | Mitigation |
|---|---|---|---|
| RISK PR-1 | **False negatives:** something that matters is not organized | GOAL §2 (2026-10-09); §3.2 learned | Nothing deleted; revival with retro-attachment; conservative lookup rule; silent-reliance detector; coverage audit and omission budget; recall bars |
| RISK PR-2 | **AI-taught understanding under-organized**, because engaging with AI teaching is quieter than your own statements; this applies at topic level, in the context cap (one context segment per page binds mostly AI or pasted text) and in the pack's knowledge slot (AI explanations nobody acted on reach new chats only by close retrieval) | GOAL §4.2; §3.3 continuity | Authorship-blind acts; silent-reliance detector; swap test; parity on relevant material; topic, leaf and pack sentinels (§3.1); on real data, U7's AI-taught split, U10 and K1's "not acted on" sub-class. Flagged, not solved: if parity fails, the tension between "personal relevance" and "AI-said first-class" comes to you rather than being traded away |
| RISK PR-3 | **Echo chamber:** centring on your views reinforces them | GOAL §5 sycophancy | Paired objections (CK-11); disconfirming evidence first; reasoned disagreement is not drift; omitted-counter-evidence verdict; DQ-19; no-rise bars, synthetic and real (F6) |
| RISK PR-4 | **Profile creep** from interests | GOAL §5; TEXTBOOK §11 | Code-counted, evidence-linked topics; no model inference; never in packs as facts; one-click hide |
| RISK PR-5 | **Generic material leaks in** (lookup mislabels; eager recurrence; generic prerequisites) | GOAL §2 (2026-10-09) | Passing mentions are not acts; hub damping; the prerequisite-act rule; lookup label by relevance; leakage, lookup-recall and encyclopedia bars; recurrence threshold calibrated on your session-2 labels |
| RISK PR-6 | **Thinner Book in early weeks** than the 2026-10-08 design | GOAL §3.2; TB H22 | Fewer but personal pages; "New this week" with reasons; growth regime unchanged; measured at simulated days 1, 7, 30, 60 |
| RISK PR-7 | **Harder reading** without a glossary | GOAL §3.2 "understand" | Needed terms; one context segment per page; "looked up" links; novice-reader arm (TEXTBOOK §13.2 D); DQ-7 governs any gloss |
| RISK PR-8 | **Model-reported acts** wrong or fabricated at desktop L0 | GOAL §4.7 | Labelled reasons; no authority (I22); existing rate caps and fabrication sentinel; reconciliation re-runs roles |
| RISK PR-9 | **Synthetic thresholds** may not fit your real use | GOAL §6 | One calibration on your session-2 labels, then frozen (I19) |

---

## Goal-fidelity check

| GOAL item | Touched how | Status |
|---|---|---|
| §1, §2 (2026-10-09) personal relevance; not an encyclopedia or glossary | The whole design | **Met by design**, pending §7; RISK PR-1, PR-5 |
| §2 (2026-10-09) objective information when it supports your thinking | Supporting role (§2.4) | Met by design |
| §3.1 shared core, both sides, attributed, evolving | Capture and extraction unchanged; relevance is a projection | Met by design (unchanged) |
| §3.2 what has been learned, from you and AIs | Organized when relevant; authorship-blind acts | Partial: RISK PR-2 |
| §3.2 what to learn | Gaps and frontier on anchor paths; open objections added | Partial: frontier quality (TB H10); RISK PR-1 |
| §3.2 reads like a textbook; understand and remember | Pages centred on your thinking; glossary replaced | At risk, as before (TB H1, H3, H7); RISK PR-6, PR-7 |
| §3.2 no quiz or mastery score | Role, not mastery; V-PR-1; no Reader signals | Met by design |
| §3.3 in-session focus and continuity, equally | Relevance-weighted selection on both; positions with objections | Partial, as before; the severity for views contradicted without acknowledgement is DQ-19 (touches the goal; until answered, unchanged) |
| §4.1 no rituals | Automatic; sessions are one-off evaluation, allowed on 2026-10-09 | Met by design |
| §4.2 AI-said first-class | Authorship-blind acts; parity and swap tests | Partial: RISK PR-2, flagged, not resolved silently |
| §4.3 AI manages; correction optional | Code computes roles; corrections optional | Met by design |
| §4.4 two architectures, one core | One relevance projection serves Book and packs | Met by design |
| §4.6 product-agnostic; not Mac-only; many devices | Acts product- and device-blind (I23) | Met by design |
| §4.7 robust maintainer | No model judges relevance; proposals verified; coverage audit; replay | Partial: semantic errors bounded statistically (RISK 6) |
| §5 sycophancy; no summaries of summaries; supersede | Paired objections; leaves-only rendering; revision records | Partial: RISK PR-3, measured |
| §6 measured, baseline first, real topics | §7 | Planned |
| §7 reframing needs the user | No reframe adopted; the depth-request line (Q-PR-1), the severity for views (Q-PR-6, DQ-19) and the parity tension (RISK PR-2) go to you | Checked |
