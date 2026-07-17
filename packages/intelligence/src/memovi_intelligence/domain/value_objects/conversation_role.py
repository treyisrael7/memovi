from enum import StrEnum


class ConversationRole(StrEnum):
    """Role of a participant turn within a conversation."""

    USER = "user"
    ASSISTANT = "assistant"
