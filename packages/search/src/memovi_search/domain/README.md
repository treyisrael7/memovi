# Search Domain Layer

The domain layer owns searchable projections and embedding invariants. It is
independent of FastAPI, databases, memory internals, vector stores, and AI SDKs.

Current contents:

- `entities` defines search documents, embeddings, and search results.
- `events` defines lightweight search domain facts.
- `providers` defines the `EmbeddingProvider` protocol for interchangeable generators.
- `retrievers` defines keyword and semantic retrieval strategies behind a shared protocol.
- `ranking` defines Reciprocal Rank Fusion and score normalization.
- `repositories` defines `SearchRepository` and `EmbeddingRepository` persistence
  interfaces, including cosine similarity search over embedding projections.
- `value_objects` defines immutable search identifiers and `EmbeddingVector`.
- `exceptions.py` defines domain-level failure types.

Search owns derived retrieval structures. Canonical knowledge remains in Memory.
