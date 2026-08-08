from collections.abc import Sequence
from datetime import datetime
from typing import Annotated, Literal, Protocol

from fastapi import APIRouter, Depends, HTTPException, Query, status
from memovi_observability import DiagnosticEventEmitter, DiagnosticEventName, timed_operation
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
_DIAGNOSTICS = DiagnosticEventEmitter()


class CollectionSearchMembershipResolver(Protocol):
    """Resolves collection membership into search set filters."""

    def resolve_search_member_ids(
        self,
        collection_id: str,
        *,
        workspace_id: WorkspaceId,
    ) -> tuple[frozenset[str], frozenset[str]]:
        """Return (document_ids, knowledge_item_ids)."""


def get_collection_search_membership_resolver() -> CollectionSearchMembershipResolver | None:
    """Optional; composition root may override with Memory CollectionService."""
    return None


class TagSearchMembershipResolver(Protocol):
    """Resolves tag assignments into search set filters."""

    def resolve_search_member_ids(
        self,
        tag_ids: Sequence[str],
        *,
        workspace_id: WorkspaceId,
    ) -> tuple[frozenset[str], frozenset[str]]:
        """Return (document_ids, knowledge_item_ids); multiple tags use AND."""


def get_tag_search_membership_resolver() -> TagSearchMembershipResolver | None:
    """Optional; composition root may override with Memory TagService."""
    return None


def _intersect_member_sets(
    left: tuple[frozenset[str] | None, frozenset[str] | None],
    right: tuple[frozenset[str], frozenset[str]],
) -> tuple[frozenset[str], frozenset[str]]:
    left_docs, left_knowledge = left
    right_docs, right_knowledge = right
    document_ids = right_docs if left_docs is None else left_docs & right_docs
    knowledge_item_ids = (
        right_knowledge if left_knowledge is None else left_knowledge & right_knowledge
    )
    return document_ids, knowledge_item_ids


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
    collection_resolver: Annotated[
        CollectionSearchMembershipResolver | None,
        Depends(get_collection_search_membership_resolver),
    ],
    tag_resolver: Annotated[
        TagSearchMembershipResolver | None,
        Depends(get_tag_search_membership_resolver),
    ],
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
    collection_id: Annotated[
        str | None,
        Query(description="Restrict results to members of a knowledge collection."),
    ] = None,
    tag_id: Annotated[
        list[str] | None,
        Query(
            description=(
                "Restrict results to resources assigned the given tag IDs. "
                "Repeat the parameter for multiple tags (AND semantics)."
            ),
        ),
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
    document_ids: frozenset[str] | None = None
    knowledge_item_ids: frozenset[str] | None = None
    if collection_id is not None:
        if collection_resolver is None:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Collection search filtering is not configured.",
            )
        try:
            document_ids, knowledge_item_ids = collection_resolver.resolve_search_member_ids(
                collection_id,
                workspace_id=workspace_id,
            )
        except Exception as exc:
            if exc.__class__.__name__ == "CollectionNotFoundError":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=str(exc),
                ) from exc
            raise

    tag_ids = [item.strip() for item in (tag_id or []) if item.strip()]
    if tag_ids:
        if tag_resolver is None:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Tag search filtering is not configured.",
            )
        try:
            tag_document_ids, tag_knowledge_ids = tag_resolver.resolve_search_member_ids(
                tag_ids,
                workspace_id=workspace_id,
            )
        except Exception as exc:
            if exc.__class__.__name__ == "TagNotFoundError":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=str(exc),
                ) from exc
            raise
        document_ids, knowledge_item_ids = _intersect_member_sets(
            (document_ids, knowledge_item_ids),
            (tag_document_ids, tag_knowledge_ids),
        )

    with timed_operation(
        "search.execute",
        metric_name="memovi.search.latency",
        attributes={"operation": "search.execute", "search.mode": mode},
    ):
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
                    document_ids=document_ids,
                    knowledge_item_ids=knowledge_item_ids,
                ),
            )
        )
    _DIAGNOSTICS.emit(
        DiagnosticEventName.SEARCH_EXECUTED,
        workspace_id=workspace_id.value,
        mode=mode,
        result_count=len(results),
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
    with timed_operation(
        "search.semantic",
        metric_name="memovi.search.latency",
        attributes={"operation": "search.semantic", "search.mode": "semantic"},
    ):
        results = use_case.execute(
            SemanticSearchQuery(
                query=q,
                workspace_id=workspace_id,
                limit=limit,
            )
        )
    _DIAGNOSTICS.emit(
        DiagnosticEventName.SEARCH_EXECUTED,
        workspace_id=workspace_id.value,
        mode="semantic",
        result_count=len(results),
    )
    return _to_response(query=q, results=results)
