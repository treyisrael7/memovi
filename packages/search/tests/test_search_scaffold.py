from memovi_search.application.dto import EmbeddingDto, SearchDocumentDto
from memovi_search.domain.entities import Embedding, SearchDocument
from memovi_search.infrastructure.persistence.models import (
    Base,
    SearchDocumentRecord,
    SearchEmbeddingRecord,
)

DOCUMENT_ID = "3b96152e-5ba9-4933-8819-2a08069a6d9f"
DOCUMENT_VERSION_ID = "7ce3e814-de68-4200-973e-b2526eee058d"
KNOWLEDGE_ITEM_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


def test_dtos_map_from_domain_entities() -> None:
    search_document = SearchDocument.create(
        knowledge_item_id=KNOWLEDGE_ITEM_ID,
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        searchable_text="Retrievable passage.",
    )
    embedding = Embedding.create(
        search_document_id=search_document.id,
        provider="openai",
        model="text-embedding-3-small",
        vector=[0.1, 0.2],
    )

    search_document_dto = SearchDocumentDto.from_search_document(search_document)
    embedding_dto = EmbeddingDto.from_embedding(embedding)

    assert search_document_dto.knowledge_item_id == KNOWLEDGE_ITEM_ID
    assert search_document_dto.searchable_text == "Retrievable passage."
    assert embedding_dto.provider == "openai"
    assert embedding_dto.vector == [0.1, 0.2]


def test_persistence_models_declare_expected_tables() -> None:
    assert SearchDocumentRecord.__tablename__ == "search_documents"
    assert SearchEmbeddingRecord.__tablename__ == "search_embeddings"
    assert Base.metadata.tables["search_documents"] is not None
    assert Base.metadata.tables["search_embeddings"] is not None
