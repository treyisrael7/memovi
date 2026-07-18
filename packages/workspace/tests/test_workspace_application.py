from datetime import UTC, datetime

import pytest
from memovi_shared import DEFAULT_WORKSPACE_ID, InvalidWorkspaceIdError, WorkspaceId

from memovi_workspace.application.commands import CreateWorkspace, CreateWorkspaceCommand
from memovi_workspace.application.queries import GetWorkspace, GetWorkspaceQuery, ListWorkspaces
from memovi_workspace.domain.entities import Workspace
from memovi_workspace.domain.exceptions import InvalidWorkspaceNameError, WorkspaceNotFoundError


class InMemoryWorkspaceRepository:
    def __init__(self) -> None:
        self.workspaces: dict[str, Workspace] = {}

    def get_by_id(self, workspace_id: WorkspaceId) -> Workspace | None:
        return self.workspaces.get(workspace_id.value)

    def add(self, workspace: Workspace) -> None:
        self.workspaces[workspace.id.value] = workspace

    def list_all(self) -> list[Workspace]:
        return sorted(self.workspaces.values(), key=lambda item: item.created_at)


def test_create_workspace() -> None:
    repo = InMemoryWorkspaceRepository()
    result = CreateWorkspace(workspaces=repo).execute(CreateWorkspaceCommand(name=" Personal "))

    assert result.workspace.name == "Personal"
    assert repo.get_by_id(WorkspaceId(result.workspace.id)) is not None


def test_get_workspace() -> None:
    repo = InMemoryWorkspaceRepository()
    created = CreateWorkspace(workspaces=repo).execute(CreateWorkspaceCommand(name="Work"))
    workspace = GetWorkspace(workspaces=repo).execute(
        GetWorkspaceQuery(workspace_id=created.workspace.id)
    )

    assert workspace.id == created.workspace.id
    assert workspace.name == "Work"


def test_get_workspace_missing() -> None:
    repo = InMemoryWorkspaceRepository()
    with pytest.raises(WorkspaceNotFoundError):
        GetWorkspace(workspaces=repo).execute(
            GetWorkspaceQuery(workspace_id=str(WorkspaceId.new())),
        )


def test_get_workspace_invalid_id() -> None:
    repo = InMemoryWorkspaceRepository()
    with pytest.raises(InvalidWorkspaceIdError):
        GetWorkspace(workspaces=repo).execute(GetWorkspaceQuery(workspace_id="bad"))


def test_list_workspaces() -> None:
    repo = InMemoryWorkspaceRepository()
    CreateWorkspace(workspaces=repo).execute(CreateWorkspaceCommand(name="A"))
    CreateWorkspace(workspaces=repo).execute(CreateWorkspaceCommand(name="B"))

    workspaces = ListWorkspaces(workspaces=repo).execute()
    assert len(workspaces) == 2


def test_default_workspace_factory() -> None:
    workspace = Workspace.default(now=datetime(2026, 1, 1, tzinfo=UTC))
    assert workspace.id == DEFAULT_WORKSPACE_ID
    assert workspace.name == "Default"


def test_invalid_workspace_name() -> None:
    with pytest.raises(InvalidWorkspaceNameError):
        Workspace.create(name="   ")
