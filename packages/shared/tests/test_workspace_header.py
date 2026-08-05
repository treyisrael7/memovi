import pytest
from memovi_shared import (
    DEFAULT_WORKSPACE_ID,
    WORKSPACE_HEADER,
    InvalidWorkspaceIdError,
    parse_workspace_id,
)


def test_workspace_header_constant() -> None:
    assert WORKSPACE_HEADER == "X-Memovi-Workspace-Id"


def test_parse_workspace_id_uses_default_when_missing() -> None:
    assert parse_workspace_id(None) == DEFAULT_WORKSPACE_ID
    assert parse_workspace_id("") == DEFAULT_WORKSPACE_ID
    assert parse_workspace_id("   ") == DEFAULT_WORKSPACE_ID


def test_parse_workspace_id_parses_valid_uuid() -> None:
    workspace_id = parse_workspace_id("00000000-0000-4000-8000-000000000002")
    assert workspace_id.value == "00000000-0000-4000-8000-000000000002"


def test_parse_workspace_id_rejects_invalid_value() -> None:
    with pytest.raises(InvalidWorkspaceIdError):
        parse_workspace_id("not-a-uuid")
