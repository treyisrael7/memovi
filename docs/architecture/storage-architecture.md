# Storage Architecture

# Purpose

This document defines how knowledge is persisted, organized, indexed, cached, backed up, and versioned throughout Memovi.

# Scope

It covers PostgreSQL, pgvector, MinIO, Redis, data ownership, lifecycle, versioning, derived data, storage boundaries, backup strategy, and future evolution.

# Relationship to ARCHITECTURE.md

[`../ARCHITECTURE.md`](../ARCHITECTURE.md) summarizes the storage model. This document is the focused storage reference.

# Storage Philosophy

Storage is divided by responsibility rather than technology.

Each storage system exists because it solves a specific class of problems. No storage technology should become responsible for data outside its intended purpose.

Memovi follows these storage principles:

* Knowledge is stored once.
* Indexes are derived.
* Caches are disposable.
* Files remain immutable whenever practical.
* Every storage technology has a clearly defined responsibility.

If two systems become sources of truth for the same information, the architecture should be reconsidered.

# Storage Overview

The platform consists of four primary storage responsibilities.

```text
                    Storage Platform

        ┌──────────────┬──────────────┬──────────────┬──────────────┐
        ▼              ▼              ▼              ▼

 Relational Data   Vector Data      Object Data      Cache

 PostgreSQL        pgvector         MinIO           Redis
```

Although several technologies are involved, the platform maintains a single logical source of truth.

# Source of Truth

The authoritative source of truth for the platform is PostgreSQL.

Everything else is derived from information ultimately owned by PostgreSQL.

Examples:

* Embeddings are derived from documents.
* Search indexes are derived from knowledge.
* Cache entries are derived from queries.
* AI responses are derived from retrieval.

Only relational knowledge should require permanent durability.

This principle simplifies disaster recovery while preventing data divergence.

# Relational Storage

## Purpose

Relational storage manages the business state of Memovi.

It owns information that defines the platform.

Examples include:

* Users
* Documents
* Knowledge
* Metadata
* Collections
* Relationships
* Permissions
* Processing status
* Connector configuration

Relational storage represents business truth. Business rules should ultimately persist here.

## Why PostgreSQL?

PostgreSQL provides several architectural advantages:

* ACID transactions
* Strong consistency
* Mature indexing
* Rich query capabilities
* JSON support
* Extensions
* Excellent ecosystem

Rather than introducing multiple operational databases early, PostgreSQL provides enough flexibility to support most platform requirements.

Complexity should only increase when operational needs justify it.

# Vector Storage

## Purpose

Vector storage enables semantic retrieval.

Vectors represent derived knowledge rather than business entities.

Embeddings should always be reproducible from stored documents. Because vectors are derived, they should never become the primary source of truth.

## Why pgvector?

The architecture intentionally keeps vector storage within PostgreSQL.

Advantages include:

* Single operational database
* Transaction consistency
* Simplified backups
* Reduced operational overhead
* Shared metadata
* Easier development

Dedicated vector databases may be evaluated in the future if operational scale requires them.

The architecture intentionally avoids premature specialization.

# Object Storage

## Purpose

Object storage preserves original artifacts.

Examples include:

* PDFs
* Images
* Audio
* Video
* Attachments
* Original files

Raw content should remain immutable whenever practical.

Processing pipelines should derive knowledge from these artifacts rather than modifying them.

## Why MinIO?

MinIO provides an S3-compatible object storage system that supports self-hosted deployments.

The architecture depends only upon object storage semantics rather than a specific implementation.

Cloud object storage providers may be substituted without affecting business domains.

# Cache

## Purpose

Cache improves performance.

Cache never owns business state.

Examples include:

* Search results
* Authentication sessions
* Temporary processing state
* Rate limiting
* Connector synchronization progress

Every cache entry should be disposable.

Deleting the cache should never result in permanent data loss.

## Why Redis?

Redis provides:

* High-performance caching
* Distributed locks
* Pub/Sub
* Streams
* Temporary state

Redis accelerates the platform. It does not define the platform.

# Data Ownership

Each storage responsibility owns different categories of information.

| Storage | Owns |
| --- | --- |
| PostgreSQL | Business entities |
| pgvector | Semantic embeddings |
| MinIO | Original artifacts |
| Redis | Temporary operational state |

Ownership should remain exclusive.

Information should not exist permanently in multiple locations unless intentionally duplicated for performance.

# Data Lifecycle

Every piece of information progresses through the same lifecycle.

```text
External Source
        │
        ▼
Object Storage
        │
        ▼
Relational Metadata
        │
        ▼
Knowledge
        │
        ▼
Embeddings
        │
        ▼
Indexes
        │
        ▼
Cache
```

Each stage enriches existing information. No stage replaces previous knowledge.

# Versioning

Business entities may evolve. Original artifacts should not.

Whenever practical:

* Original files remain immutable.
* Knowledge supports version history.
* Embeddings may be regenerated.
* Search indexes may be rebuilt.

This approach enables future improvements without requiring users to re-import information.

# Derived Data

Several platform artifacts are intentionally considered disposable.

Examples include:

* Embeddings
* Search indexes
* Cache entries
* AI summaries, when optional

These artifacts can always be regenerated from authoritative knowledge.

This simplifies migrations and reduces long-term maintenance.

# Storage Boundaries

Business domains interact with repositories rather than storage technologies.

Examples:

* Authentication should not know PostgreSQL.
* Memory should not know pgvector.
* Documents should not know MinIO.

Instead, each domain communicates through repository interfaces defined by the architecture. Infrastructure provides the implementations.

This separation preserves domain independence.

# Backup Strategy

Only authoritative data requires comprehensive backup.

Examples include:

* PostgreSQL
* Object Storage

Derived data may be regenerated.

This significantly reduces backup complexity while improving disaster recovery.

# Future Evolution

Future operational requirements may introduce:

* Read replicas
* Distributed object storage
* Dedicated vector databases
* Cold storage
* Archival systems

These changes should remain implementation concerns. Business domains should remain unaffected.

The architecture intentionally isolates storage technologies behind stable abstractions.

# Key Decisions

* PostgreSQL is the authoritative source of truth.
* pgvector stores derived semantic representations rather than business entities.
* MinIO preserves immutable source artifacts.
* Redis stores temporary operational state only.
* Business domains remain independent from storage implementations.
* Derived data should always be reproducible.
* Storage responsibilities remain exclusive.
* Future storage technologies should replace implementations rather than architectural concepts.
* Operational complexity is introduced only when justified by scale.

# Related Documents

* [`../ARCHITECTURE.md`](../ARCHITECTURE.md)
* [`knowledge-processing-pipeline.md`](knowledge-processing-pipeline.md)
* [`search-architecture.md`](search-architecture.md)
* [`deployment.md`](deployment.md)
* [`scaling.md`](scaling.md)
