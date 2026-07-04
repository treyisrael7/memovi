from datetime import UTC, datetime

import pytest
from documents.application.commands.ingest_local_document import (
    IngestLocalDocument,
    IngestLocalDocumentCommand,
)
from documents.application.exceptions import EmptyUploadError, UnsupportedMimeTypeError
from documents.domain.entities import Document, DocumentVersion, ProcessingJob
from documents.domain.enums import ProcessingStatus
from documents.domain.repositories import DocumentRepository, ProcessingJobRepository
from documents.domain.value_objects import DocumentId


class InMemoryDocumentRepository(DocumentRepository):
    def __init__(self) -> None:
        self.documents: dict[str, Document] = {}
        self.versions: dict[str, DocumentVersion] = {}

    def get_by_id(self, document_id: DocumentId) -> Document | None:
        return self.documents.get(document_id.value)

    def add(self, document: Document) -> None:
        self.documents[document.id.value] = document

    def list_all(self) -> list[Document]:
        return list(self.documents.values())

    def add_version(self, version: DocumentVersion) -> None:
        self.versions[version.id] = version

    def get_latest_version(self, document_id: DocumentId) -> DocumentVersion | None:
        versions = [
            version for version in self.versions.values() if version.document_id == document_id
        ]
        if not versions:
            return None
        return max(versions, key=lambda version: version.version_number)


class InMemoryProcessingJobRepository(ProcessingJobRepository):
    def __init__(self) -> None:
        self.jobs: dict[str, ProcessingJob] = {}

    def get_by_id(self, job_id: str) -> ProcessingJob | None:
        return self.jobs.get(job_id)

    def get_by_document_id(self, document_id: DocumentId) -> ProcessingJob | None:
        for job in self.jobs.values():
            if job.document_id == document_id:
                return job
        return None

    def add(self, job: ProcessingJob) -> None:
        self.jobs[job.id] = job

    def save(self, job: ProcessingJob) -> None:
        self.jobs[job.id] = job


class InMemoryObjectStorage:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    def put_object(self, *, key: str, content: bytes, content_type: str) -> None:
        self.objects[key] = (content, content_type)

    def get_object(self, key: str) -> bytes:
        return self.objects[key][0]


def build_use_case() -> tuple[
    IngestLocalDocument,
    InMemoryDocumentRepository,
    InMemoryProcessingJobRepository,
    InMemoryObjectStorage,
]:
    documents = InMemoryDocumentRepository()
    processing_jobs = InMemoryProcessingJobRepository()
    object_storage = InMemoryObjectStorage()
    use_case = IngestLocalDocument(
        documents=documents,
        processing_jobs=processing_jobs,
        object_storage=object_storage,
    )
    return use_case, documents, processing_jobs, object_storage


def test_ingest_local_document_persists_metadata_and_stores_artifact() -> None:
    use_case, documents, processing_jobs, object_storage = build_use_case()

    result = use_case.execute(
        IngestLocalDocumentCommand(
            filename="notes.md",
            mime_type="text/markdown",
            content=b"# Notes",
        )
    )

    assert result.processing_status is ProcessingStatus.PENDING
    assert documents.get_by_id(DocumentId(result.document_id)) is not None
    assert processing_jobs.get_by_id(result.processing_job_id) is not None

    version = documents.get_latest_version(DocumentId(result.document_id))
    assert version is not None
    assert object_storage.get_object(version.storage_key) == b"# Notes"


def test_ingest_local_document_rejects_empty_upload() -> None:
    use_case, _, _, _ = build_use_case()

    with pytest.raises(EmptyUploadError):
        use_case.execute(
            IngestLocalDocumentCommand(
                filename="empty.txt",
                mime_type="text/plain",
                content=b"",
            )
        )


def test_ingest_local_document_rejects_unsupported_mime_type() -> None:
    use_case, _, _, _ = build_use_case()

    with pytest.raises(UnsupportedMimeTypeError):
        use_case.execute(
            IngestLocalDocumentCommand(
                filename="archive.zip",
                mime_type="application/zip",
                content=b"zip-bytes",
            )
        )


def test_ingest_local_document_creates_pending_processing_job() -> None:
    use_case, _, processing_jobs, _ = build_use_case()
    before = datetime.now(UTC)

    result = use_case.execute(
        IngestLocalDocumentCommand(
            filename="readme.txt",
            mime_type="text/plain",
            content=b"hello",
        )
    )

    job = processing_jobs.get_by_id(result.processing_job_id)
    assert job is not None
    assert job.status is ProcessingStatus.PENDING
    assert job.created_at >= before
