from collections.abc import Iterator

import pytest
from api.app import create_app
from auth.api.dependencies import get_database_session as get_auth_database_session
from auth.infrastructure.persistence import Base as AuthBase
from documents.api.dependencies import (
    get_database_session as get_documents_database_session,
)
from documents.api.dependencies import (
    get_object_storage,
)
from documents.domain.enums import ProcessingStatus
from documents.infrastructure.persistence import Base as DocumentsBase
from documents.infrastructure.persistence.models import (
    DocumentRecord,
    DocumentVersionRecord,
    ProcessingJobRecord,
)
from fastapi.testclient import TestClient
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
def object_storage() -> InMemoryObjectStorage:
    return InMemoryObjectStorage()


@pytest.fixture
def test_client(object_storage: InMemoryObjectStorage) -> Iterator[tuple[TestClient, Engine]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    AuthBase.metadata.create_all(engine)
    DocumentsBase.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def database_session() -> Iterator[Session]:
        session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[get_auth_database_session] = database_session
    app.dependency_overrides[get_documents_database_session] = database_session
    app.dependency_overrides[get_object_storage] = lambda: object_storage

    client = TestClient(app, base_url="https://testserver")
    try:
        yield client, engine
    finally:
        client.close()
        engine.dispose()


def test_upload_document_returns_accepted_response(
    test_client: tuple[TestClient, Engine],
    object_storage: InMemoryObjectStorage,
) -> None:
    client, engine = test_client
    response = client.post(
        "/documents",
        files={"file": ("notes.md", b"# Notes", "text/markdown")},
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["document_id"]
    assert payload["processing_job_id"]
    assert payload["processing_status"] == ProcessingStatus.PENDING.value

    with Session(engine) as session:
        document = session.get(DocumentRecord, payload["document_id"])
        assert document is not None
        assert document.name == "notes.md"
        assert document.mime_type == "text/markdown"
        assert document.source_type == "upload"

        version = session.scalar(
            select(DocumentVersionRecord).where(
                DocumentVersionRecord.document_id == payload["document_id"]
            )
        )
        assert version is not None
        assert object_storage.get_object(version.storage_key) == b"# Notes"

        job = session.get(ProcessingJobRecord, payload["processing_job_id"])
        assert job is not None
        assert job.status == ProcessingStatus.PENDING.value
        assert job.document_version_id == version.id


def test_upload_rejects_unsupported_file_type(test_client: tuple[TestClient, Engine]) -> None:
    client, _ = test_client
    response = client.post(
        "/documents",
        files={"file": ("archive.zip", b"zip-bytes", "application/zip")},
    )

    assert response.status_code == 415


def test_upload_rejects_empty_file(test_client: tuple[TestClient, Engine]) -> None:
    client, _ = test_client
    response = client.post(
        "/documents",
        files={"file": ("empty.txt", b"", "text/plain")},
    )

    assert response.status_code == 400


def test_upload_persists_pdf_document(
    test_client: tuple[TestClient, Engine],
    object_storage: InMemoryObjectStorage,
) -> None:
    client, engine = test_client
    pdf_bytes = b"%PDF-1.4 minimal"

    response = client.post(
        "/documents",
        files={"file": ("report.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 202
    payload = response.json()

    with Session(engine) as session:
        document = session.get(DocumentRecord, payload["document_id"])
        assert document is not None
        assert document.mime_type == "application/pdf"

        version = session.scalar(
            select(DocumentVersionRecord).where(
                DocumentVersionRecord.document_id == payload["document_id"]
            )
        )
        assert version is not None
        assert object_storage.get_object(version.storage_key) == pdf_bytes

        job = session.get(ProcessingJobRecord, payload["processing_job_id"])
        assert job is not None
        assert job.status == ProcessingStatus.PENDING.value
