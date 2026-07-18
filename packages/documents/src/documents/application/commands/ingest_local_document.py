import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from memovi_shared import WorkspaceId

from documents.application.exceptions import EmptyUploadError, UnsupportedMimeTypeError
from documents.application.ports import ObjectStorage
from documents.domain.entities import Document, DocumentVersion, ProcessingJob
from documents.domain.enums import ProcessingStatus
from documents.domain.events import DocumentCreated
from documents.domain.repositories import DocumentRepository, ProcessingJobRepository
from documents.domain.value_objects import DocumentName, MimeType, SourceType

SUPPORTED_UPLOAD_MIME_TYPES = frozenset(
    {
        "application/pdf",
        "text/markdown",
        "text/plain",
        "text/x-markdown",
    }
)


@dataclass(frozen=True, slots=True)
class IngestLocalDocumentCommand:
    workspace_id: WorkspaceId
    filename: str
    mime_type: str
    content: bytes


@dataclass(frozen=True, slots=True)
class IngestLocalDocumentResult:
    document_id: str
    processing_job_id: str
    processing_status: ProcessingStatus
    event: DocumentCreated


class IngestLocalDocument:
    def __init__(
        self,
        *,
        documents: DocumentRepository,
        processing_jobs: ProcessingJobRepository,
        object_storage: ObjectStorage,
    ) -> None:
        self._documents = documents
        self._processing_jobs = processing_jobs
        self._object_storage = object_storage

    def execute(self, command: IngestLocalDocumentCommand) -> IngestLocalDocumentResult:
        if not command.content:
            raise EmptyUploadError("Uploaded file is empty.")

        mime_type = MimeType(command.mime_type)
        if mime_type.value not in SUPPORTED_UPLOAD_MIME_TYPES:
            raise UnsupportedMimeTypeError(
                f"MIME type '{mime_type.value}' is not supported for local upload.",
            )

        now = datetime.now(UTC)
        document = Document.create(
            workspace_id=command.workspace_id,
            name=DocumentName(command.filename),
            mime_type=mime_type,
            source_type=SourceType("upload"),
            now=now,
        )
        version_id = str(uuid.uuid4())
        storage_key = DocumentVersion.build_storage_key(
            document_id=document.id,
            version_id=version_id,
        )
        version = DocumentVersion(
            id=version_id,
            document_id=document.id,
            version_number=1,
            storage_key=storage_key,
            created_at=now,
        )
        job = ProcessingJob.create_pending(
            document_id=document.id,
            document_version_id=version.id,
            now=now,
        )

        self._object_storage.put_object(
            key=storage_key,
            content=command.content,
            content_type=mime_type.value,
        )
        self._documents.add(document)
        self._documents.add_version(version)
        self._processing_jobs.add(job)

        return IngestLocalDocumentResult(
            document_id=document.id.value,
            processing_job_id=job.id,
            processing_status=job.status,
            event=DocumentCreated(document_id=document.id, occurred_at=now),
        )
