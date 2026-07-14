from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KnowledgeChunkReadDto:
    chunk_index: int
    text: str


@dataclass(frozen=True, slots=True)
class KnowledgeReadDto:
    """Canonical knowledge read through the search application boundary."""

    id: str
    document_id: str
    document_version_id: str
    chunks: tuple[KnowledgeChunkReadDto, ...]
