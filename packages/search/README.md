# Memovi Search

Search and retrieval domain boundary. This package owns searchable document
representations, embedding metadata, and the contracts that downstream retrieval
capabilities will consume.

## Current scope

This package establishes the search domain foundation:

- Domain entities: `SearchDocument` and `Embedding` with enforced invariants
- Value objects: `SearchDocumentId` and `EmbeddingId`
- Repository contract: `SearchRepository`
- Domain events: `SearchDocumentRegistered` and `EmbeddingRecorded`
- Application DTOs, ports, and layer scaffolds for future use cases
- SQLAlchemy persistence models and repository implementation

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

## Document boundary

Search references processed documents and memory chunks by string UUID
identifiers. It does not import the Documents or Memory domains directly.
Normalized source text and chunk content remain owned by their source domains
until future use cases register searchable representations.
