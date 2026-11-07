# The Northstar prototype: what is built and how to use it

**As of 2026-11-07.** This page is the reference for the code in `src/northstar_agent_memory/`. It says what exists, how it works, how to run it, and what does not exist yet. It describes the build, not the design: [`GOAL.md`](GOAL.md) is the goal and overrides everything, [`DESIGN.md`](design/revision-2026-10-23/DESIGN.md) (version 3.4) is the design, and [`MEMORY-ARCHITECTURE.md`](design/revision-2026-10-23/MEMORY-ARCHITECTURE.md) holds the data structures and algorithms. Where this page and those disagree, they win.

## In short

Northstar is meant to be a personal memory and focus layer for the AI you already use. It captures what you and your AIs say, keeps your knowledge as structured, attributed memory, gives new chats the facts they lack, helps long sessions stay on the goal, and shows you an overview of your ideas. AI maintains all of it.

**Today, three of the eight build steps are done.**
- You can measure how well plain memory baselines (no Northstar) answer questions about past chats. That is step 1.
- The six stores, the event log and the write gate exist and are tested. That is step 2. Nothing writes memory into them yet.
- Capture for Claude Code exists and is tested. That is step 3. **It is not installed in any Claude Code, and no real sessions have been imported.**

**Not built yet:** maintenance (step 4), memory delivery and the recall tool (step 5), focus (step 6), the overview (step 7), robustness and the purge saga (step 8), the Codex and chat-app connectors, and Windows. Nothing in Northstar gives a chat any memory yet.

All commands below run from the repository root. They need [uv](https://docs.astral.sh/uv/) and Python 3.14 (uv fetches it). Run `uv sync` once first.

---

## 1. How the build is organized

DESIGN §10 sets eight steps, in this order. The rule is: **each part passes its own tests and automatic checks before the next part starts.**

| Step | Part | Status |
|---|---|---|
| 1 | Measurement harness and the baselines without Northstar | Built and tested. Stage 0 has run. |
| 2 | Core: six stores, event log, write gate, invariants | Built and tested |
| 3 | Capture for Claude Code | Built and tested. Not installed; no sessions imported. |
| 4 | Maintenance: extract, integrate, refresh, check, rebuild, log; weekly restructuring; scheduled job | Not built |
| 5 | Memory: search, routing, start notes, the strict gate, refill, the recall tool | Not built |
| 6 | Focus: working memory, moments, the note, the blind check, the moves | Not built |
| 7 | Overview: chat answers, the map card, the outline | Not built |
| 8 | Robustness: quarantine, rollback, the full fault suite | Not built |

The harness is first on purpose. DESIGN §8 says every measure is taken without Northstar before it is taken with it, so the baseline must exist before there is anything to compare.

**How each part was built and checked.** Each part was written in stages against the design, with its tests, and was reviewed against the design and the goal before it counted as done. The test suite (section 7) is what remains of that work. The attack tests against the write gate (`tests/core/test_attacks.py`, `test_gate_attacks.py`) are one example: they forge proposals and check that the gate refuses them.

---

## 2. Step 1: the measurement harness

Code: `src/northstar_agent_memory/models/` (model access) and `src/northstar_agent_memory/eval/` (measurement). Design: DESIGN §8.

### What it measures, and why

The harness answers one question first: how well does a system answer questions about past chats **without** Northstar? Northstar has to beat that, and "beat" has to mean something.

DESIGN §8 in brief:
- **Three kinds of evidence.** Published benchmarks where one exists, automatic checks where none does, and measures from your normal use. Your own picks decide nothing.
- **Baselines, all run in the same harness.** Each gets the same fixed answering prompt, so only the context differs.

  | System | What the model sees |
  |---|---|
  | `none` | No history at all (closed book). Finds the questions that need memory. |
  | B0 | The whole history, where it fits. Reported with its cost. |
  | B1 | Keyword search (BM25, a standard keyword-ranking formula) over the chat rounds, within the token budget. Vector search is a hook, not on by default. |
  | B2 | A search agent that greps and reads the raw history itself, in a JSON action loop. |
  | B3 | Only the evidence. The ceiling. |
  | B4 | An append-only dated log of observations written session by session. The cheapest serious competitor. |

  B1 to B4 get the same token budget (8,000, `[eval] token_budget`). What a system is shown carries nothing of the answer: sessions have opaque ids, and only B3 reads the evidence ids.
- **Questions that need memory.** A question counts toward the headline only if the model fails it with no history and passes it with the evidence.
- **Paired bars.** Every comparison is on the same items, with a 95% confidence interval of the difference (from resampling the items). Each bar is fixed before the data it judges.
- **Gap closure.** After the pilot, DESIGN §8 recalibrated the bar once, before any held-out result. Northstar must close at least half of the gap between the best of B1, B2 and B4 and the evidence ceiling B3, with the interval of its difference from that best baseline above zero. The earlier bar ("10 points above the best simple baseline") could not be met by any system.
- **The judge test.** An AI judge counts only after it accepts fewer than 1 in 10 answers that are wrong but on topic. A judge never scores its own model family's work.
- **Held-out sets** run last. The sizes are fixed in DESIGN §8.
- **Scoring pieces.** HaluMem-style scoring of extraction, update and answering, and ALCE-style citation precision and recall, are written and tested (`eval/metrics.py`). They have nothing to score until maintenance exists.

### The datasets

| Dataset | What it is | Split sizes |
|---|---|---|
| LongMemEval_S | A published benchmark of long chat histories with questions. The code verifies the file against its published checksum and renames the sessions so ids cannot leak the answer. | Development: 10 each of knowledge-update, temporal-reasoning, multi-session and single-session-user, plus 10 abstention questions (50). Held-out: 62, 60, 30 and 30 of those types in that order, plus 20 abstention. Set in `defaults.toml`. |
| Pilot persona | An invented person: 32 sessions covering the 18 scripted scenarios of research note 09, with 59 probes (28 current-state, 12 attribution, 9 history, 5 stale-premise, 5 abstention). Most scoring is by code because the hidden record holds the truth. | Development only. There is no held-out pilot yet. |

The scenarios, the persona files and the probes are in `eval/scenarios/` (invented content only).

### The model route

All hidden model calls go through one port, `ModelPort.complete(ModelRequest) -> ModelResult` (`models/port.py`). A request names its purpose, a role (`answerer`, `judge`, `worker`, `worker_small`, `checker`, `sim_user`), a family (`anthropic` or `openai`; `stub` for tests) and, if wanted, a strict JSON schema. The model ID comes from `defaults.toml`, per family and role. There are no sampling parameters.

**Two routes** (DESIGN §1.4, revised 2026-10-29), chosen by `route.default` in config:
- **`harness` (the default).** Claude Code's headless mode runs Claude models, and Codex's `exec` runs ChatGPT's models, on your own plans. There is no API key and no dollar bill.
- **`api`.** The vendors' APIs with your keys, metered in dollars. It is kept as an option and as a fallback.

**Layers.** `build_port` (`models/registry.py`) stacks three wrappers around an adapter:

| Layer | File | What it does |
|---|---|---|
| Budget guard | `models/budget.py` | On the `api` route only: refuses a live call when no monthly hard cap is set (`budget.monthly_hard_usd`), or when the call could pass the hard cap or the run's budget. Warns once past the soft cap. Writes every live call to the cost ledger. |
| Recorder | `models/recorder.py` | Stores each result before anyone reads it, and never regenerates it. The key is the family, the resolved model, the system prompt, the messages, the schema, `max_tokens`, effort, the sample number and, on the harness route, the route. The two routes never replay each other's answers. A rerun costs nothing. |
| Router | `models/registry.py` | Sends the request to the adapter for its family and route. |

**The harness adapters** (`models/harness_claude.py`, `models/harness_codex.py`, shared parts in `models/harness.py`):
- **One call, one process.** The prompt goes in on standard input. The answer is read from the program's JSON output.
- **Isolated.** Every run starts in an empty folder (`<data root>/harness-cwd`) with hooks off, no tools and no saved transcript. Claude Code runs with `--no-session-persistence` and `--safe-mode`, with its system prompt replaced. Codex runs read-only with `--ephemeral`, hooks off and web search off, and with switches that cut its prompt to a lean one.
- **On the plan login.** API-key variables are removed from the program's environment, so it cannot fall back to a key.
- **Marked as Northstar's own.** Each run carries `NORTHSTAR_HIDDEN_RUN=1`, so capture never records it as your session (see section 6).
- **Cost.** A plan has no dollar bill, so `cost_usd` is 0.0. Claude Code's own estimate at API list prices is kept in the ledger as `api_equivalent_usd`, for information only.
- **Failures** are sorted from the program's own words: not signed in, plan limit reached, model unavailable, refusal, or other. A call stops after `[harness] timeout_s` seconds (600).

**Plan limits stop a run.** A plan limit, a missing sign-in, or an unavailable model stops the whole run, because every later call would fail the same way. The run folder keeps what finished, and the same command with `--run-id` resumes it after the reset. Measurement runs set the prompt cache and the server-side refusal fallback off, so the model asked for is the model that answers.

### The commands

Every command below was checked with `--help`. A dry run comes first wherever one exists. Use a throwaway data root while trying things out: `export NORTHSTAR_HOME=$(mktemp -d)` moves everything Northstar writes there.

**`doctor`** reports the data root, the six stores, encryption at rest, the route, whether the Claude Code and Codex programs are found and signed in, key status, cost caps and the model for each role. It changes nothing.

```bash
uv run northstar doctor
```

**`models check`** lists the model IDs your API keys can reach and flags configured models that are missing. It matters only on the `api` route and makes a network call to the vendor's list endpoint, but runs no model.

```bash
uv run northstar models check --family anthropic
```

**`eval lme prepare`** checks a LongMemEval_S file against its published checksum and fixes the development and held-out subsets with a fixed seed. Download `longmemeval_s_cleaned.json` from the benchmark's authors first; the code looks for it under `<cache root>/bench/longmemeval/`, and the command takes any path.

```bash
uv run northstar eval lme prepare --file <path to longmemeval_s_cleaned.json>
```

**`eval run`** answers and judges a dataset with the baselines. Start with the dry run, which prints a cost estimate from token counts and calls no model:

```bash
uv run northstar eval run --dataset pilot --answerer-family anthropic --judge-family openai --dry-run
```

It begins with a line like `dry run: 59 pilot dev items, systems none, B0, B1, B2, B3, B4; no model is called`, then a table of calls and tokens per system. The table shows dollars at API prices, even on the harness route, where nothing is billed. Its line "more than the run budget" is advice for the `api` route and does not stop a harness run. (A `lme` dry run needs `eval lme prepare` first.) Then run it for real, here on 10 items:

```bash
uv run northstar eval run --dataset pilot --answerer-family anthropic --judge-family openai --limit 10
```

Things to know:
- The judge must be of another family than the answerer (`--allow-same-family` is for tests).
- `--systems none,B3` runs some baselines only. The default is all six.
- `--limit N` takes N items spread over the question types. `--workers` sets parallelism (default 4).
- `--replay-only` uses recorded calls and never calls a model.
- `--budget-usd` limits an `api` run. It does not apply on the harness route.
- Exit code: 0 done, 1 some items failed, 2 stopped early. A stopped or failed run prints the command to resume it with `--run-id`.
- A run on the held-out split needs `--split test --held-out`. It also needs a clean git work tree and a passing judge check for the run's judge model and prompt, and it is logged in `<data root>/eval/held-out-ledger.jsonl`. Look at the held-out data once, last. A dry run on the test split is allowed without `--held-out`:

```bash
uv run northstar eval run --dataset lme --split test --answerer-family anthropic --judge-family openai --dry-run
```

**`eval judge-check`** tests a judge on wrong-but-on-topic, partial, vague and stale answers that the other family writes. It passes only if the judge accepts under 10% of at least 60 wrong answers and accepts at least 85% of right ones. The default is 40 items. On LongMemEval it needs `eval lme prepare` first; `--dataset pilot` needs nothing.

```bash
uv run northstar eval judge-check --judge-family openai --generator-family anthropic --dataset lme
```

**`eval normal-use`** computes measures from Claude Code transcripts with no model call: sessions and active days per week, which sessions continue earlier work and which start fresh, how full the context got, and candidate re-explanations and corrections. It refuses a whole home folder or disk root, so name the folder that holds the transcripts.

```bash
uv run northstar eval normal-use --projects-dir <folder of Claude Code transcripts>
```

**`eval report`** turns a run folder into tables (`report.md` and `report.json` beside the run's files).

```bash
uv run northstar eval report --run <run id>
```

The report is paired and per system. It uses only the items the compared systems all finished. It carries an INCOMPLETE banner if a system fell short. It shows the questions that need memory, tokens, dollars at API prices and latency. Scores count only when the run's judge passed its own test with the same model and prompt.

### Where results go

Everything is under `<data root>/eval/` (see section 6):

| Path | Holds |
|---|---|
| `runs/<run id>/` | `run.json` (a fingerprint of config, models, prompts and git commit; a resume that differs is refused), `predictions.jsonl`, `judgements.jsonl`, `judge-check.json`, `judge-probes.jsonl`, `report.md`, `report.json` |
| `model-calls.sqlite` | Every recorded model request and result (the recorder) |
| `cost-ledger.sqlite` | Every live call: tokens, route, cost, latency, outcome |
| `lme_manifest.json` | The chosen LongMemEval subsets |
| `normal_use/` | Reports from `eval normal-use` |
| `held-out-ledger.jsonl` | One line per look at held-out data |

Runs that hold text from your chats are personal data. The commands refuse to write a run folder or report inside a git work tree unless you pass `--allow-repo-path`.

### Stage 0: what the first run found

Stage 0 ran on 2026-11-04 on the author's own plans through Claude Code and Codex headless. Claude Opus 5.5 answered. GPT-6.1 Sol judged, 8 answers a call. These numbers are copied from [`EXPLORATION.md`](EXPLORATION.md); the runs themselves stay in the data root.

- **Judge test: passed.** LongMemEval: 0 of 101 wrong answers accepted (95% upper bound 3.7%), 40 of 40 right ones accepted. Pilot persona: 8.7% of 115 wrong answers accepted, under the 10% bar, but 28.6% of partial answers, a weak spot.
- **LongMemEval_S, development set (50 questions; 40 need memory):** no history 0%; B1 keyword search 72.5%; B2 search agent 92.5%; B3 the evidence 100%. On 15 questions (11 need memory): B0, the whole history, 11 of 11 at about 143,000 tokens a question; B4, an observation log, 9 of 11.
- **Pilot persona (59 probes; 46 need memory):** B0 97.8%, B1 93.5%, B2 89.1%, B4 80.4%. The weakest kinds are attribution (B4 50%, B2 67%) and how views changed (B2 67%). Six probes failed even with the evidence.
- **Normal use before Northstar** (from the author's sessions, code only): 68 sessions on 24 active days over 4 weeks; 55 continue earlier work and 13 start fresh; 24 passed half the context window.
- **What it means.** With a 2026 model, reading the whole history is at the ceiling for histories of this length, and simple search is close behind. Northstar's measurable room is in judgment-heavy questions (attribution, how views changed), in the tokens read per question, and in histories longer than the window. That is why DESIGN §8 changed the bar to gap closure.

### Known limits

- **Gap closure is decided but not in the code.** `defaults.toml` still holds `lme_margin_points = 10`, and `eval/report.py` still applies the old "at least N points above" bar. EXPLORATION lists this as a follow-up.
- **Other follow-ups from Stage 0 (EXPLORATION):** audit the six probes that failed with the evidence, using the other model family; tighten the judge on partial answers; show plan usage, with cached tokens, in the report.
- **No held-out pilot persona.** The pilot is a development set; DESIGN §8 plans one held-out persona.
- **Published sets not built:** HaluMem-Medium, Laban et al.'s sharded tasks and MT-Bench's human judgments (DESIGN §8).
- **Vector search** is a hook in B1, not wired in. It waits for the local search model.
- **No Northstar arm yet.** Memory does not exist, so there is no "with Northstar" run.
- **Normal-use labelling.** `eval normal-use` counts candidate re-explanations by code. The model step that labels them, which counts only when it quotes your words, is not run by the command, and is to be used once the detector passes its own check.
- **Claude Code transcripts only.** There is no reader for Codex or chat-app history.
- **Codex does not say which model answered,** so `served_model` there is the model asked for.
- **Background work does not yet wait while you are in a session.** DESIGN §1.4 says maintenance will. Only the stop-at-first-limit rule exists, in measurement runs.

---

## 3. Step 2: the core

Code: `src/northstar_agent_memory/core/`. Design: MEMORY-ARCHITECTURE §2, §3, §5.9 and §7. The core makes no model call. Code decides, and models only propose.

### The six stores

Each store is one SQLite file under the data root, with one writer. `open_store(name)` opens it with the right SQLite settings and applies pending schema migrations (the schema files are `core/schema/<store>.sql`). Canonical stores sync fully to disk. Every row carries a `tenant_id` (`local` now) to leave room for a later cloud version.

| Store | Holds | Written by | Adapter | Built so far |
|---|---|---|---|---|
| `history.db` and `blobs/` | Chat history word for word: sources, messages, work events, snapshots | Capture | `SQLiteHistoryStore` | Complete for what capture needs. Append-only: triggers refuse update and delete. |
| `memory.db` | Memory: the event log, items, evidence, links, supersessions, conflicts, goals and questions, your work, working style, corrections, scopes, topics and placements | The write gate only | `WriteGate`, `Projector`, `SQLiteMemoryReader` | Complete for the gate. No stage proposes to it yet. |
| `working.db` | Work in progress: threads, sessions, live decisions, versions with your feedback, side topics, delivery receipts | The live writer | `SQLiteWorkingStore` | Storage only. Never a source for memory. |
| `index.db` | The AI index: item lines, keys, link view, goal cards, start notes, use counts, the gate's bar per project | The maintenance rebuild | `SQLiteIndexStore` | Storage and keyword (BM25) search. No builder. |
| `overview.db` | The human structure: topic and idea views, suggestions, open items, where you left off, layout, marks | The maintenance rebuild and your viewing | `SQLiteOverviewStore` | Storage only. No builder. |
| `runs.db` | Maintenance runs: jobs with locks, recorded model calls, proposals, verdicts, quarantine, error budgets, the change log | Maintenance | `SQLiteRunStore` | Storage and rules. No maintenance runs yet. |

The stores are reached through seven ports (`core/ports.py`). A contract test checks that each SQLite adapter matches its port, so a Postgres adapter can replace it later.

### The event log

`memory.db` changes only by appending events. There are 42 event types in 12 families (`core/events.py`):

| Family | Types (count) |
|---|---|
| evidence | `evidence.anchored` (1) |
| items | created, revised, value changed, scope widened, status changed, checked (6) |
| your moves | `stance.recorded` (1) |
| links | proposed, applied, confirmed, rejected, retracted (5) |
| supersession | applied, undone (2) |
| conflicts | opened, resolved, reopened, undone (4) |
| goals and questions | goal created, status changed, confirmed; question created, status changed (5) |
| your work | registered, labelled (2) |
| working style | recorded, revised (2) |
| corrections | applied, lifted (2) |
| structure | topic created, split, branched, merged, folded back, renamed, dormant; idea placed, moved (9) |
| maintenance and privacy | compensation batch, purge applied, scope hold changed (3) |

The **projector** turns events into current-state rows and keeps row history, so any past state can be read ("as of" a sequence number or a time) through `SQLiteMemoryReader`. It is deterministic: it reads only the database and the event, with no clock and no randomness. Some fields are **stamped**, not proposed: the speaker, agent, model family, origin and context of a quote are copied by the gate from chat history, so a proposal cannot claim them (I3, I20).

**Replay** (`core/replay.py`): `rebuild` replays every event into a fresh database, and `verify_replay` compares its hash with the live one and lists which rows differ (I18). They are functions. No command or schedule runs them yet.

### The write gate

`WriteGate` (`core/gate.py`) is the only writer of `memory.db`. A stage hands it a `Proposal`, which is a list of draft events with their evidence quotes, the objects it read as `object@version`, and its run and proposal ids. The gate checks in this order and then writes in one transaction, or says why not:

| # | Check | Result if it fails |
|---|---|---|
| 0 | **Replay:** this proposal was applied before | `duplicate`, nothing changes (I14) |
| 1 | **Intake:** every op matches its versioned schema, carries no stamped field and this run's key; no op claims to be yours | `rejected` |
| 2 | **Fencing:** the run is still the current run in `runs.db`, so an old or replaced run cannot write | `rejected` |
| 3 | **Freshness:** nothing the proposer read has changed | `requeued`, not failed |
| 4 | **Freezes:** the change type is not frozen by an error budget or a sentinel | `rejected` |
| 5 | **Code checks:** the invariants, and your corrections | `rejected` |
| 6 | **Verification** for the op's risk tier, from verdicts recorded in `runs.db` | `rejected` |
| 7 | **Caps and the loss bound:** a run may retire at most 5% of active items (at least 1) | `held` for a second check |
| 8 | **One transaction:** stamp, append events with the run key, project | `rejected` (`projection`) if the store refuses |

This is MEMORY-ARCHITECTURE §5.9's order, with replay and intake added in front. The gate never trusts what a proposal says about itself.

**Risk tiers.** Low changes (evidence, refresh, a placement in an existing topic) need only the code checks. Medium changes (a new item from your move, an adoption, some links) need one passing check by a family other than the one that did the work or said the claim. High changes (supersede, merge, a conflict, a widened scope, any topic change, a rollback) need a full-effort check by the other family. Where no other family is left, the check is labelled "not independent" and the change still applies; the families allowed are `[maintenance] check_families`.

**User authority.** Your own marks (a correction, a confirmation, a purge) reach the gate only through `apply_user(proposal, UserAuthority(surface, user_action=True))`. The surface is `capture`, `ui` or `cli`. A model's proposal that names the actor `user` is refused at intake. Your marks need no model verdict and are exempt from caps and freezes, but the code checks still apply. Nothing in the package builds a `UserAuthority` yet; only tests do.

### The invariants

`core/invariants.py` holds the table `INVARIANTS`, with the 25 invariants of MEMORY-ARCHITECTURE §7 (I8 was dropped with the Book and I22 merged into I5) and what enforces each. The gate runs the checks on every proposal. `sweep(stores)` runs the checks after the fact over whole stores, read-only.

| Enforced now (gate, sweep, trigger, capture or replay) | Left to later steps |
|---|---|
| I1 evidence exists; I2 exact quotes; I3 speaker and origin come from capture; I4 "adopted" needs your words; I5 goals, style lines and corrections need your words; I6 append-only; I7 no derived input; I12 a merge needs an exact key or two families; I13 caps and loss bound; I14 replay applies nothing twice; I15 versioned schemas; I16 time order; I17 everything has a scope (gate and sweep); I20 origin never changes; I21 your corrections bind; I24 Northstar's own text is marked at capture | **Rebuild:** I9 nothing leaves the index or the structure without a reason; I27 links Northstar found are not shown until you confirm. **Extraction:** I10 hedges cap certainty; the extraction half of I11. **Delivery:** I25 views, principles and working style are never pushed; the delivery half of I17 (a push stays inside its scope). **Structure:** I26 no structural change reversed within its dwell. **Lint:** I19 and I23 are only partly covered. |

I18 (replay) is built as a function. For I19, a test keeps the numbers in `defaults.toml` equal to the numbers the code holds. For I23, a test checks that two core files name no product.

### How other parts must call it

- **Proposals are saved first.** A stage records its proposal in `runs.db` (`save_proposal`), then asks the gate to apply it. Verdicts come from `runs.db` too, not from the proposal.
- **Model calls are recorded before they are read.** A model's raw output goes into `runs.db` (`record_call`), keyed by a prompt hash, and is never regenerated. A verdict (`record_verdict`) must name a recorded call of this run, by the family it states. A verdict that names no call is stored and backs nothing.
- **Typed inputs only.** Extraction, integration and abstraction must not read overview text, start notes, the change log or earlier model output (I7). `read_change_log` exists for audits, and typed input assembly must never call it.
- **Working memory is never evidence.** `working.db` has no method that returns text shaped for the gate.
- **The glue is not built.** The link between the model port's recorder (`eval/model-calls.sqlite`) and `runs.db` belongs to maintenance (step 4).

### Known limits

- No command reads or writes `memory.db`. `doctor` only reports which stores exist.
- `SQLiteIndexStore.search` returns the keyword list only. The link, meaning and time lists, their fusion and the near-duplicate drop come with the index builder.
- The purge saga of MEMORY-ARCHITECTURE §3.4 is not built. The pieces it needs exist: the `purge.applied` event, which stubs items and scrubs quotes, and `authorize_purge` in `history.db`.
- The schema and the contract assume SQLite. A Postgres adapter, and the cloud swap, are later.

---

## 4. Step 3: capture for Claude Code

Code: `src/northstar_agent_memory/capture/` and the `plugin/` folder. Design: MEMORY-ARCHITECTURE §2.2 and §5.2, and `docs/design/components/connectors-claude-code-and-codex.md`.

**It is built and tested. It is not installed in the author's Claude Code, and no real sessions have been imported.** Nothing is captured until you install it, name your personal folders, and the data folder passes the encryption check.

### The flow

```
Claude Code event -> hook -> spool (day files) -> ingester -> history.db
                                                     ^
                                  reconciles against Claude Code's transcript files
```

1. **The hook** (`capture/hook.py`) is `python -m northstar_agent_memory.capture.hook <event>`. Claude Code runs it for seven events and passes the event's JSON on standard input. It never blocks the session. It uses no database, network or model, prints nothing, and always exits 0. A watchdog ends it after 1.0 s for `UserPromptSubmit`, 0.4 s for `SessionEnd` and 0.75 s for the rest. In order, it:
   1. exits at once for a hidden run or an out-of-scope folder;
   2. writes nothing if there is no valid encryption stamp;
   3. for events that carry text, first writes a marker record with no text, then replaces secrets, then writes the record;
   4. starts the ingester in the background unless one is running.
2. **The spool** (`capture/spool.py`) is append-only day files at `<data root>/spool/claude-code/<UTC date>.jsonl`, owner-only (folders 0700, files 0600). A hook appends one line and exits. A torn last line is left alone until it is finished, and a bad line is counted and skipped without losing good ones. The marker record exists so that a hook killed mid-scrub still leaves the turn known, and reconciliation can fetch it from the transcript.
3. **The ingester** (`capture/ingest.py`) is the one writer of `history.db`. One runs at a time (a lock file). It drains the spool, writes sources and messages through `SQLiteHistoryStore`, reconciles, records work events, and exits.
4. **`history.db`** holds the result: one source per session (kind `chat`, app `claude-code`, scope `project:<repository>`), and every message word for word with its speaker, origin, agent and model family set from Claude Code's own roles, never inferred.

The hooks capture these events: `SessionStart`, `UserPromptSubmit`, `Stop` (the assistant's final text for the turn), `SubagentStop` (kept on its own branch), `PreCompact`, `PostCompact` (only a note that it happened, never the summary, which is a model's text) and `SessionEnd`. Only named fields are kept. Tool inputs and the rest of each payload are never spooled.

Ingest is safe to repeat: running it twice stores nothing twice. Each message carries its spool record's id, and a record already stored is skipped. A record that conflicts with what is stored is logged and skipped, never overwritten.

### The scope gate

Only a session whose working folder is inside one of your personal folders is captured. Everything else is ignored silently: no spool line, no log line.
- The folders are `[capture] personal_paths` in `<data root>/settings.toml` (section 5). `~` is allowed.
- The working folder is resolved first (symlinks followed), so a link inside a personal folder that points out does not count.
- A git worktree under a personal repository counts.
- Comparison ignores case on macOS and Windows, as the volume does. `Personal2` is never taken for `Personal`.
- The data root is never in scope, even inside a personal folder.
- The gate runs again on each transcript line's own folder, so a turn typed after a `cd` out of your folders is never added.

### Secrets

`capture/secrets.py` replaces each secret with `[secret removed: <kind>]` before anything is written, in the spool and in the database. It is plain code with no model. It looks for private key blocks, vendor API keys and tokens, login tokens (JWTs), passwords in URLs, authorization headers, `.env` lines and `password=`-style pairs, and long high-entropy strings next to a word like "token". It leaves ordinary text alone: UUIDs, commit hashes, placeholders, numbers and prose. A second pass changes nothing. If the scrubber cannot load outside a test run, nothing is written.

### Turn origin

`capture/origin.py` splits a user turn by origin, from Claude Code's own markers only. It never calls a model.

| Origin | Meaning |
|---|---|
| `typed` | What you typed (the default) |
| `pasted` | Claude Code's pasted-text markers; a mixed prompt stays typed, with the paste offsets kept |
| `command` and `command_output` | A slash or shell command you typed, and what it printed. Words after a slash command are typed. A bare `/clear` is no turn. |
| `system_injection` | Text a hook or Claude Code added. Not your words, and not stored. |
| `northstar_injected` | A block Northstar delivered, wrapped in its own `northstar-context` marker. It wins over everything around it, so it is never taken for your words (I24). |

### Reconciliation and work events

- **Reconciliation.** Claude Code's transcript files are audit truth and the hooks are the record. When a session has ended, or has been quiet for 120 seconds, the ingester reads its transcript. It adds turns the hooks missed, and the assistant's intermediate texts, with fidelity `reconciled`. A turn both have but with different words is logged as a mismatch (hashes and sizes only) and neither is changed. Turns from before capture began for a session are not reconciled; the backfill is the way to bring them in.
- **Work events.** When a captured session ends, the commits made in its folder during the session are recorded as work events: kind `commit`, evidence `medium`, the label being the first line of the message with secrets removed. The repository is named by a hash of its remote, so no path or password reaches the record. The code reads git with plain read-only commands and cannot change the repository.

### The encryption stamp

Real capture needs the data folder to be encrypted at rest. `capture install` checks (on macOS, FileVault on the boot volume, or an encrypted unlocked volume) and writes a stamp at `<data root>/capture/encryption.stamp`. The hook looks for a valid stamp on every event and writes nothing without one. The stamp names the data folder and its volume, so moving the folder or the volume invalidates it, and the fix is to run `capture install` again. The check is macOS only for now.

### Install options

There are two ways, and you use one, not both. With both in place every turn would be spooled twice, so the second is refused. Neither runs without a path, and neither looks for your real Claude Code settings on its own.

- **A settings file.** `--settings PATH` merges the hooks into a `settings.json` you name. It splices into the file's own text, so every other byte stays as it was. A timestamped backup is kept beside it. A second install updates the entries in place, and `capture uninstall --settings PATH` takes out only Northstar's entries.
- **A plugin folder.** `--plugin-dir PATH` writes a self-contained Claude Code plugin into PATH with the interpreter's absolute path in every hook, and prints the commands that add it.

The hook command is the project's own interpreter (`<repo>/.venv/bin/python -P -m northstar_agent_memory.capture.hook <event>`), run directly with no shell and no `uv run` in front. `-P` keeps the session's working folder off the module path.

The repository's own `plugin/` folder is something else: the same hooks with a path relative to the checkout, for trying capture with `claude --plugin-dir ./plugin` from a checkout only. See [`plugin/README.md`](../plugin/README.md).

### The commands

**`capture status`** shows personal folders, installed hooks, the encryption stamp, the spool, the ingester, what `history.db` holds by app, and the capture log's last error. It only reads.

```bash
uv run northstar capture status
```

**`capture install`** puts the hooks in. Run the dry run first. It prints exactly what would be added and writes nothing. Try it on a scratch file, not on your real settings:

```bash
uv run northstar capture install --settings <scratch folder>/settings.json --dry-run
```

It checks that the hook command starts, checks encryption, then lists one `add` line per event with its timeout (SessionStart 5, UserPromptSubmit 3, Stop 8, the other four 2). The real install is the same command without `--dry-run`. It writes the stamp and records the install so `status` can find it.

**`capture backfill`** imports past transcripts from a folder laid out like `~/.claude/projects`. It needs personal folders set and the encryption check to pass, and it refuses a whole home folder or disk root. Only sessions inside your personal folders are stored. The rest are counted, never stored. The dry run counts sessions in and out of scope and messages, and stores nothing (it rolls back inside a scratch database, and may leave an empty `capture/` folder under the data root):

```bash
uv run northstar capture backfill --from <folder of transcripts> --dry-run
```

The real import is the same command without `--dry-run`. It is safe to repeat, and it matches what live capture stored by transcript line, so the two histories agree. It does not record work events, because a commit counts as made "during a captured session" only live. A message whose place holds other words is counted as a conflict and left alone.

**`capture ingest`** drains the spool into `history.db` now, and prints counts. The hooks start the ingester themselves, so you rarely need this.

```bash
uv run northstar capture ingest
```

**`capture uninstall`** removes only Northstar's hooks from a settings file. What was captured stays in `history.db`.

```bash
uv run northstar capture uninstall --settings <path to settings.json> --dry-run
```

### What is not done

- **Not installed** in the author's Claude Code, and **no real sessions imported.** The backfill is a one-time step that needs the user's go-ahead (GOAL, 2026-10-29).
- The hook prints nothing. Delivering memory on `UserPromptSubmit` is step 5.
- Paste demotion is not done. The connector design (§8) would treat a long multi-line segment, code fences or text that matches recent tool output as pasted, even without Claude Code's marker. Origin comes from Claude Code's markers only.
- Codex and the chat apps have no connector. Windows is not supported.

---

## 5. Configuration

Two layers, merged by `northstar_agent_memory.config.load()`:
- **`src/northstar_agent_memory/config/defaults.toml`** ships with the code. It holds Northstar's starting values, versioned (invariant I19): `config_version` names the set. A value changes only through a tested release: edit, bump `config_version`, record why. Nothing in it is personal.
- **`<data root>/settings.toml`** is yours. It overrides matching keys, table by table, and is never in the repository.

### Keys in `defaults.toml`

| Section | Keys | Meaning |
|---|---|---|
| (top) | `config_version` | The version of the starting values |
| `[models.anthropic]`, `[models.openai]` | `answerer`, `judge`, `worker`, `worker_small`, `checker`, `sim_user` | The model ID for each role. A role with no model refuses live calls. |
| `[prices.<model>]` | `input`, `output`, `cache_read`, `cache_write_multiplier`, and `long_*` for long prompts | US dollars per million tokens. Used on the `api` route. A model with no price refuses live calls there. |
| `[route]` | `default` | `"harness"` (default) or `"api"` |
| `[harness]` | `claude_binary`, `codex_binary`, `timeout_s` | Program paths (empty means: look on PATH, then in the desktop apps) and the longest one call may take |
| `[budget]` | `monthly_soft_usd`, `monthly_hard_usd`, `run_default_usd` | Dollar caps for the `api` route. 0 means not set, and live API calls are refused. |
| `[maintenance]` | `loss_bound`, `loss_bound_min`, `max_ops_per_proposal`, `max_structure_changes_per_run`, `max_label_changes_per_run`, `idea_move_share`, `quarantine_attempts`, `quarantine_days`, `max_job_attempts`, `error_budget`, `error_budget_min_sample`, `check_families`, `idle_trigger_minutes`, `goal_card_top_items`, `fingerprint_words`, `echo_overlap` | The write gate's and the run store's starting values (MEMORY-ARCHITECTURE §5.13) |
| `[eval]` | `token_budget`, `judge_false_accept_max`, `judge_batch_size`, `lme_margin_points`, `seed` | DESIGN §8's values, fixed before the data they judge. `lme_margin_points` is the old bar; see section 2. |
| `[eval.longmemeval]` and `[eval.longmemeval.per_type_test]` | `types`, `per_type_dev`, `abstention_dev`, `abstention_test`, `b0_test_per_type`, and the held-out count per type | The subset sizes |

### Keys that go in your `settings.toml`

The file does not exist until you make it. Any key above can be overridden. The ones you will want:

```toml
[capture]
personal_paths = ["~/Projects", "~/Notes"]   # folders whose Claude Code sessions are captured

[route]
default = "harness"                          # or "api"

[maintenance]
check_families = ["anthropic"]               # only if you have one model family; checks are then labelled
```

- `[capture] personal_paths` has no default. With none set, nothing is captured.
- `[route] default` picks how hidden calls reach the models.
- `[budget]` keys matter only on the `api` route.
- `[harness]` paths are needed only if the Claude Code or Codex program is not found on its own.

---

## 6. Data and privacy

The repository is public. **Personal data lives only under the data root, never in the repository.**

### The data root

| Setting | Data root | Cache root (public, re-downloadable) |
|---|---|---|
| Default (macOS) | `~/Library/Application Support/Northstar` | `~/Library/Caches/Northstar` |
| `NORTHSTAR_HOME=X` | `X/data` | `X/cache` |

Layout (`core/db.py`, `paths.py`, `capture/spool.py`):

| Path under the data root | Holds | Personal? |
|---|---|---|
| `history.db`, `blobs/` | Chat history word for word, work events, snapshots | Yes |
| `memory.db`, `working.db`, `index.db`, `overview.db`, `runs.db` | The other five stores | Yes, once anything is written |
| `spool/claude-code/` | The hooks' day files, until ingested | Yes |
| `capture/` | `capture.log` (errors; never turn text), `ingest.lock`, `state.json`, `encryption.stamp`, `installs.json` | The log and the stamp hold paths, not chats |
| `eval/` | Runs, recorded model calls, the cost ledger, held-out ledger, normal-use reports (section 2) | Yes when run on your chats. The recorder holds prompts and answers. |
| `harness-cwd/` | An empty folder that hidden runs start in | No |
| `settings.toml` | Your settings | Yes (it names your folders) |

The cache root holds downloaded public benchmark files only (`bench/longmemeval/`).

### The guards

- **`NORTHSTAR_HOME`** moves both roots. Every test sets it (section 7). Use it for any trial.
- **Encryption at rest.** The stores refuse to open on an unencrypted volume on macOS (`EncryptionRequired`): FileVault on the boot volume, or an encrypted, unlocked volume. The check is skipped only in a test run: `NORTHSTAR_TEST_MODE` is set, or `NORTHSTAR_HOME` points inside a temporary folder. The hook has its own check, the stamp (section 4). `doctor` prints "not enforced while NORTHSTAR_HOME is set" whenever that variable is set, even when it points outside a temporary folder; the stores themselves follow the rule above.
- **Scope.** Only sessions in your personal folders are captured. The data root is never in scope.
- **Self-capture marker.** `NORTHSTAR_HIDDEN_RUN=1` is set in the environment of every Claude Code or Codex run Northstar starts. Hooks and the ingester exit at once when it is set (I24). Northstar's own text is never your session.
- **Secrets** are replaced before anything reaches the spool or the database.
- **Results stay out of git.** `eval` commands refuse to write inside a git work tree unless you pass `--allow-repo-path`. `normal-use` and `backfill` refuse a whole home folder.
- **Keys** come from the macOS Keychain (item `northstar-<family>`) or the vendor's environment variable. They are never printed, logged or put in an error message. The harness route needs none.
- **No command defaults to your real Claude Code configuration.** `capture install` and `uninstall` need an explicit path.

---

## 7. Testing

Run the whole suite from the repository root:

```bash
uv run pytest -q
```

On 2026-11-07 it ran 3,153 tests, all passing, in about a minute. No test calls a model, starts a vendor program or touches your data.

| Folder | Tests | What it covers |
|---|---|---|
| `tests/core/` | 1,764 | Every core module: the stores and their triggers, events and schemas, the projector, the reader, replay, the gate and its attacks, the invariants, the run store, working memory, the index and overview stores, and an end-to-end scenario on invented data. `test_contract.py` checks that each adapter matches its port and that the config numbers match the code's. |
| `tests/models/` | 347 | The port, schema checks, the recorder, the budget guard and ledger, keys, the API adapters, and the two harness adapters with their failure handling |
| `tests/eval/` | 431 | LongMemEval loading and selection, token counting, the baselines, the judges and the judge test, metrics, the runner, the report, the scenarios, normal-use measures, and the Claude Code transcript reader. Fixtures in `tests/eval/fixtures/` are invented. |
| `tests/capture/` | 503 | The hook, spool, ingester, scope gate, secret removal, origin, work events, backfill, install, and `test_integration.py`, which drives the real hook, ingester and backfill together on invented sessions |
| `tests/test_cli.py` | 108 | The command line |

To run part of it:

```bash
uv run pytest tests/core -q
```

```bash
uv run pytest tests/capture/test_secrets.py -q
```

```bash
uv run pytest -q -k gate
```

### The guards in the tests

- **`tests/conftest.py`**, applied to every test automatically:
  - `NORTHSTAR_HOME` is a throwaway folder for each test, so no test touches the real data root.
  - API-key variables are removed and the Keychain is switched off, so no test can make a live call.
  - Starting a vendor program is made an error: `harness.run_process` raises, `shutil.which` finds neither `claude` nor `codex`, the bundled Claude and Codex copies are hidden, and `CODEX_HOME` points nowhere. A test that needs a run fakes `run_process` and names a program in settings.
- **Capture tests** (`tests/capture/__init__.py`): every folder, session, transcript and secret is invented (the "token" is a made-up string). They never read `~/.claude` or any real Claude Code configuration. The integration tests assert before and after each test that the data root is the throwaway one.
- **Core tests** use an invented person and project (the worked example of MEMORY-ARCHITECTURE §6). Attack tests (`test_attacks.py`, `test_gate_attacks.py`) forge proposals to check that the gate refuses them.

---

## 8. What comes next

Steps 4 to 8 follow DESIGN §10, one at a time, each tested before the next. Then the whole is measured as DESIGN §8 says: the scripted scenarios and published benchmarks first, then two to four weeks of normal use against the baseline weeks. Windows follows.

| Step | What it builds | Where it is specified |
|---|---|---|
| 4 Maintenance | Extract, integrate, refresh, check, rebuild and log, then the weekly restructuring and the scheduled job. Hidden sub-tasks run on the model port, the proposals go through the write gate, and checks run on the other family. | DESIGN §10; MEMORY-ARCHITECTURE §5 |
| 5 Memory | Search and routing, start notes, the strict gate for a new chat, refill after compaction, and the recall tool. Delivery on `UserPromptSubmit` comes here. | MEMORY-ARCHITECTURE §4 |
| 6 Focus | Working memory kept live, the three default moments, the note for one reply, the blind check, the moves (step back, split, fresh start) and the decisions check | DESIGN §3 |
| 7 Overview | Chat answers through the recall tool, the map card in Claude desktop chat that opens full screen, and a short outline in Claude Code | DESIGN §6 |
| 8 Robustness | Quarantine, rollback and the full fault suite, plus the purge saga | MEMORY-ARCHITECTURE §5.9, §5.12, §3.4 |

After the eight steps, the connectors for Codex and the chat apps are still to build, and so is Windows (the encryption check, scope comparison and paths are written to allow it, but nothing is tested there).

### Open items carried into those steps

From the code's own notes, and the follow-ups in EXPLORATION:

- **Step 4, the glue.** Connect the model port's recorder to `runs.db`'s `record_call`, so every maintenance call is recorded in the run store. Make background work wait while you are in a session.
- **Step 4, the builders.** The index builder fills `index.db`: the link, meaning and time search lists, rank fusion, the near-duplicate drop and the full rebuild. The overview builder fills `overview.db`: placement of new topics near their strongest links, and the projection checks of MEMORY-ARCHITECTURE §5.10 (I9, I27).
- **Step 4, extraction.** Hedge rules (I10) and the extraction side of I11, so that Northstar's delivered text never counts as evidence.
- **Step 4, replay on a schedule.** Run `verify_replay` weekly, and the `sweep`, as MEMORY-ARCHITECTURE §3.1 says. Both exist as functions only.
- **Step 5, delivery.** The delivery checks of I17 and I25 (pushes stay inside scope; views, principles and working style are never pushed). The `UserPromptSubmit` hook, which prints nothing today.
- **Step 6, focus.** The live writer for `working.db`, and a first real caller of `UserAuthority`.
- **Step 7, structure.** The structure gate for I26.
- **Step 8, purge.** The saga of MEMORY-ARCHITECTURE §3.4, which uses `purge.applied` and `authorize_purge`.
- **Measurement follow-ups.** The list under "Known limits" in section 2: gap closure in the report, the audit of the six probes, the judge on partial answers, plan usage in the report, the labelling step of `eval normal-use`, and a held-out pilot persona.
- **Capture follow-ups.** Install capture, with the user's go-ahead, and import the user's sessions with the backfill; then start the weeks of normal use that the baseline measures are compared with.
