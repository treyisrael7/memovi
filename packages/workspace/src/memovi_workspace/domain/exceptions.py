class WorkspaceDomainError(Exception):
    """Base exception for workspace domain invariant failures."""


class InvalidWorkspaceNameError(WorkspaceDomainError):
    """Raised when a workspace name is invalid."""


class WorkspaceNotFoundError(WorkspaceDomainError):
    """Raised when a requested workspace does not exist."""
