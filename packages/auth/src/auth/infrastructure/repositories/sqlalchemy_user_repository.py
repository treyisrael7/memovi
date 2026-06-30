from datetime import UTC, datetime

from sqlalchemy.orm import Session as OrmSession

from auth.domain.entities import User
from auth.domain.value_objects import Email, PasswordHash, UserId
from auth.infrastructure.persistence.models import UserRecord


class SqlAlchemyUserRepository:
    def __init__(self, session: OrmSession) -> None:
        self._session = session

    def get_by_id(self, user_id: UserId) -> User | None:
        record = self._session.get(UserRecord, user_id.value)
        if record is None:
            return None
        return self._to_domain(record)

    def get_by_email(self, email: Email) -> User | None:
        record = (
            self._session.query(UserRecord).filter(UserRecord.email == email.value).one_or_none()
        )
        if record is None:
            return None
        return self._to_domain(record)

    def add(self, user: User) -> None:
        self._session.add(
            UserRecord(
                id=user.id.value,
                email=user.email.value,
                password_hash=user.password_hash.value,
                created_at=user.created_at,
            )
        )

    def _to_domain(self, record: UserRecord) -> User:
        return User(
            id=UserId(record.id),
            email=Email(record.email),
            password_hash=PasswordHash(record.password_hash),
            created_at=_as_utc(record.created_at),
        )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
