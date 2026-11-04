"""SQLiteOverviewStore: topic and idea views, suggestions, open items, where you left off, layout and marks (§2.11)."""

from __future__ import annotations

import sqlite3

import pytest

from northstar_agent_memory.core import ports
from northstar_agent_memory.core import overview_store
from northstar_agent_memory.core.overview_store import SQLiteOverviewStore

# Invented: Robin's energy dashboard (MEMORY-ARCHITECTURE §6).


@pytest.fixture
def store(open_all):
    return SQLiteOverviewStore(open_all["overview"])


def idea(store, item_id="m1", **kw):
    args = dict(shown_line="one SQLite file per meter", shown_is_yours=True, origin_mark="yours", version=1)
    store.put_idea(item_id, **{**args, **kw})


def test_it_is_an_overview_store(store):
    assert isinstance(store, ports.OverviewStore)


def test_open_from_a_root_and_the_default_root(store_root, isolated_home):
    s = SQLiteOverviewStore.open(store_root)
    assert (store_root / "overview.db").is_file()
    s.close()
    from northstar_agent_memory import paths

    s = SQLiteOverviewStore.open()
    assert (paths.data_root() / "overview.db").is_file()
    s.close()


# --- topics ---


def test_topics_top_level_and_sub_topics(store):
    store.put_topic("t1", "Storage", entries=["m1", "m2"], more_count=3, open_count=1, changed_since_seen=True)
    store.put_topic("t2", "Alerts")
    store.put_topic("t3", "Downsampling", parent_id="t1")
    store.put_topic("t4", "Schema", parent_id="t1", status="dormant")
    assert [t["topic_id"] for t in store.topics()] == ["t2", "t1"]  # by label
    assert [t["topic_id"] for t in store.topics(parent_id="t1")] == ["t3", "t4"]
    assert store.topics(parent_id="t2") == []
    top = store.topic_view("t1")
    assert top["label"] == "Storage" and top["entries"] == ["m1", "m2"] and top["more_count"] == 3
    assert top["open_count"] == 1 and top["changed_since_seen"] == 1 and top["status"] == "active"
    assert top["parent_id"] is None and top["tenant_id"] == "local" and top["built_at"].endswith("Z")
    assert store.topic_view("t4")["status"] == "dormant"
    assert store.topic_view("nope") is None


def test_put_topic_replaces_and_delete_topic_removes(store):
    store.put_topic("t1", "Storage", entries=["m1"])
    store.put_topic("t1", "Data storage", entries=["m2", "m3"])
    assert store.topic_view("t1")["label"] == "Data storage" and store.topic_view("t1")["entries"] == ["m2", "m3"]
    store.delete_topic("t1")
    assert store.topic_view("t1") is None


def test_topic_validation(store):
    with pytest.raises(ValueError):
        store.put_topic("t1", " ")
    with pytest.raises(sqlite3.IntegrityError):
        store.put_topic("t1", "x", status="archived")
    with pytest.raises(sqlite3.IntegrityError):
        store.put_topic("t1", "x", more_count=-1)


# --- ideas ---


def test_an_idea_shows_your_words_with_its_origin_and_work(store):
    idea(
        store, work_cues=[{"label": "logger commit", "snapshot": "blob1"}], sources=[{"app": "claude-code", "title": "Logger", "day": "2026-03-02"}],
        links=["l1"], conflict_pairs=[["m1", "m7"]], version=3,
    )
    row = store.idea_view("m1")
    assert row["shown_line"] == "one SQLite file per meter" and row["shown_is_yours"] == 1 and row["origin_mark"] == "yours"
    assert row["work_cues"] == [{"label": "logger commit", "snapshot": "blob1"}] and row["links"] == ["l1"]
    assert row["sources"][0]["app"] == "claude-code" and row["conflict_pairs"] == [["m1", "m7"]] and row["version"] == 3
    assert store.idea_view("nope") is None


def test_an_idea_in_northstars_words_is_marked(store):
    idea(store, "m2", shown_line="Readings older than 7 days are kept as hourly averages", shown_is_yours=False, origin_mark="adopted from Claude")
    row = store.idea_view("m2")
    assert row["shown_is_yours"] == 0 and row["origin_mark"] == "adopted from Claude"


def test_idea_rules(store):
    with pytest.raises(ValueError):
        idea(store, work_cues=["a", "b", "c", "d"])
    idea(store, work_cues=["a", "b", "c"])
    with pytest.raises(ValueError):
        idea(store, shown_line=" ")
    idea(store, shown_line="v2", version=2)
    assert store.idea_view("m1")["shown_line"] == "v2" and store.idea_view("m1")["work_cues"] == []
    store.delete_idea("m1")
    assert store.idea_view("m1") is None


# --- suggestions (I27) ---


def suggestion(link_id="l1", **kw):
    return {"link_id": link_id, "from_id": "m8", "to_id": "m1", "type": "supports", "reason": "m8 repeats m1 in another project", **kw}


def test_suggestions_wait_for_your_confirmation(store):
    store.put_suggestion(suggestion("l1", created_at="2026-03-04T00:00:00Z"))
    store.put_suggestion(suggestion("l2", created_at="2026-03-03T00:00:00Z"))
    assert [s["link_id"] for s in store.suggestions()] == ["l2", "l1"]
    assert store.suggestions()[0]["status"] == "waiting" and store.suggestions("confirmed") == []
    store.set_suggestion_status("l1", "confirmed")
    store.set_suggestion_status("l2", "rejected")
    assert store.suggestions() == []
    assert [s["link_id"] for s in store.suggestions("confirmed")] == ["l1"]
    assert [s["link_id"] for s in store.suggestions("rejected")] == ["l2"]


def test_suggestion_validation(store):
    with pytest.raises(ValueError):
        store.put_suggestion({"link_id": "l1"})
    with pytest.raises(ValueError):
        store.put_suggestion(suggestion(status="maybe"))
    with pytest.raises(sqlite3.IntegrityError):
        store.put_suggestion(suggestion(type="likes"))
    with pytest.raises(ValueError):
        store.suggestions("maybe")
    with pytest.raises(ValueError):
        store.set_suggestion_status("l1", "maybe")
    with pytest.raises(KeyError):
        store.set_suggestion_status("nope", "confirmed")


def test_a_suggestion_added_again_is_replaced(store):
    store.put_suggestion(suggestion("l1", reason="first"))
    store.put_suggestion(suggestion("l1", reason="second"))
    [s] = store.suggestions()
    assert s["reason"] == "second"


# --- open items and where you left off ---


def test_open_items(store):
    a = store.put_open_item("open_question", "m11", "How do I avoid alert fatigue?", topic_id="t2", since="2026-03-11")
    b = store.put_open_item("active_goal", "m9", "Alert me when the dryer costs double", topic_id="t2", since="2026-03-09")
    c = store.put_open_item("goal_gap", "m9", "Nothing advances the alert goal yet", topic_id="t3")
    assert [o["id"] for o in store.open_items(topic_id="t2")] == [b, a]
    assert [o["id"] for o in store.open_items(topic_id="t3")] == [c]
    assert len(store.open_items()) == 3
    row = store.open_items(topic_id="t3")[0]
    assert (row["kind"], row["ref_id"], row["since"]) == ("goal_gap", "m9", None)
    assert store.put_open_item("next_step", "m3", "Add the UPS", open_item_id="fixed") == "fixed"
    with pytest.raises(ValueError):
        store.put_open_item("term_appeared", "m1", "x")


def test_left_off(store):
    store.put_left_off(
        "T1", last_state="Logger writes one file per meter", last_steps=["added WAL", "wrote the downsampler"],
        changed_since=["m2 now says 14 days"], goal="Alert me when the dryer costs double", next_step="Test the alert",
        open_questions=["How do I avoid alert fatigue?"],
    )
    row = store.left_off("T1")
    assert row["last_state"] == "Logger writes one file per meter" and row["last_steps"] == ["added WAL", "wrote the downsampler"]
    assert row["changed_since"] == ["m2 now says 14 days"] and row["goal"].startswith("Alert me")
    assert row["next_step"] == "Test the alert" and row["open_questions"] == ["How do I avoid alert fatigue?"]
    store.put_left_off("T1")
    empty = store.left_off("T1")
    assert empty["last_state"] == "" and empty["last_steps"] == [] and empty["goal"] is None
    assert store.left_off("nope") is None


# --- layout ---


def node(node_id, kind, x, y):
    return {"node_id": node_id, "node_kind": kind, "x": x, "y": y}


def test_set_layout_keeps_the_previous_position(store):
    assert store.layout() == [] and store.layout_meta() is None
    store.set_layout([node("t1", "topic", 1.0, 2.0), node("m1", "entry", 3.0, 4.0)], seed=7)
    first = {n["node_id"]: n for n in store.layout()}
    assert (first["t1"]["x"], first["t1"]["y"], first["t1"]["prev_x"], first["t1"]["prev_y"]) == (1.0, 2.0, None, None)
    assert store.layout_meta()["seed"] == 7 and store.layout_meta()["version"] == 1
    store.set_layout([node("t1", "topic", 1.5, 2.5), node("t2", "topic", 9.0, 9.0)], seed=7)
    second = {n["node_id"]: n for n in store.layout()}
    assert set(second) == {"t1", "t2"}  # m1 was left out and is dropped
    assert (second["t1"]["x"], second["t1"]["prev_x"], second["t1"]["prev_y"]) == (1.5, 1.0, 2.0)
    assert second["t2"]["prev_x"] is None
    assert store.layout_meta()["version"] == 2
    store.set_layout([node("t1", "topic", 1.5, 2.5)], seed=8)
    assert store.layout_meta()["seed"] == 8 and store.layout_meta()["version"] == 3
    assert {n["node_id"]: (n["prev_x"], n["prev_y"]) for n in store.layout()}["t1"] == (1.5, 2.5)  # an unchanged topic stays in place


def test_layout_validation_changes_nothing(store):
    store.set_layout([node("t1", "topic", 1.0, 2.0)], seed=1)
    with pytest.raises(ValueError):
        store.set_layout([node("t1", "topic", 5.0, 5.0), node("x", "island", 0.0, 0.0)], seed=2)
    assert store.layout()[0]["x"] == 1.0 and store.layout_meta()["seed"] == 1


# --- marks ---


def test_mark_seen(store):
    assert store.mark("m1") is None
    store.mark_seen("m1", 2, at="2026-03-05T00:00:00.000Z")
    assert {k: store.mark("m1")[k] for k in ("last_seen_version", "seen_at", "pinned")} == {
        "last_seen_version": 2, "seen_at": "2026-03-05T00:00:00.000Z", "pinned": 0,
    }
    store.mark_seen("m1", 3)
    assert store.mark("m1")["last_seen_version"] == 3


def test_pins(store):
    store.mark_seen("m1", 2)
    store.set_pinned("m1", True)
    store.set_pinned("m2", True)  # never seen: version 0
    assert store.pinned() == ["m1", "m2"]
    assert store.mark("m1")["last_seen_version"] == 2 and store.mark("m2")["last_seen_version"] == 0
    store.mark_seen("m1", 4)
    assert store.mark("m1")["pinned"] == 1  # seeing it again keeps the pin
    store.set_pinned("m1", False)
    assert store.pinned() == ["m2"] and store.mark("m1")["last_seen_version"] == 4


def test_hidden_opens_feed_the_split_bar(store):
    assert store.topic_mark("t1") is None
    store.record_hidden_open("t1", at="2026-03-05T00:00:00.000Z")
    store.record_hidden_open("t1", at="2026-03-06T00:00:00.000Z")
    store.record_hidden_open("t2")
    row = store.topic_mark("t1")
    assert row["hidden_opens"] == 2 and row["last_opened_at"] == "2026-03-06T00:00:00.000Z"
    assert store.topic_mark("t2")["hidden_opens"] == 1


# --- rebuild support ---


def test_clear_derived_keeps_layout_and_marks(store):
    store.put_topic("t1", "Storage")
    idea(store)
    store.put_suggestion(suggestion())
    store.put_open_item("open_question", "m11", "q")
    store.put_left_off("T1")
    store.set_layout([node("t1", "topic", 1.0, 2.0)], seed=3)
    store.mark_seen("m1", 2)
    store.set_pinned("m1", True)
    store.record_hidden_open("t1")
    store.clear_derived()
    for table in overview_store.DERIVED_TABLES:  # a waiting suggestion is derived: it goes
        assert store.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0, table
    assert len(store.layout()) == 1 and store.layout_meta()["seed"] == 3
    assert store.mark("m1")["pinned"] == 1 and store.topic_mark("t1")["hidden_opens"] == 1


def test_clear_derived_keeps_your_decisions_on_suggestions(store):
    """The attack: a rebuild wiped the suggestion table, so a link you rejected came back as waiting."""
    store.put_suggestion(suggestion("l-yes", created_at="2026-03-03T00:00:00Z"))
    store.put_suggestion(suggestion("l-no", created_at="2026-03-04T00:00:00Z"))
    store.put_suggestion(suggestion("l-wait", created_at="2026-03-05T00:00:00Z"))
    store.set_suggestion_status("l-yes", "confirmed")
    store.set_suggestion_status("l-no", "rejected")
    store.clear_derived()
    assert [s["link_id"] for s in store.suggestions("confirmed")] == ["l-yes"]
    assert [s["link_id"] for s in store.suggestions("rejected")] == ["l-no"]
    assert store.suggestions("waiting") == []  # only what was waiting is derived
    for link_id in ("l-yes", "l-no", "l-wait"):  # the builder finds all three links again
        store.put_suggestion(suggestion(link_id))
    assert [s["link_id"] for s in store.suggestions("rejected")] == ["l-no"]  # still rejected, not waiting again
    assert [s["link_id"] for s in store.suggestions("confirmed")] == ["l-yes"]
    assert [s["link_id"] for s in store.suggestions("waiting")] == ["l-wait"]
    assert store.suggestions("rejected")[0]["created_at"] == "2026-03-04T00:00:00Z"


def test_the_state_tables_are_named(store):
    assert overview_store.STATE_TABLES == ("layout", "layout_meta", "mark", "topic_mark")
    assert not set(overview_store.STATE_TABLES) & set(overview_store.DERIVED_TABLES)


def test_derived_tables_are_every_table_but_your_state(store):
    tables = {
        r["name"] for r in store.conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")
        if r["name"] != "schema_version"
    }
    assert tables - set(overview_store.DERIVED_TABLES) == set(overview_store.STATE_TABLES)


def link_row(status, **kw):
    """A row of memory's link table, as far as a suggestion needs it."""
    return {"id": "l1", "from_id": "m8", "to_id": "m1", "type": "supports", "reason": "m8 repeats m1", "status": status, "stated_by": "northstar", **kw}


def test_a_suggestion_takes_its_status_from_memorys_link_row(store):
    assert store.put_suggestion_from_link(link_row("proposed")) == "waiting"
    assert [s["link_id"] for s in store.suggestions()] == ["l1"]
    assert store.put_suggestion_from_link(link_row("confirmed")) == "confirmed"
    assert store.suggestions() == [] and [s["link_id"] for s in store.suggestions("confirmed")] == ["l1"]
    assert store.put_suggestion_from_link(link_row("rejected")) == "rejected"
    assert [s["link_id"] for s in store.suggestions("rejected")] == ["l1"]


def test_memory_wins_over_a_stale_decision_held_here(store):
    store.put_suggestion(suggestion("l1"))
    store.set_suggestion_status("l1", "rejected")  # this copy says rejected
    store.clear_derived()
    store.put_suggestion_from_link(link_row("proposed"))  # memory says the link is still proposed
    assert [s["link_id"] for s in store.suggestions()] == ["l1"]
    store.put_suggestion(suggestion("l2"))
    store.clear_derived()
    store.put_suggestion_from_link(link_row("rejected", id="l2"))  # memory has your later rejection
    assert [s["link_id"] for s in store.suggestions("rejected")] == ["l2"]


@pytest.mark.parametrize("status, stated_by", [("applied", "northstar"), ("retracted", "northstar"), ("proposed", "you"), ("confirmed", "construction")])
def test_a_link_that_is_not_a_suggestion_is_removed(store, status, stated_by):
    store.put_suggestion(suggestion("l1"))
    assert store.put_suggestion_from_link(link_row(status, stated_by=stated_by)) is None
    assert store.suggestions("waiting") == [] and store.suggestions("confirmed") == [] and store.suggestions("rejected") == []


def test_a_suggestion_rebuilt_from_a_link_keeps_its_age(store):
    store.put_suggestion(suggestion("l1", created_at="2026-03-03T00:00:00Z"))
    store.put_suggestion_from_link(link_row("proposed"))
    assert store.suggestions()[0]["created_at"] == "2026-03-03T00:00:00Z"
    assert store.suggestions()[0]["reason"] == "m8 repeats m1"


def test_the_overview_holds_no_ai_prose_or_file_path_columns(store):
    # I27 and §2.11: nothing here is shaped for IDs shown to you, file paths or unconfirmed links on an idea.
    columns = {r["name"] for t in ("topic_view", "idea_view", "left_off") for r in store.conn.execute(f"PRAGMA table_info({t})")}
    assert not columns & {"path", "file_path", "summary", "ai_text"}


# --- tenants ---


def test_another_tenant_sees_nothing(open_all, store):
    store.put_topic("t1", "Storage")
    store.mark_seen("m1", 1)
    other = SQLiteOverviewStore(open_all["overview"], tenant_id="acme")
    assert other.topics() == [] and other.mark("m1") is None and other.layout() == []
    other.put_topic("t9", "Acme topic")  # ids of its own: the schema's primary keys do not include tenant_id (reported)
    other.set_layout([node("a", "topic", 0.0, 0.0)], seed=1)
    assert other.layout_meta()["tenant_id"] == "acme"
    other.clear_derived()
    assert other.topics() == [] and store.topic_view("t1") is not None


def test_state_survives_reopening(store_root):
    s = SQLiteOverviewStore.open(store_root)
    s.set_layout([node("t1", "topic", 1.0, 2.0)], seed=5)
    s.close()
    again = SQLiteOverviewStore.open(store_root)
    assert again.layout()[0]["x"] == 1.0 and again.layout_meta()["seed"] == 5
    again.close()


def test_a_suggestion_put_again_keeps_your_decision(store):
    store.put_suggestion(suggestion("l1", created_at="2026-03-03T00:00:00Z"))
    store.set_suggestion_status("l1", "rejected")
    store.put_suggestion(suggestion("l1"))  # a later build finds the same link again
    assert store.suggestions() == [] and [s["link_id"] for s in store.suggestions("rejected")] == ["l1"]
    assert store.suggestions("rejected")[0]["created_at"] == "2026-03-03T00:00:00Z"
    store.put_suggestion(suggestion("l1", status="waiting"))  # an explicit status still wins
    assert [s["link_id"] for s in store.suggestions()] == ["l1"]
