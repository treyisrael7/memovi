from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SearchDocumentRecord(Base):
    """Persistence model for searchable document representations."""

    __tablename__ = "search_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    document_version_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    chunk_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "document_version_id",
            "chunk_id",
            name="uq_search_documents_document_version_chunk",
        ),
    )


class SearchEmbeddingRecord(Base):
    """Persistence model for embedding metadata associated with search documents."""

    __tablename__ = "search_embeddings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    search_document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("search_documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    model_id: Mapped[str] = mapped_column(String(128), nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "search_document_id",
            "model_id",
            name="uq_search_embeddings_document_model",
        ),
    )
