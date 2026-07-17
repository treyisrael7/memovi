from enum import StrEnum


class PromptRole(StrEnum):
    """Provider-agnostic role for a prompt message."""

    SYSTEM = "system"
    USER = "user"
