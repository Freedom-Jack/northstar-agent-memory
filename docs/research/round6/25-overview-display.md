# Round 6 research: how to show you your overview

**Date:** 2026-10-24. **Read with:** [`GOAL.md`](../../GOAL.md) §1 and §2 (the human-view rows of 2026-10-15, the answers of 2026-10-24); [`DESIGN.md`](../../design/revision-2026-10-23/DESIGN.md) §1.2–§1.3, §6 and §8; [`EXPLORATION.md`](../../EXPLORATION.md) §3; notes [20](../round4/20-index-expansion-capture.md), [22](../round5/22-surface-facts.md) §C–§E and [23](../round5/23-memory-architecture-and-dreaming.md) §4. Builds on them without repeating them.
**Question:** how should Northstar show a person their overview: a few topics in their words, their ideas and the AI ideas they adopted, connect and conflict links, and one to three pieces of real work under each idea? It opens on request in Claude desktop chat, possibly in ChatGPT, and in a compact form in Claude Code.
**Method:** one desk pass on 2026-10-24. **[E]** = a source shows it: opened today, quoted from the page itself in a search result, or in the earlier note named. **[L]** = my inference. **Unverified** = seen only in a secondary source or a search summary. Findings constrain the HOW only (GOAL §5). No personal data was read.

**Short answer.**
- No product or study tests glancing at an AI-made overview of one person's ideas, so note 20's gap stands. The nearest products show a short overview; ChatGPT and NotebookLM send depth to the chat. None publishes how people use the view [E].
- Studies back the parts: a small first screen (3–5 groups, two levels), a layout that keeps what you saw in place, your own words and work as cues, origin stored and marked quietly, and one-step corrections [E for the parts, L for the whole].
- For someone revisiting their own ideas, outline versus map matters little for understanding. It matters for finding an idea fast and for seeing links and conflicts [L].
- The surfaces decide a lot. An inline card in Claude or ChatGPT holds about 4–5 data points and two actions, with no drill-in. A map needs fullscreen. Requests that need the AI's judgment go to the chat. Panels keep no lasting state. Claude Code gets text [E].
- Compare first: **A, a topic outline with conflict pairs**, against **B, a stable topic map with connect and conflict lines**. Same items, same work cues, each opening as a small card, run inside the §8 overview test on non-Northstar work [L].
- Keep the panel revisit-only, and make "ask about this for my problem" one visible step into the chat. Whether the person takes that step, and whether it changes their answer, is the evidence for revisit versus expand [L].

---

## 1. How products show memory back to people

All rows are [E] unless marked.

| Product | First view | Depth | Origin | Correction | Evidence of use |
|---|---|---|---|---|---|
| **ChatGPT memory summary** (Dreaming, 4 Jun 2026) | "A personalized overview" (the example covers work, hobbies, travel, community); layout not documented | A summary; for more, "just chat with the model"; may omit details and sources | Not on the summary; "Sources" under some replies | Type or highlight a correction; "Don't mention this again" (source kept); topics to bring up and when | None for the page; OpenAI's evals measure replies (note 23) |
| **ChatGPT saved memories** (legacy) | A list of items | One line each | — | Delete, or ask it to forget; by plan, search, sorting, version history | None |
| **Claude memory** | A list of **topics** saved as you chat | Open a topic | Not stated; past-chat search links its chats | Edit, delete, or tell Claude; per project. Legacy: one summary rebuilt every 24 hours | None |
| **Gemini personal context** (Aug 2025) | Saved info; a past-chats switch, on by default | — | — | Edit saved info; delete chats | None found; menus unverified |
| **NotebookLM mind map** (now Gemini Notebook) | A tree of the sources' topics | Expand or collapse; **selecting a node asks the chat about it** | Chat answers cite sources | — | None found |
| **Heptabase; Obsidian graph view** | Whiteboards of cards; a graph of notes, or a local graph around one note | Open the card or note | User-made | The user arranges it | Vendor claims only. No study of graph-view use found in two searches; a 2025 case study of Obsidian users does not mention it |
| **Readwise; Apple Journal; Facebook memories** | A daily set of highlights; moments from photos, outings, workouts; past posts | — | Yours | Frequency settings; per-source switches; filters for people and dates | Vendor descriptions. Facebook's 2017 research post: people need to remove unwelcome memories (unverified, page blocked) |
| **Rewind / Limitless** | A timeline of the screen | Search | — | — | Bought by Meta; desktop app shutting down (note 20) |

**What studies say about people and AI memory views.**
- [E] In 2,050 ChatGPT memory entries from 80 users, 96% were created by the system on its own, 84% were directly grounded in what users said, and 28% held GDPR-defined personal data (Dash et al., WWW 2026). Without a view, people cannot know what their memory holds.
- [Unverified] In 20 interviews, most ChatGPT users were negatively surprised by what it remembered, and wanted more visibility and control ("Relational Gains, Privacy Strains", ACM 2026; abstract seen only in a search summary).

**Lessons.**
- [E] The products converge on a short overview. ChatGPT puts depth in the chat, NotebookLM turns a node click into a chat question, and Claude opens a topic in place.
- [E] None shows a person's ideas, their links, conflicts across contexts, or their work, and none has published how people use the view. They offer patterns, not evidence.
- [L] Borrow one-step corrections, "don't mention", per-project scope (already in DESIGN §5), and a click that becomes a chat question. Avoid one rewritten summary with no sources (note 23).

## 2. Research on display forms

### 2.1 Outline, map, cards or timeline

| # | Finding | Source |
|---|---|---|
| a | 47 students read a hypertext with a hierarchical map, a network map or an alphabetical list. The hierarchical map improved global comprehension for low-knowledge readers. For high-knowledge readers the form made no difference | Potelle & Rouet 2003 [E, abstract] |
| b | Studying a concept map beat studying an outline or list by g = 0.28 (k = 10), for students learning others' material. Building maps helps more than studying them (note 20, 1.1) | Nesbit & Adesope 2006, as reported by Schroeder et al. 2018 [E, secondary] |
| c | Reading or building argument maps improved immediate recall of arguments, in three experiments that also used hierarchical outlining, summarising and reading text. The abstract reports no comprehension effect | Dwyer, Hogan & Stewart 2013 [E, abstract] |
| d | **A glance at an AI-made map.** 14 undergraduates read one article as linear text and one through a GPT-4o-mini concept map, counterbalanced. With the map, rated mental demand fell 31.5% and time with the material rose 22.6%; the test was completed 14.1% faster, with about equal accuracy (97% against 98%, near ceiling) | Han & Choi, BEA 2025 [E] |
| e | For one's own past events, what happened is the best cue and dates are weak (note 23, H.2). Adding landmarks (holidays, news, photos, calendar events) to a timeline of personal search results reportedly sped up retrieval | Storms 2024 [E]; Ringel et al. 2003 [result unverified] |
| f | People recognized pages they had seen from titles and URLs about 90% of the time. Thumbnails needed about 144×144 pixels for 80% recognition | Kaasten, Greenberg & Edwards 2002 [unverified, secondary summary] |

**Lessons.**
- [L] A person knows their own ideas, so they read their overview as a "high-knowledge reader". By (a), shape should matter little for understanding; it matters for finding an idea fast and for seeing links and conflicts.
- [E] Row (d) is the first study found of glancing at an AI-made map. It maps a text, not a person's ideas, and is small. A map felt easier at equal accuracy.
- [L] A timeline should not be the main shape (e); a date can be a small mark on a work cue.
- [L] A one-line label is a strong cue, and a snapshot must be big enough to recognize (f). This matches "one line per item is enough" (GOAL §2).

### 2.2 Overview and detail

- [E] Overview+detail shows both side by side, zooming shows them one after the other, and focus+context puts the detail inside its context (Cockburn, Karlson & Bederson 2008; taxonomy only, conclusions not read).
- [E] With 32 people navigating maps, an overview made no difference to correctness. 80% preferred having one, saying it helped them keep track of where they were. On one of the two maps they were faster without it (Hornbæk, Bederson & Plaisant 2002).
- [E] In a five-day field study (n = 24), people kept chat central and used a synced canvas for overview, revisiting and alternatives (Amin et al. 2026; note 20, 2.5).
- [L] People want an overview more than it speeds them up. That suits a view opened rarely, before an interview or a decision (GOAL §2).

### 2.3 A stable layout

- [E] Spatial memory helps people re-find their own items, and rearranging breaks it (note 20, 1.7).
- [E] When a changing graph kept its layout, people oriented faster and with fewer errors, most when finding nodes and following paths (Archambault & Purchase, GD 2012). Other experiments by the same group found little effect on errors or memorability (2011, 2012).
- [E] Teevan's Re:Search Engine keeps the parts of a result list people are likely to remember, and puts new results only where old ones were forgotten, because people forget much of a list (UIST 2007). That it re-found as well without blocking new finds is unverified (search summary).
- [L] Dreaming restructures topics weekly (DESIGN §1.4). Apply Re:Search: viewed and pinned topics and ideas stay where they were; new, split or merged ones go into open space, marked "new since you last looked".

### 2.4 Re-finding, and your own work as cues

- [E] People said they reached their own files by navigation in 56–68% of retrievals and by search in only 4–15%, even with better desktop search; search was a last resort (Bergman et al. 2008, self-reports).
- [E] A cue works best when it was part of how the memory was formed, and images of one's own past bring it back (note 23, H.1 and H.8). The user said the same: "Seeing my real work brings it back" (GOAL §2).
- [E] People who wrote essays with an LLM struggled to quote their own work and felt the least ownership (Kosmyna et al. 2025, n = 54, preprint).
- [L] A browsable overview fits how people re-find their own things. A work cue should show the person's own artifact, not an AI paraphrase of it.

### 2.5 Showing human or AI origin

- [E] A week later, people recalled worse which ideas had involved an AI (Zindulka et al., CHI 2026; note 23, H.6).
- [E] 13 creative writers shown a visual record of their LLM use rated it 6.31, against 3.14 for a baseline, on usefulness for transparency (d = 2.27), and kept a sense of control and ownership (Hoque et al., CHI 2024; self-reports; figures read from the paper via search).
- [E] The user found three source tags on every line "too busy" (GOAL §2).
- [L] Store origin on every item but mark only the exception: an adopted idea carries a small "from Claude" or "from ChatGPT"; no mark means yours.

### 2.6 How much fits on a first screen

- [E] Attention holds about four chunks, and weak grouping, not size, caused disorientation (note 20, 1.2). Added depth hurt web search, and a medium breadth did best (Larson & Czerwinski 1998).
- [E] Claude's inline cards hold at most 4–5 data points; carousels hold 3–8 items (§3).
- [L] First screen: 3–5 topics, each with its two or three most used ideas, everything else one tap away. Two levels: topics, then ideas. Work sits inside an idea, not as a third level to navigate.

### 2.7 Conflicts between your own ideas

- [E] No study of showing conflicts between one person's ideas was found. Argument maps have evidence for building them (note 20, 1.3) and some for recall when reading them (2.1c). Edge crossings are a main cost in node-and-line layouts (note 20, 1.2).
- [E] Decision records mark a status (accepted, superseded) and link to what replaced them (note 20, 1.6).
- [L] Show a conflict as a side-by-side pair, each half with its context: "real builds: start with workflows" against what the person holds for interviews. Draw a line only when both ideas are in view. Keep "conflict" (both still held, in different contexts) apart from "replaced" (an old view given up).

### 2.8 Resurfacing schedules

- [E] Readwise shows highlights on a schedule; Apple Journal and Facebook push past items. Facebook added filters after unwelcome reminders (unverified).
- [L] The user opens the overview to prepare or check a decision, and the AI brings knowledge up in chat (GOAL §2). No push schedule is needed. A short "changed since you last looked" line serves the revisit.

## 3. What the surfaces allow

| Surface | What it can show | What it keeps | Links back |
|---|---|---|---|
| **Claude desktop chat, MCP App** | **Inline card:** height fits content, no scrolling inside, at most 2 actions and 4–5 data points, no drill-ins, menus or multiple views. **Inline carousel:** 3–8 cards, each an image, a title, up to 3 lines and one action. **Fullscreen:** for dashboards and visualizations, with collapsible sidebars, tabs or pages; the chat box stays visible. Widths from 320 px; on mobile the host caps inline height and clips. The host asks before it displays (note 22, C3, C9) | The spec defines no saved view state; restoring it is listed as future work. A view is rendered from its tool result | `ui/open-link` opens a URL in the browser; the host may refuse. Tools marked app-only fetch detail without the model. `ui/message` adds a user message to the chat |
| **ChatGPT** | The same three forms: cards with at most 2 actions, no scrolling inside and no tabs or deeper navigation; carousels of 3–8; fullscreen with the composer. Custom MCP needs a public HTTPS address or OpenAI's tunnel; write tools are documented for Business, Enterprise and Edu; Plus is unclear; whether Chat mode on Windows shows the UI is not stated (note 22, D2–D4, D9) | Widget state "belongs to one rendered UI instance"; lasting data belongs on the server | As above |
| **Claude Code** | Not listed as an MCP Apps host (note 22, E1). Replies are Markdown; tables and links render, and links are clickable in some terminals (user reports, unverified). In the Desktop Code tab a mod can draw a pane (note 22, A7) | Text in the transcript | URLs |

**What this means** [L]:
- The first view must be a small card: the topics only, with two actions, "Open overview" (fullscreen) and "Ask about a topic" (chat).
- The full outline or map lives in fullscreen. Opening an idea in place is allowed inside the app.
- Applying an idea to a problem needs the AI's judgment, so the guidelines send it to the chat, where the expansion is an ordinary reply. This gives expansion a clean place; it does not settle whether it is wanted (GOAL §2, 2026-10-24).
- Layout, pins and "seen" marks must live in Northstar's human structure (DESIGN §1.3), not in the panel.
- Work opens as a permalink or a viewer, never a path string (GOAL §2).
- The sketch round can test in Claude desktop chat now; ChatGPT waits on plan limits.

## 4. Candidates for the sketch round

All four share the same human structure (DESIGN §1.3) and the same rules:
- one-line work cues ("what you did there") with a snapshot or the key lines;
- origin marked only on adopted ideas;
- "open" items;
- lines the AI spotted but the person never stated appear only once confirmed (GOAL §2);
- one-tap corrections: "not what I think", "keep", "project only";
- no IDs or paths.

### A. Topic outline with conflict pairs
- **First view:** a card with 3–5 topics in the person's words, each with a count and its most used idea, and one line such as "2 conflicts · 3 open".
- **Drill in:** fullscreen shows two levels, topics as sections and ideas as one-liners. A conflict is a pair row inside its topic. A link to another topic is a short "also: <topic>" under the idea. Tapping an idea opens it in place: 1–3 work cues, origin if adopted, sources, corrections.
- **Compact (Claude Code):** the same outline as Markdown, at most 5 topics × 3 ideas, conflicts as "↔" pairs, work as links with one line each.
- **Evidence:** fits the inline rules and plain text; collapsible sections are the recommended in-app interaction (§3); a hierarchy helps orientation (2.1a); breadth beats depth (2.6); people navigate to their own items (2.4).
- **Risks:** it may "read like an answer", as four text formats did (2026-10-14); links across topics are weak; it may not feel like the "map ... but better and smarter" the user asked for.

### B. Stable topic map
- **First view:** the same card, with a small picture of the map's regions.
- **Drill in:** fullscreen shows topics as regions in fixed places and ideas as short claims inside them, with connect lines and a distinct conflict line labelled with its two contexts. New items sit in open space. Tapping an idea opens a side panel with work, origin, sources and corrections.
- **Compact:** a map cannot be text, so Claude Code uses A's outline.
- **Evidence:** the user picked "map", big picture, lines and topics (GOAL §2); a kept layout helps orientation (2.3); a glanced AI map felt easier at equal accuracy (2.1d); reading argument maps helped recall (2.1c).
- **Risks:** three map shapes were rejected for their shape (EXPLORATION §3); maps help their builders most (note 20, 1.1); edge crossings; it needs fullscreen; Dreaming's changes can push the layout.

### C. Work wall by topic
- **First view:** a carousel of 3–8 work cards for one topic, each a snapshot and one line.
- **Drill in:** a card opens the ideas it shows, with their links and origin.
- **Evidence:** the work-first sketch was "much closer" (GOAL §2); one's own work is the strongest cue (2.4); carousels fit the panel (§3).
- **Risks:** the user did not pick "work as the entries" for the overall display; ideas, links and conflicts drop to second place; code may not be recognizable at card size (2.1f).
- **Best use** [L]: the recall layer inside A and B, not a rival to them.

### D. Cheat-sheet table: ideas against contexts
- **First view:** rows are ideas grouped by topic; columns are the contexts the person used them in (real builds, interviews, side projects); each cell holds their position in a few words, and differing cells show a conflict.
- **Drill in:** a cell opens its work and sources.
- **Evidence:** the user found tables and cheat sheets helpful (GOAL §2); a crib sheet helps in the moment (note 20, 1.8); the user's main conflict example is across contexts (GOAL §1).
- **Risks:** it works only with few contexts; cells go empty; it is too wide for 320 px or an inline card; links across topics are lost.
- **Best use** [L]: a view for checking a decision, or a fallback.

## 5. Recommendation

**Compare A and B first** [L]. They answer the user's open request: an overall display "just like the maps in the last version, but better and smarter", with the big picture, topics and lines. Build both from the same items and work cues so only the shape differs; earlier rounds mixed content and shape (EXPLORATION §3). A also yields the compact form the Claude Code prototype needs (DESIGN §9). C becomes the work layer of both; D stays in reserve.

**How to compare them within the §8 overview test** [L]:
1. **Material:** the person's non-Northstar topics and work, using items they have confirmed, so the content is right before the shape is judged.
2. **Tasks:** §8's four set tasks of 5 minutes each, from the occasions the user named: preparing for something (including one open-world task, such as an interview) and checking a decision. One reading of §8: two matched tasks of each kind on different topics, one with the usual means (the apps' chat search and memory, repositories), one with the overview. In the overview arm, alternate A and B across the four kinds, in counterbalanced order.
3. **Bars:** §8's are unchanged: the overview wins at least 3 of 4 and loses none, with at most 1 line in 10 flagged "not what I think". A against B is read from the same tasks: which form's tasks were won, time to the first useful cue, which cue triggered recall (the line, the work or a link), and flags. End with both forms on one topic and a direct pick. With one rater and two tasks per form, this is directional only.
4. **First view:** start every overview task from the inline card, so the card is tested too.

**Revisit-only or expand** [L]. Run each overview task in two stages. The panel starts revisit-only. Then a visible "ask about this for my problem" step sends the idea and the task's problem to the assistant. Its answer follows the AI-side rules: no memory talk, with the person's items, their work and fresh thinking kept apart (note 20, §2).
- **Favours revisit-only:** most tasks finish without the step; or expansions do not change the answer; or they draw flags such as "presumes", "not what I think" or "reads like an answer".
- **Favours expand:** the step is taken in most tasks, mainly the open-world ones, and the person says it improved their answer, without those flags.
- **Either way:** keep the expansion in the chat, apart from the overview, quoting the person's work rather than paraphrasing it (2.4, 2.5).
- **Bias:** starting revisit-only favours revisit-only slightly; the open-world task is where expand must show its value.

## 6. Gaps and unverified items

- Still no study of glancing at an AI-made overview of one person's ideas; the nearest is 2.1d, an AI map of a text read by 14 students.
- No study of showing conflicts between one person's ideas, and no published data on how people use ChatGPT's or Claude's memory views.
- Unverified: Kaasten's thumbnail figures, Ringel's landmark result, Teevan's evaluation, Facebook's research post, the "Relational Gains" interviews, Gemini's current menus, Claude Code's link rendering, and whether ChatGPT's Chat mode on Windows shows panels.
- Not checked in depth: Tana, Mem, and Apple's and Google's photo "memories".

## Sources

**Products, and studies of their use**
- OpenAI, "Memory FAQ", help page, checked 2026-10-24. https://help.openai.com/en/articles/8590148-memory-faq
- OpenAI, ChatGPT memory and Dreaming, 4 Jun 2026. https://openai.com/index/chatgpt-memory-dreaming
- Anthropic, "Use Claude's chat search and memory to build on previous context", help page. https://support.claude.com/en/articles/11817273-use-claude-s-chat-search-and-memory-to-build-on-previous-context
- 9to5Google, Gemini personal context, 13 Aug 2025 (via search summary). https://9to5google.com/2025/08/13/gemini-personal-context/
- Google, "Use Mind Maps in NotebookLM", help page. https://support.google.com/notebooklm/answer/16212283?hl=en
- Heptabase wiki, "User Interface Logic" and "Heptabase 1.0". https://wiki.heptabase.com/user-interface-logic ; https://wiki.heptabase.com/version-one
- Obsidian Help, "Graph view". https://obsidian.md/help/plugins/graph
- Ferreira et al., "How People Manage Knowledge in their 'Second Brains'", arXiv 2509.20187, Sep 2025. https://arxiv.org/abs/2509.20187
- Readwise docs, "Reviewing highlights". https://docs.readwise.io/readwise/docs/faqs/reviewing-highlights
- Apple, Journal, App Store listing. https://apps.apple.com/app/journal/id6447391597
- Facebook Research blog, "Facebook memories: the research behind the products that connect you with your past", 6 Sep 2017 (page blocked; via search summary). https://research.facebook.com/blog/2017/09/facebook-memories-the-research-behind-the-products-that-connect-you-with-your-past/
- Dash et al., "The Algorithmic Self-Portrait: Deconstructing Memory in ChatGPT", WWW 2026, arXiv 2602.01450. https://arxiv.org/abs/2602.01450
- "Relational Gains, Privacy Strains: Exploring Users' Perceptions and Experiences with ChatGPT's Memory Feature", ACM, 2026 (abstract via search summary). https://dl.acm.org/doi/10.1145/3772318.3791635

**Display research**
- Potelle & Rouet, "Effects of content representation and readers' prior knowledge on the comprehension of hypertext", IJHCS 58(3), 2003. https://doi.org/10.1016/S1071-5819(03)00016-8
- Nesbit & Adesope, "Learning with concept and knowledge maps: a meta-analysis", Rev. Educ. Res. 76(3), 2006. https://www.sfu.ca/~jcnesbit/articles/nesbitadesope2006.htm
- Schroeder et al., "Studying and constructing concept maps: a meta-analysis", Educ. Psychol. Rev. 30(2), 2018. https://doi.org/10.1007/s10648-017-9403-9
- Dwyer, Hogan & Stewart, "An examination of the effects of argument mapping on students' memory and comprehension performance", Thinking Skills and Creativity 8, 2013. https://research.universityofgalway.ie/en/publications/an-examination-of-the-effects-of-argument-mapping-on-students-mem-6/
- Han & Choi, "Beyond Linear Digital Reading: An LLM-Powered Concept Mapping Approach for Reducing Cognitive Load", BEA 2025. https://aclanthology.org/2025.bea-1.58.pdf
- Storms, diary-study review, J. Cogn., 2024 (note 23). https://pmc.ncbi.nlm.nih.gov/articles/PMC10798175
- Ringel, Cutrell, Dumais & Horvitz, "Milestones in Time", INTERACT 2003. https://www.erichorvitz.com/landmark.htm
- Kaasten, Greenberg & Edwards, "How People Recognise Previously Seen Web Pages from Titles, URLs and Thumbnails", HCI 2002 (listing), and a secondary summary. https://grouplab.cpsc.ucalgary.ca/Publications/ShawnKaasten ; https://www.donotlick.com/thumbnails-titles-and-urls-how-users-recognize-representations-of-websites/
- Cockburn, Karlson & Bederson, "A review of overview+detail, zooming, and focus+context interfaces", ACM Computing Surveys 41(1), 2008. https://www.microsoft.com/en-us/research/wp-content/uploads/2008/01/cockburn-ComputingSurveys09.pdf
- Hornbæk, Bederson & Plaisant, "Navigation patterns and usability of zoomable user interfaces with and without an overview", TOCHI 9(4), 2002. https://lccd.umiacs.umd.edu/node/16152
- Amin et al., "Conversations in Space", arXiv 2605.15848, 2026 (note 20). https://arxiv.org/abs/2605.15848
- Archambault & Purchase, "Mental map preservation helps user orientation in dynamic graphs", GD 2012; with their 2012 memorability study and 2011 TVCG study. https://eprints.gla.ac.uk/78675 ; https://eprints.gla.ac.uk/66915 ; https://research.monash.edu/en/publications/animation-small-multiples-and-the-effect-of-mental-map-preservati/
- Teevan, "The Re:Search Engine: Simultaneous Support for Finding and Re-Finding", UIST 2007. https://www.microsoft.com/en-us/research/?p=157104
- Bergman et al., "Improved search engines and navigation preference in personal information management", TOIS 26(4), 2008. https://doi.org/10.1145/1402256.1402259
- Tulving & Thomson 1973 (note 23). https://doi.org/10.1037/h0020071
- Sellen et al., CHI 2007 (note 23). https://doi.org/10.1145/1240624.1240636
- Kosmyna et al., "Your Brain on ChatGPT", arXiv 2506.08872, 2025, preprint. https://arxiv.org/abs/2506.08872
- Zindulka et al., CHI 2026 (note 23). https://arxiv.org/abs/2509.11851
- Hoque et al., "The HaLLMark Effect", CHI 2024, arXiv 2311.13057. https://arxiv.org/abs/2311.13057
- Larson & Czerwinski, "Web page design: implications of memory, structure and scent for information retrieval", CHI 1998. https://www.microsoft.com/en-us/research/publication/web-page-design-implications-memory-structure-scent-information-retrieval/

**Surfaces**
- MCP Apps overview, modelcontextprotocol.io. https://modelcontextprotocol.io/extensions/apps/overview
- MCP Apps specification, version 2026-01-26. https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/2026-01-26/apps.mdx
- Claude, MCP Apps design guidelines. https://claude.com/docs/connectors/building/mcp-apps/design-guidelines
- OpenAI, Apps SDK UI guidelines. https://developers.openai.com/apps-sdk/concepts/ui-guidelines
- OpenAI, Apps SDK state management. https://developers.openai.com/apps-sdk/build/state-management
- Claude Code link rendering, user issue reports on a third-party mirror. https://claudeissues.com/issue/37808-markdown-links-in-tables-expand-to-full-url-instead-of-showing-short-link-text ; https://claudeissues.com/issue/78294-markdown-links-in-responses-are-not-clickable-in-terminal-ghostty-need-raw-url-f

**Earlier notes and project documents** (in this repository)
- Note 20, [`round4/20-index-expansion-capture.md`](../round4/20-index-expansion-capture.md): Cowan, Krieglstein, Ware, Robertson, Czerwinski, Scarr, Dickson and Miller, argument maps, decision records.
- Note 22, [`round5/22-surface-facts.md`](../round5/22-surface-facts.md): C3, C9, D2–D4, D9, E1, A7.
- Note 23, [`round5/23-memory-architecture-and-dreaming.md`](../round5/23-memory-architecture-and-dreaming.md) §1 and §4.
- [`GOAL.md`](../../GOAL.md), [`DESIGN.md`](../../design/revision-2026-10-23/DESIGN.md), [`EXPLORATION.md`](../../EXPLORATION.md).
