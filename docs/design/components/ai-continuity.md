# AI side: cross-session continuity

**Components:** C23 continuity engine (goal router, pack selection, ledger seeding, re-explanation detector, continuity receipts) and the packs C15 compiles for it (core pack, resume pack).
**Status:** design draft for adversarial review. Not approved. Nothing here is built.
**Written:** 2026-10-08. No new product facts were verified here. Facts are cited by SPINE Appendix B number (Pn) or by the connector document that checked them.
**Authority:** [`docs/GOAL.md`](../../GOAL.md) overrides this document; the user's answers of 2026-10-08 override the round-2 synthesis. [SPINE](../foundations/SPINE.md) is binding; departures are in §14. Where the goal may not be met, this document records a risk (§15) or a question (§16). It adopts no reframe.
**Inputs:** GOAL; SPINE; TEXTBOOK; [CD], [GD], [OBS]; SYNTHESIS ("SYN §n"); notes [10]–[14]. Sister component documents: [CX] `connectors-desktop-and-mcp.md` (the one MCP tool contract and MCP channel budgets), [HK] `connectors-claude-code-and-codex.md`, [IS] `ai-in-session.md`, [CDM] `core-data-model.md`, [PL] `platform-security-privacy.md`, [MT] `maintainer.md`. `docs/archive/` is not used.
**Sister document:** the in-session design (C09, C10), written in parallel. It owns the pin, the card on triggers, the Drift Checker, correction wording and restart triggers. This document states what it needs from them (§13).
**Labels:** (Unv) unverified, with its spike. "Starting value" = a parameter tuned by the gated release in §7.4.

---

## 0. Summary

1. **One engine, one compiler, every surface.** C23 decides what a new chat starts with; C15 renders it per channel. Nothing depends on vendor memory.
2. **A fixed 13-slot pack** (§3.1) with a required, floored knowledge slot. The selection score has no speaker or product term.
3. **Every line is an attributed, dated, ID-cited, third-person record**, current versions only, with supersession notes. Facts, not commands. No inferred stances, no profile (§3.2).
4. **About 2,000 tokens (1.5–3k), never above the channel limit**, fitted deterministically; cut items are listed and fetchable; small channels get parts (§3.4).
5. **The goal router works with or without a first message**, over open goals from every surface; a model only in an ambiguous band, constrained to candidate IDs (§4).
6. **Goal→item links come mostly from structure** (the session goal stack at promotion). Retrieval beyond the pack sits behind the index port, with five arms tested (§4.4, §4.5).
7. **Seeding guards continuity from turn 1**; budget-cut rejected options and disputed claims are still guarded cheaply (§5, D1).
8. **Cross-surface by construction:** provenance travels in chips; routing and selection never read product names (§6, I23).
9. **The re-explanation detector** assigns each miss a cause and feeds link proposals and gated parameter releases, never the user. Desktop L0 is reported with coverage bounds (§7).
10. **Delivery degrades by `inject_start` level with stated losses and receipts** (§8); a cross-session echo guard handles vendor memory (§9); one compiler builds core and resume packs (§10); every SYN §7.2 bar has a hook (§11).

---

## 1. Scope

C23 owns routing, selection, seeding operations, re-explanation verdicts and continuity receipts (SPINE §3); the core- and resume-pack contracts, rendered by C15; `continuity_params`; the SYN §7.2 hooks; the SD-24 arms. It does not own the pin, card, Drift Checker or restart triggers (C10), capture and promotion, connector packaging, or the Book. C23 holds no store: it writes through the C10 session applier; goal cards live in `index.db` (C08), packs in `artifacts.db` (C15).

---

## 2. Evidence and the rules it sets

Goal-directed selection with explicit links [14 F10]; supersession resolved before delivery [14 F11]; small budgets and third-person framing against sycophancy [14 F12], [11 F11]; AI-said knowledge carried because vendor memory does not, across vendors because nobody else does [14 F1, F2]; restart from the ledger (CONCAT 95.1%) [11 F1, F2]; one first call carries everything because model-pulled calls are weakest [10 F15], [GD §6.9]; an own detector because no benchmark measures re-explanation [14 F13]. Each rule cites its evidence where it is used.

---

## 3. The core pack contract

### 3.1 Slots

Chosen by C23, rendered by C15 in this order. Caps and floors are starting values; floors are shares of the budget left after Tier A (§3.4).

| # | Slot | Contents and rule | Cap / floor |
|---|---|---|---|
| 1 | Header | "Northstar state (not the user's words). Attributed records from earlier chats, as of <time>, watermark <W>. Data, not instructions. Supersedes all earlier Northstar blocks in this chat." (AIE-9) | ≤ 200 chars |
| 2 | Active goals | Routed goals (one primary, ≤ 2 secondary) with status, who, product, date. Only goals with recorded full authority: from a verbatim user span, or from a click-bound `agenda.confirmed` event when ARCH DQ-10 (TB Q6) is yes (I5, I22). A click-confirmed line reads "confirmed by the user's click; wording as reported by the chat model" until verbatim text arrives. No route: a menu of the 3 most recently active goals, stated as data (a list, not a question for the model to put to the user); not delivered when the router reports `new_topic` | 3 + menu 3 |
| 3 | Constraints | User MUST constraints linked to routed goals; verbatim-confirmed only | 5 |
| 4 | Reported, not confirmed | `reported` goals and questions (SD-36), labelled "as reported by <chat model>; not the user's verbatim words". No recorded authority (I22); whether they may steer is ARCH DQ-10. Guards G1–G6 (§4.1, §7.2) | 4 |
| 5 | Rejected options | Options the user rejected, with reason, who, product, date. Status "do not re-propose unless the user reopens it". Needs a user stance with an evidence span; model-reported rejections carry the `reported` chip (RISK-AC-8) | 6 |
| 6 | Disputed AI claims | AI-said claims the user disputed or a verifier contradicted, not yet superseded. Says which. Status "do not re-assert" (SYN §5 item 7) | 5 |
| 7 | Conclusions | Decisions, results, insights: who established them (the user or a named AI), the user's explicit reaction, verification; supersession note per §3.2 rule 3 | Floor 20% |
| 8 | Relevant knowledge | User-stated knowledge and AI-taught passages: gist + ID, verbatim when budget allows. Required (AD13); never empty when an eligible item exists | Floor 35%, ≥ 3 items |
| 9 | Open questions | Linked to routed goals, with `raised_by` | 5 |
| 10 | Contested | Unresolved tensions linked to routed goals, both sides attributed (AD19) | 3 |
| 11 | Recent provisional | Session items, not yet verified, from sessions on any surface that are still open or ended ≤ 14 days ago (SPINE §5.5); never from path-B sessions (SPINE §4.6) | Floor 10% |
| 12 | Also held | IDs and three-word titles of selected items cut by the budget | ≤ 300 chars |
| 13 | Footer | "Detail for any ID: northstar_fetch." Plus the refresh fact on model-pulled profiles ([CX §2.6]) | ≤ 200 chars |

**Never in a pack:** a user profile, engagement states (SPINE §4.7), Reader state, inferred stances, `suggested_topic` items as learned (SD-23), superseded or retracted items as current, quarantined or excised items.
**Knowledge vs conclusions:** knowledge is what is known or taught (fact, definition, explanation, procedure, example, comparison); conclusions are what the work decided or found (decision, insight, conclusion). One item fills one slot.

### 3.2 Line format and wording rules

`<ID> <kind> — <who> (<product>, <date said>) [chips] — as of <version date>: <text>`

Chips, only when they apply: `reported` (model-reported capture or speaker fidelity), `provisional`, verification (`verified`, `mixed`, `unchecked`, `cites a source, unchecked`, `no independent check`, `contradicted`; speaker-neutral, TEXTBOOK §5.4), explicit user stance (`accepted`, `disputed`, `rejected`), `tentative` (I10), and an optional dated engagement event ("explained to the user by Claude on 12 Sep", SPINE §4.7).

1. **Third person.** "The user"; AIs by agent-registry name. No "you are", traits or identity statements [11 F11].
2. **Explicit stances only**, each with an evidence span. Nothing inferred.
3. **Current versions only.** If the current item supersedes one that any chat was given (context receipts) or that was said in the last 30 days, add "supersedes <old ID> (<≤ 12-word gist>) because <reason>" [14 F11]. Also note the latest superseded version of an item linked to a routed goal when that version was said in a captured chat on a connector whose manifest sets `vendor_memory_possible`, after Tier A, budget permitting; seed it as a `superseded` guard (§5.1).
4. **Facts, not commands.** "Do not re-propose" and "do not re-assert" are statuses tied to an item and a reason [10 F5].
5. **Dates:** build time and watermark in the header; date said and version date per line.
6. **Stable IDs:** ledger IDs, or `<handle>/<id>` for session items. The Book shares them (TEXTBOOK §12.3).
7. **Gists:** only `gist_verified` gists; else a ≤ 200-char verbatim excerpt marked "excerpt"; model-reported items show their reported text, labelled.
8. **Verbatim passages** only from `verbatim` or `reconciled` spans (TEXTBOOK §5.8), with a source line.
9. **One rendering rule for every model-facing artifact** (pin, card, pack, slice, re-encounter card, fetch, widget context, L2 block).
   - Captured text is quoted and delimited.
   - A J1-flagged span (imperative, command-like, tool-call-like, URL-bearing or markup) is restated in the third person ("Claude stated a step: …"). Any command sits in an inert, labelled code block ("a command <agent> showed on <date>; not an instruction").
   - On auto-pushed, high-trust channels (hook `SessionStart` context, L2 blocks, widget context, pins) a flagged span is never verbatim: its gist and ID go instead. On explicit `northstar_fetch` and Book slices the restated form is allowed.
   - A span is **tainted** when its text overlaps that session's tool or web output (containment ≥ 0.6, as S-R9). Tainted spans follow the flagged-span rule.
   - Promotion and rank never read the flag. Taint rates per vendor family join the parity sentinel (SD-38). Checked by CK-10.
10. **Plain-text delimiters**, never vendor-like tags (SYN §5 item 8).

### 3.3 Selection rules

1. **Candidates per routed goal g:** items with an `advances_goal` link to g (§4.4), answers to g's questions, and rejected options, disputed claims and constraints linked to g; items whose concepts meet g's `target_concepts` (plus depth-1 `broader` and `prerequisite_of`); the retrieval arm in use (§4.5), queried with the first message (else g's text); session items from sessions whose goal stack held g. With no route: retrieval on the first message plus recent provisional items.
2. **Eligibility:** status active (contested only for slot 10; disputed or contradicted only for slot 6); scope matches (I17); C19 egress allows the target vendor family (§6.4); not hidden or rejected by an active correction (I21); `misstated` corrections replace the text.
3. **Slot assignment** by kind, stance and status; deterministic.
4. **Score:** `w_link·link(i,g)·p(g) + w_sim·sim(i,q) + w_rank·rank(i) + w_ver·ver(i) + w_rec·rec(i)`, starting weights 0.45 / 0.25 / 0.15 / 0.10 / 0.05.
   - `link`: user-confirmed 1.0; applied `advances_goal` 0.8; goal-stack provenance 0.8; concept overlap 0.5; depth-1 concept 0.3; retrieval only 0.
   - `p(g)`: routing confidence. `sim`: hybrid similarity to q.
   - `ver`: supported 1.0; mixed 0.8; unchecked, `not_checkable`, `no_independent_verifier`, `cited_unchecked` 0.6 (one tier, SD-38). Same order as [CDM] `best_rank` `ver_tier` (supported > mixed > unchecked tier > contradicted); contradicted items reach only slot 6.
   - `rec`: exp(−age / 30 days).
   - **No speaker term and no product term** (CK-6). The vendor-parity sentinel (SD-38) watches the knowledge slot.
5. **Diversity:** maximal marginal relevance (λ 0.7); ≤ 3 items per `primary_concept`; of near duplicates (cosine ≥ 0.9), keep the higher score.
6. **Output:** ordered item IDs with versions per slot, plus the guard-only list (§5.2).

### 3.4 Budget and fitting

**Target** about 2,000 tokens, range 1.5–3k (SYN §5 item 6). The binding limit is the manifest's `budget_chars` (SPINE §4.7); 4 characters per token is the planning estimate. [CX §2.7] is the single budget table for MCP channels and the [HK §15] manifest for hook channels; the rows below restate them.

| Channel | Pack budget | Source |
|---|---|---|
| Claude Code `SessionStart` `additionalContext` | ≤ 9,000 chars (`start_chars`; product cap 10,000, P5) | [HK §15] |
| Claude Code turn 1 | 2,400 chars (`turn_chars`), shared with the pin; the turn-1 delta and the start parts together stay within `start_chars` | [HK §15] |
| Codex `SessionStart` and turn 1 | ~2,500 tokens model-visible by default; shared with the pin on turn 1 | P12, [HK §15] |
| Desktop first tool result | ≤ 12,000 chars (first-call budget; pack 1.5–3k tokens; Claude host ~150,000, P3; ChatGPT (Unv)). The relay allows 12,000 for the first call ([PL §3.3]) | [CX §2.7] |
| Desktop later tool results (deltas) | Per-turn result ≤ 4,000 chars: card ≤ 2,400, pin ≤ 600 | [CX §2.7] |
| Widget model context | ≤ 1,200 chars (real limit (Unv), CD-S2, CS4) | [CX §2.7] |
| L2-inject visible start block | ≤ 1,500 chars, part S under the [OBS] §4.4 content rule (the user's typed goals and constraints; no reported goals, disputed AI claims or recent provisional items), because visible text reaches the transcript and vendor memory with the user's voice. Per-turn blocks: 600 chars, 1,800 on triggers ([IS §8.3]) | [OBS §4.4] |
| Restart deep-link prefill | Handle plus one fixed line, ≤ 600 chars, no item text (limit (Unv), CD-S5; RISK-CX-5). The pack arrives on the first `northstar_context` call | [CX §2.7] |

**Fitting, deterministic.**
1. **Tier A** (must include): header, routed goals, constraints, reported goals, rejected and disputed items for routed goals, footer. If Tier A alone exceeds the budget, the pack is split; Tier A is never cut silently.
2. **Floors** for knowledge, conclusions and recent provisional, when they have eligible items.
3. **Fill** the rest of slots 7–11 by score.
4. **Verbatim upgrade:** while budget remains, replace the top knowledge gists with their verbatim span (≤ 800 chars each). The upgrade obeys §3.2 rule 9: a flagged or tainted span is restated, and on an auto-pushed channel it stays a gist and ID.
5. **Truncate** lowest score first; record cuts in `truncations[]`; list them in slot 12. Cut rejected, disputed and constraint items become guard-only seeds.

**Parts.** Each is its own artifact with receipts.
- **S (start):** Tier A plus recent provisional. At chat start when the first message is unknown or the channel is small.
- **K (knowledge):** conclusions, knowledge, open questions, contested. With S when routing is confident (D2); else with the first delivery after the first user message, as a card (SPINE §4.7).
- **V (verbatim):** passages, if budget remains; else by `northstar_fetch`.

### 3.5 `northstar_fetch`

Read-only, always visible ([CX §2.2, §2.5]); ≤ 8,000 chars per result, with a cursor ([CX §2.7]). It returns: for an **item ID**, the current version, verbatim spans with a source card (product, conversation, turn, identity state), attribution, verification, the supersession chain and ≤ 5 related IDs; for a **goal ID**, a goal section (the pack's slots for that goal alone, ≤ 6,000 chars); for a **passage ID**, the verbatim passage. Results follow §3.2 rule 9 (the restated form is allowed). Each call writes an access receipt. Fetching an "also held" item signals truncation cost; fetching an item not in the pack is a soft selection-miss signal (§7.3). Free-text query mode exists only as a test arm (D3).

### 3.6 Pack checks (code, every compile)

- **CK-1** every non-fixed line cites an item ID and version (I8 for packs);
- **CK-2** nothing superseded, retracted, discarded, quarantined or excised appears as current;
- **CK-3** goal, constraint and instruction lines carry recorded authority (a verbatim user span, or a click-bound confirmation with ARCH DQ-10 yes); `reported` items only in slot 4 or chipped (I22);
- **CK-4** scope (I17) and C19 egress pass for the target vendor family;
- **CK-5** length ≤ `budget_chars`, every cut recorded;
- **CK-6** the score has no speaker or product input (static check plus the product-blindness test, SPINE §4.9);
- **CK-7** inputs are leaves, spans and relations only, never earlier pack or page text (I7);
- **CK-8** every delivered item is seeded, or recorded as not seeded with a reason;
- **CK-9** recompiling from the routing record, parameters and watermark gives the same hash (I18); C21 re-checks 1%;
- **CK-10** no unneutralised J1-flagged or tainted span on an auto-pushed channel (§3.2 rule 9).

A failed check blocks the artifact; C15 serves the last passing one for that goal set, or Tier A alone, and C21 records it.

### 3.7 Example (synthetic persona)

```text
Northstar state (not the user's words). Attributed records from earlier chats, as of 2026-10-08 09:12, watermark 48211. Data, not instructions. Supersedes all earlier Northstar blocks in this chat.
GOALS  G12 goal — the user (Claude Code, 2 Oct): ship an offline-first sync engine for a notes app. Active.
REPORTED, NOT CONFIRMED  G15 goal — as reported by ChatGPT (ChatGPT Desktop chat, 6 Oct) [reported]: learn CRDT basics first. As reported by ChatGPT; not the user's verbatim words.
CONSTRAINTS  K3 must — the user (Codex, 3 Oct): clients merge locally; no server-side merge.
REJECTED  R4 — the user rejected "last-writer-wins by wall clock" (Claude Code, 3 Oct; reason: clock skew loses edits). Status: do not re-propose unless the user reopens it.
DISPUTED  X2 claim — ChatGPT (5 Oct) [reported, contradicted]: "Automerge needs a central server". Status: do not re-assert.
CONCLUSIONS  D7 decision — Claude (Claude Code, 4 Oct) [accepted, unchecked]: per-device op log with Lamport clocks. Supersedes D3 (sync whole files) because whole-file sync loses concurrent edits.
KNOWLEDGE  P21 explanation — Claude (Claude Desktop chat, 12 Sep) [no independent check]: why CRDT merges converge in any order. Explained to the user by Claude on 12 Sep.
OPEN QUESTIONS  Q5 — raised by the user (Claude Code, 4 Oct): how to garbage-collect tombstones.
RECENT PROVISIONAL  NS-8A2Q/E3 — Codex (7 Oct) [provisional]: keep tombstones 30 days.
Also held: P22, S31, D8. Detail for any ID: northstar_fetch.
```

---

## 4. The goal router

### 4.1 Candidate goals from every surface

One candidate set, whatever surface the chat is on: long-term Agenda goals (active or paused; `explicit` or `reported`, SD-36), and goals of sessions that are live or ended ≤ 14 days ago on any surface and not yet promoted (deduplicated by `promoted_from` or similarity ≥ 0.9).

Each candidate has a **goal card** in `index.db`, rebuilt by C08 on `ledger.committed` and on session goal changes: goal text and aliases, target-concept labels, gists of its top 8 linked items, its open questions, the `context_ref`s and titles of sessions where it was active, and last-active time. Cards are in FTS and the embeddings cache.

**Guards for reported goals and questions (SD-36 kept with guards; SEC-5).**

| # | Guard |
|---|---|
| G1 Provenance | A reported goal or question is created only if its text appears in the model's `user_message` copy for that turn: not from `prev_reply_points`, not matching assistant, tool or Northstar text (I24), and with no URL, command or tool-call span. There is no imperative test: "help me design…" is an ordinary goal |
| G2 Rate cap | At most 2 new reported goals per session and 5 a day across surfaces. Overflow stays session-scoped |
| G3 Routing cap | A first-session, unreconciled reported goal never becomes primary on text or recency alone; it is capped at p 0.6 as a secondary. The cap lifts once it recurs in ≥ 2 sessions on ≥ 2 days |
| G4 Decay | Kept in slot 4 and Tier A only while reported in ≥ 2 sessions on ≥ 2 days, or reported within the last 30 days, or confirmed. Otherwise it appears only in the Book's "Reported goals" list, by ID. The same decay applies to model-reported rejections and disputes |
| G5 Rendering | Rendered under §3.2 rule 9 |
| G6 Confirmation | A restatement confirms only under §7.2 step 8's rule |

**Fabrication sentinel:** the share of reported goals never restated or reconciled within 30 days, per connector, to C21.

### 4.2 Algorithm

| Stage | Signal | Value (starting) |
|---|---|---|
| 0 Explicit | A handle, goal ID or item ID in the first message or prefill | Route, p = 1.0 |
| 1 Lineage | `parent_handle` (restart, compact, clear, fork, resume) → the parent's goal stack | Session goal 0.9; north star 0.8 |
| 2 Context | `context_ref` matches cards | Exact 1.0; same repository root 0.8; same project name 0.6 |
| 3 Text | BM25 and embedding similarity of q to cards | 0–1 each |
| 4 Recency | exp(−Δt / 7 days) since last activity on any surface | 0–1 |
| 5 Live sibling | A session active in the last 30 minutes, any surface, with this goal on its stack | 0 or 1 |

- **Fusion:** a weighted sum of stages 1–5, calibrated to a probability `p(g)` (isotonic, on the routing golden set, SP-AC-1). Product and surface are never features (I23).
- **Route** when `p ≥ 0.7` with a margin ≥ 0.1; secondaries need `p ≥ 0.5`; ≤ 3 goals. A reported goal is capped by G3 (§4.1).
- **Ambiguous** (`0.35 ≤ p < 0.7`, or margin < 0.1): the `goal_router` role (SPINE §8.1) gets q, `context_ref` and ≤ 8 cards. Output: `{routed: [{goal_id ∈ candidates, role, reason_span}], new_topic}`. Validators: IDs are candidates, `reason_span` is a substring of q, ≤ 3 goals. On timeout or invalid output: deterministic goals with `p ≥ 0.35`.
- **No route** (all `p < 0.35`): goal menu plus message-direct retrieval (§3.3).
- **The router never creates or changes goals.** Only the Goal-Change Handler (C10) pushes a session goal, from a user span.

### 4.3 Routing moments, with and without a first message

| Moment | Known | Router |
|---|---|---|
| Hook `SessionStart` startup or clear | `context_ref`, maybe a parent | Stages 1, 2, 4, 5. `p ≥ 0.7`: parts S and K now (D2); else S with the goal menu. `clear` records the previous session as a weak parent |
| Hook `SessionStart` compact or fork | Parent | Resume pack (§10) |
| Hook `SessionStart` resume, or a desktop chat reopened ≥ 6 hours later | The chat's handle | Delta: items for its goals changed since its last delivery (context receipts) |
| Hook turn 1 | Verbatim prompt | Full re-route; the delta rides turn 1 as a card, pin last. **Turn-1 budget** (starting value, turn 1 only): re-route plus pack within p95 2.0 s, inside the 2.5 s client deadline ([HK] §4.3), measured in SP-AC-4. If exceeded, the routed goal section goes first and the rest on turn 2 |
| Desktop first tool call (L0, L0+) | `hint_text`; `prior_hint_texts` if the call came late (§13) | Full routing on the model's copy; with no copy, stages 4–5 and the menu |
| L2-inject pre-armed block | Nothing yet | Goal menu of the user's typed goals, under the [OBS] §4.4 content rule; the observer's verbatim first message then triggers a full re-route |
| Restart, or a new chat that adopts a pending resume pack | `parent_handle` from the prefill, the handle or the registry entry | Resume pack |

**Pending resume packs (restart level `suggested`).** At each new session's first routing, C23 consults the **pending-resume registry**: one table in `session.db`, written only by the C10 applier, read by C23, entries kept 24 hours ([IS §9.3], [CDM §5]). C23 holds no copy. A parked pack is adopted only on an explicit handle (stage 0) or when C23 routes the chat to the parked pack's goals with `p ≥ 0.7` (§4.2). Adoption sets `parent_handle` and lineage, is labelled with that lineage in the continuity receipt, and is reversible like any join (SPINE §5.2). Otherwise the chat gets its core pack and the entry expires unused.

**Routing window:** C23 re-routes on user turns 1–3 when the Goal-Change Handler reports a low-confidence continuation or a new topic, sending deltas only. After turn 3, relevance retrieval belongs to C10's card, except for mid-chat routing below.

**Mid-chat routing (any turn).** On a confident Goal-Change Handler (GCH) `goal_change` or pivot toward a long-term goal not on the session's stack, C23 routes the user turn (U_t) against goal cards. At `p ≥ 0.7` with a margin over the next candidate (≥ 0.1, as §4.2), it delivers that goal's precompiled section (part K) within the card budget and seeds it (`on_route: true`), including guard-only rejected, disputed and constraint items (§5.2). `context.get` reaches C23 for this case (§13).

### 4.4 Explicit goal→item links

All links are `advances_goal` relations (SPINE §5.2), written only by C12, with a `basis`:

| Basis | Created by, when | Confidence |
|---|---|---|
| `goal_stack` | Code, at promotion: the item's span was made while g was on that session's goal stack | 0.8 (0.6 for focus-level goals) |
| `j5`, `answers` | J5 proposals in the slow lane | Verified by risk tier |
| `user` | A `must_link` correction (C18) | 1.0, hard constraint (I21) |
| `reexplained` | C23 link candidate (§7.4), checked by J5 | 0.6 |

`goal_stack` links come from structure, not a model, so most items gain a goal link at promotion. That is what LoCoMo-Plus says similarity alone cannot supply [14 F10].

### 4.5 Retrieval beyond the pack (SD-24)

The index port (C08) offers `goal_cards.search`, `items.by_links`, `items.hybrid`, `items.as_of` and `relations.subgraph`. Every arm implements it, so arms swap by configuration.

| Arm | Adds to the links | Status |
|---|---|---|
| R0 | Nothing | Ablation |
| R1 | FTS5 + embeddings, reciprocal rank fusion | **Default** |
| R2 | R1 + graph expansion, depth ≤ 2 | Test |
| R3 | R1 + agentic search: a model with `northstar_fetch` by ID and query, ≤ 3 calls | Test (D3) |
| R4 | R1 + a per-goal standing section compiled from leaves only (I7) | Test |

**Testing** (C22, offline, SYN §7.2): same pairs, probes and budget per arm, at the pack budget and at SYN's 8K; baselines B1, B2, B4, vendor memory approximated on and off. Decision rule (SYN §7.2): a structured arm must beat the best baseline by ≥ 10 points on update and belief-evolution metrics, or the simpler retrieval wins *for the retrieval layer only*; the pack contract stays. Secondary: routing- and selection-miss shares (§7.3) and p95 latency. Live: R1 only until UQ-9 allows sub-arms.

---

## 5. Ledger seeding

### 5.1 Seed operations

C23 proposes; the C10 session applier validates and writes (SYN §3.4).

```yaml
session_op:
  op: ADD                                # seeds are plain ADDs: no SEED or ROUTE op type
  session: NS-8A2Q   turn: 0             # 0 = before the first user turn
  actor: seeding   actor_ref: continuity_params_v3
  item: {seeded_from: {item_id: D7@v2, artifact_hash: 9c1e, delivery_receipt: 01JB},
         seed_kind: conclusion, by: ai,                         # by keeps the original speaker: user | ai
         authority: confirmed,                                  # confirmed | provisional | reported
         delivery: delivered, on_route: true, as_of: 2026-10-04}  # delivered | unknown | guard_only
```

The routing decision is a `routing_record` row, not an operation ([CDM §5]). **Authority** uses [CDM]'s enum: long-term items seed as `confirmed`; `reported` items (slot 4, model-reported rejections and disputes) as `reported`; recent provisional session items (slot 11) keep `provisional`, or `reported` when model-reported.

| Seed kind (slot) | Session ledger section | Drift Checker checks | Severity cap |
|---|---|---|---|
| goal (2) | Goal stack, north star, `source: core:<id>` ([11] impl. 1) | Adherence | As in-session |
| constraint (3) | Constraints, `by: user` | Violation | High |
| model-reported constraint (11) | Constraints, `reported`, provisional; only from sessions in the 14-day recent window | Violation | One level lower (medium). Per ARCH DQ-10; until answered, as now |
| reported_goal (4) | Agenda, not on the goal stack | None; a verbatim restatement is a confirmation candidate (§7.2, G6) | — (per ARCH DQ-10; until answered, as now) |
| rejected (5) | Rejected | Re-proposal without the user reopening it | High |
| disputed (6) | Established, disputed | Re-assertion as fact | High |
| conclusion (7) | Established | Contradiction; unwarranted flip without new evidence | High (user). AI: High if the user accepted it or it is verified; Medium otherwise |
| knowledge (8) | Established | Contradiction | Medium |
| superseded (§3.2 rule 3) | Established, superseded | Stale assertion of the old version | Medium |
| open_question (9) | Open questions | None | — |
| contested (10) | Established, contested | One side presented as settled | Low; no correction on first occurrence |
| provisional (11) | Established, provisional | As its underlying kind | One level lower |

C10 owns the check algorithms and correction text. Each seed carries the reason and provenance a specific correction needs ("rejected by the user on 3 Oct in Claude Code because clock skew loses edits"); specific corrections cut drift 87% against 35–38% for generic reminders [11 F6].

### 5.2 Delivery states and timing

| State | When | Checks |
|---|---|---|
| `delivered` | The connector's receipt confirms placement | Full |
| `unknown` | Widget model context (no acknowledgement, SPINE §4.5) | Full; verdicts tagged for analysis |
| `guard_only` | Rejected, disputed or constraint items cut by the budget or in an undelivered part | Tiers 0–1 screen (string, alias, embedding at a high threshold); a tier-1 hit may go to tier 2 within [IS] §6.4's volume caps. A hit yields a correction citing the item (so the model then sees it) only on a tier-0 exact or alias match, or a quote-backed tier-2 verdict; never on tier 1 alone. ≤ 1 guard correction per turn, ≤ 1 per item, ≤ 3 per session; promoted to `delivered` when a later part delivers them (D1) |

| Tier | Seeds written | Checked |
|---|---|---|
| Hook | At the `SessionStart` receipt; deltas at the turn-1 receipt | `in_turn`: a re-proposed rejected option can be corrected before the user reads the first reply |
| Observed chat (L1) | At the first delivery the model receives | `next_turn_verbatim` |
| Sanctioned chat (L0, L0+) | At the first Northstar call under `per_turn_write`; under `per_turn_readonly` at the first declared write that records the turn ([CX] §2.5 rule 5); with no call, nothing | `next_turn_reported`, on self-report, weak |
| Path B (either desktop app) | None: path B writes no seeds; the pack is delivered and checked in-call only ([CX] §2.5) | In-call tier-0 checks only |

### 5.3 When the user changes course

Seeds guard; they never lock the user in.
- A user turn that contradicts a seed goes to the Goal-Change Handler first, whose item-level output ([IS] §5) names the seeds the turn reverses, reopens or refines. A user refine, pivot or reversal supersedes the seed in the session (`SUPERSEDE`, reason `user_later_statement`); checks stop; the slow lane proposes the long-term supersession from the verbatim span. The user is never asked.
- Reopening a rejected option ("let's reconsider wall-clock LWW") lifts that seed.
- An AI reversal *with* new grounding (a tool result, a cited source) is not an unwarranted flip; C10 records an `ai_self_correction` candidate.
- After a re-route away from a goal, its seeds are marked `on_route: false`; only rejected, disputed and constraint seeds keep checks. Off-route rejected and disputed seeds become guard-only at medium severity. Constraints whose old goal shares the session's `context_ref` keep their severity. Other off-route constraints also keep theirs by default; demoting them is an ablation arm (§11).
- On desktop L0, a contradiction known only from the model's copy makes a provisional supersession; I22 governs anything long-term.
- **Retractions:** on `items.retracted(ids)` the C10 applier retracts matching seeds, expires queued corrections that cite them, and invalidates pins and pending resume packs.

---

## 6. Cross-surface continuity by construction

### 6.1 Why it holds

- **One core, one compiler.** Every surface reads the same ledger and session store; C15 renders one selection per channel ([14 F2]).
- **Product-blind routing and selection.** Goals and items from every surface are candidates, and no feature reads a product name (I23, CK-6). A Claude Code goal reaches a ChatGPT chat on content, lineage and recency.
- **Recent work is visible at once.** Provisional items enter slot 11 as soon as the steward writes them, even while the source session is open.

### 6.2 How provenance travels

- **Speaker and agent** (vendor, product, surface, model; attribution `agent_id` → agent registry): shown as "Claude (Claude Code)", model in fetch detail. Never a policy input (I23), except `speaker_model_family` for verifier routing and the echo rule (§9).
- **Capture and speaker fidelity:** the `reported` chip; drives authority (I22) and quoting.
- **Verification and independence:** a chip and the `ver` term.
- **Conversation identity state:** in fetch source cards.
- **Cross-surface start (analysis only):** most delivered items were last evidenced on a product other than the target's.

### 6.3 Pairings

| Source contributes | Fidelity and timing |
|---|---|
| Claude Code, Codex | Verbatim both sides; provisional within one turn (target p95 < 5 s, SP-6); long-term after ~2 hours [13 §I] |
| Claude Desktop chat L0 or ChatGPT Desktop chat L0, paths C1, C2, W, or A for saved turns | Model-reported; AI points one turn late; user goals as `reported` (SD-36); after each call |
| Either desktop chat L0, path B | **Nothing**, except `northstar_note` or a one-off export (RISK 33) |
| Either desktop chat with L1 | Verbatim, seconds after each reply |

| From → to | The new chat starts with | Limit |
|---|---|---|
| Claude Code → ChatGPT Desktop | Verbatim-backed goals, constraints, conclusions and AI-taught passages in the first `northstar_context` result | Only if the model calls (RISK 4; CS5) |
| ChatGPT Desktop → Claude Code | Reported items with chips; user goals in slot 4; delivered deterministically | Nothing under path B (RISK 33); no authority (RISK 34) |
| Claude Desktop ↔ ChatGPT Desktop | Reported items, model-pulled both ways | Coverage-limited measurement (§7.5) |
| Codex ↔ Claude Code | Verbatim, deterministic both ways | Codex budget forces parts (RISK-AC-5) |

### 6.4 Cross-vendor delivery and concurrency

- **Cross-vendor delivery** puts one vendor's captured content into the other vendor's chat, which then holds it and may store it in its memory. Working rule, pending SPINE UQ-12 (ARCH DQ-3(b)), as in [PL] §6.3 column V: personal `normal` items go across vendors; `sensitive` items are masked where the vendor would gain new exposure; `private`, work and unclassified items go only to vendor families that already hold every source span ("no new exposure"). C19 enforces it.
- **Concurrent sessions** on two surfaces may establish opposite provisional items. Both go to slot 10 as a contested pair, both attributed, neither silently picked (SYN §5 item 3); a sentinel counts pairs (RISK-AC-7).

---

## 7. The re-explanation detector

### 7.1 Inputs and outputs

- **In:** user turns 1–5 at any fidelity with `paste_ranges` and `northstar_block_ranges`; `prior_hint_texts` from a late L0 first call; the routing record, artifacts, receipts and seeds; candidates from C08 and `session.db`.
- **Out:** verdicts (via the C10 applier), metrics (C21), link candidates (`session.db`, for the slow lane).

### 7.2 Algorithm

1. **Clean:** remove Northstar blocks by exact match (I24). Keep pasted ranges, flagged: pasting a summary from another chat is the commonest cross-surface re-explanation.
2. **Split** into sentences, or paragraphs for long pastes; ≤ 40 units.
3. **Candidates:** an exact ID mention is a `recall_reference` (positive, not a miss). Otherwise BM25 + embeddings, top 5, over delivered items, active best-rank items, recent session items (14 days, not path B) and superseded items; keep cosine ≥ 0.75.
4. **Judge** with the `reexplain_detector` role (SPINE §8.1): `restates`, `recall_request`, `corrects_ai` ("as I said", "we ruled that out"), `new_or_different`, `unrelated`. The output must quote the unit (substring check).
5. **Reference rule:** a short mention by name (< 15 words, no added detail) is a reference, not a re-explanation. Calibrated in SP-AC-3.
6. **One verdict per (turn, item).**
7. **Cause** by code (§7.3).
8. **Special cases:** a restatement that changes content goes to the Goal-Change Handler. A verbatim restatement of a `reported` goal is also a **confirmation candidate** through the normal verbatim-match path (I22), with no user action. **G6:** it confirms only if a `user_typed`, origin-confirmed span outside paste ranges contains the goal's full normalised text (at least 4 content words), or an independent-family entailment check passes.

```yaml
reexplain_verdict: {session: NS-8A2Q, turn: 2, unit_span: "we decided per-device op logs with Lamport clocks",
                    item: D7@v2, label: restates, content_kind: conclusion, speaker_of_item: ai,
                    fidelity: verbatim_live, cause: delivered_unused, pasted: false,
                    judge: {role: reexplain_detector, recorded_output: 01JC}}
```

### 7.3 Miss causes

| Cause | Test (joins, by code) | Fix owner |
|---|---|---|
| `no_pack` | Shadow arm, no call, or `inject_start` static or none | Delivery; first-call rate |
| `not_routed` | The item is linked to a goal the router did not pick | Router |
| `not_linked` | Right goal; no link; retrieval missed it | Links, retrieval arm |
| `not_selected` | A candidate scored below the cut before budget | Score weights |
| `truncated` | Selected, cut by the budget | Budget, parts |
| `delivered_unused` | Delivered (or `unknown`) and still restated | Wording, placement; user habit cannot be separated live |
| `not_in_core` | Only in an expired session, raw capture, or nowhere | Capture (RISK 19, 33), promotion |
| `stale` | The user restates a superseded version | Supersession notes |

### 7.4 Feeding tuning, never the user

No verdict reaches the user as a prompt, badge, question or task. The Reader's health page may show aggregates to anyone who opens it.
1. **Links (automatic):** each `not_linked` or `not_routed` hit under a confident route writes a link candidate (g, i, `reexplained`). At episode close C11 hands it to J5; C12 applies it if checks pass. The next pack for g carries i.
2. **Parameters (gated releases):** router weights, thresholds, floors and score weights form a versioned bundle `continuity_params@vN`. Releases follow SPINE I19's one rule, the rule [MT] D4 states (J10e is dropped for the prototype): automatic releases only through a committed procedure with replay and canary gates, versioned bundles and automatic rollback. The procedure (gates, metrics, margins, rollback trigger) is itself a versioned commit. Replay gate: nightly, C22 replays the miss log and frozen probes against candidate bundles, and a bundle passes only if misses fall without loss in detector precision, AI-said recall, cross-surface recall, the sycophancy probe or budget. Canary gate: the bundle must pass the nightly canary ([MT] J10c) before it activates. C21 then promotes it, and rolls it back automatically if live misses rise over 7 days. This is not online learning.
3. **Sentinels to C21:** `not_routed` > 30%; `truncated` > 20% on a channel; `delivered_unused` rising for one model family; `not_in_core` rising on one connector.

### 7.5 Measuring continuity on desktop L0

At L0 the core sees a user turn only when the model calls a tool; a chat with no call is invisible (SPINE §4.6). This known gap is reported, not hidden.
- **Observed rate:** hits over seen turns 1–5, on the model's copy; precision calibrated with CS6 copy-fidelity data. A late first call adds `prior_hint_texts` (≤ 4 earlier user messages), labelled (SP-AC-5).
- **Coverage and bounds:** first-call rate and r(t), t ≤ 5, from CD-S3, CS5 and the `openai/session` call index. Rates are given as [hits / estimated turns, (hits + unseen turns) / estimated turns], never as a bare point.
- **Calibration:** L1 shadow capture if UQ-1 allows; scripted synthetic sessions run by the builder; an export only if the user volunteers one, never recurring (SD-32). Invisible chats count only when verbatim text arrives later, as `no_pack`.
- **Reporting:** desktop L0 is its own row, never pooled with hook results (SD-18).
- **Path B:** the stateless call keeps only content-free operational logs; delivered item IDs are derived on demand from the echoed tag ([CX] §2.5 rule 7). Decided in review (FEAS-1).

---

## 8. Delivery per `inject_start` level

### 8.1 By level

Seeding timing per tier is §5.2.

| Level | Channel | Delivered | What this level loses |
|---|---|---|---|
| `deterministic` | Hook `SessionStart` + turn 1 (Claude Code, Codex); SDK; L2-inject block | Part S at start; K at start if `p ≥ 0.7` (D2), else turn 1; deltas on turns 1–3 | Nothing structural; Codex's budget forces parts |
| `deterministic_after_mount` | First tool call, then widget context (cond. CD-S2, CS4) | Full pack in the first result; then a continuity strip | Chats with no first call; strip delivery is `unknown` |
| `model_pulled` | First Northstar tool result (L0) | Full pack, pin last | Chats with no call get nothing and are invisible; routing on a copy |
| `static` | Boot text only | No pack, no seeds | Continuity; marked "no pack delivered" |
| `none` | — | — | Marked as not meeting continuity |

### 8.2 Hook tier

`SessionStart` (P5, P12) calls C23 synchronously (pack p95 1.5 s); per-`start_kind` handling is §4.3.

### 8.3 Desktop L0: boot line and first call

The one-time boot line names `northstar_context` on both desktop products, the one tool contract's first-call tool ([CX §1.2, §4.2, §5.3]). The first `northstar_context` call carries the model's copy of the user message (plus `prior_hint_texts` if late); C23 routes on it, and the result holds the full pack (first call ≤ 12,000 chars, [CX §2.7]), then the pin and refresh fact. **One call carries pack, handle, seeding and widget mount** (under `per_turn_readonly`, seeding waits for a declared write, [CX] §2.5 rule 5), so on L0 continuity's channel is stronger than per-turn focus's ([GD §6.9]). No call: nothing until verbatim text arrives; the first-call rate is a sentinel.

### 8.4 Widget context: the continuity strip

After mount (cond. CD-S2, CS4), widget model context (a `model_context` artifact, SPINE §5.2) carries, beside the pin and within ~1,200 chars: routed goal IDs with one line each, rejected and disputed IDs with three-word titles, and ≤ 5 top knowledge and conclusion IDs. The turn-1 re-route delta reaches the next turn this way without another model call. Delivery is `unknown`.

### 8.5 L2 (only as UQ-1 allows), and restart openers

- **Pre-armed start block** (L2-inject): when the observer sees a new chat, a visible block of ≤ 1,500 chars: part S under the [OBS] §4.4 content rule (the user's typed goals and constraints, as a goal menu, plus "detail for any goal: northstar_fetch G<n>"; no reported goals, disputed AI claims or recent provisional items). It is part S only, because no message is known. The verbatim first message then re-routes; the delta rides the widget, the next tool result or the next block. Losses: visible in the transcript and to vendor memory (SD-16); the user may delete it (`user_removed`, never re-added that turn).
- **Prepared fresh chat** (L2-auto, prepared, never sent): the resume pack plus the carried-over draft; the user sends. Northstar-authored (I24).
- **Deep link** (L0/L0+, cond. CD-S5): the prefill (a `prefill` artifact) carries the handle plus one fixed line, ≤ 600 chars, no item text ([CX §2.7]; RISK-CX-5). The new chat's first `northstar_context` call carries the prefilled handle in `user_message` (stage 0) and returns the full resume pack. **`ui/message`** (cond. CS4): the resume pack as one titled item, ≤ 12,000 chars ([CX §2.7]).

### 8.6 Context receipts and the continuity receipt

Every delivery writes a **context receipt** (SPINE §5.2): session, artifact ID and hash, items with versions, placement, delivered state, arm, text hashes, time. Receipts feed the Book's "this chat draws on" card (TEXTBOOK §5.9, §10.8), the echo guard (§9), resume deltas and evaluation. C23 extends SPINE §4.5's continuity receipt (one per new session, written by the C10 applier):

```yaml
continuity_receipt:
  session: NS-8A2Q   start_kind: new_chat   parent_handle: null   arm: treatment   params: continuity_params_v3
  routing: {routed_on: hint_text, method: deterministic, goals: {G12: 0.82, G15: 0.55}, rerouted_at: []}
  parts: [{part: S+K, artifact: core_pack@9c1e, placement: tool_result, delivered: true, turn: 1}]
  truncated: [P22, S31, D8]
  seeded: {delivered: 24, unknown: 0, guard_only: 3}
  reexplain: [{turn: 2, item: D7, label: restates, cause: delivered_unused, fidelity: model_reported}]
  coverage: {turns_seen: [1, 2, 4], first_call_turn: 1, prior_hint_texts: 0}
  cross_surface: true            # analysis only
```

---

## 9. Vendor memory and the self-poisoning guard

**Policy (SD-16):** leave the user's vendor-memory settings alone; label every block; prefer hidden channels; measure absorption; if harm is measured, propose a change to the user, never make it ([GD §9], [CD §4.7]).

**What is carried from vendor memory:** nothing live; no API exposes it ([14] risk 6). A vendor-memory export the user chooses to give once is ingested as an external document whose speaker is that vendor's memory agent, labelled "AI-written summary about the user, not the user's words" ([10] impl. 10). It never creates goals, constraints, preferences or instructions (I5, I22). It enters a pack only through the knowledge slot when linked to a routed goal, with that label, never as a profile.

**The loop:** a pack line reaches the model → vendor memory stores it, perhaps as a fact about the user → a later chat surfaces it → the AI says it → Northstar captures it as AI-said → it looks like independent support → it is promoted and packed again (SYN RISK 11).

**Guards.**
- **Self-capture exclusion:** exact Northstar text in captured turns is stored as `northstar_*` origin (I24).
- **Same-session echo:** AI-said spans that follow a delivery and overlap it (n-gram containment ≥ 0.6) are `northstar_echo` (TEXTBOOK §5.9).
- **Cross-session echo (D4):** the same rule against artifacts delivered to sessions of the same `speaker_model_family` in the last 90 days, when the span has no fresh grounding.
- **Consequence:** echoes stay visible as AI-said but never count as independent lineage, raise verification or promote alone (I11).
- **Unprompted-echo sentinel:** in sessions with no delivery (shadow arm, no call), AI-said spans matching earlier artifacts measure absorption live, with no user involvement.
- **Wording:** third-person records under "not the user's words" give memory extractors less reason to store them as user facts (Unv: CS10, DS9, SP-AC-6).

---

## 10. Consolidate-and-restart: resume pack and core pack

C15 compiles both with one function and the same checks (§3.6). Neither is ever built from transcript text or an earlier pack (I7; [11 F2]).

| | Core pack | Resume pack |
|---|---|---|
| Purpose, trigger | A new chat starts with earlier work; C23 at session start | A long or drifted session continues fresh (CONCAT [11 F1]); C10 restart triggers (SPINE §4.6) |
| Routing | §4 | The parent's goal stack |
| Session items | Slot 11 only | First: the parent's goal stack, constraints, established items from both speakers with turn references, rejected options, open questions, assumptions ("confirm before relying"), artifact versions, pending corrections, last k turns as captured leaves ([11] impl. 6) |
| Long-term items | All slots | Knowledge and conclusions for the parent's goals, after session items |
| Budget | ~2,000 tokens | Up to the channel limit (Claude Code 9,000 chars, [HK §15]; desktop first call 12,000, [CX §2.7]) |
| Seeding, misses | §5; continuity misses | Same kinds with parent turn references ("parent t12"); restart misses counted separately |

The restarted session has `parent_handle`, `start_kind: restart`, its own receipt, and delivery by the target's level (§8). The old chat stays usable (SD-15).

---

## 11. Measurement hooks for SYN §7.2

**Offline.**
- **Data:** continuation pairs from the one-off backfill (SD-32), same- and cross-surface; constructed pairs continue a split chat on the other vendor's model.
- **Hook** `continuity.replay(as_of, first_message, render_profile, params, arms)`: read-only and deterministic; compiles as of the split point (SPINE §5.4).
- **Arms:** vanilla; vendor memory (approximated by a one-off export as context, (Unv) fidelity); Northstar; Northstar + vendor memory; B1, B2, B4; R0–R4.
- **Ablations (HOW only):** router variants; links, seeding, provisional slot and verbatim upgrade on/off; demoting off-route constraints that do not share the session's `context_ref` (§5.3); a second-person control for sycophancy. The pack contract and knowledge slot are redesigned if they fail, never cut (SYN §7).
- **Probes** (SYN §7.2): prior goals; user-stated and AI-taught knowledge; user and AI conclusions; rejected options; superseded facts; abstention. Third-family judge (SPINE §8.3).

**Live.**
- **Arms:** pack on or off per new chat, assigned by C10 (SD-31). Off is a shadow arm: C23 routes and selects and records "would have delivered", but delivers and seeds nothing. **Only after the user's yes to UQ-9**; until then offline and synthetic only.
- **Primary:** re-explanation in turns 1–5, pack on vs off, by tier, by same- vs cross-surface start, by item speaker. The shadow record splits off-arm misses into preventable and not.
- **Co-primary:** contradictions of seeded AI-established items in turns 1–10, by speaker. Recorded as an exception to [EV] §1.1's one-primary rule.
- **Secondary:** seed-check hits in turns 1–10; recall requests and `corrects_ai`; first-call rate; turn-1 routing changes; truncation shares.
- **Vendor-memory staleness sentinel:** stale assertions in turns 1–3 of chats where Northstar never delivered the old version (no context receipt holds it). These are attributable to vendor memory or vendor chat search. Reported per connector to C21.
- **Detector validation:** C22 re-judges 10% of verdicts with the eval judge; precision and recall ≥ 85% on the golden set before live numbers are reported (SP-AC-3).

| SYN §7.2 bar | Measured by | Reported per |
|---|---|---|
| ≥ 30% fewer re-explanations in turns 1–5 than pack off | Detector (live); simulated user (offline) | Tier, connector, surface pairing; L0 with bounds |
| Continuity recall ≥ 80% and ≥ 10 points above vanilla + vendor memory | Offline probes | Surface pair |
| AI-said recall ≥ 80% and within 5 points of user-said (raised from SYN's 75% and 10 points) | Offline probes by speaker; live hits on AI-said items | AI vendor family (SD-38) |
| Cross-surface recall within 10 points of same-surface, both directions | Offline cross pairs; live split | Direction |
| ≥ 50% fewer re-proposals | Offline probes; live `rejected` seed hits | Tier |
| Stale assertions ≤ 5% | Offline probes; live `superseded` seed hits | Tier |
| No rise in agreement on contested prompts | Offline sycophancy probes | — |
| Pack ≤ ~3k tokens | Compile records | Channel |
| False seed corrections: no rise against shadow in turns 1–10 (review bar) | SP-AC-7 replay; live seed-correction verdicts vs the shadow arm | Seed kind, tier |

---

## 12. Robustness, latency and failure

- **When a C23 model loses focus (GOAL §4.7):** routing and selection are deterministic first; the router model only chooses among candidates under a schema and substring validators, with deterministic fallback; packs are deterministic (CK-9) and cannot write to the ledger; detector verdicts feed metrics and link *candidates* only, which pass J5 and C12; every model output is recorded (SPINE §8.5).
- **Fault injection (C22):** random router picks, noisy embeddings, dropped links. Pass: metrics degrade within bounds and the `not_routed` and `not_linked` sentinels fire within a day.
- **Latency:** deterministic routing p95 < 300 ms; model call < 1 s; pack p95 < 1.5 s (SPINE §4.4, §8.1); hook turn 1, re-route plus pack p95 2.0 s (§4.3). C15 precompiles goal sections on `ledger.committed`; starts mostly assemble and fit. Over budget, part S ships and K follows.
- **Failure:** fall back to the last cached part S for the top goals, or nothing; never block the product (SD-29); receipts record it.
- **Starting parameters** are those given in §3–§9, bundled as `continuity_params@v1`.

---

## 13. Interfaces

**C23 needs.**

| From | Shape |
|---|---|
| C10 events | `session.opened(handle, start_kind, context_ref, parent_handle, capabilities, arm)`; `session.early_turn(handle, turn ≤ 5, text_or_hash, fidelity, paste_ranges, northstar_block_ranges, prior_hint_texts?)`; `delivery.receipt` |
| C10 applier | Accepts `RoutingRecord` (a `routing_record` row), seed `ADD`s with `actor: seeding` (§5.1), `ReexplainVerdict` (§7.2), `LinkCandidate`, `ContinuityReceipt` (§8.6); validates I22 and scope |
| C10 in-session design | The Drift Checker honours `seed_kind`, `authority`, `delivery`, `on_route` and the severity caps (§5.1) and reports seed hits with the seed ID. The Goal-Change Handler supersedes seeds per §5.3 from its item-level output ([IS] §5), reports low-confidence continuations for re-routing, and reports a confident `goal_change` or pivot toward a goal not on the stack (mid-chat routing, §4.3). The applier handles `items.retracted(ids)` per §5.3. `restart.prepare` passes `parent_handle` and session selections |
| C08 index port | `goal_cards.search`, `items.by_links`, `items.hybrid`, `items.as_of`, `relations.subgraph`, `best_rank`; goal cards rebuilt on commit and on session goal changes |
| C09 `session.db` (read) | Recent and live session items; context receipts; last-delivery watermarks; the pending-resume registry (written by the C10 applier, TTL 24 h, §4.3) |
| C04 | `context.get{moment: session_start | turn_start (≤ 3) | tool_call (first); hint_text?; prior_hint_texts?; budget_chars}`. `prior_hint_texts` is a new optional field (minor version, SPINE §4.4). `context.get` also reaches C23 on any later turn with a confident GCH `goal_change` or pivot toward a goal not on the stack (mid-chat routing, §4.3) |
| C18 | Active `hide`, `reject_content`, `misstated`, `must_link`, `cannot_link` by item and goal |
| C19 | `egress.allowed(item_id, target_vendor_family) → bool`; excision purges receipts and cached sections |
| C20 | `goal_router`, `reexplain_detector` roles, family-routed and recorded |
| Connectors ([CX §2.3, §4.3, §5.4]) | First `northstar_context` call: `user_message` copied exactly; an optional `northstar_context` argument `prior_user_messages` (≤ 4) when late, mapped to `prior_hint_texts` (a requested minor addition to the [CX §2.3] schema). Restart prefills carry the handle and one fixed line |

**C23 provides.**

| To | Shape |
|---|---|
| C15 | `PackRequest{kind: core_pack | resume_pack | card(purpose: continuity_delta | goal_section) | model_context(continuity strip, §8.4); part: S|K|V; session; routed_goals[{id, p}]; selections{slot: [item@ver]}; guard_only[]; budget_chars; render_profile; as_of_watermark}` → `Artifact{artifact_id, hash, items[], truncations[], parts[]}`. Only artifact kinds in SPINE §5.2's extended list are used (pin, card, correction, core_pack, resume_pack, boot_text, charter, slice, prefill, model_context); card `purpose` and `boot_text` `profile` are fields, not kinds |
| C05 | `northstar_fetch(id)` semantics for items, goals and passages (§3.5); query mode only if R3 wins (D3) |
| C21 | `continuity.route.*`, `.pack.*` (size, truncation, AI-said share by vendor family), `.seed.*`, `.reexplain.*` (rate, causes, coverage), `.first_call_rate`, `.unprompted_echo` |
| C22 | `continuity.replay(...)`; receipts; verdicts; arm flags |
| C11 → J5 → C12 | `LinkCandidate{goal_id, item_id, basis: reexplained, session, turn, unit_span_hash}` in `session.db`, read at episode close |
| C13 J5 | Read access to delivered artifact text and receipts by vendor family and window, for the echo rule (§9) |
| C16, C17 | Context receipts by session (SPINE §5.6) |

---

## 14. Departures from SPINE

| # | SPINE says | This design | Why |
|---|---|---|---|
| D1 | Seeding enters the **delivered** pack items (§3, C23 table) | Also seeds **guard-only** items (rejected, disputed, constraints for routed goals) cut by the budget or deferred; cheap checks; corrections only on a tier-0 exact or alias match or a quote-backed tier-2 verdict; ≤ 1 guard correction per turn, ≤ 1 per item, ≤ 3 per session | Budget cuts should not remove protection against re-proposal and re-assertion, which SYN §7.2 bars. A hit delivers the item in a specific correction. False positives bounded by thresholds, the caps and the SP-AC-7 bar (RISK-AC-2, §11) |
| D2 | With no first message, the start carries goals, constraints and recent provisional items; knowledge follows on turn 1 (§4.6) | At `p ≥ 0.7` from lineage or context, the start also carries knowledge and conclusions; turn 1 sends the delta | Routing is reliable without the message on compact, fork, resume and in a repository with a strong `context_ref`. Codex's turn-1 channel (~2,500 tokens) is shared with the pin, so knowledge moved earlier is not cut. A wrong start is bounded by the threshold and fixed at turn 1 |
| D3 | `northstar_fetch` returns an item by ID (§6.2) | Goal IDs return a goal section (goals are Agenda items, so within SPINE). Free-text query mode **only if** arm R3 wins | Agentic search scored 72.5% vs 48.5% for RAG [14 F10]; the arm must be testable through the same read-only tool |
| D4 (**adopted; not a departure**) | SPINE §5.3 does not limit `northstar_echo` to a session. TEXTBOOK §5.9 now says the same (TB X17; ARCH R4) | The echo rule also covers later sessions of the same model family within 90 days, when the span has no fresh grounding | Vendor memory can carry pack text into later chats (SYN RISK 11); otherwise an absorbed line returns as independent AI-said support |

Not departures: `prior_hint_texts` is an optional field (SPINE §4.4 minor-version rule); open sessions in slot 11 follow SPINE §5.5; the `basis` field and the extended receipt fill in SPINE sketches.

---

## 15. Risks

**SPINE and SYN risks carried here:** 4 (desktop start is model-pulled: one first call carries everything, first-call sentinel, widget strip); 7 (AI-taught errors carried forward: chips, disputed slot, `ver`); 9 (packs re-inject captured text: data records, I5, I22, CK-3, §3.2 rule 9, CK-10, red-team canaries); 11 (vendor-memory absorption: §9, D4, §3.2 rule 3's `vendor_memory_possible` note, staleness sentinel); 12 (noise: ≥ 8 samples, CIs); 13 (cross-vendor exposure: C19 egress, SPINE UQ-12); 19 (model-reported items: chips, reconciliation); 22 (contested items: slot 10); 24 (wrong parent from a bad join: lineage only from explicit handles, hook parents or prefills); 25 (fabricated reports: RISK-AC-8; guards G1–G6 and the fabrication sentinel, §4.1); 33 (path B contributes nothing: §6.3); 34 (reported goals lack authority: slot 4, a verbatim restatement confirms under G6; steering is ARCH DQ-10); 35 (packs into an employer-account chat at L0: delivery follows the install-time account declaration, UQ-3).

**New risks.**

| # | Risk | Threatens | Mitigation |
|---|---|---|---|
| RISK-AC-1 | **Misrouting** puts irrelevant knowledge in the chat, raising over-personalization and sycophancy [14 F12] | §3.3; §6 criterion 2 | Calibrated thresholds; model only when ambiguous; re-routes on turns 1–3; `not_routed` sentinel; SP-AC-1 |
| RISK-AC-2 | **Over-constraining seeds:** false corrections, or resistance to a change of mind | §3.3; §4.3 | Goal-Change Handler first (item-level output); user supersession; reopening lifts rejections; severity caps; no tier-1-only guard corrections, ≤ 1 per item and ≤ 3 per session; off-route demotion (§5.3); SP-AC-7 bar (§11) |
| RISK-AC-3 | **Unreliable re-explanation metric:** no benchmark [14 F13]; unknown precision; L0 sees only called turns | §6 criterion 2 | Golden set and eval-judge re-judging (≥ 85%); coverage bounds; L0 reported separately; offline simulated user as a second source |
| RISK-AC-4 | **Cross-vendor absorption:** delivered content is stored in the other vendor's memory and resurfaces stale | §3.3; privacy | Hidden channels; supersession notes; D4; SP-AC-6; SPINE UQ-12 |
| RISK-AC-5 | **Small channels thin the knowledge slot** (Codex ~2,500 tokens, widget ~1,200 chars); AI-said recall may miss its bar there | §4.2; §6 criterion 2 | Parts S/K/V; knowledge floor; fetch; per-channel reporting |
| RISK-AC-6 | **Start latency** from a routing call or cold compile | §4.1 | Precompiled sections; deterministic first; part S fallback; fail open |
| RISK-AC-7 | **Concurrent sessions** establish opposite provisional items | §3.3 | Contested pair, never silently picked; pair sentinel |
| RISK-AC-8 | **Fabricated rejections or disputes** from model reports (possibly injected, RISK 25) suppress valid options later | §4.2; §3.3 | `reported` chip; guard-only in their first later session; re-derived on reconciliation; G4 decay (§4.1); fabrication sentinels ([GD §7], §4.1) |

---

## 16. Questions for the user

| ID | Question | Why it is the user's | Working assumption (pending user answer) |
|---|---|---|---|
| **SPINE UQ-12** (formerly UQ-AC-1; ARCH DQ-3(b)) | **Carrying knowledge across vendors.** To start a ChatGPT Desktop chat with what was established in Claude Code (and the reverse), Northstar must put content captured on one vendor's product into the other vendor's chat. That vendor then receives it and may keep it in its own memory, outside Northstar's control and beyond excision. May Northstar do this? | It accepts an exposure (RISK 13, RISK-AC-4). Declining would limit continuity to within one vendor, which narrows GOAL §3.3 and §4.6, so it is the user's choice | As SPINE UQ-12 and [PL] §6.3: **Yes** for personal `normal` items; `sensitive` items masked where the vendor would gain new exposure; `private`, work and unclassified items only to vendor families that already hold every source span ("no new exposure"). Related to UQ-11, which covers model workers, not chat delivery |

Otherwise covered by SPINE: live pack-off arms (UQ-9); pre-armed blocks and prepared chats (UQ-1); which accounts receive packs (UQ-3); path B (UQ-8a); reported goals across sessions (SD-36, kept with guards after the review, §4.1); whether reported goals steer later chats and reported constraints persist (ARCH DQ-10); vendor-memory policy (SD-16, HOW).

---

## 17. Spikes

| Spike | Question | Settles |
|---|---|---|
| SP-AC-1 | Routing golden set (synthetic multi-goal personas, four connectors): top-1, recall@3, no-route precision, latency | §4.2; RISK-AC-1 |
| SP-AC-2 | Budget sweep (1k–5k tokens); floors; gist vs verbatim; third- vs second-person framing | §3.4; budget and sycophancy bars |
| SP-AC-3 | Re-explanation golden set (restatements, references, recall requests, pastes); detector vs eval judge; reference threshold | §7.2; RISK-AC-3 |
| SP-AC-4 | Claude Code `SessionStart` output per source and timeout; Codex `SessionStart` cap and position (beyond P5, P12: (Unv)); hook turn-1 re-route plus pack latency against the 2.0 s budget | §8.2; §4.3 turn-1 budget; D2; RISK-AC-5 |
| SP-AC-5 | L0 first-message copy fidelity; whether a late call passes `prior_user_messages` (extends CD-S3, CS5, CS6) | §7.5 |
| SP-AC-6 | After a week: do one vendor's pack lines appear in the other's memory; unprompted-echo rate (extends CS10, DS9) | §9; D4; RISK-AC-4 |
| SP-AC-7 | Replayed starts where the user changed course: false-correction rate per seed kind, incl. guard-only | §5; D1; RISK-AC-2; **feeds a bar** (§11) |

**Depends on:** CD-S1, CD-S2, CD-S3, CD-S5, CD-S11, CS1, CS4, CS5, CS6, CS11, DS2, DS3, DS7, DS9, DS10, SP-1, SP-6, SP-7.

---

## 18. Goal-fidelity check

| GOAL item | Served by | Status |
|---|---|---|
| §3.3 Cross-session: relevant goals, knowledge and conclusions without re-explaining | Router, required knowledge slot, seeding, delivery by level, resume pack | **Hook tier: partial until measured** (designed to meet it; RISK 12, RISK-AC-1; RISK-AC-5 on Codex). **Desktop chat: partial** (RISK 4, 34; nothing under path B, RISK 33) |
| §4.5 Both AI aims, equally | Own router, selection, seeding, detector, receipts, model roles, degradation rules and measurement; seeding joins the in-session checks | Met by design in depth; delivery limits as §3.3 row |
| §6 criterion 2, measured | Detector, receipts, replay hook, arms, per-bar hooks | **Partial:** live arms need UQ-9; desktop L0 only with coverage bounds (RISK-AC-3, RISK 4) |
| §4.2 AI-said first-class | Speaker-neutral score (CK-6); AI-taught passages in the required slot; AI conclusions attributed; AI-said recall bar; parity sentinel | Met at hook and observed tiers; **partial on desktop L0** (RISK 19, 33, RISK-AC-5) |
| §3.1 Attributed, evolving, history kept | Chips; supersession notes; history by fetch | Met |
| §4.1 No rituals | No per-chat step on hook tiers; one-time boot line on desktop; never a prompt about re-explanation | Met on hook tier; desktop conditions as SPINE §12 |
| §4.3 The AI manages it | Routing, selection, linking, seeding, tuning automatic; corrections optional | Met |
| §4.4 Two architectures, one core | Packs project the Book's leaves; shared IDs; receipts feed "this chat draws on" | Met |
| §4.6 Product-agnostic | Keyed on levels and budgets; product-blind routing and selection (I23, CK-6) | **Partial:** cross-vendor delivery pending SPINE UQ-12 (RISK-AC-4) |
| §4.7 Robust maintainer | Deterministic first; constrained model steps; recorded outputs; CK-1–CK-10; links via J5 and C12; gated releases (I19); fault injection | Structural errors met; router and detector errors bounded statistically (RISK 6, RISK-AC-1, RISK-AC-3) |
| §4.8 Prototype built and evaluated | Replay hook, arms, ablations, probes, bars, spikes | Met by plan |
| §5 constraints (supersede, no summaries of summaries, sycophancy, injection) | §3.2 rule 3; CK-7; third person; I5, I22 | Met by design; sycophancy measured (SP-AC-2) |
| §7 Reframing needs the user | No reframe; SPINE UQ-12 asks the one exposure question; ARCH DQ-10 asks whether reported goals steer | Checked |

---

## Consistency fixes (2026-10-08)

| Issue | Change |
|---|---|
| X01 | [CX §1.2, §2] is the tool contract: boot line and first call use `northstar_context`; a restart pack comes by handle through it (§8.3, §8.5); citations in §3.1, §3.5, §13 moved to [CX] |
| X06 | §3.4 restates [CX §2.7] (MCP) and [HK §15] (hooks): first call 12,000; per-turn 4,000; prefill = handle + one fixed line, ≤ 600, no item text; L2-inject start ≤ 1,500 (part S), per-turn 600 / 1,800; relay first call 12,000. §8.3, §8.5, §10 match |
| X07 | §5.1 seed shape: `ADD`, `actor: seeding`, `actor_ref`, `seeded_from {item_id@version, artifact_hash, delivery_receipt}`, `seed_kind`, `delivery`, `on_route`, original `by`; no SEED/ROUTE ops; authority `confirmed`, `provisional`, `reported` |
| X09 | §4.3, §13: one pending-resume registry in `session.db` (C10 applier writes, C23 reads, 24 h); adopted only on a handle or a route with `p ≥ 0.7`, with lineage, reversible |
| X25 | §3.2, §3.3: `cited_unchecked`; `ver` order supported > mixed > unchecked tier > contradicted |
| X30 | §8.4, §8.5, §13: SPINE §5.2 extended kinds (slice, prefill, model_context); card `purpose` and `boot_text` `profile` are fields |
| X32 | §7.4: `continuity_params` releases follow SPINE I19's one rule, as [MT] J10e does (J10e since dropped for the prototype; see Final-gate fixes) |

---

## Review revisions (2026-10-08)

The review fixes for this file. The full review record is [`REVIEW.md`](../REVIEW.md) (§5 findings, §6 fixed differently, §9 carried tasks, §10 smaller issues).

| Finding | What changed here |
|---|---|
| AIE-1 | §5.3, §13: "goes to the Goal-Change Handler first" now means [IS] §5's item-level output, naming the seeds a turn reverses, reopens or refines |
| AIE-2 | §3.1 slot 4: neutral label "as reported by <chat model>; not the user's verbatim words"; cap 2 → 4. §3.7: G15's tail reworded to match. §5.1: the `reported_goal` row and a new model-reported constraint row follow ARCH DQ-10; until it is answered, they work as now |
| AIE-3 | §5.1: a seeded AI conclusion is High if the user accepted it or it is verified; Medium otherwise |
| AIE-5 | §4.3: mid-chat routing on a confident GCH `goal_change` or pivot toward a long-term goal not on the stack; at `p ≥ 0.7` with a margin, the goal's section (part K) is delivered within the card budget and seeded, guard-only items included. §13: `context.get` reaches C23 for this case |
| AIE-6 | §5.2: a guard-only hit corrects only on a tier-0 exact or alias match or a quote-backed tier-2 verdict, never tier 1 alone; caps 1 per turn, 1 per item, 3 per session (D1 matches). §5.3: off-route rejected and disputed seeds become guard-only at medium; constraints sharing the session's `context_ref` keep their severity; demoting other off-route constraints is an ablation arm (§11). RISK-AC-2 updated |
| AIE-10 | §11: AI-said recall bar ≥ 80% and within 5 points of user-said; co-primary live metric (contradictions of seeded AI-established items in turns 1–10, by speaker), recorded as an exception to [EV] §1.1; SP-AC-7's false-seed-correction rate is a bar (no rise against shadow in turns 1–10). §17: SP-AC-7 feeds a bar |
| AIE-12 | §3.2 rule 3: also note the latest superseded version said in a captured chat on a `vendor_memory_possible` connector, after Tier A, budget permitting, seeded as a `superseded` guard. §11: vendor-memory staleness sentinel for turns 1–3 |
| CONS-2 | §3.1 slot 2 and §3.6 CK-3 test recorded authority: a verbatim user span, or a click-bound `agenda.confirmed` event with ARCH DQ-10 yes. A click-confirmed line is labelled until verbatim text arrives |
| MR-8 | §5.3: on `items.retracted(ids)` the C10 applier retracts matching seeds, expires queued corrections that cite them, and invalidates pins and pending resume packs. §13 notes it |
| SEC-4 | §3.2 rule 9 (new): one rendering rule for every model-facing artifact; third-person restatement; commands in inert, labelled code blocks; flagged spans never verbatim on auto-pushed channels; taint by measured overlap. The old rule 9 (plain-text delimiters) is now rule 10. §3.4 step 4 and §3.5 obey rule 9. §3.6: CK-10. §15 risk 9 and §18 updated |
| SEC-5 | §4.1: guards G1–G5 and a fabrication sentinel for reported goals and questions; §7.2 step 8: G6 confirmation rule; §4.2: G3 cap noted. §15 risks 25 and 34, RISK-AC-8 and §16 updated |
| R3 (ARCH §12.2) | §6.4 and §16 follow SPINE UQ-12 and [PL] §6.3 |
| R4 (ARCH §12.2) | §14 D4 relabelled as adopted, not a departure (TEXTBOOK §5.9 now matches) |
| R11 (ARCH §12.2) | §15, §16, §18: UQ-AC-1 replaced by SPINE UQ-12 |
| AIS smaller issues | §3.1: the no-route goal menu is stated as data and not delivered on `new_topic`. §4.3: hook turn-1 budget (re-route plus pack p95 2.0 s inside the 2.5 s client deadline), measured in SP-AC-4; if exceeded, the routed goal section goes first. §12 and §17 match |
| FEAS-1, CONS-9 | Landed at the final gate. §5.2: no seeds on path B; under `per_turn_readonly`, seeds wait for the first declared write ([CX] §2.5 rule 5). §6.3: saved paths C1, C2, W or A; path B on either app gives nothing. §7.3: no ephemeral session cache. §7.5: path B keeps only content-free operational logs. §8.3: seeding waits for a declared write under `per_turn_readonly` |
| AIE-9 | Landed at the final gate. §3.1 slot 1 header and the §3.7 example end with "Supersedes all earlier Northstar blocks in this chat." ([IS] §8.2; [CX] §2.6) |

**Wording note.** The click-confirmed line in §3.1 reads "confirmed by the user's click", not "your click", because pack lines are third-person records (§3.2 rule 1) read by the model.

---

## Final-gate fixes (2026-10-08)

The final gate found review fixes that had not reached this file. Each is a HOW change; no non-negotiable is weakened.

| Finding | What changed |
|---|---|
| FEAS-1, CONS-9 | Path B and read-only paths follow [CX] §2.5's stateless rule: no session cache, no seeds before a declared write, content-free logs only (§5.2, §6.3, §7.3, §7.5, §8.3) |
| AIE-9 | Pack header states that it supersedes earlier Northstar blocks (§3.1, §3.7) |
| L2-inject content rule (SEC smaller issue) | Visible start blocks follow the [OBS] §4.4 content rule: the user's typed goals and constraints only; no reported goals, disputed AI claims or recent provisional items (§3.4, §4.3, §8.5) |
| CPLX-8 | J10e is dropped for the prototype, so §7.4 cites the rule [MT] D4 states; X32 annotated |
