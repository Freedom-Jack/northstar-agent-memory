"""The six schema files: tables, tenant_id, enumerated CHECKs, append-only triggers and FTS5 (MEMORY-ARCHITECTURE §2.2-§2.12)."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import get_args

import pytest

from northstar_agent_memory import transcript
from northstar_agent_memory.core import db, events

NOW = "2026-03-02T09:30:00.000Z"

EXPECTED_TABLES = {
    "history": {"source", "message", "work_event", "blob", "reconciliation", "purge_authorization"},
    "memory": {
        "event", "event_subject", "purge_authorization", "item", "evidence", "link", "supersession", "conflict",
        "work", "style_line", "correction", "scope", "stance", "topic", "placement",
    },
    "working": {"work_thread", "session", "live_decision", "version", "version_feedback", "side_topic", "receipt"},
    "index": {
        "item_line", "item_filtered", "keys", "vectors", "history_keys", "history_vectors", "link_view", "goal_card",
        "start_note", "use", "gate_bar", "gate_bar_move",
    },
    "overview": {
        "topic_view", "idea_view", "suggestion", "open_item", "left_off", "layout", "layout_meta", "mark", "topic_mark",
    },
    "runs": {"run", "job", "model_call", "proposal", "verdict", "quarantine", "budget", "change_log"},
}
CURRENT_STATE = ("item", "evidence", "link", "supersession", "conflict", "work", "style_line", "correction", "scope", "topic", "placement")
EXPECTED_TABLES["memory"] |= {f"{t}_history" for t in CURRENT_STATE}


def tables_of(conn):
    rows = conn.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
    return {r["name"]: r["sql"] for r in rows}


def real_tables(conn):
    """Tables without the shadow tables FTS5 adds."""
    found = tables_of(conn)
    virtual = [n for n, sql in found.items() if sql.upper().startswith("CREATE VIRTUAL")]
    return {n for n in found if not any(n.startswith(v + "_") for v in virtual) and n != "schema_version"}


def refused(conn, sql, params=(), *, match=None):
    """The statement is refused by a constraint or a trigger."""
    with pytest.raises(sqlite3.IntegrityError, match=match):
        conn.execute(sql, params)


# --- shape ---------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", db.STORES)
def test_each_store_has_the_expected_tables(open_all, name):
    assert real_tables(open_all[name]) == EXPECTED_TABLES[name]


@pytest.mark.parametrize("name", db.STORES)
def test_every_table_carries_tenant_id_defaulting_to_local(open_all, name):
    conn = open_all[name]
    for table in real_tables(conn):
        columns = {r["name"]: r for r in conn.execute(f"PRAGMA table_info({table})")}
        assert "tenant_id" in columns, f"{name}.{table} has no tenant_id"
        if "VIRTUAL" not in tables_of(conn)[table].upper():
            assert columns["tenant_id"]["notnull"] == 1 and "local" in columns["tenant_id"]["dflt_value"]
    tenants = conn.execute("SELECT tenant_id FROM schema_version").fetchall()
    assert [r[0] for r in tenants] == ["local"]


def test_memory_has_a_history_table_for_each_current_state_table(memory):
    for table in CURRENT_STATE:
        columns = [r["name"] for r in memory.execute(f"PRAGMA table_info({table}_history)")]
        assert {"id", "seq_from", "seq_to", "snapshot"} <= set(columns)
        assert "seq_from" in [r["name"] for r in memory.execute(f"PRAGMA table_info({table})")]
    assert "version" in [r["name"] for r in memory.execute("PRAGMA table_info(item_history)")]


# --- every enumerated field has a CHECK that matches the Python enums --------------------------------------------


def check_values(conn, table, column):
    sql = tables_of(conn)[table]
    match = re.search(rf"CHECK\s*\(\s*{column}\s+IN\s*\(([^)]*)\)\s*\)", sql)
    assert match, f"{table}.{column} has no IN check"
    return tuple(v.strip().strip("'") for v in match.group(1).split(","))


MESSAGE_ENUMS = [
    ("history", "source", "kind", get_args(transcript.SourceKind)),
    ("history", "source", "sensitivity", ("normal", "sensitive", "private")),
    ("history", "message", "speaker", get_args(transcript.Speaker)),
    ("history", "message", "origin", get_args(transcript.Origin)),
    ("history", "message", "fidelity", ("verbatim", "model_reported", "reconciled")),
    ("history", "work_event", "kind", events.WORK_KINDS),
    ("history", "work_event", "evidence", events.WORK_EVIDENCE),
    ("history", "reconciliation", "method", ("hash", "tag", "fuzzy", "none")),
    ("history", "reconciliation", "outcome", ("matched", "reported_only", "could_not_confirm")),
    ("memory", "event", "type", events.EVENT_TYPES),
    ("memory", "item", "kind", events.ITEM_KINDS),
    ("memory", "item", "class", events.ITEM_CLASSES),
    ("memory", "item", "value", events.ITEM_VALUES),
    ("memory", "item", "status", events.ITEM_STATUSES),
    ("memory", "item", "check_status", events.CHECK_STATUSES),
    ("memory", "item", "goal_basis", events.GOAL_BASES),
    ("memory", "item", "goal_status", events.GOAL_STATUSES),
    ("memory", "item", "raised_by", events.QUESTION_RAISED_BY),
    ("memory", "item", "question_status", events.QUESTION_STATUSES),
    ("memory", "evidence", "subject_kind", events.EVIDENCE_SUBJECT_KINDS),
    ("memory", "evidence", "role", events.EVIDENCE_ROLES),
    ("memory", "evidence", "speaker", get_args(transcript.Speaker)),
    ("memory", "evidence", "origin", get_args(transcript.Origin)),
    ("memory", "evidence", "lineage", events.LINEAGES),
    ("memory", "link", "type", events.LINK_TYPES),
    ("memory", "link", "stated_by", events.LINK_STATED_BY),
    ("memory", "link", "status", events.LINK_STATUSES),
    ("memory", "link", "to_kind", events.LINK_TO_KINDS),
    ("memory", "supersession", "reason", events.SUPERSESSION_REASONS),
    ("memory", "supersession", "status", events.SUPERSESSION_STATUSES),
    ("memory", "conflict", "kind", events.CONFLICT_KINDS),
    ("memory", "conflict", "state", events.CONFLICT_STATES),
    ("memory", "work", "kind", events.WORK_KINDS),
    ("memory", "work", "evidence", events.WORK_EVIDENCE),
    ("memory", "work", "label_source", events.WORK_LABEL_SOURCES),
    ("memory", "style_line", "basis", events.STYLE_BASES),
    ("memory", "style_line", "status", events.STYLE_STATUSES),
    ("memory", "correction", "kind", events.CORRECTION_KINDS),
    ("memory", "correction", "via", events.CORRECTION_VIA),
    ("memory", "correction", "status", events.CORRECTION_STATUSES),
    ("memory", "correction", "lifted_reason", events.CORRECTION_LIFTED_REASONS),
    ("memory", "scope", "kind", events.SCOPE_KINDS),
    ("memory", "stance", "stance", events.STANCES),
    ("memory", "topic", "status", events.TOPIC_STATUSES),
    ("memory", "placement", "role", events.PLACEMENT_ROLES),
    ("working", "work_thread", "status", ("active", "paused", "closed")),
    ("working", "work_thread", "goal_basis", ("stated", "reused")),
    ("working", "live_decision", "kind", ("decided", "ruled_out", "constraint")),
    ("working", "live_decision", "status", ("live", "in_memory", "dropped")),
    ("working", "version", "artifact_kind", ("git_ref", "render", "file")),
    ("working", "side_topic", "status", ("open", "split_off", "closed")),
    ("working", "receipt", "kind", ("start_note", "facts", "refill", "focus_note", "recall")),
    ("index", "item_line", "kind", events.ITEM_KINDS),
    ("index", "item_line", "class", events.ITEM_CLASSES),
    ("index", "item_line", "status", events.ITEM_STATUSES),
    ("index", "item_line", "value", events.ITEM_VALUES),
    ("index", "item_line", "check_status", events.CHECK_STATUSES),
    ("index", "vectors", "field", ("line", "question_key")),
    ("index", "link_view", "type", events.LINK_TYPES),
    ("index", "link_view", "strength", ("stated_or_confirmed", "construction", "checked")),
    ("index", "use", "kind", ("delivered", "recalled", "viewed", "built_on")),
    ("index", "gate_bar_move", "direction", ("lower", "raise")),
    ("index", "gate_bar_move", "reason", ("re_explanation", "presumption", "leak")),
    ("overview", "suggestion", "type", events.LINK_TYPES),
    ("overview", "suggestion", "status", ("waiting", "confirmed", "rejected")),
    ("overview", "open_item", "kind", ("open_question", "open_conflict", "active_goal", "next_step", "goal_gap")),
    ("overview", "layout", "node_kind", ("topic", "entry")),
    ("runs", "run", "trigger", ("idle", "nightly", "weekly", "manual")),
    ("runs", "run", "state", ("queued", "running", "held", "applied", "failed", "cancelled", "undone")),
    ("runs", "job", "stage", ("trigger", "replay", "extract", "integrate", "refresh", "check", "weekly", "rebuild", "log")),
    ("runs", "job", "state", ("queued", "leased", "running", "done", "failed", "quarantined", "cancelled")),
    ("runs", "model_call", "status", ("ok", "error", "timeout")),
    ("runs", "proposal", "risk_tier", events.RISK_TIERS),
    ("runs", "proposal", "state", ("pending", "applied", "rejected", "quarantined", "requeued")),
    ("runs", "verdict", "outcome", ("pass", "fail")),
    ("runs", "quarantine", "target_kind", ("proposal", "item", "link")),
    ("runs", "quarantine", "state", ("open", "exited")),
    ("runs", "quarantine", "exit", ("fresh_call", "re_extracted", "discarded", "applied")),
]


@pytest.mark.parametrize(("store", "table", "column", "expected"), MESSAGE_ENUMS, ids=lambda v: v if isinstance(v, str) else "")
def test_enumerated_check_matches_the_enum(open_all, store, table, column, expected):
    assert set(check_values(open_all[store], table, column)) == set(expected)


def test_the_42_event_types_in_the_check_are_the_42_in_events(memory):
    assert tuple(check_values(memory, "event", "type")) == events.EVENT_TYPES


def test_transcript_records_fit_history_check(history):
    """Every Source.kind, Speaker and Origin the harness knows can be stored."""
    for i, kind in enumerate(get_args(transcript.SourceKind)):
        history.execute("INSERT INTO source (id, kind, scope, created_at) VALUES (?, ?, 'personal', ?)", (f"s{i}", kind, NOW))


# --- history ----------------------------------------------------------------------------------------------------


def add_source(h, sid="s1", scope="project:energy-dash"):
    h.execute("INSERT INTO source (id, kind, app, project, scope, created_at) VALUES (?, 'chat', 'claude-code', 'energy-dash', ?, ?)", (sid, scope, NOW))


def add_message(h, mid="s1:0", sid="s1", ordinal=0, speaker="user", origin="typed", text="Store readings in SQLite."):
    h.execute(
        "INSERT INTO message (id, source_id, ordinal, speaker, origin, text, content_hash, recorded_at)"
        " VALUES (?, ?, ?, ?, ?, ?, 'h', ?)",
        (mid, sid, ordinal, speaker, origin, text, NOW),
    )


def authorize(conn, table, target_id, purge_id="purge-1"):
    conn.execute(
        "INSERT INTO purge_authorization (purge_id, target_table, target_id, authorized_at) VALUES (?, ?, ?, ?)",
        (purge_id, table, target_id, NOW),
    )


def test_history_rejects_bad_enum_values(history):
    add_source(history)
    refused(history, "INSERT INTO source (id, kind, scope, created_at) VALUES ('x', 'dream', 'personal', ?)", (NOW,))
    refused(history, "INSERT INTO source (id, kind, scope, created_at) VALUES ('x', 'chat', 'everywhere', ?)", (NOW,))
    refused(history, "INSERT INTO source (id, kind, scope, sensitivity, created_at) VALUES ('x', 'chat', 'personal', 'secret', ?)", (NOW,))
    with pytest.raises(sqlite3.IntegrityError):
        add_message(history, speaker="robot")
    with pytest.raises(sqlite3.IntegrityError):
        add_message(history, origin="dreamed")
    refused(history, "UPDATE source SET kind='nope' WHERE id='s1'")
    add_message(history)
    refused(
        history,
        "INSERT INTO message (id, source_id, ordinal, speaker, origin, text, content_hash, fidelity, recorded_at)"
        " VALUES ('s1:1', 's1', 1, 'user', 'typed', 't', 'h', 'guessed', ?)",
        (NOW,),
    )
    refused(
        history,
        "INSERT INTO work_event (id, source_id, kind, ref, evidence, recorded_at) VALUES ('w', 's1', 'commit', 'abc', 'certain', ?)",
        (NOW,),
    )


def test_history_requires_a_scope_and_a_source_for_each_message(history):
    refused(history, "INSERT INTO source (id, kind, created_at) VALUES ('x', 'chat', ?)", (NOW,))
    with pytest.raises(sqlite3.IntegrityError):
        add_message(history)  # no source s1


def test_a_message_keeps_its_slot_once(history):
    add_source(history)
    add_message(history)
    with pytest.raises(sqlite3.IntegrityError):
        add_message(history, mid="s1:0b")  # same source, branch, ordinal and speaker
    add_message(history, mid="s1:0a", speaker="assistant", origin="assistant_output")


def test_message_and_work_event_refuse_update_and_delete(history):
    add_source(history)
    add_message(history)
    history.execute(
        "INSERT INTO work_event (id, source_id, kind, ref, evidence, recorded_at) VALUES ('w1', 's1', 'commit', 'a41c9e0', 'medium', ?)",
        (NOW,),
    )
    refused(history, "UPDATE message SET meta='{}' WHERE id='s1:0'", match="append-only")
    refused(history, "DELETE FROM message WHERE id='s1:0'", match="append-only")
    refused(history, "UPDATE work_event SET evidence='strong' WHERE id='w1'")
    refused(history, "DELETE FROM work_event WHERE id='w1'", match="append-only")
    assert history.execute("SELECT COUNT(*) FROM message").fetchone()[0] == 1


@pytest.mark.parametrize("column", ["speaker", "origin", "text", "agent", "model_family", "content_hash"])
def test_speaker_origin_and_text_never_change(history, column):
    add_source(history)
    add_message(history)
    authorize(history, "message", "s1:0")  # even a purge does not rewrite them (I3, I20)
    refused(history, f"UPDATE message SET {column}='changed' WHERE id='s1:0'", match="never change")


def test_a_purge_authorized_delete_is_allowed(history):
    add_source(history)
    add_message(history)
    add_message(history, mid="s1:1", ordinal=1, speaker="assistant", origin="assistant_output")
    authorize(history, "message", "s1:0")
    history.execute("DELETE FROM message WHERE id='s1:0'")
    assert [r[0] for r in history.execute("SELECT id FROM message")] == ["s1:1"]
    refused(history, "DELETE FROM message WHERE id='s1:1'", match="append-only")  # only the named row


def test_a_purge_authorization_for_another_table_does_not_open_a_row(history):
    add_source(history)
    add_message(history)
    authorize(history, "work_event", "s1:0")
    refused(history, "DELETE FROM message WHERE id='s1:0'", match="append-only")


def test_a_purge_authorized_update_of_other_columns_is_allowed(history):
    add_source(history)
    add_message(history)
    refused(history, "UPDATE message SET meta='{\"x\":1}' WHERE id='s1:0'")
    authorize(history, "message", "s1:0")
    history.execute("UPDATE message SET meta='{\"x\":1}' WHERE id='s1:0'")


def test_blobs_and_authorizations_are_append_only(history):
    sha = "a" * 64
    history.execute("INSERT INTO blob (sha256, size, created_at) VALUES (?, 3, ?)", (sha, NOW))
    refused(history, "UPDATE blob SET size=4 WHERE sha256=?", (sha,))
    refused(history, "DELETE FROM blob WHERE sha256=?", (sha,))
    authorize(history, "blob", sha)
    history.execute("DELETE FROM blob WHERE sha256=?", (sha,))
    refused(history, "UPDATE purge_authorization SET target_id='x'")
    refused(history, "DELETE FROM purge_authorization")
    refused(history, "INSERT INTO blob (sha256, size, created_at) VALUES ('short', 1, ?)", (NOW,))


def test_a_work_event_may_point_to_a_blob_only_if_it_exists(history):
    add_source(history)
    refused(
        history,
        "INSERT INTO work_event (id, source_id, kind, ref, evidence, snapshot_sha256, recorded_at)"
        " VALUES ('w', 's1', 'render', 'r', 'weak', ?, ?)",
        ("b" * 64, NOW),
    )


def test_reconciliation_records_every_outcome(history):
    add_source(history)
    add_message(history, origin="model_reported")
    history.execute(
        "INSERT INTO reconciliation (id, reported_message_id, method, outcome, recorded_at) VALUES ('r1', 's1:0', 'none', 'reported_only', ?)",
        (NOW,),
    )
    refused(
        history,
        "INSERT INTO reconciliation (id, reported_message_id, method, outcome, recorded_at) VALUES ('r2', 's1:0', 'hash', 'matched', ?)",
        (NOW,),
    )  # a match names the word-for-word message
    refused(history, "UPDATE reconciliation SET score=1 WHERE id='r1'")


# --- memory -----------------------------------------------------------------------------------------------------


def add_event(m, eid, type_="item.created", *, run_id=None, proposal_id=None, index=None, actor="code:test", payload="{}"):
    m.execute(
        "INSERT INTO event (id, type, subjects, payload, actor, run_id, proposal_id, index_in_proposal, config_version, recorded_at)"
        " VALUES (?, ?, '[\"m1\"]', ?, ?, ?, ?, ?, 'cfg', ?)",
        (eid, type_, payload, actor, run_id, proposal_id, index, NOW),
    )


def add_item(m, iid="m1", *, kind="decision", cls="fact", scope="project:energy-dash", origin="yours", seq=1, **extra):
    columns = dict(
        id=iid, kind=kind, **{"class": cls}, line="Readings are stored in SQLite", scope=scope, learned_in="A", origin=origin,
        said_at=NOW, recorded_at=NOW, created_seq=seq, seq_from=seq,
    )
    columns.update(extra)
    names = ", ".join(f'"{c}"' for c in columns)
    m.execute(f"INSERT INTO item ({names}) VALUES ({', '.join('?' for _ in columns)})", tuple(columns.values()))


def test_events_get_increasing_seq_and_unique_ids(memory):
    add_event(memory, "e1")
    add_event(memory, "e2")
    assert [r[0] for r in memory.execute("SELECT seq FROM event ORDER BY seq")] == [1, 2]
    with pytest.raises(sqlite3.IntegrityError):
        add_event(memory, "e1")


def test_seq_is_never_reused_after_a_purge_delete(memory):
    add_event(memory, "e1")
    authorize(memory, "event", "e1")
    memory.execute("DELETE FROM event WHERE id='e1'")
    add_event(memory, "e2")
    assert memory.execute("SELECT seq FROM event WHERE id='e2'").fetchone()[0] == 2


def test_an_unknown_event_type_or_actor_is_refused(memory):
    with pytest.raises(sqlite3.IntegrityError):
        add_event(memory, "e1", "item.imagined")
    with pytest.raises(sqlite3.IntegrityError):
        add_event(memory, "e1", actor="somebody")
    with pytest.raises(sqlite3.IntegrityError):
        add_event(memory, "e1", payload="not json")
    add_event(memory, "e1", actor="user")
    add_event(memory, "e2", actor="model:claude-test@1#9f2c")


def test_replaying_a_run_cannot_apply_twice(memory):
    add_event(memory, "e1", run_id="r1", proposal_id="p1", index=0)
    add_event(memory, "e2", run_id="r1", proposal_id="p1", index=1)
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        add_event(memory, "e3", run_id="r1", proposal_id="p1", index=0)  # I14
    add_event(memory, "e4", run_id="r2", proposal_id="p1", index=0)


def test_a_proposal_index_comes_with_its_proposal_and_run(memory):
    with pytest.raises(sqlite3.IntegrityError):
        add_event(memory, "e1", run_id="r1", proposal_id="p1", index=None)
    with pytest.raises(sqlite3.IntegrityError):
        add_event(memory, "e1", run_id=None, proposal_id="p1", index=0)


def test_event_log_is_append_only_unless_a_purge_names_the_event(memory):
    add_event(memory, "e1")
    add_event(memory, "e2")
    refused(memory, "UPDATE event SET payload='{\"a\":1}' WHERE id='e1'", match="append-only")
    refused(memory, "DELETE FROM event WHERE id='e1'", match="append-only")
    authorize(memory, "event", "e1")
    memory.execute("UPDATE event SET payload='{\"scrubbed\":true}' WHERE id='e1'")
    refused(memory, "UPDATE event SET type='item.revised' WHERE id='e1'", match="never changes")
    refused(memory, "UPDATE event SET seq=99 WHERE id='e1'", match="never changes")
    memory.execute("DELETE FROM event WHERE id='e1'")
    refused(memory, "DELETE FROM event WHERE id='e2'", match="append-only")


def test_a_compensating_event_must_name_an_existing_event(memory):
    add_event(memory, "e1")
    memory.execute(
        "INSERT INTO event (id, type, subjects, payload, actor, compensates, config_version, recorded_at)"
        " VALUES ('e2', 'supersession.undone', '[]', '{}', 'code:t', 'e1', 'c', ?)",
        (NOW,),
    )
    refused(
        memory,
        "INSERT INTO event (id, type, subjects, payload, actor, compensates, config_version, recorded_at)"
        " VALUES ('e3', 'supersession.undone', '[]', '{}', 'code:t', 'nope', 'c', ?)",
        (NOW,),
    )


def test_item_enums_and_class_rule(memory):
    add_item(memory)
    for column, bad in [("kind", "idea"), ("value", "gold"), ("status", "deleted"), ("check_status", "maybe")]:
        with pytest.raises(sqlite3.IntegrityError):
            add_item(memory, "bad", **{column: bad})
    with pytest.raises(sqlite3.IntegrityError):
        add_item(memory, "bad", cls="opinion")
    with pytest.raises(sqlite3.IntegrityError):
        add_item(memory, "bad", origin="the model")
    with pytest.raises(sqlite3.IntegrityError):
        add_item(memory, "bad", scope="everywhere")
    with pytest.raises(sqlite3.IntegrityError):
        add_item(memory, "bad", scope="session:abc")  # an item's scope is personal, project or work
    with pytest.raises(sqlite3.IntegrityError):
        add_item(memory, "bad", kind="principle", cls="fact")  # a view kind is never a fact
    add_item(memory, "ok", kind="decision", cls="view")  # when unsure, view
    add_item(memory, "ok2", kind="principle", cls="view", scope="personal", origin="adopted:claude-code")
    assert memory.execute("SELECT value, status, check_status, version FROM item WHERE id='m1'").fetchone()[:] == (
        "forming", "active", "not_needed", 1,
    )


def test_goals_and_questions_carry_their_own_state(memory):
    add_item(memory, "g1", kind="goal", cls="view", goal_basis="stated", goal_status="active", work_id="T2")
    add_item(memory, "q1", kind="question", cls="view", raised_by="you", question_status="open")
    with pytest.raises(sqlite3.IntegrityError):
        add_item(memory, "g2", kind="goal", cls="view")  # a goal has a basis and a status
    with pytest.raises(sqlite3.IntegrityError):
        add_item(memory, "g3", kind="goal", cls="view", goal_basis="inferred", goal_status="active")
    with pytest.raises(sqlite3.IntegrityError):
        add_item(memory, "d1", goal_basis="stated", goal_status="active")  # only goals have goal fields
    with pytest.raises(sqlite3.IntegrityError):
        add_item(memory, "q2", kind="question", cls="view", raised_by="northstar", question_status="open")
    with pytest.raises(sqlite3.IntegrityError):
        add_item(memory, "d2", question_status="open")


def test_evidence_before_its_item_in_one_transaction(memory):
    """§6.2 appends the evidence before item.created; foreign keys are checked at COMMIT."""
    with db.transaction(memory):
        memory.execute(
            "INSERT INTO link (id, from_id, to_id, type, reason, stated_by, status, created_seq, seq_from)"
            " VALUES ('l1', 'm2', 'm1', 'supports', 'because', 'northstar', 'applied', 1, 1)"
        )
        add_item(memory, "m1")
        add_item(memory, "m2")
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        with db.transaction(memory):
            memory.execute(
                "INSERT INTO link (id, from_id, to_id, type, reason, stated_by, status, created_seq, seq_from)"
                " VALUES ('l2', 'ghost', 'm1', 'supports', 'because', 'northstar', 'applied', 2, 2)"
            )
    assert memory.execute("SELECT COUNT(*) FROM link").fetchone()[0] == 1


def add_evidence(m, eid="ev1", subject="m1", **extra):
    columns = dict(
        id=eid, subject_kind="item", subject_id=subject, message_id="A1", start_char=0, end_char=5, quote="Store",
        role="primary", speaker="user", origin="typed", created_seq=1, seq_from=1,
    )
    columns.update(extra)
    m.execute(f"INSERT INTO evidence ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})", tuple(columns.values()))


def test_evidence_is_frozen_once_anchored(memory):
    add_evidence(memory)
    for column in ["quote", "speaker", "origin", "agent", "model_family", "message_id", "start_char", "lineage"]:
        refused(memory, f"UPDATE evidence SET {column}=? WHERE id='ev1'", ("x" if column != "start_char" else 1,), match="frozen")
    memory.execute("UPDATE evidence SET subject_id='m2', seq_from=5 WHERE id='ev1'")  # a merge moves it
    authorize(memory, "evidence", "ev1")
    memory.execute("UPDATE evidence SET quote='[removed]' WHERE id='ev1'")  # a purge scrubs it


def test_evidence_enums_and_span(memory):
    for bad in [dict(role="proof"), dict(speaker="model"), dict(origin="guess"), dict(lineage="echo"), dict(subject_kind="topic"),
                dict(start_char=5, end_char=5), dict(start_char=-1)]:
        with pytest.raises(sqlite3.IntegrityError):
            add_evidence(memory, **bad)
    add_evidence(memory, lineage="northstar_echo", role="adoption", speaker="assistant", origin="assistant_output")


def test_link_rules(memory):
    add_item(memory, "m1")
    add_item(memory, "m2")

    def add_link(lid, **kw):
        columns = dict(id=lid, from_id="m1", to_id="m2", type="supports", reason="r", stated_by="you", status="applied", created_seq=1, seq_from=1)
        columns.update(kw)
        memory.execute(f"INSERT INTO link ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})", tuple(columns.values()))

    add_link("ok")
    add_link("work", type="used_in", to_id="w1", to_kind="work")
    add_link("self_case", type="advances", to_id="m2")
    for bad in [dict(type="causes"), dict(stated_by="model"), dict(status="seen"), dict(to_id="m1"),
                dict(type="used_in"), dict(to_kind="work"), dict(to_kind="idea"), dict(checked_by="x")]:
        with pytest.raises(sqlite3.IntegrityError):
            add_link("bad", **bad)


def test_supersession_conflict_work_style_correction_scope_enums(memory):
    add_item(memory, "m1")
    add_item(memory, "m2")

    def insert(table, **columns):
        memory.execute(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})", tuple(columns.values()))

    sup = dict(id="s1", old_item="m1", old_version=1, new_item="m2", reason="refresh", at=NOW, created_seq=1, seq_from=1)
    insert("supersession", **sup)
    for bad in [dict(reason="mood"), dict(status="deleted")]:
        with pytest.raises(sqlite3.IntegrityError):
            insert("supersession", **{**sup, "id": "s2", **bad})

    con = dict(id="c1", side_a_item="m1", side_a_version=1, side_b_item="m2", side_b_version=1, kind="across_contexts", state="both_stand", created_seq=1, seq_from=1)
    insert("conflict", **con)
    for bad in [dict(kind="far"), dict(state="won"), dict(side_b_item="m1"), dict(resolution="{bad json")]:
        with pytest.raises(sqlite3.IntegrityError):
            insert("conflict", **{**con, "id": "c2", **bad})
    insert("conflict", **{**con, "id": "c3", "state": "undone"})

    work = dict(id="w1", kind="commit", ref="a41c9e0", evidence="medium", created_seq=1, seq_from=1)
    insert("work", **work)
    for bad in [dict(kind="email"), dict(evidence="certain"), dict(label_source="guess")]:
        with pytest.raises(sqlite3.IntegrityError):
            insert("work", **{**work, "id": "w2", **bad})

    style = dict(id="st1", line="short answers", scope="personal", basis="stated_default", created_seq=1, seq_from=1)
    insert("style_line", **style)
    for bad in [dict(basis="guess"), dict(status="gone"), dict(scope="nowhere")]:
        with pytest.raises(sqlite3.IntegrityError):
            insert("style_line", **{**style, "id": "st2", **bad})


def test_correction_rules(memory):
    base = dict(id="co1", kind="pin", target="m1", via="click", at=NOW, created_seq=1, seq_from=1)

    def insert(**kw):
        columns = {**base, **kw}
        memory.execute(f"INSERT INTO correction ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})", tuple(columns.values()))

    insert()
    insert(id="co2", kind="not_what_i_think", via="typed", evidence_id="ev1")
    with pytest.raises(sqlite3.IntegrityError):
        insert(id="co3", via="typed")  # I5: typed corrections cite your words
    with pytest.raises(sqlite3.IntegrityError):
        insert(id="co4", kind="forget")
    with pytest.raises(sqlite3.IntegrityError):
        insert(id="co5", status="lifted")  # lifted needs a reason
    with pytest.raises(sqlite3.IntegrityError):
        insert(id="co6", status="lifted", lifted_reason="more evidence")  # later evidence never lifts one
    insert(id="co7", status="lifted", lifted_reason="your_undo")


def test_scope_rows(memory):
    memory.execute("INSERT INTO scope (id, kind, created_seq, seq_from) VALUES ('personal', 'personal', 1, 1)")
    memory.execute("INSERT INTO scope (id, kind, held, held_seq, created_seq, seq_from) VALUES ('project:energy-dash', 'project', 1, 2, 1, 2)")
    for sql in [
        "INSERT INTO scope (id, kind, created_seq, seq_from) VALUES ('project:x', 'work', 1, 1)",
        "INSERT INTO scope (id, kind, created_seq, seq_from) VALUES ('team:x', 'team', 1, 1)",
        "INSERT INTO scope (id, kind, created_seq, seq_from) VALUES ('project:y', 'project', 1, 1), ('project:z', 'personal', 1, 1)",
        "INSERT INTO scope (id, kind, held, created_seq, seq_from) VALUES ('work:acme', 'work', 1, 1, 1)",  # held needs held_seq
    ]:
        with pytest.raises(sqlite3.IntegrityError):
            memory.execute(sql)


def add_topic(m, tid, parent=None, status="active", redirect=None):
    m.execute(
        "INSERT INTO topic (id, label, parent_id, status, redirect_to, created_seq, seq_from) VALUES (?, ?, ?, ?, ?, 1, 1)",
        (tid, tid, parent, status, redirect),
    )


def test_topics_have_two_levels_and_stable_ids(memory):
    add_topic(memory, "t1")
    add_topic(memory, "t2", parent="t1")
    with pytest.raises(sqlite3.IntegrityError, match="two levels"):
        add_topic(memory, "t3", parent="t2")
    add_topic(memory, "t4")
    refused(memory, "UPDATE topic SET parent_id='t2' WHERE id='t4'", match="two levels")
    memory.execute("UPDATE topic SET parent_id='t1' WHERE id='t4'")
    with pytest.raises(sqlite3.IntegrityError):
        add_topic(memory, "t5", status="dissolved")
    with pytest.raises(sqlite3.IntegrityError):
        add_topic(memory, "t6", status="merged_into")  # a retired topic says where it went
    add_topic(memory, "t7", status="merged_into", redirect="t1")
    with pytest.raises(sqlite3.IntegrityError):
        add_topic(memory, "t8", redirect="t1")  # only a retired topic redirects
    with pytest.raises(sqlite3.IntegrityError):
        add_topic(memory, "t1")  # ids are never reused


def test_placement_one_home_and_up_to_two_also_in(memory):
    for item in ("m1", "m2"):
        add_item(memory, item)
    for tid in ("t1", "t2", "t3", "t4"):
        add_topic(memory, tid)

    def place(pid, item, topic, role):
        memory.execute(
            "INSERT INTO placement (id, item_id, topic_id, role, created_seq, seq_from) VALUES (?, ?, ?, ?, 1, 1)", (pid, item, topic, role)
        )

    place("p1", "m1", "t1", "home")
    with pytest.raises(sqlite3.IntegrityError):
        place("p2", "m1", "t2", "home")  # every idea has one home
    with pytest.raises(sqlite3.IntegrityError):
        place("p3", "m1", "t1", "also_in")  # one place per topic
    place("p4", "m1", "t2", "also_in")
    place("p5", "m1", "t3", "also_in")
    with pytest.raises(sqlite3.IntegrityError, match="two also_in"):
        place("p6", "m1", "t4", "also_in")
    with pytest.raises(sqlite3.IntegrityError):
        place("p7", "m2", "t1", "somewhere")
    place("p8", "m2", "t1", "home")


def test_stance_is_append_only(memory):
    add_item(memory)
    memory.execute("INSERT INTO stance (id, item_id, stance, evidence_ids, created_seq) VALUES ('st', 'm1', 'adopted', '[\"ev1\"]', 1)")
    with pytest.raises(sqlite3.IntegrityError):
        memory.execute("INSERT INTO stance (id, item_id, stance, evidence_ids, created_seq) VALUES ('st2', 'm1', 'liked', '[]', 1)")
    refused(memory, "UPDATE stance SET stance='stated' WHERE id='st'", match="append-only")
    refused(memory, "DELETE FROM stance WHERE id='st'", match="append-only")


def test_row_history_holds_every_earlier_state(memory):
    """§2.3: archive a row before changing it; 'as of seq N' is the current row if seq_from <= N, else the history row."""
    add_item(memory, "m1", seq=3)
    with db.transaction(memory):
        assert db.archive_row(memory, "item", "m1", 7)
        memory.execute("UPDATE item SET version=2, line='Readings are stored in SQLite, one file per meter', seq_from=7 WHERE id='m1'")
    with db.transaction(memory):
        assert db.archive_row(memory, "item", "m1", 11)
        memory.execute("UPDATE item SET status='superseded', seq_from=11 WHERE id='m1'")
    rows = memory.execute("SELECT id, version, seq_from, seq_to, snapshot FROM item_history ORDER BY seq_from").fetchall()
    assert [(r["version"], r["seq_from"], r["seq_to"]) for r in rows] == [(1, 3, 7), (2, 7, 11)]
    first = json.loads(rows[0]["snapshot"])
    assert first["line"] == "Readings are stored in SQLite" and first["status"] == "active" and first["id"] == "m1"
    as_of = lambda n: memory.execute(  # noqa: E731
        "SELECT json_extract(snapshot, '$.line') FROM item_history WHERE id='m1' AND seq_from <= ? AND ? < seq_to", (n, n)
    ).fetchone()
    assert as_of(5)[0] == "Readings are stored in SQLite"
    assert "one file per meter" in as_of(8)[0]
    assert as_of(11) is None  # from seq 11 the current row is the state
    assert memory.execute("SELECT status FROM item WHERE id='m1'").fetchone()[0] == "superseded"
    assert db.archive_row(memory, "item", "missing", 12) is False


def test_row_history_for_every_current_state_table(memory):
    add_topic(memory, "t1")
    assert db.archive_row(memory, "topic", "t1", 5)
    row = memory.execute("SELECT seq_from, seq_to, json_extract(snapshot, '$.label') FROM topic_history").fetchone()
    assert tuple(row) == (1, 5, "t1")


def test_row_history_is_append_only_and_ordered(memory):
    add_topic(memory, "t1")
    db.archive_row(memory, "topic", "t1", 5)
    refused(memory, "UPDATE topic_history SET snapshot='{}' WHERE id='t1'", match="append-only")
    refused(memory, "DELETE FROM topic_history WHERE id='t1'", match="append-only")
    refused(memory, "INSERT INTO topic_history (id, seq_from, seq_to, snapshot) VALUES ('t1', 9, 9, '{}')")  # seq_to > seq_from
    refused(memory, "INSERT INTO topic_history (id, seq_from, seq_to, snapshot) VALUES ('t1', 1, 6, '{}')")  # one state per seq_from
    authorize(memory, "topic_history", "t1")
    memory.execute("DELETE FROM topic_history WHERE id='t1'")


# --- working ------------------------------------------------------------------------------------------------------


def test_working_enums_and_one_best_version(open_all):
    w = open_all["working"]
    w.execute("INSERT INTO work_thread (id, title, scope, opened_at, last_active) VALUES ('T1', 'alerts', 'project:energy-dash', ?, ?)", (NOW, NOW))
    for bad in [
        "INSERT INTO work_thread (id, title, scope, status, opened_at, last_active) VALUES ('T2', 'x', 'personal', 'done', 'n', 'n')",
        "INSERT INTO work_thread (id, title, scope, opened_at, last_active) VALUES ('T2', 'x', 'galaxy', 'n', 'n')",
        "INSERT INTO work_thread (id, title, scope, goal_text, opened_at, last_active) VALUES ('T2', 'x', 'personal', 'goal', 'n', 'n')",  # a goal has a basis
        "INSERT INTO work_thread (id, title, scope, goal_text, goal_basis, opened_at, last_active) VALUES ('T2', 'x', 'personal', 'goal', 'reported', 'n', 'n')",
    ]:
        with pytest.raises(sqlite3.IntegrityError):
            w.execute(bad)
    w.execute("INSERT INTO version (id, thread_id, artifact, best, created_at) VALUES ('v1', 'T1', 'refs/northstar/v1', 1, ?)", (NOW,))
    w.execute("INSERT INTO version (id, thread_id, artifact, parent_id, created_at) VALUES ('v2', 'T1', 'refs/northstar/v2', 'v1', ?)", (NOW,))
    with pytest.raises(sqlite3.IntegrityError):
        w.execute("UPDATE version SET best=1 WHERE id='v2'")  # one best per thread
    w.execute("UPDATE version SET best=0 WHERE id='v1'")
    w.execute("UPDATE version SET best=1 WHERE id='v2'")
    with pytest.raises(sqlite3.IntegrityError):
        w.execute("INSERT INTO live_decision (id, thread_id, kind, line, your_quote, message_id, created_at) VALUES ('d', 'T1', 'guessed', 'l', 'q', 'm', ?)", (NOW,))
    w.execute("INSERT INTO live_decision (id, thread_id, kind, line, your_quote, message_id, created_at) VALUES ('d', 'T1', 'decided', 'l', 'q', 'm', ?)", (NOW,))
    w.execute("INSERT INTO session (id, app, thread_id, started_at, last_active) VALUES ('S1', 'claude-code', 'T1', ?, ?)", (NOW, NOW))
    w.execute("INSERT INTO receipt (id, session_id, at, kind, text_hash) VALUES ('r1', 'S1', ?, 'facts', 'h')", (NOW,))
    with pytest.raises(sqlite3.IntegrityError):
        w.execute("INSERT INTO receipt (id, session_id, at, kind, text_hash) VALUES ('r2', 'S1', ?, 'whisper', 'h')", (NOW,))
    with pytest.raises(sqlite3.IntegrityError):
        w.execute("INSERT INTO receipt (id, session_id, at, kind, text_hash) VALUES ('r3', 'nope', ?, 'facts', 'h')", (NOW,))
    w.execute("INSERT INTO side_topic (id, thread_id, line) VALUES ('sd', 'T1', 'avoid alert fatigue')")
    with pytest.raises(sqlite3.IntegrityError):
        w.execute("INSERT INTO side_topic (id, thread_id, line, status) VALUES ('sd2', 'T1', 'x', 'lost')")


# --- index ------------------------------------------------------------------------------------------------------


def test_keys_is_an_fts5_table_that_matches_and_ranks(open_all):
    ix = open_all["index"]
    assert "fts5" in tables_of(ix)["keys"].lower()
    ix.execute("INSERT INTO keys (tenant_id, item_id, line, your_words, why, question_key, topic_labels, aliases) VALUES ('local', 'm1', ?, ?, ?, ?, ?, ?)",
               ("Readings are stored in SQLite on the Pi, one file per meter", "one file per meter", "", "where to store readings", "Energy dashboard", ""))
    ix.execute("INSERT INTO keys (tenant_id, item_id, line, your_words, why, question_key, topic_labels, aliases) VALUES ('local', 'm2', ?, '', '', ?, ?, ?)",
               ("Alert when the price is twice the median", "how to avoid alert fatigue", "Price alerts", "alerting"))
    hit = ix.execute("SELECT item_id FROM keys WHERE keys MATCH 'sqlite' ORDER BY bm25(keys)").fetchall()
    assert [r["item_id"] for r in hit] == ["m1"]
    assert [r["item_id"] for r in ix.execute("SELECT item_id FROM keys WHERE keys MATCH 'fatigue'")] == ["m2"]
    assert [r["item_id"] for r in ix.execute("SELECT item_id FROM keys WHERE keys MATCH 'topic_labels:alerts'")] == ["m2"]
    assert [r["item_id"] for r in ix.execute("SELECT item_id FROM keys WHERE keys MATCH 'your_words:meter'")] == ["m1"]
    assert [r["item_id"] for r in ix.execute("SELECT item_id FROM keys WHERE keys MATCH 'cafe'")] == []
    ix.execute("INSERT INTO keys (tenant_id, item_id, line) VALUES ('local', 'm3', 'Un café noir')")
    assert [r["item_id"] for r in ix.execute("SELECT item_id FROM keys WHERE keys MATCH 'cafe'")] == ["m3"]  # diacritics fold
    ix.execute("DELETE FROM keys WHERE item_id='m1'")
    assert [r["item_id"] for r in ix.execute("SELECT item_id FROM keys WHERE keys MATCH 'sqlite'")] == []


def test_history_keys_search_your_words_apart_from_the_reply(open_all):
    ix = open_all["index"]
    assert "fts5" in tables_of(ix)["history_keys"].lower()
    ix.execute(
        "INSERT INTO history_keys (tenant_id, exchange_id, source_id, user_message_id, reply_message_id, occurred_at, your_text, reply_text, item_lines)"
        " VALUES ('local', 'x1', 's1', 's1:0', 's1:1', ?, ?, ?, ?)",
        (NOW, "Store readings in SQLite on the Pi", "You could use InfluxDB instead", "decided by the user: SQLite on the Pi"),
    )
    assert [r["exchange_id"] for r in ix.execute("SELECT exchange_id FROM history_keys WHERE history_keys MATCH 'your_text:sqlite'")] == ["x1"]
    assert [r["exchange_id"] for r in ix.execute("SELECT exchange_id FROM history_keys WHERE history_keys MATCH 'your_text:influxdb'")] == []
    assert [r["exchange_id"] for r in ix.execute("SELECT exchange_id FROM history_keys WHERE history_keys MATCH 'reply_text:influxdb'")] == ["x1"]
    assert [r["source_id"] for r in ix.execute("SELECT source_id FROM history_keys WHERE history_keys MATCH 'pi'")] == ["s1"]


def test_vectors_are_keyed_by_item_and_model_and_sized(open_all):
    ix = open_all["index"]
    vec = bytes(16)  # four float32
    ix.execute("INSERT INTO vectors (item_id, model, field, version, dim, vector, built_at) VALUES ('m1', 'minilm', 'line', 1, 4, ?, ?)", (vec, NOW))
    ix.execute("INSERT INTO vectors (item_id, model, field, version, dim, vector, built_at) VALUES ('m1', 'other', 'line', 1, 4, ?, ?)", (vec, NOW))
    ix.execute("INSERT INTO vectors (item_id, model, field, version, dim, vector, built_at) VALUES ('m1', 'minilm', 'question_key', 1, 4, ?, ?)", (vec, NOW))
    with pytest.raises(sqlite3.IntegrityError):
        ix.execute("INSERT INTO vectors (item_id, model, field, version, dim, vector, built_at) VALUES ('m1', 'minilm', 'line', 2, 4, ?, ?)", (vec, NOW))
    with pytest.raises(sqlite3.IntegrityError):
        ix.execute("INSERT INTO vectors (item_id, model, field, version, dim, vector, built_at) VALUES ('m2', 'minilm', 'line', 1, 4, ?, ?)", (bytes(15), NOW))
    with pytest.raises(sqlite3.IntegrityError):
        ix.execute("INSERT INTO vectors (item_id, model, field, version, dim, vector, built_at) VALUES ('m2', 'minilm', 'gist', 1, 4, ?, ?)", (vec, NOW))
    with pytest.raises(sqlite3.IntegrityError):
        ix.execute("INSERT INTO history_vectors (exchange_id, model, dim, vector, built_at) VALUES ('x1', 'minilm', 4, ?, ?)", (bytes(3), NOW))


def test_index_lines_cards_notes_use_and_bar(open_all):
    ix = open_all["index"]
    ix.execute(
        "INSERT INTO item_line (item_id, version, kind, line_text, class, scope, status, value, check_status, built_at)"
        " VALUES ('m1', 1, 'decision', '2026-03-02 · project energy-dash · decided by the user: SQLite', 'fact', 'project:energy-dash', 'active', 'kept', 'not_needed', ?)",
        (NOW,),
    )
    with pytest.raises(sqlite3.IntegrityError):
        ix.execute(
            "INSERT INTO item_line (item_id, version, kind, line_text, class, scope, status, value, check_status, built_at)"
            " VALUES ('m2', 1, 'decision', 'x', 'fact', 'project:a', 'active', 'forming', 'unsure', ?)",
            (NOW,),
        )
    ix.execute("INSERT INTO item_filtered (item_id, reason) VALUES ('m9', 'held scope')")
    ix.execute("INSERT INTO goal_card (id, thread_id, goal_text, built_at) VALUES ('T2', 'T2', 'alert me when the dryer costs double', ?)", (NOW,))
    with pytest.raises(sqlite3.IntegrityError):
        ix.execute("INSERT INTO goal_card (id, goal_text, built_at) VALUES ('x', 'a goal with no anchor', ?)", (NOW,))
    ix.execute("INSERT INTO start_note (thread_id, text, items, built_at, watermark) VALUES ('T2', 'Earlier work', '[\"m1@1\"]', ?, 1046)", (NOW,))
    ix.execute("INSERT INTO link_view (link_id, from_id, to_id, to_kind, type, strength) VALUES ('l1', 'm10', 'm9', 'item', 'advances', 'construction')")
    for i, (kind, at, ctx) in enumerate([("delivered", "2026-03-03", "c1"), ("delivered", "2026-03-04", "c2"), ("viewed", "2026-03-05", "c1")]):
        ix.execute("INSERT INTO use (id, item_id, kind, at, context) VALUES (?, 'm1', ?, ?, ?)", (f"u{i}", kind, at, ctx))
    with pytest.raises(sqlite3.IntegrityError):
        ix.execute("INSERT INTO use (id, item_id, kind, at, context) VALUES ('u9', 'm1', 'liked', 'x', 'c')")
    s = ix.execute("SELECT * FROM use_summary WHERE item_id='m1'").fetchone()
    assert (s["delivered"], s["recalled"], s["viewed"], s["built_on"], s["contexts"], s["last_at"]) == (2, 0, 1, 0, 2, "2026-03-05")
    ix.execute("INSERT INTO gate_bar (project, bar, floor, updated_at) VALUES ('energy-dash', 0.6, 0.4, ?)", (NOW,))
    with pytest.raises(sqlite3.IntegrityError):
        ix.execute("INSERT INTO gate_bar (project, bar, floor, updated_at) VALUES ('garden', 0.3, 0.4, ?)", (NOW,))  # never below the floor
    ix.execute("INSERT INTO gate_bar_move (id, project, at, direction, reason, bar_before, bar_after) VALUES ('g1', 'energy-dash', ?, 'lower', 're_explanation', 0.7, 0.6)", (NOW,))


# --- overview -----------------------------------------------------------------------------------------------------


def test_overview_tables(open_all):
    o = open_all["overview"]
    o.execute("INSERT INTO topic_view (topic_id, label, built_at) VALUES ('t1', 'Energy dashboard', ?)", (NOW,))
    with pytest.raises(sqlite3.IntegrityError):
        o.execute("INSERT INTO topic_view (topic_id, label, status, built_at) VALUES ('t2', 'x', 'merged', ?)", (NOW,))
    o.execute("INSERT INTO idea_view (item_id, shown_line, shown_is_yours, origin_mark, version, built_at) VALUES ('m1', 'one file per meter', 1, 'yours', 1, ?)", (NOW,))
    o.execute("INSERT INTO suggestion (link_id, from_id, to_id, type, reason, created_at) VALUES ('l1', 'm8', 'm1', 'supports', 'r', ?)", (NOW,))
    with pytest.raises(sqlite3.IntegrityError):
        o.execute("INSERT INTO suggestion (link_id, from_id, to_id, type, reason, status, created_at) VALUES ('l2', 'a', 'b', 'supports', 'r', 'drawn', ?)", (NOW,))
    o.execute("INSERT INTO open_item (id, kind, ref_id, line, built_at) VALUES ('o1', 'open_question', 'm11', 'How do I avoid alert fatigue?', ?)", (NOW,))
    with pytest.raises(sqlite3.IntegrityError):
        o.execute("INSERT INTO open_item (id, kind, ref_id, line, built_at) VALUES ('o2', 'new_term', 'x', 'a term that merely appeared', ?)", (NOW,))
    o.execute("INSERT INTO left_off (thread_id, updated_at) VALUES ('T2', ?)", (NOW,))
    o.execute("INSERT INTO layout (node_id, node_kind, x, y, updated_at) VALUES ('t1', 'topic', 1.0, 2.0, ?)", (NOW,))
    with pytest.raises(sqlite3.IntegrityError):
        o.execute("INSERT INTO layout (node_id, node_kind, x, y, prev_x, updated_at) VALUES ('t2', 'topic', 1.0, 2.0, 1.0, ?)", (NOW,))
    o.execute("INSERT INTO layout_meta (id, seed, updated_at) VALUES (1, 42, ?)", (NOW,))
    with pytest.raises(sqlite3.IntegrityError):
        o.execute("INSERT INTO layout_meta (id, seed, updated_at) VALUES (2, 43, ?)", (NOW,))
    o.execute("INSERT INTO mark (item_id, last_seen_version, seen_at) VALUES ('m1', 1, ?)", (NOW,))
    o.execute("INSERT INTO topic_mark (topic_id, hidden_opens) VALUES ('t1', 2)")
    with pytest.raises(sqlite3.IntegrityError):
        o.execute("INSERT INTO topic_mark (topic_id, hidden_opens) VALUES ('t2', -1)")


# --- runs ----------------------------------------------------------------------------------------------------------


def test_runs_tables(open_all):
    r = open_all["runs"]
    r.execute("INSERT INTO run (id, trigger, started_at) VALUES ('r1', 'idle', ?)", (NOW,))
    with pytest.raises(sqlite3.IntegrityError):
        r.execute("INSERT INTO run (id, trigger, started_at) VALUES ('r2', 'whim', ?)", (NOW,))
    r.execute("INSERT INTO job (id, run_id, stage, idempotency_key, created_at, updated_at) VALUES ('j1', 'r1', 'extract', 'k1', ?, ?)", (NOW, NOW))
    with pytest.raises(sqlite3.IntegrityError):
        r.execute("INSERT INTO job (id, run_id, stage, idempotency_key, created_at, updated_at) VALUES ('j2', 'r1', 'extract', 'k1', ?, ?)", (NOW, NOW))  # same key
    with pytest.raises(sqlite3.IntegrityError):
        r.execute("INSERT INTO job (id, run_id, stage, idempotency_key, created_at, updated_at) VALUES ('j3', 'r1', 'dream', 'k3', ?, ?)", (NOW, NOW))
    r.execute("INSERT INTO model_call (id, run_id, job_id, provider, model, family, prompt_hash, input_ids, called_at) VALUES ('mc1', 'r1', 'j1', 'claude', 'm', 'claude', 'h', '[\"A1\",\"A2\"]', ?)", (NOW,))
    r.execute("INSERT INTO proposal (id, run_id, ops, risk_tier, created_at) VALUES ('p1', 'r1', '[]', 'medium', ?)", (NOW,))
    with pytest.raises(sqlite3.IntegrityError):
        r.execute("INSERT INTO proposal (id, run_id, ops, risk_tier, created_at) VALUES ('p2', 'r1', '[]', 'extreme', ?)", (NOW,))
    r.execute("INSERT INTO verdict (id, proposal_id, checker_family, outcome, independent, at) VALUES ('v1', 'p1', 'openai', 'pass', 1, ?)", (NOW,))
    with pytest.raises(sqlite3.IntegrityError):
        r.execute("INSERT INTO verdict (id, proposal_id, checker_family, outcome, independent, at) VALUES ('v2', 'p1', 'openai', 'maybe', 1, ?)", (NOW,))
    r.execute("INSERT INTO change_log (id, run_id, at, change_type, line) VALUES ('cl1', 'r1', ?, 'supersede', 'Replaced a view')", (NOW,))
    with pytest.raises(sqlite3.IntegrityError):
        r.execute("INSERT INTO change_log (id, run_id, at, change_type, line) VALUES ('cl2', 'nope', ?, 'x', 'x')", (NOW,))


def test_model_calls_keep_input_ids_never_the_assembled_text(open_all):
    columns = {row["name"] for row in open_all["runs"].execute("PRAGMA table_info(model_call)")}
    assert {"input_ids", "prompt_hash", "raw_output"} <= columns
    assert not {c for c in columns if "prompt" in c and c != "prompt_hash"}
    assert not columns & {"input", "input_text", "assembled", "assembled_text", "messages"}


def test_quarantine_has_at_most_three_attempts_and_a_matching_exit(open_all):
    r = open_all["runs"]
    base = "INSERT INTO quarantine (id, target_kind, target_id, reason, attempts, deadline, state, exit, created_at) VALUES (?, 'proposal', 'p1', 'failed', ?, ?, ?, ?, ?)"
    r.execute(base, ("q1", 3, NOW, "open", None, NOW))
    for args in [("q2", 4, NOW, "open", None, NOW), ("q3", 0, NOW, "open", None, NOW), ("q4", 1, NOW, "exited", None, NOW), ("q5", 1, NOW, "open", "discarded", NOW), ("q6", 1, NOW, "exited", "ignored", NOW)]:
        with pytest.raises(sqlite3.IntegrityError):
            r.execute(base, args)
    r.execute(base, ("q7", 2, NOW, "exited", "discarded", NOW))


def test_budget_freezes_with_a_time(open_all):
    r = open_all["runs"]
    r.execute("INSERT INTO budget (change_type, audited_n, audited_errors, audited_error_rate, updated_at) VALUES ('merge', 100, 1, 0.01, ?)", (NOW,))
    with pytest.raises(sqlite3.IntegrityError):
        r.execute("INSERT INTO budget (change_type, audited_n, audited_errors, audited_error_rate, updated_at) VALUES ('supersede', 10, 11, 1.0, ?)", (NOW,))
    with pytest.raises(sqlite3.IntegrityError):
        r.execute("INSERT INTO budget (change_type, audited_error_rate, frozen_at, updated_at) VALUES ('purge', 0, ?, ?)", (NOW, NOW))


# --- tenant_id leads every key ---------------------------------------------------------------------------------------

ROWID_KEYS = {("event", "seq"), ("message", "seq"), ("work_event", "seq")}  # the autoincrement watermarks stay the row id


def primary_key(conn, table):
    columns = sorted((r["pk"], r["name"]) for r in conn.execute(f"PRAGMA table_info({table})") if r["pk"])
    return [name for _, name in columns]


@pytest.mark.parametrize("name", db.STORES)
def test_every_primary_key_and_unique_constraint_starts_with_tenant_id(open_all, name):
    conn = open_all[name]
    for table in real_tables(conn):
        if "VIRTUAL" in tables_of(conn)[table].upper():
            continue
        pk = primary_key(conn, table)
        assert pk, f"{name}.{table} has no primary key"
        if len(pk) == 1 and (table, pk[0]) in ROWID_KEYS:
            continue
        assert pk[0] == "tenant_id", f"{name}.{table} key is {pk}"
        for index in conn.execute(f"PRAGMA index_list({table})").fetchall():
            if index["unique"]:
                first = conn.execute(f"PRAGMA index_info({index['name']})").fetchall()[0]["name"]
                assert first == "tenant_id", f"{name}.{table} unique index {index['name']} starts with {first}"


@pytest.mark.parametrize("name", db.STORES)
def test_every_foreign_key_names_the_tenant(open_all, name):
    conn = open_all[name]
    for table in real_tables(conn):
        groups = {}
        for fk in conn.execute(f"PRAGMA foreign_key_list({table})"):
            groups.setdefault(fk["id"], []).append(fk)
        for group in groups.values():
            if group[0]["table"] == "event" and [g["to"] for g in group] == ["seq"]:
                continue  # event_subject.seq: the seq is global
            assert {g["from"] for g in group} >= {"tenant_id"}, f"{name}.{table} -> {group[0]['table']} ignores the tenant"
            assert {g["to"] for g in group} >= {"tenant_id"}


def test_two_tenants_can_hold_the_same_id_in_memory_db(memory):
    for tenant in ("local", "acme"):
        add_item(memory, "m1", tenant_id=tenant)
        add_evidence(memory, "ev1", "m1", tenant_id=tenant)
        add_topic_for(memory, "t1", tenant)
        add_event_for(memory, "e1", tenant)
    assert memory.execute("SELECT COUNT(*) FROM item WHERE id = 'm1'").fetchone()[0] == 2
    with pytest.raises(sqlite3.IntegrityError):
        add_item(memory, "m1", tenant_id="acme")  # the same tenant still cannot repeat it


def add_topic_for(m, tid, tenant):
    m.execute("INSERT INTO topic (tenant_id, id, label, created_seq, seq_from) VALUES (?, ?, 'T', 1, 1)", (tenant, tid))


def add_event_for(m, eid, tenant):
    m.execute(
        "INSERT INTO event (tenant_id, id, type, subjects, payload, actor, config_version, recorded_at)"
        " VALUES (?, ?, 'item.created', '[]', '{}', 'code:test', 'cfg', ?)", (tenant, eid, NOW),
    )


def test_a_foreign_key_does_not_reach_into_another_tenants_rows(memory):
    add_item(memory, "m1", tenant_id="acme")
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        memory.execute(
            "INSERT INTO stance (tenant_id, id, item_id, stance, evidence_ids, created_seq) VALUES ('local', 's1', 'm1', 'stated', '[\"e\"]', 1)"
        )
    memory.execute("INSERT INTO stance (tenant_id, id, item_id, stance, evidence_ids, created_seq) VALUES ('acme', 's1', 'm1', 'stated', '[\"e\"]', 1)")


def test_each_store_keeps_one_row_per_tenant_and_key(open_all):
    """The keys the design names: work_thread, item_line, layout_meta, job idempotency, gate_bar, budget, event id."""
    w, i, o, r = open_all["working"], open_all["index"], open_all["overview"], open_all["runs"]
    for tenant in ("local", "acme"):
        w.execute("INSERT INTO work_thread (tenant_id, id, title, scope, opened_at, last_active) VALUES (?, 'T1', 't', 'personal', ?, ?)", (tenant, NOW, NOW))
        i.execute(
            "INSERT INTO item_line (tenant_id, item_id, version, kind, line_text, class, scope, status, value, check_status, built_at)"
            " VALUES (?, 'm1', 1, 'decision', 'l', 'fact', 'personal', 'active', 'forming', 'not_needed', ?)", (tenant, NOW),
        )
        i.execute("INSERT INTO gate_bar (tenant_id, project, bar, floor, updated_at) VALUES (?, 'energy-dash', 0.5, 0.3, ?)", (tenant, NOW))
        o.execute("INSERT INTO layout_meta (tenant_id, id, seed, updated_at) VALUES (?, 1, 7, ?)", (tenant, NOW))
        r.execute("INSERT INTO run (tenant_id, id, trigger, started_at) VALUES (?, 'r1', 'idle', ?)", (tenant, NOW))
        r.execute("INSERT INTO job (tenant_id, id, run_id, stage, idempotency_key, created_at, updated_at) VALUES (?, 'j1', 'r1', 'extract', 'k1', ?, ?)", (tenant, NOW, NOW))
        r.execute("INSERT INTO budget (tenant_id, change_type, updated_at) VALUES (?, 'merge', ?)", (tenant, NOW))
    for conn, sql in [
        (w, "INSERT INTO work_thread (id, title, scope, opened_at, last_active) VALUES ('T1', 't', 'personal', ?, ?)"),
        (i, "INSERT INTO gate_bar (project, bar, floor, updated_at) VALUES ('energy-dash', 0.5, 0.3, ?)"),
        (o, "INSERT INTO layout_meta (id, seed, updated_at) VALUES (1, 7, ?)"),
        (r, "INSERT INTO budget (change_type, updated_at) VALUES ('merge', ?)"),
        (r, "INSERT INTO job (id, run_id, stage, idempotency_key, created_at, updated_at) VALUES ('j9', 'r1', 'extract', 'k1', ?, ?)"),
    ]:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(sql, (NOW,) * sql.count("?"))


# --- evidence is removed only under a purge authorization -------------------------------------------------------------


def test_evidence_cannot_be_deleted_without_a_purge_authorization(memory):
    """Attack: delete the evidence an item rests on (I1), straight in memory.db."""
    add_item(memory)
    add_evidence(memory)
    refused(memory, "DELETE FROM evidence WHERE id = 'ev1'", match="removed only under a purge authorization")
    authorize(memory, "event", "ev1")  # another table's authorization does not open it
    refused(memory, "DELETE FROM evidence WHERE id = 'ev1'", match="purge authorization")
    authorize(memory, "evidence", "ev2")  # nor does another row's
    refused(memory, "DELETE FROM evidence WHERE id = 'ev1'", match="purge authorization")
    authorize(memory, "evidence", "ev1")
    memory.execute("DELETE FROM evidence WHERE id = 'ev1'")
    assert memory.execute("SELECT COUNT(*) FROM evidence").fetchone()[0] == 0
    refused(memory, "DELETE FROM purge_authorization", match="append-only")  # the authorization stays


def test_the_authorization_must_be_for_the_same_tenant(memory):
    add_item(memory, tenant_id="acme")
    add_evidence(memory, tenant_id="acme")
    authorize(memory, "evidence", "ev1")  # the 'local' tenant's authorization
    refused(memory, "DELETE FROM evidence WHERE id = 'ev1'", match="purge authorization")


def test_more_of_evidence_is_frozen(memory):
    add_evidence(memory)
    for column, value in [("role", "support"), ("subject_kind", "correction"), ("context", "personal"), ("created_seq", 9), ("id", "ev9")]:
        refused(memory, f"UPDATE evidence SET {column} = ? WHERE id = 'ev1'", (value,), match="frozen")


# --- sources, runs: the rest of the append-only gaps -------------------------------------------------------------------


def test_a_source_keeps_its_kind_and_scope_and_its_sensitivity_only_rises(history):
    add_source(history)
    refused(history, "UPDATE source SET scope = 'personal' WHERE id = 's1'", match="kind or scope")
    refused(history, "UPDATE source SET kind = 'work' WHERE id = 's1'", match="kind or scope")
    refused(history, "UPDATE source SET tenant_id = 'acme' WHERE id = 's1'", match="kind or scope")
    history.execute("UPDATE source SET scope = scope, title = 'renamed' WHERE id = 's1'")  # a no-op on scope is fine
    history.execute("UPDATE source SET sensitivity = 'sensitive' WHERE id = 's1'")
    history.execute("UPDATE source SET sensitivity = 'private' WHERE id = 's1'")
    for lower in ("sensitive", "normal"):
        refused(history, "UPDATE source SET sensitivity = ? WHERE id = 's1'", (lower,), match="may only rise")
    # even a purge authorization does not let the scope change (it lets the row go)
    authorize(history, "source", "s1")
    refused(history, "UPDATE source SET scope = 'personal' WHERE id = 's1'", match="kind or scope")


def test_a_source_is_deleted_only_under_a_purge_authorization(history):
    add_source(history)
    refused(history, "DELETE FROM source WHERE id = 's1'", match="append-only")
    authorize(history, "source", "s1")
    history.execute("DELETE FROM source WHERE id = 's1'")


def runs_rows(r):
    r.execute("INSERT INTO run (id, trigger, started_at) VALUES ('r1', 'idle', ?)", (NOW,))
    r.execute("INSERT INTO proposal (id, run_id, ops, risk_tier, state, created_at) VALUES ('p1', 'r1', '[]', 'medium', 'pending', ?)", (NOW,))
    r.execute("INSERT INTO proposal (id, run_id, ops, risk_tier, state, created_at) VALUES ('p2', 'r1', '[]', 'medium', 'applied', ?)", (NOW,))
    r.execute("INSERT INTO model_call (id, run_id, provider, model, family, prompt_hash, called_at) VALUES ('mc1', 'r1', 'claude', 'm', 'claude', 'h', ?)", (NOW,))
    r.execute("INSERT INTO verdict (id, proposal_id, checker_family, outcome, independent, model_call_id, at) VALUES ('v1', 'p1', 'openai', 'pass', 1, 'mc1', ?)", (NOW,))
    r.execute("INSERT INTO change_log (id, run_id, at, change_type, line, event_ids) VALUES ('cl1', 'r1', ?, 'supersede', 'Replaced a view', '[]')", (NOW,))


def test_an_applied_proposal_is_final(open_all):
    """Attack: rewrite or drop the proposal the log was made from."""
    r = open_all["runs"]
    runs_rows(r)
    r.execute("UPDATE proposal SET state = 'applied' WHERE id = 'p1'")  # pending -> applied is how it gets there
    for sql in ("UPDATE proposal SET state = 'rejected' WHERE id = 'p1'", "UPDATE proposal SET ops = '[{}]' WHERE id = 'p2'",
                "DELETE FROM proposal WHERE id = 'p2'"):
        refused(r, sql, match="applied proposal is final")
    r.execute("INSERT INTO proposal (id, run_id, ops, risk_tier, state, created_at) VALUES ('p3', 'r1', '[]', 'low', 'pending', ?)", (NOW,))
    r.execute("UPDATE proposal SET state = 'rejected' WHERE id = 'p3'")  # others still move
    r.execute("DELETE FROM proposal WHERE id = 'p3'")


def test_a_change_log_row_is_final_except_that_it_is_marked_undone_once(open_all):
    r = open_all["runs"]
    runs_rows(r)
    for column in ("line", "change_type", "event_ids", "undo_handle", "at", "run_id", "id"):
        value = "'[1]'" if column == "event_ids" else "'x'"
        refused(r, f"UPDATE change_log SET {column} = {value} WHERE id = 'cl1'", match="final")
    refused(r, "DELETE FROM change_log WHERE id = 'cl1'", match="final")
    r.execute("UPDATE change_log SET undone_at = ? WHERE id = 'cl1'", (NOW,))
    refused(r, "UPDATE change_log SET undone_at = NULL WHERE id = 'cl1'", match="undone once")
    refused(r, "UPDATE change_log SET undone_at = '2027-01-01T00:00:00.000Z' WHERE id = 'cl1'", match="undone once")
    r.execute("UPDATE change_log SET undone_at = ? WHERE id = 'cl1'", (NOW,))  # the same value is no change


def test_verdicts_and_model_calls_are_append_only(open_all):
    """The gate takes verdicts from runs.db, so a verdict (and the call it names) cannot be rewritten or removed."""
    r = open_all["runs"]
    runs_rows(r)
    for sql in ("UPDATE verdict SET outcome = 'fail' WHERE id = 'v1'", "UPDATE verdict SET checker_family = 'claude' WHERE id = 'v1'",
                "DELETE FROM verdict WHERE id = 'v1'", "UPDATE model_call SET family = 'openai' WHERE id = 'mc1'",
                "UPDATE model_call SET raw_output = 'x' WHERE id = 'mc1'", "DELETE FROM model_call WHERE id = 'mc1'"):
        refused(r, sql, match="append-only")


def test_a_verdict_names_a_proposal_and_a_call_that_exist(open_all):
    r = open_all["runs"]
    runs_rows(r)
    refused(r, "INSERT INTO verdict (id, proposal_id, checker_family, outcome, independent, at) VALUES ('v2', 'nope', 'openai', 'pass', 1, ?)", (NOW,))
    refused(r, "INSERT INTO verdict (id, proposal_id, checker_family, outcome, independent, model_call_id, at) VALUES ('v3', 'p1', 'openai', 'pass', 1, 'nope', ?)", (NOW,))


def test_every_history_table_has_both_append_only_triggers(memory):
    names = {r["name"] for r in memory.execute("SELECT name FROM sqlite_master WHERE type = 'trigger'")}
    history_tables = {t for t in tables_of(memory) if t.endswith("_history")}
    assert history_tables == {f"{t}_history" for t in CURRENT_STATE}
    for table in history_tables:
        assert {f"{table}_no_update", f"{table}_no_delete"} <= names, table
        version = ", version" if table == "item_history" else ""
        memory.execute(f"INSERT INTO {table} (id, seq_from, seq_to, snapshot{version}) VALUES ('x', 1, 2, '{{}}'{', 1' if version else ''})")
        refused(memory, f"UPDATE {table} SET seq_to = 9 WHERE id = 'x'", match="append-only")
        refused(memory, f"DELETE FROM {table} WHERE id = 'x'", match="append-only")


# --- each schema file lists the triggers it defines --------------------------------------------------------------------

SCHEMA_DIR = Path(db.__file__).parent / "schema"


def listed_triggers(text):
    """The names in the comment block 'Triggers this file defines' at the top of a schema file."""
    block = re.search(r"-- Triggers this file defines[^\n]*\n((?:--[^\n]*\n)+)", text)
    assert block, "no 'Triggers this file defines' comment block"
    lines = [line[2:].strip() for line in block.group(1).splitlines()]
    return {n.strip() for line in lines if re.match(r"^[a-z_, ]+$", line) and not line.startswith("none") for n in line.split(",") if n.strip()}


@pytest.mark.parametrize("name", db.STORES)
def test_the_trigger_list_at_the_top_of_a_schema_file_matches_its_triggers(name):
    text = (SCHEMA_DIR / f"{name}.sql").read_text(encoding="utf-8")
    defined = set(re.findall(r"^CREATE TRIGGER (\w+)", text, re.M))
    assert listed_triggers(text) == defined


def test_the_listed_triggers_are_the_ones_the_database_has(open_all):
    for name in ("history", "memory", "runs"):
        have = {r["name"] for r in open_all[name].execute("SELECT name FROM sqlite_master WHERE type = 'trigger'")}
        assert listed_triggers((SCHEMA_DIR / f"{name}.sql").read_text(encoding="utf-8")) == have


def test_event_subject_rows_are_append_only_unless_a_purge_authorized_their_event(memory):
    add_event(memory, "e1")
    add_event(memory, "e2")
    memory.execute("INSERT INTO event_subject (subject_id, seq) VALUES ('m1', 1), ('m1', 2)")
    refused(memory, "UPDATE event_subject SET subject_id = 'm2' WHERE seq = 1", match="append-only")
    refused(memory, "DELETE FROM event_subject WHERE seq = 1", match="append-only")
    authorize(memory, "event", "e1")
    memory.execute("DELETE FROM event_subject WHERE seq = 1")
    refused(memory, "DELETE FROM event_subject WHERE seq = 2", match="append-only")


def test_the_gates_required_triggers_are_all_defined_in_the_schema_files():
    """The gate's sweep (invariants.REQUIRED_TRIGGERS) names triggers by store; each must be one the files define."""
    invariants = pytest.importorskip("northstar_agent_memory.core.invariants")
    required = getattr(invariants, "REQUIRED_TRIGGERS", None)
    if required is None:
        pytest.skip("the gate does not list required triggers yet")
    for store, wanted in required.items():
        text = (SCHEMA_DIR / f"{store}.sql").read_text(encoding="utf-8")
        assert set(wanted) <= listed_triggers(text), sorted(set(wanted) - listed_triggers(text))
