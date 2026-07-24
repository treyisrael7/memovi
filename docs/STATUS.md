# Memovi Status

Living implementation tracker for Memovi as a desktop-first knowledge operating
system on a reusable backend platform. Last reviewed: 2026-07-24 (Milestone 21).

* [`ROADMAP.md`](ROADMAP.md) / [`ROADMAP_V2.md`](ROADMAP_V2.md) describe where Memovi is going.
* [`STATUS.md`](STATUS.md) describes where Memovi is today.

---

# Milestone 0 — Foundation

**Overall Status:** Complete

Engineering foundation is in place: workspaces, local infrastructure, CI, tooling, and documentation.

**Completed**

* Repository and workspace layout
* Local Docker Compose infrastructure
* CI, quality tooling, pre-commit, and documentation

**In Progress**

* None

**Remaining**

* None for this milestone

**Known Risks**

* None material

**Next Recommended Work**

* Maintain foundation as later milestones add packages and ops surface

---

# Milestone 1 — Platform

**Overall Status:** In progress

Backend composition root is operational. Observability foundation (request context, structured logs, diagnostic bridge, metrics, readiness) is in place. Typed config and architecture boundary tests remain.

**Completed**

* FastAPI composition root and bootstrap
* Dependency injection and router registration
* Health liveness (`/health`) and readiness (`/ready`) endpoints
* Domain packages for auth, documents, search, and intelligence
* `memovi_observability` RequestContext, structured JSON logging, diagnostic event bridge, metrics recorder, and OpenTelemetry-API spans

**In Progress**

* Domain package scaffolding for remaining packages
* Environment-based configuration (typed `memovi_config` not yet wired)

**Remaining**

* Architecture tests validating package boundaries
* Typed configuration wiring

**Known Risks**

* Cross-cutting concerns may stay ad hoc without typed config

**Next Recommended Work**

* Wire typed configuration and add architecture boundary tests

---

# Milestone 2 — Identity & Ownership

**Overall Status:** In progress

Local authentication works. Workspace ownership is enforced on knowledge-sensitive paths. Auth session ↔ active workspace coupling and audit logging remain open.

**Completed**

* User registration
* Secure local login
* HTTP-only session cookies
* Session persistence and logout
* Current-user API boundary
* Workspace domain (`packages/workspace`) with Default Workspace seed
* `WorkspaceId` shared primitive and repository-level workspace isolation
* Optional `X-Memovi-Workspace-Id` API resolution with Default fallback

**In Progress**

* None

**Remaining**

* Bind active workspace to authenticated session (replace default header fallback)
* Audit logging for ownership-sensitive actions
* Workspace membership / roles

**Known Risks**

* Knowledge APIs remain unauthenticated; workspace header is an ownership boundary, not yet an authz model

**Next Recommended Work**

* Attach authenticated user context and membership checks to workspace-scoped APIs

---

# Milestone 3 — Knowledge Ingestion

**Overall Status:** In progress

Upload-to-processing pipeline is operational locally. OCR and richer connector intake remain open.

**Completed**

* Document uploads (`POST /documents`)
* MinIO-backed object storage
* Document processing engine for PDF, Markdown, and plain text
* Processing queue and background worker
* Chunk generation via Memory materialization on `ProcessingCompleted`
* Event-driven handoff into Memory

**In Progress**

* Local file intake (upload path exists; connector framework not built)
* Metadata extraction beyond ingest/process basics
* Document versioning (initial version on upload; no re-version workflow)

**Remaining**

* OCR pipeline

**Known Risks**

* Unsupported formats and OCR gaps limit ingestion coverage

**Next Recommended Work**

* Harden processing status visibility and expand supported ingest formats as needed

---

# Milestone 4 — Knowledge Platform

**Overall Status:** In progress

Memory materialization and chunk persistence work. Organization features and public Memory APIs remain.

**Completed**

* Memory domain core for chunk materialization and persistence from processing events

**In Progress**

* Memory domain ownership of knowledge items (HTTP `/memory` read surface exposed for explorer)
* Processing status as a knowledge concern (job statuses exist in documents; no public Memory status API)
* Knowledge independence from AI providers (memory/search do not depend on Intelligence; organization incomplete)

**Remaining**

* Collections
* Tags
* Version history
* Knowledge relationships beyond provenance edges
* Metadata management as a first-class platform concern

**Known Risks**

* Knowledge organization may lag behind ingestion and search capability

**Next Recommended Work**

* Add semantic entity/topic extraction while keeping explorer contracts stable

---

# Milestone 5 — Retrieval Intelligence

**Overall Status:** In progress

Keyword, semantic, and hybrid retrieval are operational. Query planning, caching, summaries, and deeper ranking remain.

**Completed**

* Full-text / keyword retrieval
* Vector / semantic retrieval (pgvector)
* Hybrid retrieval with Reciprocal Rank Fusion
* Metadata filtering
* Stable search APIs (`GET /search`)

**In Progress**

* Semantic ranking (score normalization + RRF; no learned reranker)

**Remaining**

* Query planning and context budgeting
* Cache and summary lookup paths

**Known Risks**

* Without planning/cache/summary paths, retrieval remains search-centric rather than cost-aware

**Next Recommended Work**

* Add query planning, context budgeting, and cheaper lookup paths before deeper ranking

---

# Milestone 6 — Reasoning Engine

**Overall Status:** In progress

Reasoning pipeline, conversation memory, Conversation REST API (including list,
rename, delete, and SSE streaming), and Search-backed retrieval for conversations
are operational. AI summaries remain.

**Completed**

* Reasoning pipeline (retrieve → assemble → prompt → provider)
* Conversation memory (`ConversationService`, history-aware context)
* Conversation REST API (create/list/get/rename/delete, list/send messages, SSE stream)
* Conversation titles and workspace-scoped listing
* Per-request provider/model selection on send/stream
* Execution traces and citations
* Provider gateway with `fake` and `openai` adapters (including token streaming)
* Search-backed knowledge retrieval (`SearchKnowledgeRetriever` in `apps/api`)
* Durable conversation storage (`SqlAlchemyConversationRepository` in `apps/api`)

**In Progress**

* Provider abstraction and routing (env-driven selection; broader providers reserved)
* Prompt construction (`PromptBuilder`; no prompt library/versioning product)
* Tool execution framework (`ToolRegistry` / `ToolExecutor` / `EchoTool`; not in conversation Reason path)
* Cost-aware model selection (basic provider/model config only)

**Remaining**

* AI summaries
* WebSocket/realtime channels beyond SSE (only if needed)

**Known Risks**

* Tool framework is not yet part of the conversation path

**Next Recommended Work**

* Close Phase 1 platform gaps (ownership, observability, API stability)
* Migrate Intelligence `ModelGateway` onto `packages/models` (`ModelRegistry` / `ModelProvider`)

---

# Milestone 17 — Model Provider Framework

**Overall Status:** Complete (architecture foundation)

**Completed**

* `packages/models` (`memovi-models`) Model Provider Framework
* Core contracts: `ModelProvider`, `ModelRegistry`, `ModelRequest`, `ModelResponse`, `ModelMetadata`, `ModelCapabilities`, `ProviderConfiguration`, `ProviderHealth`
* Normalized provider error codes (authentication, unavailable, rate_limit, timeout, unsupported_capability, invalid_configuration, …)
* `FakeModelProvider` for tests and local wiring (no production vendor SDKs)
* Architecture reference: `docs/architecture/MODEL_PROVIDER_FRAMEWORK.md`

**In Progress**

* None

**Remaining**

* Concrete adapters: OpenAI, Anthropic, Gemini, Ollama, OpenRouter, LM Studio
* Intelligence migration from in-package `ReasoningProvider` / `ModelGateway` onto `memovi-models`
* Optional Search embeddings convergence onto shared capability model
* Desktop provider settings UI (consumes configuration; not owned here)

**Known Risks**

* Until Intelligence migrates, vendor SDK dependencies remain in `memovi-intelligence`

**Next Recommended Work**

* Implement the first production adapter (OpenAI or Ollama) behind `ModelProvider`, then adapt Intelligence `ModelGateway` to resolve through `ModelRegistry`

---

# Milestone 19 — Conversation Experience

**Overall Status:** Complete

Desktop Chat is the first functional conversation surface. It consumes Conversation
and Intelligence APIs only; no domain logic lives in the client.

**Completed**

* Conversation list / create / rename / delete
* Conversation history persistence via backend APIs
* SSE token streaming with stop (AbortController) and clean error surfacing
* Markdown rendering, code blocks, copy message / copy code
* Enter to send, Shift+Enter newline, auto-scroll, retry failed responses
* Top-bar workspace and model selection reflected in stream requests
* Workspace switching reloads isolated conversation lists
* `docs/architecture/DESKTOP_CLIENT.md` conversation flow

**Remaining**

* Multi-chat tabs, prompt library, agents, voice, images, automation, plugins (explicitly out of scope)

---

# Milestone 20 — Knowledge Explorer

**Overall Status:** Complete

Desktop Knowledge Explorer is the first read-only inspection surface for answering
"What does Memovi know?" without asking the AI. It consumes Memory, Documents, and
Search APIs only; no knowledge business logic lives in the client.

**Completed**

* Memory HTTP read APIs (`/memory`, detail, dashboard, concepts, relationships)
* Documents list/get HTTP for Sources (`GET /documents`, `GET /documents/{id}`)
* Desktop Knowledge page with Overview, Search, Concepts, Entities, Relationships, Sources
* List + detail inspection with source links, related concepts/entities, confidence, timestamps
* Full-text search with immediate updates and workspace / document / entity-type filters
* Workspace isolation via `X-Memovi-Workspace-Id`
* `docs/architecture/KNOWLEDGE_EXPLORER.md`

**Remaining**

* Graph visualization, manual editing, merging, deleting, auto-corrections, version history (explicitly out of scope)
* Semantic entity/topic extraction and confidence scoring (future pipeline stages)

---

# Milestone 21 — Capability Execution Engine

**Overall Status:** Complete

Conversations and API clients invoke registered capabilities only through the
Capability Execution Engine. Intelligence never calls capabilities directly.

**Completed**

* `CapabilityExecutionEngine` with resolve → authorize → invoke → audit pipeline
* Execution types: request, context, result, status, audit entry; permission modes
  (`always_allow`, `ask_every_time`, `deny`)
* HTTP surface under `/capabilities` (list, submit, approve, cancel, audit, policy)
* Conversation bridge: `POST/GET /conversations/{id}/capability-executions`
* Composition-root registration of Filesystem capability + Intelligence port adapter
* Desktop Chat pending-approval / progress / result presentation
* `docs/architecture/CAPABILITY_EXECUTION.md`

**Remaining**

* Durable audit persistence, additional concrete capabilities, settings UI for policies

---

# Milestone 22 — Filesystem Write Capability

**Overall Status:** Complete

The Filesystem Capability is the trusted interface for creating, modifying,
moving, copying, renaming, and deleting files. The Capability Execution Engine
remains responsible for permission modes, approval, and audit.

**Completed**

* Write operations: create file/directory, replace, append, rename, copy, move, delete
* Overwrite policies: `reject` (default), `ask_user`, `replace` — never silent overwrite
* Deletion modes: `trash` (default when available) and explicit `permanent`
* Fine-grained permissions: `filesystem.create` / `modify` / `move` / `delete`
  plus coarse `filesystem.write` umbrella
* Structured success/error payloads; content redacted in audit arguments
* Desktop confirmation, progress, success/failure, overwrite Replace, and undo messaging
* `docs/architecture/FILESYSTEM_WRITE.md`

**Verified**

* Filesystem — existing read operations still function
* Capability Engine — writes execute through the Execution Engine (production path)
* Permissions — read-only cannot write; ask-every-time prompts before run; deny blocks
* Knowledge — indexed documents untouched (no documents/memory coupling)
* Desktop — confirmation, progress, and friendly failure messages
* Observability — audit records for writes; request/correlation IDs on execution + audit
* Regression — automation suite green; full suite green aside from intermittent unrelated documents worker flake

**Remaining**

* Durable audit persistence (shared with Milestone 21)
* Desktop settings UI for capability permission policies
* Autonomous workflows and background scheduling (explicitly out of scope)

---

# Forward Roadmap Status

Future work tracks [`ROADMAP.md`](ROADMAP.md) / [`ROADMAP_V2.md`](ROADMAP_V2.md) Phases 1–6.
Milestones 0–6 above remain the platform foundation tracker; Milestone 17 adds the shared model provider boundary.
Milestone 20 adds the Knowledge Explorer inspection surface. Milestone 21 adds the
Capability Execution Engine.

---

# Phase 1 — Complete V1 Platform

**Overall Status:** In progress

Documents, Memory, Search, and Intelligence vertical slices exist. Workspace
ownership is enforced on those paths. Observability, production hardening, and
API stability remain.

**Completed**

* Core Documents → Memory → Search → Intelligence pipeline paths
* Conversation API with Search-backed retrieval and durable storage
* Workspace ownership boundary with repository and search isolation

**In Progress**

* Typed config and platform package/contract hardening
* API stability for clients

**Remaining**

* Documents / Memory / Search / Intelligence production readiness
* Auth-bound workspace membership and audit logging
* Production hardening
* API stability for clients

**Completed (Phase 1 platform)**

* Observability foundation: request context propagation, structured logs, diagnostic event bridge, metrics interface, OTel-neutral spans, `/ready` checks

**Known Risks**

* Building the desktop client before API stability lands creates rework

**Next Recommended Work**

* Finish API stability and typed config before Phase 2

---

# Phase 2 — Desktop Client

**Overall Status:** In progress

The flagship Tauri desktop shell lives in `apps/desktop`. It launches, probes
backend health/readiness, and exposes Chat plus the Knowledge Explorer over the
platform APIs. Remaining product pages are still placeholders.

**Completed**

* `apps/desktop` Tauri + React shell foundation
* Sidebar / top bar / main content / status bar layout
* Backend connection detection, reconnect polling, and friendly errors
* Navigation registry reserved for Chat, Knowledge, Documents, Search, Workspaces, Models,
  Activity, Capabilities, and Settings
* Chat conversation experience (list/create/rename/delete, history, SSE streaming,
  markdown/code copy, stop/retry, workspace + model selectors)
* Knowledge Explorer (overview, search, concepts, entities, relationships, sources)
* `docs/architecture/DESKTOP_CLIENT.md`
* `docs/architecture/KNOWLEDGE_EXPLORER.md`

**In Progress**

* Desktop foundation validation and local developer workflow

**Remaining**

* Collections
* Settings
* Model management product page
* Workspace management product page
* Indexing status

**Known Risks**

* Building rich client pages before Phase 1 contracts stabilize creates rework
* Desktop requires Rust and host linker tooling beyond Node/Python setup

**Next Recommended Work**

* Expand Documents ingestion UX and deepen semantic entity/concept extraction behind explorer labels

---

# Phase 3 — Capability Framework

**Overall Status:** In progress

**Completed**

* `packages/automation` Capability Framework foundation
* Core contracts: `Capability`, `CapabilityRegistry`, `CapabilityInvoker`, `CapabilityMetadata`, `CapabilityPermission`, `CapabilityRequest`, `CapabilityResult`, `CapabilityContext`, `CapabilityExecutionPolicy`
* Capability Execution Engine with permission modes, approval states, and audit trail
* Composition-root filesystem registration and Intelligence execution port adapter
* Desktop approval / progress presentation for capability executions
* Unit and integration tests for registry, permissions, execution, cancellation, timeouts, and error contracts
* Smoke tests for MockFilesystem / MockTerminal registration, invocation, unknown-capability structured errors, and deterministic re-composition
* `FilesystemCapability` (`filesystem`) with root-scoped path safety, structured errors, and read/write permission enforcement
* Filesystem write operations with overwrite/trash policies and fine-grained create/modify/move/delete permissions
* Filesystem smoke and write tests: register, read/write, traversal rejection, permission and audit coverage
* Architecture references: `docs/architecture/CAPABILITY_FRAMEWORK.md`, `docs/architecture/CAPABILITY_EXECUTION.md`, `docs/architecture/FILESYSTEM_CAPABILITY.md`, `docs/architecture/FILESYSTEM_WRITE.md`

**In Progress**

* None

**Remaining**

* Concrete capabilities: Terminal, Browser, Git, Clipboard, Notifications
* Desktop settings UI for capability permission policies
* Plugin system / loading
* Durable audit persistence

**Known Risks**

* Hosts that grant filesystem permissions over overly broad roots expand the trusted surface

**Next Recommended Work**

* Add the next concrete capability (Terminal or Git) and durable audit storage

---

# Phase 4 — Automation

**Overall Status:** Not started

**Completed**

* None

**In Progress**

* None

**Remaining**

* Safe execution
* Approval workflow
* Task orchestration
* Background jobs
* Capability composition

**Known Risks**

* Automation without approval and provenance undermines trust

**Next Recommended Work**

* Build on the Capability Framework, not as a parallel agent stack

---

# Phase 5 — Knowledge Evolution

**Overall Status:** Not started

**Completed**

* None

**In Progress**

* None

**Remaining**

* Summaries
* Long-term memory
* Knowledge graph
* Reasoning cache
* Inference-efficient retrieval

**Known Risks**

* Without this layer, AI and embedding spend will grow with corpus size

**Next Recommended Work**

* Begin after V1 platform and desktop product contracts are stable

---

# Phase 6 — Ecosystem

**Overall Status:** Not started

**Completed**

* None

**In Progress**

* None

**Remaining**

* Optional web client
* Optional mobile client
* Cloud sync
* Enterprise deployment
* Connector marketplace

**Known Risks**

* Treating web or mobile as primary would conflict with the desktop-first vision

**Next Recommended Work**

* Keep ecosystem clients optional and API-backed

---

# How To Update This Document

When implementation changes:

1. Move items between Completed / In Progress / Remaining
2. Refresh Overall Status and the short summary
3. Update Known Risks and Next Recommended Work
4. Keep [`ROADMAP.md`](ROADMAP.md) / [`ROADMAP_V2.md`](ROADMAP_V2.md) focused on direction, not progress
5. Keep Milestones 0–6 as the platform foundation; use Phases 1–6 for forward work
