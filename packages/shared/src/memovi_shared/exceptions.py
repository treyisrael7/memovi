class SharedDomainError(Exception):
    """Base exception for shared primitive invariant failures."""


class InvalidWorkspaceIdError(SharedDomainError):
    """Raised when a workspace identifier is malformed."""
