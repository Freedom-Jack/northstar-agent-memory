# Northstar: where the exploration stands

**Written 2026-10-14, as a handoff to a fresh session; updated 2026-10-24.** [`GOAL.md`](GOAL.md) is authoritative and overrides this note. Read GOAL.md first (especially §1 and §2 from 2026-10-10 to 2026-10-24), then this note.

**Status (2026-10-28).** The probe phase is closed. The three-job design (revision 3.2) is settled except for one piece: the overview's form. After the deep research (notes 26, 26a–26d) the user picked a smarter map first. They found the look-and-react round of it not helpful (below). The next step for the overview is not agreed yet.
- the design: [`design/revision-2026-10-23/DESIGN.md`](design/revision-2026-10-23/DESIGN.md);
- the review page: [`design/revision-2026-10-23/review.html`](design/revision-2026-10-23/review.html), published privately at https://claude.ai/artifact/Wj6HjavkFpxdT87EqBERyp;
- the research findings page: [`research/round6/overview-form-findings.html`](research/round6/overview-form-findings.html), published privately at https://claude.ai/artifact/CpU3aQtQQcX8N7ZWHxZYrp;
- the sketch round's brief and results: [`design/revision-2026-10-23/overview-sketch-round.md`](design/revision-2026-10-23/overview-sketch-round.md).

The other documents in `docs/design/` are the earlier proposal of 2026-10-09, kept as a component library (DESIGN §12). Nothing is built.

This note holds aggregated findings only. The user's chat content and probe data stay outside the repo, in `~/northstar-probe/` (§6).

**The overview look-and-react round (2026-10-28, done).** Counts only; the user's words are in GOAL §1 and §2 (2026-10-28), and the page, data and notes are in the probe workspace (`out/ov-c*`).
- **Built:** one view with three ways in, from the sketch round's three chats plus the website work up to 22 Oct.
  - The map: 4 topics, 14 entries on the map and 22 in all, 16 pieces of work as cues, 4 open questions.
  - Links: 1 conflict pair and 1 link stated by the user, both shown; 2 links Northstar suggested, kept off the map until confirmed.
  - 4 "where you left off" cards.
  - Ask: exact words over 211 of the user's messages, with 119 AI replies as a second tier.
  - A text version, and a reactions box.
  - All 141 quoted strings were checked word for word; 0 failed.
- **Use, from the page's log:** 11 clicks on the map (10 distinct items in all 4 topics), 2 asks (the same two words, taken from an open question), 0 "where you left off" cards opened, 0 text-version views, 0 "not what I think" flags, 0 suggested links decided. The first logged click was at 13:41 and the notes were copied at 13:45.
- **Verdict:** not helpful, with nothing marked as working. The user's pick for the first way in ("where you left off") differs from the log (the map first).
- **The format still needed explaining:** the user asked what they were doing when the page opened.
- **Two gaps the user then named** (GOAL §1, §2):
  - the architecture's algorithms and data structures, for the AI's knowledge and for the user's;
  - how the human view appears: inside ChatGPT or Claude, a UI such as the maps, or a mind map.
- **Next:** not agreed yet.

**Start here (2026-10-27, research on the overview's form).**
- **What ran:** four research agents in parallel, then a synthesis ([`research/round6/26-best-form-synthesis.md`](research/round6/26-best-form-synthesis.md)). About 1.19M subagent tokens against an estimate of 1.5M.
  - [26a](research/round6/26a-refinding-and-resumption.md): finding one's own things again and resuming work.
  - [26b](research/round6/26b-visualizing-own-ideas.md): visualization and learning science.
  - [26c](research/round6/26c-practitioner-writing.md): practitioners.
  - [26d](research/round6/26d-products-and-use.md): products.
  - Together about 200 sources.
- **Findings:**
  - No study tests an AI-made overview of one person's ideas.
  - The three needs want different forms:
    - **the big picture:** a few entries per topic in the person's own words, each with a work cue (weak to moderate);
    - **getting back into work:** "where you left off", meaning the work as it was left, what changed, and the next step (moderate);
    - **questions about the past:** ask in the chat, with quotes from the record and their places (moderate; the strongest product convergence).
  - The shape matters less than the content. Maps beat outlines by g = 0.28 for students, and by about nothing for high-ability learners.
  - The risks that set the details:
    - an AI's wording (one wrong summary detail changed recall from 83.6% to 44.8%);
    - answers from summarized memory (ChatGPT's memory scored 57.7%, against 91.8% reading the full history);
    - citations that are not checkable (random citations still raised trust).
- **Checked against sources:** Elsweiler 2008 (topic 85.1% against time 57.5%), Nesbit & Adesope, Melumad & Yun, Sim et al., LongMemEval, Ding et al., Chan et al., the Ask Photos pause and NotebookLM's node-to-chat. 26b was corrected where it called AI summaries "paraphrase".
- **Direction (L):** one overview with three ways in.
  - A smarter map: few entries, the user's own words, work on each, lines around the focused idea, a stable layout.
  - "Where you left off".
  - Ask, with quotes first.
  - A text outline as the Claude Code version. Revisit or expand stays the user's call.
- **Decided 2026-10-28:** the first view is the smarter map (GOAL §1, §2).
- **Next:** a look-and-react round, not timed, of one view with all three ways in, from the user's real chats. The timed comparison waits for the prototype (DESIGN §8).

**The overview sketch round (2026-10-27, done).**
- **The test:** 8 lookups in 4 pairs, with the user's usual means against a sketch. The win rule was fixed beforehand. Aggregates only; answers and scoring are in the probe workspace (`out/ov-user-answers.txt`, `out/ov-results.json`).
  - **Result: 2 wins, 2 ties, 0 losses, which misses the bar of at least 3 wins (DESIGN §8).** One rater, so this is directional.
  - **The sketches helped with "who said what" and "where ideas pull apart":** right answers in about 1 and 3 minutes, where the user's memory or ChatGPT gave partial ones.
  - **Memory was fast but fuzzy** (about 40 seconds, partly wrong).
  - **Ideas that recur across topics were the hardest:** the usual means found nothing in 4 minutes. The paired sketch question was answered without looking ("My north star project lol"), so it gave no comparison.
  - Caveats: the user built these chats and knew them well; the questions differ within each pair.
- **The user's verdict:** "Neither. Leaning towards B but still not very helpful. I asked for a deep research on what is the best form, article/papers/published etc,." They would use "Ask about this" and are still not sure about revisit versus expand.
- **What the log shows:** both uses of "Ask about this" were questions about the user's own past ("what did I do before …", "what it is"), not applying an idea to a problem. That suggests asking one's memory in the chat may matter more than the layout. To test.
- **The test format confused the user** ("you want to test me on how much I remember the old chats?"). Explain that a timed lookup measures the tool, or use look-and-react rounds at the sketch stage.
- **Next:** deep research on the best form, as the user asked. The plan and its token cost go to the user first. Note 25 was one desk pass and found no study of this kind of overview.

**Start here (2026-10-25, revision 3.2).**
- **Round 3 answers** (page doc `review/answers-3`; verbatim in GOAL §1 and §2):
  - Q9 "Partly". ChatGPT's Dreaming memory system was a reference for what Northstar is "in a sense like", not a mechanism to copy. Northstar has memory structures (AI and human), helps with focus and memory, and "still works with existing AI like ChatGPT and Claude, it is not on its own". The user's reason: "Better commercial this way and able to embrace the powerful world class AI".
  - Q10 was left to the design: "you design, based on what I told you".
  - Q11 "Yes": Claude and ChatGPT may check each other's work.
  - Q12: the website work plus chats the user adds to the probe inbox; the user offered "a few chat example".
  - Q13 "Not sure yet" about the phone.
- **What revision 3.2 does:**
  - **Positioning first** (DESIGN §0): a memory and focus layer for the AI the user already uses; like ChatGPT's Dreaming inside ChatGPT, but across all their AIs, with structures for the AI and for them, and focus. Nothing in the design blocks a commercial version; the first version stays personal (GOAL §4.6).
  - **ChatGPT's system is now the reference** (DESIGN §1.5), not the frame. §1 is renumbered: §1.1 stores, §1.2 maintenance, §1.3 what reaches the AI, §1.4 where the thinking runs, §1.5 the reference.
  - **The background process is called "maintenance"**, the user's word for job 3, since "Dreaming" is OpenAI's name.
  - **The route is decided** (DESIGN §1.4): hidden sub-tasks go through the vendors' APIs on the same model families.
    - Third-party products may not use claude.ai logins or plan limits without approval (SPINE P8), and OpenAI recommends API keys for automation (P11).
    - It leaves the user's chat allowance alone, and the plan-login scripting route may close (P7).
    - For now: the user's own API keys, or plan API credits (SP-5).
  - **Cross-vendor checks are on.**
  - **The phone stays after the four first connectors** until the user decides.
- **Waiting on the user (updated later on 2026-10-25):** the overview test. The user sent three ChatGPT chats (two interview-prep chats, one winter-tire purchase chat); they now sit in the probe workspace, outside the repo.
  - The sketches and the test are built: 4 topics, 22 ideas, 12 work cues; sketch A (outline) and sketch B (map). The test page is `http://localhost:8765/ov-test.html`.
  - Status and file list: [`overview-sketch-round.md`](design/revision-2026-10-23/overview-sketch-round.md).
  - An optional note on the review page saves to `review/answers-4`.
- **Next:** the overview sketch round, per its brief ([`overview-sketch-round.md`](design/revision-2026-10-23/overview-sketch-round.md)). It compares a topic outline with conflict pairs against a stable topic map, inside the DESIGN §8 overview test, locally on `localhost:8765`. Then the Claude Code prototype on this Mac.
- **Cost of revision 3.2:** none; no agents were run.

**Revision 3.1 (2026-10-24, done: answered on 2026-10-25).**
- **What the user said in round 2** (verbatim in GOAL §1): focus is confirmed; go ahead with the overview round and then the Claude Code prototype on this Mac, with two changes:
  - Northstar's intelligence runs on the AI the user already uses (Claude, ChatGPT or any harness), "generalized and instead of seperated, unless you tell me it has to";
  - "dreaming" means ChatGPT's Dreaming memory system, the product feature, not sleep.
- **What revision 3.1 does:**
  - **The architecture is shown against ChatGPT's memory system** (DESIGN §1.1–§1.2), from OpenAI's Dreaming post and memory help page, read 2026-10-24 and cited by URL: chat history; saved memories (separate notes) against memory items; Dreaming; what new chats get; the memory summary page against the user's overview; sources; project-only memory; temporary chats.
    - Where OpenAI publishes nothing (Dreaming's stages, checks, undo), the design says so rather than implying absence.
    - The sleep and brain framing is gone from the architecture. DESIGN §14 keeps human-memory findings as parallels only.
  - **It runs on the AI the user already uses** (DESIGN §1.6). There is no Northstar AI to talk to or manage:
    - focus's thinking happens in the assistant's own reply, from a note Northstar prepares;
    - background jobs (Dreaming, the working-memory tagger, memory's selection) run as hidden sub-tasks on the same model families as the user's apps.
  - **Four places still run apart, each with its reason:**
    - focus's blind version check, in a fresh context (blindness is impossible inside the conversation); §8 compares it with the in-reply check;
    - Dreaming's checks, by the other family (routing from SPINE §8.3), which sends excerpts across vendors and so needs the user's OK;
    - a trigger for Dreaming (Claude's scheduled tasks or the Mac's scheduler; not an AI);
    - a small local search model (keyword-only is the alternative).
  - **The route stays the API by default** (SPINE UQ-6, ARCHITECTURE R16), on the same models, unless the user chooses their plans through `claude -p` and `codex exec` (Q10). The risks are quota, the `--bare` default (P7), OpenAI's automation advice (P11) and terms.
  - **Cost, corrected:** about $25–85 a month at 20–100 turns a day (±2×) through the API, by the 2026-10-09 cost model ([MT] §9.6), or roughly 0.5–2M tokens a day on the plans. The earlier $20–40 left out parts of that model.
  - **Latency:** memory's selection in a new chat must fit the 3-second budget ([HK] §4.3), or code alone decides. Focus's notes are prepared ahead.
  - **Smaller fixes:** working style is pull-only (2026-10-15 "not alter the behaviours"); phase close is labelled and off; no fixed topic counts; the "getting worse" statement now covers both sessions; evidence wording matches the notes (Kuo, Tutor CoPilot, Leins, Wu).
- **Waiting on the user** (page collection `review`, document `answers-3`; rounds 1 and 2 are in `answers` and `answers-2`, both recorded in GOAL §1):
  - Q9: does DESIGN §1 match ChatGPT's Dreaming memory system?
  - Q10: should hidden sub-tasks run through the API (recommended) or the user's plans, or be decided after a test?
  - Q11: may Claude and ChatGPT check each other's work?
  - Q12: what may the overview sketches use? The default is the website work only; the user may add chats to the probe inbox or name other sources.
  - Q13: should the phone come after the four first connectors, or second as on 2026-10-09?
- **The overview research is done:** [`research/round6/25-overview-display.md`](research/round6/25-overview-display.md).
  - No study tests glancing at an AI-made overview of one person's ideas.
  - Claude's inline card holds about 4–5 data points and two actions, so the full overview opens to full screen. Panels keep no state.
  - The sketch round should compare A, a topic outline with conflict pairs, against B, a stable topic map. The panel stays revisit-only, with "ask about this for my problem" as one step into the chat.
- **Next, already approved:**
  1. The overview sketch round on non-Northstar work (Q12 sets the material).
  2. The Claude Code prototype on this Mac (DESIGN §9), about 10 builder-weeks (±50%), then Windows.
  3. The tests in DESIGN §8.
- **Checks:** revision 3's adversarial review (Sonnet 5.5) found 4 blocking issues, all fixed in 3.1:
  - not every separation was shown to be needed;
  - running on the user's plans reversed UQ-6 without asking;
  - the ChatGPT comparison implied unpublished internals and missed that saved memories are separate notes;
  - "never marked getting worse" was false for the Northstar session.

  It also found 5 should-fix issues: latency and the window measure, Codex trust and the ChatGPT tunnel key, evidence wording, cost, and working style. All five are fixed, along with the minor ones.
- **Cost of revision 3:** about 0.64M subagent tokens: the review 0.38M (estimated 0.15M) and the overview research note 0.26M.

**Revision 2 (2026-10-24, done: answered the same day).**
- **What the user asked for on 2026-10-24** (verbatim in GOAL §1):
  - an architecture of the memory system for the AI and for the human;
  - something like OpenAI's "dreaming";
  - a focus job that brings its own intelligence from the AI side, not "an alarm system" of notes beside the chat;
  - research and papers behind the design;
  - the first prototype on this Mac, Windows right after.
- **What revision 2 does:**
  - **The memory architecture, now explicit** (DESIGN §1):
    - five layers: working memory; a raw record that is never edited; knowledge written only by dreaming; working style; the user's work;
    - two structures built from them: the AI index, and the human structure (topics in the user's words, connect and conflict links, open items, work cues).
  - **Dreaming:** an eight-stage consolidation cycle between sessions, with a shadow copy, a journal, reconsolidation and forgetting. It borrows the shape of ChatGPT's dreaming, Codex's memory pipeline and Anthropic's Dreams, but not their single rewritten summary or summaries built from summaries.
  - **Focus** (DESIGN §3): it still speaks only at a few systematic moments. At a moment, a focus model works out goal, needs and gap, runs a blind quality check and picks one suggestion or nothing. It hands the AI a brief for one reply; the AI answers first, offers the step in two sentences and acts only on a yes.
  - **Research:** a table ties every part to its research (DESIGN §14).
- **Asked the user:** Q6 (does the new focus match?), Q7 (does the architecture answer the note?), Q8 (go ahead?). Answered on 2026-10-24: Q6 yes; Q7 no, "dreaming" meant ChatGPT's Dreaming memory system; Q8 yes, with the changes in the notes. Recorded in GOAL §1 and §2; the page document is `answers-2`.
- **New research (2026-10-24):**
  - [`research/round5/23-memory-architecture-and-dreaming.md`](research/round5/23-memory-architecture-and-dreaming.md): what dreaming is in products, offline consolidation in agent research, the neuroscience behind it, the human side, and a proposed architecture.
  - [`research/round5/24-focus-intelligence-evidence.md`](research/round5/24-focus-intelligence-evidence.md): guidance through the assistant, steering by one-reply briefs, the limits of AI judges on design versions, how tutoring systems keep a learner on a higher goal, and fresh restarts.
- **After confirmation, in order:**
  1. A short research pass on overview displays, then one sketch round on non-Northstar work that tries both revisit-only and expand.
  2. The thin Claude Code prototype on this Mac (DESIGN §9), about 9 builder-weeks (±50%), then Windows.
  3. The tests in DESIGN §8.
- **Trigger replay (2026-10-24; aggregate only, details in the probe workspace).** Focus's systematic moments were replayed in code on the two marked sessions (13 marks; 21 points marked "continue"):
  - a new day: 5 marks hit, 1 false alarm;
  - the context past half the window: 1 hit, 1 false alarm;
  - the context past two thirds: 0 hits, 2 false alarms;
  - a commit: 0 hits, 1–2 false alarms (2 commits, both in the website session);
  - "looks good"-style words: 1 hit, 1 false alarm.

  So the defaults are a new day, half the window, and on request: 6 of 13 marks, 2 false alarms. Commits, two thirds and closing words are off. Both sessions were picked because they drifted.
- **Checks:** revision 2's adversarial review (Sonnet 5.5, high) found 4 blocking and 11 should-fix issues; all are fixed in DESIGN.md and the page.
  - Evidence had been overstated: Laban's 95.1%, Kuo's 52%, Bridge's 97% and Leins's 87%.
  - Focus's one instruction to the AI had been flagged too quietly, and the example had been chosen to fit the design.
  - The human structure was missing as a layer of its own.
- **Cost of revision 2:** about 0.78M subagent tokens: the architecture note 0.35M, the focus note 0.28M, the review 0.15M. The trigger replay was code only.

**Round 1 (2026-10-23, done: answered on 2026-10-24).**
- **Waiting on the user:** approval or feedback, and five answers (DESIGN §9).
  - **Q1, the role of focus.** It changes a confirmed answer (GOAL §2, 2026-10-15), so it is asked, not assumed. The options:
    - (a) lighter, recommended: it speaks only at a few moments (return after time away, phase close, very long chat, on request) and judges "worse" from the user's own feedback;
    - (b) the same, plus its own side-by-side quality check;
    - (c) as confirmed: it also judges quality and the moment, built as an experiment.
  - **Q2:** does the overview only revisit, with expansion for a problem happening in the assistant's answer?
  - **Q3:** three readings to confirm: "side job" means beside the chat with equal weight; the overview is served by memory's delivery; "facts, not judgment" means views go to the AI only on request.
  - **Q4:** prototype on this Mac first, where the sessions are, or Windows first, as ordered on 2026-10-09.
  - **Q5:** approve, approve with changes, or not yet.
- **Where the answers arrive:** in chat, or saved on the review page.
  - The page stores them in its database at collection `review`, document `answers`. Read them with ArtifactData `get` on the page's URL.
  - The page also has a "Copy my answers" fallback.
- **The design in brief** (DESIGN §0): three jobs over one core.
  - Focus holds the goal and work in progress, and speaks at a few moments.
  - Memory gives plain context: facts, not judgment, empty by default.
  - Maintenance defers value until evidence, checks adopted AI claims, and builds both structures.
  - The human view is a revisit-only overview inside the assistant, with real work as recall cues.
- **New research (2026-10-23):**
  - [`research/round5/21-focus-prior-art.md`](research/round5/21-focus-prior-art.md): no product holds an aim above the activity or suggests a fresh session for quality reasons; remarks belong at coarse breakpoints; how often matters most.
  - [`research/round5/22-surface-facts.md`](research/round5/22-surface-facts.md), product facts per surface. New since 2026-10-09:
    - Claude Code mods can draw a band and a pane in the desktop app.
    - Hook messages are reported dropped in the desktop Code tab.
    - On Windows, tool-blocking hooks now fail closed.
    - ChatGPT custom tools need a public address or OpenAI's tunnel even on desktop, and write tools are documented only for Business, Enterprise and Edu.
- **Checks done:** a goal-fidelity pass, and an adversarial review by Sonnet 5.5 at high effort. Its three blocking findings are fixed in both documents:
  - two open GOAL questions had been settled silently;
  - Q1 was framed unevenly and focus's "flag worse" role had been dropped;
  - several pass bars could not fail.
- **After approval, in order:**
  1. Record the answers in GOAL.md §1 and §2, together with the human-view sketch answers of 2026-10-15, which are still only in §3 here.
  2. A short research pass on overview displays, then one sketch round on non-Northstar work; the two sketches in the "work-first index sketch" session can seed it.
  3. The thin Claude Code prototype (DESIGN §8), about 8 builder-weeks (±50%). It needs the Q4 answer, the user's go-ahead for their sessions, an API key for background calls, which repositories are personal, and about 15 minutes for a marking page.
  4. The tests in DESIGN §7, against the user's real apps, each with a bar that can fail.
- **Cost of this step:** about 1.0M subagent tokens: the focus note 0.25M, the facts note 0.62M, the review 0.16M.

**Handoff of 2026-10-23 (done: carried in the revised design).** The probe phase is closed. The user agreed to one last focus test, then consolidation (GOAL.md §1, 2026-10-23). Next is **one fresh session** that writes the **revised three-job design** as a **short, layered review page** for the user's approval. The three jobs are focus, memory and maintenance.
- **Model.** Opus 5.5 at **max** effort. On 2026-10-23 the user first said xhigh, then, starting the session: "I want to start it with opus 5.5 max".
  - Suggestions from a side session, not the user's words: first a short research note on focus (what already exists for goal tracking and drift detection), at high; the final check against GOAL.md at max; the adversarial review by a different model from the author, for example Sonnet 5.5 at high.
  - State token costs before any workflow: the user has a spend limit. Each workflow agent costs at least 50K tokens.
- **Read first:**
  - GOAL.md: authoritative, with §1 and §2 through 2026-10-23.
  - §2 below: what each probe showed.
  - [`research/round4/three-jobs-analysis.md`](research/round4/three-jobs-analysis.md): the framing, its leans and its open questions.
  - §3: hypotheses.
  - `docs/design/` holds earlier proposals. Use it as a component library, not as the design.
- **What the design must carry from the probes** (details in §2):
  - **Memory:**
    - Plain context with no usage rules and no visible memory talk; facts, not judgment.
    - No unstated facts, and no lessons carried across projects.
    - Strict selection works mechanically.
    - AI judges are miscalibrated, so the user's blind picks are the ground truth.
  - **Human view:**
    - A big-picture overview of the user's ideas, with their actual work as the recall layer, one line each.
    - It revisits; it does not generate. It lives "in the assistant, when I ask".
    - Four prose formats and three map shapes were rejected.
  - **Focus:**
    - No watcher recovered the user's moments from the session alone. The best simple signal was the user returning after a break.
    - The user's cues were side topics; length plus "peaked" or "phase done"; and their own judgment of quality.
    - Firmness is a setting.
    - The lighter role in §2 ("What the focus probe showed") is a question for the user, not a decision.
  - **Maintenance:**
    - Extraction credits 88-96% of items correctly.
    - The value threshold is unsolved: about chance.
    - Scope starts narrow at capture.
- **How each job will be tested.** The design should say this, against the user's real apps (GOAL.md §2). The maintenance and memory replays were not run.
- **Open, not urgent:**
  - The two index sketches in the linked "work-first index sketch" session.
  - The empty inbox: real first messages and the interview-prep chat, which the memory and maintenance tests need.
  - The analysis's §6 questions, asked only when each one is needed.
- **Data:**
  - Raw session copies are in `~/northstar-probe/raw/`. Claude Code snapshots expire from about 2026-11-07; the copies keep them.
  - Probe outputs, including the focus replay (`out/focus-replay/`, plan `out/focus-replay-plan.md`), are in `~/northstar-probe/out/`.

Earlier handoff steps (2026-10-15), all done:
- the user's focus marks;
- the data copy (2026-10-15);
- the focus replay on the website session, plus its held-out test (§2).

---

## 1. What is settled

The WHAT is in GOAL.md. In short, as of 2026-10-14:
- A system, not a practice. No required rituals. The AI manages it; the user's corrections are optional.
- **The unit of memory is the user's own knowledge.** That means ideas and conclusions validated through discussion or research with AI, each with why, where it applies and how it was reached. AI ideas the user **adopted** count, and are credited to the AI. Other AI answers go only to a private, searchable raw archive.
- An AI answer is not memory just because the user asked a question. Memory starts from the user's own signals: a statement, a follow-up, agreement or disagreement, or using an idea.
- Personal relevance decides what is organized, and there is a **value threshold**: being the user's own idea is not enough.
- **The human view must be short and genuinely helpful.** The long textbook, the ID-based map and four text formats were all rejected.
- **(2026-10-15) The human view is a big-picture index of the user's ideas, not a textbook.** It is closest to a map: topics, with lines where ideas connect or conflict. The user glances at it when preparing for something or checking a decision. Depth is not fixed text: an AI assistant expands an entry for the problem at hand. Entries point to the user's actual work, meaning anything they got their hands on. When chat brings knowledge up at the right moment, the index is opened rarely. The user confirmed this direction and asked us to explore its best form.
- **The AI side** addresses in-session focus and cross-session continuity equally, gives context only when it is strongly linked to the conversation, and **must not stop the AI's own creativity**.
- **(2026-10-15) Provide memory; don't alter the AI's behaviour.** Memory goes to the AI as plain context with no usage rules. It adds facts the AI lacks, not judgment. The reply has no visible memory talk. A new chat presumes no unstated facts and carries no lesson from one project into another; it does not start blank. The baseline is the user's real apps as they normally use them.
- Product-agnostic, with connectors. Windows first, then iOS, then Mac. Many machines and phones share one memory.
- Evaluation comes baseline-first, on the user's real topics. The user's own blind picks are the ground truth.
- Uncertain design choices become **settings with defaults**.

## 2. What the probes showed

Two probe rounds ran on the user's real chats on this Mac. All of those chats are about designing Northstar itself, which limits the evidence (§4).

| Question | What we found |
|---|---|
| Can the user's knowledge be pulled out of chats and credited correctly? | **Mostly yes.** Three extraction methods credited 88-96% of items correctly. About half the items the user holds were AI ideas they adopted, which confirms that adoption matters. 14 of 50 items quoted rough phrasing too literally. |
| What is worth keeping? | **Not solved.** About half the extracted items were judged worth keeping. Three value models matched the user's keep labels only about 48% of the time, no better than chance. But the labels themselves were uncertain, and every item came from one project. The user said many "don't keep" items are project knowledge, useful for the project but not personal. |
| What should the human view look like? | **Not solved.** An ID-based knowledge map was rejected ("doesn't help me with my logic flow"). Four research-based text formats were also rejected, rated 1-2 out of 5 and "read like an answer from Claude/ChatGPT … not a real helpful format": theme briefs, a situation playbook, question-led answer cards, and principles with cases. |
| Does strongly linked selection pick the right knowledge? | **Yes, mechanically.** It found 9 of 10 required items and added nothing on unrelated topics. In a larger mixed memory (226 items) it also found genuinely relevant items. At that size, pasting everything leaked irrelevant personal details into unrelated answers. Strict selection, though, missed context when the question was about a whole project. |
| Does giving the AI memory produce better replies for the user? | **Not yet, by the user's own judgment.** An AI judge rated memory-backed replies far higher. Across 9 blind pairs, the user preferred the memory-backed reply only twice; they preferred a reply with no memory, or a general profile, 5 times, and called 2 ties. Two framings were tried: memory as facts, and memory as background with "don't restate, add something new". Reading the replies shows memory makes the AI **echo the user's known positions** and crowds out new value. |

**Lesson for evaluation:** AI judges rewarded visible use of memory, which the user does not value. Any judge must first be calibrated against the user's own blind picks.

**Round 4 (2026-10-15): fresh answer first, memory second.** Five ways of replying were tested on six first messages: the four from round 3, plus two new ones outside Northstar (choosing an agent framework at work; reviewing a long AI-written design doc). All five used the same selected memory:
- **fresh**: no memory;
- **addendum**: the fresh reply unchanged, plus a short memory pass added at the end;
- **parallel**: the fresh reply and a memory brief written in parallel, then merged;
- **in-prompt**: the round-3 approach, with memory in the prompt;
- **one-pass**: a single call told to answer fresh first and then add memory, the version chat apps would need.

What is known before the picks:

| Check | Result |
|---|---|
| AI judges' predictions, recorded before the user ranks | Both judges ranked the fresh reply last in 10 of 12 rankings, and never above third. One judge was generic. The other was told the user's taste and their earlier picks. If the user ranks the fresh reply higher, the judges are still miscalibrated. |
| Memory selected by mistake, on two everyday questions | The parallel brief correctly added nothing in both. In-prompt and one-pass did not leak. The addendum pass leaked once: it tied a plain MCP how-to on Windows back to the user's Northstar plans. An appended memory pass needs its own relevance gate. |
| Strict selection outside Northstar | 2 of 3 new messages got a strongly linked item. The third, about choosing an embedding model, got nothing: its candidate, the user's evaluation principle, was recorded with a Northstar scope. Transfer across contexts depends on how scope is recorded. |
| Length | Memory arms ran 285-412 words, against 265-332 for fresh. The addendum arm was the longest in 5 of 6 sets, so length is a confound to keep in mind when reading the picks. |

**Results, from the user's blind ranks.** Six analysts (one per set), a synthesis and two skeptics produced these; only findings that survived are listed. Full detail is in `~/northstar-probe/out/r4-analysis.json`.

| Finding | Evidence | Confidence |
|---|---|---|
| Only the top picks carry clear signal | In 4 of 6 sets, the ranks below the top pick follow display order exactly; chance gives that about 1 time in 12 per set. The user said they ordered the rest "depending on the set". | High |
| Top picks: fresh 3, parallel 2, in-prompt 1, addendum 0, one-pass 0 | Fresh winning 3 of 6 is suggestive, not significant (p ≈ 0.10). Memory won where it supplied facts the model lacked: what Northstar is and what was already decided. | Low to medium |
| Memory that presumed context lost | There were two clean comparisons. A merged reply opening "You've already got the core piece" lost to a fresh reply with the same advice and length. An addendum that added the user's Northstar review-page preference to a work design-doc review lost to the same body without it. | Medium |
| The arm prompts caused part of this | "Skip what the user already knows" turned memory into presumption and cut fresh advice. The required "From your earlier thinking" opener pointed at the user's past. The memory pass never declined on the six real sets, even where the fresh reply already said what the memory said. One-pass leaked its "Part 1" label and used memory in that part. | Medium |
| Usage rules in the prompt did not control behaviour | One in-prompt reply applied a record scoped "not necessarily interviews" to an interview, backed by an invented claim about what interviewers reward. | Low |
| Scope was written too broadly at capture | A review preference learned on Northstar was saved as applying to "reviewing AI-produced proposals" and was then selected for a work sign-off. | Low |
| The test conditions capped quality | The user called all five replies "close world" and "too amateur". Replies were written with no tools or web, about 250 words and a role-play prompt. This project's memory index also reaches subagents, so "fresh" may not have been memory-free. | Medium |
| The AI judges are still miscalibrated | Their top pick matched the user's in 1 of 12 rankings, and they never ranked fresh first. The scenario rubrics rewarded what the user rejected, such as applying Northstar lessons to a new project. | Medium |

**What the user decided from this** (GOAL.md §2, 2026-10-15): "provide memory for the AI agents/LLM, not to alter the behaviours". In practice: plain context with no usage rules, no visible memory talk, facts not judgment, no unstated facts, and no lessons carried across projects. The baseline is the user's real apps.

**Focus marks (2026-10-15), the user's website session.** Ground truth for the focus replay. Per-message marks stay in the probe workspace; the user's answers are in GOAL.md §1.
- **8 of 20 messages marked:** 6 "suggest a fresh session" (one only "if it is applicable") and 2 "step back to the goal". None was marked "it is getting worse". The other 12 are "continue", 11 of them noted explicitly.
- **Not drift:** two early pauses were usage limits. Two messages after a "fresh" mark were marked "continue" because they would already have been in the split-off session.
- **Best version:** mid-session (after message 14), not the first draft.
- **Firmness:** a setting.
- **Goal:** a design demo. Whether to continue should be judged from the human's feedback in the session; the user is "not sure if there is a systematic way to determine this".
- **The session's own AI** never suggested a fresh session unprompted. It agreed when the user asked, near the end.
- **Reading, not decided:** "fresh" covers two cases. One splits off a side errand that doesn't serve the session's goal. The other restarts from the best version once the design work has peaked. 8 of 20 is more often than "speaks up rarely" (GOAL.md §2); most of the difference is side errands. The replay scores against the marks as they are.

**Focus replay, stage 1 (2026-10-15).** Two watchers read the session one turn at a time, seeing only the past: one from the text, one also from the screenshots. Both used the Opus 5.5 workflow agents at medium effort, with the same neutral instructions as the marking page ("most turns need nothing"). Results are in `~/northstar-probe/out/focus-replay/`.

| Arm | Spoke at | Hits (of 7) | False alarms (of 12) | Best version at the end |
|---|---|---|---|---|
| Text watcher | none | 0 | 0 | the last version, not the user's pick |
| Text + screenshots | none | 0 | 0 | the last version; it picked the user's version when that one appeared, then switched |
| The session's own AI | none unprompted | 0 | 0 | n/a |
| Rule: user returns on a new day | 3 points | 2 | 1 | n/a |
| Rule: every 5 messages | 4 points | 2 | 2 | n/a |
| Rule: after compaction / context past half | 0 or 1 point | 0 | 0 or 1 | n/a (the session never compacted) |

- **Fails every bar.** No arm, rule or watcher comes close to 5 hits with at most 2 false alarms.
- **It saw, but did not speak.** Both watchers' cards logged the side errands as open threads (13 to 17 by mid-session), and the screenshot watcher preferred the user's best version over the one before it. So the gap is the **threshold for speaking**, not perception. Under "speak only where a good collaborator would", the model stays as silent as the session's own AI.
- **Best version.** Both watchers moved to the newest version once it appeared, though the user's later feedback listed what it had lost. "Newest reviewed" beat "best" here.
- **Audit.** No agent read anything beyond its listed screenshots.
- **Cost.** 2.42M tokens for 40 agents. Each workflow agent carries about 40K tokens of fixed prompt (cached), so plan at least 50K per agent.
- **Graded rerun (approved by the user, same day).** The screenshot watcher ran again with two 0-10 scores per point: "a fresh session would help" and "stepping back would help". The bar, fixed beforehand, was rank agreement (AUC) of at least 0.80.
  - **Result: AUC 0.58** (exact permutation p 0.30), so it fails. Scores sat at 1-3 almost everywhere.
  - **The one clear rise came where the user asked outright** whether to start fresh. "Stepping back" rose slightly during the side errands, on marked and unmarked messages alike.
  - **The best version again moved to the newest.** Cost 1.24M tokens; audit clean. Total for the replay: 3.66M.
- **Reading, not decided.**
  - **Nothing systematic recovered the user's marks**, from the session alone, with neutral instructions: no fixed rule, and no watcher, whether deciding or scoring. A watcher noticed the cues (side errands, a version the user praised) but did not weigh them as the user does. It responded only when the user said it.
  - **What the marks encode looks like the user's own working style**: split side errands into their own session, and keep the version they liked even when a newer one is "reviewed". The session alone doesn't show that.
  - That would make it a per-user setting or profile, learned from the user's feedback, rather than a general rule. **Untested.**
  - **Next, per the approved plan's fail branch:** ask the user which cue they used at each marked point. Then test any profile built from those cues on a different session, not this one.
- **The user's cues (same day; answers in GOAL.md §1).** The marks fall into two groups:
  - **Early marks: a side topic** that didn't serve the session's goal. Each should have been split into its own session.
  - **Later marks: the session had got long**, together with "the work had peaked" or "a phase was done".
  - The user's view: "some watcher can tell by session being too long and knowing the goal". Could a watcher know without knowing them? "Some of each".
- **The best-version mark is weak.** The user called it "just a feeling", made from screenshots rather than the full site. So it should not gate a pass until the full version can be seen.
- **A blind spot in the replay.** The watchers saw a condensed transcript: about 47K characters, with each AI reply capped. The real session ran 9 days and reached about 790K tokens of context. "Long", the user's most frequent cue, was hardly visible to them.
- **Next test (proposed, needs the user's OK):**
  - **The watcher gets the real session size each turn:** context used, days elapsed, AI actions so far.
  - **It is told the two triggers in general terms:** offer to split off a side topic that doesn't serve the goal; suggest a fresh session when the session is long and the work has peaked or a phase is done.
  - **It runs on a held-out session the user marks first.** The website project has none: its other long sessions are branches sharing 14-16 turns with this one. The candidate is Northstar's own long exploration session (15 messages, Oct 8-15), which the user ended by moving to a fresh session.

**Held-out test (run 2026-10-23; the user's last test before consolidation).** A size-aware watcher read Northstar's long exploration session. It had the same instructions, plus the real session size each turn and the user's two triggers in general terms. The bar was fixed before the user marked the session: 16 points, 6 scored "fresh" marks and 9 "continue".

| Arm | Spoke at | Hits (of 6) | False alarms (of 9) | AUC |
|---|---|---|---|---|
| Size-aware watcher with the user's triggers | 2 points | 1 | 1 | 0.52 |
| Rule: the user returns on a new day | 3 points | 3 | 0 | n/a |
| Rule: context past half the window | 1 point | 1 | 0 | n/a |
| The session's own AI | none unprompted | 0 | 0 | n/a |

- **It fails.** It hit 1 of 6 (the bar was at least 5) and scored below the new-day rule. AUC 0.52 is chance.
- **It tracked length, not the user's moments.** Its "fresh" score rose steadily with session size, from 1 at the start to 8 at the end. Its two notes were well argued: one matched a mark, the other came where the user said "continue".
- **Quality judgments drove the marks.** The user's notes on this session's marks point to judging the work itself: weak results from earlier rounds, "Research maybe", "Looks like you start breaking things now".
- **Cost 0.98M tokens; audit clean.** The whole focus probe cost 4.64M tokens.

**What the focus probe showed (a reading for the design, not decided).**
- **No watcher recovered the user's moments from the session alone.** That held with neutral instructions, graded scores, and the session's size plus the user's own triggers. The user's doubt ("I am not sure if there is a systematic way to determine this") held.
- **The moments rest on the user's judgment:** whether a side topic belongs here, whether the work has peaked, whether results are getting worse. The session shows the cues but not the judgment.
- **The one systematic signal: returning after a break.** The user coming back on a new day coincided with 5 of 13 marks across both sessions, with 1 false alarm. A break is also when a fresh session costs least.
- **To weigh in the design review:**
  - Focus would not infer the moment. It would offer a light check at natural breaks, and make "start fresh with the goal and the best version" one move whenever the user asks, as they did in both sessions. Firmness stays a setting.
  - This changes the confirmed HOW "judges whether the work is still getting better" (GOAL.md §2), so it goes to the user as a question, not a decision.

## 3. Hypotheses to explore next

**AI side: fresh answer first, memory second.** This is the user's idea (2026-10-14). The AI answers without memory, so its creativity is untouched. A separate pass then adds what memory contributes, either at the end or in parallel, followed by a synthesis. The pass would cover:
- a conflict with a decision the user made;
- a ruled-out option coming back;
- a link to a prior conclusion, including from another context, as in the interview vs real-build example;
- what the user need not re-explain.

Arms to test, judged by the user blind:
- fresh only;
- fresh plus a memory addendum;
- fresh and memory synthesized;
- memory in the prompt (the current approach).

Hook surfaces (Claude Code, Codex) can run the second pass natively. Chat apps would need a one-pass approximation.

**Tested in round 4 (§2). Next round, under the user's 2026-10-15 answers:**
- **Baseline:** the user's real apps as they normally use them, with Northstar added on top. Record the model behind every reply, and run outside this project's memory index. Claude Code can do this today: a prompt hook adds the records as plain context. The chat apps would need a memory tool.
- **Messages:** the user's real first messages from the inbox, on and off Northstar, with the selector run end to end. Include cases where the right output is the unchanged fresh reply, and one long chat for in-session focus.
- **Arms**, none with usage rules or visible memory talk:
  - plain background: the records only;
  - memory as a tool the model calls when it needs it;
  - a gated, silent merge: the pass must quote the fresh sentence it would change, or the fresh reply is shown unchanged. It never adds lines about the user and never deletes fresh content.
- **Drop:** "skip what the user already knows", the labelled opener, and one-pass in its Part 1/Part 2 form.
- **Records:** store where each record was learned, separately from its claimed scope, and pass its still-forming status. Widen scope only after a second context (a setting, per the user's default).
- **Ranking page:**
  - The user picks a top reply, then marks the rest "about equal" or ranks them.
  - Shuffle the order of replies and sets.
  - Don't say which reply has no memory.
  - Add a one-tap reason: better content, presumes my context, repeats me, generic, too long.
  - Use fewer replies per set and more sets.
- **Judges:** none choose between arms until they are calibrated on the user's top picks and notes.

**AI side: in-session focus. Never probed before; confirmed by the user on 2026-10-15** (GOAL.md §1, §2). Rounds 1 to 4 tested only the first message of a new chat. In the user's two real examples the AI forgot nothing. Instead, it followed each latest message and lost the goal the session existed for:
- in interview preparation, practice questions replaced "succeed in the interview";
- in a website redesign, small tweaks each looked fine, but the design got worse than the first draft.

Focus is a separate job from memory. Northstar holds the goal above the current activity and judges whether the work is still getting better. It speaks up rarely: to step back to the goal, to flag that things are getting worse, or to suggest a fresh session carrying the goal and the best version so far. It never rewrites answers. This automates what the user did by hand on Northstar: an authoritative goal document, and a fresh session when the work drifts.

Focus probe, in progress:
1. **Ground truth.** The user marks, on a timeline of their real long sessions, where a good collaborator should have spoken up and what it should have done. The first session is the website redesign, with the site's screenshots at each step. The interview-preparation chat follows once exported. Northstar's own sessions are too short for this (2 to 7 messages each).
2. **Replay.** Candidate watchers read each session turn by turn, seeing only what was known at that point, and decide whether to speak up and what to say. The candidates:
   - the model alone;
   - a watcher that holds the stated goal outside the chat;
   - the same watcher plus the user's memory;
   - possibly one that compares the current state with the best version so far, for example through screenshots.
3. **Measure.** Does it speak up near the user's marks and stay quiet elsewhere? The user also picks blind among the candidates' messages.

How firmly it speaks up is open: a note, a pause, or a setting. On hook surfaces (Claude Code, Codex) a watcher can run after every turn. The chat apps would need a lighter version.

**Human side: stop generating AI-prose formats; co-design instead.** Four prose formats failed for the same reason. The next step should start from the user, not from another generated format:
- When would they open it?
- What notes, documents or tools have they actually found helpful?

**Answered 2026-10-15 (GOAL.md §2).** The user wants a big-picture index of their ideas, closest to a map. They glance at it when preparing or checking a decision. An AI assistant expands an entry for the problem at hand, and entries point to their actual work. The earlier "lighter reading view" possibility is now the confirmed direction. The user asked us to explore the best form. Questions to explore next:
- What a glanceable map of one person's ideas looks like when the big picture comes first, and how it shows conflicts across contexts.
- How an AI assistant expands an entry for an open-ended problem without falling back on fixed explanations (this joins up with the AI-side fresh-first work).
- How to capture and link "anything I got my hands on" (code, diagrams, documents, decisions), not only chats. Pictures of their actual work are one format the user has found helpful.

Show the user sketches early. Don't build full formats until a sketch lands.

**Sketched 2026-10-15: three map shapes, all rejected for their shape.** Research is in [`research/round4/20-index-expansion-capture.md`](research/round4/20-index-expansion-capture.md); the sketches and data stay in `~/northstar-probe/out/hv1-*`.

Where the user's actual work lives (their answers):
- Code: personal GitHub, local folders and a work Git server, but mostly inside AI tools.
- Notes: few.
- Diagrams and images: inside documents or repositories.
- Scope: personal material only for now.

Three rough sketches used the kept round-1 items plus real work on this Mac: two other personal repositories, Northstar documents, review pages, AI sessions and one screenshot. The sketches were:
- a topic map: themes, with lines for connect, conflict and replaced;
- a position map: how far an idea reaches against how settled it is, with project-only decisions folded away;
- a work map: projects as metro lines over time, with ideas as stations.

Any idea could be expanded for a sample situation.

What the user said:
- Verdict: "None I guess, all looks unhelpful."
- Why: asked what made them unhelpful, the user picked **the shape**. A map of ideas doesn't help them recall, even with the right ideas. They did not pick the content.
- Expansions: "Partly, like reference with session path doesn't really help, it is just a path string to me."
- Work references: a useful one **shows what they did there** (the key lines, the diagram, the result) and gives **one line on what it shows**.
- Links the AI spots in their work but they never stated: shown only once they confirm.
- Where the view lives: "You decide."
- Permission: the next sketch may use their other personal repositories and AI sessions.

This fits the research. No study supports glancing at an AI-made map of someone's ideas. Maps help the people who build them, and recall by place or thumbnail works for a person's own items. That matches the user's own report that diagrams and images help when they are their actual work.

**Hypothesis for the next round. It changes the confirmed "map" HOW, so it needs the user's OK before it is built.** Invert the index:
- Entries are the user's actual work, shown concretely: a diagram, a screenshot, the key lines or a result.
- Each entry has one line on what it shows or decided. Ideas become captions and links, not nodes.
- Expansion happens in the assistant, where chat stays central. It is written fresh from the problem, the user's items and their work, with those sources kept visibly apart.
- No path strings.
- Build it from content beyond Northstar, so that content and shape are not confounded.

**Sketched 2026-10-15, round 2: work first.** The user approved the inverted index before it was built. Both sketches used only non-Northstar content: the website redesign (its diagrams, and the first draft beside demo 4a), Logic Foundry's first result, and the user's own brief and note, with their words as captions. Sketches and data stay in `~/northstar-probe/out/hv2-*`.
- A, inside an assistant reply while preparing for an agent design interview: a fresh answer, four work cards, then lines tagged "you said", "your work" and "fresh".
- B, a work wall: nine tiles in rows by where the work lives, idea chips that light up the work behind them, and a list of what the value threshold left out.

What the user said:
- Pick: A, "inside the assistant", but "ONLY if the assistant you meant like ChatGPT or Claude, not a self created one". They assumed the wall would be fixed; if it stays current they "would probably work on both, still towards assistant as I can ask questions".
- Compared with the three maps: "Much closer". Why: seeing their real work brings it back, and one line per item is enough.
- The three source tags: "Too busy". The left-out list (taste, one-off decisions): right. Where it lives: "In the assistant, when I ask".
- In their words: "human version should have its own structure and only for revisiting, not for generating new ideas. I would still love to have a data/knowledge structure for human side, and a nice overall display format just like the maps in the last version, but better and smarter, this requires researchs."
- For that display they picked big picture first, connect and conflict lines, and grouping by topic. They did not pick "work as the entries". What the assistant should give back for a problem: "I am not sure yet".

Reading, for the next round (not decided):
- Work is how the user recalls, not how the overview is organized. Real work with one line each sits under a topic overview that shows where ideas connect or conflict. The earlier "None… the shape" rejected those three maps, not an overview as such.
- The human view revisits; it does not generate. Sketch A's fresh lines belong to the ordinary answer (the AI side). Whether expanding an entry for a problem counts as revisiting is open, and it touches GOAL.md §2's "Depth" row.
- Next: research a human-side knowledge structure (its topics, links and conflicts, and how the AI maintains them) and a smarter overview over it, with the user's work as the recall layer.

**Capture** (research note 20, §3):
- Treat "got my hands on" as an evidence ladder: authored, committed or decided is strongest; AI-session edits are weaker; merely viewed is weakest.
- Keep a local, append-only ledger of pointers (stable ID, content hash, label, permalink), because vendor activity feeds expire.
- Copy AI-session logs before Claude Code's 30-day purge.
- On iOS, capture is explicit only, through Share or Shortcuts.

**Value and scope.** The user's starting defaults, as settings:
- leave project-only knowledge to each product's own memory or project files;
- a principle becomes personal only once it appears in a second context;
- Northstar keeps a small working-style profile;
- showing memory use in chat: undecided.

Testing the value threshold needs chats on topics other than Northstar.

**Rules.** Fixed code rules only for safety and trust; model judgment for meaning; thresholds tuned from the user's own data and corrections (agreed in discussion on 2026-10-10).

## 4. Limits of the evidence so far

- All probe chats are about one project: designing Northstar. That makes value, scope and format tests weak. The user has been asked for a few chats on other topics, for example agent building for interviews and for real projects. The inbox was still empty on 2026-10-15, so the value threshold has not been re-run.
- Rounds 1 and 3 had only 9 blind pairs with memory, plus one general-vs-none pair. Judges and replies came from the same model family, and replies were generated directly, not through the real apps.
- Round 4 had one rater, 6 sets and one sample per arm. Display order filled most ranks below each top pick. Sets came in a fixed order, with the two Northstar sets last. The page said one reply had no memory. Replies came from a role-play prompt with no tools and about 250 words, possibly with this project's memory index in context.
- One review-page bug (all four formats displayed at once) cost one round of ratings. It was fixed and re-rated.

## 5. Documents

| Path | What it is |
|---|---|
| [`GOAL.md`](GOAL.md) | Authoritative goal, with the user's verbatim answers through 2026-10-24 (round 2) |
| [`research/round3/`](research/round3/SYNTHESIS.md) | Research on formats, practice and tools, processing jobs, value threshold and scope, and memory injection |
| [`research/round2/`](research/round2/SYNTHESIS.md) | Research on integration surfaces, drift, knowledge structure, robust maintenance and the memory-layer landscape |
| [`research/round4/three-jobs-analysis.md`](research/round4/three-jobs-analysis.md) | The three-job framing (focus, memory, maintenance): how the jobs fit over one core, what each has shown and not shown, gaps, what to test next and open questions (2026-10-15) |
| [`research/round5/`](research/round5/) | Prior art for the focus job (21); product facts per surface, checked 2026-10-23 (22); memory architectures and dreaming (23); evidence for focus speaking through the AI (24) |
| [`research/round6/`](research/round6/26-best-form-synthesis.md) | How to show the user their overview: the first pass (25), the deep research on the best form (26a–26d) and its synthesis (26), and the findings page |
| [`design/revision-2026-10-23/`](design/revision-2026-10-23/DESIGN.md) | **The current proposal**: the three-job design over one memory architecture (DESIGN.md) and its review page (review.html). Approved with changes twice on 2026-10-24; round 3 answered 2026-10-25; revision 3.2 current; the sketch round's brief is `overview-sketch-round.md` |
| [`design/`](design/README.md) | **Earlier proposals**: ARCHITECTURE.md, the 2026-10-09 revision documents, the review record, foundations and component specs. Useful as a component library (connector facts, maintainer robustness, platform analysis), not as the current design |

## 6. Local only: the probe workspace

`~/northstar-probe/` sits outside the repo and is private to the user's account.

| Path | What it holds |
|---|---|
| `inbox/` | Where the user drops chats: pasted `.txt` files with `Me:` / `AI:` markers, or ChatGPT and Claude export zips |
| `data/` | Parsed conversations, one JSON per chat |
| `out/` | Probe results (`r1-*`, `scale-*`, `r3-*`, `r4-*`), the user's answers (`*-user-answers.txt`) and the review pages. Round 4: `r4-results.json`, `r4-answer-key.json`, `r4-review.html`, `r4-user-answers.txt`, `r4-analysis.json`. Focus probe: `focus-mark.html`, `focus-img/` (screenshots of the user's site from the session) |
| `tools/` | Parsers (`parse_sessions.py`, `parse_inbox.py`), review-page builders, analysis, and the probe workflow scripts |

`.claude/launch.json` defines `probe-review`, which serves `~/northstar-probe/out` on `localhost:8765` for the browser pane.

## 7. Open questions for the user

1. ~~A few chats on topics other than Northstar, in `~/northstar-probe/inbox/`.~~ Now item 8.
2. ~~For the human view: when would you open it, and what have you actually found helpful?~~ Answered 2026-10-15 (GOAL.md §2).
3. ~~Shall the next probe test "fresh answer first, memory second"?~~ Done in round 4 (§2). The user's answers are in GOAL.md §2 (2026-10-15).
4. ~~Where does the user's actual work live?~~ Answered 2026-10-15 (§3, "Where the user's actual work lives").
5. ~~The five questions of the revised design.~~ Answered 2026-10-24 (GOAL §1, §2).
6. ~~Q6–Q8 of revision 2.~~ Answered 2026-10-24 (GOAL §1, §2).
7. ~~Q9–Q13 of revision 3.1.~~ Answered 2026-10-25 (GOAL §1, §2); the phone's place is still open ("not sure yet").
8. New (2026-10-25): a few chats on other topics in `~/northstar-probe/inbox/` for the sketch round (replaces item 1).
