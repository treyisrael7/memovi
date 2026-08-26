from collections.abc import Iterator
from datetime import UTC, datetime

from api.app import create_app
from api.document_processing import configure_document_processing
from auth.api.dependencies import get_database_session
from auth.api.session_cookies import PACKAGED_TAURI_ORIGINS
from auth.infrastructure.persistence import Base as AuthBase
from documents.application.workers import DocumentProcessingWorkerConfig
from documents.infrastructure.queue import InMemoryProcessingJobQueue
from documents.infrastructure.storage import InMemoryObjectStorage
from fastapi.testclient import TestClient
from httpx import Response
from memovi_shared import DEFAULT_WORKSPACE_ID
from memovi_workspace.infrastructure.persistence import Base as WorkspaceBase
from memovi_workspace.infrastructure.persistence.models import WorkspaceRecord
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


def _cookie_header(response: Response) -> str:
    headers = response.headers
    return headers.get("set-cookie") or ""


def _cookie_request_header(set_cookie: str) -> str:
    """First name=value pair. TestClient will not store Secure cookies on http://."""
    return set_cookie.split(";", 1)[0].strip()


def _assert_packaged_creation_cookie(cookie: str) -> None:
    lower = cookie.lower()
    assert "memovi_session=" in cookie
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "samesite=none" in lower
    assert "partitioned" in lower
    assert "path=/" in lower
    assert "max-age=0" not in lower
    assert "01 jan 1970" not in lower


def _assert_deletion_cookie(cookie: str, *, partitioned: bool, secure: bool) -> None:
    lower = cookie.lower()
    assert "memovi_session=" in cookie
    assert "HttpOnly" in cookie
    assert "path=/" in lower
    assert "max-age=0" in lower
    assert "01 jan 1970" in lower
    if secure:
        assert "Secure" in cookie
    else:
        assert "Secure" not in cookie
    if partitioned:
        assert "samesite=none" in lower
        assert "partitioned" in lower
    else:
        assert "partitioned" not in lower


def build_test_client(*, base_url: str = "https://testserver") -> tuple[TestClient, Engine]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    AuthBase.metadata.create_all(engine)
    WorkspaceBase.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    with Session(engine) as session:
        session.add(
            WorkspaceRecord(
                id=DEFAULT_WORKSPACE_ID.value,
                name="Default",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )
        session.commit()

    def database_session() -> Iterator[Session]:
        session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app = create_app()
    app.state.auth_session_factory = session_factory
    configure_document_processing(
        app,
        session_factory=session_factory,
        queue=InMemoryProcessingJobQueue(),
        worker_config=DocumentProcessingWorkerConfig(
            max_retries=1,
            poll_interval_seconds=0.05,
        ),
        object_storage=InMemoryObjectStorage(),
    )
    app.dependency_overrides[get_database_session] = database_session
    return TestClient(app, base_url=base_url), engine


def test_complete_auth_flow() -> None:
    client, engine = build_test_client()
    try:
        with client:
            register_response = client.post(
                "/auth/register",
                json={"email": "USER@example.com", "password": "password123"},
            )
            assert register_response.status_code == 201
            assert register_response.json()["email"] == "user@example.com"
            assert "memovi_session=" in register_response.headers["set-cookie"]
            assert "HttpOnly" in register_response.headers["set-cookie"]
            assert "Secure" in register_response.headers["set-cookie"]

            me_response = client.get("/auth/me")
            assert me_response.status_code == 200
            assert me_response.json()["email"] == "user@example.com"

            logout_response = client.post("/auth/logout")
            assert logout_response.status_code == 204

            logged_out_response = client.get("/auth/me")
            assert logged_out_response.status_code == 401

            login_response = client.post(
                "/auth/login",
                json={"email": "user@example.com", "password": "password123"},
            )
            assert login_response.status_code == 200
            assert login_response.json()["email"] == "user@example.com"
    finally:
        engine.dispose()


def test_register_rejects_duplicate_email() -> None:
    client, engine = build_test_client()
    try:
        with client:
            first_response = client.post(
                "/auth/register",
                json={"email": "user@example.com", "password": "password123"},
            )
            assert first_response.status_code == 201

            duplicate_response = client.post(
                "/auth/register",
                json={"email": "USER@example.com", "password": "password123"},
            )
            assert duplicate_response.status_code == 409
    finally:
        engine.dispose()


def test_login_rejects_invalid_password() -> None:
    client, engine = build_test_client()
    try:
        with client:
            register_response = client.post(
                "/auth/register",
                json={"email": "user@example.com", "password": "password123"},
            )
            assert register_response.status_code == 201

            login_response = client.post(
                "/auth/login",
                json={"email": "user@example.com", "password": "wrong-password"},
            )
            assert login_response.status_code == 401
    finally:
        engine.dispose()


def test_protected_endpoint_requires_authentication() -> None:
    client, engine = build_test_client()
    try:
        with client:
            response = client.get("/workspaces")
            assert response.status_code == 401
    finally:
        engine.dispose()


def test_dev_desktop_origin_sets_lax_http_cookie() -> None:
    client, engine = build_test_client(base_url="http://testserver")
    origin = "http://127.0.0.1:1420"
    try:
        with client:
            register_response = client.post(
                "/auth/register",
                json={"email": "dev@example.com", "password": "password123"},
                headers={"Origin": origin},
            )
            assert register_response.status_code == 201
            cookie = _cookie_header(register_response)
            assert "memovi_session=" in cookie
            assert "HttpOnly" in cookie
            assert "Secure" not in cookie
            assert "SameSite=lax" in cookie.lower() or "samesite=lax" in cookie.lower()
            assert "partitioned" not in cookie.lower()

            me_response = client.get("/auth/me", headers={"Origin": origin})
            assert me_response.status_code == 200
            assert me_response.json()["email"] == "dev@example.com"

            logout_response = client.post("/auth/logout", headers={"Origin": origin})
            assert logout_response.status_code == 204
            logout_cookie = _cookie_header(logout_response)
            _assert_deletion_cookie(logout_cookie, partitioned=False, secure=False)
            assert "samesite=lax" in logout_cookie.lower()
    finally:
        engine.dispose()


def test_packaged_tauri_origin_sets_none_secure_cookie_and_session_works() -> None:
    client, engine = build_test_client(base_url="http://testserver")
    origin = PACKAGED_TAURI_ORIGINS[1]  # https://tauri.localhost
    try:
        with client:
            register_response = client.post(
                "/auth/register",
                json={"email": "tauri@example.com", "password": "password123"},
                headers={"Origin": origin},
            )
            assert register_response.status_code == 201
            cookie = _cookie_header(register_response)
            _assert_packaged_creation_cookie(cookie)
            assert register_response.headers.get("access-control-allow-origin") == origin
            assert register_response.headers.get("access-control-allow-credentials") == "true"

            # httpx/TestClient will not persist Secure cookies on http://; send the
            # token explicitly the way a WebView Cookie header would.
            cookie_header = _cookie_request_header(cookie)
            me_response = client.get(
                "/auth/me",
                headers={"Origin": origin, "Cookie": cookie_header},
            )
            assert me_response.status_code == 200
            assert me_response.json()["email"] == "tauri@example.com"
            assert me_response.headers.get("access-control-allow-origin") == origin
            assert me_response.headers.get("access-control-allow-credentials") == "true"

            logout_response = client.post(
                "/auth/logout",
                headers={"Origin": origin, "Cookie": cookie_header},
            )
            assert logout_response.status_code == 204
            logout_cookie = _cookie_header(logout_response)
            _assert_deletion_cookie(logout_cookie, partitioned=True, secure=True)

            logged_out = client.get(
                "/auth/me",
                headers={"Origin": origin, "Cookie": cookie_header},
            )
            assert logged_out.status_code == 401

            login_response = client.post(
                "/auth/login",
                json={"email": "tauri@example.com", "password": "password123"},
                headers={"Origin": origin},
            )
            assert login_response.status_code == 200
            assert "samesite=none" in _cookie_header(login_response).lower()
            assert "partitioned" in _cookie_header(login_response).lower()

            restored = client.get(
                "/auth/me",
                headers={
                    "Origin": origin,
                    "Cookie": _cookie_request_header(_cookie_header(login_response)),
                },
            )
            assert restored.status_code == 200
    finally:
        engine.dispose()


def test_packaged_tauri_custom_scheme_origin_sets_none_secure_cookie() -> None:
    client, engine = build_test_client(base_url="http://testserver")
    try:
        with client:
            response = client.post(
                "/auth/register",
                json={"email": "scheme@example.com", "password": "password123"},
                headers={"Origin": "tauri://localhost"},
            )
            assert response.status_code == 201
            cookie = _cookie_header(response).lower()
            assert "samesite=none" in cookie
            assert "secure" in cookie
            assert "httponly" in cookie
            assert "partitioned" in cookie
    finally:
        engine.dispose()


def test_windows_packaged_origin_logout_deletes_chips_cookie() -> None:
    client, engine = build_test_client(base_url="http://testserver")
    origin = "http://tauri.localhost"
    try:
        with client:
            register_response = client.post(
                "/auth/register",
                json={"email": "webview@example.com", "password": "password123"},
                headers={"Origin": origin},
            )
            assert register_response.status_code == 201
            created = _cookie_header(register_response)
            _assert_packaged_creation_cookie(created)

            logout_response = client.post(
                "/auth/logout",
                headers={
                    "Origin": origin,
                    "Cookie": _cookie_request_header(created),
                    "X-Memovi-Native-Smoke": "1",
                },
            )
            assert logout_response.status_code == 204
            deleted = _cookie_header(logout_response)
            _assert_deletion_cookie(deleted, partitioned=True, secure=True)
            contract = logout_response.headers.get("X-Memovi-Session-Cookie") or ""
            assert "Partitioned" in contract
            assert "Max-Age=0" in contract
            assert "1970" in contract
            received = logout_response.headers.get("X-Memovi-Session-Received") or ""
            assert received.startswith("n=1;fp=")
            token = _cookie_request_header(created).split("=", 1)[1]
            assert token not in received
            assert token not in contract
    finally:
        engine.dispose()


def test_logout_revokes_every_duplicate_session_cookie() -> None:
    client, engine = build_test_client(base_url="http://testserver")
    origin = "http://tauri.localhost"
    try:
        with client:
            register_response = client.post(
                "/auth/register",
                json={"email": "dup@example.com", "password": "password123"},
                headers={"Origin": origin},
            )
            first = _cookie_request_header(_cookie_header(register_response))
            login_response = client.post(
                "/auth/login",
                json={"email": "dup@example.com", "password": "password123"},
                headers={"Origin": origin},
            )
            second = _cookie_request_header(_cookie_header(login_response))
            assert first != second

            logout_response = client.post(
                "/auth/logout",
                headers={"Origin": origin, "Cookie": f"{first}; {second}"},
            )
            assert logout_response.status_code == 204

            assert (
                client.get("/auth/me", headers={"Origin": origin, "Cookie": first}).status_code
                == 401
            )
            assert (
                client.get("/auth/me", headers={"Origin": origin, "Cookie": second}).status_code
                == 401
            )
    finally:
        engine.dispose()


def test_auth_me_is_not_cacheable() -> None:
    client, engine = build_test_client()
    try:
        with client:
            client.post(
                "/auth/register",
                json={"email": "cache@example.com", "password": "password123"},
            )
            me_response = client.get("/auth/me")
            assert me_response.status_code == 200
            assert me_response.headers.get("cache-control") == "no-store"
    finally:
        engine.dispose()
