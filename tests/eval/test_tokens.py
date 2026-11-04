"""Token estimate and budget fitting: pure functions, no models."""

from __future__ import annotations

from northstar_agent_memory.eval.tokens import TRUNCATED, Fitted, cut_to_tokens, estimate_tokens, fit_to_budget


def test_estimate_is_ceil_of_chars_over_3_5():
    assert estimate_tokens("") == 0
    assert estimate_tokens("a") == 1
    assert estimate_tokens("a" * 7) == 2
    assert estimate_tokens("a" * 8) == 3


def test_estimate_over_counts_plain_english():
    text = "The quick brown fox jumps over the lazy dog. " * 100
    # Ordinary English runs near 4 characters a token, so 3.5 never under-counts it.
    assert estimate_tokens(text) >= len(text) / 4.2


def test_fit_keeps_whole_blocks_in_priority_order():
    blocks = ["a" * 35, "b" * 35, "c" * 35]  # 10 tokens each
    assert fit_to_budget(blocks, 25).blocks == blocks[:2]
    assert fit_to_budget(blocks, 30).blocks == blocks
    assert fit_to_budget([], 100) == Fitted([])
    assert not fit_to_budget(blocks, 30).truncated and fit_to_budget(blocks, 30).text is None


def test_fit_skips_a_later_block_that_does_not_fit_but_tries_the_ones_after():
    blocks = ["a" * 35, "b" * 350, "c" * 35]
    fitted = fit_to_budget(blocks, 25)
    assert fitted.blocks == [blocks[0], blocks[2]] and not fitted.truncated


def test_fit_cuts_the_top_block_when_it_alone_is_over_the_budget():
    blocks = ["a" * 350, "b" * 7]
    fitted = fit_to_budget(blocks, 20)
    assert fitted.truncated and fitted.blocks == [blocks[0]]  # the budget is spent on it
    assert fitted.text.endswith("\n" + TRUNCATED) and fitted.text.startswith("aaaa")
    assert estimate_tokens(fitted.text) <= 20
    assert set(fitted.text.removesuffix("\n" + TRUNCATED)) == {"a"}


def test_fit_cut_uses_key_and_stays_within_the_budget_for_any_size():
    items = [{"t": "x" * 700}, {"t": "y" * 7}]
    for budget in range(1, 60):
        fitted = fit_to_budget(items, budget, key=lambda b: b["t"])
        if fitted.truncated:
            assert fitted.blocks == [items[0]] and estimate_tokens(fitted.text) <= budget
        else:
            assert sum(estimate_tokens(b["t"]) for b in fitted.blocks) <= budget


def test_fit_with_no_room_even_for_the_marker_keeps_nothing_cut():
    fitted = fit_to_budget(["z" * 100], 2)
    assert fitted == Fitted([]) and not fitted.truncated
    assert fit_to_budget(["z" * 100], 0).blocks == []


def test_fit_does_not_cut_a_block_that_fits_or_one_that_is_not_first():
    blocks = ["a" * 35, "b" * 350]
    fitted = fit_to_budget(blocks, 20)
    assert fitted.blocks == [blocks[0]] and not fitted.truncated and fitted.text is None


def test_fit_does_not_exceed_the_budget():
    blocks = ["w" * n for n in (40, 10, 90, 5, 33, 70, 12)]
    fitted = fit_to_budget(blocks, 30)
    assert not fitted.truncated and sum(estimate_tokens(b) for b in fitted.blocks) <= 30


def test_cut_to_tokens():
    text = "z" * 100
    assert cut_to_tokens(text, 0) == ""
    assert estimate_tokens(cut_to_tokens(text, 10)) <= 10
    assert cut_to_tokens("short", 1000) == "short"
