import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from documents.domain.exceptions import InvalidDocumentVersionError
from documents.domain.value_objects import DocumentId


@dataclass(frozen=True, slots=True)
class DocumentVersion:
    """Immutable version snapshot for a normalized document."""

    id: str
    document_id: DocumentId
    version_number: int
    storage_key: str
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.id:
            raise InvalidDocumentVersionError("Document version ID is required.")
        if self.version_number < 1:
            raise InvalidDocumentVersionError("Document version number must be at least 1.")
        if not self.storage_key.strip():
            raise InvalidDocumentVersionError("Document version storage key is required.")

    @classmethod
    def initial(
        cls,
        *,
        document_id: DocumentId,
        storage_key: str,
        now: datetime | None = None,
    ) -> DocumentVersion:
        version_id = str(uuid.uuid4())
        return cls(
            id=version_id,
            document_id=document_id,
            version_number=1,
            storage_key=storage_key,
            created_at=now or datetime.now(UTC),
        )

    @staticmethod
    def build_storage_key(*, document_id: DocumentId, version_id: str) -> str:
        return f"documents/{document_id.value}/versions/{version_id}/original"
