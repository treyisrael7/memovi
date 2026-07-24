from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from memovi_observability import timed_operation
from memovi_shared import WorkspaceId
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session as OrmSession

from memovi_intelligence.domain.entities import Conversation
from memovi_intelligence.domain.exceptions import ConversationNotFoundError
from memovi_intelligence.domain.value_objects import (
    Citation,
    ConversationHistory,
    ConversationId,
    ConversationRole,
    ConversationTurn,
)
from memovi_intelligence.infrastructure.persistence.models import (
    ConversationRecord,
    ConversationTurnRecord,
)

_REPO = "SqlAlchemyConversationRepository"


class SqlAlchemyConversationRepository:
    """SQLAlchemy-backed ConversationRepository for durable conversation state."""

    def __init__(self, session: OrmSession) -> None:
        self._session = session

    def create(self, *, workspace_id: WorkspaceId) -> Conversation:
        with timed_operation("repository.create", repository=_REPO):
            conversation = Conversation.create(workspace_id=workspace_id)
            self._session.add(
                ConversationRecord(
                    id=conversation.id.value,
                    workspace_id=conversation.workspace_id.value,
                    title=conversation.title,
                    created_at=conversation.created_at,
                    updated_at=conversation.updated_at,
                )
            )
            self._session.flush()
            return conversation

    def get(
        self,
        conversation_id: ConversationId,
        *,
        workspace_id: WorkspaceId,
    ) -> Conversation | None:
        with timed_operation("repository.get", repository=_REPO):
            record = (
                self._session.query(ConversationRecord)
                .filter(
                    ConversationRecord.id == conversation_id.value,
                    ConversationRecord.workspace_id == workspace_id.value,
                )
                .one_or_none()
            )
            if record is None:
                return None
            return self._to_domain(record)

    def list(self, *, workspace_id: WorkspaceId) -> tuple[Conversation, ...]:
        with timed_operation("repository.list", repository=_REPO):
            records = (
                self._session.query(ConversationRecord)
                .filter(ConversationRecord.workspace_id == workspace_id.value)
                .order_by(ConversationRecord.updated_at.desc())
                .all()
            )
            return tuple(self._to_domain(record) for record in records)

    def rename(
        self,
        conversation_id: ConversationId,
        title: str,
        *,
        workspace_id: WorkspaceId,
    ) -> Conversation:
        with timed_operation("repository.rename", repository=_REPO):
            record = (
                self._session.query(ConversationRecord)
                .filter(
                    ConversationRecord.id == conversation_id.value,
                    ConversationRecord.workspace_id == workspace_id.value,
                )
                .one_or_none()
            )
            if record is None:
                raise ConversationNotFoundError(
                    f"Conversation '{conversation_id.value}' was not found.",
                )
            updated = Conversation(
                id=ConversationId(record.id),
                workspace_id=WorkspaceId(record.workspace_id),
                title=title,
                history=ConversationHistory(turns=self._load_turns(record.id)),
                created_at=_as_utc(record.created_at),
                updated_at=datetime.now(UTC),
            )
            record.title = updated.title
            record.updated_at = updated.updated_at
            self._session.flush()
            return updated

    def delete(
        self,
        conversation_id: ConversationId,
        *,
        workspace_id: WorkspaceId,
    ) -> None:
        with timed_operation("repository.delete", repository=_REPO):
            record = (
                self._session.query(ConversationRecord)
                .filter(
                    ConversationRecord.id == conversation_id.value,
                    ConversationRecord.workspace_id == workspace_id.value,
                )
                .one_or_none()
            )
            if record is None:
                raise ConversationNotFoundError(
                    f"Conversation '{conversation_id.value}' was not found.",
                )
            self._session.execute(
                delete(ConversationTurnRecord).where(
                    ConversationTurnRecord.conversation_id == conversation_id.value
                )
            )
            self._session.delete(record)
            self._session.flush()

    def append_turn(
        self,
        conversation_id: ConversationId,
        turn: ConversationTurn,
        *,
        workspace_id: WorkspaceId,
    ) -> Conversation:
        record = (
            self._session.query(ConversationRecord)
            .filter(
                ConversationRecord.id == conversation_id.value,
                ConversationRecord.workspace_id == workspace_id.value,
            )
            .one_or_none()
        )
        if record is None:
            raise ConversationNotFoundError(
                f"Conversation '{conversation_id.value}' was not found.",
            )

        next_index = self._next_turn_index(conversation_id.value)
        self._session.add(
            ConversationTurnRecord(
                id=str(uuid4()),
                conversation_id=conversation_id.value,
                turn_index=next_index,
                role=turn.role.value,
                content=turn.content,
                timestamp=turn.timestamp,
                citations=_serialize_citations(turn.citations),
            )
        )
        record.updated_at = turn.timestamp
        self._session.flush()
        return self._to_domain(record)

    def list_turns(
        self,
        conversation_id: ConversationId,
        *,
        workspace_id: WorkspaceId,
    ) -> tuple[ConversationTurn, ...]:
        record = (
            self._session.query(ConversationRecord)
            .filter(
                ConversationRecord.id == conversation_id.value,
                ConversationRecord.workspace_id == workspace_id.value,
            )
            .one_or_none()
        )
        if record is None:
            raise ConversationNotFoundError(
                f"Conversation '{conversation_id.value}' was not found.",
            )
        return self._load_turns(conversation_id.value)

    def _next_turn_index(self, conversation_id: str) -> int:
        count = self._session.scalar(
            select(func.count())
            .select_from(ConversationTurnRecord)
            .where(ConversationTurnRecord.conversation_id == conversation_id)
        )
        return int(count or 0)

    def _load_turns(self, conversation_id: str) -> tuple[ConversationTurn, ...]:
        turn_records = self._session.scalars(
            select(ConversationTurnRecord)
            .where(ConversationTurnRecord.conversation_id == conversation_id)
            .order_by(ConversationTurnRecord.turn_index.asc())
        ).all()
        return tuple(_to_turn(turn_record) for turn_record in turn_records)

    def _to_domain(self, record: ConversationRecord) -> Conversation:
        return Conversation(
            id=ConversationId(record.id),
            workspace_id=WorkspaceId(record.workspace_id),
            title=getattr(record, "title", None) or "New conversation",
            history=ConversationHistory(turns=self._load_turns(record.id)),
            created_at=_as_utc(record.created_at),
            updated_at=_as_utc(record.updated_at),
        )


def _to_turn(record: ConversationTurnRecord) -> ConversationTurn:
    return ConversationTurn(
        role=ConversationRole(record.role),
        content=record.content,
        timestamp=_as_utc(record.timestamp),
        citations=_deserialize_citations(record.citations),
    )


def _serialize_citations(citations: tuple[Citation, ...]) -> list[dict[str, Any]]:
    return [
        {
            "document_id": citation.document_id,
            "chunk_id": citation.chunk_id,
            "document_title": citation.document_title,
            "score": citation.score,
        }
        for citation in citations
    ]


def _deserialize_citations(raw: object) -> tuple[Citation, ...]:
    if not raw:
        return ()
    if not isinstance(raw, list):
        raise TypeError("citations must deserialize from a JSON list.")
    return tuple(
        Citation(
            document_id=str(item["document_id"]),
            chunk_id=str(item["chunk_id"]),
            document_title=(
                None if item.get("document_title") is None else str(item["document_title"])
            ),
            score=_optional_float(item.get("score")),
        )
        for item in raw
    )


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float, str)):
        return float(value)
    raise TypeError(f"Expected numeric metadata value, got {type(value)!r}")


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
