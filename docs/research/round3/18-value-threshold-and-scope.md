# 18. Value threshold and scope: what is worth remembering, and where

Round 3 research note. Revised 2026-10-14; replaces the draft of 2026-10-10. Read with `docs/GOAL.md` (answers of 2026-10-10 in §1 and §2).
Question: what makes a piece of personal knowledge worth remembering, how should a memory system decide, and when does project knowledge belong in personal memory?
Strength: **A** = primary source read at the URL. **B** = primary, but only an abstract or search summary read, or a preprint. **C** = practitioner or secondary. No probe content or personal data appears here.

## Answer

"Keep it?" is two questions, and the probe asked them as one. **Value**: would remembering this change a future decision or understanding by more than it costs? **Scope**: where would that change happen, in one project or across the user's work? Research gives value a clear shape: a memory is worth **need × gain**, how likely it is to be needed times how much it would change a choice (Mattar & Daw). If nothing would change, it is worth nothing. Need shows in recurrence, recency and the time span of recurrence (Anderson & Schooler), and in links to the user's plans (memory serves the future: Klein et al.). What a generic model or a search can supply adds little (Mallen et al.); what took long reasoning is costly to lose. Products barely score importance: they use LLM judgement, size pressure and hard project boundaries, store trivia, preferences and inferences about the person, leak across contexts, and never promote project learning to personal knowledge. **Recommendation:** two gates (whose; is it knowledge), a merge check, a scope test that strips project names, then a profile of **need, gain and cost to rebuild**, each rated low, medium or high with a reason. A simple rule combines them. Its bar comes from comparison with the user's own nearby items and from their corrections, not from a fixed score. Uncertain items wait as *pending*. Project knowledge sits in a scoped layer outside the personal map. It is promoted when stated generally, when it recurs in a second context, or when it conflicts with knowledge from another.

## 1. What the probe shows (aggregate only)

- About half the items were worth keeping. Being the user's own idea was not enough: some were passing preferences.
- Many items were project-specific. "Don't keep" meant "not for personal memory", not "forget it". Value and scope were mixed in one label.
- 14 of 50 items were too literal: a restatement problem (note 17), which the scope test below also fixes.
- The chats were nearly all about one project. They can test value inside a project, not promotion, which needs two contexts.

## 2. Evidence table

| # | Source | Str. | Finding | Use for Northstar |
|---|---|---|---|---|
| 1 | Anderson & Schooler 1991; Anderson et al. 2023; Press et al. 2014 | B | Need follows frequency, recency and spacing in real environments; memory mirrors it. **Range**, the span an item recurs over, is a key predictor. As a cache, the model alone did about as well as the worst algorithms | Need from recurrence and range, plus links to live goals |
| 2 | Mattar & Daw 2018 | A | A memory's priority = **gain × need**. Gain is how much better the next choice gets, zero if it would not change. Need is expected future use | The shape of the value rule |
| 3 | Howard 1966; Richards & Frankland 2017 | B | Information is worth what it changes in a decision. Memory exists to improve decisions; forgetting outdated detail helps generalisation | Gain = decision impact. Keep the gist; let states fade |
| 4 | Klein, Robertson, Delton & Lax 2011 | A | Memory is prospective. Planning-oriented encoding recalls better, most when self-referential | Links to the user's plans raise need |
| 5 | Gick & Holyoak 1983 | B | One example rarely transfers, even with the principle stated. Comparing two gives a schema that does | Promote on a second context |
| 6 | Mallen et al. 2023 | A | Models already handle popular facts; retrieval helps mainly on long-tail ones. Retrieving only when needed is better and cheaper | Distinctiveness: what a generic model says adds little |
| 7 | Sparrow, Liu & Wegner 2011 | B, contested | People expecting later access recall content less and where to find it more. One experiment failed replication (Camerer et al. 2018); the memory ones were not retested | Easy to look up: keep a pointer, not an item |
| 8 | Nielsen 2018 (citing Gwern) | C | Keep a fact if it seems worth about 10 minutes of future time (Gwern: 5). Works far better "in service to some personal creative project" | Cost to rebuild × recurrence |
| 9 | Matuschak; Forte | C | Notes by concept accumulate across projects; notes by project do not. Test new ideas against standing problems. Forte's capture criteria are called too vague | Personal layer by concept; use standing questions |
| 10 | Park et al. 2023, Generative Agents | A | An LLM rates "poignancy" 1–10, chores to life events; retrieval sums recency, importance and relevance equally; reflection at summed importance 150. Failures: missed retrieval, embellishment | A generic absolute scale does not fit knowledge |
| 11 | MemGPT 2023; Letta | A | No importance score. At a set share of context (e.g. 70%) a "memory pressure" warning tells the LLM to save what matters. Blocks have size limits | Capacity pressure as a dynamic bar |
| 12 | Mem0 prompt; Chhikara et al. 2025 | A | Default categories are mostly preferences and personal details, favourite movies included. Each new fact is compared with its 10 nearest: add, update, delete or no-op | Preference-first capture fails; the comparison is sound |
| 13 | Xiong et al. 2025 | B (preprint) | Agents copy retrieved experiences, errors included. Strict selective addition beat add-all on four agents by 15–26 points with 14–58% less memory | A strict bar helps the AI side too |
| 14 | OpenAI memory help pages | C (via search) | Oct 2025: automatic management ends "memory full"; less important memories move to the background. Jun 2026: a new system keeps "the details it determines are most important" | Ranking with no published value model |
| 15 | Algorithmic Self-Portrait, WWW '26 | A | 2,050 real ChatGPT memories, 80 users: 96% saved unasked; 52% inferences about the person; 28% personal data | Automatic capture stores the person, not their knowledge |
| 16 | Willison 2025 | C | Memory put an unrequested location into an image and built a "dossier". He wanted per-project memory | Leaks across contexts |
| 17 | Claude memory help | A | Saved as topics: role, projects, preferences, ongoing work. "Each project has its own memory", plus non-project memory, "not memory from other projects" | Personal flows down; nothing flows up |
| 18 | Claude Code memory docs | A | Managed, user, project, local scopes; auto memory per repository. Saves what "would be useful in a future conversation", skips what it "can derive from the codebase". `/doctor` keeps rationale and "conventions that differ from tool defaults" | Future use, cost to rebuild and distinctiveness are product rules already |
| 19 | Copilot; Cursor; Windsurf docs | A | Copilot: repository facts (citations checked) vs user preferences; unused for 28 days, deleted. Cursor: project, user, team rules. Windsurf: workspace memories; rules on request | Scope set at write time; promotion manual |
| 20 | Aberdeen et al. 2010, Gmail Priority Inbox | A | Global model plus a per-user model of how the user differs, and a **per-user threshold**. Corrections weigh more; consistent marks move the threshold at once. Errors 45% → 38% → 31%. Much opened mail is "interesting", not "important" | A per-user bar. Opening is not valuing |
| 21 | Liu et al. 2024, PairS | A | LLM judges differ from human standards. Pairwise comparison beats direct scoring | Compare candidates with nearby items |

Memory-induced echo at reply time is covered in note 19.

## 3. The value model

**The rule in one line.** Keep an item when it is likely to be needed and would change something when needed (need × gain), unless it is cheap to get back. Keep a high-gain item that would be costly to rebuild even when need is unclear. This follows rows 2, 6–8 and 18.

| Dimension | Question | How judged |
|---|---|---|
| **Need** | How likely is a situation where this is needed, and over how long? | *Computed* from the store: distinct sessions, range in time, distinct contexts. *Judged*: links to standing goals, questions and plans (rows 4, 9). *Durability* is part of need: a principle stays needed, a state ("doing X this week") does not |
| **Gain** | Would it change what the user or an AI does or concludes? | *Judged*: is it a rule, approach, position, conclusion or tension? Does it carry a why, a scope or an exception? *Tested* for distinctiveness: ask a no-memory model the item's question; if its answer already says it, gain is low. The user's own reasons, scope and exceptions count as distinct even when the principle is common |
| **Cost to rebuild** | How hard would it be to get back? | *Computed*: turns, research and reversals behind it. *Judged*: can the repo, docs or a search supply it? If so, keep a pointer, not an item (rows 7, 18) |
| **Reach** (decides scope, not value) | Is it still useful with project names removed? | The strip test (§5, step 4). Confirmed by a second context (row 5) |

**Combining.** Each dimension gets low, medium or high with a one-line reason that cites evidence.
- *Not kept* (archive only): gain is low, or need and cost to rebuild are both low.
- *Keep*: gain is at least medium, and need or cost to rebuild is high.
- *Pending*: everything else. It waits in the archive with its ratings until evidence moves it.

The levels are not absolute: each is judged against the user's nearest kept and dropped items (§6). The rule fixes the *shape* of the decision; the *bar* comes from the user's corpus and corrections.

**Why not a weighted score.** Fixed weights and 1–10 scales are the hard-coded rules the user rejected (GOAL §2). LLM absolute scores drift from human standards (row 21), generic anchors rate life events, not ideas (row 10), and in the probe an AI judge disagreed with the user's blind picks.

**How the probe's hard cases fall out.**

| Case | Need | Gain | Cost | Result |
|---|---|---|---|---|
| Passing preference: no why, said once, nothing depends on it | low | low | low | Not kept |
| Recurring instruction on how the AI should reply | high | style only | low | Fails the kind gate (§5): an AI working-style profile or vendor memory |
| Project design decision with reasons | high in project | high | high | Project layer |
| Principle reached in a project, still sound without its names | rising | high | high | Personal (pending if no general signal yet) |
| Generic fact that came up in passing | — | low (generic) | low | Not kept, or attached to an item as support |

## 4. How products scope memory

| Product | Scopes | Personal into project? | Project into personal? |
|---|---|---|---|
| Claude chat | Account memory; one memory per project | Yes, unless switched off per project | Never |
| ChatGPT | Saved memories and chat history; projects; project-only memory (Aug 2025) | Yes by default; no with project-only | Never |
| Claude Code | Managed, user, project, local files; auto memory per repository | User files load in every project | Manual |
| Cursor; Windsurf | User, project, team rules; workspace memories | User or global rules load everywhere | Manual, on request |
| Copilot | Repository facts; user preferences | Preferences apply across repositories | Never; split at write time |

Everywhere, personal context flows down into projects and nothing flows up on its own. Promotion is the gap, and it is the job GOAL §1 describes: a lesson from real development still at hand when preparing for an interview.

## 5. Layer decision procedure

**Three layers.**
- *Personal*: the Northstar map; may enter any chat when very strongly linked (GOAL §2).
- *Project*: one project's scope; never in the personal map; injected only in that project.
- *Not kept*: only in the private, searchable raw archive.

**Steps for each candidate**, run in batches in the maintainer's background pass, never in the live chat.

1. **Gate: whose.** Is it the user's own statement, or AI teaching the user visibly adopted (stated, followed up, agreed with or built on)? If not: not kept.
2. **Gate: kind.** Is it knowledge (a principle, approach, position, conclusion, open question or tension), not a state, a generic fact or an instruction on how the AI should reply? A preference with a why is an approach and passes; a passing one fails on value in step 5. A generic fact can only attach to an item as support.
3. **Merge check.** Compare it with its nearest items in both layers (row 12).
   - Same idea: it becomes new evidence for that item (another session or context), raising need and perhaps triggering promotion.
   - Refines it: update the item, keeping history.
   - Conflicts with it: in the same context the newer view supersedes; across contexts both stand as a tension, each with its scope.
4. **Scope: the strip test.** The AI restates the item without project names, files or components. Would it still change a decision elsewhere?
   - Yes, and the user gave general reasons or spoke generally: **personal**, with the project recorded as where it was learned.
   - Yes, but no general signal: **personal, pending** until a second context appears.
   - No: **project**.

   The restatement becomes the item's wording; the verbatim words stay one click away as the source.
5. **Value within the layer.** Apply the rule in §3: keep, pending or not kept.
6. **Over time.**
   - *Project to personal* when (a) the user states the item as general; (b) it recurs in a second, distinct context (row 5); or (c) it conflicts with or qualifies knowledge from another context. Such a conflict is personal knowledge in itself (GOAL §2). On promotion, the AI writes the general version and links each context.
   - *Pending to kept* when the item recurs, is used, or is built on.
   - *Fading*: an item unused over a long range loses prominence but is never deleted. A quiet project's layer is archived; promoted items stay personal.

Note 16's tests map onto this: reasons and "not generic" into gain, live questions and recurrence into need, the strip test into reach.

## 6. Making the threshold dynamic

1. **Anchor to the user's own items.** The judge sees the user's nearest kept and dropped items, with reasons, not generic anchors.
2. **Compare, don't cut off.** An item joins only if nothing nearby already covers it as well or better. The bar rises as the corpus grows.
3. **A reading budget per area.** When an area outgrows its summary, weaker items fold under stronger ones: the capacity pressure of row 11. The budget comes from the human-view design (note 15), not a count set here.
4. **Defer, don't guess.** Pending items wait for recurrence, range, use or a second context. The user does nothing.
5. **Learn from corrections, never require them.** A keep, drop or "project only" mark is stored as an example and outweighs implicit signals. Marks pointing the same way move that area's bar at once (row 20). Implicit signals, strongest first: the user re-raises the idea; an item is pulled back from the archive (a missed keep); long non-use (weak negative); an item is opened (weak: interesting is not important).
6. **A stricter bar when injecting.** A chat gets an item only when it would change *this* answer beyond what a generic answer gives (rows 6, 13; note 19).

## 7. What this means for Northstar

1. Store on each item a `scope` (personal, project:*name*, or pending), a status (pending, kept, fading) and a value profile: three ratings, one-line reasons and evidence links. No single score.
2. Add maintainer jobs: gates, merge check, strip test (which writes the restatement), no-memory distinctiveness check, pairwise placement, promotion check. Run them in batches, only on gate-passers, so token cost stays bounded.
3. Log archive retrievals as the false-negative signal, and sample "not kept" items in audits.
4. Benchmark: label two axes per item, "worth remembering?" and "applies where: this project, beyond it, unsure?", on chats from at least two contexts. Report agreement per axis; measure the judge against the user before trusting it.
5. Replace the current design's fixed counts and windows with the §6 rules where they apply.

**Where project knowledge lives: a choice for the user.** The user leans towards keeping it out of Northstar. It stays out of the personal map and personal injection either way. Whether the store holds a project layer at all is a HOW choice:

| Option | For | Against |
|---|---|---|
| A. Leave it to each product's project memory | Simplest; matches the user's lean | Breaks across products; promotion must search the raw archive; cross-context conflicts are hard to spot |
| **B. A thin project layer in Northstar, written out to CLAUDE.md, AGENTS.md and the like** (recommended) | One store across products; promotion and conflict checks have their evidence | More to build; needs a strict scope gate |

**Risks.** A small corpus calibrates the bar poorly at first; pending items and the archive limit the damage. The LLM judge can disagree with the user, as the probe showed for replies. Promotion could carry project trivia into the map; the strip test and second-context rule guard against it. The distinctiveness check depends on one model's knowledge, so a model change can shift it.

**Questions for the user.**
1. Project knowledge: option A or B?
2. A principle from one real project: personal at once if the user gave reasons (recommended), or only after a second context?
3. Recurring working preferences: vendor memory and product instructions (recommended), or a small Northstar working-style profile?

## Sources (all checked 2026-10-14)

- Anderson & Schooler (1991). https://www.psychologicalscience.org/journals/psychological-science/j.1467-9280.1991.tb00174.x/ (abstract)
- Anderson et al. (2023). https://philpapers.org/rec/ANDTEB (abstract via search)
- Press, Pacer, Griffiths & Christian (2014). https://collaborate.princeton.edu/en/publications/caching-algorithms-and-rational-models-of-memory/ (abstract)
- Mattar & Daw (2018). https://pmc.ncbi.nlm.nih.gov/articles/PMC6203620
- Howard (1966). https://synapsesocial.com/papers/W2001863269 (abstract via search)
- Richards & Frankland (2017). https://doi.org/10.1016/j.neuron.2017.04.037 (abstract via search)
- Klein et al. (2011). https://pmc.ncbi.nlm.nih.gov/articles/PMC3302925 (summarises the 2010 study)
- Gick & Holyoak (1983). https://deepblue.lib.umich.edu/items/196ea13e-fb69-4a74-a6f9-864c81aed465 (abstract)
- Mallen et al. (2023). https://arxiv.org/abs/2212.10511
- Sparrow et al. (2011); replication, Camerer et al. (2018). https://authors.library.caltech.edu/91063/ (via search)
- Nielsen (2018). http://augmentingcognition.com/ltm.html
- Matuschak. https://notes.andymatuschak.org/Evergreen_notes_should_be_concept-oriented
- Forte. https://fortelabs.com/blog/12-favorite-problems-how-to-spark-genius-with-the-power-of-open-questions/ ; critique (weak): https://curtismchale.ca/2022/07/30/building-a-second-brain-gives-you-permission-to-fall-into-collectors-fallacy
- Park et al. (2023). https://arxiv.org/html/2304.03442
- MemGPT (2023). https://arxiv.org/html/2310.08560 ; Letta. https://docs.letta.com/guides/agents/memory-blocks
- Mem0 prompt. https://github.com/mem0ai/mem0/blob/main/mem0/configs/prompts.py ; Chhikara et al. (2025). https://arxiv.org/html/2504.19413
- Xiong et al. (2025, preprint). https://arxiv.org/html/2505.16067v2
- OpenAI Memory FAQ, release notes (blocked; via search summaries). https://help.openai.com/en/articles/8590148 ; https://help.openai.com/en/articles/6825453-chatgpt-release-notes
- The Algorithmic Self-Portrait (2026). https://arxiv.org/html/2602.01450v1
- Willison. https://simonwillison.net/2025/May/21/chatgpt-new-memory/ ; https://simonwillison.net/2025/Aug/22/project-memory/
- Claude memory. https://support.claude.com/en/articles/11817273-using-claude-s-chat-search-and-memory-to-build-on-previous-context
- Claude Code memory. https://code.claude.com/docs/en/memory
- GitHub Copilot memory. https://docs.github.com/en/copilot/concepts/agents/copilot-memory
- Cursor. https://cursor.com/docs/context/rules ; Windsurf (now Devin docs). https://docs.devin.ai/desktop/cascade/memories
- Aberdeen et al. (2010). https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/36955.pdf
- Liu et al. (2024). https://arxiv.org/abs/2403.16950
