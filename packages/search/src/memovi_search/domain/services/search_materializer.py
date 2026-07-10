import re
import uuid
from datetime import UTC, datetime

from memovi_search.domain.entities import SearchDocument
from memovi_search.domain.exceptions import InvalidSearchMaterializationError
from memovi_search.domain.value_objects import SearchDocumentId

_SEARCH_MATERIALIZATION_NAMESPACE = uuid.UUID("8c4e1a72-3f9d-4b6e-a1c2-5d7f9e0b3a84")
_WHITESPACE_PATTERN = re.compile(r"\s+")


class SearchMaterializer:
    """Materializes a searchable document projection from canonical chunk text."""

    def materialize(
        self,
        *,
        knowledge_item_id: str,
        document_id: str,
        document_version_id: str,
        chunk_texts: list[str],
        now: datetime | None = None,
    ) -> SearchDocument:
        if not chunk_texts:
            raise InvalidSearchMaterializationError(
                "At least one chunk text is required to materialize a search document.",
            )

        searchable_text = _build_searchable_text(chunk_texts)
        if not searchable_text:
            raise InvalidSearchMaterializationError(
                "Chunk texts must produce non-empty searchable text.",
            )

        timestamp = now or datetime.now(UTC)
        return SearchDocument(
            id=_search_document_id(knowledge_item_id),
            knowledge_item_id=knowledge_item_id,
            document_id=document_id,
            document_version_id=document_version_id,
            searchable_text=searchable_text,
            created_at=timestamp,
            updated_at=timestamp,
        )


def _build_searchable_text(chunk_texts: list[str]) -> str:
    combined = "".join(chunk_texts)
    return _WHITESPACE_PATTERN.sub(" ", combined).strip()


def _search_document_id(knowledge_item_id: str) -> SearchDocumentId:
    derived_id = uuid.uuid5(
        _SEARCH_MATERIALIZATION_NAMESPACE,
        f"search-document:{knowledge_item_id}",
    )
    return SearchDocumentId(str(derived_id))
