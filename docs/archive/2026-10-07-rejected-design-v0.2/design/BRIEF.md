# Northstar: approval brief

*Read this first. 2026-10-07. Design v0.2 has been reviewed and is waiting for your approval; nothing is built yet. Full design: [DESIGN.md](DESIGN.md). Every review finding and what was done about it: [REVIEW.md](REVIEW.md). The research behind both: [SYNTHESIS.md](../research/SYNTHESIS.md).*

## What we propose, and why

Your brief: you learn all the time, through AI conversations, research, work, reading and your own thinking, but it piles up as disconnected fragments instead of a coherent, evolving understanding.

The research reframed it:
- **Recall is not the hard part.** Searching raw logs already answers "what did I say about X?" about as well as dedicated memory products.
- **AI-written summaries feel like understanding but reduce learning.** People who let a model synthesize for them learn less than people who do it themselves.
- **The unsolved problems are elsewhere:** keeping "the AI said X" apart from "I hold X", recording how a view changed without losing the old one, and keeping a light habit going.

So instead of a knowledge base, we propose a small local system with four parts:

1. **An archive that keeps everything.** Claude Code deletes its logs after 30 days and nothing else keeps them. Northstar copies every personal session permanently, with secrets removed, and makes it searchable.
2. **A short record of what you hold, in your own words:** open questions and aims; your *positions* on them, including your understanding of how something works; *decisions*, with the options you rejected and what you expected; and notes. Every change is a new dated entry saying what changed and why, so nothing is overwritten.
3. **A weekly 20-minute Session:** 8–10 timed prompt cards in a terminal, built from your own week without any AI. You recall where you stand before seeing your earlier answer, say what you took away from a learning conversation, relate something new to a position, confirm commitments made in passing, and close with "what changed this week?". Nothing enters the record unless you type it.
4. **A decisions file for your AI tools (the "pack"):** about 2,500 tokens listing your decisions, rejected options, views you no longer hold and open questions, which Claude Code reads in your personal folders. Your opinions stay out by default: memory profiles make assistants more agreeable, not more useful.

**The trade, stated plainly.** About 7 items a week, plus a monthly review, get integrated in your own words. Everything else stays in the archive, searchable but not condensed; no AI-written page ever stands in for your view. If you wanted condensed topic knowledge, answer "no" to Q0 below ([DESIGN §1.2](DESIGN.md#12-what-this-is-and-what-it-is-not)).

**In v0:** the Claude Code archive and search; the record with full history ("what did I think in March?"); the weekly Session; decision capture inside Claude Code chats; the pack; secret removal and deleting a source on request.
**Not in v0:** an AI-maintained wiki, graph or vector databases, a web app, reading ChatGPT, Claude.ai or Codex history (v0.5; Codex logs are copied now), AI-prepared cards (v0.5), spaced repetition, predictions, a goal hierarchy, phone capture, multi-machine sync, and anything from client or employer work, which is ignored unless you opt a client in. Each deferred item has a written trigger to bring it back ([DESIGN §14](DESIGN.md#14-deferred-decisions-and-their-triggers-the-ladder)).

## What you will experience

- **Day 0 (about 20 minutes):** answer the questions at the end of this brief; request your ChatGPT and Claude.ai exports.
- **Build days 1–2:** archiving and search start (`ns find`; `ns` is Northstar's command-line tool). On build day 2 you record 3–5 real decisions (about 15 minutes), and Claude Code sees them that day and should stop re-suggesting what you rejected.
- **Weeks 0–1:** write 3–5 open questions or aims (about 10 minutes), then sit two 20-minute Sessions prepared by hand from your material outside this project, including exports and one learning conversation. They decide whether the Session tool gets built.
- **Weeks 1–2:** a report of dated quotes from your exports where your view changed.
- **Day 14:** v0 complete.
- **Every week after:** an hour before your slot (default Friday 16:30) a notification says the Session is ready. At 20 minutes it stops; nothing carries over. Between Sessions, Claude Code may ask "Log that as a decision?" at most once a day and three times a week; ignoring it records nothing.
- **Monthly:** one review card to keep, park, close or merge your questions, ending with "explain one thing without looking".
- **Weeks 3–8:** short evaluation tasks (below).

`ns pause` takes weeks out of every clock and check; a missed week costs nothing.

## What it costs you

- **Use:** about 25 minutes a week (the Session plus a few minutes of capture). If your typical week exceeds 30 minutes for three weeks, the Session gets fewer cards.
- **Onboarding:** under 45 minutes before the first payoff.
- **Evaluation:** at most 2 hours in total over 8 weeks, timed separately.
- **Building:** six part-time build sessions of 2–4 hours with coding agents, over about two calendar weeks.
- **Money:** nothing for v0, which uses no AI model and needs no API key. Optional later: about $11–21 once, with an API key, to mine the Claude.ai export.

## How we will know it works, and when we stop

Satisfaction never counts as success; what you do, and tests with pass marks fixed in advance, decide.

| When | Check | If it fails |
|---|---|---|
| Weeks 0–1 | Both hand-built Sessions held at the slot, each within 25 minutes | Build the version without a weekly Session (in-the-moment capture, monthly review) |
| Day 14 | v0 works: archive, record, history, the pack loading in a real session, safety checks | Fix it, or cut by the written cut order |
| Week 4 | Use (a Session or 2+ captures a week); time within 30 minutes; an audit that 30 entries really are your words; how often a change in your thinking had nowhere to go | Step down to a lighter routine; fix the faulty capture path; rethink the record's categories if over 20% had no home |
| Week 6 | The pack reduces re-suggestions of rejected options across ~30 scripted prompts | Redesign the pack |
| Week 8 | The structured record beats the same records as a plain dated journal by ≥10 points on ~100 test questions | AI tools read the journal form; you still record the same things |

Building pauses in any week you did not use the system, and nothing beyond v0 is built until you have used it two weeks running. Even the lightest fallback beats today: a permanent, searchable archive plus a small decision journal for your AI tools. The project can stop at week 4 or week 8 with a written record of why ([DESIGN §10](DESIGN.md#10-evaluation-plan), [§12.3](DESIGN.md#123-if-the-ritual-fails-the-degradation-ladder-and-the-runner-up)).

## Main risks

1. **The builder's trap:** building is more fun than using. Guards: the use gate, no building in unused weeks, a six-session v0.
2. **The weekly habit fades.** Guards: a hard 20-minute cap, no backlog, a reminder, a 5-minute option; decisions pay off without Sessions.
3. **It under-serves learning.** Understanding positions and takeaway cards help; Q0 and the "nowhere to go" count are the real checks.
4. **AI words recorded as yours.** Code decides who said each line, every field must trace to your typing, and the week-4 audit checks it.
5. **Work confidentiality.** Work is ignored, the pack loads only in personal folders, and archived text only goes back to its source account.
6. **Thin data.** Today's logs are two days old and mostly about this project; exports and the weeks 0–1 Sessions test real material.

Full list: [DESIGN §13](DESIGN.md#13-risks-and-mitigations).

## What we need from you

In priority order. The first five gate the build; if you approve without answering one, we use the default shown.

- **Q0. Is this the system you want?** A record of what you hold plus a raw archive, on the trade stated above, not a knowledge base. *Default: yes.* "No" means a redesign and a fresh review before anything is built.
- **Q6. Work and accounts.** Is client or employer work done in Claude Code or Codex on this laptop, and which folders, git remotes and client names mark it? Are your Claude and ChatGPT accounts employer-provisioned (the Claude account here uses a work email)? Are folderless desktop chats personal? *Default: work ignored by any markers you give; each folderless chat sorted with one key; the pack loads only under `~/Personal`; the Claude account treated as employer-provisioned, so the pack stays off until you name an account at Q5.*
- **Q3. The Session.** A timed 20-minute weekly Session in a terminal, starting with two in weeks 0–1? Which slot? *Default: yes, Friday 16:30.* "No" means the version without a weekly Session from day 1.
- **Q2. Purpose.** Rank "think better", "my AI tools know my decisions", "learn and keep what I learn". *Default: no ranking (the balanced design).* AI-first moves decision capture ahead of the Session; learning-first favours takeaway cards.
- **Q5. Privacy.** Which accounts may receive your personal records? Which topics (health, relationships, finances, other people) must stay private or never be archived? *Default: your Claude account only, subject to Q6; private goes nowhere; no topics excluded until you name them.*

The rest:
- **Q1. Exports:** request both today? *Default: yes; if none arrive in time, weeks 0–1 use Claude Code material.*
- **Q4. Own words:** type one-line positions yourself? *Default: yes; v0 has no AI drafts.*
- **API key:** *Default: none; v0 needs none.*
- **Q8. Interface:** *Default: terminal plus one Markdown page; no phone notes folder.*
- **Q10. History:** *Default: a permanent record, with any source deletable on request.*
- **Q11. Decisions:** *Default: expectations and revisit dates now, predictions later.*
- **Q12. Success:** in your words, what would make you say this worked at three months? *Default: only the checks above.*

What each answer changes: [DESIGN §15](DESIGN.md#152-questions-for-jack-in-priority-order). Decisions are recorded as ADRs (architecture decision records) in [docs/decisions](../decisions/README.md) and become Accepted when you approve.
