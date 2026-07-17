from dataclasses import dataclass

from memovi_intelligence.domain.exceptions import InvalidPromptError
from memovi_intelligence.domain.value_objects.prompt_role import PromptRole


@dataclass(frozen=True, slots=True)
class PromptMessage:
    """Single role-tagged message in a provider-agnostic prompt."""

    role: PromptRole
    content: str

    def __post_init__(self) -> None:
        if not isinstance(self.role, PromptRole):
            raise InvalidPromptError("Prompt message role must be a PromptRole.")
        content = self.content.strip()
        if not content:
            raise InvalidPromptError("Prompt message content is required.")
        object.__setattr__(self, "content", content)
