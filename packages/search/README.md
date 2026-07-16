# Memovi Search

Search and retrieval domain boundary. This package owns searchable projections
of durable knowledge, embedding metadata, and retrieval capabilities that
consume indexed knowledge.

## Current scope

This package provides the search domain model, materialization workflow, and
first retrieval capability:

- Domain entities: `SearchDocument` and `Embedding` with enforced invariants
- Value objects: `SearchDocumentId` and `EmbeddingId`
- Repository contract: `SearchRepository` with PostgreSQL full-text search
- Domain service: `SearchMaterializer` for deterministic search document creation
- Application command: `MaterializeSearchDocument` for persistence orchestration
- Application handler: `SearchKnowledgeMaterializedHandler` for event-driven indexing
- Application query: `SearchKnowledge` for ranked full-text retrieval
- Domain events: `SearchDocumentRegistered`, `EmbeddingRecorded`, and `SearchIndexed`
- Application DTOs, ports, and layer scaffolds for future use cases
- SQLAlchemy persistence models and repository implementation

Search owns derived retrieval structures. It does not own canonical knowledge.
Everything in Search must be reproducible from Memory.

The import package is `memovi_search` because the package boundary is already
clear from `packages/search`.

## Full-text search

`SearchDocument` persistence stores:

- `searchable_text` — normalized text assembled from canonical memory chunks
- `search_vector` — PostgreSQL `tsvector` generated with the English text search
  configuration whenever a search document is created or updated

A GIN index on `search_vector` supports ranked retrieval ordered by
`ts_rank`. The `SearchKnowledge` query returns `SearchResultDto` records with
document identifiers, searchable text, and relevance scores.

## Layout

- `domain` — business model, invariants, repository interfaces, and events
- `application` — use cases, DTOs, ports, and worker placeholders
- `infrastructure` — persistence models and SQLAlchemy repositories
- `api` — router, dependency, and schema scaffolds without endpoints yet

## Out of scope for this foundation

- Embedding generation workflows
- Vector storage and pgvector integration
- Hybrid retrieval and reranking
- FastAPI search endpoints

Cross-domain wiring from memory materialization to search indexing lives in
the API composition root (`apps/api`), which subscribes to `KnowledgeMaterialized`
and invokes `SearchKnowledgeMaterializedHandler` without creating a compile-time
dependency from Memory to Search or Search to Memory.

## Memory boundary

Search references knowledge items and processed documents by string UUID
identifiers. It does not import the Memory or Documents domains. Canonical
knowledge and normalized source text remain owned by Memory until future use
cases register searchable projections.
