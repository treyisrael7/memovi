from dataclasses import dataclass

from memovi_search.domain.repositories import SearchRepository
from memovi_search.domain.services import SearchMaterializer


@dataclass(frozen=True, slots=True)
class MaterializeSearchDocumentCommand:
    knowledge_item_id: str
    document_id: str
    document_version_id: str
    chunk_texts: list[str]


@dataclass(frozen=True, slots=True)
class MaterializeSearchDocumentResult:
    search_document_id: str


class MaterializeSearchDocument:
    """Persists a search document materialized from canonical chunk text."""

    def __init__(
        self,
        *,
        search_materializer: SearchMaterializer,
        search_repository: SearchRepository,
    ) -> None:
        self._search_materializer = search_materializer
        self._search_repository = search_repository

    def execute(
        self,
        command: MaterializeSearchDocumentCommand,
    ) -> MaterializeSearchDocumentResult:
        search_document = self._search_materializer.materialize(
            knowledge_item_id=command.knowledge_item_id,
            document_id=command.document_id,
            document_version_id=command.document_version_id,
            chunk_texts=command.chunk_texts,
        )
        self._search_repository.save_document(search_document)

        return MaterializeSearchDocumentResult(
            search_document_id=search_document.id.value,
        )
