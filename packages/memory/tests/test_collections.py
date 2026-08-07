from datetime import UTC, datetime

import pytest
from fakes import InMemoryCollectionRepository
from memovi_memory.application.services import CollectionService
from memovi_memory.domain.exceptions import (
    CollectionMembershipNotFoundError,
    CollectionNotFoundError,
    DuplicateCollectionMembershipError,
    InvalidCollectionError,
)
from memovi_memory.domain.value_objects import CollectionMetadata
from memovi_shared import WorkspaceId

DOCUMENT_ID = "3b96152e-5ba9-4933-8819-2a08069a6d9f"
KNOWLEDGE_ID = "7ce3e814-de68-4200-973e-b2526eee058d"
OTHER_WORKSPACE = WorkspaceId("11111111-1111-4111-8111-111111111111")


def _service() -> tuple[CollectionService, InMemoryCollectionRepository]:
    repository = InMemoryCollectionRepository()
    return CollectionService(repository=repository), repository


def test_create_collection_assigns_metadata_and_activity() -> None:
    service, repository = _service()
    now = datetime(2026, 8, 7, 12, 0, tzinfo=UTC)
    created = service.create(
        workspace_id=WorkspaceId.default(),
        name="  Research  ",
        description=" Papers ",
        now=now,
    )
    assert created.name == "Research"
    assert created.description == "Papers"
    assert len(repository.activities) == 1
    assert repository.activities[0].activity_type == "created"


def test_collection_metadata_rejects_blank_name() -> None:
    with pytest.raises(InvalidCollectionError):
        CollectionMetadata(name="   ")


def test_rename_and_add_remove_members() -> None:
    service, _repository = _service()
    created = service.create(workspace_id=WorkspaceId.default(), name="Projects")
    renamed = service.rename(
        created.id,
        workspace_id=WorkspaceId.default(),
        name="Work",
    )
    assert renamed.name == "Work"

    membership = service.add_member(
        created.id,
        workspace_id=WorkspaceId.default(),
        member_kind="document",
        member_id=DOCUMENT_ID,
        reason="Primary project brief",
    )
    assert membership.reason == "Primary project brief"

    with pytest.raises(DuplicateCollectionMembershipError):
        service.add_member(
            created.id,
            workspace_id=WorkspaceId.default(),
            member_kind="document",
            member_id=DOCUMENT_ID,
        )

    service.add_member(
        created.id,
        workspace_id=WorkspaceId.default(),
        member_kind="knowledge",
        member_id=KNOWLEDGE_ID,
    )
    summary = service.summary(created.id, workspace_id=WorkspaceId.default())
    assert summary.item_count == 2
    assert summary.counts_by_kind["document"] == 1
    assert summary.counts_by_kind["knowledge"] == 1

    members = service.list_members(
        created.id,
        workspace_id=WorkspaceId.default(),
        query="brief",
    )
    assert len(members) == 1
    assert members[0].member_id == DOCUMENT_ID

    service.remove_member(
        created.id,
        workspace_id=WorkspaceId.default(),
        member_kind="document",
        member_id=DOCUMENT_ID,
    )
    with pytest.raises(CollectionMembershipNotFoundError):
        service.remove_member(
            created.id,
            workspace_id=WorkspaceId.default(),
            member_kind="document",
            member_id=DOCUMENT_ID,
        )


def test_collections_are_workspace_scoped() -> None:
    service, _repository = _service()
    created = service.create(workspace_id=WorkspaceId.default(), name="Personal")
    with pytest.raises(CollectionNotFoundError):
        service.get(created.id, workspace_id=OTHER_WORKSPACE)


def test_resolve_search_member_ids() -> None:
    service, _repository = _service()
    created = service.create(workspace_id=WorkspaceId.default(), name="School")
    service.add_member(
        created.id,
        workspace_id=WorkspaceId.default(),
        member_kind="document",
        member_id=DOCUMENT_ID,
    )
    service.add_member(
        created.id,
        workspace_id=WorkspaceId.default(),
        member_kind="knowledge",
        member_id=KNOWLEDGE_ID,
    )
    service.add_member(
        created.id,
        workspace_id=WorkspaceId.default(),
        member_kind="conversation",
        member_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    )
    document_ids, knowledge_ids = service.resolve_search_member_ids(
        created.id,
        workspace_id=WorkspaceId.default(),
    )
    assert document_ids == frozenset({DOCUMENT_ID})
    assert knowledge_ids == frozenset({KNOWLEDGE_ID})


def test_delete_collection_removes_memberships() -> None:
    service, repository = _service()
    created = service.create(workspace_id=WorkspaceId.default(), name="Temp")
    service.add_member(
        created.id,
        workspace_id=WorkspaceId.default(),
        member_kind="workflow",
        member_id="organize-inbox",
    )
    service.delete(created.id, workspace_id=WorkspaceId.default())
    assert repository.collections == {}
    assert repository.memberships == {}
    with pytest.raises(CollectionNotFoundError):
        service.get(created.id, workspace_id=WorkspaceId.default())
