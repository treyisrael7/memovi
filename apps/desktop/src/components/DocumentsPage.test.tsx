import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import type { DocumentSummary } from "../api/types";
import { DOCUMENT_READY_TOAST } from "../documents/processingPresentation";
import {
  DOCUMENT_STATUS_POLL_INTERVAL_MS,
  DocumentsPage,
} from "./DocumentsPage";

const listDocuments = vi.fn();
const uploadDocument = vi.fn();
const reprocessDocument = vi.fn();
const getDocument = vi.fn();
const deleteDocument = vi.fn();
const createConversation = vi.fn();
const setActivePage = vi.fn();
const startConversationAbout = vi.fn();
const clearDocumentSeed = vi.fn();
const showToast = vi.fn();

vi.mock("./ui/ToastContext", () => ({
  useToast: () => ({ showToast }),
}));

vi.mock("../api/documents", () => ({
  listDocuments: (...args: unknown[]) => listDocuments(...args),
  uploadDocument: (...args: unknown[]) => uploadDocument(...args),
  reprocessDocument: (...args: unknown[]) => reprocessDocument(...args),
  getDocument: (...args: unknown[]) => getDocument(...args),
  deleteDocument: (...args: unknown[]) => deleteDocument(...args),
}));

vi.mock("../api/conversations", () => ({
  createConversation: (...args: unknown[]) => createConversation(...args),
}));

const appState = {
  activeWorkspace: { id: "ws-1", name: "Test" },
  connection: { status: "connected" as const },
  activeModel: null as {
    provider: string;
    model: string;
    label: string;
  } | null,
  startConversationAbout,
  setActivePage,
  documentSeed: null,
  clearDocumentSeed,
};

vi.mock("../state/AppStateContext", () => ({
  useAppState: () => appState,
}));

function doc(overrides: Partial<DocumentSummary> = {}): DocumentSummary {
  return {
    id: "doc-1",
    name: "notes.txt",
    mime_type: "text/plain",
    source_type: "upload",
    created_at: "2026-01-01T00:00:00.000Z",
    processing_status: "pending",
    ...overrides,
  };
}

function renderPage() {
  return render(<DocumentsPage />);
}

describe("DocumentsPage processing UX", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    appState.activeModel = null;
    listDocuments.mockReset();
    uploadDocument.mockReset();
    reprocessDocument.mockReset();
    getDocument.mockReset();
    deleteDocument.mockReset();
    createConversation.mockReset();
    setActivePage.mockReset();
    startConversationAbout.mockReset();
    showToast.mockReset();
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  it("shows received then processing after upload", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const current = { items: [] as DocumentSummary[] };
    listDocuments.mockImplementation(async () => ({ items: current.items }));
    uploadDocument.mockResolvedValue({
      document_id: "doc-1",
      processing_job_id: "job-1",
      processing_status: "pending",
    });

    renderPage();
    expect(await screen.findByText(/No documents yet/i)).toBeInTheDocument();

    current.items = [doc({ processing_status: "pending" })];
    const fileInput = document.querySelector(
      'input[type="file"]',
    ) as HTMLInputElement;
    const file = new File(["hello"], "notes.txt", { type: "text/plain" });
    await user.upload(fileInput, file);

    expect(
      await screen.findByText(/Uploaded — queued for processing/i),
    ).toBeInTheDocument();
    expect((await screen.findAllByText(/^Received$/i)).length).toBeGreaterThan(
      0,
    );
    expect(
      screen.getAllByText(/Memovi received this document/i).length,
    ).toBeGreaterThan(0);

    current.items = [doc({ processing_status: "extracting" })];
    await vi.advanceTimersByTimeAsync(DOCUMENT_STATUS_POLL_INTERVAL_MS);
    expect(
      (await screen.findAllByText(/^Processing$/i)).length,
    ).toBeGreaterThan(0);
    expect(
      screen.getAllByText(/Memovi is processing this document/i).length,
    ).toBeGreaterThan(0);
  });

  it("transitions processing → ready and toasts once", async () => {
    const current = {
      items: [doc({ processing_status: "extracting" })],
    };
    listDocuments.mockImplementation(async () => ({ items: current.items }));

    renderPage();
    expect(
      (await screen.findAllByText(/^Processing$/i)).length,
    ).toBeGreaterThan(0);

    current.items = [doc({ processing_status: "completed" })];
    await vi.advanceTimersByTimeAsync(DOCUMENT_STATUS_POLL_INTERVAL_MS);
    expect((await screen.findAllByText(/^Ready$/i)).length).toBeGreaterThan(0);
    expect(showToast).toHaveBeenCalledWith(DOCUMENT_READY_TOAST, "ok");
    expect(screen.getByRole("button", { name: /^Search it$/i })).toBeEnabled();
    expect(
      screen.getByRole("button", { name: /^Ask about this$/i }),
    ).toBeEnabled();

    expect(
      showToast.mock.calls.filter((call) => call[0] === DOCUMENT_READY_TOAST),
    ).toHaveLength(1);
    await vi.advanceTimersByTimeAsync(DOCUMENT_STATUS_POLL_INTERVAL_MS);
    await vi.advanceTimersByTimeAsync(DOCUMENT_STATUS_POLL_INTERVAL_MS);
    expect(
      showToast.mock.calls.filter((call) => call[0] === DOCUMENT_READY_TOAST),
    ).toHaveLength(1);
  });

  it("shows a failed state with retry, without stack traces", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    listDocuments.mockResolvedValue({
      items: [
        doc({
          processing_status: "failed",
          processing_failure_reason: `Traceback (most recent call last):
  File "worker.py", line 9, in run
RuntimeError: parser exploded`,
        }),
      ],
    });
    reprocessDocument.mockResolvedValue({
      processing_job_id: "job-2",
      processing_status: "pending",
    });
    getDocument.mockResolvedValue(doc({ processing_status: "pending" }));

    renderPage();
    expect((await screen.findAllByText(/^Failed$/i)).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Processing failed/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Try processing again/i).length).toBeGreaterThan(
      0,
    );
    expect(screen.queryByText(/worker\.py/)).not.toBeInTheDocument();
    expect(screen.getByText(/parser exploded/i)).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: /^Retry processing$/i }),
    );
    await waitFor(() => {
      expect(reprocessDocument).toHaveBeenCalledWith("ws-1", "doc-1");
    });
    expect(showToast).toHaveBeenCalledWith(
      "Processing queued again for notes.txt.",
      "ok",
    );
  });

  it("stops polling after unmount and after a terminal status", async () => {
    const current = {
      items: [doc({ processing_status: "pending" })],
    };
    listDocuments.mockImplementation(async () => ({ items: current.items }));

    const view = renderPage();
    await screen.findAllByText(/^Received$/i);
    const callsAfterLoad = listDocuments.mock.calls.length;

    await vi.advanceTimersByTimeAsync(DOCUMENT_STATUS_POLL_INTERVAL_MS);
    expect(listDocuments.mock.calls.length).toBeGreaterThan(callsAfterLoad);

    current.items = [doc({ processing_status: "completed" })];
    await vi.advanceTimersByTimeAsync(DOCUMENT_STATUS_POLL_INTERVAL_MS);
    await screen.findAllByText(/^Ready$/i);
    const callsWhenReady = listDocuments.mock.calls.length;

    await vi.advanceTimersByTimeAsync(DOCUMENT_STATUS_POLL_INTERVAL_MS * 3);
    expect(listDocuments.mock.calls.length).toBe(callsWhenReady);

    current.items = [doc({ processing_status: "pending" })];
    listDocuments.mockClear();
    view.unmount();
    await vi.advanceTimersByTimeAsync(DOCUMENT_STATUS_POLL_INTERVAL_MS * 3);
    expect(listDocuments).not.toHaveBeenCalled();
  });

  it("does not show indexing messaging when no model is configured", async () => {
    appState.activeModel = null;
    listDocuments.mockResolvedValue({
      items: [doc({ processing_status: "completed" })],
    });

    renderPage();
    expect((await screen.findAllByText(/^Ready$/i)).length).toBeGreaterThan(0);
    expect(screen.queryByText(/^Indexing$/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/embedd/i)).not.toBeInTheDocument();
    expect(
      screen.getAllByText(/This is ready to search/i).length,
    ).toBeGreaterThan(0);
  });
});
