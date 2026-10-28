# What changed on 2026-10-09, and what is still open

**Status:** the concise explanation you asked for in comment 6. It accompanies the revised [ARCHITECTURE.md](../ARCHITECTURE.md), which stays the approval document. Proposal and evaluation-plan stage only: nothing is approved, built or run, and the approval process is unchanged unless you say yes to DQ-14(c), which would start the baseline before design approval (GOAL §7). Written 2026-10-09; an internal check the same day led to the fixes listed in §9.
**Authority:** [GOAL.md](../../GOAL.md) overrides this file. Where a document in this folder conflicts with an older spec, the document in this folder wins until the specs are updated after approval.
**Reading:** about 10 minutes. §1–§5 answer your comments 1–5 in order. §6 lists what is still open. §7 records where the five revision documents disagreed. §8 lists the older spec sections they supersede. §9 lists the check fixes.

| Comment | Detailed design | In ARCHITECTURE |
|---|---|---|
| 1. Platforms | [platform-and-devices.md](platform-and-devices.md) [PF] | §0, §2, §9, §11 |
| 2. Connectors | [connector-strategy.md](connector-strategy.md) [CN] | §0, §7 |
| 3. Knowledge organization | [knowledge-organization.md](knowledge-organization.md) [KO] | §3, §4.3 |
| 4. Personal relevance | [personal-relevance.md](personal-relevance.md) [PR] | §3, §4.1–§4.2, §5, §6 |
| 5. Evaluation | [benchmark-v0.md](benchmark-v0.md) [BM] | §10, §11 |

---

## 1. Platform support (comment 1)

**What the proposal now says.**
- Northstar works on **Windows and Mac**, in your order: **Windows first, then iOS, then Mac**.
- **One core, many edges.** One core on a machine you control holds the one shared memory. Each computer runs a small native edge (hooks, MCP proxy, spool, pin cache). Phones run nothing; they reach Northstar through the vendors' apps.
- Every Mac-specific piece now sits behind an OS port with a Windows, Mac and Linux adapter. An OS-blindness test checks that the core behaves identically on all three.
- All four first connectors run on Windows (verified 2026-10-09, [PF] W1–W13).

**What changed from before.** The 2026-10-08 design ran on one Mac. We found about 20 Mac assumptions: launchd, Unix sockets with code-signature checks, the Keychain, Touch ID, FileVault, Time Machine and Spotlight exclusions, Mac paths, the hook launcher, a Mac-only `.mcpb`, the Accessibility observer, and a verifier sized for a 48 GB Mac. **All of them were at the edge or in deployment; none was in the core's logic** ([PF] §2.1).

**Limitations and tradeoffs, stated plainly.**
- **Windows proves less about which program is calling the core** than a Mac's code-signature check. Credential limits still stop a fake caller from gaining authority (RISK-PF-1).
- **Windows Home without BitLocker or Device Encryption** has no encrypted-volume fallback, so Northstar would encrypt its own stores, at some speed cost (SP-PF-4).
- **Most Windows PCs cannot run the independent verifier**, which needs about 24 GB of graphics memory. Without a qualifying machine, checks run on the workers' own vendor and are labelled "not independent" (RISK-PF-4).
- **iPhone limits:** no Northstar process, no observer, no local MCP and no hooks can exist there. Phone chat apps call tools from the vendor's cloud, so **Claude phone chat needs an endpoint reachable from the public internet**. ChatGPT phone chat may not while a computer is awake: chats typed on the phone can run on a connected Windows or Mac computer and use its MCP servers (verified; whether Northstar works there is spike SP-PF-17). Reading the Book on the phone and coding driven from the phone need no public endpoint.
- **The remote connector bypasses each computer's edge.** It carries no device identity, so marking a device "work", revoking a device and spooling do not apply to it; it is scoped by the account you declared, revoked per vendor, and loses turns made while the host is down unless you run an export. So Claude Desktop chat moves to it only as an opt-in per device.
- **Order across devices** follows when words were said, not when they arrived: a laptop reconnecting after a day cannot undo a view you revised on your phone (a Stage I gate).
- **"Local now" cannot mean "one Mac" once phones join.** We propose "self-hosted now": everything on machines you control, plus one narrow public endpoint. This touches GOAL §4.6, so it is asked as DQ-13, not adopted.
- **Cost:** about +9 to +15 builder-weeks; a rented host, if you chose one, about $5–20 a month (Unv).

**Why.** Your answer: Windows and Mac as a strong preference, many machines and potentially phones sharing one memory. One core keeps the single Apply gate that makes maintenance robust (GOAL §4.7). A core on each device that synced would let two gates race on merges and break hash-identical replay, so we rejected it ([PF] §4.3).

---

## 2. Connectors: shared integration or a connector per app? (comment 2)

**What the proposal now says.** Neither extreme. Northstar uses **one shared integration layer with three shared engines**, plus thin per-product adapters:
- one MCP server and widget for every chat app, on Windows, Mac and iOS;
- one hook engine for every product with lifecycle hooks (Claude Code, Codex; later Gemini CLI, Cursor, VS Code);
- one optional observer core, with one backend per OS, only with your consent.

About 85% of connector code is shared (about 75% if the observer is built).

**What MCP achieves alone, judged by effectiveness** ([CN] §3):

| Capability | MCP alone | Hooks (where offered) |
|---|---|---|
| Capture | Weak: the model's copy of your words, on called turns only; AI explanations only as short "reported" points | Both sides verbatim, every turn |
| In-session focus | Partial: a state note on called turns; every turn only if the widget note persists (Unv) | A note every turn; the real reply checked; one correction before control returns |
| Cross-session continuity | Good only if the model calls Northstar before its first reply; that rate is unmeasured (CD-S3, CS5); otherwise none. One call returns the full pack | Pack before the first reply |
| Independent record for audits | None | Yes |

The reason is structural. With MCP, the chat model decides when to call Northstar and what to report. That is the attention-losing agent your goal warns about.

**Where product-specific code is necessary or clearly better:**
- **hooks wherever a product has them** (about 1,000–1,500 lines each), because they beat MCP on every capability;
- **observer UI profiles**, only with your consent: the only verbatim route on the chat apps, but brittle and grey under vendor terms;
- **packaging, install and restart links** per product and OS.

**What changed from before.** The 2026-10-08 design already shared one MCP contract and one hook engine. This revision:
- makes the connection rule explicit (SDK if we own the loop; hooks if offered; MCP plus widget plus boot text where MCP is spoken; observer only with consent; exports for backfill);
- compiles the hook engine on every OS from the start, because Windows needs a real `.exe`;
- makes the remote connector a first-class channel, since it is the only way phones reach Northstar;
- adds phone rows. Claude for iOS works through a remote connector; ChatGPT chats typed on the phone may use your computer's local server while it is awake (SP-PF-17), and phone-native ChatGPT chats are unknown (SP-PF-7). Coding driven from the phone keeps hook quality, because the session runs on your computer.

**Why.** You asked for a choice by actual effectiveness, with no mandate either way. What is measured, and what is not: **MCP-only against hooks is measured on the CLI track** (an automated arm M on Claude Code and Codex, hooks off, same scripts: F1, K1, verbatim share of AI-said capture, call rate); **chat-app cells measure MCP plus the widget against no Northstar**, because those apps offer only MCP; **observer against MCP** only if you allow the observer (DQ-1). A first-call gate (≥ 90% of new chats) is pre-registered per connector and reported next to continuity. Per-connector, per-OS diagnostics (call rate, widget delivery, verbatim share, your actions, latency) explain the rest.

---

## 3. Knowledge organization: integration, subdivision, consolidation (comment 3)

**What the proposal now says.** Yes, the method evolves the structure in both directions, and [KO] explains it with seven worked examples, **with one limit:** Northstar cannot state a broader principle that nobody stated. Across branches it can show what related pages share, sentence by sentence with citations, but a general claim needs a source, yours or an AI's, that states it (§6.10).
- **Two layers.** The core says *what the ideas are*; the Book outline says *how they are presented* (section → subsection → page → chapter → part). Identity changes are rare, high-tier and audited. Presentation changes are computed by code, budgeted and reversible.
- **Where new material belongs.** Code scores six signals, strongest first:
  1. an explicit reference (your typed words, or an item delivered in that chat);
  2. the question or problem it serves;
  3. the claim it argues with;
  4. the reasoning it continues;
  5. shared concepts;
  6. similarity, which only finds candidates (it may choose a section only inside a page the other signals chose).

  Code then walks a fixed ladder: not organized → attach → extend → new narrower idea → new page → new branch. Each placement shows its top two reasons.
- **When to subdivide.** A section becomes a subsection when it is relevant, persistent and cohesive, and either large (≥ 8 linked items) or anchored on its own question, problem or view (≥ 4). Size alone never splits. A page that grows ≥ 3 separable subsections becomes a chapter, keeping its addresses.
- **When to consolidate.** Four forms:
  - duplicates merge (two model families must agree);
  - a subsection that thins out folds back;
  - overlapping chapters merge;
  - a principle that appears across branches gets a broader idea and an overview page, while the related pages stay where they are.

  Inactivity alone never consolidates anything.
- **Overviews never summarize summaries.** Each one is written from source items, at least one per child. Chapter and part overviews keep the textbook's cited sentences. A cross-branch overview states a general claim only when a source states it; Northstar's own delivered text never counts as that source.
- **Stability.** Entry thresholds are higher than exit thresholds; triggers must persist; nothing reverses within 4 editions. Every change can be undone and is viewable as of a date. Four optional corrections are added.

**What changed from before.** The 2026-10-08 design could split and merge chapters by size, merge two names for one idea, and split a concept whose meaning changed. It could not grow a section into a subsection, grow a page into a chapter, fold back, merge overlapping branches, generalize across branches, place material by the reasoning it continues, or keep generic hub terms from gluing chapters together ([KO] §8).

**Why.** You asked whether the method supports evolution both ways and how it decides. When unsure, the rule is to do whatever is cheapest to undo, so a wrong guess costs little. The method is measured on planted growth scenarios (for example, misplacement ≤ 10% of pages; false merges ≤ 5%; invented themes ≤ 10%), and in session 2 you judge 16 real placements and changes.

---

## 4. Personal relevance and "what to learn" (comment 4)

**What the proposal now says.** Relevance is **a topic's role in your thinking**, computed by code from your recorded acts: you asked about it in pursuit of something, stated, argued, applied or revised a view, built on an explanation, took up an AI suggestion, or came back to it on another day. **Naming a term in passing is not an act**, and terms used across many unrelated conversations need a strong act. **No model judges "this matters to you"** in production, because models over-infer user attributes.
- **Roles.**
  - *Anchored*: part of your thinking; organized.
  - *Supporting*: objective material that answers your question, is a reason or objection in your argument, or is a prerequisite you engaged with (asked about, followed up, or said you did not follow). It is organized as a section of what it serves. A generic prerequisite used across many of your topics, which you never engaged with, stays background.
  - *Background*: kept, attributed and searchable, but not organized.
- **Lookups.** A lookup is defined by relevance, not form: a context-free question with no stated purpose, answered and not followed up, whether phrased as what, how or why. A question is a lookup only if two independent labels agree, it has no reference to you, your project or earlier turns, it was answered at once, and you did nothing further with it. "What is an LLM?" asked once is background. If you later ask how an LLM should behave in your project, the topic is organized and the earlier lookup is attached to it.
- **What to learn.** Gaps exist only on the paths of your goals, questions, problems, interests and views. A term that merely appeared is never a gap, and a prerequisite becomes one only after an act of yours on it. An AI suggestion you did not take up shows only when it lies on an anchor's path, labelled "not taken up", never as a gap. New gap kinds: open objections to your views, and tensions among your own views.
- **The glossary is replaced** by "Terms in your book" (only terms the Book covers) and a "Looked up" list in the back matter.
- **Your views are first-class.** Issue pages ("Where you stand") show your position, reasons, objections and how your view changed, all quoted. AI reasoning is never stored as yours unless you stated or accepted it.
- **When a reply contradicts your view without acknowledging it,** how hard Northstar pushes back is your decision (DQ-19, §6.9), because it weighs in-session focus against sycophancy. A reply that engages your view and disagrees with reasons is never drift. Until you answer, the 2026-10-08 rule (high severity) stands.
- **Guardrails.**
  - Relevance is authorship-blind: building on an AI explanation counts exactly like your own statement, and a passing mention counts for neither speaker.
  - It describes role, never mastery.
  - Interests are topics with evidence, never traits, and never enter AI context as facts about you.
  - Nothing captured is deleted.
  - Objections travel with your views into chats, so the system does not echo you back to yourself.

**What changed from before.** The 2026-10-08 design gave a page to any concept with one long explanation, two mentions or any question, "What is an LLM?" included. It made every unexplained term a gap and kept a glossary of every term ([PR] §1).

**Why.** You asked for personal relevance, not subjective versus objective, as the line, and for a Book about your intellectual development rather than an encyclopedia. Supporting material keeps objective information when it serves your thinking. Background material stays findable, so nothing is lost if a topic matters later.

---

## 5. Evaluation: baseline first (comment 5)

**What the proposal now says.** Benchmark v0 is the first evaluation, run twice on the same scripts from your real topics, in the same four products on Windows:
- **Phase B** runs without Northstar. It can start before anything is built, once you approve the plan.
- **Phase N** runs with Northstar.

It has two parts:
- **Part A, AI assistance.** 40-turn drift scripts and continuity chains in the real apps, with your goals, constraints, rejected options and views planted, the AI's strongest objection to your view elicited, and the AI's explanations and recommendations elicited and quoted. Scored by a local judge of a third model family, blind to phase. On view items a reasoned disagreement passes; only ignoring or contradicting your view without acknowledgement fails, so echoing you is not rewarded. On the coding agents, an extra arm runs Northstar through MCP only, to compare it with hooks.
- **Part B, the human side.** About 2 hours with you, before and after, in four sittings of about 30 minutes or two of about an hour; or about 1 hour in a short format with weaker verdicts (DQ-14(e) asks whether an hour counts as short). Open-book tasks on your real record ("what did I conclude about X, and why?", "how did my view change?"), plus the relevance and structure checks. Your listed topics are split at random: some become scripts, the others tasks, so typing the scripts cannot rehearse the tasks.

**Improvement is defined in advance**, with guards:
- **F1**, late errors in long chats: ≥ 30% fewer and ≥ 5 points fewer, separately for items you established and items the AI established.
- **K1**, continuity recall: ≥ +20 points; ≥ +15 for AI-said knowledge and for your views.
- **U1**, Book answer correctness against your current means: ≥ +20 points.
- **U6**, relevance precision: ≥ 0.80.
- **Guards** include agreement on contested positions (F6, not up > 5 points) and AI-taught material on your real data (U7's AI-taught split, U10).

Verdicts are: clear, directional, no meaningful change, worse, no headroom, or underpowered. A full-size late baseline with Northstar switched off runs during Phase N; Phase B is the pre-registered baseline, and the late baseline is the comparison whenever model versions changed, which a months-long build makes likely.

**What changed from before.** The 2026-10-08 plan was heavier and synthetic-first, with no user sessions. Its parts are now kept as build gates (goldens, canaries, fault injection), folded into v0, or deferred to v1 (deeper replay, public benchmarks) and v2 (live arms on your real use) ([BM] §10).

**Why.** You asked for a manageable baseline-first benchmark covering both sides, with meaningful measurements on your real topics, and allowed short sessions. Cost: about 2 hours of your time if someone else builds (about 1 hour in the short format). If you build, also about 125–145 builder hours (about 42 of them typing), plus about 35–45 hours of labelling if no local judge passes (DQ-14(f)); Lite about 60–70 builder hours. About $250–650 of API, mostly the backfill the Book needs anyway. Unaided remembering stays unmeasured (DQ-16).

---

## 6. Unresolved questions and tradeoffs

The five documents raised 28 questions, and the check added two (Q-PR-6, BQ-10). We merged them into the items below, and added two tradeoffs the check surfaced (§6.9 is a decision; §6.10 is a stated limit). Questions that only change presentation are bundled with defaults in item 8.

**ID mapping:**
- PQ-1 to PQ-3, CN-Q1 and CN-Q4 → DQ-13
- BQ-1 to BQ-6, BQ-10 and Q-PR-5 → DQ-14; BQ-7 follows DQ-3(b); BQ-8 is settled as HOW
- BQ-9 → DQ-16
- CN-Q2 and PQ-4 → DQ-1
- Q-PR-3 → DQ-15; Q-PR-6 → DQ-19
- Q-PR-1, Q-PR-2, Q-PR-4 and Q-KO-1 to Q-KO-4 → DQ-17
- CN-Q3, CN-Q5 and PQ-5 → DQ-18

Full wording is in ARCHITECTURE §14.

### 6.1 Where the one memory lives once phones join, and what "local now" allows (DQ-13)

*Touches the goal (GOAL §4.6). Needed before the iOS stage.*
- **Options.**
  - Location: (i) an always-on machine you own; (ii) a VM you rent and control; (iii) your main computer plus a tunnel.
  - "Local now": (i) "self-hosted now", meaning machines you own plus one narrow public endpoint, behind OAuth, serving only the remote tool profile; (ii) the same, with the core on a rented VM; (iii) no public endpoint.
  - Tunnel: Tailscale Funnel (its relays cannot read the content), OpenAI's Secure MCP Tunnel (ChatGPT only), or Cloudflare (which can read traffic in transit).
- **Consequences.** (iii) keeps everything off the public internet, but Claude phone chat gets no Northstar (ChatGPT chats typed on the phone may still reach your computer while it is awake, SP-PF-17): a narrowing of "many machines and potentially phones". With an endpoint, Claude Desktop chat may move to the remote connector, but only as an opt-in per device, because device controls do not reach it. (ii) puts your data at a hosting provider, which is "cloud" in your words. A workstation core leaves phones and other machines without Northstar while it sleeps.
- **Recommendation.** An always-on machine you own, ideally one that also meets the verifier floor; "self-hosted now"; Tailscale Funnel for both vendors, with OpenAI's tunnel as ChatGPT's fallback.

### 6.2 Go-ahead for the baseline (DQ-14)

*Needed now, before session 1 and Phase B.*
- **Options.**
  - (a) Consent to use your real topics in scripted chats, one local export of your chats, and locally drafted tasks.
  - (b) Bench accounts (one extra personal account per vendor), your own accounts, or vendor memory off.
  - (c) Start before design approval. This changes GOAL §7's order for evaluation only; asked, not assumed.
  - (d) Standard (about 125–145 builder hours) or Lite (about 60–70), and the thresholds.
  - (e) Your time: does an hour count as short? Four sittings of about 30 minutes; two of about an hour; or a short format of about 1 hour with weaker verdicts.
  - (f) Only if no local judge passes: the builder labels everything (about 2,100 checks, about 35–45 hours), or a third vendor judges.
  - Phase B's other gates: DQ-2, DQ-5(a), and bench-folder encryption that needs no Northstar code (BitLocker or Device Encryption, or an encrypted container).
- **Consequences.** Without consent, the baseline-first measurement on your real topics (GOAL §6) cannot run. Your own accounts would expose them to whoever types the runs. Turning memory off understates the vendor baseline. Lite gives mostly "directional" verdicts. The bench accounts cost one plan per vendor for about 2 months.
- **Recommendation.** Yes to consent; bench accounts; start now; Standard with the stated thresholds; four short sittings; the builder labels if needed.

### 6.3 The desktop observer, now also on Windows (DQ-1, extended)

*The read part is needed before Stage 4.*
- **Options.** (a) No; (b) read only; (c) read plus a visible block where the widget fails; (d) also send messages.
- **Consequences.**
  - Without it, the chat apps never get verbatim AI-said capture (GOAL §4.2), and in-session focus there depends on the widget spikes.
  - With it, you accept the same grey exposure under both vendors' terms on both OSes. Windows shows no OS permission prompt, so Northstar's own consent screen is the only gate.
  - Expect repairs after app updates.
- **Recommendation.** If you accept the exposure and your employer allows it: (b), with (c) only where the widget fails. Build the Windows backend first, once the Windows chat-app spikes show where it is needed.

### 6.4 Your views in new chats (DQ-15)

*Touches the goal (GOAL §3.3 continuity against GOAL §5 sycophancy).*
- **Options.** (a) Only when the chat's goal or issue links them, always with their strongest open objection; (b) always; (c) never.
- **Consequences.** (b) raises agreement sycophancy: memory profiles raised it by up to 45% in the evidence. (c) means you re-explain your views in each new chat.
- **Recommendation.** (a).

### 6.5 "Helps you remember" stays unmeasured, or a closed-book block (DQ-16)

*Touches the goal (GOAL §3.2 "remember" against "not a quiz"). Needed before session 1.*
- **Options.** (a) No closed-book block in v0; (b) a 5-minute closed-book block in both sessions, for evaluation only.
- **Consequences.** (a) leaves "remember" At risk, by proxy. (b) measures it, but tests you, which the textbook design ruled out.
- **Recommendation.** (a); revisit after v0.

### 6.6 Tradeoff: personal relevance against AI-said knowledge being first-class (RISK PR-2)

*No decision now.*
- **The tradeoff.** Your own statements are acts in themselves. AI teaching counts only once you act on it: follow up, accept, apply or rely on it. Quiet engagement with AI teaching is therefore more likely to be missed. Relevance could then under-organize what AIs taught you (GOAL §4.2).
- **Where it can bite.** At topic level (is the topic organized), and in two quieter gates: the context cap (one context segment per page; your statements are always linked, so the cap binds mostly AI or pasted text) and the pack's knowledge slot (only anchored or supporting items; AI explanations nobody acted on reach new chats only through close retrieval).
- **Two deliberate asymmetries,** stated openly: acts come only from your turns (what "personal" means), and the explicit-reference placement signal counts AI text only when a delivery receipt grounds it, to stop echoes. The author of the content is never an input.
- **Mitigations in the design.** Authorship-blind acts; a silent-reliance detector (any number of earlier AI explanations); a speaker-swap test; AI-taught and user-stated recall within 5 points; topic, leaf and pack sentinels; structural parity, including explicit-reference placements; nothing deleted.
- **Measured on your real data** in v0: recall of the AI-taught items you list in session 1 (U7's split, within 15 points of user-stated); AI-taught false negatives among background topics with a replied-to AI explanation (U10, ≤ 20%); continuity for AI explanations you did not act on (a K1 sub-class).
- **If parity fails** in the golden book or in v0, the tension comes to you rather than being traded away. The choice would be between widening what counts as relevant for AI teaching (more generic material in the Book) and accepting, labelled, lower organization of AI-taught material.
- **Recommendation.** Proceed. The measure is designed to show this early.

### 6.7 Tradeoff: what Windows first costs

*Decision only through DQ-5(a).*
- **What it costs.**
  - About +9 to +15 builder-weeks for platforms, plus 1.5–2.5 for structure evolution and about 7 for personal relevance (±50%; about 2 in Stage 0b, 5 in Stage 1): a total of about 47–66 builder-weeks, or 42–58 without the observer (was 29–41).
  - Weaker caller identity on Windows.
  - Northstar's own store encryption on Windows Home without BitLocker or Device Encryption.
  - Spikes and calibration per OS.
  - No independent verifier unless a machine meets the floor.
- **Recommendation.** For the Windows stage (DQ-5(a)), a personal Windows machine with BitLocker or Device Encryption on; ideally a desktop with a large-memory GPU, which could later be the always-on core and the verifier node.

### 6.8 Defaults and optional extras (DQ-17, DQ-18)

*Block nothing; answer only to override.*
- **Book defaults (DQ-17).**
  - "Teach me X in depth" counts as something you want to explore; a bare "What is X?" does not.
  - A "Looked up" list in the back matter.
  - A set-aside topic that comes back gets one "came up again" line with Restore.
  - One subsection level.
  - A principle across branches gets an overview page, and the related pages stay put.
  - Structural changes get one line on the first screen and a "Put it back" note on each affected page.
  - Weekly editions after the first 14 days.
- **Extras (DQ-18).**
  - Claude Desktop chat on your own API key as an opt-in focus surface (hooks run there; API billing; history only on that computer). Default: not offered.
  - Which other AI tools you use weekly. Each with hooks costs 300–700 lines.
  - Android: default iOS only, Android-ready.
- **Recommendation.** Keep the defaults. Spike the API-key mode on synthetic data before offering it. Tell us which tools you use weekly.

### 6.9 When a reply contradicts your view without acknowledging it (DQ-19)

*Touches the goal (GOAL §3.3 in-session focus against GOAL §5 sycophancy). Needed before Stage 1.*
- **The tension.** Correcting such a reply keeps the chat on what you established; it also pushes the AI toward your view. A reply that engages your view and disagrees with reasons is never drift, in any option.
- **Scope.** Positions you hold on an issue: a claim, belief or insight you stated, or an AI claim you accepted. Goals, constraints, decisions, rejected options and accepted AI explanations outside an issue keep their existing guards.
- **Options.** (a) High, as for any accepted item (the default until you answer); (b) medium, a correction in the next delivery that asks for acknowledgement, not agreement; (c) a card only.
- **Recommendation.** (b).

### 6.10 Stated limit: Northstar cannot state a principle that nobody stated

*No decision now.*
- **The limit.** Related branches can merge, and a broader overview can show what they share, sentence by sentence with citations. But a general claim of Northstar's own would be an invented theme, so a cross-branch overview states one only when you or an AI stated it, in a chat that had not received Northstar's text on the topic.
- **What you would see.** "In 4.2.3, 3.2.2 and 5.1.6, derived state is rebuilt from its inputs", until someone says "derived state is disposable"; then the overview can say it, quoting the source.
- **Recommendation.** Accept the limit; it is what keeps overviews from summarizing summaries (GOAL §5).

---

## 7. Where the five documents disagreed, and how we resolved it

These resolutions are also recorded as R17–R25 in ARCHITECTURE §12.2.

| # | Disagreement | Resolution | Reason |
|---|---|---|---|
| R17 | **Core location for phones.** [PF] recommends an always-on machine you own plus a narrow public endpoint (PQ-1, PQ-2). [CN] recommends a small hosted core early (CN-Q1 (b)). | One decision, DQ-13, with [PF]'s options and recommendation; a rented VM only with your yes. CN-Q4 follows: the `.mcpb` in the Windows stage, the remote connector once the endpoint exists. | [PF] is the deeper analysis and keeps data on hardware you own, closest to "local now". [CN]'s option (b) itself defers to [PF] for encryption and scoping. |
| R18 | **Observer on Windows.** [CN] says build the UI Automation backend first if you consent. [PF] says do not build it in the Windows stage; decide after the Windows chat spikes (PQ-4). | Consent is part of DQ-1 for both OSes. If you say yes, Stage 4 builds it after the Windows chat-app spikes (SP-PF-14, CN-S3) and Stages 2–3 show where it is needed, Windows backend first. | Both hold: [PF] on timing, [CN] on order. |
| R19 | **Edge transport.** [CN] left it to [PF]. | Named pipe on Windows, with loopback TCP plus a credential as fallback; Unix socket on Mac. | [PF] chose it; Node speaks named pipes natively (W20). |
| R20 | **Spike IDs.** The same tests appear under two names. | CN-S5 = SP-PF-7 (ChatGPT on iOS); CN-S6 = SP-PF-9 (phone-driven coding hooks); CN-S4 runs inside SP-PF-14 (Windows) and SP-PF-8 (iOS). ARCHITECTURE cites the SP-PF IDs. | One test, one record. |
| R21 | **Your sessions.** [PR] proposed about 15 and 20 minutes. [KO] proposed a 5-minute add-on and its own baseline task. [BM] proposed two one-hour sessions. | [BM]'s sessions carry [PR]'s and [KO]'s modules, re-budgeted at worst-case task caps, with at least 15 seconds per relevance label. The format is your choice (DQ-14(e)): four sittings of about 30 minutes, two of about an hour, or a short format of about 1 hour with weaker verdicts. [KO]'s "where does your thinking stand" task is [BM]'s T2; [PR]'s no-Northstar probe is K6. | One session plan, about 2 hours of your time in the full formats; we do not assume an hour counts as short. |
| R22 | **Effort totals.** | [PF]'s +9 to +15 builder-weeks already includes [CN]'s 1–2 for the Windows edge. [KO]'s 1.5–2.5 is added to Stage 1. A second observer backend adds 3–4 ([CN]), only if you consent on both OSes. [PR] is now sized at about 7 builder-weeks (±50%; about 2 in Stage 0b, 5 in Stage 1; [PR] §8) and included. Benchmark hours sit outside the stages. | No double counting; the totals are complete. |
| R23 | **When Phase N runs.** [BM] §3 says per connector as each is ready; its Supersedes says Stage 5 opens with Phase N. | Phase N runs per connector once it is ready on Windows. The v0 report closes in Stage 5. iOS and Mac cells are v0.1. | It keeps the early connectors from waiting on the late ones. |
| R24 | **DQ-5(a) and PQ-1.** [PF] merges DQ-5(a)'s location question into PQ-1. | DQ-5(a) keeps the Windows-stage location, because it blocks real data now. DQ-13 decides the location once phones join. | Different stages; one blocks now. |
| R25 | **28 new questions, plus Q-PR-6 and BQ-10 from the check.** | Merged into DQ-13 to DQ-19 and DQ-1's extension (§6); Q-PR-6 is DQ-19, BQ-10 is DQ-14(e). Presentation-only choices become defaults in DQ-17. | The approver's path stays about 30 minutes. |

**Notes, not for decision.**
- [KO] and [PR] share one interface (roles, anchors, `reasoning_thread`). Where both replace the same TEXTBOOK section (§4.7, §6), [PR]'s text stands and [KO] adds only its nesting and structure rules. They should be reviewed together. The core-data-model owner should confirm that the new operations `MINT_NARROWER` and `MINT_BROADER` map to existing event types.
- After the check fixes, all five revision documents run about 5–14 KB over the ~40 KB target. We left them rather than cut content.

---

## 8. Older spec sections now superseded

No spec has been edited. Until the specs are updated after approval, the revision document named here wins. Details are in each document's "Supersedes" section. ARCHITECTURE.md itself is revised in place.

| Spec | Sections | What changes | Source |
|---|---|---|---|
| [foundations/SPINE.md](../foundations/SPINE.md) | §4.2, §4.8, §4.10 | Levels gain a `platform` attribute; Gemini CLI, Cursor and VS Code become hook-map candidates; rows per OS and for phones | [CN] |
| | §5.2 | Agenda gains `question_kind`, interest and issue; new relation `responds_to`; engagement becomes `user_act`; projections `relevance_facts` and `reasoning_thread`. Supersession direction and the current item follow `Message.occurred_at` from a handshake-corrected edge clock, never arrival | [PR], [PF] |
| | §7.1–§7.5, §7.7; Appendix B P26 | launchd and Unix sockets become macOS adapters of OS ports; phones need an internet-reachable endpoint; the forwarder becomes `northstar-edge` in the Windows stage; "local now" restated pending DQ-13; hardware target per platform | [PF] |
| [foundations/TEXTBOOK.md](../foundations/TEXTBOOK.md) | §4.1, §4.3, §4.4, §4.5 | Subsections and overview pages; issue pages; "Why it's here"; needed terms and open objections in block 9; thread anchors; no chapter without a personal anchor; glossary becomes "Terms in your book" and "Looked up" | [KO], [PR] |
| | §4.7 | Replaced by [PR] §4.1 (the relevance gate; teaching decides page form only), plus [KO]'s nesting rule | [PR], [KO] |
| | §6.1–§6.4 | Gaps, `frontier_anchors`, interests instead of "possible directions", the next-step score and reason codes | [PR] |
| | §7.2, §7.3, §7.5, §7.9 | Placement by [KO] §3; background excluded from clustering; hub damping; overlap merge; page → chapter; hysteresis and dwell; spin-off told apart from meaning split | [KO] |
| | §5.9, §8.3, §8.11 (B5, B7, new B17, B18), §8.12, §9.1 | Sub-topic-first sections; one stratified `overview_leaves`; parent pages, chapters and parts keep §4.5's sentence rule, and only cross-branch overviews need an eligible general-claim leaf; context receipts also gate that eligibility; new invariants and sentinels; four new corrections | [KO] |
| | §10, §10.4–§10.6, §11, §12.1 | Reader on every device; the new first screen; term links and back matter; no model-judged relevance; `user_act` and the new records | [PF], [PR] |
| | §13.1–§13.5 | Growth and relevance scenarios; group B parity re-based on relevant material; new group R; arms S0–S5; two one-off evaluation sessions instead of "no user sessions"; §13.5 folded into session 2 | [KO], [PR], [BM] |
| [foundations/desktop-observer-macos.md](../foundations/desktop-observer-macos.md) | Scope, §4.1 | One observer core with OS backends; this document becomes the Mac backend's spec; Windows first if consented (R18) | [CN], [PF] |
| [components/core-data-model.md](../components/core-data-model.md) | §2.2 rows 21–22; §6 `index.db`; §10.4 | Event mapping for `MINT_NARROWER` and `MINT_BROADER`; `subthread_facts`, `user_act`, `relevance_facts`, `reasoning_thread`; Time Machine becomes the macOS case of `BackupGuard` | [KO], [PR], [PF] |
| [components/maintainer.md](../components/maintainer.md) | §3.7, §4.2–§4.6, §6.4, §7.2, §8 | New high-tier operations; J3 emits `question_kind` and `generalization`; J5 proposes `responds_to`; new J5i; J8c before every edition; relevance coverage audit; per-platform verifier node; new sentinels; four new faults (over-split, over-generalize and role flip from [KO]; late spool inversion from [PF]) | [KO], [PR], [PF] |
| [components/ai-in-session.md](../components/ai-in-session.md) | §6.5, §8.1, §11 | A reasoned disagreement that engages your view is not drift; the severity for contradicting it without acknowledgement follows DQ-19 (until you answer, high, unchanged); the omitted-counter-evidence verdict; relevance in the card and pin tie-breaks; metrics feed v1 | [PR], [BM] |
| [components/ai-continuity.md](../components/ai-continuity.md) | §3.1–§3.3, §3.6, §11 | Positions slot, `rel` in the score, CK-11, knowledge eligibility, "never in a pack" additions; bars become v1 targets | [PR], [BM] |
| [components/connectors-desktop-and-mcp.md](../components/connectors-desktop-and-mcp.md) | §2, §3.4, §4.1, §5.1, §6.1, §7.1, §8, D8 | Hook-tier `northstar_fetch` and `northstar_book` limited to the session's project scope and delivered items, with a read budget; `.mcpb` for `win32`; restart link per OS; the remote connector as a normal channel; joins by turn tag; peer check per OS; install steps and level rows per OS and for phones | [CN], [PF] |
| [components/connectors-claude-code-and-codex.md](../components/connectors-claude-code-and-codex.md) | §0, §1, §3, §4.3, §13 (D-HK-5), §14.3 | Hook tier on Windows and Mac; a compiled launcher per OS; Codex `commandWindows`; Remote Control and connected-PC Codex tasks; the hook-tier tool read scope and budget | [CN], [PF] |
| [components/platform-security-privacy.md](../components/platform-security-privacy.md) | §0, §1 B1, §2.1–§2.10, §3, §4.1–§4.2, §7 RT-17, D-PL-2 | Becomes the macOS adapter of OS ports, with Windows and Linux added; passkey step-up; the relay replaced by the iOS-stage endpoint; OAuth, an HTTPS Reader and the forwarder arrive earlier; RT-17 adds bulk reads through the tools; the public endpoint gets its own hostname, passkey RP ID and no Reader cookies, plus a source-IP allowlist where the tunnel allows | [PF] |
| [components/evaluation-and-build-plan.md](../components/evaluation-and-build-plan.md) | §0 items 1–4, §1.1, §1.4–§1.6, §2.1–§2.3, §3.2, §3.3, §3.5, §4, §5.1, §5.2, §5.4, §6 | v0 is the first evaluation; one pre-registration; v0 statistics; Phase B before the build; bench install; stages reordered by platform with per-OS and cross-device cells; relevance and structure measures; costs | [BM], [PF], [PR] |

---

## 9. Check fixes (2026-10-09)

An internal check of this revision found 17 major and 16 minor issues, and no blockers. All are fixed in ARCHITECTURE.md and the revision documents. None changes the WHAT: the one that touches it is put to you as DQ-19 (§6.9), and one limit is stated rather than hidden (§6.10).

**Personal relevance** ([PR]; ARCHITECTURE §4.1–§4.2; [KO] §7.4)
- A term you only name in passing is no longer an act. A weak act needs the topic to be the subject of your turn; terms used across many conversations (hubs) need a strong act; a prerequisite of many anchored topics that you never engaged with is generic. [KO]'s Example G names the rules that keep "LLM" in the background.
- Needed terms and prerequisite gaps need an act of yours: you asked, followed up an answer that turned on it, or said you did not follow it.
- One rule for AI suggestions you did not take up: shown only on an active anchor's path, labelled "not taken up", ranked below your items, never a gap.
- Lookups are defined by relevance, not form ("what", "how" or "why"); lookup recall is reported.
- New planted cases: a generic hub, a generic prerequisite (hard bar: 0 gaps, 0 sections), a generic how-or-why question, an untaken AI suggestion.
- "Linked" versus "context" is defined in code; leaf and pack parity sentinels watch the context cap and the pack's knowledge slot; the silent-reliance detector accepts any number of earlier AI explanations; RISK PR-2 and §6.6 cover all three gates.
- How severely to treat a reply that contradicts your view without acknowledging it is now your decision, DQ-19, with its scope stated; it left "settled as HOW" and gained a risk row (ARCHITECTURE §13 row 19).
- [PR]'s build work is sized: about 7 builder-weeks (±50%), now in the totals (47–66).

**Knowledge organization** ([KO])
- Northstar's own delivered text cannot return as evidence for an overview: an AI's general claim counts only from a chat that received no Northstar text on the topic (planted case G-ECHO-THEME, bar 0).
- Only cross-branch overviews need a stated general claim; chapter, part and parent-page big pictures keep TEXTBOOK §4.5. The limit is stated in §3, §6.10 and ARCHITECTURE §13 row 17.
- Similarity may choose a section only inside a page that other signals chose.
- A chapter's exit bar sits above its formation overlap, so it cannot merge straight back (oscillation bar: 0 in 12 editions).
- The two deliberate asymmetries (acts come from your turns; explicit references count AI text only with a delivery receipt) are stated in ARCHITECTURE §3 and [KO] §7.3, and structural parity checks them.

**Connectors and devices** ([CN], [PF]; ARCHITECTURE §0, §0.1, §3, §7, §9)
- MCP's continuity is restated as good only if the model calls Northstar before its first reply; a first-call gate (K0, ≥ 90%) is pre-registered per connector.
- Arm M compares MCP only with hooks on Claude Code and Codex; the effectiveness claim in §2 and [CN] §8 now says what is measured and what is not.
- ChatGPT chats typed on the phone but running on a connected computer may use that computer's local server (verified; for Northstar, spike SP-PF-17). DQ-13's premise is restated.
- Order across devices follows when words were said: a late spool cannot undo a newer view (new fault and Stage I gate).
- The remote connector bypasses the edge: device controls do not reach it; it is scoped by account and revoked per vendor; Claude Desktop chat moves to it only as an opt-in per device.
- The security claim is narrowed: hook-tier tools read only the session's project scope and delivered items, within a budget (RT-17).
- The public endpoint gets its own hostname and passkey RP ID, and an IP allowlist where the tunnel allows.

**Benchmark v0** ([BM]; ARCHITECTURE §0, §10, §11, DQ-14)
- On view items, a reasoned disagreement passes. The AI's strongest objection is elicited, and F6 guards against agreement sycophancy on your real topics. F1 scores the first reply; the hook correction is reported separately (F1c). Item IDs and correction phrases are masked, with an unblinding check.
- Sessions: three formats, budgeted at worst-case caps with at least 15 seconds a label. We ask whether an hour counts as short.
- AI-taught material on your real data: a session-1 prompt, U7's AI-taught split and U10.
- Your topics are split at random into script and task topics, so typing scripts cannot rehearse the tasks.
- The late baseline is full-size by default and budgeted; K6 runs twice in session 2; the wait follows a measured vendor-memory latency.
- U6's comparison with other rules is secondary at v0's label counts.
- Cost is stated for the case where you build; Phase B's gates are listed exactly, including bench-folder encryption that needs no Northstar code; DQ-14(c) is marked as changing GOAL §7's order for evaluation only.
