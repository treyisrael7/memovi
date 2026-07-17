# Memovi Engineering Snapshot

Handoff document for a principal engineer or AI assistant.
Generated from repository inspection. No speculative claims.
If something is not present in the repository, it is stated as absent.

Companion documents:

* `ROADMAP.md` / `ROADMAP_V2.md` — direction
* `STATUS.md` — living implementation tracker
* `ARCHITECTURE.md` — architecture blueprint

---

# 1 Repository Overview

## Directory tree (collapsed)

```text
memovi/
├── .cursor/
├── .devcontainer/
├── .github/workflows/
├── apps/
│   ├── api/                 # FastAPI composition root (memovi-api)
│   └── web/                 # Next.js shell (placeholder UI)
├── packages/
│   ├── auth/                # memovi-auth
│   ├── config/              # memovi-config (scaffold)
│   ├── connectors/          # memovi-connectors (scaffold)
│   ├── contracts/           # memovi-contracts (scaffold)
│   ├── documents/           # memovi-documents
│   ├── intelligence/        # memovi-intelligence
│   ├── memory/              # memovi-memory
│   ├── observability/       # memovi-observability (scaffold)
│   ├── search/              # memovi-search
│   └── shared/              # memovi-shared (scaffold)
├── database/
│   └── migrations/versions/ # Alembic revisions
├── docker/                  # .gitkeep only
├── docs/
│   ├── adr/
│   ├── architecture/
│   ├── development/
│   └── diagrams/
├── scripts/
├── tests/
├── ARCHITECTURE.md
├── CONTRIBUTING.md
├── ENGINEERING_SNAPSHOT.md
├── LICENSE
├── PHILOSOPHY.md
├── README.md
├── ROADMAP.md
├── ROADMAP_V2.md
├── STATUS.md
├── alembic.ini
├── compose.yml
├── package.json
├── pnpm-workspace.yaml
├── pyproject.toml
├── Taskfile.yml
└── uv.lock
```

## Major packages

| Package | Distribution | Import root | Status |
|---------|--------------|-------------|--------|
| auth | `memovi-auth` | `auth` | Implemented |
| documents | `memovi-documents` | `documents` | Implemented |
| memory | `memovi-memory` | `memovi_memory` | Implemented (no HTTP routes) |
| search | `memovi-search` | `memovi_search` | Implemented |
| intelligence | `memovi-intelligence` | `memovi_intelligence` | Implemented |
| config | `memovi-config` | `memovi_config` | Scaffold only |
| connectors | `memovi-connectors` | `memovi_connectors` | Scaffold only |
| contracts | `memovi-contracts` | `memovi_contracts` | Scaffold only |
| observability | `memovi-observability` | `memovi_observability` | Scaffold only |
| shared | `memovi-shared` | `memovi_shared` | Scaffold only |

## Apps

| App | Role |
|-----|------|
| `apps/api` | Backend composition root. Registers routers, DB sessions, document processing worker, in-process event bus, memory/search integration adapters. |
| `apps/web` | Next.js frontend workspace shell. No product chat or knowledge UI. |

## Shared libraries

There is no substantive shared library code.

* `packages/shared` — empty package root
* `packages/contracts` — empty `events/`, `messages/`, `schemas/`
* `packages/config` — empty settings package
* `packages/observability` — empty `logging/`, `metrics/`, `tracing/`

Cross-domain coupling is composed only in `apps/api`, not via shared packages.

---

# 2 Domain Architecture

Domain packages do **not** import each other. Cross-domain wiring lives in `apps/api`.

There is **no** shared `DomainEvent` base class. Events are plain dataclasses / classes per package.

---

## Auth (`packages/auth`)

### Responsibilities

Local identity for a self-hosted instance: registration, login, logout, session cookies, current user. Argon2id password hashing. No JWT, OAuth, RBAC, or API keys.

### Public interfaces

* HTTP router: `auth.api.router` (`prefix="/auth"`)
* Application commands/queries via FastAPI dependencies

### Commands

* `RegisterUser` / `RegisterUserCommand` / `AuthenticatedUserResult`
* `LoginUser` / `LoginUserCommand`
* `LogoutUser`

### Queries

* `GetCurrentUser`

### Services

* Application/domain service packages exist as scaffolds; no additional application service classes beyond commands/queries.
* Ports: `PasswordHasher`, `SessionTokenService`

### Repositories

* Domain: `UserRepository`, `SessionRepository`
* Infra: `SqlAlchemyUserRepository`, `SqlAlchemySessionRepository`

### Domain events

* `UserRegistered`
* `UserLoggedIn`

Neither is published on the composition-root event bus.

### Entities

* `User`
* `Session`

### Value objects

* `Email`
* `PasswordHash`
* `UserId`

### DTOs / API schemas

* DTO: `UserDto`
* API: `AuthCredentialsRequest`, `UserResponse`

### API routers

* `POST /auth/register`
* `POST /auth/login`
* `POST /auth/logout`
* `GET /auth/me`

### Dependencies on other domains

None.

---

## Documents (`packages/documents`)

### Responsibilities

Document ingestion, object storage, processing jobs, background processing for PDF/Markdown/plain text, normalized content, processing lifecycle events.

### Public interfaces

* HTTP router: `documents.api.router` (`prefix="/documents"`)
* Commands used by worker and API

### Commands

* `CreateDocument` / `CreateDocumentCommand` / `CreateDocumentResult`
* `IngestLocalDocument` / `IngestLocalDocumentCommand` / `IngestLocalDocumentResult`
* `EnqueueDocumentProcessing` / `EnqueueDocumentProcessingCommand`
* `StartProcessing` / `StartProcessingCommand` / `StartProcessingResult`
* `CompleteProcessing` / `CompleteProcessingCommand` / `CompleteProcessingResult`
* `FailProcessing` / `FailProcessingCommand` / `FailProcessingResult`
* `ProcessDocument` / `ProcessDocumentCommand` / `ProcessDocumentResult`

### Queries

* `GetDocument`
* `ListDocuments`

Wired in dependencies; **not** exposed on the HTTP router.

### Services / workers

* Domain: `normalize_text`
* Worker: `DocumentProcessingWorker`, `DocumentProcessingWorkerConfig`
* Processors: `MarkdownDocumentProcessor`, `PdfDocumentProcessor`, `PlainTextDocumentProcessor`, `DefaultProcessorRegistry`

### Repositories / ports

* Domain repos: `DocumentRepository`, `ProcessingJobRepository`
* Infra: `SqlAlchemyDocumentRepository`, `SqlAlchemyProcessingJobRepository`
* Ports: `ProcessingJobQueue`, `ObjectStorage`, `DocumentProcessor`, `ProcessorRegistry`, `EventPublisher`
* Queue: `InMemoryProcessingJobQueue`, `NoOpProcessingJobQueue`
* Storage: `MinioObjectStorage`
* Publishers: `NoOpEventPublisher`, `CollectingEventPublisher`

### Domain events

* `DocumentCreated`
* `ProcessingStarted`
* `ProcessingCompleted`
* `ProcessingFailed`

### Entities / enums

* Entities: `Document`, `DocumentVersion`, `ProcessingJob`
* Enum: `ProcessingStatus`

### Value objects

* `DocumentId`, `DocumentName`, `MimeType`, `SourceType`

### DTOs / API schemas

* DTO: `DocumentDto`
* API: `CreateDocumentRequest`, `DocumentResponse`, `DocumentListResponse`, `IngestDocumentResponse`

### API routers

* `POST /documents` (multipart upload → ingest; returns 202)

No GET/list document routes are registered.

### Dependencies on other domains

None in package source. Downstream effects occur only via events handled in `apps/api`.

Note: empty twin tree `packages/documents/src/memovi_documents/` exists with no files.

---

## Memory (`packages/memory`)

### Responsibilities

Durable knowledge items and chunks. Materialization from processed documents. Chunk generation. Event-driven handoff into Search (via composition root).

### Public interfaces

* Application command/queries/handlers
* Empty HTTP router `prefix="/memory"` (no endpoints)
* Router is **not** registered in `apps/api`

### Commands

* `MaterializeKnowledge` / `MaterializeKnowledgeCommand` / `MaterializeKnowledgeResult`

### Queries

* `GetKnowledge`
* `ListKnowledge`
* `ListDocumentKnowledge`

### Services / handlers

* Domain: `ChunkGenerator`, `ChunkDraft`, `KnowledgeMaterializer`, `KnowledgeMaterializationResult`
* Handler: `MemoryProcessingCompletedHandler`

### Repositories / ports

* Domain: `KnowledgeRepository`, `ChunkRepository`
* Infra: `SqlAlchemyKnowledgeRepository`, `SqlAlchemyChunkRepository`
* Ports: `EventPublisher`, `ProcessedDocumentReader`

### Domain events

* `KnowledgeMaterialized` (published on bus)
* `KnowledgeConstructed` (defined; not published on bus)
* `ChunksGenerated` (defined; not published on bus)

### Entities

* `KnowledgeItem`
* `Chunk`

### Value objects

* `KnowledgeItemId`, `ChunkId`, `ChunkIndex`

### DTOs / API schemas

* DTOs: `KnowledgeDto`, `KnowledgeItemDto`, `ChunkDto`, `ProcessedDocumentSnapshot`, `ProcessingCompletedNotification`
* API schemas exist but are unused by routes: `KnowledgeItemResponse`, `ChunkResponse`, `KnowledgeItemListResponse`

### API routers

None active.

### Dependencies on other domains

None in package source. `ProcessedDocumentReader` is implemented in `apps/api` over documents repositories.

---

## Search (`packages/search`)

### Responsibilities

Search document projections, full-text search, embeddings, keyword/semantic/hybrid retrieval via `RetrievalEngine`, metadata filtering, event-driven indexing from Memory.

### Public interfaces

* HTTP router: `memovi_search.api.router` (`prefix="/search"`)
* Queries: `RetrieveKnowledge`, `SemanticSearch`, `SearchKnowledge`

### Commands

* `MaterializeSearchDocument` / `MaterializeSearchDocumentCommand` / `MaterializeSearchDocumentResult`
* `GenerateEmbedding` / `GenerateEmbeddingCommand` / `GenerateEmbeddingResult`

### Queries

* `RetrieveKnowledge` / `RetrieveKnowledgeQuery`
* `SearchKnowledge` / `SearchKnowledgeQuery`
* `SemanticSearch` / `SemanticSearchQuery`

### Services / handlers

* `RetrievalEngine`, `RetrievalMode`, `RetrievalEngineRequest`
* `EmbeddingGenerationService`
* `SearchMaterializer`
* Handlers: `SearchKnowledgeMaterializedHandler`, `SearchIndexedEmbeddingHandler`
* Ranking: `RankFusion`, `ScoreNormalizer`
* Retrievers: `KeywordRetriever`, `SemanticRetriever`, protocol `Retriever`

### Repositories / ports / providers

* Domain repos: `SearchRepository`, `EmbeddingRepository`
* Infra: `SqlAlchemySearchRepository`, `SqlAlchemyEmbeddingRepository`
* Ports: `EventPublisher`, `KnowledgeReader`
* Provider protocol: `EmbeddingProvider`
* Providers: `FakeEmbeddingProvider` (used in composition), `OpenAIEmbeddingProvider`, `OllamaEmbeddingProvider`, `SentenceTransformerEmbeddingProvider` (latter three raise `NotImplementedError` on embed)

### Domain events

* `SearchIndexed` (published; subscribed for embeddings)
* `EmbeddingGenerated` (published; no subscribers)
* `SearchDocumentRegistered` (defined; not published on bus)

### Entities / value objects

* Entities: `SearchDocument`, `Embedding`, `SearchResult`, `RankedSearchDocument`
* VOs: `SearchDocumentId`, `EmbeddingId`, `EmbeddingVector`

### DTOs / API schemas

* DTOs: `SearchDocumentDto`, `SearchResultDto`, `EmbeddingDto`, `SearchFilters`, `KnowledgeReadDto`, `KnowledgeChunkReadDto`, `KnowledgeMaterializedNotification`
* API: `SearchResponse`, `SearchResultItemResponse` (used); `SearchDocumentResponse`, `EmbeddingResponse`, `SearchDocumentListResponse` (defined, unused by routes)

### API routers

* `GET /search`
* `GET /search/semantic` (deprecated)

### Dependencies on other domains

None in package source. `KnowledgeReader` is implemented in `apps/api` over Memory `GetKnowledge`.

---

## Intelligence (`packages/intelligence`)

### Responsibilities

Reasoning orchestration, conversation memory, Conversation REST API, provider-agnostic prompts, model gateway, execution tracing, tool framework (not wired into Reason path).

### Public interfaces

* HTTP router: `memovi_intelligence.api.router` (`prefix="/conversations"`)
* Commands: `Reason`, `SendConversationMessage`

### Commands

* `Reason` — takes domain `ReasoningRequest` (+ optional `ConversationHistory`)
* `SendConversationMessage` / `SendConversationMessageCommand` / `SendConversationMessageResult`

### Queries

None under `application/queries/`.

### Services

* `ConversationService`
* `ContextAssembler`
* `PromptBuilder`
* `ModelGateway`
* `ReasoningService` (facade)
* `ExecutionTracer`
* `ToolRegistry`
* `ToolExecutor`
* Domain: `estimate_token_count`

### Repositories / ports

* Ports: `KnowledgeRetriever`, `ReasoningProvider`, `ConversationRepository`, `Tool`
* Infra: `InMemoryConversationRepository`
* Retrieval: `FakeKnowledgeRetriever`, `PlaceholderKnowledgeRetriever`
* Providers: `FakeReasoningProvider`, `OpenAIReasoningProvider`, `PlaceholderReasoningProvider`, `build_model_gateway`
* Tools: `EchoTool`
* Config: `IntelligenceConfig`, `ReasoningProviderKind`

### Domain events

None. `memovi_intelligence/events/__init__.py` is empty.

### Entities

* `Conversation`
* `ReasoningRequest`
* `ReasoningContext`
* `ReasoningResult`

### Value objects

Conversation: `ConversationId`, `ConversationRole`, `ConversationTurn`, `ConversationHistory`  
Reasoning: `ReasoningRequestId`, `ReasoningQuery`, `RetrievedKnowledge`, `AssembledDocument`, `ContextMetadata`, `Citation`  
Prompt: `Prompt`, `PromptMessage`, `PromptRole`, `PromptSection`  
Execution: `ExecutionTrace`, `ExecutionStage`, `StageTiming`, `ExecutionMetrics`  
Tools: `ToolCall`, `ToolResult`, `ToolDefinition`, `ToolParameter`

### DTOs / API schemas

* `CreateConversationResponse`
* `ConversationMetadataResponse`
* `ConversationMessageResponse`
* `ConversationMessagesResponse`
* `SendMessageRequest`
* `SendMessageResponse`
* `CitationResponse`
* `ExecutionMetadataResponse`
* `ExecutionMetricsResponse`
* `StageTimingResponse`

### API routers

* `POST /conversations`
* `GET /conversations/{conversation_id}`
* `GET /conversations/{conversation_id}/messages`
* `POST /conversations/{conversation_id}/messages`

### Dependencies on other domains

None in package source. Package defaults use `FakeKnowledgeRetriever` and `InMemoryConversationRepository` for isolated tests. `apps/api` overrides `KnowledgeRetriever` with `SearchKnowledgeRetriever` (Search `RetrieveKnowledge`).

---

## Scaffold domains

### Config

Empty typed-settings package. No runtime settings objects beyond what other packages own locally.

### Connectors

Empty layer folders. No connector implementations.

### Contracts

Empty shared events/messages/schemas.

### Observability

Empty logging/metrics/tracing folders.

### Shared

Empty package.

---

# 3 Event Flow

## Event bus

* `InProcessEventDispatcher` — synchronous subscribe/publish
* `TransactionScopedEventPublisher` — buffers until `flush()`
* Location: `apps/api/src/api/events/in_process_event_dispatcher.py`
* Wired in: `apps/api/src/api/memory_integration.py` (+ search registration)

There is no out-of-process message bus. Redis exists in Compose but has no application client usage found.

## Every domain event

| Event | Publisher | Subscribers | Trigger | Resulting actions |
|-------|-----------|-------------|---------|-------------------|
| `DocumentCreated` | Returned by `CreateDocument` / `IngestLocalDocument` | None on bus | Document create/ingest | Returned to caller only; not bus-published |
| `ProcessingStarted` | `ProcessDocument` publishes; `StartProcessing` returns | None on bus | Processing starts | Status transition |
| `ProcessingCompleted` | `ProcessDocument` / worker via publisher; `CompleteProcessing` returns | `MemoryProcessingCompletedHandler` | Successful processing | Memory materialization |
| `ProcessingFailed` | `ProcessDocument` / worker; `FailProcessing` returns | None on bus | Processing failure | Job marked failed |
| `KnowledgeMaterialized` | `MemoryProcessingCompletedHandler` | `SearchKnowledgeMaterializedHandler` | Memory materialize succeeds | Search document materialization |
| `KnowledgeConstructed` | Not published | None | N/A | Defined only |
| `ChunksGenerated` | Not published | None | N/A | Defined only |
| `SearchIndexed` | `SearchKnowledgeMaterializedHandler` | `SearchIndexedEmbeddingHandler` | Search doc materialized | Embedding generation |
| `SearchDocumentRegistered` | Not published | None | N/A | Defined only |
| `EmbeddingGenerated` | `GenerateEmbedding` | None | Embedding created | Terminal event |
| `UserRegistered` | Not published | None | N/A | Defined only |
| `UserLoggedIn` | Not published | None | N/A | Defined only |

## Event graph (active path)

```text
Document upload
  → IngestLocalDocument
  → enqueue ProcessingJob
  → DocumentProcessingWorker
  → ProcessDocument
      → ProcessingStarted (no subscribers)
      → ProcessingCompleted
            ↓
      MemoryProcessingCompletedHandler
        → MaterializeKnowledge (chunks + knowledge item)
        → KnowledgeMaterialized
              ↓
        SearchKnowledgeMaterializedHandler
          → MaterializeSearchDocument
          → SearchIndexed
                ↓
          SearchIndexedEmbeddingHandler
            → GenerateEmbedding (FakeEmbeddingProvider in composition)
            → EmbeddingGenerated (no subscribers)
```

Intelligence does not participate in this event graph.

---

# 4 REST API

Registered in `apps/api/src/api/routers.py`: auth, documents, conversations (intelligence), search, health.

## Auth

| Method | Route | Request | Response | Service |
|--------|-------|---------|----------|---------|
| POST | `/auth/register` | `AuthCredentialsRequest` | `UserResponse` (201) | `RegisterUser` |
| POST | `/auth/login` | `AuthCredentialsRequest` | `UserResponse` | `LoginUser` |
| POST | `/auth/logout` | session cookie | 204 | `LogoutUser` |
| GET | `/auth/me` | session cookie | `UserResponse` | `GetCurrentUser` |

## Documents

| Method | Route | Request | Response | Service |
|--------|-------|---------|----------|---------|
| POST | `/documents` | multipart `file` | `IngestDocumentResponse` (202) | `IngestLocalDocument` |

## Search

| Method | Route | Request | Response | Service |
|--------|-------|---------|----------|---------|
| GET | `/search` | `q`, `mode`, filters, `limit`, `offset` | `SearchResponse` | `RetrieveKnowledge` |
| GET | `/search/semantic` | `q`, `limit` | `SearchResponse` (deprecated) | `SemanticSearch` |

## Conversations (Intelligence)

| Method | Route | Request | Response | Service |
|--------|-------|---------|----------|---------|
| POST | `/conversations` | none | `CreateConversationResponse` (201) | `ConversationService.create_conversation` |
| GET | `/conversations/{conversation_id}` | path | `ConversationMetadataResponse` | `ConversationService.get_conversation` |
| GET | `/conversations/{conversation_id}/messages` | path | `ConversationMessagesResponse` | `ConversationService.get_conversation` |
| POST | `/conversations/{conversation_id}/messages` | `SendMessageRequest` | `SendMessageResponse` | `SendConversationMessage` |

## Health

| Method | Route | Request | Response | Service |
|--------|-------|---------|----------|---------|
| GET | `/health` | none | `{"status":"healthy"}` | inline handler |

## Not exposed

* Memory `/memory` router — no endpoints; not registered
* Documents get/list queries — exist as application queries, no routes
* Streaming and WebSocket endpoints — do not exist

---

# 5 Database

## Tables

### `auth_users`

* Purpose: registered users
* Important columns: `id`, `email` (unique), `password_hash`, `created_at`
* Relationships: one-to-many `auth_sessions`

### `auth_sessions`

* Purpose: session tokens
* Important columns: `id`, `user_id` FK, `token_hash` (unique), `created_at`, `expires_at`, `revoked_at`
* Relationships: many-to-one `auth_users`

### `documents_documents`

* Purpose: document metadata
* Important columns: `id`, `name`, `mime_type`, `source_type`, `created_at`
* Relationships: versions, processing jobs

### `documents_document_versions`

* Purpose: immutable document versions + normalized text
* Important columns: `id`, `document_id` FK, `version_number`, `storage_key`, `normalized_content`, `created_at`
* Relationships: parent document

### `documents_processing_jobs`

* Purpose: processing lifecycle
* Important columns: `id`, `document_id` FK, `document_version_id` FK, `status`, `failure_reason`, `created_at`, `updated_at`
* Relationships: parent document

### `memory_knowledge_items`

* Purpose: durable knowledge item per document version
* Important columns: `id`, `document_id`, `document_version_id`, `source_type`, `mime_type`, `created_at`, `updated_at`
* Unique: (`document_id`, `document_version_id`)
* Relationships: logical to chunks via `knowledge_item_id` (no ORM relationship)

### `memory_chunks`

* Purpose: text chunks
* Important columns: `id`, `knowledge_item_id`, `document_id`, `document_version_id`, `chunk_index`, `text`, `created_at`
* Unique: (`document_id`, `document_version_id`, `chunk_index`)
* No FK constraints to knowledge/documents tables

### `search_documents`

* Purpose: searchable projection of knowledge
* Important columns: `id`, `knowledge_item_id` (unique), `document_id`, `document_version_id`, `source_type`, `mime_type`, `searchable_text`, `search_vector` (tsvector), timestamps
* Indexes: metadata indexes + GIN on `search_vector`

### `search_embeddings`

* Purpose: vector embeddings for semantic search
* Important columns: `id`, `search_document_id` FK, `provider`, `model`, `dimensions`, `vector`
* Unique: (`search_document_id`, `provider`, `model`)
* Vector type: `Vector(4)` (`EMBEDDING_VECTOR_DIMENSIONS = 4`)
* Index: HNSW cosine (`ix_search_embeddings_vector_hnsw`, `vector_cosine_ops`)

## Intelligence persistence

Does not exist in SQL. Conversations use `InMemoryConversationRepository` (process-local dict).

## Migrations

Alembic `script_location = database/migrations`.

| Revision | Purpose |
|----------|---------|
| `20260629_0001` | Auth tables |
| `20260701_0002` | Documents tables |
| `20260706_0003` | `normalized_content` |
| `20260713_0004` | Memory + search tables |
| `20260713_0005` | Full-text `search_vector` + GIN |
| `20260715_0006` | Search metadata filter columns |
| `20260717_0007` | Enable pgvector; retype embeddings; HNSW index |

`database/migrations/env.py` registers auth, documents, memory, and search metadata.

## pgvector

* Extension created in migration `0007`
* Compose/CI image: `pgvector/pgvector:pg18`
* Similarity via `cosine_distance` in `SqlAlchemyEmbeddingRepository.similarity_search` (PostgreSQL)
* Current embedding dimension constant is **4** (compatible with `FakeEmbeddingProvider`)

---

# 6 Search Architecture

## RetrievalEngine

File: `packages/search/src/memovi_search/application/services/retrieval_engine.py`

* Modes: `keyword`, `semantic`, `hybrid` (`RetrievalMode`)
* Request: query, mode, limit, offset, filters
* Default API mode for `RetrieveKnowledge`: **hybrid**

Pipeline order:

1. Normalize query; empty/non-positive limit → `[]`
2. Candidate limit = `min(100, max(limit + offset, 50))`
3. Run selected retriever(s)
4. `RankFusion.fuse` (RRF when ≥2 non-empty lists)
5. Apply metadata filters
6. `ScoreNormalizer.normalize` (min-max to `[0,1]`)
7. Slice for limit/offset

## KeywordRetriever

* Uses `SearchRepository.search`
* PostgreSQL full-text (`ts_rank` / `search_vector`)

## SemanticRetriever

* Embeds query via `EmbeddingProvider`
* `EmbeddingRepository.similarity_search` (pgvector cosine distance)

## Hybrid retrieval

* Runs keyword + semantic
* Fuses with Reciprocal Rank Fusion (`RankFusion`, `DEFAULT_RRF_K = 60`, score `1/(k+rank)`)

## Ranking

* `RankFusion` — RRF fusion
* `ScoreNormalizer` — post-fusion min-max normalization
* No learned reranker exists

## Query pipeline (HTTP)

`GET /search` → `RetrieveKnowledge` → `RetrievalEngine.retrieve` → `SearchResponse`

Composition (`apps/api/src/api/search_integration.py`) wires Keyword + Semantic + RankFusion + ScoreNormalizer. Embedding provider in event/API composition defaults to `FakeEmbeddingProvider`.

---

# 7 Intelligence

## ConversationService

Creates conversations; appends user/assistant turns; loads history; gets conversation. Depends on `ConversationRepository`.

## Reason command

Orchestrates:

1. Retrieval (`KnowledgeRetriever`)
2. Context assembly (`ContextAssembler`)
3. Prompt build (`PromptBuilder`)
4. Provider resolution (`ModelGateway.resolve_provider`)
5. Model execution (`ModelGateway.execute`)
6. Attach `ExecutionTrace` + metrics → `ReasoningResult`

## PromptBuilder

Builds deterministic provider-agnostic `Prompt` with ordered sections: system instructions, user request, optional conversation history, retrieved knowledge, citations, metadata.

## ContextAssembler

Orders/deduplicates retrieved knowledge; enforces max documents/chunks/tokens; optionally attaches trimmed conversation history under turn/token budgets.

## ModelGateway

Single prompt-execution entry point. Selects configured provider from injected registry. Owns execution metadata (`provider`, `model`, duration, estimated tokens).

## ReasoningProvider

Port: `reason(prompt) -> ReasoningResult`.

Implemented:

* `FakeReasoningProvider`
* `OpenAIReasoningProvider`

Placeholder:

* `PlaceholderReasoningProvider` (`NotImplementedError`)

Factory: `build_model_gateway` registers `fake`; registers `openai` when `OPENAI_API_KEY` is set.

## ExecutionTrace

Immutable stage timings + aggregate `ExecutionMetrics`. Stages: `retrieval`, `context_assembly`, `prompt_build`, `provider_resolution`, `model_execution`. Built by `ExecutionTracer` inside `Reason`.

## Tool Framework

* `Tool` port
* `ToolRegistry` — register/discover
* `ToolExecutor` — validate args, execute, timeouts
* `EchoTool` — demo/test tool

**Not invoked by `Reason` or Conversation API.** Used in unit tests and `scripts/verify_echo_tool.py` only.

## Conversation Memory

* Domain: `Conversation`, `ConversationTurn`, `ConversationHistory`
* Application: `ConversationService`, `SendConversationMessage`
* Infra: `InMemoryConversationRepository` only
* History is passed into `Reason` **before** the new user turn is appended (current request stays in `ReasoningRequest.query` / prompt `user_request`, not in history)

## Interaction (Conversation API path)

```text
POST /conversations/{id}/messages
  → SendConversationMessage
      → ConversationService.load_history
      → Reason.execute(query, conversation_history)
          → KnowledgeRetriever (SearchKnowledgeRetriever → RetrieveKnowledge)
          → ContextAssembler
          → PromptBuilder
          → ModelGateway → ReasoningProvider
          → ReasoningResult + ExecutionTrace
      → append user turn
      → append assistant turn (+ citations)
  → SendMessageResponse
```

Search is connected through the composition-root `SearchKnowledgeRetriever` adapter.

---

# 8 Dependency Graph

## Declared package dependencies (`pyproject.toml`)

```text
memovi-api
  ├── memovi-auth
  ├── memovi-documents
  ├── memovi-intelligence
  ├── memovi-memory
  ├── memovi-search
  ├── fastapi, sqlalchemy, psycopg, python-multipart

memovi-auth          → argon2-cffi, fastapi, sqlalchemy
memovi-documents     → boto3, fastapi, pypdf, python-multipart, sqlalchemy
memovi-memory        → fastapi, sqlalchemy
memovi-search        → fastapi, pgvector, sqlalchemy
memovi-intelligence  → fastapi, openai

memovi-config / connectors / contracts / observability / shared
  → (no dependencies; scaffolds)
```

## Runtime import graph

```text
Domain packages (src/) ──X──► do not import each other

apps/api
  ├── auth
  ├── documents
  ├── memovi_memory     (via memory_integration)
  ├── memovi_search     (via search_integration)
  └── memovi_intelligence (router only; isolated defaults)
```

## Domain dependency rules (enforced by structure)

* Domain packages must not import other domain packages.
* Cross-domain collaboration happens in `apps/api` via:
  * event subscriptions
  * adapter implementations of ports (`ProcessedDocumentReader`, `KnowledgeReader`)
* Intelligence must not own durable knowledge.
* Search/Memory/Documents remain usable without Intelligence.

---

# 9 Current Interfaces

All major contracts are `typing.Protocol` (no ABC hierarchy found for these).

## Auth

* `UserRepository`, `SessionRepository`
* `PasswordHasher`, `SessionTokenService`

## Documents

* `DocumentRepository`, `ProcessingJobRepository`
* `ProcessingJobQueue`, `ObjectStorage`
* `DocumentProcessor`, `ProcessorRegistry`
* `EventPublisher`

## Memory

* `KnowledgeRepository`, `ChunkRepository`
* `ProcessedDocumentReader`
* `EventPublisher`

## Search

* `SearchRepository`, `EmbeddingRepository`
* `KnowledgeReader`
* `EmbeddingProvider` (`@runtime_checkable`)
* `Retriever`
* `EventPublisher`

## Intelligence

* `KnowledgeRetriever`
* `ReasoningProvider`
* `ConversationRepository`
* `Tool`

## Factories / strategies

* `build_model_gateway` (intelligence providers)
* `build_embedding_provider` / `EmbeddingProviderKind` (search; real remote providers not implemented)
* `DefaultProcessorRegistry` (documents)
* `RetrievalMode` selection inside `RetrievalEngine`
* `RankFusion`, `ScoreNormalizer` (ranking strategies)

---

# 10 Configuration

## Environment variables

From `.env.example` and code readers:

| Variable | Purpose |
|----------|---------|
| `POSTGRES_DB/USER/PASSWORD/HOST/PORT` | Postgres / DATABASE_URL construction |
| `DATABASE_URL` | SQLAlchemy/Alembic (optional override) |
| `REDIS_PASSWORD`, `REDIS_PORT` | Compose Redis service only |
| `MINIO_*` | Object storage credentials/endpoints/bucket |
| `INTELLIGENCE_PROVIDER` | `fake` \| `openai` |
| `INTELLIGENCE_MODEL` | optional model override |
| `OPENAI_API_KEY` | OpenAI reasoning provider |
| `OPENAI_MODEL` | OpenAI model (also used when intelligence model unset) |

## Docker / Compose

`compose.yml` services:

* `postgres` — `pgvector/pgvector:pg18`
* `redis` — `redis:8`
* `minio`

No API or web service is defined in Compose.

## Settings classes

* `IntelligenceConfig` — real typed config + `from_env()`
* `OpenAIProviderSettings` — OpenAI client settings
* `EmbeddingProviderConfig` — kind selection helper (not env-loaded end-to-end)
* `DocumentProcessingWorkerConfig` — worker tuning
* `memovi_config` package — empty; not wired
* `apps/api` `validate_configuration()` — no-op

## Feature flags

Do not exist. No `FEATURE_*` flags or feature-flag framework found.

---

# 11 Testing

## Counts

**310 tests collected** (pytest).

| Area | Count |
|------|------:|
| `packages/intelligence` | 117 |
| `packages/search` | 96 |
| `packages/memory` | 47 |
| `packages/documents` | 26 |
| `apps/api` | 16 |
| `packages/auth` | 8 |

Scaffold packages have no meaningful test suites beyond empty/test placeholders if present.

## Major suites

* Auth: application + API flows
* Documents: ingest, processors, process command, background worker
* Memory: chunking, materializer, repositories, queries, DTOs
* Search: retrieval engine, keyword/semantic, RRF, APIs, materialize, embeddings, handlers
* Intelligence: domain VOs/entities, Reason, context/prompt, gateway, providers, conversation memory, Conversation API/acceptance, tools, execution traces
* API integration: knowledge materialization → search indexing → embeddings; search filter/FTS/semantic/hybrid paths

## Testing philosophy (observed)

* Domain/application unit tests with fakes/stubs
* No real OpenAI calls in unit tests (`FakeReasoningProvider`, `FakeEmbeddingProvider`)
* Some search/API tests require PostgreSQL/pgvector
* FastAPI `TestClient` for HTTP contract tests
* Architecture tests for package boundaries: **do not exist**

## Missing coverage (factual gaps)

* Ownership enforcement on knowledge APIs (feature absent)
* Search-backed Intelligence retrieval (feature absent)
* Durable conversation persistence (feature absent)
* Tool framework integration into Reason path (feature absent)
* Real embedding providers (stubs raise `NotImplementedError`)
* Memory HTTP API (no routes)
* Frontend/product UI (shell only)
* Architecture boundary tests
* Observability/metrics tests (package empty)

---

# 12 Outstanding TODOs

Repository search for `TODO`, `FIXME`, `HACK`, `XXX` in code/docs:

**No matches found.**

Only related note found:

* `apps/web/next-env.d.ts` — generated Next.js note: file should not be edited

There is no centralized TODO ledger in code comments.

Outstanding work is tracked narratively in `STATUS.md`, not via in-code TODO markers.

---

# 13 Roadmap Progress

Compared against `ROADMAP.md` milestones (capability phases), using repository facts and `STATUS.md` as implementation evidence.

| Milestone | Status | Evidence |
|-----------|--------|----------|
| 0 Foundation | **Complete** | Workspaces, Compose, CI, tooling, docs present |
| 1 Platform | **In Progress** | Composition root/routers/health done; typed config, observability, architecture tests incomplete |
| 2 Identity & Ownership | **In Progress** | Auth complete; ownership on knowledge APIs and audit logging absent |
| 3 Knowledge Ingestion | **In Progress** | Upload, MinIO, worker, processing, chunk handoff done; OCR and connector intake absent |
| 4 Knowledge Platform | **In Progress** | Memory materialization exists; collections/tags/relationships/public Memory API absent |
| 5 Retrieval Intelligence | **In Progress** | Keyword/semantic/hybrid/filters/APIs done; query planning, cache/summary lookup, learned rerank absent |
| 6 Reasoning Engine | **In Progress** | Reason pipeline, Conversation API, traces, fake/openai providers done; Search wiring, durable chats, chat UI, summaries absent |
| 7 Memory Intelligence | **Not Started** | Hierarchical summaries/caching/embedding lifecycle policies not implemented as a milestone slice |
| 8 Connector Ecosystem | **Not Started** | Connectors package is empty scaffold |
| 9 Platform Maturity | **Not Started** | Advanced observability/distributed workers/backup maturity not implemented |
| 10 Applications | **Not Started** | `apps/web` is a placeholder shell; no product clients |

---

# 14 Technical Debt

## Known compromises

* Conversations are process-local (`InMemoryConversationRepository`)
* Embedding dimension hard-coded to **4** for fake/local vector path
* Production embedding providers are stubs (`NotImplementedError`)
* Document processing queue is in-memory (lost on process restart)
* Event bus is in-process only
* Auth events defined but unused
* Several domain events defined but never published
* Documents twin empty package tree `memovi_documents/`
* Middleware registration is a no-op
* Configuration validation is a no-op

## Temporary implementations

* `FakeEmbeddingProvider` in API composition for search events/retrieval wiring
* `FakeKnowledgeRetriever` / `FakeReasoningProvider` for isolated intelligence tests
* `NoOpEventPublisher` / collecting publishers in documents package tests
* Placeholder reasoning/knowledge retrievers that raise `NotImplementedError`

## Planned / implied refactors (from docs/status, not unfinished code branches)

* Durable conversation repository
* Ownership context on knowledge APIs
* Typed `memovi_config` and observability package fill-in
* Memory HTTP surface
* Real embedding providers
* Tool loop integration into Reason (framework exists; path does not)

## Missing production features

* OCR
* Connector sync
* Chat UI / streaming / WebSockets
* AI summaries
* Collections/tags/knowledge graph
* Audit logging
* Architecture tests
* Redis-backed queues (Redis runs in Compose unused by app code found)

---

# 15 Architectural Constraints

Enforced by package layout, ports, and composition practices:

1. **Inward dependency direction** — domain does not import infrastructure frameworks for business meaning; infrastructure implements ports.
2. **No cross-domain package imports** — domains collaborate through `apps/api` and events/adapters.
3. **AI does not own knowledge** — Intelligence consumes retrieved knowledge; Memory/Search/Documents persist knowledge.
4. **Provider independence** — reasoning and embeddings go through ports/gateways; OpenAI is an adapter.
5. **Immutable reasoning/conversation value objects** — frozen dataclasses with invariant checks (`ReasoningResult`, `Conversation`, traces, prompts, etc.).
6. **Event-driven fan-out for knowledge pipeline** — processing → memory → search → embeddings.
7. **Async heavy work off request path** — document processing via queue/worker after ingest returns 202.
8. **Thin API routers** — routes map to application commands/services; business rules stay below transport.
9. **Separate persistence metadata per domain** — distinct SQLAlchemy `Base`/tables per domain; Alembic aggregates them.
10. **Search projections are derived** — `search_documents` / embeddings are materializations, not source of truth for raw uploads.
11. **Tools are first-class but optional** — tool ports exist without coupling Reason to tools yet.
12. **Local-first auth** — session cookies + Argon2; no JWT/OAuth in foundation.

---

# 16 Implementation Summary

## Current State of Memovi

Memovi is a modular-monolith Python/FastAPI knowledge platform with a Next.js frontend shell.

Implemented vertical slices:

1. **Local auth** — register/login/logout/me with SQLAlchemy sessions and Argon2id.
2. **Document ingestion** — multipart upload to MinIO, in-memory processing queue, background worker, PDF/Markdown/text processing, normalized content.
3. **Memory materialization** — on `ProcessingCompleted`, create knowledge items and chunks.
4. **Search indexing and retrieval** — search documents, PostgreSQL FTS, pgvector embeddings (dim 4 + fake provider in composition), hybrid RRF retrieval API.
5. **Intelligence foundation** — Reason pipeline, conversation memory, Conversation REST API, execution traces, fake/OpenAI providers, tool framework (unused by Reason).

Composition root (`apps/api`) owns cross-domain event wiring and adapters. Domain packages do not import each other.

Not implemented:

* Ownership enforcement on knowledge APIs
* Search-backed conversation retrieval
* Durable conversations
* Connectors, OCR, collections/tags
* Product chat UI / streaming
* Typed shared config and observability packages
* Real embedding provider integrations
* Architecture boundary tests

The knowledge pipeline from upload through hybrid search is operational for local development. The reasoning/conversation path is operational against fake retrieval and in-memory conversation state, and is not yet closed-loop with Search.
