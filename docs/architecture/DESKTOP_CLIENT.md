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
| `apps/desktop` | Window lifecycle, navigation shell, application UI state, theme, startup experience, backend connection management | Documents, memory, search, intelligence, workspaces (domain rules), models, automation |
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

# Package Layout

```text
apps/desktop/
  src/                      # React + TypeScript UI (Vite)
    api/                    # Thin HTTP client over platform contracts
    components/             # Shell chrome (sidebar, content, status)
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
3. `GET /workspaces` — display the active workspace label when the API is reachable

Connection states:

| Status | Meaning |
| --- | --- |
| `checking` | Initial or in-flight probe |
| `connected` | Healthy and ready |
| `degraded` | Reachable but `/ready` reports incomplete dependencies |
| `disconnected` | Unreachable or unhealthy |

The shell reconnects on a short poll interval and exposes a manual retry action.
Errors are user-facing and operational (`task backend`), not provider internals.

The API allows local desktop and web origins through CORS so presentation
clients can call the same contracts from a browser-like webview without embedding
a second transport stack.

# Application Shell

The current milestone ships architecture only:

* Sidebar with a page registry
* Main content area
* Status bar with connection, workspace, and model placeholders
* Light / dark theme toggle
* Startup connection detection

No chat interface, document management UI, settings pages, or automation UI yet.

# Future Expansion

Pages are registered in `src/navigation/pages.ts`:

* Home (available)
* Chat
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

* Conversations → Conversation / Reasoning API
* Documents → Documents API
* Search → Search API
* Workspaces → Workspaces API + `X-Memovi-Workspace-Id`
* Models → future Models HTTP surface over `packages/models`
* Capabilities → Capability Framework (`packages/automation`) with desktop
  approval UX later

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
* [`MODEL_PROVIDER_FRAMEWORK.md`](MODEL_PROVIDER_FRAMEWORK.md) — model abstractions
* [`CAPABILITY_FRAMEWORK.md`](CAPABILITY_FRAMEWORK.md) — future desktop capabilities
