import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from memovi_automation.domain.exceptions import InvalidCapabilityError
from memovi_automation.domain.value_objects.capability_execution_status import (
    CapabilityExecutionStatus,
)
from memovi_automation.domain.value_objects.permission_mode import PermissionMode

_SENSITIVE_KEY_FRAGMENTS = (
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "private_key",
)

# File contents and similar payloads are never stored in audit arguments.
_CONTENT_KEYS = frozenset(
    {
        "content",
        "body",
        "text",
        "data",
        "file_content",
        "stdout",
        "stderr",
        "readable_text",
        "html",
    }
)

_URL_KEYS = frozenset({"url", "final_url"})

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


def redact_arguments(arguments: Mapping[str, object]) -> dict[str, object]:
    """Return a copy of arguments with sensitive values redacted for audit storage."""
    redacted: dict[str, object] = {}
    for key, value in arguments.items():
        lowered = key.lower()
        if lowered in _CONTENT_KEYS or any(
            fragment in lowered for fragment in _SENSITIVE_KEY_FRAGMENTS
        ):
            redacted[key] = "[REDACTED]"
        elif lowered in _URL_KEYS and isinstance(value, str):
            redacted[key] = redact_url_for_audit(value)
        elif lowered == "command" and isinstance(value, str):
            redacted[key] = redact_command_secrets(value)
        elif isinstance(value, Mapping):
            # Environment maps are redacted key-by-key so non-sensitive values remain.
            redacted[key] = redact_arguments(value)
        else:
            redacted[key] = value
    return redacted


def redact_command_secrets(command: str) -> str:
    """Redact likely secrets embedded in terminal command strings."""
    patterns = (
        (re.compile(r"(?i)(--password=)\S+"), r"\1[REDACTED]"),
        (re.compile(r"(?i)(--passwd=)\S+"), r"\1[REDACTED]"),
        (re.compile(r"(?i)(--token=)\S+"), r"\1[REDACTED]"),
        (re.compile(r"(?i)(--api[_-]?key=)\S+"), r"\1[REDACTED]"),
        (re.compile(r"(?i)\b(password=)\S+"), r"\1[REDACTED]"),
        (re.compile(r"(?i)\b(token=)\S+"), r"\1[REDACTED]"),
        (re.compile(r"(?i)\b(api[_-]?key=)\S+"), r"\1[REDACTED]"),
    )
    redacted = command
    for pattern, repl in patterns:
        redacted = pattern.sub(repl, redacted)
    return redacted


def redact_url_for_audit(url: str) -> str:
    """Redact sensitive query parameters from URL-like audit values."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return "[REDACTED_URL]"
    if not parts.query:
        return url
    redacted_pairs: list[tuple[str, str]] = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        lowered = key.lower()
        if lowered in _SENSITIVE_QUERY_KEYS or any(
            fragment in lowered
            for fragment in ("token", "secret", "password", "apikey", "api_key")
        ):
            redacted_pairs.append((key, "REDACTED"))
        else:
            redacted_pairs.append((key, value))
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(redacted_pairs), parts.fragment)
    )


@dataclass(frozen=True, slots=True)
class ExecutionAuditEntry:
    """Immutable audit record for a capability execution event."""

    id: str
    execution_id: str
    workspace_id: str
    capability_id: str
    status: CapabilityExecutionStatus
    permission_mode: PermissionMode
    arguments: Mapping[str, object]
    result_summary: Mapping[str, object]
    duration: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    conversation_id: str | None = None
    correlation_id: str | None = None
    source: str = "api"
    user_id: str | None = None
    operation: str | None = None

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise InvalidCapabilityError("Execution audit entry id is required.")
        if not self.execution_id.strip():
            raise InvalidCapabilityError("Execution audit entry execution_id is required.")
        if not self.workspace_id.strip():
            raise InvalidCapabilityError("Execution audit entry workspace_id is required.")
        if not self.capability_id.strip():
            raise InvalidCapabilityError("Execution audit entry capability_id is required.")
        if self.duration < 0:
            raise InvalidCapabilityError("Execution audit entry duration cannot be negative.")
        if not isinstance(self.arguments, Mapping):
            raise InvalidCapabilityError("Execution audit entry arguments must be a mapping.")
        if not isinstance(self.result_summary, Mapping):
            raise InvalidCapabilityError("Execution audit entry result_summary must be a mapping.")

        object.__setattr__(self, "id", self.id.strip())
        object.__setattr__(self, "execution_id", self.execution_id.strip())
        object.__setattr__(self, "workspace_id", self.workspace_id.strip())
        object.__setattr__(self, "capability_id", self.capability_id.strip())
        object.__setattr__(self, "arguments", MappingProxyType(dict(self.arguments)))
        object.__setattr__(self, "result_summary", MappingProxyType(dict(self.result_summary)))
        object.__setattr__(self, "source", self.source.strip() or "api")
        if self.user_id is not None:
            object.__setattr__(self, "user_id", self.user_id.strip() or None)
        if self.operation is not None:
            object.__setattr__(self, "operation", self.operation.strip() or None)
