from dataclasses import dataclass

from memovi_search.domain.exceptions import InvalidEmbeddingError


@dataclass(frozen=True, slots=True)
class EmbeddingVector:
    """Numeric embedding produced by an embedding provider."""

    values: list[float]
    dimensions: int

    def __post_init__(self) -> None:
        if len(self.values) == 0:
            raise InvalidEmbeddingError("Embedding vector cannot be empty.")
        if self.dimensions != len(self.values):
            raise InvalidEmbeddingError("Embedding dimensions must match vector length.")
        object.__setattr__(self, "values", list(self.values))
