"""add normalized content to document versions

Revision ID: 20260706_0003
Revises: 20260701_0002
Create Date: 2026-07-06 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260706_0003"
down_revision: str | None = "20260701_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "documents_document_versions",
        sa.Column("normalized_content", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("documents_document_versions", "normalized_content")
