class WorkspaceDomainError(Exception):
    """Base exception for workspace domain invariant failures."""


class InvalidWorkspaceNameError(WorkspaceDomainError):
    """Raised when a workspace name is invalid."""


class WorkspaceNotFoundError(WorkspaceDomainError):
    """Raised when a requested workspace does not exist."""


class WorkspaceMembershipRequiredError(WorkspaceDomainError):
    """Raised when the authenticated user is not a member of the workspace."""


class WorkspaceOwnerRequiredError(WorkspaceDomainError):
    """Raised when an owner role is required for the operation."""


class WorkspaceMemberNotFoundError(WorkspaceDomainError):
    """Raised when a membership target cannot be found."""


class WorkspaceMemberAlreadyExistsError(WorkspaceDomainError):
    """Raised when inviting a user who is already a member."""


class WorkspaceUserNotFoundError(WorkspaceDomainError):
    """Raised when an invite target email does not match a registered user."""


class CannotRemoveLastOwnerError(WorkspaceDomainError):
    """Raised when removing or demoting the last owner would orphan the workspace."""


class CannotLeaveAsSoleOwnerError(WorkspaceDomainError):
    """Raised when the sole owner attempts to leave without transferring ownership."""
