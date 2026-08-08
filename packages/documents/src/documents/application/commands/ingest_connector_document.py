"""Ingest normalized connector items into the Documents pipeline."""

from __future__ import annotations

import contextlib
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
from documents.domain.value_objects import DocumentId, DocumentName, MimeType, SourceType

# Match local upload support so connector imports behave identically downstream.
SUPPORTED_CONNECTOR_MIME_TYPES = frozenset(
    {
        "application/pdf",
        "text/markdown",
        "text/plain",
        "text/x-markdown",
    }
)


@dataclass(frozen=True, slots=True)
class IngestConnectorDocumentCommand:
    workspace_id: WorkspaceId
    name: str
    mime_type: str
    content: bytes
    connector_id: str
    external_id: str
    external_path: str | None = None
    change_kind: str = "upsert"


@dataclass(frozen=True, slots=True)
class IngestConnectorDocumentResult:
    document_id: str
    processing_job_id: str | None
    processing_status: ProcessingStatus | None
    change_kind: str
    created: bool
    event: DocumentCreated | None = None


class IngestConnectorDocument:
    """Create, update, or delete documents from connector-normalized items."""

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

    def execute(self, command: IngestConnectorDocumentCommand) -> IngestConnectorDocumentResult:
        change_kind = command.change_kind.strip().lower()
        if change_kind == "delete":
            return self._delete(command)
        if change_kind == "metadata_only":
            return self._metadata_only(command)
        return self._upsert(command)

    def _upsert(self, command: IngestConnectorDocumentCommand) -> IngestConnectorDocumentResult:
        if not command.content:
            raise EmptyUploadError("Connector import content is empty.")

        mime_type = MimeType(command.mime_type)
        if mime_type.value not in SUPPORTED_CONNECTOR_MIME_TYPES:
            raise UnsupportedMimeTypeError(
                f"MIME type '{mime_type.value}' is not supported for connector import.",
            )

        existing = self._documents.get_by_connector_external_id(
            workspace_id=command.workspace_id,
            connector_id=command.connector_id,
            external_id=command.external_id,
        )
        now = datetime.now(UTC)
        if existing is None:
            return self._create_new(command, mime_type=mime_type, now=now)
        return self._add_version(existing, command, mime_type=mime_type, now=now)

    def _create_new(
        self,
        command: IngestConnectorDocumentCommand,
        *,
        mime_type: MimeType,
        now: datetime,
    ) -> IngestConnectorDocumentResult:
        document = Document.create(
            workspace_id=command.workspace_id,
            name=DocumentName(command.name),
            mime_type=mime_type,
            source_type=SourceType("connector"),
            now=now,
            connector_id=command.connector_id.strip().lower(),
            external_id=command.external_id.strip(),
            external_path=command.external_path,
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
            workspace_id=command.workspace_id.value,
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

        return IngestConnectorDocumentResult(
            document_id=document.id.value,
            processing_job_id=job.id,
            processing_status=job.status,
            change_kind="upsert",
            created=True,
            event=DocumentCreated(document_id=document.id, occurred_at=now),
        )

    def _add_version(
        self,
        existing: Document,
        command: IngestConnectorDocumentCommand,
        *,
        mime_type: MimeType,
        now: datetime,
    ) -> IngestConnectorDocumentResult:
        updated = existing.with_identity(
            name=DocumentName(command.name),
            mime_type=mime_type,
            external_path=command.external_path,
        )
        latest = self._documents.get_latest_version(existing.id)
        next_number = 1 if latest is None else latest.version_number + 1
        version_id = str(uuid.uuid4())
        storage_key = DocumentVersion.build_storage_key(
            document_id=existing.id,
            version_id=version_id,
        )
        version = DocumentVersion(
            id=version_id,
            document_id=existing.id,
            version_number=next_number,
            storage_key=storage_key,
            created_at=now,
        )
        job = ProcessingJob.create_pending(
            document_id=existing.id,
            document_version_id=version.id,
            workspace_id=command.workspace_id.value,
            now=now,
        )

        self._object_storage.put_object(
            key=storage_key,
            content=command.content,
            content_type=mime_type.value,
        )
        self._documents.save(updated)
        self._documents.add_version(version)
        self._processing_jobs.add(job)

        return IngestConnectorDocumentResult(
            document_id=existing.id.value,
            processing_job_id=job.id,
            processing_status=job.status,
            change_kind="upsert",
            created=False,
        )

    def _metadata_only(
        self,
        command: IngestConnectorDocumentCommand,
    ) -> IngestConnectorDocumentResult:
        existing = self._documents.get_by_connector_external_id(
            workspace_id=command.workspace_id,
            connector_id=command.connector_id,
            external_id=command.external_id,
        )
        if existing is None:
            return IngestConnectorDocumentResult(
                document_id="",
                processing_job_id=None,
                processing_status=None,
                change_kind="metadata_only",
                created=False,
            )

        mime_type = MimeType(command.mime_type) if command.mime_type.strip() else existing.mime_type
        updated = existing.with_identity(
            name=DocumentName(command.name),
            mime_type=mime_type,
            external_path=command.external_path,
        )
        self._documents.save(updated)
        return IngestConnectorDocumentResult(
            document_id=existing.id.value,
            processing_job_id=None,
            processing_status=None,
            change_kind="metadata_only",
            created=False,
        )

    def _delete(self, command: IngestConnectorDocumentCommand) -> IngestConnectorDocumentResult:
        existing = self._documents.get_by_connector_external_id(
            workspace_id=command.workspace_id,
            connector_id=command.connector_id,
            external_id=command.external_id,
        )
        if existing is None:
            return IngestConnectorDocumentResult(
                document_id="",
                processing_job_id=None,
                processing_status=None,
                change_kind="delete",
                created=False,
            )

        version = self._documents.get_latest_version(existing.id)
        self._documents.delete(DocumentId(existing.id.value))
        if version is not None:
            with contextlib.suppress(Exception):
                self._object_storage.delete_object(version.storage_key)

        return IngestConnectorDocumentResult(
            document_id=existing.id.value,
            processing_job_id=None,
            processing_status=None,
            change_kind="delete",
            created=False,
        )
