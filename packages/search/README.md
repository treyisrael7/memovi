# Memovi Search

Search and retrieval domain boundary. This package owns searchable projections
of durable knowledge, embedding metadata, and the contracts that downstream
retrieval capabilities will consume.

## Current scope

This package establishes the search domain model and first materialization use case:

- Domain entities: `SearchDocument` and `Embedding` with enforced invariants
- Value objects: `SearchDocumentId` and `EmbeddingId`
- Repository contract: `SearchRepository`
- Domain service: `SearchMaterializer` for deterministic search document creation
- Application command: `MaterializeSearchDocument` for persistence orchestration
- Domain events: `SearchDocumentRegistered` and `EmbeddingRecorded`
- Application DTOs, ports, and layer scaffolds for future use cases
- SQLAlchemy persistence models and repository implementation

Search owns derived retrieval structures. It does not own canonical knowledge.
Everything in Search must be reproducible from Memory.

The import package is `memovi_search` because the package boundary is already
clear from `packages/search`.

## Layout

- `domain` — business model, invariants, repository interfaces, and events
- `application` — use-case scaffolds, DTOs, ports, and worker placeholders
- `infrastructure` — persistence models and SQLAlchemy repositories
- `api` — router, dependency, and schema scaffolds without endpoints yet

## Out of scope for this foundation

- Indexing workflows
- Vector storage and pgvector integration
- Retrieval and ranking
- FastAPI registration, event handlers, and migrations

Cross-domain wiring from memory materialization to search indexing will live in
the API composition root when those use cases are implemented.

## Memory boundary

Search references knowledge items and processed documents by string UUID
identifiers. It does not import the Memory or Documents domains. Canonical
knowledge and normalized source text remain owned by Memory until future use
cases register searchable projections.
