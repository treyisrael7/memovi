# Desktop Client Architecture

# Purpose

This document describes the flagship Memovi desktop client under `apps/desktop/`.

It explains why Memovi is desktop-first, how the client separates from the
backend, how it communicates with the platform API, and how the shell expands
into future product pages without redesign.

# Why Desktop-First

Memovi is a knowledge operating system, not a chatbot wrapper or document viewer.
The flagship product surface is a native desktop application because desktop
enables:

* A persistent knowledge workspace with local window lifecycle
* Future local models and offline-capable reasoning surfaces
* Safe filesystem and environment capabilities under a permission model
* A richer operating-system feel without moving business logic into the UI

The desktop client is still a client. The FastAPI platform remains the source of
truth for documents, memory, search, intelligence, workspaces, models, and
automation.

# Separation of Concerns

| Layer | Owns | Does not own |
| --- | --- | --- |
| `apps/desktop` | Window lifecycle, navigation shell, application UI state, theme, startup experience, backend connection management, conversation presentation, authentication presentation (login/register/logout, session restore) | Documents, memory, search, intelligence, workspaces (domain rules), models, automation, session issuance / password hashing |
| `apps/api` + `packages/*` | Domain rules, persistence, providers, workers, API contracts, session cookies | Desktop windowing, UI layout, local theme preference |

Desktop never:

* Accesses the database directly
* Embeds provider-specific AI logic
* Duplicates ingestion, search ranking, or reasoning workflows
* Owns workspace or document invariants
* Stores passwords or session tokens in local storage
* Issues or validates session credentials itself

Desktop may:

* Call platform HTTP APIs with cookie credentials
* Cache presentation state for the current session
* Restore last page / workspace preferences per user locally
* Show connection and readiness status
* Navigate between product pages
* Render streaming tokens and markdown for conversation UX
* Present login, registration, logout, and session-expiry UX over `/auth/*`

# Package Layout

```text
apps/desktop/
  src/                      # React + TypeScript UI (Vite)
    api/                    # Thin HTTP client over platform contracts
    components/             # Shell chrome + product pages
      ui/                   # Design-system primitives (layout, inputs,
                             # feedback, display, navigation) reused across pages
    navigation/             # Page registry for the primary navigation
    state/                  # Application shell state, incl. cross-page
                             # "seed" handoffs (e.g. open Chat/Knowledge/
                             # Documents from another page with context)
    styles/                 # Tokens (theme.css), component styles, shell/page CSS
  src-tauri/                # Tauri / Rust host (windowing only)
```

The design system is documented in
[`../design/DESIGN_SYSTEM.md`](../design/DESIGN_SYSTEM.md).

The Rust host owns native window lifecycle. Product UI and API consumption live
in the TypeScript frontend. Backend domains stay in Python packages.

# Backend Communication

Local development defaults to `http://127.0.0.1:8000`.

Override with `VITE_MEMOVI_API_BASE` when needed. The Vite/Tauri origin defaults
to `http://127.0.0.1:1420` so it stays same-site with the API and can send the
`memovi_session` cookie under `SameSite=Lax`. Do not mix `localhost` and
`127.0.0.1` across the webview and API base URL.

All authenticated API calls use `credentials: "include"` (including SSE streams
and document uploads) so the HttpOnly session cookie is attached. Desktop never
reads or writes the cookie value itself.

The shell probes:

1. `GET /auth/me` — restore or reject the session before product pages load
2. `GET /health` — process liveness
3. `GET /ready` — dependency readiness (database, migrations, search, workspace, …)
4. `GET /workspaces` — populate the workspace selector when authenticated and reachable
5. `GET /conversations/models` — populate the model selector

Diagnostics for connection status, environment, and per-component readiness are
also surfaced to the user directly in Settings → Diagnostics, so operators do
not need developer tools to understand backend health.

Connection states:

| Status | Meaning |
| --- | --- |
| `checking` | Initial or in-flight probe |
| `connected` | Healthy and ready |
| `degraded` | Reachable but `/ready` reports incomplete dependencies |
| `disconnected` | Unreachable or unhealthy |

Knowledge-scoped requests attach `X-Memovi-Workspace-Id` from the active
workspace selection. The desktop never invents ownership; it only forwards the
selected workspace to the API.

The shell reconnects on a short poll interval and exposes a manual retry action.
Errors are user-facing and operational (`task backend`), not provider internals.

The API allows local desktop and web origins through CORS so presentation
clients can call the same contracts from a browser-like webview without embedding
a second transport stack.

# Authentication

Desktop is the primary authenticated client over the existing local
email/password + HttpOnly session cookie architecture. It does not introduce
JWTs, alternate session stores, or client-side password persistence. Server
auth remains documented in [`AUTHORIZATION.md`](AUTHORIZATION.md).

## Flow

```text
App start
  │
  ├─ authStatus = checking
  ├─ GET /auth/me  (cookie credentials)
  │     ├─ 200 → authenticated → restore page/workspace prefs → Shell
  │     └─ 401 / network → anonymous → AuthGate (login / register)
  │
Login / Register
  │
  ├─ POST /auth/login or /auth/register  { email, password }
  ├─ Set-Cookie: memovi_session (HttpOnly; Secure on HTTPS)
  └─ authenticated → Shell (workspaces + models load)

Logout (Settings → Account)
  │
  ├─ confirmation dialog
  ├─ POST /auth/logout
  ├─ clear local shell state (workspace, models, seeds)
  └─ anonymous → AuthGate

401 on a protected API call while authenticated
  │
  ├─ session_expired dialog
  └─ acknowledge → AuthGate
```

## Session lifecycle

| Event | Behavior |
| --- | --- |
| Restore | Startup calls `GET /auth/me`. Success opens the product shell; failure shows auth screens only. |
| Persist | Browser/WebView stores the HttpOnly cookie. Desktop does not copy tokens into `localStorage`. |
| Preferences | Theme is local. Last page and active workspace id are restored per user id after login. |
| Logout | Revokes the server session, clears the cookie, and resets shell state. |
| Expiry / revoke | Protected `apiFetch` / stream / upload paths notify auth state on `401` and surface the session-expired dialog. |

Unauthenticated users never reach the product shell or page registry. There is
no client-side route library; `App` gates on `authStatus` before rendering
`Shell`.

# Application Shell

The shell provides:

* Sidebar with the primary navigation (Home, Conversations, Documents,
  Knowledge, Search, Workflows, Activity, Settings)
* Top bar with active workspace, active model, and connection status
* Main content area
* Status bar with connection details and retry
* Light / dark theme toggle (persisted locally)
* Startup connection detection after authentication
* Account email in the top bar; sign-out from Settings → Account
* Design-system UI primitives (`components/ui/`) for layout, inputs, feedback,
  display, and navigation — used consistently across every page. See
  [`../design/DESIGN_SYSTEM.md`](../design/DESIGN_SYSTEM.md).

Every page registered in `src/navigation/pages.ts` is a real, working surface.
The registry intentionally contains no placeholder entries: a page is only
added once it has a working implementation, so navigation always reflects
current product capability.

# Conversation Flow

Chat is a thin presentation surface over Intelligence conversation APIs.

```text
Desktop Chat
  │
  ├─ GET  /conversations                 list sidebar
  ├─ POST /conversations                 new conversation
  ├─ PATCH /conversations/{id}           rename
  ├─ DELETE /conversations/{id}          delete
  ├─ GET  /conversations/{id}/messages   load history
  ├─ GET  /conversations/models          model selector
  └─ POST /conversations/{id}/messages/stream
         │
         ├─ event: token   incremental assistant text
         ├─ event: done    final answer + citations + metadata
         └─ event: error   clean failure surface
```

Send path:

1. User submits a message (Enter) or inserts a newline (Shift+Enter).
2. Desktop creates a conversation if none is active.
3. Desktop appends optimistic user + pending assistant bubbles.
4. Desktop opens an SSE stream with the selected workspace header and model.
5. Tokens append to the assistant bubble; Stop aborts via `AbortController`.
6. `done` replaces the pending bubble with the persisted assistant message.
7. History reloads from the API after navigation or workspace switches.

Workspace switching reloads the conversation list from the backend so chats
remain isolated by ownership. Model selection is sent on each stream/send
request (`provider` + `model`) and does not change backend defaults permanently.

Chat also polls capability executions for the active workspace/conversation and
renders confirmation dialogs, progress, success/failure, overwrite Replace
prompts, undo messaging for trash deletes, and browser navigation/download/
search presentation. Approve, deny, and overwrite retries call the Capability
Execution Engine over HTTP; desktop never invokes capabilities or touches the
filesystem/browser APIs locally. See
[`CAPABILITY_EXECUTION.md`](CAPABILITY_EXECUTION.md),
[`FILESYSTEM_WRITE.md`](FILESYSTEM_WRITE.md), and
[`BROWSER_CAPABILITY.md`](BROWSER_CAPABILITY.md).

Markdown rendering, code-block copy, message copy, retry on failed responses,
and auto-scroll are presentation concerns only.

Assistant citations are interactive. Clicking a citation resolves the most
specific openable source using existing APIs and AppState seeds: knowledge
item (`GET /memory/by-document/{document_id}` → `openKnowledgeItem`), then
document (`GET /documents/{id}` → `openDocument`), then Search scoped to that
document (`openSearchSource`). If none of those destinations can be opened,
Chat shows a toast instead of failing silently. Chat stays mounted after first
visit so inspecting a source does not reset the active conversation. Conversation
response DTOs currently include `document_id` and `chunk_id` only — not
`knowledge_item_id` — so knowledge linking is resolved client-side.

A conversation can also be started *from* Documents or Knowledge ("Ask about
this document" / "Ask about this"): those pages create a conversation via
`POST /conversations`, then hand the new conversation id and a draft prompt to
Chat through `AppStateContext` (`startConversationAbout` / `chatSeed`). Chat
picks up the seed on mount, selects the conversation, and prefills the
composer — the user still presses Send. This keeps conversation creation and
message history on the Intelligence API; the seed is only a UI handoff.

# Product Pages

Pages are registered in `src/navigation/pages.ts`. Every entry is implemented:

* **Home** — connection/workspace/model summary and shortcuts into Documents
  and Conversations
* **Conversations** (Chat) — the grounded chat experience described above
* **Documents** — import, processing status, and lifecycle (see below)
* **Knowledge** — Knowledge Explorer: browse extracted entities, concepts,
  relationships, and sources
* **Collections** — flat knowledge organization: create/rename/delete, add/remove
  members with reasons, statistics, and recent activity (see
  [`COLLECTIONS.md`](COLLECTIONS.md))
* **Tags** — complementary cross-cutting labels: create/edit/delete, assign to
  documents/knowledge/conversations/workflows, resource metadata
  (title/description/notes), and Search multi-tag filters
* **Search** — global, per-document, knowledge, collection-, and tag-filtered
  search with recent searches (see below)
* **Workflows** — library, run, progress, history
* **Activity** — a cross-domain timeline of what happened in the workspace
  (see below)
* **Settings** — model, workspace, capability policy, appearance, account
  (sign-out), and diagnostics (see below)

Each page consumes existing platform APIs only; none owns business logic:

* Documents → Documents API (`/documents`)
* Knowledge → Memory + Documents + Search APIs (see [`KNOWLEDGE_EXPLORER.md`](KNOWLEDGE_EXPLORER.md))
* Collections → Collections API (`/collections`) owned by Memory
* Tags → Tags + resource-metadata APIs (`/tags`, `/resource-metadata`) owned by Memory
* Search → Search API (`/search`), optional `collection_id` and `tag_id` filters
* Workflows → `/workflows` API (library, execute, history); approvals still via
  Capability Execution Engine
* Activity → composes `/documents`, `/memory`, `/workflows/history`, and
  `/capabilities/executions/audit` into one timeline, client-side
* Settings → `/conversations/models`, `/workspaces`, `/capabilities`, and the
  connection probe used for diagnostics

# Documents

Documents is the primary ingestion surface: drag-and-drop or file-picker
upload, live processing status, reprocessing, and deletion. User-visible
status labels and indexed readiness are documented in
[`DOCUMENT_PIPELINE.md`](DOCUMENT_PIPELINE.md).

```text
Desktop Documents
  │
  ├─ GET    /documents                     list + processing status
  ├─ GET    /documents/{id}                detail
  ├─ GET    /memory                        knowledge presence → Indexed badge
  ├─ POST   /documents                     upload (multipart, progress via XHR)
  ├─ POST   /documents/{id}/reprocess      re-queue ingestion / retry
  └─ DELETE /documents/{id}                remove document + artifact + knowledge
```

Each document reports `processing_status` (`pending` → `extracting` /
`normalizing` → `completed` / `failed` / `cancelled`) plus optional attempt and
timing fields. Failure reasons surface in the detail pane with a primary
**Retry processing** action. While any document is in flight — or Documents
`completed` but Memory has not listed knowledge yet — the page polls on a short
interval so status advances without a manual refresh. Deletion is confirmed
through the shared `ConfirmDialog` before the API call runs. "Ask about this
document" opens a grounded conversation, gated on processing and indexing
having finished.

# Search

Search is a dedicated experience over the same knowledge index used by
Knowledge and Chat citations — it does not introduce a second search
implementation. Documents that are still processing or failed are called out
explicitly so empty results are not mistaken for "no knowledge."

```text
Desktop Search
  │
  ├─ GET /documents                                     document picker + status
  ├─ GET /memory                                        indexed readiness
  └─ GET /search?q&mode&document_id                     hybrid/keyword/semantic
```

Scopes map onto existing search modes: "All content" (hybrid), "This
document" (keyword, scoped to a chosen document), and "Knowledge" (semantic).
Recent searches persist per-workspace in local storage as a convenience only;
they are not synced to the backend. Selecting a result opens it in Knowledge;
"Ask about this" opens a grounded conversation.

# Knowledge Explorer

Knowledge is a thin inspection surface over Memory and Documents.

```text
Desktop Knowledge
  │
  ├─ GET /memory/dashboard
  ├─ GET /memory?document_id&source_type&entity_type
  ├─ GET /memory/{id}
  ├─ GET /memory/concepts
  ├─ GET /memory/relationships
  ├─ GET /documents
  └─ GET /documents/{id}
```

Sections: Overview, Entities, Concepts, Relationships, Sources. Global search
lives on the dedicated Search page and opens results here for inspection
rather than duplicating a second search UI inside the explorer.

Selecting an item shows summary, source document (with processing status),
related concepts/entities, confidence, and last updated — the provenance a
user needs to trust a piece of knowledge. Workspace switching reloads
explorer data for the active workspace header. Desktop performs no ranking,
materialization, or ownership logic.

# Activity

Activity is a read-only timeline explaining what has happened in the active
workspace: upload started, processing in progress / completed / failed, re-index
requested, knowledge extracted, workflows executed, and capabilities executed.
It is composed entirely from existing durable records — document processing
state, memory records, workflow history, and the Capability Execution Engine's
audit log (`/capabilities/executions/audit`) — merged and sorted client-side.
While documents are still processing (or indexing is catching up), Activity
refreshes on a short poll. Desktop does not introduce a new audit store; it
presents the platform's existing observability and audit data in product terms.

# Settings

Settings consolidates configuration that previously had no dedicated home:

* **General** — active model (`/conversations/models`) and theme
* **Account** — signed-in email and confirmed sign-out (`POST /auth/logout`)
* **Workspaces** — list, switch, and create workspaces (`/workspaces`)
* **Capabilities** — per-capability permission mode
  (`PUT /capabilities/{id}/permission-mode`); the server remains the sole
  authority on whether an action is actually allowed at execution time
* **Diagnostics** — the same connection snapshot (`/health`, `/ready`) used by
  the top bar and status bar, presented with per-component detail

Settings never exposes internal implementation details (table names, provider
SDK identifiers, queue internals, or session token values); it speaks in product
terms (model, workspace, capability, appearance, account, diagnostics).

# Running Locally

Prerequisites beyond the repository defaults:

* Rust toolchain (`rustup`)
* Platform linker / C++ build tools required by Tauri on the host OS

```bash
task backend          # API on :8000
task desktop          # Tauri desktop shell
```

Or:

```bash
pnpm --filter @memovi/desktop tauri:dev
```

# Related Documents

* [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — platform blueprint
* [`../PRODUCT_VISION.md`](../PRODUCT_VISION.md) — desktop-first product identity
* [`../testing/DESKTOP_TESTING.md`](../testing/DESKTOP_TESTING.md) — CI, smoke tests, release checklist
* [`repository-architecture.md`](repository-architecture.md) — monorepo layout
* [`intelligence-architecture.md`](intelligence-architecture.md) — reasoning and conversations
* [`KNOWLEDGE_EXPLORER.md`](KNOWLEDGE_EXPLORER.md) — knowledge inspection surface
* [`CAPABILITY_FRAMEWORK.md`](CAPABILITY_FRAMEWORK.md) — future desktop capabilities
* [`AUTHORIZATION.md`](AUTHORIZATION.md) — server session and authorization model
