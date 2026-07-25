"""URL validation and audit redaction for the Browser Capability."""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from memovi_automation.browser.errors import INVALID_URL
from memovi_automation.domain.exceptions import CapabilityExecutionError

_ALLOWED_SCHEMES = frozenset({"http", "https"})

_SENSITIVE_QUERY_KEYS = frozenset(
    {
        "password",
        "passwd",
        "pwd",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "id_token",
        "api_key",
        "apikey",
        "key",
        "auth",
        "authorization",
        "credential",
        "credentials",
        "session",
        "sessionid",
        "sid",
        "signature",
        "sig",
        "private_key",
    }
)


def validate_url(raw: object) -> str:
    """Normalize and accept only well-formed http(s) URLs."""
    if not isinstance(raw, str) or not raw.strip():
        raise CapabilityExecutionError(
            "Argument 'url' must be a non-empty string.",
            code=INVALID_URL,
            details={"argument": "url"},
        )

    url = raw.strip()
    try:
        parts = urlsplit(url)
    except ValueError as exc:
        raise CapabilityExecutionError(
            "URL is malformed.",
            code=INVALID_URL,
            details={"url": url},
        ) from exc

    scheme = parts.scheme.lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise CapabilityExecutionError(
            f"Unsupported URL scheme '{parts.scheme or '(none)'}'. Only http and https are allowed.",
            code=INVALID_URL,
            details={"url": url, "scheme": parts.scheme},
        )
    if not parts.netloc:
        raise CapabilityExecutionError(
            "URL is missing a host.",
            code=INVALID_URL,
            details={"url": url},
        )
    if "\x00" in url:
        raise CapabilityExecutionError(
            "URL contains a null byte.",
            code=INVALID_URL,
            details={"url": url},
        )

    # Rebuild with normalized scheme for downstream providers.
    return urlunsplit((scheme, parts.netloc, parts.path or "/", parts.query, parts.fragment))


def redact_url(url: str) -> str:
    """Return a copy of ``url`` with sensitive query parameters redacted."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return "[REDACTED_URL]"

    if not parts.query:
        return url

    redacted_pairs: list[tuple[str, str]] = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key.lower() in _SENSITIVE_QUERY_KEYS or any(
            fragment in key.lower() for fragment in ("token", "secret", "password", "apikey", "api_key")
        ):
            redacted_pairs.append((key, "REDACTED"))
        else:
            redacted_pairs.append((key, value))

    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(redacted_pairs),
            parts.fragment,
        )
    )
