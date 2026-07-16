from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SearchDocumentRecord(Base):
    """Persistence model for searchable knowledge projections."""

    __tablename__ = "search_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    knowledge_item_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        index=True,
        nullable=False,
    )
    document_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    document_version_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    searchable_text: Mapped[str] = mapped_column(Text, nullable=False)
    search_vector: Mapped[Any] = mapped_column(
        TSVECTOR().with_variant(Text(), "sqlite"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SearchEmbeddingRecord(Base):
    """Persistence model for embeddings associated with search documents."""

    __tablename__ = "search_embeddings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    search_document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("search_documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(128), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    vector: Mapped[list[float]] = mapped_column(JSON, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "search_document_id",
            "provider",
            "model",
            name="uq_search_embeddings_document_provider_model",
        ),
    )
