from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType

from memovi_connectors.domain.exceptions import InvalidConnectorError

_HEALTH_STATUSES = frozenset(
    {
        "healthy",
        "degraded",
        "unhealthy",
        "unauthorized",
        "unknown",
        "unavailable",
    },
)


@dataclass(frozen=True, slots=True)
class ConnectorHealth:
    """Normalized health and sync status for a connector instance."""

    connector_id: str
    status: str
    last_synchronized_at: datetime | None = None
    imported_document_count: int = 0
    pending_changes: int = 0
    errors: Sequence[str] = ()
    message: str | None = None
    checked_at: datetime | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        connector_id = self.connector_id.strip().lower()
        status = self.status.strip().lower()
        message = self.message.strip() if isinstance(self.message, str) else self.message

        if not connector_id:
            raise InvalidConnectorError("Connector health connector_id is required.")
        if status not in _HEALTH_STATUSES:
            raise InvalidConnectorError(
                f"Connector health status must be one of: {', '.join(sorted(_HEALTH_STATUSES))}.",
            )
        if self.imported_document_count < 0:
            raise InvalidConnectorError(
                "Connector health imported_document_count must be >= 0.",
            )
        if self.pending_changes < 0:
            raise InvalidConnectorError("Connector health pending_changes must be >= 0.")
        if not isinstance(self.details, Mapping):
            raise InvalidConnectorError("Connector health details must be a mapping.")

        checked_at = self.checked_at
        if checked_at is None:
            checked_at = datetime.now(tz=UTC)
        elif checked_at.tzinfo is None:
            checked_at = checked_at.replace(tzinfo=UTC)

        last_synchronized_at = self.last_synchronized_at
        if last_synchronized_at is not None and last_synchronized_at.tzinfo is None:
            last_synchronized_at = last_synchronized_at.replace(tzinfo=UTC)

        errors = tuple(error.strip() for error in self.errors if error and error.strip())

        object.__setattr__(self, "connector_id", connector_id)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "checked_at", checked_at)
        object.__setattr__(self, "last_synchronized_at", last_synchronized_at)
        object.__setattr__(self, "errors", errors)
        object.__setattr__(self, "details", MappingProxyType(dict(self.details)))

    @property
    def is_healthy(self) -> bool:
        return self.status == "healthy"
