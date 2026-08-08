# Memovi Connectors

Connector Framework for importing and synchronizing knowledge from external
systems into Memovi's Documents → Memory → Search → Intelligence pipeline.

## Ownership

This package owns:

* Connector contracts and registry
* Authentication references (not secret storage)
* Synchronization and change detection contracts
* Metadata normalization
* Connector health
* Scheduler foundation (no timed runs yet)
* Filesystem Connector (local folder registration and manual sync)

It does **not** own document storage, processing, knowledge extraction, search
indexing, or provider-specific product logic beyond acquire + normalize.

## Filesystem Connector

```python
from memovi_connectors import (
    ConnectorRegistry,
    ConnectorScheduler,
    FilesystemFolderService,
    AddFilesystemFolderCommand,
    SyncFilesystemFolderCommand,
    register_filesystem_connector,
    InMemoryDocumentImportPort,
    InMemoryFilesystemFolderRepository,
)
from memovi_shared import WorkspaceId

registry = ConnectorRegistry()
folders = InMemoryFilesystemFolderRepository()
document_import = InMemoryDocumentImportPort()
register_filesystem_connector(
    registry,
    document_import=document_import,
    folders=folders,
)
service = FilesystemFolderService(
    folders=folders,
    scheduler=ConnectorScheduler(registry),
)
folder = service.add_folder(
    AddFilesystemFolderCommand(
        workspace_id=WorkspaceId.default(),
        root_path="/path/to/notes",
    ),
)
result = service.sync_folder(
    SyncFilesystemFolderCommand(
        workspace_id=WorkspaceId.default(),
        folder_id=folder.id,
    ),
)
```

Production wiring lives in `apps/api` (`configure_connector_framework` +
request-scoped `DocumentsDocumentImportPort`).

See [`docs/architecture/CONNECTOR_FRAMEWORK.md`](../../docs/architecture/CONNECTOR_FRAMEWORK.md).
