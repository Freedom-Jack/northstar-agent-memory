# Robust maintainer: orchestrator, Apply, workers, verifiers, model runtime, ops

**Status:** component design draft for adversarial review. Not approved. Nothing is built. Written 2026-10-08.
**Covers:** SPINE C11 orchestrator, C12 Apply, C13 workers, C14 verifiers, C20 model runtime, and C21 at the maintenance level.
**Serves:** GOAL §3.4 and §4.7 first; also §4.1, §4.2, §4.3, §4.5, §4.8 and the §6 criterion "maintains itself without babysitting".
**Inputs:**
- GOAL; SPINE (all IDs as defined there); TEXTBOOK §7–§9; SYN §3.1, §3.5, §7.4; [13]; [11] impl. 2 and 8.
- [GD §7–§8], [CD §4.2.7] and [OBS §4.7], for capture fidelity.
- Sibling designs `ai-in-session.md` (C10) and `ai-continuity.md` (C23), where they touch the maintainer.

**Labels:** (Unv) marks an unverified product fact and names the spike that settles it. A "starting value" is calibrated once after the pilot and then frozen (SYN §7).

---

## 0. Summary

1. **Code holds the state, schedule, invariants and write authority.** Models are stateless proposal functions with no network, no writes and no delegation ([13 §A]).
2. **One job table** (`jobs.db`) with fencing leases, I14 keys, SPINE's four outcomes (code faults and cancellations kept apart), ledger-side idempotency, a retry ladder that separates transport from quality failures, watermarks and ordered locks (§3).
3. **Two lanes, one runtime.** The fast lane (JF) runs in `northstard` and writes only session scope. The slow lane writes the ledger only through Apply. Both share the model port, recorder, routing and budgets (§2).
4. **A catalog of 24 slow-lane job types** (J12 gated off until UQ-10), plus governance of the 5 fast-lane jobs. Each has a trigger, code-assembled input (job card last), a role and model, an output schema, validators, a risk tier, an Apply rule and failure handling. The book's J7.1–J7.7 and J8.1–J8.3 are scheduled here, not redesigned (§4).
5. **Apply (C12) is the single canonical gate.** It checks fencing, freshness, freezes, invariants and whether the verification is enough for the op's risk tier. It then writes in one transaction. C16's publish gate guards only a projection (§5).
6. **Verification L0–L6 by risk tier, with concrete thresholds.** SD-21 family routing is a code filter in C20. SD-38 covers content that has no permitted verifier (§6).
7. **Local verifiers on this Mac** (the target class: an Apple-silicon Mac with about 48 GB of unified memory), pending S10: Qwen3.8-27B (V1), served by `northstar-modeld` on `run/model.sock` (runtime chosen by SP-3, MLX by default); Gemma 4 (V2) for merges, UQ-4b and the gold builder; Mistral Small 3.2 as eval judge. One resident at a time, within 24 GB. S10 uses Wilson bounds and per-speaker-family parity (§6.4–§6.5).
8. **Errors are held without the user:** quarantine with four automatic exits; 21 sentinels in one controller registry with automatic actions; budgets, including an omission budget, that trip freezes or re-routes with automatic exits; rollback checked by a canonical active-state projection; a nightly sandbox canary, live tagged canaries and a golden gate on every change (§7).
9. **Fault injection:** 23 faults. Each names what must be blocked (100% of structural errors) and a target detection time (§8).
10. **One shared cost model,** at prices checked today: about **$25 a month at 20 turns a day and $74 at 100** (±2×), on Profile A. SPINE §0 and §8.4 cite it (§9.6).
11. **Down or degraded:** capture and the fast lane never wait. The slow lane catches up from watermarks, and verification fails closed. Nothing asks the user (§10).

---

## 1. Scope and principles

**In scope:** job semantics, scheduling, the catalog, Apply, verification and routing, the local verifier, quarantine, sentinels, budgets, freezes, rollback, canaries, fault injection, the model port, cost, and degraded operation.

**Owned elsewhere:** steward, drift and goal-change logic (C10, `ai-in-session.md`); routing and packs (C23, `ai-continuity.md`); book compile internals (C16, TEXTBOOK §7–§8); reconciliation matching (C06, [GD §7]); evaluation protocols (C22, SYN §7).

**Principles**, each enforced by a mechanism below:
- **P1. Any single call can lose focus.** Structural correctness never rests on one call. Semantic correctness is bounded and measured (RISK 6).
- **P2. Code decides; models propose.** No model picks a job, writes a store or judges an invariant.
- **P3. Fresh call, full spec, job card last** ([13 F1, F2]).
- **P4. Outputs are recorded, never regenerated** ([13 F7]).
- **P5. Fail closed on authority, fail open on capture.**
- **P6. Nothing waits on the user.** Every hold has an automatic exit.

---

## 2. Two lanes, one runtime

| | Fast lane (JF) | Slow lane (J1r–J11) |
|---|---|---|
| Process | `northstard` (C10, C23) | `northstar-maintainer` (C11–C14, C16, C08) |
| Jobs | JF.1 steward, JF.2 goal change, JF.3 drift judge, JF.4 goal router, JF.5 re-explanation detector | §4 |
| Scheduler | In-process queue per (session, branch). Windows are never skipped (`ai-in-session.md` §4.5) | `jobs.db` with leases (§3) |
| Writes | `session.db` through the C10 applier, session scope only | `ledger.db` through C12; `book.db` through C16 |
| Authority | Provisional; I22 holds | Long-term, after verification by tier |
| Idempotency | (handle, branch, turn, message hash) | I14 key (§3.3) |
| Recorded outputs | `session.db` `fast_model_call` rows (D1; CDM D-7) | `jobs.db` `model_call` rows |
| Checks | Applier validators on 100% of ops; J10a audit; steward budget | Apply; L0–L6; quarantine; budgets; rollback |

**JF modes.** C11 sets the mode from the steward budget (§7.3); C10 applies it. Modes apply per connector tier; desktop L0/L0+ is a tier (R13).

| Mode | Entered when | Behaviour | Exit |
|---|---|---|---|
| Normal | Default | As in `ai-in-session.md` | — |
| Degraded | The provider is down, or the reject rate is above 20% over 10 windows | Steward runs on its alternative (`ai-in-session.md` §4.5) | The primary runs in shadow on live windows (recorded, never applied); exit after 10 shadow windows within budget, scored by J10a |
| Frozen | Steward budget tripped (J10a precision below 95% per connector tier), or the steward canary regresses | Pin from the last validated state. Only deterministic goal-change rules and tier-0 checks run. Turns are marked `steward_gap`, and J10a fills them | The steward runs in shadow on live windows; exit when the steward canary passes and 3 consecutive J10a audits of shadow windows are within budget |

**Lane disagreement.** At each window close, C10 emits `window.closed{handle, branch, window_id, turn_range, reason, active_item_ids[], spans[]}` through the outbox (SPINE §6.3); `session.ended` marks only the lifecycle end. J3 extracts from the spans, never from session items (SPINE §5.5). Code compares the two lanes (§7.2 #5).

---

## 3. The orchestrator (C11)

### 3.1 Job record and outcomes

A job row in `jobs.db` has these fields:
- `job_id` (ULID), `type`, `lane` (slow, book, audit, repair, sandbox), `priority`;
- `idem_key = sha256(type, schema_v, inputs_hash, prompt_hash, route_key)`;
- `inputs {refs[], as_of watermark, inputs_hash, item_versions}`, `locks[]`;
- `epoch`: the fencing counter, raised by one on every claim (§3.2);
- `state`: queued, leased, calling, awaiting_batch, validating, awaiting_verify, held, applying, succeeded, succeeded_no_output, failed, failed_code, quarantined, cancelled. The `jobs.db` DDL ([CDM] SQL) must list exactly these states;
- `lease {owner, leased_at, expires_at}`;
- `attempts {transport, quality, routes_tried[]}`, `next_run_at`;
- `outcome`, `outcome_reason`, `config_version` (I19);
- `tenant_id`, `account_ref`.

| Terminal state (SPINE §5.2) | Meaning |
|---|---|
| `succeeded` | At least one op applied, or a book block published |
| `succeeded_no_output` | A valid empty result. Allowed only if the omission sentinel finds no cues; otherwise J11x runs on another model |
| `failed` | Should not run, for a reason other than output quality: inputs excised, superseded by a newer job, or the schema retired |
| `failed_code` | An FK or trigger abort inside Apply: a code fault, never a quality failure (§5.2) |
| `quarantined` | Output quality still failed after the retry ladder (§7.1) |
| `cancelled` | Cancelled by a rollback, an excision or a freeze action before it applied |

`failed_code` and `cancelled` are sub-cases of SPINE's `failed`, kept apart so code faults and cancellations never count as quality failures.

Transport and provider failures are never outcomes. The job goes back to `queued` with backoff.

### 3.2 Leases and fencing

- **Claim.** `UPDATE … SET state='leased', epoch=epoch+1 WHERE state='queued' OR (state is non-terminal AND the lease has expired or passed its maximum age)`. It becomes `SKIP LOCKED` on Postgres later (SPINE §7.5).
- **Reclaim.** Any non-terminal job whose lease expired is reclaimed, whatever state it reached (`calling`, `validating`, `applying` and so on). Jobs that wait with no lease (`awaiting_batch`, `awaiting_verify`, `held`) are not touched.
- **Lease length.** The TTL is 2× the type's p95 runtime, and at least 2 minutes. A heartbeat runs every TTL/3. Batch calls wait in `awaiting_batch` with no lease, and a collector polls them.
- **Maximum age.** A lease has a maximum age (start: 6× the job type's p99 run time). Past it, the lease is reclaimed even if heartbeats continue, so a hung worker cannot hold a job.
- **Fencing.** Each proposal carries its epoch. Apply rejects stale epochs, so a process that slept past its lease cannot write.
- **Boot.** Expired leases are re-queued. A recorded output for (job, attempt, call) is reused, never paid for twice.

### 3.3 Idempotency

- **Jobs:** `idem_key` is unique. It is I14's tuple plus the prompt hash and the route key. A re-run after a prompt fix is a new job; a duplicate trigger is a no-op. This `idem_key` (with `prompt_hash` and `route_key`) is the only job key across documents.
- **Ops:** ledger events carry a unique (`proposal_id`, `op_index`).
- **Across files:** SQLite in WAL mode has no atomic commit across files. The ledger is the truth for "applied". On boot, jobs left in `applying` are reconciled with it (below).

**Ledger-side idempotency.** Each Apply transaction writes `applied_job(job_id, proposal_id, output_hash)` in `ledger.db`. Apply refuses a proposal for a job that already has an applied row under a different `proposal_id`; held ops of the same proposal still apply later (P3 re-validation, §3.7). Boot reconciliation keys on `job_id` as well as `proposal_id`. `jobs.db` runs at `synchronous=FULL`. The nightly sweep adds a ledger→jobs orphan check.

### 3.4 Retry ladder and backoff

| Failure | Kind | Action |
|---|---|---|
| 429, 5xx, timeout, network failure, batch expiry | Transport | The SDK retries twice. Then the job is re-queued with backoff of 30 s × 4ⁿ plus jitter, capped at 6 h. A provider's circuit breaker opens after 5 failures in 10 minutes and probes every 5 minutes |
| Invalid schema, validator fail, J4f fail, refusal, `max_tokens` cut | Quality | Attempt 2 is a fresh call on the same route. Attempt 3 is a fresh call on the role's alternative model. Then the job is quarantined |
| Budget exhausted | Neither | Wait for budget (§9.5) |

A fresh call never contains the failed output. It may name the rule IDs that failed ([13 F2]).

### 3.5 Watermarks

| Watermark | Compared with | Lag sentinel |
|---|---|---|
| Intake sequence per source | Window-close cursor | A closed window not segmented after 1 h |
| Connector capture watermark | Session turn counts; observer or export counts | Capture gap (§7.2 #9) |
| Ledger outbox sequence | Consumer cursors (C08, C15, C16 just-in, C11) | Any consumer more than 15 minutes behind |
| Verified watermark | Window close times | p95 above 2.5 h (derived from TEXTBOOK T-FRESH: 95% of new leaves in "Just in" within 3 h); see §7.2 #12 |
| Audit watermark | Applied high-risk events | Any unaudited after 36 h |
| Config watermark | Last canary-passed config | The running config has not passed the canary |
| Printing and edition | Dirty set | TEXTBOOK §8.12 |

### 3.6 Single-writer locks

Stores keep one writer each (SPINE §6.1). Locks stop conflicting proposals on one scope from being computed in parallel, and Apply's freshness check (§5.2) catches the rest.

Locks are taken in a fixed order, which prevents deadlock: `global.excision` (C19; drains leases, blocks all but capture) → `global.migration` → `book.edition` (J8; blocks J7.6) → `book.printing` (J7.1, J7.6; blocks J8.3) → `concept:{sorted ids}` (J5 merges and supersessions, J8c, J11r) → `episode:{id}` (J2, J3, J11x). Locks have leases and epochs. Per-session serialization stays in C10.

**Global locks** carry `lease_expires_at` and `epoch`, renewed by the holder's heartbeat. A stale holder's lock is recovered; for `excision`, the saga resumes from its last step ([CDM] §10.2). Scope locks are never held across `awaiting_batch` (§4.5).

### 3.7 Scheduling

| Trigger | Starts |
|---|---|
| A window closes: the `window.closed` event | J2 → J3 → J4f → J5 |
| Verbatim text arrives for a model-reported window (C06 reconciliation) | J1r, then J3 re-derivation |
| `session.opened` is routed to a window not yet applied | **Flush:** that chain moves to P1 on the standard API |
| `ledger.committed(wm, types)` | J9a; J5 for new items; J4c for new checkable claims; J7.0; J7 dirty marks |
| `correction.applied` | J7 dirty marks; J11p if a page fails its check |
| Cron (local time) | 02:00 canary; 03:00 printing; 04:00 L4 audit and J10f; 05:00 quarantine exits; Sunday 05:30 J8c, then J8, then J12 if UQ-10 is on. J8 also follows the growth regime of [TB] §7.3 (§4.5) |
| `budget.tripped`, or a sentinel action | Freezes; J11 |
| A new config version (prompt, model, threshold, runtime, code) | J10c golden gate before activation; J11m |
| A retirement notice (60 days or more) | J11m |
| Boot or wake | Lease recovery; batch collection; catch-up (§10) |
| `excision.begin(targets)` and `excision.done(target)` from C19 | Drain and pause; each store's writer purges its own rows through its `ExcisionPort` (C11 `jobs.db`, C08 `index.db`, C16 `book.db`), while C19 writes `ledger.db` directly (§5.2); resume |

**Priorities**, highest first: P0 repair and freeze actions; P1 flushes and fast-lane fallback on the local slot; P2 J1r and the J2–J5 chain; P3 `awaiting_verify` and held re-validation; P4 J7; P5 J10; P6 J8, J8c, J12, J11x backlog, J11m; P7 C22 sandbox. A waiting job moves up one class every 6 hours, never above P1.

**Concurrency:**
- At most 4 standard-API calls at once.
- One batch per (provider, model, role), sent every 10 minutes or when 50 calls are ready.
- A 1-hour cache on the charter, because batches can outlast 5 minutes.
- **One local-model slot.** Its order is: fast-lane fallback, the drift re-judge, P3 slow-lane verification (J4f), J10a, entailment, canary, eval. The embedder is outside the slot queue (§6.4).
- **Slot admission.** Fast-lane fallback and high-tier ops are admitted first. Low-tier and evaluation work run within a daily budget of slot time.

**Other rules:**
- **Missed schedules** (the Mac was asleep) run once on wake.
- **On battery or under memory-pressure "warn",** local jobs at P3 and below wait. Remote batches still run.

### 3.8 Book jobs under the orchestrator

TEXTBOOK §8.1 fixes the pipeline. This design only schedules it.
- J7.1 and J7.6 take `book.printing`.
- J7.4 and J7.5 run as one job per dirty block, in parallel, under `block:{page,block}`.
- J8.1–J8.3 run under `book.edition` on the growth regime of TEXTBOOK §7.3 (§4.5): a bootstrap edition, daily for 14 days, then weekly. A held edition retries at the next scheduled run (TEXTBOOK §7.3).
- The book budgets (TEXTBOOK §8.8) run in C11's budget engine.
- J7.4 outputs are recorded in `jobs.db`.

---

## 4. Job catalog

### 4.1 How every input is assembled

The order is fixed, with a cached prefix first and the job card last ([13 §H]):
1. **Charter.** The non-negotiables and invariants in plain words, plus "abstain when unsure". C15 builds it from versioned configuration (I19).
2. **The output schema,** and the rule IDs the job is judged by.
3. **Data, as delimited and untrusted blocks.**
   - Messages are addressed by `message_id`, with speaker, fidelity and origin rendered by code.
   - Northstar blocks are marked so they cannot be cited (I24).
   - Data is read at a snapshot watermark. Re-processing reads the store as of the episode's time.
4. **Active corrections** on the inputs (I21).
5. **The job card:** one deliverable, the rule IDs, the schema, and "abstain rather than guess". It may name rules that failed before, but never the earlier output.

Assemblers are typed:
- J7 gets leaves only (I7, B2).
- J3 gets source blocks and neighbour gists, never page text.
- No worker sees another worker's reasoning or an earlier verdict ([11] impl. 8).

### 4.2 Proposal and verdict envelopes

```yaml
proposal: {proposal_id, job_id, epoch, schema_v, model, prompt_hash, as_of,
  ops: [{op: ADD_ITEM|REVISE_ITEM|ADD_ATTRIBUTION|SET_LINEAGE|ADD_STANCE|ADD_RELATION|SET_AGENDA_STATUS
            |SUPERSEDE|OPEN_TENSION|SAME_AS|UNMERGE|SPLIT_CONCEPT|REPARENT|RESOLVE_TENSION|SET_VERIFICATION
            |ADD_EPISODE|FIDELITY_UPGRADE,
         target?, payload, evidence: [{message_id, quote}], confidence}],
  misfits: [{item, concept, kind: contradicts|does_not_fit, evidence: [{message_id, quote}]}],   # J5 only
  abstentions: [{message_id, reason}]}
verdict: {verdict_id, target: {proposal_id, op_index}, layer: L1|L2|L3.s1|L3.s2|L3.s3|L4|L4.second,
  verifier: {model@digest, family}, independent_of_worker, independent_of_speaker,
  rules: [{rule: entailment|attribution|hedge|gist|qualifier|direction|scope, result: pass|fail|abstain, quote?}],
  confidence, threshold_set}
```

Workers set no grouping. Apply derives atomic groups in code (§5.2).

**Op → ledger event map.** CDM §2.2 is the event authority; Apply writes only these names (CDM row numbers).

| Op | CDM §2.2 event |
|---|---|
| `ADD_EPISODE`; `ADD_ITEM`; `REVISE_ITEM` ("refine") | `episode.segmented` (12); `item.created` (14), with `span.anchored` (9), `concept.created` (21) or `agenda.created` (23) as needed; `item.revised` (15) |
| `ADD_ATTRIBUTION`; `SET_LINEAGE`; `FIDELITY_UPGRADE` (J1r) | `attribution.added` (17); `attribution.lineage_set` (18); `attribution.added` with `recon_id` (CDM D-5) |
| `ADD_STANCE`; `SET_VERIFICATION`; `SET_AGENDA_STATUS` | `stance.recorded` (19); `verification.recorded` (20); `agenda.status_changed` (24) |
| `ADD_RELATION`; `SAME_AS` | `relation.recorded` (27), plus `agenda.answer_linked` (26) for `answers`; `concept.aliased` (22), or a `same_as` relation for items |
| `SUPERSEDE`; `OPEN_TENSION`; `RESOLVE_TENSION` | `supersession.applied` (29); `tension.opened` (30); `tension.resolution_recorded` (31), with `supersession.applied` and the loser's `item.status_changed` (16) when a side wins (CDM §7.2) |
| `UNMERGE`; `SPLIT_CONCEPT`; `REPARENT` (J8c) | `concept.alias_reverted`; `concept.split` (22); `concept.reparented`, which CDM adds under X10 (high tier; I12, I21) |
| C14 verdicts; J11r compensations | `item.gist_verified` (15), `relation.direction_checked` (28); §7.4, all under one `compensation.batch` (37) |

`misfits` are not ledger events. After Apply commits the J5 proposal, C08 writes each one that passes L0 (IDs exist; I1, I2) as an `anomaly_mark` row in `index.db` for J8c (TEXTBOOK §7.9). A rebuild re-reads them from recorded proposals in `jobs.db`.

### 4.3 Risk tiers

| Tier | Ops | Needed before Apply | After Apply |
|---|---|---|---|
| **Low** | Passage shell or gist; an AI-said statement held by the assistant with no stance ("encountered"); tags; a `reported` or inferred Agenda item (I22); a suggested topic (J12, while UQ-10 is on); relations `explains`, `example_of`, `applied_in`, `defines`; fidelity upgrade | L0 + L3 stage 1. If the verifier is down, the op applies as `l2_pending` | L4 on 5%, and on 100% of `l2_pending` ops |
| **Medium** | Verbatim user statement or decision; refine; stance `asserted` or `accepted` with a user span; relations `supports`, `rebuts`, `undercuts`, `answers`, `advances_goal`, `compares`, `part_of`, `prerequisite_of` (direction checked); new concept; a verification change other than `contradicted` | L0 + L1 + the L3 cascade | L4 on 5% |
| **High** | Supersede; merge or unmerge; split; re-parent; stance `endorsed`; an explicit goal created or changed (verbatim user span); a question answered; a tension resolved; `contradicted`; J8c; J11r | L0 + L1 + L2 at full effort, with the family rule. A merge also needs an identity key, or V1 and V2 to agree (I12) | L4 on 100% within 24 h; 2% budget |

### 4.4 Catalog: from capture to the core

The ladder (§3.4) and quarantine (§7.1) apply to every job. The "Failure" column lists only what is specific to each job.

| Job | Trigger | Inputs | Role → Profile A | Output | Validators beyond L0 | Tier, Apply | Failure |
|---|---|---|---|---|---|---|---|
| **J1r Reconcile** | C06 links verbatim text to a model-reported window | Reconciliation records; the window's items and ops | Code | `FIDELITY_UPGRADE` to `reconciled`; `SUPERSEDE` with reason `reconciled_absent`; a re-derivation plan | The quote matches the normalised verbatim text; the join is active and confident (RISK 24) | Low (supersedes are high). C12, then J3 on the verbatim window, a re-steward request to C10 ([GD §7]) and J10a | An ambiguous match stays unlinked and counts in copy fidelity |
| **J2 Segment** | A window closes | Addressed blocks; the charter | `segmenter` → Haiku 5.5 batch | Episode boundaries on message IDs. **Code** adds a Passage shell for every assistant span and reported AI point (SD-34) | Contiguous, non-overlapping, covering | Low; C12 | Code fallback: one episode per window |
| **J3 Extract** | An episode is applied | Episode blocks; up to 20 current neighbour items (as of the episode); corrections | `extractor` → Sonnet 5.5 batch | Candidates: role, kind tags, text, gist, evidence, holder, stance, modality, `hedge_verbatim`, certainty, qualifiers, concepts, `primary_concept`, checkability, agenda fields; `offer` and `learning_suggestion` tags. **No speaker field**. Model-reported capture: below | I1, I2 (quote within one message), I3, I4, I5/I22 (model-reported goals become `reported` Agenda items), I10, I16, I17, I20, I24; passage kind tags present; a `learning_suggestion` links a concept; at most 60 ops | Per op; C12 after J4f | `succeeded_no_output` with omission cues → J11x on the alternative model. An over-cap window is split, never discarded (below) |
| **J4f Fidelity check** | An op from J3, J5 or J8c passes L0 | One op, its spans ±2 turns, the rubric | `verifier` → V1 cascade | A verdict per rule | Family rule (§6.2); quotes resolve | L1–L3 by tier. The verdict is attached; Apply decides | If the verifier is unavailable → `awaiting_verify` (§10) |
| **J4c Claim check** (AD14) | A checkable world claim from any speaker; `recheck_after` is due; a new supports or rebuts link; the J5t margin rule | The claim; its span; linked items of independent lineage (I11). Web evidence only if UQ-18 is yes | `verifier` (claim mode) → V1 | `SET_VERIFICATION {status, evidence_kind: internal|parametric|web, evidence_refs, recheck_after}` | `contradicted` needs evidence of independent lineage, so parametric judgement alone can never contradict; never upgraded by acceptance (AD14) | Medium; `contradicted` is high and goes through J5t | No permitted family → `no_independent_verifier` (SD-38) |
| **J5 Link and resolve** | J3 items applied; at window close, also `LinkCandidate`s and code-made `goal_stack` links (`ai-continuity.md` §4.4) | Items; their top 8 neighbours by FTS and embeddings, with gists; must-link and cannot-link | `linker` → Sonnet 5.5 batch | Relations; `SAME_AS` with key evidence; supersessions `{reason, causal_alternative_ref}`; tensions; `misfits` {item, concept} for leaves that contradict or do not fit their concept's key idea (§4.2) | I11, I12, I21; reason enum; `ai_self_correction` needs a later span by the same agent; a reversal after pushback with no new evidence becomes a tension (SYN §3.1) | Per op; C12 | — |
| **J5t Tension resolution** | A new tension, or new evidence on one | Each side's recorded axes | Code (AD19 order), with J4c for margin cases | `RESOLVE_TENSION`, or `contested` plus a spawned question | Reversible | High; C12 | The residue is monitored (RISK 22) and never routed to the user |

**J3 on model-reported capture** (desktop L0/L0+; ARCH R14; BOOK-2, CONS-4):
- One item per reported `explanation` or `example` point, with `primary_concept` set.
- One passage per reported `body`.
- `this_reply_points` are handled as the same reply's points.

**J3 tags.** J3 tags an `offer` (a reflexive "want me to…?"; never placed on the frontier) apart from a `learning_suggestion`, which must link a concept (BOOK-10).

**Dense windows.** A window over J3's op cap, or over the steward's V12 limit of 12 ops, is split into sub-windows and re-run. It is never discarded whole.

**J5 update-omission probe** (MR-1). For a sample of applied items (start: 20%), code queries FTS and embedding neighbours on the same concept that have no relation to the item. Pairs with the same subject and a differing value or qualifier go to J5 on the alternative linker. Results feed sentinel #15.

### 4.5 Catalog: structure and book

| Job | Trigger | Role → Profile A | Output; checks | Writes; failure |
|---|---|---|---|---|
| **J7.0 Just in** | `ledger.committed` | Code (C16) | The rail (TEXTBOOK §7.1); B14 | `book.db` |
| **J7 Printing** (J7.1–J7.7) | Nightly, over the dirty set | `book_writer` → Sonnet 5.5 batch; `entailment` → V1 | BlockVersion; V1–V15, B1–B16; entailment on 100% of new sentences; L4 on 5% of blocks plus every big picture | C16 publish gate; extractive fallback (TEXTBOOK §8.7) |
| **J8c Concept reorganization** | Weekly, before J8; split candidates from anomaly marks (C08, from J5 `misfits`) | `reorganizer` → Sonnet 5.5 batch, over the concept subgraph, duplicate candidates, anomaly marks and corrections | `SAME_AS`, `SPLIT_CONCEPT` (a partition with labels), `REPARENT`; I12, I13 (at most 20 concepts a week), I21; a split covers every member. High tier, L4 100% | C12. Freshness per op, re-queue limit and cap overruns: below |
| **J8 Edition** (J8.1–J8.3) | The growth regime of [TB] §7.3: a bootstrap edition after the first printing with pages and after any export backfill; daily for 14 days; then weekly | J8.2 `labeler` → Sonnet 5.5 batch | Edition; B5–B10; churn budget | C16; held and retried |
| **J9a Index refresh** | Outbox | Code (C08) | `index.db`; I18 | Rebuilt from the ledger on a hash mismatch |
| **J9b Artifact invalidation** | Outbox | Code (C15, `northstard`) | Dirty artifacts | The pin serves the last validated state |
| **J12 Suggested topics** (gated) | **Off until the user answers yes to UQ-10** (versioned flag, I19). When on: weekly after J8, for active goals with fewer than 3 frontier items (starting value) | `topic_suggester` → Sonnet 5.5 batch, over the goal, its target concepts with labels and frontier, existing suggested topics and `hide` corrections; never page text (I7) | `ADD_ITEM` → `agenda.created` kind `suggested_topic`, origin `northstar_authored`, `northstar_output` source (CDM D-4). Family rule: its relevance-and-label check (L3 stage 1) runs on a family other than the suggester's (§6.2); lineage counts zero (I11). L0, the CDM CHECK (no authority, never shown as learned), at most 3 per goal a week (I13), I21. Low tier | C12; abstain → nothing |

**J8c freshness, locks and caps** (MR-10):
- **Freshness per op.** Apply checks each op against current state. Only ops whose own targets changed are re-based; the rest apply.
- **Re-queue limit.** Freshness re-queues are counted per job. After 2, the job re-runs on the standard API under short locks.
- **Locks.** Scope locks are never held across `awaiting_batch`.
- **Cap overruns.** An overrun up to 2× the I13 cap applies the top N ops by evidence and defers the rest to the next run. Above 2×, the whole job is quarantined. Every overrun is counted (sentinel #17).

### 4.6 Catalog: audit, repair, calibration

| Job | Trigger | Inputs; role → Profile A | Output → effect |
|---|---|---|---|
| **J10a Session audit** | Every 10 verbatim turns, or every 10 recorded calls at desktop L0/L0+ on the model-reported window (R13); session end; after J1r at L0; on the local verifier; it checks the steward's and Goal-Change Handler's reading, not copy fidelity; path-B sessions are reported "no audit" | The raw window and the overlapping pair; IDs and gists, never current judgements ([11] impl. 8). `session_auditor` → V1, a family other than the steward's (`ai-in-session.md` §4.6); Sonnet 5.5 batch as alternative | Re-derived ops → `session.audit_result` to C10, which applies `MARK_CONTESTED` and omissions as actor `audit`. High-impact disagreements are tie-broken by V2, otherwise left contested |
| **J10b L4 audit** | Daily | A 5% random sample; all high-risk events; all `l2_pending` ops; all ops released from a freeze or quarantine. Leaves, spans, proposals and verdicts, 5 events per call. `auditor` → Opus 5.5 batch, plus `auditor_second` | Each event judged `correct`, `error{kind}` or `uncertain`. A confirmed error → J11r, then J11x; a confirmed error on a Tension resolution records the dissent as a resolution input and re-resolves at step 5 (contested, spawned question, `next_recheck`; [CDM] §7.2). Metrics go to the budgets |
| **J10c Golden and canary** | Nightly, and before any config activates | Sandbox stores (§7.5), on production routes | C22 → `canary.result` → C21. Feeds freezes and gates |
| **J10d Sentinel sweep** | Every 15 minutes; a nightly replay check | Metrics, watermarks, state hashes (code, C21) | Sentinel states in `ops.db`; actions to C11 |
| **J10e Threshold recalibration** | **Dropped for the prototype** | — | Thresholds change only through committed, golden-gated bundles at stage gates (I19; D4) |
| **J10f Coverage audit** (episode level) | Daily; samples windows, not events (start: 5 a day) | The window's addressed blocks, without the applied items. `session_auditor` → V1 (family rule, §6.2), blind to what was applied | The auditor lists the items and updates the window should have produced; code matches the list against applied state. Misses feed the omission budget (§7.3) |
| **J11r Rollback** | A confirmed error; a freeze that lines up with a change; a replay violation | A selector (code) | Compensating events through C12; rebuild; projection check (§7.4) |
| **J11x Re-extraction** | Quarantine route 2; an omission hit; after a rollback; a fix released | The window ±N turns in the as-of sandbox; `extractor` on its alternative model | A diff, applied by C12. At most 3 attempts per window in 7 days |
| **J11q Quarantine exits** | Daily | Code, plus J4f and J11x | Release or `discarded` (§7.1) |
| **J11m Model migration** | A retirement notice, or a newly pinned model | The golden set plus 50 real windows as of their time, never applied | The config pointer switches only if no metric degrades beyond tolerance |
| **J11p Page repair** | A page fails the correction check (TEXTBOOK §9.4) | C16 | The page is shown in extractive form |

---

## 5. Worker contract and the Apply gate

### 5.1 Worker contract (C13, C14)

1. **Stateless.** One fresh call per attempt, with no memory and no reused conversation.
2. **No network, no writes, no delegation, no tools.** The output is only a schema-constrained proposal or verdict. Any retrieval is done by code beforehand (Rule of Two, [13 §G]).
3. **Input assembled by code** (§4.1). The worker never chooses what it reads.
4. **Schema mode per provider** (§9.3), plus client-side checks for what schemas cannot express (I15).
5. **Recorded before parsing,** with route, prompt hash and inputs (§9.4).
6. **Retried on a fresh call or another model** (§3.4). A failed output is never fed back.
7. **No authority from content.** Imperatives are data (I5). Speaker and origin come from code (I3, I20).
8. **Workers can never read or change** prompts, invariants, golden sets, thresholds or permissions (I19).
9. **CLI providers are opt-in only and isolated** (SPINE §8.5 rule 6; I24).

### 5.2 Apply (C12): the single canonical gate

For each proposal, in order:
1. **Fencing.** The epoch is current and the job is not cancelled.
2. **Freshness.** Every input item version still matches the snapshot. If not, the job is re-queued with fresh inputs; this counts as no failure. J8c checks freshness per op (§4.5).
3. **Freeze.** A frozen (type, tier) sends the op to `held` (§7.3).
4. **L0 checks and closures** (§5.3). Apply groups ops into dependency closures in code: ops that reference an ID minted in the same proposal, or touch the same subject, form one closure, applied or held as one unit at the highest tier inside it. An op that fails L0 is rejected with reason codes, with the rest of its closure; other closures still apply. A job that breaks the blast cap is quarantined whole (I13; J8c overruns: §4.5).
5. **Verification for the tier** (§4.3). A medium or high op without a verdict → `awaiting_verify` (parity hold); a low op applies as `l2_pending` (§4.3). A failed verdict → quarantine. A release from quarantine (§7.1 exit 4) re-enters at step 6, flagged for 100% L4.
6. **Write.** `BEGIN IMMEDIATE`, then the typed events, state tables, the `applied_job` row (§3.3) and outbox rows, then commit. One transaction per proposal.
7. **Notify.** Emit `ledger.committed`. Rejections and quarantine records go to `jobs.db`.

**Code faults.** An FK or trigger abort inside Apply is a code fault: the job goes to `failed_code`, sentinel #6 fires and the producing job type freezes. It never counts as a quality failure.

The same gate takes corrections from C18 (actor `user`), J1r reconciliations and J11r compensations. Proposals tagged `canary` (live canaries, §7.5) run through a shadow Apply: the same code against a scratch ledger, never the real one, and never quarantined. The catch result goes to `jobs.db`.

Apply never edits or deletes. Excision is the one exception (PL §6.7 X5, PL-11). C19 orchestrates it under the global lock and writes `ledger.db` directly (the SPINE §6.4 rule 3 exception), ending with the ledger event `excision.applied`. Every other store's purge is implemented and executed by that store's own writer through its `ExcisionPort`, so single writers hold.

### 5.3 What L0 checks (code, on 100% of proposals)

| Area | Checks |
|---|---|
| Provenance | **I1, I2:** every quote resolves to a span and is an exact substring after NFC and whitespace normalisation. **I24:** no quote falls inside a `northstar_*` range |
| Attribution | **I3, I20:** speaker, origin and fidelity are copied from capture; model-supplied values are ignored and logged. **I4:** `endorsed` or `accepted` needs a user span. **I11:** echo lineage never counts as support |
| Authority | **I5, I22:** instructions, preferences, goals, constraints, endorsements and active corrections only come from `user_typed` verbatim spans; anything else is rewritten to `reported` or provisional, or rejected. **I21:** nothing contradicts an active correction. For hook-channel spans, long-term authority also needs `observation.origin_confirmed` (not `confirmed_degraded`); a later `not_confirmed` triggers a compensation under one `compensation.batch` ([HK] §8; [CDM] §3.1) |
| Shape | **Endpoints:** every relation endpoint exists (an item, relation or episode). **I6:** append-only event types, with no update path. **I9:** a coverage drop needs a recorded cause. **I10:** the hedge lexicon caps certainty. **I12:** a merge needs a key or V1+V2. **I13:** caps per job. **I14:** unique ops. **I15:** client-side bounds. **I16:** temporal order. **I17:** scope inherited; egress checked in C20 |
| Elsewhere | **I7, I8:** the J7 assembler and C16. **I18:** J10d replay. **I19:** the config is canary-passed. **I23:** routing reads capability levels and `speaker_model_family` only (lint) |

---

## 6. Verification (C14)

### 6.1 Layers L0–L6

| Layer | Runs on | Mechanism | Pass rule |
|---|---|---|---|
| **L0** | Everything | Code (§5.3) | Every check passes |
| **L1** | Fields on medium and high ops: holder, stance, kind, relation type, direction | V1 labels each field from the span alone, blind to the worker's value (temperature 0.7, fixed seeds): 3 labels on high ops; on medium ops 3, or 1 only if the golden set and budgets show no loss ([EV] §2.4 ablation) | At least 2 of 3 agree with the worker (or the single label agrees). Otherwise the field goes to its safe default (assistant, no stance, relation not applied) and is marked `uncertain` |
| **L2** | Every J3, J5 and J8c op | A fresh V1 call that audits "another agent's proposal" against the span ±2 turns, rule by rule: entailment, attribution, hedge, gist, qualifier, direction | Every rule passes, with a quote. This avoids the 64.5% self-correction blind spot ([13 F2]) |
| **L3** | The L2 call, run as a cascade | Stage 1: V1 with thinking off. Stage 2, if confidence < τ1: V1 at high effort. Stage 3, if still < τ2: a permitted remote family (Profile B only). Else abstain | τ is calibrated (Trust or Escalate) so that false accepts stay ≤ α with 95% confidence on the golden set: α = 10% for fidelity, 5% for entailment. An abstain applies a low op as `l2_pending` and quarantines a medium or high op |
| **L4** | J10b | Opus 5.5 checks against the leaves. Every disagreement, and 20% of agreements, also gets a second opinion from a route that did not gate the op: V2, or a permitted remote family. V1 at high effort never confirms ops it passed at full effort. Claude-said content gets a 100% second opinion while SP-MT-2 shows V2 has capacity, else 50%, reported | A **confirmed error** needs Opus and that second opinion. Opus-only verdicts count toward a "probable error" budget (start: 2× the audited budget) with its own trip. Audited error is reported per speaker family. Audit disagreement must stay ≤ 5%. The 20% sample measures misses that Opus and the workers share (RISK-MT-2). No two-rater latent-class estimate is made; one is added only with a third rater |
| **L5** | Nightly canary; golden gate | Sandbox replay (§7.5) | No metric worse than its margin |
| **L6** | Optional user corrections | Each becomes a label (kind, target, the job that produced it) | Counts against the budget; feeds the threshold bundles at stage gates (J10e is dropped, §4.6) |

**Omissions.** L0–L4 judge ops that exist. J10f (§4.6) audits whole windows for items and updates that were never proposed, and feeds the omission budget (§7.3).

### 6.2 Family routing (SD-21)

```
permitted(op) = all families − {family of the worker that proposed op}
                             − {speaker_model_family of every AI span op rests on}   # agent registry (I23)
route(role, op) = the first model in profile[role] that is certified (§6.5), in permitted(op),
                  allowed by C19 egress, healthy and within budget
merge (I12)     = an exact identity key, or passing verdicts from two permitted families (V1 + V2)
none            → NoPermittedRoute (§6.3)
```

| Content | Excluded families | Default |
|---|---|---|
| Claude-said, user-said | anthropic | V1 (`local:qwen`) |
| ChatGPT- or Codex-said, or restated by both vendors | anthropic, openai | V1 |
| Said by a local Qwen model through any connector | anthropic, `local:qwen` | V2 (`local:gemma`) |
| Concept merge | The worker family and every speaker family | V1 + V2, or an identity key |

**Parity hold.** While V1 is down, medium and high ops from every speaker family wait together, for up to 72 h. Claude-said content is not sent to a route that ChatGPT-said content cannot use. After 72 h, each family uses its best permitted route, and the gap is reported (§7.2 #3).

### 6.3 No permitted verifier, and S10 failure

- **Verification axis (J4c).** `no_independent_verifier`, as SPINE §8.3 and SD-38 define it: ranked with `unchecked`, never blocks promotion, shown with a chip.
- **Fidelity gate (J4f) with no permitted route.** It runs on the best non-independent route, Opus 5.5 batch, flagged `independent_of_worker: false`. Such ops get L4 at 100% and never count toward the SYN §7 bars.
- **If V1 fails S10**, the following happens automatically, in this order (ARCH R12), mirroring TEXTBOOK §8.13:
  - V1 stays on as an uncertified first screen;
  - Opus 5.5 checks 100% of medium and high ops and all new book sentences;
  - L4 rises from 5% to 20%;
  - budgets tighten from 2% to 1%;
  - the health page says so once;
  - a second local family is run against S10; if it passes, it becomes the certified route;
  - then UQ-4 (ARCH DQ-12) is asked.

  Independence reads "not certified" until a permitted family passes. The Opus fallback adds about $10 a month at 20 turns a day and $52 at 100 (§9.6).

### 6.4 The local verifier on this Mac

**The machine.** The target class is an Apple-silicon Mac with about 48 GB of unified memory; SP-3 sets the floor that ARCH DQ-5 states. Exact values are recorded locally by `northstar doctor`.

| Candidate (checked 2026-10-08) | Family | Facts | Proposed use |
|---|---|---|---|
| **Qwen3.8-27B** | `local:qwen` | Dense 27B; 262,144-token context; Apache-2.0; thinking on by default, switchable per request; 18 GB on Ollama (`qwen3.8:27b`, `qwen3.8:27b-mlx`) | **V1**: verifier, entailment, session auditor, cascade stages 1–2, fast-lane fallback |
| Qwen3-30B-A3B | `local:qwen` | MoE, 30B total, 3B active; 256K context; 19 GB (`qwen3:30b`) | The listed fallback: a faster V1 if Qwen3.8 misses the latency bar. Ollama measured Qwen3.5-35B-A3B at 112 tokens/s decode on an M5 Max; its size is (Unv, SP-3) |
| **Gemma 4 31B / 26B** | `local:gemma` | 30.7B dense, or a 25.2B MoE with 3.8B active; 256K context; 19–20 GB or 16–19 GB; MLX tags exist | **V2**: merge co-verifier; the second local family for UQ-4b; verifier for Qwen-said content. Also G (gold builder, `sim_user`) in C22 runs, unless a fourth local family qualifies (§9.2) |
| **Mistral Small 3.2** | `local:mistral` | 24B (size Unv) | **Eval judge** (J, EV §1.3). The gold builder and simulated user (G) use V2's family, never J's (§9.2) |

**One V1.** S10 chooses one V1: false-accept bars first, then throughput. The MoE stays the listed fallback.

OpenAI's open-weight models are excluded. Their family is `openai`, so they can never check ChatGPT- or Codex-said content.

**Runtime.** The process boundary is `northstar-modeld` on `run/model.sock`, whatever the runtime (PL §2.1, PL-4): no TCP port and no network. C20 calls modeld over that socket. SP-3 picks the runtime that passes S10 with schema output at the latency bar:
- **MLX as a library inside modeld** is the default (PL-4); its structured-output path is (Unv, SP-3).
- **Ollama** only if SP-3 picks it. It must be bound to loopback, version-pinned, and C20 accepts only models whose pinned local digest matches, because Ollama also serves cloud-hosted models (PL V-PL-7, RISK-PL-7). Facts: JSON-schema outputs (P21) and an OpenAI-compatible API. Since 0.19 (blog of 2026-03-30) it runs on Apple's MLX engine as a preview, for Macs with more than 32 GB; which formats take the MLX path is (Unv, SP-3).
- **llama.cpp** behind modeld, only if SP-3 prefers it.

modeld shares the core's Python 3.14 interpreter. It gets its own interpreter only if SP-1 finds a gap in the native packages it needs (CPLX-11).

Routes are recorded as `model@digest` plus runtime version. Checks run at temperature 0 with a fixed seed, except L1.

**Memory.** At most one verifier-class model is resident: up to 20 GB of weights plus 4 GB of KV cache (context capped at 32K), leaving at least 24 GB for macOS, the chat apps and the core. A role switch unloads first (modeld; `keep_alive: 0` under Ollama). The `embedder` is co-resident in modeld within the same 24 GB cap (size Unv, SP-3) and is never queued behind a generation. V2 runs in a nightly merge window; the judge, the gold builder and the simulated user and reader only in C22 runs. Under memory-pressure "warn" the local queue pauses. Northstar never changes the GPU wired-memory limit, a system setting.

**Load** (Unv, SP-MT-2): about 500 local calls a day at 100 turns a day, at 8–15 s each, or about 1–2 hours of compute a day, before the drift re-judge, the embedder and J10f. The per-role load model (§6.5) replaces this estimate.

### 6.5 S10 calibration protocol and bars

**Data.** It is synthetic, versioned and never visible to workers (I19).
- **Positives:** gold items from the hidden world ledger (SYN §7.4). They are rendered by the gold builder, a family other than the system's and V1's.
- **Negatives:** mutations made by code, so every label is known by construction: M1 negation; M2 changed number, date or version; M3 speaker or holder swap (user ↔ AI, Claude ↔ ChatGPT); M4 hedge removed; M5 qualifier dropped; M6 on-topic entity swap; M7 a gist with an extra detail; M8 reversed prerequisite; M9 a true statement from another span. Real worker errors caught by the canary are added.
- **Checks on the data:** the builder spot-checks 10%, during evaluation only (SYN §7).
- **Strata:** speaker family × capture fidelity (verbatim or model-reported) × task (fidelity, gist, attribution, hedge, direction, entailment, claim check, merge pair).
- **Sizes:** fidelity 300 positives and 300 negatives; entailment 200 and 400; claim checks 100; merge pairs 100.

**Load model.** Before the throughput bar is applied, build a per-role load model (calls a day × tokens × measured tokens per second) for J4f, L1, L2/L3, J4c, J10a, J10f, entailment, the drift re-judge of Claude replies, the embedder, canaries and live verification canaries, at 20 and 100 turns a day. The throughput bar applies to the whole load.

**Procedure.**
- **Screen, then confirm.** Screen each candidate at one setting on about 200 items per task. Run the full protocol (3 runs, all strata, candidate × quantisation × runtime × reasoning setting: off, low, high) only on the best one or two configurations. Try a second runtime only if the first fails.
- The false-accept rate (FAR) is reported with its **Wilson 95% upper bound**. Certificates use Wilson bounds at full n. Any sequential early stopping is pre-registered and stops only for failure.
- Also recorded: true accepts, abstains, p50 and p95 latency at 4K and 16K tokens, throughput and peak memory.

**Bars:**

| Role | Bar |
|---|---|
| V1 fidelity | FAR upper bound < 10% overall (a point estimate of 6% at n = 300 gives 9.3%); point FAR < 10% in M3 and M4; per-speaker-family FAR within 5 points of each other (vendor parity); true accepts ≥ 80%; abstains ≤ 20%; p95 ≤ 30 s |
| V1 entailment | FAR upper bound < 5% (TEXTBOOK §8.13; a point of 2.5% at n = 400 gives 4.5%). **Entailment true accepts:** ≥ 90%, stratified by R and B sentences and by paraphrase distance |
| V2 merges | False-merge upper bound < 5% |
| Eval judge | FAR upper bound < 10% on wrong but on-topic answers (EV §1.3; SYN §7) |
| Throughput | The whole load model at 100 turns a day fits in 3 hours of local compute a day |

**Certificate.** Passing produces a certificate `{model digest, runtime, quantisation, setting, bars, date}`, which enters configuration by a versioned commit. The router uses certified models only.
- Any change of model, quantisation or runtime re-runs S10.
- The nightly canary carries 30 rotating S10 items to detect drift.

**Development mode.** Until a certificate exists, C14 runs in the R12 mode (§6.3), and no bar-counting run happens.

---

## 7. Holding errors

### 7.1 Quarantine: a holding state, never a queue

**What enters.**
- A quality failure after the retry ladder.
- A J4f failure.
- An L3 abstain on a medium or high op.
- A blast-cap breach (the whole job).
- A failed re-extraction after a confirmed L4 error.

Only **derived proposals** are held. The span, and the AI-said Passage shell, stay searchable and are labelled "uncertain" (SYN §3.5).

**The record:** `{quarantine_id, proposal_id, op_index, reasons, tier, speaker_family, created_at, route_state, attempts, next_action_at}`, keyed by (`proposal_id`, `op_index`).

**Attempts:** 1 re-verification plus 3 re-extractions.

**Automatic exits** (J11q):
1. **Re-verification** by a fresh verifier of another permitted family, then by the next L4 audit.
2. **Re-extraction** with more context (±3 turns, then ±6, then the whole episode) on the alternative extractor. At most 3 attempts in 7 days.
3. **Re-run after a fix.** A canary-passed config change touching the job type or rule re-runs the affected windows.
4. **Day 7, by tier.** Low ops apply as `l2_pending` with 100% L4. Medium and high ops whose only verdicts are abstentions are released under 100% L4 within 24 hours. Ops with a failing verdict are discarded with a reason. A discard removes only the derived proposal.

**Discards are watched.** Every discard is recorded in `jobs.db` with its tier and speaker family. Discards feed sentinels #1 and #2 by episode and family (and #18), and a 10% sample is audited against its spans.

### 7.2 Sentinels (C21 computes, C11 acts)

| # | Sentinel | Alert at (starting value) | Automatic action |
|---|---|---|---|
| 1 | **Omission:** episodes with decision, commitment or question cues, or an AI explanation over 150 tokens, or at desktop L0 two or more reported explanation points or a reported body, that produced no matching item | Any episode; above 10% of episodes over 7 days | J11x on the alternative extractor. A sustained rate triggers the J3 change check |
| 2 | **AI-said skew:** the AI-said share of candidates, applied items, quarantine and featured slots, against the golden baseline and TEXTBOOK B11 | A drop of 5 points over 7 days; AI-said share of quarantine more than 5 points above its share of proposals | Re-run on the alternative extractor; re-verify AI-said quarantine first; freeze J3 if the canary agrees |
| 3 | **Vendor parity** (SPINE §8.3): per AI family, captured share against promotion rate, featured slots and verifier-route availability | A gap above 5 points | Prioritise J4f and J4c for the lagging family; parity hold (§6.2); report |
| 4 | **Pile-up pools:** quarantine; open and contested tensions; `awaiting_verify`; held ops; tentative placements; held editions; stale pages; batch backlog | Any quarantine older than 7 days; a pool growing 2 weeks running; `awaiting_verify` older than 72 h | Raise J11q and J11x; release the parity hold; report RISK 22 growth on the health page |
| 5 | **Fast and slow lane disagreement**, per speaker and tier | Above 15% either way | An extra J10a for that tier. A steward-side cause goes to the JF budget; a slow-side cause takes the omission path |
| 6 | **Validator reject rate** per job type and model | More than 2× the 7-day baseline | Role canary. On failure, freeze the role and use its alternative model |
| 7 | **Verifier health:** planted negatives in the sandbox canary and the catch rate of live verification canaries (§7.5); escalation and abstain rates | FAR over the bar on either; a step change | Verifier freeze (§7.3) |
| 8 | **Audit disagreement;** catch rate of live audit canaries (§7.5) | Above 5%; any planted bad event judged `correct` | A job type whose Opus-vs-second-opinion disagreement exceeds 5% over 7 days trips its budget; an audit canary miss triggers the L4 second opinion on that day's sample |
| 9 | **Capture gaps:** watermarks; call-rate decay; copy fidelity; fabrication ([GD §7]); observer self-test | Per connector | Flag the session "no live audit"; run J1r when verbatim text arrives; the observer drops to shadow ([OBS §4.7]) |
| 10 | **Oscillation:** A→B→A within 30 days; churn per node | Any A→B→A; more than 3× baseline | Hold supersessions on that pair; L4 at 100% |
| 11 | **Injection canaries** (sandbox and live) that persist into any authority-bearing record or pack | Any | Freeze that path; fail the red-team CI |
| 12 | **Lag:** window close to verified; book freshness. The bar derives from TEXTBOOK T-FRESH (95% of new leaves in "Just in" within 3 h) | p95 above 2.5 h; any above 24 h | Alert; raise priority; flush the lagging chains to the standard API, subject to the §9.5 deferral order and hard cap |
| 13 | **Spend** projected against both caps, soft and hard | Spend projected past the soft cap within the month; the hard cap projected | Deferral order; hard-cap behaviour (§9.5) |
| 14 | **Identity-join reverts** | Above 2% a week | J1r re-check (RISK 24) |
| 15 | **Update omission and duplicates:** J5 probe pairs (§4.4); duplicate rate among active items per concept | Probe pairs confirmed above the omission budget; duplicate rate 3 points above the golden baseline; a duplicate pool growing 2 weeks running | The omission budget path (§7.3); duplicates go to J8c's candidate list |
| 16 | **Freeze age** per job type | 7 days | §7.3 escalation: 100% L4 and release; a new trip re-freezes |
| 17 | **J8c health:** freshness re-queues; days since the last successful J8c; duplicate-candidate backlog; cap overruns | More than 2 re-queues on a job; 10 days; a backlog growing 2 weeks running; any overrun (counted) | Re-run on the standard API under short locks (§4.5); report on the health page |
| 18 | **Discard share** per speaker family (§7.1) | A family's share of discards more than 5 points above its share of proposals | Re-verify that family's quarantine first; audit its discards at 100% until the gap closes |
| 19 | **Desktop final-reply capture share:** sessions whose last user turn has no later report | Per connector: a rise of 5 points over 7 days | Report per connector on the health page; J10f samples those sessions first |
| 20 | **Write-budget overflow** per credential ([PL] budgets) | Any | Further writes on that credential are captured but wait; one health line; no other connector slows (§9.5) |
| 21 | **Authority overlap:** authority spans that overlap that session's tool output or another session's text | Any | The span gets no authority (treated as `reported`, I22) pending J10a; repeats freeze that connector's authority path, as in #11 |

**Live tagged canaries** run through a shadow Apply: the same code against a scratch ledger (§5.2).

**One controller registry.** Every sentinel here and in [TB] §8.12 is data: metric, threshold, hysteresis, one action from a small enum, and a precedence rank. One loop evaluates them. Precedence: the spend hard cap, then authority freezes, then parity holds, then lag flushes. A 90-simulated-day interaction run on replayed outputs is part of the fault plan (§8).

### 7.3 Error budgets, freezes and automatic exits

**Audited error** means an L4 confirmed error. A budget trips when the Wilson **lower** 95% bound exceeds it, or when 3 high-risk errors are confirmed within 7 days, whichever comes first. This works at about 30 high-risk ops a week at 20 turns a day. Its power is limited: at personal volume a budget detects true error rates near 10%; 30 days cannot show ≤ 2% ([EV] §2.4).

| Budget (starting value) | Freeze | Automatic exit |
|---|---|---|
| **High-risk ops per job type:** 2% over a rolling 7 days (SYN §7.4) | That type's high-risk ops → `held`; low and medium ops continue. If a config change landed in the last 7 days: J11r by `prompt_hash` or model, and the config pointer reverts to the last canary-passed version | The canary passes, and a 100% re-check shows ≤ 2% on at least 30 ops of that type, topped up with canary and golden ops, or by a sequential test. Held ops are then re-verified and applied in order. Held structural ops (J8c, J5t) never go to J11x. After 7 days frozen, the type escalates to 100% L4 and releases; a new trip re-freezes it (sentinel #16) |
| Medium: 5%. Low: 8% | The same, for that tier | The same |
| **Probable error** (L4 Opus-only verdicts, §6.1): 2× the audited budget | The same as the audited budget for that type and tier | The same |
| **Omission** (from J10f and the canary's omission margins) | No freeze: a trip re-routes affected windows to the alternative extractor and J11x, and reverts the config if a change caused it. It never freezes J3 | J10f and canary omission back within budget |
| **Steward:** J10a precision ≥ 95% and disagreement ≤ 5% per connector tier, including desktop L0/L0+ (R13) | JF frozen for that tier (§2) | §2 |
| **Book block types** | TEXTBOOK §8.8 | TEXTBOOK §8.8 |
| **Canary margins:** extraction precision or recall −5 points; attribution −2; false endorsement +2; AI-said recall −5; steward precision −3; update omission +5; missed supersession +5; missed merge +5; duplicate rate +3 | Role or config freeze; the pointer reverts. Recall and omission margins trip the omission row instead, so J3 never freezes for them | 2 consecutive passing nights |
| **Verifier:** canary FAR over the bar | V1 treated as unavailable (§10) | 2 good nights, plus a 100-item S10 re-run |
| **Global:** the replay check finds an invariant violation in applied state | J11r on the violating events; the producing job type freezes ([CDM] §9.3). Capture, correction and compensation event types never freeze; capture violations alert and route to a C06 code fix | A new code version passes the golden set, and replay is clean |

**Sequential test.** Recall and omission margins are judged by a sequential test (CUSUM or SPRT) over a rolling window of canary and live-canary items. The real detection delay is reported. "Within one night" is claimed only for large effects.

No freeze stops capture, corrections, J1r upgrades or the deterministic fast lane.

### 7.4 Compensating rollback and projection-checked rebuild

1. **Selector:** `job_id`, `batch_id`, `model@version`, `prompt_hash`, `config_version` or a time window, optionally narrowed to concepts or episodes.
2. **Closure.** Code follows event `inputs[]` forward to find every dependent event. The closure covers jobs as well as events: from `jobs.db` `input_ids` at each job's as-of watermark, it finds the jobs whose decision inputs included a compensated object. Only those jobs re-run (step 7). **Corrections are never compensated** (I21). An item targeted by an active correction is kept, and the conflict goes to L4.
3. **Compensations** are typed and idempotent, keyed by (`rollback_id`, `target_event`). Each is a CDM §2.2 event with `compensates` set, and all of a rollback's events sit under one `compensation.batch` (37) that records the selector, range and reason:
   - added item → `item.status_changed` (16) to `retracted`, reason `rollback:{id}`;
   - relation → `relation.status_changed` (28) to `retracted`;
   - supersession → `supersession.undone` (32), with the loser's `item.status_changed` back to `active` (earlier rank restored);
   - merge → `concept.alias_reverted` (22); split → `concept.aliased` (22) back into the original; re-parent → `concept.reparented` to the prior parents;
   - stance or verification → `stance.recorded` (19) or `verification.recorded` (20) restoring the prior record;
   - tension resolution → `tension.resolution_undone` (32), then `supersession.undone` for linked rows and `tension.reopened` (33) (CDM §7.2);
   - a standalone attribution or fidelity upgrade → compensated at item level: `item.status_changed` to `retracted`, then J11x re-derives the item without that attribution (step 7). Attribution-level errors are compensated at item level (retract and re-derive); there is no separate event type, and the catalog stays at 51 (X10 closed).

4. **Apply** through C12, at most 500 events per transaction. Then emit `items.retracted(ids)` to the C10 applier, so live sessions drop the retracted items.
5. **Rebuild** the C08, C15 and C16 projections from the ledger. Book structure is restored by a compensating edition.
6. **Checks.**
   - Live: the current-state hash equals the hash of a replay with model access off (I18), and every projection matches its rebuild.
   - **Rollback correctness:** a canonical active-state projection, with content-addressed keys (a hash of primary span, role and text), equals the fault-free baseline's at the same watermark, and pack and page queries return equal answers. Event ULIDs and `recorded_at` play no part.
7. **Re-derive.** J11x re-runs the affected windows, and every job in the step 2 closure, on the fixed route; Apply applies only the diff ([13 §F.10]).

### 7.5 Canary and golden runs

- **Golden set** (SYN §7.4; TEXTBOOK §13.1). At least 40 episodes across the four first connectors, with:
  - model-reported desktop capture;
  - planted speaker swaps;
  - injection canaries;
  - one non-chat document.
- **Nightly canary**, in a sandbox that C22 drives, so the core is never written (SPINE §6.4 rule 8). On production routes it runs:
  - 2 rotating episodes through J2–J5;
  - 2 book blocks;
  - 30 S10 items;
  - 10 steward windows.
- **Live tagged canaries** (EV §2.4), beside the sandbox canary. C11 injects them from versioned `evals/canaries/` (I19); every one is tagged `canary` and runs through a shadow Apply (the same C12 code against a scratch ledger), so the real ledger is never written (§5.2). Results go to `jobs.db` (C11) and, as metrics, to `ops.db` (C21). Sentinels #7, #8 and #11 read both kinds.
  - *Verification canaries:* known-false proposals at about 2% of C14's stream.
  - *Audit canaries:* known-bad events planted in the J10b sample.
  - *Injection canaries* in synthetic sources; *watermark canaries* from eval instances.
- **Golden gate.** Any change of prompt, schema, model, runtime, quantisation, threshold or code runs the full set, plus 50 real windows as of their time, in shadow and never applied. The change activates only if every metric stays within its margin.
- **Real-data error** is estimated from L4 and L6 and reported apart from synthetic error (RISK 6).

---

## 8. Attention-loss fault injection (test design)

**How it runs.**
- C22 runs the maintainer in a sandbox over the golden stream, with a simulated clock: 30 days in a few hours, as in TEXTBOOK T-RITUAL.
- Fault plans live in `tests/fault/plans/*.yaml`.
- Faults are injected through the port's hooks (`route_override`, `pre_call`, `post_call`; SPINE §8.5 rule 7), the input assemblers, storage crash points and the clock. The hooks refuse to run unless the stores are sandbox stores.
- **Replay first.** Nominal roles replay recorded outputs; only the faulted role calls live.
- Each fault runs alone on 8 seeds. Then all faults run together once.
- **When.** The full matrix runs at stage gates. A smoke subset runs nightly.
- **Controller interaction.** A 90-simulated-day run on replayed outputs exercises the controller registry (§7.2).

| ID | Fault | Injected at | Blocked | Detected (target) |
|---|---|---|---|---|
| F1 | Weak model in a worker role | Route | 100% of structural errors | Reject-rate sentinel within 20 proposals; canary within 1 night; budget trip within 2 days |
| F2 | Missing job card | Assembler | 100% invalid outputs (I15) | Within 20 proposals |
| F3 | Noisy padding (20–80%) | Pre-call | — | Omission sentinel and canary within 1 night |
| F4 | Shuffled offsets or altered quotes | Post-call | 100% (I1, I2) | Immediate |
| F5 | Model sets the speaker | Post-call | 100% (I3) | Logged per call |
| F6 | Hedges stripped | Post-call | 100% of lexicon cases (I10) | L2 catch rate measured |
| F7 | AI imperative as an instruction or goal | Post-call | 100% (I5, I22) | Immediate |
| F8 | Real quote, wrong claim | Post-call | — | L2 catch rate measured; budget within 2 days |
| F9 | Over-merge | Post-call (J5, J8c) | 100% unless V1 and V2 are both fooled (I12) | L4 within 24 h |
| F10 | 500-event job | Post-call | 100% (I13) | Immediate |
| F11 | Page text fed to the writer | Assembler | 100% (I7, B2) | Immediate |
| F12 | Prompt bug adds speaker names | Prompt | 100% (V4) | Immediate |
| F13 | Future evidence in a re-extraction | Assembler | 100% (I16) | Immediate |
| F14 | All AI-said items dropped | Post-call | — | AI-said skew within 1 night |
| F15 | Verifier always passes | Route (V1) | — | Canary negatives → freeze within 1 night |
| F16 | Steward invents spans, or takes a goal from AI text | JF post-call | 100% (applier) | J10a within 10 turns |
| F17 | Injected text in capture | Fixture | 100% of authority (I5, I22) | Injection canaries never persist |
| F18 | Duplicate delivery; lease lost mid-apply | Scheduler | 0 duplicates (I14, fencing) | — |
| F19 | `kill -9` during Apply | Storage | 0 partial events | Replay hash equal |
| F20 | Clock skew | Clock | 100% (I16) | Immediate |
| F21 | V1 out of memory | Runtime | No medium or high op applied unverified | `awaiting_verify` sentinel; parity hold holds |
| F22 | Apply mutants: a deleted guard, swapped AD19 steps, an unclosed `row_hist`, a wrong `ver_tier` mapping | Apply code | 100%: the reference projector and the sweep must catch each | Nightly sweep |
| F23 | A looping agent: 10 calls a second for an hour through one credential | Connector | Passes if that connector stays within its write budget and spend share, and no other connector's lag exceeds its bar | Sentinel #20 |

**It passes when:**
- 100% of structural errors are blocked;
- semantic catch rates are reported, never claimed as 100%;
- freezes trip and exit automatically;
- the canonical active-state projection after J11r equals the baseline's, and pack and page queries answer the same (§7.4);
- the user takes zero actions.

**Drills, once per release:** a 12-hour provider outage; 10 hours of sleep with batches in flight; a full disk; a corrupted `index.db`; an excision mid-run; a retirement notice.

---

## 9. Model runtime (C20)

### 9.1 Port and router

`ModelPort.propose(role, input, schema, ctx) -> ModelResult`. The `ctx` carries `job_id`, `attempt`, the risk tier, the worker family, the speaker families, the scope and sensitivity ceiling, the latency budget, the preferred mode (batch, standard or local) and, in the sandbox only, a fault plan.

The router walks `profile[role]` in order and keeps the first model that passes every filter:
1. C19 egress: `private` content goes to local models only (SPINE §8.5).
2. The family rule (§6.2), for verifying roles.
3. A current certificate, for verifying roles.
4. Health (circuit breaker), budget and quota caps.

If none passes, it returns `NoPermittedRoute`. It never reads a product name (I23).

### 9.2 Roles and profiles

| Role | A (default) | B | C / D |
|---|---|---|---|
| `steward`, `goal_change`, `goal_router`, `reexplain_detector` | Rules, then Haiku 5.5 on the standard API | As A | V1 |
| `drift_judge` | In turn: Haiku 5.5, escalating to Sonnet 5.5 (Claude replies re-judged by V1). Asynchronous judgments of Claude replies: V1 directly, no Haiku duplicate. Certified by SP-IS-2, separately from S10. When V1 is unavailable, only tier-0 verdicts count as independent, reported per connector | As A | V1 |
| `segmenter` | Haiku 5.5 batch | As A | V1 |
| `extractor`, `linker`, `reorganizer`, `book_writer`, `labeler` | Sonnet 5.5 batch (Haiku 5.5 if the golden set allows) | As A | V1; CLI only with UQ-6 (C) |
| `verifier`, `entailment`, `cascade_first`, `session_auditor` | V1 | V1, with gpt-5-mini as L3 stage 3 for non-OpenAI content | V2 |
| `merge_coverifier` | V2 | V2 | Third local family (Unv), or identity keys only |
| `auditor` / `auditor_second` | Opus 5.5 batch / V2, or a permitted remote family; never the route that gated the op (§6.1) | Adds gpt-5-mini | V2 / third family |
| `topic_suggester` (J12; off until UQ-10) | Sonnet 5.5 batch | As A | V1 |
| `embedder` (C08; CDM D-10) | Local embedding model on modeld (Unv, SP-3) | As A | As A |
| `eval_judge` (J) | Mistral Small 3.2: one J for every cell | As A. The OpenAI API never judges GD or CX cells (EV D-6), and one J scores every cell, so it is never J | As A |
| `gold_builder`, `sim_user` (G) | V2's family (`local:gemma`), or a fourth local family if one passes; never J's family | As A | Fourth local family (Unv); else V2, labelled not independent (RISK 18) |
| `sim_reader` (R) | V1's family (`local:qwen`), labelled, unless a fourth local family passes (EV §1.3) | As A | Fourth local family (Unv); else reported as not certified (RISK 18) |
| `chat_under_test` (A; evaluation only, EV D-5) | Claude models on the Anthropic Batch API for CD and CC cells; OpenAI models on the OpenAI API for GD and CX cells (EV L11) | As A | As A |

**This is the single C20 role table**; SPINE §8.1 points here. Family rules for evaluation roles follow EV §1.3: G differs from W, A and J; J differs from W, V, A and G; R differs from W, J and G. G also differs from V1's family, because it renders S10 data (§6.5); where G shares V2's family, V2's S10 results are labelled not independent (RISK 18). Fast-lane calls are recorded as `fast_model_call` in `session.db` (CDM D-7).

On C and D the workers are `local:qwen`, so full independence needs four local families. With fewer, merges use identity keys only, and eval independence is reported as not certified (RISK 18).

### 9.3 Provider adapters

| Adapter | Facts relied on | Rules |
|---|---|---|
| **anthropic** | Checked 2026-10-08: a batch holds at most 100,000 requests or 256 MB; most finish under 1 h; expiry at 24 h; results kept 29 days, in any order; batch cache hits best-effort (30–98%); non-default `temperature`/`top_p`/`top_k` → 400 on 4.7+; at least 60 days' retirement notice, and no 5.5 model retires before 2027-09-22; the 4.7+ tokenizer yields about 30% more tokens. From the cached Claude API reference (Unv, SP-MT-6): `output_config.format` does not combine with citations ([13 F6]); forced `tool_choice` is rejected on Opus and Sonnet 5.5; Opus 5.5 always thinks; `fallbacks` are not accepted on batches | `custom_id` = `call_id`; refusal = quality failure; effort set per role; charter cached 1 h |
| **openai** | gpt-5-mini $0.25 / $2.00, batch $0.125 / $1.00 per MTok (checked 2026-10-08) | Profile B only; schema mode; never routed for OpenAI-said content |
| **modeld** (every local model) | `northstar-modeld` on `run/model.sock`; no TCP port, no network (PL §2.1, PL-4) | The only local adapter. Digest pinning; temperature and seed per call; residency managed by the local slot |
| Runtime inside modeld, picked by SP-3 | MLX as a library (default, PL-4; schema path Unv, SP-3). Ollama: `format` schema output (P21), MLX engine preview since 0.19. llama.cpp (Unv, SP-3) | Ollama only if SP-3 picks it: loopback-bound, version-pinned, and only models with a pinned local digest (RISK-PL-7); `keep_alive` managed by the slot |
| **cli_claude, cli_codex** | SPINE §8.2 | Opt-in (UQ-6); quota caps; isolation (I24) |

### 9.4 Recording

```yaml
model_call: {call_id: "{job}/{attempt}/{n}" | "{session}/{turn}/{role}", role, provider, model_requested,
  model_returned, runtime: {version, digest}?, prompt_hash, charter_hash, schema, input_refs, input_hash,
  egress: {scope_check, redaction_v, sensitivity_max}, mode, batch_id?, usage: {in, cached_in, cache_write, out},
  cost_usd, stop_reason, latency_ms, raw_output_ref, parsed, fault_plan_id?, recorded_at}
```

The raw output is written before parsing, and replays read records instead of calling models.

In `session.db` the same record is named `fast_model_call` (CDM D-7), written by C10.

During excision, under C19's global lock, each store's writer rewrites the records containing excised spans to a tombstoned form through its `ExcisionPort`: C11 for `jobs.db`, C10 for `fast_model_call` (§5.2). Their replays then become impossible by design, and the projections rebuild from the excised ledger.

### 9.5 Cost controls

- **Caps:** daily and monthly, soft and hard, per role and in total (SPINE UQ-16; ARCH DQ-11). A preflight estimate (characters ÷ 3.5) runs before every call. `max_tokens` is set per role.
- **Deferral order.** Thresholds are fractions of the **soft** cap; deferral starts when spend is projected past the soft cap within the month. Verification never drops below its bars, capture is never cut, and nothing is discarded.
  1. Flushes go to batch.
  2. J11x and J11m wait.
  3. Pages linked to no active goal are printed every other night.
  4. At 100%: roles switch to a cheaper alternative that has passed the canary.
  5. At 150%: new J3 for windows not linked to a goal waits; nothing is discarded. The health page says "maintenance slowed by spend cap".
- **Hard cap.** The slow lane queues: recent and goal-linked windows drain first, and the rest move to local routes or excerpt fallbacks; nothing is discarded. The fast lane moves to its Degraded path (local V1, then deterministic). One health line says so.
- **Per-connector share.** No connector may use more than 40% of the monthly cap in any 24 hours before global deferral. Over it, its content is captured but waits.
- **Sentinels.** Sentinel #13 projects against both caps. Sentinel #12's flush to the standard API is subject to this order.
- **Thinking** counts as output tokens. Effort is tuned per role on the golden set (SP-MT-6).

### 9.6 One shared cost model (Profile A)

**Prices**, checked 2026-10-08, per million tokens, input / output:

| Model | Standard | Batch | Cache hit |
|---|---|---|---|
| Haiku 5.5 (prompts ≤ 100K) | $0.10 / $0.50 | $0.05 / $0.25 | $0.01 |
| Sonnet 5.5 | $2 / $10 | $1 / $5 | $0.10 |
| Opus 5.5 | $4 / $20 | $2 / $10 | $0.20 |

A 1-hour cache write costs 2× input. Batch and cache discounts stack.

**Assumptions** ([13 §I]; `ai-in-session.md` §4.4; TEXTBOOK §8.10): a turn is about 1,100 tokens; a window about 10 turns and 10 candidates; steward 4K in, 300 out per window; J2 12.5K in, 1K out; J3 16.5K in (2K cached), 3.5K out (about 2K thinking); J5 11.5K in, 2.5K out; retries +20%, flush on 20% of windows, re-derivation +10% of J3; L4 5 events per call (8K in, 2.5K out); local calls $0.

| Component | Basis | 20 turns/day | 100 turns/day |
|---|---|---|---|
| Fast lane: steward, goal change, drift tier 2 (5% escalated to Sonnet), C23 calls | About $0.0016 per turn | $0.04/day · **$1.1/mo** | $0.18/day · **$5.3/mo** |
| Slow lane: J2 + J3 + J5 with overheads | About $0.080 per window | $0.16 · **$4.8** | $0.80 · **$24.0** |
| Local verification: J4f, L1, J4c, J10a, J10f, entailment, second opinions, the drift re-judge, the embedder | V1, V2 and the embedder on modeld; time per the load model (§6.5) | **$0** | **$0** |
| L4 core audit (Opus 5.5 batch) | 6 or 25 events a day; $0.037 per call | $0.07 · **$2.2** | $0.19 · **$5.6** |
| Book compile with its L4 (TEXTBOOK §8.10; unchanged at today's prices) | 45 calls at $0.0141 at 100 turns | $0.20 · **$6.0** | $0.95 · **$28.5** |
| Nightly canary (fixed) | 2 episodes, 2 blocks, 1 L4 call | $0.18 · **$5.3** | $0.18 · **$5.3** |
| Golden gate (fixed) | $2.76 a run, about 2 a month | **$5.5** | **$5.5** |
| **Total (±2×)** | | **≈ $0.83/day, ≈ $25/mo** | **≈ $2.47/day, ≈ $74/mo** |

Full golden runs happen only at config changes and stage gates (ARCH R1); the golden-gate line covers them.

**Variants and comparison:**
- **Live tagged canaries (§7.5)** add no API cost for verification canaries (V1). Audit canaries add about one planted event a day to J10b calls, under $0.01 a day.
- **Profile B** adds about $1 a month.
- **S10 failure (§6.3)** adds about $10 a month at 20 turns a day and $52 at 100. Opus 5.5 always thinks, so this budgets about 300 output tokens per check, against the 50 assumed in TEXTBOOK §8.10.
- **Haiku 5.5 for J3, J5 and the book writer** costs about $22 a month at 100 turns a day, but only if it passes the golden set.
- **This is the one cost model.** SPINE §0 and §8.4 cite its $25–74 a month, and EV §5.4 cites it (X23). The earlier $12–40 predated the book's cost and left out thinking tokens, the audit and the fixed canaries. Fixed costs dominate at 20 turns a day.
- **J12** (suggested topics) is off until UQ-10. When on, it adds a few batch calls a week, well under $1 a month.
- **Lag bar (§7.2 #12).** The 2.5 h bar may force more flushes than the 20% of windows assumed above; SP-MT-3 measures this, and each extra flushed window costs about 2× its batch price.

---

## 10. When the maintainer is down or degraded

| Condition | Detected by | Automatic behaviour | Catch-up and exit |
|---|---|---|---|
| Maintainer crashed | `launchd`; C21 heartbeat | Capture, the fast lane and packs continue; the pin uses the last validated state (SPINE §7.4) | Restart. Leases are recovered and `applying` jobs reconciled. The backlog is computed from watermarks, with recent and goal-linked windows first |
| Mac asleep | Wake event | Nothing runs, and nothing local is lost | Missed schedules run once. Open batches are collected; expired requests are re-submitted as transport retries |
| Provider down, key invalid, or credit exhausted | Circuit breaker; 401 or 402 | Jobs wait with backoff. The steward uses its alternative, then V1, then deterministic mode. Northstar never switches on its own to a CLI provider (UQ-6) or a new vendor | The breaker closes on a successful probe. The backlog drains by priority within the cap |
| V1 down, out of memory, failing its canary, or under memory pressure | Probe; memory pressure; sentinel #7 | **Fail closed.** Low ops apply as `l2_pending`. Medium and high ops wait under the parity hold. The LaunchAgent restarts. A model file that fails its digest check is re-fetched from its pinned source, under the install-time consent | Checks run oldest first. A failing `l2_pending` op gets J11r and quarantine. After 72 h, each speaker family takes its best permitted route |
| Budget freeze | §7.3 | §7.3 | §7.3 |
| Batch older than 24 h | Lag sentinel | Goal-linked windows move to the standard API, within the cap | — |
| Corruption or a full disk | Nightly `PRAGMA integrity_check`; write errors | That store stops writing; capture keeps spooling (SD-29) | Restore the backup, then re-apply recorded proposals through Apply. If `jobs.db` is lost too, re-extract, labelled as re-derivation |
| Excision | `excision.begin(targets)`; `global.excision` | Drain and pause. Excision runs as a resumable saga ([CDM] §10.2): each store's writer purges its own rows through its `ExcisionPort`; C19 writes `ledger.db` (§5.2). After a crash the saga resumes from its last step, and a stale lock holder is recovered by lease and epoch (§3.6) | Resume on `excision.done(target)`. Jobs on excised inputs end `failed: inputs_excised` and are re-planned |
| Model retirement | Notice | J11m shadow run; the old model is kept until 14 days before retirement | Switch when the golden gate passes. Otherwise the role uses its alternative, and the health page says so |

None of these states asks the user to do anything. The user sees only the Reader footer (TEXTBOOK §8.12), the read-only health page and `northstar status`.

---

## Sources

**Project documents:** GOAL; SPINE; TEXTBOOK; [CD]; [GD]; [OBS]; SYN; research notes [10]–[13]; `ai-in-session.md`; `ai-continuity.md`; `connectors-desktop-and-mcp.md`.

**Product facts checked 2026-10-08:**
- Anthropic pricing: https://platform.claude.com/docs/en/about-claude/pricing
- Anthropic batch processing: https://platform.claude.com/docs/en/build-with-claude/batch-processing
- Anthropic model deprecations: https://platform.claude.com/docs/en/about-claude/model-deprecations
- OpenAI pricing: https://developers.openai.com/api/docs/pricing
- Qwen3.8-27B: https://huggingface.co/Qwen/Qwen3.8-27B
- Ollama library: https://ollama.com/library/qwen3.8 · https://ollama.com/library/qwen3 · https://ollama.com/library/gemma4 · https://ollama.com/search?q=mistral-small
- Ollama on MLX: https://ollama.com/blog/mlx
- Local checks on the build machine (values kept locally).
- Facts marked (Unv) in §9.3 come from the Claude API reference cached 2026-10-06 (SP-MT-6).

---

## 11. Interfaces

| Direction | Component | Message, record or API |
|---|---|---|
| Provides → | C07 via C12 | Typed events; `applied_job` rows (§3.3); `ledger.committed(watermark, types)`; `correction.applied(id)` |
| Needs ← | C06 | Capture records; reconciliation records `{obs_ids, message_id, method, confidence}`; `capture.gap(conv_key, kind)` |
| Needs ← | C10 | `window.closed{handle, branch, window_id, turn_range, reason, active_item_ids[], spans[]}` through the outbox (SPINE §6.3); `session.ended` (lifecycle end only); JF metrics and `fast_model_call` rows |
| Provides → | C10 | `session.audit_result{handle, window, ops_rederived[], disagreements[]}`; `fastlane.mode{tier, mode, reason}`; re-steward requests; `items.retracted(ids)` after a rollback (§7.4) |
| Needs ← | C23 (`session.db`) | Routing records for flushes; `LinkCandidate{goal_id, item_id, basis, session, turn, unit_span_hash}` |
| Provides → | C08, C15 | Outbox consumption (J9a, J9b); rebuilds after J11r. C15 builds the charter that assemblers read |
| Provides ↔ | C16 | Scheduling, locks and budgets for J7 and J8; `printing.done{watermark, metrics}`; block-type freeze state |
| Needs ← | C18 | Corrections into C12; the constraint registry for assemblers (I21) |
| Needs ← | C19 | Per-call egress decisions; `excision.begin(targets)` and `excision.done(target)` (internal); the global lock. `excision.applied` is the ledger event C19 writes |
| Provides → | C19 | `ExcisionPort` purges executed by C11 (`jobs.db`), C08 (`index.db`) and C16 (`book.db`), each in its own store |
| Provides → | C20 | `ModelPort.propose(role, input, schema, ctx) -> ModelResult`; certificates; profiles |
| Provides ↔ | C21 | Metrics; `budget.tripped(job_type, tier, metric)`; `freeze.changed{freeze_id, kind, target, effect, exit_conditions, state}`; sentinel actions |
| Needs ← | C22 | `canary.result{config_version, role, metrics, pass}`; sandbox runs; fault plans |
| Provides → | C17, CLI | Health `{freezes[], pools{}, lags{}, last_canary, spend}`, read-only |
| Owns | — | `jobs.db` (writer C11): jobs, locks, `model_call` rows, verdicts, quarantine, freezes, certificates, threshold sets |

---

## 12. Departures from SPINE

| # | SPINE | This design | Why |
|---|---|---|---|
| D1 | Recorded outputs live in `jobs.db` (§5.2) | Fast-lane records go in `session.db` as `fast_model_call` rows (CDM D-7), written by the C10 applier | JF runs in `northstard`, and only C11 may write `jobs.db` |
| D2 | `eval.db` is read by C22 only (§6.1) | C22 sends `canary.result` to C21, which stores it in `ops.db` | C11 needs canary results for freeze exits and change gates |
| D3 | `cascade_first` is "a local small model" (§8.1) | Stage 1 is V1 with thinking off | Only one verifier-class model fits beside the user's apps |
| D4 | I19's single rule (X32): automatic releases only through a committed procedure with replay and canary gates, versioned bundles and automatic rollback | No automatic threshold release in the prototype. J10e is dropped; thresholds change only through committed, golden-gated bundles at stage gates | This removes the one-way ratchet of a tighten-only loop (CPLX-8, MR-1) |
| D5 | Jobs J0–J11 | Adds J1r, J4f/J4c, J5t, J7.0, J8c, J9a/b, J10a–d, J10f, J11r/x/q/m/p and J12 (gated, UQ-10); J10e is dropped for the prototype. Adds roles `session_auditor` (as in `ai-in-session.md`), `labeler`, `merge_coverifier`, `auditor_second`, `topic_suggester`, `embedder`, `sim_user`, `sim_reader`, `chat_under_test` (§9.2) | Every SPINE responsibility needs an owner and a trigger. J8c keeps core concept changes in C12, apart from the book edition |
| D6 | Profile A costs $12–40 a month (§8.4) | About $25–74 a month (§9.6) | Adds the book, thinking tokens, the audit and the canaries, at today's prices. Resolved by X23: SPINE §0 and §8.4 cite §9.6 |

---

## 13. Risks

Reused: **6** (semantic errors bounded only statistically), **18** and **30** (verifier independence and strength), **7**, **9**, **13**, **14**, **16**, **22**, **24**, **28**.

| # | Risk | Threatens | Mitigation |
|---|---|---|---|
| **RISK-MT-1** | Local verification load on a laptop (heat, battery, memory) delays checks, so the `awaiting_verify` and `l2_pending` pools grow | §4.7; freshness for §4.5 | One resident model; co-resident embedder; slot admission (§3.7); AC-power scheduling; memory guard; deferred L2 for low ops; the per-role load model (§6.5), tested by SP-MT-2 |
| **RISK-MT-2** | The L4 auditor is the workers' family, and it shares the Claude speaker's family, so shared blind spots (CAPA) may understate audited error, most for Claude-said content, and every budget built on it | §4.7; §4.2; §6 "errors bounded" | Second opinions from a route that did not gate the op (V2 or a permitted remote family) on every disagreement and 20% of agreements, and on 100% of Claude-said content while V2 has capacity (else 50%); a probable-error budget; audited error reported per speaker family; L6 labels; real-data error reported separately |
| **RISK-MT-3** | Batch latency (up to 24 h) delays verified items | §4.5 continuity | The recent-provisional slot (SPINE §5.5); flush on `session.opened`; lag sentinel |
| **RISK-MT-4** | While V1 is down, ChatGPT- and Codex-said content has no other default route | §4.2 | Parity hold; vendor-parity sentinel; V2 (UQ-4b) |
| **RISK-MT-5** | Real attention loss may take forms the 23 faults miss | §4.7, §4.8 | Each L4-confirmed error class becomes a new fault plan; HOW ablation |
| **RISK-MT-6** | Runtime churn: MLX releases change, Ollama's MLX engine (if SP-3 picks Ollama) is a preview, and tags change | §4.7 | The modeld boundary isolates the runtime choice; digest pinning; S10 re-run on change; keep the old runtime until the new one is certified |
| **RISK-MT-7** | A low spend cap slows maintenance, so pages and packs go stale | §4.5, §6 | A deferral order and hard-cap behaviour that never cut verification or capture and never discard; per-connector share; health line; SPINE UQ-16 (ARCH DQ-11) |

---

## 14. Questions for the user

Covered by SPINE already: the verifier if S10 fails (UQ-4; ARCH DQ-12), subscriptions (UQ-6), cloud calls (UQ-11). The questions this design raised now carry SPINE IDs (SPINE §11.2, the one numbered list); the old local IDs are kept in brackets. Each accepts a risk.

| ID | Question | Why it is yours | Working assumption (pending user answer) |
|---|---|---|---|
| **UQ-16** (was UQ-MT-1; ARCH DQ-11) | **Spend cap.** Maintenance is estimated at about $25 a month at 20 turns a day and $74 at 100 (±2×), on your key or plan credits (SP-5). What should the monthly cap be? | A low cap slows maintenance (RISK-MT-7) | Soft cap $80, hard cap $120; the §9.5 deferral order applies above the soft cap, and the hard-cap behaviour at the hard cap |
| **UQ-17** (was UQ-MT-2) | **Real-data calibration.** May about 100 windows of your real conversations be labelled once, locally, by the local judge, with labels you may spot-check if you wish? This would estimate real error, which synthetic data understates (RISK 6) | It uses your conversations for evaluation | No. Synthetic data only; real error comes from L4 and optional corrections and is labelled as such. **Settled as HOW (ARCH §12.1, final gate; formerly ARCH DQ-6(c)); user override only.** |
| **UQ-18** (was UQ-MT-3) | **Web fact checks.** May code send short, redacted claim text to a web search API to check AI-said facts? | Claim text leaves the Mac (RISK 13). Without it, more claims stay `unchecked` or `contested` (RISK 22) | No. Internal evidence plus `parametric` judgements only. A parametric judgement can never mark a claim `contradicted` |

---

## 15. Spikes

| Spike | Settles |
|---|---|
| **SP-3 + S10** (SPINE), with the §6.5 protocol | The choice of V1, V2 and the judge; the runtime; certificates |
| **SP-MT-1** | The L3 confidence signal: whether local runtimes expose logprobs, or whether verbalised confidence plus stage agreement can be calibrated |
| **SP-MT-2** | Runs in Stage 0 against the per-role load model (§6.5). Daily local load at 20 and 100 turns a day: wall time, heat, battery, memory, and the effect on the user's apps. Also whether V2 has capacity for 100% second opinions on Claude-said content (§6.1) |
| **SP-MT-3** | Batch turnaround and cache-hit rates for the J3 and J5 shapes, and how often a flush is needed |
| **SP-MT-4** | J3 with Citations against structured output with code-checked quotes (SYN S7) |
| **SP-MT-5** | A dry run of the fault harness (F1–F23), and equality of the canonical active-state projection after rollback with FTS and the vector cache |
| **SP-MT-6** | Thinking tokens per role at the chosen effort; checking the Anthropic adapter facts marked Unv against the live docs |
| **SP-MT-7** | Profile D capacity (local-only models, same load model, Stage 0): steward latency, `goal_change`, router, in-turn check budgets, J3 window time, and whether the overnight batch fits. Its estimates feed ARCH DQ-3(a) |
| **SP-5** (SPINE) | Whether plan API credits cover Profile A |

---

## 16. Goal-fidelity check

| GOAL item | How it is served | Status |
|---|---|---|
| §3.4 Maintenance that holds up against its own attention loss | Code orchestrator; stateless workers; Apply gate; L0–L6; budgets, freezes and rollback; fault injection | **Partial:** semantic errors are only bounded (RISK 6, RISK-MT-2); independence depends on S10 (RISK 18, 30) |
| §4.7 A robust maintainer | All of the above, plus fencing, idempotency, recording and fail-closed verification | **Partial** (RISK 6, 18, 30, RISK-MT-2, RISK-MT-5). At desktop L0, input depends on the chat model (RISK 4) |
| §4.1 No rituals | Automatic exits everywhere; no state in §10 asks the user | **Met by design.** UQ-16 to UQ-18 are one-off answers, not routines |
| §4.2 AI-said is first-class | Passage shells for every assistant span; speaker-neutral checks; skew and parity sentinels; parity hold; SD-38 | **Partial** (RISK 30, RISK-MT-4; RISK 33 upstream) |
| §4.3 The AI manages it | Every job is automatic; corrections are optional and honoured (I21) | **Partial:** contested residue remains (RISK 22) and is never routed to the user |
| §4.5 Drift and continuity, equally | JF modes; J10a; flush and lag sentinels | **Partial** (RISK-MT-3, RISK 16) |
| §4.6 Product-agnostic | Routing and sentinels use capability levels and `speaker_model_family` only | **Met by design** (I23 lint; product-blindness test) |
| §4.8 Prototype built and evaluated | Canary, golden gate, S10, fault injection, drills | **Planned** (SP-3, S10, SP-MT-5) |
| §6 Maintains itself; errors bounded, detectable, correctable | §7, §10 | **Partial** (RISK 6, RISK-MT-1, RISK-MT-7) |

---

## Consistency fixes (2026-10-08)

| ID | Change |
|---|---|
| **X10** | §4.2 op → event map in CDM §2.2 names (adds ops `REVISE_ITEM`, `SET_LINEAGE`, `SET_AGENDA_STATUS`, `OPEN_TENSION`; `REPARENT` → `concept.reparented`; `FIDELITY_UPGRADE` → `attribution.added` with `recon_id`). §7.4 compensations use CDM names under one `compensation.batch`. **Closed (2026-10-08 review):** attribution-level errors are compensated at item level (retract and re-derive); no separate event type; the catalog stays at 51 |
| **X12** | §3.7, §5.2, §9.4, §10, §11: C19 orchestrates and writes `ledger.db`; each other store's writer runs its `ExcisionPort`. Events `excision.begin(targets)`, `excision.done(target)`; ledger event `excision.applied` |
| **X13** | §9.2 is the single C20 role table: adds `embedder`, `sim_user`, `sim_reader`, `chat_under_test`, `topic_suggester`; EV §1.3 family rules (G on V2's family, never J's; one local J; no OpenAI judge for GD/CX). §6.4, §6.5 aligned. One record name: `fast_model_call` |
| **X20** | §0, §6.4, §9.3, RISK-MT-6: `northstar-modeld` on `run/model.sock`; SP-3 picks the runtime (MLX default; Ollama only loopback-pinned with a local-digest check) |
| **X22** | §3.5, §7.2 #12: alert and flush to the standard API when p95 window-close → verified exceeds 2.5 h (TEXTBOOK T-FRESH) |
| **X23** | §0, §9.6, D6, UQ-MT-1: §9.6 is the one cost model ($25–74 a month); adds the nightly dev-split golden run (about $42 a month) while EV keeps it. Superseded by ARCH R1: nightly full golden runs dropped. |
| **X24** | §5.2, §7.2, §7.5: live tagged canaries beside the sandbox canary; C11 injects, C12 rejects by tag, results to `jobs.db` and `ops.db`; sentinels read both |
| **X31** | §4.2, §4.4: J5 `misfits` → C08 `anomaly_mark`. §4.5, §9.2: gated J12 suggested topics (off until UQ-10). §4.3: explicit goals High; reported and inferred Low |
| **X32** | §4.6 J10e and D4 follow SPINE I19's single rule (committed procedure, replay and canary gates, versioned bundles, automatic rollback); J10e still only tightens. Superseded by the review (CPLX-8, MR-1): J10e dropped for the prototype |

---

## Review revisions (2026-10-08)

These rows are the review fixes for this file. The full review record, with each finding's verdict and the fixes not adopted, is [REVIEW.md](../REVIEW.md).

| Finding | What changed |
|---|---|
| **MR-1** | Omission now has production measures: the J5 update-omission probe (§4.4); J10f, an episode-level coverage audit (§4.6, §6.1); an omission budget that re-routes and never freezes J3; canary margins for update omission, missed supersession, missed merge and duplicates; a sequential test with the real detection delay reported (§7.3); sentinel #15 (§7.2). L1 drops to 1 label on medium ops only if the ablation shows no loss (§6.1) |
| **MR-2** | An L4 error is confirmed only by Opus plus a route that did not gate the op (V2 or a permitted remote family); V1 never confirms what it passed. Probable-error budget for Opus-only verdicts; audited error per speaker family; Claude-said content gets 100% second opinions while V2 has capacity, else 50%; no two-rater latent-class estimate (§6.1, §7.3, §9.2). Sentinel #8 action defined (§7.2). RISK-MT-2 extended to the speaker family |
| **MR-3** | Job record gains `epoch` and the full state list the DDL must match, with `failed_code` and `cancelled` (§3.1). Any expired non-terminal lease is reclaimed, with a maximum lease age (§3.2). One `idem_key`; ledger-side `applied_job` rows; boot reconciliation by `job_id` and `proposal_id`; `jobs.db` at `synchronous=FULL`; a ledger→jobs orphan check (§3.3, §5.2, §11). Global locks carry lease and epoch (§3.6) |
| **MR-4** | Landed at the final gate. §5.3 Authority: hook-channel spans need `observation.origin_confirmed` (not `confirmed_degraded`) for long-term authority; a later `not_confirmed` is revoked by a compensation under one `compensation.batch` ([HK] §8; [CDM] §3.1) |
| **MR-5** | A stale global-lock holder is recovered; excision resumes as a saga ([CDM] §10.2) (§3.6, §10) |
| **MR-6** | JF Degraded and Frozen exits run the primary or steward in shadow on live windows (§2). The high-risk freeze exit is sized to volume (topped up with canary and golden ops, or a sequential test); held J8c and J5t ops never go to J11x; after 7 days a frozen type escalates to 100% L4 and releases, and a new trip re-freezes it (§7.3; sentinel #16) |
| **MR-7** | Apply step 5 states verdict handling and quarantine release (§5.2). Quarantine is keyed by (`proposal_id`, `op_index`); attempts are 1 re-verification plus 3 re-extractions; exit 4 is defined by tier; every discard is recorded, fed to sentinels #1, #2 and #18 and sampled at 10% (§7.1) |
| **MR-8** | Rollback is checked by a canonical active-state projection with content-addressed keys plus equal pack and page answers; Book structure is restored by a compensating edition; the closure covers jobs; `items.retracted(ids)` goes to the C10 applier (§7.4, §8, §11, SP-MT-5) |
| **MR-9** | `atomic_group?` removed from the worker envelope (§4.2). Apply derives dependency closures in code; L0 checks relation endpoints; an FK or trigger abort is a code fault (`failed_code`, sentinel #6, producing type frozen) (§5.2, §5.3) |
| **MR-10** | J8c: freshness per op, a re-queue limit then the standard API under short locks, no scope locks across `awaiting_batch`, top-N application for overruns up to 2× and quarantine above, every overrun counted (§3.6, §4.5; sentinel #17) |
| **MR-11** | Fault F22 (Apply mutants caught by the reference projector and the sweep) (§8). The global budget freezes the producing job type; capture, correction and compensation events never freeze; capture violations route to a C06 fix (§7.3) |
| **MR-12** | Landed at the final gate. §4.6 J10b: a confirmed error on a Tension resolution records the dissent as a resolution input and re-resolves at step 5 (contested, spawned question, `next_recheck`; [CDM] §7.2) |
| **CONS-1** | Window close is the outbox event `window.closed{…}`; `session.ended` marks only the lifecycle end (§2, §3.7, §11) |
| **CONS-3** | ARCH R13 carried: JF modes and the steward budget apply per connector tier, desktop L0/L0+ included; J10a runs every 10 recorded calls at desktop L0/L0+ and checks the reading, not copy fidelity; path-B sessions are reported "no audit" (§2, §4.6, §7.3) |
| **CONS-4** | Merged with BOOK-2; ARCH R14 carried into J3: reported explanation and example points become items, and reported bodies become passages (§4.4) |
| **CONS-5** | Spend thresholds are fractions of the soft cap; deferral starts when the soft cap is projected; step 5 defers and never discards; a defined hard cap; a 40% per-connector share; sentinels #12 and #13 follow (§9.5, §7.2). UQ-MT-1 → SPINE UQ-16 (ARCH DQ-11) |
| **CONS-7** | ARCH R12 carried: after the Opus fallback a second local family is run against S10, then UQ-4 (ARCH DQ-12) is asked; independence reads "not certified" until a permitted family passes (§6.3) |
| **CPLX-1** | Per-role load model at 20 and 100 turns a day, which the throughput bar applies to (§6.5, §6.4, §9.6); co-resident embedder outside the slot queue; drift re-judge above P3 verification; slot admission rule (§3.7); one V1 chosen by S10 (§6.4); asynchronous Claude-reply judgments directly on V1 (§9.2). RISK-MT-1 cites the load model |
| **CPLX-4** | S10 screens, then confirms; Wilson bounds at full n; early stopping only for failure; development mode until a certificate exists (§6.5). The hardware floor is set by SP-3 and stated in ARCH DQ-5 (§6.4) |
| **CPLX-5** | SP-MT-7, a Profile D capacity spike in Stage 0 (§15) |
| **CPLX-6** | Fault runs are replay-first; the full matrix runs at stage gates and a smoke subset nightly (§8) |
| **CPLX-8** | One controller registry with precedence for every sentinel here and in [TB] §8.12 (§7.2). J10e dropped for the prototype (§4.6, §6.1, D4, D5, X32) |
| **CPLX-11** | Landed at the final gate. §6.4 Runtime: modeld gets its own interpreter only if SP-1 finds a gap |
| **SEC-3** | Sentinel #21: authority spans overlapping the session's tool output or another session's text (§7.2) |
| **SEC-6** | Device-specific values removed: §0 item 7 and §6.4 give the target hardware class only; exact values stay local in `northstar doctor`; the Sources line is generic |
| **SEC-10** | Hard-cap behaviour and a per-connector spend share (§9.5); sentinel #20 for write-budget overflow (§7.2); fault F23, a looping agent (§8) |
| **AIE-7** | Drift judge: asynchronous Claude-reply judgments run on V1 directly, certified by SP-IS-2 apart from S10; with V1 down only tier-0 verdicts count as independent, reported per connector (§9.2) |
| **BOOK-1** | J8 follows the [TB] §7.3 growth regime: a bootstrap edition, daily for 14 days, then weekly (§3.7, §3.8, §4.5) |
| **BOOK-2** | J3 on model-reported capture: one item per reported explanation or example point, one passage per reported body (§4.4). Sentinel #1 covers desktop L0 points and bodies; sentinel #19 tracks final-reply capture (§7.2) |
| **BOOK-4** | Entailment true-accept bar ≥ 90%, stratified by R and B sentences and paraphrase distance (§6.5) |
| **BOOK-10** | J3 tags `offer` apart from `learning_suggestion`, which must link a concept (§4.4) |
| **ARCH R1** | The nightly dev-split golden run ($42 a month) is removed from §0 item 10, §9.6 and UQ-16; X23 marked superseded. D6 had no $42 sentence, so it is unchanged |
| **ARCH R11** | Local question IDs become SPINE IDs: UQ-MT-1, -2, -3 → UQ-16, UQ-17, UQ-18 (§14, §4.4 J4c, §9.5, RISK-MT-7, §16) |
| **Carried task (c)** | X10 closed: attribution errors are compensated at item level, no new event type, the catalog stays at 51 (§7.4). X23 superseded by R1 |
| **Smaller issues** | ROB: dense windows are split, never discarded (§4.4); maximum lease age (§3.2); live tagged canaries run through a shadow Apply (§5.2, §7.2, §7.5); capture never freezes (§7.3). CONS: the `attribution.fidelity_upgraded` hedge removed from §4.2 |

---

## Final-gate fixes (2026-10-08)

The final gate found decided review fixes that had not reached this file. Each is a HOW change; no non-negotiable is weakened.

| Finding | What changed |
|---|---|
| MR-4 | §5.3 Authority adds the hook-channel `origin_confirmed` gate and revocation by compensation |
| MR-12 | §4.6 J10b: an audit-undone Tension resolution becomes contested, with a question and a recheck date |
| CPLX-11 | §6.4 Runtime: modeld's own interpreter only if SP-1 finds a gap |
| BOOK-3 | §4.5 J7 Printing: validators V1–V15 |
| Fewer questions (final gate) | §14 UQ-17 is settled as HOW at its working assumption (ARCH §12.1), user override only |
