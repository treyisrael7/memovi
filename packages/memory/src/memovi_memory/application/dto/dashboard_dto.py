from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KnowledgeDashboardDto:
    """Workspace-scoped inspection counts for the Knowledge Explorer overview."""

    workspace_id: str
    knowledge_item_count: int
    chunk_count: int
    source_document_count: int
    concept_count: int
    relationship_count: int
    source_type_counts: dict[str, int]
    mime_type_counts: dict[str, int]
