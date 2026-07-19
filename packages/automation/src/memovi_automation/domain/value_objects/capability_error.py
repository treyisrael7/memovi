from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from memovi_automation.domain.exceptions import InvalidCapabilityError


@dataclass(frozen=True, slots=True)
class CapabilityError:
    """Structured failure description attached to a CapabilityResult."""

    code: str
    message: str
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        code = self.code.strip()
        message = self.message.strip()

        if not code:
            raise InvalidCapabilityError("Capability error code is required.")
        if not message:
            raise InvalidCapabilityError("Capability error message is required.")
        if not isinstance(self.details, Mapping):
            raise InvalidCapabilityError("Capability error details must be a mapping.")

        object.__setattr__(self, "code", code)
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "details", MappingProxyType(dict(self.details)))
