# Knowledge Collections

# Purpose

This document defines Memovi's Knowledge Organization system: flat,
workspace-scoped Collections that group Documents, Knowledge, Conversations,
and Workflows for navigation and discoverability.

# Scope

It covers collection philosophy, ownership, the organization model,
membership, metadata, activity, search integration, and the desktop
management surface.

It does **not** describe nested folders, tags (separate concern), AI-assisted
organization, or changes to the Documents ingestion pipeline.

# Relationship to ARCHITECTURE.md

[`../ARCHITECTURE.md`](../ARCHITECTURE.md) identifies Collections as part of
the Knowledge Platform. This document defines the implementation contracts in
`packages/memory` (`memovi-memory`) without inventing parallel storage for
knowledge content.

# Philosophy

Knowledge should be a navigable, user-owned asset rather than a flat bag of
extracted information.

Collections organize knowledge. They do not own it.

* Flat collections for V1 — no nested folders, no arbitrary hierarchies
* Powerful search over flat groups beats deep trees for early product use
* Membership is a reference plus a reason — users should always understand why
  an item appears in a collection
* Collections never duplicate Documents, Memory, Search, or Intelligence
  ownership

# Ownership

Memory owns:

* Collection registration and persistence
* Membership references
* Collection metadata and summaries
* Recent organizational activity
* Collection HTTP API (`/collections`)

Documents continue owning:

* Storage
* Processing
* Versioning

Memory continues owning:

* Knowledge extraction (separate from organization)

Search continues owning:

* Retrieval and ranking
* Optional collection membership filters

Collections should never become an alternate knowledge store or bypass
ingestion.

# Pipeline Independence

```text
Connectors → Documents → Memory (knowledge) → Search → Intelligence
                              ↑
                     Collections (organization)
```

Collections attach organizational memberships to existing resources. Creating,
renaming, or deleting a collection does not ingest, process, re-chunk, or
re-index content.

# Core Concepts

| Type | Role |
| --- | --- |
| `Collection` | Workspace-scoped organizational group |
| `CollectionMetadata` | Name and description |
| `CollectionMembership` | Reference to a member with kind, id, and reason |
| `CollectionSummary` | Item counts and recent activity |
| `CollectionRepository` | Persistence for collections, memberships, activity |
| `CollectionService` | Application use cases for management |

# Member Kinds

A collection may include:

* `document` — Documents domain ID
* `knowledge` — Memory knowledge item ID
* `conversation` — Intelligence conversation ID
* `workflow` — Automation workflow definition ID

Memberships are polymorphic references. The referenced resource remains owned
by its domain.

# Organization Model

* Collections belong to a Workspace
* An item may belong to one or more collections
* Memberships store `reason` (default: “Added by user”)
* Activity entries record create, rename, description updates, add, and remove

# Metadata

Collections expose:

* Name
* Description
* Workspace
* Created / Updated
* Item counts (total and by kind)
* Recent activity

# Search Integration

Search continues to own retrieval. Collections integrate as an optional filter:

* `GET /search?collection_id=…` resolves document and knowledge memberships
* Results are post-filtered to those member IDs
* Workspace, document type (`source_type` / `mime_type`), and existing filters
  remain available

Conversation and workflow memberships do not appear in document/knowledge
search results; they are organizational only for V1 search.

# Desktop Experience

The desktop Collections page supports:

* List / create / rename / delete collections
* Add and remove members with an explicit reason
* Browse contents with collection-local search
* Statistics and recent activity
* Search page collection filter over the existing Search API

# Out of Scope (V1)

* Nested folders or collection hierarchies
* Tags as a first-class system (planned separately)
* Automatic membership from connectors or AI
* Changing document or knowledge ownership through collections

# Related Documents

* [`domains.md`](domains.md) — Memory owns Collections
* [`knowledge-processing-pipeline.md`](knowledge-processing-pipeline.md)
* [`search-architecture.md`](search-architecture.md)
* [`DESKTOP_CLIENT.md`](DESKTOP_CLIENT.md)
* [`../STATUS.md`](../STATUS.md)
