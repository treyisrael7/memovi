from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ConversationRecord(Base):
    """Persistence model for multi-turn conversation metadata."""

    __tablename__ = "intelligence_conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="New conversation")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ConversationTurnRecord(Base):
    """Persistence model for an ordered conversation turn."""

    __tablename__ = "intelligence_conversation_turns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("intelligence_conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    citations: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)

    __table_args__ = (
        UniqueConstraint(
            "conversation_id",
            "turn_index",
            name="uq_intelligence_conversation_turns_conversation_index",
        ),
    )
