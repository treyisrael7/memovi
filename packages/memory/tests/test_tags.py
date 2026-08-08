from datetime import UTC, datetime

import pytest
from fakes import InMemoryResourceMetadataRepository, InMemoryTagRepository
from memovi_memory.application.services import ResourceMetadataService, TagService
from memovi_memory.domain.entities import Tag
from memovi_memory.domain.exceptions import (
    DuplicateTagAssignmentError,
    DuplicateTagNameError,
    InvalidTagError,
    ResourceMetadataNotFoundError,
    TagAssignmentNotFoundError,
    TagNotFoundError,
)
from memovi_shared import WorkspaceId

DOCUMENT_A = "3b96152e-5ba9-4933-8819-2a08069a6d9f"
DOCUMENT_B = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
DOCUMENT_C = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
KNOWLEDGE_A = "7ce3e814-de68-4200-973e-b2526eee058d"
KNOWLEDGE_B = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
OTHER_WORKSPACE = WorkspaceId("11111111-1111-4111-8111-111111111111")


def _tag_service() -> tuple[TagService, InMemoryTagRepository]:
    repository = InMemoryTagRepository()
    return TagService(repository=repository), repository


def _metadata_service() -> tuple[ResourceMetadataService, InMemoryResourceMetadataRepository]:
    repository = InMemoryResourceMetadataRepository()
    return ResourceMetadataService(repository=repository), repository


def test_create_tag_normalizes_fields() -> None:
    service, _repository = _tag_service()
    now = datetime(2026, 8, 8, 12, 0, tzinfo=UTC)
    created = service.create(
        workspace_id=WorkspaceId.default(),
        name="  Research  ",
        color="  #336699  ",
        description=" Papers ",
        now=now,
    )
    assert created.name == "Research"
    assert created.color == "#336699"
    assert created.description == "Papers"


def test_tag_rejects_blank_name() -> None:
    with pytest.raises(InvalidTagError):
        Tag.create(workspace_id=WorkspaceId.default(), name="   ")


def test_rename_uniqueness_is_case_insensitive() -> None:
    service, _repository = _tag_service()
    created = service.create(workspace_id=WorkspaceId.default(), name="Alpha")
    service.create(workspace_id=WorkspaceId.default(), name="Beta")

    with pytest.raises(DuplicateTagNameError):
        service.create(workspace_id=WorkspaceId.default(), name=" alpha ")

    with pytest.raises(DuplicateTagNameError):
        service.update(created.id, workspace_id=WorkspaceId.default(), name="BETA")

    renamed = service.update(created.id, workspace_id=WorkspaceId.default(), name="Alpha Prime")
    assert renamed.name == "Alpha Prime"


def test_assign_remove_and_list_counts() -> None:
    service, _repository = _tag_service()
    created = service.create(
        workspace_id=WorkspaceId.default(),
        name="Priority",
        color="#ff0000",
    )
    assignment = service.assign(
        created.id,
        workspace_id=WorkspaceId.default(),
        member_kind="document",
        member_id=DOCUMENT_A,
    )
    assert assignment.member_id == DOCUMENT_A

    with pytest.raises(DuplicateTagAssignmentError):
        service.assign(
            created.id,
            workspace_id=WorkspaceId.default(),
            member_kind="document",
            member_id=DOCUMENT_A,
        )

    service.assign(
        created.id,
        workspace_id=WorkspaceId.default(),
        member_kind="knowledge",
        member_id=KNOWLEDGE_A,
    )
    listed = service.list(workspace_id=WorkspaceId.default())
    assert len(listed) == 1
    assert listed[0].assignment_count == 2
    assert listed[0].counts_by_kind["document"] == 1
    assert listed[0].counts_by_kind["knowledge"] == 1

    service.unassign(
        created.id,
        workspace_id=WorkspaceId.default(),
        member_kind="document",
        member_id=DOCUMENT_A,
    )
    with pytest.raises(TagAssignmentNotFoundError):
        service.unassign(
            created.id,
            workspace_id=WorkspaceId.default(),
            member_kind="document",
            member_id=DOCUMENT_A,
        )


def test_delete_tag_removes_assignments_only() -> None:
    service, repository = _tag_service()
    created = service.create(workspace_id=WorkspaceId.default(), name="Temp")
    service.assign(
        created.id,
        workspace_id=WorkspaceId.default(),
        member_kind="document",
        member_id=DOCUMENT_A,
    )
    service.delete(created.id, workspace_id=WorkspaceId.default())
    assert repository.tags == {}
    assert repository.assignments == {}
    with pytest.raises(TagNotFoundError):
        service.get(created.id, workspace_id=WorkspaceId.default())


def test_suggest_and_list_for_target() -> None:
    service, _repository = _tag_service()
    service.create(workspace_id=WorkspaceId.default(), name="Python")
    service.create(workspace_id=WorkspaceId.default(), name="PyTorch")
    service.create(workspace_id=WorkspaceId.default(), name="Rust")
    suggestions = service.suggest(workspace_id=WorkspaceId.default(), query="py")
    assert [item.name for item in suggestions] == ["Python", "PyTorch"]

    tag = service.create(workspace_id=WorkspaceId.default(), name="Inbox")
    service.assign(
        tag.id,
        workspace_id=WorkspaceId.default(),
        member_kind="document",
        member_id=DOCUMENT_A,
    )
    for_target = service.list_for_target(
        workspace_id=WorkspaceId.default(),
        member_kind="document",
        member_id=DOCUMENT_A,
    )
    assert [item.name for item in for_target] == ["Inbox"]


def test_resolve_search_member_ids_and_intersection() -> None:
    service, _repository = _tag_service()
    tag_a = service.create(workspace_id=WorkspaceId.default(), name="A")
    tag_b = service.create(workspace_id=WorkspaceId.default(), name="B")

    service.assign(
        tag_a.id,
        workspace_id=WorkspaceId.default(),
        member_kind="document",
        member_id=DOCUMENT_A,
    )
    service.assign(
        tag_a.id,
        workspace_id=WorkspaceId.default(),
        member_kind="document",
        member_id=DOCUMENT_B,
    )
    service.assign(
        tag_a.id,
        workspace_id=WorkspaceId.default(),
        member_kind="knowledge",
        member_id=KNOWLEDGE_A,
    )
    service.assign(
        tag_a.id,
        workspace_id=WorkspaceId.default(),
        member_kind="knowledge",
        member_id=KNOWLEDGE_B,
    )

    service.assign(
        tag_b.id,
        workspace_id=WorkspaceId.default(),
        member_kind="document",
        member_id=DOCUMENT_B,
    )
    service.assign(
        tag_b.id,
        workspace_id=WorkspaceId.default(),
        member_kind="document",
        member_id=DOCUMENT_C,
    )
    service.assign(
        tag_b.id,
        workspace_id=WorkspaceId.default(),
        member_kind="knowledge",
        member_id=KNOWLEDGE_B,
    )

    single_docs, single_knowledge = service.resolve_search_member_ids(
        [tag_a.id],
        workspace_id=WorkspaceId.default(),
    )
    assert single_docs == frozenset({DOCUMENT_A, DOCUMENT_B})
    assert single_knowledge == frozenset({KNOWLEDGE_A, KNOWLEDGE_B})

    docs, knowledge = service.resolve_search_member_ids(
        [tag_a.id, tag_b.id],
        workspace_id=WorkspaceId.default(),
    )
    assert docs == frozenset({DOCUMENT_B})
    assert knowledge == frozenset({KNOWLEDGE_B})


def test_tags_are_workspace_scoped() -> None:
    service, _repository = _tag_service()
    created = service.create(workspace_id=WorkspaceId.default(), name="Personal")
    with pytest.raises(TagNotFoundError):
        service.get(created.id, workspace_id=OTHER_WORKSPACE)


def test_resource_metadata_upsert() -> None:
    service, _repository = _metadata_service()
    with pytest.raises(ResourceMetadataNotFoundError):
        service.get(
            workspace_id=WorkspaceId.default(),
            member_kind="document",
            member_id=DOCUMENT_A,
        )

    created = service.upsert(
        workspace_id=WorkspaceId.default(),
        member_kind="document",
        member_id=DOCUMENT_A,
        title=" Brief ",
        description=" Overview ",
        notes=" Keep ",
    )
    assert created.title == "Brief"
    assert created.description == "Overview"
    assert created.notes == "Keep"

    updated = service.upsert(
        workspace_id=WorkspaceId.default(),
        member_kind="document",
        member_id=DOCUMENT_A,
        title="Revised",
        description=None,
        notes="Updated notes",
    )
    assert updated.title == "Revised"
    assert updated.description is None
    assert updated.notes == "Updated notes"

    loaded = service.get(
        workspace_id=WorkspaceId.default(),
        member_kind="document",
        member_id=DOCUMENT_A,
    )
    assert loaded.title == "Revised"
