from memovi_intelligence.application.ports import KnowledgeRetriever, ReasoningProvider
from memovi_intelligence.application.services.context_assembler import ContextAssembler
from memovi_intelligence.application.services.prompt_builder import PromptBuilder
from memovi_intelligence.domain.entities import ReasoningRequest, ReasoningResult
from memovi_intelligence.domain.exceptions import (
    IntelligenceDomainError,
    InvalidPromptError,
    InvalidReasoningContextError,
    NoRetrievedKnowledgeError,
    ReasoningProviderError,
)


class Reason:
    """Orchestrates retrieval, context assembly, prompt construction, and reasoning.

    Contains orchestration only: retrieve knowledge, assemble context, build a
    prompt, execute reasoning, and return an immutable ReasoningResult.
    """

    def __init__(
        self,
        *,
        knowledge_retriever: KnowledgeRetriever,
        context_assembler: ContextAssembler,
        reasoning_provider: ReasoningProvider,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        self._knowledge_retriever = knowledge_retriever
        self._context_assembler = context_assembler
        self._reasoning_provider = reasoning_provider
        self._prompt_builder = prompt_builder or PromptBuilder()

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
            prompt = self._prompt_builder.build(context)
        except InvalidPromptError:
            raise
        except IntelligenceDomainError:
            raise
        except Exception as exc:
            raise InvalidPromptError("Failed to build a valid reasoning prompt.") from exc

        try:
            return self._reasoning_provider.reason(prompt)
        except IntelligenceDomainError:
            raise
        except Exception as exc:
            raise ReasoningProviderError(
                "Reasoning provider failed while producing a result.",
            ) from exc
