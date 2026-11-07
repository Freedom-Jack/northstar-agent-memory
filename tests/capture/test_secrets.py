"""Secret scrubbing (MEMORY-ARCHITECTURE §2.2). Every token is built at test time, of the right shape and invented."""

from __future__ import annotations

import random
import string

import pytest

from northstar_agent_memory.capture.secrets import Finding, replacement, scrub, tally

ALNUM = string.ascii_letters + string.digits


def fake(prefix: str, n: int, chars: str = ALNUM, seed: int = 7) -> str:
    """prefix + n random characters, forced to hold a letter of each case and a digit so it reads as a key."""
    rnd = random.Random(seed)
    body = [rnd.choice(chars) for _ in range(n)]
    if chars == ALNUM and n >= 3:
        body[0], body[1], body[2] = "a", "Q", "7"
    return prefix + "".join(body)


def kinds(findings: list[Finding]) -> dict[str, int]:
    return {f.kind: f.count for f in findings}


def check(text: str, secret: str, kind: str) -> str:
    out, findings = scrub(text)
    assert secret not in out
    assert replacement(kind) in out
    assert kinds(findings) == {kind: 1}
    return out


# --- vendors ---------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("secret", "kind"),
    [
        (fake("sk-ant-api03-", 40, ALNUM + "-_"), "anthropic_api_key"),
        (fake("sk-", 48), "openai_api_key"),
        (fake("sk-proj-", 40, ALNUM + "-_"), "openai_api_key"),
        (fake("ghp_", 36), "github_token"),
        (fake("gho_", 36), "github_token"),
        (fake("github_pat_", 40, ALNUM + "_"), "github_token"),
        (fake("AKIA", 16, string.ascii_uppercase + string.digits), "aws_access_key"),
        (fake("AIza", 35, ALNUM + "-_"), "google_api_key"),
        (fake("xoxb-", 30, string.digits + "-"), "slack_token"),
        (fake("sk_live_", 24), "stripe_key"),
        (fake("npm_", 36), "npm_token"),
        (fake("hf_", 34), "huggingface_token"),
    ],
)
def test_vendor_keys_and_tokens_are_replaced(secret, kind):
    out = check(f"here it is: {secret} and then more words", secret, kind)
    assert out == f"here it is: {replacement(kind)} and then more words"


def test_a_vendor_key_inside_an_assignment_keeps_the_assignment():
    secret = fake("sk-ant-api03-", 40, ALNUM + "-_")
    out = check(f'client = Anthropic(api_key="{secret}")', secret, "anthropic_api_key")
    assert out == 'client = Anthropic(api_key="[secret removed: anthropic_api_key]")'


def test_a_private_key_block_is_replaced_whole():
    body = "\n".join(fake("", 64, ALNUM + "+/", seed=i) for i in range(5))
    block = f"-----BEGIN OPENSSH PRIVATE KEY-----\n{body}\n-----END OPENSSH PRIVATE KEY-----"
    out = check(f"my key:\n{block}\nthanks", block, "private_key")
    assert out == "my key:\n[secret removed: private_key]\nthanks"
    assert body.splitlines()[2] not in out


def test_a_truncated_private_key_block_is_replaced_too():
    body = "\n".join(fake("", 64, ALNUM + "+/", seed=i) for i in range(3))
    out, findings = scrub(f"-----BEGIN RSA PRIVATE KEY-----\n{body}\n\nafter")
    assert kinds(findings) == {"private_key": 1}
    assert body.splitlines()[0] not in out
    assert out.endswith("after")


def test_a_jwt_is_replaced():
    jwt = f"eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJkZW1vIn0.{fake('', 43, ALNUM + '-_')}"
    check(f"Cookie session={jwt}; path=/", jwt, "jwt")


def test_an_aws_access_key_and_its_secret_are_both_replaced():
    key_id = fake("AKIA", 16, string.ascii_uppercase + string.digits)
    secret = fake("", 40, ALNUM + "/+", seed=3)
    out, findings = scrub(f"[default]\n{key_id}\n{secret}\n")
    assert key_id not in out and secret not in out
    assert kinds(findings) == {"aws_access_key": 1, "aws_secret_key": 1}


def test_an_aws_secret_named_by_its_key_is_replaced():
    secret = fake("", 40, ALNUM + "/+", seed=4)
    out = check(f"aws_secret_access_key = {secret}", secret, "secret")
    assert out.startswith("aws_secret_access_key = ")


# --- URLs and headers ------------------------------------------------------------------------------------------


def test_a_password_in_a_url_is_replaced_but_not_the_rest_of_the_url():
    out = check("clone https://robin:hunter2pw@git.example.org/robin/dash.git now", "hunter2pw", "url_password")
    assert out == "clone https://robin:[secret removed: url_password]@git.example.org/robin/dash.git now"


def test_a_token_in_a_query_string_is_replaced():
    secret = fake("", 28)
    out = check(f"GET https://api.example.org/v1/items?page=2&access_token={secret}&limit=5", secret, "url_token")
    assert "page=2" in out and "limit=5" in out


def test_an_authorization_header_and_a_bearer_token_are_replaced():
    secret = fake("", 30)
    check(f"curl -H 'Authorization: Bearer {secret}' https://x.example", secret, "auth_header")
    secret = fake("", 32, seed=9)
    check(f"the header was Bearer {secret} in the log", secret, "bearer_token")


def test_basic_auth_credentials_in_a_header_are_replaced():
    out, findings = scrub("Authorization: Basic dXNlcjpoYXJkcGFzc3dvcmQ=")
    assert "dXNlcjpoYXJkcGFzc3dvcmQ" not in out
    assert kinds(findings) == {"auth_header": 1}


# --- key = value -----------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "secret", "kind"),
    [
        ("password=hunter2xyz", "hunter2xyz", "password"),
        ("password: Tr0ub4dor&3", "Tr0ub4dor&3", "password"),
        ('DB_PASSWORD = "correct horse"', "correct horse", "password"),
        ("token: abcDEF123456ghi", "abcDEF123456ghi", "token"),
        ("the password: hunter2. Then", "hunter2", "password"),
        ('{"api_key": "abcd1234efgh5678", "name": "x"}', "abcd1234efgh5678", "api_key"),
        ("client_secret: 'q8Zr2Lm4Vb7n'", "q8Zr2Lm4Vb7n", "secret"),
        ("--api-key=Zx81kQ2m7Rt9Wb3", "Zx81kQ2m7Rt9Wb3", "api_key"),
        ("export SESSION_SECRET=plainlongsecretvalue", "plainlongsecretvalue", "secret"),
    ],
)
def test_pairs_whose_key_names_a_secret_lose_the_value_and_keep_the_key(text, secret, kind):
    out = check(text, secret, kind)
    key = text.split(secret)[0]
    assert out.startswith(key)


def test_env_style_lines_are_scrubbed_line_by_line_whatever_the_value():
    text = "NAME=dash\nSTRIPE_API_KEY=plainvalue\nDEBUG=1\nDATABASE_PASSWORD=abc\nTOKEN=\nAPI_TOKEN=${FROM_VAULT}\n"
    out, findings = scrub(text)
    assert out == (
        "NAME=dash\nSTRIPE_API_KEY=[secret removed: api_key]\nDEBUG=1\nDATABASE_PASSWORD=[secret removed: password]\n"
        "TOKEN=\nAPI_TOKEN=${FROM_VAULT}\n"
    )
    assert kinds(findings) == {"api_key": 1, "password": 1}


def test_a_trailing_comment_on_an_env_line_is_kept():
    out, findings = scrub("STRIPE_API_KEY=plainvalue123  # rotate monthly\n")
    assert out == "STRIPE_API_KEY=[secret removed: api_key]  # rotate monthly\n"
    assert kinds(findings) == {"api_key": 1}


def test_a_long_random_string_next_to_a_secret_word_is_replaced():
    secret = fake("", 40, ALNUM, seed=11)
    out = check(f"my api key is {secret} - please keep it", secret, "high_entropy")
    assert out == "my api key is [secret removed: high_entropy] - please keep it"


def test_a_hex_string_next_to_a_secret_word_is_replaced():
    secret = "5d41402abc4b2a76b9719d911017c592"
    check(f"the secret is {secret}", secret, "high_entropy")


def test_findings_count_each_kind_and_never_hold_the_secret():
    a, b, c = fake("ghp_", 36, seed=1), fake("ghp_", 36, seed=2), fake("sk-ant-api03-", 40, ALNUM + "-_")
    out, findings = scrub(f"{a} {b} {c}")
    assert kinds(findings) == {"github_token": 2, "anthropic_api_key": 1}
    for f in findings:
        assert set(Finding.__slots__) == {"kind", "count"}
        assert all(secret not in repr(f) for secret in (a, b, c))
    assert tally(findings)["github_token"] == 2
    running = tally(findings)
    tally(findings, running)
    assert running["github_token"] == 4


# --- what must not be touched ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "01HZX3K8Q9V5T2M7N4P6R8S0AB",
        "the token 01HZX3K8Q9V5T2M7N4P6R8S0AB is an event id",
        "commit 3f786850e387550fdab836ed7e6dc881de23001b fixed it",
        "the token hash 3f786850e387550fdab836ed7e6dc881de23001b is stored",
        "sha256 of the secret: 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        "token 123e4567-e89b-12d3-a456-426614174000 belongs to the request",
        "git log: 3f78685 3f78685e387550fdab836ed7e6dc881de23001b Merge branch 'main'",
        "the token limit is 8000 tokens; max_tokens=4096 and token_count: 5000",
        "tokenizer settings, secretary notes, passwordless login, authority",
        "password = getpass.getpass()",
        "password=password and token=self.token and secret = os.environ['SECRET']",
        "password: required",
        "Use a strong password: at least 12 characters",
        "set the password to something long, token: <your token here>",
        "API_KEY=<your-key> and token: ${TOKEN}",
        "def login(user, password): return check(user, password)",
        "sk-learn is a library; risk-assessment-document-final-version-two",
        "password_policy: strict, token_type: bearer, secret_name: db-credentials",
        'password = "Enter your password:"',
        "see the secret-management-service-configuration-guide-v2 for the token rotation plan",
        "version: 2.1.309, date: 2026-11-04, build 20261104T101500Z",
        "CHARS_PER_TOKEN = 3.5  # errs high: English text averages about 4 characters per token",
        'API_TOKEN = os.environ["API_TOKEN"]\nDB_PASSWORD = settings.db_password\nSECRET_KEY = load_secret_key()',
        "SESSION_TOKEN = my_token_variable",
    ],
)
def test_ordinary_text_and_identifiers_are_left_alone(text):
    out, findings = scrub(text)
    assert out == text
    assert findings == []


def test_base64_images_in_data_urls_are_not_secrets_even_beside_a_secret_word():
    payload = fake("", 120, ALNUM + "+/", seed=5)
    text = f'token image: <img src="data:image/png;base64,{payload}=="> and the secret: data:image/png;base64,{payload}'
    out, findings = scrub(text)
    assert f"data:image/png;base64,{payload}==" in out
    assert findings == []


def test_text_without_secrets_comes_back_unchanged():
    text = "We decided to keep readings for 7 days.\n\n```python\nx = 1\n```"
    assert scrub(text) == (text, [])
    assert scrub("") == ("", [])


def test_scrubbing_twice_changes_nothing():
    secrets = [
        fake("sk-ant-api03-", 40, ALNUM + "-_"), fake("ghp_", 36), "password=hunter2xyz", "NAME=a\nAPI_KEY=zzzzzzzz",
        f"postgres://a:{fake('', 12)}@h/db", f"Authorization: Bearer {fake('', 30)}",
    ]
    once, _ = scrub("\n".join(secrets))
    again, findings = scrub(once)
    assert again == once and findings == []


def test_a_secret_is_replaced_wherever_it_sits_in_a_long_text():
    secret = fake("ghp_", 36)
    text = ("filler words. " * 500) + secret + (" more filler. " * 500)
    out, findings = scrub(text)
    assert secret not in out and kinds(findings) == {"github_token": 1}
    assert len(out) < len(text)


def test_password_stated_in_prose_is_removed():
    text, found = scrub("my password is Tr0ub4dor&3xyz, ok?")
    assert "Tr0ub4dor" not in text and [f.kind for f in found] == ["password"]


def test_password_is_followed_by_a_plain_word_is_left_alone():
    text, found = scrub("the password is required here, and the password is stored hashed")
    assert found == [] and text.startswith("the password is required")


# --- time: a long run of one character, and many secrets, cost time in proportion to the text ----------------------

import time


def best_of(text: str, runs: int = 3) -> float:
    times = []
    for _ in range(runs):
        start = time.perf_counter()
        scrub(text)
        times.append(time.perf_counter() - start)
    return min(times)


@pytest.mark.parametrize("char", ["a", "A", "_", "0", "-", ".", "=", ":", " ", "\n", "x", "/", "+"])
def test_300_kb_of_one_character_scrubs_well_under_a_tenth_of_a_second(char):
    # The key of `key = value` was tried from every character of a long run (up to 60 steps each): 0.4 s for "a" * 300_000.
    assert best_of(char * 300_000) < 0.1, char


@pytest.mark.parametrize("unit", ["a.", "a-", "1a", "a=", "a:", "1:", "a b ", "token ", "password=", "-a", "=a"])
def test_300_kb_of_a_short_repeated_unit_scrubs_in_well_under_a_second(unit):
    assert best_of((unit * (300_000 // len(unit) + 1))[:300_000]) < 0.25, unit


def test_a_run_after_a_secret_word_is_as_cheap():
    for head in ("password=", "token ", "Authorization: ", "?token=", "sk-ant-", "https://u:", "-----BEGIN PRIVATE KEY-----\n"):
        assert best_of(head + "a" * 300_000) < 0.1, head


def test_thousands_of_secrets_in_one_text_cost_time_in_proportion():
    token = fake("ghp_", 36)
    lines = [f"password=Xk{n:05d}fjs0Zq1" if n % 2 else token for n in range(14_000)]
    text = "\n".join(lines)  # every one is a candidate that has to be checked against the ones already chosen (it was 1.4 s)
    out, findings = scrub(text)
    assert sum(f.count for f in findings) == 14_000 and token not in out and "Xk00001" not in out
    assert best_of(text) < 0.5


# --- the same answers as before for the key / value rules the speed-up touched ------------------------------------


def test_a_key_is_the_last_name_run_before_the_operator_so_long_and_odd_names_still_count():
    secret = "Hunter2hunter2X9"
    assert scrub(f"--password={secret}")[0] == "--password=[secret removed: password]"
    assert scrub(f"my.api-key = '{secret}'")[0] == "my.api-key = '[secret removed: api_key]'"
    long_name = "x" * 70 + "_password"  # longer than 61: the key is its last 61 characters, which still name a password
    assert scrub(f"{long_name}={secret}")[0] == f"{long_name}=[secret removed: password]"
    assert scrub(f"1234:{'a' * 5}_token: {secret}")[0] == "1234:aaaaa_token: [secret removed: token]"


def test_a_colon_before_the_key_does_not_hide_it_from_the_scan():
    secret = "Hunter2hunter2X9"
    assert scrub(f"1:aapi_keyapi_keymy.api-key={secret}\t")[0] == "1:aapi_keyapi_keymy.api-key=[secret removed: api_key]\t"
    assert scrub(f")-=>--password={secret}")[0] == ")-=>--password=[secret removed: password]"


def test_a_name_with_no_letter_to_start_a_key_finds_nothing_and_costs_nothing():
    assert scrub("1234567=1111111111111111") == ("1234567=1111111111111111", [])
    assert best_of("1:" * 150_000) < 0.2
