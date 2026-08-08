import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from api.app import create_app
from api.database import database_session as api_database_session
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
from documents.domain.enums import ProcessingStatus
from documents.infrastructure.persistence import Base as DocumentsBase
from documents.infrastructure.persistence.models import (
    DocumentRecord,
    DocumentVersionRecord,
    ProcessingJobRecord,
)
from documents.infrastructure.queue import NoOpProcessingJobQueue
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

    def delete_object(self, key: str) -> None:
        self.objects.pop(key, None)


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
    WorkspaceBase.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

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
        session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def worker_session_factory() -> Session:
        return session_factory()

    app = create_app()
    app.state.auth_session_factory = session_factory
    configure_document_processing(
        app,
        session_factory=worker_session_factory,
        queue=NoOpProcessingJobQueue(),
        object_storage=object_storage,
    )
    app.dependency_overrides[get_auth_database_session] = database_session
    app.dependency_overrides[api_database_session] = database_session
    app.dependency_overrides[get_documents_database_session] = build_documents_database_session(
        database_session
    )
    app.dependency_overrides[get_object_storage] = lambda: object_storage

    client = TestClient(app, base_url="https://testserver")
    try:
        register_response = client.post(
            "/auth/register",
            json={"email": "documents-tester@example.com", "password": "password123"},
        )
        assert register_response.status_code == 201
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


def test_list_and_get_document_include_processing_status(
    test_client: tuple[TestClient, Engine],
) -> None:
    client, _ = test_client
    upload = client.post(
        "/documents",
        files={"file": ("notes.md", b"# Notes", "text/markdown")},
    )
    document_id = upload.json()["document_id"]

    list_response = client.get("/documents")
    assert list_response.status_code == 200
    listed = next(item for item in list_response.json()["items"] if item["id"] == document_id)
    assert listed["processing_status"] == ProcessingStatus.PENDING.value

    get_response = client.get(f"/documents/{document_id}")
    assert get_response.status_code == 200
    assert get_response.json()["processing_status"] == ProcessingStatus.PENDING.value


def test_reprocess_document_queues_new_pending_job(
    test_client: tuple[TestClient, Engine],
) -> None:
    client, engine = test_client
    upload = client.post(
        "/documents",
        files={"file": ("notes.md", b"# Notes", "text/markdown")},
    )
    document_id = upload.json()["document_id"]
    original_job_id = upload.json()["processing_job_id"]

    response = client.post(f"/documents/{document_id}/reprocess")

    assert response.status_code == 202
    payload = response.json()
    assert payload["document_id"] == document_id
    assert payload["processing_job_id"] != original_job_id
    assert payload["processing_status"] == ProcessingStatus.PENDING.value

    with Session(engine) as session:
        jobs = session.query(ProcessingJobRecord).filter(
            ProcessingJobRecord.document_id == document_id
        ).all()
        assert len(jobs) == 2


def test_reprocess_missing_document_returns_404(
    test_client: tuple[TestClient, Engine],
) -> None:
    client, _ = test_client
    response = client.post(f"/documents/{uuid.uuid4()}/reprocess")
    assert response.status_code == 404


def test_reprocess_malformed_document_id_returns_404(
    test_client: tuple[TestClient, Engine],
) -> None:
    client, _ = test_client
    response = client.post("/documents/not-a-uuid/reprocess")
    assert response.status_code == 404


def test_delete_document_removes_document_versions_and_jobs(
    test_client: tuple[TestClient, Engine],
    object_storage: InMemoryObjectStorage,
) -> None:
    client, engine = test_client
    upload = client.post(
        "/documents",
        files={"file": ("notes.md", b"# Notes", "text/markdown")},
    )
    document_id = upload.json()["document_id"]

    with Session(engine) as session:
        version = session.scalar(
            select(DocumentVersionRecord).where(
                DocumentVersionRecord.document_id == document_id
            )
        )
        storage_key = version.storage_key
    assert object_storage.get_object(storage_key) == b"# Notes"

    response = client.delete(f"/documents/{document_id}")
    assert response.status_code == 204

    with Session(engine) as session:
        assert session.get(DocumentRecord, document_id) is None
        assert (
            session.query(DocumentVersionRecord)
            .filter(DocumentVersionRecord.document_id == document_id)
            .count()
            == 0
        )
        assert (
            session.query(ProcessingJobRecord)
            .filter(ProcessingJobRecord.document_id == document_id)
            .count()
            == 0
        )
    assert storage_key not in object_storage.objects

    assert client.get(f"/documents/{document_id}").status_code == 404


def test_delete_missing_document_returns_404(
    test_client: tuple[TestClient, Engine],
) -> None:
    client, _ = test_client
    response = client.delete(f"/documents/{uuid.uuid4()}")
    assert response.status_code == 404


def test_delete_malformed_document_id_returns_404(
    test_client: tuple[TestClient, Engine],
) -> None:
    client, _ = test_client
    response = client.delete("/documents/not-a-uuid")
    assert response.status_code == 404


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
