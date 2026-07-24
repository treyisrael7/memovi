# Knowledge Explorer

# Purpose

This document describes the Knowledge Explorer: Memovi's read-first inspection
surface for answering *"What does Memovi know?"* without asking the AI.

It covers transparency philosophy, the inspection workflow, knowledge navigation,
and the relationship model used by the desktop explorer.

# Relationship to ARCHITECTURE.md

Knowledge Explorer is a client presentation of Memory, Documents, and Search.
It does not own knowledge rules. Durable knowledge remains in the Knowledge
Platform; Intelligence remains a consumer of retrieval, not the source of truth.

# Transparency Philosophy

Trust comes from explainability.

Every inspectable knowledge item should make provenance visible:

* Which source document produced it
* When it was extracted / last updated
* Which workspace owns it
* How confident the platform is (when scores exist)

The explorer is intentionally read-only in this milestone. Users inspect and
navigate; they do not merge, delete, edit, or auto-correct knowledge here.

AI chat can cite knowledge, but Chat is not required to understand what Memovi
already stored. The explorer makes memory inspectable on its own.

# Current Knowledge Model

Today's materialized knowledge is document-derived:

```text
Document
  └─ Knowledge item (entity in explorer terms)
       └─ Chunks (passages)
```

Explorer labels map to that model:

| Explorer surface | Platform meaning |
| --- | --- |
| Entities | Materialized knowledge items |
| Concepts | Structural groupings by `source_type` and `mime_type` |
| Relationships | Provenance edges (`document_of`, `chunk_of`) |
| Sources | Documents in the active workspace |
| Search | Indexed retrieval over knowledge (`GET /search`) |

Semantic entity extraction, topic concepts, confidence scoring, and graph
visualization are future pipeline stages. Until then:

* `confidence` is returned as `null` and shown as "—"
* `entity_type` filters match `source_type` or `mime_type`
* Concepts are structural inspection projections, not NLP topics

# Inspection Workflow

```text
Desktop Knowledge page
  │
  ├─ Overview     GET /memory/dashboard
  ├─ Search       GET /search
  ├─ Concepts     GET /memory/concepts
  ├─ Entities     GET /memory + GET /memory/{id}
  ├─ Relationships GET /memory/relationships
  └─ Sources      GET /documents + GET /documents/{id}
         │
         └─ derived knowledge via GET /memory?document_id=…
```

Typical inspection path:

1. Open **Knowledge** in the desktop shell.
2. Review **Overview** counts for the active workspace.
3. Browse **Entities** or **Search** to find an item.
4. Inspect summary, source document, related concepts, sibling entities,
   confidence, and timestamps in the detail pane.
5. Follow provenance into **Sources** or **Relationships**.

Workspace isolation is enforced by the API through `X-Memovi-Workspace-Id`.
The desktop only forwards the active workspace selection; it never invents
ownership or filters across workspaces locally.

Search updates as the query and filters change (workspace, document, source /
entity type). Ranking stays on the backend.

# Knowledge Navigation

Users should be able to walk:

```text
Document
   ↓
Knowledge item (entity)
   ↓
Chunk / related concept
   ↓
Related knowledge from the same source
```

Navigation is list-and-detail, not a graph canvas. Selecting a relationship or
source jumps to the linked participant so provenance stays readable.

# Relationship Model

Relationships explain *why* knowledge exists.

Current relationship types:

| Type | Meaning |
| --- | --- |
| `document_of` | Knowledge item was materialized from a document |
| `chunk_of` | Chunk belongs to a knowledge item |

These are provenance facts, not inferred semantic links. Future relationship
inference can add typed semantic edges without changing the explorer's
read-only inspection contract.

# Desktop Boundaries

Desktop owns:

* Navigation among explorer sections
* Presentation of API payloads
* Session UI state (selection, filters, query text)

Desktop does not own:

* Materialization, chunking, indexing, or ranking
* Workspace ownership rules
* Entity extraction or confidence scoring
* Mutations to knowledge

All knowledge decisions remain behind Memory, Documents, and Search APIs.

# API Surface

| Endpoint | Role |
| --- | --- |
| `GET /memory/dashboard` | Workspace counts for overview |
| `GET /memory` | Entity list with optional filters |
| `GET /memory/{id}` | Entity detail with chunks |
| `GET /memory/by-document/{document_id}` | Knowledge for one source |
| `GET /memory/concepts` | Structural concept list |
| `GET /memory/relationships` | Provenance relationship list |
| `GET /documents` | Source document list |
| `GET /documents/{id}` | Source document detail |
| `GET /search` | Full-text / semantic / hybrid search |

# Out of Scope

* Graph visualization
* Manual editing, merging, deleting
* Auto-corrections
* Knowledge version history UI

# Related Documents

* [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — platform blueprint
* [`DESKTOP_CLIENT.md`](DESKTOP_CLIENT.md) — desktop shell and API consumption
* [`knowledge-processing-pipeline.md`](knowledge-processing-pipeline.md) — pipeline stages
* [`search-architecture.md`](search-architecture.md) — retrieval
* [`domains.md`](domains.md) — Memory / Search ownership
