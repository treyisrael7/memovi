from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class KnowledgeItemRecord(Base):
    """Persistence model for durable knowledge derived from processed documents."""

    __tablename__ = "memory_knowledge_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    document_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    document_version_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "document_version_id",
            name="uq_memory_knowledge_items_document_version",
        ),
    )


class ChunkRecord(Base):
    """Persistence model for retrievable knowledge chunks."""

    __tablename__ = "memory_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    knowledge_item_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    document_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    document_version_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "document_version_id",
            "chunk_index",
            name="uq_memory_chunks_document_version_index",
        ),
    )


class CollectionRecord(Base):
    """Persistence model for workspace-scoped knowledge collections."""

    __tablename__ = "memory_collections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CollectionMembershipRecord(Base):
    """Persistence model for collection membership references."""

    __tablename__ = "memory_collection_memberships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    collection_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("memory_collections.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    workspace_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    member_kind: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    member_id: Mapped[str] = mapped_column(String(256), index=True, nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "collection_id",
            "member_kind",
            "member_id",
            name="uq_memory_collection_memberships_item",
        ),
    )


class CollectionActivityRecord(Base):
    """Persistence model for collection organizational activity."""

    __tablename__ = "memory_collection_activity"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    collection_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("memory_collections.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    workspace_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    activity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    member_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    member_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    detail: Mapped[str] = mapped_column(Text, nullable=False, default="")
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )


class TagRecord(Base):
    """Persistence model for workspace-scoped knowledge tags."""

    __tablename__ = "memory_tags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    name_key: Mapped[str] = mapped_column(String(256), nullable=False)
    color: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "name_key",
            name="uq_memory_tags_workspace_name_key",
        ),
    )


class TagAssignmentRecord(Base):
    """Persistence model for tag assignment references."""

    __tablename__ = "memory_tag_assignments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tag_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("memory_tags.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    workspace_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    member_kind: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    member_id: Mapped[str] = mapped_column(String(256), index=True, nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "tag_id",
            "member_kind",
            "member_id",
            name="uq_memory_tag_assignments_item",
        ),
    )


class ResourceMetadataRecord(Base):
    """Persistence model for polymorphic resource metadata."""

    __tablename__ = "memory_resource_metadata"

    workspace_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    member_kind: Mapped[str] = mapped_column(String(32), primary_key=True)
    member_id: Mapped[str] = mapped_column(String(256), primary_key=True)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
