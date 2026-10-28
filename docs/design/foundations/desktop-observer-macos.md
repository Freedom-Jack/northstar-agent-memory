# Desktop fidelity module for macOS (optional)

Written 2026-10-08. Design and assessment. Revised on 2026-10-08 after a goal-fidelity audit; see "Fidelity fixes (2026-10-08)" at the end. Revised again after the adversarial review; see "Review revisions (2026-10-08)" at the end.

**Status.** This is a design input for the Northstar architecture. It describes an **optional, separable** component. The user has **not** accepted it, and nothing here assumes they will. [`docs/GOAL.md`](../../GOAL.md) overrides this note. Where this note finds a part of the goal that cannot be met on a surface, it records a **risk** (§10) or a **question for the user** (§11). It never narrows the goal.

**The spine supersedes this note's vocabulary and layer names (2026-10-08).** [`SPINE.md`](SPINE.md) §4 defines the one connector contract and its capability levels; they replace the level words in §3 and §8. This note's L2 is the spine's **L2-inject** and its L3 is the spine's **L2-auto** (SPINE §1.4). Where a working assumption here differs from the spine's user questions (SPINE §11.2), the spine governs: UQ-1 replaces D-Q1 and D-Q4 for what the module may write or send, and UQ-9 governs live evaluation arms.

**Tool names follow the one MCP tool contract: CX §1.2 and §2** ([`connectors-desktop-and-mcp.md`](../components/connectors-desktop-and-mcp.md); consistency fix X01). The body of this note uses the CX names. Name map:

| Earlier name in this note (or SPINE) | CX name |
|---|---|
| `northstar_turn` (SPINE's earlier `northstar_sync`) | `northstar_context` |
| `northstar_resume` | The first `northstar_context` call of a chat, which returns the pack; a restart pack is fetched by its handle through `northstar_context` |
| Argument `user_turn_excerpt` | `user_message` (copied exactly) |
| Argument `my_last_reply_digest` | `prev_reply_points` (envelope `reported_points`) |
| Argument `session` (tag `NS-7F3K`) | `session`, carrying the turn tag `NS-7F3K.14` (format `NS-XXXXXX.<n>`, CX §2.3) |

Map of level words:

| This note (§3, §8) | SPINE §4.2 |
|---|---|
| det/verb (user turn from the composer) | `verbatim_live` |
| det/verb (transcript, after the reply) | `verbatim_rendered` |
| aft (export backfill) | `verbatim_deferred` (capture) or `deferred` (audit) |
| aft on m_rep / aft (det check) | `next_turn_reported` / `next_turn_verbatim` |
| det (injection) | `deterministic` |
| m_pull, m_rep, static, none | `model_pulled`, `model_reported`, `static`, `none` |

**What the module is.** A small macOS helper app. It reads the Claude Desktop and ChatGPT Desktop chat windows through the macOS Accessibility (AX) API. Optionally, it adds a visible, labelled Northstar block to the composer, and it can drive a fresh-chat restart. It is the desktop analogue of the browser extension in SYNTHESIS (AD1–AD3, RISK 1). The user said on 2026-10-08 that the extension is not required (GOAL §2, §4.6). The same caution applies here: this module is ToS-grey, and the user decides.

**Sources and conventions.**
- Research notes: [10] integration surfaces, [11] in-session drift, [12] knowledge structure, [13] robust maintenance, [14] memory-layer landscape, all in `docs/research/round2/`. SYNTHESIS means `docs/research/round2/SYNTHESIS.md`.
- Component docs in `docs/design/components/`: CX = `connectors-desktop-and-mcp.md`, IS = `ai-in-session.md`, AC = `ai-continuity.md`, PL = `platform-security-privacy.md`.
- Product facts carry a source URL and the date checked. All web checks were made on **2026-10-08**. Local checks of installed app bundles on this Mac were also made on 2026-10-08; they read app binaries, folder names and database schemas only, never conversation content.
- **(Unv)** marks a product fact I could not confirm. Each one has a spike in §12.
- Surfaces in this note:
  - **CD**: Claude Desktop, chat (not the Code tab, not Cowork).
  - **GD**: the ChatGPT desktop app, **Chat** mode (not Work, not Codex threads).
  - **GC**: ChatGPT Classic, the older native Mac app (see §2.1).

---

## 0. Summary

1. **Both desktop chat apps are now Chromium-based.** Claude Desktop is an Electron app. The merged ChatGPT and Codex app is the main ChatGPT desktop app, built on a Chromium/Electron-family shell. The older native app is now called ChatGPT Classic. So one AX capture engine (the Chromium AX tree) can serve both CD and GD (§2.1).
2. **Without the module**, CD and GD stay PARTIAL on the requirements that matter most: no live verbatim capture of what the AI said (GOAL §4.2), and in-session focus that works only when the model chooses to call a Northstar tool (§4.5). This is SYNTHESIS RISK 4. Exports are backfill only, because a recurring export is a ritual (RISK 19).
3. **With shadow capture (L1)**, both sides of every turn are captured verbatim, with the conversation's identity, after each reply. The core gets AI-said passages as first-class records, and an independent ground truth for audits. Delivery of focus state is still model-pulled.
4. **With visible injection (L2)**, a short, labelled Northstar block is pre-placed in the composer before each user turn. Per-turn focus on the goals and constraints the user typed, the chat-start block and specific drift corrections become deterministic, apart from turns where the user deletes the block. The block never carries AI-said, provisional or reported items, because it sits in the user's own message; those stay model-pulled (§4.4).
5. **With automation (L3)**, the module can open a fresh chat with a resume pack (consolidate-and-restart, AD12). It can also send an optional correction turn. This is the most ToS-exposed layer.
6. **What no layer gives:** correcting a reply before the user sees it (RISK 20); hidden injection; a whole-chat, same-chat comparison inside the app (RISK 21); control over vendor compaction; capture of attachment contents and of branches the user never displays.
7. **Terms.** OpenAI's terms say users may not "Automatically or programmatically extract data or Output". Anthropic's consumer terms prohibit access "through automated or non-human means". Reading the window is less exposed than an extension that calls internal APIs, and injection and automation are more exposed than reading. None of it is sanctioned (§5).
8. **Precedent cuts both ways.** OpenAI's own Computer History and Work with Apps read other apps through Accessibility. Anthropic's computer use drives other apps. Rewind was shut down after an acquisition, and Microsoft Recall was delayed over security. No enforcement against a third-party chat reader was found, which is absence of evidence, not permission (§5.3).
9. **Managed Macs.** If this Mac is employer-managed (management enrolment, security agents, a TLS proxy), employer policy may forbid a helper that reads other apps, and a security agent may flag it; whether a grant is possible depends on the management profile. Install-time checks report the facts locally (V27). Employer policy is a user question (D-Q2). macOS 27 is reported to change how Accessibility is granted (Unv) (§4.7).
10. **Security.** A process that reads every chat and can type into apps is the most sensitive part of Northstar. The design keeps it code-only, with no network, an app allowlist, write actions that fail closed, and a visible status indicator (§4.8).
11. **The user decision (D-Q1, now SPINE UQ-1)** is whether to accept the module, and which sub-modules. *Working assumption (pending user answer), as SPINE UQ-1:* yes to capture (L1 read) on allowlisted personal-account chats, with Temporary and incognito chats skipped; visible injection (L2-inject) only where the sanctioned widget context fails its spike (CD-S2 / CS4); automation limited to a restart that prepares a fresh chat but never sends it; no auto-send and no correction turns. Until the user answers, the module exists only as spikes on synthetic test chats (§11).
12. **Two sanctioned spikes come first,** because either could shrink the module: whether Codex hooks fire in GD Chat mode (DS1), and whether MCP App model context persists per turn on CD and GD (DS2).

---

## 1. Why this module exists

**The gap.** SYNTHESIS Table A rates CD and GD as follows with sanctioned channels only:

| Requirement | CD | GD |
|---|---|---|
| Capture user-said, verbatim (§3.1) | PARTIAL: live, only an MCP paraphrase | PARTIAL |
| Capture AI-said, verbatim, near real time (§4.2) | CANNOT live; PARTIAL later | CANNOT live; PARTIAL later |
| Deterministic per-turn focus injection (§3.3) | PARTIAL at best: model-pulled | CANNOT–PARTIAL |
| Check each reply and correct drift (§3.3) | CANNOT live | CANNOT live |
| Consolidate and restart (§3.3) | PARTIAL | PARTIAL |
| New chat starts with prior state (§3.3) | PARTIAL: model-dependent | PARTIAL–CANNOT |
| No per-chat user action (§4.3) | PARTIAL | PARTIAL–CANNOT |
| Independent ground truth for audit (§4.7) | PARTIAL: after the fact | PARTIAL: export |

**Why it matters now.** On 2026-10-08 the user made CD and GD first connectors (GOAL §2, §4.6). The task brief therefore makes these gaps first-priority problems. GOAL §4.2 and §4.5 are non-negotiable. A design that leaves them PARTIAL must say so as a risk. This module is the only mechanism found that can close them on these two surfaces without the vendors' help.

**Why it must stay optional.** It is ToS-grey (§5), it breaks when the apps change (§4.7), and it sees everything (§4.8). The core, the connectors and the human view must work without it. The module adds fidelity; nothing in the core depends on it.

---

## 2. Verification

### 2.1 Facts verified for this note

| # | Fact | Result | Source | Checked | Status |
|---|---|---|---|---|---|
| V1 | Claude Desktop is Electron | Bundle `com.anthropic.claudefordesktop` ships `Electron Framework.framework` with a bundled Chrome. Exact installed versions are machine facts; `northstar doctor` records them in the data root | Local inspection of `/Applications/Claude.app` | 2026-10-08 | Verified |
| V2 | Claude Desktop chat renders claude.ai web content | Its Chromium profile holds IndexedDB for the `https://claude.ai` origin | Local folder names in `~/Library/Application Support/Claude/` | 2026-10-08 | Verified |
| V3 | The ChatGPT desktop app is native (task brief) | **Corrected.** The installed `ChatGPT.app` has bundle ID `com.openai.codex`. It ships `Codex Framework.framework` (a Chromium build), `app.asar`, Electron fuse markers and "owl_electron" strings. It is a Chromium/Electron-family shell | Local inspection of `/Applications/ChatGPT.app` | 2026-10-08 | Verified (local) |
| V4 | The native app became "ChatGPT Classic" on 2026-07-09; the merged ChatGPT/Codex app is now the main desktop app; Classic can still be installed | Reported by Daring Fireball, which also calls the new app an Electron bundle of about 1.5 GB against about 159 MB for Classic | https://daringfireball.net/linked/2026/07/09/todays-the-day-openai-fucked-up-the-chatgpt-mac-app ; OpenAI release notes https://help.openai.com/en/articles/9703738 (HTTP 403) | 2026-10-08 | Secondary; consistent with V3 |
| V5 | The ChatGPT desktop app has Chat, Work and Codex | "use the toggle above the composer to select Chat or Work"; it runs on macOS, Windows and Linux | https://learn.chatgpt.com/docs/app | 2026-10-08 | Verified |
| V6 | Electron builds its AX tree only when assistive technology asks | Accessibility turns on automatically with assistive technology, and third-party tools can turn it on by setting `AXManualAccessibility` on the app element | https://www.electronjs.org/docs/latest/tutorial/accessibility | 2026-10-08 | Verified |
| V7 | AX tree has a CPU cost | Electron's API docs warn that rendering the accessibility tree "can significantly affect the performance of your app" | https://www.electronjs.org/docs/latest/api/app | 2026-10-08 | Verified (size of cost Unv) |
| V8 | Both apps are hardened against code injection | Fuses: RunAsNode off, `NODE_OPTIONS` off, `--inspect` off, embedded ASAR integrity on, load only from ASAR on, cookie encryption on | Local read of the Electron fuse wire in both framework binaries | 2026-10-08 | Verified |
| V9 | URL schemes | Claude Desktop registers `claude://`. The ChatGPT app registers `codex://` (plus http/https) | Local `Info.plist` of both apps | 2026-10-08 | Verified (what the schemes accept is Unv) |
| V10 | Prefilled new chat by URL | `claude.ai/new?q=` is widely used but undocumented; whether it auto-sends is disputed; a `claude://` variant is reported for Desktop | https://www.vincentschmalbach.com/claude-chatgpt-bookmarklets/ ; https://u2l.ai/tools/claude-prompt-link-generator ; https://directory.getdrafts.com/a/25n | 2026-10-08 | Unv |
| V11 | Codex hooks in GD **Chat** mode | Not documented. The docs say hooks "continue to work in local-only Work and Codex threads". `Stop` can force a continuation | https://learn.chatgpt.com/docs/hooks | 2026-10-08 | Unv for Chat mode |
| V12 | OpenAI MCP Extensions model context on desktop | Support table: "Model context" Supported on Desktop; thread entrypoints are opened manually by the user; context with `audience: ["assistant"]` is hidden from the user; each update replaces the last. Persistence across turns is not defined | https://github.com/openai/mcp-extensions/blob/main/docs/spec.md | 2026-10-08 | Verified; Chat-mode persistence Unv |
| V13 | Claude MCP App model context | Feeds "Claude's context for the next turn"; widgets lazy-mount as they scroll into view when a stored chat reopens; neither `hostContext` nor tool arguments carry a conversation ID | https://claude.com/docs/connectors/building/mcp-apps/instance-supersession | 2026-10-08 | Verified; per-turn persistence Unv |
| V14 | OpenAI's Computer History reads apps through Accessibility | Uses "text and other context available through macOS accessibility features"; needs no Screen Recording; off by default; Pro can enable it, and Business and Enterprise need an admin; apps can be excluded; event files deleted after 48 h; memories stored as unencrypted Markdown under `~/.codex/memories/extensions/skysight/` | https://learn.chatgpt.com/docs/customization/computer-history | 2026-10-08 | Verified |
| V15 | OpenAI's Work with Apps reads other apps through Accessibility | Help Center article 10119604 (seen as search snippets; page returned 403): most integrations rely on the macOS Accessibility API | https://help.openai.com/en/articles/10119604 | 2026-10-08 | Secondary (snippets) |
| V16 | OpenAI acquired Sky (Mac AI that reads the screen through Accessibility) | Announced 2025-10-23 | https://techcrunch.com/2025/10/23/openai-buys-sky-an-ai-interface-for-mac/ | 2026-10-08 | Secondary |
| V17 | Anthropic's computer use drives other Mac apps | In Cowork and Claude Code in Claude Desktop; Pro and Max beta; asks before each app; "generally waits if you're in the middle of typing" | https://support.claude.com/en/articles/14128542-let-claude-use-your-computer | 2026-10-08 | Verified |
| V18 | OpenAI terms prohibit programmatic extraction | "Automatically or programmatically extract data or Output"; also "Modify, copy, lease, sell or distribute any of our Services" and circumventing protective measures. Same list in the 2024-12-11 archive and in 2026 snippets. The live page lists "Effective: January 1, 2026 (Previous version)", so a newer version exists whose text I could not read | https://openai.com/policies/terms-of-use/ (Cloudflare 403) ; archive https://open.windriver.com/info/uni-license-list/licenses/openai-tou-20241211.html ; snippets via search | 2026-10-08 | Clause verified; current version text Unv |
| V19 | Anthropic consumer terms | Effective 2025-10-08. Prohibits access "through automated or non-human means, whether through a bot, script, or otherwise" except with an API key or explicit permission; "To crawl, scrape, or otherwise harvest data or information from our Services"; reverse engineering; "bypassing any of our systems or protective measures". No clause about modifying the services; third-party integrations are "at your own risk" | https://www.anthropic.com/legal/consumer-terms | 2026-10-08 | Verified |
| V20 | The native ChatGPT app once stored chats in plain text | Reported July 2024; fixed in 1.2024.171 by encrypting the store | https://www.ghacks.net/2024/07/08/chatgpts-macos-app-was-storing-chats-in-plain-text-but-it-has-been-patched/ | 2026-10-08 | Secondary |
| V21 | Rewind's Mac capture was switched off | After Meta acquired Limitless; recording disabled 2025-12-19 | https://9to5mac.com/2025/12/05/rewind-limitless-meta-acquisition/ | 2026-10-08 | Secondary |
| V22 | Microsoft Recall was delayed over security | Unencrypted early database; made opt-in with encryption and Windows Hello before relaunch | https://www.techrepublic.com/article/news-microsoft-recall-expands-rollout/ | 2026-10-08 | Secondary |
| V23 | Screenpipe reads text through Accessibility, OCR as fallback | Vendor says Accessibility uses about 100× fewer resources than OCR | https://screenpi.pe/blog/screenpipe-v2-03-accessibility-capture | 2026-10-08 | Vendor claim |
| V24 | MDM can pre-allow Accessibility and PostEvent; standard users cannot self-approve Accessibility | Apple: Accessibility "Allows specified apps to control the Mac via Accessibility APIs"; PostEvent allows sending CGEvents; supervision required. Standard-user delegation covers ListenEvent and ScreenCapture only (third-party docs) | https://support.apple.com/guide/deployment/dep38df53c2a/web ; https://support.kandji.io/support/solutions/articles/72000560493 | 2026-10-08 | Verified (Apple) + secondary |
| V25 | macOS 27 changes Accessibility granting | Developer-forum reports from the betas: legacy PPPC handling of Accessibility changed, and the switch became user-visible; an Apple DTS engineer called the change deliberate | https://origin-devforums.apple.com/forums/thread/836770 | 2026-10-08 | Unv (beta reports) |
| V26 | Screen Recording needs periodic re-approval | On macOS 15, about monthly, including ScreenCaptureKit apps; cadence on macOS 26 not confirmed | https://tidbits.com/2024/08/19/apple-reduces-excessive-sequoia-permission-requests-shifts-to-monthly | 2026-10-08 | Secondary; macOS 26 Unv |
| V27 | Environment checks | Environment checks run at install (`northstar doctor`): management enrolment, security agents, a TLS proxy, admin rights, privacy profiles; results stay in the data root | `northstar doctor` at install | At install | Install-time check; no machine facts in the repo |

### 2.2 Local storage, as found

| App | What exists | Encrypted? | Verdict |
|---|---|---|---|
| Claude Desktop (CD) | A Chromium profile for claude.ai: IndexedDB (about 3 MB), HTTP cache (about 110 MB), Local Storage, Session Storage. Also local stores for the Code tab and Cowork | Cookies yes (fuse V8). Whether chat JSON sits in the cache or IndexedDB is (Unv); content was not read | Not a capture path. Formats are undocumented, the cache evicts, and reading it is "harvest data" (V19). Relevant to security and excision, because a vendor copy may sit on disk |
| ChatGPT desktop (GD) | A Chromium profile for the built-in browser (`~/Library/Application Support/Codex/`). Codex and Work threads in `~/.codex/` as plain SQLite (`state_5.sqlite`, `thread_history_1.sqlite`, per-item JSON) and JSONL rollouts. Every thread found there was a Codex thread; no Chat-mode store was found. Only table names, column names and enum-like values were read | Codex stores: no | Codex threads are already covered by hooks, the sanctioned route [10]. Chat mode appears to be server-side only (Unv) |
| ChatGPT Classic (GC) | Conversation store encrypted since 2024 (V20) | Yes, key handling (Unv) | Decrypting it would bypass a protective measure (V18). Rejected |

### 2.3 Fetch failures

- `openai.com/policies/*`, `help.openai.com` and `support.addigy.com` returned HTTP 403. The bodies were Cloudflare bot challenges. I did not try to get past them; I used an archive and search snippets, as marked.
- `web.archive.org` could not be fetched by the tool.

### 2.4 Corrections to earlier notes

- [10] and the task brief describe the ChatGPT desktop app as native. As of 2026-10-08 the main ChatGPT desktop app is the merged Chromium-based app (V3, V4). The native app survives as ChatGPT Classic. The AX design below treats GD as Chromium web content, and GC as an optional second profile.
- The merged app is also the Codex host. That makes DS1 (do hooks fire in Chat mode?) the single most valuable spike for GD.

---

## 3. Mechanism inventory

### 3.1 Every mechanism a third party could use on CD and GD

Fidelity words follow §8: **verbatim**, **deterministic**, **model_reported** (the model paraphrases into tool arguments), **model_pulled** (happens only if the model calls a tool), **static** (fixed text), **after_the_fact**, **none**.

| ID | Mechanism | Sanctioned? | ToS risk | Breakage risk | Permissions and plan limits | Source |
|---|---|---|---|---|---|---|
| M1 | Northstar MCP tools: Claude connector (remote, or local `.mcpb` in Desktop); ChatGPT developer-mode plugin | Yes | Low | Low (Claude); medium (ChatGPT beta) | Claude: Free 1 custom connector, Pro/Max self-serve, Team/Ent Owner adds; per-chat toggle; Always allow per tool. ChatGPT: Developer mode, plan eligibility conflicting, plugin picked per chat, write approval per conversation | [10 F1, F4, F6] |
| M2 | MCP App model context: Claude `ui/update-model-context`; OpenAI Extensions model context, including hidden background context | Yes | Low | Medium (new) | Needs one tool call (Claude) or a manually opened thread entrypoint (OpenAI) before it starts | V12, V13; [10 F2, F7] |
| M3 | Static instructions: Claude profile preferences, project instructions, plugin skills; ChatGPT custom and project instructions | Yes | Low | Low | All plans; text is fixed and sits at the start of context, where it decays [11 F3] | [10 F3, F8] |
| M4 | MCP prompts the user picks | Yes | Low | Low | Claude; a per-chat user action | [10 F1] |
| M5 | Vendor exports | Yes | Low | Low | Manual; Claude: none for Team/Ent members; ChatGPT up to 7 days. Backfill only (RISK 19) | [10 F13] |
| M6 | Codex hooks in the ChatGPT desktop app | Yes | Low | Medium | Verified for local Work and Codex threads; **Chat mode Unv** (V11) | V11; [10 F9] |
| M7 | AX read of the chat window (this module) | No | Grey: OpenAI "programmatically extract"; Anthropic "automated or non-human means" and "scrape" (V18, V19) | Medium–high: UI updates | TCC Accessibility; any vendor plan; macOS only | V6, V14–V17 |
| M8 | AX write into the composer (`AXValue` or `AXSelectedText`) | No | Grey, higher than M7: automated input | High: editor internals (Unv) | TCC Accessibility | V6; DS6 |
| M9 | Clipboard paste (synthetic Cmd+V) | No | As M8 | Medium | TCC Accessibility or PostEvent; touches the user's clipboard | V24; DS6 |
| M10 | Synthetic keystrokes (CGEvent) | No | As M8 | Medium; collides with the user's typing and input methods | PostEvent | V24 |
| M11 | AX press and UI automation: New chat, Send, Copy, branch arrows | No | Grey, highest: the module acts in the app | High | TCC Accessibility | DS7 |
| M12 | Deep links: `claude://`, `codex://`, `claude.ai/new?q=` | Undocumented | Low–grey | High (undocumented) | Length limits (Unv); prompt text sits in a URL | V9, V10 |
| M13 | Screen capture plus OCR | No | Grey | Medium | Screen Recording, re-approved about monthly on macOS 15 (V26): a recurring user action, so only a diagnostic fallback | V23, V26 |
| M14 | Reading local app storage or caches | No | Grey ("harvest"); decrypting GC is "bypass protective measures" | High | Full Disk Access may be needed | §2.2 |
| M15 | Network interception (local TLS proxy) | No | High: bypassing protective measures | High | Installs a root certificate; clashes with a TLS-inspecting proxy, if one is present | V18; [10 F11] by analogy |
| M16 | Modifying or debugging the app (ASAR patch, `--inspect`, remote debugging, library injection) | No | High: "Modify … our Services"; breaks code signing | Blocked by fuses (V8) | n/a | V8, V18 |
| M17 | Vendor memory read or write | No third-party API | n/a | n/a | n/a | [10 F14] |
| M18 | Northstar's own overlay panel beside the app window (menu bar, badge) | n/a: it is Northstar's UI | None for display; reads window position via AX | Low | Shows the user, never the model | Design |
| M19 | The per-message Copy button (AX press, then read the clipboard) | No | As M11 | High | Clipboard side effects | DS4 |
| M20 | Vendor activity-memory files (ChatGPT Computer History Markdown) | Readable local files the user owns | Low–grey | Medium | Pro, off by default; vendor summaries, not verbatim | V14 |

**Rejected outright:** M14 as a capture path, M15 and M16. They are the most ToS-exposed, and M15 and M16 weaken the security of the user's own sessions. M13 is kept only as an off-by-default diagnostic, because its permission must be re-approved, which would be a user ritual (GOAL §4.1).

### 3.2 Capability by mechanism, CD and GD

Each cell gives the best fidelity the mechanism reaches. "—" means it does not help.

| Capability | M1 MCP tools | M2 MCP App context | M3 Static | M5 Export | M6 Codex hooks | M7 AX read | M8/M9 composer write | M11/M12 automation |
|---|---|---|---|---|---|---|---|---|
| Capture user turns | model_reported | — | — | after_the_fact, verbatim (backfill) | CD —; GD deterministic, verbatim **if** DS1 | deterministic, verbatim (composer value at send, plus transcript) | — | — |
| Capture AI turns verbatim | model_reported, prior turns only | — | — | after_the_fact (backfill) | GD verbatim **if** DS1 | deterministic, verbatim after the reply ends | — | Copy button gives exact Markdown (M19) |
| Per-turn context injection | model_pulled (tool result) | deterministic after first mount **if** DS2 | static | — | GD deterministic **if** DS1 | — | deterministic, visible | — |
| Chat-start injection | model_pulled; M4 user-picked | needs a first call or panel | static boot line | — | GD **if** DS1 | — | deterministic (pre-armed block) | deep link prefill (Unv) |
| Per-reply drift check and correction | check on model_reported digest only | delivery if DS2 | — | — | GD `Stop` can continue **if** DS1 | check: after_the_fact on verbatim | correction delivered next turn | optional automatic correction turn |
| Consolidate and restart | model may suggest; user acts | — | — | — | GD `SessionStart` **if** DS1 | — | start block (≤ 1,500 chars) pre-armed when the user opens a chat | automatic (open, fill, optionally send) |
| Independent ground truth for audit | — | — | — | after_the_fact | GD transcript **if** DS1 | deterministic: composer vs transcript, sweep vs incremental | — | — |
| Writes into Northstar | model_pulled (write tools; ChatGPT re-approves per conversation) | via widget to server | — | batch | GD deterministic **if** DS1 | deterministic (module to core) | — | — |

---

## 4. Module design

### 4.1 Shape

The module is a **separate signed app** ("Northstar Observer") plus a set of per-app **profiles**. It has no language model inside. It talks only to the local Northstar core.

```
 Claude Desktop (Electron)      ChatGPT desktop (Chromium shell)      [ChatGPT Classic, native]
          \                             |                              /
           \------------- macOS Accessibility API (AX) --------------/
                                        |
                        +-------------- Observer app --------------+
                        |  App profiles (per app + version)        |
                        |  Capture sub-module      (read only)     |
                        |  Injection sub-module    (switch)        |
                        |  Automation sub-module   (switch)        |
                        |  Safety governor (allowlists, fail-closed,|
                        |    typing guard, write audit log)        |
                        |  Status UI (menu bar, optional badge)    |
                        +------------------------------------------+
                                        |  Unix domain socket, local only
                                        v
                        Northstar core: raw-event intake (J0), fast lane
                        (Session Steward, Drift Checker, Context Composer),
                        slow lane, compiler (pins, cards, packs)
```

**Rules that make it separable.**
- The core never requires the module. Every core feature has a sanctioned path (L0, §6.1).
- The module never derives knowledge. It sends raw, timestamped capture events. The core's J0 normalizes them, exactly as for hooks [13]. Pins, cards and packs come from the core's compiler; the module only places them.
- The module never holds vendor credentials. It never reads cookies, tokens or network traffic.
- Each sub-module has its own switch. Injection and automation are off unless capture is on.
- **No network, now or later.** When the core moves to the cloud, the module keeps sending to the local socket. A small local intake forwarder (`northstar-forwarder`, SPINE §7.5) relays socket events to the cloud intake over authenticated HTTPS with the same spool, so the module itself never gets network access or a cloud credential.

### 4.2 Modes and switches

| Mode | Capture | Compute pin/card/check | Deliver into the app | Automation | Use |
|---|---|---|---|---|---|
| Off | No | No | No | No | Default until the user answers D-Q1 |
| **Shadow** | Yes | Yes, logged as "would have injected" | No | No | Baseline for measurement (§6 of GOAL); safe first install |
| Capture | Yes | Yes | Only through sanctioned channels (tool results, MCP App context) | No | L1 |
| Capture + Inject | Yes | Yes | Visible composer block | No | L2 |
| Capture + Inject + Automate | Yes | Yes | Visible block | Restart; optional correction turn | L3 |

Switches are per app (CD, GD, GC) and per account. An **evaluation arm** setting randomizes Shadow against Inject per new chat, as in SYNTHESIS protocol C. It is off until the user says yes to SPINE UQ-9, which also sets the share (working assumption 50%) and a stop rule after which every chat is treated.

### 4.3 Capture sub-module

**How it reads.**
1. On launch, and whenever an allowlisted app starts, the module sets `AXManualAccessibility` on the app's AX element so Chromium builds its tree (V6). If assistive technology is already running, the tree exists anyway.
2. It finds the chat's web area and the conversation region using the app profile. Chromium exposes roles, labels and text. Whether it also exposes the page URL and DOM class lists to AX clients on macOS is (Unv) (DS4).
3. It watches coarse AX notifications (focus, window, value changes in the composer) and polls only the **last message subtree**, at most twice a second, while a reply streams. It does not poll an idle window.
4. When a reply ends, it reads the whole last turn pair once, final text only. This is the desktop form of the "post-turn read" in AD2.
5. When a conversation opens, and hourly on mains power while idle, it runs a full sweep of the visible conversation for audits and backfill.

**The user turn is captured twice, independently.**
- From the composer: the module watches the composer's value. On send, the composer empties. The last non-empty value, minus any Northstar block (§4.4), is the user's turn **by construction**. Speaker comes from where the text was typed, not from parsing the transcript. This is SYNTHESIS §5 item 1 ("speaker by construction"), now on a chat surface.
- From the transcript: the rendered user message is read after the turn.
- The two must match. A mismatch is a capture alarm (§4.7) and an audit datum.
- A large one-step jump in the composer's value marks a likely paste, which feeds paste detection (RISK 10).

**Completeness by item.**

| Item | Approach | Expected fidelity | Main uncertainty |
|---|---|---|---|
| Streaming text | Watch the last message; never store partial text as final | Final text verbatim | Notification coverage for static text in Chromium (Unv); polling covers it |
| End of reply | Combine signals: the stop control disappears and the send control returns; the per-message action bar (copy, retry) appears; text unchanged for 2 s | Reliable with 2 of 3 signals (Unv) | Labels change between versions; covered by profile tests |
| Long, virtualised chats | Capture is per turn, live, so old messages need not be on screen. Sweeps read whatever the DOM holds | Live turns complete; sweeps may miss off-DOM history | Whether either app virtualises its message list (Unv, DS4). Chromium keeps off-screen DOM nodes in the AX tree |
| Code blocks | Read the code element's text; record the language label | Text verbatim; whitespace fidelity (Unv) | The Copy-button route (M19) gives exact Markdown, at a clipboard cost; off by default |
| Maths, tables, rich rendering | Read the AX text | Partial: rendered maths may come out as spoken form | Copy-button route as an option |
| Edits and branches | Read the branch indicator ("2 / 3") and the visible path. A change of visible path is a branch event; earlier paths are kept, never deleted | Visible path verbatim; branch index recorded | Branches the user never displays are not captured. Opening them would need automation (L3) |
| Regenerations | Same as branches: a retry is a sibling reply | As branches | As branches |
| Attachments | Record names, types and presence of images | Metadata only | Contents are not captured |
| Thinking, tool use, web search | Record visible summaries and a "grounded" flag when search or tools ran | Summary only; flag feeds ranking by grounding (SYNTHESIS §3.1) | Collapsed sections are not expanded |
| Model identity | Read the model selector label | Label as shown (Unv) | |
| Message identity and order | No vendor message IDs are visible to AX (Unv). Identity = conversation ID + branch path + ordinal + content hash | Stable within a conversation; reconciled to exports by hash | DOM ids may be exposed (Unv) |
| Conversation identity | Page URL from the web area (`claude.ai/chat/<id>`, `chatgpt.com/c/<id>`) if exposed; else window title plus first-message hash | Exact if the URL is exposed (Unv, DS4) | |
| Temporary and incognito chats | Detect the app's indicator; **skip when unsure** | Fail-safe | Indicator labels (Unv) |
| Account | Read the account or organization label; capture only allowlisted personal accounts (GOAL §2: personal first) | One-time setup choice if not detectable | (Unv) |
| Built-in browser in the ChatGPT app | Never captured; only chat thread views are allowed | n/a | Route detection (Unv) |

**Data contract to the core.** Each event carries:
- `speaker` (user, assistant), set by the module from where the text was observed, never by a model;
- `capture_fidelity: verbatim`, `channel: ax_observer`, the app, the app version and the profile version;
- an anchor locator `{surface, conversation_id, branch_path, ordinal, content_hash}` (SYNTHESIS §3.1);
- `origin` for any span that came from a Northstar block (`northstar_injected`), which is never user-said (§4.4);
- flags for paste, grounding, model label and attachments;
- the wire form of CX §6.1 under `northstar.connector/1.1` (the SPINE §4.3/§4.4 delta): `conv_key {kind: observer_url | title_hash}` and `account.source: ax_label | install_declaration`.

**Peer check on the socket.** The core checks the sender of **every** message on the local socket. It reads the peer's audit token (`LOCAL_PEERTOKEN`) and runs a code-signing check on it against the observer's Developer ID and bundle ID. It never identifies the observer by PID, because a PID can be reused by another process between the check and the message. A message that fails the check is dropped and raises an alarm (§4.8).

**A gain beyond capture.** When the user opens on the desktop a chat they started on mobile or the web, the sweep backfills those turns verbatim, within what the DOM holds. Cross-device turns are therefore captured whenever the chat is next opened on this Mac.

### 4.4 Injection sub-module

**The block.** One visible, plain-text block, written as attributed facts in the third person, never as commands, and never imitating vendor tags (SYNTHESIS §5 items 7–8; [10 F5]):

```
[Northstar context | auto-added | Session: NS-7F3K.14]
Goal (you, turn 1): a migration plan that keeps the API backward compatible.
Constraint (you, turn 3): no new runtime dependencies.
Constraint (you, turn 6): not option B, the big-bang switch.
Correction pending: the previous reply re-proposed option B (ruled out by you at turn 6).
[end Northstar context]
```

**Content rule: what a block may carry.** The block sits inside the user's own message. So the chat model, and any vendor memory, read it with the weight of the user's voice. For that reason a block carries only:
- goals and constraints **the user typed**, verbatim-confirmed (captured from the user's own turn, not reported by a model);
- **pending corrections** of the previous reply.

It never carries AI-said, provisional or reported items. In the example, a cutover plan Claude proposed at turn 9 would not appear. Those items reach the model only through channels that label them as Northstar output: tool results, widget context, the first `northstar_context` call or `northstar_fetch`. They stay first-class and attributed in the core; only this delivery channel excludes them. The rule applies to every block the module places: per-turn blocks, trigger blocks, chat-start blocks and the restart block (§4.5). Whether a visible block may be used at all is DQ-1(c) / SPINE UQ-1.

- **Block budgets (IS §8.3, AC §3.4):** per turn ≤ 600 chars (the pin's user-typed lines, about 80–150 tokens); ≤ 1,800 chars on triggers (the pin plus a correction, or a card's user-typed lines); at chat start ≤ 1,500 chars, drawn from AC's part S under the content rule (the user's typed goals and constraints; part S's recent provisional items are left out). The full pack (1.5–3k tokens) is never pre-armed. The rest arrives through the first `northstar_context` call, the turn-2 card or `northstar_fetch` (SPINE §4.7).
- The turn tag (`NS-7F3K.14`) uses the one turn-tag format, `NS-XXXXXX.<n>`: the session handle, a dot, the turn number (CX §2.3). It is the same tag that ends every Northstar tool result (`Session: NS-7F3K.14`). It is a join key (`nonce_echo`): the model passes it as the `session` argument of `northstar_context`, which lets the core match model-reported tool calls to the verbatim turns (§6.2).

**The pre-arm protocol.** The module cannot intercept the Send key without an event tap, which would need Input Monitoring and would behave like a keylogger. It does not do that. Instead:
1. When a reply ends (or a new chat opens), the core compiles the next pin within the fast lane. If it is late, the last validated pin is used (SYNTHESIS RISK 16 fallback).
2. If the composer is empty, the module places the block in it and puts the caret **before** the block. The user types above it, so the block ends up at the end of the user's message, the position that holds best [11 F3].
3. If the user is already typing, the module does nothing for that turn.
4. When the user sends, the composer value is captured (§4.3) and the block is split out by exact match.

**Insertion methods, in order of preference.**

| Method | Honest and visible | Failure modes | Interaction with typing |
|---|---|---|---|
| AX insert at caret (`AXSelectedText`) or set value (`AXValue`) | Yes | The editor's internal model may not register an AX write (Unv, DS6); verify by reading back | Only into an empty composer; caret restored |
| Clipboard paste (synthetic Cmd+V), then restore the clipboard | Yes. Long pastes may become a "pasted text" attachment, which is a tidy, labelled form (Unv) | Clipboard managers and Universal Clipboard may copy it; mark the pasteboard item transient and concealed; restore the old contents | As above |
| Synthetic keystrokes | Yes | Slow; Return may send early; input methods interfere | Worst: interleaves with the user's keys. Not used |
| Deep link to a prefilled new chat | Yes | Undocumented; length limits (V10). So the prefill carries only the handle and one fixed line, ≤ 600 chars, no item text; the pack arrives on the first `northstar_context` call | Only for restarts (§4.5) |

**Rules against interference (safety governor).**
- Write only into an empty composer, or one that holds only the previous Northstar block.
- Never write within 3 s of a change in the composer's value, or while an input method is composing.
- Read back after every write. On mismatch, remove the block if that is safe, then switch injection off for that chat and raise an alarm.
- If the user deletes the block, respect it for that turn and record `user_removed`. It is never re-added in the same turn.
- Never write into an app whose profile has not passed its self-test for the running app version (§4.7). Unknown version means shadow only.

**Attribution.** The block is inside the user's message as the vendor stores it. Northstar must not mistake it for user-said text:
- The core removes the block by exact match against what the module inserted, and stores it as `origin: northstar_injected`.
- If the user edited inside the block's markers, the whole marked region is stored as `northstar_injected, user_modified`. It never creates goals, constraints or instructions. Only text typed outside the markers is user-said (invariant I5).
- The model's reply may echo block contents. Lineage counting treats that echo as derived, never as independent support (I11).

**Honesty.** The block is visible, labelled and removable. The menu-bar indicator shows the mode per app. There is no hidden injection: it would need request modification (M15, M16), which is rejected.

**Side effects to accept or manage.**
- The block stays in the vendor transcript. It is shared if the user shares the chat.
- Vendor memory may absorb it (RISK 11; spike S6).
- It counts toward message length and usage limits.

### 4.5 Automation sub-module

**Restart choreography (consolidate-and-restart, AD12).** Code decides when to restart, using drift budget, context length and a detected vendor compaction. Then:
1. Wait until the app is frontmost and idle: no reply streaming, no typing for 5 s. Never steal focus from another app.
2. Read the pending draft in the old composer, if any.
3. Open a new chat: AX press on "New chat", or the app's shortcut, or a deep link (Unv, DS7).
4. Place the **restart block** (compiled from the ledger, never from the transcript, SYNTHESIS §5 item 4) and the carried-over draft beneath it. The block follows the §4.4 content rule and start-block budget (≤ 1,500 chars): the user's typed goals and constraints, pending corrections and the resume handle. The full resume pack arrives by that handle on the first `northstar_context` call.
5. **Prepared mode (proposed default if L3 is accepted):** leave it unsent and show a badge: "Fresh chat prepared with your Northstar state. The old chat is still open." The user sends their next message here, which they were about to do anyway.
6. **Auto-send mode (opt-in):** send the restart block as the first turn at once.
7. If any step fails, undo what is safe, leave the old chat untouched, and log the failure.

**Optional correction turn.** After a flagged reply, the module can send a short, labelled correction message that names the specific violation. It costs a turn and acts on the user's behalf, so it is opt-in (D-Q4).

**Optional paired-branch probe** (SYNTHESIS S9). On sampled turns, use the app's edit or retry to get a vanilla reply in the same chat, then switch the visible branch back. This is for measurement only. It is off by default, because it leaves branches and uses quota.

### 4.6 Local storage

See §2.2. No local store is used for capture. The module's only interest in vendor caches is security: excision in Northstar cannot reach the vendor's own copies, including any on-disk cache (SYNTHESIS §5 item 9).

### 4.7 Permissions, cost and robustness

**Permissions.**
- TCC Accessibility for reading and AX writes; PostEvent only if synthetic keys are used (V24).
- No Screen Recording (M13 is off by default). No Input Monitoring. No Full Disk Access.
- Whether a grant is possible depends on the user's rights and any management profile, checked at install (V27). Whether an employer allows it is a user question (D-Q2).
- The grant is tied to the app's code signature. The helper needs a stable Developer ID signature, or every rebuild loses the grant.
- macOS 27 reportedly changes how Accessibility is granted and shown (V25, Unv). That is a breakage risk to test (DS8).
- A security agent, if present, may flag a process that reads other apps and posts input events (Unv, DS8).

**Cost.** No measurement exists yet. Budgets, to be checked in DS4:

| Budget | Target |
|---|---|
| Observer CPU, idle | ≤ 0.5% average |
| Observer CPU, while a reply streams | ≤ 3% |
| Extra CPU and memory in the chat app from its AX tree | Measured with the tree on and off. If it is large, the tree is enabled only while the chat window is visible (whether it can be switched off again is Unv) |
| Full sweep of a 200-message chat | ≤ 2 s, on mains power, idle only |
| Battery | No measurable change in a 1-hour mixed-use test (powermetrics) |

Screenpipe's vendor figures suggest AX reads are cheap relative to OCR (V23). Electron warns that the tree itself is not (V7).

**Robustness to app updates.** Both apps update often; their version numbers are date-like.
- Profiles are keyed by app bundle ID and version range.
- On every launch and app update, a **self-test** runs on the open window. It checks that turns alternate, that the composer capture matches the transcript, that message counts never fall, and that the end-of-reply signals were found.
- **The self-test record is text-free.** It holds the window's Accessibility roles and hierarchy only, never text. So an AI coding agent can repair a profile from it without seeing personal content.
- If the self-test fails, the module **fails closed to shadow**. It keeps a degraded raw-text capture with an alarm, and injection and automation switch off until the profile passes.
- **Watermarks** per conversation (message count, last content hash) are compared with sweeps, with exports when they exist, and with model-reported tool calls (§6.2). A sudden drop in captured AI-said length is an alarm. This answers [10] R6 ("the maintainer can be blinded silently").
- A broken profile must trip an alarm within one day of use (SYNTHESIS §7.4 drill).
- **Who fixes a broken profile.** Repairing a profile after a vendor UI change is developer work: a code change and a release, which an AI coding agent can make from the failing self-test record (text-free, above). The user is never asked to act. Until the fix ships, the module stays in shadow (or off) and the connector runs at L0 automatically. Expected cadence (Unv): a fix every few weeks while both apps ship frequent UI releases; DS11 measures it. This is a standing maintenance dependency, flagged against GOAL §6 "maintains itself without babysitting" (DR3; SPINE RISK 36).

### 4.8 Security

| Threat | Why it matters here | Design response |
|---|---|---|
| The observer is compromised | It sees every chat and can type into apps | Minimal code; no plugins; no network access, local socket only, also when the core moves to the cloud (a separate forwarder relays, §4.1; SPINE §7.5); hardened runtime; notarized; app allowlist enforced in code; every write logged; kill switch in the menu bar |
| Another local process poses as the observer | A process that reaches the socket could feed fake "verbatim" captures into the core, or receive blocks meant for the composer | The core checks the peer on every message by its audit token (`LOCAL_PEERTOKEN`) plus a code-signing check against the observer's Developer ID and bundle ID, never by PID (§4.3). A failed check drops the message and raises an alarm |
| Prompt injection through captured text | AI replies and pasted web text are untrusted | Captured text is data only. Nothing captured is executed or becomes an instruction (I5). Workers follow the Rule of Two (SYNTHESIS §5 item 8) |
| Injection through Northstar's own block | A poisoned core item would reach every turn (RISK 9) | Only compiler output from validated items; only what the §4.4 content rule allows (typed goals and constraints, pending corrections), because the block carries the user's voice; origin binding (I20); red-team canaries never persist |
| Secrets pasted into chats | The observer captures them | Deterministic intake rules: secrets are redacted before storage and before any model call; PII is tagged at intake and masked at egress (SPINE C06; PL D-PL-4; SYNTHESIS §5 item 9) |
| Clipboard leaks | Paste-based insertion passes through the clipboard | Prefer AX insertion; mark items transient and concealed; restore the clipboard |
| Over-capture | Work accounts, incognito chats, the built-in browser | Account allowlist; skip when unsure; chat views only |
| Store at rest | Verbatim chats on disk | Per PL-3 (PL §2.4), the core's data root uses FileVault if it is on at install, else an encrypted APFS sparse bundle, and real capture stays off until one of them is present. This gate applies to the module too: it captures only synthetic test chats until then. Encrypting the store is a core decision, not the module's |
| A second vendor reads the same chats | If Computer History is on, OpenAI may ingest Claude Desktop chats too (V14) | Shown to the user as a fact. Northstar does not change vendor settings |

---

## 5. Terms of use and precedent

### 5.1 The clauses (checked 2026-10-08)

**OpenAI Terms of Use**, "What you cannot do" (V18; live page blocked; clause text from the 2024-12-11 archive and 2026 snippets, unchanged):
- "Automatically or programmatically extract data or Output"
- "Modify, copy, lease, sell or distribute any of our Services"
- circumventing rate limits, restrictions or protective measures.

**Anthropic Consumer Terms**, effective 2025-10-08 (V19):
- access "through automated or non-human means, whether through a bot, script, or otherwise", except with an API key or where Anthropic explicitly permits it;
- "To crawl, scrape, or otherwise harvest data or information from our Services";
- reverse engineering; bypassing systems or protective measures.

### 5.2 How each sub-module reads against them

This is an engineering reading, not legal advice.

| Sub-module | OpenAI | Anthropic | Exposure |
|---|---|---|---|
| Capture (M7) | Reading the rendered window into a database fits "programmatically extract … Output" closely. It makes no requests to OpenAI and changes nothing | Arguably not "access … through automated means", since the user accesses the service and the module reads local UI. "Scrape … from our Services" is the closer fit | **Grey, lower than an extension.** No internal APIs, no requests, no modification |
| Injection (M8, M9) | Automated input into the service | Closer to "automated or non-human means" | **Grey, higher** |
| Automation (M11, M12) | Automated operation | Squarely "automated means … script" | **Grey, highest.** Auto-send is the most exposed part |
| Rejected (M14–M16) | "bypass protective measures", "Modify" | "bypassing … protective measures", reverse engineering | Out of bounds |

OpenAI's terms give users ownership of their inputs and outputs (V18 snippets); Anthropic's output terms were not re-checked for this note (Unv). Either way, ownership does not settle *how* the outputs may be collected.

### 5.3 Precedent

| Case | What it shows | What it does not show |
|---|---|---|
| Screen readers (VoiceOver and others) | AX reading of chat apps is normal, and Electron builds its tree for assistive technology (V6) | Not storage, not automation |
| OpenAI Computer History; Work with Apps; the Sky acquisition (V14–V16) | OpenAI itself reads other apps' text through Accessibility, at product scale, and stores the results | That OpenAI accepts a third party doing the same to ChatGPT |
| Anthropic computer use (V17) | Anthropic itself drives other Mac apps, waits while the user types, and asks per app | That Anthropic permits automating Claude Desktop |
| Screenpipe (V23) | A shipping third-party product reads all apps through Accessibility | No vendor statement either way |
| Rewind (V21) | A screen-memory product can vanish for business reasons; churn is real (SYNTHESIS §6) | Not a ToS enforcement case |
| Microsoft Recall (V22) | Capture-everything tools face strong security scrutiny; a plaintext store was the main failure | — |
| Memory extensions (Mem0, MemoryPlugin, Supermemory) [10 F10, F12] | Third-party chat capture has run in public without enforcement | Absence of evidence is not permission |

---

## 6. Layered strategy

**Layers.** Each layer adds to the one before it.
- **L0, sanctioned baseline:** zero ToS exposure.
- **L1:** L0 plus shadow capture.
- **L2:** L1 plus visible injection.
- **L3:** L2 plus automation.

**What the core does is the same in every layer.** It runs the Session Ledger, Steward, Drift Checker, Composer, Goal-Change Handler and compiler from SYNTHESIS §3.3 and §3.4. The layers differ in what goes in (capture fidelity) and what comes out (delivery).

**One turn, by layer.**

| Step | L0 | L1 | L2 | L3 |
|---|---|---|---|---|
| User sends a message | Unseen, unless the model passes an excerpt to a tool | Captured verbatim from the composer | As L1; the Northstar block is split out by exact match | As L2 |
| Reply streams and ends | Unseen; the model may pass a digest later | Captured verbatim when it ends | As L1 | As L1 |
| Session Ledger update (Steward, fast lane) | From model_reported events only; capture fidelity marked | From verbatim spans; every operation cites a span | As L1 | As L1 |
| Goal-Change Handler, then Drift Checker | On paraphrase; weak | On the verbatim reply, after display | As L1 | As L1 |
| Compose pin, card, correction | Yes | Yes | Yes | Yes |
| Deliver | Next tool result or MCP App context, if the model calls | As L0; badge to the user | Pre-armed block before the next user turn | As L2, plus an optional correction turn |
| Restart at a threshold | Suggested; on CD, prepared by deep link (cond. CD-S5; SPINE §4.10) | As L0 | Badge; start block pre-armed in the next new chat | Fresh chat prepared automatically, not sent (UQ-1) |
| Next chat's pack | Built from model_reported items; delivered if the model calls `northstar_context` (its first call returns the pack) | Built from verbatim items; delivered model-pulled | Built from verbatim items; start block (typed goals and constraints from part S, §4.4) pre-armed at chat start; AI-said and provisional items and the rest model-pulled | As L2 |

### 6.1 L0: the sanctioned baseline

On chat surfaces, the model decides when to call tools. L0 is designed to make the Northstar call the easiest, most rewarding thing for the model to do, and to make every call carry the focus anchor.

**Channels.**
- CD: the Northstar plugin (connector plus skill) with the local core reached through a local `.mcpb` server, so no public endpoint is needed (local now) [10 F4]; tools set to Always allow.
- GD: the Northstar plugin in the desktop app. Whether Chat mode can use local MCP servers from `~/.codex/config.toml`, or only remote plugins as on the web, is (Unv) (DS1). It is selected per chat (RISK 5).
- A boot line in static instructions (Claude profile preferences; ChatGPT custom instructions). The MCP `instructions` field repeats it within its first 512 characters [10 F6]. The drafts are CX §4.2 (Claude), CX §5.3 (ChatGPT) and CX §2.8 (`instructions`); each names `northstar_context`.

**Design moves.**
1. **One cheap tool.** `northstar_context` takes no required arguments. Optional ones are `session` (the turn tag), `user_message` and `prev_reply_points` (CX §2.3). The boot line asks for a call at the start of every reply; the description says only what the tool does (CX §2.1). A cheap call with no arguments to compose is more likely to be made (S3 measures it).
2. **Every result carries the anchor.** Every Northstar tool result, whatever the tool, ends with the current pin. Tool results sit after the user's message, near the end of the context [11 F3]. Even when the model stops calling, the last pin stays in the transcript.
3. **The result is the check.** The `northstar_context` result includes the Drift Checker's verdict on the previous reply. Without capture that verdict rests on the model's own `prev_reply_points`, which is weak.
4. **MCP App keep-alive.** The first call renders a small Northstar widget. It pushes the pin through `ui/update-model-context` and refreshes it from the core, using the supersession pattern so only the newest widget speaks (V13). If DS2 shows the context is re-sent on every turn, this becomes deterministic after the first call. Two limits: widgets lazy-mount when a stored chat is reopened, so the widget may be dormant, and whether a widget can reach a local core is (Unv).
5. **Skills and boot lines as boot.** On CD, the plugin's skill tells Claude when to call Northstar [10 F3]. On GD, custom instructions apply to every turn, but they are static.
6. **Drift-triggered re-anchoring.** When the checker flags a reply, the next tool result leads with the specific correction, not the generic pin. A correction that names the violation cut drift by 87%, against 35–38% for re-injecting instructions [11 F6].
7. **Restart by suggestion.** At a drift threshold, the tool result states that a fresh chat is ready. On CD, `northstar_restart` prepares the resume pack and a deep-link prefill (cond. CD-S5; CX §4.5). Elsewhere the C10 applier writes it to the pending-resume registry in session.db; C23 reads it when routing, and a new chat's first `northstar_context` call returns it when the call names its handle or routes to the same goals (CX §5.5). The user acts or ignores it.

**What L0 cannot do.** It has no verbatim AI-said capture live (GOAL §4.2). Its in-session levers work only on turns where the model calls a tool. On GD, per-chat plugin selection and per-conversation write approval are per-chat user actions (GOAL §4.3). And because neither MCP host passes a conversation ID (V13), the core cannot tell reliably which conversation a tool call came from. That weakens traceability "in which conversation" (GOAL §3.2).

### 6.2 L1: shadow capture

**Added:** verbatim capture of both sides, conversation identity, and audit truth.

**How the loop changes.**
- The Steward and Drift Checker now run on verbatim turns. The pin, card and checks no longer depend on the model describing itself.
- Delivery is still through L0 channels: tool results, MCP App context, boot lines. The optional overlay badge can show a drift flag **to the user**; it never reaches the model.
- **Reconciliation.** Each model-reported tool call is joined to the verbatim turn by the session tag when the model passes it, and otherwise by app, time window and text similarity. Both versions are kept: `model_reported` and `verbatim`, then `reconciled` (SYNTHESIS §3.1). The difference between them is itself a measure of how much the model's self-report drifts.
- **Cross-session pack.** The next chat's pack is built from verbatim AI-said passages, not the model's paraphrase. User-centric extraction lost 17.7% on questions about what the assistant said [14 F1][03], and that is the loss this layer avoids. Delivery at chat start is still model-pulled.
- **Human view.** Every passage links to its exact conversation and turn (GOAL §3.2, "in which conversation").
- **Measurement.** Shadow chats are the in-app baseline for GOAL §6 criterion 1.

### 6.3 L2: visible injection

**Added:** deterministic delivery.
- **Per turn:** the pin's user-typed lines are pre-armed before every user turn (§4.4). On triggers, a correction or a card's user-typed lines ride the same block; the rest of a card arrives through tool results or widget context (§4.4 content rule).
- **Corrections:** a flagged reply's specific correction is delivered on the very next turn, every time, not only when the model calls a tool.
- **Chat start:** when the user opens a new chat, a start block of at most 1,500 chars is pre-armed: AC's part S (AC §3.4, §8.5), never the full 1.5–3k-token pack. The goal router cannot see the first message before it is typed, so the start block carries the active goals and constraints the user typed. Recent provisional items are left out under the §4.4 content rule; they arrive with the first `northstar_context` call. Goal-routed knowledge follows in the turn-2 card, the first `northstar_context` call or `northstar_fetch`.
- **Restart without automation:** at a drift threshold, the badge suggests a fresh chat. As soon as the user opens one, a start block (≤ 1,500 chars, with the resume handle) is pre-armed; the full resume pack arrives by that handle on the first `northstar_context` call. This is AD12's "one ignorable suggestion" made nearly free.
- **Measurement:** random injection per new chat, against shadow chats (protocol C), only after the user's yes to SPINE UQ-9, with its share and stop rule.

### 6.4 L3: automation

**Added:** automatic consolidate-and-restart (§4.5), an optional correction turn, and the optional paired-branch probe.

### 6.5 Expected effect

The effect sizes come from API and simulated-user studies, not from desktop chat apps. They show direction and rough size only, and the S8 pilot must size them here.

| Lever | Evidence | L0 | L1 | L2 | L3 |
|---|---|---|---|---|---|
| Per-turn pin | RECAP recovered 44–52% of the multi-turn loss; SNOWBALL 18–31% [11 F6] | Scaled by p_call, the share of turns where the model calls Northstar (unknown, S3; practitioner reports say calls are skipped [10 F15]) | p_call, with better content | About the full lever, less turns where the user deletes the block | As L2 |
| Specific correction | −87% drift, against −35–38% for generic re-injection [11 F6] | Weak: the check sees only a digest | Detection strong; delivery scaled by p_call | Delivered on the next turn, every time | Plus an immediate correction turn (opt-in) |
| Constraints held outside compaction | 0% violations when pinned outside compacted text, against 30–59% after compaction [11 F5] | Static instructions only, which decay [11 F3] | As L0 | Re-added every turn, so the latest copy is always fresh | As L2 |
| Consolidate and restart | CONCAT kept 95.1% of single-turn performance [11 F1] | Model suggests; user acts | As L0, with a better pack | Start block pre-armed when the user opens a chat; the pack follows on the first call | Automatic |
| Cross-session pack | 2K tokens beat 32K; about 300 relevant tokens beat about 113K [14 F12] | Model-pulled; content from paraphrase | Model-pulled; content from verbatim | Typed goals and constraints deterministic at chat start; AI-said and provisional items model-pulled (§4.4) | As L2 |
| Self-report bias | Models miss 64.5% of their own errors [13 F1] | Capture depends on self-report | Removed for capture | Removed | Removed |

---

## 7. Gain per GOAL requirement

### 7.1 Claude Desktop chat (CD)

| GOAL requirement | L0 | L1 | L2 | L3 |
|---|---|---|---|---|
| §3.1 capture user-said | PARTIAL: paraphrase when the model calls a tool | **Met**: verbatim, by construction | Met | Met |
| §4.2 AI-said first-class, verbatim | **Not met live**; exports are backfill only | **Met** after each reply | Met | Met |
| §3.3 in-session focus, per turn | PARTIAL: model-pulled; MCP App deterministic only if DS2 | PARTIAL, better content | **Met**, visible, unless the user deletes it | Met |
| §3.3 check and correct drift | Weak, on paraphrase | Check met after display; correction model-pulled | Check after display; correction on the next turn | Plus an optional correction turn. Pre-display correction never (RISK 20) |
| §3.3 consolidate and restart | Prepared, one keystroke (cond. CD-S5), else suggestion (SPINE §4.10) | Prepared | Prepared: start block pre-armed in the fresh chat | **Prepared automatically**: the module opens and fills a fresh chat; sent only if UQ-1 allows |
| §3.3 cross-session start | PARTIAL: model-dependent | PARTIAL, better pack | **Met** for the user's typed goals and constraints: deterministic. AI-said and provisional items model-pulled (§4.4 content rule) | As L2 |
| §3.2 traceable to the conversation | Weak: no conversation ID | **Met** | Met | Met |
| §4.3 no per-chat user action | PARTIAL: connector toggle and approvals per chat (default-on Unv) | As L0 for tools; capture needs none | Met | Met |
| §4.7 independent audit truth | Exports only | **Met**: composer vs transcript; sweeps; reconciliation | Met | Met |
| §6 drift measured against the same chat without Northstar | API replay only | In-app shadow baseline (different chats) | Randomized arms in-app | Plus the paired-branch probe per sampled turn. Whole-chat same-chat comparison never (RISK 21) |

### 7.2 ChatGPT desktop chat (GD)

As CD, with these differences.

| GOAL requirement | Difference from CD |
|---|---|
| All rows at L0 | Worse. The plugin is picked per chat, writes are re-approved per conversation, and plan eligibility conflicts (RISK 5). If DS1 shows Codex hooks fire in Chat mode, L0 becomes deterministic on every row, and the module is not needed for GD |
| §4.3 at L1–L3 | With capture, the plugin can be read-only. Writes then go through the module, which removes the per-conversation write approval (AD17) |
| ToS exposure | Higher: OpenAI's clause names programmatic extraction of Output (§5.2) |
| ChatGPT Classic (GC) | Native AX profile. List virtualisation is likelier in native lists (Unv). Lower priority: the merged app is the primary target |

---

## 8. Capability summary rows

Levels: **det/verb** = deterministic and verbatim; **det** = deterministic; **m_pull** = model_pulled; **m_rep** = model_reported; **static**; **aft** = after_the_fact; **none**. "(DS2)" means deterministic only if spike DS2 succeeds. SPINE §4.10 gives the same rows in the spine's levels; the map at the top of this note translates them. The **restart** column uses SPINE's own restart levels (`suggested`, `prepared`, `automatic`, `reseed_on_reset`) and follows SPINE §4.10. At L2 and L3, "det (visible)" covers only what the §4.4 content rule lets a block carry (typed goals and constraints, pending corrections); AI-said, provisional and reported items stay m_pull.

**Claude Desktop chat (CD)**

| Layer | capture_user | capture_ai | inject_turn | inject_start | check_reply | restart | audit_truth | write |
|---|---|---|---|---|---|---|---|---|
| L0 | m_rep | m_rep | m_pull + static (det after first call, DS2) | m_pull + static | aft on m_rep | prepared, one keystroke (cond. CD-S5), else suggested | aft (export backfill) | m_pull |
| L1 | det/verb | det/verb (post-reply) | m_pull + static (DS2) | m_pull + static | aft (det check), m_pull delivery | prepared | det | det |
| L2 | det/verb | det/verb | det (visible) | det (visible) | aft, det delivery next turn | prepared (start block pre-armed; the user sends) | det | det |
| L3 | det/verb | det/verb | det | det | aft, det delivery + optional correction turn | prepared (the module opens and fills a fresh chat; the user sends); automatic only if UQ-1 allows auto-send | det | det |

**ChatGPT desktop chat (GD)**

| Layer | capture_user | capture_ai | inject_turn | inject_start | check_reply | restart | audit_truth | write |
|---|---|---|---|---|---|---|---|---|
| L0 | m_rep (after per-chat selection) | m_rep | m_pull (Extensions context, DS2) + static | static + m_pull | aft on m_rep | suggested; prepared, one tap, at L0+ (cond. CS4) | aft (export, up to 7 days) | m_pull, per-conversation approval |
| L0 if DS1 succeeds | det/verb | det/verb | det | det | det before display (`Stop`) | reseed_on_reset (`SessionStart`) | det | det |
| L1 | det/verb | det/verb | m_pull + static | static + m_pull | aft, m_pull delivery | automatic at reply end only if UQ-1 allows (cond. CS4), else as L0 | det | det |
| L2 | det/verb | det/verb | det (visible) | det (visible) | aft, det delivery next turn | prepared (start block pre-armed; the user sends) | det | det |
| L3 | det/verb | det/verb | det | det | aft + optional correction turn | prepared with the pending draft carried over (the user sends); automatic only if UQ-1 allows auto-send | det | det |

---

## 9. Honest residue

What stays unmet on CD and GD, by layer. Each item is a risk for the user. None is designed away, and no other surface is offered in place of these.

**Under every layer**
- No correction before the user sees the reply. Replies stream to the screen before any check (RISK 20).
- No hidden injection. The block is visible, stays in the vendor transcript, and may enter vendor memory (RISK 11).
- No whole-chat, same-chat comparison inside the app (RISK 21).
- No control over vendor compaction (claude.ai compacts on paid plans with code execution; ChatGPT's handling is undocumented) [11 F8]. Northstar's state lives outside the transcript and is re-placed, which is the mitigation.
- Branches the user never displays, attachment contents and collapsed reasoning are not captured.
- The module is macOS only. Chats on phones and the web are captured only when later opened in a desktop app on this Mac, within what the app holds.

**L0 only (module declined)**
- GOAL §4.2 is **not met live** on CD or GD. AI-said text arrives verbatim only through exports the user triggers again and again, which is a ritual, so it counts as backfill only (RISK 19).
- GOAL §4.5 in-session focus is **model-dependent** on both. The model's choice to call a tool fades in the long chats that need it most [10 F15].
- GD also needs per-chat plugin selection and per-conversation write approval (GOAL §4.3), and is plan-gated (RISK 5).
- Traceability to the exact conversation is weak (V13).

**L1**
- Delivery of focus state is still model-pulled, so in-session focus stays PARTIAL.
- ToS-grey, breaks on UI updates, costs CPU, needs a TCC grant, which management may restrict on an employer-managed Mac.

**L2**
- Higher ToS exposure. The block clutters the transcript the user reads and shares. It can collide with the user's typing, although the governor avoids that by design. It uses message length and quota.

**L3**
- Highest ToS exposure. The module acts inside the user's app. A restart breaks the thread, although the old chat stays open. An auto-sent pack or correction turn uses quota and speaks for the user.

**Adjacent modes, described only as additional options.** Claude Cowork and the Claude Desktop Code tab, and ChatGPT Work and Codex threads, have hooks and meet these rows deterministically [10 F5, F9]. They are not replacements for the chat surfaces. Offering one in place of chat would be a reframe, so it is a question for the user (D-Q5).

---

## 10. Risks

New risk IDs for this module (DR), mapped to SYNTHESIS risks.

| # | Risk | Threatens | Mitigation | SYNTHESIS |
|---|---|---|---|---|
| DR1 | Declining the module leaves CD and GD without live verbatim AI-said capture and with model-dependent focus | §4.2, §4.5, §4.6 | L0 design moves (§6.1); DS1 and DS2 may close part of it sanctioned; reported to the user, not designed away | RISK 4, 19 |
| DR2 | ToS exposure: OpenAI's extraction clause; Anthropic's automated-means and scraping clauses. Account action is possible, though none has been seen against similar tools | Account access; the module's existence | Separate sub-modules; read-only by default; no internal APIs or credentials; personal accounts only; the user decides (D-Q1) | RISK 1 analogue |
| DR3 | App updates break profiles silently, and each fix needs developer work (a code change and a release) after a vendor UI change. Expected cadence (Unv): every few weeks while both apps ship frequent UI releases; DS11 measures it | §4.7, §4.2; §6 "maintains itself without babysitting" | Self-test; fail closed to shadow, so the connector degrades to L0 with no user action; watermarks; alarm within one day; the user is never asked to act; an AI coding agent can make the fix from the failing self-test record | [10] R6; SPINE RISK 36 |
| DR4 | Employer-managed Mac (if this Mac is one): policy may forbid the helper; a security agent, if present, may flag it; management may deny the grant later | §4.6 | Ask first (D-Q2); install-time checks (V27); DS8; nothing is installed until the user confirms | RISK 2 |
| DR5 | macOS 27 changes Accessibility consent | Module availability | DS8 on macOS 27; the module degrades to L0 cleanly | — |
| DR6 | The observer is a high-value target and sees secrets | Privacy, trust | §4.8 | RISK 9, 13 |
| DR7 | Visible blocks pollute transcripts and vendor memory, and may feed a self-poisoning loop | §3.3 | Labelled blocks; small pins; S6; vendor-memory arms | RISK 11 |
| DR8 | Composer writes collide with the user's input or the editor's model | User trust | Empty-composer rule; typing guard; read-back; switch off on mismatch | — |
| DR9 | CPU and battery cost from the app's AX tree | User experience | Budgets; tree only while visible (Unv); DS4 | — |
| DR10 | Parser misattributes speaker | §4.2; misattribution 43–55% if a model sets speaker [12][13] | Speaker by construction from the composer; alternation invariants; transcript cross-check | RISK 10 |
| DR11 | Measured gains may be small: know-but-violate up to 99%; best levers recover 20–50% per turn | §6 criterion 1 | Specific corrections; restart; size early (S8); report honestly | RISK 3 |
| DR12 | Vendor churn: either app could change architecture again (as GD did on 2026-07-09) | Module lifetime | Profiles behind an interface; the core never depends on the module | SYNTHESIS §6 churn |

---

## 11. Decisions only the user can make

Each has a working assumption. It is used only for spikes and design drafts. Nothing ships on it, and silence is never taken as an answer.

**D-Q1. Accept the desktop fidelity module? (blocking for CD and GD fidelity; analogous to SYNTHESIS Q1)**
Will you accept a Northstar helper app that reads your Claude Desktop and ChatGPT desktop chats through macOS Accessibility, and optionally adds a visible Northstar block to the composer and prepares fresh chats? It is ToS-grey under both vendors' terms (§5) and breaks when the apps change.
- Choices: (a) no; (b) shadow capture only; (c) capture plus visible injection; (d) also automation.
- *If you decline (a), you lose this:*
  - **Both apps:** no live verbatim capture of what the AI said; exports you trigger by hand are backfill only. In-session focus works only when the model chooses to call Northstar. No automatic restart. Weak traceability to the exact conversation.
  - **ChatGPT:** also per-chat plugin selection and per-conversation write approval, unless DS1 shows hooks work in Chat mode.
  - These are reported as DR1 (RISKS 4 and 19), not designed away.
- *If you choose (b) only:* capture, audit and the next chat's pack become verbatim. In-session focus stays model-dependent.
- *Working assumption (pending user answer), as SPINE UQ-1, which supersedes this question:* (b) capture on allowlisted personal-account chats, with Temporary and incognito chats skipped. Visible injection (c) is used only where the sanctioned widget context fails its spike (CD-S2 / CS4). Automation stays off, except restart in prepared (not sent) mode. No auto-send and no correction turns. Shadow arms only after a yes to SPINE UQ-9. Until you answer, the module exists only as spikes on synthetic test chats in a test account.

**D-Q2. If this Mac is employer-managed, may the helper run on it? (blocking for install)**
On an employer-managed Mac (management enrolment, security agents, a TLS proxy), your employer's policy may forbid software that reads other apps, and a security agent may flag it. Whether an Accessibility grant is possible depends on your rights and the management profile. `northstar doctor` checks these at install and keeps the results in the data root, not the repo (V27).
- *Working assumption (pending user answer):* nothing is installed on this Mac until you confirm it is allowed. Sanctioned spikes (DS1, DS2, DS3) go first; they need no Accessibility grant.

**D-Q3. Which ChatGPT desktop app do you use for chat?** The merged ChatGPT app, or ChatGPT Classic?
- *Working assumption (pending user answer):* the merged app, the primary target. A Classic profile is built only if you use it.

**D-Q4. May the module send messages for you?** This covers auto-sending a resume pack and the optional correction turn. Both use quota and are the most ToS-exposed actions.
- *Working assumption (pending user answer):* no. The module prepares; you send.

**D-Q5. Adjacent modes as additional options.** Would you like Claude Cowork and the Code tab, and ChatGPT Work and Codex threads, offered as *additional* high-fidelity places to work? They are not replacements for Claude Desktop chat or ChatGPT desktop chat, which stay first connectors.
- *Working assumption (pending user answer):* they are supported anyway as hook connectors (Claude Code and Codex are first connectors), and nothing steers you away from the chat apps.

---

## 12. Spikes

Ordered by value. DS1–DS3 need no Accessibility grant and carry no ToS exposure.

| Spike | Question | Settles |
|---|---|---|
| DS1 | In the merged ChatGPT app, do Codex hooks (`UserPromptSubmit`, `Stop`, `SessionStart`) fire for **Chat**-mode threads? Can Chat mode use local MCP servers from `~/.codex/config.toml`? | V11; whether the module is needed for GD |
| DS2 | Does MCP App model context reach the model on **every** later turn on CD, and does OpenAI Extensions model context do so in GD Chat mode? Survival across reload and lazy mount; size limit; can a widget reach a local core? (SYNTHESIS S2) | V12, V13; L0 inject_turn |
| DS3 | Over 40 turns, how often does the model call `northstar_context` unprompted, with the cheap-tool design and boot lines, on CD and GD? (SYNTHESIS S3) | p_call in §6.5 |
| DS4 | On a synthetic test account, CD and GD: AX tree completeness (roles, URL, DOM ids and classes, code whitespace, maths, branches, end-of-reply signals, list virtualisation at 50, 200 and 500 messages); CPU and energy with the tree on and off | §4.3, §4.7 |
| DS5 | The same for ChatGPT Classic, if D-Q3 says it is used | GC profile |
| DS6 | Composer insertion: AX insert vs set value vs paste, in both editors; read-back; long-paste-to-attachment thresholds; draft persistence; behaviour with input methods | §4.4 |
| DS7 | Restart choreography: New chat by AX press, shortcut and deep link (`claude://`, `codex://`); pack and draft carry-over; failure recovery | §4.5 |
| DS8 | Managed Mac (if applicable): does a security agent flag the helper? Does a grant hold under management? Behaviour on macOS 27 | DR4, DR5 |
| DS9 | Are visible blocks absorbed into Claude or ChatGPT memory? (SYNTHESIS S6) | DR7 |
| DS10 | Reconciliation: session-tag echo rate; precision of the time-and-similarity join | §6.2 |
| DS11 | Breakage drill over 4 weeks of app updates: alarm latency and false alarms | DR3 |
| DS12 | On a synthetic account only: does Claude Desktop's Chromium cache hold conversation JSON on disk? (Security and excision only; not a capture path) | §2.2 |

---

## 13. Goal-fidelity check

| GOAL item | How this note handles it |
|---|---|
| §4.1 a system, no rituals | No layer needs a recurring user action. Exports are backfill only. OCR is excluded because its permission must be re-approved. The module is set up once, if accepted |
| §4.2 AI-said first-class | L1+ captures AI turns verbatim with speaker by construction. Under L0 the gap is reported (DR1), not hidden |
| §4.3 the AI manages it | Capture and delivery are automatic. Corrections stay optional. Per-chat actions on GD under L0 are stated as residue |
| §4.4 two architectures, one core | The module feeds the core's raw-event intake only. The human view gains exact conversation links; the AI side gains deterministic delivery |
| §4.5 drift and continuity equally | §6 designs both the in-session loop and the cross-session pack under every layer, with effect estimates |
| §4.6 product-agnostic core, connectors; CD and GD first | The module is an optional fidelity channel inside the CD and GD connectors. It never replaces the chat surface. Adjacent modes are a question (D-Q5) |
| §4.7 robust maintainer | No model in the module. Self-tests, fail-closed, watermarks, two independent captures of each user turn, reconciliation against model reports |
| §4.8 prototype built and evaluated | Shadow mode and randomized arms give in-app measurement. Spikes DS1–DS12 come before the build |
| §7 reframing needs the user | Nothing is reframed. Adjacent modes go to the user (D-Q5). The module itself is a user decision (D-Q1) |

**Where a requirement could be narrowed.** Only by a user answer: declining the module (D-Q1) leaves §4.2 and §4.5 PARTIAL on CD and GD (DR1); forbidding the helper on this Mac (D-Q2) has the same effect. Both are stated as risks.

---

## Sources

All checked on 2026-10-08.

**Local inspection (no conversation content read):** `/Applications/Claude.app` and `/Applications/ChatGPT.app` bundles, `Info.plist` files and Electron fuse wires; folder names under `~/Library/Application Support/Claude/`, `~/Library/Application Support/Codex/` and `~/.codex/`; SQLite table names, column names and enum values in `~/.codex/`. Environment checks (V27) now run locally at install through `northstar doctor`; their results stay in the data root, not the repo.

**Anthropic / Claude**
- Consumer Terms: https://www.anthropic.com/legal/consumer-terms
- MCP Apps instance supersession (model context "for the next turn"; lazy mount; no conversation ID): https://claude.com/docs/connectors/building/mcp-apps/instance-supersession
- Let Claude use your computer: https://support.claude.com/en/articles/14128542-let-claude-use-your-computer

**OpenAI / ChatGPT / Codex**
- Terms of Use (live page blocked by a Cloudflare challenge): https://openai.com/policies/terms-of-use/ ; archived 2024-12-11 copy: https://open.windriver.com/info/uni-license-list/licenses/openai-tou-20241211.html
- Desktop app: https://learn.chatgpt.com/docs/app
- Hooks: https://learn.chatgpt.com/docs/hooks
- Computer History: https://learn.chatgpt.com/docs/customization/computer-history
- MCP Extensions spec: https://github.com/openai/mcp-extensions/blob/main/docs/spec.md
- Work with Apps on macOS (snippets; page 403): https://help.openai.com/en/articles/10119604
- Desktop app release notes (page 403): https://help.openai.com/en/articles/9703738
- App merger and ChatGPT Classic: https://daringfireball.net/linked/2026/07/09/todays-the-day-openai-fucked-up-the-chatgpt-mac-app
- Sky acquisition: https://techcrunch.com/2025/10/23/openai-buys-sky-an-ai-interface-for-mac/
- 2024 plaintext storage and fix: https://www.ghacks.net/2024/07/08/chatgpts-macos-app-was-storing-chats-in-plain-text-but-it-has-been-patched/

**Electron and Apple**
- Electron accessibility: https://www.electronjs.org/docs/latest/tutorial/accessibility
- Electron `app` API: https://www.electronjs.org/docs/latest/api/app
- Apple PPPC payload: https://support.apple.com/guide/deployment/dep38df53c2a/web
- PPPC services and standard-user limits: https://support.kandji.io/support/solutions/articles/72000560493
- macOS 27 Accessibility change (forum): https://origin-devforums.apple.com/forums/thread/836770
- Screen Recording monthly prompts: https://tidbits.com/2024/08/19/apple-reduces-excessive-sequoia-permission-requests-shifts-to-monthly

**Precedent**
- Rewind and Limitless: https://9to5mac.com/2025/12/05/rewind-limitless-meta-acquisition/
- Microsoft Recall: https://www.techrepublic.com/article/news-microsoft-recall-expands-rollout/
- Screenpipe: https://screenpi.pe/blog/screenpipe-v2-03-accessibility-capture

**Prefill links (community, unverified)**
- https://www.vincentschmalbach.com/claude-chatgpt-bookmarklets/ ; https://u2l.ai/tools/claude-prompt-link-generator ; https://directory.getdrafts.com/a/25n

**Research notes:** [10], [11], [12], [13], [14] and SYNTHESIS in `docs/research/round2/`.

---

## Fidelity fixes (2026-10-08)

An independent goal-fidelity audit of the spine and the desktop connector docs found the issues below in this note. Each was fixed in place. No non-negotiable was weakened.

| # | Severity | Issue | What changed |
|---|---|---|---|
| 1 | Minor | Cloud-later (SPINE §7.5) had the observer sending over HTTPS, while §4.1 and §4.8 forbid it any network access | §4.1 adds the rule "no network, now or later": a local intake forwarder (SPINE §7.5) relays socket events to the cloud. §4.8 references it |
| 2 | Minor | Profile repair after vendor UI changes is a recurring developer dependency, not stated against GOAL §6 "maintains itself without babysitting" | §4.7 and DR3 now state that a fix is developer work (which an AI coding agent can do from the failing self-test record), the expected cadence (Unv, DS11), that the user is never asked to act, and that the connector falls back to L0 automatically (SPINE RISK 36) |
| 3 | Minor | This note used its own level words and layer names, and the tool name `northstar_turn` | A note at the top maps them to SPINE §4 and SPINE §1.4 (`northstar_turn` = `northstar_sync`; L2 = L2-inject; L3 = L2-auto) and says SPINE UQ-1 and UQ-9 govern where working assumptions differ. §8 points to it |
| 4 | Minor | The evaluation arm randomized Shadow against Inject 50/50 on real chats with no user question or stop rule (§4.2, §6.3) | Both now run only after the user's yes to SPINE UQ-9, with its share and stop rule |

**Questions for the user.** No new question was added here. The live arm is SPINE UQ-9; what the module may write or send is SPINE UQ-1.

---

## Consistency fixes (2026-10-08)

A cross-document review found these issues. Each fix adopts the listed resolution so this note agrees with the rest of the design set. No non-negotiable was weakened. The "Fidelity fixes" entry #3 above is kept as a record; its `northstar_sync` mapping is superseded by X01.

| ID | Change in this note |
|---|---|
| X01 | Tool names now follow the one MCP tool contract, CX §1.2 and §2. The top note carries the CX name map: `northstar_turn` / `northstar_sync` → `northstar_context`; `northstar_resume` → the first `northstar_context` call, or a restart pack by handle; `user_turn_excerpt` → `user_message`; `my_last_reply_digest` → `prev_reply_points`. §6 table, §6.1 moves 1, 3 and 7, and DS3 use the CX names. Move 1 now says the boot line, not the description, asks for the per-turn call (CX §2.1). §6.1 points to the CX boot-line and `instructions` drafts (CX §4.2, §5.3, §2.8) |
| X06 | §4.4 states the composer-block budgets: ≤ 600 chars per turn, ≤ 1,800 on triggers (IS §8.3), start block ≤ 1,500 chars as part S (AC §3.4). The full pack is never pre-armed. §6.3, §3.2, §6 and §6.5 no longer pre-arm the 1.5–3k-token pack; the rest arrives on the first `northstar_context` call. A restart deep-link prefill carries only the handle and one fixed line, ≤ 600 chars, no item text (§4.4 insertion table) |
| X14 | One turn-tag format, `NS-XXXXXX.<n>` (CX §2.3), in the §4.4 block header and join-key text (`NS-7F3K.14`). §4.3 points to the CX §6.1 wire form under `northstar.connector/1.1`, including `account.source: ax_label` |
| X26 | §4.8 cites the PL-3 gate when FileVault is off at install: the data root uses FileVault or an encrypted sparse bundle, and real capture waits for one of them. The secrets row now says: secrets redacted, PII tagged, masked at egress (SPINE C06; PL D-PL-4) |
| X28 | §0 item 11 and D-Q1 now state the SPINE UQ-1 working assumption: L1 read yes; L2-inject only where the widget spike fails (CD-S2 / CS4); restart prepared, never sent; no correction turns. The restart column of §8, and the §6 and §7.1 restart rows, follow SPINE §4.10 (Claude Desktop chat L0: prepared, cond. CD-S5, else suggested) |

---

## Review revisions (2026-10-08)

The adversarial review found the issues below in this note. Each was fixed in place. No non-negotiable was weakened and no part of the goal was re-scoped. The full review record is [`REVIEW.md`](../REVIEW.md).

| Finding | What changed here |
|---|---|
| SEC-6 (merged with CONS-6) | Device-specific security facts are gone; they became generic conditionals. §0 item 9 now says: if this Mac is employer-managed (management enrolment, security agents, a TLS proxy), policy may forbid the helper, a security agent may flag it, and a grant depends on the management profile. V27 is now an install-time check (`northstar doctor`) whose results stay in the data root. §0 item 1 says the merged ChatGPT and Codex app is the main ChatGPT desktop app. V16 drops the local group-container fact. The §2.2 GC row drops "not installed". §2.3 drops the proxy-vendor sentences. M15 says "a TLS-inspecting proxy, if one is present". §4.7 says a grant depends on the user's rights and any management profile, checked at install, and that a security agent, if present, may flag the helper. §4.8 "Store at rest" states the PL-3 gate (FileVault if on at install, else an encrypted sparse bundle) without the machine's state. D-Q2 is now conditional ("If this Mac is employer-managed…"). DS8 and DR4 are worded conditionally; §9 L1 likewise. §7.2 and D-Q3 say the merged app is the primary target. The X26 row records the PL-3 gate generically. Also under SEC-6: exact installed app, Electron and Chromium versions left V1, V3 and §0 item 1 (they are `northstar doctor` output), and the Sources list no longer names the local management checks |
| SEC smaller issue: observer peer check by PID is racy | §4.3 adds a peer check to the socket interface, and §4.8 adds a threat row. The core checks the observer on every message by its audit token (`LOCAL_PEERTOKEN`) plus a code-signing check against its Developer ID and bundle ID, never by PID. A failed check drops the message and raises an alarm |
| SEC smaller issue: L2-inject carries state with the user's voice's weight | §4.4 adds a content rule: a block carries only goals and constraints the user typed (verbatim-confirmed) and pending corrections, never AI-said, provisional or reported items, because the chat model and vendor memory read it as the user's own words. Those items stay first-class in the core and reach the model through labelled channels (tool results, widget context, the first `northstar_context` call, `northstar_fetch`). The example block, the block budgets, the §4.5 restart block (now a start block with the resume handle; the pack follows by handle), the §4.8 injection row, §0 item 4, §6 "Next chat's pack", §6.3, §6.5, §7.1 "cross-session start" and the §8 legend follow the rule. Whether blocks are used at all is DQ-1(c) / SPINE UQ-1 |
| CPLX-10 | §4.7: the self-test record is text-free. It holds Accessibility roles and hierarchy only, never text, so an AI coding agent can repair a profile without seeing personal content. The "Who fixes a broken profile" bullet points to it |
| CONS smaller issue (OBS §6.1 item 7) | §6.1 move 7 no longer says C23 holds the pending resume pack. The C10 applier writes it to the pending-resume registry in `session.db`; C23 reads it when routing (AC §4.3; CX §4.5) |

**Questions for the user.** No new question was added here. The content rule for visible blocks is part of DQ-1(c) (SPINE UQ-1); the employer question stays D-Q2.
