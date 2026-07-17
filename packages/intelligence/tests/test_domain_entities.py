import pytest
from memovi_intelligence.domain.entities import (
    ReasoningContext,
    ReasoningRequest,
    ReasoningResult,
)
from memovi_intelligence.domain.exceptions import (
    InvalidReasoningRequestError,
    InvalidReasoningResultError,
)
from memovi_intelligence.domain.value_objects import ReasoningQuery, RetrievedPassage


def test_reasoning_request_create_assigns_id_and_normalizes_query() -> None:
    request = ReasoningRequest.create(query="  What did we decide?  ", limit=3)

    assert request.id.value
    assert request.query.value == "What did we decide?"
    assert request.limit == 3


def test_reasoning_request_is_immutable() -> None:
    request = ReasoningRequest.create(query="Summarize the notes.")

    with pytest.raises(AttributeError):
        request.limit = 10  # type: ignore[misc]


def test_reasoning_request_rejects_non_positive_limit() -> None:
    with pytest.raises(InvalidReasoningRequestError):
        ReasoningRequest.create(query="Valid query", limit=0)


def test_reasoning_context_create_preserves_passages() -> None:
    passage = RetrievedPassage(text="Decision recorded in meeting notes.", source_id="doc-1")
    context = ReasoningContext.create(query="What was decided?", passages=[passage])

    assert context.query.value == "What was decided?"
    assert context.passages == (passage,)
    assert context.is_empty is False


def test_reasoning_context_create_defaults_to_empty_passages() -> None:
    context = ReasoningContext.create(query=ReasoningQuery("Any updates?"))

    assert context.passages == ()
    assert context.is_empty is True


def test_reasoning_result_create_trims_content() -> None:
    context = ReasoningContext.create(query="Status?")
    result = ReasoningResult.create(content="  No blockers.  ", context=context)

    assert result.content == "No blockers."
    assert result.context is context


def test_reasoning_result_rejects_blank_content() -> None:
    context = ReasoningContext.create(query="Status?")

    with pytest.raises(InvalidReasoningResultError):
        ReasoningResult.create(content="   ", context=context)
