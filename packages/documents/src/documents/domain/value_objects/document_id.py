import uuid
from dataclasses import dataclass

from documents.domain.exceptions import InvalidDocumentIdError


@dataclass(frozen=True, slots=True)
class DocumentId:
    """Stable identifier for a normalized Memovi document."""

    value: str

    @classmethod
    def new(cls) -> DocumentId:
        return cls(str(uuid.uuid4()))

    def __post_init__(self) -> None:
        try:
            parsed = uuid.UUID(self.value)
        except ValueError as exc:
            raise InvalidDocumentIdError("Document ID must be a valid UUID.") from exc

        object.__setattr__(self, "value", str(parsed))

    def __str__(self) -> str:
        return self.value
