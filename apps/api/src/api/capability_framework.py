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
    InMemoryExecutionAuditStore,
    InMemoryPermissionPolicyStore,
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
from memovi_shared import DEFAULT_WORKSPACE_ID

from api.capability_execution_integration import CapabilityExecutionEngineAdapter
from api.capability_planner_integration import CapabilityPlannerAdapter


def _roots_from_env(env_name: str) -> tuple[Path, ...] | None:
    configured = os.environ.get(env_name, "").strip()
    if not configured:
        return None
    roots = [Path(part.strip()) for part in configured.split(os.pathsep) if part.strip()]
    existing = tuple(root for root in roots if root.exists() and root.is_dir())
    return existing or None


def _filesystem_roots() -> tuple[Path, ...]:
    configured = _roots_from_env("MEMOVI_FILESYSTEM_ROOTS")
    if configured is not None:
        return configured

    # Prefer an isolated temp root over the process cwd (OneDrive/monorepo trees
    # are a risky default and can make local probes unnecessarily heavy).
    fallback = Path(tempfile.mkdtemp(prefix="memovi-filesystem-"))
    return (fallback,)


def _capability_roots(env_name: str, *, fallback: tuple[Path, ...]) -> tuple[Path, ...]:
    configured = _roots_from_env(env_name)
    if configured is not None:
        return configured
    return fallback


def configure_capability_execution(app: FastAPI) -> CapabilityExecutionEngine:
    """Register capabilities and attach the execution engine to the app."""
    registry = CapabilityRegistry()
    roots = _filesystem_roots()
    register_filesystem_capability(
        registry,
        FilesystemCapabilityConfig.from_roots(roots),
    )
    terminal_roots = _capability_roots("MEMOVI_TERMINAL_ROOTS", fallback=roots)
    register_terminal_capability(
        registry,
        TerminalCapabilityConfig.from_roots(terminal_roots),
    )
    git_roots = _capability_roots("MEMOVI_GIT_ROOTS", fallback=roots)
    register_git_capability(
        registry,
        GitCapabilityConfig.from_roots(git_roots),
    )
    browser_roots = _capability_roots("MEMOVI_BROWSER_DOWNLOAD_ROOTS", fallback=roots)
    register_browser_capability(
        registry,
        BrowserCapabilityConfig.from_roots(browser_roots),
    )

    permission_store = InMemoryPermissionPolicyStore(
        default_mode=PermissionMode.ASK_EVERY_TIME,
    )
    for capability_id in ("filesystem", "terminal", "git", "browser"):
        permission_store.set(
            capability_id,
            PermissionMode.ASK_EVERY_TIME,
            workspace_id=DEFAULT_WORKSPACE_ID,
        )

    invoker = CapabilityInvoker(registry=registry)
    engine = CapabilityExecutionEngine(
        registry=registry,
        invoker=invoker,
        permission_policies=permission_store,
        audit_store=InMemoryExecutionAuditStore(),
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
