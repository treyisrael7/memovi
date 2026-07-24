from memovi_shared import WorkspaceId

from memovi_memory.application.dto import RelationshipDto
from memovi_memory.application.queries.list_knowledge import ListKnowledge


class ListRelationships:
    """Builds provenance relationships for Knowledge Explorer navigation."""

    def __init__(self, *, list_knowledge: ListKnowledge) -> None:
        self._list_knowledge = list_knowledge

    def execute(
        self,
        *,
        workspace_id: WorkspaceId,
        document_id: str | None = None,
        knowledge_item_id: str | None = None,
    ) -> list[RelationshipDto]:
        knowledge_items = self._list_knowledge.execute(workspace_id=workspace_id)
        relationships: list[RelationshipDto] = []

        for item in knowledge_items:
            if document_id is not None and item.document_id != document_id:
                continue
            if knowledge_item_id is not None and item.id != knowledge_item_id:
                continue

            relationships.append(
                RelationshipDto(
                    id=f"document_of:{item.document_id}:{item.id}",
                    relationship_type="document_of",
                    from_kind="knowledge_item",
                    from_id=item.id,
                    to_kind="document",
                    to_id=item.document_id,
                    workspace_id=item.workspace_id,
                    document_id=item.document_id,
                    knowledge_item_id=item.id,
                    created_at=item.created_at,
                )
            )

            for chunk in item.chunks:
                relationships.append(
                    RelationshipDto(
                        id=f"chunk_of:{item.id}:{chunk.id}",
                        relationship_type="chunk_of",
                        from_kind="chunk",
                        from_id=chunk.id,
                        to_kind="knowledge_item",
                        to_id=item.id,
                        workspace_id=item.workspace_id,
                        document_id=item.document_id,
                        knowledge_item_id=item.id,
                        created_at=chunk.created_at,
                    )
                )

        return relationships
