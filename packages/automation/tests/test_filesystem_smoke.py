"""Smoke tests for the production Filesystem Capability.

Checklist:
1. Register the Filesystem Capability
2. Read a known file through the Capability Registry
3. List a known directory through the Capability Registry
4. Reject path traversal
5. Return a structured error for a nonexistent file
"""

from pathlib import Path

import pytest
from memovi_automation import (
    FILESYSTEM_READ,
    CapabilityContext,
    CapabilityInvoker,
    CapabilityRegistry,
    CapabilityRequest,
    FilesystemCapabilityConfig,
    register_filesystem_capability,
)
from memovi_automation.filesystem import CAPABILITY_ID
from memovi_shared import WorkspaceId


@pytest.fixture
def smoke_root(tmp_path: Path) -> Path:
    root = tmp_path / "fs-smoke"
    root.mkdir()
    (root / "known.txt").write_text("hello from filesystem smoke", encoding="utf-8")
    docs = root / "known-dir"
    docs.mkdir()
    (docs / "one.md").write_text("one", encoding="utf-8")
    (docs / "two.md").write_text("two", encoding="utf-8")
    return root


def _compose(root: Path) -> tuple[CapabilityRegistry, CapabilityInvoker]:
    registry = CapabilityRegistry()
    register_filesystem_capability(
        registry,
        FilesystemCapabilityConfig.from_roots([root]),
    )
    return registry, CapabilityInvoker(registry=registry)


def _context() -> CapabilityContext:
    return CapabilityContext.create(
        workspace_id=WorkspaceId.default(),
        granted_permissions=frozenset({FILESYSTEM_READ}),
        correlation_id="filesystem-smoke",
    )


def _invoke(
    invoker: CapabilityInvoker,
    *,
    operation: str,
    path: str,
):
    return invoker.invoke(
        CapabilityRequest.create(
            capability_id=CAPABILITY_ID,
            arguments={"operation": operation, "path": path},
        ),
        _context(),
    )


def test_smoke_register_filesystem_capability(smoke_root: Path) -> None:
    registry, _invoker = _compose(smoke_root)

    assert registry.contains("filesystem")
    assert registry.ids == ("filesystem",)
    metadata = registry.metadata("filesystem")
    assert metadata.id == CAPABILITY_ID
    assert metadata.permissions == (FILESYSTEM_READ,)
    assert registry.permissions("filesystem") == (FILESYSTEM_READ,)


def test_smoke_read_known_file_through_registry(smoke_root: Path) -> None:
    registry, invoker = _compose(smoke_root)

    assert registry.get("filesystem").metadata().id == "filesystem"

    result = _invoke(invoker, operation="read_file", path="known.txt")

    assert result.success is True
    assert result.error is None
    assert result.capability_id == "filesystem"
    assert result.output is not None
    assert result.output["operation"] == "read_file"
    assert result.output["content"] == "hello from filesystem smoke"
    assert result.metadata["argument_count"] == 2


def test_smoke_list_known_directory_through_registry(smoke_root: Path) -> None:
    registry, invoker = _compose(smoke_root)

    assert registry.contains("filesystem")

    result = _invoke(invoker, operation="list_directory", path="known-dir")

    assert result.success is True
    assert result.error is None
    assert result.output is not None
    assert result.output["operation"] == "list_directory"
    assert result.output["entries"] == ["one.md", "two.md"]
    assert result.output["count"] == 2


def test_smoke_path_traversal_is_rejected(smoke_root: Path) -> None:
    _registry, invoker = _compose(smoke_root)

    result = _invoke(invoker, operation="read_file", path="../..")

    assert result.success is False
    assert result.output is None
    assert result.error is not None
    assert result.error.code == "invalid_path"
    assert "outside allowed roots" in result.error.message


def test_smoke_nonexistent_file_returns_structured_error(smoke_root: Path) -> None:
    _registry, invoker = _compose(smoke_root)

    result = _invoke(invoker, operation="read_file", path="does-not-exist.txt")

    assert result.success is False
    assert result.cancelled is False
    assert result.timed_out is False
    assert result.output is None
    assert result.error is not None
    assert result.error.code == "file_not_found"
    assert result.error.details["path"]
    assert "does-not-exist.txt" in str(result.error.details["path"])
