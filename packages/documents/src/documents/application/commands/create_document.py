from dataclasses import dataclass
from datetime import UTC, datetime

from documents.application.dto import DocumentDto
from documents.domain.entities import Document, DocumentVersion, ProcessingJob
from documents.domain.events import DocumentCreated
from documents.domain.repositories import DocumentRepository, ProcessingJobRepository
from documents.domain.value_objects import DocumentName, MimeType, SourceType


@dataclass(frozen=True, slots=True)
class CreateDocumentCommand:
    name: str
    mime_type: str
    source_type: str


@dataclass(frozen=True, slots=True)
class CreateDocumentResult:
    document: DocumentDto
    event: DocumentCreated


class CreateDocument:
    def __init__(
        self,
        *,
        documents: DocumentRepository,
        processing_jobs: ProcessingJobRepository,
    ) -> None:
        self._documents = documents
        self._processing_jobs = processing_jobs

    def execute(self, command: CreateDocumentCommand) -> CreateDocumentResult:
        now = datetime.now(UTC)
        document = Document.create(
            name=DocumentName(command.name),
            mime_type=MimeType(command.mime_type),
            source_type=SourceType(command.source_type),
            now=now,
        )
        version = DocumentVersion.initial(document_id=document.id, now=now)
        job = ProcessingJob.create_pending(
            document_id=document.id,
            document_version_id=version.id,
            now=now,
        )

        self._documents.add(document)
        self._documents.add_version(version)
        self._processing_jobs.add(job)

        return CreateDocumentResult(
            document=DocumentDto.from_document(document),
            event=DocumentCreated(document_id=document.id, occurred_at=now),
        )
