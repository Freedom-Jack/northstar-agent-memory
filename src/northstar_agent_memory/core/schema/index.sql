-- index.db: the AI index (MEMORY-ARCHITECTURE §2.10, §4). Derived: rebuilt by the maintenance rebuild, not backed up,
-- except gate_bar and use, which are state that use moves (see the note on those tables).
-- Version 1. Every table carries tenant_id (§3.3), and it leads every key: primary keys and unique constraints are
-- (tenant_id, id); FTS5 tables carry it as an unindexed column.
--
-- Triggers this file defines (the gate's REQUIRED_TRIGGERS are checked against this list): none. The index is derived
-- and rebuilt; `gate_bar` and `use` are state that use moves, and change in place.

-- One plain dated line per item (§2.10). Pushed lines carry no IDs; recall results carry short IDs.
CREATE TABLE item_line (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  item_id TEXT NOT NULL,
  version INTEGER NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('decision', 'ruled_out', 'result', 'conclusion', 'definition', 'plan',
    'principle', 'approach', 'position', 'goal', 'question')),
  line_text TEXT NOT NULL,                 -- the rendered line: dated, scoped, attributed, third person
  class TEXT NOT NULL CHECK (class IN ('fact', 'view')),
  scope TEXT NOT NULL CHECK (scope = 'personal' OR scope GLOB 'project:?*' OR scope GLOB 'work:?*'),
  status TEXT NOT NULL CHECK (status IN ('active', 'superseded', 'retracted', 'quarantined', 'purged')),
  value TEXT NOT NULL CHECK (value IN ('forming', 'kept')),
  check_status TEXT NOT NULL CHECK (check_status IN ('not_needed', 'unchecked', 'checked', 'contradicted', 'not_independent')),
  salience REAL NOT NULL DEFAULT 0,        -- orders only; never deletes (§5.11)
  said_at TEXT,
  built_at TEXT NOT NULL,
  PRIMARY KEY (tenant_id, item_id)
);
CREATE INDEX item_line_scope ON item_line (scope, status, class);

-- Active items kept out of the index, each with a reason (projection check, I9).
CREATE TABLE item_filtered (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  item_id TEXT NOT NULL,
  reason TEXT NOT NULL,
  PRIMARY KEY (tenant_id, item_id)
);

-- Keyword index (BM25) over line, your words, why, question key, topic labels and aliases.
CREATE VIRTUAL TABLE keys USING fts5(
  tenant_id UNINDEXED,
  item_id UNINDEXED,
  line,
  your_words,
  why,
  question_key,
  topic_labels,
  aliases,
  tokenize = 'unicode61 remove_diacritics 2'
);

-- Embeddings of line and question_key, from a small model on this Mac; keyed by model so a change rebuilds them.
CREATE TABLE vectors (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  item_id TEXT NOT NULL,
  model TEXT NOT NULL,
  field TEXT NOT NULL CHECK (field IN ('line', 'question_key')),
  version INTEGER NOT NULL,
  dim INTEGER NOT NULL CHECK (dim > 0),
  vector BLOB NOT NULL,                    -- little-endian float32
  built_at TEXT NOT NULL,
  PRIMARY KEY (tenant_id, item_id, model, field),
  CHECK (length(vector) = dim * 4)
);
CREATE INDEX vectors_model ON vectors (model);

-- Keyword and vector indexes over chat-history exchanges (a user turn with its reply), item lines added as extra keys.
-- your_text and reply_text are separate columns so a search can return your words by default (§4.7).
CREATE VIRTUAL TABLE history_keys USING fts5(
  tenant_id UNINDEXED,
  exchange_id UNINDEXED,
  source_id UNINDEXED,
  user_message_id UNINDEXED,
  reply_message_id UNINDEXED,
  occurred_at UNINDEXED,
  your_text,
  reply_text,
  item_lines,
  tokenize = 'unicode61 remove_diacritics 2'
);

CREATE TABLE history_vectors (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  exchange_id TEXT NOT NULL,
  model TEXT NOT NULL,
  dim INTEGER NOT NULL CHECK (dim > 0),
  vector BLOB NOT NULL,
  built_at TEXT NOT NULL,
  PRIMARY KEY (tenant_id, exchange_id, model),
  CHECK (length(vector) = dim * 4)
);

-- Checked links, for searching one or two steps out (§4.2 L1). `strength` orders: stated or confirmed, then by
-- construction, then checked.
CREATE TABLE link_view (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  link_id TEXT NOT NULL,
  from_id TEXT NOT NULL,
  to_id TEXT NOT NULL,
  to_kind TEXT NOT NULL CHECK (to_kind IN ('item', 'work')),
  type TEXT NOT NULL CHECK (type IN ('supports', 'refines', 'conflicts', 'answers', 'case_of', 'advances', 'used_in', 'same_as')),
  strength TEXT NOT NULL CHECK (strength IN ('stated_or_confirmed', 'construction', 'checked')),
  PRIMARY KEY (tenant_id, link_id)
);
CREATE INDEX link_view_from ON link_view (from_id);
CREATE INDEX link_view_to ON link_view (to_id);

-- Per goal and work thread (§2.10): goal text, aliases, project, top 8 linked items, open questions, last active.
CREATE TABLE goal_card (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  goal_item_id TEXT,
  thread_id TEXT,
  goal_text TEXT NOT NULL,
  aliases TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(aliases) AND json_type(aliases) = 'array'),
  project TEXT,
  top_items TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(top_items) AND json_type(top_items) = 'array'),   -- at most 8 item@version
  open_questions TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(open_questions) AND json_type(open_questions) = 'array'),
  last_active TEXT,
  built_at TEXT NOT NULL,
  CHECK (goal_item_id IS NOT NULL OR thread_id IS NOT NULL),
  PRIMARY KEY (tenant_id, id)
);
CREATE INDEX goal_card_thread ON goal_card (thread_id);
CREATE INDEX goal_card_project ON goal_card (project);

-- Per active work thread: the rendered text, the items it was built from, and the memory watermark it was built at.
CREATE TABLE start_note (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  thread_id TEXT NOT NULL,
  text TEXT NOT NULL,
  items TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(items) AND json_type(items) = 'array'),   -- item@version
  built_at TEXT NOT NULL,
  watermark INTEGER NOT NULL,              -- the memory event seq it was built at
  PRIMARY KEY (tenant_id, thread_id)
);

-- Per item, one row per use: delivered, recalled, viewed or built on, with the context. Salience (§5.11) is computed
-- from these. State, not derived: a full rebuild keeps it (it can be recomputed from receipts and marks).
CREATE TABLE use (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  item_id TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('delivered', 'recalled', 'viewed', 'built_on')),
  at TEXT NOT NULL,
  context TEXT NOT NULL,                   -- the session or chat it happened in
  PRIMARY KEY (tenant_id, id)
);
CREATE INDEX use_item ON use (item_id, kind, at);

CREATE VIEW use_summary AS
SELECT tenant_id, item_id,
  SUM(kind = 'delivered') AS delivered,
  SUM(kind = 'recalled') AS recalled,
  SUM(kind = 'viewed') AS viewed,
  SUM(kind = 'built_on') AS built_on,
  MIN(at) AS first_at,
  MAX(at) AS last_at,
  COUNT(DISTINCT context) AS contexts
FROM use GROUP BY tenant_id, item_id;

-- The strict gate's bar for each project, and the misses and leaks that moved it (§4.5 step 8). State, not derived.
CREATE TABLE gate_bar (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  project TEXT NOT NULL,
  bar REAL NOT NULL,
  floor REAL NOT NULL,                     -- the bar never drops below this
  updated_at TEXT NOT NULL,
  CHECK (bar >= floor),
  PRIMARY KEY (tenant_id, project)
);

CREATE TABLE gate_bar_move (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  project TEXT NOT NULL,
  at TEXT NOT NULL,
  direction TEXT NOT NULL CHECK (direction IN ('lower', 'raise')),
  reason TEXT NOT NULL CHECK (reason IN ('re_explanation', 'presumption', 'leak')),
  bar_before REAL NOT NULL,
  bar_after REAL NOT NULL,
  ref TEXT,                                -- the item, receipt or message that moved it
  PRIMARY KEY (tenant_id, id)
);
CREATE INDEX gate_bar_move_project ON gate_bar_move (project, at);
