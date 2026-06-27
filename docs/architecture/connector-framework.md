# Connector Framework

# Purpose

This document defines the architectural role of connectors in Memovi.

# Scope

It covers connector responsibility, external system integration, acquisition, synchronization, normalization, ownership boundaries, and relationship to the knowledge pipeline.

# Relationship to ARCHITECTURE.md

[`../../ARCHITECTURE.md`](../../ARCHITECTURE.md) identifies Connectors as the entry point for external information. This document expands that role without introducing new connector architecture.

# Connector Responsibility

Connectors integrate external systems with Memovi.

Each connector translates external data into a normalized representation understood by the platform.

Every connector follows the same lifecycle regardless of provider.

# Ownership

Connectors own:

* Authentication with external systems
* Discovery
* Synchronization
* Import scheduling
* Data normalization

Connectors do not own:

* Search
* AI
* Memory
* Storage
* Embeddings

Connectors import knowledge. They do not interpret it.

# Supported Source Categories

Knowledge enters Memovi through connectors.

Examples include:

* Local files
* GitHub
* Gmail
* Slack
* Notion
* Obsidian
* Google Drive
* REST APIs
* Future integrations

The specific provider changes, but the architectural lifecycle remains the same.

# Acquisition

Each connector authenticates with its external system, discovers available content, and retrieves raw data.

Connectors are responsible only for acquisition and source-specific translation.

They should not enrich knowledge, generate summaries, create embeddings, own search indexes, or reason over imported content.

# Normalization

Every connector produces the same internal representation.

Regardless of origin, information becomes a normalized document.

A normalized document contains:

* Content
* Metadata
* Source information
* Content type
* Timestamps
* Ownership
* Processing state

After normalization, downstream systems no longer need connector-specific logic.

The platform operates on documents rather than external formats.

# Connector Events

Connector workflows may publish events when meaningful state changes occur.

Examples from the event model include:

* `ConnectorAuthorized`
* `ConnectorSynchronized`
* `ImportCompleted`

Connector synchronization can trigger document import and downstream processing.

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

See [`event-architecture.md`](event-architecture.md).

# Relationship to Documents

Documents are the entry point into the knowledge pipeline after connector data is normalized.

Connectors hand normalized data to the Documents domain. Documents manage document metadata, upload lifecycle, file storage references, versions, extraction requests, and processing state.

Connectors should not become responsible for document lifecycle after import.

See [`domains.md`](domains.md).

# Relationship to the Pipeline

Connectors participate in the Acquisition and Normalization stages.

They feed the shared pipeline rather than creating provider-specific downstream workflows.

Every supported connector ultimately converges into the same pipeline:

```text
External Source
        │
        ▼
Connector
        │
        ▼
Normalization
        │
        ▼
Document
        │
        ▼
Processing
        │
        ▼
Knowledge
```

See [`knowledge-processing-pipeline.md`](knowledge-processing-pipeline.md).

# Key Decisions

* Connectors integrate external systems with Memovi.
* Every connector produces normalized documents.
* Connectors own discovery, synchronization, import scheduling, and data normalization.
* Connectors do not own Search, AI, Memory, Storage, or Embeddings.
* Connector-specific logic ends at normalization.
* Downstream systems should not need to know where information originated.
* Future connectors extend the same framework rather than creating parallel workflows.

# Related Documents

* [`../../ARCHITECTURE.md`](../../ARCHITECTURE.md)
* [`domains.md`](domains.md)
* [`event-architecture.md`](event-architecture.md)
* [`knowledge-processing-pipeline.md`](knowledge-processing-pipeline.md)
* [`storage-architecture.md`](storage-architecture.md)
* [`scaling.md`](scaling.md)
