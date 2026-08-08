from collections.abc import Callable, Mapping
from typing import Final, cast

from memovi_automation.application.services.capability_registry import CapabilityRegistry
from memovi_automation.browser import operations
from memovi_automation.browser.config import BrowserCapabilityConfig
from memovi_automation.browser.errors import (
    INVALID_DESTINATION,
    INVALID_QUERY,
    INVALID_TIMEOUT,
    INVALID_URL,
    PERMISSION_DENIED,
    UNSUPPORTED_OPERATION,
)
from memovi_automation.browser.provider import BrowserProvider, HttpBrowserProvider
from memovi_automation.domain.exceptions import CapabilityExecutionError
from memovi_automation.domain.value_objects import (
    BROWSER_DOWNLOAD,
    BROWSER_READ,
    BROWSER_SEARCH,
    CapabilityContext,
    CapabilityMetadata,
    CapabilityParameter,
    CapabilityPermission,
    CapabilityRequest,
)

CAPABILITY_ID: Final = "browser"

READ_OPERATIONS: Final[frozenset[str]] = frozenset(
    {
        "open_url",
        "read_page",
        "extract_content",
        "extract_links",
        "extract_metadata",
    }
)

SEARCH_OPERATIONS: Final[frozenset[str]] = frozenset({"search_web"})

DOWNLOAD_OPERATIONS: Final[frozenset[str]] = frozenset({"download_file"})

_ALL_OPERATIONS: Final[frozenset[str]] = READ_OPERATIONS | SEARCH_OPERATIONS | DOWNLOAD_OPERATIONS

_BROWSER_PERMISSIONS: Final[tuple[CapabilityPermission, ...]] = (
    BROWSER_READ,
    BROWSER_SEARCH,
    BROWSER_DOWNLOAD,
)


class BrowserCapability:
    """Trusted browser capability — structured web access.

    Discoverable through ``CapabilityRegistry`` under id ``browser``.
    Intelligence never issues browser-specific commands; callers submit
    structured operations through the Capability Execution Engine. Provider
    details (HTTP client, search backend) remain private to this package.
    """

    def __init__(
        self,
        config: BrowserCapabilityConfig,
        *,
        provider: BrowserProvider | None = None,
    ) -> None:
        self._config = config
        self._provider: BrowserProvider = provider or HttpBrowserProvider()

    @property
    def config(self) -> BrowserCapabilityConfig:
        return self._config

    def supported_operations(self) -> frozenset[str]:
        return _ALL_OPERATIONS

    def metadata(self) -> CapabilityMetadata:
        return CapabilityMetadata(
            id=CAPABILITY_ID,
            description=(
                "Structured web access: open and read pages, extract content/"
                "links/metadata, search the web, and download files into "
                "Filesystem Capability roots. Permissions separate read, "
                "search, and download."
            ),
            permissions=_BROWSER_PERMISSIONS,
            parameters=(
                CapabilityParameter(
                    name="operation",
                    type="string",
                    description=(
                        "Browser operation name (open_url, read_page, "
                        "extract_content, extract_links, extract_metadata, "
                        "search_web, download_file)."
                    ),
                ),
                CapabilityParameter(
                    name="url",
                    type="string",
                    description="Absolute http(s) URL for navigate/read/download.",
                    required=False,
                ),
                CapabilityParameter(
                    name="query",
                    type="string",
                    description="Search query for search_web.",
                    required=False,
                ),
                CapabilityParameter(
                    name="destination",
                    type="string",
                    description=(
                        "Filesystem path under an allowed download root "
                        "(Filesystem Capability roots)."
                    ),
                    required=False,
                ),
                CapabilityParameter(
                    name="overwrite",
                    type="boolean",
                    description="When true, replace an existing download destination.",
                    required=False,
                ),
                CapabilityParameter(
                    name="limit",
                    type="integer",
                    description="Max search results for search_web.",
                    required=False,
                ),
                CapabilityParameter(
                    name="timeout_seconds",
                    type="number",
                    description="Per-operation timeout capped by configuration.",
                    required=False,
                ),
            ),
        )

    def execute(self, request: CapabilityRequest, context: CapabilityContext) -> object:
        context.check_cancelled()
        operation = _require_string(request.arguments, "operation", code=UNSUPPORTED_OPERATION)
        permission = _permission_for_operation(operation)
        if not context.has_permission(permission):
            raise CapabilityExecutionError(
                f"Missing required permission '{permission}'.",
                code=PERMISSION_DENIED,
                details={
                    "permission": permission.name,
                    "operation": operation,
                },
            )
        if operation not in _ALL_OPERATIONS:
            raise CapabilityExecutionError(
                f"Unsupported browser operation '{operation}'.",
                code=UNSUPPORTED_OPERATION,
                details={"operation": operation},
            )

        timeout_seconds = _resolve_timeout(request.arguments, self._config)
        on_progress = operations.make_progress_reporter(
            _context_progress(context),
            operation=operation,
        )
        context.check_cancelled()

        if operation == "open_url":
            return operations.open_url(
                _require_string(request.arguments, "url", code=INVALID_URL),
                provider=self._provider,
                config=self._config,
                timeout_seconds=timeout_seconds,
                cancellation=context.cancellation,
                on_progress=on_progress,
            )
        if operation == "read_page":
            return operations.read_page(
                _require_string(request.arguments, "url", code=INVALID_URL),
                provider=self._provider,
                config=self._config,
                timeout_seconds=timeout_seconds,
                cancellation=context.cancellation,
                on_progress=on_progress,
            )
        if operation == "extract_content":
            return operations.extract_content(
                _require_string(request.arguments, "url", code=INVALID_URL),
                provider=self._provider,
                config=self._config,
                timeout_seconds=timeout_seconds,
                cancellation=context.cancellation,
                on_progress=on_progress,
            )
        if operation == "extract_links":
            return operations.extract_links(
                _require_string(request.arguments, "url", code=INVALID_URL),
                provider=self._provider,
                config=self._config,
                timeout_seconds=timeout_seconds,
                cancellation=context.cancellation,
                on_progress=on_progress,
            )
        if operation == "extract_metadata":
            return operations.extract_metadata(
                _require_string(request.arguments, "url", code=INVALID_URL),
                provider=self._provider,
                config=self._config,
                timeout_seconds=timeout_seconds,
                cancellation=context.cancellation,
                on_progress=on_progress,
            )
        if operation == "search_web":
            return operations.search_web(
                _require_query(request.arguments),
                provider=self._provider,
                config=self._config,
                limit=_resolve_search_limit(request.arguments, self._config),
                timeout_seconds=timeout_seconds,
                cancellation=context.cancellation,
            )
        if operation == "download_file":
            return operations.download_file(
                _require_string(request.arguments, "url", code=INVALID_URL),
                _require_string(request.arguments, "destination", code=INVALID_DESTINATION),
                provider=self._provider,
                config=self._config,
                timeout_seconds=timeout_seconds,
                overwrite=_optional_bool(request.arguments, "overwrite", False),
                cancellation=context.cancellation,
                on_progress=on_progress,
            )

        raise CapabilityExecutionError(
            f"Unsupported browser operation '{operation}'.",
            code=UNSUPPORTED_OPERATION,
            details={"operation": operation},
        )


def register_browser_capability(
    registry: CapabilityRegistry,
    config: BrowserCapabilityConfig,
    *,
    provider: BrowserProvider | None = None,
) -> BrowserCapability:
    """Register the Browser Capability on a CapabilityRegistry."""
    capability = BrowserCapability(config, provider=provider)
    registry.register(capability)
    return capability


def _permission_for_operation(operation: str) -> CapabilityPermission:
    if operation in READ_OPERATIONS:
        return BROWSER_READ
    if operation in SEARCH_OPERATIONS:
        return BROWSER_SEARCH
    if operation in DOWNLOAD_OPERATIONS:
        return BROWSER_DOWNLOAD
    return BROWSER_READ


def _require_string(
    arguments: Mapping[str, object],
    name: str,
    *,
    code: str | None = None,
) -> str:
    value = arguments.get(name)
    if not isinstance(value, str) or not value.strip():
        raise CapabilityExecutionError(
            f"Argument '{name}' must be a non-empty string.",
            code=code or UNSUPPORTED_OPERATION,
            details={"argument": name},
        )
    return value.strip()


def _require_query(arguments: Mapping[str, object]) -> str:
    value = arguments.get("query")
    if not isinstance(value, str) or not value.strip():
        raise CapabilityExecutionError(
            "Argument 'query' must be a non-empty string.",
            code=INVALID_QUERY,
            details={"argument": "query"},
        )
    return value.strip()


def _optional_bool(arguments: Mapping[str, object], name: str, default: bool) -> bool:
    if name not in arguments:
        return default
    value = arguments[name]
    if not isinstance(value, bool):
        raise CapabilityExecutionError(
            f"Argument '{name}' must be a boolean.",
            code=UNSUPPORTED_OPERATION,
            details={"argument": name},
        )
    return value


def _resolve_timeout(
    arguments: Mapping[str, object],
    config: BrowserCapabilityConfig,
) -> float:
    if "timeout_seconds" not in arguments:
        return config.default_timeout_seconds
    value = arguments["timeout_seconds"]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CapabilityExecutionError(
            "Argument 'timeout_seconds' must be a positive number.",
            code=INVALID_TIMEOUT,
            details={"argument": "timeout_seconds"},
        )
    timeout = float(value)
    if timeout <= 0:
        raise CapabilityExecutionError(
            "Argument 'timeout_seconds' must be a positive number.",
            code=INVALID_TIMEOUT,
            details={"argument": "timeout_seconds", "timeout_seconds": timeout},
        )
    return min(timeout, config.max_timeout_seconds)


def _resolve_search_limit(
    arguments: Mapping[str, object],
    config: BrowserCapabilityConfig,
) -> int:
    if "limit" not in arguments:
        return config.default_search_limit
    value = arguments["limit"]
    if isinstance(value, bool) or not isinstance(value, int):
        raise CapabilityExecutionError(
            "Argument 'limit' must be a positive integer.",
            code=UNSUPPORTED_OPERATION,
            details={"argument": "limit"},
        )
    if value <= 0:
        raise CapabilityExecutionError(
            "Argument 'limit' must be a positive integer.",
            code=UNSUPPORTED_OPERATION,
            details={"argument": "limit", "limit": value},
        )
    return min(value, config.max_search_limit)


def _context_progress(
    context: CapabilityContext,
) -> Callable[[Mapping[str, object]], None] | None:
    reporter = context.metadata.get("report_progress")
    if not callable(reporter):
        return None
    return cast(Callable[[Mapping[str, object]], None], reporter)
