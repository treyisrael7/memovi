from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class KnowledgeMaterializedNotification:
    """Search-side notification that canonical knowledge was materialized."""

    knowledge_item_id: str
    document_id: str
    document_version_id: str
    occurred_at: datetime
