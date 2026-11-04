"""The Claude Code transcript reader, on invented transcripts (tests/eval/fixtures/claude_code)."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest

from northstar_agent_memory.eval.claude_code import parse_projects, parse_session, parse_time

FIXTURES = Path(__file__).parent / "fixtures" / "claude_code"
LEDGER = "/home/demo/work/ledger-sync"
GARDEN = "/home/demo/work/garden-notes"


def write(path: Path, *objs: object) -> Path:
    path.write_text("\n".join(o if isinstance(o, str) else json.dumps(o) for o in objs) + "\n", encoding="utf-8")
    return path


def user_line(text, ts="2026-04-01T09:00:00.000Z", uuid="u1", **extra):
    return {
        "type": "user", "uuid": uuid, "sessionId": "s-x", "timestamp": ts, "cwd": "/x/proj",
        "message": {"role": "user", "content": text}, **extra,
    }


@pytest.fixture(scope="module")
def ledger1():
    return parse_session(FIXTURES / "ledger_s1.jsonl")


def test_source_record(ledger1):
    src = ledger1.source
    assert src.id == "11111111-aaaa-4000-8000-000000000001"
    assert (src.kind, src.app, src.project) == ("chat", "claude-code", LEDGER)
    assert src.started_at == "2026-03-02T09:00:05.000Z"
    assert src.title == "Ledger sync engine"  # from the summary line
    assert ledger1.id == src.id and ledger1.project == LEDGER
    assert ledger1.git_branch == "main" and ledger1.git_branches == ["main"]
    assert ledger1.first_timestamp == "2026-03-02T09:00:05.000Z"
    assert ledger1.last_timestamp == "2026-03-02T11:30:30.000Z"
    assert ledger1.started == datetime(2026, 3, 2, 9, 0, 5, tzinfo=timezone.utc)
    assert ledger1.versions == ["2.1.301"]


def test_typed_turns_exclude_everything_that_is_not_typed(ledger1):
    assert [m.text for m in ledger1.typed_turns()] == [
        "We need an offline-first sync engine for the ledger app. We decided to use per-device "
        "operation logs with Lamport clocks. The tie-break rule is that the lowest device id wins.",
        "Please add a test for tombstone expiry.",  # the system-reminder wrapper is removed
        "Now run the full suite with coverage.",
        "Thanks, that is enough for today.",
    ]
    assert all(m.origin == "typed" and m.agent == "claude-code" for m in ledger1.typed_turns())
    everything = " ".join(m.text for m in ledger1.source.messages)
    for noise in ("Caveat", "Search the repo", "Set model to", "<system-reminder>", "interrupted", "continued from"):
        assert noise not in everything


def test_assistant_text_and_tool_calls(ledger1):
    msgs = ledger1.source.messages
    assistant = [m for m in msgs if m.speaker == "assistant"]
    assert len(assistant) == 6  # a response written as several lines is one message
    assert all(m.origin == "assistant_output" and m.model_family == "anthropic" for m in assistant)
    assert assistant[0].text.startswith("I will start with the operation log format.")
    assert "Found it in oplog.py" not in " ".join(m.text for m in assistant)  # a sidechain
    tools = [m for m in msgs if m.speaker == "tool"]
    assert [m.text for m in tools] == ["Read: src/oplog.py", "Bash: Run the tests"]
    assert all(m.origin == "tool_output" for m in tools)
    assert [m.ordinal for m in msgs] == list(range(len(msgs)))
    assert msgs[3].id == f"{ledger1.id}:3" and msgs[3].source_id == ledger1.id


def test_usage_counts_each_response_once_and_not_sidechains(ledger1):
    assert [u.message_id for u in ledger1.usage] == [f"msg_l1_0{i}" for i in range(1, 8)]
    assert [u.context_tokens for u in ledger1.usage] == [12003, 12805, 150605, 300905, 522010, 40004, 40504]
    first = ledger1.usage[0]
    assert (first.input_tokens, first.cache_creation_input_tokens, first.cache_read_input_tokens) == (3, 12000, 0)
    assert first.output_tokens == 200 and first.model == "claude-opus-5-5"
    assert first.timestamp == "2026-03-02T09:00:20.000Z"
    assert ledger1.models == ["claude-opus-5-5"]


def test_compaction_point(ledger1):
    assert len(ledger1.compactions) == 1  # the boundary and its summary are one point
    c = ledger1.compactions[0]
    assert (c.timestamp, c.trigger, c.pre_tokens) == ("2026-03-02T10:31:00.000Z", "auto", 522010)


def test_skipped_lines_are_counted_by_type(ledger1):
    assert ledger1.skipped == {
        "command": 2,
        "compact_summary": 1,
        "file-history-snapshot": 1,
        "interrupt": 1,
        "meta": 1,
        "sidechain": 2,
        "summary": 1,
        "system": 1,
        "tool_result": 2,
        "unknown:progress": 1,
        "unknown:queue-operation": 1,
    }


def test_paste_ranges_and_models_in_order_of_use():
    s = parse_session(FIXTURES / "ledger_s2.jsonl")
    assert s.models == ["claude-sonnet-5-5", "claude-opus-5-5"]
    turn = s.typed_turns()[1]
    assert turn.text.startswith("Here are my notes:\n") and "<pasted_content" not in turn.text
    (start, end), = turn.meta["paste_ranges"]
    assert turn.text[start:end].startswith("The oplog format is JSON lines.")
    assert turn.text[start:end].endswith("the other side lacks.")
    assert turn.origin == "typed"  # the person typed around the paste


def test_tool_calls_with_several_inputs_and_none():
    s2 = parse_session(FIXTURES / "ledger_s2.jsonl")
    assert [m.text for m in s2.source.messages if m.speaker == "tool"] == [
        "Edit: src/uploader.py", "Grep: retry",
    ]
    s3 = parse_session(FIXTURES / "ledger_s3.jsonl")
    assert [m.text for m in s3.source.messages if m.speaker == "tool"] == [
        "Glob: src/**/export*.py", "TodoWrite",
    ]


def test_bad_json_and_api_errors_are_skipped_not_fatal():
    s = parse_session(FIXTURES / "ledger_s3.jsonl")
    assert s.skipped == {"api_error": 1, "invalid_json": 1}
    assert s.git_branch == "feature/export"
    assert len(s.typed_turns()) == 1 and len(s.usage) == 4


def test_command_with_words_is_kept_and_a_bare_command_is_not(tmp_path):
    path = write(
        tmp_path / "s.jsonl",
        user_line(
            "<command-name>/review</command-name>\n<command-message>review</command-message>\n"
            "<command-args>the tie-break change</command-args>", uuid="u1",
        ),
        user_line("<command-name>/clear</command-name>\n<command-args></command-args>", uuid="u2"),
        user_line("<local-command-stdout>done</local-command-stdout>", uuid="u3"),
    )
    s = parse_session(path)
    (turn,) = s.typed_turns()
    assert turn.text == "/review the tie-break change" and turn.meta["command"] == "/review"
    assert s.skipped == {"command": 2}


def test_unknown_shapes_never_raise(tmp_path):
    path = write(
        tmp_path / "odd.jsonl",
        "",
        "[1, 2]",
        '"just a string"',
        {"type": "user", "uuid": "a", "message": "not a dict", "timestamp": "2026-04-01T09:00:00Z"},
        {"type": "assistant", "uuid": "b", "message": {"role": "assistant", "content": None, "model": "m"}},
        {"type": "user", "uuid": "c", "message": {"role": "user", "content": [{"type": "image"}, 7]}},
        {"type": 5, "uuid": "d"},
        {"uuid": "e"},
        user_line("a real turn", uuid="f", timestamp="not a time"),
    )
    s = parse_session(path)
    assert [m.text for m in s.source.messages] == ["", "a real turn"]  # the first holds only an image
    assert s.source.messages[0].meta["images"] == 1
    assert s.skipped["invalid_json"] == 2
    assert s.skipped["user:no_message"] == 1
    assert s.skipped["unknown:5"] == 1 and s.skipped["unknown:None"] == 1
    assert s.source.started_at is None or parse_time(s.source.started_at) is not None
    assert parse_session(write(tmp_path / "empty.jsonl")).source.messages == []


def test_parse_time_treats_naive_as_utc():
    assert parse_time("2026-03-02T09:00:00") == datetime(2026, 3, 2, 9, tzinfo=timezone.utc)
    assert parse_time("2026-03-02T09:00:00Z") == parse_time("2026-03-02T11:00:00+02:00")
    assert parse_time("nonsense") is None and parse_time(None) is None and parse_time(5) is None


def test_parse_projects_sorts_by_start_and_drops_empty_files():
    sessions = parse_projects(FIXTURES)
    assert [(s.project.rsplit("/", 1)[1], s.source.started_at[:13]) for s in sessions] == [
        ("ledger-sync", "2026-03-02T09"),
        ("ledger-sync", "2026-03-02T13"),
        ("garden-notes", "2026-03-03T08"),
        ("garden-notes", "2026-03-03T11"),
        ("ledger-sync", "2026-03-20T10"),
        ("ledger-sync", "2026-03-25T10"),
    ]  # garden_agent.jsonl holds only sidechain lines, so it has no session
    assert len({s.id for s in sessions}) == 6
    assert {s.project for s in sessions} == {LEDGER, GARDEN}


def test_parse_projects_since_and_nested_folders(tmp_path):
    for name in ("ledger_s1", "ledger_s4", "garden_s1"):
        folder = tmp_path / name.split("_")[0] / "nested"
        folder.mkdir(parents=True, exist_ok=True)
        shutil.copy(FIXTURES / f"{name}.jsonl", folder / f"{name}.jsonl")
    assert len(parse_projects(tmp_path)) == 3
    later = parse_projects(tmp_path, since="2026-03-10T00:00:00+00:00")
    assert [s.source.started_at[:10] for s in later] == ["2026-03-25"]
    assert len(parse_projects(tmp_path, since=datetime(2026, 3, 3, tzinfo=timezone.utc))) == 2


def test_lines_copied_into_a_later_file_count_once(tmp_path):
    original = (FIXTURES / "ledger_s1.jsonl").read_text(encoding="utf-8").splitlines()
    fork = [json.loads(line) for line in original if line.startswith("{") and '"type": "user"' in line][:2]
    copied = [dict(o, sessionId="fork-session") for o in fork]
    extra = user_line("A new question in the fork.", ts="2026-03-02T12:00:00.000Z", uuid="fork-new")
    extra["sessionId"], extra["cwd"] = "fork-session", LEDGER
    shutil.copy(FIXTURES / "ledger_s1.jsonl", tmp_path / "a.jsonl")
    write(tmp_path / "b.jsonl", *copied, extra)
    sessions = parse_projects(tmp_path)
    by_id = {s.id: s for s in sessions}
    assert by_id["11111111-aaaa-4000-8000-000000000001"].source.messages[0].text.startswith("We need")
    fork_turns = [m.text for m in by_id["fork-session"].typed_turns()]
    assert fork_turns == ["A new question in the fork."]
    assert by_id["fork-session"].skipped["copied"] == len(copied)
