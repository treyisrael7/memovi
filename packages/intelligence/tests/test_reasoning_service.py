import pytest
from memovi_intelligence.application import (
    ContextAssembler,
    PromptBuilder,
    Reason,
    ReasoningService,
)
from memovi_intelligence.application.commands import Reason as ReasonCommand
from memovi_intelligence.config import IntelligenceConfig
from memovi_intelligence.domain.entities import ReasoningContext, ReasoningRequest, ReasoningResult
from memovi_intelligence.domain.exceptions import NoRetrievedKnowledgeError
from memovi_intelligence.domain.value_objects import RetrievedKnowledge
from memovi_intelligence.infrastructure import (
    FakeReasoningProvider,
    PlaceholderKnowledgeRetriever,
    PlaceholderReasoningProvider,
)


class StubKnowledgeRetriever:
    def __init__(self, items: tuple[RetrievedKnowledge, ...] = ()) -> None:
        self._items = items

    def retrieve(
        self,
        request: ReasoningRequest,
        *,
        limit: int,
    ) -> tuple[RetrievedKnowledge, ...]:
        return self._items[:limit]


def test_reasoning_service_initializes_with_ports_and_default_config() -> None:
    service = ReasoningService(
        knowledge_retriever=PlaceholderKnowledgeRetriever(),
        reasoning_provider=PlaceholderReasoningProvider(),
    )

    assert service.config == IntelligenceConfig()


def test_reasoning_service_accepts_explicit_config() -> None:
    config = IntelligenceConfig(default_retrieval_limit=2, max_chunks=4)
    service = ReasoningService(
        knowledge_retriever=PlaceholderKnowledgeRetriever(),
        reasoning_provider=PlaceholderReasoningProvider(),
        config=config,
    )

    assert service.config is config


def test_reasoning_service_prepare_context_uses_assembler() -> None:
    item = RetrievedKnowledge(
        chunk_id="chunk-1",
        document_id="doc-1",
        text="Assembled via service.",
        score=0.7,
    )
    service = ReasoningService(
        knowledge_retriever=StubKnowledgeRetriever((item,)),
        reasoning_provider=PlaceholderReasoningProvider(),
    )
    request = ReasoningRequest.create(query="Prepare context for this question.")

    context = service.prepare_context(request)

    assert isinstance(context, ReasoningContext)
    assert context.retrieved_knowledge == (item,)
    assert context.request is request


def test_reasoning_service_reason_delegates_to_reason_command() -> None:
    item = RetrievedKnowledge(
        chunk_id="chunk-1",
        document_id="doc-1",
        text="Service delegates successfully.",
        score=0.8,
    )
    service = ReasoningService(
        knowledge_retriever=StubKnowledgeRetriever((item,)),
        reasoning_provider=FakeReasoningProvider(),
    )
    request = ReasoningRequest.create(query="Run full reasoning.")

    result = service.reason(request)

    assert isinstance(result, ReasoningResult)
    assert result.provider == "fake"
    assert "Service delegates successfully." in result.answer


def test_placeholder_adapters_raise_not_implemented() -> None:
    request = ReasoningRequest.create(query="Adapter placeholder behavior.")
    retriever = PlaceholderKnowledgeRetriever()
    provider = PlaceholderReasoningProvider()
    item = RetrievedKnowledge(
        chunk_id="chunk-1",
        document_id="doc-1",
        text="Enough knowledge to build a prompt.",
        score=0.5,
    )
    prompt = PromptBuilder().build(
        ContextAssembler(knowledge_retriever=StubKnowledgeRetriever((item,))).assemble(request),
    )

    with pytest.raises(NotImplementedError, match="Search"):
        retriever.retrieve(request, limit=3)

    with pytest.raises(NotImplementedError, match="provider"):
        provider.reason(prompt)


def test_context_assembler_prompt_builder_and_reason_are_exported() -> None:
    assert ContextAssembler is not None
    assert PromptBuilder is not None
    assert Reason is ReasonCommand


def test_integration_request_retrieve_context_prompt_reason_result() -> None:
    items = (
        RetrievedKnowledge(
            chunk_id="chunk-a",
            document_id="doc-a",
            text="Alpha decision from notes.",
            score=0.95,
            document_title="Alpha",
        ),
        RetrievedKnowledge(
            chunk_id="chunk-b",
            document_id="doc-b",
            text="Beta follow-up detail.",
            score=0.80,
            document_title="Beta",
        ),
    )
    retriever = StubKnowledgeRetriever(items)
    assembler = ContextAssembler(knowledge_retriever=retriever)
    builder = PromptBuilder()
    command = Reason(
        knowledge_retriever=retriever,
        context_assembler=assembler,
        reasoning_provider=FakeReasoningProvider(),
        prompt_builder=builder,
    )
    request = ReasoningRequest.create(query="Summarize the decisions.", limit=2)

    context = assembler.assemble(request)
    prompt = builder.build(context)
    result = command.execute(request)

    assert len(context.retrieved_knowledge) == 2
    assert [section.name for section in prompt.sections] == [
        "system_instructions",
        "user_request",
        "retrieved_knowledge",
        "citations",
        "metadata",
    ]
    assert prompt.messages[0].role.value == "system"
    assert prompt.messages[1].role.value == "user"
    assert isinstance(result, ReasoningResult)
    assert result.context.request is request
    assert len(result.citations) == 2
    assert result.citations[0].document_id == "doc-a"
    assert result.metadata["document_count"] == 2
    assert result.metadata["section_count"] == 5
    assert "Summarize the decisions." in result.answer
    assert "Alpha decision from notes." in result.answer
    assert "Beta follow-up detail." in result.answer


def test_integration_empty_retrieval_stops_before_provider() -> None:
    retriever = StubKnowledgeRetriever(())
    assembler = ContextAssembler(knowledge_retriever=retriever)
    command = Reason(
        knowledge_retriever=retriever,
        context_assembler=assembler,
        reasoning_provider=FakeReasoningProvider(),
    )

    with pytest.raises(NoRetrievedKnowledgeError):
        command.execute(ReasoningRequest.create(query="Nothing here."))
