# Round 3 synthesis: decisions to test on real data

Written 2026-10-14. Inputs: [15] formats, [16] practice and tools, [17] processing jobs, [18] value threshold and scope, [19] memory injection (all in this folder). [`docs/GOAL.md`](../../GOAL.md) overrides this note, and its 2026-10-10 answers come first. Nothing here changes the WHAT. Every decision below is a **hypothesis to test on the user's real chats** before the design is revised. No probe content or personal data appears here. Examples are invented.

## 1. The answer in brief

1. **The view is short text, not a diagram.** Each item is one clean sentence in the user's voice, with *why*, *where it applies and where not*, and *how they got there*, answer first. Origin (mine or adopted from an AI) and status (settled, forming, replaced) are shown in words. No IDs, no global graph; sources one click away. Four candidate layouts (§2) go to the user's blind picks.
2. **About a dozen small jobs make the view, not one summary.** The model writes short sentences. Code builds the structure from typed fields and links. A different model family checks every sentence against its source. Any job may answer "unclear" (§3).
3. **"Keep it?" is two questions.** *Value*: would it change a future decision by more than it costs (need × gain, unless cheap to rebuild)? *Scope*: where would it change one, in one project or anywhere? There are three layers: **personal**, **project** and **not kept**. Uncertain items wait as *pending*. The bar comes from comparison with the user's own nearby items, not from a fixed score (§4).
4. **Memory goes to the AI as background, not as content.** Records are chosen by their effect on this answer, and an empty pack is allowed. Each record carries its scope. The framing tells the model to answer in full, spend the reply on what is new, and test past views instead of echoing them (§5).
5. **The user's blind pairwise picks are the ground truth** for formats and for replies. An AI judge counts only once it has been calibrated on those picks (§6).

## 2. The human view: format

**What the evidence settles.**

| Finding | Evidence | Strength |
|---|---|---|
| Familiar material needs cues (gist, reason, context), not explanation. Rough wording fades while meaning stays | Expertise reversal; Sachs 1967; headings stop helping on familiar topics [15] | Strong theory, moderate data |
| Maps beat outlines only slightly, and large maps overload readers | Concept maps vs outlines g = 0.28; near zero on details for readers who knew the topic [15] | Strong, but on new material |
| Comparing contexts, with the shared principle and the deciding condition stated, is what connects dots | Case comparison d = 0.50 [15]; one example rarely transfers [18] | Strong |
| Stories carry the why and are remembered | Narrative vs exposition g = 0.55, memory 0.72 (Mar et al. 2021) | Strong for the genre |
| Readers skim and almost never open sources, so the top layer must stand alone | About 20% of words read; 1% clicked a link in an AI summary [16] | Strong |
| AI-written summaries anchor and can shift a person's view | Jakesch 2023, N = 1,506 [16][17] | Strong |
| Global graphs, IDs and bare link lists go unused | Practice reports [16]; the rejected prototype | Weak, but consistent |

**Four candidates to test.** Each is a real alternative for the top page. All share the depth layer and the rules below.

| | Format | Organized by | Where the logic lives | Best evidence | Main risk |
|---|---|---|---|---|---|
| F1 | **Question-led answer cards** | The user's live questions | Each answer's "because" and scope lines | Pyramid order, claim headlines, signalling | Questions read like a quiz; reasons repeat the claim |
| F2 | **Theme briefs** | Themes in the user's terms | A 2-4 sentence brief joining items with because, but, so | Maps of content, decision records [16] | Free prose invents links (weakest measured job, 26 F1 [17]) |
| F3 | **Principles with cases** | Principles that recur across contexts | A small table: context, what holds, what differs, deciding condition | Case comparison, d = 0.50 | Overgeneralization (26-73% in summaries [17]); sparse on one-project data |
| F4 | **Situation playbook** | Situations the user will be in again | "When … do …, because …; not when …" rules | Lessons must say where they apply [16]; memory is for future use [18] | Situations split hairs; a rule loses its why |

**Rules for every candidate.**
- **No pasted words on the top layer.** A restatement that fails its check twice stays off the top layer and waits as pending. Note [17] would show the trimmed quote instead; the user's direction rules that out. Quotes live in the source layer, two clicks down.
- **The depth layer, on click:** the statement; why (1-3 reasons, each from a source); applies when / not when ("not yet clear" is allowed); how I got here (3-6 dated steps, with replaced positions shown); up to 3 typed connections; and the sources.
- **A length budget** set per screen by the reading test (T3), never a fixed count in code.
- **One-step correction** ("not what I think") with undo. Opening the view is never required.

## 3. The processing jobs

These are ordered, and each has its own check. "Code" means deterministic and replayable.

| # | Job | Made by | Check; on failure |
|---|---|---|---|
| 1 | Capture and segment: turns, speaker, time, exact spans | Code | Every quote is an exact substring |
| 2 | Find the moves over the episode: states, adopts, rejects with a reason, builds on, revises, only asks | LLM; blind re-label by a second family | Labels disagree: "unclear". A bare question records nothing |
| 3 | Value and scope gate (§4) | Code signals; LLM judges | Uncertain: pending |
| 4 | Merge check against the nearest items | Code candidates; LLM judges pairs | Same idea: new evidence. Refines: update with history. Conflicts: supersede in the same context, a tension across contexts |
| 5 | Restate as one standalone sentence, same strength and hedges | LLM | Two-way entailment by another family. Lints: no new names or numbers, no IDs, no copied run over about 8 words. Fails twice: off the top layer |
| 6 | Ground the why | LLM picks; code links | Each reason cites a span. None: "still forming" |
| 7 | Scope: applies when, not when | LLM | Each cites a span or says "inferred". Never wider than the source |
| 8 | Key: the question it answers (F1-F3) or the situation it serves (F4) | LLM | The item must answer it; no project names in a personal key |
| 9 | Link: supports, limits, conflicts, same question elsewhere | Code candidates; LLM types | One-line reason citing both sides. Conflicts and cross-context links need two families to agree, otherwise hidden |
| 10 | Abstract to a principle (F3) | LLM, only from 2+ independent contexts | Each case must fit, plus a counter-case search. Labelled "pattern Northstar sees" until the user states it |
| 11 | Track change of view | Code timeline; LLM labels it narrowed, widened, reversed or dropped | Old and new spans with dates; a sweep for missed updates |
| 12 | Compose the page | Code templates from fields and links | Every connective comes from a typed link. Budget; no IDs |
| 13 | Verify the render | Code, plus a sampled audit by another family | Each line traces to fields and sources |

Why: models are good at jobs close to the text (restate, merge), fair at scope and relations, and poor at conflicts, far analogies, unstated logic and changes of view [17]. Risky jobs need two-family agreement or stay hidden.

## 4. Value model and layers

**The rule.** Keep an item when it is likely to be needed and would change something when needed, unless it is cheap to get back. Also keep a high-gain item that is costly to rebuild. This follows Mattar & Daw (2018): an access with no effect on behaviour has zero utility, however often it is needed. Each of **need**, **gain** and **cost to rebuild** is rated low, medium or high, with a one-line reason. Not kept: gain low, or need and cost both low. Kept: gain at least medium, and need or cost high. Anything else is pending. The levels are judged against the user's nearest kept and dropped items, and the user's corrections move the bar. There is no weighted score.

| Layer | What goes there | Shown | Given to an AI |
|---|---|---|---|
| **Personal** | Passes both gates; still changes a decision with project names removed (the strip test) | The personal view | Any chat, only when very strongly linked (§5) |
| **Project** | Sound and valuable, but only meaningful inside one project | Not in the personal view | Only inside that project |
| **Not kept** | Not the user's (no uptake), not knowledge (a state, a generic fact, an instruction on how to reply), or below the bar | Nowhere | Never. Stays in the private raw archive |

**Promotion** from project to personal: the user states the idea generally, it recurs in a second context, or it conflicts with knowledge from another context. The item-by-item scorer rubric is in the run output.

**Probe fit.** The probe chats cover one project. They test value and the project layer, but not promotion, F3 or F4, which need a second context.

## 5. Giving memory to the AI

**Why memory replies lost the user's picks.** A pack of the user's conclusions reads as content to deliver. Models over-attend their context, reuse its words, and agree with views they can infer. Agreement sycophancy rose with real user context, by up to +45% with memory profiles (Jain et al., CHI 2026). Memory agents scored 26-61% below a no-memory agent on over-personalization (OP-Bench). Filtering first helped, but no setup reached the no-memory score (OP-Bench, preprint, re-checked). Judges reward visible mentions that people do not value: humans rated 54.6% of personalized replies no better than generic ones, and the best judge reached about 0.37 Spearman with humans (Zhang, Liu & August 2026).

**Decisions to test.**
1. **Select by effect on this answer.** A record goes in only if a good answer without it would be wrong or worse, and an empty pack is allowed. Selective injection beat always-on injection by 8.3 and 6.8 pass@1 points (Wu et al. 2026, preprint). This makes "very strongly linked" in GOAL §2 operational. It also replaces the design's floored knowledge slot.
2. **Push decisions and ruled-out options; deliver what the user already knows only when it passes the gate.** On tool surfaces, list the rest by title for fetching.
3. **Each record is one restated sentence with its scope.** Nothing verbatim is there to echo, and no IDs.
4. **Background framing:** answer first, then fit; spend the reply on what is new; act as an adviser; add the delta without invented disagreement. Prompt rules only partly work (BenchPreS, EMNLP 2026), so selection carries most of the load and each rule gets ablated.

The exact framing (run output) refines [19] §4: it covers earlier turns of the same chat, adds a "bears on" field, drops IDs, and keeps Northstar unnamed.

## 6. What to test on the user's real data

Pass bars are set in advance and revised after round one. Sessions are one-off and optional (GOAL §2). No task tests the user's memory: the view stays open.

| Test | Data | Measure | Pass means |
|---|---|---|---|
| **T1 Jobs** | About 30 items per job from the probe chats | Restatements the user confirms "what I hold"; too-literal share; copied runs on the top layer; uncited scope lines | At least 90% confirmed (probe credit was 90-96%); too-literal items fall from 14 in 50 to near zero; no copied runs |
| **T2 Value rubric** | The 50 probe items, relabelled on two axes (worth remembering? applies: this project, beyond it, unsure); 10 repeats later; 30+ items from a second context | Scorer vs user agreement per axis (raw and κ); precision of the personal layer; archive items the user later wants back | Agreement near the user's own repeat consistency; few "not worth it" items placed personal with high confidence |
| **T3 Formats** | The same personal items (2+ contexts) rendered as F1-F4 | Blind pairwise picks on "helps me follow my logic" (6 pairs plus 2 order-flipped repeats); an open-book task ("you are about to …: what do you hold, why, where does it apply?") with time taken and yes / partly / no; lines flagged as wrong | A format wins most of its pairs, is fastest on the task, and has no more flags. Without a clear winner, combine (e.g. F1 by default, F3 where patterns exist) and retest |
| **T4 Injection** | 20-30 scenarios from the user's real topics | Blind picks across: no memory, general profile, current pack, new framing pushed, new framing tool-first, single-rule ablations. Judge criteria C1-C6 from [19] §5 | New framing at least matches no memory on single replies; beats it on continuity tasks (fewer re-explanations, no broken decisions); restatement share well below the current pack's. The judge must prefer the plain reply when "As you concluded …" padding is added (mention-swap test) before it is trusted at scale |

## 7. Questions for the user (HOW choices)

1. **Project knowledge.** Keep a thin project layer in Northstar and write it out to CLAUDE.md, AGENTS.md and similar files (recommended in [18]), or leave it to each product's project memory? Either way it stays out of the personal view.
2. **Personal at once?** Should a principle reached in one real project become personal at once when the user gave general reasons (recommended), or only after a second context?
3. **Working-style preferences** (how replies should look): vendor memory and product instructions (recommended), or a small Northstar style profile kept outside the knowledge view?
4. **Visibility.** When memory shapes a reply silently, should the chat say so in one closing line, or is "used in this chat" in the view enough?
5. **Data.** For T2-T4, can the user share a few personal-account chats on a topic other than Northstar?

## Sources

**Re-checked by me on 2026-10-14 at the URL:**
- Jain et al., *Interaction Context Often Increases Sycophancy in LLMs*, CHI 2026: https://arxiv.org/abs/2509.12517
- Zhang, Liu & August, *Re-Centering Humans in LLM Personalization*, 2026 (preprint): https://arxiv.org/html/2606.06614v1
- Wu et al., *Remember When It Matters*, 2026 (preprint): https://arxiv.org/abs/2607.08716
- OP-Bench, 2026, arXiv preprint (no venue on the page; [19] says EMNLP 2026). Filtering gains reach about 43-50% over memory baselines, but every setup stays below the no-memory score: https://arxiv.org/html/2601.13722v2
- BenchPreS, EMNLP 2026: https://arxiv.org/abs/2603.16557
- Peters & Chin-Yee, *R. Soc. Open Sci.* 2025, overgeneralization in LLM summaries: https://pmc.ncbi.nlm.nih.gov/articles/PMC12042776/
- Metropolitansky & Larson, Claimify, ACL 2025 (abstract only; the 99% figure is from [17]'s table reading): https://arxiv.org/abs/2502.10855
- Mar et al., *Psychonomic Bull. Rev.* 2021, narrative vs exposition: https://pmc.ncbi.nlm.nih.gov/articles/PMC8219577/
- Mattar & Daw, *Nature Neuroscience* 2018, gain × need: https://pmc.ncbi.nlm.nih.gov/articles/PMC6203620

**Not re-checked (secondary here):** Alfieri et al. 2013, d = 0.50 (https://doi.org/10.1080/00461520.2013.775712; 403 on 2026-10-14). Every other figure is taken from its note [15]-[19], with that note's source and label.
