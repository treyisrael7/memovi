import { apiFetch } from "./client";
import type {
  CollectionListResponse,
  CollectionMembershipListResponse,
  CollectionMembershipResponse,
  CollectionResponse,
  CollectionSummaryResponse,
} from "./types";

export type CollectionMemberKind =
  | "document"
  | "knowledge"
  | "conversation"
  | "workflow"
  | string;

export async function listCollections(
  workspaceId: string,
): Promise<CollectionListResponse> {
  return apiFetch<CollectionListResponse>("/collections", { workspaceId });
}

export async function createCollection(
  workspaceId: string,
  body: { name: string; description?: string },
): Promise<CollectionResponse> {
  return apiFetch<CollectionResponse>("/collections", {
    workspaceId,
    method: "POST",
    body: JSON.stringify({
      name: body.name,
      description: body.description ?? "",
    }),
  });
}

export async function getCollection(
  workspaceId: string,
  collectionId: string,
): Promise<CollectionResponse> {
  return apiFetch<CollectionResponse>(`/collections/${collectionId}`, {
    workspaceId,
  });
}

export async function getCollectionSummary(
  workspaceId: string,
  collectionId: string,
): Promise<CollectionSummaryResponse> {
  return apiFetch<CollectionSummaryResponse>(
    `/collections/${collectionId}/summary`,
    { workspaceId },
  );
}

export async function renameCollection(
  workspaceId: string,
  collectionId: string,
  name: string,
): Promise<CollectionResponse> {
  return apiFetch<CollectionResponse>(`/collections/${collectionId}`, {
    workspaceId,
    method: "PATCH",
    body: JSON.stringify({ name }),
  });
}

export async function updateCollectionDescription(
  workspaceId: string,
  collectionId: string,
  description: string,
): Promise<CollectionResponse> {
  return apiFetch<CollectionResponse>(
    `/collections/${collectionId}/description`,
    {
      workspaceId,
      method: "PATCH",
      body: JSON.stringify({ description }),
    },
  );
}

export async function deleteCollection(
  workspaceId: string,
  collectionId: string,
): Promise<void> {
  await apiFetch<void>(`/collections/${collectionId}`, {
    workspaceId,
    method: "DELETE",
  });
}

export async function listCollectionMembers(
  workspaceId: string,
  collectionId: string,
  params: { memberKind?: string; q?: string } = {},
): Promise<CollectionMembershipListResponse> {
  const qs = new URLSearchParams();
  if (params.memberKind) qs.set("member_kind", params.memberKind);
  if (params.q) qs.set("q", params.q);
  const suffix = qs.size > 0 ? `?${qs.toString()}` : "";
  return apiFetch<CollectionMembershipListResponse>(
    `/collections/${collectionId}/members${suffix}`,
    { workspaceId },
  );
}

export async function addCollectionMember(
  workspaceId: string,
  collectionId: string,
  body: {
    memberKind: CollectionMemberKind;
    memberId: string;
    reason?: string;
  },
): Promise<CollectionMembershipResponse> {
  return apiFetch<CollectionMembershipResponse>(
    `/collections/${collectionId}/members`,
    {
      workspaceId,
      method: "POST",
      body: JSON.stringify({
        member_kind: body.memberKind,
        member_id: body.memberId,
        reason: body.reason ?? "Added by user",
      }),
    },
  );
}

export async function removeCollectionMember(
  workspaceId: string,
  collectionId: string,
  memberKind: string,
  memberId: string,
): Promise<void> {
  await apiFetch<void>(
    `/collections/${collectionId}/members/${encodeURIComponent(memberKind)}/${encodeURIComponent(memberId)}`,
    {
      workspaceId,
      method: "DELETE",
    },
  );
}
