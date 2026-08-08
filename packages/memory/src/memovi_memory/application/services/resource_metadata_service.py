from collections.abc import Callable
from datetime import UTC, datetime

from memovi_shared import WorkspaceId

from memovi_memory.application.dto.resource_metadata_dto import ResourceMetadataDto
from memovi_memory.domain.entities import ResourceMetadata
from memovi_memory.domain.exceptions import ResourceMetadataNotFoundError
from memovi_memory.domain.repositories import ResourceMetadataRepository
from memovi_memory.domain.value_objects import parse_member_kind

EventPublisher = Callable[[object], None]


class ResourceMetadataService:
    """Application service for polymorphic resource metadata upserts."""

    def __init__(
        self,
        *,
        repository: ResourceMetadataRepository,
        publish: EventPublisher | None = None,
    ) -> None:
        self._repository = repository
        self._publish = publish

    def get(
        self,
        *,
        workspace_id: WorkspaceId,
        member_kind: str,
        member_id: str,
    ) -> ResourceMetadataDto:
        kind = parse_member_kind(member_kind)
        metadata = self._repository.get(
            workspace_id=workspace_id,
            member_kind=kind,
            member_id=member_id.strip(),
        )
        if metadata is None:
            raise ResourceMetadataNotFoundError(
                f"Metadata for {kind.value} {member_id.strip()} was not found.",
            )
        return ResourceMetadataDto.from_metadata(metadata)

    def upsert(
        self,
        *,
        workspace_id: WorkspaceId,
        member_kind: str,
        member_id: str,
        title: str | None = None,
        description: str | None = None,
        notes: str | None = None,
        now: datetime | None = None,
    ) -> ResourceMetadataDto:
        kind = parse_member_kind(member_kind)
        timestamp = now or datetime.now(UTC)
        existing = self._repository.get(
            workspace_id=workspace_id,
            member_kind=kind,
            member_id=member_id.strip(),
        )
        if existing is None:
            metadata = ResourceMetadata.create(
                workspace_id=workspace_id,
                member_kind=kind,
                member_id=member_id,
                title=title,
                description=description,
                notes=notes,
                now=timestamp,
            )
        else:
            metadata = existing.with_fields(
                title=title,
                description=description,
                notes=notes,
                now=timestamp,
            )
        self._repository.upsert(metadata)
        return ResourceMetadataDto.from_metadata(metadata)
