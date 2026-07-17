from dataclasses import dataclass

from memovi_intelligence.domain.exceptions import InvalidExecutionTraceError


@dataclass(frozen=True, slots=True)
class ExecutionMetrics:
    """Immutable aggregate metrics for a completed reasoning execution."""

    provider: str
    model: str
    estimated_input_tokens: int
    output_tokens: int | None
    retrieved_knowledge_count: int
    document_count: int
    citation_count: int

    def __post_init__(self) -> None:
        provider = self.provider.strip()
        model = self.model.strip()
        if not provider:
            raise InvalidExecutionTraceError("provider is required.")
        if not model:
            raise InvalidExecutionTraceError("model is required.")
        if self.estimated_input_tokens < 0:
            raise InvalidExecutionTraceError(
                "estimated_input_tokens cannot be negative.",
            )
        if self.output_tokens is not None and self.output_tokens < 0:
            raise InvalidExecutionTraceError("output_tokens cannot be negative.")
        for field_name in (
            "retrieved_knowledge_count",
            "document_count",
            "citation_count",
        ):
            if getattr(self, field_name) < 0:
                raise InvalidExecutionTraceError(f"{field_name} cannot be negative.")

        object.__setattr__(self, "provider", provider)
        object.__setattr__(self, "model", model)
