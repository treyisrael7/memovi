from typing import Protocol

from memovi_intelligence.domain.entities import (
    ReasoningContext,
    ReasoningRequest,
    ReasoningResult,
)


class KnowledgeRetriever(Protocol):
    """Retrieves knowledge for reasoning without coupling to Search internals."""

    def retrieve(self, request: ReasoningRequest, *, limit: int) -> ReasoningContext:
        raise NotImplementedError


class ReasoningProvider(Protocol):
    """Produces reasoning output from prepared context without exposing provider details."""

    def reason(self, context: ReasoningContext) -> ReasoningResult:
        raise NotImplementedError
