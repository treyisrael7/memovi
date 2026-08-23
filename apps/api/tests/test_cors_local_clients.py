"""Local presentation clients (desktop/web) need CORS for API calls from webviews."""

import pytest
from api.app import create_app
from api.middleware import LOCAL_CLIENT_ORIGINS
from auth.api.session_cookies import PACKAGED_TAURI_ORIGINS
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("MEMOVI_OBJECT_STORAGE", "memory")
    monkeypatch.setenv("MEMOVI_ENV", "local")
    return TestClient(create_app())


def test_cors_allows_tauri_dev_origin(client: TestClient) -> None:
    origin = "http://localhost:1420"
    assert origin in LOCAL_CLIENT_ORIGINS

    response = client.options(
        "/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin


def test_cors_allows_simple_get_from_desktop_origin(client: TestClient) -> None:
    origin = "http://127.0.0.1:1420"

    response = client.get("/health", headers={"Origin": origin})

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
    assert response.headers.get("access-control-allow-origin") == origin
    assert response.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.parametrize("origin", PACKAGED_TAURI_ORIGINS)
def test_cors_allows_credentialed_preflight_from_packaged_tauri(
    client: TestClient,
    origin: str,
) -> None:
    assert origin in LOCAL_CLIENT_ORIGINS

    response = client.options(
        "/auth/login",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin
    assert response.headers.get("access-control-allow-credentials") == "true"
    allow_headers = response.headers.get("access-control-allow-headers", "").lower()
    assert "content-type" in allow_headers


def test_cors_rejects_unknown_origin_for_credentialed_access(client: TestClient) -> None:
    origin = "https://evil.example"

    response = client.get("/health", headers={"Origin": origin})

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") != origin
    assert response.headers.get("access-control-allow-origin") is None
    # Starlette still emits Allow-Credentials when the middleware is credentialed;
    # browsers ignore it without a matching Allow-Origin.
