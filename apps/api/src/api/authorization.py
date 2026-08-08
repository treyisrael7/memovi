"""Composition-root authorization adapters."""

from __future__ import annotations

from collections.abc import Callable

from auth.domain.value_objects import Email, UserId
from auth.infrastructure.repositories import SqlAlchemyUserRepository
from memovi_shared import WorkspaceId
from memovi_workspace.application.commands import (
    EnrollDefaultWorkspaceMember,
    EnrollDefaultWorkspaceMemberCommand,
)
from memovi_workspace.application.ports import UserDirectoryPort
from memovi_workspace.infrastructure.repositories import (
    SqlAlchemyWorkspaceMembershipRepository,
    SqlAlchemyWorkspaceRepository,
)
from sqlalchemy.orm import Session as OrmSession

SessionFactory = Callable[[], OrmSession]


class SqlAlchemyWorkspaceMembershipPort:
    """Workspace membership checks for CapabilityAuthorizationService."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def is_member(self, *, user_id: str, workspace_id: WorkspaceId) -> bool:
        session = self._session_factory()
        try:
            return SqlAlchemyWorkspaceMembershipRepository(session).is_member(
                user_id=user_id,
                workspace_id=workspace_id,
            )
        finally:
            session.close()

    def get_role(self, *, user_id: str, workspace_id: WorkspaceId) -> str | None:
        session = self._session_factory()
        try:
            membership = SqlAlchemyWorkspaceMembershipRepository(session).get(
                user_id=user_id,
                workspace_id=workspace_id,
            )
            return membership.role if membership is not None else None
        finally:
            session.close()


class SqlAlchemyUserDirectoryAdapter:
    """Auth user lookups for workspace membership invite/list enrichment."""

    def __init__(self, session: OrmSession) -> None:
        self._users = SqlAlchemyUserRepository(session)

    def find_user_id_by_email(self, email: str) -> str | None:
        try:
            user = self._users.get_by_email(Email(email.strip().lower()))
        except Exception:
            return None
        return user.id.value if user is not None else None

    def find_email_by_user_id(self, user_id: str) -> str | None:
        try:
            user = self._users.get_by_id(UserId(user_id.strip()))
        except Exception:
            return None
        return user.email.value if user is not None else None


def build_user_directory(session: OrmSession) -> UserDirectoryPort:
    return SqlAlchemyUserDirectoryAdapter(session)


class RequestScopedMembershipEnroller:
    """Enroll a user using the current request-scoped SQLAlchemy session."""

    def __init__(self, session: OrmSession) -> None:
        self._session = session

    def handle(self, *, user_id: str) -> None:
        EnrollDefaultWorkspaceMember(
            workspaces=SqlAlchemyWorkspaceRepository(self._session),
            memberships=SqlAlchemyWorkspaceMembershipRepository(self._session),
        ).execute(EnrollDefaultWorkspaceMemberCommand(user_id=user_id))
