class WorkspaceDomainError(Exception):
    """Base exception for workspace domain invariant failures."""


class InvalidWorkspaceNameError(WorkspaceDomainError):
    """Raised when a workspace name is invalid."""


class WorkspaceNotFoundError(WorkspaceDomainError):
    """Raised when a requested workspace does not exist."""


class WorkspaceMembershipRequiredError(WorkspaceDomainError):
    """Raised when the authenticated user is not a member of the workspace."""
