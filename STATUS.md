# Memovi Status

Living implementation tracker.

* `ROADMAP.md` / `ROADMAP_V2.md` describe where Memovi is going.
* `STATUS.md` describes where Memovi is today.

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

Backend composition root is operational. Cross-cutting config, structured logging, observability, and architecture tests remain incomplete.

**Completed**

* FastAPI composition root and bootstrap
* Dependency injection and router registration
* Health endpoint
* Domain packages for auth, documents, search, and intelligence

**In Progress**

* Domain package scaffolding for remaining packages
* Environment-based configuration (typed `memovi_config` not yet wired)
* Application logging (structured/JSON logging not yet implemented)
* Observability package scaffold (tracing and metrics not yet implemented)

**Remaining**

* Architecture tests validating package boundaries
* Full observability foundation

**Known Risks**

* Cross-cutting concerns may stay ad hoc without typed config and observability

**Next Recommended Work**

* Wire typed configuration and harden logging/observability foundations

---

# Milestone 2 — Identity & Ownership

**Overall Status:** In progress

Local authentication works. Ownership is not yet enforced on knowledge domains.

**Completed**

* User registration
* Secure local login
* HTTP-only session cookies
* Session persistence and logout
* Current-user API boundary

**In Progress**

* None

**Remaining**

* Ownership-aware request context on knowledge APIs
* Audit logging for ownership-sensitive actions

**Known Risks**

* Knowledge APIs remain unauthenticated, delaying true ownership guarantees

**Next Recommended Work**

* Attach ownership context to documents, memory, search, and conversation paths

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

Reasoning pipeline, conversation memory, Conversation REST API, and Search-backed retrieval for conversations are operational. Product chat UI and summaries remain.

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

* Product chat UI, streaming, and WebSockets
* AI summaries

**Known Risks**

* Tool framework is not yet part of the conversation path

**Next Recommended Work**

* Product chat UI on top of durable conversations + Search-backed retrieval

---

# Milestone 7 — Memory Intelligence

**Overall Status:** Not started

Cost-reducing memory capabilities are defined on the roadmap but not implemented as a milestone slice.

**Completed**

* None

**In Progress**

* None

**Remaining**

* Hierarchical summaries
* Semantic and response caching
* Embedding lifecycle policies
* Selective embedding and adaptive chunking
* Context compression for reasoning

**Known Risks**

* Without this layer, AI and embedding spend will grow with corpus size

**Next Recommended Work**

* Begin after Retrieval Intelligence and Reasoning Engine have stable contracts

---

# Milestone 8 — Connector Ecosystem

**Overall Status:** Not started

Connector package remains a scaffold. No production connectors.

**Completed**

* None

**In Progress**

* None

**Remaining**

* Connector SDK and contracts
* Priority source connectors
* Incremental sync and change detection
* Selective embedding at the connector boundary

**Known Risks**

* Premature connectors would bypass normalization if Memory/ingestion contracts are unfinished

**Next Recommended Work**

* Define connector contracts after Knowledge Platform ownership is clearer

---

# Milestone 9 — Platform Maturity

**Overall Status:** Not started

Production hardening capabilities remain future work.

**Completed**

* None

**In Progress**

* None

**Remaining**

* Advanced observability
* Distributed workers and scheduling
* Performance and cache maturity
* Backup and recovery improvements
* Optional knowledge graph foundations

**Known Risks**

* Scaling without observability will hide cost and failure modes

**Next Recommended Work**

* Grow observability incrementally as earlier milestones stabilize

---

# Milestone 10 — Applications

**Overall Status:** Not started

Frontend workspace exists as a shell. Product clients are not delivered.

**Completed**

* None for product applications

**In Progress**

* None

**Remaining**

* Web application and chat UI
* CLI and public API surface maturity
* Desktop / extension / mobile as needed
* SDKs over stable contracts

**Known Risks**

* Building clients before ownership, retrieval, and reasoning contracts stabilize creates rework

**Next Recommended Work**

* Keep applications behind stable Conversation, Search, and ownership APIs

---

# How To Update This Document

When implementation changes:

1. Move items between Completed / In Progress / Remaining
2. Refresh Overall Status and the short summary
3. Update Known Risks and Next Recommended Work
4. Keep `ROADMAP.md` / `ROADMAP_V2.md` focused on direction, not progress
