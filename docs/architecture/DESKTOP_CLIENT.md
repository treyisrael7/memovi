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
* Navigate between reserved product pages
* Render streaming tokens and markdown for conversation UX

# Package Layout

```text
apps/desktop/
  src/                      # React + TypeScript UI (Vite)
    api/                    # Thin HTTP client over platform contracts
    components/             # Shell chrome + Chat page
    navigation/             # Page registry for future surfaces
    state/                  # Application shell state
    styles/                 # Theme and layout
  src-tauri/                # Tauri / Rust host (windowing only)
```

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

* Sidebar with a page registry
* Top bar with active workspace, active model, and connection status
* Main content area
* Status bar with connection details and retry
* Light / dark theme toggle
* Startup connection detection
* Chat page for the conversation experience

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
renders pending-approval prompts plus executing / completed / failed / cancelled
states. Approve and deny call the Capability Execution Engine over HTTP; desktop
never invokes capabilities locally. See [`CAPABILITY_EXECUTION.md`](CAPABILITY_EXECUTION.md).

Markdown rendering, code-block copy, message copy, retry on failed responses,
and auto-scroll are presentation concerns only.

# Future Expansion

Pages are registered in `src/navigation/pages.ts`:

* Home (available)
* Chat (available)
* Knowledge (available) — Knowledge Explorer
* Documents
* Search
* Workspaces
* Models
* Activity
* Capabilities
* Settings

Unavailable pages render a reserved placeholder inside the same shell. Adding a
real page means implementing a view and flipping `available` — not redesigning
navigation, windowing, or connection management.

Future desktop features should continue to consume platform APIs:

* Knowledge → Memory + Documents + Search APIs (see [`KNOWLEDGE_EXPLORER.md`](KNOWLEDGE_EXPLORER.md))
* Documents → Documents API
* Search → Search API
* Workspaces → Workspaces API + `X-Memovi-Workspace-Id`
* Models → future Models HTTP surface over `packages/models`
* Capabilities → Capability Framework (`packages/automation`) with desktop
  approval UX later

# Knowledge Explorer

Knowledge is a thin inspection surface over Memory, Documents, and Search.

```text
Desktop Knowledge
  │
  ├─ GET /memory/dashboard
  ├─ GET /memory?document_id&source_type&entity_type
  ├─ GET /memory/{id}
  ├─ GET /memory/concepts
  ├─ GET /memory/relationships
  ├─ GET /documents
  ├─ GET /documents/{id}
  └─ GET /search?q&mode&document_id&source_type
```

Sections: Overview, Search, Concepts, Entities, Relationships, Sources.

Selecting an item shows summary, source document, related concepts/entities,
confidence, and last updated. Workspace switching reloads explorer data for the
active workspace header. Desktop performs no ranking, materialization, or
ownership logic.

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
