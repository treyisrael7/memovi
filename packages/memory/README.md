# Memovi Memory

Memory and knowledge organization domain boundary. This package owns durable
knowledge concepts that downstream search and intelligence capabilities consume.

## Current scope

This package establishes the memory domain foundation:

- Domain entities: `KnowledgeItem` and `Chunk` with enforced invariants
- Value objects: `KnowledgeItemId`, `ChunkId`, and `ChunkIndex`
- Repository contracts: `KnowledgeRepository` and `ChunkRepository`
- Domain services: deterministic `ChunkGenerator` and `KnowledgeMaterializer`
- Domain events: `KnowledgeConstructed`, `ChunksGenerated`, and `KnowledgeMaterialized`
- Application DTOs, ports, and layer scaffolds for future use cases
- Application command: `MaterializeKnowledge` for persistence orchestration
- Application handler: `MemoryProcessingCompletedHandler` for event-driven materialization
- Application queries: `GetKnowledge`, `ListKnowledge`, `ListDocumentKnowledge`,
  `ListConcepts`, `ListRelationships`, and `GetKnowledgeDashboard`
- Read DTOs: `KnowledgeDto`, `KnowledgeItemDto`, `ChunkDto`, explorer projections
- SQLAlchemy persistence models and repository implementations
- HTTP read API for Knowledge Explorer (`/memory` list/detail/dashboard/concepts/relationships)

The import package is `memovi_memory` because the package boundary is already
clear from `packages/memory`.

## Layout

- `domain` — business model, invariants, repository interfaces, and events
- `application` — use cases, DTOs, ports, and worker placeholders
- `infrastructure` — persistence models and SQLAlchemy repositories
- `api` — FastAPI router, dependencies, and response schemas

## Out of scope for this foundation

- Embeddings and vector indexes
- Search integration
- AI summarization or reasoning
- Semantic entity / topic extraction and confidence scoring
- Mutations (edit/merge/delete) and knowledge version history

Cross-domain wiring from document processing to memory materialization lives in
the API composition root (`apps/api`), which subscribes to `ProcessingCompleted`
and invokes `MemoryProcessingCompletedHandler` without creating a compile-time
dependency from Documents to Memory. The composition root also registers the
Memory router and overrides workspace/session dependencies.

## Document boundary

Memory references processed documents by `document_id` and `document_version_id`
string identifiers. It also stores denormalized `source_type` and `mime_type` so
search projections can be rematerialized from Memory without joining Documents.
It does not import the Documents domain. Normalized source text remains owned by
Documents until future use cases materialize knowledge.
