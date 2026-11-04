"""ULIDs, text normalization, content hashes and the exact-quote rule (MEMORY-ARCHITECTURE §2.3, §5.4, I2)."""

from __future__ import annotations

import threading
import unicodedata

import pytest

from northstar_agent_memory.core import ids


def test_new_id_is_a_26_character_crockford_ulid():
    value = ids.new_id()
    assert len(value) == 26
    assert set(value) <= set(ids.ALPHABET)
    assert not set(value) & set("ILOU")
    assert ids.is_ulid(value)


def test_ids_are_unique_and_ordered_in_a_tight_loop():
    made = [ids.new_id() for _ in range(20_000)]
    assert len(set(made)) == len(made)
    assert made == sorted(made)


def test_ids_are_strictly_increasing_within_one_millisecond():
    made = [ids.new_id(now_ms=1_800_000_000_000) for _ in range(500)]
    assert made == sorted(made)
    assert len(set(made)) == 500
    assert {ids.ulid_time_ms(m) for m in made} == {1_800_000_000_000}


def test_a_later_millisecond_sorts_after_an_earlier_one():
    a = ids.new_id(now_ms=1_800_000_000_000)
    b = ids.new_id(now_ms=1_800_000_000_001)
    assert a < b
    assert ids.ulid_time_ms(b) - ids.ulid_time_ms(a) == 1


def test_a_clock_that_steps_back_keeps_order():
    a = ids.new_id(now_ms=1_900_000_000_000)
    b = ids.new_id(now_ms=1_900_000_000_000 - 5_000)
    assert a < b


def test_random_overflow_moves_to_the_next_millisecond(monkeypatch):
    monkeypatch.setattr(ids, "_last_ms", 2_000_000_000_000)
    monkeypatch.setattr(ids, "_last_random", (1 << 80) - 1)
    value = ids.new_id(now_ms=2_000_000_000_000)
    assert ids.ulid_time_ms(value) == 2_000_000_000_001


def test_ulid_time_round_trips_and_rejects_non_ulids():
    value = ids.new_id(now_ms=1_700_000_123_456)
    assert ids.ulid_time_ms(value) >= 1_700_000_123_456
    with pytest.raises(ValueError):
        ids.ulid_time_ms("not-a-ulid")
    assert not ids.is_ulid("8" + "0" * 25)  # the first character is at most 7: 128 bits
    assert not ids.is_ulid(None)


def test_ids_are_unique_across_threads():
    results: list[list[str]] = []

    def work():
        results.append([ids.new_id() for _ in range(2000)])

    threads = [threading.Thread(target=work) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    flat = [i for r in results for i in r]
    assert len(set(flat)) == len(flat) == 8000
    assert all(r == sorted(r) for r in results)


def test_utc_now_is_iso_8601_with_milliseconds():
    assert ids.utc_now().endswith("Z")
    assert len(ids.utc_now()) == len("2026-03-02T09:30:00.123Z")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  hello   world  ", "hello world"),
        ("line one\n\n  line\ttwo", "line one line two"),
        ("non breaking spaces", "non breaking spaces"),
        ("", ""),
        ("   ", ""),
    ],
)
def test_normalize_text_collapses_whitespace(raw, expected):
    assert ids.normalize_text(raw) == expected


def test_normalize_text_uses_nfc():
    decomposed = "café"
    composed = "café"
    assert decomposed != composed
    assert ids.normalize_text(decomposed) == composed
    assert unicodedata.is_normalized("NFC", ids.normalize_text(decomposed))


def test_content_hash_ignores_spacing_and_unicode_form_but_not_words():
    assert ids.content_hash("café  au lait") == ids.content_hash("café au\nlait ")
    assert ids.content_hash("one file per meter") != ids.content_hash("one file per sensor")
    assert len(ids.content_hash("x")) == 64
    assert ids.content_hash("x") == ids.content_hash(" x ")


def test_quote_matches_is_an_exact_substring_after_normalizing():
    text = "Store readings in SQLite on the Pi,\n  one file per meter. No server yet."
    assert ids.quote_matches("one file per meter", text)
    assert ids.quote_matches("Pi, one file", text)  # a line break and spaces collapse
    assert ids.quote_matches("  Store   readings ", text)
    assert not ids.quote_matches("one file per sensor", text)
    assert not ids.quote_matches("store readings", text)  # case matters
    assert not ids.quote_matches("", text)
    assert not ids.quote_matches("   ", text)


def test_quote_matches_handles_nfc():
    text = "Le café est fermé"
    assert ids.quote_matches("café est", text)
    assert ids.quote_matches("café", "café")


def test_a_quote_cannot_be_longer_than_its_text():
    assert not ids.quote_matches("a b c d", "a b c")
