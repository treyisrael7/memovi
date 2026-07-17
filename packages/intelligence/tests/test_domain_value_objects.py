import uuid

import pytest
from memovi_intelligence.config import IntelligenceConfig
from memovi_intelligence.domain.exceptions import (
    InvalidIntelligenceConfigError,
    InvalidReasoningQueryError,
    InvalidReasoningRequestIdError,
    InvalidRetrievedKnowledgeError,
)
from memovi_intelligence.domain.services import estimate_token_count
from memovi_intelligence.domain.value_objects import (
    ReasoningQuery,
    ReasoningRequestId,
    RetrievedKnowledge,
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


def test_retrieved_knowledge_trims_fields() -> None:
    knowledge = RetrievedKnowledge(
        chunk_id="  chunk-1  ",
        document_id="  doc-1  ",
        text="  Indexed knowledge chunk.  ",
        score=0.91,
        document_title="  Source  ",
    )

    assert knowledge.chunk_id == "chunk-1"
    assert knowledge.document_id == "doc-1"
    assert knowledge.text == "Indexed knowledge chunk."
    assert knowledge.document_title == "Source"
    assert knowledge.score == 0.91


def test_retrieved_knowledge_rejects_blank_text() -> None:
    with pytest.raises(InvalidRetrievedKnowledgeError):
        RetrievedKnowledge(
            chunk_id="chunk-1",
            document_id="doc-1",
            text=" ",
            score=0.5,
        )


def test_retrieved_knowledge_rejects_negative_score() -> None:
    with pytest.raises(InvalidRetrievedKnowledgeError):
        RetrievedKnowledge(
            chunk_id="chunk-1",
            document_id="doc-1",
            text="Valid text",
            score=-0.1,
        )


def test_value_objects_are_immutable() -> None:
    query = ReasoningQuery("Immutable query")

    with pytest.raises(AttributeError):
        query.value = "changed"  # type: ignore[misc]


def test_estimate_token_count_is_deterministic() -> None:
    assert estimate_token_count("") == 0
    assert estimate_token_count("abcd") == 1
    assert estimate_token_count("a" * 8) == 2


def test_intelligence_config_defaults_are_valid() -> None:
    config = IntelligenceConfig()

    assert config.default_retrieval_limit == 20
    assert config.max_documents == 8
    assert config.max_chunks == 16
    assert config.max_estimated_tokens == 4_000


def test_intelligence_config_rejects_invalid_limits() -> None:
    with pytest.raises(InvalidIntelligenceConfigError):
        IntelligenceConfig(default_retrieval_limit=0)

    with pytest.raises(InvalidIntelligenceConfigError):
        IntelligenceConfig(max_documents=0)

    with pytest.raises(InvalidIntelligenceConfigError):
        IntelligenceConfig(max_estimated_tokens=0)
