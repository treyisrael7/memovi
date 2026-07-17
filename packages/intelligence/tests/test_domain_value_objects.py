import uuid

import pytest
from memovi_intelligence.config import IntelligenceConfig
from memovi_intelligence.domain.exceptions import (
    InvalidIntelligenceConfigError,
    InvalidReasoningQueryError,
    InvalidReasoningRequestIdError,
    InvalidRetrievedPassageError,
)
from memovi_intelligence.domain.value_objects import (
    ReasoningQuery,
    ReasoningRequestId,
    RetrievedPassage,
)


def test_reasoning_request_id_normalizes_uuid_string() -> None:
    raw_id = str(uuid.uuid4())
    request_id = ReasoningRequestId(raw_id.upper())

    assert request_id.value == raw_id
    assert str(request_id) == raw_id


def test_reasoning_request_id_rejects_invalid_value() -> None:
    with pytest.raises(InvalidReasoningRequestIdError):
        ReasoningRequestId("not-a-uuid")


def test_reasoning_query_trims_whitespace() -> None:
    query = ReasoningQuery("  How is indexing performed?  ")

    assert query.value == "How is indexing performed?"
    assert str(query) == "How is indexing performed?"


def test_reasoning_query_rejects_blank_value() -> None:
    with pytest.raises(InvalidReasoningQueryError):
        ReasoningQuery("   ")


def test_retrieved_passage_trims_text_and_source_id() -> None:
    passage = RetrievedPassage(
        text="  Indexed knowledge chunk.  ",
        source_id="  source-1  ",
        score=0.91,
    )

    assert passage.text == "Indexed knowledge chunk."
    assert passage.source_id == "source-1"
    assert passage.score == 0.91


def test_retrieved_passage_rejects_blank_text() -> None:
    with pytest.raises(InvalidRetrievedPassageError):
        RetrievedPassage(text=" ")


def test_retrieved_passage_rejects_negative_score() -> None:
    with pytest.raises(InvalidRetrievedPassageError):
        RetrievedPassage(text="Valid text", score=-0.1)


def test_value_objects_are_immutable() -> None:
    query = ReasoningQuery("Immutable query")

    with pytest.raises(AttributeError):
        query.value = "changed"  # type: ignore[misc]


def test_intelligence_config_defaults_are_valid() -> None:
    config = IntelligenceConfig()

    assert config.default_retrieval_limit == 5
    assert config.max_retrieved_passages == 8


def test_intelligence_config_rejects_invalid_limits() -> None:
    with pytest.raises(InvalidIntelligenceConfigError):
        IntelligenceConfig(default_retrieval_limit=0)

    with pytest.raises(InvalidIntelligenceConfigError):
        IntelligenceConfig(default_retrieval_limit=10, max_retrieved_passages=3)
