# Deployment Architecture

# Purpose

This document defines Memovi's deployment posture and operational constraints.

# Scope

It covers self-hosting, runtime components, infrastructure isolation, repository areas related to deployment, storage dependencies, observability dependencies, and deployment evolution.

# Relationship to ARCHITECTURE.md

[`../../ARCHITECTURE.md`](../../ARCHITECTURE.md) establishes that Memovi is self-hostable by default and begins as a modular monolith. This document expands the deployment-related implications of those decisions.

# Self-Hostable by Default

Memovi is designed to be deployable on personal hardware, home servers, or cloud infrastructure.

No architectural decision should unnecessarily require proprietary cloud services.

Cloud-native technologies are encouraged. Cloud-required architecture is avoided whenever practical.

# Runtime Shape

The high-level runtime model includes:

* Presentation clients
* FastAPI application
* Business domains
* Domain events
* Workers
* PostgreSQL with pgvector
* Redis
* MinIO
* Observability tooling

The top-level blueprint represents these responsibilities in the canonical system diagram.

See [`../../ARCHITECTURE.md`](../../ARCHITECTURE.md).

# Infrastructure Layer

The Infrastructure Layer provides technical capabilities required by every other layer.

Examples include:

* PostgreSQL
* pgvector
* Redis
* MinIO
* Object Storage
* Logging
* Metrics
* Tracing
* Docker
* Configuration

Infrastructure exists to support the platform. Business decisions should never originate from infrastructure components.

# Containerization

The `docker` directory contains containerization assets.

Examples include:

* Dockerfiles
* Docker Compose
* Development environments
* Production images

Infrastructure configuration should remain isolated from application logic.

See [`repository-architecture.md`](repository-architecture.md).

# Deployment Isolation

Deployment concerns should remain separate from application concerns.

Docker, CI/CD, infrastructure automation, and operational tooling should never become mixed with business logic.

This separation improves maintainability and simplifies onboarding.

# Storage Dependencies

Deployment must account for the platform's storage responsibilities:

* PostgreSQL as the authoritative source of truth
* pgvector for derived semantic representations
* MinIO for immutable source artifacts
* Redis for temporary operational state

Only authoritative data requires comprehensive backup.

See [`storage-architecture.md`](storage-architecture.md).

# Observability Dependencies

Deployment should support the observability technologies identified by the project:

* OpenTelemetry
* Prometheus
* Grafana
* Loki

Operational visibility is part of the architecture and should be considered when deploying requests, workers, events, search, connectors, and AI workflows.

See [`observability.md`](observability.md).

# Operational Simplicity

Operational complexity is introduced only when it provides measurable value.

Memovi begins as a modular monolith because it minimizes deployment complexity while preserving architectural boundaries.

Additional infrastructure, including distributed services, dedicated message brokers, or orchestration platforms, should only be introduced after operational requirements demonstrate a clear need.

# Key Decisions

* Memovi is self-hostable by default.
* Proprietary cloud requirements are avoided whenever practical.
* The platform begins as a modular monolith to minimize deployment complexity.
* Infrastructure configuration remains isolated from application logic.
* PostgreSQL and object storage require comprehensive backup.
* Derived data may be regenerated.
* Observability tooling is part of the deployed platform posture.
* Additional operational infrastructure is introduced only when justified.

# Related Documents

* [`../../ARCHITECTURE.md`](../../ARCHITECTURE.md)
* [`repository-architecture.md`](repository-architecture.md)
* [`storage-architecture.md`](storage-architecture.md)
* [`observability.md`](observability.md)
* [`scaling.md`](scaling.md)
