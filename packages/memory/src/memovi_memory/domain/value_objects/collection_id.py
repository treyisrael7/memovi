import uuid
from dataclasses import dataclass

from memovi_memory.domain.exceptions import InvalidCollectionIdError


@dataclass(frozen=True, slots=True)
class CollectionId:
    """Stable identifier for a workspace-scoped knowledge collection."""

    value: str

    @classmethod
    def new(cls) -> CollectionId:
        return cls(str(uuid.uuid4()))

    def __post_init__(self) -> None:
        try:
            parsed = uuid.UUID(self.value)
        except ValueError as exc:
            raise InvalidCollectionIdError("Collection ID must be a valid UUID.") from exc

        object.__setattr__(self, "value", str(parsed))

    def __str__(self) -> str:
        return self.value
