# Memovi Search

Search and retrieval domain boundary. This package owns searchable projections
of durable knowledge, embedding metadata, and retrieval capabilities that
consume indexed knowledge.

## Current scope

This package provides the search domain model, materialization workflow, and
unified retrieval:

- Domain entities: `SearchDocument`, `Embedding`, and `SearchResult`
- Value objects: `SearchDocumentId`, `EmbeddingId`, and `EmbeddingVector`
- Retrievers: `KeywordRetriever` and `SemanticRetriever` behind a shared
  `Retriever` protocol
- Ranking: Reciprocal Rank Fusion (`RankFusion`) and `ScoreNormalizer`
- Application service: `RetrievalEngine` orchestrates retrieval, fusion,
  filtering, normalization, and pagination
- Application query: `RetrieveKnowledge` (modes: `keyword`, `semantic`, `hybrid`)
- Provider protocol: `EmbeddingProvider` for interchangeable embedding generators
- Application service: `EmbeddingGenerationService` for provider-agnostic generation
- Deterministic `FakeEmbeddingProvider` for local wiring and tests
- Repository contracts: `SearchRepository` and `EmbeddingRepository`
- Public HTTP API: `GET /search` with `mode` (hybrid default); `GET /search/semantic`
  is deprecated and routes through the same engine
- Embedding vectors stored with PostgreSQL pgvector (`vector(N)` + HNSW cosine index)

Search owns derived retrieval structures. It does not own canonical knowledge.
Everything in Search must be reproducible from Memory.

## Unified retrieval

`RetrieveKnowledge` builds a retrieval request, runs the enabled retrievers,
fuses rankings with RRF for hybrid mode, applies metadata filters, normalizes
scores for presentation, then paginates.

| Mode | Behavior |
|------|----------|
| `keyword` | Full-text (`ts_rank`) only |
| `semantic` | Vector cosine similarity only |
| `hybrid` | RRF merge of keyword and semantic (default) |

## Search API

`GET /search`:

| Parameter | Required | Default | Notes |
|-----------|----------|---------|-------|
| `q` | yes | — | Non-empty search query |
| `mode` | no | `hybrid` | `keyword`, `semantic`, or `hybrid` |
| `document_id` | no | — | Restrict to one document |
| `source_type` | no | — | Restrict by source type |
| `mime_type` | no | — | Restrict by MIME type |
| `created_after` | no | — | Inclusive lower bound on `created_at` |
| `created_before` | no | — | Inclusive upper bound on `created_at` |
| `limit` | no | `25` | Maximum `100` |
| `offset` | no | `0` | Must be non-negative |

`GET /search/semantic` is deprecated; use `GET /search?mode=semantic`.

## Layout

- `domain` — model, retrievers, ranking, repository interfaces, events
- `application` — use cases, `RetrievalEngine`, generation services, DTOs
- `infrastructure` — persistence models, SQLAlchemy repositories, providers
- `api` — FastAPI router, dependencies, response schemas

## Out of scope

- Live embedding generation against OpenAI, Ollama, or Sentence Transformers
- AI reasoning, answer generation, or LLM prompts
- Reranking models beyond RRF

## Memory boundary

Search references knowledge items and processed documents by string UUID
identifiers. It does not import the Memory or Documents domains.
