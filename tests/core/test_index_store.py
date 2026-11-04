"""SQLiteIndexStore: the AI index tables, BM25 keyword search over keys and history_keys, use and the gate bar (§2.10)."""

from __future__ import annotations

import sqlite3

import pytest

from northstar_agent_memory.core import index_store, ports
from northstar_agent_memory.core.index_store import SQLiteIndexStore, match_query, pack_vector, unpack_vector
from northstar_agent_memory.core.ports import SearchQuery

# Invented: Robin's energy dashboard (MEMORY-ARCHITECTURE §6).


@pytest.fixture
def store(open_all):
    return SQLiteIndexStore(open_all["index"])


def line(item_id, text, **kw):
    base = dict(
        item_id=item_id, version=1, kind="decision", line_text=text, scope="project:energy-dash", status="active",
        value="kept", check_status="not_needed", salience=0.0, said_at="2026-03-02T09:30:00Z",
    )
    base["class"] = kw.pop("class_", "fact")
    return {**base, **kw}


def add(store, item_id, text, *, keys=None, **kw):
    store.put_item_line(line(item_id, text, **kw))
    store.put_keys(item_id, line=keys or text)


@pytest.fixture
def filled(store):
    add(store, "m1", "Readings are stored in SQLite on the Pi, one file per meter")
    add(store, "m2", "Readings older than 7 days are kept only as hourly averages")
    add(store, "m3", "The dashboard is demoed at the meetup in March", scope="personal")
    add(store, "m4", "Prefers short alert messages about the dryer", class_="view")
    add(store, "m5", "Old plan: store readings in Postgres", status="superseded")
    add(store, "m6", "The Pi has 4 GB of memory for readings", check_status="contradicted")
    add(store, "m7", "Readings for the course project use CSV files", scope="project:de-course")
    return store


def test_it_is_an_index_port(store):
    assert isinstance(store, ports.IndexPort)


def test_open_from_a_root_and_the_default_root(store_root, isolated_home):
    s = SQLiteIndexStore.open(store_root)
    assert (store_root / "index.db").is_file()
    s.close()
    from northstar_agent_memory import paths

    s = SQLiteIndexStore.open()
    assert (paths.data_root() / "index.db").is_file()
    s.close()


# --- item lines ---


def test_put_and_read_an_item_line(store):
    store.put_item_line(line("m1", "Readings are stored in SQLite"))
    row = store.item_line("m1")
    assert row["line_text"] == "Readings are stored in SQLite" and row["class"] == "fact" and row["version"] == 1
    assert row["salience"] == 0 and row["tenant_id"] == "local" and row["built_at"].endswith("Z")
    assert store.item_line("nope") is None


def test_put_replaces_the_line_of_the_same_item(store):
    store.put_item_line(line("m1", "old"))
    store.put_item_line(line("m1", "new", version=2))
    assert [r["line_text"] for r in store.item_lines()] == ["new"]
    assert store.item_line("m1")["version"] == 2


def test_item_line_needs_every_column_and_valid_values(store):
    bad = line("m1", "x")
    del bad["kind"]
    with pytest.raises(ValueError):
        store.put_item_line(bad)
    with pytest.raises(sqlite3.IntegrityError):
        store.put_item_line(line("m1", "x", status="deleted"))
    with pytest.raises(sqlite3.IntegrityError):
        store.put_item_line(line("m1", "x", scope="everyone"))
    assert store.item_lines() == []


def test_item_lines_filter_and_salience(filled):
    assert [r["item_id"] for r in filled.item_lines(status="superseded")] == ["m5"]
    assert [r["item_id"] for r in filled.item_lines(scope="personal")] == ["m3"]
    filled.set_salience("m1", 1.5)
    assert filled.item_line("m1")["salience"] == 1.5


def test_filtered_items_carry_a_reason(store):
    store.set_filtered("m9", "kept out: contradicted by its source")
    store.set_filtered("m9", "kept out: held scope")
    assert store.filtered() == [{"tenant_id": "local", "item_id": "m9", "reason": "kept out: held scope"}]
    with pytest.raises(ValueError):
        store.set_filtered("m10", " ")


def test_delete_item_clears_every_trace(filled):
    filled.put_vector("m1", "embed-1", "line", 1, [0.1, 0.2])
    filled.set_filtered("m1", "r")
    filled.put_link({"link_id": "l1", "from_id": "m1", "to_id": "m2", "to_kind": "item", "type": "supports", "strength": "checked"})
    filled.put_link({"link_id": "l2", "from_id": "m2", "to_id": "m3", "to_kind": "item", "type": "refines", "strength": "checked"})
    filled.delete_item("m1")
    assert filled.item_line("m1") is None and filled.search_keys("SQLite") == []
    assert filled.get_vector("m1", "embed-1", "line") is None and filled.filtered() == []
    assert [l["link_id"] for l in filled.links_of("m2")] == ["l2"]
    assert filled.item_line("m2") is not None


# --- keyword search over items ---


def test_search_keys_ranks_by_bm25_and_scores_are_positive(filled):
    hits = filled.search_keys("readings SQLite")
    assert hits[0][0] == "m1"
    assert [h[0] for h in hits][:2] == ["m1", "m2"] or {"m1", "m2"} <= {h[0] for h in hits}
    assert all(score > 0 for _, score in hits)
    assert [s for _, s in hits] == sorted((s for _, s in hits), reverse=True)


def test_search_keys_with_nothing_to_search(filled):
    assert filled.search_keys("") == [] and filled.search_keys("  ?!  ") == []
    assert filled.search_keys("zebra") == []


def test_search_keys_limit(filled):
    assert len(filled.search_keys("readings", limit=2)) == 2


def test_search_text_is_never_read_as_fts_syntax(filled):
    for text in ('"unbalanced', "SQLite AND", "a OR (b", "readings*", "col:val", "NEAR(a b)", "x -y", "'; DROP TABLE keys; --"):
        filled.search_keys(text)
    assert filled.search_keys("readings*") == filled.search_keys("readings")  # the star is not a prefix operator
    assert filled.conn.execute("SELECT COUNT(*) FROM keys").fetchone()[0] == 7


def test_match_query():
    assert match_query("Readings, SQLite!") == '"readings" OR "sqlite"'
    assert match_query("a a a") == '"a"'
    assert match_query("???") is None


def test_every_keys_column_is_searchable(store):
    store.put_item_line(line("m1", "x"))
    store.put_keys(
        "m1", line="alpha", your_words="bravo", why="charlie", question_key="delta", topic_labels="echo", aliases="foxtrot"
    )
    for word in ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot"):
        assert store.search_keys(word)[0][0] == "m1", word


def test_put_keys_replaces_the_row(store):
    store.put_keys("m1", line="alpha")
    store.put_keys("m1", line="bravo")
    assert store.search_keys("alpha") == [] and store.search_keys("bravo")[0][0] == "m1"
    assert store.conn.execute("SELECT COUNT(*) FROM keys").fetchone()[0] == 1


def test_diacritics_and_case_do_not_matter(store):
    store.put_keys("m1", line="Café readings")
    assert store.search_keys("cafe")[0][0] == "m1" and store.search_keys("CAFÉ")[0][0] == "m1"


# --- search (the port) ---


def test_push_returns_active_uncontradicted_facts_whose_scope_covers_the_chat(filled):
    hits = filled.search(SearchQuery("readings dashboard", direction="push", project="energy-dash"))
    assert {h.item_id for h in hits} == {"m1", "m2", "m3"}
    assert all(isinstance(h, ports.SearchHit) and h.found_by == ["words"] for h in hits)
    top = filled.search(SearchQuery("SQLite meter", direction="push", project="energy-dash"))[0]
    assert top.item_id == "m1" and top.version == 1 and top.kind == "decision"
    assert top.scope == "project:energy-dash" and top.line_text.startswith("Readings are stored")
    assert [h.score for h in hits] == sorted((h.score for h in hits), reverse=True) and hits[0].score > 0


def test_push_without_a_project_returns_only_personal_scope(filled):
    hits = filled.search(SearchQuery("readings dashboard demoed", direction="push"))
    assert [h.item_id for h in hits] == ["m3"]


def test_push_never_returns_a_view_a_superseded_item_or_a_contradicted_claim(filled):
    ids = {h.item_id for h in filled.search(SearchQuery("dryer Postgres Pi memory", direction="push", project="energy-dash"))}
    assert not ids & {"m4", "m5", "m6"}


def test_pull_returns_facts_and_views_in_the_allowed_scopes(filled):
    q = SearchQuery("readings dryer", direction="pull", allowed_scopes=["project:energy-dash", "personal"])
    assert {h.item_id for h in filled.search(q)} == {"m1", "m2", "m4", "m6"}
    q = SearchQuery("readings", direction="pull")
    assert {h.item_id for h in filled.search(q)} == {"m1", "m2", "m6", "m7"}
    assert {h.item_id for h in filled.search(SearchQuery("readings", direction="pull", allowed_scopes=[]))} == set()


def test_search_leaves_out_items_already_given_and_stops_at_top_n(filled):
    q = SearchQuery("readings", direction="pull", exclude_item_ids=["m1"])
    assert "m1" not in {h.item_id for h in filled.search(q)}
    assert len(filled.search(SearchQuery("readings", direction="pull", top_n=2))) == 2


def test_search_skips_keys_without_a_line(store):
    store.put_keys("ghost", line="readings in the void")
    assert store.search(SearchQuery("readings", direction="pull")) == []


def test_search_of_nothing(filled):
    assert filled.search(SearchQuery("")) == []


def test_search_of_earlier_versions_is_not_the_indexs_job(filled):
    with pytest.raises(NotImplementedError):
        filled.search(SearchQuery("readings", direction="pull", as_of_seq=3))


def test_search_does_not_look_at_who_said_it(store):
    # I23: no author or product column exists in the line table, so ranking cannot use one.
    columns = {r["name"] for r in store.conn.execute("PRAGMA table_info(item_line)")}
    assert not columns & {"speaker", "agent", "origin", "model_family", "app"}


# --- vectors ---


def test_vectors_round_trip_as_little_endian_float32(store):
    store.put_vector("m1", "embed-1", "line", 1, [0.5, -1.25, 3.0])
    assert store.get_vector("m1", "embed-1", "line") == [0.5, -1.25, 3.0]
    row = store.conn.execute("SELECT dim, vector FROM vectors").fetchone()
    assert row["dim"] == 3 and bytes(row["vector"]) == pack_vector([0.5, -1.25, 3.0]) and len(row["vector"]) == 12
    assert unpack_vector(pack_vector([1.0])) == [1.0]


def test_vectors_are_keyed_by_item_model_and_field(store):
    store.put_vector("m1", "embed-1", "line", 1, [1.0, 2.0])
    store.put_vector("m1", "embed-1", "question_key", 1, [3.0, 4.0])
    store.put_vector("m1", "embed-2", "line", 1, [5.0, 6.0, 7.0])
    store.put_vector("m1", "embed-1", "line", 2, [9.0, 9.0])  # replaces
    assert store.conn.execute("SELECT COUNT(*) FROM vectors").fetchone()[0] == 3
    assert store.get_vector("m1", "embed-1", "line") == [9.0, 9.0]
    assert store.get_vector("m1", "embed-3", "line") is None
    assert store.delete_vectors_not_from("embed-2") == 2
    assert store.get_vector("m1", "embed-2", "line") == [5.0, 6.0, 7.0]


def test_vector_validation(store):
    with pytest.raises(ValueError):
        store.put_vector("m1", "e", "title", 1, [1.0])  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        store.put_vector("m1", "e", "line", 1, [])


# --- history exchanges ---


def exchange(store, eid, your, reply="", item_lines="", **kw):
    store.put_exchange(
        eid, source_id=kw.get("source_id", "S1"), user_message_id=f"{eid}-u", reply_message_id=f"{eid}-a",
        occurred_at=kw.get("occurred_at", "2026-03-02T09:30:00Z"), your_text=your, reply_text=reply, item_lines=item_lines,
    )


@pytest.fixture
def chats(store):
    exchange(store, "x1", "how should I store the meter readings on the Pi", "Use one SQLite file per meter.")
    exchange(store, "x2", "what about the dryer alert", "You could alert when the cost doubles.", "alert when dryer costs double")
    exchange(store, "x3", "thanks, that works", "Glad that helps. SQLite is a good choice for readings.")
    return store


def test_search_history_returns_ids_with_scores_never_text(chats):
    hits = chats.search_history("meter readings SQLite")
    assert [h["exchange_id"] for h in hits][0] == "x1"
    top = hits[0]
    assert set(top) == {"exchange_id", "source_id", "user_message_id", "reply_message_id", "occurred_at", "score"}
    assert top["user_message_id"] == "x1-u" and top["reply_message_id"] == "x1-a" and top["source_id"] == "S1"
    assert top["occurred_at"] == "2026-03-02T09:30:00Z" and top["score"] > 0
    assert [h["score"] for h in hits] == sorted((h["score"] for h in hits), reverse=True)


def test_history_search_covers_your_text_the_reply_and_item_lines(chats):
    assert chats.search_history("dryer")[0]["exchange_id"] == "x2"  # your text
    assert {h["exchange_id"] for h in chats.search_history("choice")} == {"x3"}  # the reply
    assert chats.search_history("doubles")[0]["exchange_id"] == "x2"  # the reply
    assert chats.search_history("costs double")[0]["exchange_id"] == "x2"  # item lines
    assert chats.search_history("zebra") == [] and chats.search_history("") == []
    assert len(chats.search_history("the", limit=1)) <= 1


def test_put_exchange_replaces_and_delete_exchange_removes(chats):
    exchange(chats, "x1", "completely different words about heat pumps")
    assert chats.search_history("meter") == [] and chats.search_history("heat pumps")[0]["exchange_id"] == "x1"
    chats.put_history_vector("x1", "embed-1", [1.0, 2.0])
    assert chats.get_history_vector("x1", "embed-1") == [1.0, 2.0]
    chats.delete_exchange("x1")
    assert chats.search_history("heat pumps") == [] and chats.get_history_vector("x1", "embed-1") is None


def test_history_vectors(store):
    store.put_history_vector("x1", "embed-1", [1.0])
    store.put_history_vector("x1", "embed-1", [2.0, 3.0])
    assert store.get_history_vector("x1", "embed-1") == [2.0, 3.0]
    assert store.get_history_vector("x1", "embed-2") is None
    with pytest.raises(ValueError):
        store.put_history_vector("x1", "embed-1", [])


# --- links ---


def test_links(store):
    link = {"link_id": "l1", "from_id": "m1", "to_id": "m2", "to_kind": "item", "type": "supports", "strength": "stated_or_confirmed"}
    store.put_link(link)
    store.put_link({**link, "link_id": "l2", "from_id": "m3", "to_id": "m1", "type": "answers", "strength": "checked"})
    assert [l["link_id"] for l in store.links_of("m1")] == ["l1", "l2"]
    assert [l["link_id"] for l in store.links_of("m2")] == ["l1"]
    store.put_link({**link, "strength": "construction"})
    assert store.links_of("m2")[0]["strength"] == "construction"
    store.delete_link("l1")
    assert [l["link_id"] for l in store.links_of("m1")] == ["l2"]
    with pytest.raises(ValueError):
        store.put_link({"link_id": "l9"})
    with pytest.raises(sqlite3.IntegrityError):
        store.put_link({**link, "link_id": "l9", "type": "likes"})


# --- goal cards and start notes ---


def test_goal_cards(store):
    store.put_goal_card(
        "g1", "Alert me when the dryer costs double", goal_item_id="m9", aliases=["dryer alert"], project="energy-dash",
        top_items=["m1@1", "m2@1"], open_questions=["How do I avoid alert fatigue?"], last_active="2026-03-09T08:00:00Z",
    )
    store.put_goal_card("g2", "Demo at the meetup", thread_id="T1", project="energy-dash", last_active="2026-03-20T08:00:00Z")
    store.put_goal_card("g3", "Pass the course", thread_id="T2", project="de-course", last_active="2026-03-01T08:00:00Z")
    card = store.goal_card("g1")
    assert card["aliases"] == ["dryer alert"] and card["top_items"] == ["m1@1", "m2@1"] and card["goal_item_id"] == "m9"
    assert card["open_questions"] == ["How do I avoid alert fatigue?"] and card["built_at"].endswith("Z")
    assert [c["id"] for c in store.goal_cards()] == ["g2", "g1", "g3"]
    assert [c["id"] for c in store.goal_cards(project="energy-dash")] == ["g2", "g1"]
    assert store.goal_card("nope") is None


def test_goal_card_rules(store):
    with pytest.raises(ValueError):
        store.put_goal_card("g1", "goal")  # needs an item or a thread
    with pytest.raises(ValueError):
        store.put_goal_card("g1", "goal", thread_id="T1", top_items=[f"m{i}@1" for i in range(9)])
    store.put_goal_card("g1", "goal", thread_id="T1", top_items=[f"m{i}@1" for i in range(8)])
    store.put_goal_card("g1", "goal v2", thread_id="T1")
    assert store.goal_card("g1")["goal_text"] == "goal v2" and store.goal_card("g1")["top_items"] == []


def test_start_notes(store):
    store.put_start_note("T1", "Where you left off: the logger.", ["m1@1", "m2@2"], watermark=41)
    row = store.start_note("T1")
    assert row["text"].startswith("Where you left off") and row["items"] == ["m1@1", "m2@2"] and row["watermark"] == 41
    store.put_start_note("T1", "New text", [], watermark=50)
    assert store.start_note("T1")["watermark"] == 50 and store.start_note("T1")["items"] == []
    assert store.start_note("T2") is None


# --- use ---


def test_uses_and_the_summary(store):
    assert store.use_summary("m1") is None
    store.record_use("m1", "delivered", "S1", at="2026-03-02T09:00:00.000Z")
    store.record_use("m1", "delivered", "S2", at="2026-03-03T09:00:00.000Z")
    store.record_use("m1", "recalled", "S2", at="2026-03-04T09:00:00.000Z")
    store.record_use("m1", "viewed", "overview", at="2026-03-05T09:00:00.000Z")
    store.record_use("m1", "built_on", "S1", at="2026-03-06T09:00:00.000Z")
    store.record_use("m2", "viewed", "overview")
    s = store.use_summary("m1")
    assert (s["delivered"], s["recalled"], s["viewed"], s["built_on"], s["contexts"]) == (2, 1, 1, 1, 3)
    assert (s["first_at"], s["last_at"]) == ("2026-03-02T09:00:00.000Z", "2026-03-06T09:00:00.000Z")
    assert [u["kind"] for u in store.uses("m1")] == ["delivered", "delivered", "recalled", "viewed", "built_on"]
    assert store.uses("m1")[0]["context"] == "S1" and store.uses("nope") == []


def test_use_validation(store):
    with pytest.raises(ValueError):
        store.record_use("m1", "liked", "S1")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        store.record_use("m1", "viewed", "")


# --- the gate bar ---


def test_the_gate_bar_moves_one_step_and_never_below_its_floor(store):
    assert store.gate_bar("energy-dash") is None
    store.set_gate_bar("energy-dash", 0.8, 0.5)
    assert store.gate_bar("energy-dash") == 0.8
    assert store.move_gate_bar("energy-dash", "lower", "re_explanation", step=0.1, floor=0.5, ref="item:m3") == pytest.approx(0.7)
    assert store.move_gate_bar("energy-dash", "raise", "leak", step=0.2, floor=0.5) == pytest.approx(0.9)
    assert store.move_gate_bar("energy-dash", "lower", "presumption", step=0.6, floor=0.5) == 0.5  # stops at the floor
    assert store.move_gate_bar("energy-dash", "lower", "re_explanation", step=0.1, floor=0.5) == 0.5
    assert store.gate_bar("energy-dash") == 0.5


def test_every_move_is_logged(store):
    store.set_gate_bar("p", 0.8, 0.5)
    store.move_gate_bar("p", "lower", "re_explanation", step=0.1, floor=0.5, ref="item:m3")
    store.move_gate_bar("p", "raise", "leak", step=0.1, floor=0.5)
    moves = store.gate_bar_moves("p")
    assert [(m["direction"], m["reason"], m["ref"]) for m in moves] == [("lower", "re_explanation", "item:m3"), ("raise", "leak", None)]
    assert moves[0]["bar_before"] == 0.8 and moves[0]["bar_after"] == pytest.approx(0.7) and moves[1]["bar_before"] == pytest.approx(0.7)
    assert store.gate_bar_moves("other") == []


def test_a_new_floor_is_taken_up(store):
    store.set_gate_bar("p", 0.6, 0.4)
    assert store.move_gate_bar("p", "lower", "re_explanation", step=0.01, floor=0.7) == 0.7
    assert store.conn.execute("SELECT floor FROM gate_bar WHERE project = 'p'").fetchone()[0] == 0.7


def test_gate_bar_rules(store):
    with pytest.raises(ValueError):
        store.set_gate_bar("p", 0.4, 0.5)
    with pytest.raises(KeyError):
        store.move_gate_bar("p", "lower", "leak", step=0.1, floor=0.1)
    store.set_gate_bar("p", 0.8, 0.5)
    with pytest.raises(ValueError):
        store.move_gate_bar("p", "up", "leak", step=0.1, floor=0.5)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        store.move_gate_bar("p", "lower", "boredom", step=0.1, floor=0.5)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        store.move_gate_bar("p", "lower", "leak", step=0, floor=0.5)
    assert store.gate_bar_moves("p") == []


# --- rebuild support ---


def test_clear_derived_empties_the_derived_tables_and_keeps_state(filled):
    filled.put_vector("m1", "e", "line", 1, [1.0])
    filled.put_exchange("x1", source_id="S", user_message_id="u", reply_message_id=None, occurred_at="t", your_text="hello")
    filled.put_history_vector("x1", "e", [1.0])
    filled.put_goal_card("g1", "g", thread_id="T1")
    filled.put_start_note("T1", "n", [], 1)
    filled.set_filtered("m9", "r")
    filled.put_link({"link_id": "l1", "from_id": "m1", "to_id": "m2", "to_kind": "item", "type": "supports", "strength": "checked"})
    filled.record_use("m1", "viewed", "overview")
    filled.set_gate_bar("p", 0.8, 0.5)
    filled.move_gate_bar("p", "lower", "leak", step=0.1, floor=0.5)
    filled.clear_derived()
    for table in index_store.DERIVED_TABLES:
        assert filled.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0, table
    assert filled.use_summary("m1")["viewed"] == 1
    assert filled.gate_bar("p") == pytest.approx(0.7) and len(filled.gate_bar_moves("p")) == 1


def test_derived_tables_are_every_table_but_the_state_ones(store):
    tables = {
        r["name"] for r in store.conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")
        if not r["name"].startswith(("keys_", "history_keys_")) and r["name"] != "schema_version"
    }
    assert tables - set(index_store.DERIVED_TABLES) == set(index_store.STATE_TABLES) == {"use", "gate_bar", "gate_bar_move"}
    assert not set(index_store.STATE_TABLES) & set(index_store.DERIVED_TABLES)


def test_the_docstring_says_a_rebuild_keeps_use_and_the_gate_bar():
    doc = " ".join(index_store.__doc__.split())
    assert "rebuild keeps them" in doc and "`use`, `gate_bar` and `gate_bar_move`" in doc


def test_a_rebuild_keeps_what_use_and_your_corrections_taught_it(filled):
    """The attack: a rebuild that reset the bar would let leaks you flagged through again."""
    filled.set_gate_bar("energy-dash", 0.8, 0.5)
    filled.move_gate_bar("energy-dash", "raise", "leak", step=0.1, floor=0.5, ref="leak-1")
    filled.record_use("m1", "delivered", "chat-1")
    filled.record_use("m1", "viewed", "overview")
    for _ in range(2):  # two rebuilds: clear everything derived, then put the items back
        filled.clear_derived()
        add(filled, "m1", "Readings are stored in SQLite on the Pi, one file per meter")
        assert filled.gate_bar("energy-dash") == pytest.approx(0.9)
        assert [m["reason"] for m in filled.gate_bar_moves("energy-dash")] == ["leak"]
        assert [u["kind"] for u in filled.uses("m1")] == ["delivered", "viewed"]
        assert filled.use_summary("m1")["delivered"] == 1
    assert filled.move_gate_bar("energy-dash", "lower", "re_explanation", step=0.2, floor=0.5) == pytest.approx(0.7)  # no reset to 0.8


def test_a_goal_card_holds_at_most_the_configured_number_of_top_items(open_all):
    assert SQLiteIndexStore(open_all["index"]).goal_card_top_items == index_store.GOAL_CARD_TOP_ITEMS == 8
    small = SQLiteIndexStore(open_all["index"], config={"maintenance": {"goal_card_top_items": 2}})
    small.put_goal_card("g1", "goal", thread_id="T1", top_items=["a", "b"])
    with pytest.raises(ValueError, match="at most 2"):
        small.put_goal_card("g2", "goal", thread_id="T2", top_items=["a", "b", "c"])
    big = SQLiteIndexStore(open_all["index"], config={"maintenance": {"goal_card_top_items": 10}})
    big.put_goal_card("g3", "goal", thread_id="T3", top_items=[str(n) for n in range(10)])
    for bad in (0, 2.5, True, "8"):
        with pytest.raises(ValueError, match="goal_card_top_items"):
            SQLiteIndexStore(open_all["index"], config={"maintenance": {"goal_card_top_items": bad}})


def test_the_goal_card_size_comes_from_the_user_config(isolated_home, open_all):
    from northstar_agent_memory import config

    config.settings_path().parent.mkdir(parents=True, exist_ok=True)
    config.settings_path().write_text("[maintenance]\ngoal_card_top_items = 3\n", encoding="utf-8")
    assert SQLiteIndexStore(open_all["index"]).goal_card_top_items == 3


# --- tenants ---


def test_another_tenant_sees_nothing(open_all, filled):
    # The schema's primary keys do not include tenant_id, so a second tenant must use ids of its own (reported).
    other = SQLiteIndexStore(open_all["index"], tenant_id="acme")
    assert other.item_lines() == [] and other.search_keys("readings") == [] and other.gate_bar("p") is None
    other.put_item_line(line("a1", "acme readings"))
    other.put_keys("a1", line="acme readings")
    assert [h[0] for h in other.search_keys("readings")] == ["a1"]
    assert filled.item_line("a1") is None and "a1" not in [h[0] for h in filled.search_keys("readings")]
    assert other.item_line("a1")["tenant_id"] == "acme"
    other.clear_derived()
    assert other.item_lines() == [] and filled.item_line("m1") is not None and filled.search_keys("SQLite")


def test_state_survives_reopening(store_root):
    s = SQLiteIndexStore.open(store_root)
    add(s, "m1", "Readings are stored in SQLite")
    s.close()
    again = SQLiteIndexStore.open(store_root)
    assert again.search_keys("SQLite")[0][0] == "m1"
    again.close()


def test_an_item_kept_out_of_the_index_is_not_found(store, filled):
    assert [h.item_id for h in store.search(SearchQuery(text="SQLite readings", direction="pull"))][:1] == ["m1"]
    store.set_filtered("m1", "its source turn was not yours")
    assert "m1" not in [h.item_id for h in store.search(SearchQuery(text="SQLite readings", direction="pull"))]
    assert "m1" not in [h.item_id for h in store.search(SearchQuery(text="SQLite readings", direction="push", project="energy-dash"))]
