# Memovi Roadmap

> **This roadmap describes the long-term evolution of Memovi. It is organized around engineering milestones rather than release dates.**

---

# Roadmap Philosophy

Memovi is built as a platform, not a collection of isolated features.

Each milestone expands the capabilities of the platform while reinforcing the architecture established in the project's philosophy and architecture documentation.

The roadmap is intentionally outcome-driven rather than time-driven.

Features may move between milestones as the project evolves, but the overall progression should remain stable.

Every milestone should leave the platform in a usable, production-quality state.

---

# Guiding Principles

The roadmap follows several principles:

* Build the foundation before advanced features.
* Deliver complete vertical slices rather than partial systems.
* Prioritize maintainability over feature count.
* Introduce operational complexity only when justified.
* Validate architectural decisions before expanding the platform.

---

# Milestone 0 — Foundation

**Status**

Complete — 2026-06-27

**Objective**

Establish the engineering foundation that every future feature depends on.

**Deliverables**

* Repository structure
* Python workspace
* Frontend workspace
* Local Docker Compose infrastructure
* GitHub Actions validation
* Code quality tooling
* Pre-commit hooks
* VS Code Dev Container
* Task runner
* Project documentation

**Success Criteria**

* A new developer can clone the repository and start the project with minimal setup.
* Development tooling is consistent across the project.
* Architecture is reflected in the repository structure.

---

# Milestone 1 — Platform Skeleton

**Status**

In progress — core platform operational; architecture validation and observability remain.

**Objective**

Establish the backend platform that future business domains build upon.

**Deliverables**

* Backend composition root — **done**
* FastAPI application bootstrap — **done**
* Domain package scaffolding — **partial** (`auth` and `documents` implemented; other domains scaffolded)
* Configuration system — **partial** (environment-based settings; typed `memovi_config` package not yet wired)
* Dependency injection — **done**
* Structured logging — **partial** (application logging; structured/JSON logging not yet implemented)
* Observability foundation — **partial** (`packages/observability` scaffolded; tracing and metrics not yet implemented)
* Router registration — **done**
* Health endpoint — **done**
* Architecture tests — **not started**

**Success Criteria**

* The backend boots successfully. — **met**
* All domain packages follow a consistent architecture. — **partial** (implemented domains follow boundaries; others are scaffolds)
* Cross-cutting concerns are centralized. — **met**
* Every future business domain can plug into the platform without modifying its core. — **met**
* The architecture is validated through automated architecture tests. — **not met**

---

# Milestone 2 — Local Identity & Ownership

**Status**

In progress — local authentication works; ownership is not yet enforced on knowledge domains.

**Objective**

Build the local authentication layer that establishes ownership of knowledge in a
self-hosted Memovi instance.

**Deliverables**

* User registration — **done**
* Secure local login — **done**
* HTTP-only session cookies — **done**
* Session persistence and logout — **done**
* Current-user API boundary — **done**
* Ownership-aware request context — **not started** (documents ingestion is not yet user-scoped)
* Audit logging for ownership-sensitive actions — **not started**

**Success Criteria**

* Users can securely authenticate with local credentials. — **met**
* Every ownership-sensitive request can identify the current user. — **partial** (auth boundary exists; knowledge APIs do not yet require it)
* Authentication is isolated from knowledge domains. — **met**
* Memovi does not depend on JWT, OAuth, RBAC, or API keys for the local foundation. — **met**

---

# Milestone 3 — Knowledge Ingestion

**Status**

In progress — upload-to-processing pipeline is operational locally; enrichment stages remain.

**Objective**

Allow information to enter the platform through a unified ingestion pipeline.

**Deliverables**

* Document uploads — **done** (`POST /documents`, 202 Accepted)
* Local file connector — **partial** (upload ingest path via `IngestLocalDocument`; connector framework not yet built)
* Object storage — **done** (MinIO-backed immutable artifact storage)
* Metadata extraction — **partial** (filename, MIME type, source type at ingest; text extraction and normalization during processing)
* Document versioning — **partial** (version model and initial version on upload; no re-upload or new-version workflow yet)
* Document processing engine — **done** (synchronous `ProcessDocument` pipeline for PDF, Markdown, and plain text)
* Processing queue — **done** (application-layer queue abstraction with in-memory implementation for local development)
* Background document processing — **done** (worker polls queue, executes processing engine, updates job status, publishes events, retries transient failures)
* OCR pipeline — **not started**
* Chunk generation — **not started**

**Success Criteria**

* Documents are stored reliably. — **met**
* Every uploaded document enters the knowledge pipeline. — **met**
* Processing occurs asynchronously. — **met**

---

# Milestone 4 — Knowledge Platform

**Status**

In progress — memory domain scaffolding established; knowledge workflows remain.

**Objective**

Transform processed documents into structured knowledge.

**Deliverables**

* Memory domain — **partial** (entities, events, repositories, and persistence scaffold)
* Collections — **not started**
* Tags — **not started**
* Version history — **not started**
* Knowledge relationships — **not started**
* Metadata management — **not started**
* Processing status tracking — **not started**

**Success Criteria**

* Knowledge is independent from AI providers. — **not met**
* The platform can organize and manage information at scale. — **not met**

---

# Milestone 5 — Search & Retrieval

**Objective**

Provide fast, accurate retrieval across the knowledge platform.

**Deliverables**

* Full-text search — **done**
* Vector search — **partial** (event-driven embedding generation and JSON vector persistence; no pgvector or similarity search yet)
* Hybrid retrieval
* Metadata filtering — **done** (full-text search projections)
* Semantic ranking
* Search APIs — **partial** (`GET /search` for full-text search)
* Query optimization

**Success Criteria**

* Users can reliably retrieve relevant knowledge.
* Search supports multiple retrieval strategies without changing client behavior.

---

# Milestone 6 — Intelligence

**Objective**

Enable intelligent interaction with stored knowledge.

**Deliverables**

* Chat interface
* Retrieval-Augmented Generation (RAG)
* Provider abstraction
* Prompt management
* AI summaries
* Tool calling
* Provider routing

**Success Criteria**

* AI consumes platform knowledge without owning it.
* AI providers remain interchangeable.

---

# Milestone 7 — Connector Ecosystem

**Objective**

Expand the platform beyond local documents.

**Deliverables**

* GitHub connector
* Google Drive connector
* Gmail connector
* Slack connector
* Notion connector
* Obsidian connector
* Connector SDK
* Synchronization scheduling

**Success Criteria**

* New connectors follow a consistent interface.
* External systems integrate through normalization rather than custom logic.

---

# Milestone 8 — Platform Maturity

**Objective**

Strengthen the platform through operational and architectural improvements.

**Deliverables**

* Knowledge graph
* Temporal memory
* Advanced observability
* Distributed workers
* Background scheduling
* Performance optimization
* Advanced caching
* Backup and recovery improvements

**Success Criteria**

* The platform scales without architectural redesign.
* Operational visibility supports production deployments.

---

# Milestone 9 — Multi-Client Platform

**Objective**

Deliver Memovi across multiple user experiences.

**Deliverables**

* Desktop application
* Browser extension
* Mobile application
* Public API
* CLI
* SDKs

**Success Criteria**

* Every client consumes the same platform capabilities.
* Business logic remains centralized.

---

# Future Vision

Potential long-term capabilities include:

* Multi-user workspaces
* Team knowledge sharing
* Plugin marketplace
* Agent runtime
* Workflow automation
* Knowledge graph visualization
* Federated search
* Enterprise deployment
* Real-time collaboration
* Offline synchronization

These initiatives are intentionally exploratory and may evolve as the platform matures.

---

# What We Will Not Optimize For

Memovi intentionally avoids:

* Premature microservices
* Feature quantity over quality
* Vendor lock-in
* AI provider dependence
* Unnecessary architectural complexity
* Short-term optimizations that compromise long-term maintainability

---

# Measuring Progress

Progress is measured by platform maturity rather than the number of completed features.

A milestone is considered complete when:

* The architecture remains consistent.
* The feature is production-ready.
* Documentation has been updated.
* Tests are comprehensive.
* Operational visibility exists.
* Future milestones become easier to build.

---

# Living Document

This roadmap is expected to evolve.

New ideas will emerge.

Priorities will change.

Architecture will mature.

Changes should preserve the long-term vision of Memovi while remaining grounded in practical engineering decisions.

The roadmap is a guide for the platform's evolution—not a promise of fixed delivery dates.
