from memovi_shared import WorkspaceId

from memovi_automation.domain.value_objects.permission_mode import PermissionMode


class InMemoryPermissionPolicyStore:
    """Workspace-scoped in-memory permission modes for capability execution."""

    def __init__(self, *, default_mode: PermissionMode = PermissionMode.ASK_EVERY_TIME) -> None:
        self._default_mode = default_mode
        self._modes: dict[tuple[str, str], PermissionMode] = {}

    def get(self, capability_id: str, *, workspace_id: WorkspaceId) -> PermissionMode:
        return self._modes.get((workspace_id.value, capability_id), self._default_mode)

    def set(
        self,
        capability_id: str,
        mode: PermissionMode,
        *,
        workspace_id: WorkspaceId,
    ) -> None:
        self._modes[(workspace_id.value, capability_id)] = mode
