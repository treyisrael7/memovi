"""Unit tests for Browser Capability with a fake provider (no network)."""

from __future__ import annotations

from pathlib import Path

import pytest
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
from memovi_automation.browser import (
    CAPABILITY_ID,
    INVALID_URL,
    FetchResult,
    ProviderSearchResults,
    SearchHit,
)
from memovi_automation.browser.config import BrowserCapabilityConfig as Config
from memovi_shared import WorkspaceId


class FakeBrowserProvider:
    def __init__(self) -> None:
        self.pages: dict[str, FetchResult] = {}
        self.search_results: ProviderSearchResults | None = None
        self.downloads: dict[str, FetchResult] = {}

    def fetch(
        self,
        url: str,
        *,
        config: Config,
        timeout_seconds: float,
        cancellation=None,
        on_progress=None,
    ) -> FetchResult:
        if on_progress is not None:
            on_progress({"phase": "navigate", "url": url, "bytes_received": 0, "progress": 0.0})
        if url not in self.pages:
            raise AssertionError(f"Unexpected fetch URL: {url}")
        result = self.pages[url]
        if on_progress is not None:
            on_progress(
                {
                    "phase": "navigate",
                    "url": url,
                    "bytes_received": len(result.body),
                    "progress": 1.0,
                }
            )
        return result

    def search(
        self,
        query: str,
        *,
        limit: int,
        config: Config,
        timeout_seconds: float,
        cancellation=None,
    ) -> ProviderSearchResults:
        assert self.search_results is not None
        return ProviderSearchResults(
            query=query,
            results=self.search_results.results[:limit],
        )

    def download_bytes(
        self,
        url: str,
        *,
        config: Config,
        timeout_seconds: float,
        cancellation=None,
        on_progress=None,
    ) -> FetchResult:
        if on_progress is not None:
            on_progress({"phase": "download", "url": url, "bytes_received": 0, "progress": 0.0})
        if url not in self.downloads:
            raise AssertionError(f"Unexpected download URL: {url}")
        result = self.downloads[url]
        if on_progress is not None:
            on_progress(
                {
                    "phase": "download",
                    "url": url,
                    "bytes_received": len(result.body),
                    "bytes_total": len(result.body),
                    "progress": 1.0,
                }
            )
        return result


@pytest.fixture
def sandbox(tmp_path: Path) -> Path:
    root = tmp_path / "downloads"
    root.mkdir()
    return root


def _stack(root: Path, provider: FakeBrowserProvider):
    registry = CapabilityRegistry()
    capability = register_browser_capability(
        registry,
        BrowserCapabilityConfig.from_roots([root]),
        provider=provider,
    )
    return registry, CapabilityInvoker(registry=registry), capability, provider


def _context(*, granted=None) -> CapabilityContext:
    perms = granted or frozenset({BROWSER_READ, BROWSER_SEARCH, BROWSER_DOWNLOAD})
    return CapabilityContext.create(
        workspace_id=WorkspaceId.default(),
        granted_permissions=perms,
        correlation_id="browser-test",
    )


def _invoke(invoker: CapabilityInvoker, *, arguments: dict, granted=None):
    return invoker.invoke(
        CapabilityRequest.create(capability_id=CAPABILITY_ID, arguments=arguments),
        _context(granted=granted),
    )


def _html_page(url: str, *, title: str, body: str, final_url: str | None = None) -> FetchResult:
    html = (
        f"<html><head><title>{title}</title>"
        f"<meta name='description' content='demo'></head>"
        f"<body>{body}</body></html>"
    )
    return FetchResult(
        url=url,
        final_url=final_url or url,
        status_code=200,
        content_type="text/html",
        body=html.encode("utf-8"),
        redirected=bool(final_url and final_url != url),
        redirect_count=1 if final_url and final_url != url else 0,
    )


def test_browser_capability_is_discoverable(sandbox: Path) -> None:
    registry, _invoker, capability, _provider = _stack(sandbox, FakeBrowserProvider())
    assert registry.contains("browser")
    metadata = registry.metadata("browser")
    assert metadata.id == CAPABILITY_ID
    assert "browser.read" in metadata.permission_names()
    assert "browser.search" in metadata.permission_names()
    assert "browser.download" in metadata.permission_names()
    assert registry.get("browser") is capability


def test_open_and_read_page(sandbox: Path) -> None:
    provider = FakeBrowserProvider()
    url = "https://example.com/docs"
    provider.pages[url] = _html_page(
        url,
        title="Docs",
        body="<p>Hello world</p><a href='/more'>More</a>",
        final_url="https://example.com/docs/",
    )
    _registry, invoker, _cap, _p = _stack(sandbox, provider)

    opened = _invoke(invoker, arguments={"operation": "open_url", "url": url})
    assert opened.success is True
    assert opened.output["operation"] == "open_url"
    assert opened.output["title"] == "Docs"
    assert opened.output["redirected"] is True

    read = _invoke(invoker, arguments={"operation": "read_page", "url": url})
    assert read.success is True
    assert "Hello world" in read.output["content"]
    assert any(link["href"].endswith("/more") for link in read.output["links"])


def test_extract_operations(sandbox: Path) -> None:
    provider = FakeBrowserProvider()
    url = "https://example.com/"
    provider.pages[url] = _html_page(
        url,
        title="Home",
        body="<p>Body</p><a href='https://example.com/a'>A</a>",
    )
    _registry, invoker, _cap, _p = _stack(sandbox, provider)

    content = _invoke(invoker, arguments={"operation": "extract_content", "url": url})
    assert content.success is True
    assert "Body" in content.output["content"]

    links = _invoke(invoker, arguments={"operation": "extract_links", "url": url})
    assert links.success is True
    assert links.output["links"][0]["href"] == "https://example.com/a"

    meta = _invoke(invoker, arguments={"operation": "extract_metadata", "url": url})
    assert meta.success is True
    assert meta.output["page_metadata"]["description"] == "demo"


def test_search_web(sandbox: Path) -> None:
    provider = FakeBrowserProvider()
    provider.search_results = ProviderSearchResults(
        query="memovi",
        results=(
            SearchHit(title="Memovi", url="https://example.com/m", snippet="Knowledge OS"),
            SearchHit(title="Docs", url="https://example.com/d", snippet="Docs"),
        ),
    )
    _registry, invoker, _cap, _p = _stack(sandbox, provider)
    result = _invoke(
        invoker,
        arguments={"operation": "search_web", "query": "memovi", "limit": 1},
    )
    assert result.success is True
    assert result.output["result_count"] == 1
    assert result.output["results"][0]["title"] == "Memovi"


def test_download_writes_under_filesystem_root(sandbox: Path) -> None:
    provider = FakeBrowserProvider()
    url = "https://example.com/file.bin"
    provider.downloads[url] = FetchResult(
        url=url,
        final_url=url,
        status_code=200,
        content_type="application/octet-stream",
        body=b"download-bytes",
    )
    _registry, invoker, _cap, _p = _stack(sandbox, provider)
    result = _invoke(
        invoker,
        arguments={
            "operation": "download_file",
            "url": url,
            "destination": "reports/file.bin",
        },
    )
    assert result.success is True
    dest = Path(result.output["destination"])
    assert dest.exists()
    assert dest.read_bytes() == b"download-bytes"
    assert result.output["sha256"]
    assert result.output["metadata"]["filesystem_integrated"] is True
    assert dest.is_relative_to(sandbox.resolve())


def test_invalid_url_rejected(sandbox: Path) -> None:
    _registry, invoker, _cap, _p = _stack(sandbox, FakeBrowserProvider())
    result = _invoke(
        invoker,
        arguments={"operation": "open_url", "url": "file:///etc/passwd"},
    )
    assert result.success is False
    assert result.error is not None
    assert result.error.code == INVALID_URL


def test_permission_denied_without_browser_read(sandbox: Path) -> None:
    provider = FakeBrowserProvider()
    url = "https://example.com/"
    provider.pages[url] = _html_page(url, title="X", body="<p>x</p>")
    _registry, invoker, _cap, _p = _stack(sandbox, provider)
    result = _invoke(
        invoker,
        arguments={"operation": "read_page", "url": url},
        granted=frozenset({BROWSER_SEARCH}),
    )
    assert result.success is False
    assert result.error is not None
    assert result.error.code == "permission_denied"
    assert result.error.details["permission"] == "browser.read"


def test_download_requires_browser_download_permission(sandbox: Path) -> None:
    provider = FakeBrowserProvider()
    url = "https://example.com/a.bin"
    provider.downloads[url] = FetchResult(
        url=url,
        final_url=url,
        status_code=200,
        content_type="application/octet-stream",
        body=b"x",
    )
    _registry, invoker, _cap, _p = _stack(sandbox, provider)
    result = _invoke(
        invoker,
        arguments={
            "operation": "download_file",
            "url": url,
            "destination": "a.bin",
        },
        granted=frozenset({BROWSER_READ}),
    )
    assert result.success is False
    assert result.error is not None
    assert result.error.details["permission"] == "browser.download"


def test_download_outside_roots_rejected(sandbox: Path) -> None:
    provider = FakeBrowserProvider()
    url = "https://example.com/a.bin"
    provider.downloads[url] = FetchResult(
        url=url,
        final_url=url,
        status_code=200,
        content_type="application/octet-stream",
        body=b"x",
    )
    _registry, invoker, _cap, _p = _stack(sandbox, provider)

    # Portable absolute path outside the download root.
    result = _invoke(
        invoker,
        arguments={
            "operation": "download_file",
            "url": url,
            "destination": str(sandbox.parent / "evil.bin"),
        },
    )
    assert result.success is False
    assert result.error is not None
    assert result.error.code == "invalid_destination"

    # Windows drive-letter absolute form must never be treated as a relative
    # path under the sandbox on POSIX runners.
    windows_style = _invoke(
        invoker,
        arguments={
            "operation": "download_file",
            "url": url,
            "destination": "C:/Windows/evil.bin",
        },
    )
    assert windows_style.success is False
    assert windows_style.error is not None
    assert windows_style.error.code == "invalid_destination"
