import pytest

from memovi_shared import DEFAULT_WORKSPACE_ID, InvalidWorkspaceIdError, WorkspaceId


def test_workspace_id_new_generates_valid_uuid() -> None:
    workspace_id = WorkspaceId.new()
    assert WorkspaceId(workspace_id.value) == workspace_id


def test_workspace_id_rejects_invalid_value() -> None:
    with pytest.raises(InvalidWorkspaceIdError):
        WorkspaceId("not-a-uuid")


def test_default_workspace_id_is_stable() -> None:
    assert DEFAULT_WORKSPACE_ID.value == "00000000-0000-4000-8000-000000000001"
    assert WorkspaceId.default() == DEFAULT_WORKSPACE_ID
