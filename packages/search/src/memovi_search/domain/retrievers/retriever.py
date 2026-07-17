from dataclasses import dataclass
from typing import Protocol

from memovi_search.domain.entities.search_result import SearchResult


@dataclass(frozen=True, slots=True)
class RetrievalRequest:
    """Input for a single retriever invocation."""

    query: str
    limit: int


class Retriever(Protocol):
    """Strategy that returns ranked search hits for a retrieval request."""

    def retrieve(self, request: RetrievalRequest) -> list[SearchResult]:
        raise NotImplementedError
