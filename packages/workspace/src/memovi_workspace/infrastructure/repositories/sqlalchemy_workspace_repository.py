from datetime import UTC, datetime

from memovi_shared import WorkspaceId
from sqlalchemy.orm import Session as OrmSession

from memovi_workspace.domain.entities import Workspace
from memovi_workspace.infrastructure.persistence.models import WorkspaceRecord


class SqlAlchemyWorkspaceRepository:
    def __init__(self, session: OrmSession) -> None:
        self._session = session

    def get_by_id(self, workspace_id: WorkspaceId) -> Workspace | None:
        record = self._session.get(WorkspaceRecord, workspace_id.value)
        if record is None:
            return None
        return self._to_domain(record)

    def add(self, workspace: Workspace) -> None:
        self._session.add(
            WorkspaceRecord(
                id=workspace.id.value,
                name=workspace.name,
                created_at=workspace.created_at,
            )
        )

    def list_all(self) -> list[Workspace]:
        records = (
            self._session.query(WorkspaceRecord).order_by(WorkspaceRecord.created_at.asc()).all()
        )
        return [self._to_domain(record) for record in records]

    def _to_domain(self, record: WorkspaceRecord) -> Workspace:
        return Workspace(
            id=WorkspaceId(record.id),
            name=record.name,
            created_at=_as_utc(record.created_at),
        )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
