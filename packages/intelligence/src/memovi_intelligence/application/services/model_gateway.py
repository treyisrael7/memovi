from collections.abc import Iterator, Mapping
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

    def available_models(self) -> tuple[tuple[str, str], ...]:
        """Return (provider, model) pairs currently registered and selectable."""
        from memovi_intelligence.config import DEFAULT_MODELS

        models: list[tuple[str, str]] = []
        for provider_name in sorted(self._providers):
            if provider_name == self.provider_name:
                model = self.model
            else:
                try:
                    model = DEFAULT_MODELS[ReasoningProviderKind(provider_name)]
                except ValueError:
                    model = f"{provider_name}-default"
            models.append((provider_name, model))
        return tuple(models)

    def resolve_provider(self, provider_name: str | None = None) -> ReasoningProvider:
        """Resolve a provider without executing a prompt."""
        return self._resolve_provider(provider_name)

    def execute(
        self,
        prompt: Prompt,
        *,
        provider: ReasoningProvider | None = None,
        provider_name: str | None = None,
        model: str | None = None,
    ) -> ReasoningResult:
        resolved_name = provider_name or self.provider_name
        resolved = provider if provider is not None else self._resolve_provider(resolved_name)
        resolved_model = model or (self.model if resolved_name == self.provider_name else model)
        if resolved_model is None:
            resolved_model = self.model

        started = perf_counter()
        try:
            result = resolved.reason(prompt, model=resolved_model)
        except TypeError:
            # Providers that have not yet accepted the model kwarg.
            try:
                result = resolved.reason(prompt)
            except TimeoutError as exc:
                raise ReasoningProviderTimeoutError(
                    f"Reasoning provider '{resolved_name}' timed out.",
                ) from exc
            except IntelligenceDomainError:
                raise
            except Exception as exc:
                raise ReasoningProviderError(
                    f"Reasoning provider '{resolved_name}' failed while producing a result.",
                ) from exc
        except TimeoutError as exc:
            raise ReasoningProviderTimeoutError(
                f"Reasoning provider '{resolved_name}' timed out.",
            ) from exc
        except IntelligenceDomainError:
            raise
        except Exception as exc:
            raise ReasoningProviderError(
                f"Reasoning provider '{resolved_name}' failed while producing a result.",
            ) from exc

        duration = perf_counter() - started
        metadata = {
            **dict(result.metadata),
            "provider": resolved_name,
            "model": resolved_model,
            "duration": duration,
            "estimated_tokens": prompt.context.estimated_token_count,
        }
        return ReasoningResult.create(
            answer=result.answer,
            citations=result.citations,
            metadata=metadata,
            provider=resolved_name,
            execution_time=duration,
            context=result.context,
            execution_trace=result.execution_trace,
            tool_calls=result.tool_calls,
            tool_results=result.tool_results,
        )

    def execute_stream(
        self,
        prompt: Prompt,
        *,
        provider: ReasoningProvider | None = None,
        provider_name: str | None = None,
        model: str | None = None,
    ) -> Iterator[str]:
        """Yield answer deltas, then leave the caller to assemble the final result."""
        resolved_name = provider_name or self.provider_name
        resolved = provider if provider is not None else self._resolve_provider(resolved_name)
        resolved_model = model or self.model

        stream = getattr(resolved, "reason_stream", None)
        try:
            if callable(stream):
                yield from stream(prompt, model=resolved_model)
                return
            result = self.execute(
                prompt,
                provider=resolved,
                provider_name=resolved_name,
                model=resolved_model,
            )
        except IntelligenceDomainError:
            raise
        except Exception as exc:
            raise ReasoningProviderError(
                f"Reasoning provider '{resolved_name}' failed while streaming a result.",
            ) from exc

        chunk_size = 12
        answer = result.answer
        for index in range(0, len(answer), chunk_size):
            yield answer[index : index + chunk_size]

    def _resolve_provider(self, provider_name: str | None = None) -> ReasoningProvider:
        name = (provider_name or self.provider_name).strip().lower()
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
