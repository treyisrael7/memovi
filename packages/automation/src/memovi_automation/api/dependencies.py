from typing import Annotated, cast

from fastapi import Request
from memovi_shared.fastapi import get_default_active_workspace_id

from memovi_automation.application.services.capability_execution_engine import (
    CapabilityExecutionEngine,
)
from memovi_automation.application.services.workflow_engine import WorkflowEngine
from memovi_automation.domain.value_objects.authenticated_execution_context import (
    AuthenticatedExecutionContext,
)

get_active_workspace_id = get_default_active_workspace_id


def get_authenticated_execution_context() -> AuthenticatedExecutionContext:
    raise RuntimeError("Authenticated execution context dependency was not configured.")


def get_capability_execution_engine(request: Request) -> CapabilityExecutionEngine:
    engine = getattr(request.app.state, "capability_execution_engine", None)
    if engine is None:
        raise RuntimeError("Capability execution engine was not configured.")
    return cast(CapabilityExecutionEngine, engine)


def get_workflow_engine(request: Request) -> WorkflowEngine:
    engine = getattr(request.app.state, "workflow_engine", None)
    if engine is None:
        raise RuntimeError("Workflow engine was not configured.")
    return cast(WorkflowEngine, engine)
