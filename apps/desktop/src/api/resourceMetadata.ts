import { apiFetch } from "./client";
import type { ResourceMetadataResponse } from "./types";

export async function getResourceMetadata(
  workspaceId: string,
  memberKind: string,
  memberId: string,
): Promise<ResourceMetadataResponse> {
  return apiFetch<ResourceMetadataResponse>(
    `/resource-metadata/${encodeURIComponent(memberKind)}/${encodeURIComponent(memberId)}`,
    { workspaceId },
  );
}

export async function putResourceMetadata(
  workspaceId: string,
  memberKind: string,
  memberId: string,
  body: {
    title?: string | null;
    description?: string | null;
    notes?: string | null;
  },
): Promise<ResourceMetadataResponse> {
  return apiFetch<ResourceMetadataResponse>(
    `/resource-metadata/${encodeURIComponent(memberKind)}/${encodeURIComponent(memberId)}`,
    {
      workspaceId,
      method: "PUT",
      body: JSON.stringify({
        title: body.title ?? null,
        description: body.description ?? null,
        notes: body.notes ?? null,
      }),
    },
  );
}
