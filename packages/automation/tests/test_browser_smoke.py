"""Smoke tests for the production Browser Capability registration path."""

from pathlib import Path

from memovi_automation import (
    BROWSER_DOWNLOAD,
    BROWSER_READ,
    BROWSER_SEARCH,
    BrowserCapabilityConfig,
    CapabilityContext,
    CapabilityInvoker,
    CapabilityRegistry,
    CapabilityRequest,
    register_browser_capability,
)
from memovi_automation.browser import CAPABILITY_ID, FetchResult
from memovi_automation.browser.config import BrowserCapabilityConfig as Config
from memovi_shared import WorkspaceId


class FakeBrowserProvider:
    def fetch(self, url, *, config: Config, timeout_seconds, cancellation=None, on_progress=None):
        return FetchResult(
            url=url,
            final_url=url,
            status_code=200,
            content_type="text/html",
            body=b"<html><head><title>Smoke</title></head><body>ok</body></html>",
        )

    def search(self, query, *, limit, config: Config, timeout_seconds, cancellation=None):
        raise AssertionError("search not used in smoke test")

    def download_bytes(
        self, url, *, config: Config, timeout_seconds, cancellation=None, on_progress=None
    ):
        raise AssertionError("download not used in smoke test")


def test_smoke_register_browser_capability(tmp_path: Path) -> None:
    root = tmp_path / "dl"
    root.mkdir()
    registry = CapabilityRegistry()
    register_browser_capability(
        registry,
        BrowserCapabilityConfig.from_roots([root]),
        provider=FakeBrowserProvider(),
    )
    assert registry.contains("browser")
    assert registry.ids == ("browser",)
    metadata = registry.metadata("browser")
    assert "browser.read" in metadata.permission_names()
    assert BROWSER_READ in registry.permissions("browser")
    assert BROWSER_SEARCH in registry.permissions("browser")
    assert BROWSER_DOWNLOAD in registry.permissions("browser")

    invoker = CapabilityInvoker(registry=registry)
    result = invoker.invoke(
        CapabilityRequest.create(
            capability_id=CAPABILITY_ID,
            arguments={"operation": "open_url", "url": "https://example.com/"},
        ),
        CapabilityContext.create(
            workspace_id=WorkspaceId.default(),
            granted_permissions=frozenset({BROWSER_READ, BROWSER_SEARCH, BROWSER_DOWNLOAD}),
            correlation_id="browser-smoke",
        ),
    )
    assert result.success is True
    assert result.capability_id == "browser"
    assert result.output["title"] == "Smoke"
