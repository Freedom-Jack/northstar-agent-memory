"""Fixtures for the core's tests. Every fixture is invented data; the stores live under a throwaway root."""

from __future__ import annotations

import pytest

from northstar_agent_memory.core import db, events
from northstar_agent_memory.core.ids import new_id

ACTOR = "code:test"
CONFIG = "config-test-1"
MODEL_ACTOR = "model:claude-test@1#9f2c"

# One valid payload for each of the 42 event types (invented; Robin's energy dashboard from MEMORY-ARCHITECTURE §6).
EXAMPLE_PAYLOADS: dict[str, dict] = {
    "evidence.anchored": dict(
        evidence_id="ev1", subject_kind="item", subject_id="m3", message_id="A4", start_char=5, end_char=79,
        quote="keep 1-minute readings for 7 days", role="primary", speaker="assistant", agent="claude-code",
        model_family="claude", origin="assistant_output", context="energy-dash",
    ),
    "item.created": dict(
        item_id="m3", kind="decision", line="Readings older than 7 days are kept only as hourly averages",
        scope="project:energy-dash", learned_in="A", said_at="2026-03-02T09:30:00Z", evidence_ids=["ev1", "ev2"],
        origin="adopted:claude-code",
    ),
    "item.revised": dict(
        item_id="m5", base_version=1, line="Planned to demo the dashboard at the meetup on 26 March 2026; no later record",
        reason="refresh", time_bound=True,
    ),
    "item.value_changed": dict(item_id="m3", from_value="forming", to_value="kept", signal="used_in_work"),
    "item.scope_widened": dict(
        item_id="m7", base_version=1, from_scope="project:de-course", to_scope="personal", evidence_ids=["ev9"]
    ),
    "item.status_changed": dict(
        item_id="m3", from_status="active", to_status="superseded", reason="your later statement", ref="evt-1"
    ),
    "item.checked": dict(item_id="m4", check_status="checked", checker_family="openai"),
    "stance.recorded": dict(item_id="m3", stance="adopted", evidence_ids=["ev2"]),
    "link.proposed": dict(
        link_id="l1", from_id="m8", to_id="m1", link_type="supports", reason="m8 repeats m1 in another project",
        stated_by="northstar",
    ),
    "link.applied": dict(
        link_id="l2", from_id="m3", to_id="w1", link_type="used_in", reason="made in the same session as the commit",
        stated_by="construction", to_kind="work",
    ),
    "link.confirmed": dict(link_id="l1", via="click"),
    "link.rejected": dict(link_id="l1", via="typed", evidence_id="ev5"),
    "link.retracted": dict(link_id="l1", reason="an item it joins was retracted"),
    "supersession.applied": dict(
        supersession_id="s1", old_item="m5", old_version=1, new_item="m5", new_version=2, reason="refresh"
    ),
    "supersession.undone": dict(supersession_id="s1", reason="audit disagreed"),
    "conflict.opened": dict(
        conflict_id="c1", side_a_item="m6", side_a_version=1, side_b_item="m7", side_b_version=1,
        kind="across_contexts", state="both_stand", link_id="l3",
    ),
    "conflict.resolved": dict(
        conflict_id="c1", step=2, state="resolved", rule_version="rules-1", winner="m7", resolution_inputs=["evt-9"]
    ),
    "conflict.reopened": dict(conflict_id="c1", reason="the audit disagreed"),
    "conflict.undone": dict(conflict_id="c1", reason="opened in error"),
    "goal.created": dict(
        item_id="m9", line="Alert me when running the dryer costs double", scope="project:energy-dash",
        learned_in="C", said_at="2026-03-09T08:00:00Z", basis="stated", evidence_ids=["ev11"], work_id="T2",
        origin="yours",
    ),
    "goal.status_changed": dict(item_id="m9", from_status="active", to_status="done", evidence_ids=["ev12"]),
    "goal.confirmed": dict(item_id="m9", evidence_ids=["ev13"]),
    "question.created": dict(
        item_id="m11", line="How do I avoid alert fatigue?", scope="project:energy-dash", learned_in="C",
        said_at="2026-03-11T08:00:00Z", raised_by="you", evidence_ids=["ev14"], origin="yours",
    ),
    "question.status_changed": dict(item_id="m11", from_status="open", to_status="answered", answered_by=["m12"]),
    "work.registered": dict(
        work_id="w1", kind="commit", ref="a41c9e0", evidence="medium", work_event_id="we1",
        label="logger: one SQLite file per meter, WAL, downsampling", project="energy-dash",
    ),
    "work.labelled": dict(work_id="w1", label="One SQLite file per meter with downsampling", label_source="checked"),
    "style.recorded": dict(
        style_id="st1", line="Prefers short answers", scope="personal", basis="stated_default", evidence_ids=["ev20"]
    ),
    "style.revised": dict(style_id="st1", reason="reworded", line="Prefers short answers first"),
    "correction.applied": dict(
        correction_id="co1", kind="rename", target="t1", via="click", at="2026-03-10T10:00:00Z",
        constraint={"label_fixed": True}, params={"label": "Energy dashboard"},
    ),
    "correction.lifted": dict(correction_id="co1", reason="your_undo"),
    "topic.created": dict(topic_id="t2", label="Price alerts", anchor_id="m9", parent_id="t1"),
    "topic.split": dict(
        topic_id="t1", redirect_to="t3", formation_overlap=0.5, reason="two clusters for 2 runs",
        new_topics=[
            {"topic_id": "t3", "label": "Logger", "anchor_id": "m1"},
            {"topic_id": "t4", "label": "Charts", "anchor_id": "m13"},
        ],
    ),
    "topic.branched": dict(topic_id="t2", old_parent_id="t1", reason="separated from its parent for 2 runs"),
    "topic.merged": dict(from_topic_id="t4", into_topic_id="t3", reason="link weight 0.7 for 2 runs"),
    "topic.folded_back": dict(topic_id="t2", into_parent_id="t1", reason="fewer than 3 kept ideas for 4 runs"),
    "topic.renamed": dict(topic_id="t1", old_label="Energy", label="Energy dashboard", label_fixed=True, reason="you renamed it"),
    "topic.dormant": dict(topic_id="t5", to_status="dormant", reason="no activity for 21 days"),
    "idea.placed": dict(placement_id="p1", item_id="m7", topic_id="t5", role="home", tentative=False, reasons=["same chat", "argues with m6"]),
    "idea.moved": dict(item_id="m7", from_topic_id="t5", to_topic_id="t1", role="also_in", tentative=False, reason="your move correction"),
    "compensation.batch": dict(batch_id="b1", reason="audit disagreed", compensated_event_ids=["evt-1", "evt-2"]),
    "purge.applied": dict(purge_id="pg1", item_ids=["m3"], requested_at="2026-04-01T09:00:00Z"),
    "scope.hold_changed": dict(scope_id="project:energy-dash", held=True, reason="you held the project"),
}

# The same payloads as a draft carries them: stamped fields left unset (I3).
_STAMPED = {"speaker", "agent", "model_family", "origin", "context"}


def draft_payload(type_: str) -> dict:
    cls = events.PAYLOADS[(type_, 1)]
    return {k: v for k, v in EXAMPLE_PAYLOADS[type_].items() if k not in cls.STAMPED}


@pytest.fixture
def store_root(tmp_path):
    return tmp_path / "stores"


@pytest.fixture
def open_all(store_root):
    """Open every store under a throwaway root; connections close at the end of the test."""
    conns = {name: db.open_store(name, store_root) for name in db.STORES}
    yield conns
    for conn in conns.values():
        conn.close()


@pytest.fixture
def history(open_all):
    return open_all["history"]


@pytest.fixture
def memory(open_all):
    return open_all["memory"]


@pytest.fixture
def make_envelope():
    """Build an envelope for a type from EXAMPLE_PAYLOADS. `draft=True` leaves the stamped fields unset."""

    def make(type_: str, *, draft: bool = False, **overrides) -> events.EventEnvelope:
        payload = draft_payload(type_) if draft else dict(EXAMPLE_PAYLOADS[type_])
        env = events.make_event(type_, payload, actor=ACTOR, config_version=CONFIG)
        if not draft:
            env.recorded_at = "2026-03-02T09:30:00.000Z"
        for key, value in overrides.items():
            setattr(env, key, value)
        return env

    return make


@pytest.fixture
def fresh_id():
    return new_id
