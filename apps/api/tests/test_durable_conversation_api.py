import json
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from api.app import create_app
from api.database import database_session as api_database_session
from api.document_processing import configure_document_processing
from api.intelligence_integration import get_sqlalchemy_conversation_repository
from auth.api.dependencies import get_database_session as get_auth_database_session
from auth.infrastructure.persistence import Base as AuthBase
from documents.api.dependencies import get_object_storage
from documents.application.workers import DocumentProcessingWorkerConfig
from documents.infrastructure.queue import InMemoryProcessingJobQueue
from fastapi.testclient import TestClient
from memovi_intelligence.api.dependencies import (
    get_conversation_repository,
    get_knowledge_retriever,
)
from memovi_intelligence.api.dependencies import (
    get_database_session as get_intelligence_database_session,
)
from memovi_intelligence.domain.value_objects import ConversationId, ConversationRole
from memovi_intelligence.infrastructure import (
    FakeKnowledgeRetriever,
    InMemoryConversationRepository,
    SqlAlchemyConversationRepository,
)
from memovi_intelligence.infrastructure.persistence import Base as IntelligenceBase
from memovi_search.api.dependencies import get_database_session as get_search_database_session
from memovi_shared import DEFAULT_WORKSPACE_ID, WorkspaceId
from memovi_workspace.infrastructure.persistence import Base as WorkspaceBase
from memovi_workspace.infrastructure.persistence.models import WorkspaceRecord
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


class InMemoryObjectStorage:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    def put_object(self, *, key: str, content: bytes, content_type: str) -> None:
        self.objects[key] = (content, content_type)

    def get_object(self, key: str) -> bytes:
        return self.objects[key][0]


@pytest.fixture
def conversation_api_client() -> Iterator[tuple[TestClient, sessionmaker[Session], Engine]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    AuthBase.metadata.create_all(engine)
    WorkspaceBase.metadata.create_all(engine)
    IntelligenceBase.metadata.create_all(engine)
    test_session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    object_storage = InMemoryObjectStorage()

    with Session(engine) as seed_session:
        seed_session.add(
            WorkspaceRecord(
                id=DEFAULT_WORKSPACE_ID.value,
                name="Default",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )
        seed_session.commit()

    def database_session() -> Iterator[Session]:
        session = test_session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app = create_app()
    app.state.auth_session_factory = test_session_factory
    configure_document_processing(
        app,
        session_factory=test_session_factory,
        queue=InMemoryProcessingJobQueue(),
        worker_config=DocumentProcessingWorkerConfig(
            max_retries=3,
            poll_interval_seconds=0.05,
        ),
        object_storage=object_storage,
    )
    app.dependency_overrides[api_database_session] = database_session
    app.dependency_overrides[get_auth_database_session] = database_session
    app.dependency_overrides[get_search_database_session] = database_session
    app.dependency_overrides[get_intelligence_database_session] = database_session
    app.dependency_overrides[get_object_storage] = lambda: object_storage
    app.dependency_overrides[get_knowledge_retriever] = lambda: FakeKnowledgeRetriever()

    with TestClient(app, base_url="https://testserver") as client:
        register_response = client.post(
            "/auth/register",
            json={"email": "conversation-api@example.com", "password": "password123"},
        )
        assert register_response.status_code == 201
        yield client, test_session_factory, engine

    engine.dispose()


def test_conversation_api_create_get_messages_and_follow_up(
    conversation_api_client: tuple[TestClient, sessionmaker[Session], Engine],
) -> None:
    client, _, _ = conversation_api_client

    create_response = client.post("/conversations")
    assert create_response.status_code == 201
    conversation_id = create_response.json()["conversation_id"]
    assert "created_at" in create_response.json()

    metadata = client.get(f"/conversations/{conversation_id}")
    assert metadata.status_code == 200
    assert metadata.json()["conversation_id"] == conversation_id
    assert metadata.json()["message_count"] == 0

    first = client.post(
        f"/conversations/{conversation_id}/messages",
        json={"message": "What is Memovi?"},
    )
    assert first.status_code == 200
    first_payload = first.json()
    assert first_payload["conversation_id"] == conversation_id
    assert "Memovi is a self-hosted knowledge platform." in first_payload["assistant_message"]
    assert first_payload["citations"][0]["chunk_id"] == "chunk-memovi"

    messages = client.get(f"/conversations/{conversation_id}/messages")
    assert messages.status_code == 200
    history = messages.json()["messages"]
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "What is Memovi?"
    assert history[1]["role"] == "assistant"

    follow_up = client.post(
        f"/conversations/{conversation_id}/messages",
        json={"message": "Tell me more."},
    )
    assert follow_up.status_code == 200

    metadata_after = client.get(f"/conversations/{conversation_id}")
    assert metadata_after.json()["message_count"] == 4

    messages_after = client.get(f"/conversations/{conversation_id}/messages")
    contents = [message["content"] for message in messages_after.json()["messages"]]
    assert contents[0] == "What is Memovi?"
    assert contents[2] == "Tell me more."


def test_conversation_history_survives_new_repository_session(
    conversation_api_client: tuple[TestClient, sessionmaker[Session], Engine],
) -> None:
    client, session_factory, _ = conversation_api_client

    create_response = client.post("/conversations")
    conversation_id = create_response.json()["conversation_id"]

    client.post(
        f"/conversations/{conversation_id}/messages",
        json={"message": "Remember durable state."},
    )
    client.post(
        f"/conversations/{conversation_id}/messages",
        json={"message": "And another turn."},
    )

    with session_factory() as session:
        repository = SqlAlchemyConversationRepository(session)
        loaded = repository.get(
            ConversationId(conversation_id),
            workspace_id=WorkspaceId.default(),
        )
        assert loaded is not None
        assert len(loaded.turns) == 4
        assert loaded.turns[0].content == "Remember durable state."
        assert loaded.turns[2].content == "And another turn."

    continued = client.post(
        f"/conversations/{conversation_id}/messages",
        json={"message": "Continue after reload."},
    )
    assert continued.status_code == 200

    history = client.get(f"/conversations/{conversation_id}/messages").json()["messages"]
    assert len(history) == 6
    assert history[4]["content"] == "Continue after reload."
    assert history[5]["role"] == "assistant"


def test_conversation_sse_stream_persists_through_sqlalchemy(
    conversation_api_client: tuple[TestClient, sessionmaker[Session], Engine],
) -> None:
    client, session_factory, _engine = conversation_api_client
    created = client.post("/conversations")
    assert created.status_code == 201
    conversation_id = created.json()["conversation_id"]
    question = "What is Memovi?"

    with client.stream(
        "POST",
        f"/conversations/{conversation_id}/messages/stream",
        json={"message": question},
    ) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        body = "".join(response.iter_text())

    assert "event: token" in body
    assert "event: done" in body
    assert "event: error" not in body
    assert "Memovi is a self-hosted knowledge platform." in body

    done_payload: dict[str, object] | None = None
    for block in body.split("\n\n"):
        if "event: done" not in block:
            continue
        for line in block.split("\n"):
            if line.startswith("data:"):
                done_payload = json.loads(line[5:].strip())
    assert done_payload is not None
    assert done_payload["conversation_id"] == conversation_id
    assistant_message = str(done_payload["assistant_message"])
    assert "Memovi is a self-hosted knowledge platform." in assistant_message
    citations = done_payload["citations"]
    assert isinstance(citations, list)
    assert citations[0]["chunk_id"] == "chunk-memovi"
    assert citations[0]["document_id"] == "doc-memovi"

    listed = client.get(f"/conversations/{conversation_id}/messages")
    assert listed.status_code == 200
    messages = listed.json()["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == question
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == assistant_message
    assert messages[1]["citations"][0]["chunk_id"] == "chunk-memovi"

    with session_factory() as session:
        repository = SqlAlchemyConversationRepository(session)
        loaded = repository.get(
            ConversationId(conversation_id),
            workspace_id=WorkspaceId.default(),
        )
        assert loaded is not None
        assert loaded.workspace_id == WorkspaceId.default()
        assert len(loaded.turns) == 2
        assert loaded.turns[0].role is ConversationRole.USER
        assert loaded.turns[0].content == question
        assert loaded.turns[1].role is ConversationRole.ASSISTANT
        assert loaded.turns[1].content == assistant_message
        assert loaded.turns[1].citations[0].chunk_id == "chunk-memovi"


def test_composition_root_uses_sqlalchemy_conversation_repository() -> None:
    app = create_app()
    assert app.dependency_overrides[get_conversation_repository] is (
        get_sqlalchemy_conversation_repository
    )
    assert not isinstance(
        getattr(app.state, "conversation_repository", None),
        InMemoryConversationRepository,
    )
