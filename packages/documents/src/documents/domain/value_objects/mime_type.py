from dataclasses import dataclass

from documents.domain.exceptions import InvalidMimeTypeError


@dataclass(frozen=True, slots=True)
class MimeType:
    """Normalized MIME type for imported document content."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if not normalized or "/" not in normalized:
            raise InvalidMimeTypeError("MIME type must include a type and subtype.")

        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value
