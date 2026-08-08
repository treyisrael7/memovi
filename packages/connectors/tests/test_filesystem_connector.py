"""Tests for the Filesystem Connector."""

from __future__ import annotations

from pathlib import Path

import pytest
from memovi_connectors import (
    CONNECTOR_FILESYSTEM,
    ConnectorExecutionContext,
    ConnectorRegistry,
    ConnectorScheduler,
    FilesystemConnector,
    FilesystemFolderConnection,
    FilesystemFolderService,
    InMemoryDocumentImportPort,
    InMemoryFilesystemFolderRepository,
    AddFilesystemFolderCommand,
    SyncFilesystemFolderCommand,
    register_filesystem_connector,
)
from memovi_shared import WorkspaceId


@pytest.fixture
def workspace_id() -> WorkspaceId:
    return WorkspaceId.default()


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_filesystem_initial_sync_imports_supported_files(
    tmp_path: Path,
    workspace_id: WorkspaceId,
) -> None:
    _write_file(tmp_path / "notes.md", "# Hello")
    _write_file(tmp_path / "readme.txt", "plain")
    _write_file(tmp_path / "skip.bin", "binary")

    folders = InMemoryFilesystemFolderRepository()
    folder = FilesystemFolderConnection.create(
        workspace_id=workspace_id,
        root_path=str(tmp_path),
        display_name="Notes",
    )
    folders.add(folder)
    document_import = InMemoryDocumentImportPort()
    connector = FilesystemConnector(document_import=document_import, folders=folders)

    result = connector.sync(
        ConnectorExecutionContext.create(
            workspace_id=workspace_id,
            connector_id=CONNECTOR_FILESYSTEM,
            sync_mode="initial",
            metadata={"folder_id": folder.id},
        ),
    )

    assert result.success is True
    assert result.imported_count == 2
    assert len(document_import.imported) == 2
    names = {item.name for item in document_import.imported}
    assert names == {"notes.md", "readme.txt"}
    for item in document_import.imported:
        assert item.metadata.connector_id == CONNECTOR_FILESYSTEM
        assert item.metadata.extra["import_source"] == "filesystem"
        assert item.metadata.extra["folder_id"] == folder.id
        assert "external_path" in item.metadata.extra

    updated = folders.get_by_id(folder.id, workspace_id=workspace_id)
    assert updated is not None
    assert updated.sync_status == "healthy"
    assert updated.imported_document_count == 2
    assert updated.sync_cursor is not None
    assert updated.last_synchronized_at is not None


def test_filesystem_incremental_sync_detects_update_delete_and_rename(
    tmp_path: Path,
    workspace_id: WorkspaceId,
) -> None:
    first = tmp_path / "a.md"
    second = tmp_path / "keep.txt"
    _write_file(first, "one")
    _write_file(second, "keep")

    folders = InMemoryFilesystemFolderRepository()
    folder = FilesystemFolderConnection.create(
        workspace_id=workspace_id,
        root_path=str(tmp_path),
    )
    folders.add(folder)
    document_import = InMemoryDocumentImportPort()
    connector = FilesystemConnector(document_import=document_import, folders=folders)

    initial = connector.sync(
        ConnectorExecutionContext.create(
            workspace_id=workspace_id,
            connector_id=CONNECTOR_FILESYSTEM,
            sync_mode="initial",
            metadata={"folder_id": folder.id},
        ),
    )
    assert initial.success is True
    assert initial.imported_count == 2

    folder = folders.get_by_id(folder.id, workspace_id=workspace_id)
    assert folder is not None

    # Update, delete, and rename (content-hash match).
    _write_file(second, "keep-updated")
    first.unlink()
    renamed = tmp_path / "renamed.md"
    _write_file(renamed, "one")

    document_import.imported.clear()
    document_import.deleted_external_ids.clear()

    result = connector.sync(
        ConnectorExecutionContext.create(
            workspace_id=workspace_id,
            connector_id=CONNECTOR_FILESYSTEM,
            sync_mode="incremental",
            cursor=folder.sync_cursor,
            metadata={"folder_id": folder.id},
        ),
    )

    assert result.success is True
    assert result.updated_count == 1
    assert result.deleted_count >= 1
    assert result.imported_count >= 1
    assert any(item.name == "keep.txt" for item in document_import.imported)
    assert any(item.name == "renamed.md" for item in document_import.imported)
    assert any(
        external_id.endswith(":a.md")
        for external_id in document_import.deleted_external_ids
    )


def test_filesystem_folder_service_add_and_sync(
    tmp_path: Path,
    workspace_id: WorkspaceId,
) -> None:
    _write_file(tmp_path / "doc.md", "content")
    folders = InMemoryFilesystemFolderRepository()
    document_import = InMemoryDocumentImportPort()
    registry = ConnectorRegistry()
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
            workspace_id=workspace_id,
            root_path=str(tmp_path),
            display_name="Vault",
        ),
    )
    assert folder.display_name == "Vault"

    result = service.sync_folder(
        SyncFilesystemFolderCommand(workspace_id=workspace_id, folder_id=folder.id),
    )
    assert result.success is True
    assert result.imported_count == 1
    assert result.sync_mode == "initial"


def test_filesystem_rejects_missing_folder(
    workspace_id: WorkspaceId,
) -> None:
    connector = FilesystemConnector(
        document_import=InMemoryDocumentImportPort(),
        folders=InMemoryFilesystemFolderRepository(),
    )
    result = connector.sync(
        ConnectorExecutionContext.create(
            workspace_id=workspace_id,
            connector_id=CONNECTOR_FILESYSTEM,
            sync_mode="initial",
            metadata={"folder_id": "missing"},
        ),
    )
    assert result.success is False
    assert result.error_code == "folder_not_found"
