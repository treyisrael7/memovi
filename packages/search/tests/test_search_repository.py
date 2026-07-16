from datetime import UTC, datetime

from memovi_search.domain.entities import SearchDocument
from memovi_search.domain.value_objects import SearchDocumentId
from memovi_search.infrastructure.repositories import SqlAlchemySearchRepository
from postgres_support import build_postgres_session_factory, requires_postgres

DOCUMENT_ID = "d62fa912-48a9-4d57-abf2-40a137f48ffa"
DOCUMENT_VERSION_ID = "7d086319-ee8e-4fe5-9fc3-30eddad79749"
KNOWLEDGE_ITEM_ID = "f1e2d3c4-b5a6-9788-7654-3210fedcba98"
OTHER_KNOWLEDGE_ITEM_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


def _build_search_document(
    *,
    knowledge_item_id: str,
    searchable_text: str,
) -> SearchDocument:
    timestamp = datetime(2026, 7, 13, 12, 0, tzinfo=UTC)
    return SearchDocument(
        id=SearchDocumentId.new(),
        knowledge_item_id=knowledge_item_id,
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        searchable_text=searchable_text,
        created_at=timestamp,
        updated_at=timestamp,
    )


@requires_postgres
def test_search_repository_returns_matches_ranked_by_relevance() -> None:
    session_factory, engine = build_postgres_session_factory()
    memovi_document = _build_search_document(
        knowledge_item_id=KNOWLEDGE_ITEM_ID,
        searchable_text="Memovi is a self-hosted knowledge platform.",
    )
    other_document = _build_search_document(
        knowledge_item_id=OTHER_KNOWLEDGE_ITEM_ID,
        searchable_text="Unrelated notes about gardening.",
    )

    with session_factory() as session:
        repository = SqlAlchemySearchRepository(session)
        repository.save_document(memovi_document)
        repository.save_document(other_document)
        session.commit()

    with session_factory() as session:
        repository = SqlAlchemySearchRepository(session)
        results = repository.search("Memovi", limit=10, offset=0)

        assert len(results) == 1
        assert results[0].search_document.knowledge_item_id == KNOWLEDGE_ITEM_ID
        assert results[0].search_document.searchable_text == memovi_document.searchable_text
        assert results[0].relevance_score > 0

    engine.dispose()


@requires_postgres
def test_search_repository_returns_empty_results_for_missing_term() -> None:
    session_factory, engine = build_postgres_session_factory()
    search_document = _build_search_document(
        knowledge_item_id=KNOWLEDGE_ITEM_ID,
        searchable_text="Memovi is a self-hosted knowledge platform.",
    )

    with session_factory() as session:
        repository = SqlAlchemySearchRepository(session)
        repository.save_document(search_document)
        session.commit()

    with session_factory() as session:
        repository = SqlAlchemySearchRepository(session)
        assert repository.search("missing-term", limit=10, offset=0) == []

    engine.dispose()


@requires_postgres
def test_search_repository_applies_limit_and_offset() -> None:
    session_factory, engine = build_postgres_session_factory()
    documents = [
        _build_search_document(
            knowledge_item_id=f"a1b2c3d4-e5f6-7890-abcd-ef12345678{index:02d}",
            searchable_text=f"Memovi document {index}.",
        )
        for index in range(3)
    ]

    with session_factory() as session:
        repository = SqlAlchemySearchRepository(session)
        for document in documents:
            repository.save_document(document)
        session.commit()

    with session_factory() as session:
        repository = SqlAlchemySearchRepository(session)
        first_page = repository.search("Memovi", limit=1, offset=0)
        second_page = repository.search("Memovi", limit=1, offset=1)

        assert len(first_page) == 1
        assert len(second_page) == 1
        assert first_page[0].search_document.id != second_page[0].search_document.id

    engine.dispose()


@requires_postgres
def test_search_repository_updates_tsvector_when_document_is_saved_again() -> None:
    session_factory, engine = build_postgres_session_factory()
    search_document = _build_search_document(
        knowledge_item_id=KNOWLEDGE_ITEM_ID,
        searchable_text="Initial content without the target term.",
    )

    with session_factory() as session:
        repository = SqlAlchemySearchRepository(session)
        repository.save_document(search_document)
        session.commit()

    with session_factory() as session:
        repository = SqlAlchemySearchRepository(session)
        assert repository.search("Memovi", limit=10, offset=0) == []

    updated = SearchDocument(
        id=search_document.id,
        knowledge_item_id=search_document.knowledge_item_id,
        document_id=search_document.document_id,
        document_version_id=search_document.document_version_id,
        searchable_text="Updated Memovi searchable text.",
        created_at=search_document.created_at,
        updated_at=datetime(2026, 7, 13, 13, 0, tzinfo=UTC),
    )

    with session_factory() as session:
        repository = SqlAlchemySearchRepository(session)
        repository.save_document(updated)
        session.commit()

    with session_factory() as session:
        repository = SqlAlchemySearchRepository(session)
        results = repository.search("Memovi", limit=10, offset=0)

        assert len(results) == 1
        assert results[0].search_document.searchable_text == "Updated Memovi searchable text."

    engine.dispose()
