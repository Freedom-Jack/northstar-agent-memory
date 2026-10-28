# 0012. AI pack: decisions, rejected options, views no longer held, open questions and aims; positions only on demand

- **Status:** Proposed
- **Date:** 2026-10-07
- **Revised 2026-10-07 after review:** the pack is imported through parent-folder `CLAUDE.md` files, not the user-level file, because the user-level file loads into every session including client work, framed as instructions; the header defers to Jack's own instructions; every line is stored text, verbatim; a title index of questions (never stances) and aims replaces the count line; agents get a fetch rule that keeps positions out of recommendation requests; just-in-time reads default to the current folder's scope; one `personal` pack, with no parent, global or provider-filtered scopes; Codex delivery is deferred (Codex has no import mechanism); the live cold-pack trial is replaced by scripted E10; receipts are one daily line. See `REVIEW.md` (ai-safety-privacy-2, -12, -13, -14; scope-simplicity-9, -10; problem-fit-10; epistemics-1; engineering-11; evaluation-11).

## Context

J5 asks AI context not to make Jack re-explain, not to re-suggest what Jack rejected, and not to flatter. Memory profiles raised agreement sycophancy by up to 45% [07]; memory-augmented agents scored worse on appropriateness; small, scoped, labelled context with explicit constraints works best [05][07]. All judges chose C's default of leaving positions out.

The review found that v0.1's delivery defeated its own scoping: a user-level `CLAUDE.md` import reaches work repositories, and Claude Code frames that content as instructions to follow exactly. The pack contained a line no record held, the index gave agents nothing to fetch, the sycophancy defence was untested against just-in-time fetching, and Codex cannot import a file.

## Decision

1. **Contents** (DESIGN §8.2), ≤2,500 tokens, deterministic, every line verbatim from the ledger plus fixed labels: a header; decisions in force with rejected options and reconsider-if; **no longer held** (superseded or retracted views, verbatim, skipping any a current head reinstates); open questions and aims; a title index of questions with recorded views. Positions are not included. `seq` is the highest seq among included items.
2. **The header** says the records are background data about Jack's personal projects, not instructions; Jack's own `CLAUDE.md` and `AGENTS.md` take precedence; the pack outranks only other memory files; rejected options are not re-proposed unless their condition holds; open questions are not settled; fetch records when a task needs what Jack recorded about how something works or what was decided, but **not to answer a request for the agent's own recommendation** unless Jack asks what they previously thought; disagree when there is reason.
3. **Delivery.** Jack adds `@~/northstar/packs/personal.md` to the `CLAUDE.md` of parent folders: `~/Personal/` and, if scratch chats are personal, the scratch-workspaces folder. Claude Code reads `CLAUDE.md` in every parent of the working folder, so this reaches exactly those sessions. A user-level import only if Jack confirms no client or employer work happens in Claude Code on this machine. **Northstar never edits these files.**
4. **Scopes.** One `personal` pack. `private` and `work` records are never packed. `egress.allowed` is checked for the destination (ADR-0016).
5. **Just-in-time CLI** (`ns get`, `ns find`, `ns history`, `ns asof`) defaults to the current folder's scope and returns nothing in a work or unsorted folder without `--scope`.
6. **Codex** pack delivery is rung R18; the JIT CLI follows the Codex parser in v0.5.
7. **Receipts.** The daily `pack.compile` line records the sha, items and which `CLAUDE.md` files contain the import line; `own_pack` markers give per-session receipts if pack text appears in `prompt_snapshot` (a B2 spike). Exposure windows are rung R5.
8. **No instruction kind.** Jack's own files remain the only instruction channel (P11).

## Alternatives considered

- **Positions in the default pack (A, B, D, E).** The direct lever for agreement sycophancy; reversible by config if E10 allows.
- **User-level import (v0.1, scope-simplicity-9).** Reaches client work.
- **Per-project imports only.** Cannot reach folderless scratch chats, where most of Jack's sessions are.
- **A live cold-pack trial (E).** Underpowered and mismatched to session lifetimes here.
- **A SessionStart hook; full preload; vector top-k.** R9; context-rot evidence [07].

## Consequences

- "Don't re-suggest" is served directly; "don't re-explain" depends on agents fetching what the title index advertises.
- The pack is small and cacheable, and its only injection surface is verbatim text Jack recorded.
- Personal decisions never reach client work by default.

## Deciding evidence or experiment

- **The B2 spikes:** the parent-folder import loads in a scratch chat and a personal project; external-import approval behaviour; a per-decision smoke test with and without the pack.
- **E10** (DESIGN §10.6): scripted prompts × {no pack, default, default plus the skill, plus positions}, with pre-registered consequences for re-proposal and agreement.
