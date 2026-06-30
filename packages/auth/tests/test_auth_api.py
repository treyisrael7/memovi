from collections.abc import Iterator

from api.app import create_app
from auth.api.dependencies import get_database_session
from auth.infrastructure.persistence import Base
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


def build_test_client() -> tuple[TestClient, Engine]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

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
    app.dependency_overrides[get_database_session] = database_session
    return TestClient(app, base_url="https://testserver"), engine


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
