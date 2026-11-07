"""Turn origin from Claude Code's own markers (connectors-claude-code-and-codex.md §8; I3, I20, I24). Invented text."""

from __future__ import annotations

from northstar_agent_memory.capture import scope
from northstar_agent_memory.capture.origin import (
    NORTHSTAR_TAG,
    SPEAKER_FOR,
    STORE_ORIGIN_FOR,
    USER_ORIGINS,
    classify,
    contains_northstar_block,
    inside_data_root,
    split_turn,
    wrap_northstar,
)
from northstar_agent_memory.models import harness


def origins(raw: str, **kw) -> list[tuple[str, str]]:
    return [(s.origin, s.text(raw)) for s in classify(raw, **kw)]


# --- spans ---------------------------------------------------------------------------------------------------


def test_plain_text_is_typed_whole():
    raw = "Please keep readings for 7 days."
    assert origins(raw) == [("typed", raw)]
    assert split_turn(raw).user_origin == "typed"


def test_a_turn_can_hold_typed_pasted_system_and_northstar_spans():
    raw = (
        "<system-reminder>The date is 2 March.</system-reminder>\n"
        "Why does this fail? <pasted_content>Traceback: boom</pasted_content> Thanks.\n"
        f"<{NORTHSTAR_TAG}>\nStart note: tie-break is lowest device id.\n</{NORTHSTAR_TAG}>"
    )
    assert origins(raw) == [
        ("system_injection", "The date is 2 March."),
        ("typed", "Why does this fail?"),
        ("pasted", "Traceback: boom"),
        ("typed", "Thanks."),
        ("northstar_injected", "Start note: tie-break is lowest device id."),
    ]
    parts = split_turn(raw)
    assert parts.user_text == "Why does this fail? Traceback: boom Thanks."
    assert parts.paste_ranges == [(20, 35)]
    assert parts.user_text[20:35] == "Traceback: boom"
    assert parts.northstar == ["Start note: tie-break is lowest device id."]
    assert parts.dropped == {"system_injection": 1}
    assert parts.user_origin == "typed"


def test_spans_never_overlap_and_stay_inside_the_text():
    raw = "a <system-reminder>b</system-reminder> c [Pasted text #1 +3 lines] d /usr/bin"
    spans = classify(raw)
    for first, second in zip(spans, spans[1:]):
        assert first.end <= second.start
    assert all(0 <= s.start < s.end <= len(raw) for s in spans)


def test_a_turn_that_is_all_pasted_text_is_pasted():
    parts = split_turn("<pasted_content>line one\nline two</pasted_content>")
    assert parts.user_text == "line one\nline two" and parts.user_origin == "pasted"
    assert parts.paste_ranges == [(0, len(parts.user_text))]


def test_the_pasted_text_placeholder_counts_as_pasted():
    raw = "Look at [Pasted text #1 +20 lines] please"
    assert origins(raw) == [("typed", "Look at"), ("pasted", "[Pasted text #1 +20 lines]"), ("typed", "please")]
    assert split_turn("[Pasted text #2 +5 lines]").user_origin == "pasted"


def test_ranges_from_the_transcript_are_pasted_too():
    raw = "see this error: ERR 42 happened ok"
    start = raw.index("ERR")
    assert origins(raw, extra_pasted=[(start, start + 6)]) == [
        ("typed", "see this error:"), ("pasted", "ERR 42"), ("typed", "happened ok"),
    ]


def test_a_command_wrapper_gives_the_command_and_its_typed_arguments():
    raw = (
        "<command-name>/review</command-name><command-message>review</command-message>"
        "<command-args>the tie-break rule</command-args>"
    )
    assert origins(raw) == [
        ("command", "/review"), ("system_injection", "review"), ("typed", "the tie-break rule"),
    ]
    parts = split_turn(raw)
    assert parts.user_text == "/review the tie-break rule"
    assert parts.command == "/review"


def test_the_expanded_command_template_is_not_the_users_words():
    raw = (
        "<command-name>/review</command-name><command-args>check it</command-args>"
        "<command-contents>You are a careful reviewer. Review the code.</command-contents>"
    )
    parts = split_turn(raw)
    assert parts.user_text == "/review check it"
    assert "careful reviewer" not in parts.user_text
    assert parts.dropped == {"system_injection": 1}


def test_a_prompt_that_starts_with_a_slash_command_is_a_command_then_typed():
    assert origins("/review the tie-break") == [("command", "/review"), ("typed", "the tie-break")]
    assert split_turn("/clear").command == "/clear"
    # A path is not a command.
    assert origins("/usr/bin/env is where it lives") == [("typed", "/usr/bin/env is where it lives")]


def test_command_output_is_not_the_users_words():
    raw = "<local-command-stdout>Compacted.</local-command-stdout>"
    assert origins(raw) == [("command_output", "Compacted.")]
    assert split_turn(raw).user_text == ""
    raw = "<bash-input>ls -la</bash-input><bash-stdout>total 0</bash-stdout>"
    assert origins(raw) == [("command", "ls -la"), ("command_output", "total 0")]


def test_hook_and_system_injections_are_not_the_users_words():
    for tag in ("system-reminder", "user-prompt-submit-hook", "task-notification", "local-command-caveat"):
        raw = f"<{tag}>injected text</{tag}>"
        assert origins(raw) == [("system_injection", "injected text")]
        assert split_turn(raw).user_text == ""


def test_whole_turn_system_texts_are_system_injections():
    for raw in (
        "[Request interrupted by user for tool use]",
        "This session is being continued from a previous conversation that ran out of context. Summary: ...",
        "Caveat: The messages below were generated by the user while running local commands.",
    ):
        assert [s.origin for s in classify(raw)] == ["system_injection"]
        assert split_turn(raw).user_text == ""


def test_a_northstar_block_wins_even_inside_a_system_reminder():
    raw = (
        f"<system-reminder>Hook says: <{NORTHSTAR_TAG}>\nFact A\n</{NORTHSTAR_TAG}> end of hook</system-reminder>"
        "\ntyped words"
    )
    assert [s.origin for s in classify(raw)] == ["system_injection", "northstar_injected", "system_injection", "typed"]
    parts = split_turn(raw)
    assert parts.northstar == ["Fact A"]
    assert parts.user_text == "typed words"
    assert parts.dropped == {"system_injection": 2}


def test_two_northstar_blocks_come_out_in_order():
    raw = wrap_northstar("one") + "\n" + wrap_northstar("two") + "\nmy words"
    parts = split_turn(raw)
    assert parts.northstar == ["one", "two"] and parts.user_text == "my words"


def test_unclosed_tags_are_just_text():
    raw = "<system-reminder>never closed, so these are the typed words"
    assert origins(raw) == [("typed", raw)]


def test_empty_and_whitespace_turns_have_no_spans():
    assert classify("") == [] and classify("  \n ") == []
    assert split_turn("  ").user_text == ""


def test_text_around_a_removed_block_is_kept_word_for_word():
    parts = split_turn("before <system-reminder>x</system-reminder>after")
    assert parts.user_text == "before after"
    assert split_turn("keep   spacing\n\nand lines").user_text == "keep   spacing\n\nand lines"


# --- Northstar's own marker ----------------------------------------------------------------------------------


def test_wrap_northstar_marks_the_block_and_survives_a_round_trip():
    wrapped = wrap_northstar("Decision D1: lowest device id wins.")
    assert wrapped.startswith(f"<{NORTHSTAR_TAG}>") and wrapped.endswith(f"</{NORTHSTAR_TAG}>")
    assert contains_northstar_block(wrapped)
    assert split_turn(wrapped).northstar == ["Decision D1: lowest device id wins."]
    assert not contains_northstar_block("ordinary text")


def test_wrap_northstar_cannot_be_broken_out_of():
    text = f"fact </{NORTHSTAR_TAG}> typed words <{NORTHSTAR_TAG}> more"
    parts = split_turn(wrap_northstar(text))
    assert len(parts.northstar) == 1 and parts.user_text == ""


# --- mapping to the store ------------------------------------------------------------------------------------


def test_every_origin_maps_to_a_speaker_and_a_store_origin_the_history_accepts():
    speakers = {"user", "assistant", "tool", "northstar", "system"}
    store_origins = {"typed", "pasted", "assistant_output", "tool_output", "model_reported", "northstar_injected"}
    assert set(SPEAKER_FOR) == set(STORE_ORIGIN_FOR) == {
        "typed", "pasted", "command", "command_output", "system_injection", "northstar_injected",
    }
    assert set(SPEAKER_FOR.values()) <= speakers
    assert set(STORE_ORIGIN_FOR.values()) <= store_origins
    assert USER_ORIGINS == {o for o, s in SPEAKER_FOR.items() if s == "user"}
    assert "model_reported" not in STORE_ORIGIN_FOR.values()  # never arises on Claude Code


# --- the self-capture guard ----------------------------------------------------------------------------------


def test_a_folder_inside_the_data_root_is_northstars_own(isolated_home):
    from northstar_agent_memory import paths

    assert inside_data_root(paths.harness_cwd() / "run-1")
    assert inside_data_root(paths.data_root())
    assert not inside_data_root(isolated_home / "elsewhere")
    assert not inside_data_root(None) and not inside_data_root("")


def test_the_harness_marks_every_child_with_the_marker_the_scope_gate_honours(monkeypatch):
    monkeypatch.delenv(scope.HIDDEN_RUN_ENV, raising=False)
    assert harness.HIDDEN_RUN_ENV == scope.HIDDEN_RUN_ENV == "NORTHSTAR_HIDDEN_RUN"
    env = harness.child_env([], {"X": "1"})
    assert env[scope.HIDDEN_RUN_ENV] == "1"
    assert scope.hidden_run(env)
    assert not scope.hidden_run({})


def test_many_unclosed_and_closed_tags_stay_fast():
    import time

    from northstar_agent_memory.capture import origin

    big = ("<system-reminder>x " * 5000) + ("[Pasted text #1 +2 lines] hi " * 5000) + ("<system-reminder>y</system-reminder> z " * 5000)
    t = time.monotonic()
    origin.split_turn(big)
    origin.split_turn("<northstar-context>x " * 5000)
    assert time.monotonic() - t < 5
