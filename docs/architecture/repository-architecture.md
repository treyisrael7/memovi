# Repository Architecture

# Purpose

This document defines how the Memovi repository is organized and how top-level areas should evolve.

# Scope

It covers the monorepo structure, top-level directories, package responsibilities, repository ownership, and repository evolution.

# Relationship to ARCHITECTURE.md

[`../../ARCHITECTURE.md`](../../ARCHITECTURE.md) provides the repository overview. This document is the focused reference for repository organization.

# Repository Model

The repository is organized as a production-oriented monorepo.

A monorepo provides:

* A single source of truth
* Shared tooling
* Consistent dependency management
* Atomic changes across frontend and backend
* Simplified local development
* Easier refactoring across domains

As Memovi evolves, the repository structure should prioritize clarity over cleverness.

Every top-level directory has a single purpose.

# Repository Overview

```text
memovi/

├── apps/
├── packages/
├── docs/
├── docker/
├── scripts/
├── .github/
├── .cursor/

├── README.md
├── PHILOSOPHY.md
├── ARCHITECTURE.md
├── ROADMAP.md
├── CONTRIBUTING.md
├── LICENSE
└── .env.example
```

This structure separates application code, reusable platform libraries, infrastructure, automation, AI guidance, and documentation into clearly defined areas.

# Top-Level Directories

## apps/

The `apps` directory contains deployable applications.

Applications expose functionality. They do not define shared platform behavior.

Current applications include:

```text
apps/
    web/
    api/
```

Future applications may include:

```text
desktop/
mobile/
cli/
worker/
```

Every application consumes the same platform capabilities. Business logic should remain inside the platform rather than inside individual applications.

## packages/

The `packages` directory contains reusable platform libraries.

Packages exist to reduce duplication, not to centralize business logic. Business domains should never migrate into packages simply because multiple applications use them.

Examples include:

```text
packages/
    config/
    logging/
    events/
    database/
    observability/
    shared/
```

A package should answer one question:

> Could this library reasonably be published independently?

If the answer is no, it probably belongs inside a business domain instead.

## docs/

The `docs` directory contains engineering documentation.

Documentation evolves alongside the platform and should describe architecture, deployment, design decisions, diagrams, and implementation notes.

Suggested organization:

```text
docs/
    architecture/
    adr/
    deployment/
    diagrams/
    api/
```

Architecture documentation should be treated as part of the codebase rather than an afterthought.

## docker/

The `docker` directory contains containerization assets.

Examples include Dockerfiles, Docker Compose, development environments, and production images.

Infrastructure configuration should remain isolated from application logic.

## scripts/

The `scripts` directory contains automation.

Examples include local setup, database initialization, migrations, seeding, development utilities, and release automation.

Scripts should automate repetitive engineering tasks. Manual processes should gradually become scripted.

## .github/

The `.github` directory contains repository automation.

Examples include GitHub Actions, issue templates, pull request templates, CODEOWNERS, and Dependabot configuration.

Repository automation should improve consistency without increasing maintenance burden.

## .cursor/

The `.cursor` directory contains AI development guidance.

Cursor rules represent architectural constraints and engineering expectations. These rules ensure AI-generated code remains consistent with Memovi's architecture and philosophy.

AI assistants should learn the project rather than redefine it.

# Monorepo Principles

## Applications Consume the Platform

Applications should remain lightweight.

They render interfaces, accept user interaction, and call platform capabilities. Business logic belongs elsewhere.

If multiple applications require the same behavior, that behavior belongs inside the platform rather than being duplicated.

## Packages Support the Platform

Packages provide reusable technical capabilities such as logging, configuration, event infrastructure, observability, and shared utilities.

Packages should remain infrastructure-oriented. Business concepts remain inside domains.

## Documentation Is Part of the Product

Architecture documentation is treated with the same importance as source code.

Significant architectural changes should update `ARCHITECTURE.md`, relevant documentation, ADRs, and Cursor rules when applicable.

## Infrastructure Remains Isolated

Deployment concerns should remain separate from application concerns.

Docker, CI/CD, infrastructure automation, and operational tooling should never become mixed with business logic.

# Repository Evolution

The repository is expected to evolve gradually.

```text
Phase 1
apps/
packages/

↓

Phase 2
workers/

↓

Phase 3
desktop/
mobile/
cli/

↓

Phase 4
independently deployable services (if justified)
```

The repository should grow through extension rather than reorganization.

Existing structure should remain stable whenever practical.

# Repository Ownership

Every file within the repository should have a clear owner.

| Area | Primary Responsibility |
| --- | --- |
| `apps/web` | User interface |
| `apps/api` | Platform API |
| `packages` | Shared platform libraries |
| `docs` | Engineering documentation |
| `docker` | Infrastructure |
| `scripts` | Automation |
| `.cursor` | AI development guidance |

Clear ownership reduces ambiguity and improves maintainability.

# Organizational Rules

The repository follows these structural rules:

* Business logic belongs inside business domains.
* Shared libraries remain infrastructure-focused.
* Applications consume platform capabilities rather than implementing them.
* Documentation evolves with implementation.
* Infrastructure remains isolated.
* Repository structure should remain stable over time.
* New top-level directories require architectural justification.

A developer unfamiliar with Memovi should be able to understand the purpose of every top-level directory within minutes.

# Key Decisions

* Memovi is organized as a production-oriented monorepo.
* Applications expose capabilities but do not own business logic.
* Packages contain reusable platform libraries rather than business domains.
* Documentation is treated as a first-class engineering artifact.
* Infrastructure remains isolated from application code.
* AI guidance lives alongside the repository rather than inside prompts.
* Repository growth should occur through extension instead of restructuring.
* Every top-level directory has exactly one responsibility.

# Related Documents

* [`../../ARCHITECTURE.md`](../../ARCHITECTURE.md)
* [`module-architecture.md`](module-architecture.md)
* [`deployment.md`](deployment.md)
* [`observability.md`](observability.md)
* [`scaling.md`](scaling.md)
