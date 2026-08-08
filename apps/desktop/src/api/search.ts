import { apiFetch } from "./client";
import type { SearchResponse } from "./types";

export type SearchMode = "keyword" | "semantic" | "hybrid";

export interface SearchKnowledgeParams {
  q: string;
  mode?: SearchMode;
  documentId?: string;
  collectionId?: string;
  tagIds?: string[];
  sourceType?: string;
  mimeType?: string;
  limit?: number;
  offset?: number;
}

export async function searchKnowledge(
  workspaceId: string,
  params: SearchKnowledgeParams,
): Promise<SearchResponse> {
  const qs = new URLSearchParams({
    q: params.q,
    mode: params.mode ?? "hybrid",
  });
  if (params.documentId) qs.set("document_id", params.documentId);
  if (params.collectionId) qs.set("collection_id", params.collectionId);
  if (params.sourceType) qs.set("source_type", params.sourceType);
  if (params.mimeType) qs.set("mime_type", params.mimeType);
  if (params.limit != null) qs.set("limit", String(params.limit));
  if (params.offset != null) qs.set("offset", String(params.offset));
  for (const tagId of params.tagIds ?? []) {
    qs.append("tag_id", tagId);
  }

  return apiFetch<SearchResponse>(`/search?${qs.toString()}`, { workspaceId });
}
