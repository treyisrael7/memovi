from memovi_models.application.ports import ModelProvider
from memovi_models.domain.exceptions import InvalidModelError, UnknownProviderError
from memovi_models.domain.value_objects import (
    ModelCapabilities,
    ModelMetadata,
    ProviderHealth,
)


class ModelRegistry:
    """Registers and discovers model providers without global mutable state.

    Providers are registered explicitly through dependency injection.
    """

    def __init__(self) -> None:
        self._providers: dict[str, ModelProvider] = {}

    def register(self, provider: ModelProvider) -> None:
        provider_id = provider.provider_id().strip().lower()
        if not provider_id:
            raise InvalidModelError("Cannot register a provider with a blank id.")
        configuration = provider.configuration()
        if configuration.provider_id != provider_id:
            raise InvalidModelError(
                f"Provider configuration id '{configuration.provider_id}' does not match "
                f"provider id '{provider_id}'.",
            )
        if provider_id in self._providers:
            raise InvalidModelError(f"Provider '{provider_id}' is already registered.")
        self._providers[provider_id] = provider

    def get(self, provider_id: str) -> ModelProvider:
        provider = self._providers.get(provider_id.strip().lower())
        if provider is None:
            raise UnknownProviderError(f"Unknown provider '{provider_id}'.")
        return provider

    def list_providers(self) -> tuple[str, ...]:
        return tuple(self._providers.keys())

    def list_models(self, provider_id: str | None = None) -> tuple[ModelMetadata, ...]:
        if provider_id is None:
            models: list[ModelMetadata] = []
            for provider in self._providers.values():
                models.extend(provider.list_models())
            return tuple(models)
        return self.get(provider_id).list_models()

    def capabilities(self, provider_id: str) -> ModelCapabilities:
        return self.get(provider_id).capabilities()

    def health(self, provider_id: str) -> ProviderHealth:
        return self.get(provider_id).health()

    def health_all(self) -> tuple[ProviderHealth, ...]:
        return tuple(provider.health() for provider in self._providers.values())

    def contains(self, provider_id: str) -> bool:
        return provider_id.strip().lower() in self._providers

    def get_model(self, model_id: str, *, provider_id: str | None = None) -> ModelMetadata:
        """Look up model metadata by id, optionally scoped to one provider."""
        needle = model_id.strip()
        models = self.list_models(provider_id)
        matches = [model for model in models if model.id == needle]
        if not matches:
            scope = f" for provider '{provider_id}'" if provider_id else ""
            raise InvalidModelError(f"Unknown model '{model_id}'{scope}.")
        if len(matches) > 1 and provider_id is None:
            raise InvalidModelError(
                f"Model '{model_id}' is advertised by multiple providers; " "specify provider_id.",
            )
        return matches[0]
