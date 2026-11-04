import subprocess

import pytest

from northstar_agent_memory.models import keys


@pytest.fixture
def keychain(monkeypatch):
    """Turn the Keychain back on, with a fake `security` that returns `store`."""
    monkeypatch.delenv("NORTHSTAR_NO_KEYCHAIN", raising=False)
    monkeypatch.setattr(keys.shutil, "which", lambda name: "/usr/bin/security")
    store: dict[str, str] = {}
    calls: list[list[str]] = []

    def run(argv, **kw):
        calls.append(argv)
        service = argv[argv.index("-s") + 1]
        if service in store:
            return subprocess.CompletedProcess(argv, 0, stdout=store[service] + "\n", stderr="")
        return subprocess.CompletedProcess(argv, 44, stdout="", stderr="not found")

    monkeypatch.setattr(keys.subprocess, "run", run)
    return store, calls


def test_env_var_when_keychain_skipped(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-env")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-oa-env")
    assert keys.get_api_key("anthropic") == "sk-ant-env"
    assert keys.get_api_key("openai") == "sk-oa-env"
    assert keys.key_status("anthropic") == "env"


def test_missing(monkeypatch):
    assert keys.get_api_key("openai") is None and keys.key_status("openai") == "missing"
    assert keys.get_api_key("anthropic") is None and keys.key_status("anthropic") == "sdk-default"


def test_keychain_comes_first(keychain, monkeypatch):
    store, calls = keychain
    store["northstar-anthropic"] = "sk-ant-chain"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-env")
    assert keys.get_api_key("anthropic") == "sk-ant-chain"
    assert keys.key_status("anthropic") == "keychain"
    argv = calls[0]
    assert argv[:2] == ["security", "find-generic-password"] and "-w" in argv
    assert argv[argv.index("-s") + 1] == "northstar-anthropic"


def test_keychain_miss_falls_back_to_env(keychain, monkeypatch):
    store, _ = keychain
    monkeypatch.setenv("OPENAI_API_KEY", "sk-oa-env")
    assert keys.get_api_key("openai") == "sk-oa-env"
    assert keys.key_status("openai") == "env"


def test_no_keychain_switch_skips_security(keychain, monkeypatch):
    store, calls = keychain
    monkeypatch.setenv("NORTHSTAR_NO_KEYCHAIN", "1")
    assert keys.get_api_key("anthropic") is None
    assert calls == []


def test_security_failures_are_a_miss(monkeypatch):
    monkeypatch.delenv("NORTHSTAR_NO_KEYCHAIN", raising=False)
    monkeypatch.setattr(keys.shutil, "which", lambda name: "/usr/bin/security")

    def boom(argv, **kw):
        raise subprocess.TimeoutExpired(argv, 10)

    monkeypatch.setattr(keys.subprocess, "run", boom)
    assert keys.get_api_key("openai") is None


def test_unknown_family():
    with pytest.raises(ValueError):
        keys.get_api_key("stub")
