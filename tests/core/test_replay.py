"""Replay: rebuild memory from the event log alone, hash it, compare it (MEMORY-ARCHITECTURE §3.1, I18).

The random streams are valid by construction: each step reads the live tables, picks a move that is allowed now, and
appends its events. Seeds are fixed. Every fixture is invented.
"""

from __future__ import annotations

import json
import random
import sqlite3

import pytest

from northstar_agent_memory.core import db, events
from northstar_agent_memory.core.events import EVENT_TYPES, PLAIN_ITEM_KINDS
from northstar_agent_memory.core.projector import ProjectionError
from northstar_agent_memory.core.reader import HISTORY_TABLES, SQLiteMemoryReader, row_as_of
from northstar_agent_memory.core.replay import (
    CURRENT_STATE_TABLES,
    HISTORY_STATE_TABLES,
    append_event,
    canonical_hash,
    rebuild,
    rebuild_from,
    scratch_store,
    table_hashes,
    verify_replay,
)

from .projection_helpers import Log, evidence_op, history, row, seed_item, seed_topic
from .test_projector import batch, link_fields, place

SCOPES = ["personal", "project:alpha", "project:beta", "work:acme"]
SEEDS = [1, 2, 3, 4, 5, 6, 7, 8]
SCRUBBED = {"evidence": ("quote",), "link": ("reason",)}  # words a purge scrubs from earlier states


# --- the random event streams ----------------------------------------------------------------------------------------


class Sim:
    """Appends random valid moves to a Log, deciding each from the live tables."""

    def __init__(self, log: Log, seed: int):
        self.log, self.rng, self.n = log, random.Random(seed), 0
        self.last: tuple[list[str], bool] | None = None  # the last proposal's event ids, and whether it can be rolled back
        self.checkpoints: list[tuple[int, dict]] = []
        self.as_of_before_purge: list[tuple[int, dict]] = []
        self.purged_ids: set[str] = set()

    # helpers
    def nid(self, prefix: str) -> str:
        self.n += 1
        return f"{prefix}{self.n}"

    def q(self, sql: str, *args) -> list[dict]:
        return [dict(r) for r in self.log.conn.execute(sql, args)]

    def pick(self, rows: list[dict]) -> dict | None:
        return self.rng.choice(rows) if rows else None

    def items(self, where: str = "", *args) -> list[dict]:
        return self.q(f"SELECT * FROM item WHERE status = 'active' AND merged_into IS NULL {where} ORDER BY id", *args)

    def evidence(self, subject_id: str, subject_kind: str = "item", **fields):
        evidence_id = self.nid("ev")
        op = evidence_op(evidence_id, subject_id, subject_kind=subject_kind, message_id=self.nid("A"),
                         quote=f"quote {self.n}", end_char=5 + self.n % 7, **fields)  # fmt: skip
        return evidence_id, op

    def live_topics(self, where: str = "") -> list[dict]:
        return self.q(f"SELECT * FROM topic WHERE status IN ('active', 'dormant') {where} ORDER BY id")

    # items
    def new_item(self):
        kind, origin = self.rng.choice(PLAIN_ITEM_KINDS), self.rng.choice(["yours", "adopted:claude-code"])
        item_id = self.nid("m")
        ev1, op1 = self.evidence(item_id)
        ops, evs = [op1], [ev1]
        if self.rng.random() < 0.4:
            ev2, op2 = self.evidence(item_id, role="support")
            ops.append(op2), evs.append(ev2)
        fields = dict(item_id=item_id, kind=kind, line=f"{kind} line {self.n}", scope=self.rng.choice(SCOPES[:3]),
                      learned_in=self.rng.choice("ABC"), origin=origin, evidence_ids=evs, said_at="2026-03-02T09:30:00Z",
                      your_words="", why="", question_key="", applies_when="unknown", valid_from=None, valid_to=None, time_bound=False)  # fmt: skip
        if self.rng.random() < 0.3:
            fields.update(valid_from="2026-03-01", valid_to="2026-04-01", time_bound=True)
        stance = "stated" if origin == "yours" else "adopted"
        return ops + [("item.created", fields), ("stance.recorded", {"item_id": item_id, "stance": stance, "evidence_ids": evs})]

    def revise(self):
        item = self.pick(self.items())
        if item is None:
            return None
        fields = dict(item_id=item["id"], base_version=item["version"], line=f"revised {self.n}",
                      reason=self.rng.choice(["restated", "your_revision"]), time_bound=self.rng.choice([None, True, False]),
                      why=self.rng.choice([None, "new why"]))  # fmt: skip
        return [("item.revised", fields)]

    def value(self):
        item = self.pick(self.items("AND value = 'forming'"))
        return item and [("item.value_changed", {"item_id": item["id"], "signal": "later_day", "evidence_ids": []})]

    def widen(self):
        item = self.pick(self.items("AND scope LIKE 'project:%'"))
        if item is None:
            return None
        ev = self.pick(self.q("SELECT id FROM evidence WHERE subject_id = ?", item["id"]))
        if ev is None:
            return None
        return [("item.scope_widened", dict(item_id=item["id"], base_version=item["version"], from_scope=item["scope"],
                                            evidence_ids=[ev["id"]]))]  # fmt: skip

    def status(self):
        item = self.pick(self.q("SELECT * FROM item WHERE status IN ('active', 'quarantined') AND merged_into IS NULL ORDER BY id"))
        if item is None:
            return None
        to = "active" if item["status"] == "quarantined" else self.rng.choice(["quarantined", "retracted"])
        return [("item.status_changed", dict(item_id=item["id"], from_status=item["status"], to_status=to, reason="a reason", ref=None))]

    def check(self):
        item = self.pick(self.items("AND check_status = 'unchecked'"))
        return item and [("item.checked", dict(item_id=item["id"], check_status=self.rng.choice(["checked", "not_independent"]),
                                               checker_family="openai", evidence_ids=[]))]  # fmt: skip

    # links
    def link_new(self):
        a, b = self.rng.sample(self.items(), 2) if len(self.items()) >= 2 else (None, None)
        if a is None:
            return None
        fields = link_fields(self.nid("l"), a["id"], b["id"], self.rng.choice(["supports", "refines", "answers", "case_of"]))
        return [(self.rng.choice(["link.proposed", "link.applied"]), fields)]

    def link_step(self):
        link = self.pick(self.q(
            "SELECT l.* FROM link l JOIN item a ON a.id = l.from_id JOIN item b ON b.id = l.to_id WHERE l.type <> 'same_as'"
            " AND l.to_kind = 'item' AND l.status IN ('proposed', 'applied', 'confirmed') AND a.status <> 'purged'"
            " AND b.status <> 'purged' ORDER BY l.id"))  # fmt: skip
        if link is None:
            return None
        nxt = {"proposed": ["applied", "rejected", "retracted"], "applied": ["confirmed", "rejected", "retracted"],
               "confirmed": ["retracted", "rejected"]}[link["status"]]  # fmt: skip
        to = self.rng.choice(nxt)
        if to == "applied":
            return [("link.applied", link_fields(link["id"], link["from_id"], link["to_id"], link["type"], reason=link["reason"],
                                                 stated_by=link["stated_by"], checked_by=["openai"]))]  # fmt: skip
        if to == "retracted":
            return [("link.retracted", {"link_id": link["id"], "reason": "withdrawn"})]
        return [(f"link.{to}", {"link_id": link["id"], "via": "click", "evidence_id": None})]

    def same_as(self):
        pool = self.items()
        if len(pool) < 2:
            return None
        a, b = self.rng.sample(pool, 2)
        return [("link.applied", link_fields(self.nid("l"), a["id"], b["id"], "same_as", checked_by=["claude", "openai"]))]

    def unmerge(self):
        link = self.pick(self.q(
            "SELECT l.* FROM link l JOIN item a ON a.id = l.from_id JOIN item b ON b.id = l.to_id WHERE l.type = 'same_as'"
            " AND l.status IN ('applied', 'confirmed') AND a.status = 'superseded' AND a.merged_into = l.to_id"
            " AND b.merged_into IS NULL AND b.status <> 'purged' ORDER BY l.id"))  # fmt: skip
        if link is None:
            return None
        if self.rng.random() < 0.5:
            return [("link.retracted", {"link_id": link["id"], "reason": "you said they differ"})]
        return [("link.rejected", {"link_id": link["id"], "via": "click", "evidence_id": None})]

    # supersession
    def supersede(self):
        pool = self.items()
        if len(pool) < 2:
            return None
        old, new = self.rng.sample(pool, 2)
        return [("supersession.applied", dict(supersession_id=self.nid("s"), old_item=old["id"], old_version=old["version"],
                                              new_item=new["id"], new_version=None, reason="your_later_statement", evidence_ids=[]))]  # fmt: skip

    def supersede_undo(self):
        sup = self.pick(self.q(
            "SELECT s.* FROM supersession s JOIN item o ON o.id = s.old_item WHERE s.status = 'applied' AND s.old_item <> s.new_item"
            " AND o.status = 'superseded' AND o.merged_into IS NULL ORDER BY s.id"))  # fmt: skip
        return sup and [("supersession.undone", {"supersession_id": sup["id"], "reason": "audit disagreed"})]

    def refresh(self):
        item = self.pick(self.items())
        if item is None:
            return None
        return [("item.revised", dict(item_id=item["id"], base_version=item["version"], line=f"refreshed {self.n}", reason="refresh",
                                      time_bound=None, why=None)),  # fmt: skip
                ("supersession.applied", dict(supersession_id=self.nid("s"), old_item=item["id"], old_version=item["version"],
                                              new_item=item["id"], new_version=item["version"] + 1, reason="refresh", evidence_ids=[]))]  # fmt: skip

    def refresh_undo(self):
        sup = self.pick(self.q(
            "SELECT s.* FROM supersession s JOIN item o ON o.id = s.old_item WHERE s.status = 'applied' AND s.old_item = s.new_item"
            " AND o.status = 'active' AND o.merged_into IS NULL AND o.version > s.old_version ORDER BY s.id"))  # fmt: skip
        return sup and [("supersession.undone", {"supersession_id": sup["id"], "reason": "audit disagreed"})]

    # conflicts
    def conflict_open(self):
        pool = self.items()
        if len(pool) < 2:
            return None
        a, b = self.rng.sample(pool, 2)
        kind = self.rng.choice(["across_contexts", "same_context"])
        state = "both_stand" if kind == "across_contexts" else self.rng.choice(["open", "contested"])
        return [("conflict.opened", dict(conflict_id=self.nid("c"), side_a_item=a["id"], side_a_version=a["version"],
                                         side_b_item=b["id"], side_b_version=b["version"], kind=kind, state=state,
                                         question_id=None, link_id=None, recheck_after=None))]  # fmt: skip

    def conflict_step(self):
        conflict = self.pick(self.q("SELECT * FROM conflict WHERE state <> 'undone' ORDER BY id"))
        if conflict is None:
            return None
        move = self.rng.choice(["resolve", "resolve", "reopen", "undo"])
        if move == "reopen" and conflict["state"] == "open":
            move = "undo"
        if move == "undo":
            latest = self.q("SELECT e.id FROM event e, json_each(e.subjects) j WHERE j.value = ? AND e.type IN ('conflict.opened',"
                            " 'conflict.resolved', 'conflict.reopened') ORDER BY e.seq DESC LIMIT 1", conflict["id"])  # fmt: skip
            at = self.q("SELECT type FROM event WHERE seq = ?", conflict["seq_from"])
            plain = at and at[0]["type"] in ("conflict.opened", "conflict.resolved", "conflict.reopened")
            fields = {"conflict_id": conflict["id"], "reason": "audit disagreed"}
            return [("conflict.undone", fields, {} if plain and self.rng.random() < 0.3 else {"compensates": latest[0]["id"]})]
        if move == "reopen":
            return [("conflict.reopened", dict(conflict_id=conflict["id"], reason="recheck", state=self.rng.choice(["open", "contested"]),
                                               recheck_after=None))]  # fmt: skip
        step = self.rng.choice([1, 2, 3])
        fields = dict(conflict_id=conflict["id"], step=step, state={1: "both_stand", 2: "resolved", 3: "contested"}[step],
                      rule_version="rules-1", resolution_inputs=["e1"], winner=conflict["side_a_item"] if step == 2 else None,
                      question_id=None, recheck_after="2026-06-01" if step == 3 else None)  # fmt: skip
        return [("conflict.resolved", fields)]

    # goals and questions
    def goal(self):
        item_id = self.nid("m")
        ev, op = self.evidence(item_id)
        fields = dict(item_id=item_id, line=f"goal {self.n}", scope=self.rng.choice(SCOPES[:3]), learned_in="C", said_at="2026-03-09T08:00:00Z",
                      basis=self.rng.choice(["stated", "reported", "reused"]), evidence_ids=[ev], work_id=None, origin="yours",
                      your_words="", why="", applies_when="unknown")  # fmt: skip
        return [op, ("goal.created", fields)]

    def goal_status(self):
        goal = self.pick(self.items("AND kind = 'goal'"))
        if goal is None:
            return None
        to = self.rng.choice([s for s in ["active", "paused", "done", "dropped"] if s != goal["goal_status"]])
        return [("goal.status_changed", dict(item_id=goal["id"], from_status=goal["goal_status"], to_status=to, evidence_ids=[]))]

    def goal_confirm(self):
        goal = self.pick(self.items("AND kind = 'goal' AND goal_basis <> 'stated'"))
        ev = goal and self.pick(self.q("SELECT id FROM evidence WHERE subject_id = ?", goal["id"]))
        return ev and [("goal.confirmed", {"item_id": goal["id"], "evidence_ids": [ev["id"]]})]

    def question(self):
        item_id = self.nid("m")
        ev, op = self.evidence(item_id)
        fields = dict(item_id=item_id, line=f"question {self.n}?", scope=self.rng.choice(SCOPES[:3]), learned_in="C",
                      said_at="2026-03-11T08:00:00Z", raised_by=self.rng.choice(["you", "ai_taken_up", "conflict"]),
                      evidence_ids=[ev], your_words="", question_key="", origin="yours")  # fmt: skip
        return [op, ("question.created", fields)]

    def question_status(self):
        question = self.pick(self.items("AND kind = 'question'"))
        if question is None:
            return None
        to = self.rng.choice([s for s in ["open", "answered", "dormant"] if s != question["question_status"]])
        by = [self.pick(self.items("AND kind <> 'question'") or [{"id": "m0"}])["id"]] if to == "answered" else []
        return [("question.status_changed", dict(item_id=question["id"], from_status=question["question_status"], to_status=to, answered_by=by))]

    # work, style, corrections, scopes
    def work(self):
        work_id = self.nid("w")
        ops = [("work.registered", dict(work_id=work_id, kind=self.rng.choice(["commit", "file_version", "render"]), ref=f"ref{self.n}",
                                        evidence=self.rng.choice(["strong", "medium", "weak"]), work_event_id=self.nid("we"),
                                        label="a label", project="energy-dash", snapshot_sha256=None, occurred_at=None,
                                        label_source="commit_message"))]  # fmt: skip
        item = self.pick(self.items())
        if item is not None and self.rng.random() < 0.6:
            ops.append(("link.applied", dict(link_id=self.nid("l"), from_id=item["id"], to_id=work_id, link_type="used_in",
                                             reason="same session", stated_by="construction", to_kind="work", checked_by=[])))  # fmt: skip
        return ops

    def label(self):
        work = self.pick(self.q("SELECT id FROM work ORDER BY id"))
        return work and [("work.labelled", dict(work_id=work["id"], label=f"label {self.n}", label_source="checked"))]

    def style(self):
        style_id = self.nid("st")
        ev, op = self.evidence(style_id, subject_kind="style_line")
        return [op, ("style.recorded", dict(style_id=style_id, line=f"style {self.n}", scope=self.rng.choice(SCOPES),
                                            basis=self.rng.choice(["stated_default", "seen_in_sessions"]), evidence_ids=[ev]))]  # fmt: skip

    def style_revise(self):
        style = self.pick(self.q("SELECT id FROM style_line WHERE status = 'active' ORDER BY id"))
        if style is None:
            return None
        if self.rng.random() < 0.3:
            return [("style.revised", dict(style_id=style["id"], reason="not true", line=None, status="retracted", evidence_ids=[]))]
        return [("style.revised", dict(style_id=style["id"], reason="reworded", line=f"style {self.n}", status=None, evidence_ids=[]))]

    def correction(self):
        target = self.pick(self.q("SELECT id FROM item ORDER BY id") + self.q("SELECT id FROM topic ORDER BY id"))
        if target is None:
            return None
        return [("correction.applied", dict(correction_id=self.nid("co"), kind=self.rng.choice(["rename", "pin", "keep"]), target=target["id"],
                                            via="click", at="2026-03-10T10:00:00Z", constraint={"n": self.n}, evidence_id=None,
                                            params={"label": f"x{self.n}"}))]  # fmt: skip

    def correction_lift(self):
        correction = self.pick(self.q("SELECT id FROM correction WHERE status = 'active' ORDER BY id"))
        return correction and [("correction.lifted", dict(correction_id=correction["id"], reason=self.rng.choice(["your_undo", "your_later_correction"])))]

    def scope(self):
        scope_id = self.rng.choice(SCOPES)
        current = row(self.log.conn, "scope", scope_id)
        held = not (current and current["held"])
        return [("scope.hold_changed", dict(scope_id=scope_id, held=held, reason="you changed it"))]

    # topics and placement
    def topic_new(self):
        anchor = self.pick(self.items()) or {"id": "anchor"}
        return [("topic.created", dict(topic_id=self.nid("t"), label=f"Topic {self.n}", anchor_id=anchor["id"], parent_id=None,
                                       label_fixed=False, formation_overlap=None))]  # fmt: skip

    def topic_sub(self):
        parent = self.pick(self.live_topics("AND parent_id IS NULL"))
        return parent and [("topic.created", dict(topic_id=self.nid("t"), label=f"Sub {self.n}", anchor_id="anchor", parent_id=parent["id"],
                                                  label_fixed=False, formation_overlap=0.3))]  # fmt: skip

    def topic_rename(self):
        topic = self.pick(self.q("SELECT * FROM topic ORDER BY id"))
        return topic and [("topic.renamed", dict(topic_id=topic["id"], old_label=topic["label"], label=f"Renamed {self.n}",
                                                 label_fixed=self.rng.random() < 0.5, reason="you renamed it"))]  # fmt: skip

    def topic_dormant(self):
        topic = self.pick(self.live_topics())
        if topic is None:
            return None
        to = "active" if topic["status"] == "dormant" else "dormant"
        return [("topic.dormant", dict(topic_id=topic["id"], to_status=to, reason="activity changed"))]

    def topic_merge(self):
        pool = self.live_topics()
        if len(pool) < 2:
            return None
        a, b = self.rng.sample(pool, 2)
        return [("topic.merged", dict(from_topic_id=a["id"], into_topic_id=b["id"], reason="same thing"))]

    def topic_fold(self):
        topic = self.pick(self.live_topics("AND parent_id IS NOT NULL"))
        return topic and [("topic.folded_back", dict(topic_id=topic["id"], into_parent_id=topic["parent_id"], reason="thinned"))]

    def topic_branch(self):
        topic = self.pick(self.live_topics("AND parent_id IS NOT NULL"))
        return topic and [("topic.branched", dict(topic_id=topic["id"], old_parent_id=topic["parent_id"], reason="separated"))]

    def topic_split(self):
        topic = self.pick(self.live_topics())
        if topic is None:
            return None
        a, b = self.nid("t"), self.nid("t")
        return [("topic.split", dict(topic_id=topic["id"], redirect_to=a, formation_overlap=0.5, reason="two clusters",
                                     new_topics=[{"topic_id": a, "label": f"Left {self.n}", "anchor_id": "anchor"},
                                                 {"topic_id": b, "label": f"Right {self.n}", "anchor_id": "anchor"}]))]  # fmt: skip

    def idea_place(self):
        item, topic = self.pick(self.items()), self.pick(self.live_topics())
        if item is None or topic is None:
            return None
        mine = self.q("SELECT * FROM placement WHERE item_id = ?", item["id"])
        here = next((p for p in mine if p["topic_id"] == topic["id"]), None)
        also = sum(1 for p in mine if p["role"] == "also_in")
        if not mine:
            role, tentative = "home", self.rng.random() < 0.5
        elif here is not None:
            role, tentative = here["role"], False
        elif self.rng.random() < 0.3:
            role, tentative = "home", False
        elif also < 2:
            role, tentative = "also_in", self.rng.random() < 0.5
        else:
            return None
        return [("idea.placed", dict(placement_id=self.nid("p"), item_id=item["id"], topic_id=topic["id"], role=role, tentative=tentative,
                                     reasons=["same chat"]))]  # fmt: skip

    def idea_move(self):
        place_row = self.pick(self.q(
            "SELECT p.* FROM placement p JOIN item i ON i.id = p.item_id JOIN topic t ON t.id = p.topic_id"
            " WHERE i.status = 'active' AND i.merged_into IS NULL AND t.status IN ('active', 'dormant') ORDER BY p.id"))  # fmt: skip
        if place_row is None:
            return None
        taken = {p["topic_id"] for p in self.q("SELECT topic_id FROM placement WHERE item_id = ?", place_row["item_id"])}
        target = self.pick([t for t in self.live_topics() if t["id"] not in taken])
        if target is None:
            return None
        return [("idea.moved", dict(item_id=place_row["item_id"], from_topic_id=place_row["topic_id"], to_topic_id=target["id"],
                                    role=place_row["role"], tentative=False, reason="your move correction"))]  # fmt: skip

    # rollback and purge
    def rollback(self):
        if self.last is None or not self.last[1]:
            return None
        return [("compensation.batch", dict(batch_id=self.nid("b"), reason="audit disagreed", compensated_event_ids=self.last[0],
                                            run_id_undone=None))]  # fmt: skip

    def purge(self):
        pool = self.q("SELECT id FROM item WHERE status <> 'purged' ORDER BY id")
        picked = self.rng.sample(pool, min(2, len(pool)))
        return [("purge.applied", dict(purge_id=self.nid("pg"), item_ids=[p["id"] for p in picked], requested_at="2026-04-01T09:00:00Z"))]

    WEIGHTS = [
        ("new_item", 14), ("revise", 6), ("value", 4), ("widen", 3), ("status", 5), ("check", 3), ("link_new", 6), ("link_step", 6),
        ("same_as", 4), ("unmerge", 2), ("supersede", 4), ("supersede_undo", 2), ("refresh", 3), ("refresh_undo", 2),
        ("conflict_open", 4), ("conflict_step", 5), ("goal", 3), ("goal_status", 3), ("goal_confirm", 2), ("question", 3),
        ("question_status", 2), ("work", 3), ("label", 2), ("style", 3), ("style_revise", 2), ("correction", 3),
        ("correction_lift", 2), ("scope", 2), ("topic_new", 4), ("topic_sub", 3), ("topic_rename", 3), ("topic_dormant", 3),
        ("topic_merge", 2), ("topic_fold", 2), ("topic_branch", 2), ("topic_split", 2), ("idea_place", 9), ("idea_move", 4),
        ("rollback", 5),
    ]  # fmt: skip

    def step(self, action: str | None = None):
        names = [name for name, weight in self.WEIGHTS for _ in range(weight)]
        for _ in range(30):
            name = action or self.rng.choice(names)
            ops = getattr(self, name)()
            if ops:
                break
        else:
            return
        evs = self.log.run(*ops)
        undoable = name != "rollback" and "purge.applied" not in {e.type for e in evs}
        self.last = ([e.id for e in evs], undoable)
        if self.rng.random() < 0.12:
            self.checkpoints.append((self.log.conn.execute("SELECT MAX(seq) FROM event").fetchone()[0], self.snapshot()))

    def run(self, steps: int):
        for _ in range(steps):
            self.step()

    def snapshot(self) -> dict:
        return {t: {r["id"]: dict(r) for r in self.log.conn.execute(f"SELECT * FROM {t}")} for t in HISTORY_TABLES}


def stream(seed: int, conn, *, before_purge: int = 150, after_purge: int = 70) -> Sim:
    sim = Sim(Log(conn), seed)
    sim.run(before_purge)
    sim.checkpoints.append((conn.execute("SELECT MAX(seq) FROM event").fetchone()[0], sim.snapshot()))
    sim.as_of_before_purge = list(sim.checkpoints)
    sim.checkpoints.clear()
    sim.step("purge")
    sim.purged_ids = {r["id"] for r in sim.q("SELECT id FROM item WHERE status = 'purged'")}
    sim.run(after_purge)
    return sim


@pytest.fixture(scope="module")
def sims(tmp_path_factory):
    """One finished random stream per seed, each in its own memory.db."""
    built = {}
    for seed in SEEDS:
        conn = db.open_store("memory", tmp_path_factory.mktemp(f"sim{seed}"))
        built[seed] = stream(seed, conn)
    yield built
    for sim in built.values():
        sim.log.conn.close()


# --- hashing ---------------------------------------------------------------------------------------------------------


def two_item_log(conn):
    log = Log(conn)
    seed_item(log, "m1")
    seed_item(log, "m2")
    log.add("link.applied", link_fields())
    return log


def test_the_hash_covers_the_current_state_tables(memory):
    assert set(CURRENT_STATE_TABLES) == set(HISTORY_TABLES) | {"stance"} and len(CURRENT_STATE_TABLES) == 12
    assert set(table_hashes(memory)) == set(CURRENT_STATE_TABLES)
    assert set(table_hashes(memory, include_history=True)) == set(CURRENT_STATE_TABLES) | set(HISTORY_STATE_TABLES)


def test_an_empty_memory_has_a_stable_hash(memory, tmp_path):
    other = db.open_store("memory", tmp_path / "other")
    assert canonical_hash(memory) == canonical_hash(other)
    other.close()


def test_the_hash_changes_with_any_row_and_any_column(memory):
    log = two_item_log(memory)
    base = canonical_hash(memory)
    assert canonical_hash(memory) == base and len(base) == 64
    memory.execute("UPDATE item SET why = 'x' WHERE id = 'm1'")
    changed = canonical_hash(memory)
    assert changed != base
    memory.execute("UPDATE item SET why = '' WHERE id = 'm1'")
    assert canonical_hash(memory) == base
    memory.execute("PRAGMA foreign_keys=OFF")  # keys lead with tenant_id, so a lone tenant change is a broken reference
    memory.execute("UPDATE item SET tenant_id = 'acme' WHERE id = 'm1'")
    assert canonical_hash(memory) != base
    log.add("item.value_changed", {"item_id": "m1"})
    assert canonical_hash(memory) != base


# --- append and rebuild ----------------------------------------------------------------------------------------------


def test_append_event_assigns_the_next_seq_and_writes_subjects(memory):
    log = Log(memory)
    evs = seed_item(log, "m1")
    assert [e.seq for e in evs] == [1, 2]
    assert [tuple(r) for r in memory.execute("SELECT subject_id, seq FROM event_subject ORDER BY seq, subject_id")] == [
        ("ev-m1", 1), ("m1", 1), ("m1", 2)]
    stored = memory.execute("SELECT * FROM event WHERE seq = 2").fetchone()
    assert stored["id"] == evs[1].id and json.loads(stored["payload"])["item_id"] == "m1" and stored["tenant_id"] == "local"


def test_append_event_keeps_a_seq_it_is_given(memory):
    env = events.make_event("scope.hold_changed", {"scope_id": "personal", "held": True, "reason": "x"}, actor="code:t", config_version="c")
    env.recorded_at, env.seq = "2026-03-02T09:30:00.000Z", 40
    with db.transaction(memory):
        assert append_event(memory, env) == 40
    assert memory.execute("SELECT seq FROM event").fetchone()[0] == 40


def test_rebuild_from_a_file_gives_the_same_memory(memory, store_root):
    two_item_log(memory)
    log = Log(memory)
    log.count = 10
    log.add("item.revised", {"item_id": "m1", "line": "Changed", "reason": "restated"})
    log.add("topic.created", dict(topic_id="t1", label="T", anchor_id="m1", parent_id=None))
    rebuilt = rebuild(store_root / "memory.db")
    try:
        assert canonical_hash(rebuilt) == canonical_hash(memory)
        assert canonical_hash(rebuilt, include_history=True) == canonical_hash(memory, include_history=True)
        assert row(rebuilt, "item", "m1")["version"] == 2
        assert [r["seq"] for r in rebuilt.execute("SELECT seq FROM event ORDER BY seq")] == list(range(1, 8))
    finally:
        rebuilt.close()


def test_rebuild_uses_the_event_log_alone(memory, store_root, tmp_path):
    two_item_log(memory)
    log = Log(memory)
    log.count = 10
    log.add("item.value_changed", {"item_id": "m1"})
    want = canonical_hash(memory)
    copy = tmp_path / "copy.db"
    target = sqlite3.connect(copy)
    memory.backup(target)
    target.execute("PRAGMA foreign_keys=OFF")
    target.execute("DROP TRIGGER evidence_no_delete")  # the copy is damaged on purpose: its rows are not the log's to keep
    for table in HISTORY_TABLES:
        target.execute(f"DELETE FROM {table}")
    target.commit()
    target.close()
    rebuilt = rebuild(copy)
    try:
        assert canonical_hash(rebuilt) == want
    finally:
        rebuilt.close()


def test_rebuild_does_not_change_the_source(memory, store_root):
    two_item_log(memory)
    before = canonical_hash(memory, include_history=True)
    rebuild(store_root / "memory.db").close()
    assert canonical_hash(memory, include_history=True) == before
    assert memory.execute("SELECT COUNT(*) FROM event").fetchone()[0] == 5


def test_rebuild_needs_an_empty_destination(memory):
    two_item_log(memory)
    full = rebuild_from(memory)
    with pytest.raises(ValueError, match="empty"):
        rebuild_from(memory, full)
    full.close()


def test_rebuild_of_an_empty_log_is_empty(memory):
    rebuilt = rebuild_from(memory)
    assert canonical_hash(rebuilt) == canonical_hash(scratch_store())
    rebuilt.close()


def test_rebuild_keeps_the_tenant_of_the_log(tmp_path):
    conn = db.open_store("memory", tmp_path / "acme")
    log = Log(conn, tenant_id="acme")
    seed_item(log, "m1")
    report = verify_replay(conn)
    assert report.ok
    conn.close()


def test_rebuild_refuses_an_event_it_cannot_project(memory):
    log = two_item_log(memory)
    memory.execute("DROP TRIGGER event_no_update")
    memory.execute("DROP TRIGGER event_frozen")
    memory.execute("UPDATE event SET schema_version = 2 WHERE seq = 2")
    with pytest.raises(ProjectionError, match="I15"):
        rebuild_from(memory)
    assert log.count == 5


# --- verify_replay on a hand-made log --------------------------------------------------------------------------------


def test_a_clean_memory_verifies(memory):
    two_item_log(memory)
    report = verify_replay(memory)
    assert report.ok and report.mismatched_tables == [] and report.differences == []
    assert report.live_hash == report.replay_hash and len(report.live_hash) == 64


def test_an_empty_memory_verifies(memory):
    assert verify_replay(memory).ok


def test_a_corrupted_current_row_is_detected(memory):
    two_item_log(memory)
    memory.execute("UPDATE item SET line = 'edited by hand' WHERE id = 'm2'")
    report = verify_replay(memory)
    assert not report.ok and report.live_hash != report.replay_hash
    assert report.mismatched_tables == ["item"]
    assert report.differences == ["item m2: line differs"]


def test_a_row_with_no_event_behind_it_is_detected(memory):
    two_item_log(memory)
    memory.execute("INSERT INTO scope (id, kind, held, held_seq, created_seq, seq_from) VALUES ('personal', 'personal', 0, NULL, 1, 1)")
    report = verify_replay(memory)
    assert not report.ok and report.differences == ["scope personal: in memory, not in the replay"]


def test_a_missing_row_is_detected(memory):
    two_item_log(memory)
    memory.execute("PRAGMA foreign_keys=OFF")
    memory.execute("DELETE FROM link WHERE id = 'l1'")
    report = verify_replay(memory)
    assert not report.ok and report.differences == ["link l1: in the replay, not in memory"]


def test_a_changed_seq_marker_is_detected(memory):
    two_item_log(memory)
    memory.execute("UPDATE item SET seq_from = seq_from + 1 WHERE id = 'm1'")
    report = verify_replay(memory)
    assert not report.ok and report.differences == ["item m1: seq_from differs"]


def test_a_changed_row_history_is_detected(memory):
    log = two_item_log(memory)
    log.add("item.revised", {"item_id": "m1", "line": "Changed", "reason": "restated"})
    memory.execute("DROP TRIGGER item_history_no_update")
    memory.execute("UPDATE item_history SET snapshot = replace(snapshot, 'Line of m1', 'Altered') WHERE id = 'm1'")
    report = verify_replay(memory)
    assert not report.ok and report.mismatched_tables == ["item_history"]
    assert report.differences == ["item_history m1/2: snapshot differs"]


def test_a_deleted_history_row_is_detected(memory):
    log = two_item_log(memory)
    log.add("item.revised", {"item_id": "m1", "line": "Changed", "reason": "restated"})
    memory.execute("DROP TRIGGER item_history_no_delete")
    memory.execute("DELETE FROM item_history")
    assert verify_replay(memory).mismatched_tables == ["item_history"]


def test_the_differences_are_capped(memory):
    log = Log(memory)
    for i in range(70):
        seed_item(log, f"m{i}")
    memory.execute("UPDATE item SET why = 'x'")
    report = verify_replay(memory)
    assert not report.ok and len(report.differences) == 50


def test_a_plain_connection_can_be_verified(memory, store_root):
    two_item_log(memory)
    plain = sqlite3.connect(store_root / "memory.db")
    assert verify_replay(plain).ok
    plain.close()


# --- random streams --------------------------------------------------------------------------------------------------


def test_the_streams_are_a_few_hundred_events_each(sims):
    for seed, sim in sims.items():
        assert 250 <= len(sim.log.events) <= 900, seed


def test_the_streams_use_every_event_type(sims):
    used = {e.type for sim in sims.values() for e in sim.log.events}
    assert used == set(EVENT_TYPES), sorted(set(EVENT_TYPES) - used)


@pytest.mark.parametrize("seed", SEEDS)
def test_a_random_stream_replays_identically(sims, seed):
    conn = sims[seed].log.conn
    report = verify_replay(conn)
    assert report.ok, report.differences
    replayed = rebuild_from(conn)
    try:
        assert canonical_hash(replayed) == canonical_hash(conn)
        assert canonical_hash(replayed, include_history=True) == canonical_hash(conn, include_history=True)
    finally:
        replayed.close()


@pytest.mark.parametrize("seed", SEEDS)
def test_a_replay_is_repeatable(sims, seed):
    conn = sims[seed].log.conn
    hashes = []
    for _ in range(2):
        again = rebuild_from(conn)
        hashes.append(canonical_hash(again, include_history=True))
        again.close()
    assert hashes[0] == hashes[1]


@pytest.mark.parametrize("seed", SEEDS)
def test_a_random_stream_leaves_the_tables_consistent(sims, seed):
    conn = sims[seed].log.conn
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    homes = conn.execute("SELECT item_id, COUNT(*) FROM placement WHERE role = 'home' GROUP BY item_id HAVING COUNT(*) > 1").fetchall()
    assert homes == []
    also = conn.execute("SELECT item_id FROM placement WHERE role = 'also_in' GROUP BY item_id HAVING COUNT(*) > 2").fetchall()
    assert also == []
    # row history never overlaps and every interval is closed after it opened
    for table in HISTORY_TABLES:
        spans = conn.execute(f"SELECT id, seq_from, seq_to FROM {table}_history ORDER BY id, seq_from").fetchall()
        for a, b in zip(spans, spans[1:]):
            assert a["seq_to"] > a["seq_from"]
            if a["id"] == b["id"]:
                assert a["seq_to"] <= b["seq_from"], (table, a["id"])
        current = {r["id"]: r["seq_from"] for r in conn.execute(f"SELECT id, seq_from FROM {table}")}
        for span in spans:
            if span["id"] in current:
                assert span["seq_to"] <= current[span["id"]], (table, span["id"])


@pytest.mark.parametrize("seed", SEEDS)
def test_as_of_reads_give_back_every_earlier_state(sims, seed):
    sim = sims[seed]
    conn = sim.log.conn
    for checkpoints in (sim.as_of_before_purge, sim.checkpoints):
        assert checkpoints
        for seq, snap in checkpoints:
            for table, rows in snap.items():
                known = {r["id"] for r in conn.execute(f"SELECT id FROM {table}")} | {r["id"] for r in conn.execute(f"SELECT id FROM {table}_history")}
                for row_id, expected in rows.items():
                    now = row_as_of(conn, table, row_id, seq)
                    touches = {row_id, *(expected.get(k) for k in ("item_id", "subject_id", "from_id", "to_id"))}
                    if table == "item" and row_id in sim.purged_ids:
                        continue  # a purge scrubs the words of every earlier state of the item
                    if table in SCRUBBED and (table == "evidence" or sim.purged_ids & touches):
                        for state in (now, expected):
                            for key in SCRUBBED[table]:
                                state.pop(key, None)
                    assert now == expected, (table, row_id, seq)
                for row_id in known - set(rows):
                    assert row_as_of(conn, table, row_id, seq) is None, (table, row_id, seq)


def test_the_streams_roll_back_and_purge(sims):
    kinds = {e.type for sim in sims.values() for e in sim.log.events}
    assert {"compensation.batch", "purge.applied"} <= kinds
    for sim in sims.values():
        assert sim.log.conn.execute("SELECT COUNT(*) FROM item WHERE status = 'purged'").fetchone()[0] >= 1


@pytest.mark.parametrize("seed", SEEDS[:3])
def test_a_corrupted_random_stream_is_detected(sims, seed):
    conn = sims[seed].log.conn
    victim = conn.execute("SELECT id FROM item WHERE status = 'active' ORDER BY id LIMIT 1").fetchone()["id"]
    original = conn.execute("SELECT line FROM item WHERE id = ?", (victim,)).fetchone()["line"]
    conn.execute("UPDATE item SET line = ? WHERE id = ?", (original + " (edited)", victim))
    try:
        report = verify_replay(conn)
        assert not report.ok and f"item {victim}: line differs" in report.differences
    finally:
        conn.execute("UPDATE item SET line = ? WHERE id = ?", (original, victim))
    assert verify_replay(conn).ok


@pytest.mark.parametrize("seed", SEEDS[:3])
def test_a_random_stream_reads_the_same_through_the_reader_after_replay(sims, seed):
    conn = sims[seed].log.conn
    replayed = rebuild_from(conn)
    try:
        a, b = SQLiteMemoryReader(conn), SQLiteMemoryReader(replayed)
        assert a.watermark() == b.watermark()
        mid = a.watermark() // 2
        for item in conn.execute("SELECT id FROM item ORDER BY id"):
            assert a.get_item(item["id"], as_of_seq=mid) == b.get_item(item["id"], as_of_seq=mid)
            assert a.item_versions(item["id"]) == b.item_versions(item["id"])
        assert a.changed_since(mid) == b.changed_since(mid)
        assert history(conn, "item", "m1") == history(replayed, "item", "m1")
    finally:
        replayed.close()


# --- a purge replays over scrubbed events -----------------------------------------------------------------------------


def test_a_purge_replays_over_the_scrubbed_log(memory):
    log = Log(memory)
    seed_item(log, "m3", your_words="SQLite please")
    seed_item(log, "m4")
    log.add("item.revised", {"item_id": "m3", "line": "Second wording", "reason": "restated"})
    log.add("link.applied", link_fields("l1", "m3", "m4", reason="the secret reason"))
    seed_topic(log, "t1")
    place(log, "p1", "m3", "t1")
    log.add("purge.applied", {"item_ids": ["m3"]})
    log.add("item.value_changed", {"item_id": "m4"})
    payloads = " ".join(r["payload"] for r in memory.execute("SELECT payload FROM event"))
    for words in ("Second wording", "secret reason", "SQLite please", "Line of m3"):
        assert words not in payloads, words
    assert "Line of m4" in payloads  # an item that was not purged keeps its words
    report = verify_replay(memory)
    assert report.ok, report.differences


def test_a_batch_that_removes_a_stance_replays(memory):
    log = Log(memory)
    evs = seed_item(log, "m1")
    batch(log, *evs, log.events[-1])
    assert row(memory, "stance", evs[1].id) is None
    assert verify_replay(memory).ok


def test_rebuild_reads_a_path_with_characters_a_uri_would_misread(tmp_path):
    from northstar_agent_memory.core.replay import rebuild, scratch_store

    path = tmp_path / "odd #1 ? dir" / "memory.db"
    path.parent.mkdir()
    conn = scratch_store(path)
    conn.close()
    assert rebuild(path).execute("SELECT COUNT(*) FROM event").fetchone()[0] == 0
