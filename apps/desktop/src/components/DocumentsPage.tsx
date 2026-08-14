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
import {
  DOCUMENT_READY_TOAST,
  formatFailureReason,
  presentIndexedState,
  presentProcessingStatus,
  shouldPollProcessing,
} from "../documents/processingPresentation";
import { useAppState } from "../state/AppStateContext";
import { Alert } from "./ui/Alert";
import { Button } from "./ui/Button";
import { ConfirmDialog } from "./ui/ConfirmDialog";
import { EmptyState } from "./ui/EmptyState";
import { FilePicker } from "./ui/FilePicker";
import { LoadingState } from "./ui/LoadingState";
import { ProgressBar } from "./ui/ProgressBar";
import { SectionHeader } from "./ui/SectionHeader";
import { processingStatusBadge, StatusBadge } from "./ui/StatusBadge";
import { useToast } from "./ui/ToastContext";

interface UploadTask {
  id: string;
  name: string;
  progress: number;
  status: "uploading" | "done" | "error";
  error?: string;
}

export const DOCUMENT_STATUS_POLL_INTERVAL_MS = 2500;

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
  const {
    activeWorkspace,
    connection,
    startConversationAbout,
    setActivePage,
    documentSeed,
    clearDocumentSeed,
  } = useAppState();
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
  const hasLoadedOnceRef = useRef(false);
  const previousStatusRef = useRef<Map<string, string | null>>(new Map());
  const mountedRef = useRef(true);
  const refreshInFlightRef = useRef(false);
  const pendingRefreshRef = useRef(false);

  const selectedDocument = useMemo(
    () => documents.find((doc) => doc.id === selectedId) ?? null,
    [documents, selectedId],
  );

  const needsPolling = documents.some((doc) =>
    shouldPollProcessing(doc.processing_status),
  );

  const inFlightCount = documents.filter(
    (doc) => presentProcessingStatus(doc.processing_status).isInFlight,
  ).length;

  const failedCount = documents.filter(
    (doc) => doc.processing_status === "failed",
  ).length;

  const applyDocumentList = useCallback(
    (items: DocumentSummary[]) => {
      if (hasLoadedOnceRef.current) {
        for (const document of items) {
          const previous = previousStatusRef.current.has(document.id)
            ? previousStatusRef.current.get(document.id)
            : undefined;
          if (
            document.processing_status === "completed" &&
            previous !== "completed"
          ) {
            showToast(DOCUMENT_READY_TOAST, "ok");
          }
        }
      }
      previousStatusRef.current = new Map(
        items.map((document) => [
          document.id,
          document.processing_status ?? null,
        ]),
      );
      hasLoadedOnceRef.current = true;
      setDocuments(items);
      setSelectedId((current) => {
        if (current && items.some((item) => item.id === current)) {
          return current;
        }
        return items[0]?.id ?? null;
      });
    },
    [showToast],
  );

  const refresh = useCallback(async () => {
    if (!workspaceId || !canUseBackend) {
      setDocuments([]);
      return;
    }
    if (refreshInFlightRef.current) {
      pendingRefreshRef.current = true;
      return;
    }
    refreshInFlightRef.current = true;
    try {
      do {
        pendingRefreshRef.current = false;
        const docsPayload = await listDocuments(workspaceId);
        if (!mountedRef.current) return;
        applyDocumentList(docsPayload.items);
      } while (pendingRefreshRef.current && mountedRef.current);
    } catch (err) {
      if (!mountedRef.current) return;
      setError(
        err instanceof ApiRequestError
          ? err.message
          : "Failed to load documents.",
      );
    } finally {
      refreshInFlightRef.current = false;
    }
  }, [workspaceId, canUseBackend, applyDocumentList]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    if (!workspaceId || !canUseBackend) {
      setDocuments([]);
      setSelectedId(null);
      hasLoadedOnceRef.current = false;
      previousStatusRef.current = new Map();
      return;
    }
    let cancelled = false;
    setIsLoading(true);
    setError(null);
    void listDocuments(workspaceId)
      .then((docsPayload) => {
        if (cancelled || !mountedRef.current) return;
        applyDocumentList(docsPayload.items);
      })
      .catch((err: unknown) => {
        if (!cancelled && mountedRef.current) {
          setError(
            err instanceof ApiRequestError
              ? err.message
              : "Failed to load documents.",
          );
        }
      })
      .finally(() => {
        if (!cancelled && mountedRef.current) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [workspaceId, canUseBackend, applyDocumentList]);

  useEffect(() => {
    if (!documentSeed) return;
    setSelectedId(documentSeed.documentId);
    clearDocumentSeed();
  }, [documentSeed, clearDocumentSeed]);

  useEffect(() => {
    if (!needsPolling || !workspaceId || !canUseBackend) {
      return;
    }
    const timer = window.setInterval(() => {
      void refresh();
    }, DOCUMENT_STATUS_POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [needsPolling, workspaceId, canUseBackend, refresh]);

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
      showToast(`Processing queued again for ${document.name}.`, "ok");
      try {
        sessionStorage.setItem(
          `memovi.reprocess.${document.id}`,
          new Date().toISOString(),
        );
      } catch {
        // Activity uses this hint when present; ignore storage failures.
      }
      const updated = await getDocument(workspaceId, document.id);
      if (mountedRef.current) {
        setDocuments((current) =>
          current.map((item) => (item.id === document.id ? updated : item)),
        );
        previousStatusRef.current.set(
          updated.id,
          updated.processing_status ?? null,
        );
      }
      void refresh();
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
      previousStatusRef.current.delete(pendingDelete.id);
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

  const selectedView = selectedDocument
    ? presentProcessingStatus(selectedDocument.processing_status)
    : null;
  const selectedIndexed = selectedDocument
    ? presentIndexedState(selectedDocument.processing_status)
    : null;
  const selectedIsReady = selectedDocument?.processing_status === "completed";
  const failureReason = selectedDocument
    ? formatFailureReason(selectedDocument.processing_failure_reason)
    : null;

  return (
    <div className="documents-page">
      <SectionHeader
        title="Documents"
        description="Import documents to turn them into searchable, connected knowledge. Track processing here from upload through ready to search."
        level={1}
      />

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
        <FilePicker
          disabled={!canUseBackend || !workspaceId}
          buttonLabel="Choose files"
          onFilesSelected={handleFiles}
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
                      ? "Uploaded — queued for processing"
                      : `Failed: ${task.error}`}
                </div>
                <ProgressBar
                  value={Math.round(task.progress * 100)}
                  label="Upload"
                />
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {error ? <Alert tone="bad">{error}</Alert> : null}

      {!error && (inFlightCount > 0 || failedCount > 0) ? (
        <div className="documents-status-summary" role="status">
          {inFlightCount > 0 ? (
            <span>
              {inFlightCount === 1
                ? "1 document processing"
                : `${inFlightCount} documents processing`}
            </span>
          ) : null}
          {failedCount > 0 ? (
            <span className="documents-status-summary--attention">
              {failedCount === 1
                ? "1 document needs attention — open it and retry"
                : `${failedCount} documents need attention — open one and retry`}
            </span>
          ) : null}
        </div>
      ) : null}

      <div className="documents-split">
        {isLoading ? (
          <LoadingState label="Loading documents…" />
        ) : documents.length === 0 ? (
          <EmptyState
            title="No documents yet"
            description="Import your first document to start building knowledge. Processing status will appear here as soon as upload finishes."
            action={
              canUseBackend ? (
                <FilePicker
                  buttonLabel="Import a document"
                  onFilesSelected={handleFiles}
                />
              ) : undefined
            }
          />
        ) : (
          <ul className="documents-list">
            {documents.map((document) => {
              const badge = processingStatusBadge(document.processing_status);
              const view = presentProcessingStatus(document.processing_status);
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
                      {view.explanation}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}

        <div className="document-detail panel">
          {!selectedDocument || !selectedView || !selectedIndexed ? (
            <EmptyState
              title="Select a document"
              description="Choose a document from the list to see processing status and what you can do next."
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
                <div className="document-detail-badges">
                  <StatusBadge
                    {...processingStatusBadge(
                      selectedDocument.processing_status,
                    )}
                  />
                </div>
              </div>

              <div className="document-processing-panel">
                {selectedView.isInFlight ? (
                  <LoadingState label={selectedView.explanation} />
                ) : (
                  <p className="document-processing-stage">
                    {selectedView.explanation}
                  </p>
                )}
                <p className="muted document-processing-hint">
                  {selectedIndexed.detail}
                </p>
                {selectedView.nextActionHint ? (
                  <p className="document-processing-next">
                    {selectedView.nextActionHint}
                  </p>
                ) : null}
              </div>

              {selectedDocument.processing_status === "failed" ? (
                <Alert tone="bad" className="document-detail-error">
                  Processing failed
                  {failureReason ? `: ${failureReason}` : "."} Try processing
                  again.
                </Alert>
              ) : null}

              {selectedDocument.processing_status === "cancelled" ? (
                <Alert tone="warn" className="document-detail-error">
                  {failureReason
                    ? failureReason
                    : "Processing was cancelled—often because a newer reprocess replaced it."}{" "}
                  Try processing again.
                </Alert>
              ) : null}

              <dl className="meta-grid">
                <div className="meta-card">
                  <dt>Imported</dt>
                  <dd>{formatTimestamp(selectedDocument.created_at)}</dd>
                </div>
                <div className="meta-card">
                  <dt>Started</dt>
                  <dd>
                    {formatTimestamp(selectedDocument.processing_started_at)}
                  </dd>
                </div>
                <div className="meta-card">
                  <dt>Completed</dt>
                  <dd>
                    {formatTimestamp(
                      selectedDocument.processing_completed_at ??
                        (selectedDocument.processing_status === "completed"
                          ? selectedDocument.processing_updated_at
                          : null),
                    )}
                  </dd>
                </div>
                <div className="meta-card">
                  <dt>Last update</dt>
                  <dd>
                    {formatTimestamp(selectedDocument.processing_updated_at)}
                  </dd>
                </div>
                <div className="meta-card">
                  <dt>Attempt</dt>
                  <dd>{selectedDocument.processing_attempt ?? "—"}</dd>
                </div>
                <div className="meta-card">
                  <dt>Document ID</dt>
                  <dd>{selectedDocument.id}</dd>
                </div>
              </dl>

              <div className="document-detail-actions">
                {selectedIsReady ? (
                  <>
                    <Button onClick={() => setActivePage("search")}>
                      Search it
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={() => void handleAskAbout(selectedDocument)}
                      disabled={!canUseBackend}
                    >
                      Ask about this
                    </Button>
                  </>
                ) : (
                  <Button
                    onClick={() => void handleAskAbout(selectedDocument)}
                    disabled
                    title="Available once this document is ready"
                  >
                    Ask about this
                  </Button>
                )}
                <Button
                  variant={
                    selectedView.requiresAttention ? "primary" : "secondary"
                  }
                  onClick={() => void handleReprocess(selectedDocument)}
                  busy={reprocessingId === selectedDocument.id}
                  disabled={!canUseBackend}
                >
                  {reprocessingId === selectedDocument.id
                    ? "Queuing…"
                    : selectedView.requiresAttention
                      ? "Retry processing"
                      : "Reprocess"}
                </Button>
                <Button
                  variant="danger"
                  onClick={() => setPendingDelete(selectedDocument)}
                  disabled={!canUseBackend}
                >
                  Delete
                </Button>
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
