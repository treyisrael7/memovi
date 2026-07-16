"""add search metadata filter columns

Revision ID: 20260715_0006
Revises: 20260713_0005
Create Date: 2026-07-15 21:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260715_0006"
down_revision: str | None = "20260713_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "memory_knowledge_items",
        sa.Column("source_type", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "memory_knowledge_items",
        sa.Column("mime_type", sa.String(length=255), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE memory_knowledge_items "
            "SET source_type = 'upload', mime_type = 'application/octet-stream' "
            "WHERE source_type IS NULL OR mime_type IS NULL"
        )
    )
    op.alter_column("memory_knowledge_items", "source_type", nullable=False)
    op.alter_column("memory_knowledge_items", "mime_type", nullable=False)
    op.create_index(
        "ix_memory_knowledge_items_source_type",
        "memory_knowledge_items",
        ["source_type"],
    )
    op.create_index(
        "ix_memory_knowledge_items_mime_type",
        "memory_knowledge_items",
        ["mime_type"],
    )

    op.add_column(
        "search_documents",
        sa.Column("source_type", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "search_documents",
        sa.Column("mime_type", sa.String(length=255), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE search_documents "
            "SET source_type = 'upload', mime_type = 'application/octet-stream' "
            "WHERE source_type IS NULL OR mime_type IS NULL"
        )
    )
    op.alter_column("search_documents", "source_type", nullable=False)
    op.alter_column("search_documents", "mime_type", nullable=False)
    op.create_index(
        "ix_search_documents_source_type",
        "search_documents",
        ["source_type"],
    )
    op.create_index(
        "ix_search_documents_mime_type",
        "search_documents",
        ["mime_type"],
    )
    op.create_index(
        "ix_search_documents_created_at",
        "search_documents",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_search_documents_created_at", table_name="search_documents")
    op.drop_index("ix_search_documents_mime_type", table_name="search_documents")
    op.drop_index("ix_search_documents_source_type", table_name="search_documents")
    op.drop_column("search_documents", "mime_type")
    op.drop_column("search_documents", "source_type")

    op.drop_index("ix_memory_knowledge_items_mime_type", table_name="memory_knowledge_items")
    op.drop_index("ix_memory_knowledge_items_source_type", table_name="memory_knowledge_items")
    op.drop_column("memory_knowledge_items", "mime_type")
    op.drop_column("memory_knowledge_items", "source_type")
