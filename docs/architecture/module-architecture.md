# Module Architecture

# Purpose

This document defines how Memovi's modular monolith is structured and how module boundaries are maintained.

# Scope

It covers the modular monolith, layered architecture, dependency direction, module ownership, service boundaries, and the future microservice extraction strategy.

# Relationship to ARCHITECTURE.md

[`../../ARCHITECTURE.md`](../../ARCHITECTURE.md) summarizes Memovi's modular architecture. This document expands the constraints that keep the monolith modular and extractable.

# Modular Monolith

Memovi begins as a modular monolith.

Each business domain exists as an independent module within a single deployable application.

Every module owns:

* Public APIs
* Application services
* Domain models
* Persistence
* Domain events
* Tests

Modules communicate through well-defined interfaces and events rather than direct implementation details.

This provides the development simplicity of a monolith while preserving the boundaries necessary for future extraction into independent services.

The goal is not to avoid microservices. The goal is to delay distributed complexity until it becomes operationally beneficial.

# Domain-Driven Modules

Modules follow business responsibilities rather than technical categories.

Responsibilities such as Authentication, Documents, Memory, Search, Connectors, and Intelligence define module boundaries.

Technology supports the domain. The domain should never be shaped by the technology.

See [`domains.md`](domains.md).

# Layered Architecture

Every component belongs to one architectural layer.

The primary layers are:

1. Presentation
2. Application
3. Knowledge Platform
4. Intelligence
5. Processing
6. Infrastructure

Dependencies always point downward. Lower layers never depend on higher layers.

This keeps the architecture understandable while preventing circular dependencies.

# Layer Responsibilities

## Presentation

The Presentation Layer contains user interfaces and external entry points. It renders interfaces, accepts input, displays results, authenticates users, and calls platform APIs.

It contains no business logic.

## Application

The Application Layer coordinates work across domains. It owns request validation, authorization, commands, queries, application services, transaction boundaries, DTOs, and API orchestration.

It coordinates platform services rather than performing OCR, embeddings, AI provider calls, or vector queries directly.

## Knowledge Platform

The Knowledge Platform Layer owns the platform's understanding of knowledge.

It includes Documents, Memory, Search, Connectors, Collections, Tags, Metadata, and future Knowledge Graph capabilities.

The Knowledge Platform must never depend upon the Intelligence Layer.

## Intelligence

The Intelligence Layer consumes knowledge and enriches information already stored by the Knowledge Platform.

It includes chat, RAG, prompt construction, tool orchestration, provider routing, AI summaries, planning, reasoning, and future autonomous agents.

## Processing

The Processing Layer performs long-running asynchronous work.

Workers handle OCR, file parsing, document chunking, embedding generation, search indexing, entity extraction, and future graph construction.

Processing components should remain stateless whenever practical.

## Infrastructure

The Infrastructure Layer provides technical capabilities such as PostgreSQL, pgvector, Redis, MinIO, object storage, logging, metrics, tracing, Docker, and configuration.

Infrastructure exists to support the platform. Business decisions should never originate from infrastructure components.

# Dependency Direction

The foundational dependency rules are:

* Presentation depends on Application.
* Application depends on the Knowledge Platform.
* The Knowledge Platform may publish events consumed by the Processing Layer.
* Intelligence consumes knowledge but never owns it.
* Infrastructure supports every layer while remaining free of business logic.

Any architecture that violates these dependency directions should be considered an exception requiring explicit justification.

# Service Boundaries

Current module boundaries should be treated as future service boundaries.

Keep contracts explicit, persistence ownership clear, and cross-domain communication narrow.

Extraction should be possible because boundaries were respected from the start, not because the codebase is rewritten later.

# Future Microservice Extraction

Modules may be extracted only when operational requirements justify independent deployment, scaling, failure isolation, or team ownership.

Premature services increase deployment, networking, observability, data consistency, and operational cost before the domain model is mature.

Well-defined modules can be extracted later. Unnecessary services are hard to recombine.

# Key Decisions

* Memovi starts as a modular monolith.
* Domain boundaries define module boundaries.
* Dependencies point downward through layers.
* Lower layers never depend on higher layers.
* The Knowledge Platform remains independent from Intelligence.
* Infrastructure supports the platform without defining business behavior.
* Future service extraction follows domain boundaries.
* Microservices are delayed until operational needs justify them.

# Related Documents

* [`../../ARCHITECTURE.md`](../../ARCHITECTURE.md)
* [`domains.md`](domains.md)
* [`event-architecture.md`](event-architecture.md)
* [`request-lifecycle.md`](request-lifecycle.md)
* [`scaling.md`](scaling.md)
