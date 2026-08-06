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
| `apps/desktop` | Window lifecycle, navigation shell, application UI state, theme, startup experience, backend connection management, conversation presentation | Documents, memory, search, intelligence, workspaces (domain rules), models, automation |
| `apps/api` + `packages/*` | Domain rules, persistence, providers, workers, API contracts | Desktop windowing, UI layout, local theme preference |

Desktop never:

* Accesses the database directly
* Embeds provider-specific AI logic
* Duplicates ingestion, search ranking, or reasoning workflows
* Owns workspace or document invariants

Desktop may:

* Call platform HTTP APIs
* Cache presentation state for the current session
* Show connection and readiness status
* Navigate between product pages
* Render streaming tokens and markdown for conversation UX

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

Override with `VITE_MEMOVI_API_BASE` when needed.

The shell probes:

1. `GET /health` — process liveness
2. `GET /ready` — dependency readiness (database, migrations, search, workspace, …)
3. `GET /workspaces` — populate the workspace selector when the API is reachable
4. `GET /conversations/models` — populate the model selector

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

# Application Shell

The shell provides:

* Sidebar with the primary navigation (Home, Conversations, Documents,
  Knowledge, Search, Workflows, Activity, Settings)
* Top bar with active workspace, active model, and connection status
* Main content area
* Status bar with connection details and retry
* Light / dark theme toggle (persisted locally)
* Startup connection detection
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
* **Search** — global, per-document, and knowledge search with recent
  searches (see below)
* **Workflows** — library, run, progress, history
* **Activity** — a cross-domain timeline of what happened in the workspace
  (see below)
* **Settings** — model, workspace, capability policy, appearance, and
  diagnostics (see below)

Each page consumes existing platform APIs only; none owns business logic:

* Documents → Documents API (`/documents`)
* Knowledge → Memory + Documents + Search APIs (see [`KNOWLEDGE_EXPLORER.md`](KNOWLEDGE_EXPLORER.md))
* Search → Search API (`/search`)
* Workflows → `/workflows` API (library, execute, history); approvals still via
  Capability Execution Engine
* Activity → composes `/documents`, `/memory`, `/workflows/history`, and
  `/capabilities/executions/audit` into one timeline, client-side
* Settings → `/conversations/models`, `/workspaces`, `/capabilities`, and the
  connection probe used for diagnostics

# Documents

Documents is the primary ingestion surface: drag-and-drop or file-picker
upload, live processing status, reprocessing, and deletion.

```text
Desktop Documents
  │
  ├─ GET    /documents                     list + processing status
  ├─ GET    /documents/{id}                detail
  ├─ POST   /documents                     upload (multipart, progress via XHR)
  ├─ POST   /documents/{id}/reprocess      re-queue ingestion
  └─ DELETE /documents/{id}                remove document + artifact + knowledge
```

Each document reports `processing_status` (`pending` → `extracting` /
`normalizing` → `completed` or `failed`) and, on failure, a
`processing_failure_reason`. While any document is still processing, the page
polls the list on a short interval so status advances without a manual
refresh. Deletion is confirmed through the shared `ConfirmDialog` before the
API call runs. "Ask about this document" opens a grounded conversation, gated
on the document having finished processing.

# Search

Search is a dedicated experience over the same knowledge index used by
Knowledge and Chat citations — it does not introduce a second search
implementation.

```text
Desktop Search
  │
  ├─ GET /documents                                     document picker
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
workspace: documents uploaded, processing completed/failed, knowledge
extracted, workflows executed, and capabilities executed. It is composed
entirely from existing durable records — document processing state, memory
records, workflow history, and the Capability Execution Engine's audit log
(`/capabilities/executions/audit`) — merged and sorted client-side. Desktop
does not introduce a new audit store; it presents the platform's existing
observability and audit data in product terms.

# Settings

Settings consolidates configuration that previously had no dedicated home:

* **General** — active model (`/conversations/models`) and theme
* **Workspaces** — list, switch, and create workspaces (`/workspaces`)
* **Capabilities** — per-capability permission mode
  (`PUT /capabilities/{id}/permission-mode`); the server remains the sole
  authority on whether an action is actually allowed at execution time
* **Diagnostics** — the same connection snapshot (`/health`, `/ready`) used by
  the top bar and status bar, presented with per-component detail

Settings never exposes internal implementation details (table names, provider
SDK identifiers, queue internals); it speaks in product terms (model,
workspace, capability, appearance, diagnostics).

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
* [`repository-architecture.md`](repository-architecture.md) — monorepo layout
* [`intelligence-architecture.md`](intelligence-architecture.md) — reasoning and conversations
* [`KNOWLEDGE_EXPLORER.md`](KNOWLEDGE_EXPLORER.md) — knowledge inspection surface
* [`MODEL_PROVIDER_FRAMEWORK.md`](MODEL_PROVIDER_FRAMEWORK.md) — model abstractions
* [`CAPABILITY_FRAMEWORK.md`](CAPABILITY_FRAMEWORK.md) — future desktop capabilities
