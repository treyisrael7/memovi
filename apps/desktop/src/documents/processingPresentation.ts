/**
 * User-visible presentation over the Documents processing_status values.
 * Does not invent a parallel status model — maps backend enums and optional
 * knowledge presence (post-completion indexing) for desktop UX.
 */

export const DOCUMENT_PROCESSING_STATUSES = [
  "pending",
  "extracting",
  "normalizing",
  "completed",
  "failed",
  "cancelled",
] as const;

export type DocumentProcessingStatus =
  (typeof DOCUMENT_PROCESSING_STATUSES)[number];

export type ProcessingTone = "ok" | "warn" | "bad" | "idle";

/** High-level lifecycle label shown in badges. */
export type LifecycleLabel =
  | "Uploaded"
  | "Queued"
  | "Processing"
  | "Chunking"
  | "Embedding"
  | "Indexing"
  | "Completed"
  | "Failed"
  | "Cancelled"
  | "Unknown";

export type IndexedState =
  | "indexed"
  | "indexing"
  | "not_indexed"
  | "failed"
  | "cancelled"
  | "unknown";

export interface ProcessingPresentation {
  /** Canonical backend status when recognized. */
  status: DocumentProcessingStatus | null;
  /** Primary badge label (lifecycle vocabulary). */
  label: LifecycleLabel | string;
  tone: ProcessingTone;
  /** Finer stage estimate for progress copy. */
  estimatedStage: string;
  /** 0–100 progress for in-flight / terminal jobs. */
  progressPercent: number;
  /** True while Documents job is non-terminal. */
  isInFlight: boolean;
  /** True when Reprocess is the primary recovery action. */
  canRetry: boolean;
  requiresAttention: boolean;
}

export interface IndexedPresentation {
  state: IndexedState;
  label: string;
  tone: ProcessingTone;
  detail: string;
}

const IN_FLIGHT = new Set<string>(["pending", "extracting", "normalizing"]);

/**
 * Map Documents processing_status → user-facing lifecycle presentation.
 *
 * Backend owns: pending | extracting | normalizing | completed | failed | cancelled.
 * Chunking / Embedding / Indexing are estimated stages within that lifecycle
 * (normalizing ≈ preparing chunks; post-completed catch-up ≈ indexing).
 */
export function presentProcessingStatus(
  status: string | null | undefined,
  options?: { hasKnowledge?: boolean },
): ProcessingPresentation {
  const normalized = (status ?? "").toLowerCase();
  const hasKnowledge = options?.hasKnowledge === true;

  switch (normalized) {
    case "pending":
      return {
        status: "pending",
        label: "Queued",
        tone: "idle",
        estimatedStage: "Queued — waiting for a worker",
        progressPercent: 15,
        isInFlight: true,
        canRetry: false,
        requiresAttention: false,
      };
    case "extracting":
      return {
        status: "extracting",
        label: "Processing",
        tone: "warn",
        estimatedStage: "Extracting text",
        progressPercent: 40,
        isInFlight: true,
        canRetry: false,
        requiresAttention: false,
      };
    case "normalizing":
      return {
        status: "normalizing",
        label: "Chunking",
        tone: "warn",
        estimatedStage: "Normalizing and preparing knowledge",
        progressPercent: 65,
        isInFlight: true,
        canRetry: false,
        requiresAttention: false,
      };
    case "completed":
      if (!hasKnowledge && options?.hasKnowledge === false) {
        return {
          status: "completed",
          label: "Indexing",
          tone: "warn",
          estimatedStage: "Indexing for search",
          progressPercent: 85,
          isInFlight: false,
          canRetry: true,
          requiresAttention: false,
        };
      }
      return {
        status: "completed",
        label: "Completed",
        tone: "ok",
        estimatedStage: hasKnowledge
          ? "Knowledge ready and indexed"
          : "Processing complete",
        progressPercent: 100,
        isInFlight: false,
        canRetry: true,
        requiresAttention: false,
      };
    case "failed":
      return {
        status: "failed",
        label: "Failed",
        tone: "bad",
        estimatedStage: "Processing failed",
        progressPercent: 100,
        isInFlight: false,
        canRetry: true,
        requiresAttention: true,
      };
    case "cancelled":
      return {
        status: "cancelled",
        label: "Cancelled",
        tone: "idle",
        estimatedStage: "Superseded or cancelled",
        progressPercent: 0,
        isInFlight: false,
        canRetry: true,
        requiresAttention: true,
      };
    default:
      return {
        status: null,
        label: status ? status : "Unknown",
        tone: "idle",
        estimatedStage: status ? String(status) : "Unknown status",
        progressPercent: 0,
        isInFlight: false,
        canRetry: Boolean(status),
        requiresAttention: false,
      };
  }
}

/** Indexed / not-yet-indexed presentation derived from job status + knowledge. */
export function presentIndexedState(
  status: string | null | undefined,
  hasKnowledge: boolean | undefined,
): IndexedPresentation {
  const normalized = (status ?? "").toLowerCase();

  if (normalized === "failed") {
    return {
      state: "failed",
      label: "Failed indexing",
      tone: "bad",
      detail: "Processing failed before this document could be indexed.",
    };
  }
  if (normalized === "cancelled") {
    return {
      state: "cancelled",
      label: "Not indexed",
      tone: "idle",
      detail: "Processing was cancelled. Reprocess to index again.",
    };
  }
  if (IN_FLIGHT.has(normalized)) {
    return {
      state: "not_indexed",
      label: "Not yet indexed",
      tone: "idle",
      detail: "Still processing — it will not appear in search yet.",
    };
  }
  if (normalized === "completed") {
    if (hasKnowledge === true) {
      return {
        state: "indexed",
        label: "Indexed",
        tone: "ok",
        detail: "Available in search and conversations.",
      };
    }
    if (hasKnowledge === false) {
      return {
        state: "indexing",
        label: "Indexing",
        tone: "warn",
        detail: "Processing finished; knowledge indexing is catching up.",
      };
    }
    return {
      state: "unknown",
      label: "Completed",
      tone: "ok",
      detail: "Processing complete.",
    };
  }
  return {
    state: "unknown",
    label: "Unknown",
    tone: "idle",
    detail: "Indexing status is unavailable.",
  };
}

export function isProcessingInFlight(
  status: string | null | undefined,
): boolean {
  return IN_FLIGHT.has((status ?? "").toLowerCase());
}

/** Whether status updates should keep polling (job in flight or indexing lag). */
export function shouldPollProcessing(
  status: string | null | undefined,
  hasKnowledge: boolean | undefined,
): boolean {
  if (isProcessingInFlight(status)) return true;
  return (
    (status ?? "").toLowerCase() === "completed" && hasKnowledge === false
  );
}
