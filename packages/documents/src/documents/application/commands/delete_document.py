import logging
from dataclasses import dataclass

from memovi_shared import WorkspaceId

from documents.application.exceptions import DocumentNotFoundError
from documents.application.ports import ObjectStorage
from documents.domain.repositories import DocumentRepository
from documents.domain.value_objects import DocumentId

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DeleteDocumentCommand:
    document_id: str
    workspace_id: WorkspaceId


class DeleteDocument:
    """Permanently removes a document, its versions, processing jobs, and stored artifact."""

    def __init__(self, *, documents: DocumentRepository, object_storage: ObjectStorage) -> None:
        self._documents = documents
        self._object_storage = object_storage

    def execute(self, command: DeleteDocumentCommand) -> None:
        document_id = DocumentId(command.document_id)
        document = self._documents.get_by_id(document_id, workspace_id=command.workspace_id)
        if document is None:
            raise DocumentNotFoundError("Document was not found.")

        version = self._documents.get_latest_version(document_id)
        self._documents.delete(document_id)

        if version is not None:
            try:
                self._object_storage.delete_object(version.storage_key)
            except Exception:
                # The document record is already removed; the object store is a
                # separate system and orphaned artifacts do not block deletion.
                logger.warning(
                    "Failed to delete stored artifact for document %s (key=%s)",
                    document_id.value,
                    version.storage_key,
                )
