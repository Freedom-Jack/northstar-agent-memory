# Round 6 research (26d): how products let people revisit their own memory, and how people use those views

**Date:** 2026-10-27. **Read with:** [`GOAL.md`](../../GOAL.md) §1 and §2 (the human-view rows of 2026-10-15, 2026-10-24 and 2026-10-27); [note 25](25-overview-display.md) §1, whose product table this note extends rather than repeats; [note 20](../round4/20-index-expansion-capture.md); [note 22](../round5/22-surface-facts.md) §C–§E; the Result section of [`overview-sketch-round.md`](../../design/revision-2026-10-23/overview-sketch-round.md).
**Question:** what forms do products give people for revisiting their own memory and knowledge, and what is published about how people actually use those views? What does that mean for the overview's three needs: (1) see the big picture of what I think and know; (2) get back into a piece of work; (3) answer a question about my own past?
**Method:** one desk pass on 2026-10-27 (about 90 tool calls), using vendor docs and posts, press articles with figures, user research and studies. **[E]** = a source shows it: a page opened today, a quote from the page itself in a search result, or an earlier note named. **[L]** = my inference. **Vendor claim** = the company's own figure or words, not checked by anyone else. **Unverified** = seen only in a secondary source or a search summary. No personal data was read. Findings constrain the HOW only (GOAL §5).

**Short answer.**
- No AI assistant or notes app publishes how people use its memory view, mind map or graph. The only large usage numbers for revisiting one's own past are for photo and social resurfacing: Facebook's On This Day had 60 million visitors a day in 2016 and over 90 million in 2018; Google Photos Memories had over half a billion users a month in 2023 [E].
- What products ship, keep and kill points to three layers. A short generated overview is the way in. Chat gives answers with citations that jump to the source. Resurfacing is pushed at chosen moments [E for the products; no usage data for any layer].
- No maker of a graph view has published usage data. In 2025 those makers built tables (Obsidian Bases) and chat over the canvas (Heptabase). The one mass-market AI-made map, NotebookLM's, turns a click on a node into a chat question [E].
- Full-record timelines have struggled. Rewind's desktop timeline was frozen in 2024 and shut down after Meta bought Limitless in December 2025. Recall is opt-in on few PCs. Studies find that people rarely open such archives, and that a date is a weak memory cue [E].
- Chat is not a free win. In June 2025 Google paused Ask Photos over speed, quality and design. It came back with ordinary search results shown first and the AI answer below them [E].
- The trend: from browsing a stored structure to asking and getting cited answers, with a short overview as the door. Product moves show this; usage data does not [L, built on E].
- For the overview [L]: (1) a short topic overview in the person's own words, with a stable map as an optional view; (2) the actual work under each topic, plus a short cited brief; (3) cited answers, with exact matches shown first. Both times the user tried "Ask about this", they asked about their own past. That is need 3, where the evidence that products converge is strongest.

---

## 1. AI assistants' memory views

Note 25 §1 covered these views up to 2026-10-24. Below are the details it lacked, rechecked today, plus Pulse, Copilot and Gemini.

| Product | How a person revisits | Origin and sources | Corrections | What is known about use |
|---|---|---|---|---|
| **ChatGPT memory summary** (Dreaming V3, 4 Jun 2026) | A "memory summary page" with highlights by topic area (the example covers work, hobbies, travel and community). Layout not documented. To go deeper, you chat with the model. You can say which topics to bring up and when [E] | None per item on the summary. "Sources may appear below the response": a past chat, saved memory, custom instruction, file or connected email. They "may not show every factor" [E] | "Enter a correction in the text field"; "Highlight text and provide a correction"; "Don't mention this again", which "reduces future references" but keeps the source [E] | Memory serves "hundreds of millions of users". Serving Dreaming to Free users cut compute "approximately 5x". Evaluations report "a substantial lift", with no figures. Nothing on how often the page is opened [E, vendor] |
| **ChatGPT saved memories** (Apr 2024, still in settings) | "A more explicit list of individual memory items" [E] | Made in conversation | Delete, or ask to forget; "search, sorting, automatic prioritization, and version history", depending on "your plan and platform" [E] | Of 2,050 entries from 80 users, 96% were created by the system on its own (Dash et al., WWW 2026; note 25) [E] |
| **ChatGPT Pulse** (25 Sep 2025) | Each morning, "topical visual cards" researched overnight from memory, chat history and feedback. Cards last one day unless saved or followed up [E] | Not stated by OpenAI; press reports sourced links [unverified] | "Curate" requests for tomorrow; thumbs up or down [E] | No figures. OpenAI says early student testers found more value once they told it what they wanted, and that Pulse "won't always get things right", e.g. tips for a project already finished. Launched as a Pro-only mobile preview [E, vendor] |
| **Claude memory** (help page, checked today) | "A set of individual topics as you chat"; "Select any topic to read it". Each project has its own memory. Some Team and Enterprise accounts keep one summary (legacy) [E] | Topics: not stated. Deleting a chat does not remove memory made from it. Past-chat search shows "citations linking back to the original chats" [E] | Edit or delete a topic, or tell Claude. "Fix something in one topic and the change applies to every conversation from then on" [E] | None published |
| **Microsoft Copilot** (consumer; page for the older app) | Ask "What do you know about me?" and Copilot "will then summarize its memory of you". The view is a chat answer [E] | Not stated | "Forget that …" in chat; Delete all Memory [E] | None published |
| **Gemini Personal Intelligence** (14 Jan 2026, US beta) | No view of "what Gemini knows" is described. Answers draw on connected Gmail, Photos, YouTube and Search [E] | Gemini "will try to reference or explain the information it used from your connected sources" [E] | Correct it in the moment; regenerate without personalization; temporary chats [E] | None. Google lists known failures: inaccurate answers, "over-personalization", trouble with timing (for example a divorce), and inferring interests from volume (many golf photos do not mean you love golf) [E, vendor] |

**Studies of people and AI memory views.**
- [E] Chen, Molina, Liao and Cho, CHI '26, 20 interviews with ChatGPT users: "most participants experienced negative expectancy violations after learning what ChatGPT remembered about them", and showed "a strong need for greater visibility, accessibility, transparency, and user control". Correction to note 25: it lists DOI 10.1145/3772318.3791635 as "Relational Gains, Privacy Strains"; the authors' college gives that DOI as "AI Never Forgets".
- [E, search summary] Zhang et al., HAIPS 2025, 18 interviews: "diverse and often incomplete mental models" of memory; people wanted to review, edit, delete and categorize memories.
- [E, search summary] "Ghost of the past" (arXiv 2410.14931), 40 participants: most did not know memory systems existed, and once told, asked for ways to view and change them.
- [E] None of these studies measures how often people open a memory view, or what they do there.

**Lessons.**
- [E] Every assistant offers a memory view, but treats it as a control panel for accuracy and privacy, not as a place to think. ChatGPT sends depth to chat; Copilot's view is itself a chat answer.
- [E] Sources sit on answers, not on the overview. No assistant view shows each item's origin or the person's work behind it, the same gap note 25 found.
- [E] Corrections converge on editing in place, plus a "don't bring this up" that does not delete.
- [L] Gemini's list of failures describes the risk in showing someone "what you think". One reading of the user's "This is what I think right?" (GOAL §1, 2026-10-27) is the same doubt. Each item should show its origin and offer a one-tap "not what I think".

## 2. AI-made overviews: NotebookLM (now Gemini Notebook) and Perplexity

| Product | Forms | What is known about use |
|---|---|---|
| **NotebookLM**, renamed **Gemini Notebook** on 16 Jul 2026 | Over the sources a person uploads: chat with inline citations; a mind map whose nodes, when selected, ask the chat about them (note 25); Audio Overviews (two AI hosts); Video Overviews (from 29 Jul 2025); study guides [E]; briefing docs [not rechecked] | After more than 80 languages were added in April 2025, Audio Overviews created per day "doubled in just two weeks". Total users doubled "just a few weeks later", after the mobile app. A team member credits the product's success to users not needing "to think very hard about what to make" (Google, 29 Jul 2025) [E, vendor]. At the rename, "more than 30 million people and over 600,000 organizations" (Google, as reported 18 Jul 2026) [unverified: Google's post not opened]. No figure for mind maps or briefing docs; one broad search found no study of learning outcomes |
| **Perplexity Pages** (30 May 2024) and **Spaces** | Pages turns a research thread into a shareable article that readers can question further [E, secondary]. Spaces collect threads and files; reportedly renamed Projects on 30 Jul 2026, with a memory layer called "Brain" [unverified; the help page was blocked] | None found |

**Lessons.**
- [E] The generated overview with published growth is the ready-made, low-effort kind (audio). Google credits not having to choose what to make.
- [E] NotebookLM's map is a door into the chat. Clicking a node asks a question.
- [L] All this growth is for summaries of material the person uploaded, often other people's. None shows that a generated overview of one's own ideas gets used.

## 3. Asking your own past

| Product | Form | Sources | Fate and evidence of use |
|---|---|---|---|
| **Rewind** (Mac) → **Limitless** | Rewind would "privately record your activity and let you search through your own history": a local timeline plus search. Limitless (April 2024): meeting recording, summaries, briefs drawn from earlier meetings, a pendant, and questions answered from recordings [E] | Third-party listings say Ask answers link to the recorded conversations they came from [unverified] | Rewind stopped getting new features; its promised Windows app was dropped. Founder Dan Siroker said they would "reimplement many of our users' favorite Rewind features directly into Limitless". Over 10,000 pendant preorders (TechCrunch, 17 Apr 2024) [E]. Meta bought Limitless on 5 Dec 2025, and Rewind is being shut down (note 20) [E] |
| **Windows Recall** | Browse a timeline of screenshots, or describe what you remember and search text and images, then "jump back into the content you saw". Opt-in, local, behind Windows Hello [E] | The snapshot itself | No adoption figure published. Fewer than 10% of Windows 11 PCs can run it (GeekWire, 15 Apr 2026, as cited in note 20 §3.6) [E] |
| **Google Photos Ask Photos** (early access Sep 2024) | Plain-language questions over one's own photo library [E] | Photos | Paused in June 2025. A Google product manager wrote: "Ask Photos isn't where it needs to be, in terms of latency, quality and ux". A user had called it "much slower with less obvious benefits than the traditional search" [E, via search summary]. Back on 26 Jun 2025: simple queries ("beach", "dogs") show results at once, while Gemini "will work in the background" on complex ones; classic search stays available [E] |
| **Mem 2.0** (1 Oct 2025, rebuilt "from scratch") | "Just describe what you're looking for"; search that "understands meaning and intent"; chat over "everything you've ever saved"; "Heads Up": "Notes automatically resurface at exactly the right moment" [E]. Pitched with "no dashboards, no PARA systems, no endless tagging" [E, search summary] | Not described | None published. Mem planned to retire Mem 1.0 in 2024 [E, search summary] |
| **Notion Q&A** (Nov 2023) | Questions answered from the workspace pages a person can access | Answers link to source pages [E, search summary of the launch post] | None for Q&A |
| **Glean** | Workplace search plus an assistant | Not checked | "Employees using Glean Assistant average 14 queries per day" (Kleiner Perkins, 27 Feb 2024) [E, investor claim; method unknown] |
| **Granola 2.0** (14 May 2025) | Meeting notes grouped into folders; chat across a folder [E] | "Every AI answer comes with inline citations and a jump-to-source link" [E] | Users call it a "second brain" with "super-human memory"; it transcribes "millions of minutes of conversation" a day [E, vendor] |

**What research says about capture-and-ask products.** Sellen and Whittaker reviewed lifelogging (CACM 53(5), May 2010; read from the paper today) [E]:
- **Five uses.** Recollecting (reliving an experience), reminiscing (reliving it for emotional reasons), retrieving (finding specific information), reflecting (seeing patterns, or the past "from different angles"), and remembering intentions (what you plan to do).
- **Each use needs its own design.** Retrieval needs "efficient ways of searching". Reflection needs abstraction, "flexible and novel methods for viewing personal data". Intentions need "timely cues in appropriate contexts". "Systems supporting reminiscence and reflection have received far less attention than those supporting recollection and retrieval."
- **Use.** Total-capture systems "have been used by only a small number of people". Meeting-capture systems "have shown little uptake of sophisticated records". Digital family archives are "rarely accessed": asked to pick objects of memory value at home, people chose digital ones "less than 2%" of the time (Petrelli & Whittaker). SenseCam's help with recollection "rapidly decreased after only three months".
- **Cues and effort.** "Place, events, and people are stronger cues than time." People skip an accurate record "if they feel they can remember the information unaided", and "efficiency of access sometimes overrides accuracy" (Kalnikaite & Whittaker).
- **Their lessons:** "Selectivity, not total capture" and "Cues not capture".

**Lessons.**
- [E] The products that asked people to browse a full record (Rewind, Recall) published no adoption and were frozen, sold or limited. The ones still growing let you ask across a scoped set and cite the answer: a Granola folder, a Notion workspace, a Heptabase whiteboard.
- [E] Ask Photos shows that a chat answer cannot be slower than a direct match for a simple lookup. Google's fix was a hybrid, as "efficiency of access sometimes overrides accuracy" predicts.
- [L] Sellen's five uses map onto the overview's needs. Need 1 is close to reflecting, need 2 to recollecting plus remembering intentions, need 3 to retrieving. By their argument, one form will not serve all three well.

## 4. Graph, canvas and outline tools

| Tool | Main ways to revisit | AI and sources | Evidence of use |
|---|---|---|---|
| **Obsidian** | Search, backlinks, a global and a local graph, Canvas. Bases (1.9.0, 21 May 2025): "Introducing Bases, a new core plugin that lets you turn any set of notes into a powerful database", with table views and "more view types" planned [E] | User-made | No published data. In a forum thread from Nov 2023, "What's the point of the graph view?", one user had disabled it ("Couldn't find any use for it"). Another used the local graph "when I need it to be (which isn't often)". A third called it "the most important pillar of my vault". A fourth said the global graph cannot be used to "view" notes because "the position of each note changes on every load" [E, anecdotes, not a survey] |
| **Heptabase** | Whiteboards of cards, made by the user | From 23 Jul 2025, whiteboards can be added to chat, and replies include "reference links to the cards and blocks that the response is grounded on"; chat over the whole knowledge base by Nov 2025 [E] | "Many users have told us they no longer need to switch between Heptabase and NotebookLM or ChatGPT" [E, vendor claim] |
| **Tana** | An outliner with "supertags" (typed nodes); AI turns calls into action items | — | A 160,000 waitlist and 30,000 testers (company figures, Feb 2025, via search summaries of TechCrunch and the press release) [E, vendor] |
| **Roam, Capacities, Reflect** | Roam: an outliner with daily notes and a graph. Capacities: typed objects with a graph view. Reflect: backlinks and daily notes | Capacities: AI chat on its paid plan [unverified, third party]. Reflect: "chat with your notes" (App Store listing) [E] | None published. Claims that Roam declined are unsourced [E for the absence] |

**Lessons.**
- [E] No graph or canvas tool has published how much its graph is used. The one study of Obsidian users found (Ferreira et al. 2025) is about how retrieval habits shape note-making, and its abstract does not mention the graph (note 25).
- [E] The 2025–26 investments went to tables (Bases), chat with citations over the canvas (Heptabase), and AI chat (Reflect, Capacities). None went to new graph views.
- [E] Forum users who like graphs mostly use the local graph around one note. A global layout that moves on every load cannot be used to find things, which fits the stable-layout evidence in note 25 §2.3.
- [L] Graphs live on as canvases people arrange themselves, or as a small view around one note. No product uses an automatic graph as the AI's main summary of a person.

## 5. Resurfacing

| Product | Form | Controls | Evidence of use |
|---|---|---|---|
| **Facebook On This Day** (Mar 2015) and **Memories** page (Jun 2018) | Posts from this date in past years, plus Friends Made On This Day, Memories You May Have Missed, and monthly or seasonal Recaps [E] | Filters for people and dates; hiding memories of blocked people and former partners; trying to "avoid showing anything that could make you sad" [E] | "Each day 60 million people visit On This Day"; "155 million have subscribed to its notifications" (TechCrunch, 24 Mar 2016). "Over 90 million people a day" (Facebook product manager Oren Hod, via Tubefilter, 12 Jun 2018) [E, vendor figures] |
| **Facebook's memories research** (Konrad, 2017) | "Over a dozen quantitative and qualitative memory studies" over two years [E] | — | People want "reminders of fun, interesting, and important life moments". Some posts hurt to see again, and happy ones can turn sad (a first day at a job since left). Resurfacing without control went too far, so filters followed. Recaps of a period helped people sum up a chapter of their lives. Statistics alone "lacked some of the heart and soul", so the posts behind the numbers were shown instead [E] |
| **Timehop** (standalone app) | Your posts and photos from this day in past years | — | 12 million registered and 6 million daily users by the end of 2014 (TechCrunch, 2016) [E]. Usage then fell after Facebook's copy; US downloads were reported down 38% from Q4 2015 to Q4 2016 [unverified, app-analytics data via search summary] |
| **Google Photos Memories** | A carousel of past moments; from Aug 2023, a scrapbook-like view where you add or remove photos, rename, invite others, and edit or reject AI title suggestions [E] | Edit titles and photos [E] | "Used by more than half a billion people monthly" (Google, via TechCrunch, 15 Aug 2023) [E, vendor] |
| **Readwise Daily Review** | A daily set of your highlights, chosen in proportion to each source's share ("Frequency Tuning"), plus "Mastery" spaced-repetition cards (half-lives of 7, 14 and 28 days); optional email [E] | Frequency per source; a quality filter; Discard, which keeps the original [E] | None published. The App Store promise that you will retain "dramatically more" is marketing [E] |
| **Day One On This Day; Apple Journal** | Day One: entries, photos and places from this date in past years [E]. Journal: suggestions drawn from photos, outings and workouts (note 25) | Journal: per-source switches | None published. Day One reportedly moved On This Day under the "More" tab on iOS from version 2025.6 [unverified] |

**Lessons.**
- [E] Resurfacing has the largest published use of any revisit form: tens to hundreds of millions of people. All of it is for photos and social posts, inside apps people already open daily.
- [E] Resurfacing needs controls (filters, discard, frequency), and the real item beats a statistic about it. That echoes the user's "Seeing my real work brings it back" (GOAL §2).
- [E] As a standalone app it declined once a platform copied it (Timehop; the later figure is unverified).
- [L] For a person's own ideas, nothing is published. In Northstar, bringing items up at the right moment is already the job of memory in chat (GOAL §2: the overview is opened "rarely, if chat does it").

## 6. The trend

**Dated moves** [E unless marked]:
- **2015–2018:** resurfacing reaches mass use (Facebook On This Day and Memories; Google Photos Memories).
- **2023:** Notion Q&A; Google Photos Memories view with AI titles.
- **2024:** ChatGPT saved memories; Rewind frozen and pivoted to Limitless; Perplexity Pages; Ask Photos in early access.
- **2025:** Obsidian Bases (May); Granola folders with cited chat (May); Ask Photos paused, then back as a hybrid (June); Heptabase chat over whiteboards (July); ChatGPT Pulse (September); Mem 2.0 (October); Limitless bought by Meta and Rewind shut down (December).
- **2026:** Gemini Personal Intelligence (January); ChatGPT's Dreaming memory summary (June); NotebookLM renamed Gemini Notebook (July); Perplexity Spaces reportedly renamed Projects (July, unverified).

**The trend, named.** Products are moving from **browsing a stored structure** (a graph, a timeline, a list) to **asking and getting a cited answer**. The way in is a **short generated overview**, and **resurfacing** is pushed at chosen moments. The evidence:
- [E] Every AI assistant's memory product shipped a list or a summary, and most put sources on answers (ChatGPT, Claude, Gemini). None shipped a graph.
- [E] Notes tools built around graphs or canvases added cited chat (Heptabase), AI chat (Reflect, Capacities) or tables (Obsidian). None published how much its graph is used.
- [E] Full-record timelines lost out (Rewind) or stayed narrow (Recall), as research on lifelogging had predicted (Sellen & Whittaker 2010).
- [E] In the one field study of a person using an overview beside chat (n = 24, five days), chat stayed central. People used a synced canvas for overview, revisiting and alternatives, and adoption was uneven (Amin et al. 2026; note 20).

**Limits of this evidence.**
- [E] It shows what vendors chose, not what people do. No vendor compares forms or reports how often people open a memory view, mind map or graph.
- [E] Vendors have reasons besides users. TechCrunch tied Rewind's pivot to generative AI making a searchable record "far more useful".
- [E] The one well-documented test of chat over one's own past, Ask Photos, went badly on speed, and the fix kept ordinary results first.
- [E] The largest usage numbers belong to push resurfacing, not to chat or maps.
- [L] So: are products moving from graph views to chat answers plus generated overviews? Yes, for AI assistants and notes tools. The evidence is moderate: product moves across about ten companies. Nobody has shown that people revisit their knowledge better this way.

## 7. Implications for the overview

The overview stays as the user asked for it: a display of their knowledge, with the big picture first, grouped by topic, with connect and conflict lines, opened in the assistant (GOAL §2). What follows ranks forms *within* it [L]. Evidence strength: **strong** = several primary sources agree and some use data exists; **moderate** = several products converge but there is no use data; **weak** = one product, anecdotes or vendor claims only.

### 7.1 Forms ranked for each need

**Need 1: see the big picture of what I think and know.**
1. **A short generated topic overview, outline-like:** a few topics in the person's words, each with its main ideas, every item opening its sources and work. ChatGPT's memory summary, Claude's topic list and NotebookLM's reports work this way. **Moderate** for convergence; **none** for use.
2. **A stable map as a second view of the same items,** for connect and conflict lines, where clicking an item asks about it (NotebookLM's pattern). **Weak:** no published map use; forum users report rare use and dislike layouts that move.
3. **A one-line "what changed since you last looked"** (Pulse; Facebook's recaps). **Weak.**

**Need 2: get back into a piece of work.**
1. **The work itself, grouped by topic or project and opening at the source, plus a short brief on opening that cites it.** Granola's folders with cited chat, Limitless's briefs from earlier meetings and Pulse's cards do this. **Moderate** convergence; **weak** use evidence (vendor claims). Pulse's stale-project tip warns that the brief must check the work is still live.
2. **A cited answer to "where did I leave X?"** **Moderate.**
3. **A timeline** only as a date on a work cue. The evidence against a timeline as the main form is **moderate**: the fates of Rewind and Recall, and time being a weaker cue than place, events or people.

**Need 3: answer a question about my own past.**
1. **Cited answers that jump to the source, with exact matches shown first.** ChatGPT, Claude, Gemini, NotebookLM, Granola, Heptabase and Notion converge on this (Limitless unverified), and Ask Photos teaches the hybrid. **Strong** for convergence; **moderate** for use: vendor claims such as Glean's 14 queries a day, plus one documented failure on speed.
2. **Asking from the overview itself** (NotebookLM's node to chat; the sketches' "Ask about this"). **Weak to moderate:** one product, plus the user's own two tries, both questions about their past.

### 7.2 The five forms, assessed

| Form | Products that use it for a person's own material | Evidence of use | Best fit | Strength |
|---|---|---|---|---|
| **Topic outline** | Claude's memory topics; ChatGPT's summary by topic area; Tana and Roam outliners | None published | The way into need 1; also works as plain text in Claude Code | **Moderate** (convergence only) |
| **Map or graph** | Obsidian, Roam and Capacities graphs; Heptabase canvases (user-made); NotebookLM mind map (AI-made, click to ask) | None published; forum anecdotes of rare use and moving layouts; makers investing elsewhere | A second view for need 1, for links and conflicts, with a fixed layout | **Weak** |
| **Chat with cited answers** | Cited: ChatGPT, Claude, Gemini, NotebookLM, Granola, Heptabase, Notion (Limitless unverified). Chat without documented citations: Copilot, Mem, Glean | Vendor claims; the Ask Photos failure; Kalnikaite & Whittaker on speed over accuracy | Need 3 first, need 2 second | **Strong** convergence; **moderate** use |
| **Generated briefing or digest** | ChatGPT memory summary and Pulse; NotebookLM reports and audio; Limitless briefs; Facebook recaps | Growth claims for audio; none for Pulse; Facebook's research supports recaps | Need 2 (a brief on opening work); need 1 ("what changed") | **Weak to moderate** |
| **Resurfacing** | Facebook, Google Photos, Timehop, Readwise, Day One, Apple Journal, Mem's Heads Up | The largest numbers of any form (60–90 million a day; 500 million a month), all for photos and social posts; none for knowledge | None of the three needs, which are all things the person asks for; memory in chat already resurfaces | **Strong** for photos; **none** for knowledge |

### 7.3 What this suggests for the next round [L]

- **Judge the overview by the three needs, not by its look alone.** No product makes an overview do all the revisiting. They pair a short overview with the real items and with cited asking. The sketch round tested the display alone, and both of the user's "Ask about this" tries were need-3 questions. A next test could time each need: a glance (need 1), opening the right work with its brief (need 2), and a cited answer (need 3). This keeps the display the user asked for and adds the two layers products pair with it.
- **Close the gap every assistant leaves.** Show origin and the person's work on each item, not only on chat answers, keeping note 25's quiet origin mark (§2.5).
- **Corrections:** "not what I think" in place, plus a "don't bring this up" separate from delete (the ChatGPT pattern).
- **Revisit or expand:** every product that applies knowledge to a new problem does it in chat (ChatGPT's "just chat", NotebookLM's node to chat, Heptabase's chat), never inside the overview. That is a product pattern, not proof. It fits a revisit-only overview with one step into the chat. The user's two tries were questions, not expansions, which is weak evidence for revisiting first. The decision stays with the user (GOAL §2, 2026-10-27: "Not sure").

## 8. Gaps and unverified items

- No usage data for any AI memory view, mind map or graph view, and no comparison of forms by any vendor or study.
- **Unverified:** Gemini Notebook's 30 million users (secondary); Perplexity's rename to Projects and "Brain"; Day One's move to the "More" tab; Timehop's decline figure; Capacities' AI features; Limitless's cited answers and daily insights (third-party listings); sourced links on Pulse cards (press); the details of Zhang et al. and "Ghost of the past" (search summaries); how Glean measured its figure.
- **Not checked:** Logseq, Apple Photos memories, Microsoft 365 Copilot memory in depth, Perplexity's own help pages (blocked), Glean's citations.
- **Correction to note 25:** DOI 10.1145/3772318.3791635 is "AI Never Forgets" (Chen et al., CHI '26), according to the authors' college page.

## Sources

**AI assistants' memory views**
- OpenAI, "ChatGPT memory and Dreaming", 4 Jun 2026. https://openai.com/index/chatgpt-memory-dreaming
- OpenAI, "Memory FAQ", help page, checked 2026-10-27. https://help.openai.com/en/articles/8590148-memory-faq
- OpenAI, "Introducing ChatGPT Pulse", 25 Sep 2025. https://openai.com/index/introducing-chatgpt-pulse/
- Tom's Guide, Pulse launch coverage, Sep 2025 (press, for sourced cards). https://www.tomsguide.com/ai/chatgpt-pulse-is-here-now-ai-starts-the-chat-and-curates-your-feed
- Anthropic, "Use Claude's chat search and memory to build on previous context", help page, checked 2026-10-27. https://support.claude.com/en/articles/11817273-use-claude-s-chat-search-and-memory-to-build-on-previous-context
- Microsoft, "Microsoft Copilot privacy controls", support page (older app version). https://support.microsoft.com/en-us/microsoft-copilot/microsoft-copilot-privacy-controls
- Google, Josh Woodward, "Gemini introduces Personal Intelligence", 14 Jan 2026. https://blog.google/innovation-and-ai/products/gemini-app/personal-intelligence/
- Chen, Molina, Liao & Cho, "AI Never Forgets: Exploring Users' Perceptions of AI Memory and ChatGPT's Memory Feature", CHI '26, DOI 10.1145/3772318.3791635 (abstract on the authors' college page). https://grady.uga.edu/research/ai-never-forgets-exploring-users-perceptions-of-ai-memory-and-chatgpts-memory-feature/
- Zhang et al., "Understanding Users' Privacy Perceptions Towards LLM's RAG-based Memory", arXiv 2508.07664, 2025 (via search summary). https://arxiv.org/abs/2508.07664
- "'Ghost of the past': Identifying and Resolving Privacy Leakage of LLM's Memory Through Proactive User Interaction", arXiv 2410.14931 (via search summary). https://arxiv.org/abs/2410.14931
- Dash et al., "The Algorithmic Self-Portrait", WWW 2026 (note 25). https://arxiv.org/abs/2602.01450

**AI-made overviews**
- Google, Chaim Gartenberg, "The inside story of building NotebookLM", 29 Jul 2025. https://blog.google/technology/ai/developing-notebooklm/
- PPC Land, "Google kills NotebookLM name, moving 30 million users to Gemini Notebook", 18 Jul 2026 (secondary). https://ppc.land/google-kills-notebooklm-name-moving-30-million-users-to-gemini-notebook/
- Google, "Use Mind Maps in NotebookLM", help page (note 25). https://support.google.com/notebooklm/answer/16212283?hl=en
- Voicebot.ai, "Perplexity Pages turns generative AI search results into Wikipedia pages", 30 May 2024 (secondary). https://voicebot.ai/2024/05/30/perplexity-pages-turns-generative-ai-search-results-into-wikipedia-pages
- VentureBeat, "Perplexity goes beyond AI search, launches publishing platform Pages", May 2024 (secondary). https://venturebeat.com/ai/perplexity-goes-beyond-ai-search-launches-publishing-platform-pages
- Tech Jack Solutions, "Perplexity Projects, file connectors, Enterprise Pro", 2026 (secondary, for the Spaces rename). https://techjacksolutions.com/ai-brief/perplexity-projects-file-connectors-enterprise-pro/

**Asking your own past**
- TechCrunch, Ivan Mehta, "a16z-backed Rewind pivots to build AI-powered pendant to record your conversations", 17 Apr 2024. https://techcrunch.com/2024/04/17/a16z-backed-rewind-pivots-to-build-ai-powered-pendant-to-record-your-conversations
- TechCrunch, "Meta acquires AI device startup Limitless", 5 Dec 2025 (note 20). https://techcrunch.com/2025/12/05/meta-acquires-ai-device-startup-limitless/
- Limitless feedback board, "Ask AI Anything" (user requests). https://feedback.limitless.ai/board/ask-ai-anything
- Microsoft, "Retrace your steps with Recall", support page. https://support.microsoft.com/en-us/kb/5039749
- Engadget, "Google has 'paused' the Ask Photos rollout", Jun 2025. https://engadget.com/ai/google-has-paused-the-ask-photos-rollout-182409437.html
- Android Authority, Ask Photos pause, Jun 2025. https://www.androidauthority.com/google-photos-ask-photos-pause-3563859
- TechCrunch, Sarah Perez, "Google Photos merges classic search with AI to speed up results", 26 Jun 2025. https://techcrunch.com/2025/06/26/google-photos-merges-classic-search-with-ai-to-speed-up-results
- Mem, "Introducing Mem 2.0", 1 Oct 2025. https://get.mem.ai/blog/mem-2-dot-0
- AlternativeTo, "Mem 2.0 relaunches with smarter note-taking tools, offline support, and a new Agentic Chat", Oct 2025 (secondary). https://alternativeto.net/news/2025/10/mem-2-0-relaunches-with-smarter-note-taking-tools-offline-support-and-a-new-agentic-chat
- Notion, "Introducing Q&A", Nov 2023 (via search summary). https://www.notion.com/blog/introducing-q-and-a
- Maginative, "Notion unveils AI-powered Q&A to instantly answer questions about your notes", Nov 2023. https://www.maginative.com/article/notion-unveils-ai-powered-q-a-to-instantly-answer-questions-about-your-notes/
- Kleiner Perkins, "Glean Series D", 27 Feb 2024. https://www.kleinerperkins.com/perspectives/glean-series-d/
- Granola, "Granola 2.0: A second brain for your team", 14 May 2025. https://www.granola.ai/blog/two-dot-zero
- Granola, "Say hello to Team Folders", Jul 2025. https://www.granola.ai/updates/say-hello-to-team-folders
- Sellen & Whittaker, "Beyond Total Capture: A Constructive Critique of Lifelogging", CACM 53(5), May 2010 (read from the PDF). https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/p70-sellen.pdf
- Amin et al., "Conversations in Space", arXiv 2605.15848, 2026 (note 20). https://arxiv.org/abs/2605.15848

**Graph, canvas and outline tools**
- Obsidian, changelog 1.9.0, 21 May 2025. https://obsidian.md/changelog/2025-05-21-desktop-v1.9.0/
- Obsidian Forum, "What's the point of the graph view? (How are you using it?)", from 14 Nov 2023. https://forum.obsidian.md/t/whats-the-point-of-the-graph-view-how-are-you-using-it/71316
- Ferreira et al., "How People Manage Knowledge in their 'Second Brains'", arXiv 2509.20187, Sep 2025. https://arxiv.org/abs/2509.20187
- Rapid Developers, Roam Research profile (cited only for its unsourced decline claims). https://rapidevelopers.com/clone/roam-research
- TechCrunch, "Tana snaps up $25M with its AI-powered knowledge graph for work, racking up a 160K waitlist", 3 Feb 2025. https://techcrunch.com/2025/02/03/tana-snaps-up-25m-with-its-ai-powered-knowledge-graph-for-work-racking-up-a-160k-waitlist
- Heptabase, "Heptabase Updates: Chat with your whiteboards", 23 Jul 2025. https://wiki.heptabase.com/newsletters/2025-07-23
- Heptabase, changelog 2025 (via search summary). https://wiki.heptabase.com/changelog/2025
- Vantaige, Capacities profile (third party). https://vantaige.io/ai-tool/capacities
- Reflect Notes, App Store listing. https://apps.apple.com/app/id1575595407

**Resurfacing**
- TechCrunch, Josh Constine, "Facebook's Timehop clone On This Day gets 60 million daily visitors", 24 Mar 2016. https://techcrunch.com/2016/03/24/facebook-on-this-day/
- Tubefilter, "Facebook announces new feature that aggregates old memories", 12 Jun 2018. https://www.tubefilter.com/2018/06/12/facebook-new-feature-memories/
- Facebook Newsroom, "All of your Facebook memories are now in one place", Jun 2018 (page blocked; via Tubefilter). https://about.fb.com/news/2018/06/all-of-your-facebook-memories-are-now-in-one-place/
- Artie Konrad, "Facebook memories: the research behind the products that connect you with your past", 2017 (Prototypr copy; the Facebook Research original is blocked). https://blog.prototypr.io/facebook-memories-the-research-behind-the-products-that-connect-you-with-your-past-f9a1d8a49a43 ; https://research.facebook.com/blog/2017/09/facebook-memories-the-research-behind-the-products-that-connect-you-with-your-past/
- TechCrunch, "Timehop founder Jon Wegener replaced as CEO by design lead Matt Raoul", 14 Jan 2017 (for the download decline, via search summary). https://techcrunch.com/2017/01/14/timehop-founder-jon-wegener-replaced-as-ceo-by-design-lead-matt-raoul/
- TechCrunch, Sarah Perez, "Google Photos adds a scrapbook-like Memories view feature, aided by AI", 15 Aug 2023. https://techcrunch.com/2023/08/15/google-photos-adds-a-scrapbook-like-memories-view-feature-aided-by-ai
- Readwise docs, "Reviewing highlights". https://docs.readwise.io/readwise/docs/faqs/reviewing-highlights
- Readwise, App Store listing. https://apps.apple.com/us/app/-/id1476885528
- Day One, "On This Day" feature page. https://dayoneapp.com/features/on-this-day/
- Apple, Journal, App Store listing (note 25). https://apps.apple.com/app/journal/id6447391597

**Earlier notes and project documents** (in this repository)
- Note 25, [`round6/25-overview-display.md`](25-overview-display.md): §1 product table, §2.3 stable layout, §2.5 origin.
- Note 20, [`round4/20-index-expansion-capture.md`](../round4/20-index-expansion-capture.md): 2.5 (Amin et al.), 2.6 (NotebookLM rename), 3.2 (Limitless), 3.6 (Recall, GeekWire).
- Note 22, [`round5/22-surface-facts.md`](../round5/22-surface-facts.md) §C–§E.
- [`GOAL.md`](../../GOAL.md); [`overview-sketch-round.md`](../../design/revision-2026-10-23/overview-sketch-round.md).
