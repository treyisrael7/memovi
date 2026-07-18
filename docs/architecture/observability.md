# Observability

# Purpose

This document defines the architectural expectations for operational visibility in Memovi.

# Scope

It covers observability concerns for requests, background jobs, events, AI inference, connector synchronization, search operations, errors, performance, and storage-related operations.

# Relationship to ARCHITECTURE.md

[`../ARCHITECTURE.md`](../ARCHITECTURE.md) establishes observability as a core architectural concern. This document expands where visibility is required.

# Observability by Design

Operational visibility is considered a core architectural concern rather than an optional enhancement.

The platform should provide visibility into:

* Requests
* Background jobs
* AI inference
* Connector synchronization
* Search operations
* Errors
* Performance

Every major subsystem should produce meaningful telemetry that assists with debugging, optimization, and long-term maintenance.

# Observability Stack

The project identifies the following observability technologies:

* OpenTelemetry
* Prometheus
* Grafana
* Loki

These technologies support tracing, metrics, dashboards, and logs without changing the underlying architecture.

# Request Visibility

Every request should remain predictable, observable, and easy to reason about.

Failures should produce meaningful telemetry for debugging and observability.

Useful request-level signals include:

* Request duration
* Route or operation name
* Authentication and authorization failures
* Domain-level failures
* Infrastructure failures
* Response status

See [`request-lifecycle.md`](request-lifecycle.md).

# Event Visibility

Every published event should produce telemetry.

Examples include:

* Publication time
* Processing latency
* Consumer duration
* Retry count
* Failure rate
* Queue depth
* Throughput

Observability is considered part of the event system itself.

See [`event-architecture.md`](event-architecture.md).

# Worker Visibility

Workers perform long-running processing and should expose enough visibility to understand progress and failures.

Important concerns include:

* Worker start and completion
* Retry scheduling
* Permanent failures
* Queue latency
* Stage duration
* Pipeline interruption

Worker failures should remain isolated and should not terminate unrelated processing.

# Pipeline Visibility

The knowledge pipeline should make each stage observable:

* Acquisition
* Normalization
* Storage
* Processing
* Knowledge creation
* Indexing
* Retrieval
* Intelligence

This visibility makes it possible to determine where information is delayed, failed, or ready for retrieval.

See [`knowledge-processing-pipeline.md`](knowledge-processing-pipeline.md).

# Search Visibility

Search operations should be observable because retrieval quality and latency directly affect user experience and Intelligence behavior.

Useful signals include:

* Query latency
* Retrieval strategy
* Result counts
* Ranking behavior
* Index availability
* Failure rates

See [`search-architecture.md`](search-architecture.md).

# Intelligence Visibility

AI inference and Intelligence workflows should expose visibility into provider behavior and workflow performance.

Useful signals include:

* Provider name
* Request duration
* Failure rate
* Retrieval latency
* Context assembly behavior
* Tool orchestration duration

Knowledge remains independent from providers, but provider behavior must still be observable.

See [`intelligence-architecture.md`](intelligence-architecture.md).

# Connector Visibility

Connector synchronization should be observable because external systems introduce latency, partial failure, authentication failures, and provider-specific availability concerns.

Useful signals include:

* Connector type
* Synchronization start and completion
* Imported item counts
* Failure counts
* Retry counts
* Authorization failures

See [`connector-framework.md`](connector-framework.md).

# As-Built Foundation

The `memovi_observability` package provides the cross-cutting runtime surface:

* **RequestContext** — `request_id`, optional `workspace_id`, optional `correlation_id`, `timestamp`, optional `principal` (future auth). Bound by API middleware via ContextVar; workspace resolution updates the same context for the request.
* **Structured logging** — JSON log records with consistent fields: `request_id`, `workspace_id`, `correlation_id`, `operation`, `duration_ms`, `status`, `error`, `repository`, `event`.
* **Diagnostic events** — lightweight emitter that logs standardized names only (no second bus). The composition-root bridge maps pipeline domain events:
  * `DocumentCreated` → `DocumentUploaded`
  * `KnowledgeMaterialized` → `MemoryCreated`
  * `SearchIndexed` → `DocumentIndexed`
  * Direct emits: `WorkspaceCreated`, `ConversationCreated`, `SearchExecuted`
* **Metrics** — `MetricsRecorder` protocol with an in-memory implementation; timings/counters for HTTP, upload, search, embedding, conversation, memory lookup, and repository hot paths. Export adapters (Prometheus/OTel) can plug in later.
* **Tracing** — OpenTelemetry API spans around HTTP requests and timed operations; no exporter required.
* **Health** — `GET /health` liveness; `GET /ready` readiness with `database`, `vector_search`, `embedding_provider`, `migrations`, `workspace`, and `search_readiness` component checks.

The existing in-process pipeline event bus remains the source of truth for domain facts. Observability adapts those facts into diagnostic logs and metrics.

# Key Decisions

* Observability is part of the architecture, not an optional enhancement.
* Requests, events, workers, AI inference, connector sync, search, errors, and performance require visibility.
* Event telemetry includes publication time, processing latency, retries, queue depth, and throughput.
* Failures should produce meaningful telemetry without exposing implementation details to clients.
* Observability supports debugging, optimization, and long-term maintenance.
* Diagnostic event names are an observability concern; pipeline domain event names are not renamed.

# Related Documents

* [`../ARCHITECTURE.md`](../ARCHITECTURE.md)
* [`request-lifecycle.md`](request-lifecycle.md)
* [`event-architecture.md`](event-architecture.md)
* [`knowledge-processing-pipeline.md`](knowledge-processing-pipeline.md)
* [`search-architecture.md`](search-architecture.md)
* [`intelligence-architecture.md`](intelligence-architecture.md)
* [`connector-framework.md`](connector-framework.md)
* [`deployment.md`](deployment.md)
