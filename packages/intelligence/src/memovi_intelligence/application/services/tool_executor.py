from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from time import perf_counter

from memovi_intelligence.application.ports import Tool
from memovi_intelligence.application.services.tool_registry import ToolRegistry
from memovi_intelligence.domain.exceptions import (
    IntelligenceDomainError,
    InvalidToolArgumentsError,
    ToolExecutionError,
    ToolTimeoutError,
    UnknownToolError,
)
from memovi_intelligence.domain.value_objects import (
    ToolCall,
    ToolDefinition,
    ToolParameter,
    ToolResult,
)

_TYPE_CHECKS: dict[str, type | tuple[type, ...]] = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "object": Mapping,
    "array": (list, tuple),
}


class ToolExecutor:
    """Validates and executes tool calls resolved through a ToolRegistry."""

    def __init__(
        self,
        *,
        registry: ToolRegistry,
        default_timeout_seconds: float | None = 30.0,
    ) -> None:
        self._registry = registry
        if default_timeout_seconds is not None and default_timeout_seconds <= 0:
            raise ValueError("default_timeout_seconds must be positive when provided.")
        self._default_timeout_seconds = default_timeout_seconds

    @property
    def registry(self) -> ToolRegistry:
        return self._registry

    def execute(
        self,
        call: ToolCall,
        *,
        timeout_seconds: float | None = None,
    ) -> ToolResult:
        started = perf_counter()
        try:
            tool = self._registry.resolve(call.name)
        except UnknownToolError:
            raise

        definition = tool.schema()
        try:
            validated = _validate_arguments(call.arguments, definition)
        except InvalidToolArgumentsError:
            raise

        timeout = timeout_seconds if timeout_seconds is not None else self._default_timeout_seconds
        try:
            output = _invoke_tool(tool, validated, timeout_seconds=timeout)
        except ToolTimeoutError:
            raise
        except IntelligenceDomainError:
            raise
        except Exception as exc:
            raise ToolExecutionError(
                f"Tool '{call.name}' failed during execution.",
            ) from exc

        duration = perf_counter() - started
        return ToolResult.success_result(
            call_id=call.id,
            name=call.name,
            output=output,
            duration=duration,
            metadata={
                "argument_count": len(validated),
                "timeout_seconds": timeout,
            },
        )


def _invoke_tool(
    tool: Tool,
    arguments: dict[str, object],
    *,
    timeout_seconds: float | None,
) -> object:
    if timeout_seconds is None:
        return tool.execute(arguments)

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(tool.execute, arguments)
        try:
            return future.result(timeout=timeout_seconds)
        except FuturesTimeoutError as exc:
            future.cancel()
            raise ToolTimeoutError(
                f"Tool '{tool.name()}' timed out after {timeout_seconds} seconds.",
            ) from exc


def _validate_arguments(
    arguments: Mapping[str, object],
    definition: ToolDefinition,
) -> dict[str, object]:
    parameters = definition.parameter_map()
    unknown = sorted(set(arguments) - set(parameters))
    if unknown:
        raise InvalidToolArgumentsError(
            f"Unknown arguments for tool '{definition.name}': {', '.join(unknown)}.",
        )

    missing = sorted(
        parameter.name
        for parameter in definition.parameters
        if parameter.required and parameter.name not in arguments
    )
    if missing:
        raise InvalidToolArgumentsError(
            f"Missing required arguments for tool '{definition.name}': {', '.join(missing)}.",
        )

    validated: dict[str, object] = {}
    for name, value in arguments.items():
        parameter = parameters[name]
        _validate_parameter_value(parameter, value)
        validated[name] = value
    return validated


def _validate_parameter_value(parameter: ToolParameter, value: object) -> None:
    expected = _TYPE_CHECKS[parameter.type]
    if parameter.type == "boolean" and isinstance(value, bool):
        return
    if parameter.type == "integer" and isinstance(value, bool):
        raise InvalidToolArgumentsError(
            f"Argument '{parameter.name}' must be of type integer.",
        )
    if parameter.type == "number" and isinstance(value, bool):
        raise InvalidToolArgumentsError(
            f"Argument '{parameter.name}' must be of type number.",
        )
    if not isinstance(value, expected):
        raise InvalidToolArgumentsError(
            f"Argument '{parameter.name}' must be of type {parameter.type}.",
        )
