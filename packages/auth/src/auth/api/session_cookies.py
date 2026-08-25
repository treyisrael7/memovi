"""Session cookie flags for local presentation clients.

Development Tauri (`http://127.0.0.1:1420`) is same-site with the local API
(`http://127.0.0.1:8000`), so SameSite=Lax works. A packaged Tauri webview
uses a custom-protocol origin (`tauri://localhost` or `http(s)://tauri.localhost`)
that is cross-site to the API. Lax cookies are not sent on credentialed `fetch`.

Packaged origins therefore receive SameSite=None; Secure; Partitioned. That is
scoped to those Origins only — browser/dev clients keep Lax. SameSite=None
requires Secure. Chromium WebView2 treats the API cookie as third-party from
`http://tauri.localhost`; unpartitioned third-party cookies are not stored.
`Partitioned` (CHIPS) is the opt-in so the jar is keyed by the Tauri top-level
site. `http://127.0.0.1` is a potentially trustworthy origin in Chromium for
the Secure flag. WebKitGTK/WKWebView still have to be proven natively.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

DEV_DESKTOP_ORIGINS = (
    "http://localhost:1420",
    "http://127.0.0.1:1420",
)
OPTIONAL_WEB_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)
PACKAGED_TAURI_ORIGINS = (
    "tauri://localhost",
    "https://tauri.localhost",
    "http://tauri.localhost",
)

LOCAL_CLIENT_ORIGINS = DEV_DESKTOP_ORIGINS + OPTIONAL_WEB_ORIGINS + PACKAGED_TAURI_ORIGINS
PACKAGED_TAURI_ORIGIN_SET = frozenset(PACKAGED_TAURI_ORIGINS)

SameSiteValue = Literal["lax", "none"]


@dataclass(frozen=True, slots=True)
class SessionCookieFlags:
    samesite: SameSiteValue
    secure: bool
    partitioned: bool


def session_cookie_flags(
    *,
    origin: str | None,
    request_is_https: bool,
) -> SessionCookieFlags:
    """Return cookie flags for ``Set-Cookie`` / session clear."""
    if origin in PACKAGED_TAURI_ORIGIN_SET:
        return SessionCookieFlags(samesite="none", secure=True, partitioned=True)
    return SessionCookieFlags(samesite="lax", secure=request_is_https, partitioned=False)


def cookie_header_value(cookie_header: str | None, name: str) -> str | None:
    """Parse a Cookie header without Starlette's SimpleCookie parser."""
    if not cookie_header:
        return None
    for part in cookie_header.split(";"):
        piece = part.strip()
        if not piece or "=" not in piece:
            continue
        key, value = piece.split("=", 1)
        if key.strip() == name:
            return value.strip().strip('"')
    return None
