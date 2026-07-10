from dataclasses import dataclass

from memovi_memory.domain.exceptions import InvalidChunkError, InvalidChunkGeneratorError
from memovi_memory.domain.value_objects import ChunkIndex


@dataclass(frozen=True, slots=True)
class ChunkDraft:
    """In-memory structural chunk produced before persistence."""

    chunk_index: ChunkIndex
    text: str

    def __post_init__(self) -> None:
        if not self.text:
            raise InvalidChunkError("Chunk draft text is required.")


class ChunkGenerator:
    """Deterministic fixed-size chunking for normalized document text."""

    def __init__(self, *, max_chunk_size: int) -> None:
        if max_chunk_size <= 0:
            raise InvalidChunkGeneratorError("Max chunk size must be greater than zero.")
        self._max_chunk_size = max_chunk_size

    @property
    def max_chunk_size(self) -> int:
        return self._max_chunk_size

    def generate(self, normalized_text: str) -> list[ChunkDraft]:
        text = normalized_text.strip()
        if not text:
            return []

        drafts: list[ChunkDraft] = []
        next_index = 0
        for start in range(0, len(text), self._max_chunk_size):
            segment = text[start : start + self._max_chunk_size].strip()
            if not segment:
                continue

            drafts.append(
                ChunkDraft(
                    chunk_index=ChunkIndex(next_index),
                    text=segment,
                )
            )
            next_index += 1

        return drafts
