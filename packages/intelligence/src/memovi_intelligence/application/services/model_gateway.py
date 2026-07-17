from collections.abc import Mapping
from time import perf_counter

from memovi_intelligence.application.ports import ReasoningProvider
from memovi_intelligence.config import IntelligenceConfig, ReasoningProviderKind
from memovi_intelligence.domain.entities import ReasoningResult
from memovi_intelligence.domain.exceptions import (
    IntelligenceDomainError,
    ReasoningProviderError,
    ReasoningProviderTimeoutError,
    ReasoningProviderUnavailableError,
    UnknownReasoningProviderError,
)
from memovi_intelligence.domain.value_objects import Prompt


class ModelGateway:
    """Single entry point for executing prompts against language-model providers.

    Selects the configured provider from an injected registry, measures execution,
    and attaches gateway-owned metadata. Knows nothing about HTTP or API keys.
    Timing of pipeline stages is owned by Reason; this gateway only records the
    duration of the provider call itself in result metadata.
    """

    def __init__(
        self,
        *,
        providers: Mapping[str, ReasoningProvider],
        config: IntelligenceConfig | None = None,
    ) -> None:
        self._providers = dict(providers)
        self._config = config or IntelligenceConfig()

    @property
    def config(self) -> IntelligenceConfig:
        return self._config

    @property
    def provider_name(self) -> str:
        return self._config.provider_name

    @property
    def model(self) -> str:
        if self._config.model is None:
            raise RuntimeError("IntelligenceConfig.model was not resolved.")
        return self._config.model

    def resolve_provider(self) -> ReasoningProvider:
        """Resolve the configured provider without executing a prompt."""
        return self._resolve_provider()

    def execute(
        self,
        prompt: Prompt,
        *,
        provider: ReasoningProvider | None = None,
    ) -> ReasoningResult:
        resolved = provider if provider is not None else self._resolve_provider()
        started = perf_counter()
        try:
            result = resolved.reason(prompt)
        except TimeoutError as exc:
            raise ReasoningProviderTimeoutError(
                f"Reasoning provider '{self.provider_name}' timed out.",
            ) from exc
        except IntelligenceDomainError:
            raise
        except Exception as exc:
            raise ReasoningProviderError(
                f"Reasoning provider '{self.provider_name}' failed while producing a result.",
            ) from exc

        duration = perf_counter() - started
        metadata = {
            **dict(result.metadata),
            "provider": self.provider_name,
            "model": self.model,
            "duration": duration,
            "estimated_tokens": prompt.context.estimated_token_count,
        }
        return ReasoningResult.create(
            answer=result.answer,
            citations=result.citations,
            metadata=metadata,
            provider=self.provider_name,
            execution_time=duration,
            context=result.context,
            execution_trace=result.execution_trace,
            tool_calls=result.tool_calls,
            tool_results=result.tool_results,
        )

    def _resolve_provider(self) -> ReasoningProvider:
        name = self.provider_name
        try:
            ReasoningProviderKind(name)
        except ValueError as exc:
            raise UnknownReasoningProviderError(
                f"Unknown reasoning provider '{name}'.",
            ) from exc

        provider = self._providers.get(name)
        if provider is None:
            raise ReasoningProviderUnavailableError(
                f"Reasoning provider '{name}' is not available.",
            )
        return provider
