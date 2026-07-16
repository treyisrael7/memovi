# Memovi Search

Search and retrieval domain boundary. This package owns searchable projections
of durable knowledge, embedding metadata, and retrieval capabilities that
consume indexed knowledge.

## Current scope

This package provides the search domain model, materialization workflow, and
first retrieval capability:

- Domain entities: `SearchDocument` and `Embedding` with enforced invariants
- Value objects: `SearchDocumentId`, `EmbeddingId`, and `EmbeddingVector`
- Provider protocol: `EmbeddingProvider` for interchangeable embedding generators
- Application service: `EmbeddingGenerationService` for provider-agnostic generation
- Placeholder providers: OpenAI, Ollama, and Sentence Transformer (not implemented)
- Deterministic `FakeEmbeddingProvider` for local wiring and tests
- Provider selection: `EmbeddingProviderConfig` / `build_embedding_provider`
- Repository contracts: `SearchRepository` (full-text) and `EmbeddingRepository`
- Domain service: `SearchMaterializer` for deterministic search document creation
- Application commands: `MaterializeSearchDocument` and `GenerateEmbedding`
- Application handlers: `SearchKnowledgeMaterializedHandler` and
  `SearchIndexedEmbeddingHandler` for event-driven indexing and embedding
- Application query: `SearchKnowledge` for ranked full-text retrieval
- Public HTTP API: `GET /search` for ranked full-text retrieval with optional
  metadata filters
- Domain events: `SearchDocumentRegistered`, `SearchIndexed`, and `EmbeddingGenerated`
- Application DTOs, ports, and layer scaffolds for future use cases
- SQLAlchemy persistence models and repository implementations
- Embedding vectors stored as JSON `list[float]` (pgvector not yet)

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

## Search API

`GET /search` exposes ranked full-text retrieval over HTTP:

| Parameter | Required | Default | Notes |
|-----------|----------|---------|-------|
| `q` | yes | — | Non-empty search query |
| `document_id` | no | — | Restrict to one document |
| `source_type` | no | — | Restrict by source type |
| `mime_type` | no | — | Restrict by MIME type |
| `created_after` | no | — | Inclusive lower bound on `created_at` |
| `created_before` | no | — | Inclusive upper bound on `created_at` |
| `limit` | no | `25` | Maximum `100` |
| `offset` | no | `0` | Must be non-negative |

Optional metadata filters are applied to search projections before ranking.
When omitted, search behavior is unchanged.

The response returns the normalized query, result count, and ranked matches with
`search_document_id`, `knowledge_item_id`, `document_id`, `score`, and `text`.
The route stays thin: it validates query parameters, calls `SearchKnowledge`,
and maps `SearchResultDto` values to the public response schema.

## Layout

- `domain` — business model, invariants, provider protocols, repository interfaces, and events
- `application` — use cases, generation services, DTOs, ports, and worker placeholders
- `infrastructure` — persistence models, SQLAlchemy repositories, and provider adapters
- `api` — FastAPI router, dependencies, and response schemas for search

## Embedding generation

`SearchIndexed` triggers `SearchIndexedEmbeddingHandler`, which loads the
canonical `SearchDocument`, generates a vector through
`EmbeddingGenerationService`, persists an `Embedding` projection, and publishes
`EmbeddingGenerated`. Embeddings are derived data and remain reproducible from
`SearchDocument` text.

The composition root currently wires `FakeEmbeddingProvider` so the pipeline is
exercisable without external embedding APIs. Provider identity (`provider`,
`model`) is recorded on each embedding for later regeneration.

## Out of scope for this foundation

- Live embedding generation against OpenAI, Ollama, or Sentence Transformers
- Vector storage and pgvector integration
- Vector similarity search and hybrid retrieval
- Intelligence / answer generation

Cross-domain wiring from memory materialization to search indexing lives in
the API composition root (`apps/api`), which subscribes to `KnowledgeMaterialized`
and invokes `SearchKnowledgeMaterializedHandler` without creating a compile-time
dependency from Memory to Search or Search to Memory. `SearchIndexed` similarly
drives embedding generation inside Search.

## Memory boundary

Search references knowledge items and processed documents by string UUID
identifiers. It does not import the Memory or Documents domains. Canonical
knowledge and normalized source text remain owned by Memory until future use
cases register searchable projections.
