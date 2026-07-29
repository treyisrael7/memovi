"""Acceptance checklist for Workflow Automation.

1. Create a workflow that uses both Browser and Filesystem.
2. Execute and verify each step runs in the correct order.
3. Verify outputs from one step are passed to the next.
4. Approval-required capability pauses until approved.
5. Intentional failure stops with a structured error.
6. Workflow variables are validated before execution.
7. Execution history is recorded.
8. Every workflow step creates an audit entry.
9. Workflow execution generates an execution plan before running.
10. Full regression suite (run separately / CI).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

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
    InvalidWorkflowError,
    PermissionMode,
    PlanExecutionService,
    WorkflowDefinition,
    WorkflowEngine,
    WorkflowStep,
    WorkflowValidator,
    WorkflowVariable,
    register_browser_capability,
    register_filesystem_capability,
    register_git_capability,
)
from memovi_automation.browser import FetchResult, ProviderSearchResults, SearchHit
from memovi_automation.browser.config import BrowserCapabilityConfig as BrowserConfig
from memovi_automation.testing import make_auth_context
from memovi_shared import WorkspaceId

WORKSPACE = WorkspaceId.default()


class FakeBrowserProvider:
    def __init__(self) -> None:
        self.fetch_calls = 0
        self.search_calls = 0
        self.download_calls = 0
        self.download_urls: list[str] = []

    def fetch(
        self,
        url,
        *,
        config: BrowserConfig,
        timeout_seconds,
        cancellation=None,
        on_progress=None,
    ):
        self.fetch_calls += 1
        return FetchResult(
            url=url,
            final_url=url,
            status_code=200,
            content_type="text/html",
            body=b"<html><body>ok</body></html>",
        )

    def search(self, query, *, limit, config: BrowserConfig, timeout_seconds, cancellation=None):
        self.search_calls += 1
        return ProviderSearchResults(
            query=query,
            results=(SearchHit(title="Hit", url="https://example.com/a", snippet="s"),)[:limit],
        )

    def download_bytes(
        self, url, *, config: BrowserConfig, timeout_seconds, cancellation=None, on_progress=None
    ):
        self.download_calls += 1
        self.download_urls.append(url)
        return FetchResult(
            url=url,
            final_url=url,
            status_code=200,
            content_type="text/plain",
            body=b"invoice-bytes",
        )


class TrackingPlanner(CapabilityPlanner):
    """Records create_plan calls to prove plans are built before execution."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.create_plan_calls: list[dict[str, object]] = []

    def create_plan(self, **kwargs: Any):  # type: ignore[override]
        self.create_plan_calls.append(
            {
                "goal": kwargs.get("goal"),
                "steps": kwargs.get("steps"),
                "metadata": kwargs.get("metadata"),
            }
        )
        return super().create_plan(**kwargs)


def _stack(
    root: Path,
    *,
    mode: PermissionMode = PermissionMode.ALWAYS_ALLOW,
    with_browser: bool = True,
    with_git: bool = False,
):
    registry = CapabilityRegistry()
    register_filesystem_capability(
        registry,
        FilesystemCapabilityConfig.from_roots([root]),
    )
    provider = FakeBrowserProvider() if with_browser else None
    if with_browser:
        register_browser_capability(
            registry,
            BrowserCapabilityConfig.from_roots([root]),
            provider=provider,
        )
    if with_git:
        register_git_capability(
            registry,
            GitCapabilityConfig.from_roots([root]),
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
    planner = TrackingPlanner(registry=registry)
    plan_execution = PlanExecutionService(engine=engine, planner=planner)
    history = InMemoryWorkflowHistoryStore()
    workflow_engine = WorkflowEngine(
        library=InMemoryWorkflowLibrary(),
        planner=planner,
        plan_execution=plan_execution,
        history=history,
        validator=WorkflowValidator(registry=registry),
    )
    return workflow_engine, engine, planner, history, provider


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


def test_1_browser_filesystem_workflow_exists(tmp_path: Path) -> None:
    """1. Create / expose a workflow that uses both Browser and Filesystem."""
    workflow_engine, *_ = _stack(tmp_path)
    definition = workflow_engine.get_workflow("download-and-verify")

    assert definition.workflow_id == "download-and-verify"
    assert definition.required_capabilities == ("browser", "filesystem")
    assert [step.capability_id for step in definition.steps] == ["browser", "filesystem"]
    assert [step.operation for step in definition.steps] == ["download_file", "exists"]
    assert "steps.download.destination" in str(definition.steps[1].input_mapping)


def test_2_steps_run_in_correct_order(tmp_path: Path) -> None:
    """2. Execute and verify each step runs in the correct order."""
    root = tmp_path / "ws"
    root.mkdir()
    workflow_engine, _engine, planner, _history, provider = _stack(root)
    assert provider is not None

    result = workflow_engine.execute(
        workflow_id="download-and-verify",
        workspace_id=WORKSPACE,
        auth_context=make_auth_context(),
        variables={
            "url": "https://example.com/invoice.txt",
            "destination": "inbox/invoice.txt",
        },
    )

    assert result.status == "completed"
    assert result.completed_steps == ("download", "verify")
    assert [step.step_id for step in result.step_results] == ["download", "verify"]
    assert [step.capability_id for step in result.step_results] == ["browser", "filesystem"]
    assert provider.download_calls == 1
    assert (root / "inbox" / "invoice.txt").read_bytes() == b"invoice-bytes"

    # Planner was asked for download before verify (call order).
    goals = [str(call["goal"]) for call in planner.create_plan_calls]
    download_idx = next(i for i, g in enumerate(goals) if "download" in g)
    verify_idx = next(i for i, g in enumerate(goals) if "verify" in g)
    assert download_idx < verify_idx


def test_3_step_outputs_passed_to_next(tmp_path: Path) -> None:
    """3. Verify outputs from one step are correctly passed to the next."""
    root = tmp_path / "ws"
    root.mkdir()
    workflow_engine, _engine, _planner, _history, _provider = _stack(root)

    result = workflow_engine.execute(
        workflow_id="download-and-verify",
        workspace_id=WORKSPACE,
        auth_context=make_auth_context(),
        variables={
            "url": "https://example.com/report.bin",
            "destination": "downloads/report.bin",
        },
    )

    assert result.status == "completed"
    download_out = result.step_results[0].output
    assert isinstance(download_out, dict)
    assert download_out["destination"].endswith("report.bin")

    # Bound outputs from mapping + filesystem used prior destination.
    assert result.outputs["downloaded_path"] == download_out["destination"]
    assert result.outputs["bytes_written"] == len(b"invoice-bytes")
    assert result.outputs["file_exists"] is True

    verify_out = result.step_results[1].output
    assert isinstance(verify_out, dict)
    assert verify_out["exists"] is True
    assert verify_out["path"] == download_out["destination"]


def test_4_pauses_for_approval(tmp_path: Path) -> None:
    """4. Capability requiring approval pauses workflow until approved."""
    root = tmp_path / "ws"
    root.mkdir()
    workflow_engine, engine, _planner, _history, provider = _stack(
        root,
        mode=PermissionMode.ASK_EVERY_TIME,
    )
    assert provider is not None

    result = workflow_engine.execute(
        workflow_id="download-and-verify",
        workspace_id=WORKSPACE,
        auth_context=make_auth_context(),
        variables={
            "url": "https://example.com/pending.txt",
            "destination": "inbox/pending.txt",
        },
    )

    assert result.status == "awaiting_approval"
    assert result.completed_steps == ()
    assert result.step_results[0].status == "pending_approval"
    assert result.step_results[0].execution_id
    assert provider.download_calls == 0
    assert not (root / "inbox" / "pending.txt").exists()

    approved = engine.approve(
        result.step_results[0].execution_id,
        workspace_id=WORKSPACE,
        context=make_auth_context(workspace_id=WORKSPACE),
    )
    assert approved.status.value == "completed"
    assert provider.download_calls == 1
    assert (root / "inbox" / "pending.txt").exists()


def test_5_intentional_failure_stops_with_structured_error(tmp_path: Path) -> None:
    """5. Intentional failure stops execution with a structured error."""
    root = tmp_path / "ws"
    root.mkdir()
    workflow_engine, _engine, _planner, _history, _provider = _stack(root)

    failing = WorkflowDefinition(
        workflow_id="fail-after-list",
        name="Fail After List",
        description="Succeeds listing then fails reading a missing file.",
        variables=(
            WorkflowVariable(name="source_folder", type="path", description="Folder"),
        ),
        steps=(
            WorkflowStep(
                step_id="list",
                capability_id="filesystem",
                operation="list_directory",
                input_mapping={"path": "${source_folder}"},
            ),
            WorkflowStep(
                step_id="read_missing",
                capability_id="filesystem",
                operation="read_file",
                input_mapping={"path": "${source_folder}/does-not-exist.txt"},
            ),
            WorkflowStep(
                step_id="should_not_run",
                capability_id="filesystem",
                operation="list_directory",
                input_mapping={"path": "${source_folder}"},
            ),
        ),
    )
    workflow_engine.library.register(failing)

    result = workflow_engine.execute(
        workflow_id="fail-after-list",
        workspace_id=WORKSPACE,
        auth_context=make_auth_context(),
        variables={"source_folder": str(root)},
    )

    assert result.status == "failed"
    assert result.completed_steps == ("list",)
    assert result.failed_steps == ("read_missing",)
    assert "should_not_run" not in result.completed_steps
    assert len(result.step_results) == 2
    failed = result.step_results[1]
    assert failed.status == "failed"
    assert failed.error_code
    assert failed.error_message
    assert result.errors
    assert result.instance_id
    assert isinstance(result.duration, float)


def test_6_variables_validated_before_execution(tmp_path: Path) -> None:
    """6. Workflow variables are validated before execution."""
    root = tmp_path / "ws"
    root.mkdir()
    workflow_engine, engine, planner, _history, provider = _stack(root)
    assert provider is not None

    with pytest.raises(InvalidWorkflowError) as missing:
        workflow_engine.execute(
            workflow_id="download-and-verify",
            workspace_id=WORKSPACE,
            auth_context=make_auth_context(),
            variables={"url": "https://example.com/x"},
        )
    assert missing.value.code == "missing_variable"

    with pytest.raises(InvalidWorkflowError) as unknown:
        workflow_engine.execute(
            workflow_id="download-and-verify",
            workspace_id=WORKSPACE,
            auth_context=make_auth_context(),
            variables={
                "url": "https://example.com/x",
                "destination": "inbox/x.txt",
                "extra": "nope",
            },
        )
    assert unknown.value.code == "unknown_variable"

    with pytest.raises(InvalidWorkflowError) as blank:
        workflow_engine.execute(
            workflow_id="download-and-verify",
            workspace_id=WORKSPACE,
            auth_context=make_auth_context(),
            variables={"url": "   ", "destination": "inbox/x.txt"},
        )
    assert blank.value.code == "invalid_variable_value"

    # No planner/engine side effects when validation fails.
    assert planner.create_plan_calls == []
    assert engine.list_executions(workspace_id=WORKSPACE) == ()
    assert provider.download_calls == 0


def test_7_execution_history_recorded(tmp_path: Path) -> None:
    """7. Verify execution history is recorded."""
    root = tmp_path / "ws"
    root.mkdir()
    workflow_engine, _engine, _planner, history, _provider = _stack(root)

    result = workflow_engine.execute(
        workflow_id="download-and-verify",
        workspace_id=WORKSPACE,
        auth_context=make_auth_context(),
        variables={
            "url": "https://example.com/hist.txt",
            "destination": "inbox/hist.txt",
        },
    )

    entries = history.list_for_workspace(workspace_id=WORKSPACE)
    assert len(entries) == 1
    entry = entries[0]
    assert entry.instance_id == result.instance_id
    assert entry.workflow_name == "Download and Verify"
    assert entry.workspace_id == WORKSPACE.value
    assert entry.status == "completed"
    assert entry.duration == result.duration
    assert "browser" in entry.executed_capabilities
    assert "filesystem" in entry.executed_capabilities
    assert entry.audit_references == result.audit_references

    stored = history.get_result(result.instance_id, workspace_id=WORKSPACE)
    assert stored is not None
    assert stored.status == "completed"
    assert stored.outputs["file_exists"] is True


def test_8_every_step_creates_audit_entry(tmp_path: Path) -> None:
    """8. Verify every workflow step creates an audit entry."""
    root = tmp_path / "ws"
    root.mkdir()
    workflow_engine, engine, _planner, _history, _provider = _stack(root)

    result = workflow_engine.execute(
        workflow_id="download-and-verify",
        workspace_id=WORKSPACE,
        auth_context=make_auth_context(),
        variables={
            "url": "https://example.com/audit.txt",
            "destination": "inbox/audit.txt",
        },
    )

    assert len(result.audit_references) == 2
    audit = engine.list_audit(workspace_id=WORKSPACE)
    for execution_id, capability_id in zip(
        result.audit_references,
        ("browser", "filesystem"),
        strict=True,
    ):
        step_audits = [entry for entry in audit if entry.execution_id == execution_id]
        assert step_audits, f"missing audit for {execution_id}"
        assert any(entry.capability_id == capability_id for entry in step_audits)
        assert any(entry.status.value == "completed" for entry in step_audits)


def test_9_execution_plan_generated_before_running(tmp_path: Path) -> None:
    """9. Verify workflow execution generates an execution plan before running."""
    root = tmp_path / "ws"
    root.mkdir()
    (root / "folder").mkdir()
    workflow_engine, engine, planner, _history, _provider = _stack(
        root,
        with_browser=False,
    )

    # Preview plan for variable-only workflow (no prior-step refs).
    plan = workflow_engine.materialize_plan(
        workflow_id="list-directory",
        workspace_id=WORKSPACE,
        variables={"source_folder": str(root / "folder")},
    )
    assert plan.plan_id
    assert plan.steps[0].capability_id == "filesystem"
    assert plan.metadata["source"] == "workflow_engine"
    assert engine.list_executions(workspace_id=WORKSPACE) == ()

    planner.create_plan_calls.clear()
    result = workflow_engine.execute(
        workflow_id="list-directory",
        workspace_id=WORKSPACE,
        auth_context=make_auth_context(),
        variables={"source_folder": str(root / "folder")},
    )
    assert result.status == "completed"
    assert planner.create_plan_calls, "planner.create_plan must run before execute"
    assert result.step_results[0].plan_id

    # Browser+Filesystem workflow: each step has its own plan_id from planner.
    workflow_engine_b, engine_b, planner_b, _h, _p = _stack(root)
    planner_b.create_plan_calls.clear()
    multi = workflow_engine_b.execute(
        workflow_id="download-and-verify",
        workspace_id=WORKSPACE,
        auth_context=make_auth_context(),
        variables={
            "url": "https://example.com/plan.txt",
            "destination": "inbox/plan.txt",
        },
    )
    assert multi.status == "completed"
    assert len(planner_b.create_plan_calls) == 2
    assert all(step.plan_id for step in multi.step_results)
    # Plans were created before corresponding engine submissions (audit exists after).
    for step in multi.step_results:
        assert step.execution_id
        fetched = engine_b.get(step.execution_id, workspace_id=WORKSPACE)
        assert fetched.metadata.get("plan_id") == step.plan_id
        assert fetched.metadata.get("source") == "capability_planner"
        assert fetched.metadata.get("workflow_id") == "download-and-verify"


def test_acceptance_reusable_workflow_execution(tmp_path: Path) -> None:
    (tmp_path / "downloads").mkdir()
    (tmp_path / "downloads" / "invoice.pdf").write_text("%PDF", encoding="utf-8")
    workflow_engine, *_ = _stack(tmp_path, with_browser=False)

    result = workflow_engine.execute(
        workflow_id="list-directory",
        workspace_id=WORKSPACE,
        auth_context=make_auth_context(),
        variables={"source_folder": str(tmp_path / "downloads")},
    )

    assert result.status == "completed"
    assert "invoice.pdf" in result.outputs["entries"]


def test_acceptance_sequential_multi_capability_git(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path)
    workflow_engine, engine, *_rest = _stack(tmp_path, with_browser=False, with_git=True)

    result = workflow_engine.execute(
        workflow_id="summarize-git-status",
        workspace_id=WORKSPACE,
        auth_context=make_auth_context(),
        variables={"repository": str(repo)},
    )

    assert result.status == "completed"
    assert result.completed_steps == ("status", "history")
    assert "git_status" in result.outputs
    assert "recent_commits" in result.outputs
    git_audits = [
        entry for entry in engine.list_audit(workspace_id=WORKSPACE) if entry.capability_id == "git"
    ]
    assert len(git_audits) >= 2
