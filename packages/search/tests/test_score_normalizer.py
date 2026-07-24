from memovi_search.domain.entities import SearchDocument, SearchResult
from memovi_search.domain.ranking import ScoreNormalizer
from memovi_shared import WorkspaceId

DOCUMENT_ID = "3b96152e-5ba9-4933-8819-2a08069a6d9f"
DOCUMENT_VERSION_ID = "7ce3e814-de68-4200-973e-b2526eee058d"


def _result(knowledge_item_id: str, score: float) -> SearchResult:
    return SearchResult(
        search_document=SearchDocument.create(
            knowledge_item_id=knowledge_item_id,
            document_id=DOCUMENT_ID,
            document_version_id=DOCUMENT_VERSION_ID,
            source_type="upload",
            mime_type="text/markdown",
            searchable_text=knowledge_item_id,
            workspace_id=WorkspaceId.default(),
        ),
        score=score,
    )


def test_score_normalizer_applies_min_max() -> None:
    results = [
        _result("a1b2c3d4-e5f6-7890-abcd-ef1234567890", 10.0),
        _result("b2c3d4e5-f6a7-8901-bcde-f12345678901", 5.0),
        _result("c3d4e5f6-a7b8-9012-cdef-123456789012", 0.0),
    ]
    normalized = ScoreNormalizer().normalize(results)
    assert [item.score for item in normalized] == [1.0, 0.5, 0.0]


def test_score_normalizer_handles_equal_scores() -> None:
    results = [
        _result("a1b2c3d4-e5f6-7890-abcd-ef1234567890", 0.3),
        _result("b2c3d4e5-f6a7-8901-bcde-f12345678901", 0.3),
    ]
    normalized = ScoreNormalizer().normalize(results)
    assert [item.score for item in normalized] == [1.0, 1.0]


def test_score_normalizer_single_result_is_one() -> None:
    results = [_result("a1b2c3d4-e5f6-7890-abcd-ef1234567890", 0.12)]
    assert ScoreNormalizer().normalize(results)[0].score == 1.0
