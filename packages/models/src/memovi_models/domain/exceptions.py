class ModelsDomainError(Exception):
    """Base exception for model provider framework failures."""


class InvalidModelError(ModelsDomainError):
    """Raised when a model value object or registration violates constraints."""


class UnknownProviderError(ModelsDomainError):
    """Raised when a requested provider is not registered."""


class UnknownModelError(ModelsDomainError):
    """Raised when a requested model is not known to a provider."""


class ModelProviderError(ModelsDomainError):
    """Normalized provider failure with a stable error code."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details: dict[str, object] = {} if details is None else dict(details)


# Stable normalized error codes for provider failures.
AUTHENTICATION_ERROR = "authentication"
UNAVAILABLE_ERROR = "unavailable"
RATE_LIMIT_ERROR = "rate_limit"
TIMEOUT_ERROR = "timeout"
UNSUPPORTED_CAPABILITY_ERROR = "unsupported_capability"
INVALID_CONFIGURATION_ERROR = "invalid_configuration"
INVALID_REQUEST_ERROR = "invalid_request"
PROVIDER_ERROR = "provider_error"
