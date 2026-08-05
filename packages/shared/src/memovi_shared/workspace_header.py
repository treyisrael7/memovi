"""Shared workspace request header constants and parsing helpers."""

from memovi_shared.workspace_id import DEFAULT_WORKSPACE_ID, WorkspaceId

WORKSPACE_HEADER = "X-Memovi-Workspace-Id"


def parse_workspace_id(header_value: str | None) -> WorkspaceId:
    """Parse the active workspace from an ``X-Memovi-Workspace-Id`` header value.

    Returns the seeded default workspace when the header is absent or blank.
    Raises ``InvalidWorkspaceIdError`` when the value is present but not a UUID.
    """
    if header_value is None or not header_value.strip():
        return DEFAULT_WORKSPACE_ID
    return WorkspaceId(header_value.strip())
