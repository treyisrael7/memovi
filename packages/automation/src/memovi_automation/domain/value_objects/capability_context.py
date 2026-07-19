from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from memovi_shared import WorkspaceId

from memovi_automation.domain.exceptions import InvalidCapabilityError
from memovi_automation.domain.value_objects.cancellation_token import CancellationToken
from memovi_automation.domain.value_objects.capability_permission import CapabilityPermission


@dataclass(frozen=True, slots=True)
class CapabilityContext:
    """Runtime boundary through which capabilities interact with the platform.

    Capabilities must not import HTTP, FastAPI, UI, or domain internals.
    All environmental access flows through this context and host-provided ports
    attached by future concrete adapters.
    """

    workspace_id: WorkspaceId
    cancellation: CancellationToken
    correlation_id: str | None = None
    granted_permissions: frozenset[CapabilityPermission] = frozenset()
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.workspace_id, WorkspaceId):
            raise InvalidCapabilityError("Capability context workspace_id must be a WorkspaceId.")
        if not isinstance(self.cancellation, CancellationToken):
            raise InvalidCapabilityError(
                "Capability context cancellation must be a CancellationToken.",
            )
        if self.correlation_id is not None:
            correlation_id = self.correlation_id.strip()
            if not correlation_id:
                raise InvalidCapabilityError(
                    "Capability context correlation_id cannot be blank when provided.",
                )
            object.__setattr__(self, "correlation_id", correlation_id)

        if any(
            not isinstance(permission, CapabilityPermission)
            for permission in self.granted_permissions
        ):
            raise InvalidCapabilityError(
                "granted_permissions must contain CapabilityPermission instances.",
            )
        if not isinstance(self.metadata, Mapping):
            raise InvalidCapabilityError("Capability context metadata must be a mapping.")

        object.__setattr__(self, "granted_permissions", frozenset(self.granted_permissions))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    def is_cancelled(self) -> bool:
        return self.cancellation.is_cancelled

    def check_cancelled(self) -> None:
        self.cancellation.raise_if_cancelled()

    def has_permission(self, permission: CapabilityPermission) -> bool:
        return permission in self.granted_permissions

    @classmethod
    def create(
        cls,
        *,
        workspace_id: WorkspaceId,
        cancellation: CancellationToken | None = None,
        correlation_id: str | None = None,
        granted_permissions: frozenset[CapabilityPermission] | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> CapabilityContext:
        return cls(
            workspace_id=workspace_id,
            cancellation=CancellationToken() if cancellation is None else cancellation,
            correlation_id=correlation_id,
            granted_permissions=frozenset() if granted_permissions is None else granted_permissions,
            metadata={} if metadata is None else metadata,
        )
