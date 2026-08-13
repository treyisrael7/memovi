import { useState } from "react";

import { getDocument } from "../api/documents";
import { listDocumentKnowledge } from "../api/memory";
import type { Citation } from "../api/types";
import {
  resolveCitationDestination,
  SOURCE_UNAVAILABLE_MESSAGE,
} from "../chat/resolveCitationDestination";
import { useAppState } from "../state/AppStateContext";
import { useToast } from "./ui/ToastContext";

export function CitationList({ citations }: { citations: Citation[] }) {
  const {
    activeWorkspace,
    openKnowledgeItem,
    openDocument,
    openSearchSource,
  } = useAppState();
  const { showToast } = useToast();
  const [busyKey, setBusyKey] = useState<string | null>(null);

  if (citations.length === 0) {
    return null;
  }

  async function handleOpen(citation: Citation) {
    const key = `${citation.document_id}:${citation.chunk_id}`;
    const workspaceId = activeWorkspace?.id;
    if (!workspaceId || busyKey) {
      if (!workspaceId) {
        showToast(SOURCE_UNAVAILABLE_MESSAGE, "bad");
      }
      return;
    }

    setBusyKey(key);
    try {
      const destination = await resolveCitationDestination(
        workspaceId,
        citation,
        { listDocumentKnowledge, getDocument },
      );
      if (destination.kind === "knowledge") {
        openKnowledgeItem(destination.knowledgeItemId);
        return;
      }
      if (destination.kind === "document") {
        openDocument(destination.documentId);
        return;
      }
      if (destination.kind === "search") {
        openSearchSource(destination.documentId, destination.query);
        return;
      }
      showToast(destination.message, "bad");
    } catch {
      showToast(SOURCE_UNAVAILABLE_MESSAGE, "bad");
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <ul className="citation-list">
      {citations.map((citation) => {
        const key = `${citation.document_id}:${citation.chunk_id}`;
        const label = citation.document_title ?? citation.document_id;
        return (
          <li key={key}>
            <button
              type="button"
              className="citation-chip"
              title="Open the source this answer used"
              aria-label={`Open source: ${label}`}
              disabled={busyKey === key}
              onClick={() => void handleOpen(citation)}
            >
              {label}
            </button>
          </li>
        );
      })}
    </ul>
  );
}
