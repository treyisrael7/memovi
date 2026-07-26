from collections.abc import Callable
from datetime import UTC, datetime

from memovi_shared import WorkspaceId
from sqlalchemy.orm import Session as OrmSession

from memovi_automation.domain.value_objects.capability_execution_status import (
    CapabilityExecutionStatus,
)
from memovi_automation.domain.value_objects.execution_audit_entry import ExecutionAuditEntry
from memovi_automation.domain.value_objects.permission_mode import PermissionMode
from memovi_automation.infrastructure.persistence.models import ExecutionAuditRecord

SessionFactory = Callable[[], OrmSession]


class SqlAlchemyExecutionAuditStore:
    """Durable capability execution audit trail."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def append(self, entry: ExecutionAuditEntry) -> None:
        operation = entry.operation
        if operation is None:
            raw = entry.result_summary.get("operation")
            operation = raw if isinstance(raw, str) else None
        session = self._session_factory()
        try:
            session.add(
                ExecutionAuditRecord(
                    id=entry.id,
                    execution_id=entry.execution_id,
                    workspace_id=entry.workspace_id,
                    user_id=entry.user_id,
                    capability_id=entry.capability_id,
                    operation=operation,
                    status=entry.status.value,
                    permission_mode=entry.permission_mode.value,
                    arguments=dict(entry.arguments),
                    result_summary=dict(entry.result_summary),
                    duration=entry.duration,
                    timestamp=entry.timestamp,
                    conversation_id=entry.conversation_id,
                    correlation_id=entry.correlation_id,
                    source=entry.source,
                )
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_for_workspace(
        self,
        *,
        workspace_id: WorkspaceId,
        limit: int = 100,
    ) -> tuple[ExecutionAuditEntry, ...]:
        session = self._session_factory()
        try:
            records = (
                session.query(ExecutionAuditRecord)
                .filter(ExecutionAuditRecord.workspace_id == workspace_id.value)
                .order_by(ExecutionAuditRecord.timestamp.asc())
                .all()
            )
            return tuple(self._to_domain(record) for record in records[-limit:])
        finally:
            session.close()

    def list_for_execution(self, execution_id: str) -> tuple[ExecutionAuditEntry, ...]:
        session = self._session_factory()
        try:
            records = (
                session.query(ExecutionAuditRecord)
                .filter(ExecutionAuditRecord.execution_id == execution_id)
                .order_by(ExecutionAuditRecord.timestamp.asc())
                .all()
            )
            return tuple(self._to_domain(record) for record in records)
        finally:
            session.close()

    def _to_domain(self, record: ExecutionAuditRecord) -> ExecutionAuditEntry:
        return ExecutionAuditEntry(
            id=record.id,
            execution_id=record.execution_id,
            workspace_id=record.workspace_id,
            capability_id=record.capability_id,
            status=CapabilityExecutionStatus(record.status),
            permission_mode=PermissionMode(record.permission_mode),
            arguments=dict(record.arguments or {}),
            result_summary=dict(record.result_summary or {}),
            duration=record.duration,
            timestamp=_as_utc(record.timestamp),
            conversation_id=record.conversation_id,
            correlation_id=record.correlation_id,
            source=record.source,
            user_id=record.user_id,
            operation=record.operation,
        )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
