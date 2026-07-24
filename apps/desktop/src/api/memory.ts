import { apiFetch } from "./client";
import type {
  ConceptListResponse,
  KnowledgeDashboard,
  KnowledgeDetail,
  KnowledgeSummaryListResponse,
  RelationshipListResponse,
} from "./types";

export interface ListKnowledgeParams {
  documentId?: string;
  sourceType?: string;
  mimeType?: string;
  entityType?: string;
}

export async function getKnowledgeDashboard(
  workspaceId: string,
): Promise<KnowledgeDashboard> {
  return apiFetch<KnowledgeDashboard>("/memory/dashboard", { workspaceId });
}

export async function listKnowledge(
  workspaceId: string,
  params: ListKnowledgeParams = {},
): Promise<KnowledgeSummaryListResponse> {
  const qs = new URLSearchParams();
  if (params.documentId) qs.set("document_id", params.documentId);
  if (params.sourceType) qs.set("source_type", params.sourceType);
  if (params.mimeType) qs.set("mime_type", params.mimeType);
  if (params.entityType) qs.set("entity_type", params.entityType);
  const suffix = qs.size > 0 ? `?${qs.toString()}` : "";
  return apiFetch<KnowledgeSummaryListResponse>(`/memory${suffix}`, {
    workspaceId,
  });
}

export async function getKnowledge(
  workspaceId: string,
  knowledgeItemId: string,
): Promise<KnowledgeDetail> {
  return apiFetch<KnowledgeDetail>(`/memory/${knowledgeItemId}`, {
    workspaceId,
  });
}

export async function listDocumentKnowledge(
  workspaceId: string,
  documentId: string,
): Promise<KnowledgeSummaryListResponse> {
  return apiFetch<KnowledgeSummaryListResponse>(
    `/memory/by-document/${documentId}`,
    { workspaceId },
  );
}

export async function listConcepts(
  workspaceId: string,
): Promise<ConceptListResponse> {
  return apiFetch<ConceptListResponse>("/memory/concepts", { workspaceId });
}

export async function listRelationships(
  workspaceId: string,
  params: { documentId?: string; knowledgeItemId?: string } = {},
): Promise<RelationshipListResponse> {
  const qs = new URLSearchParams();
  if (params.documentId) qs.set("document_id", params.documentId);
  if (params.knowledgeItemId) qs.set("knowledge_item_id", params.knowledgeItemId);
  const suffix = qs.size > 0 ? `?${qs.toString()}` : "";
  return apiFetch<RelationshipListResponse>(`/memory/relationships${suffix}`, {
    workspaceId,
  });
}
