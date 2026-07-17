from __future__ import annotations

import os
from dataclasses import dataclass

from memovi_intelligence.config import IntelligenceConfig
from memovi_intelligence.domain.exceptions import (
    InvalidIntelligenceConfigError,
    ReasoningProviderUnavailableError,
)


@dataclass(frozen=True, slots=True)
class OpenAIProviderSettings:
    """Infrastructure settings for the OpenAI reasoning provider.

    Keeps API credentials and transport options out of the domain model.
    """

    api_key: str
    model: str
    timeout_seconds: float = 60.0
    base_url: str | None = None

    def __post_init__(self) -> None:
        api_key = self.api_key.strip()
        model = self.model.strip()
        if not api_key:
            raise InvalidIntelligenceConfigError("OpenAI API key is required.")
        if not model:
            raise InvalidIntelligenceConfigError("OpenAI model is required.")
        if self.timeout_seconds <= 0:
            raise InvalidIntelligenceConfigError("timeout_seconds must be positive.")
        base_url = self.base_url.strip() if self.base_url is not None else None
        if base_url is not None and not base_url:
            raise InvalidIntelligenceConfigError("base_url cannot be blank.")
        object.__setattr__(self, "api_key", api_key)
        object.__setattr__(self, "model", model)
        object.__setattr__(self, "base_url", base_url)

    @classmethod
    def from_config(
        cls,
        config: IntelligenceConfig,
        *,
        api_key: str | None = None,
        timeout_seconds: float = 60.0,
        base_url: str | None = None,
    ) -> OpenAIProviderSettings:
        """Build settings from IntelligenceConfig plus secret/env inputs."""
        resolved_key = api_key if api_key is not None else os.environ.get("OPENAI_API_KEY")
        if resolved_key is None or not resolved_key.strip():
            raise ReasoningProviderUnavailableError(
                "OpenAI API key is not configured.",
            )
        if config.model is None:
            raise InvalidIntelligenceConfigError("IntelligenceConfig.model was not resolved.")
        return cls(
            api_key=resolved_key,
            model=config.model,
            timeout_seconds=timeout_seconds,
            base_url=base_url,
        )
