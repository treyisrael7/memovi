import uuid
from dataclasses import dataclass

from memovi_shared.exceptions import InvalidWorkspaceIdError


@dataclass(frozen=True, slots=True)
class WorkspaceId:
    """Stable identifier for a Memovi workspace ownership boundary."""

    value: str

    @classmethod
    def new(cls) -> WorkspaceId:
        return cls(str(uuid.uuid4()))

    @classmethod
    def default(cls) -> WorkspaceId:
        return DEFAULT_WORKSPACE_ID

    def __post_init__(self) -> None:
        try:
            parsed = uuid.UUID(self.value)
        except ValueError as exc:
            raise InvalidWorkspaceIdError("Workspace ID must be a valid UUID.") from exc

        object.__setattr__(self, "value", str(parsed))

    def __str__(self) -> str:
        return self.value


# Stable seeded Default Workspace for V1 backwards-compatible fallback.
DEFAULT_WORKSPACE_ID = WorkspaceId("00000000-0000-4000-8000-000000000001")
