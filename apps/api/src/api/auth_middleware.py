"""ASGI middleware that requires authentication on non-public endpoints."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import cast

from auth.api.dependencies import SESSION_COOKIE_NAME
from auth.api.session_cookies import (
    NATIVE_SMOKE_REQUEST_HEADER,
    SESSION_RECEIVED_HEADER,
    cookie_header_value,
    describe_received_session_cookies,
)
from auth.application.dto import AuthenticatedPrincipal
from auth.infrastructure.repositories import (
    SqlAlchemySessionRepository,
    SqlAlchemyUserRepository,
)
from auth.infrastructure.security import SecureSessionTokenService
from memovi_observability import RequestContext, bind_request_context
from sqlalchemy.orm import Session as OrmSession
from starlette.types import ASGIApp, Receive, Scope, Send

from api.database import create_session

PUBLIC_PATHS = frozenset(
    {
        "/health",
        "/ready",
        "/auth/register",
        "/auth/login",
        "/openapi.json",
        "/docs",
        "/docs/oauth2-redirect",
        "/redoc",
    }
)


class AuthenticationMiddleware:
    """Reject unauthenticated access to non-public HTTP endpoints.

    Health, readiness, and auth login/register remain public. All other routes
    require a valid session cookie. Capability policy and membership checks are
    performed by Authorization Service / workspace dependencies.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self._tokens = SecureSessionTokenService()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "GET")
        if method == "OPTIONS" or path in PUBLIC_PATHS or path.startswith("/docs"):
            await self.app(scope, receive, send)
            return

        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        cookie_header = headers.get("cookie", "")
        session_token = cookie_header_value(cookie_header, SESSION_COOKIE_NAME)
        principal = self._resolve_principal(scope, session_token)
        if principal is None:
            extra_headers: list[tuple[bytes, bytes]] = [(b"cache-control", b"no-store")]
            if headers.get(NATIVE_SMOKE_REQUEST_HEADER) == "1":
                received = describe_received_session_cookies(cookie_header, SESSION_COOKIE_NAME)
                extra_headers.append(
                    (SESSION_RECEIVED_HEADER.lower().encode("ascii"), received.encode("ascii"))
                )
            await _send_json(
                send,
                status=401,
                body={"detail": "Authentication is required."},
                extra_headers=extra_headers,
            )
            return

        state = scope.setdefault("state", {})
        if isinstance(state, dict):
            state["authenticated_principal"] = principal
            current = state.get("request_context")
            if isinstance(current, RequestContext):
                updated = RequestContext(
                    request_id=current.request_id,
                    workspace_id=current.workspace_id,
                    correlation_id=current.correlation_id,
                    timestamp=current.timestamp,
                    principal=principal.user_id,
                )
                state["request_context"] = updated
                bind_request_context(updated)
        else:
            state.authenticated_principal = principal
            current = getattr(state, "request_context", None)
            if isinstance(current, RequestContext):
                updated = RequestContext(
                    request_id=current.request_id,
                    workspace_id=current.workspace_id,
                    correlation_id=current.correlation_id,
                    timestamp=current.timestamp,
                    principal=principal.user_id,
                )
                state.request_context = updated
                bind_request_context(updated)

        await self.app(scope, receive, send)

    def _session_factory(self, scope: Scope) -> Callable[[], OrmSession]:
        app = scope.get("app")
        if app is not None:
            factory = getattr(getattr(app, "state", None), "auth_session_factory", None)
            if callable(factory):
                return cast(Callable[[], OrmSession], factory)
        return create_session

    def _resolve_principal(
        self,
        scope: Scope,
        session_token: str | None,
    ) -> AuthenticatedPrincipal | None:
        if not session_token:
            return None
        session = self._session_factory(scope)()
        try:
            auth_session = SqlAlchemySessionRepository(session).get_by_token_hash(
                self._tokens.token_hash(session_token),
            )
            if auth_session is None or not auth_session.is_active(datetime.now(UTC)):
                return None
            user = SqlAlchemyUserRepository(session).get_by_id(auth_session.user_id)
            if user is None:
                return None
            return AuthenticatedPrincipal.from_user_and_session(user, auth_session)
        finally:
            session.close()


async def _send_json(
    send: Send,
    *,
    status: int,
    body: dict[str, object],
    extra_headers: list[tuple[bytes, bytes]] | None = None,
) -> None:
    payload = json.dumps(body).encode("utf-8")
    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(payload)).encode("ascii")),
    ]
    if extra_headers:
        headers.extend(extra_headers)
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": headers,
        }
    )
    await send({"type": "http.response.body", "body": payload})
