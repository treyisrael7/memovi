"""Unit tests for Workflow Automation Framework."""

from __future__ import annotations

from pathlib import Path

import pytest
from memovi_automation import (
    CapabilityExecutionEngine,
    CapabilityInvoker,
    CapabilityPlanner,
    CapabilityRegistry,
    FilesystemCapabilityConfig,
    InMemoryExecutionAuditStore,
    InMemoryPermissionPolicyStore,
    InMemoryWorkflowHistoryStore,
    InMemoryWorkflowLibrary,
    InvalidWorkflowError,
    PermissionMode,
    PlanExecutionService,
    WorkflowDefinition,
    WorkflowEngine,
    WorkflowStep,
    WorkflowValidator,
    WorkflowVariable,
    register_filesystem_capability,
    register_git_capability,
)
from memovi_automation.git import GitCapabilityConfig
from memovi_automation.testing import make_auth_context
from memovi_shared import WorkspaceId


def _stack(root: Path, *, mode: PermissionMode = PermissionMode.ALWAYS_ALLOW):
    registry = CapabilityRegistry()
    register_filesystem_capability(
        registry,
        FilesystemCapabilityConfig.from_roots([root]),
    )
    register_git_capability(
        registry,
        GitCapabilityConfig.from_roots([root]),
    )
    engine = CapabilityExecutionEngine(
        registry=registry,
        invoker=CapabilityInvoker(registry=registry),
        permission_policies=InMemoryPermissionPolicyStore(default_mode=mode),
        audit_store=InMemoryExecutionAuditStore(),
        default_permission_mode=mode,
    )
    planner = CapabilityPlanner(registry=registry)
    plan_execution = PlanExecutionService(engine=engine, planner=planner)
    history = InMemoryWorkflowHistoryStore()
    workflow_engine = WorkflowEngine(
        library=InMemoryWorkflowLibrary(),
        planner=planner,
        plan_execution=plan_execution,
        history=history,
        validator=WorkflowValidator(registry=registry),
    )
    return workflow_engine, engine, history


def test_list_built_in_workflows(tmp_path: Path) -> None:
    workflow_engine, _, _ = _stack(tmp_path)
    workflows = workflow_engine.list_workflows()
    ids = {item.workflow_id for item in workflows}
    # Available for filesystem+git stack (browser workflows omitted until registered).
    assert "list-directory" in ids
    assert "summarize-git-status" in ids
    assert "inspect-then-list" in ids
    assert "download-and-verify" not in ids


def test_validate_required_variables(tmp_path: Path) -> None:
    workflow_engine, _, _ = _stack(tmp_path)
    with pytest.raises(InvalidWorkflowError, match="source_folder"):
        workflow_engine.execute(
            workflow_id="list-directory",
            workspace_id=WorkspaceId("00000000-0000-4000-8000-000000000001"),
            auth_context=make_auth_context(),
            variables={},
        )


def test_execute_list_directory_workflow(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    (tmp_path / "b.txt").write_text("world", encoding="utf-8")
    workflow_engine, engine, history = _stack(tmp_path)

    result = workflow_engine.execute(
        workflow_id="list-directory",
        workspace_id=WorkspaceId("00000000-0000-4000-8000-000000000001"),
        auth_context=make_auth_context(),
        variables={"source_folder": str(tmp_path)},
    )

    assert result.status == "completed"
    assert result.completed_steps == ("list",)
    assert result.failed_steps == ()
    assert sorted(result.outputs["entries"]) == ["a.txt", "b.txt"]
    assert result.outputs["count"] == 2
    assert result.audit_references
    assert len(result.audit_references) == 1

    # History recorded
    entries = history.list_for_workspace(
        workspace_id=WorkspaceId("00000000-0000-4000-8000-000000000001"),
    )
    assert len(entries) == 1
    assert entries[0].workflow_name == "List Directory"
    assert entries[0].status == "completed"
    assert "filesystem" in entries[0].executed_capabilities

    # Execution went through the capability engine (audited)
    audit = engine.list_audit(
        workspace_id=WorkspaceId("00000000-0000-4000-8000-000000000001"),
    )
    assert any(entry.capability_id == "filesystem" for entry in audit)


def test_sequential_step_output_mapping(tmp_path: Path) -> None:
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "file.txt").write_text("x", encoding="utf-8")
    workflow_engine, _, _ = _stack(tmp_path)

    result = workflow_engine.execute(
        workflow_id="inspect-then-list",
        workspace_id=WorkspaceId("00000000-0000-4000-8000-000000000001"),
        auth_context=make_auth_context(),
        variables={"source_folder": str(tmp_path / "nested")},
    )

    assert result.status == "completed"
    assert result.completed_steps == ("metadata", "list")
    assert "file.txt" in result.outputs["entries"]
    assert str(tmp_path / "nested") in str(result.outputs["resolved_path"])


def test_stop_on_pending_approval(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    workflow_engine, _, _ = _stack(
        tmp_path,
        mode=PermissionMode.ASK_EVERY_TIME,
    )

    result = workflow_engine.execute(
        workflow_id="list-directory",
        workspace_id=WorkspaceId("00000000-0000-4000-8000-000000000001"),
        auth_context=make_auth_context(),
        variables={"source_folder": str(tmp_path)},
    )

    assert result.status == "awaiting_approval"
    assert result.completed_steps == ()
    assert result.step_results[0].status == "pending_approval"


def _workspace() -> WorkspaceId:
    return WorkspaceId("00000000-0000-4000-8000-000000000001")


def _approve_and_resume(workflow_engine: WorkflowEngine, engine, paused, *, auth=None):
    workspace = _workspace()
    auth = auth or make_auth_context(workspace_id=workspace)
    pending = next(
        step
        for step in paused.step_results
        if step.status == "pending_approval" and step.execution_id
    )
    engine.approve(pending.execution_id, workspace_id=workspace, context=auth)
    return workflow_engine.resume_after_capability(
        execution_id=pending.execution_id,
        workspace_id=workspace,
        auth_context=auth,
    )


def test_approval_resumes_workflow_from_waiting_step(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    workflow_engine, engine, _ = _stack(tmp_path, mode=PermissionMode.ASK_EVERY_TIME)
    auth = make_auth_context(workspace_id=_workspace())

    paused = workflow_engine.execute(
        workflow_id="list-directory",
        workspace_id=_workspace(),
        auth_context=auth,
        variables={"source_folder": str(tmp_path)},
    )
    assert paused.status == "awaiting_approval"

    resumed = _approve_and_resume(workflow_engine, engine, paused, auth=auth)

    assert resumed is not None
    assert resumed.instance_id == paused.instance_id
    assert resumed.status == "completed"
    assert resumed.completed_steps == ("list",)
    assert resumed.step_results[0].status == "completed"
    assert resumed.step_results[0].execution_id == paused.step_results[0].execution_id
    assert resumed.outputs["count"] == 1


def test_approval_denial_cancels_workflow(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    workflow_engine, engine, _ = _stack(tmp_path, mode=PermissionMode.ASK_EVERY_TIME)
    workspace = _workspace()
    auth = make_auth_context(workspace_id=workspace)

    paused = workflow_engine.execute(
        workflow_id="list-directory",
        workspace_id=workspace,
        auth_context=auth,
        variables={"source_folder": str(tmp_path)},
    )
    pending_id = paused.step_results[0].execution_id
    assert pending_id
    engine.cancel(pending_id, workspace_id=workspace, context=auth)
    denied = workflow_engine.resume_after_capability(
        execution_id=pending_id,
        workspace_id=workspace,
        auth_context=auth,
    )

    assert denied is not None
    assert denied.status == "cancelled"
    assert denied.completed_steps == ()
    assert denied.step_results[0].status == "cancelled"


def test_mid_workflow_approval_does_not_restart_earlier_steps(tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "file.txt").write_text("x", encoding="utf-8")
    workflow_engine, engine, _ = _stack(tmp_path, mode=PermissionMode.ASK_EVERY_TIME)
    auth = make_auth_context(workspace_id=_workspace())

    paused = workflow_engine.execute(
        workflow_id="inspect-then-list",
        workspace_id=_workspace(),
        auth_context=auth,
        variables={"source_folder": str(nested)},
    )
    assert paused.status == "awaiting_approval"
    assert paused.step_results[0].step_id == "metadata"
    first_execution_id = paused.step_results[0].execution_id

    after_first = _approve_and_resume(workflow_engine, engine, paused, auth=auth)
    assert after_first is not None
    assert after_first.status == "awaiting_approval"
    assert after_first.completed_steps == ("metadata",)
    assert after_first.step_results[0].execution_id == first_execution_id
    assert after_first.step_results[1].status == "pending_approval"

    finished = _approve_and_resume(workflow_engine, engine, after_first, auth=auth)
    assert finished is not None
    assert finished.status == "completed"
    assert finished.completed_steps == ("metadata", "list")
    assert finished.step_results[0].execution_id == first_execution_id
    assert "file.txt" in finished.outputs["entries"]


def test_duplicate_resume_does_not_reexecute_capability(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    workflow_engine, engine, _ = _stack(tmp_path, mode=PermissionMode.ASK_EVERY_TIME)
    workspace = _workspace()
    auth = make_auth_context(workspace_id=workspace)

    paused = workflow_engine.execute(
        workflow_id="list-directory",
        workspace_id=workspace,
        auth_context=auth,
        variables={"source_folder": str(tmp_path)},
    )
    pending_id = paused.step_results[0].execution_id
    assert pending_id
    engine.approve(pending_id, workspace_id=workspace, context=auth)
    first = workflow_engine.resume_after_capability(
        execution_id=pending_id,
        workspace_id=workspace,
        auth_context=auth,
    )
    audit_after_first = engine.list_audit(workspace_id=workspace)
    second = workflow_engine.resume_after_capability(
        execution_id=pending_id,
        workspace_id=workspace,
        auth_context=auth,
    )
    audit_after_second = engine.list_audit(workspace_id=workspace)

    assert first is not None and second is not None
    assert first.status == "completed"
    assert second.status == "completed"
    assert second.step_results[0].execution_id == first.step_results[0].execution_id
    assert len(audit_after_second) == len(audit_after_first)


def test_recover_continues_after_approval_without_duplicate(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    workflow_engine, engine, history = _stack(tmp_path, mode=PermissionMode.ASK_EVERY_TIME)
    workspace = _workspace()
    auth = make_auth_context(workspace_id=workspace)

    paused = workflow_engine.execute(
        workflow_id="list-directory",
        workspace_id=workspace,
        auth_context=auth,
        variables={"source_folder": str(tmp_path)},
    )
    pending_id = paused.step_results[0].execution_id
    assert pending_id
    engine.approve(pending_id, workspace_id=workspace, context=auth)
    stored = history.get_result(paused.instance_id, workspace_id=workspace)
    assert stored is not None
    assert stored.status == "awaiting_approval"

    recovered = workflow_engine.recover_awaiting_approvals()
    assert len(recovered) == 1
    assert recovered[0].instance_id == paused.instance_id
    assert recovered[0].status == "completed"
    assert recovered[0].completed_steps == ("list",)

    again = workflow_engine.recover_awaiting_approvals()
    assert again == ()


def test_workflow_does_not_bypass_planner(tmp_path: Path) -> None:
    """Materialized plans are validated by CapabilityPlanner."""
    workflow_engine, _, _ = _stack(tmp_path)
    plan = workflow_engine.materialize_plan(
        workflow_id="list-directory",
        workspace_id=WorkspaceId("00000000-0000-4000-8000-000000000001"),
        variables={"source_folder": str(tmp_path)},
    )
    assert plan.goal == "List Directory"
    assert plan.steps[0].capability_id == "filesystem"
    assert plan.steps[0].operation == "list_directory"
    assert plan.metadata["source"] == "workflow_engine"


def test_reject_undeclared_variable_in_definition(tmp_path: Path) -> None:
    registry = CapabilityRegistry()
    register_filesystem_capability(
        registry,
        FilesystemCapabilityConfig.from_roots([tmp_path]),
    )
    validator = WorkflowValidator(registry=registry)
    bad = WorkflowDefinition(
        workflow_id="bad",
        name="Bad",
        description="Uses undeclared var",
        variables=(),
        steps=(
            WorkflowStep(
                step_id="list",
                capability_id="filesystem",
                operation="list_directory",
                input_mapping={"path": "${missing}"},
            ),
        ),
    )
    with pytest.raises(InvalidWorkflowError, match="undeclared"):
        validator.validate_definition(bad)


def test_custom_workflow_registration(tmp_path: Path) -> None:
    workflow_engine, _, _ = _stack(tmp_path)
    custom = WorkflowDefinition(
        workflow_id="custom-meta",
        name="Custom Metadata",
        description="Get metadata for a path",
        variables=(WorkflowVariable(name="target", type="path", description="Path"),),
        steps=(
            WorkflowStep(
                step_id="meta",
                capability_id="filesystem",
                operation="get_metadata",
                input_mapping={"path": "${target}"},
                output_mapping={"size": "$.size_bytes"},
            ),
        ),
        expected_outputs=("size",),
    )
    workflow_engine.library.register(custom)
    (tmp_path / "f.txt").write_text("abc", encoding="utf-8")

    result = workflow_engine.execute(
        workflow_id="custom-meta",
        workspace_id=WorkspaceId("00000000-0000-4000-8000-000000000001"),
        auth_context=make_auth_context(),
        variables={"target": str(tmp_path / "f.txt")},
    )
    assert result.status == "completed"
    assert result.outputs["size"] == 3
