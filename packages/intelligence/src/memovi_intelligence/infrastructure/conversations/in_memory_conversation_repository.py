from memovi_shared import WorkspaceId

from memovi_intelligence.domain.entities import Conversation
from memovi_intelligence.domain.exceptions import ConversationNotFoundError
from memovi_intelligence.domain.value_objects import ConversationId, ConversationTurn


class InMemoryConversationRepository:
    """Process-local conversation store for tests and early local wiring."""

    def __init__(self) -> None:
        self._conversations: dict[str, Conversation] = {}

    def create(self, *, workspace_id: WorkspaceId) -> Conversation:
        conversation = Conversation.create(workspace_id=workspace_id)
        self._conversations[conversation.id.value] = conversation
        return conversation

    def get(
        self,
        conversation_id: ConversationId,
        *,
        workspace_id: WorkspaceId,
    ) -> Conversation | None:
        conversation = self._conversations.get(conversation_id.value)
        if conversation is None or conversation.workspace_id != workspace_id:
            return None
        return conversation

    def append_turn(
        self,
        conversation_id: ConversationId,
        turn: ConversationTurn,
        *,
        workspace_id: WorkspaceId,
    ) -> Conversation:
        conversation = self.get(conversation_id, workspace_id=workspace_id)
        if conversation is None:
            raise ConversationNotFoundError(
                f"Conversation '{conversation_id.value}' was not found.",
            )
        updated = conversation.with_turn(turn)
        self._conversations[conversation_id.value] = updated
        return updated

    def list_turns(
        self,
        conversation_id: ConversationId,
        *,
        workspace_id: WorkspaceId,
    ) -> tuple[ConversationTurn, ...]:
        conversation = self.get(conversation_id, workspace_id=workspace_id)
        if conversation is None:
            raise ConversationNotFoundError(
                f"Conversation '{conversation_id.value}' was not found.",
            )
        return conversation.turns
