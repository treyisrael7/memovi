"""create documents tables

Revision ID: 20260701_0002
Revises: 20260629_0001
Create Date: 2026-07-01 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260701_0002"
down_revision: str | None = "20260629_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "documents_documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "documents_document_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_documents_document_versions_document_id",
        "documents_document_versions",
        ["document_id"],
    )

    op.create_table(
        "documents_processing_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("document_version_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["documents_document_versions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_documents_processing_jobs_document_id",
        "documents_processing_jobs",
        ["document_id"],
    )
    op.create_index(
        "ix_documents_processing_jobs_document_version_id",
        "documents_processing_jobs",
        ["document_version_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_documents_processing_jobs_document_version_id",
        table_name="documents_processing_jobs",
    )
    op.drop_index(
        "ix_documents_processing_jobs_document_id",
        table_name="documents_processing_jobs",
    )
    op.drop_table("documents_processing_jobs")
    op.drop_index(
        "ix_documents_document_versions_document_id",
        table_name="documents_document_versions",
    )
    op.drop_table("documents_document_versions")
    op.drop_table("documents_documents")
