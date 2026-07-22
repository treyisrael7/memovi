"""add conversation title

Revision ID: 20260721_0010
Revises: 20260718_0009
Create Date: 2026-07-21 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260721_0010"
down_revision: str | None = "20260718_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_TITLE = "New conversation"


def upgrade() -> None:
    op.add_column(
        "intelligence_conversations",
        sa.Column("title", sa.String(length=200), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE intelligence_conversations SET title = :title WHERE title IS NULL"
        ).bindparams(title=DEFAULT_TITLE)
    )
    op.alter_column(
        "intelligence_conversations",
        "title",
        existing_type=sa.String(length=200),
        nullable=False,
    )


def downgrade() -> None:
    op.drop_column("intelligence_conversations", "title")
