from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from api.app import create_app
from fastapi.testclient import TestClient
from memovi_search.api.dependencies import get_retrieve_knowledge
from memovi_search.application.dto import SearchFilters, SearchResultDto
from memovi_search.application.queries import RetrieveKnowledgeQuery
from memovi_search.application.services import RetrievalMode

SEARCH_DOCUMENT_ID = "11111111-1111-1111-1111-111111111111"
KNOWLEDGE_ITEM_ID = "22222222-2222-2222-2222-222222222222"
DOCUMENT_ID = "33333333-3333-3333-3333-333333333333"
CREATED_AFTER = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
CREATED_BEFORE = datetime(2026, 7, 15, 12, 0, tzinfo=UTC)


class FakeRetrieveKnowledge:
    def __init__(self, results: list[SearchResultDto] | None = None) -> None:
        self._results = results or []
        self.last_query: RetrieveKnowledgeQuery | None = None

    def execute(self, query: RetrieveKnowledgeQuery) -> list[SearchResultDto]:
        self.last_query = query
        return self._results[query.offset : query.offset + query.limit]


@pytest.fixture
def search_results() -> list[SearchResultDto]:
    return [
        SearchResultDto(
            search_document_id=SEARCH_DOCUMENT_ID,
            knowledge_item_id=KNOWLEDGE_ITEM_ID,
            document_id=DOCUMENT_ID,
            relevance_score=0.87,
            searchable_text="Memovi indexes durable knowledge for retrieval.",
        ),
        SearchResultDto(
            search_document_id="44444444-4444-4444-4444-444444444444",
            knowledge_item_id="55555555-5555-5555-5555-555555555555",
            document_id="66666666-6666-6666-6666-666666666666",
            relevance_score=0.41,
            searchable_text="Secondary searchable passage about Memovi.",
        ),
        SearchResultDto(
            search_document_id="77777777-7777-7777-7777-777777777777",
            knowledge_item_id="88888888-8888-8888-8888-888888888888",
            document_id="99999999-9999-9999-9999-999999999999",
            relevance_score=0.12,
            searchable_text="A third indexed document for pagination.",
        ),
    ]


@pytest.fixture
def search_client(
    search_results: list[SearchResultDto],
) -> Iterator[tuple[TestClient, FakeRetrieveKnowledge]]:
    fake_search = FakeRetrieveKnowledge(results=search_results)
    app = create_app()
    app.dependency_overrides[get_retrieve_knowledge] = lambda: fake_search

    client = TestClient(app, base_url="https://testserver")
    try:
        yield client, fake_search
    finally:
        client.close()


def test_search_returns_matching_document(
    search_client: tuple[TestClient, FakeRetrieveKnowledge],
) -> None:
    client, fake_search = search_client

    response = client.get("/search", params={"q": "Memovi"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "Memovi"
    assert payload["count"] == 3
    assert payload["results"][0] == {
        "search_document_id": SEARCH_DOCUMENT_ID,
        "knowledge_item_id": KNOWLEDGE_ITEM_ID,
        "document_id": DOCUMENT_ID,
        "score": 0.87,
        "text": "Memovi indexes durable knowledge for retrieval.",
    }
    assert fake_search.last_query == RetrieveKnowledgeQuery(
        query="Memovi",
        limit=25,
        offset=0,
        mode=RetrievalMode.HYBRID,
        filters=SearchFilters(),
    )


def test_search_accepts_mode_parameter(
    search_client: tuple[TestClient, FakeRetrieveKnowledge],
) -> None:
    client, fake_search = search_client

    response = client.get("/search", params={"q": "Memovi", "mode": "keyword"})

    assert response.status_code == 200
    assert fake_search.last_query is not None
    assert fake_search.last_query.mode is RetrievalMode.KEYWORD


def test_search_returns_empty_results_when_nothing_matches() -> None:
    fake_search = FakeRetrieveKnowledge(results=[])
    app = create_app()
    app.dependency_overrides[get_retrieve_knowledge] = lambda: fake_search
    client = TestClient(app, base_url="https://testserver")

    try:
        response = client.get("/search", params={"q": "no-such-term"})
    finally:
        client.close()

    assert response.status_code == 200
    assert response.json() == {
        "query": "no-such-term",
        "count": 0,
        "results": [],
    }


def test_search_applies_pagination(
    search_client: tuple[TestClient, FakeRetrieveKnowledge],
) -> None:
    client, fake_search = search_client

    response = client.get("/search", params={"q": "Memovi", "limit": 1, "offset": 1})

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["results"][0]["search_document_id"] == "44444444-4444-4444-4444-444444444444"
    assert fake_search.last_query == RetrieveKnowledgeQuery(
        query="Memovi",
        limit=1,
        offset=1,
        mode=RetrievalMode.HYBRID,
        filters=SearchFilters(),
    )


def test_search_passes_mime_type_filter(
    search_client: tuple[TestClient, FakeRetrieveKnowledge],
) -> None:
    client, fake_search = search_client

    response = client.get(
        "/search",
        params={"q": "Memovi", "mime_type": "text/markdown"},
    )

    assert response.status_code == 200
    assert fake_search.last_query == RetrieveKnowledgeQuery(
        query="Memovi",
        limit=25,
        offset=0,
        mode=RetrievalMode.HYBRID,
        filters=SearchFilters(mime_type="text/markdown"),
    )


def test_search_passes_source_type_filter(
    search_client: tuple[TestClient, FakeRetrieveKnowledge],
) -> None:
    client, fake_search = search_client

    response = client.get(
        "/search",
        params={"q": "Memovi", "source_type": "upload"},
    )

    assert response.status_code == 200
    assert fake_search.last_query == RetrieveKnowledgeQuery(
        query="Memovi",
        limit=25,
        offset=0,
        mode=RetrievalMode.HYBRID,
        filters=SearchFilters(source_type="upload"),
    )


def test_search_passes_document_id_filter(
    search_client: tuple[TestClient, FakeRetrieveKnowledge],
) -> None:
    client, fake_search = search_client

    response = client.get(
        "/search",
        params={"q": "Memovi", "document_id": DOCUMENT_ID},
    )

    assert response.status_code == 200
    assert fake_search.last_query == RetrieveKnowledgeQuery(
        query="Memovi",
        limit=25,
        offset=0,
        mode=RetrievalMode.HYBRID,
        filters=SearchFilters(document_id=DOCUMENT_ID),
    )


def test_search_passes_date_range_filters(
    search_client: tuple[TestClient, FakeRetrieveKnowledge],
) -> None:
    client, fake_search = search_client

    response = client.get(
        "/search",
        params={
            "q": "Memovi",
            "created_after": CREATED_AFTER.isoformat(),
            "created_before": CREATED_BEFORE.isoformat(),
        },
    )

    assert response.status_code == 200
    assert fake_search.last_query == RetrieveKnowledgeQuery(
        query="Memovi",
        limit=25,
        offset=0,
        mode=RetrievalMode.HYBRID,
        filters=SearchFilters(
            created_after=CREATED_AFTER,
            created_before=CREATED_BEFORE,
        ),
    )


@pytest.mark.parametrize(
    ("params", "expected_substring"),
    [
        ({}, "q"),
        ({"q": ""}, "q"),
        ({"q": "   "}, "q"),
        ({"q": "Memovi", "limit": 101}, "limit"),
        ({"q": "Memovi", "offset": -1}, "offset"),
        ({"q": "Memovi", "mode": "invalid"}, "mode"),
    ],
)
def test_search_rejects_invalid_query_parameters(
    search_client: tuple[TestClient, FakeRetrieveKnowledge],
    params: dict[str, str | int],
    expected_substring: str,
) -> None:
    client, fake_search = search_client

    response = client.get("/search", params=params)

    assert response.status_code == 422
    assert expected_substring in response.text.lower()
    assert fake_search.last_query is None
