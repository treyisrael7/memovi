"""Production Browser Capability — structured web access."""

from memovi_automation.browser.capability import (
    CAPABILITY_ID,
    DOWNLOAD_OPERATIONS,
    READ_OPERATIONS,
    SEARCH_OPERATIONS,
    BrowserCapability,
    register_browser_capability,
)
from memovi_automation.browser.config import BrowserCapabilityConfig
from memovi_automation.browser.errors import (
    CANCELLED,
    DESTINATION_EXISTS,
    DOWNLOAD_FAILED,
    DOWNLOAD_TOO_LARGE,
    INVALID_DESTINATION,
    INVALID_QUERY,
    INVALID_TIMEOUT,
    INVALID_URL,
    NETWORK_UNAVAILABLE,
    PERMISSION_DENIED,
    TIMEOUT,
    UNSUPPORTED_CONTENT,
    UNSUPPORTED_OPERATION,
)
from memovi_automation.browser.provider import (
    BrowserProvider,
    FetchResult,
    HttpBrowserProvider,
    ProviderSearchResults,
    SearchHit,
)
from memovi_automation.browser.url_safety import redact_url, validate_url

__all__ = [
    "CAPABILITY_ID",
    "CANCELLED",
    "DESTINATION_EXISTS",
    "DOWNLOAD_FAILED",
    "DOWNLOAD_OPERATIONS",
    "DOWNLOAD_TOO_LARGE",
    "INVALID_DESTINATION",
    "INVALID_QUERY",
    "INVALID_TIMEOUT",
    "INVALID_URL",
    "NETWORK_UNAVAILABLE",
    "PERMISSION_DENIED",
    "READ_OPERATIONS",
    "SEARCH_OPERATIONS",
    "TIMEOUT",
    "UNSUPPORTED_CONTENT",
    "UNSUPPORTED_OPERATION",
    "BrowserCapability",
    "BrowserCapabilityConfig",
    "BrowserProvider",
    "FetchResult",
    "HttpBrowserProvider",
    "ProviderSearchResults",
    "SearchHit",
    "redact_url",
    "register_browser_capability",
    "validate_url",
]
