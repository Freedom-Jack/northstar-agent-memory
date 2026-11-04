-- memory.db: the event log and the current state it builds (MEMORY-ARCHITECTURE §2.3-§2.8, §3.1). Writer: the write gate only.
-- Version 1. Every table carries tenant_id (§3.3), and it leads every key: primary keys, unique constraints and foreign
-- keys are (tenant_id, id), so two tenants can never collide or point at each other's rows.
-- The event log is append-only (I6). Current-state tables hold each row as it stands now; `seq_from` is the seq of
-- the event that made that state. Before a row changes or is deleted, its old state is copied into `<table>_history`
-- with `seq_to` set to the seq of the changing event (db.archive_row), so "as of seq N" is: the current row if
-- seq_from <= N, else the history row with seq_from <= N < seq_to (§2.3 row history).
-- Foreign keys to item are DEFERRABLE INITIALLY DEFERRED: one proposal's events (evidence before the item, as in §6.2)
-- commit in one transaction and are checked at COMMIT. The projector checks the rows an event names itself and raises
-- ProjectionError, so a missing item never first shows as a foreign-key error at COMMIT.
-- Cross-store references (message_id, work_event_id, snapshot_sha256) point into history.db and are checked by the gate.
--
-- Triggers this file defines (the gate's REQUIRED_TRIGGERS are checked against this list):
--   purge_authorization_no_update, purge_authorization_no_delete
--   event_frozen, event_no_update, event_no_delete
--   event_subject_no_update, event_subject_no_delete
--   evidence_frozen, evidence_no_delete
--   stance_no_update, stance_no_delete
--   topic_two_levels_insert, topic_two_levels_update
--   placement_also_in_limit
--   item_history_no_update, item_history_no_delete
--   evidence_history_no_update, evidence_history_no_delete
--   link_history_no_update, link_history_no_delete
--   supersession_history_no_update, supersession_history_no_delete
--   conflict_history_no_update, conflict_history_no_delete
--   work_history_no_update, work_history_no_delete
--   style_line_history_no_update, style_line_history_no_delete
--   correction_history_no_update, correction_history_no_delete
--   scope_history_no_update, scope_history_no_delete
--   topic_history_no_update, topic_history_no_delete
--   placement_history_no_update, placement_history_no_delete

-- Event log ------------------------------------------------------------------------------------------------------
CREATE TABLE event (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,   -- local and increasing; the watermark
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,                        -- ULID
  type TEXT NOT NULL CHECK (type IN (
    'evidence.anchored', 'item.created', 'item.revised', 'item.value_changed',
    'item.scope_widened', 'item.status_changed', 'item.checked', 'stance.recorded',
    'link.proposed', 'link.applied', 'link.confirmed', 'link.rejected',
    'link.retracted', 'supersession.applied', 'supersession.undone', 'conflict.opened',
    'conflict.resolved', 'conflict.reopened', 'conflict.undone', 'goal.created',
    'goal.status_changed', 'goal.confirmed', 'question.created', 'question.status_changed',
    'work.registered', 'work.labelled', 'style.recorded', 'style.revised',
    'correction.applied', 'correction.lifted', 'topic.created', 'topic.split',
    'topic.branched', 'topic.merged', 'topic.folded_back', 'topic.renamed',
    'topic.dormant', 'idea.placed', 'idea.moved', 'compensation.batch',
    'purge.applied', 'scope.hold_changed')),
  schema_version INTEGER NOT NULL DEFAULT 1 CHECK (schema_version >= 1),   -- I15
  subjects TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(subjects) AND json_type(subjects) = 'array'),
  payload TEXT NOT NULL CHECK (json_valid(payload) AND json_type(payload) = 'object'),
  actor TEXT NOT NULL CHECK (actor = 'user' OR actor GLOB 'code:?*' OR actor GLOB 'model:?*'),
                                           -- user | code:<module> | model:<name>@<version>#<prompt hash>
  run_id TEXT,
  proposal_id TEXT,
  index_in_proposal INTEGER CHECK (index_in_proposal IS NULL OR index_in_proposal >= 0),
  inputs TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(inputs) AND json_type(inputs) = 'array'),   -- object@version
  compensates TEXT,                        -- set when the event undoes another
  config_version TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  CHECK ((proposal_id IS NULL) = (index_in_proposal IS NULL)),
  CHECK (proposal_id IS NULL OR run_id IS NOT NULL),
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, run_id, proposal_id, index_in_proposal),   -- I14: a replayed run applies nothing twice
  FOREIGN KEY (tenant_id, compensates) REFERENCES event (tenant_id, id)
);
CREATE INDEX event_type ON event (type, seq);
CREATE INDEX event_run ON event (run_id, proposal_id);
CREATE INDEX event_compensates ON event (compensates);

-- One row per (event, subject id), so "events about this item" is an index lookup. Written with the event.
CREATE TABLE event_subject (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  subject_id TEXT NOT NULL,
  seq INTEGER NOT NULL REFERENCES event (seq),
  PRIMARY KEY (tenant_id, subject_id, seq)
);
CREATE INDEX event_subject_seq ON event_subject (seq);
-- The subject rows are written with their event and never change; they go only with an event a purge authorized.
CREATE TRIGGER event_subject_no_update BEFORE UPDATE ON event_subject
BEGIN SELECT RAISE(ABORT, 'I6 append-only: event_subject'); END;
CREATE TRIGGER event_subject_no_delete BEFORE DELETE ON event_subject
WHEN NOT EXISTS (SELECT 1 FROM purge_authorization p JOIN event e ON e.id = p.target_id AND e.tenant_id = p.tenant_id
                 WHERE p.target_table = 'event' AND e.seq = OLD.seq AND p.tenant_id = OLD.tenant_id)
BEGIN SELECT RAISE(ABORT, 'I6 append-only: event_subject'); END;

-- What a purge may scrub or remove (§3.4), written by the purge saga before it changes anything, and kept.
-- An authorized UPDATE of an event may change only payload, subjects and inputs.
CREATE TABLE purge_authorization (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  purge_id TEXT NOT NULL,
  target_table TEXT NOT NULL,              -- a table of this store, e.g. event, evidence, item_history
  target_id TEXT NOT NULL,                 -- the row's id
  authorized_at TEXT NOT NULL,
  PRIMARY KEY (tenant_id, purge_id, target_table, target_id)
);
CREATE INDEX purge_authorization_target ON purge_authorization (tenant_id, target_table, target_id);
CREATE TRIGGER purge_authorization_no_update BEFORE UPDATE ON purge_authorization
BEGIN SELECT RAISE(ABORT, 'I6 append-only: purge_authorization'); END;
CREATE TRIGGER purge_authorization_no_delete BEFORE DELETE ON purge_authorization
BEGIN SELECT RAISE(ABORT, 'I6 append-only: purge_authorization'); END;

CREATE TRIGGER event_frozen BEFORE UPDATE OF seq, tenant_id, id, type, schema_version, actor, run_id, proposal_id,
  index_in_proposal, compensates, config_version, recorded_at ON event
BEGIN SELECT RAISE(ABORT, 'I6: an event never changes what it records'); END;
CREATE TRIGGER event_no_update BEFORE UPDATE ON event
WHEN NOT EXISTS (SELECT 1 FROM purge_authorization WHERE target_table = 'event' AND target_id = OLD.id AND tenant_id = OLD.tenant_id)
BEGIN SELECT RAISE(ABORT, 'I6 append-only: event'); END;
CREATE TRIGGER event_no_delete BEFORE DELETE ON event
WHEN NOT EXISTS (SELECT 1 FROM purge_authorization WHERE target_table = 'event' AND target_id = OLD.id AND tenant_id = OLD.tenant_id)
BEGIN SELECT RAISE(ABORT, 'I6 append-only: event'); END;

-- Items (§2.4, §2.7) ---------------------------------------------------------------------------------------------
-- Goals and questions are items; their extra state is in the goal_* and question columns.
CREATE TABLE item (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),   -- rises when the line, scope or certainty changes
  kind TEXT NOT NULL CHECK (kind IN ('decision', 'ruled_out', 'result', 'conclusion', 'definition', 'plan',
    'principle', 'approach', 'position', 'goal', 'question')),
  class TEXT NOT NULL CHECK (class IN ('fact', 'view')),     -- set by kind; when unsure, view
  line TEXT NOT NULL,
  your_words TEXT NOT NULL DEFAULT '',
  why TEXT NOT NULL DEFAULT '',
  question_key TEXT NOT NULL DEFAULT '',
  scope TEXT NOT NULL CHECK (scope = 'personal' OR scope GLOB 'project:?*' OR scope GLOB 'work:?*'),
  applies_when TEXT NOT NULL DEFAULT 'unknown',
  learned_in TEXT NOT NULL,
  contexts_seen TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(contexts_seen) AND json_type(contexts_seen) = 'array'),
  origin TEXT NOT NULL CHECK (origin = 'yours' OR origin GLOB 'adopted:?*'),   -- computed from evidence, never set by a model
  value TEXT NOT NULL DEFAULT 'forming' CHECK (value IN ('forming', 'kept')),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'superseded', 'retracted', 'quarantined', 'purged')),
  check_status TEXT NOT NULL DEFAULT 'not_needed'
    CHECK (check_status IN ('not_needed', 'unchecked', 'checked', 'contradicted', 'not_independent')),   -- adopted AI claims only
  said_at TEXT NOT NULL,
  valid_from TEXT,
  valid_to TEXT,
  recorded_at TEXT NOT NULL,
  time_bound INTEGER NOT NULL DEFAULT 0 CHECK (time_bound IN (0, 1)),
  merged_into TEXT,                        -- set by a same_as merge; the line becomes an alias
  goal_basis TEXT CHECK (goal_basis IN ('stated', 'reported', 'reused')),
  goal_status TEXT CHECK (goal_status IN ('active', 'paused', 'done', 'dropped')),
  work_id TEXT,                            -- the piece of work in working.db
  raised_by TEXT CHECK (raised_by IN ('you', 'ai_taken_up', 'conflict')),
  question_status TEXT CHECK (question_status IN ('open', 'answered', 'dormant')),
  answered_by TEXT CHECK (answered_by IS NULL OR (json_valid(answered_by) AND json_type(answered_by) = 'array')),   -- item ids that answer it; set by the projector
  created_seq INTEGER NOT NULL,
  seq_from INTEGER NOT NULL,
  CHECK (kind IN ('decision', 'ruled_out', 'result', 'conclusion', 'definition', 'plan') OR class = 'view'),
  CHECK (kind <> 'goal' OR (goal_basis IS NOT NULL AND goal_status IS NOT NULL)),
  CHECK (kind = 'goal' OR (goal_basis IS NULL AND goal_status IS NULL AND work_id IS NULL)),
  CHECK (kind <> 'question' OR (raised_by IS NOT NULL AND question_status IS NOT NULL)),
  CHECK (kind = 'question' OR (raised_by IS NULL AND question_status IS NULL AND answered_by IS NULL)),
  CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_from <= valid_to),
  PRIMARY KEY (tenant_id, id),
  FOREIGN KEY (tenant_id, merged_into) REFERENCES item (tenant_id, id) DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX item_status ON item (status, kind);
CREATE INDEX item_scope ON item (scope, status);
CREATE INDEX item_seq ON item (seq_from);

-- Evidence (§2.5). Who said it is copied from capture by the gate, then frozen (I3, I20).
-- A subject is an item, a style line or a correction (I1, I5).
CREATE TABLE evidence (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  subject_kind TEXT NOT NULL CHECK (subject_kind IN ('item', 'style_line', 'correction')),
  subject_id TEXT NOT NULL,
  message_id TEXT NOT NULL,                -- in history.db
  start_char INTEGER NOT NULL CHECK (start_char >= 0),
  end_char INTEGER NOT NULL,
  quote TEXT NOT NULL,                     -- exact; checked against the message (I2)
  role TEXT NOT NULL CHECK (role IN ('primary', 'adoption', 'support', 'reason', 'scope')),
  speaker TEXT NOT NULL CHECK (speaker IN ('user', 'assistant', 'tool', 'northstar', 'system')),
  agent TEXT,
  model_family TEXT,
  origin TEXT NOT NULL CHECK (origin IN ('typed', 'pasted', 'assistant_output', 'tool_output', 'model_reported', 'northstar_injected')),
  lineage TEXT NOT NULL DEFAULT 'primary' CHECK (lineage IN ('primary', 'northstar_echo')),   -- an echo never counts as support (I11)
  context TEXT,                            -- the message's source project, or 'personal' outside a project; stamped by the gate
  created_seq INTEGER NOT NULL,
  seq_from INTEGER NOT NULL,
  CHECK (end_char > start_char),
  PRIMARY KEY (tenant_id, id)
);
CREATE INDEX evidence_subject ON evidence (subject_id);
CREATE INDEX evidence_message ON evidence (message_id);
CREATE TRIGGER evidence_frozen BEFORE UPDATE OF tenant_id, id, subject_kind, message_id, start_char, end_char, quote, role, speaker,
  agent, model_family, origin, lineage, context, created_seq ON evidence
WHEN NOT EXISTS (SELECT 1 FROM purge_authorization WHERE target_table = 'evidence' AND target_id = OLD.id AND tenant_id = OLD.tenant_id)
BEGIN SELECT RAISE(ABORT, 'I3/I20: evidence is frozen once anchored'); END;
-- Evidence is removed only by a purge (§3.4), or by a rollback that undoes the event which anchored it; both write a
-- purge_authorization row first (the projector does), and that row is kept.
CREATE TRIGGER evidence_no_delete BEFORE DELETE ON evidence
WHEN NOT EXISTS (SELECT 1 FROM purge_authorization WHERE target_table = 'evidence' AND target_id = OLD.id AND tenant_id = OLD.tenant_id)
BEGIN SELECT RAISE(ABORT, 'I6 append-only: evidence is removed only under a purge authorization'); END;

-- Links (§2.6). `to_id` is an item, or a piece of work for used_in.
CREATE TABLE link (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  from_id TEXT NOT NULL,
  to_id TEXT NOT NULL,
  to_kind TEXT NOT NULL DEFAULT 'item' CHECK (to_kind IN ('item', 'work')),
  type TEXT NOT NULL CHECK (type IN ('supports', 'refines', 'conflicts', 'answers', 'case_of', 'advances', 'used_in', 'same_as')),
  reason TEXT NOT NULL,                    -- one line that cites both ends
  stated_by TEXT NOT NULL CHECK (stated_by IN ('you', 'northstar', 'construction')),
  status TEXT NOT NULL CHECK (status IN ('proposed', 'applied', 'confirmed', 'rejected', 'retracted')),
  checked_by TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(checked_by) AND json_type(checked_by) = 'array'),   -- families
  created_seq INTEGER NOT NULL,
  seq_from INTEGER NOT NULL,
  CHECK (to_kind = 'work' OR from_id <> to_id),
  CHECK (type <> 'used_in' OR to_kind = 'work'),
  CHECK (type = 'used_in' OR to_kind = 'item'),
  PRIMARY KEY (tenant_id, id),
  FOREIGN KEY (tenant_id, from_id) REFERENCES item (tenant_id, id) DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX link_from ON link (from_id, type);
CREATE INDEX link_to ON link (to_id, type);

-- Supersession (§2.6). The old version stays readable in item_history. new_version is NULL when the new item is a
-- different item; a refresh makes a new version of the same item (old_item = new_item).
CREATE TABLE supersession (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  old_item TEXT NOT NULL,
  old_version INTEGER NOT NULL,
  new_item TEXT NOT NULL,
  new_version INTEGER,
  reason TEXT NOT NULL CHECK (reason IN ('your_later_statement', 'ai_self_correction', 'check_contradicted',
    'your_correction', 'refresh', 'scope_split')),
  evidence_ids TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(evidence_ids) AND json_type(evidence_ids) = 'array'),
  at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'applied' CHECK (status IN ('applied', 'undone')),
  created_seq INTEGER NOT NULL,
  seq_from INTEGER NOT NULL,
  PRIMARY KEY (tenant_id, id),
  FOREIGN KEY (tenant_id, old_item) REFERENCES item (tenant_id, id) DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY (tenant_id, new_item) REFERENCES item (tenant_id, id) DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX supersession_old ON supersession (old_item, old_version);
CREATE INDEX supersession_new ON supersession (new_item);

-- Conflicts (§2.6). State 'undone' is the one addition to §2.6's four states: conflict.undone on a conflict.opened.
CREATE TABLE conflict (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  side_a_item TEXT NOT NULL,
  side_a_version INTEGER NOT NULL,
  side_b_item TEXT NOT NULL,
  side_b_version INTEGER NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('across_contexts', 'same_context')),
  state TEXT NOT NULL CHECK (state IN ('both_stand', 'open', 'resolved', 'contested', 'undone')),
  resolution TEXT CHECK (resolution IS NULL OR json_valid(resolution)),   -- {step, winner?, inputs, rule_version}
  question_id TEXT,                        -- an open question, raised when contested
  link_id TEXT,                            -- the conflicts link, when one was stated or found
  recheck_after TEXT,
  created_seq INTEGER NOT NULL,
  seq_from INTEGER NOT NULL,
  CHECK (side_a_item <> side_b_item),
  PRIMARY KEY (tenant_id, id),
  FOREIGN KEY (tenant_id, side_a_item) REFERENCES item (tenant_id, id) DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY (tenant_id, side_b_item) REFERENCES item (tenant_id, id) DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY (tenant_id, question_id) REFERENCES item (tenant_id, id) DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX conflict_state ON conflict (state);
CREATE INDEX conflict_sides ON conflict (side_a_item, side_b_item);

-- Your work (§2.7): a pointer to anything you got your hands on.
CREATE TABLE work (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('commit', 'file_version', 'render', 'diagram', 'decision_record')),
  ref TEXT NOT NULL,
  project TEXT,
  label TEXT NOT NULL DEFAULT '',          -- one line on what it shows; checked; else the commit message or file name
  label_source TEXT NOT NULL DEFAULT 'commit_message' CHECK (label_source IN ('checked', 'commit_message', 'file_name')),
  evidence TEXT NOT NULL CHECK (evidence IN ('strong', 'medium', 'weak')),
  work_event_id TEXT,                      -- in history.db
  snapshot_sha256 TEXT,
  occurred_at TEXT,
  created_seq INTEGER NOT NULL,
  seq_from INTEGER NOT NULL,
  PRIMARY KEY (tenant_id, id)
);
CREATE INDEX work_ref ON work (kind, ref);

-- Working style (§2.7): only maintenance writes it; it reaches an AI only when the AI asks (I25).
CREATE TABLE style_line (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  line TEXT NOT NULL,
  scope TEXT NOT NULL CHECK (scope = 'personal' OR scope GLOB 'project:?*' OR scope GLOB 'work:?*'),   -- where learned
  basis TEXT NOT NULL CHECK (basis IN ('stated_default', 'seen_in_sessions')),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'retracted')),
  created_seq INTEGER NOT NULL,
  seq_from INTEGER NOT NULL,
  PRIMARY KEY (tenant_id, id)
);

-- Corrections (§2.7): your one-step marks. Each is a constraint the gate enforces; later evidence never lifts it (I21).
CREATE TABLE correction (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('not_what_i_think', 'keep', 'project_only', 'rename', 'move', 'keep_together',
    'these_are_different', 'give_own_topic', 'fold_back', 'not_part_of_this', 'confirm_link', 'reject_link', 'pin', 'purge')),
  target TEXT NOT NULL,                    -- the id it applies to
  via TEXT NOT NULL CHECK (via IN ('typed', 'click')),
  evidence_id TEXT,                        -- your typed words (I5)
  params TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(params)),
  constraint_rule TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(constraint_rule)),
  at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'lifted')),   -- lifted only by your undo, a later correction, or a purge
  lifted_reason TEXT CHECK (lifted_reason IN ('your_undo', 'your_later_correction', 'purge')),
  created_seq INTEGER NOT NULL,
  seq_from INTEGER NOT NULL,
  CHECK (via <> 'typed' OR evidence_id IS NOT NULL),
  CHECK ((status = 'lifted') = (lifted_reason IS NOT NULL)),
  PRIMARY KEY (tenant_id, id)
);
CREATE INDEX correction_target ON correction (target, status);

CREATE TABLE scope (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,                        -- personal | project:<id> | work:<org> | session:<id>
  kind TEXT NOT NULL CHECK (kind IN ('personal', 'project', 'work', 'session')),
  label TEXT,
  held INTEGER NOT NULL DEFAULT 0 CHECK (held IN (0, 1)),   -- held: captured, but never delivered or shown
  held_seq INTEGER,
  created_seq INTEGER NOT NULL,
  seq_from INTEGER NOT NULL,
  CHECK ((kind = 'personal') = (id = 'personal')),
  CHECK (kind = 'personal' OR id GLOB kind || ':?*'),
  CHECK (held = 0 OR held_seq IS NOT NULL),
  PRIMARY KEY (tenant_id, id)
);

-- Stances (§2.3 "your moves"): what you did with an item. Written once per event; never changes.
CREATE TABLE stance (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,                        -- the id of the stance.recorded event
  item_id TEXT NOT NULL,
  stance TEXT NOT NULL CHECK (stance IN ('stated', 'adopted', 'ruled_out', 'revised', 'built_on')),
  evidence_ids TEXT NOT NULL CHECK (json_valid(evidence_ids) AND json_type(evidence_ids) = 'array'),
  created_seq INTEGER NOT NULL,
  PRIMARY KEY (tenant_id, id),
  FOREIGN KEY (tenant_id, item_id) REFERENCES item (tenant_id, id) DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX stance_item ON stance (item_id, stance);
CREATE TRIGGER stance_no_update BEFORE UPDATE ON stance
WHEN NOT EXISTS (SELECT 1 FROM purge_authorization WHERE target_table = 'stance' AND target_id = OLD.id AND tenant_id = OLD.tenant_id)
BEGIN SELECT RAISE(ABORT, 'I6 append-only: stance'); END;
CREATE TRIGGER stance_no_delete BEFORE DELETE ON stance
WHEN NOT EXISTS (SELECT 1 FROM purge_authorization WHERE target_table = 'stance' AND target_id = OLD.id AND tenant_id = OLD.tenant_id)
BEGIN SELECT RAISE(ABORT, 'I6 append-only: stance'); END;

-- Topics and placement (§2.8). Two levels at most.
CREATE TABLE topic (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,                        -- stable; never reused
  label TEXT NOT NULL,                     -- in your words
  label_fixed INTEGER NOT NULL DEFAULT 0 CHECK (label_fixed IN (0, 1)),   -- a label you set is fixed
  parent_id TEXT,
  anchor_id TEXT,                          -- your goal, a question you pursue, or an idea of yours (an item id)
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'dormant', 'merged_into', 'split_into', 'folded_into')),
  redirect_to TEXT,                        -- where a retired topic now lives
  formation_overlap REAL CHECK (formation_overlap IS NULL OR (formation_overlap >= 0 AND formation_overlap <= 1)),
  created_seq INTEGER NOT NULL,
  seq_from INTEGER NOT NULL,
  CHECK (parent_id IS NULL OR parent_id <> id),
  CHECK ((status IN ('merged_into', 'split_into', 'folded_into')) = (redirect_to IS NOT NULL)),
  PRIMARY KEY (tenant_id, id),
  FOREIGN KEY (tenant_id, parent_id) REFERENCES topic (tenant_id, id) DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX topic_parent ON topic (parent_id);
CREATE TRIGGER topic_two_levels_insert BEFORE INSERT ON topic
WHEN NEW.parent_id IS NOT NULL AND (SELECT parent_id FROM topic WHERE id = NEW.parent_id AND tenant_id = NEW.tenant_id) IS NOT NULL
BEGIN SELECT RAISE(ABORT, 'topics have two levels at most'); END;
CREATE TRIGGER topic_two_levels_update BEFORE UPDATE OF parent_id ON topic
WHEN NEW.parent_id IS NOT NULL AND (SELECT parent_id FROM topic WHERE id = NEW.parent_id AND tenant_id = NEW.tenant_id) IS NOT NULL
BEGIN SELECT RAISE(ABORT, 'topics have two levels at most'); END;

CREATE TABLE placement (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  item_id TEXT NOT NULL,
  topic_id TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('home', 'also_in')),
  tentative INTEGER NOT NULL DEFAULT 0 CHECK (tentative IN (0, 1)),   -- settled by the next weekly run, never by you
  reasons TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(reasons) AND json_type(reasons) = 'array'),   -- the top two signals, in words
  created_seq INTEGER NOT NULL,
  seq_from INTEGER NOT NULL,
  PRIMARY KEY (tenant_id, id),
  UNIQUE (tenant_id, item_id, topic_id),
  FOREIGN KEY (tenant_id, item_id) REFERENCES item (tenant_id, id) DEFERRABLE INITIALLY DEFERRED,
  FOREIGN KEY (tenant_id, topic_id) REFERENCES topic (tenant_id, id) DEFERRABLE INITIALLY DEFERRED
);
CREATE UNIQUE INDEX placement_one_home ON placement (tenant_id, item_id) WHERE role = 'home';   -- every idea has one home
CREATE INDEX placement_topic ON placement (topic_id, role);
CREATE TRIGGER placement_also_in_limit BEFORE INSERT ON placement
WHEN NEW.role = 'also_in' AND (SELECT COUNT(*) FROM placement WHERE item_id = NEW.item_id AND tenant_id = NEW.tenant_id AND role = 'also_in') >= 2
BEGIN SELECT RAISE(ABORT, 'an idea has up to two also_in places'); END;

-- Row history (§2.3): every earlier state of a current-state row, closed at seq_to ---------------------------------
CREATE TABLE item_history (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  version INTEGER NOT NULL,
  seq_from INTEGER NOT NULL,
  seq_to INTEGER NOT NULL,
  snapshot TEXT NOT NULL CHECK (json_valid(snapshot)),
  PRIMARY KEY (tenant_id, id, seq_from),
  CHECK (seq_to > seq_from)
);
CREATE INDEX item_history_range ON item_history (id, seq_from, seq_to);
CREATE TRIGGER item_history_no_update BEFORE UPDATE ON item_history
WHEN NOT EXISTS (SELECT 1 FROM purge_authorization WHERE target_table = 'item_history' AND target_id = OLD.id AND tenant_id = OLD.tenant_id)
BEGIN SELECT RAISE(ABORT, 'I6 append-only: item_history'); END;
CREATE TRIGGER item_history_no_delete BEFORE DELETE ON item_history
WHEN NOT EXISTS (SELECT 1 FROM purge_authorization WHERE target_table = 'item_history' AND target_id = OLD.id AND tenant_id = OLD.tenant_id)
BEGIN SELECT RAISE(ABORT, 'I6 append-only: item_history'); END;

CREATE TABLE evidence_history (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  seq_from INTEGER NOT NULL,
  seq_to INTEGER NOT NULL,
  snapshot TEXT NOT NULL CHECK (json_valid(snapshot)),
  PRIMARY KEY (tenant_id, id, seq_from),
  CHECK (seq_to > seq_from)
);
CREATE INDEX evidence_history_range ON evidence_history (id, seq_from, seq_to);
CREATE TRIGGER evidence_history_no_update BEFORE UPDATE ON evidence_history
WHEN NOT EXISTS (SELECT 1 FROM purge_authorization WHERE target_table = 'evidence_history' AND target_id = OLD.id AND tenant_id = OLD.tenant_id)
BEGIN SELECT RAISE(ABORT, 'I6 append-only: evidence_history'); END;
CREATE TRIGGER evidence_history_no_delete BEFORE DELETE ON evidence_history
WHEN NOT EXISTS (SELECT 1 FROM purge_authorization WHERE target_table = 'evidence_history' AND target_id = OLD.id AND tenant_id = OLD.tenant_id)
BEGIN SELECT RAISE(ABORT, 'I6 append-only: evidence_history'); END;

CREATE TABLE link_history (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  seq_from INTEGER NOT NULL,
  seq_to INTEGER NOT NULL,
  snapshot TEXT NOT NULL CHECK (json_valid(snapshot)),
  PRIMARY KEY (tenant_id, id, seq_from),
  CHECK (seq_to > seq_from)
);
CREATE INDEX link_history_range ON link_history (id, seq_from, seq_to);
CREATE TRIGGER link_history_no_update BEFORE UPDATE ON link_history
WHEN NOT EXISTS (SELECT 1 FROM purge_authorization WHERE target_table = 'link_history' AND target_id = OLD.id AND tenant_id = OLD.tenant_id)
BEGIN SELECT RAISE(ABORT, 'I6 append-only: link_history'); END;
CREATE TRIGGER link_history_no_delete BEFORE DELETE ON link_history
WHEN NOT EXISTS (SELECT 1 FROM purge_authorization WHERE target_table = 'link_history' AND target_id = OLD.id AND tenant_id = OLD.tenant_id)
BEGIN SELECT RAISE(ABORT, 'I6 append-only: link_history'); END;

CREATE TABLE supersession_history (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  seq_from INTEGER NOT NULL,
  seq_to INTEGER NOT NULL,
  snapshot TEXT NOT NULL CHECK (json_valid(snapshot)),
  PRIMARY KEY (tenant_id, id, seq_from),
  CHECK (seq_to > seq_from)
);
CREATE INDEX supersession_history_range ON supersession_history (id, seq_from, seq_to);
CREATE TRIGGER supersession_history_no_update BEFORE UPDATE ON supersession_history
WHEN NOT EXISTS (SELECT 1 FROM purge_authorization WHERE target_table = 'supersession_history' AND target_id = OLD.id AND tenant_id = OLD.tenant_id)
BEGIN SELECT RAISE(ABORT, 'I6 append-only: supersession_history'); END;
CREATE TRIGGER supersession_history_no_delete BEFORE DELETE ON supersession_history
WHEN NOT EXISTS (SELECT 1 FROM purge_authorization WHERE target_table = 'supersession_history' AND target_id = OLD.id AND tenant_id = OLD.tenant_id)
BEGIN SELECT RAISE(ABORT, 'I6 append-only: supersession_history'); END;

CREATE TABLE conflict_history (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  seq_from INTEGER NOT NULL,
  seq_to INTEGER NOT NULL,
  snapshot TEXT NOT NULL CHECK (json_valid(snapshot)),
  PRIMARY KEY (tenant_id, id, seq_from),
  CHECK (seq_to > seq_from)
);
CREATE INDEX conflict_history_range ON conflict_history (id, seq_from, seq_to);
CREATE TRIGGER conflict_history_no_update BEFORE UPDATE ON conflict_history
WHEN NOT EXISTS (SELECT 1 FROM purge_authorization WHERE target_table = 'conflict_history' AND target_id = OLD.id AND tenant_id = OLD.tenant_id)
BEGIN SELECT RAISE(ABORT, 'I6 append-only: conflict_history'); END;
CREATE TRIGGER conflict_history_no_delete BEFORE DELETE ON conflict_history
WHEN NOT EXISTS (SELECT 1 FROM purge_authorization WHERE target_table = 'conflict_history' AND target_id = OLD.id AND tenant_id = OLD.tenant_id)
BEGIN SELECT RAISE(ABORT, 'I6 append-only: conflict_history'); END;

CREATE TABLE work_history (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  seq_from INTEGER NOT NULL,
  seq_to INTEGER NOT NULL,
  snapshot TEXT NOT NULL CHECK (json_valid(snapshot)),
  PRIMARY KEY (tenant_id, id, seq_from),
  CHECK (seq_to > seq_from)
);
CREATE INDEX work_history_range ON work_history (id, seq_from, seq_to);
CREATE TRIGGER work_history_no_update BEFORE UPDATE ON work_history
WHEN NOT EXISTS (SELECT 1 FROM purge_authorization WHERE target_table = 'work_history' AND target_id = OLD.id AND tenant_id = OLD.tenant_id)
BEGIN SELECT RAISE(ABORT, 'I6 append-only: work_history'); END;
CREATE TRIGGER work_history_no_delete BEFORE DELETE ON work_history
WHEN NOT EXISTS (SELECT 1 FROM purge_authorization WHERE target_table = 'work_history' AND target_id = OLD.id AND tenant_id = OLD.tenant_id)
BEGIN SELECT RAISE(ABORT, 'I6 append-only: work_history'); END;

CREATE TABLE style_line_history (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  seq_from INTEGER NOT NULL,
  seq_to INTEGER NOT NULL,
  snapshot TEXT NOT NULL CHECK (json_valid(snapshot)),
  PRIMARY KEY (tenant_id, id, seq_from),
  CHECK (seq_to > seq_from)
);
CREATE INDEX style_line_history_range ON style_line_history (id, seq_from, seq_to);
CREATE TRIGGER style_line_history_no_update BEFORE UPDATE ON style_line_history
WHEN NOT EXISTS (SELECT 1 FROM purge_authorization WHERE target_table = 'style_line_history' AND target_id = OLD.id AND tenant_id = OLD.tenant_id)
BEGIN SELECT RAISE(ABORT, 'I6 append-only: style_line_history'); END;
CREATE TRIGGER style_line_history_no_delete BEFORE DELETE ON style_line_history
WHEN NOT EXISTS (SELECT 1 FROM purge_authorization WHERE target_table = 'style_line_history' AND target_id = OLD.id AND tenant_id = OLD.tenant_id)
BEGIN SELECT RAISE(ABORT, 'I6 append-only: style_line_history'); END;

CREATE TABLE correction_history (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  seq_from INTEGER NOT NULL,
  seq_to INTEGER NOT NULL,
  snapshot TEXT NOT NULL CHECK (json_valid(snapshot)),
  PRIMARY KEY (tenant_id, id, seq_from),
  CHECK (seq_to > seq_from)
);
CREATE INDEX correction_history_range ON correction_history (id, seq_from, seq_to);
CREATE TRIGGER correction_history_no_update BEFORE UPDATE ON correction_history
WHEN NOT EXISTS (SELECT 1 FROM purge_authorization WHERE target_table = 'correction_history' AND target_id = OLD.id AND tenant_id = OLD.tenant_id)
BEGIN SELECT RAISE(ABORT, 'I6 append-only: correction_history'); END;
CREATE TRIGGER correction_history_no_delete BEFORE DELETE ON correction_history
WHEN NOT EXISTS (SELECT 1 FROM purge_authorization WHERE target_table = 'correction_history' AND target_id = OLD.id AND tenant_id = OLD.tenant_id)
BEGIN SELECT RAISE(ABORT, 'I6 append-only: correction_history'); END;

CREATE TABLE scope_history (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  seq_from INTEGER NOT NULL,
  seq_to INTEGER NOT NULL,
  snapshot TEXT NOT NULL CHECK (json_valid(snapshot)),
  PRIMARY KEY (tenant_id, id, seq_from),
  CHECK (seq_to > seq_from)
);
CREATE INDEX scope_history_range ON scope_history (id, seq_from, seq_to);
CREATE TRIGGER scope_history_no_update BEFORE UPDATE ON scope_history
WHEN NOT EXISTS (SELECT 1 FROM purge_authorization WHERE target_table = 'scope_history' AND target_id = OLD.id AND tenant_id = OLD.tenant_id)
BEGIN SELECT RAISE(ABORT, 'I6 append-only: scope_history'); END;
CREATE TRIGGER scope_history_no_delete BEFORE DELETE ON scope_history
WHEN NOT EXISTS (SELECT 1 FROM purge_authorization WHERE target_table = 'scope_history' AND target_id = OLD.id AND tenant_id = OLD.tenant_id)
BEGIN SELECT RAISE(ABORT, 'I6 append-only: scope_history'); END;

CREATE TABLE topic_history (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  seq_from INTEGER NOT NULL,
  seq_to INTEGER NOT NULL,
  snapshot TEXT NOT NULL CHECK (json_valid(snapshot)),
  PRIMARY KEY (tenant_id, id, seq_from),
  CHECK (seq_to > seq_from)
);
CREATE INDEX topic_history_range ON topic_history (id, seq_from, seq_to);
CREATE TRIGGER topic_history_no_update BEFORE UPDATE ON topic_history
WHEN NOT EXISTS (SELECT 1 FROM purge_authorization WHERE target_table = 'topic_history' AND target_id = OLD.id AND tenant_id = OLD.tenant_id)
BEGIN SELECT RAISE(ABORT, 'I6 append-only: topic_history'); END;
CREATE TRIGGER topic_history_no_delete BEFORE DELETE ON topic_history
WHEN NOT EXISTS (SELECT 1 FROM purge_authorization WHERE target_table = 'topic_history' AND target_id = OLD.id AND tenant_id = OLD.tenant_id)
BEGIN SELECT RAISE(ABORT, 'I6 append-only: topic_history'); END;

CREATE TABLE placement_history (
  tenant_id TEXT NOT NULL DEFAULT 'local',
  id TEXT NOT NULL,
  seq_from INTEGER NOT NULL,
  seq_to INTEGER NOT NULL,
  snapshot TEXT NOT NULL CHECK (json_valid(snapshot)),
  PRIMARY KEY (tenant_id, id, seq_from),
  CHECK (seq_to > seq_from)
);
CREATE INDEX placement_history_range ON placement_history (id, seq_from, seq_to);
CREATE TRIGGER placement_history_no_update BEFORE UPDATE ON placement_history
WHEN NOT EXISTS (SELECT 1 FROM purge_authorization WHERE target_table = 'placement_history' AND target_id = OLD.id AND tenant_id = OLD.tenant_id)
BEGIN SELECT RAISE(ABORT, 'I6 append-only: placement_history'); END;
CREATE TRIGGER placement_history_no_delete BEFORE DELETE ON placement_history
WHEN NOT EXISTS (SELECT 1 FROM purge_authorization WHERE target_table = 'placement_history' AND target_id = OLD.id AND tenant_id = OLD.tenant_id)
BEGIN SELECT RAISE(ABORT, 'I6 append-only: placement_history'); END;
