from dataclasses import dataclass

from memovi_intelligence.domain.entities.reasoning_context import ReasoningContext
from memovi_intelligence.domain.exceptions import InvalidReasoningResultError


@dataclass(frozen=True, slots=True)
class ReasoningResult:
    """Immutable output produced by a reasoning workflow."""

    content: str
    context: ReasoningContext

    def __post_init__(self) -> None:
        normalized = self.content.strip()
        if not normalized:
            raise InvalidReasoningResultError("Reasoning result content is required.")
        object.__setattr__(self, "content", normalized)

    @classmethod
    def create(cls, *, content: str, context: ReasoningContext) -> ReasoningResult:
        return cls(content=content, context=context)
