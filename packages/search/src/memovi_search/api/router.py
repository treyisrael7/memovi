from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from pydantic import AfterValidator

from memovi_search.api.dependencies import get_search_knowledge
from memovi_search.api.schemas import SearchResponse, SearchResultItemResponse
from memovi_search.application.queries import SearchKnowledge, SearchKnowledgeQuery


def _require_non_blank_query(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("must not be empty")
    return normalized


NonBlankSearchQuery = Annotated[str, AfterValidator(_require_non_blank_query)]

router = APIRouter(prefix="/search", tags=["search"])


@router.get(
    "",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search indexed knowledge",
    description=(
        "Run a ranked full-text search over indexed searchable documents. "
        "Returns matching passages with relevance scores. "
        "Does not perform vector, hybrid, or AI-assisted retrieval."
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
            description="Full-text search query. Required and must be non-empty.",
        ),
    ],
    use_case: Annotated[SearchKnowledge, Depends(get_search_knowledge)],
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
        SearchKnowledgeQuery(
            query=q,
            limit=limit,
            offset=offset,
        )
    )
    return SearchResponse(
        query=q,
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
