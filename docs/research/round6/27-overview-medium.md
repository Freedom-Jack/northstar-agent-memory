# Round 6 research (27): where the overview appears, in the chat, as an app inside it, or as a mind map

**Date:** 2026-10-28. **Why:** after the look-and-react round, the user named this gap (GOAL §1, 2026-10-28): "what is missing is the view of this human whether it's just blend into ChatGPT or Claude, it uses some sort of UI the maps you give me, or some mind map, that you do the research on those as well." All four mock-up rounds showed the overview as a page on this Mac. None showed it inside Claude or ChatGPT.
**Read with:** [`GOAL.md`](../../GOAL.md) §1 and §2 (the human-view rows of 15 Oct to 28 Oct); notes [25](25-overview-display.md) §1 and §3, [26](26-best-form-synthesis.md), [26b](26b-visualizing-own-ideas.md) §2.4, [26d](26d-products-and-use.md) and [22](../round5/22-surface-facts.md) §C–§E; [`DESIGN.md`](../../design/revision-2026-10-23/DESIGN.md) §6. This note builds on them without repeating them.
**Question:** which medium best serves the user's three needs: (1) the big picture, (2) getting back into a piece of work, (3) questions about their past? The options:
1. plain chat answers in Claude or ChatGPT, with no UI of Northstar's own;
2. an app inside the chat: a small card that opens a full-screen map (MCP Apps in Claude, the Apps SDK in ChatGPT);
3. a mind map like NotebookLM's, where clicking a node asks the chat;
4. anything else the evidence supports.

**Method:** one desk pass on 2026-10-28 in the main session, about 15 searches and page reads on top of notes 25–26. No research agents were run.
- **Tags:** **[E]** = a source shows it (opened today, or in the earlier note named); **[L]** = inference; **unverified** = seen only in a search summary or a secondary source.
- **Strength:** **strong** = several primary sources agree and some use data exists; **moderate** = several sources or products converge, or one field study; **weak** = one small study, vendor claims or anecdotes; **none** = inference only.
- Findings constrain the HOW only (GOAL §5). No personal data was read; the 28 Oct round enters only as counts.

**Short answer.**
- No vendor or study publishes how people use an app inside a chat, or NotebookLM's mind map. Note 26d found the same gap for memory views and graphs [E].
- **The one field study of chat with a synced visual view:** people kept the chat at the centre and used the visual view for overview and revisiting. Uptake was uneven, and switching between the views cost effort (Amin et al. 2026, 24 people, five days) [E, moderate].
- **Claude's and OpenAI's own rules for apps in a chat draw the same line.** The app shows and handles what needs seeing, such as maps and visualizations. Questions, follow-ups and anything that needs the AI's judgment go to the chat. Claude's guide says not to rebuild chat inside an app [E].
- So the three needs split [L]:
  - **the big picture** needs a view that Northstar draws, with the same layout each visit and the user's exact words. A chat reply is written afresh every time, and the user turned down four text formats because they "read like an answer from Claude/ChatGPT" (GOAL §1, 14 Oct);
  - **questions about the past** work best as ordinary chat answers that quote the record, where products converge most strongly (note 26d);
  - **getting back into work** fits a chat answer too, with a small card when there is work to see.
- **NotebookLM's mind map:** copy its click-to-ask, not its shape. It is a tree of a source's topics, so it cannot draw a conflict between two branches, which is the user's main example. It is regenerated rather than edited, and no use data exists [E for the facts, L for the fit].
- **Recommendation [L]: chat first, map on request.** It combines options 1 and 2 and borrows option 3's click-to-ask. **Strength:** moderate for the split; weak for how often an in-chat map gets used.
- **The choice for the user:** this, or one of the alternatives in §5.

---

## 1. The options, and where each runs

| Option | What the user sees | Claude desktop chat | ChatGPT | Claude Code, Codex |
|---|---|---|---|---|
| **1. Chat only** | Ordinary replies, written by the assistant from Northstar's recall tool | Yes, through a local or remote MCP server (C1, C2) | Yes, if the plan allows custom tools; needs a public address or OpenAI's tunnel (D2–D4) | Yes |
| **2. App in the chat** | A small card in the reply (at most 4–5 data points and two actions) that opens a full-screen view; the chat box stays visible | Yes: desktop, web, and the iPhone in a native web view. Claude asks before an app displays (C3, C9) | Renders MCP Apps (D9), with the same tool limits as option 1; whether Chat mode on Windows shows them is not stated | Not listed as MCP Apps hosts (E1), so text instead. The desktop Code tab can draw a pane through a mod (A7) |
| **3. Mind map** | A branching tree of topics; selecting a node asks about it in the chat | As option 2, if Northstar builds it | As option 2 | A text outline |
| **4. A visual Claude draws in its reply** | Claude writes a chart or diagram inside its reply from Northstar's data | Yes, on all plans since 12 Mar 2026 (apps not listed); temporary (§2.5) | Not checked | No |

IDs refer to note 22, checked 2026-10-23 [E].

## 2. What is new since notes 25–26

### 2.1 Chat with a visual view: the one field study

Amin et al. (arXiv 2605.15848, v2 of Sep 2026) gave 24 people a chat whose conversation also appeared as a synced canvas, for five days of their own knowledge work [E]:
- 47.2% of logged events were in the chat and 28.3% on the canvas (11.4% in the sidebar). The canvas view was open longer on average, 34.1 minutes against 13.0, but that is wall-clock time and may include idle time.
- On the canvas, zooming was the most common action (881 times), then selecting nodes (246). The paper's measures of going back were 132 timeline clicks and 93 branch openings.
- Uptake was uneven. One participant never used the canvas, out of habit; another found switching between the views confusing.
- The authors read the result as a division of labour, not a replacement: chat for quick back-and-forth, the canvas for organizing, revisiting and managing directions.
- **Limits:** mostly experienced users, only five days, and the canvas showed a conversation, not a person's own ideas.

**Strength:** moderate for "chat stays central, and a visual view earns its place for overview and revisiting"; weak for transfer to an overview of one's own ideas.

### 2.2 What the vendors' rules say about apps in the chat

Claude's MCP Apps design guidelines, read today [E]:
- An app should extend the conversation, not sit beside it as a separate app. It suits a task the user can finish inside the conversation.
- **Avoid:**
  - long or static content better read elsewhere;
  - deep navigation: drill-ins, breadcrumbs, several views;
  - chat inputs that copy Claude's own features.
- **Inline:** a brief summary with optional expansion. **Full screen:** visualizations and dashboards; the composer stays visible, and the chat keeps its context.
- **Inside the app:** expanding and collapsing, and clicking points in a visualization. **In the chat:** follow-up questions, moving to another topic, and anything that needs Claude's interpretation.
- **Display modes:** inline, full screen and picture-in-picture.

OpenAI says much the same [E]:
- Its plugin docs say to add UI only when seeing or handling something materially improves part of the task, such as inspecting, comparing or navigating structured information.
- A developer write-up on OpenAI's blog (credited to Alpic; date not shown) gives three modes: inline for quick interactions, full screen for widgets that need space such as maps, and picture-in-picture when a widget stays relevant during follow-ups.

**A shared standard.** MCP Apps became an official MCP extension on 26 Jan 2026, co-developed by Anthropic and OpenAI from MCP-UI and the Apps SDK. Claude supported it at launch and ChatGPT later that week [E, secondary reports]. So one build can render in both, though each host has its own quirks.

**Lessons [L]:**
- A map is the textbook case for an app in the chat. An ask box inside it is what Claude's guide says to avoid.
- The 28 Oct page put all three ways in (map, "where you left off", ask) on one page. Under these rules, two of them belong in the chat.

### 2.3 Plain chat answers for looking back

**For chat** [E]:
- **Questions about one's past:** products converge on cited chat answers that jump to the source (ChatGPT, Claude, Gemini, NotebookLM, Granola, Heptabase, Notion). This is strong convergence, with moderate use evidence (note 26d §7).
- Copilot's memory view is itself a chat answer, and ChatGPT sends depth to the chat (note 26d §1).
- **The user's own tries:**
  - On 27 Oct the user tried "Ask about this" twice, both times with a question about their own past, and said "I'd use it" (GOAL §2).
  - On 28 Oct the page logged 2 asks and 11 map clicks, and no "where you left off" card was opened.
- **The answer must come from the record.** ChatGPT's memory answered 57.7% of questions correctly, against 91.8% for the same model reading the full history (LongMemEval; note 26a, 4.4). Northstar's recall tool reads the history word for word (DESIGN §1).

**Against chat, for the big picture** [E]:
- The user turned down four research-based text formats: "Still they all read like an answer from Claude/ChatGPT or whatever, not a real helpful format" (GOAL §1, 14 Oct).
- In a formative study of 10 people, chat with an LLM gave long-winded answers that were hard to take in quickly and to work with. The authors put this down to text and the linear chat (Graphologue, UIST 2023; abstract only).
- Google's raters strongly preferred interfaces generated for each prompt over standard LLM answers in markdown or plain text, when speed was ignored. Pages made by human experts were preferred most (Google Research, 18 Nov 2025; the paper's figures were not read).
- **A reply is written afresh each time.** Stable layouts help orientation (note 25 §2.3), and an AI's rewording can change what people remember (note 26b §3.2). Northstar cannot hold a chat reply's order or words fixed, but it can hold its own view's.

**Strength:** strong convergence that questions belong in the chat; weak to moderate that chat text is the wrong medium for the big picture. Here the user's own verdicts carry the most weight.

### 2.4 NotebookLM's mind map, and mind maps

Google's help page (the product is now Gemini Notebook), read today [E]:
- **Making it:** one tap builds the map from the uploaded sources, as a branching diagram of main topics. It is saved as a note in the Studio panel.
- **Using it:** you can zoom, and expand or collapse branches. Selecting a node asks about it in the chat. The map can be downloaded, or shared with the notebook.
- **Changing it:** to regenerate, you delete the note and generation starts again. The page does not mention editing; competitors' pages say it cannot be edited [unverified, competitor claims].
- **Limits:** not on the mobile app, and usage limits apply.
- **Use:** no figures. Reviews are anecdotes, mostly praising how it shows topics connecting before you read [E, weak]. No controlled study was found.

Mind maps in general: the evidence is about students making them while studying, and it is weak (note 26b §2.4).

**Lessons [L]:**
- **Copy the interaction:** select an entry, and the chat answers about it. This matches the vendors' split (§2.2).
- **The shape fits the user's ideas less well.** A tree puts each idea under one parent. A conflict across contexts (real builds against interviews) then sits in two branches with no line between them. A map that draws lines for the idea in focus can show it (note 26 §4).
- **NotebookLM summarizes sources a person uploaded.** Northstar's map holds the user's own ideas, kept stable between visits. Regenerating the map from scratch on every visit would undo that.

### 2.5 A visual the AI draws in its reply

- Since 12 Mar 2026, Claude can draw charts and diagrams inside its replies. The feature is in beta, on all plans and on by default; Claude draws one when it judges it helps, or when asked. Unlike artifacts, these visuals are temporary: they change as the conversation goes on [E].
- Google's generative UI points the same way (Gemini's dynamic view, 18 Nov 2025). Google states two limits: generation can take a minute or more, and outputs have occasional errors [E].

**Lessons [L]:**
- This needs no app of Northstar's own. But the AI would redraw and reword the map each time, losing the stable layout and exact words the big picture needs.
- It runs only where the vendor offers it.
- It suits a one-off picture inside an answer, not the overview.

### 2.6 What is not known

- No published use data for apps in ChatGPT or Claude, beyond launch partners and vendors' reach figures. The searches found only marketing blogs [E for the absence].
- No study compares a chat answer with an in-chat view for revisiting anything.

## 3. The options against the three needs

| Option | 1. Big picture | 2. Back into a piece of work | 3. Questions about my past | Strength |
|---|---|---|---|---|
| **1. Chat only** | Weak fit: worded afresh each time, no lines, and the medium the user turned down on 14 Oct | Good: last state, last steps, next step and links into the work, but no picture of the work | **Best fit** | Strong convergence for need 3; weak to moderate against chat for need 1 |
| **2. App in the chat** | **Best fit:** drawn by Northstar from the human structure, with the same layout, exact words and lines for the idea in focus | Fair: a carousel of 3–8 snapshots of the user's work fits; a separate "where you left off" panel went unopened on 28 Oct | Weak: asking from inside the app duplicates the chat | Moderate for the split (§2.1, §2.2); weak for use |
| **3. Mind map** | Fair: topics with expand and collapse, but no conflict lines, and regenerated | Weak: it shows topics, not work | Its click-to-ask is good, as a way into the chat | Weak |
| **4. AI-drawn visual** | Weak: redrawn and reworded each time; Claude only | Not suited | Not suited | Weak |

## 4. Recommendation: chat first, map on request [L]

**How it appears:**
- **A question about the past** ("what did I decide about X?"): an ordinary reply in Claude or ChatGPT, and in Claude Code and Codex too.
  - Exact matches from the user's own record come first, each with where it came from and a link; then a short answer.
  - Where the app can show cards, Northstar can draw the matches as a small card, so the user's words appear exactly as they were. The assistant's answer follows (the Ask Photos lesson, note 26d §3).
- **Getting back into a piece of work** ("where did I leave the website?"): a reply with the last state, the last few steps, what changed since and the stated next step, plus one step into the work. Where cards render, a small row of the work itself (a snapshot and one line each) comes with it, because "Seeing my real work brings it back" (GOAL §2).
- **The big picture** ("show my map"): a small card in the reply opens the smarter map full screen inside Claude, and inside ChatGPT where the plan allows.
  - It holds topics in the user's words, a few entries each with their work, lines for the idea in focus, and the same places on each visit (note 26 §4).
  - Selecting an entry asks the chat, and the answer appears in the chat beside the map.
  - There is no ask box in the map.
- **In Claude Code and Codex:** the same replies, with the big picture as a short outline. A pane in the desktop Code tab is possible later (A7).

**Why:**
- Each need goes where its evidence is strongest (§3).
- It is the split the vendors' own app rules prescribe, and the pattern the one field study found (§2.1, §2.2).
- **It keeps what the user asked for** (GOAL §2, 15 Oct and 28 Oct):
  - "In the assistant, when I ask", in ChatGPT or Claude, "not a self created one";
  - a map for the big picture ("Map", 15 Oct; "Smarter map first", 28 Oct);
  - "still towards assistant as I can ask questions";
  - their real work bringing ideas back.
- **It stays product-agnostic.** Two of the three needs need no UI, so they work in any harness. The map uses the standard that both Claude and ChatGPT render.
- **The map opens inside the conversation where the user is preparing.** So the chat knows the task, and can show the part of the map that matters and answer about it. On 28 Oct the material was finished work with no task at hand. Note 26c drew the same inference from practitioners: an overview opened for a purpose should use that purpose.

**What it changes:**
- DESIGN §6 already put a card and a full-screen view in Claude.
- This moves "where you left off" and "ask" out of the overview page into ordinary chat replies, drops the ask box from the map, and adds select-to-ask.
- It leaves the human structure, the map's content and every GOAL row as they are.

**Risks:**
- **No use data.** The map may be opened seldom, as the canvas was for some people in Amin et al. That suits a view the user expects to open "Rarely, if chat does it" (GOAL §2, 15 Oct).
- **The assistant chooses when to call a tool,** so the user may need to ask for the map by name. Claude also asks before an app displays (C3).
- **Chat replies can reword.** The recall tool returns exact quotes, and the card shows them as they are. But the assistant writes its own answer, and Northstar gives it no usage rules (GOAL §2, 15 Oct).
- **ChatGPT** needs a public address or a tunnel, and its personal-plan limits are unclear (D2–D4). Claude comes first.
- **Switching between map and chat costs effort** (§2.1). In Claude, full screen keeps the chat box visible, which reduces the cost.

**How it would be judged:** inside Claude, on work the user is doing at the time, during the prototype (DESIGN §9). It would use the DESIGN §8 overview test for each need, not another page on this Mac.

**Goal check:** this changes only the medium, which is the HOW (GOAL §5). "Chat only" would drop the map the user asked for (GOAL §2, 15 Oct), so it stays the user's call rather than a recommendation.

## 5. The choice for the user

How should the overview appear?
- **Chat first, map on request** (recommended): §4.
- **Map app first:** one full-screen app inside the chat, holding the map, "where you left off" and ask. This is the 28 Oct page, but inside Claude.
- **Chat only:** no UI of Northstar's own. It works in every app, but there is no map.
- **Mind map:** the big picture as a NotebookLM-style tree; clicking a branch asks the chat.

## 6. Gaps and unverified items

- **Unverified:**
  - Google's preference figures (the paper was not read);
  - Graphologue's user study (only the formative study, from the abstract);
  - whether NotebookLM's map can be edited (competitor claims only);
  - the date ChatGPT first supported MCP Apps (secondary reports);
  - whether MCP Apps render in the Claude desktop Code tab;
  - whether select-to-ask works the same way in ChatGPT.
- **Not checked:** Sensecape's results, use of Gemini's dynamic view, and ChatGPT's own in-reply visuals.
- **No study** compares chat answers with an in-chat view for revisiting one's own material.

## Sources

**New in this note** (read 2026-10-28 unless marked)
- Amin, Adatepe, Fernandes, Buschek & Butz, "Conversations in Space: Non-Linear LLM Interaction in Everyday Use", arXiv 2605.15848, v2 Sep 2026 (HTML version). https://arxiv.org/abs/2605.15848 ; https://arxiv.org/html/2605.15848v2
- Claude, "Design guidelines" for MCP Apps. https://claude.com/docs/connectors/building/mcp-apps/design-guidelines
- OpenAI, "Brainstorm plugin use cases", plugin docs (reached from the Apps SDK UX principles address). https://developers.openai.com/apps-sdk/concepts/ux-principles
- OpenAI developer blog, "15 lessons learned building ChatGPT Apps", credited to Alpic (date not shown). https://developers.openai.com/blog/15-lessons-building-chatgpt-apps
- Alpic, "MCP Apps goes official: Claude and ChatGPT support", Jan 2026 (secondary, via search summary). https://alpic.ai/blog/mcp-apps-goes-official-claude-chatgpt-support
- The New Stack, "Anthropic extends MCP with an app framework", Jan 2026 (secondary, via search summary). https://thenewstack.io/anthropic-extends-mcp-with-an-app-framework/
- WorkOS, "MCP Apps", 27 Jan 2026 (secondary, via search summary). https://workos.com/blog/2026-01-27-mcp-apps
- Anthropic, "Claude now creates interactive charts, diagrams and visualizations", 12 Mar 2026. https://claude.com/resources/articles/claude-builds-visuals
- Leviathan, Valevski, Natchu & Matias, "Generative UI: A rich, custom, visual interactive user experience for any prompt", Google Research blog, 18 Nov 2025 (the paper "Generative UI: LLMs are Effective UI Generators" was not read). https://research.google/blog/generative-ui-a-rich-custom-visual-interactive-user-experience-for-any-prompt/
- Jiang, Rayan, Dow & Xia, "Graphologue: Exploring Large Language Model Responses with Interactive Diagrams", UIST 2023, arXiv 2305.11473 (abstract). https://arxiv.org/abs/2305.11473
- Google, "Use Mind Maps in NotebookLM", help page, now for Gemini Notebook. https://support.google.com/notebooklm/answer/16212283?hl=en
- Xmind, "Export NotebookLM mind map" (competitor claim, via search summary). https://xmind.com/blog/export-notebooklm-mind-map
- MindMap AI, "MindMap AI vs Google NotebookLM" (competitor claim, via search summary). https://mindmapai.app/compare/google-notebook-lm-vs-mindmap-ai
- Digital Trends, "I underestimated this NotebookLM feature until it completely changed how I study" (anecdote, via search summary). https://www.digitaltrends.com/cool-tech/i-underestimated-this-notebooklm-feature-until-it-completely-changed-how-i-study/

**Earlier notes and project documents** (in this repository)
- Note 22, [`round5/22-surface-facts.md`](../round5/22-surface-facts.md): A7, C1–C3, C7, C9, D2–D4, D9, E1.
- Note 25, [`round6/25-overview-display.md`](25-overview-display.md): §1, §2.3, §3.
- Note 26, [`round6/26-best-form-synthesis.md`](26-best-form-synthesis.md), with [26a](26a-refinding-and-resumption.md) 4.4, [26b](26b-visualizing-own-ideas.md) §2.4 and §3.2, [26c](26c-practitioner-writing.md) and [26d](26d-products-and-use.md) §1, §3 and §7.
- [`GOAL.md`](../../GOAL.md) §1 and §2; [`DESIGN.md`](../../design/revision-2026-10-23/DESIGN.md) §1, §6, §8 and §9.
