from typing import Protocol

from memovi_intelligence.domain.entities import (
    ReasoningContext,
    ReasoningRequest,
    ReasoningResult,
)
from memovi_intelligence.domain.value_objects import RetrievedKnowledge


class KnowledgeRetriever(Protocol):
    """Retrieves ranked knowledge for reasoning without coupling to Search internals."""

    def retrieve(
        self,
        request: ReasoningRequest,
        *,
        limit: int,
    ) -> tuple[RetrievedKnowledge, ...]:
        raise NotImplementedError


class ReasoningProvider(Protocol):
    """Produces reasoning output from prepared context without exposing provider details."""

    def reason(self, context: ReasoningContext) -> ReasoningResult:
        raise NotImplementedError
