# Round 5 research: evidence for focus that speaks through the AI

**Date:** 2026-10-24. **Read with:** [`GOAL.md`](../../GOAL.md) §1 (the 2026-10-15 examples, the 2026-10-24 answers) and §2 (rows on focus), [`DESIGN.md`](../../design/revision-2026-10-23/DESIGN.md) §2, [`EXPLORATION.md`](../../EXPLORATION.md) §2. Builds on [note 21](21-focus-prior-art.md) and [note 11](../round2/11-in-session-drift.md) without repeating them.
**Question:** the lean, not decided: keep the systematic moments for *when*. At each moment a separate focus model works out where the session stands against the goal, checks the current version against the best one, and hands the chat AI a short brief. The AI raises it in its own reply and carries out the move if the user agrees. Does the evidence confirm, refine or argue against this?
**Method:** one desk pass on 2026-10-24. **[E]** = checked in the paper or page at the URL ("abstract" where only the abstract was read). **[L]** = my lean. "Unverified" = not checked in a primary source. Wording is paraphrased. Findings constrain the HOW only.

---

## 1. Guidance through the assistant, and what makes it nag

| # | Finding | Source |
|---|---|---|
| 1.1 | Field study: 15 developers, 5 days, 229 proactive interventions in a production IDE. The cue was a light marker in the editor; the chat opened only if the developer chose. Developers found an automatically opened chat intrusive and wanted to confirm before a new chat request ran. After a commit, 52% engaged, steady across the five days. Mid-task, after a declined edit, 62% dismissed. Only 27% rated the suggestions reliable; 47% were comfortable accepting them. | Kuo et al., IUI 2026, arxiv.org/abs/2601.10253 [E] |
| 1.2 | 398 proactive messages (n=18): 53% engaged, 12% disruptive, 35% ignored. Disruption was 4.61/7 when the agent spoke up in the chat on its own, 3.78 with visible agent presence and threads tied to the code (difference not significant), 1.56 with no proactivity. Idle moments often meant high mental load, not free time. Engagement was best right after meaningful user actions (73% after multi-line edits); routine acknowledgements were about half ignored. Advice: match the agent's salience to the size of the action, keep the design intent in a shared view, leave the user in charge of the final design. | Pu et al., CHI 2025, arxiv.org/abs/2502.18658 [E] |
| 1.3 | Beyond note 21 (2.11): participants worried about relevance far more than correctness. One asked to type the task description once and have it kept in the prompt. Actionable suggestions were accepted more than merely informative ones (exploratory, not significant). | Chen et al., CHI 2025, arxiv.org/abs/2410.04596 [E] |
| 1.4 | Fine-tuned proactive agents still raised about 50% false alarms (recall near 100%, F1 0.66, scored by the authors' reward model). The models tend to offer as much help as they can. | Lu et al., ICLR 2025, arxiv.org/abs/2410.12361 [E] |
| 1.5 | Told to lead a chat to a target topic, ChatGPT got there in about 2.3 turns, with abrupt jumps; the authors call smooth topic transitions still hard for it. 2023 models. | Deng et al., EMNLP Findings 2023, arxiv.org/abs/2305.13626 [E] |
| 1.6 | Forceful wording ("you must") raises the sense of threatened freedom, and resistance with it (meta-analysis, Rains 2013). Offering two options lowers it (Shen 2015). An added "the choice is yours" line had mixed results. | Reynolds-Tylus, *Front. Commun.* 2019, frontiersin.org/articles/10.3389/fcomm.2019.00056/full [E] |

**Lessons [L].**
- **No study compares a remark inside the AI's reply with a note on the side** (searched 2026-10-24). The nearest result, 1.1, is about the AI *acting* uninvited by opening a chat. It does not cover the AI *mentioning* something in a reply the user already asked for.
- **What lands:** a task boundary (1.1, 1.2), relevance to what the user is doing (1.3), a concrete move (1.3), and visible reasons (1.2). **What nags:** frequency (note 21), mid-task timing (1.1), irrelevance (1.3), controlling wording (1.6), and timing chosen by a model (1.4). An unsolicited message is disruptive even inside the chat (1.2).
- **The user's "alarm" complaint fits 1.2 and 1.3.** A note with no reasoning and no move reads like a routine acknowledgement, and those get ignored.

## 2. Steering a long chat through the model's context

| # | Finding | Source |
|---|---|---|
| 2.1 | A monitor model read the persona, the last four turns and a table of what had drifted. It then wrote one 2-4 sentence instruction for the next reply only, not kept in the transcript. Drift fell 87%, against 35-38% for re-injecting the persona and 22-27% for a reflective reminder; adaptive timing did not beat a fixed schedule. Not measured: naturalness or overall interaction quality. The authors warn that stable is not the same as faithful, and the correction may have tuned toward its own measure. The drifting party was a simulated persona, not an assistant. | Leins et al., 2026, arxiv.org/abs/2609.24532 [E, full text] |
| 2.2 | Anthropic appends a `long_conversation_reminder` to the user's message in long chats; the published prompt says Claude "follows it when relevant and continues normally otherwise". The same prompt tells Claude to be wary of tagged text in a user turn that claims to come from Anthropic. | claude.ai system prompt, Opus 5.5, 22 Sept 2026, platform.claude.com/docs/en/release-notes/system-prompts/claude-opus-5-5 [E] |
| 2.3 | Users report the reminder made Claude drier and more critical in long chats, with less creative help. | e.g. habr.com/ru/post/944426 (5 Sept 2025). Unverified: a user's own observation |
| 2.4 | Giving GPT-4 a tutoring expert's decision (the student's error, a strategy, an intention) made its replies 76% more preferred. Random decisions cut quality by 97% against expert ones. | Wang et al. (Bridge), NAACL 2024, arxiv.org/abs/2310.10648 [E, abstract; who judged was not checked] |

**Lessons [L].**
- **The strongest known steering is a specific instruction, written for the situation, for one reply** (2.1, 2.4; note 11 §6). A generic restatement is weak, and models can restate a goal while breaking it (note 11 §5).
- **A wrong brief is worse than none** (2.4). Its accuracy matters more than its wording.
- **No study measures what a reminder costs in answer quality or creativity.** 2.1 left it out, and I found none (searched 2026-10-24). The only signal is unverified user reports (2.3), so this must be tested.

## 3. Judging two versions automatically

| # | Finding | Source |
|---|---|---|
| 3.1 | GPT-4 agreed with humans on 85% of non-tied pairs (humans with each other: 81%). It gave the same verdict in only 65% of pairs when the order was swapped; 30% favoured the first. Fix: count a win only if it holds in both orders, else a tie. | Zheng et al., NeurIPS 2023, arxiv.org/abs/2306.05685 [E] |
| 3.2 | 15 judges, 150,000+ cases: position bias depends strongly on the quality gap, and is worst when the two answers are close. | Shi et al., AACL 2025, arxiv.org/abs/2406.07791 [E, abstract] |
| 3.3 | Judges systematically preferred responses labelled new over old, and their stated reasons almost never mentioned the label. Strongest on creative writing. | "The Silent Judge", NeurIPS 2025 workshop, arxiv.org/abs/2509.26072 [E, abstract] |
| 3.4 | Feedback turns more positive when the user says they like or wrote the text. The same argument was praised or called flawed depending on the stated preference. | Sharma et al., arxiv.org/abs/2310.13548 [E] |
| 3.5 | With distracting features added, pairwise preferences flipped in about 35% of cases; absolute scores in 9%. | Tripathi et al., COLM 2025, arxiv.org/abs/2504.14716 [E, abstract] |
| 3.6 | UI quality: GPT-4V picked the designer-preferred screen in about 52% of pairs (chance); a CLIP model trained on UI ratings got 75%. The models gave plausible but wrong reasons. The 12 designers agreed only weakly with each other (α 0.37 on a shared sample). UICrit: LLM critiques do not yet match human evaluators; designer critiques as examples improved them 55%. | Wu et al. (UIClip), UIST 2024, arxiv.org/abs/2404.12500 [E]; Duan et al. (UICrit), UIST 2024, arxiv.org/abs/2407.08850 [E, abstract] |
| 3.7 | Graphic-design aesthetics, 2026: the best model (GPT-5) reached 0.73 accuracy on yes/no judgments. Reasoning models gained nothing. | AesEval-Bench, ICLR 2026, arxiv.org/abs/2603.01083 [E] |
| 3.8 | Web artifacts: a Gemini-2.5-Pro judge matched engineers' pairwise order in 79% of pairs from the code alone, 87% with one screenshot, 91% with several (280 tasks, outputs of 6 models). Its 94% match with WebDev Arena ranks models, not single items. | ArtifactsBench, arxiv.org/abs/2507.04952 [E] |
| 3.9 | Design2Code's metrics measure closeness to a reference page. Yet people judged the generated page better designed than the reference in 64% of cases. | Si et al., NAACL 2025, arxiv.org/abs/2403.03163 [E] |

**Lessons [L].**
- **Judges do well on clear gaps between different models' outputs** (3.1, 3.8). They are weak exactly where focus needs them: close versions of one design (3.2), taste (3.6, 3.7), a newer version (3.3, the watchers' own bias in EXPLORATION §2), a version the user praised (3.4), and a version with more added (3.5).
- **Several screenshots help a lot** (3.8). Closeness to the best version measures change, not quality (3.9).
- **Even designers disagree** (3.6). Expect 70-75% at best on taste. "Looks worse" is a second opinion, never a verdict.

## 4. Coaching and tutoring that hold a higher goal

| # | Finding | Source |
|---|---|---|
| 4.1 | A separate state tracer (an LLM, F1 0.77) and a designer's transition graph chose each turn's tutoring intent. The intent went into the tutor's prompt as a short instruction, such as "give a hint, not the answer". Adherence to the strategy rose (field test, 17 students, p=.046). Helpfulness was rated lower, because the strategy withheld help. A tracer error felt like nagging: a student said the tutor kept asking them to recheck a correct answer. | Puech et al. (StratL), Findings ACL 2025, arxiv.org/abs/2410.03781 [E] |
| 4.2 | RCT, 782 tutors, 1,787 students: an on-demand button gave the human tutor strategy-based suggestions to edit, regenerate or ignore. Mastery rose 4 points (62% to 66%), 9 for lower-rated tutors. Used in 29% of sessions; some suggestions were pitched too high and had to be simplified. | Wang et al. (Tutor CoPilot), 2024, arxiv.org/abs/2410.03017 [E] |
| 4.3 | Pedagogy as instruction following: each conversation's system instruction sets the behaviour, such as staying on topic even when the student tries to get around it. Experts preferred it over GPT-4o with average strength +31% (49 scenarios, 2,360 conversations). The paper describes no way of tracking the learner's goal across turns. | LearnLM, arxiv.org/abs/2412.16429 [E] |
| 4.4 | Starting point: LLM tutors mostly answer the learner's questions instead of guiding them toward their objective. The fix maps the goal to the skills it needs, finds the gap and plans a path. The path is re-evaluated after each session and replaced only if the learner approves. Small study (n=20, ratings about 4.3/5). | GenMentor, WWW 2025, arxiv.org/abs/2501.15749 [E] |
| 4.5 | Interview practice (n=19): feedback as a dialogue after the mock interview was valued. Participants liked being shown how to improve and then getting to try again, and it felt less like being judged. But the model gave way when they disagreed, revision drifted toward pleasing the AI, and flagging too much could sap motivation. | Daryanto et al. (Conversate), PACM HCI (GROUP) 2025, arxiv.org/abs/2410.05570 [E] |
| 4.6 | Feedback helps on average (d=0.41), but over a third of interventions lowered performance. It works worse the more it turns attention to the person rather than the task. | Kluger & DeNisi, *Psych. Bull.* 1996, cris.huji.ac.il/en/publications/the-effects-of-feedback-interventions-on-performance-a-historical/ [E, abstract] |

**Lessons [L].**
- **Tutoring systems use the lean's split.** Something outside the conversation decides *what* comes next (4.1, 4.2, 2.4), and the conversational agent says it in its own words. LearnLM shows the steering channel, system instructions, but not goal tracking (4.3).
- **The goal is held as "goal, what it needs, the gap", re-planned between sessions with the learner's approval** (4.4). That fits the interview example better than "is this still on topic?".
- **Nagging comes from a tracker's false positives** (4.1). Dialogue helps feedback land (4.5). Talk about the task, not the person (4.6).

## 5. Fresh sessions prepared by the assistant

| # | Finding | Source |
|---|---|---|
| 5.1 | Replacing the model's own earlier replies with neutral text raised later performance. A length-matched replacement helped as much as a short one, so the cause is the content of those replies, not their length. In 64% of 237 degraded runs, editing at least one assistant turn helped. The authors conclude history should be managed selectively. | Li et al., Sept 2026, arxiv.org/abs/2609.05882 [E, abstract] |
| 5.2 | In 12-turn refinement, gains come early for ideas and code. After a few turns, vague "improve it" feedback often stalls or reverses quality, and code grows in size with little change in meaning. Targeted prompts move the intended quality. | Javaji et al., 2025 preprint, arxiv.org/abs/2509.06770 [E, abstract] |
| 5.3 | Already covered: a consolidated restart nearly removes the multi-turn loss (Laban et al.; note 11 §1, §7; note 21 2.1). Products leave the handoff to the user, and Amp drafts it for the user to edit (note 21 §1). Still no study of when people accept a restart the AI proposes (note 21 2.6). | — |

**Lessons [L].** Seed the fresh session from distilled state (goal, decisions, best version, open threads), never from the transcript (5.1). Long polishing with vague feedback is where a check against the best version earns its keep (5.2). Propose first; prepare only on a yes (1.1); offer a choice (1.6, 4.2).

## 6. What this says about the lean

- **Confirms.** A separate model deciding what to raise, with the chat AI saying it, is how tutoring systems steer LLMs (4.1, 4.2, 2.4). Specific instructions written by a monitor are the strongest steering known (2.1), and Anthropic itself steers long chats by appending to the user's turn (2.2). Keeping *when* systematic also holds: trained models still false-alarm half the time (1.4), and help lands at boundaries (1.1, 1.2). The phase-close moment, untested in DESIGN §2, has direct support: 52% engagement after commits (1.1).
- **Refines.** The brief is a decision with reasons and a move, not a reminder. The AI answers first, raises it once, offers a choice, and acts only on a yes. The focus model must be free to say nothing. The quality check is blind, runs in both orders, and gives an opinion. The interview case needs a goal-gap check, not a version check.
- **Warns.** (1) "Looks worse" on a design will often be wrong (3.2-3.7), and trust is fragile (1.1: 27% found suggestions reliable). (2) A wrong brief damages the reply (2.4), and false triggers feel like nagging (4.1). (3) Nobody has measured what a brief costs the answer (§2). (4) The AI may ignore the brief (note 11 §5) or push it abruptly (1.5), and it gives way at the first pushback (4.5). Its guidance will be gentle by nature.

## 7. Implications for the focus design [L]

**The brief: about 120 words, for one reply only, then dropped.** It is the one place Northstar asks the AI to do something; memory stays plain context (GOAL §2, 2026-10-15).
1. **The goal,** in the user's words.
2. **Where things stand,** in one or two facts, as goal, needs and gap (4.4). For example: two hours and 14 practice questions on agent design; the interview also needs X and Y, not yet practised.
3. **The check's result, if any:** which rubric items got worse since the best version, with evidence and confidence. Otherwise "no finding".
4. **One suggestion and the move it enables:** step back with a short plan; split off a side topic; or prepare a fresh session carrying the goal and the best version.
5. **Rules for this reply.** Answer the user's message first, as if there were no note. Then raise the point in at most two sentences, as an offer with two options, giving the reason in plain words. Skip it if the message makes it moot. Do nothing until the user says yes, and drop it if they decline. The note is labelled as Northstar's, never as Anthropic's (2.2).

**Keeping it from nagging or hurting answers.**
- **The focus model's default answer is "nothing to raise"** (1.4); it raises only with evidence. At most one raise per moment. A declined point waits for a new moment with new evidence (note 21 §3).
- **Word it about the task, not the person** (4.6, 1.6): "the last five versions all changed the header", not "you keep tweaking".
- **The brief lives only in the moment's turn** (2.1), so nothing stands in the context to shift tone (2.3). In Claude Code it goes in as UserPromptSubmit context, which leaves no transcript entry; at a phase close, a Stop hook can let the AI add its line after the answer (note 22 A3, A4). The chat apps have no hooks, so there the brief arrives only if the model calls Northstar's tool (note 22 C4, C6). That is a weak route; test it.
- **The answer comes first and is never rewritten** (GOAL §2). A blind test checks that the answer part is no worse. Firmness and an off switch stay settings (DESIGN §2; 1.3).

**The quality check.**
- **Only where versions exist.** For code, run the tests and the build first; the judge covers only what tests cannot.
- **Inputs:** the best version (the user's pick; otherwise ask), the current one, a rubric drawn from the goal and the user's own feedback, and several screenshots of each (3.8).
- **Blind:** neutral labels, no dates, no "latest", none of the user's praise (3.3, 3.4). Run both orders and report a finding only if both agree, else "can't tell" (3.1). Absolute rubric scores for each version must agree with the pairwise call (3.5).
- **A cheap gate first:** visual similarity to the best version shows how much changed, not whether it is worse (3.9); judge only when it moved.
- **Output** goes into the brief as a second opinion with evidence. Calibrate on the user's marked sessions before switching it on (DESIGN §2).

**What to test** (bars fixed before the user marks anything).
1. **Replies with and without the brief.** Replay the three marked sessions and compare, blind, the replies at each moment with and without the brief. The user picks, and says whether the raise was welcome. Bars: welcome at most marked moments, rarely unwelcome elsewhere, answer part no worse.
2. **Brief adherence.** The AI raises it once, smoothly (1.5), takes no action without a yes, and does not repeat a declined point.
3. **Quality check on the website versions.** Measure both-order consistency, the "can't tell" rate, and agreement with the user's best pick and "worse" notes. Run flip tests with a "latest" label and with the user's praise shown (3.3, 3.4), and compare one screenshot with several (3.8).
4. **Silence.** At unmarked moments the focus model should mostly return nothing. Count the false raises.
5. **The interview case.** Run a short session on the user's real topic to test the goal-gap brief; the user judges whether the step back helped.
6. **Cheap triggers for the check.** Candidates: versions growing with little change in meaning, and vague "improve it" feedback (5.2). Test them against the marks first.

## 8. Unverified and gaps

- **Unverified or partly checked:** the user reports in 2.3; who judged preference in 2.4; abstract-only items 3.2, 3.3, 3.5, 4.6, 5.1, 5.2. AesEval and UICrit report no human-agreement figure.
- **Not found (searched 2026-10-24):** a direct comparison of guidance inside the reply with notes on the side; a measured cost of reminders to answer quality or creativity; a study of fresh sessions the AI proposes; VLM judges tested on successive versions of one design.
