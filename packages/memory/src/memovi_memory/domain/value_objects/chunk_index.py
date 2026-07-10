from dataclasses import dataclass

from memovi_memory.domain.exceptions import InvalidChunkIndexError


@dataclass(frozen=True, slots=True)
class ChunkIndex:
    """Zero-based ordering of a chunk within its parent knowledge item."""

    value: int

    def __post_init__(self) -> None:
        if self.value < 0:
            raise InvalidChunkIndexError("Chunk index must be zero or greater.")
