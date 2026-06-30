class AuthDomainError(Exception):
    """Base exception for authentication domain invariant failures."""


class InvalidEmailError(AuthDomainError):
    """Raised when an email address cannot identify a local Memovi user."""


class InvalidPasswordHashError(AuthDomainError):
    """Raised when a password hash does not match the supported local format."""


class InvalidUserIdError(AuthDomainError):
    """Raised when a user identifier is malformed."""


class InvalidSessionError(AuthDomainError):
    """Raised when a session entity violates its invariants."""
