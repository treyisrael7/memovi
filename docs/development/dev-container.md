# Dev Container

Memovi includes a VS Code Dev Container for a consistent local development environment.

## Included Tools

- Python 3.14
- Node.js 24
- pnpm 10.33.4 through Corepack
- uv
- Docker CLI through the host Docker engine
- Git
- GitHub CLI

## Recommended Extensions

The Dev Container automatically installs the workspace extensions declared in `.devcontainer/devcontainer.json`:

- Python, Pylance, Ruff, Black, and MyPy
- ESLint and Prettier
- Docker
- GitHub Actions and GitHub Pull Requests
- YAML support

## Usage

Open the repository in VS Code and run:

```text
Dev Containers: Reopen in Container
```

On first creation, the container runs:

```bash
corepack enable
corepack prepare pnpm@10.33.4 --activate
uv sync --all-groups
pnpm install --frozen-lockfile
uv run pre-commit install
```

The Dev Container uses Docker outside of Docker, so Docker commands run inside the container target the host Docker engine. This allows the local Compose infrastructure to be managed from the container:

```bash
docker compose up -d
```

Forwarded ports are configured for the web app and local infrastructure:

- `3000` for Next.js
- `5432` for PostgreSQL
- `6379` for Redis
- `9000` for the MinIO API
- `9001` for the MinIO console

## Notes

The container does not run backend or frontend application services automatically. It only prepares the development environment and installs dependencies.

If dependencies change, rebuild the container or rerun:

```bash
uv sync --all-groups
pnpm install --frozen-lockfile
```
