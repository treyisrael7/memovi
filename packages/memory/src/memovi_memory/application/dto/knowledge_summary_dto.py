from dataclasses import dataclass
from datetime import datetime

from memovi_memory.application.dto.knowledge_dto import KnowledgeDto


@dataclass(frozen=True, slots=True)
class KnowledgeSummaryDto:
    """List-oriented knowledge projection for inspection surfaces."""

    id: str
    workspace_id: str
    document_id: str
    document_version_id: str
    source_type: str
    mime_type: str
    created_at: datetime
    updated_at: datetime
    chunk_count: int
    summary: str
    confidence: float | None

    @classmethod
    def from_knowledge(cls, knowledge: KnowledgeDto, *, summary_limit: int = 280) -> "KnowledgeSummaryDto":
        preview = ""
        if knowledge.chunks:
            preview = knowledge.chunks[0].text.strip()
            if len(preview) > summary_limit:
                preview = f"{preview[: summary_limit - 1].rstrip()}…"
        return cls(
            id=knowledge.id,
            workspace_id=knowledge.workspace_id,
            document_id=knowledge.document_id,
            document_version_id=knowledge.document_version_id,
            source_type=knowledge.source_type,
            mime_type=knowledge.mime_type,
            created_at=knowledge.created_at,
            updated_at=knowledge.updated_at,
            chunk_count=len(knowledge.chunks),
            summary=preview,
            confidence=None,
        )
