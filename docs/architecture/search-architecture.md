# Search Architecture

# Purpose

This document defines the responsibilities and boundaries of Search within Memovi.

# Scope

It covers retrieval responsibility, supported retrieval strategies, indexes, ranking, storage relationship, pipeline relationship, and boundaries with Memory and Intelligence.

# Relationship to ARCHITECTURE.md

[`../ARCHITECTURE.md`](../ARCHITECTURE.md) identifies Search as a core domain and retrieval as a pipeline stage. This document expands that concern without changing the high-level blueprint.

# Search Responsibility

Search is responsible for retrieving knowledge.

It determines how information is discovered, not how it is stored.

Search should support multiple retrieval strategies without exposing implementation details to consumers.

# Ownership

Search owns:

* Full-text search
* Vector search
* Hybrid retrieval
* Metadata filtering
* Ranking
* Query planning
* Retrieval optimization

Search does not own:

* Knowledge storage
* AI responses
* Documents
* Connectors

Search retrieves. It does not generate answers.

Retrieval is workspace-scoped. Keyword, semantic, and hybrid paths require `workspace_id` at the SQL/filter boundary before ranking so results cannot leak across ownership contexts.

# Retrieval Strategies

Retrieval may combine multiple techniques.

Examples include:

* Keyword search
* Vector similarity
* Metadata filtering
* Hybrid ranking
* Future graph traversal

The architecture allows multiple retrieval techniques to coexist because each serves a different discovery need.

Unified retrieval is orchestrated by `RetrievalEngine` / `RetrieveKnowledge` with
modes `keyword`, `semantic`, and `hybrid` (RRF fusion). Metadata filters are applied
after retrieval and fusion.

# Indexing

Knowledge becomes retrievable through indexing.

Multiple indexes may exist simultaneously:

* Full-text index
* Vector index
* Metadata index
* Future graph index

Indexes are derived artifacts. They can always be rebuilt from the underlying knowledge.

For this reason, indexes should never become the primary source of truth.

# Vector Storage

Vector storage enables semantic retrieval.

Vectors represent derived knowledge rather than business entities. Embeddings should always be reproducible from stored documents.

Memovi keeps vector storage within PostgreSQL through pgvector to preserve a single operational database, transaction consistency, simplified backups, reduced operational overhead, shared metadata, and easier development.

Search persists embeddings as `vector(N)` with an HNSW index using cosine distance, and exposes semantic retrieval through `SemanticSearch` / `GET /search/semantic`. Embeddings remain derived data regenerable from Memory.

Dedicated vector databases may be evaluated in the future if operational scale requires them.

See [`storage-architecture.md`](storage-architecture.md).

# Embedding Providers

Embedding generation is isolated behind an `EmbeddingProvider` protocol owned by Search.

Application code calls `EmbeddingGenerationService`, which remains provider-agnostic.
Concrete adapters (OpenAI, Ollama, Sentence Transformers, and future providers) live in
infrastructure and are selected through configuration.

Provider SDKs must not leak into the domain model. Embedding vectors are validated as
domain value objects before they participate in indexing or retrieval workflows.

# Search in the Request Lifecycle

Search requests remain synchronous when retrieval can complete quickly.

```text
User
    │
    ▼
Search Query
    │
    ▼
Presentation
    │
    ▼
Search Domain
    │
    ▼
Retrieve Knowledge
    │
    ▼
Rank Results
    │
    ▼
Return Results
```

The request completes once retrieval has finished. No additional background processing is required for ordinary search.

See [`request-lifecycle.md`](request-lifecycle.md).

# Relationship to Intelligence

Intelligence consumes Search capabilities when assembling context.

Intelligence does not bypass Search to access persistence directly. Knowledge retrieval always occurs through Search and Memory.

Search returns knowledge. Intelligence reasons over retrieved knowledge.

See [`intelligence-architecture.md`](intelligence-architecture.md).

# Relationship to the Pipeline

Search participates in the Index and Retrieve stages of the knowledge pipeline.

Processing creates derived indexes. Retrieval uses those indexes to return relevant knowledge.

Retrieval never modifies knowledge.

# Key Decisions

* Search owns retrieval, ranking, filtering, and query planning.
* Search does not own knowledge storage or AI responses.
* Indexes are derived rather than authoritative.
* Vector data is derived and reproducible from stored documents.
* Embedding generation is provider-agnostic and selected through configuration.
* pgvector is used to avoid premature vector database specialization.
* Intelligence consumes Search instead of bypassing it.
* Retrieval returns knowledge and does not generate answers.

# Related Documents

* [`../ARCHITECTURE.md`](../ARCHITECTURE.md)
* [`domains.md`](domains.md)
* [`request-lifecycle.md`](request-lifecycle.md)
* [`knowledge-processing-pipeline.md`](knowledge-processing-pipeline.md)
* [`storage-architecture.md`](storage-architecture.md)
* [`intelligence-architecture.md`](intelligence-architecture.md)
