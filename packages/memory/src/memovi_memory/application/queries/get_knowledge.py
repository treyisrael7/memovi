from memovi_observability import get_metrics_recorder, timed_operation
from memovi_shared import WorkspaceId

from memovi_memory.application.dto import KnowledgeDto
from memovi_memory.application.exceptions import KnowledgeItemNotFoundError
from memovi_memory.domain.repositories import ChunkRepository, KnowledgeRepository
from memovi_memory.domain.value_objects import KnowledgeItemId


class GetKnowledge:
    """Returns canonical knowledge for a single knowledge item."""

    def __init__(
        self,
        *,
        knowledge_repository: KnowledgeRepository,
        chunk_repository: ChunkRepository,
    ) -> None:
        self._knowledge_repository = knowledge_repository
        self._chunk_repository = chunk_repository

    def execute(self, knowledge_item_id: str, *, workspace_id: WorkspaceId) -> KnowledgeDto:
        with timed_operation(
            "memory.lookup",
            metric_name="memovi.memory.lookup",
            attributes={"operation": "memory.lookup"},
        ):
            knowledge_item = self._knowledge_repository.get_by_id(
                KnowledgeItemId(knowledge_item_id),
                workspace_id=workspace_id,
            )
            if knowledge_item is None:
                raise KnowledgeItemNotFoundError("Knowledge item was not found.")

            chunks = self._chunk_repository.list_by_document_version(
                document_id=knowledge_item.document_id,
                document_version_id=knowledge_item.document_version_id,
                workspace_id=workspace_id,
            )
            get_metrics_recorder().increment("memovi.memory.lookup.count")
            return KnowledgeDto.from_knowledge_item_and_chunks(knowledge_item, chunks)
