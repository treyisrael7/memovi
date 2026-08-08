from __future__ import annotations

from memovi_shared import WorkspaceId

from memovi_automation.application.ports_authorization import (
    CapabilityAuthorizationDecision,
    WorkspaceMembershipPort,
)
from memovi_automation.application.ports_execution import PermissionPolicyStore
from memovi_automation.application.services.capability_registry import CapabilityRegistry
from memovi_automation.domain.exceptions import (
    AuthorizationDeniedError,
    UnknownCapabilityError,
)
from memovi_automation.domain.value_objects.authenticated_execution_context import (
    AuthenticatedExecutionContext,
)
from memovi_automation.domain.value_objects.permission_mode import PermissionMode


class CapabilityAuthorizationService:
    """Server-owned authorization for capability execution.

    Resolves workspace membership and capability policy mode. Never trusts
    client-supplied permission modes or authorization flags.
    """

    def __init__(
        self,
        *,
        membership: WorkspaceMembershipPort,
        permission_policies: PermissionPolicyStore,
        registry: CapabilityRegistry,
        default_permission_mode: PermissionMode = PermissionMode.ASK_EVERY_TIME,
    ) -> None:
        self._membership = membership
        self._permission_policies = permission_policies
        self._registry = registry
        self._default_permission_mode = default_permission_mode

    def require_workspace_member(
        self,
        *,
        user_id: str,
        workspace_id: WorkspaceId,
    ) -> None:
        if not self._membership.is_member(user_id=user_id, workspace_id=workspace_id):
            raise AuthorizationDeniedError(
                f"User '{user_id}' is not a member of workspace '{workspace_id.value}'.",
                code="workspace_membership_required",
                details={
                    "user_id": user_id,
                    "workspace_id": workspace_id.value,
                },
            )

    def require_workspace_owner(
        self,
        *,
        user_id: str,
        workspace_id: WorkspaceId,
    ) -> None:
        role = self._membership.get_role(user_id=user_id, workspace_id=workspace_id)
        if role is None:
            raise AuthorizationDeniedError(
                f"User '{user_id}' is not a member of workspace '{workspace_id.value}'.",
                code="workspace_membership_required",
                details={
                    "user_id": user_id,
                    "workspace_id": workspace_id.value,
                },
            )
        if role != "owner":
            raise AuthorizationDeniedError(
                f"User '{user_id}' must be an owner of workspace '{workspace_id.value}'.",
                code="workspace_owner_required",
                details={
                    "user_id": user_id,
                    "workspace_id": workspace_id.value,
                    "role": role,
                },
            )

    def authorize_capability(
        self,
        *,
        user_id: str,
        session_id: str,
        workspace_id: WorkspaceId,
        request_id: str,
        capability_id: str,
        source: str = "api",
        conversation_id: str | None = None,
        correlation_id: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> tuple[AuthenticatedExecutionContext, CapabilityAuthorizationDecision]:
        self.require_workspace_member(user_id=user_id, workspace_id=workspace_id)

        try:
            capability_metadata = self._registry.metadata(capability_id)
        except UnknownCapabilityError:
            context = AuthenticatedExecutionContext.create(
                user_id=user_id,
                workspace_id=workspace_id,
                session_id=session_id,
                request_id=request_id,
                effective_permissions=frozenset(),
                conversation_id=conversation_id,
                correlation_id=correlation_id,
                source=source,
                metadata=metadata,
            )
            decision = CapabilityAuthorizationDecision(
                allowed=False,
                permission_mode=self._default_permission_mode,
                effective_permissions=frozenset(),
                denial_reason=f"Unknown capability '{capability_id}'.",
            )
            return context, decision

        permission_mode = self._resolve_permission_mode(
            capability_id=capability_id,
            workspace_id=workspace_id,
        )
        declared = frozenset(capability_metadata.permission_names())

        if permission_mode is PermissionMode.DENY:
            decision = CapabilityAuthorizationDecision(
                allowed=False,
                permission_mode=permission_mode,
                effective_permissions=frozenset(),
                denial_reason=(
                    f"Capability '{capability_id}' is denied by the active permission policy."
                ),
            )
            effective = frozenset()
        else:
            decision = CapabilityAuthorizationDecision(
                allowed=True,
                permission_mode=permission_mode,
                effective_permissions=declared,
            )
            effective = declared

        context = AuthenticatedExecutionContext.create(
            user_id=user_id,
            workspace_id=workspace_id,
            session_id=session_id,
            request_id=request_id,
            effective_permissions=effective,
            conversation_id=conversation_id,
            correlation_id=correlation_id,
            source=source,
            metadata=metadata,
        )
        return context, decision

    def _resolve_permission_mode(
        self,
        *,
        capability_id: str,
        workspace_id: WorkspaceId,
    ) -> PermissionMode:
        try:
            return self._permission_policies.get(
                capability_id,
                workspace_id=workspace_id,
            )
        except Exception:
            return self._default_permission_mode
