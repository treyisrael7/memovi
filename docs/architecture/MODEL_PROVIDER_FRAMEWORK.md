# Model Provider Framework

# Purpose

This document defines Memovi's Model Provider Framework: a provider-neutral
architecture for discovering, configuring, health-checking, and invoking
language models without coupling Intelligence to a single LLM vendor.

# Scope

It covers the `packages/models` abstractions, registry, capability discovery,
configuration, health, and error normalization. It does not cover desktop UI,
provider selection screens, model marketplaces, or concrete OpenAI / Anthropic /
Gemini / Ollama / OpenRouter / LM Studio adapters.

# Relationship to ARCHITECTURE.md

[`../ARCHITECTURE.md`](../ARCHITECTURE.md) establishes that Intelligence consumes
knowledge and routes to AI providers. This document introduces
`packages/models` (`memovi-models`) as the shared provider-neutral boundary so
Intelligence (and later Search embeddings) can depend on abstractions rather
than vendor SDKs.

# Why This Framework Exists

Memovi must not depend on a single LLM vendor.

Supported providers should eventually include:

* OpenAI
* Anthropic
* Google Gemini
* Ollama
* OpenRouter
* LM Studio
* Future local providers

All model interactions must occur through a common abstraction. Providers can be
added without changing Intelligence business logic.

# Package Ownership

`packages/models` owns:

* `ModelProvider` interface
* Provider registry
* Model metadata
* Provider configuration
* Capability discovery
* Health checks
* Error normalization

It does **not** own:

* RAG / conversation orchestration (Intelligence)
* Durable knowledge (Memory)
* Desktop settings UI
* Vendor SDKs in the public API surface

# Core Interfaces

| Type | Role |
| --- | --- |
| `ModelProvider` | Protocol for discovery, health, and `complete(request)` |
| `ModelRegistry` | Explicit DI registration and lookup |
| `ModelRequest` / `ModelResponse` | Provider-neutral invocation contracts |
| `ModelMetadata` | Per-model id, display name, capabilities, context window |
| `ModelCapabilities` | chat, embeddings, streaming, tool_calling, vision, structured_output |
| `ProviderConfiguration` | Enabled flag, base URL, api key env name, defaults, timeout |
| `ProviderHealth` | healthy / unhealthy / unknown / unavailable snapshots |

Providers self-register by implementing `ModelProvider` and being passed to
`ModelRegistry.register(...)`. There is no global registry singleton and no
reflection-based discovery.

# Registry

```python
from memovi_models import FakeModelProvider, ModelRegistry

registry = ModelRegistry()
registry.register(FakeModelProvider())

registry.list_providers()
registry.list_models()
registry.capabilities("fake")
registry.health("fake")
registry.health_all()
registry.get("fake").complete(request)
```

# Capability Discovery

Providers advertise capabilities. Intelligence should query them rather than
hardcoding vendor behavior:

* `chat`
* `embeddings`
* `streaming`
* `tool_calling`
* `vision`
* `structured_output`

`ModelCapabilities.supports("tool_calling")` and `enabled_names()` support
inspection. Aggregate provider capabilities are available via
`registry.capabilities(provider_id)`.

# Configuration

Multiple providers may be registered simultaneously. Configuration remains
independent of UI:

* `provider_id`
* `enabled`
* `base_url`
* `api_key_env` (environment variable **name**, never the secret value)
* `default_model`
* `timeout_seconds`
* `extra` (non-secret provider options)

Future desktop settings should compose and persist these objects, then inject
providers into the registry.

# Error Model

Normalized failure codes:

| Code | Meaning |
| --- | --- |
| `authentication` | Missing or invalid credentials |
| `unavailable` | Provider cannot be reached or is disabled |
| `rate_limit` | Provider rate limit exceeded |
| `timeout` | Provider exceeded allotted time |
| `unsupported_capability` | Requested capability not offered |
| `invalid_configuration` | Provider config is incomplete or invalid |
| `invalid_request` | Request violates provider/model constraints |
| `provider_error` | Generic normalized provider failure |

`ModelResponse` carries structured `ModelError` on failure. `ModelProviderError`
is available when adapters need to raise before producing a response.

# Relationship to Intelligence Today

Intelligence currently owns `ModelGateway` and `ReasoningProvider` adapters
(including an OpenAI SDK dependency). That remains the live reasoning path.

This framework is the target boundary. Future work should:

1. Implement concrete providers under `memovi_models.infrastructure.providers`
2. Adapt Intelligence `ModelGateway` to resolve providers from `ModelRegistry`
3. Move vendor SDK dependencies out of Intelligence into `packages/models`
4. Optionally converge Search `EmbeddingProvider` onto the same capability model

Until that migration completes, Intelligence must not import vendor types into
domain/application layers; new model work should prefer `memovi-models`
contracts.

# Future Provider Implementations

```text
memovi_models/infrastructure/providers/
├── fake_model_provider.py      # shipped (tests / local)
├── openai_model_provider.py    # future
├── anthropic_model_provider.py # future
├── gemini_model_provider.py    # future
├── ollama_model_provider.py    # future
├── openrouter_model_provider.py
└── lm_studio_model_provider.py
```

Each adapter:

* Implements `ModelProvider`
* Maps vendor errors to normalized codes
* Exposes `ModelMetadata` / `ModelCapabilities`
* Keeps secrets in env/secret stores referenced by `ProviderConfiguration`

# Key Decisions

* Provider-neutral contracts live in `packages/models`, not Intelligence.
* Registration is explicit via dependency injection.
* Capability flags drive feature availability; no vendor hardcoding in callers.
* Configuration never embeds API keys.
* Architecture-only milestone: no production vendor adapters yet.

# Related Documents

* [`../ARCHITECTURE.md`](../ARCHITECTURE.md)
* [`intelligence-architecture.md`](intelligence-architecture.md)
* [`domains.md`](domains.md)
* [`CAPABILITY_FRAMEWORK.md`](CAPABILITY_FRAMEWORK.md)
* [`../STATUS.md`](../STATUS.md)
* [`../ROADMAP.md`](../ROADMAP.md)
