from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from memovi_intelligence.domain.exceptions import InvalidPromptError
from memovi_intelligence.domain.value_objects.citation import Citation
from memovi_intelligence.domain.value_objects.prompt_message import PromptMessage
from memovi_intelligence.domain.value_objects.prompt_section import PromptSection

if TYPE_CHECKING:
    from memovi_intelligence.domain.entities.reasoning_context import ReasoningContext


@dataclass(frozen=True, slots=True)
class Prompt:
    """Complete provider-agnostic reasoning prompt built from a context."""

    sections: tuple[PromptSection, ...]
    messages: tuple[PromptMessage, ...]
    citations: tuple[Citation, ...]
    context: ReasoningContext

    def __post_init__(self) -> None:
        if not self.sections:
            raise InvalidPromptError("Prompt must include at least one section.")
        if not self.messages:
            raise InvalidPromptError("Prompt must include at least one message.")
        if any(not isinstance(section, PromptSection) for section in self.sections):
            raise InvalidPromptError("sections must contain PromptSection instances.")
        if any(not isinstance(message, PromptMessage) for message in self.messages):
            raise InvalidPromptError("messages must contain PromptMessage instances.")
        if any(not isinstance(citation, Citation) for citation in self.citations):
            raise InvalidPromptError("citations must contain Citation instances.")

        ordered_sections = tuple(sorted(self.sections, key=lambda section: section.order))
        orders = [section.order for section in ordered_sections]
        if orders != sorted(set(orders)):
            raise InvalidPromptError("Prompt section orders must be unique.")

        object.__setattr__(self, "sections", ordered_sections)
        object.__setattr__(self, "messages", tuple(self.messages))
        object.__setattr__(self, "citations", tuple(self.citations))

    def section(self, name: str) -> PromptSection:
        for section in self.sections:
            if section.name == name:
                return section
        raise InvalidPromptError(f"Prompt section '{name}' was not found.")

    @property
    def query(self) -> str:
        return self.context.query
