from memovi_intelligence.application.commands import Reason
from memovi_intelligence.application.services import (
    ContextAssembler,
    ConversationService,
    ModelGateway,
    PromptBuilder,
)
from memovi_intelligence.config import IntelligenceConfig
from memovi_intelligence.domain.entities import ReasoningRequest
from memovi_intelligence.domain.value_objects import ConversationRole, RetrievedKnowledge
from memovi_intelligence.infrastructure import FakeReasoningProvider, InMemoryConversationRepository
from memovi_shared import WorkspaceId


class StubKnowledgeRetriever:

    def __init__(self, items: tuple[RetrievedKnowledge, ...] = ()) -> None:
        self._items = items

    def retrieve(self, request: ReasoningRequest, *, limit: int) -> tuple[RetrievedKnowledge, ...]:
        return self._items[:limit]


def test_conversation_reason_updates_conversation_history() -> None:
    knowledge = (
        RetrievedKnowledge(
            chunk_id="chunk-memovi",
            document_id="doc-memovi",
            text="Memovi is a self-hosted knowledge platform.",
            score=0.95,
            document_title="Memovi",
        ),
    )
    retriever = StubKnowledgeRetriever(knowledge)
    config = IntelligenceConfig(provider="fake")
    conversations = ConversationService(repository=InMemoryConversationRepository())
    reason = Reason(
        knowledge_retriever=retriever,
        context_assembler=ContextAssembler(knowledge_retriever=retriever, config=config),
        model_gateway=ModelGateway(providers={"fake": FakeReasoningProvider()}, config=config),
        prompt_builder=PromptBuilder(),
    )
    conversation = conversations.create_conversation(workspace_id=WorkspaceId.default())
    conversations.append_user_turn(
        conversation.id, "Introduce yourself briefly.", workspace_id=WorkspaceId.default()
    )
    conversations.append_assistant_turn(
        conversation.id, "I am Memovi's reasoning assistant.", workspace_id=WorkspaceId.default()
    )
    prior_history = conversations.load_history(conversation.id, workspace_id=WorkspaceId.default())
    follow_up = "What is Memovi?"
    result = reason.execute(
        ReasoningRequest.create(query=follow_up), conversation_history=prior_history
    )
    conversations.append_user_turn(conversation.id, follow_up, workspace_id=WorkspaceId.default())
    updated = conversations.append_assistant_turn(
        conversation.id,
        result.answer,
        citations=result.citations,
        workspace_id=WorkspaceId.default(),
    )
    assert [turn.role for turn in updated.turns] == [
        ConversationRole.USER,
        ConversationRole.ASSISTANT,
        ConversationRole.USER,
        ConversationRole.ASSISTANT,
    ]
    assert updated.turns[2].content == follow_up
    assert updated.turns[3].content == result.answer
    assert updated.turns[3].citations == result.citations
    assert "Memovi is a self-hosted knowledge platform." in result.answer
    assert [turn.content for turn in result.context.conversation_history.turns] == [
        "Introduce yourself briefly.",
        "I am Memovi's reasoning assistant.",
    ]
    prompt = PromptBuilder().build(result.context)
    assert "conversation_history" in {section.name for section in prompt.sections}
    assert "Introduce yourself briefly." in prompt.section("conversation_history").content
    assert (
        "Memovi is a self-hosted knowledge platform."
        in prompt.section("retrieved_knowledge").content
    )
