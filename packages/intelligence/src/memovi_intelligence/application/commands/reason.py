from collections.abc import Mapping

from memovi_intelligence.application.ports import KnowledgeRetriever
from memovi_intelligence.application.services.context_assembler import ContextAssembler
from memovi_intelligence.application.services.execution_tracer import ExecutionTracer
from memovi_intelligence.application.services.model_gateway import ModelGateway
from memovi_intelligence.application.services.prompt_builder import PromptBuilder
from memovi_intelligence.domain.entities import ReasoningRequest, ReasoningResult
from memovi_intelligence.domain.exceptions import (
    IntelligenceDomainError,
    InvalidPromptError,
    InvalidReasoningContextError,
    NoRetrievedKnowledgeError,
)
from memovi_intelligence.domain.value_objects import (
    ConversationHistory,
    ExecutionMetrics,
    ExecutionStage,
)


class Reason:
    """Orchestrates retrieval, context assembly, prompt construction, and reasoning.

    Contains orchestration only: retrieve knowledge, assemble context, build a
    prompt, execute through ModelGateway, and return an immutable ReasoningResult
    with a structured execution_trace.
    """

    def __init__(
        self,
        *,
        knowledge_retriever: KnowledgeRetriever,
        context_assembler: ContextAssembler,
        model_gateway: ModelGateway,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        self._knowledge_retriever = knowledge_retriever
        self._context_assembler = context_assembler
        self._model_gateway = model_gateway
        self._prompt_builder = prompt_builder or PromptBuilder()

    def execute(
        self,
        request: ReasoningRequest,
        *,
        conversation_history: ConversationHistory | None = None,
    ) -> ReasoningResult:
        tracer = ExecutionTracer()
        limit = (
            request.limit
            if request.limit is not None
            else self._context_assembler.config.default_retrieval_limit
        )

        with tracer.stage(ExecutionStage.RETRIEVAL):
            retrieved = tuple(self._knowledge_retriever.retrieve(request, limit=limit))
        if not retrieved:
            raise NoRetrievedKnowledgeError(
                "No knowledge was retrieved for the reasoning request.",
            )

        with tracer.stage(ExecutionStage.CONTEXT_ASSEMBLY):
            try:
                context = self._context_assembler.assemble_from(
                    request,
                    retrieved,
                    conversation_history=conversation_history,
                )
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

        with tracer.stage(ExecutionStage.PROMPT_BUILD):
            try:
                prompt = self._prompt_builder.build(context)
            except InvalidPromptError:
                raise
            except IntelligenceDomainError:
                raise
            except Exception as exc:
                raise InvalidPromptError(
                    "Failed to build a valid reasoning prompt.",
                ) from exc

        with tracer.stage(ExecutionStage.PROVIDER_RESOLUTION):
            provider = self._model_gateway.resolve_provider()

        with tracer.stage(ExecutionStage.MODEL_EXECUTION):
            result = self._model_gateway.execute(prompt, provider=provider)

        metrics = ExecutionMetrics(
            provider=result.provider,
            model=self._model_gateway.model,
            estimated_input_tokens=context.estimated_token_count,
            output_tokens=_optional_output_tokens(result.metadata),
            retrieved_knowledge_count=len(context.retrieved_knowledge),
            document_count=len(context.assembled_documents),
            citation_count=len(result.citations),
        )
        execution_trace = tracer.build(metrics)

        return ReasoningResult.create(
            answer=result.answer,
            citations=result.citations,
            metadata=result.metadata,
            provider=result.provider,
            execution_time=execution_trace.total_duration,
            context=result.context,
            execution_trace=execution_trace,
            tool_calls=result.tool_calls,
            tool_results=result.tool_results,
        )


def _optional_output_tokens(metadata: Mapping[str, object]) -> int | None:
    raw = metadata.get("completion_tokens")
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw if raw >= 0 else None
    if isinstance(raw, float) and raw.is_integer():
        value = int(raw)
        return value if value >= 0 else None
    if isinstance(raw, str):
        try:
            value = int(raw)
        except ValueError:
            return None
        return value if value >= 0 else None
    return None
