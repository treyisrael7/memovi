# Memovi Intelligence

Intelligence domain boundary. This package owns AI-facing orchestration, provider
boundaries, API contracts, and events while keeping durable knowledge independent
from model providers.

## Current Scope

This package establishes Intelligence domain boundaries and the core reasoning
pipeline:

* Immutable reasoning concepts (`ReasoningRequest`, `ReasoningContext`, `ReasoningResult`)
* Conversation memory (`Conversation`, `ConversationTurn`, `ConversationHistory`, `ConversationId`)
* Unused `ToolCall` / `ToolResult` fields on `ReasoningResult` (`tool_calls` / `tool_results`) — retained type plumbing only; not an execution framework and not product-supported. Host actions use the Automation Capability Framework.
* Read-only execution tracing (`ExecutionTrace`, `ExecutionStage`, `StageTiming`, `ExecutionMetrics`)
* Provider-agnostic prompt construction (`Prompt`, `PromptMessage`, `PromptRole`, `PromptSection`)
* Citations attached to reasoning answers
* Context assembly via `ContextAssembler` (ordering, deduplication, document/chunk/token limits, optional conversation history)
* `PromptBuilder` transforms assembled context into deterministic prompts, including a separate conversation history section
* `ConversationService` and `ConversationRepository` for multi-turn conversation state
* `ModelGateway` selects the configured provider and executes prompts with gateway-owned metadata
* `Reason` command orchestration: retrieve → assemble → prompt → gateway → result, with per-stage timing
* `SendConversationMessage` use case: persist user/assistant turns around a Reason execution
* Conversation REST API (`POST/GET /conversations`, `GET/POST /conversations/{id}/messages`)
* Application ports for knowledge retrieval and reasoning providers
* Deterministic `FakeReasoningProvider` / `FakeKnowledgeRetriever` / `InMemoryConversationRepository` for tests; production `OpenAIReasoningProvider`; Search-backed retrieval and SQLAlchemy conversation persistence are wired in `apps/api`
* Package configuration with provider selection. V1 `INTELLIGENCE_PROVIDER` values: `fake`, `openai`. Reserved/future reasoning names (`anthropic`, `ollama`, `gemini`) are rejected at configuration validation. Embedding providers (`SEARCH_EMBEDDING_PROVIDER`) are separate and may include `ollama`.

It does not implement LLM tool calling, streaming/realtime channels beyond the
conversation SSE path, or agents. Desktop (and other) clients consume the
Conversation API; Intelligence does not own UI.

## Conversation API

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/conversations` | Create a conversation |
| `GET` | `/conversations/{conversation_id}` | Conversation metadata |
| `GET` | `/conversations/{conversation_id}/messages` | Ordered message history |
| `POST` | `/conversations/{conversation_id}/messages` | Send a user message and run Reason |

`POST .../messages` accepts `{"message": "..."}` and returns the assistant message,
citations, provider, model, conversation id, and execution metadata.

## Layout

```text
src/memovi_intelligence/
├── api/                  # REST routes, schemas, and dependencies
├── application/          # Use cases, commands, and ports
├── domain/               # Reasoning concepts and invariants
└── infrastructure/       # Provider and retrieval adapters
```
