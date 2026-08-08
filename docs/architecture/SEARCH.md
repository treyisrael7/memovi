# Search Embedding Providers

# Purpose

This document describes how Memovi selects and runs embedding providers for
semantic search. It complements [`search-architecture.md`](search-architecture.md),
which owns retrieval boundaries and index design.

# Relationship to Architecture

Search owns the `EmbeddingProvider` protocol and embedding generation. The API
composition root wires a single configured provider into indexing, retrieval,
readiness checks, and Intelligence retrieval. No parallel provider abstraction
is introduced; adapters extend the existing Search protocol.

# Supported Providers

| Provider | Config value | Default model | Notes |
| --- | --- | --- | --- |
| Fake | `fake` | `fake-embedding-v1` | Deterministic local vectors for tests, offline demos, and explicit local development |
| OpenAI | `openai` | `text-embedding-3-small` | Requires API key; requests schema-matched `dimensions` |
| Ollama | `ollama` | `all-minilm` | Local HTTP endpoint; model output must match schema dimensions |
| Sentence Transformers | `sentence_transformer` | `all-MiniLM-L6-v2` | Local model; package install required |

Fake is never selected implicitly by production wiring. Composition always goes
through configuration. Local defaults use `SEARCH_EMBEDDING_PROVIDER=fake`
explicitly so demos and CI remain offline-capable.

# Configuration

Environment variables (loaded by `SearchEmbeddingConfig.from_env()`):

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `SEARCH_EMBEDDING_PROVIDER` | no | `fake` | `fake`, `openai`, `ollama`, or `sentence_transformer` |
| `SEARCH_EMBEDDING_MODEL` | no | provider default | Model override |
| `SEARCH_EMBEDDING_DIMENSIONS` | no | schema constant (`384`) | Must match pgvector column size |
| `SEARCH_EMBEDDING_ENDPOINT` | Ollama; optional OpenAI | Ollama `http://127.0.0.1:11434` | Base URL |
| `SEARCH_EMBEDDING_API_KEY` / `OPENAI_API_KEY` | OpenAI | — | Secret; never logged |
| `SEARCH_EMBEDDING_TIMEOUT_SECONDS` | no | `60` | Provider HTTP timeout |

Startup validates configuration and probes the selected provider. Invalid
provider names, missing models/keys, dimension mismatches, and unreachable
endpoints fail fast with no silent fallback to Fake.

# Vector Dimensions

pgvector stores fixed-size vectors (`EMBEDDING_VECTOR_DIMENSIONS = 384`).

All providers must emit vectors of that length. OpenAI uses the `dimensions`
request parameter. Ollama and Sentence Transformers must use models whose native
output matches the schema (defaults above do). Changing dimensions requires:

1. Updating `EMBEDDING_VECTOR_DIMENSIONS`
2. An Alembic migration that clears and recreates `search_embeddings.vector`
3. Full re-index from Memory

# Production Recommendations

* Prefer **OpenAI** `text-embedding-3-small` with the schema `dimensions` for managed
  production quality.
* Prefer **Ollama** `all-minilm` (or another 384-dim model) for self-hosted local
  inference without cloud API keys.
* Prefer **Sentence Transformers** `all-MiniLM-L6-v2` for in-process local
  embeddings when the optional `sentence-transformers` extra is installed.
* Set `SEARCH_EMBEDDING_PROVIDER` explicitly in production env. Do not rely on the
  local `fake` default outside development, tests, and offline demos.
* Keep `OPENAI_API_KEY` / `SEARCH_EMBEDDING_API_KEY` in secret stores; never commit
  them or log them.

# Composition Root

`apps/api` loads config at startup, builds the provider once, attaches it to
`app.state.embedding_provider`, and passes it into:

* Search index embedding handlers
* Search / Intelligence retrieval dependencies
* `/ready` embedding readiness

Factory entry point: `build_embedding_provider(...)`.

# Observability

Embedding calls record:

* Provider name and model
* Duration (`memovi.embedding.provider` / generation timings)
* Vector dimensions
* Success and failure counters

Secrets and raw prompt text are not logged by the provider adapters.

# Testing Strategy

* Unit tests cover config validation and each adapter with fakes/mocks (no network).
* Integration tests and local development use explicit `FakeEmbeddingProvider` /
  `SEARCH_EMBEDDING_PROVIDER=fake`.
* Production providers are not required for CI. Optional live smoke checks may call
  OpenAI/Ollama outside the default suite.
* Retrieval architecture tests remain provider-agnostic behind `EmbeddingProvider`.

# Related Documents

* [`search-architecture.md`](search-architecture.md) — retrieval ownership and indexes
* [`../STATUS.md`](../STATUS.md) — milestone progress
* [`MODEL_PROVIDER_FRAMEWORK.md`](MODEL_PROVIDER_FRAMEWORK.md) — optional future
  convergence of Search embeddings onto the shared model framework
