"""Capability Execution Engine integration for Browser Capability."""

from __future__ import annotations

from pathlib import Path

from memovi_automation.testing import make_auth_context
from memovi_automation import (
    BrowserCapabilityConfig,
    CapabilityExecutionEngine,
    CapabilityExecutionRequest,
    CapabilityExecutionStatus,
    CapabilityInvoker,
    CapabilityRegistry,
    InMemoryExecutionAuditStore,
    InMemoryPermissionPolicyStore,
    PermissionMode,
    register_browser_capability,
)
from memovi_automation.browser import FetchResult, ProviderSearchResults, SearchHit
from memovi_automation.browser.config import BrowserCapabilityConfig as Config
from memovi_shared import WorkspaceId


class FakeBrowserProvider:
    def __init__(self) -> None:
        self.pages: dict[str, FetchResult] = {}
        self.downloads: dict[str, FetchResult] = {}
        self.search_results = ProviderSearchResults(
            query="q",
            results=(SearchHit(title="T", url="https://example.com/t", snippet="s"),),
        )

    def fetch(self, url, *, config: Config, timeout_seconds, cancellation=None, on_progress=None):
        return self.pages[url]

    def search(self, query, *, limit, config: Config, timeout_seconds, cancellation=None):
        return ProviderSearchResults(query=query, results=self.search_results.results[:limit])

    def download_bytes(
        self, url, *, config: Config, timeout_seconds, cancellation=None, on_progress=None
    ):
        return self.downloads[url]


def _engine(root: Path, provider: FakeBrowserProvider, *, mode: PermissionMode):
    registry = CapabilityRegistry()
    register_browser_capability(
        registry,
        BrowserCapabilityConfig.from_roots([root]),
        provider=provider,
    )
    policies = InMemoryPermissionPolicyStore(default_mode=mode)
    policies.set("browser", mode, workspace_id=WorkspaceId.default())
    return CapabilityExecutionEngine(
        registry=registry,
        invoker=CapabilityInvoker(registry=registry),
        permission_policies=policies,
        audit_store=InMemoryExecutionAuditStore(),
        default_permission_mode=mode,
    )


def test_always_allow_executes_browser_through_engine(tmp_path: Path) -> None:
    root = tmp_path / "dl"
    root.mkdir()
    provider = FakeBrowserProvider()
    url = "https://example.com/"
    provider.pages[url] = FetchResult(
        url=url,
        final_url=url,
        status_code=200,
        content_type="text/html",
        body=b"<html><head><title>Hi</title></head><body>Hi</body></html>",
    )
    engine = _engine(root, provider, mode=PermissionMode.ALWAYS_ALLOW)
    result = engine.submit(
        CapabilityExecutionRequest.create(
            capability_id="browser",
            workspace_id=WorkspaceId.default(),
            arguments={"operation": "open_url", "url": url},
            source="test",
        ), make_auth_context())
    assert result.status is CapabilityExecutionStatus.COMPLETED
    assert result.output["title"] == "Hi"
    audit = engine.list_audit(workspace_id=WorkspaceId.default())
    completed = [e for e in audit if e.status is CapabilityExecutionStatus.COMPLETED][-1]
    assert completed.arguments["operation"] == "open_url"
    assert completed.arguments["url"] == url
    assert completed.result_summary.get("url") == url


def test_ask_every_time_requires_approval_for_download(tmp_path: Path) -> None:
    root = tmp_path / "dl"
    root.mkdir()
    provider = FakeBrowserProvider()
    url = "https://example.com/a.bin"
    provider.downloads[url] = FetchResult(
        url=url,
        final_url=url,
        status_code=200,
        content_type="application/octet-stream",
        body=b"payload",
    )
    engine = _engine(root, provider, mode=PermissionMode.ASK_EVERY_TIME)
    pending = engine.submit(
        CapabilityExecutionRequest.create(
            capability_id="browser",
            workspace_id=WorkspaceId.default(),
            arguments={
                "operation": "download_file",
                "url": url,
                "destination": "a.bin",
            },
        ), make_auth_context())
    assert pending.status is CapabilityExecutionStatus.PENDING_APPROVAL
    assert pending.metadata["operation_summary"]["operation"] == "download_file"

    completed = engine.approve(pending.execution_id, workspace_id=WorkspaceId.default(), context=make_auth_context())
    assert completed.status is CapabilityExecutionStatus.COMPLETED
    assert Path(completed.output["destination"]).read_bytes() == b"payload"


def test_deny_blocks_browser(tmp_path: Path) -> None:
    root = tmp_path / "dl"
    root.mkdir()
    engine = _engine(root, FakeBrowserProvider(), mode=PermissionMode.DENY)
    result = engine.submit(
        CapabilityExecutionRequest.create(
            capability_id="browser",
            workspace_id=WorkspaceId.default(),
            arguments={"operation": "search_web", "query": "x"},
        ), make_auth_context())
    assert result.status is CapabilityExecutionStatus.FAILED
    assert result.error is not None
    assert result.error.code == "permission_denied"


def test_audit_redacts_sensitive_url_query_params(tmp_path: Path) -> None:
    root = tmp_path / "dl"
    root.mkdir()
    provider = FakeBrowserProvider()
    raw_url = "https://example.com/page?token=super-secret&q=ok"
    # Provider keys on validated/normalized URL from capability.
    normalized = "https://example.com/page?token=super-secret&q=ok"
    provider.pages[normalized] = FetchResult(
        url=normalized,
        final_url=normalized,
        status_code=200,
        content_type="text/html",
        body=b"<html><head><title>X</title></head><body>x</body></html>",
    )
    engine = _engine(root, provider, mode=PermissionMode.ALWAYS_ALLOW)
    result = engine.submit(
        CapabilityExecutionRequest.create(
            capability_id="browser",
            workspace_id=WorkspaceId.default(),
            arguments={"operation": "open_url", "url": raw_url},
        ), make_auth_context())
    assert result.status is CapabilityExecutionStatus.COMPLETED
    audit = engine.list_audit(workspace_id=WorkspaceId.default())
    completed = [e for e in audit if e.status is CapabilityExecutionStatus.COMPLETED][-1]
    assert "super-secret" not in completed.arguments["url"]
    assert "REDACTED" in completed.arguments["url"]
    assert "q=ok" in completed.arguments["url"]
