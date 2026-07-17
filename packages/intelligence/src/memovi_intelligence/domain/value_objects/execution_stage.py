from enum import StrEnum


class ExecutionStage(StrEnum):
    """Named stage in a reasoning execution pipeline."""

    RETRIEVAL = "retrieval"
    CONTEXT_ASSEMBLY = "context_assembly"
    PROMPT_BUILD = "prompt_build"
    PROVIDER_RESOLUTION = "provider_resolution"
    MODEL_EXECUTION = "model_execution"


PIPELINE_STAGE_ORDER: tuple[ExecutionStage, ...] = (
    ExecutionStage.RETRIEVAL,
    ExecutionStage.CONTEXT_ASSEMBLY,
    ExecutionStage.PROMPT_BUILD,
    ExecutionStage.PROVIDER_RESOLUTION,
    ExecutionStage.MODEL_EXECUTION,
)
