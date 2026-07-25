"""WorkflowHistory — query prior workflow executions."""

from __future__ import annotations

from memovi_shared import WorkspaceId

from memovi_automation.application.ports_workflow import WorkflowHistoryStore
from memovi_automation.domain.value_objects.workflow import (
    WorkflowExecutionResult,
    WorkflowHistoryEntry,
)


class WorkflowHistory:
    """Read API over workflow execution history for clients and audit UX."""

    def __init__(self, store: WorkflowHistoryStore) -> None:
        self._store = store

    @property
    def store(self) -> WorkflowHistoryStore:
        return self._store

    def list(
        self,
        *,
        workspace_id: WorkspaceId,
        limit: int = 100,
    ) -> tuple[WorkflowHistoryEntry, ...]:
        return self._store.list_for_workspace(workspace_id=workspace_id, limit=limit)

    def get(
        self,
        instance_id: str,
        *,
        workspace_id: WorkspaceId,
    ) -> WorkflowHistoryEntry | None:
        return self._store.get(instance_id, workspace_id=workspace_id)

    def get_result(
        self,
        instance_id: str,
        *,
        workspace_id: WorkspaceId,
    ) -> WorkflowExecutionResult | None:
        return self._store.get_result(instance_id, workspace_id=workspace_id)
