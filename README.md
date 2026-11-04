# Northstar

Northstar is a personal memory system for the AI era. It captures what you learn from your own thinking **and what AIs tell and teach you**, and it keeps that knowledge structured and evolving. It is a memory and focus layer for the AI you already use, with two architectures over a shared core:
- **For the human:** a structure of your own ideas and your work: what you have learned, from yourself and from AIs, and what you are working toward. You reach it in the assistant you use. Questions about your past and "where did I leave this?" come back as chat answers that quote your record, and the big picture opens as a map on request.
- **For AI assistants:** a memory system for any AI agent or LLM, through connectors (first Claude and ChatGPT, chat and code). It keeps long chats focused on your goal and carries continuity across chats.

AI does all of the maintenance, and the system is designed to stay reliable even when the maintaining agent loses focus.

**The goal is defined in [`docs/GOAL.md`](docs/GOAL.md). That file overrides every other document here.**

## Status

- **Research, round 1: done.** Nine notes and a synthesis in [`docs/research/`](docs/research/). They are reference material. Their reframing conclusions are superseded by `GOAL.md`.
- **Design v0.2: rejected by the user** (2026-10-07). Archived in [`docs/archive/`](docs/archive/2026-10-07-rejected-design-v0.2/README.md).
- **Research, round 2 (goal-anchored): done** (2026-10-08). Five notes and a synthesis in [`docs/research/round2/`](docs/research/round2/SYNTHESIS.md), which passed a goal-fidelity audit. Its questions were carried into the design.
- **Design of 2026-10-08 and 2026-10-09: done, then re-explored.** It passed design, adversarial review ([`docs/design/REVIEW.md`](docs/design/REVIEW.md)) and goal-fidelity checks, and is now a component library ([`docs/design/`](docs/design/README.md)).
- **Probes on real chats and research rounds 3 to 6: done** (2026-10-10 to 2026-10-28). The findings are in [`docs/EXPLORATION.md`](docs/EXPLORATION.md), aggregated with no personal content, and the notes are in [`docs/research/`](docs/research/).
- **Design: settled** (2026-10-28). [`DESIGN.md`](docs/design/revision-2026-10-23/DESIGN.md) version 3.4 is the baseline (version 3.3 of 2026-10-28, with the route revised on 2026-10-29): three jobs (focus, memory and maintenance) over one core. [`MEMORY-ARCHITECTURE.md`](docs/design/revision-2026-10-23/MEMORY-ARCHITECTURE.md), the data structures and algorithms behind it, was approved as written. From here, research decides the design, not the user's reactions.
- **Now: building the baseline prototype** in Claude Code on this Mac (DESIGN §9), in the order of DESIGN §10, starting with the measurement harness and the baseline without Northstar. It is measured with published benchmarks, automatic checks and measures from normal use (DESIGN §8), then improved by measuring. Its hidden model calls run on the user's own AI plans through the harness they use, Claude Code and Codex, not on separate API keys (DESIGN §1.4, version 3.4).

## Repository map

| Path | What it holds |
|---|---|
| [`docs/GOAL.md`](docs/GOAL.md) | **Read first.** The authoritative goal, the user's answers, the non-negotiables, and the process rules |
| [`docs/design/revision-2026-10-23/`](docs/design/revision-2026-10-23/DESIGN.md) | **The current design:** `DESIGN.md` (version 3.4, the baseline) and `MEMORY-ARCHITECTURE.md` (approved 2026-10-28) |
| [`docs/EXPLORATION.md`](docs/EXPLORATION.md) | Where the exploration stands: probe findings (aggregated) and the history of the design rounds |
| [`docs/research/`](docs/research/) | Research notes, rounds 1 to 6 |
| [`docs/design/`](docs/design/README.md) | Earlier proposals of 2026-10-08 and 2026-10-09 (`ARCHITECTURE.md`, the revision documents, foundations and component specs), kept as a component library |
| [`docs/archive/`](docs/archive/) | Rejected work, kept for the record only |
| `src/northstar_agent_memory/` | The implementation, being built |

Personal data never goes in this repository, which is public.
