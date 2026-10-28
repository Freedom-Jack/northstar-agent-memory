# Ingestion and Extraction: Turning Raw Streams into Attributed Knowledge Candidates

Track 08. Status: research note, 2026-10-07. Web tools were used, and the web search budget ran out partway through. Claims I could not re-check in this session are marked "(unverified)". Some findings come from inspecting the session-log schemas on this machine (`~/.claude/projects`, `~/.codex`). For those I read only keys, counts and sizes, never the content.

## Scope and questions

This track covers the front of the system: where a person's knowledge comes from in the AI era, and how a raw stream (chat exports, agent session logs, highlights, notes, mail, transcripts, code) becomes *candidate knowledge updates*. Storage, consolidation and retrieval belong to other tracks. Here the output is a proposal ("here is something that may belong in your knowledge, here is who said it, here is how you related to it"), not a committed write.

Questions:

1. What do realistic sources look like as data, and what signal do they carry for free?
2. What should the unit of extraction be (atomic facts, propositions, decisions, episodes)?
3. **The attribution problem.** When an assistant asserts something in a conversation, how do we tell whether the person accepted it, rejected it, was unsure, or never engaged with it? When should we ask?
4. Where should processing happen: at capture time (hot path) or in batch? How much human review is affordable before fatigue makes it worthless?
5. What are the realistic error modes: hallucinated extractions, omissions, misattribution, upstream transcription errors, privacy leaks, injected instructions?

Key question: **what pipeline turns a stream of raw material into candidate knowledge updates with correct attribution and acceptable human review cost?**

## Key findings

**1. In AI-session logs, the person's own words are a small minority of the bytes, and the role labels lie.**
*Mechanism:* agentic tools record tool outputs, harness messages and injected context under the same "user" role as human typing. A role-based extractor therefore credits the person with words they never wrote.
*Evidence (local inspection of this machine, 12 Claude Code sessions, ~8.7M characters):* tool results made up ~79% of characters and sit under `type: "user"` entries as `tool_result` blocks. Assistant tool calls made up ~11%, assistant prose ~3.4%, and user-role text not wrapped in a system tag ~2.5%. That last figure is an overestimate of human typing, because workflow-orchestrator prompts like the one that launched this track also look like plain user text. System-injected `<task-notification>` text alone (~258K chars) was larger than all the plain user text (~221K). In the 3 Codex rollouts present, `role: "user"` messages starting with `<environment_context>` held ~6.6K chars against ~2.7K of plain user text, and `developer`-role injections were larger still.
*Source:* local schema inspection. The Codex rollout line shape is `{timestamp, type, payload, ordinal}`, with types `session_meta`, `response_item`, `event_msg`, `turn_context` and others. This agrees with third-party documentation of the rollout format (Vaughan 2026), though that source says files are `.jsonl.zst`; the files here were plain `.jsonl`.

**2. Human-authored is not human-believed.** The person's own turns contain requests, hypotheticals ("suppose X…"), steelman and devil's-advocate prompts, text drafted on someone else's behalf ("write a reply saying I love the proposal"), pasted third-party material, and role-play.
*Mechanism:* the speech act decides whether a sentence is a sincere assertion. Pasting is especially dangerous. Pasted articles, error logs and colleagues' messages land in user-role text (the Claude Code log here even carries a `<pasted_content>` wrapper, but chat exports usually flatten pastes into plain user text).
*Evidence:* a structural argument, plus the observation above. I found no benchmark that measures this directly; it is a gap.

**3. Explicit endorsement is rare, so stance must be inferred from weak signals.**
*Mechanism:* people use assistants to get tasks done, not to certify beliefs. Moving on to the next request means "good enough for now", not "I now believe this". In human conversation, a relevant next turn counts as weak acceptance (Clark & Brennan's grounding). In human-AI conversation, the person often never read the claim at all.
*Evidence:* WildReward reports that about 82% of follow-up queries in WildChat convey no explicit feedback, and explicit positive feedback is about 1% (arXiv 2602.08829). Liu, Zhang & Choi (arXiv 2507.23158) find that implicit feedback helps you understand users but is a noisy learning signal. WildFeedback and SigX-style taxonomies list the usable implicit signals: rephrasing, correction ("actually I meant…"), abandonment, "no engagement" and "ignored".

**4. Today's production memory systems store assistant-introduced content as user memory about half the time.**
*Mechanism:* extractors are told to extract "facts about the user" from a dialogue. They cannot tell what the user said from what the assistant said while the user stayed silent.
*Evidence:* HaluMem (arXiv 2511.03506, Nov 2025) seeds "distractor memories", which it defines as false but similar memories that the AI uses naturally while the user stays silent. It measures False Memory Resistance (FMR), the share of distractors a system ignores. On HaluMem-Medium, FMR was Mem0 56.8%, Mem0-Graph 55.7%, Supermemory 51.8%, MemOS 44.9% and Memobase 80.8%. Memobase scored highest only because it extracts very little (recall 14.6%). Put plainly, the systems with usable recall absorbed **roughly 43–55% of assistant-introduced distractors**. This is the attribution problem measured in a benchmark, and the commercial systems fail it. (Figures read from the alphaxiv rendering of the paper; check them against the PDF before quoting externally.)

**5. Contrary to the popular fear, the dominant extraction failure is omission, not fabrication.**
*Evidence:* the same HaluMem tables show memory-*update* hallucination rates of only 0.26–1.15%, but update *omission* of 37–94%. Mem0 failed to apply 74% of the updates it should have. Extraction target precision was high (86–92%), but recall on the medium set was below 60% for every system except MemOS (74%). On the long set (~1M tokens), Mem0's recall collapsed from 42.9% to 3.2%.
*Mechanism:* extraction prompts are tuned to be conservative, and the "update vs. new vs. conflict" decision is hard, so it defaults to doing nothing. The consequence is quiet staleness: the store looks clean but drifts away from reality. **Design for missed updates and misattribution first, and for invented facts second.**

**6. Destructive in-place updates are being abandoned by the systems that pioneered them.**
*Evidence:*
- The original Mem0 pipeline (Chhikara et al., arXiv 2504.19413) sent each candidate to ADD, UPDATE, DELETE or NOOP. Mem0's April 2026 algorithm switched to single-pass, **ADD-only** extraction where "the new fact lives alongside the old one, and both survive". The vendor reports LoCoMo 71.4→92.5 and LongMemEval 67.8→94.4. These are vendor-reported and not independently verified.
- OpenAI's June 2026 "Dreaming V3" memory update (Thurrott, 2026-06-05) said the previous saved-memory system "often became stale" and contained contradictions. They replaced it with background curation into an editable memory summary, which also revises time-sensitive items (a planned trip becomes a past trip).
- A June 2026 architecture study (Yang, arXiv 2606.15903) argues that production failures are mostly *forgetting* failures (failing to supersede or delete correctly), while benchmarks measure only recall.

*Implication:* ingestion should emit **append-only candidates with proposed relations** (refines, supersedes, contradicts) and leave the irreversible decisions to a separate consolidation step.

**7. Abstaining under ambiguity is the most transferable idea in claim extraction, and decomposition itself is unstable.**
*Mechanism:* Claimify (Metropolitansky & Larson, ACL 2025, arXiv 2502.10855) runs four stages: sentence splitting, selection, disambiguation, decomposition. It extracts a claim only when it is confident about the correct reading, and it evaluates coverage and decontextualization (whether the claim can be understood without its source). Separately, Wanner et al. (arXiv 2403.11903) show that FActScore results change with the decomposition method, so "atomic facts" are not a well-defined, reproducible unit.
*Implication:* the same paragraph will atomize differently on different runs and models. A store keyed on atomized facts will churn duplicates whenever the extractor changes. Keep stable source spans as anchors, and treat the extracted text as a revisable rendering of those spans.

**8. Propositions improve retrieval, but atomization strips out the reasoning that matters most in personal knowledge.**
*Evidence:* Dense X Retrieval (Chen et al., EMNLP 2024, arXiv 2312.06648) found that indexing propositions instead of passages improved Recall@20 by +10.1 points on average for unsupervised dense retrievers and +2.2 for supervised ones. FActScore (Min et al., arXiv 2305.14251) showed that atomic-fact scoring can estimate an *aggregate* score with under 2% error. That is a statement about the aggregate, not about each fact.
*Mechanism:* atomization helps question answering over encyclopedic text, where every fact stands alone. A person's understanding is relational: "I chose X *because* Y, *despite* Z, *unless* W." Atomic facts drop the connectives that turn a list of facts into reasoning. Decisions, arguments and changes of mind need a richer unit.

**9. Stance is a property of the whole episode, and sometimes of several episodes, so it cannot be judged turn by turn.**
*Mechanism:* the person may push back five turns later, regenerate the answer, abandon the thread, or adopt the idea a week later in code or in their own notes. A hot-path extractor running per turn has to guess before the evidence exists.
*Evidence of convergence:* the shipped systems all moved to deferred batch processing.
- Codex's local memory store (`~/.codex/memories_1.sqlite` here) has a `stage1_outputs` table keyed by `thread_id`, holding `raw_memory`, `rollout_summary`, `source_updated_at`, `usage_count`, `last_usage` and `selected_for_phase2`. Alongside it are a leased `jobs` table with input and success watermarks, and a `consolidation_progress` table. That adds up to per-thread extraction followed by a separate global consolidation phase.
- ChatGPT's 2026 memory "dreams" in the background over chat history.
- Claude's March 2026 memory import says absorbing imported memories takes up to 24 hours (PCWorld, 2026-03-03).

**10. Export formats carry free stance signals that most pipelines throw away.**
- *ChatGPT export:* `conversations.json` is a list of conversations, each with a `mapping` tree of nodes linked by parent and children. Edits and regenerations produce sibling branches. Some nodes are empty placeholders, and timestamps are Unix seconds. The ZIP also contains `message_feedback.json` (thumbs up and down), `user.json`, `model_comparisons.json` and `chat.html` (ai-chat-importer guide). I believe `current_node` marks the active leaf and that `content_type` values include text, code, multimodal and reasoning variants (unverified). **A regenerated or edited-away branch is a cheap rejection signal.** Thumbs-down marks an assistant answer the person disliked.
- *Claude.ai export:* `conversations.json` holds conversations, each with a `chat_messages` array whose `sender` is `human` or `assistant`, plus timestamps. The ZIP also includes `projects.json` and `users.json`, and per one viewer tool, `memories.json`. A reported issue says conversations carry no project link, so project context is lost (claudeissues #40411). Content blocks and attachment fields exist in recent exports (unverified detail).
- *Readwise:* the `GET /api/v2/export/` endpoint supports `updatedAfter` and `pageCursor` for incremental sync. Each highlight carries `text`, `note`, `location`, `highlighted_at`, `tags`, `is_favorite` and `is_discard`. The person's `note` is their own voice. `is_discard` (from Readwise's own review flow) is an explicit rejection.
- *Kindle `My Clippings.txt`* (from knowledge): records are separated by `==========`, with a title/author line and a "Your Highlight … Location … Added on …" line. Editing a highlight appends a new record without removing the old one, so near-duplicate cleanup is required.
- *Code repositories:* commits are the strongest *behavioral* endorsement available. An assistant-proposed change that survives into a commit was adopted. One that was reverted or never committed was not.

**11. Upstream conversion is itself a source of hallucination.** Koenecke et al., "Careless Whisper" (FAccT 2024, arXiv 2402.08021), found that about 1% of Whisper transcriptions contained entire invented phrases, 38% of which were harmful, and that this was more likely with long pauses. Voice memos and meeting transcripts are the person's words *as rendered by a model*. A claim extracted from an ASR transcript inherits that error rate, and nobody notices unless the audio pointer is kept.

**12. Ingestion is an attack surface.** Rehberger's "SpAIware" (Sept 2024) planted persistent instructions in ChatGPT memory through indirect prompt injection from untrusted content, giving exfiltration across sessions. OpenAI patched that vector but acknowledged that injection into memory remains open (The Hacker News). A January 2026 Radware proof of concept ("ZombieAgent") reportedly chained connectors and memory for persistence (secondary report, unverified). Any pipeline that extracts from web pages, mail or AI outputs and later injects the results into an AI's context is a persistence mechanism for whoever wrote the source.

**13. A review queue with low precision teaches people to click "accept".** Clinical decision support is the best-documented case. Drug-safety alerts are overridden 49–96% of the time (van der Sijs et al., JAMIA 2006; recalled, not re-verified in this session). The mechanism carries over directly: once most items in a queue are irrelevant, the reviewer's prior becomes "dismiss" or "approve all", and real problems pass unread. A rubber-stamped knowledge store is worse than an unreviewed one that admits it is unreviewed, because it carries false authority.

## Source landscape (design view)

| Source | Format reality | Share of text that is the person's own | Free stance signals | Main risks |
|---|---|---|---|---|
| ChatGPT export | Tree `mapping`, branches, feedback file | Low–medium; includes pastes | Branches, thumbs, abandonment, follow-up corrections | Misattribution; full re-dump on every export (needs idempotent ingest) |
| Claude.ai export | Linear `chat_messages`, sender field | Low–medium | Corrections, abandonment | No project linkage; misattribution |
| Claude Code / Codex logs | JSONL event streams, tool I/O under "user" | Very low (~2–3% by chars here) | Commits, file diffs kept/reverted, rejected tool approvals | Secrets in tool output; injected text in user role |
| Highlights (Readwise/Kindle) | API JSON / clippings text | Selection is the person's; text is the author's | Highlight = salience, `note` = own voice, discard | Highlighting is not agreeing; duplicates |
| Own notes (markdown) | Files | High | Revisions over time (git history) | Drafts, quotes and to-dos mixed with beliefs |
| Email | mbox / Takeout | Medium (sent) / low (received) | Sent vs. received, replies | Third-party personal data; injection |
| Meetings / voice | ASR transcript + audio | Mixed speakers | Who-said-what (diarization) | ASR hallucination; others' statements; consent |
| Work docs | Docs/PDF | Varies | Authorship, comments | Confidentiality |

## Ideas worth stealing

1. **Speaker × holder × stance on every candidate.** Each candidate records who uttered it (speaker), whose belief it would be (holder), the person's stance toward it, and the evidence span for that stance. This turns HaluMem's distractor failure from a hidden error into a queryable field. *(Synthesis motivated by HaluMem's FMR framing.)*
2. **An "encountered" layer that is separate from "believed".** Everything the assistant told the person is valuable as *testimony with provenance* ("Claude said on 2026-05-03 that X"). It must not be stored as the person's belief. Mem0's 2026 shift to capturing assistant statements as first-class facts is right for *agent task memory* and wrong for a *personal belief model* unless it is labeled. *(Contrast drawn from the Mem0 2026 blog.)*
3. **Abstain under ambiguity.** If a span has several plausible readings, keep the span and flag it rather than emitting a guessed claim. *(Claimify.)*
4. **Decontextualize at extraction time and resolve relative time against the episode timestamp.** "Next July" becomes "July 2026", and "my manager" becomes the named role if it is known. Mark time-sensitive candidates for re-evaluation. *(Claimify decontextualization metric; ChatGPT Dreaming V3's trip example.)*
5. **Two-stage, watermark-driven batch jobs.** Run per-source extraction idempotently, keyed by (source id, `source_updated_at`), then a separate consolidation phase selects which items go forward. Leases and retry counters make it restartable. *(Observed in Codex's `memories_1.sqlite` schema.)* Use **usage counters** (`usage_count`, `last_usage`) as salience feedback.
6. **Treat abandoned branches, regenerations and thumbs-down as negative evidence**, and treat commits, reuse in the person's own later writing, and repeated retrieval as positive evidence. *(ChatGPT export structure; WildFeedback/SigX signal taxonomy.)*
7. **Surprise-based episode boundaries.** EM-LLM (ICLR 2025, arXiv 2407.09450) segments streams at points of high surprise and refines boundaries with graph methods; its segmentation correlated with human-perceived events. A practical version uses embedding change points plus an LLM pass over topic shifts. Segment conversations into topics, and also *join* topics across conversations.
8. **Importance scored at write time but used only at read time.** Generative Agents (Park et al. 2023) rated "poignancy" from 1 to 10 at write time and used it for retrieval and reflection triggers rather than for dropping items. Salience should rank items, not delete them, because the raw log is kept.
9. **A low-friction keep/discard ritual.** Readwise's daily review, with its `is_discard` flag, is a proven daily habit: small, swipe-like decisions that feed back into the data. Model review on this rather than on an inbox.
10. **A single editable summary as the human review surface.** ChatGPT's Memory Summary and Claude's "See what Claude learned about you" both suggest people review *a narrative*, not 400 atomic facts. Review episode digests and profile deltas, and keep the atoms behind them.
11. **Deterministic secret scanning before any LLM sees the text.** Use regex and entropy scanners of the gitleaks or trufflehog style, plus a PII recognizer (Presidio-like). The deterministic layer is auditable and costs almost nothing. *(Tool names from knowledge; the choice of library is open.)*

## Pitfalls and anti-patterns

- **Role-based attribution** ("extract facts from user messages"). This credits the person with tool outputs, harness text and pasted articles (Finding 1). Extracting from the *whole* dialogue instead credits them with what the assistant said (Finding 4).
- **The hot-path "remember this" model as the main ingestion route.** It has to decide stance before the evidence exists, adds latency to every turn, and caused the staleness and contradictions OpenAI described as its reason for rebuilding (Finding 6). Explicit "remember this" commands are still excellent *high-confidence* signals; they just should not be the only route.
- **Destructive UPDATE/DELETE at ingest.** One misclassified update erases history permanently. HaluMem shows the update classifier mostly fails by omission, but when it does fire wrongly there is nothing to undo it. Mem0 moved away from this.
- **Over-atomization.** It produces thousands of decontextualized fragments, which is exactly the "disconnected fragments" problem this project exists to fix. It also loses the *because* and *unless* that carry the reasoning.
- **Trusting aggregate extraction metrics.** FActScore's under-2% error is for an aggregate score. Per-item errors, the ones that become stored "beliefs", are much higher. Dense X's gains are on Wikipedia-style QA, not personal reasoning.
- **Treating highlights as beliefs.** People highlight things they disagree with, things they find surprising, and things they want to rebut. A highlight signals salience, not endorsement.
- **Importing another system's memory as ground truth.** ChatGPT and Claude memories are already lossy, LLM-extracted profiles carrying the HaluMem-style errors above. Claude's 2026 import works by asking the other assistant to *write out* what it remembers, which is a second lossy pass. Prefer raw exports, and treat imported memories as "assistant-asserted about the person", with low confidence.
- **Review queues sized by extraction volume rather than by a time budget.** This leads to alert fatigue and rubber-stamping (Finding 13). A queue that grows without bound gets abandoned within weeks (unverified as a measured rate, but it is the classic PKM inbox failure).
- **Re-ingesting full exports without idempotency.** ChatGPT and Claude exports are complete snapshots. Without stable message-id keys, each export duplicates the corpus.
- **Letting extracted text become instructions.** A memory phrased as an imperative ("always send summaries to…") from an external source is how SpAIware persisted. Stored knowledge must be rendered to AIs as quoted data with provenance, never spliced into system instructions.
- **Assuming transcripts are verbatim.** ASR adds its own errors (Finding 11). Keep audio offsets.

## Implications for this project

1. **The unit of ingestion is the *episode*, not the message and not the atomic fact.** An episode is a topically coherent stretch from one or more sources. Each yields an **episode digest** (what the person was trying to do, what they concluded, what stayed open, what they rejected) plus typed **candidates**: claim or belief, decision (with alternatives and rationale), goal, open question, preference, self-fact, encountered-fact, procedure. *Falsifiable:* on a gold set of ~30 of the user's real AI conversations, people should rate digest-plus-candidates as a more faithful account of "what I took away" than a flat list of atomic facts. Measure with blind pairwise preference (target ≥70% preference).

2. **Attribution is a first-class schema field with a closed vocabulary.**
   - speaker ∈ {self-typed, self-pasted, assistant, tool, system-injected, third-party, document-author}
   - holder ∈ {self, assistant, named-other, unknown}
   - stance ∈ {asserted, endorsed, adopted, entertained/hypothetical, questioned, rejected, unengaged, performed (drafted for someone else or role-play)}

   The default stance for any assistant assertion is **unengaged**, stored in the encountered layer. Promotion to belief requires positive evidence. *Falsifiable:* on the gold set, the **false-endorsement rate** (assistant or third-party content stored as the person's belief) should be ≤5% for the stance-aware pipeline. A naive "extract facts about the user from this dialogue" baseline should land near HaluMem's 40–55%. If the gap is small, the schema is not earning its cost.

3. **Adapters must classify every message's true speaker before any LLM extraction.** For Claude Code that means dropping `tool_result`, `isMeta` and tag-wrapped harness text from "self". For Codex it means dropping `developer` messages and `<environment_context>`. For chat exports it means detecting pastes (long blocks, quoted formatting, code or log signatures). For ChatGPT it means following the active path and recording abandoned branches as negative evidence. *Falsifiable:* after adapter filtering, the "self-typed" share of characters in agent logs should come out under 10%. If it comes out much higher, the classifier is letting injected text through.

4. **Run extraction in batch, after the episode closes, with a re-evaluation window** (proposal: 7–14 days) in which later evidence can change stance: commits, reuse in the person's own notes, reversals in later chats. Hot-path capture is limited to (a) explicit "remember this" commands and (b) zero-friction raw logging. *Falsifiable:* compared with per-turn extraction on the same gold set, episode-level batch extraction should cut stance errors by at least half.

5. **Ingestion never mutates or deletes knowledge. It emits proposals.** Each candidate carries proposed relations to existing items (duplicate-of, refines, supersedes, contradicts, supports), found by embedding neighbors and an LLM judge. The consolidation track decides what to apply. Raw sources are kept immutable and content-addressed, so the knowledge layer can be rebuilt with a better extractor later. This is the only good answer to Finding 7's instability.

6. **Human review runs on a fixed time budget and is ranked by value of information,** roughly impact × uncertainty. That puts conflicts with existing beliefs, decisions, self-model claims, anything about other people, and low-confidence stance on high-salience items at the top. Review happens at the episode-card level ("Is this what you concluded? yes / partly / no / skip"), and skip means no change. Unreviewed items stay usable with an "unreviewed" label. *Targets:* ≤15 minutes a week. An acceptance rate between ~60% and ~90%: above 95% means the queue is not adding information or the reviewer is rubber-stamping, below 50% means extraction precision is too low. Track queue abandonment as the primary failure metric.

7. **Ask the person in the moment only when an answer is cheap and decisive.** One proposed experiment is an optional end-of-session prompt, "Did you settle on X? (yes / no / still open)", shown at most once per session and only for decisions. Compare stance accuracy and annoyance against batch-only review.

8. **Privacy filtering is a deterministic stage before any model call.** It redacts secrets (keys, tokens, connection strings), flags third-party personal information, and keeps a sensitivity tag on each candidate that controls whether it can ever be exported into an AI's context. Agent logs need this most, because tool outputs routinely contain environment variables and config. *Falsifiable:* seeded synthetic secrets in a test corpus must give 0 leaks into candidates.

9. **Content from external sources is quarantined from instruction space.** Candidates from web pages, mail, documents or assistant outputs that are phrased as imperatives aimed at an AI are tagged and never surfaced to AI systems as directives, only as quoted, attributed data.

10. **Start with the two sources this user already produces in bulk: AI chat exports and agent session logs plus git.** They are where the attribution problem is hardest and the stance signals (branches, commits) are richest. Add highlights and notes second, because those are mostly self-authored and easier. Leave meetings, voice and email for last: third-party and ASR risks with little extra signal for a first prototype.

11. **Cost is not the blocker.** Back of the envelope, not a citation: 3,000 conversations at ~5K tokens each is ~15M input tokens per full extraction pass, which is tens of dollars at mid-tier model prices. Reprocessing the entire archive when the extractor improves is affordable, which makes Implication 5 (rebuildable derived layers) practical.

## Tensions and open questions

- **Eager or lazy extraction?** The shipped systems are converging on raw history plus background synthesis plus query-time retrieval (ChatGPT's reference-chat-history and dreaming, Mem0's ADD-only). That raises the question of whether eager candidate extraction is worth building at all, or whether digests plus raw spans with extraction at query time are enough. Run this as a head-to-head test on personal questions ("What did I decide about X and why?") before committing to an eager pipeline.
- **How long should stance stay open?** Adoption can happen months later. A long window gives better stance but slower knowledge. Should stance ever be "final"?
- **Encountered vs. believed is a spectrum.** Repeated exposure without objection can turn into tacit belief. Should repeated unengaged exposure eventually prompt a question ("You've been told X four times. Do you hold this?")?
- **Review decisions are themselves unreliable.** People endorse in hindsight, misremember their reasoning, and accept fluent summaries. Is a later review better evidence than the original behavior? Behavioral signals may deserve more weight than review clicks.
- **How to segment across sources.** One idea runs through a chat, a commit and a note. Is the episode a time window, a topic, or a project? This probably needs hierarchical episodes. That overlaps with the structure track.
- **Third-party information.** A colleague's stated opinion in a meeting is valuable to the person but is personal data about someone else. What is the policy for storing it, and especially for exporting it to an AI?
- **Assistant claims that turn out to be wrong.** The encountered layer could support later fact-checking ("three things Claude told you in 2025 are contradicted by later sources"). Is that in scope, and who verifies?
- **Model drift.** Changing the extraction model changes how things are atomized (Wanner et al.). How do we version candidates so a re-run does not produce a flood of near-duplicates?
- **Gold-set creation cost.** Every falsifiable claim above needs ~30 annotated conversations from the user's own data, roughly 4–8 hours of the person's time (estimate). Is that acceptable, and can annotations be collected inside normal review?

## Sources

- Local inspection, this machine (2026-10-07): Claude Code session JSONL schema (`~/.claude/projects/*/*.jsonl`), Claude Code file-based memory (`MEMORY.md` index plus typed frontmatter files), Codex rollout JSONL (`~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`), and the Codex memory DB schema (`~/.codex/memories_1.sqlite`). Keys, counts and sizes only.
- ChatGPT export format guide (ai-chat-importer): https://ai-chat-importer.com/guides/chatgpt-export-format-explained
- Claude export guide (ai-chat-importer): https://ai-chat-importer.com/blog/how-to-export-claude-conversations
- Claude export missing project associations (issue report): https://claudeissues.com/issue/40411-claude-ai-data-export-missing-conversation-to-project-associations
- claude-export-viewer (mentions users/projects/memories/conversations JSON): https://tomevault.io/tome/lordjabez/claude-export-viewer
- Codex CLI rollout format (D. Vaughan, 2026): https://codex.danielvaughan.com/2026/03/30/codex-cli-session-analytics-jsonl-rollout
- Readwise API (v2 export endpoint): https://readwise.io/api_deets
- Metropolitansky & Larson, "Towards Effective Extraction and Evaluation of Factual Claims" (Claimify), ACL 2025: https://arxiv.org/abs/2502.10855
- Wanner et al., "A Closer Look at Claim Decomposition", *SEM 2024: https://arxiv.org/abs/2403.11903
- Chen et al., "Dense X Retrieval: What Retrieval Granularity Should We Use?", EMNLP 2024: https://arxiv.org/abs/2312.06648
- Min et al., "FActScore", EMNLP 2023: https://arxiv.org/abs/2305.14251
- Chhikara et al., "Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory", 2025: https://arxiv.org/abs/2504.19413
- Mem0, "The token-efficient memory algorithm" (Apr 2026, updated Sep 2026): https://mem0.ai/blog/mem0-the-token-efficient-memory-algorithm
- HaluMem: "Evaluating Hallucinations in Memory Systems of Agents" (Nov 2025): https://arxiv.org/abs/2511.03506 (tables via https://www.alphaxiv.org/abs/2511.03506)
- Yang, "Control-Plane Placement Shapes Forgetting…" (ForgetEval), June 2026: https://arxiv.org/abs/2606.15903
- WildReward: "Learning Reward Models from In-the-Wild Human Interactions" (2026): https://arxiv.org/abs/2602.08829
- Liu, Zhang & Choi, "User Feedback in Human-LLM Dialogues…" (2025): https://arxiv.org/abs/2507.23158
- WildFeedback (2024): https://arxiv.org/abs/2408.15549
- Fountas et al., "EM-LLM: Human-inspired Episodic Memory for Infinite Context LLMs", ICLR 2025: https://arxiv.org/abs/2407.09450
- Park et al., "Generative Agents", 2023: https://arxiv.org/abs/2304.03442
- Koenecke et al., "Careless Whisper: Speech-to-Text Hallucination Harms", FAccT 2024: https://arxiv.org/abs/2402.08021
- SpAIware / ChatGPT memory injection (The Hacker News, Sept 2024): https://thehackernews.com/2024/09/chatgpt-macos-flaw-couldve-enabled-long.html
- OpenAI ChatGPT memory "Dreaming V3" (Thurrott, June 2026): https://www.thurrott.com/a-i/337052/openai-is-improving-how-chatgpts-memory-works
- Claude memory import (PCWorld, March 2026): https://pcworld.com/article/3076376/claude-can-now-import-chat-histories-from-chatgpt-and-other-ais.html ; Bloomberg (2026-03-03): https://www.bloomberg.com/news/articles/2026-03-03/anthropic-tries-to-win-users-from-chatgpt-with-memory-feature
- van der Sijs et al., "Overriding of drug safety alerts in computerized physician order entry", JAMIA 2006 (recalled; not re-verified this session).
- Clark & Brennan, "Grounding in communication", 1991 (from knowledge).
