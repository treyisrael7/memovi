from dataclasses import dataclass

from memovi_intelligence.domain.exceptions import InvalidReasoningRequestError
from memovi_intelligence.domain.value_objects import ReasoningQuery, ReasoningRequestId


@dataclass(frozen=True, slots=True)
class ReasoningRequest:
    """Immutable intent to reason over retrieved knowledge."""

    id: ReasoningRequestId
    query: ReasoningQuery
    limit: int | None = None

    def __post_init__(self) -> None:
        if self.limit is not None and self.limit < 1:
            raise InvalidReasoningRequestError("Retrieval limit must be at least 1 when provided.")

    @classmethod
    def create(
        cls,
        *,
        query: str,
        limit: int | None = None,
        request_id: ReasoningRequestId | None = None,
    ) -> ReasoningRequest:
        return cls(
            id=request_id or ReasoningRequestId.new(),
            query=ReasoningQuery(query),
            limit=limit,
        )
