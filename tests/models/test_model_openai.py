import openai
import pytest

import model_fakes as f
from northstar_agent_memory.models.budget import billed_result
from northstar_agent_memory.models.openai_adapter import OpenAIAdapter
from northstar_agent_memory.models.port import ModelError, ModelRefused, ModelUnavailable, NoCredentials


@pytest.fixture
def oconfig(config):
    return f.with_openai(config)


def adapter(config, client):
    return OpenAIAdapter(config, client=client)


def test_request_shape(oconfig):
    client = f.FakeOpenAI()
    result = adapter(oconfig, client).complete(f.make_req(family="openai", schema=f.SCHEMA, effort="medium", max_tokens=900))
    kw = client.calls[0]
    assert kw["model"] == "gpt-test"
    assert kw["instructions"] == "Be brief."
    assert kw["input"] == [{"role": "user", "content": "hello"}]
    assert kw["max_output_tokens"] == 900
    assert kw["reasoning"] == {"effort": "medium"}
    fmt = kw["text"]["format"]
    assert fmt["type"] == "json_schema" and fmt["strict"] is True and fmt["schema"] == f.SCHEMA and fmt["name"]
    for banned in ("temperature", "top_p"):
        assert banned not in kw
    assert result.parsed == {"verdict": "ok"} and result.served_model == "gpt-test-2026"
    assert result.stop_reason == "end_turn"


@pytest.mark.parametrize(("effort", "sent"), [("xhigh", "high"), ("max", "high"), ("low", "low")])
def test_effort_mapping(oconfig, effort, sent):
    client = f.FakeOpenAI(f.o_response(text="x"))
    adapter(oconfig, client).complete(f.make_req(family="openai", effort=effort))
    assert client.calls[0]["reasoning"] == {"effort": sent}


def test_no_effort_no_reasoning_and_no_schema_no_text_format(oconfig):
    client = f.FakeOpenAI(f.o_response(text="plain"))
    result = adapter(oconfig, client).complete(f.make_req(family="openai"))
    assert "reasoning" not in client.calls[0] and "text" not in client.calls[0]
    assert result.text == "plain" and result.parsed is None


def test_cost_uses_cached_split(oconfig):
    client = f.FakeOpenAI(f.o_response(input_tokens=1_000_000, cached=400_000, output_tokens=100_000))
    result = adapter(oconfig, client).complete(f.make_req(family="openai"))
    assert result.usage.input_tokens == 600_000 and result.usage.cache_read_tokens == 400_000
    assert result.cost_usd == pytest.approx(0.6 + 0.04 + 0.4)


def test_refusal(oconfig):
    client = f.FakeOpenAI(f.o_response(refusal="I can't help with that."))
    with pytest.raises(ModelRefused) as info:
        adapter(oconfig, client).complete(f.make_req(family="openai", schema=f.SCHEMA))
    assert billed_result(info.value).stop_reason == "refusal"


def test_incomplete_schema_call_is_an_error(oconfig):
    client = f.FakeOpenAI(f.o_response(text='{"ver', status="incomplete", reason="max_output_tokens"))
    with pytest.raises(ModelError, match="cut off"):
        adapter(oconfig, client).complete(f.make_req(family="openai", schema=f.SCHEMA))


def test_failed_response(oconfig):
    client = f.FakeOpenAI(f.o_response(text="", status="failed", error=type("E", (), {"message": "server_error"})()))
    with pytest.raises(ModelError, match="server_error"):
        adapter(oconfig, client).complete(f.make_req(family="openai"))


def test_empty_openai_role_refuses_cleanly(config):
    config["models"]["openai"]["judge"] = ""  # the shipped config sets every role
    client = f.FakeOpenAI()
    with pytest.raises(ModelError, match="northstar models check"):
        adapter(config, client).complete(f.make_req(family="openai"))
    assert client.calls == []


def test_model_without_price_refuses(config):
    client = f.FakeOpenAI()
    with pytest.raises(ModelError, match="no price"):
        adapter(config, client).complete(f.make_req(family="openai", model="gpt-unpriced"))
    assert client.calls == []


def test_wrong_family_refused(oconfig):
    with pytest.raises(ModelError):
        adapter(oconfig, f.FakeOpenAI()).complete(f.make_req(family="anthropic"))


def test_sdk_errors(oconfig):
    err = f.http_error(openai.RateLimitError, 429, header="x-request-id", rid="req_55")
    with pytest.raises(ModelError, match="rate limit") as info:
        adapter(oconfig, f.FakeOpenAI(error=err)).complete(f.make_req(family="openai"))
    assert "req_55" in str(info.value)


def test_no_key_raises_no_credentials(oconfig):
    with pytest.raises(NoCredentials):
        OpenAIAdapter(oconfig, None)


def test_failed_response_without_usage_is_a_model_error(oconfig):
    from types import SimpleNamespace as NS

    response = f.o_response(status="failed", error=NS(message="boom"))
    response.usage = None
    with pytest.raises(ModelError, match="boom"):
        OpenAIAdapter(oconfig, client=f.FakeOpenAI(response)).complete(f.make_req(family="openai"))


def test_shipped_config_sets_every_openai_role_and_price(config):
    from northstar_agent_memory.models.budget import require_model, require_price

    for role in ("answerer", "judge", "worker", "worker_small", "checker", "sim_user"):
        model = require_model(config, f.make_req(family="openai", role=role))
        assert require_price(config, model)["output"] > 0


def test_cache_flag_and_fallback_flag_send_nothing_to_openai(oconfig):
    client = f.FakeOpenAI()
    adapter(oconfig, client).complete(f.make_req(family="openai", cache=True, allow_fallback=False))
    assert set(client.calls[0]) == {"model", "input", "max_output_tokens", "store", "instructions"}


@pytest.mark.parametrize(("cls", "status"), [(openai.AuthenticationError, 401), (openai.PermissionDeniedError, 403)])
def test_rejected_credentials_raise_no_credentials(oconfig, cls, status):
    err = f.http_error(cls, status, header="x-request-id", rid="req_8")
    with pytest.raises(NoCredentials, match="req_8"):
        adapter(oconfig, f.FakeOpenAI(error=err)).complete(f.make_req(family="openai"))


def test_unknown_model_raises_model_unavailable(oconfig):
    err = f.http_error(openai.NotFoundError, 404, header="x-request-id", rid="req_3")
    with pytest.raises(ModelUnavailable, match="not found.*req_3"):
        adapter(oconfig, f.FakeOpenAI(error=err)).complete(f.make_req(family="openai"))


def test_long_prompt_uses_long_cache_read_price(config):
    # gpt-6.1-sol: over 272K prompt tokens bills 4 in, 15 out and 0.20 for cached input
    client = f.FakeOpenAI(f.o_response(input_tokens=500_000, cached=400_000, output_tokens=100_000))
    result = adapter(config, client).complete(f.make_req(family="openai"))  # judge is gpt-6.1-sol
    assert result.cost_usd == pytest.approx(100_000 * 4 / 1e6 + 100_000 * 15 / 1e6 + 400_000 * 0.20 / 1e6)
    short = f.FakeOpenAI(f.o_response(input_tokens=200_000, cached=100_000, output_tokens=100_000))
    result = adapter(config, short).complete(f.make_req(family="openai"))
    assert result.cost_usd == pytest.approx(100_000 * 2 / 1e6 + 100_000 * 10 / 1e6 + 100_000 * 0.10 / 1e6)
