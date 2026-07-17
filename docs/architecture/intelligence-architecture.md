# Intelligence Architecture

# Purpose

This document defines the role and boundaries of Intelligence within Memovi.

# Scope

It covers AI's architectural role, Intelligence ownership, provider isolation, RAG, summaries, planning, relationship to Search and Memory, and boundaries with the Knowledge Platform.

# Relationship to ARCHITECTURE.md

[`../../ARCHITECTURE.md`](../../ARCHITECTURE.md) establishes that AI consumes knowledge but does not own it. This document expands that constraint for Intelligence-specific behavior.

# Intelligence Role

The Intelligence Layer consumes knowledge.

It never owns knowledge.

The Intelligence domain applies reasoning to knowledge already managed by the platform and transforms retrieved knowledge into useful responses.

The Knowledge Platform must never depend upon Intelligence.

# Ownership

Intelligence owns:

* Chat
* Retrieval-Augmented Generation
* Prompt construction
* Provider routing
* Tool orchestration
* AI summaries
* Planning
* Reasoning
* Future autonomous workflows

Intelligence does not own:

* Knowledge persistence
* Search indexes
* User authentication
* Connector synchronization

Artificial intelligence is a consumer of knowledge rather than its owner.

# Package Foundation

The Intelligence package (`packages/intelligence`) establishes domain boundaries before
provider integrations land.

Core immutable concepts:

* `ReasoningRequest` — intent to reason over retrieved knowledge
* `ReasoningContext` — assembled knowledge context for a future provider
* `ReasoningResult` — immutable reasoning output

Application orchestration is owned by `ReasoningService`, which depends only on ports:

* `KnowledgeRetriever` — future Search-facing retrieval boundary
* `ReasoningProvider` — future AI provider boundary

Infrastructure currently provides placeholder adapters that raise `NotImplementedError`.
Package configuration exists without provider selection. Chat, prompts, streaming, and
agents remain out of scope until later milestones.

# Provider Isolation

Provider-specific logic remains isolated within Intelligence.

Replacing one AI provider with another should require minimal architectural change because knowledge storage, retrieval, and memory remain independent from provider implementations.

The architecture supports the project technologies identified for AI, including Ollama, OpenAI, Anthropic, and Sentence Transformers, without making any one provider the foundation of the platform.

# Retrieval-Augmented Generation

AI conversations combine multiple domains.

```text
User
    │
    ▼
Question
    │
    ▼
Presentation
    │
    ▼
Intelligence
    │
    ▼
Search
    │
    ▼
Memory
    │
    ▼
Context Assembly
    │
    ▼
Provider
    │
    ▼
Response
```

Knowledge retrieval always occurs through Search and Memory.

The Intelligence domain consumes platform capabilities. It does not access persistence directly.

# Summaries and Enrichment

AI summaries are part of Intelligence, but they are not the authoritative source of knowledge.

When summaries are derived artifacts, they should be reproducible from authoritative stored knowledge and original documents.

This preserves the principle that knowledge remains independent from AI providers.

# Planning and Future Agents

The Intelligence domain may support planning, reasoning, tool execution, and future autonomous workflows.

These capabilities should reason over retrieved knowledge without modifying the underlying platform ownership model.

Future autonomous agents remain consumers of platform capabilities.

# Relationship to Search

Search retrieves knowledge.

Intelligence reasons over retrieved knowledge.

Search does not generate answers, and Intelligence should not bypass Search to retrieve from persistence directly.

See [`search-architecture.md`](search-architecture.md).

# Relationship to the Knowledge Pipeline

Intelligence is the final stage of the pipeline after retrieval.

It consumes normalized, stored, indexed, and retrieved knowledge.

It should not create parallel workflows that bypass acquisition, normalization, storage, indexing, or retrieval.

See [`knowledge-processing-pipeline.md`](knowledge-processing-pipeline.md).

# Key Decisions

* AI consumes knowledge; it does not own knowledge.
* The Knowledge Platform must not depend on Intelligence.
* Provider-specific logic remains isolated within Intelligence.
* RAG uses Search and Memory rather than direct persistence access.
* AI summaries are derived and should not become the source of truth.
* Future agents consume platform capabilities without redefining ownership.
* Knowledge remains independently useful when no language model is available.

# Related Documents

* [`../../ARCHITECTURE.md`](../../ARCHITECTURE.md)
* [`domains.md`](domains.md)
* [`search-architecture.md`](search-architecture.md)
* [`knowledge-processing-pipeline.md`](knowledge-processing-pipeline.md)
* [`storage-architecture.md`](storage-architecture.md)
* [`observability.md`](observability.md)
