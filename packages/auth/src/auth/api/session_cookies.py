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

Deletion must repeat the creation attributes (name, Path, host-only Domain,
HttpOnly, Secure, SameSite, Partitioned) plus Max-Age=0 and an expired Expires.
Python 3.14's ``http.cookies`` treats integer ``expires=0`` as “now”, not the
Unix epoch, so deletion uses an explicit 1970-01-01 GMT datetime.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
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

SESSION_COOKIE_PATH = "/"
COOKIE_DELETION_EXPIRES = datetime(1970, 1, 1, tzinfo=UTC)
NATIVE_SMOKE_REQUEST_HEADER = "x-memovi-native-smoke"
SESSION_COOKIE_CONTRACT_HEADER = "X-Memovi-Session-Cookie"
SESSION_RECEIVED_HEADER = "X-Memovi-Session-Received"

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


def cookie_header_values(cookie_header: str | None, name: str) -> tuple[str, ...]:
    """All non-empty values for ``name`` in a Cookie header, left to right."""
    if not cookie_header:
        return ()
    found: list[str] = []
    for part in cookie_header.split(";"):
        piece = part.strip()
        if not piece or "=" not in piece:
            continue
        key, value = piece.split("=", 1)
        if key.strip() != name:
            continue
        token = value.strip().strip('"')
        if token:
            found.append(token)
    return tuple(found)


def cookie_header_value(cookie_header: str | None, name: str) -> str | None:
    """Parse a Cookie header without Starlette's SimpleCookie parser."""
    values = cookie_header_values(cookie_header, name)
    return values[0] if values else None


def session_token_fingerprint(token: str) -> str:
    """Short SHA-256 prefix for smoke correlation. Never log the raw token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:12]


def describe_session_cookie_contract(
    *,
    name: str,
    flags: SessionCookieFlags,
    deleting: bool,
) -> str:
    """Attribute summary for smoke/CORS-exposed diagnostics. No cookie value."""
    parts = [f"name={name}", f"Path={SESSION_COOKIE_PATH}", "HttpOnly"]
    if flags.secure:
        parts.append("Secure")
    parts.append(f"SameSite={flags.samesite}")
    if flags.partitioned:
        parts.append("Partitioned")
    if deleting:
        parts.append("Max-Age=0")
        parts.append("Expires=Thu, 01 Jan 1970 00:00:00 GMT")
    return "; ".join(parts)


def describe_received_session_cookies(cookie_header: str | None, name: str) -> str:
    values = cookie_header_values(cookie_header, name)
    fingerprints = ",".join(session_token_fingerprint(token) for token in values)
    return f"n={len(values)};fp={fingerprints or '-'}"
