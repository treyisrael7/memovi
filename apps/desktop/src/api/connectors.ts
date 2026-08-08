import { apiFetch } from "./client";
import type {
  ConnectorListResponse,
  FilesystemFolder,
  FilesystemFolderListResponse,
  SyncFilesystemFolderResponse,
} from "./types";

export async function listConnectors(
  workspaceId?: string | null,
): Promise<ConnectorListResponse> {
  return apiFetch<ConnectorListResponse>("/connectors", { workspaceId });
}

export async function listFilesystemFolders(
  workspaceId: string,
): Promise<FilesystemFolderListResponse> {
  return apiFetch<FilesystemFolderListResponse>("/connectors/filesystem/folders", {
    workspaceId,
  });
}

export async function addFilesystemFolder(
  workspaceId: string,
  body: { root_path: string; display_name?: string | null },
): Promise<FilesystemFolder> {
  return apiFetch<FilesystemFolder>("/connectors/filesystem/folders", {
    method: "POST",
    workspaceId,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function removeFilesystemFolder(
  workspaceId: string,
  folderId: string,
): Promise<void> {
  await apiFetch<void>(`/connectors/filesystem/folders/${folderId}`, {
    method: "DELETE",
    workspaceId,
  });
}

export async function syncFilesystemFolder(
  workspaceId: string,
  folderId: string,
  syncMode?: "initial" | "incremental" | null,
): Promise<SyncFilesystemFolderResponse> {
  return apiFetch<SyncFilesystemFolderResponse>(
    `/connectors/filesystem/folders/${folderId}/sync`,
    {
      method: "POST",
      workspaceId,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(
        syncMode ? { sync_mode: syncMode } : {},
      ),
    },
  );
}
