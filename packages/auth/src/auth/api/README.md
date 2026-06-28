# Auth API Layer

The API layer owns transport-specific auth entry points. It translates HTTP
requests into application use cases and maps application results or errors back
to HTTP responses.

Current contents are placeholders only:

- `router.py` defines the auth router without endpoints.
- `schemas.py` will contain request and response schemas.
- `dependencies.py` will contain FastAPI dependency wiring.
