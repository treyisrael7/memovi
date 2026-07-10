import uuid
from dataclasses import dataclass

from memovi_memory.domain.exceptions import InvalidChunkIdError


@dataclass(frozen=True, slots=True)
class ChunkId:
    """Stable identifier for a retrievable knowledge chunk."""

    value: str

    @classmethod
    def new(cls) -> ChunkId:
        return cls(str(uuid.uuid4()))

    def __post_init__(self) -> None:
        try:
            parsed = uuid.UUID(self.value)
        except ValueError as exc:
            raise InvalidChunkIdError("Chunk ID must be a valid UUID.") from exc

        object.__setattr__(self, "value", str(parsed))

    def __str__(self) -> str:
        return self.value
