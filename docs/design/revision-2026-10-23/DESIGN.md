# Northstar: the revised design

**Status:** proposal, version 3.2, written 2026-10-25. Nothing is built. [GOAL.md](../../GOAL.md) overrides this document.
- **Round 1, 2026-10-24.** You approved version 1 with changes: an architecture for the AI and for you, something like OpenAI's "dreaming", a focus that brings its own intelligence, research behind every part, and this Mac first.
- **Round 2, 2026-10-24.** You confirmed the new focus, approved going ahead, and asked that Northstar run on the AI you already use, and that "dreaming" mean ChatGPT's Dreaming memory system, not sleep.
- **Round 3, 2026-10-25** (GOAL §1, §2). You explained that ChatGPT's Dreaming was a reference, not something to copy literally: Northstar has memory structures for the AI and for you, helps with focus and memory, and "still works with existing AI like ChatGPT and Claude, it is not on its own". You also:
  - left the route to the AI to us;
  - allowed Claude and ChatGPT to check each other;
  - chose your website work plus chats you add for the sketches;
  - are not sure yet about the phone.
- **This version** leads with that positioning and keeps ChatGPT's system as the reference (§1.5). It calls the background process **maintenance**, your word for job 3, decides the route (§1.4), and turns on cross-vendor checks. It still revises the 2026-10-09 design ([ARCHITECTURE.md](../ARCHITECTURE.md)) and keeps its connector, platform and maintainer work (§12).

**Review page:** [`review.html`](review.html), published as a private page; the link is in [EXPLORATION.md](../../EXPLORATION.md).

**Reviews:** each version had a goal-fidelity pass and an adversarial review by a different model (Sonnet 5.5). Version 3's review found 4 blocking issues, all fixed in 3.1: unproven separations, an unasked reversal of the API default, a ChatGPT comparison that implied unpublished internals, and a wrong statement about your marks. Version 3.2 records your round-3 answers.

**Evidence tags:**
- **E2, E3** = [EXPLORATION.md](../../EXPLORATION.md) §2 (the probes) and §3 (the sketch rounds).
- **Notes 01–25** are in [`docs/research/`](../../research/); the newest are [25](../../research/round6/25-overview-display.md) (how to show your overview), [23](../../research/round5/23-memory-architecture-and-dreaming.md) (memory architectures and dreaming), [24](../../research/round5/24-focus-intelligence-evidence.md) (focus through the AI), [21](../../research/round5/21-focus-prior-art.md) and [22](../../research/round5/22-surface-facts.md).
- The 2026-10-09 documents reused here: [CN] connectors, [PF] platforms, [KO] knowledge organization, [PR] relevance, [BM] benchmark ([`revision-2026-10-09/`](../revision-2026-10-09/)); [MT] maintainer, [HK] hook connectors, [CX] desktop and MCP, [IS] in-session, [AC] continuity, [CDM] data model, [PL] platform and privacy ([`components/`](../components/)); [SPINE] ([`foundations/SPINE.md`](../foundations/SPINE.md)); [TB] the textbook ([`foundations/TEXTBOOK.md`](../foundations/TEXTBOOK.md)).
- §14 maps each part to its research.

---

## 0. On one page

**What Northstar is.** A memory and focus layer for the AI you already use.
- **Like ChatGPT's Dreaming memory system,** it gives your AI memory that builds up in the background (§1.5).
- **Unlike it,** it does three more things:
  - it works across all your AIs (Claude, ChatGPT, Codex or any harness);
  - it keeps memory structures for the AI and for you;
  - it helps you stay focused in long sessions.
- **It is not an AI of its own.** Every judgment is made by your own AI's models, in your conversation or as hidden sub-tasks through the vendors' APIs (§1.4). Northstar's code keeps the memory and checks it.
- **It embraces the world-class AIs you use** instead of competing with them, which you noted is better commercially (GOAL §2, 2026-10-25). The first version stays personal (GOAL §4.6), and nothing in the design blocks a commercial one.

The three jobs (GOAL §1, 2026-10-15):
1. **Focus, a side job.** At a few moments in a long session, your AI works out what the goal still needs and whether the work got worse. It answers you first, then offers the step in at most two sentences, and acts only on your yes (§3).
2. **Memory, add context.** New chats get the facts they lack, as plain context; often nothing (§4). Your overview opens when you ask (§6).
3. **Maintenance, behind the scenes.** Capture, then the maintenance run: a background process that builds your memory structures, keeps them current, checks them and logs every change (§1.2, §5).

```mermaid
flowchart LR
  APPS["Your AI apps<br/>Claude, ChatGPT, Codex, any harness"] -- "your chats<br/>both sides where the app allows" --> HIST[("Chat history<br/>kept word for word")]
  HIST --> MAINT{{"Maintenance<br/>in the background"}}
  MAINT --> MEM["Memory: your knowledge<br/>separate items, each citing its source"]
  MEM -- "for the AI: what new chats start from" --> APPS
  MEM --> OV["For you: your overview<br/>a map of your ideas and your work"]
  APPS --> FOC["Focus<br/>during long sessions"]
  FOC -- "a short note for one reply" --> APPS
```

**What changed in round 3:**
- **The positioning comes first.** Northstar is a layer over your AIs, as ChatGPT's Dreaming is inside ChatGPT. The component-by-component comparison is now the reference (§1.5), not the frame.
- **The background process is called maintenance.** That is your word for job 3; "Dreaming" is OpenAI's name, and you didn't mean it literally.
- **Hidden sub-tasks go through the vendors' APIs** (§1.4): you left the route to us, and it is the route a product can build on.
- **Claude and ChatGPT check each other's work,** as you allowed.

**Next:** the overview sketch round on your website work plus a few chats you add (§6). Then the Claude Code prototype on this Mac.

---

## 1. The memory system

### 1.1 What sits underneath

| Store | Holds | Written |
|---|---|---|
| **Chat history** | Every captured turn, both sides where the app allows, and every work event, word for word, dated and attributed. Never edited | At once, by capture |
| **Memory items** | Your ideas and the AI ideas you adopted, one clear line each, with why, scope, origin, links and the chat turns they came from. Goals and open questions | Only by maintenance, through one write gate |
| **Working memory** | For each piece of work in progress: the goal, decisions, ruled-out options, versions with your feedback, the best version you picked, open side topics | Live: code records versions and your feedback; a small model notes decisions in your own turns |
| **Working style** | A few lines on how you like AIs to work with you, kept where learned | Only by maintenance. Reaches the AI only when it asks (§1.3) |
| **Your work** | Pointers to anything you got your hands on, with a small snapshot | Capture, then maintenance |
| **For the AI: the AI index** | One plain dated line per memory item, with scope and links, plus a search index; a start note for each piece of work in progress | Rebuilt by maintenance |
| **For you: the human structure** | Topics in your words; which ideas sit in each; connect and conflict links; open items; your work under each idea; your pins, corrections and "seen" marks; a stable layout | Rebuilt by maintenance; topics split and merge weekly |

The last two rows are the two memory structures you asked for (GOAL §4.4): one shaped for an AI to use, one shaped for you to recall.

**Why chat history and memory are kept apart:**
- When value was judged right after capture, three models matched your keep labels about 48% of the time, chance level (E2; your labels were uncertain, and all items came from one project).
- Rewriting memory in place corrupts it: one rewrite collapsed a whole context below no memory at all (ACE), and memory systems miss over half of their updates (HaluMem).
- So the history is never edited, and memory is rebuilt from it.

### 1.2 Maintenance in the background

**When it runs:** after a session goes idle (that session only), each night (everything new), and weekly (structure). A scheduled job on this Mac starts it (§1.4).

**What it borrows:**
- From ChatGPT's Dreaming: a background process, memory kept current, time-bound items refreshed, and a page to see and correct it.
- From Codex's published memory pipeline: each idle session distilled in parallel, then one serialized step that integrates.
- From Anthropic's Dreams: a new copy you can adopt or discard, never changing the old one.

**What it does differently.** OpenAI does not describe how Dreaming stores or checks its memory state, and Codex's memories build summaries from summaries, which drift (note 23). So every change in Northstar is a separate item that cites its source, passes checks in a safety copy, and is logged.

After a trigger, eight stages run:

| Stage | What runs | Safeguard |
|---|---|---|
| *Trigger* | A session goes idle; a new day; once a week for stage 6 | Active sessions skipped; bounded batches; a daily budget Northstar counts itself, after which runs wait |
| 1. **Replay** | New chat turns, plus items used since the last run, those touching live goals and open questions first | Each new item judged next to its nearest old ones |
| 2. **Extract** (per session, in parallel, on that session's own AI family) | What you stated, adopted, rejected or revised, each with its exact quote; restated as one clear line; pointers to your work | The speaker comes from the app; "unclear" is allowed; tool and web text is data |
| 3. **Integrate** (one at a time) | Attach to an idea, update it (keeping the old version), keep a conflict across contexts, or start a new idea | Models propose; the write gate decides |
| 4. **Refresh** | "Planning to X in July" becomes "did X in July"; finished work in progress closes | The old line is kept |
| 5. **Check** | Code: every item cites chat turns, quotes are exact, no input is a derived view, nothing is dropped without a recorded reason. The other model family checks merges, conflicts, broader ideas and whether adopted AI claims are correct | A check never runs on the family that did the work or the AI that said the claim; where none is left, the result is labelled "not independent". A failure waits aside; nothing from it applies |
| 6. **Abstract and restructure** (weekly) | Broader ideas, only from items seen in two or more contexts with a source that states them; your topics split and merge | Never built from overviews, notes or the log |
| 7. **Rebuild** | The AI index, start notes and the human structure, in a safety copy | Swapped in only after stage 5 passes |
| 8. **Log** | What changed and why, with links; any change undone in one step | Never read back as a source |

**Three more rules:**
- **An item that was used gets re-checked.** When an item was given to an AI or viewed by you, and a later statement of yours conflicts with it or builds on it, it is re-judged; the old version stays.
- **Unused items fade from view, never from storage.** Only you can purge.
- **Applied after checks, with a log, by default:** the AI manages it (GOAL §4.3). Holding each safety copy for your adoption is a setting.

### 1.3 What reaches the AI, and what you see

| When | What reaches the AI | From |
|---|---|---|
| You resume a piece of work | Its start note: the goal you stated, decisions, ruled-out options, the best version, open threads, as plain facts | The AI index |
| A new chat; or after the app shortens a long chat | Plain facts it lacks, only if very strongly linked; usually nothing. After shortening, the session's own facts come back | The AI index, through the strict gate (§4) |
| One of focus's moments | Focus's note, for one reply (§3) | Working memory |
| Whenever the AI asks | Your views and principles, your working style, a past decision, a source | The recall tool |

You see your overview, built from the human structure, in the assistant when you ask (§6).

### 1.4 Where the thinking runs: on the AI you already use

You asked that Northstar run on the AI you use (Claude, ChatGPT, or any harness), generalized rather than separate, unless it has to be separate (GOAL §2, round 2), and that it work with existing AI, not on its own (round 3).

**The rule.** Northstar has no AI of its own to talk to, sign in to or manage. Its code holds the memory: storage, the write gate, schedules, a search index and the checks. Every judgment is made by your own AI, the same model families as the apps you use, in one of two ways:
- **In your conversation:** your assistant itself. It reads Northstar's notes, calls its recall tool, and does focus's thinking in its own reply.
- **As a hidden sub-task:** Northstar's code asks the same model family in the background, with a fresh context and a lean prompt. Claude handles work from Claude's apps, and ChatGPT's models handle work from ChatGPT and Codex. Any harness with an API or SDK plugs in the same way. You never see these runs, and they are never captured as your sessions.

**The route, decided** (you left it to us, 2026-10-25): hidden sub-tasks go through the vendors' APIs, on the same model families as your apps.
- **It is the route a product can build on.** Anthropic does not allow third-party products to use claude.ai logins or plan limits unless approved ([SPINE] P8), and OpenAI calls API keys "the right default for automation" (P11).
- **It leaves your chat allowance alone.** You have hit your weekly limit before.
- **It lasts.** The scripting route through your plan's command-line tool may close, because the mode Anthropic documents for scripts never reads plan logins and "will become the default for `-p`" (P7).
- **For you now:** your own Anthropic and OpenAI API keys. Your plan's monthly API credits may cover the Claude part, if it includes them (Max and Team do, P9; spike SP-5 checks). A commercial version would decide its own billing later.

| Job | How it runs | On which AI |
|---|---|---|
| **Focus's thinking at a moment** | Your assistant, in its own reply, from a note Northstar prepares ahead (§3.3) | The assistant you are talking to |
| **Focus's blind version check** | A hidden sub-task, prepared ahead: during the nightly run for a new-day moment, right after the turn that crossed half the window otherwise. Its result goes into the note | The same family as your assistant, in a fresh context |
| **Keeping working memory current:** decisions and ruled-out options in your turns | A hidden sub-task on a small model, in the background after each of your turns | The same family as your assistant |
| **Memory's selection in a new chat** | Code ranks candidates locally; a small model keeps only very strong links, within the 3-second budget for your first message ([HK] §4.3). If it would take longer, code alone decides with a stricter bar. The first reply of a new chat can wait up to about 3 seconds | The same family as your assistant |
| **What your assistant asks for:** your views, a past decision, a source | Your assistant calls Northstar's recall tool | Your assistant itself |
| **Maintenance** | Hidden sub-tasks, started by a scheduled job after idle sessions and nightly | Each session's own AI family: Claude for Claude's apps, ChatGPT's models for ChatGPT and Codex |
| **Maintenance checks** | Hidden sub-tasks | The other family, as you allowed |
| **Search** | A small embedding model on this Mac. It finds candidates and judges nothing | Not an AI call |

The chat apps have no hooks, so there focus works only when you ask: your assistant calls Northstar's tool and does the thinking itself.

**Where it still runs apart, and why** (you asked us to say):
1. **Focus's blind version check, in a fresh context of the same AI.**
   - Blindness cannot be had inside the conversation that holds the versions, their order and your praise. Judges favour versions labelled "new" ("The Silent Judge", 2025) and the version users like (Sharma et al. 2023). Models showed an average 64.5% "blind spot": they failed to correct their own errors, yet corrected the same errors presented as coming from elsewhere (Tsui, NeurIPS 2025).
   - §8 still compares it with your assistant checking in its own reply. If that agrees with you as often, the simpler one is used.
   - The rest of focus's thinking runs in your assistant's reply. A hidden sub-task would replace it only if §8 shows it does better on your sessions.
2. **Maintenance checks, by the other model family.**
   - Models' errors overlap, more so between similar models, and judges favour models like themselves (Goel et al., ICML 2025; Panickssery et al. 2024).
   - So a check never runs on the family that did the work or the AI that said the claim (kept from [SPINE] §8.3). Extracting each session with its own AI's family and checking with the other keeps both apart.
   - It sends excerpts of your Claude chats to OpenAI, and of your ChatGPT chats to Anthropic; you allowed this on 2026-10-25. Only the excerpts a check needs are sent.
3. **A trigger for maintenance when no chat is open.** A scheduled job starts the work; it is not an AI. It is Claude's own scheduled tasks, which run while the Claude app is open or on its next launch, or the Mac's scheduler, which runs even when the app is closed.
4. **A small search model on this Mac.** It turns text into numbers so related items can be found; it writes nothing and judges nothing. Keyword search alone needs no model but misses items said in other words. That is a setting.

**What it costs:** about $25–85 a month at 20–100 turns a day (±2×), mostly maintenance.
- The 2026-10-09 cost model gives about $25 at 20 turns a day and $74 at 100 for the same pipeline ([MT] §9.6, at its listed prices and assumptions). Cross-family checks and focus's blind checks add a few dollars.
- Your plan's API credits may cover part of it (SP-5).
- Our first estimate of $20–40 left out parts of that model.

### 1.5 The reference: ChatGPT's Dreaming memory system

You pointed to ChatGPT's Dreaming memory system as what Northstar is like "in a sense": memory that builds up in the background and works inside an AI you already use. Here is what OpenAI publishes, and how Northstar relates.

**What OpenAI publishes.** These points come from OpenAI's Dreaming post ([openai.com/index/chatgpt-memory-dreaming](https://openai.com/index/chatgpt-memory-dreaming)) and memory help page ([help.openai.com/en/articles/8590148-memory-faq](https://help.openai.com/en/articles/8590148-memory-faq)), both read on 2026-10-24; note 23 §1 summarizes the same sources.
- **Saved memories:** details you ask ChatGPT to remember, or that it saves on its own where available. They are written "during the conversation" and can go stale. They are separate notes, stored apart from chats, so deleting a chat does not delete them.
- **Reference chat history:** ChatGPT uses relevant information from past conversations. What it keeps "can change as ChatGPT updates what is most useful to remember".
- **Dreaming:** a "background process" that learns from many conversations and synthesizes ChatGPT's "memory state", which supplements saved memories.
  - It began in April 2025 as V0; V3 has rolled out since 4 June 2026.
  - Memories are "automatically updated as time passes": a planned trip to Singapore in July becomes a trip that happened in July 2026.
- **What new chats get:** they "start from shared context rather than from scratch". OpenAI does not say what is loaded or how it is chosen.
- **Memory summary:** a high-level page of what ChatGPT knows, which "does not necessarily include every detail or source". You can correct it, choose "Don't mention this again", say which topics to bring up and when, or turn memory off.
- **Sources:** shown under some replies, so you can open, correct or delete what a reply drew on.
- **Project-only memory** limits memory to one project. **Temporary chats** "do not create or update memories".
- **Evaluation:** OpenAI's internal tests, read from the post's charts, show three gains between saved memories alone and V3:
  - carrying context forward, from 41.5% to 82.8%;
  - following preferences, from 31.4% to 71.3%;
  - time-sensitive answers, from 9.4% to 75.1%.

  Serving Free users cost about 5× less.
  - Caveats (note 23): the measures are not defined, the year labels are our reading of inconsistent chart titles, and nothing can be reproduced.
  - There is no paper, and nothing on storage, selection, schedule, checks or undo.

**How Northstar relates:**

| ChatGPT | Northstar | What is different |
|---|---|---|
| **Chat history**, referenced when relevant | **Chat history**, kept word for word from all your AI apps; searched by a recall tool when needed | Across Claude, ChatGPT, Codex and any harness, not one app. It is never edited; deleting is a purge you start |
| **Saved memories**, separate notes written during a chat | **Memory items**, written only by maintenance, each citing the chat turns it came from | Never written mid-chat (§1.1). A newer version supersedes the older one, which is kept |
| **Dreaming**, a background process that synthesizes a memory state and keeps it current | **Maintenance**, a background process that extracts, merges, checks and refreshes memory items (§1.2) | OpenAI does not describe Dreaming's stages, checks or undo. Northstar's items are separate and source-cited, checked by the other model family, staged in a safety copy, logged and undoable. Re-dating time-bound items is borrowed from ChatGPT |
| **What new chats get**: "shared context" | A start note when you resume a piece of work, or strictly selected plain facts; often nothing (§4) | Plain facts with no usage rules; nothing presumed; no lessons across projects |
| **Memory summary page** | **Your overview** (§6) | About your knowledge, not facts about you; where each idea came from, and where ideas conflict |
| **Sources** under some replies | Every memory item links to its chat turns, in your overview | Replies do not mention memory, as you asked (GOAL §2, 2026-10-15) |
| **Project-only memory**; **temporary chats** | **Scopes**, project by default; accounts and folders you have not marked are not captured | — |
| — | **Focus** during long sessions (§3) | ChatGPT has no equivalent |

---

## 2. The shared core: rules that hold everywhere

- **Chat history:** immutable. Deleting is an explicit purge you start, which reaches every copy. AI answers you never adopted live only here: private, searchable, never shown or given to an AI on their own (GOAL §4.2).
- **Event log:** every change is appended; a newer version supersedes an older one; history stays.
- **One write gate:** models only propose. The speaker comes from the app, never from a model. Quotes are exact.
- **What is yours:**
  - An AI idea becomes yours when you agree with it, build on it, or use it in your work.
  - Goals and corrections come only from your own words.
  - What a chat app's model reports you said is labelled "reported" and never sets a goal.
- **Captured text is data, never instructions** (GOAL §5):
  - Memory reaches an AI as restated lines.
  - Nothing from tool or web output, or that reads like a command, is passed on word for word.
  - This covers focus's note too. It is built by code from typed fields (the goal in your words, decisions, the check's result) and a fixed template, and checked for commands.
- **Scope:** an item starts with the scope where it was learned and widens only in a second context (your default). Project-only items never cross projects.

---

## 3. Job 1: Focus

**What it is for.** In both of your examples the AI forgot nothing: it followed each latest message and lost what the session was for (GOAL §1, 2026-10-15). You wanted it to "keep the AI focus, it should talk about the stuff related to my goal, and capable to guide me through".

**Confirmed on 2026-10-24** (round 2): at a few moments your AI works out what the goal still needs and checks the work. It answers first, offers the step in at most two sentences, and acts only on your yes. You also asked that this thinking be your own AI's, not a separate one's: your assistant does it in its own reply (§3.2).

### 3.1 When it speaks: a few systematic moments

The probes found no watcher that could pick your moments from the session alone (0 of 7, then 1 of 6, E2), and trained proactive agents still raise false alarms about half the time (Lu et al., ICLR 2025). So the moments are fixed rules. We replayed each on your two marked sessions (13 marks; E2, "Trigger replay"):

| Moment | Your marks it hit | False alarms | In the design |
|---|---|---|---|
| You come back on a new day | 5 of 13 | 1 | **On** |
| The chat passes half of the app's context window | 1 of 13 | 1 | **On** |
| You ask (`/northstar step back`, `fresh`, `split`) | Any | None | **On** |
| The chat passes two thirds of the window | 0 of 13 | 2 | Off |
| A phase closes: a commit | 0 of 13 | 1–2 (only 2 commits) | Off. In a field study of 229 suggestions, about half of developers engaged with those shown right after a commit, while 62% of those shown mid-task after a declined edit were dismissed (Kuo et al., IUI 2026). So it stays a setting to test |
| A phase closes: "looks good"-style words | 1 of 13 | 1 | Off |

- **The defaults would have spoken at 6 of your 13 moments, with 2 false alarms.** That is in-sample: the same marks chose the defaults, so expect fewer on new sessions. For the rest, you ask.
- **Phase close** was one of the moments in the option you picked in round 1. Its two signals hit 0 and 1 of your marks, so it is off by default, as in the three moments you confirmed in round 2.
- **How the window is measured:** from the token counts Claude Code writes to its transcript, read when you send your next message, as our replay did. For Codex this is unverified (note 22 B9).
- **These sessions were picked because they drifted,** so none of this is tested on ordinary sessions.
- **Candidate moments, tested on your marks first:** a side topic starting (your early marks), versions that grow without changing much, and repeated vague "improve it" feedback (note 24 §5).

### 3.2 What your AI works out at a moment

Your assistant works this out in its own reply, from a note Northstar prepares ahead with the goal in your words, where things stand, and the blind check's result.
1. **Goal, needs, gap.** For the interview case: "two hours, 14 practice questions on agent design; the interview also needs a timed mock answer and a story from your own build, not yet practised". Tutoring systems hold a learner's goal this way (GenMentor, WWW 2025).
2. **A quality check** (your pick), where versions exist. This is the one part that runs apart: a hidden sub-task of the same AI, because blindness cannot be had inside the conversation (§1.4).
   - It compares the current version with the best one you picked, against a rubric drawn from your goal and your feedback.
   - It runs blind (neutral labels, no dates, no "latest", none of your praise), in both orders, with several screenshots for web work rendered from saved snapshots. On code, tests and the build run first.
   - It reports only if both orders and the absolute scores agree; otherwise "can't tell".
   - It is calibrated on about 10 blind pairs of your own versions before it is switched on. In the website session you never marked "getting worse", and four of its five later marks were about length or clutter; in the Northstar session you marked it once (GOAL §1, 2026-10-16).
   - Judges flip about a third of pairwise calls when the order changes, favour versions labelled "new", and reach about 73% on design taste (note 24 §3).
3. **One suggestion and the move it enables:** step back with a short plan; split off a side topic; or prepare a fresh session with the goal and the best version.
4. **Or nothing,** the default. Replies built on random tutoring decisions were far worse than replies built on an expert's (Bridge, NAACL 2024): a wrong suggestion is costly.

### 3.3 How you hear it: a note for one reply

- **The note:** about 120 words, for one reply only (note 24 §7). It holds the goal in your words, where things stand, the check's result if any, and one instruction: answer the message first; then, only if a step clearly serves the goal, raise it in at most two sentences, as an offer with two options and a plain reason; act only on a yes.
- **It stays in the chat's hidden history.** The apps keep added context there, so the note says it applies to that reply only, and §8 checks that later replies do not keep acting on it.
  - In the study behind this kind of note, the instruction was not kept in the transcript (Leins et al. 2026), so its 87% may not carry over.
  - Users have reported that a standing reminder made Claude's tone drier in long chats (note 24 2.3; unverified reports).
- **This is the one exception to "plain context, no rules"** (GOAL §2, 2026-10-15). It applies only to focus's reply at a moment; memory stays plain facts. It never rewrites an answer, and the added sentences are about the task, not about you or your past: "the last five versions all changed the header", not "you keep tweaking" (Kluger and DeNisi 1996).
- **After your yes, the AI acts:** for example, it starts the mock round with a short rubric, or prepares the fresh session and tells you how to open it. A declined point waits for a new moment with new evidence.
- **Why through the AI:**
  - Tutoring systems split deciding from saying (StratL; Bridge). In one randomized trial, an on-demand assistant that suggested strategies to human tutors raised students' mastery by 4 points (Tutor CoPilot).
  - A one-reply instruction written for the situation cut drift by 87%, against 22–38% for generic reminders, on a simulated persona (Leins et al. 2026).
  - Anthropic steers long chats by appending to the user's turn (note 24 §2).

### 3.4 Also part of focus

- **Decisions check, on by default** (shown in Q6, which you confirmed). When a reply names an option you ruled out, or edits an outdated file, code catches it and the next reply's note carries one line saying so. You can switch it off or send it only to you.
- **Fresh start, in one move.** The seed carries the goal, decisions, ruled-out options, open threads and the best version you pick, never the drifted transcript.
  - Replacing a model's own earlier replies with neutral text raised its later performance (Li et al. 2026).
  - Putting all the information in one prompt kept 95.1% of single-turn performance, against about 61% spread over turns (Laban et al., ICLR 2026).
  - The seed is distilled rather than complete, so its benefit is tested (§8).
- **Firmness:** off; gentle; normal (default); firm.
- **Option (c), judging the moment as well,** stays an experiment, off until it matches your marks.

---

## 4. Job 2: Memory, the read path

**What it is for.** Continuity across chats, products and compaction, without you re-explaining (GOAL §3.3).

**What the probes showed** (confidence as rated in E2):
- You preferred the memory-backed reply in only 2 of 9 pairs; in round 4 the reply with no memory took 3 of 6 top picks.
- Memory won where it supplied facts the model lacked, and lost where it presumed context or carried a lesson across projects.
- Strict selection found 9 of 10 required items and nothing off-topic.

**How it works:**
- **Plain context, no rules.** Nothing about you as a person reaches the AI unasked.
- **Facts, not judgment** (confirmed). Decisions, results, conclusions and what things are go in when strongly linked. Your views, principles and working style go only when the AI asks: you said "the key is to provide memory for the AI agents/LLM, not to alter the behaviours" (GOAL §2, 2026-10-15).
- **Strict and empty by default.** Most replies stay the AI's own fresh answer. Re-explanations you had to make loosen the gate; a presumption or a leak tightens it.
- **When:** start notes when you resume work; strict facts in a new chat; the session's facts after compaction; the recall tool any time.
- **Your apps' own memory stays as it is,** ChatGPT's included. Lasting project knowledge stays in each product's memory and files (your default). Northstar adds what crosses apps, and your knowledge.

---

## 5. Job 3: Maintenance, the write path

**What it is for.** One correct, attributed memory that stays correct when any one model call loses focus (GOAL §3.4, §4.7): capture plus the maintenance run (§1.2).

**What the probes showed** (E2):
- Extraction credited 88–96% of items correctly, and about half of what you hold were AI ideas you adopted.
- Value judged right after capture matched your labels about 48% of the time: chance.
- Scope was written too broadly at capture.

**The jobs, by stage:**
- **Extract:** your moves only; a bare question records nothing; generic facts are not organized unless they support one of your ideas (GOAL §2). Each item is restated as one clear line; a second model checks the meaning both ways.
- **Integrate:** merges and links. Conflicts and cross-context links need two independent checks.
- **Check:** adopted AI claims are marked checked, unchecked or contradicted. Contradicted claims never reach an AI as fact; web checks are off unless you allow them.
- **Value, deferred:** an item starts as forming, and is kept once you come back to it on another day, build on it, use it in your work, see it in a second context, or say so (Go-CLS: Sun et al., Nature Neuroscience 2023; Xiong et al. 2025). Your optional marks move the bar per topic.
- **Structure, both ways** (GOAL §2, 2026-10-09; method kept from [KO]):
  - New material goes where it continues something.
  - A topic splits when it no longer fits one glance and holds a distinct recurring thread. There is no fixed count: the sketch round sets the starting budget, and it adapts to how you use the overview (GOAL §2: dynamic over hard-coded).
  - Topics merge when they say the same thing.

**Robust when one agent loses focus** (kept from [MT]; note 13):
- Code holds the state and the write authority. Workers are stateless and see only what code gives them; their outputs are recorded and replayed.
- Risky changes are checked by the other model family, under the routing rule in §1.2.
- Failures wait aside with automatic exits; error budgets pause a job type that errs; rollback replays compensating events.
- Nothing waits on you.

**Corrections** are optional and one step: "not what I think", "keep", "project only".

---

## 6. The human view: your overview

Northstar's counterpart of ChatGPT's memory summary page, built around your ideas and your work.

**What you told us:**
- Big picture first, grouped by topic, with connect and conflict lines.
- One line per item, and your real work brings it back.
- "Only for revisiting, not for generating new ideas"; the display "requires researchs".
- It lives "in the assistant, when I ask", inside Claude or ChatGPT (GOAL §1, §2).

**Proposed:**
- **Big picture:** a few topics in your words, with connect and conflict lines. What to learn is marked "open": your open questions, conflicts between your ideas, and gaps on your own paths. A term that merely appeared is never a gap.
- **A topic:** its ideas, one line each, marked yours or adopted from a named AI.
- **An idea:** one to three pieces of your work, each with one line on what it shows, then its sources. No IDs or file paths.
- **Where:** when you ask, a small card inline in Claude desktop chat (and ChatGPT if your plan allows) that opens to full screen; a text version inside Claude Code's chat.
- **Revisit, or also expand?** You were not sure. The panel stays revisit-only, with "ask about this for my problem" as one visible step into the chat; whether you take that step, and whether it changes your answer, is the evidence.

**What the research found** (note 25, 2026-10-24):
- No product or study tests glancing at an AI-made overview of one person's ideas; note 20's gap stands. ChatGPT's and NotebookLM's views send depth to the chat, and none publishes how people use the view.
- Studies back the parts: a small first screen, a layout that keeps what you saw in place, your own words and work as cues, origin marked quietly, and one-step corrections.
- Outline versus map matters little for understanding. It matters for finding an idea fast and for seeing links and conflicts.
- The surfaces decide a lot:
  - an inline card in Claude holds about 4–5 data points and two actions, with no drill-in, so the full overview needs full screen;
  - anything that needs the AI's judgment goes to the chat;
  - panels keep no lasting state, so pins, "seen" marks and the stable layout live in Northstar's store.

**Why it is shaped this way** (notes 23 §4, 25):
- A cue helps recall when it was part of how the memory was formed (Tulving and Thomson 1973, from secondary sources). So each idea shows your work.
- A week later, people recalled less accurately which ideas had involved an AI (Zindulka et al., CHI 2026). So origin is shown.
- Imposed groupings hurt joint memory in couples (Wegner, Erber and Raymond 1991, from the abstract). So topics come from your words.

**The sketch round (2026-10-27) and the research after it.**
- **The round:** sketches A (an outline) and B (a map) were built from your website work and three chats you sent. The test missed its bar (2 wins, 2 ties, 0 losses), and you chose neither: "Leaning towards B but still not very helpful."
- **The research you asked for:** four deep notes and a synthesis ([note 26](../../research/round6/26-best-form-synthesis.md)).
  - Your three needs want different forms, and the shape matters less than the content.
  - It points to one overview with three ways in:
    - a smarter map: few entries in your own words, each with your work, and lines around the idea in focus;
    - "where you left off";
    - ask, with quotes from your record first.
  - The first view is your choice: the smarter map, or a text hub with the map second.
- **Next:** one look-and-react round of that view, from your real chats, with no timer. Sketches stay on this Mac.

---

## 7. Connectors, platforms and storage

**One shared integration layer, thin adapters** (kept from [CN]). Each connector also carries §1.4's "where the thinking runs".

| App | Capture | Memory | Focus | Your overview |
|---|---|---|---|---|
| **Claude Code** | Both sides, word for word, through hooks (note 22 A1–A4) | Start notes; facts after clear, fork and compaction; recall tool | Full: your assistant thinks in its reply from the note; the blind check runs as a sub-task | A text version in the chat; the full panel in Claude desktop chat |
| **Codex** | As Claude Code (B1–B3) | As Claude Code | As Claude Code, with ChatGPT's models | A text version in the chat |
| **Claude desktop chat** | Only when the model calls Northstar, as its report (C4) | Only when the model calls Northstar: weak (C6) | On request only: your assistant calls Northstar's tool and thinks in its reply; weak, tested | A card inline in the chat that opens to full screen (C9; note 25) |
| **ChatGPT desktop chat** | Possibly none on a personal plan: write tools are documented only for Business, Enterprise and Edu (D4) | Needs a public address or OpenAI's outbound tunnel, even on desktop; the tunnel needs an OpenAI Platform organization and API key (D2, D3) | On request, as in Claude's chat, if your plan allows custom tools | A card, if your plan allows (D9) |

- **Codex specifics:** each Northstar hook must be trusted in Codex once, and again after each update, since an edited hook is skipped until re-trusted (B1). Hooks do not run in Work Cloud tasks, and the IDE extension is unverified (B6).
- **Platforms:** this Mac first, Windows right after. The phone was second in your 2026-10-09 order; you are not sure yet (2026-10-25). Until you decide, the plan puts it after the four first connectors, because phone chat needs an always-on core and a reachable address.
- **Storage:** local now (SQLite and files, encrypted at rest); other computers later forward to one core; cloud later is a storage swap. Only what you mark as personal is captured.

---

## 8. How each job is tested against your real apps

**Rules:**
- Your real app as you normally use it is the baseline. Your blind picks decide; an AI judge counts only once it matches you.
- Every bar is fixed before the data, and each can fail. With one rater, a pass is directional evidence.

| Job | Test | Passes only if all hold |
|---|---|---|
| **Memory** | 16 real first messages from three or more projects (10 continue earlier work, 6 start fresh), each run in Claude Code as you use it, with and without Northstar. Blind pairs. The first reply's added wait is timed | On continuing messages: something delivered in at least 8 of 10, and you prefer Northstar's reply in at least 7 of 10. A third fewer re-explanations. Nothing on at least 5 of 6 new starts. No presumed facts; no leaks across projects. The added wait stays within 3 seconds |
| **Focus** | (1) The moments replayed on a new long session you mark first. (2) At each moment, the reply with and without the note, blind. (3) About 10 blind pairs of your own versions; flip tests; the blind sub-task against your assistant checking in its own reply; and, for the thinking, your assistant's reply against a hidden sub-task. (4) A short real interview-prep session. (5) At 8 late points, the long chat against a seeded fresh session. (6) Two to four weeks of real use. (7) After each raise, the next three replies | (1) At least 1 in 3 of your marks caught, with at most 1 false alarm per session. (2) The raise is welcome in at least 2 of 3 moments; the answer part is preferred or tied in at least 8 of 10; silent at 3 in 4 unmarked moments yet raising at least half the marked ones. (3) The check agrees with you on at least 7 of the pairs where it gives an opinion and never flips on the label alone. A separate sub-task is kept only where it beats your assistant's own reply. (4) You say the step back helped. (5) The seeded session wins at least 6 of 8. (6) At least half of raises accepted, at most 1 in 4 declined as wrong, and you keep it on. (7) No later reply repeats the raise or changes tone because of the note |
| **Maintenance** | Replay over your copied sessions, run by run; a 15-minute marking page of about 60 items; injected faults; eight simulated weeks of runs | 90% of items confirmed as what you hold; scope wrong at most 10%; no leaks; every item cites chat turns; nothing dropped without a reason; recall of planted items holds over eight weeks; every structural fault blocked. The value rule agrees with your marks on at least 63% of 60 items, or it fails for now and the overview shows only items you confirmed |
| **Overview** | Four set tasks from your real topics, 5 minutes each, with the overview and with your usual means (your apps' chat search and memory, your repositories). In the sketch round, the overview tasks alternate A and B (note 25 §5) | The overview wins at least 3 of 4 and loses none; at most 1 line in 10 flagged "not what I think" |

---

## 9. The first prototype: Claude Code on this Mac

**Aim.** All three jobs in Claude Code, with your overview also in Claude's desktop chat, on your real work and your own AI. **This Mac first,** where your sessions are; Windows right after.

**In v0:**
1. **Capture:** a Claude Code plugin with hooks; with your go-ahead, a one-time backfill of your copied sessions.
2. **Core:** chat history, the event log, the write gate, scopes.
3. **Maintenance:** started by a scheduled job after idle sessions and nightly, with weekly restructuring; the safety copy and log; checks by the other model family.
4. **Memory:** start notes, strict facts within the 3-second budget, the refill after compaction, the recall tool.
5. **Focus:**
   - working memory, with file snapshots on a hidden git ref and headless renders of web work;
   - the three default moments;
   - the note, and your assistant's thinking in its reply;
   - the blind check as a hidden sub-task;
   - the moves: step back, split and fresh start;
   - the decisions check and firmness.
6. **Overview:** a read-only card inline in Claude desktop chat that opens to full screen, plus a text version in Claude Code, in the shape the sketch round settles.
7. **Robustness:** the write gate, invariants, quarantine, rollback, the log, and a fault-injection smoke test. The full fault suite runs before the prototype counts as evaluated.
8. **Tests:** §8.

**Checked before building:**
- SP-5: whether your Claude plan includes monthly API credits and how they are used;
- whether a small-model call fits the 3-second budget on your first message;
- Northstar's own runs must never be captured as your sessions ([HK] §11's guard, kept).

**Effort:** about 10 builder-weeks (±50%), our estimate by part, not a measurement.

| Part | Builder-weeks |
|---|---|
| Capture | 1 |
| Core | 1 |
| Maintenance | 2.5 |
| Memory | 0.5 |
| Focus | 2 |
| Overview panel | 1.5 |
| Robustness and tests | 1.5 |

**Running cost:** about $25–85 a month at 20–100 turns a day (±2×), through the APIs (§1.4). It is measured in the first week, under a cap you set ([SPINE] UQ-16 suggested a soft cap of $80 and a hard cap of $120).

**Needed from you then:**
- the go-ahead for your sessions;
- an Anthropic API key (or your plan's API credits) and an OpenAI API key;
- which repositories and folders are personal;
- about 15 minutes for the marking page and about 10 for the version pairs.
- When Codex follows: trusting Northstar's hooks in Codex.

---

## 10. Decisions so far, and what is next

**Decided:**
- **Round 1 (2026-10-24):** focus gets its own quality check; "facts, not judgment"; this Mac first; approval with changes.
- **Round 2 (2026-10-24):** focus confirmed; go ahead; Northstar runs on the AI you already use; "dreaming" means ChatGPT's Dreaming memory system.
- **Round 3 (2026-10-25):** ChatGPT's Dreaming is a reference for what Northstar is like, not a mechanism to copy; it works with existing AI, not on its own. Claude and ChatGPT may check each other. The sketches use your website work plus chats you add. The phone: not sure yet.
- **Decided by the design, as you left to it:**
  - focus runs beside the conversation with equal weight to memory;
  - your overview is served by memory's read path;
  - hidden sub-tasks go through the vendors' APIs (§1.4).

**Open:**
- **The phone's place in the order:** you are not sure yet. Until you decide, it comes after the four first connectors.

**Next, as you approved:**
1. **The overview sketch round** (§6): your website work plus a few chats you add to `~/northstar-probe/inbox/`. It compares a topic outline with conflict pairs against a stable topic map.
2. **The Claude Code prototype on this Mac** (§9), then Windows.
3. **The tests** (§8).

**Smaller choices we made** (tell us if any is wrong):
- The background process is called **maintenance**, your word for job 3, since "Dreaming" is OpenAI's name and you did not mean it literally.
- Your working-style lines reach the AI only when it asks, like your views. They used to go in where learned (your pick of 2026-10-10). We changed it because of "provide memory, not alter the behaviours" (2026-10-15).
- Phase close is off by default (§3.1).
- A goal from an earlier chat of the same work is reused and shown for correction.
- Only your stated goal reaches the AI as a fact.
- What to learn lives in your overview.
- There is no project layer beyond work in progress.

**Settings and their starting values:**

| Setting | Default |
|---|---|
| How sub-tasks reach your AI | The vendors' APIs, on the same model families |
| Checks across vendors | On (your answer of 2026-10-25) |
| Focus firmness | Normal |
| Focus moments | A new day; past half the window; on request |
| Focus's quality check | On where versions exist, once calibrated |
| Decisions check | One line in the AI's next reply; or only you; or off |
| Maintenance changes | Applied after checks, with a log; or held for your adoption |
| Your views and working style | Only when the AI asks |
| Lasting project knowledge | Each product's memory and files (your default) |
| When a project idea becomes personal | After a second context (your default) |
| Memory use shown in chat | Never inside the reply; options: a note outside it, or "used in this chat" in your overview |
| Search | A small local search model; or keywords only |
| Web checks of AI claims | Off |
| What is captured | Personal accounts, repositories and folders you mark |

---

## 11. Risks

| # | Risk | What we do |
|---|---|---|
| 1 | The moments catch about half of your moments (6 of 13, in-sample) | On-request moves; candidate moments tested on your marks; option (c) as an experiment |
| 2 | A wrong note is costly, and a false raise feels like nagging | Default silence; one raise per moment; blind checks with "can't tell"; the bars in §8 |
| 3 | No study has measured what a note costs the answer itself, and our note stays in the chat's hidden history, unlike the study's | The answer comes first; the note says "this reply only"; §8 tests the answer part and the three replies after |
| 4 | Focus's thinking runs in the conversation that drifted | §8 compares it with a hidden sub-task, which replaces it only if it does better |
| 5 | Running costs more than we first said: about $25–85 a month through the APIs | A cap you set; measured in the first week; your plan's API credits may cover part |
| 6 | Checks across vendors send excerpts between Anthropic and OpenAI | Allowed by you; only the excerpts a check needs; listed in the log |
| 7 | The chat apps have no hooks, so focus works there only on request | Said plainly; the scheduled job on this Mac processes chat-app captures |
| 8 | Judges are weakest on close versions and on taste | Blind, both orders, several screenshots, calibration on your own pairs; a second opinion only |
| 9 | Maintenance can drift or drop updates over months (HaluMem; one curated map fell from 96% to 72%) | Source-cited items only; no derived inputs; the safety copy; the log; an eight-week drift test |
| 10 | ChatGPT may allow only read access on a personal plan, and needs a reachable address and an OpenAI API key for the tunnel; Codex hooks need re-trusting after updates | Checked on your plan before that stage; reported, never hidden |
| 11 | Value may stay hard to learn, so the overview starts thin | Deferral; your optional marks; a failing value test keeps the overview to items you confirmed |
| 12 | The overview's look is unproven; an inline card holds little | Full screen for the map; the sketch round compares two forms |

---

## 12. What is kept, replaced and dropped from the 2026-10-09 design

| Kept | Replaced | Dropped |
|---|---|---|
| Connector strategy ([CN], [HK], [CX]) | The Book ([TB]) → the human structure and your overview | Textbook explanations; re-encounter cards; gaps from terms that merely appeared |
| Platforms ([PF]) | The per-turn steward and corrections ([IS]) → focus's working memory, your assistant's thinking at a few moments, and a one-reply note | Labelled memory blocks; usage rules in memory |
| Maintainer robustness ([MT]) | The maintainer's job catalog → the maintenance run, with a safety copy and a log | The holistic AI judge |
| Core data model ([CDM], [PL]) | The fixed-slot start pack ([AC]) → start notes, strict facts elsewhere | The local third-family verifier as the default: a separate AI you asked not to have. Cross-family checks replace it, as you allowed |
| Structure in both directions ([KO]) | Anthropic API workers → the same model families as the apps you use, through the vendors' APIs (UQ-6 kept) | |
| Family-aware routing ([SPINE] §8.3) and its cost model ([MT] §9.6) | Relevance scoring ([PR]) → deferred value and scope; benchmark v0 ([BM]) → tests against your real apps | |

---

## 13. Goal-fidelity check

| GOAL item | Where | Status |
|---|---|---|
| §4.1 A system, no rituals | Every job runs without you | By design; one-time API keys |
| §4.2 Adopted AI knowledge first-class and validated; the rest archived | §1, §2, §5 | By design on Claude Code and Codex; partial on the chat apps |
| §4.3 The AI manages it | §1.2, §5 | By design |
| §4.4 Two architectures over one core | §1.1, §1.3 | By design: the AI index and the human structure |
| §4.5, §3.3 In-session focus and continuity, equally | §3, §4 | Partial: the moments catch about half of your moments (risk 1); the chat apps (risk 7) |
| §4.6 Product-agnostic with connectors; platforms; local now; personal first | §1.4, §7, §9 | By design; partial for ChatGPT (risk 10); the phone's place open (you are not sure yet) |
| §4.7, §4.8 Robust maintainer; built and evaluated | §5, §8, §9 | By design and planned |
| §2 (2026-10-15) Plain context, no rules, no memory talk | §3.3, §4 | Confirmed (round 2) with focus's one-reply note as the one exception; working style pull-only |
| §2 (2026-10-24, round 2) Runs on the AI the user uses; separation only where needed, with reasons | §1.4 | By design: focus thinks in the assistant's reply; four places run apart, each with its reason |
| §2 (2026-10-25, round 3) Like ChatGPT's Dreaming in sense, not literally: memory structures for AI and human; focus and memory; works with existing AI, not on its own | §0, §1.5 | By design: positioning first, ChatGPT's system as the reference; the route keeps a commercial path open |
| §2 and §3.2 Human view | §1.1, §6 | At risk until a sketch lands (risk 12); research done (note 25) |
| §2 (2026-10-09, 2026-10-10) Structure both ways; relevance; value threshold; dynamic rules | §5 | Partial (risk 11); no fixed topic counts |
| §2, §6 Baseline first, real apps, improvement defined in advance | §8 | Planned; every test can fail |
| §5 Research constraints, including injection | §1.2, §2, §4 | By design |
| §7 Reframing needs you | §10 | Checked: every answer recorded in GOAL.md; the one open item (the phone) left open |

---

## 14. The research behind each part

Each row names the strongest sources, stated as the notes state them; "probes" means your own data (E2).

| Part | Research behind it |
|---|---|
| **Chat history kept; memory built from it** (§1.1) | Probes: value judged after capture was chance, with uncertain labels from one project. One rewrite collapsed a context below no memory (ACE). Memory systems miss over half of updates and accumulate invented content (HaluMem 2025). In brain research, a parallel rather than a proof: fast capture and slow learning are separate systems (McClelland, McNaughton and O'Reilly 1995). [notes 01, 13, 23] |
| **Maintenance in the background** (§1.2) | ChatGPT's Dreaming: a background process that synthesizes the memory state and keeps it current (OpenAI product post, 2026; no paper). Codex memories (open code): per-session extraction, then one consolidator. Anthropic's Dreams (preview): a new store you adopt or discard. Sleep-time compute (Letta, 2025): about 5× less answer-time compute at equal accuracy, and up to 13–18% more accurate, when the next request was predictable. [notes 03, 23] |
| **Separate items, safety copy, log, no summaries of summaries** (§1.2) | Iterated rewriting drifts toward model defaults (note 06; Perez et al., ICLR 2025). Consolidation strips hedges (Kwon 2026). OpenClaw bounds what a rewrite may drop. [notes 06, 13, 23] |
| **Re-check on use; fade, never delete** (§1.2) | Parallels from human memory, not proofs: a retrieved memory becomes changeable again, mainly after a mismatch, and the old one persists (Nader, Schafe and LeDoux 2000; Lee, Nader and Schiller 2017); the odds that a memory is needed follow its past use (Anderson and Schooler 1991). [notes 01, 23] |
| **Where it runs apart, and the route** (§1.4) | Blind check: judges favour "new" ("The Silent Judge", 2025) and what users like (Sharma et al. 2023); an average 64.5% blind spot for one's own errors (Tsui, NeurIPS 2025). Other family: errors overlap more between similar models (Goel et al., ICML 2025); judges favour their own text (Panickssery et al. 2024). The route: [SPINE] §8.2, P7, P8, P9, P11, UQ-6. Hooks and latency: note 22 A3, B1, B3, B6, B9; [HK] §4.3. [notes 13, 22, 24] |
| **Value deferred** (§5) | Go-CLS (Sun et al., Nature Neuroscience 2023); need × gain (Mattar and Daw 2018); strict selective addition beat add-all by 15–26 points (Xiong et al. 2025). [notes 01, 18] |
| **One write gate; second-family checks** (§2, §5) | Self-conditioning (Sinha et al., ICLR 2026); weak self-correction (Huang et al., ICLR 2024); family-aware routing ([SPINE] §8.3). [note 13] |
| **Captured text is data, including focus's note** (§2) | Detection defences fail under adaptive attack ("The Attacker Moves Second", 2025); only write-time origin binding is sound (Louck 2026). [note 13] |
| **Restate; link; conflicts only with two checks** (§5) | Claimify (ACL 2025): 99% of restated claims entailed when it may decline; opinion conflicts found poorly (ContraDoc, NAACL 2024). [note 17] |
| **Memory: strict, plain facts, views on request** (§4) | A memory agent that injects a short reminder or stays silent raised pass@1 by 8.3 and 6.8 points and beat always-on injection (Wu et al. 2026, preprint); memory profiles raised agreement sycophancy by up to 45% (Jain et al., CHI 2026). Probes. [note 19] |
| **Focus: fixed moments** (§3.1) | Your trigger replay (6 of 13, in-sample). Proactive agents still false-alarm about half the time (Lu et al., ICLR 2025). Kuo et al. (IUI 2026): 52% engaged after commits; 62% dismissed mid-task after a declined edit. [notes 21, 24] |
| **Focus: a note for one reply** (§3.3) | Tutoring systems split deciding from saying (StratL, ACL Findings 2025; Bridge, NAACL 2024); Tutor CoPilot's trial, with suggestions to human tutors on demand (+4 points); goal, needs, gap (GenMentor, WWW 2025); a monitor's one-reply instruction, not kept in the transcript, cut drift 87% on a simulated persona (Leins et al. 2026). [note 24] |
| **Focus: rare, an offer, about the task** (§3.3) | More frequent proactive help halved preference (Chen et al., CHI 2025); feedback aimed at the person backfires (Kluger and DeNisi 1996). [notes 21, 24] |
| **Focus: blind quality check** (§3.2) | Order bias and the both-orders fix (Zheng et al., NeurIPS 2023); judges favour "new" ("The Silent Judge", 2025) and what users like (Sharma et al. 2023); design taste near 73% (AesEval-Bench, ICLR 2026). [note 24] |
| **Fresh start from distilled state** (§3.4) | All information in one prompt kept 95.1% of single-turn performance (Laban et al., ICLR 2026); replacing a model's own earlier replies raised later performance (Li et al. 2026). [notes 11, 24] |
| **Your overview** (§6) | No study of glancing at an AI-made overview of one person's ideas (notes 20, 25). The parts: encoding specificity (Tulving and Thomson 1973); origin recalled worse a week later (Zindulka et al., CHI 2026); transactive memory (Wegner, Erber and Raymond 1991); re-finding (Whittaker 2011); with a model-made concept map, 14 students rated mental demand 31.5% lower at equal accuracy, mapping a text rather than a person's ideas (Han and Choi, BEA 2025); Claude's guidelines for inline cards (note 25 §3). [notes 20, 23, 25] |
| **Tests: your blind picks decide** (§8) | People rated 54.6% of personalized replies no better than generic ones; the best judge correlated about 0.37 with them (Zhang, Liu and August 2026). [note 19] |
