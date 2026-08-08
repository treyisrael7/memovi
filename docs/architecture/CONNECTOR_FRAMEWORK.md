# Connector Framework

# Purpose

This document defines Memovi's Connector Framework: the architecture for
importing and synchronizing knowledge from external systems into the existing
Documents → Memory → Search → Intelligence pipeline.

# Scope

It covers connector responsibility, core interfaces, lifecycle,
synchronization, authentication references, metadata normalization, health,
scheduler foundation, ownership boundaries, the relationship to Documents, and
the production **Filesystem Connector**.

It does **not** describe concrete GitHub, Google Drive, Slack, or Notion
adapters, OAuth provider flows, filesystem watchers, or scheduled background
runners.

# Relationship to ARCHITECTURE.md

[`../ARCHITECTURE.md`](../ARCHITECTURE.md) identifies Connectors as the entry
point for external information. This document defines the implementation
contracts in `packages/connectors` (`memovi-connectors`) without inventing a
parallel knowledge architecture.

The previous kebab-case note [`connector-framework.md`](connector-framework.md)
redirects here.

# Why Connectors Exist

External systems become additional knowledge sources.

Examples:

* GitHub
* Google Drive
* Slack
* Gmail
* Notion
* Obsidian
* Filesystem
* Cloud storage

Connectors import content. They do not interpret it.

The Documents → Memory → Search → Intelligence pipeline remains the single
source of truth after normalization.

# Pipeline Position

```text
Conversation
    │
    ▼
Intelligence
    │
    ▼
Knowledge (Memory)
    │
    ▼
Documents
    │
    ▼
Connector Framework
    │
    ▼
External System
```

Connectors feed Documents. Documents continue owning ingestion, storage,
versioning, and processing. Memory owns knowledge extraction. Search owns
indexing.

# Ownership

Connectors own:

* Connector registration and discovery
* Authentication abstraction (credential references, not secret storage)
* Discovery against external systems
* Incremental synchronization and change detection
* Metadata normalization into a provider-neutral shape
* Connector health reporting
* Import scheduling foundation (registration only today)
* Filesystem folder registration and manual sync

Connectors do not own:

* Document storage or object storage
* Processing / OCR / chunking
* Versioning
* Knowledge extraction (Memory)
* Search indexes or embeddings
* AI reasoning

Connectors import knowledge. They do not interpret it.

# Package Ownership

`packages/connectors` (`memovi-connectors`) owns:

* `Connector` protocol
* `ConnectorRegistry`
* `ConnectorConfiguration` / `AuthCredentialRef`
* `ConnectorExecutionContext`
* `ConnectorResult`
* `ConnectorMetadata`
* `ConnectorHealth`
* `NormalizedSourceMetadata` / `NormalizedImportItem`
* `DocumentImportPort`
* `ConnectorScheduler` foundation
* Domain events: `ConnectorAuthorized`, `ConnectorSynchronized`, `ImportCompleted`
* Production `FilesystemConnector` + filesystem folder connections

Concrete provider adapters register explicitly at the composition root. There is
no reflection and no global registry singleton.

# Core Interfaces

| Type | Role |
| --- | --- |
| `Connector` | Protocol for acquire + normalize + sync |
| `ConnectorRegistry` | Explicit registration, lookup, metadata, health |
| `ConnectorConfiguration` | Enabled flag, auth ref, sync cursor, options (no secrets) |
| `AuthCredentialRef` | Points at env/secret-store credentials without embedding values |
| `ConnectorExecutionContext` | Workspace, sync mode, cursor, correlation |
| `ConnectorResult` | Sync outcome with counts, errors, normalized items |
| `ConnectorMetadata` | Stable id, display name, source category, auth methods |
| `ConnectorHealth` | Status, last sync, errors, imported count, pending changes |
| `NormalizedSourceMetadata` | Provider-neutral source metadata for Documents |
| `NormalizedImportItem` | Content + metadata handed to Documents |
| `DocumentImportPort` | Composition-root handoff into Documents ingest/create |
| `ConnectorScheduler` | Schedule registration + on-demand `run_now` (no cron yet) |

# Connector Lifecycle

```text
Register connector type
        │
        ▼
Configure instance (auth ref, options)
        │
        ▼
Authorize / resolve credentials
        │
        ▼
Discover remote content
        │
        ▼
Sync (initial | incremental)
        │
        ▼
Normalize → NormalizedImportItem
        │
        ▼
DocumentImportPort → Documents
        │
        ▼
Documents processing → Memory → Search
```

1. **Register** — composition root calls `ConnectorRegistry.register(...)`.
2. **Configure** — settings carry `AuthCredentialRef`, never raw tokens.
3. **Authorize** — infrastructure resolves the credential ref; may publish
   `ConnectorAuthorized`.
4. **Sync** — `Connector.sync(context)` runs initial or incremental import.
5. **Normalize** — external records become `NormalizedImportItem` values.
6. **Handoff** — `DocumentImportPort.import_item(...)` creates/updates Documents
   with `source_type="connector"`.
7. **Downstream** — existing document processing, memory extraction, and search
   indexing proceed unchanged.

# Synchronization Model

Supported sync modes:

| Mode | Meaning |
| --- | --- |
| `initial` | First import / full crawl for the configured scope |
| `incremental` | Resume from `cursor` / last sync watermark |

Change kinds on normalized items:

| `change_kind` | Meaning |
| --- | --- |
| `upsert` | Create or update document content |
| `delete` | Remote content removed; Documents should tombstone/remove |
| `metadata_only` | Metadata changed without content rewrite |

The framework supports:

* Initial import
* Incremental sync
* Deleted content detection
* Metadata updates

**Scheduled synchronization is not implemented yet.** `ConnectorScheduler`
accepts `ConnectorScheduleSpec` values and can execute `run_now(...)`, but it
does not run a background timer or worker loop. Manual sync is the supported
path for the Filesystem Connector today.

# Authentication

Credentials remain isolated from connector implementations.

`AuthCredentialRef` supports future methods:

* OAuth
* API keys
* Personal access tokens
* Service accounts
* `none` (local / unauthenticated sources)

Configuration stores **references** (`secret_env`, `secret_ref`), not secret
values. Provider-specific OAuth dances and secret stores are composition-root /
infrastructure concerns outside this foundation.

# Metadata Normalization

Every connector produces the same internal representation before Documents.

`NormalizedSourceMetadata` carries:

* Source
* Owner
* Created / modified timestamps
* Tags
* External ID
* Connector ID
* Workspace
* Extra provider-neutral fields (for example `external_path`, `import_source`,
  `file_type`)

After normalization, Memory, Search, and Intelligence must not require
connector-specific logic. Provenance remains available through normalized
metadata and Documents fields:

* `source_type="connector"`
* `connector_id`
* `external_id` (stable identity for upsert/delete)
* `external_path` (display / provenance path when available)

# Health

Each connector reports `ConnectorHealth`:

* Status (`healthy`, `degraded`, `unhealthy`, `unauthorized`, `unknown`,
  `unavailable`)
* Last synchronization time
* Errors
* Imported document count
* Pending changes

Registries expose `health(connector_id)` and `health_all()`.

Filesystem folder connections also track per-folder sync status, last sync
time, imported count, and last error for the desktop Connectors page.

# Relationship to Documents

Documents are the entry point into the knowledge pipeline after connector data
is normalized.

* Connectors produce `NormalizedImportItem`
* `DocumentImportPort` is implemented at the API composition root
  (`DocumentsDocumentImportPort`) and calls `IngestConnectorDocument`
* Documents own storage, versions, processing jobs, and lifecycle
* Connectors must not become a second document store

`SourceType` allows `"connector"`. Upload remains `"upload"`. Connector upserts
create a first version or append a new version and enqueue the existing
processing pipeline. Deletes remove the matching document by
`(workspace_id, connector_id, external_id)`.

# Filesystem Connector

The Filesystem Connector (`connector_id=filesystem`) is the first production
connector on this framework. It proves local-folder import without introducing
a second ingestion architecture.

## Responsibilities

* Register a local folder for a workspace
* Initial import of supported files (`.txt`, `.md` / `.markdown`, `.pdf`)
* Incremental sync from a JSON path inventory cursor (size, mtime, sha256)
* File updates (content change → upsert / new document version)
* File deletions (path vanished → delete change kind)
* Practical rename detection (vanished + appeared paths matched by content hash
  within one sync pass → delete old identity + upsert new path)
* Metadata normalization into `NormalizedImportItem`

## Synchronization lifecycle

```text
Add folder (API / desktop)
        │
        ▼
Manual Sync Now
        │
        ▼
Resolve folder + root path
        │
        ▼
Scan supported files under root
        │
        ▼
Diff against sync_cursor
  ├── appeared  → upsert
  ├── shared+changed → upsert
  ├── vanished  → delete
  └── rename (hash match) → delete + upsert
        │
        ▼
DocumentImportPort per item
        │
        ▼
Persist new cursor + folder health
        │
        ▼
Documents processing → Memory → Search
```

Sync modes:

* First sync for a folder uses `initial` when no cursor exists
* Later manual syncs use `incremental` unless the client requests `initial`

Out of scope for this milestone: filesystem watchers and scheduled sync.

## Metadata mapping

| Source field | Normalized / Documents target |
| --- | --- |
| Connector type | `connector_id=filesystem` |
| Folder + relative path | `external_id="{folder_id}:{relative_path}"` |
| Absolute path | `extra.external_path` → Documents `external_path` |
| Relative path | `extra.relative_path` |
| MIME / extension | `mime_type`, `extra.file_type` |
| File created / modified | `created_at` / `modified_at` |
| Workspace | `workspace_id` |
| Import source | `extra.import_source="filesystem"`, `source=filesystem://…` |

## API surface

* `GET /connectors` — registered connector metadata
* `GET /connectors/health` — connector-type health
* `GET /connectors/filesystem/folders` — connected folders for the workspace
* `POST /connectors/filesystem/folders` — add folder (`root_path`, optional
  `display_name`)
* `DELETE /connectors/filesystem/folders/{id}` — remove folder registration
* `POST /connectors/filesystem/folders/{id}/sync` — manual sync

## Desktop

The Connectors page supports add folder, remove folder, manual sync, last sync
time, sync status, imported document count, and error state. It does not
redesign navigation beyond adding the Connectors surface.

# Events

Meaningful connector facts may publish:

* `ConnectorAuthorized`
* `ConnectorSynchronized`
* `ImportCompleted`

These describe domain facts, not commands for Documents. Sync completion can
trigger document import and the existing downstream pipeline.

# Composition Root

`apps/api` wires the framework via `configure_connector_framework(app)`:

* Creates `ConnectorRegistry` and `ConnectorScheduler`
* Registers the production `FilesystemConnector`
* Attaches them to `app.state`
* Binds request-scoped `DocumentImportPort` + folder repository during
  filesystem sync via `FilesystemConnector.configure_runtime(...)`

`FakeConnector` remains for tests and local wiring only.

# Extending With a Future Provider

Future GitHub, Google Drive, Slack, and Notion connectors should:

1. Implement the `Connector` protocol in `memovi_connectors` infrastructure (or
   a dedicated adapter module).
2. Normalize remote records into `NormalizedImportItem` with stable
   `external_id` values.
3. Call `DocumentImportPort` for every importable change.
4. Register the connector at the composition root.
5. Reuse Documents provenance (`connector_id`, `external_id`, `external_path`)
   rather than inventing provider-specific document stores.
6. Do not add provider-specific branches to Memory, Search, or Intelligence.

Prefer proving the shared contracts over provider-specific product features.

# Key Decisions

* Connectors integrate external systems with Memovi.
* Every connector produces normalized documents.
* Documents remain the ingestion and storage owner.
* Credentials are referenced, never embedded in connector configuration.
* Incremental sync and delete detection are first-class contracts.
* Scheduling is a foundation only — no timed runners yet.
* The Filesystem Connector is the reference production adapter for the
  framework.
* Future connectors extend this framework rather than creating parallel
  workflows.

# Related Documents

* [`../ARCHITECTURE.md`](../ARCHITECTURE.md)
* [`domains.md`](domains.md)
* [`event-architecture.md`](event-architecture.md)
* [`knowledge-processing-pipeline.md`](knowledge-processing-pipeline.md)
* [`storage-architecture.md`](storage-architecture.md)
* [`scaling.md`](scaling.md)
* [`../ROADMAP.md`](../ROADMAP.md) — Connector Philosophy
