"""Live verification: EchoTool through ToolRegistry and ToolExecutor."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "packages" / "intelligence" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def main() -> None:
    from memovi_intelligence.application.services import ToolExecutor, ToolRegistry
    from memovi_intelligence.domain.entities import (
        ReasoningContext,
        ReasoningRequest,
        ReasoningResult,
    )
    from memovi_intelligence.domain.value_objects import ToolCall
    from memovi_intelligence.infrastructure import EchoTool

    registry = ToolRegistry()
    tool = EchoTool()
    registry.register(tool)
    print("registered = True")
    print(f"resolved_by_name = {registry.resolve('echo') is tool}")
    print(f"discovered = {[definition.name for definition in registry.discover()]}")

    executor = ToolExecutor(registry=registry)
    call = ToolCall.create(
        name="echo",
        arguments={"message": "Hello Memovi"},
    )
    print(f"call_arguments = {dict(call.arguments)}")

    result = executor.execute(call)
    print(f"executed = {result.success}")
    print(f"output = {result.output}")
    print(f"duration = {result.duration}")
    print(f"metadata = {dict(result.metadata)}")

    request = ReasoningRequest.create(query="Say hello with a tool")
    context = ReasoningContext.empty(request)
    reasoning = ReasoningResult.create(
        answer="Tool echoed Hello Memovi",
        provider="fake",
        execution_time=result.duration,
        context=context,
        tool_calls=(call,),
        tool_results=(result,),
    )
    print(f"reasoning_tool_calls = {len(reasoning.tool_calls)}")
    print(f"reasoning_tool_results = {len(reasoning.tool_results)}")
    print(f"reasoning_tool_output = {reasoning.tool_results[0].output}")

    assert registry.resolve("echo") is tool
    assert result.success is True
    assert result.output == {"message": "Hello Memovi"}
    assert result.metadata["argument_count"] == 1
    assert reasoning.tool_calls[0].arguments["message"] == "Hello Memovi"
    assert reasoning.tool_results[0].output == {"message": "Hello Memovi"}
    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
