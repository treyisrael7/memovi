from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import FastAPI
from memovi_automation import (
    BrowserCapabilityConfig,
    CapabilityExecutionEngine,
    CapabilityInvoker,
    CapabilityPlanner,
    CapabilityRegistry,
    FilesystemCapabilityConfig,
    GitCapabilityConfig,
    InMemoryWorkflowHistoryStore,
    InMemoryWorkflowLibrary,
    PermissionMode,
    PlanExecutionService,
    TerminalCapabilityConfig,
    WorkflowEngine,
    WorkflowValidator,
    register_browser_capability,
    register_filesystem_capability,
    register_git_capability,
    register_terminal_capability,
)
from memovi_automation.application.services.capability_authorization_service import (
    CapabilityAuthorizationService,
)
from memovi_automation.infrastructure.sqlalchemy_execution_audit_store import (
    SqlAlchemyExecutionAuditStore,
)
from memovi_automation.infrastructure.sqlalchemy_permission_policy_store import (
    SqlAlchemyPermissionPolicyStore,
)
from memovi_config.settings.capabilities import CapabilitiesSettings
from memovi_shared import DEFAULT_WORKSPACE_ID

from api.authorization import SqlAlchemyWorkspaceMembershipPort
from api.capability_execution_integration import CapabilityExecutionEngineAdapter
from api.capability_planner_integration import CapabilityPlannerAdapter
from api.database import create_session


def _filesystem_roots(settings: CapabilitiesSettings) -> tuple[Path, ...]:
    if settings.filesystem_roots is not None:
        return settings.filesystem_roots

    fallback = Path(tempfile.mkdtemp(prefix="memovi-filesystem-"))
    return (fallback,)


def _capability_roots(
    configured: tuple[Path, ...] | None,
    *,
    fallback: tuple[Path, ...],
) -> tuple[Path, ...]:
    if configured is not None:
        return configured
    return fallback


def configure_capability_execution(app: FastAPI) -> CapabilityExecutionEngine:
    """Register capabilities and attach the execution engine to the app."""
    registry = CapabilityRegistry()
    settings = CapabilitiesSettings.from_environ(os.environ)
    roots = _filesystem_roots(settings)
    register_filesystem_capability(
        registry,
        FilesystemCapabilityConfig.from_roots(roots),
    )
    terminal_roots = _capability_roots(settings.terminal_roots, fallback=roots)
    register_terminal_capability(
        registry,
        TerminalCapabilityConfig.from_roots(terminal_roots),
    )
    git_roots = _capability_roots(settings.git_roots, fallback=roots)
    register_git_capability(
        registry,
        GitCapabilityConfig.from_roots(git_roots),
    )
    browser_roots = _capability_roots(settings.browser_download_roots, fallback=roots)
    register_browser_capability(
        registry,
        BrowserCapabilityConfig.from_roots(browser_roots),
    )

    def db_factory() -> object:
        # Resolve at call time so tests can override app.state.auth_session_factory
        # after create_app() wires the capability framework.
        override = getattr(app.state, "auth_session_factory", None)
        factory = override if callable(override) else create_session
        return factory()

    permission_store = SqlAlchemyPermissionPolicyStore(
        db_factory,  # type: ignore[arg-type]
        default_mode=PermissionMode.ASK_EVERY_TIME,
    )
    # Seed Ask Every Time for the default workspace when durable DB is available.
    try:
        for capability_id in ("filesystem", "terminal", "git", "browser"):
            permission_store.set(
                capability_id,
                PermissionMode.ASK_EVERY_TIME,
                workspace_id=DEFAULT_WORKSPACE_ID,
            )
    except Exception:
        # Local/unit app construction may run before migrations/tables exist.
        pass

    authorization = CapabilityAuthorizationService(
        membership=SqlAlchemyWorkspaceMembershipPort(db_factory),  # type: ignore[arg-type]
        permission_policies=permission_store,
        registry=registry,
        default_permission_mode=PermissionMode.ASK_EVERY_TIME,
    )

    invoker = CapabilityInvoker(registry=registry)
    engine = CapabilityExecutionEngine(
        registry=registry,
        invoker=invoker,
        permission_policies=permission_store,
        audit_store=SqlAlchemyExecutionAuditStore(db_factory),  # type: ignore[arg-type]
        authorization=authorization,
        default_permission_mode=PermissionMode.ASK_EVERY_TIME,
    )
    planner = CapabilityPlanner(registry=registry)
    plan_execution = PlanExecutionService(engine=engine, planner=planner)
    workflow_history_store = InMemoryWorkflowHistoryStore()
    workflow_engine = WorkflowEngine(
        library=InMemoryWorkflowLibrary(),
        planner=planner,
        plan_execution=plan_execution,
        history=workflow_history_store,
        validator=WorkflowValidator(registry=registry),
    )

    app.state.capability_registry = registry
    app.state.capability_invoker = invoker
    app.state.capability_execution_engine = engine
    app.state.capability_execution_port = CapabilityExecutionEngineAdapter(engine)
    app.state.capability_planner = planner
    app.state.capability_plan_execution = plan_execution
    app.state.capability_planner_port = CapabilityPlannerAdapter(
        planner=planner,
        plan_execution=plan_execution,
    )
    app.state.workflow_engine = workflow_engine
    app.state.workflow_history_store = workflow_history_store
    app.state.filesystem_allowed_roots = roots
    app.state.terminal_allowed_roots = terminal_roots
    app.state.git_allowed_roots = git_roots
    app.state.browser_download_roots = browser_roots
    return engine
