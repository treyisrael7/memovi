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
from memovi_shared import WorkspaceId


class InMemoryDocumentRepository(DocumentRepository):
    def __init__(self) -> None:
        self.documents: dict[str, Document] = {}
        self.versions: dict[str, DocumentVersion] = {}

    def get_by_id(
        self,
        document_id: DocumentId,
        *,
        workspace_id: WorkspaceId,
    ) -> Document | None:
        document = self.documents.get(document_id.value)
        if document is None or document.workspace_id != workspace_id:
            return None
        return document

    def get_by_id_unscoped(self, document_id: DocumentId) -> Document | None:
        return self.documents.get(document_id.value)

    def get_by_connector_external_id(
        self,
        *,
        workspace_id: WorkspaceId,
        connector_id: str,
        external_id: str,
    ) -> Document | None:
        for document in self.documents.values():
            if (
                document.workspace_id == workspace_id
                and document.connector_id == connector_id.strip().lower()
                and document.external_id == external_id.strip()
            ):
                return document
        return None

    def add(self, document: Document) -> None:
        self.documents[document.id.value] = document

    def save(self, document: Document) -> None:
        self.documents[document.id.value] = document

    def delete(self, document_id: DocumentId) -> None:
        self.documents.pop(document_id.value, None)
        self.versions = {
            version_id: version
            for version_id, version in self.versions.items()
            if version.document_id != document_id
        }

    def list_by_workspace(self, *, workspace_id: WorkspaceId) -> list[Document]:
        return [
            document
            for document in self.documents.values()
            if document.workspace_id == workspace_id
        ]

    def count_by_connector(
        self,
        *,
        workspace_id: WorkspaceId,
        connector_id: str,
        external_id_prefix: str | None = None,
    ) -> int:
        count = 0
        for document in self.documents.values():
            if document.workspace_id != workspace_id:
                continue
            if document.connector_id != connector_id.strip().lower():
                continue
            if external_id_prefix is not None and not (
                document.external_id or ""
            ).startswith(external_id_prefix):
                continue
            count += 1
        return count

    def add_version(self, version: DocumentVersion) -> None:
        self.versions[version.id] = version

    def get_latest_version(self, document_id: DocumentId) -> DocumentVersion | None:
        versions = [
            version for version in self.versions.values() if version.document_id == document_id
        ]
        if not versions:
            return None
        return max(versions, key=lambda version: version.version_number)

    def get_version_by_id(self, version_id: str) -> DocumentVersion | None:
        return self.versions.get(version_id)

    def save_version(self, version: DocumentVersion) -> None:
        self.versions[version.id] = version


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

    def delete_object(self, key: str) -> None:
        self.objects.pop(key, None)


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
    workspace_id = WorkspaceId.default()

    result = use_case.execute(
        IngestLocalDocumentCommand(
            workspace_id=workspace_id,
            filename="notes.md",
            mime_type="text/markdown",
            content=b"# Notes",
        )
    )

    assert result.processing_status is ProcessingStatus.PENDING
    assert (
        documents.get_by_id(DocumentId(result.document_id), workspace_id=workspace_id) is not None
    )
    assert processing_jobs.get_by_id(result.processing_job_id) is not None

    version = documents.get_latest_version(DocumentId(result.document_id))
    assert version is not None
    assert object_storage.get_object(version.storage_key) == b"# Notes"


def test_ingest_local_document_rejects_empty_upload() -> None:
    use_case, _, _, _ = build_use_case()

    with pytest.raises(EmptyUploadError):
        use_case.execute(
            IngestLocalDocumentCommand(
                workspace_id=WorkspaceId.default(),
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
                workspace_id=WorkspaceId.default(),
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
            workspace_id=WorkspaceId.default(),
            filename="readme.txt",
            mime_type="text/plain",
            content=b"hello",
        )
    )

    job = processing_jobs.get_by_id(result.processing_job_id)
    assert job is not None
    assert job.status is ProcessingStatus.PENDING
    assert job.created_at >= before


def test_document_repository_isolates_workspaces() -> None:
    documents = InMemoryDocumentRepository()
    processing_jobs = InMemoryProcessingJobRepository()
    object_storage = InMemoryObjectStorage()
    use_case = IngestLocalDocument(
        documents=documents,
        processing_jobs=processing_jobs,
        object_storage=object_storage,
    )
    workspace_a = WorkspaceId.new()
    workspace_b = WorkspaceId.new()

    result_a = use_case.execute(
        IngestLocalDocumentCommand(
            workspace_id=workspace_a,
            filename="a.txt",
            mime_type="text/plain",
            content=b"a",
        )
    )
    use_case.execute(
        IngestLocalDocumentCommand(
            workspace_id=workspace_b,
            filename="b.txt",
            mime_type="text/plain",
            content=b"b",
        )
    )

    assert documents.get_by_id(DocumentId(result_a.document_id), workspace_id=workspace_b) is None
    assert len(documents.list_by_workspace(workspace_id=workspace_a)) == 1
    assert len(documents.list_by_workspace(workspace_id=workspace_b)) == 1


def test_ingest_connector_document_upsert_update_and_delete() -> None:
    from documents.application.commands.ingest_connector_document import (
        IngestConnectorDocument,
        IngestConnectorDocumentCommand,
    )

    documents = InMemoryDocumentRepository()
    processing_jobs = InMemoryProcessingJobRepository()
    object_storage = InMemoryObjectStorage()
    use_case = IngestConnectorDocument(
        documents=documents,
        processing_jobs=processing_jobs,
        object_storage=object_storage,
    )
    workspace_id = WorkspaceId.default()

    created = use_case.execute(
        IngestConnectorDocumentCommand(
            workspace_id=workspace_id,
            name="notes.md",
            mime_type="text/markdown",
            content=b"# one",
            connector_id="filesystem",
            external_id="folder:notes.md",
            external_path="/tmp/notes.md",
            change_kind="upsert",
        ),
    )
    assert created.created is True
    assert created.processing_job_id is not None
    document = documents.get_by_connector_external_id(
        workspace_id=workspace_id,
        connector_id="filesystem",
        external_id="folder:notes.md",
    )
    assert document is not None
    assert document.source_type.value == "connector"
    assert document.external_path == "/tmp/notes.md"

    updated = use_case.execute(
        IngestConnectorDocumentCommand(
            workspace_id=workspace_id,
            name="notes.md",
            mime_type="text/markdown",
            content=b"# two",
            connector_id="filesystem",
            external_id="folder:notes.md",
            external_path="/tmp/notes.md",
            change_kind="upsert",
        ),
    )
    assert updated.created is False
    assert updated.document_id == created.document_id
    latest = documents.get_latest_version(DocumentId(created.document_id))
    assert latest is not None
    assert latest.version_number == 2
    assert object_storage.get_object(latest.storage_key) == b"# two"

    deleted = use_case.execute(
        IngestConnectorDocumentCommand(
            workspace_id=workspace_id,
            name="notes.md",
            mime_type="text/markdown",
            content=b"",
            connector_id="filesystem",
            external_id="folder:notes.md",
            change_kind="delete",
        ),
    )
    assert deleted.document_id == created.document_id
    assert (
        documents.get_by_connector_external_id(
            workspace_id=workspace_id,
            connector_id="filesystem",
            external_id="folder:notes.md",
        )
        is None
    )
