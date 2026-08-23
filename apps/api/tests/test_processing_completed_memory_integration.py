import time
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from api.app import create_app
from api.database import database_session as api_database_session
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
from documents.domain.events import ProcessingCompleted
from documents.infrastructure.persistence import Base as DocumentsBase
from documents.infrastructure.persistence.models import ProcessingJobRecord
from documents.infrastructure.queue import InMemoryProcessingJobQueue
from fastapi.testclient import TestClient
from memovi_memory.domain.events import KnowledgeMaterialized
from memovi_memory.infrastructure.persistence.models import Base as MemoryBase
from memovi_memory.infrastructure.persistence.models import ChunkRecord, KnowledgeItemRecord
from memovi_search.infrastructure.persistence.models import Base as SearchBase
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


def _wait_for_knowledge(
    engine: Engine,
    *,
    minimum_count: int = 1,
    timeout_seconds: float = 5.0,
) -> list[KnowledgeItemRecord]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        with Session(engine) as session:
            items = list(session.scalars(select(KnowledgeItemRecord)).all())
            if len(items) >= minimum_count:
                return items
        time.sleep(0.05)
    with Session(engine) as session:
        count = len(list(session.scalars(select(KnowledgeItemRecord)).all()))
    pytest.fail(
        f"Expected at least {minimum_count} knowledge items within "
        f"{timeout_seconds}s (found {count})."
    )


@pytest.fixture
def memory_integration_client() -> Iterator[tuple[TestClient, Engine, InProcessEventDispatcher]]:
    object_storage = InMemoryObjectStorage()

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    AuthBase.metadata.create_all(engine)
    WorkspaceBase.metadata.create_all(engine)
    DocumentsBase.metadata.create_all(engine)
    MemoryBase.metadata.create_all(engine)
    SearchBase.metadata.create_all(engine)
    with Session(engine) as seed_session:
        seed_session.add(
            WorkspaceRecord(
                id=DEFAULT_WORKSPACE_ID.value,
                name="Default",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )
        seed_session.commit()
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
    )
    dispatcher: InProcessEventDispatcher = app.state.event_dispatcher

    app.dependency_overrides[api_database_session] = database_session
    app.dependency_overrides[get_auth_database_session] = database_session
    app.dependency_overrides[get_documents_database_session] = build_documents_database_session(
        database_session
    )
    app.dependency_overrides[get_object_storage] = lambda: object_storage

    with TestClient(app, base_url="https://testserver") as client:
        register_response = client.post(
            "/auth/register",
            json={"email": "memory-integration@example.com", "password": "password123"},
        )
        assert register_response.status_code == 201
        yield client, engine, dispatcher

    engine.dispose()


def test_processing_completed_materializes_knowledge_and_publishes_event(
    memory_integration_client: tuple[TestClient, Engine, InProcessEventDispatcher],
) -> None:
    client, engine, dispatcher = memory_integration_client

    response = client.post(
        "/documents",
        files={"file": ("notes.md", b"# Title\r\n\r\nBody text for knowledge.", "text/markdown")},
    )
    assert response.status_code == 202
    payload = response.json()

    _wait_for_job_status(
        engine,
        payload["processing_job_id"],
        ProcessingStatus.COMPLETED,
    )
    _wait_for_knowledge(engine, minimum_count=1)

    with Session(engine) as session:
        knowledge_items = session.scalars(select(KnowledgeItemRecord)).all()
        chunks = session.scalars(select(ChunkRecord)).all()

        assert len(knowledge_items) == 1
        assert knowledge_items[0].document_id == payload["document_id"]
        assert len(chunks) >= 1

    completed_events = [
        event for event in dispatcher.published_events if isinstance(event, ProcessingCompleted)
    ]
    materialized_events = [
        event for event in dispatcher.published_events if isinstance(event, KnowledgeMaterialized)
    ]

    assert len(completed_events) == 1
    assert len(materialized_events) == 1
    materialized = materialized_events[0]
    assert materialized.document_id == payload["document_id"]
    assert materialized.chunk_count == len(chunks)
    assert materialized.knowledge_item_id == knowledge_items[0].id


def test_processing_completed_with_empty_normalized_content_skips_memory(
    memory_integration_client: tuple[TestClient, Engine, InProcessEventDispatcher],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, engine, dispatcher = memory_integration_client

    def normalize_to_empty(_: str) -> str:
        return "   "

    monkeypatch.setattr(
        "documents.application.commands.process_document.normalize_text",
        normalize_to_empty,
    )

    response = client.post(
        "/documents",
        files={"file": ("empty.md", b"ignored", "text/markdown")},
    )
    assert response.status_code == 202
    payload = response.json()

    _wait_for_job_status(
        engine,
        payload["processing_job_id"],
        ProcessingStatus.COMPLETED,
    )

    with Session(engine) as session:
        assert session.scalars(select(KnowledgeItemRecord)).all() == []
        assert session.scalars(select(ChunkRecord)).all() == []

    assert any(isinstance(event, ProcessingCompleted) for event in dispatcher.published_events)
    assert not any(
        isinstance(event, KnowledgeMaterialized) for event in dispatcher.published_events
    )


def test_documents_package_does_not_depend_on_memory() -> None:
    pyproject = Path("packages/documents/pyproject.toml").read_text(encoding="utf-8")
    assert "memovi-memory" not in pyproject


def test_memory_package_does_not_import_documents() -> None:
    memory_root = Path("packages/memory/src/memovi_memory")
    offenders: list[str] = []

    for path in memory_root.rglob("*.py"):
        content = path.read_text(encoding="utf-8")
        if "from documents" in content or "import documents" in content:
            offenders.append(str(path))

    assert offenders == []
