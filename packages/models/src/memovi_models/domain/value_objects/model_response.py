from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from memovi_models.domain.exceptions import InvalidModelError
from memovi_models.domain.value_objects.model_error import ModelError
from memovi_models.domain.value_objects.model_usage import ModelUsage


@dataclass(frozen=True, slots=True)
class ModelResponse:
    """Immutable outcome of a model invocation."""

    request_id: str
    provider_id: str
    model_id: str
    success: bool
    content: str | None = None
    error: ModelError | None = None
    usage: ModelUsage | None = None
    duration: float = 0.0
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        request_id = self.request_id.strip()
        provider_id = self.provider_id.strip().lower()
        model_id = self.model_id.strip()

        if not request_id:
            raise InvalidModelError("Model response request_id is required.")
        if not provider_id:
            raise InvalidModelError("Model response provider_id is required.")
        if not model_id:
            raise InvalidModelError("Model response model_id is required.")
        if self.duration < 0:
            raise InvalidModelError("Model response duration cannot be negative.")
        if self.success and self.error is not None:
            raise InvalidModelError("Successful model responses cannot include an error.")
        if not self.success and self.error is None:
            raise InvalidModelError("Failed model responses must include an error.")
        if self.error is not None and not isinstance(self.error, ModelError):
            raise InvalidModelError("Model response error must be a ModelError.")
        if self.usage is not None and not isinstance(self.usage, ModelUsage):
            raise InvalidModelError("Model response usage must be a ModelUsage.")
        if not isinstance(self.metadata, Mapping):
            raise InvalidModelError("Model response metadata must be a mapping.")

        object.__setattr__(self, "request_id", request_id)
        object.__setattr__(self, "provider_id", provider_id)
        object.__setattr__(self, "model_id", model_id)
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @classmethod
    def success_result(
        cls,
        *,
        request_id: str,
        provider_id: str,
        model_id: str,
        content: str | None = None,
        usage: ModelUsage | None = None,
        duration: float = 0.0,
        metadata: Mapping[str, object] | None = None,
    ) -> ModelResponse:
        return cls(
            request_id=request_id,
            provider_id=provider_id,
            model_id=model_id,
            success=True,
            content=content,
            error=None,
            usage=usage,
            duration=duration,
            metadata={} if metadata is None else metadata,
        )

    @classmethod
    def failure_result(
        cls,
        *,
        request_id: str,
        provider_id: str,
        model_id: str,
        error: ModelError,
        duration: float = 0.0,
        metadata: Mapping[str, object] | None = None,
    ) -> ModelResponse:
        return cls(
            request_id=request_id,
            provider_id=provider_id,
            model_id=model_id,
            success=False,
            content=None,
            error=error,
            usage=None,
            duration=duration,
            metadata={} if metadata is None else metadata,
        )
