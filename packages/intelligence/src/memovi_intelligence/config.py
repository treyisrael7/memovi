from dataclasses import dataclass

from memovi_intelligence.domain.exceptions import InvalidIntelligenceConfigError


@dataclass(frozen=True, slots=True)
class IntelligenceConfig:
    """Typed package configuration for Intelligence.

    Provider selection is intentionally deferred until provider adapters are introduced.
    """

    default_retrieval_limit: int = 5
    max_retrieved_passages: int = 8

    def __post_init__(self) -> None:
        if self.default_retrieval_limit < 1:
            raise InvalidIntelligenceConfigError(
                "default_retrieval_limit must be at least 1.",
            )
        if self.max_retrieved_passages < 1:
            raise InvalidIntelligenceConfigError(
                "max_retrieved_passages must be at least 1.",
            )
        if self.default_retrieval_limit > self.max_retrieved_passages:
            raise InvalidIntelligenceConfigError(
                "default_retrieval_limit cannot exceed max_retrieved_passages.",
            )
