# Event Architecture

# Purpose

This document defines how events coordinate asynchronous behavior in Memovi.

# Scope

It covers event philosophy, event platform expectations, event principles, lifecycle, ownership, categories, worker model, chaining, failure strategy, versioning, observability, contracts, and boundaries.

# Relationship to ARCHITECTURE.md

[`../ARCHITECTURE.md`](../ARCHITECTURE.md) summarizes event-driven processing. This document is the focused reference for event architecture.

# Event Philosophy

Events coordinate asynchronous behavior.

Rather than tightly coupling long-running workflows together, domains publish business events describing meaningful state changes. Other components may subscribe to those events and perform additional work independently.

Events communicate what happened. They do not instruct other components what to do.

# Why Events?

Without events, complex workflows quickly become tightly coupled.

```text
Upload Document
↓
OCR
↓
Chunk
↓
Embeddings
↓
Summaries
↓
Index
↓
Update Memory
```

Every component depends directly on the next. Changing one step often requires modifying several others.

Instead, Memovi publishes business events.

```text
Document Uploaded
↓
OCR Completed
↓
Document Chunked
↓
Embeddings Generated
↓
Knowledge Indexed
```

Each worker reacts independently. No component needs to understand the entire workflow.

# Event Platform

The Event Platform provides asynchronous communication between domains.

The architecture intentionally does not prescribe a specific messaging technology.

Current implementations may use:

* Redis Streams
* PostgreSQL-backed queues
* RabbitMQ
* Kafka
* Future messaging systems

Messaging infrastructure is replaceable. The architectural model remains constant.

# Event Principles

## Events Describe Facts

Events describe something that has already happened.

Examples include:

* `DocumentUploaded`
* `ConnectorSynchronized`
* `EmbeddingsGenerated`
* `KnowledgeIndexed`

Events should never represent commands. Past-tense naming reflects completed business actions.

## Events Represent Business Meaning

Events communicate changes in the business domain. They should avoid implementation details.

Good events describe meaningful platform behavior:

* `DocumentUploaded`
* `SearchIndexed`
* `MemoryUpdated`

Poor events expose technical implementation:

* `SQLInsertCompleted`
* `PgVectorStored`

Consumers should understand the event without knowing how it was implemented.

## Events Are Immutable

Once published, events never change.

Corrections are represented by publishing new events rather than modifying previous ones.

Immutability simplifies debugging, replay, auditing, and future event sourcing if desired.

## Events Are Idempotent

Workers should safely process the same event multiple times.

Duplicate delivery should never produce inconsistent platform state.

Idempotency simplifies retries and improves resilience.

# Event Lifecycle

Every event follows the same lifecycle.

```text
Business Action
        │
        ▼
Domain Event
        │
        ▼
Event Platform
        │
        ▼
Worker
        │
        ▼
Business Result
        │
        ▼
New Event
```

Large workflows become chains of independent business events rather than deeply nested orchestration.

# Event Ownership

Every event has exactly one publisher.

Multiple consumers may subscribe.

| Event | Publisher | Consumers |
| --- | --- | --- |
| `DocumentUploaded` | Documents | Processing |
| `OCRCompleted` | Processing | Processing |
| `EmbeddingsGenerated` | Processing | Search, Memory |
| `MemoryUpdated` | Memory | Intelligence |
| `ConnectorSynchronized` | Connectors | Documents |

Clear ownership prevents conflicting event definitions.

# Event Categories

## Domain Events

Represent meaningful business state changes.

Examples:

* `DocumentUploaded`
* `MemoryCreated`
* `CollectionUpdated`

## Processing Events

Represent asynchronous pipeline progress.

Examples:

* `OCRCompleted`
* `DocumentChunked`
* `EmbeddingsGenerated`
* `SummaryCreated`

## Integration Events

Represent communication with external systems.

Examples:

* `ConnectorAuthorized`
* `ConnectorSynchronized`
* `ImportCompleted`

## System Events

Represent operational behavior.

Examples:

* `WorkerStarted`
* `WorkerCompleted`
* `RetryScheduled`

System events primarily support observability rather than business behavior.

# Worker Model

Workers subscribe to events.

Workers should remain:

* Stateless
* Independent
* Focused on one responsibility

Examples include:

```text
OCR Worker
Chunk Worker
Embedding Worker
Summary Worker
Entity Extraction Worker
Search Index Worker
```

Workers should perform one task well. Large workers should be decomposed rather than expanded.

# Event Chaining

Long-running workflows naturally become pipelines.

```text
DocumentUploaded
        │
        ▼
OCR Worker
        │
        ▼
OCRCompleted
        │
        ▼
Chunk Worker
        │
        ▼
DocumentChunked
        │
        ▼
Embedding Worker
        │
        ▼
EmbeddingsGenerated
        │
        ▼
Index Worker
        │
        ▼
KnowledgeIndexed
```

Each worker understands only its own responsibility. No worker orchestrates the entire pipeline.

# Failure Strategy

Worker failures should remain isolated.

A failed OCR operation should not terminate unrelated processing.

Preferred strategy:

1. Retry transient failures.
2. Record permanent failures.
3. Publish failure events when appropriate.
4. Continue processing unrelated work.

Future implementations may introduce dead-letter queues and replay tooling. These mechanisms are implementation concerns rather than architectural requirements.

# Event Versioning

Events represent contracts between producers and consumers.

Breaking changes should be avoided.

When evolution becomes necessary, new event versions should coexist with previous versions during migration. Consumers should migrate intentionally rather than relying on immediate replacement.

# Event Observability

Every published event should produce telemetry.

Examples include:

* Publication time
* Processing latency
* Consumer duration
* Retry count
* Failure rate
* Queue depth
* Throughput

Operational visibility is considered part of the architecture rather than an optional enhancement.

See [`observability.md`](observability.md).

# Event Contracts

Events should remain intentionally small.

A typical event contains:

* Event identifier
* Event type
* Aggregate identifier
* Timestamp
* Version
* Minimal business payload

Large business objects should not be transmitted directly through events.

Consumers retrieve additional information when necessary. This keeps events lightweight and stable.

# Architectural Boundaries

Events coordinate communication.

They do not replace APIs. They do not replace business domains. They do not become distributed remote procedure calls.

Whenever synchronous communication remains simpler, synchronous communication is preferred.

Events exist to reduce coupling, not to increase architectural complexity.

# Key Decisions

* Events describe completed business actions.
* Messaging technology is replaceable.
* Every event has one publisher and many potential consumers.
* Workers remain stateless and narrowly focused.
* Events are immutable and idempotent.
* Large workflows emerge through event chains rather than centralized orchestration.
* Event contracts evolve carefully through versioning.
* Observability is considered part of the event system itself.
* Events coordinate domains without increasing coupling.

# Related Documents

* [`../ARCHITECTURE.md`](../ARCHITECTURE.md)
* [`domains.md`](domains.md)
* [`request-lifecycle.md`](request-lifecycle.md)
* [`knowledge-processing-pipeline.md`](knowledge-processing-pipeline.md)
* [`observability.md`](observability.md)
* [`scaling.md`](scaling.md)
