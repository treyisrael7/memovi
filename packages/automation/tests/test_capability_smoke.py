"""Smoke tests for the Capability Framework composition path.

These are test-only mocks — not product filesystem/terminal capabilities.
"""

from memovi_automation import (
    FILESYSTEM_READ,
    TERMINAL_EXECUTE,
    CapabilityContext,
    CapabilityInvoker,
    CapabilityMetadata,
    CapabilityParameter,
    CapabilityRegistry,
    CapabilityRequest,
)
from memovi_shared import WorkspaceId


class MockFilesystem:
    """Smoke-test mock for a future filesystem capability."""

    def metadata(self) -> CapabilityMetadata:
        return CapabilityMetadata(
            id="mock.filesystem",
            description="Mock filesystem capability for smoke tests.",
            permissions=(FILESYSTEM_READ,),
            parameters=(
                CapabilityParameter(
                    name="path",
                    type="string",
                    description="Path to read.",
                ),
            ),
        )

    def execute(self, request: CapabilityRequest, context: CapabilityContext) -> object:
        context.check_cancelled()
        return {
            "capability": "mock.filesystem",
            "path": str(request.arguments["path"]),
            "content": "mock-file-contents",
            "workspace_id": str(context.workspace_id),
        }


class MockTerminal:
    """Smoke-test mock for a future terminal capability."""

    def metadata(self) -> CapabilityMetadata:
        return CapabilityMetadata(
            id="mock.terminal",
            description="Mock terminal capability for smoke tests.",
            permissions=(TERMINAL_EXECUTE,),
            parameters=(
                CapabilityParameter(
                    name="command",
                    type="string",
                    description="Command to execute.",
                ),
            ),
        )

    def execute(self, request: CapabilityRequest, context: CapabilityContext) -> object:
        context.check_cancelled()
        return {
            "capability": "mock.terminal",
            "command": str(request.arguments["command"]),
            "exit_code": 0,
            "stdout": "ok",
            "workspace_id": str(context.workspace_id),
        }


def _compose_smoke_stack() -> tuple[CapabilityRegistry, CapabilityInvoker]:
    """Deterministic composition root for smoke capabilities.

    Mirrors application restart: a new registry is constructed and the same
    capabilities are registered in the same order via dependency injection.
    """
    registry = CapabilityRegistry()
    registry.register(MockFilesystem())
    registry.register(MockTerminal())
    return registry, CapabilityInvoker(registry=registry)


def _context() -> CapabilityContext:
    return CapabilityContext.create(
        workspace_id=WorkspaceId.default(),
        correlation_id="capability-smoke",
    )


def test_smoke_register_two_mock_capabilities_appear_in_registry() -> None:
    registry, _invoker = _compose_smoke_stack()

    discovered = {item.id: item for item in registry.list()}

    assert set(discovered) == {"mock.filesystem", "mock.terminal"}
    assert registry.contains("mock.filesystem")
    assert registry.contains("mock.terminal")
    assert discovered["mock.filesystem"].permissions == (FILESYSTEM_READ,)
    assert discovered["mock.terminal"].permissions == (TERMINAL_EXECUTE,)
    assert registry.ids == ("mock.filesystem", "mock.terminal")


def test_smoke_execute_each_registered_capability_successfully() -> None:
    registry, invoker = _compose_smoke_stack()
    context = _context()

    filesystem_result = invoker.invoke(
        CapabilityRequest.create(
            capability_id="mock.filesystem",
            arguments={"path": "/tmp/notes.txt"},
        ),
        context,
    )
    terminal_result = invoker.invoke(
        CapabilityRequest.create(
            capability_id="mock.terminal",
            arguments={"command": "echo hello"},
        ),
        context,
    )

    assert registry.get("mock.filesystem").metadata().id == "mock.filesystem"
    assert registry.get("mock.terminal").metadata().id == "mock.terminal"

    assert filesystem_result.success is True
    assert filesystem_result.error is None
    assert filesystem_result.output == {
        "capability": "mock.filesystem",
        "path": "/tmp/notes.txt",
        "content": "mock-file-contents",
        "workspace_id": str(WorkspaceId.default()),
    }

    assert terminal_result.success is True
    assert terminal_result.error is None
    assert terminal_result.output == {
        "capability": "mock.terminal",
        "command": "echo hello",
        "exit_code": 0,
        "stdout": "ok",
        "workspace_id": str(WorkspaceId.default()),
    }


def test_smoke_nonexistent_capability_returns_structured_error() -> None:
    _registry, invoker = _compose_smoke_stack()

    result = invoker.invoke(
        CapabilityRequest.create(
            capability_id="mock.nonexistent",
            arguments={},
        ),
        _context(),
    )

    assert result.success is False
    assert result.cancelled is False
    assert result.timed_out is False
    assert result.output is None
    assert result.error is not None
    assert result.error.code == "unknown_capability"
    assert result.error.details["capability_id"] == "mock.nonexistent"
    assert "mock.nonexistent" in result.error.message


def test_smoke_capability_registration_is_deterministic_across_restart() -> None:
    first_registry, first_invoker = _compose_smoke_stack()
    first_ids = first_registry.ids
    first_metadata = tuple(
        (item.id, item.description, item.permission_names()) for item in first_registry.list()
    )
    first_filesystem = first_invoker.invoke(
        CapabilityRequest.create(
            capability_id="mock.filesystem",
            arguments={"path": "a.txt"},
        ),
        _context(),
    )

    # Simulate application restart: discard prior stack and compose again.
    del first_registry
    del first_invoker

    second_registry, second_invoker = _compose_smoke_stack()
    second_ids = second_registry.ids
    second_metadata = tuple(
        (item.id, item.description, item.permission_names()) for item in second_registry.list()
    )
    second_filesystem = second_invoker.invoke(
        CapabilityRequest.create(
            capability_id="mock.filesystem",
            arguments={"path": "a.txt"},
        ),
        _context(),
    )

    assert first_ids == second_ids == ("mock.filesystem", "mock.terminal")
    assert first_metadata == second_metadata
    assert first_filesystem.success is True
    assert second_filesystem.success is True
    assert first_filesystem.output == second_filesystem.output
