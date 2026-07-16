# Memovi API

The API application package is the backend composition root for Memovi.

It is responsible for assembling the FastAPI platform, registering routers,
configuring application lifecycle behavior, wiring request-scoped infrastructure
dependencies, and exposing operational endpoints such as health checks.

Business behavior remains in domain packages. For example, local authentication
lives in `packages/auth`; this app only wires its router and database session
dependency into the running API.

Cross-domain event wiring also lives here: document processing publishes
`ProcessingCompleted`, and the composition root dispatches it to
`MemoryProcessingCompletedHandler`, which materializes knowledge and publishes
`KnowledgeMaterialized`. Search subscribes through
`SearchKnowledgeMaterializedHandler`, which materializes searchable documents
and publishes `SearchIndexed`. Search then generates embedding projections via
`SearchIndexedEmbeddingHandler` and publishes `EmbeddingGenerated`.

Run the local API development server from the repository root:

```bash
task backend
```

The health endpoint is available at `http://localhost:8000/health`.
Authentication endpoints are available under `http://localhost:8000/auth`.
Full-text search is available at `http://localhost:8000/search`.
