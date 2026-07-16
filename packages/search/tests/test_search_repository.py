from datetime import UTC, datetime

from memovi_search.domain.entities import SearchDocument
from memovi_search.domain.value_objects import SearchDocumentId
from memovi_search.infrastructure.repositories import SqlAlchemySearchRepository
from postgres_support import build_postgres_session_factory, requires_postgres

DOCUMENT_ID = "d62fa912-48a9-4d57-abf2-40a137f48ffa"
DOCUMENT_VERSION_ID = "7d086319-ee8e-4fe5-9fc3-30eddad79749"
OTHER_DOCUMENT_ID = "e73ab023-59ba-5e68-bc03-51b248f59a0b"
OTHER_DOCUMENT_VERSION_ID = "8e19742a-ff9f-5af6-a1d4-41feebe8a85a"
KNOWLEDGE_ITEM_ID = "f1e2d3c4-b5a6-9788-7654-3210fedcba98"
OTHER_KNOWLEDGE_ITEM_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
THIRD_KNOWLEDGE_ITEM_ID = "b2c3d4e5-f6a7-8901-bcde-f12345678901"
SOURCE_TYPE = "upload"
MIME_TYPE = "text/markdown"
EARLY = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
MID = datetime(2026, 7, 13, 12, 0, tzinfo=UTC)
LATE = datetime(2026, 7, 15, 12, 0, tzinfo=UTC)


def _build_search_document(
    *,
    knowledge_item_id: str,
    searchable_text: str,
    document_id: str = DOCUMENT_ID,
    document_version_id: str = DOCUMENT_VERSION_ID,
    source_type: str = SOURCE_TYPE,
    mime_type: str = MIME_TYPE,
    created_at: datetime = MID,
) -> SearchDocument:
    return SearchDocument(
        id=SearchDocumentId.new(),
        knowledge_item_id=knowledge_item_id,
        document_id=document_id,
        document_version_id=document_version_id,
        source_type=source_type,
        mime_type=mime_type,
        searchable_text=searchable_text,
        created_at=created_at,
        updated_at=created_at,
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
        source_type=search_document.source_type,
        mime_type=search_document.mime_type,
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


def _seed_filterable_documents(
    session_factory: object,
) -> tuple[SearchDocument, SearchDocument, SearchDocument]:
    markdown_upload = _build_search_document(
        knowledge_item_id=KNOWLEDGE_ITEM_ID,
        searchable_text="Memovi markdown upload notes.",
        document_id=DOCUMENT_ID,
        document_version_id=DOCUMENT_VERSION_ID,
        source_type="upload",
        mime_type="text/markdown",
        created_at=EARLY,
    )
    plain_connector = _build_search_document(
        knowledge_item_id=OTHER_KNOWLEDGE_ITEM_ID,
        searchable_text="Memovi plain connector notes.",
        document_id=OTHER_DOCUMENT_ID,
        document_version_id=OTHER_DOCUMENT_VERSION_ID,
        source_type="connector",
        mime_type="text/plain",
        created_at=MID,
    )
    pdf_upload = _build_search_document(
        knowledge_item_id=THIRD_KNOWLEDGE_ITEM_ID,
        searchable_text="Memovi pdf upload notes.",
        document_id="f84bc134-6acb-4f79-cd14-62c359a6ab1c",
        document_version_id="9f2a853b-0aa0-4a97-b1e5-52affcf9b96b",
        source_type="upload",
        mime_type="application/pdf",
        created_at=LATE,
    )

    with session_factory() as session:  # type: ignore[operator]
        repository = SqlAlchemySearchRepository(session)
        repository.save_document(markdown_upload)
        repository.save_document(plain_connector)
        repository.save_document(pdf_upload)
        session.commit()

    return markdown_upload, plain_connector, pdf_upload


@requires_postgres
def test_search_repository_filters_by_document_id() -> None:
    session_factory, engine = build_postgres_session_factory()
    markdown_upload, _, _ = _seed_filterable_documents(session_factory)

    with session_factory() as session:
        repository = SqlAlchemySearchRepository(session)
        results = repository.search("Memovi", limit=10, offset=0, document_id=DOCUMENT_ID)

        assert len(results) == 1
        assert results[0].search_document.id == markdown_upload.id

    engine.dispose()


@requires_postgres
def test_search_repository_filters_by_document_version_id() -> None:
    session_factory, engine = build_postgres_session_factory()
    _, plain_connector, _ = _seed_filterable_documents(session_factory)

    with session_factory() as session:
        repository = SqlAlchemySearchRepository(session)
        results = repository.search(
            "Memovi",
            limit=10,
            offset=0,
            document_version_id=OTHER_DOCUMENT_VERSION_ID,
        )

        assert len(results) == 1
        assert results[0].search_document.id == plain_connector.id

    engine.dispose()


@requires_postgres
def test_search_repository_filters_by_source_type() -> None:
    session_factory, engine = build_postgres_session_factory()
    _, plain_connector, _ = _seed_filterable_documents(session_factory)

    with session_factory() as session:
        repository = SqlAlchemySearchRepository(session)
        results = repository.search("Memovi", limit=10, offset=0, source_type="connector")

        assert len(results) == 1
        assert results[0].search_document.id == plain_connector.id

    engine.dispose()


@requires_postgres
def test_search_repository_filters_by_mime_type() -> None:
    session_factory, engine = build_postgres_session_factory()
    markdown_upload, _, _ = _seed_filterable_documents(session_factory)

    with session_factory() as session:
        repository = SqlAlchemySearchRepository(session)
        results = repository.search("Memovi", limit=10, offset=0, mime_type="text/markdown")

        assert len(results) == 1
        assert results[0].search_document.id == markdown_upload.id

    engine.dispose()


@requires_postgres
def test_search_repository_filters_by_created_after() -> None:
    session_factory, engine = build_postgres_session_factory()
    _, plain_connector, pdf_upload = _seed_filterable_documents(session_factory)

    with session_factory() as session:
        repository = SqlAlchemySearchRepository(session)
        results = repository.search("Memovi", limit=10, offset=0, created_after=MID)

        assert {result.search_document.id for result in results} == {
            plain_connector.id,
            pdf_upload.id,
        }

    engine.dispose()


@requires_postgres
def test_search_repository_filters_by_created_before() -> None:
    session_factory, engine = build_postgres_session_factory()
    markdown_upload, plain_connector, _ = _seed_filterable_documents(session_factory)

    with session_factory() as session:
        repository = SqlAlchemySearchRepository(session)
        results = repository.search("Memovi", limit=10, offset=0, created_before=MID)

        assert {result.search_document.id for result in results} == {
            markdown_upload.id,
            plain_connector.id,
        }

    engine.dispose()


@requires_postgres
def test_search_repository_filters_combine_mime_type_and_source_type() -> None:
    session_factory, engine = build_postgres_session_factory()
    markdown_upload, _, _ = _seed_filterable_documents(session_factory)

    with session_factory() as session:
        repository = SqlAlchemySearchRepository(session)
        results = repository.search(
            "Memovi",
            limit=10,
            offset=0,
            source_type="upload",
            mime_type="text/markdown",
        )

        assert len(results) == 1
        assert results[0].search_document.id == markdown_upload.id

    engine.dispose()


@requires_postgres
def test_search_repository_filters_combine_document_id_and_date_range() -> None:
    session_factory, engine = build_postgres_session_factory()
    markdown_upload, _, _ = _seed_filterable_documents(session_factory)

    with session_factory() as session:
        repository = SqlAlchemySearchRepository(session)
        results = repository.search(
            "Memovi",
            limit=10,
            offset=0,
            document_id=DOCUMENT_ID,
            created_after=EARLY,
            created_before=MID,
        )

        assert len(results) == 1
        assert results[0].search_document.id == markdown_upload.id

        empty = repository.search(
            "Memovi",
            limit=10,
            offset=0,
            document_id=DOCUMENT_ID,
            created_after=LATE,
        )
        assert empty == []

    engine.dispose()
