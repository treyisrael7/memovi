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
* `ReasoningContext` — assembled knowledge context for prompt construction
* `Prompt` — provider-agnostic reasoning prompt (`PromptMessage`, `PromptRole`, `PromptSection`)
* `ReasoningResult` — immutable reasoning output with a read-only `execution_trace`
* `ExecutionTrace` — structured stage timings and aggregate metrics for a reasoning request
* `Conversation` / `ConversationHistory` / `ConversationTurn` — multi-turn conversation memory

`ReasoningContext` includes the originating request, retained retrieved knowledge,
assembled documents, assembly metadata, an estimated token count, and optional
trimmed conversation history.

`ReasoningResult` is immutable and includes the answer, citations, metadata, provider
name, execution time, the context that produced it, and an `execution_trace`.

The `Reason` command records timing for each pipeline stage (`retrieval`,
`context_assembly`, `prompt_build`, `provider_resolution`, `model_execution`) and
populates metrics such as provider, model, estimated input tokens, optional output
tokens, retrieved knowledge count, document count, and citation count. Timing is
owned by the command, not by providers.

`ConversationService` creates conversations, appends user and assistant turns, and
loads history through `ConversationRepository`. `ContextAssembler` may attach recent
conversation history under configurable turn and token limits; history never bypasses
those limits or the overall estimated-token budget. `PromptBuilder` renders history as
its own `conversation_history` section, separate from retrieved knowledge.

`ContextAssembler` builds that context through the `KnowledgeRetriever` port. It orders
by retrieval ranking, removes duplicate chunks, skips excess documents when limits
require it, and trims to configurable document, chunk, and estimated-token budgets.

`PromptBuilder` converts a `ReasoningContext` into a deterministic `Prompt` with ordered
sections for system instructions, user request, retrieved knowledge, citations, and
metadata. It does not encode OpenAI, Anthropic, or Ollama message schemas.

`ModelGateway` is the single entry point for executing prompts. It selects the configured
provider from an injected registry, isolates provider lifecycle from the reasoning
pipeline, and owns execution metadata (`provider`, `model`, `duration`,
`estimated_tokens`). It does not know HTTP or API keys. Implemented providers today are
`fake` and `openai`; `anthropic`, `ollama`, and `gemini` remain reserved configuration
values.

The central use case is the `Reason` command:

```text
ReasoningRequest
    │
    ▼
KnowledgeRetriever
    │
    ▼
ContextAssembler
    │
    ▼
PromptBuilder
    │
    ▼
ModelGateway
    │
    ▼
ReasoningProvider
    │
    ▼
ReasoningResult
```

Application ports remain:

* `KnowledgeRetriever` — future Search-facing retrieval boundary
* `ReasoningProvider` — future AI provider boundary (`reason(prompt) -> ReasoningResult`)

Infrastructure currently provides a deterministic `FakeReasoningProvider` for tests and
an `OpenAIReasoningProvider` adapter that maps provider-agnostic prompts to Chat
Completions. Placeholder adapters remain for unfinished Search wiring.
Package configuration supports provider selection. Chat, streaming, and agents remain
out of scope until later milestones.

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
