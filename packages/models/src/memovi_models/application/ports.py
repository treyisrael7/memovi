from typing import Protocol

from memovi_models.domain.value_objects import (
    ModelCapabilities,
    ModelMetadata,
    ModelRequest,
    ModelResponse,
    ProviderConfiguration,
    ProviderHealth,
)


class ModelProvider(Protocol):
    """Provider-neutral interface for model discovery and invocation.

    Implementations may use vendor SDKs internally but must not leak SDK types
    through this contract. Intelligence depends only on this protocol.
    """

    def provider_id(self) -> str:
        """Stable provider identifier (e.g. openai, ollama, fake)."""
        raise NotImplementedError

    def configuration(self) -> ProviderConfiguration:
        """Return the provider's configuration (no secret values)."""
        raise NotImplementedError

    def list_models(self) -> tuple[ModelMetadata, ...]:
        """Return models advertised by this provider."""
        raise NotImplementedError

    def capabilities(self) -> ModelCapabilities:
        """Return aggregate capabilities across advertised models."""
        raise NotImplementedError

    def health(self) -> ProviderHealth:
        """Return a normalized health snapshot for this provider."""
        raise NotImplementedError

    def complete(self, request: ModelRequest) -> ModelResponse:
        """Execute a chat/completion-style request and return a ModelResponse.

        Unsupported capabilities, auth failures, timeouts, and similar outcomes
        should be normalized into ModelResponse failures or ModelProviderError
        with stable codes — never raw vendor exceptions.
        """
        raise NotImplementedError
