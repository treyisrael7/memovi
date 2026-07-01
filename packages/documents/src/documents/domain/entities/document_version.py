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
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.id:
            raise InvalidDocumentVersionError("Document version ID is required.")
        if self.version_number < 1:
            raise InvalidDocumentVersionError("Document version number must be at least 1.")

    @classmethod
    def initial(
        cls,
        *,
        document_id: DocumentId,
        now: datetime | None = None,
    ) -> DocumentVersion:
        return cls(
            id=str(uuid.uuid4()),
            document_id=document_id,
            version_number=1,
            created_at=now or datetime.now(UTC),
        )
