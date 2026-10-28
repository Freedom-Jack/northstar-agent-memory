# Round 6 research (26a): getting back to your own information and work

**Date:** 2026-10-27. **Read with:** [`GOAL.md`](../../GOAL.md) §1 and §2 (the human-view rows of 2026-10-15, 2026-10-24 and 2026-10-27); note [25](25-overview-display.md); note [20](../round4/20-index-expansion-capture.md); note [23](../round5/23-memory-architecture-and-dreaming.md) §4; [`DESIGN.md`](../../design/revision-2026-10-23/DESIGN.md) §6; [`overview-sketch-round.md`](../../design/revision-2026-10-23/overview-sketch-round.md), Result. Builds on them without repeating them.
**Question:** what does published evidence say about how people get back to their own information and work? Which forms does it support for the overview's three needs: (1) see the big picture of what I think and know; (2) get back into a piece of work; (3) answer a question about my own past?
**Slice:** one of four parallel notes: re-finding, task resumption, lifelogging, and asking versus browsing.
**Method:** one desk pass on 2026-10-27. **[E]** = a source shows it; papers were read today unless marked "abstract" or "secondary" (seen through another paper or a summary). **[L]** = my inference. **Unverified** = seen only in a search summary or slides. Findings constrain the HOW only (GOAL §5). No personal data was read.

**Short answer.**
- People get back to their own things mostly by going to a place they know, in small steps. Search wins in big unsorted piles such as email. People remember an item's topic and purpose far better than its date [E].
- To resume work, the best-supported cue is the work as it was left: its last state and the last few steps, in order. The goal or next step you set comes second. A summary is quickest to read but drops detail [E, small or lab studies].
- Records of the past are used to retrieve and relive more than to reflect. Pictures of your own activity bring back the episode; location data helps people infer what happened [E].
- For a question about your past, asking is quicker. But AI answers from memory were right only 58% of the time in one pilot, citations can make wrong answers look right, and a chatbot can plant false memories [E].
- So the overview needs your ideas for the big picture and episodes of your real work for resuming and answering. It needs three ways in: browse, "where you left off", and ask, with each answer quoting your own record and its place [L].
- Evidence is moderate for needs 2 and 3 and weak for need 1. No study found tests an AI-made overview of one person's ideas, so the gap in notes 20 and 25 stands [E].

---

## 1. Re-finding your own things: place or query

| # | Finding | Source |
|---|---|---|
| 1.1 | Re-finding is common. In one year of Yahoo logs from 114 users, up to 40% of queries were re-finding queries. Changes to the result list between visits made re-finding harder. | Teevan, Adar, Jones & Potts, SIGIR 2007 [E, abstract] |
| 1.2 | People prefer small steps from a known place, even when they know exactly what they want. In 151 short interviews with 15 MIT computer-science graduate students over five days, only 34 of 81 searches for a specific item (42%) used keyword search, against 23 of 42 searches for general information (55%). The small steps cost less effort and kept a sense of where people were. They also helped people understand and trust the result, including accepting that something was not there. | Teevan, Alvarado, Ackerman & Karger, CHI 2004 [E; small, old, one population] |
| 1.3 | For their own files, people navigate more than they search (56–68% against 4–15%, self-reported; note 25 §2.4). In an fMRI study of 17 students retrieving their own files, folder navigation activated regions used in real-world navigation, and search activated left frontal language regions; success rates were similar. A logged field study also found search used as a last resort. | Bergman et al., TOIS 2008 [E, via note 25]; Benn et al., *Sci. Rep.* 2015 [E]; Fitchett, PhD thesis, and Fitchett & Cockburn, IJHCS 2015 [E, abstract; figures not read] |
| 1.4 | In email the picture flips. A field study of 345 long-term users and more than 85,000 re-finding actions found that people who built complex folders relied on them, but were no more successful and were slower. Search and threads worked better. Scrolling was the most common way to re-find. | Whittaker, Matthews, Cerruti, Badenes & Tang, CHI 2011 [E, abstract] |
| 1.5 | An index of everything a person had seen ("Stuff I've Seen") was used by 234 Microsoft employees for six weeks. Queries averaged 1.59 words; 48% used a filter; 25% named a person. Of 8,254 result lists, 5,037 were sorted by date and 2,038 by relevance, though half the users started with relevance as the default. 76% of opened items were email; 89.4% were from the last year. Previews often answered the need without opening anything. | Dumais, Cutrell, Cadiz, Jancke, Sarin & Robbins, SIGIR 2003 [E; old, one company] |
| 1.6 | What people remember when they re-find. 21 people re-found messages in their own university email. They remembered the topic in 85.1% of tasks, why it was sent in 80.9%, the sender in 77.1%, when it came in 57.5%, and attachments in 12.8%. Memory of the sender fell from 95.6% for messages seen within a week to 56.7% for the oldest group. When people describe documents as stories, time, place and purpose come up most, and keywords, times and locations are often half-remembered or wrong. | Elsweiler, Baillie & Ruthven, TOIS 2008 [E; small]; Gonçalves & Jorge 2004 and Blanc-Brude & Scapin 2007 [E, secondary via Elsweiler et al.] |
| 1.7 | Structure carries meaning. People's project folders mirrored how they broke a project into parts, and stood for their growing understanding of it. When an interface split material by format (documents, email, bookmarks), 20 users' project material split with it; when it allowed, they kept it together. Bergman and Whittaker build a design approach for personal information on three principles: subjective importance, project classification and context. | Jones, Phuwanartnurak, Gill & Bruce, CHI 2005 [E, abstract]; Bergman, Beyth-Marom & Nachmias, CHI 2006 [E, abstract]; Bergman & Whittaker 2016 [E, table of contents only] |
| 1.8 | Reminding matters. Bookmarks and history were little used. Emailing a link to oneself worked because it reminded and carried a note of why the link mattered. In a field study, highlighting the files a person was predicted to need, in place in the file browser, cut retrieval time from 12.2 to 10.6 seconds. | Jones, Bruce & Dumais, CIKM 2001 [E, abstract]; Fitchett, Cockburn & Gutwin, CHI 2014 [unverified, secondary summary] |

**Lessons.**
- [L] Navigation suits a small structure you know; search suits a big pile nobody sorted. The overview is the first kind, built on top of the second (chats). So browse the overview, and ask or search the archive. Do not make the person pick one route.
- [L] Label every item by what people remember: what it was about and why it mattered (1.6), then who was involved (the seller, the interviewer) and a rough time. A date is a filter and a sort order, not the label (1.5, 1.6; note 23 H.2).
- [L] Let the label answer. In 1.5 the preview often did the job. "One line per item is enough" (GOAL §2) fits, if the line carries topic and purpose.
- [L] The person should not have to file anything (1.4). The AI builds the structure and the person corrects it, as GOAL §2 already says. But the structure should follow the person's own projects and topics, and gather the chats, code and documents of one project in one place (1.7).
- [L] A quiet reminding function belongs in the view: open items, and "changed since you last looked" (1.8; note 25 §2.3).

## 2. Getting back into a piece of work

| # | Finding | Source |
|---|---|---|
| 2.1 | Goals fade while you do something else, and need cues to come back (the memory-for-goals model). In a lab task with 96 students, the first action after an interruption took 3.8 seconds, double the 1.9 seconds between normal actions. Seeing the task during the 8 seconds before an interruption shortened the return (marginal at 6 seconds, no effect at 2 or 4). With an 8-second warning, people rehearsed what they would do next and resumed faster. | Altmann & Trafton, *Cogn. Sci.* 2002 [E, cited in 2004]; Altmann & Trafton, CogSci 2004 [E; lab, seconds]; Trafton, Altmann, Brock & Mintz, IJHCS 2003 [E, abstract; lab] |
| 2.2 | In the field the costs are minutes and hours. Logs of 27 Microsoft workers over two weeks (2,267 hours): after answering an email alert, people spent on average 9 minutes 33 seconds before returning to any suspended application, then about 16 more minutes before the work was back in the state they had left it. 27% of alerts led to more than two hours away from the windows they had been working in. Suspended windows less than 25% visible took significantly longer to return to than windows more than 75% visible. People left cursor positions and highlights as cues for themselves. | Iqbal & Horvitz, CHI 2007 [E; field, one company] |
| 2.3 | 57% of "working spheres" were interrupted; most were resumed the same day, but after more than two other activities. In a one-week diary of 11 workers, tasks they had to return to were rated harder to switch to, were longer (120 against 45 minutes), used more documents (2.5 against 1.6) and had more interruptions (1.5 against 0.7). The authors judged that software supported the resumption of complex, long projects poorly. | Mark, Gonzalez & Harris, CHI 2005 [E, abstract]; Czerwinski, Horvitz & Wilhite, CHI 2004 [E; small] |
| 2.4 | Programmers rebuild context before working. In 10,000 recorded sessions of 86 programmers, only 10% resumed editing within a minute, and only 7% edited without first visiting other places in the code. 371 surveyed programmers relied on notes. In a lab study, two automatic cues each doubled the task success rate over notes alone: a timeline of the code snippets they had touched, and a summary of the code elements they had worked on most. Developers strongly preferred the timeline. | Parnin & Rugaber, SQJ 2011 [E, abstract]; Parnin & DeLine, CHI 2010 [E, abstract; that resumption speed did not differ is unverified, from slides] |
| 2.5 | Restoring a task's working set helps. 16 industry programmers used a tool that remembered which code each task involved and reloaded it when the task was reactivated. Over several weeks, compared with their own baseline, they spent significantly more of their time editing and less navigating. | Kersten & Murphy, FSE 2006, and its CSCW 2006 companion [E; field, volunteers, before and after] |
| 2.6 | Pictures of your own screen bring back the context. Six graduate students recorded two weeks of work (210 hours). Shown small stills of their own screen, they described the moment with 4.47 contextual details on average (who, what, where, when, why, feelings); 95% of these memories mostly or partly matched their reports on the day. Plain full-screen stills did as well as or better than crops or video. In a second study, 10 programmers, writers and designers resuming long tasks all kept to-do lists: lists helped them choose the next goal, and looking over the work turned up implicit cues. The authors advise showing pictures of the activity, not only abstractions, and highlighting connections, changes, and implicit goals and plans. | Rule, Tabard & Hollan, *HCI* 2017 [E; small]; Rule et al., CogSci 2015 [E, abstract] |
| 2.7 | Older findings agree. People recalled more of their day from time-lapse video than from text summaries. Memory for important computing events was fragile a month later, and people preferred snapshots to video. To recognise their own activity 80% of the time, four participants of 2.6 needed full-screen stills about 320 pixels tall (crops about 520; compare note 25 §2.1f). | Lamming & Newman 1992 [E, secondary via Rule et al.]; Czerwinski & Horvitz, HCI 2002 [E, abstract]; Rule et al. 2017 [E; n = 4] |
| 2.8 | A plan to resume helps. Across four studies, a short "ready-to-resume" plan made when switching away reduced attention residue, and performance on the interrupting task held up. | Leroy & Glomb, *Org. Sci.* 2018 [E, abstract] |
| 2.9 | A summary is fast but loses detail. 57 Microsoft employees caught up on a scripted 35-minute meeting they had missed, then wrote a summary email. The 33 with Copilot showed the largest speed gain in the report (across its studies, tool users took 26% to 73% of the control group's time). Their summaries held 11.06 of 15 key details, against 12.40 without Copilot. | Microsoft, *AI and Productivity Report*, 2023 [E; access was by division, not random; someone else's meeting] |

**Which cue works best: a summary, the last state, the artifact itself, or the goal?**
- **The artifact in its last state, with the trail that led there,** has the most support: visible suspended work (2.2), cues seen before the break (2.1), snippet timelines (2.4), restored working sets (2.5) and stills of one's own screen (2.6, 2.7). It brings back the cues present when the memory formed (note 23 H.1). [E, consistent across lab and small field studies]
- **The goal and the next step** come second. The goal is what fades (2.1); rehearsing the next step, a ready-to-resume plan and to-do lists help people choose what to do next (2.1, 2.8, 2.6). [E, moderate]
- **A summary** is the weakest resumption cue: quicker to read but missing detail (2.9), less preferred than chronological snippets (2.4), and weaker than images (2.7, secondary). [E, weak to moderate]
- [L] The best form combines the first two and keeps the summary as a label: what the work looked like when you stopped, the last few steps in order, what has changed since, and the next step or open question you stated.

**Lessons.**
- [L] Resuming is the need with the best evidence, but it comes from programmers and office workers, over minutes to weeks; none of it covers work done through AI chats. The mechanism should carry over; the effect sizes may not.
- [L] People will not re-read a long chat to resume. A short trail of their own steps across chat and work, in order, is the counterpart of the snippet timeline (2.4).
- [L] "Where you left off" is a different view from "what I think". It is organized by piece of work and by time, not by idea.

## 3. What people use records of their past for

| # | Finding | Source |
|---|---|---|
| 3.1 | Sellen and Whittaker name five uses of records of one's past: recollecting (re-living an episode), reminiscing (for its emotional value), retrieving (finding a specific item), reflecting (seeing patterns in one's past), and remembering intentions (things still to do). They found little evidence that lifelogs helped with any of them, and argued for selective capture of good cues instead of total capture. | Sellen & Whittaker, CACM 2010 [E, secondary summaries; the article page was blocked] |
| 3.2 | A wearable camera study (SenseCam): 19 students, 15 analysed, 10 retested after four months. Images of their own day improved recall of events they truly remembered, and of events they only knew had happened. They recognised their own images over 80% of the time, as well at four months as at three days, and could put only their own images in order. For remembered events, images the camera took on its own were better triggers than ones people chose to take, against the authors' prediction. The authors stress that such systems capture cues that trigger memory, not the experience itself. | Sellen, Fogg, Aitken, Hodges, Rother & Wood, CHI 2007 [E; small] |
| 3.3 | Images and location data help in different ways. Images prompted detailed, re-lived memories; location data prompted inference about what must have happened. | Kalnikaite, Sellen, Whittaker & Kirk, CHI 2010 [E, abstract] |
| 3.4 | People use a record only when it is quicker than their own memory. In a lab study, people traded accuracy for speed: they preferred quick access to possibly wrong information (their own memory) over slow access to correct information (the record). Use of the record depended on how good they judged their own memory to be, and on how easy the record was to use. | Kalnikaite & Whittaker, CHI 2007 [E, abstract; best paper] |
| 3.5 | A synthesis of several lifelogging studies proposed four principles: selectivity, embodiment, synergy with human memory, and support for reminiscence. | Whittaker et al., *HCI* 2012 [E, abstract] |
| 3.6 | Much of the camera evidence comes from memory-impaired people. A systematic review found 28 studies of wearable cameras and autobiographical memory. In five of six people with Alzheimer's disease, reviewing camera images brought back more details of an event over two weeks than a written diary did. | Allé et al., *Neuropsychol. Rev.* 2017 [E, abstract]; Woodberry et al., *Memory* 2015 [E, abstract; n = 6] |
| 3.7 | Meeting records do two jobs. Shared records act as an agreement on decisions and commitments; personal notes act as a private memory aid for actions and their circumstances. | Whittaker et al., MLMI, Springer 2006 [E, abstract] |
| 3.8 | With a wearable audio aid holding years of recorded conversations, people answered questions about past conversations, usually within minutes. | Vemuri et al., UbiComp 2004, and Vemuri's thesis [E, summary only] |

**Lessons.**
- [L] Across §1 and §3, retrieving and recollecting have the most evidence, and reflecting the least (3.1). Need 1, "see the big picture", is a reflecting job, so it rests on the weakest ground in this slice.
- [L] Two kinds of memory need two kinds of cue. A picture of the actual work brings back the episode (3.2, 2.6); a structure such as topics or places helps people infer and "know" (3.3, by analogy with location data). An overview of ideas by topic is a knowing view, yet both "Ask" questions in the sketch round were about episodes ("what did I do before …").
- [L] A few strong cues beat a complete record (3.1, 3.5), which supports the value threshold (GOAL §2) and one to three pieces of work per idea.
- [L] Speed decides use (3.4). If the overview is slower than remembering or asking the chat, it will not be opened, which fits the user's expectation to open it rarely (GOAL §2).
- [L] Decisions deserve their own list (3.7): what was decided, where, and whether it still holds.

## 4. Asking versus browsing your own past

| # | Finding | Source |
|---|---|---|
| 4.1 | Agents that bring up your own documents while you work (the Remembrance Agent and two successors) led people to retrieve and use more of their information than a search engine did. | Rhodes & Maes, *IBM Syst. J.* 2000 [E, abstract; old] |
| 4.2 | Memoro, a wearable assistant that answers from a person's recorded conversations: 20 people, lab conversations about fictional people. Confidence in what they recalled rose from 43.1/100 without help to 75.4–80.0 with it. Answers were right 84.0% of the time when the person asked (query mode), 80.3% for a plain LLM baseline, and 70.7% when the system guessed the need without a question (23.5% wrong). Short answers cut answer length by 85%. Half (10 of 20) preferred the no-question mode. | Zulfikar, Chan & Maes, CHI 2024 [E; lab, small] |
| 4.3 | What people ask about their past. In a one-month diary study, people logged 299 questions they wanted to ask about their own photos and screenshots. 74.4% needed more than finding one item: a time, place, person or event, or a pattern across memories. With 10 people and 137 of their questions, answers that linked related memories were rated accurate 71.5% of the time, against 43.1% for plain retrieval. Each answer listed the memories it used; 25 of 137 failed. | Li, Zhang & Ma, OmniQuery, CHI 2025 [E; small; the paper gives both 29 and 32 diary participants] |
| 4.4 | An AI's memory of your past is unreliable. On 97 questions about short chat histories (three to six sessions), ChatGPT with its memory feature answered 57.7% correctly, against 91.8% when GPT-4o read the whole history. Another assistant (Coze) answered 33.0%. ChatGPT tended to overwrite important facts as the chat went on. | Wu et al., LongMemEval, ICLR 2025 [E; a pilot run by annotators] |
| 4.5 | Citations are not proof. Across four AI search engines, 51.5% of generated sentences were fully supported by their citations, and 74.5% of citations supported their sentence. In a separate experiment, citations raised trust even when they were random; trust fell when people checked them. | Liu, Zhang & Liang, EMNLP Findings 2023 [E]; Ding et al., AAAI 2025 [E, abstract; sample size not stated there] |
| 4.6 | Reading the source is the check that works. 80 people fact-checked claims with an LLM's explanation or with search. Explanations were faster at similar accuracy, but people over-relied on wrong ones, and adding search results to the explanation gave nothing over search alone. In product research, LLM search was faster and as accurate when right; people relied on it when wrong; colour-marking possibly wrong text helped them catch errors. | Si et al., NAACL 2024 [E, abstract]; Spatharioti et al., CHI 2025 [E, preprint abstract] |
| 4.7 | A chatbot can change what you remember. In a simulated witness interview with 200 people, a generative chatbot produced over three times the immediate false memories of a control group, and 1.7 times those of a survey; 36.4% of answers to it were misled. A week later the false memories remained, held with more confidence than in the control group. | Chan et al., IUI 2025 [E; lab] |
| 4.8 | Revisiting past AI conversations. 10 data workers used a design probe to revisit past analysis chats. Their needs were to recall, reorient and prioritise. They navigated by visual recall (a chart they remembered), in sequence, or through higher-level summaries. Long linear transcripts did not fit their non-linear work. | Gu, Palani & Setlur, CHI 2026 [E, abstract; small] |
| 4.9 | Asking an assistant about work information. In Microsoft's lab studies (147 and 163 paid participants in a simulated company), Copilot made look-ups in email and files faster, with no significant effect on accuracy. | Microsoft, *AI and Productivity Report*, 2023 [E; vendor report] |

**Lessons.**
- [E] Asking is the quickest route to a fact from your past (4.2, 4.9), and people tend to use whichever route is quicker (3.4). The user typed questions about their own past both times they used "Ask about this" (overview-sketch-round.md, Result).
- [E] But an answer from AI memory can be wrong (4.4), a citation can make a wrong answer look right (4.5), and a confident wrong answer can change the person's own memory of the past (4.7).
- [L] So an answer about the past should be built like OmniQuery's (4.3): from the person's own records, quoting their exact words or showing the piece of work, with its place (which chat, which day, which work). When nothing is found, it should say where it looked, so the person can trust the "no" (1.2).
- [L] Browsing stays as the check and the fallback. Opening the quote should land in the browsable record, in its context (1.2, 4.6).
- [L] Questions about one's past are mostly about episodes with context: when, with whom, at which step (4.3, 1.6). Answering them needs an index of episodes (what you did, where, when, with whom, in which work), not only an index of ideas.
- [L] Bringing past items up unasked (4.1) is the memory job in the chat (DESIGN §4), not the overview's.

## 5. What this suggests about the sketch round [L]

The sketch round scored 2 wins, 2 ties and no losses, short of its bar; the sketches got seller attribution and a cross-context conflict right. The user chose neither ("still not very helpful"), and both "Ask" tries were questions about their past (overview-sketch-round.md, Result). They gave no further reason, so these are hypotheses to test:
- Both sketches were organized by idea and topic, a "knowing" view (§3), with work as one-line cues inside ideas. That serves need 1. Needs 2 and 3 turn on episodes and the work itself: the last state, the trail and the exact record (§2, §4).
- Answering a question meant leaving the view through "Ask". If asking is the main route for need 3, the sourced answer may belong inside the overview experience, not at a side exit.
- Browsing a map to answer a specific question is slower than asking (3.4). A map can still be right for need 1.
- None of this changes the WHAT. Answering a question about your own past is revisiting, which GOAL §2 keeps as the overview's job. Whether it should also "expand" an idea stays open (GOAL §2, 2026-10-27); this slice has almost no evidence on that. An episode layer is a change of form and should be shown to the user before it is built.

## 6. Gaps and unverified items

- No study found tests an overview of one person's ideas for any of the three needs.
- Resumption evidence is mostly lab work over seconds or small field studies (6 to 27 people), much of it on programmers, none on work done through AI chats. One search found no meta-analysis of resumption cues.
- Much re-finding evidence is old (2001–2011) and predates LLM assistants. The asking studies are small (10–20 people) or use general rather than personal content (4.5–4.7).
- Unverified: the Finder Highlights times (1.8); that resumption speed did not differ in Parnin & DeLine (2.4); Fitchett's figures (1.3); the exact wording of the five Rs (3.1); Lamming & Newman, Gonçalves & Jorge and Blanc-Brude & Scapin (secondary only); the content of Bergman & Whittaker's principles (1.7); the sample size in Ding et al. (4.5).

## Implications for the overview

The three needs map onto different kinds of memory [L]: need 1 is reflecting and "knowing"; need 2 is recollecting plus remembering intentions; need 3 is retrieving. Each needs its own form. Strength below: **moderate** = consistent results across several studies, some in the field, but small or old; **weak** = one or two small studies, lab only, or inference from neighbouring tasks. Nothing is strong, because no study tests this view.

**Need 1: see the big picture of what I think and know**

| Rank | Form | Evidence | Strength |
|---|---|---|---|
| 1 | A small, stable structure in the person's own topics and projects, browsed by place, with open items and "changed since you last looked" as reminders | 1.2, 1.3, 1.7, 1.8; note 25 §2.3 | Moderate for finding things this way; weak for the big-picture use itself (3.1) |
| 2 | Each idea labelled by what it is about and why it mattered, in the person's words, with one picture of real work | 1.6, 2.6, 3.2; note 23 H.1, H.4 | Moderate |
| 3 | Time as a filter or sort order, not the main shape | 1.5, 1.6; note 23 H.2 | Moderate |

**Need 2: get back into a piece of work**

| Rank | Form | Evidence | Strength |
|---|---|---|---|
| 1 | "Where you left off" for each piece of work: its last state as a recognisable picture (a full screenshot, or the key lines when a picture would be too small), the last few steps in order, and what has changed since | 2.1, 2.2, 2.4, 2.5, 2.6, 2.7 | Moderate |
| 2 | With it, the goal and next step the person stated, and the open questions | 2.1, 2.6, 2.8 | Moderate |
| 3 | One step from there into the artifact itself (a permalink or viewer, never a path), then into the chat | 2.5; GOAL §2 on path strings | Weak to moderate |
| 4 | A summary only as the one-line label, never in place of 1 and 2 | 2.4, 2.7, 2.9 | Weak to moderate |

**Need 3: answer a question about my own past**

| Rank | Form | Evidence | Strength |
|---|---|---|---|
| 1 | Ask in the assistant. The answer quotes the person's own record and shows its place (chat, day, piece of work). A "not found" shows where it looked | 1.2, 3.4, 4.2, 4.3; the user's two "Ask" tries | Moderate that people will ask; moderate that unsourced answers mislead (4.4–4.7, mostly on general content) |
| 2 | Browse or filter the same records by topic, person and rough time, landing on the same quote in its context | 1.4, 1.5, 1.6, 4.8 | Moderate |
| 3 | A list of decisions per topic, with status (holds, replaced) and where each was made | 3.7; note 20 1.6 | Weak |

**Across the three needs** [L]:
- Keep two layers under one view, linked both ways: ideas (need 1) and episodes of real work (needs 2 and 3). An idea points to its episodes; an episode shows the ideas it touched.
- Give three ways in: browse the ideas, open "where you left off", and ask. Note 25 §3's inline carousel (3–8 cards, each an image, a title, up to three lines and one action) fits "where you left off"; the full-screen view fits the ideas.
- In the DESIGN §8 overview test, measure each need on its own terms: time to the first useful action when resuming; correct answers and time for questions about the past, with and without the quoted source; and the person's own judgement for the big picture.

## Sources

**Re-finding**
- Teevan, Adar, Jones & Potts, "Information re-retrieval: repeat queries in Yahoo's logs", SIGIR 2007. https://www.microsoft.com/en-us/research/publication/information-re-retrieval-repeat-queries-yahoos-logs/
- Teevan, Alvarado, Ackerman & Karger, "The perfect search engine is not enough: a study of orienteering behavior in directed search", CHI 2004. https://people.csail.mit.edu/teevan/work/publications/papers/chi04.pdf
- Bergman et al., "Improved search engines and navigation preference in personal information management", TOIS 26(4), 2008 (note 25). https://doi.org/10.1145/1402256.1402259
- Benn, Bergman, Glazer, Arent, Wilkinson, Varley & Whittaker, "Navigating through digital folders uses the same brain structures as real world navigation", *Scientific Reports* 5:14719, 2015. https://pmc.ncbi.nlm.nih.gov/articles/PMC4589681/
- Fitchett & Cockburn, "An empirical characterisation of file retrieval", IJHCS 74, 2015; Fitchett, Cockburn & Gutwin, "Finder highlights", CHI 2014 (listings). https://dblp.dagstuhl.de/pid/23/3957.html ; Finder Highlights figures via https://pim.famnit.upr.si/wp/?p=317
- Whittaker, Matthews, Cerruti, Badenes & Tang, "Am I wasting my time organizing email? A study of email refinding", CHI 2011. https://doi.org/10.1145/1978942.1979457
- Dumais, Cutrell, Cadiz, Jancke, Sarin & Robbins, "Stuff I've Seen: a system for personal information retrieval and re-use", SIGIR 2003. https://www.microsoft.com/en-us/research/wp-content/uploads/2003/01/siscore-sigir2003-final.pdf
- Elsweiler, Baillie & Ruthven, "Exploring memory in email refinding", TOIS 26(4), 2008; cites Gonçalves & Jorge (IUI 2004) and Blanc-Brude & Scapin (IUI 2007). https://epub.uni-regensburg.de/22682/1/Tois2008_exploring_email.pdf
- Jones, Phuwanartnurak, Gill & Bruce, "Don't take my folders away! Organizing personal information to get things done", CHI 2005. https://digital.lib.washington.edu/researchworks/handle/1773/2031
- Bergman, Beyth-Marom & Nachmias, "The project fragmentation problem in personal information management", CHI 2006. https://doi.org/10.1145/1124772.1124813
- Bergman & Whittaker, *The Science of Managing Our Digital Stuff*, MIT Press, 2016. https://academic.oup.com/mit-press-scholarship-online/book/22884
- Jones, Bruce & Dumais, "Keeping found things found on the web", CIKM 2001. https://www.microsoft.com/en-us/research/publication/keeping-found-things-found-web/

**Getting back into work**
- Altmann & Trafton, "Task interruption: resumption lag and the role of cues", CogSci 2004 (cites their "Memory for goals" model, *Cognitive Science* 26, 2002). https://escholarship.org/content/qt18b4r661/qt18b4r661_noSplash_3f34d996b3c4b2f3df0252199a2e55fc.pdf
- Trafton, Altmann, Brock & Mintz, "Preparing to resume an interrupted task", IJHCS 58, 2003. https://interruptions.net/literature/Trafton-IJHCS03.pdf
- Iqbal & Horvitz, "Disruption and recovery of computing tasks: field study, analysis, and directions", CHI 2007. https://www.erichorvitz.com/CHI_2007_Iqbal_Horvitz.pdf
- Mark, Gonzalez & Harris, "No task left behind? Examining the nature of fragmented work", CHI 2005. https://doi.org/10.1145/1054972.1055017
- Czerwinski, Horvitz & Wilhite, "A diary study of task switching and interruptions", CHI 2004. https://www.erichorvitz.com/taskdiary.pdf
- Parnin & Rugaber, "Resumption strategies for interrupted programming tasks", *Software Quality Journal* 19, 2011. https://doi.org/10.1007/s11219-010-9104-9
- Parnin & DeLine, "Evaluating cues for resuming interrupted programming tasks", CHI 2010; and the authors' slides. https://www.microsoft.com/en-us/research/publication/evaluating-cues-for-resuming-interrupted-programming-tasks/ ; https://www.slideshare.net/slideshow/evaluating-cues-for-resuming-interrupted-programming-tasks/6202259
- Kersten & Murphy, "Using task context to improve programmer productivity", FSE 2006; and their CSCW 2006 position paper on Mylar. https://doi.org/10.1145/1181775.1181777 ; https://eclipse.dev/mylyn/publications/2006-11-mylar-cscw.pdf
- Rule, Tabard & Hollan, "Using visual histories to reconstruct the mental context of suspended activities", *Human–Computer Interaction* 32(5–6), 2017 (cites Lamming & Newman 1992). https://doi.org/10.1080/07370024.2017.1300063
- Rule, Tabard, Boyd & Hollan, "Restoring the context of interrupted work with desktop thumbnails", CogSci 2015. https://escholarship.org/uc/item/1pt4c25g
- Czerwinski & Horvitz, "An investigation of memory for daily computing events", HCI 2002. https://erichorvitz.com/memorycomputing.htm
- Leroy & Glomb, "Tasks interrupted: ... how a 'ready-to-resume' plan mitigates the effects", *Organization Science* 29(3), 2018. https://ideas.repec.org/a/inm/ororsc/v29y2018i3p380-397.html
- Microsoft Research (Cambon et al.), *AI and Productivity Report, First Edition*, MSR-TR-2023-43, 2023. https://www.microsoft.com/en-us/research/uploads/prod/2023/12/AI-and-Productivity-Report-First-Edition.pdf

**Records of the past**
- Sellen & Whittaker, "Beyond total capture: a constructive critique of lifelogging", CACM 53(5), 2010. https://cacm.acm.org/?p=29937
- Sellen, Fogg, Aitken, Hodges, Rother & Wood, "Do life-logging technologies support memory for the past? An experimental study using SenseCam", CHI 2007. https://microsoft.com/en-us/research/uploads/prod/2007/09/Do-life-logging-technologies-support-memory.pdf
- Kalnikaite, Sellen, Whittaker & Kirk, "Now let me see where I was: understanding how lifelogs mediate memory", CHI 2010. https://www.microsoft.com/en-us/research/?p=159071
- Kalnikaite & Whittaker, "Software or wetware? Discovering when and why people use digital prosthetic memory", CHI 2007 (abstract via talk listing). https://talks.cam.ac.uk/talk/index/8325/
- Whittaker et al., "Socio-technical lifelogging: deriving design principles for a future proof digital past", *Human–Computer Interaction* 27, 2012. https://shura.shu.ac.uk/5415/
- Allé et al., "Wearable cameras are useful tools to investigate and remediate autobiographical memory impairment: a systematic PRISMA review", *Neuropsychology Review*, 2017. https://www.springermedicine.com/wearable-cameras-are-useful-tools-to-investigate-and-remediate-a/21721852
- Woodberry et al., SenseCam review against a written diary in Alzheimer's disease, *Memory*, 2015. https://www.microsoft.com/en-us/research/wp-content/uploads/2018/02/Woodberry-et-al-Memory.pdf
- Whittaker et al., "Analysing meeting records: an ethnographic study and technological implications", MLMI, Springer LNCS, 2006 (co-authors not checked). https://doi.org/10.1007/11677482_9
- Vemuri, Schmandt, Bender, Tellex & Lassey, "An audio-based personal memory aid", UbiComp 2004; Vemuri, *Personal Long-Term Memory Aids*, MIT PhD thesis, 2004. https://www.media.mit.edu/speech/old/papers/2004/vemuri_UBI04_Audio-BasedPersonalMemoryAid.pdf ; https://www.media.mit.edu/publications/personal-long-term-memory-aids

**Asking versus browsing**
- Rhodes & Maes, "Just-in-time information retrieval agents", *IBM Systems Journal* 39(3–4), 2000. https://www.bradleyrhodes.com/Papers/rhodes-jitir-agents-ibmsj-2000.pdf
- Zulfikar, Chan & Maes, "Memoro: using large language models to realize a concise interface for real-time memory augmentation", CHI 2024. https://arxiv.org/abs/2403.02135
- Li, Zhang & Ma, "OmniQuery: contextually augmenting captured multimodal memory to enable personal question answering", CHI 2025. https://arxiv.org/abs/2409.08250
- Wu, Wang, Yu, Zhang, Chang & Yu, "LongMemEval: benchmarking chat assistants on long-term interactive memory", ICLR 2025. https://arxiv.org/abs/2410.10813
- Liu, Zhang & Liang, "Evaluating verifiability in generative search engines", Findings of EMNLP 2023. https://arxiv.org/abs/2304.09848
- Ding et al., "Citations and trust in LLM generated responses", AAAI 2025. https://arxiv.org/abs/2501.01303
- Si et al., "Large language models help humans verify truthfulness — except when they are convincingly wrong", NAACL 2024. https://aclanthology.org/2024.naacl-long.81
- Spatharioti, Rothschild, Goldstein & Hofman, "Effects of LLM-based search on decision making: speed, accuracy, and overreliance", CHI 2025 (preprint: "Comparing traditional and LLM-based search for consumer choice"). https://arxiv.org/abs/2307.03744
- Chan, Pataranutaporn, Suri, Zulfikar, Maes & Loftus, "Conversational AI powered by large language models amplifies false memories in witness interviews", IUI 2025. https://arxiv.org/abs/2408.04681
- Gu, Palani & Setlur, "'I need to find that one chart': how data workers navigate, summarize and communicate analytical conversations", CHI 2026. https://www.tableau.com/fr-fr/research/publications/syncsense

**Earlier notes and project documents** (in this repository)
- Note 25, [`round6/25-overview-display.md`](25-overview-display.md): §2.1f, §2.3, §2.4, §3.
- Note 23, [`round5/23-memory-architecture-and-dreaming.md`](../round5/23-memory-architecture-and-dreaming.md) §4: H.1, H.2, H.4.
- Note 20, [`round4/20-index-expansion-capture.md`](../round4/20-index-expansion-capture.md): 1.6.
- [`GOAL.md`](../../GOAL.md), [`DESIGN.md`](../../design/revision-2026-10-23/DESIGN.md) §4, §6, §8, [`overview-sketch-round.md`](../../design/revision-2026-10-23/overview-sketch-round.md).
