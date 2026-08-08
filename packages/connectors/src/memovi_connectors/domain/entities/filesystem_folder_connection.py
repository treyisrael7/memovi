"""Filesystem folder connection entity for the Filesystem Connector."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from types import EllipsisType
from uuid import uuid4

from memovi_shared import WorkspaceId

from memovi_connectors.domain.exceptions import InvalidConnectorError

_SYNC_STATUSES = frozenset({"idle", "syncing", "healthy", "error"})


@dataclass(frozen=True, slots=True)
class FilesystemFolderConnection:
    """A registered local folder synchronized by the Filesystem Connector."""

    id: str
    workspace_id: WorkspaceId
    root_path: str
    display_name: str
    sync_cursor: str | None = None
    sync_status: str = "idle"
    last_error: str | None = None
    imported_document_count: int = 0
    last_synchronized_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        folder_id = self.id.strip()
        root_path = self.root_path.strip()
        display_name = self.display_name.strip()
        sync_status = self.sync_status.strip().lower()
        if not folder_id:
            raise InvalidConnectorError("Filesystem folder id is required.")
        if not isinstance(self.workspace_id, WorkspaceId):
            raise InvalidConnectorError("Filesystem folder workspace_id must be a WorkspaceId.")
        if not root_path:
            raise InvalidConnectorError("Filesystem folder root_path is required.")
        if not display_name:
            raise InvalidConnectorError("Filesystem folder display_name is required.")
        if sync_status not in _SYNC_STATUSES:
            allowed = ", ".join(sorted(_SYNC_STATUSES))
            raise InvalidConnectorError(
                f"Filesystem folder sync_status must be one of: {allowed}.",
            )
        if self.imported_document_count < 0:
            raise InvalidConnectorError("imported_document_count must be >= 0.")

        now = datetime.now(tz=UTC)
        created_at = self.created_at or now
        updated_at = self.updated_at or now
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=UTC)
        last_synchronized_at = self.last_synchronized_at
        if last_synchronized_at is not None and last_synchronized_at.tzinfo is None:
            last_synchronized_at = last_synchronized_at.replace(tzinfo=UTC)

        object.__setattr__(self, "id", folder_id)
        object.__setattr__(self, "root_path", root_path)
        object.__setattr__(self, "display_name", display_name)
        object.__setattr__(self, "sync_status", sync_status)
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "updated_at", updated_at)
        object.__setattr__(self, "last_synchronized_at", last_synchronized_at)

    @classmethod
    def create(
        cls,
        *,
        workspace_id: WorkspaceId,
        root_path: str,
        display_name: str | None = None,
        now: datetime | None = None,
    ) -> FilesystemFolderConnection:
        timestamp = now or datetime.now(tz=UTC)
        path = root_path.strip()
        fallback_name = path.rsplit("\\", maxsplit=1)[-1].rsplit("/", maxsplit=1)[-1]
        name = (display_name or fallback_name).strip()
        return cls(
            id=str(uuid4()),
            workspace_id=workspace_id,
            root_path=path,
            display_name=name or path,
            created_at=timestamp,
            updated_at=timestamp,
        )

    def with_sync_state(
        self,
        *,
        sync_cursor: str | None = None,
        sync_status: str | None = None,
        last_error: str | None | EllipsisType = ...,
        imported_document_count: int | None = None,
        last_synchronized_at: datetime | None | EllipsisType = ...,
        now: datetime | None = None,
    ) -> FilesystemFolderConnection:
        timestamp = now or datetime.now(tz=UTC)
        return FilesystemFolderConnection(
            id=self.id,
            workspace_id=self.workspace_id,
            root_path=self.root_path,
            display_name=self.display_name,
            sync_cursor=self.sync_cursor if sync_cursor is None else sync_cursor,
            sync_status=self.sync_status if sync_status is None else sync_status,
            last_error=self.last_error if last_error is ... else last_error,
            imported_document_count=(
                self.imported_document_count
                if imported_document_count is None
                else imported_document_count
            ),
            last_synchronized_at=(
                self.last_synchronized_at if last_synchronized_at is ... else last_synchronized_at
            ),
            created_at=self.created_at,
            updated_at=timestamp,
        )
