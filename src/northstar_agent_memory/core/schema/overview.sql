-- overview.db: the human structure (MEMORY-ARCHITECTURE §2.11). Derived: rebuilt each maintenance run from the last
-- layout, except `layout`, `layout_meta`, `mark` and `topic_mark`, which are your state and are backed up.
-- Version 1. It holds what any display needs; how it looks is not decided here. Every table carries tenant_id (§3.3),
-- and it leads every key: primary keys and unique constraints are (tenant_id, id).
--
-- Triggers this file defines (the gate's REQUIRED_TRIGGERS are checked against this list): none. Everything here is
-- derived or your own display state, and is rebuilt or changed in place.
-- Never holds AI prose, IDs shown to you, file paths, or links Northstar found until you confirm them (I27).

CREATE TABLE topic_view (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  topic_id TEXT NOT NULL,
  label TEXT NOT NULL,
  parent_id TEXT,
  entries TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(entries) AND json_type(entries) = 'array'),   -- up to G item ids: pins, open items, then salience
  more_count INTEGER NOT NULL DEFAULT 0 CHECK (more_count >= 0),
  open_count INTEGER NOT NULL DEFAULT 0 CHECK (open_count >= 0),
  changed_since_seen INTEGER NOT NULL DEFAULT 0 CHECK (changed_since_seen IN (0, 1)),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'dormant')),
  built_at TEXT NOT NULL,
  PRIMARY KEY (tenant_id, topic_id)
);
CREATE INDEX topic_view_parent ON topic_view (parent_id);

CREATE TABLE idea_view (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  item_id TEXT NOT NULL,
  shown_line TEXT NOT NULL,                -- your words if they carry it; else the line, marked as Northstar's wording
  shown_is_yours INTEGER NOT NULL CHECK (shown_is_yours IN (0, 1)),
  origin_mark TEXT NOT NULL,               -- 'yours', or 'adopted from <agent>'
  work_cues TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(work_cues) AND json_type(work_cues) = 'array'),   -- 1 to 3: a label and a snapshot
  sources TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(sources) AND json_type(sources) = 'array'),         -- app, chat title, day
  links TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(links) AND json_type(links) = 'array'),               -- stated or confirmed only
  conflict_pairs TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(conflict_pairs) AND json_type(conflict_pairs) = 'array'),
  version INTEGER NOT NULL,
  built_at TEXT NOT NULL,
  PRIMARY KEY (tenant_id, item_id)
);

-- Links Northstar found, waiting for your confirmation; never drawn before it (I27).
CREATE TABLE suggestion (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  link_id TEXT NOT NULL,
  from_id TEXT NOT NULL,
  to_id TEXT NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('supports', 'refines', 'conflicts', 'answers', 'case_of', 'advances', 'used_in', 'same_as')),
  reason TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'waiting' CHECK (status IN ('waiting', 'confirmed', 'rejected')),
  created_at TEXT NOT NULL,
  PRIMARY KEY (tenant_id, link_id)
);

-- What to learn: open questions, open conflicts, active goals, next steps you stated, and gaps on your own paths.
-- A term that merely appeared is never a gap.
CREATE TABLE open_item (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('open_question', 'open_conflict', 'active_goal', 'next_step', 'goal_gap')),
  ref_id TEXT NOT NULL,                    -- the item or conflict it comes from
  line TEXT NOT NULL,
  topic_id TEXT,
  since TEXT,
  built_at TEXT NOT NULL,
  PRIMARY KEY (tenant_id, id)
);
CREATE INDEX open_item_topic ON open_item (topic_id);

-- Per work thread: last state, last steps, what changed since, goal, next step, open questions.
CREATE TABLE left_off (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  thread_id TEXT NOT NULL,
  last_state TEXT NOT NULL DEFAULT '',
  last_steps TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(last_steps) AND json_type(last_steps) = 'array'),
  changed_since TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(changed_since) AND json_type(changed_since) = 'array'),
  goal TEXT,
  next_step TEXT,
  open_questions TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(open_questions) AND json_type(open_questions) = 'array'),
  updated_at TEXT NOT NULL,
  PRIMARY KEY (tenant_id, thread_id)
);

-- Layout: positions of topics and entries, the previous layout, and the seed. Unchanged topics stay in place.
CREATE TABLE layout (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  node_id TEXT NOT NULL,                   -- a topic id or an item id
  node_kind TEXT NOT NULL CHECK (node_kind IN ('topic', 'entry')),
  x REAL NOT NULL,
  y REAL NOT NULL,
  prev_x REAL,
  prev_y REAL,
  updated_at TEXT NOT NULL,
  CHECK ((prev_x IS NULL) = (prev_y IS NULL)),
  PRIMARY KEY (tenant_id, node_id)
);

CREATE TABLE layout_meta (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id INTEGER NOT NULL CHECK (id = 1),
  seed INTEGER NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (tenant_id, id)
);

-- Marks (§2.11): per idea, the last version you saw; per topic, how often you open its hidden entries.
-- They stay on this Mac, are never given to a model, and only feed salience and the split bar.
CREATE TABLE mark (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  item_id TEXT NOT NULL,
  last_seen_version INTEGER NOT NULL,
  seen_at TEXT NOT NULL,
  pinned INTEGER NOT NULL DEFAULT 0 CHECK (pinned IN (0, 1)),
  PRIMARY KEY (tenant_id, item_id)
);

CREATE TABLE topic_mark (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  topic_id TEXT NOT NULL,
  hidden_opens INTEGER NOT NULL DEFAULT 0 CHECK (hidden_opens >= 0),
  last_opened_at TEXT,
  PRIMARY KEY (tenant_id, topic_id)
);
