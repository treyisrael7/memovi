from dataclasses import dataclass
from enum import StrEnum

from memovi_shared import WorkspaceId

from memovi_search.application.dto import SearchFilters
from memovi_search.domain.entities.search_document import SearchDocument
from memovi_search.domain.entities.search_result import SearchResult
from memovi_search.domain.ranking import RankFusion, ScoreNormalizer
from memovi_search.domain.retrievers import RetrievalRequest, Retriever

_DEFAULT_CANDIDATE_CEILING = 100
_MINIMUM_CANDIDATE_POOL = 50


class RetrievalMode(StrEnum):
    """Supported unified retrieval strategies."""

    KEYWORD = "keyword"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"


@dataclass(frozen=True, slots=True)
class RetrievalEngineRequest:
    """Application-level retrieval request for the unified engine."""

    query: str
    mode: RetrievalMode
    limit: int
    offset: int
    workspace_id: WorkspaceId
    filters: SearchFilters | None = None


class RetrievalEngine:
    """Orchestrates keyword/semantic retrieval, fusion, filtering, and ranking."""

    def __init__(
        self,
        *,
        keyword_retriever: Retriever,
        semantic_retriever: Retriever,
        rank_fusion: RankFusion | None = None,
        score_normalizer: ScoreNormalizer | None = None,
    ) -> None:
        self._keyword_retriever = keyword_retriever
        self._semantic_retriever = semantic_retriever
        self._rank_fusion = rank_fusion or RankFusion()
        self._score_normalizer = score_normalizer or ScoreNormalizer()

    def retrieve(self, request: RetrievalEngineRequest) -> list[SearchResult]:
        normalized_query = request.query.strip()
        if not normalized_query or request.limit <= 0:
            return []

        candidate_limit = _candidate_limit(limit=request.limit, offset=request.offset)
        retrieval_request = RetrievalRequest(
            query=normalized_query,
            limit=candidate_limit,
            workspace_id=request.workspace_id,
        )

        ranked_lists = self._execute_retrievers(request.mode, retrieval_request)
        fused = self._rank_fusion.fuse(ranked_lists)
        filters = request.filters or SearchFilters()
        filtered = _apply_metadata_filters(
            fused,
            filters,
            workspace_id=request.workspace_id,
        )
        normalized = self._score_normalizer.normalize(filtered)
        return normalized[request.offset : request.offset + request.limit]

    def _execute_retrievers(
        self,
        mode: RetrievalMode,
        request: RetrievalRequest,
    ) -> list[list[SearchResult]]:
        if mode is RetrievalMode.KEYWORD:
            return [self._keyword_retriever.retrieve(request)]
        if mode is RetrievalMode.SEMANTIC:
            return [self._semantic_retriever.retrieve(request)]
        return [
            self._keyword_retriever.retrieve(request),
            self._semantic_retriever.retrieve(request),
        ]


def _candidate_limit(*, limit: int, offset: int) -> int:
    return min(
        _DEFAULT_CANDIDATE_CEILING,
        max(limit + offset, _MINIMUM_CANDIDATE_POOL),
    )


def _apply_metadata_filters(
    results: list[SearchResult],
    filters: SearchFilters,
    *,
    workspace_id: WorkspaceId,
) -> list[SearchResult]:
    return [
        result
        for result in results
        if _matches_filters(result.search_document, filters, workspace_id=workspace_id)
    ]


def _matches_filters(
    document: SearchDocument,
    filters: SearchFilters,
    *,
    workspace_id: WorkspaceId,
) -> bool:
    if document.workspace_id != workspace_id:
        return False
    if filters.workspace_id is not None and document.workspace_id != filters.workspace_id:
        return False
    if filters.document_id is not None and document.document_id != filters.document_id:
        return False
    if (
        filters.document_version_id is not None
        and document.document_version_id != filters.document_version_id
    ):
        return False
    if filters.source_type is not None and document.source_type != filters.source_type:
        return False
    if filters.mime_type is not None and document.mime_type != filters.mime_type:
        return False
    if filters.created_after is not None and document.created_at < filters.created_after:
        return False
    return not (filters.created_before is not None and document.created_at > filters.created_before)
