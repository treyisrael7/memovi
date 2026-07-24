from datetime import UTC, datetime

from memovi_shared import WorkspaceId

from memovi_memory.application.dto import ChunkDto, KnowledgeDto
from memovi_memory.application.queries.get_knowledge_dashboard import GetKnowledgeDashboard
from memovi_memory.application.queries.list_concepts import ListConcepts
from memovi_memory.application.queries.list_relationships import ListRelationships


class _FakeListKnowledge:
    def __init__(self, items: list[KnowledgeDto]) -> None:
        self._items = items

    def execute(self, *, workspace_id: WorkspaceId) -> list[KnowledgeDto]:
        assert workspace_id == WorkspaceId.default()
        return list(self._items)


def _knowledge(
    *,
    knowledge_id: str,
    document_id: str,
    source_type: str = "upload",
    mime_type: str = "text/markdown",
    chunk_text: str = "Memovi stores durable knowledge.",
) -> KnowledgeDto:
    now = datetime(2026, 7, 24, 12, 0, tzinfo=UTC)
    return KnowledgeDto(
        id=knowledge_id,
        workspace_id=WorkspaceId.default().value,
        document_id=document_id,
        document_version_id="version-1",
        source_type=source_type,
        mime_type=mime_type,
        created_at=now,
        updated_at=now,
        chunks=(
            ChunkDto(
                id=f"chunk-{knowledge_id}",
                knowledge_item_id=knowledge_id,
                document_id=document_id,
                document_version_id="version-1",
                chunk_index=0,
                text=chunk_text,
                created_at=now,
            ),
        ),
    )


def test_list_concepts_groups_source_and_mime_types() -> None:
    items = [
        _knowledge(knowledge_id="k1", document_id="d1", source_type="upload"),
        _knowledge(
            knowledge_id="k2",
            document_id="d2",
            source_type="import",
            mime_type="application/pdf",
        ),
    ]
    concepts = ListConcepts(list_knowledge=_FakeListKnowledge(items)).execute(
        workspace_id=WorkspaceId.default(),
    )
    ids = {concept.id for concept in concepts}
    assert "source_type:upload" in ids
    assert "source_type:import" in ids
    assert "mime_type:text/markdown" in ids
    assert "mime_type:application/pdf" in ids


def test_list_relationships_builds_document_and_chunk_edges() -> None:
    items = [_knowledge(knowledge_id="k1", document_id="d1")]
    relationships = ListRelationships(list_knowledge=_FakeListKnowledge(items)).execute(
        workspace_id=WorkspaceId.default(),
    )
    types = {rel.relationship_type for rel in relationships}
    assert types == {"document_of", "chunk_of"}
    assert any(rel.to_id == "d1" for rel in relationships)


def test_dashboard_counts_workspace_knowledge() -> None:
    items = [
        _knowledge(knowledge_id="k1", document_id="d1"),
        _knowledge(knowledge_id="k2", document_id="d1", mime_type="text/plain"),
    ]
    list_knowledge = _FakeListKnowledge(items)
    list_concepts = ListConcepts(list_knowledge=list_knowledge)
    list_relationships = ListRelationships(list_knowledge=list_knowledge)
    dashboard = GetKnowledgeDashboard(
        list_knowledge=list_knowledge,
        list_concepts=list_concepts,
        list_relationships=list_relationships,
    ).execute(workspace_id=WorkspaceId.default())

    assert dashboard.knowledge_item_count == 2
    assert dashboard.chunk_count == 2
    assert dashboard.source_document_count == 1
    assert dashboard.concept_count >= 2
    assert dashboard.relationship_count == 4
