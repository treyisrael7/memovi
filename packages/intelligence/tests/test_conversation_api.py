from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from memovi_intelligence.api.dependencies import (
    get_conversation_repository,
    get_intelligence_config,
    get_knowledge_retriever,
    get_model_gateway,
)
from memovi_intelligence.api.router import router
from memovi_intelligence.application.services import ModelGateway
from memovi_intelligence.config import IntelligenceConfig
from memovi_intelligence.infrastructure import (
    FakeKnowledgeRetriever,
    FakeReasoningProvider,
    InMemoryConversationRepository,
)


@pytest.fixture
def conversation_client() -> Iterator[TestClient]:
    repository = InMemoryConversationRepository()
    config = IntelligenceConfig(provider="fake")
    retriever = FakeKnowledgeRetriever()
    gateway = ModelGateway(
        providers={"fake": FakeReasoningProvider()},
        config=config,
    )

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_conversation_repository] = lambda: repository
    app.dependency_overrides[get_intelligence_config] = lambda: config
    app.dependency_overrides[get_knowledge_retriever] = lambda: retriever
    app.dependency_overrides[get_model_gateway] = lambda: gateway

    client = TestClient(app, base_url="https://testserver")
    try:
        yield client
    finally:
        client.close()


def test_create_conversation(conversation_client: TestClient) -> None:
    response = conversation_client.post("/conversations")

    assert response.status_code == 201
    payload = response.json()
    assert "conversation_id" in payload
    assert payload["title"] == "New conversation"
    assert "created_at" in payload


def test_list_rename_and_delete_conversation(conversation_client: TestClient) -> None:
    created = conversation_client.post("/conversations").json()
    conversation_id = created["conversation_id"]

    listed = conversation_client.get("/conversations")
    assert listed.status_code == 200
    assert listed.json()["conversations"][0]["conversation_id"] == conversation_id

    renamed = conversation_client.patch(
        f"/conversations/{conversation_id}",
        json={"title": "Project notes"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "Project notes"

    deleted = conversation_client.delete(f"/conversations/{conversation_id}")
    assert deleted.status_code == 204
    assert conversation_client.get("/conversations").json()["conversations"] == []


def test_stream_message_emits_tokens_and_done(conversation_client: TestClient) -> None:
    conversation_id = conversation_client.post("/conversations").json()["conversation_id"]

    with conversation_client.stream(
        "POST",
        f"/conversations/{conversation_id}/messages/stream",
        json={"message": "What is Memovi?"},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    assert "event: token" in body
    assert "event: done" in body
    assert "Memovi is a self-hosted knowledge platform." in body


def test_list_models(conversation_client: TestClient) -> None:
    response = conversation_client.get("/conversations/models")
    assert response.status_code == 200
    payload = response.json()
    assert payload["default_provider"] == "fake"
    assert payload["default_model"] == "fake-reasoning-v1"
    assert payload["models"][0]["provider"] == "fake"


def test_send_first_message(conversation_client: TestClient) -> None:
    create_response = conversation_client.post("/conversations")
    conversation_id = create_response.json()["conversation_id"]

    response = conversation_client.post(
        f"/conversations/{conversation_id}/messages",
        json={"message": "What is Memovi?"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["conversation_id"] == conversation_id
    assert "Memovi is a self-hosted knowledge platform." in payload["assistant_message"]
    assert payload["provider"] == "fake"
    assert payload["model"] == "fake-reasoning-v1"
    assert payload["citations"][0]["document_id"] == "doc-memovi"
    assert payload["execution"]["metrics"]["retrieved_knowledge_count"] >= 1
    assert [stage["stage"] for stage in payload["execution"]["stages"]] == [
        "retrieval",
        "context_assembly",
        "prompt_build",
        "provider_resolution",
        "model_execution",
    ]


def test_send_follow_up_message(conversation_client: TestClient) -> None:
    create_response = conversation_client.post("/conversations")
    conversation_id = create_response.json()["conversation_id"]

    first = conversation_client.post(
        f"/conversations/{conversation_id}/messages",
        json={"message": "Introduce yourself briefly."},
    )
    assert first.status_code == 200

    follow_up = conversation_client.post(
        f"/conversations/{conversation_id}/messages",
        json={"message": "What is Memovi?"},
    )
    assert follow_up.status_code == 200
    assert "Memovi is a self-hosted knowledge platform." in follow_up.json()["assistant_message"]


def test_retrieve_history(conversation_client: TestClient) -> None:
    create_response = conversation_client.post("/conversations")
    conversation_id = create_response.json()["conversation_id"]

    conversation_client.post(
        f"/conversations/{conversation_id}/messages",
        json={"message": "What is Memovi?"},
    )

    response = conversation_client.get(f"/conversations/{conversation_id}/messages")

    assert response.status_code == 200
    payload = response.json()
    assert payload["conversation_id"] == conversation_id
    assert len(payload["messages"]) == 2
    assert payload["messages"][0]["role"] == "user"
    assert payload["messages"][0]["content"] == "What is Memovi?"
    assert payload["messages"][1]["role"] == "assistant"
    assert payload["messages"][1]["citations"][0]["chunk_id"] == "chunk-memovi"


def test_get_conversation_metadata(conversation_client: TestClient) -> None:
    create_response = conversation_client.post("/conversations")
    conversation_id = create_response.json()["conversation_id"]

    conversation_client.post(
        f"/conversations/{conversation_id}/messages",
        json={"message": "What is Memovi?"},
    )

    response = conversation_client.get(f"/conversations/{conversation_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["conversation_id"] == conversation_id
    assert payload["title"] == "What is Memovi?"
    assert payload["message_count"] == 2
    assert "created_at" in payload
    assert "updated_at" in payload


def test_unknown_conversation_returns_404(conversation_client: TestClient) -> None:
    unknown_id = "11111111-1111-1111-1111-111111111111"

    get_response = conversation_client.get(f"/conversations/{unknown_id}")
    assert get_response.status_code == 404

    messages_response = conversation_client.get(f"/conversations/{unknown_id}/messages")
    assert messages_response.status_code == 404

    send_response = conversation_client.post(
        f"/conversations/{unknown_id}/messages",
        json={"message": "What is Memovi?"},
    )
    assert send_response.status_code == 404


def test_invalid_conversation_id_returns_422(conversation_client: TestClient) -> None:
    response = conversation_client.get("/conversations/not-a-uuid")
    assert response.status_code == 422


def test_empty_message_returns_422(conversation_client: TestClient) -> None:
    create_response = conversation_client.post("/conversations")
    conversation_id = create_response.json()["conversation_id"]

    empty_response = conversation_client.post(
        f"/conversations/{conversation_id}/messages",
        json={"message": ""},
    )
    assert empty_response.status_code == 422

    blank_response = conversation_client.post(
        f"/conversations/{conversation_id}/messages",
        json={"message": "   "},
    )
    assert blank_response.status_code == 422
