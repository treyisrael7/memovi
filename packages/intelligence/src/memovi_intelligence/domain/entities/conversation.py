from dataclasses import dataclass
from datetime import UTC, datetime

from memovi_intelligence.domain.exceptions import InvalidConversationError
from memovi_intelligence.domain.value_objects.conversation_history import (
    ConversationHistory,
)
from memovi_intelligence.domain.value_objects.conversation_id import ConversationId
from memovi_intelligence.domain.value_objects.conversation_turn import ConversationTurn


@dataclass(frozen=True, slots=True)
class Conversation:
    """Immutable multi-turn conversation state for reasoning workflows."""

    id: ConversationId
    history: ConversationHistory
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.id, ConversationId):
            raise InvalidConversationError("id must be a ConversationId.")
        if not isinstance(self.history, ConversationHistory):
            raise InvalidConversationError("history must be a ConversationHistory.")
        if not isinstance(self.created_at, datetime):
            raise InvalidConversationError("created_at must be a datetime.")
        if not isinstance(self.updated_at, datetime):
            raise InvalidConversationError("updated_at must be a datetime.")
        if self.updated_at < self.created_at:
            raise InvalidConversationError(
                "updated_at cannot be earlier than created_at.",
            )

    @classmethod
    def create(
        cls,
        *,
        conversation_id: ConversationId | None = None,
        created_at: datetime | None = None,
    ) -> Conversation:
        now = created_at if created_at is not None else datetime.now(UTC)
        return cls(
            id=conversation_id or ConversationId.new(),
            history=ConversationHistory.empty(),
            created_at=now,
            updated_at=now,
        )

    def with_turn(
        self,
        turn: ConversationTurn,
        *,
        updated_at: datetime | None = None,
    ) -> Conversation:
        timestamp = updated_at if updated_at is not None else turn.timestamp
        return Conversation(
            id=self.id,
            history=self.history.append(turn),
            created_at=self.created_at,
            updated_at=timestamp,
        )

    @property
    def turns(self) -> tuple[ConversationTurn, ...]:
        return self.history.turns
