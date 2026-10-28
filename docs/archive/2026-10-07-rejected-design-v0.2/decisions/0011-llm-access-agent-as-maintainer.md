# 0011. LLM access: v0 needs no model; agent-as-maintainer from v0.5; API optional

- **Status:** Proposed
- **Date:** 2026-10-07
- **Revised 2026-10-07 after review:** v0 needs no model at all; agent prep moves to v0.5 and runs in a custom `tools: Read` subagent whose output is piped to `ns work submit`, spiked first (a `.claude/settings.json` in a workspace does not restrict a subagent); "no new exposure" is replaced by the egress rules of ADR-0016; the cross-family judge and the cross-provider model-swap check (NFR3) are dropped. See `REVIEW.md` (engineering-5; ai-safety-privacy-3, -5; evaluation-6; scope-simplicity-6).

## Context

There is no API key, no `claude`, `codex` or `ollama` CLI on PATH (Claude Code runs through the desktop app; a Codex CLI is bundled inside the ChatGPT app), and Jack works at a large IT consulting firm. The design must work with Jack's own coding agent doing judgement steps, with an API key if one is added, and later with a local model. Most of the pipeline needs no model (DESIGN §9.1).

The review found that v0.1's maintainer isolation does not exist as described (subagents inherit the parent session's permission context; an allow list only auto-approves), that LLM prep would have had little to process in v0, and that a judge from another model family would send content to a provider that never saw it.

## Decision

1. **v0 needs no model.** Archive, speakers, redaction, index, card building, the Session, `now.md`, the pack, as-of, in-flow verification and excision are deterministic. G0 agendas and the E8 report are done by hand by same-origin agents.
2. **From v0.5, one job protocol for every backend** (DESIGN §9.2). `ns work next` writes a job folder; a backend returns JSON; `ns work submit <id> -` runs the gates and records the prompt sha and reported model. Replay never calls a model.
3. **Default backend: agent-as-maintainer.** A custom subagent definition (`.claude/agents/northstar-maintainer.md`) with `tools: Read` only, which reads the job folder and returns JSON as its final message; the parent pipes it to `ns work submit`. Its real permission behaviour is spiked before it is relied on. `ns setup` prints allow rules for Jack to add; it never writes settings. Supervision minutes count against Jack's budget.
4. **Optional API backend** (`[api]` extra; the official `anthropic` and `openai` SDKs; structured outputs; the Batch API). The configured default is `claude-opus-5-5`; Jack may set `claude-sonnet-5-5` or `claude-haiku-4-5` per task. Model IDs live only in config.
5. **Egress** follows ADR-0016: archive text only to its origin account; Jack's records by per-scope policy.
6. **Evaluation judging** uses the same provider as the answerer on a different model, validated by a planted-answer meta-evaluation (ADR-0014).
7. **Local backend** is rung R12. **Drift control** (v0.5): a golden job set re-run when the reported model changes.

## Alternatives considered

- **Require an API key from day one.** A new data processor before any value.
- **Per-workspace settings as isolation (v0.1).** Does not restrict a subagent.
- **A cross-family judge or swap check.** Breaks egress.
- **Local models first.** Unknown quality on the quote gate; kept for `private` content (R12).
- **An LLM call inside the live Session.** Slow and non-deterministic.

## Consequences

- v0 runs with no key, no added cost and no model exposure.
- Full export backfill realistically needs a key: Anthropic for the Claude.ai export, OpenAI for ChatGPT (DESIGN §9.5).
- Agent-mode quality varies; the gates and the golden set contain it.

## Deciding evidence or experiment

- The v0.5 trigger for agent prep (DESIGN §12.1) and the maintainer spike.
- The golden-set rerun on any model change.
- R12's trigger.
