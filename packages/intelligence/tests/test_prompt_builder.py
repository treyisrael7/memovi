import pytest
from memovi_intelligence.application.services import ContextAssembler, PromptBuilder
from memovi_intelligence.domain.entities import ReasoningContext, ReasoningRequest
from memovi_intelligence.domain.exceptions import InvalidPromptError
from memovi_intelligence.domain.value_objects import (
    Prompt,
    PromptMessage,
    PromptRole,
    PromptSection,
    RetrievedKnowledge,
)
from memovi_intelligence.infrastructure import FakeReasoningProvider


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


def _knowledge(
    *,
    chunk_id: str = "chunk-1",
    document_id: str = "doc-1",
    text: str = "Decision recorded in meeting notes.",
    score: float = 0.9,
    document_title: str | None = "Notes",
) -> RetrievedKnowledge:
    return RetrievedKnowledge(
        chunk_id=chunk_id,
        document_id=document_id,
        text=text,
        score=score,
        document_title=document_title,
    )


def _context_for(
    items: tuple[RetrievedKnowledge, ...],
    query: str = "What was decided?",
) -> ReasoningContext:
    retriever = StubKnowledgeRetriever(items)
    assembler = ContextAssembler(knowledge_retriever=retriever)
    return assembler.assemble(ReasoningRequest.create(query=query))


def test_prompt_builder_creates_ordered_sections() -> None:
    context = _context_for((_knowledge(),))
    prompt = PromptBuilder().build(context)

    assert [section.name for section in prompt.sections] == [
        "system_instructions",
        "user_request",
        "retrieved_knowledge",
        "citations",
        "metadata",
    ]
    assert [section.order for section in prompt.sections] == [0, 1, 2, 3, 4]


def test_prompt_builder_organizes_instructions_knowledge_and_citations() -> None:
    item = _knowledge()
    context = _context_for((item,), query="Summarize the decision.")
    prompt = PromptBuilder().build(context)

    assert prompt.section("user_request").content == "Summarize the decision."
    assert "Decision recorded in meeting notes." in prompt.section("retrieved_knowledge").content
    assert "chunk-1" in prompt.section("citations").content
    assert "doc-1" in prompt.section("citations").content
    assert f"request_id={context.request.id.value}" in prompt.section("metadata").content
    assert prompt.citations[0].chunk_id == "chunk-1"
    assert prompt.citations[0].document_id == "doc-1"
    assert prompt.context is context


def test_prompt_builder_messages_use_provider_agnostic_roles() -> None:
    prompt = PromptBuilder().build(_context_for((_knowledge(),)))

    assert len(prompt.messages) == 2
    assert prompt.messages[0].role is PromptRole.SYSTEM
    assert prompt.messages[1].role is PromptRole.USER
    assert "Memovi's reasoning assistant" in prompt.messages[0].content
    assert "## USER REQUEST" in prompt.messages[1].content
    assert "## RETRIEVED KNOWLEDGE" in prompt.messages[1].content
    assert "## CITATIONS" in prompt.messages[1].content
    assert "## METADATA" in prompt.messages[1].content


def test_prompt_builder_is_deterministic() -> None:
    context = _context_for((_knowledge(), _knowledge(chunk_id="chunk-2", text="Second note.")))
    builder = PromptBuilder()

    first = builder.build(context)
    second = builder.build(context)

    assert first.sections == second.sections
    assert first.messages == second.messages
    assert first.citations == second.citations


def test_prompt_builder_rejects_empty_context() -> None:
    request = ReasoningRequest.create(query="Empty")
    context = ContextAssembler(
        knowledge_retriever=StubKnowledgeRetriever(),
    ).assemble(request)

    with pytest.raises(InvalidPromptError, match="empty reasoning context"):
        PromptBuilder().build(context)


def test_prompt_section_and_message_invariants() -> None:
    with pytest.raises(InvalidPromptError):
        PromptSection(name=" ", content="content", order=0)
    with pytest.raises(InvalidPromptError):
        PromptMessage(role=PromptRole.USER, content="  ")


def test_fake_provider_consumes_prompt() -> None:
    prompt = PromptBuilder().build(_context_for((_knowledge(),), query="What happened?"))
    result = FakeReasoningProvider().reason(prompt)

    assert result.provider == "fake"
    assert result.citations == prompt.citations
    assert result.context is prompt.context
    assert "What happened?" in result.answer
    assert "Decision recorded in meeting notes." in result.answer
    assert result.metadata["section_count"] == 5
    assert result.metadata["message_count"] == 2


def test_prompt_value_object_exposes_section_lookup() -> None:
    prompt = PromptBuilder().build(_context_for((_knowledge(),)))
    section = prompt.section("system_instructions")

    assert isinstance(prompt, Prompt)
    assert section.name == "system_instructions"


def test_what_is_memovi_prompt_and_fake_provider() -> None:
    knowledge = (
        RetrievedKnowledge(
            chunk_id="chunk-memovi",
            document_id="doc-memovi",
            text="Memovi is a self-hosted knowledge platform.",
            score=0.95,
            document_title="Memovi",
        ),
        RetrievedKnowledge(
            chunk_id="chunk-knowledge",
            document_id="doc-principles",
            text="Knowledge is the product.",
            score=0.90,
            document_title="Principles",
        ),
        RetrievedKnowledge(
            chunk_id="chunk-ai",
            document_id="doc-principles",
            text="AI is a consumer.",
            score=0.85,
            document_title="Principles",
        ),
    )
    # Deliberately unsorted input; assembly must rank by score before prompting.
    shuffled = (knowledge[2], knowledge[0], knowledge[1])
    request = ReasoningRequest.create(query="What is Memovi?")
    context = ContextAssembler(
        knowledge_retriever=StubKnowledgeRetriever(shuffled),
    ).assemble(request)

    prompt = PromptBuilder().build(context)

    assert prompt.section("system_instructions").content
    assert "Memovi's reasoning assistant" in prompt.section("system_instructions").content
    assert prompt.section("user_request").content == "What is Memovi?"
    assert [item.text for item in prompt.context.retrieved_knowledge] == [
        "Memovi is a self-hosted knowledge platform.",
        "Knowledge is the product.",
        "AI is a consumer.",
    ]
    knowledge_section = prompt.section("retrieved_knowledge").content
    memovi_pos = knowledge_section.index("Memovi is a self-hosted knowledge platform.")
    knowledge_pos = knowledge_section.index("Knowledge is the product.")
    ai_pos = knowledge_section.index("AI is a consumer.")
    assert memovi_pos < knowledge_pos < ai_pos

    assert len(prompt.citations) == 3
    assert prompt.citations[0].chunk_id == "chunk-memovi"
    assert prompt.citations[0].document_id == "doc-memovi"
    assert prompt.citations[0].score == 0.95
    assert "chunk-memovi" in prompt.section("citations").content
    assert "doc-memovi" in prompt.section("citations").content

    serialized = "\n".join(
        (
            *(section.content for section in prompt.sections),
            *(message.content for message in prompt.messages),
        )
    )
    assert "openai" not in serialized.lower()
    assert "anthropic" not in serialized.lower()
    assert "ollama" not in serialized.lower()
    assert "chat.completions" not in serialized.lower()
    assert all(message.role in {PromptRole.SYSTEM, PromptRole.USER} for message in prompt.messages)

    result = FakeReasoningProvider().reason(prompt)

    assert result.answer
    assert "What is Memovi?" in result.answer
    assert "Memovi is a self-hosted knowledge platform." in result.answer
    assert result.citations == prompt.citations
    assert result.context is prompt.context
    assert result.provider == "fake"
    assert result.execution_time == 0.0
    assert result.metadata["query"] == "What is Memovi?"
    assert result.metadata["chunk_count"] == 3
