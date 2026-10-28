# Core data model and ledger

**Scope:** SPINE C06, C07, C08, C18 and C19 at the data level; SPINE §5, §6.1, §6.4.
**Status:** design draft for adversarial review. Not approved. Nothing here is built. Written 2026-10-08.
**Authority:** [`docs/GOAL.md`](../../GOAL.md), then the user's answers of 2026-10-08, then [SPINE](../foundations/SPINE.md). This document changes only the HOW. It uses SPINE IDs (C, I, SD, UQ, RISK) and TEXTBOOK IDs (V, B, Q, H).
**Companion:** [`core-data-model.sql`](core-data-model.sql) holds the full portable DDL: every table, CHECK, index and invariant trigger, per store. An earlier version ran on this Mac's Python 3.14 SQLite and its triggers were tested; it has not been re-run since the 2026-10-08 consistency and review edits (§9.4). This document explains the DDL and does not repeat it.
**Inputs:** GOAL; SPINE; TEXTBOOK §5.8–5.9, §6–9, §12; [CD] §4.2; [GD] §6.2, §7; [OBS] §4.3–4.4; SYN §3.1, §3.5, §5; [11] impl. 1–2; [12] impl. 1–12; [13] §A–F, §I.
**Sibling docs** (cited by the 2026-10-08 fixes): [PL] `platform-security-privacy.md`, [HK] `connectors-claude-code-and-codex.md`, [CX] `connectors-desktop-and-mcp.md`, [IS] `ai-in-session.md`, [AC] `ai-continuity.md`, [MT] `maintainer.md`.
**Owned here:** store schemas, the event catalog, the query layer and ports, invariant checks, supersession and Tension as data, excision, volume. **Not owned:** algorithms (C13, C14, C16) and the meaning of job states (C11 owns those; this document owns the jobs schema).

---

## 0. Summary

1. **Three layers, one writer per store** (SPINE §5.1, §6.1). Capture is immutable. The ledger is an append-only `event` log plus state tables that Apply (C12) updates in the same transaction. Projections can be rebuilt.
2. **51 ledger event types**, each with its proposer, risk tier and gates (§2).
3. **Text lives once,** in `intake.db`. Ledger spans hold anchors (offsets, `quote`, `prefix`, `suffix`); ledger messages hold no text. Excision stays small and quote checks stay exact.
4. **One message, many observations.** A model-reported copy, an observer read and an export of one turn are reconciled by normalized hash, then nonce, then fuzzy match, and every outcome is recorded (§3.3).
5. **Identity has two levels.** `session.db` holds live, core-minted handles and joins. Joins above a confidence bar are mirrored into the ledger as reversible events. An episode's identity state is computed from its joins, never asserted (§3.4).
6. **Axes are copied, never inferred.** Triggers reject an attribution that differs from its span (I3, I20), and an endorsement, authority tag or explicit goal without verbatim user-typed evidence (I4, I5, I22).
7. **Every mutable row has history** (`row_hist`), so as-of and changed-since queries are index lookups (§8).
8. **A Tension resolution is a record:** the ordered inputs per side, the deciding step, the margin class and the rule-set version. Undo is a compensating chain (§7).
9. **Corrections become constraints** that Apply checks on every proposal (I21). A CHECK keeps model-reported chat corrections `proposed` (I22).
10. **I1–I24 each have an exact rule, an enforcement point and a sweep query** (§9).
11. **Excision** is a resumable saga. It reaches every store, recorded model outputs, backups and the Markdown mirror. It blocks re-capture, survives crashes and restores, and ends with a raw-byte zero-hit check (§10). Time Machine is excluded at install, so every Northstar copy stays reachable ([PL] §2.5, UQ-14); vendor copies stay out of reach (RISK-CDM-1).
12. **Volume.** The "36K events a year" of [13 §I] counts knowledge candidates. This schema writes about 0.5M typed events and 1.3 GB a year at 100 turns a day; at 10× it still fits SQLite (§11).

---

## 1. Conventions and store map

| Topic | Rule |
|---|---|
| IDs | Prefixed ULIDs (`src_ msg_ obs_ sp_ ep_ cn_ st_ ps_ ag_ rl_ su_ tn_ tr_ cr_ ts_ jb_ mc_ ar_ agt_`). An item's prefix follows its role, which never changes. Versioned references read `st_91K@3` (TEXTBOOK §8.4). Handles are `NS-` plus 6 base32 characters, checked for collision; short handles are easier for a chat model to copy ([CD §4.2.5]) |
| Watermark | `event.seq`, local and monotonic. ULIDs order events across devices (SPINE §7.5 rule 4) |
| Portable types | ISO-8601 UTC text; JSON text with `json_valid`; `CHECK (x IN …)` enums; 0/1 booleans; no SQLite `STRICT` and no Postgres enum types |
| Canonical JSON | Sorted keys, no extra whitespace, decimals as 4-place strings, so replay hashes are stable (I18) |
| Tenancy | `tenant_id` on every table; `account_ref` on capture-rooted records (D-2) |
| `norm_hash` | sha256 of NFC, collapsed whitespace, Markdown artefacts removed, after secret redaction ([GD §7]). One function everywhere |
| Cross-file references | No foreign keys across files; each is checked by the sweep (§9.3) |
| Pragmas | WAL; `synchronous=FULL` on ledger, intake and jobs (MR-3); `foreign_keys=ON`; `secure_delete=ON` everywhere |

| Store | Writer | Tables |
|---|---|---|
| `intake.db` | C06 | envelope, observation, origin_confirmation, reported_point, delivery_receipt, capture_watermark, self_capture_match, excision_bar |
| `ledger.db` | C12; C19 during excision | event, event_subject, row_hist, apply_txn, applied_job · agent, source, source_key, source_join, message, message_observation, reconciliation(_point), span, episode, episode_message · item, item_tag, item_concept, concept, concept_alias, concept_broader, agenda, agenda_target, agenda_answer · attribution, stance, verification · relation, supersession, tension, tension_side, tension_resolution · correction, active_constraint · scope, tombstone |
| `session.db` | C10 applier (C23 through it) | session, session_conv_key, identity_join_event, turn_nonce, widget_instance, session_item, session_op, turn_receipt, continuity_receipt, context_receipt(_item), drift_verdict, queued_correction, routing_record, pending_resume, reexplain_hit, fast_model_call |
| `index.db` | C08 | best_rank, item_agent, fts_map, text_fts, embedding, edge_view, engagement_event, anomaly_mark, concept_facts, derived_agenda, goal_card |
| `artifacts.db` | C15 | artifact, artifact_shingle |
| `book.db` | C16 | landmark, landmark_label, redirect, build_record, build_input, leaf_home, sentence_cite, dirty_page (plus TEXTBOOK §12.2 tables, specified by C16) |
| `reader.db`, `ops.db` | C17, C21 | reader_state; metric, sentinel, invariant_violation, checkpoint, registered_store |
| `jobs.db` | C11 | job, model_call, proposal, validator_result, quarantine, error_budget, scope_lock, global_lock |

Every store also has `excision_run`; append-only triggers allow changes only on the excision connection, through an application-defined function registered only on that connection (or TEMP triggers), never through a persistent row. `excision_run` records progress only, so a crashed run can resume (§10.2); it grants no bypass (MR-5).

---

## 2. Canonical event catalog

### 2.1 How Apply writes

- **One proposal, one transaction:** events, `event_subject` rows, state rows, `row_hist` rows and the proposal's `applied_job` row (§6, MR-3) commit together. `row_hist` covers item, message, episode, source_join, agenda, relation, supersession, tension, correction and concept.
- **Insert order** (the triggers rely on it): spans → item → attribution → stance, verification → tags, concepts → agenda → relations → supersession, Tension.
- **Gate order:** I15 schema → I14 idempotency → I1, I2 provenance → I3, I20 speaker and origin → I4, I5, I22 authority (for spans from `hook`-channel observations, C12 also reads `observation.origin_confirmed` in `intake.db`, §3.1; no `confirmed` outcome, no long-term authority; `confirmed_degraded` is not enough) → I17 scope → I21 corrections → I13 blast radius per job → I16 time → risk routing (a worker proposal at medium or high tier without a C14 verdict → `awaiting_verify` (the [MT] §5.2 parity hold); a failed verdict → quarantine; user corrections and code events need none). Rejections are not events; C11 stores them in `validator_result`.
- **Every event carries** actor kind and reference (module, or model@version with prompt hash), origin for user actors, `proposal_id` with an index within the proposal (unique together, I14), job and batch IDs, risk tier, `inputs` (`obj@version` read), `compensates` and `config_v` (I19).

### 2.2 Catalog

C12 writes every event; "Proposer" sends it. Tier L, M, H per [13 §D]. I14 and I15 gate all events.

| # | Type | Key payload | Proposer | Tier | Gates |
|---|---|---|---|---|---|
| **Capture** ||||||
| 1 | `agent.registered` | agent, display name, vendor, product, surface, model, model_family | C06 | L | I23 (family is the only policy field) |
| 2 | `source.registered` | source, type, product metadata, connector, account_ref, title?, link template?, context_ref?, uri?, scope, sensitivity | C06 | L | I17, I20, C19 allowlist |
| 3 | `source.key_added`, `source.titled` | key kind and value; title and its source | C06, C10 | L | key unique; a title never comes from a model |
| 4 | `source.joined`, `source.join_reverted` | join, sources, method, confidence, session ref; reason | C10 via C06; C18 | M | join bar (§3.4); RISK 24 |
| 5 | `message.captured` | message, source, branch, ordinal or call index, role, speaker, agent, origin, model, grounding, time, hash, first observation, fidelity, speaker fidelity | C06 | L | I3, I16, I20, I24; path B writes no observation ([CX] §2.5) |
| 6 | `observation.linked` | message, observation, link role | C06 | L | same hash or a reconciliation |
| 7 | `message.reconciled` | recon, message, reported and verbatim observations, method, score, outcome, point results | C06 | M | I2; I20 (origins never change) |
| 8 | `message.speaker_moved` | message, from, to, recon | C06 | M | reconciliation evidence only |
| 9 | `span.anchored` | span, message, observation, locator, offsets, quote, prefix, suffix, speaker, agent, origin, fidelity, grounded, hedge?, scope, sensitivity, distressing | C06; J3 via its assembler | L | I1, I2, I3, I20 |
| 10 | `hygiene.flagged` | target; paste, imperative, PII ranges, distressing, Northstar block | C06 (J1) | L | I5, I24 |
| 11 | `branch.recorded` | source, from, to | C06 | L | — |
| **Episodes** ||||||
| 12 | `episode.segmented`, `episode.closed` | episode, source, branch, message range, context_ref, product, model, times | J2; C11 | L | contiguous, non-overlapping (key on `episode_message`), covering |
| 13 | `episode.identity_changed` | episode, from, to, cause | C12, in the join's transaction | M | computed, never proposed |
| **Items** ||||||
| 14 | `item.created` | item, role, tags, text, gist, qualifiers, primary concept, concepts, certainty, span size, holder, scope, valid_from, promoted_from?, attributions | J3; C18 (user note); [MT] suggested-topic job via C11 (off until UQ-10) | L for AI-said `encountered`, M for user beliefs, H for explicit goals, L for reported and inferred goals | I1, I3, I4, I5, I10, I16, I17, I22 |
| 15 | `item.revised`, `item.gist_verified` | new `content_v` and fields; verdict, verifier, family | J5; C14 | M; L | I10, I21; SD-21 |
| 16 | `item.status_changed`, `item.scope_changed` | from, to, reason | C11 (J11), C14 audit, J3; C19 | M–H | I6, I17, I21 |
| 17 | `attribution.added` | item, span, evidence role, modality, hedge, lineage, group, recon_id? | J3, J5; J1r (`FIDELITY_UPGRADE`: capture fidelity `reconciled` with `recon_id`, D-5) | L | I3, I4, I11, I20 (trigger) |
| 18 | `attribution.lineage_set` | attribution, lineage, group, receipt? | J5 | L | I11, B15; `northstar_echo` needs a context receipt in that session, or ([AC] D4) in any session of the same `speaker_model_family` within 90 days when the span has no fresh grounding |
| 19 | `stance.recorded` | item, attitude, evidence kind, span or correction, belief_from, belief_to? | J3; JF promotion; C18 | M; H when endorsing AI-said | I4, I16, I22 (trigger) |
| 20 | `verification.recorded` | item@v, checkability, status, verifier, family, independence flags, evidence, recheck | C14 | M | AD14, I11, SD-21, SD-38 |
| 21 | `concept.created`, `concept.label_changed` | label, aliases, broader, identity key; label, by | J3, J5; J8.2, C18 | L; M | I1; I21 (`fixed_label`) |
| 22 | `concept.aliased`, `concept.alias_reverted`, `concept.split`, `concept.reparented` | from, to (or into), method, verdicts; for a re-parent, broader parents before and after (`concept_broader`) | J5, C18; J8 via C16; J8c (`REPARENT`) | H | I12, I21 (`fixed_parent`, `forbidden_parent`), I13; [13 §D] high-risk path |
| 23 | `agenda.created` | agenda, kind, goal basis?, raised_by, agent?, targets, reason? | J3; JF promotion; [MT] suggested-topic job via C11 (off until UQ-10) | H for explicit goals; L for reported and inferred | I5, I22, SD-36; `suggested_topic` only when the UQ-10 flag is on |
| 24 | `agenda.status_changed` | field, from, to, reason | J5; C18; code (expiry) | H for goals | I5 (only user evidence moves goals), I21 |
| 25 | `agenda.confirmed` | origin (`verbatim_match`, `reader_click`, `app_click`), evidence, authority | C12 on reconciliation; C18 | H | I20, I22 (a click gives `book_only` unless TEXTBOOK Q6, asked as ARCH DQ-10(a), is yes; then `full`, §4.1) |
| 26 | `agenda.answer_linked` | question, answer | J5 | M | I1 |
| **Relations, supersession, Tension** ||||||
| 27 | `relation.recorded` | relation, from, to, type, confidence, creator, direction checked, status (proposed or applied), basis? (`advances_goal` only, §4.3) | J5; code at promotion (`goal_stack`); C18 (`user`) | L–M | I12 (`same_as`), I13, I21 |
| 28 | `relation.direction_checked`, `relation.status_changed` | verdict, checker, family; new status | C14; C18, J11 | M | SD-21; I21 |
| 29 | `supersession.applied` | old item@v, new item?, reason, evidence, causal_alt_ref?, resolution? | J5; C12 rules; C18 | H | I6, I11, I21; AD19 (§7) |
| 30 | `tension.opened` | tension, sides (item@v), detector | J5 | M | sides distinct |
| 31 | `tension.resolution_recorded` | step, outcome, winner?, inputs, decided_by, margin class, verify job?, rule-set version | C12 rule engine | H | AD19 order; 100% L4 audit |
| 32 | `tension.resolution_undone`, `supersession.undone` | resolution or supersession, compensates, cause | J11; C18 | H | — |
| 33 | `tension.reopened` | trigger (new evidence, re-check due) | C11 | M | — |
| **Corrections** ||||||
| 34 | `correction.proposed` | kind, target, payload, `proposed_via`, channel, expiry | C18 | L | I20; I22 (model-reported chat corrections stop here) |
| 35 | `correction.applied` | origin, constraint form, evidence span? | C18 | H | I20, I21, I22 |
| 36 | `correction.lifted`, `correction.expired` | lifted_by and ref; — | C18, C19; code | H; L | user undo, a later user correction, or excision only; proposals expire after 7 days |
| **Maintenance, privacy** ||||||
| 37 | `compensation.batch` | selector (job, batch or model@version), range, reason | J11 | H | I6: compensates, never deletes |
| 38 | `excision.applied` | tombstone, closure counts, stores purged, zero-hit | C19 | — | the only destructive event |
| 39 | `scope.hold_changed` | scope, held (0/1), rule ref, reason | C19 | H | I17, I19; §4.5 |

The table groups 51 event names into 39 rows. **Maintainer ops** map onto these names; [MT] owns the op→event map: `REPARENT` → `concept.reparented`; `FIDELITY_UPGRADE` → `attribution.added` with `recon_id` (no separate event); `SET_VERIFICATION` → `verification.recorded`; `ADD_EPISODE` → `episode.segmented`; `SUPERSEDE` → `supersession.applied`; rollback compensations → `supersession.undone`, `relation.status_changed` and `item.status_changed`, all under one `compensation.batch`. **Outside the ledger:** `intake.db` records (C06; I14, I24, the path-B CHECK; `observation.origin_confirmed`, §3.1); `session.db` operations ADD, REFINE, SUPERSEDE, RETRACT, MARK_CONTESTED, GOAL_PUSH, GOAL_POP, GOAL_SUPERSEDE, ASSUMPTION_CONFIRM and ARTIFACT_VERSION ([11] impl. 2) (C10; span string-match, user-only goals and constraints, I22). C23 seeds are `ADD` ops (§5); routing is a `routing_record` row, not an op. Also BookLedger events (C16; B7–B10); job records (C11; I13, I14, I19).

---

## 3. Capture: observations, messages, spans, identity

### 3.1 Observations (`intake.db`)

- **Kinds:** `full_text`; `reported_copy` (the model's copy of a user message); `reported_points`; `partial` (head and tail of a message over 4,000 characters: first and last 1,800 plus its length, one rule on every MCP host, [CX] §2.3). There is no hash-only kind (FEAS-1).
- **Reported points** ([CD] `established_last_reply`, [GD] `prev_reply_points`) are an observation of the previous reply, at most 5 rows (text ≤ 200, quote ≤ 120 characters, optional body ≤ 1,500 on explanation or example points, by CHECK): points about that reply, never a copy of it. Points from a closing call (`this_reply_points`) are rows with `reply_scope` `this`, attached to the same reply ([CX] §2.3).
- **Path B (and unrecorded turns under A or C2):** the stateless per-turn call writes no observation; only content-free operational logs (time, tool, status, latency) are kept, outside intake.db content tables ([CX] §2.5).
- **Observer double capture** ([OBS §4.3]): the composer value and the rendered transcript are two verbatim observations of one message. A mismatch is a capture alarm; agreement means `audit_truth = live_independent`.
- **Northstar blocks** ([OBS §4.4]) are cut out by exact match against `artifact_shingle` and stored as `northstar_injected` spans; an edited block is flagged and is never user-said (I5).
- **Secrets are never stored:** J1 replaces them before writing and records only kind and range. PII is kept, tagged, and redacted on egress (D-6).
- Observations are immutable outside excision (trigger).
- **Origin confirmation** ([HK] §8). Origin stays immutable (I20). For `hook`-channel `user_typed` observations, C06 later appends an `observation.origin_confirmed` record (`origin_confirmation`: obs_id, method `transcript_entry_type` or `template_continuation_hash`, outcome `confirmed`, `not_confirmed` or `confirmed_degraded`, time) from the transcript sweep's result. When the transcript reader is unavailable, C06 falls back to its own template and continuation-hash classification (method `template_continuation_hash`; no template match → `confirmed_degraded`) and reports the degradation to C21. **`confirmed_degraded`:** steers live, no long-term authority until the reader confirms or HK-S3 re-certifies the templates; a later `not_confirmed` triggers a C12 revocation (MR-4). C12's I5/I22 gate reads it (§2.1); live steering does not wait for it.

### 3.2 Canonical capture (`ledger.db`)

- **Source** is source-generic (SYN §3.1). Chat locator `{surface, conversation, message_id, branch_path, ordinal, call_index}`; document `{uri | file_hash, page?, char_range}`; `northstar_output` `{job_id, call_id, char_range}`, which anchors a suggested topic to its recorded job output (D-4). Reader notes are `note` sources with origin `user_typed`.
- **Message** groups observations (link roles capture, reported_copy, reported_points, all immutable); `best_obs_id` names the best one. Speaker, origin, agent and hash are immutable (trigger). Only reconciliation changes `best_obs_id`, `fidelity` and `recon_state`. A partial unique index keeps one message per (source, branch, ordinal, speaker).
- **Span** is insert-only and keeps its observation's fidelity. `reconciled` is an attribution value with a `recon_id` (D-5).
- **Episode coverage** is structural: `episode_message` is keyed by message.

### 3.3 Reconciliation by content hash

C06 runs it whenever verbatim text arrives for a conversation with model-reported observations ([GD §7], [CD §4.2.7]).

| Step | Rule | Recorded |
|---|---|---|
| 1 | Candidates: same join component, same role, within ±10 minutes (starting value) | — |
| 2 | Equal `norm_hash`; for `partial`, head and tail hashes match a prefix and suffix | `norm_hash` |
| 3 | The verbatim turn, or an exported tool result, carries the turn nonce (CD-S7) | `nonce` |
| 4 | Edit-distance ratio ≥ 0.9 (starting value), best unique match | `fuzzy`, score |
| 5 | Each reported quote must be a substring of the normalized verbatim reply | `quote_status` per point |
| 6 | **Matched:** verbatim becomes best; J3 re-anchors items on new verbatim spans, attribution fidelity `reconciled`. **Reported only:** items superseded, `reconciled_absent`. **Verbatim only:** added and counted as omission. **Other speaker:** `message.speaker_moved` | `message.reconciled` |

**Incomplete verbatim capture.** When the verbatim side is known to be incomplete (observer virtualisation, a partial export), J1r records `could_not_confirm`, not `reconciled_absent`, and supersedes nothing. Nothing is deleted. Copy fidelity, quote-verify, omission and fabrication rates come straight from these tables (RISK 25, 32).

### 3.4 Session identity: handles, nonces, joins

- **Live level** (`session.db`, C10): core-minted handles, `session_conv_key` joins with method and confidence, `turn_nonce`, `widget_instance`. It serves `session.resolve` in 50 ms. Join methods, in both stores: `exact_key`, `nonce_echo`, `widget_origin` ([CX] D7), `process_lineage` ([HK] D-HK-3), `content_hash_sequence`, `fuzzy_time_text`; `minted` is live-only.
- **Durable level** (`ledger.db`, C12): `source_key`, `source_join`, `episode.identity_state`. The Book and history read it.
- **Sync rule.** When C10 joins a key that belongs to another source with confidence at or above the **join bar** (0.9, calibrated by SP-7), it proposes `source.joined` with a `session_join_ref`. A revert in either store reverts the other. Joins below the bar stay live-only and never reach the Book. The sweep compares the two stores.
- **Identity state,** computed in Apply over the active join component: `identified` if any source has a hook session, transcript path, observer conversation or export conversation key; `session_only` if it has a minted handle or `openai_session`; otherwise `not_identified`. A title shows only if a joined source has a title source (TEXTBOOK §5.8). "Wrong conversation" reverts the join (`user_dispute`).
- **Keys per connector:** Claude Desktop L0, minted handle plus per-turn nonce ([CD §4.2.5]) and `widget_origin`; ChatGPT, `openai_session` (stability (Unv), CS11, S-R7); observer, the URL's conversation ID if Accessibility exposes it, else a title hash ((Unv), DS4), with its block tag as a nonce; hooks, session ID and transcript path, with MCP calls joined by `process_lineage`; exports, their conversation ID. **One turn-tag format** everywhere: `NS-XXXXXX.<n>` (handle, dot, turn; [CX] §2.3).

---

## 4. Knowledge: items, axes, relations, corrections

### 4.1 Items and goal authority

- One `item` table for the four roles, plus `concept` (label, identity key, `alias_of`), `concept_alias`, `concept_broader` (several parents) and `agenda`. Tags live in `item_tag`; concept links live in `item_concept`, with one primary by partial unique index.
- `content_v` rises only when text, gist, qualifiers or certainty change, which TEXTBOOK's memo keys cite. Other changes write `row_hist` only.
- No rank on items (D-1). Next steps and gaps are derived (§6), never canonical ([12] Model C).

**Goal authority** (I22, SD-36, TEXTBOOK §5.8, Q6), enforced by CHECKs on `agenda` and the `explicit_goal` triggers:

| Goal | Basis | Authority | Book | AI packs |
|---|---|---|---|---|
| Stated in a verbatim user span | explicit | full | Goals | goal slot |
| Known only from a model's report | reported | none | "Reported goals, not yet confirmed" | labelled reported slot, no authority |
| Reported, then a Reader or card click | reported | book_only | Goals, labelled "as reported" | reported slot, until Q6 is yes (configuration flag checked in Apply) |
| Reported, then a click, with Q6 (ARCH DQ-10(a)) answered yes | reported (`goal_status` keeps its values: active, paused, done, expired) | full, set by a click-bound `agenda.confirmed` (`reader_click` or `app_click`; never on the turn the goal was reported) | Goals, labelled "confirmed by your click; wording as reported" | goal slot, with the same label |
| Reported, then verbatim text matches | explicit (`agenda.confirmed`, `verbatim_match`) | full | Goals | goal slot |
| Inferred interest | inferred | none (CHECK) | "Possible directions", fading after 60 days | never a goal |
| Northstar-suggested topic (UQ-10) | — | none (CHECK); `raised_by = northstar` only for this kind | labelled, never shown as learned | — |

### 4.2 Attribution, stance, verification

- **`attribution`** links item to span with an evidence role (primary, support, user_evidence, answer, causal_alt). Speaker, agent and origin are copies of the span's, by trigger, and frozen. It also holds speaker fidelity, capture fidelity (with `reconciled`), modality, verbatim hedge, lineage and lineage group.
- **Lineage group** is the ID of a lineage's first primary span. An `ai_echo` shares its origin's group and counts once; a `northstar_echo` gets `ns:<receipt>` (CHECK) and counts zero (I11, B15). The receipt is from the same session or, per [AC] D4, from any session of the same `speaker_model_family` within 90 days when the span has no fresh grounding (vendor-memory loop, SYN RISK 11). `lineage` and `agent.model_family` give C21 the share of AI-said spans discounted as echoes, by vendor family (TEXTBOOK §13.2 B, SD-38 parity sentinel).
- **"Wrong speaker"** adds a `fixed_attribution` constraint; the adapter's role stays in the record (TEXTBOOK §9.1).
- **`stance`** (holder `user` only) and **`verification`** are append-only; the item keeps the current values. A CHECK refuses `supported`, `contradicted` or `mixed` without evidence (AD14).

### 4.3 Relations, supersession, Tension

- **`relation`**: the 18 SPINE types. Endpoints are items, relations or episodes (episodes for `example_of`, `applied_in`). A partial unique index stops duplicate live edges. `basis` is set only on `advances_goal` (CHECK): `goal_stack`, `j5`, `answers`, `user`, `reexplained` ([AC] §4.4).
- **`supersession`**: old item@version, new item, reason (SPINE's six plus `rank_resolution`, D-8), evidence, `causal_alt_ref`, resolution. CHECKs: only `reconciled_absent` lacks a new item; a rank resolution must cite its resolution.
- **`tension`**, `tension_side`, `tension_resolution`: §7.

### 4.4 Corrections and precedence

**Kind → constraint** (TEXTBOOK §9.1): misstated → `bar_text` + `quote_form` (barred hash required) · reject_content → `exclude` · attribution_fix → `fixed_attribution` · conversation_dispute → `fixed_identity` and a join revert · stance_fix → `fixed_stance` · relation_reject → `cannot_link` · hide, next_step_hide → `hide` · rename → `fixed_label` · placement_must, put_back → `fixed_parent` · placement_must_not → `forbidden_parent` · pin → `pin` · merge → `must_link` · unmerge → `cannot_link` on `same_as` · goal_status, question_status → `fixed_status` · goal_confirmation → `agenda.confirmed`.

**Origin** is one of TEXTBOOK's four and is set only when a correction is applied; a proposal records `proposed_via` (`chat_model_reported`, `chat_unmatched`). CHECKs: applied needs an origin; chat origins need an evidence span; proposals need an expiry.

**Precedence, enforced by Apply:**
1. An active constraint beats every automated proposal; Apply looks up each subject and object a proposal touches (I21).
2. Between user corrections in one family (must/cannot link; fixed/forbidden parent; label; status) on one subject, the later wins; the earlier is lifted as `superseded`.
3. A proposal constrains nothing and expires silently after 7 days; nothing queues (GOAL §4.1).
4. Later evidence never lifts a correction; it only sets a chip flag (TEXTBOOK §9.5).
5. Only user undo, rule 2 or excision lifts one (CHECK and trigger).

### 4.5 Scope and sensitivity

Every source, span and item has a scope and a sensitivity tier, with the vocabulary of [PL] §6.1 (C19 owns the policy). **Scope kinds:** `personal`, `project` (`project:<id>`), `work` (`work:<org>`), `unclassified` (`unclassified:<repo_hash>`, treated as work), `session` (`session:<handle>`), `eval`. **Tier** (`sensitivity` column): `normal`, `sensitive`, `private`; `private` is a tier only, never a scope kind. A separate `distressing` flag follows TEXTBOOK D7, H6. **Held** ([HK] §7 late reclassification) is a flag, not a scope kind: `scope.held` (ledger, set by `scope.hold_changed`) and `session.held` (`session.db`, C10 applier). C19 sets it on the matched sessions and their per-repository scope. Held content gets no egress, no packs and no Book: C15, C16 and C20 filter on it with I17. Excision stays the user's choice. Egress rules per scope and vendor family are C19 configuration (I19); each model call records its policy version.

### 4.6 What the triggers enforce

| Triggers (companion file) | Rule |
|---|---|
| `attribution_axes`, `attribution_axes_frozen` | I3, I20: speaker, origin and agent equal the span's and never change |
| `stance_endorsement` | I4, I22: `asserted` or `accepted` needs a user-typed, non-model-reported span |
| `authority_tag`, `explicit_goal`, `explicit_goal_upd` | I5, I22: instruction, preference and constraint tags, and explicit goals, need that span; a reported goal turns explicit only on a verbatim match |
| `message_immutable`, `observation_no_update`, `span_no_*` | I20: capture fields never change |
| `*_no_upd`, `*_no_del`, `row_hist_close_only` | I6: append-only except on the excision connection (§1) |
| `apply_txn_no_del`, `session_op_no_del`, `correction_no_del`, `active_constraint_no_del`, `attribution_no_del`, `tombstone_no_del`, `reconciliation_point_no_del` | I6: these rows are never deleted outside excision; status changes go through `row_hist` |
| `relation_endpoints` | MR-9: `from_id` and `to_id` each exist in `item`, `relation` or `episode`; an abort here is a code fault |
| `correction_lift` | I21: lifting needs a recorded reason |
| `path_b_no_items` | SPINE §5.5: a session item for a turn needs `persist_policy` `full`, or `on_write` with a declared write recorded that turn (§5) |

One rule is a sweep check, not a trigger: an item with status `superseded` has an active `supersession` row (§9.3). Postgres gets the same triggers in PL/pgSQL, plus `REVOKE UPDATE, DELETE` on append-only tables, at the cloud-adapter stage (§8.3).

---

## 5. Session store (`session.db`)

- **`session`:** handle; account and its source (`channel`, `install_declaration` or `ax_label` from the observer, [CX] §6.1; RISK 35); connector and product metadata (I23); declared capabilities and MCP flags; start kind; parent handle; context_ref; arm; `persist_policy`; scope; `held` (§4.5).
- **`persist_policy`** is derived by C04 from the connector manifest's `capture_mode`: `full`, `none` or `on_write`. The guard is per turn: a session item for a turn is allowed when the policy is `full`, or `on_write` and a declared write was recorded that turn (CONS-9).
- **`session_item`** uses the item schema's names plus session fields ([11] impl. 1): `by_` (user, ai: always the original speaker, seeds included), goal level, constraint force, user reaction, reason, source turn and span, status, authority (`provisional` for in-session verbatim, `confirmed` for seeded long-term items, `reported`; [IS] uses these names), `seeded_from`, `promoted_to`, branch. **Seed fields** ([AC] §5.1): `seeded_from {item: item_id@version, artifact_hash, delivery_receipt}` (key `item`, as the DDL; the same in [IS] and [AC]), `seed_kind`, `delivery` (`delivered`, `unknown`, `guard_only`), `on_route`. CHECKs: a constraint needs user-typed, non-model-reported text (seeds copy their source span's axes) or is held as `reported`; an item without `seeded_from` cites a span; seed fields are set together or not at all.
- **`session_op`** is append-only, with a unique idempotency key per (session, branch, turn, message hash, operation). A seed is an `ADD` op with actor `seeding` and `actor_ref` = the `continuity_params` version; there are no SEED or ROUTE op types.
- **`pending_resume`** ([IS] §9.3, restart level `suggested`): parent handle, resume-pack artifact and hash, goal IDs, created, expires (24 h), state (`pending`, `adopted`, `expired`, `reverted`), adopting handle, `adopted_via` (`explicit_handle` or `c23_route`, as the DDL; the same in [IS] and [AC]) and route p. The C10 applier is its single writer; C23 reads it when routing. Adoption needs an explicit handle, or a C23 route with p ≥ 0.7 ([AC] §4.2). It sets the new session's `parent_handle` (lineage, labelled) and is reversible (`reverted`).
- **Receipts:** `turn_receipt` (SPINE §4.5); `continuity_receipt` (`written_late` when verbatim text comes later); `context_receipt` and its items (item@version, slice, text hash), indexed by session and by item.
- **Also:** `drift_verdict`, `queued_correction` (`weak` for self-report checks), `routing_record`, `reexplain_hit`, `turn_nonce`, `widget_instance` ([CD §4.2.4] `{createdAt, seq}`; [GD §6.2.4] `openai/widgetSessionId`), `fast_model_call` (D-7).
- **Recent window** (SPINE §5.5): provisional items from sessions ended within 14 days, newest first.

---

## 6. Projections and jobs

| Store | Contents and rules |
|---|---|
| `index.db` (C08) | **`best_rank`**, a deterministic function of recorded axes (SYN §3.1 step 3). `ver_tier`: supported 3; mixed 2; unchecked, not_checkable, cited_unchecked and `no_independent_verifier` 1 (SD-38); contradicted 0. This order is binding for every ranker, so [AC]'s `ver` scores mixed above the unchecked tier. `lineages`: distinct groups (I11). `grounded`: browsing or tools. `recency`: time-sensitive items only. **Speaker is never an input.** `rank_group` spans active supersessions, Tension sides and `same_as`; `is_best` marks the head; both contested sides stay best, in slot `contested`. Constraints clear `book_eligible` (`exclude`, `hide`) and `pack_eligible` (`exclude`); agenda authority sets `pack_slot`. **`item_agent`** answers "what did X tell me". **`text_fts`**: contentless FTS5 with `contentless_delete` and `secure-delete` (PF-1). **`embedding`**: keyed by object, version and model; f16. **`edge_view`**: TEXTBOOK §7.2 weights. **`engagement_event`**: dated and span-linked, no state; derived by code (`explained_to` from AI explanation, definition or example leaves on the concept; `asked_about` from user questions; `used` from `applied_in` links on user spans; `restated` from user restatement lineage). **`concept_facts`**: facts about the content (an explanation leaf exists, mentions, independent episodes, substantive teaching) for TEXTBOOK §4.7 and §6.3, never about the user. C08 computes the substantive-teaching flag in code; no model sets it (R14, [TB] §4.7). **`derived_agenda`**: the TEXTBOOK §6.4 score in code, read by C16 and C23. **`goal_card`** ([AC] §4.1): per candidate goal, its text and aliases, target-concept labels, gists of its top 8 linked items, open questions, `context_ref`s and titles of sessions where it was active, last-active time; in FTS and embeddings; rebuilt on `ledger.committed` and on session goal changes, so C08 reads `session.db`. **`anomaly_mark`**: C08 writes one (kind `misfit`) for each J5 `misfit {item, concept}` output ([MT] J5), on that concept's page; J8c reads them as split candidates (TEXTBOOK §7.9) |
| `artifacts.db` (C15) | `artifact` (kind incl. `prefill` for restart messages; items@version; watermark; budget; truncations; text; unique hash); `artifact_shingle` (8-token window hashes) for I24 and echo containment (0.6, TEXTBOOK §5.9) |
| `book.db` (C16) | `landmark` (a non-active landmark must redirect), `landmark_label`, `redirect`; `build_record` (watermarks, inputs and output hashes, config) and `build_input` (obj@version, "built from"); `leaf_home` (B5); `sentence_cite` (B1, I8); `dirty_page`. **Canonical for restore:** BookLedger, Edition and the landmark tables are path-dependent (J8 snapshots, landmark weights; TEXTBOOK §7.2, B10) and cannot be rebuilt from the core ledger, so they are backed up and restored; only BlockVersion renders are rebuilt (§11) |
| `reader.db`, `ops.db` | `reader_state`: private, never read by C15, switchable off, covered by excision. A per-page open counter, exposed to C16 only as the derived `landmark_signals` vector, never as raw counts; it is a navigation signal for landmark weights, never a claim about what you know. Metrics, sentinels, `invariant_violation`, `checkpoint` (rolling table hashes), `registered_store` (every file that may hold content, including C22 snapshots) |
| `jobs.db` (C11) | `synchronous=FULL`. `job` (one unique `idem_key`, as [MT] §3.3 defines it (I14); `config_v`; lane; `state` with the full [MT] §3.1 machine: queued, leased, calling, awaiting_batch, validating, awaiting_verify, ready, held, applying, done, then the terminal outcome; lease owner, `epoch` and expiry, so Apply rejects a stale epoch; attempts; batch); `model_call` (provider, model as returned, family, prompt hash, input fingerprint and IDs, egress policy version, raw and parsed output, tokens, cost, fault tag); `proposal`; `validator_result`; `quarantine` (deadline, at most 3 attempts by CHECK, exit route); `error_budget`; locks. **Model calls store input IDs, never assembled input text**, so outputs are the only content to excise. **Counterpart in `ledger.db`:** `applied_job(job_id, proposal_id, output_hash)`, written in Apply's transaction (§2.1). The ledger is the truth for "applied": after a crash between the two files, a job left in `applying` is settled from it and never applied twice (MR-3). Postgres leases use `SKIP LOCKED` |

**No engagement state anywhere:** a lint fails the build if a DDL column name matches `mastery|known|confus|understood|level`, except `goal_level` (TEXTBOOK Q5).

---

## 7. Supersession and Tension resolution as data

### 7.1 Ordered rule inputs (SYN §3.1, AD19)

J5 opens a Tension. Resolution is code in Apply over recorded axes only. Per side it snapshots into `tension_resolution.inputs`:

```yaml
{item: st_91K@3, holder: assistant, self_held: false, qualifiers: {...}, ver_status: supported, ver_tier: 3,
 verifier_family: "local:x", independent_of_speaker: true, lineage_groups: [sp_1, sp_9], lineages: 2, grounded: 1,
 valid_from: "2026-09-12", time_sensitive: false,
 explicit_signals: [{kind: ai_self_correction, span: sp_77, follows_pushback_without_evidence: false}],
 active_constraints: [cr_12]}
```

Beside the per-side snapshots, the inputs record any **audit dissent** on this Tension: the resolution an L4 audit undid, the auditor and its finding (MR-12).

| Step | Rule | Recorded |
|---|---|---|
| 0 | An active user correction on either side decides | `user_correction` |
| 1 | The sides differ in a qualifier (valid time, context, version, population) | `both_stand_scoped`, the qualifier |
| 2 | (a) A later user statement on a self-held item (the user's own goals, decisions, preferences, plans); (b) an AI self-correction, **unless** it directly follows user pushback with no new evidence (then step 4); (c) a `contradicted` verdict with evidence from a family other than the speaker's | `superseded` with that reason |
| 3 | Lexicographic: `ver_tier`, `lineages`, `grounded`, then `recency` (time-sensitive only). Speaker is never compared | `superseded`, `rank_resolution`, the first differing component |
| 4 | `clear` only if decided by `ver_tier`, or by `lineages` with a gap of at least 2; `narrow` cases get one search-grounded verification by a family other than both speakers', then re-rank | `margin_verified`, the verify job |
| 5 | Still tied, or not checkable, or the last resolution was undone by audit (taken straight here) | `contested`; a spawned question (`raised_by = conflict`); `next_recheck` |

Thresholds are versioned configuration, recorded as `rule_set_v` (I19).

### 7.2 What is recorded, and how it is undone

One transaction records the resolution with full inputs; for `superseded`, also a `supersession` row citing it, and the loser's status change; then the Tension state and current resolution. Every resolution is high tier, so C11 enqueues a 100% L4 audit, recorded in `audit_state`. A disagreeing audit triggers automatic undo, never a user task. Its dissent is recorded as an input of the next resolution, which goes straight to step 5: `contested`, a spawned question and a recheck date (MR-12).

| Trigger | Chain, in one transaction |
|---|---|
| Audit disagreement | `tension.resolution_undone` → `supersession.undone` for each linked row → loser `active` → a new resolution at step 5 (Tension `contested`, a spawned question, `next_recheck`), with the dissent in its inputs |
| J11 rollback by job, batch or model; rule-set change | `tension.resolution_undone` → `supersession.undone` for each linked row → loser `active` → Tension `open` → C11 re-queues |
| User undo of a correction | The correction is lifted, then the same chain; re-resolution sees the remaining constraints |
| New evidence, or a re-check date, on a contested Tension | `tension.reopened`; a new resolution; old rows stay |

`row_hist` keeps every prior state, so the Book shows the outranked side with its reason (TEXTBOOK §7.5, §7.8). **Sentinels (C21):** oscillation (superseded, restored, superseded within 30 days; its hold puts the Tension in state `contested`); pile-up (count and age of open and contested Tensions, RISK 22); parity (rank losses by speaker family against Tension sides by family, GOAL §4.2).

---

## 8. Query layer and repository ports

### 8.1 Queries (TEXTBOOK §12.1, SPINE §5.6)

| Query | Implementation | Index |
|---|---|---|
| Best-rank projection | `best_rank` by allowed scopes, eligibility and `is_best`, ordered by tier and lineages, joined to goal links | `best_rank_pick`, `relation_to` |
| As of a time | `W = max(seq)` recorded by then; the `row_hist` row with `rec_from_seq ≤ W < rec_to_seq` (or open). Best-rank as of W is C08's function over those snapshots | `row_hist` key, `event_time` |
| Changed since W | `SELECT DISTINCT subject_id FROM event_subject WHERE seq > W` | `event_subject_seq` |
| Dirty set for a printing | Changed since the last published printing's `ledger_seq`. Relation, attribution, verification and constraint events list their items as subjects. Pages via `leaf_home` and C16 memo keys | as above |
| Subgraph by relation type | Recursive CTE over `relation`, type-filtered, status applied or user-confirmed, depth-bounded, minus `cannot_link` | `relation_from` |
| Receipts by session | Context receipts and items by handle and time; reverse by item for the echo guard (same session, or same family within 90 days, [AC] D4) | `context_receipt_session`, `_item_rev` |
| Recent provisional | §5 | `session_item_recent`, `session_ended` |
| "What did X tell me about Y?" | FTS → `fts_map` → `item_agent` → `best_rank` | FTS |

### 8.2 Repository ports

Components reach storage only through these protocols (SPINE §7.5 rule 1): a SQLite adapter now, Postgres later, one contract suite for both.

| Port | Writer | Main calls |
|---|---|---|
| `CaptureStore` | C06 | `put_envelope`, `put_observation`, `watermark`, `bar_check` |
| `LedgerWriter` | C12 only | `apply(proposals) -> txn | rejections` |
| `LedgerReader` | all | `get(id, as_of)`, `changed_since`, `events_since`, `subgraph`, `join_component` |
| `SessionStore` | C10 | `resolve`, `apply_op`, `receipts`, `recent_provisional`, `pending_resume(handle \| goal_ids)` (read by C23) |
| `IndexPort` | C08 | `best`, `search_text`, `search_vector`, `concept_facts`, `derived_agenda` |
| `ArtifactStore`, `BookStore` | C15, C16 | put, get, shingles; builds, leaf homes, dirty pages |
| `JobStore`, `Recorder` | C11; C11 and C10 | enqueue, lease, complete; `record_call` |
| `BlobStore`, `Outbox` | C06; each writer | content-addressed blobs; emit, poll |
| `ExcisionPort` | per store, executed inside that store's own writer; C19 orchestrates and runs the `ledger.db` port itself | `closure`, `purge`, `verify -> hits` |

### 8.3 Postgres mapping (cloud later)

One schema per store with row-level security on `tenant_id`; `seq` as an identity column; `jsonb` (`json_array_length` → `jsonb_array_length`); CHECK enums, partial indexes, recursive CTEs, `ON CONFLICT` and `RETURNING` unchanged; PL/pgSQL triggers plus `REVOKE`; FTS5 → `tsvector` with GIN; embeddings → `pgvector`; job polling → `SKIP LOCKED` or a managed queue; outbox → queue; the excision bypass → an excision role and a transaction-local setting, plus an advisory lock. **Postgres triggers and the Postgres CI matrix are deferred to the cloud-adapter stage** (CPLX-9). CDM-S4 checks the DDL on Postgres once now, including forward foreign-key order.

---

## 9. Invariants as concrete checks

### 9.1 I1–I24

"Sweep" is the nightly read-only J10 run (§9.3); hits go to `ops.invariant_violation`.

| ID | Exact rule | Enforced at | Detected after the fact |
|---|---|---|---|
| I1 | Every non-excised item has an active primary attribution whose span exists and whose observation exists (or whose document or `northstar_output` locator resolves) | C12; FK | Sweep: items without a primary; dangling observations |
| I2 | `normalize(quote)` = `normalize(text[start:end])` of its observation; prefix and suffix match | C12 (reads intake); C16 for quotes (B3) | Sweep: all new spans plus 1% of older ones |
| I3 | Message speaker from the connector role map; span = message; attribution = span; no proposal schema has a speaker field | Trigger; schema; conformance (SPINE §4.9) | Sweep: three-way join |
| I4 | Endorsement only with a verbatim user-typed span; AI-said defaults to holder `assistant`, stance `none` | Trigger; C12 | Sweep |
| I5 | Instruction, preference, constraint tags and explicit goals only with such a primary or user-evidence span | Triggers; session applier | Sweep |
| I6 | No UPDATE or DELETE on append-only tables; `row_hist` only closes; the only exception is the excision connection (§1) | Triggers; REVOKE | Rolling table hashes in `ops.checkpoint`: a changed old range is a violation |
| I7 | J7 inputs are leaf IDs and span text only | C16 assembler | Sweep: block-version manifests with other kinds |
| I8 | R sentences and headings cite ≥ 1 leaf; B sentences ≥ 2 leaves and a relation; cites active or historical | C16 V1, V2 | Sweep over `sentence_cite` |
| I9 | Leaves covered in printing n−1 but not n have a drop event between the builds | C16 V9, B5 | Sweep: `build_input` difference against `event_subject` |
| I10 | A verbatim hedge on a primary span caps certainty below `firm` unless ≥ 2 independent groups support it | C12 | Sweep |
| I11 | Lineages count distinct groups; echoes as in §4.2; a `supported` verdict cannot cite an echo of the same item | C12; C08 | Sweep: recompute against `best_rank` |
| I12 | An alias needs an identity-key match or two agreeing verdicts from different families; aliases are acyclic; reverts restore members | C12; CHECK | Sweep: alias cycles |
| I13 | Per job, events ≤ N and nodes touched ≤ M (configuration) | C12; over → reject all, quarantine | Sweep: events per job |
| I14 | Unique envelope key, job key, (proposal, index) per event, session-op key | UNIQUE | Replay-twice conformance test |
| I15 | Proposals validate against the versioned JSON Schema plus code checks | C12; CHECKs | Sweep: `json_valid`, enum scans |
| I16 | `valid_from ≤ recorded_at`; `belief_from ≤` the span's capture time | C12 | Sweep |
| I17 | Everything has a scope; packs, slices, the Book and model inputs include only allowed scopes | NOT NULL; C15, C16, C20 | Sweep: receipt items outside session scopes; model inputs against their policy version |
| I18 | Replaying `event` into empty tables gives equal table hashes; deterministic projections rebuild hash-identical with models off | Canonical JSON; explicit ordering | Weekly replay; nightly checkpoints. An independently written reference projector, sharing no code with Apply, replays events in CI and in the weekly replay; its tables must equal Apply's (MR-11) |
| I19 | Invariants, thresholds, prompts and golden sets are versioned files outside every store; stores hold only `config_v` | Lint | Sweep: each recent `config_v` is committed |
| I20 | Origin set at write by C06; spans insert-only; message capture fields frozen; items have no origin column | Triggers; schema | Sweep: attribution against span origin |
| I21 | No automated event contradicts an active constraint; lifting only by undo, a later correction or excision | C12; C15, C16 per artifact and page (B6); CHECK, trigger | Sweep: evaluate every active constraint on current state |
| I22 | Authority needs verbatim user-typed evidence, or a `reader_click`/`app_click` origin where TEXTBOOK §9.2 allows; a click gives a reported goal `book_only` unless the Q6 flag is on | Triggers; CHECKs; C12; session applier | Property tests; sweep |
| I23 | No product, mode or connector names in core packages, and no SQL predicate on product columns outside display and analysis | Lint on code and SQL | Product-blindness test (SPINE §4.9) |
| I24 | Ranges matching an artifact shingle or a Northstar marker get a `northstar_*` origin; worker calls are never captured | C06; `self_capture_match` | Sweep: user-typed spans hitting artifacts above 0.6 |

### 9.2 Book invariants (TEXTBOOK §8.11): data support

C16 owns the checks; this document owns the data. B1, B8: `sentence_cite`, `redirect`, `landmark.status` · B2: typed input manifests · B3: attribution capture fidelity · B4: V4's lexicon is the `agent` registry plus generic agent nouns, applied as speakers of speech or stance verbs ([TB] §8.5) · B5: `leaf_home` · B6: `active_constraint` · B7, B9: BookLedger events · B10: build hashes and `config_v` · B11: `best_rank.speakers`, `item_agent`, `concept_facts` · B12: sentence kinds · B13: hedge and certainty · B14: scopes · B15: lineage · B16: §10.2 step 4.

### 9.3 The sweep

J10 attaches every store read-only and runs one query per row of §9.1, plus cross-file checks: observation IDs referenced by spans and reconciliations exist; active joins above the bar agree between `session.db` and `ledger.db`; receipt, promotion and artifact items exist; no index row is orphaned (an orphan means a missed purge); applied proposals' transactions exist. Added by the review:
- **Ledger → jobs orphans** (MR-3): every `applied_job` row has its job in `jobs.db`, and that job is settled as applied.
- **Dangling relation endpoints** (MR-9): every `from_id` and `to_id` resolves to an item, relation or episode.
- **Revoked hook authority** (MR-4): an authority-bearing item whose hook evidence has a `not_confirmed` origin record is an I22 violation.
- **Supersession state:** an item with status `superseded` has an active `supersession` row (this also catches an excised winner whose loser was not restored, §10.1).

Structural checks (I1–I6, I11–I15, I17, I20–I24) must report zero. A hit raises a C21 sentinel. **The action:** freeze the producing job type, except capture, correction and compensation types; capture violations alert and route to a C06 fix. C11 then runs J11 repair. Nothing becomes a user task.

### 9.4 Tests already run

On 2026-10-08, before the consistency and review edits, every store section of the companion file executed on SQLite 3.53.1 (PF-1), and 37 checks passed. **Blocked:** an attribution unlike its span; an instruction, an endorsement and an explicit goal from model-reported spans; a reported goal made explicit without a verbatim span; a suggested topic with authority; a question raised by Northstar; an applied correction without origin; a lift without reason; event update and delete; raising an origin; a rank supersession without a winner; `supported` without evidence; a duplicate idempotency key; text on a hash-only observation (check retired: the hash-only kind is gone, FEAS-1); a sixth reported point; a path-B steward item; a model-reported session constraint with authority; a non-pack session item without a span; deleting an observation outside excision; a replayed proposal event. **Allowed:** the same writes with valid evidence; a click confirming a reported goal in the book only; a pack-seeded constraint; a model-reported constraint held as `reported`; several events from one proposal; excision redacting an event. A contentless FTS delete removes the match.

**Status:** Not yet re-run after the 2026-10-08 consistency and review edits. Re-running every check on the updated DDL is a Stage 0a task; until then the results above are historical.

---

## 10. Excision

Excision runs as a **resumable saga** (MR-5): it writes what it will remove before it removes anything, so a crash at any point resumes instead of leaving a half-purged store.

### 10.1 Closure

- **The user, or a standing policy rule shown at install ([PL] D-PL-5), starts it.** The user starts it from the Reader (with confirmation) or `northstar excise`. A policy rule fires only on a recorded deterministic signal, never on a model's judgment. Targets: an item, span, message, conversation (with its join component), scope, or a text query.
- **Closure, computed by code and shown before the user confirms** (a policy run is listed on the privacy page instead): target → messages → observations and blobs → spans → attributions. An item is in it if any primary span is, or if its text contains a needle. Items where an excised span is only support lose that attribution and stay. Then everything derived: relations, supersessions, Tension sides, agenda links, corrections on targets, quoting session items and ops, receipts, artifacts, book blocks, index rows, recorded model outputs.
- **Provenance closure,** bounded to text-bearing derivations. Model-written objects that consumed closure text as a support span, a revise input, a `build_input` or a `sentence_cite` are re-derived without it, or redacted. This catches paraphrases a lexical needle misses. Jobs that read an item only as neighbour context are not in the closure.
- **Supersession winners.** Excising a supersession's winner restores the loser to `active`, or re-resolves it when a Tension is open (§7.2), so excision never hides the other side.
- **Needles:** normalized 8-token shingles and every exact quote of 20 or more characters. Plaintext needles are held in memory and, so a crashed run can resume, in an encrypted needle file (key in the Keychain) kept until the report step ([PL] X10). After that only HMACs keyed by a per-tombstone Keychain key are kept, so later re-checks need no plaintext.

### 10.2 Run: the saga, store by store

1. **Lock, then record the intent.** C19 takes `global_lock('excision')`, a lease renewed by C19's heartbeat, so a crashed run's lock expires instead of blocking. Before any purge, C19 durably writes the tombstone (state `in_progress`), the HMAC needle set and the closure IDs to the ledger and to the external restore registry (§10.3), and writes the encrypted needle file. It then emits `excision.begin(targets)`; C06 keeps spooling new envelopes (SD-29) and replays them afterwards.
2. **Purge.** Each store's own writer opens its excision connection (§1), records progress in `excision_run` and executes that store's `ExcisionPort.purge`, so single writers hold ([PL] §6.7 X5). C19 does this itself only for `ledger.db` (SPINE §6.1 exception). **Each purge is idempotent and re-entrant:** running it again, or after a crash midway, gives the same result.

| Place | Action |
|---|---|
| `intake.db` | Delete observations and points; null envelope metadata; add `excision_bar` rows |
| `ledger.db` | Delete closure state rows. Events stay in sequence with text fields replaced by `"[excised:ts_…]"` and `excised = 1`; `row_hist` likewise. Items stay as `excised` stubs whose text is the tombstone marker, so IDs resolve to "removed at your request on [date]" (TEXTBOOK §7.5). Corrections on targets are lifted (`excision`). A supersession whose winner is excised is undone, and its loser restored or queued for re-resolution (§10.1) |
| `session.db` | Delete quoting items, ops, verdicts and queued corrections; replace receipt text hashes of closure items with `excised` (a short text's hash is guessable) |
| `index.db` | Delete rank, FTS (contentless delete with `secure-delete`), embedding, edge, engagement, anomaly and agenda rows |
| `artifacts.db`, `book.db`, `reader.db` | Redact artifact text and delete shingles; re-render pages; redact old block versions, editions and slice caches; delete leaf homes and reader rows for removed pages |
| `jobs.db`, `fast_model_call` | Copy providers and batch IDs into the tombstone's `external_copies`; then redact raw and parsed outputs, proposals and quarantine bodies with needles or closure IDs; `excised = 1`, so replay yields "excised" |
| Registered stores (incl. C22 snapshots), blobs, spool, the hook pin cache `run/pincache`, `tmp/`, `run/workers/`, `book/`, mirror folder | Delete or rewrite |
| `backups/` and the named drive ([PL] §2.5) | Each encrypted archive is purged and re-encrypted under a new key, and the old key is deleted; any that fails is deleted. Archives on the drive the user named (UQ-14) are rewritten when next mounted, shown as pending, no action asked ([PL] §6.7 X8) |

3. Physical cleanup: `secure_delete` is always on; then WAL checkpoint (TRUNCATE), FTS5 `optimize`, `VACUUM` on touched files.
4. **Zero-hit check (B16).** The haystack is one rule, as [PL] X9: every registered store plus every file under the data root, including `run/pincache`, `tmp/` and `run/workers/`, searched as raw bytes, plus the mirror folder and `~/Library/Logs/Northstar/` (SQLite stores text uncompressed; compressed files are decompressed first; archives are decrypted in memory), plus FTS matches and orphan-ID checks. Pass only at zero. **On failure:** one more purge, then a C21 alert with locations; the saga stays `in_progress` and resumes at the next boot and nightly. A run never ends silently.
5. **Close.** Set the tombstone's state to `done` in the ledger and the registry; write the ledger event `excision.applied`; delete the encrypted needle file ([PL] X10); close runs; release the lock; emit the internal event `excision.done(target)`; recompute replay baselines (I18).

**Resume.** At boot, any `in_progress` tombstone resumes from its recorded closure and needles before `northstard` accepts traffic. The nightly run retries any saga still open.

### 10.3 Re-capture and restore

- **Re-capture bar:** C06 drops any new observation whose hash or shingles match `excision_bar` (keyed HMACs), so an observer sweep or export backfill cannot bring the text back.
- **Restore safety:** tombstones (state, IDs and keyed HMACs, never content) are written to `~/Library/Application Support/Northstar-excision/registry.json` before any purge (§10.2 step 1), outside the data root and its backups. At start, `northstard` re-applies any excision missing from restored stores, and resumes any `in_progress` one, before accepting traffic.

### 10.4 Out of reach

- What vendors already hold: app history, vendor memory, and model-provider retention of API and Batch requests (SYN §5 item 9; provider terms (Unv) here). The tombstone lists them.
- **Synced mirror copies** of the optional Markdown mirror. RISK-CDM-1.
- **Time Machine is not a gap by design.** `~/Library/Application Support` is included in Time Machine by default, so install checks inclusion and excludes the data root (PF-2; `tmutil addexclusion`, [PL] §2.3, §2.5), and `northstar doctor` reports if the exclusion is removed. Durability comes from Northstar's own encrypted archives and an optional named drive (UQ-14).

---

## 11. Volume and performance

[13 §I] assumes 100 turns a day, ~1,100 tokens a turn and ~100 candidates a day: the "36K a year". This schema writes more typed events per candidate. Estimates are ±2×.

| Per year | 1× (100 turns a day) | 10× |
|---|---|---|
| Knowledge candidates | ~36K | ~365K |
| Observations / messages / spans | ~110K / ~73K / ~110K | ×10 |
| Items created (~40 active leaves a day, TEXTBOOK §8.10) | ~15–25K | ~150–250K |
| Ledger events (~700 capture a day + ~7 per candidate) | **~0.5M** | **~5M** |
| Session ops and receipts / model calls | ~0.2M / ~130K | ×10 |
| Storage: intake / ledger / jobs / index / other | ~300 / 350 / 400 / 100 / 150 MB | ×10 |
| **Total** | **~1.3 GB** | **~13 GB** |

| Path | Budget | How |
|---|---|---|
| Pin | p95 < 300 ms (SPINE §7.2) | Never touches `ledger.db`: C15 builds the pin; C10 holds the core cache of the last validated state |
| Core pack | p95 < 1.5 s | `best_rank_pick` plus goal links: tens of ms at 10× |
| Apply per proposal | < 50 ms | Indexed gates; a single writer, so no lock waits |
| As-of, changed-since, receipts | < 20 ms | B-tree lookups |
| Subgraph, depth ≤ 4 | < 100 ms at 10× (~30K concepts, ~200K relations), (Unv) until CDM-S1 | Index and depth bound |
| Vector top-k | ~5 ms at 1× (~40K × 1024 f16, brute force); ~50 ms at 10× | Behind `IndexPort`; an extension if SP-1 finds one; int8 halves memory |
| Full replay (I18) | < 1 min at 1×; ~5 min at 10× (~20K events/s, estimate) | Weekly; checkpoints nightly |

**Growth.** Backups follow [PL] §2.5: encrypted archives, 7 nightly plus pre-operation copies, Time Machine excluded. Restore treats as canonical intake, ledger, session, jobs and, in `book.db`, BookLedger, Edition and the landmark tables (§6); index, artifacts and BlockVersion renders are rebuilt instead. At 10×, intake and jobs gain yearly cold partitions (read-only, compressed, attached on demand). The ledger stays one file, because as-of queries span years. Embeddings are keyed by model, so a model change rebuilds in the background. A C21 disk sentinel compresses and partitions automatically before space runs short.

---

## 12. Coverage of Book and connector needs

**TEXTBOOK §12.1 and SPINE §5.6:** item fields (ID, role, tags incl. `suggestion`, text, verified gist, qualifiers, concepts with one primary, version, certainty, span size) → `item*`; best rank and reason → `best_rank`; attribution (speaker, speaker fidelity, agent, span, modality, hedge, lineage incl. `northstar_echo`) → `attribution`; agent registry → `agent`; stance and verification → their tables; span and source (type, locator, quote, prefix, suffix, capture fidelity, branch, model, browsing, title, link template) → `span`, `source`, `message`; episode (product, surface, model, times, project, identity state, connector key, joins) → `episode`, `source_join`; relations (18 types, confidence, direction check, status, creator) → `relation`; supersession (reason, evidence, causal alternative) and Tension (sides, state, spawned question) → §4.3; goals and questions (explicit, reported, inferred; confirmation and origin; raised by; targets; answers) → `agenda*`; engagement events, anomaly marks → `index.db`; corrections (kind, target, payload, holder, origin, proposed or applied, active or lifted, barred hash) → `correction`, `active_constraint`; context receipts by session → `context_receipt*`; scope, sensitivity, distressing → every item, span and source; tombstones; recorded outputs → `model_call`; landmarks, redirects, freshness → `landmark*`, `redirect`, `build_*`, `dirty_page`; suggested topics → `agenda` with a `northstar_output` source.

**[CD], [GD], [OBS]:** minted handle → `session.handle`, `source_key`; per-turn nonce and block tag → `turn_nonce`; `openai/session` → `source_key`, `session_conv_key`; head-and-tail copies → `partial` observations; reported points → `reported_point`, checked in `reconciliation_point`; read-only calls → no capture row; delivered IDs derived on demand from the echoed tag ([CX] §2.5 rule 7); widget supersession → `widget_instance`; `delivered: unknown`, `user_removed`, arms → receipts; composer and transcript → two observations; Northstar blocks and edits → `ns_block_*`, `northstar_injected` spans; model label, app and profile version, grounding, attachments, pastes → `observation`; watermarks → `capture_watermark`; account source (`channel`, `install_declaration`, observer `ax_label`) → the `account_source` column on `envelope` and `session` (a column, not a table); restart prefill → artifact `prefill`, `self_capture_match`.

---

## 13. Interfaces

**Provided**

| To | What | Shape |
|---|---|---|
| C06 | `CaptureStore`, `normalize`, `norm_hash`, the excision bar | `put_envelope(env) -> stored | duplicate` |
| C12 | Catalog and gate order; triggers; `LedgerWriter` | `Proposal{proposal_id, job_id, kind, events[], inputs[], risk_tier}` → `{txn_id, seqs}` or `{rejections[{check_id, detail}]}` |
| C08 | Projection schemas and the rank key | `IndexPort` |
| C10, C23 | `session.db`; recent-window and receipt queries; the identity sync rule | `SessionStore` |
| C11 | `jobs.db` schema | `JobStore`, `Recorder` |
| C13 assemblers | As-of reads for re-processing sandboxes ([13 §F.12]) | `LedgerReader.get(id, as_of=seq)` |
| C15 | Pack queries (best-rank, recent provisional, reported and contested slots); `artifacts.db` | `IndexPort`, `ArtifactStore` |
| C16, C17 | Every §8.1 query; book registry and build tables; `reader.db` | `LedgerReader`, `BookStore` |
| C18 | Correction tables and precedence | correction proposals |
| C19 | `ExcisionPort` (executed by each store's writer); tombstone, bar and registry formats; scopes and `held` | §10; internal events `excision.begin(targets)`, `excision.done(target)` |
| C21, C22 | Sweep checks, checkpoints, sentinel queries, reconciliation metrics; read-only snapshots | read-only SQL and ports |

**Needed**

| From | What |
|---|---|
| C01, C04 | Envelopes per SPINE §4.4 with idempotency key, account source, conversation-key kind and `persist_policy` |
| C11 | Job, batch and `config_v` on every proposal; L4 audits for high-tier events |
| C13, C14 | Proposals without speaker, origin or fidelity fields; verdicts with family and independence flags |
| C16 | Block-version input manifests, `sentence_cite` rows, DDL for BookLedger, Edition, BlockVersion |
| C19 | Egress policy versions, the account allowlist, the Keychain key for needle HMACs |
| C20 | A recorder call per model call; a new role **`embedder`**, local by default (D-10) |
| Configuration (I19) | Join bar, reconciliation window and ratio, margin gap, blast radius, recent window, echo threshold, Q6 and UQ-10 flags, versioned and hashed |

---

## 14. Departures from SPINE

| # | SPINE | This design | Why |
|---|---|---|---|
| D-1 | `rank`, `rank_reason` on Item (§5.2) | In the `best_rank` projection; the ledger keeps rank inputs only in Tension resolutions | Rank is a pure function of recorded axes (SYN §3.1); stored canonically, it would need an event per re-rank and could contradict its own inputs |
| D-2 | `account_ref` on every record (§7.5 rule 2) | `tenant_id` everywhere; `account_ref` on envelope, observation, source, message, session | One item can cite spans from two accounts, so one column would be wrong; derived records resolve the account through their spans |
| D-3 | §5.1: C06 writes capture; §6.1: C12 alone writes sources, messages, spans | C06 writes observations and proposes capture events; C12 writes ledger rows without a model; text lives only in intake | Reconciles the two sections with one writer per store and one copy of the text |
| D-4 | Six source types | Adds `northstar_output` | A suggested topic (UQ-10) needs an immutable source for I1 |
| D-5 | Span fidelity includes `reconciled` (§5.3) | `reconciled` on the attribution, with `recon_id` | Spans are immutable (I20); reconciliation re-anchors attributions, where TEXTBOOK §5.4 reads the chip |
| D-6 | C06 redacts "secrets and PII" at capture | Secrets removed before storage; PII tagged, redacted on egress | The Book quotes the user's words verbatim (TEXTBOOK §5.7, V5); egress redaction still protects what leaves the Mac (SPINE §8.5) |
| D-7 | No model-call records in `session.db` (§6.1) | `fast_model_call`, written by C10 | SPINE §8.5 rule 3 with one writer per store; only C11 writes `jobs.db` |
| D-8 | Six supersession reasons | Adds `rank_resolution` | AD19 step 3 resolves without an explicit signal; TEXTBOOK §7.5 renders it as a supersession |
| D-9 | C19 is the excision exception for `ledger.db` (§6.1) | **Withdrawn 2026-10-08 (X12).** Now as SPINE and [PL] §6.7 X5: C19 orchestrates under the global lock; each store's writer executes its own `ExcisionPort`; C19 writes `ledger.db` directly | No departure remains; single writers hold |
| D-10 | No embedding role (§8.1) | C20 role `embedder`, local by default | C08's embeddings need a model, and their inputs are captured text (SPINE §7.7, UQ-11) |

---

## 15. Risks

Reused: **RISK 4, 19, 34, 35** (desktop L0 capture, delivery and account limits, which this schema records honestly but cannot fix); **RISK 6** (semantic errors bounded only statistically); **13** (exposure; embeddings stay local); **22** (contested pile-up, §7.2 sentinels); **24** (wrong joins: the bar, reversibility, the sweep); **25** (fabricated reports, measured in `reconciliation_point`); **26** (core erosion; the I23 SQL lint); **32** (double capture: one message, many observations); **33** (path B stores nothing: enforced, not solved); **30** (no permitted verifier for some AI-said items: `no_independent_verifier` ranks with `unchecked`).

| # | Risk | Threatens | Mitigation |
|---|---|---|---|
| **RISK-CDM-1** | Excision cannot reach synced mirror copies or vendor and provider copies, nor a Time Machine copy if the user removes the install-time exclusion; a restore from such a copy can bring content back | SYN §5 item 9; trust | Time Machine excluded at install ([PL] §2.5); unreachable places listed per tombstone; restore registry and re-capture bar (§10.3); `northstar doctor` reports a removed exclusion; UQ-14 |
| **RISK-CDM-2** | Replay not hash-identical across SQLite or Python versions | I18, B10; GOAL §4.7 | Canonical JSON; explicit ordering; pinned versions; CDM-S3 |
| **RISK-CDM-3** | No foreign keys across files: a crash or rollback between stores leaves dangling references | §4.7; traceability | ID-and-version references; missing targets treated as excluded; the sweep; J11 repair |
| **RISK-CDM-4** | Typed events run ~14× the "36K" figure, and recorded outputs dominate storage; at 10× the laptop disk fills faster | GOAL §6 "maintains itself without babysitting" if the disk fills | §11 plan; compressed canonical backups; cold partitions; automatic disk sentinel; CDM-S1 |
| **RISK-CDM-5** | Secret redaction before storage removes legitimate text for good | §4.2 for that span | High-precision patterns; kind recorded; redaction-rate sentinel; tuned on the golden set |
| **RISK-CDM-6** | The lexicographic margin rule is a heuristic and may resolve narrow cases wrongly | RISK 22; SYN §7.4 | Calibrated on the golden set (CDM-S6); 100% L4 audit; automatic undo |

---

## 16. Questions for the user

No open question is owned here. This file's former question is retired (2026-10-08, X04). Backups and permanent removal are one question, **SPINE UQ-14** (asked in [PL] §13), with its working assumption: Time Machine excluded, Northstar's own encrypted archives, no external drive until you name one.

Covered elsewhere: install-time account declaration (SPINE UQ-3); path B (SPINE UQ-8(a)); suggested topics (SPINE UQ-10, gated by a flag and a CHECK); egress for model calls (SPINE UQ-11); a click confirming a reported goal for AI packs (TEXTBOOK Q6, asked as ARCH DQ-10(a); a configuration flag).

---

## 17. Spikes

| Spike | Question | Settles |
|---|---|---|
| **SP-1** (SPINE; partly settled by PF-1) | Is there a vector extension with Python 3.14 arm64 macOS wheels? | Brute force or extension behind `IndexPort` |
| **SP-7** (SPINE) | Join precision per method | The join bar; RISK 24 |
| **CDM-S1** | Synthetic load at 1× and 10×: Apply throughput, §11 latencies, sweep and replay time, disk | §11; RISK-CDM-4 |
| **CDM-S2** | Excision drill: WAL, freelist, FTS segments, backups, mirror, restore from an older backup, replayed export; zero hits required | §10; B16; RISK-CDM-1 |
| **CDM-S3** | Replay on two SQLite and two Python patch versions; compare table hashes | I18, B10; RISK-CDM-2 |
| **CDM-S4** | DDL (including forward foreign-key order) and §8.1 queries on Postgres, checked once now; Postgres triggers and CI at the cloud-adapter stage | SD-26; §8.3 |
| **CDM-S5** | Reconciliation thresholds on synthetic paired captures | §3.3; RISK 25, 32 |
| **CDM-S6** | Margin calibration on the golden set | §7.1; RISK-CDM-6 |

| ID | Product fact checked | Source | Checked |
|---|---|---|---|
| PF-1 | uv-managed CPython 3.14.8 on this Mac reports SQLite 3.53.1; FTS5, `contentless_delete=1`, FTS5 `secure-delete`, `json_valid` in CHECK, `RETURNING`, generated columns and `enable_load_extension` all work; the companion DDL executes in full | Local check, `python3.14 -I`, in-memory databases | 2026-10-08 |
| PF-2 | Install checks Time Machine inclusion and excludes the data root; observed values are kept locally | `tmutil` at install; values in local `northstar doctor` output, never in the repo ([PL] §2.5) | At each install |

---

## 18. Goal-fidelity check

| GOAL item | How this component serves it | Status |
|---|---|---|
| §3.1 Shared core: both sides captured, attributed, evolving without destroying history | Both speakers captured; axes as copied columns; append-only log with row history; supersession, never overwrite; source-generic anchors | Partial: the schema meets it, but what is captured depends on RISK 19 and RISK 33 (desktop L0, outside this component) and RISK-CDM-5 (redaction) |
| §4.1 No rituals | No review queue in any table; proposals expire silently; quarantine has exits; sweeps act through C11 and C21; excision is never prompted | Met |
| §4.2 AI-said first-class | Same tables and axes for every speaker; speaker never a rank input; `no_independent_verifier` in the `unchecked` tier; parity sentinels | Partial: RISK 33, RISK 30 |
| §4.3 The AI manages it; correction optional | Every write is a proposal applied by code; corrections are optional constraints | Partial: path B turns ChatGPT L0 capture off (RISK 33) |
| §4.4 Two architectures, one core | One ledger; separate AI and Book projections from the same leaves; one shared `derived_agenda` | Met |
| §4.5 Drift and continuity, equally | Session ledger, turn receipts, drift verdicts; continuity receipts, routing, seeding, re-explanation; reported goals kept without authority (SD-36) | Partial: the data is in place; desktop delivery limits remain (RISK 4, 34) |
| §4.6 Product-agnostic; local now, cloud later; personal first | Product columns are metadata under an SQL lint; ports with a Postgres mapping; `tenant_id` everywhere; account source recorded | Partial: product-agnostic data and cloud ports by design; personal-first at L0 rests on the install declaration (RISK 35); erosion watched (RISK 26) |
| §4.7 Robust maintainer | One writer per store; Apply gates; tested triggers; a check and a sweep per invariant; recorded outputs; compensation; replay | Partial: structural guarantees subject to RISK-CDM-2, RISK-CDM-3; semantic errors bounded (RISK 6) |
| §4.8 Prototype built and evaluated | Executable DDL on the verified local SQLite; benchmark and drill spikes | Planned (CDM-S1 to CDM-S6) |
| §6 The book shows sources and what to learn | Every TEXTBOOK §12.1 field mapped (§12); identity computed, never claimed; reported goals and suggested topics labelled by schema | Partial: every field is carried; desktop L0 fidelity limits remain (TEXTBOOK H8, RISK 19) |
| §6 Maintains itself; errors bounded, detectable, correctable | Sweeps, checkpoints, sentinels, reversible resolutions and joins, excision with a zero-hit check, automatic disk handling | Partial: RISK-CDM-1, RISK-CDM-3, RISK-CDM-4, RISK 6 |

---

## Consistency fixes (2026-10-08)

Cross-document fixes adopted so this file agrees with the design set. No non-negotiable is weakened. The companion `core-data-model.sql` must carry the matching DDL changes (§9.4).

| ID | Change here |
|---|---|
| X04 | Backups follow [PL] §2.5: Time Machine excluded at install, Northstar's own encrypted archives, optional named drive. UQ-CDM-1 retired in favour of UQ-PL-3 (§16); §0 item 11, §10.2 backups row, §10.4 and RISK-CDM-1 point to it. `book.db`'s BookLedger, Edition and landmark tables are canonical for restore; only BlockVersion renders, index and artifacts are rebuilt (§6, §11) |
| X07 | Seeds are `ADD` ops with actor `seeding`, `actor_ref` = `continuity_params` version, `seeded_from {item_id@version, artifact_hash, delivery_receipt}`, `seed_kind`, `delivery`, `on_route`; `by_` keeps the original speaker (user, ai); SEED and ROUTE op types dropped; routing is a `routing_record` row. Authority enum stays `confirmed`, `provisional`, `reported` (§2.2, §5) |
| X09 | New `pending_resume` table in `session.db`: C10 applier the single writer, C23 the reader, 24 h TTL, adoption only by explicit handle or a C23 route with p ≥ 0.7, lineage set and reversible (§1, §5, §8.2) |
| X10 | §2.2 is the event authority. Added `concept.reparented` (row 22, high tier, I12 and I21 gates) for `REPARENT`; `FIDELITY_UPGRADE` is `attribution.added` with `recon_id` (row 17); maintainer op and compensation names mapped to catalog names under `compensation.batch` |
| X11 | Scope and tier vocabulary from [PL] §6.1: scope kinds `personal`, `project`, `work`, `unclassified`, `session`, `eval`; `private` is a tier only. `held` is a flag on scope and session, set by the new `scope.hold_changed` (row 39) (§4.5, §5) |
| X12 | C19 orchestrates excision under the global lock; each store's writer executes its own `ExcisionPort`; C19 writes `ledger.db` directly. Internal events `excision.begin(targets)` and `excision.done(target)`; `excision.applied` stays the ledger event. D-9 withdrawn (§8.2, §10.2, §13, §14) |
| X14 | Join methods gain `process_lineage` and `widget_origin`; account source gains `ax_label`; one turn-tag format `NS-XXXXXX.<n>` (§3.4, §5, §12) |
| X17 | `northstar_echo` gate accepts a receipt from any session of the same `speaker_model_family` within 90 days when the span has no fresh grounding ([AC] D4); echo share by vendor family available to C21 (§2.2 row 18, §4.2, §8.1) |
| X18 | Origin stays immutable. New intake record `observation.origin_confirmed` (`origin_confirmation` table), read by the C12 I5/I22 gate for hook channels; template and continuation-hash fallback when the transcript reader is unavailable, with the degradation reported (§1, §2.1, §3.1) |
| X25 | Status renamed `cited_unchecked`; the `ver_tier` order (supported > mixed > unchecked tier > contradicted) is binding for [AC]'s `ver` (§6) |
| X29 | `goal_card` added to `index.db` (C08 reads `session.db`); `relation.basis` added for `advances_goal` (§1, §2.2 row 27, §4.3, §6) |
| X31 | `anomaly_mark` rows come from J5 `misfit {item, concept}` outputs; the [MT] gated suggested-topic job (off until UQ-10) is the proposer in rows 14 and 23; row 23 (and row 14 for consistency) tiers: H for explicit goals, L for reported and inferred (§2.2, §6) |

---

## Review revisions (2026-10-08)

These are the review fixes adopted in this file. The full record, with each finding's verdict and reasons, is [REVIEW.md](../REVIEW.md). Every change is a HOW change: no non-negotiable is weakened and no WHAT changes. The companion `core-data-model.sql` must carry the matching DDL changes; re-running its checks is a Stage 0a task (§9.4).

| ID | Change here |
|---|---|
| MR-3 | `synchronous=FULL` on `jobs.db` (§1, §6). The `job` row has one `idem_key` as [MT] §3.3, a lease `epoch` and the full [MT] §3.1 state machine (§6). New `applied_job(job_id, proposal_id, output_hash)` in `ledger.db`, written in Apply's transaction, so the ledger is the truth for "applied" (§1, §2.1, §6). New ledger → jobs orphan check (§9.3) |
| MR-4 | Origin confirmation uses the DDL names: method `transcript_entry_type` or `template_continuation_hash`; outcome `confirmed`, `not_confirmed` or `confirmed_degraded`. The fallback gives `confirmed_degraded`: steers live, no long-term authority until the reader confirms or HK-S3 re-certifies the templates; a later `not_confirmed` triggers a C12 revocation (§2.1, §3.1). The sweep reports authority resting on `not_confirmed` hook evidence as an I22 violation (§9.3) |
| MR-5 | Append-only triggers are bypassed only on the excision connection (an application-defined function or TEMP triggers), never by a persistent row; `excision_run` records progress only (§1, §4.6, I6). Excision is a resumable saga: tombstone (`in_progress`), HMAC needles and closure IDs written first to the ledger and the registry; an encrypted needle file until [PL] X10; idempotent, re-entrant purges; boot resume before traffic; a lock lease renewed by C19's heartbeat. Provenance closure, bounded to text-bearing derivations. One haystack rule, as [PL] X9. A failed scan gets one more purge, then an alert, and the saga stays open. A standing policy rule ([PL] D-PL-5) may also start it (§0 item 11, §10) |
| MR-7 | A medium or high worker proposal without a C14 verdict goes to `awaiting_verify` (the [MT] §5.2 parity hold); only a failed verdict goes to quarantine (§2.1) |
| MR-8 | No text change needed here. Rollback stays the §7.2 compensating chain under `compensation.batch`; [MT] §7.4 owns the canonical active-state projection, the compensating Book edition, the bounded job closure and the `items.retracted` notice to C10 |
| MR-9 | New `relation_endpoints` trigger: `from_id` and `to_id` exist in `item`, `relation` or `episode`; an abort is a code fault (§4.6). Dangling endpoints added to the sweep (§9.3) |
| MR-11 | I18 gains an independently written reference projector, sharing no code with Apply, run in CI and in the weekly replay (§9.1). The sweep's action is to freeze the producing job type, except capture, correction and compensation types; capture violations alert and route to a C06 fix (§9.3) |
| MR-12 | An audit's dissent is recorded as a resolution input. A resolution undone by audit goes straight to step 5: `contested`, a spawned question, a recheck date. The oscillation hold's state is `contested` (§7.1, §7.2) |
| CONS-2 | Goal authority gains the Q6 (ARCH DQ-10(a)) yes path: a click-bound `agenda.confirmed` sets authority `full`, labelled "confirmed by your click; wording as reported"; basis stays `reported` and `goal_status` keeps its values (§4.1; also §2.2 row 25, §16) |
| CONS-4 | C08 computes `concept_facts`' substantive-teaching flag in code; no model sets it (R14, [TB] §4.7) (§6) |
| CONS-9 | `persist_policy` is derived by C04 from the manifest's `capture_mode`: `full`, `none` or `on_write`; the session-item guard is per turn (§4.6, §5) |
| CONS-10 | `reader.db` gains a per-page open counter, exposed to C16 only as the derived `landmark_signals` vector (§6) |
| CPLX-9 | Postgres triggers and the Postgres CI matrix are deferred to the cloud-adapter stage; CDM-S4 checks the DDL once now, including forward foreign-key order (§4.6, §8.3, §17) |
| SEC-6 | PF-2 no longer records this Mac's Time Machine state: install checks inclusion and excludes the data root, and observed values stay in local `northstar doctor` output (§10.4, §17) |
| SEC-8 | The hook pin cache `run/pincache`, `tmp/` and `run/workers/` are purged and are in the zero-hit haystack (§10.2) |
| BOOK-7 | B4: V4's lexicon is the agent registry plus generic agent nouns, applied as speakers of speech or stance verbs ([TB] §8.5) (§9.2) |
| ROB smaller issues | DDL names in the text (`not_confirmed`, `template_continuation_hash`, `account_source` as a column, §3.1, §12); `*_no_del` guards for `apply_txn`, `session_op`, `correction`, `active_constraint`, `attribution`, `tombstone`, `reconciliation_point` (§4.6); partial copies are the first and last 1,800 characters ([CX] §2.3, §3.1); incomplete verbatim capture gives `could_not_confirm`, not `reconciled_absent`, and supersedes nothing (§3.3); "superseded implies an active supersession" sweep check (§4.6, §9.3); excising a supersession winner restores or re-resolves the loser (§10.1, §10.2) |
| CONS smaller issues | `pending_resume.adopted_via` is `explicit_handle` or `c23_route`; the `seeded_from` key is `item` (§5). C15 builds pins and C10 holds the core cache (§11) |
| Carried task (c) | The header and §9.4 say the DDL checks have not been re-run since the 2026-10-08 edits; re-running them is a Stage 0a task, and the earlier results are historical |
| IDs | Local question IDs replaced by SPINE IDs: UQ-PL-3 → UQ-14 in §0, §10, RISK-CDM-1 and §16 (the X04 row above keeps its original wording as a record) |
| FEAS-1 | Landed at the final gate. The `hash_only` observation kind and the `observation.persist_policy` column (with both CHECKs) are removed. Path B, and unrecorded turns under A or C2, write no observation; only content-free operational logs are kept, outside `intake.db` content tables ([CX] §2.5). §12 maps read-only calls to no capture row; the §9.4 hash-only check is retired (§2.2 row 5, §3.1, §9.4, §12) |
| BOOK-2 | Landed at the final gate. `reported_point` gains `body` (≤ 1,500 characters, explanation or example points only, by CHECK) and `reply_scope` (`prev`, or `this` for closing-call points, `this_reply_points`), so [TB] §4.7's R14 flag and [MT] J3 can read reported bodies (§3.1) |

---

## Final-gate fixes (2026-10-08)

The final gate found that two decided review fixes had not reached this file or its DDL. Both are HOW changes; no non-negotiable is weakened.

| Finding | What changed |
|---|---|
| FEAS-1 | No observation on path B or on unrecorded turns; `hash_only` and `observation.persist_policy` removed (§2.2 row 5, §3.1, §9.4, §12; SQL `observation`) |
| BOOK-2 | Reported points carry an optional `body` and a `reply_scope` for closing calls (§3.1; SQL `reported_point`) |
