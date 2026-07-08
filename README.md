# Memovi

> Your knowledge, organized. AI that remembers what matters.

Memovi is a self-hosted knowledge platform for turning fragmented documents,
notes, conversations, code, and external services into durable, searchable
memory.

This README is the developer entry point. For system design, see
[`ARCHITECTURE.md`](ARCHITECTURE.md) and [`docs/architecture/`](docs/architecture/).

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

This installs Python dependencies, installs frontend dependencies, enables the
pinned pnpm version, and installs pre-commit hooks.

If you are not using Task, the equivalent commands are documented in
[`docs/development/developer-tooling.md`](docs/development/developer-tooling.md).

## Repository Layout

```text
.
|-- apps/
|   |-- api/                  # FastAPI composition root
|   `-- web/                  # Next.js frontend workspace
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
|-- docs/
|   |-- adr/
|   |-- architecture/         # Architecture reference docs
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

The API app currently contains the backend composition root, health endpoint,
and local authentication endpoints. Auth owns its domain model, use cases,
SQLAlchemy repositories, Alembic migration, and tests inside `packages/auth`.

## Development Workflow

Start from a clean setup:

```bash
task setup
```

Start local infrastructure and the frontend development server:

```bash
task dev
```

Start local infrastructure and the backend API development server:

```bash
task backend
```

The API health endpoint is available at `http://localhost:8000/health`.
Local authentication endpoints are available under `http://localhost:8000/auth`.

Run validation before opening a pull request:

```bash
task backend:check
task lint
task format
task typecheck
task test
```

Pre-commit runs formatting, linting, type checks, and file hygiene checks before
commits. CI runs backend and frontend validation through GitHub Actions.

## Task Commands

- `task setup` installs dependencies and Git hooks.
- `task backend` starts Docker infrastructure and the backend API dev server.
- `task backend:check` runs backend lint, format check, typecheck, and tests.
- `task backend:dev` is an alias for `task backend`.
- `task frontend` runs frontend lint, format check, typecheck, and build.
- `task docker-up` starts local infrastructure.
- `task docker-down` stops local infrastructure.
- `task db:migrate` starts PostgreSQL and applies Alembic migrations.
- `task backend:process -- <processing_job_id>` runs document processing locally.
- `task lint` runs backend and frontend linters.
- `task format` formats backend and frontend files.
- `task typecheck` runs backend and frontend type checks.
- `task test` runs tests.
- `task dev` starts Docker infrastructure and the frontend dev server.

Run `task --list` for the full command list, including scoped backend and
frontend subtasks.

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

Memovi is in early development. The repository currently provides the Python
workspace, frontend workspace, local infrastructure, developer tooling, CI, Dev
Container foundation, and local session-based authentication foundation.
