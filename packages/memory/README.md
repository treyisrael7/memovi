# Memovi Memory

Memory and knowledge organization domain boundary. This package owns durable
knowledge concepts that downstream search and intelligence capabilities consume.

## Current scope

This package establishes the memory domain foundation:

- Domain entities: `KnowledgeItem` and `Chunk` with enforced invariants
- Value objects: `KnowledgeItemId`, `ChunkId`, and `ChunkIndex`
- Repository contracts: `KnowledgeRepository` and `ChunkRepository`
- Domain services: deterministic `ChunkGenerator` and `KnowledgeMaterializer`
- Domain events: `KnowledgeConstructed` and `ChunksGenerated`
- Application DTOs, ports, and layer scaffolds for future use cases
- Application command: `MaterializeKnowledge` for persistence orchestration
- SQLAlchemy persistence models and repository implementations

The import package is `memovi_memory` because the package boundary is already
clear from `packages/memory`.

## Layout

- `domain` — business model, invariants, repository interfaces, and events
- `application` — use-case scaffolds, DTOs, ports, and worker placeholders
- `infrastructure` — persistence models and SQLAlchemy repositories
- `api` — router, dependency, and schema scaffolds without endpoints yet

## Out of scope for this foundation

- Knowledge construction workflows
- Chunk generation
- Embeddings and vector indexes
- Search integration
- AI summarization or reasoning
- FastAPI registration, migrations, and composition-root wiring

## Document boundary

Memory references processed documents by `document_id` and `document_version_id`
string identifiers. It does not import the Documents domain. Normalized source
text remains owned by Documents until future use cases materialize knowledge.
