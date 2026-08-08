from dataclasses import dataclass
from typing import Protocol

from memovi_shared import WorkspaceId

from memovi_automation.domain.value_objects.authenticated_execution_context import (
    AuthenticatedExecutionContext,
)
from memovi_automation.domain.value_objects.permission_mode import PermissionMode


@dataclass(frozen=True, slots=True)
class CapabilityAuthorizationDecision:
    """Server-owned authorization outcome for a capability execution request."""

    allowed: bool
    permission_mode: PermissionMode
    effective_permissions: frozenset[str]
    denial_reason: str | None = None

    @property
    def requires_approval(self) -> bool:
        return self.allowed and self.permission_mode is PermissionMode.ASK_EVERY_TIME


class WorkspaceMembershipPort(Protocol):
    """Cross-domain membership checks used by Authorization Service."""

    def is_member(self, *, user_id: str, workspace_id: WorkspaceId) -> bool:
        raise NotImplementedError

    def get_role(self, *, user_id: str, workspace_id: WorkspaceId) -> str | None:
        raise NotImplementedError


class AuthorizationService(Protocol):
    """Resolves identity, membership, and capability permission decisions.

    Capabilities must never evaluate authorization themselves. Callers obtain
    decisions exclusively through this service.
    """

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
        raise NotImplementedError

    def require_workspace_member(
        self,
        *,
        user_id: str,
        workspace_id: WorkspaceId,
    ) -> None:
        raise NotImplementedError

    def require_workspace_owner(
        self,
        *,
        user_id: str,
        workspace_id: WorkspaceId,
    ) -> None:
        raise NotImplementedError
