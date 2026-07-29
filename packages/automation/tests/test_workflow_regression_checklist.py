"""Regression checklist for Workflow Automation integration.

Capability Planner — plans work independently of workflows.
Capability Engine — individual capability execution unchanged.
Filesystem / Terminal / Git / Browser — work inside workflows.
Permissions — enforced inside workflows.
Observability — workflow_id in structured logs; request_id on every step.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import pytest
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
    WorkflowDefinition,
    WorkflowEngine,
    WorkflowStep,
    WorkflowValidator,
    WorkflowVariable,
    register_browser_capability,
    register_filesystem_capability,
    register_git_capability,
    register_terminal_capability,
)
from memovi_automation.browser import FetchResult, ProviderSearchResults, SearchHit
from memovi_automation.browser.config import BrowserCapabilityConfig as BrowserConfig
from memovi_automation.testing import make_auth_context
from memovi_observability import RequestContext, bind_request_context, clear_request_context
from memovi_shared import WorkspaceId

WORKSPACE = WorkspaceId.default()


class FakeBrowserProvider:
    def download_bytes(
        self, url, *, config: BrowserConfig, timeout_seconds, cancellation=None, on_progress=None
    ):
        return FetchResult(
            url=url,
            final_url=url,
            status_code=200,
            content_type="text/plain",
            body=b"payload",
        )

    def fetch(
        self,
        url,
        *,
        config: BrowserConfig,
        timeout_seconds,
        cancellation=None,
        on_progress=None,
    ):
        return FetchResult(
            url=url,
            final_url=url,
            status_code=200,
            content_type="text/html",
            body=b"<html></html>",
        )

    def search(self, query, *, limit, config: BrowserConfig, timeout_seconds, cancellation=None):
        return ProviderSearchResults(
            query=query,
            results=(SearchHit(title="t", url="https://example.com", snippet="s"),)[:limit],
        )


def _full_stack(root: Path, *, mode: PermissionMode = PermissionMode.ALWAYS_ALLOW):
    registry = CapabilityRegistry()
    register_filesystem_capability(
        registry,
        FilesystemCapabilityConfig.from_roots([root]),
    )
    register_terminal_capability(
        registry,
        TerminalCapabilityConfig.from_roots([root]),
    )
    register_git_capability(
        registry,
        GitCapabilityConfig.from_roots([root]),
    )
    register_browser_capability(
        registry,
        BrowserCapabilityConfig.from_roots([root]),
        provider=FakeBrowserProvider(),
    )
    policies = InMemoryPermissionPolicyStore(default_mode=mode)
    for capability_id in registry.ids:
        policies.set(capability_id, mode, workspace_id=WORKSPACE)
    engine = CapabilityExecutionEngine(
        registry=registry,
        invoker=CapabilityInvoker(registry=registry),
        permission_policies=policies,
        audit_store=InMemoryExecutionAuditStore(),
        default_permission_mode=mode,
    )
    planner = CapabilityPlanner(registry=registry)
    plan_execution = PlanExecutionService(engine=engine, planner=planner)
    workflow_engine = WorkflowEngine(
        library=InMemoryWorkflowLibrary(),
        planner=planner,
        plan_execution=plan_execution,
        history=InMemoryWorkflowHistoryStore(),
        validator=WorkflowValidator(registry=registry),
    )
    return workflow_engine, engine, planner


def _git_repo(root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    (repo / "readme.md").write_text("hello\n", encoding="utf-8")
    subprocess.run(["git", "add", "readme.md"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    return repo


def test_planner_works_independently_of_workflows(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    (root / "a.txt").write_text("ok", encoding="utf-8")
    _workflow_engine, engine, planner = _full_stack(root)

    plan = planner.create_plan(
        workspace_id=WORKSPACE,
        goal="Independent plan",
        steps=[
            {
                "step_id": "exists",
                "capability_id": "filesystem",
                "operation": "exists",
                "arguments": {"path": "a.txt"},
            }
        ],
    )
    result = PlanExecutionService(engine=engine, planner=planner).execute_plan(
        plan, context=make_auth_context()
    )
    assert result.status == "completed"
    assert result.step_results[0].output["exists"] is True
    # No workflow history side effects from planner-only path.
    assert _workflow_engine.history.list_for_workspace(workspace_id=WORKSPACE) == ()


def test_individual_capability_execution_unchanged(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    (root / "note.txt").write_text("solo", encoding="utf-8")
    _workflow_engine, engine, _planner = _full_stack(root)

    from memovi_automation import CapabilityExecutionRequest

    result = engine.submit(
        CapabilityExecutionRequest.create(
            capability_id="filesystem",
            workspace_id=WORKSPACE,
            arguments={"operation": "read_file", "path": "note.txt"},
            source="regression",
        ), make_auth_context())
    assert result.status.value == "completed"
    assert result.output["content"] == "solo"


def test_filesystem_read_write_inside_and_outside_workflows(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    workflow_engine, engine, _planner = _full_stack(root)

    write_flow = WorkflowDefinition(
        workflow_id="write-then-read",
        name="Write Then Read",
        description="Filesystem write + read",
        variables=(
            WorkflowVariable(name="path", type="path", description="File path"),
            WorkflowVariable(name="content", type="string", description="Body"),
        ),
        steps=(
            WorkflowStep(
                step_id="write",
                capability_id="filesystem",
                operation="create_file",
                input_mapping={
                    "path": "${path}",
                    "content": "${content}",
                },
            ),
            WorkflowStep(
                step_id="read",
                capability_id="filesystem",
                operation="read_file",
                input_mapping={"path": "${path}"},
                output_mapping={"body": "$.content"},
            ),
        ),
        expected_outputs=("body",),
    )
    workflow_engine.library.register(write_flow)

    result = workflow_engine.execute(
        workflow_id="write-then-read",
        workspace_id=WORKSPACE,
        auth_context=make_auth_context(),
        variables={"path": "out.txt", "content": "workflow-write"},
    )
    assert result.status == "completed"
    assert result.outputs["body"] == "workflow-write"
    assert (root / "out.txt").read_text(encoding="utf-8") == "workflow-write"
    assert engine.list_executions(workspace_id=WORKSPACE)


def test_terminal_inside_workflow(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    workflow_engine, _engine, _planner = _full_stack(root)

    result = workflow_engine.execute(
        workflow_id="run-command",
        workspace_id=WORKSPACE,
        auth_context=make_auth_context(),
        variables={
            "command": "echo terminal-ok",
            "working_directory": str(root),
        },
    )
    assert result.status == "completed"
    assert result.completed_steps == ("execute",)
    assert result.outputs["exit_code"] == 0
    assert "terminal-ok" in str(result.outputs["stdout"])


def test_git_inside_workflow(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    repo = _git_repo(root)
    workflow_engine, _engine, _planner = _full_stack(root)

    result = workflow_engine.execute(
        workflow_id="summarize-git-status",
        workspace_id=WORKSPACE,
        auth_context=make_auth_context(),
        variables={"repository": str(repo)},
    )
    assert result.status == "completed"
    assert result.completed_steps == ("status", "history")


def test_browser_inside_workflow(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    workflow_engine, _engine, _planner = _full_stack(root)

    result = workflow_engine.execute(
        workflow_id="download-and-verify",
        workspace_id=WORKSPACE,
        auth_context=make_auth_context(),
        variables={
            "url": "https://example.com/a.txt",
            "destination": "inbox/a.txt",
        },
    )
    assert result.status == "completed"
    assert result.outputs["file_exists"] is True


def test_permissions_enforced_inside_workflows(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    workflow_engine, _engine, _planner = _full_stack(
        root,
        mode=PermissionMode.DENY,
    )

    result = workflow_engine.execute(
        workflow_id="list-directory",
        workspace_id=WORKSPACE,
        auth_context=make_auth_context(),
        variables={"source_folder": str(root)},
    )
    assert result.status == "failed"
    assert result.step_results[0].status == "failed"
    assert result.step_results[0].error_code in {
        "permission_denied",
        "PERMISSION_DENIED",
        "denied",
    } or (
        result.step_results[0].error_message
        and "permission" in result.step_results[0].error_message.lower()
    )


def test_workflow_ids_in_structured_logs_and_request_id_propagation(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    workflow_engine, engine, _planner = _full_stack(root)

    token = bind_request_context(
        RequestContext.create(
            request_id="req-workflow-123",
            workspace_id=WORKSPACE,
            correlation_id="corr-workflow-123",
        )
    )
    try:
        with caplog.at_level(logging.INFO, logger="memovi.automation.workflow"):
            result = workflow_engine.execute(
                workflow_id="download-and-verify",
                workspace_id=WORKSPACE,
                auth_context=make_auth_context(request_id="req-workflow-123"),
                variables={
                    "url": "https://example.com/logged.txt",
                    "destination": "inbox/logged.txt",
                },
            )
    finally:
        clear_request_context(token)

    assert result.status == "completed"
    assert result.metadata.get("request_id") == "req-workflow-123"
    assert result.metadata.get("correlation_id") == "corr-workflow-123"

    records = [r for r in caplog.records if r.name == "memovi.automation.workflow"]
    assert records
    assert any(getattr(r, "workflow_id", None) == "download-and-verify" for r in records)
    assert any(getattr(r, "operation", None) == "workflow.execute.start" for r in records)
    step_logs = [
        r
        for r in records
        if getattr(r, "operation", None) == "workflow.step.execute"
    ]
    assert len(step_logs) == 2
    for record in step_logs:
        assert getattr(record, "request_id", None) == "req-workflow-123"
        assert getattr(record, "workflow_id", None) == "download-and-verify"
        assert getattr(record, "step_id", None) in {"download", "verify"}

    for step in result.step_results:
        assert step.execution_id
        fetched = engine.get(step.execution_id, workspace_id=WORKSPACE)
        assert fetched.metadata.get("request_id") == "req-workflow-123"
        assert fetched.metadata.get("workflow_id") == "download-and-verify"
        assert fetched.correlation_id == "corr-workflow-123"


def test_workflow_library_lists_available_capabilities(tmp_path: Path) -> None:
    """Desktop library loads from the same list_workflows surface."""
    root = tmp_path / "ws"
    root.mkdir()
    workflow_engine, _engine, _planner = _full_stack(root)
    ids = {item.workflow_id for item in workflow_engine.list_workflows()}
    assert "list-directory" in ids
    assert "run-command" in ids
    assert "summarize-git-status" in ids
    assert "download-and-verify" in ids


def test_history_records_previous_runs(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    workflow_engine, _engine, _planner = _full_stack(root)

    first = workflow_engine.execute(
        workflow_id="list-directory",
        workspace_id=WORKSPACE,
        auth_context=make_auth_context(),
        variables={"source_folder": str(root)},
    )
    second = workflow_engine.execute(
        workflow_id="list-directory",
        workspace_id=WORKSPACE,
        auth_context=make_auth_context(),
        variables={"source_folder": str(root)},
    )
    history = workflow_engine.history.list_for_workspace(workspace_id=WORKSPACE)
    assert len(history) == 2
    assert {entry.instance_id for entry in history} == {
        first.instance_id,
        second.instance_id,
    }
