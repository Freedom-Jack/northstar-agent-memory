"""Load the versioned starting values, with the user's own settings on top.

defaults.toml ships with the code (I19). The user's settings live in
<data root>/settings.toml and override matching keys; they hold personal choices
such as the monthly cost cap and which folders are personal.
"""

from __future__ import annotations

import tomllib
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any

from northstar_agent_memory.paths import data_root


def _merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def settings_path() -> Path:
    return data_root() / "settings.toml"


@lru_cache(maxsize=1)
def defaults() -> dict[str, Any]:
    text = resources.files(__package__).joinpath("defaults.toml").read_text(encoding="utf-8")
    return tomllib.loads(text)


def load() -> dict[str, Any]:
    """Defaults merged with the user's settings. Not cached: settings may change."""
    config = defaults()
    path = settings_path()
    if path.exists():
        config = _merge(config, tomllib.loads(path.read_text(encoding="utf-8")))
    return config


def model_for(config: dict, family: str, role: str) -> str:
    """The configured model ID for a family and role, or "" when not set."""
    return config.get("models", {}).get(family, {}).get(role, "")


def price_for(config: dict, model: str) -> dict | None:
    return config.get("prices", {}).get(model)
