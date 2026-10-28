# Keeping an AI-Maintained Memory Correct When the Maintainer Itself Loses Focus

Track 13, round 2. Written 2026-10-07. Status: research note that feeds design. It does not decide anything.
Anchor: `docs/GOAL.md` §3.4 and non-negotiables 3 (the AI manages it) and 7 (the maintainer is robust). Product facts are date-stamped. Items I could not check against a primary source are marked "(unverified)" or "(secondary source)". Numbers a vendor reports about its own product are labelled as vendor-reported.

---

## Questions this track answers (tied to GOAL.md)

GOAL.md §3.4 asks for "AI-managed maintenance that holds up against its own attention loss … It must not depend on one agent staying attentive". §6 adds that "maintenance errors are bounded, detectable and correctable". This track answers how to build that, without asking the user to review anything (non-negotiables 1 and 3).

1. **Shape.** Should maintenance be one autonomous agent, or a deterministic workflow of small jobs? What does the evidence on long-horizon reliability say?
2. **Invariants.** Which correctness properties can code enforce outright, so that no model has to stay attentive to keep them?
3. **Verification.** Which checks actually catch errors: self-critique, self-consistency, cross-model verifiers, or quote and provenance validation? How independent can a verifier be?
4. **Failure evidence.** How does maintenance in existing memory systems (Mem0, Zep/Graphiti, A-MEM-style evolution, ChatGPT, Codex) fail, and what fixed it?
5. **Attribution.** How do we keep **AI-said knowledge first-class** (non-negotiable 2) and correctly attributed, when extractors are known to drop or misattribute assistant content?
6. **Monitoring and recovery.** How are errors detected continuously and rolled back automatically, with human correction as an optional signal only?
7. **Injection.** What happens when the maintainer reads untrusted content (AI outputs, pasted web text)?
8. **Dogfooding.** Can the maintainer anchor itself with the same goal and state anchoring that the system gives to chats?
9. **Cost and latency** at 20–100 chat turns a day, including the fast path that in-session focus needs (non-negotiable 5).

---

## Key findings

**1. Reliability falls with the number of steps and with self-generated context. A long-lived maintainer agent is the wrong shape.**
- *Mechanism.* Each step has some error probability p, and errors feed back. A task of n dependent steps succeeds with probability about (1−p)ⁿ. On top of that, a model conditions on its own earlier mistakes.
- *Evidence on self-conditioning.* Sinha et al., "The Illusion of Diminishing Returns" (ICLR 2026), supplied the plan and the knowledge so that only execution was measured. Per-step accuracy still fell as steps accumulated. Models were "more likely to make mistakes when their context contains their own earlier errors", and scaling model size did not remove this. Thinking reduced it.
- *Evidence on multi-turn drift.* Laban et al. (ICLR 2026) found that every model tested scored on average 39% lower in multi-turn conversation than single-turn, and the loss was mostly *unreliability*, not lost capability. Putting all the information into one turn (CONCAT) recovered 95.1% of single-turn performance.
- *Practitioner reports.* Anthropic's guidance agrees. Agents carry "the potential for compounding errors" (Building Effective Agents, Dec 2024), and "agents are stateful and errors compound" (multi-agent research system, Jun 2025). Context is "a finite resource with diminishing marginal returns" because attention creates "n² pairwise relationships for n tokens" (context engineering, Sep 2025).
- *Long tasks at high reliability.* METR's 50%-success time horizon doubled about every 7 months (Mar 2025). Secondary sources report that the 80%-success horizon is several times shorter than the 50% one (unverified). Maintenance needs far better than 80% per operation.
- *Implication.* A maintainer that runs indefinitely and accumulates state will accumulate errors. Reliability has to come from short, stateless jobs that receive their full specification in a single turn.

**2. Self-correction in the same context is weak. Verification works when it is rules-based or when the verifier sees the output as someone else's work.**
- *Intrinsic self-correction.* Huang et al. (ICLR 2024) found that LLMs often fail to fix their own reasoning without external feedback, and sometimes get worse. In a budget-matched comparison, self-consistency (88.2%) beat multi-agent debate (83.0%).
- *The blind spot.* Self-Correction Bench (Tsui, NeurIPS 2025) measured an average 64.5% "blind spot": models failed to correct their own errors but did correct identical errors presented as coming from elsewhere.
- *Anthropic's guidance (Sep 2025).* Its Agent SDK post says "the best form of feedback is providing clearly defined rules for an output, then explaining which rules failed and why". It calls LLM-as-judge "generally not a very robust method" with "heavy latency tradeoffs".
- *Implication.* Make code checks the backbone. Model verification runs in a *fresh call*, framed as auditing another agent's proposal.

**3. Verifier independence has limits: models increasingly make the same mistakes.**
- *Correlated errors.* Goel et al. (ICML 2025) defined CAPA, a chance-adjusted measure of error overlap. LLM judges favour models similar to themselves, and "errors of different models are converging" as capability rises. That generalizes the self-preference result (Panickssery et al. 2024, round-1 note 09).
- *Semantic entropy.* Farquhar et al. (Nature 2024) flag confabulations by sampling several answers and measuring disagreement in meaning. Their own stated limit: "If an LLM makes consistent mistakes, this new method won't catch that."
- *Calibrated selective verification.* This gives statistical bounds instead of hope:
  - *Trust or Escalate* (Jung, Brahman and Choi, ICLR 2025) runs a cascade that starts with a cheap judge and escalates when its confidence is low. It has a provable guarantee of agreement with humans. A cascade starting from Mistral-7B kept more than 80% human agreement while covering nearly 80% of items.
  - *Conformal factuality* (Mohri and Hashimoto, ICML 2024) gave 80–90% correctness guarantees by backing off to less specific claims.
  - Both need a labelled calibration set.
- *Implication.* Cross-model checks reduce error but do not make it independent. Statistical guarantees need ground truth. That makes golden sets mandatory, and makes optional user corrections valuable as calibration data.

**4. Maintenance in shipped memory systems fails mainly by omission, misattribution and corruption-by-rewrite. The fixes all moved toward append-only, deterministic and verified.**
- *HaluMem (Nov 2025), via round-1 notes 08 and 09:*
  - Update omission was above 50% for most systems, while update hallucination was at or below 1.15%.
  - Systems with usable recall absorbed about 43–55% of assistant-introduced "distractor" memories as user facts.
- *Assistant content gets dropped.* Zep fell 17.7% on LongMemEval's "single-session-assistant" questions, the ones about what the AI said (round-1 note 03). The class of knowledge that non-negotiable 2 makes first-class is the class extractors drop.
- *Rewriting corrupts.*
  - In ACE, one rewrite collapsed an 18K-token context to 122 tokens and pushed accuracy below the no-memory baseline (round-1 note 03).
  - Microsoft's "Human-Inspired Memory Architecture" (May 2026), on LongMemEval-S: agglomerative clustering with merge scored 48.4%, raw RAG 78.4%, and dedup-only 76.8%.
  - "Manufactured Confidence" (Kwon, Jun 2026) shows consolidation in mem0 and LangMem stripping hedges, so hearsay becomes confident fact. A passive "unverified" tag was ignored. Keeping the tentative wording, plus one redundant source, restored correct decisions.
- *What fixed it:*
  - Mem0 moved to ADD-only extraction (Apr 2026; vendor-reported gains).
  - Zep added deterministic entity dedupe on identity keys, so entities are "merged deterministically instead of relying on similarity" (changelog 2026-07-09).
  - TrustMem (Jun 2026) puts a Memory Transition Verifier that scores coverage, preservation and faithfulness in front of updates. It cut transition-level omission, corruption and hallucination by 40.1%, 79.1% and 50.0% against the strongest baseline.

**5. A maintained memory reuses its own errors.**
- *Experience-following.* Xiong et al. (ACL 2026) show agents copy retrieved precedent. Erroneous records spread forward, and add-all memory widened the error gap over time. Strict selective addition plus evaluator feedback closed it.
- *Memory contagion.* Liu (Jun 2026) found evaluator bias spreading through memory even when consolidation was perfect (an oracle), on older models, at contamination rates as low as 20%.
- *Circular reporting* (round-1 note 06): an AI inference retrieved later as "known" counts as its own corroboration.
- *Implication.* The maintainer must never treat its own derived output as evidence. Consolidation must read leaves (source-anchored claims), not earlier syntheses.

**6. Some guarantees can be bought from the API. Use them, but know what they do not cover.** Checked 2026-10-07 against platform.claude.com docs.
- *Structured outputs* (`output_config.format` or strict tool use) guarantee schema-valid JSON. The schema subset excludes numeric bounds, string lengths and recursion; the SDK validates those client-side. So they guarantee *syntax*, not *semantics*.
- *Citations* give a hard guarantee: "citations are guaranteed to contain valid pointers to the provided documents". `cited_text` is not billed as output tokens. "Custom content" documents are cited at the granularity of the blocks you supply, so one block per chat message gives a pointer to a message ID.
- *The two do not combine.* Citations are incompatible with structured outputs and return a 400.
- *Lessons from Anthropic's long-running harness (Nov 2025).* JSON state files were used because "the model is less likely to inappropriately change or overwrite JSON files". The coding agent was told "it is unacceptable to remove or edit tests". The verification artifacts were placed outside the agent's power to edit.

**7. Durable orchestration with recorded LLM outputs is a solved pattern. Re-running a model is not replaying it.**
- *Temporal* runs model calls as activities. On replay, "if the event history already contains the result of that activity, Temporal returns the recorded result immediately".
- *No sampling control.* Thinking Machines (Sep 2025) traced endpoint nondeterminism to batch variance, which happens even at temperature 0. Claude 4.7 and later models now return a 400 for non-default `temperature`/`top_p`/`top_k` (deprecations page, 2026-10-07).
- *Models retire.* Anthropic guarantees at least 60 days' notice; Sonnet 4 and Opus 4 retired on 2026-06-15. The exact past output therefore cannot be regenerated.
- *A production template exists in Codex's memory pipeline* (openai/codex `codex-rs/memories/README.md`):
  - Phase-1 jobs are "leased/claimed in the state DB".
  - Outcomes are `succeeded`, `succeeded_no_output` or `failed`, with retry backoff.
  - Phase 2 takes "a single global phase-2 lock".
  - It runs the consolidation sub-agent "with no approvals, no network, and local write access only", disables delegation, and writes a git-style diff.

**8. The maintainer must read untrusted text, and detection-based injection defenses fail under adaptive attack. Containment by architecture works for actions, not for content.**
- *Detection fails.* "The Attacker Moves Second" (OpenAI, Anthropic and Google DeepMind authors, Oct 2025) bypassed 12 published defenses, with attack success "above 90% for most". Human red-teaming reached 100%.
- *Containment rules:*
  - Meta's Rule of Two (Oct 2025): at most two of {untrusted input, sensitive data, state change or external communication} in one session.
  - Willison's "lethal trifecta" (Jun 2025).
  - The design-patterns paper (Beurer-Kellner et al., Jun 2025): map-reduce isolation, dual LLM, plan-then-execute.
  - CaMeL kept 77% task utility, against 84% undefended, with provable security on AgentDojo.
- *The limit.* These patterns stop injected text from choosing *actions*. Injected text can still shape the *content* of permitted outputs, and the maintainer's outputs *are* content.
- *Memory-specific results (2026):*
  - Provenance laundering: consolidation rewrites external text as apparent user history. Up to 1.000 attack success on vulnerable consolidated memories (Xu et al., Jul 2026).
  - Louck (Jun 2026) proves, with TLA+ models, that no content- or lineage-based defense is sound under laundering. Write-time origin binding is *necessary*. Laundering reached up to 68% attack success against existing defenses and 0% against origin-bound authority.

**9. Continuous quality control for LLM pipelines rests on assertions, golden sets, error budgets and graded escalation.**
- *Assertions.* SPADE (Shankar et al., PVLDB 2024) synthesizes data-quality assertions for LLM pipelines and has been used on more than 2,000 pipelines.
- *Criteria drift.* "Who Validates the Validators?" (UIST 2024) shows that evaluation criteria shift as outputs are seen, so a check set has to be versioned.
- *Grader types.* Anthropic's evals guidance (Jan 2026) names three: code, model and human. Human grading is reserved mainly for calibration.
- *Error budgets.* Google SRE's policy is to "halt all changes and releases other than P0 issues or security fixes until the service is back within its SLO".
- *Compensating transactions.* Microsoft's pattern undoes completed steps with idempotent compensating actions, while recording "information about each step and how to undo it".

**10. The anchoring techniques that keep agents on task are usable by the maintainer itself.**
- *Recitation.* Manus (Jul 2025) recites goals by rewriting a `todo.md` at the end of context ("around 50 tool calls on average" per task). It keeps failures in context ("erasing failure removes evidence"), and its compression is "always designed to be restorable".
- *External state.* Anthropic recommends structured notes outside the context window, and sub-agents that return "condensed, distilled summary" output of about 1–2K tokens (Sep 2025). Sub-agents "store their work in external systems, then pass lightweight references back" (Jun 2025).
- *State and progress.* The long-running harness pairs a JSON feature list carrying a `passes` field with a progress file, git commits, and one feature per session (Nov 2025).

**11. Cost is not the constraint. Prices as of 2026-10-07, per million tokens.**

| Model | Input | Output | Batch input / output | Cache read |
|---|---|---|---|---|
| Claude Haiku 5.5 (prompts ≤100K) | $0.10 | $0.50 | $0.05 / $0.25 | — |
| Claude Sonnet 5.5 | $2 | $10 | $1 / $5 | 0.05× input |
| Claude Opus 5.5 | $4 | $20 | $2 / $10 | 0.05× input |
| OpenAI gpt-5-mini | $0.25 | $2.00 | $0.125 / $1.00 | — |

The Batch API takes 50% off; most batches finish in under 1 hour, and they expire after 24 hours. The OpenAI price is from developers.openai.com. At realistic volumes maintenance costs roughly a dollar a day (see the table below). What limits the design is reliability and latency.

---

## What this means for the Northstar architecture

The organizing rule: **the maintainer never holds the system in its head.** Code holds the state, the schedule, the invariants and the authority to write. LLMs are short, stateless, tool-less proposal functions whose inputs are assembled from the store.

### A. Shape: deterministic orchestrator plus stateless workers [maintainer]

1. **The orchestrator is code, not an agent.** A SQLite job table follows the Codex pattern (Finding 7):
   - leases, an idempotency key, and an outcome enum (`succeeded`, `succeeded_no_output`, `failed`, `quarantined`);
   - retry with backoff, and watermarks per source;
   - a single-writer lock per structural scope.

   No LLM chooses the next job, decides what gets written, or judges whether an invariant holds. This is the "workflow, not agent" choice from Building Effective Agents. An agent loop is allowed only inside one bounded job, and only where the steps cannot be scripted in advance (none of the jobs below need one).
2. **Every LLM call is a pure function: assembled input in, schema-constrained proposal out, no direct writes.** Workers get no network, no write tools, and no delegation, as in the Codex consolidation sub-agent. An optional *read-only* retrieval tool may be scoped by code to a fixed index snapshot. The output is validated by code, then applied as typed ledger events by the apply step.
3. **Each job sees its full spec in one turn and never inherits a previous job's conversation** (Finding 1: CONCAT recovers 95.1%). A job that fails validation is retried in a *fresh* call, possibly on a different model, never by "fixing it" in the same thread (Finding 2).
4. **LLM outputs are recorded decisions, not projections** [core]. Each proposal is stored with `job_id`, `batch_id`, `model@version`, a prompt hash, input IDs and the raw output. Replay reads what was recorded. Only deterministic views can be rebuilt from scratch (this extends round-1 note 06, Finding 3).

### B. Job types [maintainer; components named per job]

| Job | Kind | Input (assembled by code) | Output | Lane |
|---|---|---|---|---|
| J0 Capture & normalize | deterministic | adapter payload | immutable source record: message IDs, platform role, timestamps, content hash | both [surface adapters, core] |
| J1 Hygiene | deterministic plus small classifier | source record | secret/PII redaction, paste detection, imperative-text tag, sensitivity tier | both |
| JF Session anchor update | small LLM | last k turns, current session anchor, goal pack | *provisional* session-scoped state: goal, constraints, decisions and facts established in this chat by either side | fast [AI in-session] |
| J2 Segment | heuristic plus small LLM | closed conversation | episode span ranges (validated: contiguous, non-overlapping, covering) | slow |
| J3 Extract | LLM | one episode as message-addressed blocks, charter, ≤N neighbour items | candidates: kind, content, **span pointers**, holder, stance, certainty; for both user-said and AI-said content | slow [core] |
| J4 Verify | LLM, fresh context, different model | candidate, its spans, ±2 turns of context, rubric | per-rule verdicts: supported / unsupported / misattributed / hedge-lost / abstain | slow |
| J5 Link & resolve | embedding retrieval (code) plus LLM | candidate, top-k neighbours | proposed relations: duplicate-of, refines, supersedes, contradicts, supports, answers-question, advances-goal | slow [core, human structure] |
| J6 Apply | deterministic | validated proposals | typed ledger events; "upstream changed" flags on dependents | slow [core] |
| J7 Regenerate views | LLM per dirty node, nightly | leaf claims and spans only | topic page, learned-map node, "what to learn" node; every sentence cites claim IDs | nightly [human structure] |
| J8 Reorganize | LLM, weekly or triggered | structure snapshot, metrics | structural diff (split, merge, re-parent), applied automatically within a blast-radius limit | weekly [human structure] |
| J9 Compile packs | deterministic (optional small LLM) | current view | cross-session context pack and per-scope goal pack | on change [AI cross-session, AI in-session] |
| J10 Audit & monitor | deterministic plus strong LLM | samples, canaries | metrics, alerts, error-budget state | daily/weekly |
| J11 Repair | deterministic | `job_id` / `batch_id` / model filter | compensating events, quarantine, re-extraction plan | on alert |

5. **There are two lanes, because in-session focus cannot wait for batch verification** [AI in-session, maintainer].
   - JF runs every few turns on a small model through the standard API. It writes **only** to session scope, and its items carry a *provisional* label in the anchor.
   - Cross-session memory and the human structure receive only slow-lane, verified items.
   - When an episode closes, JF output is compared with J3 and J4 results. Disagreement is itself a monitored metric.
6. **AI-said knowledge is extracted, verified and monitored as its own stream** [core]. J3 runs over both sides with the same schema. J10 tracks the AI-said share of items per episode against the golden set, because shipped extractors systematically drop assistant content (Finding 4). A sharp fall in that share is an alert, not a curiosity.

### C. Invariants enforced in code [core, maintainer]

The validator rejects any proposal that violates one of these, or the apply step refuses it. None of them depends on a model paying attention.

- **I1 Provenance.** Every derived item has at least one span pointer (`source_id`, `message_id`, character range) that resolves to an immutable source.
- **I2 Quote fidelity.** Every quote is an exact substring of its referenced span after canonical normalization (Unicode NFC, collapsed whitespace), and the offsets match. With the Citations API on message-level custom-content blocks, the pointer itself is guaranteed (Finding 6), and code still re-checks it.
- **I3 Speaker by construction.** `speaker` is copied from the source message's adapter role, never set by the model. A span that crosses speakers is split or rejected. This turns the HaluMem distractor failure into something a type check catches.
- **I4 Endorsement needs user evidence.** An AI-said claim can be marked `endorsed` or `adopted` only if it cites a user-authored evidence span. Without one, it stays `encountered` with holder `assistant`. That keeps AI-said items first-class without crediting them to the user.
- **I5 No instruction promotion.** Only user-typed spans can create items of kind `instruction`. Imperatives from AI, pasted or external text are stored as quoted data.
- **I6 Append-only.** There is no UPDATE or DELETE on the ledger; every change is a typed event. Excision is the only destructive operation, and only the user starts it.
- **I7 No summarizing summaries.** J7's input assembler type-checks that it receives only leaf claims and source spans, never previous page text.
- **I8 Citation closure.** Every sentence on a generated page cites at least one claim ID that is active or explicitly historical.
- **I9 Coverage monotonicity.** A regenerated view cannot drop a claim it covered before unless a recorded event (retract, supersede, merge, scope change) explains the drop. This is the guard against ACE-style collapse.
- **I10 Hedge preservation.** If a lexicon finds hedges in the source span ("I think", "maybe", "not sure"), the item's certainty is capped at `tentative` unless an independent span supports more. J4 adds a semantic check.
- **I11 Independence counting.** Support equals the number of distinct primary sources. AI-derived items never count as support for themselves or for their inputs.
- **I12 Reversible merges.** A merge is an alias event. It needs either an exact identity-key match (Zep-style) or agreement between two verifiers from different families.
- **I13 Blast-radius cap.** There are limits on events per job and on nodes touched per reorganization. A job over the limit is quarantined whole.
- **I14 Idempotency.** The pair (job type, input hash, `schema_v`, model) maps to one job ID, so a re-run cannot duplicate.
- **I15 Schema validity.** Strict structured output, plus client-side checks of the constraints the schema subset cannot express.
- **I16 Temporal sanity.** `valid_from` ≤ `recorded_at`, and held-time ≤ capture time.
- **I17 Scope.** Every item has a scope, and packs include only matching scopes.
- **I18 View determinism.** Deterministic views rebuild hash-identical with model access disabled.
- **I19 Separation of duties.** Workers cannot read or modify invariants, prompts, golden sets, thresholds or their own permissions. These change only by a versioned commit outside the maintainer. This is the "do not edit the tests" rule from Finding 6, and it blocks metric gaming.
- **I20 Origin binding.** Origin and trust tier are bound by adapter code at write time and are immutable afterwards (Finding 8). No job output can raise an item's origin tier.

### D. Verification strategy [maintainer]

7. **Verification is layered and routed by risk.** Each event type has a risk tier:
   - *Low*: add an `encountered` AI-said claim, add a tag. Checks: invariants plus a cheap verifier.
   - *Medium*: refine, link, add a user belief. Checks: invariants plus a verifier on a different model.
   - *High*: supersede, merge, stance change to `endorsed`, goal or "what to learn" changes, structural reorganization. Checks: invariants, self-consistency on the uncertain fields, a verifier from another family, and a 100% sampled audit by the strongest model.

   | Layer | What | Catches | Does not catch |
   |---|---|---|---|
   | L0 Code invariants (I1–I20) | Always, on 100% of proposals | Provenance, quotes, speaker, schema, blast radius, instruction promotion | Wrong meaning drawn from a valid span |
   | L1 Self-consistency | 2–3 samples on stance, kind and relation; disagreement leads to abstain/`uncertain` | Confabulated or unstable judgments (Farquhar) | Consistent mistakes |
   | L2 Independent verifier | Fresh call, "audit this proposal", entailment against the span | Unsupported claims, misattribution, lost hedges (avoids the blind spot) | Errors shared across model families (CAPA) |
   | L3 Calibrated cascade | Cheap verifier first; escalate when confidence is below a threshold calibrated on the golden set (Trust or Escalate) | Bounds the false-accept rate *relative to calibration labels* | Distribution shift away from the calibration set |
   | L4 Sampled audit | Strongest model, daily: about 5% of applied events plus all high-risk ones, judged against the leaves | Drift and systematic prompt bugs; feeds the error budget | Rare errors outside the sample |
   | L5 Golden and canary sets | Fixed episodes with known answers (the round-1 world-ledger harness), run nightly and on every prompt or model change | Regressions, omission, model swaps | Real-world patterns missing from the set |
   | L6 User corrections (optional) | Any correction becomes a labelled example, recalibrates L3 and is counted against the error budget | Personal ground truth | Nothing is required of the user |

8. **Omission gets dedicated detectors, because it is the dominant and least visible error** (Finding 4).
   - Deterministic sentinels flag episodes whose text contains decision or commitment cues ("let's go with", "I'll use", "so the answer is", unresolved user questions, AI explanations over N tokens) but that produced zero items of the matching kind. Those episodes are re-extracted by a second model.
   - Canaries measure recall directly.

### E. Monitoring metrics [maintainer, with a human-structure health view]

- *Pre-validation invariant violation rate* per job type and model. This measures model health; after validation the rate is zero.
- *Verifier reject rate* and *cascade escalation rate*. A step change means drift or a prompt bug.
- *Canary scores:*
  - extraction precision and recall;
  - attribution accuracy (user-said vs AI-said vs third party);
  - false-endorsement rate;
  - update omission rate and stale-assertion rate;
  - wrong-merge and duplicate rates;
  - hedge retention, rare-detail retention, and coverage after N regenerations.

  These come from round-1 note 09.
- *Audit disagreement rate* (L4 against what was applied). This is the main error-budget signal.
- *AI-said share* and *items per episode*, compared with the golden-set baseline.
- *Churn and oscillation:* A→B→A supersessions within a time window, and events per node per week.
- *Fast/slow-lane disagreement.*
- *Injection canaries:* planted strings in test sources, and whether they persist.
- *Lag:* turn to provisional anchor (target: within one turn), turn to verified (typically under 2 hours), and cost per day.

### F. Recovery [core, maintainer]

9. **Error budgets trigger an automatic freeze, not a human ritual.**
   - Example budget: audited error rate on high-risk events of 2% or less over a rolling 7 days, and no canary metric down more than X points. The numbers are to be calibrated.
   - When the budget is exhausted, the affected job type stops applying high-risk events. Capture and low-risk events continue, and held proposals are kept. If a canary regression lines up with a prompt or model change, the change is rolled back.
   - This copies the SRE freeze (Finding 9), aimed at the maintainer's own changes.
10. **Rollback is a compensating event batch selected by `job_id`, `batch_id` or `model@version`,** followed by a deterministic rebuild of the views. Compensations are idempotent (the Microsoft pattern). Because sources are immutable, a systematic error is fixed by re-extracting the affected window with the corrected prompt and applying the *diff* as typed events.
11. **Quarantine is a holding state, not a review queue.** A failed proposal is retried once on a different model. If it still fails, it stays quarantined. The underlying source span stays searchable as raw text and is shown with an "uncertain" label wherever it is relevant. The user can look but never has to.
12. **Re-processing runs in an as-of sandbox.** When past episodes are re-extracted (model migration, prompt fix), the job sees the store *as of the episode's timestamp*. That prevents hindsight contamination and keeps stance timing honest.
13. **Model migration is treated as a deployment.**
    - Pin model IDs per job type (for example `claude-sonnet-5-5`, tentative retirement no sooner than 2027-09-28).
    - Run the replacement in shadow on the golden set plus a sample of real episodes.
    - Switch only if no metric degrades beyond tolerance.
    - Retirement notices (at least 60 days) start this automatically.

### G. Prompt-injection containment [maintainer, surface adapters, AI cross-session]

14. **Workers meet the Rule of Two by construction.** They have untrusted input and sensitive data, but no state change and no external communication. Their only output is a proposal that code validates.
15. **Map-reduce isolation.** Each episode is processed in its own call, so injected text in one episode cannot redirect jobs on other episodes.
16. **Origin binding at write time** (I20) plus provenance-capped trust is the defense against laundering through consolidation (Finding 8). AI-facing packs render memory as quoted, source-labelled data, never as directives. Red-team canaries run in CI.
17. **The plain residual.** A poisoned *claim* can still enter the core, labelled with its true origin (see Risk R4).

### H. Dogfooding: the maintainer anchors itself with the system's own primitives [maintainer, AI in-session]

18. **A maintainer charter** is a short, stable, cache-friendly prefix in every job: the relevant GOAL non-negotiables, the invariants in plain words, and "abstain when unsure". It has the same shape as the goal pack the system gives to chats.
19. **A job card at the end of the prompt** recites the single deliverable, the rule IDs it will be judged by, and the output schema (Manus-style recitation, Finding 10).
20. **The maintainer's own state is a set of rows in the store, not a conversation:** queue, metrics, open issues, error-budget state. The same anchor compiler (J9) can produce a "maintainer pack" for any diagnostic job. If the anchoring primitive works for the maintainer, that is early evidence that it works for chats.

### I. Cost and latency estimate [maintainer]

*Assumptions (mine; the user's real distribution is unmeasured):*
- one turn averages about 1,100 tokens (user about 200, AI about 900);
- an episode is about 10 turns;
- about 10 candidates per episode;
- slow lane on the Batch API, fast lane on the standard API.

*Model mix:*
- JF and J2 on Haiku 5.5;
- J3, J5 and J7 on Sonnet 5.5;
- J4: Haiku first, escalating about 30% to Sonnet; the 20% high-risk items also go to gpt-5-mini;
- L4 audits on Opus 5.5;
- a fixed nightly canary of about 75K input and 17K output tokens per day.

*Thinking tokens are included roughly.* Read the figures as ±2×.

| Volume | Episodes/day | Approx. tokens/day (in / out) | Batch-lane cost/day | All-standard cost/day | Monthly (batch) |
|---|---|---|---|---|---|
| 20 turns | 2 | ~0.3M / ~0.05M (incl. canary) | ~$0.40 | ~$0.80 | ~$12 |
| 50 turns | 5 | ~0.6M / ~0.10M | ~$0.75 | ~$1.50 | ~$23 |
| 100 turns | 10 | ~1.1M / ~0.18M | ~$1.35 | ~$2.70 | ~$40 |

- Where the money goes: Sonnet extraction and nightly regeneration dominate. Verification on Haiku and gpt-5-mini costs cents.
- An all-Haiku pipeline would cost about $1–3 a month, but its attribution and stance quality is unmeasured; that is a golden-set question, not a budget one.
- *Latency:*
  - The fast lane makes one small call every 2–3 turns, asynchronous to the chat. The provisional anchor is fresh within about one turn; the per-call latency for Haiku 5.5 is unverified.
  - The slow lane waits for episode close (idle 30–60 minutes or chat end), then batch processing, which usually takes under an hour and at most 24. Verified cross-session items are usually ready within about 2 hours.
  - An "on-demand flush" over the standard API (2× cost) covers starting a new chat soon after the last one.
  - The human structure updates nightly.
- *Storage:* about 36K events a year at 100 candidates a day. That is trivial for SQLite.

---

## Options and trade-offs the design must decide

1. **Which model family verifies.**
   - A cross-vendor verifier (for example OpenAI) has the most independent errors (CAPA). But it needs a second API key and sends personal memory to a second provider, which bears on the personal-vs-work account question.
   - A same-vendor verifier on a different tier is simpler and less independent.
   - Middle option: cross-vendor only for high-risk events, after redaction.
2. **Citations API or structured outputs with code-checked offsets for J3.**
   - Citations guarantee valid pointers and are cheap on output, but they cannot be combined with structured outputs.
   - Option 1: a two-call design (cite, then structure).
   - Option 2: one structured call that emits message IDs plus quotes, with the substring check done in code (I2).
   - Measure both on the golden set.
3. **How far automatic application goes for high-risk operations** (supersede, merge, reorganize). Non-negotiable 3 sets the default to automatic. The question is how tight the blast-radius cap and the error-budget thresholds are, and whether a guardrail trip means "hold, visible" or "retry on another model". Neither may become a required review.
4. **How much the fast lane may influence the in-session anchor before verification.** More influence gives fresher anchoring; less gives fewer provisional errors in the chat.
5. **Model tiering per job.** Haiku 5.5 or Sonnet 5.5 for extraction, and whether thinking is on or effort is low. The golden set decides, not price.
6. **Batch vs standard for the slow lane,** and the episode-close rule: idle time, chat end, or an explicit signal from the adapter.
7. **Orchestrator technology.** A plain SQLite job table with Python (local-first, simple) or Temporal/DBOS (durable, heavier). For a single-user prototype, SQLite is likely enough.
8. **Where the maintainer runs.** A laptop that sleeps (missed capture windows) or an always-on scheduled host (cloud cost, data location).
9. **Where golden data comes from.** Synthetic personas (safe, too easy: round-1 note 09's Sim2Real gap) or a slice of the user's real conversations (realistic, but raises privacy and employer-account issues).
10. **Granularity of regeneration.** Per dirty node nightly, or on demand when a view is opened. This trades cost against staleness of the human structure.
11. **Error-budget numbers and freeze semantics.** These are initial guesses to calibrate in Stage 0 of the round-1 evaluation plan.

---

## Risks to the goal

- **R1. Non-negotiable 7 can be met only probabilistically.**
  - The architecture makes *structural* errors (provenance, quotes, speaker, instruction promotion, history loss, blast radius) checkable by code and effectively eliminable.
  - *Semantic* errors (stance, importance, what counts as a supersession, what to learn next) can only be bounded statistically.
  - Model errors are converging (CAPA), so some will pass every model-based layer. "Bounded, detectable, correctable" holds for structural errors and only approximately for semantic ones.
- **R2. Omission is the dominant failure and the hardest to detect.** It shows up only through canaries and heuristic sentinels, which sample. Missed AI explanations threaten non-negotiable 2 directly; missed decisions and goals threaten non-negotiable 5 (continuity).
- **R3. Stance may simply not be in the data.** About 82% of follow-ups carry no explicit feedback (round-1 note 08). Verification cannot create the evidence. Expect either false endorsement or a large share of AI-said items left at `encountered`. The second is safe but may weaken how much the "what has been learned" map can say about what the user actually holds.
- **R4. Prompt injection is contained, not solved.** Workers cannot act, but poisoned *content* can enter the core with its true origin label. If the AI-facing packs serve that content, chats can be pulled off the user's goal: the in-session and cross-session goals are exposed. Detectors fail under adaptive attack.
- **R5. Calibration without human labels is weak.** If the user never corrects anything, error-budget thresholds and verifier cascades are calibrated only on synthetic golden sets, which are known to be too easy. That is not a reason to require review (non-negotiable 1). It is a reason to expect the measured error rate to understate the real one.
- **R6. Cross-vendor verification and employer accounts.** The strongest independence measure sends personal memory to a second provider, possibly under a work account. This needs a user decision.
- **R7. The fast lane depends on near-real-time capture from Claude.ai and ChatGPT web,** which is a surface-adapter dependency outside this track. If capture is only possible through periodic exports, in-session focus cannot be served by maintained state. That would be a risk to non-negotiables 5 and 6.
- **R8. Model churn.** Retirements every 12–18 months force re-validation. Re-extraction with a new model atomizes text differently and can churn near-duplicates (round-1 note 08). Recorded outputs protect history, but not consistency going forward.
- **R9. Complexity is itself a reliability risk.** Twelve job types, six verification layers and twenty invariants are a lot of code. Every layer has to earn its place in ablation (round-1 note 09, item 8), or it is cut.

---

## Sources

Anthropic engineering and documentation
- Building Effective Agents (2024-12-19). https://www.anthropic.com/engineering/building-effective-agents
- How we built our multi-agent research system (2025-06-13). https://www.anthropic.com/engineering/multi-agent-research-system
- Effective context engineering for AI agents (2025-09-29). https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Building agents with the Claude Agent SDK (2025-09-29). https://claude.com/blog/building-agents-with-the-claude-agent-sdk
- Effective harnesses for long-running agents (2025-11-26). https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- Demystifying evals for AI agents (2026-01-09; partly via secondary summaries). https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- Citations (checked 2026-10-07). https://platform.claude.com/docs/en/build-with-claude/citations
- Structured outputs (checked 2026-10-07). https://platform.claude.com/docs/en/build-with-claude/structured-outputs
- Pricing (checked 2026-10-07). https://platform.claude.com/docs/en/about-claude/pricing
- Batch processing (checked 2026-10-07). https://platform.claude.com/docs/en/build-with-claude/batch-processing
- Model deprecations (checked 2026-10-07). https://platform.claude.com/docs/en/about-claude/model-deprecations

Long-horizon reliability and self-correction
- Sinha, Arun, Goel, Staab, Geiping, "The Illusion of Diminishing Returns: Measuring Long Horizon Execution in LLMs", ICLR 2026. https://arxiv.org/abs/2509.09677
- Laban, Hayashi, Zhou, Neville, "LLMs Get Lost In Multi-Turn Conversation", ICLR 2026. https://arxiv.org/abs/2505.06120
- METR, "Measuring AI Ability to Complete Long Tasks" (2025-03-19). https://metr.org/blog/2025-03-19-measuring-ai-ability-to-complete-long-tasks/
- Huang et al., "Large Language Models Cannot Self-Correct Reasoning Yet", ICLR 2024. https://arxiv.org/abs/2310.01798
- Tsui, "Self-Correction Bench", NeurIPS 2025. https://arxiv.org/abs/2507.02778
- Cemri et al., "Why Do Multi-Agent LLM Systems Fail?" (MAST), NeurIPS 2025 (consulted for verification failure modes). https://arxiv.org/abs/2503.13657

Verification and calibration
- Goel et al., "Great Models Think Alike and this Undermines AI Oversight", ICML 2025. https://arxiv.org/abs/2502.04313
- Farquhar, Kossen, Kuhn, Gal, "Detecting hallucinations in large language models using semantic entropy", Nature 630 (2024). https://www.nature.com/articles/s41586-024-07421-0
- Jung, Brahman, Choi, "Trust or Escalate: LLM Judges with Provable Guarantees for Human Agreement", ICLR 2025. https://arxiv.org/abs/2407.18370
- Mohri, Hashimoto, "Language Models with Conformal Factuality Guarantees", ICML 2024. https://arxiv.org/abs/2402.10978
- Shankar et al., "SPADE: Synthesizing Data Quality Assertions for LLM Pipelines", PVLDB 17 (2024). https://arxiv.org/abs/2401.03038
- Shankar et al., "Who Validates the Validators?", UIST 2024. https://arxiv.org/abs/2404.12272

Memory-maintenance failures and fixes
- HaluMem (Nov 2025), via round-1 notes 08/09. https://arxiv.org/abs/2511.03506
- Yang et al., "TrustMem: Learning Trustworthy Memory Consolidation" (2026-06-23). https://arxiv.org/abs/2606.25161
- Kwon, "Manufactured Confidence: How Memory Consolidation Turns Hearsay into Confident Facts" (2026-06-28). https://arxiv.org/abs/2606.29279
- Kerestecioglu et al. (Microsoft), "Human-Inspired Memory Architecture for LLM Agents" (2026-05-08). https://arxiv.org/abs/2605.08538
- Xiong et al., "How Memory Management Impacts LLM Agents: An Empirical Study of Experience-Following Behavior", ACL 2026. https://arxiv.org/abs/2505.16067
- Liu, "Memory Contagion: Cross-Temporal Propagation of Evaluator Bias via Agent Memory" (2026-06). https://arxiv.org/abs/2606.23195
- Lam et al., "Governing Evolving Memory in LLM Agents (SSGM)" (2026; conceptual, consulted). https://arxiv.org/abs/2603.11768
- Lin et al., "A Survey on Long-Term Memory Security in LLM Agents" (2026; consulted). https://arxiv.org/abs/2604.16548
- Zep changelog, "Deterministic entity dedupe and strict ontology extraction" (2026-07-09). https://help.getzep.com/changelog/2026/7/9
- Mem0 2026 ADD-only algorithm (vendor-reported; via round-1 note 08). https://mem0.ai/blog/mem0-the-token-efficient-memory-algorithm
- Zhang et al., "Agentic Context Engineering" (ACE), ICLR 2026, via round-1 note 03. https://arxiv.org/abs/2510.04618
- OpenAI Codex memories pipeline README (read 2026-10-07). https://github.com/openai/codex/blob/main/codex-rs/memories/README.md ; user docs: https://developers.openai.com/codex/memories

Orchestration, determinism, recovery
- Temporal, OpenAI Agents SDK integration docs. https://docs.temporal.io/develop/python/integrations/openai-agents ; announcement: https://temporal.io/blog/announcing-openai-agents-sdk-integration
- Thinking Machines Lab, "Defeating Nondeterminism in LLM Inference" (Sep 2025; via Willison's summary). https://simonwillison.net/2025/Sep/11/defeating-nondeterminism/
- Microsoft, Compensating Transaction pattern. https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction
- Google SRE Workbook, Error Budget Policy. https://sre.google/workbook/error-budget-policy/
- Manus, "Context Engineering for AI Agents: Lessons from Building Manus" (2025-07-18). https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus

Prompt injection
- Willison, "The lethal trifecta for AI agents" (2025-06-16). https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/
- Willison, on "Agents Rule of Two" and "The Attacker Moves Second" (2025-11-02). https://simonwillison.net/2025/Nov/2/new-prompt-injection-papers/ ; Meta: https://ai.meta.com/blog/practical-ai-agent-security/
- Beurer-Kellner et al., "Design Patterns for Securing LLM Agents against Prompt Injections" (2025). https://arxiv.org/abs/2506.08837
- Debenedetti et al., "Defeating Prompt Injections by Design" (CaMeL, 2025). https://arxiv.org/abs/2503.18813
- Hines et al., "Defending Against Indirect Prompt Injection Attacks With Spotlighting" (2024; consulted). https://arxiv.org/abs/2403.14720
- Louck, "Securing LLM-Agent Long-Term Memory Against Poisoning: Non-Malleable, Origin-Bound Authority" (2026-06-23). https://arxiv.org/abs/2606.24322
- Xu et al., "Memory Provenance Laundering in LLM Agents" (2026-07-31). https://arxiv.org/abs/2607.29167

Pricing (non-Anthropic)
- OpenAI API pricing (checked 2026-10-07). https://developers.openai.com/api/docs/pricing

---

## Review revisions (2026-10-08)

Changes from the adversarial design review. The full review record is `docs/design/REVIEW.md`.

| Finding | What changed |
|---|---|
| SEC-6 | Risk R6 heading renamed from "Cross-vendor verification and the employer-domain account" to "Cross-vendor verification and employer accounts". The text "possibly under a work account" is unchanged. Nothing else changed. |
