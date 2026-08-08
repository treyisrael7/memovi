import uuid
from dataclasses import dataclass

from memovi_memory.domain.exceptions import InvalidTagIdError


@dataclass(frozen=True, slots=True)
class TagId:
    """Stable identifier for a workspace-scoped knowledge tag."""

    value: str

    @classmethod
    def new(cls) -> TagId:
        return cls(str(uuid.uuid4()))

    def __post_init__(self) -> None:
        try:
            parsed = uuid.UUID(self.value)
        except ValueError as exc:
            raise InvalidTagIdError("Tag ID must be a valid UUID.") from exc

        object.__setattr__(self, "value", str(parsed))

    def __str__(self) -> str:
        return self.value
