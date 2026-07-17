from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from memovi_intelligence.domain.exceptions import InvalidToolError


@dataclass(frozen=True, slots=True)
class ToolResult:
    """Immutable outcome of a single tool execution."""

    call_id: str
    name: str
    success: bool
    output: object | None = None
    error: str | None = None
    duration: float = 0.0
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        call_id = self.call_id.strip()
        name = self.name.strip()
        error = self.error.strip() if isinstance(self.error, str) else self.error

        if not call_id:
            raise InvalidToolError("Tool result call_id is required.")
        if not name:
            raise InvalidToolError("Tool result name is required.")
        if self.duration < 0:
            raise InvalidToolError("Tool result duration cannot be negative.")
        if self.success and error:
            raise InvalidToolError("Successful tool results cannot include an error.")
        if not self.success and not error:
            raise InvalidToolError("Failed tool results must include an error.")
        if not isinstance(self.metadata, Mapping):
            raise InvalidToolError("Tool result metadata must be a mapping.")

        object.__setattr__(self, "call_id", call_id)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "error", error)
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @classmethod
    def success_result(
        cls,
        *,
        call_id: str,
        name: str,
        output: object | None = None,
        duration: float = 0.0,
        metadata: Mapping[str, object] | None = None,
    ) -> ToolResult:
        return cls(
            call_id=call_id,
            name=name,
            success=True,
            output=output,
            error=None,
            duration=duration,
            metadata={} if metadata is None else metadata,
        )

    @classmethod
    def failure_result(
        cls,
        *,
        call_id: str,
        name: str,
        error: str,
        duration: float = 0.0,
        metadata: Mapping[str, object] | None = None,
    ) -> ToolResult:
        return cls(
            call_id=call_id,
            name=name,
            success=False,
            output=None,
            error=error,
            duration=duration,
            metadata={} if metadata is None else metadata,
        )
