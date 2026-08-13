import { ApiRequestError } from "../api/client";
import type { Citation } from "../api/types";

export const SOURCE_UNAVAILABLE_MESSAGE =
  "This source is no longer available.";

export type CitationDestination =
  | { kind: "knowledge"; knowledgeItemId: string }
  | { kind: "document"; documentId: string }
  | { kind: "search"; documentId: string; query: string }
  | { kind: "unavailable"; message: string };

export interface CitationLookup {
  listDocumentKnowledge: (
    workspaceId: string,
    documentId: string,
  ) => Promise<{ items: Array<{ id: string }> }>;
  getDocument: (workspaceId: string, documentId: string) => Promise<unknown>;
}

function isNotFound(error: unknown): boolean {
  return error instanceof ApiRequestError && error.status === 404;
}

/**
 * Prefer the most specific openable destination for a chat citation.
 * Citations currently expose document_id (not knowledge_item_id), so knowledge
 * is resolved through the existing by-document memory API.
 */
export async function resolveCitationDestination(
  workspaceId: string,
  citation: Citation,
  lookup: CitationLookup,
): Promise<CitationDestination> {
  const documentId = citation.document_id.trim();
  if (!documentId) {
    return { kind: "unavailable", message: SOURCE_UNAVAILABLE_MESSAGE };
  }

  try {
    const knowledge = await lookup.listDocumentKnowledge(
      workspaceId,
      documentId,
    );
    const knowledgeItemId = knowledge.items[0]?.id;
    if (knowledgeItemId) {
      return { kind: "knowledge", knowledgeItemId };
    }
  } catch (error) {
    if (!isNotFound(error) && !(error instanceof ApiRequestError)) {
      return { kind: "unavailable", message: SOURCE_UNAVAILABLE_MESSAGE };
    }
  }

  try {
    await lookup.getDocument(workspaceId, documentId);
    return { kind: "document", documentId };
  } catch (error) {
    if (!isNotFound(error)) {
      return { kind: "unavailable", message: SOURCE_UNAVAILABLE_MESSAGE };
    }
  }

  const query = citation.document_title?.trim() || documentId;
  return { kind: "search", documentId, query };
}
