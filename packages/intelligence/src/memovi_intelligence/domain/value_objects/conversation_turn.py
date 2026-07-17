from dataclasses import dataclass
from datetime import datetime

from memovi_intelligence.domain.exceptions import InvalidConversationError
from memovi_intelligence.domain.value_objects.citation import Citation
from memovi_intelligence.domain.value_objects.conversation_role import ConversationRole


@dataclass(frozen=True, slots=True)
class ConversationTurn:
    """Immutable single exchange within a conversation."""

    role: ConversationRole
    content: str
    timestamp: datetime
    citations: tuple[Citation, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.role, ConversationRole):
            raise InvalidConversationError("turn role must be a ConversationRole.")
        content = self.content.strip()
        if not content:
            raise InvalidConversationError("turn content is required.")
        if not isinstance(self.timestamp, datetime):
            raise InvalidConversationError("turn timestamp must be a datetime.")
        if any(not isinstance(citation, Citation) for citation in self.citations):
            raise InvalidConversationError(
                "citations must contain Citation instances.",
            )

        object.__setattr__(self, "content", content)
        object.__setattr__(self, "citations", tuple(self.citations))
