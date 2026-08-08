"""Fixed embedding vector dimensions for pgvector storage.

The column type requires a fixed size. Production providers and Fake must emit
vectors of this length. Changing the size requires a new Alembic migration and
a full re-index of ``search_embeddings``.
"""

EMBEDDING_VECTOR_DIMENSIONS = 384
