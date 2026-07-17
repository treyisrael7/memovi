from memovi_intelligence.domain.entities import ReasoningContext, ReasoningResult


class PlaceholderReasoningProvider:
    """Placeholder AI provider adapter.

    Concrete LLM provider integrations will replace this implementation later.
    """

    def reason(self, context: ReasoningContext) -> ReasoningResult:
        raise NotImplementedError(
            "Reasoning provider integrations are not implemented yet.",
        )
