from dataclasses import FrozenInstanceError
from time import sleep

import pytest
from memovi_intelligence.application.ports import Tool
from memovi_intelligence.application.services import ToolExecutor, ToolRegistry
from memovi_intelligence.domain.entities import ReasoningContext, ReasoningRequest, ReasoningResult
from memovi_intelligence.domain.exceptions import (
    InvalidToolArgumentsError,
    InvalidToolError,
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
from memovi_intelligence.infrastructure import EchoTool


class _NoopTool:
    def name(self) -> str:
        return "noop"

    def description(self) -> str:
        return "No-op tool for registry discovery tests."

    def schema(self) -> ToolDefinition:
        return ToolDefinition(name="noop", description=self.description(), parameters=())

    def execute(self, arguments: dict[str, object]) -> object:
        return {"ok": True}


class _FailingEchoTool(EchoTool):
    def execute(self, arguments: dict[str, object]) -> object:
        raise RuntimeError("echo tool failed")


class _SlowEchoTool(EchoTool):
    def execute(self, arguments: dict[str, object]) -> object:
        sleep(0.2)
        return super().execute(arguments)


def _registry_with(*tools: Tool) -> ToolRegistry:
    registry = ToolRegistry()
    for tool in tools:
        registry.register(tool)
    return registry


def test_tool_registry_register_discover_and_resolve() -> None:
    echo = EchoTool()
    noop = _NoopTool()
    registry = _registry_with(echo, noop)

    assert {definition.name for definition in registry.discover()} == {"echo", "noop"}
    assert registry.resolve("echo") is echo
    assert registry.contains("noop")
    assert registry.names == ("echo", "noop")


def test_tool_registry_rejects_duplicate_and_unknown() -> None:
    registry = _registry_with(EchoTool())

    with pytest.raises(InvalidToolError, match="already registered"):
        registry.register(EchoTool())
    with pytest.raises(UnknownToolError, match="Unknown tool"):
        registry.resolve("missing")


def test_tool_executor_executes_echo_tool() -> None:
    executor = ToolExecutor(registry=_registry_with(EchoTool()))
    call = ToolCall.create(name="echo", arguments={"message": "Hello Memovi"})

    result = executor.execute(call)

    assert isinstance(result, ToolResult)
    assert result.success is True
    assert result.call_id == call.id
    assert result.name == "echo"
    assert result.output == {"message": "Hello Memovi"}
    assert result.duration >= 0.0
    assert result.metadata["argument_count"] == 1


def test_tool_executor_rejects_unknown_tool() -> None:
    executor = ToolExecutor(registry=ToolRegistry())

    with pytest.raises(UnknownToolError):
        executor.execute(ToolCall.create(name="missing", arguments={}))


def test_tool_executor_validates_arguments() -> None:
    executor = ToolExecutor(registry=_registry_with(EchoTool()))

    with pytest.raises(InvalidToolArgumentsError, match="Missing required"):
        executor.execute(ToolCall.create(name="echo", arguments={}))
    with pytest.raises(InvalidToolArgumentsError, match="Unknown arguments"):
        executor.execute(
            ToolCall.create(name="echo", arguments={"message": "x", "extra": 1}),
        )
    with pytest.raises(InvalidToolArgumentsError, match="must be of type string"):
        executor.execute(ToolCall.create(name="echo", arguments={"message": 123}))


def test_tool_executor_maps_execution_failure() -> None:
    executor = ToolExecutor(registry=_registry_with(_FailingEchoTool()))

    with pytest.raises(ToolExecutionError, match="failed during execution"):
        executor.execute(ToolCall.create(name="echo", arguments={"message": "boom"}))


def test_tool_executor_maps_timeout() -> None:
    executor = ToolExecutor(
        registry=_registry_with(_SlowEchoTool()),
        default_timeout_seconds=0.05,
    )

    with pytest.raises(ToolTimeoutError, match="timed out"):
        executor.execute(ToolCall.create(name="echo", arguments={"message": "slow"}))


def test_tool_value_objects_are_immutable() -> None:
    definition = ToolDefinition(
        name="echo",
        description="Echo",
        parameters=(ToolParameter(name="message", type="string", description="Text"),),
    )
    call = ToolCall.create(name="echo", arguments={"message": "hi"})
    result = ToolResult.success_result(call_id=call.id, name="echo", output={"message": "hi"})

    with pytest.raises(FrozenInstanceError):
        definition.name = "other"  # type: ignore[misc]
    with pytest.raises(TypeError):
        call.arguments["message"] = "changed"  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        result.success = False  # type: ignore[misc]


def test_reasoning_result_includes_optional_tool_invocation() -> None:
    call = ToolCall.create(name="echo", arguments={"message": "Hello Memovi"})
    tool_result = ToolResult.success_result(
        call_id=call.id,
        name="echo",
        output={"message": "Hello Memovi"},
        metadata={"argument_count": 1},
    )
    result = ReasoningResult.create(
        answer="Echoed Hello Memovi",
        provider="fake",
        execution_time=0.01,
        context=ReasoningContext.empty(ReasoningRequest.create(query="Echo hello")),
        tool_calls=(call,),
        tool_results=(tool_result,),
    )

    assert result.tool_calls == (call,)
    assert result.tool_results == (tool_result,)
    assert result.tool_results[0].output == {"message": "Hello Memovi"}
    with pytest.raises(FrozenInstanceError):
        result.tool_calls = ()  # type: ignore[misc]
