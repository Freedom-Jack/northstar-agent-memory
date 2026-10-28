# Northstar as three jobs: analysis

2026-10-15. GOAL.md is authoritative. [E] = evidence (probe, count, or product doc checked 2026-10-15). [L] = untested lean. Nothing here changes the WHAT; anything that might is a question in §6.

> **Marking: what "done" means.** The marking page (`focus-mark.html` in the probe workspace, served by the `probe-review` launch config) shows the 20 messages of the website session. Tick "step back", "worse" or "fresh" only where a good collaborator should have spoken up; most rows stay empty. Then answer the questions at the end: the goal the session should have kept in view, which pictured row shows the best version of the site, and how firm it should be. Press "Copy my answers" and paste the result into the chat. It takes about 10 minutes, and answers stay in that browser between sittings.
>
> **Status.** Produced by one analyst per job, a goal-coverage critic, a synthesis, a skeptic (28 issues) and a reconcile. It is an analysis to steer the next probes, not a design. The questions in §6 are open.

## 1. The framing
Your words (GOAL §1): "1. Focus, a side job 2. Memory, add context 3. (Behind the scene) Maintain both AI and human memory structure".
- **Focus** watches one piece of work from outside the chat. It holds the goal above the current activity and judges whether the work still improves. It rarely speaks up, and only in a note beside the reply. It never rewrites a reply.
- **Memory** gives the AI facts it lacks, as plain context. Often it gives nothing. No rules, no memory talk, no unstated facts, no lessons across projects.
- **Maintenance** keeps one correct, attributed core of your knowledge and actual work. From it, it builds records, work cards (per piece of work: goal, versions, best version, decisions, ruled-out options) and the index. Nothing is required of you; corrections are optional.

## 2. How the jobs fit
One core. Every write goes through one code path, the gate; models only propose. Focus writes live session state; Maintenance turns it into long-term records afterwards.

| Job | Reads | Writes | Speaks to |
|---|---|---|---|
| Focus | your turns, diffs, renders, work card | live state, verdicts | you, rarely; the AI only when a pause denies an edit |
| Memory | records | what it gave, missed, leaked | the AI, silently |
| Maintenance | transcripts, exports, commits, signals, corrections | archive, work ledger, scoped records, index | you, via rare capped confirm items in the index |

Timing. Chat start: Focus loads the card; Memory pushes, often nothing. Each message: Focus classifies the turn; Memory only offers its tool. End of turn: Focus snapshots and starts its judge; Maintenance queues capture. Compaction, clear, fork: both reload. Nightly: Maintenance builds records.

Seam rules [L]: Memory goes only into the model's context. Focus goes only to you, and shares one note budget with any memory note. Text Northstar shaped never counts as you adopting an idea.

## 3. Each job

### Focus
**Purpose.** In both your examples the AI forgot nothing. It followed each latest message and lost what the session was for. Memory cannot fix that.

**Known [E].**
- Never probed. Round 4 judges matched your top pick in 1 of 12, so judges need calibrating on your marks.
- Website: 20 messages over 9 days; 56 screenshots, on rows 1, 2, 5, 13, 14 and 18 only. Across its 11 transcripts, most edits ran in subagents or Bash (539 vs 224 Edit/Write calls; about 8,700 Bash). Checkpoints miss both (code.claude.com/docs/en/checkpointing), so most versions must be rebuilt another way.
- Prompt rules did not steer the model (low confidence, one case). /goal likewise judges with a separate model (code.claude.com/docs/en/goal).
- The 87% drift cut from specific corrections came from a simulated persona (round 2 note 11). Models also break decisions they can restate (DriftBench, up to 99%). That is model-side drift, not your user-led drift.

**Untested.** Inferring the higher goal; a vision judge's "worse" vs your taste; text work; handoff vs continuing.

**Leans [L].**
- Goal: inferred one level up or inherited from the card; never asked up front. The first note states it, so correcting it takes one move. It stays out of the AI's context (Q5).
- Best version: the one you praised, else the judge's pick, plus your pin. State lives per piece of work.
- "Worse": a vision judge compares versions in both orders and checks that praised parts survive. The note shows best and current side by side.
- Decisions: a cheap per-reply check against the card's decisions and ruled-out options. A break is told to you (to the AI too: Q6).
- Speak only past an evidence gate: persistent signal, two judgments agree, no pivot, cooldown, cap, a higher bar after each dismissal.
- Delivery: a detached judge writes to the card. You see its note through a synchronous hook's systemMessage or an OS notification. Async hook output reaches only the AI [E, code.claude.com/docs/en/hooks]. Check that the desktop Code tab shows it.
- Firmness: a setting. Default "note, then pause", pending the marks. A pause holds your next prompt or denies the next edit until you answer [E]. Not /goal or Stop-hook blocks, which keep the AI working [E, learn.chatgpt.com/docs/hooks].
- Fresh session: a git branch of the best version's files, plus a new chat seeded with the goal and that version. Never automatic. Not /branch, which copies the conversation.

**Main risk.** False alarms get Focus switched off.

### Memory
**Purpose.** Continuity across chats and after compaction, without re-explaining.

**Known [E].**
- Strict selection found 9 of 10 required items and nothing off-topic. Earlier rounds: memory made the AI echo you.
- Round 4 top picks: none 3, parallel 2, in-prompt 1 (weak). Memory won by supplying project facts the model lacked. Replies that presumed context lost.
- Model-pulled calls are the least reliable channel (round 3 note 19, secondary).

**Leans [L].**
- Your 2026-10-14 defaults: goals you stated, personal knowledge (seen in a second context) only when very strongly linked, and the working-style profile. Project facts come from each product's own files, so round 4's wins depend on those files.
- Other setting value (Q11): Northstar also gives dated project facts those files lack: what a thing is, state, decisions, ruled-out options, results.
- Your positions come back only when the model asks. No claims about you beyond the profile (Q15). One provenance line, no instructions (Q12).
- Link test: would a good expert have to ask you this first? Empty by default.
- Hook surfaces: a tiny push plus a tool. Chat apps: the tool only, the weakest channel, so a continuity risk. Fallback: a check you invoke, or a boot line.
- Push at chat start. Mid-session, push only after compaction, clear or fork. The tool is always there.

**Main risk.** Inside one product, CLAUDE.md and vendor memory already help. Gain may show only across products [L].

### Maintenance
**Purpose.** A correct, attributed core that stays correct when one model call loses focus. Code holds state and write authority.

**Known [E].**
- Extraction credited 88-96% correctly; half were AI ideas you adopted. Value judged at capture matched you about 48%, which is chance. Nothing has run on real data.
- Retention (code.claude.com/docs/en/claude-directory): these sessions began in the desktop app, so Claude Code 2.1.295 keeps their transcripts at any age, unless org-managed settings differ (not checked). File snapshots and large tool outputs still expire 30 days after last save, from about 2026-11-07.
- Codex holds about 73 local session files since Oct 7, unused so far.

**Leans [L].**
- An immutable archive plus an append-only event log; views are rebuilt from it.
- Value is deferred until evidence: recurrence, building on it, a second context, committed work. Delivery never counts. Deferral gates promotion to the personal core and index, not continuity in the same work.
- Scope starts narrowest at capture; widening needs a cited second context. Structure changes come from a fit test, checked twice, with your pins.
- What to learn: open questions and next steps from your own words, shown in the index (Q8).
- Work: pointer, hash, permalink, small snapshot. One local queue per device; one home machine runs maintenance under a lock.

**Main risk.** The value threshold may not be learnable from your data yet.

### Surfaces
| Surface | Focus | Memory | Capture |
|---|---|---|---|
| Claude Code | Full [E] | Full; small margin over CLAUDE.md [L] | Verbatim; snapshots expire |
| Codex | Most; systemMessage shown; SessionStart covers compact, fork [E] | As Claude Code | rollout JSONL via transcript_path, "not a stable interface" [E] |
| Claude Desktop chat | Partial: tool, your check, handoff | Model-pulled | Model reports, exports |
| ChatGPT Desktop chat | Partial, weaker | Model-pulled; custom MCP reportedly needs public HTTPS (docs.pieces.app/products/mcp/chatgpt-developer-mode; verify) | Exports |

Windows: as Mac for Claude Code and Codex [E]. iOS and web: code runs via Remote Control on a computer; chat apps work only via a remote MCP endpoint; capture is by explicit share (connector-strategy.md).

## 4. Gaps and overlaps [L]
- **Evaluation:** each job is tested against your real apps: focus vs marks, memory vs blind picks, maintenance vs audits, index vs a recall task. No uncalibrated judge decides.
- **One channel on chat apps:** Focus speaks via a tool result the model surfaces (unreliable), an MCP App widget (unverified), or a check you invoke.
- **Goals:** Maintenance stores your stated goals; Memory delivers them; Focus holds the inferred goal outside the AI's context.
- **"Don't drift from what was established" (§3.3):** before compaction, Focus's decisions check covers it; after, Memory pushes the session's facts again.
- **Shared:** one delivery layer under all jobs; captured text is data; per-vendor rules; deletion on request.

## 5. What to test next
0. **Preserve data (Q1).** Copy into ~/northstar-probe: transcripts, subagent logs, file snapshots, tool outputs, Codex sessions. Raising cleanupPeriodDays is your call.
1. **Focus replay, website.** Now: rebuild site states from Write/Edit inputs in main and subagent logs, in time order, checked against the screenshots; flag Bash gaps. After the marks, replay turn by turn. Arms: model alone; a watcher with the goal card; plus a best-vs-current visual check; each with inferred and stated goal. No memory arm: no website records exist, and Northstar's would cross projects. Pass bar, set in advance: ≥1 hit within ±1 message of a mark, ≤1 false alarm, your best version, and beats a random speaker with as many notes. Then you blind-pick among the arms' messages. The interview chat stays held out.
2. **Maintenance replay, Northstar plus website.** Six injected faults; a 15-minute marking page. Pass: scope wrong ≤10%; no cross-project leaks; code catches every structural fault; the keep rule beats 48% by a preset margin on a preset item count. If too few items recur, report the keep rule as not yet judgeable.
3. **Memory replay split by date.** About 12 first messages, ≥3 repositories (Q1). Each repo at the message's date; vendor memory frozen, else off in every arm; uncontrolled factors listed. Arms: real app; plus push; plus tool. Then 12-16 blind pairs. Pass: ties or beats the real app, no presumed context, no leaks, a third fewer re-explanations.
- Beside step 1: tool-call rate on Claude Desktop chat. ChatGPT waits on Q14.

All runs: spend guard, resumable steps, outside this project's memory index.

## 6. Questions only you can answer
Full wording is in the question list. **Now:** 1. Copy the raw data, and use the website plus one or two other personal repos? 2. Best pictured row (now asked on the marking page)?
**Before the focus replay:** 3. "Side job": beside the chat, or ranked below memory? 4. Reuse a goal from an earlier chat of the same work? 5. A confirmed goal as one plain line in the AI's context? 6. Tell the AI too when it breaks a decision?
**Later:** 7. Index on demand: Memory, or a fourth "recall" job? 8. What-to-learn: index, Focus note, or both? 9. Who brings knowledge up "at the right moment"? 10. Ideas across contexts: on request, once personal, or never? 11. Project facts: product files only, or Northstar too? 12. One fixed line marking memory as data? 13. Partial focus on desktop chat apps? 14. A public HTTPS endpoint for ChatGPT under "local now"? 15. Working-style profile? 16. Hidden project-only records for promotion and conflicts?

## Not changed
- Deletion: went further than proposed. The docs keep desktop-started transcripts, so only snapshots and tool outputs expire.
- Step 3 vendor memory: frozen first, not simply off, since the baseline is the real app.
- Windows, iOS and the glossary: one line each instead of columns and a term list, to fit the size limit.
