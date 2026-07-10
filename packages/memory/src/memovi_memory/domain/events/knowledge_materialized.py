from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class KnowledgeMaterialized:
    """Domain fact emitted after knowledge is materialized from a processed document."""

    knowledge_item_id: str
    document_id: str
    document_version_id: str
    chunk_count: int
    occurred_at: datetime
