/**
 * User-visible presentation over the Documents processing_status values.
 * Does not invent a parallel status model — maps backend enums and optional
 * knowledge presence (post-completion indexing) for desktop UX.
 *
 * Never invents indeterminate progress percentages. Stages shown here are only
 * what can be inferred from Documents status + whether knowledge exists yet.
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
  | "Queued"
  | "Processing"
  | "Indexing"
  | "Ready"
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
  /** Short plain-language explanation of what is happening. */
  explanation: string;
  /** What the user should do next, when actionable. */
  nextActionHint: string | null;
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
 * "Indexing" is inferred only when processing completed but knowledge is not
 * present yet (materialization / search catch-up).
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
        explanation: "Waiting for Memovi to start reading this document.",
        nextActionHint: null,
        isInFlight: true,
        canRetry: false,
        requiresAttention: false,
      };
    case "extracting":
      return {
        status: "extracting",
        label: "Processing",
        tone: "warn",
        explanation: "Reading the document and extracting its text.",
        nextActionHint: null,
        isInFlight: true,
        canRetry: false,
        requiresAttention: false,
      };
    case "normalizing":
      return {
        status: "normalizing",
        label: "Processing",
        tone: "warn",
        explanation: "Preparing the document so Memovi can understand it.",
        nextActionHint: null,
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
          explanation: "Generating searchable knowledge from this document.",
          nextActionHint: null,
          isInFlight: false,
          canRetry: true,
          requiresAttention: false,
        };
      }
      return {
        status: "completed",
        label: "Ready",
        tone: "ok",
        explanation: hasKnowledge
          ? "This document is ready to search and ask about."
          : "Processing finished. Memovi will show it as ready once knowledge appears.",
        nextActionHint: hasKnowledge
          ? "Search it or ask a question about it."
          : null,
        isInFlight: false,
        canRetry: true,
        requiresAttention: false,
      };
    case "failed":
      return {
        status: "failed",
        label: "Failed",
        tone: "bad",
        explanation: "Memovi could not finish processing this document.",
        nextActionHint:
          "Try Retry processing. If it fails again, check the file format or re-upload.",
        isInFlight: false,
        canRetry: true,
        requiresAttention: true,
      };
    case "cancelled":
      return {
        status: "cancelled",
        label: "Cancelled",
        tone: "idle",
        explanation:
          "Processing stopped—often because a newer reprocess replaced it.",
        nextActionHint: "Use Retry processing to run it again.",
        isInFlight: false,
        canRetry: true,
        requiresAttention: true,
      };
    default:
      return {
        status: null,
        label: status ? status : "Unknown",
        tone: "idle",
        explanation: status
          ? `Unrecognized status: ${status}`
          : "Processing status is unavailable.",
        nextActionHint: status ? "Try Retry processing." : null,
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
      label: "Failed",
      tone: "bad",
      detail: "Processing failed before this document could become searchable.",
    };
  }
  if (normalized === "cancelled") {
    return {
      state: "cancelled",
      label: "Not ready",
      tone: "idle",
      detail: "Processing was cancelled. Retry to make it searchable.",
    };
  }
  if (IN_FLIGHT.has(normalized)) {
    return {
      state: "not_indexed",
      label: "Not ready",
      tone: "idle",
      detail: "Still processing — it will not appear in search yet.",
    };
  }
  if (normalized === "completed") {
    if (hasKnowledge === true) {
      return {
        state: "indexed",
        label: "Ready",
        tone: "ok",
        detail: "Available in search and conversations.",
      };
    }
    if (hasKnowledge === false) {
      return {
        state: "indexing",
        label: "Indexing",
        tone: "warn",
        detail: "Generating searchable knowledge.",
      };
    }
    return {
      state: "unknown",
      label: "Ready",
      tone: "ok",
      detail: "Processing complete.",
    };
  }
  return {
    state: "unknown",
    label: "Unknown",
    tone: "idle",
    detail: "Search readiness is unavailable.",
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
