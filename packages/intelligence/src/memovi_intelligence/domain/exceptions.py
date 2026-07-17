class IntelligenceDomainError(Exception):
    """Base exception for intelligence domain invariant failures."""


class InvalidReasoningRequestIdError(IntelligenceDomainError):
    """Raised when a reasoning request identifier is malformed."""


class InvalidReasoningQueryError(IntelligenceDomainError):
    """Raised when a reasoning query violates domain constraints."""


class InvalidRetrievedPassageError(IntelligenceDomainError):
    """Raised when a retrieved passage violates domain constraints."""


class InvalidReasoningRequestError(IntelligenceDomainError):
    """Raised when a reasoning request violates its invariants."""


class InvalidReasoningContextError(IntelligenceDomainError):
    """Raised when a reasoning context violates its invariants."""


class InvalidReasoningResultError(IntelligenceDomainError):
    """Raised when a reasoning result violates its invariants."""


class InvalidIntelligenceConfigError(IntelligenceDomainError):
    """Raised when intelligence package configuration is invalid."""
