# Search Domain Layer

The domain layer owns searchable projections and embedding invariants. It is
independent of FastAPI, databases, memory internals, vector stores, and AI SDKs.

Current contents:

- `entities` defines search documents and embeddings.
- `events` defines lightweight search domain facts.
- `providers` defines the `EmbeddingProvider` protocol for interchangeable generators.
- `repositories` defines persistence interfaces owned by the domain.
- `value_objects` defines immutable search identifiers and `EmbeddingVector`.
- `exceptions.py` defines domain-level failure types.

Search owns derived retrieval structures. Canonical knowledge remains in Memory.
