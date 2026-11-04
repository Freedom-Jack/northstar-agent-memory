"""The model port: one way to call any model family (DESIGN §1.4, MEMORY-ARCHITECTURE §5.12).

Every judgment in Northstar is made by the user's own AI families through the vendors'
APIs. Code calls models only through `ModelPort.complete`, so recording, cost metering
and the family rule live in one place.

Rules for callers:
- Messages hold plain text only. A multi-step loop appends the model's reply as an
  "assistant" message and the next observation as a "user" message.
- `schema` asks for structured output. Schemas must be strict so that both vendors
  accept them: every object lists all of its properties in "required" and sets
  "additionalProperties": false; an optional value uses a type union with "null".
- No sampling parameters exist here: current Claude models reject them, and outputs
  are recorded rather than regenerated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

Family = Literal["anthropic", "openai", "stub"]
FAMILIES: tuple[Family, ...] = ("anthropic", "openai")

# Roles map to model IDs per family in config/defaults.toml ([models.<family>]).
Role = Literal["answerer", "judge", "worker", "worker_small", "checker", "sim_user"]


def other_family(family: str) -> Family:
    """The family that checks work done by `family` (the family rule, DESIGN §1.4)."""
    if family == "anthropic":
        return "openai"
    if family == "openai":
        return "anthropic"
    raise ValueError(f"no other family for {family!r}")


@dataclass(slots=True)
class ModelRequest:
    purpose: str  # what the call is for, e.g. "lme.answer", "judge.qa", "scenario.render"
    role: Role
    family: Family
    system: str
    messages: list[dict]  # [{"role": "user" | "assistant", "content": str}, ...]
    schema: dict | None = None  # strict JSON schema; the result's `parsed` holds the object
    max_tokens: int = 4096
    effort: str | None = None  # "low" | "medium" | "high" | "xhigh" | "max"
    model: str | None = None  # overrides the configured model for this role
    sample: int = 0  # sample index, so repeated samples are recorded separately
    metadata: dict = field(default_factory=dict)  # never sent to the model
    cache: bool = False  # ask the vendor to cache the prompt; only worth it for a prefix reused soon
    allow_fallback: bool = True  # a server-side refusal fallback may answer; measurement runs turn it off


@dataclass(slots=True)
class Usage:
    input_tokens: int = 0  # uncached input tokens
    output_tokens: int = 0  # includes reasoning tokens where the vendor bills them as output
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(
            self.input_tokens + other.input_tokens,
            self.output_tokens + other.output_tokens,
            self.cache_read_tokens + other.cache_read_tokens,
            self.cache_write_tokens + other.cache_write_tokens,
        )


@dataclass(slots=True)
class ModelResult:
    text: str
    parsed: Any | None  # the structured output, when a schema was given
    usage: Usage
    cost_usd: float  # what this call cost when it ran live
    latency_s: float
    family: Family
    model: str  # the model requested
    served_model: str  # the model that answered (differs after a server-side fallback)
    stop_reason: str | None
    request_id: str | None = None
    from_record: bool = False  # replayed from the recorder; no new spend


@runtime_checkable
class ModelPort(Protocol):
    def complete(self, req: ModelRequest) -> ModelResult: ...


class ModelError(Exception):
    """A model call failed after the SDK's own retries."""


class ModelRefused(ModelError):
    """The model declined the request (stop reason "refusal")."""


class BudgetExceeded(ModelError):
    """A live call would pass a cost cap."""


class PlanLimitReached(BudgetExceeded):
    """The user's plan or workspace refused the call for usage or spend (the harness route).

    Fatal for a run: background work waits for the reset rather than retrying (DESIGN §1.4).
    """


class NoCostCap(ModelError):
    """No monthly cost cap is set, so live calls are refused (DESIGN §9)."""


class NoCredentials(ModelError):
    """No API key is available for the family, or the vendor rejected it (401, 403)."""


class ModelUnavailable(ModelError):
    """The vendor does not serve the configured model to this key (404). Fatal for a run."""


class SchemaNotStrict(ValueError):
    """A schema that one of the vendors would reject in strict mode."""
