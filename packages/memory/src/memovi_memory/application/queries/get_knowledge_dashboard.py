from collections import Counter

from memovi_shared import WorkspaceId

from memovi_memory.application.dto import KnowledgeDashboardDto
from memovi_memory.application.queries.list_concepts import ListConcepts
from memovi_memory.application.queries.list_knowledge import ListKnowledge
from memovi_memory.application.queries.list_relationships import ListRelationships


class GetKnowledgeDashboard:
    """Aggregates workspace knowledge counts for the explorer overview."""

    def __init__(
        self,
        *,
        list_knowledge: ListKnowledge,
        list_concepts: ListConcepts,
        list_relationships: ListRelationships,
    ) -> None:
        self._list_knowledge = list_knowledge
        self._list_concepts = list_concepts
        self._list_relationships = list_relationships

    def execute(self, *, workspace_id: WorkspaceId) -> KnowledgeDashboardDto:
        knowledge_items = self._list_knowledge.execute(workspace_id=workspace_id)
        concepts = self._list_concepts.execute(workspace_id=workspace_id)
        relationships = self._list_relationships.execute(workspace_id=workspace_id)

        source_types = Counter(item.source_type for item in knowledge_items)
        mime_types = Counter(item.mime_type for item in knowledge_items)
        document_ids = {item.document_id for item in knowledge_items}
        chunk_count = sum(len(item.chunks) for item in knowledge_items)

        return KnowledgeDashboardDto(
            workspace_id=workspace_id.value,
            knowledge_item_count=len(knowledge_items),
            chunk_count=chunk_count,
            source_document_count=len(document_ids),
            concept_count=len(concepts),
            relationship_count=len(relationships),
            source_type_counts=dict(sorted(source_types.items())),
            mime_type_counts=dict(sorted(mime_types.items())),
        )
