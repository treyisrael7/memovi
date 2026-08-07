from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from memovi_shared import WorkspaceId

from memovi_connectors.application.ports import Connector
from memovi_connectors.application.services.connector_registry import ConnectorRegistry
from memovi_connectors.domain.exceptions import InvalidConnectorError, UnknownConnectorError
from memovi_connectors.domain.value_objects import ConnectorExecutionContext, ConnectorResult


@dataclass(frozen=True, slots=True)
class ConnectorScheduleSpec:
    """Declarative schedule intent for a future connector scheduler.

    This is foundation-only: specs can be registered and listed, but nothing
    runs them on a timer yet.
    """

    connector_id: str
    workspace_id: WorkspaceId
    sync_mode: str = "incremental"
    interval_seconds: int | None = None
    enabled: bool = True
    options: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        connector_id = self.connector_id.strip().lower()
        sync_mode = self.sync_mode.strip().lower()
        if not connector_id:
            raise InvalidConnectorError("Schedule spec connector_id is required.")
        if not isinstance(self.workspace_id, WorkspaceId):
            raise InvalidConnectorError("Schedule spec workspace_id must be a WorkspaceId.")
        if sync_mode not in {"initial", "incremental"}:
            raise InvalidConnectorError(
                "Schedule spec sync_mode must be initial or incremental.",
            )
        if self.interval_seconds is not None and self.interval_seconds <= 0:
            raise InvalidConnectorError(
                "Schedule spec interval_seconds must be positive when set.",
            )
        if not isinstance(self.options, Mapping):
            raise InvalidConnectorError("Schedule spec options must be a mapping.")
        object.__setattr__(self, "connector_id", connector_id)
        object.__setattr__(self, "sync_mode", sync_mode)
        object.__setattr__(self, "options", MappingProxyType(dict(self.options)))


class ConnectorScheduler:
    """Foundation for future scheduled connector synchronization.

    Owns schedule registration and on-demand sync execution through the
    registry. Does **not** run a background cron or worker loop yet.
    """

    def __init__(self, registry: ConnectorRegistry) -> None:
        self._registry = registry
        self._schedules: dict[tuple[str, str], ConnectorScheduleSpec] = {}

    def register_schedule(self, spec: ConnectorScheduleSpec) -> None:
        if not self._registry.contains(spec.connector_id):
            raise UnknownConnectorError(
                f"Cannot schedule unknown connector '{spec.connector_id}'.",
            )
        key = (spec.connector_id, str(spec.workspace_id))
        self._schedules[key] = spec

    def list_schedules(self) -> tuple[ConnectorScheduleSpec, ...]:
        return tuple(self._schedules.values())

    def get_schedule(
        self,
        *,
        connector_id: str,
        workspace_id: WorkspaceId,
    ) -> ConnectorScheduleSpec | None:
        return self._schedules.get((connector_id.strip().lower(), str(workspace_id)))

    def run_now(
        self,
        *,
        connector_id: str,
        context: ConnectorExecutionContext,
    ) -> ConnectorResult:
        """Execute a sync immediately through the registered connector."""
        connector: Connector = self._registry.get(connector_id)
        if context.connector_id != connector.connector_id():
            raise InvalidConnectorError(
                "Execution context connector_id must match the requested connector.",
            )
        return connector.sync(context)
