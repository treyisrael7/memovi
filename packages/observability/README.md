# Memovi Observability

Cross-cutting request context, structured logging, diagnostic event emission,
metrics recording, and provider-neutral OpenTelemetry spans.

## Contents

* `RequestContext` — request/workspace/correlation identity bound at the API boundary
* Structured JSON logging with consistent field names
* `DiagnosticEventEmitter` — log + metric only (no event bus)
* `MetricsRecorder` — future-compatible counters and timings
* OpenTelemetry API spans (no exporter required)

Domain packages should not invent request IDs or telemetry formats. Bind
`RequestContext` at the API boundary and use the helpers in this package for
logs, metrics, spans, and diagnostic events.
