import time
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from api.app import create_app
from api.document_processing import configure_document_processing
from api.documents_session import build_documents_database_session
from api.events import InProcessEventDispatcher
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
from memovi_search.infrastructure.persistence.models import SearchDocumentRecord
from postgres_support import postgres_available, postgres_database_url
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


def _wait_for_search_documents(
    engine: Engine,
    *,
    minimum_count: int = 1,
    timeout_seconds: float = 5.0,
) -> list[SearchDocumentRecord]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        with Session(engine) as session:
            search_documents = list(session.scalars(select(SearchDocumentRecord)).all())
            if len(search_documents) >= minimum_count:
                return search_documents
        time.sleep(0.05)

    with Session(engine) as session:
        count = len(list(session.scalars(select(SearchDocumentRecord)).all()))

    pytest.fail(
        f"Expected at least {minimum_count} search documents within "
        f"{timeout_seconds}s (found {count}).",
    )


def _upload_document(
    client: TestClient,
    *,
    filename: str,
    content: bytes,
    mime_type: str,
) -> dict[str, str]:
    response = client.post(
        "/documents",
        files={"file": (filename, content, mime_type)},
    )
    assert response.status_code == 202
    payload = response.json()
    assert isinstance(payload, dict)
    return {
        "document_id": str(payload["document_id"]),
        "processing_job_id": str(payload["processing_job_id"]),
    }


@pytest.fixture
def search_filter_client() -> Iterator[tuple[TestClient, Engine]]:
    if not postgres_available():
        pytest.skip("PostgreSQL is required for search filter integration tests.")

    object_storage = InMemoryObjectStorage()
    engine = create_engine(postgres_database_url(), pool_pre_ping=True)
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
    _: InProcessEventDispatcher = app.state.event_dispatcher

    app.dependency_overrides[get_auth_database_session] = database_session
    app.dependency_overrides[get_documents_database_session] = build_documents_database_session(
        database_session
    )
    app.dependency_overrides[get_search_database_session] = database_session
    app.dependency_overrides[get_object_storage] = lambda: object_storage

    with TestClient(app, base_url="https://testserver") as client:
        yield client, engine

    engine.dispose()


def test_search_api_filters_uploaded_documents_by_metadata(
    search_filter_client: tuple[TestClient, Engine],
) -> None:
    client, engine = search_filter_client
    before_upload = datetime.now(UTC) - timedelta(seconds=1)

    markdown = _upload_document(
        client,
        filename="memovi-markdown.md",
        content=b"# Memovi\n\nMemovi markdown knowledge.",
        mime_type="text/markdown",
    )
    plain = _upload_document(
        client,
        filename="memovi-plain.txt",
        content=b"Memovi plain text knowledge.",
        mime_type="text/plain",
    )

    _wait_for_job_status(engine, markdown["processing_job_id"], ProcessingStatus.COMPLETED)
    _wait_for_job_status(engine, plain["processing_job_id"], ProcessingStatus.COMPLETED)
    search_documents = _wait_for_search_documents(engine, minimum_count=2)
    after_upload = datetime.now(UTC) + timedelta(seconds=1)

    with Session(engine) as session:
        for record in session.scalars(select(SearchDocumentRecord)).all():
            assert record.source_type == "upload"
            assert record.mime_type in {"text/markdown", "text/plain"}

    unfiltered = client.get("/search", params={"q": "Memovi"})
    assert unfiltered.status_code == 200
    assert unfiltered.json()["count"] == 2

    by_mime = client.get(
        "/search",
        params={"q": "Memovi", "mime_type": "text/markdown"},
    )
    assert by_mime.status_code == 200
    mime_payload = by_mime.json()
    assert mime_payload["count"] == 1
    assert mime_payload["results"][0]["document_id"] == markdown["document_id"]

    by_source = client.get(
        "/search",
        params={"q": "Memovi", "source_type": "upload"},
    )
    assert by_source.status_code == 200
    assert by_source.json()["count"] == 2

    missing_source = client.get(
        "/search",
        params={"q": "Memovi", "source_type": "connector"},
    )
    assert missing_source.status_code == 200
    assert missing_source.json()["count"] == 0

    by_document = client.get(
        "/search",
        params={"q": "Memovi", "document_id": plain["document_id"]},
    )
    assert by_document.status_code == 200
    document_payload = by_document.json()
    assert document_payload["count"] == 1
    assert document_payload["results"][0]["document_id"] == plain["document_id"]

    by_date = client.get(
        "/search",
        params={
            "q": "Memovi",
            "created_after": before_upload.isoformat(),
            "created_before": after_upload.isoformat(),
        },
    )
    assert by_date.status_code == 200
    assert by_date.json()["count"] == 2

    outside_range = client.get(
        "/search",
        params={
            "q": "Memovi",
            "created_after": after_upload.isoformat(),
        },
    )
    assert outside_range.status_code == 200
    assert outside_range.json()["count"] == 0

    assert {document.document_id for document in search_documents} == {
        markdown["document_id"],
        plain["document_id"],
    }
