# Developer Tooling

Memovi uses Task as the repository task runner and pre-commit for commit-time checks.

## Task Runner

Install Task from the official documentation at [`taskfile.dev`](https://taskfile.dev/installation/).

List available tasks:

```bash
task --list
```

Set up the repository:

```bash
task setup
```

Common development commands:

```bash
task lint
task format
task typecheck
task test
task dev
```

The top-level tasks compose smaller backend and frontend tasks instead of duplicating command logic. For example, `task lint` runs `task backend:lint` and `task frontend:lint`.

## Installation Details

`task setup` installs Python dependencies, frontend dependencies, and Git hooks.
It wraps these lower-level commands:

```bash
corepack enable
corepack prepare pnpm@10.33.4 --activate
uv sync --all-groups
pnpm install --frozen-lockfile
uv run pre-commit install
```

Run all hooks manually:

```bash
uv run pre-commit run --all-files
```

## Hooks

Python hooks use the tool configuration in `pyproject.toml`:

- Ruff runs lint and import checks with automatic safe fixes.
- Black formats Python files.
- MyPy performs strict type checking.

JavaScript hooks use the `apps/web` package scripts:

- ESLint runs `corepack pnpm --filter @memovi/web lint`.
- Prettier runs `corepack pnpm --filter @memovi/web format`.

General hooks use `pre-commit-hooks`:

- trailing whitespace fixer
- end-of-file fixer
- YAML validation
- JSON validation
- large file detection

The hooks assume `uv`, Node.js Corepack, and Docker-independent local tooling are available on the developer machine.

For a preconfigured VS Code environment with these tools installed, use the Dev Container documented in [`dev-container.md`](dev-container.md).
