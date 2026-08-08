import { apiFetch } from "./client";
import type {
  TagAssignmentListResponse,
  TagAssignmentResponse,
  TagListResponse,
  TagResponse,
  TagSuggestResponse,
} from "./types";

export type TagMemberKind =
  | "document"
  | "knowledge"
  | "conversation"
  | "workflow"
  | string;

export async function listTags(workspaceId: string): Promise<TagListResponse> {
  return apiFetch<TagListResponse>("/tags", { workspaceId });
}

export async function createTag(
  workspaceId: string,
  body: { name: string; color?: string | null; description?: string },
): Promise<TagResponse> {
  return apiFetch<TagResponse>("/tags", {
    workspaceId,
    method: "POST",
    body: JSON.stringify({
      name: body.name,
      color: body.color ?? null,
      description: body.description ?? "",
    }),
  });
}

export async function updateTag(
  workspaceId: string,
  tagId: string,
  body: {
    name?: string;
    color?: string | null;
    description?: string;
  },
): Promise<TagResponse> {
  return apiFetch<TagResponse>(`/tags/${tagId}`, {
    workspaceId,
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function deleteTag(
  workspaceId: string,
  tagId: string,
): Promise<void> {
  await apiFetch<void>(`/tags/${tagId}`, {
    workspaceId,
    method: "DELETE",
  });
}

export async function suggestTags(
  workspaceId: string,
  q = "",
): Promise<TagSuggestResponse> {
  const qs = new URLSearchParams();
  if (q) qs.set("q", q);
  const suffix = qs.size > 0 ? `?${qs.toString()}` : "";
  return apiFetch<TagSuggestResponse>(`/tags/suggest${suffix}`, {
    workspaceId,
  });
}

export async function listTagsForTarget(
  workspaceId: string,
  memberKind: TagMemberKind,
  memberId: string,
): Promise<TagSuggestResponse> {
  const qs = new URLSearchParams({
    member_kind: memberKind,
    member_id: memberId,
  });
  return apiFetch<TagSuggestResponse>(`/tags/for-target?${qs.toString()}`, {
    workspaceId,
  });
}

export async function listTagAssignments(
  workspaceId: string,
  tagId: string,
  params: { memberKind?: string; q?: string } = {},
): Promise<TagAssignmentListResponse> {
  const qs = new URLSearchParams();
  if (params.memberKind) qs.set("member_kind", params.memberKind);
  if (params.q) qs.set("q", params.q);
  const suffix = qs.size > 0 ? `?${qs.toString()}` : "";
  return apiFetch<TagAssignmentListResponse>(
    `/tags/${tagId}/assignments${suffix}`,
    { workspaceId },
  );
}

export async function assignTag(
  workspaceId: string,
  tagId: string,
  body: { memberKind: TagMemberKind; memberId: string },
): Promise<TagAssignmentResponse> {
  return apiFetch<TagAssignmentResponse>(`/tags/${tagId}/assignments`, {
    workspaceId,
    method: "POST",
    body: JSON.stringify({
      member_kind: body.memberKind,
      member_id: body.memberId,
    }),
  });
}

export async function unassignTag(
  workspaceId: string,
  tagId: string,
  memberKind: string,
  memberId: string,
): Promise<void> {
  await apiFetch<void>(
    `/tags/${tagId}/assignments/${encodeURIComponent(memberKind)}/${encodeURIComponent(memberId)}`,
    {
      workspaceId,
      method: "DELETE",
    },
  );
}
