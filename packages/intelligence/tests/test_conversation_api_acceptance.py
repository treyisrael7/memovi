"""Acceptance scenarios for the Conversation API."""
from __future__ import annotations
from memovi_shared import WorkspaceId
from fastapi import FastAPI
from fastapi.testclient import TestClient
from memovi_intelligence.api.dependencies import get_conversation_repository, get_intelligence_config, get_knowledge_retriever, get_model_gateway
from memovi_intelligence.api.router import router
from memovi_intelligence.application.commands import Reason, SendConversationMessage, SendConversationMessageCommand
from memovi_intelligence.application.services import ContextAssembler, ConversationService, ModelGateway, PromptBuilder
from memovi_intelligence.config import IntelligenceConfig
from memovi_intelligence.domain.value_objects import ConversationId, ConversationRole, RetrievedKnowledge
from memovi_intelligence.infrastructure import FakeKnowledgeRetriever, FakeReasoningProvider, InMemoryConversationRepository
KNOWLEDGE = (RetrievedKnowledge(chunk_id='chunk-memovi', document_id='doc-memovi', text='Memovi is a self-hosted knowledge platform.', score=0.95, document_title='Memovi'), RetrievedKnowledge(chunk_id='chunk-builder', document_id='doc-origin', text='Memovi is built by its project maintainers as an open platform.', score=0.9, document_title='Origin'))

def _build() -> tuple[TestClient, InMemoryConversationRepository, SendConversationMessage]:
    repository = InMemoryConversationRepository()
    config = IntelligenceConfig(provider='fake')
    retriever = FakeKnowledgeRetriever(items=KNOWLEDGE)
    gateway = ModelGateway(providers={'fake': FakeReasoningProvider()}, config=config)
    conversations = ConversationService(repository=repository)
    reason = Reason(knowledge_retriever=retriever, context_assembler=ContextAssembler(knowledge_retriever=retriever, config=config), model_gateway=gateway, prompt_builder=PromptBuilder())
    send = SendConversationMessage(conversations=conversations, reason=reason)
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_conversation_repository] = lambda: repository
    app.dependency_overrides[get_intelligence_config] = lambda: config
    app.dependency_overrides[get_knowledge_retriever] = lambda: retriever
    app.dependency_overrides[get_model_gateway] = lambda: gateway
    return (TestClient(app, base_url='https://testserver'), repository, send)

def test_1_create_conversation() -> None:
    client, _, _ = _build()
    with client:
        response = client.post('/conversations')
    assert response.status_code == 201
    payload = response.json()
    assert set(payload.keys()) == {'conversation_id', 'created_at'}
    assert payload['conversation_id']
    assert payload['created_at']

def test_2_first_message() -> None:
    client, repository, _ = _build()
    with client:
        conversation_id = client.post('/conversations').json()['conversation_id']
        response = client.post(f'/conversations/{conversation_id}/messages', json={'message': 'What is Memovi?'})
    assert response.status_code == 200
    payload = response.json()
    assert payload['conversation_id'] == conversation_id
    assert 'Memovi is a self-hosted knowledge platform.' in payload['assistant_message']
    assert payload['citations']
    assert payload['citations'][0]['document_id'] == 'doc-memovi'
    assert [stage['stage'] for stage in payload['execution']['stages']] == ['retrieval', 'context_assembly', 'prompt_build', 'provider_resolution', 'model_execution']
    assert 'metrics' in payload['execution']
    stored = repository.get(ConversationId(conversation_id), workspace_id=WorkspaceId.default())
    assert stored is not None
    assert stored.turns[0].role is ConversationRole.USER
    assert stored.turns[0].content == "What is Memovi?"
    assert stored.turns[1].role is ConversationRole.ASSISTANT

def test_3_follow_up() -> None:
    client, repository, send = _build()
    with client:
        conversation_id = client.post('/conversations').json()['conversation_id']
        first = client.post(f'/conversations/{conversation_id}/messages', json={'message': 'What is Memovi?'})
        assert first.status_code == 200
        first_answer = first.json()['assistant_message']
        follow_up = send.execute(SendConversationMessageCommand(conversation_id=conversation_id, message='Who built it?', workspace_id=WorkspaceId.default()))
        history = client.get(f'/conversations/{conversation_id}/messages')
    context = follow_up.reasoning_result.context
    history_contents = [turn.content for turn in context.conversation_history.turns]
    stored = repository.get(ConversationId(conversation_id), workspace_id=WorkspaceId.default())
    assert stored is not None
    assert len(stored.turns) == 4
    assert stored.turns[2].content == "Who built it?"
    assert history.status_code == 200
    assert len(history.json()['messages']) == 4
    assert history_contents == ['What is Memovi?', first_answer]
    prompt = PromptBuilder().build(context)
    history_section = prompt.section('conversation_history').content
    assert 'What is Memovi?' in history_section
    assert first_answer in history_section
    assert 'Who built it?' not in history_contents
    assert 'Who built it?' not in history_section
    assert context.query == 'Who built it?'
    assert prompt.section('user_request').content == 'Who built it?'

def test_4_retrieve_history() -> None:
    client, _, _ = _build()
    with client:
        conversation_id = client.post('/conversations').json()['conversation_id']
        client.post(f'/conversations/{conversation_id}/messages', json={'message': 'What is Memovi?'})
        client.post(f'/conversations/{conversation_id}/messages', json={'message': 'Who built it?'})
        response = client.get(f'/conversations/{conversation_id}/messages')
    assert response.status_code == 200
    payload = response.json()
    assert payload['conversation_id'] == conversation_id
    messages = payload['messages']
    assert len(messages) == 4
    assert messages[0]['role'] == 'user'
    assert messages[0]['content'] == 'What is Memovi?'
    assert messages[0]['timestamp']
    assert messages[0]['citations'] == []
    assert messages[1]['role'] == 'assistant'
    assert messages[1]['timestamp']
    assert messages[1]['citations']
    assert messages[1]['citations'][0]['chunk_id'] == 'chunk-memovi'
    assert messages[2]['role'] == 'user'
    assert messages[2]['content'] == 'Who built it?'
    assert messages[2]['timestamp']
    assert messages[3]['role'] == 'assistant'
    assert messages[3]['timestamp']
    assert messages[3]['citations']
