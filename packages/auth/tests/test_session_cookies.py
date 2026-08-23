from auth.api.session_cookies import (
    PACKAGED_TAURI_ORIGINS,
    session_cookie_flags,
)


def test_dev_desktop_origin_stays_lax_on_http() -> None:
    samesite, secure = session_cookie_flags(
        origin="http://127.0.0.1:1420",
        request_is_https=False,
    )
    assert samesite == "lax"
    assert secure is False


def test_https_without_origin_stays_lax_secure() -> None:
    samesite, secure = session_cookie_flags(origin=None, request_is_https=True)
    assert samesite == "lax"
    assert secure is True


def test_packaged_tauri_origins_use_none_and_secure() -> None:
    for origin in PACKAGED_TAURI_ORIGINS:
        samesite, secure = session_cookie_flags(origin=origin, request_is_https=False)
        assert samesite == "none", origin
        assert secure is True, origin


def test_unknown_origin_does_not_get_none() -> None:
    samesite, secure = session_cookie_flags(
        origin="https://evil.example",
        request_is_https=False,
    )
    assert samesite == "lax"
    assert secure is False
