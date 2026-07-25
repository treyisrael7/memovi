"""Milestone 25 acceptance checklist for Browser Capability.

1. Open a valid webpage and verify the page title and metadata are returned.
2. Extract readable content from a webpage and verify structured content is produced.
3. Perform a web search and verify structured search results are returned.
4. Download a test file with user approval and verify it is saved to the selected directory.
5. Cancel an in-progress download and verify cleanup is performed correctly.
6. Attempt to open an invalid URL and verify a normalized error is returned.
7. Deny browser permission and verify execution is blocked.
8. Verify download operations integrate correctly with the Filesystem Capability.
9. Verify every browser operation creates an audit entry.
10. Run the full regression suite (executed separately in CI / local verification).
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

from memovi_automation import (
    BrowserCapabilityConfig,
    CapabilityExecutionEngine,
    CapabilityExecutionPolicy,
    CapabilityExecutionRequest,
    CapabilityExecutionStatus,
    CapabilityInvoker,
    CapabilityRegistry,
    FilesystemCapabilityConfig,
    InMemoryExecutionAuditStore,
    InMemoryPermissionPolicyStore,
    PermissionMode,
    register_browser_capability,
    register_filesystem_capability,
)
from memovi_automation.browser import (
    FetchResult,
    INVALID_URL,
    ProviderSearchResults,
    SearchHit,
)
from memovi_automation.browser.config import BrowserCapabilityConfig as Config
from memovi_automation.domain.exceptions import CapabilityCancelledError
from memovi_shared import WorkspaceId

SAMPLE_HTML = """<!DOCTYPE html>
<html>
<head>
  <title>Acceptance Page</title>
  <meta name="description" content="Browser acceptance">
  <meta name="author" content="Memovi">
</head>
<body>
  <h1>Welcome</h1>
  <p>Readable content for Memovi.</p>
  <a href="/next">Next</a>
</body>
</html>
"""


class FakeBrowserProvider:
    def __init__(self, *, slow_download_seconds: float = 0.0) -> None:
        self.pages: dict[str, FetchResult] = {}
        self.downloads: dict[str, FetchResult] = {}
        self.slow_download_seconds = slow_download_seconds
        self.download_started = threading.Event()
        self.search_results = ProviderSearchResults(
            query="memovi browser",
            results=(
                SearchHit(
                    title="Memovi Browser",
                    url="https://example.com/browser",
                    snippet="Structured browser capability",
                ),
                SearchHit(
                    title="Capability Docs",
                    url="https://example.com/docs",
                    snippet="Architecture reference",
                ),
            ),
        )

    def fetch(self, url, *, config: Config, timeout_seconds, cancellation=None, on_progress=None):
        return self.pages[url]

    def search(self, query, *, limit, config: Config, timeout_seconds, cancellation=None):
        return ProviderSearchResults(query=query, results=self.search_results.results[:limit])

    def download_bytes(
        self, url, *, config: Config, timeout_seconds, cancellation=None, on_progress=None
    ):
        self.download_started.set()
        if on_progress is not None:
            on_progress(
                {
                    "phase": "download",
                    "url": url,
                    "bytes_received": 0,
                    "progress": 0.0,
                }
            )
        if self.slow_download_seconds > 0:
            deadline = time.time() + self.slow_download_seconds
            while time.time() < deadline:
                if cancellation is not None and cancellation.is_cancelled:
                    raise CapabilityCancelledError("Download cancelled.")
                time.sleep(0.05)
            if cancellation is not None:
                cancellation.raise_if_cancelled()
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


def _seed_page(provider: FakeBrowserProvider, url: str) -> None:
    provider.pages[url] = FetchResult(
        url=url,
        final_url=url,
        status_code=200,
        content_type="text/html; charset=utf-8",
        body=SAMPLE_HTML.encode("utf-8"),
    )


def _engine(
    root: Path,
    provider: FakeBrowserProvider,
    *,
    mode: PermissionMode,
    with_filesystem: bool = False,
) -> CapabilityExecutionEngine:
    registry = CapabilityRegistry()
    if with_filesystem:
        register_filesystem_capability(
            registry,
            FilesystemCapabilityConfig.from_roots([root]),
        )
    register_browser_capability(
        registry,
        BrowserCapabilityConfig.from_roots([root]),
        provider=provider,
    )
    policies = InMemoryPermissionPolicyStore(default_mode=mode)
    policies.set("browser", mode, workspace_id=WorkspaceId.default())
    if with_filesystem:
        policies.set("filesystem", PermissionMode.ALWAYS_ALLOW, workspace_id=WorkspaceId.default())
    return CapabilityExecutionEngine(
        registry=registry,
        invoker=CapabilityInvoker(registry=registry),
        permission_policies=policies,
        audit_store=InMemoryExecutionAuditStore(),
        default_permission_mode=mode,
    )


def _submit(
    engine: CapabilityExecutionEngine,
    arguments: dict[str, object],
    *,
    policy: CapabilityExecutionPolicy | None = None,
):
    return engine.submit(
        CapabilityExecutionRequest.create(
            capability_id="browser",
            workspace_id=WorkspaceId.default(),
            arguments=arguments,
            policy=policy,
            source="acceptance",
        )
    )


def test_1_open_webpage_returns_title_and_metadata(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    provider = FakeBrowserProvider()
    url = "https://example.com/start"
    _seed_page(provider, url)
    engine = _engine(root, provider, mode=PermissionMode.ALWAYS_ALLOW)

    result = _submit(engine, {"operation": "open_url", "url": url})
    assert result.status is CapabilityExecutionStatus.COMPLETED
    assert result.output is not None
    assert result.output["title"] == "Acceptance Page"
    assert result.output["page_metadata"]["description"] == "Browser acceptance"
    assert result.output["page_metadata"]["author"] == "Memovi"
    assert result.output["status_code"] == 200


def test_2_extract_readable_structured_content(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    provider = FakeBrowserProvider()
    url = "https://example.com/page"
    _seed_page(provider, url)
    engine = _engine(root, provider, mode=PermissionMode.ALWAYS_ALLOW)

    result = _submit(engine, {"operation": "extract_content", "url": url})
    assert result.status is CapabilityExecutionStatus.COMPLETED
    assert result.output["operation"] == "extract_content"
    assert result.output["title"] == "Acceptance Page"
    assert "Readable content for Memovi" in result.output["content"]
    assert isinstance(result.output["content"], str)
    assert result.output["success"] is True


def test_3_web_search_returns_structured_results(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    engine = _engine(root, FakeBrowserProvider(), mode=PermissionMode.ALWAYS_ALLOW)

    result = _submit(engine, {"operation": "search_web", "query": "memovi browser", "limit": 2})
    assert result.status is CapabilityExecutionStatus.COMPLETED
    assert result.output["operation"] == "search_web"
    assert result.output["query"] == "memovi browser"
    assert result.output["result_count"] == 2
    first = result.output["results"][0]
    assert first["title"]
    assert first["url"].startswith("https://")
    assert first["snippet"]


def test_4_download_with_approval_saves_to_selected_directory(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    selected = root / "downloads"
    selected.mkdir()
    provider = FakeBrowserProvider()
    url = "https://example.com/report.bin"
    provider.downloads[url] = FetchResult(
        url=url,
        final_url=url,
        status_code=200,
        content_type="application/octet-stream",
        body=b"approved-download-bytes",
    )
    engine = _engine(root, provider, mode=PermissionMode.ASK_EVERY_TIME)

    pending = _submit(
        engine,
        {
            "operation": "download_file",
            "url": url,
            "destination": "downloads/report.bin",
        },
    )
    assert pending.status is CapabilityExecutionStatus.PENDING_APPROVAL

    completed = engine.approve(pending.execution_id, workspace_id=WorkspaceId.default())
    assert completed.status is CapabilityExecutionStatus.COMPLETED
    dest = Path(completed.output["destination"])
    assert dest == (selected / "report.bin").resolve()
    assert dest.exists()
    assert dest.read_bytes() == b"approved-download-bytes"
    assert completed.output["sha256"]


def test_5_cancel_in_progress_download_cleans_up(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    provider = FakeBrowserProvider(slow_download_seconds=30.0)
    url = "https://example.com/large.bin"
    provider.downloads[url] = FetchResult(
        url=url,
        final_url=url,
        status_code=200,
        content_type="application/octet-stream",
        body=b"should-not-land",
    )
    engine = _engine(root, provider, mode=PermissionMode.ALWAYS_ALLOW)
    destination = "inbox/large.bin"
    staging = root / "inbox" / "large.bin.memovi-partial"
    final_path = root / "inbox" / "large.bin"

    request = CapabilityExecutionRequest.create(
        capability_id="browser",
        workspace_id=WorkspaceId.default(),
        arguments={
            "operation": "download_file",
            "url": url,
            "destination": destination,
        },
        policy=CapabilityExecutionPolicy(timeout_seconds=60.0, cancellable=True),
        source="acceptance",
    )
    holder: dict[str, object] = {}

    def _run() -> None:
        holder["result"] = engine.submit(request)

    worker = threading.Thread(target=_run, daemon=True)
    worker.start()

    assert provider.download_started.wait(timeout=5)
    # Staging marker should exist while download is in flight.
    deadline = time.time() + 5
    while time.time() < deadline and not staging.exists():
        time.sleep(0.05)
    assert staging.exists()

    cancelled = engine.cancel(request.id, workspace_id=WorkspaceId.default())
    assert cancelled.status is CapabilityExecutionStatus.CANCELLED
    worker.join(timeout=15)

    final = holder.get("result")
    assert final is not None
    assert final.status in {
        CapabilityExecutionStatus.CANCELLED,
        CapabilityExecutionStatus.FAILED,
    }
    assert not staging.exists(), "partial download staging file must be cleaned up"
    assert not final_path.exists(), "final download path must not remain after cancel"


def test_6_invalid_url_returns_normalized_error(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    engine = _engine(root, FakeBrowserProvider(), mode=PermissionMode.ALWAYS_ALLOW)

    result = _submit(engine, {"operation": "open_url", "url": "javascript:alert(1)"})
    assert result.status is CapabilityExecutionStatus.FAILED
    assert result.error is not None
    assert result.error.code == INVALID_URL
    assert "stack" not in (result.error.message or "").lower()
    assert "Traceback" not in (result.error.message or "")


def test_7_deny_browser_permission_blocks_execution(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    provider = FakeBrowserProvider()
    url = "https://example.com/page"
    _seed_page(provider, url)
    engine = _engine(root, provider, mode=PermissionMode.DENY)

    result = _submit(engine, {"operation": "open_url", "url": url})
    assert result.status is CapabilityExecutionStatus.FAILED
    assert result.error is not None
    assert result.error.code == "permission_denied"
    assert result.output is None


def test_8_download_integrates_with_filesystem_capability(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    provider = FakeBrowserProvider()
    url = "https://example.com/notes.txt"
    provider.downloads[url] = FetchResult(
        url=url,
        final_url=url,
        status_code=200,
        content_type="text/plain",
        body=b"filesystem integration payload",
    )
    engine = _engine(
        root,
        provider,
        mode=PermissionMode.ALWAYS_ALLOW,
        with_filesystem=True,
    )

    downloaded = _submit(
        engine,
        {
            "operation": "download_file",
            "url": url,
            "destination": "shared/notes.txt",
        },
    )
    assert downloaded.status is CapabilityExecutionStatus.COMPLETED
    assert downloaded.output["metadata"]["filesystem_integrated"] is True
    dest = Path(downloaded.output["destination"])
    assert dest.is_relative_to(root.resolve())

    # Read back through the Filesystem Capability — same root, same engine path.
    fs_read = engine.submit(
        CapabilityExecutionRequest.create(
            capability_id="filesystem",
            workspace_id=WorkspaceId.default(),
            arguments={"operation": "read_file", "path": "shared/notes.txt"},
            source="acceptance",
        )
    )
    assert fs_read.status is CapabilityExecutionStatus.COMPLETED
    assert fs_read.output is not None
    assert fs_read.output["content"] == "filesystem integration payload"

    fs_exists = engine.submit(
        CapabilityExecutionRequest.create(
            capability_id="filesystem",
            workspace_id=WorkspaceId.default(),
            arguments={"operation": "exists", "path": "shared/notes.txt"},
            source="acceptance",
        )
    )
    assert fs_exists.status is CapabilityExecutionStatus.COMPLETED
    assert fs_exists.output["exists"] is True


def test_9_every_browser_operation_creates_audit_entry(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    provider = FakeBrowserProvider()
    page_url = "https://example.com/page"
    download_url = "https://example.com/file.bin"
    _seed_page(provider, page_url)
    provider.downloads[download_url] = FetchResult(
        url=download_url,
        final_url=download_url,
        status_code=200,
        content_type="application/octet-stream",
        body=b"audit-bytes",
    )
    engine = _engine(root, provider, mode=PermissionMode.ALWAYS_ALLOW)

    operations: list[dict[str, object]] = [
        {"operation": "open_url", "url": page_url},
        {"operation": "read_page", "url": page_url},
        {"operation": "extract_content", "url": page_url},
        {"operation": "extract_links", "url": page_url},
        {"operation": "extract_metadata", "url": page_url},
        {"operation": "search_web", "query": "memovi browser"},
        {
            "operation": "download_file",
            "url": download_url,
            "destination": "audit/file.bin",
        },
    ]

    for arguments in operations:
        result = _submit(engine, arguments)
        assert result.status is CapabilityExecutionStatus.COMPLETED, arguments["operation"]

    audit = engine.list_audit(workspace_id=WorkspaceId.default())
    completed_ops = {
        entry.arguments.get("operation")
        for entry in audit
        if entry.capability_id == "browser"
        and entry.status is CapabilityExecutionStatus.COMPLETED
    }
    expected = {
        "open_url",
        "read_page",
        "extract_content",
        "extract_links",
        "extract_metadata",
        "search_web",
        "download_file",
    }
    assert expected.issubset(completed_ops)

    for entry in audit:
        if entry.capability_id != "browser":
            continue
        if entry.status is not CapabilityExecutionStatus.COMPLETED:
            continue
        assert entry.workspace_id == WorkspaceId.default().value
        assert entry.duration >= 0
        assert entry.timestamp is not None
        assert entry.result_summary.get("operation") == entry.arguments.get("operation")
