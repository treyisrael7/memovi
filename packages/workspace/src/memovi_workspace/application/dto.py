from dataclasses import dataclass
from datetime import datetime

from memovi_workspace.domain.entities import Workspace


@dataclass(frozen=True, slots=True)
class WorkspaceDto:
    id: str
    name: str
    created_at: datetime

    @classmethod
    def from_workspace(cls, workspace: Workspace) -> WorkspaceDto:
        return cls(
            id=workspace.id.value,
            name=workspace.name,
            created_at=workspace.created_at,
        )
