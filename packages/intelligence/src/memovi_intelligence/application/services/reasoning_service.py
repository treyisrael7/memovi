from memovi_intelligence.application.ports import KnowledgeRetriever, ReasoningProvider
from memovi_intelligence.config import IntelligenceConfig
from memovi_intelligence.domain.entities import (
    ReasoningContext,
    ReasoningRequest,
    ReasoningResult,
)


class ReasoningService:
    """Orchestrates reasoning workflows over retrieved knowledge.

    Coordinates future Search retrieval and AI provider calls through ports.
    Concrete retrieval and provider execution are intentionally not invoked yet.
    """

    def __init__(
        self,
        *,
        knowledge_retriever: KnowledgeRetriever,
        reasoning_provider: ReasoningProvider,
        config: IntelligenceConfig | None = None,
    ) -> None:
        self._knowledge_retriever = knowledge_retriever
        self._reasoning_provider = reasoning_provider
        self._config = config or IntelligenceConfig()

    @property
    def config(self) -> IntelligenceConfig:
        return self._config

    def prepare_context(self, request: ReasoningRequest) -> ReasoningContext:
        """Prepare reasoning context for a future provider.

        KnowledgeRetriever coordination with Search is deferred.
        """
        raise NotImplementedError("Knowledge retrieval is not implemented yet.")

    def reason(self, request: ReasoningRequest) -> ReasoningResult:
        """Run a reasoning workflow for the given request.

        End-to-end orchestration against Search and providers is deferred.
        """
        raise NotImplementedError("Reasoning workflows are not implemented yet.")
