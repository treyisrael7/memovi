from dataclasses import dataclass, replace
from datetime import UTC, datetime

from memovi_shared import WorkspaceId

from memovi_memory.domain.exceptions import InvalidResourceMetadataError
from memovi_memory.domain.value_objects import CollectionMemberKind

_MAX_TITLE_LENGTH = 512
_MAX_DESCRIPTION_LENGTH = 4000
_MAX_NOTES_LENGTH = 8000
_MAX_MEMBER_ID_LENGTH = 256


@dataclass(frozen=True, slots=True)
class ResourceMetadata:
    """Memory-owned polymorphic metadata for a platform resource.

    Avoids adding title/description/notes columns onto Documents or
    Intelligence entities. Unique per (workspace, member_kind, member_id).
    """

    workspace_id: WorkspaceId
    member_kind: CollectionMemberKind
    member_id: str
    title: str | None
    description: str | None
    notes: str | None
    updated_at: datetime

    def __post_init__(self) -> None:
        member_id = self.member_id.strip()
        if not member_id:
            raise InvalidResourceMetadataError("Member ID is required.")
        if len(member_id) > _MAX_MEMBER_ID_LENGTH:
            raise InvalidResourceMetadataError(
                f"Member ID must be at most {_MAX_MEMBER_ID_LENGTH} characters.",
            )
        object.__setattr__(self, "member_id", member_id)
        object.__setattr__(
            self,
            "title",
            normalize_optional_text(self.title, _MAX_TITLE_LENGTH, "Title"),
        )
        object.__setattr__(
            self,
            "description",
            normalize_optional_text(self.description, _MAX_DESCRIPTION_LENGTH, "Description"),
        )
        object.__setattr__(
            self,
            "notes",
            normalize_optional_text(self.notes, _MAX_NOTES_LENGTH, "Notes"),
        )

    @classmethod
    def create(
        cls,
        *,
        workspace_id: WorkspaceId,
        member_kind: CollectionMemberKind,
        member_id: str,
        title: str | None = None,
        description: str | None = None,
        notes: str | None = None,
        now: datetime | None = None,
    ) -> ResourceMetadata:
        return cls(
            workspace_id=workspace_id,
            member_kind=member_kind,
            member_id=member_id,
            title=title,
            description=description,
            notes=notes,
            updated_at=now or datetime.now(UTC),
        )

    def with_fields(
        self,
        *,
        title: str | None = None,
        description: str | None = None,
        notes: str | None = None,
        now: datetime | None = None,
    ) -> ResourceMetadata:
        return replace(
            self,
            title=title,
            description=description,
            notes=notes,
            updated_at=now or datetime.now(UTC),
        )


def normalize_optional_text(value: str | None, max_length: int, label: str) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > max_length:
        raise InvalidResourceMetadataError(f"{label} must be at most {max_length} characters.")
    return normalized
