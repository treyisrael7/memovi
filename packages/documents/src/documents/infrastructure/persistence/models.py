from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from documents.domain.enums import ProcessingStatus


class Base(DeclarativeBase):
    pass


class DocumentRecord(Base):
    """Persistence scaffold for normalized documents. Repository mapping is not implemented."""

    __tablename__ = "documents_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    versions: Mapped[list[DocumentVersionRecord]] = relationship(back_populates="document")
    processing_jobs: Mapped[list[ProcessingJobRecord]] = relationship(back_populates="document")


class DocumentVersionRecord(Base):
    """Persistence scaffold for document version snapshots."""

    __tablename__ = "documents_document_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents_documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    normalized_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    document: Mapped[DocumentRecord] = relationship(back_populates="versions")


class ProcessingJobRecord(Base):
    """Persistence scaffold for document ingestion processing jobs."""

    __tablename__ = "documents_processing_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents_documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    document_version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents_document_versions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ProcessingStatus.PENDING,
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    document: Mapped[DocumentRecord] = relationship(back_populates="processing_jobs")
