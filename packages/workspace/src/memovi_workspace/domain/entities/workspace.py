from dataclasses import dataclass
from datetime import UTC, datetime

from memovi_shared import WorkspaceId

from memovi_workspace.domain.exceptions import InvalidWorkspaceNameError


@dataclass(frozen=True, slots=True)
class Workspace:
    """Ownership boundary for user-facing knowledge resources."""

    id: WorkspaceId
    name: str
    created_at: datetime

    def __post_init__(self) -> None:
        normalized = self.name.strip()
        if not normalized:
            raise InvalidWorkspaceNameError("Workspace name is required.")
        if len(normalized) > 256:
            raise InvalidWorkspaceNameError("Workspace name must be at most 256 characters.")
        object.__setattr__(self, "name", normalized)

    @classmethod
    def create(
        cls,
        *,
        name: str,
        workspace_id: WorkspaceId | None = None,
        now: datetime | None = None,
    ) -> Workspace:
        return cls(
            id=workspace_id or WorkspaceId.new(),
            name=name,
            created_at=now or datetime.now(UTC),
        )

    @classmethod
    def default(cls, *, now: datetime | None = None) -> Workspace:
        return cls.create(
            name="Default",
            workspace_id=WorkspaceId.default(),
            now=now,
        )
