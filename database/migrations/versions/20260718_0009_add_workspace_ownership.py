"""add workspace ownership

Revision ID: 20260718_0009
Revises: 20260717_0008
Create Date: 2026-07-18 00:00:00
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "20260718_0009"
down_revision: str | None = "20260717_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_WORKSPACE_ID = "00000000-0000-4000-8000-000000000001"

OWNED_TABLES = (
    "documents_documents",
    "memory_knowledge_items",
    "memory_chunks",
    "search_documents",
    "intelligence_conversations",
)


def upgrade() -> None:
    op.create_table(
        "workspace_workspaces",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.bulk_insert(
        sa.table(
            "workspace_workspaces",
            sa.column("id", sa.String),
            sa.column("name", sa.String),
            sa.column("created_at", sa.DateTime(timezone=True)),
        ),
        [
            {
                "id": DEFAULT_WORKSPACE_ID,
                "name": "Default",
                "created_at": datetime(2026, 1, 1, tzinfo=UTC),
            }
        ],
    )

    for table_name in OWNED_TABLES:
        op.add_column(
            table_name,
            sa.Column("workspace_id", sa.String(length=36), nullable=True),
        )
        op.execute(
            sa.text(f"UPDATE {table_name} SET workspace_id = :workspace_id").bindparams(
                workspace_id=DEFAULT_WORKSPACE_ID,
            )
        )
        op.alter_column(table_name, "workspace_id", nullable=False)
        op.create_index(
            f"ix_{table_name}_workspace_id",
            table_name,
            ["workspace_id"],
        )
        op.create_foreign_key(
            f"fk_{table_name}_workspace_id",
            table_name,
            "workspace_workspaces",
            ["workspace_id"],
            ["id"],
        )


def downgrade() -> None:
    for table_name in reversed(OWNED_TABLES):
        op.drop_constraint(f"fk_{table_name}_workspace_id", table_name, type_="foreignkey")
        op.drop_index(f"ix_{table_name}_workspace_id", table_name=table_name)
        op.drop_column(table_name, "workspace_id")

    op.drop_table("workspace_workspaces")
