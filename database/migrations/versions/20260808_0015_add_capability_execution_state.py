"""add durable capability execution state table

Revision ID: 20260808_0015
Revises: 20260808_0014
Create Date: 2026-08-08 19:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260808_0015"
down_revision: str | None = "20260808_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "automation_capability_executions",
        sa.Column("execution_id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("session_id", sa.String(length=128), nullable=True),
        sa.Column("capability_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("permission_mode", sa.String(length=32), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=True),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False, server_default="api"),
        sa.Column("duration", sa.Float(), nullable=False, server_default="0"),
        sa.Column("output", sa.JSON(), nullable=True),
        sa.Column("error", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("pending_request", sa.JSON(), nullable=True),
        sa.Column("pending_auth", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_details", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_automation_capability_executions_workspace_id",
        "automation_capability_executions",
        ["workspace_id"],
    )
    op.create_index(
        "ix_automation_capability_executions_user_id",
        "automation_capability_executions",
        ["user_id"],
    )
    op.create_index(
        "ix_automation_capability_executions_capability_id",
        "automation_capability_executions",
        ["capability_id"],
    )
    op.create_index(
        "ix_automation_capability_executions_status",
        "automation_capability_executions",
        ["status"],
    )
    op.create_index(
        "ix_automation_capability_executions_conversation_id",
        "automation_capability_executions",
        ["conversation_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_automation_capability_executions_conversation_id",
        table_name="automation_capability_executions",
    )
    op.drop_index(
        "ix_automation_capability_executions_status",
        table_name="automation_capability_executions",
    )
    op.drop_index(
        "ix_automation_capability_executions_capability_id",
        table_name="automation_capability_executions",
    )
    op.drop_index(
        "ix_automation_capability_executions_user_id",
        table_name="automation_capability_executions",
    )
    op.drop_index(
        "ix_automation_capability_executions_workspace_id",
        table_name="automation_capability_executions",
    )
    op.drop_table("automation_capability_executions")
