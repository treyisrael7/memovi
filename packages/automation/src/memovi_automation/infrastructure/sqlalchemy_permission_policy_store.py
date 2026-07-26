from collections.abc import Callable
from datetime import UTC, datetime

from memovi_shared import WorkspaceId
from sqlalchemy.orm import Session as OrmSession

from memovi_automation.domain.value_objects.permission_mode import PermissionMode
from memovi_automation.infrastructure.persistence.models import (
    CapabilityPermissionPolicyRecord,
)

SessionFactory = Callable[[], OrmSession]


class SqlAlchemyPermissionPolicyStore:
    """Durable workspace-scoped capability permission policies."""

    def __init__(
        self,
        session_factory: SessionFactory,
        *,
        default_mode: PermissionMode = PermissionMode.ASK_EVERY_TIME,
    ) -> None:
        self._session_factory = session_factory
        self._default_mode = default_mode

    def get(self, capability_id: str, *, workspace_id: WorkspaceId) -> PermissionMode:
        session = self._session_factory()
        try:
            record = session.get(
                CapabilityPermissionPolicyRecord,
                {"workspace_id": workspace_id.value, "capability_id": capability_id},
            )
            if record is None:
                return self._default_mode
            return PermissionMode(record.permission_mode)
        finally:
            session.close()

    def set(
        self,
        capability_id: str,
        mode: PermissionMode,
        *,
        workspace_id: WorkspaceId,
    ) -> None:
        session = self._session_factory()
        try:
            record = session.get(
                CapabilityPermissionPolicyRecord,
                {"workspace_id": workspace_id.value, "capability_id": capability_id},
            )
            now = datetime.now(UTC)
            if record is None:
                session.add(
                    CapabilityPermissionPolicyRecord(
                        workspace_id=workspace_id.value,
                        capability_id=capability_id,
                        permission_mode=mode.value,
                        updated_at=now,
                    )
                )
            else:
                record.permission_mode = mode.value
                record.updated_at = now
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
