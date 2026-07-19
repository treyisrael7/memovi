"""Infrastructure adapters for model providers.

Production vendor adapters (OpenAI, Anthropic, Gemini, Ollama, OpenRouter,
LM Studio) will live here. This foundation ships only FakeModelProvider.
"""

from memovi_models.infrastructure.providers import FakeModelProvider

__all__ = ["FakeModelProvider"]
