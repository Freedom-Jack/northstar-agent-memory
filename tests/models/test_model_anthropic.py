from types import SimpleNamespace as NS

import anthropic
import pytest

import model_fakes as f
from northstar_agent_memory.models.anthropic_adapter import FALLBACK_BETA, AnthropicAdapter
from northstar_agent_memory.models.budget import billed_result
from northstar_agent_memory.models.port import (
    ModelError,
    ModelRefused,
    ModelUnavailable,
    NoCredentials,
    SchemaNotStrict,
)


def adapter(config, client):
    return AnthropicAdapter(config, client=client)


def test_request_shape_opus_uses_beta_with_fallbacks(config):
    client = f.FakeAnthropic()
    adapter(config, client).complete(f.make_req(schema=f.SCHEMA, effort="high", max_tokens=2000, cache=True))
    route, kw = client.calls[0]
    assert route == "beta"
    assert kw["betas"] == [FALLBACK_BETA] and kw["fallbacks"] == "default"
    assert kw["model"] == "claude-opus-5-5"
    assert kw["output_config"] == {"format": {"type": "json_schema", "schema": f.SCHEMA}, "effort": "high"}
    assert kw["cache_control"] == {"type": "ephemeral"}
    assert kw["system"] == "Be brief." and kw["max_tokens"] == 2000
    for banned in ("temperature", "top_p", "top_k", "thinking", "tools", "tool_choice"):
        assert banned not in kw


def test_sonnet_also_gets_fallbacks(config):
    client = f.FakeAnthropic(f.a_response(model="claude-sonnet-5-5"))
    adapter(config, client).complete(f.make_req(model="claude-sonnet-5-5"))
    assert client.calls[0][0] == "beta" and client.calls[0][1]["fallbacks"] == "default"


def test_haiku_uses_plain_messages_without_fallbacks(config):
    client = f.FakeAnthropic(f.a_response(text="hi", model="claude-haiku-5-5"))
    result = adapter(config, client).complete(f.make_req(role="worker_small"))
    route, kw = client.calls[0]
    assert route == "messages"
    assert "fallbacks" not in kw and "betas" not in kw
    assert "output_config" not in kw
    assert result.text == "hi" and result.parsed is None


def test_structured_output_parsed_and_thinking_blocks_skipped(config):
    content = [NS(type="thinking", thinking="hmm"), NS(type="text", text='{"verdict": "yes"}')]
    client = f.FakeAnthropic(f.a_response(content=content))
    result = adapter(config, client).complete(f.make_req(schema=f.SCHEMA))
    assert result.parsed == {"verdict": "yes"}
    assert result.request_id == "req_abc"
    assert result.family == "anthropic" and result.model == result.served_model == "claude-opus-5-5"
    assert not result.from_record


def test_invalid_json_raises_with_billed_result(config):
    client = f.FakeAnthropic(f.a_response(text="not json"))
    with pytest.raises(ModelError, match="not valid JSON") as info:
        adapter(config, client).complete(f.make_req(schema=f.SCHEMA))
    assert billed_result(info.value).cost_usd > 0


def test_cost_math_with_cache(config):
    usage = f.a_usage(i=1_000_000, o=100_000, cr=2_000_000, cw=400_000)
    client = f.FakeAnthropic(f.a_response(usage=usage))
    result = adapter(config, client).complete(f.make_req())
    # opus: 4 in, 20 out, 0.20 cache read, cache write 4 * 1.25 = 5
    assert result.cost_usd == pytest.approx(4 + 2 + 0.4 + 2.0)
    assert (result.usage.input_tokens, result.usage.cache_read_tokens, result.usage.cache_write_tokens) == (
        1_000_000,
        2_000_000,
        400_000,
    )


def test_haiku_short_and_long_prices(config):
    short = f.FakeAnthropic(f.a_response(text="x", model="claude-haiku-5-5", usage=f.a_usage(i=90_000, o=1000)))
    r = adapter(config, short).complete(f.make_req(model="claude-haiku-5-5"))
    assert r.cost_usd == pytest.approx(90_000 * 0.10 / 1e6 + 1000 * 0.50 / 1e6)
    long = f.FakeAnthropic(f.a_response(text="x", model="claude-haiku-5-5", usage=f.a_usage(i=150_000, o=1000)))
    r = adapter(config, long).complete(f.make_req(model="claude-haiku-5-5"))
    assert r.cost_usd == pytest.approx(150_000 * 0.50 / 1e6 + 1000 * 2.50 / 1e6)


def test_long_threshold_counts_cached_tokens(config):
    usage = f.a_usage(i=10_000, o=0, cr=95_000)
    client = f.FakeAnthropic(f.a_response(text="x", model="claude-haiku-5-5", usage=usage))
    r = adapter(config, client).complete(f.make_req(model="claude-haiku-5-5"))
    # prompt of 105K tokens is long: input at 0.50, cache reads keep their 10% ratio (0.05)
    assert r.cost_usd == pytest.approx(10_000 * 0.50 / 1e6 + 95_000 * 0.05 / 1e6)


def test_refusal_raises_before_content_is_read(config):
    details = NS(category="cyber")
    response = f.a_response(content=[NS(type="text", text="partial")], stop="refusal", details=details)
    with pytest.raises(ModelRefused, match="cyber") as info:
        adapter(config, f.FakeAnthropic(response)).complete(f.make_req())
    assert billed_result(info.value).stop_reason == "refusal"


def test_max_tokens_on_schema_call_is_an_error(config):
    response = f.a_response(text='{"verdict": "tru', stop="max_tokens")
    with pytest.raises(ModelError, match="cut off"):
        adapter(config, f.FakeAnthropic(response)).complete(f.make_req(schema=f.SCHEMA))


def test_max_tokens_on_text_call_returns_text(config):
    result = adapter(config, f.FakeAnthropic(f.a_response(text="half", stop="max_tokens"))).complete(f.make_req())
    assert result.text == "half" and result.stop_reason == "max_tokens"


def test_max_tokens_above_cap_rejected_without_calling(config):
    client = f.FakeAnthropic()
    with pytest.raises(ModelError, match="16000"):
        adapter(config, client).complete(f.make_req(max_tokens=20_000))
    assert client.calls == []


def test_missing_model_and_price(config):
    client = f.FakeAnthropic()
    config["models"]["anthropic"]["judge"] = ""
    with pytest.raises(ModelError, match="northstar models check"):
        adapter(config, client).complete(f.make_req())
    with pytest.raises(ModelError, match="no price"):
        adapter(config, client).complete(f.make_req(model="claude-unpriced"))
    assert client.calls == []


def test_wrong_family_and_non_strict_schema(config):
    client = f.FakeAnthropic()
    with pytest.raises(ModelError):
        adapter(config, client).complete(f.make_req(family="openai"))
    with pytest.raises(SchemaNotStrict):
        adapter(config, client).complete(f.make_req(schema={"type": "object", "properties": {"a": {"type": "string"}}}))
    assert client.calls == []


def test_fallback_is_priced_per_attempt(config):
    iterations = [
        NS(type="message", model="claude-opus-5-5", input_tokens=1_000_000, output_tokens=0,
           cache_read_input_tokens=0, cache_creation_input_tokens=0),
        NS(type="fallback_message", model="claude-sonnet-5-5", input_tokens=1_000_000, output_tokens=100_000,
           cache_read_input_tokens=0, cache_creation_input_tokens=0),
    ]
    content = [NS(type="text", text="declined"), NS(type="fallback"), NS(type="text", text="answer")]
    response = f.a_response(content=content, model="claude-sonnet-5-5",
                            usage=f.a_usage(i=1_000_000, o=100_000, iterations=iterations))
    result = adapter(config, f.FakeAnthropic(response)).complete(f.make_req())
    assert result.text == "answer"
    assert result.served_model == "claude-sonnet-5-5" and result.model == "claude-opus-5-5"
    assert result.cost_usd == pytest.approx(4.0 + 2.0 + 1.0)


@pytest.mark.parametrize(
    ("cls", "status", "text"),
    [
        (anthropic.RateLimitError, 429, "rate limit"),
        (anthropic.InternalServerError, 500, "error 500"),
    ],
)
def test_sdk_errors_become_model_errors_with_request_id(config, cls, status, text):
    client = f.FakeAnthropic(error=f.http_error(cls, status, rid="req_77"))
    with pytest.raises(ModelError, match=text) as info:
        adapter(config, client).complete(f.make_req())
    assert "req_77" in str(info.value)


def test_connection_error(config):
    import httpx2

    err = anthropic.APIConnectionError(request=httpx2.Request("POST", "https://api.test"))
    with pytest.raises(ModelError, match="could not reach"):
        adapter(config, f.FakeAnthropic(error=err)).complete(f.make_req())


def test_no_credentials_raises_no_credentials(monkeypatch, config):
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    monkeypatch.setenv("HOME", "/nonexistent-home")  # no SDK profile or credentials file
    with pytest.raises(NoCredentials, match="northstar-anthropic"):
        AnthropicAdapter(config)


def test_caching_is_sent_only_when_asked(config):
    client = f.FakeAnthropic()
    adapter(config, client).complete(f.make_req())
    adapter(config, client).complete(f.make_req(cache=True))
    adapter(config, client).complete(f.make_req(cache=True, model="claude-haiku-5-5"))
    (_, plain), (_, cached), (_, haiku) = client.calls
    assert "cache_control" not in plain
    assert cached["cache_control"] == {"type": "ephemeral"} and haiku["cache_control"] == {"type": "ephemeral"}


def test_fallback_off_uses_plain_messages_for_a_fallback_model(config):
    client = f.FakeAnthropic()
    adapter(config, client).complete(f.make_req(allow_fallback=False, schema=f.SCHEMA))
    route, kw = client.calls[0]
    assert route == "messages"
    assert "betas" not in kw and "fallbacks" not in kw
    assert kw["model"] == "claude-opus-5-5"


def test_fallback_off_refusal_raises_model_refused_and_is_billed(config):
    response = f.a_response(content=[NS(type="text", text="")], stop="refusal", details=NS(category="cyber"))
    client = f.FakeAnthropic(response)
    with pytest.raises(ModelRefused) as info:
        adapter(config, client).complete(f.make_req(allow_fallback=False))
    assert client.calls[0][0] == "messages"
    assert billed_result(info.value).cost_usd > 0


def test_fallback_default_is_on(config):
    assert f.make_req().allow_fallback is True and f.make_req().cache is False


@pytest.mark.parametrize(("cls", "status"), [(anthropic.AuthenticationError, 401), (anthropic.PermissionDeniedError, 403)])
def test_rejected_credentials_raise_no_credentials(config, cls, status):
    client = f.FakeAnthropic(error=f.http_error(cls, status, rid="req_9"))
    with pytest.raises(NoCredentials, match="req_9"):
        adapter(config, client).complete(f.make_req())


def test_unknown_model_raises_model_unavailable(config):
    client = f.FakeAnthropic(error=f.http_error(anthropic.NotFoundError, 404, rid="req_4"))
    with pytest.raises(ModelUnavailable, match="not found.*req_4") as info:
        adapter(config, client).complete(f.make_req())
    assert isinstance(info.value, ModelError)
