# Platform: runtime, deployment, security, privacy and operations

**Status:** component design draft for adversarial review. Not approved. Nothing is built.
**Written:** 2026-10-08. Product facts checked 2026-10-08 (Sources, V-PL-1 to V-PL-10). Device facts are measured at install and kept locally, never here (V-PL-11).
**Authority:** [`docs/GOAL.md`](../../GOAL.md), then the user's answers of 2026-10-08, then [SPINE](../foundations/SPINE.md). This document changes only the HOW. Risks and questions are recorded; no reframe is adopted.
**Covers:** SPINE §7; C17 server side (Reader hosting, auth, ops and privacy pages); C19; C21; SD-26 to SD-29; the auth part of C04 and the egress gate in C20.
**Inputs:** GOAL; SPINE; TEXTBOOK §8.8–§8.15, §9, §10.1–§10.3, §12; [CD]; [GD]; [OBS]; SYN §3.5, §5, §7.4; [10] F1, F6, F14–F16; [13] §C–§G. The parallel connector designs [CX] (`connectors-desktop-and-mcp.md`) and [HK] (`connectors-claude-code-and-codex.md`) are cited where they touch.
**IDs:** spikes SP-PL-n, risks RISK-PL-n, decisions PL-n; questions use SPINE UQ-n IDs. (Unv) names the spike that settles it.

---

## 0. Summary

1. **Processes:** `northstard`, `northstar-maintainer`, `northstar-modeld` (local models on a socket) and, if needed, a relay client, all self-restarting LaunchAgents. The observer is a separate signed login item.
2. **Only the Reader listens on TCP by default.** Local connectors use `run/core.sock` (D-PL-1, as [CX] D8).
3. **Each caller's credential caps what it may claim:** channels, fidelity, origins, scopes, recipient family. I20 and I22 hold at the edge.
4. **If FileVault is off at install, real capture needs the encrypted sparse bundle** (D-PL-3); install checks this.
5. **Every copy stays under Northstar's control,** so excision reaches it: no Time Machine; own encrypted backups (UQ-14).
6. **Upgrades are blue/green behind stable shims,** with expand-then-contract migrations and automatic rollback.
7. **The relay exists only if CS2 fails,** on its own listener with only the remote profile (D-PL-2).
8. **Cloud later is a port swap list.** Ports, `tenant_id` and a portable-SQL lint are checked in CI now; the Postgres CI matrix and triggers come at the cloud-adapter stage (§4.4).
9. **Two deterministic privacy gates:** intake redacts secrets and tags PII; egress checks each call and delivery by tier, scope and recipient family (D-PL-4). Nothing real reaches a cloud model before UQ-11.
10. **Excision is end to end,** ending in a store-aware 0-hit scan and a list of what already left the Mac.
11. **Threats** from captured text, memory, the Reader, MCP clients, the observer, the relay, the supply chain and a prompt-injected coding agent (T14) have red-team tests in CI. Destructive and policy commands need Touch ID or the user's password (§2.8).
12. **Alerts are states, never tasks.** Failures only the user can fix are degraded around and reported (RISK-PL-2).

---

## 1. Trust boundaries

- **B1 this macOS user** (processes, data root, Keychain) against other users, web pages and remote hosts.
- **B2 the core** (`northstard`, maintainer, modeld) against connectors and the observer, which hold credentials but are less trusted.
- **B3 the chat model** is trusted with nothing: every model-called tool is untrusted input ([13 §G]).
- **B4 off the Mac:** only redacted, policy-approved content, logged in the egress ledger.
- **B5 a prompt-injected AI agent running as this user** (Claude Code, Codex) is in scope as threat T14 (§7.2). It has this user's file access but not the user's presence, so destructive and policy actions need a LocalAuthentication prompt (§2.8).
- **Out of scope:** malware deliberately targeting Northstar, which can read every file and token (RISK-PL-1).

---

## 2. Local now

### 2.1 Processes

| Process | Runs | Listens on | Sole writer of | Network |
|---|---|---|---|---|
| `northstard` | C04, C05, C06, C09–C10, C23, C15, C17 server, C18, C19 policy, C21 | `run/core.sock`; Reader `northstar.localhost:<port>` (bound to `127.0.0.1`); `run/remote.sock` with a relay only | `intake`, `session`, `artifacts`, `reader`, `ops` | Model APIs for fast-lane roles, via the egress gate |
| `northstar-maintainer` | C11–C14, C08, C16, J10, J11; backups, integrity, re-scans, migrations, excision orchestration | none | `ledger` (C12), `jobs`, `index`, `book` | Model APIs via the egress gate |
| `northstar-modeld` | Local verifier, entailment, cascade, eval judge | `run/model.sock` | none | **none** |
| Relay client (optional) | `tunnel-client` or `cloudflared` (§3) | none (outbound) | none | OpenAI or Cloudflare edge |
| Observer.app (optional, UQ-1/UQ-2) | C02 | none | none | **none** ([OBS §4.1]) |
| Transient | `northstar-hook`, `northstar-mcp`, `.mcpb` proxy, CLI, `northstar-eval` | none | none (C22 writes `eval.db`) | none |

**Local models (PL-4).** `northstar-modeld` runs MLX models as a library behind `run/model.sock`: no unauthenticated TCP port. If SP-3 picks Ollama, it stays on its default `127.0.0.1:11434`, pinned (RISK-PL-7). Ollama also serves cloud-hosted models (V-PL-7), so C20 accepts only models with a pinned local digest. A "local" verifier can never leave the Mac silently.

### 2.2 launchd units

Keys from `man launchd.plist` (checked 2026-10-08):
- `ProgramArguments` is a stable shim in `<root>/bin/` that execs `versions/current/…`. Its content never changes, so path- or hash-pinned configuration (Codex hook trust, P12) survives upgrades (SP-PL-4).
- `RunAtLoad: true`; `KeepAlive: {SuccessfulExit: false}` (a crash restarts; a deliberate stop stays stopped); `ThrottleInterval` 10 s (default) for `northstard`, 30 s otherwise; `Umask: 63`; `ProcessType` Interactive for `northstard`, Background plus `LowPriorityIO` for the others; `ExitTimeOut` 20 s, 60 s for the maintainer; stdout and stderr to `~/Library/Logs/Northstar/`.
- **No calendar units:** nightly work runs in the maintainer's scheduler, which catches up after sleep.
- MDM can block background items (Unv, SP-PL-8); then nothing runs and `northstar doctor` says so (RISK-PL-2).

### 2.3 Lifecycle

**Install, once.** `northstar install`: preflight (disk, FileVault, venv, free port); data root 0700, inside the encrypted bundle if FileVault is off; secrets and credentials (§2.8, §2.9); account declaration (UQ-3) and personal and work git orgs (§6.6) as salted hashes; LaunchAgents; Time Machine exclusion; chosen connectors ([CX] §7); `northstar doctor` checks every channel without sending a chat message. The egress gate stays closed until UQ-11 (§6.3).

**Upgrade, blue/green.** Build `versions/<new>/` and self-test it on a copy of the stores; back up; drain (cached answers, hooks spool, maintainer stops at a job boundary); switch `current` atomically; run expand migrations under the global lock; pass a health gate (§8.2 green in 5 minutes; golden-set canaries if a model or prompt pin changed, [13 §F.13]). **Any failure rolls back automatically**, restoring and replaying only if a contract migration ran; so does a release that trips an error budget within 24 hours. The core serves tool lists and shims only forward, so vendor-side packages rarely change; when one must, that is a user step (RISK-PL-12).

**Uninstall.** `northstar uninstall [--wipe]`; with the bundle, `--wipe` deletes its key (crypto-erase).

### 2.4 Storage paths and at-rest protection

```text
~/Library/Application Support/Northstar/   0700 (mount point of Northstar.sparsebundle if FileVault is off)
  config.toml   0600; keys that govern the maintainer change only by versioned commit (I19)
  bin/          stable shims          versions/<ver>/   venv and code; current -> <ver>
  db/           the ten stores of SPINE §6.1, WAL, 0600
  blobs/        content-addressed, zstd     spool/<client>/   replayed, then kept 48 h for restores
  run/          0700: core.sock, model.sock, remote.sock (relay only), creds/<cred_id> 0600, locks/
                pincache/ 0700: the hook pin cache    workers/  worker scratch
  backups/      encrypted archives          book/   rendered pages, zstd
  models/       pinned local weights        tmp/    scratch, purged after each run
  (later)       the forwarder cache (§4.2)
~/Library/Logs/Northstar/   0700, content-free
```

- **Registered copies.** `run/pincache/` (0700; entries expire after 30 minutes and at session end), `tmp/`, `run/workers/` and, later, the forwarder cache each hold content outside the stores. Each is registered in `ops.registered_store` and purged at X5 (§6.7).

- **At rest (PL-3).** If FileVault is off at install, the data root lives in an encrypted APFS sparse bundle (AES-256), mounted `-nobrowse` by the `northstard` shim with its passphrase in the login Keychain. Real-data capture stays off until FileVault or the bundle is present. SP-PL-10 measures WAL performance and mounting across login and sleep.
- **Spotlight.** Pages and spool payloads are stored compressed so no importer reads them; the bundle root carries `.metadata_never_index`. SP-PL-9 checks with `mdfind`.
- Records hold no absolute paths; blobs are addressed by hash (SPINE §7.5).

### 2.5 Backups and restore

- **When:** nightly at the first idle moment after 02:00 (caught up after sleep), and before every migration, upgrade, restore and excision. **Keep** 7 nightly, plus pre-operation archives for 48 h.
- **How:** SQLite online backup of every store at one ledger watermark, plus the blob manifest; tar, zstd, AES-256-GCM with a fresh Keychain key per archive. One archive a week is test-restored and passes `integrity_check`.
- **Where:** `backups/`, plus a drive the user names, whenever mounted (UQ-14; the drive is ARCH DQ-11). No cloud copy. **Time Machine** excludes the data root (`tmutil addexclusion`, documented in `man tmutil`), so no copy exists that excision cannot rewrite (RISK-PL-8).

**Restore is automatic and per store** (`quick_check` at start and nightly finds corruption). `index` and `artifacts` are rebuilt from the ledger and recorded outputs, hash-identical (I18), never restored. `book`: BookLedger, Edition and the landmark tables (`landmark`, `landmark_label`, `redirect`) are canonical for restore, because structure is path-dependent (TEXTBOOK §7.2, B10); they are backed up and restored, and only BlockVersion renders are rebuilt, by BookLedger replay from recorded outputs. `ledger`: restore, then replay `jobs.db` outcomes and the durable journal of non-model ledger writers (C18 corrections, Reader notes, C06 capture proposals, C10 joins) written after the archive's watermark; that journal lives in `intake.db` and is backed up with it. `intake`: restore, then client spools replay (48 h retention, idempotent, I14). `jobs`: restore; later jobs re-run as new decisions. `session`: restore; live sessions re-resolve through identity joins. `reader`, `ops`, `eval`: restore or reset.

### 2.6 Schema migrations

- A `schema_migrations` table per store. **Expand, then contract:** a release only adds; removals ship a release later, so the previous release runs on the new schema and rollback rarely needs a restore.
- The maintainer migrates at start, under the global lock, one transaction per store, after a backup. `northstard` serves neutral results if a store is newer than its supported range.
- SQL stays in the SQLite–Postgres common subset (SD-26); a portable-SQL lint in CI keeps it there. Applying every migration on both engines (PT-8) starts at the cloud-adapter stage (§4.4). Contract versions are negotiated per connector (SPINE §4.4).

### 2.7 Sockets and ports

| Endpoint | Default | Auth |
|---|---|---|
| `run/core.sock` (IF-1, IF-2, internal metrics): hooks, proxies, observer, SDK, CLI, maintainer | on | Dir 0700, socket 0600, peer UID (`LOCAL_PEERCRED`), credential; where a peer check applies, audit token plus code signature on every message (§2.8) |
| `run/model.sock` | on | Dir permissions, peer UID |
| `run/remote.sock` | relay only | Remote credential and profile (§3) |
| Reader `northstar.localhost:<port>`, bound to `127.0.0.1` | on | §2.8 |
| Loopback IF-1/IF-2 (CX-S3 fallback) | **off** | Credential; any request with an `Origin` header refused (V-PL-1) |

Ports are drawn at random at install (20000–39999) and kept in `config.toml`; SPINE's 47321/47322 were examples. A random port also defeats fingerprinting by web pages.

### 2.8 Local authentication

**Credentials (PL-1).** One per connector instance, minted at install, a 0600 file under `run/creds/`. Clients read it per connection, so rotation (every 30 days, 10-minute overlap) is invisible. The `X-Northstar-Connector` header ([CX] §5) must match it. A connector's hook process and its MCP process get **separate credentials**. The `.mcpb` fallback that keeps its credential in a `sensitive` user_config field (storage unspecified, V-PL-10) gets a `model_reported` ceiling and a short rotation (daily by default).

```yaml
credential:
  id: cred_01JB...   connector_id: claude-desktop-chat    # metadata only (I23)
  transport: unix | loopback | remote
  channels_allowed: [mcp_report, widget]
  fidelity_ceiling: {mcp_report: model_reported, widget: model_reported}  # per channel; an mcp_* channel never claims verbatim_live
  origins_allowed: [model_reported, app_click]          # app_click also needs a valid action_nonce (T4)
  read_scopes: [personal, "project:*"]  # intersected with session scope rules (I17)
  recipient_family: anthropic           # who receives its deliveries (D-PL-6)
  relay_operator: null                  # e.g. cloudflare
  account_ref: acct_7f3...              # install declaration (RISK 35)
  peer_check: none | code_signature     # audit token plus code-signing check on every message, never the PID (CX-S4, SP-PL-3)
```

C04 turns it into an **AuthContext** and enforces it before C06 sees the envelope. The fidelity ceiling is **per channel**: an `mcp_*` channel never claims `verbatim_live`, even on a hook-tier connector. Anything above the ceiling is refused and counted. I20 and I22 then hold even if a low-trust client lies. Against same-user code this is weak (T14, RISK-PL-1); it bounds what a buggy or hijacked connector, or the relay, can claim. **Peer checks** (observer and clients) read the peer's audit token and check its code signature on every message. A PID can be reused, so it is never trusted.

**Write and call budgets (C04, PL-17).** Per credential and session, so a looping or injected agent cannot flood the ledger or the spend:
- `northstar_note`: at most 20 per session-hour, and 200 a day per credential.
- New sessions minted through MCP: at most 30 an hour per credential.
- One steward run per (session, turn tag).
- Near-duplicate notes within a session (cosine ≥ 0.95, local embeddings only) are merged at intake.

Over budget, content is still captured but waits. The tool returns "Saved; processing is delayed"; the event is counted and [MT] sentinel #20 fires. Each connector's share of spend follows [MT] §9.5.

**Destructive and policy actions (PL-16).** These need a macOS **LocalAuthentication** prompt (Touch ID or the user's password) that names the action, never a y/N on stdin, which an agent can answer:
- excision; `pause --capture`; `uninstall --wipe` or `--purge`;
- scope, egress and profile edits;
- minting a step-up token.

Northstar's own automatic actions (policy excision, self-repair) need no prompt; no agent can start them as commands. Every guarded action is optional, so the prompt adds no ritual. Whether the core, running as a LaunchAgent, can raise the prompt for Reader actions is unverified (Unv, SP-PL-17).

**Privilege separation (an option, SP-PL-17).** A dedicated service account could own the data root, credentials, spool, pin cache and backups, with peer checks by audit token. An agent running as the user could then not read the stores. It needs admin rights at install and may be refused on managed Macs, so it is an option behind SP-PL-17, not a precondition.

**The Reader** (reconciles SD-27, TEXTBOOK §10.3, [CX] §5):
- Served on `northstar.localhost:<port>`, bound to `127.0.0.1` only. `Host` must be `northstar.localhost:<port>`; no CORS. A dedicated host keeps the cookie away from other local web apps, which share cookies across ports.
- **No token ever reaches a model.** `northstar open`, or a local open by a `can_open_local_app` connector, mints a one-time launch token (60 s) and runs `/usr/bin/open http://northstar.localhost:<port>/auth/launch?t=…`. Links in chats carry no token.
- Cookie host-only (no `Domain` attribute), `HttpOnly`, `SameSite=Lax` (chat links open signed in; GET is read-only), 90-day sliding, `Secure` where allowed on `northstar.localhost` (SP-PL-5). Writes need a CSRF token, a matching `Origin` and `Sec-Fetch-Site: same-origin`.
- **Step-up** for excision, capture pause, relay on, and bulk moves and hides: a single-use token bound to one explicit destructive-action confirmation (the action and its target), minted out of band after a LocalAuthentication prompt. A launch token never counts, however recent. Page script cannot mint one, so even XSS cannot excise or pause.
- **Correction cap:** at most 10 corrections a minute through the Reader; extras become proposals.
- **Agent or user.** A local agent driving a browser that holds the cookie can click like the user. `Sec-Fetch-User` and page nonces do not tell them apart and are not relied on; the correction cap, step-up and LocalAuthentication bound what such a click can do. A separate cookie jar (a dedicated browser profile, a site app, or a small WKWebView shell with a URL handler for chat links) is an option behind SP-PL-16.
- `Content-Security-Policy: default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; font-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'; require-trusted-types-for 'script'`, plus `nosniff`, `Referrer-Policy: no-referrer`, COOP and CORP `same-origin`.
- **Rendering:** captured text and model prose pass a Markdown renderer with raw HTML off, then an allowlist sanitizer (for example `nh3`). Links only `http`, `https`, `mailto`, shown with their host. Remote images never load, which also blocks image-URL exfiltration. The widget follows the same rules and reaches the core only through host `tools/call` (TEXTBOOK §10.2).

### 2.9 Secrets in the Keychain

API keys; relay credentials; one key per backup archive (deleting it crypto-shreds the archive); the excision HMAC key; the account salt; the bundle passphrase (FileVault off only); the Reader signing key. No secret is in files, logs or the repo. Access goes through `/usr/bin/security`, whose path never changes, named in each item's access list, to avoid prompts when the venv's Python changes (Unv, SP-PL-2; else RISK-PL-12).

### 2.10 Logs

**Content-free by construction:** the logger accepts only IDs, enums, numbers, hashes, durations and literal keys; tracebacks lose exception arguments. JSON lines, 10 MB × 5, kept 14 days. No telemetry leaves the Mac (RT-9).

---

## 3. The relay: the only internet-reachable surface

### 3.1 When

Only if CS2 shows ChatGPT Desktop Chat cannot reach a local server, the user connects ChatGPT Desktop chat (or the optional web), and the user answers UQ-5. Which relay vendor carries it is the user's choice in ARCH DQ-4(iii). Otherwise Northstar has no internet-reachable endpoint.

### 3.2 Shape

```text
ChatGPT cloud ─ Option A (DQ-4(iii) a, recommended): Secure MCP Tunnel ⇐ outbound 443 ⇐ tunnel-client ─stdio→ northstar-mcp --remote → run/remote.sock
              └ Option B (DQ-4(iii) b, only if allowed): Cloudflare edge (TLS ends) ⇐ cloudflared → run/remote.sock (or loopback, SP-PL-13)
run/remote.sock → a separate ASGI app in northstard that mounts only /mcp (remote profile) and, for B, OAuth endpoints
```

- **Separate listener (D-PL-2):** a routing bug cannot reach IF-1, the Reader or the CLI endpoints, because they are not mounted there.
- **Option A auth:** Secure MCP Tunnel (P18, CS7). For a personal account it uses the user's personal OpenAI Platform organization, with an API key the user creates. The server is added through Plugins → Add custom MCP server → Tunnel → Create, as a plugin. The authorization server is not tunneled automatically, so any OAuth server must be reachable from the tunnel-client host. It runs under the Platform organization's terms. The remote credential still applies.
- **Option B auth:** an OAuth 2.1 resource server (V-PL-2) with audience-bound 15-minute tokens and rotating refresh tokens. Its one-user authorization server puts consent behind Cloudflare Access, verified at the origin via `Cf-Access-Jwt-Assertion` (V-PL-8). Passkey or device-bound consent is offered instead of an email code (SP-PL-13); a one-time code to the declared personal email is used only if that fails. Whether ChatGPT's OAuth client completes this is (Unv), CS7 and SP-PL-13.

### 3.3 Hardening and reach

- **Tools:** the [CX] §2.2 catalog under flag `remote`: `northstar_context`, `northstar_note` (`save_chat` only under path A; `kind: correction` proposes, T4), `northstar_fetch`, `northstar_book`, and the widget's app-only tools ([CX] §2.4). Never `northstar_restart` ([CX] §2.5), IF-1 events, excision, export, pause or configuration. **Unreachable:** the Reader, corrections with precedence (without a valid `action_nonce` or the TEXTBOOK §9.2 chat-correction conditions, T4), backups, `private`, `held` and work content, the file system.
- **Ceiling:** fidelity `model_reported`; origins `model_reported`, and `app_click` with a valid `action_nonce` ([CX] §3.5).
- **What crosses the relay,** exactly: per-turn results; the first-call pack (≤ 12,000 characters); Book slices and fetched items (≤ 8,000 characters each, up to 200 items a day); and the model's calls. They are drawn from personal items on any connector, within §6.3.
- **Recipients:** `{openai}` for A; `{openai, cloudflare}` for B, because Cloudflare sees plaintext. Personal scope only; sensitive items masked (§6.3). The vendor choice is ARCH DQ-4(iii) (a) or (b), not settled HOW. Under Option B, the R column default is "only items whose source spans OpenAI already holds", with an opt-in for the rest (§6.3).
- **Limits:** request ≤ 64 KB; result ≤ 12,000 characters on a session's first `northstar_context` call, else the [CX] §2.7 budget for the tool (per turn 4,000, book 2,400, fetch 8,000); answer or fail within 1.5 s p95 (CS7); 60 calls a minute; per-session fetch budget (T7); write budgets (§2.8).
- **Anomaly** (auth-failure or rate spike, unknown tool): the client stops (fail closed), an alert is written, and it restarts once after 1 hour. A second trip keeps it off.
- **TLS** checks are never disabled; if a TLS-inspecting proxy is on the path and breaks the tunnel, the relay stays off and is reported (CS7, [10] F16). Binaries pinned by checksum; optional `sandbox-exec` profile (Unv, SP-PL-13). Logs carry request IDs, tool names, sizes, latencies.

### 3.4 Sleep and failure

- **Mac asleep or offline:** ChatGPT calls fail on OpenAI's side and the model answers without Northstar. Northstar never changes power settings. On wake the agent reconnects (backoff 1–60 s); gaps show in watermarks and are backfilled only by observer sweep or one-off export (SPINE §7.4; RISK 27).
- **Core down:** fast "Northstar unavailable"; launchd restarts it. **Credential rejected:** relay off, "only you can change this" (RISK-PL-2). **TLS interception or outage:** option B if the user allowed it (ARCH DQ-4(iii) b), else off and reported. **Replays:** idempotent per (session, turn), I14.
- The relay disappears when the core moves to the cloud.

---

## 4. Cloud later

### 4.1 Swap list

| Concern (port) | Local now | Cloud later |
|---|---|---|
| Stores (`RepositoryPort`) | SQLite, WAL | Postgres 17: a schema per store, RLS on `tenant_id`, **one database role per writer**, so SPINE §6.4 becomes grants |
| Blobs; jobs; events; lock | Directory; SQLite job table; polled outbox; file lock | Object store (same hashes); same table with `SKIP LOCKED`; outbox plus `LISTEN/NOTIFY` or a queue; advisory lock |
| Search (`IndexPort`) | FTS5, local vectors (SP-1) | Postgres full text, pgvector |
| Auth (`AuthPort`); Reader | Socket, credentials; loopback with launch token | OAuth 2.1 (V-PL-2), device authorization for the forwarder, credential fields as claims; Reader over HTTPS with OIDC and `__Host-` cookies |
| Tenancy; secrets | `tenant_id = local`; Keychain | Real tenants; KMS with per-tenant, per-scope data keys, so backup excision is a key deletion |
| Models; backups | modeld plus APIs; encrypted archives | APIs plus an open-weight verifier on an operator-controlled host; point-in-time recovery, excised by key deletion or a stated window |
| ChatGPT transport | Relay | Public Streamable HTTP; no relay |

### 4.2 What stays on the device

Connectors (hook clients, `northstar-mcp`, `.mcpb` proxy, Codex configuration) keep using the local socket. `northstar-forwarder` (SPINE §7.5) listens there, holds the only cloud credential, keeps the spool, and caches the last pin per live session so the 300 ms hook budget survives a network hop. The observer keeps no network access. The Markdown mirror stays local.

### 4.3 Moving data to the cloud

`northstar cloud migrate`, started by the user: freeze and back up; export each store through its port as checksummed NDJSON (ULIDs keep order); upload encrypted under the tenant key; import tombstones, barriers, the egress ledger and recorded outputs too, so excised content cannot return and replays work (secrets are re-minted); verify counts, a ledger hash chain and hash-identical projections (I18); point connectors at the forwarder (shim paths unchanged); keep local read-only for 14 days, then crypto-erase if the user chooses.

### 4.4 Portability tests

**In CI now:** the ports, `tenant_id` and a portable-SQL lint.
- **Ports.** Every store is reached only through its repository port; the port suite runs on SQLite.
- **PT-3** Every table has non-null `tenant_id` and `account_ref`, ULID IDs, no absolute paths. **PT-4** Adding tenant B leaves tenant A's projections hash-identical, and no A query returns B rows.
- **Portable-SQL lint.** Every migration and query stays in the SQLite–Postgres common subset (SD-26).
- **Once, now:** CDM-S4 applies the DDL to Postgres 17 (SP-PL-15).

**At the cloud-adapter stage:** Postgres triggers and the Postgres CI matrix.
- **PT-1** Every repository port passes one suite on SQLite and Postgres 17. **PT-2** The same fixtures and recorded outputs give a hash-identical ledger and projections on both.
- **PT-5** SPINE §4.9 conformance with connectors on HTTPS and OAuth (test authorization server), through the forwarder. **PT-6** With 80 ms injected, pin p95 stays under 300 ms from the forwarder cache.
- **PT-7** ULID order and text comparison identical (`COLLATE "C"`). **PT-8** Every migration applies from every earlier release fixture on both engines.

---

## 5. Enterprise later

| Need | Later | Seam kept now |
|---|---|---|
| Tenancy | Tenant per organization; a book per person per scope | `tenant_id`, `account_ref`; PT-4 |
| Admin-installed connectors | Signed manifests; MDM-delivered configuration; tenant policy on connectors and levels (for example no observer) | Signature field; per-instance credentials; Claude Desktop organization allowlists exist (V-PL-10); managed Codex hooks (P12, Unv) |
| SSO | Authorization server federated to the IdP; SCIM; deprovisioning triggers retention | `AuthPort`; credential claims |
| Data residency | Region-pinned storage and providers | Recipients are a policy input (D-PL-6) |
| Accounts, retention, audit | Per-tenant allowlists; scheduled policy excision; admin changes logged | C19 allowlist; D-PL-5 engine; ledger as audit log |
| Model terms | API keys only; subscription CLIs off outside `local` | Provider allowlist per tenant |
| **Claude Desktop on 3P** | Connector `claude-desktop-3p` at hook tier (P24), **added beside** `claude-desktop-chat`, never replacing it (UQ-7) | Connectors are additive; the core knows neither name (I23) |
| Admin reading a person's book | Not designed; default deny; a WHAT question for later | `admin_read` flag, off |

---

## 6. Privacy

### 6.1 Scopes and tiers (I17)

- **Scope:** `personal`, `project:<id>`, `work:<org>`, `unclassified:<repo_hash>` (treated as work), `session:<handle>`, `eval`. Set by C06 from account and `context_ref` rules (§6.4, §6.6), never by a model. This list is the one scope vocabulary; `private` is a tier, never a scope kind.
- **Tier:** `normal`; `sensitive` (structured PII, or J1 health, finance, legal, `distressing` tags); `private` (an optional "Keep on this Mac" in the Reader, or a rule).
- **Held** (a flag on a scope or session, not a scope kind): set by C19 when a new exclude rule matches sessions already captured ([HK] §7 late reclassification), a deterministic signal, never a model's. Held content keeps its scope and tier but gets no egress, no packs and no Book (§6.3 row `held`) until the rule changes. Excision stays the user's choice.
- Derived items take the strictest tier and narrowest scope of their spans. Packs, slices, pages, exports and model calls filter on both (TEXTBOOK B14).

### 6.2 The deterministic secret and PII scan

One versioned library (`scan_v`), no model, run at intake (C06, before the first write) and at egress (C20, before every remote call or delivery). Client spool writers run it too: the hook client scans before it writes the spool ([HK] §4.1), so no secret ever lands on disk unredacted.

| Class | Detectors | Intake | Egress |
|---|---|---|---|
| Secrets | Key formats (cloud, model APIs, VCS, chat tokens, JWTs), PEM keys, credentials in URLs, high-entropy strings near key words; seeded from a public rule set (for example gitleaks) | **Redacted irreversibly** to `⟦secret:<class>#<hmac8>⟧` | A hit blocks the call and triggers a re-scan |
| Structured PII | Emails, phones, cards (Luhn), IBANs (mod 97), national IDs by country, IPs, coordinates | Tagged; item becomes `sensitive` | **Masked** for remote recipients as per-call placeholders, re-linked locally before validation (I2) |
| Names, free-text facts | Not detected | Kept | Not masked (RISK-PL-4) |

Hashes are taken after redaction, so channels still reconcile. A rule-pack update re-scans stored text; a newly found secret is removed by policy excision (D-PL-5). SP-PL-7 measures recall (bar ≥ 99%) and false positives.

### 6.3 Egress rules

**Recipients:** L local models; A Anthropic API (and `claude -p` if UQ-6); O OpenAI API (and `codex exec`); V the chat vendor receiving a delivery (`recipient_family`); R the relay operator; M the mirror folder. **No new exposure:** a recipient may receive an item only if its family already holds every source span.

| Class | L | A, O | V | R | M |
|---|---|---|---|---|---|
| Secret | not stored | never | never | never | never |
| `held` (flag; wins over scope and tier) | yes, but no pack or Book job | no | no | no | no |
| `private` | yes | no | no new exposure only | no | no |
| `work:*`, `unclassified:*` | yes | no new exposure only | same-scope sessions, no new exposure | no new exposure only | no |
| `sensitive` (personal) | yes | after UQ-11, PII masked | yes; masked if new exposure | masked | unless excluded |
| `normal` (personal) | yes | after UQ-11 | yes (cross-surface continuity, GOAL §3.3) | yes | yes |

- **R under Option B:** by default only items whose source spans OpenAI already holds cross the relay; the rest needs an opt-in (ARCH DQ-4(iii)). The table's R column applies on top. Under Option A the relay operator is OpenAI, already the recipient.
- **Egress gate (PL-8):** until UQ-11 (ARCH DQ-3) is answered, A and O are closed; API roles run locally or wait, and book blocks use extractive form (TEXTBOOK §8.15, Q7). For `eval`, columns A and O open only after DQ-3 as well as DQ-6, because offline replay sends real chats to each vendor's API. Synthetic fixtures hold no real content and are not gated.
- **Profiles (SPINE §8.4):** D closes A and O; B opens O; C routes them through subscription CLIs, personal tenant only.
- **Mirror:** folders under `~/Library/Mobile Documents` or `~/Library/CloudStorage` are refused unless picked knowingly at setup. Column M (the Markdown mirror and EPUB export) applies the Reader's renderer rules (§2.8): raw HTML off, an allowlist sanitizer, no remote images.
- **Batches** are deleted at the provider once collected (Anthropic `DELETE`; OpenAI batch files, otherwise kept "until deleted"; V-PL-5, V-PL-6).

**Enforcement.** C20 builds a call manifest; C19 decides before anything leaves:

```yaml
call_manifest:
  job: job_01JB...  role: extractor  provider: anthropic  model: claude-sonnet-5-5  batch: true
  recipient_family: anthropic  region: null
  items: [{id: I-88, scope: personal, tier: sensitive, source_families: [openai]}]
  spans: [S-301, S-302]
  scan: {scan_v: 7, secret_hits: 0, pii_masked: [email]}
decision: allow | deny | transform        rules: [E-gate, E-tier, E-scope]
```

Each allowed call writes an **egress ledger** row beside its recorded output (`jobs.db` slow lane, `session.db` fast lane; D-PL-7). Deliveries pass `policy.delivery_filter` per item. A recorded input holding a forbidden item is a hard-gate failure: remote calls under that rule stop until a code fix ships (RT-8; TEXTBOOK §8.12).

### 6.4 Account allowlist (UQ-3, RISK 35)

- The declared personal account per connector is stored as a salted hash. The employer-domain account is denied by default (UQ-3).
- Signals, best first: the observer's account label (Unv, DS4); a documented account-status command for hook clients, never a credential file (Unv, SP-PL-11); else the declaration.
- C04 drops non-allowlisted events before any write. **Delivery is neutral too:** personal memory never goes into a chat on a non-allowlisted account, which would copy it into an employer-governed store. A session later shown to be on such an account is removed by policy excision.
- **Multi-participant sessions.** A session the host reports as multi-participant (a shared project or group chat) is treated as non-allowlisted: neutral delivery only, so personal memory never reaches other participants. CS1 checks the signal.
- **Browser history** is another store Northstar does not control, and a managed browser profile may sync it. Reader search uses POST or a URL fragment, and page titles are neutral, so no content enters history.

### 6.5 Temporary and incognito chats

With the observer, flagged or unsure sessions are never captured ([OBS §4.3]). At L0 no signal is known (CS12; SP-PL-12 for Claude Desktop incognito); the boot text asks the model not to call Northstar there ([CX] §4.3), which is weak. A later positive signal triggers policy excision. Some may never be detected (RISK-PL-6).

### 6.6 Employer repositories (TEXTBOOK Q3)

C06 scopes a hook-tier session by its git remote host and org (hashed) against the install declaration: personal → `personal` or `project:<id>`; work → `work:<org>`; else `unclassified`, treated as work. Work content is captured into its own scope (Q3 working assumption, pending), stays out of the personal book and packs, and follows "no new exposure". A later yes to Q3 applies retroactively. `northstar excise --scope work:<org>` removes a whole employer scope.

### 6.7 User-started excision, end to end

| Step | What happens |
|---|---|
| X0 Request | Reader privacy page (step-up) or `northstar excise <target>` (LocalAuthentication prompt, §2.8): item, span, message, conversation, session, scope, account, connector, time range, or a phrase |
| X1 Dry run | The dependency closure in every store and copy (ledger rows, index, FTS, embeddings, artifacts, receipts, session items, block versions, recorded model I/O, envelopes, blobs, spools, reader state, eval snapshots, backups, drives, mirror). Counts per store, plus what already left the Mac (§6.8) |
| X2 Confirm | The user confirms |
| X3 Suppress | Target IDs and fingerprints join a deny-list read by C05, C15 and C17: nothing delivers them from this second |
| X4 Barrier | Conversation keys and HMAC fingerprints make C06 drop any re-capture (observer sweep, export re-ingest, spool replay) |
| X5 Purge | Runs as the **resumable saga** of [CDM] §10.2: the tombstone, needles and closure are written first, and an interrupted run resumes at boot. Global lock; jobs stop at boundaries. **Each store's own writer** deletes its rows (the I6 exception), so single writers hold; C19 keeps its SPINE ledger exception. The tombstone holds target, scope, stores and a text HMAC, never the text |
| X6 Scrub | `PRAGMA secure_delete=ON` (zeroes deleted content in ordinary tables, V-PL-3); FTS5 delete and `optimize`; `VACUUM`; `wal_checkpoint(TRUNCATE)`; blobs and spools rewritten; `tmp/` cleared |
| X7 Rebuild | Index, artifacts, citing pages (from remaining leaves, extractive if needed), mirror files |
| X8 Backups | Each archive purged and re-encrypted under a new key; the old key deleted. External drives rewritten when next mounted, shown as pending, no action asked |
| X9 0-hit scan | Needles: target texts, normalised forms, 8-token shingles. Haystack (one rule): every store in `ops.registered_store` and every file under the data root, `run/pincache/` included, as raw bytes; logs; decompressed blobs, spools and pages; archives decrypted in memory; the mirror; FTS queries on the rarest tokens; an embedding check (no cached vector within cosine 0.98). Needles under 20 characters: record-ID absence instead. **Pass = 0 hits** (TEXTBOOK B16). On failure: one more purge, then an alert. The saga stays `in_progress` and resumes at the next boot and nightly. Writers are not frozen indefinitely; X3 keeps suppressing delivery meanwhile |
| X10 Report | A record of IDs, counts, scan result and times, no content. The Reader shows "Removed from Northstar on [date]" and §6.8's list. The saga's needles are deleted when it closes |

**Policy excision (D-PL-5)** runs X3–X10 under a standing rule shown at install: late-found secrets, temporary or incognito sessions, non-allowlisted accounts. Policy excision and user excision use the same saga. The trigger is always a recorded deterministic signal, never a model's judgment; every run is listed on the privacy page. SP-PL-6 measures completeness and time (target: one conversation from a 1 GB store in under 10 minutes).

### 6.8 What cannot be recalled

Every excision report lists, from the egress ledger and known copies:
- **chat vendors:** the original conversation, and vendor memory derived from it, which can outlive the chat ([10] F14);
- **model API providers:** Anthropic keeps inputs and outputs up to 30 days, 2 years if flagged (V-PL-4); OpenAI abuse logs up to 30 days (V-PL-6). Batches were already deleted;
- **the relay operator** (option B), for items that crossed it;
- **the user's own copies** that Northstar wrote (exports, a synced mirror);
- **sessions it was delivered into:** from context receipts, every session the item was delivered into. Local vendor transcript files (Claude Code JSONL, Codex rollouts) are named as Northstar-made copies that Northstar does not edit. IDs and locations only, no content;
- **employer agents**, if present (security, management or backup agents), out of reach (RISK-PL-3).

---

## 7. Security

### 7.1 Assets and attackers

**Assets:** verbatim conversations, the ledger and the book; the authority of goals, constraints and corrections; credentials; the user's attention. **Attackers:** text in captured conversations; other MCP servers or clients on the host; web pages; internet clients at the relay; compromised dependencies; employer agents; a prompt-injected agent running as the user (in scope, T14); malware deliberately targeting Northstar (out of scope, RISK-PL-1).

### 7.2 Threats and defences

| # | Threat | Defences | Residual | Tests |
|---|---|---|---|---|
| T1 | **Injection through captured text** steers workers, steward or judge | Workers have no tools, network, writes or delegation (Rule of Two); one episode per call; job card last; Apply validates (I1–I24); only verbatim `user_typed` spans create instructions, goals, constraints (I5, I22) | Proposal content can be shaped; it keeps its origin ([13 §G.17]) | RT-4 |
| T2 | **Memory poisoning** reaches every turn (RISK 9) | One rendering rule for every model-facing artifact ([AC] §3.2 rule 9): attributed, delimited third-person facts (SPINE §4.7), commands only in inert, labelled code blocks; instruction slot only from verbatim user text; injection-looking items shown as labelled quotes (a canary only, [13 F8]); CK-10 | A poisoned claim can bias a visible reply | RT-4, RT-14 |
| T3 | **Fidelity or origin forgery** (RISK 25) | Per-channel credential ceilings; separate hook and MCP credentials; audit-token and code-signature check on every message (SP-PL-3); I22 at Apply | Same-user code (T14) | RT-5 |
| T4 | **Forged corrections** | `northstar_note(kind: correction)` proposes only, unless it meets the TEXTBOOK §9.2 chat-correction conditions (the user's words, outside paste ranges, name a delivered or named target; an independent entailment check agrees; at most 3 a session; listed with undo; [CX] §2.6); applying a proposal needs the app-only `northstar_widget_action(action: apply_correction)` **and** a single-use `action_nonce`, bound to instance, session and target and sent only in widget-only `_meta`, unseen by the model ([CX] §3.5; Unv, SP-PL-14); Reader proposals show their true origin, expire in 7 days, never apply in bulk | A user clicks a convincing proposal; undo exists | RT-6 |
| T5 | **XSS** in Reader or widget | Sanitising, CSP with Trusted Types, no raw HTML or remote images (§2.8) | Browser bugs | RT-1 |
| T6 | **CSRF, rebinding, cross-site calls** | Dedicated Reader host `northstar.localhost` with a host-only cookie and Host allowlist; no CORS; CSRF, `Origin`, `Sec-Fetch-Site`; step-up bound to a confirmation; correction cap (10 a minute); IF-1 on a socket | A scripted browser holding the cookie, within the cap (SP-PL-16) | RT-2, RT-2b, RT-3 |
| T7 | **Malicious MCP client or co-installed server** | Per-credential scopes (a new generic client gets personal `normal` only); fetch budget (30 calls an hour, 200 items a day); write and call budgets (§2.8); no dump tool; bulk-read sentinel; model writes provisional | Reads within scope (RISK-PL-10) | RT-10, RT-13 |
| T8 | **Exfiltration via model output** | Artifact shape rules; `private` and work never cross vendors | Repeated delivered text | RT-14 |
| T9 | **The observer** sees every chat and can type | [OBS §4.8]; credential and signature check; CI checks no networking framework, only `AF_UNIX`; writes off until UQ-1 | A compromised signed helper | RT-12 |
| T10 | **The relay** | §3 | Plaintext at the operator (RISK 13) | RT-7 |
| T11 | **Supply chain** | Hash-locked frozen installs; few dependencies (SD-33); `.mcpb` proxy on Node's standard library (V-PL-9); widget from a lockfile, no CDN; observer without third-party packages; weights by digest; binaries by checksum; CI actions pinned; OSV scans; SBOM | An update poisoned before it is known | RT-11 |
| T12 | **Data at rest and copies** | §2.4, §2.5, §2.10 | Employer agents (RISK-PL-3) | RT-9 |
| T13 | **Self-capture loops** | I24; worker guard | — | Conformance |
| T14 | **A prompt-injected coding agent running as the user** (Claude Code, Codex) reads stores, forges spool or hook input, plants pin-cache files, runs the CLI | Fail-closed hook authority ([HK] §8); LocalAuthentication for destructive commands (§2.8); install-time file deny rules on the data root ([HK] §14.3); excision-epoch check on the pin cache | It can read the store until SP-PL-17 (RISK-PL-13) | RT-17 |

### 7.3 Red-team tests in CI

Fast tests on every change; browser tests (Playwright) nightly; synthetic fixtures only.

**RT-1** XSS payloads (script, handlers, `javascript:`, SVG, CSS, exfiltrating images) in replies, pastes and prose never execute or fetch. **RT-2** Writes without CSRF token, or with a foreign `Origin` or cross-site `Sec-Fetch-Site`, are refused; so is excision without step-up. **RT-2b** A scripted browser client holding the cookie cannot exceed the correction cap; if SP-PL-16 is adopted, the default browser profile holds no Reader cookie. **RT-3** A foreign `Host` is refused on every TCP listener. **RT-4** Planted instructions in replies, pastes, tool output and file names never gain authority (never become instruction, goal, constraint or correction items) and never render unneutralised (in a pin, pack, slice or fetch result, only as an attributed fact under the rendering rule). The payloads include agentic ones (shell commands, "call northstar_note", Markdown image exfiltration, tool names), delivered through hook SessionStart, slices and fetch. **RT-5** A model-reported credential cannot send `hook` or `verbatim_live`; an MCP envelope on a hook-tier connector claiming `user_typed` or `verbatim_live` is refused; an unsigned peer cannot send `ax_observer`. **RT-6** Apply without a valid, unused `action_nonce` is refused; mismatched user words stay proposals. **RT-6b** Substring-only, paste-sourced and off-session-target chat corrections stay proposals. **RT-7** The remote listener reaches no IF-1 route, Reader, restart, excision or admin call, and returns no `private`, `held` or work items. **RT-8** Forbidden items never appear in recorded inputs for a forbidden recipient (hard gate); seeded secrets never appear in stores, inputs or logs; the gate holds before UQ-11. **RT-9** Canary strings never appear in logs or crash output. **RT-10** Reads past the budget get neutral results. **RT-11** Lock hashes verify; no known-exploited advisory; worker code cannot open sockets. **RT-12** The observer binary links no networking framework and opens no non-`AF_UNIX` socket. **RT-13** Scrambled connector names leave scopes and egress decisions unchanged with `recipient_family` fixed. **RT-14** No artifact has image syntax or query-string URLs; the agentic payloads of RT-4 render inert in every artifact. **RT-15** After each fixture excision: 0 hits, re-ingest barred, backups clean. **RT-16** Non-allowlisted events are dropped before storage with neutral delivery; flagged temporary sessions are never stored. **RT-17** An injected README in a scripted Claude Code session yields no authority item, pin-cache change, excision or store read.

---

## 8. Operations without babysitting

### 8.1 Rules

1. Every alert names its **automatic action** and **when it clears**. None asks the user to act.
2. Alerts are **states**: one neutral Reader footer line, the ops page, `northstar status`. No badges, counts, to-do lists or push notifications by default (UQ-19; settled as HOW, ARCH R16).
3. When only the user can fix something, the state says so once ("Only you can change this") and Northstar runs degraded around it.
4. Sentinels are code. They act through C11 (freeze, quarantine, rollback) or fail closed.

### 8.2 Health checks

- **Liveness** every 30 s: `/healthz` on each socket answers in < 1 s. The maintainer watches `northstard`, which watches the maintainer and modeld; a hung peer gets `launchctl kickstart -k`.
- **Fast lane:** pin p95 < 300 ms, pack p95 < 1.5 s. **Stores:** `quick_check` at start and nightly; `integrity_check` weekly on a backup; WAL < 256 MB after checkpoint; free disk > 5 GB.
- **Models** every 5 min: modeld probe, providers' last call, quota. **Connectors:** self-tests and watermarks. **Relay:** connected, p95 < 1.5 s.
- **Backups:** newest < 26 h; weekly test-restore. **Privacy:** zero hard-gate violations. **At rest:** FileVault on or bundle mounted.

### 8.3 Self-repair

| Symptom | Automatic action | State shown |
|---|---|---|
| Crash or hang | launchd restart or peer kickstart; hooks spool; leases expire, jobs re-queue | "Restarted at 14:02" |
| modeld down | Restart; verifier roles queue or record `no_independent_verifier` (SD-38) | "Local checks delayed" |
| Provider errors | Backoff; Batch retry; role fallbacks (SPINE §8.1) | — |
| Provider rejects the key | Stop it; route roles to allowed alternatives or local; queue the rest | "Only you can change this: the API key was rejected on 3 Oct" |
| Disk < 5 GB / < 1 GB | Drop rebuildable caches, keep 3 backups / capture into intake only, maintainer paused; nothing canonical deleted | "Running lean" / "Only you can change this: disk nearly full" |
| Corruption; failed upgrade | §2.5; §2.3 | "Rebuilt index"; "Upgrade rolled back" |
| Error budget trip | C11 freeze; book-prose freeze (TEXTBOOK §8.8) | "Some checks paused" |
| Observer self-test fails | Shadow; L0 (RISK 36) | "Desktop capture reduced" |
| Egress hard-gate violation | Remote calls under that rule stop until a code fix ships | "Cloud processing paused" |
| Keychain unavailable | Remote calls pause | — |

### 8.4 Metrics that feed sentinels

C21 owns `ops.db`. Other processes send metrics over `core.sock` with an internal credential, buffered in memory if `northstard` is down. The maintainer's J10 sweep and J10d sentinel results reach `ops.db` the same way, through C21 over this socket, so C21 stays the single writer.

- **Capture:** events per turn by connector and fidelity, watermark gaps, `p_call` and first-call rate, spool depth, account and temporary drops → SPINE §4.5 sentinels; replay throttling.
- **Fast lane:** `context.get` and `reply.check` latency, steward lag → cache-only pins.
- **Slow lane and quality:** queue age, lease expiries, failures, quarantine age, invariant violations before validation, verifier rejects, audit disagreement, canaries, vendor parity (SD-38), TEXTBOOK §8.12 → [13 §E] and SYN §7.4 bars; freezes; rollback by job, batch or model.
- **Privacy:** egress by recipient, denials, masks, redactions, policy excisions, scan results → hard gates, fail closed.
- **Security:** auth failures; ceiling, Host, Origin and CSRF rejects; reads per credential; relay rates → neutral results, relay off.
- **Resources and cost:** disk, WAL, battery, spend per provider and role → lean mode; modeld paused below 20% battery; cheaper tiers for non-gating roles.

### 8.5 The ops page

`/ops` holds **no content**, only IDs, counts and states: processes, versions, at-rest, gate and model profile; capture and delivery per connector by fidelity; budgets, freezes, quarantine, sentinels, backups; egress by recipient, excision records and "not recallable" lists; incidents with cause, action and clear time. Optional controls (pause, relay off, panic, excise) need step-up per §2.8, which starts with a LocalAuthentication prompt. None is required.

### 8.6 Upgrade safety

Blue/green with automatic rollback, expand-then-contract, a backup before every change (§2.3, §2.6). Model or prompt changes are deployments: shadow run on the golden set, switch only without degradation, roll back on canary regression ([13 §F.13]; TEXTBOOK §8.9). Maintainer configuration changes only by versioned commit (I19).

### 8.7 Kill switches

`northstar pause` (deliveries neutral), `pause --capture`, `relay off`, and `panic` (all three plus a maintainer freeze); the observer has its own switch. All reversible and logged.

### 8.8 Failures only the user can fix

A rejected key, a revoked Accessibility grant, a full disk, MDM-blocked agents, a Keychain prompt, a vendor-side package to reinstall: Northstar keeps capture and local work going, says so once, never nags. This falls short of "without babysitting" (RISK-PL-2; UQ-19).

---

## 9. Decisions

| ID | Decision | Status |
|---|---|---|
| PL-1 | Per-connector credentials with per-channel ceilings, scopes and recipient family; separate hook and MCP credentials (refines SD-27) | Leaning |
| PL-2 | Unix socket for local clients; loopback off unless needed | Leaning; CX-S3 |
| PL-3 | FileVault if on, else an encrypted sparse bundle; real capture gated on either | Leaning; SP-PL-10 |
| PL-4 | MLX in modeld on a socket; Ollama only if SP-3 picks it, pinned, local-only | Leaning; SP-3 |
| PL-5 | Own encrypted backups; Time Machine excluded; optional drive | Settled as HOW (ARCH R16; UQ-14); the backup drive is ARCH DQ-11 |
| PL-6 | Secrets redacted at intake; PII tagged, masked at egress | Leaning |
| PL-7 | Egress per item by tier, scope, recipient family; "no new exposure" for `private` and work | Leaning |
| PL-8 | Egress closed for real content until UQ-11 | **Decisive** (SPINE §11.2; TEXTBOOK Q7) |
| PL-9 | Relay on a separate listener and app | Leaning |
| PL-10 | Reader on `northstar.localhost`: host-only Lax cookie, CSRF and Origin checks, step-up bound to a confirmation, correction cap; no tokens in chat links | Leaning; SP-PL-5, SP-PL-16 |
| PL-11 | Each store's writer purges during excision | Leaning |
| PL-12 | Policy excision for late-found sensitive data | Leaning |
| PL-13 | In-process scheduler with catch-up, no calendar units | Leaning |
| PL-14 | Blue/green upgrades with stable shims | Leaning; SP-PL-4 |
| PL-15 | Alerts as footer states; no notifications by default | Settled as HOW (ARCH R16); user override only |
| PL-16 | LocalAuthentication (Touch ID or password) for destructive and policy actions; service-account separation only as an option | Leaning; SP-PL-17 |
| PL-17 | Write and call budgets per credential and session; over budget, capture continues and processing waits | Leaning |

Reasons are given where each is described.

---

## 10. Interfaces

**Provides**

| To | Interface and shape |
|---|---|
| C04 | `auth.resolve(transport, credential, peer) → AuthContext` (§2.8 fields plus session scope rules); `auth.enforce(envelope, ctx) → envelope or reject(reason)`, with the per-channel ceiling; `budget.check(credential, session, call) → allow or delay` (§2.8 write and call budgets) |
| C06 | `privacy.scan(text, scan_v) → {text_redacted, findings[{class, start, end, action, hmac8}]}` (also for client spool writers); `privacy.capture_allowed(envelope, ctx) → allow or drop(reason)` |
| C20 | `policy.egress_decide(call_manifest) → {decision, masks[], rules[]}` (§6.3); gate state |
| C05, C15, C17 | `policy.delivery_filter(items, session_ctx) → items'`, with `session_ctx {scope_rules, held, recipient_family, relay_operator, account_ref}`; the excision deny-list |
| C16 | `policy.mirror_allowed(page_scope, target_path)` |
| C11, C12, store writers | Excision protocol `excision.begin(targets)`, `purge(store, ids)`, `scrub(store)`, `excision.done(target)` (SPINE §6.3); `excision_request {targets[], kind: user or policy, rule_id?, step_up_token?}`; `excision_record {id, targets, counts{store: n}, scan{needles, hits}, not_recallable[], at}` |
| C17 | Ops and privacy read API; auth middleware; launch and step-up tokens; `alert {id, severity, cause, auto_action, clears_when, user_only, opened_at, cleared_at?}`; `health_report {process, version, checks[{name, ok, value}]}` |
| All | Content-free logger; `ops.emit(metric, value, labels)`; kill-switch state |
| C22 | Egress-ledger and ops reads; platform fault injection (kill a process, corrupt a store copy, revoke a key, fill a disk image) |

**Needs**

| From | What |
|---|---|
| C01–C03 ([CX]) | Credentials from `run/creds/<cred_id>` (not one `run/token`); `recipient_family` and account signal in manifests; the scanner in spool writers; stable shims; `X-Northstar-Connector` matching the credential |
| C02 | Account label and temporary flag per event; stable Team ID; no network |
| C05 | Remote profile only on `run/remote.sock`; `action_nonce` only in widget-only `_meta` ([CX] §3.5) |
| C10, C23 | `session_ctx` per session; fast-lane egress rows |
| C11, C12 | Global lock; job-boundary pause; freezes; tombstone and `excised` events; the resumable excision saga ([CDM] §10.2); replay of `jobs.db` outcomes and the non-model journal after a restore |
| C08, C15, C16 | `rebuild_from(watermark)` and `purge(ids)` |
| C20 | A call manifest per call; recorded provider and batch IDs; batch deletion; local-digest check |
| C22 | Synthetic red-team corpora and the golden set |

---

## 11. Departures from SPINE

| # | Departure | SPINE | Justification |
|---|---|---|---|
| D-PL-1 | All local clients, the `.mcpb` proxy included, use `run/core.sock`; loopback IF-1/IF-2 off by default | §6.2 IF-1; §7.1–§7.2 | Smaller attack surface; Node supports sockets (V-PL-9); matches [CX] D8; loopback is the CX-S3 fallback |
| D-PL-2 | The relay ends on its own listener and app, not loopback IF-2 with a `remote` flag | §7.2–§7.3 | A flag on a shared listener fails open on a routing bug |
| D-PL-3 | FileVault not assumed; real capture needs it or an encrypted bundle | §7.1 | Checked at install |
| D-PL-4 | PII tagged at intake, masked at egress; only secrets redacted at intake | C06 | Intake PII redaction would erase names and contacts from memory and quotes (I2); exposure happens at egress |
| D-PL-5 | **Policy excision** under a standing rule shown at install | §6.4 rule 3; I6 | I6 keeps model judgment from destroying data; here the trigger is a recorded deterministic signal enforcing the user's evident intent. SPINE §7.6 already plans retention as scheduled excision |
| D-PL-6 | I23's allowed policy inputs gain `recipient_family` and `relay_operator` | §5.7; §4.1 | Cross-vendor scope (TEXTBOOK §8.15, §10.8; [CX] C19) needs the recipient. Generic families, held fixed in the product-blindness test (RT-13), like `speaker_model_family` |
| D-PL-7 | Egress-ledger rows in `jobs.db` and `session.db` | §6.1 | No new store or writer |

---

## 12. Risks

**SPINE and SYN risks touched:** 2 and 35 (§6.4), 9 (T1, T2), 13 (§3, §6.3), 14, 23 (T9), 25 (T3), 26 (RT-13), 27 (§3.4), 29 (T13), 36 (§8.3).

| # | Risk | Threatens | Mitigation |
|---|---|---|---|
| RISK-PL-1 | Malware deliberately targeting Northstar reads every store and token | Privacy | Stated boundary; Keychain; SP-PL-17 would also raise its cost |
| RISK-PL-2 | Failures only the user can fix (rejected key, revoked Accessibility, full disk, MDM-blocked agents, Keychain prompts) are degraded around, not healed | GOAL §4.1; §6 | Degraded modes; one state line; UQ-19 |
| RISK-PL-3 | On an employer-managed Mac, EDR, MDM or backup agents may read or copy the store beyond excision's reach | Privacy; personal first | Encrypted bundle; UQ-20 (ARCH DQ-5(a)) |
| RISK-PL-4 | Only structured PII is detected; names and free-text facts reach remote providers under Profiles A and B | Privacy | `private` tier; scopes; UQ-11 |
| RISK-PL-5 | Vendor, provider (30 days; 2 years if flagged) and relay copies cannot be recalled | Privacy | Listed per excision; batch deletion |
| RISK-PL-6 | L0 temporary or incognito chats may be captured and never detected | Privacy | Boot text; observer; policy excision; SP-PL-12 |
| RISK-PL-7 | Ollama, if used, is unauthenticated on loopback and serves cloud models | Privacy | PL-4; digest pinning |
| RISK-PL-8 | Without an external drive, disk loss loses the memory | GOAL §3.1 | UQ-14 (drive: ARCH DQ-11) |
| RISK-PL-9 | SQLite-only constructs block the cloud move | GOAL §4.6 | Portable-SQL lint and PT-3, PT-4 now; CDM-S4 once; PT-1 to PT-8 at the cloud-adapter stage |
| RISK-PL-10 | Injected instructions pull memory through read tools and leak it | Privacy | Scopes, budgets, no dump tool |
| RISK-PL-11 | A host exposes widget metadata or app-only tools to the model, so a model could "click" | I21 | `action_nonce` ([CX] §3.5); SP-PL-14 |
| RISK-PL-12 | Codex hook trust, `.mcpb` reinstall, plugin updates or Keychain prompts may need a user step on some upgrades | GOAL §4.1 | Stable shims; SP-PL-2, SP-PL-4 |
| RISK-PL-13 | A prompt-injected coding agent running as the user can still read the stores directly (T14) | Privacy; GOAL §5 | File deny rules at install ([HK] §14.3); LocalAuthentication for destructive actions; service-account option (SP-PL-17) |

---

## 13. Questions for the user

Covered elsewhere: accounts (UQ-3), the observer and managed-Mac policy for it (UQ-1, UQ-2), the relay (UQ-5), subscription providers (UQ-6), "local now" (UQ-11, TEXTBOOK Q7), employer repositories (TEXTBOOK Q3).

None new. Covered by SPINE UQ-19 (notifications; settled as HOW, ARCH R16; user override only), UQ-20 (memory on a managed Mac; ARCH DQ-5(a)) and UQ-14 (backups: own encrypted archives settled as HOW; the backup drive is ARCH DQ-11). The former local IDs UQ-PL-1, UQ-PL-2 and UQ-PL-3 map to UQ-19, UQ-20 and UQ-14.

---

## 14. Spikes

| Spike | Question | Settles |
|---|---|---|
| SP-PL-1 | With CX-S3: can the `.mcpb` server read `run/creds/…` and reach `run/core.sock`? | D-PL-1 |
| SP-PL-2 | Keychain reads via `/usr/bin/security` without prompts across Python upgrades | §2.9; RISK-PL-12 |
| SP-PL-3 | With CX-S4: can Python 3.14 read the peer's UID and audit token on `run/core.sock`, and check its code signature from the audit token on every message within the hook budget? | T3 |
| SP-PL-4 | Codex and Claude Code hooks calling a fixed shim: any re-trust prompt on upgrade? | PL-14 |
| SP-PL-5 | Does `northstar.localhost` resolve to loopback in the user's browser? Cookie flags (host-only, `Secure`) on `http://northstar.localhost`; local-network-access prompts | PL-10 |
| SP-PL-6 | Excision on a 1 GB synthetic store: 0 hits after the X6 scrub; time | §6.7 |
| SP-PL-7 | Scanner recall (≥ 99%) and false positives | §6.2 |
| SP-PL-8 | LaunchAgents under management, if present, across sleep and wake | §2.2; RISK-PL-2 |
| SP-PL-9 | A canary under the data root never found by `mdfind` | §2.4 |
| SP-PL-10 | Sparse bundle: WAL throughput; mount at login without prompts | PL-3 |
| SP-PL-11 | A documented account-status command for Claude Code and Codex | §6.4; RISK 35 |
| SP-PL-12 | Claude Desktop incognito: tools offered? any signal? | §6.5; RISK-PL-6 |
| SP-PL-13 | With CS7: `cloudflared` to a socket origin; ChatGPT's OAuth client behind Access; passkey or device-bound consent instead of an email code; `sandbox-exec` | §3 |
| SP-PL-14 | With S-R1, S-R2, CD-S13, CS4: are widget-only metadata and app-only tools hidden from the model? | T4; RISK-PL-11 |
| SP-PL-15 | With CDM-S4: the DDL applies once on Postgres 17; the portable-SQL lint catches each seeded SQLite-only construct. PT-1 and PT-2 wait for the cloud-adapter stage | SD-26; RISK-PL-9 |
| SP-PL-16 | Reader cookie jar and URL handler: can a dedicated browser profile, a site app, or a small WKWebView shell hold the only Reader cookie, with a URL handler so chat links still open signed in? | T6; PL-10; RT-2b |
| SP-PL-17 | Privilege separation: can a dedicated service account own the data root, credentials, spool, pin cache and backups, with peer checks by audit token, on a managed Mac without breaking the 300 ms hook budget? Also: can the core, as a LaunchAgent, raise a LocalAuthentication prompt? | T14; PL-16; RISK-PL-13 |

---

## 15. Goal-fidelity check

| GOAL item | Where served | Status |
|---|---|---|
| §4.1 No rituals | One-time install; self-repair; alerts as states; policy excision | **Partial** (RISK-PL-2, RISK-PL-12; UQ-19) |
| §4.2 AI-said first-class | Scans, tiers and egress never read the speaker | Not weakened; work-scope "no new exposure" may route one vendor's work content to local models, watched by the parity sentinel (SD-38, RISK 30) |
| §4.3 The AI manages it | Privacy, backups, migrations, repair run without the user; correction and excision optional | **Partial** (RISK-PL-2) |
| §4.4 Two architectures, one core | One set of stores serves both projections and the Reader | Met by design |
| §4.5 Drift and continuity | Fail-open spooling; cached pins; fast relay failure; cross-surface delivery | **Partial** (RISK 27: relay while the Mac sleeps) |
| §4.6 Product-agnostic core | Policy keyed on capabilities and generic families (D-PL-6, RT-13) | **Partial**: holds by design and test; erosion over time is RISK 26 |
| §4.6 Local now | Local stores and services; egress gate; every off-Mac flow logged | **Partial** (UQ-11; RISK 13; RISK-PL-3, UQ-20) |
| §4.6 Cloud later | Swap list, forwarder, migration, PT-1 to PT-8 | Planned (RISK-PL-9) |
| §4.6 Personal first, enterprise later | Allowlist with neutral delivery; tenancy and SSO seams; 3P only as an addition | **Partial** (RISK 35) |
| §4.7 Robust maintainer | Sentinels, freezes, release rollback, model changes as deployments, I19 | **Partial** (RISK 6, RISK-PL-2) |
| §4.8 Built and evaluated | Red-team and portability suites; platform fault injection | Planned |
| §5 Injection through stored memory | T1–T8, T14; one rendering rule; RT-4, RT-14, RT-17 | **Partial** (RISK 9, RISK-PL-10; T14: a prompt-injected coding agent can still read the store until SP-PL-17, RISK-PL-13) |
| §6 Maintains itself | §8; excision and backups self-verified | **Partial** (RISK-PL-2, RISK 36) |
| Privacy (SYN §5 item 9) | §6 | **Partial** (RISK-PL-4, RISK-PL-5, RISK-PL-6) |

No reframe is adopted. Each limit found is a risk or a question.

---

## Sources

**Project documents:** GOAL; SPINE §4.4–§4.9, §5.7, §6, §7, §8.4–§8.5, §10–§11, Appendix B; TEXTBOOK §8.8–§8.15, §9.1–§9.2, §10.1–§10.3, §10.8, §12, §13.2 H, §15 Q3, Q7; [CD] §4.1, §5–§6; [GD] §6.2, §9, §10.2, §13; [OBS] §4.1–§4.8; [CX] §4–§7, §10; SYN §3.5, §5, §7.4, §8; [10] F1, F6, F14–F16, R4, R7; [13] §C, §E–§G, §I.

**Product facts verified for this document on 2026-10-08:**

- **V-PL-1** Streamable HTTP servers "MUST validate the `Origin` header … to prevent DNS rebinding attacks", SHOULD bind to localhost, SHOULD authenticate. https://modelcontextprotocol.io/specification/2025-11-25/basic/transports
- **V-PL-2** MCP authorization: OAuth 2.1 resource servers; RFC 9728 and RFC 8707 required; PKCE S256; audience validation; no token passthrough; stdio takes credentials from the environment instead. https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization
- **V-PL-3** `secure_delete` zeroes deleted content; FAST leaves freelist traces; it applies "only … to ordinary tables". https://sqlite.org/pragma.html#pragma_secure_delete
- **V-PL-4** Anthropic API inputs and outputs deleted "within 30 days" by default, up to 2 years if flagged (page dated 2026-07-01); third-party claims of 7 days not confirmed (Unv). https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data
- **V-PL-5** Batch results available 29 days; `DELETE /v1/messages/batches/{id}` once ended. https://platform.claude.com/docs/en/build-with-claude/batch-processing ; https://platform.claude.com/docs/en/api/messages/batches/delete
- **V-PL-6** OpenAI API abuse logs up to 30 days; no training by default; `/v1/batches` state kept "until deleted". https://developers.openai.com/api/docs/guides/your-data
- **V-PL-7** Ollama binds `127.0.0.1:11434`; cross-origin from `127.0.0.1` and `0.0.0.0` by default; cloud-hosted models exist; no authentication documented. https://docs.ollama.com/faq
- **V-PL-8** Cloudflare Access: validate `Cf-Access-Jwt-Assertion` against the team certs and check `aud`. https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/
- **V-PL-9** Node `http.request` `socketPath`: "Unix domain socket". https://nodejs.org/api/http.html
- **V-PL-10** MCPB servers run locally over stdio; no sandbox stated; organization allowlists exist; `sensitive` config storage unspecified. https://claude.com/docs/connectors/building/mcpb ; https://github.com/modelcontextprotocol/mcpb/blob/main/MANIFEST.md
- **V-PL-11** Install-time checks (`fdesetup status`, `sw_vers`, binaries on PATH) run on the device; results are kept locally by `northstar doctor`.

Other product facts are relied on from SPINE Appendix B and the connector documents, with their dates.

---

## Consistency fixes (2026-10-08)

| Issue | Change in this document |
|---|---|
| X01 | Adopted the [CX] §1.2/§2 tool catalog. §3.3 relay tools are now `northstar_context`, `northstar_note`, `northstar_fetch`, `northstar_book` and the [CX] §2.4 app-only tools; `northstar_page` and `northstar_correct` are gone, and `northstar_restart` stays off the relay. T4 uses `northstar_note(kind: correction)` and `northstar_widget_action(action: apply_correction)`. `action_nonce` ([CX] §3.5) is the single name for the click credential in §2.8, §3.3, T4, RT-6, §10 and RISK-PL-11 |
| X04 | Kept PL-5 and UQ-PL-3 as the one backup policy: Time Machine excluded, own encrypted archives, optional named drive. UQ-PL-3 now says it replaces UQ-CDM-1. §2.5 restore: BookLedger, Edition and the landmark tables are canonical; they are backed up and restored, and only BlockVersion renders, `index` and `artifacts` are rebuilt |
| X06 | §3.3 relay limit: up to 12,000 characters on a session's first `northstar_context` call, and otherwise the [CX] §2.7 budget per tool (per turn 4,000, book 2,400, fetch 8,000). This replaces the flat 10,000 |
| X11 | §6.1 states the one scope vocabulary and says `private` is a tier only. It adds `held` as a flag on a scope or session ([HK] §7), not a scope kind: no egress, no packs, no Book. A `held` row goes in the §6.3 table, `held` joins `session_ctx` (§10), and §3.3 and RT-7 exclude held content |

---

## Review revisions (2026-10-08)

The full review record is [`REVIEW.md`](../REVIEW.md).

| Finding | What changed here |
|---|---|
| SEC-6 | Device facts left the document. §0 item 4 is now a conditional that install checks. §2.2 cites `man launchd.plist` (checked 2026-10-08); §2.5 cites `man tmutil`. §3.3 names no proxy vendor ("if a TLS-inspecting proxy is on the path"). D-PL-3 says "checked at install". RISK-PL-3 drops "FileVault is off today". UQ-PL-2 and SP-PL-8 state conditions, not this Mac's setup. V-PL-11 now says install-time checks run on the device and `northstar doctor` keeps the results locally |
| SEC-1 | §1 adds B5: a prompt-injected AI agent running as this user is in scope as T14. Out of scope narrows to malware deliberately targeting Northstar. §2.8 and PL-16: destructive and policy actions need a LocalAuthentication prompt (Touch ID or password), never a y/N on stdin; step-up is bound to one explicit destructive-action confirmation, not any recent launch token. Service-account privilege separation is an option behind SP-PL-17, not a precondition. §7.1 moves the injected agent in scope; §7.2 adds T14; §7.3 adds RT-17; RISK-PL-1 narrowed; RISK-PL-13 added; §15 keeps GOAL §5 Partial with T14 named |
| SEC-8 | §2.4 registers `run/pincache/` (entries expire after 30 minutes and at session end), `tmp/`, `run/workers/` and the later forwarder cache in `ops.registered_store`, purged at X5. §6.7 X9 includes them. §6.8 lists, from context receipts, every session an item was delivered into, naming local vendor transcript files as copies Northstar does not edit |
| MR-3 | §2.5 ledger restore replays `jobs.db` outcomes and the durable journal of non-model ledger writers (in `intake.db`, backed up with it). §10 Needs updated |
| MR-5 | §6.7 X5 runs as the resumable saga of [CDM] §10.2. X9 uses one haystack rule. On failure the saga stays `in_progress` and resumes at boot and nightly; writers are not frozen indefinitely, and X3 keeps suppressing delivery. User and policy excision share the saga. This also settles the ROB smaller issue on X9 against [CDM] §10.2 |
| SEC-11 | §2.8: the Reader moves to `northstar.localhost` with a host-only cookie and an updated Host allowlist; at most 10 corrections a minute, extras become proposals; step-up for bulk moves and hides; `Sec-Fetch-User` and page nonces are not relied on; a separate cookie jar is an option behind SP-PL-16 (new). T6, RT-2b, PL-10 and SP-PL-5 updated |
| SEC-12 | §2.8: C04 enforces a per-channel fidelity ceiling (an `mcp_*` channel never claims `verbatim_live`); hook and MCP processes get separate credentials; the `.mcpb` `sensitive` fallback gets a `model_reported` ceiling and short rotation. T3, RT-5 and PL-1 updated |
| SEC-10 | §2.8 and PL-17: write and call budgets per credential and session. Over budget, content is still captured and processing waits; the tool says "Saved; processing is delayed"; [MT] sentinel #20 fires. Spend share per connector follows [MT] §9.5. §3.3 limits, T7 and the C04 interface updated |
| SEC-9 | §3.3 lists exactly what crosses the relay. The vendor choice is ARCH DQ-4(iii) (a) or (b), not settled HOW (§3.1, §3.2 labels). Under Option B the R default is "only items whose source spans OpenAI already holds", with an opt-in for the rest (§3.3, §6.3) |
| FEAS-4 | §3.2 Option A: the personal Platform organization; added through Plugins → Add custom MCP server → Tunnel → Create, as a plugin; the authorization server is not tunneled; the Platform organization's terms apply |
| SEC-2 | T4 and §3.3 use the TEXTBOOK §9.2 chat-correction conditions. RT-6b added |
| SEC-4 | T2 uses one rendering rule for every model-facing artifact ([AC] §3.2 rule 9) and CK-10. RT-4 restated; RT-14 extended with agentic payloads |
| CPLX-9 | §4.4 split: ports, `tenant_id` and a portable-SQL lint stay in CI now; Postgres triggers and the Postgres CI matrix move to the cloud-adapter stage; CDM-S4 checks the DDL once. §0 item 8, §2.6, SP-PL-15 and RISK-PL-9 follow |
| SEC smaller issues | Peer checks use the audit token plus a code-signing check on every message, never the PID (§2.7, §2.8, SP-PL-3). The hook client scans before writing the spool (§6.2). Eval egress needs DQ-3 as well as DQ-6 (§6.3). Mirror and EPUB use the Reader's renderer rules (§6.3). Multi-participant sessions get neutral delivery only (§6.4). Reader search uses POST or a fragment, with neutral titles (§6.4). Relay consent by passkey or device-bound consent (§3.2, SP-PL-13). RT-4 says "never gain authority and never render unneutralised". Step-up bound to a confirmation and the `.mcpb` fallback ceiling (§2.8) |
| CONS smaller issue | §8.4: the maintainer's J10 sweep and J10d sentinel results reach `ops.db` through C21 over the socket; C21 stays the single writer |

---

## Final-gate fixes (2026-10-08)

Carried task (a) of the review had not finished here. Each change is a HOW change; no non-negotiable is weakened.

| Finding | What changed |
|---|---|
| Carried task (a), R11, R16 | §13 asks nothing new: the local questions UQ-PL-1, UQ-PL-2 and UQ-PL-3 are SPINE UQ-19, UQ-20 and UQ-14, and the SPINE IDs replace them in §0 item 5, §2.5, §8.1, §8.5, §9, the Risks and §15. PL-5 and PL-15 read "Settled as HOW (ARCH R16)"; the backup drive is ARCH DQ-11 and the managed-Mac question is ARCH DQ-5(a). Log rows above keep their original wording as a record |
