from memovi_intelligence.application.ports import Tool
from memovi_intelligence.domain.exceptions import InvalidToolError, UnknownToolError
from memovi_intelligence.domain.value_objects import ToolDefinition


class ToolRegistry:
    """Registers and resolves tools without executing them."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        name = tool.name().strip()
        if not name:
            raise InvalidToolError("Cannot register a tool with a blank name.")
        definition = tool.schema()
        if definition.name != name:
            raise InvalidToolError(
                f"Tool schema name '{definition.name}' does not match tool name '{name}'.",
            )
        if name in self._tools:
            raise InvalidToolError(f"Tool '{name}' is already registered.")
        self._tools[name] = tool

    def discover(self) -> tuple[ToolDefinition, ...]:
        return tuple(tool.schema() for tool in self._tools.values())

    def resolve(self, name: str) -> Tool:
        tool = self._tools.get(name.strip())
        if tool is None:
            raise UnknownToolError(f"Unknown tool '{name}'.")
        return tool

    def contains(self, name: str) -> bool:
        return name.strip() in self._tools

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._tools.keys())
