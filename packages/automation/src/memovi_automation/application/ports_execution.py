from typing import Protocol

from memovi_shared import WorkspaceId

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
