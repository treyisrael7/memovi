from auth.api.session_cookies import (
    PACKAGED_TAURI_ORIGINS,
    cookie_header_value,
    session_cookie_flags,
)


def test_dev_desktop_origin_stays_lax_on_http() -> None:
    flags = session_cookie_flags(
        origin="http://127.0.0.1:1420",
        request_is_https=False,
    )
    assert flags.samesite == "lax"
    assert flags.secure is False
    assert flags.partitioned is False


def test_https_without_origin_stays_lax_secure() -> None:
    flags = session_cookie_flags(origin=None, request_is_https=True)
    assert flags.samesite == "lax"
    assert flags.secure is True
    assert flags.partitioned is False


def test_packaged_tauri_origins_use_none_secure_partitioned() -> None:
    for origin in PACKAGED_TAURI_ORIGINS:
        flags = session_cookie_flags(origin=origin, request_is_https=False)
        assert flags.samesite == "none", origin
        assert flags.secure is True, origin
        assert flags.partitioned is True, origin


def test_cookie_header_value_reads_session_name() -> None:
    assert cookie_header_value("memovi_session=abc; other=x", "memovi_session") == "abc"
    assert cookie_header_value(None, "memovi_session") is None


def test_unknown_origin_does_not_get_none() -> None:
    flags = session_cookie_flags(
        origin="https://evil.example",
        request_is_https=False,
    )
    assert flags.samesite == "lax"
    assert flags.secure is False
    assert flags.partitioned is False
