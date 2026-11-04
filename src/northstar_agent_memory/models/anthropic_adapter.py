"""Claude through the Anthropic API, behind the model port (DESIGN §1.4).

One non-streaming Messages call per request, with max_tokens at most 16,000.
Structured output and effort go in output_config. Prompt caching is sent only when
the request asks for it (`cache`): a cache write costs 1.25 times the input price, so
a single-use context must not pay it. No sampling, thinking or tool parameters are
sent: adaptive thinking is the default, and current models reject the rest. Opus 5.5
and Sonnet 5.5 calls opt into the server-side refusal fallback when the request
allows it (`allow_fallback`), so a request one model declines can be served by
another; Haiku 5.5 has none, and a measurement run turns the fallback off so that the
model it names is the one that answers. The model that answered is kept as
`served_model`, and after a fallback each attempt is priced at its own model's rates.

A refusal that survives raises ModelRefused, and a truncated or invalid structured
output raises ModelError. Both carry the billed result (budget.attach). A rejected key
(401, 403) raises NoCredentials, and a model the key cannot reach (404) raises
ModelUnavailable, which is fatal for a run.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import anthropic

from northstar_agent_memory.config import price_for
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

log = logging.getLogger(__name__)

FALLBACK_BETA = "server-side-fallback-2026-07-01"
FALLBACK_MODELS = frozenset({"claude-opus-5-5", "claude-sonnet-5-5"})
MAX_TOKENS = 16_000  # the most a non-streaming call allows


class AnthropicAdapter:
    """ModelPort for the "anthropic" family. `client` replaces the SDK client in tests."""

    def __init__(self, config: dict, api_key: str | None = None, *, client: Any = None) -> None:
        self.config = config
        self.client = client if client is not None else _make_client(api_key)
        self._unpriced: set[str] = set()

    def complete(self, req: ModelRequest) -> ModelResult:
        if req.family != "anthropic":
            raise ModelError(f"the Anthropic adapter got a {req.family!r} request")
        model = require_model(self.config, req)
        price = require_price(self.config, model)
        if req.max_tokens > MAX_TOKENS:
            raise ModelError(f"max_tokens {req.max_tokens} is above {MAX_TOKENS}, the most a non-streaming call allows")
        params = _params(req, model)
        started = time.monotonic()
        try:
            if req.allow_fallback and model in FALLBACK_MODELS:
                response = self.client.beta.messages.create(**params, betas=[FALLBACK_BETA], fallbacks="default")
            else:
                response = self.client.messages.create(**params)
        except anthropic.NotFoundError as err:
            raise ModelUnavailable(f"Anthropic API: model {model!r} not found (request {err.request_id})") from err
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as err:
            raise NoCredentials(
                f"Anthropic API rejected the credentials ({err.status_code}, request {err.request_id})"
            ) from err
        except anthropic.RateLimitError as err:
            raise ModelError(f"Anthropic API rate limit, after the SDK's retries (request {err.request_id})") from err
        except anthropic.APIStatusError as err:
            raise ModelError(
                f"Anthropic API error {err.status_code} (request {err.request_id}): {err.message}"
            ) from err
        except anthropic.APIConnectionError as err:
            raise ModelError(f"could not reach the Anthropic API: {err}") from err
        except anthropic.AnthropicError as err:
            raise ModelError(f"Anthropic SDK error: {err}") from err
        return self._result(req, model, price, response, time.monotonic() - started)

    def _result(self, req: ModelRequest, model: str, price: dict, response: Any, latency: float) -> ModelResult:
        usage, cost = self._usage_and_cost(response.usage, model, price)
        result = ModelResult(
            text="",
            parsed=None,
            usage=usage,
            cost_usd=cost,
            latency_s=latency,
            family="anthropic",
            model=model,
            served_model=response.model or model,
            stop_reason=response.stop_reason,
            request_id=getattr(response, "_request_id", None),
        )
        # Checked before the content is read: a refused reply may hold partial output.
        if response.stop_reason == "refusal":
            category = getattr(response.stop_details, "category", None)
            detail = f" ({category})" if category else ""
            raise attach(ModelRefused(f"{result.served_model} refused the request{detail}"), result)
        texts = [block.text for block in _reply_blocks(response.content) if block.type == "text"]
        if req.schema is None:
            result.text = "".join(texts)
            return result
        result.text = texts[0] if texts else ""
        if response.stop_reason == "max_tokens":
            raise attach(ModelError(f"structured output cut off at max_tokens={req.max_tokens}"), result)
        try:
            result.parsed = json.loads(result.text)
        except json.JSONDecodeError as err:
            message = f"structured output is not valid JSON (stop reason {response.stop_reason})"
            raise attach(ModelError(message), result) from err
        return result

    def _usage_and_cost(self, raw: Any, model: str, price: dict) -> tuple[Usage, float]:
        attempts = [a for a in (getattr(raw, "iterations", None) or []) if a.type in ("message", "fallback_message")]
        if not any(a.type == "fallback_message" for a in attempts):
            usage = _usage(raw)
            return usage, cost_usd(price, usage)
        # After a fallback, the top-level usage covers only the attempt that answered, and
        # each attempt bills at its own model's rates. A declined attempt is counted even
        # when the vendor waives it, so the cost errs high.
        total, cost = Usage(), 0.0
        for attempt in attempts:
            part = _usage(attempt)
            total += part
            cost += cost_usd(self._price(attempt.model or model, price), part)
        return total, cost

    def _price(self, model: str, requested_price: dict) -> dict:
        price = price_for(self.config, model)
        if price:
            return price
        if model not in self._unpriced:
            self._unpriced.add(model)
            log.warning("no price for fallback model %s in config; costing it at the requested model's price", model)
        return requested_price


def _make_client(api_key: str | None) -> anthropic.Anthropic:
    """A client with the given key, or with the SDK's own credential chain when there is none."""
    try:
        client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
    except anthropic.AnthropicError as err:
        raise NoCredentials(f"Anthropic credentials could not be loaded: {err}") from err
    if client.api_key is None and client.auth_token is None and client.credentials is None:
        raise NoCredentials(
            "no Anthropic credentials: store an API key in the Keychain as service 'northstar-anthropic', "
            "set ANTHROPIC_API_KEY, or sign in with `ant auth login`"
        )
    return client


def _params(req: ModelRequest, model: str) -> dict:
    params: dict[str, Any] = {
        "model": model,
        "max_tokens": req.max_tokens,
        "messages": [{"role": m["role"], "content": m["content"]} for m in req.messages],
    }
    if req.cache:
        params["cache_control"] = {"type": "ephemeral"}
    if req.system:
        params["system"] = req.system
    output_config: dict[str, Any] = {}
    if req.schema is not None:
        assert_strict(req.schema)
        output_config["format"] = {"type": "json_schema", "schema": req.schema}
    if req.effort is not None:
        output_config["effort"] = req.effort
    if output_config:
        params["output_config"] = output_config
    return params


def _reply_blocks(content: list) -> list:
    """The reply's own blocks: after a fallback mid-reply, those after the last switch point."""
    start = 0
    for i, block in enumerate(content):
        if block.type == "fallback":
            start = i + 1
    return content[start:]


def _usage(raw: Any) -> Usage:
    return Usage(
        input_tokens=raw.input_tokens or 0,
        output_tokens=raw.output_tokens or 0,
        cache_read_tokens=getattr(raw, "cache_read_input_tokens", 0) or 0,
        cache_write_tokens=getattr(raw, "cache_creation_input_tokens", 0) or 0,
    )
