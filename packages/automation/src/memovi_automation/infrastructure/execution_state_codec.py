"""JSON helpers for durable capability execution state."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from memovi_shared import WorkspaceId

from memovi_automation.domain.value_objects.authenticated_execution_context import (
    AuthenticatedExecutionContext,
)
from memovi_automation.domain.value_objects.cancellation_token import CancellationToken
from memovi_automation.domain.value_objects.capability_error import CapabilityError
from memovi_automation.domain.value_objects.capability_execution_policy import (
    CapabilityExecutionPolicy,
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
from memovi_automation.domain.value_objects.permission_mode import PermissionMode


def json_safe(value: object) -> object:
    """Convert nested values into JSON-serializable structures."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    if isinstance(value, Mapping):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return str(value)


def serialize_error(error: CapabilityError | None) -> dict[str, object] | None:
    if error is None:
        return None
    return {
        "code": error.code,
        "message": error.message,
        "details": dict(error.details),
    }


def deserialize_error(payload: object | None) -> CapabilityError | None:
    if payload is None:
        return None
    if not isinstance(payload, Mapping):
        return CapabilityError(code="unknown", message=str(payload))
    code = payload.get("code")
    message = payload.get("message")
    details = payload.get("details")
    return CapabilityError(
        code=str(code) if code is not None else "unknown",
        message=str(message) if message is not None else "Unknown error",
        details=dict(details) if isinstance(details, Mapping) else {},
    )


def serialize_result(result: CapabilityExecutionResult) -> dict[str, object]:
    return {
        "execution_id": result.execution_id,
        "capability_id": result.capability_id,
        "workspace_id": result.workspace_id,
        "status": result.status.value,
        "permission_mode": result.permission_mode.value,
        "output": json_safe(result.output),
        "error": serialize_error(result.error),
        "duration": result.duration,
        "conversation_id": result.conversation_id,
        "correlation_id": result.correlation_id,
        "created_at": result.created_at.astimezone(UTC).isoformat(),
        "updated_at": result.updated_at.astimezone(UTC).isoformat(),
        "metadata": json_safe(dict(result.metadata)),
    }


def deserialize_result(payload: Mapping[str, Any]) -> CapabilityExecutionResult:
    return CapabilityExecutionResult(
        execution_id=str(payload["execution_id"]),
        capability_id=str(payload["capability_id"]),
        workspace_id=str(payload["workspace_id"]),
        status=CapabilityExecutionStatus(str(payload["status"])),
        permission_mode=PermissionMode(str(payload["permission_mode"])),
        output=payload.get("output"),
        error=deserialize_error(payload.get("error")),
        duration=float(payload.get("duration") or 0.0),
        conversation_id=_optional_str(payload.get("conversation_id")),
        correlation_id=_optional_str(payload.get("correlation_id")),
        created_at=_parse_datetime(payload["created_at"]),
        updated_at=_parse_datetime(payload["updated_at"]),
        metadata=dict(payload.get("metadata") or {}),
    )


def serialize_pending_request(request: CapabilityExecutionRequest) -> dict[str, object]:
    policy_payload: dict[str, object] | None = None
    if request.policy is not None:
        policy_payload = {
            "timeout_seconds": request.policy.timeout_seconds,
            "cancellable": request.policy.cancellable,
            "permission_mode": (
                None
                if request.policy.permission_mode is None
                else request.policy.permission_mode.value
            ),
        }
    return {
        "id": request.id,
        "capability_id": request.capability_id,
        "workspace_id": request.workspace_id.value,
        "arguments": json_safe(dict(request.arguments)),
        "conversation_id": request.conversation_id,
        "correlation_id": request.correlation_id,
        "source": request.source,
        "metadata": json_safe(dict(request.metadata)),
        "policy": policy_payload,
    }


def deserialize_pending_request(payload: Mapping[str, Any]) -> CapabilityExecutionRequest:
    policy_raw = payload.get("policy")
    policy: CapabilityExecutionPolicy | None = None
    if isinstance(policy_raw, Mapping):
        mode_raw = policy_raw.get("permission_mode")
        policy = CapabilityExecutionPolicy(
            timeout_seconds=policy_raw.get("timeout_seconds"),  # type: ignore[arg-type]
            cancellable=bool(policy_raw.get("cancellable", True)),
            permission_mode=(
                None if mode_raw is None else PermissionMode(str(mode_raw))
            ),
        )
    return CapabilityExecutionRequest(
        capability_id=str(payload["capability_id"]),
        workspace_id=WorkspaceId(str(payload["workspace_id"])),
        arguments=dict(payload.get("arguments") or {}),
        id=str(payload["id"]),
        conversation_id=_optional_str(payload.get("conversation_id")),
        correlation_id=_optional_str(payload.get("correlation_id")),
        policy=policy,
        source=str(payload.get("source") or "api"),
        metadata=dict(payload.get("metadata") or {}),
    )


def serialize_auth_context(auth: AuthenticatedExecutionContext) -> dict[str, object]:
    return {
        "user_id": auth.user_id,
        "workspace_id": auth.workspace_id.value,
        "session_id": auth.session_id,
        "request_id": auth.request_id,
        "effective_permissions": sorted(auth.effective_permissions),
        "conversation_id": auth.conversation_id,
        "correlation_id": auth.correlation_id,
        "source": auth.source,
        "metadata": json_safe(dict(auth.metadata)),
    }


def deserialize_auth_context(payload: Mapping[str, Any]) -> AuthenticatedExecutionContext:
    permissions_raw = payload.get("effective_permissions") or []
    permissions = frozenset(str(item) for item in permissions_raw)
    return AuthenticatedExecutionContext(
        user_id=str(payload["user_id"]),
        workspace_id=WorkspaceId(str(payload["workspace_id"])),
        session_id=str(payload["session_id"]),
        request_id=str(payload["request_id"]),
        effective_permissions=permissions,
        cancellation=CancellationToken(),
        conversation_id=_optional_str(payload.get("conversation_id")),
        correlation_id=_optional_str(payload.get("correlation_id")),
        source=str(payload.get("source") or "api"),
        metadata=dict(payload.get("metadata") or {}),
    )


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    text = str(value)
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
