from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from memovi_intelligence.domain.entities.reasoning_context import ReasoningContext
from memovi_intelligence.domain.exceptions import InvalidReasoningResultError
from memovi_intelligence.domain.value_objects.citation import Citation


@dataclass(frozen=True, slots=True)
class ReasoningResult:
    """Immutable output produced by a reasoning workflow."""

    answer: str
    citations: tuple[Citation, ...]
    metadata: Mapping[str, object]
    provider: str
    execution_time: float
    context: ReasoningContext

    def __post_init__(self) -> None:
        answer = self.answer.strip()
        provider = self.provider.strip()

        if not answer:
            raise InvalidReasoningResultError("Reasoning result answer is required.")
        if not provider:
            raise InvalidReasoningResultError("Reasoning result provider is required.")
        if self.execution_time < 0:
            raise InvalidReasoningResultError("execution_time cannot be negative.")
        if any(not isinstance(citation, Citation) for citation in self.citations):
            raise InvalidReasoningResultError("citations must contain Citation instances.")
        if not isinstance(self.metadata, Mapping):
            raise InvalidReasoningResultError("metadata must be a mapping.")

        object.__setattr__(self, "answer", answer)
        object.__setattr__(self, "provider", provider)
        object.__setattr__(self, "citations", tuple(self.citations))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @classmethod
    def create(
        cls,
        *,
        answer: str,
        citations: tuple[Citation, ...] = (),
        metadata: Mapping[str, object] | None = None,
        provider: str,
        execution_time: float,
        context: ReasoningContext,
    ) -> ReasoningResult:
        return cls(
            answer=answer,
            citations=citations,
            metadata={} if metadata is None else metadata,
            provider=provider,
            execution_time=execution_time,
            context=context,
        )
