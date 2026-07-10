from dataclasses import dataclass

from memovi_memory.application.exceptions import NoChunksGeneratedError
from memovi_memory.domain.repositories import ChunkRepository, KnowledgeRepository
from memovi_memory.domain.services import ChunkGenerator, KnowledgeMaterializer


@dataclass(frozen=True, slots=True)
class MaterializeKnowledgeCommand:
    document_id: str
    document_version_id: str
    normalized_text: str


@dataclass(frozen=True, slots=True)
class MaterializeKnowledgeResult:
    knowledge_item_id: str
    chunk_count: int


class MaterializeKnowledge:
    """Persists knowledge materialized from normalized document text."""

    def __init__(
        self,
        *,
        chunk_generator: ChunkGenerator,
        knowledge_materializer: KnowledgeMaterializer,
        knowledge_repository: KnowledgeRepository,
        chunk_repository: ChunkRepository,
    ) -> None:
        self._chunk_generator = chunk_generator
        self._knowledge_materializer = knowledge_materializer
        self._knowledge_repository = knowledge_repository
        self._chunk_repository = chunk_repository

    def execute(self, command: MaterializeKnowledgeCommand) -> MaterializeKnowledgeResult:
        chunk_drafts = self._chunk_generator.generate(command.normalized_text)
        if not chunk_drafts:
            raise NoChunksGeneratedError(
                "Normalized text did not produce any knowledge chunks.",
            )

        materialization = self._knowledge_materializer.materialize(
            document_id=command.document_id,
            document_version_id=command.document_version_id,
            chunk_drafts=chunk_drafts,
        )

        self._knowledge_repository.save(materialization.knowledge_item)
        self._chunk_repository.save_many(materialization.chunks)

        return MaterializeKnowledgeResult(
            knowledge_item_id=materialization.knowledge_item.id.value,
            chunk_count=len(materialization.chunks),
        )
