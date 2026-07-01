from dataclasses import dataclass

from documents.domain.exceptions import InvalidSourceTypeError

ALLOWED_SOURCE_TYPES = frozenset({"upload", "connector", "import"})


@dataclass(frozen=True, slots=True)
class SourceType:
    """Provider-independent origin for normalized document content."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if normalized not in ALLOWED_SOURCE_TYPES:
            raise InvalidSourceTypeError(
                f"Source type must be one of: {', '.join(sorted(ALLOWED_SOURCE_TYPES))}.",
            )

        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value
