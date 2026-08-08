import { apiFetch } from "./client";
import { DEFAULT_WORKSPACE_ID } from "./config";
import type {
  TransferWorkspaceOwnershipResponse,
  WorkspaceListResponse,
  WorkspaceMembership,
  WorkspaceMembershipListResponse,
  WorkspaceResponse,
} from "./types";

export async function listWorkspaces(): Promise<WorkspaceResponse[]> {
  const payload = await apiFetch<WorkspaceListResponse>("/workspaces");
  return payload.workspaces;
}

export async function createWorkspace(
  name: string,
): Promise<WorkspaceResponse> {
  return apiFetch<WorkspaceResponse>("/workspaces", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
}

export async function listWorkspaceMembers(
  workspaceId: string,
): Promise<WorkspaceMembership[]> {
  const payload = await apiFetch<WorkspaceMembershipListResponse>(
    `/workspaces/${workspaceId}/members`,
  );
  return payload.items;
}

export async function inviteWorkspaceMember(
  workspaceId: string,
  email: string,
): Promise<WorkspaceMembership> {
  return apiFetch<WorkspaceMembership>(`/workspaces/${workspaceId}/members`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
}

export async function removeWorkspaceMember(
  workspaceId: string,
  memberUserId: string,
): Promise<WorkspaceMembership> {
  return apiFetch<WorkspaceMembership>(
    `/workspaces/${workspaceId}/members/${memberUserId}`,
    { method: "DELETE" },
  );
}

export async function transferWorkspaceOwnership(
  workspaceId: string,
  newOwnerUserId: string,
): Promise<TransferWorkspaceOwnershipResponse> {
  return apiFetch<TransferWorkspaceOwnershipResponse>(
    `/workspaces/${workspaceId}/transfer-ownership`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ new_owner_user_id: newOwnerUserId }),
    },
  );
}

export async function leaveWorkspace(
  workspaceId: string,
): Promise<WorkspaceMembership> {
  return apiFetch<WorkspaceMembership>(`/workspaces/${workspaceId}/leave`, {
    method: "POST",
  });
}

/** Prefer the seeded default workspace when present; otherwise the first listed. */
export function resolveActiveWorkspace(
  workspaces: WorkspaceResponse[],
): WorkspaceResponse | null {
  if (workspaces.length === 0) {
    return null;
  }
  return (
    workspaces.find((workspace) => workspace.id === DEFAULT_WORKSPACE_ID) ??
    workspaces[0]
  );
}
