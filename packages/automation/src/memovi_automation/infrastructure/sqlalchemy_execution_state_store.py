"""Durable SQLAlchemy capability execution state store."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, cast

from memovi_observability import get_metrics_recorder
from memovi_shared import WorkspaceId
from sqlalchemy.orm import Session as OrmSession

from memovi_automation.domain.value_objects.authenticated_execution_context import (
    AuthenticatedExecutionContext,
)
from memovi_automation.domain.value_objects.capability_error import CapabilityError
from memovi_automation.domain.value_objects.capability_execution_request import (
    CapabilityExecutionRequest,
)
from memovi_automation.domain.value_objects.capability_execution_result import (
    CapabilityExecutionResult,
)
from memovi_automation.domain.value_objects.capability_execution_status import (
    CapabilityExecutionStatus,
)
from memovi_automation.domain.value_objects.permission_mode import PermissionMode
from memovi_automation.infrastructure.execution_state_codec import (
    deserialize_auth_context,
    deserialize_error,
    deserialize_pending_request,
    json_safe,
    serialize_auth_context,
    serialize_error,
    serialize_pending_request,
)
from memovi_automation.infrastructure.persistence.models import CapabilityExecutionRecord

SessionFactory = Callable[[], OrmSession]

_TERMINAL = frozenset(
    {
        CapabilityExecutionStatus.COMPLETED.value,
        CapabilityExecutionStatus.FAILED.value,
        CapabilityExecutionStatus.CANCELLED.value,
    }
)


class SqlAlchemyExecutionStateStore:
    """Postgres/SQLite-backed live execution and pending-approval state."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def save_result(self, result: CapabilityExecutionResult) -> None:
        session = self._session_factory()
        try:
            record = session.get(CapabilityExecutionRecord, result.execution_id)
            user_id = _meta_str(result.metadata, "user_id")
            session_id = _meta_str(result.metadata, "session_id")
            source = _meta_str(result.metadata, "source") or "api"
            started_at = (
                result.created_at if result.status is CapabilityExecutionStatus.EXECUTING else None
            )
            completed_at = result.updated_at if result.status.value in _TERMINAL else None
            failure_details = None if result.error is None else result.error.message

            if record is None:
                record = CapabilityExecutionRecord(
                    execution_id=result.execution_id,
                    workspace_id=result.workspace_id,
                    user_id=user_id,
                    session_id=session_id,
                    capability_id=result.capability_id,
                    status=result.status.value,
                    permission_mode=result.permission_mode.value,
                    conversation_id=result.conversation_id,
                    correlation_id=result.correlation_id,
                    source=source,
                    duration=result.duration,
                    output=json_safe(result.output),
                    error=serialize_error(result.error),
                    metadata_json=cast(dict[str, Any], json_safe(dict(result.metadata))),
                    pending_request=None,
                    pending_auth=None,
                    created_at=result.created_at,
                    updated_at=result.updated_at,
                    started_at=started_at or result.created_at,
                    completed_at=completed_at,
                    failure_details=failure_details,
                )
                session.add(record)
            else:
                if (
                    record.started_at is None
                    and result.status is CapabilityExecutionStatus.EXECUTING
                ):
                    record.started_at = result.updated_at
                record.workspace_id = result.workspace_id
                record.user_id = user_id or record.user_id
                record.session_id = session_id or record.session_id
                record.capability_id = result.capability_id
                record.status = result.status.value
                record.permission_mode = result.permission_mode.value
                record.conversation_id = result.conversation_id
                record.correlation_id = result.correlation_id
                record.source = source
                record.duration = result.duration
                record.output = json_safe(result.output)
                record.error = serialize_error(result.error)
                record.metadata_json = cast(dict[str, Any], json_safe(dict(result.metadata)))
                record.updated_at = result.updated_at
                if result.status.value in _TERMINAL:
                    record.completed_at = result.updated_at
                    record.pending_request = None
                    record.pending_auth = None
                    record.failure_details = failure_details

            session.commit()
            self._record_status_metric(result.status)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_result(self, execution_id: str) -> CapabilityExecutionResult | None:
        session = self._session_factory()
        try:
            record = session.get(CapabilityExecutionRecord, execution_id)
            if record is None:
                return None
            return self._to_result(record)
        finally:
            session.close()

    def list_results(
        self,
        *,
        workspace_id: WorkspaceId,
        status: CapabilityExecutionStatus | None = None,
        conversation_id: str | None = None,
    ) -> tuple[CapabilityExecutionResult, ...]:
        session = self._session_factory()
        try:
            query = session.query(CapabilityExecutionRecord).filter(
                CapabilityExecutionRecord.workspace_id == workspace_id.value,
            )
            if status is not None:
                query = query.filter(CapabilityExecutionRecord.status == status.value)
            if conversation_id is not None:
                query = query.filter(
                    CapabilityExecutionRecord.conversation_id == conversation_id,
                )
            records = query.order_by(CapabilityExecutionRecord.updated_at.asc()).all()
            return tuple(self._to_result(record) for record in records)
        finally:
            session.close()

    def save_pending(
        self,
        request: CapabilityExecutionRequest,
        auth_context: AuthenticatedExecutionContext,
    ) -> None:
        session = self._session_factory()
        try:
            record = session.get(CapabilityExecutionRecord, request.id)
            if record is None:
                raise ValueError(
                    f"Cannot save pending payload for unknown execution '{request.id}'.",
                )
            record.pending_request = serialize_pending_request(request)
            record.pending_auth = serialize_auth_context(auth_context)
            record.user_id = auth_context.user_id
            record.session_id = auth_context.session_id
            record.updated_at = datetime.now(UTC)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_pending(
        self,
        execution_id: str,
    ) -> tuple[CapabilityExecutionRequest, AuthenticatedExecutionContext] | None:
        session = self._session_factory()
        try:
            record = session.get(CapabilityExecutionRecord, execution_id)
            if record is None or record.pending_request is None or record.pending_auth is None:
                return None
            return (
                deserialize_pending_request(record.pending_request),
                deserialize_auth_context(record.pending_auth),
            )
        finally:
            session.close()

    def clear_pending(self, execution_id: str) -> None:
        session = self._session_factory()
        try:
            record = session.get(CapabilityExecutionRecord, execution_id)
            if record is None:
                return
            record.pending_request = None
            record.pending_auth = None
            record.updated_at = datetime.now(UTC)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def fail_interrupted_executions(
        self,
        *,
        reason: str,
    ) -> tuple[CapabilityExecutionResult, ...]:
        now = datetime.now(UTC)
        session = self._session_factory()
        recovered: list[CapabilityExecutionResult] = []
        try:
            records = (
                session.query(CapabilityExecutionRecord)
                .filter(
                    CapabilityExecutionRecord.status == CapabilityExecutionStatus.EXECUTING.value,
                )
                .all()
            )
            for record in records:
                record.status = CapabilityExecutionStatus.FAILED.value
                record.error = serialize_error(
                    CapabilityError(code="interrupted_by_restart", message=reason),
                )
                record.failure_details = reason
                record.completed_at = now
                record.updated_at = now
                metadata = dict(record.metadata_json or {})
                metadata["recovered"] = True
                record.metadata_json = metadata
                record.pending_request = None
                record.pending_auth = None
                recovered.append(self._to_result(record))
            session.commit()
            if recovered:
                get_metrics_recorder().increment(
                    "memovi.capabilities.execution.recovered",
                    value=float(len(recovered)),
                )
            return tuple(recovered)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _to_result(self, record: CapabilityExecutionRecord) -> CapabilityExecutionResult:
        return CapabilityExecutionResult(
            execution_id=record.execution_id,
            capability_id=record.capability_id,
            workspace_id=record.workspace_id,
            status=CapabilityExecutionStatus(record.status),
            permission_mode=PermissionMode(record.permission_mode),
            output=record.output,
            error=deserialize_error(record.error),
            duration=record.duration,
            conversation_id=record.conversation_id,
            correlation_id=record.correlation_id,
            created_at=_as_utc(record.created_at),
            updated_at=_as_utc(record.updated_at),
            metadata=dict(record.metadata_json or {}),
        )

    def _record_status_metric(self, status: CapabilityExecutionStatus) -> None:
        metrics = get_metrics_recorder()
        if status is CapabilityExecutionStatus.COMPLETED:
            metrics.increment("memovi.capabilities.execution.completed")
        elif status is CapabilityExecutionStatus.FAILED:
            metrics.increment("memovi.capabilities.execution.failed")
        elif status is CapabilityExecutionStatus.CANCELLED:
            metrics.increment("memovi.capabilities.execution.cancelled")
        elif status is CapabilityExecutionStatus.PENDING_APPROVAL:
            metrics.increment("memovi.capabilities.execution.pending_approval")


def _meta_str(metadata: object, key: str) -> str | None:
    if not isinstance(metadata, dict):
        return None
    value = metadata.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
