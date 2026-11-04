"""Where the API keys come from (DESIGN §1.4, §9).

Order: the macOS Keychain (service `northstar-<family>`, account the login user), then
the vendor's environment variable. For Anthropic, no key means the SDK's own credential
resolution is used. Keys are never logged, printed or put in an error message.
Set NORTHSTAR_NO_KEYCHAIN=1 to skip the Keychain (tests always do).
"""

from __future__ import annotations

import getpass
import os
import shutil
import subprocess
from typing import Literal

ENV_VARS = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}
KeyStatus = Literal["keychain", "env", "sdk-default", "missing"]


def _keychain_key(family: str) -> str | None:
    if os.environ.get("NORTHSTAR_NO_KEYCHAIN") == "1" or shutil.which("security") is None:
        return None
    try:
        proc = subprocess.run(
            ["security", "find-generic-password", "-s", f"northstar-{family}", "-a", getpass.getuser(), "-w"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    key = proc.stdout.strip()
    return key if proc.returncode == 0 and key else None


def _env_key(family: str) -> str | None:
    return os.environ.get(ENV_VARS[family], "").strip() or None


def _check_family(family: str) -> None:
    if family not in ENV_VARS:
        raise ValueError(f"no API key for family {family!r}")


def get_api_key(family: str) -> str | None:
    """The API key for `family`, or None (for Anthropic: let the SDK find its credentials)."""
    _check_family(family)
    return _keychain_key(family) or _env_key(family)


def key_status(family: str) -> KeyStatus:
    """Where the key for `family` would come from, for the doctor command. Never returns the key."""
    _check_family(family)
    if _keychain_key(family):
        return "keychain"
    if _env_key(family):
        return "env"
    return "sdk-default" if family == "anthropic" else "missing"
