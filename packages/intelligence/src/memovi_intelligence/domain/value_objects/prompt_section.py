from dataclasses import dataclass

from memovi_intelligence.domain.exceptions import InvalidPromptError


@dataclass(frozen=True, slots=True)
class PromptSection:
    """Named content block within a provider-agnostic prompt."""

    name: str
    content: str
    order: int

    def __post_init__(self) -> None:
        name = self.name.strip()
        content = self.content.strip()

        if not name:
            raise InvalidPromptError("Prompt section name is required.")
        if not content:
            raise InvalidPromptError("Prompt section content is required.")
        if self.order < 0:
            raise InvalidPromptError("Prompt section order cannot be negative.")

        object.__setattr__(self, "name", name)
        object.__setattr__(self, "content", content)
