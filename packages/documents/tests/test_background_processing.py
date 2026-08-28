import time
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from api.app import create_app
from api.database import database_session as api_database_session
from api.document_processing import configure_document_processing
from api.documents_session import build_documents_database_session
from api.events import InProcessEventDispatcher, TransactionScopedEventPublisher
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
from documents.domain.events import ProcessingCompleted, ProcessingFailed, ProcessingStarted
from documents.infrastructure.events.noop_event_publisher import CollectingEventPublisher
from documents.infrastructure.persistence import Base as DocumentsBase
from documents.infrastructure.persistence.models import (
    DocumentVersionRecord,
    ProcessingJobRecord,
)
from documents.infrastructure.queue import InMemoryProcessingJobQueue
from fastapi.testclient import TestClient
from memovi_shared import DEFAULT_WORKSPACE_ID
from memovi_workspace.infrastructure.persistence import Base as WorkspaceBase
from memovi_workspace.infrastructure.persistence.models import WorkspaceRecord
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


class FlakyObjectStorage(InMemoryObjectStorage):
    def __init__(self, *, fail_times: int, error: Exception) -> None:
        super().__init__()
        self._fail_times = fail_times
        self._error = error
        self._attempts = 0

    def get_object(self, key: str) -> bytes:
        self._attempts += 1
        if self._attempts <= self._fail_times:
            raise self._error
        return super().get_object(key)


def _wait_for_job_status(
    engine: Engine,
    processing_job_id: str,
    expected_status: ProcessingStatus,
    *,
    timeout_seconds: float = 15.0,
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


@pytest.fixture
def background_processing_client(
    request: pytest.FixtureRequest,
) -> Iterator[tuple[TestClient, Engine, InMemoryObjectStorage, CollectingEventPublisher]]:
    object_storage = getattr(request, "param", InMemoryObjectStorage())
    event_publisher = CollectingEventPublisher()

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    AuthBase.metadata.create_all(engine)
    DocumentsBase.metadata.create_all(engine)
    WorkspaceBase.metadata.create_all(engine)
    test_session_factory = sessionmaker(bind=engine, expire_on_commit=False)

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

    def worker_session_factory() -> Session:
        return test_session_factory()

    app = create_app()
    app.state.auth_session_factory = test_session_factory
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
        event_publisher=event_publisher,
    )

    app.dependency_overrides[api_database_session] = database_session
    app.dependency_overrides[get_auth_database_session] = database_session
    app.dependency_overrides[get_documents_database_session] = build_documents_database_session(
        database_session
    )
    app.dependency_overrides[get_object_storage] = lambda: object_storage

    with TestClient(app, base_url="https://testserver") as client:
        register_response = client.post(
            "/auth/register",
            json={"email": "processing-tester@example.com", "password": "password123"},
        )
        assert register_response.status_code == 201
        yield client, engine, object_storage, event_publisher

    engine.dispose()


def test_upload_returns_before_processing_completes(
    background_processing_client: tuple[
        TestClient, Engine, InMemoryObjectStorage, CollectingEventPublisher
    ],
) -> None:
    client, engine, _, _ = background_processing_client

    response = client.post(
        "/documents",
        files={"file": ("notes.md", b"# Notes", "text/markdown")},
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["processing_status"] == ProcessingStatus.PENDING.value

    with Session(engine) as session:
        job = session.get(ProcessingJobRecord, payload["processing_job_id"])
        assert job is not None
        # Worker may advance before the follow-up read; only require non-terminal progress.
        assert job.status != ProcessingStatus.COMPLETED.value
        assert job.status != ProcessingStatus.FAILED.value


def test_upload_is_processed_asynchronously_to_completion(
    background_processing_client: tuple[
        TestClient, Engine, InMemoryObjectStorage, CollectingEventPublisher
    ],
) -> None:
    client, engine, _, event_publisher = background_processing_client

    response = client.post(
        "/documents",
        files={"file": ("notes.md", b"# Title\r\n\r\nBody", "text/markdown")},
    )
    payload = response.json()

    job = _wait_for_job_status(
        engine,
        payload["processing_job_id"],
        ProcessingStatus.COMPLETED,
    )
    assert job.failure_reason is None

    with Session(engine) as session:
        version = session.scalar(
            select(DocumentVersionRecord).where(
                DocumentVersionRecord.document_id == payload["document_id"]
            )
        )
        assert version is not None
        assert version.normalized_content == "# Title\n\nBody"

    assert any(isinstance(event, ProcessingStarted) for event in event_publisher.events)
    assert any(isinstance(event, ProcessingCompleted) for event in event_publisher.events)


def test_background_processing_marks_invalid_documents_as_failed(
    background_processing_client: tuple[
        TestClient, Engine, InMemoryObjectStorage, CollectingEventPublisher
    ],
) -> None:
    client, engine, _, event_publisher = background_processing_client

    response = client.post(
        "/documents",
        files={"file": ("broken.pdf", b"not-a-pdf", "application/pdf")},
    )
    payload = response.json()

    job = _wait_for_job_status(
        engine,
        payload["processing_job_id"],
        ProcessingStatus.FAILED,
    )
    assert job.failure_reason is not None
    assert any(isinstance(event, ProcessingFailed) for event in event_publisher.events)


@pytest.mark.parametrize(
    "background_processing_client",
    [
        FlakyObjectStorage(
            fail_times=2,
            error=ConnectionError("temporary object storage outage"),
        ),
    ],
    indirect=True,
)
def test_background_processing_retries_transient_failures(
    background_processing_client: tuple[
        TestClient, Engine, InMemoryObjectStorage, CollectingEventPublisher
    ],
) -> None:
    client, engine, object_storage, event_publisher = background_processing_client
    assert isinstance(object_storage, FlakyObjectStorage)

    response = client.post(
        "/documents",
        files={"file": ("notes.md", b"Retry me", "text/markdown")},
    )
    payload = response.json()

    job = _wait_for_job_status(
        engine,
        payload["processing_job_id"],
        ProcessingStatus.COMPLETED,
    )
    assert job.failure_reason is None
    assert object_storage._attempts == 3
    assert any(isinstance(event, ProcessingCompleted) for event in event_publisher.events)


@pytest.mark.parametrize(
    "background_processing_client",
    [
        FlakyObjectStorage(
            fail_times=5,
            error=TimeoutError("object storage timeout"),
        ),
    ],
    indirect=True,
)
def test_background_processing_fails_after_retry_limit(
    background_processing_client: tuple[
        TestClient, Engine, InMemoryObjectStorage, CollectingEventPublisher
    ],
) -> None:
    client, engine, _, event_publisher = background_processing_client

    response = client.post(
        "/documents",
        files={"file": ("notes.md", b"Give up", "text/markdown")},
    )
    payload = response.json()

    job = _wait_for_job_status(
        engine,
        payload["processing_job_id"],
        ProcessingStatus.FAILED,
    )
    assert job.failure_reason is not None
    assert "timeout" in job.failure_reason.lower()
    assert any(isinstance(event, ProcessingFailed) for event in event_publisher.events)


def test_upload_is_processed_with_durable_queue() -> None:
    """Pending DB jobs complete when the durable queue is wired (no in-memory backlog)."""
    from documents.infrastructure.queue import SqlAlchemyProcessingJobQueue

    object_storage = InMemoryObjectStorage()
    event_publisher = CollectingEventPublisher()
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    AuthBase.metadata.create_all(engine)
    DocumentsBase.metadata.create_all(engine)
    WorkspaceBase.metadata.create_all(engine)
    test_session_factory = sessionmaker(bind=engine, expire_on_commit=False)

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
    queue = SqlAlchemyProcessingJobQueue(
        test_session_factory,
        poll_interval_seconds=0.05,
    )
    configure_document_processing(
        app,
        session_factory=test_session_factory,
        queue=queue,
        worker_config=DocumentProcessingWorkerConfig(
            max_retries=3,
            poll_interval_seconds=0.05,
        ),
        object_storage=object_storage,
        event_publisher=event_publisher,
    )
    app.dependency_overrides[api_database_session] = database_session
    app.dependency_overrides[get_auth_database_session] = database_session
    app.dependency_overrides[get_documents_database_session] = build_documents_database_session(
        database_session
    )
    app.dependency_overrides[get_object_storage] = lambda: object_storage

    with TestClient(app, base_url="https://testserver") as client:
        register_response = client.post(
            "/auth/register",
            json={"email": "durable-queue@example.com", "password": "password123"},
        )
        assert register_response.status_code == 201
        response = client.post(
            "/documents",
            files={"file": ("notes.md", b"# Durable\n\nBody", "text/markdown")},
        )
        assert response.status_code == 202
        payload = response.json()
        job = _wait_for_job_status(
            engine,
            payload["processing_job_id"],
            ProcessingStatus.COMPLETED,
        )
        assert job.attempt >= 1
        assert job.started_at is not None
        assert job.completed_at is not None

    engine.dispose()


def test_processing_completed_is_dispatched_after_worker_session_release() -> None:
    """Downstream handlers must not nest sessions on the worker connection.

    Flushing ProcessingCompleted while the worker session is still checked out
    nests transactions on SQLite StaticPool and can discard handler writes.
    """
    object_storage = InMemoryObjectStorage()
    dispatcher = InProcessEventDispatcher()
    open_sessions = {"count": 0}
    event_publisher = TransactionScopedEventPublisher(dispatcher)
    original_flush = event_publisher.flush
    sessions_open_at_flush: list[int] = []

    def flush_and_record() -> None:
        sessions_open_at_flush.append(open_sessions["count"])
        original_flush()

    event_publisher.flush = flush_and_record  # type: ignore[method-assign]

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    AuthBase.metadata.create_all(engine)
    DocumentsBase.metadata.create_all(engine)
    WorkspaceBase.metadata.create_all(engine)
    test_session_factory = sessionmaker(bind=engine, expire_on_commit=False)

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

    def worker_session_factory() -> Session:
        open_sessions["count"] += 1
        session = test_session_factory()
        original_close = session.close

        def close() -> None:
            if not getattr(session, "_memovi_counted_close", False):
                session._memovi_counted_close = True  # type: ignore[attr-defined]
                open_sessions["count"] -= 1
            original_close()

        session.close = close  # type: ignore[method-assign]
        return session

    visible_normalized: list[str | None] = []

    def on_processing_completed(event: object) -> None:
        if not isinstance(event, ProcessingCompleted):
            return
        with Session(engine) as session:
            version = session.scalar(
                select(DocumentVersionRecord).where(
                    DocumentVersionRecord.document_id == event.document_id.value
                )
            )
            visible_normalized.append(None if version is None else version.normalized_content)

    dispatcher.subscribe(ProcessingCompleted, on_processing_completed)

    app = create_app()
    app.state.auth_session_factory = test_session_factory
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
        event_publisher=event_publisher,
        event_dispatcher=dispatcher,
    )
    app.dependency_overrides[api_database_session] = database_session
    app.dependency_overrides[get_auth_database_session] = database_session
    app.dependency_overrides[get_documents_database_session] = build_documents_database_session(
        database_session
    )
    app.dependency_overrides[get_object_storage] = lambda: object_storage

    with TestClient(app, base_url="https://testserver") as client:
        register_response = client.post(
            "/auth/register",
            json={"email": "flush-after-close@example.com", "password": "password123"},
        )
        assert register_response.status_code == 201
        response = client.post(
            "/documents",
            files={"file": ("notes.md", b"# Title\r\n\nBody", "text/markdown")},
        )
        assert response.status_code == 202
        payload = response.json()
        _wait_for_job_status(
            engine,
            payload["processing_job_id"],
            ProcessingStatus.COMPLETED,
        )
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            if any(isinstance(event, ProcessingCompleted) for event in dispatcher.published_events):
                break
            time.sleep(0.05)
        else:
            pytest.fail("ProcessingCompleted was not dispatched after the job completed.")

    engine.dispose()

    assert sessions_open_at_flush == [0]
    assert visible_normalized == ["# Title\n\nBody"]
