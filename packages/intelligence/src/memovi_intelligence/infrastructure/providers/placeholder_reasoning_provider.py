from memovi_intelligence.domain.entities import ReasoningResult
from memovi_intelligence.domain.value_objects import Prompt


class PlaceholderReasoningProvider:
    """Placeholder AI provider adapter.

    Concrete LLM provider integrations will replace this implementation later.
    """

    def reason(self, prompt: Prompt, *, model: str | None = None) -> ReasoningResult:
        raise NotImplementedError(
            "Reasoning provider integrations are not implemented yet.",
        )
