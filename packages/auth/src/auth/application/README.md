# Auth Application Layer

The application layer coordinates auth use cases: load domain objects, call
domain behavior, use repository interfaces, and return DTOs.

Contents:

- `commands` — register, login, and logout use cases.
- `queries` — current user and authenticated principal resolution.
- `dto` — application input and output records.
- `ports.py` — password hasher, session token, and optional registration callback ports.
- `exceptions.py` — application-level failure types.
