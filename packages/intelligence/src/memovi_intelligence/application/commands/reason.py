from memovi_intelligence.application.ports import KnowledgeRetriever, ReasoningProvider
from memovi_intelligence.application.services.context_assembler import ContextAssembler
from memovi_intelligence.domain.entities import ReasoningRequest, ReasoningResult
from memovi_intelligence.domain.exceptions import (
    IntelligenceDomainError,
    InvalidReasoningContextError,
    NoRetrievedKnowledgeError,
    ReasoningProviderError,
)


class Reason:
    """Orchestrates retrieval, context assembly, and provider reasoning.

    Contains orchestration only: retrieve knowledge, assemble context, execute
    reasoning, and return an immutable ReasoningResult.
    """

    def __init__(
        self,
        *,
        knowledge_retriever: KnowledgeRetriever,
        context_assembler: ContextAssembler,
        reasoning_provider: ReasoningProvider,
    ) -> None:
        self._knowledge_retriever = knowledge_retriever
        self._context_assembler = context_assembler
        self._reasoning_provider = reasoning_provider

    def execute(self, request: ReasoningRequest) -> ReasoningResult:
        limit = (
            request.limit
            if request.limit is not None
            else self._context_assembler.config.default_retrieval_limit
        )
        retrieved = tuple(self._knowledge_retriever.retrieve(request, limit=limit))
        if not retrieved:
            raise NoRetrievedKnowledgeError(
                "No knowledge was retrieved for the reasoning request.",
            )

        try:
            context = self._context_assembler.assemble_from(request, retrieved)
        except IntelligenceDomainError:
            raise
        except Exception as exc:
            raise InvalidReasoningContextError(
                "Failed to assemble a valid reasoning context.",
            ) from exc

        if context.is_empty:
            raise NoRetrievedKnowledgeError(
                "Retrieved knowledge could not be retained for reasoning context.",
            )

        try:
            return self._reasoning_provider.reason(context)
        except IntelligenceDomainError:
            raise
        except Exception as exc:
            raise ReasoningProviderError(
                "Reasoning provider failed while producing a result.",
            ) from exc
