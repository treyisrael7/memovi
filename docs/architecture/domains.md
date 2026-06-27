# Domain Architecture

# Purpose

This document defines Memovi's business domains, their responsibilities, ownership boundaries, and communication model.

# Scope

It covers domain responsibilities, what each domain owns, what each domain must not own, cross-domain communication, current ownership boundaries, and rules for future domains.

# Relationship to ARCHITECTURE.md

[`../../ARCHITECTURE.md`](../../ARCHITECTURE.md) summarizes the domain model. This document is the focused reference for domain-level responsibility and ownership.

# Domain Model

Memovi is organized around business capabilities rather than technical concerns.

Each domain represents a distinct responsibility within the platform. Domains own their business logic, persistence, events, and public interfaces.

No domain should become responsible for functionality that belongs elsewhere. Strong ownership reduces coupling, improves maintainability, and allows domains to evolve independently.

# Domain Overview

The core platform consists of six primary business domains.

```text
                 Memovi

              Application
                    │
    ┌───────────────┼───────────────┐
    │               │               │
    ▼               ▼               ▼
 Authentication  Knowledge      Intelligence
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
   Documents     Memory      Search
                    │
              Connectors
```

Every feature implemented within Memovi should belong to one of these domains.

If a feature does not clearly belong to an existing domain, a new domain should only be introduced after careful consideration.

# Domain Responsibilities

## Authentication

### Purpose

The Authentication domain is responsible for user identity and access control.

It answers the question:

> Who is making this request, and what are they allowed to do?

### Owns

* Users
* Authentication
* Authorization
* Sessions
* API Keys
* OAuth Providers
* Roles
* Permissions

### Does Not Own

* User knowledge
* User preferences unrelated to authentication
* Documents
* AI interactions

Authentication should remain independent from business capabilities. Its responsibility ends once identity has been established.

## Documents

### Purpose

The Documents domain manages every piece of information entering the platform.

Regardless of where information originates, it first becomes a document. Examples include PDFs, Markdown, emails, source code, Slack messages, notes, images, and web pages.

Documents represent raw knowledge before enrichment.

### Owns

* Document metadata
* Upload lifecycle
* File storage references
* Document versions
* Content extraction requests
* Processing state

### Does Not Own

* Embeddings
* Search indexes
* AI summaries
* Knowledge relationships

Documents are the entry point into the knowledge pipeline, not the final representation.

## Memory

### Purpose

Memory represents the platform's persistent understanding of knowledge.

Unlike Documents, which represent raw information, Memory represents structured knowledge that can be retrieved, connected, and reasoned over.

Memory is the heart of Memovi.

### Owns

* Knowledge records
* Relationships
* Collections
* Tags
* Metadata
* Version history
* Temporal state
* Knowledge graph (future)

### Does Not Own

* File uploads
* OCR
* Embeddings
* AI providers
* Prompt generation

Memory should remain valuable even if every AI provider disappeared tomorrow.

## Search

### Purpose

Search is responsible for retrieving knowledge.

It determines how information is discovered, not how it is stored. Search should support multiple retrieval strategies without exposing implementation details to consumers.

### Owns

* Full-text search
* Vector search
* Hybrid retrieval
* Metadata filtering
* Ranking
* Query planning
* Retrieval optimization

### Does Not Own

* Knowledge storage
* AI responses
* Documents
* Connectors

Search retrieves. It does not generate answers.

See [`search-architecture.md`](search-architecture.md).

## Connectors

### Purpose

Connectors integrate external systems with Memovi.

Each connector translates external data into a normalized representation understood by the platform. Every connector follows the same lifecycle regardless of provider.

### Owns

* Authentication with external systems
* Discovery
* Synchronization
* Import scheduling
* Data normalization

### Does Not Own

* Search
* AI
* Memory
* Storage
* Embeddings

Connectors import knowledge. They do not interpret it.

See [`connector-framework.md`](connector-framework.md).

## Intelligence

### Purpose

The Intelligence domain applies reasoning to knowledge already managed by the platform.

It transforms retrieved knowledge into useful responses. Intelligence depends upon the Knowledge Platform. The Knowledge Platform must never depend upon Intelligence.

### Owns

* Chat
* Prompt construction
* Provider routing
* Tool orchestration
* AI summaries
* Planning
* Reasoning
* Future autonomous workflows

### Does Not Own

* Knowledge persistence
* Search indexes
* User authentication
* Connector synchronization

Artificial intelligence is a consumer of knowledge rather than its owner. This dependency direction is one of the most important architectural constraints within Memovi.

See [`intelligence-architecture.md`](intelligence-architecture.md).

# Domain Communication

Domains should communicate through stable interfaces.

When long-running workflows are involved, communication should occur through domain events.

```text
Document Uploaded
        │
        ▼
Processing Pipeline
        │
        ▼
Memory Updated
```

```text
Connector Sync Completed
        │
        ▼
Documents Imported
        │
        ▼
Embeddings Generated
        │
        ▼
Search Indexed
```

Direct coupling between domains should remain minimal. Every new dependency should have a clear architectural justification.

See [`event-architecture.md`](event-architecture.md) and [`request-lifecycle.md`](request-lifecycle.md).

# Domain Ownership

Every business capability should have exactly one owner.

| Capability | Owning Domain |
| --- | --- |
| User authentication | Authentication |
| File uploads | Documents |
| Knowledge storage | Memory |
| Semantic retrieval | Search |
| External integrations | Connectors |
| AI reasoning | Intelligence |

Shared ownership should be avoided whenever practical.

If multiple domains appear responsible for the same capability, the architectural boundary should be reconsidered.

# Future Domains

Additional domains should only be introduced when they represent a fundamentally new business capability.

Possible future examples include:

* Collaboration
* Notifications
* Billing
* Organizations
* Administration

New domains should never exist simply to separate implementation details. They should exist because the platform has acquired a new business responsibility.

# Key Decisions

* Every domain owns a single business capability.
* Business logic is organized by responsibility rather than technology.
* Knowledge is centered around the Memory domain.
* Search retrieves knowledge but never owns it.
* Intelligence consumes knowledge without persisting it.
* Connectors normalize information before it enters the platform.
* Documents represent raw information.
* Memory represents structured knowledge.
* Strong boundaries are preferred over convenience.
* Future service extraction should follow domain boundaries rather than technical layers.

# Related Documents

* [`../../ARCHITECTURE.md`](../../ARCHITECTURE.md)
* [`module-architecture.md`](module-architecture.md)
* [`request-lifecycle.md`](request-lifecycle.md)
* [`event-architecture.md`](event-architecture.md)
* [`knowledge-processing-pipeline.md`](knowledge-processing-pipeline.md)
* [`search-architecture.md`](search-architecture.md)
* [`intelligence-architecture.md`](intelligence-architecture.md)
* [`connector-framework.md`](connector-framework.md)
