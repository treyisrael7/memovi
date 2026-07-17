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
from memovi_intelligence.domain.services import estimate_token_count
from memovi_intelligence.domain.value_objects import (
    AssembledDocument,
    ContextMetadata,
    RetrievedKnowledge,
)


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


def test_reasoning_context_empty_has_zero_counts() -> None:
    request = ReasoningRequest.create(query="Any updates?")
    context = ReasoningContext.empty(request)

    assert context.request is request
    assert context.query == "Any updates?"
    assert context.retrieved_knowledge == ()
    assert context.assembled_documents == ()
    assert context.estimated_token_count == 0
    assert context.is_empty is True
    assert context.metadata.retrieved_count == 0


def test_reasoning_context_preserves_assembled_fields() -> None:
    request = ReasoningRequest.create(query="What was decided?")
    knowledge = RetrievedKnowledge(
        chunk_id="chunk-1",
        document_id="doc-1",
        text="Decision recorded in meeting notes.",
        score=0.9,
        document_title="Notes",
    )
    document = AssembledDocument(
        document_id="doc-1",
        title="Notes",
        chunks=(knowledge,),
        text=knowledge.text,
        estimated_token_count=estimate_token_count(knowledge.text),
    )
    context = ReasoningContext(
        request=request,
        retrieved_knowledge=(knowledge,),
        assembled_documents=(document,),
        metadata=ContextMetadata(
            retrieved_count=1,
            retained_chunk_count=1,
            retained_document_count=1,
            truncated=False,
        ),
        estimated_token_count=document.estimated_token_count,
    )

    assert context.retrieved_knowledge == (knowledge,)
    assert context.assembled_documents == (document,)
    assert context.is_empty is False


def test_reasoning_result_create_trims_content() -> None:
    request = ReasoningRequest.create(query="Status?")
    context = ReasoningContext.empty(request)
    result = ReasoningResult.create(content="  No blockers.  ", context=context)

    assert result.content == "No blockers."
    assert result.context is context


def test_reasoning_result_rejects_blank_content() -> None:
    request = ReasoningRequest.create(query="Status?")
    context = ReasoningContext.empty(request)

    with pytest.raises(InvalidReasoningResultError):
        ReasoningResult.create(content="   ", context=context)
