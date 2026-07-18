# Memovi Product Vision

Canonical explanation of what Memovi is, why the architecture exists, and where
the product is going.

New contributors should read this after [`../README.md`](../README.md). For
system structure and boundaries, continue to [`ARCHITECTURE.md`](ARCHITECTURE.md).
For sequencing of work, see [`ROADMAP.md`](ROADMAP.md).

---

# Mission

Memovi is building a **knowledge operating system**, not a chatbot.

The mission is to help people collect, organize, retrieve, understand, and act
on their own knowledge—documents, notes, conversations, code, and external
services—under their control.

Artificial intelligence is part of that experience. It is not the product.

Chat is one interface to knowledge. Retrieval, organization, provenance, and
durable memory remain useful even when no language model is available.

---

# Product Identity

Memovi is a **desktop-first knowledge operating system** powered by a
**reusable backend platform**.

* The flagship product surface is a native desktop application.
* The backend API is the platform boundary.
* An optional web client and future mobile or CLI clients can share the same API.
* Clients are replaceable. Backend domains are not rewritten for each UI.

Desktop is preferred because it enables local models, filesystem access,
automation, and a richer operating experience without changing backend
architecture.

---

# Core Principles

## Knowledge before AI

Knowledge is the product. AI consumes knowledge; it does not own it.

Durable storage, metadata, provenance, search indexes, and memory remain
independent of any single model or provider.

## Automation before Agents

Memovi extends into automation through explicit capabilities, permissions, and
approval—not through opaque autonomous agents.

Safe composition of tools comes before agent-like autonomy.

## Desktop first

The primary product experience is desktop.

Web is optional. Mobile is future and optional. Neither replaces the desktop
flagship.

## Client independence

All clients call the same platform API.

Business logic belongs in backend domains. UIs present knowledge and capture
intent; they do not become a second source of truth.

## Provider independence

Remote APIs, local runtimes, and future providers are adapters.

Swapping a model or embedding provider must not require rewriting Memory,
Search, Documents, or client contracts.

## Composable architecture

Domains such as Documents, Memory, Search, and Intelligence stay independent
and compose through the API and events.

New capabilities attach at clear boundaries rather than sprawling through the
system.

## Local-first when practical

Self-hosting, local models, and local filesystem access are first-class goals
when they improve user control, privacy, or capability—without forcing
proprietary cloud dependencies into the core architecture.

---

# Architecture Layers

```text
Client
   │
   ▼
API
   │
   ├── Documents
   ├── Memory
   ├── Search
   ├── Intelligence
   └── Automation (future)
   │
   ▼
Storage
```

## Client

The presentation surface: primarily the desktop app; optionally web or other
clients.

Responsibilities:

* Render interfaces and accept user input
* Display results, status, and provenance
* Call the platform API
* Host local UX such as model selection and workspace navigation

The client contains no core business rules for knowledge ownership, retrieval,
or reasoning.

## API

The FastAPI platform boundary and composition root.

Responsibilities:

* Expose stable contracts to every client
* Authenticate and authorize requests
* Wire domains together without merging them
* Keep transport concerns out of domain logic

The API is what makes Memovi a platform rather than a single application.

## Documents

Ingestion of raw artifacts into the platform.

Responsibilities:

* Upload and artifact storage
* Processing jobs and normalization
* Hand-off of processed content into Memory

Documents own acquisition and processing of source material, not long-term
knowledge organization.

## Memory

Durable, organized knowledge.

Responsibilities:

* Knowledge items, chunks, metadata, and versioning foundations
* Organization such as collections and tags (as the platform matures)
* Knowledge that remains useful without AI

Memory is the architectural center of Memovi.

## Search

Retrieval over indexed knowledge.

Responsibilities:

* Keyword, semantic, and hybrid retrieval
* Filtering and ranking
* Stable retrieval APIs for clients and Intelligence

Search finds knowledge. It does not own raw uploads or reasoning.

## Intelligence

Reasoning over retrieved knowledge.

Responsibilities:

* Conversation and reasoning orchestration
* Prompt construction and provider routing
* Citations, traces, and explainability

Intelligence consumes Memory and Search. It never becomes the source of truth
for knowledge.

## Automation (future)

Safe execution of user-approved work on top of knowledge and capabilities.

Responsibilities (as the product evolves):

* Permissioned access to filesystem, terminal, browser, git, and related tools
* Approval workflows and task orchestration
* Composition of capabilities without inventing a parallel knowledge store

Automation builds on knowledge. It does not replace it.

## Storage

Infrastructure that persists and serves platform data.

Responsibilities:

* PostgreSQL (and pgvector) for durable records and vectors
* Object storage for artifacts
* Supporting infrastructure such as Redis where needed

Storage is an implementation detail behind domain repositories and contracts.

---

# Long-Term Vision

Memovi grows from a durable knowledge platform into a full knowledge operating
system.

Future capabilities include:

* Multiple AI providers behind one gateway
* Local models on the desktop and self-hosted runtimes
* Filesystem access
* Git integration
* Terminal access
* Email and calendar as knowledge sources and surfaces
* Browser capabilities
* Safe automation with approval
* Summaries and long-term memory
* Knowledge evolution: graphs, reasoning caches, and inference-efficient retrieval

The intended evolution remains:

```text
Platform
   → Desktop Product
   → Capabilities
   → Automation
   → Knowledge Operating System
   → Ecosystem (optional clients and deployment)
```

Optional web and mobile clients, cloud sync, enterprise deployment, and a
connector marketplace belong to the ecosystem layer. They do not redefine the
product as web-first.

---

# Non-Goals

Memovi is not:

* A chatbot wrapper
* Another RAG demo
* A browser extension product
* An AI IDE
* An autonomous agent

The focus is helping users **understand and work with their knowledge**, then
**safely extending** into automation when the knowledge platform and permission
model are strong enough to support it.

---

# Related Documents

* [`../README.md`](../README.md) — developer entry point
* [`README.md`](README.md) — documentation hub
* [`ARCHITECTURE.md`](ARCHITECTURE.md) — architectural blueprint
* [`ROADMAP.md`](ROADMAP.md) / [`ROADMAP_V2.md`](ROADMAP_V2.md) — phased direction
* [`PHILOSOPHY.md`](PHILOSOPHY.md) — engineering values
* [`STATUS.md`](STATUS.md) — implementation progress
