from typing import Protocol

from memovi_shared import WorkspaceId

from memovi_workspace.domain.entities.workspace_membership_event import (
    WorkspaceMembershipEvent,
)


class WorkspaceMembershipEventRepository(Protocol):
    """Persistence for durable workspace membership audit events."""

    def add(self, event: WorkspaceMembershipEvent) -> None:
        raise NotImplementedError

    def list_for_workspace(
        self,
        workspace_id: WorkspaceId,
        *,
        limit: int = 100,
    ) -> list[WorkspaceMembershipEvent]:
        raise NotImplementedError
