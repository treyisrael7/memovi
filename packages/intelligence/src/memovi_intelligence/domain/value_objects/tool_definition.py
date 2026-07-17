from dataclasses import dataclass

from memovi_intelligence.domain.exceptions import InvalidToolError
from memovi_intelligence.domain.value_objects.tool_parameter import ToolParameter


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """Immutable schema describing a callable tool."""

    name: str
    description: str
    parameters: tuple[ToolParameter, ...] = ()

    def __post_init__(self) -> None:
        name = self.name.strip()
        description = self.description.strip()

        if not name:
            raise InvalidToolError("Tool definition name is required.")
        if not description:
            raise InvalidToolError("Tool definition description is required.")
        if any(not isinstance(parameter, ToolParameter) for parameter in self.parameters):
            raise InvalidToolError("parameters must contain ToolParameter instances.")

        names = [parameter.name for parameter in self.parameters]
        if len(names) != len(set(names)):
            raise InvalidToolError("Tool parameter names must be unique.")

        object.__setattr__(self, "name", name)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "parameters", tuple(self.parameters))

    def parameter_map(self) -> dict[str, ToolParameter]:
        return {parameter.name: parameter for parameter in self.parameters}
