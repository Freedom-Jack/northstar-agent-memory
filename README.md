# Northstar

Northstar is a personal memory system for the AI era. It captures what you learn from your own thinking **and what AIs tell and teach you**, and it keeps that knowledge structured and evolving. The system has two architectures over a shared core:
- **For the human:** a structural memory of what has been learned and what to learn next. It is a big-picture index of your ideas, closest to a map, that you glance at before an interview or a decision. An AI assistant expands any entry for the problem at hand, and entries lead to your actual work.
- **For AI assistants:** a memory system for any AI agent or LLM, through connectors (first Claude and ChatGPT, chat and code). It keeps long chats focused on your goal and carries continuity across chats.

AI does all of the maintenance, and the system is designed to stay reliable even when the maintaining agent loses focus.

**The goal is defined in [`docs/GOAL.md`](docs/GOAL.md). That file overrides every other document here.**

## Status

- **Research, round 1: done.** Nine notes and a synthesis in [`docs/research/`](docs/research/). They are reference material. Their reframing conclusions are superseded by `GOAL.md`.
- **Design v0.2: rejected by the user** (2026-10-07). Archived in [`docs/archive/`](docs/archive/2026-10-07-rejected-design-v0.2/README.md).
- **Research, round 2 (goal-anchored): done** (2026-10-08). Five notes and a synthesis in [`docs/research/round2/`](docs/research/round2/SYNTHESIS.md), which passed a goal-fidelity audit. Its questions were carried into the design.
- **Design: done** ([`docs/design/`](docs/design/README.md)). **Adversarial review: done** ([`docs/design/REVIEW.md`](docs/design/REVIEW.md)). The design passed design, adversarial review and goal-fidelity checks on 2026-10-08.
- **Now (2026-10-15): exploring the design again, using probes on real chats.** Read [`docs/EXPLORATION.md`](docs/EXPLORATION.md) after `GOAL.md`. The design documents are earlier proposals; nothing is approved.
- **Build:** not started. `src/` holds only the empty `uv` scaffold.

## Repository map

| Path | What it holds |
|---|---|
| [`docs/GOAL.md`](docs/GOAL.md) | **Read first.** The authoritative goal, the non-negotiables, and the process rules |
| [`docs/design/`](docs/design/README.md) | The design: `ARCHITECTURE.md` (the approval document), `REVIEW.md` (the adversarial review), foundations and component specs |
| [`docs/research/`](docs/research/) | Research notes (round 1: tracks 01–09 and `SYNTHESIS.md`; round 2 in `round2/`) |
| [`docs/archive/`](docs/archive/) | Rejected work, kept for the record only |
| `src/northstar_agent_memory/` | *Planned:* the implementation |

Personal data never goes in this repository.
