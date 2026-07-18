from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from memovi_shared import WorkspaceId
from pydantic import AfterValidator

from memovi_search.api.dependencies import (
    get_active_workspace_id,
    get_retrieve_knowledge,
    get_semantic_search,
)
from memovi_search.api.schemas import SearchResponse, SearchResultItemResponse
from memovi_search.application.dto import SearchFilters, SearchResultDto
from memovi_search.application.queries import (
    RetrieveKnowledge,
    RetrieveKnowledgeQuery,
    SemanticSearch,
    SemanticSearchQuery,
)
from memovi_search.application.services import RetrievalMode


def _require_non_blank_query(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("must not be empty")
    return normalized


NonBlankSearchQuery = Annotated[str, AfterValidator(_require_non_blank_query)]
SearchMode = Literal["keyword", "semantic", "hybrid"]

router = APIRouter(prefix="/search", tags=["search"])


def _to_response(*, query: str, results: list[SearchResultDto]) -> SearchResponse:
    return SearchResponse(
        query=query,
        count=len(results),
        results=[
            SearchResultItemResponse(
                search_document_id=result.search_document_id,
                knowledge_item_id=result.knowledge_item_id,
                document_id=result.document_id,
                score=result.relevance_score,
                text=result.searchable_text,
            )
            for result in results
        ],
    )


@router.get(
    "",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search indexed knowledge",
    description=(
        "Run unified retrieval over indexed knowledge in the active workspace. "
        "Supported modes: keyword (full-text), semantic (vector similarity), "
        "and hybrid (Reciprocal Rank Fusion of both). Hybrid is the default. "
        "Optional metadata filters are applied after retrieval and fusion. "
        "Active workspace is resolved from X-Memovi-Workspace-Id or the Default Workspace."
    ),
    responses={
        200: {"description": "Ranked search results for the query."},
        422: {"description": "Invalid or missing query parameters."},
    },
)
def search(
    q: Annotated[
        NonBlankSearchQuery,
        Query(
            min_length=1,
            description="Search query. Required and must be non-empty.",
        ),
    ],
    use_case: Annotated[RetrieveKnowledge, Depends(get_retrieve_knowledge)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
    mode: Annotated[
        SearchMode,
        Query(
            description=("Retrieval mode: keyword, semantic, or hybrid (default hybrid)."),
        ),
    ] = "hybrid",
    document_id: Annotated[
        str | None,
        Query(description="Restrict results to a single document ID."),
    ] = None,
    source_type: Annotated[
        str | None,
        Query(description="Restrict results to a document source type."),
    ] = None,
    mime_type: Annotated[
        str | None,
        Query(description="Restrict results to a MIME type."),
    ] = None,
    created_after: Annotated[
        datetime | None,
        Query(description="Include documents created at or after this timestamp."),
    ] = None,
    created_before: Annotated[
        datetime | None,
        Query(description="Include documents created at or before this timestamp."),
    ] = None,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=100,
            description="Maximum number of results to return (default 25, max 100).",
        ),
    ] = 25,
    offset: Annotated[
        int,
        Query(
            ge=0,
            description="Number of results to skip before returning matches.",
        ),
    ] = 0,
) -> SearchResponse:
    results = use_case.execute(
        RetrieveKnowledgeQuery(
            query=q,
            workspace_id=workspace_id,
            mode=RetrievalMode(mode),
            limit=limit,
            offset=offset,
            filters=SearchFilters(
                workspace_id=workspace_id,
                document_id=document_id,
                source_type=source_type,
                mime_type=mime_type,
                created_after=created_after,
                created_before=created_before,
            ),
        )
    )
    return _to_response(query=q, results=results)


@router.get(
    "/semantic",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Semantic search indexed knowledge (deprecated)",
    description=(
        "Deprecated. Prefer GET /search?mode=semantic. "
        "Routes through the unified RetrievalEngine in semantic mode."
    ),
    responses={
        200: {"description": "Ranked semantic search results for the query."},
        422: {"description": "Invalid or missing query parameters."},
    },
    deprecated=True,
)
def semantic_search(
    q: Annotated[
        NonBlankSearchQuery,
        Query(
            min_length=1,
            description="Semantic search query. Required and must be non-empty.",
        ),
    ],
    use_case: Annotated[SemanticSearch, Depends(get_semantic_search)],
    workspace_id: Annotated[WorkspaceId, Depends(get_active_workspace_id)],
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=100,
            description="Maximum number of results to return (default 25, max 100).",
        ),
    ] = 25,
) -> SearchResponse:
    results = use_case.execute(
        SemanticSearchQuery(
            query=q,
            workspace_id=workspace_id,
            limit=limit,
        )
    )
    return _to_response(query=q, results=results)
