"""Fake SDK clients and responses shaped like the vendors' (no network)."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace as NS

import httpx2

from northstar_agent_memory import config as cfg
from northstar_agent_memory.models.harness import Process
from northstar_agent_memory.models.port import ModelRequest


def make_config(**budget) -> dict:
    config = copy.deepcopy(cfg.load())
    config["budget"] = {**config["budget"], **budget}
    return config


def with_openai(config: dict, model: str = "gpt-test", price: dict | None = None) -> dict:
    config = copy.deepcopy(config)
    config["models"]["openai"]["judge"] = model
    config["prices"][model] = price or {"input": 1.0, "output": 4.0, "cache_read": 0.1}
    return config


def make_req(**kw) -> ModelRequest:
    base = dict(
        purpose="test.call",
        role="judge",
        family="anthropic",
        system="Be brief.",
        messages=[{"role": "user", "content": "hello"}],
    )
    base.update(kw)
    return ModelRequest(**base)


SCHEMA = {
    "type": "object",
    "properties": {"verdict": {"type": "string"}},
    "required": ["verdict"],
    "additionalProperties": False,
}


def http_error(cls, status: int, header: str = "request-id", rid: str = "req_1", module=None):
    request = httpx2.Request("POST", "https://api.test/v1")
    response = httpx2.Response(status, request=request, headers={header: rid})
    return cls("boom", response=response, body=None)


# --- Anthropic ---------------------------------------------------------------------


def a_usage(i=100, o=50, cr=0, cw=0, iterations=None) -> NS:
    return NS(
        input_tokens=i,
        output_tokens=o,
        cache_read_input_tokens=cr,
        cache_creation_input_tokens=cw,
        iterations=iterations,
    )


def a_response(text='{"verdict": "ok"}', *, model="claude-opus-5-5", stop="end_turn", usage=None, content=None,
               details=None) -> NS:
    blocks = content if content is not None else [NS(type="text", text=text)]
    return NS(
        content=blocks,
        model=model,
        stop_reason=stop,
        stop_details=details,
        usage=usage or a_usage(),
        _request_id="req_abc",
    )


class FakeAnthropic:
    """Records each call as (route, kwargs); returns `response` or raises `error`."""

    def __init__(self, response=None, error=None) -> None:
        self.response = response if response is not None else a_response()
        self.error = error
        self.calls: list[tuple[str, dict]] = []
        self.messages = NS(create=lambda **kw: self._call("messages", kw))
        self.beta = NS(messages=NS(create=lambda **kw: self._call("beta", kw)))

    def _call(self, route: str, kwargs: dict):
        self.calls.append((route, kwargs))
        if self.error:
            raise self.error
        return self.response


# --- OpenAI ------------------------------------------------------------------------


def o_response(text='{"verdict": "ok"}', *, status="completed", reason=None, refusal=None, model="gpt-test-2026",
               input_tokens=1000, cached=0, output_tokens=200, error=None) -> NS:
    parts = [NS(type="refusal", refusal=refusal)] if refusal else [NS(type="output_text", text=text)]
    return NS(
        id="resp_1",
        model=model,
        status=status,
        incomplete_details=NS(reason=reason) if reason else None,
        error=error,
        output=[NS(type="message", content=parts)],
        output_text="" if refusal else text,
        usage=NS(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_tokens_details=NS(cached_tokens=cached),
        ),
    )


class FakeOpenAI:
    def __init__(self, response=None, error=None) -> None:
        self.response = response if response is not None else o_response()
        self.error = error
        self.calls: list[dict] = []
        self.responses = NS(create=self._create)

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


# --- Claude Code and Codex, run as programs ----------------------------------------------


def make_program(path: Path) -> Path:
    """A file that looks like an installed program (it is never run: harness.run_process is faked)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def with_programs(config: dict, claude: Path | None = None, codex: Path | None = None) -> dict:
    config = copy.deepcopy(config)
    config["harness"] = {**config["harness"], "claude_binary": str(claude or ""), "codex_binary": str(codex or "")}
    return config


class FakeProcess:
    """Stands in for harness.run_process. Each call is kept as it was made, with what the folder and the schema
    file looked like at that moment; the replies are returned in turn, the last one repeating, and an exception
    reply is raised."""

    def __init__(self, *replies: Process | BaseException) -> None:
        self.replies = list(replies) or [Process(0, "", "")]
        self.calls: list[dict] = []

    def __call__(self, argv, *, stdin, cwd, env, timeout_s):
        cwd = Path(cwd)
        call = {
            "argv": list(argv),
            "stdin": stdin,
            "cwd": cwd,
            "env": dict(env),
            "timeout_s": timeout_s,
            "cwd_was_empty": cwd.is_dir() and not any(cwd.iterdir()),
        }
        if "--output-schema" in argv:
            path = Path(argv[argv.index("--output-schema") + 1])
            call["schema_path"] = path
            call["schema_text"] = path.read_text(encoding="utf-8") if path.exists() else None
        self.calls.append(call)
        reply = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        if isinstance(reply, BaseException):
            raise reply
        return reply


def claude_json(result="ok", *, structured=None, is_error=False, subtype="success", stop="end_turn", cost=0.0123,
                models=None, usage=None, **extra) -> str:
    """What `claude -p --output-format json` prints: the result message."""
    if models is None:
        models = {
            "claude-opus-5-5": {"inputTokens": 120, "outputTokens": 30, "cacheReadInputTokens": 400,
                                "cacheCreationInputTokens": 50, "costUSD": cost}
        }
    data = {
        "type": "result",
        "subtype": subtype,
        "is_error": is_error,
        "duration_ms": 1500,
        "duration_api_ms": 1400,
        "num_turns": 1,
        "result": result,
        "stop_reason": stop,
        "session_id": "sess-1",
        "total_cost_usd": cost,
        "usage": usage if usage is not None else {"input_tokens": 120, "output_tokens": 30,
                                                   "cache_read_input_tokens": 400, "cache_creation_input_tokens": 50},
        "modelUsage": models,
        "permission_denials": [],
        "uuid": "uuid-1",
    }
    if structured is not None:
        data["structured_output"] = structured
    data.update(extra)
    return json.dumps(data)


def claude_ok(result="ok", **kw) -> Process:
    return Process(0, claude_json(result, **kw), "")


def claude_failed(text: str, *, status=None, **extra) -> Process:
    """A run that failed inside: Claude Code prints the failure as the result and exits 1."""
    nothing = {"claude-opus-5-5": {"inputTokens": 0, "outputTokens": 0, "cacheReadInputTokens": 0,
                                   "cacheCreationInputTokens": 0, "costUSD": 0}}
    usage = {"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}
    return Process(1, claude_json(text, is_error=True, models=nothing, usage=usage, cost=0, api_error_status=status, **extra), "")


def codex_events(answer='{"verdict": "ok"}', *, usage=None, thread="thread-1", failed=None, errors=(), noise=()) -> str:
    """What `codex exec --json` prints: one JSON event per line."""
    events: list = [{"type": "thread.started", "thread_id": thread}, {"type": "turn.started"}, *noise]
    events += [{"type": "error", "message": message} for message in errors]
    if failed is not None:
        events.append({"type": "turn.failed", "error": {"message": failed}})
    else:
        events.append({"type": "item.completed", "item": {"id": "item_0", "type": "reasoning", "text": "thinking"}})
        if answer is not None:
            events.append({"type": "item.completed", "item": {"id": "item_1", "type": "agent_message", "text": answer}})
        events.append({
            "type": "turn.completed",
            "usage": usage or {"input_tokens": 1000, "cached_input_tokens": 400, "output_tokens": 200,
                               "reasoning_output_tokens": 50},
        })
    return "".join(json.dumps(e) + "\n" for e in events)


def codex_ok(answer='{"verdict": "ok"}', **kw) -> Process:
    return Process(0, codex_events(answer, **kw), "")


def codex_failed(message: str, **kw) -> Process:
    return Process(1, codex_events(failed=message, **kw), "")
