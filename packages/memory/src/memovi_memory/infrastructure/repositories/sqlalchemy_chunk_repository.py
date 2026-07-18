from datetime import UTC, datetime

from memovi_shared import WorkspaceId
from sqlalchemy.orm import Session as OrmSession

from memovi_memory.domain.entities import Chunk
from memovi_memory.domain.value_objects import ChunkId, ChunkIndex, KnowledgeItemId
from memovi_memory.infrastructure.persistence.models import ChunkRecord


class SqlAlchemyChunkRepository:
    def __init__(self, session: OrmSession) -> None:
        self._session = session

    def save_many(self, chunks: list[Chunk]) -> None:
        for chunk in chunks:
            record = self._session.get(ChunkRecord, chunk.id.value)
            if record is None:
                self._session.add(self._to_record(chunk))
                continue

            record.workspace_id = chunk.workspace_id.value
            record.knowledge_item_id = (
                chunk.knowledge_item_id.value if chunk.knowledge_item_id is not None else None
            )
            record.document_id = chunk.document_id
            record.document_version_id = chunk.document_version_id
            record.chunk_index = chunk.chunk_index.value
            record.text = chunk.text

    def list_by_document_version(
        self,
        *,
        document_id: str,
        document_version_id: str,
        workspace_id: WorkspaceId | None = None,
    ) -> list[Chunk]:
        query = self._session.query(ChunkRecord).filter(
            ChunkRecord.document_id == document_id,
            ChunkRecord.document_version_id == document_version_id,
        )
        if workspace_id is not None:
            query = query.filter(ChunkRecord.workspace_id == workspace_id.value)
        records = query.order_by(ChunkRecord.chunk_index.asc()).all()
        return [self._to_domain(record) for record in records]

    def delete_by_document_version(
        self,
        *,
        document_id: str,
        document_version_id: str,
        workspace_id: WorkspaceId | None = None,
    ) -> None:
        query = self._session.query(ChunkRecord).filter(
            ChunkRecord.document_id == document_id,
            ChunkRecord.document_version_id == document_version_id,
        )
        if workspace_id is not None:
            query = query.filter(ChunkRecord.workspace_id == workspace_id.value)
        query.delete()

    def _to_domain(self, record: ChunkRecord) -> Chunk:
        return Chunk(
            id=ChunkId(record.id),
            workspace_id=WorkspaceId(record.workspace_id),
            knowledge_item_id=(
                KnowledgeItemId(record.knowledge_item_id)
                if record.knowledge_item_id is not None
                else None
            ),
            document_id=record.document_id,
            document_version_id=record.document_version_id,
            chunk_index=ChunkIndex(record.chunk_index),
            text=record.text,
            created_at=_as_utc(record.created_at),
        )

    def _to_record(self, chunk: Chunk) -> ChunkRecord:
        return ChunkRecord(
            id=chunk.id.value,
            workspace_id=chunk.workspace_id.value,
            knowledge_item_id=(
                chunk.knowledge_item_id.value if chunk.knowledge_item_id is not None else None
            ),
            document_id=chunk.document_id,
            document_version_id=chunk.document_version_id,
            chunk_index=chunk.chunk_index.value,
            text=chunk.text,
            created_at=chunk.created_at,
        )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
