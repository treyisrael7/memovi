# Search Domain Layer

The domain layer owns searchable document concepts and invariants. It is
independent of FastAPI, databases, memory internals, vector stores, and AI SDKs.

Current contents:

- `entities` defines search documents and embedding metadata.
- `events` defines lightweight search domain facts.
- `repositories` defines persistence interfaces owned by the domain.
- `value_objects` defines immutable search identifiers.
- `exceptions.py` defines domain-level failure types.
