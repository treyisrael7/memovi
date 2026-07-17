from collections.abc import Sequence
from datetime import UTC, datetime

from memovi_intelligence.application.ports import ConversationRepository
from memovi_intelligence.domain.entities import Conversation
from memovi_intelligence.domain.exceptions import ConversationNotFoundError
from memovi_intelligence.domain.value_objects import (
    Citation,
    ConversationHistory,
    ConversationId,
    ConversationRole,
    ConversationTurn,
)


class ConversationService:
    """Application service for creating conversations and managing turn history."""

    def __init__(self, *, repository: ConversationRepository) -> None:
        self._repository = repository

    def create_conversation(self) -> Conversation:
        return self._repository.create()

    def append_user_turn(
        self,
        conversation_id: ConversationId,
        content: str,
        *,
        citations: Sequence[Citation] = (),
        timestamp: datetime | None = None,
    ) -> Conversation:
        return self._append_turn(
            conversation_id,
            role=ConversationRole.USER,
            content=content,
            citations=tuple(citations),
            timestamp=timestamp,
        )

    def append_assistant_turn(
        self,
        conversation_id: ConversationId,
        content: str,
        *,
        citations: Sequence[Citation] = (),
        timestamp: datetime | None = None,
    ) -> Conversation:
        return self._append_turn(
            conversation_id,
            role=ConversationRole.ASSISTANT,
            content=content,
            citations=tuple(citations),
            timestamp=timestamp,
        )

    def load_history(self, conversation_id: ConversationId) -> ConversationHistory:
        conversation = self._repository.get(conversation_id)
        if conversation is None:
            raise ConversationNotFoundError(
                f"Conversation '{conversation_id.value}' was not found.",
            )
        return conversation.history

    def get_conversation(self, conversation_id: ConversationId) -> Conversation:
        conversation = self._repository.get(conversation_id)
        if conversation is None:
            raise ConversationNotFoundError(
                f"Conversation '{conversation_id.value}' was not found.",
            )
        return conversation

    def _append_turn(
        self,
        conversation_id: ConversationId,
        *,
        role: ConversationRole,
        content: str,
        citations: tuple[Citation, ...],
        timestamp: datetime | None,
    ) -> Conversation:
        turn = ConversationTurn(
            role=role,
            content=content,
            timestamp=timestamp if timestamp is not None else datetime.now(UTC),
            citations=citations,
        )
        return self._repository.append_turn(conversation_id, turn)
