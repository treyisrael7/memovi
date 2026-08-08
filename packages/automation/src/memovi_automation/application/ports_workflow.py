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
        """Create or replace a workflow definition (upsert)."""
        raise NotImplementedError

    def create(self, definition: WorkflowDefinition) -> WorkflowDefinition:
        """Persist a new workflow definition. Raises if the id already exists."""
        raise NotImplementedError

    def update(self, definition: WorkflowDefinition) -> WorkflowDefinition:
        """Replace an existing workflow definition. Raises if missing."""
        raise NotImplementedError

    def delete(self, workflow_id: str) -> None:
        """Remove a workflow definition. Raises if missing or built-in protected."""
        raise NotImplementedError

    def duplicate(
        self,
        workflow_id: str,
        *,
        new_workflow_id: str | None = None,
        name: str | None = None,
    ) -> WorkflowDefinition:
        """Copy an existing definition under a new id."""
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
        """Persist or upsert a full workflow execution result."""
        raise NotImplementedError

    def list_by_status(
        self,
        *,
        status: str,
    ) -> tuple[WorkflowExecutionResult, ...]:
        """List executions matching a status (used for startup recovery)."""
        raise NotImplementedError

    def fail_interrupted_executions(
        self,
        *,
        reason: str,
    ) -> tuple[WorkflowExecutionResult, ...]:
        """Mark interrupted non-terminal runs as failed; avoid duplicate resume."""
        raise NotImplementedError
