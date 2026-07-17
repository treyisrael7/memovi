from dataclasses import dataclass

from memovi_intelligence.domain.exceptions import InvalidReasoningContextError
from memovi_intelligence.domain.value_objects import ReasoningQuery, RetrievedPassage


@dataclass(frozen=True, slots=True)
class ReasoningContext:
    """Immutable knowledge context prepared for a future reasoning provider."""

    query: ReasoningQuery
    passages: tuple[RetrievedPassage, ...]

    def __post_init__(self) -> None:
        if any(not isinstance(passage, RetrievedPassage) for passage in self.passages):
            raise InvalidReasoningContextError(
                "Reasoning context passages must be RetrievedPassage instances.",
            )
        object.__setattr__(self, "passages", tuple(self.passages))

    @classmethod
    def create(
        cls,
        *,
        query: str | ReasoningQuery,
        passages: list[RetrievedPassage] | tuple[RetrievedPassage, ...] | None = None,
    ) -> ReasoningContext:
        normalized_query = query if isinstance(query, ReasoningQuery) else ReasoningQuery(query)
        return cls(
            query=normalized_query,
            passages=tuple(passages or ()),
        )

    @property
    def is_empty(self) -> bool:
        return len(self.passages) == 0
