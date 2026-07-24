from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class RelationshipDto:
    """Provenance relationship between knowledge graph participants.

    Relationships describe why knowledge exists (document → knowledge → chunk),
    not inferred semantic edges.
    """

    id: str
    relationship_type: str
    from_kind: str
    from_id: str
    to_kind: str
    to_id: str
    workspace_id: str
    document_id: str
    knowledge_item_id: str | None
    created_at: datetime
