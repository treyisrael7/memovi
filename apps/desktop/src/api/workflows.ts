import { apiFetch } from "./client";
import type {
  WorkflowDefinition,
  WorkflowExecutionResult,
  WorkflowHistoryListResponse,
  WorkflowListResponse,
} from "./types";

export async function listWorkflows(
  workspaceId: string,
): Promise<WorkflowListResponse> {
  return apiFetch<WorkflowListResponse>("/workflows", { workspaceId });
}

export async function getWorkflow(
  workspaceId: string,
  workflowId: string,
): Promise<WorkflowDefinition> {
  return apiFetch<WorkflowDefinition>(`/workflows/${workflowId}`, {
    workspaceId,
  });
}

export async function executeWorkflow(
  workspaceId: string,
  workflowId: string,
  body: {
    variables?: Record<string, unknown>;
    conversation_id?: string | null;
    correlation_id?: string | null;
  } = {},
): Promise<WorkflowExecutionResult> {
  return apiFetch<WorkflowExecutionResult>(`/workflows/${workflowId}/execute`, {
    workspaceId,
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function listWorkflowHistory(
  workspaceId: string,
  limit = 50,
): Promise<WorkflowHistoryListResponse> {
  return apiFetch<WorkflowHistoryListResponse>(
    `/workflows/history?limit=${limit}`,
    { workspaceId },
  );
}

export async function getWorkflowExecution(
  workspaceId: string,
  instanceId: string,
): Promise<WorkflowExecutionResult> {
  return apiFetch<WorkflowExecutionResult>(`/workflows/history/${instanceId}`, {
    workspaceId,
  });
}
