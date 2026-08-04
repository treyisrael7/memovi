import { ApiRequestError, apiFetch, apiUrl } from "./client";
import { WORKSPACE_ID_HEADER } from "./config";
import type {
  DocumentListResponse,
  DocumentSummary,
  IngestDocumentResponse,
  ReprocessDocumentResponse,
} from "./types";

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

export async function deleteDocument(
  workspaceId: string,
  documentId: string,
): Promise<void> {
  await apiFetch<void>(`/documents/${documentId}`, {
    workspaceId,
    method: "DELETE",
  });
}

export async function reprocessDocument(
  workspaceId: string,
  documentId: string,
): Promise<ReprocessDocumentResponse> {
  return apiFetch<ReprocessDocumentResponse>(
    `/documents/${documentId}/reprocess`,
    {
      workspaceId,
      method: "POST",
    },
  );
}

/**
 * Uploads a document with progress reporting. Uses XMLHttpRequest because the
 * Fetch API does not expose upload progress events.
 */
export function uploadDocument(
  workspaceId: string,
  file: File,
  options: {
    onProgress?: (fraction: number) => void;
    signal?: AbortSignal;
  } = {},
): Promise<IngestDocumentResponse> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", apiUrl("/documents"));
    xhr.withCredentials = true;
    xhr.setRequestHeader(WORKSPACE_ID_HEADER, workspaceId);

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && options.onProgress) {
        options.onProgress(event.loaded / event.total);
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as IngestDocumentResponse);
        } catch {
          reject(
            new ApiRequestError("Backend returned an unexpected response.", {
              status: xhr.status,
              kind: "parse",
            }),
          );
        }
        return;
      }

      let detail: string | null = null;
      try {
        const payload = JSON.parse(xhr.responseText) as { detail?: unknown };
        if (typeof payload.detail === "string") {
          detail = payload.detail;
        }
      } catch {
        detail = null;
      }
      reject(
        new ApiRequestError(
          detail ?? `Upload failed with HTTP ${xhr.status}.`,
          {
            status: xhr.status,
            kind: "http",
            detail,
          },
        ),
      );
    };

    xhr.onerror = () => {
      reject(
        new ApiRequestError(
          "Cannot reach the Memovi backend. Start it with `task backend`, then retry.",
          { kind: "network" },
        ),
      );
    };

    xhr.onabort = () => {
      reject(new DOMException("Upload was cancelled.", "AbortError"));
    };

    if (options.signal) {
      if (options.signal.aborted) {
        xhr.abort();
        return;
      }
      options.signal.addEventListener("abort", () => xhr.abort());
    }

    const formData = new FormData();
    formData.append("file", file);
    xhr.send(formData);
  });
}
