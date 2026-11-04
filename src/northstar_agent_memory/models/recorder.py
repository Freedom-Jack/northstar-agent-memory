"""Record every model output before it is read, and never regenerate it (MEMORY-ARCHITECTURE §5.12).

A call is keyed by what the model is shown and how: family, the resolved model, system,
messages, schema, max_tokens, effort and sample. The purpose and metadata are not part
of the key. Modes:
- "record": a hit returns the stored result (`from_record=True`: no new spend); a miss
  calls the inner port and stores the result. Threads sending the same request share one
  live call: the first holds a lock on the key, and the others wait and replay its result.
- "replay": a miss raises ModelError; nothing is ever called live.
- "live": always calls the inner port, and replaces the stored result.

A call the vendor billed but whose output failed (a refusal, a truncated or invalid
structured output) is stored too and raises the same error on replay, with the billed
result attached as `err.result`. A copy of the request is stored with each result so a
recording can be audited. Changing the configured model changes the key, and so does
turning the server-side refusal fallback off (`allow_fallback=False`), which can change
who answers; the default keeps the keys that were recorded before the field existed.
Prompt caching changes only the price, so it is not part of the key.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import sqlite3
import threading
from collections.abc import Callable, Iterator
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from pathlib import Path

from northstar_agent_memory.models.budget import attach, billed_result
from northstar_agent_memory.models.port import (
    ModelError,
    ModelPort,
    ModelRefused,
    ModelRequest,
    ModelResult,
    Usage,
)

MODES = ("record", "replay", "live")
ERRORS: dict[str, type[ModelError]] = {"ModelError": ModelError, "ModelRefused": ModelRefused}
_RESULT_FIELDS = frozenset(f.name for f in dataclasses.fields(ModelResult))

_SCHEMA = """
CREATE TABLE IF NOT EXISTS recordings (
    key TEXT PRIMARY KEY,
    recorded_at TEXT NOT NULL,
    purpose TEXT NOT NULL,
    family TEXT NOT NULL,
    model TEXT NOT NULL,
    request_json TEXT NOT NULL,
    result_json TEXT NOT NULL,
    cost_usd REAL NOT NULL,
    error TEXT,
    error_message TEXT
);
"""


def request_key(req: ModelRequest, model: str, route: str = "api") -> str:
    """The recording key for `req` as served by `model` on `route`.

    API keys carry no route, so they match recordings made before the harness route existed.
    A harness key does, so a run on one route never replays the other's answers: the two can
    answer differently, and a comparison must hold one condition (DESIGN §8).
    """
    shown = {
        "family": req.family,
        "model": model,
        "system": req.system,
        "messages": req.messages,
        "schema": req.schema,
        "max_tokens": req.max_tokens,
        "effort": req.effort,
        "sample": req.sample,
    }
    if not req.allow_fallback:
        shown["allow_fallback"] = False
    if route != "api" and req.family != "stub":
        shown["route"] = route
    canonical = json.dumps(shown, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class RecordingPort:
    """A ModelPort that stores what the port it wraps returns. `resolver` names the model a request will use."""

    def __init__(
        self,
        inner: ModelPort,
        db_path: Path,
        mode: str = "record",
        resolver: Callable[[ModelRequest], str] | None = None,
        route: str = "api",
    ) -> None:
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}, not {mode!r}")
        self.inner = inner
        self.db_path = Path(db_path)
        self.mode = mode
        self.resolver = resolver or (lambda req: req.model or "")
        self.route = route
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.Lock()
        self._key_locks: dict[str, list] = {}  # key -> [lock, threads holding or waiting for it]
        self._key_locks_guard = threading.Lock()
        with self._write_lock, closing(self._connect()) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, timeout=30)

    def will_call_live(self, req: ModelRequest) -> bool:
        """Whether `complete` would call the inner port (the budget guard asks before it admits a call)."""
        if self.mode == "replay":
            return False
        return self.mode == "live" or self._load(self._key(req)) is None

    def complete(self, req: ModelRequest) -> ModelResult:
        key = self._key(req)
        if self.mode != "live":
            row = self._load(key)
            if row is not None:
                return self._replay(row)
            if self.mode == "replay":
                raise ModelError(
                    f"no recording for the {req.purpose!r} call (key {key[:12]}) in {self.db_path.name}; "
                    "replay mode never calls a model"
                )
        if self.mode == "live":
            return self._call_and_store(key, req)
        with self._locked(key):
            # Another thread may have stored the result while this one waited for the lock.
            row = self._load(key)
            if row is not None:
                return self._replay(row)
            return self._call_and_store(key, req)

    def _call_and_store(self, key: str, req: ModelRequest) -> ModelResult:
        try:
            result = self.inner.complete(req)
        except ModelError as err:
            billed = billed_result(err)
            if billed is not None and not billed.from_record:
                self._store(key, req, billed, type(err).__name__, str(err))
            raise
        self._store(key, req, result)
        return result

    @contextmanager
    def _locked(self, key: str) -> Iterator[None]:
        """Hold the lock for `key`; the lock is dropped from the table when no thread wants it."""
        with self._key_locks_guard:
            entry = self._key_locks.setdefault(key, [threading.Lock(), 0])
            entry[1] += 1
        try:
            with entry[0]:
                yield
        finally:
            with self._key_locks_guard:
                entry[1] -= 1
                if entry[1] == 0:
                    del self._key_locks[key]

    def count(self) -> int:
        with closing(self._connect()) as conn:
            return conn.execute("SELECT COUNT(*) FROM recordings").fetchone()[0]

    def _key(self, req: ModelRequest) -> str:
        return request_key(req, self.resolver(req), self.route)

    def _load(self, key: str) -> sqlite3.Row | None:
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            return conn.execute("SELECT * FROM recordings WHERE key = ?", (key,)).fetchone()

    def _store(
        self, key: str, req: ModelRequest, result: ModelResult, error: str | None = None, message: str | None = None
    ) -> None:
        verb = "REPLACE" if self.mode == "live" else "IGNORE"
        row = (
            key,
            datetime.now(UTC).isoformat(timespec="seconds"),
            req.purpose,
            result.family,
            result.model,
            json.dumps(dataclasses.asdict(req), sort_keys=True, ensure_ascii=False, default=str),
            json.dumps(dataclasses.asdict(result), sort_keys=True, ensure_ascii=False),
            result.cost_usd,
            error,
            message,
        )
        with self._write_lock, closing(self._connect()) as conn, conn:
            conn.execute(f"INSERT OR {verb} INTO recordings VALUES ({', '.join('?' * len(row))})", row)

    def _replay(self, row: sqlite3.Row) -> ModelResult:
        # A harness result also stored `api_equivalent_usd`; a replay is a plain ModelResult, so it is left out.
        data = {key: value for key, value in json.loads(row["result_json"]).items() if key in _RESULT_FIELDS}
        data["usage"] = Usage(**data["usage"])
        data["from_record"] = True
        result = ModelResult(**data)
        if row["error"] is not None:
            error = ERRORS.get(row["error"], ModelError)
            raise attach(error(row["error_message"]), result)
        return result

