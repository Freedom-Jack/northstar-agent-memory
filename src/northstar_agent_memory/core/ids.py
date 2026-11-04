"""Identifiers and text normalization for the core (MEMORY-ARCHITECTURE §2.3, §5.4, invariant I2).

`new_id()` makes a ULID: a time-ordered, 26-character Crockford base32 identifier, so event IDs order across
devices. `normalize_text`, `content_hash` and `quote_matches` share one normalization, so a quote that passes
I2 is found by the same rule wherever it is checked.
"""

from __future__ import annotations

import hashlib
import re
import secrets
import threading
import time
import unicodedata
from datetime import datetime, timezone

ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # Crockford base32: no I, L, O, U
_DECODE = {c: i for i, c in enumerate(ALPHABET)}
ULID_LENGTH = 26
_RANDOM_BITS = 80

_lock = threading.Lock()
_last_ms = -1
_last_random = 0


def _encode(value: int) -> str:
    chars = []
    for _ in range(ULID_LENGTH):
        chars.append(ALPHABET[value & 31])
        value >>= 5
    return "".join(reversed(chars))


def new_id(now_ms: int | None = None) -> str:
    """A new ULID. Strictly increasing within one process, also inside one millisecond.

    If the clock steps back, the last timestamp is reused so order still holds. `now_ms` is for tests.
    """
    global _last_ms, _last_random
    with _lock:
        ms = time.time_ns() // 1_000_000 if now_ms is None else now_ms
        if ms <= _last_ms:
            ms = _last_ms
            rand = _last_random + 1
            if rand >> _RANDOM_BITS:  # 2**80 ids in one millisecond: move to the next one
                ms += 1
                rand = secrets.randbits(_RANDOM_BITS)
        else:
            rand = secrets.randbits(_RANDOM_BITS)
        _last_ms, _last_random = ms, rand
        return _encode((ms << _RANDOM_BITS) | rand)


def is_ulid(value: object) -> bool:
    return isinstance(value, str) and len(value) == ULID_LENGTH and value[0] <= "7" and all(c in _DECODE for c in value)


def ulid_time_ms(ulid: str) -> int:
    """The millisecond timestamp inside a ULID (UTC, Unix epoch)."""
    if not is_ulid(ulid):
        raise ValueError(f"not a ULID: {ulid!r}")
    value = 0
    for c in ulid:
        value = (value << 5) | _DECODE[c]
    return value >> _RANDOM_BITS


def utc_now() -> str:
    """The current time as ISO 8601 UTC with milliseconds, e.g. 2026-03-02T09:30:00.123Z (recorded_at)."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


_WHITESPACE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Unicode NFC, runs of whitespace collapsed to one space, ends stripped."""
    return _WHITESPACE.sub(" ", unicodedata.normalize("NFC", text)).strip()


def content_hash(text: str) -> str:
    """SHA-256 (hex) of the normalized text. Same words, same hash, whatever the spacing or Unicode form."""
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def quote_matches(quote: str, text: str) -> bool:
    """Invariant I2: the quote is an exact substring of the text, after normalizing both. An empty quote never matches."""
    wanted = normalize_text(quote)
    return bool(wanted) and wanted in normalize_text(text)
