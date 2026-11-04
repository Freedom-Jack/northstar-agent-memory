-- runs.db: maintenance run records (MEMORY-ARCHITECTURE §2.12, §5.3, §5.9, §5.12). Operational; canonical for restore.
-- Version 1. Writer: maintenance. Every table carries tenant_id (§3.3), and it leads every key: primary keys, unique
-- constraints and foreign keys are (tenant_id, id).
-- Model calls keep input ids, never the assembled text (§2.12); outputs are recorded before they are read and never
-- regenerated (§5.12). The change log is never read back as an input (I7).
-- The gate takes verdicts from here and nowhere else (§5.9), so what it relies on is final once written: a model call
-- and a verdict never change or go; an applied proposal never changes or goes; a change_log row never goes and its
-- text never changes (only `undone_at` is set, once, when the change is undone).
--
-- Triggers this file defines (the gate's REQUIRED_TRIGGERS are checked against this list):
--   model_call_no_update, model_call_no_delete
--   proposal_applied_final_update, proposal_applied_final_delete
--   verdict_no_update, verdict_no_delete
--   change_log_frozen, change_log_undone_once, change_log_no_delete

CREATE TABLE run (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  trigger TEXT NOT NULL CHECK (trigger IN ('idle', 'nightly', 'weekly', 'manual')),
  watermark_from INTEGER NOT NULL DEFAULT 0,   -- history message seq
  watermark_to INTEGER,
  budget_used TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(budget_used)),
  state TEXT NOT NULL DEFAULT 'queued' CHECK (state IN ('queued', 'running', 'held', 'applied', 'failed', 'cancelled', 'undone')),
  safety_copy TEXT,                        -- path of the working copy of memory, index and overview (§5.10)
  result TEXT CHECK (result IS NULL OR json_valid(result)),
  started_at TEXT NOT NULL,
  ended_at TEXT,
  PRIMARY KEY (tenant_id, id)
);
CREATE INDEX run_state ON run (state);

CREATE TABLE job (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  stage TEXT NOT NULL CHECK (stage IN ('trigger', 'replay', 'extract', 'integrate', 'refresh', 'check', 'weekly', 'rebuild', 'log')),
  idempotency_key TEXT NOT NULL,
  payload TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(payload)),
  lease_owner TEXT,
  lease_until TEXT,
  attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
  state TEXT NOT NULL DEFAULT 'queued' CHECK (state IN ('queued', 'leased', 'running', 'done', 'failed', 'quarantined', 'cancelled')),
  error TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (tenant_id, id),
  UNIQUE (tenant_id, idempotency_key),
  FOREIGN KEY (tenant_id, run_id) REFERENCES run (tenant_id, id)
);
CREATE INDEX job_queue ON job (state, stage, lease_until);
CREATE INDEX job_run ON job (run_id);

CREATE TABLE model_call (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  run_id TEXT,
  job_id TEXT,
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  family TEXT NOT NULL,
  prompt_hash TEXT NOT NULL,
  input_ids TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(input_ids) AND json_type(input_ids) = 'array'),   -- never the assembled text
  raw_output TEXT,                         -- recorded before it is read
  tokens_in INTEGER CHECK (tokens_in IS NULL OR tokens_in >= 0),
  tokens_out INTEGER CHECK (tokens_out IS NULL OR tokens_out >= 0),
  cost REAL CHECK (cost IS NULL OR cost >= 0),
  status TEXT NOT NULL DEFAULT 'ok' CHECK (status IN ('ok', 'error', 'timeout')),
  called_at TEXT NOT NULL,
  PRIMARY KEY (tenant_id, id),
  FOREIGN KEY (tenant_id, run_id) REFERENCES run (tenant_id, id),
  FOREIGN KEY (tenant_id, job_id) REFERENCES job (tenant_id, id)
);
CREATE INDEX model_call_run ON model_call (run_id);
CREATE INDEX model_call_hash ON model_call (prompt_hash);
CREATE TRIGGER model_call_no_update BEFORE UPDATE ON model_call
BEGIN SELECT RAISE(ABORT, 'I6 append-only: model_call (an output is recorded once and never regenerated, §5.12)'); END;
CREATE TRIGGER model_call_no_delete BEFORE DELETE ON model_call
BEGIN SELECT RAISE(ABORT, 'I6 append-only: model_call'); END;

CREATE TABLE proposal (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  job_id TEXT,
  ops TEXT NOT NULL CHECK (json_valid(ops) AND json_type(ops) = 'array'),            -- event envelope drafts
  evidence TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(evidence) AND json_type(evidence) = 'array'),   -- quotes with message ids and spans
  abstentions TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(abstentions) AND json_type(abstentions) = 'array'),
  inputs TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(inputs) AND json_type(inputs) = 'array'),         -- object@version
  risk_tier TEXT NOT NULL CHECK (risk_tier IN ('low', 'medium', 'high')),
  state TEXT NOT NULL DEFAULT 'pending' CHECK (state IN ('pending', 'applied', 'rejected', 'quarantined', 'requeued')),
  created_at TEXT NOT NULL,
  PRIMARY KEY (tenant_id, id),
  FOREIGN KEY (tenant_id, run_id) REFERENCES run (tenant_id, id),
  FOREIGN KEY (tenant_id, job_id) REFERENCES job (tenant_id, id)
);
CREATE INDEX proposal_run ON proposal (run_id, state);
-- An applied proposal is what the event log was made from (I14): it never changes and never goes.
CREATE TRIGGER proposal_applied_final_update BEFORE UPDATE ON proposal
WHEN OLD.state = 'applied'
BEGIN SELECT RAISE(ABORT, 'I6: an applied proposal is final'); END;
CREATE TRIGGER proposal_applied_final_delete BEFORE DELETE ON proposal
WHEN OLD.state = 'applied'
BEGIN SELECT RAISE(ABORT, 'I6: an applied proposal is final'); END;

CREATE TABLE verdict (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  proposal_id TEXT NOT NULL,
  checker_family TEXT NOT NULL,
  rules TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(rules) AND json_type(rules) = 'array'),   -- meaning both ways, attribution, scope, hedge
  outcome TEXT NOT NULL CHECK (outcome IN ('pass', 'fail')),
  independent INTEGER NOT NULL CHECK (independent IN (0, 1)),   -- 0: labelled "not independent"
  model_call_id TEXT,
  notes TEXT NOT NULL DEFAULT '',
  at TEXT NOT NULL,
  PRIMARY KEY (tenant_id, id),
  FOREIGN KEY (tenant_id, proposal_id) REFERENCES proposal (tenant_id, id),
  FOREIGN KEY (tenant_id, model_call_id) REFERENCES model_call (tenant_id, id)
);
CREATE INDEX verdict_proposal ON verdict (proposal_id);
CREATE TRIGGER verdict_no_update BEFORE UPDATE ON verdict
BEGIN SELECT RAISE(ABORT, 'I6 append-only: verdict'); END;
CREATE TRIGGER verdict_no_delete BEFORE DELETE ON verdict
BEGIN SELECT RAISE(ABORT, 'I6 append-only: verdict'); END;

-- A failing proposal waits aside with automatic exits; nothing from it applies and nothing waits on you (§5.9).
CREATE TABLE quarantine (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  target_kind TEXT NOT NULL CHECK (target_kind IN ('proposal', 'item', 'link')),
  target_id TEXT NOT NULL,
  reason TEXT NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 1 CHECK (attempts BETWEEN 1 AND 3),   -- at most 3
  deadline TEXT NOT NULL,                  -- 3 attempts in 7 days (start)
  state TEXT NOT NULL DEFAULT 'open' CHECK (state IN ('open', 'exited')),
  exit TEXT CHECK (exit IN ('fresh_call', 're_extracted', 'discarded', 'applied')),
  created_at TEXT NOT NULL,
  CHECK ((state = 'exited') = (exit IS NOT NULL)),
  PRIMARY KEY (tenant_id, id)
);
CREATE INDEX quarantine_open ON quarantine (state, deadline);

-- Error budget per change type: audited error rate, and whether the type is frozen (§5.9).
CREATE TABLE budget (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  change_type TEXT NOT NULL,
  audited_n INTEGER NOT NULL DEFAULT 0 CHECK (audited_n >= 0),
  audited_errors INTEGER NOT NULL DEFAULT 0 CHECK (audited_errors >= 0 AND audited_errors <= audited_n),
  audited_error_rate REAL NOT NULL DEFAULT 0 CHECK (audited_error_rate >= 0 AND audited_error_rate <= 1),
  frozen INTEGER NOT NULL DEFAULT 0 CHECK (frozen IN (0, 1)),
  frozen_at TEXT,
  updated_at TEXT NOT NULL,
  CHECK (frozen = 1 OR frozen_at IS NULL),
  PRIMARY KEY (tenant_id, change_type)
);

-- One plain line per change, with its undo (§5.10). For you and for audits; never an input (I7).
CREATE TABLE change_log (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  at TEXT NOT NULL,
  change_type TEXT NOT NULL,
  line TEXT NOT NULL,                      -- what changed and why
  event_ids TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(event_ids) AND json_type(event_ids) = 'array'),
  undo_handle TEXT,                        -- what to compensate; NULL when nothing can be undone
  undone_at TEXT,
  PRIMARY KEY (tenant_id, id),
  FOREIGN KEY (tenant_id, run_id) REFERENCES run (tenant_id, id)
);
CREATE INDEX change_log_run ON change_log (run_id);
-- A change_log row is final: it is never deleted, its text never changes, and `undone_at` is set once when the change
-- is undone (never cleared or moved).
CREATE TRIGGER change_log_frozen BEFORE UPDATE ON change_log
WHEN NEW.tenant_id IS NOT OLD.tenant_id OR NEW.id IS NOT OLD.id OR NEW.run_id IS NOT OLD.run_id OR NEW.at IS NOT OLD.at
  OR NEW.change_type IS NOT OLD.change_type OR NEW.line IS NOT OLD.line OR NEW.event_ids IS NOT OLD.event_ids
  OR NEW.undo_handle IS NOT OLD.undo_handle
BEGIN SELECT RAISE(ABORT, 'I6: a change_log row is final'); END;
CREATE TRIGGER change_log_undone_once BEFORE UPDATE OF undone_at ON change_log
WHEN OLD.undone_at IS NOT NULL AND NEW.undone_at IS NOT OLD.undone_at
BEGIN SELECT RAISE(ABORT, 'I6: a change_log row is undone once'); END;
CREATE TRIGGER change_log_no_delete BEFORE DELETE ON change_log
BEGIN SELECT RAISE(ABORT, 'I6: a change_log row is final'); END;
