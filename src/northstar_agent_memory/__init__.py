"""Northstar: a memory and focus layer for the AI you already use.

The design is docs/design/revision-2026-10-23/DESIGN.md (version 3.3) and
MEMORY-ARCHITECTURE.md; docs/GOAL.md overrides both.
"""

__version__ = "0.1.0"


def main() -> None:
    from northstar_agent_memory.cli import main as cli_main

    cli_main()
