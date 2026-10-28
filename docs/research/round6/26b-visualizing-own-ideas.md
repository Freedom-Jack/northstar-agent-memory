# Round 6 research (26b): how to show a person their own ideas

**Date:** 2026-10-27. **Read with:** [`GOAL.md`](../../GOAL.md) §1 and §2 (the human-view rows of 2026-10-15, 2026-10-24 and 2026-10-27); notes [25](25-overview-display.md), [20](../round4/20-index-expansion-capture.md) §1 and [23](../round5/23-memory-architecture-and-dreaming.md) §4; [`DESIGN.md`](../../design/revision-2026-10-23/DESIGN.md) §6; the Result section of [`overview-sketch-round.md`](../../design/revision-2026-10-23/overview-sketch-round.md). Builds on them without repeating them.
**Question:** which form best lets a person see and re-understand their own body of ideas? It must serve three needs: (1) see the big picture of what I think and know; (2) get back into a piece of work; (3) answer a question about my own past. On 2026-10-27 the user tried a topic outline (sketch A) and a stable topic map (sketch B), chose neither, leaned towards B, and asked for published evidence on the best form.
**Slice:** one of four parallel notes. This one covers knowledge visualization and learning science. Re-finding and resumption, practitioner writing, and products are covered by the other three.
**Method:** desk research on 2026-10-27. **[E]** = a source shows it: a full text, a table or an abstract read today, or the earlier note named. **[L]** = my inference. **Unverified** = seen only in a search summary or a secondary source. Effect sizes are given as the source states them. Most of this evidence is about **students learning set material**, or people using interfaces in short lab tasks; each section says so. Findings constrain the HOW only (GOAL §5). No personal data was read.

**Short answer.**
- Still no study tests a person glancing at an AI-made overview of their own ideas. The nearest evidence is about students studying given material, interface experiments, and new studies of AI summaries [E].
- The shape matters less than expected, and least for experts. Studying a map beat studying an outline or list by g = 0.28; for high-ability learners the map effect was g = 0.13, not significant. A person is the expert on their own ideas [E; the transfer is L].
- What matters is what each form makes cheap. An outline makes topics and main ideas cheap. A matrix makes comparisons cheap. A node-link map makes links and paths cheap, but crossings and size soon cost more than they give [E].
- The largest effects come from how a view is used, not its shape. Trying to recall before looking beats re-reading, and beats studying a concept map. AI-written summaries carry two risks. Learning from an AI synthesis left knowledge shallower than searching oneself, and a summary with one wrong detail changed what people remembered [E]. Neither study tested a paraphrase of a person's own ideas [L].
- So the evidence favours layers over one picture: a two-level outline of claims in the person's words for the big picture; conflicts as side-by-side pairs or an ideas-by-contexts table; a small, stable map around one idea for links; work cues inside; an optional "recall first" step when preparing [L].
- Assessed: the outline (A) is best supported for the glance and for text surfaces; the full map (B) only for following links. The better form is a layered "issue outline". Its parts have evidence; the whole is untested [L].

---

## 1. What the evidence covers

The evidence comes from students studying other people's material, from lab tasks with graphs and layouts, and from new studies of AI summaries [E]. None studies one person revisiting their own ideas months later. Three facts bridge the gap [L]:
- **The reader is an expert** on their own ideas, so findings for high-knowledge readers apply best.
- **The structure is given:** Northstar's AI groups, labels and links the ideas, so findings on studying a given map apply, not those on building one.
- **The content is self-generated:** the overview cues the person's past thinking; it is not new material.

## 2. Maps against outlines and text

### 2.1 Concept and knowledge maps: the meta-analyses

All rows are students learning set material, from grade 4 to university, mostly on immediate or short-delay tests.

| Comparison | Effect | Source |
|---|---|---|
| All uses of maps | g = 0.60 (67 effect sizes, 55 studies, 5,818 people) | Nesbit & Adesope 2006, Table 2 [E] |
| Building a map / studying a given map, each against its own comparison | g = 0.82 (k = 27) / g = 0.37 (k = 40) | same [E] |
| Studying a map against studying text | g = 0.39 (k = 29, N = 2,027) | same, Table 6 [E] |
| Studying a map against studying an outline or list | g = 0.28 (k = 10, N = 561) | same, Table 6 [E] |
| Building a map against writing text or an outline | g = 0.19 (k = 7, N = 686) | same, Table 6 [E] |
| Maps, recall of central ideas / of details | g = 0.60 / g = 0.20 (k = 6 each) | same [E] |
| Studying maps: learners low / high in ability or prior knowledge | g = 0.40 (k = 5, significant) / g = 0.13 (k = 5, not significant); high domain knowledge alone g = 0.03 (k = 3) | same, Table 7 [E] |
| Hyperlinked maps against hyperlinked outlines in hypertext | No significant advantage | same, text [E] |
| Update: 142 effect sizes, n = 11,814 | g = 0.58; building 0.72, studying 0.43; high heterogeneity | Schroeder et al. 2018 [E, abstract] |

A correction to note 20, row 1.1: the figures 0.58, 0.72 and 0.43 are Schroeder et al.'s. Nesbit & Adesope's own are in the table above.

**Lessons.**
- [E] A given map helps students a little more than an outline or list. The gain is mainly for central ideas and for learners low in ability or prior knowledge. For high-ability learners it is small and not significant.
- [E] Building beats studying. But building a map beats building an outline by only g = 0.19, so most of the "build" benefit comes from the activity, not from the map.
- [L] For a person revisiting their own ideas, map against outline should change understanding very little. The map's edge on central ideas fits the "big picture" need, but it is small.

### 2.2 Graphic organizers, matrices and outlines

- [E] College students who had enough time to study graphic organizers of a long text learned more hierarchical and comparative relations than those given an outline or the text alone. They applied the knowledge better and wrote more integrated essays (Robinson & Kiewra 1995, two experiments).
- [E] A matrix let readers work out relations between concepts more quickly than an outline or text. The advantage disappeared on a delayed test, and the authors suggest the ease itself may be why (Robinson & Schraw 1994; abstract summary only).
- [E] 72 students studied a 2,000-word text as plain text, as extracted key ideas, as an outline, or as a matrix. The matrix was best for facts and for relationships, because it puts related facts together by topic and by category. Typographic signals of the structure did not help on their own, nor did extracting ideas. In a second experiment (54 students), the matrix helped only when its rows followed a natural order (Kauffman & Kiewra 2010).
- [E] The theory behind these results is "computational efficiency": a display helps when it puts together what the reader must use together, so nothing has to be searched for (Larkin & Simon 1987, as applied by Kauffman & Kiewra).
- [E] In an ontology-mapping task, an indented tree was "more organized and familiar" to novices. A graph was more controllable and intuitive, with no repeated items, especially when an item had several parents (Fu, Noy & Storey 2013).

**Lessons.**
- [L] Each form answers a different question fastest:
  - outline: what are my topics, and my main ideas in each?
  - matrix: how does my view differ from one context to another?
  - graph: what is connected to what, and by which path?
- [L] The user's main conflict is across contexts: "real builds" against "interviews" (GOAL §1, 2026-10-10). That is a two-way comparison, the case where a matrix does best.
- [L] An idea that belongs to two topics must appear twice in an outline, while a graph shows it once. This is the outline's weakest point.
- [L] Robinson & Schraw's delayed result warns a glance view: what is easy to read is not always what lasts.

### 2.3 Overviews in hypertext, and prior knowledge

- [E] Readers of an electronic text with a structured overview (a hierarchical map) or an unstructured one (a menu-like list) remembered more topics and recalled more broadly than readers of plain text. Without a specific goal, the list led to more fragmented knowledge. The hierarchical overview was easier to recall and use, and led to more review (Dee-Lucas & Larkin 1995).
- [E] A hierarchical map helped low-knowledge readers' global comprehension. For high-knowledge readers the form made no difference (Potelle & Rouet 2003; note 25).
- [E] Low-knowledge learners gained more conceptual knowledge, and felt less lost, with a hierarchical concept map than with a network map. High-knowledge learners were not more disoriented by the network. Both groups spent less mental effort with the hierarchy (Amadieu et al. 2009; abstract via search, sample size unverified).
- [E] Reading a graphical overview first went with better comprehension of difficult hypertexts (Salmerón et al. 2009, two eye-tracking studies; summary only).
- [E] Headings, overviews and summaries changed what college students recalled only when the text's topic structure was complex. When half the topics had headings, topics without headings were recalled worse than in a text with no headings at all: signals steer attention (Lorch & Lorch 1996).
- [E] Advance organizers, an overview given before the material, helped learning and retention across 135 studies (Luiten, Ames & Ackerson 1980; the size is not in the abstract).
- [E] Aids that help novices can lose their value, or hurt, for experienced learners: the expertise reversal effect (Kalyuga et al. 2003, a review).

**Lessons.**
- [E] A hierarchical overview shown first is well supported for orientation and for memory of topics, at lower effort.
- [L] For an expert on their own ideas, the overview's job is to orient and to cue, not to teach. Expect small gains from any shape, and real costs from clutter.
- [L] What the overview leaves out gets less attention (Lorch & Lorch). A "3 more" count under each topic keeps the rest in view.

### 2.4 Mind maps

- [E] 50 medical students studied a 600-word text with a mind map or with their usual method. A week later the mind-map group recalled 10% more facts (95% CI −1% to 22%), and liked the method less (Farrand, Hussain & Hennessy 2002).
- [E] The mind-map meta-analyses found are small and in minor journals; for example, 11 studies of e-learning mind maps on critical thinking, mean effect 0.81 (Edumaspul 2023). Their quality is unverified.
- [L] A mind map is a radial tree, and its evidence is about making one while studying.

### 2.5 Argument and issue maps

- [E] In three experiments, reading or building an argument map improved immediate recall of arguments, compared with hierarchical outlining, summarising and reading text. The abstract reports no comprehension effect (Dwyer, Hogan & Stewart 2013).
- [E, secondary] Critical-thinking courses with heavy argument-mapping practice gained about 0.8 standard deviations, over twice the gain of standard courses (van Gelder's figure, as reported by Davies, Barnett & van Gelder; the meta-analysis behind it, Alvarez Ortiz 2007, was not read). One such course gained about 0.72 SD from pre-test to post-test, with no control group (Twardy 2004). Both are about learning to reason by building maps.
- [E] IBIS (issue, position, argument) was used in an industrial field trial to record more than 2,300 requirements and design decisions. The form used in that trial was a "simple indented text notation", not the graphical tool gIBIS (Conklin & Burgess-Yakemovic 1991).
- [E] Design-rationale documents were useful to some designers as support for their reasoning, but not sufficient (Karsenty 1996; summary only). The cost of capture is the main barrier (Buckingham Shum & Hammond 1994; note 20, row 1.4).
- [E] In two controlled experiments with 75 master's students, the value of a rationale item depended on its kind and on the task it served. Recording only the items needed at least half the time halved the documentation (Falessi et al. 2013).
- [E] Formal structure imposed before people need it is a common failure (Shipman & Marshall 1999).

**Lessons.**
- [L] The user's own conflicts have the shape of an issue with positions. The question "how should I build an agent?" has the answer "workflows first" in real builds and a different one in interviews. IBIS records exactly that.
- [L] In that field trial, IBIS was kept as an indented outline. An issue structure does not need a graph to be useful.
- [L] Show what the occasion needs (Falessi): for an interview, the position and its reason; for a decision check, the context and the trade-off.

## 3. Given against self-made, and made by an AI

### 3.1 The generation effect and its limits

- [E] People remember words they generated better than words they read, on recognition and on recall (Slamecka & Graf 1978). Across 86 studies the benefit is about 0.40 SD (Bertsch et al. 2007). A meta-analysis of 310 experiments found that generating helps memory for both the item and its context, more so when the person is less constrained (McCurdy et al. 2020).
- [E] A given organizer can beat a self-made one. In three experiments, learners who read a passage with organizers provided by the author did better on transfer than those who built their own: d = 0.24 (not significant), 0.43 and 0.84. Retention did not differ. The authors' reading: building added load that crowded out deeper processing (Stull & Mayer 2007).
- [E] Across 33 studies, taking and reviewing notes helped learning substantially. Giving students a framework or the instructor's notes improved this more than training them, and helped lower-level students most (Kobayashi 2006).

**Lessons.** [L] The person already did the generating, in their chats and work. The overview serves the review step, where a well-made given structure is fine. What it must not do is replace the person's own words, which carry the memory (note 23, H.1 and H.4).

### 3.2 When an AI makes or words the structure

- [E] In seven experiments (n = 10,462), people who learned a topic from LLM summaries rather than web links developed shallower knowledge. They felt less invested and wrote sparser, less original advice, even when the summaries carried links (Melumad & Yun 2025).
- [E] 91 university students who researched a science issue with ChatGPT rather than Google reported lower cognitive load, but reasoned less well in their recommendations (Stadler, Bannert & Sailer 2024).
- [E] In a high-school maths field experiment, an AI tutor raised practice scores, but students who leaned on an unguarded GPT-4 did worse once it was taken away. A tutor that gave teacher-designed hints instead of answers mitigated this (Bastani et al. 2025, significance statement).
- [E] In three experiments (N = 172 each), offloading to a device improved the task but weakened memory of what was offloaded, unless people expected a memory test (Grinschgl, Papenmeier & Meyerhoff 2021). Saving items to a device also helped people learn what came next (Storm & Stone 2015; Runge, Frings & Tempel 2019).
- [E] Most LLM summaries of a short video omitted its central event. Among 328 people who had watched the video, those who then read a misleading AI summary recalled the event less accurately than those who read an accurate one: 44.8% against 83.6% recalled the right sign (Sim, Eiger & Kohno, AIES 2026; figures as reported in press coverage of the paper, checked 2026-10-27).
- [E] A week after producing ideas with and without an LLM, 184 people misattributed origin more after AI use, worst in mixed workflows (Zindulka et al., CHI 2026; note 23).
- [E] People who repeatedly improved other people's ideas later recalled those ideas as their own, at "dramatically high levels" (Stark & Perfect 2008).
- [E] Users did not feel they owned AI-written text, but did not declare AI authorship either. More influence over the text raised their sense of ownership (Draxler et al. 2024; n = 30 and 96).
- [E] Higher confidence in AI went with less critical thinking, in a survey of 319 knowledge workers (Lee et al., CHI 2025; self-report).
- [E] ChatGPT-made concept maps were rated about as good as teachers' (Schicchi et al. 2025, 83 secondary students; search summary only, learning results unverified). Students reading an AI-made concept map reported less mental demand at equal accuracy (Han & Choi 2025; note 25).

**Lessons.**
- [L] An AI may make the structure: the groups, the order, the links. The evidence on given organizers says this is fine.
- [L] An AI should not word the content. AI syntheses left knowledge shallower, and a wrong detail in an AI summary rewrote memory. A rewording of a person's own ideas risks the same, though no study has tested that case. Each line should be the person's own claim, quoted or lightly trimmed, with their work beside it.
- [L] Origin cannot be rebuilt from memory, and adopted ideas drift towards "mine" the more they are worked on. Origin must be stored, and shown quietly (note 25, 2.5).
- [L] So a "not what I think" flag is more than a quality score: a wrong line can rewrite the memory it was meant to cue. The DESIGN §8 bar of 1 flag in 10 lines may be too loose for lines shown without their source.

## 4. Overviews, graphs and layouts

### 4.1 "Overview first"

- [E] Shneiderman's "overview first, zoom and filter, then details on demand" (1996) is a design guideline. A review of the papers that cite it found it lacks empirical validation (Craft & Cairns 2005).
- [E] The survey by Cockburn, Karlson & Bederson concludes that none of overview+detail, zooming and focus+context is ideal:
  - a separate overview costs attention when switching between it and the detail;
  - zooming costs re-orientation after each jump;
  - distortion ("fisheye") rarely improved performance outside spatial data, and can harm pointing at targets.
- [E] Still, the same survey finds overview+detail and zooming often repay their costs. In one study it reports, a fisheye text view was read faster, but an overview+detail view was understood better.
- [E] People prefer having an overview more than it speeds them up (Hornbæk, Bederson & Plaisant 2002; note 25).

**Lessons.** [L] "Overview first" is well supported for orientation and preference, weakly for speed. Use overview plus detail, not distortion: a stable outline or map beside the idea that is open.

### 4.2 Node-link against matrix, and clutter

- [E] Above about 20 nodes, adjacency matrices beat node-link diagrams on most of seven basic tasks. Only path finding favoured node-link throughout (Ghoniem, Fekete & Castagliola 2005).
- [E] With 557 online participants and a 258-node network, node-link diagrams beat matrices on questions about topology and connectivity. Group tasks were mostly equal, and matrices won at counting clusters (Okoe, Jianu & Kobourov 2017; the paper is inconsistent about memorability).
- [E] Edge crossings were "by far the most important" layout factor for understanding a graph. Bends and symmetry mattered less (Purchase 1997).

**Lessons.** [L] A person's overview is a sparse graph: tens of ideas and fewer real links. Node-link works well for the few links around one idea. A whole-map view gains crossings fast, and suits path questions the person rarely asks. For a dense two-way structure, such as ideas against contexts, a table is the readable form.

### 4.3 Spatial memory and stable layouts

- [E] People who placed their own web pages on a sloping 3D plane (Data Mountain) showed statistically reliable advantages over a favourites list (Robertson et al. 1998; see note 20, row 1.7).
- [E] But location alone is a weak cue. Finding objects by location alone was at first as accurate as by name, but fell off much faster as objects were added. Office-like landmarks did not help (Jones & Dumais 1986, three experiments).
- [E] Keeping items in place mattered more than keeping the view's size: a spatially stable view, scaled to fit, "dramatically" outperformed one that reflowed (Scarr et al. 2013).

**Lessons.** [L] Spatial memory forms through repeated use and, in Data Mountain, through placing items oneself. An AI-placed map opened a few times a year will build little of it. So names, not positions, must carry recall. Stability still matters, so that the little that forms is not destroyed; an outline that reorders itself on every visit has the same cost.

### 4.4 Spatial hypertext, and space to think

- Unverified (only the opening was read): spatial hypertext was designed so that people can express structure that is still changing, by where they put things (Marshall & Shipman 1995).
- [E] Analysts with large displays used the space as external memory and as a layer of meaning (Andrews, Endert & North 2010).
- [E] Visualizations of personal data supported reminiscing when they evoked familiarity and allowed for subjective views (Thudt et al. 2016, a technology probe).

**Lessons.** [L] These support space that the person arranges. They argue for letting the person pin or move items in the overview, not for an AI-drawn canvas. For one's own past, the aim is recognition, not surprise.

## 5. Revisiting as active recall

- [E] Students who re-read a prose passage did better at 5 minutes. Those who tried to recall it did better after 2 days and after a week, although re-reading made people more confident (Roediger & Karpicke 2006).
- [E] Across 272 effect sizes, practice tests beat restudying and every other comparison (Adesope, Trevisan & Sundararajan 2017). The overall effect is reported as g = 0.61 (a secondary summary). Across the main meta-analyses, including Rowland's of 2014, the testing effect is put at about 0.50 to 0.61 (a secondary summary). Rowland found that recall tests help more than recognition tests (abstract).
- [E] Retrieval practice beat building a concept map with the text in view, on inference questions and even on a concept-map test (Karpicke & Blunt 2011). Building a concept map from memory worked as well as writing what one recalls, and both beat restudying (Blunt & Karpicke 2014). Adding concept mapping to retrieval practice added nothing (O'Day & Karpicke 2021).
- [E] Seeing some studied items as cues lowers recall of the rest. The effect is robust and medium-sized across 109 samples (N = 5,605), and weaker after long delays (Pepe et al. 2023).
- [E] Comparing cases side by side beat studying them one at a time: d = 0.50 across 57 experiments. It worked best when learners looked for similarities and were given the principle afterwards (Alfieri, Nokes-Malach & Schunn 2013).
- [E] When two sources disagreed, readers looked more at the sources and remembered them better (Braasch et al. 2012).
- [E] Stories were understood and recalled better than expository texts, across more than 75 samples and 33,000 participants (Mar et al. 2021).

**Lessons.**
- [L] A glance is re-reading. It works for the next few minutes, which suits a quick look before an interview. It builds little that lasts, and it inflates confidence.
- [L] Trying to recall first is the strongest known way to make revisiting stick. For "preparing for something", an optional step could show a topic or an issue and hide the person's position until they try. It must stay optional, with no schedule and no score: the user rejected study routines ("not a learning lessons for me", GOAL §1), and asked during the test whether it was a quiz.
- [L] Part-list cuing points the same way. Showing a topic's top 2–3 ideas may hide the others from recall. Recall first, then reveal everything, with a count of what is not shown.
- [L] A conflict helps memory when shown as a pair with each side's context: comparison (Alfieri) and source memory (Braasch) both improve.
- [L] A one-line "how I got here" (the context, what was decided, what happened) may be recalled better than a bare claim (Mar et al.). This is untested for one's own ideas.

## 6. Gaps and unverified items

- No study tests glancing at an AI-made overview of one's own ideas, or showing conflicts between one person's ideas. Note 20's gap stands.
- Almost all the learning evidence is about students and set material. Most HCI evidence comes from short lab tasks.
- Unverified or summary-only: Adesope's and Rowland's effect sizes; the 0.8 SD argument-mapping figure and Alvarez Ortiz's meta-analysis; Robinson & Schraw beyond the abstract summary; Karsenty's results; Amadieu's sample; Salmerón's results; Schicchi's learning results; the mind-map meta-analyses' quality.
- Not checked: O'Donnell, Dansereau & Hall's review of knowledge maps; Hornbæk & Hertzum's review of what "overview" means.

---

## Implications for the overview

**Strength of evidence**, as used below:
- **Strong:** meta-analyses or many experiments, with a mechanism likely to carry over.
- **Moderate:** several experiments, but on other people or other material.
- **Weak:** one or two small studies, or analogy.
- **None:** inference only.

Every rating is for the form serving the need. All evidence is indirect, because no study covers one person's own ideas.

### Need 1: see the big picture of what I think and know

1. **A two-level topic outline of claims.** Topics in the person's words. Under each, 2–4 one-line claims in their words, a count of the rest, and conflicts marked in place. **Moderate.** Hierarchical overviews help orientation and memory of topics, at lower effort (Dee-Lucas & Larkin; Amadieu; Potelle & Rouet). Headings steer attention (Lorch & Lorch). For experts, the shape adds little (Nesbit & Adesope, Table 7; Kalyuga).
2. **A stable topic map with regions and lines (sketch B).** About equal to the outline for the glance; better when the links across topics are the point. **Weak to moderate.** Maps beat outlines by g = 0.28 for students, and by about nothing for high-ability learners. Crossings and the limits of spatial memory weigh against a whole map (Purchase; Jones & Dumais).
3. **A table of ideas against contexts,** for the ideas held in more than one context. **Moderate** for comparisons (Robinson & Kiewra; Kauffman & Kiewra), but it covers only part of the overview.

### Need 2: get back into a piece of work

1. **One idea opened in place, with its work cues and a small map of its neighbours:** the ideas it connects to, the ones it conflicts with, and where it was adopted from. Under about 20 nodes, with positions kept between visits. **Moderate** for the parts: one's own work as the cue (note 23, H.1 and H.8); node-link for links and paths at small size (Ghoniem; Okoe); stable positions (Scarr). Untested as a whole.
2. **An optional "recall first" step** ("what did you decide about this, and why?") before the idea opens. **Strong** for students learning set material (Roediger & Karpicke; Adesope; Karpicke & Blunt). **None** for getting back into one's own work.
3. **The outline as the way in.** **Weak.** People navigate to their own things (note 25, 2.4), and names beat places as cues (Jones & Dumais).

### Need 3: answer a question about my own past

1. **An answer in the chat that quotes the person's own words and work, with origin and date, and opens the overview at that idea.** **Moderate** for the risks this avoids: AI summaries changing memory (Sim et al.), shallow knowledge from AI syntheses (Melumad & Yun), blurred origin (Zindulka; Stark & Perfect). The form itself is untested.
2. **The table of ideas against contexts,** for "what did I think about X when doing Y?". **Moderate**, from the matrix studies; indirect.
3. **The map.** **Weak.** It helps only with "how are these connected?".

### The three forms assessed

- **Topic outline (sketch A).** The best-supported default for the glance. Hierarchy first, cheap to read, works as plain text in Claude Code, and fits an inline card (note 25, §3). It is weak at links across topics, where items repeat, and it does not feel like a "map". Its risk of reading "like an answer" (GOAL §2, 2026-10-14) comes from content more than shape; claims in the person's words, with work cues, are the remedy [L].
- **Topic map or graph (sketch B).** Supported for following links and paths, at small size. No evidence shows it improves an expert's understanding over an outline. A whole map costs crossings and needs fullscreen. It also builds little spatial memory when the AI places the items and the person opens it rarely. The evidence fits B best as a local view around one idea, or as a regions view that draws lines only for the idea in focus [L].
- **The form the evidence points to: a layered "issue outline".**
  - Layer 1, the big picture: topics, each with 2–4 claims in the person's words and a count of the rest.
  - Layer 2, inside a topic: the issues the person worked on, as questions; under each, their position in each context, side by side when the positions differ; one line on why; and one to three work cues.
  - On demand: a small, stable map around the open idea for links, and a table of ideas against contexts for checking a decision.
  - Optional: "recall first" before revealing, off by default.

  It keeps what the user asked for: the big picture first, grouping by topic, and connect and conflict lines (GOAL §2, 2026-10-15). It draws the lines where they are readable. Each part has [E] support; the whole is [L] and must be tested.
- **Nothing here changes the WHAT.** The topics, lines and big picture stay. The evidence only says where each form carries them best.

### On the open question: revisit only, or also expand

- [E] Ready-made AI syntheses left knowledge shallower (Melumad & Yun), and hints protected learning where answers did not (Bastani et al.).
- [L] If the overview hands an idea to the chat ("ask about this for my problem"), the evidence favours a reply that starts from the person's own position and leaves them a move, over a finished synthesis. This bears on the shape of an expansion. It does not settle whether the overview should offer one; that stays open with the user (GOAL §2, 2026-10-27).

### What to test next, within DESIGN §8

- Build the issue outline, the local map and the table from the same items as sketches A and B, so only the form changes (note 25, §5). Record the time to the first useful cue, which cue triggered recall (the line, the work, a link or the table), and "not what I think" flags.
- Offer "recall first" as a setting, off by default, and count whether it is used.

---

## Sources

**Maps, organizers and outlines**
- Nesbit & Adesope, "Learning with concept and knowledge maps: a meta-analysis", *Review of Educational Research* 76(3), 2006 (full text, Tables 2, 6 and 7). https://www.sfu.ca/~jcnesbit/articles/NesbitAdesope2006.pdf
- Schroeder, Nesbit, Anguiano & Adesope, "Studying and constructing concept maps: a meta-analysis", *Educational Psychology Review* 30(2), 2018 (abstract). https://doi.org/10.1007/s10648-017-9403-9 ; https://summit.sfu.ca/item/17789
- Robinson & Kiewra, "Visual argument: graphic organizers are superior to outlines in improving learning from text", *Journal of Educational Psychology* 87(3), 1995 (abstract). https://doi.org/10.1037/0022-0663.87.3.455
- Robinson & Schraw, "Computational efficiency through visual argument: do graphic organizers communicate relations in text too effectively?", *Contemporary Educational Psychology* 19, 1994 (abstract summary). https://doi.org/10.1006/ceps.1994.1029
- Kauffman & Kiewra, "What makes a matrix so effective? An empirical test of the relative benefits of signaling, extraction, and localization", *Instructional Science* 38, 2010 (abstract and introduction). https://doi.org/10.1007/s11251-009-9095-8 ; https://kiewra.unl.edu/sites/unl.edu.cehs.kiewra/files/media/file/What%20Makes%20a%20Matrix%20So%20Effective.pdf
- Larkin & Simon, "Why a diagram is (sometimes) worth ten thousand words", *Cognitive Science* 11, 1987 (as applied by Kauffman & Kiewra). https://doi.org/10.1016/S0364-0213(87)80026-5
- Fu, Noy & Storey, "Indented tree or graph? A usability study of ontology visualization techniques in the context of class mapping evaluation", ISWC 2013 (abstract). https://doi.org/10.1007/978-3-642-41335-3_8
- Dee-Lucas & Larkin, "Learning from electronic texts: effects of interactive overviews for information access", *Cognition and Instruction* 13(3), 1995 (abstract). https://doi.org/10.1207/s1532690xci1303_4
- Potelle & Rouet, "Effects of content representation and readers' prior knowledge on the comprehension of hypertext", *IJHCS* 58(3), 2003 (note 25). https://doi.org/10.1016/S1071-5819(03)00016-8
- Amadieu, van Gog, Paas, Tricot & Mariné, "Effects of prior knowledge and concept-map structure on disorientation, cognitive load, and learning", *Learning and Instruction* 19(5), 2009 (abstract via search). https://doi.org/10.1016/j.learninstruc.2009.02.005 ; https://research.ou.nl/ws/files/1022307/Amadieu-etal_LI_2009.pdf
- Salmerón, Baccino, Cañas, Madrid & Fajardo, "Do graphical overviews facilitate or hinder comprehension in hypertext?", *Computers & Education* 53(4), 2009 (summary). https://doi.org/10.1016/j.compedu.2009.06.013
- Lorch & Lorch, "Effects of organizational signals on free recall of expository text", *Journal of Educational Psychology* 88(1), 1996 (abstract). https://doi.org/10.1037/0022-0663.88.1.38
- Luiten, Ames & Ackerson, "A meta-analysis of the effects of advance organizers on learning and retention", *American Educational Research Journal* 17(2), 1980 (abstract). https://doi.org/10.3102/00028312017002211
- Kalyuga, Ayres, Chandler & Sweller, "The expertise reversal effect", *Educational Psychologist* 38(1), 2003 (abstract). https://doi.org/10.1207/S15326985EP3801_4
- Farrand, Hussain & Hennessy, "The efficacy of the 'mind map' study technique", *Medical Education* 36(5), 2002 (abstract). https://doi.org/10.1046/j.1365-2923.2002.01205.x
- "Meta-analysis: the effect of e-learning-based mind mapping on students' critical thinking skills", *Edumaspul* 7(2), 2023 (abstract). https://doi.org/10.33487/edumaspul.v7i2.6473

**Argument maps, issue maps and design rationale**
- Dwyer, Hogan & Stewart, "An examination of the effects of argument mapping on students' memory and comprehension performance", *Thinking Skills and Creativity* 8, 2013 (abstract). https://doi.org/10.1016/j.tsc.2012.12.002
- Davies, Barnett & van Gelder, "Using computer-aided argument mapping to teach reasoning" (book chapter; van Gelder's 0.8 SD figure via search summary). https://ecampusontario.pressbooks.pub/criticalthinking1234/chapter/introduction/
- Twardy, "Argument maps improve critical thinking", *Teaching Philosophy* 27(2), 2004 (preprint, via search summary). https://doi.org/10.5840/teachphil200427213 ; https://web-archive.southampton.ac.uk/cogprints.org/3008/
- Conklin & Burgess-Yakemovic, "A process-oriented approach to design rationale", *Human-Computer Interaction* 6(3–4), 1991 (abstract). https://doi.org/10.1207/s15327051hci0603&4_6
- Karsenty, "An empirical evaluation of design rationale documents", CHI 1996 (summary only). https://doi.org/10.1145/238386.238462
- Buckingham Shum & Hammond, "Argumentation-based design rationale: what use at what cost?", *IJHCS* 40(4), 1994 (summary; note 20). https://doi.org/10.1006/ijhc.1994.1029
- Falessi, Briand, Cantone, Capilla & Kruchten, "The value of design rationale information", *ACM TOSEM* 22(3), 2013 (abstract). https://doi.org/10.1145/2491509.2491515
- Shipman & Marshall, "Formality considered harmful", *CSCW* 8(4), 1999 (summary; note 20). https://doi.org/10.1023/A:1008716330212

**Given, self-made and AI-made**
- Slamecka & Graf, "The generation effect: delineation of a phenomenon", *JEP: Human Learning and Memory* 4(6), 1978 (abstract). https://doi.org/10.1037/0278-7393.4.6.592
- Bertsch, Pesta, Wiscott & McDaniel, "The generation effect: a meta-analytic review", *Memory & Cognition* 35(2), 2007 (summary; note 23). https://doi.org/10.3758/BF03193441
- McCurdy, Viechtbauer, Sklenar, Frankenstein & Leshikar, "Theories of the generation effect and the impact of generation constraint: a meta-analytic review", *Psychonomic Bulletin & Review* 27, 2020 (abstract). https://doi.org/10.3758/s13423-020-01762-3
- Stull & Mayer, "Learning by doing versus learning by viewing: three experimental comparisons of learner-generated versus author-provided graphic organizers", *Journal of Educational Psychology* 99(4), 2007 (abstract). https://doi.org/10.1037/0022-0663.99.4.808
- Kobayashi, "Combined effects of note-taking/-reviewing on learning and the enhancement through interventions: a meta-analytic review", *Educational Psychology* 26(3), 2006 (abstract). https://doi.org/10.1080/01443410500342070
- Melumad & Yun, "Experimental evidence of the effects of large language models versus web search on depth of learning", *PNAS Nexus*, 2025 (abstract). https://doi.org/10.1093/pnasnexus/pgaf316
- Stadler, Bannert & Sailer, "Cognitive ease at a cost: LLMs reduce mental effort but compromise depth in student scientific inquiry", *Computers in Human Behavior* 160, 2024 (abstract). https://doi.org/10.1016/j.chb.2024.108386
- Bastani et al., "Generative AI without guardrails can harm learning: evidence from high school mathematics", *PNAS*, 2025 (significance statement). https://doi.org/10.1073/pnas.2422633122
- Grinschgl, Papenmeier & Meyerhoff, "Consequences of cognitive offloading: boosting performance but diminishing memory", *Quarterly Journal of Experimental Psychology* 74(9), 2021 (abstract). https://doi.org/10.1177/17470218211008060
- Storm & Stone, "Saving-enhanced memory", *Psychological Science* 26(2), 2015 (as described by Runge et al.). https://doi.org/10.1177/0956797614559285
- Runge, Frings & Tempel, "Saving-enhanced performance: saving items after study boosts performance in subsequent cognitively demanding tasks", *Memory*, 2019 (abstract). https://doi.org/10.1080/09658211.2019.1654520
- Sim, Eiger & Kohno, "AI-enabled human memory manipulation: misleading AI-generated summaries distort human memory", AIES 2026 (full text). https://ojs.aaai.org/index.php/AIES/article/download/43310/50870/47416
- Zindulka et al., "The AI memory gap: users misremember what they created with AI or without", CHI 2026 (abstract; note 23). https://arxiv.org/abs/2509.11851
- Stark & Perfect, "The effects of repeated idea elaboration on unconscious plagiarism", *Memory & Cognition* 36(1), 2008 (abstract and method). https://doi.org/10.3758/MC.36.1.65
- Draxler et al., "The AI ghostwriter effect: when users do not perceive ownership of AI-generated text but self-declare as authors", *ACM TOCHI* 31(2), 2024 (abstract). https://doi.org/10.1145/3637875
- Lee et al., "The impact of generative AI on critical thinking: self-reported reductions in cognitive effort and confidence effects from a survey of knowledge workers", CHI 2025 (abstract). https://doi.org/10.1145/3706598.3713778
- Schicchi et al., "A closer look at ChatGPT's role in concept map generation for education", *Interactive Learning Environments*, 2025 (search summary only). https://iris.uniroma3.it/handle/11590/511000
- Han & Choi, "Beyond linear digital reading: an LLM-powered concept mapping approach for reducing cognitive load", BEA 2025 (note 25). https://aclanthology.org/2025.bea-1.58.pdf

**Overviews, graphs and layouts**
- Shneiderman, "The eyes have it: a task by data type taxonomy for information visualizations", IEEE Symposium on Visual Languages, 1996. https://doi.org/10.1109/VL.1996.545307
- Craft & Cairns, "Beyond guidelines: what can we learn from the visual information seeking mantra?", IV 2005 (abstract). https://doi.org/10.1109/IV.2005.28
- Cockburn, Karlson & Bederson, "A review of overview+detail, zooming, and focus+context interfaces", *ACM Computing Surveys* 41(1), 2009 (summary section). https://www.microsoft.com/en-us/research/wp-content/uploads/2008/01/cockburn-ComputingSurveys09.pdf
- Hornbæk, Bederson & Plaisant, "Navigation patterns and usability of zoomable user interfaces with and without an overview", *TOCHI* 9(4), 2002 (note 25). https://lccd.umiacs.umd.edu/node/16152
- Ghoniem, Fekete & Castagliola, "On the readability of graphs using node-link and matrix-based representations: a controlled experiment and statistical analysis", *Information Visualization* 4(2), 2005 (abstract). https://doi.org/10.1057/palgrave.ivs.9500092
- Okoe, Jianu & Kobourov, "Revisited experimental comparison of node-link and matrix representations", GD 2017, and "Node-link or adjacency matrices: old question, new insights", *TVCG*, 2019 (results via the arXiv full text). https://arxiv.org/abs/1709.00293 ; https://doi.org/10.1109/TVCG.2018.2865940
- Purchase, "Which aesthetic has the greatest effect on human understanding?", Graph Drawing 1997 (abstract). https://doi.org/10.1007/3-540-63938-1_67
- Robertson et al., "Data Mountain: using spatial memory for document management", UIST 1998 (abstract; note 20). https://doi.org/10.1145/288392.288596
- Jones & Dumais, "The spatial metaphor for user interfaces: experimental tests of reference by location versus name", *ACM TOIS* 4(1), 1986 (abstract). https://doi.org/10.1145/5401.5405
- Scarr, Cockburn, Gutwin & Malacria, "Testing the robustness and performance of spatially consistent interfaces", CHI 2013 (abstract). https://doi.org/10.1145/2470654.2466430
- Marshall & Shipman, "Spatial hypertext: designing for change", *CACM* 38(8), 1995 (opening only). https://doi.org/10.1145/208344.208350
- Andrews, Endert & North, "Space to think: large high-resolution displays for sensemaking", CHI 2010 (abstract). https://doi.org/10.1145/1753326.1753336
- Thudt, Baur, Huron & Carpendale, "Visual mementos: reflecting memories with personal data", *TVCG* 22(1), 2016 (abstract). https://doi.org/10.1109/TVCG.2015.2467831

**Revisiting and recall**
- Roediger & Karpicke, "Test-enhanced learning: taking memory tests improves long-term retention", *Psychological Science* 17(3), 2006 (abstract). https://doi.org/10.1111/j.1467-9280.2006.01693.x
- Adesope, Trevisan & Sundararajan, "Rethinking the use of tests: a meta-analysis of practice testing", *Review of Educational Research* 87(3), 2017 (abstract; g via secondary summaries). https://doi.org/10.3102/0034654316689306 ; https://www.learningscientists.org/blog/2017/2/9-1
- Rowland, "The effect of testing versus restudy on retention: a meta-analytic review of the testing effect", *Psychological Bulletin* 140(6), 2014 (abstract; size via a secondary summary). https://doi.org/10.1037/a0037559
- Secondary summary giving the 0.50–0.61 range across these meta-analyses: *Frontiers in Psychology* 9:2412, 2018 (via search summary). https://www.frontiersin.org/articles/10.3389/fpsyg.2018.02412/pdf
- Karpicke & Blunt, "Retrieval practice produces more learning than elaborative studying with concept mapping", *Science* 331, 2011 (abstract). https://doi.org/10.1126/science.1199327
- Blunt & Karpicke, "Learning with retrieval-based concept mapping", *Journal of Educational Psychology* 106(3), 2014 (abstract). https://doi.org/10.1037/a0035934
- O'Day & Karpicke, "Comparing and combining retrieval practice and concept mapping", *Journal of Educational Psychology* 113(5), 2021 (abstract). https://doi.org/10.1037/edu0000486
- Pepe, Moyer, Peña & Rajaram, "Deceitful hints: a meta-analytic review of the part-list cuing impairment in recall", *Psychonomic Bulletin & Review* 30, 2023 (abstract). https://doi.org/10.3758/s13423-023-02263-9
- Alfieri, Nokes-Malach & Schunn, "Learning through case comparisons: a meta-analytic review", *Educational Psychologist* 48(2), 2013 (abstract). https://doi.org/10.1080/00461520.2013.775712
- Braasch, Rouet, Vibert & Britt, "Readers' use of source information in text comprehension", *Memory & Cognition* 40(3), 2012 (abstract). https://doi.org/10.3758/s13421-011-0160-6
- Mar, Li, Nguyen & Ta, "Memory and comprehension of narrative versus expository texts: a meta-analysis", *Psychonomic Bulletin & Review* 28, 2021 (abstract). https://doi.org/10.3758/s13423-020-01853-1

**Named in §6 but not read**
- O'Donnell, Dansereau & Hall, "Knowledge maps as scaffolds for cognitive processing", *Educational Psychology Review* 14(1), 2002. https://doi.org/10.1023/A:1013132527007
- Hornbæk & Hertzum, "The notion of overview in information visualization", *IJHCS* 69(7–8), 2011. https://doi.org/10.1016/j.ijhcs.2011.02.007

**Earlier notes and project documents** (in this repository)
- Note 25, [`25-overview-display.md`](25-overview-display.md): products, surfaces, the outline and map candidates, 2.1–2.7.
- Note 20, [`round4/20-index-expansion-capture.md`](../round4/20-index-expansion-capture.md) §1: grouping and size, argument maps, spatial memory, crib sheets.
- Note 23, [`round5/23-memory-architecture-and-dreaming.md`](../round5/23-memory-architecture-and-dreaming.md) §4: H.1–H.8.
- [`GOAL.md`](../../GOAL.md), [`DESIGN.md`](../../design/revision-2026-10-23/DESIGN.md) §6 and §8, [`overview-sketch-round.md`](../../design/revision-2026-10-23/overview-sketch-round.md).
