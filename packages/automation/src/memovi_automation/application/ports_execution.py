from typing import Protocol

from memovi_shared import WorkspaceId

from memovi_automation.domain.value_objects.authenticated_execution_context import (
    AuthenticatedExecutionContext,
)
from memovi_automation.domain.value_objects.capability_execution_request import (
    CapabilityExecutionRequest,
)
from memovi_automation.domain.value_objects.capability_execution_result import (
    CapabilityExecutionResult,
)
from memovi_automation.domain.value_objects.capability_execution_status import (
    CapabilityExecutionStatus,
)
from memovi_automation.domain.value_objects.execution_audit_entry import ExecutionAuditEntry
from memovi_automation.domain.value_objects.permission_mode import PermissionMode


class PermissionPolicyStore(Protocol):
    """Resolves and updates capability-specific permission modes."""

    def get(self, capability_id: str, *, workspace_id: WorkspaceId) -> PermissionMode:
        raise NotImplementedError

    def set(
        self,
        capability_id: str,
        mode: PermissionMode,
        *,
        workspace_id: WorkspaceId,
    ) -> None:
        raise NotImplementedError


class ExecutionAuditStore(Protocol):
    """Persists and lists capability execution audit entries."""

    def append(self, entry: ExecutionAuditEntry) -> None:
        raise NotImplementedError

    def list_for_workspace(
        self,
        *,
        workspace_id: WorkspaceId,
        limit: int = 100,
    ) -> tuple[ExecutionAuditEntry, ...]:
        raise NotImplementedError

    def list_for_execution(self, execution_id: str) -> tuple[ExecutionAuditEntry, ...]:
        raise NotImplementedError


class ExecutionStateStore(Protocol):
    """Persists live capability execution state and pending approval payloads.

    Cancellation tokens remain process-local. Pending request arguments are stored
    so approvals can resume after restart; audit entries continue to redact
    sensitive fields separately.
    """

    def save_result(self, result: CapabilityExecutionResult) -> None:
        raise NotImplementedError

    def get_result(self, execution_id: str) -> CapabilityExecutionResult | None:
        raise NotImplementedError

    def list_results(
        self,
        *,
        workspace_id: WorkspaceId,
        status: CapabilityExecutionStatus | None = None,
        conversation_id: str | None = None,
    ) -> tuple[CapabilityExecutionResult, ...]:
        raise NotImplementedError

    def save_pending(
        self,
        request: CapabilityExecutionRequest,
        auth_context: AuthenticatedExecutionContext,
    ) -> None:
        raise NotImplementedError

    def get_pending(
        self,
        execution_id: str,
    ) -> tuple[CapabilityExecutionRequest, AuthenticatedExecutionContext] | None:
        raise NotImplementedError

    def clear_pending(self, execution_id: str) -> None:
        raise NotImplementedError

    def fail_interrupted_executions(
        self,
        *,
        reason: str,
    ) -> tuple[CapabilityExecutionResult, ...]:
        """Mark in-flight ``executing`` rows failed after process restart."""
        raise NotImplementedError
