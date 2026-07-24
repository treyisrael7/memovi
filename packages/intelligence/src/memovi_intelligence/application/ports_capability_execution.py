from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from memovi_shared import WorkspaceId


@dataclass(frozen=True, slots=True)
class CapabilityExecutionView:
    """Intelligence-facing structured capability execution result."""

    execution_id: str
    capability_id: str
    workspace_id: str
    status: str
    permission_mode: str
    output: object | None
    error_code: str | None
    error_message: str | None
    duration: float
    conversation_id: str | None
    created_at: datetime
    updated_at: datetime
    metadata: Mapping[str, object]


class CapabilityExecutionPort(Protocol):
    """Bridge from Intelligence to the Capability Execution Engine.

    Intelligence must never import or call concrete capabilities. All host
    actions flow through this port into the execution engine.
    """

    def submit(
        self,
        *,
        workspace_id: WorkspaceId,
        capability_id: str,
        arguments: Mapping[str, object],
        conversation_id: str | None = None,
        correlation_id: str | None = None,
        permission_mode: str | None = None,
    ) -> CapabilityExecutionView:
        raise NotImplementedError

    def approve(
        self,
        execution_id: str,
        *,
        workspace_id: WorkspaceId,
    ) -> CapabilityExecutionView:
        raise NotImplementedError

    def cancel(
        self,
        execution_id: str,
        *,
        workspace_id: WorkspaceId,
    ) -> CapabilityExecutionView:
        raise NotImplementedError

    def get(
        self,
        execution_id: str,
        *,
        workspace_id: WorkspaceId,
    ) -> CapabilityExecutionView:
        raise NotImplementedError

    def list_for_conversation(
        self,
        *,
        workspace_id: WorkspaceId,
        conversation_id: str,
    ) -> tuple[CapabilityExecutionView, ...]:
        raise NotImplementedError
