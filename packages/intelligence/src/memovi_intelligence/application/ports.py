from typing import Protocol

from memovi_intelligence.domain.entities import ReasoningRequest, ReasoningResult
from memovi_intelligence.domain.value_objects import Prompt, RetrievedKnowledge


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
    """Produces reasoning output from a provider-agnostic prompt."""

    def reason(self, prompt: Prompt) -> ReasoningResult:
        raise NotImplementedError
