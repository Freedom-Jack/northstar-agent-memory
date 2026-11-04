"""Where Northstar keeps its files.

Personal data lives only under the data root (MEMORY-ARCHITECTURE §3.1), never in
the repository. Public benchmark downloads live under the cache root.
Set NORTHSTAR_HOME to move both roots (tests always do).
"""

from __future__ import annotations

import os
from pathlib import Path


def data_root() -> Path:
    """The data root: ~/Library/Application Support/Northstar, or $NORTHSTAR_HOME/data."""
    home = os.environ.get("NORTHSTAR_HOME")
    if home:
        return Path(home) / "data"
    return Path.home() / "Library" / "Application Support" / "Northstar"


def cache_root() -> Path:
    """Public, re-downloadable data such as benchmark files."""
    home = os.environ.get("NORTHSTAR_HOME")
    if home:
        return Path(home) / "cache"
    return Path.home() / "Library" / "Caches" / "Northstar"


def eval_root() -> Path:
    """Evaluation records: model-call recordings, the cost ledger, results.

    Results computed from the user's own chats are personal data, so they stay here.
    """
    return data_root() / "eval"


def bench_root() -> Path:
    """Downloaded public benchmarks (LongMemEval and the like)."""
    return cache_root() / "bench"


def harness_cwd() -> Path:
    """The empty folder that hidden harness runs start in (DESIGN §1.4), so no project files reach a run."""
    return data_root() / "harness-cwd"


def ensure(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
