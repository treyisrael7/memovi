"""create memory and search tables

Revision ID: 20260713_0004
Revises: 20260706_0003
Create Date: 2026-07-13 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260713_0004"
down_revision: str | None = "20260706_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "memory_knowledge_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("document_version_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id",
            "document_version_id",
            name="uq_memory_knowledge_items_document_version",
        ),
    )
    op.create_index(
        "ix_memory_knowledge_items_document_id",
        "memory_knowledge_items",
        ["document_id"],
    )
    op.create_index(
        "ix_memory_knowledge_items_document_version_id",
        "memory_knowledge_items",
        ["document_version_id"],
    )

    op.create_table(
        "memory_chunks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("knowledge_item_id", sa.String(length=36), nullable=True),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("document_version_id", sa.String(length=36), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id",
            "document_version_id",
            "chunk_index",
            name="uq_memory_chunks_document_version_index",
        ),
    )
    op.create_index(
        "ix_memory_chunks_document_id",
        "memory_chunks",
        ["document_id"],
    )
    op.create_index(
        "ix_memory_chunks_document_version_id",
        "memory_chunks",
        ["document_version_id"],
    )
    op.create_index(
        "ix_memory_chunks_knowledge_item_id",
        "memory_chunks",
        ["knowledge_item_id"],
    )

    op.create_table(
        "search_documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("knowledge_item_id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("document_version_id", sa.String(length=36), nullable=False),
        sa.Column("searchable_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_search_documents_document_id",
        "search_documents",
        ["document_id"],
    )
    op.create_index(
        "ix_search_documents_document_version_id",
        "search_documents",
        ["document_version_id"],
    )
    op.create_index(
        "ix_search_documents_knowledge_item_id",
        "search_documents",
        ["knowledge_item_id"],
        unique=True,
    )

    op.create_table(
        "search_embeddings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("search_document_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=128), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("vector", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["search_document_id"],
            ["search_documents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "search_document_id",
            "provider",
            "model",
            name="uq_search_embeddings_document_provider_model",
        ),
    )
    op.create_index(
        "ix_search_embeddings_search_document_id",
        "search_embeddings",
        ["search_document_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_search_embeddings_search_document_id",
        table_name="search_embeddings",
    )
    op.drop_table("search_embeddings")
    op.drop_index(
        "ix_search_documents_knowledge_item_id",
        table_name="search_documents",
    )
    op.drop_index(
        "ix_search_documents_document_version_id",
        table_name="search_documents",
    )
    op.drop_index(
        "ix_search_documents_document_id",
        table_name="search_documents",
    )
    op.drop_table("search_documents")
    op.drop_index(
        "ix_memory_chunks_knowledge_item_id",
        table_name="memory_chunks",
    )
    op.drop_index(
        "ix_memory_chunks_document_version_id",
        table_name="memory_chunks",
    )
    op.drop_index(
        "ix_memory_chunks_document_id",
        table_name="memory_chunks",
    )
    op.drop_table("memory_chunks")
    op.drop_index(
        "ix_memory_knowledge_items_document_version_id",
        table_name="memory_knowledge_items",
    )
    op.drop_index(
        "ix_memory_knowledge_items_document_id",
        table_name="memory_knowledge_items",
    )
    op.drop_table("memory_knowledge_items")
