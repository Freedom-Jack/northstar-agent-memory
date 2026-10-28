# 0003. Archive agent logs first: structure-preserving, redacted at ingest, retention decoupled from scope

- **Status:** Proposed
- **Date:** 2026-10-07
- **Revised 2026-10-07 after review:** retention no longer depends on directory scope, so the desktop app's per-chat scratch workspaces (where most of Jack's typing happens) are archived; secrets are redacted and tool payloads stubbed as the archive is written; work is ignored entirely (no metadata mode); archiving runs on a schedule, never on read commands; Codex is copied raw and parsed in v0.5; `cleanupPeriodDays` is raised only temporarily, if at all. See `REVIEW.md` (engineering-1, -6, -8; scope-simplicity-2; ai-safety-privacy-4, -8).

## Context

On this machine `cleanupPeriodDays` is unset, so Claude Code prunes logs after 30 days, and nothing else keeps them. Of 208 session files, 196 are orchestrated subagent transcripts. Ten of the twelve top-level sessions live in per-chat scratch workspaces created fresh for each folderless chat, holding about 88% of Jack's typed characters (DESIGN §1.1).

v0.1 keyed retention on directory scope and defaulted everything unmatched to "metadata only", so it would have kept almost none of Jack's real material. It also kept raw bytes indefinitely, including secrets and tool payloads (file contents, command output, possibly client data) that no stage ever used, and asked Jack to raise the global vendor retention, which would keep every vendor copy, work included, forever.

The reason to keep more than normalized text is real: once the vendor deletes the original, a normalizer or classifier bug cannot be fixed by re-parsing. That argument concerns line structure, not secret tokens or tool payloads.

## Decision

1. **B1 is the archive** and delivers before anything else (ADR-0015).
2. **Retention is decoupled from scope.** Every source is archived except `ignore` (work). Scope gates only model use and packs (ADR-0013).
3. **The ingest transform** runs as each segment is written (DESIGN §6.6): secrets become deterministic `⟦SECRET:<rule>:<hash6>⟧` tokens inside JSON string values; tool payloads become `{sha256, bytes, tool}` stubs; line structure is kept, so quotes verify and re-parsing works.
4. **Storage.** Content-addressed blobs (`compression.zstd`), `chmod 700`, segment-append while the stored prefix still hashes the same, only up to the last newline, full re-archive on a prefix mismatch; idempotent by native message ID.
5. **When it runs.** The daily launchd job, the start of `ns session`, and `ns archive`. Never on read commands.
6. **Discovery is recursive** over the whole session tree, including `subagents/workflows/**` and sidecars; whole subagent files are tagged `orchestrator` (DESIGN §6.3).
7. **Codex** rollouts are copied from B1 and parsed in v0.5.
8. **Vendor retention.** Day 0 offers an optional temporary raise of `cleanupPeriodDays` to 60 as insurance against a slipped build; `ns doctor` prompts the revert after 14 clean days.
9. **Anchors** are native message ID plus verbatim quote plus sha256, never offsets.

## Alternatives considered

- **Normalized text only (A, D).** Any normalizer bug becomes permanent.
- **Raw bytes, unredacted (v0.1, B, C).** Keeps secrets and unused tool payloads, so the archive cannot safely sit in backups.
- **Metadata only for anything unclassified (v0.1).** Loses the scratch chats, which are most of Jack's sessions.
- **Archive work raw and rely on `llm = none`.** Whether client logs may be stored at all is a per-contract question; work is ignored until Jack opts a client in.
- **Per-source encryption with crypto-shredding.** Rung R14.

## Consequences

- Preservation survives every other experiment failing.
- The archive is much smaller than the vendor logs and safer to back up.
- Work sessions are not preserved; that is accepted until a per-client opt-in.
- Line-level structure survives, so adapters can be fixed and re-run.

## Deciding evidence or experiment

- B1 acceptance (DESIGN §12.1): re-archive is a no-op; read commands never write; exhaustive orchestrated tagging; 0 seeded secrets in decoded blobs or the index.
- Q6 at approval decides the ignore rules and whether scratch chats are personal.
