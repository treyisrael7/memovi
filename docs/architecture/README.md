# Architecture Documentation

# Purpose

This directory contains the focused engineering references that expand the high-level blueprint in [`../ARCHITECTURE.md`](../ARCHITECTURE.md).

# Scope

Use these documents when a topic needs more detail than the top-level architecture overview should carry.

Each document covers one architectural concern and should remain aligned with the decisions in [`../ARCHITECTURE.md`](../ARCHITECTURE.md).

# Relationship to ARCHITECTURE.md

[`../ARCHITECTURE.md`](../ARCHITECTURE.md) is the canonical blueprint.

The files in this directory are supporting references. They clarify, expand, and organize the same architecture; they do not introduce separate architectural direction.

# Reading Guide

Start with [`../PRODUCT_VISION.md`](../PRODUCT_VISION.md) for product direction, then
[`../ARCHITECTURE.md`](../ARCHITECTURE.md) for the platform blueprint. Follow the
document that matches the concern being changed or reviewed.

| Document | Concern |
| --- | --- |
| [`../PRODUCT_VISION.md`](../PRODUCT_VISION.md) | Canonical product vision: mission, identity, principles, layers, non-goals |
| [`domains.md`](domains.md) | Business domains, responsibilities, ownership, communication, and future domains |
| [`module-architecture.md`](module-architecture.md) | Modular monolith, layers, dependency direction, and service boundaries |
| [`repository-architecture.md`](repository-architecture.md) | Monorepo structure, top-level directories, ownership, and repository evolution |
| [`request-lifecycle.md`](request-lifecycle.md) | Synchronous request flow, async transitions, failures, and transaction boundaries |
| [`event-architecture.md`](event-architecture.md) | Event philosophy, event lifecycle, event ownership, workers, failures, and versioning |
| [`knowledge-processing-pipeline.md`](knowledge-processing-pipeline.md) | Acquisition, normalization, storage, processing, knowledge creation, indexing, retrieval, and intelligence |
| [`storage-architecture.md`](storage-architecture.md) | PostgreSQL, pgvector, MinIO, Redis, data ownership, backup, and versioning |
| [`search-architecture.md`](search-architecture.md) | Search responsibility, retrieval strategies, indexes, ranking, and boundaries |
| [`intelligence-architecture.md`](intelligence-architecture.md) | AI's role, provider routing, RAG, summaries, planning, and boundaries |
| [`connector-framework.md`](connector-framework.md) | Connector responsibilities, external sync, acquisition, and normalization |
| [`CAPABILITY_FRAMEWORK.md`](CAPABILITY_FRAMEWORK.md) | Capability abstractions, registry, permissions, invocation, and plugin path |
| [`FILESYSTEM_CAPABILITY.md`](FILESYSTEM_CAPABILITY.md) | Read-only filesystem capability: safety, permissions, operations |
| [`MODEL_PROVIDER_FRAMEWORK.md`](MODEL_PROVIDER_FRAMEWORK.md) | Provider-neutral model abstractions, registry, capabilities, health |
| [`DESKTOP_CLIENT.md`](DESKTOP_CLIENT.md) | Flagship Tauri desktop shell, client boundaries, and API communication |
| [`observability.md`](observability.md) | Telemetry for requests, workers, events, AI, connectors, search, errors, and performance |
| [`deployment.md`](deployment.md) | Self-hostable posture, runtime components, infrastructure isolation, and deployment constraints |
| [`scaling.md`](scaling.md) | Evolution strategy, worker scaling, storage scaling, and future service extraction |

# Maintenance Rules

When implementation changes affect an architectural concern, update the relevant focused document and check whether the high-level blueprint also needs to change.

Avoid duplicating large explanations across files. Put detailed content in the most specific document and link to it from related documents.

# Key Decisions

* [`../ARCHITECTURE.md`](../ARCHITECTURE.md) remains the canonical blueprint.
* Each document in this directory owns one architectural concern.
* Deep-dive documents expand the blueprint without contradicting it.
* Duplicate explanations should be consolidated into the most specific document.

# Related Documents

* [`../README.md`](../README.md) — documentation hub
* [`../PRODUCT_VISION.md`](../PRODUCT_VISION.md)
* [`../ARCHITECTURE.md`](../ARCHITECTURE.md)
* [`../PHILOSOPHY.md`](../PHILOSOPHY.md)
* [`../ROADMAP.md`](../ROADMAP.md)
