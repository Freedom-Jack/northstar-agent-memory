# Archived: rejected design v0.2 (2026-10-07)

**Do not build from anything in this folder.** It is kept only as a record.

The user rejected this design at approval (Q0 = "no"). It turned the goal into something else: "a commitment ledger, a weekly 20-minute integration Session, and a decisions-only pack". The user wants an architected memory system. It has a human-facing structural memory and an AI-facing memory system that keeps long chats on goal and carries continuity across chats. It captures both what the user said and what the AI said, and the AI manages all of it. See [`docs/GOAL.md`](../../GOAL.md).

**Why it drifted.** Every research and design agent was told to "challenge the framing". The synthesis concluded "build a loop, not a store", and every later stage optimized that reframed goal without checking back with the user.

**What remains useful, as constraints on the HOW only:**
- the attribution machinery: deciding who actually said each line, which separates the user's typed text from agent and orchestrator text;
- supersession instead of overwrite;
- the as-of time model;
- privacy scopes and excision;
- the egress rules;
- the findings about the shape of the logs on disk.

Contents: `design/`, which holds the brief, the design, the review, the judging and five proposals, and `decisions/`, which holds 16 ADRs, all left at status Proposed and now rejected.
