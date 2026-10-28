# 0002. Canonical substrate: two append-only JSONL ledgers outside git

- **Status:** Proposed
- **Date:** 2026-10-07
- **Revised 2026-10-07 after review:** reads never write or lock; archive and ledger use separate locks; readers ignore a partial final line; index determinism is a canonical logical dump, with byte identity only for `now.md` and the pack; machine ops cut from 13 to 7 and derived state (`auth`, integrity, episodes) removed from the ledgers; the collision-proof ID claim is dropped. See `REVIEW.md` (engineering-8, -10, -11; scope-simplicity-4).

## Context

SYNTHESIS disagreement 1 asks which store is canonical: SQLite ([06]), or editable Markdown with a database as projection ([02], [07]). The synthesis said to decide by *who edits what*. Three requirements constrain the choice: excision must reach every derived store (FR28); Jack's words must be readable without the app for decades (FR29, NFR1); and the scale is small (hundreds to low thousands of Jack's acts a year).

## Decision

- **Canonical:** two append-only JSONL files in `~/northstar/ledger/`: `person.jsonl` (Jack's acts only) and `machine.jsonl` (what ran and what was served). The vocabularies are in DESIGN §4.3.
- **Writers.** Ledger appends take a ledger lock, write whole lines, fsync, and validate against the op schema. Archiving and index rebuilds take a separate lock. The first line of each file is a `schema` record.
- **Readers.** Reads never write and never lock, and ignore a final line without a newline.
- **Store only what cannot be derived.** Episodes, integrity grades and verification results are computed in the index, never stored.
- **Views, not stores.** `index.sqlite` is disposable; determinism means equal canonical logical dumps. `views/now.md` and `packs/personal.md` are byte-identical across rebuilds.
- **No git.** `NS_HOME` is not a repository; the README states what excision cannot reach.
- **No hand-editing.** Jack acts through `ns`. A notes folder, if Jack asks for one (Q8), is ingested as *sources*, not as a second canonical store.
- **Schema changes** bump `v` and migrate by copy-and-transform; the replay test arrives with the first migration (DESIGN §4.7).
- **IDs** are unique per machine; a future merge renames collisions with an alias (ADR-0004).

## Alternatives considered

- **SQLite canonical (A).** Triggers enforce append-only and it scales, but the file is unreadable without tooling and excision needs `VACUUM`, WAL truncation and backup rewriting. At this scale JSONL replays in well under a second.
- **Editable Markdown canonical (B).** Best legibility, but append-only and quote fidelity become lint conventions; needs a round-trip parser and merge driver; excision means `git filter-repo`.
- **SQLite plus a JSONL mirror (E).** Two stores to keep consistent.
- **Monthly shards (D).** Workable; one file per authority is simpler to read cold.

## Consequences

- Jack's record is greppable and diffable with plain tools, and a fresh model can read it with only the README.
- Excision is a copy-and-transform rewrite with no history surgery.
- Parallel agent sessions cannot contend with the ledger by reading it.
- Editable "Where I stand" sections are rung R10.

## Deciding evidence or experiment

- The dead-tool test (v1): a fresh agent given only the export answers ≥80% of 20 history questions.
- Replay time at 10⁶ synthetic events (NFR8); above 5 seconds, revisit sharding.
