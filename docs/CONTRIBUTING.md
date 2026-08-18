# Contributing to Memovi

Memovi is an open-source, self-hosted, desktop-first knowledge operating system.
Knowledge is the product; AI consumes that knowledge. You run the stack locally.
There is no hosted Memovi subscription in this repository.

Start with the root [`README.md`](../README.md) for product context, quick start,
providers, and testing. This guide is the contributor entry point, not a second
architecture document.

## Prerequisites and local setup

Requirements and the happy path (including **migrations**) are in the README
Quick start. In short:

```bash
task setup
task db:migrate
task backend     # terminal 1; starts Postgres + MinIO if needed; does not migrate
task desktop     # terminal 2
```

`task backend` does not apply Alembic migrations. Run `task db:migrate` before
using persisted API features.

More tooling detail: [`development/developer-tooling.md`](development/developer-tooling.md).  
Compose services: [`development/local-infrastructure.md`](development/local-infrastructure.md).  
Environment variables: [`architecture/CONFIGURATION.md`](architecture/CONFIGURATION.md).

## Tests

* Backend unit/integration: `task test` (or `task ci:backend`).
* Desktop unit + mock smoke: `task desktop:test`.
* Mock desktop smoke only: `task desktop:smoke` (in-memory API stub; no FastAPI).
* Live desktop/API smoke: `task desktop:smoke:live` — real FastAPI, Postgres, and
  MinIO; fake providers; jsdom. It does not launch a native Tauri window.
  Requires a migrated database and a running API (`task backend` in another
  terminal). See [`testing/DESKTOP_TESTING.md`](testing/DESKTOP_TESTING.md).
* Local CI parity: `task ci`. This does **not** run live smoke or Tauri packaging.

Run the checks that match what you changed. Do not skip tests that cover the
behavior you touched.

## Where code lives

| Area | Location |
| --- | --- |
| Platform API (composition root) | `apps/api` |
| Desktop client | `apps/desktop` |
| Optional web shell | `apps/web` |
| Domains | `packages/*` (auth, documents, memory, search, intelligence, automation, connectors, …) |
| Migrations | `database/` |
| Architecture | [`ARCHITECTURE.md`](ARCHITECTURE.md), [`architecture/`](architecture/) |
| Implementation status | [`STATUS.md`](STATUS.md) |
| Direction | [`ROADMAP.md`](ROADMAP.md), [`ROADMAP_V2.md`](ROADMAP_V2.md) |

Prefer extending an existing domain or client path over introducing a new
architecture, package, or parallel pipeline.

## Expectations

* Keep changes focused on the requested behavior.
* Do not add features, domains, or infrastructure “while you are here.”
* Meaningful behavior changes should include tests.
* Update documentation when setup, configuration, APIs, or contributor-facing
  behavior change. Do not treat stale docs as acceptable.
* Never commit secrets, `.env` files, API keys, or credentials. Use placeholders
  in examples. Provider keys belong in the API process environment, not the
  desktop client.
* Match existing style and the repository Task/CI commands rather than adding
  new toolchains.

## Pull requests

Describe why the change exists. Note how you verified it (`task ci`, a narrower
task, or live smoke). If something cannot be verified locally, say so.

There is no documented review SLA, chat community, or required approver list in
this repository. Follow the README and the architecture docs for technical
direction.
