-- history.db: chat history, word for word, never edited (MEMORY-ARCHITECTURE §2.2, §3.4). Writer: capture.
-- Version 1. Every table carries tenant_id (§3.3), and it leads every key: primary keys, unique constraints and
-- foreign keys are (tenant_id, id).
-- Append-only (I6): UPDATE and DELETE on message, work_event and blob are refused unless purge_authorization names
-- the row (§3.4). Speaker, origin and text can never change, with or without a purge (I3, I20). A source never
-- changes its kind or scope, and its sensitivity may only rise (normal, sensitive, private); it is deleted only
-- under a purge authorization.
--
-- Triggers this file defines (the gate's REQUIRED_TRIGGERS are checked against this list):
--   purge_authorization_no_update, purge_authorization_no_delete
--   source_identity_frozen, source_sensitivity_only_rises, source_no_delete
--   message_identity_frozen, message_no_update, message_no_delete
--   work_event_identity_frozen, work_event_no_update, work_event_no_delete
--   blob_no_update, blob_no_delete
--   reconciliation_no_update, reconciliation_no_delete

CREATE TABLE source (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('chat', 'work', 'document', 'northstar_output')),
  app TEXT,
  account TEXT,
  project TEXT,                      -- the repository or folder
  title TEXT,
  started_at TEXT,
  scope TEXT NOT NULL CHECK (scope = 'personal' OR scope GLOB 'project:?*' OR scope GLOB 'work:?*' OR scope GLOB 'session:?*'),
  sensitivity TEXT NOT NULL DEFAULT 'normal' CHECK (sensitivity IN ('normal', 'sensitive', 'private')),
  meta TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(meta)),
  created_at TEXT NOT NULL,
  PRIMARY KEY (tenant_id, id)
);

CREATE TABLE blob (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  sha256 TEXT NOT NULL CHECK (length(sha256) = 64),
  size INTEGER NOT NULL CHECK (size >= 0),
  media_type TEXT,
  created_at TEXT NOT NULL,
  PRIMARY KEY (tenant_id, sha256)
);

CREATE TABLE message (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,   -- the capture watermark; never reused
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,                        -- e.g. "<source_id>:<ordinal>"
  source_id TEXT NOT NULL,
  branch TEXT NOT NULL DEFAULT '0',
  ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
  speaker TEXT NOT NULL CHECK (speaker IN ('user', 'assistant', 'tool', 'northstar', 'system')),
  agent TEXT,
  model_family TEXT,
  origin TEXT NOT NULL CHECK (origin IN ('typed', 'pasted', 'assistant_output', 'tool_output', 'model_reported', 'northstar_injected')),
  occurred_at TEXT,
  text TEXT NOT NULL,                      -- word for word; secrets replaced before writing
  content_hash TEXT NOT NULL,
  fidelity TEXT NOT NULL DEFAULT 'verbatim' CHECK (fidelity IN ('verbatim', 'model_reported', 'reconciled')),
  meta TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(meta)),   -- never an input to ranking (I23)
  recorded_at TEXT NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, source_id, branch, ordinal, speaker),
  FOREIGN KEY (tenant_id, source_id) REFERENCES source (tenant_id, id)
);
CREATE INDEX message_source ON message (source_id, branch, ordinal);
CREATE INDEX message_hash ON message (content_hash);
CREATE INDEX message_time ON message (occurred_at);

CREATE TABLE work_event (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  source_id TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('commit', 'file_version', 'render', 'diagram', 'decision_record')),
  ref TEXT NOT NULL,                       -- commit SHA, file hash and path, or permalink
  evidence TEXT NOT NULL CHECK (evidence IN ('strong', 'medium', 'weak')),
  snapshot_sha256 TEXT,
  occurred_at TEXT,
  meta TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(meta)),
  recorded_at TEXT NOT NULL,
  UNIQUE (tenant_id, id),
  FOREIGN KEY (tenant_id, source_id) REFERENCES source (tenant_id, id),
  FOREIGN KEY (tenant_id, snapshot_sha256) REFERENCES blob (tenant_id, sha256)
);
CREATE INDEX work_event_source ON work_event (source_id);

-- Message reconciliation (§2.2): every outcome of matching a model-reported turn to word-for-word text is recorded.
-- Append-only. The reported message is never edited: the reconciled text arrives as its own message.
CREATE TABLE reconciliation (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  reported_message_id TEXT NOT NULL,
  verbatim_message_id TEXT,
  method TEXT NOT NULL CHECK (method IN ('hash', 'tag', 'fuzzy', 'none')),
  score REAL,
  outcome TEXT NOT NULL CHECK (outcome IN ('matched', 'reported_only', 'could_not_confirm')),
  recorded_at TEXT NOT NULL,
  CHECK (outcome <> 'matched' OR verbatim_message_id IS NOT NULL),
  PRIMARY KEY (tenant_id, id),
  FOREIGN KEY (tenant_id, reported_message_id) REFERENCES message (tenant_id, id),
  FOREIGN KEY (tenant_id, verbatim_message_id) REFERENCES message (tenant_id, id)
);

-- What a purge may remove (§3.4). Rows are written by the purge saga before it deletes anything, and kept.
CREATE TABLE purge_authorization (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  purge_id TEXT NOT NULL,
  target_table TEXT NOT NULL CHECK (target_table IN ('source', 'message', 'work_event', 'blob', 'reconciliation')),
  target_id TEXT NOT NULL,                 -- the row's id (blob: its sha256)
  authorized_at TEXT NOT NULL,
  PRIMARY KEY (tenant_id, purge_id, target_table, target_id)
);
CREATE INDEX purge_authorization_target ON purge_authorization (tenant_id, target_table, target_id);
CREATE TRIGGER purge_authorization_no_update BEFORE UPDATE ON purge_authorization
BEGIN SELECT RAISE(ABORT, 'I6 append-only: purge_authorization'); END;
CREATE TRIGGER purge_authorization_no_delete BEFORE DELETE ON purge_authorization
BEGIN SELECT RAISE(ABORT, 'I6 append-only: purge_authorization'); END;

-- A source keeps its kind and scope for good (the scope decides who may see its text). Its sensitivity may be raised
-- by a later call, never lowered.
CREATE TRIGGER source_identity_frozen BEFORE UPDATE ON source
WHEN NEW.tenant_id IS NOT OLD.tenant_id OR NEW.id IS NOT OLD.id OR NEW.kind IS NOT OLD.kind OR NEW.scope IS NOT OLD.scope
BEGIN SELECT RAISE(ABORT, 'I6: a source never changes its kind or scope'); END;
CREATE TRIGGER source_sensitivity_only_rises BEFORE UPDATE OF sensitivity ON source
WHEN (CASE NEW.sensitivity WHEN 'normal' THEN 0 WHEN 'sensitive' THEN 1 ELSE 2 END)
   < (CASE OLD.sensitivity WHEN 'normal' THEN 0 WHEN 'sensitive' THEN 1 ELSE 2 END)
BEGIN SELECT RAISE(ABORT, 'a source''s sensitivity may only rise'); END;
CREATE TRIGGER source_no_delete BEFORE DELETE ON source
WHEN NOT EXISTS (SELECT 1 FROM purge_authorization WHERE target_table = 'source' AND target_id = OLD.id AND tenant_id = OLD.tenant_id)
BEGIN SELECT RAISE(ABORT, 'I6 append-only: source'); END;

CREATE TRIGGER message_identity_frozen BEFORE UPDATE OF tenant_id, id, source_id, speaker, agent, model_family, origin, text, content_hash ON message
BEGIN SELECT RAISE(ABORT, 'I3/I20: speaker, origin and text never change'); END;
CREATE TRIGGER message_no_update BEFORE UPDATE ON message
WHEN NOT EXISTS (SELECT 1 FROM purge_authorization WHERE target_table = 'message' AND target_id = OLD.id AND tenant_id = OLD.tenant_id)
BEGIN SELECT RAISE(ABORT, 'I6 append-only: message'); END;
CREATE TRIGGER message_no_delete BEFORE DELETE ON message
WHEN NOT EXISTS (SELECT 1 FROM purge_authorization WHERE target_table = 'message' AND target_id = OLD.id AND tenant_id = OLD.tenant_id)
BEGIN SELECT RAISE(ABORT, 'I6 append-only: message'); END;

CREATE TRIGGER work_event_identity_frozen BEFORE UPDATE OF tenant_id, id, source_id, kind, ref, evidence ON work_event
BEGIN SELECT RAISE(ABORT, 'I6: a work event never changes what it records'); END;
CREATE TRIGGER work_event_no_update BEFORE UPDATE ON work_event
WHEN NOT EXISTS (SELECT 1 FROM purge_authorization WHERE target_table = 'work_event' AND target_id = OLD.id AND tenant_id = OLD.tenant_id)
BEGIN SELECT RAISE(ABORT, 'I6 append-only: work_event'); END;
CREATE TRIGGER work_event_no_delete BEFORE DELETE ON work_event
WHEN NOT EXISTS (SELECT 1 FROM purge_authorization WHERE target_table = 'work_event' AND target_id = OLD.id AND tenant_id = OLD.tenant_id)
BEGIN SELECT RAISE(ABORT, 'I6 append-only: work_event'); END;

CREATE TRIGGER blob_no_update BEFORE UPDATE ON blob
BEGIN SELECT RAISE(ABORT, 'I6 append-only: blob'); END;
CREATE TRIGGER blob_no_delete BEFORE DELETE ON blob
WHEN NOT EXISTS (SELECT 1 FROM purge_authorization WHERE target_table = 'blob' AND target_id = OLD.sha256 AND tenant_id = OLD.tenant_id)
BEGIN SELECT RAISE(ABORT, 'I6 append-only: blob'); END;

CREATE TRIGGER reconciliation_no_update BEFORE UPDATE ON reconciliation
BEGIN SELECT RAISE(ABORT, 'I6 append-only: reconciliation'); END;
CREATE TRIGGER reconciliation_no_delete BEFORE DELETE ON reconciliation
WHEN NOT EXISTS (SELECT 1 FROM purge_authorization WHERE target_table = 'reconciliation' AND target_id = OLD.id AND tenant_id = OLD.tenant_id)
BEGIN SELECT RAISE(ABORT, 'I6 append-only: reconciliation'); END;
