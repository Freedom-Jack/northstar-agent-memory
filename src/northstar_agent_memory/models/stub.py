"""A model that needs no network, for tests and dry runs (DESIGN §1.4).

The handler gets the request and returns a string, a dict (the structured output, which
also becomes the JSON text) or a whole ModelResult. Usage comes from a character
estimate and cost is zero, so dry runs exercise the recorder and the ledger without
spending. `scripted` builds a handler from replies listed by purpose.
"""

from __future__ import annotations

import json
import math
import threading
from collections.abc import Callable
from typing import Any

from northstar_agent_memory.models.port import ModelError, ModelRequest, ModelResult, Usage

CHARS_PER_TOKEN = 4

Handler = Callable[[ModelRequest], "str | dict | ModelResult"]


def _tokens(chars: int) -> int:
    return math.ceil(chars / CHARS_PER_TOKEN)


class StubModel:
    """ModelPort with canned answers. `calls` keeps every request it received."""

    def __init__(self, handler: Handler | None = None) -> None:
        self.handler: Handler = handler or (lambda req: "stub")
        self.calls: list[ModelRequest] = []

    def complete(self, req: ModelRequest) -> ModelResult:
        self.calls.append(req)
        reply = self.handler(req)
        if isinstance(reply, ModelResult):
            return reply
        if isinstance(reply, dict):
            parsed: Any = reply
            text = json.dumps(reply, sort_keys=True)
        else:
            parsed, text = None, str(reply)
        if req.schema is not None and parsed is None:
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as err:
                raise ModelError(f"stub reply for {req.purpose!r} is not JSON, and the request has a schema") from err
        chars = len(req.system) + sum(len(str(m.get("content", ""))) for m in req.messages)
        model = f"stub-{req.role}"
        return ModelResult(
            text=text,
            parsed=parsed,
            usage=Usage(input_tokens=_tokens(chars), output_tokens=_tokens(len(text))),
            cost_usd=0.0,
            latency_s=0.0,
            family=req.family,
            model=model,
            served_model=model,
            stop_reason="end_turn",
        )


def example_of(schema: dict) -> Any:
    """The smallest value that satisfies a JSON schema: first enum value, "stub", 0, false, [], or null where allowed."""
    if "enum" in schema:
        return schema["enum"][0]
    kind = schema.get("type")
    kinds = kind if isinstance(kind, list) else [kind]
    if "object" in kinds:
        return {name: example_of(sub) for name, sub in schema.get("properties", {}).items()}
    for k, value in (("array", []), ("string", "stub"), ("integer", 0), ("number", 0), ("boolean", False)):
        if k in kinds:
            return value
    return None


def schema_aware(req: ModelRequest) -> str | dict:
    """A handler for the stub family on the command line: a schema request gets a valid empty reply, the rest "stub"."""
    return example_of(req.schema) if req.schema is not None else "stub"


def scripted(replies: dict[str, list], default: str | dict | ModelResult = "stub") -> Handler:
    """A handler that answers each purpose from its list, in order.

    A purpose with no list, or whose list has run out, gets `default`. Pass an
    Exception in a list to raise it on that call.
    """
    queues = {purpose: list(items) for purpose, items in replies.items()}
    lock = threading.Lock()

    def handler(req: ModelRequest) -> str | dict | ModelResult:
        with lock:
            queue = queues.get(req.purpose)
            reply = queue.pop(0) if queue else default
        if isinstance(reply, BaseException):
            raise reply
        return reply

    return handler
