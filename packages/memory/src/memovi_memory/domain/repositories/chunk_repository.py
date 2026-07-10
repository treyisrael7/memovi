from typing import Protocol

from memovi_memory.domain.entities import Chunk


class ChunkRepository(Protocol):
    """Persistence contract for knowledge chunks."""

    def save_many(self, chunks: list[Chunk]) -> None:
        raise NotImplementedError

    def list_by_document_version(
        self,
        *,
        document_id: str,
        document_version_id: str,
    ) -> list[Chunk]:
        raise NotImplementedError

    def delete_by_document_version(
        self,
        *,
        document_id: str,
        document_version_id: str,
    ) -> None:
        raise NotImplementedError
