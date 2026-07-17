# Memovi Intelligence

Intelligence domain boundary. This package owns AI-facing orchestration, provider
boundaries, API contracts, and events while keeping durable knowledge independent
from model providers.

## Current Scope

This package establishes Intelligence domain boundaries and the core reasoning
pipeline:

* Immutable reasoning concepts (`ReasoningRequest`, `ReasoningContext`, `ReasoningResult`)
* Provider-agnostic prompt construction (`Prompt`, `PromptMessage`, `PromptRole`, `PromptSection`)
* Citations attached to reasoning answers
* Context assembly via `ContextAssembler` (ordering, deduplication, document/chunk/token limits)
* `PromptBuilder` transforms assembled context into deterministic prompts
* `ModelGateway` selects the configured provider and executes prompts with gateway-owned metadata
* `Reason` command orchestration: retrieve → assemble → prompt → gateway → result
* Application ports for knowledge retrieval and reasoning providers
* Deterministic `FakeReasoningProvider` and production `OpenAIReasoningProvider` adapters
* Placeholder infrastructure adapters for unfinished Search/LLM integrations
* Package configuration with provider selection (`provider=fake|openai`; future: anthropic, ollama, gemini)

It does not yet implement LLM integrations, chat, conversations, streaming, or agents.

## Layout

```text
src/memovi_intelligence/
├── api/                  # Transport entry points (reserved)
├── application/          # Use cases, commands, and ports
├── domain/               # Reasoning concepts and invariants
└── infrastructure/       # Provider and retrieval adapters
```
