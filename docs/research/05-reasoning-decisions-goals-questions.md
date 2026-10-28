# Track 05: Beyond facts. Representing reasoning, decisions, goals, and open questions

*Research note, 2026-10-07. Web tools were used to check specific claims and find 2025–2026 work. The shared web-search budget ran out partway through, so a few claims come from memory and are marked "(unverified)".*

## Scope and questions

Most "second brain" and AI-memory designs treat knowledge as **statements about the world**: facts, notes, claims, and the links between them. A person's working understanding also contains other things: **questions** they are carrying, **decisions** they made and why, **expectations** about how things will turn out, **goals** that decide what matters, **principles** they have distilled, and a history of **changing their mind**. This track asks how those objects should be represented. Claims and beliefs as such belong to other tracks. Here they come up only where these objects depend on them.

Questions this note tries to answer:

1. Which object types are **necessary and sufficient**? Which items on the brief's list (ideas, beliefs, reasoning, decisions, goals, uncertainty, contradictions, evolving understanding) are really object types, and which are properties or relations?
2. What **fields** does each type need? Which must be filled at capture, and which can wait?
3. How do these objects **connect to claims and beliefs** so that a change in one shows up in the others (for example, a weakened belief flags the decisions resting on it)?
4. What makes capture **cheap enough to happen**, given that design-rationale capture has failed for 50 years?
5. How do goals and open questions decide **relevance**, meaning which incoming information matters?
6. How do these objects **evolve** without destroying the history that gives them their value?

## Key findings

**1. Formal rationale capture (IBIS, QOC, DRL) failed in practice. Cost and benefit fall on different people at different times, and the schemas demand premature formalization.**
*Mechanism:* IBIS (Kunz & Rittel, 1970) structures reasoning as Issues → Positions → Arguments. QOC (MacLean, Young, Bellotti & Moran, 1991) adds explicit **Criteria** for judging Options. DRL (Lee & Lai, 1991) adds goals, claims, and evaluation relations. All three ask the person to stop and classify their thinking while they are still thinking. The capturer pays now. The benefit goes later to someone else, usually a future maintainer. Grudin's disparity argument from CSCW (1988), applied to design capture (Grudin, 1996), explains the result: people don't do unrewarded work for unknown future beneficiaries. Shipman & Marshall's *Formality Considered Harmful* (1999) adds a second mechanism. Formal structure forces users to state things they don't yet know, commit early to categories, and spell out tacit knowledge, so they avoid it or fill it in badly.
*Evidence:* Buckingham Shum & Hammond's review of argumentation-based design rationale (IJHCS 1994) carries the question "what use at what cost?" in its title. It found the cognitive overhead real and the downstream benefits poorly demonstrated. Shipman & McCall (1997) concluded that rationale should be allowed to *emerge from design communication* rather than be authored as a separate artifact. One partial success, **dialogue mapping** with gIBIS/Compendium (Conklin), works for a specific reason. A dedicated facilitator bears the capture cost, and the map pays off *inside the meeting* as shared clarity on a common display.
*For us:* in a personal system the "someone else" who benefits is the future self, and Grudin's gap still applies. A design that only pays off at retrieval time months later will repeat the IBIS failure.

**2. ADRs are the best-known success in rationale capture. Even so, adoption is thin and many records are written after the fact.**
*Mechanism:* Nygard's lightweight ADR (2011) succeeds through constraints:
- Five fields: Title, Context, Decision, Status, Consequences.
- One or two pages.
- Stored in version control next to the code.
- Numbered and never reused.
- An accepted ADR is not rewritten. A new one supersedes it, so the history survives.

The stated motivation names the failure ADRs prevent. Without recorded rationale, newcomers either accept old decisions blindly or reverse them blindly.
*Evidence:* ThoughtWorks Technology Radar moved Lightweight ADRs to "Adopt" in November 2017. The empirical picture is more sober. Buchgeher et al. (IEEE Access, 2023) mined GitHub and found 921 repositories with ADRs. About half held only 1–5 records, which suggests teams tried the practice without keeping it up. Sustained use was a team activity spread over time. An ICSA 2026 study of the same population (~5,800 ADRs) found that about 63% were *created already in "accepted" status*. That bypasses the deliberation ADRs exist for and means most were written after the decision. ADR attributes correlated only weakly with code-quality metrics.
*For us:* the parts worth taking are the *immutability-plus-supersession* structure and the tiny template. The weak spot is the social trigger (PR review) that keeps ADRs alive in teams. A personal system has no such trigger, so something else must play the reviewer.

**3. Most of a decision or belief record's value comes from a timestamp set before the outcome is known. Memory of past beliefs is reconstructed, not retrieved.**
*Mechanism:* Hindsight bias (Fischhoff, 1975) and consistency bias rewrite what we remember believing. Markus (1986) re-interviewed people nine years after a 1973 attitude survey. Their recalled 1973 positions were much closer to their 1982 positions than to what they had actually said. They understated how much they had changed. Outcome bias (Baron & Hershey, 1988) means a decision gets judged by how it turned out, which Annie Duke calls "resulting" (*Thinking in Bets*, 2018). The only witness to "what I knew and expected then" that isn't contaminated is a record written then and left unchanged.
*Evidence:* Michael Mauboussin relays Kahneman's best single piece of advice for investors: buy a cheap notebook and record decisions as you make them. The record should include what you expect, why, and how you feel (popularized by Farnam Street).
*For us:* fields recording beliefs and expectations at a point in time must be **append-only once committed**. A system that lets someone tidy up last year's reasoning destroys the evidence its review features depend on.

**4. AI can cut capture cost dramatically, but the rationale it writes is mostly *plausible*, not *actual*.**
*Mechanism:* An LLM asked why a choice was made produces the generic reasons such choices usually have, not the specific reasons this person had.
*Evidence:* Zhou et al. (ACM TOSEM, 2025) had five LLMs, with three prompting strategies, generate design rationale for 100 architecture decisions from Stack Overflow and GitHub.
- Measured against expert-annotated rationale, **precision was only 0.267–0.278**, while recall was 0.627–0.715.
- Of the arguments the experts had not mentioned, roughly 64–69% were still judged helpful.
- About 1.6–3.2% were potentially misleading.

A related February 2026 study (Su et al.) checked 980 ADRs across 109 repos for violations. LLMs did well on **explicit, code-inferable decisions** and poorly on implicit or organizational ones.
*For us:* AI-generated rationale is useful as a *prompt* ("did you also weigh X?"). Stored as the person's rationale, it is harmful. It also launders AI reasoning into the record that is supposed to counter hindsight. Separately, decisions that AI systems will read need explicit, checkable statements of what was decided. Narrative alone isn't enough.

**5. Calibration improves only through explicit, resolvable predictions with feedback. Most personal decisions produce neither.**
*Mechanism:* Calibration is learned from frequent, quick, unambiguous feedback. Weather forecasting is the classic well-calibrated case (unverified as to specific studies). Life decisions give slow, confounded feedback, so people never learn their own error rates. Turning a vague expectation into a proposition with a probability, a resolution criterion, and a date *manufactures* feedback.
*Evidence:*
- Tetlock's *Expert Political Judgment* (2005) followed 284 experts (~28,000 predictions per Wikipedia's summary, 1984–2003). They did barely better than chance and often worse than simple extrapolation.
- The Good Judgment Project won IARPA's tournament, reportedly about 30% better than intelligence analysts with classified access (as reported in *Superforecasting*).
- Under an hour of probabilistic-reasoning training improved Brier scores by **6–11%** (Chang et al., JDM 2016).
- Fatebook (Sage, July 2023) builds the practice into a tool. A prediction is one line in a new tab, dates are auto-detected, an email reminder asks for resolution, records are private by default, a calibration chart builds up, and it plugs into Slack and Chrome.

*2025–2026:* On ForecastBench (Forecasting Research Institute, January 2026), superforecasters scored 0.085 (difficulty-adjusted Brier) against 0.102 for the best LLMs. Parity is projected around November 2026 (95% CI January 2026 – November 2027).
*For us:* AI can now produce a credible *outside-view* forecast to set beside the person's. That enables an interesting experiment comparing the person's calibration with the AI's on the same personal questions.

**6. Premortems help, but the famous "30% improvement" measures the number of reasons generated, not accuracy.**
*Mechanism:* Framing failure as certain ("it is a year from now and this failed; why?") licenses dissent and produces specific failure stories (Klein, HBR 2007).
*Evidence:* The study usually cited (Mitchell, Russo & Pennington, 1989) found that prospective hindsight increased the *number* of reasons people generated by about 30%. It did not assess their quality. Later tests are thin but positive. Veinott, Klein & Wiggins (2010) found premortems reduced plan overconfidence about twice as much as pros/cons methods. Gallop & Bischoff (2016, as summarized by Jason Collins) found more high-quality and "black swan" risks among experienced engineers.
*For us:* a premortem is a cheap, high-yield *capture prompt*. Its output maps directly onto **kill criteria and revisit triggers**, which are machine-checkable fields.

**7. Goals work, but they form networks and have side effects. The cheapest high-yield format is the if-then plan.**
*Evidence:*
- Specific, hard goals raise performance (Locke & Latham's 35-year program, 2002).
- Implementation intentions ("if situation X, then I do Y") had **d = 0.65** across 94 independent tests (Gollwitzer & Sheeran, 2006).
- Goal systems theory (Kruglanski et al., 2002) treats goals and means as an associative **network**. One means can serve several goals (multifinality), and one goal can have several means (equifinality). A tree like OKR cascades or GTD horizons misrepresents this.
- *Goals Gone Wild* (Ordóñez et al., 2009) documents side effects: narrowed focus, distorted risk-taking, unethical shortcuts, inhibited learning.
- Making a concrete plan removed the intrusive-thought costs of unfinished goals (Masicampo & Baumeister, JPSP 2011). In other conditions a specific plan made people closed-minded about alternative routes (Masicampo & Baumeister, 2012). Replication status of both is unverified.

*Contradicts popular belief:* the Zeigarnik effect, the claim that unfinished tasks are *remembered* better and the usual justification for "open loops", failed a 2025 meta-analysis (Ghibellini & Meier). Across 37 studies excluding Zeigarnik's own, the recall ratio of interrupted to completed tasks was about 0.99. The **Ovsiankina effect**, the tendency to *resume* interrupted tasks, held at about 67% resumption.
*For us:* recording an open goal or question doesn't pay off because it relieves a memory burden. It pays off as a *resumption cue* and as a *plan that lets the mind let go*.

**8. Goals and open questions decide what other knowledge is relevant. They are the demand side.**
*Mechanism:* A fact has no relevance until it bears on something the person is trying to do or know. Feynman's advice, as relayed by Rota ("Ten Lessons I Wish I Had Been Taught", 1997): keep about a dozen favorite problems in mind and test every new trick or result against each of them. Hamming ("You and Your Research", 1986) observed that great scientists carry 10–20 important problems and drop everything when a new idea bears on one. He also set aside Friday "Great Thoughts Time" to revisit them. GTD's horizons of focus run from purpose and principles through vision, 1–2 year goals, areas of focus, and projects down to actions. Higher horizons generate and filter lower ones.
*Evidence quality:* this is practitioner wisdom from very productive people, not controlled research. The *mechanism*, standing queries that route incoming information, is concrete enough to implement and test.
*For us:* "disconnected fragments" may be less a linking problem than a missing-demand problem. A fragment that connects to no question, goal, or decision may be legitimately disposable.

**9. Belief change is under-recorded and under-remembered, so the change log has to be produced by the system.**
*Mechanism:* Consistency bias overwrites the remembered past (Markus, 1986). Disconfirming information is also forgotten faster. Darwin's "golden rule" in his autobiography was to write down any fact or thought that went against his general results *immediately*, because he had learned that such items slipped from memory far more readily than favorable ones.
*Evidence:* the Edge 2008 annual question ("What have you changed your mind about? Why?") drew 165 contributors. People can produce good changelogs when prompted, but hardly anyone keeps one spontaneously.
*For us:* "what I changed my mind about" should be a **query over revision events**, not a document someone has to remember to write. Disconfirming evidence deserves *asymmetric* (higher-priority) capture.

**10. Principles and mental models decay because compressing them strips away cases and boundary conditions.**
*Mechanism:* A principle compresses many experiences into one rule. Once the cases are gone, nobody can tell when the rule doesn't apply. The principle then becomes a resource for justifying whatever was already wanted rather than a guide. Legal precedent survives because a holding stays attached to its facts. Later courts distinguish cases by comparing facts, not rules.
*Evidence (weaker):* Dalio's *Principles* began as an evolving internal document and was fixed as a book in 2017. Journalistic accounts of Bridgewater (Copeland, *The Fund*, 2023) describe the principles being applied selectively. That is a characterization from memory and contested by Dalio (unverified). There is little systematic research on personal principles documents.
*For us:* a principle with no linked origin cases should count as a weak object.

**11. Preferences and values are often constructed at the moment they are elicited, not retrieved.**
*Evidence:* decades of preference-reversal research (Lichtenstein & Slovic, *The Construction of Preference*, 2006). Normatively equivalent ways of asking (choice vs pricing) give systematically different answers, depending on framing, reference points, and time pressure.
*2025:* consumer AI memory has gone mainstream. Claude memory reached Team/Enterprise in September 2025 and Pro/Max in October 2025. It is project-scoped, with a user-viewable and editable summary. These systems mostly store preferences as flat statements ("prefers X").
*For us:* a stated preference is an observation in a context, not a timeless fact. **Criteria actually used in real decisions** (QOC's "C") are better evidence of values than self-description, and they accumulate as a side effect of decision capture.

**12. Dependency tracking between beliefs and conclusions is solved in logic and unsolved in practice, because people rarely record justifications.**
*Mechanism:* Truth Maintenance Systems (Doyle, 1979; de Kleer's ATMS, 1986) record which beliefs justify which conclusions and relabel the dependents automatically when a premise is withdrawn. Human decisions rest on many implicit assumptions. Recording all of them is impossible, and auto-retracting a human decision is wrong because the person may have other reasons.
*For us:* a workable version tracks only a few **load-bearing assumptions** the person (or the AI, with confirmation) marks explicitly. It also **flags instead of retracting**. Project management's RAID log (Risks, Assumptions, Issues, Dependencies) is the practical precedent: assumptions listed so they can be checked.

## Ideas worth stealing

1. **Append-only records with supersession chains** (Nygard ADRs). A committed decision is never edited. A new decision supersedes it and links back. Status values: proposed → accepted → deprecated/superseded.
2. **Pre-outcome expectation fields** (Kahneman via Mauboussin; Farnam Street's decision-journal template). Record what you expect, why, how confident you are, and how you feel, before the outcome. Review later against the record, not against memory.
3. **The premortem as a capture prompt** (Klein). At commitment time the AI asks: "Assume this went badly a year from now. What happened?" The answers become kill criteria.
4. **Tripwires and kill criteria** (Heath & Heath, *Decisive*, 2013; Duke, *Quit*, 2022). Conditions or dates, fixed in advance, that force a revisit. They are machine-checkable against incoming information.
5. **The Fatebook capture loop.** One-line capture, auto-parsed resolution date, reminder to resolve, private by default, calibration chart as the reward, and capture inside tools already in use. For us, "already in use" means the AI chat.
6. **Feynman/Hamming problem lists as standing queries.** Keep a short list (about 12–20) of open questions. Every new input is tested against each, and matches attach as candidate evidence. Hamming's Friday "Great Thoughts Time" becomes a scheduled review of the list.
7. **IBIS's question-centered structure for contradictions.** Two conflicting views become two *positions on the same issue*, with pro and con arguments, rather than two floating facts with a "contradicts" edge. Anchoring the conflict to a question makes it productive and tells you what would resolve it.
8. **QOC's explicit Criteria.** Recording *what was optimized* in each decision produces a profile of revealed values over time.
9. **Dialogue mapping's facilitator role** (Conklin). Someone other than the thinker bears the capture cost, and the map pays off immediately. An AI assistant can play the facilitator *during* a conversation, keeping a live issue/option/consideration map whose by-product is the record.
10. **Incremental formalization** (Shipman & McCall, 1999; Shipman & Marshall, 1999). Capture informally first. The system *proposes* structure later, and the person accepts or ignores it.
11. **Lab-notebook discipline.** Dated entries, never erased (corrections are struck through and annotated, not deleted), failures recorded alongside successes, and expectation stated before observation.
12. **Darwin's golden rule.** Capture disconfirming evidence immediately and with priority.
13. **The Edge prompt as a ritual.** "What have you changed your mind about, and why?" works as a quarterly review, generated from revision events.
14. **The if-then format** (Gollwitzer). Goals and decisions carry "if X, then Y" clauses. These are both the most effective psychological format and directly usable as triggers.
15. **Horizon plus cadence on goals** (GTD). Each goal has a time horizon, and review frequency scales with it: weekly for projects, quarterly for 1–2 year goals, annually for vision and purpose.
16. **The Decision Quality chain as a review rubric** (Spetzler et al., Strategic Decisions Group). Frame, alternatives, information, values and trade-offs, reasoning, commitment. Reviews grade the *decision* against the information available then, separately from the *outcome*.
17. **The TMS justification set, trimmed.** Each decision names at most a handful of load-bearing assumptions, pinned to the belief *version* that held at decision time.
18. **AI outside-view counter-forecast** (ForecastBench-era capability). Record an independent AI probability next to the person's. Keep it out of view until the person has committed, to avoid anchoring.

## Pitfalls and anti-patterns

1. **A rich schema at capture time.** IBIS/QOC/DRL tools asked for full argument structure up front and were abandoned outside facilitated settings (Finding 1). Every required field is a tax on capture.
2. **Post-hoc rationale.** About 63% of open-source ADRs were born "accepted" (Finding 2). Rationale written after the outcome is contaminated by hindsight and, at best, a reconstruction.
3. **Rationalization laundering.** LLM-generated "reasons" (precision about 0.27 against the actual rationale) saved as if the person had stated them. The record that was supposed to correct for hindsight then becomes plausible fiction.
4. **Mutable belief records.** Editing last year's belief in place erases the evidence of change. Markus-style drift then happens inside the tool as well as inside the head.
5. **Judging by outcomes ("resulting").** Reviews that ask only "did it work?" teach the wrong lessons from luck.
6. **Capture without scheduled return.** Most journals and logs are write-only. Fatebook's resolution reminder and ADRs' supersession are what close the loop. GTD's weekly review is widely reported as the first habit people drop (anecdotal, unverified).
7. **Goals as rigid trees with metric fixation.** OKR cascades and horizon trees miss multifinality. Over-specified metrics produce the *Goals Gone Wild* side effects. "Zombie goals" that are never closed keep distorting relevance.
8. **Over-planning.** A concrete plan relieves cognitive load but can close the mind to better routes (Masicampo & Baumeister, 2012).
9. **Principles as frozen dogma.** Principles cut off from their origin cases turn into justification engines (Finding 10).
10. **Preference-as-fact memory.** "User prefers concise answers" stored without context. A one-off constructed preference then gets applied forever.
11. **Alarm fatigue from dependency propagation.** If every belief change flags dozens of decisions, the flags will be ignored. TMS-style full propagation suits machines, not people.
12. **Overclaimed evidence in design rationale.** The "premortem gives 30% better accuracy" and "unfinished tasks stick in memory" claims are both wrong as usually stated (Findings 6 and 7). Design choices built on them need different justifications.

## Implications for this project

1. **Adopt a small, question-centered object model with six types.** Uncertainty, contradiction, and evolution are *properties and relations* of these objects, not types of their own. The proposed minimum:

   | Type | Required at capture | Filled later or optional | Key links |
   |---|---|---|---|
   | **Question** | text; status (open / dormant / answered / dissolved) | why it matters; current best answer(s) with confidence; what would change my mind; sub-questions | answered-by → Claim; serves → Goal; raises → Question |
   | **Decision** | what was chosen; ≥1 rejected option; one-line reason; revisit date | criteria; load-bearing assumptions; expectations; feelings; reversibility; premortem; outcome review | decides → Question; assumes → Claim@version; expects → Prediction; serves → Goal; supersedes → Decision |
   | **Prediction** | proposition; probability; resolve-by date; resolution criterion | resolution; AI counter-forecast | about → Claim / Decision |
   | **Goal** | desired state; horizon; status (active / dormant / done / abandoned) | success criteria; if-then plans; kill criteria; review cadence | serves → Goal (DAG, multiple parents) |
   | **Principle** | rule; scope | origin cases; counter-cases; invocation log | generalizes → Decision / Log entry |
   | **Log entry** | timestamp; raw content; source (conversation, reading, thought) | none | cited-by → everything |

   Every object carries: stable id, an append-only version history, **per-field provenance** (stated by person / inferred by AI and confirmed / suggested by AI only), and **revision events** recording old → new, trigger, reason, and date. Claims and beliefs (other tracks) must expose versions and back-links ("load-bearing for"). "Ideas" are candidate answers to questions, or unattached log entries. "Reasoning" is support/oppose links between claims and positions.
   *Falsifiable test:* annotate 50 of the user's real AI conversations. If more than 15% of the items worth keeping can't be expressed without a new type, the model is insufficient.

2. **Organize around open questions, not topics.** Keep a visible list of about 12–30 active questions.
   *Test:* replay a backlog of conversations and notes and measure what fraction of substantive fragments attach to a question or active decision. Below about 40%, question-first organization is insufficient as the main anchor. Above about 60%, it is strong evidence that question anchors beat topical clustering.

3. **Lock fields set before the outcome.** Expectations, reasons, confidence, and assumption versions freeze when a decision is committed. Any change makes a new version.
   *Test:* at each decision review, ask the user what they expected *before* showing the record. Divergence between recall and record is the expected effect (Markus/Fischhoff). Seeing that divergence is the review's payoff. If users rarely diverge, the review feature is less valuable than assumed.

4. **Never store AI-inferred rationale as stated rationale.** Provenance is tracked per field. AI suggestions appear as "Did you also consider…?" and are written as the person's own only after explicit confirmation.
   *Measure:* the endorsement rate of AI-proposed reasons. TOSEM 2025 predicts most generated reasons won't match the actual ones even when they are helpful.

5. **Capture at moments of commitment inside AI conversations, through a draft-and-confirm step.** Phrases like "I'll go with…", "I think…", "I wonder whether…", "my goal is…" trigger an AI-drafted object that the person confirms, edits, or discards in one step.
   *Budget:* median human time of 20 seconds or less per object, with 70% or more of drafts accepted after light edits. If the budget is missed, drop required fields before adding UI. This makes conversation integration a *capture* question for this track, not a later integration detail.

6. **Every committed decision gets a default revisit date plus an optional condition trigger, and reviews happen inside the conversation flow.** The default is something like 90 days, or a date parsed from the decision. A review shows the frozen record, any resolved predictions, and changed assumptions, and asks for a decision-quality grade separate from the outcome.
   *Test:* if fewer than 50% of due reviews are completed within two weeks, the review must be redesigned. For example, the AI raises it opportunistically when the topic recurs, rather than relying on a separate ritual.

7. **Propagate belief changes only through marked load-bearing assumptions (at most 3 per decision), and flag instead of retracting.** When a linked claim's confidence moves past a threshold, or the claim is superseded, the decision gets a "premise changed, review?" flag showing the difference.
   *Test:* at least 50% of flags should be judged worth reviewing. Below that, tighten the threshold or the marking.

8. **Attach at least one resolvable prediction to consequential decisions, and report calibration after 30 or more resolutions.** Optionally record an AI counter-forecast, hidden until resolution.
   *Experiment:* after six months, compare Brier scores for person, AI, and their average on the same personal questions. ForecastBench suggests the average may beat both. This is a concrete, falsifiable payoff to evaluate.

9. **Weight relevance by active goals and open questions for both human and AI retrieval.** Items linked to active goals, open questions, or pending decisions rank above items that are only semantically similar.
   *Test:* A/B on held-out "what do I know about X" queries, plain semantic retrieval against goal/question-weighted retrieval, judged blind by the user.

10. **Represent goals as a DAG with horizon and review cadence, and let goal status drive dormancy.** When a goal is abandoned or achieved, questions and decisions that served *only* that goal go dormant. They are hidden from default relevance but never deleted. Goals carry if-then plans as their main actionable form.

11. **Principles must link at least one origin case to be "active."** Track invocations, meaning decisions that cite the principle. Principles not invoked in 12 months go dormant, and principles with recorded counter-cases surface for revision.

12. **Compile a separate projection for AI consumers.** Humans get narrative records (context, alternatives, feelings, history). AI systems get compact **constraint cards**:
    - the decision in active voice;
    - its scope and status;
    - rejected options marked "do not re-suggest unless…";
    - revisit conditions;
    - the current best answers to open questions, with confidence.

    The Feb 2026 ADR-violation results suggest LLMs use explicit, checkable statements well and implicit ones poorly.
    *Eval:* in scripted sessions, measure how often an assistant re-proposes options the user already rejected, with and without the cards.

13. **Generate "what I changed my mind about" from revision events.** A quarterly view lists beliefs and decisions whose stance changed, with triggers.
    *Test:* the user should find at least 3 genuine, non-trivial changes per quarter. If not, either capture of belief revisions is failing or the window is too short.

14. **Give disconfirming evidence asymmetric priority (Darwin's rule).** When new input contradicts an active belief, a pending decision's assumption, or a goal's premise, it is captured with higher priority and attached to the relevant question as an opposing position, not filed by topic.

## Tensions and open questions

1. **Primary anchor: questions, goals, or chronology?** Questions give the best contradiction handling and routing. Goals give the best relevance. Chronology (the lab-notebook log) is the only lossless layer. The likely answer is a chronological log at the bottom with question and goal anchors above it, but the prototype should test whether users actually navigate by questions.
2. **Which decisions are worth recording?** Bezos's one-way and two-way doors (2015 shareholder letter) suggest recording irreversible ones. But many small reversible choices together reveal values. What threshold keeps capture cheap without losing that signal?
3. **When to formalize.** Draft-and-confirm in the moment risks interrupting thought. Batch formalization afterwards risks hindsight contamination of exactly the fields that matter. One option: lock only the *expectation and confidence* fields in the moment and formalize everything else later.
4. **Who reviews, and will they?** The payoff lives in review, yet review is the habit most often dropped. Can AI-initiated, in-context reviews replace the weekly-review ritual without turning into nagging?
5. **Anchoring vs. outside view.** Showing an AI forecast or AI premortem at capture improves information but may anchor the person and erase their independent judgment. That independent judgment is what calibration tracking needs to measure.
6. **Pinning assumption versions vs. live links.** Decisions need the belief *as it was* for fair review, and the belief *as it is* for flagging. Both links are needed. How costly is that in storage and UI?
7. **Can values be inferred from decision criteria without being wrong or creepy?** Preference construction says stated values are unreliable. Inferred values may be more accurate but less endorsed. Who has the final say on what the system believes the person values?
8. **Seeds without questions.** Many valuable ideas arrive before the person can say what question they answer. Forcing them into questions is premature formalization. Leaving them unattached recreates the fragment pile. One option: an unattached inbox with decay and periodic AI-proposed attachments.
9. **Goodhart inside the system.** If the system tracks goal progress or calibration scores, will the person start optimizing the metric, for example by making easy predictions? Fatebook's "relative Brier" approach and private-by-default help, but this needs testing.
10. **Sensitive content and AI consumers.** Decision journals record feelings and doubts. Which parts of a decision record should *ever* go into the AI projection, and should that be decided per field?
11. **Is the dependency structure worth it?** If users rarely mark load-bearing assumptions, propagation never fires. The prototype should test whether AI-proposed assumption links (confirmed by the user) reach useful precision before building propagation machinery.

## Sources

- Kunz, W. & Rittel, H. (1970). *Issues as Elements of Information Systems.* Working Paper 131, IURD, UC Berkeley. Overview: https://en.wikipedia.org/wiki/Issue-based_information_system
- Conklin, J. & Begeman, M. (1988). gIBIS: A hypertext tool for exploratory policy discussion. *ACM TOIS* 6(4).
- MacLean, A., Young, R., Bellotti, V., Moran, T. (1991). Questions, Options, and Criteria: Elements of design space analysis. *Human–Computer Interaction* 6(3–4).
- Lee, J. & Lai, K. (1991). What's in design rationale? *Human–Computer Interaction* 6(3–4).
- Buckingham Shum, S. & Hammond, N. (1994). Argumentation-based design rationale: what use at what cost? *IJHCS* 40(4), 603–652. https://www.scribd.com/document/65622348/Argumentation-Based-Design-Rationale
- Shipman, F. & McCall, R. (1997). Integrating different perspectives on design rationale: supporting the emergence of design rationale from design communication. *AI EDAM*. https://www.cambridge.org/core/product/F025C0DDD3C116475771226A571DDF02
- Shipman, F. & Marshall, C. (1999). Formality considered harmful. *Computer Supported Cooperative Work* 8(4).
- Shipman, F. & McCall, R. (1999). Incremental formalization with the Hyper-Object Substrate. *ACM TOIS* 17(2).
- Bezos, J. (2015). Amazon shareholder letter (Type 1 / Type 2 decisions); cited from memory.
- Grudin, J. (1988). Why CSCW applications fail. *Proc. CSCW '88*; Grudin, J. (1996). Evaluating opportunities for design capture. In Moran & Carroll (eds.), *Design Rationale: Concepts, Techniques, and Use.*
- Nygard, M. (2011). Documenting Architecture Decisions. https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions
- ThoughtWorks Technology Radar: Lightweight Architecture Decision Records. https://www.thoughtworks.com/radar/techniques/lightweight-architecture-decision-records
- Buchgeher, G. et al. (2023). Using Architecture Decision Records in Open Source Projects: An MSR Study on GitHub. *IEEE Access.* https://research.jku.at/en/publications/using-architecture-decision-records-in-open-source-projects-an-ms/
- de Santana Junior, E. G. et al. (2026). Architecture Decision Records: Adoption, Impact and Developer Engagement in Open Source. ICSA 2026. https://conf.researchr.org/details/icsa-2026/icsa-2026-papers/34/Architecture-Decision-Records-Adoption-Impact-and-Developer-Engagement-in-Open-Sou
- Su, et al. (2026). Evaluating Large Language Models for Detecting Architectural Decision Violations. arXiv:2602.07609. https://arxiv.org/abs/2602.07609
- Zhou, X. et al. (2025). Using LLMs in Generating Design Rationale for Software Architecture Decisions. *ACM TOSEM*. arXiv:2504.20781. https://arxiv.org/abs/2504.20781
- Fischhoff, B. (1975). Hindsight ≠ foresight. *J. Exp. Psych.: Human Perception and Performance* 1(3).
- Markus, G. (1986). Stability and change in political attitudes: Observe, recall, and explain. *Political Behavior.* Summary: https://www.spring.org.uk/?p=5212
- Baron, J. & Hershey, J. (1988). Outcome bias in decision evaluation. *JPSP* 54(4).
- Duke, A. (2018). *Thinking in Bets*; Duke, A. (2022). *Quit.*
- Farnam Street on decision journals and Kahneman's notebook advice (via Mauboussin): https://fs.blog/how-to-improve-the-quality-of-our-decision-making/
- Klein, G. (2007). Performing a project premortem. *HBR* 85(9). Evidence review: Collins, J., "The premortem": https://corporate.jcx.au/premortem ; https://en.wikipedia.org/wiki/Pre-mortem
- Mitchell, D., Russo, J. E., Pennington, N. (1989). Back to the future: Temporal perspective in the explanation of events. *J. Behavioral Decision Making* 2(1).
- Heath, C. & Heath, D. (2013). *Decisive.*
- Tetlock, P. (2005). *Expert Political Judgment*; Tetlock, P. & Gardner, D. (2015). *Superforecasting.* https://en.wikipedia.org/wiki/Philip_E._Tetlock
- Chang, W., Chen, E., Mellers, B., Tetlock, P. (2016). Developing expert political judgment. *Judgment and Decision Making* 11(5). https://ideas.repec.org/a/cup/judgdm/v11y2016i5p509-526_8.html
- Forecasting Research Institute (Jan 2026). LLMs are closing the gap on human superforecasters (ForecastBench). https://forecastingresearch.substack.com/p/llms-are-closing-the-gap-on-human ; ForecastBench paper: https://arxiv.org/abs/2409.19839
- Sage / Adam Binks (2023). Introducing Fatebook. https://www.greaterwrong.com/posts/yS3d46m23wRKDQobt/introducing-fatebook-the-fastest-way-to-make-and-track
- Locke, E. & Latham, G. (2002). Building a practically useful theory of goal setting and task motivation. *American Psychologist* 57(9).
- Gollwitzer, P. & Sheeran, P. (2006). Implementation intentions and goal achievement: A meta-analysis. *Advances in Exp. Social Psych.* 38. https://www.socmot.uni-konstanz.de/publications/implementation-intentions-and-goal-achievement-meta-analysis-effects-and-processes
- Kruglanski, A. et al. (2002). A theory of goal systems. *Advances in Exp. Social Psych.* 34. Overview: https://www.frontiersin.org/articles/10.3389/fpsyg.2018.01052/pdf
- Ordóñez, L., Schweitzer, M., Galinsky, A., Bazerman, M. (2009). Goals gone wild. *Academy of Management Perspectives.* https://repository.upenn.edu/mgmt_papers/325
- Masicampo, E. J. & Baumeister, R. (2011). Consider it done! *JPSP* 101(4). https://supp.apa.org/psycarticles/supplemental/a0024192/a0024192_supp.html ; Masicampo & Baumeister (2012). Committed but closed-minded. *Social Cognition* 30. https://roybaumeister.com/2012/06/16/committed-but-closed-minded-when-making-a-specific-plan-for-a-goal-hinders-success/
- Ghibellini, R. & Meier, B. (2025). Interruption, recall and resumption: a meta-analysis of the Zeigarnik and Ovsiankina effects. *Humanities and Social Sciences Communications* 12. https://ideas.repec.org/a/pal/palcom/v12y2025i1d10.1057_s41599-025-05000-w.html
- Allen, D. GTD Horizons of Focus. https://gettingthingsdone.com/2018/12/the-gtd-horizons-of-focus-for-determining-your-priorities/
- Rota, G.-C. (1997). Ten Lessons I Wish I Had Been Taught. *Notices of the AMS* 44(1). https://www.ams.org/notices/199701/comm-rota.pdf
- Hamming, R. (1986). You and Your Research. https://www.cs.utexas.edu/~dahlin/bookshelf/hamming.html
- Darwin, C. *Autobiography* (golden rule passage). https://stafforini.com/quotes/darwin-1958-autobiography-charles-darwin-q-1163790d/
- Edge Annual Question 2008: What have you changed your mind about? Why? https://www.edge.org/annual-question/what-have-you-changed-your-mind-about-why
- Dalio, R. (2017). *Principles*; Copeland, R. (2023). *The Fund* (characterization unverified).
- Lichtenstein, S. & Slovic, P. (eds.) (2006). *The Construction of Preference.* Cambridge University Press. https://decisionresearch.org/book-collection/the-construction-of-preference
- Doyle, J. (1979). A truth maintenance system. *Artificial Intelligence* 12(3); de Kleer, J. (1986). An assumption-based TMS. *Artificial Intelligence* 28(2).
- Spetzler, C., Winter, H., Meyer, J. (2016). *Decision Quality.* Wiley.
- Anthropic (2025). Claude memory announcement (Team/Enterprise Sept 11, 2025; Pro/Max Oct 23, 2025). https://claude.com/blog/memory
