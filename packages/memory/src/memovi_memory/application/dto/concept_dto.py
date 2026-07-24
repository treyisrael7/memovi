from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConceptDto:
    """Structural concept grouping derived from durable knowledge metadata.

    Concepts here are inspection projections (source type / MIME type), not
    NLP-extracted topics. Semantic concept extraction remains a future pipeline stage.
    """

    id: str
    kind: str
    label: str
    knowledge_item_count: int
    knowledge_item_ids: tuple[str, ...]
