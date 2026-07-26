"""Composition-root authorization adapters."""

from __future__ import annotations

from collections.abc import Callable

from memovi_shared import WorkspaceId
from memovi_workspace.application.commands import (
    EnrollDefaultWorkspaceMember,
    EnrollDefaultWorkspaceMemberCommand,
)
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


class RequestScopedMembershipEnroller:
    """Enroll a user using the current request-scoped SQLAlchemy session."""

    def __init__(self, session: OrmSession) -> None:
        self._session = session

    def handle(self, *, user_id: str) -> None:
        EnrollDefaultWorkspaceMember(
            workspaces=SqlAlchemyWorkspaceRepository(self._session),
            memberships=SqlAlchemyWorkspaceMembershipRepository(self._session),
        ).execute(EnrollDefaultWorkspaceMemberCommand(user_id=user_id))
