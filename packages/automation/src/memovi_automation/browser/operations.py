"""Structured browser operations returning normalized result dictionaries."""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable, Mapping
from pathlib import Path

from memovi_automation.browser.config import BrowserCapabilityConfig
from memovi_automation.browser.content_extract import extract_page_content
from memovi_automation.browser.errors import (
    DESTINATION_EXISTS,
    DOWNLOAD_FAILED,
    INVALID_DESTINATION,
    UNSUPPORTED_CONTENT,
)
from memovi_automation.browser.provider import BrowserProvider, ProgressCallback
from memovi_automation.browser.url_safety import redact_url, validate_url
from memovi_automation.domain.exceptions import (
    CapabilityCancelledError,
    CapabilityExecutionError,
)
from memovi_automation.domain.value_objects import CancellationToken
from memovi_automation.filesystem.path_safety import resolve_safe_path


def open_url(
    url: str,
    *,
    provider: BrowserProvider,
    config: BrowserCapabilityConfig,
    timeout_seconds: float,
    cancellation: CancellationToken | None = None,
    on_progress: ProgressCallback | None = None,
) -> dict[str, object]:
    started = time.perf_counter()
    safe_url = validate_url(url)
    fetch = provider.fetch(
        safe_url,
        config=config,
        timeout_seconds=timeout_seconds,
        cancellation=cancellation,
        on_progress=on_progress,
    )
    extracted = _extract_if_html(fetch.body, fetch.content_type, fetch.final_url)
    duration = time.perf_counter() - started
    return {
        "operation": "open_url",
        "success": True,
        "url": redact_url(safe_url),
        "final_url": redact_url(fetch.final_url),
        "status_code": fetch.status_code,
        "title": extracted.get("title", ""),
        "page_metadata": extracted.get("metadata", {}),
        "redirected": fetch.redirected,
        "redirect_count": fetch.redirect_count,
        "content_type": fetch.content_type,
        "duration_seconds": duration,
        "metadata": {
            "url": redact_url(safe_url),
            "final_url": redact_url(fetch.final_url),
            "status_code": fetch.status_code,
            "redirected": fetch.redirected,
            "title": extracted.get("title", ""),
            "duration_seconds": duration,
        },
    }


def read_page(
    url: str,
    *,
    provider: BrowserProvider,
    config: BrowserCapabilityConfig,
    timeout_seconds: float,
    cancellation: CancellationToken | None = None,
    on_progress: ProgressCallback | None = None,
) -> dict[str, object]:
    started = time.perf_counter()
    safe_url = validate_url(url)
    fetch = provider.fetch(
        safe_url,
        config=config,
        timeout_seconds=timeout_seconds,
        cancellation=cancellation,
        on_progress=on_progress,
    )
    if not _is_html(fetch.content_type, fetch.body):
        raise CapabilityExecutionError(
            "Remote content is not a readable HTML page.",
            code=UNSUPPORTED_CONTENT,
            details={
                "url": redact_url(safe_url),
                "content_type": fetch.content_type,
            },
        )
    extracted = extract_page_content(
        fetch.body.decode("utf-8", errors="replace"),
        base_url=fetch.final_url,
    )
    duration = time.perf_counter() - started
    readable = str(extracted["readable_text"])
    truncated = False
    max_chars = min(config.max_response_bytes, 200_000)
    if len(readable) > max_chars:
        readable = readable[:max_chars]
        truncated = True

    return {
        "operation": "read_page",
        "success": True,
        "url": redact_url(safe_url),
        "final_url": redact_url(fetch.final_url),
        "status_code": fetch.status_code,
        "title": extracted["title"],
        "content": readable,
        "content_truncated": truncated,
        "links": extracted["links"],
        "page_metadata": extracted["metadata"],
        "content_type": fetch.content_type,
        "duration_seconds": duration,
        "metadata": {
            "url": redact_url(safe_url),
            "final_url": redact_url(fetch.final_url),
            "title": extracted["title"],
            "link_count": len(extracted["links"]),  # type: ignore[arg-type]
            "content_truncated": truncated,
            "duration_seconds": duration,
        },
    }


def extract_content(
    url: str,
    *,
    provider: BrowserProvider,
    config: BrowserCapabilityConfig,
    timeout_seconds: float,
    cancellation: CancellationToken | None = None,
    on_progress: ProgressCallback | None = None,
) -> dict[str, object]:
    page = read_page(
        url,
        provider=provider,
        config=config,
        timeout_seconds=timeout_seconds,
        cancellation=cancellation,
        on_progress=on_progress,
    )
    return {
        "operation": "extract_content",
        "success": True,
        "url": page["url"],
        "final_url": page["final_url"],
        "title": page["title"],
        "content": page["content"],
        "content_truncated": page["content_truncated"],
        "duration_seconds": page["duration_seconds"],
        "metadata": {
            "url": page["url"],
            "title": page["title"],
            "content_truncated": page["content_truncated"],
            "duration_seconds": page["duration_seconds"],
        },
    }


def extract_links(
    url: str,
    *,
    provider: BrowserProvider,
    config: BrowserCapabilityConfig,
    timeout_seconds: float,
    cancellation: CancellationToken | None = None,
    on_progress: ProgressCallback | None = None,
) -> dict[str, object]:
    page = read_page(
        url,
        provider=provider,
        config=config,
        timeout_seconds=timeout_seconds,
        cancellation=cancellation,
        on_progress=on_progress,
    )
    links = page["links"]
    return {
        "operation": "extract_links",
        "success": True,
        "url": page["url"],
        "final_url": page["final_url"],
        "title": page["title"],
        "links": links,
        "duration_seconds": page["duration_seconds"],
        "metadata": {
            "url": page["url"],
            "link_count": len(links) if isinstance(links, list) else 0,
            "duration_seconds": page["duration_seconds"],
        },
    }


def extract_metadata(
    url: str,
    *,
    provider: BrowserProvider,
    config: BrowserCapabilityConfig,
    timeout_seconds: float,
    cancellation: CancellationToken | None = None,
    on_progress: ProgressCallback | None = None,
) -> dict[str, object]:
    page = read_page(
        url,
        provider=provider,
        config=config,
        timeout_seconds=timeout_seconds,
        cancellation=cancellation,
        on_progress=on_progress,
    )
    return {
        "operation": "extract_metadata",
        "success": True,
        "url": page["url"],
        "final_url": page["final_url"],
        "title": page["title"],
        "content_type": page["content_type"],
        "status_code": page["status_code"],
        "page_metadata": page["page_metadata"],
        "duration_seconds": page["duration_seconds"],
        "metadata": {
            "url": page["url"],
            "title": page["title"],
            "status_code": page["status_code"],
            "duration_seconds": page["duration_seconds"],
        },
    }


def search_web(
    query: str,
    *,
    provider: BrowserProvider,
    config: BrowserCapabilityConfig,
    limit: int,
    timeout_seconds: float,
    cancellation: CancellationToken | None = None,
) -> dict[str, object]:
    started = time.perf_counter()
    results = provider.search(
        query,
        limit=limit,
        config=config,
        timeout_seconds=timeout_seconds,
        cancellation=cancellation,
    )
    structured = [
        {
            "title": hit.title,
            "url": redact_url(hit.url) if hit.url.startswith("http") else hit.url,
            "snippet": hit.snippet,
        }
        for hit in results.results
    ]
    duration = time.perf_counter() - started
    return {
        "operation": "search_web",
        "success": True,
        "query": query,
        "results": structured,
        "result_count": len(structured),
        "duration_seconds": duration,
        "metadata": {
            "query": query,
            "result_count": len(structured),
            "duration_seconds": duration,
        },
    }


def download_file(
    url: str,
    destination: str,
    *,
    provider: BrowserProvider,
    config: BrowserCapabilityConfig,
    timeout_seconds: float,
    overwrite: bool = False,
    cancellation: CancellationToken | None = None,
    on_progress: ProgressCallback | None = None,
) -> dict[str, object]:
    """Download a remote file into a Filesystem Capability root."""
    started = time.perf_counter()
    safe_url = validate_url(url)
    try:
        dest_path = resolve_safe_path(destination, allowed_roots=config.download_roots)
    except CapabilityExecutionError as exc:
        raise CapabilityExecutionError(
            "Download destination is invalid or outside allowed filesystem roots.",
            code=INVALID_DESTINATION,
            details={"destination": destination, "reason": exc.code},
        ) from exc

    for root in config.download_roots:
        if dest_path == root:
            raise CapabilityExecutionError(
                "Refusing to write a download onto an allowed root path.",
                code=INVALID_DESTINATION,
                details={"destination": str(dest_path)},
            )

    if dest_path.exists() and not overwrite:
        raise CapabilityExecutionError(
            f"Download destination already exists: {dest_path}",
            code=DESTINATION_EXISTS,
            details={"destination": str(dest_path)},
        )

    # Stage under the same root so cancel/failure never leaves a partial final file.
    staging_path = dest_path.with_name(f"{dest_path.name}.memovi-partial")
    _safe_unlink(staging_path)

    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        # Marker lets cancel cleanup remove in-progress download artifacts.
        staging_path.write_bytes(b"")
        if on_progress is not None:
            on_progress(
                {
                    "phase": "download",
                    "url": redact_url(safe_url),
                    "bytes_received": 0,
                    "progress": 0.0,
                    "destination": str(dest_path),
                    "staging_path": str(staging_path),
                }
            )

        fetch = provider.download_bytes(
            safe_url,
            config=config,
            timeout_seconds=timeout_seconds,
            cancellation=cancellation,
            on_progress=on_progress,
        )
        if cancellation is not None:
            cancellation.raise_if_cancelled()

        digest = hashlib.sha256(fetch.body).hexdigest()
        staging_path.write_bytes(fetch.body)
        if dest_path.exists() and overwrite:
            _safe_unlink(dest_path)
        staging_path.replace(dest_path)
    except CapabilityCancelledError:
        _safe_unlink(staging_path)
        raise
    except CapabilityExecutionError:
        _safe_unlink(staging_path)
        raise
    except OSError as exc:
        _safe_unlink(staging_path)
        raise CapabilityExecutionError(
            "Failed to save download to filesystem destination.",
            code=DOWNLOAD_FAILED,
            details={
                "destination": str(dest_path),
                "os_error": type(exc).__name__,
            },
        ) from exc
    except Exception:
        _safe_unlink(staging_path)
        raise

    duration = time.perf_counter() - started
    if on_progress is not None:
        on_progress(
            {
                "phase": "download",
                "url": redact_url(safe_url),
                "bytes_received": len(fetch.body),
                "bytes_total": len(fetch.body),
                "progress": 1.0,
                "destination": str(dest_path),
                "complete": True,
            }
        )

    return {
        "operation": "download_file",
        "success": True,
        "url": redact_url(safe_url),
        "final_url": redact_url(fetch.final_url),
        "destination": str(dest_path),
        "bytes_written": len(fetch.body),
        "content_type": fetch.content_type,
        "sha256": digest,
        "status_code": fetch.status_code,
        "duration_seconds": duration,
        "metadata": {
            "url": redact_url(safe_url),
            "destination": str(dest_path),
            "bytes_written": len(fetch.body),
            "sha256": digest,
            "filesystem_integrated": True,
            "duration_seconds": duration,
        },
    }


def _safe_unlink(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except OSError:
        return


def _is_html(content_type: str, body: bytes) -> bool:
    if "html" in content_type:
        return True
    snippet = body[:200].lstrip().lower()
    return snippet.startswith(b"<!doctype html") or snippet.startswith(b"<html")


def _extract_if_html(body: bytes, content_type: str, base_url: str) -> dict[str, object]:
    if not _is_html(content_type, body):
        return {"title": "", "readable_text": "", "links": [], "metadata": {}}
    return extract_page_content(
        body.decode("utf-8", errors="replace"),
        base_url=base_url,
    )


def make_progress_reporter(
    context_reporter: Callable[[Mapping[str, object]], None] | None,
    *,
    operation: str,
) -> ProgressCallback | None:
    if context_reporter is None:
        return None

    def _report(partial: Mapping[str, object]) -> None:
        try:
            payload = {
                "operation": operation,
                "success": False,
                "streaming": True,
                "phase": partial.get("phase", operation),
                "bytes_received": partial.get("bytes_received", 0),
                "bytes_total": partial.get("bytes_total"),
                "progress": partial.get("progress", 0.0),
                "url": partial.get("url"),
                "destination": partial.get("destination"),
                "metadata": {
                    "streaming": True,
                    "phase": partial.get("phase", operation),
                    "progress": partial.get("progress", 0.0),
                },
            }
            context_reporter(payload)
        except Exception:
            return

    return _report
