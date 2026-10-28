# 0008. Conflicts: link them as tension-questions; never resolve them automatically

- **Status:** Proposed
- **Date:** 2026-10-07
- **Revised 2026-10-07 after review:** the tension type `scope` is renamed `context` (where a claim holds lives in its text; `scope` is only the privacy and pack partition); conflicts also surface in the monthly review and whenever Jack supersedes a record listed in an open tension; deterministic position-to-position neighbour cards and lint arrive in v0.5 behind a trigger; opening a tension asks for its text in Jack's words and has no side effects. See `REVIEW.md` (epistemics-1, -9, -10; problem-fit-6, -7).

## Context

The research rules out newest-wins (most "contradictions" are scope or time mismatches [04]), read-time reconciliation (STALE best model 55.2%), and forced resolution (synthetic blends [01][06]). Some conflicts should be held open on purpose [01]. LLM conflict detection in personal text is unproven (E6).

The review found that v0.1 could not surface a conflict between two of Jack's own positions on different questions or in different scopes, which the brief names explicitly, and that its worked example created a tension's text, type and a confidence drop from a single keypress.

## Decision

1. **A tension is a Question** with `about: [ids]` and `tension: rebut | context | temporal | unknown`. It inherits the question lifecycle: open; **held** (deliberately unresolved, cards suppressed for 8 weeks); answered (by a superseding position or decision); dissolved. Where a claim holds is written into its text by a revision, never into `scope`.
2. **Only Jack opens, types, holds or closes a tension.** Opening one asks for the question in Jack's words (Enter accepts a fixed template); the type defaults to `unknown`; nothing else changes as a side effect. No code path resolves a conflict.
3. **How conflicts surface in v0, without an LLM:** a `challenges` answer on a relate card; recall drift; the monthly review, where Jack sees the whole question set; and a prompt whenever Jack supersedes a record listed in an open tension ("Is it answered by this?").
4. **v0.5, triggered at ≥20 current positions:** a deterministic position-to-position card from local BM25 neighbours across all scopes, at most one per Session, using the existing relate card and tension option; and lint (antibody hits, overdue revisits, positions resting only on AI for over 60 days, tensions whose records are all superseded). Showing Jack's own work-scope record to Jack in a terminal is not exposure.
5. **LLM tension proposals stay off** until E6 shows ≥60% precision on 50 labelled pairs.
6. **Visibility.** Open tensions appear on `now.md` and question pages, and on `ns get` for the records they list. They reach AI tools only in critique mode (v1).

## Alternatives considered

- **Typed tension objects with their own lifecycle (A, D).** Duplicate the question lifecycle. Rung R4.
- **No tension representation (C, strict).** Loses FR12.
- **AI-proposed tensions from day one (D, E).** Noisy cards while trust in the Session is forming.
- **Position-to-position checks in v0.** Too few positions in the first weeks to find anything; the monthly review covers the gap.

## Consequences

- Conflicts become agenda items; the question cap keeps the agenda focused.
- Some conflicts go unnoticed until Jack meets them; missed conflicts cost less than false ones.
- Merge and tension stay independent: two records are the same idea or in conflict, never both.

## Deciding evidence or experiment

- E6 decides LLM proposals.
- The supports share in `ns metrics` (an alarm for confirmation-seeking).
- R4's trigger: E6 ≥60% and more than 10 open tensions Jack cannot manage.
