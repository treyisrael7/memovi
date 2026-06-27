# Request Lifecycle

# Purpose

This document defines how synchronous user requests move through Memovi and where long-running work transitions into asynchronous processing.

# Scope

It covers request flow, request stages, synchronous versus asynchronous operations, example flows, failure handling, and transaction boundaries.

# Relationship to ARCHITECTURE.md

[`../../ARCHITECTURE.md`](../../ARCHITECTURE.md) summarizes the request model. This document is the detailed lifecycle reference.

# Overview

Every interaction within Memovi follows a consistent lifecycle.

Regardless of whether a user uploads a document, performs a search, connects a new service, or interacts with an intelligent assistant, requests move through the same architectural stages.

This consistency improves maintainability, simplifies debugging, and provides a predictable foundation for future capabilities.

The request lifecycle is intentionally separated from background processing.

User requests should remain fast and deterministic. Long-running work is delegated to the Processing Layer through domain events.

# Request Flow

Every synchronous request follows the same high-level path.

```text
Client
    │
    ▼
Presentation Layer
    │
    ▼
Application Layer
    │
    ▼
Business Domain
    │
    ▼
Persistence
    │
    ▼
Response
```

Each layer has a clearly defined responsibility. Requests should move through these layers without bypassing architectural boundaries.

# Stage 1 - Client Request

Every interaction begins with a client.

Examples include:

* Web application
* Desktop application
* Browser extension
* Mobile application
* CLI
* Public API

Clients are responsible for presenting information and collecting user input. Clients should never implement business logic.

Every client consumes the same platform capabilities.

# Stage 2 - Presentation

The Presentation Layer receives the request.

Responsibilities include:

* Request validation
* Authentication
* Authorization
* Input serialization
* Output formatting

The Presentation Layer determines whether a request is valid. It does not decide how the request should be fulfilled.

Once validated, responsibility transfers to the Application Layer.

# Stage 3 - Application

The Application Layer coordinates the use case.

Responsibilities include:

* Selecting the appropriate domain
* Beginning transactions
* Coordinating workflows
* Publishing domain events
* Returning application results

Application services orchestrate business capabilities. They do not contain business rules themselves.

Business decisions remain within the Domain layer.

# Stage 4 - Domain

The Domain Layer performs business work.

Examples include:

* Creating documents
* Updating memory
* Searching knowledge
* Registering connectors
* Managing permissions

Business rules should remain independent of infrastructure.

The Domain determines what should happen. It does not determine how persistence is implemented.

# Stage 5 - Persistence

Infrastructure stores or retrieves information.

Examples include:

* PostgreSQL
* pgvector
* Redis
* MinIO

Persistence implementations remain hidden behind repositories and infrastructure adapters.

Business domains should never depend directly upon storage technologies.

# Stage 6 - Response

After the business operation completes, the Application Layer returns a result.

Presentation converts that result into an appropriate response.

The response should represent completed work only. Operations expected to continue asynchronously should acknowledge acceptance rather than completion.

# Synchronous vs Asynchronous Operations

Memovi intentionally distinguishes between immediate work and background work.

Operations expected to complete quickly remain synchronous.

Examples include:

* Authentication
* Searching
* Reading knowledge
* Updating metadata
* Managing collections

Long-running work transitions into asynchronous processing.

Examples include:

* OCR
* Chunk generation
* Embedding creation
* Large connector synchronization
* AI summarization
* Entity extraction

Users should never wait for operations that can safely continue in the background.

# Example - Document Upload

Uploading a document illustrates the complete request lifecycle.

```text
User
    │
    ▼
Upload Document
    │
    ▼
Presentation
    │
    ▼
Application
    │
    ▼
Documents Domain
    │
    ▼
Store File
    │
    ▼
Publish DocumentUploaded Event
    │
    ▼
Return Success
```

Processing has not yet begun. The request ends after the document has been safely accepted. Subsequent work occurs asynchronously.

# Example - Semantic Search

Search requests remain synchronous.

```text
User
    │
    ▼
Search Query
    │
    ▼
Presentation
    │
    ▼
Search Domain
    │
    ▼
Retrieve Knowledge
    │
    ▼
Rank Results
    │
    ▼
Return Results
```

The request completes once retrieval has finished. No additional background processing is required.

# Example - AI Conversation

Intelligent conversations combine multiple domains.

```text
User
    │
    ▼
Question
    │
    ▼
Presentation
    │
    ▼
Intelligence
    │
    ▼
Search
    │
    ▼
Memory
    │
    ▼
Context Assembly
    │
    ▼
Provider
    │
    ▼
Response
```

The Intelligence domain consumes platform capabilities. It does not access persistence directly.

Knowledge retrieval always occurs through the Search and Memory domains.

# Request Boundaries

Every request should satisfy these principles:

* Complete quickly whenever practical.
* Avoid unnecessary coupling.
* Publish events instead of performing expensive work inline.
* Return deterministic results.
* Respect domain ownership.
* Never bypass architectural layers.

If a request requires substantial computation, it should transition into background processing.

# Failure Handling

Failures should occur as early as possible.

Validation errors belong within the Presentation Layer.

Business rule violations belong within Domains.

Infrastructure failures remain isolated within Infrastructure.

Unexpected failures should never leak implementation details to clients.

Every failure should produce meaningful telemetry for debugging and observability.

See [`observability.md`](observability.md).

# Transaction Boundaries

Transactions belong to application use cases.

A transaction should represent a single business operation.

Long-running workflows should never remain inside a single database transaction.

Instead:

1. Complete the business transaction.
2. Publish the appropriate domain event.
3. Continue processing asynchronously.

This approach improves scalability while reducing lock contention and operational complexity.

# Key Decisions

* Every request follows the same layered path through the platform.
* Presentation validates, but Domains decide.
* Application services coordinate without owning business rules.
* Persistence remains hidden behind repositories and adapters.
* Long-running work transitions into asynchronous processing.
* AI interactions consume platform capabilities rather than bypassing them.
* Transaction boundaries align with business operations rather than technical implementation.
* Every request should remain predictable, observable, and easy to reason about.

# Related Documents

* [`../../ARCHITECTURE.md`](../../ARCHITECTURE.md)
* [`domains.md`](domains.md)
* [`module-architecture.md`](module-architecture.md)
* [`event-architecture.md`](event-architecture.md)
* [`knowledge-processing-pipeline.md`](knowledge-processing-pipeline.md)
* [`observability.md`](observability.md)
