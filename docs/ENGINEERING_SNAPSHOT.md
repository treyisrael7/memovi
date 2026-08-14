# Memovi Engineering Snapshot

Handoff document for a principal engineer or AI assistant.
Generated from repository inspection. No speculative claims.
If something is not present in the repository, it is stated as absent.

Companion documents:

* [`ROADMAP.md`](ROADMAP.md) / [`ROADMAP_V2.md`](ROADMAP_V2.md) — direction
* [`STATUS.md`](STATUS.md) — living implementation tracker
* [`ARCHITECTURE.md`](ARCHITECTURE.md) — architecture blueprint
* [`PRODUCT_VISION.md`](PRODUCT_VISION.md) — product vision

---

# 1 Repository Overview

## Directory tree (collapsed)

```text
memovi/
├── .cursor/
├── .devcontainer/
├── .github/workflows/
├── apps/
│   ├── api/                 # FastAPI composition root (platform API)
│   ├── desktop/             # Flagship Tauri desktop client
│   └── web/                 # Optional web client shell (not primary product)
├── packages/
│   ├── auth/                # memovi-auth
│   ├── automation/          # memovi-automation
│   ├── config/              # memovi-config
│   ├── connectors/          # memovi-connectors
│   ├── documents/           # memovi-documents
│   ├── intelligence/        # memovi-intelligence
│   ├── memory/              # memovi-memory
│   ├── observability/       # memovi-observability
│   ├── search/              # memovi-search
│   ├── shared/              # memovi-shared
│   └── workspace/           # memovi-workspace
├── database/
│   └── migrations/versions/ # Alembic revisions
├── docker/                  # .gitkeep only
├── docs/
│   ├── PRODUCT_VISION.md
│   ├── ARCHITECTURE.md
│   ├── ROADMAP.md
│   ├── ROADMAP_V2.md
│   ├── STATUS.md
│   ├── PHILOSOPHY.md
│   ├── ENGINEERING_SNAPSHOT.md
│   ├── README.md
│   ├── architecture/
│   └── development/
├── scripts/
├── tests/                   # Reserved placeholders for future cross-package tests
├── README.md
├── LICENSE
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
| memory | `memovi-memory` | `memovi_memory` | Implemented |
| search | `memovi-search` | `memovi_search` | Implemented |
| intelligence | `memovi-intelligence` | `memovi_intelligence` | Implemented |
| automation | `memovi-automation` | `memovi_automation` | Implemented |
| workspace | `memovi-workspace` | `memovi_workspace` | Implemented |
| config | `memovi-config` | `memovi_config` | Typed settings + startup validation |
| connectors | `memovi-connectors` | `memovi_connectors` | Filesystem connector + framework |
| observability | `memovi-observability` | `memovi_observability` | RequestContext, structured logs, metrics, diagnostic events, OTel spans |
| shared | `memovi-shared` | `memovi_shared` | `WorkspaceId`, workspace header parsing, FastAPI workspace dependency |

## Apps

| App | Role |
|-----|------|
| `apps/api` | Backend composition root / platform API. Registers routers, DB sessions, document processing worker, in-process event bus, memory/search/intelligence integration adapters. |
| `apps/desktop` | Flagship Tauri + React desktop client. Consumes the platform API; does not own business logic. |
| `apps/web` | Optional web client workspace shell. |

## Shared libraries

* `packages/shared` — `WorkspaceId`, workspace header constants, parsing helpers, and package-default FastAPI workspace dependency
* `packages/config` — typed settings, env parsing, secrets, startup validation
  (auth session cookie/TTL via `AuthSettings`)
* `packages/models` and `packages/contracts` — removed in Milestone 46
* `packages/observability` — RequestContext, structured JSON logging, MetricsRecorder, diagnostic emitter, OTel-API tracing

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
* API schemas: knowledge explorer responses (`KnowledgeSummaryResponse`, `KnowledgeDetailResponse`, `ChunkResponse`, etc.)

### API routers

`/memory` — knowledge explorer list, detail, concepts, relationships, dashboard

### Dependencies on other domains

None in package source. `ProcessedDocumentReader` is implemented in `apps/api` over documents repositories.

---

## Search (`packages/search`)

### Responsibilities

Search document projections, full-text search, embeddings, keyword/semantic/hybrid retrieval via `RetrievalEngine`, metadata filtering, event-driven indexing from Memory.

### Public interfaces

* HTTP router: `memovi_search.api.router` (`prefix="/search"`)
* Queries: `RetrieveKnowledge`, `SearchKnowledge`

### Commands

* `MaterializeSearchDocument` / `MaterializeSearchDocumentCommand` / `MaterializeSearchDocumentResult`
* `GenerateEmbedding` / `GenerateEmbeddingCommand` / `GenerateEmbeddingResult`

### Queries

* `RetrieveKnowledge` / `RetrieveKnowledgeQuery`
* `SearchKnowledge` / `SearchKnowledgeQuery`

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
* Providers: `FakeEmbeddingProvider` (explicit local/tests), `OpenAIEmbeddingProvider`,
  `OllamaEmbeddingProvider`, `SentenceTransformerEmbeddingProvider` (config-selected in composition)

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
* Infra: `InMemoryConversationRepository`, `SqlAlchemyConversationRepository`
* Retrieval: `FakeKnowledgeRetriever`
* Providers: `FakeReasoningProvider`, `OpenAIReasoningProvider`, `build_model_gateway`
* Config: `IntelligenceConfig`, `ReasoningProviderKind`

### Domain events

None. Intelligence does not ship a package-level `events/` module.

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

None in package source. Package defaults use `FakeKnowledgeRetriever` and `InMemoryConversationRepository` for isolated tests. `apps/api` overrides `KnowledgeRetriever` with `SearchKnowledgeRetriever` and `ConversationRepository` with `SqlAlchemyConversationRepository`.

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

There is no out-of-process message bus. Redis is not used in V1; distributed queues or Redis Streams remain future architectural options.

## Every domain event

| Event | Publisher | Subscribers | Trigger | Resulting actions |
|-------|-----------|-------------|---------|-------------------|
| `DocumentCreated` | Returned by `CreateDocument` / `IngestLocalDocument` | None on bus | Document create/ingest | Returned to caller only; not bus-published |
| `ProcessingStarted` | `ProcessDocument` publishes; `StartProcessing` returns | None on bus | Processing starts | Status transition |
| `ProcessingCompleted` | `ProcessDocument` / worker via publisher; `CompleteProcessing` returns | `MemoryProcessingCompletedHandler` | Successful processing | Memory materialization |
| `ProcessingFailed` | `ProcessDocument` / worker; `FailProcessing` returns | None on bus | Processing failure | Job marked failed |
| `KnowledgeMaterialized` | `MemoryProcessingCompletedHandler` | `SearchKnowledgeMaterializedHandler` | Memory materialize succeeds | Search document materialization |
| `SearchIndexed` | `SearchKnowledgeMaterializedHandler` | `SearchIndexedEmbeddingHandler` | Search doc materialized | Embedding generation |
| `SearchDocumentRegistered` | Not published | None | N/A | Defined only |
| `EmbeddingGenerated` | `GenerateEmbedding` | None | Embedding created | Terminal event |

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
            → GenerateEmbedding (configured EmbeddingProvider)
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
| GET | `/health` | none | `{"status":"healthy"}` | liveness |
| GET | `/ready` | none | component readiness aggregate | database, vector_search, embedding_provider, migrations, workspace, search_readiness |

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

| Table | Purpose |
|-------|---------|
| `intelligence_conversations` | Conversation id + created/updated timestamps |
| `intelligence_conversation_turns` | Ordered turns with role, content, citations JSON |

Package default remains `InMemoryConversationRepository` for tests. `apps/api` wires `SqlAlchemyConversationRepository`.

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
| `20260717_0008` | Intelligence conversation tables |

`database/migrations/env.py` registers auth, documents, intelligence, memory, and search metadata.

## pgvector

* Extension created in migration `0007`
* Compose/CI image: `pgvector/pgvector:pg18`
* Similarity via `cosine_distance` in `SqlAlchemyEmbeddingRepository.similarity_search` (PostgreSQL)
* Current embedding dimension constant is **384** (pgvector schema; providers must match)

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

Composition (`apps/api`) wires Keyword + Semantic + RankFusion + ScoreNormalizer.
Embedding provider selection uses `SearchEmbeddingConfig` / `build_embedding_provider`
(Fake only when `SEARCH_EMBEDDING_PROVIDER=fake`).

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

Factory: `build_model_gateway` registers `fake`; registers `openai` when `OPENAI_API_KEY` is set.

## ExecutionTrace

Immutable stage timings + aggregate `ExecutionMetrics`. Stages: `retrieval`, `context_assembly`, `prompt_build`, `provider_resolution`, `model_execution`. Built by `ExecutionTracer` inside `Reason`.

## Tool Framework

* `Tool` port
* `ToolRegistry` — register/discover
* `ToolExecutor` — validate args, execute, timeouts

**Frozen / not product-supported.** Not invoked by `Reason` or the Conversation API.
Covered by unit tests only (`packages/intelligence/tests/test_tool_framework.py`).
Host actions use the Automation Capability Framework instead.

## Conversation Memory

* Domain: `Conversation`, `ConversationTurn`, `ConversationHistory`
* Application: `ConversationService`, `SendConversationMessage`
* Infra: `InMemoryConversationRepository` (tests); `SqlAlchemyConversationRepository` (composition root)
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

memovi-config / connectors / contracts
  → (scaffolds)
memovi-observability → memovi-shared, opentelemetry-api
memovi-shared → (primitives)
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
| `MINIO_*` | Object storage credentials/endpoints/bucket |
| `INTELLIGENCE_PROVIDER` | `fake` \| `openai` |
| `INTELLIGENCE_MODEL` | optional model override |
| `OPENAI_API_KEY` | OpenAI reasoning provider |
| `OPENAI_MODEL` | OpenAI model (also used when intelligence model unset) |

## Docker / Compose

`compose.yml` services:

* `postgres` — `pgvector/pgvector:pg18`
* `minio`

No API or web service is defined in Compose.

## Settings classes

* `memovi_config.Settings` — authoritative aggregate; `load_settings()` / `validate_configuration()`
* Domain settings: `ApiSettings`, `DatabaseSettings`, `AuthSettings`, `SearchSettings`,
  `EmbeddingsSettings`, `ModelsSettings`, `StorageSettings`, `CapabilitiesSettings`,
  `ConnectorsSettings`, `ObservabilitySettings`, `DesktopSettings`
* `IntelligenceConfig` / `SearchEmbeddingConfig` — domain DTOs that load via `memovi_config`
* `OpenAIProviderSettings` — OpenAI client settings
* `EmbeddingProviderConfig` — kind selection helper for provider factory
* `DocumentProcessingWorkerConfig` — worker tuning
* `apps/api` `validate_configuration()` — delegates to `memovi_config.validate_configuration()`

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
* Tool framework integration into Reason path (feature absent)
* Real embedding providers wired through configuration (`openai`, `ollama`, `sentence_transformer`)
* Memory HTTP API (no routes)
* Desktop client / optional web product UI (web shell only today)
* Architecture boundary tests
* Observability/metrics tests (package empty)

---

# 12 Outstanding TODOs

Repository search for `TODO`, `FIXME`, `HACK`, `XXX` in code/docs:

**No matches found.**

Only related note found:

* `apps/web/next-env.d.ts` — generated Next.js note: file should not be edited

There is no centralized TODO ledger in code comments.

Outstanding work is tracked narratively in [`STATUS.md`](STATUS.md), not via in-code TODO markers.

---

# 13 Roadmap Progress

Compared against [`ROADMAP.md`](ROADMAP.md) / [`ROADMAP_V2.md`](ROADMAP_V2.md), using repository facts and [`STATUS.md`](STATUS.md).

## Platform foundation (Milestones 0–6)

| Milestone | Status | Evidence |
|-----------|--------|----------|
| 0 Foundation | **Complete** | Workspaces, Compose, CI, tooling, docs present |
| 1 Platform | **In Progress** | Composition root/routers/observability/typed config done; architecture tests incomplete |
| 2 Identity & Ownership | **In Progress** | Auth complete; ownership on knowledge APIs and audit logging absent |
| 3 Knowledge Ingestion | **In Progress** | Upload, MinIO, worker, processing, chunk handoff done; OCR and connector intake absent |
| 4 Knowledge Platform | **In Progress** | Memory materialization exists; collections/tags/relationships/public Memory API absent |
| 5 Retrieval Intelligence | **In Progress** | Keyword/semantic/hybrid/filters/APIs done; query planning, cache/summary lookup, learned rerank absent |
| 6 Reasoning Engine | **In Progress** | Reason pipeline, Conversation API, Search wiring, durable chats done; desktop UX deferred to Phase 2 |

## Forward roadmap (Phases 1–6)

| Phase | Status | Evidence |
|-------|--------|----------|
| 1 Complete V1 Platform | **In Progress** | Core pipeline + ownership + observability foundation exist; hardening and API stability remain |
| 2 Desktop Client | **In Progress** | Tauri shell foundation in `apps/desktop`; product pages not built yet |
| 3 Capability Framework | **In Progress** | Framework + read-only FilesystemCapability; terminal/git/plugins/approval UX remain |
| Model Provider Framework (M17) | **Removed (M46)** | Unused `packages/models` deleted; live path is Intelligence `ModelGateway` |
| 4 Automation | **Not Started** | No approval workflow or capability orchestration product path |
| 5 Knowledge Evolution | **Not Started** | Summaries, long-term memory, graph, reasoning cache absent |
| 6 Ecosystem | **Not Started** | Optional web/mobile, cloud sync, enterprise, connector marketplace absent |

---

# 14 Technical Debt

## Known compromises

* Embedding dimension hard-coded to **4** for fake/local vector path
* Production embedding providers are config-selected at the API composition root
* Document processing queue is durable in Postgres (`SqlAlchemyProcessingJobQueue`)
* Event bus is in-process only
* Auth domain-event package is reserved but publishes no event types yet
* Several domain events defined but never published

## Temporary implementations

* Explicit `FakeEmbeddingProvider` / `SEARCH_EMBEDDING_PROVIDER=fake` for local and tests
* `FakeKnowledgeRetriever` / `FakeReasoningProvider` for isolated intelligence tests
* `NoOpEventPublisher` / collecting publishers in documents package tests

## Planned / implied refactors (from docs/status, not unfinished code branches)

* Ownership context on knowledge APIs
* Architecture boundary tests
* Live smoke coverage against hosted OpenAI / Ollama outside default CI
* Optional post-V1 LLM tool-calling (frozen `ToolRegistry` / `ToolExecutor`; not on Reason path)

## Missing production features

* OCR
* Additional connector providers beyond filesystem
* Desktop realtime channels / streaming polish
* AI summaries
* Knowledge graph
* Architecture tests
* Redis-backed queues (Redis is not used in V1; distributed queues remain a future option)

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

Memovi is a desktop-first knowledge operating system built as a modular-monolith
Python/FastAPI backend platform. An optional web client shell exists; the
flagship desktop shell exists in `apps/desktop`; product pages are not built yet.

Implemented vertical slices:

1. **Local auth** — register/login/logout/me with SQLAlchemy sessions and Argon2id.
2. **Document ingestion** — multipart upload to MinIO, durable processing queue, background worker, PDF/Markdown/text processing, normalized content.
3. **Memory materialization** — on `ProcessingCompleted`, create knowledge items and chunks.
4. **Search indexing and retrieval** — search documents, PostgreSQL FTS, pgvector embeddings (dim 4 + fake provider in composition), hybrid RRF retrieval API.
5. **Intelligence foundation** — Reason pipeline, conversation memory, Conversation REST API, execution traces, fake/OpenAI providers, frozen ToolRegistry/ToolExecutor (not on Reason path).

Composition root (`apps/api`) owns cross-domain event wiring and adapters. Domain packages do not import each other. Clients attach at the API boundary.

Not implemented:

* OCR
* Additional connector providers beyond filesystem
* Knowledge graph
* Optional live embedding provider smoke jobs
* Architecture boundary tests

The knowledge pipeline from upload through hybrid search is operational for local development. Conversation reasoning is closed-loop with Search-backed retrieval and durable SQLAlchemy conversation persistence at the composition root. The flagship desktop shell in `apps/desktop` consumes that API.
