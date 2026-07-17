# Memovi Intelligence

Intelligence domain boundary. This package owns AI-facing orchestration, provider
boundaries, API contracts, and events while keeping durable knowledge independent
from model providers.

## Current Scope

This package establishes Intelligence domain boundaries:

* Immutable reasoning concepts (`ReasoningRequest`, `ReasoningContext`, `ReasoningResult`)
* Context assembly via `ContextAssembler` (ordering, deduplication, document/chunk/token limits)
* Application ports for knowledge retrieval and reasoning providers
* `ReasoningService` orchestration surface (providers not wired yet)
* Placeholder infrastructure adapters
* Package configuration without provider selection

It does not yet implement LLM integrations, prompts, chat, conversations, streaming,
or agents.

## Layout

```text
src/memovi_intelligence/
├── api/                  # Transport entry points (reserved)
├── application/          # Use cases and ports
├── domain/               # Reasoning concepts and invariants
└── infrastructure/       # Provider and retrieval adapters
```
