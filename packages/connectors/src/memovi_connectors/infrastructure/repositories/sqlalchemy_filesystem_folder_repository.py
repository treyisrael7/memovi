"""SQLAlchemy repository for filesystem folder connections."""

from __future__ import annotations

from datetime import UTC, datetime

from memovi_shared import WorkspaceId
from sqlalchemy.orm import Session as OrmSession

from memovi_connectors.domain.entities import FilesystemFolderConnection
from memovi_connectors.infrastructure.persistence.models import FilesystemFolderRecord


class SqlAlchemyFilesystemFolderRepository:
    def __init__(self, session: OrmSession) -> None:
        self._session = session

    def get_by_id(
        self,
        folder_id: str,
        *,
        workspace_id: WorkspaceId,
    ) -> FilesystemFolderConnection | None:
        record = (
            self._session.query(FilesystemFolderRecord)
            .filter(
                FilesystemFolderRecord.id == folder_id,
                FilesystemFolderRecord.workspace_id == workspace_id.value,
            )
            .one_or_none()
        )
        if record is None:
            return None
        return self._to_domain(record)

    def list_by_workspace(self, *, workspace_id: WorkspaceId) -> list[FilesystemFolderConnection]:
        records = (
            self._session.query(FilesystemFolderRecord)
            .filter(FilesystemFolderRecord.workspace_id == workspace_id.value)
            .order_by(FilesystemFolderRecord.created_at.asc())
            .all()
        )
        return [self._to_domain(record) for record in records]

    def add(self, folder: FilesystemFolderConnection) -> None:
        self._session.add(
            FilesystemFolderRecord(
                id=folder.id,
                workspace_id=folder.workspace_id.value,
                root_path=folder.root_path,
                display_name=folder.display_name,
                sync_cursor=folder.sync_cursor,
                sync_status=folder.sync_status,
                last_error=folder.last_error,
                imported_document_count=folder.imported_document_count,
                last_synchronized_at=folder.last_synchronized_at,
                created_at=folder.created_at or datetime.now(tz=UTC),
                updated_at=folder.updated_at or datetime.now(tz=UTC),
            )
        )

    def save(self, folder: FilesystemFolderConnection) -> None:
        record = self._session.get(FilesystemFolderRecord, folder.id)
        if record is None:
            raise ValueError(f"Filesystem folder '{folder.id}' was not found.")
        record.root_path = folder.root_path
        record.display_name = folder.display_name
        record.sync_cursor = folder.sync_cursor
        record.sync_status = folder.sync_status
        record.last_error = folder.last_error
        record.imported_document_count = folder.imported_document_count
        record.last_synchronized_at = folder.last_synchronized_at
        record.updated_at = folder.updated_at or datetime.now(tz=UTC)

    def delete(self, folder_id: str, *, workspace_id: WorkspaceId) -> None:
        record = (
            self._session.query(FilesystemFolderRecord)
            .filter(
                FilesystemFolderRecord.id == folder_id,
                FilesystemFolderRecord.workspace_id == workspace_id.value,
            )
            .one_or_none()
        )
        if record is not None:
            self._session.delete(record)

    def _to_domain(self, record: FilesystemFolderRecord) -> FilesystemFolderConnection:
        return FilesystemFolderConnection(
            id=record.id,
            workspace_id=WorkspaceId(record.workspace_id),
            root_path=record.root_path,
            display_name=record.display_name,
            sync_cursor=record.sync_cursor,
            sync_status=record.sync_status,
            last_error=record.last_error,
            imported_document_count=record.imported_document_count,
            last_synchronized_at=_as_utc(record.last_synchronized_at),
            created_at=_as_utc(record.created_at),
            updated_at=_as_utc(record.updated_at),
        )


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
