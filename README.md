# Memovi

> Knowledge is the product. Memory is the architecture. AI is a consumer of
> knowledge — not its owner.

Memovi is an **open source**, **MIT licensed**, **self-hosted**, **desktop-first**
knowledge operating system. You run it on your machine. It is not a hosted AI
subscription, not an AI wrapper, and not merely “chat with PDFs.”

It turns documents, notes, conversations, code, and connected folders into
durable, organized, searchable knowledge that you control. The flagship client
is a Tauri desktop app. A FastAPI modular monolith is the platform boundary.
Clients do not own business logic. You bring your own model provider (or use
the built-in fake providers for local development).

This README is the developer entry point.

* License: [`LICENSE`](LICENSE) (MIT)
* Contributing: [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md)
* Product direction: [`docs/PRODUCT_VISION.md`](docs/PRODUCT_VISION.md)
* Documentation hub: [`docs/README.md`](docs/README.md)
* Architecture: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
* Configuration: [`docs/architecture/CONFIGURATION.md`](docs/architecture/CONFIGURATION.md)
* Desktop testing: [`docs/testing/DESKTOP_TESTING.md`](docs/testing/DESKTOP_TESTING.md)
* Roadmap / status: [`docs/ROADMAP.md`](docs/ROADMAP.md), [`docs/STATUS.md`](docs/STATUS.md)
* Later vision: [`docs/ROADMAP_V2.md`](docs/ROADMAP_V2.md)

## What exists today

The core V1 product path is implemented:

* Desktop client (`apps/desktop`) with first-run/home, documents, search, chat,
  collections, tags, connectors, workflows, settings, and diagnostics
* Local authentication and workspaces
* Document upload, processing, and durable knowledge
* Filesystem folder connector
* Keyword, semantic, and hybrid search (`GET /search?mode=keyword|semantic|hybrid`)
* RAG conversations with citations and navigation to the cited source
* Capability framework, planner, execution, and workflows (including approval/resume)
* PostgreSQL for durable application data; MinIO for persistent object storage
* Fake reasoning and fake embedding providers for local/dev; OpenAI for real chat
* Live desktop ↔ FastAPI smoke against real Postgres and MinIO

## Product journey

```text
Install
  → start local infrastructure
  → run migrations
  → start the API
  → launch desktop
  → configure an AI provider (optional; fake is the default)
  → connect or upload knowledge
  → wait for processing
  → search
  → ask questions
  → inspect cited knowledge
  → optionally run approved capabilities / workflows
```

## Prerequisites

- Python 3.14
- [`uv`](https://docs.astral.sh/uv/)
- Node.js 24 with Corepack
- pnpm 10.33.4 (pinned; `task setup` activates it via Corepack)
- [`Task`](https://taskfile.dev/)
- Docker Desktop or Docker Engine with Compose
- Git
- Rust toolchain (`rustup`) and host C++ / linker tools required by
  [Tauri](https://v2.tauri.app/start/prerequisites/) — needed to run the desktop
  client, not to run the API

GitHub CLI is optional (useful for some contributor workflows). It is not
required to install, run, or test Memovi.

VS Code users can use the Dev Container instead of installing most tools
directly. See [`docs/development/dev-container.md`](docs/development/dev-container.md).

## Quick start

Install Task, then from the repository root:

```bash
task setup
```

That installs Python dependencies, JavaScript workspace dependencies (including
the optional web client), the pinned pnpm version, and pre-commit hooks.

Copy `.env.example` to `.env` when you want local overrides (provider keys,
ports, credentials). Compose and the API also work from the documented local
defaults if you skip this at first.

Apply database migrations. `task db:migrate` starts PostgreSQL if needed, then
runs Alembic. **`task backend` does not run migrations.**

```bash
task db:migrate
```

Start the API in one terminal. This starts Docker Compose (PostgreSQL and MinIO)
if those containers are not already running, then serves the API on
`127.0.0.1:8000`. It does not apply migrations.

```bash
task backend
```

In a second terminal, start the desktop client:

```bash
task desktop
```

Then: register or sign in, upload or connect knowledge, wait until processing
is complete, search, and ask questions. Capabilities and workflows are available
when you want host actions with approval.

Health: `http://127.0.0.1:8000/health`.  
Auth: `http://127.0.0.1:8000/auth`.  
Search: `http://127.0.0.1:8000/search`.

Equivalent commands without Task are in
[`docs/development/developer-tooling.md`](docs/development/developer-tooling.md).

## Local storage

`compose.yml` provides:

- **PostgreSQL 18** with pgvector on `127.0.0.1:5432` — durable application data
  (users, sessions, documents metadata, knowledge, search indexes, jobs)
- **MinIO** on `127.0.0.1:9000` (console `127.0.0.1:9001`) — persistent object
  storage for uploaded files

The API defaults to MinIO (`MEMOVI_OBJECT_STORAGE=minio`). If MinIO is down,
startup fails. There is no silent fallback.

`MEMOVI_OBJECT_STORAGE=memory` is development/testing-only, ephemeral, and
allowed only when `MEMOVI_ENV` is a development value (`local`, `development`,
`dev`, or `test`). Do not use it as the normal path.

```bash
task docker-up      # start Postgres + MinIO without starting the API
task docker-down    # stop them (data volumes are kept)
```

Details: [`docs/development/local-infrastructure.md`](docs/development/local-infrastructure.md).

## Providers

Two settings are independent. Both default to **fake** for local development.

| Variable | What it controls | Default |
| --- | --- | --- |
| `INTELLIGENCE_PROVIDER` | Chat / reasoning (`fake` or `openai`) | `fake` |
| `SEARCH_EMBEDDING_PROVIDER` | Semantic search vectors (`fake`, `openai`, `ollama`, or `sentence_transformer`) | `fake` |

**Fake reasoning** (`INTELLIGENCE_PROVIDER=fake`) returns a deterministic answer
from retrieved knowledge. No network model call. Enough to exercise chat,
citations, and the desktop shell.

**Fake embeddings** (`SEARCH_EMBEDDING_PROVIDER=fake`) emit deterministic local
vectors. Keyword search still uses PostgreSQL full-text search. Semantic/hybrid
modes run, but they are not a production embedding model.

Fake providers are for development, tests, and offline demos. They are not
equivalent to a production AI provider.

### Real OpenAI reasoning

Do not enter API keys in the desktop client. Credentials stay in the API
process environment.

1. Copy `.env.example` to `.env` if you have not already.
2. Set:

   ```bash
   INTELLIGENCE_PROVIDER=openai
   OPENAI_API_KEY=<your key>
   ```

3. Restart the API (`task backend`).
4. In the desktop app, open **Settings → Diagnostics** and click **Recheck now**.

Optional: `OPENAI_MODEL` or `INTELLIGENCE_MODEL` (default `gpt-4o-mini` when
the provider is `openai`). Full variable list:
[`docs/architecture/CONFIGURATION.md`](docs/architecture/CONFIGURATION.md).

V1 reasoning adapters in this repository are **fake** and **openai**. Do not
assume other names in config enums are live adapters.

## Repository layout

```text
.
|-- apps/
|   |-- api/                  # FastAPI composition root (platform API)
|   |-- desktop/              # Flagship Tauri desktop client
|   `-- web/                  # Optional web client workspace (shell)
|-- packages/                 # Domain packages (auth, documents, memory, …)
|-- database/                 # Alembic migrations
|-- docs/
|-- compose.yml               # Local PostgreSQL and MinIO
|-- pyproject.toml
|-- pnpm-workspace.yaml
`-- Taskfile.yml
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and
[`docs/architecture/DESKTOP_CLIENT.md`](docs/architecture/DESKTOP_CLIENT.md).

## Testing

| Check | Command | What it proves |
| --- | --- | --- |
| Backend unit/integration | `task test` | Pytest (fails if no tests are collected; needs Postgres for suites that use it) |
| Backend CI parity | `task ci:backend` | Ruff, Black, MyPy, pytest, and the 80% coverage floor |
| Desktop unit + mock smoke | `task desktop:test` | Desktop unit tests and mock-backend critical path |
| Mock desktop smoke only | `task desktop:smoke` | Critical UI path against an in-memory API stub |
| Live desktop/API smoke | `task desktop:smoke:live` | Same React shell against real FastAPI + Postgres + MinIO |
| Native packaged auth smoke | `task desktop:smoke:native` | Real WebView cookie jar (local packaged binary; not CI) |
| Local CI parity | `task ci` | Backend lint/types/tests/coverage + desktop typecheck/unit/mock smoke/Vite build + optional web lint/types/build |

`task ci` does **not** run live smoke, does **not** launch a native Tauri
window, and does **not** run Tauri packaging. Linux, unsigned Windows, and
unsigned macOS Tauri packaging run in GitHub Actions
(`.github/workflows/desktop.yml`). Packaging is not native launch or auth
testing; macOS WKWebView auth remains unverified. Signing, notarization, and
GitHub Releases are future work. Packaged WebView session cookies are a local
check (`task desktop:smoke:native`); see
[`docs/testing/NATIVE_DESKTOP_SMOKE.md`](docs/testing/NATIVE_DESKTOP_SMOKE.md).

Live smoke (`task desktop:smoke:live`) requires Postgres, MinIO, migrated
schema, and a running API. It sets `MEMOVI_LIVE_API=1`. It uses **fake**
reasoning and embedding providers for determinism. It runs in jsdom (Vitest);
it is not native window automation.

Typical live-smoke sequence:

```bash
task db:migrate
task backend              # terminal 1
task desktop:smoke:live   # terminal 2
```

Narrower local checks:

```bash
task backend:check
task desktop:check
task lint
task format
task typecheck
```

Desktop testing details: [`docs/testing/DESKTOP_TESTING.md`](docs/testing/DESKTOP_TESTING.md).

## Task commands

- `task setup` — install dependencies and Git hooks
- `task backend` — start Docker infrastructure and the API (does **not** migrate)
- `task db:migrate` — start PostgreSQL if needed and apply Alembic migrations
- `task desktop` — start the Tauri desktop client
- `task docker-up` / `task docker-down` — start/stop Postgres and MinIO
- `task test` — backend pytest (no coverage floor; fails if no tests are collected)
- `task desktop:test` / `task desktop:smoke` / `task desktop:smoke:live` / `task desktop:smoke:native`
- `task desktop:check` — desktop typecheck, tests (unit + mock smoke), Vite build
- `task ci` / `task ci:backend` / `task ci:desktop` / `task ci:frontend`
- `task dev` — Docker infrastructure and the optional web-workspace dev server

Run `task --list` for the full list.

## Status

Memovi is **0.1.0** in a **pre-alpha / public-development** stage. The core V1
product path above is implemented. Current work is release polish, contributor
readiness, packaging, and operational hardening — not building the first
desktop pages, chat, documents, or capabilities from scratch.

This is not a finished stable 1.0 release. Metadata in `pyproject.toml` still
uses Development Status :: 2 - Pre-Alpha.

## License

Memovi is licensed under the [MIT License](LICENSE).
