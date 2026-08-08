from datetime import UTC, datetime

from memovi_observability import timed_operation
from memovi_shared import WorkspaceId
from sqlalchemy.orm import Session as OrmSession

from memovi_workspace.domain.entities.workspace_membership_event import (
    WorkspaceMembershipEvent,
)
from memovi_workspace.infrastructure.persistence.models import (
    WorkspaceMembershipEventRecord,
)

_REPO = "SqlAlchemyWorkspaceMembershipEventRepository"


class SqlAlchemyWorkspaceMembershipEventRepository:
    def __init__(self, session: OrmSession) -> None:
        self._session = session

    def add(self, event: WorkspaceMembershipEvent) -> None:
        with timed_operation("repository.add", repository=_REPO):
            self._session.add(
                WorkspaceMembershipEventRecord(
                    id=event.id,
                    workspace_id=event.workspace_id.value,
                    event_type=event.event_type,
                    actor_user_id=event.actor_user_id,
                    target_user_id=event.target_user_id,
                    detail=event.detail,
                    occurred_at=event.occurred_at,
                )
            )

    def list_for_workspace(
        self,
        workspace_id: WorkspaceId,
        *,
        limit: int = 100,
    ) -> list[WorkspaceMembershipEvent]:
        with timed_operation("repository.list_for_workspace", repository=_REPO):
            records = (
                self._session.query(WorkspaceMembershipEventRecord)
                .filter(WorkspaceMembershipEventRecord.workspace_id == workspace_id.value)
                .order_by(WorkspaceMembershipEventRecord.occurred_at.desc())
                .limit(max(1, min(limit, 500)))
                .all()
            )
            return [self._to_domain(record) for record in records]

    def _to_domain(self, record: WorkspaceMembershipEventRecord) -> WorkspaceMembershipEvent:
        return WorkspaceMembershipEvent(
            id=record.id,
            workspace_id=WorkspaceId(record.workspace_id),
            event_type=record.event_type,
            actor_user_id=record.actor_user_id,
            target_user_id=record.target_user_id,
            occurred_at=_as_utc(record.occurred_at),
            detail=record.detail or "",
        )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
