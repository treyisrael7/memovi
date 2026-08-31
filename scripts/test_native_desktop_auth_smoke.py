from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest

_SCRIPT = Path(__file__).resolve().parent / "native_desktop_auth_smoke.py"


def load_smoke() -> Any:
    spec = importlib.util.spec_from_file_location("native_desktop_auth_smoke", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


smoke = load_smoke()


def passing_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": True,
        "origin": "http://tauri.localhost",
        "userAgent": "Mozilla/5.0 Edg/128.0",
        "documentCookieReadable": "",
        "steps": [
            {"name": "origin", "origin": "http://tauri.localhost"},
            {
                "name": "register",
                "status": 201,
                "email": "native-smoke-1@memovi.test",
            },
            {
                "name": "me_after_register",
                "status": 200,
                "email": "native-smoke-1@memovi.test",
            },
            {"name": "logout", "status": 204},
            {"name": "me_after_logout", "status": 401},
            {"name": "me_after_logout_repeat", "status": 401},
        ],
    }
    payload.update(overrides)
    return payload


def test_format_summary_is_comparable_across_platforms() -> None:
    text = smoke.format_summary(
        platform_name="linux",
        origin="tauri://localhost",
        api="http://127.0.0.1:8000",
        register=201,
        me_authenticated=200,
        logout=204,
        me_after_logout=401,
        me_repeat=401,
        result="PASS",
        os_label="Ubuntu 24.04",
        tauri="2.11.5",
        webview="WebKitGTK",
    )
    assert "platform=linux" in text
    assert "origin=tauri://localhost" in text
    assert "api=http://127.0.0.1:8000" in text
    assert "register=201" in text
    assert "me_authenticated=200" in text
    assert "logout=204" in text
    assert "me_after_logout=401" in text
    assert "me_repeat=401" in text
    assert "result=PASS" in text


def test_evaluate_report_pass(capsys: pytest.CaptureFixture[str]) -> None:
    code = smoke.evaluate_report(
        passing_payload(),
        api_base="http://127.0.0.1:8000",
        platform_name="windows",
        os_label="Windows test",
        tauri="2.11.5",
        webview="WebView2",
    )
    captured = capsys.readouterr()
    assert code == 0
    assert "result=PASS" in captured.out
    assert "platform=windows" in captured.out
    assert "origin=http://tauri.localhost" in captured.out


def test_evaluate_report_rejects_dev_origin() -> None:
    payload = passing_payload(origin="http://127.0.0.1:1420")
    assert smoke.evaluate_report(payload, api_base="http://127.0.0.1:8000") == 1


def test_evaluate_report_rejects_missing_origin() -> None:
    payload = passing_payload(origin="")
    assert smoke.evaluate_report(payload, api_base="http://127.0.0.1:8000") == 1


def test_evaluate_report_rejects_logout_still_authenticated() -> None:
    payload = passing_payload()
    for step in payload["steps"]:
        if step["name"] == "me_after_logout":
            step["status"] = 200
        if step["name"] == "me_after_logout_repeat":
            step["status"] = 200
    payload["ok"] = False
    payload["error"] = "expected 401 after logout, got 200"
    assert smoke.evaluate_report(payload, api_base="http://127.0.0.1:8000") == 1


def test_evaluate_report_requires_repeat_401() -> None:
    payload = passing_payload()
    for step in payload["steps"]:
        if step["name"] == "me_after_logout_repeat":
            step["status"] = 200
    payload["ok"] = False
    assert smoke.evaluate_report(payload, api_base="http://127.0.0.1:8000") == 1


def test_evaluate_report_rejects_email_mismatch() -> None:
    payload = passing_payload()
    for step in payload["steps"]:
        if step["name"] == "me_after_register":
            step["email"] = "someone-else@memovi.test"
    payload["ok"] = False
    assert smoke.evaluate_report(payload, api_base="http://127.0.0.1:8000") == 1


def test_evaluate_report_uses_observed_origin_not_a_hardcoded_scheme() -> None:
    payload = passing_payload(origin="tauri://localhost")
    for step in payload["steps"]:
        if step["name"] == "origin":
            step["origin"] = "tauri://localhost"
    code = smoke.evaluate_report(payload, api_base="http://127.0.0.1:8000", platform_name="macos")
    assert code == 0


def test_resolve_executable_uses_macos_app_binary(tmp_path: Path) -> None:
    app = tmp_path / "Memovi.app" / "Contents" / "MacOS"
    app.mkdir(parents=True)
    binary = app / "Memovi"
    binary.write_text("stub", encoding="utf-8")
    resolved = smoke.resolve_executable(tmp_path / "Memovi.app")
    assert resolved == binary
    assert smoke.is_launchable(tmp_path / "Memovi.app")


def test_find_binary_explicit_missing() -> None:
    assert smoke.find_binary(str(Path("/no/such/memovi-desktop")), include_debug=False) is None


def test_tauri_version_from_lock() -> None:
    version = smoke.tauri_version()
    assert version == "unknown" or version[0].isdigit()
