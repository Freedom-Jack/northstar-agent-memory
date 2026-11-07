# Northstar

Northstar is a personal memory and focus layer for the AI you already use: Claude, ChatGPT, Codex or any other harness. It is not an AI of its own.

It captures what you and your AIs say. It keeps your knowledge as structured, attributed, evolving memory. It gives new chats the facts they lack. It helps long sessions stay on your goal. It shows you an overview of your ideas. AI does all of the maintenance.

**Status: early build.** The design is settled and three of eight build steps are done. Nothing is installed into your AI tools yet, and the memory itself is not built. See [Status](#status).

**The goal is defined in [`docs/GOAL.md`](docs/GOAL.md). That file overrides every other document here.**

## What Northstar is

People learn through AI chats, research, work and their own thinking. The result piles up as fragments: long chats lose the goal they were started for, and new chats start without what earlier chats established. Northstar is a system for that problem, not a set of habits.

It is designed to do three jobs. Only capture, the first step of the third job, is built, and it is not installed yet (see [Status](#status)).

1. **Focus.** In a long session, your own AI works out what the goal still needs and whether the work is getting worse. It speaks up rarely, answers you first, and acts only on your yes.
2. **Memory.** A new chat gets the facts it lacks, as plain context, and often nothing at all. Northstar adds facts. It does not tell the AI how to behave.
3. **Maintenance.** In the background, capture records every turn word for word, and a maintenance run turns that history into memory, checks it, and logs every change.

What an AI taught you counts as memory once you adopt it, and it stays attributed to the AI. Other AI answers stay in a private, searchable archive and are not memory on their own ([GOAL §4](docs/GOAL.md)).

Two memory structures sit over one shared core, and both are rebuilt from it:

- **For the AI:** short dated lines, search keys and start notes, shaped so the right few facts are found fast.
- **For you:** an overview of your ideas, grouped by topic, with your own words and your actual work under each idea. It comes as chat answers when you ask, with a map on request.

Northstar runs on the AI you already use. Its code holds the memory and checks it. Every judgment is made by your own AI's models, either in your conversation or as hidden background calls through the harness you use: Claude Code's headless mode and Codex's headless mode, on your own plans. The vendors' APIs are an option, not the default. Hidden runs start in an empty folder with hooks off, so they are never captured as your sessions. See [DESIGN §1.4](docs/design/revision-2026-10-23/DESIGN.md).

The design is in [`DESIGN.md`](docs/design/revision-2026-10-23/DESIGN.md) (start with §0, one page). The data structures and algorithms behind it are in [`MEMORY-ARCHITECTURE.md`](docs/design/revision-2026-10-23/MEMORY-ARCHITECTURE.md) (start with §0).

## Status

The design is settled: [`DESIGN.md`](docs/design/revision-2026-10-23/DESIGN.md) version 3.4 is the baseline, and [`MEMORY-ARCHITECTURE.md`](docs/design/revision-2026-10-23/MEMORY-ARCHITECTURE.md) was approved as written. The build follows the eight steps of [DESIGN §10](docs/design/revision-2026-10-23/DESIGN.md). The plan is to build a baseline, then improve it by measuring.

| Step | What | State |
|---|---|---|
| 1 | The measurement harness and the baselines without Northstar | **Done.** Stage 0 has run |
| 2 | The core: six SQLite stores, the event log, the write gate, the invariants | **Done** |
| 3 | Capture for Claude Code | **Built and tested. Not installed yet, and no sessions imported yet** |
| 4 | Maintenance | Next |
| 5 | Memory: delivery to new chats and the recall tool | Later |
| 6 | Focus | Later |
| 7 | The overview | Later |
| 8 | Robustness and the purge saga | Later |

**Stage 0** ran the baselines without Northstar on the user's own plans (results in [`docs/EXPLORATION.md`](docs/EXPLORATION.md)). The judge test passed: 0 of 101 wrong answers accepted on LongMemEval (the judge was weaker on partial answers on the pilot persona). On LongMemEval's development set, no history scored 0%, keyword search 72.5%, a search agent 92.5%, and the evidence itself 100%. With a current model, reading the whole history is already at the ceiling for histories this long, so the bar was recalibrated once: Northstar must close at least half of the gap to the evidence ceiling ([DESIGN §8](docs/design/revision-2026-10-23/DESIGN.md)).

**Not built yet:**

- maintenance, memory delivery and the recall tool, focus, the overview, robustness and the purge saga (steps 4 to 8);
- the Codex and chat-app connectors (Claude Desktop chat, ChatGPT chat);
- Windows.

## Requirements

- macOS. Windows is planned for later.
- Python 3.14 and [uv](https://docs.astral.sh/uv/).
- FileVault turned on. Capture refuses to run without disk encryption.
- For the harness route, which is the default: Claude Code signed in, and the ChatGPT app's Codex signed in.
  - Claude Code's bundled command-line tool needs one sign-in with its `auth login` command. `northstar doctor` prints the exact command for your machine.
  - Codex runs headless on the login of the ChatGPT app.

The measurement tools that make no model calls, and the tests, need neither login.

## Getting started

Install the dependencies:

```bash
uv sync
```

Check the setup:

```bash
uv run northstar doctor
```

`doctor` only reads. It prints:

- the data root, the settings file and the FileVault status;
- the six stores, each present or not, with its schema version and size;
- the capture status (see below);
- the route for hidden model calls (harness or api), and where each harness program was found and whether it is signed in;
- where an API key would come from for each vendor, without showing it;
- the models configured for each role.

## Using what is built

[`docs/PROTOTYPE.md`](docs/PROTOTYPE.md) has the detail. This is the short version. Every command accepts `--help`.

### Measuring

The harness measures memory systems against published benchmarks and a scripted persona, starting with the baselines without Northstar.

Verify a downloaded LongMemEval file and fix its development and test subsets. Get `longmemeval_s_cleaned.json` from the benchmark's public release:

```bash
uv run northstar eval lme prepare --file longmemeval_s_cleaned.json
```

Print the cost estimate for a run, and stop. Always do this first:

```bash
uv run northstar eval run --dataset lme --answerer-family anthropic --judge-family openai --dry-run
```

Test a judge on wrong-but-on-topic answers. A judge must pass this before its scores count:

```bash
uv run northstar eval judge-check --judge-family openai --generator-family anthropic
```

Run the baselines (`none` and `B0` to `B4`), then print the tables for the run:

```bash
uv run northstar eval run --dataset lme --answerer-family anthropic --judge-family openai --systems none,B1,B2
```

```bash
uv run northstar eval report --run RUN_ID
```

A judge never scores its own vendor's answers, and a look at the held-out split needs `--held-out`, a clean work tree and a passing judge check. These runs call real models on your plans, so read the dry-run estimate first.

Compute measures from normal use (context fill, continued chats, corrections) from a folder of Claude Code transcripts. This makes no model calls:

```bash
uv run northstar eval normal-use --projects-dir FOLDER
```

### Capture

Capture records what is said in your Claude Code sessions, both sides, word for word. It is built and tested but **not installed in anything**: nothing is captured until you install it.

**Installing capture changes your Claude Code settings. Do it only deliberately, with your own go-ahead.** Always use `--dry-run` first.

Capture only works on personal folders. List them as `[capture] personal_paths` in `<data root>/settings.toml`. With none listed, nothing is captured.

See what an import would do. This counts sessions in and out of scope and messages, and stores nothing:

```bash
uv run northstar capture backfill --from FOLDER --dry-run
```

`FOLDER` is laid out like Claude Code's own projects folder. The command stops with an error until `[capture] personal_paths` names at least one folder. A real backfill is the same command without `--dry-run`. It is a one-time import of saved sessions, and running it again writes only what is new.

See what an install would change, without changing anything:

```bash
uv run northstar capture install --settings PATH --dry-run
```

`--settings PATH` merges the hooks into the settings file you name and keeps a timestamped backup beside it. `--plugin-dir PATH` instead writes a plugin folder and prints the commands that add it. There is no default path. Use one of the two, not both.

Look at capture's state (reads only), drain the spool into the history store by hand, and remove only Northstar's hooks:

```bash
uv run northstar capture status
```

```bash
uv run northstar capture ingest
```

```bash
uv run northstar capture uninstall --settings PATH --dry-run
```

To try capture from a checkout without touching your settings, see [`plugin/README.md`](plugin/README.md).

## Privacy

This repository is public and holds no personal data.

- **Where data lives.** On your Mac only. The data root is `~/Library/Application Support/Northstar` and holds the stores, the settings and evaluation results. The cache root is `~/Library/Caches/Northstar` and holds public benchmark downloads. Set `NORTHSTAR_HOME` to move both to a temporary folder for tests or for trying a command safely.
- **What never enters the repository.** Chats, evaluation results computed from your chats, stores and settings. Result files are written under the data root, and the commands refuse to write them inside a git work tree unless you pass `--allow-repo-path`. `.gitignore` also excludes `*.sqlite`, `runs/`, `normal_use/` and `settings.toml`.
- **Secrets are removed before anything is written.** Keys, tokens, passwords and private keys are replaced with a marker, in the spool and in the database.
- **Only personal folders are captured.** A session outside the folders you list is ignored without a trace.
- **Northstar's own runs are never captured.** Hidden harness runs start in an empty folder under the data root and carry a marker that stops the hooks. The data root itself is never in scope.
- **Capture makes no model calls.** It is plain code. Only hidden background calls and measurement runs send text to a model, through the harness you use.

## Repository map

| Path | What it holds |
|---|---|
| `src/northstar_agent_memory/models/` | Model access through one port: the vendors' APIs, or Claude Code and Codex headless (the default), with recording and metering |
| `src/northstar_agent_memory/eval/` | The measurement harness: LongMemEval subsets, baselines, judges, scoring, the pilot persona, measures from normal use |
| `src/northstar_agent_memory/core/` | The six stores, the event log, the write gate and the invariants |
| `src/northstar_agent_memory/capture/` | Capture for Claude Code: hook client, spool, ingester, scope gate, secret removal, turn origin, backfill, work events, install |
| `src/northstar_agent_memory/config/` | Versioned starting values (`defaults.toml`), overridden by your own `settings.toml` |
| `src/northstar_agent_memory/cli.py` | The `northstar` command |
| `plugin/` | A Claude Code plugin for trying capture from a checkout ([`plugin/README.md`](plugin/README.md)) |
| `tests/` | The tests, one folder per area |

| Docs | What it holds |
|---|---|
| [`docs/GOAL.md`](docs/GOAL.md) | **Read first.** The authoritative goal, the user's answers, the non-negotiables and the process rules |
| [`docs/design/revision-2026-10-23/DESIGN.md`](docs/design/revision-2026-10-23/DESIGN.md) | The current design (version 3.4, the baseline) |
| [`docs/design/revision-2026-10-23/MEMORY-ARCHITECTURE.md`](docs/design/revision-2026-10-23/MEMORY-ARCHITECTURE.md) | The data structures and algorithms behind it (approved as written) |
| [`docs/EXPLORATION.md`](docs/EXPLORATION.md) | Where the exploration stands, the Stage 0 record, and aggregated probe findings |
| [`docs/PROTOTYPE.md`](docs/PROTOTYPE.md) | How to use what is built, in detail |
| [`docs/research/`](docs/research/) | Research notes, rounds 1 to 6 |
| [`docs/design/`](docs/design/README.md) | The earlier proposal of 2026-10-09, kept as a component library |
| [`docs/archive/`](docs/archive/) | Rejected work, kept for the record only |

## Development

Run the tests:

```bash
uv run pytest -q
```

They run offline in about a minute (3,153 passed at the time of writing). Guards in `tests/conftest.py` keep them safe:

- every test gets a throwaway data root through `NORTHSTAR_HOME`, never the real one;
- no API keys reach a test, and the Keychain is off;
- no test can find, start or read the login of the real Claude Code or Codex. A test that needs a run fakes the process.

When a change touches a design question, check it against [`docs/GOAL.md`](docs/GOAL.md). It overrides every other document, including this one.

Personal data never goes in this repository, which is public.
