import time
from collections.abc import Iterator

import pytest
from api.app import create_app
from api.document_processing import configure_document_processing
from api.documents_session import build_documents_database_session
from api.events import InProcessEventDispatcher
from api.search_integration import build_search_knowledge
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
from memovi_search.application.queries import SearchKnowledgeQuery
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
            search_documents = session.scalars(select(SearchDocumentRecord)).all()
            if len(search_documents) >= minimum_count:
                return search_documents
        time.sleep(0.05)

    with Session(engine) as session:
        count = len(session.scalars(select(SearchDocumentRecord)).all())

    pytest.fail(
        f"Expected at least {minimum_count} search documents within "
        f"{timeout_seconds}s (found {count}).",
    )


@pytest.fixture
def full_text_search_client() -> Iterator[tuple[TestClient, Engine, InProcessEventDispatcher]]:
    if not postgres_available():
        pytest.skip("PostgreSQL is required for full-text search integration tests.")

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
    dispatcher: InProcessEventDispatcher = app.state.event_dispatcher

    app.dependency_overrides[get_auth_database_session] = database_session
    app.dependency_overrides[get_documents_database_session] = build_documents_database_session(
        database_session
    )
    app.dependency_overrides[get_object_storage] = lambda: object_storage

    with TestClient(app, base_url="https://testserver") as client:
        yield client, engine, dispatcher

    engine.dispose()


def test_upload_process_and_search_returns_memovi_document(
    full_text_search_client: tuple[TestClient, Engine, InProcessEventDispatcher],
) -> None:
    client, engine, _ = full_text_search_client

    response = client.post(
        "/documents",
        files={
            "file": (
                "memovi-overview.md",
                b"# Memovi\r\n\r\nMemovi is a self-hosted knowledge platform.",
                "text/markdown",
            )
        },
    )
    assert response.status_code == 202
    payload = response.json()

    _wait_for_job_status(
        engine,
        payload["processing_job_id"],
        ProcessingStatus.COMPLETED,
    )
    _wait_for_search_documents(engine)

    with Session(engine) as session:
        search = build_search_knowledge(session)
        results = search.execute(
            SearchKnowledgeQuery(
                query="Memovi",
                limit=10,
                offset=0,
            )
        )

        assert len(results) == 1
        assert results[0].document_id == payload["document_id"]
        assert "Memovi" in results[0].searchable_text
        assert results[0].relevance_score > 0

        missing_results = search.execute(
            SearchKnowledgeQuery(
                query="missing-term",
                limit=10,
                offset=0,
            )
        )
        assert missing_results == []
