from memovi_intelligence.application.ports import KnowledgeRetriever
from memovi_intelligence.config import IntelligenceConfig
from memovi_intelligence.domain.entities import ReasoningContext, ReasoningRequest
from memovi_intelligence.domain.services import estimate_token_count
from memovi_intelligence.domain.value_objects import (
    AssembledDocument,
    ContextMetadata,
    ConversationHistory,
    RetrievedKnowledge,
)

_DOCUMENT_TEXT_SEPARATOR = "\n\n"


class ContextAssembler:
    """Builds an immutable ReasoningContext from retrieved knowledge.

    Gathers ranked knowledge through KnowledgeRetriever, orders by score, removes
    duplicates, enforces document/chunk/token limits, and assembles document views.
    Optional conversation history is trimmed to configured turn and token limits and
    attached without merging into retrieved knowledge.
    """

    def __init__(
        self,
        *,
        knowledge_retriever: KnowledgeRetriever,
        config: IntelligenceConfig | None = None,
    ) -> None:
        self._knowledge_retriever = knowledge_retriever
        self._config = config or IntelligenceConfig()

    @property
    def config(self) -> IntelligenceConfig:
        return self._config

    def assemble(
        self,
        request: ReasoningRequest,
        *,
        conversation_history: ConversationHistory | None = None,
    ) -> ReasoningContext:
        limit = request.limit if request.limit is not None else self._config.default_retrieval_limit
        retrieved = tuple(self._knowledge_retriever.retrieve(request, limit=limit))
        return self.assemble_from(
            request,
            retrieved,
            conversation_history=conversation_history,
        )

    def assemble_from(
        self,
        request: ReasoningRequest,
        retrieved: tuple[RetrievedKnowledge, ...],
        *,
        conversation_history: ConversationHistory | None = None,
    ) -> ReasoningContext:
        """Assemble context from already-retrieved knowledge without re-querying."""
        retained_history = _trim_conversation_history(
            conversation_history,
            config=self._config,
        )

        if not retrieved:
            empty = ReasoningContext.empty(request)
            if retained_history.is_empty:
                return empty
            return ReasoningContext(
                request=request,
                retrieved_knowledge=(),
                assembled_documents=(),
                metadata=empty.metadata,
                estimated_token_count=retained_history.estimated_token_count,
                conversation_history=retained_history,
            )

        ordered = _order_by_ranking(retrieved)
        retained, stats = _select_knowledge(ordered, config=self._config)
        assembled_documents = _assemble_documents(retained)
        knowledge_tokens = sum(document.estimated_token_count for document in assembled_documents)

        # Conversation tokens never bypass the overall estimated-token budget.
        remaining_tokens = max(0, self._config.max_estimated_tokens - knowledge_tokens)
        conversation_token_budget = min(
            self._config.max_conversation_tokens,
            remaining_tokens,
        )
        retained_history = retained_history.trim(
            max_turns=self._config.max_conversation_turns,
            max_tokens=conversation_token_budget,
        )

        return ReasoningContext(
            request=request,
            retrieved_knowledge=retained,
            assembled_documents=assembled_documents,
            metadata=ContextMetadata(
                retrieved_count=len(retrieved),
                retained_chunk_count=len(retained),
                retained_document_count=len(assembled_documents),
                truncated=stats.truncated,
                duplicate_chunks_removed=stats.duplicate_chunks_removed,
                duplicate_documents_skipped=stats.duplicate_documents_skipped,
            ),
            estimated_token_count=(knowledge_tokens + retained_history.estimated_token_count),
            conversation_history=retained_history,
        )


class _SelectionStats:
    __slots__ = (
        "duplicate_chunks_removed",
        "duplicate_documents_skipped",
        "truncated",
    )

    def __init__(self) -> None:
        self.duplicate_chunks_removed = 0
        self.duplicate_documents_skipped = 0
        self.truncated = False


def _trim_conversation_history(
    conversation_history: ConversationHistory | None,
    *,
    config: IntelligenceConfig,
) -> ConversationHistory:
    if conversation_history is None or conversation_history.is_empty:
        return ConversationHistory.empty()
    return conversation_history.trim(
        max_turns=config.max_conversation_turns,
        max_tokens=config.max_conversation_tokens,
    )


def _order_by_ranking(
    retrieved: tuple[RetrievedKnowledge, ...],
) -> tuple[RetrievedKnowledge, ...]:
    return tuple(
        sorted(
            retrieved,
            key=lambda item: (-item.score, item.chunk_id, item.document_id),
        )
    )


def _select_knowledge(
    ordered: tuple[RetrievedKnowledge, ...],
    *,
    config: IntelligenceConfig,
) -> tuple[tuple[RetrievedKnowledge, ...], _SelectionStats]:
    stats = _SelectionStats()
    retained: list[RetrievedKnowledge] = []
    seen_chunk_ids: set[str] = set()
    included_document_ids: set[str] = set()
    used_tokens = 0

    for item in ordered:
        if item.chunk_id in seen_chunk_ids:
            stats.duplicate_chunks_removed += 1
            stats.truncated = True
            continue

        is_new_document = item.document_id not in included_document_ids
        if is_new_document and len(included_document_ids) >= config.max_documents:
            stats.duplicate_documents_skipped += 1
            stats.truncated = True
            continue

        if len(retained) >= config.max_chunks:
            stats.truncated = True
            break

        chunk_tokens = estimate_token_count(item.text)
        if used_tokens + chunk_tokens > config.max_estimated_tokens:
            stats.truncated = True
            # Skip an individually oversized lead chunk; otherwise stop (prefix trim).
            if not retained and chunk_tokens > config.max_estimated_tokens:
                continue
            break

        retained.append(item)
        seen_chunk_ids.add(item.chunk_id)
        used_tokens += chunk_tokens
        if is_new_document:
            included_document_ids.add(item.document_id)

    return tuple(retained), stats


def _assemble_documents(
    retained: tuple[RetrievedKnowledge, ...],
) -> tuple[AssembledDocument, ...]:
    if not retained:
        return ()

    chunks_by_document: dict[str, list[RetrievedKnowledge]] = {}
    document_order: list[str] = []
    titles: dict[str, str | None] = {}

    for item in retained:
        if item.document_id not in chunks_by_document:
            chunks_by_document[item.document_id] = []
            document_order.append(item.document_id)
            titles[item.document_id] = item.document_title
        chunks_by_document[item.document_id].append(item)
        if titles[item.document_id] is None and item.document_title is not None:
            titles[item.document_id] = item.document_title

    documents: list[AssembledDocument] = []
    for document_id in document_order:
        chunks = tuple(chunks_by_document[document_id])
        text = _DOCUMENT_TEXT_SEPARATOR.join(chunk.text for chunk in chunks)
        documents.append(
            AssembledDocument(
                document_id=document_id,
                title=titles[document_id],
                chunks=chunks,
                text=text,
                estimated_token_count=estimate_token_count(text),
            )
        )
    return tuple(documents)
