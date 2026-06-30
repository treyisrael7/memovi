from datetime import UTC, datetime

from sqlalchemy.orm import Session as OrmSession

from auth.domain.entities import Session
from auth.domain.value_objects import UserId
from auth.infrastructure.persistence.models import SessionRecord


class SqlAlchemySessionRepository:
    def __init__(self, session: OrmSession) -> None:
        self._session = session

    def get_by_token_hash(self, token_hash: str) -> Session | None:
        record = (
            self._session.query(SessionRecord)
            .filter(SessionRecord.token_hash == token_hash)
            .one_or_none()
        )
        if record is None:
            return None
        return self._to_domain(record)

    def add(self, session: Session) -> None:
        self._session.add(
            SessionRecord(
                id=session.id,
                user_id=session.user_id.value,
                token_hash=session.token_hash,
                created_at=session.created_at,
                expires_at=session.expires_at,
                revoked_at=session.revoked_at,
            )
        )

    def save(self, session: Session) -> None:
        record = self._session.get(SessionRecord, session.id)
        if record is None:
            self.add(session)
            return

        record.user_id = session.user_id.value
        record.token_hash = session.token_hash
        record.created_at = session.created_at
        record.expires_at = session.expires_at
        record.revoked_at = session.revoked_at

    def _to_domain(self, record: SessionRecord) -> Session:
        return Session(
            id=record.id,
            user_id=UserId(record.user_id),
            token_hash=record.token_hash,
            created_at=_as_utc(record.created_at),
            expires_at=_as_utc(record.expires_at),
            revoked_at=_as_utc(record.revoked_at) if record.revoked_at is not None else None,
        )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
