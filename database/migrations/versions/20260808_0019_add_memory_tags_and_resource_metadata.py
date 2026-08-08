"""add memory tags and resource metadata tables

Revision ID: 20260808_0019
Revises: 20260808_0018
Create Date: 2026-08-08 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260808_0019"
down_revision: str | None = "20260808_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "memory_tags",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("name_key", sa.String(length=256), nullable=False),
        sa.Column("color", sa.String(length=64), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "name_key",
            name="uq_memory_tags_workspace_name_key",
        ),
    )
    op.create_index("ix_memory_tags_workspace_id", "memory_tags", ["workspace_id"])

    op.create_table(
        "memory_tag_assignments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tag_id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("member_kind", sa.String(length=32), nullable=False),
        sa.Column("member_id", sa.String(length=256), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["memory_tags.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tag_id",
            "member_kind",
            "member_id",
            name="uq_memory_tag_assignments_item",
        ),
    )
    op.create_index(
        "ix_memory_tag_assignments_tag_id",
        "memory_tag_assignments",
        ["tag_id"],
    )
    op.create_index(
        "ix_memory_tag_assignments_workspace_id",
        "memory_tag_assignments",
        ["workspace_id"],
    )
    op.create_index(
        "ix_memory_tag_assignments_member_kind",
        "memory_tag_assignments",
        ["member_kind"],
    )
    op.create_index(
        "ix_memory_tag_assignments_member_id",
        "memory_tag_assignments",
        ["member_id"],
    )

    op.create_table(
        "memory_resource_metadata",
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("member_kind", sa.String(length=32), nullable=False),
        sa.Column("member_id", sa.String(length=256), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("workspace_id", "member_kind", "member_id"),
    )


def downgrade() -> None:
    op.drop_table("memory_resource_metadata")

    op.drop_index(
        "ix_memory_tag_assignments_member_id",
        table_name="memory_tag_assignments",
    )
    op.drop_index(
        "ix_memory_tag_assignments_member_kind",
        table_name="memory_tag_assignments",
    )
    op.drop_index(
        "ix_memory_tag_assignments_workspace_id",
        table_name="memory_tag_assignments",
    )
    op.drop_index(
        "ix_memory_tag_assignments_tag_id",
        table_name="memory_tag_assignments",
    )
    op.drop_table("memory_tag_assignments")

    op.drop_index("ix_memory_tags_workspace_id", table_name="memory_tags")
    op.drop_table("memory_tags")
