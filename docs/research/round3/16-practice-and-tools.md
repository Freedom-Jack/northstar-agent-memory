# 16. How people structure personal thinking in practice, and what works

Round 3, track 16. Research note, rewritten 2026-10-14 (replaces the 2026-10-10 draft). It feeds the design and decides nothing. [`docs/GOAL.md`](../../GOAL.md) is authoritative; this note argues only about HOW.

**Scope.** Practices and tools: what people do, what they report, how it fails. Formats are tested in [15], processing jobs in [17], the value threshold in [18], memory injection in [19]. This note adds practice evidence and does not redo them.

**Method.** Web search and fetch, 2026-10-14. **Strong** = log study, controlled experiment or large audit; **medium** = small study or primary product docs; **weak** = practitioner writing, forums, reviews. No large, credible survey of PKM tool users was found, so most evidence is practice, not measured outcomes.

---

## Answer

Practices that last do three things. They **rewrite** material into the owner's own claims. They **file by concept or live question**, not by source. And they keep the **line of reasoning in a separate short layer**: a map of content with commentary, a decision record's context and consequences, a lab notebook's contents page. They fail in four ways: collecting instead of thinking, storing and never rereading, link graphs that become hairballs, and upkeep too heavy to sustain. The shared cause is that **whoever does the work does not get the benefit at that moment**. Two things work: **delivery at the moment of use** (lessons pushed into the decision, not a repository waiting to be searched), and a top layer that is **short, says where each item applies, and shows who said it**, because readers skim and almost never open sources. An AI maintainer removes the capture cost, so the bottleneck moves to **reading and trust**. AI summaries anchor judgement, can shift a person's views, and lose trust fast when wrong. For Northstar: a handful of answer-first briefs under the user's live questions, with scope and origin in plain words, no graph and no IDs, opening on the theme the user is returning to; and an AI side that injects little, only what is very strongly linked, with the reason each item was picked.

---

## 1. Evidence table

| # | Finding | Evidence | Strength | Src |
|---|---|---|---|---|
| E1 | Knowledge builds up when notes are filed by concept and joined to old notes as they are written. | Luhmann placed each day's rewritten notes among existing cards; links were sparse; poorly linked regions went dead [02]. Notes filed by book or project scatter one idea under many names. | medium + weak | [02], S1 |
| E2 | In commonplace books, selecting was the thinking, under the reader's own headings. | Readers copied chosen passages under their headings, added their own observations, and reread and rearranged them. | weak (secondary) | S2 |
| E3 | The order of thought lives in a separate layer, made when a pile gets confusing. | Maps of content are made at the "mental squeeze point", to develop ideas, not just store links. | weak | S3 |
| E4 | Decision records work when short, reasoned and superseded rather than deleted. | One or two pages, full sentences, "a conversation with a future developer". Context, decision, status, consequences. Old records stay, marked superseded. | medium | S4 |
| E5 | Even engineers record few decisions and skip the deliberation. | About half of repos using ADRs have only 1–5. In 921 repos, ~63% of 5,800 ADRs were opened as already "accepted". | strong (abstracts) | S5, S6 |
| E6 | Lab notebooks keep two tiers: a dated log and a contents page with summaries. | Date each entry and say why it matters; record failures; never erase, correct beside. | medium | S7 |
| E7 | Rationale capture fails on cost, unclear benefit and hard reuse; the proposed fix is selective capture. | Rarely captured; most rationale tools never evaluated. Systems fail when those who do the work are not those who benefit (Grudin). | medium | S8, S9 |
| E8 | Repositories that wait to be searched go unused. Lessons must be pushed into the decision and say where they apply. | NASA's lessons system was hard to sift and few managers contributed. Most lessons systems are passive and stand-alone; lessons often omit the process they apply to and the conditions for use. | medium | S10, S11 |
| E9 | Context-triggered suggestions get unused information used. Good ones hide weak matches and explain themselves. | Proactive agents led people to view and use information they would not have looked up. The Remembrance Agent showed "No suggestion" below a threshold and the keywords behind each pick. | medium | S12, S13 |
| E10 | Storing everything and rereading nothing ends in abandonment. | One writer deleted ~10,000 notes from seven years: rarely revisited, sorting always left for later. She kept one note of a few must-remember items. | weak (one case) | S14 |
| E11 | Hand-made links cost more than they return; users want the right snippet surfaced with context. | Far more time spent writing backlinks than following them; rereading felt like sifting junk. | weak | S15 |
| E12 | Global graphs are hairballs; only local views and orphan-finding get used. | In an Obsidian thread about half the posters had turned the graph off or saw no use; layouts shift each load. | weak | S16 |
| E13 | How people plan to retrieve shapes how they organise. | Obsidian case study of lab researchers. | medium (abstract) | S17 |
| E14 | Heavy-setup tools work for their builders and lose others. | Heptabase's founder made ~4,000 cards and 180 whiteboards by hand in two years. Tana reviewers report a steep learning curve. | weak | S18, S19 |
| E15 | Some keep resurfacing manual on purpose, because doing it builds understanding. | Obsidian's CEO: no folders, link first mentions, a "random revisit" by hand every few months. | weak | S20 |
| E16 | AI-native tools moved from AI filing to in-context resurfacing plus undo. | Mem 2.0, rebuilt: notes resurface while writing or meeting; version history rolls back AI edits. Notion 3.0: agent memory as pages plus an instructions page. Reflect: suggested backlinks you accept or dismiss. | medium (vendor) | S21–S23 |
| E17 | AI topic trees orient; they do not show reasoning and cannot be edited. | NotebookLM mind maps: expand a node or ask about it; regenerate, not edit. A tutorial calls them a keyword skeleton. | medium + weak | S24, S25 |
| E18 | Pro/con structure helps reasoning, but no more than an outline. | Argument mapping beat control but not hierarchical outlining (81 students). The one Kialo study is a self-report survey. | medium + weak | S26, S27 |
| E19 | Readers skim and almost never open sources. | ~20% of a page's words read (45,237 page views). 900 adults: 1% of visits with an AI summary clicked a link in it. | strong | S28, S29 |
| E20 | The first summary sets the anchor, and people underrate its pull. | Preregistered, N=278 (preprint). | medium | S30 |
| E21 | AI rewording can shift what people believe. | CHI 2023, N=1,506: an opinionated assistant shifted writing and later attitudes. | strong | S31 |
| E22 | Visible AI errors destroy trust; marking AI text helps checking. | Apple paused news summaries after false headlines and italicised the rest. Granola: user notes black, AI additions grey, with a quote trace. | medium | S32, S33 |
| E23 | Status and provenance work best on the surface. | Epistemic-status notes: how it was learned, how sure. | weak | S34 |
| E24 | Memory leaking across contexts annoys the users who care most. | Memory pulled unrelated details into a chat and spoiled an experiment; the user asked for project-scoped memory. | weak | S35 |
| E25 | "How to work with me" manuals are one page and practical, but self-described and unproven. | Kroghrud's one-page manual; critics call manager READMEs self-serving. No outcome study. | weak | S36, S37 |

**Gaps.** Nothing measures whether people read an AI-maintained view of their own knowledge.

---

## 2. Practices and tools at a glance

| Practice or tool | Where the logic lives | Works | Fails |
|---|---|---|---|
| Commonplace book | reader's own headings | choosing is thinking | becomes a hodgepodge |
| Zettelkasten, evergreen notes | concept notes, links | builds up over years | heavy upkeep; dead regions |
| Maps of content | the map's commentary | made when a pile confuses | bare link lists |
| PARA | folders by actionability | archive at project end | lessons stuck in old projects |
| Decision records, lab notebooks | context, consequences, contents page | short; superseded, not deleted | few written; the why skipped |
| Obsidian, Logseq, Roam | links, graph, daily notes | flexible local files | hairballs; links cost more than they return |
| Tana, Notion, Heptabase | schema or spatial layout | strong once built | setup and manual cost |
| Kialo | pro/con tree | tensions visible | no better than an outline |
| NotebookLM | AI topic tree, cited | orientation, grounding | topics, not reasoning |
| Mem, Reflect, Notion AI | AI search, resurfacing | no filing | trust needs undo and control |

---

## 3. Failure modes and what Northstar should do

| Failure | What avoided it in practice | Northstar implication |
|---|---|---|
| **Collector's fallacy**: having material feels like knowing it (S38) | own-words rewrite; selective capture (E7) | claims, not quotes; most AI text stays in the raw archive (GOAL §2); threshold per [18] |
| **Notes never reread** (E10, E11) | lessons pushed into the decision (E8, E9) | the AI is the main daily reader; the view opens on the theme in use and stands alone in two minutes |
| **Graph hairball** (E12) | sparse links; maps with commentary | no global graph; two or three "related" lines saying how items relate |
| **Upkeep burden** (E7, E14) | upkeep tied to use; supersede, don't rewrite | the AI maintains; re-map a theme when its brief stops reading well, not on a counter |
| **AI summaries ignored, or wrong and trusted** (E19–E22) | provenance on the surface; quote trace; undo | accurate top layer; origin in words or styling; one-step correction |
| **Verdicts without reasons or scope** (E5, E8) | context, consequences, conditions | every item carries why and where it applies |
| **Context leakage** (E24) | project scoping | project scope by default; inject only when very strongly linked |

---

## 4. What this means for Northstar

### 4.1 The bottleneck moves from writing to reading and trust

Most PKM failures are cost failures: the person pays at capture and is repaid later, if ever (E7, E10, E11). Northstar removes that cost. Two costs remain. **Reading**: will a busy person open the view and get something from it in two minutes? **Trust**: does it say what they actually hold? There is also a warning. Some practitioners keep processing manual because doing it is how they learn (E15), and one deleted vault came with a complaint about outsourced reflection (E10). Northstar must not need a ritual (GOAL §4.1). So the view records and connects thinking the user already did in conversation. It is a memory and a map, not a substitute for thinking. Its test: can the user follow and use their own logic when they come back to a topic?

### 4.2 Design lessons for the human view

These refine the default in [15], "question-led claim cards in a pyramid".

1. **Group by the user's live questions or themes, never by chat or source** (E1, E2), named in the user's terms.
2. **Open each theme with a two-to-four-sentence brief, answer first, in prose with "because", "but", "so"** (E3, E4). This is the dot-connecting layer the rejected knowledge map lacked. It must stand alone, since sources are rarely opened (E19).
3. **State where each claim applies and where not** (E8). Unscoped lessons were the ones nobody reused. Put cross-context conflicts beside the claim, with the context that resolves them (for example real builds versus interviews).
4. **Show origin and status in words or styling, never codes** (E22, E23): mine or adopted from an AI; settled, forming or replaced.
5. **Two tiers, like a lab notebook** (E6): briefs on top; a dated "how I got here" trail with the original wording one click away. Supersede, never erase (E4).
6. **No global graph, no internal IDs** (E12).
7. **Open on the theme in use** (E8, E9): when a chat returns to a theme, the view, or a link in the AI's reply, lands on that brief. An optional "what changed since you last looked" line can sit on top. Nothing must be read (GOAL §4.1).
8. **One-step correction with undo** (E16, E22). AI-written briefs can shift what a person believes about their own view (E20, E21), so "that's not what I think" must be one action.

### 4.3 Jobs and checks (reliability in [17])

Practice implies six jobs. **Distil** rough phrasing into one claim in the user's terms; the probe found 14 of 50 items too literal (E1, E2). **Scope** every claim (E8). **Place** it under a live question, never a source (E1). **Connect**: write the brief's because, but and so, each sentence linked to its claims (E3, E4). **Supersede**: mark settled, forming or replaced, never overwrite (E4, E6). **Re-map** a theme at its squeeze point, with the reason recorded (E3). Connect is the hardest job and the one most likely to move the user's view (E21), so it needs claim-level grounding.

### 4.4 What practice adds to the value threshold (see [18])

- **Selectivity is the remedy everywhere** (E2, E7, E10). This supports [18]'s gates and its *pending* state.
- **Adoption works like commonplace selection.** Almost half of the probe items the user holds were adopted AI ideas. Others' words became the reader's when chosen, filed under the reader's heading and commented on (E2). So for an adopted AI idea, record what the user did with it: agreed, built on, used, or limited it.
- **Project knowledge fits a project scope.** PARA archives at project end; users want project-scoped memory (E24); decision records serve their project (E4). As in [18]: the AI uses project knowledge inside the project, it stays out of the personal view, and an item is promoted when it holds without project names. GOAL leaves this open and the user leans "no", so it is a proposal for the user.
- **Passing preferences** are nearer to a how-to-work-with-me note than to knowledge (E25). If kept at all, they shape the AI's style, outside the knowledge view, as an option for the user.

### 4.5 The AI side (see [19])

- **Delivery at the moment of use is what makes stored lessons useful** (E8, E9). This supports injecting only relevant, very strongly linked knowledge.
- **Show nothing when nothing is strong, and log why each item was picked** (E9), so injection is checkable (GOAL §4.7).
- **A manual is for adapting, not reciting** (E25). In the probe, linked memory made replies echo the user's views and add less. Knowledge should shape the answer quietly and be named only when the answer extends, contradicts or revises it.

### 4.6 Risks and open questions

- Mostly practice, not outcomes. Treat §4.2 as a hypothesis for the human-side benchmark: can the user, in two minutes, say what they hold on a theme, why, and where it applies?
- Opening on the theme in use needs a link from each chat surface to the view; connector support is unverified.
- Whether project-only knowledge belongs in Northstar is the user's call.
- Briefs can misstate the user's view (E20, E21): ground every sentence, show origin, make correction one step.

---

## Sources

Checked 2026-10-14. "ss" = seen only through search-result summaries; "abs" = abstract only.

- S1 Matuschak, concept-oriented notes https://notes.andymatuschak.org/Evergreen_notes_should_be_concept-oriented (practitioner)
- S2 Fine Books Magazine on commonplace books, citing Darnton https://www.finebooksmagazine.com/blog/collecting-commonplace-books (secondary)
- S3 Milo, maps of content https://www.linkingyourthinking.com/ideaverse/youre-already-doing-it-sort-of (practitioner)
- S4 Nygard (2011) https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions (primary)
- S5 Buchgeher et al., IEEE Access (2023) https://research.jku.at/en/publications/using-architecture-decision-records-in-open-source-projects-an-ms/ (abs)
- S6 de Santana Junior et al., ICSA 2026 https://conf.researchr.org/details/icsa-2026/icsa-2026-papers/34/Architecture-Decision-Records-Adoption-Impact-and-Developer-Engagement-in-Open-Sou (abs)
- S7 Schnell, PLOS Comp Bio (2015) https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1004385 (primary)
- S8 Burge, AI EDAM 22(4) (2008) https://www.cambridge.org/core/journals/ai-edam/article/design-rationale-researching-under-uncertainty/CA05C6AE6DDD832D828B28590ACAE23D (abs; other barrier lists ss)
- S9 Grudin, "Why CSCW Applications Fail" (1988) https://www.cs.uml.edu/~holly/teaching/91550/spring2012/p85-grudin.pdf (ss)
- S10 GAO-02-195 (2002) https://www.gao.gov/products/GAO-02-195 (primary summary); contributor share via https://govexec.com/management/2002/02/nasa-managers-not-sharing-lessons-learned-report-says/11045 (secondary)
- S11 Weber, Aha et al., FLAIRS 2000 https://cdn.aaai.org/FLAIRS/2000/FLAIRS00-033.pdf (PDF unreadable; ss)
- S12 Rhodes, MIT thesis (2000) https://dspace.mit.edu/handle/1721.1/9022 (abs)
- S13 Rhodes & Maes, IBM Systems Journal (2000) https://www.bradleyrhodes.com/Papers/rhodes-jitir-agents-ibmsj-2000.pdf (primary, partly read)
- S14 Westenberg, "I Deleted My Second Brain" (2025) https://westenberg.beehiiv.com/p/i-deleted-my-second-brain (practitioner, one case)
- S15 Shipper, "The Fall of Roam" (2022) https://every.to/chain-of-thought/the-fall-of-roam (practitioner)
- S16 Obsidian forum, graph view thread https://forum.obsidian.md/t/whats-the-point-of-the-graph-view-how-are-you-using-it/71316 (forum)
- S17 Ferreira et al., arXiv 2509.20187 (2025) https://arxiv.org/abs/2509.20187 (abs, preprint)
- S18 Heptabase founder's workflow https://wiki.heptabase.com/how-Heptabases-founder-use-Heptabase-for-learning (vendor)
- S19 Tana reviews https://www.g2.com/products/tana-2025-09-29/reviews (weak; ss)
- S20 Ango, "How I use Obsidian" https://stephango.com/vault (practitioner)
- S21 Mem 2.0 (Oct 2025) https://get.mem.ai/blog/mem-2-dot-0 (vendor)
- S22 Notion 3.0 (Sept 2025) https://notion.com/releases/2025-09-18 (vendor; ss)
- S23 Reflect, AI backlinks https://reflect.app/blog/automatically-add-backlinks-using-ai (vendor; ss)
- S24 Google, NotebookLM mind maps https://support.google.com/notebooklm/answer/16212283 (primary)
- S25 NotebookLM mind-map tutorial https://www.digitaltrends.com/cool-tech/i-underestimated-this-notebooklm-feature-until-it-completely-changed-how-i-study/ (weak; ss)
- S26 Dwyer, Hogan & Stewart (2011) https://research.universityofgalway.ie/en/publications/the-promotion-of-critical-thinking-skills-through-argument-mappin-6/ (abs)
- S27 Mahoney (2022), Kialo https://fler.rikkyo.ac.jp/journal/jc0e3e00000000a9-att/JFLER(2022_Vol.3)_13_Mahoney.pdf (ss; self-report)
- S28 Nielsen (2008) https://www.nngroup.com/articles/how-little-do-users-read/ (primary)
- S29 Pew Research Center (July 2025) https://www.pewresearch.org/short-reads/2025/07/22/google-users-are-less-likely-to-click-on-links-when-an-ai-summary-appears-in-the-results/ (primary)
- S30 Wang et al., "First Impressions", arXiv 2609.14900 (2026) https://arxiv.org/abs/2609.14900 (abs, preprint)
- S31 Jakesch et al., CHI 2023 https://arxiv.org/abs/2302.00560 (abs)
- S32 Apple pauses news summaries (Jan 2025) https://abc7news.com/post/apple-is-pulling-ai-generated-notifications-news-generating-fake-headlines/15810860/ (news; ss)
- S33 Granola https://www.granola.ai/blog/announcement ; https://docs.granola.ai/help-center/taking-notes/ai-enhanced-notes (vendor)
- S34 Appleton, "Epistemic disclosure" https://maggieappleton.com/epistemic-disclosure (practitioner)
- S35 Willison on ChatGPT memory (May 2025) https://simonwillison.net/2025/May/21/chatgpt-new-memory/ (practitioner)
- S36 Quartz on Kroghrud (2017) https://qz.com/1046131/writing-a-user-manual-at-work-makes-teams-less-anxious-and-more-productive/ (weak; ss)
- S37 "Burn your manager README" https://hackernoon.com/burn-your-manager-readme-a8bfab7b9d8f (weak; ss)
- S38 Tietze, "The Collector's Fallacy" (2014) https://zettelkasten.de/posts/collectors-fallacy (practitioner)
- Internal, not re-checked: [02] `../02-pkm-practice-and-failure.md` (Luhmann via Schmidt 2018, https://sociologica.unibo.it/article/download/8350/8272); [15], [17], [18], [19] in this folder.
