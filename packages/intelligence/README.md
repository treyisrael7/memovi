# Memovi Intelligence

Intelligence domain boundary. This package owns AI-facing orchestration, provider
boundaries, API contracts, and events while keeping durable knowledge independent
from model providers.

## Current Scope

This package establishes Intelligence domain boundaries and the core reasoning
pipeline:

* Immutable reasoning concepts (`ReasoningRequest`, `ReasoningContext`, `ReasoningResult`)
* Conversation memory (`Conversation`, `ConversationTurn`, `ConversationHistory`, `ConversationId`)
* Tool execution framework (`Tool`, `ToolRegistry`, `ToolExecutor`, `ToolCall`, `ToolResult`, `ToolDefinition`)
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
* Deterministic `FakeReasoningProvider` / `FakeKnowledgeRetriever` and production `OpenAIReasoningProvider` adapters
* Placeholder infrastructure adapters for unfinished Search integrations
* Package configuration with provider selection (`provider=fake|openai`; future: anthropic, ollama, gemini)

It does not yet implement concrete product tools, streaming, WebSockets, or agents.

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
