import { apiFetch } from "./client";
import type { DocumentListResponse, DocumentSummary } from "./types";

export async function listDocuments(
  workspaceId: string,
): Promise<DocumentListResponse> {
  return apiFetch<DocumentListResponse>("/documents", { workspaceId });
}

export async function getDocument(
  workspaceId: string,
  documentId: string,
): Promise<DocumentSummary> {
  return apiFetch<DocumentSummary>(`/documents/${documentId}`, { workspaceId });
}
