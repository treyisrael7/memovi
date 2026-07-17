"""enable pgvector for search embeddings

Revision ID: 20260717_0007
Revises: 20260715_0006
Create Date: 2026-07-17 09:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "20260717_0007"
down_revision: str | None = "20260715_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_EMBEDDING_VECTOR_DIMENSIONS = 4


def upgrade() -> None:
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))

    # Embeddings are derived and regenerable; clear JSON rows before typed storage.
    op.execute(sa.text("DELETE FROM search_embeddings"))
    op.drop_column("search_embeddings", "vector")
    op.add_column(
        "search_embeddings",
        sa.Column(
            "vector",
            Vector(_EMBEDDING_VECTOR_DIMENSIONS),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_search_embeddings_vector_hnsw",
        "search_embeddings",
        ["vector"],
        postgresql_using="hnsw",
        postgresql_ops={"vector": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index(
        "ix_search_embeddings_vector_hnsw",
        table_name="search_embeddings",
    )
    op.execute(sa.text("DELETE FROM search_embeddings"))
    op.drop_column("search_embeddings", "vector")
    op.add_column(
        "search_embeddings",
        sa.Column("vector", sa.JSON(), nullable=False),
    )
