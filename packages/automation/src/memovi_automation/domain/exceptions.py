class AutomationDomainError(Exception):
    """Base exception for automation / capability domain failures."""


class InvalidCapabilityError(AutomationDomainError):
    """Raised when a capability value object or registration violates constraints."""


class UnknownCapabilityError(AutomationDomainError):
    """Raised when a requested capability is not registered."""


class InvalidCapabilityArgumentsError(AutomationDomainError):
    """Raised when capability arguments fail schema validation."""


class CapabilityExecutionError(AutomationDomainError):
    """Raised when a capability fails during execution."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "execution_failed",
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details: dict[str, object] = {} if details is None else dict(details)


class CapabilityTimeoutError(AutomationDomainError):
    """Raised when a capability exceeds its allotted execution time."""


class CapabilityCancelledError(AutomationDomainError):
    """Raised when a capability invocation is cancelled."""
