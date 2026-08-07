# Connector Framework

# Purpose

This document defines Memovi's Connector Framework: the architecture for
importing and synchronizing knowledge from external systems into the existing
Documents → Memory → Search → Intelligence pipeline.

# Scope

It covers connector responsibility, core interfaces, lifecycle,
synchronization, authentication references, metadata normalization, health,
scheduler foundation, ownership boundaries, and the relationship to Documents.

It does **not** describe concrete GitHub, Google Drive, Slack, or other provider
adapters, OAuth provider flows, or scheduled background runners.

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
does not run a background timer or worker loop.

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

After normalization, Memory, Search, and Intelligence must not require
connector-specific logic. Provenance remains available through normalized
metadata and `source_type="connector"` on Documents.

# Health

Each connector reports `ConnectorHealth`:

* Status (`healthy`, `degraded`, `unhealthy`, `unauthorized`, `unknown`,
  `unavailable`)
* Last synchronization time
* Errors
* Imported document count
* Pending changes

Registries expose `health(connector_id)` and `health_all()`.

# Relationship to Documents

Documents are the entry point into the knowledge pipeline after connector data
is normalized.

* Connectors produce `NormalizedImportItem`
* `DocumentImportPort` is implemented at the API composition root
* Documents own storage, versions, processing jobs, and lifecycle
* Connectors must not become a second document store

`SourceType` already allows `"connector"`. Upload remains `"upload"`.

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
* Attaches them to `app.state`
* Registers zero production connectors today

Future provider milestones add explicit `register_*_connector(registry, ...)`
calls here. `FakeConnector` exists for tests and local wiring only.

# Extending With a Provider

1. Implement the `Connector` protocol in `memovi_connectors` infrastructure (or
   a dedicated adapter module).
2. Normalize remote records into `NormalizedImportItem`.
3. Call `DocumentImportPort` for every importable change.
4. Register the connector at the composition root.
5. Do not add provider-specific branches to Memory, Search, or Intelligence.

# Key Decisions

* Connectors integrate external systems with Memovi.
* Every connector produces normalized documents.
* Documents remain the ingestion and storage owner.
* Credentials are referenced, never embedded in connector configuration.
* Incremental sync and delete detection are first-class contracts.
* Scheduling is a foundation only — no timed runners yet.
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
