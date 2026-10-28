# Design review record: Northstar v0.1 → v0.2

*2026-10-07. Lead architect's adjudication of the adversarial review of `docs/design/DESIGN.md` v0.1. Seven reviewers (problem fit, engineering, epistemics, human experience, AI safety and privacy, evaluation, scope and simplicity) filed 92 findings: 17 blockers, 60 major, 15 minor. The revised design is `DESIGN.md` v0.2 (reviewed, pending approval); affected ADRs are revised in place and two new ADRs (0015, 0016) were added.*

**Dispositions:** 51 accepted, 41 accepted with modification, 0 rejected in full. Specific recommendations declined inside accepted findings are listed under "Rejected findings and why" at the end.

**How contested claims were checked.** Before acting, the lead architect re-verified the factual claims the findings depend on, reading keys and paths only, never message content:
- `~/.claude/projects`: 208 JSONL files, 196 under `<project>/<session>/subagents/workflows/<wf>/agent-*.jsonl`, 12 top-level; 10 of the 12 top-level sessions sit in 6 desktop scratch-workspace folders (`scratch-YYYY-MM-DD-xxxxxx`). Confirms engineering-1, engineering-6, human-13, scope-simplicity-2.
- Top-level record types: 1,198 `attachment` lines, including 25 `queued_command` (8 with `origin.kind: human`, 17 task notifications) and 24 `prompt_snapshot`; 106 human-origin user turns, 10 with a separate `<system-reminder>` text block; 6 `[Request interrupted…` lines. Confirms engineering-4, engineering-6 and ai-safety-privacy-1.
- The agent shell exposes `CLAUDECODE`, `CLAUDE_CODE_SESSION_ID`, `CLAUDE_CODE_CHILD_SESSION`, `CLAUDE_CODE_EAGER_FLUSH`, `CLAUDE_CODE_ORGANIZATION_UUID` and `CLAUDE_CODE_ACCOUNT_UUID`. Confirms the transcript-pull and egress-by-account recommendations are implementable.
- Codex: 6 rollouts; 4 have `session_meta` with `thread_source: subagent`, `forked_from_id`, `parent_thread_id` and `subagent_history_start_ordinal`. `~/.codex` also holds `memories_1.sqlite`. Confirms engineering-6 and ai-safety-privacy-11.
- Calendar: 2026-10-14 is a Wednesday, 2026-10-17 and 2026-11-07 are Saturdays. Confirms epistemics-1's weekday errors.
- v0.1 used gendered pronouns for Jack on 33 lines of DESIGN.md and in 11 of 15 ADR files, including the pack header shipped to AI tools. Confirms problem-fit-12.
- Research citations behind problem-fit-1, -4 and -7 ([01] synthesis condition 1, implications 11 and 12; SYN §1.1 and T4) read as quoted. SYN also records [05]'s view that fragments attached to nothing "may be legitimately disposable", which moderated problem-fit-4.

**Length.** DESIGN.md v0.2 is about 19.7K words against about 17.5K for v0.1. The v0 build specification inside it is roughly half its former size; the growth comes from the normative fold rules (§5.6), the explicit scope table the review asked for (§1.2), and the learning path (§5.7). §12 will be extracted into a ≤250-line `BUILD-v0.md` after approval (scope-simplicity-12).

**Net complexity of v0 went down.** Additions to v0: the takeaway card variant, a note option on capture cards, close answers as notes, `form: aim`, the monthly review card and `part_of`, `basis`, an optional `would_change_if`, `reinstates`, `decided_at_q`, `questions[]`, an undo buffer, the sort and in-flow-audit due cards, a calendar file and notification, `ns pause`, the egress check, ignore terms and the write guard. Each is a field, an enum value, a card variant reusing an existing flow, or a few dozen lines. Cuts from v0: chat-mode Sessions with their JSON step API and pending/verified state machine; the whole LLM prep pipeline (jobs, six gates, three prompts, digests, counterpoints, hidden guesses, the maintain skill); the Codex parser; the notes adapter; ranking weights, load rules, re-entry and fresh-start modes; catch trials; echo detection by exposure, exposure windows and `ns exposed`; six of seven generated views; `ns context` and `ns check`; `--id` and `--pattern` excision; the six-arm evaluation runner and signature drafting; the pack trial; parent, global and provider-filtered scopes; the metadata-only archive mode; four machine ops and the `auth` field. The machine vocabulary fell from 13 ops to 7, and v0's size estimate from 3,000–3,500 lines (reviewers estimated 6–8K as specified) to 2,000–2,500.

---

## Summary table

| ID | Reviewer | Severity | Title | Disposition |
|---|---|---|---|---|
| problem-fit-1 | problem-fit | blocker | "I learned how X works" has no home and no path in | Accept-modified |
| problem-fit-2 | problem-fit | blocker | The evaluation cannot falsify the pivot | Accept-modified |
| problem-fit-3 | problem-fit | major | Ladder rungs for learning, consolidation and goals cannot fire | Accept-modified |
| problem-fit-4 | problem-fit | major | Notes are fragments by the research's own definition | Accept-modified |
| problem-fit-5 | problem-fit | major | Goals forced into questions get parked out of sight | Accept-modified |
| problem-fit-6 | problem-fit | major | Contradictions between Jack's own positions never surface | Accept-modified |
| problem-fit-7 | problem-fit | major | Consolidation of the whole is refused, not designed | Accept-modified |
| problem-fit-8 | problem-fit | major | The frame is justified and validated on unrepresentative material | Accept-modified |
| problem-fit-9 | problem-fit | major | Approval questions default to the design's frame | Accept |
| problem-fit-10 | problem-fit | minor | The pack's index gives agents nothing to fetch | Accept-modified |
| problem-fit-11 | problem-fit | minor | Uncertainty is a level, reasoning one line; no crux | Accept-modified |
| problem-fit-12 | problem-fit | minor | The design assumes Jack's pronouns | Accept |
| engineering-1 | engineering | blocker | Scoping by cwd misses the desktop app's scratch chats | Accept-modified |
| engineering-2 | engineering | blocker | Fold and as-of semantics cannot express the fixture's cases | Accept |
| engineering-3 | engineering | major | The 18 ops cannot produce several flows and views | Accept-modified |
| engineering-4 | engineering | major | Authorship verification is weak and fragile; `auth` is mutable state | Accept |
| engineering-5 | engineering | major | Chat-mode Sessions are impractical; maintainer isolation does not exist | Accept |
| engineering-6 | engineering | major | Adapter paths, record types and Codex rules are wrong | Accept |
| engineering-7 | engineering | major | Excision verification is vacuous; pattern antibodies contradict themselves | Accept-modified |
| engineering-8 | engineering | major | Archiving on every command makes reads into writers | Accept |
| engineering-9 | engineering | major | v0 is about twice its stated size | Accept |
| engineering-10 | engineering | minor | 4-character IDs do collide under merge | Accept |
| engineering-11 | engineering | minor | Byte-identical index and stable pack hash are brittle | Accept |
| epistemics-1 | epistemics | blocker | The worked example labels system-generated content as Jack's | Accept |
| epistemics-2 | epistemics | blocker | Revisions drop belief time | Accept |
| epistemics-3 | epistemics | major | As-of ignores its qualifiers; example outputs are wrong | Accept |
| epistemics-4 | epistemics | major | "Rests only on AI" is vacuous; `basis` was dropped | Accept-modified |
| epistemics-5 | epistemics | major | Lexical echo detection is unsound | Accept-modified |
| epistemics-6 | epistemics | major | The change-type vocabulary has holes | Accept-modified |
| epistemics-7 | epistemics | major | Reversals and undos cannot be represented | Accept |
| epistemics-8 | epistemics | major | Session decisions are automatically "contemporaneous" | Accept |
| epistemics-9 | epistemics | major | One question per position; revisions drop grounds | Accept-modified |
| epistemics-10 | epistemics | minor | "Scope" means two different things | Accept-modified |
| epistemics-11 | epistemics | minor | The lowest confidence band is broken; test-retest is noise | Accept-modified |
| epistemics-12 | epistemics | minor | Jack's own observations cannot be grounds | Accept-modified |
| epistemics-13 | epistemics | minor | Positions never go stale | Accept |
| human-1 | human | blocker | Evaluation needs many unbudgeted hours | Accept |
| human-2 | human | blocker | First value arrives after 2.5 hours and two weeks | Accept |
| human-3 | human | major | Week-0 homework assumes a history that doesn't exist | Accept |
| human-4 | human | major | G0 tests novelty on the wrong corpus, passes on willingness | Accept |
| human-5 | human | major | Nothing cues the weekly slot | Accept |
| human-6 | human | major | Chat as the default venue breaks the card UX | Accept |
| human-7 | human | major | Pending authorship causes limbo and repeat work | Accept |
| human-8 | human | major | Overloaded keys and no undo make mis-keys permanent | Accept-modified |
| human-9 | human | major | The six-way change question can't be applied consistently | Accept-modified |
| human-10 | human | major | Kill criteria fire on noise and normal absences | Accept |
| human-11 | human | major | Jack's pages open with Jack's lapses | Accept |
| human-12 | human | major | Seven views nobody reads | Accept |
| human-13 | human | major | One-time directory classification doesn't fit the desktop app | Accept-modified |
| human-14 | human | minor | In-flow offers have no daily cap; G1 forces a decision | Accept |
| ai-safety-privacy-1 | ai-safety-privacy | blocker | Verification checks text appears, not that Jack wrote it for this card | Accept-modified |
| ai-safety-privacy-2 | ai-safety-privacy | blocker | The global import puts personal decisions into work sessions | Accept-modified |
| ai-safety-privacy-3 | ai-safety-privacy | blocker | "No new exposure" is enforced only at prep dispatch | Accept-modified |
| ai-safety-privacy-4 | ai-safety-privacy | blocker | Raw archive keeps secrets and tool output; retention raised globally | Accept-modified |
| ai-safety-privacy-5 | ai-safety-privacy | major | Maintainer isolation doesn't work; other untrusted paths exist | Accept-modified |
| ai-safety-privacy-6 | ai-safety-privacy | major | `auth: tty` does not establish that Jack acted | Accept |
| ai-safety-privacy-7 | ai-safety-privacy | major | Agent-mode Sessions leak private and work records | Accept-modified |
| ai-safety-privacy-8 | ai-safety-privacy | major | Work-scope rules mis-ordered; "metadata" undefined; Q6 unanswerable | Accept-modified |
| ai-safety-privacy-9 | ai-safety-privacy | major | Exports have no scope rule and are priced on the wrong provider | Accept |
| ai-safety-privacy-10 | ai-safety-privacy | major | Excision leaves known copies; the zero-hit grep can pass falsely | Accept-modified |
| ai-safety-privacy-11 | ai-safety-privacy | major | Codex memories ignored; vendor memory outlives retractions | Accept-modified |
| ai-safety-privacy-12 | ai-safety-privacy | major | The sycophancy defence is untested against just-in-time fetching | Accept |
| ai-safety-privacy-13 | ai-safety-privacy | major | Codex has no AGENTS.md import; its sandbox blocks `ns` writes | Accept |
| ai-safety-privacy-14 | ai-safety-privacy | minor | Day-level cold-pack arm mismatched and underpowered | Accept |
| evaluation-1 | evaluation | blocker | The G3 rule cannot detect plausible effects | Accept |
| evaluation-2 | evaluation | blocker | Archive gold is impossible or circular for most probes | Accept |
| evaluation-3 | evaluation | blocker | Jack's evaluation time is understated about 10× | Accept-modified |
| evaluation-4 | evaluation | major | Arms see different information | Accept |
| evaluation-5 | evaluation | major | Budgets cannot be matched; full context contradicts corpus size | Accept |
| evaluation-6 | evaluation | major | The cross-family judge is unavailable and breaks P13 | Accept |
| evaluation-7 | evaluation | major | Safeguards against designer = user = rater are nominal | Accept |
| evaluation-8 | evaluation | major | Kill criteria rest on tiny samples and an invalid catch trial | Accept-modified |
| evaluation-9 | evaluation | major | The signature test contradicts itself | Accept |
| evaluation-10 | evaluation | major | E9 lets a null result remove the own-words guard | Accept |
| evaluation-11 | evaluation | major | The live pack trial lacks power and a measurable baseline | Accept |
| evaluation-12 | evaluation | minor | G0 tests an atypical Session and passes on intention | Accept |
| evaluation-13 | evaluation | minor | The speaker audit cannot establish 98% precision | Accept |
| evaluation-14 | evaluation | major | About 20 measurements, most deciding nothing | Accept |
| scope-simplicity-1 | scope-simplicity | blocker | v0 is twice its budget with no cut order | Accept-modified |
| scope-simplicity-2 | scope-simplicity | blocker | Scratch-workspace sessions would never be archived | Accept |
| scope-simplicity-3 | scope-simplicity | major | The ratchet ratio and time kill contradict the plan | Accept-modified |
| scope-simplicity-4 | scope-simplicity | major | Ledgers store derivable state and duplicates | Accept-modified |
| scope-simplicity-5 | scope-simplicity | major | Schema holes invite agents to invent fields | Accept |
| scope-simplicity-6 | scope-simplicity | major | LLM prep is built before there is data for it | Accept-modified |
| scope-simplicity-7 | scope-simplicity | major | Ranking weights and load rules are premature and duplicated | Accept |
| scope-simplicity-8 | scope-simplicity | major | Catch trials have nothing to catch | Accept |
| scope-simplicity-9 | scope-simplicity | major | User-level import defeats closed scopes; P13 forbids the pack | Accept-modified |
| scope-simplicity-10 | scope-simplicity | major | Echo and exposure machinery serve a closed channel | Accept |
| scope-simplicity-11 | scope-simplicity | major | The six-arm eval runner is premature and infeasible to grade | Accept |
| scope-simplicity-12 | scope-simplicity | major | 13K words and 14 ADRs restate numbers and have drifted | Accept-modified |
| scope-simplicity-13 | scope-simplicity | minor | Full excision in v0 can shrink to source excision | Accept |
| scope-simplicity-14 | scope-simplicity | minor | Notes adapter, Codex parsing and two-clock as-of have no v0 data | Accept-modified |

---

## Reviewer verdicts

**Problem fit.** The core bet is right, and I would not change it. Understanding forms in Jack through own-words integration on a bounded schedule, and the system's job is to preserve the raw record, feed that integration cheaply, and keep a small, attributed record. The research supports this strongly. The pivot to a commitment ledger is justified against AI-written synthesis and vendor-style profile memory. But it over-corrects: it narrows "what Jack holds" to stances and decisions. That drops what the research itself recommends keeping: person-authored explanations of core models ([01] implication 12, SYN T4), goals as demand anchors ([05], SYN P9), and first-class restructuring ([01] implication 11). It also drops the learning hooks that every one of proposals B, C and D carried. As a result, the brief's central scenario has no path into the record: learning how something works from AI conversations, research and reading. Ideas land in write-once notes that never resurface. Contradictions between Jack's own positions, especially across work and personal scopes, cannot surface. Foundation #2 is met only one record at a time. The ladder rungs that would restore coverage (R2, R6, R7) have triggers that cannot fire, and the probes and decision rule cannot detect the gap. Jack would likely not recognise this as the knowledge system they asked for, and the approval questions do not let them redirect it. The fixes are additive and need no new kinds. With the two blockers fixed (knowledge representation and capture, and knowledge probes in the pre-registered evaluation) plus the approval framing question, the design is ready to build.

**Engineering.** Not ready to build as written, but close; the fixes are mostly cuts and pinned-down rules, not new machinery. Two things must be settled before M0/M1. First, scope is keyed on cwd, but about 88% of Jack's typed words are in per-chat desktop scratch workspaces that the defaults archive metadata-only, which loses the raw record P1 exists to protect. Second, the fold/as-of semantics cannot express revise-time held_from, retroactive linking, splits or the unknown state, so neither fold.py nor its "spec" fixture can be written. The log-shape check confirms the core markers but shows wrong subagent paths, unhandled attachment records (including human queued messages) and Codex wrappers that would wreck self precision; all are fixable in M0 with fixtures built from the real shapes. Authorship verification should switch from relaying text to reading the transcript directly via CLAUDE_CODE_SESSION_ID. Chat-mode Sessions should leave v0 in favour of the desktop app's terminal panel. Excision verification must decode the compressed blobs. With those changes and the listed deferrals, a v0 of about 3–3.5K lines in about 10 part-time sessions is plausible; as specified, v0 is closer to 6–8K lines.

**Epistemics.** The conceptual core is the right size and mostly right: holder-fixed positions, encounters only on relate, correction kept separate from revision, tension-as-question, frozen decisions, and deferring the proposition table. But v0.1 is not ready to build. The canonical worked example attributes code- and AI-written question text, reasons, decision fields and pack lines to Jack. `position.revise` drops the P3 belief-time field, so every change of mind is dated to the Session. As-of treats `no_later_than` as exact and invents belief-time confidence, and the example outputs are wrong under the design's own semantics. J6 is broken by definition: "rests only on AI" is vacuous and blind to adoption, C's `basis` was dropped, and echo detection cannot see echoes. Integrity grades, reversals and the change-type vocabulary have gaps that produce wrong derived outputs. Nearly every fix is a small edit to the schema or the runner. Once applied and the fixtures are regenerated from a corrected example, the model is ready to build.

**Human experience.** Not ready to build. There are two blockers. First, the evaluation plan asks Jack for many hours of grading, auditing and labelling that no budget counts, and that work alone would trip the 30 min/week stop line. Second, the early-reward schedule contradicts the build plan and the ratchet: the week-1 pack lands around day 14, and E8 sits behind a v1 gate that needs two weeks of use first, so Jack would put in about 2.5 hours of homework and two weeks of building before the system gives anything back. The majors cluster on the chat-default Session, card ergonomics, the absence of any cue for the weekly slot, and an audit posture with fragile kill criteria. All of these can be fixed by cutting or reordering: a ≤45-minute onboarding with a same-day decisions pack; 3–5 starter questions; probes moved to week 3; terminal-default Sessions with prep before a cued slot; numbered options with undo; a 3-way change type; one rubber-stamping instrument; a ≤2 h evaluation budget; and pause-aware kill criteria with minimum samples. With those changes the core bet becomes cheap and honest to test, and v0 shrinks.

**AI safety and privacy.** Not ready to build as written, but it gets there with fixes that mostly cut or simplify. Five problems block building: agent-relayed answers are "verified" when the reply text appears in any human turn, so single keys, queued messages and agent-worded decision text slip through or void falsely; the pack in the user-level CLAUDE.md reaches every session, including work and client repos, framed as override-level instructions; "no new exposure" is enforced only at prep dispatch while packs, Session relays, `ns context`, the cross-family judge and the week-0 wizard all break it; the raw archive keeps secrets and unused tool output indefinitely, and the Day 0 `cleanupPeriodDays` change makes vendor copies of work logs permanent; and Codex has no AGENTS.md import mechanism. The proportionate fixes: read Jack's answer straight from the transcript after a card nonce; import packs only in personal project CLAUDE.md files and scope JIT reads by cwd; one egress check keyed on provider and account; redact secrets and stub tool output at ingest with default vendor retention; cut Codex pack delivery from v0. With those, plus the scope-rule ordering fix, a defined "metadata", a scope rule for exports and a `tools: Read` maintainer subagent, M0 can start.

**Evaluation.** The v0 build can go ahead after fixes, but §10 is not ready and should be rewritten before pre-registration. The G3 rule cannot detect plausible effects: with about 28 decision probes the minimal detectable effect is about 17 points, and simulated P(keep) for a true +10–15 advantage is 3–24%. Its gold is infeasible for current-position and forward-history probes and circular where feasible. Its arms differ in what information they can see, so it measures access rather than structure. Its cross-family judge breaks P13. The kill criteria rest on samples of 3–4 events, an invalid catch trial and a self-contradictory signature test. Jack's evaluation workload, roughly 15–25 hours over 8 weeks, sits outside the 30-minute budget and would itself drive abandonment. E3's only consequential branch could discard the P3 fields. Replace it with a lean plan: automatic CI and usage logs, card verdicts, three consistent triggers, and two adequately powered tests (scripted E10, and NS vs a properly built B5 on about 100 auto-generated probes with event gold), with Jack capped at ≤3 hours.

**Scope and simplicity.** Not ready to build as written, but close once cut down. The architecture is right: C's substrate, D's Session, A's non-recoverable fields, a decisions-first pack. The plan applies P14 to everything except itself. v0 is about twice its 10-session budget with no cut order, and carries about a dozen mechanisms that cannot be exercised on two weeks of thin, Northstar-dominated data. Two problems must be fixed first: the desktop scratch-workspace sessions, most of Jack's actual sessions, would be archived as metadata only; and the canonical ledger has schema holes and stores derivable state. After four changes it is ready: a five-session v0, retention decoupled from scope, closed and de-duplicated ledger ops, and a short BUILD-v0 spec as the only file build agents follow. None of these cuts loses a P3 field.

**Keep lists.** Every item on the seven keep lists survives in v0.2: archive first with deterministic speaker classification and whole-file orchestrator tagging; quotes cut by code with a speaker gate; two append-only JSONL ledgers outside git with a disposable index; the correction/revision split with an unanchored change question and fixture-first as-of; `held_from` with its qualifier; tension-as-question with `held` and no automatic resolution; decision freezing with Jack-typed expectation and confidence, `considered_ai`-style separation of AI reasons (now: the agent may only point at Jack's quotes), and the `endorsed` path; the bounded Session with recall before reveal, fixed stems, counterpoints only after answers (v0.5), a hard cap and no carry-over; the decisions-first pack with positions out by default and no instruction kind; the write-path CI suite; the use gate and mechanism ledger with cut rules; the degradation ladder; the plain-journal question; measurement as a by-product of card verdicts; and the scripted E10. Where a keep-list item conflicted with another finding (the ratchet ratio, the week-0 G0, raised `cleanupPeriodDays`), the resolution is recorded below.

---

## Conflicts between reviewers, and how they were resolved

1. **Add coverage (problem fit) vs cut scope (scope, engineering).** Coverage was added only as fields, enum values and card variants that reuse existing flows (takeaway, aim, notes, monthly review). Every heavier ask was deferred behind a measurable trigger (position-to-position cards at ≥20 positions; lint; LLM prep). The cuts are far larger than the additions.
2. **Pack delivery: user-level (scope-simplicity-9) vs per-project (ai-safety-privacy-2).** Most of Jack's chats are folderless scratch chats, which have no project `CLAUDE.md`. Claude Code reads `CLAUDE.md` in every parent folder, so the import goes in parent folders (`~/Personal/CLAUDE.md`, and the scratch-workspaces folder if those chats are personal). A user-level import is allowed only if Jack confirms no client work happens in Claude Code on this machine.
3. **The ratchet's 3× build/use ratio (evaluation keep list) vs "delete the ratio" (scope-simplicity-3).** During the v0 build the ratio is meaningless, so it is replaced by T3: no building in a week without use, after G1. That keeps the anti-builder's-trap intent and stops the rule firing on the plan itself.
4. **Raise `cleanupPeriodDays` (human keep list) vs keep the default (ai-safety-privacy-4).** The oldest log is two days old and B1 archives everything within days, so a permanent raise buys nothing and keeps work copies forever. Day 0 offers an optional temporary raise to 60 days as insurance, and `ns doctor` prompts the revert after 14 clean days.
5. **Keep the week-4 false-endorsement audit (human-1, human-11) vs replace it with continuous tracking (evaluation-8).** The audit is the only direct check that recorded entries are really Jack's, so it stays, but as an incident finder with no percentage threshold; continuous `not mine`/`misquoted` rates run alongside.
6. **Change types: drop `sharpen` (human-9) vs define it (epistemics-6).** Dropped. The option set is "my view changed / the world changed / the record was wrong / not sure", and "not sure" still records the new view (epistemics-6's key point). The correction/revision split, the one irreversible distinction, is kept.
7. **Fixture size: ~8 scenarios (scope-simplicity-14) vs retroactive linking, splits and three-valued as-of (engineering-2, epistemics-3, epistemics-7).** Twelve scenarios, one per normative rule cluster.
8. **Agent-written agenda in v0 (scope-simplicity-6) vs unverified subagent isolation (engineering-5, ai-safety-privacy-5).** v0 uses only the deterministic floor; the agent agenda arrives in v0.5 after a spike of a `tools: Read` subagent. G0's hand-built agendas already show what an agent adds.
9. **Evaluation budget: ≤2 h (human-1) vs ≤3 h (evaluation-3).** ≤2 h, itemized; it satisfies both.
10. **G0 timing: before any code (v0.1, scope keep list) vs don't hold M0 (human-4).** Archiving and the pack proceed at once; only the Session runner waits for G0.
11. **G0 material from exports (problem-fit-8) vs same-origin exposure (ai-safety-privacy-3).** G0 uses exports, but each export is read only by an agent of the provider that produced it.

---

## Findings and dispositions

Each entry gives the problem and recommendation in brief, the disposition with its rationale, and where DESIGN.md changed.

### Problem fit

**problem-fit-1 · blocker · "I learned how X works" has no home and no path in**
- *Problem:* Only stances, decisions, questions and notes could enter the record; capture cards cited only self spans, so a learning conversation (knowledge in assistant turns) yielded nothing, and AI-only understanding was invisible to J6.
- *Recommendation:* Position also covers understanding on a "How does X work?" question; add a `takeaway` variant inside the capture cap, triggered deterministically, recall before reveal, with AI lineage.
- *Disposition:* **Accept-modified.** The core fix is adopted as proposed: no new kind or op, a takeaway variant inside the ≤3 capture cap, triggered when most self turns are questions and the assistant wrote ≥5× more. The reveal shows the code-cut start of the assistant's answer (digests do not exist in v0), and AI origin is recorded through the restored `basis` field and auto-filled `prompted_by` rather than by minting an encounter, which is simpler and feeds the same "rests only on AI" flag.
- *DESIGN.md:* §0, §1.2 (scope table), §1.3 (J7 primary), §3.2, §5.7 (learning example), §6.5, §7.2.

**problem-fit-2 · blocker · The evaluation can only measure the jobs the pivot chose**
- *Problem:* Probes and the decision rule covered stance, decision, history and honesty only; nothing measured learned knowledge, so the frame validated itself.
- *Recommendation:* 4 of the 20 week-0 probes become knowledge probes; add a J7 bucket; use close-card answers as a monthly coverage instrument with >20% "no home" as a pivot signal.
- *Disposition:* **Accept-modified.** Week-0 probes were dropped (human-3, evaluation-2), so the knowledge category is built into the week-3 stems and the generated probe set instead, with a separately reported J7 sub-score. The close-card coverage instrument is adopted exactly, tagged at weeks 4 and 8, with the 20% pivot signal pre-registered.
- *DESIGN.md:* §10.2, §10.4, §10.5 (E1).

**problem-fit-3 · major · The rungs that would restore learning, consolidation and goals cannot fire**
- *Problem:* R7 needed "want to know" flags nothing records; R6 needed E7, which was N/A; R2's trigger was suppressed by phrasing goals as questions.
- *Recommendation:* Relabel as cut, or make triggers measurable (a `want_to_know` boolean, a scheduled E7, a direct count of aims).
- *Disposition:* **Accept-modified.** Triggers were made measurable from data the design now records, without the extra boolean: R7 counts positions created by takeaway cards; R2 counts aims; R6 runs E7 as a gate when its first trigger fires. FR23 is now true in v0 through takeaway and recall cards.
- *DESIGN.md:* §10.5 (E7), §14 (R2, R6, R7), Appendix B (FR18, FR23).

**problem-fit-4 · major · Notes are fragments by the research's own definition**
- *Problem:* Notes had no lifecycle, could not be reworded or retracted, never returned to prep, had no capture option, and the close card mapped to no op.
- *Recommendation:* Let `reword`/`retract` take notes, cite notes via `from:`, feed unattached notes to relate cards, add a note option, record close answers as notes.
- *Disposition:* **Accept-modified.** All four parts adopted using existing machinery: `reword` and the new kind-agnostic `record.status` accept notes; `prompted_by` (already present) links a note to the position it grew into; notes from the last 90 days, unattached first, are relate-card sources; capture cards gain `4 note`; close answers are `note.write` with `close: true`. SYN's caveat that unattached fragments "may be legitimately disposable" is honoured by the 90-day window rather than resurfacing forever.
- *DESIGN.md:* §3.2, §4.3, §6.5, §7.2.

**problem-fit-5 · major · Goals forced into questions get parked and vanish from the pack**
- *Problem:* Goals phrased as questions lose horizon and outcome semantics, compete for the 12 open slots, receive "park?" cards and drop out of the pack.
- *Recommendation:* `form: aim` on `question.open`, exempt from the cap and park card, reviewed monthly, listed in the pack; R2 counts aims.
- *Disposition:* **Accept-modified.** Adopted as proposed; the monthly review is the existing review card rather than a separate aim card. Aims read `answered` as achieved and `dissolved` as abandoned. A dedicated goal kind with horizon and cadence stays rung R2.
- *DESIGN.md:* §1.2, §3.2, §4.3, §5.2, §8.2 (pack lists aims), §14 R2.

**problem-fit-6 · major · Contradictions between Jack's own positions can never surface**
- *Problem:* No mechanism co-activates position with position, especially across scopes; LLM tensions are off.
- *Recommendation:* Deterministic local BM25 neighbours among current positions across all scopes, ≤1 P→P relate card per Session.
- *Disposition:* **Accept-modified.** Adopted, but scheduled for v0.5 behind a measurable trigger (≥20 current positions): in v0's first weeks there are too few positions for a neighbour search to find anything, and the monthly review already shows the whole question set at once. The reviewer's point that a local terminal display is not exposure is written into §5.4.
- *DESIGN.md:* §5.4, §12.1 (v0.5 list).

**problem-fit-7 · major · Consolidation of the whole is refused, not designed**
- *Problem:* Nothing reorganizes the question set; there is no act of domain-level consolidation; the backlog would take years to integrate; restructuring has only alias and split.
- *Recommendation:* Record the monthly write-up as Jack's position; a monthly agenda card (keep, park, answer, dissolve, alias, nest via `part_of`); state the trade plainly; seed backfill by question.
- *Disposition:* **Accept-modified.** The monthly review card is adopted (replacing one relate card that month), with nesting as a `part_of` relation value instead of a new field, followed by one unaided recall whose answer becomes a dated position: Jack's consolidation in Jack's words. The signature test it would have reused is cut (evaluation-9), so the recall card carries that role. The trade (≈7 integrations a week plus a monthly consolidation; everything else stays raw) is stated in §1.2 and approved at Q0. Backfill is seeded by question (≤3 historical spans per open question).
- *DESIGN.md:* §1.2, §3.3, §5.2, §6.7, §7.2, §15.2 (Q0).

**problem-fit-8 · major · The frame is justified and validated on unrepresentative material**
- *Problem:* §1.1 inferred from two days of build logs that the backlog is a future problem; G0 tested the ritual on Northstar coding sessions, where a decision ledger fits best.
- *Recommendation:* ≥3 G0 cards from web-chat exports including a learning conversation; rate whether cards touched "the knowledge I meant"; delay G0 rather than build on Claude Code data alone.
- *Disposition:* **Accept-modified.** G0 now uses material outside the Northstar build, with ≥3 export cards including a takeaway on a learning conversation. Because the build no longer waits for G0 (human-4), only G0 #2 waits up to 7 days for an export, and only the Session runner is gated. Exports are read by a same-origin agent (ai-safety-privacy-3). §1.1 now says plainly that the corpus is unrepresentative.
- *DESIGN.md:* §1.1, §12.1 (G0).

**problem-fit-9 · major · Approval questions default to the design's frame**
- *Problem:* Assumed answers mirrored the design; "learning-first" changed nothing structural; Jack was never asked whether the pivot is what they want.
- *Recommendation:* Add question 0; make the learning-first branch concrete; ask the success question open-ended.
- *Disposition:* **Accept.** Q0 opens §15.2 with the frame, the trade and what the system will not do. Learning-first now gives takeaways all capture slots, puts an explain-without-looking recall into every monthly review, halves R7's trigger, and makes the J7 sub-score E3's primary report (E9 itself is cut, per evaluation-10). Q12 is open-ended.
- *DESIGN.md:* §15.1, §15.2.

**problem-fit-10 · minor · The pack's index gives agents nothing to fetch**
- *Problem:* A count-only index means agents cannot know what exists, so just-in-time fetching never happens and the trial would test a strawman.
- *Recommendation:* A title index of questions with recorded views (no stance text) plus aims.
- *Disposition:* **Accept-modified.** Adopted, combined with ai-safety-privacy-12's narrower fetch rule: agents fetch when a task needs what Jack recorded about how something works or what was decided, and do not fetch positions to answer a request for their own recommendation. The two findings pull in opposite directions; the header now encodes both, and E10's pack-plus-skill arm measures the result.
- *DESIGN.md:* §8.2.

**problem-fit-11 · minor · Uncertainty is a level and reasoning one line; positions have no crux**
- *Problem:* Positions lack the cheapest structural form of uncertainty, what would change Jack's mind; long-form reasoning has no documented home.
- *Recommendation:* Optional `would_change_if`, prompted only for confident positions, used in ranking; document notes plus relate for long reasoning.
- *Disposition:* **Accept-modified.** The optional field is added, prompted only for `confident` positions (Enter skips). It is not used for ranking in v0, which has no ranking weights (scope-simplicity-7). Long reasoning lives in a note cited by `prompted_by`.
- *DESIGN.md:* §1.2, §4.3, Appendix A (D11).

**problem-fit-12 · minor · The design assumes Jack's pronouns**
- *Problem:* DESIGN.md and the ADRs used gendered pronouns for Jack, including the pack header sent to every agent.
- *Recommendation:* "Records Jack wrote or recorded"; use Jack, they or you everywhere.
- *Disposition:* **Accept.** Mechanical, and it matters most in the pack header. DESIGN.md, every ADR, the ADR README and JUDGING.md now use Jack or they/them. In the final edit before approval, the gendered references to Jack in proposals A and E were also changed to they/them; their content is otherwise unedited.
- *DESIGN.md:* throughout; §8.2 header.

### Engineering

**engineering-1 · blocker · Scoping by cwd misses the desktop app's scratch chats**
- *Problem:* About 88% of Jack's typed characters are in per-chat scratch workspaces, which fell to `unclassified` (metadata only, no model, no pack); a one-time classification cannot cover future folders; the NS_HOME exclusion also keyed on cwd.
- *Recommendation:* Archive every source raw and let scope gate only model use and packing; a built-in `scratch-workspaces/**` rule; per-episode scope via a one-key card; decision scope never from cwd; identify Session chats by session ID.
- *Disposition:* **Accept-modified.** Retention is decoupled from scope: everything except work is archived. Scratch chats get one setup answer (personal, or sorted per chat on a one-key due card). In-flow decisions take scope from `--scope` or default `personal` and are refused in work folders, never inferred from cwd beyond that. Session identification became moot because Sessions run in a terminal (engineering-5). Modified on one point: work is ignored entirely rather than archived raw, per ai-safety-privacy-8, because storing client logs at all is the open question.
- *DESIGN.md:* §1.1, §4.6, §6.4, §6.6, §8.4.

**engineering-2 · blocker · Fold and as-of semantics cannot express the fixture's cases**
- *Problem:* No `held_from` on revise; no retroactive linking; splits had no op and forks were lint errors; no single-head guarantee; `no_later_than` had no as-of meaning; world/sharpen `held_to` undefined; partial dates had no comparison rule.
- *Recommendation:* About ten normative rules, a `supersede` op usable between existing records, multiple heads, three-valued as-of, world/sharpen rules, interval comparison; write the fixture from the rules.
- *Disposition:* **Accept.** §5.6 now holds 13 normative rules and `supersede` replaces `position.revise` and `decision.supersede`. A confirmation rule (`last_confirmed`) was added so that bounds tighten from Jack's own live acts, which the worked example needed. The fixture has 12 scenarios written from the rules.
- *DESIGN.md:* §3.3, §3.5, §4.3, §5.6, §10.1.

**engineering-3 · major · The 18 ops cannot produce several flows and views**
- *Problem:* No op for unclassified restates, scope changes, lapsed decisions, decision corrections, reinstatement, note revision, build minutes or the do-not-assume line.
- *Recommendation:* Kind-agnostic `record.correct`, `record.status`, `record.rescope`; restate as unclassified revise; render do-not-assume verbatim; `ns log build`.
- *Disposition:* **Accept-modified.** The three kind-agnostic ops replace `position.correct`, `position.retract` and `position.confidence`'s overlap; the count stays at 18. Restates disappear as a separate flow: `ns revise` runs the same three-way question in a terminal, so no "unclassified" state exists. Do-not-assume lines render the superseded text verbatim. Build minutes are derived from archived `project:northstar` episodes (human-1) instead of a new command.
- *DESIGN.md:* §4.3, §7.4, §8.2, §10.7.

**engineering-4 · major · Authorship verification is weak where it matters and fragile where it doesn't**
- *Problem:* Single-key answers verify trivially; shell relay corrupts text; queued messages are missed (≈7% of human inputs); subagent `ns decide` resolves to the parent transcript; `auth: tty` is forgeable; mutable `auth` sat on immutable events.
- *Recommendation:* Pull, don't relay: read the latest human input from the transcript named by `CLAUDE_CODE_SESSION_ID`, refuse in child sessions, verify synchronously; drop pending; state the threat model.
- *Disposition:* **Accept.** Adopted in full for `ns decide`, the only remaining agent path, together with ai-safety-privacy-1's card nonce and display proof. `auth` is removed; only verified events reach `person.jsonl`. The threat-model sentence is restored.
- *DESIGN.md:* §3.4, §4.2, §8.4, §8.5.

**engineering-5 · major · Chat-mode Sessions are impractical; maintainer isolation does not exist as described**
- *Problem:* 40–60 model round trips per Session inside a 20-minute cap; unspecified runner state; ask-user answers come back as tool results; subagents inherit parent permissions; the allowlist forbade writing output.
- *Recommendation:* Terminal-only Sessions in v0; agent mode only for `ns decide` and prep; `ns work submit` reads stdin; a restricted subagent definition, spiked; setup prints allowlist lines.
- *Disposition:* **Accept.** Sessions are terminal-only (chat mode is rung R17). The maintainer becomes a `tools: Read` custom subagent whose final message is piped to `ns work submit <id> -`, spiked before v0.5 relies on it. `ns setup` prints rules for Jack to add; it never writes settings.
- *DESIGN.md:* §6.5, §7.3, §8.5, §9.2, §14 R17.

**engineering-6 · major · Adapter paths, record types and Codex rules are wrong**
- *Problem:* Subagent files live under `subagents/workflows/<wf>/`; attachment records (including human `queued_command`) were unhandled; system-reminder blocks would mislabel Jack's whole turn; interruption lines fell to heuristics; Codex wrappers and subagent forks would wreck `self` precision.
- *Recommendation:* Recursive discovery and path-segment tagging; per-block classification; parse queued commands as self; tags denied by default; Codex fork rules; add self recall to the audit; fixtures from these shapes.
- *Disposition:* **Accept.** Verified on disk and adopted as written. Codex rules are specified now and implemented with the v0.5 parser; Codex bytes are copied raw from B1.
- *DESIGN.md:* §6.2, §6.3, §12.1 (B1 acceptance).

**engineering-7 · major · Excision verification is vacuous; pattern antibodies contradict themselves**
- *Problem:* Grep cannot see into compressed blobs; a hashed pattern cannot match new text; content hashes in tombstones are a dictionary oracle; blob remapping unspecified; iCloud out of reach.
- *Recommendation:* Verify through the decode path; redact at archive-write time; antibodies by rule or message ID; HMAC all hashes; IDs in tombstones; specify remapping; list iCloud.
- *Disposition:* **Accept-modified.** Decode-path verification, redaction at write time, ID-only antibodies and tombstones, and the iCloud limit are adopted. HMAC is not needed: tombstones no longer carry hashes, and excision removes every anchor (quote and hash together) that cites the excised source, so no orphan hash remains. v0 excision is `--source` only (scope-simplicity-13), which deletes whole blobs, so blob remapping arrives with `--pattern` in v1.
- *DESIGN.md:* §4.3 (`excise`), §5.5, §6.6.

**engineering-8 · major · Archiving on every command turns reads into writers**
- *Problem:* Parallel agents calling `ns context` would each scan and write the archive under one lock; partial final lines and vendor rewrites were unhandled.
- *Recommendation:* Reads never write or lock; archive only on schedule, at Session start and on `ns archive`; separate locks; tolerant readers; archive to the last newline; re-archive on prefix mismatch.
- *Disposition:* **Accept.** Adopted as written; it is simpler than v0.1.
- *DESIGN.md:* §4.1, §6.1, §6.6.

**engineering-9 · major · v0 is about twice its stated size**
- *Problem:* v0 combined C's base, D's card engine, E's capture and A's clocks with a six-arm eval runner in a claimed 3–3.5K lines; M2 alone was infeasible.
- *Recommendation:* Cut now, state the critical path, defer the eval runner, `ns check`, chat Sessions, pattern excision, catch trials, load rules, me/honesty views and the receipts spike.
- *Disposition:* **Accept.** All listed deferrals were made, plus the LLM prep pipeline (scope-simplicity-6). The critical path is stated, and v0 is six build sessions with a written cut order. The receipts spike stays in B2 because it is cheap and P3 depends on it.
- *DESIGN.md:* §11, §12.1, ADR-0015.

**engineering-10 · minor · 4-character IDs do collide under merge**
- *Problem:* 2^20 IDs per kind give ≈61% collision probability at 1,000 records per machine; `seq` collides too.
- *Recommendation:* Drop the claim; the merge renames colliding IDs; `seq` is local.
- *Disposition:* **Accept.** Claim removed; R16's merge renames with an alias. Four characters are kept for readability.
- *DESIGN.md:* §3.6, §14 R16, ADR-0004.

**engineering-11 · minor · Byte-identical index and stable pack hash are brittle**
- *Problem:* SQLite bytes vary by build and batching; the pack header's ledger `seq` changes with any event.
- *Recommendation:* Determinism as a canonical logical dump; byte identity only for views and packs; pack `seq` = max seq of included items.
- *Disposition:* **Accept.**
- *DESIGN.md:* §4.4, §8.2.

### Epistemics

**epistemics-1 · blocker · The worked example writes system-generated content into Jack's records**
- *Problem:* Tension text, type and a confidence drop came from a single `t`; "because" and decision fields differed from what Jack typed; `chosen` and `assumptions` were never asked; the pack contained text no record held; default-yes prompts; every weekday wrong.
- *Recommendation:* Every person-event field traces to a keystroke; tension text typed or a fixed template; no side effects; ask `chosen`; store expectations verbatim plus a parsed date; verbatim pack lines; correct weekdays; a CI provenance assertion.
- *Disposition:* **Accept.** §5.7 and §4.5 were rewritten on real 2026 weekdays. Every prompt is shown; the confidence change is its own prompt; `chosen` has an Enter default of Jack's own new position text; assumptions were removed from decisions; semantic prompts have no default; the pack renders stored text verbatim. CI asserts provenance on every person event.
- *DESIGN.md:* §4.5, §5.7, §7.2, §8.2, §10.1.

**epistemics-2 · blocker · Revisions drop belief time**
- *Problem:* `position.revise` had no `held_from`, so every change of mind was dated to the Session, contradicting Jack's own earlier notes.
- *Recommendation:* `held_from` on revisions and an end bound on retractions; default to the earliest self evidence on the card, confirmed with one key; auto-fill `prompted_by`; add a fixture.
- *Disposition:* **Accept.** Every new position carries `held_from`; the Session asks "Since when? Enter = no later than <your note>, t = today"; `record.status` carries `held_to`; `prompted_by` is filled from the card. Fixture scenario 2.
- *DESIGN.md:* §3.5, §4.3, §5.6, §5.7, §10.1.

**epistemics-3 · major · As-of ignores its qualifiers; example outputs are wrong**
- *Problem:* `no_later_than` was treated as exact; confidence was shown at dates before it was recorded; history mixed clocks; `valid_to` had no query.
- *Recommendation:* Three-valued as-of with printed bounds; confidence only from its first record; one clock per column; `valid_to` display-only or queryable; fixtures per qualifier.
- *Disposition:* **Accept.** Rules 6–10 in §5.6; `valid_to` is display-only in v0.
- *DESIGN.md:* §5.6, §5.7, §10.1.

**epistemics-4 · major · J6 cannot see where a belief came from**
- *Problem:* "Rests only on AI" was computed from supports links most positions lack; adoption of an AI's suggestion in Jack's words was invisible; C's `basis` was dropped; relayed documents escaped as `doc:`.
- *Recommendation:* Restore `basis` as a P3 field, asked with one multi-select key; store the prep's guess hidden; redefine the flag; lineage by speaker first.
- *Disposition:* **Accept-modified.** `basis` is restored on positions and decisions (per decision rather than per reason, to keep the prompt to one key) and listed in P3. The hidden prep guess waits for v0.5 prep. The flag is redefined and assistant spans are always `ai:<provider>`. R5 stays deferred, as the reviewer advised.
- *DESIGN.md:* §2 (P3), §3.4, §4.3, §5.7.

**epistemics-5 · major · Lexical echo detection is unsound**
- *Problem:* Echo depended on pack exposure windows that positions never enter, and lexical overlap cannot tell echo from agreement.
- *Recommendation:* An order-and-exposure rule: echo if an earlier self turn in the session grounds the record, or a pack or `ns get` containing it was seen.
- *Disposition:* **Accept-modified.** The lexical threshold is gone. The order half of the rule (earlier self turn in the same session is the record's `from_span` or in its `prompted_by`) ships in v0 because it is a few lines; the exposure half needs receipts that moved to R5 (scope-simplicity-10). §3.4 and Appendix B now agree.
- *DESIGN.md:* §3.4, Appendix B (FR14).

**epistemics-6 · major · The change-type vocabulary has holes**
- *Problem:* `?` lost the new view; "unclassified" had no op; `sharpen` was undefined and misused for narrowing; `r` merged two meanings; retractions were missing from the feed while world changes were in it; decision supersession was untyped.
- *Recommendation:* `change ∈ {mind, world, sharpen, unknown}`; `?` records the new view; define sharpen; one follow-up after `r`; retractions as "dropped"; world changes tagged; reuse the enum for decisions.
- *Disposition:* **Accept-modified.** Adopted except for `sharpen`, which is folded into "my view changed" per human-9 (the because-line carries the nuance). `change ∈ {mind, world, unknown}` is shared by positions and decisions.
- *DESIGN.md:* §5.3, §5.6 rule 12, §4.3.

**epistemics-7 · major · Reversals, reinstated retractions and undone corrections cannot be represented**
- *Problem:* A→B→A had no link to the original A; nothing un-retracts; `never_held` had no inverse; derived lines contradicted the current head.
- *Recommendation:* `reinstates`; derived outputs skip reinstated records; allow `never_held: false`; fixtures.
- *Disposition:* **Accept.** `reinstates` on `position.state`, `record.status active`, and a reversible `record.correct`. Fixture scenarios 4, 9 and 10.
- *DESIGN.md:* §3.3, §4.3, §5.6 rules 8 and 11, §10.1.

**epistemics-8 · major · Integrity is automatically "contemporaneous" for Session decisions**
- *Problem:* `decided_at` defaulted to record time with no qualifier, so a hindsight-contaminated expectation typed days later was graded contemporaneous.
- *Recommendation:* `decided_at_q` defaulting to the earliest self span; compute integrity in code; add `endorsed`.
- *Disposition:* **Accept.** Integrity is computed (rule 13) and never stored. The worked example's decision is now honestly `retrospective`.
- *DESIGN.md:* §3.5, §4.3, §4.5, §5.6, §5.7.

**epistemics-9 · major · One question per position; revisions drop grounds and links**
- *Problem:* `question?` was single-valued and revise carried neither questions nor provenance, so the current position's grounds and `ns why` were empty; tensions pointed at stale versions.
- *Recommendation:* `questions[]` inherited on revise; auto-filled `prompted_by`; predecessors' grounds listed separately; lint for stale tensions; `ns get` returns open tensions.
- *Disposition:* **Accept-modified.** Adopted, with the stale-tension lint moved to v0.5 and replaced in v0 by a direct prompt whenever Jack supersedes a record listed in an open tension.
- *DESIGN.md:* §4.3, §5.4, §5.6 (`ns why`), §7.5.

**epistemics-10 · minor · "Scope" means two things**
- *Problem:* The privacy/pack partition shared a name with "the range where a claim is true", inviting an epistemic edit to change privacy routing.
- *Recommendation:* Truth-scope lives only in text; rename the field (for example `realm`).
- *Disposition:* **Accept-modified.** Truth-scope lives only in the claim's text, stated in §3.3. The smaller rename was made instead: the tension type `scope` became `context`, so the word "scope" now means only the partition.
- *DESIGN.md:* §3.3, §4.3, ADR-0008.

**epistemics-11 · minor · The lowest confidence band is broken; test-retest detects nothing**
- *Problem:* "Hunch <60%" included disbelief; probability labels on normative positions; confidence changes had optional reasons; n=10 test-retest is noise.
- *Recommendation:* Hunch = 50–60%; below 50% offers retract or question; label "how sure"; reuse relate's why; κ on ≥20 or drop the test.
- *Disposition:* **Accept-modified.** All adopted, and the test-retest is dropped rather than enlarged (evaluation-14).
- *DESIGN.md:* §3.4, §4.3, §14.

**epistemics-12 · minor · Partial agreement and Jack's own observations cannot be grounds**
- *Problem:* Encounters were defined as someone else's claim; Jack's own observation was filed as Codex's; relate linked the whole quote.
- *Recommendation:* Let Jack trim the quote; encounters from any speaker with `self:experience`; offer self observations first.
- *Disposition:* **Accept-modified.** Encounters now come from any speaker, and self spans rank first; the worked example's decisive evidence is now Jack's own observation. Quote trimming is declined for v0: typing an exact substring at a terminal prompt is error-prone, and `refines` plus the why-line carries partial agreement.
- *DESIGN.md:* §3.2, §5.7, §6.5.

**epistemics-13 · minor · Positions never go stale**
- *Problem:* An unrevisited position counts as held forever in as-of, pages and `ns get`.
- *Recommendation:* Derive `last_confirmed`; show "presumed" after N months.
- *Disposition:* **Accept.** `last_confirmed` is derived (rule 5) and shown on `now.md`, `ns show` and `ns get`; it also tightens as-of bounds.
- *DESIGN.md:* §3.5, §5.6, §7.5.

### Human experience

**human-1 · blocker · The evaluation plan needs many hours of Jack's work that no budget counts**
- *Problem:* About 15 measurement jobs, 720 answers to blind-grade per E3 run, and only the signature test counted; either the 30-minute stop line fires on evaluation or NFR2 misstates the cost.
- *Recommendation:* A separate evaluation budget (≤2 h); grade once; Jack grades few arms and one repeat; 20 probes; one rubber-stamping instrument; derive build minutes; move the rest to the ladder.
- *Disposition:* **Accept.** Evaluation has its own itemized ≤2 h budget, timed by `ns eval` and kept off the stop line. An LLM judge grades; Jack spot-checks 20 items for E3 and 10% for E10. The week-4 audit is the one rubber-stamping instrument. Build minutes come from archived episodes. E9, test-retest, source attribution, the surprise log and golden-set labelling are cut or moved to v0.5.
- *DESIGN.md:* §7.1, §10.3, §10.7.

**human-2 · blocker · Time to first value is about 2.5 hours plus two weeks**
- *Problem:* The week-1 pack arrived around day 14; E8 sat behind the v1 gate; onboarding asked 2.5 hours of homework.
- *Recommendation:* Day 0 ≤20 min; archive, TTY `ns decide` and the pack in build days 1–2 so Claude Code sees 3–5 real decisions that day; the Session runner after; E8 exempt from the gate as a hand-run report in weeks 1–2.
- *Disposition:* **Accept.** B1 archives, B2 delivers terminal `ns decide` and the pack with Jack's first decisions; E8 is hand-run in weeks 1–2 and exempt from the build gate. Onboarding before the first payoff is under 45 minutes.
- *DESIGN.md:* §0, §6.7, §7.1, §7.7, §12.1.

**human-3 · major · Week-0 homework assumes a history the archive doesn't have**
- *Problem:* Week-0 probes need archive gold that two days of logs cannot supply; twelve questions spanning work and life would only ever get recall cards.
- *Recommendation:* Drop week-0 probes, write them at week 3; start with 3–5 questions from active work.
- *Disposition:* **Accept.** Stems are written in week 3; Jack starts with 3–5 questions or aims; questions grow from capture cards.
- *DESIGN.md:* §7.1, §10.2, §15.1 (Q7).

**human-4 · major · G0 tests a novelty Session on an unrepresentative corpus and passes on stated willingness**
- *Problem:* One Session on Northstar material at peak motivation, passed by "willing to repeat".
- *Recommendation:* Don't hold M0 for G0; two hand-built Sessions in weeks 0 and 1 on non-Northstar material; gate only the Session runner on behaviour (both held at the slot, each ≤25 min).
- *Disposition:* **Accept.**
- *DESIGN.md:* §0, §12.1 (G0), §12.2.

**human-5 · major · Nothing cues the weekly slot**
- *Problem:* The habit has a slot in config and no reminder, though the research names the external trigger as what closes the loop.
- *Recommendation:* An `.ics` from setup; prep an hour before the slot; one macOS notification; no follow-up after a miss.
- *Disposition:* **Accept.**
- *DESIGN.md:* §7.3, §4.1 (`session.ics`), §12.1 (B4).

**human-6 · major · Claude Code chat as the default venue breaks the card UX and eats the 20 minutes**
- *Problem:* Enter defaults impossible, single keys become chat turns, model latency per prompt, prep at Session start, faithful re-typing of cards required.
- *Recommendation:* Terminal panel by default; chat Sessions a rung; prep before the slot; finish the current card at the cap.
- *Disposition:* **Accept.**
- *DESIGN.md:* §7.2 (timer), §7.3, §14 R17.

**human-7 · major · Holding events at `auth: pending` causes limbo and repeat work**
- *Problem:* Verification waited for the next archive run; "pending" showed on Jack's pages; voids came back as due cards.
- *Recommendation:* Verify synchronously; normalise inside `ns`; never show "pending"; voids to `ns doctor`.
- *Disposition:* **Accept.** With terminal Sessions only `ns decide` needs verification, which is synchronous; failed captures never reach the ledger and are counted in `ns doctor`.
- *DESIGN.md:* §3.4, §8.4.

**human-8 · major · Overloaded one-letter keys and no undo make mis-keys permanent**
- *Problem:* The same letter meant different things on adjacent prompts; no undo; `correct` could not fix change type, a relation or a verdict.
- *Recommendation:* Digits with analogous choices in the same positions; a per-card buffer with undo; `change` correctable; `relate.retract`; listable and reversible antibodies.
- *Disposition:* **Accept-modified.** Digits, undo and correctable `change` are adopted. Instead of a new `relate.retract` op, the latest relate for a pair wins, so relating with `nothing` withdraws a link; instead of an `unreject` op, the latest candidate verdict wins and `ns rejected` lists them.
- *DESIGN.md:* §3.3, §4.3, §7.2, §7.6.

**human-9 · major · The six-way change question asks for a distinction the example can't apply**
- *Problem:* Mind vs sharpen is not reliably separable, P3 makes the answer permanent, and the worked example contradicted itself.
- *Recommendation:* Three options plus `?`: my view changed, the world changed, the record was wrong; rewording through the recall card.
- *Disposition:* **Accept-modified.** Adopted, with epistemics-6's refinement that "not sure" still records the new view.
- *DESIGN.md:* §5.3, §10.8.

**human-10 · major · Kill criteria fire on noise and on ordinary absences**
- *Problem:* Catch misses at n≤4, a signature test at n=3 with a planted error, and "2 weeks unused" killing the project while the design promises no guilt.
- *Recommendation:* `ns pause`; minimum sample sizes; split the signature score.
- *Disposition:* **Accept.** `ns pause` excludes weeks from every clock; catch trials and the signature test are cut; the three triggers never rest on 3 or 4 events.
- *DESIGN.md:* §7.1, §10.7.

**human-11 · major · Jack's own reading surfaces open with a list of Jack's lapses**
- *Problem:* Six overlapping rubber-stamping instruments surfaced on `now.md`'s WATCH line and `honesty.md`; the tool would feel like an examiner.
- *Recommendation:* Keep measurements in `machine.jsonl` and `ns metrics`; remove the WATCH line; `ns metrics --honesty` on request; one instrument; no catch trials; no "say it yourself" prioritisation.
- *Disposition:* **Accept.**
- *DESIGN.md:* §7.5, §7.7, §10.7, §13 risk 14.

**human-12 · major · Seven generated views, with no place or moment where Jack reads them**
- *Recommendation:* One file, `now.md`, plus `ns show <id>`; a 5-line "what changed" at the end of every Session; drop the other files.
- *Disposition:* **Accept.**
- *DESIGN.md:* §4.1, §7.2 (close), §7.5.

**human-13 · major · "Classify the 11 directories once" doesn't fit the desktop app**
- *Problem:* New scratch folders appear per chat; the Northstar cap misses Northstar work done from scratch chats.
- *Recommendation:* One day-0 answer for the scratch root; lazy classification by a due card; tag Northstar episodes by tool-call paths.
- *Disposition:* **Accept-modified.** Merged with engineering-1: one setup answer for scratch chats (personal, or sorted per chat on a due card), unmatched folders default to `unsorted` (archived, no model, no pack), and Northstar is tagged by cwd or tool-call paths.
- *DESIGN.md:* §4.6, §6.4, §6.6.

**human-14 · minor · In-flow `ns decide` has no daily cap, and G1 demands a decision**
- *Recommendation:* Cap offers at 1 a day and 3 a week, as one non-blocking line; setup prints allow rules; G1 counts a decision by any route; count use only on non-build days.
- *Disposition:* **Accept.** The use-on-non-build-days point is moot: the criterion it applied to ("find or context used on 5 days") was dropped.
- *DESIGN.md:* §4.6 (`[capture]`), §8.4, §8.5, §12.1 (G1).

### AI safety and privacy

**ai-safety-privacy-1 · blocker · Transcript verification checks that the text appears, not that Jack wrote it for this card**
- *Problem:* Single keys match any turn; answers were not tied to cards; agent-worded `chosen`/`rejected` text reached the pack as verified; "newest file" was ambiguous; queued messages and ask-user answers were missed.
- *Recommendation:* Agents never relay text; a nonce per card; `ns` reads the transcript by session ID, proves the card was displayed, records the next human entry; no ask-user tools; agent-worded fields kept out of the pack; spike the flush.
- *Disposition:* **Accept-modified.** Adopted for `ns decide`; Session cards no longer pass through agents at all. Every text field of an in-flow decision is a code-cut quote of Jack's own words or Jack's typed reply, so no agent-worded text exists to keep out.
- *DESIGN.md:* §8.4, §10.1 (forgery fixtures).

**ai-safety-privacy-2 · blocker · The global import puts personal decisions into every session, including work**
- *Problem:* `~/.claude/CLAUDE.md` loads everywhere and is framed by Claude Code as instructions to follow exactly; the JIT CLI had no default scope.
- *Recommendation:* Import packs only in personal project folders; JIT scope from cwd; reword the header to defer to Jack's instructions; acknowledge the instruction channel in P11.
- *Disposition:* **Accept-modified.** Imports go in parent-folder `CLAUDE.md` files (`~/Personal/`, and the scratch-workspaces folder if those chats are personal), which reach exactly those sessions; a user-level import only if Jack confirms no client work happens in Claude Code here. This resolves the conflict with scope-simplicity-9. JIT reads default to the folder's scope; the header defers to Jack's own instructions; P11 is amended.
- *DESIGN.md:* §2 (P11), §8.1, §8.2, §15.2 (Q6).

**ai-safety-privacy-3 · blocker · "No new exposure" is enforced only at prep dispatch**
- *Problem:* Packs, Session relays, prep inputs, `ns context`, the cross-family judge and the G0 wizard all send text to providers that never saw it; "provider" is too coarse.
- *Recommendation:* Two rules at one choke point: archive text only to its origin account; Jack's records per a per-scope policy; drop the cross-family judge; G0 from Jack's own personal turns; ask whether accounts are employer-provisioned.
- *Disposition:* **Accept-modified.** Adopted as ADR-0016 and P13. G0 may use export material, but only through an agent of the same origin, which satisfies the rule while keeping problem-fit-8's requirement. The employer-account question is part of gating Q6.
- *DESIGN.md:* §2 (P13), §6.5, §9.2, §12.1 (G0), §15.2.

**ai-safety-privacy-4 · blocker · Redact secrets and stub tool output at ingest; don't raise `cleanupPeriodDays` permanently**
- *Problem:* The archive kept secrets and tool payloads (file contents, command output, possible client data) that no stage uses; the global retention setting kept every vendor copy, work included.
- *Recommendation:* Structure-preserving redaction and stubs at archive time; prefix sha in the manifest; default retention or a temporary raise; a deny rule for `Read(~/northstar/archive/**)`.
- *Disposition:* **Accept-modified.** Adopted; the retention change is an optional, temporary 60-day insurance with a `ns doctor` reminder to revert (resolving the conflict with the human keep list).
- *DESIGN.md:* §2 (P1), §6.6, §8.5, §12.1 (day 0).

**ai-safety-privacy-5 · major · Maintainer isolation does not work as described, and untrusted text reaches agents by other routes**
- *Recommendation:* A `tools: Read` custom subagent whose output is piped to `ns work submit`; speaker gate on digests; imperative filter on all free text; extend the red-team; Codex episodes cue-floor only.
- *Disposition:* **Accept-modified.** All adopted for v0.5, where agent prep now lives; v0 has no model step, and Session cards never pass through an agent. The red-team covers consent forgeries on the in-flow path.
- *DESIGN.md:* §6.5, §8.5, §9.2.

**ai-safety-privacy-6 · major · `auth: tty` and the single-writer convention do not establish that Jack acted**
- *Recommendation:* State the threat model; refuse person-writes under agent environment variables even with a pty; print deny rules; a weekly keep-or-void card for records made outside the Session.
- *Disposition:* **Accept.** A B2 spike checks which variables separate the agent's shell from the desktop terminal panel, so the guard cannot block Jack.
- *DESIGN.md:* §8.5, §7.2 (due cards).

**ai-safety-privacy-7 · major · Default agent-mode Sessions send private and work records to Anthropic, and Session chats are mined**
- *Recommendation:* Hold cards whose scope forbids the agent's provider; detect Session and maintainer transcripts by content.
- *Disposition:* **Accept-modified.** Resolved structurally: Sessions run in a terminal, so nothing is sent and nothing is mined. The hold-private-cards rule is written into R17 for any future chat mode; content-based maintainer detection arrives with v0.5. Spans already cited by a recorded decision are excluded from capture candidates.
- *DESIGN.md:* §6.5, §7.3, §14 R17.

**ai-safety-privacy-8 · major · Work rules are mis-ordered, "metadata" is undefined, and Q6 is unanswerable as a yes or no**
- *Recommendation:* Most restrictive rule wins; no recursive personal globs; define metadata minimally; work defaults to `ignore`; Q6 stops being a build gate and becomes a per-client opt-in.
- *Disposition:* **Accept-modified.** Most-restrictive-wins, work-as-ignore and the per-client opt-in are adopted; the metadata mode was removed, so it needs no definition. Personal roots stay, because they are Jack's explicit choice at setup and every stricter rule (ignore remotes, paths and client terms) overrides them. Q6 remains a gate but now asks three factual questions answerable in a minute.
- *DESIGN.md:* §4.6, §6.6, §15.2 (Q6).

**ai-safety-privacy-9 · major · Exports have no scope rule and are priced on the wrong provider**
- *Recommendation:* Import only `conversations.json`, never the ZIP; Jack picks a scope at import; ignore terms; ChatGPT only via OpenAI or the cue floor.
- *Disposition:* **Accept.**
- *DESIGN.md:* §6.2, §6.7, §9.5.

**ai-safety-privacy-10 · major · Excision leaves known copies, and the zero-hit grep can pass falsely**
- *Recommendation:* Include `eval/`, `wizard/` and `notes/`; a Python walk that follows symlinks; report-only scans of vendor stores with commands; state the iCloud limit.
- *Disposition:* **Accept-modified.** Adopted for v0's source excision. The notes folder is deferred until Jack asks for phone capture, so the iCloud case arises only then and is stated in Q8 and the README.
- *DESIGN.md:* §5.5, §15.2 (Q8).

**ai-safety-privacy-11 · major · Codex memories are left out, and vendor memory can outlive retractions**
- *Recommendation:* `ns doctor` scans vendor memory stores for IDs and stale text; archive Codex memories; hold settings constant during tests.
- *Disposition:* **Accept-modified.** Scheduled for v0.5 with the Codex parser; in v0 the pack has existed for days, not months. Settings are held constant during E10.
- *DESIGN.md:* §6.2, §8.5.

**ai-safety-privacy-12 · major · The sycophancy defence depends on agents not fetching positions, which is never tested**
- *Recommendation:* Narrow the fetch rule; drop the position count from the index; an E10 arm with the skill; a pre-registered 10-point rule for the default pack.
- *Disposition:* **Accept.** Balanced against problem-fit-10 as described there.
- *DESIGN.md:* §8.2, §8.5, §10.6.

**ai-safety-privacy-13 · major · Codex has no AGENTS.md import, and its sandbox blocks writes**
- *Recommendation:* Cut Codex pack delivery from v0; make reads pure; spike user- and project-level imports and a behavioural smoke test.
- *Disposition:* **Accept.** Codex delivery is rung R18; reads are pure (engineering-8); the import spikes and a per-decision smoke test are in B2.
- *DESIGN.md:* §8.1, §10.6, §12.1 (B2), §14 R18.

**ai-safety-privacy-14 · minor · A day-level cold-pack arm does not match how sessions run**
- *Recommendation:* Analyse by session-start sha, or replace with scripted per-decision probes and drop the trial.
- *Disposition:* **Accept.** The live trial is dropped; scripted E10 and the per-decision smoke test replace it.
- *DESIGN.md:* §10.6.

### Evaluation

**evaluation-1 · blocker · The G3 rule cannot detect plausible effects**
- *Problem:* With about 28 decision probes the minimal detectable effect is about 17 points; the collapse branch used a point estimate; the resampling unit was unspecified.
- *Recommendation:* About 100 auto-generated probes, cluster bootstrap by record, one run per arm, one statistic for both branches, the MDE in the protocol, and P3 fields never removable.
- *Disposition:* **Accept.**
- *DESIGN.md:* §10.4.

**evaluation-2 · blocker · Gold from archive spans is impossible for current-position and forward probes, and circular where possible**
- *Recommendation:* Pre-register gold per category: export spans for past state; recorded events for current and forward probes, used only where both arms share the information.
- *Disposition:* **Accept.**
- *DESIGN.md:* §10.2.

**evaluation-3 · blocker · Jack's evaluation time is understated about 10×**
- *Recommendation:* A logged evaluation bucket capped at ≤3 h; LLM judge primary; one repeat; no week-3 reading; E1 only from real card verdicts.
- *Disposition:* **Accept-modified.** Adopted with the tighter ≤2 h cap from human-1.
- *DESIGN.md:* §7.1, §10.3, §10.7.

**evaluation-4 · major · The arms see different information**
- *Recommendation:* B5 = the same ledger rendered as an untyped journal with the same search; B2 and B4 out of the decision rule; P3 fields protected.
- *Disposition:* **Accept.**
- *DESIGN.md:* §10.3, §10.4.

**evaluation-5 · major · Budgets cannot be matched, and full context contradicts corpus size**
- *Recommendation:* Budget = total tokens in context including tool results; drop B0 or run it once; A0 and B3 only as probe filters.
- *Disposition:* **Accept.** B3 is dropped rather than used as a filter, because it needs Jack to hand-pick spans.
- *DESIGN.md:* §10.3.

**evaluation-6 · major · The cross-family judge is unavailable and would break P13**
- *Recommendation:* Same-provider judge on a different model with a ≥30-item meta-evaluation; pre-registered adjudication; drop the NFR3 swap check.
- *Disposition:* **Accept.**
- *DESIGN.md:* §9.4, §10.3, Appendix B (NFR3).

**evaluation-7 · major · Most safeguards against designer = user = rater are nominal**
- *Recommendation:* LLM judge primary; log real information needs as probe candidates; commit the protocol to git before data.
- *Disposition:* **Accept.**
- *DESIGN.md:* §10.2, §10.3.

**evaluation-8 · major · Kill criteria rest on tiny samples and an invalid catch trial**
- *Recommendation:* Three triggers (disuse, load, builder's trap) with one definition each; remove catch trials; track false endorsement continuously instead of a one-off audit.
- *Disposition:* **Accept-modified.** Triggers adopted and catch trials removed. The week-4 audit is kept (human-1 and human-11 asked for exactly one rubber-stamping instrument, and it is the only direct check of recorded entries), but it produces incidents to fix, not a pass/fail percentage, so its small sample cannot kill anything.
- *DESIGN.md:* §10.5 (E2), §10.7.

**evaluation-9 · major · The signature-test kill criterion contradicts itself**
- *Disposition:* **Accept.** The signature test, its drafts and its build are cut; recall cards measure whether the record matches Jack.
- *DESIGN.md:* §7.1, §10.7.

**evaluation-10 · major · E9 lets an underpowered null result remove the own-words guard**
- *Disposition:* **Accept.** E9 is cut; own words is the fixed default; drafts appear only on Jack's request, from v0.5.
- *DESIGN.md:* §7.7, §10.5.

**evaluation-11 · major · The live pack trial lacks power and has an unmeasurable baseline**
- *Recommendation:* Scripted E10 as the only AI-side decision test, analysed with McNemar; drop the live trial and its week-0 baseline.
- *Disposition:* **Accept.**
- *DESIGN.md:* §10.6.

**evaluation-12 · minor · G0 tests a Session unlike later ones, and passes on intention**
- *Disposition:* **Accept.** Merged with human-4 and problem-fit-8: export material, behaviour-based gate, "would repeat" recorded only.
- *DESIGN.md:* §12.1 (G0).

**evaluation-13 · minor · The speaker audit cannot establish 98% precision**
- *Recommendation:* Exhaustive orchestrated tagging in code; a ~60-turn smoke set; `not mine` and `misquoted` verdicts as the running metric.
- *Disposition:* **Accept.** Combined with engineering-6's recall target.
- *DESIGN.md:* §6.3.

**evaluation-14 · major · About 20 measurements need Jack's time; most decide nothing**
- *Recommendation:* A lean plan: automatic checks, three triggers, two powered tests, E8 and the dead-tool test kept, and a long list of cuts.
- *Disposition:* **Accept.** Adopted as the structure of the new §10.
- *DESIGN.md:* §10.

### Scope and simplicity

**scope-simplicity-1 · blocker · v0 is about twice its 10-session budget and has no cut order**
- *Recommendation:* A five-session v0 with a written cut order; LLM prep, chat Sessions, Codex parsing, exports, the eval runner, `context` and `check` in v0.5; everything else behind triggers; no P3 loss.
- *Disposition:* **Accept-modified.** Six sessions rather than five: the sixth holds the CI suite and source excision, which three other reviewers asked to keep in v0, and B2 is separated out so the pack lands on day 2 (human-2). The cut order and the "never cut" list are in §12.1.
- *DESIGN.md:* §0, §11, §12.1, ADR-0015.

**scope-simplicity-2 · blocker · Scratch-workspace sessions would never be archived**
- *Disposition:* **Accept.** Merged with engineering-1.
- *DESIGN.md:* §4.6, §6.6.

**scope-simplicity-3 · major · The ratchet ratio and the 30-minute kill contradict the plan**
- *Recommendation:* Delete the ratio; keep only the use gate; define the time kill once on Session, capture and supervision minutes; spread evaluation chores.
- *Disposition:* **Accept-modified.** The ratio is replaced by T3 (no building in a week without use, after G1), which keeps the evaluation reviewer's anti-trap intent. The load trigger is defined once, and evaluation minutes are a separate budget.
- *DESIGN.md:* §10.7, §12.1.

**scope-simplicity-4 · major · The ledgers store derivable state and duplicate records**
- *Recommendation:* Derive `auth` and `integrity`; verify lazily; drop `episode.cut`, `verify.author` and `source.archive`; one `wording_by` per field; six machine ops.
- *Disposition:* **Accept-modified.** All adopted, except that verification is synchronous at confirm time (engineering-4) rather than lazy at pack compile. Machine ops are 7 (adding `session.pause`).
- *DESIGN.md:* §3.4, §3.5, §4.2, §4.3.

**scope-simplicity-5 · major · Schema holes invite agents to invent canonical fields**
- *Disposition:* **Accept.** Every Session keystroke becomes a person event; close answers are notes; `nothing` is a relation value; restates no longer need an unclassified state; `endorsed` is `frozen: null`; `me.md` actions are gone; `ns state` and `ns revise` exist.
- *DESIGN.md:* §4.3, §7.4, §7.6.

**scope-simplicity-6 · major · The LLM prep pipeline is built before there is data for it**
- *Recommendation:* v0 prep = the zero-LLM floor plus an agent-written agenda file that must pass the quote and speaker gates; the rest to v0.5 after a subagent spike.
- *Disposition:* **Accept-modified.** Taken one step further: v0 uses only the deterministic floor, and the agent-written agenda waits for the v0.5 spike of a `tools: Read` subagent, because its isolation is unverified (engineering-5, ai-safety-privacy-5).
- *DESIGN.md:* §6.5, §9.1.

**scope-simplicity-7 · major · Ranking weights and load rules are tuned before any Session exists**
- *Disposition:* **Accept.** Fixed segment order with simple tie-breaks; the duplicate penalty terms are deleted; weights, load rules and re-entry move to v0.5 behind triggers.
- *DESIGN.md:* §7.2.

**scope-simplicity-8 · major · Catch trials have nothing to catch under the own-words design**
- *Disposition:* **Accept.** Cut from v0, the kill list and R13's criteria.
- *DESIGN.md:* §7.2, §10.7, §14 R13.

**scope-simplicity-9 · major · The user-level pack import defeats closed scopes, and P13 as worded forbids the pack**
- *Recommendation:* One personal pack imported at user level, stated plainly; personal or private records; no parent, global or provider-filtered scopes; Codex later; reword P13.
- *Disposition:* **Accept-modified.** One personal pack, two record scopes for packing (personal packed, private never), no parent or global scopes, Codex later, and P13 rewritten. The delivery point follows ai-safety-privacy-2 instead: parent-folder imports by default, user-level only if Jack confirms no client work in Claude Code here.
- *DESIGN.md:* §2 (P13), §8.1, §8.2.

**scope-simplicity-10 · major · Echo and exposure machinery serve a closed channel and miss the unrecoverable fact**
- *Recommendation:* One receipt line per archive run with the pack sha, ledger seq and whether the import line is present; keep `own_pack`; move echo, exposure windows and `ns exposed` to R5.
- *Disposition:* **Accept.**
- *DESIGN.md:* §4.3 (`pack.compile`), §8.5, §14 R5.

**scope-simplicity-11 · major · The six-arm, three-repeat eval runner is premature**
- *Disposition:* **Accept.** v0 delivers only the committed protocol and the stem template; the runner is v1, with two arms.
- *DESIGN.md:* §10.3, §12.1.

**scope-simplicity-12 · major · 13K words and about 900 lines of ADRs restate numbers and have drifted**
- *Recommendation:* A ≤250-line BUILD-v0.md as the only build-agent input; ADRs cite DESIGN sections; v1 material moved out of v0 sections; they/them throughout.
- *Disposition:* **Accept-modified.** The drift items were fixed (one time trigger, consistent phases, one timeline convention of build sessions and weeks). ADRs were revised to cite DESIGN sections instead of restating thresholds. BUILD-v0.md will be extracted from §12 after approval rather than written now, because building has not been approved; the repo `CLAUDE.md` will then point only at it.
- *DESIGN.md:* throughout; §11, §12.

**scope-simplicity-13 · minor · Full excision in v0 can shrink to source excision**
- *Disposition:* **Accept.**
- *DESIGN.md:* §5.5.

**scope-simplicity-14 · minor · The notes adapter, Codex parsing and two-clock as-of have no v0 data**
- *Recommendation:* Copy Codex raw without parsing; notes adapter after Q8; an ~8-scenario fold fixture; both clocks and the rest with backfill.
- *Disposition:* **Accept-modified.** Codex is copied raw and the notes adapter waits. The fixture has 12 scenarios, because engineering-2, epistemics-3 and epistemics-7 showed rules v0 needs at once (revision onset, three-valued as-of, reversal). `--recorded-by` stays in v0 because it is only a filter on `at`.
- *DESIGN.md:* §5.6, §6.2, §10.1.

---

## Changes in v0.2

**Problem framing and scope**
- Positions cover Jack's understanding of how something works; a takeaway capture card brings learning conversations in, recall before reveal (problem-fit-1).
- `form: aim` for goals, exempt from the cap and park prompts, reviewed monthly, listed in the pack (problem-fit-5).
- Notes are revisable and retractable, feed relate cards for 90 days, and capture cards offer "note"; close answers are notes (problem-fit-4).
- A monthly review card consolidates the question set (keep, park, answer, dissolve, alias, nest with `part_of`) and ends with an unaided recall (problem-fit-7).
- §1.2 states in and out of scope per brief item, and the bounded-integration trade; Q0 asks Jack whether this is the system they asked for (problem-fit-7, -9).
- Disk facts corrected and the corpus called unrepresentative (problem-fit-8, engineering-1).
- They/them for Jack everywhere, including the pack header (problem-fit-12).

**Data model and semantics**
- `supersede` op between existing records; `held_from` on every new position; `record.correct`, `record.status`, `record.rescope` replace position-only ops; `reinstates`; `questions[]`; `basis`; `would_change_if`; `decided_at_q`; `close` notes; `part_of` and `nothing` relation values; tension type `context` (engineering-2, -3; epistemics-2, -4, -6, -7, -8, -9, -10).
- 13 normative fold rules: heads, held intervals, `last_confirmed`, three-valued as-of, corrections on both clocks, confidence dating, partial dates, reinstatement, the change feed, computed integrity (engineering-2; epistemics-3, -13).
- Change question reduced to my view changed / the world changed / the record was wrong / not sure, with "not sure" still recording the view (human-9, epistemics-6).
- `auth`, stored `integrity`, `episode.cut`, `verify.author`, `source.archive` and `pack.expose` removed; machine ops 13 → 7 (scope-simplicity-4, -10).
- Hunch is 50–60%; confidence shown as "how sure" (epistemics-11). Echo by order only (epistemics-5).
- Worked example rewritten on real weekdays, every field tracing to a keystroke, plus a learning example (epistemics-1).

**Ingestion and privacy**
- Retention decoupled from scope; scratch chats archived; work ignored entirely; scopes ignore / private / unsorted / personal, most restrictive wins; ignore terms (engineering-1, scope-simplicity-2, ai-safety-privacy-8).
- Secrets redacted and tool payloads stubbed at archive time; structure kept; `cleanupPeriodDays` only temporarily raised (ai-safety-privacy-4).
- Adapters fixed to the real log shapes: recursive discovery, per-block classification, queued messages, tags denied by default, Codex fork rules (engineering-6).
- Reads never write; separate locks; partial-line-tolerant readers (engineering-8).
- Egress by origin account plus per-scope policy at one choke point, ADR-0016 (ai-safety-privacy-3).
- Exports: `conversations.json` only, scope chosen at import, ChatGPT only via OpenAI (ai-safety-privacy-9).

**Human and AI surfaces**
- Sessions in a terminal; chat mode is R17 (engineering-5, human-6). Numbered options, no preselected semantic answers, a per-card undo buffer (human-8). A calendar file and a notification after prep runs before the slot (human-5). `ns pause` (human-10).
- One generated page (`now.md`) plus `ns show`; no lapse lists or audit numbers on Jack's page; measurements on request (human-11, -12).
- In-flow `ns decide` by transcript pull with a nonce and display proof, quotes-only fields, synchronous verification, capped offers (engineering-4, ai-safety-privacy-1, human-7, -14).
- Pack imported through parent-folder `CLAUDE.md`, not globally; verbatim lines; deferring header; title index; a fetch rule; `seq` of included items; Codex delivery deferred (ai-safety-privacy-2, -12, -13; problem-fit-10; engineering-11).
- Write guard against agent shells, printed deny rules, a weekly keep-or-void card for in-flow decisions, an explicit threat model (ai-safety-privacy-6).

**Evaluation and build**
- §10 rewritten: write-path CI with a provenance assertion and a 12-scenario fold fixture; E3 as NS against the same ledger rendered as a journal on ~100 generated probes; scripted E10; three pause-aware triggers; coverage signal; ≤2 h of Jack's time; same-provider judge (evaluation-1 to -14; human-1).
- Cut: the signature test, catch trials, E9, the live pack trial and week-0 baseline, B0/B3/B4 as decision arms, three repeats, the cross-family judge, NFR3, test-retest, source-attribution checks, monthly samples.
- v0 is six build sessions with a critical path and cut order; same-day payoff in B2; G0 is two hand-built Sessions on export material that gate only the Session runner; v0.5 items each behind a trigger (engineering-9; scope-simplicity-1, -6, -7, -11, -13, -14; human-2, -3, -4).
- The 3× build ratio replaced by T3; one definition of each trigger (scope-simplicity-3).
- New ADRs: 0015 (v0 cut line, build order and gates) and 0016 (egress control). ADRs 0001–0014 revised in place.

---

## Rejected findings and why

No finding was rejected in full. Every finding pointed at a real defect, and most fixes removed mechanism. These specific recommendations inside accepted findings were declined:

- **A `want_to_know` flag (problem-fit-3).** Positions created by takeaway cards already count learning intent, so the flag would be a second signal for the same thing.
- **Minting an encounter for every takeaway (problem-fit-1).** `basis: ai` plus an auto-filled `prompted_by` gives the same "rests only on AI" result and the same provenance with no extra record.
- **Position-to-position cards in v0 (problem-fit-6).** Deferred to v0.5 with an automatic trigger at ≥20 current positions: there is nothing for a neighbour search to find in the first weeks.
- **Using `would_change_if` as a ranking feature (problem-fit-11).** v0 has no ranking weights.
- **Archiving work raw once Q6 permits (engineering-1, scope-simplicity-2).** Work is ignored by default until a per-client opt-in (ai-safety-privacy-8), because whether client logs may be stored at all is a per-contract question.
- **HMAC on every content hash (engineering-7).** Tombstones carry IDs only and excision removes whole anchors, so no orphan hash remains to protect.
- **A `relate.retract` op and an `unreject` op (human-8).** "Latest relate for a pair wins" and "latest verdict wins" do the same with no new ops.
- **A distinct `sharpen` change type (epistemics-6).** Folded into "my view changed", following human-9 and the evidence of v0.1's own example.
- **Renaming the `scope` field to `realm` (epistemics-10).** Renaming the tension type to `context` removes the collision with a smaller change.
- **Trimming quotes on relate cards (epistemics-12).** Typing an exact substring at a prompt is error-prone; `refines` and the why-line carry partial agreement.
- **No recursive personal globs (ai-safety-privacy-8).** Personal roots are Jack's explicit choice at setup, and every stricter rule overrides them; asking Jack about each new folder is the chore human-13 warned about.
- **Removing Q6 as a gate (ai-safety-privacy-8).** It stays a gate but now asks three quick factual questions (where work happens, whose accounts these are, whether scratch chats are personal), because the pack-delivery and egress defaults depend on them.
- **An agent-written agenda in v0 (scope-simplicity-6).** Deferred until a `tools: Read` subagent's isolation is spiked.
- **A five-session v0 (scope-simplicity-1).** Six sessions, to keep CI and source excision in v0 and deliver the pack on day 2.
- **Deleting the build/use ratio outright (scope-simplicity-3)** and **dropping the week-4 audit (evaluation-8).** Both replaced by lighter forms (T3; an incident-finding audit) that keep what other reviewers' keep lists asked for.
- **Writing BUILD-v0.md now (scope-simplicity-12).** It will be extracted from §12 after approval; writing build instructions before approval would pre-empt Jack's decision.
- **Keeping `cleanupPeriodDays` strictly at its default (ai-safety-privacy-4).** An optional, temporary raise remains as insurance against a slipped build, with a reminder to revert.
