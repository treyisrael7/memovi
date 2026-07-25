"""In-memory workflow library with built-in reusable definitions."""

from __future__ import annotations

from threading import Lock

from memovi_automation.domain.exceptions import UnknownWorkflowError
from memovi_automation.domain.value_objects.workflow import (
    WorkflowDefinition,
    WorkflowStep,
    WorkflowVariable,
)


def built_in_workflows() -> tuple[WorkflowDefinition, ...]:
    """Human-readable starter workflows for the library."""
    return (
        WorkflowDefinition(
            workflow_id="list-directory",
            name="List Directory",
            description="List entries in a folder using the Filesystem capability.",
            variables=(
                WorkflowVariable(
                    name="source_folder",
                    type="path",
                    description="Folder to list",
                    required=True,
                ),
            ),
            steps=(
                WorkflowStep(
                    step_id="list",
                    capability_id="filesystem",
                    operation="list_directory",
                    input_mapping={"path": "${source_folder}"},
                    output_mapping={"entries": "$.entries", "count": "$.count"},
                    expected_result="Directory listing",
                    description="List files and folders at source_folder",
                ),
            ),
            expected_outputs=("entries", "count"),
        ),
        WorkflowDefinition(
            workflow_id="summarize-git-status",
            name="Summarize Git Status",
            description="Inspect a repository status, then fetch recent commit history.",
            variables=(
                WorkflowVariable(
                    name="repository",
                    type="path",
                    description="Path to the Git repository",
                    required=True,
                ),
            ),
            steps=(
                WorkflowStep(
                    step_id="status",
                    capability_id="git",
                    operation="status",
                    input_mapping={"repository": "${repository}"},
                    output_mapping={"git_status": "$"},
                    expected_result="Repository status",
                    description="Read working tree status",
                ),
                WorkflowStep(
                    step_id="history",
                    capability_id="git",
                    operation="commit_history",
                    input_mapping={
                        "repository": "${repository}",
                        "limit": 10,
                    },
                    output_mapping={"recent_commits": "$"},
                    expected_result="Recent commits",
                    description="Read recent commit history",
                ),
            ),
            expected_outputs=("git_status", "recent_commits"),
        ),
        WorkflowDefinition(
            workflow_id="inspect-then-list",
            name="Inspect Path Then List",
            description=(
                "Get metadata for a path, then list the directory using the "
                "resolved path from the prior step."
            ),
            variables=(
                WorkflowVariable(
                    name="source_folder",
                    type="path",
                    description="Directory to inspect",
                    required=True,
                ),
            ),
            steps=(
                WorkflowStep(
                    step_id="metadata",
                    capability_id="filesystem",
                    operation="get_metadata",
                    input_mapping={"path": "${source_folder}"},
                    output_mapping={"resolved_path": "$.path"},
                    expected_result="Path metadata",
                ),
                WorkflowStep(
                    step_id="list",
                    capability_id="filesystem",
                    operation="list_directory",
                    input_mapping={"path": "${steps.metadata.path}"},
                    output_mapping={"entries": "$.entries"},
                    expected_result="Directory listing",
                ),
            ),
            expected_outputs=("resolved_path", "entries"),
        ),
        WorkflowDefinition(
            workflow_id="run-command",
            name="Run Command",
            description="Execute a shell command with the Terminal capability.",
            variables=(
                WorkflowVariable(
                    name="command",
                    type="string",
                    description="Shell command to run",
                    required=True,
                ),
                WorkflowVariable(
                    name="working_directory",
                    type="path",
                    description="Working directory under an allowed root",
                    required=False,
                    default=None,
                ),
            ),
            steps=(
                WorkflowStep(
                    step_id="execute",
                    capability_id="terminal",
                    operation="execute",
                    input_mapping={
                        "command": "${command}",
                        "working_directory": "${working_directory}",
                    },
                    output_mapping={
                        "exit_code": "$.exit_code",
                        "stdout": "$.stdout",
                    },
                    expected_result="TerminalResult",
                    description="Run command via Terminal",
                ),
            ),
            expected_outputs=("exit_code", "stdout"),
        ),
        WorkflowDefinition(
            workflow_id="download-and-verify",
            name="Download and Verify",
            description=(
                "Download a file with the Browser capability, then verify it "
                "exists with the Filesystem capability using the prior step output."
            ),
            variables=(
                WorkflowVariable(
                    name="url",
                    type="string",
                    description="URL to download",
                    required=True,
                ),
                WorkflowVariable(
                    name="destination",
                    type="path",
                    description="Filesystem destination under an allowed root",
                    required=True,
                ),
            ),
            steps=(
                WorkflowStep(
                    step_id="download",
                    capability_id="browser",
                    operation="download_file",
                    input_mapping={
                        "url": "${url}",
                        "destination": "${destination}",
                    },
                    output_mapping={
                        "downloaded_path": "$.destination",
                        "bytes_written": "$.bytes_written",
                    },
                    expected_result="DownloadResult",
                    description="Download URL to destination via Browser",
                ),
                WorkflowStep(
                    step_id="verify",
                    capability_id="filesystem",
                    operation="exists",
                    input_mapping={"path": "${steps.download.destination}"},
                    output_mapping={"file_exists": "$.exists"},
                    expected_result="FilesystemExists",
                    description="Confirm downloaded file exists via Filesystem",
                ),
            ),
            expected_outputs=("downloaded_path", "bytes_written", "file_exists"),
        ),
    )


class InMemoryWorkflowLibrary:
    """Thread-safe process-local WorkflowLibrary."""

    def __init__(
        self,
        definitions: tuple[WorkflowDefinition, ...] | None = None,
        *,
        include_built_ins: bool = True,
    ) -> None:
        self._lock = Lock()
        self._definitions: dict[str, WorkflowDefinition] = {}
        if include_built_ins:
            for item in built_in_workflows():
                self._definitions[item.workflow_id] = item
        if definitions is not None:
            for item in definitions:
                self._definitions[item.workflow_id] = item

    def get(self, workflow_id: str) -> WorkflowDefinition:
        key = workflow_id.strip()
        with self._lock:
            definition = self._definitions.get(key)
        if definition is None:
            raise UnknownWorkflowError(
                f"Unknown workflow '{workflow_id}'.",
                workflow_id=workflow_id,
            )
        return definition

    def list(self) -> tuple[WorkflowDefinition, ...]:
        with self._lock:
            return tuple(self._definitions.values())

    def register(self, definition: WorkflowDefinition) -> None:
        with self._lock:
            self._definitions[definition.workflow_id] = definition
