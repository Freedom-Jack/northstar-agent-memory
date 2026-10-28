# 0013. Privacy, scopes and excision

- **Status:** Proposed
- **Date:** 2026-10-07
- **Revised 2026-10-07 after review:** scopes are `ignore`, `private`, `unsorted` and `personal`, and the most restrictive matching rule wins; work is ignored entirely (no metadata mode) until Jack opts a client in, so Q6 is no longer a storage-policy gate; unmatched folders and, if Jack chooses, scratch chats are `unsorted` (archived, no model, no pack) and sorted per chat on a one-key card; client and employer names are an ignore list; secrets are redacted and tool payloads stubbed at archive time; v0 excision is by source, verified through the decode path, with a read-only report of copies left in vendor stores; tombstones carry IDs only. See `REVIEW.md` (engineering-1, -7; human-13; scope-simplicity-2, -13; ai-safety-privacy-4, -8, -10).

## Context

Agent logs contain secrets [08]. Jack works at a large IT consulting firm, where what may be stored or processed is usually set per client contract. Context sent to a provider cannot be recalled [06]. Accurate memory in the wrong context is a leak (ConfAIde: 39% wrong-context disclosure [09]). Deletion must reach every derived store [SYN §2.3; FR28].

The review found v0.1's scope model keyed on folders the desktop app creates fresh for each chat, ordered rules so a client repository under `~/Personal` would be personal, left "metadata" undefined (titles and branches can name a client), asked a firm-wide yes/no that could stall the build, and verified excision with a grep that cannot see inside compressed blobs.

## Decision

1. **Scopes** (DESIGN §6.6), most restrictive rule wins:

   | Scope | Archived | Model | Pack | Assigned by |
   |---|---|---|---|---|
   | `ignore` (work) | no, not even metadata | — | — | ignore remotes, paths, and client or employer terms (titles and text) |
   | `private` | yes | never | never | private terms, or Jack per record or chat |
   | `unsorted` | yes | no | no | anything unmatched; a one-key sort card asks personal / private / work (work is excised at once) |
   | `personal` | yes | origin account only (ADR-0016) | yes | personal roots set at `ns setup`, and scratch chats if Jack says so |

   A record's `scope` is only this partition; where a claim holds lives in its text (ADR-0008).
2. **The ingest transform** (ADR-0003) redacts about 30 secret families plus high-entropy tokens and stubs tool payloads as the archive is written, keeping line structure. CI seeds 30 secrets, one inside a compressed blob, and requires 0 hits in decoded blobs, the index, `now.md` and the pack.
3. **Excision in v0 is by source** (`ns excise --source <native-session-id>`, DESIGN §5.5): plan; Jack confirms in a terminal; an ID-only tombstone; blobs and candidate lines removed and citing anchors marked excised (Jack's typed text stays); the native ID added to the ingest antibody list; rebuild; **verify by decompressing every blob and walking `NS_HOME` with symlinks followed**; then a read-only report of copies left in `~/.claude/projects`, `~/.claude/file-history` and `~/.codex`, with commands Jack can run. Record and pattern excision arrive in v1, with antibodies that store a rule or message ID, never the literal.
4. **Known limits, in the README:** Time Machine, iCloud copies (if a notes folder is ever synced), and vendor servers. Providers that received content are listed, never claimed as recalled. Rung R14 (per-source encryption with crypto-shredding).
5. **"What my AI tools are told"** is `ns show pack`; corrections go through `ns correct`, `ns status` and `ns rescope`.

## Alternatives considered

- **Metadata-only default for unclassified folders (v0.1).** Loses most of Jack's sessions and still leaks client names in titles.
- **Archive work raw and rely on `llm = none`.** Whether client logs may be stored at all is per contract.
- **First-match-wins rules.** A stricter rule must always win.
- **Pattern excision in v0.** Little to excise in a ledger of a few dozen lines; source excision covers the realistic case.
- **A git-tracked vault; encryption from day one.** History rewrites; key management before evidence.

## Consequences

- Northstar knows nothing about work sessions until Jack opts a client in; decisions about work can still be recorded by hand with `--scope work` and stay out of every pack.
- Archive copies are safer than the vendor originals they preserve.
- Personal records never reach client work through Northstar.

## Deciding evidence or experiment

- **Q6 at approval:** where work happens, whose accounts these are, and whether scratch chats are personal.
- **CI:** seeded secrets, wrong-context fixtures (a work-folder `ns find` returns nothing; `private` never packed), excision through the decode path.
- **R14's trigger:** a client opt-in requires it, or Jack excises sensitive content.
