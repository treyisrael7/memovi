import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type DragEvent,
} from "react";

import { ApiRequestError } from "../api/client";
import { createConversation } from "../api/conversations";
import {
  deleteDocument,
  getDocument,
  listDocuments,
  reprocessDocument,
  uploadDocument,
} from "../api/documents";
import type { DocumentSummary } from "../api/types";
import { useAppState } from "../state/AppStateContext";
import { ConfirmDialog } from "./ui/ConfirmDialog";
import { EmptyState } from "./ui/EmptyState";
import { LoadingState } from "./ui/LoadingState";
import { processingStatusBadge, StatusBadge } from "./ui/StatusBadge";
import { useToast } from "./ui/ToastContext";

interface UploadTask {
  id: string;
  name: string;
  progress: number;
  status: "uploading" | "done" | "error";
  error?: string;
}

const IN_FLIGHT_STATUSES = new Set(["pending", "extracting", "normalizing"]);

function formatTimestamp(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function formatBytesLabel(mimeType: string): string {
  return mimeType || "unknown type";
}

export function DocumentsPage() {
  const { activeWorkspace, connection, startConversationAbout } = useAppState();
  const { showToast } = useToast();
  const workspaceId = activeWorkspace?.id ?? null;
  const canUseBackend =
    connection.status === "connected" || connection.status === "degraded";

  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploads, setUploads] = useState<UploadTask[]>([]);
  const [isDragActive, setIsDragActive] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<DocumentSummary | null>(
    null,
  );
  const [isDeleting, setIsDeleting] = useState(false);
  const [reprocessingId, setReprocessingId] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const selectedDocument = useMemo(
    () => documents.find((doc) => doc.id === selectedId) ?? null,
    [documents, selectedId],
  );

  const hasInFlightProcessing = documents.some((doc) =>
    IN_FLIGHT_STATUSES.has(doc.processing_status ?? ""),
  );

  const refresh = useCallback(async () => {
    if (!workspaceId || !canUseBackend) {
      setDocuments([]);
      return;
    }
    try {
      const payload = await listDocuments(workspaceId);
      setDocuments(payload.items);
      setSelectedId((current) => {
        if (current && payload.items.some((item) => item.id === current)) {
          return current;
        }
        return payload.items[0]?.id ?? null;
      });
    } catch (err) {
      setError(
        err instanceof ApiRequestError
          ? err.message
          : "Failed to load documents.",
      );
    }
  }, [workspaceId, canUseBackend]);

  useEffect(() => {
    if (!workspaceId || !canUseBackend) {
      setDocuments([]);
      setSelectedId(null);
      return;
    }
    let cancelled = false;
    setIsLoading(true);
    setError(null);
    void listDocuments(workspaceId)
      .then((payload) => {
        if (cancelled) return;
        setDocuments(payload.items);
        setSelectedId(payload.items[0]?.id ?? null);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(
            err instanceof ApiRequestError
              ? err.message
              : "Failed to load documents.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [workspaceId, canUseBackend]);

  useEffect(() => {
    if (!hasInFlightProcessing || !workspaceId || !canUseBackend) {
      return;
    }
    const timer = window.setInterval(() => {
      void refresh();
    }, 2000);
    return () => window.clearInterval(timer);
  }, [hasInFlightProcessing, workspaceId, canUseBackend, refresh]);

  const handleFiles = useCallback(
    (files: FileList | File[]) => {
      if (!workspaceId) return;
      const list = Array.from(files);
      for (const file of list) {
        const taskId = crypto.randomUUID();
        setUploads((current) => [
          ...current,
          { id: taskId, name: file.name, progress: 0, status: "uploading" },
        ]);
        uploadDocument(workspaceId, file, {
          onProgress: (fraction: number) => {
            setUploads((current) =>
              current.map((task) =>
                task.id === taskId ? { ...task, progress: fraction } : task,
              ),
            );
          },
        })
          .then(() => {
            setUploads((current) =>
              current.map((task) =>
                task.id === taskId
                  ? { ...task, progress: 1, status: "done" }
                  : task,
              ),
            );
            showToast(`${file.name} uploaded — processing started.`, "ok");
            window.setTimeout(() => {
              setUploads((current) =>
                current.filter((task) => task.id !== taskId),
              );
            }, 3000);
            void refresh();
          })
          .catch((err: unknown) => {
            const message =
              err instanceof ApiRequestError
                ? err.message
                : "Upload failed unexpectedly.";
            setUploads((current) =>
              current.map((task) =>
                task.id === taskId
                  ? { ...task, status: "error", error: message }
                  : task,
              ),
            );
            showToast(`${file.name} failed to upload: ${message}`, "bad");
          });
      }
    },
    [workspaceId, refresh, showToast],
  );

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragActive(false);
    if (event.dataTransfer.files.length > 0) {
      handleFiles(event.dataTransfer.files);
    }
  }

  async function handleReprocess(document: DocumentSummary) {
    if (!workspaceId) return;
    setReprocessingId(document.id);
    try {
      await reprocessDocument(workspaceId, document.id);
      showToast(`Reprocessing ${document.name}…`, "ok");
      const updated = await getDocument(workspaceId, document.id);
      setDocuments((current) =>
        current.map((item) => (item.id === document.id ? updated : item)),
      );
    } catch (err) {
      showToast(
        err instanceof ApiRequestError
          ? err.message
          : "Failed to queue reprocessing.",
        "bad",
      );
    } finally {
      setReprocessingId(null);
    }
  }

  async function handleConfirmDelete() {
    if (!workspaceId || !pendingDelete) return;
    setIsDeleting(true);
    try {
      await deleteDocument(workspaceId, pendingDelete.id);
      setDocuments((current) =>
        current.filter((item) => item.id !== pendingDelete.id),
      );
      if (selectedId === pendingDelete.id) {
        setSelectedId(null);
      }
      showToast(`Deleted ${pendingDelete.name}.`, "ok");
      setPendingDelete(null);
    } catch (err) {
      showToast(
        err instanceof ApiRequestError
          ? err.message
          : "Failed to delete document.",
        "bad",
      );
    } finally {
      setIsDeleting(false);
    }
  }

  async function handleAskAbout(document: DocumentSummary) {
    if (!workspaceId) return;
    try {
      const created = await createConversation(workspaceId);
      startConversationAbout(
        created.conversation_id,
        `Tell me what you know from "${document.name}".`,
      );
    } catch (err) {
      showToast(
        err instanceof ApiRequestError
          ? err.message
          : "Failed to start a conversation.",
        "bad",
      );
    }
  }

  return (
    <div className="documents-page">
      <div className="documents-header">
        <div>
          <h1>Documents</h1>
          <p>
            Import documents to turn them into searchable, connected knowledge.
            Track processing here from upload through extraction.
          </p>
        </div>
      </div>

      <div
        className="dropzone"
        data-active={isDragActive}
        onDragOver={(event) => {
          event.preventDefault();
          setIsDragActive(true);
        }}
        onDragLeave={() => setIsDragActive(false)}
        onDrop={onDrop}
      >
        <p className="dropzone-copy">
          <strong>Drag and drop</strong> documents here, or use the file picker.
          {!canUseBackend ? " Connect to the backend to import documents." : ""}
        </p>
        <button
          type="button"
          className="primary-button"
          disabled={!canUseBackend || !workspaceId}
          onClick={() => fileInputRef.current?.click()}
        >
          Choose files
        </button>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          hidden
          onChange={(event) => {
            if (event.target.files) {
              handleFiles(event.target.files);
            }
            event.target.value = "";
          }}
        />
      </div>

      {uploads.length > 0 ? (
        <div className="upload-queue">
          {uploads.map((task) => (
            <div key={task.id} className="upload-queue-item">
              <div>
                <div className="upload-queue-name">{task.name}</div>
                <div className="upload-queue-status">
                  {task.status === "uploading"
                    ? `Uploading… ${Math.round(task.progress * 100)}%`
                    : task.status === "done"
                      ? "Uploaded"
                      : `Failed: ${task.error}`}
                </div>
                <div className="progress-bar">
                  <div
                    className="progress-bar-fill"
                    style={{ width: `${Math.round(task.progress * 100)}%` }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {error ? (
        <div className="banner" data-tone="bad" role="alert">
          {error}
        </div>
      ) : null}

      <div className="documents-split">
        {isLoading ? (
          <LoadingState label="Loading documents…" />
        ) : documents.length === 0 ? (
          <EmptyState
            title="No documents yet"
            description="Import your first document to start building knowledge."
          />
        ) : (
          <ul className="documents-list">
            {documents.map((document) => {
              const badge = processingStatusBadge(document.processing_status);
              return (
                <li key={document.id}>
                  <button
                    type="button"
                    data-active={document.id === selectedId}
                    onClick={() => setSelectedId(document.id)}
                  >
                    <div className="documents-list-title-row">
                      <span className="documents-list-title">
                        {document.name}
                      </span>
                      <StatusBadge {...badge} />
                    </div>
                    <span className="documents-list-meta">
                      {document.source_type} ·{" "}
                      {formatTimestamp(document.created_at)}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}

        <div className="document-detail panel">
          {!selectedDocument ? (
            <EmptyState
              title="Select a document"
              description="Choose a document from the list to see its processing status and details."
            />
          ) : (
            <>
              <div className="document-detail-header">
                <div>
                  <h2>{selectedDocument.name}</h2>
                  <p className="muted">
                    {formatBytesLabel(selectedDocument.mime_type)} ·{" "}
                    {selectedDocument.source_type}
                  </p>
                </div>
                <StatusBadge
                  {...processingStatusBadge(selectedDocument.processing_status)}
                />
              </div>

              {selectedDocument.processing_status === "failed" &&
              selectedDocument.processing_failure_reason ? (
                <div className="banner document-detail-error" data-tone="bad">
                  {selectedDocument.processing_failure_reason}
                </div>
              ) : null}

              <dl className="meta-grid">
                <div className="meta-card">
                  <dt>Imported</dt>
                  <dd>{formatTimestamp(selectedDocument.created_at)}</dd>
                </div>
                <div className="meta-card">
                  <dt>Last processed</dt>
                  <dd>
                    {formatTimestamp(selectedDocument.processing_updated_at)}
                  </dd>
                </div>
                <div className="meta-card">
                  <dt>Document ID</dt>
                  <dd>{selectedDocument.id}</dd>
                </div>
              </dl>

              <div className="document-detail-actions">
                <button
                  type="button"
                  className="primary-button"
                  onClick={() => void handleAskAbout(selectedDocument)}
                  disabled={
                    !canUseBackend ||
                    selectedDocument.processing_status !== "completed"
                  }
                  title={
                    selectedDocument.processing_status !== "completed"
                      ? "Available once processing completes"
                      : undefined
                  }
                >
                  Ask about this document
                </button>
                <button
                  type="button"
                  className="retry-button"
                  onClick={() => void handleReprocess(selectedDocument)}
                  disabled={
                    !canUseBackend || reprocessingId === selectedDocument.id
                  }
                >
                  {reprocessingId === selectedDocument.id
                    ? "Queuing…"
                    : "Reprocess"}
                </button>
                <button
                  type="button"
                  className="danger-button"
                  onClick={() => setPendingDelete(selectedDocument)}
                  disabled={!canUseBackend}
                >
                  Delete
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {pendingDelete ? (
        <ConfirmDialog
          title={`Delete "${pendingDelete.name}"?`}
          description="This removes the document, its stored file, and any knowledge extracted from it. This cannot be undone."
          confirmLabel="Delete"
          tone="danger"
          busy={isDeleting}
          onConfirm={() => void handleConfirmDelete()}
          onCancel={() => setPendingDelete(null)}
        />
      ) : null}
    </div>
  );
}
