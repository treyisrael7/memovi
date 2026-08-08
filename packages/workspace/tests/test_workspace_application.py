from datetime import UTC, datetime

import pytest
from memovi_shared import InvalidWorkspaceIdError, WorkspaceId
from memovi_workspace.application.commands import (
    CreateWorkspace,
    CreateWorkspaceCommand,
    InviteWorkspaceMember,
    InviteWorkspaceMemberCommand,
    LeaveWorkspace,
    LeaveWorkspaceCommand,
    RemoveWorkspaceMember,
    RemoveWorkspaceMemberCommand,
    TransferWorkspaceOwnership,
    TransferWorkspaceOwnershipCommand,
)
from memovi_workspace.application.queries import (
    GetWorkspace,
    GetWorkspaceQuery,
    ListWorkspaceMembers,
    ListWorkspaceMembersQuery,
    ListWorkspaces,
    ListWorkspacesQuery,
)
from memovi_workspace.domain.entities import Workspace, WorkspaceMembership
from memovi_workspace.domain.entities.workspace_membership_event import (
    WorkspaceMembershipEvent,
)
from memovi_workspace.domain.exceptions import (
    CannotLeaveAsSoleOwnerError,
    CannotRemoveLastOwnerError,
    InvalidWorkspaceNameError,
    WorkspaceMemberAlreadyExistsError,
    WorkspaceMembershipRequiredError,
    WorkspaceNotFoundError,
    WorkspaceOwnerRequiredError,
    WorkspaceUserNotFoundError,
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

    def update(self, membership: WorkspaceMembership) -> None:
        for index, item in enumerate(self.memberships):
            if item.id == membership.id or (
                item.user_id == membership.user_id and item.workspace_id == membership.workspace_id
            ):
                self.memberships[index] = membership
                return
        self.add(membership)

    def remove(
        self,
        *,
        user_id: str,
        workspace_id: WorkspaceId,
    ) -> WorkspaceMembership | None:
        for index, item in enumerate(self.memberships):
            if item.user_id == user_id and item.workspace_id == workspace_id:
                return self.memberships.pop(index)
        return None

    def list_for_user(self, user_id: str) -> list[WorkspaceMembership]:
        return [item for item in self.memberships if item.user_id == user_id]

    def list_for_workspace(self, workspace_id: WorkspaceId) -> list[WorkspaceMembership]:
        return [item for item in self.memberships if item.workspace_id == workspace_id]

    def list_workspace_ids_for_user(self, user_id: str) -> list[WorkspaceId]:
        return [item.workspace_id for item in self.list_for_user(user_id)]

    def count_by_role(self, *, workspace_id: WorkspaceId, role: str) -> int:
        return sum(
            1
            for item in self.memberships
            if item.workspace_id == workspace_id and item.role == role
        )


class InMemoryEventRepository:
    def __init__(self) -> None:
        self.events: list[WorkspaceMembershipEvent] = []

    def add(self, event: WorkspaceMembershipEvent) -> None:
        self.events.append(event)

    def list_for_workspace(
        self,
        workspace_id: WorkspaceId,
        *,
        limit: int = 100,
    ) -> list[WorkspaceMembershipEvent]:
        items = [event for event in self.events if event.workspace_id == workspace_id]
        return items[:limit]


class InMemoryUserDirectory:
    def __init__(self, mapping: dict[str, str] | None = None) -> None:
        # email -> user_id
        self.by_email = mapping or {}

    def find_user_id_by_email(self, email: str) -> str | None:
        return self.by_email.get(email.strip().lower())

    def find_email_by_user_id(self, user_id: str) -> str | None:
        for email, mapped in self.by_email.items():
            if mapped == user_id:
                return email
        return None


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
    assert workspace.role == "owner"


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


def test_list_workspaces_includes_role() -> None:
    repo = InMemoryWorkspaceRepository()
    memberships = InMemoryMembershipRepository()
    CreateWorkspace(workspaces=repo, memberships=memberships).execute(
        CreateWorkspaceCommand(name="Work", owner_user_id="user-1"),
    )
    listed = ListWorkspaces(workspaces=repo, memberships=memberships).execute(
        ListWorkspacesQuery(user_id="user-1"),
    )
    assert len(listed) == 1
    assert listed[0].role == "owner"


def test_invite_remove_transfer_leave_membership_lifecycle() -> None:
    repo = InMemoryWorkspaceRepository()
    memberships = InMemoryMembershipRepository()
    events = InMemoryEventRepository()
    users = InMemoryUserDirectory({"member@example.com": "user-2"})
    created = CreateWorkspace(workspaces=repo, memberships=memberships).execute(
        CreateWorkspaceCommand(name="Team", owner_user_id="user-1"),
    )
    workspace_id = created.workspace.id

    invited = InviteWorkspaceMember(
        workspaces=repo,
        memberships=memberships,
        events=events,
        users=users,
    ).execute(
        InviteWorkspaceMemberCommand(
            workspace_id=workspace_id,
            actor_user_id="user-1",
            email="member@example.com",
        )
    )
    assert invited.role == "member"
    assert events.events[-1].event_type == "member_invited"

    members = ListWorkspaceMembers(
        workspaces=repo,
        memberships=memberships,
        users=users,
    ).execute(ListWorkspaceMembersQuery(workspace_id=workspace_id, actor_user_id="user-1"))
    assert len(members) == 2

    with pytest.raises(WorkspaceOwnerRequiredError):
        InviteWorkspaceMember(
            workspaces=repo,
            memberships=memberships,
            events=events,
            users=users,
        ).execute(
            InviteWorkspaceMemberCommand(
                workspace_id=workspace_id,
                actor_user_id="user-2",
                email="someone@example.com",
            )
        )

    with pytest.raises(CannotLeaveAsSoleOwnerError):
        LeaveWorkspace(workspaces=repo, memberships=memberships, events=events).execute(
            LeaveWorkspaceCommand(workspace_id=workspace_id, user_id="user-1"),
        )

    TransferWorkspaceOwnership(
        workspaces=repo,
        memberships=memberships,
        events=events,
        users=users,
    ).execute(
        TransferWorkspaceOwnershipCommand(
            workspace_id=workspace_id,
            actor_user_id="user-1",
            new_owner_user_id="user-2",
        )
    )
    assert memberships.get(user_id="user-2", workspace_id=WorkspaceId(workspace_id)).is_owner
    assert events.events[-1].event_type == "ownership_transferred"

    LeaveWorkspace(workspaces=repo, memberships=memberships, events=events).execute(
        LeaveWorkspaceCommand(workspace_id=workspace_id, user_id="user-1"),
    )
    assert not memberships.is_member(
        user_id="user-1",
        workspace_id=WorkspaceId(workspace_id),
    )
    assert events.events[-1].event_type == "member_left"


def test_cannot_remove_last_owner() -> None:
    repo = InMemoryWorkspaceRepository()
    memberships = InMemoryMembershipRepository()
    events = InMemoryEventRepository()
    created = CreateWorkspace(workspaces=repo, memberships=memberships).execute(
        CreateWorkspaceCommand(name="Solo", owner_user_id="user-1"),
    )
    with pytest.raises(CannotRemoveLastOwnerError):
        RemoveWorkspaceMember(
            workspaces=repo,
            memberships=memberships,
            events=events,
        ).execute(
            RemoveWorkspaceMemberCommand(
                workspace_id=created.workspace.id,
                actor_user_id="user-1",
                target_user_id="user-1",
            )
        )


def test_invite_unknown_user() -> None:
    repo = InMemoryWorkspaceRepository()
    memberships = InMemoryMembershipRepository()
    events = InMemoryEventRepository()
    users = InMemoryUserDirectory()
    created = CreateWorkspace(workspaces=repo, memberships=memberships).execute(
        CreateWorkspaceCommand(name="Team", owner_user_id="user-1"),
    )
    with pytest.raises(WorkspaceUserNotFoundError):
        InviteWorkspaceMember(
            workspaces=repo,
            memberships=memberships,
            events=events,
            users=users,
        ).execute(
            InviteWorkspaceMemberCommand(
                workspace_id=created.workspace.id,
                actor_user_id="user-1",
                email="missing@example.com",
            )
        )


def test_invite_duplicate_member() -> None:
    repo = InMemoryWorkspaceRepository()
    memberships = InMemoryMembershipRepository()
    events = InMemoryEventRepository()
    users = InMemoryUserDirectory({"member@example.com": "user-2"})
    created = CreateWorkspace(workspaces=repo, memberships=memberships).execute(
        CreateWorkspaceCommand(name="Team", owner_user_id="user-1"),
    )
    InviteWorkspaceMember(
        workspaces=repo,
        memberships=memberships,
        events=events,
        users=users,
    ).execute(
        InviteWorkspaceMemberCommand(
            workspace_id=created.workspace.id,
            actor_user_id="user-1",
            email="member@example.com",
        )
    )
    with pytest.raises(WorkspaceMemberAlreadyExistsError):
        InviteWorkspaceMember(
            workspaces=repo,
            memberships=memberships,
            events=events,
            users=users,
        ).execute(
            InviteWorkspaceMemberCommand(
                workspace_id=created.workspace.id,
                actor_user_id="user-1",
                email="member@example.com",
            )
        )


def test_invalid_workspace_name() -> None:
    repo = InMemoryWorkspaceRepository()
    memberships = InMemoryMembershipRepository()
    with pytest.raises(InvalidWorkspaceNameError):
        CreateWorkspace(workspaces=repo, memberships=memberships).execute(
            CreateWorkspaceCommand(name="   ", owner_user_id="user-1"),
        )


def test_get_workspace_invalid_id() -> None:
    repo = InMemoryWorkspaceRepository()
    memberships = InMemoryMembershipRepository()
    with pytest.raises(InvalidWorkspaceIdError):
        GetWorkspace(workspaces=repo, memberships=memberships).execute(
            GetWorkspaceQuery(workspace_id="not-a-uuid", user_id="user-1"),
        )


def test_get_missing_workspace() -> None:
    repo = InMemoryWorkspaceRepository()
    memberships = InMemoryMembershipRepository()
    missing_id = "00000000-0000-4000-8000-000000000099"
    memberships.add(
        WorkspaceMembership.create(
            workspace_id=WorkspaceId(missing_id),
            user_id="user-1",
            role="member",
            now=datetime.now(UTC),
        )
    )
    with pytest.raises(WorkspaceNotFoundError):
        GetWorkspace(workspaces=repo, memberships=memberships).execute(
            GetWorkspaceQuery(workspace_id=missing_id, user_id="user-1"),
        )
