# 17. Processing jobs: from rough chat statements to clear, connected knowledge

Round 3 research note. Written 2026-10-14; this rerun replaces the 2026-10-10 draft. Read with `docs/GOAL.md` (the 2026-10-10 answers in §1 and §2 take precedence). Companion notes: `15` (formats), `18` (value threshold and scope), `19` (memory injection).
Question: which processing jobs turn raw chat statements into clear, connected knowledge a person can read, and how reliable are current LLMs at each?

## Answer

Turning chats into readable knowledge takes about a dozen separate jobs, not one "summarize" step, and LLMs are uneven across them. They are **good at jobs that stay close to the text**. They can restate a rough statement as one clear, standalone sentence (99% entailed by the source when the method may decline unclear cases), and they can spot duplicates (about 90 F1 zero-shot). They are **fair at jobs that judge relations or conditions**: support versus attack (75 F1, binary only), argument structure in dialogue (48–67 F1), and the conditions an answer depends on (condition F1 47–61, while answer accuracy is 76%). They are **poor at jobs that go beyond the text**. These include finding conflicts between opinions, seeing the same question in a context that looks different (below chance zero-shot), and recovering unstated "because" and "so" links (26 F1). They also include turning cases into principles (26–73% overgeneralized), summarizing summaries, and noticing that a view changed (memory systems miss 37–94% of updates). Automatic checkers catch only part of this (best ≈77 on a standard benchmark). So Northstar should run each job as a small step with its own check. Every job may decline, and a different model family does the checking. **Code, not the model, should build the structure**: segments, timelines, candidate pairs and each page's reading order, filled from typed links. The model writes only short sentences, and each one is checked against its source. **The user's own words are the evidence under every item, stance, condition, conflict, principle and change**, one click away. They are also the fallback when a restatement fails its check. They are not what the page shows by default.

## The probe's failures map onto jobs

| Probe finding (aggregate only) | Job that addresses it |
|---|---|
| 14 of 50 items were too literal: rough phrasing pasted as-is | Restate (job 3), with a meaning check |
| About half the items were not worth keeping; many were project-only | Value and scope gate (job 2; method in note `18`) |
| The knowledge map with IDs did not show the logic | Question key, links and page composition (jobs 6, 8, 11; formats in note `15`) |
| Credit was right 90–96% of the time; almost half the held items were adopted AI ideas | Find the moves (job 1), keeping both the AI's span and the user's adoption span |
| Replies given memory echoed the user's views back | Inject the restated principle with its scope as background (note `19`) |

## Evidence table

Strength: **A** = peer-reviewed primary source. **B** = preprint, or a setting far from ours. **C** = vendor or secondary. The source list says whether tables or only the abstract were read. All checked 2026-10-14.

| Job | Reliability now | Evidence and numbers | Main failure | Str. |
|---|---|---|---|---|
| Find claims | Good with a strong or tuned model | Claim detection F1: 51.5 zero-shot vs 85.2 fine-tuned (Llama-3.1-8B, AMELIA) | Implicit, context-bound claims. Stance in conversation is "underexplored" (2025 survey) | B |
| Support or attack | Fair | Binary macro F1: Llama-2-70B 75 vs RoBERTa 68 (Gorur 2024). With "no relation" as a third class: 28.3 zero-shot vs 88.3 fine-tuned (AMELIA) | Deciding that two items are *not* related | B |
| Argument structure in dialogue | Fair to poor | Best DialAM-2024 system: 67.05 F1 on whole maps, 48.25 on the related parts only | Chats are harder than essays | A |
| Restate so it stands alone | Good | Claimify: 99.0% of claims entailed; coverage F1 83.7 vs 56–63 for other methods; 2.4–5.4% of sentences declined as "cannot disambiguate". Without its selection stage, coverage fell to 54.4. Atomic facts lose context; "molecular" facts add just enough (Gunjal & Durrett 2024) | Lost context, or a claim forced from an unclear sentence | A |
| Does a clear rewrite help readers? | Yes, modestly | Simplified texts, 4,563 readers: +4 points comprehension, also with the text hidden (Google, 2025) | Vendor study | C |
| Check that meaning is kept | Fair | LLM-AggreFact: best ≈77 (Bespoke-MiniCheck-7B 77.4, Claude 3.5 Sonnet 77.2, GPT-4o 75.9). On dialogue, GPT-4 as judge is worse than specialised metrics (TofuEval). "Same meaning" can be tested as entailment both ways (semantic entropy, Nature 2024) | A check filters errors; it does not prove a rewrite right | A |
| Rewrites add content | Ongoing | Single short documents: 1.8–24.2% of summaries flagged; most frontier models 3–15% (Vectara, updated 2026-09-22) | Some share of rewrites always drifts | C |
| Rewrites shift voice or view | Real risk | A feedback-tuned model made essays more alike (Padmakumar & He 2024). An opinionated assistant shifted what 1,506 people wrote and later said they believed (Jakesch 2023) | The restatement drifts toward generic wording or the model's view | A |
| Abstract to a principle | Poor alone | LLMs propose good rules but apply them badly (Qiu 2024). They often get cases right without a correct rule, by leaning on similar examples (MIRAGE 2025) | A principle that sounds right but does not fit its cases | A |
| Overgeneralization | Poor | 4,900 summaries, 10 models: 26–73% overgeneralized for several models; 4.85× the odds of expert summaries. A "be accurate" prompt made it worse (OR 1.90). Newer models were often worse; Claude models lowest | Qualifiers dropped; past results become present facts; findings become advice | A |
| Scope and conditions | Fair to poor | MDCR: GPT-4o answer accuracy 76.4%, condition F1 46.8 (exact) / 60.8 (relaxed). Condition recall 39–67% across models; most errors at the identification step (Chain of Condition) | Conditions lost while the answer stays right | B |
| Merge duplicates | Good | Zero-shot GPT-4 entity matching 89.95 average F1, on par with fine-tuned Ditto at 89.3 (Peeters 2025) | Merging two items whose scope differs | A |
| Find conflicts | Poor | ContraDoc, asked "is there a contradiction?": GPT-4 recall 8%, F1 15.6. Judge-then-find: F1 54. It located 61% of opinion contradictions vs 85% of negations | Subjective conflicts are the hardest type | A |
| Same question elsewhere | Poor | ARN: near analogies ≈75%, far ≈40% (humans 94–98%). GPT-4 is below chance on far ones zero-shot; a sentence-similarity baseline scored 1% on the hardest split. A grounded writer "over-associates unrelated facts" (STORM) | Surface similarity beats shared structure; links without a reason | A / B |
| Standalone statements for retrieval | Good | Indexing by propositions instead of passages: +10.1 Recall@20 for unsupervised retrievers, +2.2 for supervised (Dense X, EMNLP 2024) | — | A |
| Logic flow (discourse) | Poor zero-shot | Implicit relations, PDTB 3.0: GPT-4 macro F1 25.8 vs 60.1 supervised; prompt tricks did not help (LAW 2024). A fine-tuned Llama-2-70B RST parser beat the prior best (55.4) by only 2–3 points | Unstated "because", "but", "so" | A |
| Summaries of summaries | Poor | Hierarchical merging is more coherent; incremental updating keeps more detail (BooookScore). No auto-rater correlates strongly with humans; the end of a book is over-weighted (FABLES). GPT-4o and Claude 3 Opus <20% joint score vs humans 56% (SummHay) | Omission and recency bias | A |
| Repeated rewriting | Poor | Iterated rewrites converge on "attractors", more with open-ended instructions (ICLR 2025). Summary-based compaction lost 60% of facts and 54% of constraints, with the model still confident (2026 preprint) | Never rewrite the system's own output | A / B |
| Keep minority views | Poor | 9 LLMs, 6 datasets: model and human summaries both under-represent some perspectives (NAACL 2024) | The user's unusual views vanish first | A |
| Track a change of view | Poor | Frontier models ≈50% at following evolving profiles (PersonaMem). Memory systems omit 37–94% of updates, invent ≤1.2% (HaluMem). Assistants lose ≈30% accuracy over long histories (LongMemEval). Hard personalizers resist drift poorly; grounded models miss real updates (BeliefShift) | A missed update, not a false one | A / B |
| Checker bias | Known | LLM judges score their own outputs higher, linked to recognizing their own text (Panickssery 2024) | Checking with the same model | A |

**Gap.** No benchmark measures these jobs on personal AI chats. The numbers come from essays, debates, science, news, fiction and synthetic users. Dialogue results (DialAM, TofuEval) are worse, so treat every figure as an upper bound.

## Proposed pipeline

Each job is small, writes an append-only proposal, and has its own check. "Code" means deterministic: the same input gives the same output, so runs replay (I18). Any LLM job may return "unclear"; such items wait as pending and never reach the page.

| # | Job | Made by | Check, and what happens on failure | User's words kept as evidence |
|---|---|---|---|---|
| 0 | **Capture and segment**: turns, speaker, time, exact spans | Code | Speaker comes from the channel; every quote is an exact substring (I1–I3) | It is the record |
| 1 | **Find the moves**: the user states, adopts, rejects, builds on, revises, or only asks. Judged over the episode, not turn by turn | LLM, then a blind re-label by a second family | The labels must agree, otherwise "unclear". A bare question records nothing | **Yes**: the move span. For an adopted AI idea, the AI span and the user's adoption span |
| 2 | **Value and scope gate** | Signals by code: recurrence across sessions, reasons given, acted on, project tags. LLM judges "position or passing preference" and tests scope with project names removed | Ranked against the user's nearby items, not a fixed cut; uncertain items pend; project-only items go to the project layer (note `18`) | Spans stay in the archive |
| 3 | **Restate**: one short standalone sentence. Just enough context, same strength and certainty, no new claims | LLM | Two-way entailment by a different family. Code lints: no new names or numbers; hedges, negations and "only" kept; length cap; no IDs. If it fails twice, show the trimmed exact quote, marked as the user's own words | **Yes**: one click under the statement |
| 4 | **Conditions and scope**: applies when, not when, which context | LLM | Each condition cites a span or is marked "inferred". The restated scope may not be wider than the source. "Scope unknown" is allowed and never filled in by guessing | **Yes**: the span for each condition |
| 5 | **Reasons and route**: why, and which exchanges led there | LLM picks; code links the exchanges | Each reason cites a span. An AI reason counts as the user's only if job 1 found adoption | **Yes** |
| 6 | **Question key**: the question the item answers, in general words | LLM | The item must answer that question (entailment). A general item's question must not need the project's name | No; derived |
| 7 | **Merge duplicates** | Candidates by code (embeddings plus word overlap on statement and question); LLM judges pairs | Two families agree (I12). Different scope means link, not merge. Every merge is reversible | Both originals kept |
| 8 | **Link**: supports, refines, conflicts, same question in another context | Candidates by code from question keys; LLM types each link | Each link carries a one-line reason citing both items. Conflicts and cross-context links need two families to agree. Otherwise they stay hidden as "possible" (DQ-15) | **Yes**: both sides of a conflict |
| 9 | **Abstract to a principle** | LLM proposes, only from two or more independent instances in different sessions or contexts | Each instance must check as a case of it; a counter-instance search and job 4's scope check run. Labelled "pattern Northstar sees" until the user states it | **Yes**: the instances |
| 10 | **Track change of view** | Timeline by code: supersede, never overwrite. LLM labels the change (narrowed, widened, reversed, dropped) | Old and new spans with dates. A periodic "stale" sweep looks for later statements that should supersede an item | **Yes**: old and new spans |
| 11 | **Compose the pages** | Code: templates filled from typed fields and links (question-led cards, principle with cases, timeline, local tension view; note `15`) | Every connective sentence comes from a typed link and is checked as in job 3. No IDs on any page | Quotes one click behind each line |
| 12 | **Summarize upward** (topic overviews) | LLM, from leaves only (I7). Regenerated, never patched | A coverage list: each leaf is either reflected or listed as "not in this summary". Faithfulness check. Rare and older items are protected | Leaves cited |

**Deterministic:** job 0, all of job 11, and the code parts of jobs 2, 5, 7, 8 and 10. That covers segments, value signals, candidate pairs, timelines, page order and layout. Quote checks, lints, coverage lists, caps and scope filters are code too.
**LLM, always checked by another family:** jobs 1, 3, 4, 6 and 12, plus the judgements in jobs 7–10.
**User's words required as evidence:** every stance or adoption (1), every item (3), every condition (4), every reason (5), both sides of every conflict (8), every principle's instances (9) and both ends of every change (10). The words sit under the statement, not in place of it.

**Checks for every job.** The checker comes from a different model family than the writer. "Unclear" is a valid result, as in Claimify, which declines 2–5% of sentences. Each job has an error budget measured on the user's own chats, a second model audits a daily sample, and user corrections are hard constraints (I21). No step needs the user to review anything.

## What it means for Northstar

1. **Show the clear statement; keep the quote under it.** This fixes the "too literal" items without losing provenance. The exact quote is the fallback when a restatement fails, not the default.
2. **Build structure in code from typed links.** Recovering unstated logic from prose is the weakest measured job (26 F1). The model fills typed fields; templates turn them into "because", "but" and "so" sentences. That is the logic flow the knowledge map lacked.
3. **Give every item a question key.** It organizes the question-led view in note `15`. It is also how links across contexts get found, since surface similarity fails on far analogies.
4. **Make conditions a first-class field, with "scope unknown" allowed.** The project-versus-personal decision (note `18`) and conflicts between contexts depend on it. Overgeneralization is the best-measured failure, so the scope check never skips.
5. **Gate abstraction** as in job 9.
6. **Show a conflict only when two families agree, with both quotes.** A wrong conflict costs trust, so uncertain ones stay hidden.
7. **Expect missed updates, not false ones**, hence the stale sweep.
8. **Regenerate overviews from leaves and check coverage.** Faithfulness checks alone miss omissions, recency bias and lost minority views.
9. **AI side (hypothesis).** A standalone principle with its scope may work better as injected background ("prefer X when Y") than "you concluded X", and standalone statements retrieve better (Dense X). Test this against the echo problem in note `19`.
10. **Measure each job first.** Hand-label about 30 items per job from the user's real chats in one short optional session, and set error budgets from that.

## Open questions

- How strict should the restatement check be? A strict check rejects good paraphrases; a loose one lets meaning drift. Start strict and measure the rejection rate.
- Should "pattern Northstar sees" items appear in the main view or one level down? This depends on note `18`.
- Should the question key be shown as a heading, or used only behind the scenes? Note `15` suggests showing it.

## Sources

All checked 2026-10-14. "Abstract" means only the abstract was read.

- Savigny & Yun (2025), AMELIA, preprint. https://arxiv.org/abs/2508.17926 (B; Table 2 read)
- Li et al. (2025), LLMs in Argument Mining: A Survey, preprint. https://arxiv.org/abs/2506.16383 (B)
- Gorur, Rago & Toni (2024), relation-based argument mining with LLMs. https://arxiv.org/abs/2402.11243 (B: preprint; results read)
- Ruiz-Dolz et al. (2024), DialAM-2024 overview, ArgMining. https://aclanthology.org/2024.argmining-1.8 ; top system https://aclanthology.org/2024.argmining-1.9 (A, abstracts)
- Metropolitansky & Larson (2025), Claimify, ACL. https://arxiv.org/abs/2502.10855 (A; Tables 1–4 read)
- Gunjal & Durrett (2024), Molecular Facts, Findings of EMNLP. https://arxiv.org/abs/2406.20079 (A, abstract)
- Google Research (2025-05-06), minimally-lossy simplification. https://research.google/blog/making-complex-text-understandable-minimally-lossy-text-simplification-with-gemini/ (C, vendor blog)
- Tang, Laban & Durrett (2024), MiniCheck, EMNLP. https://arxiv.org/abs/2404.10774 ; LLM-AggreFact leaderboard (undated) https://llm-aggrefact.github.io/ (A)
- Tang et al. (2024), TofuEval, NAACL. https://aclanthology.org/2024.naacl-long.251 (A, abstract)
- Farquhar et al. (2024), semantic entropy, Nature. https://www.nature.com/articles/s41586-024-07421-0 (A for the method; numbers not used)
- Vectara hallucination leaderboard, updated 2026-09-22. https://github.com/vectara/hallucination-leaderboard (C: vendor, automated judge)
- Padmakumar & He (2024), writing with LMs reduces content diversity, ICLR. https://arxiv.org/abs/2309.05196 (A, abstract)
- Jakesch et al. (2023), co-writing with opinionated LMs, CHI. https://arxiv.org/abs/2302.00560 (A, abstract)
- Qiu et al. (2024), Phenomenal yet Puzzling, ICLR. https://arxiv.org/abs/2310.08559 (A, abstract)
- Li et al. (2025), MIRAGE, ICLR. https://arxiv.org/abs/2410.09542 (A, abstract)
- Peters & Chin-Yee (2025), generalization bias in LLM summaries, R. Soc. Open Sci. https://pmc.ncbi.nlm.nih.gov/articles/PMC12042776/ (A)
- Chen et al. (2024), MDCR, preprint. https://arxiv.org/abs/2406.11784 (B; Table 1 read)
- Chain of Condition (2024), preprint. https://arxiv.org/abs/2408.05442 (B; Tables 11–12 read)
- Peeters, Steiner & Bizer (2025), entity matching with LLMs, EDBT. https://arxiv.org/abs/2310.11244 (A; Tables 4 and 6 read)
- Li, Raheja & Kumar (2024), ContraDoc, NAACL. https://arxiv.org/abs/2311.09182 (A; Tables 2–6 read)
- Sourati et al. (2024), ARN, TACL. https://arxiv.org/abs/2310.00996 (A; Table 2 read)
- Shao et al. (2024), STORM, NAACL. https://arxiv.org/abs/2402.14207 (B, abstract)
- Chen et al. (2024), Dense X Retrieval, EMNLP. https://arxiv.org/abs/2312.06648 (A; gains from the arXiv text)
- Yung et al. (2024), Prompting implicit discourse relation annotation, LAW. https://arxiv.org/abs/2402.04918 (A; results read)
- Maekawa et al. (2024), RST parsing with LLMs, EACL. https://aclanthology.org/2024.eacl-long.171 (A; gain stated only as "2–3 points")
- Chang et al. (2024), BooookScore, ICLR. https://arxiv.org/abs/2310.00785 (A, abstract)
- Kim et al. (2024), FABLES. https://arxiv.org/abs/2404.01261 (A, abstract)
- Laban et al. (2024), Summary of a Haystack. https://arxiv.org/abs/2407.01370 (A, abstract)
- Perez et al. (2025), When LLMs Play the Telephone Game, ICLR. https://arxiv.org/abs/2407.04503 (A, abstract)
- Zahn & Chana (2026), Knowledge Objects, preprint. https://arxiv.org/abs/2603.17781 (B, abstract)
- Zhang et al. (2024), fair summarization of diverse perspectives, NAACL. https://arxiv.org/abs/2311.07884 (A, abstract)
- Jiang et al. (2025), PersonaMem. https://arxiv.org/abs/2504.14225 (B, abstract)
- HaluMem (2025), preprint. https://arxiv.org/abs/2511.03506 (B; update table read)
- Wu et al. (2025), LongMemEval, ICLR. https://arxiv.org/abs/2410.10813 (A, abstract)
- Myakala et al. (2026), BeliefShift, preprint. https://arxiv.org/abs/2603.23848 (B, abstract; no numbers)
- Panickssery, Bowman & Feng (2024), self-preference in LLM evaluators, NeurIPS. https://arxiv.org/abs/2404.13076 (A, abstract)
- Internal: `docs/research/06-time-history-and-consolidation.md`, `docs/research/08-ingestion-and-extraction.md`; round 3 notes `15`, `18`, `19`.

**Corrections to the 2026-10-10 draft.** Claimify coverage is 83.7, not 87.9. Vectara frontier rates are about 3–15%. AMELIA is a preprint (B). GPT-4 on PDTB 3.0 replaces the 2023 ChatGPT discourse figure. ContraDoc, ARN and MDCR numbers are now from the papers' tables.
