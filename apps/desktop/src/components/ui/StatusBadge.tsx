import { Badge, type BadgeTone } from "./Badge";
import {
  presentProcessingStatus,
  type ProcessingTone,
} from "../../documents/processingPresentation";

export type StatusTone = ProcessingTone;

interface StatusBadgeProps {
  label: string;
  tone: StatusTone;
}

/** Consistent status pill used for processing status, executions, and workflows. */
export function StatusBadge({ label, tone }: StatusBadgeProps) {
  return <Badge label={label} tone={tone as BadgeTone} />;
}

/** Maps a document processing status to a shared badge presentation. */
export function processingStatusBadge(
  status: string | null | undefined,
  options?: { hasKnowledge?: boolean },
): StatusBadgeProps {
  const view = presentProcessingStatus(status, options);
  return { label: view.label, tone: view.tone };
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
