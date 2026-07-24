# Memovi Roadmap

> Engineering roadmap for Memovi as a desktop-first knowledge operating system.
> Organized by capability phases, not release dates.

---

# Philosophy

Memovi is a desktop-first, AI-native knowledge operating system.

It is not a chatbot wrapper, a document viewer, a web-app-first product, or a
pile of AI features. It is a reusable backend platform whose flagship experience
is a desktop client; web and other clients are optional surfaces over the same API.

The platform is built around one rule:

**Knowledge is the product. Memory is the architecture. AI is a consumer of memory—not its owner.**

AI is an expensive computational resource. It should run only when cheaper layers cannot answer.

---

# Guiding Principles

* **Desktop-first** — the flagship product surface is a native desktop client.
* **Backend-first** — the reusable platform API is stable before product UX expands.
* **Client-independent** — desktop, optional web, and future clients share one API.
* **Knowledge-first** — durable knowledge outranks any single model or UI.
* **Automation on knowledge** — capabilities and automation build on the knowledge platform, not around it.
* **Platform before products** — shared capabilities come before client-specific features.
* **Architecture before features** — boundaries and ownership stay clear as scope grows.
* **Cost-aware by default** — prefer local, cached, and retrieved answers before generation.
* **AI as a last resort** — use models when reasoning or synthesis is required, not by habit.
* **Vendor independence** — providers are adapters; the knowledge model is not.
* **Modular architecture** — domains stay extractable without premature microservices.
* **Simplicity over cleverness** — prefer explicit, boring systems that stay maintainable.

---

# Evolution Path

```text
Platform
    │
    ▼
Desktop Product
    │
    ▼
Capabilities
    │
    ▼
Automation
    │
    ▼
Knowledge Operating System
    │
    ▼
Ecosystem (optional clients & deployment)
```

---

# Memory Philosophy

Memovi treats memory as layered architecture, not a single store.

## Raw Memory

Unprocessed source material.

* Documents
* Files
* Artifacts

## Structured Memory

Normalized, owned, durable knowledge.

* Metadata
* Ownership
* Versions
* Relationships

## Semantic Memory

Meaning derived from structured knowledge.

* Embeddings
* Concepts
* Summaries

## Working Memory

Short-lived context for an active task.

* Active conversation
* Current task
* Temporary context

## Reasoning Memory

Artifacts produced by AI workflows.

* Prompts
* Execution traces
* Tool outputs

---

# Retrieval Philosophy

Retrieval should become increasingly intelligent over time.

Memovi calls this **Retrieval Intelligence**: the system that decides what knowledge to fetch, how to fetch it, and how much context to spend before reasoning.

Retrieval should attempt the least expensive path first.

Example progression:

1. Exact or cached answer
2. Metadata / structured lookup
3. Keyword retrieval
4. Semantic or hybrid retrieval
5. Summaries or compressed context
6. Model reasoning only when required

---

# Platform Foundation

Completed and in-progress platform milestones. These are not reopened for redesign;
remaining gaps are finished under Phase 1.

## Milestone 0 — Foundation

**Objective**

Establish the engineering base every later milestone depends on.

**Primary Deliverables**

* Repository and workspace layout
* Local infrastructure
* CI, quality tooling, and documentation

**Success Criteria**

* A new engineer can clone, run, and contribute with minimal setup.
* Architecture is visible in repository structure.

---

## Milestone 1 — Platform

**Objective**

Establish the backend composition root and cross-cutting platform services.

**Primary Deliverables**

* FastAPI composition root
* Domain package boundaries
* Configuration, dependency injection, logging
* Health and router registration
* Observability foundation

**Success Criteria**

* The backend boots reliably.
* New domains can plug in without rewriting the core.

---

## Milestone 2 — Identity & Ownership

**Objective**

Make knowledge ownership explicit for a self-hosted instance.

**Primary Deliverables**

* Local registration and authentication
* Session-based identity
* Ownership-aware request context (Workspace + `WorkspaceId`; V1 header/`Default` fallback delivered)
* Audit trail for ownership-sensitive actions

**Success Criteria**

* Every ownership-sensitive request can identify the acting user.
* Auth remains isolated from knowledge domains.
* Knowledge reads/writes are workspace-scoped at repository and search boundaries.

---

## Milestone 3 — Knowledge Ingestion

**Objective**

Bring external information into the platform through one pipeline.

**Primary Deliverables**

* Document upload and object storage
* Processing jobs and background workers
* Text extraction and normalization
* Chunk generation
* Event-driven handoff into Memory

**Success Criteria**

* Uploaded documents enter the knowledge pipeline asynchronously.
* Processing failures are visible and recoverable.

---

## Milestone 4 — Knowledge Platform

**Objective**

Turn processed artifacts into durable, organized knowledge.

**Primary Deliverables**

* Memory domain ownership of knowledge items
* Metadata and versioning foundations
* Collections and tags
* Processing status as a knowledge concern
* Knowledge independent of AI providers

**Success Criteria**

* Knowledge remains useful with no language model available.
* Organization and ownership are first-class, not bolted on.

---

## Milestone 5 — Retrieval Intelligence

**Objective**

Provide fast, cost-aware retrieval across knowledge.

**Primary Deliverables**

* Keyword, semantic, and hybrid retrieval
* Metadata filtering
* Query planning and context budgeting
* Cache and summary lookup paths
* Stable search APIs

**Success Criteria**

* Relevant knowledge can be retrieved without invoking a model.
* Clients can change retrieval mode without changing product contracts.

---

## Milestone 6 — Reasoning Engine

**Objective**

Enable controlled reasoning over retrieved knowledge.

**Primary Deliverables**

* Reasoning pipeline (retrieve → assemble → prompt → provider)
* Provider abstraction and routing
* Shared Model Provider Framework (`packages/models`) for vendor-neutral contracts
* Conversation memory and Conversation API
* Execution traces and citations
* Tool execution framework
* Cost-aware model selection

**Success Criteria**

* AI consumes memory; it does not own it.
* Providers are interchangeable behind one gateway.
* Reasoning results remain explainable through traces and citations.

---

# Forward Roadmap

Future work after the platform foundation. Ordered from platform completion to
product, capabilities, automation, knowledge evolution, and ecosystem.

---

## Phase 1 — Complete V1 Platform

**Objective**

Finish a production-ready, client-agnostic V1 backend platform.

**Primary Deliverables**

* Documents — complete ingestion reliability and operator visibility
* Memory — durable knowledge organization foundations
* Search — stable retrieval contracts and quality hardening
* Intelligence — production-ready conversation and reasoning APIs
* Ownership — workspace isolation delivered; auth membership and audit remain
* Observability — logging, metrics, and traces that explain cost and failure
* Production hardening — resilience, backups, worker maturity
* API stability — versioned, documented contracts for clients

**Success Criteria**

* Desktop and other clients can build against a stable API.
* Knowledge pipeline is operable without UI-specific assumptions.
* Operators can explain failures and latency from telemetry.

---

## Phase 2 — Desktop Client

**Objective**

Ship the flagship desktop knowledge OS on the V1 platform API.

**Primary Deliverables**

* Native desktop application (`apps/desktop` Tauri shell foundation shipped)
* Conversation UI
* Knowledge Explorer (read-only inspection of memory)
* Collections
* Settings
* Model management
* Workspace management
* Indexing status

**Success Criteria**

* Desktop is clearly the primary product surface.
* UX consumes platform APIs; business logic stays in backend domains.
* Local-model and filesystem-oriented UX is possible without backend redesign.

---

## Phase 3 — Capability Framework

**Objective**

Give the desktop OS safe, permissioned access to the user’s environment.

**Primary Deliverables**

* Capability Framework foundation (`packages/automation`)
* Filesystem (read-only capability shipped; writes later)
* Terminal
* Browser
* Git
* Clipboard
* Notifications
* Plugin system
* Permission model (declarative now; enforcement with approval UX next)

**Success Criteria**

* Capabilities are explicit, auditable, and permissioned.
* Plugins cannot bypass knowledge or ownership boundaries.
* The backend remains the source of durable knowledge truth.
* Intelligence discovers capabilities through the registry; capabilities remain provider-agnostic.

---

## Phase 4 — Automation

**Objective**

Compose capabilities into safe, user-approved automation on top of knowledge.

**Primary Deliverables**

* Safe execution
* Approval workflow
* Task orchestration
* Background jobs
* Capability composition

**Success Criteria**

* Automation runs only with clear approval and provenance.
* Tasks compose capabilities without inventing parallel knowledge stores.
* Background work is observable and interruptible.

---

## Phase 5 — Knowledge Evolution

**Objective**

Make memory actively reduce future retrieval and inference cost.

**Primary Deliverables**

* Summaries
* Long-term memory
* Knowledge graph
* Reasoning cache
* Inference-efficient retrieval

**Success Criteria**

* Common needs are satisfied from memory or cache before generation.
* Knowledge becomes cheaper to reuse as the system matures.
* Graph and summary layers strengthen retrieval without owning raw truth.

---

## Phase 6 — Ecosystem

**Objective**

Extend the same platform to optional clients and broader deployment models.

**Primary Deliverables**

* Optional web client
* Optional mobile client
* Cloud sync
* Enterprise deployment
* Connector marketplace

**Success Criteria**

* Web and mobile remain optional; desktop stays the flagship.
* Additional clients do not fork business logic.
* Connectors and deployment options attach at platform boundaries.

---

# Connector Philosophy

Connectors normalize external information into Memovi's knowledge model.

They should support:

* Incremental synchronization
* Change detection
* Selective embedding
* Metadata preservation

Connectors must not encode product-specific business logic.

Once data is normalized, downstream ingestion, memory, retrieval, and reasoning should not need to know the source system. Marketplace packaging belongs in Phase 6.

---

# What Memovi Optimizes For

* Long-term maintainability
* Low operational and AI cost
* Explainable reasoning
* Provider independence
* Scalable knowledge organization
* Reusable modular architecture
* Clear ownership and provenance
* Desktop-first product clarity
* Production-quality vertical slices

---

# What Memovi Does Not Optimize For

* Unnecessary AI calls
* Premature microservices
* Web-first product framing
* Feature quantity over platform quality
* Vendor lock-in
* Hidden platform behavior
* Tightly coupled AI providers
* Demo-driven architecture
* Clever abstractions that obscure data flow

---

# Measuring Progress

A phase is complete when:

* Architecture remains consistent with this roadmap
* The capability is operable, tested, and documented
* Cost and failure modes are visible
* Later phases become easier, not harder

Progress is platform and product maturity, not feature count.

---

# Living Document

This roadmap will change.

Capabilities may move between phases.

The philosophy should not:

* Knowledge remains the product
* Memory remains the architecture
* AI remains a consumer
* Desktop remains the flagship client
* The API remains the platform boundary
* Cost efficiency remains a design constraint
