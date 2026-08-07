from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from memovi_shared import WorkspaceId


@dataclass(frozen=True, slots=True)
class ConnectorAuthorized:
    """A connector instance completed authentication for a workspace."""

    connector_id: str
    workspace_id: WorkspaceId
    occurred_at: datetime

    @classmethod
    def create(
        cls,
        *,
        connector_id: str,
        workspace_id: WorkspaceId,
        occurred_at: datetime | None = None,
    ) -> ConnectorAuthorized:
        return cls(
            connector_id=connector_id.strip().lower(),
            workspace_id=workspace_id,
            occurred_at=occurred_at or datetime.now(tz=UTC),
        )


@dataclass(frozen=True, slots=True)
class ConnectorSynchronized:
    """A connector sync run completed (success or normalized failure)."""

    connector_id: str
    workspace_id: WorkspaceId
    sync_mode: str
    success: bool
    imported_count: int
    occurred_at: datetime

    @classmethod
    def create(
        cls,
        *,
        connector_id: str,
        workspace_id: WorkspaceId,
        sync_mode: str,
        success: bool,
        imported_count: int = 0,
        occurred_at: datetime | None = None,
    ) -> ConnectorSynchronized:
        return cls(
            connector_id=connector_id.strip().lower(),
            workspace_id=workspace_id,
            sync_mode=sync_mode.strip().lower(),
            success=success,
            imported_count=imported_count,
            occurred_at=occurred_at or datetime.now(tz=UTC),
        )


@dataclass(frozen=True, slots=True)
class ImportCompleted:
    """Normalized items from a connector were handed to Documents."""

    connector_id: str
    workspace_id: WorkspaceId
    document_ids: tuple[str, ...]
    occurred_at: datetime

    @classmethod
    def create(
        cls,
        *,
        connector_id: str,
        workspace_id: WorkspaceId,
        document_ids: tuple[str, ...] = (),
        occurred_at: datetime | None = None,
    ) -> ImportCompleted:
        return cls(
            connector_id=connector_id.strip().lower(),
            workspace_id=workspace_id,
            document_ids=document_ids,
            occurred_at=occurred_at or datetime.now(tz=UTC),
        )
