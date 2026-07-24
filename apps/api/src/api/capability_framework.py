from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import FastAPI
from memovi_automation import (
    CapabilityExecutionEngine,
    CapabilityInvoker,
    CapabilityRegistry,
    FilesystemCapabilityConfig,
    InMemoryExecutionAuditStore,
    InMemoryPermissionPolicyStore,
    PermissionMode,
    register_filesystem_capability,
)
from memovi_shared import DEFAULT_WORKSPACE_ID

from api.capability_execution_integration import CapabilityExecutionEngineAdapter


def _filesystem_roots() -> tuple[Path, ...]:
    configured = os.environ.get("MEMOVI_FILESYSTEM_ROOTS", "").strip()
    if configured:
        roots = [Path(part.strip()) for part in configured.split(os.pathsep) if part.strip()]
        existing = tuple(root for root in roots if root.exists() and root.is_dir())
        if existing:
            return existing

    # Prefer an isolated temp root over the process cwd (OneDrive/monorepo trees
    # are a risky default and can make local probes unnecessarily heavy).
    fallback = Path(tempfile.mkdtemp(prefix="memovi-filesystem-"))
    return (fallback,)


def configure_capability_execution(app: FastAPI) -> CapabilityExecutionEngine:
    """Register capabilities and attach the execution engine to the app."""
    registry = CapabilityRegistry()
    roots = _filesystem_roots()
    register_filesystem_capability(
        registry,
        FilesystemCapabilityConfig.from_roots(roots),
    )

    permission_store = InMemoryPermissionPolicyStore(
        default_mode=PermissionMode.ASK_EVERY_TIME,
    )
    permission_store.set(
        "filesystem",
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

    app.state.capability_registry = registry
    app.state.capability_invoker = invoker
    app.state.capability_execution_engine = engine
    app.state.capability_execution_port = CapabilityExecutionEngineAdapter(engine)
    app.state.filesystem_allowed_roots = roots
    return engine
