from collections.abc import Iterator

import pytest
from api.app import create_app
from fastapi.testclient import TestClient
from memovi_search.api.dependencies import get_semantic_search
from memovi_search.application.dto import SearchResultDto
from memovi_search.application.queries import SemanticSearchQuery

SEARCH_DOCUMENT_ID = "11111111-1111-1111-1111-111111111111"
KNOWLEDGE_ITEM_ID = "22222222-2222-2222-2222-222222222222"
DOCUMENT_ID = "33333333-3333-3333-3333-333333333333"


class FakeSemanticSearch:
    def __init__(self, results: list[SearchResultDto] | None = None) -> None:
        self._results = results or []
        self.last_query: SemanticSearchQuery | None = None

    def execute(self, query: SemanticSearchQuery) -> list[SearchResultDto]:
        self.last_query = query
        return self._results[: query.limit]


@pytest.fixture
def semantic_results() -> list[SearchResultDto]:
    return [
        SearchResultDto(
            search_document_id=SEARCH_DOCUMENT_ID,
            knowledge_item_id=KNOWLEDGE_ITEM_ID,
            document_id=DOCUMENT_ID,
            relevance_score=0.93,
            searchable_text="Memovi indexes durable knowledge for retrieval.",
        ),
        SearchResultDto(
            search_document_id="44444444-4444-4444-4444-444444444444",
            knowledge_item_id="55555555-5555-5555-5555-555555555555",
            document_id="66666666-6666-6666-6666-666666666666",
            relevance_score=0.41,
            searchable_text="Secondary searchable passage about Memovi.",
        ),
    ]


@pytest.fixture
def semantic_client(
    semantic_results: list[SearchResultDto],
) -> Iterator[tuple[TestClient, FakeSemanticSearch]]:
    fake_search = FakeSemanticSearch(results=semantic_results)
    app = create_app()
    app.dependency_overrides[get_semantic_search] = lambda: fake_search

    client = TestClient(app, base_url="https://testserver")
    try:
        yield client, fake_search
    finally:
        client.close()


def test_semantic_search_returns_matching_document(
    semantic_client: tuple[TestClient, FakeSemanticSearch],
) -> None:
    client, fake_search = semantic_client

    response = client.get("/search/semantic", params={"q": "Memovi"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "Memovi"
    assert payload["count"] == 2
    assert payload["results"][0] == {
        "search_document_id": SEARCH_DOCUMENT_ID,
        "knowledge_item_id": KNOWLEDGE_ITEM_ID,
        "document_id": DOCUMENT_ID,
        "score": 0.93,
        "text": "Memovi indexes durable knowledge for retrieval.",
    }
    assert fake_search.last_query == SemanticSearchQuery(query="Memovi", limit=25)


def test_semantic_search_applies_limit(
    semantic_client: tuple[TestClient, FakeSemanticSearch],
) -> None:
    client, fake_search = semantic_client

    response = client.get("/search/semantic", params={"q": "Memovi", "limit": 1})

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert fake_search.last_query == SemanticSearchQuery(query="Memovi", limit=1)


@pytest.mark.parametrize(
    ("params", "expected_substring"),
    [
        ({}, "q"),
        ({"q": ""}, "q"),
        ({"q": "   "}, "q"),
        ({"q": "Memovi", "limit": 101}, "limit"),
    ],
)
def test_semantic_search_rejects_invalid_query_parameters(
    semantic_client: tuple[TestClient, FakeSemanticSearch],
    params: dict[str, str | int],
    expected_substring: str,
) -> None:
    client, fake_search = semantic_client

    response = client.get("/search/semantic", params=params)

    assert response.status_code == 422
    assert expected_substring in response.text.lower()
    assert fake_search.last_query is None
