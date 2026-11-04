-- working.db: working memory, the live record of each piece of work in progress (MEMORY-ARCHITECTURE §2.9).
-- Version 1. Writer: the live writer (code, plus a small model that notes decisions in your turns).
-- Canonical for live state, provisional, and never a source for memory (§2.9). Rows change in place.
-- message_id values point into history.db. Every table carries tenant_id (§3.3), and it leads every key: primary
-- keys, unique constraints and foreign keys are (tenant_id, id).
--
-- Triggers this file defines (the gate's REQUIRED_TRIGGERS are checked against this list): none. Working memory is
-- provisional and never a source for memory, so its rows change in place.

CREATE TABLE work_thread (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  title TEXT NOT NULL,
  project TEXT,
  scope TEXT NOT NULL CHECK (scope = 'personal' OR scope GLOB 'project:?*' OR scope GLOB 'work:?*'),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'closed')),
  goal_text TEXT,                          -- your words
  goal_message_id TEXT,
  goal_basis TEXT CHECK (goal_basis IN ('stated', 'reused')),
  opened_at TEXT NOT NULL,
  last_active TEXT NOT NULL,
  CHECK ((goal_text IS NULL) = (goal_basis IS NULL)),
  PRIMARY KEY (tenant_id, id)
);
CREATE INDEX work_thread_project ON work_thread (project, status);

CREATE TABLE session (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  app TEXT,
  project TEXT,
  thread_id TEXT,
  context_used INTEGER CHECK (context_used IS NULL OR context_used >= 0),   -- token count from the app's transcript
  started_at TEXT NOT NULL,
  last_active TEXT NOT NULL,
  PRIMARY KEY (tenant_id, id),
  FOREIGN KEY (tenant_id, thread_id) REFERENCES work_thread (tenant_id, id)
);
CREATE INDEX session_thread ON session (thread_id);

CREATE TABLE live_decision (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  thread_id TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('decided', 'ruled_out', 'constraint')),
  line TEXT NOT NULL,
  your_quote TEXT NOT NULL,                -- only from your own turns
  message_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'live' CHECK (status IN ('live', 'in_memory', 'dropped')),
  created_at TEXT NOT NULL,
  PRIMARY KEY (tenant_id, id),
  FOREIGN KEY (tenant_id, thread_id) REFERENCES work_thread (tenant_id, id)
);
CREATE INDEX live_decision_thread ON live_decision (thread_id, status);

-- A version of the work: a snapshot on a hidden git ref, or a rendered image. `best` is your pick, or your last
-- approval in your own words; at most one version per thread is best.
CREATE TABLE version (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  thread_id TEXT NOT NULL,
  artifact TEXT NOT NULL,                  -- hidden git ref, or blob sha256 of a render
  artifact_kind TEXT NOT NULL DEFAULT 'git_ref' CHECK (artifact_kind IN ('git_ref', 'render', 'file')),
  parent_id TEXT,
  made_at_turn INTEGER CHECK (made_at_turn IS NULL OR made_at_turn >= 0),
  best INTEGER NOT NULL DEFAULT 0 CHECK (best IN (0, 1)),
  created_at TEXT NOT NULL,
  PRIMARY KEY (tenant_id, id),
  FOREIGN KEY (tenant_id, thread_id) REFERENCES work_thread (tenant_id, id),
  FOREIGN KEY (tenant_id, parent_id) REFERENCES version (tenant_id, id)
);
CREATE INDEX version_thread ON version (thread_id, created_at);
CREATE UNIQUE INDEX version_one_best ON version (tenant_id, thread_id) WHERE best = 1;

CREATE TABLE version_feedback (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  version_id TEXT NOT NULL,
  your_quote TEXT NOT NULL,
  message_id TEXT NOT NULL,
  at TEXT NOT NULL,
  PRIMARY KEY (tenant_id, id),
  FOREIGN KEY (tenant_id, version_id) REFERENCES version (tenant_id, id)
);
CREATE INDEX version_feedback_version ON version_feedback (version_id);

CREATE TABLE side_topic (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  thread_id TEXT NOT NULL,
  line TEXT NOT NULL,
  opened_at_message TEXT,
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'split_off', 'closed')),
  PRIMARY KEY (tenant_id, id),
  FOREIGN KEY (tenant_id, thread_id) REFERENCES work_thread (tenant_id, id)
);
CREATE INDEX side_topic_thread ON side_topic (thread_id, status);

-- Everything Northstar gave an AI (§2.9). Drives the echo guard, the re-check on use and "used in this chat".
CREATE TABLE receipt (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  at TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('start_note', 'facts', 'refill', 'focus_note', 'recall')),
  items TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(items) AND json_type(items) = 'array'),   -- item@version
  text_hash TEXT NOT NULL,
  fingerprints TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(fingerprints) AND json_type(fingerprints) = 'array'),   -- 8-word fingerprints
  PRIMARY KEY (tenant_id, id),
  FOREIGN KEY (tenant_id, session_id) REFERENCES session (tenant_id, id)
);
CREATE INDEX receipt_session ON receipt (session_id, at);
