from dataclasses import dataclass
from datetime import UTC, datetime

from memovi_shared import WorkspaceId

from memovi_intelligence.domain.exceptions import InvalidConversationError
from memovi_intelligence.domain.value_objects.conversation_history import (
    ConversationHistory,
)
from memovi_intelligence.domain.value_objects.conversation_id import ConversationId
from memovi_intelligence.domain.value_objects.conversation_turn import ConversationTurn

DEFAULT_CONVERSATION_TITLE = "New conversation"
MAX_CONVERSATION_TITLE_LENGTH = 200


def normalize_conversation_title(title: str) -> str:
    normalized = " ".join(title.split())
    if not normalized:
        raise InvalidConversationError("title must not be blank.")
    if len(normalized) > MAX_CONVERSATION_TITLE_LENGTH:
        raise InvalidConversationError(
            f"title must be at most {MAX_CONVERSATION_TITLE_LENGTH} characters.",
        )
    return normalized


def title_from_message(message: str) -> str:
    """Derive a display title from the first user message."""
    compact = " ".join(message.split())
    if not compact:
        return DEFAULT_CONVERSATION_TITLE
    if len(compact) <= MAX_CONVERSATION_TITLE_LENGTH:
        return compact
    return compact[: MAX_CONVERSATION_TITLE_LENGTH - 1].rstrip() + "…"


@dataclass(frozen=True, slots=True)
class Conversation:
    """Immutable multi-turn conversation state for reasoning workflows."""

    id: ConversationId
    workspace_id: WorkspaceId
    title: str
    history: ConversationHistory
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.id, ConversationId):
            raise InvalidConversationError("id must be a ConversationId.")
        if not isinstance(self.workspace_id, WorkspaceId):
            raise InvalidConversationError("workspace_id must be a WorkspaceId.")
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
        object.__setattr__(self, "title", normalize_conversation_title(self.title))

    @classmethod
    def create(
        cls,
        *,
        workspace_id: WorkspaceId,
        conversation_id: ConversationId | None = None,
        title: str = DEFAULT_CONVERSATION_TITLE,
        created_at: datetime | None = None,
    ) -> Conversation:
        now = created_at if created_at is not None else datetime.now(UTC)
        return cls(
            id=conversation_id or ConversationId.new(),
            workspace_id=workspace_id,
            title=title,
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
            workspace_id=self.workspace_id,
            title=self.title,
            history=self.history.append(turn),
            created_at=self.created_at,
            updated_at=timestamp,
        )

    def with_title(
        self,
        title: str,
        *,
        updated_at: datetime | None = None,
    ) -> Conversation:
        timestamp = updated_at if updated_at is not None else datetime.now(UTC)
        return Conversation(
            id=self.id,
            workspace_id=self.workspace_id,
            title=title,
            history=self.history,
            created_at=self.created_at,
            updated_at=timestamp,
        )

    @property
    def turns(self) -> tuple[ConversationTurn, ...]:
        return self.history.turns

    @property
    def has_default_title(self) -> bool:
        return self.title == DEFAULT_CONVERSATION_TITLE
