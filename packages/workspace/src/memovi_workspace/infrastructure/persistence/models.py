from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class WorkspaceRecord(Base):
    """Persistence model for workspace ownership boundaries."""

    __tablename__ = "workspace_workspaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WorkspaceMembershipRecord(Base):
    """Persistence model for authenticated workspace membership."""

    __tablename__ = "workspace_memberships"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "user_id",
            name="uq_workspace_memberships_workspace_user",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspace_workspaces.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WorkspaceMembershipEventRecord(Base):
    """Durable audit trail for workspace membership changes."""

    __tablename__ = "workspace_membership_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspace_workspaces.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor_user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    target_user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    detail: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
