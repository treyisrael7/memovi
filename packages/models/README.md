# Memovi Models

Model Provider Framework. Owns provider-neutral abstractions so Intelligence
never depends on a single LLM vendor SDK.

## Current Scope

* `ModelProvider` protocol
* `ModelRegistry` for explicit DI registration and discovery
* Model metadata, capabilities, configuration, and health contracts
* Normalized error model
* `FakeModelProvider` for tests and local wiring

It does **not** implement OpenAI, Anthropic, Gemini, Ollama, OpenRouter, or
LM Studio adapters, provider selection UI, or a model marketplace.

## Layout

```text
src/memovi_models/
├── application/       # Ports, registry
├── domain/            # Value objects and exceptions
└── infrastructure/    # Fake provider only (no vendor SDKs)
```

See [`docs/architecture/MODEL_PROVIDER_FRAMEWORK.md`](../../docs/architecture/MODEL_PROVIDER_FRAMEWORK.md).
