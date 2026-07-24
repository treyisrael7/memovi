import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from api.app import create_app
from api.document_processing import configure_document_processing
from api.documents_session import build_documents_database_session
from api.events import InProcessEventDispatcher
from auth.api.dependencies import get_database_session as get_auth_database_session
from auth.infrastructure.persistence import Base as AuthBase
from documents.api.dependencies import get_database_session as get_documents_database_session
from documents.api.dependencies import get_object_storage
from documents.application.workers import DocumentProcessingWorkerConfig
from documents.infrastructure.persistence import Base as DocumentsBase
from documents.infrastructure.queue import InMemoryProcessingJobQueue
from fastapi.testclient import TestClient
from memovi_memory.domain.events import KnowledgeMaterialized
from memovi_memory.infrastructure.persistence.models import Base as MemoryBase
from memovi_memory.infrastructure.persistence.models import ChunkRecord, KnowledgeItemRecord
from memovi_search.domain.events import EmbeddingGenerated, SearchIndexed
from memovi_search.infrastructure.persistence.models import Base as SearchBase
from memovi_search.infrastructure.persistence.models import (
    SearchDocumentRecord,
    SearchEmbeddingRecord,
)
from memovi_search.infrastructure.providers import FakeEmbeddingProvider
from memovi_shared import WorkspaceId
from sqlalchemy import Engine, create_engine, select
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
def embedding_integration_client() -> Iterator[tuple[TestClient, Engine, InProcessEventDispatcher]]:
    object_storage = InMemoryObjectStorage()
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    AuthBase.metadata.create_all(engine)
    DocumentsBase.metadata.create_all(engine)
    MemoryBase.metadata.create_all(engine)
    SearchBase.metadata.create_all(engine)
    test_session_factory = sessionmaker(bind=engine, expire_on_commit=False)

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

    def worker_session_factory() -> Session:
        return test_session_factory()

    app = create_app()
    queue = InMemoryProcessingJobQueue()
    configure_document_processing(
        app,
        session_factory=worker_session_factory,
        queue=queue,
        worker_config=DocumentProcessingWorkerConfig(max_retries=3, poll_interval_seconds=0.05),
        object_storage=object_storage,
    )
    dispatcher: InProcessEventDispatcher = app.state.event_dispatcher
    app.dependency_overrides[get_auth_database_session] = database_session
    app.dependency_overrides[get_documents_database_session] = build_documents_database_session(
        database_session
    )
    app.dependency_overrides[get_object_storage] = lambda: object_storage
    with TestClient(app, base_url="https://testserver") as client:
        yield (client, engine, dispatcher)
    engine.dispose()


def test_search_indexed_generates_persists_and_publishes_embedding(
    embedding_integration_client: tuple[TestClient, Engine, InProcessEventDispatcher],
) -> None:
    _, engine, dispatcher = embedding_integration_client
    knowledge_item_id = str(uuid.uuid4())
    document_id = str(uuid.uuid4())
    document_version_id = str(uuid.uuid4())
    timestamp = datetime(2026, 7, 10, 16, 0, tzinfo=UTC)
    provider = FakeEmbeddingProvider()
    with Session(engine) as session:
        workspace_id = WorkspaceId.default().value
        session.add(
            KnowledgeItemRecord(
                id=knowledge_item_id,
                workspace_id=workspace_id,
                document_id=document_id,
                document_version_id=document_version_id,
                source_type="upload",
                mime_type="text/markdown",
                created_at=timestamp,
                updated_at=timestamp,
            )
        )
        session.add(
            ChunkRecord(
                id=str(uuid.uuid4()),
                workspace_id=workspace_id,
                knowledge_item_id=knowledge_item_id,
                document_id=document_id,
                document_version_id=document_version_id,
                chunk_index=0,
                text="Alpha passage.",
                created_at=timestamp,
            )
        )
        session.commit()
    dispatcher.publish(
        KnowledgeMaterialized(
            knowledge_item_id=knowledge_item_id,
            document_id=document_id,
            document_version_id=document_version_id,
            chunk_count=1,
            occurred_at=timestamp,
            workspace_id=WorkspaceId.default(),
        )
    )
    with Session(engine) as session:
        search_documents = session.scalars(select(SearchDocumentRecord)).all()
        embeddings = session.scalars(select(SearchEmbeddingRecord)).all()
        assert len(search_documents) == 1
        assert len(embeddings) == 1
        embedding = embeddings[0]
        assert embedding.search_document_id == search_documents[0].id
        assert embedding.provider == provider.provider
        assert embedding.model == provider.model
        assert embedding.dimensions == len(embedding.vector)
        assert embedding.vector == provider.embed(search_documents[0].searchable_text).values
    indexed_events = [
        event for event in dispatcher.published_events if isinstance(event, SearchIndexed)
    ]
    generated_events = [
        event for event in dispatcher.published_events if isinstance(event, EmbeddingGenerated)
    ]
    assert len(indexed_events) == 1
    assert len(generated_events) == 1
    generated = generated_events[0]
    assert generated.search_document_id == indexed_events[0].search_document_id
    assert generated.provider == provider.provider
    assert generated.model == provider.model
    assert generated.dimensions == len(embedding.vector)
    assert generated.embedding_id == embedding.id
