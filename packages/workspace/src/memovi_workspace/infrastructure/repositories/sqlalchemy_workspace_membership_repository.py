from datetime import UTC, datetime

from memovi_observability import timed_operation
from memovi_shared import WorkspaceId
from sqlalchemy.orm import Session as OrmSession

from memovi_workspace.domain.entities.workspace_membership import WorkspaceMembership
from memovi_workspace.infrastructure.persistence.models import WorkspaceMembershipRecord

_REPO = "SqlAlchemyWorkspaceMembershipRepository"


class SqlAlchemyWorkspaceMembershipRepository:
    def __init__(self, session: OrmSession) -> None:
        self._session = session

    def is_member(self, *, user_id: str, workspace_id: WorkspaceId) -> bool:
        return self.get(user_id=user_id, workspace_id=workspace_id) is not None

    def get(
        self,
        *,
        user_id: str,
        workspace_id: WorkspaceId,
    ) -> WorkspaceMembership | None:
        with timed_operation("repository.get", repository=_REPO):
            record = (
                self._session.query(WorkspaceMembershipRecord)
                .filter(
                    WorkspaceMembershipRecord.user_id == user_id.strip(),
                    WorkspaceMembershipRecord.workspace_id == workspace_id.value,
                )
                .one_or_none()
            )
            if record is None:
                return None
            return self._to_domain(record)

    def add(self, membership: WorkspaceMembership) -> None:
        with timed_operation("repository.add", repository=_REPO):
            existing = self.get(
                user_id=membership.user_id,
                workspace_id=membership.workspace_id,
            )
            if existing is not None:
                return
            self._session.add(
                WorkspaceMembershipRecord(
                    id=membership.id,
                    workspace_id=membership.workspace_id.value,
                    user_id=membership.user_id,
                    role=membership.role,
                    created_at=membership.created_at,
                )
            )

    def list_for_user(self, user_id: str) -> list[WorkspaceMembership]:
        with timed_operation("repository.list_for_user", repository=_REPO):
            records = (
                self._session.query(WorkspaceMembershipRecord)
                .filter(WorkspaceMembershipRecord.user_id == user_id.strip())
                .order_by(WorkspaceMembershipRecord.created_at.asc())
                .all()
            )
            return [self._to_domain(record) for record in records]

    def list_workspace_ids_for_user(self, user_id: str) -> list[WorkspaceId]:
        return [item.workspace_id for item in self.list_for_user(user_id)]

    def _to_domain(self, record: WorkspaceMembershipRecord) -> WorkspaceMembership:
        return WorkspaceMembership(
            id=record.id,
            workspace_id=WorkspaceId(record.workspace_id),
            user_id=record.user_id,
            role=record.role,
            created_at=_as_utc(record.created_at),
        )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
