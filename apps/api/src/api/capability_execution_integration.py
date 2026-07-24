from collections.abc import Mapping

from memovi_automation import (
    CapabilityExecutionEngine,
    CapabilityExecutionNotFoundError,
    CapabilityExecutionPolicy,
    CapabilityExecutionRequest,
    CapabilityExecutionResult,
    PermissionMode,
)
from memovi_intelligence.application.ports_capability_execution import CapabilityExecutionView
from memovi_intelligence.domain.exceptions import IntelligenceDomainError
from memovi_shared import WorkspaceId


class CapabilityExecutionBridgeError(IntelligenceDomainError):
    """Raised when the automation engine rejects an intelligence-facing request."""


class CapabilityExecutionEngineAdapter:
    """Composition-root adapter: Intelligence port → CapabilityExecutionEngine.

    Keeps Intelligence free of concrete capability imports and direct invoker calls.
    """

    def __init__(self, engine: CapabilityExecutionEngine) -> None:
        self._engine = engine

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
        policy = None
        if permission_mode is not None:
            try:
                policy = CapabilityExecutionPolicy(
                    permission_mode=PermissionMode(permission_mode),
                )
            except ValueError as exc:
                raise CapabilityExecutionBridgeError(
                    f"Invalid permission_mode '{permission_mode}'.",
                ) from exc

        request = CapabilityExecutionRequest.create(
            capability_id=capability_id,
            workspace_id=workspace_id,
            arguments=dict(arguments),
            conversation_id=conversation_id,
            correlation_id=correlation_id,
            policy=policy,
            source="intelligence",
        )
        result = self._engine.submit(request)
        return _to_view(result)

    def approve(
        self,
        execution_id: str,
        *,
        workspace_id: WorkspaceId,
    ) -> CapabilityExecutionView:
        try:
            result = self._engine.approve(execution_id, workspace_id=workspace_id)
        except CapabilityExecutionNotFoundError as exc:
            raise CapabilityExecutionBridgeError(str(exc)) from exc
        return _to_view(result)

    def cancel(
        self,
        execution_id: str,
        *,
        workspace_id: WorkspaceId,
    ) -> CapabilityExecutionView:
        try:
            result = self._engine.cancel(execution_id, workspace_id=workspace_id)
        except CapabilityExecutionNotFoundError as exc:
            raise CapabilityExecutionBridgeError(str(exc)) from exc
        return _to_view(result)

    def get(
        self,
        execution_id: str,
        *,
        workspace_id: WorkspaceId,
    ) -> CapabilityExecutionView:
        try:
            result = self._engine.get(execution_id, workspace_id=workspace_id)
        except CapabilityExecutionNotFoundError as exc:
            raise CapabilityExecutionBridgeError(str(exc)) from exc
        return _to_view(result)

    def list_for_conversation(
        self,
        *,
        workspace_id: WorkspaceId,
        conversation_id: str,
    ) -> tuple[CapabilityExecutionView, ...]:
        results = self._engine.list_executions(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
        )
        return tuple(_to_view(item) for item in results)


def _to_view(result: CapabilityExecutionResult) -> CapabilityExecutionView:
    return CapabilityExecutionView(
        execution_id=result.execution_id,
        capability_id=result.capability_id,
        workspace_id=result.workspace_id,
        status=result.status.value,
        permission_mode=result.permission_mode.value,
        output=result.output,
        error_code=result.error.code if result.error is not None else None,
        error_message=result.error.message if result.error is not None else None,
        duration=result.duration,
        conversation_id=result.conversation_id,
        created_at=result.created_at,
        updated_at=result.updated_at,
        metadata=dict(result.metadata),
    )


__all__ = [
    "CapabilityExecutionBridgeError",
    "CapabilityExecutionEngineAdapter",
]
