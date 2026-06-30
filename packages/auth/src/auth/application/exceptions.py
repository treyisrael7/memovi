class AuthApplicationError(Exception):
    """Base exception for local authentication use-case failures."""


class EmailAlreadyRegisteredError(AuthApplicationError):
    """Raised when registration would create a duplicate local identity."""


class InvalidCredentialsError(AuthApplicationError):
    """Raised when login credentials do not match a local user."""


class UnauthenticatedError(AuthApplicationError):
    """Raised when a request does not have an active local session."""
