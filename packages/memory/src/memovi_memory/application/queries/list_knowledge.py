from memovi_memory.application.dto import KnowledgeDto
from memovi_memory.domain.entities import KnowledgeItem
from memovi_memory.domain.repositories import ChunkRepository, KnowledgeRepository


class ListKnowledge:
    """Returns canonical knowledge for all materialized knowledge items."""

    def __init__(
        self,
        *,
        knowledge_repository: KnowledgeRepository,
        chunk_repository: ChunkRepository,
    ) -> None:
        self._knowledge_repository = knowledge_repository
        self._chunk_repository = chunk_repository

    def execute(self) -> list[KnowledgeDto]:
        return [
            self._to_dto(knowledge_item) for knowledge_item in self._knowledge_repository.list()
        ]

    def _to_dto(self, knowledge_item: KnowledgeItem) -> KnowledgeDto:
        chunks = self._chunk_repository.list_by_document_version(
            document_id=knowledge_item.document_id,
            document_version_id=knowledge_item.document_version_id,
        )
        return KnowledgeDto.from_knowledge_item_and_chunks(knowledge_item, chunks)
