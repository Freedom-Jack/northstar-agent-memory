"""GPT models through the OpenAI Responses API, behind the model port (DESIGN §1.4).

One non-streaming call per request. The system text goes in `instructions`, structured
output in `text.format` (strict), and effort in `reasoning`; no sampling parameters
are sent. OpenAI reports cached tokens inside `input_tokens`, so uncached input is
the difference. Reasoning tokens are already part of `output_tokens`. OpenAI caches
long prompts by itself, so `ModelRequest.cache` sends nothing here. A request for a
role with no model, or a model with no price, raises ModelError instead of guessing.

A refusal raises ModelRefused, and a truncated or invalid structured output raises
ModelError. Both carry the billed result (budget.attach). A rejected key (401, 403)
raises NoCredentials, and a model the key cannot reach (404) raises ModelUnavailable,
which is fatal for a run.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

import openai

from northstar_agent_memory.models.budget import attach, cost_usd, require_model, require_price
from northstar_agent_memory.models.port import (
    ModelError,
    ModelRefused,
    ModelRequest,
    ModelResult,
    ModelUnavailable,
    NoCredentials,
    Usage,
)
from northstar_agent_memory.models.schema import assert_strict

# OpenAI's reasoning efforts stop at "high" for the models this harness uses.
EFFORTS = {"low": "low", "medium": "medium", "high": "high", "xhigh": "high", "max": "high"}


class OpenAIAdapter:
    """ModelPort for the "openai" family. `client` replaces the SDK client in tests."""

    def __init__(self, config: dict, api_key: str | None = None, *, client: Any = None) -> None:
        self.config = config
        self.client = client if client is not None else _make_client(api_key)

    def complete(self, req: ModelRequest) -> ModelResult:
        if req.family != "openai":
            raise ModelError(f"the OpenAI adapter got a {req.family!r} request")
        model = require_model(self.config, req)
        price = require_price(self.config, model)
        params = _params(req, model)
        started = time.monotonic()
        try:
            response = self.client.responses.create(**params)
        except openai.NotFoundError as err:
            raise ModelUnavailable(f"OpenAI API: model {model!r} not found (request {err.request_id})") from err
        except (openai.AuthenticationError, openai.PermissionDeniedError) as err:
            raise NoCredentials(
                f"OpenAI API rejected the credentials ({err.status_code}, request {err.request_id})"
            ) from err
        except openai.RateLimitError as err:
            raise ModelError(f"OpenAI API rate limit, after the SDK's retries (request {err.request_id})") from err
        except openai.APIStatusError as err:
            raise ModelError(f"OpenAI API error {err.status_code} (request {err.request_id}): {err.message}") from err
        except openai.APIConnectionError as err:
            raise ModelError(f"could not reach the OpenAI API: {err}") from err
        except openai.OpenAIError as err:
            raise ModelError(f"OpenAI SDK error: {err}") from err
        return _result(req, model, price, response, time.monotonic() - started)


def _make_client(api_key: str | None) -> openai.OpenAI:
    if not api_key:
        raise NoCredentials(
            "no OpenAI API key: store one in the Keychain as service 'northstar-openai' or set OPENAI_API_KEY"
        )
    try:
        return openai.OpenAI(api_key=api_key)
    except openai.OpenAIError as err:
        raise NoCredentials(f"OpenAI credentials could not be loaded: {err}") from err


def _params(req: ModelRequest, model: str) -> dict:
    params: dict[str, Any] = {
        "model": model,
        "input": [{"role": m["role"], "content": m["content"]} for m in req.messages],
        "max_output_tokens": req.max_tokens,
        "store": False,
    }
    if req.system:
        params["instructions"] = req.system
    if req.effort is not None:
        if req.effort not in EFFORTS:
            raise ModelError(f"unknown effort {req.effort!r}")
        params["reasoning"] = {"effort": EFFORTS[req.effort]}
    if req.schema is not None:
        assert_strict(req.schema)
        name = re.sub(r"[^A-Za-z0-9_-]", "_", str(req.schema.get("title") or "response"))[:64]
        params["text"] = {"format": {"type": "json_schema", "name": name, "schema": req.schema, "strict": True}}
    return params


def _result(req: ModelRequest, model: str, price: dict, response: Any, latency: float) -> ModelResult:
    usage = _usage(response.usage)
    refusal = _refusal(response)
    incomplete = response.status == "incomplete"
    reason = response.incomplete_details.reason if incomplete and response.incomplete_details else None
    if refusal is not None:
        stop_reason = "refusal"
    elif reason == "max_output_tokens":
        stop_reason = "max_tokens"
    else:
        stop_reason = "end_turn" if response.status == "completed" else response.status
    result = ModelResult(
        text="",
        parsed=None,
        usage=usage,
        cost_usd=cost_usd(price, usage),
        latency_s=latency,
        family="openai",
        model=model,
        served_model=response.model or model,
        stop_reason=stop_reason,
        request_id=getattr(response, "_request_id", None) or getattr(response, "id", None),
    )
    if refusal is not None:
        raise attach(ModelRefused(f"{result.served_model} refused the request"), result)
    if response.status == "failed":
        message = response.error.message if response.error else "no detail"
        raise attach(ModelError(f"OpenAI response failed: {message}"), result)
    result.text = response.output_text
    if req.schema is None:
        return result
    if stop_reason == "max_tokens":
        raise attach(ModelError(f"structured output cut off at max_tokens={req.max_tokens}"), result)
    try:
        result.parsed = json.loads(result.text)
    except json.JSONDecodeError as err:
        raise attach(ModelError(f"structured output is not valid JSON (status {response.status})"), result) from err
    return result


def _refusal(response: Any) -> str | None:
    for item in response.output:
        if item.type != "message":
            continue
        for part in item.content:
            if part.type == "refusal":
                return part.refusal
    return None


def _usage(raw: Any) -> Usage:
    if raw is None:  # a failed response may carry no usage
        return Usage()
    cached = (raw.input_tokens_details.cached_tokens if raw.input_tokens_details else 0) or 0
    return Usage(
        input_tokens=max(raw.input_tokens - cached, 0),
        output_tokens=raw.output_tokens,
        cache_read_tokens=cached,
    )
