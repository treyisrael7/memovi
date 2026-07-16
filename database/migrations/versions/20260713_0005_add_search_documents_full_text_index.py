"""add search documents full text index

Revision ID: 20260713_0005
Revises: 20260713_0004
Create Date: 2026-07-13 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260713_0005"
down_revision: str | None = "20260713_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "search_documents",
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE search_documents " "SET search_vector = to_tsvector('english', searchable_text)"
        )
    )
    op.alter_column("search_documents", "search_vector", nullable=False)
    op.create_index(
        "ix_search_documents_search_vector",
        "search_documents",
        ["search_vector"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_search_documents_search_vector",
        table_name="search_documents",
    )
    op.drop_column("search_documents", "search_vector")
