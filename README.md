# Memovi

> Your knowledge, organized. AI that remembers what matters.

Memovi is a desktop-first, AI-native knowledge operating system.

It is built around a reusable backend platform that turns fragmented documents,
notes, conversations, code, and external services into durable, searchable
memory. The flagship product experience is a desktop application. The same API
powers an optional web client and can support future mobile or CLI clients
without changing backend domain architecture.

Knowledge is the product. AI is a consumer of that knowledge. Clients are
replaceable; the FastAPI platform boundary stays stable.

This README is the developer entry point.

* Product direction: [`docs/PRODUCT_VISION.md`](docs/PRODUCT_VISION.md)
* Documentation hub: [`docs/README.md`](docs/README.md)
* Architecture: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
* Roadmap / status: [`docs/ROADMAP.md`](docs/ROADMAP.md), [`docs/STATUS.md`](docs/STATUS.md)

## Prerequisites

- Python 3.14
- [`uv`](https://docs.astral.sh/uv/)
- Node.js 24 with Corepack
- pnpm 10.33.4
- [`Task`](https://taskfile.dev/)
- Docker Desktop or Docker Engine with Compose
- Git
- GitHub CLI

VS Code users can use the Dev Container instead of installing most tools
directly. See [`docs/development/dev-container.md`](docs/development/dev-container.md).

## Installation

Install Task, then set up the repository:

```bash
task setup
```

This installs Python dependencies, installs optional web-workspace dependencies,
enables the pinned pnpm version, and installs pre-commit hooks.

If you are not using Task, the equivalent commands are documented in
[`docs/development/developer-tooling.md`](docs/development/developer-tooling.md).

## Repository Layout

```text
.
|-- apps/
|   |-- api/                  # FastAPI composition root (platform API)
|   `-- web/                  # Optional web client workspace (shell)
|-- packages/
|   |-- auth/
|   |-- connectors/
|   |-- config/
|   |-- contracts/
|   |-- documents/
|   |-- intelligence/
|   |-- memory/
|   |-- observability/
|   |-- search/
|   `-- shared/
|-- database/
|-- docker/
|-- docs/                     # Product, planning, architecture, development docs
|   |-- README.md             # Documentation hub
|   |-- PRODUCT_VISION.md
|   |-- ARCHITECTURE.md
|   |-- ROADMAP.md
|   |-- STATUS.md
|   |-- adr/
|   |-- architecture/         # Architecture deep-dives
|   `-- development/          # Local development docs
|-- scripts/
|-- tests/
|   |-- architecture/
|   |-- integration/
|   `-- fixtures/
|-- .devcontainer/            # VS Code Dev Container definition
|-- .github/workflows/        # Repository validation workflows
|-- compose.yml               # Local PostgreSQL, Redis, and MinIO
|-- pyproject.toml            # Python workspace and tooling config
|-- pnpm-workspace.yaml       # pnpm workspace config
`-- Taskfile.yml              # Repository task runner
```

The API app is the composition root for the reusable backend platform: health,
local authentication, documents, search, and conversation reasoning. Auth owns
its domain model, use cases, SQLAlchemy repositories, Alembic migration, and
tests inside `packages/auth`. Search owns ranked full-text, semantic, and hybrid
retrieval and exposes `GET /search` with `mode=keyword|semantic|hybrid` (hybrid
default). Desktop and other clients consume these APIs; they do not own business
logic.

A future desktop app workspace will live under `apps/` alongside `api`. The
existing `apps/web` workspace is an optional client shell, not the primary
product surface.

## Development Workflow

Start from a clean setup:

```bash
task setup
```

Start local infrastructure and the optional web development server:

```bash
task dev
```

Start local infrastructure and the backend API development server:

```bash
task backend
```

The API health endpoint is available at `http://localhost:8000/health`.
Local authentication endpoints are available under `http://localhost:8000/auth`.
Full-text, semantic, and hybrid search are available at `http://localhost:8000/search`.

Run validation before opening a pull request:

```bash
task backend:check
task lint
task format
task typecheck
task test
```

Pre-commit runs formatting, linting, type checks, and file hygiene checks before
commits. CI validates the backend and optional web workspace through GitHub Actions.

## Task Commands

- `task setup` installs dependencies and Git hooks.
- `task backend` starts Docker infrastructure and the backend API dev server.
- `task backend:check` runs backend lint, format check, typecheck, and tests.
- `task backend:dev` is an alias for `task backend`.
- `task frontend` runs optional web-workspace lint, format check, typecheck, and build.
- `task docker-up` starts local infrastructure.
- `task docker-down` stops local infrastructure.
- `task db:migrate` starts PostgreSQL and applies Alembic migrations.
- `task backend:process -- <processing_job_id>` runs document processing locally.
- `task lint` runs backend and web-workspace linters.
- `task format` formats backend and web-workspace files.
- `task typecheck` runs backend and web-workspace type checks.
- `task test` runs tests.
- `task dev` starts Docker infrastructure and the optional web-workspace dev server.

Run `task --list` for the full command list, including scoped backend and
web-workspace subtasks.

## Docker Services

Local infrastructure is defined in `compose.yml`:

- PostgreSQL 18 with pgvector on `127.0.0.1:5432`
- Redis 8 on `127.0.0.1:6379`
- MinIO API on `127.0.0.1:9000`
- MinIO console on `127.0.0.1:9001`

Start services:

```bash
task docker-up
```

Stop services:

```bash
task docker-down
```

Service credentials, health checks, volumes, and configuration are documented in
[`docs/development/local-infrastructure.md`](docs/development/local-infrastructure.md). Copy
`.env.example` to `.env` when you need local overrides.

Run database migrations before using persisted API features. PostgreSQL must be running:

```bash
task db:migrate
```

Or start infrastructure first, then migrate manually:

```bash
task docker-up
uv run alembic upgrade head
```

## Status

Memovi is in early development. The repository currently provides the reusable
backend platform (Python workspace, FastAPI composition root, local
infrastructure, developer tooling, CI, Dev Container foundation, and local
session-based authentication), with an optional web client shell. The flagship
desktop client is the next product surface on top of the stable API.
