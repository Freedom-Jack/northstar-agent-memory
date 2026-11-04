"""Every test runs against a throwaway data root, never the real one, and never starts a vendor's program."""

from __future__ import annotations

import shutil

import pytest


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("NORTHSTAR_HOME", str(tmp_path / "northstar-home"))
    # Tests never make live model calls: no keys reach them.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("NORTHSTAR_NO_KEYCHAIN", "1")
    from northstar_agent_memory import config

    config.defaults.cache_clear()
    yield tmp_path / "northstar-home"


@pytest.fixture(autouse=True)
def no_vendor_programs(tmp_path, monkeypatch):
    """The harness route runs Claude Code and Codex, which are on the machine that runs the tests: no test may
    start them, find them, or read their login. A test that needs a run fakes `harness.run_process` and names a
    program in settings; one that needs a lookup patches the lookup (see tests/models/test_model_harness_*.py)."""
    from northstar_agent_memory.models import harness, harness_claude, harness_codex

    def refuse(argv, **kwargs):
        raise AssertionError("a test tried to start a program: fake harness.run_process")

    monkeypatch.setattr(harness, "run_process", refuse)
    monkeypatch.setattr(harness_claude, "bundled_copies", lambda: [])
    monkeypatch.setattr(harness_codex, "CODEX_APP_BINARY", tmp_path / "no-chatgpt-app" / "codex")
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "no-codex-home"))
    real_which = shutil.which
    monkeypatch.setattr(shutil, "which", lambda cmd, *a, **k: None if cmd in ("claude", "codex") else real_which(cmd, *a, **k))
