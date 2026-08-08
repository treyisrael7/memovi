from __future__ import annotations

import os
from dataclasses import dataclass

from memovi_config.exceptions import ConfigurationError
from memovi_config.settings.models import (
    DEFAULT_MODELS as CONFIG_DEFAULT_MODELS,
)
from memovi_config.settings.models import (
    ModelsSettings,
)
from memovi_config.settings.models import (
    ReasoningProviderKind as ReasoningProviderKind,
)

from memovi_intelligence.domain.exceptions import InvalidIntelligenceConfigError

DEFAULT_MODELS = CONFIG_DEFAULT_MODELS


@dataclass(frozen=True, slots=True)
class IntelligenceConfig:
    """Typed package configuration for Intelligence."""

    default_retrieval_limit: int = 20
    max_documents: int = 8
    max_chunks: int = 16
    max_estimated_tokens: int = 4_000
    max_conversation_turns: int = 20
    max_conversation_tokens: int = 2_000
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
        if self.max_conversation_turns < 1:
            raise InvalidIntelligenceConfigError(
                "max_conversation_turns must be at least 1.",
            )
        if self.max_conversation_tokens < 1:
            raise InvalidIntelligenceConfigError(
                "max_conversation_tokens must be at least 1.",
            )

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

    @classmethod
    def from_env(cls) -> IntelligenceConfig:
        """Load provider selection from process environment variables.

        Environment parsing is owned by ``memovi_config.ModelsSettings``.
        """
        try:
            models = ModelsSettings.from_environ(os.environ)
        except ConfigurationError as exc:
            raise InvalidIntelligenceConfigError(str(exc)) from exc
        return cls(provider=models.provider, model=models.model)

    @property
    def provider_name(self) -> str:
        return self.provider
