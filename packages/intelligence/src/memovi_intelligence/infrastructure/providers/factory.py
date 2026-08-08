from __future__ import annotations

import os

from memovi_config.env import get_str
from memovi_config.settings.models import ModelsSettings

from memovi_intelligence.application.ports import ReasoningProvider
from memovi_intelligence.application.services.model_gateway import ModelGateway
from memovi_intelligence.config import DEFAULT_MODELS, IntelligenceConfig, ReasoningProviderKind
from memovi_intelligence.domain.exceptions import ReasoningProviderUnavailableError
from memovi_intelligence.infrastructure.providers.fake_reasoning_provider import (
    FakeReasoningProvider,
)
from memovi_intelligence.infrastructure.providers.openai_provider_settings import (
    OpenAIProviderSettings,
)
from memovi_intelligence.infrastructure.providers.openai_reasoning_provider import (
    OpenAIReasoningProvider,
)


def build_model_gateway(config: IntelligenceConfig | None = None) -> ModelGateway:
    """Build a ModelGateway with registered providers for configuration switching.

    Both ``fake`` and ``openai`` are registered when an OpenAI API key is available,
    so changing ``INTELLIGENCE_PROVIDER`` alone selects the active provider.
    """
    resolved = config or IntelligenceConfig.from_env()
    providers: dict[str, ReasoningProvider] = {
        ReasoningProviderKind.FAKE.value: FakeReasoningProvider(),
    }

    models = ModelsSettings.from_environ(os.environ)
    api_key = (
        models.openai_api_key.get_secret_value() if models.openai_api_key is not None else None
    )
    if api_key and api_key.strip():
        # OpenAI adapter uses OPENAI_MODEL (not the active intelligence provider model).
        openai_model = (
            get_str(os.environ, "OPENAI_MODEL", default=None)
            or DEFAULT_MODELS[ReasoningProviderKind.OPENAI]
        )
        settings = OpenAIProviderSettings(
            api_key=api_key,
            model=openai_model,
        )
        providers[ReasoningProviderKind.OPENAI.value] = OpenAIReasoningProvider(
            settings=settings,
        )
    elif resolved.provider == ReasoningProviderKind.OPENAI.value:
        raise ReasoningProviderUnavailableError(
            "OpenAI API key is not configured.",
        )

    return ModelGateway(providers=providers, config=resolved)
