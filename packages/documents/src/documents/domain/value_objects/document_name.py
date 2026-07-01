from dataclasses import dataclass

from documents.domain.exceptions import InvalidDocumentNameError

MAX_DOCUMENT_NAME_LENGTH = 512


@dataclass(frozen=True, slots=True)
class DocumentName:
    """Human-readable label for imported knowledge content."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip()
        if not normalized:
            raise InvalidDocumentNameError("Document name is required.")
        if len(normalized) > MAX_DOCUMENT_NAME_LENGTH:
            raise InvalidDocumentNameError(
                f"Document name must be at most {MAX_DOCUMENT_NAME_LENGTH} characters.",
            )

        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value
