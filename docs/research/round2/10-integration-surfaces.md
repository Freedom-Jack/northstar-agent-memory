# Integration surfaces: what a third-party memory system can actually do on each AI surface (October 2026)

Track 10, round 2. Written 2026-10-07. This note is checked against `docs/GOAL.md`, which overrides it. Where the evidence says part of the goal cannot be met on a surface, the gap is stated as a **risk**. It is never replaced with a smaller goal.

**Method.** I read vendor docs directly where I could: claude.com/docs, code.claude.com, support.claude.com, developers.openai.com, learn.chatgpt.com, Chrome and Apple developer docs. I read the source code of three open-source extensions and one Claude Code memory plugin through the GitHub API. I used community threads and practitioner write-ups only where no primary source exists, and those claims are labelled.
- Some OpenAI Help Center pages and the live OpenAI Terms of Use returned HTTP 403. MemoryPlugin's site failed TLS verification (expired certificate). For those sources I relied on search snippets or archived copies, and the text says so.
- Product facts are as of the fetch date, 2026-10-07, unless another date is given.
- "(unverified)" means I could not confirm the claim from a primary source.

Round-1 constraints this note builds on: attribution, speaker classification and stance [08]; context rot and progressive disclosure [07]; extraction losses and assistant-said blind spots [03].

---

## Questions this track answers (tied to GOAL.md)

| # | Question | GOAL.md anchor |
|---|---|---|
| Q1 | On each surface, can the system **capture what the user said and what the AI said**, verbatim and with attribution? | §3.1 shared core; §4.2 AI-said is first-class |
| Q2 | Can it **inject context on every turn**, so a long chat stays on the user's goal? | §3.3 in-session focus; §4.5 |
| Q3 | Can it **inject context at chat start**, so a new chat continues earlier work? | §3.3 cross-session continuity; §4.5 |
| Q4 | Can the model **call our tools**? Does it do so on its own, or only when told? Can we **write back**? | §4.3 the AI manages it |
| Q5 | What are the plan requirements, latency, reliability, ToS exposure and breakage risk? | §4.6 surfaces; §4.8 a working prototype |
| Q6 | How does a third-party system coexist with the vendors' own memory? | §3.3; injection and sycophancy constraints in §5 |
| Q7 | What gives the maintainer an **independent ground truth**, so capture errors are detectable? | §4.7 a robust maintainer |

Surfaces in priority order (GOAL §2, §4.6):
1. claude.ai (web) and chatgpt.com (web).
2. Claude Desktop (chat, and the Code tab), ChatGPT Desktop (macOS), Claude Code, Codex.

---

## Key findings

### A. Claude surfaces

**1. A remote MCP "custom connector" reaches every Claude surface from one server. It is a sanctioned, low-risk channel, but the model decides when to use it.** (claude.com docs and support.claude.com, fetched 2026-10-07)

*Plans:*
- Custom connectors work on Free, Pro, Max, Team and Enterprise. The Free plan can add **one** custom connector.
- On Team and Enterprise, only an Owner adds a connector, or on Enterprise a member with a library-management role. Members then connect individually.

*Hosting:*
- Claude connects "from Anthropic's cloud infrastructure, rather than from your local device", on every client. The server must therefore be reachable from Anthropic's IP ranges.
- For local development, Anthropic's testing guide recommends Cloudflare Tunnel or ngrok.
- Anthropic's own MCP tunnels are a research preview for Enterprise organizations by request, so they are not an option for a personal account.

*Protocol:*
- Streamable HTTP is supported; legacy HTTP+SSE still works but is being deprecated.
- Auth can be OAuth (DCR, Claude's published client identity, or your own client), "No sign in", or static request headers. Header auth is in beta for a limited set of organizations.
- Claude supports **tools, prompts and resources**, text and image tool results, and text and binary resources.
- It does **not** support resource subscriptions, sampling, or "advanced or draft capabilities".

*Limits:*
- On claude.ai and Desktop, a tool result can be about 150,000 characters and a tool call can run for 240 s.
- Claude Code allows 25,000 tokens of MCP output by default (configurable).

*Use in a chat:*
- Connectors work "on the web, desktop, and mobile". The user turns each one on per conversation from the **+ → Connectors** toggle.
- Claude asks before it calls a tool (**Allow once** or **Always allow**). Each tool can be set to Always allow, Needs approval or Blocked.
- Research mode can call connector tools without asking.
- Connectors added on claude.ai also appear in Claude Code when it is signed in with the same account.

*Gaps in the docs:*
- I found no documentation of whether a connector is on by default in a new chat, or how connectors behave inside Projects (both unverified).

**2. Claude's MCP Apps can feed context into "the next turn". This is the only sanctioned way to inject changing context on claude.ai, but it is new and its persistence across turns is unverified.**
- The MCP Apps extension (SEP-1865, marked Stable 2026-01-26) defines `ui/update-model-context`. The host "SHOULD provide the context to the model in future turns". It "MAY defer" the update until the next user message. Each update overwrites the previous one.
- Claude's docs describe widgets that "independently push model-context updates, the data a widget feeds into Claude's context for the next turn". Every tool call that renders an app mounts a new iframe. Older copies stay live unless the developer adds a supersession pattern; Claude's docs describe one using `BroadcastChannel`.
- claude.ai web renders MCP Apps, and so do Desktop and iOS.
- **What this means.** Once the model has called a Northstar tool once in a chat, a Northstar widget could keep a small focus anchor in the model's context, refreshed from the server, without further tool calls.
- **Unverified:**
  - whether the context is re-sent on every later turn or only the next one;
  - whether it survives a page reload;
  - how much text the host accepts.

**3. Claude plugins bring a connector and a skill into chat together. Hooks in a plugin are ignored in chat.** (claude.com/docs/plugins/platform-support)
- In chat (web, desktop and mobile), a plugin's **skills load** and its **remote MCP server** is offered on the plugin's Connectors tab.
- Hooks, agents and local MCP servers are "Ignored" in chat. Cowork and Claude Code load them.
- A plugin installed on the claude.ai account is synced into Claude Code at the next session start.
- **What this means.** One Northstar plugin can ship a skill that tells Claude when to call Northstar, the connector itself, and Claude Code hooks, all as one install.

**4. Claude Desktop chat adds local MCP, but it has no hooks and cannot run browser extensions.**
- Local servers run over stdio. They are packaged as `.mcpb` desktop extensions or added in `claude_desktop_config.json`.
- A local server needs no public HTTPS.
- Desktop chat gets the same remote connectors and MCP Apps as the web.
- Advanced Research cannot call local MCP tools.
- Nothing documented gives a third party a per-turn hook into Desktop chat. Desktop is an app, not a browser, so a browser extension cannot reach it.

**5. Claude Code, including the Desktop app's Code tab, has the most complete integration surface: deterministic hooks on both sides of every turn.** (code.claude.com/docs/en/hooks, fetched 2026-10-07)

*Where hooks fire:* "Claude Code fires the same hook events wherever it runs: sessions in the terminal, IDE extensions, the Desktop app, and cloud sessions."

*Injecting on every turn (`UserPromptSubmit`):*
- It fires on every prompt, including turns Claude Code starts on its own.
- It receives the verbatim `prompt`, with pastes wrapped in `<pasted_content>` markers.
- Its `additionalContext` is injected as a system reminder that the user does not see as a chat message.
- `additionalContext`, `systemMessage`, `initialUserMessage` and plain stdout are each capped at 10,000 characters. Anything longer is saved to a file and replaced by a 2,000-character preview, and Claude is not asked to read the file.
- The default timeout is 30 s.

*Injecting at session start (`SessionStart`):*
- Matchers are `startup`, `resume`, `clear`, `compact` and `fork`.
- `compact` fires after auto or manual compaction, so the goal can be re-injected exactly when in-session drift is most likely.

*Around compaction:*
- `PreCompact` receives the trigger and any `/compact` instructions. It can block compaction.
- `PostCompact` receives `compact_summary`.

*Capturing the AI's side:*
- `Stop` and `SubagentStop` receive `last_assistant_message`, the final assistant text. The docs say to use it instead of the transcript, because "the transcript file isn't guaranteed to include the final message at Stop time".
- A `Stop` hook can force Claude to continue, up to 8 times in a row by default.
- `MessageDisplay` sees assistant text but is display-only.

*Other details:*
- `transcript_path` points to a JSONL file that is written asynchronously and "may lag".
- Hook types are `command`, `http`, `mcp_tool` (call an MCP tool deterministically), `prompt` and `agent`. Agent hooks are marked experimental.
- The docs warn that injected text "framed as out-of-band system commands can trigger Claude's prompt-injection defenses", and recommend factual statements instead.
- Prior art: thedotmack/claude-mem (about 97.8k GitHub stars, last pushed 2026-10-07) registers `SessionStart` (startup, resume, clear and compact), `UserPromptSubmit`, `PostToolUse`, `Stop` and `SessionEnd`. This is the pattern Northstar needs.

### B. OpenAI surfaces

**6. On ChatGPT web, a custom MCP server becomes a "plugin" through Developer mode. It works, but has more friction than on Claude, and plan eligibility is unclear.**

*What an MCP server is in the UI (as of 2026):*
- "Plugins" now package skills and MCP apps. The Plugin Directory replaced the App Directory in July 2026 (secondary source).
- Simon Willison's TIL (2026-07-29) describes the user flow:
  - turn on Developer mode under Security and login, a toggle labelled "ELEVATED RISK";
  - add the server under Plugins → + → New Plugin;
  - then **select the plugin in each chat** through + or `@`.
- MCP tools are not available in Advanced Voice mode.
- OpenAI's docs say custom servers are added on **ChatGPT web**.

*Protocol:*
- Transports are SSE and streaming HTTP.
- Auth can be OAuth (static credentials, CIMD or DCR), none, or a mixed mode.
- The MCP `instructions` field is read. OpenAI advises keeping its first 512 characters self-contained.

*Write confirmations:*
- Tools without `readOnlyHint` count as writes and need confirmation.
- An approval can be remembered only "for a given tool for a conversation". "New conversations will prompt for confirmation again", and so will a refreshed conversation.

*Tunnel option:* OpenAI's **Secure MCP Tunnel** (around 2026-05-27, secondary source) lets a local stdio or HTTP server serve ChatGPT through an outbound-only `tunnel-client`. It requires Platform-organization "Tunnels" permissions and a tunnel tied to the ChatGPT workspace. Whether a personal Plus or Pro account can use it is unverified.

*Plans conflict:*
- OpenAI's own Help Center versions, seen as snippets because the page returned 403, say full MCP with write actions is for Business, Enterprise and Edu.
- Other versions and third-party guides say Plus and Pro, or say Pro is read/fetch-only.
- Free is excluded. Willison's personal account worked in July 2026.
- **Treat this as unverified for the user's account.**

*Known defects (community reports, not vendor statements):*
- Custom apps stopped working inside ChatGPT **Projects** around the December 2025 rename. The forum thread was still unresolved at its last post (2026-02-24).
- Several users report that memory is off or cannot be saved while Developer mode is on (unverified).

**7. OpenAI's new MCP Extensions add a per-thread side panel and hidden "background context". At launch they cover the desktop app and the Work browser, not classic chatgpt.com chat.** (developers.openai.com/plugins/build/extensions; github.com/openai/mcp-extensions, repository created 2026-09-29)

*What they add:*
- **Thread entrypoints**: a Northstar panel opened beside any conversation, one instance per thread.
- `ui/update-model-context` items that are idempotent, replace earlier ones, and appear as removable composer attachments. Items marked `annotations.audience: ["assistant"]` are **hidden from the user** but still sent to the model.
- Composer at-mentions, available on desktop only.

*Where they work:* The spec's support table "describes expected support at DevDay launch. **Web refers to the Work browser; classic ChatGPT is excluded.**" The extensions page says web support is "coming soon to ChatGPT Free and Go users".

*Classic chat:* For classic chat, the Apps SDK documents widget state with a `modelContent` field ("Text or JSON the model should see"), and names `ui/update-model-context` as "the portable MCP Apps mechanism for updating model-visible context". How these persist across turns is unverified.

**8. Custom GPTs are being retired on 2026-12-11, and with them the one ChatGPT feature that applied a third party's instructions to every message.**
- OpenAI's retirement FAQ, seen as snippets, says "a GPT applied its instructions to every message in its chat, while a skill runs when ChatGPT decides it fits".
- GPT actions do not migrate. They must be rebuilt as an app or MCP server.
- Custom instructions and project instructions still apply every turn, but they are static text that only the user's UI can change.

**9. In October 2026, the ChatGPT desktop app hosts Codex, and its local Work and Codex threads support local MCP and hooks.** (learn.chatgpt.com)
- The ChatGPT desktop app offers Chat and Work modes plus Codex. It "share[s] MCP configuration for the same Codex host": stdio and Streamable HTTP servers configured in Settings → MCP servers or in `~/.codex/config.toml`.
- Codex hooks are "enabled by default":
  - `UserPromptSubmit` receives `prompt`, and its stdout or `additionalContext` is "added as extra developer context";
  - `SessionStart` matchers are `startup`, `resume`, `clear` and `compact`, and after compaction "matching `compact` hooks run before the next model request";
  - `Stop` receives `last_assistant_message`;
  - `PreCompact` and `PostCompact` exist;
  - `transcript_path` is provided but its format "isn't a stable interface";
  - non-managed hooks must be trusted, and trust is tied to the hook's hash.
- The docs say hooks "continue to work in local-only Work and Codex threads".
- Whether hooks run in plain **Chat** mode of the desktop app is unverified. Chat mode uses plugins, as on the web.
- Codex keeps its own local memories, off by default.
- **Computer History**, available to Pro on macOS, turns activity read through Accessibility into memories.

### C. Browser extensions: what they really do, and their limits

**10. Every memory extension I inspected captures and injects through the page itself, with no vendor API, and the best-known one has been abandoned.**

*Mem0/OpenMemory* (`mem0ai/mem0-chrome-extension`, v1.3.17): **archived**, last push 2026-03-23. Reading its source code shows:
- **Capture:** when the user sends a message, it reads the user's message plus the **last two messages from the DOM**, using Tailwind class selectors such as `.flex.flex-col.text-sm.md\:pb-9` and `[data-message-author-role]`. It posts them to `api.mem0.ai/v1/memories/` with `infer: true`.
- **Injection:** it rewrites the composer's `innerHTML` to append a visible green "memories" block, so the injected text becomes part of the user's message.
- It does no network interception.

*Supermemory:*
- Its extension added Tab-to-insert memory suggestions next to the composer on Claude and Gemini (changelog, 2026-07-22). Insertion is manual.
- It also added a guided importer for ChatGPT, Claude, Grok and Gemini (2026-06-24).
- For ChatGPT it recommends its MCP server through Developer mode, plus a custom instruction asking ChatGPT to use it.

*MemoryPlugin* (vendor-stated, read through search snippets):
- It runs a background sync per platform that pulls new conversations about once an hour, with no export files. This needs the user to be signed in to both MemoryPlugin and the chat site in the same browser.
- Injection needs "one-click activation per chat".
- It works in Chrome and Safari, and its MCP server does recall only. "Syncing always runs through the extension."
- A separate macOS app syncs Claude Code, Codex and Cursor logs from `~/.claude`, `~/.codex` and `~/.cursor`.

*Exporters show the reliable read path.*
- `pionxzh/chatgpt-exporter`, about 2.8k stars and pushed 2026-09-26, gets a bearer token from `/api/auth/session`. It then fetches `/backend-api/conversation/:id`, the full branched tree (`mapping`, `current_node`).
- Claude exporters fetch `/api/organizations/{org}/chat_conversations/{id}?tree=True&rendering_mode=messages`.
- Both are undocumented internal endpoints and break without notice. One Claude exporter's store listing notes breakage after an artifact-format change.

**11. Manifest V3 decides how an extension can do this.** (Chrome docs, fetched 2026-10-07)

*What MV3 cannot do:*
- `webRequest` exposes request bodies but **no response bodies**.
- Blocking `webRequest` is limited to policy-installed extensions.
- `declarativeNetRequest` can block, redirect and edit **headers**, but not bodies.

*How to read the stream anyway:*
- An extension cannot read a streamed answer from the network layer.
- It must either read the DOM, or patch `window.fetch` in a content script with `"world": "MAIN"`. "The host page can access and interfere with the injected script", which also means the page can detect it.
- To rewrite an outgoing request body, the same MAIN-world patch is the only route.

*Safari on macOS:*
- A Safari web extension must ship inside a containing app.
- Signing with Developer ID outside the App Store reportedly works from Safari 18.4 (Apple forum replies). Otherwise "Allow unsigned extensions" resets every time Safari quits.
- Whether Safari supports the manifest's MAIN-world key is unverified. A forum answer credits Safari 16.4 with MAIN support in `registerContentScripts`.

*Reach:* Extensions do not reach Claude Desktop, ChatGPT Desktop or the mobile apps.

**12. ToS: both vendors' consumer terms prohibit automated extraction. A capture extension is ToS-grey. A connector or hook is not.**
- OpenAI's Terms of Use (copy effective 2024-12-11; the live page returned 403) prohibit:
  - "Automatically or programmatically extract data or Output";
  - "Modify, copy, lease, sell or distribute any of our Services";
  - "bypass any protective measures".
- Anthropic's Consumer Terms (effective 2025-10-08) prohibit:
  - access "through automated or non-human means, whether through a bot, script, or otherwise", except through an API key or where Anthropic explicitly permits it;
  - "crawl, scrape, or otherwise harvest data".
- I found **no enforcement action** against memory or export extensions. Mem0, MemoryPlugin, Supermemory and several exporters operate publicly. That is absence of evidence, not permission.

### D. Official history exports and vendor memory

**13. No vendor offers a consumer API for chat history. Exports are manual and slow.**
- **Claude:** Settings → Privacy → Export data, from web or Desktop only. The emailed link expires after 24 h. **Team and Enterprise members cannot export; only the Primary Owner can.** Round 1 found that exports carry no link between conversations and Projects [08].
- **ChatGPT:** the export can take "up to 7 days" to arrive, and the link expires after 24 h.
- Both exports contain both sides of every conversation and are full snapshots, so ingestion must be idempotent [08].

**14. Vendor memory in 2026 is automatic, scoped and visible, and it will overlap with Northstar's injections.**

*Claude* (support.claude.com, fetched 2026-10-07):
- Memory is on by default for Free, Pro and Max. On Team and Enterprise an admin must enable it.
- The "new experience" saves memory "as individual topics while you chat". The legacy experience used a synthesis rebuilt every 24 h; its export window closed 2026-09-09.
- Memory is project-scoped.
- Past-chat search (Pro and above) appears as visible tool calls with citations.
- Incognito chats are neither saved nor searched.
- "Deleting a conversation doesn't remove memory entries generated from it."
- Import and export are experimental and work by copy-paste.

*ChatGPT:*
- "Dreaming" arrived on 2026-06-04 (secondary sources). It is a background synthesis into an editable memory summary that is "automatically updated … as you chat".
- "Don't mention this again" reduces references to a detail but "does not delete the information".
- Reference chat history now cites the past chats it draws on.
- Temporary Chats neither use nor create memories.

*Third-party access:* Neither vendor has a third-party write API into its memory. Claude Code memory files (`CLAUDE.md`, auto memory) and Codex `AGENTS.md` are plain files we can write. Codex memories are "generated state", not meant for hand editing.

### E. Reliability evidence relevant to the injection channels

**15. Asking the model to call a tool every turn is the weakest channel, and long chats make it weaker.**
- **No vendor publishes reliability data** for instruction-triggered tool calls.
- Practitioner reports agree on three points:
  - a tool spec alone did not get Claude to store memories (mcp-server-memory-file README);
  - "MCP servers cannot force clients to call tools at session start";
  - even hook text plus CLAUDE.md is "not perfect", with occasional skips.
- Claude Code's docs treat CLAUDE.md as "context, not enforced configuration".
- The research is consistent with this:
  - Li et al. (COLM 2024) measured significant **instruction drift within 8 rounds** for LLaMA2-70B-chat and GPT-3.5.
  - Laban et al. (2025, 200,000+ simulated conversations) found a **39% average drop** from single-turn to multi-turn. Repeating all prior user turns on every turn ("snowball") **recovered only 15–20%**. Giving the whole conversation as one fresh prompt ("concat") scored about **95% of single-turn**. The paper's advice to users: "Consolidate before retrying."
- Implications:
  - Per-turn re-anchoring helps, but only partly.
  - Restarting from a consolidated state is far stronger. That needs chat-start injection, not per-turn injection.
  - A channel that depends on the drifting model choosing to re-anchor fails in exactly the situation it is meant to fix.

**16. Account and network environment may add constraints.**
- If a TLS-inspecting proxy is on the network path, it may block code hosts or break TLS verification.
- If the Claude account is an employer account, and that account belongs to a Team or Enterprise organization (unverified), then:
  - the user **cannot add custom connectors** (an Owner must);
  - the user **cannot export their own data**;
  - admins control desktop extensions and memory.

### F. Capability matrix (verified 2026-10-07)

Legend:
- **Det** = deterministic: it happens whatever the model does.
- **Model** = only if the model decides to call a tool.
- **Para** = the model paraphrases the content into tool arguments, so it is not verbatim.
- **Static** = fixed text that the system cannot update per turn.
- **Unv** = unverified.

| Surface / mechanism | Capture user | Capture AI | Inject every turn | Inject at chat start | Model calls our tools | Write to Northstar | Plan / tier | ToS / breakage |
|---|---|---|---|---|---|---|---|---|
| claude.ai: remote MCP connector (+ plugin skill) | Model, Para | Model, Para (prior turns only) | Model | Model, or user-picked MCP prompt/resource | Yes, at the model's discretion; approval or Always allow; per-chat toggle | Yes, via tools | Free: 1 connector; Pro/Max self-serve; Team/Ent: Owner adds; needs a public endpoint | Low / low |
| claude.ai: MCP App model context | No | No | Det after first mount (Unv per-turn persistence) | Needs one tool call first | n/a | Via widget → server | As above | Low / medium (new feature) |
| claude.ai: profile or project instructions | No | No | Static | Static | n/a | No | All | Low / low |
| claude.ai: browser extension | Det, verbatim | Det, verbatim | Det (composer or request) | Det | n/a | Yes (extension → core) | Any plan; Chrome-family easy, Safari needs an app wrapper | **ToS-grey / high** |
| Claude export | Batch, verbatim | Batch, verbatim | No | No | n/a | n/a | Not for Team/Ent members | Low / low; slow and manual |
| Claude Desktop chat: local (.mcpb) or remote MCP | Model, Para | Model, Para | Model (+ MCP App, Unv) | Model | Yes | Yes | As connectors; local needs no public HTTPS | Low / low |
| Claude Code and Desktop Code tab: hooks + MCP | Det, verbatim (`prompt`) | Det, verbatim (`last_assistant_message`, transcript) | Det (`UserPromptSubmit`, ≤10k chars) | Det (`SessionStart` incl. `compact`) | Yes, plus deterministic `mcp_tool` hooks | Yes, plus files | Any Claude Code plan | Low / medium (hook API evolves) |
| chatgpt.com: Developer-mode MCP plugin | Model, Para | Model, Para | Model; must select per chat (`@`/+) | Model, after selection | Yes once selected; writes re-confirmed in each new or refreshed chat | Yes | Business/Ent/Edu certain; Plus/Pro conflicting; Free no | Low / medium (beta; Projects broken; memory may be off) |
| chatgpt.com: MCP App or extension model context | No | No | Det after mount (Unv); hidden background context is Work browser/desktop only at launch | Needs one tool call or panel | n/a | Via widget | As above | Low / medium |
| chatgpt.com: custom or project instructions | No | No | Static | Static | n/a | No | All; GPTs end 2026-12-11 | Low / low |
| chatgpt.com: browser extension | Det, verbatim | Det, verbatim | Det | Det | n/a | Yes | Any | **ToS-grey (explicit "programmatically extract") / high** |
| ChatGPT export | Batch | Batch | No | No | n/a | n/a | Personal plans (Business/Ent Unv) | Low / low; up to 7 days |
| ChatGPT Desktop, Chat mode | Model, Para | Model, Para | Model | Model | Plugins as on web | Yes | As web | Low / medium |
| ChatGPT Desktop, local Work/Codex threads | Det (`prompt`) | Det (`last_assistant_message`) | Det (developer context) | Det (`SessionStart` incl. `compact`) | Yes (local stdio MCP) | Yes, plus files | Any; hooks need trust review | Low / medium (Unv for Work threads) |
| Codex CLI / IDE / app | Det | Det | Det | Det | Yes | Yes, plus AGENTS.md | Any | Low / medium (transcript format unstable) |

---

## What this means for the Northstar architecture

1. **[Surface adapters] Every adapter needs two channels. A sanctioned control channel lets the model pull and record. A fidelity channel observes both sides verbatim and injects deterministically.**
   - On Claude Code, Codex and local ChatGPT-desktop threads, hooks provide both channels.
   - On claude.ai and chatgpt.com, the control channel is MCP. The only deterministic fidelity channel is a browser extension (findings 10–12).
   - On Claude Desktop chat and ChatGPT Desktop Chat mode, there is **no fidelity channel** in real time (risk R2).
   - Design the adapter contract so each channel can be missing, and so the core knows which ones were present for each turn.

2. **[Core] Record capture fidelity on every turn: `verbatim`, `model_reported` or `reconciled`.**
   - When a chat model passes "what I just said" into a tool, it is paraphrasing its own output, and the round-1 evidence on self-report is poor [07 MirageBench; 03 Zep −17.7% on assistant-said questions].
   - Model-reported capture is therefore AI-said *about* the conversation. It is never the record of the conversation.
   - When verbatim text arrives later, from the extension, a hook or an export, the core reconciles by platform message ID and keeps both versions.
   - This is the attribution schema from [08] (speaker, holder, stance) with one extra field for the capture channel.

3. **[AI in-session] Define one surface-neutral "focus anchor" artifact, and render it per channel.**
   - What it is: a small, deterministic, ID-cited block (target ≤1.5k tokens; hard limit under 10,000 characters to fit Claude Code). It holds the active goal, what has been established (attributed user-said or AI-said), open questions and conflicts.
   - How it reaches each surface:
     - `UserPromptSubmit` `additionalContext` in Claude Code;
     - developer context in Codex;
     - the composer or request in the extension;
     - `ui/update-model-context` from an MCP App, where that is confirmed to persist;
     - the result of a `northstar_focus` tool call;
     - a static project-instruction fallback.
   - Write it as factual statements, not commands, because of Claude Code's injection-defense warning (finding 5).
   - It must be recomputed from **captured** turns. On surfaces without verbatim capture it can only be recomputed from model-reported capture, which degrades it.

4. **[AI in-session] Use two mechanisms against drift, chosen by the evidence: per-turn re-anchoring, and consolidate-and-restart.**
   - Per-turn re-anchoring recovers only part of the loss (Laban "snowball": 15–20%). A fresh prompt with consolidated state ("concat") recovers about 95% (finding 15).
   - So the in-session subsystem should also produce a **handoff pack**: a consolidated state for the current task that can seed a fresh chat.
   - On hook surfaces this is automatic at `compact`.
   - On the web, the extension can open a new chat with the pack inserted. Whether that needs the user's click is a design decision (D7). It must not become a required ritual.

5. **[AI cross-session] The chat-start pack uses the strongest channel available on each surface.**
   - `SessionStart` (startup, resume, clear, compact) on Claude Code and Codex.
   - Automatic insertion by the extension in a new chat on claude.ai or chatgpt.com.
   - Otherwise, a static boot line in profile or project instructions ("Northstar is connected; call `northstar_resume` first"), backed by an MCP **prompt** the user can pick on claude.ai.
   - Vendor-memory import is a low-fidelity seed only, never the channel of record [08].

6. **[Surface adapters] One remote MCP server, packaged as a Claude plugin and as a ChatGPT plugin, covers the most surfaces through sanctioned channels.**
   - Claude: web, Desktop, mobile, Claude Code and Cowork (finding 1). ChatGPT: web, Desktop Chat and Work, and mobile (finding 9; learn.chatgpt.com/docs/plugins).
   - Requirements:
     - a public HTTPS endpoint that Anthropic's cloud and OpenAI can reach;
     - OAuth, or a secret-URL or header scheme;
     - Streamable HTTP;
     - tool results kept well under 150k characters;
     - distinctive tool names (`northstar_*`), so they are not confused with vendor memory tools.
   - Read tools get a truthful `readOnlyHint`. Write tools stay few, because ChatGPT re-confirms them in every new conversation.

7. **[Surface adapters] Build the browser extension as two separable modules, so the riskier one can be switched off.**
   - (a) **Capture.**
     - Prefer reading the conversation after each turn completes: either the DOM once streaming ends, or the conversation JSON the page itself loads.
     - Avoid a live SSE tee, because it is more fragile and more exposed.
     - Capture both sides verbatim, keep branch and regeneration structure, classify the speaker (detect pastes), and skip Incognito and Temporary chats.
   - (b) **Injection.**
     - Default to a visible, collapsible block appended in the composer.
     - Rewriting the request in the MAIN world is optional.
     - Include a **shadow mode** (capture only, no injection) so the drift measurement GOAL §6 requires can compare the same kind of chat with and without Northstar.
   - Ship Chrome-family browsers first. Safari needs an Xcode-wrapped app; Developer ID distribution reportedly works from Safari 18.4.

8. **[Maintainer] Capture completeness must be checkable without trusting any single agent.**
   - Each adapter keeps a watermark per conversation: message count and last platform message ID.
   - The maintainer compares those watermarks against an independent source:
     - Claude Code and Codex transcripts;
     - the extension's post-turn conversation fetch;
     - an official export, when one exists.
   - Selector breakage shows up as a capture-rate anomaly, for example turns rendered but not captured, or a sudden drop in AI-said text length. A daily canary conversation exercises each adapter.
   - The chat model's own tool calls are never the maintainer. They are untrusted inputs, consistent with the offline maintainer design in round 1 [03 §6].

9. **[Core / maintainer] Run every injection path through the round-1 injection defences.** Injected text is data in labelled delimiters, and captured AI or web text never becomes an instruction [07 Impl. 9]. Page scripts can detect and tamper with MAIN-world code (finding 11), so keep secrets out of it and use minimal host permissions.

10. **[AI cross-session / core] Coexist with vendor memory by dividing the work.** Northstar injects goal and focus state with provenance and supersession. Vendor memory handles personalization. Ingest vendor-memory text only as "assistant-asserted about the person" [08]. Expose a policy per surface (vendor memory on, off, or Northstar-only in scoped Projects), because double injection raises over-personalization and sycophancy risk [07 F6].

11. **[Human structure] Make injection visible on the surfaces, but build the human view separately.** The extension panel or an MCP App shows which item IDs Northstar injected [07 F9]. The navigable map of what was learned and what to learn next lives in Northstar's own interface, built from the core.

### Recommended adapter strategy per surface, and which goal requirements each can meet

Columns are GOAL requirements:
- **Cap-U**: capture what the user said.
- **Cap-AI**: capture what the AI said, verbatim (§4.2).
- **Focus**: per-turn in-session focus (§3.3).
- **Cont**: cross-session start (§3.3).
- **Auto**: AI-managed with no user action per chat (§4.3).
- **Audit**: independent ground truth for the maintainer (§4.7).

| Surface | Recommended adapter | Cap-U | Cap-AI | Focus | Cont | Auto | Audit |
|---|---|---|---|---|---|---|---|
| claude.ai (web) | Extension (capture + visible injection) **+** Northstar plugin (connector + skill) **+** a one-line boot in profile instructions | Met (extension) | Met (extension); Partial without it | Met (extension, deterministic); Partial via MCP/MCP App | Met | Met after one-time install, if the connector defaults to on (Unv) | Met (post-turn fetch; export optional) |
| chatgpt.com (web) | Extension as **primary** **+** Developer-mode plugin as secondary (plan permitting) **+** custom-instruction boot | Met (extension) | Met (extension); Partial without it | Met (extension); **Not met** without it (plugin needs per-chat selection) | Met (extension); Partial without it | Met with extension; **Not met** without it (per-chat `@`, per-chat write approval) | Met (post-turn fetch); export up to 7 days |
| Claude Desktop (chat) | Same Northstar plugin; local `.mcpb` variant for the local core; capture backfilled from the web-side sync of server-stored conversations | Partial (Para live; verbatim later via sync) | Partial (verbatim only after the fact) | **Partial**: model-dependent (+ MCP App, Unv) | Partial: model-dependent | Partial | Met after the fact |
| Claude Desktop (Code tab) and Claude Code | Claude Code plugin: hooks (`SessionStart`, `UserPromptSubmit`, `Stop`, `PreCompact`/`PostCompact`, `SessionEnd`) + MCP + a CLAUDE.md pointer | Met | Met | Met | Met | Met | Met (transcript) |
| ChatGPT Desktop (macOS) | Chat mode: ChatGPT plugin. Work/Codex local threads: Codex hooks + local MCP (shared `config.toml`) | Chat: Partial. Local threads: Met | Chat: Partial. Local threads: Met | Chat: **Not met** to Partial. Local threads: Met (Unv for Work) | Chat: Partial. Local threads: Met | Chat: Partial. Local threads: Met | Chat: export only. Local threads: Met |
| Codex (CLI/IDE/app) | Codex hooks (`UserPromptSubmit`, `SessionStart` incl. `compact`, `Stop`) + MCP + an AGENTS.md pointer; rely on `last_assistant_message`, not the transcript format | Met | Met | Met | Met | Met (after trusting the hooks) | Met |

---

## Options and trade-offs the design must decide

**D1. How the web extension captures.**

| Option | Pros | Cons |
|---|---|---|
| (a) DOM read after streaming ends | Least invasive | Breaks on UI changes; loses branch structure |
| (b) Reading the page's own conversation JSON from internal endpoints after each turn | Exact text; branches and regenerations; message IDs for idempotency | Undocumented endpoints; most clearly what both ToS clauses describe |
| (c) MAIN-world fetch tee of the SSE stream | Real-time | Most fragile; most detectable |
| (d) No extension: MCP self-report plus periodic export | ToS-clean | Fails Cap-AI verbatim in real time, and Focus on ChatGPT |

These can be mixed, for example (a) or (b) live with (d) as backfill.

**D2. How the web extension injects.**
- (a) A visible block appended to the composer. It is honest and user-correctable, but it stays in the transcript, which affects capture and attribution.
- (b) An invisible request rewrite. It feels cleaner but is ToS-riskier ("modify", "bypass protective measures") and still stored server-side.
- (c) No extension injection: rely on MCP App model context, if the spike shows it persists, plus tool calls.

**D3. Hosting.**
- (a) A small public MCP front end in the cloud, with the core in the cloud. Always available, but it is a third-party copy of all conversations.
- (b) A local core reached through a tunnel (Cloudflare or ngrok for Claude; Secure MCP Tunnel for ChatGPT, where available). Private, but down whenever the laptop sleeps.
- (c) Local only: extension, hooks and Desktop local MCP. It gives up the claude.ai and chatgpt.com MCP channel.

A TLS-inspecting proxy, if present (finding 16), also affects this choice.

**D4. Browser target.** Chrome-family first: the cheapest path, with MAIN world documented. Safari first, if that is the user's browser, means an Xcode app plus Developer ID signing. *The user's browser is unknown, so this needs an answer.*

**D5. Vendor-memory policy per surface.** Choose among: leave vendor memory on (risk of double injection); turn it off where Northstar is active; or use Projects where vendor memory is scoped. Also decide how ChatGPT Developer mode's possible effect on memory changes this choice.

**D6. Account.** A personal account, or an employer account? This decides whether custom connectors and exports are available at all (finding 16). It also decides data ownership.

**D7. Consolidate-and-restart.** Should Northstar open a fresh chat automatically with a handoff pack when it detects drift? Options: fully automatic; one suggested click; or off. Each is a trade-off between the strongest evidence-backed mechanism (finding 15) and the rule against required rituals.

**D8. ChatGPT write path.** Accept a per-conversation write confirmation; or route ChatGPT writes only through the extension and hooks, keeping the plugin read-only and labelled honestly. Marking write tools `readOnlyHint` to avoid prompts would misrepresent them and is not recommended.

**D9. Order of building adapters.** The goal fixes the *priority*: web first. The design still has to decide whether the extension or the MCP plugin is built first on the web. The evidence favours the extension, because only it meets Cap-AI and Focus deterministically. The MCP plugin is quicker to build and carries no ToS exposure.

---

## Risks to the goal

**R1 — Without the browser extension, the web cannot fully meet the two web-first non-negotiables (§4.2 AI-said capture and §4.5 in-session focus). The extension is ToS-grey and fragile.**
- On claude.ai and chatgpt.com, verbatim real-time capture of the AI's messages and deterministic per-turn injection are possible **only** through a browser extension (findings 10–12).
- OpenAI's terms explicitly prohibit "automatically or programmatically extract[ing] … Output". Anthropic's terms prohibit "automated or non-human means" and scraping.
- If either vendor objects or changes its frontend, the web adapter drops to:
  - MCP self-report, which is a paraphrase;
  - per-turn calls at the model's discretion, with unmeasured reliability;
  - exports that arrive late and are triggered by hand.
- In that state the goal is **partially met**: cross-session continuity works, verbatim AI-said capture and per-turn focus do not. **The user should decide whether to accept this ToS exposure (D1 and D2).**

**R2 — Desktop chat surfaces have no deterministic per-turn channel. This applies to Claude Desktop chat, ChatGPT Desktop Chat mode and mobile.**
- No sanctioned third-party mechanism injects on every turn or captures verbatim in real time (findings 4, 9).
- In-session focus there depends on the model choosing to call Northstar. Round-1 and drift evidence say that choice fades in exactly the long chats that need it (finding 15).
- Capture happens only after the fact, through the web-side sync or an export.
- **§4.6 (desktop apps second) is therefore at risk of being met only partially.**
- MCP App model context is the one possible way out. It is unverified and must be tested early.

**R3 — ChatGPT's MCP path is unstable and may need the user's action in every chat (§4.3 the AI manages it).**
- Plan eligibility for Plus and Pro conflicts across OpenAI's own pages.
- Plugins must be selected per conversation. Write approvals reset in each new or refreshed conversation.
- Custom apps were reported broken in Projects (unresolved as of February 2026). Memory may be unavailable in Developer mode.
- OpenAI's new hidden-context extensions launched only for the desktop app and the Work browser.
- **Without the extension, ChatGPT web cannot be fully AI-managed.**

**R4 — Account and environment constraints may block the sanctioned channels altogether.**
- If the Claude account is an employer Team or Enterprise member: no self-added connectors, no self-export, and admin control over extensions and memory.
- If a TLS-inspecting proxy is on the network path, captured conversations sent to a cloud core would cross it.
- Personal knowledge on an employer account also raises ownership and confidentiality problems.

**R5 — Measurement validity (§6).**
- Measuring drift reduction "against the same chat without the system" needs a control arm on a consumer UI. That UI's system prompt, model routing and vendor memory are not under our control, and runs are not repeatable (Laban: about 30% unreliability even at temperature 0).
- The extension's shadow mode helps but does not remove the noise.
- A complementary API replay harness can be controlled, but it measures a different product, because the vendor apps' system prompts differ from the API's.

**R6 — The maintainer can be blinded silently (§4.7).**
- Selector-based capture fails without errors. If a UI change stops the capture of AI messages, the core fills with user-only fragments, which is exactly the fragment pile-up the original brief describes.
- This must be bounded by watermarks, canaries and reconciliation (Implication 8). Otherwise non-negotiable 7 is not met.

**R7 — Injection channels are attack surfaces.** A compromised extension or a poisoned memory reaches every turn (SpAIware and MINJA in [03], [07]). Claude Code may also discount injected text that reads like commands, which weakens badly written focus anchors.

**R8 — Interference with vendor memory.** Northstar's injections and vendor memory can contradict or duplicate each other, and neither vendor lets a third party read or write its memory. Expect over-personalization, or stale vendor memories overriding Northstar's supersession.

**Early spikes that settle the unverified points (in order):**
1. On the user's real accounts: can a custom connector and a Developer-mode plugin be added, does Developer mode turn memory off, and is a connector on by default in a new chat?
2. Does MCP App `ui/update-model-context` persist across *later* turns on claude.ai and chatgpt.com, and does it survive a reload?
3. Over a 40-turn chat, how often does an instruction-triggered `northstar_focus` call actually happen?
4. Extension capture fidelity against an export, on 20 conversations.
5. Do Codex hooks fire in local ChatGPT-desktop Work threads?

---

## Sources

**Project and round-1 notes (local)**
- `docs/GOAL.md`; `docs/research/03-ai-memory-systems.md`; `07-human-vs-ai-consumers.md`; `08-ingestion-and-extraction.md`; `SYNTHESIS.md` (findings only; its reframing is superseded).

**Anthropic / Claude**
- Get started with connectors (surfaces, per-chat toggle, approvals): https://claude.com/docs/connectors/getting-started
- Add a connector that isn't in the directory (Free = 1 custom connector; Team/Ent Owner adds; header auth beta; desktop extensions): https://claude.com/docs/connectors/custom/add-unlisted
- Build an MCP server for Claude (supported features; ~150k chars / 240 s; Claude Code 25k tokens): https://claude.com/docs/connectors/building/index
- Test your connector (Cloudflare Tunnel / ngrok for local servers): https://claude.com/docs/connectors/building/testing
- MCP tunnels (Enterprise research preview): https://claude.com/docs/connectors/mcp-tunnels/overview
- Plugin feature support across platforms: https://claude.com/docs/plugins/platform-support
- MCP Apps, getting started: https://claude.com/docs/connectors/building/mcp-apps/getting-started ; Supersede older widget instances (model context "for the next turn"): https://claude.com/docs/connectors/building/mcp-apps/instance-supersession
- Desktop extensions (MCPB): https://claude.com/docs/connectors/building/mcpb ; https://support.claude.com/en/articles/10949351
- Custom connectors using remote MCP (Anthropic-cloud origin, IP allowlisting, Research auto-invocation): https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp
- Chat search and memory (fetched 2026-10-07): https://support.claude.com/en/articles/11817273
- Import and export memory (via search snippets): https://support.claude.com/en/articles/12123587
- Export your Claude data (via search snippets): https://support.claude.com/en/articles/9450526-export-your-claude-data
- Claude Code hooks reference: https://code.claude.com/docs/en/hooks
- Anthropic Consumer Terms (effective 2025-10-08): https://www.anthropic.com/legal/consumer-terms

**OpenAI / ChatGPT / Codex**
- Connect from ChatGPT (plugins; `@` to invoke; HTTPS or tunnel): https://developers.openai.com/apps-sdk/deploy/connect-chatgpt
- Custom MCP server (transports, auth, `readOnlyHint`, per-conversation confirmations, `instructions` 512 chars): https://developers.openai.com/api/docs/guides/custom-mcp-server
- Secure MCP Tunnel: https://developers.openai.com/api/docs/guides/secure-mcp-tunnels ; launch-date secondary source: https://mer.vin/2026/05/openai-secure-mcp-tunnel-private-mcp-servers-for-chatgpt-codex-and-the-api/
- Plugin Extensions: https://developers.openai.com/plugins/build/extensions ; spec (support table, "classic ChatGPT is excluded"; background context): https://github.com/openai/mcp-extensions/blob/main/docs/spec.md
- MCP Events (Work chats): https://developers.openai.com/plugins/build/mcp-events
- Apps SDK state management (`modelContent`, `ui/update-model-context`): https://developers.openai.com/apps-sdk/build/state-management ; user interaction / discovery: https://developers.openai.com/apps-sdk/concepts/user-interaction
- Plugins in ChatGPT and Codex: https://learn.chatgpt.com/docs/plugins ; MCP (desktop app shares Codex host config): https://learn.chatgpt.com/docs/extend/mcp
- Codex hooks: https://learn.chatgpt.com/docs/hooks ; Memories: https://learn.chatgpt.com/docs/customization/memories ; Computer History: https://learn.chatgpt.com/docs/customization/computer-history ; Desktop app: https://learn.chatgpt.com/docs/app ; ChatGPT Work: https://learn.chatgpt.com/docs/get-started-with-work ; Feature maturity: https://learn.chatgpt.com/docs/feature-maturity
- Developer mode Help Center article (403; seen via snippets, versions conflict): https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt
- Custom GPT retirement FAQ (via snippets): https://help.openai.com/en/articles/20001519 ; coverage: https://visualstudiomagazine.com/articles/2026/09/28/openai-replacing-custom-gpts-with-plugins-including-for-codex-in-vs-code.aspx
- Memory FAQ (via snippets): https://help.openai.com/en/articles/8590148-memory-faq ; Dreaming coverage: https://engadget.com/2187811/chatgpt-s-memory-is-getting-better-especially-if-you-re-on-the-free-tier
- Export data (via snippets): https://help.openai.com/en/articles/7260999
- OpenAI Terms of Use, archived copy effective 2024-12-11 (live page 403): https://open.windriver.com/info/uni-license-list/licenses/openai-tou-20241211.html ; live: https://openai.com/policies/terms-of-use/
- Community: Developer mode and memory: https://community.openai.com/t/chatgpt-cant-create-new-memories/1358208 ; apps not working in Projects: https://community.openai.com/t/apps-custom-connectors-not-working-inside-projects/1369786
- Simon Willison, "Adding a custom MCP server to Claude and ChatGPT" (2026-07-28/29): https://til.simonwillison.net/llms/mcp-in-claude-and-chatgpt

**Extensions and prior art (code inspected through the GitHub API on 2026-10-07)**
- Mem0/OpenMemory Chrome extension (archived; `manifest.json`, `src/chatgpt/content.ts`, `src/claude/content.ts`): https://github.com/mem0ai/mem0-chrome-extension ; launch post: https://mem0.ai/blog/introducing-the-openmemory-chrome-extension
- Supermemory changelog (2026-07-22 inline suggestions): https://supermemory.ai/changelog/browser-extension-support-for-claude-and-gemini.md ; ChatGPT web setup: https://supermemory.ai/docs/supermemory-mcp/chatgpt-web ; Claude Code plugin: https://github.com/supermemoryai/claude-supermemory
- MemoryPlugin (vendor-stated, via search snippets; site TLS failed): https://blog.memoryplugin.com/sync-memory-across-chatgpt-claude-gemini-perplexity-grok/ ; https://help.memoryplugin.com/platforms/claude ; https://blog.memoryplugin.com/meet-memoryplugin-sync/
- chatgpt-exporter (`src/api.ts`): https://github.com/pionxzh/chatgpt-exporter
- Claude exporters using internal endpoints: https://github.com/agarwalvishal/claude-chat-exporter ; https://github.com/Emnolope/claude-conversation-export ; https://addons.mozilla.org/addon/claude-exporter/
- claude-mem (`plugin/hooks/hooks.json`): https://github.com/thedotmack/claude-mem
- Practitioner reports on tool-call reliability: https://glama.ai/mcp/servers/@g0t4/mcp-server-memory-file ; https://glama.ai/mcp/servers/xmszm/memory ; https://scottspence.com/posts/how-to-make-claude-code-follow-hook-instructions

**Browser platform**
- Chrome content scripts (`world`, `run_at`): https://developer.chrome.com/docs/extensions/reference/manifest/content-scripts
- Chrome webRequest (MV3): https://developer.chrome.com/docs/extensions/reference/api/webRequest ; declarativeNetRequest: https://developer.chrome.com/docs/extensions/reference/api/declarativeNetRequest
- Safari web extension distribution: https://developer.apple.com/documentation/safariservices/distributing-your-safari-web-extension ; Developer ID support from Safari 18.4 (forum): https://developer.apple.com/forums/thread/782005 ; MAIN world in Safari (forum): https://developer.apple.com/forums/thread/728849

**Protocols and research**
- MCP Apps, SEP-1865 (`ui/update-model-context` semantics): https://github.com/modelcontextprotocol/ext-apps
- Laban, Hayashi, Zhou, Neville, "LLMs Get Lost In Multi-Turn Conversation" (2025): https://arxiv.org/abs/2505.06120
- Li et al., "Measuring and Controlling Instruction (In)Stability in Language Model Dialogs" (COLM 2024): https://arxiv.org/abs/2402.10962

---

## Review revisions (2026-10-08)

The full review record is `docs/design/REVIEW.md`.

| Finding | What changed |
|---|---|
| SEC-6 | Finding 16 retitled "Account and network environment may add constraints". Its first bullet now names no product or host. The employer-domain email bullet is folded into a conditional ("If the Claude account is an employer account, and..."). The Team or Enterprise evidence under it is unchanged. |
| SEC-6 | D6 now asks "a personal account, or an employer account?" |
| SEC-6 | R4 now reads "If the Claude account is an employer Team or Enterprise member" and states the proxy risk as a condition: if a TLS-inspecting proxy is on the network path, captured conversations sent to a cloud core would cross it. |

---

## Final-gate fixes (2026-10-08)

| Finding | What changed |
|---|---|
| Ground rule 6; REVIEW §9(b) | Finding 16's first bullet is now a generic condition: "If a TLS-inspecting proxy is on the network path, it may block code hosts or break TLS verification." D3 (hosting) reads "A TLS-inspecting proxy, if present (finding 16), also affects this choice." The SEC-6 log row above no longer restates what happened on the research machine. All other evidence is unchanged. |
