"""Cost metering and caps: prices, the cost ledger and the budget guard (DESIGN §9, §10).

Every live call is priced from config, never from code, and written to the cost
ledger. The budget guard wraps a port. Before a live call it makes a conservative
estimate and refuses the call when no monthly cap is set, when the call could pass
the hard cap, or when it could pass the run's budget. Past the soft cap it warns
once, so that maintenance can defer lower-priority work (DESIGN §10). Replayed calls
(`from_record`) cost nothing new.

That is the "api" route. On the "harness" route (DESIGN §1.4, 2026-10-29) a call runs on the
user's own plan and has no dollar bill, so there is nothing to estimate or cap: the guard admits
it, and the plan's own limit shows up as PlanLimitReached, which stops a run like any other
BudgetExceeded. The ledger still records the call: its tokens, its route, and what the vendor's
own meter put at API list prices (`api_equivalent_usd`, information only).

A call that fails after the vendor answered (a refusal, or a truncated or invalid
structured output) was still billed. The adapters raise such errors with the billed
ModelResult attached as `err.result` (`attach`), so the ledger meters them and the
recorder keeps them (MEMORY-ARCHITECTURE §5.12).

Model resolution lives here because pricing needs it: a request's model is its own
`model`, else the configured one for its family and role.
"""

from __future__ import annotations

import json
import logging
import math
import sqlite3
import threading
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from northstar_agent_memory.config import model_for, price_for, settings_path
from northstar_agent_memory.models.port import (
    BudgetExceeded,
    ModelError,
    ModelPort,
    ModelRequest,
    ModelResult,
    NoCostCap,
    Usage,
)

log = logging.getLogger(__name__)

CHARS_PER_TOKEN = 3.5  # errs high: English text averages about 4 characters per token
OUTPUT_ESTIMATE_CAP = 4000  # output tokens assumed when estimating a call
ROUTES = ("harness", "api")  # how hidden calls reach the models (DESIGN §1.4); the guard meters only "api"


def resolve_model(config: dict, req: ModelRequest) -> str:
    """The model a request will use, or "" when none is configured."""
    if req.model:
        return req.model
    if req.family == "stub":
        return f"stub-{req.role}"
    return model_for(config, req.family, req.role)


def require_model(config: dict, req: ModelRequest) -> str:
    model = resolve_model(config, req)
    if not model:
        raise ModelError(
            f"no {req.family} model is configured for role {req.role!r}; "
            "run `northstar models check` to see which models your key can reach"
        )
    return model


def require_price(config: dict, model: str) -> dict:
    price = price_for(config, model)
    if not price:
        raise ModelError(f"no price for model {model!r} in config; cost metering needs one under [prices]")
    return price


def cost_usd(price: dict, usage: Usage) -> float:
    """Dollars for one call's usage, at prices per million tokens."""
    input_price, output_price = price["input"], price["output"]
    cache_read_price = price.get("cache_read", input_price)
    threshold = price.get("long_threshold_tokens")
    prompt = usage.input_tokens + usage.cache_read_tokens + usage.cache_write_tokens
    if threshold and prompt > threshold:
        # A long prompt is billed at the long rates. Cache reads use the long cache price when
        # the table has one, else they keep their ratio to input.
        cache_read_price = price.get("long_cache_read", cache_read_price * price["long_input"] / input_price)
        input_price, output_price = price["long_input"], price["long_output"]
    cache_write_price = input_price * price.get("cache_write_multiplier", 1.0)
    total = (
        usage.input_tokens * input_price
        + usage.output_tokens * output_price
        + usage.cache_read_tokens * cache_read_price
        + usage.cache_write_tokens * cache_write_price
    )
    return total / 1_000_000


def estimate_tokens(chars: int) -> int:
    return math.ceil(chars / CHARS_PER_TOKEN)


def request_chars(req: ModelRequest) -> int:
    chars = len(req.system) + sum(len(str(m.get("content", ""))) for m in req.messages)
    if req.schema is not None:
        chars += len(json.dumps(req.schema))
    return chars


def estimate_cost(price: dict, req: ModelRequest) -> float:
    """A cost for `req` that errs high: no cache discount, and output near its cap.

    Input is priced at the cache-write rate only when the request asks Anthropic to cache
    it; otherwise nothing is cached, and it is priced as plain input.
    """
    tokens = estimate_tokens(request_chars(req))
    caching = req.cache and req.family == "anthropic"
    usage = Usage(
        input_tokens=0 if caching else tokens,
        output_tokens=min(req.max_tokens, OUTPUT_ESTIMATE_CAP),
        cache_write_tokens=tokens if caching else 0,
    )
    return cost_usd(price, usage)


def attach(err: ModelError, result: ModelResult) -> ModelError:
    """Mark `err` as raised after the vendor answered: `result` is what the call cost."""
    err.result = result  # type: ignore[attr-defined]
    return err


def billed_result(err: BaseException) -> ModelResult | None:
    """The billed result attached to an error, when the vendor answered before it failed."""
    return getattr(err, "result", None)


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat(timespec="seconds")


_LEDGER_SCHEMA = """
CREATE TABLE IF NOT EXISTS calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    run_id TEXT NOT NULL,
    family TEXT NOT NULL,
    model TEXT NOT NULL,
    served_model TEXT,
    purpose TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cache_read_tokens INTEGER NOT NULL,
    cache_write_tokens INTEGER NOT NULL,
    cost_usd REAL NOT NULL,
    latency_s REAL NOT NULL,
    outcome TEXT NOT NULL,
    request_id TEXT,
    route TEXT,
    api_equivalent_usd REAL
);
CREATE INDEX IF NOT EXISTS calls_at ON calls (at);
CREATE INDEX IF NOT EXISTS calls_run ON calls (run_id);
"""

_LEDGER_COLUMNS = (
    "at, run_id, family, model, served_model, purpose, input_tokens, output_tokens, "
    "cache_read_tokens, cache_write_tokens, cost_usd, latency_s, outcome, request_id, route, api_equivalent_usd"
)


def _add_missing_columns(conn: sqlite3.Connection) -> None:
    """Bring a ledger made before the harness route up to date. Every call it holds was made by a stub or went
    to a vendor's API, so that is what its route is."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(calls)")}
    for name, kind in (("route", "TEXT"), ("api_equivalent_usd", "REAL")):
        if name not in columns:
            try:
                conn.execute(f"ALTER TABLE calls ADD COLUMN {name} {kind}")
            except sqlite3.OperationalError:  # another process added it first
                pass
    conn.execute("UPDATE calls SET route = CASE family WHEN 'stub' THEN 'stub' ELSE 'api' END WHERE route IS NULL")
    conn.commit()


class CostLedger:
    """Every live model call and what it cost (UTC timestamps), in SQLite."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.Lock()
        with self._write_lock, closing(self._connect()) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(_LEDGER_SCHEMA)
            _add_missing_columns(conn)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, timeout=30)

    def record(self, run_id: str, purpose: str, result: ModelResult, outcome: str = "ok", route: str = "api") -> None:
        """Add one live call. `outcome` is "ok" or the error a billed call raised; `route` is how the call
        reached the model. A harness result also carries `api_equivalent_usd`, which is kept beside `cost_usd`."""
        u = result.usage
        row = (
            _iso(datetime.now(UTC)),
            run_id,
            result.family,
            result.model,
            result.served_model,
            purpose,
            u.input_tokens,
            u.output_tokens,
            u.cache_read_tokens,
            u.cache_write_tokens,
            result.cost_usd,
            result.latency_s,
            outcome,
            result.request_id,
            route,
            getattr(result, "api_equivalent_usd", None),
        )
        with self._write_lock, closing(self._connect()) as conn, conn:
            conn.execute(f"INSERT INTO calls ({_LEDGER_COLUMNS}) VALUES ({', '.join('?' * len(row))})", row)

    def month_to_date_usd(self, now: datetime | None = None) -> float:
        """Spend since the start of the current calendar month, in UTC."""
        start = (now or datetime.now(UTC)).astimezone(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return self._sum("at >= ?", (_iso(start),))

    def run_spent_usd(self, run_id: str) -> float:
        return self._sum("run_id = ?", (run_id,))

    def entries(self, run_id: str | None = None) -> list[dict]:
        where, args = ("WHERE run_id = ?", (run_id,)) if run_id is not None else ("", ())
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(f"SELECT {_LEDGER_COLUMNS} FROM calls {where} ORDER BY id", args).fetchall()
        return [dict(row) for row in rows]

    def _sum(self, where: str, args: tuple) -> float:
        with closing(self._connect()) as conn:
            (total,) = conn.execute(f"SELECT COALESCE(SUM(cost_usd), 0) FROM calls WHERE {where}", args).fetchone()
        return float(total)


class BudgetGuard:
    """A ModelPort that meters live calls and refuses those that could pass a cap.

    It asks the port it wraps whether a request will run live (`will_call_live`, which
    the recorder answers), so recorded calls pass even when no cap is set. The "stub"
    family costs nothing and needs no cap, and neither does a call on the "harness" route:
    a plan has no dollar bill, so only the "api" route is metered against the caps.
    """

    def __init__(
        self,
        inner: ModelPort,
        ledger: CostLedger,
        config: dict,
        run_id: str,
        run_budget_usd: float | None = None,
        route: str = "api",
    ) -> None:
        if route not in ROUTES:
            raise ValueError(f"route must be one of {ROUTES}, not {route!r}")
        self.route = route
        budget = config.get("budget", {})
        self.inner = inner
        self.ledger = ledger
        self.config = config
        self.run_id = run_id
        self.hard_cap_usd = float(budget.get("monthly_hard_usd") or 0)
        self.soft_cap_usd = float(budget.get("monthly_soft_usd") or 0)
        default_run = budget.get("run_default_usd") or 0
        self.run_budget_usd = float(run_budget_usd if run_budget_usd is not None else default_run)
        self.past_soft_cap = False
        self._lock = threading.Lock()
        self._reserved = 0.0  # estimates of this run's live calls still in flight

    def complete(self, req: ModelRequest) -> ModelResult:
        route = "stub" if req.family == "stub" else self.route
        estimate = self._admit(req) if route == "api" and self._will_call_live(req) else 0.0
        try:
            result = self.inner.complete(req)
            if not result.from_record:
                self.ledger.record(self.run_id, req.purpose, result, route=route)
            return result
        except ModelError as err:
            billed = billed_result(err)
            if billed is not None and not billed.from_record:
                self.ledger.record(self.run_id, req.purpose, billed, outcome=type(err).__name__, route=route)
            raise
        finally:
            if estimate:
                with self._lock:
                    self._reserved -= estimate

    def _will_call_live(self, req: ModelRequest) -> bool:
        check = getattr(self.inner, "will_call_live", None)
        return True if check is None else bool(check(req))

    def _admit(self, req: ModelRequest) -> float:
        if self.hard_cap_usd <= 0:
            raise NoCostCap(
                "no monthly cost cap is set, so live model calls are refused; set budget.monthly_hard_usd "
                f"and budget.monthly_soft_usd in {settings_path()} (DESIGN §9 suggests a soft $80 and a hard $120)"
            )
        estimate = estimate_cost(require_price(self.config, require_model(self.config, req)), req)
        with self._lock:
            month = self.ledger.month_to_date_usd() + self._reserved
            run = self.ledger.run_spent_usd(self.run_id) + self._reserved
            if month + estimate > self.hard_cap_usd:
                raise BudgetExceeded(
                    f"this call (about ${estimate:.4f}) could pass the monthly hard cap of "
                    f"${self.hard_cap_usd:.2f}: ${month:.2f} is spent or in flight this month"
                )
            if run + estimate > self.run_budget_usd:
                raise BudgetExceeded(
                    f"this call (about ${estimate:.4f}) could pass the budget of run {self.run_id!r}, "
                    f"${self.run_budget_usd:.2f}: ${run:.2f} is spent or in flight"
                )
            if self.soft_cap_usd > 0 and month + estimate > self.soft_cap_usd and not self.past_soft_cap:
                self.past_soft_cap = True
                log.warning(
                    "model spend this month (about $%.2f) is past the soft cap of $%.2f",
                    month + estimate,
                    self.soft_cap_usd,
                )
            self._reserved += estimate
        return estimate
