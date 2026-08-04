import { apiFetch } from "./client";
import type {
  CapabilityExecution,
  CapabilityExecutionListResponse,
  CapabilityListResponse,
  ConversationCapabilityExecutionListResponse,
  ExecutionAuditListResponse,
  PermissionModeResponse,
} from "./types";

export async function listCapabilities(
  workspaceId: string,
): Promise<CapabilityListResponse> {
  return apiFetch<CapabilityListResponse>("/capabilities", { workspaceId });
}

export async function setCapabilityPermissionMode(
  workspaceId: string,
  capabilityId: string,
  permissionMode: string,
): Promise<PermissionModeResponse> {
  return apiFetch<PermissionModeResponse>(
    `/capabilities/${capabilityId}/permission-mode`,
    {
      workspaceId,
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ permission_mode: permissionMode }),
    },
  );
}

export async function listPendingExecutions(
  workspaceId: string,
): Promise<CapabilityExecutionListResponse> {
  return apiFetch<CapabilityExecutionListResponse>(
    "/capabilities/executions?status=pending_approval",
    { workspaceId },
  );
}

export async function listConversationExecutions(
  workspaceId: string,
  conversationId: string,
): Promise<ConversationCapabilityExecutionListResponse> {
  return apiFetch<ConversationCapabilityExecutionListResponse>(
    `/conversations/${conversationId}/capability-executions`,
    { workspaceId },
  );
}

export async function listExecutionAudit(
  workspaceId: string,
  limit = 100,
): Promise<ExecutionAuditListResponse> {
  return apiFetch<ExecutionAuditListResponse>(
    `/capabilities/executions/audit?limit=${limit}`,
    { workspaceId },
  );
}

export async function requestConversationCapabilityExecution(
  workspaceId: string,
  conversationId: string,
  body: {
    capability_id: string;
    arguments?: Record<string, unknown>;
  },
): Promise<CapabilityExecution> {
  return apiFetch<CapabilityExecution>(
    `/conversations/${conversationId}/capability-executions`,
    {
      workspaceId,
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  );
}

export async function submitCapabilityExecution(
  workspaceId: string,
  body: {
    capability_id: string;
    arguments?: Record<string, unknown>;
    conversation_id?: string | null;
  },
): Promise<CapabilityExecution> {
  return apiFetch<CapabilityExecution>("/capabilities/executions", {
    workspaceId,
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function approveCapabilityExecution(
  workspaceId: string,
  executionId: string,
): Promise<CapabilityExecution> {
  return apiFetch<CapabilityExecution>(
    `/capabilities/executions/${executionId}/approve`,
    { workspaceId, method: "POST" },
  );
}

export async function cancelCapabilityExecution(
  workspaceId: string,
  executionId: string,
): Promise<CapabilityExecution> {
  return apiFetch<CapabilityExecution>(
    `/capabilities/executions/${executionId}/cancel`,
    { workspaceId, method: "POST" },
  );
}
