"""In-memory capability execution state store (tests / local defaults)."""

from __future__ import annotations

from datetime import UTC, datetime
from threading import Lock

from memovi_shared import WorkspaceId

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


class InMemoryExecutionStateStore:
    """Process-local execution state used by unit tests."""

    def __init__(self) -> None:
        self._results: dict[str, CapabilityExecutionResult] = {}
        self._pending: dict[
            str, tuple[CapabilityExecutionRequest, AuthenticatedExecutionContext]
        ] = {}
        self._lock = Lock()

    def save_result(self, result: CapabilityExecutionResult) -> None:
        with self._lock:
            self._results[result.execution_id] = result
            if result.status is not CapabilityExecutionStatus.PENDING_APPROVAL:
                self._pending.pop(result.execution_id, None)

    def get_result(self, execution_id: str) -> CapabilityExecutionResult | None:
        with self._lock:
            return self._results.get(execution_id)

    def list_results(
        self,
        *,
        workspace_id: WorkspaceId,
        status: CapabilityExecutionStatus | None = None,
        conversation_id: str | None = None,
    ) -> tuple[CapabilityExecutionResult, ...]:
        with self._lock:
            values = list(self._results.values())
        filtered = [
            item
            for item in values
            if item.workspace_id == workspace_id.value
            and (status is None or item.status is status)
            and (conversation_id is None or item.conversation_id == conversation_id)
        ]
        filtered.sort(key=lambda item: item.updated_at)
        return tuple(filtered)

    def save_pending(
        self,
        request: CapabilityExecutionRequest,
        auth_context: AuthenticatedExecutionContext,
    ) -> None:
        with self._lock:
            self._pending[request.id] = (request, auth_context)

    def get_pending(
        self,
        execution_id: str,
    ) -> tuple[CapabilityExecutionRequest, AuthenticatedExecutionContext] | None:
        with self._lock:
            return self._pending.get(execution_id)

    def clear_pending(self, execution_id: str) -> None:
        with self._lock:
            self._pending.pop(execution_id, None)

    def fail_interrupted_executions(
        self,
        *,
        reason: str,
    ) -> tuple[CapabilityExecutionResult, ...]:
        now = datetime.now(UTC)
        recovered: list[CapabilityExecutionResult] = []
        with self._lock:
            for execution_id, current in list(self._results.items()):
                if current.status is not CapabilityExecutionStatus.EXECUTING:
                    continue
                failed = CapabilityExecutionResult(
                    execution_id=current.execution_id,
                    capability_id=current.capability_id,
                    workspace_id=current.workspace_id,
                    status=CapabilityExecutionStatus.FAILED,
                    permission_mode=current.permission_mode,
                    output=current.output,
                    error=CapabilityError(
                        code="interrupted_by_restart",
                        message=reason,
                    ),
                    duration=current.duration,
                    conversation_id=current.conversation_id,
                    correlation_id=current.correlation_id,
                    created_at=current.created_at,
                    updated_at=now,
                    metadata={**dict(current.metadata), "recovered": True},
                )
                self._results[execution_id] = failed
                recovered.append(failed)
        return tuple(recovered)
