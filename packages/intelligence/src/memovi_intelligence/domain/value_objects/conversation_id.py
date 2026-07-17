import uuid
from dataclasses import dataclass

from memovi_intelligence.domain.exceptions import InvalidConversationIdError


@dataclass(frozen=True, slots=True)
class ConversationId:
    """Stable identifier for a conversation."""

    value: str

    @classmethod
    def new(cls) -> ConversationId:
        return cls(str(uuid.uuid4()))

    def __post_init__(self) -> None:
        try:
            parsed = uuid.UUID(self.value)
        except ValueError as exc:
            raise InvalidConversationIdError(
                "Conversation ID must be a valid UUID.",
            ) from exc

        object.__setattr__(self, "value", str(parsed))

    def __str__(self) -> str:
        return self.value
