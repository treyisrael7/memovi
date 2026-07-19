# Memovi Status

Living implementation tracker for Memovi as a desktop-first knowledge operating
system on a reusable backend platform.

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

* Memory domain ownership of knowledge items (HTTP `/memory` surface not exposed)
* Processing status as a knowledge concern (job statuses exist in documents; no public Memory status API)
* Knowledge independence from AI providers (memory/search do not depend on Intelligence; organization incomplete)

**Remaining**

* Collections
* Tags
* Version history
* Knowledge relationships
* Metadata management as a first-class platform concern

**Known Risks**

* Knowledge organization may lag behind ingestion and search capability

**Next Recommended Work**

* Expose Memory APIs and establish collections/tags foundations

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

Reasoning pipeline, conversation memory, Conversation REST API, and Search-backed retrieval for conversations are operational. Desktop client UX and summaries remain.

**Completed**

* Reasoning pipeline (retrieve → assemble → prompt → provider)
* Conversation memory (`ConversationService`, history-aware context)
* Conversation REST API (create/get conversation, list/send messages)
* Execution traces and citations
* Provider gateway with `fake` and `openai` adapters
* Search-backed knowledge retrieval (`SearchKnowledgeRetriever` in `apps/api`)
* Durable conversation storage (`SqlAlchemyConversationRepository` in `apps/api`)

**In Progress**

* Provider abstraction and routing (env-driven selection; broader providers reserved)
* Prompt construction (`PromptBuilder`; no prompt library/versioning product)
* Tool execution framework (`ToolRegistry` / `ToolExecutor` / `EchoTool`; not in conversation Reason path)
* Cost-aware model selection (basic provider/model config only)

**Remaining**

* Desktop client conversation UX, streaming, and realtime channels as needed
* AI summaries

**Known Risks**

* Tool framework is not yet part of the conversation path

**Next Recommended Work**

* Close Phase 1 platform gaps (ownership, observability, API stability), then Desktop Client

---

# Forward Roadmap Status

Future work tracks [`ROADMAP.md`](ROADMAP.md) / [`ROADMAP_V2.md`](ROADMAP_V2.md) Phases 1–6.
Milestones 0–6 above remain the platform foundation tracker.

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

**Overall Status:** Not started

Optional web workspace exists as a shell. The flagship desktop client is not
delivered. Backend APIs are the platform boundary for all clients.

**Completed**

* None for product clients

**In Progress**

* None

**Remaining**

* Native desktop application
* Conversation UI
* Collections
* Settings
* Model management
* Workspace management
* Indexing status

**Known Risks**

* Building clients before Phase 1 contracts stabilize creates rework

**Next Recommended Work**

* Keep the desktop client behind stable Conversation, Search, and ownership APIs

---

# Phase 3 — Capability Framework

**Overall Status:** In progress

**Completed**

* `packages/automation` Capability Framework foundation
* Core contracts: `Capability`, `CapabilityRegistry`, `CapabilityInvoker`, `CapabilityMetadata`, `CapabilityPermission`, `CapabilityRequest`, `CapabilityResult`, `CapabilityContext`, `CapabilityExecutionPolicy`
* Declarative permission model (metadata only; no approval UI)
* Unit and integration tests for registry, permissions, execution, cancellation, timeouts, and error contracts
* Smoke tests for MockFilesystem / MockTerminal registration, invocation, unknown-capability structured errors, and deterministic re-composition
* Architecture reference: `docs/architecture/CAPABILITY_FRAMEWORK.md`

**In Progress**

* None

**Remaining**

* Concrete capabilities: Filesystem, Terminal, Browser, Git, Clipboard, Notifications
* Permission enforcement and user approval UX
* Plugin system / loading

**Known Risks**

* Concrete capabilities without enforcement of the declared permission model become an unsafe automation surface

**Next Recommended Work**

* Implement the first concrete capability (Filesystem read) behind `CapabilityContext`, then wire discovery for Intelligence

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
