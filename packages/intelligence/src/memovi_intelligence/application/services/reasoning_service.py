from memovi_intelligence.application.ports import KnowledgeRetriever, ReasoningProvider
from memovi_intelligence.application.services.context_assembler import ContextAssembler
from memovi_intelligence.config import IntelligenceConfig
from memovi_intelligence.domain.entities import (
    ReasoningContext,
    ReasoningRequest,
    ReasoningResult,
)


class ReasoningService:
    """Orchestrates reasoning workflows over retrieved knowledge.

    Coordinates context assembly through KnowledgeRetriever and future AI provider calls.
    Provider execution is intentionally not invoked yet.
    """

    def __init__(
        self,
        *,
        knowledge_retriever: KnowledgeRetriever,
        reasoning_provider: ReasoningProvider,
        config: IntelligenceConfig | None = None,
        context_assembler: ContextAssembler | None = None,
    ) -> None:
        self._config = config or IntelligenceConfig()
        self._knowledge_retriever = knowledge_retriever
        self._reasoning_provider = reasoning_provider
        self._context_assembler = context_assembler or ContextAssembler(
            knowledge_retriever=knowledge_retriever,
            config=self._config,
        )

    @property
    def config(self) -> IntelligenceConfig:
        return self._config

    def prepare_context(self, request: ReasoningRequest) -> ReasoningContext:
        """Assemble reasoning context from retrieved knowledge."""
        return self._context_assembler.assemble(request)

    def reason(self, request: ReasoningRequest) -> ReasoningResult:
        """Run a reasoning workflow for the given request.

        End-to-end provider orchestration is deferred.
        """
        raise NotImplementedError("Reasoning workflows are not implemented yet.")
