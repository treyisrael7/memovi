"""Ports for workflow library and history storage."""

from __future__ import annotations

from typing import Protocol

from memovi_shared import WorkspaceId

from memovi_automation.domain.value_objects.workflow import (
    WorkflowDefinition,
    WorkflowExecutionResult,
    WorkflowHistoryEntry,
)


class WorkflowLibrary(Protocol):
    """Catalog of reusable workflow definitions."""

    def get(self, workflow_id: str) -> WorkflowDefinition:
        raise NotImplementedError

    def list(self) -> tuple[WorkflowDefinition, ...]:
        raise NotImplementedError

    def register(self, definition: WorkflowDefinition) -> None:
        raise NotImplementedError


class WorkflowHistoryStore(Protocol):
    """Durable-or-process-local history of workflow executions."""

    def append(self, entry: WorkflowHistoryEntry) -> None:
        raise NotImplementedError

    def list_for_workspace(
        self,
        *,
        workspace_id: WorkspaceId,
        limit: int = 100,
    ) -> tuple[WorkflowHistoryEntry, ...]:
        raise NotImplementedError

    def get(
        self,
        instance_id: str,
        *,
        workspace_id: WorkspaceId,
    ) -> WorkflowHistoryEntry | None:
        raise NotImplementedError

    def get_result(
        self,
        instance_id: str,
        *,
        workspace_id: WorkspaceId,
    ) -> WorkflowExecutionResult | None:
        raise NotImplementedError

    def store_result(self, result: WorkflowExecutionResult) -> None:
        raise NotImplementedError
