"""Replace secrets before anything is written, to the spool or to the database (MEMORY-ARCHITECTURE §2.2;
connectors-claude-code-and-codex.md §4.1 step 6).

`scrub(text)` returns the text with each secret replaced by "[secret removed: <kind>]" and a list of findings:
the kinds and how many of each, never the secret itself. Plain code, no model.

What it looks for, most specific first (an earlier kind wins where two overlap):
- private key blocks; API keys and tokens of the main vendors (Anthropic, OpenAI, GitHub, AWS access key with its
  secret, Google, Slack, Stripe, npm, Hugging Face, SendGrid); JWTs;
- passwords in URLs, and token-like query parameters;
- "Authorization:" headers and "Bearer <token>";
- .env lines whose key names a secret, and "password=", "token:", "api_key: ..." pairs in code, JSON and YAML;
- a long high-entropy string close to a word such as "token" or "password".

Ordinary text is left alone: ULIDs, UUIDs, git commit hashes and other hex digests, base64 images in data URLs,
variables and function calls on the right of "password=", placeholders such as "<token>" or "${TOKEN}", numbers
("max_tokens=4096") and prose. A second pass over scrubbed text changes nothing, so a message scrubbed on the way
into the spool and again on its way into history is stored once.
"""

from __future__ import annotations

import bisect
import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Iterable

REPLACEMENT = "[secret removed: {kind}]"


@dataclass(frozen=True, slots=True)
class Finding:
    """One kind of secret found, and how many. Never the secret."""

    kind: str
    count: int


def replacement(kind: str) -> str:
    return REPLACEMENT.format(kind=kind)


def tally(findings: Iterable[Finding], into: Counter[str] | None = None) -> Counter[str]:
    """Add findings to a running count by kind (the backfill summary)."""
    counts: Counter[str] = Counter() if into is None else into
    for finding in findings:
        counts[finding.kind] += finding.count
    return counts


# --- vendor tokens -------------------------------------------------------------------------------------------

_BODY = r"[A-Za-z0-9_\-]"
_VENDOR: list[tuple[str, re.Pattern[str]]] = [
    ("private_key", re.compile(
        r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY(?: BLOCK)?-----.*?-----END [A-Z0-9 ]*PRIVATE KEY(?: BLOCK)?-----", re.S)),
    # A block cut short (a truncated paste): the header and the base64 lines after it.
    ("private_key", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY(?: BLOCK)?-----(?:[ \t]*\r?\n[A-Za-z0-9+/=:,\- ]{16,})+")),
    ("anthropic_api_key", re.compile(rf"\bsk-ant-{_BODY}{{20,}}")),
    ("openai_api_key", re.compile(rf"\bsk-(?:proj|svcacct|admin)-{_BODY}{{20,}}|\bsk-[A-Za-z0-9]{{32,}}(?![A-Za-z0-9])")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,255}|\bgithub_pat_[A-Za-z0-9_]{22,255}")),
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}(?![A-Za-z0-9])")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}(?![0-9A-Za-z_\-])")),
    ("slack_token", re.compile(r"\bxox[abposr]-[A-Za-z0-9\-]{10,}|\bxapp-[A-Za-z0-9\-]{10,}")),
    ("slack_webhook", re.compile(r"https://hooks\.slack\.com/services/[A-Za-z0-9]+/[A-Za-z0-9]+/[A-Za-z0-9]{16,}")),
    ("stripe_key", re.compile(r"\b[sr]k_(?:live|test)_[A-Za-z0-9]{16,}")),
    ("npm_token", re.compile(r"\bnpm_[A-Za-z0-9]{36}(?![A-Za-z0-9])")),
    ("huggingface_token", re.compile(r"\bhf_[A-Za-z0-9]{34,}")),
    ("sendgrid_key", re.compile(r"\bSG\.[A-Za-z0-9_\-]{22}\.[A-Za-z0-9_\-]{43}")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]*")),
]

# Base64 data (images in data URLs) is never a secret, whatever words sit beside it.
_DATA_URL = re.compile(r"data:[\w.+\-]+/[\w.+\-]+(?:;[\w.+=\-]+)*;base64,[A-Za-z0-9+/=_\-]+")

# AWS: a 40-character secret within a couple of lines of an access key id.
_AWS_SECRET = re.compile(r"(?<![A-Za-z0-9/+=])[A-Za-z0-9/+]{40}(?![A-Za-z0-9/+=])")
_AWS_WINDOW = 200

# --- URLs and headers ----------------------------------------------------------------------------------------

_URL_PASSWORD = re.compile(r"(?<![A-Za-z0-9+.\-])[A-Za-z][A-Za-z0-9+.\-]{0,20}://[^\s/:@]+:(?P<val>[^\s/@]+)@")
_URL_PARAM = re.compile(
    r"(?i)[?&;](?:access_token|refresh_token|id_token|auth_token|api_key|apikey|api-key|token|secret|client_secret"
    r"|password|passwd|pwd|sig|signature|x-amz-signature|x-amz-security-token)=(?P<val>[^&\s#\"'<>]{6,})"
)
_AUTH_HEADER = re.compile(
    r"(?i)\bauthorization[ \t]*[:=][ \t]*[\"']?(?:(?:bearer|basic|token|digest)[ \t]+)?(?P<val>[\w.~+/\-]{8,}=*)"
)
_BEARER = re.compile(r"(?i)\bbearer[ \t]+(?P<val>[A-Za-z0-9._~+/\-]{20,}=*)")

# --- key = value ---------------------------------------------------------------------------------------------

# The key is the tail of a run of name characters (at most 61 long, starting with a letter or "_") that ends at the
# operator. The run is taken whole, from its first character, and the key cut from its end in `_pair_candidates`: trying
# a match at every character of a long run, as a lazy `{0,60}?` key does, costs 60 steps for each one (300 KB of one
# letter took 0.4 s). The lookbehind lets a match start only at the front of a run; the possessive `++` is safe because
# the next character can never be one the run takes. The value is matched apart, only for a run with a usable key, so
# a long text of "1:1:1:..." does not read 300 characters of value for each of its colons.
_PAIR_HEAD = re.compile(r"""(?<![\w.\-])(?P<run>[\w.\-]++)["']?[ \t]*(?P<op>=>|:|=)[ \t]*""")
_PAIR_VALUE = re.compile(r"""(?P<val>"[^"\n]{1,300}"|'[^'\n]{1,300}'|[^\s,;)\]}"']{1,300})""")
_KEY_START = re.compile(r"[A-Za-z_]")
_KEY_MAX = 61
# A .env line: the value is the rest of the line, whatever it holds.
_DOTENV = re.compile(
    r"(?m)^[ \t]*(?:export[ \t]+)?(?P<key>[A-Z][A-Z0-9_]*)[ \t]*=[ \t]*(?P<val>[^\n]*?)[ \t]*$"
)
_WORDS = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+")
_PASSWORD_WORDS = {"password", "passwords", "passwd", "pwd", "passphrase"}
_SECRET_WORDS = {"secret", "secrets", "credential", "credentials"}
_TOKEN_WORDS = {"token"}  # "tokens" is a count of model tokens, not a secret
_API_KEY_PAIRS = {("api", "key"), ("api", "keys"), ("access", "key"), ("private", "key"), ("auth", "key"), ("auth", "token")}
# A key that ends in one of these describes a secret (its name, count, place) rather than holding one.
_DESCRIPTIVE_LAST = {
    "count", "limit", "type", "name", "id", "path", "file", "length", "len", "expiry", "expires", "ttl", "url", "uri",
    "header", "field", "env", "var", "prefix", "label", "hint", "policy", "manager", "store", "provider", "service",
    "scope", "budget", "usage", "size", "endpoint", "page", "form", "input", "dir", "folder", "mode", "kind",
}
_PLACEHOLDER_WORDS = {
    "none", "null", "nil", "true", "false", "undefined", "string", "str", "empty", "redacted", "changeme", "change-me",
    "example", "password", "secret", "token", "required", "optional", "todo", "tbd", "n/a", "hidden", "masked",
    "env", "environ", "getpass", "input", "unset", "default", "placeholder", "dummy", "test", "value", "xxx",
}
_PLACEHOLDER_START = ("<", "{", "$", "%", "[", "...", "***", "•", "your", "my-", "my_", "example", "<<", "@")
_IDENT_CHAIN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")
_UNITS = re.compile(r"\d+[A-Za-z]{1,3}")
_VERSIONISH = re.compile(r"v?\d+(?:[.\-:/]\d+)*")

# --- long strings beside a secret word -----------------------------------------------------------------------

_NEAR = re.compile(
    r"(?i)\b(?:secrets?|tokens?|passwords?|passwd|passphrase|credentials?|api[ _\-]?keys?|apikey|access[ _\-]?keys?"
    r"|private[ _\-]?keys?)\b(?P<gap>[^\n]{0,30}?)(?<![A-Za-z0-9+/_=\-])(?P<val>[A-Za-z0-9+/_=\-]{24,})(?![A-Za-z0-9+/_=\-])"
)
_HASH_WORDS = re.compile(r"(?i)hash|\bsha\d*\b|commit|checksum|digest|uuid|\bid\b|\bmd5\b|etag|\brev\b|ulid")
_HEX = re.compile(r"[0-9a-fA-F]+")
_UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
_ULID = re.compile(r"[0-7][0-9A-HJKMNP-TV-Z]{25}")
_MIN_ENTROPY = 3.5


def _hash_context(text: str, start: int) -> bool:
    """Words just before a value that name it a hash, a digest or an id: sha256 of the secret: <hex>."""
    return _HASH_WORDS.search(text[max(0, start - 40) : start]) is not None


def _entropy(value: str) -> float:
    counts = Counter(value)
    n = len(value)
    return -sum(c / n * math.log2(c / n) for c in counts.values())


def _classes(value: str) -> tuple[bool, bool, bool, bool]:
    return (
        any(c.islower() for c in value),
        any(c.isupper() for c in value),
        any(c.isdigit() for c in value),
        any(not c.isalnum() for c in value),
    )


def _is_wordy(value: str) -> bool:
    """Mostly lowercase words joined by - or _ : an identifier or a slug, not a key."""
    pieces = [p for p in re.split(r"[-_/+=]", value) if p]
    if len(pieces) < 3:
        return False
    word_chars = sum(len(p) for p in pieces if len(p) >= 3 and p.isalpha() and p.islower())
    return word_chars * 2 > sum(len(p) for p in pieces)


def _looks_random(value: str) -> bool:
    """A long string that reads as a key: mixed classes with a digit, high entropy, not a UUID, ULID or slug."""
    if _UUID.fullmatch(value) or _ULID.fullmatch(value) or _is_wordy(value):
        return False
    lower, upper, digit, _ = _classes(value)
    if not digit or not (lower or upper):
        return False
    return _entropy(value) >= _MIN_ENTROPY


# --- the key / value rules ---------------------------------------------------------------------------------


def _key_kind(key: str) -> str | None:
    """"password", "secret", "token", "api_key" or "credential" if the key's own words name one; else None."""
    words = [w.lower() for w in _WORDS.findall(key)]
    if not words:
        return None
    last = words[-1]
    if last in _DESCRIPTIVE_LAST and len(words) > 1:
        return None
    if any(w in _PASSWORD_WORDS for w in words):
        return "password"
    if any(w in _TOKEN_WORDS for w in words):
        return "token"
    if any(w in _SECRET_WORDS for w in words):
        return "secret"
    if "apikey" in words:
        return "api_key"
    if any((a, b) in _API_KEY_PAIRS for a, b in zip(words, words[1:])):
        return "api_key"
    if "credential" in words or "credentials" in words:
        return "credential"
    return None


def _is_placeholder(value: str) -> bool:
    v = value.strip().strip("'\"`").strip()
    if not v:
        return True
    low = v.lower()
    if low in _PLACEHOLDER_WORDS or low.startswith(_PLACEHOLDER_START):
        return True
    if re.fullmatch(r"[xX*•.\-_ #]+", v):
        return True
    if re.fullmatch(r"[A-Z][A-Z0-9_]+", v):  # a constant's name: TOKEN_NAME
        return True
    return "process.env" in v or "os.environ" in v or "getenv" in v


def _unquoted_is_secret(kind: str, value: str) -> bool:
    if any(ch in value for ch in "()[]$<>`") or value.startswith("-"):
        return False  # a call, an index, a template or a flag
    if _VERSIONISH.fullmatch(value) or _UNITS.fullmatch(value):
        return False
    if _IDENT_CHAIN.fullmatch(value) and not any(c.isdigit() for c in value):
        return False  # a variable or attribute: password=password, token=self.token
    if "/" in value and not any(c.isdigit() for c in value):
        return False  # a path
    lower, upper, digit, symbol = _classes(value)
    letter = lower or upper
    floor = 6 if kind == "password" else 8
    if len(value) < floor:
        return False
    if kind != "password" and len(value) < 12 and not (digit and letter and (upper or symbol)):
        return False
    return (digit and letter) or (letter and symbol) or (lower and upper and len(value) >= 12)


def _quoted_is_secret(inner: str) -> bool:
    if len(inner) < 6 or _is_placeholder(inner):
        return False
    if inner.startswith(("http://", "https://")) and "@" not in inner:
        return False
    if re.search(r"\s", inner):
        words = inner.split()
        if len(words) >= 4 or inner.endswith((":", "?", ".", "!")):
            return False  # a prompt or a sentence
    if _IDENT_CHAIN.fullmatch(inner) and "_" in inner and inner.islower():
        return False  # a name such as "user_token_cache"
    return True


def _dotenv_is_secret(kind: str, value: str) -> bool:
    """A value on a line like `STRIPE_API_KEY=...`, whose key names a secret. The value may be any word, but a line of
    code that merely looks like one (`TOKEN = os.environ[...]`, `CHARS_PER_TOKEN = 3.5`, `PASSWORD = my_var`) is not."""
    quoted = len(value) > 1 and value[0] in "'\"" and value[-1] == value[0]
    inner = value[1:-1] if quoted else value.strip()
    if len(inner) < 3 or _is_placeholder(inner) or inner.startswith("[secret removed"):
        return False
    if _VERSIONISH.fullmatch(inner) or _UNITS.fullmatch(inner):
        return kind == "password" and inner.isdigit() and len(inner) >= 6
    if quoted:
        return not (re.search(r"\s", inner) and (len(inner.split()) >= 4 or inner.endswith((":", "?", ".", "!"))))
    if any(ch in inner for ch in "()[]$<>`"):
        return False
    return not (_IDENT_CHAIN.fullmatch(inner) and ("_" in inner or "." in inner))  # a variable


def _trim_end(text: str, start: int, end: int) -> int:
    """Leave sentence punctuation after an unquoted value out of the secret."""
    while end > start + 1 and text[end - 1] in ".!?:":
        end -= 1
    return end


# --- scanning ------------------------------------------------------------------------------------------------

# (priority, start, end, kind); the lowest priority number wins an overlap.
_Candidate = tuple[int, int, int, str]


def _vendor_candidates(text: str) -> list[_Candidate]:
    out: list[_Candidate] = []
    for prio, (kind, pattern) in enumerate(_VENDOR):
        for m in pattern.finditer(text):
            out.append((prio, m.start(), m.end(), kind))
    base = len(_VENDOR)
    for m in _AWS_ID_RE.finditer(text):
        lo, hi = max(0, m.start() - _AWS_WINDOW), m.end() + _AWS_WINDOW
        for s in _AWS_SECRET.finditer(text, lo, hi):
            lower, upper, digit, _ = _classes(s.group())
            if (s.start() >= m.end() or s.end() <= m.start()) and lower and upper and digit:
                out.append((base, s.start(), s.end(), "aws_secret_key"))
    return out


_AWS_ID_RE = re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}(?![A-Za-z0-9])")


def _url_candidates(text: str, prio: int) -> list[_Candidate]:
    out: list[_Candidate] = []
    for m in _URL_PASSWORD.finditer(text):
        if not _is_placeholder(m.group("val")) and not m.group("val").startswith("%7B"):
            out.append((prio, m.start("val"), m.end("val"), "url_password"))
    for m in _URL_PARAM.finditer(text):
        if not _is_placeholder(m.group("val")) and not m.group("val").startswith("%7B"):
            out.append((prio + 1, m.start("val"), m.end("val"), "url_token"))
    for m in _AUTH_HEADER.finditer(text):
        if not _is_placeholder(m.group("val")):
            out.append((prio + 2, m.start("val"), m.end("val"), "auth_header"))
    for m in _BEARER.finditer(text):
        val = m.group("val")
        if any(c.isdigit() for c in val) and not _is_placeholder(val) and not val.startswith("[secret"):
            out.append((prio + 3, m.start("val"), m.end("val"), "bearer_token"))
    return out


def _pair_candidates(text: str, prio: int) -> list[_Candidate]:
    out: list[_Candidate] = []
    for m in _DOTENV.finditer(text):
        kind = _key_kind(m.group("key"))
        if kind is None:
            continue
        val = m.group("val")
        quote = 1 if val[:1] in "'\"" and val[-1:] == val[:1] and len(val) > 1 else 0
        if not quote:
            val = re.split(r"[ \t]+#", val, maxsplit=1)[0].rstrip()  # a trailing comment is not part of the value
        if not _dotenv_is_secret(kind, val):
            continue
        out.append((prio, m.start("val") + quote, m.start("val") + len(val) - quote, kind))
    pos = 0
    while (m := _PAIR_HEAD.search(text, pos)) is not None:
        run = m.group("run")
        first = _KEY_START.search(run, max(0, len(run) - _KEY_MAX))
        found = _PAIR_VALUE.match(text, m.end()) if first is not None else None
        if found is None:  # no key or no value here: a later match may start inside what follows, as at each character
            pos = m.end("run")
            continue
        pos = found.end()
        key_start = m.start("run") + first.start()
        kind = _key_kind(run[first.start() :])
        if kind is None:
            continue
        val = found.group("val")
        start, end = found.start("val"), found.end("val")
        if _HEX.fullmatch(val) and len(val) >= 32 and _hash_context(text, key_start):
            continue  # a digest, named as one
        if val[0] in "'\"":
            inner = val[1:-1]
            if not _quoted_is_secret(inner):
                continue
            start, end = start + 1, end - 1
        else:
            end = _trim_end(text, start, end)
            val = text[start:end]
            if _is_placeholder(val) or not _unquoted_is_secret(kind, val):
                continue
        out.append((prio + 1, start, end, kind))
    return out


_IS_PASSWORD = re.compile(r"(?i)\b(?:password|passcode|passphrase|passwd)[ \t]+is[ \t]+[`'\"]?(?P<val>[^\s`'\"]{8,100})")


def _is_candidates(text: str, prio: int) -> list[_Candidate]:
    """Prose such as "my password is Tr0ub4dor&3": a value with letters and a digit or symbol, not a word."""
    out: list[_Candidate] = []
    for m in _IS_PASSWORD.finditer(text):
        start, end = m.start("val"), _trim_end(text, m.start("val"), m.end("val"))
        val = text[start:end]
        lower, upper, digit, symbol = _classes(val)
        if (lower or upper) and (digit or symbol) and not _is_placeholder(val) and not val.startswith("[secret"):
            out.append((prio, start, end, "password"))
    return out


def _near_candidates(text: str, prio: int) -> list[_Candidate]:
    out: list[_Candidate] = []
    for m in _NEAR.finditer(text):
        val = m.group("val")
        if val.startswith("[secret"):
            continue
        if _HEX.fullmatch(val):
            # A hex string beside "token" is a key unless it is named as a hash or a commit.
            if _hash_context(text, m.start("val")) or len(val) < 32 or _UUID.fullmatch(val):
                continue
        elif not _looks_random(val):
            continue
        out.append((prio, m.start("val"), m.end("val"), "high_entropy"))
    return out


def _overlaps(starts: list[int], spans: list, start: int, end: int) -> bool:
    """Whether [start, end) overlaps a span of `spans` (disjoint, sorted; `starts` is their start offsets)."""
    i = bisect.bisect_left(starts, start)
    if i < len(spans) and spans[i][0] < end:
        return True  # the first span that starts at or after `start` begins before `end`
    return i > 0 and spans[i - 1][1] > start


def scrub(text: str) -> tuple[str, list[Finding]]:
    """The text with every secret replaced by "[secret removed: <kind>]", and what was found (kinds and counts)."""
    if not text:
        return text, []
    protected = [(m.start(), m.end()) for m in _DATA_URL.finditer(text)]
    candidates = _vendor_candidates(text)
    base = len(_VENDOR) + 1
    candidates += _url_candidates(text, base)
    candidates += _pair_candidates(text, base + 4)
    candidates += _is_candidates(text, base + 5)
    candidates += _near_candidates(text, base + 6)

    # Both lists are disjoint and kept sorted by start, so "does this overlap one?" looks at one neighbour on each side
    # (bisect): a pass over every kept span for every candidate is quadratic, and 14,000 passwords took 1.4 s.
    protected_starts = [ps for ps, _ in protected]
    chosen_starts: list[int] = []
    chosen: list[tuple[int, int, str]] = []
    for _, start, end, kind in sorted(candidates):
        if end <= start:
            continue
        if _overlaps(protected_starts, protected, start, end):
            continue
        if _overlaps(chosen_starts, chosen, start, end):
            continue
        at = bisect.bisect_left(chosen_starts, start)
        chosen_starts.insert(at, start)
        chosen.insert(at, (start, end, kind))
    if not chosen:
        return text, []
    pieces: list[str] = []
    pos = 0
    counts: Counter[str] = Counter()
    for start, end, kind in chosen:
        pieces.append(text[pos:start])
        pieces.append(replacement(kind))
        counts[kind] += 1
        pos = end
    pieces.append(text[pos:])
    return "".join(pieces), [Finding(kind, n) for kind, n in sorted(counts.items())]
