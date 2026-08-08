"""add durable workflow library and history tables

Revision ID: 20260808_0016
Revises: 20260808_0015
Create Date: 2026-08-08 20:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260808_0016"
down_revision: str | None = "20260808_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "automation_workflow_definitions",
        sa.Column("workflow_id", sa.String(length=128), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), nullable=True),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("steps", sa.JSON(), nullable=False),
        sa.Column("variables", sa.JSON(), nullable=False),
        sa.Column("expected_outputs", sa.JSON(), nullable=False),
        sa.Column("required_capabilities", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_automation_workflow_definitions_workspace_id",
        "automation_workflow_definitions",
        ["workspace_id"],
    )

    op.create_table(
        "automation_workflow_history",
        sa.Column("instance_id", sa.String(length=36), primary_key=True),
        sa.Column("workflow_id", sa.String(length=128), nullable=False),
        sa.Column("workflow_name", sa.String(length=256), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration", sa.Float(), nullable=False, server_default="0"),
        sa.Column("result_summary", sa.JSON(), nullable=False),
        sa.Column("executed_capabilities", sa.JSON(), nullable=False),
        sa.Column("executed_steps", sa.JSON(), nullable=False),
        sa.Column("failed_steps", sa.JSON(), nullable=False),
        sa.Column("error_details", sa.JSON(), nullable=False),
        sa.Column("audit_references", sa.JSON(), nullable=False),
        sa.Column("full_result", sa.JSON(), nullable=True),
    )
    op.create_index(
        "ix_automation_workflow_history_workflow_id",
        "automation_workflow_history",
        ["workflow_id"],
    )
    op.create_index(
        "ix_automation_workflow_history_workspace_id",
        "automation_workflow_history",
        ["workspace_id"],
    )
    op.create_index(
        "ix_automation_workflow_history_user_id",
        "automation_workflow_history",
        ["user_id"],
    )
    op.create_index(
        "ix_automation_workflow_history_status",
        "automation_workflow_history",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_automation_workflow_history_status",
        table_name="automation_workflow_history",
    )
    op.drop_index(
        "ix_automation_workflow_history_user_id",
        table_name="automation_workflow_history",
    )
    op.drop_index(
        "ix_automation_workflow_history_workspace_id",
        table_name="automation_workflow_history",
    )
    op.drop_index(
        "ix_automation_workflow_history_workflow_id",
        table_name="automation_workflow_history",
    )
    op.drop_table("automation_workflow_history")
    op.drop_index(
        "ix_automation_workflow_definitions_workspace_id",
        table_name="automation_workflow_definitions",
    )
    op.drop_table("automation_workflow_definitions")
