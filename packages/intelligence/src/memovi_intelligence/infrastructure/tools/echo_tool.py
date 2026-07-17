from memovi_intelligence.domain.value_objects import ToolDefinition, ToolParameter


class EchoTool:
    """Deterministic fake tool that returns the input message unchanged.

    Intended for local wiring and tests — not a product capability.
    """

    TOOL_NAME = "echo"

    def name(self) -> str:
        return self.TOOL_NAME

    def description(self) -> str:
        return "Echoes the provided message unchanged."

    def schema(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.TOOL_NAME,
            description=self.description(),
            parameters=(
                ToolParameter(
                    name="message",
                    type="string",
                    description="Message to echo back unchanged.",
                    required=True,
                ),
            ),
        )

    def execute(self, arguments: dict[str, object]) -> object:
        message = str(arguments["message"])
        return {"message": message}
