export type StatusTone = "ok" | "warn" | "bad" | "idle";

interface StatusBadgeProps {
  label: string;
  tone: StatusTone;
}

/** Consistent status pill used for processing status, executions, and workflows. */
export function StatusBadge({ label, tone }: StatusBadgeProps) {
  return (
    <span className="status-badge" data-tone={tone}>
      {label}
    </span>
  );
}

const PROCESSING_TONE: Record<string, StatusTone> = {
  pending: "idle",
  extracting: "warn",
  normalizing: "warn",
  completed: "ok",
  failed: "bad",
};

const PROCESSING_LABEL: Record<string, string> = {
  pending: "Queued",
  extracting: "Extracting",
  normalizing: "Normalizing",
  completed: "Knowledge ready",
  failed: "Processing failed",
};

/** Maps a document processing status to a shared badge presentation. */
export function processingStatusBadge(
  status: string | null | undefined,
): StatusBadgeProps {
  if (!status) {
    return { label: "Unknown", tone: "idle" };
  }
  return {
    label: PROCESSING_LABEL[status] ?? status,
    tone: PROCESSING_TONE[status] ?? "idle",
  };
}

const EXECUTION_TONE: Record<string, StatusTone> = {
  pending_approval: "warn",
  executing: "warn",
  running: "warn",
  awaiting_approval: "warn",
  completed: "ok",
  failed: "bad",
  cancelled: "idle",
};

const EXECUTION_LABEL: Record<string, string> = {
  pending_approval: "Needs approval",
  executing: "Running",
  running: "Running",
  awaiting_approval: "Needs approval",
  completed: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
};

/** Maps a capability/workflow execution status to a shared badge presentation. */
export function executionStatusBadge(status: string): StatusBadgeProps {
  return {
    label: EXECUTION_LABEL[status] ?? status,
    tone: EXECUTION_TONE[status] ?? "idle",
  };
}
