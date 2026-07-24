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
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        with Session(engine) as session:
            count = len(list(session.scalars(select(SearchEmbeddingRecord)).all()))
            if count >= minimum_count:
                return
        time.sleep(0.05)
    pytest.fail(f"Expected at least {minimum_count} embeddings.")


def _upload(client: TestClient, *, filename: str, content: bytes, mime_type: str) -> dict[str, str]:
    response = client.post(
        "/documents",
        files={"file": (filename, content, mime_type)},
    )
    assert response.status_code == 202
    payload = response.json()
    return {
        "document_id": str(payload["document_id"]),
        "processing_job_id": str(payload["processing_job_id"]),
    }


@pytest.fixture
def retrieval_client() -> Iterator[tuple[TestClient, Engine]]:
    if not postgres_available():
        pytest.skip("PostgreSQL is required for unified retrieval integration tests.")

    object_storage = InMemoryObjectStorage()
    engine = create_engine(postgres_database_url(), pool_pre_ping=True)
    ensure_pgvector_extension(engine)
    for base in (AuthBase, DocumentsBase, MemoryBase, SearchBase):
        base.metadata.drop_all(engine)
    for base in (AuthBase, DocumentsBase, MemoryBase, SearchBase):
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
    app.dependency_overrides[get_object_storage] = lambda: object_storage

    with TestClient(app, base_url="https://testserver") as client:
        yield client, engine

    engine.dispose()


def test_unified_retrieval_modes_filters_pagination_and_deduplication(
    retrieval_client: tuple[TestClient, Engine],
) -> None:
    client, engine = retrieval_client

    memovi_md = _upload(
        client,
        filename="memovi.md",
        content=b"# Memovi\n\nMemovi knowledge platform overview.",
        mime_type="text/markdown",
    )
    memovi_txt = _upload(
        client,
        filename="memovi.txt",
        content=b"Memovi plain text knowledge notes.",
        mime_type="text/plain",
    )
    gardening = _upload(
        client,
        filename="garden.md",
        content=b"# Garden\n\nTomato plants need sunlight.",
        mime_type="text/markdown",
    )

    for upload in (memovi_md, memovi_txt, gardening):
        _wait_for_job_status(engine, upload["processing_job_id"], ProcessingStatus.COMPLETED)
    _wait_for_embeddings(engine, minimum_count=3)

    with Session(engine) as session:
        assert len(list(session.scalars(select(SearchDocumentRecord)).all())) == 3

    keyword = client.get("/search", params={"q": "Memovi", "mode": "keyword"})
    assert keyword.status_code == 200
    keyword_payload = keyword.json()
    assert keyword_payload["count"] == 2
    assert {item["document_id"] for item in keyword_payload["results"]} == {
        memovi_md["document_id"],
        memovi_txt["document_id"],
    }

    semantic = client.get(
        "/search",
        params={"q": "Memovi knowledge", "mode": "semantic", "limit": 3},
    )
    assert semantic.status_code == 200
    assert semantic.json()["count"] == 3

    hybrid = client.get("/search", params={"q": "Memovi", "mode": "hybrid"})
    assert hybrid.status_code == 200
    hybrid_ids = [item["document_id"] for item in hybrid.json()["results"]]
    assert len(hybrid_ids) == len(set(hybrid_ids))
    assert memovi_md["document_id"] in hybrid_ids

    filtered = client.get(
        "/search",
        params={"q": "Memovi", "mode": "hybrid", "mime_type": "text/markdown"},
    )
    assert filtered.status_code == 200
    filtered_payload = filtered.json()
    # Hybrid fusion includes semantic candidates; mime filter keeps markdown docs only.
    assert filtered_payload["count"] == 2
    assert {item["document_id"] for item in filtered_payload["results"]} == {
        memovi_md["document_id"],
        gardening["document_id"],
    }
    assert all(
        item["document_id"] != memovi_txt["document_id"] for item in filtered_payload["results"]
    )

    page = client.get(
        "/search",
        params={"q": "Memovi", "mode": "keyword", "limit": 1, "offset": 1},
    )
    assert page.status_code == 200
    assert page.json()["count"] == 1
    assert page.json()["results"][0]["document_id"] in {
        memovi_md["document_id"],
        memovi_txt["document_id"],
    }
