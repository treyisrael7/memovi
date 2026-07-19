from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from memovi_models.domain.exceptions import InvalidModelError


@dataclass(frozen=True, slots=True)
class ProviderConfiguration:
    """Provider settings independent of UI and vendor SDKs.

    Secrets must not be embedded here. Prefer ``api_key_env`` (environment
    variable name) over storing credential values on the configuration object.
    """

    provider_id: str
    enabled: bool = True
    base_url: str | None = None
    api_key_env: str | None = None
    default_model: str | None = None
    timeout_seconds: float | None = 30.0
    extra: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        provider_id = self.provider_id.strip().lower()
        if not provider_id:
            raise InvalidModelError("Provider configuration provider_id is required.")
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise InvalidModelError(
                "Provider configuration timeout_seconds must be positive when set.",
            )
        if not isinstance(self.extra, Mapping):
            raise InvalidModelError("Provider configuration extra must be a mapping.")

        base_url = self.base_url.strip() if isinstance(self.base_url, str) else self.base_url
        if isinstance(base_url, str) and not base_url:
            raise InvalidModelError("Provider configuration base_url cannot be blank when set.")

        api_key_env = (
            self.api_key_env.strip() if isinstance(self.api_key_env, str) else self.api_key_env
        )
        if isinstance(api_key_env, str) and not api_key_env:
            raise InvalidModelError("Provider configuration api_key_env cannot be blank when set.")

        default_model = (
            self.default_model.strip()
            if isinstance(self.default_model, str)
            else self.default_model
        )
        if isinstance(default_model, str) and not default_model:
            raise InvalidModelError(
                "Provider configuration default_model cannot be blank when set.",
            )

        object.__setattr__(self, "provider_id", provider_id)
        object.__setattr__(self, "base_url", base_url)
        object.__setattr__(self, "api_key_env", api_key_env)
        object.__setattr__(self, "default_model", default_model)
        object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))


# Well-known provider identifiers for future adapters.
PROVIDER_OPENAI = "openai"
PROVIDER_ANTHROPIC = "anthropic"
PROVIDER_GEMINI = "gemini"
PROVIDER_OLLAMA = "ollama"
PROVIDER_OPENROUTER = "openrouter"
PROVIDER_LM_STUDIO = "lm_studio"
PROVIDER_FAKE = "fake"
