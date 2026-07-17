from datetime import UTC, datetime, timedelta

from memovi_intelligence.application.services import ContextAssembler, PromptBuilder
from memovi_intelligence.config import IntelligenceConfig
from memovi_intelligence.domain.entities import ReasoningRequest
from memovi_intelligence.domain.services import estimate_token_count
from memovi_intelligence.domain.value_objects import (
    ConversationHistory,
    ConversationRole,
    ConversationTurn,
    RetrievedKnowledge,
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


def _knowledge(
    *,
    chunk_id: str = "chunk-1",
    document_id: str = "doc-1",
    text: str = "Memovi is a self-hosted knowledge platform.",
    score: float = 0.9,
) -> RetrievedKnowledge:
    return RetrievedKnowledge(
        chunk_id=chunk_id,
        document_id=document_id,
        text=text,
        score=score,
        document_title="Memovi",
    )


def _history(*contents: str) -> ConversationHistory:
    turns = tuple(
        ConversationTurn(
            role=ConversationRole.USER if index % 2 == 0 else ConversationRole.ASSISTANT,
            content=content,
            timestamp=datetime(2026, 7, 17, 12, 0, tzinfo=UTC) + timedelta(seconds=index),
        )
        for index, content in enumerate(contents)
    )
    return ConversationHistory(turns=turns)


def test_context_assembler_without_history_leaves_conversation_empty() -> None:
    assembler = ContextAssembler(
        knowledge_retriever=StubKnowledgeRetriever((_knowledge(),)),
    )
    context = assembler.assemble(ReasoningRequest.create(query="What is Memovi?"))

    assert context.conversation_history.is_empty
    assert context.estimated_token_count == estimate_token_count(
        "Memovi is a self-hosted knowledge platform.",
    )


def test_context_assembler_attaches_trimmed_conversation_history() -> None:
    history = _history("one", "two", "three", "four")
    assembler = ContextAssembler(
        knowledge_retriever=StubKnowledgeRetriever((_knowledge(),)),
        config=IntelligenceConfig(max_conversation_turns=2, max_conversation_tokens=10_000),
    )

    context = assembler.assemble_from(
        ReasoningRequest.create(query="Follow up?"),
        (_knowledge(),),
        conversation_history=history,
    )

    assert [turn.content for turn in context.conversation_history.turns] == ["three", "four"]
    assert context.estimated_token_count > estimate_token_count(
        "Memovi is a self-hosted knowledge platform.",
    )


def test_context_assembler_conversation_respects_remaining_token_budget() -> None:
    knowledge_text = "Knowledge " * 40
    knowledge = _knowledge(text=knowledge_text)
    knowledge_tokens = estimate_token_count(knowledge_text)
    history = _history("prior turn one " * 30, "prior turn two " * 30)

    assembler = ContextAssembler(
        knowledge_retriever=StubKnowledgeRetriever((knowledge,)),
        config=IntelligenceConfig(
            max_estimated_tokens=knowledge_tokens,
            max_conversation_turns=10,
            max_conversation_tokens=10_000,
        ),
    )

    context = assembler.assemble_from(
        ReasoningRequest.create(query="Budget check"),
        (knowledge,),
        conversation_history=history,
    )

    assert context.conversation_history.is_empty
    assert context.estimated_token_count == knowledge_tokens


def test_prompt_builder_adds_separate_conversation_history_section() -> None:
    history = _history("Earlier question about Memovi", "Earlier answer about Memovi")
    assembler = ContextAssembler(
        knowledge_retriever=StubKnowledgeRetriever((_knowledge(),)),
    )
    context = assembler.assemble(
        ReasoningRequest.create(query="What is Memovi?"),
        conversation_history=history,
    )
    prompt = PromptBuilder().build(context)

    assert [section.name for section in prompt.sections] == [
        "system_instructions",
        "user_request",
        "conversation_history",
        "retrieved_knowledge",
        "citations",
        "metadata",
    ]
    history_section = prompt.section("conversation_history").content
    knowledge_section = prompt.section("retrieved_knowledge").content
    assert "Earlier question about Memovi" in history_section
    assert "Earlier answer about Memovi" in history_section
    assert "Memovi is a self-hosted knowledge platform." in knowledge_section
    assert "Earlier question about Memovi" not in knowledge_section
    assert "## CONVERSATION HISTORY" in prompt.messages[1].content
