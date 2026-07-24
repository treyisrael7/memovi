"""Local presentation clients (desktop/web) need CORS for API calls from webviews."""

from api.app import create_app
from api.middleware import LOCAL_CLIENT_ORIGINS
from fastapi.testclient import TestClient


def test_cors_allows_tauri_dev_origin() -> None:
    client = TestClient(create_app())
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


def test_cors_allows_simple_get_from_desktop_origin() -> None:
    client = TestClient(create_app())
    origin = "http://127.0.0.1:1420"

    response = client.get("/health", headers={"Origin": origin})

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
    assert response.headers.get("access-control-allow-origin") == origin
