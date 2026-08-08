from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from threading import Lock
from time import perf_counter
from uuid import uuid4

from memovi_shared import WorkspaceId

from memovi_automation.application.ports_authorization import AuthorizationService
from memovi_automation.application.ports_execution import (
    ExecutionAuditStore,
    ExecutionStateStore,
    PermissionPolicyStore,
)
from memovi_automation.application.services.capability_authorization_service import (
    CapabilityAuthorizationService,
)
from memovi_automation.application.services.capability_invoker import CapabilityInvoker
from memovi_automation.application.services.capability_registry import CapabilityRegistry
from memovi_automation.domain.exceptions import (
    AuthorizationDeniedError,
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
from memovi_automation.domain.value_objects.execution_audit_entry import (
    ExecutionAuditEntry,
    redact_arguments,
)
from memovi_automation.domain.value_objects.permission_mode import PermissionMode
from memovi_observability import get_metrics_recorder


class _AllowAllMembership:
    def is_member(self, *, user_id: str, workspace_id: WorkspaceId) -> bool:
        return True


class CapabilityExecutionEngine:
    """Secure pipeline for resolving, authorizing, invoking, and auditing capabilities.

    Intelligence and HTTP callers submit execution requests here. They must never
    call Capability.execute or CapabilityInvoker.invoke directly. Authorization is
    evaluated exclusively by Authorization Service using AuthenticatedExecutionContext.
    """

    def __init__(
        self,
        *,
        registry: CapabilityRegistry,
        invoker: CapabilityInvoker,
        permission_policies: PermissionPolicyStore,
        audit_store: ExecutionAuditStore,
        authorization: AuthorizationService | None = None,
        default_permission_mode: PermissionMode = PermissionMode.ASK_EVERY_TIME,
        execution_store: ExecutionStateStore | None = None,
        recover_on_start: bool = False,
    ) -> None:
        self._registry = registry
        self._invoker = invoker
        self._permission_policies = permission_policies
        self._audit_store = audit_store
        if execution_store is None:
            # Default process-local store for unit tests; production wires SQLAlchemy.
            from memovi_automation.infrastructure.in_memory_execution_state_store import (
                InMemoryExecutionStateStore,
            )

            execution_store = InMemoryExecutionStateStore()
        self._execution_store = execution_store
        self._default_permission_mode = default_permission_mode
        self._authorization = authorization or CapabilityAuthorizationService(
            membership=_AllowAllMembership(),
            permission_policies=permission_policies,
            registry=registry,
            default_permission_mode=default_permission_mode,
        )
        self._cancellations: dict[str, CancellationToken] = {}
        self._lock = Lock()
        if recover_on_start:
            self.recover_interrupted_executions()

    @property
    def registry(self) -> CapabilityRegistry:
        return self._registry

    @property
    def authorization(self) -> AuthorizationService:
        return self._authorization

    def submit(
        self,
        request: CapabilityExecutionRequest,
        context: AuthenticatedExecutionContext,
    ) -> CapabilityExecutionResult:
        """Submit a capability for execution under server-owned authorization."""
        if context.workspace_id != request.workspace_id:
            raise InvalidCapabilityArgumentsError(
                "Authenticated execution context workspace_id must match the request.",
            )

        auth_context, decision = self._authorization.authorize_capability(
            user_id=context.user_id,
            session_id=context.session_id,
            workspace_id=request.workspace_id,
            request_id=context.request_id,
            capability_id=request.capability_id,
            source=request.source,
            conversation_id=request.conversation_id or context.conversation_id,
            correlation_id=request.correlation_id or context.correlation_id,
            metadata=dict(request.metadata),
        )
        # Preserve caller cancellation token across authorization rebuild.
        if context.cancellation is not auth_context.cancellation:
            auth_context = AuthenticatedExecutionContext(
                user_id=auth_context.user_id,
                workspace_id=auth_context.workspace_id,
                session_id=auth_context.session_id,
                request_id=auth_context.request_id,
                effective_permissions=auth_context.effective_permissions,
                cancellation=context.cancellation,
                conversation_id=auth_context.conversation_id,
                correlation_id=auth_context.correlation_id,
                source=auth_context.source,
                metadata=dict(auth_context.metadata),
            )

        if not decision.allowed:
            if decision.denial_reason and "Unknown capability" in decision.denial_reason:
                error = CapabilityError(
                    code="unknown_capability",
                    message=decision.denial_reason,
                    details={"capability_id": request.capability_id},
                )
            else:
                error = CapabilityError(
                    code="permission_denied",
                    message=decision.denial_reason
                    or (
                        f"Capability '{request.capability_id}' is denied by "
                        "the active permission policy."
                    ),
                    details={
                        "capability_id": request.capability_id,
                        "permission_mode": decision.permission_mode.value,
                    },
                )
            result = self._failed_result(
                request,
                permission_mode=decision.permission_mode,
                error=error,
                auth_context=auth_context,
            )
            self._store_result(result)
            self._audit(request, result, auth_context=auth_context)
            return result

        permission_mode = decision.permission_mode

        if permission_mode is PermissionMode.ASK_EVERY_TIME:
            now = datetime.now(UTC)
            result = CapabilityExecutionResult(
                execution_id=request.id,
                workspace_id=request.workspace_id.value,
                capability_id=request.capability_id,
                status=CapabilityExecutionStatus.PENDING_APPROVAL,
                permission_mode=permission_mode,
                conversation_id=request.conversation_id,
                correlation_id=request.correlation_id,
                created_at=now,
                updated_at=now,
                metadata={
                    **dict(request.metadata),
                    "source": request.source,
                    "awaiting_approval": True,
                    "operation_summary": _operation_summary(request.arguments),
                    "user_id": auth_context.user_id,
                    "session_id": auth_context.session_id,
                    "request_id": auth_context.request_id,
                },
            )
            with self._lock:
                self._cancellations[request.id] = auth_context.cancellation
            self._store_result(result)
            self._execution_store.save_pending(request, auth_context)
            self._audit(request, result, auth_context=auth_context)
            return result

        return self._execute(request, auth_context, permission_mode)

    def approve(
        self,
        execution_id: str,
        *,
        workspace_id: WorkspaceId,
        context: AuthenticatedExecutionContext,
    ) -> CapabilityExecutionResult:
        """Approve a pending execution and run it under authenticated context."""
        self._authorization.require_workspace_member(
            user_id=context.user_id,
            workspace_id=workspace_id,
        )
        with self._lock:
            cancellation = self._cancellations.get(execution_id)
        pending_pair = self._execution_store.get_pending(execution_id)
        current = self._execution_store.get_result(execution_id)

        if pending_pair is None or current is None:
            raise CapabilityExecutionNotFoundError(
                f"Unknown capability execution '{execution_id}'.",
            )
        pending, pending_auth = pending_pair
        if pending.workspace_id != workspace_id:
            raise CapabilityExecutionNotFoundError(
                f"Unknown capability execution '{execution_id}'.",
            )
        if current.status is not CapabilityExecutionStatus.PENDING_APPROVAL:
            raise InvalidCapabilityArgumentsError(
                f"Execution '{execution_id}' is not awaiting approval "
                f"(status={current.status.value}).",
            )

        token = cancellation or context.cancellation
        auth_context = AuthenticatedExecutionContext(
            user_id=context.user_id,
            workspace_id=workspace_id,
            session_id=context.session_id,
            request_id=context.request_id,
            effective_permissions=pending_auth.effective_permissions,
            cancellation=token,
            conversation_id=pending.conversation_id,
            correlation_id=pending.correlation_id,
            source=pending.source,
            metadata=dict(pending.metadata),
        )
        # Re-evaluate policy at approval time (server-owned; may have changed).
        _, decision = self._authorization.authorize_capability(
            user_id=auth_context.user_id,
            session_id=auth_context.session_id,
            workspace_id=workspace_id,
            request_id=auth_context.request_id,
            capability_id=pending.capability_id,
            source=pending.source,
            conversation_id=pending.conversation_id,
            correlation_id=pending.correlation_id,
            metadata=dict(pending.metadata),
        )
        if not decision.allowed or decision.permission_mode is PermissionMode.DENY:
            raise AuthorizationDeniedError(
                decision.denial_reason
                or f"Capability '{pending.capability_id}' is denied by policy.",
                code="permission_denied",
                details={"capability_id": pending.capability_id},
            )
        auth_context = auth_context.with_effective_permissions(decision.effective_permissions)
        return self._execute(pending, auth_context, decision.permission_mode)

    def cancel(
        self,
        execution_id: str,
        *,
        workspace_id: WorkspaceId,
        context: AuthenticatedExecutionContext,
    ) -> CapabilityExecutionResult:
        """Cancel a pending or in-flight execution."""
        self._authorization.require_workspace_member(
            user_id=context.user_id,
            workspace_id=workspace_id,
        )
        with self._lock:
            cancellation = self._cancellations.get(execution_id)
        current = self._execution_store.get_result(execution_id)
        pending_pair = self._execution_store.get_pending(execution_id)
        pending = None if pending_pair is None else pending_pair[0]

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
            metadata={**dict(current.metadata), "user_id": context.user_id},
        )
        self._store_result(result)
        self._execution_store.clear_pending(execution_id)
        with self._lock:
            self._cancellations.pop(execution_id, None)

        request = pending or CapabilityExecutionRequest.create(
            capability_id=current.capability_id,
            workspace_id=workspace_id,
            request_id=execution_id,
            conversation_id=current.conversation_id,
            correlation_id=current.correlation_id,
        )
        self._audit(request, result, auth_context=context)
        return result

    def get(
        self,
        execution_id: str,
        *,
        workspace_id: WorkspaceId,
    ) -> CapabilityExecutionResult:
        result = self._execution_store.get_result(execution_id)
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
        return self._execution_store.list_results(
            workspace_id=workspace_id,
            status=status,
            conversation_id=conversation_id,
        )

    def recover_interrupted_executions(self) -> tuple[CapabilityExecutionResult, ...]:
        """Mark in-flight executions failed after process restart (no duplicate resume)."""
        recovered = self._execution_store.fail_interrupted_executions(
            reason="Capability execution was interrupted by process restart.",
        )
        for result in recovered:
            request = CapabilityExecutionRequest.create(
                capability_id=result.capability_id,
                workspace_id=WorkspaceId(result.workspace_id),
                request_id=result.execution_id,
                conversation_id=result.conversation_id,
                correlation_id=result.correlation_id,
                source=str(result.metadata.get("source") or "api"),
                metadata=dict(result.metadata),
            )
            self._audit(request, result)
        if recovered:
            get_metrics_recorder().increment(
                "memovi.capabilities.execution.resume_skipped",
                value=float(len(recovered)),
                tags={"reason": "interrupted_by_restart"},
            )
        return recovered

    def set_permission_mode(
        self,
        capability_id: str,
        mode: PermissionMode,
        *,
        workspace_id: WorkspaceId,
        context: AuthenticatedExecutionContext,
    ) -> None:
        self._authorization.require_workspace_member(
            user_id=context.user_id,
            workspace_id=workspace_id,
        )
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

    def _execute(
        self,
        request: CapabilityExecutionRequest,
        auth_context: AuthenticatedExecutionContext,
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
            metadata={
                **dict(request.metadata),
                "source": request.source,
                "operation_summary": _operation_summary(request.arguments),
                "user_id": auth_context.user_id,
                "session_id": auth_context.session_id,
                "request_id": auth_context.request_id,
            },
        )
        with self._lock:
            self._cancellations[request.id] = auth_context.cancellation
        self._store_result(executing)
        self._execution_store.clear_pending(request.id)

        self._audit(request, executing, auth_context=auth_context)
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
                auth_context=auth_context,
            )
            self._store_result(result)
            self._audit(request, result, auth_context=auth_context)
            return result

        if auth_context.effective_permissions:
            granted = frozenset(
                permission
                for permission in metadata.permissions
                if permission.name in auth_context.effective_permissions
            )
        else:
            granted = frozenset(metadata.permissions)
        capability_context = CapabilityContext.create(
            workspace_id=request.workspace_id,
            cancellation=auth_context.cancellation,
            correlation_id=request.correlation_id,
            granted_permissions=granted,
            metadata={
                **dict(request.metadata),
                "execution_id": request.id,
                "conversation_id": request.conversation_id,
                "source": request.source,
                "user_id": auth_context.user_id,
                "session_id": auth_context.session_id,
                "request_id": auth_context.request_id,
                # Host progress port — must win over caller-supplied metadata.
                "report_progress": lambda output: self._publish_progress(
                    request.id,
                    output,
                ),
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
                auth_context=auth_context,
            )
            self._store_result(result)
            self._audit(request, result, auth_context=auth_context)
            return result

        duration = invoke_result.duration if invoke_result.duration else perf_counter() - started
        if invoke_result.cancelled:
            status = CapabilityExecutionStatus.CANCELLED
        elif invoke_result.success:
            status = CapabilityExecutionStatus.COMPLETED
        else:
            status = CapabilityExecutionStatus.FAILED

        result_metadata: dict[str, object] = {
            **dict(request.metadata),
            "source": request.source,
            "operation_summary": _operation_summary(request.arguments),
            "invoker": dict(invoke_result.metadata),
            "user_id": auth_context.user_id,
            "session_id": auth_context.session_id,
            "request_id": auth_context.request_id,
        }
        if (
            invoke_result.error is not None
            and invoke_result.error.code == "overwrite_confirmation_required"
        ):
            result_metadata["retry_arguments"] = dict(request.arguments)

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
            metadata=result_metadata,
        )
        self._store_result(result)
        self._audit(request, result, auth_context=auth_context)
        if result.duration:
            get_metrics_recorder().timing(
                "memovi.capabilities.execution.duration_ms",
                result.duration * 1000.0,
                tags={"status": result.status.value, "capability": result.capability_id},
            )
        return result

    def _failed_result(
        self,
        request: CapabilityExecutionRequest,
        *,
        permission_mode: PermissionMode,
        error: CapabilityError,
        duration: float = 0.0,
        created_at: datetime | None = None,
        auth_context: AuthenticatedExecutionContext | None = None,
    ) -> CapabilityExecutionResult:
        now = datetime.now(UTC)
        metadata: dict[str, object] = {"source": request.source, **dict(request.metadata)}
        if auth_context is not None:
            metadata["user_id"] = auth_context.user_id
            metadata["session_id"] = auth_context.session_id
            metadata["request_id"] = auth_context.request_id
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
            metadata=metadata,
        )

    def _store_result(self, result: CapabilityExecutionResult) -> None:
        self._execution_store.save_result(result)

    def _publish_progress(self, execution_id: str, output: object) -> None:
        """Publish best-effort streaming output while an execution is still running."""
        current = self._execution_store.get_result(execution_id)
        if current is None:
            return
        if current.status is not CapabilityExecutionStatus.EXECUTING:
            return
        self._store_result(
            CapabilityExecutionResult(
                execution_id=current.execution_id,
                capability_id=current.capability_id,
                workspace_id=current.workspace_id,
                status=current.status,
                permission_mode=current.permission_mode,
                output=output,
                error=current.error,
                duration=current.duration,
                conversation_id=current.conversation_id,
                correlation_id=current.correlation_id,
                created_at=current.created_at,
                updated_at=datetime.now(UTC),
                metadata=dict(current.metadata),
            )
        )

    def _audit(
        self,
        request: CapabilityExecutionRequest,
        result: CapabilityExecutionResult,
        *,
        auth_context: AuthenticatedExecutionContext | None = None,
    ) -> None:
        summary: dict[str, object] = {
            "status": result.status.value,
            "success": result.status is CapabilityExecutionStatus.COMPLETED,
            **_operation_summary(request.arguments),
        }
        if result.error is not None:
            summary["error_code"] = result.error.code
            summary["error_message"] = result.error.message
        if result.output is not None:
            summary["has_output"] = True
            if isinstance(result.output, dict):
                if "exit_code" in result.output:
                    summary["exit_code"] = result.output["exit_code"]
                if "duration_seconds" in result.output:
                    summary["command_duration_seconds"] = result.output["duration_seconds"]
                if "working_directory" in result.output:
                    summary["working_directory"] = result.output["working_directory"]
                if "repository" in result.output:
                    summary["repository"] = result.output["repository"]
                if "branch" in result.output:
                    summary["branch"] = result.output["branch"]
                if result.output.get("operation") == "commit" and "short_sha" in result.output:
                    summary["short_sha"] = result.output["short_sha"]
                if "url" in result.output and isinstance(result.output["url"], str):
                    summary["url"] = result.output["url"]
                if "query" in result.output and isinstance(result.output["query"], str):
                    summary["query"] = result.output["query"]
                if "destination" in result.output and isinstance(
                    result.output["destination"], str
                ):
                    summary["destination"] = result.output["destination"]
                if "sha256" in result.output:
                    summary["sha256"] = result.output["sha256"]
                if "result_count" in result.output:
                    summary["result_count"] = result.output["result_count"]
                output_meta = result.output.get("metadata")
                if isinstance(output_meta, dict):
                    if "undo_available" in output_meta:
                        summary["undo_available"] = output_meta["undo_available"]
                    if "delete_mode" in output_meta:
                        summary["delete_mode"] = output_meta["delete_mode"]
                    if "clean" in output_meta:
                        summary["clean"] = output_meta["clean"]
                    if "filesystem_integrated" in output_meta:
                        summary["filesystem_integrated"] = output_meta[
                            "filesystem_integrated"
                        ]

        operation = summary.get("operation")
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
            user_id=None if auth_context is None else auth_context.user_id,
            operation=operation if isinstance(operation, str) else None,
        )
        self._audit_store.append(entry)


def _operation_summary(arguments: object) -> dict[str, object]:
    """Build a redacted operation/target summary for UI and audit records."""
    if not isinstance(arguments, Mapping):
        return {}
    summary: dict[str, object] = {}
    operation = arguments.get("operation")
    if isinstance(operation, str) and operation.strip():
        summary["operation"] = operation.strip()
    path = arguments.get("path")
    if isinstance(path, str) and path.strip():
        summary["target"] = path.strip()
    destination = arguments.get("destination")
    if isinstance(destination, str) and destination.strip():
        summary["destination"] = destination.strip()
    overwrite_policy = arguments.get("overwrite_policy")
    if isinstance(overwrite_policy, str) and overwrite_policy.strip():
        summary["overwrite_policy"] = overwrite_policy.strip()
    delete_mode = arguments.get("delete_mode")
    if isinstance(delete_mode, str) and delete_mode.strip():
        summary["delete_mode"] = delete_mode.strip()
    command = arguments.get("command")
    if isinstance(command, str) and command.strip():
        summary["command"] = command.strip()
        if "target" not in summary:
            summary["target"] = command.strip()
    working_directory = arguments.get("working_directory")
    if isinstance(working_directory, str) and working_directory.strip():
        summary["working_directory"] = working_directory.strip()
    repository = arguments.get("repository")
    if isinstance(repository, str) and repository.strip():
        summary["repository"] = repository.strip()
        if "target" not in summary:
            summary["target"] = repository.strip()
    branch = arguments.get("branch") or arguments.get("name")
    if isinstance(branch, str) and branch.strip():
        summary["branch"] = branch.strip()
    message = arguments.get("message")
    if isinstance(message, str) and message.strip():
        summary["has_message"] = True
    url = arguments.get("url")
    if isinstance(url, str) and url.strip():
        from memovi_automation.domain.value_objects.execution_audit_entry import (
            redact_url_for_audit,
        )

        redacted_url = redact_url_for_audit(url.strip())
        summary["url"] = redacted_url
        if "target" not in summary:
            summary["target"] = redacted_url
    query = arguments.get("query")
    if isinstance(query, str) and query.strip():
        summary["query"] = query.strip()
        if "target" not in summary:
            summary["target"] = query.strip()
    if "content" in arguments:
        summary["has_content"] = True
    if "env" in arguments:
        summary["has_env"] = True
    return summary
