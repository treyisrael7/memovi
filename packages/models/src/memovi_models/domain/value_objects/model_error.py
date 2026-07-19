from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from memovi_models.domain.exceptions import InvalidModelError


@dataclass(frozen=True, slots=True)
class ModelError:
    """Structured failure attached to a ModelResponse."""

    code: str
    message: str
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        code = self.code.strip()
        message = self.message.strip()
        if not code:
            raise InvalidModelError("Model error code is required.")
        if not message:
            raise InvalidModelError("Model error message is required.")
        if not isinstance(self.details, Mapping):
            raise InvalidModelError("Model error details must be a mapping.")
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "details", MappingProxyType(dict(self.details)))
