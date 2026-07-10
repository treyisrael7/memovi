import uuid
from dataclasses import dataclass

from memovi_memory.domain.exceptions import InvalidKnowledgeItemIdError


@dataclass(frozen=True, slots=True)
class KnowledgeItemId:
    """Stable identifier for durable knowledge derived from processed documents."""

    value: str

    @classmethod
    def new(cls) -> KnowledgeItemId:
        return cls(str(uuid.uuid4()))

    def __post_init__(self) -> None:
        try:
            parsed = uuid.UUID(self.value)
        except ValueError as exc:
            raise InvalidKnowledgeItemIdError("Knowledge item ID must be a valid UUID.") from exc

        object.__setattr__(self, "value", str(parsed))

    def __str__(self) -> str:
        return self.value
