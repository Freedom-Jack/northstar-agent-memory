-- Northstar core data model: portable DDL (SQLite now, Postgres later).
-- Companion to core-data-model.md, which explains every table, rule and departure.
-- Status: design draft for adversarial review. Not approved. Contains no personal data.
-- Each "-- STORE:" section is one SQLite file (SPINE §6.1) with exactly one writer.
-- Verified on 2026-10-08, before the consistency and review edits: every section executed on SQLite 3.53.1 and the
-- invariant triggers aborted as intended (core-data-model.md §9.4, PF-1). Not yet re-run since; see the footer.
-- Postgres mapping: core-data-model.md §8.3.
-- Pragmas per store: journal_mode=WAL; synchronous=FULL (intake, ledger, jobs) else NORMAL (MR-3);
-- foreign_keys=ON; secure_delete=ON; busy_timeout=5000.
-- Excision bypass (MR-5): the append-only and immutability triggers test ns_excision_active(), an application-defined
-- function that each writer registers on every connection it opens. It returns 0, except on the one connection a
-- store's writer opens for an excision step while that run's tombstone is 'in_progress'. The bypass ends with that
-- connection, so a crash leaves none behind. A connection that never registered the function cannot prepare a guarded
-- UPDATE or DELETE ("no such function"), so the guard fails closed. excision_run records progress only, for resuming;
-- it grants no bypass. Postgres: a transaction-local setting (SET LOCAL) read by the same triggers.

-- =====================================================================================
-- STORE: intake.db   (writer: C06)
-- =====================================================================================
CREATE TABLE excision_run (tenant_id TEXT NOT NULL DEFAULT 'local', run_id TEXT PRIMARY KEY, tombstone_id TEXT,
  state TEXT NOT NULL CHECK (state IN ('in_progress','done')), started_at TEXT NOT NULL, ended_at TEXT);   -- progress only (MR-5)
CREATE TABLE envelope (tenant_id TEXT NOT NULL DEFAULT 'local',
  envelope_id TEXT PRIMARY KEY, idem_key TEXT NOT NULL UNIQUE, schema TEXT NOT NULL, type TEXT NOT NULL,
  connector_id TEXT NOT NULL, connector_v TEXT NOT NULL, mcp_profile TEXT,
  product TEXT NOT NULL CHECK (json_valid(product)),                       -- metadata only (I23)
  account_ref TEXT NOT NULL,
  account_source TEXT NOT NULL CHECK (account_source IN ('channel','install_declaration','ax_label')),   -- ax_label: X14
  handle TEXT, conv_key_kind TEXT, conv_key_value TEXT, branch_path TEXT,
  channel TEXT NOT NULL CHECK (channel IN ('hook','mcp_report','ax_observer','export','sdk','widget')),
  occurred_at TEXT NOT NULL, sent_at TEXT, received_at TEXT NOT NULL, spooled INTEGER NOT NULL DEFAULT 0,
  payload_meta TEXT CHECK (payload_meta IS NULL OR json_valid(payload_meta)));   -- payload minus text fields
  -- northstar.connector/1.1 additions (turn_origin, explicit_request, client.host_pid, flags.canary, ...) ride payload_meta (X14)
CREATE TABLE observation (tenant_id TEXT NOT NULL DEFAULT 'local',
  obs_id TEXT PRIMARY KEY, envelope_id TEXT NOT NULL REFERENCES envelope, account_ref TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('user','assistant')),
  obs_kind TEXT NOT NULL CHECK (obs_kind IN ('full_text','reported_copy','reported_points','partial')),   -- no hash_only: path B writes no observation (FEAS-1)
  sub_channel TEXT,   -- composer | transcript | prompt_hook | stop_hook | transcript_file | tool_args | export_json | reader
  fidelity TEXT NOT NULL CHECK (fidelity IN ('verbatim_live','verbatim_rendered','verbatim_deferred','model_reported')),
  handle TEXT, conv_key_kind TEXT, conv_key_value TEXT, branch_path TEXT, ordinal INTEGER, call_index INTEGER,
  turn_nonce TEXT, product_message_id TEXT,
  text TEXT, text_blob TEXT,                                               -- blob hash URI above 64 KB
  total_len INTEGER, head_len INTEGER, tail_len INTEGER,                    -- head+tail copies ([CD] 4,000; [GD] 1,000+1,000)
  raw_hash TEXT NOT NULL, norm_hash TEXT NOT NULL,
  redactions TEXT, pii_ranges TEXT, paste_ranges TEXT, ns_block_ranges TEXT,
  ns_block_user_modified INTEGER NOT NULL DEFAULT 0 CHECK (ns_block_user_modified IN (0,1)),
  attachments_meta TEXT, grounding TEXT, citations TEXT, model_label TEXT, app_version TEXT, profile_version TEXT,
  reply_complete INTEGER, occurred_at TEXT NOT NULL, received_at TEXT NOT NULL,
  CHECK (obs_kind <> 'partial' OR (head_len IS NOT NULL AND tail_len IS NOT NULL AND total_len IS NOT NULL)));
CREATE INDEX obs_norm ON observation(norm_hash);
CREATE INDEX obs_conv ON observation(conv_key_kind, conv_key_value, call_index);
CREATE INDEX obs_handle ON observation(handle, call_index);
CREATE INDEX obs_nonce ON observation(turn_nonce);
CREATE TABLE reported_point (tenant_id TEXT NOT NULL DEFAULT 'local',
  obs_id TEXT NOT NULL REFERENCES observation, idx INTEGER NOT NULL CHECK (idx BETWEEN 0 AND 4),
  kind TEXT NOT NULL, text TEXT NOT NULL CHECK (length(text) <= 200), quote TEXT CHECK (quote IS NULL OR length(quote) <= 120),
  body TEXT,                                                               -- reported explanation body (BOOK-2, R14)
  reply_scope TEXT NOT NULL DEFAULT 'prev' CHECK (reply_scope IN ('prev','this')),   -- 'this': closing call (this_reply_points)
  CHECK (body IS NULL OR (length(body) <= 1500 AND kind IN ('explanation','example'))),
  PRIMARY KEY (obs_id, idx));
CREATE TABLE delivery_receipt (tenant_id TEXT NOT NULL DEFAULT 'local',
  envelope_id TEXT PRIMARY KEY REFERENCES envelope, handle TEXT, turn INTEGER,
  artifact_id TEXT NOT NULL, artifact_hash TEXT NOT NULL, kind TEXT NOT NULL,
  placement TEXT NOT NULL CHECK (placement IN ('additional_context','tool_result','widget_context','composer_block','start_message')),
  delivered TEXT NOT NULL CHECK (delivered IN ('true','false','unknown')),
  suppressed_by_arm INTEGER NOT NULL DEFAULT 0, user_removed INTEGER NOT NULL DEFAULT 0, at TEXT NOT NULL);
CREATE TABLE capture_watermark (tenant_id TEXT NOT NULL DEFAULT 'local',
  conv_key_kind TEXT NOT NULL, conv_key_value TEXT NOT NULL, source_channel TEXT NOT NULL,
  message_count INTEGER NOT NULL, last_content_hash TEXT, at TEXT NOT NULL,
  PRIMARY KEY (conv_key_kind, conv_key_value, source_channel, at));
CREATE TABLE self_capture_match (tenant_id TEXT NOT NULL DEFAULT 'local',
  obs_id TEXT NOT NULL REFERENCES observation, artifact_id TEXT NOT NULL, start_char INTEGER NOT NULL, end_char INTEGER NOT NULL,
  match TEXT NOT NULL CHECK (match IN ('exact','marker','prefill')), PRIMARY KEY (obs_id, artifact_id, start_char));
CREATE TABLE excision_bar (tenant_id TEXT NOT NULL DEFAULT 'local',
  bar_hmac TEXT PRIMARY KEY, tombstone_id TEXT NOT NULL);                  -- keyed HMAC of norm text and shingles
CREATE TABLE outbox (tenant_id TEXT NOT NULL DEFAULT 'local',
  seq INTEGER PRIMARY KEY, topic TEXT NOT NULL, payload TEXT NOT NULL CHECK (json_valid(payload)), created_at TEXT NOT NULL);
-- observation.origin_confirmed (X18): origin stays immutable (I20); confirmation of a hook-channel user_typed prompt is a
-- separate append-only record. transcript_entry_type = the HK transcript sweep; template_continuation_hash = C06 fallback
-- when the reader is unavailable (no template or continuation-hash match -> confirmed_degraded, never confirmed), always
-- degraded = 1 and reported by C21. confirmed_degraded steers the live session only: no long-term authority until a
-- transcript record confirms it or the templates are re-certified; a later not_confirmed revokes it (MR-4).
-- When both exist, the transcript record wins. Read by the C12 I5/I22 gate (see the ledger triggers below).
CREATE TABLE origin_confirmation (tenant_id TEXT NOT NULL DEFAULT 'local',
  obs_id TEXT NOT NULL REFERENCES observation,
  method TEXT NOT NULL CHECK (method IN ('transcript_entry_type','template_continuation_hash')),
  outcome TEXT NOT NULL CHECK (outcome IN ('confirmed','confirmed_degraded','not_confirmed')),
  degraded INTEGER NOT NULL CHECK (degraded IN (0,1)), detail TEXT, at TEXT NOT NULL,
  PRIMARY KEY (obs_id, method), CHECK ((method = 'template_continuation_hash') = (degraded = 1)),
  CHECK (method <> 'template_continuation_hash' OR outcome IN ('confirmed_degraded','not_confirmed')),   -- MR-4
  CHECK (outcome <> 'confirmed_degraded' OR method = 'template_continuation_hash'));
CREATE TRIGGER origin_confirmation_no_upd BEFORE UPDATE ON origin_confirmation
WHEN NOT ns_excision_active()
BEGIN SELECT RAISE(ABORT, 'I6 append-only: origin_confirmation'); END;
CREATE TRIGGER origin_confirmation_no_del BEFORE DELETE ON origin_confirmation
WHEN NOT ns_excision_active()
BEGIN SELECT RAISE(ABORT, 'I6 append-only: origin_confirmation'); END;
CREATE TRIGGER observation_no_update BEFORE UPDATE ON observation
WHEN NOT ns_excision_active()
BEGIN SELECT RAISE(ABORT, 'I6/I20 observations are immutable'); END;
CREATE TRIGGER observation_no_delete BEFORE DELETE ON observation
WHEN NOT ns_excision_active()
BEGIN SELECT RAISE(ABORT, 'I6 observations are deleted only by excision'); END;

-- =====================================================================================
-- STORE: ledger.db   (writer: C12 Apply; C19 only on its excision connection, MR-5)
-- =====================================================================================
CREATE TABLE excision_run (tenant_id TEXT NOT NULL DEFAULT 'local', run_id TEXT PRIMARY KEY, tombstone_id TEXT,
  state TEXT NOT NULL CHECK (state IN ('in_progress','done')), started_at TEXT NOT NULL, ended_at TEXT);   -- progress only (MR-5)

-- Event log ---------------------------------------------------------------------------
-- event.type: names from the core-data-model.md §2.2 catalog, the event authority (X10). The maintainer's op names map
-- onto it: REPARENT -> concept.reparented (H; I12, I21 fixed_parent/forbidden_parent); FIDELITY_UPGRADE ->
-- attribution.added with recon_id (capture_fidelity 'reconciled'); rollback -> supersession.undone,
-- relation.status_changed, item.status_changed, each with `compensates`, under one compensation.batch.
CREATE TABLE event (tenant_id TEXT NOT NULL DEFAULT 'local',
  seq INTEGER PRIMARY KEY, event_id TEXT NOT NULL UNIQUE, type TEXT NOT NULL, schema_v INTEGER NOT NULL,
  subject_id TEXT NOT NULL,
  actor_kind TEXT NOT NULL CHECK (actor_kind IN ('code','user','worker','verifier','excision')),
  actor_ref TEXT NOT NULL,                                                  -- module@ver | model@ver#prompt_hash | user
  origin TEXT CHECK (origin IN ('reader_click','app_click','chat_verbatim','chat_verbatim_reconciled')),
  proposal_id TEXT, proposal_ix INTEGER, job_id TEXT, batch_id TEXT,      -- one proposal may write several events
  risk_tier TEXT NOT NULL CHECK (risk_tier IN ('low','medium','high')),
  inputs TEXT NOT NULL CHECK (json_valid(inputs)), payload TEXT NOT NULL CHECK (json_valid(payload)), reason TEXT,
  compensates TEXT REFERENCES event(event_id), config_v TEXT NOT NULL, recorded_at TEXT NOT NULL,
  excised INTEGER NOT NULL DEFAULT 0 CHECK (excised IN (0,1)),
  CHECK (actor_kind <> 'user' OR origin IS NOT NULL),
  CHECK ((proposal_id IS NULL) = (proposal_ix IS NULL)),
  UNIQUE (proposal_id, proposal_ix));                                       -- I14 at the event level
CREATE INDEX event_type_seq ON event(type, seq);
CREATE INDEX event_job ON event(job_id, batch_id);
CREATE INDEX event_time ON event(recorded_at);
CREATE TABLE event_subject (tenant_id TEXT NOT NULL DEFAULT 'local',
  subject_id TEXT NOT NULL, seq INTEGER NOT NULL REFERENCES event(seq), PRIMARY KEY (subject_id, seq));
CREATE INDEX event_subject_seq ON event_subject(seq);
CREATE TABLE row_hist (tenant_id TEXT NOT NULL DEFAULT 'local',
  tbl TEXT NOT NULL, row_id TEXT NOT NULL, rec_from_seq INTEGER NOT NULL, rec_to_seq INTEGER,
  snapshot TEXT NOT NULL CHECK (json_valid(snapshot)), status TEXT, content_v INTEGER,
  PRIMARY KEY (tbl, row_id, rec_from_seq), CHECK (rec_to_seq IS NULL OR rec_to_seq > rec_from_seq));
CREATE TABLE apply_txn (tenant_id TEXT NOT NULL DEFAULT 'local',
  txn_id TEXT PRIMARY KEY, first_seq INTEGER NOT NULL, last_seq INTEGER NOT NULL,
  proposal_ids TEXT NOT NULL CHECK (json_valid(proposal_ids)), applied_at TEXT NOT NULL);
-- Ledger-side idempotency (MR-3): the ledger is the truth for "applied". Apply writes one row in the same transaction
-- as the proposal's events. A crash duplicate or a stale re-run of the same job cannot apply a second proposal
-- (trigger below). On boot, jobs.db jobs left in 'applying' are reconciled by job_id; the sweep reports ledger rows
-- with no jobs.db job (orphan check).
CREATE TABLE applied_job (tenant_id TEXT NOT NULL DEFAULT 'local',
  job_id TEXT NOT NULL, proposal_id TEXT NOT NULL, output_hash TEXT NOT NULL, applied_seq INTEGER NOT NULL,
  PRIMARY KEY (job_id, proposal_id));
CREATE TABLE outbox (tenant_id TEXT NOT NULL DEFAULT 'local',
  seq INTEGER PRIMARY KEY, topic TEXT NOT NULL, payload TEXT NOT NULL CHECK (json_valid(payload)), created_at TEXT NOT NULL);

-- Scope -------------------------------------------------------------------------------
-- Kinds per platform-security-privacy.md §6.1 (C19 owns the policy; X11): personal, project:<id>, work:<org>,
-- unclassified:<repo_hash> (treated as work), session:<handle>, eval. 'private' is a sensitivity tier, never a kind.
-- held (HK late reclassification): no egress (C19), no packs, no Book (C08 clears pack_ and book_eligible). A flag, not a kind.
CREATE TABLE scope (tenant_id TEXT NOT NULL DEFAULT 'local',
  scope_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL CHECK (kind IN ('personal','project','work','unclassified','session','eval')),
  label TEXT, parent_scope TEXT REFERENCES scope, created_seq INTEGER NOT NULL,
  held INTEGER NOT NULL DEFAULT 0 CHECK (held IN (0,1)), held_seq INTEGER, CHECK (held = 0 OR held_seq IS NOT NULL));

-- Capture (canonical) -----------------------------------------------------------------
CREATE TABLE agent (tenant_id TEXT NOT NULL DEFAULT 'local',
  agent_id TEXT PRIMARY KEY, display_name TEXT NOT NULL, vendor TEXT, product TEXT, surface TEXT, model TEXT,
  model_family TEXT NOT NULL, first_seen_seq INTEGER NOT NULL, UNIQUE (vendor, product, surface, model));
CREATE TABLE source (tenant_id TEXT NOT NULL DEFAULT 'local',
  source_id TEXT PRIMARY KEY, account_ref TEXT NOT NULL,
  source_type TEXT NOT NULL CHECK (source_type IN ('chat_conversation','document','web_page','note','work_artifact',
    'export_file','northstar_output')),
  product_family TEXT, product TEXT, product_mode TEXT, surface TEXT, connector_id TEXT,      -- metadata only (I23)
  title TEXT, title_source TEXT CHECK (title_source IN ('hook','observer','export','user','document')),
  deep_link TEXT, deep_link_template TEXT, context_ref TEXT, uri TEXT, file_hash TEXT, started_at TEXT,
  scope_id TEXT NOT NULL REFERENCES scope,
  sensitivity TEXT NOT NULL DEFAULT 'normal' CHECK (sensitivity IN ('normal','sensitive','private')),
  created_seq INTEGER NOT NULL, CHECK (title IS NULL OR title_source IS NOT NULL));
CREATE TABLE source_key (tenant_id TEXT NOT NULL DEFAULT 'local',
  key_kind TEXT NOT NULL CHECK (key_kind IN ('minted_handle','hook_session_id','transcript_path','openai_session',
    'observer_conv_id','observer_title_hash','export_conv_id','doc_uri')),
  key_value TEXT NOT NULL, source_id TEXT NOT NULL REFERENCES source, added_seq INTEGER NOT NULL,
  PRIMARY KEY (key_kind, key_value));
CREATE INDEX source_key_src ON source_key(source_id);
CREATE TABLE source_join (tenant_id TEXT NOT NULL DEFAULT 'local',
  join_id TEXT PRIMARY KEY, source_a TEXT NOT NULL REFERENCES source, source_b TEXT NOT NULL REFERENCES source,
  method TEXT NOT NULL CHECK (method IN ('exact_key','nonce_echo','process_lineage','widget_origin','content_hash_sequence',
    'fuzzy_time_text')),                                                    -- process_lineage, widget_origin: X14
  confidence REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1), session_join_ref TEXT,
  status TEXT NOT NULL CHECK (status IN ('active','reverted')), applied_seq INTEGER NOT NULL, reverted_seq INTEGER,
  revert_reason TEXT CHECK (revert_reason IN ('contradicting_evidence','user_dispute','excision')),
  CHECK (source_a < source_b), CHECK (status = 'active' OR revert_reason IS NOT NULL));
CREATE INDEX source_join_a ON source_join(source_a, status);
CREATE INDEX source_join_b ON source_join(source_b, status);
CREATE TABLE message (tenant_id TEXT NOT NULL DEFAULT 'local',
  message_id TEXT PRIMARY KEY, account_ref TEXT NOT NULL, source_id TEXT NOT NULL REFERENCES source,
  product_message_id TEXT, branch_path TEXT NOT NULL DEFAULT '0', ordinal INTEGER, call_index INTEGER,
  platform_role TEXT NOT NULL,
  speaker TEXT NOT NULL CHECK (speaker IN ('user','assistant','tool','external','northstar','system')),
  agent_id TEXT REFERENCES agent,
  origin TEXT NOT NULL CHECK (origin IN ('user_typed','user_pasted','assistant_output','tool_output','external_document',
    'model_reported','northstar_injected','northstar_authored')),
  model TEXT, grounding TEXT, citations TEXT, occurred_at TEXT NOT NULL, content_hash TEXT NOT NULL,
  best_obs_id TEXT NOT NULL,                                                -- in intake.db
  fidelity TEXT NOT NULL CHECK (fidelity IN ('verbatim_live','verbatim_rendered','verbatim_deferred','model_reported','reconciled')),
  speaker_fidelity TEXT NOT NULL CHECK (speaker_fidelity IN ('by_construction','model_reported','reconciled')),
  recon_state TEXT NOT NULL DEFAULT 'none' CHECK (recon_state IN ('none','matched','reported_only','could_not_confirm')),
  created_seq INTEGER NOT NULL, CHECK (speaker <> 'assistant' OR agent_id IS NOT NULL));
CREATE UNIQUE INDEX message_slot ON message(source_id, branch_path, ordinal, speaker) WHERE ordinal IS NOT NULL;
-- Desktop messages keyed by call index (ROB smaller issue): one per source, branch, call index and speaker, so a call's
-- user message and the reply it reports do not collide.
CREATE UNIQUE INDEX message_call_slot ON message(source_id, branch_path, call_index, speaker) WHERE call_index IS NOT NULL;
CREATE INDEX message_hash ON message(content_hash);
CREATE INDEX message_source ON message(source_id, occurred_at);
CREATE TABLE message_observation (tenant_id TEXT NOT NULL DEFAULT 'local',
  message_id TEXT NOT NULL REFERENCES message, obs_id TEXT NOT NULL,                  -- obs_id in intake.db
  link_role TEXT NOT NULL CHECK (link_role IN ('capture','reported_copy','reported_points')),   -- message.best_obs_id names the best
  linked_seq INTEGER NOT NULL, PRIMARY KEY (message_id, obs_id));
CREATE TABLE reconciliation (tenant_id TEXT NOT NULL DEFAULT 'local',
  recon_id TEXT PRIMARY KEY, message_id TEXT NOT NULL REFERENCES message, reported_obs TEXT NOT NULL, verbatim_obs TEXT,
  method TEXT NOT NULL CHECK (method IN ('norm_hash','nonce','fuzzy','none')), score REAL,
  outcome TEXT NOT NULL CHECK (outcome IN ('matched','reported_only','verbatim_only','speaker_moved','could_not_confirm')),
  applied_seq INTEGER NOT NULL, CHECK (outcome IN ('reported_only','could_not_confirm') OR verbatim_obs IS NOT NULL));
CREATE TABLE reconciliation_point (tenant_id TEXT NOT NULL DEFAULT 'local',
  recon_id TEXT NOT NULL REFERENCES reconciliation, obs_id TEXT NOT NULL, idx INTEGER NOT NULL,
  quote_status TEXT NOT NULL CHECK (quote_status IN ('quote_verified','quote_failed','no_quote')),
  support TEXT CHECK (support IN ('supported','unsupported')), PRIMARY KEY (recon_id, obs_id, idx));
CREATE TABLE span (tenant_id TEXT NOT NULL DEFAULT 'local',
  span_id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES source, message_id TEXT REFERENCES message,
  obs_id TEXT,                                                              -- text basis, in intake.db
  locator TEXT NOT NULL CHECK (json_valid(locator)), start_char INTEGER NOT NULL, end_char INTEGER NOT NULL,
  quote TEXT NOT NULL, prefix TEXT, suffix TEXT, quote_norm_hash TEXT NOT NULL,
  speaker TEXT NOT NULL CHECK (speaker IN ('user','assistant','tool','external','northstar','system')),
  agent_id TEXT REFERENCES agent, speaker_model_family TEXT,
  origin TEXT NOT NULL CHECK (origin IN ('user_typed','user_pasted','assistant_output','tool_output','external_document',
    'model_reported','northstar_injected','northstar_authored')),
  capture_fidelity TEXT NOT NULL CHECK (capture_fidelity IN ('verbatim_live','verbatim_rendered','verbatim_deferred','model_reported')),
  branch_path TEXT, model TEXT, grounded INTEGER NOT NULL DEFAULT 0 CHECK (grounded IN (0,1)), hedge_verbatim TEXT,
  scope_id TEXT NOT NULL REFERENCES scope,
  sensitivity TEXT NOT NULL DEFAULT 'normal' CHECK (sensitivity IN ('normal','sensitive','private')),
  distressing INTEGER NOT NULL DEFAULT 0 CHECK (distressing IN (0,1)), created_seq INTEGER NOT NULL,
  CHECK (start_char >= 0 AND end_char > start_char),
  CHECK (speaker <> 'assistant' OR agent_id IS NOT NULL));
CREATE INDEX span_message ON span(message_id);
CREATE INDEX span_qhash ON span(quote_norm_hash);
CREATE TABLE episode (tenant_id TEXT NOT NULL DEFAULT 'local',
  episode_id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES source, branch_path TEXT NOT NULL,
  product TEXT, surface TEXT, model TEXT, context_ref TEXT, started_at TEXT, ended_at TEXT, closed_at TEXT,
  identity_state TEXT NOT NULL CHECK (identity_state IN ('identified','session_only','not_identified')),
  connector_id TEXT, connector_session_key TEXT, created_seq INTEGER NOT NULL);
CREATE TABLE episode_message (tenant_id TEXT NOT NULL DEFAULT 'local',
  message_id TEXT PRIMARY KEY REFERENCES message, episode_id TEXT NOT NULL REFERENCES episode);   -- one episode per message

-- Knowledge ---------------------------------------------------------------------------
CREATE TABLE item (tenant_id TEXT NOT NULL DEFAULT 'local',
  item_id TEXT PRIMARY KEY, role TEXT NOT NULL CHECK (role IN ('concept','statement','passage','agenda')),
  content_v INTEGER NOT NULL DEFAULT 1, text TEXT NOT NULL, gist TEXT,
  gist_verified INTEGER NOT NULL DEFAULT 0 CHECK (gist_verified IN (0,1)),
  qualifiers TEXT CHECK (qualifiers IS NULL OR json_valid(qualifiers)),     -- {valid_time, context, version, population, time_sensitive}
  primary_concept TEXT REFERENCES item(item_id),
  certainty TEXT NOT NULL DEFAULT 'unknown' CHECK (certainty IN ('firm','tentative','unknown')), span_size INTEGER,
  holder TEXT NOT NULL CHECK (holder IN ('user','assistant','external','none')),
  status TEXT NOT NULL CHECK (status IN ('active','superseded','retracted','contested','quarantined','discarded','excised')),
  verification TEXT NOT NULL DEFAULT 'unchecked' CHECK (verification IN ('unchecked','not_checkable','supported','contradicted',
    'mixed','cited_unchecked','no_independent_verifier')),                 -- speaker-neutral name (X25)
  user_stance TEXT NOT NULL DEFAULT 'none' CHECK (user_stance IN ('asserted','accepted','questioned','disputed','rejected','none')),
  scope_id TEXT NOT NULL REFERENCES scope,
  sensitivity TEXT NOT NULL DEFAULT 'normal' CHECK (sensitivity IN ('normal','sensitive','private')),
  distressing INTEGER NOT NULL DEFAULT 0 CHECK (distressing IN (0,1)),
  valid_from TEXT, valid_to TEXT, promoted_from TEXT, created_seq INTEGER NOT NULL, updated_seq INTEGER NOT NULL);
CREATE INDEX item_status ON item(status, role);
CREATE TABLE item_tag (tenant_id TEXT NOT NULL DEFAULT 'local',
  item_id TEXT NOT NULL REFERENCES item, tag TEXT NOT NULL, added_seq INTEGER NOT NULL, PRIMARY KEY (item_id, tag));
CREATE TABLE concept (tenant_id TEXT NOT NULL DEFAULT 'local',
  concept_id TEXT PRIMARY KEY REFERENCES item, label TEXT NOT NULL, identity_key TEXT UNIQUE,
  label_fixed_by TEXT REFERENCES correction, alias_of TEXT REFERENCES concept, CHECK (alias_of IS NULL OR alias_of <> concept_id));
CREATE TABLE item_concept (tenant_id TEXT NOT NULL DEFAULT 'local',
  item_id TEXT NOT NULL REFERENCES item, concept_id TEXT NOT NULL REFERENCES concept,
  is_primary INTEGER NOT NULL DEFAULT 0 CHECK (is_primary IN (0,1)), PRIMARY KEY (item_id, concept_id));
CREATE UNIQUE INDEX item_one_primary ON item_concept(item_id) WHERE is_primary = 1;
CREATE INDEX item_concept_rev ON item_concept(concept_id);
CREATE TABLE concept_alias (tenant_id TEXT NOT NULL DEFAULT 'local',
  alias TEXT NOT NULL, concept_id TEXT NOT NULL REFERENCES concept,
  kind TEXT NOT NULL CHECK (kind IN ('alias','former_label','merged')),
  status TEXT NOT NULL CHECK (status IN ('active','reverted')), PRIMARY KEY (alias, concept_id));
CREATE TABLE concept_broader (tenant_id TEXT NOT NULL DEFAULT 'local',      -- changed by concept.created, concept.reparented (X10)
  child TEXT NOT NULL REFERENCES concept, parent TEXT NOT NULL REFERENCES concept,
  status TEXT NOT NULL CHECK (status IN ('active','retracted')), updated_seq INTEGER NOT NULL,   -- row_hist keeps earlier parents
  PRIMARY KEY (child, parent), CHECK (child <> parent));
CREATE TABLE agenda (tenant_id TEXT NOT NULL DEFAULT 'local',
  agenda_id TEXT PRIMARY KEY REFERENCES item,
  kind TEXT NOT NULL CHECK (kind IN ('goal','question','suggested_topic')),   -- 'suggestion' is an item kind tag (CONS)
  goal_basis TEXT CHECK (goal_basis IN ('explicit','reported','inferred')),
  goal_status TEXT CHECK (goal_status IN ('active','paused','done','expired')),
  question_status TEXT CHECK (question_status IN ('open','answered','dormant')),
  topic_status TEXT CHECK (topic_status IN ('suggested','hidden')),
  raised_by TEXT NOT NULL CHECK (raised_by IN ('user','agent','conflict','northstar')), raised_by_agent TEXT REFERENCES agent,
  spawned_from_tension TEXT REFERENCES tension, suggest_reason TEXT,
  authority TEXT NOT NULL DEFAULT 'none' CHECK (authority IN ('none','book_only','full')),
  confirmation_origin TEXT CHECK (confirmation_origin IN ('verbatim_match','reader_click','app_click')), confirmation_seq INTEGER,
  CHECK (kind <> 'goal' OR (goal_basis IS NOT NULL AND goal_status IS NOT NULL)),
  CHECK (kind <> 'question' OR question_status IS NOT NULL),
  CHECK (kind <> 'suggested_topic' OR (raised_by = 'northstar' AND authority = 'none' AND topic_status IS NOT NULL)),
  CHECK (raised_by <> 'northstar' OR kind = 'suggested_topic'),
  CHECK (kind = 'goal' OR authority = 'none'),
  CHECK (goal_basis IS NULL OR goal_basis <> 'explicit' OR authority = 'full'),
  CHECK (goal_basis IS NULL OR goal_basis <> 'inferred' OR authority = 'none'),
  CHECK (authority = 'none' OR goal_basis = 'explicit' OR confirmation_origin IS NOT NULL));
CREATE TABLE agenda_target (tenant_id TEXT NOT NULL DEFAULT 'local',
  agenda_id TEXT NOT NULL REFERENCES agenda, concept_id TEXT NOT NULL REFERENCES concept, PRIMARY KEY (agenda_id, concept_id));
CREATE TABLE agenda_answer (tenant_id TEXT NOT NULL DEFAULT 'local',
  question_id TEXT NOT NULL REFERENCES agenda, answer_item TEXT NOT NULL REFERENCES item,
  linked_seq INTEGER NOT NULL, PRIMARY KEY (question_id, answer_item));

-- Attribution axes --------------------------------------------------------------------
CREATE TABLE attribution (tenant_id TEXT NOT NULL DEFAULT 'local',
  attr_id TEXT PRIMARY KEY, item_id TEXT NOT NULL REFERENCES item, span_id TEXT NOT NULL REFERENCES span,
  evidence_role TEXT NOT NULL CHECK (evidence_role IN ('primary','support','user_evidence','answer','causal_alt')),
  speaker TEXT NOT NULL, agent_id TEXT, speaker_model_family TEXT, origin TEXT NOT NULL,   -- copies of the span (trigger)
  speaker_fidelity TEXT NOT NULL CHECK (speaker_fidelity IN ('by_construction','model_reported','reconciled')),
  capture_fidelity TEXT NOT NULL CHECK (capture_fidelity IN ('verbatim_live','verbatim_rendered','verbatim_deferred',
    'model_reported','reconciled')),
  modality TEXT CHECK (modality IN ('asserts','explains','suggests','asks','denies')), hedge_verbatim TEXT,
  lineage TEXT NOT NULL DEFAULT 'primary' CHECK (lineage IN ('primary','ai_echo','northstar_echo','restatement')),
  lineage_group TEXT NOT NULL, recon_id TEXT REFERENCES reconciliation,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','withdrawn')), added_seq INTEGER NOT NULL,
  CHECK (capture_fidelity <> 'reconciled' OR recon_id IS NOT NULL),
  CHECK (lineage <> 'northstar_echo' OR lineage_group LIKE 'ns:%'));
  -- northstar_echo group = ns:<context_receipt_id>. Apply accepts a receipt from this session, or (AC D4, X17) from any
  -- session whose receipt has the span's speaker_model_family, delivered within 90 days, when the span has no fresh
  -- grounding. Cross-file (session.db), so checked in Apply and by the sweep.
CREATE INDEX attribution_item ON attribution(item_id, evidence_role);
CREATE INDEX attribution_span ON attribution(span_id);
CREATE TABLE stance (tenant_id TEXT NOT NULL DEFAULT 'local',
  stance_id TEXT PRIMARY KEY, item_id TEXT NOT NULL REFERENCES item,
  holder TEXT NOT NULL DEFAULT 'user' CHECK (holder = 'user'),
  attitude TEXT NOT NULL CHECK (attitude IN ('asserted','accepted','questioned','disputed','rejected','none')),
  evidence_kind TEXT NOT NULL CHECK (evidence_kind IN ('explicit','branch_abandoned','reused','restated','thumbs','user_correction')),
  span_id TEXT REFERENCES span, correction_id TEXT REFERENCES correction, belief_from TEXT NOT NULL, belief_to TEXT,
  recorded_seq INTEGER NOT NULL, CHECK (span_id IS NOT NULL OR correction_id IS NOT NULL));
CREATE TABLE verification (tenant_id TEXT NOT NULL DEFAULT 'local',
  ver_id TEXT PRIMARY KEY, item_id TEXT NOT NULL REFERENCES item, content_v INTEGER NOT NULL,
  checkability TEXT NOT NULL CHECK (checkability IN ('checkable','not_checkable','time_sensitive')),
  status TEXT NOT NULL CHECK (status IN ('unchecked','not_checkable','supported','contradicted','mixed','cited_unchecked',
    'no_independent_verifier')),                                            -- X25
  verifier TEXT, verifier_family TEXT,
  independent_of_worker INTEGER NOT NULL CHECK (independent_of_worker IN (0,1)),
  independent_of_speaker INTEGER NOT NULL CHECK (independent_of_speaker IN (0,1)),
  evidence_refs TEXT NOT NULL CHECK (json_valid(evidence_refs)), job_id TEXT, checked_at TEXT NOT NULL, recheck_after TEXT,
  recorded_seq INTEGER NOT NULL,
  CHECK (status NOT IN ('supported','contradicted','mixed') OR json_array_length(evidence_refs) > 0));
CREATE INDEX verification_item ON verification(item_id, recorded_seq);

-- Relations, supersession, Tension ----------------------------------------------------
CREATE TABLE relation (tenant_id TEXT NOT NULL DEFAULT 'local',
  rel_id TEXT PRIMARY KEY, from_id TEXT NOT NULL, to_id TEXT NOT NULL,       -- item, relation or episode IDs
  type TEXT NOT NULL CHECK (type IN ('explains','defines','example_of','applied_in','part_of','broader','prerequisite_of',
    'compares','supports','rebuts','undercuts','refines','answers','advances_goal','supersedes','contradicts','contests','same_as')),
  confidence REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  direction_checked INTEGER NOT NULL DEFAULT 0 CHECK (direction_checked IN (0,1)), direction_verdict TEXT,
  status TEXT NOT NULL CHECK (status IN ('proposed','applied','user_confirmed','user_rejected','retracted')),   -- SPINE §5.2
  created_by TEXT NOT NULL, applied_seq INTEGER, updated_seq INTEGER NOT NULL,
  basis TEXT CHECK (basis IN ('goal_stack','j5','answers','user','reexplained')),   -- goal-link basis, AC §4.4 (X29)
  CHECK (from_id <> to_id), CHECK (type <> 'advances_goal' OR basis IS NOT NULL));
CREATE UNIQUE INDEX relation_once ON relation(from_id, to_id, type) WHERE status IN ('proposed','applied','user_confirmed');
CREATE INDEX relation_from ON relation(from_id, type, status);
CREATE INDEX relation_to ON relation(to_id, type, status);
CREATE TABLE tension (tenant_id TEXT NOT NULL DEFAULT 'local',
  tension_id TEXT PRIMARY KEY, state TEXT NOT NULL CHECK (state IN ('open','resolved','contested')),
  detected_by TEXT NOT NULL, spawned_question TEXT REFERENCES agenda, current_resolution TEXT REFERENCES tension_resolution,
  next_recheck TEXT, opened_seq INTEGER NOT NULL, updated_seq INTEGER NOT NULL);
CREATE TABLE tension_side (tenant_id TEXT NOT NULL DEFAULT 'local',
  tension_id TEXT NOT NULL REFERENCES tension, item_id TEXT NOT NULL REFERENCES item, item_v INTEGER NOT NULL,
  PRIMARY KEY (tension_id, item_id));
CREATE TABLE tension_resolution (tenant_id TEXT NOT NULL DEFAULT 'local',
  resolution_id TEXT PRIMARY KEY, tension_id TEXT NOT NULL REFERENCES tension,
  step TEXT NOT NULL CHECK (step IN ('user_correction','scope','explicit_signal','rank','margin_verified','contested')),
  outcome TEXT NOT NULL CHECK (outcome IN ('both_stand_scoped','superseded','contested')),
  winner TEXT REFERENCES item, inputs TEXT NOT NULL CHECK (json_valid(inputs)), decided_by TEXT,
  margin_class TEXT CHECK (margin_class IN ('clear','narrow')), verify_job TEXT, rule_set_v TEXT NOT NULL,
  audit_state TEXT NOT NULL DEFAULT 'pending' CHECK (audit_state IN ('pending','agreed','disagreed')),
  status TEXT NOT NULL CHECK (status IN ('active','undone')), applied_seq INTEGER NOT NULL, undone_seq INTEGER, undo_cause TEXT,
  CHECK ((outcome = 'superseded') = (winner IS NOT NULL)));
CREATE TABLE supersession (tenant_id TEXT NOT NULL DEFAULT 'local',
  sup_id TEXT PRIMARY KEY, old_item TEXT NOT NULL REFERENCES item, old_v INTEGER NOT NULL, new_item TEXT REFERENCES item,
  reason TEXT NOT NULL CHECK (reason IN ('user_later_statement','ai_self_correction','verifier_contradicted','user_correction',
    'reconciled_absent','scope_split','rank_resolution')),
  evidence_refs TEXT NOT NULL CHECK (json_valid(evidence_refs)), causal_alt_ref TEXT REFERENCES item,
  resolution_id TEXT REFERENCES tension_resolution,
  status TEXT NOT NULL CHECK (status IN ('active','undone')), applied_seq INTEGER NOT NULL, undone_seq INTEGER,
  CHECK (new_item IS NOT NULL OR reason = 'reconciled_absent'),
  CHECK (new_item IS NULL OR new_item <> old_item),
  CHECK (reason <> 'rank_resolution' OR resolution_id IS NOT NULL));
CREATE INDEX supersession_old ON supersession(old_item, status);

-- Corrections -------------------------------------------------------------------------
CREATE TABLE correction (tenant_id TEXT NOT NULL DEFAULT 'local',
  correction_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL CHECK (kind IN ('misstated','reject_content','attribution_fix','conversation_dispute','stance_fix',
    'relation_reject','hide','rename','placement_must','placement_must_not','pin','merge','unmerge','next_step_hide',
    'goal_status','goal_confirmation','question_status','put_back')),
  target_kind TEXT NOT NULL CHECK (target_kind IN ('item','relation','concept','page','sentence','episode','agenda','span')),
  target_id TEXT NOT NULL, target_v INTEGER, payload TEXT NOT NULL CHECK (json_valid(payload)),
  constraint_form TEXT CHECK (constraint_form IN ('must_link','cannot_link','fixed_parent','forbidden_parent','fixed_label',
    'hide','exclude','bar_text','quote_form','fixed_attribution','fixed_stance','fixed_status','pin','fixed_identity')),
  holder TEXT NOT NULL DEFAULT 'user' CHECK (holder = 'user'),
  proposed_via TEXT CHECK (proposed_via IN ('chat_model_reported','chat_unmatched')),
  origin TEXT CHECK (origin IN ('reader_click','app_click','chat_verbatim','chat_verbatim_reconciled')),
  channel TEXT NOT NULL CHECK (channel IN ('reader','widget','chat')),
  evidence_span TEXT REFERENCES span, barred_text_hash TEXT, note_item TEXT REFERENCES item,
  state TEXT NOT NULL CHECK (state IN ('proposed','applied','expired')),
  status TEXT NOT NULL CHECK (status IN ('active','lifted')),
  lifted_by TEXT CHECK (lifted_by IN ('user_undo','superseded','excision')), lifted_ref TEXT, expires_at TEXT,
  proposed_seq INTEGER NOT NULL, applied_seq INTEGER, lifted_seq INTEGER,
  CHECK (state <> 'applied' OR origin IS NOT NULL),                                        -- I22
  CHECK (origin IS NULL OR origin NOT IN ('chat_verbatim','chat_verbatim_reconciled') OR evidence_span IS NOT NULL),
  CHECK (kind <> 'misstated' OR barred_text_hash IS NOT NULL),
  CHECK (status = 'active' OR lifted_by IS NOT NULL),
  CHECK (state <> 'proposed' OR expires_at IS NOT NULL));
CREATE INDEX correction_target ON correction(target_id, state, status);
CREATE TABLE active_constraint (tenant_id TEXT NOT NULL DEFAULT 'local',
  constraint_id TEXT PRIMARY KEY, correction_id TEXT NOT NULL REFERENCES correction,
  form TEXT NOT NULL, subject_id TEXT NOT NULL, object_id TEXT NOT NULL DEFAULT '-', value TEXT,
  UNIQUE (form, subject_id, object_id));
CREATE INDEX active_constraint_obj ON active_constraint(object_id);

-- Tombstones --------------------------------------------------------------------------
-- Excision is a resumable saga (MR-5): the tombstone and its needle HMACs are written first, as 'in_progress', before
-- any store is purged; each store's excision_run records its progress; 'done' once every store is purged and the
-- zero-hit check has run.
CREATE TABLE tombstone (tenant_id TEXT NOT NULL DEFAULT 'local',
  tombstone_id TEXT PRIMARY KEY, target_kind TEXT NOT NULL, target_id TEXT NOT NULL, scope_id TEXT,
  state TEXT NOT NULL CHECK (state IN ('in_progress','done')),
  requested_at TEXT NOT NULL, requested_via TEXT NOT NULL CHECK (requested_via IN ('reader_click','cli')),
  closure_ids TEXT NOT NULL CHECK (json_valid(closure_ids)),               -- IDs only, never content
  stores_purged TEXT NOT NULL CHECK (json_valid(stores_purged)),
  needle_hmacs TEXT NOT NULL CHECK (json_valid(needle_hmacs)),             -- keyed by a per-tombstone Keychain key
  zero_hit TEXT NOT NULL CHECK (zero_hit IN ('pending','pass','fail')), zero_hit_report TEXT,
  external_copies TEXT, completed_at TEXT);

-- Invariant triggers (core-data-model.md §4.6) ----------------------------------------
CREATE TRIGGER attribution_axes BEFORE INSERT ON attribution
WHEN NEW.speaker IS NOT (SELECT speaker FROM span WHERE span_id = NEW.span_id)
  OR NEW.origin IS NOT (SELECT origin FROM span WHERE span_id = NEW.span_id)
  OR NEW.agent_id IS NOT (SELECT agent_id FROM span WHERE span_id = NEW.span_id)
BEGIN SELECT RAISE(ABORT, 'I3/I20: attribution must copy the span axes'); END;
CREATE TRIGGER attribution_axes_frozen BEFORE UPDATE OF speaker, origin, agent_id, span_id, item_id ON attribution
BEGIN SELECT RAISE(ABORT, 'I3/I20: attribution axes are immutable'); END;
CREATE TRIGGER stance_endorsement BEFORE INSERT ON stance
WHEN NEW.attitude IN ('asserted','accepted') AND NOT EXISTS (SELECT 1 FROM span s WHERE s.span_id = NEW.span_id
  AND s.speaker = 'user' AND s.origin = 'user_typed' AND s.capture_fidelity <> 'model_reported')
BEGIN SELECT RAISE(ABORT, 'I4/I22: endorsement needs a verbatim user-typed span'); END;
-- X18: for a span whose observation arrived on channel 'hook', the C12 I5/I22 gate also needs an intake.db
-- origin_confirmation with outcome 'confirmed' before authority tags, explicit goals or applied chat corrections.
-- 'confirmed_degraded' is not enough, and a later 'not_confirmed' revokes what was granted (MR-4).
-- Cross-file, so it runs in Apply before these triggers and the sweep re-checks it.
CREATE TRIGGER authority_tag BEFORE INSERT ON item_tag
WHEN NEW.tag IN ('instruction','preference','constraint') AND NOT EXISTS (
  SELECT 1 FROM attribution a JOIN span s ON s.span_id = a.span_id
  WHERE a.item_id = NEW.item_id AND a.evidence_role IN ('primary','user_evidence') AND a.status = 'active'
    AND s.origin = 'user_typed' AND s.capture_fidelity <> 'model_reported')
BEGIN SELECT RAISE(ABORT, 'I5/I22: authority needs a verbatim user-typed span'); END;
CREATE TRIGGER explicit_goal BEFORE INSERT ON agenda
WHEN NEW.kind = 'goal' AND NEW.goal_basis = 'explicit' AND NOT EXISTS (
  SELECT 1 FROM attribution a JOIN span s ON s.span_id = a.span_id
  WHERE a.item_id = NEW.agenda_id AND a.evidence_role IN ('primary','user_evidence') AND a.status = 'active'
    AND s.origin = 'user_typed' AND s.capture_fidelity <> 'model_reported')
BEGIN SELECT RAISE(ABORT, 'I5/I22: explicit goal needs a verbatim user-typed span'); END;
CREATE TRIGGER explicit_goal_upd BEFORE UPDATE OF goal_basis ON agenda
WHEN NEW.goal_basis = 'explicit' AND OLD.goal_basis IS NOT 'explicit' AND NOT EXISTS (
  SELECT 1 FROM attribution a JOIN span s ON s.span_id = a.span_id
  WHERE a.item_id = NEW.agenda_id AND a.evidence_role IN ('primary','user_evidence') AND a.status = 'active'
    AND s.origin = 'user_typed' AND s.capture_fidelity <> 'model_reported')
BEGIN SELECT RAISE(ABORT, 'I22: a reported goal becomes explicit only on a verbatim match'); END;
CREATE TRIGGER message_immutable BEFORE UPDATE OF speaker, origin, agent_id, content_hash, source_id, occurred_at ON message
WHEN NOT ns_excision_active()
BEGIN SELECT RAISE(ABORT, 'I20: capture fields are immutable'); END;
CREATE TRIGGER correction_lift BEFORE UPDATE OF status ON correction
WHEN NEW.status = 'lifted' AND NEW.lifted_by IS NULL
BEGIN SELECT RAISE(ABORT, 'I21: a correction is lifted only by user undo, a later correction or excision'); END;
CREATE TRIGGER row_hist_close_only BEFORE UPDATE ON row_hist
WHEN (OLD.rec_to_seq IS NOT NULL OR NEW.snapshot IS NOT OLD.snapshot OR NEW.rec_from_seq IS NOT OLD.rec_from_seq)
  AND NOT ns_excision_active()
BEGIN SELECT RAISE(ABORT, 'I6: history rows are closed once and never edited'); END;
-- I6 append-only: no UPDATE or DELETE outside an excision connection (ns_excision_active(), header; MR-5).
CREATE TRIGGER event_no_upd BEFORE UPDATE ON event WHEN NOT ns_excision_active()
BEGIN SELECT RAISE(ABORT, 'I6 append-only: event'); END;
CREATE TRIGGER event_no_del BEFORE DELETE ON event WHEN NOT ns_excision_active()
BEGIN SELECT RAISE(ABORT, 'I6 append-only: event'); END;
CREATE TRIGGER event_subject_no_upd BEFORE UPDATE ON event_subject WHEN NOT ns_excision_active()
BEGIN SELECT RAISE(ABORT, 'I6 append-only: event_subject'); END;
CREATE TRIGGER event_subject_no_del BEFORE DELETE ON event_subject WHEN NOT ns_excision_active()
BEGIN SELECT RAISE(ABORT, 'I6 append-only: event_subject'); END;
CREATE TRIGGER row_hist_no_del BEFORE DELETE ON row_hist WHEN NOT ns_excision_active()
BEGIN SELECT RAISE(ABORT, 'I6 append-only: row_hist'); END;
CREATE TRIGGER span_no_upd BEFORE UPDATE ON span WHEN NOT ns_excision_active()
BEGIN SELECT RAISE(ABORT, 'I6/I20 append-only: span'); END;
CREATE TRIGGER span_no_del BEFORE DELETE ON span WHEN NOT ns_excision_active()
BEGIN SELECT RAISE(ABORT, 'I6 append-only: span'); END;
CREATE TRIGGER stance_no_upd BEFORE UPDATE ON stance WHEN NOT ns_excision_active()
BEGIN SELECT RAISE(ABORT, 'I6 append-only: stance'); END;
CREATE TRIGGER stance_no_del BEFORE DELETE ON stance WHEN NOT ns_excision_active()
BEGIN SELECT RAISE(ABORT, 'I6 append-only: stance'); END;
CREATE TRIGGER verification_no_upd BEFORE UPDATE ON verification WHEN NOT ns_excision_active()
BEGIN SELECT RAISE(ABORT, 'I6 append-only: verification'); END;
CREATE TRIGGER verification_no_del BEFORE DELETE ON verification WHEN NOT ns_excision_active()
BEGIN SELECT RAISE(ABORT, 'I6 append-only: verification'); END;
CREATE TRIGGER reconciliation_no_upd BEFORE UPDATE ON reconciliation WHEN NOT ns_excision_active()
BEGIN SELECT RAISE(ABORT, 'I6 append-only: reconciliation'); END;
CREATE TRIGGER reconciliation_no_del BEFORE DELETE ON reconciliation WHEN NOT ns_excision_active()
BEGIN SELECT RAISE(ABORT, 'I6 append-only: reconciliation'); END;
CREATE TRIGGER message_observation_no_upd BEFORE UPDATE ON message_observation WHEN NOT ns_excision_active()
BEGIN SELECT RAISE(ABORT, 'I6 append-only: message_observation'); END;
CREATE TRIGGER message_observation_no_del BEFORE DELETE ON message_observation WHEN NOT ns_excision_active()
BEGIN SELECT RAISE(ABORT, 'I6 append-only: message_observation'); END;
CREATE TRIGGER apply_txn_no_upd BEFORE UPDATE ON apply_txn WHEN NOT ns_excision_active()
BEGIN SELECT RAISE(ABORT, 'I6 append-only: apply_txn'); END;
-- Missing *_no_del guards (ROB smaller issue). Corrections are lifted and attributions withdrawn, never deleted.
CREATE TRIGGER apply_txn_no_del BEFORE DELETE ON apply_txn WHEN NOT ns_excision_active()
BEGIN SELECT RAISE(ABORT, 'I6 append-only: apply_txn'); END;
CREATE TRIGGER correction_no_del BEFORE DELETE ON correction WHEN NOT ns_excision_active()
BEGIN SELECT RAISE(ABORT, 'I6/I21: corrections are lifted, never deleted'); END;
CREATE TRIGGER active_constraint_no_del BEFORE DELETE ON active_constraint
WHEN NOT ns_excision_active()
  AND (SELECT status FROM correction WHERE correction_id = OLD.correction_id) IS NOT 'lifted'
BEGIN SELECT RAISE(ABORT, 'I21: an active constraint is removed only when its correction is lifted'); END;
CREATE TRIGGER attribution_no_del BEFORE DELETE ON attribution WHEN NOT ns_excision_active()
BEGIN SELECT RAISE(ABORT, 'I6: attributions are withdrawn, never deleted'); END;
CREATE TRIGGER reconciliation_point_no_del BEFORE DELETE ON reconciliation_point WHEN NOT ns_excision_active()
BEGIN SELECT RAISE(ABORT, 'I6 append-only: reconciliation_point'); END;
CREATE TRIGGER tombstone_no_del BEFORE DELETE ON tombstone          -- never deleted, even by excision (restore safety)
BEGIN SELECT RAISE(ABORT, 'I6: tombstones are never deleted'); END;
-- MR-3: one applied proposal per job; the ledger row is append-only.
CREATE TRIGGER applied_job_once BEFORE INSERT ON applied_job
WHEN EXISTS (SELECT 1 FROM applied_job WHERE job_id = NEW.job_id AND proposal_id <> NEW.proposal_id)
BEGIN SELECT RAISE(ABORT, 'MR-3/I14: a job applies at most one proposal'); END;
CREATE TRIGGER applied_job_no_upd BEFORE UPDATE ON applied_job WHEN NOT ns_excision_active()
BEGIN SELECT RAISE(ABORT, 'I6 append-only: applied_job'); END;
CREATE TRIGGER applied_job_no_del BEFORE DELETE ON applied_job WHEN NOT ns_excision_active()
BEGIN SELECT RAISE(ABORT, 'I6 append-only: applied_job'); END;
-- MR-9: both relation endpoints exist as an item, a relation or an episode. Apply derives dependency closures in code,
-- so an abort here is a code fault, never a worker's choice.
CREATE TRIGGER relation_endpoints BEFORE INSERT ON relation
WHEN NOT EXISTS (SELECT 1 FROM item WHERE item_id = NEW.from_id UNION ALL SELECT 1 FROM relation WHERE rel_id = NEW.from_id
                 UNION ALL SELECT 1 FROM episode WHERE episode_id = NEW.from_id)
  OR NOT EXISTS (SELECT 1 FROM item WHERE item_id = NEW.to_id UNION ALL SELECT 1 FROM relation WHERE rel_id = NEW.to_id
                 UNION ALL SELECT 1 FROM episode WHERE episode_id = NEW.to_id)
BEGIN SELECT RAISE(ABORT, 'MR-9: relation endpoints must exist as item, relation or episode'); END;
-- State tables (item, message, relation, ...) are updated only by Apply, inside a transaction that also
-- appends the event and closes/opens row_hist. Postgres: same triggers in PL/pgSQL plus REVOKE UPDATE, DELETE.

-- =====================================================================================
-- STORE: session.db   (writer: C10 session applier; C23 writes through it)
-- =====================================================================================
-- Readers include C23 (routing, pending_resume) and C08 (goal cards; X09, X29).
CREATE TABLE excision_run (tenant_id TEXT NOT NULL DEFAULT 'local', run_id TEXT PRIMARY KEY, tombstone_id TEXT,
  state TEXT NOT NULL CHECK (state IN ('in_progress','done')), started_at TEXT NOT NULL, ended_at TEXT);   -- progress only (MR-5)
CREATE TABLE session (tenant_id TEXT NOT NULL DEFAULT 'local',
  handle TEXT PRIMARY KEY, account_ref TEXT NOT NULL,
  account_source TEXT NOT NULL CHECK (account_source IN ('channel','install_declaration','ax_label')),   -- X14
  connector_id TEXT NOT NULL, product_family TEXT, product TEXT, product_mode TEXT,          -- metadata only (I23)
  capabilities_declared TEXT NOT NULL CHECK (json_valid(capabilities_declared)), manifest_v TEXT, mcp_profile TEXT, mcp_flags TEXT,
  start_kind TEXT NOT NULL CHECK (start_kind IN ('startup','resume','clear','compact','fork','new_chat','restart')),
  parent_handle TEXT REFERENCES session, context_ref TEXT, title TEXT,
  arm TEXT NOT NULL CHECK (arm IN ('treatment','shadow','none')), source_id TEXT,           -- ledger.db
  persist_policy TEXT NOT NULL CHECK (persist_policy IN ('full','none','on_write')),
    -- CONS-9: C04 derives it from capture_mode. per_call (and hooks) -> full; widget_record, save_on_request -> on_write
    -- (only turns a declared write recorded); receipts_only -> none (the stateless per-turn tool keeps nothing, FEAS-1)
  scope_id TEXT NOT NULL, started_at TEXT NOT NULL, ended_at TEXT, end_reason TEXT,
  held INTEGER NOT NULL DEFAULT 0 CHECK (held IN (0,1)));    -- X11: a late exclude rule matched this session; as scope.held
CREATE INDEX session_ended ON session(ended_at);
CREATE TABLE session_conv_key (tenant_id TEXT NOT NULL DEFAULT 'local',
  handle TEXT NOT NULL REFERENCES session, key_kind TEXT NOT NULL, key_value TEXT NOT NULL,
  method TEXT NOT NULL CHECK (method IN ('exact_key','nonce_echo','process_lineage','widget_origin','content_hash_sequence',
    'fuzzy_time_text','minted')),                                           -- X14
  confidence REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  status TEXT NOT NULL CHECK (status IN ('active','reverted')), joined_at TEXT NOT NULL, reverted_at TEXT, revert_reason TEXT,
  PRIMARY KEY (handle, key_kind, key_value));
CREATE INDEX conv_key_lookup ON session_conv_key(key_kind, key_value, status);
CREATE TABLE identity_join_event (tenant_id TEXT NOT NULL DEFAULT 'local',
  seq INTEGER PRIMARY KEY, handle TEXT NOT NULL, key_kind TEXT NOT NULL, key_value TEXT NOT NULL,
  op TEXT NOT NULL CHECK (op IN ('join','revert')), method TEXT, confidence REAL, evidence TEXT, at TEXT NOT NULL);
CREATE TABLE turn_nonce (tenant_id TEXT NOT NULL DEFAULT 'local',   -- turn tag 'NS-XXXXXX.<n>' (X14)
  nonce TEXT PRIMARY KEY, handle TEXT NOT NULL REFERENCES session, branch_path TEXT NOT NULL, turn INTEGER NOT NULL,
  artifact_id TEXT, issued_at TEXT NOT NULL);
CREATE TABLE widget_instance (tenant_id TEXT NOT NULL DEFAULT 'local',
  handle TEXT NOT NULL REFERENCES session, seq INTEGER NOT NULL, host_widget_session_id TEXT,
  created_at TEXT NOT NULL, superseded_at TEXT, PRIMARY KEY (handle, seq));
-- Turns recorded by a declared write (CONS-9, FEAS-1): the widget's record, an approved save_chat, or a note.
-- Written by the C10 applier when C06 accepts that write; the per-turn guard on session_item reads it.
CREATE TABLE recorded_turn (tenant_id TEXT NOT NULL DEFAULT 'local',
  handle TEXT NOT NULL REFERENCES session, branch_path TEXT NOT NULL, turn INTEGER NOT NULL,
  write_kind TEXT NOT NULL CHECK (write_kind IN ('widget_record','save_chat','note')),
  write_ref TEXT NOT NULL,                                                  -- receipt token or envelope ID of the write
  recorded_at TEXT NOT NULL, PRIMARY KEY (handle, branch_path, turn));
CREATE TABLE session_item (tenant_id TEXT NOT NULL DEFAULT 'local',
  item_id TEXT PRIMARY KEY, handle TEXT NOT NULL REFERENCES session,
  role TEXT NOT NULL CHECK (role IN ('concept','statement','passage','agenda')),
  kind_tags TEXT NOT NULL CHECK (json_valid(kind_tags)), text TEXT NOT NULL, gist TEXT,
  by_ TEXT NOT NULL CHECK (by_ IN ('user','ai')),                         -- original speaker, kept on seeds (X07)
  speaker TEXT NOT NULL CHECK (speaker IN ('user','assistant','tool','external','northstar','system')), agent_id TEXT,
  origin TEXT NOT NULL CHECK (origin IN ('user_typed','user_pasted','assistant_output','tool_output','external_document',
    'model_reported','northstar_injected','northstar_authored')),
  capture_fidelity TEXT NOT NULL CHECK (capture_fidelity IN ('verbatim_live','verbatim_rendered','verbatim_deferred',
    'model_reported','reconciled')),
  goal_level TEXT CHECK (goal_level IN ('north_star','session_goal','focus')),
  constraint_force TEXT CHECK (constraint_force IN ('must','should')),
  user_reaction TEXT CHECK (user_reaction IN ('accepted','challenged','unknown')), reason TEXT,
  source_turn INTEGER, source_span TEXT CHECK (source_span IS NULL OR json_valid(source_span)),   -- {obs_id, start, end, quote}
  status TEXT NOT NULL CHECK (status IN ('provisional','superseded','retracted','contested','discarded','promoted')),
  authority TEXT NOT NULL CHECK (authority IN ('provisional','reported','confirmed')),
    -- provisional: in-session verbatim; confirmed: seeded long-term with authority; reported: model-reported (I22). X07
  seeded_from TEXT CHECK (seeded_from IS NULL OR (json_valid(seeded_from)
    AND json_extract(seeded_from, '$.item') IS NOT NULL AND json_extract(seeded_from, '$.artifact_hash') IS NOT NULL)),
    -- {item: "<item_id>@<version>", artifact_hash, delivery_receipt}; the receipt is absent only for guard_only (X07)
  seed_kind TEXT CHECK (seed_kind IN ('goal','constraint','reported_goal','rejected','disputed','conclusion','knowledge',
    'superseded','open_question','contested','provisional')),              -- ai-continuity.md §5.1
  delivery TEXT CHECK (delivery IN ('delivered','unknown','guard_only')), on_route INTEGER CHECK (on_route IN (0,1)),
  promoted_to TEXT, branch_path TEXT NOT NULL, created_op INTEGER NOT NULL, updated_op INTEGER NOT NULL,
  CHECK (constraint_force IS NULL OR authority = 'reported'
         OR (speaker = 'user' AND origin = 'user_typed' AND capture_fidelity <> 'model_reported')),
  CHECK (seeded_from IS NOT NULL OR source_span IS NOT NULL),
  CHECK ((seeded_from IS NULL) = (seed_kind IS NULL) AND (seeded_from IS NULL) = (delivery IS NULL)
         AND (seeded_from IS NULL) = (on_route IS NULL)),
  CHECK (delivery IS NULL OR delivery = 'guard_only' OR json_extract(seeded_from, '$.delivery_receipt') IS NOT NULL));
CREATE INDEX session_item_recent ON session_item(status, handle);
CREATE TABLE session_op (tenant_id TEXT NOT NULL DEFAULT 'local',
  op_seq INTEGER PRIMARY KEY, handle TEXT NOT NULL REFERENCES session, branch_path TEXT NOT NULL, turn INTEGER NOT NULL,
  op TEXT NOT NULL CHECK (op IN ('ADD','REFINE','SUPERSEDE','RETRACT','MARK_CONTESTED','GOAL_PUSH','GOAL_POP','GOAL_SUPERSEDE',
    'ASSUMPTION_CONFIRM','ARTIFACT_VERSION')),               -- seeds are ADD; routing is a routing_record row (X07)
  item_id TEXT, actor TEXT NOT NULL, actor_ref TEXT,          -- seeding: actor_ref = continuity_params version
  payload TEXT NOT NULL CHECK (json_valid(payload)),
  validator_results TEXT NOT NULL CHECK (json_valid(validator_results)), idem_key TEXT NOT NULL UNIQUE, at TEXT NOT NULL,
  CHECK (actor <> 'seeding' OR actor_ref IS NOT NULL));
CREATE TABLE turn_receipt (tenant_id TEXT NOT NULL DEFAULT 'local',
  handle TEXT NOT NULL REFERENCES session, branch_path TEXT NOT NULL, turn INTEGER NOT NULL,
  arm TEXT NOT NULL CHECK (arm IN ('treatment','shadow','none')),
  capture_user TEXT, capture_ai TEXT, inject_turn TEXT, widget TEXT, check_reply TEXT, gaps TEXT,
  PRIMARY KEY (handle, branch_path, turn));
CREATE TABLE continuity_receipt (tenant_id TEXT NOT NULL DEFAULT 'local',
  handle TEXT PRIMARY KEY REFERENCES session, start_kind TEXT NOT NULL, parent_handle TEXT,
  arm TEXT NOT NULL CHECK (arm IN ('treatment','shadow','none')),
  routed_on TEXT NOT NULL CHECK (routed_on IN ('context_ref','parent_handle','first_message_verbatim','hint_text','none')),
  goals_routed TEXT, pack_artifact TEXT, pack_delivered TEXT CHECK (pack_delivered IN ('true','false','unknown')),
  placement TEXT, seeded TEXT, reexplain_hits TEXT, turns_seen TEXT,
  written_late INTEGER NOT NULL DEFAULT 0 CHECK (written_late IN (0,1)), written_at TEXT NOT NULL);
CREATE TABLE context_receipt (tenant_id TEXT NOT NULL DEFAULT 'local',
  receipt_id TEXT PRIMARY KEY, handle TEXT NOT NULL REFERENCES session, turn INTEGER, artifact_id TEXT NOT NULL,
  artifact_hash TEXT NOT NULL, kind TEXT NOT NULL, placement TEXT NOT NULL,
  delivered TEXT NOT NULL CHECK (delivered IN ('true','false','unknown')),
  suppressed_by_arm INTEGER NOT NULL DEFAULT 0, at TEXT NOT NULL,
  speaker_model_family TEXT);       -- the receiving session's assistant family (agent registry, I23); cross-session echo, X17
CREATE INDEX context_receipt_session ON context_receipt(handle, at);
CREATE INDEX context_receipt_family ON context_receipt(speaker_model_family, at);
CREATE TABLE context_receipt_item (tenant_id TEXT NOT NULL DEFAULT 'local',
  receipt_id TEXT NOT NULL REFERENCES context_receipt, item_id TEXT NOT NULL, item_v INTEGER, slice_id TEXT,
  text_hash TEXT NOT NULL, PRIMARY KEY (receipt_id, item_id));
CREATE INDEX context_receipt_item_rev ON context_receipt_item(item_id);
CREATE TABLE drift_verdict (tenant_id TEXT NOT NULL DEFAULT 'local',
  verdict_id TEXT PRIMARY KEY, handle TEXT NOT NULL REFERENCES session, turn INTEGER NOT NULL,
  items_checked TEXT NOT NULL, results TEXT NOT NULL, severity TEXT, judge_model TEXT, judge_family TEXT,
  independent INTEGER NOT NULL CHECK (independent IN (0,1)), correction_id TEXT, at TEXT NOT NULL);
CREATE TABLE queued_correction (tenant_id TEXT NOT NULL DEFAULT 'local',
  correction_id TEXT PRIMARY KEY, handle TEXT NOT NULL REFERENCES session, for_turn INTEGER, text TEXT NOT NULL,
  item_ids TEXT NOT NULL, weak INTEGER NOT NULL DEFAULT 0 CHECK (weak IN (0,1)),
  status TEXT NOT NULL CHECK (status IN ('queued','delivered','expired','superseded')),
  created_at TEXT NOT NULL, delivered_receipt TEXT);
CREATE TABLE routing_record (tenant_id TEXT NOT NULL DEFAULT 'local',    -- C23 routing, written by C10 (no ROUTE op; X07)
  handle TEXT NOT NULL REFERENCES session, seq INTEGER NOT NULL, routed_on TEXT NOT NULL, goals TEXT NOT NULL,
  at TEXT NOT NULL, PRIMARY KEY (handle, seq));
-- Pending-resume registry (X09): restart level 'suggested'. One registry, written by the C10 applier, read by C23 when
-- routing. expires_at = created_at + 24 h. Adopted only by a chat naming the handle, or a C23 route with p >= 0.7; the
-- adopter gets parent_handle (lineage, labelled) and adoption is reversible ('reverted').
CREATE TABLE pending_resume (tenant_id TEXT NOT NULL DEFAULT 'local',
  pending_id TEXT PRIMARY KEY, parent_handle TEXT NOT NULL REFERENCES session,
  artifact_id TEXT NOT NULL, artifact_hash TEXT NOT NULL,                  -- resume_pack in artifacts.db
  goal_ids TEXT NOT NULL CHECK (json_valid(goal_ids)), created_at TEXT NOT NULL, expires_at TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('pending','adopted','expired','reverted')),
  adopted_by TEXT REFERENCES session, adopted_via TEXT CHECK (adopted_via IN ('explicit_handle','c23_route')),
  route_p REAL CHECK (route_p BETWEEN 0 AND 1), adopted_at TEXT, reverted_at TEXT,
  CHECK (expires_at > created_at),
  CHECK (state NOT IN ('adopted','reverted') OR (adopted_by IS NOT NULL AND adopted_via IS NOT NULL)),
  CHECK (adopted_via IS NULL OR adopted_via <> 'c23_route' OR (route_p IS NOT NULL AND route_p >= 0.7)),
  CHECK (adopted_by IS NULL OR adopted_by <> parent_handle));
CREATE UNIQUE INDEX pending_resume_open ON pending_resume(parent_handle) WHERE state = 'pending';
CREATE INDEX pending_resume_live ON pending_resume(state, expires_at);
CREATE TABLE reexplain_hit (tenant_id TEXT NOT NULL DEFAULT 'local',
  handle TEXT NOT NULL REFERENCES session, turn INTEGER NOT NULL, item_id TEXT NOT NULL, span TEXT NOT NULL,
  capture_fidelity TEXT NOT NULL, verdict_by TEXT NOT NULL, at TEXT NOT NULL, PRIMARY KEY (handle, turn, item_id));
CREATE TABLE fast_model_call (tenant_id TEXT NOT NULL DEFAULT 'local',          -- same shape as jobs.db model_call
  call_id TEXT PRIMARY KEY, handle TEXT, role TEXT NOT NULL, provider TEXT NOT NULL, model_returned TEXT NOT NULL,
  model_family TEXT NOT NULL, prompt_hash TEXT NOT NULL, input_fingerprint TEXT NOT NULL, input_ids TEXT NOT NULL,
  egress_policy_v TEXT NOT NULL, redaction_report TEXT, raw_output TEXT, parsed_output TEXT,
  tokens_in INTEGER, tokens_out INTEGER, cost_microusd INTEGER, latency_ms INTEGER, fault_injected TEXT,
  started_at TEXT NOT NULL, ended_at TEXT, excised INTEGER NOT NULL DEFAULT 0 CHECK (excised IN (0,1)));
-- Per-turn persistence guard (CONS-9; replaces path_b_no_items): a session item is stored when the session's policy
-- is 'full', or 'on_write' and its turn was recorded by a declared write; never when 'none'.
CREATE TRIGGER session_item_persist BEFORE INSERT ON session_item
WHEN NOT EXISTS (SELECT 1 FROM session s WHERE s.handle = NEW.handle AND (s.persist_policy = 'full'
    OR (s.persist_policy = 'on_write' AND EXISTS (SELECT 1 FROM recorded_turn r WHERE r.handle = NEW.handle
        AND r.branch_path = NEW.branch_path AND r.turn = NEW.source_turn))))
BEGIN SELECT RAISE(ABORT, 'CONS-9: session items persist only under full, or on_write for a recorded turn'); END;
CREATE TRIGGER session_op_no_upd BEFORE UPDATE ON session_op WHEN NOT ns_excision_active()
BEGIN SELECT RAISE(ABORT, 'session ops are append-only'); END;
CREATE TRIGGER session_op_no_del BEFORE DELETE ON session_op WHEN NOT ns_excision_active()
BEGIN SELECT RAISE(ABORT, 'session ops are append-only'); END;

-- =====================================================================================
-- STORE: index.db   (writer: C08; rebuildable)
-- =====================================================================================
CREATE TABLE excision_run (tenant_id TEXT NOT NULL DEFAULT 'local', run_id TEXT PRIMARY KEY, tombstone_id TEXT,
  state TEXT NOT NULL CHECK (state IN ('in_progress','done')), started_at TEXT NOT NULL, ended_at TEXT);   -- progress only (MR-5)
CREATE TABLE indexer_offset (tenant_id TEXT NOT NULL DEFAULT 'local',
  consumer TEXT PRIMARY KEY, ledger_seq INTEGER NOT NULL, session_seq INTEGER, at TEXT NOT NULL);
CREATE TABLE best_rank (tenant_id TEXT NOT NULL DEFAULT 'local',
  item_id TEXT PRIMARY KEY, content_v INTEGER NOT NULL, role TEXT NOT NULL, status TEXT NOT NULL,
  rank_group TEXT NOT NULL, is_best INTEGER NOT NULL CHECK (is_best IN (0,1)),
  ver_tier INTEGER NOT NULL CHECK (ver_tier BETWEEN 0 AND 3),   -- 3 supported; 2 mixed; 1 unchecked, not_checkable,
                                                                 -- cited_unchecked, no_independent_verifier; 0 contradicted (X25)
  lineages INTEGER NOT NULL, grounded INTEGER NOT NULL,
  recency TEXT, rank_key TEXT NOT NULL, rank_reason TEXT NOT NULL,
  scope_id TEXT NOT NULL, sensitivity TEXT NOT NULL, distressing INTEGER NOT NULL,
  best_capture TEXT NOT NULL, speaker_fidelity TEXT NOT NULL, speakers TEXT NOT NULL,
  pack_slot TEXT CHECK (pack_slot IN ('goal','reported','knowledge','conclusion','question','rejected','disputed','contested',
    'recent_provisional')),
  pack_eligible INTEGER NOT NULL, book_eligible INTEGER NOT NULL, corrected INTEGER NOT NULL,
  newer_evidence_since_correction INTEGER NOT NULL DEFAULT 0, updated_seq INTEGER NOT NULL);
CREATE INDEX best_rank_pick ON best_rank(scope_id, pack_eligible, is_best, ver_tier DESC, lineages DESC);
CREATE INDEX best_rank_group ON best_rank(rank_group);
CREATE TABLE item_agent (tenant_id TEXT NOT NULL DEFAULT 'local',
  item_id TEXT NOT NULL, agent_id TEXT NOT NULL, PRIMARY KEY (agent_id, item_id));
CREATE TABLE fts_map (tenant_id TEXT NOT NULL DEFAULT 'local',
  rowid INTEGER PRIMARY KEY,
  obj_kind TEXT NOT NULL CHECK (obj_kind IN ('item','span','source_title','concept_label','goal_card')),   -- goal_card: X29
  obj_id TEXT NOT NULL, obj_v INTEGER, UNIQUE (obj_kind, obj_id, obj_v));
CREATE VIRTUAL TABLE text_fts USING fts5(body, content='', contentless_delete=1, tokenize='unicode61 remove_diacritics 2');
INSERT INTO text_fts(text_fts, rank) VALUES ('secure-delete', 1);
CREATE TABLE embedding (tenant_id TEXT NOT NULL DEFAULT 'local',
  obj_kind TEXT NOT NULL, obj_id TEXT NOT NULL, obj_v INTEGER NOT NULL, model_id TEXT NOT NULL,
  dim INTEGER NOT NULL, dtype TEXT NOT NULL CHECK (dtype IN ('f16','f32','i8')), vec BLOB NOT NULL,
  PRIMARY KEY (obj_kind, obj_id, obj_v, model_id));
CREATE TABLE edge_view (tenant_id TEXT NOT NULL DEFAULT 'local',
  from_id TEXT NOT NULL, type TEXT NOT NULL, to_id TEXT NOT NULL, weight TEXT NOT NULL CHECK (weight IN ('high','medium','low')),
  confidence REAL, direction_checked INTEGER NOT NULL, PRIMARY KEY (from_id, type, to_id));
CREATE INDEX edge_view_to ON edge_view(to_id, type);
CREATE TABLE engagement_event (tenant_id TEXT NOT NULL DEFAULT 'local',              -- dated records only; no state, no score
  eng_id TEXT PRIMARY KEY, concept_id TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('explained_to','asked_about','used','restated')),
  span_id TEXT NOT NULL, agent_id TEXT, at TEXT NOT NULL, derived_seq INTEGER NOT NULL);
CREATE INDEX engagement_concept ON engagement_event(concept_id, at);
CREATE TABLE anomaly_mark (tenant_id TEXT NOT NULL DEFAULT 'local',
  item_id TEXT NOT NULL, page_id TEXT NOT NULL, kind TEXT NOT NULL, at TEXT NOT NULL, PRIMARY KEY (item_id, page_id, kind));
CREATE TABLE concept_facts (tenant_id TEXT NOT NULL DEFAULT 'local',  -- facts about the content, never about the user
  concept_id TEXT PRIMARY KEY, has_explanation_leaf INTEGER NOT NULL, mentioned INTEGER NOT NULL,
  mention_breadth INTEGER NOT NULL, independent_episodes INTEGER NOT NULL, substantive_teaching INTEGER NOT NULL,
  computed_seq INTEGER NOT NULL);
CREATE TABLE derived_agenda (tenant_id TEXT NOT NULL DEFAULT 'local',
  view_id TEXT PRIMARY KEY, kind TEXT NOT NULL CHECK (kind IN ('next_step','gap')),
  goal_id TEXT, concept_id TEXT, item_id TEXT,
  reason_code TEXT NOT NULL CHECK (reason_code IN ('ready','asked','raised','suggested','mentioned','direction','unsettled',
    'check','dangling','prerequisite')),
  score TEXT NOT NULL, labels TEXT, computed_seq INTEGER NOT NULL);
CREATE INDEX derived_agenda_goal ON derived_agenda(goal_id, kind);
-- Goal cards (X29): the C23 router's candidates (ai-continuity.md §4.1). C08 rebuilds them on ledger.committed and on
-- session goal changes (it reads session.db); they are in FTS (fts_map 'goal_card') and the embedding cache.
CREATE TABLE goal_card (tenant_id TEXT NOT NULL DEFAULT 'local',
  goal_id TEXT PRIMARY KEY,                                                 -- agenda ID (ledger.db) or session item ID
  goal_store TEXT NOT NULL CHECK (goal_store IN ('ledger','session')), handle TEXT,
  goal_basis TEXT, goal_status TEXT, text TEXT NOT NULL, aliases TEXT CHECK (aliases IS NULL OR json_valid(aliases)),
  target_labels TEXT NOT NULL CHECK (json_valid(target_labels)),
  top_item_gists TEXT NOT NULL CHECK (json_valid(top_item_gists) AND json_array_length(top_item_gists) <= 8),
  open_questions TEXT NOT NULL CHECK (json_valid(open_questions)),
  session_contexts TEXT NOT NULL CHECK (json_valid(session_contexts)),     -- [{handle, context_ref, title}]
  last_active_at TEXT, scope_id TEXT NOT NULL, sensitivity TEXT NOT NULL, ledger_seq INTEGER NOT NULL, session_seq INTEGER,
  CHECK (goal_store = 'ledger' OR handle IS NOT NULL));
CREATE INDEX goal_card_recent ON goal_card(goal_status, last_active_at);

-- =====================================================================================
-- STORE: artifacts.db   (writer: C15)
-- =====================================================================================
CREATE TABLE excision_run (tenant_id TEXT NOT NULL DEFAULT 'local', run_id TEXT PRIMARY KEY, tombstone_id TEXT,
  state TEXT NOT NULL CHECK (state IN ('in_progress','done')), started_at TEXT NOT NULL, ended_at TEXT);   -- progress only (MR-5)
CREATE TABLE artifact (tenant_id TEXT NOT NULL DEFAULT 'local',
  artifact_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL CHECK (kind IN ('pin','card','correction','core_pack','resume_pack','boot_text','charter','slice','prefill')),
  handle TEXT, items TEXT NOT NULL CHECK (json_valid(items)),                  -- [{id, v, slot}]
  built_from_seq INTEGER NOT NULL, budget_chars INTEGER, render_profile TEXT, truncations TEXT,
  text TEXT NOT NULL, hash TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL);
CREATE INDEX artifact_handle ON artifact(handle, created_at);
CREATE TABLE artifact_shingle (tenant_id TEXT NOT NULL DEFAULT 'local',
  shingle_hash TEXT NOT NULL, artifact_id TEXT NOT NULL REFERENCES artifact, PRIMARY KEY (shingle_hash, artifact_id));

-- =====================================================================================
-- STORE: book.db   (writer: C16; BookLedger, Edition, BlockVersion DDL belongs to the C16 design)
-- =====================================================================================
CREATE TABLE excision_run (tenant_id TEXT NOT NULL DEFAULT 'local', run_id TEXT PRIMARY KEY, tombstone_id TEXT,
  state TEXT NOT NULL CHECK (state IN ('in_progress','done')), started_at TEXT NOT NULL, ended_at TEXT);   -- progress only (MR-5)
CREATE TABLE landmark (tenant_id TEXT NOT NULL DEFAULT 'local',
  landmark_id TEXT PRIMARY KEY, kind TEXT NOT NULL CHECK (kind IN ('page','chapter','part','block','sentence')),
  concept_id TEXT, status TEXT NOT NULL CHECK (status IN ('active','merged','split','retired')),
  current_label TEXT, label_source TEXT CHECK (label_source IN ('code','model_checked','user')), current_number TEXT,
  redirect_to TEXT, updated_build TEXT NOT NULL, CHECK (status = 'active' OR redirect_to IS NOT NULL));
CREATE TABLE landmark_label (tenant_id TEXT NOT NULL DEFAULT 'local',
  landmark_id TEXT NOT NULL REFERENCES landmark, label TEXT NOT NULL, number TEXT, from_build TEXT NOT NULL, to_build TEXT,
  PRIMARY KEY (landmark_id, from_build));
CREATE TABLE redirect (tenant_id TEXT NOT NULL DEFAULT 'local',
  from_id TEXT PRIMARY KEY, to_id TEXT NOT NULL,
  reason TEXT NOT NULL CHECK (reason IN ('merged_into','split_into','retired','excised')), since_build TEXT NOT NULL,
  chooser_until TEXT);
CREATE TABLE build_record (tenant_id TEXT NOT NULL DEFAULT 'local',
  build_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL CHECK (kind IN ('just_in','printing','edition','slice','export','fallback_render')),
  ledger_seq INTEGER NOT NULL, session_seq INTEGER, index_seq INTEGER, inputs_hash TEXT NOT NULL, config_v TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('running','published','held','failed')), validator_summary TEXT,
  output_hash TEXT, started_at TEXT NOT NULL, finished_at TEXT);
CREATE INDEX build_kind_seq ON build_record(kind, status, ledger_seq);
CREATE TABLE build_input (tenant_id TEXT NOT NULL DEFAULT 'local',
  build_id TEXT NOT NULL REFERENCES build_record, obj_id TEXT NOT NULL, obj_v INTEGER, PRIMARY KEY (build_id, obj_id));
CREATE TABLE leaf_home (tenant_id TEXT NOT NULL DEFAULT 'local',
  item_id TEXT PRIMARY KEY, page_id TEXT NOT NULL, block TEXT NOT NULL, since_build TEXT NOT NULL);   -- B5: one home
CREATE TABLE sentence_cite (tenant_id TEXT NOT NULL DEFAULT 'local',
  sn_id TEXT NOT NULL, block_version_id TEXT NOT NULL, cite_id TEXT NOT NULL, cite_v INTEGER,
  cite_kind TEXT NOT NULL CHECK (cite_kind IN ('leaf','relation','span')), PRIMARY KEY (sn_id, block_version_id, cite_id));
CREATE INDEX sentence_cite_rev ON sentence_cite(cite_id);
CREATE TABLE dirty_page (tenant_id TEXT NOT NULL DEFAULT 'local',
  page_id TEXT PRIMARY KEY, since_seq INTEGER NOT NULL, reasons TEXT NOT NULL CHECK (json_valid(reasons)));

-- =====================================================================================
-- STORE: reader.db   (writer: C17; private; eval.db belongs to C22 and registers in ops.registered_store)
-- =====================================================================================
CREATE TABLE excision_run (tenant_id TEXT NOT NULL DEFAULT 'local', run_id TEXT PRIMARY KEY, tombstone_id TEXT,
  state TEXT NOT NULL CHECK (state IN ('in_progress','done')), started_at TEXT NOT NULL, ended_at TEXT);   -- progress only (MR-5)
CREATE TABLE reader_state (tenant_id TEXT NOT NULL DEFAULT 'local',
  reader_id TEXT NOT NULL, page_id TEXT NOT NULL, last_printing_seen TEXT, view_toggles TEXT,
  PRIMARY KEY (reader_id, page_id));
-- Per-page open counter (CONS-10): the owned input for landmark weight, the refutation fold and the dormant fold
-- (TEXTBOOK §7.2, §7.4, §7.6). Navigation only, never a measure of the reader. C17 passes C16 derived landmark_signals
-- only; this table never leaves reader.db, is switchable off and is covered by excision.
CREATE TABLE page_open (tenant_id TEXT NOT NULL DEFAULT 'local',
  page_id TEXT PRIMARY KEY, open_count INTEGER NOT NULL DEFAULT 0 CHECK (open_count >= 0), last_opened_at TEXT);

-- =====================================================================================
-- STORE: ops.db   (writer: C21)
-- =====================================================================================
CREATE TABLE excision_run (tenant_id TEXT NOT NULL DEFAULT 'local', run_id TEXT PRIMARY KEY, tombstone_id TEXT,
  state TEXT NOT NULL CHECK (state IN ('in_progress','done')), started_at TEXT NOT NULL, ended_at TEXT);   -- progress only (MR-5)
CREATE TABLE metric (tenant_id TEXT NOT NULL DEFAULT 'local',
  name TEXT NOT NULL, labels TEXT NOT NULL, value REAL NOT NULL, at TEXT NOT NULL, PRIMARY KEY (name, labels, at));
CREATE TABLE sentinel (tenant_id TEXT NOT NULL DEFAULT 'local',
  name TEXT PRIMARY KEY, state TEXT NOT NULL CHECK (state IN ('ok','alert','frozen')), since TEXT NOT NULL, detail TEXT);
CREATE TABLE invariant_violation (tenant_id TEXT NOT NULL DEFAULT 'local',
  check_id TEXT NOT NULL, object_id TEXT NOT NULL, sweep_id TEXT NOT NULL, detected_at TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('open','repaired','accepted_false_positive')), PRIMARY KEY (check_id, object_id, sweep_id));
CREATE TABLE checkpoint (tenant_id TEXT NOT NULL DEFAULT 'local',
  store TEXT NOT NULL, tbl TEXT NOT NULL, upto_seq INTEGER NOT NULL, row_count INTEGER NOT NULL, rolling_hash TEXT NOT NULL,
  at TEXT NOT NULL, PRIMARY KEY (store, tbl, upto_seq));
CREATE TABLE registered_store (tenant_id TEXT NOT NULL DEFAULT 'local',      -- every file excision must reach
  path_ref TEXT PRIMARY KEY, owner TEXT NOT NULL, holds_content INTEGER NOT NULL CHECK (holds_content IN (0,1)));

-- =====================================================================================
-- STORE: jobs.db   (writer: C11; the maintainer owns the semantics)
-- =====================================================================================
CREATE TABLE excision_run (tenant_id TEXT NOT NULL DEFAULT 'local', run_id TEXT PRIMARY KEY, tombstone_id TEXT,
  state TEXT NOT NULL CHECK (state IN ('in_progress','done')), started_at TEXT NOT NULL, ended_at TEXT);   -- progress only (MR-5)
CREATE TABLE job (tenant_id TEXT NOT NULL DEFAULT 'local',
  job_id TEXT PRIMARY KEY, type TEXT NOT NULL,
  lane TEXT NOT NULL CHECK (lane IN ('slow','nightly','weekly','repair','audit','eval')),
  idem_key TEXT NOT NULL UNIQUE,      -- sha256(type, schema_v, inputs_hash, prompt_hash, route_key): I14 (MR-3)
                                      -- one formula everywhere; a prompt fix or a new model route is a new job
  inputs_hash TEXT NOT NULL, input_ids TEXT NOT NULL CHECK (json_valid(input_ids)), schema_v INTEGER NOT NULL,
  role TEXT, model TEXT, prompt_hash TEXT, config_v TEXT NOT NULL, scope_lock TEXT,
  risk_tier TEXT CHECK (risk_tier IN ('low','medium','high')), priority INTEGER NOT NULL DEFAULT 5, watermark_seq INTEGER,
  state TEXT NOT NULL CHECK (state IN ('queued','leased','calling','awaiting_batch','validating','awaiting_verify','held',
    'applying','succeeded','succeeded_no_output','failed','failed_code','quarantined','cancelled')),   -- MR-3
  epoch INTEGER NOT NULL DEFAULT 0,                      -- fencing: +1 at every claim; Apply rejects a stale epoch (MR-3)
  lease_owner TEXT, leased_at TEXT, lease_expires_at TEXT,
  attempts INTEGER NOT NULL DEFAULT 0, max_attempts INTEGER NOT NULL DEFAULT 3,
  next_run_at TEXT, batch_id TEXT, parent_job TEXT, outcome_reason TEXT, created_at TEXT NOT NULL, finished_at TEXT,
  -- leased, calling, validating and applying hold a lease; awaiting_batch, awaiting_verify and held wait without one
  CHECK (state NOT IN ('leased','calling','validating','applying')
         OR (lease_owner IS NOT NULL AND leased_at IS NOT NULL AND lease_expires_at IS NOT NULL)));
CREATE INDEX job_ready ON job(state, next_run_at, priority);
CREATE INDEX job_batch ON job(batch_id);
-- Claim (MR-3; ROB smaller issue "maximum lease age"): a queued job, or any non-terminal job whose lease expired or
-- exceeded its maximum age, so a heartbeat cannot keep a hung worker alive. Every claim bumps the epoch.
--   UPDATE job SET state = 'leased', epoch = epoch + 1, lease_owner = :worker, leased_at = :now,
--          lease_expires_at = :now_plus_ttl
--   WHERE job_id = :id AND ((state = 'queued' AND (next_run_at IS NULL OR next_run_at <= :now))
--     OR (state NOT IN ('succeeded','succeeded_no_output','failed','failed_code','quarantined','cancelled')
--         AND (lease_expires_at < :now OR leased_at < :now_minus_max_lease_age)));
-- A reclaimed 'applying' job is first reconciled with ledger.db applied_job by job_id. Postgres: SKIP LOCKED.
CREATE TABLE model_call (tenant_id TEXT NOT NULL DEFAULT 'local',
  call_id TEXT PRIMARY KEY, job_id TEXT NOT NULL REFERENCES job, role TEXT NOT NULL, provider TEXT NOT NULL,
  model_returned TEXT NOT NULL, model_family TEXT NOT NULL, prompt_hash TEXT NOT NULL, input_fingerprint TEXT NOT NULL,
  input_ids TEXT NOT NULL, egress_policy_v TEXT NOT NULL, redaction_report TEXT,
  raw_output TEXT, raw_output_blob TEXT, parsed_output TEXT, tokens_in INTEGER, tokens_out INTEGER, cost_microusd INTEGER,
  latency_ms INTEGER, batch_ref TEXT, fault_injected TEXT, started_at TEXT NOT NULL, ended_at TEXT,
  excised INTEGER NOT NULL DEFAULT 0 CHECK (excised IN (0,1)));
CREATE INDEX model_call_job ON model_call(job_id);
CREATE TABLE proposal (tenant_id TEXT NOT NULL DEFAULT 'local',
  proposal_id TEXT PRIMARY KEY, job_id TEXT NOT NULL REFERENCES job, call_id TEXT REFERENCES model_call,
  epoch INTEGER NOT NULL,                                  -- the job's epoch at claim; Apply rejects a stale one (MR-3)
  kind TEXT NOT NULL, body TEXT NOT NULL CHECK (json_valid(body)),
  state TEXT NOT NULL CHECK (state IN ('pending','awaiting_verify','held','applied','rejected','quarantined','released',
    'discarded')),                                         -- awaiting_verify, held: MR-3, MR-7
  applied_txn TEXT, created_at TEXT NOT NULL);
CREATE INDEX proposal_job ON proposal(job_id, state);
CREATE TABLE validator_result (tenant_id TEXT NOT NULL DEFAULT 'local',
  proposal_id TEXT NOT NULL REFERENCES proposal, check_id TEXT NOT NULL, passed INTEGER NOT NULL CHECK (passed IN (0,1)),
  detail TEXT, at TEXT NOT NULL, PRIMARY KEY (proposal_id, check_id, at));
-- Quarantine (MR-7): one record per held op; a whole-job hold (blast-cap breach) writes one row per op.
-- speaker_family: the speaker family of the op's primary evidence, for the per-family sentinels (#2, #3).
CREATE TABLE quarantine (tenant_id TEXT NOT NULL DEFAULT 'local',
  proposal_id TEXT NOT NULL REFERENCES proposal, op_index INTEGER NOT NULL, reason TEXT NOT NULL,
  tier TEXT NOT NULL CHECK (tier IN ('low','medium','high')), speaker_family TEXT NOT NULL,
  entered_at TEXT NOT NULL, deadline TEXT NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts <= 4),             -- 1 re-verification + 3 re-extractions
  exit_route TEXT CHECK (exit_route IN ('reverify','reextract','rerun_after_fix','final_release','final_discard')),
  exited_at TEXT, PRIMARY KEY (proposal_id, op_index));
-- Discards are recorded, sampled for audit and fed to the sentinels per speaker family (MR-7).
CREATE TABLE discard (tenant_id TEXT NOT NULL DEFAULT 'local',
  proposal_id TEXT NOT NULL, op_index INTEGER NOT NULL, reason TEXT NOT NULL,
  tier TEXT NOT NULL CHECK (tier IN ('low','medium','high')), speaker_family TEXT NOT NULL,
  discarded_at TEXT NOT NULL, PRIMARY KEY (proposal_id, op_index),
  FOREIGN KEY (proposal_id, op_index) REFERENCES quarantine (proposal_id, op_index));
CREATE TABLE error_budget (tenant_id TEXT NOT NULL DEFAULT 'local',
  job_type TEXT NOT NULL, block_type TEXT NOT NULL DEFAULT '-', window_start TEXT NOT NULL,
  audited INTEGER NOT NULL, errors INTEGER NOT NULL, state TEXT NOT NULL CHECK (state IN ('ok','frozen')),
  frozen_at TEXT, exit_condition TEXT, PRIMARY KEY (job_type, block_type, window_start));
CREATE TABLE scope_lock (tenant_id TEXT NOT NULL DEFAULT 'local',
  scope TEXT PRIMARY KEY, holder_job TEXT NOT NULL, expires_at TEXT NOT NULL);
CREATE TABLE global_lock (tenant_id TEXT NOT NULL DEFAULT 'local',
  name TEXT PRIMARY KEY CHECK (name IN ('excision','migration')), holder TEXT NOT NULL, since TEXT NOT NULL,
  lease_expires_at TEXT NOT NULL, epoch INTEGER NOT NULL);      -- a lock lease with a fencing epoch (MR-3, MR-5)

-- =====================================================================================
-- ## Consistency fixes (2026-10-08)
-- =====================================================================================
-- Not yet re-run after the 2026-10-08 consistency and review edits; re-running every store and CHECK is a Stage 0a task.
-- X07  session_op: SEED and ROUTE removed; seeds are ADD with actor 'seeding' and actor_ref = continuity_params version
--      (CHECK). session_item: by_ is the original speaker (user|ai; 'pack' removed); seeded_from JSON
--      {item: id@version, artifact_hash, delivery_receipt}; seed_kind, delivery (delivered|unknown|guard_only), on_route;
--      a seed needs all four, a non-seed needs a span; authority stays confirmed|provisional|reported. Routing = routing_record.
-- X09  session.db pending_resume: one registry, C10 writes, C23 reads; 24 h expiry; adopted via explicit_handle or
--      c23_route with p >= 0.7 (CHECK); one open entry per parent; reversible.
-- X10  Event-type note: the core-data-model.md §2.2 catalog is the authority; REPARENT -> concept.reparented,
--      FIDELITY_UPGRADE -> attribution.added with recon_id, rollback compensations named. concept_broader gains updated_seq.
-- X11  scope.kind: personal|project|work|unclassified|session|eval ('private' removed; it is a tier). 'held' is a flag:
--      scope.held (+ held_seq) and session.held; no egress, no packs, no Book.
-- X14  Join methods process_lineage, widget_origin (source_join, session_conv_key); account_source ax_label (envelope,
--      session); turn tag 'NS-XXXXXX.<n>'; connector/1.1 fields, explicit_request included, ride envelope.payload_meta.
-- X17  Echo rule note on attribution: receipt from any same-family session within 90 days, no fresh grounding;
--      context_receipt.speaker_model_family and index make the check a lookup.
-- X18  intake.db origin_confirmation (observation.origin_confirmed), append-only; transcript or degraded template/
--      continuation-hash fallback; read by the C12 I5/I22 gate for hook-channel spans (note at the ledger triggers).
-- X25  'ai_cited_unchecked' renamed 'cited_unchecked' (item, verification); ver_tier order written on best_rank.
-- X29  relation.basis (goal_stack|j5|answers|user|reexplained), required for advances_goal; index.db goal_card (C08,
--      reads session.db) and fts_map kind 'goal_card'.

-- =====================================================================================
-- ## Review fixes (2026-10-08)
-- =====================================================================================
-- The adversarial review's DDL changes. Full record: ../REVIEW.md (findings in §5, smaller issues in §10).
-- Not yet re-run (see above).
-- MR-3    Pragmas: synchronous=FULL on jobs.db as well as intake and ledger. job: epoch; states queued, leased,
--         calling, awaiting_batch, validating, awaiting_verify, held, applying, succeeded, succeeded_no_output, failed,
--         failed_code, quarantined, cancelled ('waiting_batch' renamed); leased_at, and a lease CHECK on the
--         lease-holding states; one idem_key formula, sha256(type, schema_v, inputs_hash, prompt_hash, route_key);
--         claim reclaims any non-terminal job whose lease expired or exceeded its maximum age. proposal: epoch; states
--         awaiting_verify and held. global_lock: lease_expires_at, epoch. ledger.db applied_job (job_id, proposal_id,
--         output_hash, applied_seq), append-only, with applied_job_once refusing a second proposal for the same job.
-- MR-4    origin_confirmation: outcome confirmed_degraded. The template/continuation-hash method records only
--         confirmed_degraded or not_confirmed, never confirmed (CHECK). Comment and the X18 gate note updated.
-- MR-5    Excision bypass: ns_excision_active(), a connection-scoped function, replaces the persistent
--         excision_run.active flag in every trigger and fails closed where unregistered (header). excision_run.state
--         records progress only. tombstone.state (in_progress, done), written first so the saga can resume.
-- MR-7    quarantine: key (proposal_id, op_index); tier and speaker_family; attempts <= 4 (1 re-verification + 3
--         re-extractions). New discard record with reason, tier and speaker_family.
-- MR-9    relation_endpoints: from_id and to_id must exist as an item, a relation or an episode.
-- CONS-9  session.persist_policy full|none|on_write, derived from capture_mode. New recorded_turn table.
--         session_item_persist replaces path_b_no_items: full, or on_write for a recorded turn; never none.
-- CONS-10 reader.db page_open: open_count and last_opened_at per page.
-- CONS    Smaller issues: agenda.kind drops 'suggestion' (an item kind tag); relation.status keeps 'retracted'
--         (SPINE §5.2 lists it).
-- ROB     Smaller issues: *_no_del for apply_txn, session_op, correction, active_constraint (allowed once its
--         correction is lifted), attribution, tombstone (never deleted, even by excision) and reconciliation_point;
--         message_call_slot, a unique index on (source_id, branch_path, call_index, speaker) beside message_slot;
--         maximum lease age in the claim (MR-3).
-- Task (c) Header and footer say the DDL is not yet re-run; the re-run is a Stage 0a task.
-- FEAS-1  observation: obs_kind 'hash_only' removed, and the observation.persist_policy column with both of its CHECKs.
--         Path B (and unrecorded turns under A or C2) writes no observation; only content-free operational logs (time,
--         tool, status, latency) are kept, outside intake.db content tables ([CX] §2.5). session.persist_policy stays.
-- BOOK-2  reported_point: body (<= 1,500 characters, only on explanation or example points, by CHECK) and reply_scope
--         ('prev' | 'this'; 'this' marks closing-call points, this_reply_points, attached to the same reply; [CX] §2.3).

-- =====================================================================================
-- ## Final-gate fixes (2026-10-08)
-- =====================================================================================
-- FEAS-1 and BOOK-2 had not reached this DDL. Both landed at the final gate (rows above). Checked on SQLite: the
-- intake.db section parses; a 'hash_only' observation and a body on a non-explanation point are refused.
-- The full re-run of every store is still a Stage 0a task.
