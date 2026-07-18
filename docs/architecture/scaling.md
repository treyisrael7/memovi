# Scaling Architecture

# Purpose

This document defines how Memovi is expected to evolve as operational requirements grow.

# Scope

It covers modular monolith evolution, worker scaling, storage evolution, repository evolution, connector and pipeline extensibility, and future service extraction.

# Relationship to ARCHITECTURE.md

[`../ARCHITECTURE.md`](../ARCHITECTURE.md) states that Memovi favors operational simplicity and future evolution. This document expands the existing scaling and evolution strategy without introducing new architectural decisions.

# Scaling Philosophy

Operational complexity is introduced only when it provides measurable value.

The architecture should always remain simpler than the problems it is solving.

Memovi begins as a modular monolith because it minimizes deployment complexity while preserving architectural boundaries.

# Modular Evolution

Strong boundaries today enable future service extraction if operational requirements justify it.

Modules may become independent services later when there is a demonstrated need for:

* Independent deployment
* Independent scaling
* Failure isolation
* Team ownership
* Operational separation

Future service extraction should follow domain boundaries rather than technical layers.

See [`module-architecture.md`](module-architecture.md).

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
desktop/   # flagship client
mobile/
cli/

↓

Phase 4
independently deployable services (if justified)
```

The repository should grow through extension rather than reorganization.

Existing structure should remain stable whenever practical.

See [`repository-architecture.md`](repository-architecture.md).

# Worker Scaling

Workers subscribe to events and perform focused background work.

Examples include:

* OCR Worker
* Chunk Worker
* Embedding Worker
* Summary Worker
* Entity Extraction Worker
* Search Index Worker

Workers should remain stateless, independent, and focused on one responsibility.

Large workers should be decomposed rather than expanded.

Worker failures should remain isolated so a failed OCR operation does not terminate unrelated processing.

See [`event-architecture.md`](event-architecture.md).

# Pipeline Evolution

The knowledge pipeline is intentionally extensible.

New capabilities should integrate by extending existing stages rather than introducing parallel workflows.

Examples include:

* Future OCR improvements
* Additional embedding providers
* Knowledge graph construction
* Topic clustering
* Automatic classification
* Relationship inference
* Cross-document linking

Every enhancement should strengthen the existing pipeline rather than replacing it.

See [`knowledge-processing-pipeline.md`](knowledge-processing-pipeline.md).

# Storage Evolution

Future operational requirements may introduce:

* Read replicas
* Distributed object storage
* Dedicated vector databases
* Cold storage
* Archival systems

These changes should remain implementation concerns.

Business domains should remain unaffected because storage technologies are isolated behind stable abstractions.

See [`storage-architecture.md`](storage-architecture.md).

# Event Platform Evolution

The architecture intentionally does not prescribe a specific messaging technology.

Current implementations may use Redis Streams, PostgreSQL-backed queues, RabbitMQ, Kafka, or future messaging systems.

Messaging infrastructure is replaceable. The architectural model remains constant.

# Connector Growth

New connectors should extend the connector framework.

They should authenticate with their external system, discover available content, retrieve raw data, and normalize it into the common document representation.

Future connectors should not introduce provider-specific downstream workflows.

See [`connector-framework.md`](connector-framework.md).

# Scaling Constraints

Scaling should not violate these constraints:

* Knowledge remains the product.
* Domains retain clear ownership.
* The Knowledge Platform remains independent from Intelligence.
* Storage responsibilities remain exclusive.
* Indexes and caches remain derived.
* Messaging technology remains replaceable.
* Future services follow domain boundaries.

# Key Decisions

* Operational simplicity is preferred over premature distribution.
* Memovi scales first through modular boundaries, workers, and storage abstractions.
* Microservices are introduced only when operational requirements justify them.
* Repository growth occurs through extension rather than restructuring.
* Pipeline capabilities extend existing stages rather than bypassing them.
* Storage technologies may evolve without changing business domains.
* Messaging infrastructure is replaceable.

# Related Documents

* [`../ARCHITECTURE.md`](../ARCHITECTURE.md)
* [`module-architecture.md`](module-architecture.md)
* [`repository-architecture.md`](repository-architecture.md)
* [`event-architecture.md`](event-architecture.md)
* [`knowledge-processing-pipeline.md`](knowledge-processing-pipeline.md)
* [`storage-architecture.md`](storage-architecture.md)
* [`connector-framework.md`](connector-framework.md)
* [`deployment.md`](deployment.md)
