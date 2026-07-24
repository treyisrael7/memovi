from __future__ import annotations

from datetime import UTC, datetime
from threading import Lock
from time import perf_counter
from uuid import uuid4

from memovi_shared import WorkspaceId

from memovi_automation.application.ports_execution import (
    ExecutionAuditStore,
    PermissionPolicyStore,
)
from memovi_automation.application.services.capability_invoker import CapabilityInvoker
from memovi_automation.application.services.capability_registry import CapabilityRegistry
from memovi_automation.domain.exceptions import (
    CapabilityExecutionNotFoundError,
    InvalidCapabilityArgumentsError,
    UnknownCapabilityError,
)
from memovi_automation.domain.value_objects import (
    CancellationToken,
    CapabilityContext,
    CapabilityError,
    CapabilityExecutionPolicy,
    CapabilityRequest,
)
from memovi_automation.domain.value_objects.capability_execution_context import (
    CapabilityExecutionContext,
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
from memovi_automation.domain.value_objects.execution_audit_entry import (
    ExecutionAuditEntry,
    redact_arguments,
)
from memovi_automation.domain.value_objects.permission_mode import PermissionMode


class CapabilityExecutionEngine:
    """Secure pipeline for resolving, authorizing, invoking, and auditing capabilities.

    Intelligence and HTTP callers submit execution requests here. They must never
    call Capability.execute or CapabilityInvoker.invoke directly.
    """

    def __init__(
        self,
        *,
        registry: CapabilityRegistry,
        invoker: CapabilityInvoker,
        permission_policies: PermissionPolicyStore,
        audit_store: ExecutionAuditStore,
        default_permission_mode: PermissionMode = PermissionMode.ASK_EVERY_TIME,
    ) -> None:
        self._registry = registry
        self._invoker = invoker
        self._permission_policies = permission_policies
        self._audit_store = audit_store
        self._default_permission_mode = default_permission_mode
        self._executions: dict[str, CapabilityExecutionResult] = {}
        self._pending_requests: dict[str, CapabilityExecutionRequest] = {}
        self._cancellations: dict[str, CancellationToken] = {}
        self._lock = Lock()

    @property
    def registry(self) -> CapabilityRegistry:
        return self._registry

    def submit(
        self,
        request: CapabilityExecutionRequest,
        context: CapabilityExecutionContext | None = None,
    ) -> CapabilityExecutionResult:
        """Submit a capability for execution under the active permission policy."""
        execution_context = context or CapabilityExecutionContext.create(
            workspace_id=request.workspace_id,
            conversation_id=request.conversation_id,
            correlation_id=request.correlation_id,
            source=request.source,
            metadata=dict(request.metadata),
        )
        if execution_context.workspace_id != request.workspace_id:
            raise InvalidCapabilityArgumentsError(
                "Execution context workspace_id must match the request workspace_id.",
            )

        try:
            capability = self._registry.get(request.capability_id)
        except UnknownCapabilityError:
            result = self._failed_result(
                request,
                permission_mode=self._resolve_permission_mode(request),
                error=CapabilityError(
                    code="unknown_capability",
                    message=f"Unknown capability '{request.capability_id}'.",
                    details={"capability_id": request.capability_id},
                ),
            )
            self._store_result(result)
            self._audit(request, result)
            return result

        _ = capability  # resolved for existence; invoker re-resolves at execute time
        permission_mode = self._resolve_permission_mode(request)

        if permission_mode is PermissionMode.DENY:
            result = self._failed_result(
                request,
                permission_mode=permission_mode,
                error=CapabilityError(
                    code="permission_denied",
                    message=(
                        f"Capability '{request.capability_id}' is denied by "
                        "the active permission policy."
                    ),
                    details={
                        "capability_id": request.capability_id,
                        "permission_mode": permission_mode.value,
                    },
                ),
            )
            self._store_result(result)
            self._audit(request, result)
            return result

        if permission_mode is PermissionMode.ASK_EVERY_TIME:
            now = datetime.now(UTC)
            result = CapabilityExecutionResult(
                execution_id=request.id,
                capability_id=request.capability_id,
                workspace_id=request.workspace_id.value,
                status=CapabilityExecutionStatus.PENDING_APPROVAL,
                permission_mode=permission_mode,
                conversation_id=request.conversation_id,
                correlation_id=request.correlation_id,
                created_at=now,
                updated_at=now,
                metadata={
                    "source": request.source,
                    "awaiting_approval": True,
                    **dict(request.metadata),
                },
            )
            with self._lock:
                self._pending_requests[request.id] = request
                self._cancellations[request.id] = execution_context.cancellation
                self._executions[request.id] = result
            self._audit(request, result)
            return result

        return self._execute(request, execution_context.cancellation, permission_mode)

    def approve(
        self,
        execution_id: str,
        *,
        workspace_id: WorkspaceId,
    ) -> CapabilityExecutionResult:
        """Approve a pending execution and run it."""
        with self._lock:
            pending = self._pending_requests.get(execution_id)
            current = self._executions.get(execution_id)
            cancellation = self._cancellations.get(execution_id)

        if pending is None or current is None:
            raise CapabilityExecutionNotFoundError(
                f"Unknown capability execution '{execution_id}'.",
            )
        if pending.workspace_id != workspace_id:
            raise CapabilityExecutionNotFoundError(
                f"Unknown capability execution '{execution_id}'.",
            )
        if current.status is not CapabilityExecutionStatus.PENDING_APPROVAL:
            raise InvalidCapabilityArgumentsError(
                f"Execution '{execution_id}' is not awaiting approval "
                f"(status={current.status.value}).",
            )

        token = cancellation or CancellationToken()
        return self._execute(pending, token, current.permission_mode)

    def cancel(
        self,
        execution_id: str,
        *,
        workspace_id: WorkspaceId,
    ) -> CapabilityExecutionResult:
        """Cancel a pending or in-flight execution."""
        with self._lock:
            current = self._executions.get(execution_id)
            pending = self._pending_requests.get(execution_id)
            cancellation = self._cancellations.get(execution_id)

        if current is None:
            raise CapabilityExecutionNotFoundError(
                f"Unknown capability execution '{execution_id}'.",
            )
        if current.workspace_id != workspace_id.value:
            raise CapabilityExecutionNotFoundError(
                f"Unknown capability execution '{execution_id}'.",
            )

        if current.status in {
            CapabilityExecutionStatus.COMPLETED,
            CapabilityExecutionStatus.FAILED,
            CapabilityExecutionStatus.CANCELLED,
        }:
            return current

        if cancellation is not None:
            cancellation.cancel()

        now = datetime.now(UTC)
        result = CapabilityExecutionResult(
            execution_id=current.execution_id,
            capability_id=current.capability_id,
            workspace_id=current.workspace_id,
            status=CapabilityExecutionStatus.CANCELLED,
            permission_mode=current.permission_mode,
            error=CapabilityError(
                code="cancelled",
                message=f"Capability execution '{execution_id}' was cancelled.",
            ),
            duration=current.duration,
            conversation_id=current.conversation_id,
            correlation_id=current.correlation_id,
            created_at=current.created_at,
            updated_at=now,
            metadata=dict(current.metadata),
        )
        with self._lock:
            self._executions[execution_id] = result
            self._pending_requests.pop(execution_id, None)

        request = pending or CapabilityExecutionRequest.create(
            capability_id=current.capability_id,
            workspace_id=workspace_id,
            request_id=execution_id,
            conversation_id=current.conversation_id,
            correlation_id=current.correlation_id,
        )
        self._audit(request, result)
        return result

    def get(
        self,
        execution_id: str,
        *,
        workspace_id: WorkspaceId,
    ) -> CapabilityExecutionResult:
        with self._lock:
            result = self._executions.get(execution_id)
        if result is None or result.workspace_id != workspace_id.value:
            raise CapabilityExecutionNotFoundError(
                f"Unknown capability execution '{execution_id}'.",
            )
        return result

    def list_executions(
        self,
        *,
        workspace_id: WorkspaceId,
        status: CapabilityExecutionStatus | None = None,
        conversation_id: str | None = None,
    ) -> tuple[CapabilityExecutionResult, ...]:
        with self._lock:
            values = list(self._executions.values())
        filtered = [
            item
            for item in values
            if item.workspace_id == workspace_id.value
            and (status is None or item.status is status)
            and (conversation_id is None or item.conversation_id == conversation_id)
        ]
        filtered.sort(key=lambda item: item.updated_at)
        return tuple(filtered)

    def set_permission_mode(
        self,
        capability_id: str,
        mode: PermissionMode,
        *,
        workspace_id: WorkspaceId,
    ) -> None:
        if not self._registry.contains(capability_id):
            raise UnknownCapabilityError(f"Unknown capability '{capability_id}'.")
        self._permission_policies.set(capability_id, mode, workspace_id=workspace_id)

    def get_permission_mode(
        self,
        capability_id: str,
        *,
        workspace_id: WorkspaceId,
    ) -> PermissionMode:
        if not self._registry.contains(capability_id):
            raise UnknownCapabilityError(f"Unknown capability '{capability_id}'.")
        return self._permission_policies.get(capability_id, workspace_id=workspace_id)

    def list_audit(
        self,
        *,
        workspace_id: WorkspaceId,
        limit: int = 100,
    ) -> tuple[ExecutionAuditEntry, ...]:
        return self._audit_store.list_for_workspace(workspace_id=workspace_id, limit=limit)

    def _resolve_permission_mode(self, request: CapabilityExecutionRequest) -> PermissionMode:
        if request.policy is not None and request.policy.permission_mode is not None:
            return request.policy.permission_mode
        try:
            return self._permission_policies.get(
                request.capability_id,
                workspace_id=request.workspace_id,
            )
        except Exception:
            return self._default_permission_mode

    def _execute(
        self,
        request: CapabilityExecutionRequest,
        cancellation: CancellationToken,
        permission_mode: PermissionMode,
    ) -> CapabilityExecutionResult:
        now = datetime.now(UTC)
        executing = CapabilityExecutionResult(
            execution_id=request.id,
            capability_id=request.capability_id,
            workspace_id=request.workspace_id.value,
            status=CapabilityExecutionStatus.EXECUTING,
            permission_mode=permission_mode,
            conversation_id=request.conversation_id,
            correlation_id=request.correlation_id,
            created_at=now,
            updated_at=now,
            metadata={"source": request.source, **dict(request.metadata)},
        )
        with self._lock:
            self._executions[request.id] = executing
            self._pending_requests.pop(request.id, None)
            self._cancellations[request.id] = cancellation

        self._audit(request, executing)

        started = perf_counter()
        try:
            metadata = self._registry.metadata(request.capability_id)
        except UnknownCapabilityError as exc:
            result = self._failed_result(
                request,
                permission_mode=permission_mode,
                error=CapabilityError(
                    code="unknown_capability",
                    message=str(exc),
                    details={"capability_id": request.capability_id},
                ),
                created_at=executing.created_at,
            )
            self._store_result(result)
            self._audit(request, result)
            return result

        capability_context = CapabilityContext.create(
            workspace_id=request.workspace_id,
            cancellation=cancellation,
            correlation_id=request.correlation_id,
            granted_permissions=frozenset(metadata.permissions),
            metadata={
                "execution_id": request.id,
                "conversation_id": request.conversation_id,
                "source": request.source,
                **dict(request.metadata),
            },
        )
        invoke_policy = request.policy or CapabilityExecutionPolicy()
        capability_request = CapabilityRequest.create(
            capability_id=request.capability_id,
            arguments=dict(request.arguments),
            request_id=request.id,
            policy=CapabilityExecutionPolicy(
                timeout_seconds=invoke_policy.timeout_seconds,
                cancellable=invoke_policy.cancellable,
                permission_mode=permission_mode,
            ),
        )

        try:
            invoke_result = self._invoker.invoke(capability_request, capability_context)
        except InvalidCapabilityArgumentsError as exc:
            result = self._failed_result(
                request,
                permission_mode=permission_mode,
                error=CapabilityError(
                    code="invalid_arguments",
                    message=str(exc),
                ),
                duration=perf_counter() - started,
                created_at=executing.created_at,
            )
            self._store_result(result)
            self._audit(request, result)
            return result

        duration = invoke_result.duration if invoke_result.duration else perf_counter() - started
        if invoke_result.cancelled:
            status = CapabilityExecutionStatus.CANCELLED
        elif invoke_result.success:
            status = CapabilityExecutionStatus.COMPLETED
        else:
            status = CapabilityExecutionStatus.FAILED

        result = CapabilityExecutionResult(
            execution_id=request.id,
            capability_id=request.capability_id,
            workspace_id=request.workspace_id.value,
            status=status,
            permission_mode=permission_mode,
            output=invoke_result.output,
            error=invoke_result.error,
            duration=duration,
            conversation_id=request.conversation_id,
            correlation_id=request.correlation_id,
            created_at=executing.created_at,
            updated_at=datetime.now(UTC),
            metadata={
                "source": request.source,
                "invoker": dict(invoke_result.metadata),
                **dict(request.metadata),
            },
        )
        self._store_result(result)
        self._audit(request, result)
        return result

    def _failed_result(
        self,
        request: CapabilityExecutionRequest,
        *,
        permission_mode: PermissionMode,
        error: CapabilityError,
        duration: float = 0.0,
        created_at: datetime | None = None,
    ) -> CapabilityExecutionResult:
        now = datetime.now(UTC)
        return CapabilityExecutionResult(
            execution_id=request.id,
            capability_id=request.capability_id,
            workspace_id=request.workspace_id.value,
            status=CapabilityExecutionStatus.FAILED,
            permission_mode=permission_mode,
            error=error,
            duration=duration,
            conversation_id=request.conversation_id,
            correlation_id=request.correlation_id,
            created_at=created_at or now,
            updated_at=now,
            metadata={"source": request.source, **dict(request.metadata)},
        )

    def _store_result(self, result: CapabilityExecutionResult) -> None:
        with self._lock:
            self._executions[result.execution_id] = result

    def _audit(
        self,
        request: CapabilityExecutionRequest,
        result: CapabilityExecutionResult,
    ) -> None:
        summary: dict[str, object] = {
            "status": result.status.value,
            "success": result.status is CapabilityExecutionStatus.COMPLETED,
        }
        if result.error is not None:
            summary["error_code"] = result.error.code
            summary["error_message"] = result.error.message
        if result.output is not None:
            summary["has_output"] = True

        entry = ExecutionAuditEntry(
            id=str(uuid4()),
            execution_id=result.execution_id,
            workspace_id=result.workspace_id,
            capability_id=result.capability_id,
            status=result.status,
            permission_mode=result.permission_mode,
            arguments=redact_arguments(request.arguments),
            result_summary=summary,
            duration=result.duration,
            timestamp=result.updated_at,
            conversation_id=result.conversation_id,
            correlation_id=result.correlation_id,
            source=request.source,
        )
        self._audit_store.append(entry)
