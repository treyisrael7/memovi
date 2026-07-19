from time import perf_counter

from memovi_models.domain.exceptions import (
    INVALID_CONFIGURATION_ERROR,
    UNSUPPORTED_CAPABILITY_ERROR,
    ModelProviderError,
)
from memovi_models.domain.value_objects import (
    PROVIDER_FAKE,
    ModelCapabilities,
    ModelError,
    ModelMetadata,
    ModelRequest,
    ModelResponse,
    ModelUsage,
    ProviderConfiguration,
    ProviderHealth,
)


class FakeModelProvider:
    """Deterministic in-memory provider for tests and local wiring.

    Not a production vendor adapter. Supports chat completion only.
    """

    def __init__(
        self,
        *,
        provider_id: str = PROVIDER_FAKE,
        model_id: str = "fake-chat",
        enabled: bool = True,
        healthy: bool = True,
        default_reply: str = "fake-response",
    ) -> None:
        self._provider_id = provider_id.strip().lower()
        self._model_id = model_id.strip()
        self._enabled = enabled
        self._healthy = healthy
        self._default_reply = default_reply
        self._config = ProviderConfiguration(
            provider_id=self._provider_id,
            enabled=enabled,
            default_model=self._model_id,
            timeout_seconds=5.0,
        )
        self._model = ModelMetadata(
            id=self._model_id,
            provider_id=self._provider_id,
            display_name=f"Fake Chat ({self._model_id})",
            capabilities=ModelCapabilities(chat=True),
            context_window=8192,
            description="Deterministic fake chat model for tests.",
        )

    def provider_id(self) -> str:
        return self._provider_id

    def configuration(self) -> ProviderConfiguration:
        return self._config

    def list_models(self) -> tuple[ModelMetadata, ...]:
        return (self._model,)

    def capabilities(self) -> ModelCapabilities:
        return self._model.capabilities

    def health(self) -> ProviderHealth:
        if not self._enabled:
            return ProviderHealth(
                provider_id=self._provider_id,
                status="unavailable",
                message="Fake provider is disabled.",
            )
        if not self._healthy:
            return ProviderHealth(
                provider_id=self._provider_id,
                status="unhealthy",
                message="Fake provider is marked unhealthy.",
            )
        return ProviderHealth(
            provider_id=self._provider_id,
            status="healthy",
            message="Fake provider is ready.",
        )

    def complete(self, request: ModelRequest) -> ModelResponse:
        started = perf_counter()
        if not self._enabled:
            return ModelResponse.failure_result(
                request_id=request.id,
                provider_id=self._provider_id,
                model_id=request.model_id,
                error=ModelError(
                    code=INVALID_CONFIGURATION_ERROR,
                    message="Fake provider is disabled.",
                ),
                duration=perf_counter() - started,
            )
        if request.stream:
            return ModelResponse.failure_result(
                request_id=request.id,
                provider_id=self._provider_id,
                model_id=request.model_id,
                error=ModelError(
                    code=UNSUPPORTED_CAPABILITY_ERROR,
                    message="Fake provider does not support streaming.",
                    details={"capability": "streaming"},
                ),
                duration=perf_counter() - started,
            )
        if request.model_id != self._model_id:
            raise ModelProviderError(
                f"Unknown model '{request.model_id}' for fake provider.",
                code="invalid_request",
                details={"model_id": request.model_id},
            )

        last_user = next(
            (message.content for message in reversed(request.messages) if message.role == "user"),
            "",
        )
        content = f"{self._default_reply}:{last_user}" if last_user else self._default_reply
        return ModelResponse.success_result(
            request_id=request.id,
            provider_id=self._provider_id,
            model_id=request.model_id,
            content=content,
            usage=ModelUsage(input_tokens=len(last_user), output_tokens=len(content), total_tokens=len(last_user) + len(content)),
            duration=perf_counter() - started,
            metadata={"fake": True},
        )
