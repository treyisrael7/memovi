from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from uuid import uuid4

from memovi_intelligence.domain.exceptions import InvalidToolError


@dataclass(frozen=True, slots=True)
class ToolCall:
    """Immutable request to execute a named tool with arguments."""

    name: str
    arguments: Mapping[str, object]
    id: str = ""

    def __post_init__(self) -> None:
        name = self.name.strip()
        call_id = self.id.strip() if self.id else str(uuid4())

        if not name:
            raise InvalidToolError("Tool call name is required.")
        if not isinstance(self.arguments, Mapping):
            raise InvalidToolError("Tool call arguments must be a mapping.")
        if not call_id:
            raise InvalidToolError("Tool call id is required.")

        object.__setattr__(self, "name", name)
        object.__setattr__(self, "id", call_id)
        object.__setattr__(
            self,
            "arguments",
            MappingProxyType(dict(self.arguments)),
        )

    @classmethod
    def create(
        cls,
        *,
        name: str,
        arguments: Mapping[str, object] | None = None,
        call_id: str | None = None,
    ) -> ToolCall:
        return cls(
            name=name,
            arguments={} if arguments is None else arguments,
            id=call_id or "",
        )
