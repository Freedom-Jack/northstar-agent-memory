# Round 4 research: a glanceable index, on-demand expansion, and capturing actual work

**Date:** 2026-10-15. **Read with:** [`GOAL.md`](../../GOAL.md) §2 and §3.2 (answers of 2026-10-15), and [`EXPLORATION.md`](../../EXPLORATION.md) §3.
**Questions:**
1. What makes a map of one person's own ideas and work glanceable?
2. How can an AI assistant expand an index entry for a new, open-ended problem without falling back on fixed explanations?
3. How can work beyond chats (repositories, diagrams, documents, decisions, images) be captured and linked on Windows, iOS and Mac?

**Method:** one desk-research pass, with spot checks of the newest claims. **[V]** means the page was opened and read. **[S]** means the claim was seen only in search summaries or secondary sources. Dates are publication or last-update dates. "Undated" marks living vendor pages. Findings constrain the HOW only (GOAL.md §5).

---

## 1. Glanceable maps of one person's ideas

| # | Finding | Source |
|---|---|---|
| 1.1 | Concept maps help most when the learner **builds** them. Using an existing map helps less: overall g ≈ 0.58, constructing ≈ 0.72, studying ≈ 0.43. Effects vary widely between studies. | Nesbit & Adesope, *Rev. Educ. Res.* 76(3), Sep 2006 [V]; Schroeder et al., *Educ. Psychol. Rev.* 30(2), 2018 (online Mar 2017) [g values S] |
| 1.2 | Legibility depends on structure more than size. Weak grouping increased disorientation, while cutting 77 nodes to 50 made no difference. Edge crossings and broken paths are the main layout costs. Focus of attention holds about 4 chunks. | Krieglstein et al., *ETR&D* 70(1), 2022 [V]; Ware et al., *Information Visualization* 1(2), 2002 [S]; Cowan, *BBS* 24(1), 2001 [S] |
| 1.3 | Argument and issue maps (IBIS: question, idea, pro/con; Compendium; Kialo) have controlled evidence only for **training people to build them**. No study tests glancing at a map someone else made. | Dwyer, Hogan & Stewart, *Metacognition & Learning* 7(3), 2012 [V]; Twardy, *Teaching Philosophy* 27(2), 2004 [S] |
| 1.4 | The best-documented failure is maintenance. Capture overhead kills argument maps unless they give value at once. People reject more formal structure than they need. Opportunistic search beats elaborate filing. People reach things in small contextual steps ("orienteering"). | Buckingham Shum et al., KMi-05-18, 2006 [S]; Shipman & Marshall, *CSCW* 8(4), 1999 [V]; Whittaker et al., CHI 2011 [S]; Teevan et al., CHI 2004 [S] |
| 1.5 | Wardley maps put components by visibility to a user need and by stage of evolution, and they show movement over time. Applying this to a person's ideas is an analogy with no evidence. Personal sites carry status instead: gwern's status and confidence tags, and digital-garden "seedling / budding / evergreen". | Learn Wardley Mapping, "Landscape", undated [V]; gwern.net "About", living page [V]; Appleton, "A Brief History & Ethos of the Digital Garden", undated [V] |
| 1.6 | Lab notebooks and decision records index by **date, title and a link to the versioned artifact**. Decision records are append-only, with a status (proposed, accepted, superseded) and a link to the record that supersedes them. | Schnell, *PLOS Comput Biol*, 10 Sep 2015 [V]; Microsoft Learn, "Maintain an architecture decision record", updated 2026-04-13 [V] |
| 1.7 | Spatial memory helps retrieval of one's **own** stored items, and thumbnails help at first. Interfaces that move or rearrange items break spatial memory. The evidence is about web pages and commands, not maps of ideas. Canvas tools (Heptabase, Obsidian Canvas, TheBrain) have only vendor claims. | Robertson et al., UIST 1998 [V]; Czerwinski et al., INTERACT 1999 [V]; Scarr, Cockburn & Gutwin, *Found. Trends HCI* 6(1), 2013 [S] |
| 1.8 | Crib sheets: making one does not improve learning, while having one can help in the moment. The benefit is retrieval, not learning. | Dickson & Miller, *Teaching of Psychology* 32(4), 2005 [V]; Dickson & Bauer, *Teaching of Psychology* 35(2), 2008 [V] |

**Lessons.**
- No study supports glancing at an AI-made map of someone's ideas. The evidence favours maps people build themselves, and one's own items found by place or thumbnail.
- If a map is used: keep a few groups, use short claims rather than topic names, make conflict its own edge type, keep the layout stable between visits, and show each item's status.
- An index entry in the lab-notebook style is a date, a title and a link to the real artifact, with depth kept off-screen.

## 2. Expanding an entry for a new problem

| # | Finding | Source |
|---|---|---|
| 2.1 | GraphRAG precomputes community summaries and answers global questions by query-focused summarization over them. Indexing is expensive, and the repository is "largely in maintenance mode". | Edge et al., arXiv 2404.16130, Apr 2024 (v2 Feb 2025) [V]; microsoft/graphrag README, undated [V] |
| 2.2 | LazyGraphRAG defers all LLM work to query time. The vendor reports indexing at about 0.1% of GraphRAG's cost, with comparable global-search quality. RAPTOR precomputes a summary tree. Both are built around a corpus, not around the problem being solved. | Microsoft Research blog, 25 Nov 2024 [V]; Sarthi et al., arXiv 2401.18059, Jan 2024 [V] |
| 2.3 | On-demand node expansion (Sensecape: explain, questions, subtopics; Graphologue: diagrams from LLM text) increased exploration in small studies (n=12 and n=7). Diagrams that don't match the user's mental model were hard to follow. | Suh et al., UIST 2023, arXiv 2305.11483 [V]; Jiang et al., UIST 2023, arXiv 2305.11473 [V] |
| 2.4 | Luminate counters "rapid convergence" by first generating dimensions specific to the problem, then responses along them. Selenite keeps sources apart: criteria come from the model, options come from pages the user actually read, and each is tied to its evidence. | Suh et al., CHI 2024, arXiv 2310.12953 [V]; Liu et al., CHI 2024, arXiv 2310.02161 [V] |
| 2.5 | In a five-day field study (n=24), people kept chat central. They moved to a synchronized canvas for overview, for revisiting and for alternatives, and adoption was uneven. | Amin et al., "Conversations in Space", arXiv 2605.15848, May 2026 (v2 15 Sep 2026) [V, spot-checked] |
| 2.6 | Source-grounded answering: NotebookLM, renamed Gemini Notebook on 16 Jul 2026, answers from uploaded sources with inline citations. | Google blog, 16 Jul 2026 [V, spot-checked]; Google Help, undated [V] |
| 2.7 | Memory profiles raised agreement with the user by the most (up to +45%). Perspective sycophancy rose when the model could infer the user's view. | Jain et al., arXiv 2509.12517, Sep 2025 (v3 Feb 2026) [V]; Sharma et al., ICLR 2024 [S] |

**Lessons.**
- Precompute the index (entries, links, pointers to work), not the prose. Write each expansion when it is asked for, from the current problem.
- Keep three sources visibly apart in an expansion: the person's own items, their actual work, and the model's own fresh thinking.
- Output how the idea applies to the problem: where it applies, where it conflicts, and what is missing. Do not output a definition.
- To limit echo, let the model work on the problem before it reads the stored positions. This matches the AI side's fresh-first hypothesis and is untested here.
- Overview and depth can live in different places. Chat stays central, and the overview is visited when needed.

## 3. Capturing and linking actual work

| # | Finding | Source |
|---|---|---|
| 3.1 | Git records author and committer separately. Both can be set by hand, so neither is tamper-evident. AI co-author trailers are configurable, so they are only a soft signal. A pinned permalink pins content to a commit SHA. | git-scm.com docs, undated [V]; GitHub Docs, "Getting permanent links to files", undated [V] |
| 3.2 | Hosted activity feeds are short-lived. The GitHub Events API keeps 30 days and 300 events. Graph `/insights/used` (viewed vs modified) stops returning data after **November 2026** and never supported personal Microsoft accounts. Rewind/Limitless was acquired by Meta on 5 Dec 2025 and its desktop software is being shut down. | GitHub Docs, "REST: Events", undated [V]; Microsoft Learn, updated 2026-02-06 [V, spot-checked]; TechCrunch, 5 Dec 2025 [V] |
| 3.3 | Claude Code writes plaintext JSONL per session and deletes it after 30 days by default (`cleanupPeriodDays`). The format changes between versions. Codex's session layout is documented only unofficially. | Anthropic, Claude Code docs "Manage sessions" and "Settings", fetched 2026-10-15 [V]; Vaughan, 1 Jun 2026 [S] |
| 3.4 | Diagram files are machine-readable. draw.io is XML, and its PNG/SVG exports can embed the diagram. Excalidraw is JSON. A diagram committed to git inherits git authorship. | diagrams.net FAQ, undated [V]; Excalidraw docs, undated [V] |
| 3.5 | On iOS, passive capture is blocked by the limited photo library and other platform limits. The routes are user-initiated: the Share extension, Shortcuts and the photo picker. Screenshots are flagged, and Live Text OCR is available on recent devices. | Apple Developer docs, © 2026 [V]; VisionKit ImageAnalyzer [S] |
| 3.6 | Windows Recall is opt-in and local, with encryption bound to Windows Hello. It runs only on Copilot+ PCs, and fewer than 10% of Windows 11 PCs can run it, per GeekWire. Security criticism continues. | Microsoft Learn, "Recall overview", updated 2026-02-03 [V]; GeekWire, 15 Apr 2026 [V] |
| 3.7 | IDs are stable across rename and move: OneDrive item IDs and Drive file IDs. Paths break. File watchers see changes, not people. On Windows the change buffer can overflow and force a rescan, while macOS FSEvents can replay from an event ID. | Microsoft Learn, updated 2026-05-14 and 2025-07-01 [V]; Google Drive API guide, undated [V]; Apple FSEvents guide (archive) [V] |

**Lessons.**
- Treat "got my hands on" as an evidence ladder, and store the kind of evidence with each pointer:
  - strong: authored, committed or decided (git author, a committed diagram or decision record);
  - medium: AI-session edits and trailers;
  - weak: viewed or opened;
  - not evidence: screen presence.
- Keep a local, append-only ledger of pointers, because vendor activity feeds expire. Copy AI-session logs before the 30-day purge, and treat them as private plaintext.
- Store each pointer as a stable ID, a content hash, a human label and a permalink, and resolve it lazily.
- Platforms: on Windows and Mac, git and AI-session logs are dependable, and the Mac also has Spotlight and FSEvents. On iOS, capture is explicit only (Share, Shortcuts). Do not depend on Recall.

## 4. Gaps

- No study of glancing at an AI-built map of one person's ideas, and no evidence-based node limit. Applying Wardley maps to ideas is unevidenced.
- No study compares expansions grounded in a person's own items with generic ones. Anti-echo ordering is unproven.
- The HCI studies are small (n = 7–24) and short. GraphRAG and LazyGraphRAG figures are vendor-reported.
- Not verified: an iCloud per-file activity API (none found), Codex session format, Click to Do.
