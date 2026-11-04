"""Build the port the harness uses (DESIGN §1.4, §9; MEMORY-ARCHITECTURE §5.12).

`build_port` routes each request by its family to the right adapter, wraps the router
in the recorder, and wraps that in the budget guard: replays cost nothing, live calls
are metered, and a missing key fails only when its family is first used.

The route says what the adapters are (DESIGN §1.4, revised 2026-10-29). "harness", the
default in config, runs Claude Code and Codex headless on the user's own plans: no key,
no dollar bill. "api" uses the vendors' APIs and the user's keys, metered against the
caps. A `route` argument overrides the configured one. A stub family is the same on both.
"""

from __future__ import annotations

import threading
from pathlib import Path

from northstar_agent_memory.config import settings_path
from northstar_agent_memory.models.anthropic_adapter import AnthropicAdapter
from northstar_agent_memory.models.budget import ROUTES, BudgetGuard, CostLedger, resolve_model
from northstar_agent_memory.models.harness_claude import ClaudeCodeHeadless
from northstar_agent_memory.models.harness_codex import CodexExec
from northstar_agent_memory.models.keys import get_api_key
from northstar_agent_memory.models.openai_adapter import OpenAIAdapter
from northstar_agent_memory.models.port import (
    FAMILIES,
    ModelError,
    ModelPort,
    ModelRequest,
    ModelResult,
    NoCredentials,
)
from northstar_agent_memory.models.recorder import RecordingPort
from northstar_agent_memory.models.stub import StubModel, schema_aware
from northstar_agent_memory.paths import eval_root

RECORD_DB = "model-calls.sqlite"
LEDGER_DB = "cost-ledger.sqlite"


def resolve_route(config: dict, route: str | None = None) -> str:
    """The route to use: `route` when given, else [route].default from config (the harness when it has none)."""
    chosen = route or config.get("route", {}).get("default") or "harness"
    if chosen not in ROUTES:
        raise ModelError(f"route {chosen!r} is not one of {', '.join(ROUTES)}: set route.default in {settings_path()}")
    return chosen


class FamilyRouter:
    """Sends each request to the adapter for its family on one route, creating adapters on first use."""

    def __init__(self, config: dict, route: str | None = None) -> None:
        self.config = config
        self.route = resolve_route(config, route)
        self._ports: dict[str, ModelPort] = {}
        self._lock = threading.Lock()

    def complete(self, req: ModelRequest) -> ModelResult:
        return self._port(req.family).complete(req)

    def _port(self, family: str) -> ModelPort:
        with self._lock:
            if family not in self._ports:
                self._ports[family] = self._make(family)
            return self._ports[family]

    def _make(self, family: str) -> ModelPort:
        if family == "stub":
            return StubModel(schema_aware)
        if family not in FAMILIES:
            raise ModelError(f"unknown model family {family!r}")
        if self.route == "harness":
            # The program is looked for at the first call, as a missing key is.
            return ClaudeCodeHeadless(self.config) if family == "anthropic" else CodexExec(self.config)
        if family == "anthropic":
            return AnthropicAdapter(self.config, get_api_key("anthropic"))
        key = get_api_key("openai")
        if key is None:
            raise NoCredentials("no OpenAI API key: store one in the Keychain as 'northstar-openai' or set OPENAI_API_KEY")
        return OpenAIAdapter(self.config, key)


def build_port(
    config: dict,
    *,
    run_id: str,
    record_db: Path | None = None,
    ledger_db: Path | None = None,
    mode: str = "record",
    run_budget_usd: float | None = None,
    route: str | None = None,
) -> ModelPort:
    """The recorded, budget-guarded port for one run. Databases default to paths under eval_root().
    `route` overrides the configured one; `run_budget_usd` applies only on the "api" route."""
    router = FamilyRouter(config, route)
    recorder = RecordingPort(
        router,
        record_db or eval_root() / RECORD_DB,
        mode=mode,
        resolver=lambda req: resolve_model(config, req),
        route=router.route,
    )
    ledger = CostLedger(ledger_db or eval_root() / LEDGER_DB)
    return BudgetGuard(recorder, ledger, config, run_id, run_budget_usd, route=router.route)
