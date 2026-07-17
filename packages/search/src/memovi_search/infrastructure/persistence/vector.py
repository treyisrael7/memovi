"""Fixed embedding vector dimensions for pgvector storage.

The column type requires a fixed size. This matches the currently wired
`FakeEmbeddingProvider` and must stay in sync when production providers
are introduced (with a new migration).
"""

EMBEDDING_VECTOR_DIMENSIONS = 4
