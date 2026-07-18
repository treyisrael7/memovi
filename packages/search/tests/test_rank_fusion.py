from memovi_shared import WorkspaceId
from memovi_search.domain.entities import SearchDocument, SearchResult
from memovi_search.domain.ranking import DEFAULT_RRF_K, RankFusion
DOCUMENT_ID = '3b96152e-5ba9-4933-8819-2a08069a6d9f'
DOCUMENT_VERSION_ID = '7ce3e814-de68-4200-973e-b2526eee058d'

def _result(knowledge_item_id: str, score: float) -> SearchResult:
    return SearchResult(search_document=SearchDocument.create(knowledge_item_id=knowledge_item_id, document_id=DOCUMENT_ID, document_version_id=DOCUMENT_VERSION_ID, source_type='upload', mime_type='text/markdown', searchable_text=knowledge_item_id, workspace_id=WorkspaceId.default()), score=score)

def test_rank_fusion_uses_reciprocal_rank_fusion() -> None:
    first = _result('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 0.9)
    second = _result('b2c3d4e5-f6a7-8901-bcde-f12345678901', 0.8)
    third = _result('c3d4e5f6-a7b8-9012-cdef-123456789012', 0.7)
    fused = RankFusion(k=60).fuse([[first, second], [second, third]])
    by_id = {item.search_document.knowledge_item_id: item.score for item in fused}
    assert by_id[second.search_document.knowledge_item_id] == 1 / (DEFAULT_RRF_K + 2) + 1 / (DEFAULT_RRF_K + 1)
    assert by_id[first.search_document.knowledge_item_id] == 1 / (DEFAULT_RRF_K + 1)
    assert by_id[third.search_document.knowledge_item_id] == 1 / (DEFAULT_RRF_K + 2)
    assert fused[0].search_document.knowledge_item_id == second.search_document.knowledge_item_id

def test_rank_fusion_deduplicates_across_lists() -> None:
    shared = _result('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 1.0)
    fused = RankFusion().fuse([[shared], [shared]])
    assert len(fused) == 1
    assert fused[0].search_document.knowledge_item_id == shared.search_document.knowledge_item_id

def test_rank_fusion_passthrough_for_single_list() -> None:
    only = [_result('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 0.5)]
    assert RankFusion().fuse([only]) == only
