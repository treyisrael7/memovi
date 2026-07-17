from dataclasses import dataclass
from enum import StrEnum

from memovi_intelligence.domain.exceptions import InvalidIntelligenceConfigError


class ReasoningProviderKind(StrEnum):
    """Known reasoning provider identifiers.

    Only ``fake`` is implemented. Remaining values reserve future adapters.
    """

    FAKE = "fake"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    GEMINI = "gemini"


DEFAULT_MODELS: dict[ReasoningProviderKind, str] = {
    ReasoningProviderKind.FAKE: "fake-reasoning-v1",
    ReasoningProviderKind.OPENAI: "gpt-4o-mini",
    ReasoningProviderKind.ANTHROPIC: "claude-sonnet-4-5",
    ReasoningProviderKind.OLLAMA: "llama3.2",
    ReasoningProviderKind.GEMINI: "gemini-2.0-flash",
}


@dataclass(frozen=True, slots=True)
class IntelligenceConfig:
    """Typed package configuration for Intelligence."""

    default_retrieval_limit: int = 20
    max_documents: int = 8
    max_chunks: int = 16
    max_estimated_tokens: int = 4_000
    provider: str = ReasoningProviderKind.FAKE.value
    model: str | None = None

    def __post_init__(self) -> None:
        if self.default_retrieval_limit < 1:
            raise InvalidIntelligenceConfigError(
                "default_retrieval_limit must be at least 1.",
            )
        if self.max_documents < 1:
            raise InvalidIntelligenceConfigError("max_documents must be at least 1.")
        if self.max_chunks < 1:
            raise InvalidIntelligenceConfigError("max_chunks must be at least 1.")
        if self.max_estimated_tokens < 1:
            raise InvalidIntelligenceConfigError("max_estimated_tokens must be at least 1.")

        provider = self.provider.strip().lower()
        if not provider:
            raise InvalidIntelligenceConfigError("provider cannot be blank.")
        object.__setattr__(self, "provider", provider)

        if self.model is None:
            try:
                resolved_model = DEFAULT_MODELS[ReasoningProviderKind(provider)]
            except ValueError:
                resolved_model = f"{provider}-default"
        else:
            resolved_model = self.model.strip()
        if not resolved_model:
            raise InvalidIntelligenceConfigError("model cannot be blank.")
        object.__setattr__(self, "model", resolved_model)

    @property
    def provider_name(self) -> str:
        return self.provider
