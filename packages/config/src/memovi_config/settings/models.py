"""Model / intelligence provider process settings."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from memovi_config.env import Environ, get_secret, get_str
from memovi_config.exceptions import ConfigurationError
from memovi_config.secrets import SecretValue


class ReasoningProviderKind(StrEnum):
    """Known reasoning provider identifiers."""

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
class ModelsSettings:
    """Typed configuration for intelligence / reasoning model selection."""

    provider: str = ReasoningProviderKind.FAKE.value
    model: str | None = None
    openai_api_key: SecretValue | None = None

    def __post_init__(self) -> None:
        provider = self.provider.strip().lower()
        if not provider:
            raise ConfigurationError("INTELLIGENCE_PROVIDER cannot be blank.")
        object.__setattr__(self, "provider", provider)

        if self.model is None:
            try:
                resolved_model = DEFAULT_MODELS[ReasoningProviderKind(provider)]
            except ValueError:
                resolved_model = f"{provider}-default"
        else:
            resolved_model = self.model.strip()
        if not resolved_model:
            raise ConfigurationError("INTELLIGENCE_MODEL cannot be blank.")
        object.__setattr__(self, "model", resolved_model)

    def ensure_provider_secrets(self) -> None:
        """Fail fast when the selected provider is missing required secrets.

        Called during full startup validation. Domain ``from_env`` loaders may
        load provider/model selection without requiring secrets yet.
        """
        if self.provider == ReasoningProviderKind.OPENAI.value and (
            self.openai_api_key is None or not self.openai_api_key.get_secret_value().strip()
        ):
            raise ConfigurationError(
                "OPENAI_API_KEY is required when INTELLIGENCE_PROVIDER=openai.",
            )

    def __repr__(self) -> str:
        return (
            "ModelsSettings("
            f"provider={self.provider!r}, "
            f"model={self.model!r}, "
            f"openai_api_key={'SecretValue(***)' if self.openai_api_key else None})"
        )

    @classmethod
    def from_environ(cls, environ: Environ) -> ModelsSettings:
        provider = (
            get_str(
                environ,
                "INTELLIGENCE_PROVIDER",
                default=ReasoningProviderKind.FAKE.value,
            )
            or ReasoningProviderKind.FAKE.value
        )
        model = get_str(environ, "INTELLIGENCE_MODEL", default=None)
        if model is None and provider.strip().lower() == ReasoningProviderKind.OPENAI.value:
            model = get_str(environ, "OPENAI_MODEL", default=None)
        openai_api_key = get_secret(environ, "OPENAI_API_KEY", default=None)
        return cls(provider=provider, model=model, openai_api_key=openai_api_key)
