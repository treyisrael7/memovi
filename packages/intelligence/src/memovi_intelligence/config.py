from dataclasses import dataclass

from memovi_intelligence.domain.exceptions import InvalidIntelligenceConfigError


@dataclass(frozen=True, slots=True)
class IntelligenceConfig:
    """Typed package configuration for Intelligence.

    Provider selection is intentionally deferred until provider adapters are introduced.
    """

    default_retrieval_limit: int = 20
    max_documents: int = 8
    max_chunks: int = 16
    max_estimated_tokens: int = 4_000

    def __post_init__(self) -> None:
        if self.default_retrieval_limit < 1:
            raise InvalidIntelligenceConfigError(
                "default_retrieval_limit must be at least 1.",
            )
        if self.max_documents < 1:
            raise InvalidIntelligenceConfigError("max_documents must be at least 1.")
        if self.max_chunks < 1:
            raise InvalidIntelligenceConfigError("max_chunks must be at least 1.")
        if self.max_estimated_tokens < 1:
            raise InvalidIntelligenceConfigError("max_estimated_tokens must be at least 1.")
