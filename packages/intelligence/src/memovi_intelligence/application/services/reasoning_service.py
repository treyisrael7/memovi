from memovi_intelligence.application.ports import KnowledgeRetriever, ReasoningProvider
from memovi_intelligence.application.services.context_assembler import ContextAssembler
from memovi_intelligence.application.services.prompt_builder import PromptBuilder
from memovi_intelligence.config import IntelligenceConfig
from memovi_intelligence.domain.entities import (
    ReasoningContext,
    ReasoningRequest,
    ReasoningResult,
)


class ReasoningService:
    """Coordinates context preparation and reasoning workflows.

    Context assembly is available directly. End-to-end reasoning delegates to the
    Reason command.
    """

    def __init__(
        self,
        *,
        knowledge_retriever: KnowledgeRetriever,
        reasoning_provider: ReasoningProvider,
        config: IntelligenceConfig | None = None,
        context_assembler: ContextAssembler | None = None,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        self._config = config or IntelligenceConfig()
        self._knowledge_retriever = knowledge_retriever
        self._reasoning_provider = reasoning_provider
        self._context_assembler = context_assembler or ContextAssembler(
            knowledge_retriever=knowledge_retriever,
            config=self._config,
        )
        self._prompt_builder = prompt_builder or PromptBuilder()

    @property
    def config(self) -> IntelligenceConfig:
        return self._config

    def prepare_context(self, request: ReasoningRequest) -> ReasoningContext:
        """Assemble reasoning context from retrieved knowledge."""
        return self._context_assembler.assemble(request)

    def reason(self, request: ReasoningRequest) -> ReasoningResult:
        """Run the full reasoning pipeline for the given request."""
        # Imported lazily to avoid an application.commands ↔ services cycle.
        from memovi_intelligence.application.commands.reason import Reason

        return Reason(
            knowledge_retriever=self._knowledge_retriever,
            context_assembler=self._context_assembler,
            reasoning_provider=self._reasoning_provider,
            prompt_builder=self._prompt_builder,
        ).execute(request)
