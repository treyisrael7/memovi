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
* `Reason` command orchestration: retrieve → assemble → prompt → reason → result
* Application ports for knowledge retrieval and reasoning providers
* Deterministic `FakeReasoningProvider` for tests and local wiring
* Placeholder infrastructure adapters for unfinished Search/LLM integrations
* Package configuration without provider selection

It does not yet implement LLM integrations, chat, conversations, streaming, or agents.

## Layout

```text
src/memovi_intelligence/
├── api/                  # Transport entry points (reserved)
├── application/          # Use cases, commands, and ports
├── domain/               # Reasoning concepts and invariants
└── infrastructure/       # Provider and retrieval adapters
```
