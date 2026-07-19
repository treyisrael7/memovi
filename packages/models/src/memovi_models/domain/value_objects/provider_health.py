from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType

from memovi_models.domain.exceptions import InvalidModelError

_HEALTH_STATUSES = frozenset({"healthy", "unhealthy", "unknown", "unavailable"})


@dataclass(frozen=True, slots=True)
class ProviderHealth:
    """Normalized health snapshot for a model provider."""

    provider_id: str
    status: str
    message: str | None = None
    checked_at: datetime | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        provider_id = self.provider_id.strip().lower()
        status = self.status.strip().lower()
        message = self.message.strip() if isinstance(self.message, str) else self.message

        if not provider_id:
            raise InvalidModelError("Provider health provider_id is required.")
        if status not in _HEALTH_STATUSES:
            raise InvalidModelError(
                f"Provider health status must be one of: {', '.join(sorted(_HEALTH_STATUSES))}.",
            )
        if not isinstance(self.details, Mapping):
            raise InvalidModelError("Provider health details must be a mapping.")

        checked_at = self.checked_at
        if checked_at is None:
            checked_at = datetime.now(tz=UTC)
        elif checked_at.tzinfo is None:
            checked_at = checked_at.replace(tzinfo=UTC)

        object.__setattr__(self, "provider_id", provider_id)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "checked_at", checked_at)
        object.__setattr__(self, "details", MappingProxyType(dict(self.details)))

    @property
    def is_healthy(self) -> bool:
        return self.status == "healthy"
