from pathlib import Path

import pytest
from memovi_automation import (
    FILESYSTEM_READ,
    FILESYSTEM_WRITE,
    CapabilityContext,
    CapabilityInvoker,
    CapabilityRegistry,
    CapabilityRequest,
    FilesystemCapability,
    FilesystemCapabilityConfig,
    register_filesystem_capability,
)
from memovi_automation.filesystem import CAPABILITY_ID, PERMISSION_DENIED
from memovi_shared import WorkspaceId


@pytest.fixture
def sandbox(tmp_path: Path) -> Path:
    root = tmp_path / "allowed"
    root.mkdir()
    (root / "notes.txt").write_text("# Title\n\nBody", encoding="utf-8")
    nested = root / "docs"
    nested.mkdir()
    (nested / "a.md").write_text("alpha", encoding="utf-8")
    (nested / "b.md").write_text("beta", encoding="utf-8")
    (root / "binary.bin").write_bytes(b"\x00\x01\x02\xff")
    return root


@pytest.fixture
def outside(tmp_path: Path) -> Path:
    path = tmp_path / "outside"
    path.mkdir()
    (path / "secret.txt").write_text("secret", encoding="utf-8")
    return path


def _stack(root: Path) -> tuple[CapabilityRegistry, CapabilityInvoker, FilesystemCapability]:
    registry = CapabilityRegistry()
    config = FilesystemCapabilityConfig.from_roots([root], max_read_bytes=1024)
    capability = register_filesystem_capability(registry, config)
    return registry, CapabilityInvoker(registry=registry), capability


def _context(*, granted: frozenset = frozenset({FILESYSTEM_READ})) -> CapabilityContext:
    return CapabilityContext.create(
        workspace_id=WorkspaceId.default(),
        granted_permissions=granted,
        correlation_id="filesystem-test",
    )


def _invoke(
    invoker: CapabilityInvoker,
    *,
    operation: str,
    path: str,
    encoding: str | None = None,
    granted: frozenset = frozenset({FILESYSTEM_READ}),
):
    arguments: dict[str, object] = {"operation": operation, "path": path}
    if encoding is not None:
        arguments["encoding"] = encoding
    return invoker.invoke(
        CapabilityRequest.create(capability_id=CAPABILITY_ID, arguments=arguments),
        _context(granted=granted),
    )


def test_filesystem_capability_is_discoverable_through_registry(sandbox: Path) -> None:
    registry, _invoker, capability = _stack(sandbox)

    assert registry.contains(CAPABILITY_ID)
    metadata = registry.metadata(CAPABILITY_ID)
    assert metadata.id == "filesystem"
    assert metadata.permissions == (FILESYSTEM_READ,)
    assert {parameter.name for parameter in metadata.parameters} == {
        "operation",
        "path",
        "encoding",
    }
    assert registry.get(CAPABILITY_ID) is capability


def test_read_file_list_directory_read_directory_exists_and_metadata(sandbox: Path) -> None:
    _registry, invoker, _capability = _stack(sandbox)

    read_file = _invoke(invoker, operation="read_file", path="notes.txt")
    assert read_file.success is True
    assert read_file.output is not None
    assert read_file.output["content"] == "# Title\n\nBody"
    assert read_file.output["encoding"] == "utf-8"
    assert read_file.metadata["argument_count"] == 2

    listed = _invoke(invoker, operation="list_directory", path="docs")
    assert listed.success is True
    assert listed.output is not None
    assert listed.output["entries"] == ["a.md", "b.md"]
    assert listed.output["count"] == 2

    directory = _invoke(invoker, operation="read_directory", path="docs")
    assert directory.success is True
    assert directory.output is not None
    assert directory.output["count"] == 2
    names = [entry["name"] for entry in directory.output["entries"]]
    assert names == ["a.md", "b.md"]
    assert all(entry["is_file"] for entry in directory.output["entries"])

    exists = _invoke(invoker, operation="exists", path="notes.txt")
    assert exists.success is True
    assert exists.output == {
        "operation": "exists",
        "path": str((sandbox / "notes.txt").resolve()),
        "exists": True,
        "is_file": True,
        "is_directory": False,
    }

    missing = _invoke(invoker, operation="exists", path="missing.txt")
    assert missing.success is True
    assert missing.output is not None
    assert missing.output["exists"] is False

    metadata = _invoke(invoker, operation="get_metadata", path="notes.txt")
    assert metadata.success is True
    assert metadata.output is not None
    assert metadata.output["is_file"] is True
    assert metadata.output["size_bytes"] == (sandbox / "notes.txt").stat().st_size
    assert "modified_at" in metadata.output


def test_path_traversal_and_outside_root_rejected(sandbox: Path, outside: Path) -> None:
    _registry, invoker, _capability = _stack(sandbox)

    traversal = _invoke(invoker, operation="read_file", path="../outside/secret.txt")
    assert traversal.success is False
    assert traversal.error is not None
    assert traversal.error.code == "invalid_path"

    absolute_outside = _invoke(
        invoker,
        operation="read_file",
        path=str(outside / "secret.txt"),
    )
    assert absolute_outside.success is False
    assert absolute_outside.error is not None
    assert absolute_outside.error.code == "invalid_path"


def test_permission_denied_without_filesystem_read(sandbox: Path) -> None:
    _registry, invoker, _capability = _stack(sandbox)

    result = _invoke(
        invoker,
        operation="read_file",
        path="notes.txt",
        granted=frozenset(),
    )

    assert result.success is False
    assert result.error is not None
    assert result.error.code == PERMISSION_DENIED
    assert result.error.details["permission"] == "filesystem.read"


def test_file_not_found_and_type_errors(sandbox: Path) -> None:
    _registry, invoker, _capability = _stack(sandbox)

    missing = _invoke(invoker, operation="read_file", path="nope.txt")
    assert missing.success is False
    assert missing.error is not None
    assert missing.error.code == "file_not_found"

    not_file = _invoke(invoker, operation="read_file", path="docs")
    assert not_file.success is False
    assert not_file.error is not None
    assert not_file.error.code == "not_a_file"

    not_dir = _invoke(invoker, operation="list_directory", path="notes.txt")
    assert not_dir.success is False
    assert not_dir.error is not None
    assert not_dir.error.code == "not_a_directory"


def test_unsupported_operation_and_future_write_reserved(sandbox: Path) -> None:
    _registry, invoker, _capability = _stack(sandbox)

    unknown = _invoke(invoker, operation="watch", path="notes.txt")
    assert unknown.success is False
    assert unknown.error is not None
    assert unknown.error.code == "unsupported_operation"

    write_without_perm = _invoke(
        invoker,
        operation="write_file",
        path="notes.txt",
        granted=frozenset({FILESYSTEM_READ}),
    )
    assert write_without_perm.success is False
    assert write_without_perm.error is not None
    assert write_without_perm.error.code == PERMISSION_DENIED
    assert write_without_perm.error.details["permission"] == "filesystem.write"

    write_with_perm = _invoke(
        invoker,
        operation="write_file",
        path="notes.txt",
        granted=frozenset({FILESYSTEM_READ, FILESYSTEM_WRITE}),
    )
    assert write_with_perm.success is False
    assert write_with_perm.error is not None
    assert write_with_perm.error.code == "unsupported_operation"


def test_binary_and_oversized_files(sandbox: Path) -> None:
    _registry, invoker, _capability = _stack(sandbox)
    (sandbox / "large.txt").write_text("x" * 2048, encoding="utf-8")

    binary = _invoke(invoker, operation="read_file", path="binary.bin")
    assert binary.success is False
    assert binary.error is not None
    assert binary.error.code == "not_text_file"

    large = _invoke(invoker, operation="read_file", path="large.txt")
    assert large.success is False
    assert large.error is not None
    assert large.error.code == "file_too_large"


def test_absolute_path_within_root_allowed(sandbox: Path) -> None:
    _registry, invoker, _capability = _stack(sandbox)

    result = _invoke(
        invoker,
        operation="read_file",
        path=str(sandbox / "notes.txt"),
    )

    assert result.success is True
    assert result.output is not None
    assert result.output["content"] == "# Title\n\nBody"


def test_null_byte_path_rejected(sandbox: Path) -> None:
    _registry, invoker, _capability = _stack(sandbox)

    result = _invoke(invoker, operation="exists", path="notes\x00.txt")
    assert result.success is False
    assert result.error is not None
    assert result.error.code == "invalid_path"


def test_config_rejects_missing_or_non_directory_roots(tmp_path: Path) -> None:
    with pytest.raises(Exception, match="does not exist"):
        FilesystemCapabilityConfig.from_roots([tmp_path / "missing"])

    file_root = tmp_path / "file.txt"
    file_root.write_text("x", encoding="utf-8")
    with pytest.raises(Exception, match="must be a directory"):
        FilesystemCapabilityConfig.from_roots([file_root])


def test_executes_only_through_registry_invoker(sandbox: Path) -> None:
    registry, invoker, capability = _stack(sandbox)
    context = _context()

    # Direct execute still works for the capability object, but the supported
    # platform path is registry discovery + invoker.
    direct = capability.execute(
        CapabilityRequest.create(
            capability_id=CAPABILITY_ID,
            arguments={"operation": "exists", "path": "notes.txt"},
        ),
        context,
    )
    via_registry = invoker.invoke(
        CapabilityRequest.create(
            capability_id=CAPABILITY_ID,
            arguments={"operation": "exists", "path": "notes.txt"},
        ),
        context,
    )

    assert registry.list()[0].id == CAPABILITY_ID
    assert via_registry.success is True
    assert via_registry.output == direct
