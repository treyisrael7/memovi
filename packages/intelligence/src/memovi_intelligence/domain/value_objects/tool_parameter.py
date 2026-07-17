from dataclasses import dataclass

from memovi_intelligence.domain.exceptions import InvalidToolError

_SUPPORTED_TYPES = frozenset(
    {
        "string",
        "integer",
        "number",
        "boolean",
        "object",
        "array",
    }
)


@dataclass(frozen=True, slots=True)
class ToolParameter:
    """Immutable description of a single tool argument."""

    name: str
    type: str
    description: str
    required: bool = True

    def __post_init__(self) -> None:
        name = self.name.strip()
        param_type = self.type.strip().lower()
        description = self.description.strip()

        if not name:
            raise InvalidToolError("Tool parameter name is required.")
        if param_type not in _SUPPORTED_TYPES:
            raise InvalidToolError(
                f"Unsupported tool parameter type '{self.type}'.",
            )
        if not description:
            raise InvalidToolError("Tool parameter description is required.")

        object.__setattr__(self, "name", name)
        object.__setattr__(self, "type", param_type)
        object.__setattr__(self, "description", description)
