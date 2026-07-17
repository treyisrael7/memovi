import time
from collections.abc import Iterator

import pytest
from api.app import create_app
from api.document_processing import configure_document_processing
from api.documents_session import build_documents_database_session
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


def _wait_for_embeddings(
    engine: Engine,
    *,
    minimum_count: int,
    timeout_seconds: float = 5.0,
) -> list[SearchEmbeddingRecord]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        with Session(engine) as session:
            embeddings = list(session.scalars(select(SearchEmbeddingRecord)).all())
            if len(embeddings) >= minimum_count:
                return embeddings
        time.sleep(0.05)

    with Session(engine) as session:
        count = len(list(session.scalars(select(SearchEmbeddingRecord)).all()))

    pytest.fail(
        f"Expected at least {minimum_count} embeddings within {timeout_seconds}s (found {count}).",
    )


def _upload_document(
    client: TestClient,
    *,
    filename: str,
    content: bytes,
) -> dict[str, str]:
    response = client.post(
        "/documents",
        files={"file": (filename, content, "text/markdown")},
    )
    assert response.status_code == 202
    payload = response.json()
    return {
        "document_id": str(payload["document_id"]),
        "processing_job_id": str(payload["processing_job_id"]),
    }


@pytest.fixture
def semantic_search_client() -> Iterator[tuple[TestClient, Engine]]:
    if not postgres_available():
        pytest.skip("PostgreSQL is required for semantic search integration tests.")

    object_storage = InMemoryObjectStorage()
    engine = create_engine(postgres_database_url(), pool_pre_ping=True)
    ensure_pgvector_extension(engine)
    AuthBase.metadata.drop_all(engine)
    DocumentsBase.metadata.drop_all(engine)
    MemoryBase.metadata.drop_all(engine)
    SearchBase.metadata.drop_all(engine)
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
    app.dependency_overrides[get_object_storage] = lambda: object_storage

    with TestClient(app, base_url="https://testserver") as client:
        yield client, engine

    engine.dispose()


def test_upload_generate_embeddings_and_semantic_search_returns_similar_documents(
    semantic_search_client: tuple[TestClient, Engine],
) -> None:
    client, engine = semantic_search_client

    cats = _upload_document(
        client,
        filename="cats.md",
        content=b"# Pets\n\nCats and kittens play indoors.",
    )
    dogs = _upload_document(
        client,
        filename="dogs.md",
        content=b"# Pets\n\nDogs and puppies play outdoors.",
    )
    quantum = _upload_document(
        client,
        filename="quantum.md",
        content=b"# Physics\n\nQuantum entanglement and particle spin.",
    )

    for upload in (cats, dogs, quantum):
        _wait_for_job_status(engine, upload["processing_job_id"], ProcessingStatus.COMPLETED)
    _wait_for_embeddings(engine, minimum_count=3)

    with Session(engine) as session:
        assert len(list(session.scalars(select(SearchDocumentRecord)).all())) == 3
        assert len(list(session.scalars(select(SearchEmbeddingRecord)).all())) == 3

    response = client.get(
        "/search",
        params={"q": "cats kittens pets", "mode": "semantic", "limit": 3},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "cats kittens pets"
    assert payload["count"] == 3

    result_ids = [result["document_id"] for result in payload["results"]]
    assert result_ids[0] == cats["document_id"]
    assert quantum["document_id"] in result_ids
    assert result_ids.index(cats["document_id"]) < result_ids.index(quantum["document_id"])
    assert payload["results"][0]["score"] >= payload["results"][-1]["score"]
