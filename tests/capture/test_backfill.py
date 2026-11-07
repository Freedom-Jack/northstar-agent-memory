"""Backfill of past Claude Code transcripts into history.db (connectors-claude-code-and-codex.md §12). Invented transcripts."""

from __future__ import annotations

import json
import random
import string
from pathlib import Path

import pytest

from northstar_agent_memory import paths
from northstar_agent_memory.capture import ingest, scope
from northstar_agent_memory.capture.backfill import backfill
from northstar_agent_memory.capture.origin import NORTHSTAR_TAG, wrap_northstar
from northstar_agent_memory.core.history import SQLiteHistoryStore
from northstar_agent_memory.transcript import Message, Source

from . import T0 as LIVE_T0, assert_throwaway_root, put, write_settings

SID = "aaaaaaaa-1111-4000-8000-000000000001"
T0 = "2026-03-02T09:00:00.000Z"


def stamp(n: int) -> str:
    return f"2026-03-02T09:{n // 60:02d}:{n % 60:02d}.000Z"


def fake_token(prefix: str = "ghp_", n: int = 36, seed: int = 5) -> str:
    rnd = random.Random(seed)
    return prefix + "aQ7" + "".join(rnd.choice(string.ascii_letters + string.digits) for _ in range(n - 3))


class Transcript:
    """Builds the lines of one invented transcript."""

    def __init__(self, cwd: Path | str, sid: str = SID) -> None:
        self.cwd, self.sid = str(cwd), sid
        self.lines: list[dict | str] = []
        self.n = 0

    def _base(self, kind: str, **extra) -> dict:
        self.n += 1
        return {
            "parentUuid": None, "isSidechain": False, "userType": "external", "cwd": self.cwd, "sessionId": self.sid,
            "version": "2.1.309", "gitBranch": "main", "entrypoint": "cli", "uuid": f"{self.sid[:4]}-{self.n:04d}",
            "timestamp": stamp(self.n), "type": kind, **extra,
        }

    def user(self, content, **extra) -> str:
        line = self._base("user", message={"role": "user", "content": content}, **extra)
        self.lines.append(line)
        return line["uuid"]

    def assistant(self, *blocks, mid: str | None = None, **extra) -> str:
        content = [b if isinstance(b, dict) else {"type": "text", "text": b} for b in blocks]
        line = self._base(
            "assistant", requestId=f"req_{self.n}",
            message={"id": mid or f"msg_{self.n}", "type": "message", "role": "assistant", "model": "claude-opus-5-5", "content": content,
                     "usage": {"input_tokens": 3, "output_tokens": 9}},
            **extra,
        )
        self.lines.append(line)
        return line["uuid"]

    def raw(self, text: str) -> None:
        self.lines.append(text)

    def write(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(l if isinstance(l, str) else json.dumps(l) for l in self.lines) + "\n", encoding="utf-8")
        return path


@pytest.fixture(autouse=True)
def _throwaway_root():
    assert_throwaway_root()
    yield
    assert_throwaway_root()


@pytest.fixture
def world(tmp_path):
    """A personal folder, a transcripts folder laid out like ~/.claude/projects, a store and the settings."""
    personal = tmp_path / "Personal"
    (personal / "energy-dash").mkdir(parents=True)
    (tmp_path / "Work" / "billing").mkdir(parents=True)
    root = tmp_path / "claude-projects"
    root.mkdir()
    store = SQLiteHistoryStore(tmp_path / "stores")
    config = {"capture": {"personal_paths": [str(personal)]}}
    yield type("World", (), {
        "personal": personal, "work": tmp_path / "Work", "root": root, "store": store, "config": config, "tmp": tmp_path,
        "dash": personal / "energy-dash",
    })
    store.close()


def run(world, **kw):
    lines: list[str] = []
    report = backfill(world.root, world.store, config=world.config, progress=lines.append, **kw)
    return report, lines


def basic_session(world, sid=SID, cwd=None, project="-p-energy-dash") -> Transcript:
    t = Transcript(cwd or world.dash, sid)
    t.user("We keep 1-minute readings for 7 days. Please add hourly averages.")
    t.assistant("I will add an hourly average table.")
    t.user("Good. Name the table hourly_avg.")
    t.assistant("Done: the table is hourly_avg.")
    t.write(world.root / project / f"{sid}.jsonl")
    return t


def stored(world, sid=SID) -> list[Message]:
    return [m.message for m in world.store.messages_for_source(sid)]


def dump(world) -> str:
    rows = []
    for table in ("source", "message", "work_event"):
        rows += [str(tuple(r)) for r in world.store.conn.execute(f"SELECT * FROM {table} ORDER BY 1, 2")]  # noqa: S608
    return "\n".join(rows)


# --- the plain case --------------------------------------------------------------------------------------------


def test_an_in_scope_session_is_written_word_for_word_with_roles_from_claude_code(world):
    basic_session(world)
    report, _ = run(world)
    assert (report.sessions_in_scope, report.sessions_out_of_scope, report.messages_written) == (1, 0, 4)
    info = world.store.get_source_info(SID)
    assert (info["kind"], info["app"], info["scope"], info["project"]) == ("chat", "claude-code", "project:energy-dash", "energy-dash")
    assert info["started_at"] == stamp(1)
    msgs = stored(world)
    assert [(m.speaker, m.origin, m.agent, m.model_family) for m in msgs] == [
        ("user", "typed", "claude-code", None), ("assistant", "assistant_output", "claude-code", "anthropic"),
        ("user", "typed", "claude-code", None), ("assistant", "assistant_output", "claude-code", "anthropic"),
    ]
    assert msgs[0].text == "We keep 1-minute readings for 7 days. Please add hourly averages."
    assert [m.ordinal for m in msgs] == [0, 1, 2, 3]
    assert msgs[0].meta["uuid"] == f"{SID[:4]}-0001" and msgs[0].occurred_at == stamp(1)
    fidelity = {r[0] for r in world.store.conn.execute("SELECT fidelity FROM message")}
    assert fidelity == {"verbatim"}


def test_tool_traffic_thinking_meta_sidechain_and_summaries_are_not_stored(world):
    t = Transcript(world.dash)
    t.lines.append({"type": "summary", "summary": "Dashboard work", "leafUuid": "x"})
    t.user("Run the tests please")
    t.assistant({"type": "thinking", "thinking": "hmm", "signature": "s"})
    t.assistant({"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "pytest -q"}})
    t.user([{"type": "tool_result", "tool_use_id": "t1", "content": "12 passed"}])
    t.assistant("All 12 tests pass.")
    t.user("Injected by a hook", isMeta=True)
    t.user("This session is being continued from a previous conversation. Summary: invented.", isCompactSummary=True)
    t.user("[Request interrupted by user]")
    t.assistant("Agent chatter", isSidechain=True)
    t.write(world.root / "p" / f"{SID}.jsonl")
    report, _ = run(world)
    main = [m for m in stored(world) if m.branch is None]
    assert [(m.speaker, m.text) for m in main] == [("user", "Run the tests please"), ("assistant", "All 12 tests pass.")]
    # The sidechain is not part of the conversation: only its final message is kept, on a branch of its own.
    assert [(m.branch, m.text) for m in stored(world) if m.branch] == [(f"sidechain:{SID}", "Agent chatter")]
    assert report.messages_written == 3
    assert report.not_captured["tool_use"] == 1
    assert report.lines_skipped["sidechain"] == 1 and report.lines_skipped["meta"] == 1
    assert world.store.get_source_info(SID)["title"] == "Dashboard work"


def test_one_response_in_several_lines_is_one_assistant_message(world):
    t = Transcript(world.dash)
    t.user("Explain the tie-break.")
    t.assistant("First paragraph.", mid="msg_a")
    t.assistant("Second paragraph.", mid="msg_a")
    t.assistant({"type": "tool_use", "id": "t1", "name": "Read", "input": {"file_path": "/x"}}, mid="msg_a")
    t.assistant("After the tool ran: third.", mid="msg_b")
    t.write(world.root / "p" / f"{SID}.jsonl")
    run(world)
    assert [m.text for m in stored(world) if m.speaker == "assistant"] == [
        "First paragraph.\n\nSecond paragraph.", "After the tool ran: third.",
    ]


# --- scope -----------------------------------------------------------------------------------------------------


def test_sessions_outside_the_personal_folders_are_counted_and_never_stored(world):
    basic_session(world)
    other = Transcript(world.work / "billing", "bbbbbbbb-2222-4000-8000-000000000002")
    other.user("the secret-sounding client name is Acme Corp, invoice 4411")
    other.assistant("Noted: invoice 4411 for Acme Corp.")
    other.write(world.root / "-w-billing" / f"{other.sid}.jsonl")
    report, lines = run(world)
    assert (report.sessions_in_scope, report.sessions_out_of_scope) == (1, 1)
    assert world.store.get_source_info(other.sid) is None
    assert "Acme" not in dump(world) and "4411" not in dump(world)
    assert any(line.startswith("-w-billing: 0 sessions in scope, 1 out of scope") for line in lines)


def test_a_file_with_no_working_folder_is_out_of_scope(world):
    (world.root / "p").mkdir()
    (world.root / "p" / "nocwd.jsonl").write_text(json.dumps({"type": "user", "message": {"role": "user", "content": "hi"}}) + "\n")
    report, _ = run(world)
    assert report.sessions_out_of_scope == 1 and report.messages_written == 0


def test_northstars_own_runs_are_skipped(world):
    own = paths.harness_cwd() / "run-1"
    t = Transcript(own, "cccccccc-3333-4000-8000-000000000003")
    t.user("hidden call text")
    t.assistant("hidden answer")
    t.write(world.root / "-own" / f"{t.sid}.jsonl")
    # Even a personal-folder setting that would cover the data root does not capture it.
    config = {"capture": {"personal_paths": [str(paths.data_root().parent), str(world.personal)]}}
    report = backfill(world.root, world.store, config=config, progress=None)
    assert report.sessions_own_runs == 1 and report.sessions_in_scope == 0 and report.messages_written == 0
    assert world.store.get_source_info(t.sid) is None


def test_a_hidden_run_does_nothing_at_all(world, monkeypatch):
    basic_session(world)
    monkeypatch.setenv(scope.HIDDEN_RUN_ENV, "1")
    report, lines = run(world)
    assert report.hidden_run and report.messages_written == 0 and world.store.get_source_info(SID) is None
    assert "own runs" in lines[0]


def test_a_turn_typed_after_leaving_the_personal_folder_is_left_out(world):
    t = Transcript(world.dash)
    t.user("In the dashboard folder")
    t.assistant("Ok, here.")
    t.cwd = str(world.work / "billing")
    t.user("Now in the work folder: client Acme invoice")
    t.assistant("Work folder answer")
    t.write(world.root / "p" / f"{SID}.jsonl")
    report, _ = run(world)
    assert [m.text for m in stored(world)] == ["In the dashboard folder", "Ok, here."]
    assert report.not_captured["out_of_scope_turn"] == 2
    assert "Acme" not in dump(world)


# --- secrets ---------------------------------------------------------------------------------------------------


def test_secrets_are_replaced_before_anything_is_written(world):
    token, key = fake_token(), fake_token("sk-ant-api03-", 40, seed=8)
    t = Transcript(world.dash)
    t.user(f"Use this token {token} for the repo and password: hunter2pw")
    t.assistant(f"I set ANTHROPIC_API_KEY={key} in the .env file.")
    t.lines.append({"type": "summary", "summary": f"Setup with {token}", "leafUuid": "x"})
    t.write(world.root / "p" / f"{SID}.jsonl")
    report, _ = run(world)
    text = dump(world)
    assert token not in text and key not in text and "hunter2pw" not in text
    assert stored(world)[0].text == "Use this token [secret removed: github_token] for the repo and password: [secret removed: password]"
    assert dict(report.secrets) == {"github_token": 2, "password": 1, "anthropic_api_key": 1}
    assert any("Secrets removed, by kind: anthropic_api_key 1, github_token 2, password 1" in l for l in report.summary_lines())


def test_the_summary_lists_secrets_removed_by_kind(world):
    t = Transcript(world.dash)
    t.user(f"token {fake_token()} and {fake_token(seed=6)}")
    t.assistant("ok")
    t.write(world.root / "p" / f"{SID}.jsonl")
    _, lines = run(world)
    assert any("Secrets removed, by kind: github_token 2" in line for line in lines)


# --- origins ---------------------------------------------------------------------------------------------------


def test_a_user_turn_keeps_only_the_users_words_and_marks_pastes(world):
    t = Transcript(world.dash)
    t.user(
        "<system-reminder>Today is Monday.</system-reminder>\n"
        "Why does this fail? <pasted_content>Traceback: boom</pasted_content> Thanks."
    )
    t.user("<pasted_content>all of this is pasted</pasted_content>")
    t.write(world.root / "p" / f"{SID}.jsonl")
    run(world)
    first, second = stored(world)
    assert (first.speaker, first.origin, first.text) == ("user", "typed", "Why does this fail? Traceback: boom Thanks.")
    assert first.meta["paste_ranges"] == [[20, 35]]
    assert (second.origin, second.text) == ("pasted", "all of this is pasted")
    assert "Today is Monday" not in dump(world)


def test_a_slash_command_with_words_is_kept_and_a_bare_one_is_not(world):
    t = Transcript(world.dash)
    t.user("<command-name>/review</command-name><command-message>review</command-message><command-args>the tie-break</command-args>")
    t.user("<command-name>/clear</command-name><command-message>clear</command-message><command-args></command-args>")
    t.user("<local-command-stdout>Compacted</local-command-stdout>")
    t.write(world.root / "p" / f"{SID}.jsonl")
    run(world)
    msgs = stored(world)
    assert [(m.text, m.meta.get("command")) for m in msgs] == [("/review the tie-break", "/review")]


def test_text_northstar_delivered_is_marked_northstar_injected_and_never_the_users(world):
    t = Transcript(world.dash)
    uuid = t.user(f"What was decided about ties?\n{wrap_northstar('Decision D1: lowest device id wins.')}")
    meta_uuid = t.user(f"<system-reminder>Hook output: {wrap_northstar('Start note: Lamport clocks.')}</system-reminder>", isMeta=True)
    t.write(world.root / "p" / f"{SID}.jsonl")
    run(world)
    rows = [(m.speaker, m.origin, m.text, m.id) for m in stored(world)]
    assert rows == [
        ("user", "typed", "What was decided about ties?", f"{SID}:{uuid}"),
        ("northstar", "northstar_injected", "Decision D1: lowest device id wins.", f"{SID}:{uuid}:n0"),
        ("northstar", "northstar_injected", "Start note: Lamport clocks.", f"{SID}:{meta_uuid}:n0"),
    ]
    assert NORTHSTAR_TAG not in dump(world)


def test_a_northstar_block_quoted_in_a_tool_result_is_not_captured(world):
    t = Transcript(world.dash)
    t.user("Read the file")
    t.user([{"type": "tool_result", "tool_use_id": "t1", "content": wrap_northstar("quoted in a file")}])
    t.assistant("It holds a note.")
    t.write(world.root / "p" / f"{SID}.jsonl")
    run(world)
    assert [m.speaker for m in stored(world)] == ["user", "assistant"]


# --- idempotency -----------------------------------------------------------------------------------------------


def test_a_second_run_stores_nothing_new(world):
    basic_session(world)
    first, _ = run(world)
    before = dump(world)
    second, _ = run(world)
    assert (first.messages_written, second.messages_written) == (4, 0)
    assert second.messages_already_stored == 4 and second.messages_conflict == 0
    assert dump(world) == before
    assert world.store.watermark().message_seq == 4


def test_a_session_that_grew_gets_only_its_new_lines(world):
    t = basic_session(world)
    run(world)
    t.user("One more thing: add a weekly rollup.")
    t.assistant("Added the weekly rollup.")
    t.write(world.root / "-p-energy-dash" / f"{SID}.jsonl")
    report, _ = run(world)
    assert report.messages_written == 2 and report.messages_already_stored == 4
    assert [m.ordinal for m in stored(world)] == [0, 1, 2, 3, 4, 5]
    assert stored(world)[-1].text == "Added the weekly rollup."


def test_it_matches_live_capture_by_the_transcript_lines_uuid(world):
    t = basic_session(world)
    uuid0 = f"{SID[:4]}-0001"
    world.store.add_source(Source(id=SID, kind="chat", app="claude-code"), scope="project:energy-dash")
    live = Message(
        id="live-1", source_id=SID, ordinal=0, speaker="user", text="We keep 1-minute readings for 7 days. Please add hourly averages.",
        origin="typed", agent="claude-code", meta={"uuid": uuid0},
    )
    world.store.append_message(live)
    report, _ = run(world)
    assert report.messages_written == 3 and report.messages_already_stored == 1
    assert len(stored(world)) == 4 and stored(world)[0].id == "live-1"
    assert [m.ordinal for m in stored(world)] == [0, 1, 2, 3]
    assert t.sid == SID


def test_it_matches_a_live_message_that_has_no_uuid_by_speaker_and_exact_text(world):
    basic_session(world)
    world.store.add_source(Source(id=SID, kind="chat", app="claude-code"), scope="project:energy-dash")
    for i, (speaker, text, origin) in enumerate(
        [("user", "Good. Name the table hourly_avg.", "typed"), ("assistant", "Done: the table is hourly_avg.", "assistant_output")]
    ):
        world.store.append_message(Message(id=f"live-{i}", source_id=SID, ordinal=i, speaker=speaker, text=text, origin=origin, agent="claude-code"))
    report, _ = run(world)
    assert report.messages_written == 2 and report.messages_already_stored == 2
    assert [m.text for m in stored(world)].count("Good. Name the table hourly_avg.") == 1


def test_a_stored_message_with_other_words_is_a_conflict_and_is_left_alone(world):
    t = Transcript(world.dash)
    t.user("Explain the tie-break.")
    t.assistant("First paragraph.", mid="msg_a")
    t.write(world.root / "p" / f"{SID}.jsonl")
    run(world)  # the response was caught half-written
    t.assistant("Second paragraph.", mid="msg_a")
    t.write(world.root / "p" / f"{SID}.jsonl")
    report, _ = run(world)
    assert [m.text for m in stored(world)] == ["Explain the tie-break.", "First paragraph."]
    assert (report.messages_written, report.messages_conflict, report.messages_already_stored) == (0, 1, 1)
    assert any("1 in conflict" in line for line in report.summary_lines())


def test_a_session_id_already_stored_with_another_kind_is_counted_and_left_alone(world):
    basic_session(world)
    world.store.add_source(Source(id=SID, kind="document", app="claude-code"), scope="project:energy-dash")
    report, _ = run(world)
    assert report.sessions_conflict == 1 and report.messages_written == 0


# --- subagents -------------------------------------------------------------------------------------------------


def test_a_subagents_final_message_is_kept_on_its_own_branch(world):
    t = Transcript(world.dash)
    t.user("Check the repo for TODOs")
    t.assistant("I started a subagent.")
    t.assistant("Found 3 TODOs in src/", isSidechain=True, agentId="agent-7")
    last = t.assistant("Final report: TODOs are in readings.py, rollup.py and cli.py.", isSidechain=True, agentId="agent-7")
    t.assistant("The subagent found three TODOs.")
    t.write(world.root / "p" / f"{SID}.jsonl")
    report, _ = run(world)
    msgs = world.store.messages_for_source(SID)
    main = [m.message for m in msgs if m.message.branch is None]
    sub = [m.message for m in msgs if m.message.branch == "sidechain:agent-7"]
    assert [m.speaker for m in main] == ["user", "assistant", "assistant"]
    assert [(m.text, m.ordinal, m.speaker, m.origin) for m in sub] == [
        ("Final report: TODOs are in readings.py, rollup.py and cli.py.", 0, "assistant", "assistant_output")
    ]
    assert sub[0].meta["speaker_scope"] == "subagent" and sub[0].meta["uuid"] == last
    assert report.messages_written == 4
    assert run(world)[0].messages_written == 0  # and once only


def test_a_subagent_file_in_its_own_folder_adds_its_final_message_to_the_parent_session(world):
    basic_session(world)
    sub = Transcript(world.dash, SID)
    sub.n = 100
    sub.user("do the task", isSidechain=True, agentId="agent-9")
    sub.assistant("Task result from the subagent.", isSidechain=True, agentId="agent-9")
    sub.write(world.root / "-p-energy-dash" / SID / "subagents" / "agent-9.jsonl")
    report, _ = run(world)
    assert report.sessions_in_scope == 1
    sub_msgs = [m.message for m in world.store.messages_for_source(SID) if m.message.branch == "sidechain:agent-9"]
    assert [m.text for m in sub_msgs] == ["Task result from the subagent."]
    assert len([m for m in stored(world, SID) if m.branch is None]) == 4


def test_a_subagent_message_without_its_session_stored_is_not_written(world):
    sub = Transcript(world.dash, SID)
    sub.assistant("orphan result", isSidechain=True, agentId="agent-1")
    sub.write(world.root / "p" / SID / "subagents" / "agent-1.jsonl")
    report, _ = run(world)
    assert report.messages_written == 0 and report.not_captured["subagent_without_session"] == 1


# --- forks, bad input, reporting ---------------------------------------------------------------------------------


def test_lines_copied_into_a_forked_session_are_counted_once(world):
    parent = basic_session(world)
    fork = Transcript(world.dash, "dddddddd-4444-4000-8000-000000000004")
    fork.lines = [dict(line) for line in parent.lines]  # the copied history, same uuids and timestamps
    for line in fork.lines:
        line["sessionId"] = fork.sid
    fork.n = 50
    fork.user("A new question in the fork.")
    fork.write(world.root / "-p-energy-dash" / f"{fork.sid}.jsonl")
    report, _ = run(world)
    assert report.sessions_in_scope == 2
    assert len(stored(world, SID)) == 4
    assert [m.text for m in stored(world, fork.sid)] == ["A new question in the fork."]


def test_bad_lines_and_unreadable_content_do_not_stop_the_run(world):
    t = Transcript(world.dash)
    t.raw("not json at all")
    t.raw("[1, 2, 3]")
    t.user("A real question")
    t.raw('{"type": "weird-new-type", "uuid": "z"}')
    t.assistant("A real answer")
    t.write(world.root / "p" / f"{SID}.jsonl")
    report, _ = run(world)
    assert report.messages_written == 2
    assert report.lines_skipped["invalid_json"] == 2


def test_one_progress_line_per_project_and_a_summary_at_the_end(world):
    basic_session(world, project="-p-energy-dash")
    basic_session(world, sid="eeeeeeee-5555-4000-8000-000000000005", project="-p-energy-dash-2")
    report, lines = run(world)
    project_lines = [l for l in lines if l.startswith("-p-energy-dash")]
    assert len(project_lines) == 2
    assert project_lines[0] == "-p-energy-dash: 1 sessions in scope, 0 out of scope, 4 messages written, 0 skipped"
    assert any(l.startswith("Backfill: 2 sessions in scope, 0 out of scope") for l in lines)
    assert any(l.startswith("Messages: 8 written, 0 already stored") for l in lines)
    assert [p.name for p in report.projects] == ["-p-energy-dash", "-p-energy-dash-2"]
    assert (report.projects[0].messages_written, report.messages_skipped) == (4, 0)


def test_the_progress_goes_nowhere_when_asked_and_prints_by_default(world, capsys):
    basic_session(world)
    backfill(world.root, world.store, config=world.config, progress=None)
    assert capsys.readouterr().out == ""
    backfill(world.root, world.store, config=world.config)
    assert "Backfill: 1 sessions in scope" in capsys.readouterr().out


def test_settings_come_from_the_users_settings_file_by_default(world, isolated_home):
    basic_session(world)
    (isolated_home / "data").mkdir(parents=True, exist_ok=True)
    (isolated_home / "data" / "settings.toml").write_text(f'[capture]\npersonal_paths = ["{world.personal}"]\n', encoding="utf-8")
    report = backfill(world.root, world.store, progress=None)
    assert report.sessions_in_scope == 1 and report.messages_written == 4


def test_an_empty_or_missing_folder_is_fine(world, tmp_path):
    assert backfill(world.root, world.store, config=world.config, progress=None).projects == []
    assert backfill(tmp_path / "nowhere", world.store, config=world.config, progress=None).sessions_in_scope == 0


def test_the_evaluation_fixtures_import_and_import_again_unchanged(world):
    fixtures = Path(__file__).parent.parent / "eval" / "fixtures" / "claude_code"
    config = {"capture": {"personal_paths": ["/home/demo/work"]}}
    first = backfill(fixtures, world.store, config=config, progress=None)
    assert first.sessions_in_scope >= 4 and first.messages_written > 20 and first.hidden_run is False
    before = dump(world)
    second = backfill(fixtures, world.store, config=config, progress=None)
    assert second.messages_written == 0 and second.messages_already_stored == first.messages_written
    assert dump(world) == before
    # Nothing but the user's, the assistant's and Northstar's words, with ordinals counting up from 0.
    assert {r[0] for r in world.store.conn.execute("SELECT DISTINCT speaker FROM message")} <= {"user", "assistant", "northstar"}
    for (sid,) in world.store.conn.execute("SELECT id FROM source").fetchall():
        ordinals = [m.ordinal for m in stored(world, sid) if m.branch is None]
        assert ordinals == list(range(len(ordinals)))


# --- live capture and backfill together (the same words are stored once) -------------------------------------------


@pytest.fixture
def live(world):
    """The store live capture writes to (the throwaway data root's), with the personal folder in the settings."""
    write_settings(world.personal)
    with SQLiteHistoryStore() as store:
        yield store


def rows(store, sid=SID):
    return [(m.message.branch, m.message.speaker, m.message.origin, m.message.text) for m in store.messages_for_source(sid)]


def test_a_subagent_final_message_stored_live_is_not_stored_again_by_the_backfill(world, live):
    final = "Final report: TODOs are in readings.py, rollup.py and cli.py."
    put("UserPromptSubmit", world.dash, LIVE_T0, SID, prompt="Check the repo for TODOs")
    put("SubagentStop", world.dash, LIVE_T0 + 10, SID, last_assistant_message=final, agent_id="agent-7", agent_type="Explore")
    put("Stop", world.dash, LIVE_T0 + 20, SID, last_assistant_message="The subagent found three TODOs.")
    assert ingest.drain(reconcile=False).messages == 3
    t = Transcript(world.dash)
    t.user("Check the repo for TODOs")
    t.assistant("Found 3 TODOs in src/", isSidechain=True, agentId="agent-7")
    t.assistant(final, isSidechain=True, agentId="agent-7")
    t.assistant("The subagent found three TODOs.")
    t.write(world.root / "p" / f"{SID}.jsonl")
    before = rows(live)
    report = backfill(world.root, live, config=world.config, progress=None)
    assert report.messages_written == 0
    assert rows(live) == before
    assert [r for r in before if r[0]] == [("sidechain:agent-7", "assistant", "assistant_output", final)]  # the one branch name


def test_a_subagent_final_message_stored_under_the_old_branch_name_is_matched_by_its_text(world, live):
    final = "Final report: all done."
    live.add_source(Source(id=SID, kind="chat", app="claude-code"), scope="project:energy-dash")
    live.append_message(Message(id="old-1", source_id=SID, ordinal=0, speaker="assistant", text=final, origin="assistant_output",
                                agent="claude-code", branch="subagent:agent-7"))
    t = Transcript(world.dash)
    t.user("Do the task")
    t.assistant("Started.", isSidechain=True, agentId="agent-7")
    t.assistant(final, isSidechain=True, agentId="agent-7")
    t.write(world.root / "p" / f"{SID}.jsonl")
    report = backfill(world.root, live, config=world.config, progress=None)
    assert report.messages_written == 1  # only the user's turn
    assert [r for r in rows(live) if r[0]] == [("subagent:agent-7", "assistant", "assistant_output", final)]


def test_a_subagent_file_named_for_its_agent_id_gets_the_branch_live_capture_uses(world, live):
    put("UserPromptSubmit", world.dash, LIVE_T0, SID, prompt="hello")
    put("SubagentStop", world.dash, LIVE_T0 + 10, SID, last_assistant_message="Result.", agent_id="a1b2c3")
    ingest.drain(reconcile=False)
    sub = Transcript(world.dash, SID)
    sub.n = 100
    sub.assistant("Result.", isSidechain=True)  # no agentId on the line: the file name carries it
    sub.write(world.root / "p" / SID / "subagents" / "agent-a1b2c3.jsonl")
    basic = Transcript(world.dash, SID)
    basic.user("hello")
    basic.write(world.root / "p" / f"{SID}.jsonl")
    assert backfill(world.root, live, config=world.config, progress=None).messages_written == 0
    assert [r[0] for r in rows(live) if r[0]] == ["sidechain:a1b2c3"]


def test_a_command_a_paste_and_a_northstar_block_stored_live_are_not_doubled_by_the_backfill(world, live):
    block = wrap_northstar("Decision D1: lowest device id wins.")
    prompts = ["/review the tie-break rule", "Why? <pasted_content>KeyError: 'x'</pasted_content> thanks",
               f"What was decided about ties?\n{block}", "<pasted_content>all of this is pasted</pasted_content>"]
    for i, prompt in enumerate(prompts):
        put("UserPromptSubmit", world.dash, LIVE_T0 + i * 10, SID, prompt=prompt)
        put("Stop", world.dash, LIVE_T0 + i * 10 + 5, SID, last_assistant_message=f"Answer {i}.")
    assert ingest.drain(reconcile=False).messages == 9
    t = Transcript(world.dash)
    t.user("<command-name>/review</command-name><command-message>review</command-message><command-args>the tie-break rule</command-args>")
    t.assistant("Answer 0.")
    t.user(prompts[1])
    t.assistant("Answer 1.")
    t.user(prompts[2])
    t.assistant("Answer 2.")
    t.user(prompts[3])
    t.assistant("Answer 3.")
    t.write(world.root / "p" / f"{SID}.jsonl")
    before = rows(live)
    report = backfill(world.root, live, config=world.config, progress=None)
    assert (report.messages_written, report.messages_conflict) == (0, 0)
    assert rows(live) == before and len(before) == 9
    assert [r[1:] for r in before if r[1] == "northstar"] == [("northstar", "northstar_injected", "Decision D1: lowest device id wins.")]
    for _, speaker, _, text in before:  # nothing of Northstar's is stored as the user's
        assert speaker != "user" or "Decision D1" not in text and NORTHSTAR_TAG not in text
    assert [r[2] for r in before if r[1] == "user"] == ["typed", "typed", "typed", "pasted"]


def test_a_session_reconciled_by_the_ingester_is_not_doubled_by_the_backfill(world, live):
    """Live capture lost two turns and the assistant's narration; reconciliation adds them; the backfill adds nothing."""
    block = wrap_northstar("Decision D1: lowest device id wins.")
    path = world.root / "p" / f"{SID}.jsonl"
    kw = {"transcript_path": str(path)}
    put("SessionStart", world.dash, LIVE_T0, SID, source="startup", **kw)
    put("UserPromptSubmit", world.dash, LIVE_T0 + 1, SID, prompt="Fix it.", **kw)  # the transcript's lines are a second apart
    put("Stop", world.dash, LIVE_T0 + 4, SID, last_assistant_message="Fixed.", **kw)
    put("SessionEnd", world.dash, LIVE_T0 + 200, SID, reason="other", **kw)
    t = Transcript(world.dash)
    t.user("Fix it.")
    t.assistant("Let me look at the file.", {"type": "tool_use", "id": "t1", "name": "Read", "input": {"file_path": "/x"}})
    t.user([{"type": "tool_result", "tool_use_id": "t1", "content": "contents"}])
    t.assistant("Fixed.")
    t.n += 20  # a minute of thinking
    t.user(f"What was decided about ties?\n{block}")  # both hooks of this turn were lost
    t.assistant("Let me check the notes.")
    t.assistant("D1 wins ties.")
    t.write(path)
    result = ingest.drain(now=LIVE_T0 + 300)
    assert (result.reconciled, result.mismatches, result.errors) == (5, 0, 0)
    before = rows(live)
    assert [(r[1], r[3]) for r in before if r[1] != "system"] == [
        ("user", "Fix it."), ("assistant", "Fixed."), ("assistant", "Let me look at the file."),
        ("user", "What was decided about ties?"), ("northstar", "Decision D1: lowest device id wins."),
        ("assistant", "Let me check the notes."), ("assistant", "D1 wins ties."),
    ]
    report = backfill(world.root, live, config=world.config, progress=None)
    assert (report.messages_written, report.messages_conflict) == (0, 0)
    assert rows(live) == before
