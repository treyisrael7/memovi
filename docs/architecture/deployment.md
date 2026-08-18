# Deployment Architecture

# Purpose

This document defines Memovi's deployment posture and operational constraints.

# Scope

It covers self-hosting, runtime components, infrastructure isolation, repository areas related to deployment, storage dependencies, observability dependencies, and deployment evolution.

# Relationship to ARCHITECTURE.md

[`../ARCHITECTURE.md`](../ARCHITECTURE.md) establishes that Memovi is self-hostable by default and begins as a modular monolith. This document expands the deployment-related implications of those decisions.

# Self-Hostable by Default

Memovi is designed to be deployable on personal hardware, home servers, or cloud infrastructure.

No architectural decision should unnecessarily require proprietary cloud services.

Cloud-native technologies are encouraged. Cloud-required architecture is avoided whenever practical.

# Runtime Shape

**V1 local/self-hosted runtime:**

* Tauri desktop (primary) and optional web shell
* One FastAPI process (composition root): HTTP API, in-process event dispatcher,
  in-process `DocumentProcessingWorker`
* PostgreSQL with pgvector
* MinIO
* Structured logs, OpenTelemetry API spans, in-process metrics, `/health` `/ready`

Redis is **not used in V1**. Distributed queues, Redis Streams, Kubernetes, and
a Prometheus/Grafana/Loki stack are **future / V2** deployment options.

See [`../ARCHITECTURE.md`](../ARCHITECTURE.md).

# Infrastructure Layer

The Infrastructure Layer provides technical capabilities required by every other layer.

Examples include:

* PostgreSQL
* pgvector
* MinIO
* Object Storage
* Logging
* Metrics
* Tracing
* Docker
* Configuration

Infrastructure exists to support the platform. Business decisions should never originate from infrastructure components.

# Containerization

**V1:** local infrastructure is `compose.yml` at the repository root (PostgreSQL
and MinIO only). The API and desktop are not Compose services.

The `docker/` directory is reserved and empty. V1 does not ship production
Dockerfiles, Kubernetes manifests, or a packaged observability stack.

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

Redis is not used in V1 for temporary operational state. Distributed queues or
Redis Streams remain future architectural options.

Only authoritative data requires comprehensive backup.

See [`storage-architecture.md`](storage-architecture.md).

# Observability Dependencies

**V1:** structured logs, OpenTelemetry API spans (no required exporter),
in-process metrics, health and readiness endpoints.

Prometheus, Grafana, and Loki are **future / V2** options if operators want a
metrics/dashboard/log stack. They are not technologies Memovi currently deploys.

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
* V1 observability is logs, OTel API spans, in-process metrics, and health/ready — not a Prometheus/Grafana/Loki deployment.
* Additional operational infrastructure is introduced only when justified.

# Related Documents

* [`../ARCHITECTURE.md`](../ARCHITECTURE.md)
* [`repository-architecture.md`](repository-architecture.md)
* [`storage-architecture.md`](storage-architecture.md)
* [`observability.md`](observability.md)
* [`scaling.md`](scaling.md)
