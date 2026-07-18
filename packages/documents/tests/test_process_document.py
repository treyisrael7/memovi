import pytest
from documents.application.commands.ingest_local_document import (
    IngestLocalDocument,
    IngestLocalDocumentCommand,
)
from documents.application.commands.process_document import ProcessDocument, ProcessDocumentCommand
from documents.application.exceptions import TransientDocumentProcessingError
from documents.domain.entities import DocumentVersion, ProcessingJob
from documents.domain.enums import ProcessingStatus
from documents.domain.events import ProcessingCompleted, ProcessingFailed, ProcessingStarted
from documents.domain.value_objects import DocumentId
from documents.infrastructure.events.noop_event_publisher import CollectingEventPublisher
from documents.infrastructure.processors.registry import DefaultProcessorRegistry
from memovi_shared import WorkspaceId
from pdf_fixtures import build_pdf_with_text
from test_documents_application import (
    InMemoryDocumentRepository,
    InMemoryObjectStorage,
    InMemoryProcessingJobRepository,
)


def build_processing_engine(
    *,
    documents: InMemoryDocumentRepository | None = None,
    processing_jobs: InMemoryProcessingJobRepository | None = None,
    object_storage: InMemoryObjectStorage | None = None,
    event_publisher: CollectingEventPublisher | None = None,
) -> tuple[
    ProcessDocument,
    InMemoryDocumentRepository,
    InMemoryProcessingJobRepository,
    InMemoryObjectStorage,
    CollectingEventPublisher,
]:
    documents = documents or InMemoryDocumentRepository()
    processing_jobs = processing_jobs or InMemoryProcessingJobRepository()
    object_storage = object_storage or InMemoryObjectStorage()
    event_publisher = event_publisher or CollectingEventPublisher()
    use_case = ProcessDocument(
        documents=documents,
        processing_jobs=processing_jobs,
        object_storage=object_storage,
        processor_registry=DefaultProcessorRegistry(),
        event_publisher=event_publisher,
    )
    return use_case, documents, processing_jobs, object_storage, event_publisher


def seed_pending_job(
    *,
    documents: InMemoryDocumentRepository,
    processing_jobs: InMemoryProcessingJobRepository,
    object_storage: InMemoryObjectStorage,
    filename: str,
    mime_type: str,
    content: bytes,
) -> tuple[str, str, DocumentVersion]:
    ingest = IngestLocalDocument(
        documents=documents,
        processing_jobs=processing_jobs,
        object_storage=object_storage,
    )
    result = ingest.execute(
        IngestLocalDocumentCommand(
            workspace_id=WorkspaceId.default(),
            filename=filename,
            mime_type=mime_type,
            content=content,
        )
    )
    version = documents.get_latest_version(DocumentId(result.document_id))
    assert version is not None
    return result.processing_job_id, result.document_id, version


def test_process_document_extracts_markdown_and_completes() -> None:
    engine, documents, processing_jobs, object_storage, publisher = build_processing_engine()
    job_id, document_id, version = seed_pending_job(
        documents=documents,
        processing_jobs=processing_jobs,
        object_storage=object_storage,
        filename="notes.md",
        mime_type="text/markdown",
        content=b"# Title\r\n\r\nBody text",
    )

    result = engine.execute(ProcessDocumentCommand(processing_job_id=job_id))

    assert result.processing_status is ProcessingStatus.COMPLETED
    updated_version = documents.get_version_by_id(version.id)
    assert updated_version is not None
    assert updated_version.normalized_content == "# Title\n\nBody text"
    job = processing_jobs.get_by_id(job_id)
    assert job is not None
    assert job.status is ProcessingStatus.COMPLETED
    assert isinstance(publisher.events[0], ProcessingStarted)
    assert isinstance(publisher.events[1], ProcessingCompleted)
    assert publisher.events[0].document_id.value == document_id


def test_process_document_extracts_plain_text() -> None:
    engine, documents, processing_jobs, object_storage, _ = build_processing_engine()
    job_id, _, version = seed_pending_job(
        documents=documents,
        processing_jobs=processing_jobs,
        object_storage=object_storage,
        filename="readme.txt",
        mime_type="text/plain",
        content=b"Line one\r\n\r\nLine two",
    )

    result = engine.execute(ProcessDocumentCommand(processing_job_id=job_id))

    assert result.processing_status is ProcessingStatus.COMPLETED
    updated_version = documents.get_version_by_id(version.id)
    assert updated_version is not None
    assert updated_version.normalized_content == "Line one\n\nLine two"


def test_process_document_extracts_pdf() -> None:
    engine, documents, processing_jobs, object_storage, _ = build_processing_engine()
    pdf_bytes = build_pdf_with_text("Hello PDF")
    job_id, _, version = seed_pending_job(
        documents=documents,
        processing_jobs=processing_jobs,
        object_storage=object_storage,
        filename="report.pdf",
        mime_type="application/pdf",
        content=pdf_bytes,
    )

    result = engine.execute(ProcessDocumentCommand(processing_job_id=job_id))

    assert result.processing_status is ProcessingStatus.COMPLETED
    updated_version = documents.get_version_by_id(version.id)
    assert updated_version is not None
    assert "Hello PDF" in (updated_version.normalized_content or "")


def test_process_document_marks_failed_jobs_and_publishes_event() -> None:
    engine, documents, processing_jobs, object_storage, publisher = build_processing_engine()
    job_id, _, _ = seed_pending_job(
        documents=documents,
        processing_jobs=processing_jobs,
        object_storage=object_storage,
        filename="broken.pdf",
        mime_type="application/pdf",
        content=b"not-a-pdf",
    )

    result = engine.execute(ProcessDocumentCommand(processing_job_id=job_id))

    assert result.processing_status is ProcessingStatus.FAILED
    job = processing_jobs.get_by_id(job_id)
    assert job is not None
    assert job.status is ProcessingStatus.FAILED
    assert job.failure_reason is not None
    assert isinstance(publisher.events[0], ProcessingStarted)
    assert isinstance(publisher.events[1], ProcessingFailed)


def test_process_document_raises_transient_errors_for_infrastructure_failures() -> None:
    class FailingObjectStorage(InMemoryObjectStorage):
        def get_object(self, key: str) -> bytes:
            raise ConnectionError("storage unavailable")

    processor, documents, processing_jobs, object_storage, _ = build_processing_engine(
        object_storage=FailingObjectStorage(),
    )
    job_id, _, _ = seed_pending_job(
        documents=documents,
        processing_jobs=processing_jobs,
        object_storage=object_storage,
        filename="notes.md",
        mime_type="text/markdown",
        content=b"hello",
    )

    with pytest.raises(TransientDocumentProcessingError):
        processor.execute(ProcessDocumentCommand(processing_job_id=job_id))

    job = processing_jobs.get_by_id(job_id)
    assert job is not None
    assert job.status is ProcessingStatus.EXTRACTING


def test_process_document_transitions_through_expected_statuses() -> None:
    documents = InMemoryDocumentRepository()
    processing_jobs = TrackingProcessingJobRepository()
    object_storage = InMemoryObjectStorage()
    engine, _, _, _, _ = build_processing_engine(
        documents=documents,
        processing_jobs=processing_jobs,
        object_storage=object_storage,
    )
    job_id, _, _ = seed_pending_job(
        documents=documents,
        processing_jobs=processing_jobs,
        object_storage=object_storage,
        filename="notes.md",
        mime_type="text/markdown",
        content=b"Status flow",
    )

    engine.execute(ProcessDocumentCommand(processing_job_id=job_id))

    assert processing_jobs.status_history == [
        ProcessingStatus.EXTRACTING,
        ProcessingStatus.NORMALIZING,
        ProcessingStatus.COMPLETED,
    ]


class TrackingProcessingJobRepository(InMemoryProcessingJobRepository):
    def __init__(self) -> None:
        super().__init__()
        self.status_history: list[ProcessingStatus] = []

    def save(self, job: ProcessingJob) -> None:
        self.status_history.append(job.status)
        super().save(job)
