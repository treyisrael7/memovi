import uuid
from dataclasses import dataclass

from memovi_search.domain.exceptions import InvalidSearchDocumentIdError


@dataclass(frozen=True, slots=True)
class SearchDocumentId:
    """Stable identifier for a searchable document representation."""

    value: str

    @classmethod
    def new(cls) -> SearchDocumentId:
        return cls(str(uuid.uuid4()))

    def __post_init__(self) -> None:
        try:
            parsed = uuid.UUID(self.value)
        except ValueError as exc:
            raise InvalidSearchDocumentIdError(
                "Search document ID must be a valid UUID.",
            ) from exc

        object.__setattr__(self, "value", str(parsed))

    def __str__(self) -> str:
        return self.value
