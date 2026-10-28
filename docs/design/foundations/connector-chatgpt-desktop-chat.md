# Connector design: ChatGPT Desktop chat

**Status: design draft, revised after adversarial review. Not approved. Nothing here is built.** Revised on 2026-10-08 after a goal-fidelity audit, a cross-document consistency pass and an adversarial review; see "Fidelity fixes (2026-10-08)", "Consistency fixes (2026-10-08)" and "Review revisions (2026-10-08)" at the end. The full review record is [`REVIEW.md`](../REVIEW.md).
Written 2026-10-08. [`docs/GOAL.md`](../../GOAL.md) overrides this document. Where this surface cannot meet part of the goal, the gap is stated as a **risk for the user** (§10). The goal is never narrowed here.

**The spine supersedes this document's contract and vocabulary (2026-10-08).** [`SPINE.md`](SPINE.md) §4 defines the one connector contract and its capability levels. They replace this document's "adapter contract" (§1.2) and level vocabulary (§1.4, §12). Where a working assumption here differs from the spine's user questions (SPINE §11.2), the spine governs: in particular UQ-1 (nothing is sent for you) and UQ-8(a) (what a chat adds to memory). Vocabulary map:

| This document | SPINE §4.2 |
|---|---|
| deterministic, verbatim (capture) | `verbatim_live` |
| verbatim (rendered) | `verbatim_rendered` |
| after_the_fact, for capture by export | `verbatim_deferred` |
| after_the_fact, for a reply check | `next_turn_verbatim` (observer) or `next_turn_reported` (self-report) |
| after_the_fact, for the audit | `deferred` |
| deterministic (injection) | `deterministic` |
| deterministic after mount | `deterministic_after_mount` |
| model_pulled, model_reported, static, none | same names |
| control channel, fidelity channel | per-capability `channel` attributes (`mcp_report`, `widget_context`, `ax_observer`, `export`) |
| `northstar_context`, `northstar_note`, `northstar_fetch` | same names in the one tool contract, CX §2 (see the tool-name map below); `prev_reply_points` = the envelope's `reported_points` |
| L2a, L2e / L2b, L2d | SPINE L2-inject / L2-auto (SPINE §1.4) |
| Packaging "Path A–D" (§6.2.1, earlier drafts) | **PK-1, PK-3, PK-4** (CX §1.2, §5.1). PK-1 and PK-2 were one route and are merged as PK-1 (REVIEW FEAS-2). The letters A, B, C1, C2 and W now mean only the write paths (§6.2.2; ARCH DQ-4(ii)) |

**The tool contract is CX §1.2 and §2** (CX = [`connectors-desktop-and-mcp.md`](../components/connectors-desktop-and-mcp.md), justified in its D1–D3; [CD] = `connector-claude-desktop-chat.md`; [OBS] = `desktop-observer-macos.md`). It replaces the tool names in SPINE §6.2 and TEXTBOOK. Tool-name map for this connector:

| Name used here or elsewhere | CX name (what this connector serves) |
|---|---|
| `northstar_context` (here); `northstar_resume`, `northstar_sync` (SPINE, [CD]); `northstar_turn` ([OBS]) | `northstar_context`. Its first call in a chat returns the start pack. `readOnlyHint` follows the manifest flags: `true` under `per_turn_readonly`, where the tool is stateless; `false` under `per_turn_write` (CX §2.5; §6.2.2) |
| `northstar_note` kinds `note`, `correction`, `decision`, `ai_point` (here); `northstar_correct` (SPINE, TEXTBOOK) | `northstar_note(kind: note \| decision \| goal \| question \| correction \| save_chat)`, with an optional `speaker`. Model-reported AI points persist through the capture path (§6.2.2), not through a separate kind |
| `northstar_fetch` | same |
| `northstar_page`, `_learned`, `_to_learn`, `_changes`, `_toc` (SPINE, TEXTBOOK) | `northstar_book(view: …)` |
| App-only "widget heartbeat, latest pin" (here) | `northstar_widget_state` |
| App-only "user correction", "restart pack" (here); `northstar_apply_correction` (TEXTBOOK) | `northstar_widget_action(action: apply_correction \| confirm_goal \| reject_goal \| hide_item \| restart \| dismiss_card)`. A click is bound to the user by a single-use **`action_nonce`** (CX §3.5), the one name for the click credential |
| `northstar_widget_record` | same name; a declared write. Input: the widget's own call's arguments, read from tool-input; no receipt token (REVIEW FEAS-1; supersedes CX §2.4, D6). Path C2 only |
| `northstar_restart` | Not in this connector's profile: ChatGPT Desktop chat sees four tools, `northstar_context`, `northstar_note`, `northstar_fetch`, `northstar_book` (CX §2.2). Restart is offered in results and, at L0+, by the widget's **Fresh chat** button (§6.2.6) |

**Scope.** The **Chat** mode of the ChatGPT macOS desktop app, on a **personal Plus or Pro** account. This is one of the four first connectors (GOAL §4.6). GOAL now treats this surface's gaps as first-priority problems (GOAL §2, answers of 2026-10-08).

**Out of scope here, designed elsewhere.**
- The **macOS observer module** (Accessibility capture and input) is designed in depth by a separate agent. This document names it as a layer and states only what this connector needs from it (§6.4, §6.5).
- The shared core, the maintainer, the human view and the other connectors.

**Evidence.** Round-2 notes [10] integration surfaces, [11] in-session drift, [13] robust maintenance, [14] memory-layer landscape, and the round-2 synthesis (cited as SYNTHESIS §n). Round-1 notes are used only through those. `docs/archive/` is not used.

**Conventions.**
- "(Unv)" marks a product fact I could not confirm from a primary source today. Each one names the spike that settles it (§13).
- Product facts carry an ID such as (V4). §3 gives the URL and the date checked for each.
- IDs used in this document: V = verified fact, CS = spike, CR = risk, CQ = decision for the user, PK = packaging route (§6.2.1).

---

## 0. Summary

1. **The sanctioned channels on this surface are remote and model-pulled.** Local MCP servers and Codex hooks are documented for Work and Codex threads in the desktop app, not for Chat (V5, V6, V7). OpenAI's own local plugin, Apple Messages, "doesn't work in regular ChatGPT chats" (V5). Treat local MCP and hooks in Chat as absent until spikes CS2 and CS3 say otherwise.
2. **Official plan eligibility got worse since [10].** OpenAI's help center (updated 2026-10-07) says developer mode and full MCP are for Business and Enterprise/Edu on the web. Pro gets read/fetch MCP. Plus is not listed (V1). A community report from 2026-09-28 says a personal Pro account could create and use a custom MCP app (V2). Official sources also conflict: OpenAI's developer guide says custom servers support read and write tools and are saved as personal plugins, with no plan gate (V3). Spike CS1 decides which route this account has, on day 1 of Stage 0 (§13).
3. **The biggest sanctioned lever is OpenAI's MCP Extensions.** A widget can put hidden context in the model's view (`ui/update-model-context` with audience `["assistant"]`) and can open a new conversation with content (`ui/message` with `target: "new"`) (V11). If these work in desktop Chat (CS4), Northstar needs **one early tool call per chat**, not one per turn. After that, pin delivery is deterministic and restart is one tap. This turns the hardest problem on this surface ("the model must call every turn") into an easier one ("the model must call once, at the start, when it drifts least").
4. **Design for a surface where the model decides when to call.**
   - One cheap per-turn tool (`northstar_context`) whose result is useful to the model and that never prompts in each chat: truthfully read-only and stateless where approvals recur, a declared write only under a one-time permission (path C1, §6.2.2). Path W, a declared write with a recurring approval, is offered only as the user's choice (ARCH DQ-4(ii)).
   - Every Northstar result carries the focus anchor.
   - Boot lines in four places: custom instructions, project instructions, the plugin's skill, and the MCP `instructions` field.
   - A widget that keeps context alive after the first call.
5. **Model-reported capture is evidence, never the record.** The model copies the user's message and quotes key points of its own previous reply. Northstar reconciles this against verbatim text when it arrives (Accessibility capture or export) and measures the gap (§7).
6. **Optional higher-fidelity layers are ToS-grey and need the user's decision.**
   - **L1, Accessibility read:** near-real-time verbatim capture of both sides, an independent audit truth, and real per-reply drift checks.
   - **L2, Accessibility write:** deterministic visible injection and a prepared consolidate-and-restart with the pending message carried over. Under SPINE UQ-1, nothing is sent for the user unless the user allows it.
   - **L3, internal data paths:** internal endpoints, local app storage, debugger attach. Not recommended.
7. **What stays unmet.** On every layer, a drifted reply cannot be corrected before the user sees it. On the sanctioned layers alone, AI-said capture is not verbatim and there is no live audit truth. On a Plus plan, the sanctioned MCP path may not exist at all. These are stated as risks (§10).
8. **Decisions only the user can make** are CQ1–CQ8 (§11). Each has a working assumption, marked "pending user answer". CQ5 and CQ8 are asked as ARCH DQ-4(iii) and DQ-4(ii).

---

## 1. Surface, layers and vocabulary

### 1.1 The surface

| Item | Fact | Source |
|---|---|---|
| App | The new ChatGPT desktop app has **Chat** and **Work** under ChatGPT, plus **Codex**. The previous native app is now **ChatGPT Classic** | V9 |
| What Chat is | "Chat is for fast, conversational assistance and everyday questions." Work is an agent for longer tasks. Work and Codex models are "not available in regular ChatGPT conversations" | V8 |
| Where Chat conversations live | "Chats created in Chat sync between ChatGPT web and the desktop app." They are server-side conversations, the same as chatgpt.com | V8 |
| Desktop app | The ChatGPT desktop app is an Electron app; the merged app hosts Codex | Product fact, checked 2026-10-08 (V9) |
| Classic variant | ChatGPT Classic still gets model updates and fixes, but "new agent features may be available only in the new app" | V9 |

This design targets **Chat mode in the new app**. If the user mainly uses ChatGPT Classic, L0 may not be available there at all (Unv, CS1), and only L1 and L2 would apply. That is CQ7.

### 1.2 Adapter contract

*Superseded by SPINE §4 (see the note at the top). The two-channel wording below is kept as this document's own reasoning; the contract is the spine's capability vector.*

Every connector has a **control channel** (the model can pull and record) and a **fidelity channel** (both sides observed verbatim, context injected deterministically). Either may be missing on a given turn, and the core records which were present [10 impl. 1; SYNTHESIS §3.6].

On this surface:
- the control channel is a **remote MCP plugin** (L0);
- the fidelity channel is **missing** in the sanctioned set. It exists only through the macOS observer (L1, L2) or internal data paths (L3).

### 1.3 Layers

| Layer | What it is | ToS position |
|---|---|---|
| **L0** | Sanctioned baseline: Northstar ChatGPT plugin (skill + remote MCP tools + focus widget), boot lines, one-off export backfill | Sanctioned |
| **L0+** | Sanctioned upgrades that depend on unverified product behaviour: Extensions hidden context and new-thread messages in Chat (CS4), local MCP in Chat (CS2), hooks in Chat (CS3) | Sanctioned |
| **L1** | macOS observer, **read only**: Accessibility reading of the ChatGPT window | Grey: "programmatically extract … Output" (V17) |
| **L2** | macOS observer, **write**: Accessibility input into the composer, new-chat creation, optional settings edits | Grey-light: automation of the user's own UI; no clause names it (V17) |
| **L3** | Internal data paths: internal web endpoints, local app storage, Electron debugger attach | Grey to prohibited; not recommended |

### 1.4 Level vocabulary (used in §4 and §12)

| Level | Meaning |
|---|---|
| **deterministic** | Happens whatever the model does |
| **deterministic after mount** | Deterministic once a Northstar widget is mounted, which needs one model tool call first |
| **verbatim** | The exact text. `verbatim (rendered)` means the text as displayed, read through Accessibility; formatting may differ from the server copy |
| **model_pulled** | Happens only if the model decides to call a Northstar tool |
| **model_reported** | The model copies or summarizes content into tool arguments. It is AI-said *about* the conversation [10 impl. 2] |
| **static** | Fixed text the system cannot update per turn |
| **after_the_fact** | Arrives after the reply was shown: minutes (L1), or days (export) |
| **none** | No mechanism |

---

## 2. What GOAL needs from this connector

| GOAL requirement | What this connector must provide |
|---|---|
| §3.1, §4.2: capture both sides, AI-said first-class, attributed | User turns and AI turns, verbatim where possible, with speaker set by code and capture fidelity recorded (SYNTHESIS §3.1, AD6) |
| §3.3, §4.5: in-session focus | A per-turn pin, a card on triggers, specific corrections, and consolidate-and-restart (SYNTHESIS §3.3, AD11, AD12) |
| §3.3, §4.5: cross-session continuity | The core pack at chat start, including the knowledge slot (SYNTHESIS §3.4, AD13) |
| §4.1, §4.3: no rituals; AI manages it | No per-chat user action required. Any one-time setup is acceptable. Optional actions must never be required |
| §4.6: product-agnostic core with connectors | The connector speaks the core's adapter contract only. Nothing ChatGPT-specific enters the core except surface metadata |
| §4.7: robust maintainer | Independent ground truth for capture, watermarks, and detection of silent capture loss. The chat model is never the maintainer (SYNTHESIS AD9) |
| §6: measured drift reduction and continuity | A control arm on this surface, and capture good enough to score it |

---

## 3. Verified product facts (checked 2026-10-08)

Only facts that were unverified in [10] or are decision-critical were checked. All dates are the date I checked them.

**Access notes.**
- `help.openai.com` returned HTTP 403 to the WebFetch tool. The same pages returned HTTP 200 to `curl` with a browser user agent. No proxy block page appeared, so the 403 is the site's bot protection, not a proxy.
- `developers.openai.com/api/docs/guides/developer-mode` now returns **HTTP 404**. A search snippet of the older copy listed "Plus, Pro, Business, Enterprise, and Education" on the web. That page has been removed or moved.

| ID | Fact | Source | Checked | Status |
|---|---|---|---|---|
| V1 | "Apps, full MCP support, and developer mode are available for ChatGPT Business and Enterprise/Edu customers on ChatGPT web." "Are MCP apps available on mobile? No - web only." "Can I connect to a local MCP server? Not directly … use Secure MCP Tunnel." "Pro users can connect MCPs with read/fetch permissions in developer mode." Plus is not mentioned. In workspaces, "App selection applies to the message where you use it, not the entire conversation." Page "Updated: yesterday" | https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt | 2026-10-08 | Verified (official), but conflicts with V3 (official) and V2 (community). CS1 decides |
| V2 | A personal Pro account "can create and use a remote OAuth MCP through https://chatgpt.com/plugins → + → Create MCP App". Teammates' personal accounts needed the Developer mode toggle at chatgpt.com/settings/security. An automated Support reply said "personal Plus/Pro users should have Developer Mode". No OpenAI staff reply. Desktop app not tested. Posted 2026-09-28 | https://community.openai.com/t/create-mcp-app-missing-from-plugins-menu-on-personal-chatgpt-accounts/1401436 | 2026-10-08 | Community report (secondary) |
| V3 | Custom MCP server guide: `readOnlyHint` is respected; tools without it are writes; writes need confirmation by default; the choice can be remembered "for a given tool for a conversation"; "New conversations will prompt for confirmation again". Keep the first 512 characters of MCP `instructions` self-contained. Says "Use ChatGPT on the web"; select the plugin with `@`. Re-checked in review: a custom server is added through Plugins → + → Add custom MCP server → Create as a plugin; custom servers support read and write tools in personal plugins, with no plan gate stated; a remembered approval is asked again after a reload or reopen | https://developers.openai.com/api/docs/guides/custom-mcp-server | 2026-10-08 | Verified; conflicts with V1 on plans |
| V4 | Plugins help: "ChatGPT automatically uses your installed plugins when they're relevant to your request. You can also select a plugin directly with an @ mention". "Your plugin can include local MCP apps that run on your computer, and you can run the plugin on ChatGPT Desktop." Saving it "does not make those tools available on web or mobile". "You can create a plugin with an app hosted on ChatGPT Sites on any ChatGPT plan." Personal skills are generally for Business and Enterprise/Edu (re-checked in review). Page "Updated: 2 days ago" | https://help.openai.com/en/articles/20001256-plugins-in-chatgpt-and-codex | 2026-10-08 | Verified |
| V5 | "Plugins work in Chat and Work across ChatGPT on the web, desktop, and mobile". The local Apple Messages plugin works "In Codex and ChatGPT Work … it doesn't work in regular ChatGPT chats." "When a plugin capability runs through a Codex host, the host's sandbox and approval policy applies." "Bundled skills become available when you start a new chat" | https://learn.chatgpt.com/docs/plugins.md | 2026-10-08 | Verified |
| V6 | "The ChatGPT desktop app, Codex CLI, and IDE extension support MCP servers and share MCP configuration for the same Codex host" (Settings → MCP servers; `~/.codex/config.toml`). "ChatGPT web can use remote MCP-backed tools supplied by plugins." Hooks "continue to work in local-only Work and Codex threads". Chat mode is not mentioned | https://learn.chatgpt.com/docs/extend/mcp.md | 2026-10-08 | Verified; Chat mode (Unv) |
| V7 | Codex hooks: `UserPromptSubmit` `additionalContext` "is added as extra developer context"; `Stop` gets `last_assistant_message`, and `decision: "block"` makes Codex continue; `SessionStart` matchers `startup`, `resume`, `clear`, `compact`; model-visible hook output is limited to "roughly 2,500 tokens" by default; hooks must be trusted by hash. No mention of ChatGPT Chat | https://learn.chatgpt.com/docs/hooks | 2026-10-08 | Verified; Chat mode (Unv) |
| V8 | "Chats created in Chat sync between ChatGPT web and the desktop app." Local Work chats run on the computer, but "Messages and task context may be stored in the cloud". Work and Codex models "are not available in regular ChatGPT conversations" | https://help.openai.com/en/articles/20001275-chatgpt-work-and-codex | 2026-10-08 | Verified |
| V9 | The new app has Chat, Work and Codex. The previous app is "ChatGPT Classic"; "New agent features may be available only in the new app." Renamed on Jul 9, 2026 | https://help.openai.com/en/articles/20001276-moving-to-the-new-chatgpt-desktop-app ; https://help.openai.com/en/articles/9703738-chatgpt-macos-app-release-notes | 2026-10-08 | Verified |
| V10 | Classic app release note, Feb 13, 2026: "Phased out certificate pinning exceptions." Aug 2024: "Enhanced security for local data storage" | https://help.openai.com/en/articles/9703738-chatgpt-macos-app-release-notes | 2026-10-08 | Verified |
| V11 | MCP Extensions spec: for use across "ChatGPT Work, ChatGPT Desktop, and ChatGPT mobile apps"; "Web refers to the Work browser; classic ChatGPT is excluded." `ui/update-model-context`: "Each call replaces the model context previously supplied by the same MCP App instance"; blocks with `annotations.audience: ["assistant"]` "are hidden from the user"; "All model context is sent to the model regardless of audience"; apps get their context back in `hostContext["openai/modelContext"]` "on initialization or remount". `ui/message`: `target` is `"active"` or `"new"` ("Request sending a message to a new conversation"); `send` defaults to `true`; titled text "becomes a labeled inline item that can be removed as a single unit"; apps are not notified when it is removed. Thread entrypoints: users "manually open an MCP App as a new content tab within a thread"; "Every thread will have a different instance". **Not specified:** whether context is sent on every turn, persistence, size limits, and whether desktop **Chat** mode is covered | https://github.com/openai/mcp-extensions/blob/main/docs/spec.md | 2026-10-08 | Verified; Chat-mode coverage (Unv) |
| V12 | Extensions page: thread entrypoint via `{ type: "thread" }`; "Composer mentions are available only in the ChatGPT desktop app"; "Plugin extensions on the web are coming soon to ChatGPT Free and Go users" | https://developers.openai.com/plugins/build/extensions | 2026-10-08 | Verified |
| V13 | Apps SDK state: `modelContent` is "Text or JSON the model should see"; `privateContent` is UI-only; widget state "belongs to one rendered UI instance"; `ui/update-model-context` is "the portable MCP Apps mechanism for updating model-visible context". No persistence or timing rules stated | https://developers.openai.com/apps-sdk/build/state-management | 2026-10-08 | Verified; timing (Unv) |
| V14 | Apps SDK reference: tool calls carry `_meta["openai/session"]`, an "Anonymized conversation id for correlating tool calls within the same ChatGPT session". `toolOutput`: "the model reads them verbatim". `readOnlyHint` is required; it signals that the tool "only retrieves or computes information", and hints "only influence how ChatGPT or Codex frames the tool call". `_meta.ui.visibility` defaults to `["model", "app"]`. Widgets can `callTool` and `sendFollowUpMessage` | https://developers.openai.com/apps-sdk/reference | 2026-10-08 | Verified |
| V15 | App permissions for personal accounts: Always ask, Allow read actions, Allow low-risk actions, Allow all actions. "Always allow: When offered for an eligible, explicitly connected personal account, allow supported future actions without repeated prompts" | https://help.openai.com/en/articles/20001495-managing-app-permissions-in-chatgpt | 2026-10-08 | Verified; applies to custom Northstar app (Unv; CS1 tests no-auth against OAuth) |
| V16 | Computer History uses "text and other context available through macOS accessibility features"; "It does not include screenshots"; no Screen Recording permission; "off by default for ChatGPT Pro, Business, and Enterprise users in the ChatGPT desktop app on macOS"; events deleted after 48 hours; memories are plain Markdown under `~/.codex/memories/extensions/skysight/`, "not encrypted" | https://learn.chatgpt.com/docs/customization/computer-history | 2026-10-08 | Verified |
| V17 | OpenAI Terms of Use, effective January 1, 2026. You may not: "Automatically or programmatically extract data or Output"; "Modify, copy, lease, sell or distribute any of our Services"; "reverse engineer, decompile or discover the source code or underlying components"; "bypass any protective measures". Also: you "own the Output". No clause about "automated means" of access was found | https://openai.com/policies/terms-of-use/ | 2026-10-08 | Verified |
| V18 | Export: available for Free, Go, Plus, Pro; "Exports can take up to 7 days to arrive"; the link "expires 24 hours after you receive it" | https://help.openai.com/en/articles/7260999-exporting-your-chatgpt-history-and-data | 2026-10-08 | Verified |
| V19 | Memory: "Improved Memory continually updates a broader summary"; sources include past chats, saved memories, **custom instructions**, files and connected apps; "Don't mention this again … does not delete the original source"; a Temporary chat can choose whether it uses "memories, custom instructions, and plugins" and does not create memories | https://help.openai.com/en/articles/8590148-memory-faq | 2026-10-08 | Verified |
| V20 | Custom instructions are "applied immediately across all chats (including existing conversations)", on all plans, on Web and Desktop. "the model may provide plug-in developers with relevant information from your instructions" | https://help.openai.com/en/articles/8096356-chatgpt-custom-instructions | 2026-10-08 | Verified |
| V21 | Projects: project instructions "override your global custom instructions"; inside projects, custom instructions are "Not available (only project instructions)"; "Apps in projects are available on ChatGPT Free, Go, Plus, Pro, …"; project-only memory exists | https://help.openai.com/en/articles/10169521-projects-in-chatgpt | 2026-10-08 | Verified |
| V22 | Custom GPTs retire Dec 11, 2026. GPT instructions become a skill. "ChatGPT may also use a relevant installed skill automatically when its description matches your request … the plugin will not necessarily run on every request" | https://help.openai.com/en/articles/20001519-custom-gpt-retirement-and-migration-faq | 2026-10-08 | Verified |
| V23 | Secure MCP Tunnel: needs Platform-organization Tunnels permissions; personal accounts use "the personal Platform organization that belongs to that account"; `tunnel-client` makes outbound HTTPS to `api.openai.com:443` and needs no inbound access; serves stdio or HTTP servers; added in ChatGPT through Plugins → Add custom MCP server → Tunnel → Create as a plugin; the authorization server is not tunneled automatically (re-checked in review); "does not support public plugin submission". No plan list | https://developers.openai.com/api/docs/guides/secure-mcp-tunnels | 2026-10-08 | Verified; personal Plus/Pro use (Unv) |
| V24 | ChatGPT Sites: public beta for workspaces, Plus and Pro; created in Work (web) or Work/Codex (desktop). "Hosting a plugin is available to all plans": a Site can host an MCP server whose tools become a plugin | https://help.openai.com/en/articles/20001339-creating-and-managing-chatgpt-sites ; https://help.openai.com/en/articles/20001547-hosting-a-plugin-with-chatgpt-sites | 2026-10-08 | Verified; Site → external MCP for personal plans (Unv) |
| V25 | Electron: "third-party assistive technology can toggle accessibility features inside Electron applications" by setting `AXManualAccessibility` | https://www.electronjs.org/docs/latest/tutorial/accessibility | 2026-10-08 | Verified |
| V26 | "Dreaming": a background memory synthesis, launched about 2026-06-04 for Plus and Pro in the US | https://www.pcworld.com/article/3158111/chatgpt-new-dreaming-feature-makes-it-way-better-at-remembering-you.html | 2026-10-08 | Secondary |
| V27 | Developer mode may stop memory from saving (users report turning developer mode off fixes it) | https://community.openai.com/t/chatgpt-cant-create-new-memories/1358208 | 2026-10-08 | Community (Unv) |

---

## 4. Mechanism inventory

Each table lists every mechanism a third party could use for one capability. "Sanctioned" means a documented, intended integration path. ToS and breakage risk are Low, Medium or High.

### 4.1 Capture user turns

| Mechanism | Fidelity | Sanctioned | ToS risk | Breakage | Plan / tier | Source |
|---|---|---|---|---|---|---|
| Plugin tool argument: the model copies the user's message into `northstar_context` | model_reported; only when the model calls; long pastes may be truncated | Yes | Low | Medium (plugin beta, eligibility churn) | Path depends on CS1 (V1, V2, V4) | V3, V4, V14 |
| Codex `UserPromptSubmit` hook `prompt` | verbatim, deterministic | Yes | Low | Medium | Documented for Work/Codex threads only; Chat (Unv, CS3) | V6, V7 |
| Widget or thread panel | none: a widget does not see conversation text | Yes | Low | n/a | n/a | V11, V14 |
| macOS observer, Accessibility read (L1) | verbatim (rendered), near real time, both sides | No | Grey (V17 "programmatically extract") | Medium–High (Electron UI churn) | Any plan; one-time macOS Accessibility grant | V25; observer design |
| Official export | verbatim, batch, full history | Yes | Low | Low | Free, Go, Plus, Pro (V18) | V18 |
| Internal conversation endpoint via a signed-in browser (L3a) | verbatim, exact, with message IDs and branches; minutes later | No | High (explicit extraction clause) | High | Any | [10 F10], V8, V17 |
| Local app storage of the Electron app (L3b) | Unknown (cache contents, possible encryption) (Unv) | No | High (extraction, reverse engineering) | High | Any | V10, V17 |
| Computer History memory files | Summaries of activity, not turns | Yes (user's own files) | Low | Medium | Pro only; off by default | V16 |

### 4.2 Capture AI turns verbatim

| Mechanism | Fidelity | Sanctioned | ToS risk | Breakage | Plan / tier | Source |
|---|---|---|---|---|---|---|
| Plugin tool argument: the model quotes key points of its **previous** reply at its next call | model_reported, one turn late, selective | Yes | Low | Medium | As 4.1 | V3, V14 |
| Codex `Stop` hook `last_assistant_message` | verbatim, deterministic | Yes | Low | Medium | Chat (Unv, CS3) | V7 |
| macOS observer, Accessibility read (L1) | verbatim (rendered), at reply end | No | Grey | Medium–High | Any | V25 |
| Official export | verbatim, batch | Yes | Low | Low | Personal plans; up to 7 days | V18 |
| Internal endpoint (L3a) | verbatim, exact | No | High | High | Any | [10 F10] |
| Local app storage (L3b) | (Unv) | No | High | High | Any | V10 |

### 4.3 Deterministic per-turn context injection

| Mechanism | Fidelity | Sanctioned | ToS risk | Breakage | Plan / tier | Source |
|---|---|---|---|---|---|---|
| Tool result of `northstar_context` (pin in `structuredContent`, read verbatim by the model) | model_pulled; arrives at the end of context, the best position [11 F3] | Yes | Low | Medium | As 4.1 | V14 |
| Widget `ui/update-model-context`, audience `["assistant"]` (hidden) | deterministic after mount, **if** sent on later turns (Unv) | Yes | Low | Medium (new spec) | Desktop; Chat mode (Unv, CS4) | V11 |
| Widget `setWidgetState({modelContent})` | deterministic after mount (Unv timing) | Yes | Low | Medium | (Unv, CS4) | V13 |
| Widget `ui/message {target: "active", send: false}`: stage a titled, removable Northstar item in the composer | deterministic after mount, visible, rides the user's next message | Yes | Low | Medium | Desktop; Chat (Unv, CS4) | V11 |
| Thread-panel model context (same API as the widget, one instance per thread) | deterministic after the user opens the panel once in that thread | Yes | Low | Medium | (Unv, CS4) | V11, V12 |
| Custom instructions | static, start of context (decays [11 F3]); user-written | Yes | Low | Low | All plans | V20 |
| Project instructions | static, start of context; per project | Yes | Low | Low | All plans | V21 |
| Skill (in the plugin) | model decides when it loads; "not necessarily on every request" | Yes | Low | Low | Plugin access | V5, V22 |
| MCP `instructions` field (first 512 characters) | static guidance at tool-selection time | Yes | Low | Low | As 4.1 | V3 |
| Codex `UserPromptSubmit` `additionalContext` | deterministic, ≤ ~2,500 tokens | Yes | Low | Medium | Chat (Unv, CS3) | V7 |
| Observer write (L2a): append a labelled Northstar block to the user's message on send | deterministic, visible | No | Grey-light (no clause names it) | High (focus, IME, UI changes) | Any | observer design |
| Observer rewrites custom or project instructions (L2c) | deterministic but global, start of context; "applied immediately across all chats" | No | Grey-light; changes an account setting | High | Any | V20, V21 |
| Electron debugger attach to rewrite the composer or request (L3c) | deterministic, invisible possible | No | High ("modify", "bypass") | High (may be blocked) (Unv) | Any | V17 |

### 4.4 Chat-start injection

| Mechanism | Fidelity | Sanctioned | ToS risk | Breakage | Plan / tier | Source |
|---|---|---|---|---|---|---|
| First `northstar_context` call in a new `openai/session` returns the core pack | model_pulled; first-turn call odds are the best of the chat (shortest context [11 F3]) | Yes | Low | Medium | As 4.1 | V14 |
| Boot line in custom instructions (all non-project chats) | static | Yes | Low | Low | All | V20 |
| Boot line in project instructions (project chats) | static, per project | Yes | Low | Low | All | V21 |
| Skill auto-load on relevant requests | model decides | Yes | Low | Low | Plugin access | V22 |
| `ui/message {target: "new"}` from a widget or panel: open a new chat whose first message is the resume pack | deterministic once triggered; trigger is a click or an observer event | Yes | Low | Medium | Desktop (Unv in Chat, CS4) | V11 |
| Codex `SessionStart` | deterministic | Yes | Low | Medium | Chat (Unv, CS3) | V7 |
| Observer (L2b): on a new chat, insert the pack (or a plugin `@` mention) into the first message | deterministic, visible | No | Grey-light | High | Any | observer design |
| Vendor memory | not under our control; user-centric; carries little AI-said content [14 F1] | n/a | n/a | n/a | n/a | V19 |

### 4.5 Per-reply drift check and correction

No mechanism on this surface checks a reply **before** the user sees it (no `Stop`-hook equivalent unless CS3 passes).

| Mechanism | Fidelity | Sanctioned | ToS risk | Breakage | Plan / tier | Source |
|---|---|---|---|---|---|---|
| Next-call check: at the next `northstar_context` call, the Drift Checker judges the model's reported points of its previous reply, plus correction cues in the user's copied message; a specific correction returns in that result | after_the_fact, model_reported, one turn late; only when the model calls | Yes | Low | Medium | As 4.1 | [11 F6], V14 |
| Widget pushes the pending correction as hidden model context | after_the_fact, deterministic after mount | Yes | Low | Medium | (Unv, CS4) | V11 |
| Observer read (L1) + out-of-band Drift Checker on the verbatim reply; correction via next result, widget context or L2 | after_the_fact, verbatim, seconds after display | No | Grey | Medium–High | Any | observer design |
| Optional non-blocking macOS notification or panel badge ("possible conflict with D3") | after_the_fact | Yes (own UI) | Low | Low | Any | [11 impl. 4] |
| Automatic correction turn (L2d): Northstar sends a short correction message after a flagged reply | after_the_fact, visible, doubles cost | No | Grey-light | High | Any | [11 D5] |
| Codex `Stop` hook block + continuation | before display | Yes | Low | Medium | Chat (Unv, CS3) | V7 |

### 4.6 Consolidate-and-restart into a fresh chat

| Mechanism | Fidelity | Sanctioned | ToS risk | Breakage | Plan / tier | Source |
|---|---|---|---|---|---|---|
| Tool result tells the model a fresh chat is ready; the user opens one; the boot line and first call bring the resume pack | model_pulled pack; user opens the chat (optional, not required) | Yes | Low | Medium | As 4.1 | V14, V20 |
| Widget or panel button: `ui/message {target: "new", send: true}` with the resume pack as a titled item | one tap, then deterministic | Yes | Low | Medium | (Unv, CS4) | V11 |
| Same call fired automatically at reply end, timed by the observer (L1 timing + sanctioned API) | deterministic | Mixed (sanctioned action, grey timing signal) | Grey (L1) | Medium | (Unv, CS4) | V11 |
| Observer write (L2b): new chat, paste pack plus the user's pending message, send | deterministic, with carry-over | No | Grey-light | High | Any | observer design |
| Native "Branch in new chat" | copies the drifted transcript; wrong input by design [11 F2] | Yes | Low | Low | All | [11 F12] |

### 4.7 Independent ground truth for the capture audit

| Mechanism | Fidelity | Sanctioned | ToS risk | Breakage | Plan / tier | Source |
|---|---|---|---|---|---|---|
| Official export | verbatim, complete, with conversation and message IDs; manual; up to 7 days. Backfill only, because a recurring export is a ritual (SYNTHESIS RISK 19) | Yes | Low | Low | Personal plans | V18 |
| `openai/session` call watermark (calls per session, gaps) | detects missing **calls**, not missing **turns** | Yes | Low | Medium | As 4.1 | V14 |
| Observer read (L1) vs tool-call reports | independent of the chat model; near real time | No | Grey | Medium–High | Any | observer design |
| Computer History memory files (hint that a ChatGPT session happened) | weak, summarized, Pro only | Yes | Low | Medium | Pro | V16 |
| Internal endpoint (L3a) | exact | No | High | High | Any | [10 F10] |

### 4.8 Writes into Northstar

| Mechanism | Fidelity | Sanctioned | ToS risk | Breakage | Plan / tier | Source |
|---|---|---|---|---|---|---|
| Write tool `northstar_note` (explicit notes, decisions, goals and questions; corrections said in chat as `kind: correction`; under path A, `kind: save_chat` saves the unsaved turns it carries in its own arguments, §6.2.2) | model_pulled; confirmation per tool per conversation (asked again after a reload or reopen), or "Always allow" if offered (Unv) | Yes | Low | Medium | **Official sources conflict:** writes for Business/Ent/Edu, Pro read/fetch (V1), against read and write tools in personal plugins with no plan gate (V3). CS1 decides | V1, V3, V15 |
| Widget or panel UI: the user corrects an item by clicking or typing in the Northstar widget; the widget calls the app-only `northstar_widget_action`, bound to the click by an `action_nonce` (CX §3.5) | deterministic; **user-typed origin** (I20) | Yes | Low | Medium | (Unv, CS4) | V14 |
| Observer read (L1) → core writes by code | deterministic, verbatim | No | Grey | Medium–High | Any | observer design |
| Export ingest | batch | Yes | Low | Low | Personal plans | V18 |

---

## 5. Design principles for a surface where the model decides when to call

The chat model decides when to call tools. It is also the party that drifts. A channel that depends on the drifting model choosing to re-anchor "fails in exactly the situation it is meant to fix" [10 F15]. The principles below reduce that dependence as far as the sanctioned set allows, and say where it cannot be removed.

- **P1. Need one call, not forty.** The strongest sanctioned design asks the model for **one** call, early, when instruction-following is best [11 F3]. A widget mounted by that call keeps the context alive afterwards (L0+, CS4). Every other call is a bonus.
- **P2. Make the call cheap and worth it.**
  - One per-turn tool, `northstar_context`, with short arguments, that never prompts for approval in each chat: truthfully read-only and stateless under `per_turn_readonly`, a declared write only under `per_turn_write`, where a one-time permission covers it (CX §2.5). Path W accepts one approval per chat instead, only if the user picks it (ARCH DQ-4(ii)).
  - Its result helps the model answer: it names items established earlier that are no longer near the end of the model's context ("not in your recent context: E4 (t7), D2 (t12)") [11 F2, F3].
  - Few tools in total, distinct `northstar_*` names [10 impl. 6].
- **P3. Every result carries the anchor.** Whatever Northstar tool the model calls, the result ends with the current pin. Tool results land at the end of the context, the position that survives best [11 F3].
- **P4. Boot lines in four places.** Custom instructions (non-project chats), project instructions (project chats, because custom instructions do not apply there, V21), the plugin's skill description (V22), and the MCP `instructions` field (V3). All are written as facts, not commands [10 F5].
- **P5. Prime the habit early.** Models condition on their own earlier behaviour [11 F2]. A call on turn 1, and a visible benefit from it, raises the odds of later calls. This is a hypothesis. CS5 measures it.
- **P6. Drift raises the value of the next call.** When the out-of-band Drift Checker holds a pending correction, the widget's hidden context (L0+) or the next result says so specifically. A specific correction cut drift by 87%, against 35–38% for a generic reminder [11 F6].
- **P7. The chat model is never the maintainer.** Its tool arguments are untrusted input. The Session Steward and Drift Checker run out of band, isolated, on bounded input [11 impl. 2; SYNTHESIS §3.5, AD9].
- **P8. Fail visibly.** Context receipts record what was injected [10 impl. 11]. Missing calls and missing captures show up as watermark gaps, never as silence (§8).

---

## 6. Layered strategy

### 6.1 Layer map

| Layer | Components | Needs from the user | Depends on |
|---|---|---|---|
| L0 | Northstar ChatGPT plugin: skill + remote MCP server (`northstar_context`, `northstar_note`, `northstar_fetch`, `northstar_book`; CX §2.2) + focus widget. Boot lines. Relay from the local core. One-off export backfill | One-time install; one-time custom-instructions line; boot line in each project used (CR10) | CS1 (which plugin path), CS7 (relay) |
| L0+ | Widget hidden context; `ui/message` new-chat restart; thread panel; local MCP in Chat; hooks in Chat | Nothing extra | CS4, CS2, CS3 |
| L1 | macOS observer, read only (separate design) | One-time macOS Accessibility grant; CQ1 | CQ1; CS8 |
| L2 | macOS observer, write | CQ2, CQ3 | L1; CS9 |
| L3 | Internal endpoints, app storage, debugger attach | CQ4 | Not recommended |

### 6.2 L0: the sanctioned baseline

#### 6.2.1 Packaging and hosting

The Chat surface reaches only **remote** MCP tools (V1, V5, V6, Unv until CS2). The core is local (GOAL §2). So a relay is needed. The plugin path depends on what the account allows (CS1).

Packaging routes are named PK-1, PK-3 and PK-4 (CX §5.1). PK-1 and PK-2 were one route and are merged (REVIEW FEAS-2). The letters A, B, C1, C2 and W are reserved for the write paths (§6.2.2).

| Route | How | When it applies | Write tools |
|---|---|---|---|
| **PK-1 Custom MCP server saved as a personal plugin** (preferred) | Plugins → + → Add custom MCP server → Create as a plugin (developer guide, V3, checked 2026-10-08), with Developer mode on where the route needs it. Pointed at the relay. The skill is bundled into the same plugin where the plan allows it (see below). Gives automatic use when relevant (V4) instead of `@` on each message | CS1 shows the account can add one | **Official sources conflict** (below). CS1 decides |
| **PK-3 ChatGPT Sites relay** | A Site hosts a thin MCP server that forwards to the Northstar relay. Help 20001256 says Sites plugins work on any plan (V4); "Hosting a plugin is available to all plans" (V24) | PK-1 is blocked (for example on Plus). Site → external MCP for personal plans (Unv, CS7) | (Unv) |
| **PK-4 Read-only** | Any route where only read/fetch tools are allowed (V1, Pro) | Writes blocked | None. Capture under L0 is then limited to what read calls can carry (§6.2.3) |

**Plan eligibility: official sources conflict.**
- Help 12584461 (V1): full MCP for Business and Enterprise/Edu; Pro gets read/fetch in Developer mode; Plus is not listed.
- The developer guide (V3): custom servers support read and write tools and are saved as personal plugins; it states no plan gate.
- CS1 decides on this account. The community report (V2) stays community evidence only.
- **The bundled skill may be missing.** Personal skills are generally for Business and Enterprise/Edu (help 20001256, V4). On Plus or Pro, the plugin may carry only the MCP server, so the boot lines and MCP `instructions` (§6.2.3) must work without the skill.

**Relay options** (CQ5, asked as ARCH DQ-4(iii)):
- **Secure MCP Tunnel** (V23): outbound-only `tunnel-client` to `api.openai.com:443`; no public endpoint; serves the local stdio server directly. Needs an OpenAI Platform organization and a runtime API key. Personal accounts use the personal Platform organization that belongs to the account. It is added through Plugins → Add custom MCP server → Tunnel → Create as a plugin. The authorization server is not tunneled automatically, so OAuth needs its own reachable endpoint (CS7). Personal Plus/Pro use is (Unv, CS7).
- **Cloudflare named tunnel or ngrok** with OAuth [10 F1]: a public HTTPS endpoint into the local core. The tunnel vendor can read everything in transit (ARCH DQ-4(iii)).
- **Sites relay** (PK-3): Northstar content passes through an OpenAI-hosted Site.

Every relay is a transit point for conversation text, which is SYNTHESIS RISK 13. The relay stores nothing. A sleeping laptop means Northstar is unavailable; the model then answers without it, and the gap shows in the watermarks (§8). If a TLS-inspecting proxy is on the path, CS7 checks whether it breaks the tunnel.

#### 6.2.2 Tool surface

The tool contract is CX §2. Schemas are in CX §2.3 and annotation rules in CX §2.5. This connector's profile:

| Tool | Hint | Arguments | Returns | Notes |
|---|---|---|---|---|
| `northstar_context` | `readOnlyHint: true` under `per_turn_readonly` (paths C2, A, B), where it is stateless; `false` under `per_turn_write` (paths C1, W), where it records the call (CX §2.5) | All optional (CX §2.3): `session` (handle and turn tag from the latest result); `user_message` (copied exactly; over 4,000 characters, the first and last 1,800 plus the length); `prev_reply_points` (up to 5 items, each `{kind, text ≤ 200 chars, quote ≤ 120 chars copied exactly from the previous reply, body?}`, with `body` ≤ 1,500 chars only on explanation or example points); `this_reply_points` (a closing call at the end of an explaining reply, recorded only through a declared write); `widget_tag` (the widget tag the model echoes; CX §2.3) | The pin (always, last); the card (on triggers); a specific correction (if pending); the core pack (first call of a new `openai/session`); "not in your recent context" list; a restart offer (when thresholds are crossed); under path A, a save cue (CX §2.6). Mounts the focus widget | The per-turn tool. Never prompts for approval in each chat, except under path W, which only the user can choose |
| `northstar_note` | write | `kind` (`note`, `decision`, `goal`, `question`, `correction`, `save_chat`), `text`, `quote`, `target`, `speaker` (CX §2.3) | Confirmation and the pin; a confirm card for corrections and goals | Approval per conversation (asked again after a reload or reopen), or "Always allow" if offered (V3, V15). `save_chat` is accepted only under path A, and carries the unsaved turns in its own arguments |
| `northstar_fetch` | `readOnlyHint: true` | `id` | The verbatim passage or item with its sources | For the pack's knowledge slot (SYNTHESIS §3.4) |
| `northstar_book` | `readOnlyHint: true` | `view` (`page`, `learned_about`, `next_for_goal`, `changes_since`, `contents`, `draws_on`) | A compiled Book slice and an "Open in book" link | TEXTBOOK §12.3; CX §2.2 |
| App-only tools | `_meta.ui.visibility: ["app"]` (V14) | `northstar_widget_state` (registration, heartbeat, latest pin); `northstar_widget_action` (user correction, goal confirmation, restart; needs an `action_nonce`); `northstar_book_data`; `northstar_widget_record` (path C2 only) (CX §2.4) | Hidden from the model | Called by the widget, not the model |

**The read-only rule (decided in review, REVIEW FEAS-1, SEC-7).** Under `per_turn_readonly`, `northstar_context` must be truly read-only, because a false `readOnlyHint` is ruled out (SYNTHESIS AD17). The review found that a held-content cache is state, so it is not read-only under OpenAI's or MCP's definitions. So the tool is **stateless**, as [CX] §2.5 defines:
- it computes its result from items already stored and from its own call's arguments (OpenAI's own definition: a tool that "only retrieves or computes information", V14);
- it stores no content and no hash of `user_message`;
- it keeps no session state and queues no work;
- it makes no model call;
- it keeps operational logs only, content-free ([PL] §2.10).

Persistent capture of content goes only through a tool that declares itself a write: `northstar_context` under `per_turn_write` (C1, W), the app-only `northstar_widget_record` (C2), or `northstar_note` (explicit notes; `save_chat` under A).

**What the read-only rule costs (fidelity fix, 2026-10-08; restated in review).** If `northstar_context` is the only per-turn tool and nothing else records, a ChatGPT chat adds **no** user-said and **no** AI-said knowledge to memory, apart from an explicit `northstar_note` or a one-off export. Because the tool is stateless, nothing is held: without the widget, what a chat establishes does not reach later pins in that same chat, and nothing reaches the next chat's pack. That gives up GOAL §4.2, §4.3 (automatic capture) and cross-session continuity (§3.3) on a first connector (SPINE RISK 33). It also weakens in-session checks on turns that are not recorded: the tool makes no model call, so those turns get code-only checks. So the read-only rule protects only **pin delivery**: the pin never waits on a click. Content capture takes one of the paths below (SPINE §4.6, SD-17; ARCH DQ-4(ii)). The manifest field `capture_mode` names the path (CX §2.5, D4):

| Path | How content is persisted | Per-chat click | Status |
|---|---|---|---|
| **C1** | `northstar_context` itself is declared a write (`per_turn_write`, `capture_mode: per_call`). It records each call's `user_message` and `prev_reply_points` without a per-chat prompt, because a one-time personal-account permission covers it (V15). **Permissions (REVIEW FEAS-4):** "Always allow" is offered only for an explicitly connected personal account (help 20001495, V15), so CS1 tests no-auth against OAuth on the same route and adopts OAuth only if it unlocks Always allow. "Allow low-risk actions" set per app or connection is preferred over the account default. Northstar advises this at install and never changes the setting (SD-16). An "Always ask" account default makes even reads prompt, so install guidance checks it | None after one setup | Spike CS1 |
| **C2** | The model-facing tool stays truthfully read-only and stateless (`per_turn_readonly`, `capture_mode: widget_record`). The widget reads its own call's arguments from tool-input (`ui/notifications/tool-input` or `window.openai.toolInput`, available at once for calls that need no approval) and records them through `northstar_widget_record`, a declared write. No receipt token. The widget shows "Northstar recorded this turn". Used only if the host does not prompt for it and OpenAI's published guidance permits it; Northstar never uses it to hide a write from the user | None | Spike CS4 (whether the host allows this app-only write with no per-chat prompt is (Unv)) |
| **A** | The per-turn tool stays read-only and stateless (`per_turn_readonly`, `capture_mode: save_on_request`). A chat is saved by `northstar_note(kind: save_chat)` carrying the unsaved turns in its own arguments, or by a widget **Save this chat** click (preferred). Northstar cues a save (CX §2.6). Nothing is held by the core in between | One approval per chat if it is remembered for the chat, again after a reload or reopen (custom MCP guide, V3), otherwise one per save. The pin never waits on it | Fallback; the user decides (ARCH DQ-4(ii)). Capture is not automatic: a chat keeps nothing if no save happens, or if the user declines or skips the approval (CR16) |
| **B** | Read-only and stateless (`per_turn_readonly`, `capture_mode: receipts_only`). Nothing persists from the per-turn tool; only explicit `northstar_note` writes, each approved | None | Fallback; the user decides (ARCH DQ-4(ii)). Narrows §4.2 and §4.3 on this surface |
| **W** | `northstar_context` is declared a write with a recurring approval (`per_turn_write`, `capture_mode: per_call`; ARCH DQ-4(ii)). Once approved, capture and focus work as on a click-free app | One approval per chat, and again after each reload or reopen. If an approval is skipped, that chat gets neither the pin nor capture (CR16) | Option the user may pick (ARCH DQ-4(ii)) |

**Spike results.** Not run yet. CS1 and CS4 touch the user's ChatGPT account, so they need the user's go-ahead (§13). CS1 runs on day 1 of Stage 0, and CS4 follows in Stage 0 (SPINE SD-18). Their results will be recorded here. ARCH DQ-4(ii) (this document's CQ8) is asked only if both fail.

**Conflict with SPINE §5.5, resolved.** SPINE §5.5 carries recent provisional items from any surface into the next pack. The core never holds unsaved turns from this connector: under the stateless rule, content reaches the store only through a declared write. Under paths C1, C2 and W, each recorded call is persisted, and §5.5 applies as on any other surface. Under path A, §5.5 applies to the turns a save recorded; turns never saved never reach the core. Under path B, nothing from the chat reaches the core, so §5.5 has nothing to carry.

**Result shape.** Plain text plus `structuredContent`, worded as attributed facts, labelled as Northstar state, never imitating vendor tags [11 impl. 3; SYNTHESIS §5 item 8]. Example:

```
[Northstar session state, kept for the user; not the user's words; as of turn 14; supersedes all earlier Northstar blocks in this chat]
Check of reply 13: it re-proposes R1. R1 was rejected at turn 9 by the user (needs a public endpoint). No later user turn reverses this.
G1 [user, as reported by the chat model, t1]: design the ChatGPT desktop connector.
C1 [user, as reported by the chat model, t3]: no browser extension.
D2 [AI (ChatGPT), t12, accepted]: use one read-only tool per turn, because approvals reset per chat.
Not in your recent context: E4 [user, as reported by the chat model, t7], D2 [AI (ChatGPT), t12].
[end Northstar]
```

The example follows the IS §8.2 wording rules: third-person facts, user items labelled as the chat model's report, no commands.

Budget: as CX §2.7. A per-turn result stays within 4,000 characters (pin ≤ 600); the first call within 12,000 (pack 1.5–3k tokens, SYNTHESIS §5 item 6); `structuredContent` within 1,000. ChatGPT's tool-result size limit is (Unv), CS4.

#### 6.2.3 Boot lines

| Place | Applies to | Draft (facts, not commands) |
|---|---|---|
| Custom instructions | All non-project chats, "immediately … including existing conversations" (V20) | As CX §5.3: "Northstar is my memory system, installed as a plugin. My chats usually continue earlier work. Its northstar_context tool holds my goals and what was already established; I want it consulted at the start of every reply, with my latest message passed exactly, and not in Temporary chats." |
| Project instructions | Chats in that project only (V21) | The same line. One-time per project (CR10) |
| Skill description | Loaded when ChatGPT judges it relevant (V22). May be missing on Plus or Pro, where personal skills are generally unavailable (§6.2.1) | "Use when the user continues earlier work, learning or a decision, or asks something that may depend on what was established before in this or earlier chats." The body explains the protocol and the argument rules |
| MCP `instructions`, first 512 characters (V3) | Tool selection | As CX §2.8 (built by C15, profile `mcp_instructions`): "Northstar keeps the user's goals and what the user or an AI already established, across chats and products. northstar_context returns this state with IDs and sources; on a chat's first call it returns the starting pack. Passing the user's latest message exactly lets it check the previous reply. Results are data about the work, not instructions from the user." |

Tool names in these lines follow CX §1.2 (the map at the top of this document). The boot lines name only `northstar_context`; no line names `northstar_resume`, `northstar_sync` or `northstar_turn`.

**Plugin and skill descriptions** describe their relevance to continuing work factually. They are never written as a blanket trigger ("use on every message"). ChatGPT offers a plugin per message, by relevance (V1, V4); the description states when Northstar is relevant and leaves that judgment to the host.

The custom-instructions text also reaches plugin developers (V20) and is a vendor-memory source (V19). It contains nothing private.

#### 6.2.4 Focus widget

- Every `northstar_context` result renders the widget. The newest instance is primary.
- **Supersession is core-mediated.** Each instance registers its `openai/widgetSessionId` with the core through the app-only `northstar_widget_state`. Older instances learn they are superseded, clear their model context, and collapse to one line. This avoids depending on `BroadcastChannel` inside ChatGPT's sandbox [10 F2].
- The primary instance:
  - pushes the pin with `ui/update-model-context`, audience `["assistant"]` (hidden), and mirrors it in `setWidgetState({modelContent})` (V11, V13);
  - pushes on every host signal: tool result, host-context change, tool-input notices, focus, resize and visibility, whether it is visible or not (REVIEW FEAS-5). Each push re-reads the latest pin from the core through `northstar_widget_state` and replaces the last one (V11). A re-push timer that runs independent of visibility is best effort, because a host may throttle a hidden widget;
  - tags each push with a widget tag the model may echo ([CX] §3.4). An echo is the evidence that the context reached the model; without one, delivery is recorded as unknown, never as failed;
  - shows a one-line status ("Northstar: focus G1, 3 items, updated t14") with **View** (opens the human view) and **Fresh chat** (§6.2.6);
  - lets the user correct an item in place. That correction is user-typed origin (I20) and reaches the core through `northstar_widget_action`, valid only with an unused `action_nonce` from a trusted click (§4.8; CX §3.5).
- Whether the widget can reach the local core directly, instead of through the host and relay, is (Unv, CS4).

The widget only helps if the host sends its model context on **later** turns. The spec does not say (V11). That is CS4, the most important spike for this surface.

#### 6.2.5 Session identity

- The session ledger is keyed by `_meta["openai/session"]`, the anonymized conversation ID ChatGPT sends with every tool call (V14). The model does not have to report it. Stability across app restarts and devices is (Unv, CS11).
- The anonymized ID cannot be joined to export conversation IDs directly. The join is by content: the hash of the copied user message, aligned with the export or observer text (§7).

#### 6.2.6 How the in-session focus loop works under L0

**A turn under L0, step by step.**
1. The user sends a message.
2. The model may call `northstar_context(session, user_message, prev_reply_points)` (CX §2.3). The odds depend on the boot lines, the skill and chat length (CS5).
3. The core looks up the session ledger by `openai/session`.
   - The **Goal-Change Handler** classifies the copied user message (continue, refine, pivot, goal change, tangent) [11 impl. 5].
   - **Correction cues** in the user message ("as I said", "no, I meant") count as drift evidence against the previous reply [11 impl. 11].
   - The **Drift Checker** judges the reported points of the previous reply against active items, deterministic checks first, then an isolated judge [11 impl. 4]. Under the stateless read-only profile, the judge runs only on turns a declared write recorded; other turns get the deterministic checks only, because the tool makes no model call (§6.2.2).
4. The result returns the pin, a card on triggers, any specific correction, and the "not in your recent context" list. The widget mounts or updates.
5. The model answers, with the anchor at the end of its context.
6. After the call is recorded by a declared write (paths C1 and W at once; C2 through the widget; A when a save records it), the **Session Steward** runs out of band on the reported text: ledger plus the reported turn pair plus the previous pair [11 impl. 2]. Unrecorded turns get no steward run. Its validators require each operation to cite a span that string-matches the **reported** text. Items are marked `capture: model_reported` and labelled "provisional, reported by ChatGPT" in the pin.
7. If the model did not call, nothing happens on that turn, and the core cannot know a turn occurred.

| Component | How it works under L0 | Strength |
|---|---|---|
| Session Ledger | Keyed by `openai/session`. Fed by reported user messages and reported AI points. Branch structure is invisible | Partial: model_reported, gaps when no call |
| Session Steward | Out of band, isolated. Validators bind spans to the reported text only. Goals from reported user text are provisional and cannot become constraints or instructions until verbatim text confirms them (I5, hardened for this surface; CR13) | Partial |
| Pin | Every result, plus widget context (L0+) | model_pulled; deterministic after mount if CS4 passes |
| Card | Triggers: every N calls, after a pivot, after a drift flag, after a long gap between calls (possible compaction) [11 impl. 3] | model_pulled |
| Drift check | One turn late, on reported points plus user correction cues | Weak: the model reports on itself, and self-report misses errors (64.5% of own errors missed [13]; SYNTHESIS §3.5) |
| Correction | Specific, cites item IDs, rides the next result or widget context [11 F6] | model_pulled / after mount |
| Consolidate-and-restart | When thresholds cross (drift score over a window, call count high-water mark, suspected compaction), the result offers a fresh chat in one line, and the widget shows **Fresh chat**. A click sends `ui/message {target: "new"}` with the resume pack as a titled item (Unv, CS4). Without CS4, the user opens a new chat and the first call brings the resume pack. The pack is built from the ledger, never from the transcript [11 F2] | Optional one tap; the old chat stays |

**Why restart is one tap, not automatic, under L0.** Northstar does not know when a reply has finished, so an automatic `ui/message {target: "new"}` could pull the user away mid-reply. Automatic restart needs a reply-end signal (L1) or full input control (L2). The user never has to restart; per-turn levers keep working without it.

#### 6.2.7 Cross-session continuity under L0

- A new chat gets a new `openai/session`. The first `northstar_context` call returns the **core pack** (SYNTHESIS §3.4): active goals, the knowledge slot (user-stated knowledge and AI-taught passages as gist plus ID, fetchable verbatim with `northstar_fetch`), conclusions with who established them, open questions, rejected options ("do not re-propose"), disputed AI claims ("do not re-assert"), contested items, recent provisional items from any surface, and `reported` goals in a labelled slot (SPINE SD-36). The pack carries no per-concept engagement state; an item may at most cite a dated, attributed engagement event (SPINE §4.7, §5.2).
- **What earlier ChatGPT chats contribute** depends on the capture path (§6.2.2). Under paths C1, C2 and W, they contribute like any other surface. Under path A, only the turns a save recorded contribute. Under path B, they contribute nothing, so a new ChatGPT chat starts only with what other surfaces established (SPINE RISK 33).
- The **goal router** uses the copied first message [SYNTHESIS §3.4].
- The pack is cross-surface by construction: a ChatGPT chat starts with what was established in Claude Desktop, Claude Code or Codex.
- The pack's items seed the new ledger. The Drift Checker runs from turn 1.
- The **re-explanation detector** runs on copied user messages. Under L0 it only sees turns where the model called.
- If the model never calls in a chat, that chat gets no pack, and Northstar cannot see the miss until verbatim text arrives (L1 or export).

#### 6.2.8 Capture and writes under L0

- **User side:** under `per_turn_readonly`, `northstar_context` is stateless and keeps nothing (§6.2.2). Content is stored through the capture path chosen in §6.2.2 (C1, C2, W, or A when a save records the turns; unsaved turns are never held), through an explicit `northstar_note`, or through reconciliation. **Under path B, a chat stores no user-said content at all**, apart from explicit notes or a one-off export.
- **AI side:** `prev_reply_points` are model_reported AI-said content *about* the previous reply [10 impl. 2]. Stored through the same capture path, with speaker `ai`, reporter `chat_model`, and `capture: model_reported`. **Under path B, no AI-said content from the chat is stored** (SPINE RISK 33).
- **Long-term promotion:** model_reported items may be promoted only with a "reported by ChatGPT, not verbatim" chip, and they are re-derived when verbatim text arrives (§7). The human view shows the chip.
- **Backfill:** a one-off export at install time ingests past history (V18). A recurring export would be a ritual, so it is never the path that meets §4.2 (SYNTHESIS RISK 19).

### 6.3 L0+: sanctioned upgrades that depend on spikes

| Upgrade | If the spike passes | Effect |
|---|---|---|
| **Widget hidden context in Chat** (CS4) | `ui/update-model-context` reaches the model on later turns in desktop Chat | inject_turn becomes **deterministic after mount**. Delivery no longer decays with chat length. The only model-dependent step is the first call (P1) |
| **New-chat message in Chat** (CS4) | `ui/message {target: "new"}` opens a Chat conversation with the content | restart becomes **one tap, deterministic**. The resume pack is the first message of the new chat: the CONCAT pattern [11 F1, F7] |
| **Staged composer item in Chat** (CS4) | `ui/message {target: "active", send: false}` stages a titled, removable item | A sanctioned, **visible** per-turn card or correction that rides the user's next message. Used only when the hidden context fails, because visible blocks may be absorbed by vendor memory (CR9) |
| **Thread panel in Chat** (CS4) | Thread entrypoints are offered in Chat | A live Northstar tab beside the chat: the ledger, flags, a restart button and corrections. Opening it is optional, per thread. It is one context provider per thread, so widget instances defer to it |
| **Local MCP in Chat** (CS2) | Chat can call a local stdio server or a local plugin app | No relay is needed, which removes CR4 and RISK 13 for this surface. Not expected (V5) |
| **Codex hooks in Chat** (CS3) | `UserPromptSubmit`, `Stop` and `SessionStart` fire in Chat threads | This surface becomes as strong as Codex: verbatim capture, deterministic injection, and correction before display. Not expected (V6, V7) |

### 6.4 L1: macOS observer, read only

The separate observer design covers how this works. This connector needs these events from it:

| Event | Fields this connector uses |
|---|---|
| `turn.completed` | app (ChatGPT or Classic), mode (Chat, Work, Codex), conversation title, turn index, role, rendered text, start and end times, streaming finished |
| `chat.opened`, `chat.switched`, `chat.new` | conversation identity as visible in the UI |
| `chat.temporary` | whether the chat is a Temporary chat, so it is never captured |
| `reply.ended` | the reply-end signal used to time restarts and checks |

**What L1 changes, per GOAL requirement.**
- **Capture (§3.1, §4.2):** both sides verbatim (rendered) seconds after each reply. Speaker is set by code from the UI role. The Session Steward runs on real spans, not reports.
- **In-session focus (§3.3):** the Drift Checker judges the **real** reply, not the model's self-report. Corrections become accurate and specific. The re-explanation detector sees every turn.
- **Restart:** automatic at reply end, **only if the user allows automatic sending under SPINE UQ-1**; until then it stays one tap. When thresholds cross and UQ-1 allows it, the observer's `reply.ended` event lets the widget fire `ui/message {target: "new"}` safely (if CS4 passes); otherwise restart stays one tap until L2.
- **Audit (§4.7):** an independent ground truth for every turn. Tool-call reports are reconciled within seconds (§7). Missing calls are now visible as "turns without a call".
- **Measurement (§6):** **shadow mode** (capture only, no injection) gives the control arm on this surface [10 impl. 7].

**Cost.** One-time macOS Accessibility permission. Local processing only. A Temporary-chat skip and an account allowlist (SYNTHESIS §5 item 9).

**ToS and breakage.**
- The Terms prohibit "Automatically or programmatically extract data or Output" (V17). Accessibility reading of the window is programmatic extraction of Output, even though the user owns the Output (V17). It is grey.
- Precedent: OpenAI's own **Computer History** reads activity through macOS accessibility features and writes model-summarized memories to plain files (V16). This shows the technique is normal on macOS and used by OpenAI. It does not grant a third party permission to extract ChatGPT Output.
- Detection risk is low, because nothing is sent to OpenAI. ToS exposure is about permission, not detection.
- Breakage is medium to high. The Electron app ships often, and its accessibility tree can change without notice. Silent failure is the danger (SYNTHESIS RISK 6, [10 R6]); §8 covers detection.

### 6.5 L2: macOS observer, write

| Sub-layer | What it does | Gain | Cost and risk |
|---|---|---|---|
| **L2a Visible per-turn block** | On send, appends a short labelled block (the pin, or the card and correction on triggers) to the user's message | inject_turn **deterministic** without any model call, even if CS4 fails | Visible in the transcript and in vendor memory input (CR9). Collides with typing and input methods. Capture strips the block by its delimiter |
| **L2b Prepared restart with carry-over** | At threshold, after the reply ends: opens a new chat and fills it with the resume pack and the user's pending message. The user sends it. Auto-send only if the user allows it under SPINE UQ-1 | restart **prepared**, one user action; **automatic** only with a yes to UQ-1 (SPINE §4.10), matching SYNTHESIS AD12's leaning and spike S11 | Breaks the thread; the old chat stays available. High breakage |
| **L2c Rolling instructions** | Rewrites custom instructions (or a project's instructions) with the current goals | inject_start and a weak inject_turn that are **deterministic** at the start of context, "applied immediately across all chats" (V20) | Global across all chats, so only cross-session goals fit. Start-of-context position decays [11 F3]. Feeds vendor memory (V19). Changes an account setting automatically (CQ3) |
| **L2d Correction turn** | After a flagged reply, sends a short visible correction message | Correction lands before the user's next turn | Sends messages on the user's behalf; doubles cost [11 D5]. Off by default |
| **L2e Assisted first call** | In a new chat, adds an `@Northstar` mention to the first message | Forces the first call, which mounts the widget (P1) | Visible; small |

**ToS.** L2 writes the user's own input and settings. It extracts nothing. No clause in the Terms names it (V17). It still automates the Services, so it is grey-light. Breakage is high.

### 6.6 L3: internal data paths (not recommended)

| Path | Gain | Why not |
|---|---|---|
| L3a Internal conversation endpoint through a signed-in browser (desktop Chat syncs to the web, V8) | Exact text, branch tree, message IDs: the best audit truth after export | Explicit extraction clause (V17); undocumented and breaks without notice [10 F10]. The web connector is optional (GOAL §4.6) |
| L3b Local storage of the Electron app | Possibly local conversation caches (Unv) | Extraction plus reverse engineering of storage formats (V17); contents unknown; possible encryption (V10) |
| L3c Electron debugger attach (DOM read and write, request rewrite) | Everything a browser extension gets, on desktop | "Modify … our Services" and "bypass any protective measures" (V17); may be blocked by the app (Unv); a security hazard on the user's machine |
| Using the app's session token | Same as L3a without a browser | Credential handling; never acceptable |

### 6.7 Adjacent modes: options, never replacements

The same app offers **Work** (local Work threads run Codex hooks and local MCP, V6) and **Codex** (full hooks). The web app chatgpt.com is optional (GOAL §4.6). These may be offered as **additional** options, for example "continue this long session in a local Work thread". Proposing any of them **instead of** Chat would re-scope the surface, so it goes to the user as CQ6. The Codex connector is designed separately.

### 6.8 Gains per GOAL requirement, per layer

| GOAL requirement | L0 | L0+ (CS4 passes) | L1 | L1 + L2 | L3 |
|---|---|---|---|---|---|
| §4.2 AI-said captured verbatim | **Not met live**: model_reported points, one turn late. Verbatim only from a one-off export | Same as L0 | **Met** (rendered verbatim, seconds) | Met | Met (exact) |
| §3.1 user-said captured | Partial: model_reported, when called | Same | Met | Met | Met |
| §3.3 in-session focus: per-turn pin | Partial: model_pulled, decays | **Mostly met**: deterministic after one call | As L0 or L0+ | **Met**: deterministic even without a call | n/a |
| §3.3 per-reply drift check | Weak: on self-report, one turn late | Same check; correction delivery deterministic | Good check, after display | Plus optional correction turn | n/a |
| §3.3 consolidate-and-restart | Optional; user opens a new chat | One tap, deterministic pack | As L0 or L0+; automatic at reply end only with a yes to UQ-1 (and CS4) | Prepared with carry-over (the user sends); automatic only with a yes to UQ-1 | n/a |
| §3.3 cross-session pack | model_pulled at the first call | First call still needed | As L0/L0+, plus misses become visible | Deterministic (L2e or L2c) | n/a |
| §4.3 no per-chat action | Partial: per-project boot line; `@` on each message if CS1 shows the route is not offered automatically (V1); under option A, one approval per chat if remembered (again after a reload or reopen), else one per save, and capture waits on a save (CR16); under option W, one approval per chat and per reload; under option B capture is off instead (ARCH DQ-4(ii)) | Same; path C2 may remove the approval (CS4) | Same; capture by the observer needs no click | Same | n/a |
| §4.7 audit truth | After the fact (one-off export) | Same | **Met**, live | Met | Met |
| §6 measurement on this surface | Weak: no control arm without capture | Weak | Shadow-mode arm | Plus randomized levers | n/a |

### 6.9 Expected effect, quantified where the evidence allows

**What the evidence says** [11 F1, F5, F6; SYNTHESIS §3.3]:
- Multi-turn chats lose 39% on average, mostly reliability. One consolidated prompt (CONCAT) keeps 95.1% of single-turn performance.
- Re-injection helps partly: RECAP recovers 44–52% of the gap, SNOWBALL 18–31%, goal restatement at turns 4 and 7 adds 16–27% to judge scores.
- A behaviour-specific correction cut drift 87%, against 35–38% for persona re-injection. Adaptive timing added nothing.
- Constraints pinned outside compacted text stayed at 0% violations, against 30% (up to 59%) after compaction.
- No vendor publishes how often a model calls a tool it is told to call. Practitioners report skips [10 F15].

**Model.** Effective recovery on a turn ≈ (probability the anchor is delivered on that turn) × (effect of the anchor). The first factor is what the layers change.

At L0 the delivery probability is the tool-call rate r(t), and it has two parts (REVIEW FEAS-3):
- **o(t), tool offered:** ChatGPT offers a plugin per message, by relevance, or because the user typed `@` on that message (V1, V4). A tool that is not offered cannot be called.
- **c(t), model chose to call:** given the tool is offered, the model decides to call it.
- So r(t) ≈ o(t) × c(t). The two fail for different reasons: c(t) responds to boot lines and to a useful result; o(t) depends on the host's relevance judgment (which reads the factual plugin description, §6.2.3) or on `@`. CS5 logs "not offered" and "offered but not called" apart.

| Layer | Delivery probability on turn t | Effect when delivered | Illustration only (not evidence) |
|---|---|---|---|
| L0 | r(t) ≈ o(t) × c(t), the tool-call rate, likely highest at turn 1 and falling (CS5) | Pin: roughly in the SNOWBALL-to-RECAP band (18–52% of the gap). Corrections: up to −87% on detected behaviours, but detection on self-report is weak | If r falls from 0.9 to 0.4 by turn 40, recovery at turn 40 is about 7–21% instead of 18–52% |
| L0+ | ≈ 1 after the first call, if CS4 passes | Same pin effect; corrections delivered every time | 18–52% from the turn after the first call |
| L1 + L0+ | ≈ 1 after the first call | Corrections detected on real replies, so more of the −87% lever applies | Higher than L0+; size unknown until protocol B or C |
| L1 + L2 | 1 | Same, with automatic restart | Restart returns quality towards ~95% of single-turn (CONCAT), minus pack losses (unknown) |

**Reading this.** L0 alone is unlikely to meet the SYNTHESIS §7.1 bars (at least 30% fewer contradictions and 25% better adherence at 40+ turns) unless CS5 shows a high and stable call rate. L0+ might. L1 + L2 is the configuration most likely to meet them. These are expectations to test, not results.

**Cross-session.** The first call of a chat is the most likely call of all, because the context is short and instruction drift has not set in [11 F3]. So L0's cross-session channel should be stronger than its in-session channel. CS5 measures the first-call rate. The SYNTHESIS §7.2 bar is at least 30% fewer re-explanations in the first 5 turns.

---

## 7. Reconciling model-reported capture with verbatim capture

**Why.** Model-reported capture is the model paraphrasing or copying. It is AI-said *about* the conversation, never its record [10 impl. 2]. User-centric extraction loses AI content (Zep: −17.7% on assistant-said questions) [14 F1].

**Records.**
- Each report is stored as an observation with `capture: model_reported`, `channel: mcp_report`, the `openai/session`, call index, time and the normalized-text hash.
- Verbatim text arrives with `capture: verbatim` and `channel: ax_rendered` (L1) or `channel: export`. After a match, both are kept, and the linked item becomes `capture: reconciled` (SYNTHESIS §3.1, AD6).

**Matching.**
1. Normalize both texts: Unicode NFC, collapsed whitespace, markdown rendering artefacts removed.
2. Link each reported `user_message` to a verbatim user turn by hash. Otherwise use a fuzzy match (edit-distance ratio, within a time window).
3. For each reported AI point, check that its `quote` is a substring of the verbatim AI turn: `quote_verified` or `quote_failed`.
4. Re-run the Session Steward on the verbatim window. Compare its operations with the reported ones:
   - matched: the item becomes `reconciled`;
   - reported only: superseded with `reason: reconciled_absent`, kept as history (SYNTHESIS §5 item 3);
   - verbatim only: added. This counts as an omission in the reports.
5. Session joins: the `openai/session` key is mapped to the observer's or the export's conversation by the sequence of user-message hashes.

**Metrics, used as sentinels and as calibration.**
- Copy fidelity: the share of reported user messages that match exactly.
- Quote-verify rate for AI points.
- Omission rate: AI-said items found in verbatim text but missing from reports, scored separately (GOAL §4.2).
- Fabrication rate: reported points with no support in the verbatim reply.

**Calibrated trust, never promotion of authority.** When copy fidelity is high over a rolling window, reported user text may seed provisional session goals with more confidence. It never creates instructions or constraints (I5): a model can be induced by injected content to "report" text the user never typed (CR13).

---

## 8. Maintainer and audit on this surface

| Signal | Layer | What it detects |
|---|---|---|
| Calls per `openai/session`, and gaps in time | L0 | The model stopped calling. It cannot detect turns without a call. Under the stateless read-only profile this comes from content-free operational logs, never used to change a result (§6.2.2) |
| Call-rate decay curve per session | L0 | The core L0 failure mode, measured continuously (CS5 in production) |
| Widget heartbeat (`northstar_widget_state`) | L0+ | Whether the widget is alive and pushing context |
| Context receipts (what was injected, when) | All | What the model was given; also for the human view [10 impl. 11] |
| Turns seen by the observer vs calls received | L1 | Missing calls, exactly |
| Observer capture anomalies: a turn shown but not captured; a sudden drop in AI-said text length | L1 | Silent observer breakage after an app update [10 impl. 8] |
| Observer self-test, passive | L1 + L2 | Profile breakage after an app update: runs on an already open window at launch, app update, wake and hourly, and fails closed to shadow ([OBS] §4.7; CX §6.3). It sends nothing. **No canary chat is sent**: it would be a message sent for the user (SPINE UQ-1; SPINE fidelity fix 12) |
| Export reconciliation | L0 and up | Final truth, when an export is requested; backfill only (RISK 19) |
| Computer History files (Pro, opt-in) | L0 | A weak hint that ChatGPT was used when Northstar saw no calls (V16). Privacy: read only entries about ChatGPT, if the files allow it (Unv) |

**Rules carried over.** Tool calls by the chat model are untrusted input (SYNTHESIS §3.5). The steward never reads its own earlier verdicts [11 impl. 8]. Every K turns (L1), an audit pass re-derives the ledger from raw transcript windows and measures disagreement [11 impl. 8]. Under L0 there are no raw windows, so this audit runs only after verbatim text arrives (CR7).

---

## 9. Vendor memory, Projects and Temporary chats

**Vendor memory policy (a design decision, GOAL §2).**
- Leave the user's memory settings as they are. Northstar never changes them itself.
- Prefer channels that do not look like user words: tool results and hidden widget context. Use visible blocks (L0+ staged items, L2a) only when the hidden channel fails, because visible blocks become part of the user's message and may be absorbed into memory as if the user said them (SYNTHESIS RISK 11; [11 risk 3]). **Caveat (review):** OpenAI's hidden widget context also rides as a composer attachment on the user's own message, so "hidden is safer for vendor memory" is unproven. CS10 measures the hidden channel too (CR9).
- Label every block "Northstar state (not the user's words)".
- Do not adopt L2c by default: custom instructions are a memory source (V19).
- Ingest nothing from vendor memory except as "assistant-asserted about the person" [10 impl. 10].
- Measure absorption (CS10). If a self-poisoning loop is measured, Northstar proposes a change to the user; it does not make it.
- Note: developer mode may stop memory from saving (V27, community). Whichever route needs Developer mode, the user may lose vendor memory in those chats (CR15).

**Projects.**
- Inside a project, custom instructions do not apply; only the project's instructions do (V21). The boot line must be added once per project (CR10), or added by L2c if the user accepts CQ3.
- Apps work in projects on personal plans (V21). Whether installed plugins are used automatically inside projects is (Unv, CS1).

**Temporary chats.**
- A Temporary chat can be set to use plugins (V19). Under L0, Northstar may receive tool calls from a Temporary chat and cannot tell (Unv, CS12).
- Mitigation: the boot text says not to call Northstar in Temporary chats; any session the observer marks temporary is purged; under L0 alone this is a residual privacy risk (CR11).

---

## 10. Honest residue: risks for the user

Nothing below is designed away. Each risk names the GOAL items it threatens and links to SYNTHESIS risks.

### 10.1 What stays unmet, per layer

| Layer | What stays unmet |
|---|---|
| **L0** | AI-said text is not captured verbatim live (§4.2). Per-turn focus depends on the drifting model calling a tool (§3.3, §4.5). No reply can be checked before or reliably after display. No live audit truth (§4.7). Restart and the cross-session pack depend on model calls or a user click. On Plus, the sanctioned MCP path may not exist (CR3) |
| **L0+** | AI-said capture still not verbatim. The first call per chat is still model-pulled. Drift checks still judge the model's self-report. No live audit truth |
| **L1** | No correction before display. Injection still as L0 or L0+. Grey ToS. Breaks silently when the app's UI changes, unless detected |
| **L1 + L2** | No correction before display (only a follow-up turn). Visible blocks pollute the transcript and may feed vendor memory. Grey ToS. High breakage |
| **L3** | Not recommended; explicit ToS exposure |

### 10.2 Risk register

| ID | Risk | Threatens | Mitigation | Links |
|---|---|---|---|---|
| CR1 | Under L0, per-turn focus is model-pulled, and tool calls likely fade in exactly the long chats that need them | §3.3, §4.5, §6 | P1–P6; widget context (CS4); L2a; measure r(t), with "not offered" and "offered but not called" apart (CS5, §6.9) | RISK 4, [10 F15] |
| CR2 | Under L0 and L0+, AI-said capture is the model's report of its previous reply: selective, one turn late, not verbatim | §4.2 | `quote` fields; reconciliation (§7); L1; one-off export backfill | RISK 19, [10 impl. 2] |
| CR3 | Official sources conflict on plan eligibility. Help (2026-10-07): developer mode and full MCP for Business/Ent/Edu on the web; Pro read/fetch; Plus not listed (V1). Developer guide: read and write tools in personal plugins, no plan gate (V3). On Plus, L0 may have no custom MCP tool at all; on Pro, writes may be blocked. The only route may need `@` on every message | §4.3, §4.6 | CS1 on day 1 of Stage 0; routes PK-1 to PK-4 (§6.2.1); Sites relay (PK-3, Unv); ARCH DQ-4(i) asked at once if CS1 fails; L1 for capture | RISK 5 |
| CR4 | Chat reaches only remote MCP, so a local core needs a relay. A sleeping laptop makes Northstar unavailable | §4.6; privacy | Secure MCP Tunnel or Cloudflare tunnel; relay stores nothing; gaps visible in watermarks | RISK 13 |
| CR5 | No layer can correct a reply before the user sees it (no `Stop` hook unless CS3 passes) | §3.3, §6 | Specific correction next turn (−87% [11 F6]); optional badge; L2d | RISK 20 |
| CR6 | L0 cannot restart automatically; carrying over the pending message needs L2 | §3.3 | One-tap restart (CS4); L2b | RISK 20; AD12 |
| CR7 | L0 has no live audit truth; capture gaps are invisible until an export, which is manual and up to 7 days | §4.7 | L1; export backfill; call watermarks | RISK 6, RISK 19 |
| CR8 | L1 and L2 are ToS-grey (V17) and break when the frequently updated Electron UI changes; failures can be silent | §4.7; account standing | User decision (CQ1, CQ2); observer anomaly sentinels; kill switch | RISK 6, [10 R6] |
| CR9 | Visible injection (staged items, L2a) enters the transcript and may be absorbed into vendor memory as user-said. OpenAI's hidden context is also a composer attachment on the user's own message, so "hidden is safer for vendor memory" is unproven (review) | §3.3; sycophancy | Prefer hidden context and tool results until measured; labels; CS10 measures the hidden channel too | RISK 11 |
| CR10 | Custom instructions do not apply in project chats; the boot line is needed once per project | §4.1, §4.3 | Skill and MCP `instructions` still apply (Unv in projects); L2c if accepted | — |
| CR11 | Under L0, Temporary chats may send tool calls to Northstar without a reliable signal | Privacy | Boot text; observer purge (L1); CS12 | SYNTHESIS §5 item 9 |
| CR12 | No same-chat counterfactual inside the app; ChatGPT's system prompt is unpublished, so API replay fidelity is low | §6 | Shadow mode (L1); protocol B with its gap stated; at least 8 samples | RISK 12, RISK 21 |
| CR13 | Tool results and model context are injection surfaces. A model can be led by injected content to "report" user text that was never typed | Trust; §4.7 | I5 hardened: reported user text never creates instructions or constraints; delimited data; red-team CI | RISK 9 |
| CR14 | Product churn: developer-mode guide removed (404), app renamed in July, Extensions spec repository created 2026-09-29 [10 F7] | §4.8 | Everything behind the adapter contract; spikes re-run on each app update | RISK 14 |
| CR15 | Developer mode may stop vendor memory from saving (community). Applies to whichever route needs Developer mode | User experience | CS1 checks memory saving on Pro; tell the user | V27 |
| CR16 | If "Always allow" is not offered, write tools need approval once per new conversation if the approval is remembered for it, again after a reload or reopen (custom MCP guide, V3), and otherwise at every write. Under option A, a chat is saved only by `northstar_note(kind: save_chat)` carrying its unsaved turns, or by a widget **Save this chat** click; nothing is held in between. A chat loses its content when the user declines or skips the approval, or when **no save happens** (the model never calls `save_chat` and nobody clicks). Under option W, a skipped approval loses both the pin and capture for that chat. Keeping L0 read-only instead (path B) means a chat adds nothing to memory at all | §4.1, §4.2, §4.3, §3.3 continuity | Stateless read-only pin tool so focus never waits on a click (except under W); paths C1 and C2 first (CS1, CS4); widget Save click; save cue (CX §2.6); L1 for capture; ARCH DQ-4(ii) | RISK 19; SPINE RISK 33; RISK-CX-3 |

---

## 11. Decisions only the user can make

Each has a working assumption, used only for spikes and drafts. **Nothing ships on it, and silence is never taken as an answer** (SYNTHESIS §9 rules).

| ID | Decision | Why it is the user's | Working assumption (pending user answer) |
|---|---|---|---|
| CQ1 | Accept **L1**: Northstar reads the ChatGPT window through macOS Accessibility | ToS-grey (V17 "programmatically extract … Output"); it is the only way found to meet §4.2 and §4.7 live on this surface | **Yes**, read only, processed locally, Temporary chats skipped, an account allowlist, one-click kill switch |
| CQ2 | Accept **L2** writes: L2b automatic restart with carry-over, L2e assisted first call, and L2a visible per-turn blocks | Automation of the user's own input; visible changes to their messages | **Superseded by SPINE UQ-1**, which asks this for both desktop apps. Until the user answers UQ-1: nothing is sent for the user; L2b may prepare a fresh chat with carry-over but never sends it; L2a and L2e only where CS4 shows hidden widget context does not work in Chat; L2d off |
| CQ3 | Accept **L2c**: Northstar rewrites custom or project instructions automatically | Changes an account setting; feeds vendor memory (V19) | **No** |
| CQ4 | Accept any **L3** path | Explicit ToS exposure, credentials, reverse engineering | **No.** Never the app's token. A browser-side fetch only if the user later turns on the optional web connector |
| CQ5 | Which **relay** carries tool calls from ChatGPT to the local core. **Asked as ARCH DQ-4(iii)** (REVIEW SEC-9), which takes over the vendor choice from ARCH R16. If ChatGPT cannot reach the Mac (CS2 fails), everything Northstar sends ChatGPT crosses the relay: per-turn notes, the start pack (up to 12,000 characters), Book slices and fetched items (up to 8,000 characters each, at most 200 a day), drawn from the user's personal items on any connector (Claude content too if ARCH DQ-3(b) is yes). **(a)** OpenAI's Secure MCP Tunnel only: no new reader; needs an OpenAI Platform organization and API key the user creates, under its terms. **(b)** Also allow a Cloudflare tunnel fallback: Cloudflare can read everything in transit, and its sign-in emails the user a code; by default only items whose sources OpenAI already holds cross it | A new party may read the user's items in transit (RISK 13); the tunnel needs an account and key only the user can create | **(a)**; (b) only if (a) fails (ARCH's recommendation). No relay storage. Nothing ships on it until the user answers |
| CQ6 | May Northstar **offer**, as an extra option, continuing a long session in a local Work thread or Codex? Using either **instead of** Chat would be a reframe | Touches the surface scope (GOAL §4.6) | **Offer only as an opt-in choice** in the restart menu. Chat remains the target surface and is evaluated on its own |
| CQ7 | Which **plan** (Plus or Pro) and which **app** (new ChatGPT or ChatGPT Classic) do you use for Chat? | Facts only the user knows. Plus may have no custom MCP (V1). Computer History is Pro only (V16). Classic may lack plugins (V9) | New app. Plan unknown, so spikes assume **Plus**, the worst case |
| CQ8 | **What a desktop chat adds to memory without the observer.** **Asked as ARCH DQ-4(ii)** (REVIEW FEAS-1, FEAS-4, CLR-1), which covers either desktop app (Claude Desktop chat too, when its click-free spikes fail), only if paths C1 and C2 both fail (§6.2.2). To stay honestly read-only, the per-turn tool stores nothing, so without the widget what a chat establishes does not reach later pins in that same chat. **Option A:** a chat is saved when you approve a save: once per chat if you remember it for that chat, again after a reload or reopen, otherwise at every save. A save is `northstar_note(kind: save_chat)` carrying the unsaved turns, or a widget **Save this chat** click. Skipped or never asked means the chat adds nothing (CR16). **Option B:** no clicks; these chats add **nothing** to memory (neither user-said nor AI-said) unless L1 is on or the user says "remember this", and nothing they established reaches the next chat. **Option W:** declare the per-turn tool a write: one approval per chat and after each reload, then capture and focus work as on a click-free app; a skipped approval loses the pin too. Under A and B, the per-turn pin needs no click | Option A is a per-chat action (§4.1, §4.3), and its capture waits on a save. Option B gives up §4.2, automatic capture (§4.3) and cross-session continuity (§3.3) on a first connector. Option W puts the pin behind a per-chat approval | Paths C1 or C2 if a spike passes. Otherwise **no option is assumed**: drafts carry A, B and W as a switch, and nothing ships until the user answers. ARCH's recommendation: B with the observer (DQ-1 read); otherwise A. Option B is labelled as narrowing §4.2 and §4.3 on this surface. *(The earlier assumption, "read-only by default; write only when the user says 'remember this'", is withdrawn because it narrowed §4.2 and §4.3 without the user.)* |

**No reframe is adopted in this document.** Replacing Chat with Work, Codex or the web would be a reframe, and it is asked as CQ6, not assumed.

---

## 12. Capability summary rows

Vocabulary from §1.4. One row per layer configuration. SPINE §4.10 gives the same rows in the spine's levels, and splits each L0 and L0+ capture cell into what reaches the core and what is persisted, by capture path (§6.2.2).

| Configuration | capture_user | capture_ai | inject_turn | inject_start | check_reply | restart | audit_truth | write |
|---|---|---|---|---|---|---|---|---|
| **L0** (CS2, CS3, CS4 fail) | model_reported (when called) | model_reported (previous reply, points with quotes) | model_pulled | model_pulled + static boot line | after_the_fact, model_reported, one turn late | model_pulled suggestion; user opens a new chat; pack model_pulled | after_the_fact (one-off export) | model_pulled (write tool; approval per conversation or "Always allow", Unv); Pro may be read-only |
| **L0+** (CS4 passes) | model_reported | model_reported | deterministic after mount (hidden) | model_pulled first call, then deterministic | after_the_fact, model_reported; correction delivery deterministic after mount | one tap, deterministic pack (`ui/message` new) | after_the_fact (export) | model_pulled; plus deterministic user corrections in the widget |
| **L0 with hooks in Chat** (CS3 passes; not expected) | deterministic, verbatim | deterministic, verbatim | deterministic | deterministic | before display (`Stop` block) | deterministic | deterministic | deterministic |
| **L1** (+ L0 or L0+) | verbatim (rendered), deterministic | verbatim (rendered), deterministic at reply end | as L0 or L0+ | as L0 or L0+ | after_the_fact, verbatim (seconds) | automatic at reply end only with a yes to UQ-1 (and CS4); else as L0 or L0+ | deterministic, independent, live | deterministic (core writes from capture); model_pulled for notes |
| **L1 + L2** | verbatim (rendered), deterministic | verbatim (rendered), deterministic | deterministic, visible (L2a) or hidden (L0+) | deterministic (L2e, or L2c if accepted) | after_the_fact, verbatim; optional correction turn (L2d, off until UQ-1) | prepared with carry-over (the user sends); automatic only with a yes to UQ-1 | deterministic, independent, live | deterministic |
| **L3** (not recommended) | verbatim, exact, after_the_fact (minutes) | verbatim, exact, after_the_fact | deterministic (L3c) | deterministic (L3c) | after_the_fact | deterministic (L3c) | deterministic, exact | deterministic |

---

## 13. Spikes, in order

The first four decide the layer structure. Run them on the user's real account after approval (GOAL §7). They touch the user's settings and configuration, so each needs the user's go-ahead. **CS1 runs on day 1 of Stage 0, right after the user answers ARCH DQ-2** (the spike go-ahead). If it fails, ARCH DQ-4(i) is asked at once, not at Stage 3.

| ID | Question | Pass / fail and what changes | Cost |
|---|---|---|---|
| **CS1** | On this account: can it add a custom MCP server and save it as a personal plugin (Plugins → + → Add custom MCP server → Create as a plugin; Developer mode at Settings → Security where needed)? Are write tools allowed? Can the plugin bundle a skill? Does the plugin appear in **desktop Chat**? Is it used without `@`? Inside projects? **A scripted "list your tools" turn on turns 2–40, without `@`**, to measure whether the tool is available apart from whether the model chooses it. Is approval per conversation, or is "Always allow" offered? **No-auth against OAuth on the same route:** is "Always allow" offered only for an explicitly connected account (V15)? Each default permission level (Always ask, Allow read actions, Allow low-risk actions, Allow all actions) against `readOnlyHint` and against `destructiveHint: false` with `openWorldHint: false`. **Does a permission remove the per-conversation approval for a declared write tool (path C1)?** Does a remembered approval persist across a reload, an app restart and a new chat? If an approval is declined, does the model still get the read-only pin tool's result? Does Developer mode stop memory saving on Pro? Does the host report multi-participant sessions (a shared project or a group chat)? | Picks route PK-1, PK-3 or PK-4 (§6.2.1). Settles CR3, CR15, CR16, and path C1 (§6.2.2). Adopts OAuth only if it unlocks Always allow. If it fails, ARCH DQ-4(i) is asked at once | 1 hour |
| **CS4** | In **desktop Chat**: does the widget render; does `ui/update-model-context` (audience `["assistant"]`) reach the model on the next turn and on later turns? Test with a random codeword asked at +1, +5 and +20 turns, after an app restart, and with the widget scrolled out of view. **Pass rule as CD-S2:** no tool calls after turn 3, the widget off-screen, a reply within 10 s, and the marker present on ≥ 95% of 20 turns. Does the model echo the widget tag ([CX] §3.4)? Size limit at 1k, 5k and 20k characters. Does `ui/message {target: "new"}` open a Chat conversation? Does `send: false` stage an item? Are thread entrypoints offered? Can the widget reach the local core directly? **Path C2: does the widget get its own call's arguments from tool-input (`ui/notifications/tool-input` or `window.openai.toolInput`) at once, and can it record them through `northstar_widget_record`, a declared write, with no prompt, while the model-facing tool stays stateless? Does OpenAI's published guidance permit it?** | Pass makes L0+ real (the biggest sanctioned gain). Fail leaves L0, and raises the value of L2a. The C2 result decides whether ARCH DQ-4(ii) is needed (§6.2.2) | Half a day |
| **CS3** | Install a trivial, trusted logging hook (`UserPromptSubmit`, `Stop`, `SessionStart`). Send messages in desktop Chat, local Work and Codex | Pass (not expected) makes this surface as strong as Codex | 1 hour |
| **CS2** | Add a stdio test server in Settings → MCP servers. Also test a **personal plugin with a local MCP app** (V4) in **Chat mode** specifically. Does Chat list or call either? | Pass removes the relay. Expected to fail (V5) | 1 hour |
| CS5 | Over 40-turn chats: the tool-call rate r(t) and the first-call rate, with boot lines in different combinations, and with and without an early visible benefit (P5). Log "not offered" and "offered but not called" apart (§6.9). Add time to first token | Sizes CR1 and §6.9. Sets whether L0 can meet the §7.1 bars | 2 days |
| CS6 | Copy fidelity: exact-match rate of copied user messages; quote-verify rate of AI points; omissions (against export or observer text) | Calibrates §7 | 1 day (with CS8 or an export) |
| CS11 | Is `openai/session` stable across a conversation, across app restarts, and between desktop and web for the same conversation? Different across conversations? | Settles session keying | 1 hour |
| CS7 | Secure MCP Tunnel with the personal Platform organization, added through Plugins → Add custom MCP server → Tunnel → Create as a plugin; how the authorization server is reached, since it is not tunneled automatically (V23); TLS-proxy effects, if a proxy is present; latency p50 and p95 (target p95 under 1.5 s); Cloudflare tunnel as fallback; Site → external MCP (PK-3). **Runs in Stage 0; the Sites part runs whatever CS2 shows** | Settles CQ5 (ARCH DQ-4(iii)) and CR4 | Half a day |
| CS12 | In a Temporary chat with plugins on: does the host signal it? Does the model know? | Settles CR11 | 1 hour |
| CS8 | (Observer design owns it.) Accessibility capture of the Electron Chat view: turn boundaries, reply end, role, mode, Temporary flag; fidelity against an export on 20 chats | Needed for L1 | Observer design |
| CS9 | (Observer design owns it.) Composer append on send, new-chat creation, carry-over, collisions with typing and input methods | Needed for L2 | Observer design |
| CS10 | After a week of use: do Northstar phrases appear in the memory summary, per channel (tool results, hidden context, visible blocks)? The hidden channel is measured too, because it rides as a composer attachment on the user's message (CR9) | Settles the vendor-memory policy (§9) | 1 week, passive |

---

## 14. Goal-fidelity check

| Non-negotiable (GOAL §4) | How this design handles it | Where it is at risk |
|---|---|---|
| 1. A system, no rituals | All maintenance runs out of band. One-time setup only. Restart and corrections are optional. Exports are backfill only. Plugin and skill descriptions state relevance to continuing work factually, never as a blanket trigger (§6.2.3) | Per-project boot line (CR10); `@` on each message if the route is not offered automatically (V1; CS1; ARCH DQ-4(i)); under option A, a save approval per chat (again after a reload) or per save; under option W, one approval per chat and per reload (CR16; ARCH DQ-4(ii)) |
| 2. AI-said first-class | AI points captured with quotes; reconciled and scored separately; verbatim through L1 | L0/L0+ capture is not verbatim (CR2). **Under path B, nothing from a chat is persisted, AI-said or user-said** (§6.2.2; SPINE RISK 33) |
| 3. The AI manages it | Steward, Drift Checker and pack compiler run by code; the chat model is never the maintainer | Model-pulled steps on L0 (CR1). Automatic capture holds under paths C1 and C2, and under W once approved. Under option A, content persists only when a save happens (the model calls `save_chat` or the user clicks **Save this chat**) and the user approves; nothing is held in between (CR16). Under path B, capture is off unless the user says "remember this" (ARCH DQ-4(ii)) |
| 4. Two architectures, one core | The connector feeds the core only; the widget links to the human view; packs come from the core compiler | — |
| 5. Drift and continuity, equally | In-session loop (§6.2.6) and cross-session pack (§6.2.7) designed per layer, with measurements for both | CR1, CR5, CR6. Under path B, a ChatGPT chat carries nothing into later chats (SPINE RISK 33). Under paths A and B without the widget, later pins in a chat cannot reflect that chat's own unsaved turns, and those turns get code-only checks (§6.2.2) |
| 6. Product-agnostic core with connectors | Adapter contract only; `openai/session` and channel tags are surface metadata; the pack is cross-surface | Plan gating (CR3); relay (CR4) |
| 7. Robust maintainer | Untrusted tool input; watermarks; reconciliation; observer audit; I5 hardened | No live audit truth on L0 (CR7) |
| 8. Prototype built and evaluated | Spikes ordered; shadow-mode control arm with L1; protocol B replay | Measurement validity (CR12) |

**Scope check.** This document keeps Chat as the target surface. Work, Codex and the web appear only as additional options (CQ6). No requirement is narrowed by this document. Option B of ARCH DQ-4(ii) (CQ8) would narrow §4.2 and §4.3 on this surface; it is labelled as such and waits for the user. The stateless read-only rule decided in review weakens in-session focus on paths A and B when the widget is absent (§6.2.2). That cost is stated, option W removes it at the price of a per-chat approval, and the choice stays with the user (ARCH DQ-4(ii)). Every gap is a risk in §10 or a decision in §11.

---

## 15. Sources

**Project notes (local).** `docs/GOAL.md`; `docs/research/round2/10-integration-surfaces.md` [10]; `11-in-session-drift.md` [11]; `13-robust-ai-maintenance.md` [13]; `14-memory-layer-landscape.md` [14]; `SYNTHESIS.md` (round 2).

**OpenAI and ChatGPT** (all checked 2026-10-08):
- Developer mode and MCP apps: https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt
- Plugins in ChatGPT and Codex: https://help.openai.com/en/articles/20001256-plugins-in-chatgpt-and-codex
- Managing app permissions: https://help.openai.com/en/articles/20001495-managing-app-permissions-in-chatgpt
- ChatGPT Work and Codex: https://help.openai.com/en/articles/20001275-chatgpt-work-and-codex
- Moving to the new desktop app: https://help.openai.com/en/articles/20001276-moving-to-the-new-chatgpt-desktop-app
- macOS app release notes: https://help.openai.com/en/articles/9703738-chatgpt-macos-app-release-notes
- Memory in ChatGPT: https://help.openai.com/en/articles/8590148-memory-faq
- Custom instructions: https://help.openai.com/en/articles/8096356-chatgpt-custom-instructions
- Projects: https://help.openai.com/en/articles/10169521-projects-in-chatgpt
- Export: https://help.openai.com/en/articles/7260999-exporting-your-chatgpt-history-and-data
- Custom GPT retirement FAQ: https://help.openai.com/en/articles/20001519-custom-gpt-retirement-and-migration-faq
- ChatGPT Sites: https://help.openai.com/en/articles/20001339-creating-and-managing-chatgpt-sites ; hosting a plugin: https://help.openai.com/en/articles/20001547-hosting-a-plugin-with-chatgpt-sites
- Plugins (learn): https://learn.chatgpt.com/docs/plugins.md ; MCP: https://learn.chatgpt.com/docs/extend/mcp.md ; Hooks: https://learn.chatgpt.com/docs/hooks ; Computer History: https://learn.chatgpt.com/docs/customization/computer-history ; Desktop app: https://learn.chatgpt.com/docs/app ; Work: https://learn.chatgpt.com/docs/get-started-with-work
- Custom MCP server guide: https://developers.openai.com/api/docs/guides/custom-mcp-server
- Secure MCP Tunnel: https://developers.openai.com/api/docs/guides/secure-mcp-tunnels
- Plugin extensions: https://developers.openai.com/plugins/build/extensions ; spec: https://github.com/openai/mcp-extensions/blob/main/docs/spec.md
- Apps SDK state management: https://developers.openai.com/apps-sdk/build/state-management ; reference: https://developers.openai.com/apps-sdk/reference
- Build plugins: https://developers.openai.com/plugins/build/plugins
- Connect from ChatGPT: https://developers.openai.com/apps-sdk/deploy/connect-chatgpt
- Developer-mode guide (now HTTP 404): https://developers.openai.com/api/docs/guides/developer-mode
- Terms of Use (effective 2026-01-01): https://openai.com/policies/terms-of-use/

**Community and secondary** (checked 2026-10-08):
- Create MCP App on personal accounts (2026-09-28): https://community.openai.com/t/create-mcp-app-missing-from-plugins-menu-on-personal-chatgpt-accounts/1401436
- Developer mode and memory: https://community.openai.com/t/chatgpt-cant-create-new-memories/1358208
- Dreaming coverage: https://www.pcworld.com/article/3158111/chatgpt-new-dreaming-feature-makes-it-way-better-at-remembering-you.html

**Platform**
- Electron accessibility: https://www.electronjs.org/docs/latest/tutorial/accessibility ; Electron fuses: https://www.electronjs.org/docs/latest/tutorial/fuses (checked 2026-10-08)

---

## Fidelity fixes (2026-10-08)

An independent goal-fidelity audit of the spine and the desktop connector docs found the issues below in this document. Each was fixed in place. No non-negotiable was weakened.

| # | Severity | Issue | What changed |
|---|---|---|---|
| 1 | Blocker | With `northstar_context` read-only and writes only on "remember this" (CQ8's old working assumption), a ChatGPT chat at L0 stored only hashes, so it added no user-said or AI-said knowledge and carried nothing into the next chat. §6.2.2 ("never promoted"), §6.2.8, CQ8 and §14 did not show this cost | §6.2.2 now states the cost and splits pin delivery (always read-only) from content capture, with four paths: C1 (one-time permission, V15, spike CS1), C2 (app-only widget write, spike CS4), A (approval per new chat) and B (read-only). It resolves the conflict with SPINE §5.5 explicitly. §6.2.7 and §6.2.8 say what each path persists. CQ8 rewritten with both costs; the old working assumption is withdrawn, no option is assumed, and option B is labelled as narrowing §4.2 and §4.3. CS1 and CS4 gain the path-C questions. CR16, §6.8 and §14 rows 1, 2, 3 and 5 updated. **Spike results are not recorded yet:** CS1 and CS4 touch the user's account and need the user's go-ahead (§13); §6.2.2 holds the place |
| 2 | Major | The pack listed "engagement state" | §6.2.7: no per-concept engagement state; at most dated, attributed engagement events; `reported` goals in a labelled slot (SPINE §4.7, SD-36) |
| 3 | Minor | CQ2's working assumption accepted L2b, an automatic restart that sends | CQ2 now points to SPINE UQ-1: nothing is sent for the user until UQ-1 is answered; L2b prepares but never sends; L2a and L2e only where CS4 fails; L2d off. §6.4's "automatic at reply end" now needs UQ-1's yes |
| 4 | Minor | This document described the superseded control/fidelity-channel adapter contract and its own level words | A note at the top says SPINE §4 supersedes them, with a vocabulary and tool-name map. §1.2 and §12 point to it |

**Questions for the user.** No new question was added here. The capture question is CQ8, asked through SPINE UQ-8(a), and only if spikes CS1 and CS4 both fail.

---

## Consistency fixes (2026-10-08)

A cross-document consistency review found the issues below. Each resolution was adopted as given, in place, without restructuring. No non-negotiable was weakened. No new user question was added.

| ID | Issue | Change in this document |
|---|---|---|
| X01 | Three incompatible MCP tool catalogs across the design set | The CX catalog (CX §1.2, §2; D1–D3) is the one tool contract. The note at the top gains a tool-name map: `northstar_resume` / `_sync` / `_turn` → `northstar_context`; `northstar_correct` → `northstar_note(kind: correction)`; `northstar_page` and the TEXTBOOK read tools → `northstar_book(view)`; `northstar_apply_correction` → `northstar_widget_action`; `action_nonce` is the one name for the click credential. §6.2.2's tool table now follows CX §2.2–§2.5: `northstar_context`'s `readOnlyHint` follows the flags (false only under `per_turn_write`, path C1); `northstar_note` kinds are CX's (no `ai_point`); `northstar_book` added; app-only tools named. Result budgets point to CX §2.7. §0, §4.8, §5 P2, §6.1, §6.2.4, §6.2.6 and §8 use the CX names. The §6.2.3 boot-line drafts use CX §5.3 and §2.8 and name only `northstar_context` |
| X02 | UQ-8(a) option A described as automatic capture, with three different mechanisms | CX D5 adopted: one approval per chat; content held in the cache until `northstar_note(kind: save_chat)`, cued at most every fifth call; unsaved content expires 24 hours after the last call (or at a daemon restart). Changed: §6.2.2 path table (with `capture_mode` per path), the read-only rule, the SPINE §5.5 paragraph, §6.2.7, §6.2.8, §6.8, CQ8 (option A is no longer called automatic), §14 row 3. CR16 now states the extra loss mode, "the model never calls `save_chat`", and links RISK-CX-3 and SPINE RISK 33 |
| X27 | Packaging "Path A–D" collided with write paths A, B, C1, C2 | Packaging routes are now PK-1 to PK-4 in §6.2.1, §6.8, §9, CR3, CS1, CS7 and §14. A, B, C1 and C2 are reserved for the UQ-8(a) write paths |
| X28 | Superseded working assumptions left in the body | §8's daily canary chat, which sent messages, is replaced by the observer's passive self-test, which sends nothing ([OBS] §4.7; CX §6.3). Also aligned to SPINE §11.2 UQ-1 and §4.10: §0 item 6, the §6.5 L2b row (prepared; the user sends), and the §6.8 and §12 restart cells for L1 and L1 + L2 (automatic only with a yes to UQ-1) |

---

## Review revisions (2026-10-08)

The adversarial review's fixes for this document, applied in place. The full review record is [`REVIEW.md`](../REVIEW.md) (§4, §5, §6, §8, §10, Appendix B). No non-negotiable was weakened and no WHAT changed. Where a fix has a cost to the goal, the cost is stated and the choice goes to the user through ARCH §14.

| Finding | What changed here |
|---|---|
| FEAS-1 | §6.2.2: "The read-only rule (flagged for review)" is now "decided in review". Under `per_turn_readonly`, `northstar_context` is **stateless** as [CX] §2.5 defines: no stored content, no message hash, no session state, no queued work, no model call; content-free operational logs only. The held-content cache is deleted, and so is the sentence about merging everything into `northstar_note` (superseded). Path table: C2 records the call's own arguments from tool-input through `northstar_widget_record`, a declared write, with no receipt token; A saves by `save_chat` carrying the unsaved turns, or by a widget **Save this chat** click (preferred), with nothing held in between; B persists nothing; new path W declares the per-turn tool a write with a recurring approval. The SPINE §5.5 paragraph now says the core never holds unsaved turns. The cost is stated: without the widget, a chat's own turns do not reach its later pins, and unrecorded turns get code-only checks. Consequential edits: the tool-name map, §0 item 4, §4.8, §5 P2, §6.2.6 steps 3 and 6, §6.2.7, §6.2.8, §6.8, §8, CR16, CQ8, §14 rows 1, 3 and 5, and the scope check |
| FEAS-2 | §6.2.1: PK-1 and PK-2 merged into one route, **PK-1, custom MCP server saved as a personal plugin** (Plugins → + → Add custom MCP server → Create as a plugin). PK-3 (Sites, any plan per help 20001256) and PK-4 kept. The conflict of official sources is recorded (help 12584461 against the developer guide); CS1 decides; V2 stays community evidence. The bundled skill may be missing on Plus or Pro. CR15 now applies to whichever route needs Developer mode, and CS1 checks memory saving on Pro. Secure MCP Tunnel facts added (personal Platform organization; Plugins → Add custom MCP server → Tunnel → Create as a plugin; authorization server not tunneled). V1, V3, V4 and V23 updated; §0 item 2, CR3, §9 and §14 row 1 follow. CS1 runs on day 1 of Stage 0 after ARCH DQ-2; CS7's Sites part runs in Stage 0 whatever CS2 shows; CS2 tests a personal plugin with a local MCP app in Chat mode |
| FEAS-3 | §6.9: r(t) is split into "tool offered" (relevance gate or `@` on that message) and "model chose to call"; CS5 logs "not offered" and "offered but not called" apart and adds time to first token. CS1 adds a scripted "list your tools" turn on turns 2–40 without `@`. `@` is described per message (§6.8, §14). CR9, §9 and CS10: OpenAI's hidden context is a composer attachment on the user's own message, so "hidden is safer for vendor memory" is unproven, and CS10 measures the hidden channel too (FEAS smaller issue) |
| FEAS-4 | §6.2.2 C1 row: "Always allow" only for an explicitly connected personal account; CS1 tests no-auth against OAuth and adopts OAuth only if it unlocks Always allow; per-app "Allow low-risk actions" preferred over the account default; Northstar only advises (SD-16); install guidance checks for an "Always ask" default. Path A: one approval per chat if remembered, again after a reload or reopen, otherwise one per save. CR16, §4.8 and the `northstar_note` row add the reload case. CS1 adds each default permission level against the annotations and persistence across reload, restart and new chat |
| FEAS-5 | §6.2.4: the widget pushes on every host signal (tool result, host-context change, tool-input notices, focus, resize, visibility), visible or not; a visibility-independent re-push timer is best effort; each push carries a widget tag the model may echo ([CX] §3.4). CS4 gains the CD-S2 pass rule (no tool calls after turn 3, widget off-screen, reply within 10 s, marker on ≥ 95% of 20 turns) and the echo check |
| SEC-6 | Device-specific facts removed: the §1.1 "App installed on this Mac" row (path, bundle ID, version) is now a generic product fact; the proxy vendor is gone from the §3 access notes, §6.2.1, CR4 and CS7 (now "TLS-proxy effects, if a proxy is present"). Also removed: the installed build date (§6.4) and "installed on this Mac" (CQ7) |
| SEC-7 | Merged into FEAS-1: no kept cache, no model call on unrecorded turns, content-free records. `openWorldHint` stays false (CS1 tests `destructiveHint: false` with `openWorldHint: false`). CS1 also checks whether the host reports multi-participant sessions (SEC smaller issue) |
| SEC-9 | CQ5 is asked as ARCH DQ-4(iii), with the list of what crosses the relay and options (a) Secure MCP Tunnel only, (b) also a Cloudflare fallback. The vendor choice moves there from ARCH R16. §6.2.1 relay options point to it |
| CLR-1 | CQ8 is asked as ARCH DQ-4(ii), which covers either desktop app, with options A, B and W. §6.2.3 adds: plugin and skill descriptions state relevance to continuing work factually, never as a blanket trigger |
| BOOK-2 | Landed at the final gate. §6.2.2 `northstar_context` arguments add `body` (≤ 1,500 chars on explanation or example points), `this_reply_points` (the closing call, recorded only through a declared write) and `widget_tag` (CX §2.3). The result example is rewritten in IS §8.2 style: third person, reported user items labelled, no commands |

**Questions for the user.** No new question is added here. This document's CQ5 and CQ8 are asked as ARCH DQ-4(iii) and DQ-4(ii); the `@`-on-every-message case is in ARCH DQ-4(i).

---

## Final-gate fixes (2026-10-08)

Each is a HOW change; no non-negotiable is weakened.

| Finding | What changed |
|---|---|
| BOOK-2 | §6.2.2 arguments and result example (row above) |
| FEAS-2 naming | The one ChatGPT packaging route is "PK-1 (custom MCP server saved as a personal plugin)" everywhere, as in CX §1.2 and §5.1; "PK-1/2" is retired (§0 map, §6.2.1, review row FEAS-2) |
