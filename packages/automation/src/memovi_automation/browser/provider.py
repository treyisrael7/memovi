"""Browser provider abstraction and default HTTP implementation.

The Capability surface never exposes provider types. Intelligence and Desktop
receive only normalized dictionaries from BrowserCapability operations.
"""

from __future__ import annotations

import json
import socket
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus, urlencode
from urllib.request import Request, urlopen

from memovi_automation.browser.config import BrowserCapabilityConfig
from memovi_automation.browser.errors import (
    DOWNLOAD_FAILED,
    DOWNLOAD_TOO_LARGE,
    NETWORK_UNAVAILABLE,
    TIMEOUT,
    UNSUPPORTED_CONTENT,
)
from memovi_automation.domain.exceptions import (
    CapabilityCancelledError,
    CapabilityExecutionError,
)
from memovi_automation.domain.value_objects import CancellationToken

ProgressCallback = Callable[[Mapping[str, object]], None]


@dataclass(frozen=True, slots=True)
class FetchResult:
    """Normalized HTTP fetch outcome used inside the browser package."""

    url: str
    final_url: str
    status_code: int
    content_type: str
    body: bytes
    headers: Mapping[str, str] = field(default_factory=dict)
    redirected: bool = False
    redirect_count: int = 0


@dataclass(frozen=True, slots=True)
class SearchHit:
    title: str
    url: str
    snippet: str


@dataclass(frozen=True, slots=True)
class ProviderSearchResults:
    query: str
    results: tuple[SearchHit, ...]


class BrowserProvider(Protocol):
    """Private provider contract for network access.

    Implementations may use urllib, httpx, or a headless browser. That choice
    must not leak into capability results.
    """

    def fetch(
        self,
        url: str,
        *,
        config: BrowserCapabilityConfig,
        timeout_seconds: float,
        cancellation: CancellationToken | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> FetchResult:
        """Fetch a URL and return bytes + response metadata."""

    def search(
        self,
        query: str,
        *,
        limit: int,
        config: BrowserCapabilityConfig,
        timeout_seconds: float,
        cancellation: CancellationToken | None = None,
    ) -> ProviderSearchResults:
        """Perform a web search and return structured hits."""

    def download_bytes(
        self,
        url: str,
        *,
        config: BrowserCapabilityConfig,
        timeout_seconds: float,
        cancellation: CancellationToken | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> FetchResult:
        """Download remote bytes (may be larger than a page read)."""


class HttpBrowserProvider:
    """Default BrowserProvider using the Python standard library."""

    def fetch(
        self,
        url: str,
        *,
        config: BrowserCapabilityConfig,
        timeout_seconds: float,
        cancellation: CancellationToken | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> FetchResult:
        return self._request(
            url,
            config=config,
            timeout_seconds=timeout_seconds,
            max_bytes=config.max_response_bytes,
            cancellation=cancellation,
            on_progress=on_progress,
            phase="navigate",
        )

    def search(
        self,
        query: str,
        *,
        limit: int,
        config: BrowserCapabilityConfig,
        timeout_seconds: float,
        cancellation: CancellationToken | None = None,
    ) -> ProviderSearchResults:
        _check_cancelled(cancellation)
        # DuckDuckGo Instant Answer API — no API key required.
        endpoint = (
            "https://api.duckduckgo.com/?"
            + urlencode({"q": query, "format": "json", "no_redirect": "1", "no_html": "1"})
        )
        result = self._request(
            endpoint,
            config=config,
            timeout_seconds=timeout_seconds,
            max_bytes=config.max_response_bytes,
            cancellation=cancellation,
            on_progress=None,
            phase="search",
        )
        try:
            payload = json.loads(result.body.decode("utf-8", errors="replace"))
        except json.JSONDecodeError as exc:
            raise CapabilityExecutionError(
                "Search provider returned unsupported content.",
                code=UNSUPPORTED_CONTENT,
                details={"content_type": result.content_type},
            ) from exc

        hits: list[SearchHit] = []
        abstract = str(payload.get("AbstractText") or "").strip()
        abstract_url = str(payload.get("AbstractURL") or "").strip()
        heading = str(payload.get("Heading") or query).strip()
        if abstract and abstract_url:
            hits.append(SearchHit(title=heading or query, url=abstract_url, snippet=abstract))

        for topic in payload.get("RelatedTopics") or []:
            if len(hits) >= limit:
                break
            if not isinstance(topic, dict):
                continue
            if "Topics" in topic:
                for nested in topic.get("Topics") or []:
                    if len(hits) >= limit:
                        break
                    hit = _topic_hit(nested)
                    if hit is not None:
                        hits.append(hit)
                continue
            hit = _topic_hit(topic)
            if hit is not None:
                hits.append(hit)

        # Fallback: synthesize a search landing URL when Instant Answer is empty.
        if not hits:
            hits.append(
                SearchHit(
                    title=f"Search results for {query}",
                    url=f"https://duckduckgo.com/?q={quote_plus(query)}",
                    snippet="Open the search page for full results.",
                )
            )

        return ProviderSearchResults(query=query, results=tuple(hits[:limit]))

    def download_bytes(
        self,
        url: str,
        *,
        config: BrowserCapabilityConfig,
        timeout_seconds: float,
        cancellation: CancellationToken | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> FetchResult:
        return self._request(
            url,
            config=config,
            timeout_seconds=timeout_seconds,
            max_bytes=config.max_download_bytes,
            cancellation=cancellation,
            on_progress=on_progress,
            phase="download",
        )

    def _request(
        self,
        url: str,
        *,
        config: BrowserCapabilityConfig,
        timeout_seconds: float,
        max_bytes: int,
        cancellation: CancellationToken | None,
        on_progress: ProgressCallback | None,
        phase: str,
    ) -> FetchResult:
        _check_cancelled(cancellation)
        if on_progress is not None:
            on_progress(
                {
                    "phase": phase,
                    "url": url,
                    "bytes_received": 0,
                    "progress": 0.0,
                }
            )

        request = Request(
            url,
            headers={"User-Agent": config.user_agent, "Accept": "*/*"},
            method="GET",
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
                _check_cancelled(cancellation)
                final_url = response.geturl()
                status_code = int(getattr(response, "status", 200) or 200)
                headers = {key.lower(): value for key, value in response.headers.items()}
                content_type = headers.get("content-type", "application/octet-stream")
                content_length_header = headers.get("content-length")
                expected = (
                    int(content_length_header)
                    if content_length_header and content_length_header.isdigit()
                    else None
                )
                if expected is not None and expected > max_bytes:
                    raise CapabilityExecutionError(
                        f"Remote content exceeds size limit ({max_bytes} bytes).",
                        code=DOWNLOAD_TOO_LARGE,
                        details={
                            "content_length": expected,
                            "max_bytes": max_bytes,
                        },
                    )

                chunks: list[bytes] = []
                received = 0
                while True:
                    _check_cancelled(cancellation)
                    chunk = response.read(64 * 1024)
                    if not chunk:
                        break
                    received += len(chunk)
                    if received > max_bytes:
                        raise CapabilityExecutionError(
                            f"Remote content exceeds size limit ({max_bytes} bytes).",
                            code=DOWNLOAD_TOO_LARGE,
                            details={
                                "bytes_received": received,
                                "max_bytes": max_bytes,
                            },
                        )
                    chunks.append(chunk)
                    if on_progress is not None:
                        progress = (
                            min(1.0, received / expected) if expected and expected > 0 else 0.0
                        )
                        on_progress(
                            {
                                "phase": phase,
                                "url": url,
                                "final_url": final_url,
                                "bytes_received": received,
                                "bytes_total": expected,
                                "progress": progress,
                            }
                        )

                body = b"".join(chunks)
                redirected = final_url.rstrip("/") != url.rstrip("/")
                return FetchResult(
                    url=url,
                    final_url=final_url,
                    status_code=status_code,
                    content_type=content_type.split(";")[0].strip().lower(),
                    body=body,
                    headers=headers,
                    redirected=redirected,
                    redirect_count=1 if redirected else 0,
                )
        except CapabilityExecutionError:
            raise
        except CapabilityCancelledError:
            raise
        except TimeoutError as exc:
            raise CapabilityExecutionError(
                "Browser request timed out.",
                code=TIMEOUT,
                details={"url": url},
            ) from exc
        except socket.timeout as exc:
            raise CapabilityExecutionError(
                "Browser request timed out.",
                code=TIMEOUT,
                details={"url": url},
            ) from exc
        except HTTPError as exc:
            raise CapabilityExecutionError(
                f"HTTP request failed with status {exc.code}.",
                code=DOWNLOAD_FAILED if phase == "download" else NETWORK_UNAVAILABLE,
                details={"url": url, "status_code": exc.code},
            ) from exc
        except URLError as exc:
            reason = getattr(exc, "reason", None)
            if isinstance(reason, TimeoutError | socket.timeout):
                raise CapabilityExecutionError(
                    "Browser request timed out.",
                    code=TIMEOUT,
                    details={"url": url},
                ) from exc
            raise CapabilityExecutionError(
                "Network unavailable or host unreachable.",
                code=NETWORK_UNAVAILABLE,
                details={"url": url},
            ) from exc
        except OSError as exc:
            raise CapabilityExecutionError(
                "Network unavailable or host unreachable.",
                code=NETWORK_UNAVAILABLE,
                details={"url": url, "os_error": type(exc).__name__},
            ) from exc


def _topic_hit(topic: object) -> SearchHit | None:
    if not isinstance(topic, dict):
        return None
    text = str(topic.get("Text") or "").strip()
    first_url = topic.get("FirstURL")
    url = str(first_url or "").strip()
    if not text or not url:
        return None
    title = text.split(" - ", 1)[0].strip() or text[:80]
    return SearchHit(title=title, url=url, snippet=text)


def _check_cancelled(cancellation: CancellationToken | None) -> None:
    if cancellation is not None:
        cancellation.raise_if_cancelled()
