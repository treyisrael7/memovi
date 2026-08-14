/**
 * User-visible presentation over Documents `processing_status` values.
 * Does not invent stages the backend cannot distinguish (no embedding /
 * knowledge-materialization substeps). The document list is the source of truth.
 *
 * Never invents indeterminate progress percentages.
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
  "Received" | "Processing" | "Ready" | "Failed" | "Cancelled" | "Unknown";

export type IndexedState =
  "indexed" | "not_indexed" | "failed" | "cancelled" | "unknown";

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

export const DOCUMENT_READY_TOAST = "Document ready to search.";

/**
 * Map Documents processing_status → user-facing lifecycle presentation.
 *
 * Backend owns: pending | extracting | normalizing | completed | failed | cancelled.
 * extracting vs normalizing are both shown as "Processing" — the UI cannot
 * honestly show embedding or search-index substeps from this field.
 */
export function presentProcessingStatus(
  status: string | null | undefined,
  _options?: { hasKnowledge?: boolean; hasModel?: boolean },
): ProcessingPresentation {
  const normalized = (status ?? "").toLowerCase();

  switch (normalized) {
    case "pending":
      return {
        status: "pending",
        label: "Received",
        tone: "idle",
        explanation:
          "Memovi received this document. It is waiting to be processed.",
        nextActionHint: null,
        isInFlight: true,
        canRetry: false,
        requiresAttention: false,
      };
    case "extracting":
    case "normalizing":
      return {
        status: normalized as "extracting" | "normalizing",
        label: "Processing",
        tone: "warn",
        explanation: "Memovi is processing this document.",
        nextActionHint: null,
        isInFlight: true,
        canRetry: false,
        requiresAttention: false,
      };
    case "completed":
      return {
        status: "completed",
        label: "Ready",
        tone: "ok",
        explanation: "This is ready to search.",
        nextActionHint: "Search it or ask about this document.",
        isInFlight: false,
        canRetry: true,
        requiresAttention: false,
      };
    case "failed":
      return {
        status: "failed",
        label: "Failed",
        tone: "bad",
        explanation: "Processing failed.",
        nextActionHint: "Try processing again.",
        isInFlight: false,
        canRetry: true,
        requiresAttention: true,
      };
    case "cancelled":
      return {
        status: "cancelled",
        label: "Cancelled",
        tone: "idle",
        explanation: "Processing stopped before this document was ready.",
        nextActionHint: "Try processing again.",
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
        nextActionHint: status ? "Try processing again." : null,
        isInFlight: false,
        canRetry: Boolean(status),
        requiresAttention: false,
      };
  }
}

/**
 * Search-readiness presentation derived only from Documents processing_status.
 * Knowledge presence and embedding availability are not distinct backend
 * document states, so they are not shown as separate stages.
 */
export function presentIndexedState(
  status: string | null | undefined,
  _hasKnowledge?: boolean,
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
      detail: "Processing was cancelled. Try processing again.",
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
    return {
      state: "indexed",
      label: "Ready",
      tone: "ok",
      detail: "Available in search and conversations.",
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

/** Whether status updates should keep polling (non-terminal Documents job). */
export function shouldPollProcessing(
  status: string | null | undefined,
  _hasKnowledge?: boolean,
): boolean {
  return isProcessingInFlight(status);
}

/** User-safe failure copy; never returns stack frames or tracebacks. */
export function formatFailureReason(
  reason: string | null | undefined,
): string | null {
  if (!reason?.trim()) return null;
  const trimmed = reason.trim();
  const looksLikeTrace =
    /traceback \(most recent call last\)/i.test(trimmed) ||
    /file ".+", line \d+/i.test(trimmed) ||
    /^\s*at \S+/m.test(trimmed) ||
    trimmed.includes("\n    at ");

  if (looksLikeTrace) {
    const lines = trimmed
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean);
    const last = lines[lines.length - 1] ?? "";
    const lastLooksSafe =
      last.length > 0 &&
      last.length <= 200 &&
      !/^file /i.test(last) &&
      !last.startsWith("at ") &&
      !/traceback/i.test(last);
    return lastLooksSafe ? last : "Processing failed.";
  }

  if (trimmed.length > 280) {
    return `${trimmed.slice(0, 277)}…`;
  }
  return trimmed;
}
