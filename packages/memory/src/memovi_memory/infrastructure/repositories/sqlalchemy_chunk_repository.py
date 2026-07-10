from datetime import UTC, datetime

from sqlalchemy.orm import Session as OrmSession

from memovi_memory.domain.entities import Chunk
from memovi_memory.domain.value_objects import ChunkId, ChunkIndex, KnowledgeItemId
from memovi_memory.infrastructure.persistence.models import ChunkRecord


class SqlAlchemyChunkRepository:
    def __init__(self, session: OrmSession) -> None:
        self._session = session

    def get_by_id(self, chunk_id: ChunkId) -> Chunk | None:
        record = self._session.get(ChunkRecord, chunk_id.value)
        if record is None:
            return None
        return self._to_domain(record)

    def list_by_knowledge_item_id(self, knowledge_item_id: KnowledgeItemId) -> list[Chunk]:
        records = (
            self._session.query(ChunkRecord)
            .filter(ChunkRecord.knowledge_item_id == knowledge_item_id.value)
            .order_by(ChunkRecord.chunk_index.asc())
            .all()
        )
        return [self._to_domain(record) for record in records]

    def add(self, chunk: Chunk) -> None:
        self._session.add(self._to_record(chunk))

    def add_many(self, chunks: list[Chunk]) -> None:
        for chunk in chunks:
            self._session.add(self._to_record(chunk))

    def delete_by_knowledge_item_id(self, knowledge_item_id: KnowledgeItemId) -> None:
        (
            self._session.query(ChunkRecord)
            .filter(ChunkRecord.knowledge_item_id == knowledge_item_id.value)
            .delete()
        )

    def _to_domain(self, record: ChunkRecord) -> Chunk:
        return Chunk(
            id=ChunkId(record.id),
            knowledge_item_id=KnowledgeItemId(record.knowledge_item_id),
            index=ChunkIndex(record.chunk_index),
            content=record.content,
            created_at=_as_utc(record.created_at),
        )

    def _to_record(self, chunk: Chunk) -> ChunkRecord:
        return ChunkRecord(
            id=chunk.id.value,
            knowledge_item_id=chunk.knowledge_item_id.value,
            chunk_index=chunk.index.value,
            content=chunk.content,
            created_at=chunk.created_at,
        )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
