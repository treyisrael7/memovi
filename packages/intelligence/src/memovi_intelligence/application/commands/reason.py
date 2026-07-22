from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from time import perf_counter

from memovi_intelligence.application.ports import KnowledgeRetriever
from memovi_intelligence.application.services.context_assembler import ContextAssembler
from memovi_intelligence.application.services.execution_tracer import ExecutionTracer
from memovi_intelligence.application.services.model_gateway import ModelGateway
from memovi_intelligence.application.services.prompt_builder import PromptBuilder
from memovi_intelligence.domain.entities import (
    ReasoningContext,
    ReasoningRequest,
    ReasoningResult,
)
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
    Prompt,
)


@dataclass(frozen=True, slots=True)
class ReasonStreamToken:
    content: str


@dataclass(frozen=True, slots=True)
class ReasonStreamCompleted:
    result: ReasoningResult


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
        provider: str | None = None,
        model: str | None = None,
    ) -> ReasoningResult:
        tracer = ExecutionTracer()
        prompt, context = self._prepare(request, conversation_history, tracer)

        with tracer.stage(ExecutionStage.PROVIDER_RESOLUTION):
            resolved_provider = self._model_gateway.resolve_provider(provider)

        with tracer.stage(ExecutionStage.MODEL_EXECUTION):
            result = self._model_gateway.execute(
                prompt,
                provider=resolved_provider,
                provider_name=provider,
                model=model,
            )

        return self._finalize(result, context, tracer, provider=provider, model=model)

    def execute_stream(
        self,
        request: ReasoningRequest,
        *,
        conversation_history: ConversationHistory | None = None,
        provider: str | None = None,
        model: str | None = None,
    ) -> Iterator[ReasonStreamToken | ReasonStreamCompleted]:
        tracer = ExecutionTracer()
        prompt, context = self._prepare(request, conversation_history, tracer)

        with tracer.stage(ExecutionStage.PROVIDER_RESOLUTION):
            resolved_provider = self._model_gateway.resolve_provider(provider)

        chunks: list[str] = []
        started = perf_counter()
        with tracer.stage(ExecutionStage.MODEL_EXECUTION):
            for delta in self._model_gateway.execute_stream(
                prompt,
                provider=resolved_provider,
                provider_name=provider,
                model=model,
            ):
                chunks.append(delta)
                yield ReasonStreamToken(content=delta)

        answer = "".join(chunks)
        duration = perf_counter() - started
        resolved_model = model or self._model_gateway.model
        resolved_provider_name = provider or self._model_gateway.provider_name
        streamed = ReasoningResult.create(
            answer=answer,
            citations=prompt.citations,
            metadata={
                "query": prompt.query,
                "chunk_count": len(prompt.citations),
                "document_count": len(prompt.context.assembled_documents),
                "estimated_token_count": prompt.context.estimated_token_count,
                "model": resolved_model,
                "streamed": True,
                "duration": duration,
            },
            provider=resolved_provider_name,
            execution_time=duration,
            context=prompt.context,
        )
        result = self._finalize(
            streamed,
            context,
            tracer,
            provider=provider,
            model=model,
        )
        yield ReasonStreamCompleted(result=result)

    def _prepare(
        self,
        request: ReasoningRequest,
        conversation_history: ConversationHistory | None,
        tracer: ExecutionTracer,
    ) -> tuple[Prompt, ReasoningContext]:
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

        return prompt, context

    def _finalize(
        self,
        result: ReasoningResult,
        context: ReasoningContext,
        tracer: ExecutionTracer,
        *,
        provider: str | None,
        model: str | None,
    ) -> ReasoningResult:
        resolved_provider = provider or self._model_gateway.provider_name
        resolved_model = model or self._model_gateway.model
        metrics = ExecutionMetrics(
            provider=resolved_provider,
            model=resolved_model,
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
            provider=resolved_provider,
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
