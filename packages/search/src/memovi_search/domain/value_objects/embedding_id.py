import uuid
from dataclasses import dataclass

from memovi_search.domain.exceptions import InvalidEmbeddingIdError


@dataclass(frozen=True, slots=True)
class EmbeddingId:
    """Stable identifier for embedding metadata associated with a search document."""

    value: str

    @classmethod
    def new(cls) -> EmbeddingId:
        return cls(str(uuid.uuid4()))

    def __post_init__(self) -> None:
        try:
            parsed = uuid.UUID(self.value)
        except ValueError as exc:
            raise InvalidEmbeddingIdError("Embedding ID must be a valid UUID.") from exc

        object.__setattr__(self, "value", str(parsed))

    def __str__(self) -> str:
        return self.value
