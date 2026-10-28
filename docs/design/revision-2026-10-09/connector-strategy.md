# Connector strategy: one shared integration layer, or a connector per product?

**Status:** revision proposal for your approval. It answers your comment 2 of 2026-10-09. Nothing here is built. Written 2026-10-09.
**Authority:** [GOAL.md](../../GOAL.md) overrides this document, and your answers of 2026-10-09 override everything earlier. This document does not edit existing specs. Where it changes them, the "Supersedes" section says so.
**Inputs:** [ARCHITECTURE.md](../ARCHITECTURE.md) §0, §2, §7; [SPINE](../foundations/SPINE.md) §4; [CX] [connectors-desktop-and-mcp.md](../components/connectors-desktop-and-mcp.md); [HK] [connectors-claude-code-and-codex.md](../components/connectors-claude-code-and-codex.md); [OBS] [desktop-observer-macos.md](../foundations/desktop-observer-macos.md); [CD], [GD] in `foundations/`; evidence [10], [11], [14].
**Labels:** levels use SPINE §4.2 names (`verbatim_live`, `model_pulled` and so on). **(Unv)** marks an unverified product fact and names the spike that settles it. **N1–N19** are product facts verified today (§9). New IDs: spikes CN-S, risks RISK-CN, questions CN-Q.

---

## 0. The answer on one page

**Short answer.** Northstar does not need a separate, full connector for every application. It also cannot get what you asked for from MCP alone. The effective design is **one shared integration layer with three shared engines**, plus **thin per-product adapters**:

1. **One MCP server and one widget** (shared). Every chat app that speaks MCP uses the same tools and widget, on Windows, Mac and iOS; only the boot-line wording and packaging differ.
2. **One hook engine** (shared). Every product with lifecycle hooks (Claude Code, Codex, and later Gemini CLI, Cursor, VS Code) uses the same engine. Each product supplies only a hook map, which is mostly data.
3. **One observer core** (shared, optional, needs your consent). It reads desktop chat windows. It has one backend per operating system: UI Automation on Windows, Accessibility on Mac, nothing on iOS. Each app has a small UI profile.

**Why not MCP alone.** With MCP, the chat model decides whether to call Northstar and what to report. That is the attention-losing agent your goal warns about (GOAL §1). Capture is the model's copy, only on called turns, and AI-said text is never verbatim. Focus reaches the model only on called turns, unless the widget channel holds (unverified), and replies are checked only against the model's own summary. Continuity is MCP's best case, but only if the model calls Northstar before its first reply; that rate is unmeasured (CD-S3, CS5), and without the call a new chat gets nothing (§3.1–§3.2).

**Why not a separate connector per app.** Most of the work is the same everywhere: the tool contract, the widget, the capture pipeline, the spool, the self-tests. Writing it per product would multiply bugs and repairs. About 85% of connector code is shared, or about 75% if the observer is built (§5.3).

**Where product-specific code is necessary or clearly better:** hooks wherever a product has them (about 1,000–1,500 lines each; they beat MCP on every capability); observer UI profiles, only if you allow the observer (the only route to verbatim desktop chat capture; brittle and ToS-grey); packaging and install per product and OS (§3.3).

| Option | Capture | In-session focus | Continuity | Code and upkeep | Verdict |
|---|---|---|---|---|---|
| A. MCP-only, everywhere | Model's copy on called turns; AI-said never verbatim | Called turns only; checks the model's self-report | Pack on a chat's first call | Smallest | Too weak for capture and focus; discards hooks, which are strictly better on the coding agents |
| B. A full connector per app | Best each product allows | same | same | Largest: the same logic 6–10 times | As C, at several times the code |
| **C. Shared engines + thin adapters** | Best each product allows | same | same | About 15–22k shared lines; 0.1–1.5k per product | **Recommended** |

The design awaiting your approval (ARCH §7) already had one MCP tool contract and one hook engine. This revision makes the rule explicit, makes the edge work on **Windows and iOS**, and adds two findings: **phone chat apps reach Northstar through a remote MCP endpoint**, except ChatGPT chats that run on a connected computer (N19; Unv, SP-PF-17), and the coding agents keep **hook-tier quality when driven from the phone**, because the session runs on your computer (N8, N18; Codex hooks Unv, CN-S6).

---

## 1. What "effective" means here

We judge each mechanism by the level it reaches on each capability (SPINE §4.2), best first:
- **Capture, user and AI:** `verbatim_live` · `verbatim_rendered` (read seconds later) · `verbatim_deferred` (export) · `model_reported` (the chat model's copy) · none.
- **State every turn** and **pack at chat start:** `deterministic` · `deterministic_after_mount` (after a widget mounts) · `model_pulled` (only if the model calls) · `static` (fixed instructions) · none.
- **Reply check:** `in_turn` (before control returns to you) · `next_turn_verbatim` · `next_turn_reported` (the model's self-report) · none.
- **Restart:** `automatic` · `reseed_on_reset` · `prepared` (one action by you) · `suggested` · none.
- **Audit truth** (a capture record that does not depend on the chat model): `live_independent` · `live_single` · `deferred` · none.
- **Your actions:** fewer and one-time is better (GOAL §4.1).

Two rules follow:
- **A `model_pulled` channel fails exactly when it is needed.** A drifting model is the one deciding whether to re-anchor ([10] F15). So model-pulled focus is weakest in long chats.
- **Capture quality caps everything downstream.** Packs, pins and Book pages are built from what was captured. Model-reported capture gives labelled gists, not quotes (ARCH §4).

---

## 2. The integration mechanisms, defined honestly

| # | Mechanism | Who decides it happens | Sanctioned | Where it exists |
|---|---|---|---|---|
| M1 | **MCP tools only:** the model may call `northstar_context`, `_note`, `_fetch`, `_book` | The chat model, each time; a tool description alone rarely triggers calls ([10] F15) | Yes | Every MCP host; local or remote on computers, remote only on phones (N4) |
| M2 | **MCP plus instructions:** a boot line in the app's instructions, the server's `instructions`, a skill, MCP prompts you can pick | Still the model; the boot line raises the call rate (unmeasured: CD-S3, CS5); a picked prompt is deterministic but is your action | Yes | As M1. Claude account instructions reach every chat, mobile included ([CD] V15). "Skills over MCP" (N13) might later replace the pasted line (Unv, CN-S7) |
| M3 | **Widget model context (MCP Apps):** after one tool call, a widget pushes a short state note before later turns; OpenAI adds a thread panel you can open yourself | The host, after the first call or your click; per-turn persistence unverified | Yes | Claude web, desktop, iOS (N4, N5). OpenAI desktop, Work web, iOS, Android; "classic ChatGPT is excluded" (N11) |
| M4 | **Product hooks:** the product runs Northstar at chat start, each message, each reply, compaction | The product, each time | Yes | Claude Code and Codex on Windows and Mac (N1, N2, N9); Cowork (N6); Claude Desktop chat only in API-key mode (N7); Gemini CLI, Cursor, VS Code (N15–N17). Not consumer chat apps |
| M5 | **OS observer:** a helper reads the chat window through the OS accessibility layer; optionally places a visible block in the message box | Northstar code, each time | **Grey** under both vendors' terms (P10, P20) | Windows (UI Automation), Mac (Accessibility). **None on iOS** |
| M6 | **Official exports** | You, by hand | Yes | Claude web or desktop; ChatGPT up to 7 days ([10] F13). Backfill only |
| M7 | **Others found** (below) | — | — | — |

**M7, other mechanisms.**
- **Owned loop (SDK).** An app that builds its own prompts calls Northstar directly (SPINE §4.8). It is the strongest channel: rebuilding the prompt from consolidated state recovered about 95% of single-turn quality ([10] F15). A Northstar-built chat client would be one; we do **not** propose replacing your products with it, only, at most, an optional extra surface.
- **Vendor modes that run hooks.** Claude Desktop **Cowork** (N6), Claude Desktop **chat in API-key mode** (N7; local-only history, API billing) and ChatGPT **Work** threads ([HK] HP28) give hook quality inside the desktop apps, in another mode (CN-Q3; UQ-7).
- **Phone-driven sessions on a computer.** Claude Code Remote Control (N8) and Codex tasks on a connected Mac or Windows PC (N18) run on your computer while you type on the phone, so hooks fire there (Unv for Codex, CN-S6).
- **IDE extension points.** VS Code agent hooks (Preview) reuse Claude Code's file formats, with differing behaviour (N17): M4 again.
- **Not useful or rejected.** MCP Events push your server's events into ChatGPT Work chats, never chat text to Northstar (N12). Internal web APIs are what exporters scrape: grey and brittle ([10] F10). Browser extensions are not required (GOAL §4.6). An iOS share sheet captures only what you share, each time; a custom iOS keyboard sees only your typing and must be used for every message, a ritual (GOAL §4.1).

---

## 3. Effectiveness by mechanism

The full product × platform × capability × mechanism matrix factors into three tables: this one (mechanism × capability), §4 (which mechanisms each product offers on each platform) and §6 (the result per product and platform). Each cell here gives the best level the mechanism reaches. Evidence: [10] F5, F9, F15; [11] F3, F6, F12; [14] F5, F6; [CX] §2, §3, §8; [HK] §2; [OBS] §3.2.

| Capability | M1 MCP tools | M2 + instructions | M3 + widget context | M4 hooks | M5 observer | M6 export | M7 owned loop |
|---|---|---|---|---|---|---|---|
| Capture, user | `model_reported`, only on called turns | `model_reported` on called turns; target ≥ 90% of turns, unmeasured (CD-S3, CS5) | as M2. The widget can store each call's arguments (path C2), still the model's copy | `verbatim_live` (prompt field) | `verbatim_live` (message box at send) | `verbatim_deferred` | `verbatim_live` |
| Capture, AI | `model_reported`: ≤ 5 short points per reply, a turn late; the last reply of a chat is lost without a closing call | as M1 | as M1 | `verbatim_live` (final reply field) | `verbatim_rendered`, seconds after the reply | `verbatim_deferred` | `verbatim_live` |
| State every turn | `model_pulled`; nothing if no call | `model_pulled` + `static` boot text, which decays [11] F3 | `deterministic_after_mount` (Unv: CD-S2, CS4, CN-S4); delivery measured by tag echo | `deterministic` (Claude Code ≤ 10,000 chars; Codex about 2,500 tokens) | none from reading; `deterministic` only with a visible block (consent) | none | `deterministic`, full rebuild possible |
| Reply check | `next_turn_reported`: checks the model's summary of its own reply | as M1 | as M1; the correction rides the widget note | `in_turn`: the real reply, one correction before control returns | `next_turn_verbatim` | audit only | `in_turn` |
| Restart | `suggested` (Claude: `prepared` by deep link, Unv CD-S5) | as M1 | `prepared`, one tap (ChatGPT, Unv CS4) | `reseed_on_reset` + `prepared` | `prepared` (automation, consent) | none | `automatic` |
| Pack at chat start | `model_pulled` at the first call | `model_pulled`, prompted by the boot line; a picked MCP prompt is deterministic | needs a first call, or your panel click (OpenAI) | `deterministic` | `deterministic` only with a visible block | none | `deterministic` |
| Audit truth | none: the same model writes and reports | none | none | `live_independent` | `live_independent` | `deferred` | `live_single` |
| Your actions | Install; tool approval; per-chat toggles possible (Claude per conversation; ChatGPT `@` when not picked) | + paste the boot line once (once per Project on ChatGPT) | + "Always allow" for app display | Install; Codex hook trust once and after the hook changes | Install; Mac Accessibility grant; Windows has no OS grant (Unv, CN-S3) | Each export by hand | None, but only for apps you build |
| Platforms | Windows, Mac, iOS (remote) | as M1 | Claude: all three (N5). ChatGPT: per N11, Unv | Windows, Mac; iOS only through sessions on a computer | Windows, Mac; not iOS | Any, via web or desktop | Any |

### 3.1 What a shared MCP layer achieves alone

- **Continuity: good only if the model calls Northstar before its first reply; otherwise none.** That first-call rate is unmeasured (CD-S3, CS5): Claude can defer loading tools ([CD] V14), and ChatGPT calls a plugin only when it judges it relevant (P29). One call at chat start returns the full pack (≤ 12,000 characters), and one call per chat is far likelier than one per turn. The pack carries what hook products captured, so Claude Code work reaches a phone chat (ARCH §6). Benchmark v0 pre-registers a first-call gate per connector (§8).
- **Deliberate reads and writes: good.** Saves, "what did we decide", Book slices and corrections work on every MCP host.
- **Focus: partial.** A pin on called turns; on every turn after the first call if the widget note persists (unverified), the one sanctioned per-turn route in chat apps ([10] F2; [14] F6).
- **Capture: weak.** Your words as the model's copy; AI explanations as short points labelled "reported", never verbatim (RISK 19).

### 3.2 Where it falls short, and why

1. **The model decides when to call.** Nothing in MCP makes a host call a tool or send the conversation to a server; hosts must get your consent before tools run (N13); Claude can defer loading tools ([CD] V14).
2. **The model decides what to report.** Northstar sees the model's account of the chat, not the chat. A reply that drifted is checked only if the model reports the drift ([10] impl. 2).
3. **No independent record.** The same model writes the content and the report, so the maintainer has nothing to audit against (GOAL §4.7; [10] impl. 8).
4. **Late and lossy AI-said capture.** Points from the previous reply arrive at the next call. The last reply of a chat needs a closing call or your next message (BOOK-2).
5. **Per-chat friction varies by host.** ChatGPT uses a plugin when it judges it relevant, and `@` lasts one message (P29, P30). Write approvals can recur per chat (P19).

### 3.3 Where product-specific code is necessary or clearly better

- **Hooks, where a product has them.** They beat MCP on every row above, for a thin adapter. Keep MCP beside them for deliberate reads and writes (`pull_fallback`, [HK] D-HK-5).
- **The observer, only with your consent.** The only route to verbatim chat-app capture, real-reply checks and audit truth. One backend per OS and one UI profile per app and OS; it breaks when the apps change their UI (RISK 36).
- **Packaging, install and restart links.** A Claude plugin, a `.mcpb`, a Codex plugin or config block, a ChatGPT plugin, a remote connector URL; each product's link scheme per OS (Unv, CN-S9). Small and unavoidable.

---

## 4. Which mechanisms each product offers, per platform

| Product | Windows | iOS | Mac |
|---|---|---|---|
| **Claude chat app** | M1–M3 by a local `.mcpb` (Node bundled, N3) or a remote connector (N4); M5 by UI Automation (Unv, CN-S3); M6. Hooks only in Cowork (N6) or API-key chat (N7) | M1–M3, **remote connector only**, added first on web or desktop; widgets render (N4, N5). No hooks, no observer | As Windows; M5 by Accessibility ([OBS]) |
| **Claude Code** (terminal, IDE, Desktop Code tab) | **M4** + local MCP; native; hooks via Git Bash or PowerShell; exec form needs a real `.exe` (N1, N2) | Remote Control drives a session **running on your computer**, with its local config (N8; [HK] §1); hooks fire there. Cloud sessions not live ([HK] HP20) | **M4** + local MCP |
| **ChatGPT chat app** (desktop Chat mode; ChatGPT for iOS) | M1–M2 by a plugin (remote MCP; local reach Unv, CS2); M3 Unv (N11; CS4); M5 by UI Automation (Unv, CN-S3); M6. App runs on Windows (N10) | Two routes. **Chats on a connected computer:** the phone works with ChatGPT chats running on your Mac or Windows host, whose MCP servers come from the host (N19); so the host's local Northstar server may serve them, with no public endpoint, while the host is awake (Unv, SP-PF-17). **Phone-native chats:** M1–M3 **only if** custom MCP plugins work on the phone: sources conflict, "web, desktop, and mobile" ([GD] V5) against "web only" ([GD] V1); CN-S5 decides | As Windows; M5 by Accessibility |
| **Codex** (CLI, IDE, app threads) | **M4** + local MCP; `commandWindows` (N9); native app (N10) | Phone-started tasks run in the cloud or on a connected Mac or Windows PC (N18); hooks on the PC Unv (CN-S6) | **M4** + local MCP |
| **Other agents** | Gemini CLI, Cursor, VS Code: M4 by a hook map (N15–N17). Other MCP clients: M1–M2. Your own agents: M7 | Phone apps with remote MCP: M1–M2 | As Windows |
| **Web apps** (optional) | M1–M3 by the same remote endpoint as iOS | same | same |

---

## 5. The recommended connector architecture

Three shared engines (MCP server and widget, hook engine, observer core) feed one contract (`northstar.connector/1.x`) into the unchanged, product-agnostic core. Per-product adapters only package, configure and map.

### 5.1 Shared

- **One MCP tool contract and server** (C05): the [CX] §2 tools, annotations derived from flags, budgets. One codebase served two ways: stdio on a computer, and Streamable HTTP behind sign-in for remote hosts and phones.
- **One widget bundle** ([CX] §3): the host shim detects features and never branches on a product name; Claude and OpenAI both implement MCP Apps.
- **One hook engine** (`northstar-hook`, [HK] §4): spool first, fail open, scope gate, turn origin, budgets. **New:** a small compiled binary per OS from the start, because Windows exec form needs a real executable (N1) and start-up must fit the 300 ms budget. Products differ only in event names and payloads.
- **One manifest format** (SPINE §4.3), with a new `platform` attribute on each declared level (`win32`, `darwin`, `ios`, `web`). The core still keys on levels, never on products or OS (I23).
- **One observer core** ([OBS] §4: capture, self-test, safety governor, block placement, spool), written once in a portable language, with **one backend per OS**: UI Automation on Windows, Accessibility on Mac.
- **One edge transport:** a local channel per OS (Unix socket on Mac; named pipe or local socket on Windows, chosen in the platform revision), plus authenticated HTTPS to a remote core through the forwarder (SPINE §7.5), so many machines feed one memory with no adapter change.
- **One SDK, one conformance suite, one host emulator** (SPINE §4.8–§4.9; CX-S7), including the product-blindness test.

### 5.2 Per product

- **Claude Code:** hook map (data), payload schemas, transcript reader, turn-origin templates, and one Claude plugin (hooks, local MCP, skill). The same plugin can carry the remote connector for chat and loads its hooks in Cowork (N6; CN-S7).
- **Codex:** hook map, payload schemas (with `commandWindows`), transcript reader, plugin or marked config blocks, `AGENTS.md` pointer, hook-trust step.
- **Claude Desktop chat:** `.mcpb` proxy and manifest (`win32`, `darwin`) or the remote connector URL; boot line; restart link per OS.
- **ChatGPT Desktop chat:** plugin registration; manifest (`capture_mode` per DQ-4); boot and skill text.
- **Phone apps:** a manifest and the remote registration. **No client code.**
- **Observer:** one UI profile per app and OS (roles, labels, end-of-reply signals, private-chat indicator), with fixtures.
- **Other hook agents:** a hook map and payload schemas each.

### 5.3 Code size (estimate, ±50%, nothing built)

| Part | Lines |
|---|---|
| **Shared:** MCP server and contract, stdio and HTTP | 3,000–4,000 |
| Widget and host shim | 1,500–2,500 |
| Hook engine (compiled) | 2,500–3,500 |
| Observer core | 3,000–4,500 |
| Edge transport and installer, per OS (Windows, Mac) | 800–1,500 each |
| SDK (Python, TypeScript) | 600–900 each |
| Conformance suite and host emulator | 2,000–3,000 |
| **Shared total** | **about 15,000–22,000** |
| **Per product:** Claude Code adapter | 900–1,500 |
| Codex adapter | 900–1,500 |
| Claude Desktop chat | 400–800 |
| ChatGPT Desktop chat | 200–500 |
| Each phone app | under 100 |
| Observer OS backend (if consented) | 1,500–2,500 per OS |
| Observer UI profile, per app and OS | 300–700 each, plus repairs after app updates |
| Each further hook agent | 300–700 |

The four first connectors plus the phones add about 2,500–4,500 lines over the shared layer: about 15% of the total. With the observer on one OS, the OS backend and two profiles raise the product- and OS-specific share to about 25%. **Upkeep** is less even: hook maps change rarely, while UI profiles need repairs every few weeks (Unv, DS11).

### 5.4 The rule for connecting any product

For each product and platform, use every mechanism below that the product offers. The core needs no change (SPINE §4.8).
1. **It runs a loop we own:** the SDK.
2. **It has lifecycle hooks:** a hook map on the shared engine, plus the MCP server for deliberate reads and writes.
3. **It speaks MCP:** the shared server, the widget where the host renders MCP Apps, and boot text in its instruction slot.
4. **Only with your consent, on Windows and Mac:** the observer, where a UI profile exists.
5. **Wherever offered:** exports, for backfill only.

The receipts record which level was reached on every turn (SPINE §4.5). So the evaluation reports each product and platform separately, never pooled (ARCH §10).

---

## 6. What each product and platform gets

Plain words. "Reported" means the chat model's account, labelled and never given authority (I22). Levels that depend on a spike say so.

| Product · platform | Capture | In-session focus | Continuity | You do once | Stays unmet |
|---|---|---|---|---|---|
| **Claude Code · Windows, Mac** | Both sides, word for word | A note every turn; one visible correction of a serious drift before control returns to you; edits checked by code rules | Pack before the first reply; re-seeded after compaction or `/clear` | Install the plugin; workspace trust | Cloud sessions (DQ-9); Windows latency (CN-S1) |
| **Codex · Windows, Mac** | As Claude Code | As Claude Code (Northstar's own continuation cap) | As Claude Code | Trust the hooks once, and after Northstar's hook changes | Cloud tasks; Windows app hooks (CN-S2) |
| **Claude Desktop chat · Windows, Mac, no observer** | Your message as the model's copy; ≤ 5 reported points per AI reply, a turn late | A note on called turns; every turn if the widget note persists (CD-S2, CN-S4); checks use the model's self-report | Pack if the model calls on its first reply | Install `.mcpb` or remote connector; paste one line; "Always allow" | No verbatim AI-said text; uncalled turns unseen (RISK 4, 19); maybe a Tool access step per conversation (CD-S1) |
| **ChatGPT Desktop chat · Windows, Mac, no observer** | As Claude, only on messages where ChatGPT uses Northstar; what is kept depends on the save path (DQ-4) | As Claude, on those messages; widget note Unv in Chat mode (CS4) | Pack on the first call | Add the plugin; paste the boot line (per Project); "Always allow" if offered | Plan route (CS1, RISK 5); `@` where relevance fails; nothing kept on path B (RISK 33) |
| **Either desktop chat app · with observer** (DQ-1; on Windows also CN-Q2) | Both sides verbatim, seconds after each reply | Real replies checked after you read them; a visible block where the widget fails | Missed calls detected; verbatim items in later packs | Allow the observer once; Mac also grants Accessibility | ToS-grey; repairs after app updates (RISK 23, 36) |
| **Claude for iOS** | As Claude Desktop chat without observer, through the remote connector | Note on called turns; widget note if it persists on mobile (CN-S4) | Pack on the first call, including work captured on your computers | Add the connector on web or desktop (N5); the account-wide boot line applies | No verbatim capture except a later export (RISK-CN-2); needs an endpoint (CN-Q1) |
| **ChatGPT chats on a connected computer** (typed on the phone, running on your Windows or Mac host) | As ChatGPT Desktop chat on that host, through its local MCP server (Unv, SP-PF-17) | As ChatGPT Desktop chat; hooks only if they fire there (Unv, SP-PF-17) | Pack on the first call | Nothing beyond the host's setup | The host must be awake, online and signed in (N19); all Unv until SP-PF-17 |
| **ChatGPT for iOS, phone-native chats** | As ChatGPT Desktop chat, **only if** CN-S5 passes | same | same | As ChatGPT Desktop chat | **May get nothing** if custom MCP plugins are web-only and no host is awake (RISK-CN-6) |
| **Coding from the phone** (Claude Code Remote Control; Codex on a connected PC) | Hook tier on the computer that runs the session | Hook tier | Hook tier | Nothing extra | The computer must be awake; Codex hooks and prompt origin there are Unv (CN-S6) |
| **Optional extras** | Web apps: as iOS. Other hook agents: hook tier. Claude Desktop chat in API-key mode: hook tier (CN-Q3) | | | | Each reported in its own cell; none stands in for a first connector |

**Same chat on two devices.** Claude chats sync between phone and desktop; calls from both join one session by the turn tag ([CX] §2.3). Only an export, or an observer sweep when the chat is opened on a desktop ([OBS] §4.3), recovers phone turns verbatim.

---

## 7. Effects on the Windows-first order and on iOS

### 7.1 Windows first

**Nothing in the connector strategy needs a Mac.** The hook tier is documented on Windows (N1, N2, N9) and both chat apps run there (N3, N10). Today's Mac-only items are edge details:

| Mac-only today | Windows counterpart | Where decided |
|---|---|---|
| Hook launcher in `~/Library`, Python first ([HK] §3, §4.3) | Compiled `.exe` in the user's app-data folder, exec form (N1) | Here (§5.1) |
| Unix socket; audit-token peer check ([CX] §6.1) | Named pipe or local socket; peer check by process and signature (Unv) | Platform revision |
| `.mcpb` for `darwin`; restart by `/usr/bin/open` ([CX] §4.1) | `.mcpb` for `win32` too (N3); link opened by the Windows shell (Unv, CN-S9) | Here |
| Relay client under `launchd` ([CX] §7.1) | A Windows service or scheduled task | Platform revision |
| Accessibility observer ([OBS]) | UI Automation backend: Chromium serves it natively since Chrome 138 (N14) and both apps are Chromium-based (SPINE P23); Unv on Windows (CN-S3) | Here (§5.1) |

**Effect on the build order (connector view).** The detailed stages belong to the build-plan revision.
1. The thin slice runs on **Claude Code on Windows**, with the compiled hook engine from day 1.
2. Codex on Windows, then the shared MCP server and widget for both chat apps on Windows.
3. If you allow the observer, the **UI Automation backend is built first**, and Accessibility on Mac later. This reverses today's order.
4. Mac: re-run the conformance suite and the account spikes; build the Accessibility backend if consented.
5. The spikes that depend on the app (CD-S1, CD-S2, CD-S3, CD-S5, CS1, CS2, CS4) run on **both** Windows and Mac. Results can differ per OS.

**Effort (connector part, ±50%).** The Windows edge and compiled hook engine add about 1–2 builder-weeks. A Windows observer backend instead of the Mac one is a swap; a second backend adds about 3–4 builder-weeks.

### 7.2 iOS

**Phone chat reaches Northstar through remote MCP** (N4), except ChatGPT chats run on a connected computer (N19; Unv, SP-PF-17). There are no hooks and no observer on iOS. So:
- **Claude phone chat needs an internet-reachable endpoint; ChatGPT phone chat may not while a host is awake.** Claude calls remote connectors from Anthropic's cloud ([10] F1); ChatGPT phone-native chats call from OpenAI's, but ChatGPT chats run on a connected computer use that computer's MCP servers (N19; Unv for Northstar, SP-PF-17). Today's design has one only as a ChatGPT fallback (the relay) and a cloud core "later". iOS second brings it into the prototype; many machines sharing one memory need a reachable store anyway. This touches "local now" (GOAL §4.6): your decision (CN-Q1).
- **Then the phones cost almost no connector code.** The same server and widget serve Claude for iOS, the web apps and, if you choose, Claude Desktop chat on every computer (CN-Q4).
- **Phone chat is the weakest cell:** tool-call tier, plus the widget if it persists on mobile. Its best feature is continuity: a phone chat can start with the pack built from your coding sessions and desktop chats.
- **Phone coding keeps hook-tier quality** when the session runs on your computer (N8, N18).

### 7.3 Mac last

The Mac design stays as specified ([CX], [HK], [OBS]). It is re-tested, not redesigned.

---

## 8. How effectiveness will be measured

The baseline-first benchmark (your comment 5) compares chats with and without Northstar. What it measures, and what it does not:
- **MCP-only against hooks is measured on the CLI track.** Phase N adds an automated arm M on Claude Code and Codex: hooks off; the MCP server, its server instructions and a CLAUDE.md or AGENTS.md boot line on; the same scripts. F1, K1, the verbatim share of AI-said capture and the call rate are reported next to the hook arm, on the same product (benchmark v0 §4.7).
- **Chat-app cells measure MCP plus the widget against no Northstar**, because those apps offer no hooks; there product and mechanism cannot be separated.
- **Observer against MCP** is measured only if you allow the observer (DQ-1).

Per-cell connector diagnostics explain any difference. Each is reported per product and per OS, never pooled:
- **call rate** per turn, and **first-call rate** per chat, on MCP cells; a **first-call gate** is pre-registered per connector (at least 90% of new chats call before the first reply) and reported next to K1;
- **widget delivery**, by the share of widget tags the model echoes ([CX] §3.4);
- **verbatim share** of captured AI-said text, and **coverage** against an export;
- **your actions** per 100 chats (approvals, `@` picks, toggles, re-trusts);
- **added latency** per turn, especially Windows hook start-up.

---

## 9. Product facts verified today (2026-10-09)

| ID | Fact | Source |
|---|---|---|
| N1 | Claude Code hooks run via Git Bash on Windows, or PowerShell without it; Windows exec form needs a real executable, not a `.cmd` shim | https://code.claude.com/docs/en/hooks |
| N2 | Claude Code runs natively on Windows 10 1809+; Desktop app on macOS, Windows, Linux | https://code.claude.com/docs/en/setup |
| N3 | Claude Desktop runs on `darwin` and `win32`; Node.js ships with it on both; `.mcpb` directory listings deprecated | https://claude.com/docs/connectors/building/mcpb |
| N4 | Web: remote connectors and MCP Apps; desktop adds local extensions; mobile: remote connectors; per-conversation toggle; Always allow per tool | https://claude.com/docs/connectors/getting-started |
| N5 | On mobile, MCP Apps render in a native web view (`WKWebView` on iOS); connectors are added on web or desktop first | https://claude.com/docs/connectors/building/mcp-apps/design-guidelines |
| N6 | Chat ignores plugin hooks and local MCP; Cowork and Claude Code load hooks; account plugins sync to Claude Code | https://claude.com/docs/plugins/platform-support |
| N7 | Claude Desktop chat on own inference runs plugin hooks (1.52386.0+); history stays on the device, unsynced; off by default | https://claude.com/docs/third-party/claude-desktop/chat |
| N8 | Remote Control drives, from the Claude phone app, a Claude Code session running on your machine with its local tools and configuration | https://code.claude.com/docs/en/remote-control |
| N9 | Codex hooks: `commandWindows` Windows override; trust of the exact definition; local Work and Codex threads; Chat mode not mentioned | https://learn.chatgpt.com/docs/hooks |
| N10 | ChatGPT desktop app on macOS, Windows, Linux; the Windows app supports plugins and skills | https://learn.chatgpt.com/docs/app ; https://learn.chatgpt.com/docs/windows/windows-app.md |
| N11 | OpenAI MCP extensions: thread panel and model context on desktop, Work web, iOS, Android; "classic ChatGPT is excluded"; no conversation text to servers | https://github.com/openai/mcp-extensions/blob/main/docs/spec.md |
| N12 | MCP Events: server-to-ChatGPT events, Work chats only | https://developers.openai.com/plugins/build/mcp-events |
| N13 | MCP spec 2026-07-28: tools, resources, prompts, elicitation; extensions Tasks, Skills over MCP, MCP Apps; hosts need user consent before invoking tools; no conversation feed to servers | https://modelcontextprotocol.io/specification/latest |
| N14 | From Chrome 138, Chromium on Windows enables native UI Automation by default | https://developer.chrome.com/blog/windows-uia-support-update |
| N15 | Gemini CLI hooks: SessionStart, BeforeAgent add context; AfterAgent reviews output | https://geminicli.com/docs/hooks/ |
| N16 | Cursor hooks include `beforeSubmitPrompt`, `afterAgentResponse` (search summary of official pages) | https://cursor.com/docs/hooks |
| N17 | VS Code agent hooks (Preview): SessionStart, UserPromptSubmit, Stop and more; shared files do "not make their behavior identical" | https://code.visualstudio.com/docs/agent-customization/hooks |
| N18 | Codex phone tasks run "in the cloud or on a connected computer", a Mac or Windows PC; hooks not mentioned | https://learn.chatgpt.com/docs/remote.md |
| N19 | In the iOS app you work "with ChatGPT or Codex chats on a connected Mac or Windows device"; MCP servers, skills, browser access and Computer Use "come from that host's configuration"; the host must be "awake, online, and signed in to the same account and workspace" | https://learn.chatgpt.com/docs/remote-connections.md |

All checked 2026-10-09. Earlier facts are reused from [CD], [GD], [HK] and SPINE P1–P37, with their dates.

---

## 10. Spikes

All on synthetic chats; any spike on your accounts needs your go-ahead (DQ-2).

| Spike | Question | Settles |
|---|---|---|
| CN-S1 | Claude Code on Windows: compiled hook binary in exec form; added p95 ≤ 300 ms with antivirus on; Git Bash and PowerShell; plugin hooks under workspace trust | RISK-CN-4 |
| CN-S2 | Codex on Windows (CLI, IDE, app): `commandWindows` hooks; trust across updates; thread classification | §6 Codex row |
| CN-S3 | After a yes to CN-Q2 only: UI Automation read of both apps on Windows (tree without a screen reader, message box, end-of-reply signals, private-chat indicator, CPU, any OS prompt) | RISK-CN-3 |
| CN-S4 | Widget model context: CD-S2 and CS4 re-run on Windows, and on Claude for iOS | M3 per OS |
| CN-S5 | ChatGPT for iOS: does a custom MCP plugin added on the web work in phone chats; approvals; model context. The connected-computer route is SP-PF-17 | RISK-CN-6 |
| CN-S6 | Phone-driven coding: hooks in Codex tasks on a connected PC; are phone-typed prompts classified as user-typed ([HK] §8) in both products? | §6 phone coding row |
| CN-S7 | One Claude plugin across Chat, Cowork and Claude Code; one OpenAI plugin across Chat and Codex; can "Skills over MCP" or server `instructions` replace the pasted boot line? | §5.2; one-time steps |
| CN-S8 | After a yes to CN-Q3 only: Claude Desktop API-key chat on Windows and Mac: hook events in chat, latency, cost per 100 turns | CN-Q3 |
| CN-S9 | Restart links: does the Claude app open a prefilled new chat from a link on Windows and iOS? | Restart per OS |

---

## Supersedes

| File and section | What changes |
|---|---|
| [ARCHITECTURE.md](../ARCHITECTURE.md) §0, §0.1 | Each connector paragraph applies on Windows and Mac; phone rows are added per §6; the observer is "an optional desktop helper (Windows or Mac)", not "an optional Mac helper" |
| ARCHITECTURE.md §2, §7 | The edge has three shared engines and a remote MCP endpoint for phones and web; §7 gains the connection rule (§5.4) and the shared and per-product split (§5.1–§5.2); the remote connector is a first-class channel, not only the FEAS-7 fallback |
| ARCHITECTURE.md §11 | Connector stages run Windows first; the observer's Windows backend first if consented (§7.1); stage detail moves to the build-plan revision |
| [SPINE](../foundations/SPINE.md) §4.2, §4.8, §4.10 | Levels gain a `platform` attribute; Gemini CLI, Cursor and VS Code are named hook-map candidates (N15–N17); §4.10 gains rows per OS and for phones, as §6 here |
| [CX](../components/connectors-desktop-and-mcp.md) §4.1, §5.1 | `.mcpb` declares `[darwin, win32]`; the restart opener is per OS, not `/usr/bin/open`; the remote connector is a normal channel; a reachable endpoint is in scope for iOS whatever CS2 shows, subject to CN-Q1 |
| CX §3.4 | With a remote connector and `ui.domain` set, the widget origin is per server, so the `widget_origin` join does not apply; joins use the turn tag |
| CX §6.1, §7.1, §8 | The audit-token peer check is the Mac backend's (Windows: platform revision); install steps per OS, and Windows shows no OS grant for the observer (Unv, CN-S3); the level table gains Windows, iOS and phone-driven coding rows |
| [HK](../components/connectors-claude-code-and-codex.md) §0, §1, §3, §4.3 | "Hook tier on the Mac" becomes "on Windows and Mac"; Windows surfaces, Remote Control and connected-PC Codex tasks are added (CN-S6); the launcher path is per OS; the hook engine is compiled on every OS from the start |
| [OBS](../foundations/desktop-observer-macos.md) §4.1 | One observer core with OS backends; Windows first if consented (CN-Q2); this document stays the Mac backend's spec |

Platform-wide changes (storage, encryption, credentials, approval prompts, services) belong to the platform revision.

---

## Open questions for the user

**CN-Q1. A reachable endpoint for your phones.** *Touches the goal: GOAL §4.6 "local now, cloud later".* Phones reach Northstar only through an internet-reachable endpoint. (a) A hosted endpoint relaying to an always-on computer of yours; it fails while that computer sleeps. (b) A small hosted core early, which many machines need anyway. (c) No endpoint yet: phone chats get nothing; phone coding still works through sessions on your computer. *Until you answer:* (c); phone chat cells read "not run". **Recommendation: (b)**, encrypted and scoped as the platform revision proposes, with items you mark private never leaving your devices. Choose (c) if keeping everything local matters more than phone chats.

**CN-Q2. The observer on Windows** (extends DQ-1). May Northstar read your Claude and ChatGPT desktop chat windows on Windows through UI Automation? The vendor terms are the same, so it is equally grey. Windows shows no OS permission prompt for this (Unv, CN-S3), so Northstar's own consent screen is the only gate. *Until you answer:* nothing installed. **Recommendation:** as DQ-1: read-only, if you accept the exposure and your employer allows it; build the Windows backend first.

**CN-Q3. Claude Desktop chat on your own API key, as an optional focus surface.** In that mode plugin hooks run in chat (N7), giving hook-tier capture and focus inside the Claude app on Windows and Mac. Costs: API billing per message; history only on that computer, not your phone or the web; a chat list apart from your normal account. *Until you answer:* not offered. **Recommendation:** spike it on synthetic data (CN-S8); offer it only as an opt-in for long, focused work; your normal Claude chat stays the first connector.

**CN-Q4. Claude Desktop chat: local extension or remote connector?** With an endpoint (CN-Q1), one remote connector serves Claude on every computer, the web and the phone with one setup. A local `.mcpb` keeps traffic on the computer and can open a prepared fresh chat, but serves only that computer. *Until you answer:* the `.mcpb`. **Recommendation:** the remote connector as an opt-in per device if you choose an endpoint; devices marked "work", or where device scoping, device revoke or spooling matter, keep the `.mcpb` through the edge (the remote connector carries no device identity; ARCH §0.1, DQ-13).

**CN-Q5. Other agents you use.** Which other AI tools do you use weekly (for example Gemini CLI, Cursor, VS Code with Copilot)? Each with hooks costs about 300–700 lines. *Until you answer:* only the first four. **Recommendation:** name the ones you use weekly; we add their hook maps after the first four pass.

---

## Risks

| # | Risk | Threatens | Mitigation |
|---|---|---|---|
| RISK-CN-1 | Chat-app cells without the observer stay tool-call tier: capture and focus depend on an unmeasured call rate that may fall in long chats; continuity is served better than focus there (extends RISK 4) | GOAL §3.3, §4.2, §4.5 on both chat apps and all phone chats | Widget note (CN-S4); one call carries pin and pack; call-rate sentinel; observer (DQ-1, CN-Q2); hooks wherever offered; per-cell results |
| RISK-CN-2 | No observer is possible on iOS: phone chats never get verbatim AI-said capture, real-reply checks or audit truth, except by export or a desktop sweep of a synced chat | GOAL §4.2, §4.7 on iOS | Labelled reported capture; reconciliation; exports; continuity from other surfaces |
| RISK-CN-3 | The Windows observer is unverified for both apps, grey under vendor terms, has no OS consent prompt, and may be flagged by security software | GOAL §4.6, §4.2 | Consent-gated (CN-Q2); read-only first; fail-closed self-test; signed binary; CN-S3 before any build |
| RISK-CN-4 | Windows hook start-up (process launch, antivirus scan, shell choice) may break the 300 ms prompt budget | GOAL §4.1, §3.3 | Compiled binary; exec form; fail open with the cached pin; CN-S1 |
| RISK-CN-5 | UI profiles double (two apps on two OSes), and so do observer repairs | GOAL §6 "maintains itself" | Text-free self-test records; repairs by a coding agent; one OS backend first |
| RISK-CN-6 | ChatGPT for iOS may not run custom MCP plugins (official sources conflict); chats on a connected computer may reach the host's local server, but only while it is awake (N19) | GOAL §4.6 phones | CN-S5; SP-PF-17; continuity from other surfaces; "not met" only if both routes fail |
| RISK-CN-7 | Phones need a reachable endpoint, which conflicts with "local now" until you decide; a relay to a sleeping computer fails | GOAL §4.6 | CN-Q1; private items stay on device; no real data before your answer |
| RISK-CN-8 | Four products on three platforms mean more spikes to re-run after vendor updates | GOAL §4.8 on time | Host emulator; conformance suite per OS; reruns triggered by app versions |
| RISK-CN-9 | Hook formats converge but behave differently (N17): a map can pass in one product and fail in another | GOAL §4.6 | Fixtures and conformance tests per product |
| RISK-CN-10 | Shared engines are shared failure points: one bug hits every product | GOAL §4.7 | Fail open; conformance and fault-injection suites; staged rollout per product |

---

## Goal-fidelity check

| GOAL item | How this document serves it | Status |
|---|---|---|
| §2 (2026-10-09) Connectors by effectiveness; no MCP mandate either way | §3 rates every mechanism per capability with evidence; §5.4 uses the best each product offers; §8 measures MCP-only against hooks on the same products (CLI track) | Met by design; chat-app mechanisms compared analytically, since those apps offer only MCP |
| §2, §4.6 (2026-10-09) Not Mac-only; Windows, then iOS, then Mac | Every engine runs on Windows and Mac; Windows first (§7.1); iOS by remote MCP (§7.2) | Partial: iOS needs an endpoint (CN-Q1, RISK-CN-7); Windows observer Unv (RISK-CN-3) |
| §2 (2026-10-09) Many machines and phones, one memory | One contract and a forwarder feed one core from every machine (§5.1) | Partial: depends on CN-Q1 and the platform revision |
| §3.3, §4.5 Focus and continuity, equally | Hooks give both; chat apps get the widget, restart and the observer option | Partial: chat apps without the observer favour continuity (RISK-CN-1) |
| §4.2 AI-said first-class; §4.3 the AI manages it | Code captures verbatim on hook products and with the observer; labelled reported points elsewhere | Partial: chat apps without the observer, all phone chats (RISK 19, RISK-CN-2) |
| §4.1 No rituals | One-time installs; every per-chat step listed per cell | Partial: ChatGPT `@`, approvals, per-conversation toggles (RISK 5, 33) |
| §4.6 Product-agnostic core with connectors | Core unchanged; product-free shared engines; adapters mostly data; product-blindness test | Met by design |
| §4.7 Robust maintainer | The chat model's calls are never the maintainer; hooks and the observer give audit truth; engines fail open | Partial: no audit truth on tool-call-only cells |
| §3.2 Book with sources | Verbatim sources where captured; "session only" gists elsewhere | Partial, as ARCH §15 |
| §4.8 Prototype built and evaluated | Per-cell levels, spikes and diagnostics feed the baseline-first benchmark (§8) | Planned |
| §7 Reframing needs the user | Nothing dropped or narrowed; CN-Q1 touches "local now" and is asked, not assumed; no Northstar client replaces your products | Checked |
