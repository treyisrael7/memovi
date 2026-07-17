class IntelligenceDomainError(Exception):
    """Base exception for intelligence domain invariant failures."""


class InvalidReasoningRequestIdError(IntelligenceDomainError):
    """Raised when a reasoning request identifier is malformed."""


class InvalidReasoningQueryError(IntelligenceDomainError):
    """Raised when a reasoning query violates domain constraints."""


class InvalidRetrievedKnowledgeError(IntelligenceDomainError):
    """Raised when retrieved knowledge violates domain constraints."""


class InvalidAssembledDocumentError(IntelligenceDomainError):
    """Raised when an assembled document violates domain constraints."""


class InvalidContextMetadataError(IntelligenceDomainError):
    """Raised when context metadata violates domain constraints."""


class InvalidReasoningRequestError(IntelligenceDomainError):
    """Raised when a reasoning request violates its invariants."""


class InvalidReasoningContextError(IntelligenceDomainError):
    """Raised when a reasoning context violates its invariants."""


class InvalidReasoningResultError(IntelligenceDomainError):
    """Raised when a reasoning result violates its invariants."""


class InvalidExecutionTraceError(IntelligenceDomainError):
    """Raised when execution tracing value objects violate domain constraints."""


class InvalidCitationError(IntelligenceDomainError):
    """Raised when a citation violates domain constraints."""


class InvalidPromptError(IntelligenceDomainError):
    """Raised when a prompt or prompt component violates domain constraints."""


class NoRetrievedKnowledgeError(IntelligenceDomainError):
    """Raised when reasoning cannot proceed because retrieval returned no knowledge."""


class ReasoningProviderError(IntelligenceDomainError):
    """Raised when a reasoning provider fails during execution."""


class UnknownReasoningProviderError(IntelligenceDomainError):
    """Raised when the configured reasoning provider is not recognized."""


class ReasoningProviderUnavailableError(IntelligenceDomainError):
    """Raised when a known reasoning provider is not registered or ready."""


class ReasoningProviderTimeoutError(IntelligenceDomainError):
    """Raised when a reasoning provider exceeds its allotted execution time."""


class InvalidIntelligenceConfigError(IntelligenceDomainError):
    """Raised when intelligence package configuration is invalid."""
