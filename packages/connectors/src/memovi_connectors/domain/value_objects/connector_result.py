from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType

from memovi_connectors.domain.exceptions import InvalidConnectorError
from memovi_connectors.domain.value_objects.normalized_import import NormalizedImportItem


@dataclass(frozen=True, slots=True)
class ConnectorResult:
    """Outcome of a connector synchronization run."""

    connector_id: str
    success: bool
    sync_mode: str
    imported_count: int = 0
    updated_count: int = 0
    deleted_count: int = 0
    skipped_count: int = 0
    pending_changes: int = 0
    cursor: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    items: Sequence[NormalizedImportItem] = ()
    completed_at: datetime | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        connector_id = self.connector_id.strip().lower()
        sync_mode = self.sync_mode.strip().lower()
        if not connector_id:
            raise InvalidConnectorError("Connector result connector_id is required.")
        if sync_mode not in {"initial", "incremental"}:
            raise InvalidConnectorError(
                "Connector result sync_mode must be initial or incremental.",
            )
        for count_name in (
            "imported_count",
            "updated_count",
            "deleted_count",
            "skipped_count",
            "pending_changes",
        ):
            value = getattr(self, count_name)
            if not isinstance(value, int) or value < 0:
                raise InvalidConnectorError(f"Connector result {count_name} must be >= 0.")
        if not self.success and not (self.error_code or self.error_message):
            raise InvalidConnectorError(
                "Failed connector results require error_code or error_message.",
            )
        if not isinstance(self.details, Mapping):
            raise InvalidConnectorError("Connector result details must be a mapping.")

        completed_at = self.completed_at
        if completed_at is None:
            completed_at = datetime.now(tz=UTC)
        elif completed_at.tzinfo is None:
            completed_at = completed_at.replace(tzinfo=UTC)

        cursor = self.cursor.strip() if isinstance(self.cursor, str) else self.cursor
        error_code = (
            self.error_code.strip() if isinstance(self.error_code, str) else self.error_code
        )
        error_message = (
            self.error_message.strip()
            if isinstance(self.error_message, str)
            else self.error_message
        )

        object.__setattr__(self, "connector_id", connector_id)
        object.__setattr__(self, "sync_mode", sync_mode)
        object.__setattr__(self, "cursor", cursor)
        object.__setattr__(self, "error_code", error_code)
        object.__setattr__(self, "error_message", error_message)
        object.__setattr__(self, "completed_at", completed_at)
        object.__setattr__(self, "items", tuple(self.items))
        object.__setattr__(self, "details", MappingProxyType(dict(self.details)))

    @classmethod
    def success_result(
        cls,
        *,
        connector_id: str,
        sync_mode: str,
        imported_count: int = 0,
        updated_count: int = 0,
        deleted_count: int = 0,
        skipped_count: int = 0,
        pending_changes: int = 0,
        cursor: str | None = None,
        items: Sequence[NormalizedImportItem] = (),
        details: Mapping[str, object] | None = None,
    ) -> ConnectorResult:
        return cls(
            connector_id=connector_id,
            success=True,
            sync_mode=sync_mode,
            imported_count=imported_count,
            updated_count=updated_count,
            deleted_count=deleted_count,
            skipped_count=skipped_count,
            pending_changes=pending_changes,
            cursor=cursor,
            items=items,
            details={} if details is None else details,
        )

    @classmethod
    def failure_result(
        cls,
        *,
        connector_id: str,
        sync_mode: str,
        error_code: str,
        error_message: str,
        pending_changes: int = 0,
        cursor: str | None = None,
        details: Mapping[str, object] | None = None,
    ) -> ConnectorResult:
        return cls(
            connector_id=connector_id,
            success=False,
            sync_mode=sync_mode,
            pending_changes=pending_changes,
            cursor=cursor,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )
