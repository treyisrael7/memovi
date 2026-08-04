import { apiFetch } from "./client";
import { DEFAULT_WORKSPACE_ID } from "./config";
import type { WorkspaceListResponse, WorkspaceResponse } from "./types";

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
