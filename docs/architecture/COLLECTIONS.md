# Knowledge Collections

# Purpose

This document defines Memovi's Knowledge Organization system: flat,
workspace-scoped Collections that group Documents, Knowledge, Conversations,
and Workflows for navigation and discoverability.

It also describes how **Tags** and **resource metadata** complement Collections
without replacing them.

# Scope

It covers collection philosophy, ownership, the organization model,
membership, metadata, activity, search integration, and the desktop
management surface — plus how Tags and lightweight resource metadata relate
to Collections.

It does **not** describe nested folders, AI-assisted organization, or changes
to the Documents ingestion pipeline.

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

## Tag philosophy

Tags complement Collections. They do not nest under Collections and do not
replace them.

* **Collections** are intentional groups (for example Work, Projects, Finance)
* **Tags** are lightweight, cross-cutting labels (for example AI, Meeting,
  Research) that can span many collections
* A resource may belong to many Collections and many Tags
* Favor simplicity over hierarchy — no tag trees in V1
* Deleting a tag removes assignments only; underlying content is unchanged

Tags live in Memory alongside Collections (`Tag`, `TagAssignment`), with the
same polymorphic member kinds (`document`, `knowledge`, `conversation`,
`workflow`).

## Metadata model

Lightweight **resource metadata** is Memory-owned and keyed by the same
polymorphic target identity as Collections/Tags:

* Title
* Description
* User notes

This avoids duplicating metadata columns across Documents, Intelligence, and
Automation. Collection-level name/description remain on the Collection itself;
per-resource title/description/notes use `/resource-metadata`.

# Ownership

Memory owns:

* Collection registration and persistence
* Membership references
* Collection metadata and summaries
* Recent organizational activity
* Collection HTTP API (`/collections`)
* Tags, tag assignments, tag suggestions/counts (`/tags`)
* Resource metadata (`/resource-metadata`)

Documents continue owning:

* Storage
* Processing
* Versioning

Memory continues owning:

* Knowledge extraction (separate from organization)

Search continues owning:

* Retrieval and ranking
* Optional collection and tag membership filters

Collections and Tags should never become an alternate knowledge store or bypass
ingestion.

# Pipeline Independence

```text
Connectors → Documents → Memory (knowledge) → Search → Intelligence
                              ↑
              Collections + Tags (organization)
```

Collections and Tags attach organizational references to existing resources.
Creating, renaming, or deleting either does not ingest, process, re-chunk, or
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
| `Tag` | Workspace-scoped cross-cutting label (unique name) |
| `TagAssignment` | Polymorphic assignment of a tag to a resource |
| `ResourceMetadata` | Title, description, and notes for a target resource |
| `TagService` | Tag CRUD, assign/unassign, suggest, search resolution |

# Member Kinds

A collection or tag may include:

* `document` — Documents domain ID
* `knowledge` — Memory knowledge item ID
* `conversation` — Intelligence conversation ID
* `workflow` — Automation workflow definition ID

Memberships and assignments are polymorphic references. The referenced resource
remains owned by its domain.

# Organization Model

* Collections belong to a Workspace
* An item may belong to one or more collections
* Memberships store `reason` (default: “Added by user”)
* Activity entries record create, rename, description updates, add, and remove
* Tags belong to a Workspace; names are unique within a workspace
  (case-insensitive)
* Tags may optionally carry a color and description
* Tag assignments do not store a reason (labels are intentionally lightweight)

# Collections metadata

Collections expose:

* Name
* Description
* Workspace
* Created / Updated
* Item counts (total and by kind)
* Recent activity

# Interaction with Search

Search continues to own retrieval. Organization integrates as optional filters:

* `GET /search?collection_id=…` resolves document and knowledge memberships
* `GET /search?tag_id=…` (repeatable) resolves tag assignments; **multiple tags
  use AND** (intersect document sets and knowledge sets)
* Collection and tag filters may be combined (intersection)
* Results are post-filtered to those member IDs
* Workspace, document type (`source_type` / `mime_type`), and existing filters
  remain available
* Tag suggestions and assignment counts live on `/tags` (not a separate search
  product)

Conversation and workflow memberships/assignments do not appear in
document/knowledge search results; they are organizational only for V1 search.

# Interaction with Collections

| Concern | Collections | Tags |
| --- | --- | --- |
| Purpose | Intentional groups | Cross-cutting labels |
| Hierarchy | Flat only | Flat only |
| Search | `collection_id` | repeated `tag_id` (AND) |
| Delete | Removes memberships | Removes assignments |
| Content | Unchanged | Unchanged |

Do not nest tags inside collections. Do not invent a third organization
framework.

# Desktop Experience

The desktop Collections page supports:

* List / create / rename / delete collections
* Add and remove members with an explicit reason
* Browse contents with collection-local search
* Statistics and recent activity
* Search page collection filter over the existing Search API

The desktop Tags page supports:

* Tag management (create / edit / delete)
* Assignments and inline-style chips
* Resource metadata editing (title, description, notes)
* Search page multi-tag filter chips

# Out of Scope (V1)

* Nested folders or collection hierarchies
* Tag hierarchies or automatic AI tagging
* Automatic membership from connectors
* Changing document or knowledge ownership through collections or tags

# Related Documents

* [`domains.md`](domains.md) — Memory owns Collections, Tags, Metadata
* [`knowledge-processing-pipeline.md`](knowledge-processing-pipeline.md)
* [`search-architecture.md`](search-architecture.md)
* [`DESKTOP_CLIENT.md`](DESKTOP_CLIENT.md)
* [`../STATUS.md`](../STATUS.md)
