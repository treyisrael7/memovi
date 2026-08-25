# Auth API Layer

The API layer owns transport-specific auth entry points. It translates HTTP
requests into application use cases and maps application results or errors back
to HTTP responses.

Contents:

- `router.py` — `/auth` routes for register, login, logout, and current user.
- `session_cookies.py` — local client Origins and SameSite/Secure/Partitioned flags
  (Lax for same-site dev/web; None+Secure+Partitioned for packaged Tauri Origins).
- `schemas.py` — request and response schemas.
- `dependencies.py` — FastAPI dependency wiring (repositories, session cookie/TTL
  from `memovi_config.AuthSettings`).
