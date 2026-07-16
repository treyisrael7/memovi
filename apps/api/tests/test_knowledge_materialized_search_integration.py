import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

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
from documents.infrastructure.persistence import Base as DocumentsBase
from documents.infrastructure.queue import InMemoryProcessingJobQueue
from fastapi.testclient import TestClient
from memovi_memory.domain.events import KnowledgeMaterialized
from memovi_memory.infrastructure.persistence.models import Base as MemoryBase
from memovi_memory.infrastructure.persistence.models import ChunkRecord, KnowledgeItemRecord
from memovi_search.domain.events import SearchIndexed
from memovi_search.infrastructure.persistence.models import Base as SearchBase
from memovi_search.infrastructure.persistence.models import SearchDocumentRecord
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
def search_integration_client() -> Iterator[tuple[TestClient, Engine, InProcessEventDispatcher]]:
    object_storage = InMemoryObjectStorage()

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
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


def test_knowledge_materialized_indexes_search_and_publishes_event(
    search_integration_client: tuple[TestClient, Engine, InProcessEventDispatcher],
) -> None:
    _, engine, dispatcher = search_integration_client
    knowledge_item_id = str(uuid.uuid4())
    document_id = str(uuid.uuid4())
    document_version_id = str(uuid.uuid4())
    timestamp = datetime(2026, 7, 10, 16, 0, tzinfo=UTC)

    with Session(engine) as session:
        session.add(
            KnowledgeItemRecord(
                id=knowledge_item_id,
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
                knowledge_item_id=knowledge_item_id,
                document_id=document_id,
                document_version_id=document_version_id,
                chunk_index=0,
                text="Alpha passage.",
                created_at=timestamp,
            )
        )
        session.add(
            ChunkRecord(
                id=str(uuid.uuid4()),
                knowledge_item_id=knowledge_item_id,
                document_id=document_id,
                document_version_id=document_version_id,
                chunk_index=1,
                text="Beta passage.",
                created_at=timestamp,
            )
        )
        session.commit()

    dispatcher.publish(
        KnowledgeMaterialized(
            knowledge_item_id=knowledge_item_id,
            document_id=document_id,
            document_version_id=document_version_id,
            chunk_count=2,
            occurred_at=timestamp,
        )
    )

    with Session(engine) as session:
        search_documents = session.scalars(select(SearchDocumentRecord)).all()

        assert len(search_documents) == 1
        assert search_documents[0].knowledge_item_id == knowledge_item_id
        assert search_documents[0].searchable_text == "Alpha passage.Beta passage."

    indexed_events = [
        event for event in dispatcher.published_events if isinstance(event, SearchIndexed)
    ]

    assert len(indexed_events) == 1
    indexed = indexed_events[0]
    assert indexed.knowledge_item_id == knowledge_item_id
    assert indexed.document_id == document_id
    assert indexed.search_document_id == search_documents[0].id


def test_knowledge_materialized_with_missing_knowledge_skips_search(
    search_integration_client: tuple[TestClient, Engine, InProcessEventDispatcher],
) -> None:
    _, engine, dispatcher = search_integration_client

    dispatcher.publish(
        KnowledgeMaterialized(
            knowledge_item_id=str(uuid.uuid4()),
            document_id=str(uuid.uuid4()),
            document_version_id=str(uuid.uuid4()),
            chunk_count=0,
            occurred_at=datetime.now(UTC),
        )
    )

    with Session(engine) as session:
        assert session.scalars(select(SearchDocumentRecord)).all() == []

    assert not any(isinstance(event, SearchIndexed) for event in dispatcher.published_events)


def test_knowledge_materialized_with_empty_searchable_text_skips_search_indexed(
    search_integration_client: tuple[TestClient, Engine, InProcessEventDispatcher],
) -> None:
    _, engine, dispatcher = search_integration_client
    knowledge_item_id = str(uuid.uuid4())
    document_id = str(uuid.uuid4())
    document_version_id = str(uuid.uuid4())
    timestamp = datetime(2026, 7, 10, 16, 0, tzinfo=UTC)

    with Session(engine) as session:
        session.add(
            KnowledgeItemRecord(
                id=knowledge_item_id,
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
                knowledge_item_id=knowledge_item_id,
                document_id=document_id,
                document_version_id=document_version_id,
                chunk_index=0,
                text="   ",
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
        )
    )

    with Session(engine) as session:
        assert session.scalars(select(SearchDocumentRecord)).all() == []

    assert not any(isinstance(event, SearchIndexed) for event in dispatcher.published_events)


def test_memory_package_does_not_import_search() -> None:
    memory_root = Path("packages/memory/src/memovi_memory")
    offenders: list[str] = []

    for path in memory_root.rglob("*.py"):
        content = path.read_text(encoding="utf-8")
        if "from memovi_search" in content or "import memovi_search" in content:
            offenders.append(str(path))

    assert offenders == []


def test_search_package_does_not_import_memory() -> None:
    search_root = Path("packages/search/src/memovi_search")
    offenders: list[str] = []

    for path in search_root.rglob("*.py"):
        content = path.read_text(encoding="utf-8")
        if "from memovi_memory" in content or "import memovi_memory" in content:
            offenders.append(str(path))

    assert offenders == []


def test_memory_package_does_not_depend_on_search_in_pyproject() -> None:
    pyproject = Path("packages/memory/pyproject.toml").read_text(encoding="utf-8")
    assert "memovi-search" not in pyproject


def test_search_package_does_not_depend_on_memory_in_pyproject() -> None:
    pyproject = Path("packages/search/pyproject.toml").read_text(encoding="utf-8")
    assert "memovi-memory" not in pyproject
