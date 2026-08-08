"""Shared membership authorization helpers for workspace commands."""

from memovi_shared import WorkspaceId

from memovi_workspace.domain.entities.workspace_membership import (
    OWNER_ROLE,
    WorkspaceMembership,
)
from memovi_workspace.domain.exceptions import (
    WorkspaceMembershipRequiredError,
    WorkspaceOwnerRequiredError,
)
from memovi_workspace.domain.repositories.workspace_membership_repository import (
    WorkspaceMembershipRepository,
)


def require_membership(
    memberships: WorkspaceMembershipRepository,
    *,
    user_id: str,
    workspace_id: WorkspaceId,
) -> WorkspaceMembership:
    membership = memberships.get(user_id=user_id, workspace_id=workspace_id)
    if membership is None:
        raise WorkspaceMembershipRequiredError(
            f"User '{user_id}' is not a member of workspace '{workspace_id.value}'.",
        )
    return membership


def require_owner(
    memberships: WorkspaceMembershipRepository,
    *,
    user_id: str,
    workspace_id: WorkspaceId,
) -> WorkspaceMembership:
    membership = require_membership(
        memberships,
        user_id=user_id,
        workspace_id=workspace_id,
    )
    if membership.role != OWNER_ROLE:
        raise WorkspaceOwnerRequiredError(
            f"User '{user_id}' must be an owner of workspace '{workspace_id.value}'.",
        )
    return membership
