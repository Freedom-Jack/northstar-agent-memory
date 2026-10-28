# 0016. Egress control: archive text goes only to its origin account; Jack's records follow a per-scope policy

- **Status:** Proposed
- **Date:** 2026-10-07
- **Origin:** new after the 2026-10-07 review; replaces "no new exposure" (P13 and ADR-0011 item 4 as they stood in v0.1). See `REVIEW.md` (ai-safety-privacy-3, -2, -9; scope-simplicity-9; evaluation-6).

## Context

v0.1's principle P13 said text goes only to a provider that already saw it, but only prep-job dispatch enforced it. Packs went to both Anthropic and OpenAI; agent-mode Sessions relayed Codex quotes to Claude; `ns context` returned spans from every adapter to whichever agent asked; the judge had to come from a different model family; and a decision Jack typed in a terminal had been seen by no provider, so P13 as worded forbade the pack itself.

"Provider" is also too coarse. A consumer account, an employer's organisation and a personal API key are different data processors. The Claude account in this environment is registered to an employer-domain email, and the agent environment exposes `CLAUDE_CODE_ORGANIZATION_UUID` and `CLAUDE_CODE_ACCOUNT_UUID`.

## Decision

1. **Archive-derived text** (any speaker's raw turns, other speakers' encounter quotes, digests) goes only to the **account it came from**: provider plus organisation or account ID, recorded with each source at archive time from the vendor's local configuration. If the account cannot be read, the provider alone is used and `ns doctor` warns.
2. **Jack's own ledger records** (text Jack typed, or quoted from Jack's own turns and recorded) follow a **per-scope policy Jack sets at Q5**, for example `personal` → the named Claude account; `private` → nowhere; `work` → nowhere.
3. **One choke point.** Pack compilation, `ns get` and `ns find`, v0.5 jobs and evaluation all call `egress.allowed(item, destination)`. The destination is read from the calling agent's environment; a terminal with no agent is local and may see everything.
4. **Consequences for other mechanisms:** ChatGPT exports go only to an OpenAI backend or the cue floor; G0 agendas and the E8 report are built by an agent of the same origin as their material; evaluation uses a same-provider judge; there is no cross-provider model-swap check.
5. **Employer accounts.** Q6 asks whether Jack's Claude and ChatGPT accounts are employer-provisioned. If they are, personal records go to no model by default, and v0.5 prep runs only on accounts Jack names.

## Alternatives considered

- **"No new exposure" by provider (v0.1).** Unenforced outside jobs, and self-contradictory for the pack.
- **Per-scope allowlists by provider only (E).** Ignore that the account, not the vendor, is the processor.
- **Nothing to any model.** Possible as a Q5 answer; v0 is unaffected, since it needs no model.

## Consequences

- Every path that sends text to a model goes through one tested function, with CI fixtures (a Codex-origin span never reaches a Claude destination; `private` is never packed; a work-folder `ns find` returns nothing).
- Some convenient flows become impossible, such as a GPT judge over Claude content; that is intended.
- Jack decides, once, where personal records may go.

## Deciding evidence or experiment

- Q5 and Q6 at approval.
- The egress fixtures in CI (DESIGN §10.1).
