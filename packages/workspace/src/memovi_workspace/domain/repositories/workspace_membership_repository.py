from typing import Protocol

from memovi_shared import WorkspaceId

from memovi_workspace.domain.entities.workspace_membership import WorkspaceMembership


class WorkspaceMembershipRepository(Protocol):
    """Persistence contract for workspace membership."""

    def is_member(self, *, user_id: str, workspace_id: WorkspaceId) -> bool:
        raise NotImplementedError

    def get(
        self,
        *,
        user_id: str,
        workspace_id: WorkspaceId,
    ) -> WorkspaceMembership | None:
        raise NotImplementedError

    def add(self, membership: WorkspaceMembership) -> None:
        raise NotImplementedError

    def update(self, membership: WorkspaceMembership) -> None:
        raise NotImplementedError

    def remove(
        self,
        *,
        user_id: str,
        workspace_id: WorkspaceId,
    ) -> WorkspaceMembership | None:
        raise NotImplementedError

    def list_for_user(self, user_id: str) -> list[WorkspaceMembership]:
        raise NotImplementedError

    def list_for_workspace(self, workspace_id: WorkspaceId) -> list[WorkspaceMembership]:
        raise NotImplementedError

    def list_workspace_ids_for_user(self, user_id: str) -> list[WorkspaceId]:
        raise NotImplementedError

    def count_by_role(self, *, workspace_id: WorkspaceId, role: str) -> int:
        raise NotImplementedError
