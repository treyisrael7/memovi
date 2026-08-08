from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
from api.app import create_app
from api.database import database_session as api_database_session
from auth.api.dependencies import get_database_session as get_auth_database_session
from auth.infrastructure.persistence import Base as AuthBase
from fastapi import FastAPI
from fastapi.testclient import TestClient
from memovi_search.api.dependencies import get_semantic_search
from memovi_search.application.dto import SearchResultDto
from memovi_search.application.queries import SemanticSearchQuery
from memovi_shared import DEFAULT_WORKSPACE_ID, WorkspaceId
from memovi_workspace.infrastructure.persistence import Base as WorkspaceBase
from memovi_workspace.infrastructure.persistence.models import WorkspaceRecord
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

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


def _build_authenticated_app(
    dependency_overrides: dict[Callable[..., Any], Callable[..., Any]] | None = None,
) -> tuple[FastAPI, Engine]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    AuthBase.metadata.create_all(engine)
    WorkspaceBase.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    with Session(engine) as seed_session:
        seed_session.add(
            WorkspaceRecord(
                id=DEFAULT_WORKSPACE_ID.value,
                name="Default",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )
        seed_session.commit()

    def database_session() -> Iterator[Session]:
        session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app = create_app()
    app.state.auth_session_factory = session_factory
    app.dependency_overrides[api_database_session] = database_session
    app.dependency_overrides[get_auth_database_session] = database_session
    for dep, override in (dependency_overrides or {}).items():
        app.dependency_overrides[dep] = override
    return app, engine


def _register(client: TestClient, *, email: str) -> None:
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "password123"},
    )
    assert response.status_code == 201


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
    app, engine = _build_authenticated_app(
        {get_semantic_search: lambda: fake_search},
    )
    client = TestClient(app, base_url="https://testserver")
    try:
        _register(client, email="semantic-tester@example.com")
        yield (client, fake_search)
    finally:
        client.close()
        engine.dispose()


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
    assert fake_search.last_query == SemanticSearchQuery(
        query="Memovi", limit=25, workspace_id=WorkspaceId.default()
    )


def test_semantic_search_applies_limit(
    semantic_client: tuple[TestClient, FakeSemanticSearch],
) -> None:
    client, fake_search = semantic_client
    response = client.get("/search/semantic", params={"q": "Memovi", "limit": 1})
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert fake_search.last_query == SemanticSearchQuery(
        query="Memovi", limit=1, workspace_id=WorkspaceId.default()
    )


@pytest.mark.parametrize(
    ("params", "expected_substring"),
    [({}, "q"), ({"q": ""}, "q"), ({"q": "   "}, "q"), ({"q": "Memovi", "limit": 101}, "limit")],
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
