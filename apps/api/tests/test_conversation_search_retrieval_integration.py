import time
from collections.abc import Iterator

import pytest
from api.app import create_app
from api.document_processing import configure_document_processing
from api.documents_session import build_documents_database_session
from api.intelligence_integration import get_search_knowledge_retriever
from auth.api.dependencies import get_database_session as get_auth_database_session
from auth.infrastructure.persistence import Base as AuthBase
from documents.api.dependencies import (
    get_database_session as get_documents_database_session,
)
from documents.api.dependencies import (
    get_object_storage,
)
from documents.application.workers import DocumentProcessingWorkerConfig
from documents.domain.enums import ProcessingStatus
from documents.infrastructure.persistence import Base as DocumentsBase
from documents.infrastructure.persistence.models import ProcessingJobRecord
from documents.infrastructure.queue import InMemoryProcessingJobQueue
from fastapi.testclient import TestClient
from memovi_intelligence.api.dependencies import (
    get_database_session as get_intelligence_database_session,
    get_knowledge_retriever,
)
from memovi_intelligence.infrastructure import FakeKnowledgeRetriever
from memovi_intelligence.infrastructure.persistence import Base as IntelligenceBase
from memovi_memory.infrastructure.persistence.models import Base as MemoryBase
from memovi_search.api.dependencies import get_database_session as get_search_database_session
from memovi_search.infrastructure.persistence.models import Base as SearchBase
from memovi_search.infrastructure.persistence.models import (
    SearchDocumentRecord,
    SearchEmbeddingRecord,
)
from postgres_support import ensure_pgvector_extension, postgres_available, postgres_database_url
from sqlalchemy import Engine, create_engine, select
from sqlalchemy.orm import Session, sessionmaker

UNIQUE_KNOWLEDGE = (
    "The Aurora lattice protocol 7X9Q stores durable knowledge shards "
    "for orbital research crews."
)


class InMemoryObjectStorage:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    def put_object(self, *, key: str, content: bytes, content_type: str) -> None:
        self.objects[key] = (content, content_type)

    def get_object(self, key: str) -> bytes:
        return self.objects[key][0]


def _wait_for_job_status(
    engine: Engine,
    processing_job_id: str,
    expected_status: ProcessingStatus,
    *,
    timeout_seconds: float = 5.0,
) -> ProcessingJobRecord:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        with Session(engine) as session:
            job = session.get(ProcessingJobRecord, processing_job_id)
            if job is not None and job.status == expected_status.value:
                return job
        time.sleep(0.05)

    with Session(engine) as session:
        job = session.get(ProcessingJobRecord, processing_job_id)
        current_status = job.status if job is not None else "missing"

    pytest.fail(
        f"Processing job {processing_job_id} did not reach "
        f"{expected_status.value} within {timeout_seconds}s (last status: {current_status}).",
    )


def _wait_for_search_index(
    engine: Engine,
    *,
    minimum_documents: int = 1,
    minimum_embeddings: int = 1,
    timeout_seconds: float = 5.0,
) -> list[SearchDocumentRecord]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        with Session(engine) as session:
            documents = list(session.scalars(select(SearchDocumentRecord)).all())
            embeddings = list(session.scalars(select(SearchEmbeddingRecord)).all())
            if len(documents) >= minimum_documents and len(embeddings) >= minimum_embeddings:
                return documents
        time.sleep(0.05)

    with Session(engine) as session:
        document_count = len(list(session.scalars(select(SearchDocumentRecord)).all()))
        embedding_count = len(list(session.scalars(select(SearchEmbeddingRecord)).all()))

    pytest.fail(
        f"Expected at least {minimum_documents} search documents and "
        f"{minimum_embeddings} embeddings within {timeout_seconds}s "
        f"(found {document_count} documents, {embedding_count} embeddings).",
    )


@pytest.fixture
def conversation_retrieval_client() -> Iterator[tuple[TestClient, Engine]]:
    if not postgres_available():
        pytest.skip("PostgreSQL is required for conversation retrieval integration tests.")

    object_storage = InMemoryObjectStorage()
    engine = create_engine(postgres_database_url(), pool_pre_ping=True)
    ensure_pgvector_extension(engine)
    for base in (AuthBase, DocumentsBase, MemoryBase, SearchBase, IntelligenceBase):
        base.metadata.drop_all(engine)
    for base in (AuthBase, DocumentsBase, MemoryBase, SearchBase, IntelligenceBase):
        base.metadata.create_all(engine)
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

    app = create_app()
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
    app.dependency_overrides[get_auth_database_session] = database_session
    app.dependency_overrides[get_documents_database_session] = build_documents_database_session(
        database_session
    )
    app.dependency_overrides[get_search_database_session] = database_session
    app.dependency_overrides[get_intelligence_database_session] = database_session
    app.dependency_overrides[get_object_storage] = lambda: object_storage

    with TestClient(app, base_url="https://testserver") as client:
        yield client, engine

    engine.dispose()


def test_conversation_reasons_over_indexed_search_knowledge(
    conversation_retrieval_client: tuple[TestClient, Engine],
) -> None:
    client, engine = conversation_retrieval_client
    app = client.app

    assert app.dependency_overrides[get_knowledge_retriever] is get_search_knowledge_retriever
    assert not isinstance(
        getattr(app.state, "knowledge_retriever", None),
        FakeKnowledgeRetriever,
    )

    upload = client.post(
        "/documents",
        files={
            "file": (
                "aurora-lattice.md",
                f"# Aurora\n\n{UNIQUE_KNOWLEDGE}".encode(),
                "text/markdown",
            )
        },
    )
    assert upload.status_code == 202
    upload_payload = upload.json()
    document_id = str(upload_payload["document_id"])

    _wait_for_job_status(
        engine,
        upload_payload["processing_job_id"],
        ProcessingStatus.COMPLETED,
    )
    search_documents = _wait_for_search_index(engine)
    search_document_ids = {document.id for document in search_documents}
    assert all(document.document_id == document_id for document in search_documents)

    create_response = client.post("/conversations")
    assert create_response.status_code == 201
    conversation_id = create_response.json()["conversation_id"]

    message_response = client.post(
        f"/conversations/{conversation_id}/messages",
        json={"message": "What is the Aurora lattice protocol?"},
    )
    assert message_response.status_code == 200
    payload = message_response.json()

    assert UNIQUE_KNOWLEDGE in payload["assistant_message"]
    assert payload["execution"]["metrics"]["retrieved_knowledge_count"] >= 1
    assert payload["citations"]
    assert all(citation["document_id"] == document_id for citation in payload["citations"])
    assert all(citation["chunk_id"] in search_document_ids for citation in payload["citations"])
    assert all(
        citation["chunk_id"] != FakeKnowledgeRetriever.DEFAULT_KNOWLEDGE.chunk_id
        for citation in payload["citations"]
    )
    assert all(
        citation["document_id"] != FakeKnowledgeRetriever.DEFAULT_KNOWLEDGE.document_id
        for citation in payload["citations"]
    )
    assert FakeKnowledgeRetriever.DEFAULT_KNOWLEDGE.text not in payload["assistant_message"]
