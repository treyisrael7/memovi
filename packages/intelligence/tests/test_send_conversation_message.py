from memovi_shared import WorkspaceId
from memovi_intelligence.application.commands import Reason, SendConversationMessage, SendConversationMessageCommand
from memovi_intelligence.application.services import ContextAssembler, ConversationService, ModelGateway, PromptBuilder
from memovi_intelligence.config import IntelligenceConfig
from memovi_intelligence.domain.value_objects import ConversationRole
from memovi_intelligence.infrastructure import FakeKnowledgeRetriever, FakeReasoningProvider, InMemoryConversationRepository

def _build_send_message() -> tuple[SendConversationMessage, ConversationService, InMemoryConversationRepository]:
    repository = InMemoryConversationRepository()
    conversations = ConversationService(repository=repository)
    retriever = FakeKnowledgeRetriever()
    config = IntelligenceConfig(provider='fake')
    reason = Reason(knowledge_retriever=retriever, context_assembler=ContextAssembler(knowledge_retriever=retriever, config=config), model_gateway=ModelGateway(providers={'fake': FakeReasoningProvider()}, config=config), prompt_builder=PromptBuilder())
    return (SendConversationMessage(conversations=conversations, reason=reason), conversations, repository)

def test_send_conversation_message_updates_repository_and_history() -> None:
    send_message, conversations, repository = _build_send_message()
    conversation = conversations.create_conversation(workspace_id=WorkspaceId.default())
    first = send_message.execute(SendConversationMessageCommand(conversation_id=conversation.id.value, message='Introduce yourself briefly.', workspace_id=WorkspaceId.default()))
    assert first.provider == 'fake'
    assert first.model == 'fake-reasoning-v1'
    assert first.execution_trace.stages
    assert 'Memovi is a self-hosted knowledge platform.' in first.assistant_message
    stored = repository.get(conversation.id, workspace_id=WorkspaceId.default())
    assert stored is not None
    assert len(stored.turns) == 2
    assert stored.turns[0].role is ConversationRole.USER
    assert stored.turns[1].role is ConversationRole.ASSISTANT
    assert stored.turns[1].citations == first.citations
    second = send_message.execute(SendConversationMessageCommand(conversation_id=conversation.id.value, message='What is Memovi?', workspace_id=WorkspaceId.default()))
    assert 'Memovi is a self-hosted knowledge platform.' in second.assistant_message
    updated = repository.get(conversation.id, workspace_id=WorkspaceId.default())
    assert updated is not None
    assert len(updated.turns) == 4
    assert [turn.role for turn in updated.turns] == [ConversationRole.USER, ConversationRole.ASSISTANT, ConversationRole.USER, ConversationRole.ASSISTANT]
    assert updated.turns[2].content == 'What is Memovi?'
    assert updated.turns[3].content == second.assistant_message
    history = conversations.load_history(conversation.id, workspace_id=WorkspaceId.default())
    assert len(history.turns) == 4
    assert history.turns[0].content == 'Introduce yourself briefly.'
