from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from uuid import uuid4

from memovi_models.domain.exceptions import InvalidModelError
from memovi_models.domain.value_objects.model_message import ModelMessage


@dataclass(frozen=True, slots=True)
class ModelRequest:
    """Immutable request to invoke a model through a provider."""

    model_id: str
    messages: tuple[ModelMessage, ...]
    id: str = ""
    temperature: float | None = None
    max_tokens: int | None = None
    stream: bool = False
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        model_id = self.model_id.strip()
        request_id = self.id.strip() if self.id else str(uuid4())

        if not model_id:
            raise InvalidModelError("Model request model_id is required.")
        if not request_id:
            raise InvalidModelError("Model request id is required.")
        if not self.messages:
            raise InvalidModelError("Model request messages must not be empty.")
        if any(not isinstance(message, ModelMessage) for message in self.messages):
            raise InvalidModelError("Model request messages must contain ModelMessage instances.")
        if self.temperature is not None and not 0.0 <= self.temperature <= 2.0:
            raise InvalidModelError("Model request temperature must be between 0 and 2.")
        if self.max_tokens is not None and self.max_tokens <= 0:
            raise InvalidModelError("Model request max_tokens must be positive when set.")
        if not isinstance(self.metadata, Mapping):
            raise InvalidModelError("Model request metadata must be a mapping.")

        object.__setattr__(self, "model_id", model_id)
        object.__setattr__(self, "id", request_id)
        object.__setattr__(self, "messages", tuple(self.messages))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @classmethod
    def create(
        cls,
        *,
        model_id: str,
        messages: Sequence[ModelMessage] | Sequence[tuple[str, str]],
        request_id: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stream: bool = False,
        metadata: Mapping[str, object] | None = None,
    ) -> ModelRequest:
        normalized: list[ModelMessage] = []
        for message in messages:
            if isinstance(message, ModelMessage):
                normalized.append(message)
            else:
                role, content = message
                normalized.append(ModelMessage(role=role, content=content))
        return cls(
            model_id=model_id,
            messages=tuple(normalized),
            id=request_id or "",
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
            metadata={} if metadata is None else metadata,
        )
