import pytest
from memovi_intelligence.application.services import ContextAssembler
from memovi_intelligence.config import IntelligenceConfig
from memovi_intelligence.domain.entities import ReasoningRequest
from memovi_intelligence.domain.services import estimate_token_count
from memovi_intelligence.domain.value_objects import RetrievedKnowledge


class FakeKnowledgeRetriever:
    def __init__(self, items: tuple[RetrievedKnowledge, ...] = ()) -> None:
        self._items = items
        self.last_limit: int | None = None

    def retrieve(
        self,
        request: ReasoningRequest,
        *,
        limit: int,
    ) -> tuple[RetrievedKnowledge, ...]:
        self.last_limit = limit
        return self._items[:limit]


class FifteenChunkFakeRetriever(FakeKnowledgeRetriever):
    """Returns 15 ranked chunks across multiple documents, including duplicates.

    Shape (intentionally unsorted / duplicated):
    - 5 documents (doc-1 .. doc-5)
    - 12 unique chunk IDs
    - 3 near-peer duplicates of top-ranked chunks (chunk-01/02/03)
    """

    def __init__(self) -> None:
        super().__init__(items=_fifteen_chunk_fixture())


def _knowledge(
    *,
    chunk_id: str,
    document_id: str,
    text: str,
    score: float,
    document_title: str | None = None,
) -> RetrievedKnowledge:
    return RetrievedKnowledge(
        chunk_id=chunk_id,
        document_id=document_id,
        text=text,
        score=score,
        document_title=document_title,
    )


def _fifteen_chunk_fixture() -> tuple[RetrievedKnowledge, ...]:
    """Build 15 chunks: multiple documents + duplicate chunk IDs, unsorted by score.

    Unique chunk scores descend from 0.95. Duplicate copies of the top three chunks
    sit just below their primaries so ranked selection encounters and drops them.
    """
    unique = [
        _knowledge(
            chunk_id=f"chunk-{index:02d}",
            document_id=f"doc-{((index - 1) % 5) + 1}",
            text=f"Passage {index:02d} from document {((index - 1) % 5) + 1}.",
            score=round(1.00 - (index * 0.05), 2),
            document_title=f"Document {((index - 1) % 5) + 1}",
        )
        for index in range(1, 13)
    ]
    # Near-peer duplicates of retained top chunks so selection removes them.
    duplicates = [
        _knowledge(
            chunk_id="chunk-01",
            document_id="doc-1",
            text="Passage 01 from document 1.",
            score=0.94,
            document_title="Document 1",
        ),
        _knowledge(
            chunk_id="chunk-02",
            document_id="doc-2",
            text="Passage 02 from document 2.",
            score=0.89,
            document_title="Document 2",
        ),
        _knowledge(
            chunk_id="chunk-03",
            document_id="doc-3",
            text="Passage 03 from document 3.",
            score=0.84,
            document_title="Document 3",
        ),
    ]
    # Interleave so retrieval order is not already ranked.
    return (
        unique[0],
        duplicates[0],
        unique[4],
        unique[1],
        unique[8],
        duplicates[1],
        unique[2],
        unique[9],
        unique[3],
        unique[5],
        duplicates[2],
        unique[6],
        unique[10],
        unique[7],
        unique[11],
    )


def test_assemble_empty_retrieval_returns_empty_context() -> None:
    request = ReasoningRequest.create(query="Anything found?")
    assembler = ContextAssembler(knowledge_retriever=FakeKnowledgeRetriever())

    context = assembler.assemble(request)

    assert context.request is request
    assert context.is_empty is True
    assert context.retrieved_knowledge == ()
    assert context.assembled_documents == ()
    assert context.estimated_token_count == 0
    assert context.metadata.retrieved_count == 0
    assert context.metadata.truncated is False


def test_assemble_removes_duplicate_chunks() -> None:
    duplicate = _knowledge(
        chunk_id="chunk-1",
        document_id="doc-1",
        text="Shared chunk text.",
        score=0.5,
    )
    higher = _knowledge(
        chunk_id="chunk-1",
        document_id="doc-1",
        text="Shared chunk text.",
        score=0.9,
    )
    other = _knowledge(
        chunk_id="chunk-2",
        document_id="doc-1",
        text="Another chunk.",
        score=0.4,
    )
    assembler = ContextAssembler(
        knowledge_retriever=FakeKnowledgeRetriever((duplicate, higher, other)),
        config=IntelligenceConfig(max_chunks=10, max_documents=5, max_estimated_tokens=1_000),
    )

    context = assembler.assemble(ReasoningRequest.create(query="Deduplicate chunks"))

    assert [item.chunk_id for item in context.retrieved_knowledge] == ["chunk-1", "chunk-2"]
    assert context.retrieved_knowledge[0].score == 0.9
    assert context.metadata.duplicate_chunks_removed == 1
    assert context.metadata.truncated is True


def test_assemble_orders_by_retrieval_ranking() -> None:
    lower = _knowledge(chunk_id="b", document_id="doc-1", text="Lower", score=0.2)
    higher = _knowledge(chunk_id="a", document_id="doc-2", text="Higher", score=0.8)
    middle = _knowledge(chunk_id="c", document_id="doc-3", text="Middle", score=0.5)
    assembler = ContextAssembler(
        knowledge_retriever=FakeKnowledgeRetriever((lower, higher, middle)),
    )

    context = assembler.assemble(ReasoningRequest.create(query="Order by score"))

    assert [item.chunk_id for item in context.retrieved_knowledge] == ["a", "c", "b"]
    assert [document.document_id for document in context.assembled_documents] == [
        "doc-2",
        "doc-3",
        "doc-1",
    ]


def test_assemble_enforces_token_limit_deterministically() -> None:
    first = _knowledge(
        chunk_id="chunk-1",
        document_id="doc-1",
        text="a" * 8,  # 2 estimated tokens
        score=1.0,
    )
    second = _knowledge(
        chunk_id="chunk-2",
        document_id="doc-1",
        text="b" * 8,  # 2 estimated tokens
        score=0.9,
    )
    third = _knowledge(
        chunk_id="chunk-3",
        document_id="doc-2",
        text="c" * 8,
        score=0.8,
    )
    assembler = ContextAssembler(
        knowledge_retriever=FakeKnowledgeRetriever((first, second, third)),
        config=IntelligenceConfig(
            max_chunks=10,
            max_documents=10,
            max_estimated_tokens=4,
        ),
    )

    context = assembler.assemble(ReasoningRequest.create(query="Token limit"))

    assert [item.chunk_id for item in context.retrieved_knowledge] == ["chunk-1", "chunk-2"]
    assert context.estimated_token_count == estimate_token_count(first.text + "\n\n" + second.text)
    assert context.metadata.truncated is True
    assert context.metadata.retained_chunk_count == 2


def test_assemble_enforces_document_limit() -> None:
    doc1_a = _knowledge(
        chunk_id="c1",
        document_id="doc-1",
        text="Doc one A",
        score=1.0,
        document_title="One",
    )
    doc1_b = _knowledge(
        chunk_id="c2",
        document_id="doc-1",
        text="Doc one B",
        score=0.9,
    )
    doc2 = _knowledge(
        chunk_id="c3",
        document_id="doc-2",
        text="Doc two",
        score=0.8,
        document_title="Two",
    )
    assembler = ContextAssembler(
        knowledge_retriever=FakeKnowledgeRetriever((doc1_a, doc1_b, doc2)),
        config=IntelligenceConfig(
            max_documents=1,
            max_chunks=10,
            max_estimated_tokens=1_000,
        ),
    )

    context = assembler.assemble(ReasoningRequest.create(query="Document limit"))

    assert [item.chunk_id for item in context.retrieved_knowledge] == ["c1", "c2"]
    assert len(context.assembled_documents) == 1
    assert context.assembled_documents[0].document_id == "doc-1"
    assert context.assembled_documents[0].title == "One"
    assert context.metadata.duplicate_documents_skipped == 1
    assert context.metadata.truncated is True


def test_assemble_enforces_chunk_limit() -> None:
    items = tuple(
        _knowledge(
            chunk_id=f"chunk-{index}",
            document_id=f"doc-{index}",
            text=f"Text {index}",
            score=1.0 - (index * 0.1),
        )
        for index in range(5)
    )
    assembler = ContextAssembler(
        knowledge_retriever=FakeKnowledgeRetriever(items),
        config=IntelligenceConfig(
            max_chunks=2,
            max_documents=10,
            max_estimated_tokens=1_000,
        ),
    )

    context = assembler.assemble(ReasoningRequest.create(query="Chunk limit"))

    assert len(context.retrieved_knowledge) == 2
    assert context.metadata.retained_chunk_count == 2
    assert context.metadata.truncated is True


def test_assemble_uses_request_limit_for_retrieval() -> None:
    items = tuple(
        _knowledge(
            chunk_id=f"chunk-{index}",
            document_id="doc-1",
            text=f"Text {index}",
            score=1.0 - (index * 0.1),
        )
        for index in range(5)
    )
    retriever = FakeKnowledgeRetriever(items)
    assembler = ContextAssembler(knowledge_retriever=retriever)

    assembler.assemble(ReasoningRequest.create(query="Limited retrieval", limit=2))

    assert retriever.last_limit == 2


def test_fifteen_chunk_fake_retriever_dedupes_orders_and_respects_limits() -> None:
    retriever = FifteenChunkFakeRetriever()
    request = ReasoningRequest.create(query="Assemble from fifteen fake chunks")
    raw = retriever.retrieve(request, limit=20)
    assert len(raw) == 15

    config = IntelligenceConfig(
        default_retrieval_limit=15,
        max_documents=3,
        max_chunks=5,
        max_estimated_tokens=1_000,
    )
    assembler = ContextAssembler(knowledge_retriever=retriever, config=config)

    context = assembler.assemble(request)

    # Duplicates removed: 15 retrieved -> 3 duplicate chunk IDs dropped before limits.
    assert context.metadata.retrieved_count == 15
    assert context.metadata.duplicate_chunks_removed == 3
    retained_ids = [item.chunk_id for item in context.retrieved_knowledge]
    assert len(retained_ids) == len(set(retained_ids))

    # Ordering preserved by retrieval ranking (score desc); document limit skips
    # higher-ranked chunks from docs beyond max_documents.
    assert retained_ids == ["chunk-01", "chunk-02", "chunk-03", "chunk-06", "chunk-07"]
    scores = [item.score for item in context.retrieved_knowledge]
    assert scores == sorted(scores, reverse=True)
    assert all(
        left.score >= right.score
        for left, right in zip(
            context.retrieved_knowledge,
            context.retrieved_knowledge[1:],
            strict=False,
        )
    )

    # Configured limits respected.
    assert len(context.retrieved_knowledge) <= config.max_chunks
    assert len(context.assembled_documents) <= config.max_documents
    assert context.estimated_token_count <= config.max_estimated_tokens
    assert context.metadata.retained_chunk_count == 5
    assert context.metadata.retained_document_count == 3
    assert [document.document_id for document in context.assembled_documents] == [
        "doc-1",
        "doc-2",
        "doc-3",
    ]
    assert context.metadata.truncated is True

    # ReasoningContext is immutable.
    with pytest.raises(AttributeError):
        context.estimated_token_count = 0  # type: ignore[misc]
    with pytest.raises(AttributeError):
        context.retrieved_knowledge = ()  # type: ignore[misc]
    with pytest.raises(AttributeError):
        context.metadata = context.metadata  # type: ignore[misc]
