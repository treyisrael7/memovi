"""resize search embedding vectors for production providers

Revision ID: 20260808_0013
Revises: 20260807_0012
Create Date: 2026-08-08 16:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from memovi_search.infrastructure.persistence.vector import EMBEDDING_VECTOR_DIMENSIONS
from pgvector.sqlalchemy import Vector

revision: str = "20260808_0013"
down_revision: str | None = "20260807_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PREVIOUS_EMBEDDING_VECTOR_DIMENSIONS = 4


def upgrade() -> None:
    # Embeddings are derived and regenerable; clear rows before resizing storage.
    op.execute(sa.text("DELETE FROM search_embeddings"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_search_embeddings_vector_hnsw"))
    op.drop_column("search_embeddings", "vector")
    op.add_column(
        "search_embeddings",
        sa.Column(
            "vector",
            Vector(EMBEDDING_VECTOR_DIMENSIONS),
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
    op.execute(sa.text("DELETE FROM search_embeddings"))
    op.drop_index(
        "ix_search_embeddings_vector_hnsw",
        table_name="search_embeddings",
    )
    op.drop_column("search_embeddings", "vector")
    op.add_column(
        "search_embeddings",
        sa.Column(
            "vector",
            Vector(_PREVIOUS_EMBEDDING_VECTOR_DIMENSIONS),
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
