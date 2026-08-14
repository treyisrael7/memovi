import { useCallback, useEffect, useMemo, useState } from "react";

import { ApiRequestError } from "../api/client";
import {
  executeWorkflow,
  getWorkflowExecution,
  listWorkflowHistory,
  listWorkflows,
} from "../api/workflows";
import type {
  WorkflowDefinition,
  WorkflowExecutionResult,
  WorkflowHistoryEntry,
} from "../api/types";
import {
  approveCapabilityExecution,
  cancelCapabilityExecution,
} from "../api/capabilities";
import { useAppState } from "../state/AppStateContext";
import { Alert } from "./ui/Alert";
import { Button } from "./ui/Button";
import { EmptyState } from "./ui/EmptyState";
import { executionStatusBadge, StatusBadge } from "./ui/StatusBadge";
import { Tabs } from "./ui/Tabs";
import { PageLayout } from "./ui/PageLayout";
import { LoadingState } from "./ui/LoadingState";

type WorkflowTab = "library" | "run" | "history";

function formatTimestamp(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds)) return "—";
  if (seconds < 1) return `${Math.round(seconds * 1000)} ms`;
  return `${seconds.toFixed(2)} s`;
}

export function WorkflowsPage() {
  const { activeWorkspace, connection } = useAppState();
  const workspaceId = activeWorkspace?.id ?? null;
  const canUseBackend =
    connection.status === "connected" || connection.status === "degraded";

  const [tab, setTab] = useState<WorkflowTab>("library");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRunning, setIsRunning] = useState(false);

  const [workflows, setWorkflows] = useState<WorkflowDefinition[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [variableValues, setVariableValues] = useState<Record<string, string>>(
    {},
  );
  const [latestResult, setLatestResult] =
    useState<WorkflowExecutionResult | null>(null);
  const [history, setHistory] = useState<WorkflowHistoryEntry[]>([]);

  const selected = useMemo(
    () => workflows.find((item) => item.workflow_id === selectedId) ?? null,
    [workflows, selectedId],
  );

  const refresh = useCallback(async () => {
    if (!workspaceId || !canUseBackend) return;
    setIsLoading(true);
    setError(null);
    try {
      const [library, historyResponse] = await Promise.all([
        listWorkflows(workspaceId),
        listWorkflowHistory(workspaceId),
      ]);
      setWorkflows(library.items);
      setHistory(historyResponse.items);
      setSelectedId((current) => {
        if (current && library.items.some((item) => item.workflow_id === current)) {
          return current;
        }
        return library.items[0]?.workflow_id ?? null;
      });
    } catch (err) {
      const message =
        err instanceof ApiRequestError
          ? err.message
          : "Failed to load workflows.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [workspaceId, canUseBackend]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (!selected) {
      setVariableValues({});
      return;
    }
    const next: Record<string, string> = {};
    for (const variable of selected.variables) {
      next[variable.name] =
        variable.default == null ? "" : String(variable.default);
    }
    setVariableValues(next);
  }, [selected]);

  async function handleRun() {
    if (!workspaceId || !selected) return;
    setIsRunning(true);
    setError(null);
    setTab("run");
    try {
      const variables: Record<string, unknown> = {};
      for (const variable of selected.variables) {
        const raw = variableValues[variable.name] ?? "";
        if (!raw && variable.required && variable.default == null) {
          throw new Error(`Variable "${variable.name}" is required.`);
        }
        if (raw !== "" || variable.default != null) {
          variables[variable.name] = raw !== "" ? raw : variable.default;
        }
      }
      const result = await executeWorkflow(workspaceId, selected.workflow_id, {
        variables,
      });
      setLatestResult(result);
      const historyResponse = await listWorkflowHistory(workspaceId);
      setHistory(historyResponse.items);
    } catch (err) {
      const message =
        err instanceof ApiRequestError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Workflow execution failed.";
      setError(message);
    } finally {
      setIsRunning(false);
    }
  }

  async function handleApprovePending() {
    if (!workspaceId || !latestResult) return;
    const pending = latestResult.step_results.find(
      (step) => step.status === "pending_approval" && step.execution_id,
    );
    if (!pending?.execution_id) return;
    setIsRunning(true);
    setError(null);
    try {
      await approveCapabilityExecution(workspaceId, pending.execution_id);
      const refreshed = await getWorkflowExecution(
        workspaceId,
        latestResult.instance_id,
      );
      setLatestResult(refreshed);
      const historyResponse = await listWorkflowHistory(workspaceId);
      setHistory(historyResponse.items);
    } catch (err) {
      const message =
        err instanceof ApiRequestError
          ? err.message
          : "Failed to approve capability execution.";
      setError(message);
    } finally {
      setIsRunning(false);
    }
  }

  async function handleDenyPending() {
    if (!workspaceId || !latestResult) return;
    const pending = latestResult.step_results.find(
      (step) => step.status === "pending_approval" && step.execution_id,
    );
    if (!pending?.execution_id) return;
    setIsRunning(true);
    setError(null);
    try {
      await cancelCapabilityExecution(workspaceId, pending.execution_id);
      const refreshed = await getWorkflowExecution(
        workspaceId,
        latestResult.instance_id,
      );
      setLatestResult(refreshed);
      const historyResponse = await listWorkflowHistory(workspaceId);
      setHistory(historyResponse.items);
    } catch (err) {
      const message =
        err instanceof ApiRequestError
          ? err.message
          : "Failed to deny capability execution.";
      setError(message);
    } finally {
      setIsRunning(false);
    }
  }

  async function openHistoryResult(instanceId: string) {
    if (!workspaceId) return;
    setError(null);
    try {
      const result = await getWorkflowExecution(workspaceId, instanceId);
      setLatestResult(result);
      setTab("run");
    } catch (err) {
      const message =
        err instanceof ApiRequestError
          ? err.message
          : "Failed to load workflow result.";
      setError(message);
    }
  }

  if (!workspaceId) {
    return (
      <PageLayout
        title="Workflows"
        description="Select a workspace to browse and run workflows."
      >
        <EmptyState title="No workspace selected" />
      </PageLayout>
    );
  }

  return (
    <PageLayout
      className="workflows-page"
      title="Workflows"
      description="Reusable capability sequences. Desktop owns presentation only — planning and execution stay on the platform."
      actions={
        <Button onClick={() => void refresh()} busy={isLoading}>
          Refresh
        </Button>
      }
    >
      <Tabs
        aria-label="Workflow views"
        className="workflows-tabs"
        value={tab}
        onChange={(id) => setTab(id as WorkflowTab)}
        items={[
          { id: "library", label: "Library" },
          { id: "run", label: "Run / Progress" },
          { id: "history", label: "History" },
        ]}
      />

      {error ? <Alert tone="bad">{error}</Alert> : null}

      {!canUseBackend ? (
        <EmptyState
          title="Backend unavailable"
          description="Connect to the backend to use workflows."
        />
      ) : null}

      {tab === "library" ? (
        <div className="workflows-split">
          <ul className="workflows-list">
            {workflows.map((workflow) => (
              <li key={workflow.workflow_id}>
                <button
                  type="button"
                  className="workflows-list-item"
                  data-active={workflow.workflow_id === selectedId}
                  onClick={() => {
                    setSelectedId(workflow.workflow_id);
                    setTab("run");
                  }}
                >
                  <strong>{workflow.name}</strong>
                  <span>{workflow.description}</span>
                  <em>
                    {workflow.steps.length} steps ·{" "}
                    {workflow.required_capabilities.join(", ")}
                  </em>
                </button>
              </li>
            ))}
            {workflows.length === 0 && !isLoading ? (
              <li>
                <EmptyState title="No workflows registered" />
              </li>
            ) : null}
            {isLoading && workflows.length === 0 ? (
              <li>
                <LoadingState label="Loading workflows…" />
              </li>
            ) : null}
          </ul>
          {selected ? (
            <article className="workflows-detail">
              <h2>{selected.name}</h2>
              <p>{selected.description}</p>
              <h3>Steps</h3>
              <ol className="workflows-steps">
                {selected.steps.map((step) => (
                  <li key={step.step_id}>
                    <strong>{step.step_id}</strong> — {step.capability_id}.
                    {step.operation}
                    {step.description ? ` · ${step.description}` : ""}
                  </li>
                ))}
              </ol>
              <h3>Variables</h3>
              <ul className="workflows-vars">
                {selected.variables.map((variable) => (
                  <li key={variable.name}>
                    <code>{variable.name}</code> ({variable.type}
                    {variable.required ? ", required" : ""}) —{" "}
                    {variable.description || "No description"}
                  </li>
                ))}
                {selected.variables.length === 0 ? (
                  <li>No variables</li>
                ) : null}
              </ul>
              <Button onClick={() => setTab("run")}>Configure & Run</Button>
            </article>
          ) : null}
        </div>
      ) : null}

      {tab === "run" ? (
        <div className="workflows-run">
          {selected ? (
            <>
              <h2>Run {selected.name}</h2>
              <div className="workflows-form">
                {selected.variables.map((variable) => (
                  <label key={variable.name} className="workflows-field">
                    <span>
                      {variable.name}
                      {variable.required ? " *" : ""}
                    </span>
                    <input
                      type="text"
                      value={variableValues[variable.name] ?? ""}
                      placeholder={variable.description || variable.type}
                      onChange={(event) =>
                        setVariableValues((current) => ({
                          ...current,
                          [variable.name]: event.target.value,
                        }))
                      }
                    />
                  </label>
                ))}
              </div>
              <div className="workflows-actions">
                <Button
                  disabled={isRunning}
                  busy={isRunning}
                  onClick={() => void handleRun()}
                >
                  {isRunning ? "Running…" : "Run Workflow"}
                </Button>
              </div>
            </>
          ) : (
            <EmptyState
              title="Select a workflow"
              description="Choose a workflow from the library to configure and run."
            />
          )}

          {latestResult ? (
            <div className="workflows-progress">
              <h3>Execution Progress</h3>
              <dl className="meta-grid">
                <div className="meta-card">
                  <dt>Status</dt>
                  <dd>
                    <StatusBadge {...executionStatusBadge(latestResult.status)} />
                  </dd>
                </div>
                <div className="meta-card">
                  <dt>Duration</dt>
                  <dd>{formatDuration(latestResult.duration)}</dd>
                </div>
                <div className="meta-card">
                  <dt>Completed</dt>
                  <dd>{latestResult.completed_steps.join(", ") || "—"}</dd>
                </div>
                <div className="meta-card">
                  <dt>Failed</dt>
                  <dd>{latestResult.failed_steps.join(", ") || "—"}</dd>
                </div>
              </dl>

              {latestResult.status === "completed" &&
              latestResult.metadata?.resumed_from_approval ? (
                <p className="lede">
                  Workflow resumed after approval and finished.
                </p>
              ) : null}

              {latestResult.status === "awaiting_approval" ? (
                <div className="workflows-actions">
                  <p className="lede">
                    A capability step is waiting for approval. Approve to continue
                    this workflow from that step — you do not need to run it again.
                  </p>
                  <Button
                    disabled={isRunning}
                    onClick={() => void handleApprovePending()}
                  >
                    Approve
                  </Button>
                  <Button
                    variant="danger"
                    disabled={isRunning}
                    onClick={() => void handleDenyPending()}
                  >
                    Deny
                  </Button>
                </div>
              ) : null}

              <h4>Steps</h4>
              <ol className="workflows-steps">
                {latestResult.step_results.map((step) => (
                  <li key={step.step_id}>
                    <strong>{step.step_id}</strong> [{step.status}]{" "}
                    {step.capability_id}.{step.operation}
                    {step.error_message ? ` — ${step.error_message}` : ""}
                    {step.execution_id ? (
                      <em> · audit {step.execution_id.slice(0, 8)}…</em>
                    ) : null}
                  </li>
                ))}
              </ol>

              <h4>Outputs</h4>
              <pre className="workflows-json">
                {JSON.stringify(latestResult.outputs, null, 2)}
              </pre>

              {latestResult.errors.length > 0 ? (
                <>
                  <h4>Errors</h4>
                  <ul>
                    {latestResult.errors.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}

      {tab === "history" ? (
        <div className="workflows-history">
          <h2>Execution History</h2>
          <ul className="workflows-history-list">
            {history.map((entry) => (
              <li key={entry.instance_id}>
                <button
                  type="button"
                  className="workflows-list-item"
                  onClick={() => void openHistoryResult(entry.instance_id)}
                >
                  <strong>{entry.workflow_name}</strong>
                  <span>
                    {formatTimestamp(entry.executed_at)} ·{" "}
                    {formatDuration(entry.duration)} · {entry.status}
                  </span>
                  <em>
                    {entry.executed_capabilities.join(", ") || "No capabilities"}
                  </em>
                </button>
              </li>
            ))}
            {history.length === 0 ? (
              <li className="lede">No workflow executions yet.</li>
            ) : null}
          </ul>
        </div>
      ) : null}
    </PageLayout>
  );
}
