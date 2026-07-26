from datetime import UTC, datetime

import pytest
from memovi_shared import DEFAULT_WORKSPACE_ID, InvalidWorkspaceIdError, WorkspaceId
from memovi_workspace.application.commands import CreateWorkspace, CreateWorkspaceCommand
from memovi_workspace.application.queries import (
    GetWorkspace,
    GetWorkspaceQuery,
    ListWorkspaces,
    ListWorkspacesQuery,
)
from memovi_workspace.domain.entities import Workspace, WorkspaceMembership
from memovi_workspace.domain.exceptions import (
    InvalidWorkspaceNameError,
    WorkspaceMembershipRequiredError,
    WorkspaceNotFoundError,
)


class InMemoryWorkspaceRepository:
    def __init__(self) -> None:
        self.workspaces: dict[str, Workspace] = {}

    def get_by_id(self, workspace_id: WorkspaceId) -> Workspace | None:
        return self.workspaces.get(workspace_id.value)

    def add(self, workspace: Workspace) -> None:
        self.workspaces[workspace.id.value] = workspace

    def list_all(self) -> list[Workspace]:
        return sorted(self.workspaces.values(), key=lambda item: item.created_at)


class InMemoryMembershipRepository:
    def __init__(self) -> None:
        self.memberships: list[WorkspaceMembership] = []

    def is_member(self, *, user_id: str, workspace_id: WorkspaceId) -> bool:
        return self.get(user_id=user_id, workspace_id=workspace_id) is not None

    def get(
        self,
        *,
        user_id: str,
        workspace_id: WorkspaceId,
    ) -> WorkspaceMembership | None:
        for item in self.memberships:
            if item.user_id == user_id and item.workspace_id == workspace_id:
                return item
        return None

    def add(self, membership: WorkspaceMembership) -> None:
        if self.get(user_id=membership.user_id, workspace_id=membership.workspace_id) is None:
            self.memberships.append(membership)

    def list_for_user(self, user_id: str) -> list[WorkspaceMembership]:
        return [item for item in self.memberships if item.user_id == user_id]

    def list_workspace_ids_for_user(self, user_id: str) -> list[WorkspaceId]:
        return [item.workspace_id for item in self.list_for_user(user_id)]


def test_create_workspace() -> None:
    repo = InMemoryWorkspaceRepository()
    memberships = InMemoryMembershipRepository()
    result = CreateWorkspace(workspaces=repo, memberships=memberships).execute(
        CreateWorkspaceCommand(name=" Personal ", owner_user_id="user-1"),
    )

    assert result.workspace.name == "Personal"
    assert repo.get_by_id(WorkspaceId(result.workspace.id)) is not None
    assert memberships.is_member(
        user_id="user-1",
        workspace_id=WorkspaceId(result.workspace.id),
    )


def test_get_workspace() -> None:
    repo = InMemoryWorkspaceRepository()
    memberships = InMemoryMembershipRepository()
    created = CreateWorkspace(workspaces=repo, memberships=memberships).execute(
        CreateWorkspaceCommand(name="Work", owner_user_id="user-1"),
    )
    workspace = GetWorkspace(workspaces=repo, memberships=memberships).execute(
        GetWorkspaceQuery(workspace_id=created.workspace.id, user_id="user-1"),
    )

    assert workspace.id == created.workspace.id
    assert workspace.name == "Work"


def test_get_workspace_requires_membership() -> None:
    repo = InMemoryWorkspaceRepository()
    memberships = InMemoryMembershipRepository()
    created = CreateWorkspace(workspaces=repo, memberships=memberships).execute(
        CreateWorkspaceCommand(name="Work", owner_user_id="user-1"),
    )
    with pytest.raises(WorkspaceMembershipRequiredError):
        GetWorkspace(workspaces=repo, memberships=memberships).execute(
            GetWorkspaceQuery(workspace_id=created.workspace.id, user_id="user-2"),
        )


def test_get_workspace_missing() -> None:
    repo = InMemoryWorkspaceRepository()
    memberships = InMemoryMembershipRepository()
    with pytest.raises(WorkspaceNotFoundError):
        GetWorkspace(workspaces=repo, memberships=memberships).execute(
            GetWorkspaceQuery(workspace_id=str(WorkspaceId.new()), user_id="user-1"),
        )


def test_get_workspace_invalid_id() -> None:
    repo = InMemoryWorkspaceRepository()
    memberships = InMemoryMembershipRepository()
    with pytest.raises(InvalidWorkspaceIdError):
        GetWorkspace(workspaces=repo, memberships=memberships).execute(
            GetWorkspaceQuery(workspace_id="bad", user_id="user-1"),
        )


def test_list_workspaces_for_user() -> None:
    repo = InMemoryWorkspaceRepository()
    memberships = InMemoryMembershipRepository()
    CreateWorkspace(workspaces=repo, memberships=memberships).execute(
        CreateWorkspaceCommand(name="A", owner_user_id="user-1"),
    )
    CreateWorkspace(workspaces=repo, memberships=memberships).execute(
        CreateWorkspaceCommand(name="B", owner_user_id="user-2"),
    )

    workspaces = ListWorkspaces(workspaces=repo, memberships=memberships).execute(
        ListWorkspacesQuery(user_id="user-1"),
    )
    assert len(workspaces) == 1
    assert workspaces[0].name == "A"


def test_default_workspace_factory() -> None:
    workspace = Workspace.default(now=datetime(2026, 1, 1, tzinfo=UTC))
    assert workspace.id == DEFAULT_WORKSPACE_ID
    assert workspace.name == "Default"


def test_invalid_workspace_name() -> None:
    with pytest.raises(InvalidWorkspaceNameError):
        Workspace.create(name="   ")
