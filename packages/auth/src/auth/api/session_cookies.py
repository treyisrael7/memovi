"""Session cookie flags for local presentation clients.

Development Tauri (`http://127.0.0.1:1420`) is same-site with the local API
(`http://127.0.0.1:8000`), so SameSite=Lax works. A packaged Tauri webview
uses a custom-protocol origin (`tauri://localhost` or `http(s)://tauri.localhost`)
that is cross-site to the API. Lax cookies are not sent on credentialed `fetch`.

Packaged origins therefore receive SameSite=None; Secure. That is scoped to
those Origins only — browser/dev clients keep Lax. SameSite=None requires
Secure; `http://127.0.0.1` is a potentially trustworthy origin in Chromium.
WebKit/Tauri still has to honor that cookie; API tests cannot prove the native
jar.
"""

from __future__ import annotations

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


def session_cookie_flags(
    *,
    origin: str | None,
    request_is_https: bool,
) -> tuple[SameSiteValue, bool]:
    """Return ``(samesite, secure)`` for ``Set-Cookie`` / ``delete_cookie``."""
    if origin in PACKAGED_TAURI_ORIGIN_SET:
        return "none", True
    return "lax", request_is_https
