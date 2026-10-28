# 15. Formats for understanding your own knowledge

*Round 3 research note. Written 2026-10-10. Read with [GOAL.md](../../GOAL.md) §2 (2026-10-10): the unit is the user's own knowledge, and the human view is short, connects the dots, and gives depth on click.*

**Question.** Which ways of showing a person's own body of knowledge help them understand it, follow its logic, connect the dots across contexts, and remember it when they reread it in short visits?

## Answer

No single format wins. The evidence favours a **short text structure, not a diagram**: **claim cards**, each with one clean sentence of what the person holds, **why**, **where it applies and where not**, a one-line story of **how they got there**, and links, with sources one click away, grouped under the **questions the person is working on**, answer first. Maps and outlines perform about the same (concept maps beat outlines and lists by only g = 0.28, and in one study the gap on details was near zero for readers who knew the topic); large maps are hard to take in, and AI is weakest at hierarchy. The big measured gains come from elsewhere: summaries over full text, stories over exposition (g = 0.55), comparing cases with the shared principle stated (d = 0.50), and headlines written as claims. The rejected knowledge map had no "because" and no "where it applies", and its IDs only added load. **Recommendation:** (1) question-led claim cards in a pyramid as the default; (2) a principle-with-cases view for dots across contexts; (3) a short thinking timeline for how an idea evolved; (4) a small, local tension view only for conflicts. Argument maps, mind maps and whole-knowledge graphs should not be the default.

## Evidence table

Strength: **Strong** means meta-analyses or many experiments. **Moderate** means several experiments, or one meta-analysis with caveats. **Weak** means small or single studies. **None** means practitioner writing only. Most of this research tested students learning *new* material, usually on immediate tests. Below, "own knowledge" means familiar material reread later, which is an extrapolation.

| Format | Good for | Evidence (strength) | Reading load | Fit: own knowledge | Fit: AI generation |
|---|---|---|---|---|---|
| **Argument map** (claim, reasons, objections as a tree) | Making reasons explicit; finding gaps | Building maps with heavy practice and feedback raised reasoning scores: d = 0.71 after a 12-week seminar (Cullen 2018); about 0.8 SD (van Gelder, secondary); tripled gains (Twardy 2004). *Reading* a ready-made map gave better memory but not better comprehension, and a 50-part argument was too big to take in (Dwyer 2010). No consistent edge over outlines [04]. **Moderate for building, weak for reading** | High; 2-D scanning; poor on phones | Good for one contested idea; overkill as a default | Medium-low: finding the relations between arguments is still an open problem for LLMs (survey, 2025) |
| **Concept / knowledge map** (labelled nodes and links) | Seeing how many ideas relate | Studying maps beat studying text, g = 0.39 (k = 29), and beat outlines and lists, g = 0.28 (k = 10). Larger gains for central ideas than details; the only detectable subgroup gain was for readers with low verbal ability. Layout matters: a gestalt-designed map scored 1.10 against 0.35 in one study. In one study, map vs outline on detail recall by high-prior-knowledge readers was 0.02 (all from Nesbit & Adesope 2006). Building beats studying (Schroeder 2018). **Strong, but mostly new material** | Medium, and rises fast with size | Small local maps only; little added for familiar material | Medium: picks out concepts well; link labels and layout are weak |
| **Mind map** (radial, unlabelled links) | Brainstorming; overview of one topic | 10% more recall at one week, but the CI crossed zero (n = 50; Farrand 2002). No gain over ordinary notes (n = 131; D'Antoni 2010). LLM mind maps scored lower on hierarchy (51 vs 62) and took longer to fix (2025). **Weak** | Low-medium, but the links say nothing about "because" | Poor for following logic | Weak at hierarchy |
| **Outline / hierarchical summary** | Top-down order; fast scanning; phones | Studying summaries beat studying full texts for main points (Reder & Anderson 1980, secondary). Graphic organizers beat outlines on relations and delayed tests (Robinson & Kiewra 1995, abstract). Maps beat outlines only slightly (above). **Moderate** | Low | High | High; density needs a budget, because readers prefer dense summaries only up to a point (Chain of Density 2023) |
| **Pyramid principle** (Minto: answer first, then grouped reasons) | Following the logic in a short visit | No direct test found. Indirect support: context given before a passage strongly improved comprehension and recall (Bransford & Johnson 1972); signals improve memory for what they signal (Lorch 1989); concise, scannable text scored 124% better in one usability test (Morkes & Nielsen 1997). **Weak direct, moderate indirect** | Low | High: it forces "what do I conclude, and why" | High, if every reason traces to a source |
| **Toulmin** (claim, grounds, warrant, qualifier, rebuttal) | Scope and exceptions | Found no reader-side experiments. The studies are content analyses of writing. **Weak** | Medium with all slots; low with qualifier and rebuttal only | The qualifier and rebuttal map directly onto "where it applies, where not" | Medium: the warrant is often invented |
| **IBIS / issue map** (question, positions, pros and cons) | Conflicts, open questions, decisions | Worked with a skilled live facilitator; failed when users had to classify their own input [04][05]. The vendor page gives no outcome data. **Weak** | Medium | High for tensions and for "what to learn" | Medium-high: the AI can play the facilitator |
| **Decision record / decision journal** | How a conclusion was reached; what replaced what | ADR adoption on GitHub is low: half of repos have 1-5 records (2023). One action-research study found ADRs fixed several documentation problems (2024). Hindsight bias is robust (Fischhoff 1975), but journals have not been tested as a cure. **Weak** | Low per record; high in bulk | Good behind "how I got here"; poor as the front page | High: fixed fields and a superseded status |
| **Evergreen notes** (atomic, concept-oriented, densely linked) | Units that accumulate over time | Practitioner writing only. Matuschak gives no studies, though claim titles have indirect support (signalling row). **None** | Low per note; dense links overwhelm | High as a storage discipline | High for atomic claims; risk of over-linking |
| **Progressive summarization / highlighting** | Finding the key lines in a source | The method itself is untested. Highlighting supplied by someone else improved memory and comprehension (g = 0.44 each). Highlighting your own text improved memory only (g = 0.36) (Ponce 2022). **Moderate for supplied highlights** | Low | Good for the source layer behind the click | High, if the highlights are accurate |
| **Cornell notes** (cue column, notes, summary) | A cue, its answer, and a summary | Small single-site studies favour it over outline and verbatim notes; no meta-analysis found. **Weak** | Low | The layout fits; the study routine does not (no rituals) | High |
| **Narrative of how my thinking evolved** | Memory; the "why"; change over time | Stories are recalled and understood better than exposition: g = 0.55 overall, 0.72 for memory, 0.48 for comprehension; 78 samples, 33,078 people (Mar 2021). Not tested on personal histories. **Strong for the genre** | Low if short; long stories bury the point | High | Medium: risk of invented causes and hindsight smoothing |
| **Question-led** (question, answer, reasons, conditions) | Orienting the reader; organizing what to learn | Prequestions steer attention to relevant material (Carpenter, secondary). Questions help recall of the material they target and can hurt the rest (Schmitt 1985, secondary). No clear winner between question and statement headings. **Weak-moderate** | Low | High: the person's own questions are the best signal of gaps [12 F12] | High |
| **Signalling and headings** | Memory for the main structure | Signals improve memory for the content they flag, not for the rest (Lorch 1989). Headings helped recall of unfamiliar topics, not familiar ones (Lorch & Lorch 1996). Meta-analysis: g = 0.53 retention, 0.33 transfer (Schneider 2018, secondary). Sentence headlines beat topic headlines on comprehension and on recall a week later (Garner & Alley, conference). **Strong for signals; moderate for claim headlines** | Reduces load | Claim headlines: high. Topic headings: low value for familiar material | High |
| **Visual vs text** | Choosing a medium | Diagrams win when a task needs spatial search or many relations seen at once (Larkin & Simon 1987). Maps help low-verbal readers most (above). Explanation that novices need hurts experts (expertise reversal; Kalyuga 2003). Surface wording fades fast while meaning stays (Sachs 1967). **Strong theory, moderate data** | Text is lower for linear logic | Text first; small local visuals | Text is more faithful; diagrams are more error-prone |
| **Case comparison / principle with cases** *(added)* | Connecting the dots across contexts | Comparing cases beat studying single cases, d = 0.50 (57 experiments; Alfieri 2013). Comparing two cases made transfer about three times as likely as studying them separately (Loewenstein, Thompson & Gentner; Gentner et al. 2003). Expert knowledge is tied to its conditions of use (*How People Learn*, secondary). **Strong** | Medium | High: it fits the "real work vs interview" conflict (GOAL §2) | Medium: risk of false analogies and platitudes |

## What the evidence says, in short

1. **Your own knowledge needs cues, not explanations.** Full explanations hurt experienced readers (expertise reversal), and headings stop helping with familiar topics. What brings an idea back is its gist, its reason and its context. Wording fades fast while meaning lasts (Sachs), so rough verbatim phrasing helps little. Write the gist in clean words and keep the quote as a source.
2. **Short is right, with a length budget.** Summaries beat full texts for main points. Irrelevant detail hurts, g = −0.33 (seductive details, Sundararajan & Adesope 2020).
3. **Logic comes from "because" and order, not from a diagram.** For familiar material an outline matches a map. Argument maps help when people *build* them with practice, which the user will not do (GOAL §4.1).
4. **Cross-context dots are the best-evidenced part:** two contexts side by side, with the shared principle *and* the separating condition stated.
5. **Stories carry the why.** One line of "how I got here" is enough on the card.
6. **Claims as headlines.** Internal IDs and separate link lists add load with no content.

## Recommended formats

An invented example of the default card (not from the user's data):

```
How do I make a talk land?                          <- the question being worked on
  Lead with the one claim, then three reasons.      <- current answer (your voice)
  Why: listeners keep the first claim; reasons without it scatter.
  Applies: 10-30 min talks, mixed audiences.  Not: workshops (questions come first).
  How you got here: tried story-first (Mar) -> feedback, rebuilt (Apr) -> switched (May)
  Connects: "Write the summary first" (writing)   Tension: "Start from their question" >
  Sources: 4 chats, 1 article >
```

| # | Format | Use | Why | What would make it fail |
|---|---|---|---|---|
| A | **Question-led claim cards in a pyramid** | The default page: a handful of active questions, each with its current answer; the card on click; sources on a second click | Pyramid plus claim headlines plus signalling; cue first, depth on demand | Vague or AI-voiced claims ("You've concluded..."); more than about 7 questions per screen; reasons that just restate the claim; reasons the AI invented that are not in the sources; questions that read like a quiz (the answer must sit right under the question, never hidden) |
| B | **Principle with cases** | Shown when one principle appears in two or more contexts: a table with one row per context, saying what holds, what differs, and the deciding condition | Case-comparison and conditional-knowledge evidence | Forced analogies; principles abstracted into platitudes ("it depends"); project-only items padding the table; the deciding condition left out |
| C | **Thinking timeline** | On click from a card: 3-6 dated steps of how a position changed, with superseded positions visible and a reason for each change | Narrative advantage; ADR-style supersession | Turning into a diary of every chat; invented cause-and-effect; quietly rewriting the past to look consistent (hindsight) |
| D | **Local tension view** | Only for conflicts: the question on top, two positions side by side, pros and cons, and the condition that decides between them. Text by default; a tiny diagram only if there are 7 nodes or fewer | IBIS question-centred conflicts; diagrams help only when relations must be seen at once | Growing into a graph; unlabelled links; IDs; a diagram on a phone; listing a "tension" that is really a scope difference |

## The processing jobs that produce these formats

Pasting the original words is not enough. These are the jobs behind the view. Each one is checkable, which fits GOAL §3.4.

1. **Restate.** Rewrite each item as one gist-level sentence in the person's voice. Mark adopted AI ideas as such. Keep the verbatim quote as a source.
2. **Ground the why.** Pull out the reasons actually given in the discussions. If there are none, the item is still forming.
3. **Scope.** Derive "applies when" and "not when" from the contexts where the item came up (Toulmin's qualifier and rebuttal).
4. **Abstract across contexts.** Find items that are instances of one principle. Write the principle and keep the items as its cases (view B).
5. **Order.** Build the pyramid: the question, the answer, two to four grouped reasons. Group by the question the person is working on, never by source chat.
6. **Narrate.** Write the timeline from the supersession history (view C).
7. **Pair tensions.** Put conflicting positions under one question, with the condition that decides between them (view D).
8. **Budget and verify.** Enforce limits on length and density. Check every line against its sources. Render without internal IDs.

Jobs 2-4 also give an input to the **value threshold** asked for in GOAL §2. An item with no reason, no scope beyond one moment, and no connection is probably a passing preference. That is one signal, not the threshold itself.

## What this means for Northstar

- **The human view becomes a set of rendered claim cards, not a map.** The store keeps atomic, sourced items. The view is produced by jobs 1-8, and code renders it from structured fields rather than letting a model draw diagrams freely.
- **The default view is A; views B, C and D open from it.** There is no global graph, no radial mind map, and no IDs on screen. This is consistent with round 2 [12 F15].
- **The same fields serve the AI side.** In the probe, memory made replies echo the user's positions back. "Applies when / not when" gives the injector a concrete test for "very strongly linked" (GOAL §2), and gives the AI a condition to reason with instead of a position to repeat. This is a hypothesis to test, not a finding.
- **Project-only knowledge (open; the user leans no).** One way to handle it: project items appear only as cases under a personal principle (view B), or in a separate project view, so they never pad the personal view. This goes to the user as a question.
- **Benchmark idea.** In the allowed one-off session, show cards in two formats after a delay; ask the person to give the why and scope in their own words, and note which format they pick. A measurement, not a product feature.

## Limits of this evidence

No study tests a person rereading their *own* knowledge, so the fit ratings are extrapolations. Several figures come from abstracts or secondary summaries (labelled). Argument-mapping studies are often by the tools' own authors. Pyramid, evergreen notes, progressive summarization and decision journals have no direct tests.

## Sources

All sources checked 2026-10-10. Square brackets are earlier notes in this repo: [04] `../04-epistemic-representation.md`, [05] `../05-reasoning-decisions-goals-questions.md`, [12] `../round2/12-knowledge-structure.md`.

- Nesbit & Adesope (2006), *RER* 76(3), full text read: https://www.sfu.ca/~jcnesbit/articles/NesbitAdesope2006.pdf
- Schroeder et al. (2018), concept-map meta-analysis: https://link.springer.com/article/10.1007/s10648-017-9403-9
- Dwyer, Hogan & Stewart (2010), abstract: https://research.universityofgalway.ie/en/publications/the-evaluation-of-argument-mapping-as-a-learning-tool-comparing-t/
- Cullen et al. (2018), *npj Sci. Learn.*, abstract: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6279835/
- Twardy (2004), abstract: https://philarchive.org/rec/TWAAMI ; van Gelder's 0.8 SD figure, secondary (the page blocked fetching): https://ecampusontario.pressbooks.pub/criticalthinking1234/chapter/introduction/
- Farrand et al. (2002), abstract: https://www.gwern.net/doc/psychology/spaced-repetition/2002-farrand.pdf ; D'Antoni et al. (2010): https://bmcmededuc.biomedcentral.com/articles/10.1186/1472-6920-10-61
- LLM vs designer mind maps (arXiv 2501.09457, 2025), read: https://arxiv.org/html/2501.09457v1
- LLMs in argument mining, survey (2025), abstract: https://arxiv.org/abs/2506.16383
- Reder & Anderson (1980), secondary: https://www.andrew.cmu.edu/user/reder/publications/80_lmr_jra.html
- Robinson & Kiewra (1995), abstract: https://doi.org/10.1037/0022-0663.87.3.455
- Adams et al. (2023), Chain of Density: https://arxiv.org/abs/2309.04269
- Minto pyramid, practitioner summary (no evidence found): https://untools.co/minto-pyramid/
- Bransford & Johnson (1972), secondary summaries: https://doi.org/10.1016/S0022-5371(72)80006-9
- Lorch (1989): https://link.springer.com/doi/10.1007/BF01320135 ; Lorch & Lorch (1996): https://scholars.uky.edu/en/publications/effects-of-headings-on-text-recall-and-summarization/
- Schneider et al. (2018) signalling meta-analysis, secondary: https://www.qic-wd.org/sites/default/files/Umbrella%20Summary%20-%20Signaling%20in%20Training%20111021.pdf
- Garner & Alley, assertion-evidence (conference paper): https://peer.asee.org/assertion-evidence-slides-appear-to-lead-to-better-comprehension-and-recall-of-more-complex-concepts.pdf
- Morkes & Nielsen (1997): https://www.nngroup.com/articles/concise-scannable-and-objective-how-to-write-for-the-web/
- Sundararajan & Adesope (2020), seductive details: https://rex.libraries.wsu.edu/esploro/outputs/journalArticle/Keep-it-Coherent-A-Meta-Analysis-of/99900601155501842
- Kalyuga et al. (2003), expertise reversal: https://ro.uow.edu.au/edupapers/136
- Sachs (1967), abstract: https://link.springer.com/article/10.3758/BF03208784
- Larkin & Simon (1987): https://mechanism.ucsd.edu/bill/teaching/F12/cs200/Readings/larkin.whyadiagramissometimesworth.1987.pdf
- Mar et al. (2021), full text read: https://pmc.ncbi.nlm.nih.gov/articles/PMC8219577/
- Alfieri et al. (2013), abstract: https://doi.org/10.1080/00461520.2013.775712 ; Gentner et al. (2003): https://dedregentner.owlstown.net/publications/38525
- *How People Learn* (NRC 2000), secondary on conditions of applicability: https://www.nationalacademies.org/read/9853/chapter/1
- Ponce et al. (2022), highlighting meta-analysis, abstract: https://link.springer.com/10.1007/s10648-021-09654-1
- Prequestions (Carpenter), secondary: https://www.earli.org/assets/images/Abstract-Vita-Shana-Carpenter-SIG67-Conference.pdf
- Matuschak, evergreen notes: https://notes.andymatuschak.org/Evergreen_notes ; titles as APIs: https://notes.andymatuschak.org/Evergreen_note_titles_are_like_APIs
- Forte, progressive summarization: https://fortelabs.com/blog/progressive-summarization-a-practical-technique-for-designing-discoverable-notes/
- Nygard (2011), ADRs: https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions ; ADR action research (2024): https://research.chalmers.se/en/publication/542849 ; ADRs on GitHub (2023): https://research.jku.at/en/publications/using-architecture-decision-records-in-open-source-projects-an-ms/
- Conklin, dialogue mapping (no outcome data): https://cognexus.org/id17.htm
- Hindsight bias overview (Pohl, secondary on Fischhoff 1975): https://iphils.uj.edu.pl/~a.trybus/classes/logic/cs/20.Pohl.Hindsight.Bias.pdf
- Cornell notes, single study (Akintunde 2013): https://dspace.unijos.edu.ng/jspui/handle/123456789/2566
