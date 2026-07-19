from dataclasses import FrozenInstanceError
from time import sleep

import pytest
from memovi_shared import WorkspaceId

from memovi_automation import (
    FILESYSTEM_READ,
    FILESYSTEM_WRITE,
    TERMINAL_EXECUTE,
    CancellationToken,
    CapabilityCancelledError,
    CapabilityContext,
    CapabilityError,
    CapabilityExecutionError,
    CapabilityExecutionPolicy,
    CapabilityInvoker,
    CapabilityMetadata,
    CapabilityParameter,
    CapabilityPermission,
    CapabilityRegistry,
    CapabilityRequest,
    CapabilityResult,
    InvalidCapabilityArgumentsError,
    InvalidCapabilityError,
    UnknownCapabilityError,
)


class _EchoCapability:
    """Test-only mock capability — not a product capability."""

    def metadata(self) -> CapabilityMetadata:
        return CapabilityMetadata(
            id="test.echo",
            description="Echoes a message for framework tests.",
            permissions=(FILESYSTEM_READ,),
            parameters=(
                CapabilityParameter(
                    name="message",
                    type="string",
                    description="Message to echo.",
                    required=True,
                ),
            ),
        )

    def execute(self, request: CapabilityRequest, context: CapabilityContext) -> object:
        context.check_cancelled()
        return {
            "message": str(request.arguments["message"]),
            "workspace_id": str(context.workspace_id),
        }


class _WriteCapability:
    def metadata(self) -> CapabilityMetadata:
        return CapabilityMetadata(
            id="test.write",
            description="Mock write capability for multi-capability tests.",
            permissions=(FILESYSTEM_WRITE,),
            parameters=(
                CapabilityParameter(
                    name="path",
                    type="string",
                    description="Target path.",
                ),
                CapabilityParameter(
                    name="content",
                    type="string",
                    description="Content to write.",
                ),
            ),
        )

    def execute(self, request: CapabilityRequest, context: CapabilityContext) -> object:
        return {
            "path": request.arguments["path"],
            "content": request.arguments["content"],
            "wrote": True,
        }


class _FailingCapability(_EchoCapability):
    def execute(self, request: CapabilityRequest, context: CapabilityContext) -> object:
        raise CapabilityExecutionError(
            "echo failed",
            code="echo_failed",
            details={"reason": "boom"},
        )


class _UnexpectedFailingCapability(_EchoCapability):
    def execute(self, request: CapabilityRequest, context: CapabilityContext) -> object:
        raise RuntimeError("unexpected")


class _SlowCapability(_EchoCapability):
    def execute(self, request: CapabilityRequest, context: CapabilityContext) -> object:
        sleep(0.2)
        return super().execute(request, context)


class _CooperativeCancelCapability(_EchoCapability):
    def execute(self, request: CapabilityRequest, context: CapabilityContext) -> object:
        for _ in range(50):
            context.check_cancelled()
            sleep(0.01)
        return super().execute(request, context)


def _context(
    *,
    cancellation: CancellationToken | None = None,
    granted: frozenset[CapabilityPermission] | None = None,
) -> CapabilityContext:
    return CapabilityContext.create(
        workspace_id=WorkspaceId.default(),
        cancellation=cancellation,
        granted_permissions=granted,
        correlation_id="test-correlation",
    )


def _registry_with(*capabilities: object) -> CapabilityRegistry:
    registry = CapabilityRegistry()
    for capability in capabilities:
        registry.register(capability)  # type: ignore[arg-type]
    return registry


def test_capability_registry_register_list_and_lookup() -> None:
    echo = _EchoCapability()
    write = _WriteCapability()
    registry = _registry_with(echo, write)

    assert {item.id for item in registry.list()} == {"test.echo", "test.write"}
    assert registry.get("test.echo") is echo
    assert registry.contains("test.write")
    assert registry.ids == ("test.echo", "test.write")
    assert registry.metadata("test.echo").description.startswith("Echoes")
    assert registry.permissions("test.write") == (FILESYSTEM_WRITE,)


def test_capability_registry_rejects_duplicate_and_unknown() -> None:
    registry = _registry_with(_EchoCapability())

    with pytest.raises(InvalidCapabilityError, match="already registered"):
        registry.register(_EchoCapability())
    with pytest.raises(UnknownCapabilityError, match="Unknown capability"):
        registry.get("missing")


def test_capability_permission_normalization_and_validation() -> None:
    permission = CapabilityPermission("Filesystem.Read")
    assert permission.name == "filesystem.read"
    assert str(TERMINAL_EXECUTE) == "terminal.execute"

    with pytest.raises(InvalidCapabilityError):
        CapabilityPermission("")
    with pytest.raises(InvalidCapabilityError):
        CapabilityPermission("filesystem..read")
    with pytest.raises(InvalidCapabilityError):
        CapabilityPermission("filesystem read")


def test_capability_metadata_requires_unique_permissions_and_parameters() -> None:
    with pytest.raises(InvalidCapabilityError, match="permission names must be unique"):
        CapabilityMetadata(
            id="dup.permissions",
            description="Invalid",
            permissions=(FILESYSTEM_READ, FILESYSTEM_READ),
        )
    with pytest.raises(InvalidCapabilityError, match="parameter names must be unique"):
        CapabilityMetadata(
            id="dup.parameters",
            description="Invalid",
            parameters=(
                CapabilityParameter(name="path", type="string", description="a"),
                CapabilityParameter(name="path", type="string", description="b"),
            ),
        )


def test_capability_invoker_success_contract() -> None:
    invoker = CapabilityInvoker(registry=_registry_with(_EchoCapability()))
    request = CapabilityRequest.create(
        capability_id="test.echo",
        arguments={"message": "Hello Memovi"},
    )

    result = invoker.invoke(request, _context())

    assert isinstance(result, CapabilityResult)
    assert result.success is True
    assert result.request_id == request.id
    assert result.capability_id == "test.echo"
    assert result.output == {
        "message": "Hello Memovi",
        "workspace_id": str(WorkspaceId.default()),
    }
    assert result.error is None
    assert result.cancelled is False
    assert result.timed_out is False
    assert result.duration >= 0.0
    assert result.metadata["argument_count"] == 1


def test_capability_invoker_returns_structured_error_for_unknown() -> None:
    invoker = CapabilityInvoker(registry=_registry_with(_EchoCapability()))

    result = invoker.invoke(
        CapabilityRequest.create(capability_id="missing", arguments={}),
        _context(),
    )

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "unknown_capability"
    assert result.error.details["capability_id"] == "missing"
    assert "Unknown capability" in result.error.message


def test_capability_invoker_rejects_invalid_arguments() -> None:
    invoker = CapabilityInvoker(registry=_registry_with(_EchoCapability()))

    with pytest.raises(InvalidCapabilityArgumentsError, match="Missing required"):
        invoker.invoke(
            CapabilityRequest.create(capability_id="test.echo", arguments={}),
            _context(),
        )
    with pytest.raises(InvalidCapabilityArgumentsError, match="Unknown arguments"):
        invoker.invoke(
            CapabilityRequest.create(
                capability_id="test.echo",
                arguments={"message": "x", "extra": 1},
            ),
            _context(),
        )
    with pytest.raises(InvalidCapabilityArgumentsError, match="must be of type string"):
        invoker.invoke(
            CapabilityRequest.create(
                capability_id="test.echo",
                arguments={"message": 123},
            ),
            _context(),
        )


def test_capability_invoker_maps_structured_execution_failure() -> None:
    invoker = CapabilityInvoker(registry=_registry_with(_FailingCapability()))

    result = invoker.invoke(
        CapabilityRequest.create(capability_id="test.echo", arguments={"message": "boom"}),
        _context(),
    )

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "echo_failed"
    assert result.error.message == "echo failed"
    assert result.error.details["reason"] == "boom"


def test_capability_invoker_maps_unexpected_exception() -> None:
    invoker = CapabilityInvoker(registry=_registry_with(_UnexpectedFailingCapability()))

    result = invoker.invoke(
        CapabilityRequest.create(capability_id="test.echo", arguments={"message": "boom"}),
        _context(),
    )

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "execution_failed"
    assert result.error.details["exception_type"] == "RuntimeError"


def test_capability_invoker_timeout_behavior() -> None:
    invoker = CapabilityInvoker(
        registry=_registry_with(_SlowCapability()),
        default_policy=CapabilityExecutionPolicy(timeout_seconds=0.05),
    )

    result = invoker.invoke(
        CapabilityRequest.create(capability_id="test.echo", arguments={"message": "slow"}),
        _context(),
    )

    assert result.success is False
    assert result.timed_out is True
    assert result.error is not None
    assert result.error.code == "timeout"


def test_capability_invoker_pre_cancelled() -> None:
    token = CancellationToken()
    token.cancel()
    invoker = CapabilityInvoker(registry=_registry_with(_EchoCapability()))

    result = invoker.invoke(
        CapabilityRequest.create(capability_id="test.echo", arguments={"message": "x"}),
        _context(cancellation=token),
    )

    assert result.success is False
    assert result.cancelled is True
    assert result.error is not None
    assert result.error.code == "cancelled"


def test_capability_invoker_cooperative_cancellation() -> None:
    token = CancellationToken()
    invoker = CapabilityInvoker(
        registry=_registry_with(_CooperativeCancelCapability()),
        default_policy=CapabilityExecutionPolicy(timeout_seconds=2.0),
    )

    def _cancel_soon() -> None:
        sleep(0.05)
        token.cancel()

    from threading import Thread

    Thread(target=_cancel_soon, daemon=True).start()
    result = invoker.invoke(
        CapabilityRequest.create(capability_id="test.echo", arguments={"message": "x"}),
        _context(cancellation=token),
    )

    assert result.success is False
    assert result.cancelled is True
    assert result.error is not None
    assert result.error.code == "cancelled"


def test_capability_context_permission_inspection() -> None:
    context = _context(granted=frozenset({FILESYSTEM_READ}))

    assert context.has_permission(FILESYSTEM_READ)
    assert not context.has_permission(FILESYSTEM_WRITE)
    assert context.correlation_id == "test-correlation"


def test_cancellation_token_raises() -> None:
    token = CancellationToken()
    token.raise_if_cancelled()
    token.cancel()
    with pytest.raises(CapabilityCancelledError):
        token.raise_if_cancelled()


def test_value_objects_are_immutable() -> None:
    metadata = CapabilityMetadata(
        id="test.echo",
        description="Echo",
        permissions=(FILESYSTEM_READ,),
        parameters=(CapabilityParameter(name="message", type="string", description="Text"),),
    )
    request = CapabilityRequest.create(capability_id="test.echo", arguments={"message": "hi"})
    result = CapabilityResult.success_result(
        request_id=request.id,
        capability_id="test.echo",
        output={"message": "hi"},
    )
    error = CapabilityError(code="x", message="y")

    with pytest.raises(FrozenInstanceError):
        metadata.id = "other"  # type: ignore[misc]
    with pytest.raises(TypeError):
        request.arguments["message"] = "changed"  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        result.success = False  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        error.code = "z"  # type: ignore[misc]


def test_execution_policy_validation() -> None:
    with pytest.raises(InvalidCapabilityError, match="positive"):
        CapabilityExecutionPolicy(timeout_seconds=0)


def test_integration_register_multiple_mock_capabilities_and_invoke() -> None:
    registry = CapabilityRegistry()
    registry.register(_EchoCapability())
    registry.register(_WriteCapability())
    invoker = CapabilityInvoker(registry=registry)
    context = _context(granted=frozenset({FILESYSTEM_READ, FILESYSTEM_WRITE}))

    echo_result = invoker.invoke(
        CapabilityRequest.create(
            capability_id="test.echo",
            arguments={"message": "one"},
            policy=CapabilityExecutionPolicy(timeout_seconds=5.0),
        ),
        context,
    )
    write_result = invoker.invoke(
        CapabilityRequest.create(
            capability_id="test.write",
            arguments={"path": "/tmp/a.txt", "content": "body"},
        ),
        context,
    )

    assert [item.id for item in registry.list()] == ["test.echo", "test.write"]
    assert registry.permissions("test.echo") == (FILESYSTEM_READ,)
    assert registry.permissions("test.write") == (FILESYSTEM_WRITE,)

    assert echo_result.success is True
    assert echo_result.output == {
        "message": "one",
        "workspace_id": str(WorkspaceId.default()),
    }
    assert write_result.success is True
    assert write_result.output == {
        "path": "/tmp/a.txt",
        "content": "body",
        "wrote": True,
    }
    assert echo_result.metadata["cancellable"] is True
    assert write_result.metadata["argument_count"] == 2
