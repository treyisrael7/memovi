# Knowledge Processing Pipeline

# Purpose

This document defines the canonical workflow that transforms raw information into structured, searchable knowledge.

# Scope

It covers pipeline philosophy, lifecycle stages, canonical flow, invariants, evolution, and failure recovery.

# Relationship to ARCHITECTURE.md

[`../ARCHITECTURE.md`](../ARCHITECTURE.md) summarizes the knowledge pipeline. This document is the focused reference for pipeline behavior and constraints.

# Pipeline Responsibility

The Knowledge Processing Pipeline is the core workflow of Memovi.

Its responsibility is to transform raw information into structured, searchable knowledge.

Regardless of where information originates, every source follows the same conceptual lifecycle. This allows the platform to process PDFs, source code, emails, chat conversations, notes, and future data sources using a unified architecture.

The pipeline separates ingestion from retrieval. Raw information enters the platform once. Knowledge may be retrieved thousands of times.

Optimizing ingestion enables every downstream capability.

# Pipeline Philosophy

The pipeline is designed around normalization.

External systems contain information in different formats. The rest of the platform should never need to understand those formats.

Instead, every source becomes a common internal representation before additional processing begins. Once normalized, downstream systems no longer need to know where information originated.

This dramatically reduces complexity across the platform.

# Pipeline Overview

Every piece of information follows the same lifecycle.

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
        │
        ▼
Indexing
        │
        ▼
Retrieval
        │
        ▼
Intelligence
```

Each stage has one responsibility.

Information should never skip stages unless explicitly justified.

# Stage 1 - Acquisition

Knowledge enters Memovi through a connector.

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

Each connector authenticates with its external system, discovers available content, and retrieves raw data.

Connectors are responsible only for acquisition. They should not interpret or enrich knowledge.

See [`connector-framework.md`](connector-framework.md).

# Stage 2 - Normalization

Every connector produces the same internal representation.

This is one of the most important architectural constraints within Memovi.

Regardless of origin, information becomes a normalized document.

A normalized document contains:

* Content
* Metadata
* Source information
* Content type
* Timestamps
* Ownership
* Processing state

After normalization, downstream systems no longer need connector-specific logic. The platform now operates on documents rather than external formats.

# Stage 3 - Storage

Normalized documents become durable platform assets.

Storage responsibilities include:

* Original content
* Metadata
* Version history
* Ownership
* Processing status

Storage is intentionally separated from indexing.

Documents may exist long before processing completes. This separation improves reliability while simplifying recovery.

See [`storage-architecture.md`](storage-architecture.md).

# Stage 4 - Processing

Document processing enriches raw information.

Processing occurs asynchronously through domain events.

Typical processing stages include:

* OCR
* Parsing
* Chunk generation
* Language detection
* Entity extraction
* Embedding generation
* AI summaries
* Metadata enrichment

Each processing step performs one responsibility before publishing another event.

Processing stages should remain independent.

See [`event-architecture.md`](event-architecture.md).

# Stage 5 - Knowledge Creation

Raw information becomes structured knowledge.

Examples include:

* Searchable passages
* Relationships
* Collections
* Tags
* Entities
* Version history

Future platform capabilities may also include:

* Knowledge graphs
* Temporal memory
* Semantic relationships
* Topic clustering

Knowledge creation is where information becomes useful beyond simple storage.

# Stage 6 - Indexing

Knowledge becomes retrievable.

Multiple indexes may exist simultaneously.

Examples include:

* Full-text index
* Vector index
* Metadata index
* Future graph index

Indexing prepares knowledge for efficient retrieval.

Indexes are derived artifacts. They can always be rebuilt from the underlying knowledge.

For this reason, indexes should never become the primary source of truth.

See [`search-architecture.md`](search-architecture.md).

# Stage 7 - Retrieval

Search retrieves relevant knowledge.

Retrieval may combine multiple techniques.

Examples include:

* Keyword search
* Vector similarity
* Metadata filtering
* Hybrid ranking
* Future graph traversal

Retrieval returns knowledge. It does not generate answers.

# Stage 8 - Intelligence

The Intelligence domain consumes retrieved knowledge.

Examples include:

* Chat
* Summaries
* Planning
* Tool execution
* Future autonomous workflows

The Intelligence layer reasons over retrieved knowledge without modifying the underlying platform.

Knowledge remains independent from the AI provider.

See [`intelligence-architecture.md`](intelligence-architecture.md).

# Canonical Processing Flow

```text
PDF
Slack
GitHub
Gmail
Notion
        │
        ▼
Connector
        │
        ▼
Normalized Document
        │
        ▼
Stored
        │
        ▼
DocumentUploaded Event
        │
        ▼
OCR
        │
        ▼
Chunking
        │
        ▼
Embeddings
        │
        ▼
Entity Extraction
        │
        ▼
Knowledge Created
        │
        ▼
Indexed
        │
        ▼
Search Ready
        │
        ▼
Available to Intelligence
```

Every supported connector ultimately converges into this same pipeline.

# Pipeline Invariants

The Knowledge Processing Pipeline follows these invariants:

* Every connector produces normalized documents.
* Every document enters durable storage before processing begins.
* Every processing stage performs one responsibility.
* Every processing stage publishes meaningful events.
* Indexes are rebuildable.
* Knowledge remains independent from AI providers.
* Retrieval never modifies knowledge.
* Intelligence consumes knowledge without owning it.

These invariants should remain true regardless of future implementation changes.

# Pipeline Evolution

The pipeline is intentionally extensible.

New capabilities should integrate by extending existing stages rather than introducing parallel workflows.

Examples include future OCR improvements, additional embedding providers, knowledge graph construction, topic clustering, automatic classification, relationship inference, and cross-document linking.

Every enhancement should strengthen the existing pipeline rather than replacing it.

# Failure Recovery

The pipeline is designed to recover gracefully from interruption.

Because every stage is event-driven and idempotent:

* Failed processing may be retried.
* Individual stages may be replayed.
* Indexes may be rebuilt.
* New enrichment algorithms may process historical knowledge.

The platform should never require re-importing information simply because downstream processing evolves.

Durable storage always precedes enrichment.

# Key Decisions

* Every source follows the same ingestion lifecycle.
* Normalization separates external systems from internal knowledge.
* Processing remains asynchronous and event-driven.
* Knowledge is created once and retrieved many times.
* Indexes are derived rather than authoritative.
* Intelligence consumes knowledge instead of producing it.
* Every pipeline stage owns one responsibility.
* Future capabilities extend the pipeline rather than bypassing it.
* The pipeline is the central architectural abstraction of Memovi.

# Related Documents

* [`../ARCHITECTURE.md`](../ARCHITECTURE.md)
* [`connector-framework.md`](connector-framework.md)
* [`event-architecture.md`](event-architecture.md)
* [`storage-architecture.md`](storage-architecture.md)
* [`search-architecture.md`](search-architecture.md)
* [`intelligence-architecture.md`](intelligence-architecture.md)
* [`scaling.md`](scaling.md)
