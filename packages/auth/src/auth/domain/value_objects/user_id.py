import uuid
from dataclasses import dataclass

from auth.domain.exceptions import InvalidUserIdError


@dataclass(frozen=True, slots=True)
class UserId:
    """Stable identifier for a Memovi identity."""

    value: str

    @classmethod
    def new(cls) -> UserId:
        return cls(str(uuid.uuid4()))

    def __post_init__(self) -> None:
        try:
            parsed = uuid.UUID(self.value)
        except ValueError as exc:
            raise InvalidUserIdError("User ID must be a valid UUID.") from exc

        object.__setattr__(self, "value", str(parsed))

    def __str__(self) -> str:
        return self.value
